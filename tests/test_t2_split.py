import json

import pytest

from pii_anonymizer.t2_split import main, review_sample, split


def records():
    """80 realistic snippets (some sharing a group) and 40 templates of 3 variants."""
    rows = []
    for i in range(80):
        rows.append(
            {
                "id": f"t2-r{i:03d}",
                "group": f"r{i // 2 if i < 20 else i}",  # the first 20 come in pairs
                "kind": "realistic",
                "source": ("prompt", "email", "pdf", "docx", "csv", "txt")[i % 6],
                "lang": ("fr", "de", "it", "en")[i % 4],
            }
        )
    for t in range(40):
        for seed in range(3):
            rows.append(
                {
                    "id": f"t2-p{t:02d}-{seed}",
                    "group": f"p{t}",
                    "kind": "planted",
                    "source": ("prompt", "pdf", "csv")[t % 3],
                    "lang": ("fr", "de", "it", "en")[t % 4],
                }
            )
    return rows


def test_no_group_is_on_both_sides_and_every_snippet_is_kept_once():
    rows = records()
    dev, final = split(rows)
    assert not {r["group"] for r in dev} & {r["group"] for r in final}
    assert sorted(r["id"] for r in dev + final) == sorted(r["id"] for r in rows)


def test_each_side_gets_half_of_the_snippets():
    dev, final = split(records())
    assert abs(len(dev) - len(final)) <= 3  # one template's variants


def test_split_is_seeded_and_ignores_the_file_order():
    rows = records()
    dev, _ = split(rows)
    assert dev == split(rows)[0]
    assert {r["id"] for r in dev} == {r["id"] for r in split(rows[::-1])[0]}
    assert dev != split(rows, seed=0)[0]


def test_review_sample_draws_24_units_and_keeps_templates_whole():
    rows = records()
    sample = review_sample(rows)
    assert sample == review_sample(rows[::-1])
    assert len(sample) == len(set(sample)) == 24
    groups = {r["group"] for r in rows if r["kind"] == "planted"}
    ids = {r["id"] for r in rows if r["kind"] == "realistic"}
    assert set(sample) <= groups | ids


def test_main_writes_both_sides(tmp_path, capsys):
    t2 = tmp_path / "t2.jsonl"
    t2.write_text("".join(json.dumps(r) + "\n" for r in records()), encoding="utf-8")
    main([str(t2), str(tmp_path / "dev.jsonl"), str(tmp_path / "final.jsonl")])
    assert "| **total** | " in capsys.readouterr().out
    lines = (tmp_path / "dev.jsonl").read_text().splitlines()
    lines += (tmp_path / "final.jsonl").read_text().splitlines()
    assert len(lines) == 200


def test_main_refuses_to_overwrite_its_input(tmp_path):
    t2 = tmp_path / "t2.jsonl"
    t2.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(t2), str(t2), str(tmp_path / "final.jsonl")])
