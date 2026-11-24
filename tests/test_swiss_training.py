import json
import re
from hashlib import sha256

import pytest

from pii_anonymizer.rules import ean13_ok, iban_ok
from pii_anonymizer.swiss import inject_all
from pii_anonymizer.swiss_training import check_disjoint, inject_share, main
from pii_anonymizer.t2_holdout import Holdout, source_id
from pii_anonymizer.t2_holdout import main as freeze_holdout

TEXT = "Anna Muster, AVS 1 69 01 75895 374 66, tel. +33 6 12 34 56 78, IBAN: DE12 3456, Bern"


def test_holdout_normalizes_t2_variants_to_the_base_id():
    variants = [{"id": f"t2-0021-s{seed}-ch", "text": f"variant {seed}"} for seed in range(3)]
    holdout = Holdout.from_records(variants)
    assert holdout.source_ids == {"t2-0021"}
    assert len(holdout.text_sha256) == 3
    with pytest.raises(ValueError, match="also test rows"):
        holdout.check_disjoint([{"id": "t2-0021", "text": "another text"}])
    assert source_id("public-s0-ch-ch") == "public-s0"
    assert source_id("t2-0021-s3-ch") == "t2-0021-s3"
    assert source_id("t2-0021-s0") == "t2-0021-s0"


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
    out = inject_share([*ROWS, PLAIN], share=0.2)
    assert [r["id"].removesuffix("-ch") for r in out] == [r["id"] for r in ROWS] + ["plain"]
    assert out[-1] == PLAIN


def test_about_the_share_of_eligible_rows_gets_swiss_values():
    out = inject_share(ROWS, share=0.2)
    swiss = sum(r["id"].endswith("-ch") for r in out)
    assert 150 < swiss < 250
    assert inject_share(ROWS, share=0) == ROWS
    assert all(r["id"].endswith("-ch") for r in inject_share(ROWS, share=1))


def test_labels_and_offsets_stay_right():
    for out in inject_share(ROWS, share=0.5):
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
    assert inject_share(ROWS) == inject_share(ROWS, seed=3)
    assert inject_share(ROWS, seed=3) != inject_share(ROWS, seed=4)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_training_values_differ_from_the_test_values(seed):
    test = {r["id"]: r["text"] for r in inject_all(ROWS[:50], seed=seed)}
    train = inject_share(ROWS[:50], share=1)
    assert all(r["text"] != test[r["id"]] for r in train)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_the_test_seeds_are_refused(seed):
    with pytest.raises(ValueError, match="test set"):
        inject_share(ROWS, seed=seed)


def test_invalid_share_is_refused():
    with pytest.raises(ValueError, match="share"):
        inject_share(ROWS, share=1.5)


def test_a_row_shared_with_a_test_set_is_refused():
    test_swiss = inject_all([_record(7)], seed=0)
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
    alone = inject_share([ROWS[5]], share=0.5)
    together = inject_share(ROWS[:10], share=0.5)
    assert alone[0] == together[5]


def _write_rows(path, *records):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), "utf-8")


def test_frozen_manifest_can_be_used_with_raw_exclusions(tmp_path):
    final, manifest = tmp_path / "t2-final.jsonl", tmp_path / "holdout.json"
    source, output, t1 = (tmp_path / name for name in ("train.jsonl", "out.jsonl", "t1.jsonl"))
    final_text = "Données privées\n"
    final_rows = [
        {"id": "z-ch-ch", "text": final_text, "entities": []},
        {"id": "a", "text": final_text, "entities": []},
        {"id": "z-ch", "text": final_text, "entities": []},
    ]
    _write_rows(final, *final_rows)
    freeze_holdout([str(final), str(manifest)])
    first = manifest.read_bytes()
    assert json.loads(first) == {
        "source_ids": ["a", "z"],
        "text_sha256": [sha256(final_text.encode("utf-8")).hexdigest()],
    }
    _write_rows(final, *reversed(final_rows))
    freeze_holdout([str(final), str(manifest)])
    assert manifest.read_bytes() == first
    final.unlink()

    _write_rows(source, ROWS[0])
    _write_rows(t1, PLAIN)
    args = [str(source), str(output), "--exclude-manifest", str(manifest)]
    main(args + ["--exclude", str(t1)])
    assert json.loads(output.read_text("utf-8")) == inject_share(ROWS[:1])[0]

    _write_rows(t1, ROWS[0])
    with pytest.raises(ValueError, match="also test rows"):
        main(args + ["--exclude", str(t1)])


def _aliased_output(path, kind):
    if kind == "direct":
        return path
    output = path.with_name("alias.jsonl")
    if kind == "symlink":
        output.symlink_to(path)
    else:
        output.hardlink_to(path)
    return output


