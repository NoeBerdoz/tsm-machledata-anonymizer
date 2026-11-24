import json
import re
from collections import defaultdict

import pytest

from pii_anonymizer import swiss, t2_marking
from pii_anonymizer.rules import ean13_ok, find_phone, iban_ok
from pii_anonymizer.spans import load_dataset


def _write_rows(path, *rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _row(marked_text, *, id="t2-0061", kind="realistic", source="prompt"):
    return {
        "id": id,
        "marked_text": marked_text,
        "lang": "fr",
        "source": source,
        "kind": kind,
        "group": f"case-{id}",
    }


@pytest.mark.parametrize(
    ("marked", "plain", "values", "source"),
    [
        (
            '📎 Résume {"name":"⟦full_name|Élise Exemple⟧","note":"a\\\\b"}\r\n',
            '📎 Résume {"name":"Élise Exemple","note":"a\\\\b"}\r\n',
            ["Élise Exemple"],
            "prompt",
        ),
        (
            'C-001,"⟦full_name|E\u0301lise⟧","⟦email|elise@example.invalid⟧"\n',
            'C-001,"E\u0301lise","elise@example.invalid"\n',
            ["E\u0301lise", "elise@example.invalid"],
            "csv",
        ),
        (
            "SELECT '⟦username|case_user⟧';\n\tINFO [⟦username|case_user⟧] "
            'x = "⟦password|test|pipe⟧⟦test|!⟧"\t',
            "SELECT 'case_user';\n\tINFO [case_user] x = \"test|pipe!\"\t",
            ["case_user", "case_user", "test|pipe", "!"],
            "txt",
        ),
        (
            "Tél. ⟦PHONE|+41 79 123 45 67⟧",
            "Tél. +41 79 123 45 67",
            ["+41 79 123 45 67"],
            "prompt",
        ),
        (
            "Adresse ⟦street_address|Rue du Midi\n14⟧",
            "Adresse Rue du Midi\n14",
            ["Rue du Midi\n14"],
            "pdf",
        ),
    ],
)
def test_build_compiles_exact_text_and_code_point_offsets(tmp_path, marked, plain, values, source):
    author, output = tmp_path / "marked.jsonl", tmp_path / "rows.jsonl"
    row = _row(marked, source=source)
    if source == "pdf":
        row["filename"] = "letter.pdf"
    _write_rows(author, row)
    t2_marking.main(["build", str(author), str(output)])
    (example,) = load_dataset(output)
    assert example.text == plain
    assert example.lang == "fr"
    assert len(example.entities) == len(values)
    cursor = 0
    for entity, value in zip(example.entities, values, strict=True):
        start = plain.index(value, cursor)
        cursor = start + len(value)
        assert (entity.start, entity.end) == (start, cursor)
    if "⟦PHONE|" in marked:
        (entity,) = example.entities
        assert entity.label == "PHONE"
        assert set(swiss.read_jsonl(output)[0]["entities"][0]) == {"start", "end", "label"}


@pytest.mark.parametrize(
    ("marked", "error"),
    [
        ("⟧", "stray closing bracket"),
        ("⟦label|value", "unclosed mark"),
        ("⟦label|⟦label|value⟧⟧", "nested or unclosed mark"),
        ("⟦label|⟧", "nonempty value"),
        ("⟦label| value⟧", "marked values cannot start or end with whitespace"),
        ("⟦label|value\t⟧", "marked values cannot start or end with whitespace"),
        ("⟦phone_number@UNKNOWN|+41⟧", "invalid mark header"),
        ("⟦@AVS|worker⟧", "Swiss slots require template mode"),
    ],
)
def test_build_reports_location_and_keeps_previous_output(tmp_path, capsys, marked, error):
    author, output = tmp_path / "marked.jsonl", tmp_path / "rows.jsonl"
    _write_rows(author, _row("unchanged"), _row(f"😀{marked}", id="t2-0062"))
    output.write_text("previous output\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        t2_marking.main(["build", str(author), str(output)])
    assert f"{author}, line 2, row 't2-0062', character 2: {error}" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "previous output\n"


def test_build_rejects_duplicate_ids(tmp_path, capsys):
    author, output = tmp_path / "marked.jsonl", tmp_path / "rows.jsonl"
    _write_rows(author, _row("one"), _row("two"))
    with pytest.raises(SystemExit, match="2"):
        t2_marking.main(["build", str(author), str(output)])
    assert "line 2, row 't2-0061': duplicate id" in capsys.readouterr().err
    assert not output.exists()


def test_build_rejects_realistic_id_in_template_range(tmp_path, capsys):
    author, output = tmp_path / "marked.jsonl", tmp_path / "rows.jsonl"
    _write_rows(author, _row("realistic text", id="t2-0031"))
    with pytest.raises(SystemExit, match="2"):
        t2_marking.main(["build", str(author), str(output)])
    assert "row 't2-0031': realistic IDs must be in" in capsys.readouterr().err
    assert not output.exists()


def test_template_mode_writes_three_variants_for_each_of_40_templates(tmp_path):
    source, output = tmp_path / "templates.jsonl", tmp_path / "planted.jsonl"
    avs = "⟦@AVS/dashes|worker⟧"
    iban = "⟦@IBAN/lower|salary⟧"
    rows = [
        _row(
            f"Paie {avs}, compte {iban}, rappel {avs} pour ⟦full_name|Élise⟧. Tél. ⟦@PHONE|tel⟧",
            id=f"t2-{i:04}",
            kind="planted",
        )
        for i in range(21, 61)
    ]
    _write_rows(source, *rows)
    args = [str(source), str(output), "--template-slots"]
    swiss.main(args)
    before = output.read_bytes()
    examples = load_dataset(output)
    assert len(examples) == len({example.id for example in examples}) == 120
    seeds_by_template = defaultdict(list)
    for row, example in zip(swiss.read_jsonl(output), examples, strict=True):
        base_id, _, seed = example.id.removesuffix("-ch").rpartition("-s")
        seeds_by_template[base_id].append(int(seed))
        assert row["group"] == f"case-{base_id}"
        assert row["kind"] == "planted"
        assert [entity.label for entity in example.entities] == [
            "AVS",
            "IBAN",
            "AVS",
            "full_name",
            "PHONE",
        ]
        assert all(set(entity) == {"start", "end", "label"} for entity in row["entities"])
        avs_value, iban_value, repeated, name, phone = [
            example.text[entity.start : entity.end] for entity in example.entities
        ]
        assert name == "Élise"
        assert repeated == avs_value
        assert re.fullmatch(r"756-\d{4}-\d{4}-\d{2}", avs_value)
        assert ean13_ok(avs_value.replace("-", ""))
        assert iban_value.startswith(("ch", "li")) and iban_ok(iban_value)
        assert len(find_phone(phone)) == 1
    assert seeds_by_template == {row["id"]: [0, 1, 2] for row in rows}
    assert len({example.text for example in examples[:3]}) == 3
    swiss.main(args)
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    ("marked", "error"),
    [
        ("⟦full_name|Élise⟧", "expected at least one Swiss slot"),
        ("⟦@AVS/lower|worker⟧", "unknown AVS format"),
        ("⟦@AVS:national_id_number|worker⟧", "invalid Swiss slot"),
        (
            "⟦@AVS|worker⟧ ⟦@PHONE|worker⟧",
            "conflicting kind or format for slot 'worker'",
        ),
    ],
)
def test_template_mode_rejects_invalid_slots(tmp_path, capsys, marked, error):
    author, output = tmp_path / "templates.jsonl", tmp_path / "planted.jsonl"
    _write_rows(author, _row(marked, id="t2-0021", kind="planted"))
    with pytest.raises(SystemExit, match="2"):
        swiss.main([str(author), str(output), "--template-slots"])
    assert error in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize(
    ("base_id", "error"),
    [
        ("t2-0061", "template IDs must be in"),
        ("t2-0022", "more than one template uses group 'pair'"),
    ],
)
def test_template_mode_rejects_reserved_ids_or_shared_groups(tmp_path, capsys, base_id, error):
    author, output = tmp_path / "templates.jsonl", tmp_path / "planted.jsonl"
    first = {**_row("⟦@AVS|worker⟧", id="t2-0021", kind="planted"), "group": "pair"}
    _write_rows(author, first, {**first, "id": base_id})
    with pytest.raises(SystemExit, match="2"):
        swiss.main([str(author), str(output), "--template-slots"])
    assert f"row {base_id!r}: {error}" in capsys.readouterr().err
    assert not output.exists()
