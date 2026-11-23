"""Split T2 into dev and final by group, and draw the snippets for the second reader.

Usage:
    uv run python -m pii_anonymizer.t2_split data/test/t2.jsonl \\
        data/test/t2-dev.jsonl data/test/t2-final.jsonl
    uv run python -m pii_anonymizer.t2_split data/test/t2.jsonl --review

Whole groups go to one side, half of the snippets to each, stratified by `source`, `kind`
and `lang`, with seed 42. See docs/test-set-decision.md.
"""

import argparse
import random
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path

from pii_anonymizer.public_data import write_jsonl
from pii_anonymizer.swiss import read_jsonl
from pii_anonymizer.t2_holdout import paths_alias

SEED = 42
REVIEW = 24
STRATA = ("source", "kind", "lang")


def split(records: Sequence[dict], seed: int = SEED) -> tuple[list[dict], list[dict]]:
    """(dev, final), each in the order of the file. A group never sits on both sides."""
    groups = defaultdict(list)
    for record in records:
        groups[record["group"]].append(record)
    strata = defaultdict(list)
    for name, rows in groups.items():
        # The variants of a template share their source, kind and language, so one snippet
        # stands for the group: the smallest id, so the file order does not matter.
        first = min(rows, key=lambda r: r["id"])
        strata[tuple(first[key] for key in STRATA)].append(name)

    rng = random.Random(seed)
    sizes = [0, 0]
    dev_groups = set()
    for stratum in sorted(strata):
        names = sorted(strata[stratum])
        rng.shuffle(names)
        here = [0, 0]
        for name in names:
            # The side with fewer snippets in this stratum, then overall, so odd strata
            # do not all lean the same way.
            side = min((0, 1), key=lambda s: (here[s], sizes[s]))
            here[side] += len(groups[name])
            sizes[side] += len(groups[name])
            if side == 0:
                dev_groups.add(name)
    dev = [r for r in records if r["group"] in dev_groups]
    final = [r for r in records if r["group"] not in dev_groups]
    return dev, final


def review_sample(records: Sequence[dict], n: int = REVIEW, seed: int = SEED) -> list[str]:
    """`n` units for the second reader: a realistic snippet's id, or a template's group."""
    units = sorted({r["id"] if r["kind"] == "realistic" else r["group"] for r in records})
    return sorted(random.Random(seed).sample(units, n))


def mix(dev: Sequence[dict], final: Sequence[dict]) -> str:
    """A Markdown table of the snippets per source, kind and language on each side."""
    lines = ["| | dev | final |", "|---|---|---|"]
    for key in STRATA:
        counts = Counter(r[key] for r in dev), Counter(r[key] for r in final)
        for value in sorted(counts[0].keys() | counts[1].keys()):
            lines.append(f"| {key} = {value} | {counts[0][value]} | {counts[1][value]} |")
    lines.append(f"| **total** | {len(dev)} | {len(final)} |")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("t2", type=Path, help="all T2 snippets, JSONL")
    parser.add_argument("dev", type=Path, nargs="?", help="output t2-dev.jsonl")
    parser.add_argument("final", type=Path, nargs="?", help="output t2-final.jsonl")
    parser.add_argument("--review", action="store_true", help="print the units to re-check")
    args = parser.parse_args(argv)

    records = read_jsonl(args.t2)
    if args.review:
        print("\n".join(review_sample(records)))
        return
    if args.dev is None or args.final is None:
        parser.error("give the dev and final outputs, or --review")
    for out in (args.dev, args.final):
        if paths_alias(out, args.t2):
            parser.error(f"output aliases input: {out}")
    if paths_alias(args.dev, args.final):
        parser.error("dev and final must be different files")

    dev, final = split(records)
    write_jsonl(dev, args.dev)
    write_jsonl(final, args.final)
    print(mix(dev, final))


if __name__ == "__main__":
    main()
