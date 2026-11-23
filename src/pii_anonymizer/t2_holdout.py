"""Export the Teacher exclusion manifest from the final T2 split at freeze time."""

import argparse
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pii_anonymizer.swiss import T2_TEMPLATE_ID, read_jsonl

FINAL_FILENAME = "t2-final.jsonl"
_T2_VARIANT = re.compile(rf"({T2_TEMPLATE_ID})-s[012]-ch")


def source_id(record_id: str) -> str:
    """Remove the suffixes added by Swiss injection."""
    while record_id.endswith("-ch"):
        variant = _T2_VARIANT.fullmatch(record_id)
        if variant:
            return variant[1]
        record_id = record_id.removesuffix("-ch")
    return record_id


def text_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def paths_alias(first: Path, second: Path) -> bool:
    """Check resolved paths and existing file identity, including hard links."""
    if first.resolve() == second.resolve():
        return True
    try:
        return first.samefile(second)
    except FileNotFoundError:
        return False


@dataclass
class Holdout:
    source_ids: set[str]
    text_sha256: set[str]

    @classmethod
    def from_records(cls, records: Iterable[Mapping]) -> "Holdout":
        ids, hashes = set(), set()
        for record in records:
            ids.add(source_id(record["id"]))
            hashes.add(text_hash(record["text"]))
        return cls(ids, hashes)

    @classmethod
    def read(cls, path: Path) -> "Holdout":
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.keys() != {"source_ids", "text_sha256"}:
            raise ValueError(f"{path}: expected source_ids and text_sha256 in the manifest")
        ids, hashes = manifest["source_ids"], manifest["text_sha256"]
        if (
            not isinstance(ids, list)
            or not ids
            or any(
                not isinstance(value, str) or not value or source_id(value) != value
                for value in ids
            )
        ):
            raise ValueError(f"{path}: expected nonempty normalized source ids")
        if (
            not isinstance(hashes, list)
            or not hashes
            or any(
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                for value in hashes
            )
        ):
            raise ValueError(f"{path}: expected nonempty lowercase SHA-256 digests")
        return cls(set(ids), set(hashes))

    def check_disjoint(self, records: Iterable[Mapping]) -> None:
        shared = [
            record["id"]
            for record in records
            if source_id(record["id"]) in self.source_ids
            or text_hash(record["text"]) in self.text_sha256
        ]
        if shared:
            raise ValueError(
                f"{len(shared)} training rows are also test rows, such as {shared[:3]}"
            )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("final", type=Path, help="the frozen final T2 JSONL")
    parser.add_argument("manifest", type=Path, help="output manifest JSON")
    args = parser.parse_args(argv)
    if paths_alias(args.manifest, args.final):
        parser.error(f"output aliases input: {args.manifest} and {args.final}")

    holdout = Holdout.from_records(read_jsonl(args.final))
    if not holdout.source_ids or "" in holdout.source_ids:
        parser.error("final T2 must contain rows with nonempty source ids")
    manifest = {
        "source_ids": sorted(holdout.source_ids),
        "text_sha256": sorted(holdout.text_sha256),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
