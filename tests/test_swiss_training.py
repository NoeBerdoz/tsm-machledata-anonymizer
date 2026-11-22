import json
import re

import pytest

from pii_anonymizer.rules import ean13_ok, iban_ok
from pii_anonymizer.swiss import inject_all
from pii_anonymizer.swiss_training import TEST_SEED, check_disjoint, inject_share, main

TEXT = "Anna Muster, AVS 1 69 01 75895 374 66, tel. +33 6 12 34 56 78, IBAN: DE12 3456, Bern"


def _entity(text, value, label):
    start = text.index(value)
    return {"start": start, "end": start + len(value), "label": label}


def _record(i):
    return {
        "id": f"train-{i}",
        "text": TEXT,
        "lang": "fr",
        "entities": [
            _entity(TEXT, "Anna", "GIVENNAME"),
            _entity(TEXT, "1 69 01 75895 374 66", "SOCIALNUM"),
            _entity(TEXT, "+33 6 12 34 56 78", "TELEPHONENUM"),
            _entity(TEXT, "IBAN: DE12 3456", "iban"),
            _entity(TEXT, "Bern", "CITY"),
        ],
    }


PLAIN = {"id": "plain", "text": "Anna", "entities": [{"start": 0, "end": 4, "label": "GIVENNAME"}]}
ROWS = [_record(i) for i in range(1000)]


def _values(record):
    return [record["text"][e["start"] : e["end"]] for e in record["entities"]]


def test_every_row_is_kept_in_order():
    out = inject_share([*ROWS, PLAIN], share=0.2, seed=1)
    assert [r["id"].removesuffix("-ch") for r in out] == [r["id"] for r in ROWS] + ["plain"]
    assert out[-1] == PLAIN


def test_about_the_share_of_eligible_rows_gets_swiss_values():
    out = inject_share(ROWS, share=0.2, seed=1)
    swiss = sum(r["id"].endswith("-ch") for r in out)
    assert 150 < swiss < 250
    assert inject_share(ROWS, share=0, seed=1) == ROWS
    assert all(r["id"].endswith("-ch") for r in inject_share(ROWS, share=1, seed=1))


def test_labels_and_offsets_stay_right():
    for out in inject_share(ROWS, share=0.5, seed=1):
        values = _values(out)
        assert values[0] == "Anna" and values[4] == "Bern"
        labels = [e["label"] for e in out["entities"]]
        if out["id"].endswith("-ch"):
            assert labels == ["GIVENNAME", "AVS", "PHONE", "IBAN", "CITY"]
            assert ean13_ok(re.sub(r"[ .-]", "", values[1]))
            assert iban_ok(values[3])
        else:
            assert out == ROWS[int(out["id"].split("-")[1])]


def test_same_seed_same_rows_and_other_seed_other_rows():
    assert inject_share(ROWS, seed=1) == inject_share(ROWS, seed=1)
    assert inject_share(ROWS, seed=1) != inject_share(ROWS, seed=2)


def test_training_values_differ_from_the_test_values():
    test = {r["id"]: r["text"] for r in inject_all(ROWS[:50], seed=TEST_SEED)}
    train = inject_share(ROWS[:50], share=1, seed=1)
    assert all(r["text"] != test[r["id"]] for r in train)


def test_the_test_seed_is_refused():
    with pytest.raises(ValueError, match="test set"):
        inject_share(ROWS, seed=TEST_SEED)
    with pytest.raises(ValueError, match="share"):
        inject_share(ROWS, share=1.5, seed=1)


def test_a_row_shared_with_a_test_set_is_refused():
    test_swiss = inject_all([_record(7)], seed=TEST_SEED)
    with pytest.raises(ValueError, match="1 training rows"):
        check_disjoint(ROWS, [test_swiss])  # same source id, other text
    other_id = {**_record(0), "id": "t1-x"}
    with pytest.raises(ValueError, match="training rows"):
        check_disjoint(ROWS[:1], [[other_id]])  # same text, other id
    check_disjoint(ROWS[:1], [[PLAIN]])


def test_command_line(tmp_path):
    source = tmp_path / "train.jsonl"
    source.write_text("".join(json.dumps(r) + "\n" for r in ROWS[:20]), encoding="utf-8")
    test = tmp_path / "test.jsonl"
    test.write_text(json.dumps(PLAIN) + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    main([str(source), str(out), "--exclude", str(test), "--share", "1"])
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 20 and all(r["id"].endswith("-ch") for r in rows)

    test.write_text(json.dumps(ROWS[3]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        main([str(source), str(out), "--exclude", str(test)])


def test_rows_are_independent_of_each_other():
    alone = inject_share([ROWS[5]], share=0.5, seed=1)
    together = inject_share(ROWS[:10], share=0.5, seed=1)
    assert alone[0] == together[5]
