"""A smaller test set with the same number of texts in each language.

Usage:
    uv run python -m pii_anonymizer.subset data/test/t1-openpii-1m.jsonl \\
        data/test/t1-openpii-1m-200.jsonl

The app's engine runs a 4B model, so it is measured on 200 texts per test set (50 per
language) instead of 1,000. Every detector is scored on the same subsets, so the numbers
compare. See docs/baselines.md.
"""

import argparse
import json
import random
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from pii_anonymizer.public_data import write_jsonl

SEED = 0
PER_LANGUAGE = 50


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stratified(records: Sequence[dict], per_language: int = PER_LANGUAGE, seed: int = SEED):
    """`per_language` records of each language (`lang` key), drawn with a fixed seed.

    The records keep their order in the file. Raises ValueError if a language has fewer.
    """
    rng = random.Random(seed)
    by_lang = defaultdict(list)
    for index, record in enumerate(records):
        by_lang[record["lang"]].append(index)
    picked = set()
    for lang in sorted(by_lang):
        indexes = by_lang[lang]
        if len(indexes) < per_language:
            raise ValueError(f"only {len(indexes)} texts in {lang!r}, {per_language} asked")
        picked.update(rng.sample(indexes, per_language))
    return [records[i] for i in sorted(picked)]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write a subset with as many texts per language.")
    parser.add_argument("dataset", type=Path, help="test set in JSONL")
    parser.add_argument("out", type=Path, help="the subset, in JSONL")
    parser.add_argument("--per-language", type=int, default=PER_LANGUAGE)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    subset = stratified(read_jsonl(args.dataset), args.per_language, args.seed)
    write_jsonl(subset, args.out)
    print(f"{args.out}: {len(subset)} texts, {args.per_language} per language")


if __name__ == "__main__":
    main()
