"""Fine-tune a small GLiNER2-PII checkpoint for the cloud pipeline."""

import hashlib
import json
import os
import random
import sys
import tarfile
import time
from pathlib import Path

import mlflow
import torch
import yaml
from datasets import load_dataset
from gliner2 import AutoExtractor, InputExample
from gliner2.training.trainer import ExtractorTrainer, TrainingConfig
from google.cloud import secretmanager
from huggingface_hub import snapshot_download
from tracking import tracked_run

LANGUAGES = {"en", "fr", "de", "it"}
LABELS = {
    "GIVENNAME": "first_name",
    "SURNAME": "last_name",
    "EMAIL": "email",
    "TELEPHONENUM": "phone_number",
    "STREET": "street_address",
    "CITY": "city",
    "ZIPCODE": "postal_code",
    "SOCIALNUM": "national_id_number",
    "IDCARDNUM": "government_id",
    "PASSPORTNUM": "passport_number",
    "DRIVERLICENSENUM": "drivers_license_number",
    "TAXNUM": "tax_number",
    "CREDITCARDNUMBER": "card_number",
}
TARGETS = sorted(set(LABELS.values()))
PASSWORD_RESOURCE = "projects/tsmmachledata-projet/secrets/mlflow-training-password/versions/latest"


def load_rows(settings):
    stream = load_dataset(
        settings["dataset"],
        revision=settings["dataset_revision"],
        split="train",
        streaming=True,
    )
    stream = stream.filter(lambda row: row.get("language") in LANGUAGES)
    stream = stream.shuffle(seed=settings["seed"], buffer_size=10_000)
    rows = []
    for row in stream.take(settings["rows"]):
        text = row["source_text"]
        mask = row["privacy_mask"]
        mask = json.loads(mask) if isinstance(mask, str) else mask
        entities = {label: [] for label in TARGETS}
        spans = []
        for item in mask:
            label = LABELS.get(item["label"])
            if label is None:
                continue
            value = text[item["start"] : item["end"]]
            spans.append((item["start"], item["end"]))
            if value not in entities[label]:
                entities[label].append(value)
        rows.append({"text": text, "entities": entities, "spans": spans})
    return rows


def recall(model, rows):
    model.eval()
    if hasattr(model, "processor"):
        model.processor.change_mode(is_training=False)
    with torch.no_grad():
        results = model.batch_extract_entities(
            [row["text"] for row in rows], TARGETS, batch_size=16, include_spans=True
        )
    found = total = 0
    for row, result in zip(rows, results, strict=True):
        masked = set()
        for items in result["entities"].values():
            for item in items:
                masked.update(range(item["start"], item["end"]))
        for start, end in row["spans"]:
            total += 1
            found += all(index in masked for index in range(start, end))
    return found / total if total else 0.0


def package_checkpoint(model_dir: Path) -> str:
    files = sorted(path for path in model_dir.rglob("*") if path.is_file())
    if not files or not (model_dir / "config.json").is_file():
        raise RuntimeError("The trainer did not save a model checkpoint")
    archive_path = Path("model.tar.gz")
    with tarfile.open(archive_path, "w:gz", compresslevel=1) as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(model_dir), recursive=False)
    digest = hashlib.sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(params: Path, revision: str) -> None:
    settings = yaml.safe_load(params.read_bytes())["training"]
    source = (settings["dataset"], settings["dataset_revision"], "train")
    with secretmanager.SecretManagerServiceClient() as client:
        password = client.access_secret_version(request={"name": PASSWORD_RESOURCE})
    os.environ["MLFLOW_TRACKING_PASSWORD"] = password.payload.data.decode("utf-8")

    with tracked_run("training", [], params, revision, upstream_source=source) as run:
        rows = load_rows(settings)
        random.Random(settings["seed"]).shuffle(rows)
        test_rows = settings["holdout_rows"]
        if not 0 < test_rows < len(rows):
            raise ValueError("The sampled data must hold training and validation rows")
        test, train = rows[:test_rows], rows[test_rows:]
        digest = hashlib.sha256(
            json.dumps(rows, sort_keys=True, ensure_ascii=True).encode()
        ).hexdigest()
        mlflow.set_tag("source.sample_sha256", digest, synchronous=True)

        model_path = snapshot_download(settings["base_model"], revision=settings["model_revision"])
        model = AutoExtractor.from_pretrained(model_path).to("cuda")
        before = recall(model, test)
        examples = [InputExample(text=row["text"], entities=row["entities"]) for row in train]
        config = TrainingConfig(
            output_dir="checkpoint",
            seed=settings["seed"],
            num_epochs=settings["epochs"],
            batch_size=settings["batch_size"],
            fp16=True,
            eval_strategy="no",
            save_best=False,
            num_workers=2,
        )
        start = time.monotonic()
        ExtractorTrainer(model, config).train(train_data=examples)
        seconds = time.monotonic() - start
        metrics = {
            "train_rows": len(train),
            "validation_rows": len(test),
            "recall_before": before,
            "recall_after": recall(model, test),
            "train_seconds": seconds,
        }
        model_hash = package_checkpoint(Path(config.output_dir) / "final")
        mlflow.log_metrics(metrics, synchronous=True)
        mlflow.log_param("model_sha256", model_hash, synchronous=True)
        metadata = {"git_sha": revision, "run_id": run.info.run_id, "model_sha256": model_hash}

    Path("training.json").write_text(json.dumps(metadata) + "\n", encoding="utf-8")
    print("SUMMARY", json.dumps(metrics))


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
