"""Seeded samples of public test splits, in our test set format.

Usage:
    uv run python -m pii_anonymizer.public_data data/test/

Writes into the given folder:

- t1-openpii-1m.jsonl and t1-open-pii-500k.jsonl: 250 rows per language (FR, DE, IT, EN) of
  each validation split, so 1,000 rows per file.
- gretel-test-iban.jsonl: up to 100 documents per language of the Gretel test split that
  hold an `iban` or `bban` entity. The Swiss test set starts from them
  (docs/swiss-identifiers.md).

The labels stay as the dataset writes them. Needs the `baselines` dependency group. See
docs/baselines.md.
"""

import argparse
import json
import os
import random
from collections.abc import Iterable, Mapping
from pathlib import Path

SEED = 42
ROWS_PER_LANGUAGE = 250
LANGUAGES = ("fr", "de", "it", "en")

# Output name -> Hugging Face dataset id. Both have the same columns.
SOURCES = {
    "t1-openpii-1m": "ai4privacy/pii-masking-openpii-1m",
    "t1-open-pii-500k": "ai4privacy/open-pii-masking-500k-ai4privacy",
}
# The Hub converts every dataset to parquet on its `refs/convert/parquet` branch, so we read
# only the columns we need instead of the full JSONL files (the OpenPII-1M validation file
# alone is 920 MB). The Hub rewrites that branch when a dataset changes, so we pin the commit
# we sampled from. If a pinned commit disappears, the download fails instead of silently
# giving other rows, and the `dataset_sha256` column of results.csv shows any change.
PARQUET_REVISIONS = {
    "ai4privacy/pii-masking-openpii-1m": "c064392b9d3ddccc3a2997d41630631f9be465f0",
    "ai4privacy/open-pii-masking-500k-ai4privacy": "1b151200bdc469f9a70f4efa25c57b28b50edeb2",
    "gretelai/synthetic_pii_finance_multilingual": "0d815fcd7f2077abb724dbb5e378ad5e8bf1acb6",
}
COLUMNS = ["uid", "source_text", "privacy_mask", "language", "region"]

# Gretel: only its test split, because its train split is a candidate training set
# (option A in docs/datasets.md).
GRETEL_ID = "gretelai/synthetic_pii_finance_multilingual"
GRETEL_NAME = "gretel-test-iban"
GRETEL_ROWS_PER_LANGUAGE = 100
GRETEL_LABELS = ("iban", "bban")
GRETEL_COLUMNS = ["index", "language", "generated_text", "pii_spans"]
# Gretel writes the language in full ("France" is its spelling for French).
GRETEL_LANGUAGES = {"France": "fr", "German": "de", "Italian": "it", "English": "en"}


def convert_row(row: Mapping, source: str) -> tuple[dict, int]:
    """One ai4privacy row -> one test set record, and the number of entities dropped.

    An entity is dropped when its offsets do not point to its value (`text[start:end]` is not
    the `value` field), because the evaluation would then score the wrong characters.
    """
    text = row["source_text"]
    entities = []
    dropped = 0
    for mask in row["privacy_mask"]:
        start, end = mask["start"], mask["end"]
        if not 0 <= start < end <= len(text) or text[start:end] != mask["value"]:
            dropped += 1
            continue
        entities.append({"start": start, "end": end, "label": mask["label"]})
    record = {
        "id": f"{source}-{row['uid']}",
        "text": text,
        "entities": entities,
        "lang": row["language"],
        "source": source,
        "region": row["region"],
    }
    return record, dropped


def sample_rows(
    rows: Iterable[Mapping], per_language: int = ROWS_PER_LANGUAGE, seed: int = SEED
) -> list[Mapping]:
    """A fixed random sample of `per_language` rows for each language in LANGUAGES.

    The rows are sorted by uid first, so the sample does not depend on the file order.
    """
    by_language: dict[str, list[Mapping]] = {lang: [] for lang in LANGUAGES}
    for row in rows:
        if row["language"] in by_language:
            by_language[row["language"]].append(row)
    rng = random.Random(seed)
    sample = []
    for lang in LANGUAGES:
        candidates = sorted(by_language[lang], key=lambda r: int(r["uid"]))
        if len(candidates) < per_language:
            raise ValueError(f"only {len(candidates)} rows in {lang}, need {per_language}")
        sample.extend(rng.sample(candidates, per_language))
    return sample


