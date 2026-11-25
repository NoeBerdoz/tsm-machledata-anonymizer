from collections import Counter

import pytest

from pii_anonymizer.evaluate import read_ids
from pii_anonymizer.latency_sample import latency_ids, main

# The source mix of T2-dev: 24, 20, 16, 16, 16 and 8 snippets.
MIX = {"prompt": 24, "email": 20, "pdf": 16, "docx": 16, "csv": 16, "txt": 8}


def records():
    return [
        {"id": f"{source}-{i}", "source": source}
        for source, count in MIX.items()
        for i in range(count)
    ]


def test_sample_is_proportional_to_the_sources():
    ids = latency_ids(records())
    counts = Counter(i.split("-")[0] for i in ids)
    # 30 % of each source, the three .8 remainders round up
    assert counts == {"prompt": 7, "email": 6, "pdf": 5, "docx": 5, "csv": 5, "txt": 2}


def test_sample_is_seeded_and_keeps_the_file_order():
    rows = records()
    ids = latency_ids(rows, seed=1)
    assert ids == latency_ids(rows, seed=1)
    assert ids != latency_ids(rows, seed=2)
    order = [r["id"] for r in rows]
    assert [order.index(i) for i in ids] == sorted(order.index(i) for i in ids)


def test_sample_refuses_a_set_that_is_too_small():
    with pytest.raises(ValueError, match="only 10"):
        latency_ids(records()[:10])


def test_command_writes_a_commented_id_file(tmp_path):
    source = tmp_path / "t2-dev.jsonl"
    source.write_text(
        "".join(f'{{"id": "{r["id"]}", "source": "{r["source"]}"}}\n' for r in records())
    )
    out = tmp_path / "ids.txt"
    main([str(source), str(out)])
    assert out.read_text().startswith("#")
    assert len(read_ids(out)) == 30
