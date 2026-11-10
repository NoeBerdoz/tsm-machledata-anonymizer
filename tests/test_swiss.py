import json
import random
import re

import pytest

from pii_anonymizer.baselines import UnionDetector
from pii_anonymizer.rules import ean13_ok, iban_ok
from pii_anonymizer.spans import Span
from pii_anonymizer.swiss import (
    AREA_CODES,
    AVS_FORMATS,
    IBAN_FORMATS,
    MOBILE_PREFIXES,
    PHONE_FORMATS,
    avs_number,
    fake_value,
    format_avs,
    format_iban,
    format_phone,
    iban_number,
    inject,
    inject_all,
    main,
    phone_number,
)

TEXT = "Anna Muster, AVS 1 69 01 75895 374 66, tel. +33 6 12 34 56 78, IBAN: DE12 3456, Bern"


def _entity(text, value, label):
    start = text.index(value)
    return {"start": start, "end": start + len(value), "label": label}


RECORD = {
    "id": "r1",
    "text": TEXT,
    "lang": "de",
    "entities": [
        _entity(TEXT, "Anna", "GIVENNAME"),
        _entity(TEXT, "1 69 01 75895 374 66", "SOCIALNUM"),
        _entity(TEXT, "+33 6 12 34 56 78", "TELEPHONENUM"),
        _entity(TEXT, "IBAN: DE12 3456", "iban"),
        _entity(TEXT, "Bern", "CITY"),
    ],
}


def _values(record):
    return [record["text"][e["start"] : e["end"]] for e in record["entities"]]


def test_generated_avs_and_iban_pass_the_validators():
    rng = random.Random(0)
    for _ in range(500):
        avs = avs_number(rng)
        assert avs.startswith("756") and len(avs) == 13 and ean13_ok(avs)
        iban = iban_number(rng)
        assert iban[:2] in ("CH", "LI") and len(iban) == 21 and iban_ok(iban)
    assert iban_ok(iban_number(rng, country="LI"))


def test_a_wrong_check_digit_fails():
    rng = random.Random(1)
    avs = avs_number(rng)
    wrong = avs[:12] + str((int(avs[12]) + 1) % 10)
    assert not ean13_ok(wrong)
    iban = iban_number(rng)
    wrong_iban = iban[:2] + f"{(int(iban[2:4]) + 1) % 100:02d}" + iban[4:]
    assert not iban_ok(wrong_iban)


def test_phone_numbers_use_swiss_prefixes():
    rng = random.Random(2)
    for _ in range(200):
        number = phone_number(rng)
        assert len(number) == 10 and number[0] == "0"
        assert number[1:3] in MOBILE_PREFIXES + AREA_CODES


def test_every_format_is_written_as_people_write_it():
    avs, iban, phone = "7561234567897", "CH9300762011623852957", "0791234567"
    assert {format_avs(avs, s) for s in AVS_FORMATS} == {
        "756.1234.5678.97",
        "7561234567897",
        "756 1234 5678 97",
        "756-1234-5678-97",
    }
    assert {format_iban(iban, s) for s in IBAN_FORMATS} == {
        "CH93 0076 2011 6238 5295 7",
        "CH9300762011623852957",
        "ch93 0076 2011 6238 5295 7",
    }
    assert {format_phone(phone, s) for s in PHONE_FORMATS} == {
        "+41 79 123 45 67",
        "079 123 45 67",
        "+41791234567",
        "0041 79 123 45 67",
        "+41 (0)79 123 45 67",
        "079/123 45 67",
    }


def test_formatted_values_still_validate():
    rng = random.Random(3)
    for _ in range(200):
        assert ean13_ok(re.sub(r"[ .-]", "", fake_value("AVS", rng)))
        assert iban_ok(fake_value("IBAN", rng))


