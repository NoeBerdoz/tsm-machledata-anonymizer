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
    dev, final = split(rows)
    assert (dev, final) == split(rows) == split(rows[::-1])
    assert [r["id"] for r in dev] == sorted(r["id"] for r in dev)
    assert dev != split(rows, seed=0)[0]


def test_review_sample_draws_24_units_and_keeps_templates_whole():
    rows = records()
    sample = review_sample(rows)
    assert sample == review_sample(rows[::-1])
    assert len(sample) == len(set(sample)) == 24
    groups = {r["group"] for r in rows if r["kind"] == "planted"}
    ids = {r["id"] for r in rows if r["kind"] == "realistic"}
    assert set(sample) <= groups | ids


def write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return str(path)


def three_files(tmp_path):
    """The fixture as #57, #58 and #59 write it: realistic, files and planted."""
    rows = records()
    return [
        write(tmp_path / "realistic.jsonl", rows[:60]),
        write(tmp_path / "files.jsonl", rows[60:80]),
        write(tmp_path / "planted.jsonl", rows[80:]),
    ]


def test_main_splits_several_files_the_same_way_in_any_order(tmp_path, capsys):
    inputs = three_files(tmp_path)
    outputs = []
    for order in (inputs, inputs[::-1]):
        dev, final = tmp_path / "dev.jsonl", tmp_path / "final.jsonl"
        main([*order, "--dev", str(dev), "--final", str(final)])
        outputs.append((dev.read_bytes(), final.read_bytes()))
    assert "| **total** | " in capsys.readouterr().out
    assert outputs[0] == outputs[1]
    assert sum(len(side.splitlines()) for side in outputs[0]) == 200


def test_main_reviews_several_files(tmp_path, capsys):
    main([*three_files(tmp_path), "--review"])
    assert capsys.readouterr().out.splitlines() == review_sample(records())


def test_main_refuses_an_id_in_two_files(tmp_path, capsys):
    inputs = three_files(tmp_path)
    with pytest.raises(SystemExit):
        main([*inputs, inputs[0], "--review"])
    assert "appear more than once" in capsys.readouterr().err


def test_main_refuses_to_overwrite_its_input(tmp_path):
    inputs = three_files(tmp_path)
    with pytest.raises(SystemExit):
        main([*inputs, "--dev", inputs[1], "--final", str(tmp_path / "final.jsonl")])
