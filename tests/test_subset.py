from collections import Counter

import pytest

from pii_anonymizer.subset import main, read_jsonl, stratified


def records(per_language):
    return [
        {"id": f"{lang}-{i}", "lang": lang, "text": "x", "entities": []}
        for i in range(per_language)
        for lang in ("fr", "de", "it", "en")
    ]


def test_subset_has_the_same_number_of_texts_per_language():
    subset = stratified(records(20), per_language=5)
    assert Counter(r["lang"] for r in subset) == {"fr": 5, "de": 5, "it": 5, "en": 5}


def test_subset_is_seeded_and_keeps_the_file_order():
    rows = records(20)
    first = stratified(rows, per_language=5, seed=1)
    assert first == stratified(rows, per_language=5, seed=1)
    assert first != stratified(rows, per_language=5, seed=2)
    positions = [rows.index(r) for r in first]
    assert positions == sorted(positions)


def test_subset_refuses_a_language_with_too_few_texts():
    with pytest.raises(ValueError, match="only 3"):
        stratified(records(3), per_language=5)


def test_command_writes_the_subset(tmp_path):
    source = tmp_path / "set.jsonl"
    source.write_text(
        "".join(f'{{"id": "{r["id"]}", "lang": "{r["lang"]}"}}\n' for r in records(60))
    )
    out = tmp_path / "set-200.jsonl"
    main([str(source), str(out)])
    assert len(read_jsonl(out)) == 200