@pytest.mark.parametrize("kind", ["direct", "symlink", "hardlink"])
@pytest.mark.parametrize("target", ["source", "raw", "manifest"])
def test_training_output_cannot_alias_an_input(tmp_path, capsys, kind, target):
    source = tmp_path / "train.jsonl"
    extra_source = tmp_path / "extra-train.jsonl"
    raw = tmp_path / "test.jsonl"
    extra_raw = tmp_path / "extra-test.jsonl"
    manifest = tmp_path / "holdout.json"
    final = tmp_path / "t2-final.jsonl"
    _write_rows(source, ROWS[0])
    _write_rows(extra_source, ROWS[1])
    _write_rows(raw, PLAIN)
    _write_rows(extra_raw, {**PLAIN, "id": "extra-test"})
    _write_rows(final, {**PLAIN, "id": "final"})
    freeze_holdout([str(final), str(manifest)])
    protected = {"source": extra_source, "raw": extra_raw, "manifest": manifest}[target]
    output = _aliased_output(protected, kind)
    original = protected.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(source),
                str(extra_source),
                str(output),
                "--exclude",
                str(raw),
                "--exclude",
                str(extra_raw),
                "--exclude-manifest",
                str(manifest),
            ]
        )
    assert exc.value.code == 2
    assert "output aliases input" in capsys.readouterr().err
    assert protected.read_bytes() == output.read_bytes() == original


@pytest.mark.parametrize("kind", ["direct", "symlink", "hardlink"])
def test_freeze_output_cannot_alias_final(tmp_path, capsys, kind):
    final = tmp_path / "t2-final.jsonl"
    _write_rows(final, PLAIN)
    output = _aliased_output(final, kind)
    original = final.read_bytes()
    with pytest.raises(SystemExit) as exc:
        freeze_holdout([str(final), str(output)])
    assert exc.value.code == 2
    assert "output aliases input" in capsys.readouterr().err
    assert final.read_bytes() == output.read_bytes() == original


def test_freeze_does_not_export_empty_manifest(tmp_path):
    final, manifest = tmp_path / "t2-final.jsonl", tmp_path / "holdout.json"
    _write_rows(final)
    with pytest.raises(SystemExit) as exc:
        freeze_holdout([str(final), str(manifest)])
    assert exc.value.code == 2
    assert not manifest.exists()


@pytest.mark.parametrize("collision", ["source id", "source text", "emitted text"])
@pytest.mark.parametrize("exclusion", ["raw", "manifest"])
def test_overlap_leaves_output_untouched(tmp_path, collision, exclusion):
    source, output = tmp_path / "train.jsonl", tmp_path / "out.jsonl"
    test, manifest = tmp_path / "test.jsonl", tmp_path / "holdout.json"
    row = ROWS[0]
    emitted = inject_share([row], share=1)[0]
    held_out = {
        "source id": {**PLAIN, "id": f"{row['id']}-ch-ch"},
        "source text": {**row, "id": "other"},
        "emitted text": {**emitted, "id": "other"},
    }[collision]
    _write_rows(source, row)
    _write_rows(test, held_out)
    flags = ["--exclude", str(test)]
    if exclusion == "manifest":
        freeze_holdout([str(test), str(manifest)])
        test.unlink()
        flags = ["--exclude-manifest", str(manifest)]
    args = [str(source), str(output), "--share", "1", *flags]

    with pytest.raises(ValueError, match="also test rows"):
        main(args)
    assert not output.exists()
    output.write_text("existing output\n", "utf-8")
    with pytest.raises(ValueError, match="also test rows"):
        main(args)
    assert output.read_text("utf-8") == "existing output\n"


def test_cli_refuses_raw_final_before_reading_it(tmp_path, capsys):
    source, output = tmp_path / "train.jsonl", tmp_path / "out.jsonl"
    final = tmp_path / "t2-final.jsonl"
    alias = tmp_path / "renamed.jsonl"
    alias.symlink_to(final)
    for path in (final, alias):
        with pytest.raises(SystemExit) as exc:
            main([str(source), str(output), "--exclude", str(path)])
        assert exc.value.code == 2
        assert "supply --exclude-manifest" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize(
    "manifest",
    [
        PLAIN,
        {"source_ids": [], "text_sha256": []},
        {"source_ids": ["held-out-ch"], "text_sha256": ["0" * 64]},
        {"source_ids": ["held-out"], "text_sha256": ["invalid"]},
    ],
)
def test_cli_rejects_invalid_manifest_before_writing(tmp_path, manifest):
    source, output, path = (
        tmp_path / name for name in ("train.jsonl", "out.jsonl", "holdout.json")
    )
    _write_rows(source, ROWS[0])
    path.write_text(json.dumps(manifest), "utf-8")
    with pytest.raises(ValueError, match="expected"):
        main([str(source), str(output), "--exclude-manifest", str(path)])
    assert not output.exists()
