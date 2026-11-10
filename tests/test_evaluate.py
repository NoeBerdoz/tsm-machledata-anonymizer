import csv
import json

import pytest

import pii_anonymizer.evaluate
from pii_anonymizer.evaluate import evaluate
from pii_anonymizer.spans import Span, load_dataset

RECORDS = [
    {
        "id": "t2-0001",
        "text": "IBAN CH93 0076 2011 6238 5295 7 for Anna",
        "entities": [
            {"start": 5, "end": 31, "label": "IBAN"},
            {"start": 36, "end": 40, "label": "PERSON"},
        ],
        "lang": "en",
    },
    {"id": "t2-0002", "text": "call +41 79 123 45 67", "entities": [], "source": "logs"},
]


@pytest.fixture(autouse=True)
def fixed_cpu(monkeypatch):
    """Avoid asking the OS for the CPU in every test."""
    monkeypatch.setattr(pii_anonymizer.evaluate, "cpu_name", lambda: "Test CPU")


class IbanOnly:
    """Masks the IBAN of the first record and nothing else."""

    runtime = "test"
    files = []

    def detect(self, text, lang=None):
        return [Span(5, 31, "IBAN")] if text.startswith("IBAN") else []


class MasksEverything:
    runtime = "test"
    files = []

    def detect(self, text, lang=None):
        return [Span(0, len(text), "X")]


def write_dataset(path, records=RECORDS):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_load_dataset_ignores_extra_keys(tmp_path):
    examples = load_dataset(write_dataset(tmp_path / "t2-dev.jsonl"))
    assert [e.id for e in examples] == ["t2-0001", "t2-0002"]
    assert examples[0].entities[0] == Span(5, 31, "IBAN")


def test_load_dataset_refuses_bad_offsets(tmp_path):
    bad = [{"id": "x", "text": "short", "entities": [{"start": 2, "end": 9, "label": "A"}]}]
    with pytest.raises(ValueError, match="line 1"):
        load_dataset(write_dataset(tmp_path / "bad.jsonl", bad))


def test_results_row_is_replaced_on_rerun(tmp_path):
    dataset = write_dataset(tmp_path / "t2-dev.jsonl")
    out = tmp_path / "results"
    no_ids = tmp_path / "no-ids.txt"

    evaluate("regex", IbanOnly(), dataset, out, no_ids)
    evaluate("everything", MasksEverything(), dataset, out, no_ids)
    rows = read_csv(out / "results.csv")
    assert [(r["model"], r["dataset"]) for r in rows] == [
        ("everything", "t2-dev"),
        ("regex", "t2-dev"),
    ]
    assert rows[1]["strict_recall"] == "0.5000"
    assert rows[1]["char_precision"] == "1.0000"
    # Latency and size are not measured here, so their cells stay empty.
    assert rows[1]["latency_p95_ms"] == ""
    assert rows[1]["size_bytes"] == ""

    evaluate("regex", MasksEverything(), dataset, out, no_ids)
    rows = read_csv(out / "results.csv")
    assert len(rows) == 2
    assert rows[1]["model"] == "regex"
    assert rows[1]["strict_recall"] == "1.0000"

    per_type = read_csv(out / "recall_per_type.csv")
    assert [(r["model"], r["label"], r["n_entities"]) for r in per_type] == [
        ("everything", "IBAN", "1"),
        ("everything", "PERSON", "1"),
        ("regex", "IBAN", "1"),
        ("regex", "PERSON", "1"),
    ]
    assert "| regex | t2-dev | 100.0 % |" in (out / "summary.md").read_text()


def test_undefined_precision_leaves_an_empty_cell(tmp_path):
    class Nothing:
        runtime = "test"
        files = []

        def detect(self, text, lang=None):
            return []

    out = tmp_path / "results"
    evaluate("nothing", Nothing(), write_dataset(tmp_path / "t2-dev.jsonl"), out, tmp_path / "x")
    row = read_csv(out / "results.csv")[0]
    assert row["strict_recall"] == "0.0000"
    assert row["char_precision"] == ""


def test_latency_and_size_are_measured_when_available(tmp_path):
    ids = tmp_path / "latency_ids.txt"
    ids.write_text("# latency sample\nt2-0001\nt2-0002\n", encoding="utf-8")
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"x" * 2_500_000)

    detector = IbanOnly()
    detector.files = [weights]
    out = tmp_path / "results"
    evaluate("regex", detector, write_dataset(tmp_path / "t2-dev.jsonl"), out, ids)
    row = read_csv(out / "results.csv")[0]
    assert row["size_bytes"] == "2500000"
    assert row["size_mb"] == "2.5"
    assert row["latency_inputs"] == "2"
    assert row["latency_calls"] == "20"
    assert row["latency_p95_ms"] != ""


def test_partial_latency_sample_fails(tmp_path):
    ids = tmp_path / "latency_ids.txt"
    ids.write_text("t2-0001\nt2-9999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="t2-9999"):
        evaluate("regex", IbanOnly(), write_dataset(tmp_path / "t2-dev.jsonl"), tmp_path, ids)


def test_each_cpu_keeps_its_own_row(tmp_path, monkeypatch):
    dataset = write_dataset(tmp_path / "t2-dev.jsonl")
    out = tmp_path / "results"
    no_ids = tmp_path / "no-ids.txt"
    reference = "11th Gen Intel(R) Core(TM) i5-1130G7 @ 1.10GHz"

    monkeypatch.setattr(pii_anonymizer.evaluate, "cpu_name", lambda: "Other CPU")
    evaluate("regex", IbanOnly(), dataset, out, no_ids)
    monkeypatch.setattr(pii_anonymizer.evaluate, "cpu_name", lambda: reference)
    evaluate("regex", IbanOnly(), dataset, out, no_ids)
    rows = read_csv(out / "results.csv")
    assert {r["cpu"] for r in rows} == {"Other CPU", reference}

    # A rerun on the same CPU replaces only that CPU's row.
    evaluate("regex", MasksEverything(), dataset, out, no_ids)
    rows = {r["cpu"]: r for r in read_csv(out / "results.csv")}
    assert len(rows) == 2
    assert rows[reference]["strict_recall"] == "1.0000"
    assert rows["Other CPU"]["strict_recall"] == "0.5000"

    # Quality does not depend on the machine: one set of per-type rows.
    assert len(read_csv(out / "recall_per_type.csv")) == 2

    summary = (out / "summary.md").read_text()
    assert summary.count("| Model | Dataset |") == 2
    assert summary.index(f"## {reference} (reference)") < summary.index("## Other CPU")