def test_injection_keeps_every_offset_right():
    out = inject(RECORD, random.Random(0))
    assert out["id"] == "r1-ch"
    labels = [e["label"] for e in out["entities"]]
    assert labels == ["GIVENNAME", "AVS", "PHONE", "IBAN", "CITY"]
    values = _values(out)
    # Entities before and after the replaced ones keep their text.
    assert values[0] == "Anna" and values[4] == "Bern"
    assert ean13_ok(re.sub(r"[ .-]", "", values[1]))
    assert iban_ok(values[3])
    # The label written inside the gold span stays in the text, outside the entity.
    assert "IBAN: " + values[3] in out["text"]
    assert out["text"].endswith(", Bern")
    # Every Swiss value is a valid one that the input did not hold.
    assert "+33" not in out["text"] and "DE12" not in out["text"]


def test_spaces_around_a_value_stay_outside_the_entity():
    text = "Call 030 1265007  now"
    record = {"id": "x", "text": text, "entities": [_entity(text, "030 1265007 ", "TELEPHONENUM")]}
    out = inject(record, random.Random(0))
    value = _values(out)[0]
    assert value == value.strip()
    assert out["text"].startswith("Call ") and out["text"].endswith(value + "  now")


def test_a_repeated_value_gets_the_same_swiss_value():
    text = "Account GB12X, again GB12X."
    first = _entity(text, "GB12X", "bban")
    second = {"start": text.rindex("GB12X"), "end": text.rindex("GB12X") + 5, "label": "bban"}
    out = inject({"id": "y", "text": text, "entities": [first, second]}, random.Random(0))
    a, b = _values(out)
    assert a == b and iban_ok(a)


def test_same_seed_same_output_and_other_seed_other_output():
    assert inject_all([RECORD], seed=0) == inject_all([RECORD], seed=0)
    assert inject_all([RECORD], seed=0) != inject_all([RECORD], seed=1)


def test_rows_without_matching_entities_are_untouched():
    record = {"id": "z", "text": "Anna", "entities": [{"start": 0, "end": 4, "label": "GIVENNAME"}]}
    before = json.dumps(record)
    assert inject(record, random.Random(0)) is None
    assert inject_all([record], seed=0) == []
    assert json.dumps(record) == before


def test_command_line_writes_only_injected_rows(tmp_path):
    plain = {"id": "z", "text": "Anna", "entities": [{"start": 0, "end": 4, "label": "GIVENNAME"}]}
    source = tmp_path / "in.jsonl"
    source.write_text(json.dumps(RECORD) + "\n" + json.dumps(plain) + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    main([str(source), str(out), "--seed", "0"])
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in rows] == ["r1-ch"]
    assert [e["label"] for e in rows[0]["entities"]] == [
        "GIVENNAME",
        "AVS",
        "PHONE",
        "IBAN",
        "CITY",
    ]


class _Fixed:
    def __init__(self, spans, runtime, files=()):
        self.spans, self.runtime, self.files = spans, runtime, list(files)

    def detect(self, text, lang=None):
        return list(self.spans)


def test_union_detector_merges_spans():
    a = _Fixed([Span(0, 4, "AVS"), Span(10, 12, "PHONE")], "python-re 3.13")
    b = _Fixed([Span(0, 4, "AVS"), Span(20, 25, "person")], "torch 2.9.1", files=["w.bin"])
    union = UnionDetector([a, b], files_from=b)
    assert union.detect("x" * 30) == [
        Span(0, 4, "AVS"),
        Span(10, 12, "PHONE"),
        Span(20, 25, "person"),
    ]
    assert union.runtime == "python-re 3.13 + torch 2.9.1"
    assert union.files == ["w.bin"]


def test_registry_has_the_combined_detector():
    from pii_anonymizer.evaluate import DETECTORS

    assert "regex+gliner2" in DETECTORS


@pytest.mark.parametrize("kind", ["AVS", "IBAN", "PHONE"])
def test_fake_values_differ_between_calls(kind):
    rng = random.Random(4)
    assert len({fake_value(kind, rng) for _ in range(20)}) > 15
