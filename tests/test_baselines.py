import json

import pytest

import pii_anonymizer.evaluate
from pii_anonymizer.baselines import GLINER2_LABELS, privacy_filter_spans
from pii_anonymizer.evaluate import DETECTORS, evaluate
from pii_anonymizer.public_data import LANGUAGES, convert_row, sample_rows
from pii_anonymizer.spans import Span, load_dataset

# Two rows in the ai4privacy format, written by hand. The second has one entity whose
# offsets do not point to its value.
ROWS = [
    {
        "uid": 7,
        "source_text": "Ma mère Astrit Kofi est née à Ruswil",
        "privacy_mask": [
            {"label": "GIVENNAME", "start": 8, "end": 14, "value": "Astrit", "label_index": 1},
            {"label": "SURNAME", "start": 15, "end": 19, "value": "Kofi", "label_index": 1},
            {"label": "CITY", "start": 30, "end": 36, "value": "Ruswil", "label_index": 1},
        ],
        "language": "fr",
        "region": "CH",
    },
    {
        "uid": 8,
        "source_text": "Call Anna at 079 123 45 67",
        "privacy_mask": [
            {"label": "GIVENNAME", "start": 5, "end": 9, "value": "Anna", "label_index": 1},
            {"label": "TELEPHONENUM", "start": 12, "end": 20, "value": "079 123 45 67"},
        ],
        "language": "en",
        "region": "CH",
    },
]


def test_registry_has_the_three_baselines():
    assert {"regex", "presidio", "gliner2"} <= set(DETECTORS)


def test_registry_has_privacy_filter_and_its_union():
    assert {"privacy-filter", "regex+privacy-filter"} <= set(DETECTORS)


def test_privacy_filter_spans_join_strip_and_clip():
    # The shape of the pipeline output with aggregation_strategy="simple": the E- token of a
    # BIOES entity comes out as a group of its own, and tokens carry the space before them.
    text = "My name is Harry Potter, call +41 79 123 45 67"
    entities = [
        {"entity_group": "private_person", "start": 10, "end": 16, "word": " Harry"},
        {"entity_group": "private_person", "start": 16, "end": 23, "word": " Potter"},
        {"entity_group": "private_phone", "start": 29, "end": 43, "word": " +41 79 123 45 "},
        {"entity_group": "private_phone", "start": 43, "end": 47, "word": "67"},
        {"entity_group": "secret", "start": 10, "end": 11, "word": " "},
    ]
    spans = privacy_filter_spans(entities, text)
    assert [(s.label, text[s.start : s.end]) for s in spans] == [
        ("private_person", "Harry Potter"),
        ("private_phone", "+41 79 123 45 67"),
    ]
    # The last group ends one past the text: it is clipped.
    assert spans[-1].end == len(text)


def test_privacy_filter_spans_keep_different_labels_apart():
    text = "Anna 1990"
    entities = [
        {"entity_group": "private_person", "start": 0, "end": 4},
        {"entity_group": "private_date", "start": 4, "end": 9},
    ]
    assert privacy_filter_spans(entities, text) == [
        Span(0, 4, "private_person"),
        Span(5, 9, "private_date"),
    ]


def test_gliner2_uses_the_42_card_labels():
    assert len(GLINER2_LABELS) == 42
    assert len(set(GLINER2_LABELS)) == 42


def test_convert_row_keeps_labels_and_offsets():
    record, dropped = convert_row(ROWS[0], "t1-test")
    assert dropped == 0
    assert record["id"] == "t1-test-7"
    assert record["lang"] == "fr"
    assert record["source"] == "t1-test"
    assert record["entities"][0] == {"start": 8, "end": 14, "label": "GIVENNAME"}
    text = record["text"]
    assert [text[e["start"] : e["end"]] for e in record["entities"]] == ["Astrit", "Kofi", "Ruswil"]


