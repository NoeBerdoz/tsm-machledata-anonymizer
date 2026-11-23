"""The training subset of the teacher v1: 50,000 seeded rows of the public train splits.

Usage:
    uv run --group baselines python -m pii_anonymizer.teacher_data data/train/teacher-v1.jsonl \\
        --exclude data/test/t1-openpii-1m.jsonl --exclude data/test/t1-open-pii-500k.jsonl \\
        --exclude data/test/gretel-test-iban.jsonl --exclude data/test/t1-swiss.jsonl

- 10,000 rows per language (FR, DE, IT, EN) of the OpenPII-1M train split,
- 2,500 documents per language of the Gretel train split (all of them if a language has
  fewer),
- then Swiss values in a seeded share of the rows (swiss_training.py, issue #42).

Only train splits are read. Every row must have a label of the teacher (teacher_labels.py)
and must not be a test row: the script stops otherwise. See docs/teacher.md.
"""

import argparse
import json
import os
import random
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from pii_anonymizer.public_data import (
    COLUMNS,
    GRETEL_COLUMNS,
    GRETEL_ID,
    GRETEL_LANGUAGES,
    LANGUAGES,
    PARQUET_REVISIONS,
    convert_gretel_row,
    convert_row,
    sample_rows,
    write_jsonl,
)
from pii_anonymizer.swiss import read_jsonl
from pii_anonymizer.swiss_training import check_disjoint, inject_share
from pii_anonymizer.teacher_labels import gliner_label

OPENPII_ID = "ai4privacy/pii-masking-openpii-1m"
OPENPII_NAME = "openpii-1m-train"
GRETEL_NAME = "gretel-train"
OPENPII_PER_LANGUAGE = 10_000
GRETEL_PER_LANGUAGE = 2_500
# The test samples use seed 42 (public_data.py) and the Swiss test set seed 0.
SEED = 1


def sample_gretel_train(
    rows: Iterable[Mapping], per_language: int = GRETEL_PER_LANGUAGE, seed: int = SEED
) -> list[Mapping]:
    """Up to `per_language` Gretel rows of each of our languages, a fixed sample.

    The rows are sorted by index first, so the sample does not depend on the file order.
    """
    by_language: dict[str, list[Mapping]] = {lang: [] for lang in GRETEL_LANGUAGES}
    for row in rows:
        if row["language"] in by_language:
            by_language[row["language"]].append(row)
    rng = random.Random(seed)
    sample = []
    for lang in GRETEL_LANGUAGES:
        candidates = sorted(by_language[lang], key=lambda r: int(r["index"]))
        sample.extend(rng.sample(candidates, min(per_language, len(candidates))))
    return sample


def convert(rows: Iterable[Mapping], converter, source: str) -> tuple[list[dict], int]:
    records, dropped = [], 0
    for row in rows:
        record, n = converter(row, source)
        records.append(record)
        dropped += n
    return records, dropped


def check_labels(records: Iterable[Mapping]) -> None:
    """Raise ValueError if an entity has a label that the teacher does not know."""
    unknown = Counter()
    for record in records:
        for entity in record["entities"]:
            try:
                gliner_label(entity["label"])
            except KeyError:
                unknown[entity["label"]] += 1
    if unknown:
        raise ValueError(f"labels without a teacher label: {dict(unknown)}")


def build(
    openpii_rows: Iterable[Mapping],
    gretel_rows: Iterable[Mapping],
    test_sets: Iterable[Iterable[Mapping]],
    seed: int = SEED,
) -> list[dict]:
    """The training records: sampled, converted, checked, with Swiss values in a share."""
    openpii, dropped_openpii = convert(
        sample_rows(openpii_rows, OPENPII_PER_LANGUAGE, seed), convert_row, OPENPII_NAME
    )
    gretel, dropped_gretel = convert(
        sample_gretel_train(gretel_rows, GRETEL_PER_LANGUAGE, seed),
        convert_gretel_row,
        GRETEL_NAME,
    )
    records = openpii + gretel
    print(f"{len(openpii)} OpenPII-1M rows ({dropped_openpii} entities dropped)")
    print(f"{len(gretel)} Gretel documents ({dropped_gretel} entities dropped)")
    check_labels(records)
    check_disjoint(records, test_sets)
    # The Swiss values use their own training seed, outside those of the Swiss test sets.
    return inject_share(records)


def load_train(dataset_id: str, columns: Sequence[str], filters=None):
    """The train split of a pinned Hub dataset, only the given columns."""
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from datasets import load_dataset

    return load_dataset(
        dataset_id,
        revision=PARQUET_REVISIONS[dataset_id],
        data_files={"train": "default/train/*.parquet"},
        split="train",
        columns=list(columns),
        filters=filters,
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the training subset of the teacher v1.")
    parser.add_argument("out", type=Path, help="the training JSONL file")
    parser.add_argument(
        "--exclude",
        type=Path,
        action="append",
        required=True,
        help="a test file whose rows must not be in training (repeat for each test file)",
    )
    args = parser.parse_args(argv)

    test_sets = [read_jsonl(path) for path in args.exclude]
    openpii_rows = load_train(OPENPII_ID, COLUMNS, [("language", "in", list(LANGUAGES))])
    gretel_rows = load_train(GRETEL_ID, GRETEL_COLUMNS)
    records = build(openpii_rows, gretel_rows, test_sets)
    write_jsonl(records, args.out)

    per_source = Counter((r["source"], r["lang"]) for r in records)
    swiss = sum(r["id"].endswith("-ch") for r in records)
    print(f"{args.out}: {len(records)} rows, {swiss} with Swiss values")
    for (source, lang), n in sorted(per_source.items()):
        print(f"  {source} {lang}: {n}")
    print(json.dumps({"rows": len(records), "swiss_rows": swiss}))


if __name__ == "__main__":
    main()