def write_jsonl(records: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_validation(dataset_id: str) -> Iterable[Mapping]:
    """The validation split of a Hub dataset, only our columns and languages."""
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from datasets import load_dataset

    return load_dataset(
        dataset_id,
        revision=PARQUET_REVISIONS[dataset_id],
        data_files={"validation": "default/validation/*.parquet"},
        split="validation",
        columns=COLUMNS,
        filters=[("language", "in", list(LANGUAGES))],
    )


def convert_gretel_row(row: Mapping, source: str = GRETEL_NAME) -> tuple[dict, int]:
    """One Gretel row -> one test set record, and the number of entities dropped.

    Gretel gives offsets without the value, so the check is weaker than for ai4privacy: an
    entity is dropped when its span does not fit the text, is empty, or starts or ends with
    whitespace.
    """
    text = row["generated_text"]
    entities = []
    dropped = 0
    for span in json.loads(row["pii_spans"]):
        start, end = span["start"], span["end"]
        value = text[start:end] if 0 <= start < end <= len(text) else ""
        if not value or value != value.strip():
            dropped += 1
            continue
        entities.append({"start": start, "end": end, "label": span["label"]})
    record = {
        "id": f"{source}-{row['index']}",
        "text": text,
        "entities": entities,
        "lang": GRETEL_LANGUAGES[row["language"]],
        "source": source,
    }
    return record, dropped


def has_bank_account(row: Mapping) -> bool:
    """True if the Gretel row holds an `iban` or `bban` entity."""
    return any(span["label"] in GRETEL_LABELS for span in json.loads(row["pii_spans"]))


def sample_gretel(
    rows: Iterable[Mapping], per_language: int = GRETEL_ROWS_PER_LANGUAGE, seed: int = SEED
) -> list[Mapping]:
    """Up to `per_language` rows with a bank account for each language, a fixed sample.

    The rows are sorted by index first, so the sample does not depend on the file order.
    A language with fewer rows gives all of them.
    """
    by_language: dict[str, list[Mapping]] = {lang: [] for lang in GRETEL_LANGUAGES}
    for row in rows:
        if row["language"] in by_language and has_bank_account(row):
            by_language[row["language"]].append(row)
    rng = random.Random(seed)
    sample = []
    for lang in GRETEL_LANGUAGES:
        candidates = sorted(by_language[lang], key=lambda r: int(r["index"]))
        sample.extend(rng.sample(candidates, min(per_language, len(candidates))))
    return sample


def load_gretel_test() -> Iterable[Mapping]:
    """The test split of Gretel, only our columns."""
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from datasets import load_dataset

    return load_dataset(
        GRETEL_ID,
        revision=PARQUET_REVISIONS[GRETEL_ID],
        data_files={"test": "default/test/*.parquet"},
        split="test",
        columns=GRETEL_COLUMNS,
    )


def build(out_dir: Path) -> None:
    for name, dataset_id in SOURCES.items():
        rows = sample_rows(load_validation(dataset_id))
        records = []
        n_entities = n_dropped = 0
        for row in rows:
            record, dropped = convert_row(row, name)
            records.append(record)
            n_entities += len(record["entities"]) + dropped
            n_dropped += dropped
        path = out_dir / f"{name}.jsonl"
        write_jsonl(records, path)
        print(
            f"{path}: {len(records)} texts, {n_entities} entities, "
            f"{n_dropped} dropped because text[start:end] != value"
        )

    records = []
    n_entities = n_dropped = 0
    for row in sample_gretel(load_gretel_test()):
        record, dropped = convert_gretel_row(row)
        records.append(record)
        n_entities += len(record["entities"]) + dropped
        n_dropped += dropped
    path = out_dir / f"{GRETEL_NAME}.jsonl"
    write_jsonl(records, path)
    print(
        f"{path}: {len(records)} texts, {n_entities} entities, "
        f"{n_dropped} dropped because the span is empty, does not fit or has outer spaces"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the public test samples.")
    parser.add_argument("out_dir", type=Path, help="folder for the JSONL files, usually data/test/")
    build(parser.parse_args(argv).out_dir)


if __name__ == "__main__":
    main()