def test_convert_row_drops_misaligned_entities():
    record, dropped = convert_row(ROWS[1], "t1-test")
    assert dropped == 1
    assert [e["label"] for e in record["entities"]] == ["GIVENNAME"]


def test_converted_rows_load_as_a_test_set(tmp_path):
    path = tmp_path / "t1.jsonl"
    records = [convert_row(row, "t1-test")[0] for row in ROWS]
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    examples = load_dataset(path)
    assert [e.lang for e in examples] == ["fr", "en"]
    assert examples[0].entities[2] == Span(30, 36, "CITY")


def test_sample_is_seeded_and_balanced():
    languages = (*LANGUAGES, "es")
    rows = [{"uid": i, "language": languages[i % 5]} for i in range(500)]
    first = sample_rows(rows, per_language=5, seed=1)
    again = sample_rows(list(reversed(rows)), per_language=5, seed=1)
    assert [r["uid"] for r in first] == [r["uid"] for r in again]
    assert [r["language"] for r in first] == [lang for lang in LANGUAGES for _ in range(5)]
    with pytest.raises(ValueError, match="only"):
        sample_rows(rows, per_language=10_000)


class RecordsLanguage:
    """Remembers the language it receives for each text."""

    runtime = "test"
    files = []

    def __init__(self):
        self.seen = {}

    def detect(self, text, lang=None):
        self.seen[text] = lang
        return []


def test_evaluation_passes_the_language(tmp_path, monkeypatch):
    monkeypatch.setattr(pii_anonymizer.evaluate, "cpu_name", lambda: "Test CPU")
    records = [
        {"id": "a", "text": "Bonjour Anna", "entities": [], "lang": "fr"},
        {"id": "b", "text": "Hello Anna", "entities": []},
    ]
    path = tmp_path / "t1.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    detector = RecordsLanguage()
    evaluate("lang", detector, path, tmp_path / "results", tmp_path / "no-ids.txt")
    assert detector.seen == {"Bonjour Anna": "fr", "Hello Anna": None}


def test_presidio_finds_an_email_in_french():
    pytest.importorskip("presidio_analyzer")
    pytest.importorskip("fr_core_news_lg")
    detector = DETECTORS["presidio"]()
    text = "Écrivez à anna.meier@example.ch demain."
    spans = detector.detect(text, lang="fr")
    assert ("EMAIL_ADDRESS", "anna.meier@example.ch") in [
        (s.label, text[s.start : s.end]) for s in spans
    ]
    with pytest.raises(ValueError, match="language"):
        detector.detect(text)


def test_gliner2_offsets_point_to_the_entity():
    pytest.importorskip("gliner2")
    hub = pytest.importorskip("huggingface_hub")
    from pii_anonymizer.baselines import GLINER2_MODEL

    if not isinstance(hub.try_to_load_from_cache(GLINER2_MODEL, "model.safetensors"), str):
        pytest.skip("GLiNER2-PII is not downloaded")
    detector = DETECTORS["gliner2"]()
    text = "Please write to anna.meier@example.ch before Friday."
    spans = detector.detect(text)
    assert ("email", "anna.meier@example.ch") in [(s.label, text[s.start : s.end]) for s in spans]


def test_privacy_filter_offsets_point_to_the_entity():
    pytest.importorskip("transformers")
    hub = pytest.importorskip("huggingface_hub")
    from pii_anonymizer.baselines import PRIVACY_FILTER_MODEL

    if not isinstance(hub.try_to_load_from_cache(PRIVACY_FILTER_MODEL, "model.safetensors"), str):
        pytest.skip("OpenAI Privacy Filter is not downloaded")
    detector = DETECTORS["privacy-filter"]()
    text = "Please write to Noémie Müller at anna.meier@example.ch before Friday."
    found = [(s.label, text[s.start : s.end]) for s in detector.detect(text)]
    assert ("private_email", "anna.meier@example.ch") in found
    assert ("private_person", "Noémie Müller") in found
