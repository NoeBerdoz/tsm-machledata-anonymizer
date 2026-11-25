import json
import re
import subprocess
import sys
from pathlib import Path

from pii_anonymizer import backend, engine, o4
from pii_anonymizer.baselines import GLINER2_LABELS
from pii_anonymizer.spans import Span

GENERATOR = Path(__file__).resolve().parents[1] / "scripts" / "generate_o4_requests.py"


class FakeDetector:
    runtime = "fake"
    files = ()

    def __init__(self, names, label="full_name"):
        self.names = names
        self.label = label
        self.languages = set()

    def detect(self, text, lang=None):
        self.languages.add(lang)
        return [
            Span(match.start(), match.end(), self.label)
            for name in self.names
            for match in re.finditer(re.escape(name), text)
        ]


def single_value_request(identifier, prompt, value, label="PERSON"):
    start = prompt.index(value)
    return {
        "id": identifier,
        "lang": "en",
        "prompt": prompt,
        "files": [],
        "values": [
            {
                "id": f"{identifier}-1",
                "label": label,
                "value": value,
                "occurrences": [{"source": "prompt", "start": start, "end": start + len(value)}],
            }
        ],
    }


def write_manifest(path, *requests):
    path.write_text("".join(json.dumps(request) + "\n" for request in requests), encoding="utf-8")
    return path


def test_runs_generated_requests_and_restores_repeats_and_literal(tmp_path):
    subprocess.run([sys.executable, str(GENERATOR), str(tmp_path)], check=True)
    manifest = tmp_path / "requests.jsonl"
    requests = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    detector = FakeDetector(
        {
            planted["value"]
            for request in requests
            for planted in request["values"]
            if planted["label"] == "PERSON"
        }
    )

    report = o4.run(manifest, detector)

    assert report["planted"] == report["detected"] == 100
    assert report["all_leaks"] == report["app_leaks"] == report["detector_misses"] == []
    assert report["restored"] == report["intact"] > 100
    assert detector.languages == {"fr", "de", "it", "en"}
    french = report["requests"][0]
    assert french["capture_counts"] == {"backend": 1, "sentry": 0, "llm": 1}
    assert set(french["spans"]) == {"prompt", "suivi.txt", "virements.pdf"}
    assert french["restoration"]["failures"] == []
    repeated = french["values"][0]["occurrences"]
    assert len([item for item in repeated if item["source"] == "prompt"]) == 2
    assert all(item["detected"] for item in repeated)


def test_counts_every_echo_of_a_placeholder_with_a_missing_mapping(monkeypatch, tmp_path):
    subprocess.run([sys.executable, str(GENERATOR), str(tmp_path)], check=True)
    manifest = tmp_path / "requests.jsonl"
    with manifest.open(encoding="utf-8") as requests:
        french = json.loads(next(requests))
    detector = FakeDetector(
        {planted["value"] for planted in french["values"] if planted["label"] == "PERSON"}
    )
    original_pseudonymize = engine.pseudonymize

    def lose_mapping_entry(texts):
        masked, mapping = original_pseudonymize(texts)
        del mapping["<PERSON_2>"]
        return masked, mapping

    monkeypatch.setattr(engine, "pseudonymize", lose_mapping_entry)
    run = o4.run_request(french, tmp_path, detector)

    assert "<PERSON_1>" in run.captures["backend"][0]["body"]["text"]
    assert run.restoration == {
        "intact": 30,
        "restored": 26,
        "failures": ["<PERSON_2>"] * 4,
    }


