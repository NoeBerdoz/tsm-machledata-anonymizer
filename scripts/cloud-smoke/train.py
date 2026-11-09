"""Tiny fine-tuning of GLiNER2-PII, only to check that training works on Google Cloud (#7).

Runs as an Agent Platform custom job (see docs/cloud-training.md). It prints the scores
before and after training, and saves the model to Cloud Storage.
"""

import json
import random
import sys
import time

import torch
from datasets import load_dataset
from gliner2 import AutoExtractor, InputExample
from gliner2.training.trainer import ExtractorTrainer, TrainingConfig

MODEL = "fastino/gliner2-privacy-filter-PII-multi"
DATASET = "ai4privacy/pii-masking-openpii-1m"  # train split only: validation is T1
N_ROWS = 1000
LANGUAGES = {"en", "fr", "de", "it"}
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "output"

# ai4privacy label -> GLiNER2-PII label (draft, for this test only)
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


def load_rows():
    """About 1,000 rows: text, entities for GLiNER2, and gold spans for the scores."""
    stream = load_dataset(DATASET, split="train", streaming=True)
    stream = stream.filter(lambda r: r.get("language") in LANGUAGES)
    stream = stream.shuffle(seed=42, buffer_size=10_000)
    rows = []
    for row in stream:
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
        if len(rows) >= N_ROWS:
            return rows
    return rows


def recall(model, rows):
    """Share of gold entities whose characters are all masked (as in docs/smart-goals.md)."""
    model.eval()
    if hasattr(model, "processor"):
        model.processor.change_mode(is_training=False)
    with torch.no_grad():
        results = model.batch_extract_entities(
            [r["text"] for r in rows], TARGETS, batch_size=16, include_spans=True
        )
    found = total = 0
    for row, result in zip(rows, results, strict=True):
        masked = set()
        for items in result["entities"].values():
            for item in items:
                masked.update(range(item["start"], item["end"]))
        for start, end in row["spans"]:
            total += 1
            found += all(i in masked for i in range(start, end))
    return found / total if total else 0.0


def main():
    start = time.time()
    print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")

    rows = load_rows()
    random.Random(42).shuffle(rows)
    test, train = rows[:100], rows[100:]
    print(f"Data: {len(train)} train rows, {len(test)} test rows")

    model = AutoExtractor.from_pretrained(MODEL).to("cuda")
    before = recall(model, test)
    print(f"Recall before training: {before:.3f}")

    examples = [InputExample(text=r["text"], entities=r["entities"]) for r in train]
    config = TrainingConfig(
        output_dir=OUTPUT,
        num_epochs=2,
        batch_size=8,
        fp16=True,  # the T4 has no bf16
        eval_strategy="no",
        save_best=False,
        num_workers=2,
    )
    train_start = time.time()
    ExtractorTrainer(model, config).train(train_data=examples)
    train_minutes = (time.time() - train_start) / 60

    after = recall(model, test)
    print(f"Recall after training: {after:.3f}")

    summary = {
        "train_rows": len(train),
        "test_rows": len(test),
        "recall_before": round(before, 3),
        "recall_after": round(after, 3),
        "train_minutes": round(train_minutes, 1),
        "total_minutes": round((time.time() - start) / 60, 1),
        "gpu_max_memory_gb": round(torch.cuda.max_memory_allocated() / 1e9, 1),
    }
    print("SUMMARY", json.dumps(summary))
    with open(f"{OUTPUT}/summary.json", "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
