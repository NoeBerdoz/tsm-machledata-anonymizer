import json
from io import BytesIO

import pytest
from docx import Document

from pii_anonymizer import swiss, t2_files, t2_marking
from pii_anonymizer.files import read_text
from pii_anonymizer.spans import load_dataset

# The smallest PDF that pypdf can read: one page with one line of text.
PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R
/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 42>>stream
BT /F1 12 Tf 10 50 Td (Marie Dupont) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
trailer<</Root 1 0 R>>
startxref
0
%%EOF
"""


def test_reads_utf8_with_a_bom():
    assert read_text("a.txt", "﻿Genève".encode()) == "Genève"


def test_reads_a_windows_csv():
    assert read_text("a.CSV", "nom;ville\nMüller;Genève".encode("cp1252")).endswith("Genève")


def test_reads_docx_paragraphs_and_tables_in_order():
    document = Document()
    document.add_paragraph("Avant")
    document.add_table(rows=1, cols=2).rows[0].cells[0].text = "Marie Dupont"
    document.add_paragraph("Après")
    data = BytesIO()
    document.save(data)
    assert read_text("a.docx", data.getvalue()).split("\n") == ["Avant", "Marie Dupont\t", "Après"]


def test_reads_pdf():
    assert "Marie Dupont" in read_text("a.pdf", PDF)


def test_t2_file_round_trip_and_whitespace_mismatch(tmp_path, capsys):
    layout, document = tmp_path / "lease.json", tmp_path / "lease.docx"
    layout.write_text(
        json.dumps(["Contrat de bail", {"table": [["Locataire", "Élise Exemple"]]}, "Fin"]),
        encoding="utf-8",
    )
    t2_files.main(["docx", str(layout), str(document)])
    t2_files.main(["extract", str(document)])
    docx_text = capsys.readouterr().out
    assert docx_text == "Contrat de bail\nLocataire\tÉlise Exemple\nFin"

    pdf = tmp_path / "form.pdf"
    pdf.write_bytes(PDF)
    author, results = tmp_path / "marked.jsonl", tmp_path / "t2-files.jsonl"
    author_rows = [
        {
            "id": f"t2-{number:04}",
            "marked_text": text.replace(name, f"⟦full_name|{name}⟧"),
            "lang": "fr",
            "source": path.suffix[1:],
            "kind": "realistic",
            "group": f"case-{number}",
            "filename": path.name,
        }
        for number, (path, text, name) in enumerate(
            [
                (document, docx_text, "Élise Exemple"),
                (pdf, read_text(pdf.name, PDF), "Marie Dupont"),
            ],
            start=1,
        )
    ]
    author.write_text("".join(json.dumps(row) + "\n" for row in author_rows), encoding="utf-8")
    t2_marking.main(["build", str(author), str(results)])
    t2_files.main(["verify", str(results)])
    assert "verified 2 file rows" in capsys.readouterr().out
    assert len(load_dataset(results)) == 2

    rows = swiss.read_jsonl(results)
    rows[0]["text"] = rows[0]["text"].replace("\t", " ")
    results.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        t2_files.main(["verify", str(results)])
    error = capsys.readouterr().err
    assert "row 't2-0001': lease.docx: extracted text differs at character" in error


def test_planted_docx_renders_each_seed_and_keeps_batch_on_mismatch(tmp_path, capsys):
    assets = tmp_path / "assets"
    assets.mkdir()
    layout = assets / "t2-0023.json"
    layout.write_text(
        json.dumps(["Assurance", {"table": [["Compte", "{{refund}}"]]}]), encoding="utf-8"
    )
    author, output = tmp_path / "templates.jsonl", tmp_path / "planted.jsonl"
    row = {
        "id": "t2-0023",
        "marked_text": "Assurance\nCompte\t⟦@IBAN/lower|refund⟧",
        "lang": "fr",
        "source": "docx",
        "kind": "planted",
        "group": "insurance",
        "filename": "assets/t2-0023.docx",
    }
    author.write_text(json.dumps(row) + "\n", encoding="utf-8")
    args = [str(author), str(output), "--template-slots", "--assets-dir", str(assets)]
    swiss.main(args)
    assert t2_files.verify(output) == 3
    rows = swiss.read_jsonl(output)
    assert [item["filename"] for item in rows] == [
        f"assets/t2-0023-s{seed}-ch.docx" for seed in range(3)
    ]
    assert len({item["text"] for item in rows}) == 3
    snapshot = {path: path.read_bytes() for path in [output, *assets.glob("*.docx")]}
    swiss.main(args)
    assert all(path.read_bytes() == data for path, data in snapshot.items())

    row["marked_text"] += "\n"
    author.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        swiss.main(args)
    assert "t2-0023-s0-ch.docx: extracted text differs" in capsys.readouterr().err
    assert all(path.read_bytes() == data for path, data in snapshot.items())


@pytest.mark.parametrize("probe", ["PROBE_PHONE", "probe_iban"])
def test_pdf_verification_rejects_a_draft_probe_even_when_text_matches(tmp_path, capsys, probe):
    pdf = tmp_path / "form.pdf"
    data = PDF.replace(b"Marie Dupont", probe.encode("ascii").ljust(len(b"Marie Dupont")))
    pdf.write_bytes(data)
    extracted = read_text(pdf.name, data)
    assert probe in extracted
    dataset = tmp_path / "t2-planted.jsonl"
    row = {"id": "t2-0021-s0-ch", "source": "pdf", "filename": pdf.name, "text": extracted}
    dataset.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="2"):
        t2_files.main(["verify", str(dataset)])
    assert f"form.pdf: unresolved Typst draft probe {probe!r}" in capsys.readouterr().err
