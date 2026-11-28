"""Fine-tune GLiNER2-PII into the teacher v1 (#46). Runs inside the Agent Platform job.

    python train.py params.yaml <git sha> <outputs dir> ci|trial|full

The job copies this file next to tracking.py, teacher_labels.py, params.yaml and the training
subset with its DVC pointer. It writes into the outputs directory:

- epoch-1.tar.gz as soon as the first epoch ends, so a cap during the second epoch keeps it,
- model.tar.gz, the model after the last epoch,
- training.json, the metrics, the hashes and the MLflow run id.
"""

import hashlib
import json
import os
import random
import shutil
import sys
import tarfile
import time
from pathlib import Path

import mlflow
import torch
import yaml
from gliner2 import AutoExtractor, InputExample
from gliner2.training.trainer import ExtractorTrainer, TrainingConfig
from google.cloud import secretmanager
from huggingface_hub import snapshot_download
from teacher_labels import TARGETS, to_example
from tracking import tracked_run

PASSWORD_RESOURCE = "projects/tsmmachledata-projet/secrets/mlflow-training-password/versions/latest"
DATA = Path("teacher-v1.jsonl")
POINTER = Path("teacher-v1.jsonl.dvc")


def settings_for(params: dict, mode: str) -> dict:
    settings = dict(params["training"])
    settings.update(settings.pop("modes")[mode])
    return settings


def read_rows() -> list[dict]:
    """The training subset, after checking it against the md5 of its DVC pointer."""
    expected = yaml.safe_load(POINTER.read_bytes())["outs"][0]["md5"]
    digest = hashlib.md5(DATA.read_bytes(), usedforsecurity=False).hexdigest()
    if digest != expected:
        raise RuntimeError(f"{DATA} has md5 {digest}, its DVC pointer says {expected}")
    with DATA.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def split(rows: list[dict], settings: dict) -> tuple[list[dict], list[dict]]:
    """The held-out rows and the training rows, drawn with the seed."""
    rng = random.Random(settings["seed"])
    if settings["rows"] is not None:
        rows = rng.sample(rows, settings["rows"] + settings["holdout_rows"])
    else:
        rows = list(rows)
        rng.shuffle(rows)
    holdout = settings["holdout_rows"]
    return rows[:holdout], rows[holdout:]


def recall(model, rows: list[dict]) -> float:
    """The share of gold entities whose characters are all masked, as in smart-goals.md."""
    if not rows:
        return float("nan")
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
        for entity in row["entities"]:
            value = row["text"][entity["start"] : entity["end"]]
            start = entity["start"] + len(value) - len(value.lstrip())
            end = entity["end"] - (len(value) - len(value.rstrip()))
            total += 1
            found += all(index in masked for index in range(start, end))
    return found / total if total else float("nan")


def package(model_dir: Path, archive: Path) -> str:
    """Write the checkpoint folder as a .tar.gz and return its SHA-256."""
    if not (model_dir / "config.json").is_file():
        raise RuntimeError(f"No model checkpoint in {model_dir}")
    (model_dir / "labels.json").write_text(json.dumps(TARGETS) + "\n", encoding="utf-8")
    files = sorted(path for path in model_dir.rglob("*") if path.is_file())
    local = Path(archive.name)
    with tarfile.open(local, "w:gz", compresslevel=1) as handle:
        for path in files:
            handle.add(path, arcname=path.relative_to(model_dir), recursive=False)
    with local.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local, archive)
    return digest


def out_of_memory(error: BaseException) -> bool:
    # Inside TorchScript, a CUDA out-of-memory error is a plain RuntimeError.
    return isinstance(error, torch.cuda.OutOfMemoryError) or "out of memory" in str(error)


