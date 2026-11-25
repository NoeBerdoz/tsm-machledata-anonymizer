"""Draw the latency sample: 30 snippet IDs of T2-dev, spread across its sources.

Usage:
    uv run python -m pii_anonymizer.latency_sample data/test/t2-dev.jsonl \\
        src/pii_anonymizer/latency_ids.txt

Each source gets its share of the 30 IDs (largest remainder), drawn with a fixed seed.
See docs/benchmark-protocol.md.
"""

import argparse
import random
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from pii_anonymizer.subset import SEED, read_jsonl

LATENCY_TEXTS = 30


def latency_ids(
    records: Sequence[dict], n: int = LATENCY_TEXTS, seed: int = SEED, by: str = "source"
) -> list[str]:
    """The IDs of `n` records, proportional to the groups of `by`, in file order."""
    if len(records) < n:
        raise ValueError(f"only {len(records)} texts, {n} asked")
    groups = defaultdict(list)
    for index, record in enumerate(records):
        groups[record.get(by)].append(index)
    keys = sorted(groups, key=str)
    quotas = {k: len(groups[k]) * n // len(records) for k in keys}
    # Largest remainder; sorted() is stable, so ties go to the first key by name.
    by_remainder = sorted(keys, key=lambda k: -(len(groups[k]) * n % len(records)))
    for k in by_remainder[: n - sum(quotas.values())]:
        quotas[k] += 1
    rng = random.Random(seed)
    picked = sorted(i for k in keys for i in rng.sample(groups[k], quotas[k]))
    return [records[i]["id"] for i in picked]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write the latency sample of a test set.")
    parser.add_argument("dataset", type=Path, help="test set in JSONL, usually T2-dev")
    parser.add_argument("out", type=Path, help="the ID file, usually latency_ids.txt")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    ids = latency_ids(read_jsonl(args.dataset), seed=args.seed)
    header = (
        f"# Latency sample: {len(ids)} snippets of {args.dataset.name}, seed {args.seed},\n"
        "# proportional to each source. Written by pii_anonymizer.latency_sample.\n"
    )
    args.out.write_text(header + "\n".join(ids) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(ids)} IDs")


if __name__ == "__main__":
    main()
