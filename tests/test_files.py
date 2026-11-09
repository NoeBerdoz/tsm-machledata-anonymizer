from io import BytesIO

from docx import Document

from pii_anonymizer.files import read_text

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