class Trainer(ExtractorTrainer):
    """Copies the first-epoch checkpoint to the outputs as soon as it is saved.

    It also counts the batches skipped for lack of GPU memory. GLiNER2 skips an
    OutOfMemoryError by itself; skip_step_errors lets it skip the RuntimeError of
    TorchScript too, and any error that is not out of memory still stops the run.
    """

    outputs: Path
    epoch_1: dict | None = None
    skipped_batches: int = 0

    def _record_failed_batch(self, batch, *, data_loader_step: int, error: BaseException):
        super()._record_failed_batch(batch, data_loader_step=data_loader_step, error=error)
        if not out_of_memory(error):
            raise error
        self.skipped_batches += 1
        torch.cuda.empty_cache()

    def _save_checkpoint(self, name: str):
        super()._save_checkpoint(name)
        if name == "checkpoint-epoch-1" and self.is_main_process:
            digest = package(self.output_dir / name, self.outputs / "epoch-1.tar.gz")
            self.epoch_1 = {"sha256": digest, "step": self.global_step}
            (self.outputs / "epoch-1.json").write_text(json.dumps(self.epoch_1) + "\n")
            print("EPOCH-1", json.dumps(self.epoch_1), flush=True)


def main(params_path: Path, revision: str, outputs: Path, mode: str) -> None:
    if mode not in ("ci", "trial", "full"):
        raise ValueError("The mode is ci, trial or full")
    params = yaml.safe_load(params_path.read_bytes())
    settings = settings_for(params, mode)
    with secretmanager.SecretManagerServiceClient() as client:
        password = client.access_secret_version(request={"name": PASSWORD_RESOURCE})
    os.environ["MLFLOW_TRACKING_PASSWORD"] = password.payload.data.decode("utf-8")
    outputs.mkdir(parents=True, exist_ok=True)

    with tracked_run("training", [POINTER], params_path, revision) as run:
        mlflow.set_tags({"model": "teacher-v1", "mode": mode}, synchronous=True)
        all_rows = read_rows()
        holdout, train = split(all_rows, settings)
        examples = [
            InputExample(text=row["text"], entities=to_example(row["text"], row["entities"]))
            for row in train
        ]

        model_path = snapshot_download(settings["base_model"], revision=settings["model_revision"])
        model = AutoExtractor.from_pretrained(model_path).to("cuda")
        before = recall(model, holdout)
        config = TrainingConfig(
            output_dir="checkpoint",
            seed=settings["seed"],
            num_epochs=settings["epochs"],
            batch_size=settings["batch_size"],
            gradient_accumulation_steps=settings["gradient_accumulation_steps"],
            fp16=True,
            eval_strategy="epoch",
            save_best=False,
            save_total_limit=settings["epochs"] + 2,
            num_workers=2,
            skip_step_errors=True,
        )
        trainer = Trainer(model, config)
        trainer.outputs = outputs
        start = time.monotonic()
        summary = trainer.train(train_data=examples)
        seconds = time.monotonic() - start

        train_chars = sum(len(r["text"]) for r in train)
        chars_per_second = train_chars * settings["epochs"] / seconds
        all_chars = sum(len(r["text"]) for r in all_rows)
        metrics = {
            "train_rows": len(train),
            "holdout_rows": len(holdout),
            "train_chars": train_chars,
            "train_seconds": seconds,
            "rows_per_second": len(train) * settings["epochs"] / seconds,
            "chars_per_second": chars_per_second,
            # The training time of the full subset at this speed, without setup.
            "full_run_hours_estimate": all_chars * settings["epochs"] / chars_per_second / 3600,
            "total_steps": summary["total_steps"],
            "gpu_max_memory_gb": torch.cuda.max_memory_allocated() / 1e9,
            "skipped_batches": trainer.skipped_batches,
        }
        if holdout:
            metrics["recall_before"] = before
            metrics["recall_after"] = recall(model, holdout)
        model_hash = package(Path(config.output_dir) / "final", outputs / "model.tar.gz")
        mlflow.log_metrics(metrics, synchronous=True)
        mlflow.log_param("model_sha256", model_hash, synchronous=True)
        if trainer.epoch_1:
            mlflow.log_param("epoch_1_sha256", trainer.epoch_1["sha256"], synchronous=True)
        metadata = {
            "git_sha": revision,
            "run_id": run.info.run_id,
            "mode": mode,
            "model_sha256": model_hash,
            "epoch_1": trainer.epoch_1,
            "metrics": metrics,
        }

    (outputs / "training.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("SUMMARY", json.dumps(metrics), flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4])
