"""Put valid fake Swiss identifiers into a seeded share of the training rows.

Usage:
    uv run python -m pii_anonymizer.swiss_training <train.jsonl> [<train2.jsonl> ...] \\
        <out.jsonl> --exclude data/test/t1-openpii-1m.jsonl --exclude ... [--share 0.2]

A wrapper around `swiss.py`, which writes the Swiss test set. For training, the rows are all
kept. Among the rows with an entity of a Swiss kind (`SOCIALNUM`, `TELEPHONENUM`,
`phone_number`, `iban`, `bban`), a seeded share receives Swiss values, in the same written
formats as the test set. The other rows keep their foreign values, because the app must mask
those too. See docs/swiss-identifiers.md.

The training seed differs from the test seed, and every row is checked against the given
test files: no training row may share an id or a text with a test row.
"""

import argparse
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from pii_anonymizer.swiss import KINDS, inject, read_jsonl

# The Swiss test set was written with --seed 0 (docs/swiss-identifiers.md).
TEST_SEED = 0
SEED = 1
# Share of the rows with an entity of a Swiss kind that receive Swiss values.
SHARE = 0.2
SWISS_LABELS = frozenset(KINDS.values())


def has_swiss_kind(record: Mapping) -> bool:
    return any(entity["label"] in KINDS for entity in record["entities"])


def source_id(record_id: str) -> str:
    """The id of the source row: without the `-ch` that the injection adds."""
    return record_id.removesuffix("-ch")


def inject_share(records: Iterable[Mapping], share: float = SHARE, seed: int = SEED) -> list[dict]:
    """Every record, with Swiss values in a seeded share of those of a Swiss kind.

    Each record gets its own generator, seeded from the seed and the record id, so the choice
    and the values of a row do not depend on the other rows. The prefix `train:` keeps these
    generators apart from those of the test set even for the same seed and id.
    """
    if not 0 <= share <= 1:
        raise ValueError(f"the share must be between 0 and 1, not {share}")
    if seed == TEST_SEED:
        raise ValueError(f"seed {TEST_SEED} is the seed of the Swiss test set")
    out = []
    for record in records:
        rng = random.Random(f"train:{seed}:{record['id']}")
        injected = None
        if has_swiss_kind(record) and rng.random() < share:
            injected = inject(record, rng)
        out.append(injected if injected is not None else dict(record))
    return out


def check_disjoint(train: Iterable[Mapping], test_sets: Iterable[Iterable[Mapping]]) -> None:
    """Raise ValueError if a training row shares a source id or a text with a test row.

    The test files to give are the source rows (the T1 samples, `gretel-test-iban.jsonl`,
    T2) and the Swiss test set: its texts are rewritten, but its ids still name its sources.
    """
    test_ids: set[str] = set()
    test_texts: set[str] = set()
    for records in test_sets:
        for record in records:
            test_ids.add(source_id(record["id"]))
            test_texts.add(record["text"])
    shared = [
        record["id"]
        for record in train
        if source_id(record["id"]) in test_ids or record["text"] in test_texts
    ]
    if shared:
        raise ValueError(f"{len(shared)} training rows are also test rows, such as {shared[:3]}")


def counts(records: Sequence[Mapping]) -> dict[str, dict[str, int]]:
    """Per language: the rows, the rows with Swiss values, and the Swiss values per label."""
    per_lang: dict[str, dict[str, int]] = {}
    for record in records:
        c = per_lang.setdefault(record.get("lang") or "?", {"rows": 0, "swiss_rows": 0})
        c["rows"] += 1
        labels = [e["label"] for e in record["entities"] if e["label"] in SWISS_LABELS]
        if record["id"].endswith("-ch"):
            c["swiss_rows"] += 1
        for label in labels:
            c[label] = c.get(label, 0) + 1
    return per_lang


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Put Swiss values into a share of training rows.")
    parser.add_argument("paths", nargs="+", type=Path, help="training JSONL files, then the output")
    parser.add_argument("--share", type=float, default=SHARE, help="share of eligible rows")
    parser.add_argument("--seed", type=int, default=SEED, help=f"not {TEST_SEED}, the test seed")
    parser.add_argument(
        "--exclude",
        type=Path,
        action="append",
        required=True,
        help="a test file whose rows must not be in training (repeat for each test file)",
    )
    args = parser.parse_args(argv)
    if len(args.paths) < 2:
        parser.error("give at least one input file and the output file")
    *inputs, output = args.paths

    records = [record for path in inputs for record in read_jsonl(path)]
    check_disjoint(records, (read_jsonl(path) for path in args.exclude))
    out = inject_share(records, args.share, args.seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for record in out:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    eligible = sum(has_swiss_kind(record) for record in records)
    swiss = sum(record["id"].endswith("-ch") for record in out)
    print(f"{output}: {len(out)} rows, {eligible} of a Swiss kind, {swiss} with Swiss values")
    for lang, c in sorted(counts(out).items()):
        print(
            f"  {lang}: {c['rows']} rows, {c['swiss_rows']} Swiss, AVS {c.get('AVS', 0)}, "
            f"PHONE {c.get('PHONE', 0)}, IBAN {c.get('IBAN', 0)}"
        )


if __name__ == "__main__":
    main()
