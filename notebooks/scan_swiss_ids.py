"""Scan public PII datasets for Swiss identifiers and for agent-style text (issue #5).

Download the parquet files listed at https://huggingface.co/api/datasets/<name>/parquet
into <dl>/openpii, <dl>/p500k, <dl>/gretel and <dl>/nemotron, then run:

    uv run --with pyarrow python notebooks/scan_swiss_ids.py <dl> openpii p500k gretel nemotron
"""

import collections
import json
import re
import sys

import pyarrow.parquet as pq

DL = sys.argv[1]

AVS = re.compile(r"(?<!\d)756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}(?!\d)")
IBAN = re.compile(r"\b(?:CH|LI)\d{2}(?:\s?[0-9A-Z]{4}){4}\s?[0-9A-Z](?![0-9A-Z])")
PHONE = re.compile(r"(?:\+41|0041)[\s.-]?\(?0?\)?[\s.-]?\d{2}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}")
UID = re.compile(r"\bCHE[-\s]?\d{3}\.?\d{3}\.?\d{3}\b")
STYLE = {
    "json": re.compile(r'\{\s*"[\w-]+"\s*:'),
    "log_ts": re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"),
    "log_level": re.compile(r"\b(?:INFO|WARN|WARNING|ERROR|DEBUG)\b"),
    "shell": re.compile(r"(?m)^\s*\$ \w+"),
    "code": re.compile(r"(?m)^\s*(?:def |class |import |function |const |public )"),
    "traceback": re.compile(r"Traceback \(most recent call last\)"),
}


def avs_ok(s):
    d = re.sub(r"\D", "", s)
    total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(d[:12]))
    return (10 - total % 10) % 10 == int(d[12])


def iban_ok(s):
    s = re.sub(r"\s", "", s)
    r = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1


def load(name):
    if name in ("openpii", "p500k"):
        files = {"openpii": ["validation.0", "validation.1"], "p500k": ["validation.0"]}[name]
        for f in files:
            t = pq.read_table(
                f"{DL}/{name}/{f}.parquet",
                columns=["source_text", "privacy_mask", "language", "region"],
            )
            for text, mask, lang, region in zip(
                *(t.column(c).to_pylist() for c in t.column_names), strict=False
            ):
                yield text, [(m["start"], m["end"], m["label"]) for m in mask], lang, region
    elif name == "gretel":
        for f in ["train.0", "test.0"]:
            t = pq.read_table(
                f"{DL}/gretel/{f}.parquet", columns=["generated_text", "pii_spans", "language"]
            )
            for text, spans, lang in zip(
                *(t.column(c).to_pylist() for c in t.column_names), strict=False
            ):
                sp = [(s["start"], s["end"], s["label"]) for s in json.loads(spans)]
                yield text, sp, lang, None
    elif name == "nemotron":
        for f in ["train.0", "test.0"]:
            t = pq.read_table(f"{DL}/nemotron/{f}.parquet", columns=["text", "spans", "locale"])
            for text, spans, loc in zip(
                *(t.column(c).to_pylist() for c in t.column_names), strict=False
            ):
                try:
                    sp = json.loads(spans)
                except json.JSONDecodeError:
                    import ast

                    sp = ast.literal_eval(spans)
                yield text, [(s["start"], s["end"], s["label"]) for s in sp], "en", loc


def label_of(spans, a, b):
    for s, e, lab in spans:
        if s <= a and e >= b:
            return lab
    for s, e, lab in spans:
        if s < b and e > a:
            return "partial:" + lab
    return "UNLABELLED"


out = {}
for name in sys.argv[2:]:
    n = 0
    regions = collections.Counter()
    hits = {k: collections.Counter() for k in ("avs", "iban", "phone", "uid")}
    valid = collections.Counter()
    examples = collections.defaultdict(list)
    style = collections.Counter()
    for text, spans, _lang, region in load(name):
        n += 1
        if region:
            regions[region] += 1
        for key, rx, check in (
            ("avs", AVS, avs_ok),
            ("iban", IBAN, iban_ok),
            ("phone", PHONE, None),
            ("uid", UID, None),
        ):
            for m in rx.finditer(text):
                hits[key][label_of(spans, m.start(), m.end())] += 1
                if check and check(m.group()):
                    valid[key] += 1
                if len(examples[key]) < 3:
                    examples[key].append(text[max(0, m.start() - 60) : m.end() + 40])
        for k, rx in STYLE.items():
            if rx.search(text):
                style[k] += 1
    out[name] = {
        "rows": n,
        "regions_top": regions.most_common(40),
        "hits": {k: dict(v) for k, v in hits.items()},
        "checksum_valid": dict(valid),
        "examples": examples,
        "style_rows": dict(style),
    }
    print(name, json.dumps(out[name], ensure_ascii=False, indent=1), flush=True)
