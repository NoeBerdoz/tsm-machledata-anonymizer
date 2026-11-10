"""Put valid fake Swiss identifiers into public test rows.

Usage:
    uv run python -m pii_anonymizer.swiss <in.jsonl> [<in2.jsonl> ...] <out.jsonl> --seed 0

No public dataset holds valid Swiss identifiers, so we make them. In each row, the value of
an entity of the right kind is replaced by a fake Swiss value of the same kind:

- `SOCIALNUM` becomes an AVS number (label `AVS`),
- `TELEPHONENUM` or `phone_number` becomes a Swiss phone number (label `PHONE`),
- `iban` or `bban` becomes a CH or LI IBAN (label `IBAN`).

The text is rewritten and the offsets of every later entity are shifted, so all labels stay
right by construction. Rows without such an entity are not written. Pure standard library.
See docs/swiss-identifiers.md.
"""

import argparse
import json
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from pii_anonymizer.rules import ean13_ok, iban_ok

# Gold label of the public datasets -> the Swiss label it becomes.
KINDS = {
    "SOCIALNUM": "AVS",
    "TELEPHONENUM": "PHONE",
    "phone_number": "PHONE",
    "iban": "IBAN",
    "bban": "IBAN",
}

MOBILE_PREFIXES = ("75", "76", "77", "78", "79")
# Real area codes, without the leading 0: Lausanne, Geneva, Yverdon, Fribourg, Valais, Bern,
# Biel and Neuchâtel, Lucerne, Zurich, Winterthur, Rapperswil, Baden, Swisscom business,
# Basel, Olten, St. Gallen, Chur, Ticino.
AREA_CODES = (
    "21", "22", "24", "26", "27", "31", "32", "41", "43", "44",
    "52", "55", "56", "58", "61", "62", "71", "81", "91",
)  # fmt: skip
MOBILE_SHARE = 0.6
LI_SHARE = 0.1

# Written formats and their weights. The dashes, the slash and the lowercase IBAN come from
# the review of pull request #19: people write them and the app's rules missed them.
AVS_FORMATS = {"dots": 6, "compact": 2, "spaces": 1, "dashes": 1}
IBAN_FORMATS = {"grouped": 6, "compact": 3, "lower": 1}
PHONE_FORMATS = {
    "intl": 3,  # +41 79 123 45 67
    "national": 3,  # 079 123 45 67
    "intl_compact": 1,  # +41791234567
    "intl_00": 1,  # 0041 79 123 45 67
    "intl_trunk": 1,  # +41 (0)79 123 45 67
    "slash": 1,  # 079/123 45 67
}

# A label written inside the gold span, such as "IBAN: DE12 ...", stays in the text.
_LABEL_PREFIX = re.compile(r"(?i)^iban\s*:?\s*")


