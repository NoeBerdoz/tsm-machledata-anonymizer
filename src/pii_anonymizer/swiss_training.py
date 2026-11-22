"""Put valid fake Swiss identifiers into a seeded share of the training rows.

Usage:
    uv run python -m pii_anonymizer.swiss_training <train.jsonl> [<train2.jsonl> ...] \\
        <out.jsonl> --exclude data/test/t1-openpii-1m.jsonl --exclude-manifest <manifest.json>

A wrapper around `swiss.py`, which writes the Swiss test set. For training, the rows are all
kept. Among the rows with an entity of a Swiss kind (`SOCIALNUM`, `TELEPHONENUM`,
`phone_number`, `iban`, `bban`), a seeded share receives Swiss values, in the same written
formats as the test set. The other rows keep their foreign values, because the app must mask
those too. See docs/swiss-identifiers.md.

Training uses a separate seed. Both source and emitted rows are checked against the supplied
holdouts by source id and text hash.
"""

import argparse
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from itertools import chain
from pathlib import Path

from pii_anonymizer.swiss import KINDS, inject, read_jsonl
from pii_anonymizer.t2_holdout import FINAL_FILENAME, Holdout, paths_alias

# The Swiss T1 set uses seed 0, and T2 variants use seeds 0 through 2.
TEST_SEEDS = (0, 1, 2)
SEED = 3
# Share of the rows with an entity of a Swiss kind that receive Swiss values.
SHARE = 0.2
SWISS_LABELS = frozenset(KINDS.values())


def has_swiss_kind(record: Mapping) -> bool:
    return any(entity["label"] in KINDS for entity in record["entities"])


def inject_share(records: Iterable[Mapping], share: float = SHARE, seed: int = SEED) -> list[dict]:
    """Every record, with Swiss values in a seeded share of those of a Swiss kind.

    Each record gets its own generator, seeded from the seed and the record id, so the choice
    and the values of a row do not depend on the other rows. The prefix `train:` keeps these
    generators apart from those of the test set even for the same seed and id.
    """
    if not 0 <= share <= 1:
        raise ValueError(f"the share must be between 0 and 1, not {share}")
    if seed in TEST_SEEDS:
        raise ValueError(f"seed {seed} is reserved for Swiss test sets")
    out = []
    for record in records:
        rng = random.Random(f"train:{seed}:{record['id']}")
        injected = None
        if has_swiss_kind(record) and rng.random() < share:
            injected = inject(record, rng)
        out.append(injected if injected is not None else dict(record))
    return out


def check_disjoint(train: Iterable[Mapping], test_sets: Iterable[Iterable[Mapping]]) -> None:
    """Check a set of training rows against raw test sets."""
    Holdout.from_records(chain.from_iterable(test_sets)).check_disjoint(train)


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
    parser.add_argument(
        "--seed", type=int, default=SEED, help=f"training seed (default {SEED}, reserved 0, 1, 2)"
    )
    parser.add_argument(
        "--exclude",
        type=Path,
        action="append",
        default=[],
        help="raw test JSONL such as T1 or T2-dev (repeatable)",
    )
    parser.add_argument("--exclude-manifest", type=Path, help="the frozen T2 exclusion manifest")
    args = parser.parse_args(argv)
    if len(args.paths) < 2:
        parser.error("give at least one input file and the output file")
    if not args.exclude and args.exclude_manifest is None:
        parser.error("give at least one --exclude or --exclude-manifest")
    *inputs, output = args.paths
    protected_paths = inputs + args.exclude
    if args.exclude_manifest is not None:
        protected_paths.append(args.exclude_manifest)
    if any(
        FINAL_FILENAME in (path.name, path.resolve().name) for path in [output, *protected_paths]
    ):
        parser.error("keep t2-final.jsonl on the freeze side and supply --exclude-manifest")
    for path in protected_paths:
        if paths_alias(output, path):
            parser.error(f"output aliases input: {output} and {path}")

    holdout = Holdout.from_records(record for path in args.exclude for record in read_jsonl(path))
    if args.exclude_manifest is not None:
        final = Holdout.read(args.exclude_manifest)
        holdout.source_ids.update(final.source_ids)
        holdout.text_sha256.update(final.text_sha256)
    records = [record for path in inputs for record in read_jsonl(path)]
    holdout.check_disjoint(records)
    out = inject_share(records, args.share, args.seed)
    holdout.check_disjoint(out)
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
