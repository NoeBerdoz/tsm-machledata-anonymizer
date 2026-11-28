import json

import pytest

from pii_anonymizer import teacher_data
from pii_anonymizer.t2_holdout import Holdout, text_hash
from pii_anonymizer.teacher_data import build, check_labels, sample_gretel_train

TEXT = "Anna Muster, tel. +33 6 12 34 56 78"


def _openpii(uid, lang):
    return {
        "uid": str(uid),
        "source_text": f"{TEXT} #{uid}",
        "privacy_mask": [
            {"start": 0, "end": 4, "value": "Anna", "label": "GIVENNAME"},
            {"start": 18, "end": 35, "value": "+33 6 12 34 56 78", "label": "TELEPHONENUM"},
        ],
        "language": lang,
        "region": "FR",
    }


def _gretel(index, lang):
    text = f"IBAN DE12 3456 of Acme AG #{index}"
    spans = [{"start": 5, "end": 14, "label": "iban"}, {"start": 18, "end": 25, "label": "company"}]
    return {
        "index": index,
        "language": lang,
        "generated_text": text,
        "pii_spans": json.dumps(spans),
    }


LANGS = {"fr": "France", "de": "German", "it": "Italian", "en": "English"}
OPENPII = [_openpii(i * 10 + n, lang) for n, lang in enumerate(LANGS) for i in range(6)]
GRETEL = [_gretel(i * 10 + n, g) for n, g in enumerate(LANGS.values()) for i in range(3)]
GRETEL.append(_gretel(999, "Spanish"))


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(teacher_data, "OPENPII_PER_LANGUAGE", 5)
    monkeypatch.setattr(teacher_data, "GRETEL_PER_LANGUAGE", 2)


def test_build_samples_every_language_of_both_sources(small):
    records = build(OPENPII, GRETEL, [])
    sources = {(r["source"], r["lang"]) for r in records}
    assert len(records) == 4 * 5 + 4 * 2
    assert sources == {(s, lang) for s in ("openpii-1m-train", "gretel-train") for lang in LANGS}


def test_build_is_seeded(small):
    assert build(OPENPII, GRETEL, []) == build(OPENPII, GRETEL, [])
    assert build(OPENPII, GRETEL, [], seed=1) != build(OPENPII, GRETEL, [], seed=2)


def test_offsets_stay_right(small):
    for record in build(OPENPII, GRETEL, []):
        for entity in record["entities"]:
            assert record["text"][entity["start"] : entity["end"]].strip()


def test_a_test_row_stops_the_build(small):
    test_row = {"id": "t1", "text": f"{TEXT} #0", "entities": []}
    with pytest.raises(ValueError, match="training rows"):
        build(OPENPII, GRETEL, [[test_row]])


def test_a_t2_final_row_stops_the_build(small):
    rows = build(OPENPII, GRETEL, [])
    manifest = Holdout(source_ids=set(), text_sha256={text_hash(rows[0]["text"])})
    with pytest.raises(ValueError, match="training rows"):
        build(OPENPII, GRETEL, [], manifest=manifest)
    assert build(OPENPII, GRETEL, [], manifest=Holdout({"t2-0001"}, set())) == rows


def test_the_raw_t2_final_is_refused(tmp_path):
    final = tmp_path / "t2-final.jsonl"
    with pytest.raises(SystemExit):
        teacher_data.main([str(tmp_path / "out.jsonl"), "--exclude", str(final)])


def test_an_unknown_label_stops_the_build():
    with pytest.raises(ValueError, match="FAVOURITECOLOUR"):
        check_labels([{"entities": [{"start": 0, "end": 1, "label": "FAVOURITECOLOUR"}]}])


def test_gretel_takes_all_rows_when_a_language_has_fewer():
    sample = sample_gretel_train(GRETEL, per_language=10, seed=1)
    assert len(sample) == 12
    assert "Spanish" not in {r["language"] for r in sample}
