"""Read the text of the files that the user attaches."""

from io import BytesIO
from pathlib import Path

from docx import Document
from docx.table import Table
from pypdf import PdfReader

FILE_TYPES = ["pdf", "txt", "docx", "csv"]


def _read_docx(data: bytes) -> str:
    lines = []
    for block in Document(BytesIO(data)).iter_inner_content():
        if isinstance(block, Table):
            lines += ["\t".join(cell.text for cell in row.cells) for row in block.rows]
        else:
            lines.append(block.text)
    return "\n".join(lines)


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")  # what Excel writes on Windows


def read_text(name: str, data: bytes) -> str:
    """Return the text of a PDF, DOCX, TXT or CSV file."""
    extension = Path(name).suffix.lower()
    if extension == ".pdf":
        return "\n".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages)
    if extension == ".docx":
        return _read_docx(data)
    return _decode(data)