def _choose(rng: random.Random, weights: Mapping[str, int]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def ean13_digit(first12: str) -> str:
    """The EAN-13 check digit of 12 digits."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def iban_check_digits(country: str, bban: str) -> str:
    """The two ISO 13616 check digits of an IBAN, from its country code and BBAN."""
    number = "".join(str(int(c, 36)) for c in bban + country + "00")
    return f"{98 - int(number) % 97:02d}"


def avs_number(rng: random.Random) -> str:
    """756, nine random digits and the EAN-13 check digit: 13 digits, no separators."""
    first12 = "756" + _digits(rng, 9)
    number = first12 + ean13_digit(first12)
    assert ean13_ok(number)
    return number


def iban_number(rng: random.Random, country: str | None = None) -> str:
    """A CH (or LI) IBAN: country, check digits, 5-digit bank number, 12-digit account."""
    if country is None:
        country = "LI" if rng.random() < LI_SHARE else "CH"
    bban = _digits(rng, 5) + _digits(rng, 12)
    iban = country + iban_check_digits(country, bban) + bban
    assert iban_ok(iban)
    return iban


def phone_number(rng: random.Random) -> str:
    """A Swiss number in national form without separators, such as 0791234567."""
    prefix = rng.choice(MOBILE_PREFIXES if rng.random() < MOBILE_SHARE else AREA_CODES)
    return "0" + prefix + rng.choice("23456789") + _digits(rng, 6)


def format_avs(number: str, style: str) -> str:
    groups = [number[:3], number[3:7], number[7:11], number[11:]]
    separators = {"dots": ".", "compact": "", "spaces": " ", "dashes": "-"}
    return separators[style].join(groups)


def format_iban(iban: str, style: str) -> str:
    grouped = " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))
    return {"grouped": grouped, "compact": iban, "lower": grouped.lower()}[style]


def format_phone(number: str, style: str) -> str:
    area, rest = number[1:3], number[3:]
    groups = f"{rest[:3]} {rest[3:5]} {rest[5:]}"
    return {
        "intl": f"+41 {area} {groups}",
        "national": f"0{area} {groups}",
        "intl_compact": f"+41{area}{rest}",
        "intl_00": f"0041 {area} {groups}",
        "intl_trunk": f"+41 (0){area} {groups}",
        "slash": f"0{area}/{groups}",
    }[style]


def fake_value(kind: str, rng: random.Random) -> str:
    """A valid fake Swiss value of the kind (`AVS`, `IBAN` or `PHONE`), in a random format."""
    if kind == "AVS":
        return format_avs(avs_number(rng), _choose(rng, AVS_FORMATS))
    if kind == "IBAN":
        return format_iban(iban_number(rng), _choose(rng, IBAN_FORMATS))
    if kind == "PHONE":
        return format_phone(phone_number(rng), _choose(rng, PHONE_FORMATS))
    raise ValueError(f"unknown kind {kind!r}")


def _core(text: str, start: int, end: int, kind: str) -> tuple[int, int]:
    """The part of a gold span to replace: no surrounding spaces, no "IBAN:" label."""
    value = text[start:end]
    start += len(value) - len(value.lstrip())
    end -= len(value) - len(value.rstrip())
    if kind == "IBAN":
        prefix = _LABEL_PREFIX.match(text[start:end])
        if prefix and prefix.end() < end - start:
            start += prefix.end()
    return start, end


def inject(record: Mapping, rng: random.Random) -> dict | None:
    """The record with a Swiss value in place of each entity of a matching kind.

    The same original value gets the same Swiss value within one record, so a document
    that repeats an account number still repeats it. An entity that overlaps another one
    is left as it is, because its text cannot be replaced cleanly. Returns None when no
    entity was replaced.
    """
    text = record["text"]
    entities = sorted(record["entities"], key=lambda e: (e["start"], e["end"]))
    targets = set()
    for i, entity in enumerate(entities):
        if entity["label"] not in KINDS:
            continue
        overlaps = any(
            j != i and other["start"] < entity["end"] and entity["start"] < other["end"]
            for j, other in enumerate(entities)
        )
        start, end = _core(text, entity["start"], entity["end"], KINDS[entity["label"]])
        if not overlaps and start < end:
            targets.add(i)
    if not targets:
        return None

    pieces = []
    new_entities = []
    expected = []
    chosen: dict[tuple[str, str], str] = {}
    cursor = shift = 0
    for i, entity in enumerate(entities):
        if i in targets:
            kind = KINDS[entity["label"]]
            start, end = _core(text, entity["start"], entity["end"], kind)
            key = (kind, text[start:end])
            if key not in chosen:
                chosen[key] = fake_value(kind, rng)
            value = chosen[key]
            pieces.append(text[cursor:start])
            pieces.append(value)
            cursor = end
            new_start = start + shift
            new_entities.append({"start": new_start, "end": new_start + len(value), "label": kind})
            expected.append(value)
            shift += len(value) - (end - start)
        else:
            new_entities.append(
                {**entity, "start": entity["start"] + shift, "end": entity["end"] + shift}
            )
            expected.append(text[entity["start"] : entity["end"]])
    pieces.append(text[cursor:])
    new_text = "".join(pieces)

    for entity, value in zip(new_entities, expected, strict=True):
        if new_text[entity["start"] : entity["end"]] != value:
            raise AssertionError(f"offsets broken in {record.get('id')}: {entity}")
    return {**record, "id": f"{record['id']}-ch", "text": new_text, "entities": new_entities}


def inject_all(records: Iterable[Mapping], seed: int) -> list[dict]:
    """Inject every record that has a matching entity, and drop the others.

    Each record gets its own generator, seeded from the seed and the record id. So a row's
    values do not depend on the other rows, and a fixed seed gives the same file on every
    machine (string seeds go through SHA-512, not through Python's salted hash).
    """
    out = []
    for record in records:
        injected = inject(record, random.Random(f"{seed}:{record['id']}"))
        if injected is not None:
            out.append(injected)
    return out


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Put valid fake Swiss identifiers into rows.")
    parser.add_argument("paths", nargs="+", type=Path, help="input JSONL files, then the output")
    parser.add_argument("--seed", type=int, default=0, help="seed of the random values")
    args = parser.parse_args(argv)
    if len(args.paths) < 2:
        parser.error("give at least one input file and the output file")
    *inputs, output = args.paths

    records = [record for path in inputs for record in read_jsonl(path)]
    injected = inject_all(records, args.seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for record in injected:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    counts: dict[str, dict[str, int]] = {}
    for record in injected:
        per_lang = counts.setdefault(record.get("lang") or "?", {"rows": 0})
        per_lang["rows"] += 1
        for entity in record["entities"]:
            if entity["label"] in ("AVS", "PHONE", "IBAN"):
                per_lang[entity["label"]] = per_lang.get(entity["label"], 0) + 1
    print(f"{output}: {len(injected)} of {len(records)} rows received a Swiss value")
    for lang, c in sorted(counts.items()):
        print(
            f"  {lang}: {c['rows']} rows, AVS {c.get('AVS', 0)}, "
            f"PHONE {c.get('PHONE', 0)}, IBAN {c.get('IBAN', 0)}"
        )


if __name__ == "__main__":
    main()
