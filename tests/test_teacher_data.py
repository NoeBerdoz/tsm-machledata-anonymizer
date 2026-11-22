import json

import pytest

from pii_anonymizer import teacher_data
from pii_anonymizer.t2_holdout import Holdout
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


def test_an_unknown_label_stops_the_build():
    with pytest.raises(ValueError, match="FAVOURITECOLOUR"):
        check_labels([{"entities": [{"start": 0, "end": 1, "label": "FAVOURITECOLOUR"}]}])


def test_gretel_takes_all_rows_when_a_language_has_fewer():
    sample = sample_gretel_train(GRETEL, per_language=10, seed=1)
    assert len(sample) == 12
    assert "Spanish" not in {r["language"] for r in sample}


def test_final_manifest_checks_the_augmented_corpus(small):
    rows = build(OPENPII, GRETEL, [])
    rewritten = next(row for row in rows if row["id"].endswith("-ch"))
    final = Holdout.from_records([{"id": "different-id", "text": rewritten["text"]}])
    with pytest.raises(ValueError, match="training rows"):
        build(OPENPII, GRETEL, [], t2_manifest=final)


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--t2-manifest", "manifest.json"],
        ["--candidate", "--exclude", "t2-final.jsonl"],
        ["--t2-manifest", "t2-final.jsonl", "--t2-dev", "dev.jsonl"],
    ],
)
def test_reference_inputs_checked_before_opening_files(tmp_path, extra):
    with pytest.raises(SystemExit) as error:
        teacher_data.main([str(tmp_path / "candidate.jsonl"), "--exclude", "t1.jsonl", *extra])
    assert error.value.code == 2


def test_candidate_cannot_overwrite_reference_through_symlink(tmp_path):
    reference = tmp_path / "teacher-v1.jsonl"
    reference.write_bytes(b"reference")
    alias = tmp_path / "candidate.jsonl"
    alias.symlink_to(reference)
    with pytest.raises(SystemExit) as error:
        teacher_data.main([str(alias), "--candidate", "--exclude", "t1.jsonl"])
    assert error.value.code == 2
    assert reference.read_bytes() == b"reference"