def test_reports_outbound_leak_once_and_traces_missed_occurrences(monkeypatch, tmp_path):
    prompt = "Élise Burnier, Jules Simon, Ada Green. Élise Burnier."
    note = "Jules Simon and Élise Burnier."
    (tmp_path / "notes.txt").write_text(note, encoding="utf-8")
    planted = [
        {
            "id": identifier,
            "value": value,
            "label": "PERSON",
            "occurrences": [
                {"source": source, "start": match.start(), "end": match.end()}
                for source, text in [("prompt", prompt), ("notes.txt", note)]
                for match in re.finditer(re.escape(value), text)
            ],
        }
        for identifier, value in [
            ("leak", "Élise Burnier"),
            ("partial", "Jules Simon"),
            ("miss", "Ada Green"),
        ]
    ]
    request = {
        "id": "demo",
        "lang": "fr",
        "prompt": prompt,
        "files": ["notes.txt"],
        "values": planted,
    }
    manifest = tmp_path / "requests.jsonl"
    manifest.write_text(json.dumps(request) + "\n", encoding="utf-8")
    original_answer = backend.ask_llm

    def leak(text):
        return original_answer(text + "\nÉlise Burnier\nÉlise Burnier")

    monkeypatch.setattr(backend, "ask_llm", leak)

    class PartialDetector(FakeDetector):
        def detect(self, text, lang=None):
            end = " Simon" if text == prompt else ""
            return super().detect(text, lang) + [
                Span(match.start(), match.end(), "PERSON")
                for match in re.finditer("Jules" + end, text)
            ]

    report = o4.run(manifest, PartialDetector(["Élise Burnier"]))

    assert report["planted"] == 3
    assert report["detected"] == 1
    assert report["app_leaks"] == ["leak"]
    assert report["detector_misses"] == ["miss", "partial"]
    assert report["all_leaks"] == ["leak", "miss", "partial"]
    leak, partial, miss = report["requests"][0]["values"]
    assert leak["found_in"] == ["llm"]
    assert [occurrence["detected"] for occurrence in partial["occurrences"]] == [True, False]
    assert partial["found_in"] == []
    assert miss["found_in"] == ["backend", "llm"]


def test_traces_a_sentry_event_by_decoded_field():
    text = "Élise Burnier"
    request = {
        "values": [
            {
                "id": "name",
                "value": text,
                "label": "PERSON",
                "occurrences": [{"source": "prompt", "start": 0, "end": len(text)}],
            }
        ]
    }
    captures = {
        "backend": [{"text": "Élise", "other": "Burnier"}],
        "sentry": [{"exception": [{"value": "Unexpected value Élise\n Burnier"}]}],
        "llm": [],
    }
    result = o4.trace(
        request, {"prompt": text}, {"prompt": [Span(0, len(text), "PERSON")]}, captures
    )

    assert result["values"][0]["found_in"] == ["sentry"]
    assert result["spans"]["prompt"][0]["found_in"] == ["sentry"]


def test_checks_each_displayed_placeholder_with_spaces_normalized():
    person, literal = "<PERSON_2>", "<PERSON_1>"
    displayed = o4.SEPARATOR.join(["Élise Burnier", literal, "Different Person"])
    result = o4.check_restoration(
        [person, literal, person], displayed, {person: "Élise\n  Burnier"}
    )

    assert result == {"intact": 2, "restored": 1, "failures": [person]}


def test_finds_compact_ibans_within_a_decoded_capture_field():
    iban = "CH05 4438 5535 0877 0501 0"
    request = single_value_request("transfer", iban, iban, "IBAN")
    captures = {
        "backend": [{"text": "CH0544385535", "other": "087705010"}],
        "llm": [{"text": "Use CH0544385535087705010."}],
    }
    report = o4.trace(request, {"prompt": iban}, {"prompt": [Span(0, len(iban), "IBAN")]}, captures)

    assert report["values"][0]["found_in"] == ["llm"]
    assert report["spans"]["prompt"][0]["found_in"] == ["llm"]


def test_finds_a_stale_value_in_a_later_request_and_counts_it_once(monkeypatch, tmp_path):
    first = single_value_request("first", "First: Ada Green", "Ada Green")
    later = single_value_request("later", "Later: Jules Simon", "Jules Simon")
    manifest = write_manifest(tmp_path / "requests.jsonl", first, later)
    original_answer = backend.ask_llm

    def leak(text):
        if text.startswith("Later:"):
            text += "\nAda Green\nAda Green"
        return original_answer(text)

    monkeypatch.setattr(backend, "ask_llm", leak)
    report = o4.run(manifest, FakeDetector(["Ada Green", "Jules Simon"]))

    assert report["detected"] == 2
    assert report["app_leaks"] == report["all_leaks"] == ["first-1"]
    assert report["requests"][0]["values"][0]["found_in"] == ["llm"]
    assert report["requests"][1]["values"][0]["found_in"] == []


def test_restores_a_literal_tagged_as_account_id(tmp_path):
    literal = "<PERSON_1>"
    request = single_value_request("example", f"Ada Green used {literal}.", "Ada Green")
    manifest = write_manifest(tmp_path / "requests.jsonl", request)

    report = o4.run(manifest, FakeDetector(["Ada Green", literal], label="account_id"))

    assert report["restored"] == report["intact"] == 2
    assert report["requests"][0]["restoration"]["failures"] == []
    assert {o4.placeholder_label(label) for label in GLINER2_LABELS} <= {
        *engine.MODEL_LABELS,
        *engine.RULE_LABELS,
    }
