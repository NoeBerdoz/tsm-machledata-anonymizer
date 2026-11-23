"""Build DOCX layouts and verify the exact text of T2 attachments."""

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from docx import Document
from pypdf.errors import PyPdfError

from pii_anonymizer.files import read_text
from pii_anonymizer.t2_marking import FILE_SOURCES, SLOT_NAME, SOURCES, check_filename, read_rows

_DOCX_SLOT = re.compile(rf"\{{\{{({SLOT_NAME})\}}\}}")
_TYPST_PROBE = re.compile(r"PROBE_[A-Za-z0-9_-]*", re.IGNORECASE)


def render_docx(layout: Path, slots: Mapping[str, str] | None = None) -> bytes:
    """Render an ordered JSON array of paragraphs and rectangular tables."""
    blocks = json.loads(layout.read_text(encoding="utf-8"))
    if not isinstance(blocks, list) or not blocks:
        raise ValueError(f"{layout}: expected a nonempty array of paragraphs and tables")

    def fill(text: str) -> str:
        if slots is None:
            return text
        try:
            return _DOCX_SLOT.sub(lambda match: slots[match[1]], text)
        except KeyError as error:
            raise ValueError(f"{layout}: unknown DOCX slot {error.args[0]!r}") from error

    document = Document()
    for number, block in enumerate(blocks, start=1):
        if isinstance(block, str):
            document.add_paragraph(fill(block))
            continue
        if not isinstance(block, dict) or set(block) != {"table"}:
            raise ValueError(f"{layout}, block {number}: expected a paragraph or a table")
        rows = block["table"]
        if (
            not isinstance(rows, list)
            or not rows
            or not isinstance(rows[0], list)
            or not rows[0]
            or any(
                not isinstance(row, list)
                or len(row) != len(rows[0])
                or any(not isinstance(value, str) for value in row)
                for row in rows
            )
        ):
            raise ValueError(f"{layout}, block {number}: expected a rectangular table of strings")
        table = document.add_table(rows=len(rows), cols=len(rows[0]))
        for row, values in zip(table.rows, rows, strict=True):
            for cell, value in zip(row.cells, values, strict=True):
                cell.text = fill(value)

    buffer = BytesIO()
    document.save(buffer)
    # Stable ZIP entry timestamps keep a rebuild of the same layout identical.
    output = BytesIO()
    with ZipFile(buffer) as original, ZipFile(output, "w") as fixed:
        for name in sorted(original.namelist()):
            entry = ZipInfo(name)
            entry.create_system = 0
            fixed.writestr(entry, original.read(name), compress_type=ZIP_DEFLATED)
    return output.getvalue()


def render_pdf(layout: Path, slots: Mapping[str, str]) -> bytes:
    command = [
        "typst",
        "compile",
        "--format",
        "pdf",
        "--ignore-system-fonts",
        "--creation-timestamp",
        "0",
    ]
    for name, value in slots.items():
        command.extend(("--input", f"{name}={value}"))
    try:
        return subprocess.run([*command, str(layout), "-"], check=True, capture_output=True).stdout
    except FileNotFoundError as error:
        raise ValueError("Install the typst CLI to render PDF templates.") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"{layout}: {detail}") from error


def _extract(filename: str, data: bytes) -> str:
    try:
        return read_text(filename, data)
    except (BadZipFile, PyPdfError) as error:
        raise ValueError(f"{filename}: cannot extract text: {error}") from error


def check_extraction(filename: str, data: bytes, expected: str) -> None:
    actual = _extract(filename, data)
    if Path(filename).suffix.lower() == ".pdf" and (probe := _TYPST_PROBE.search(actual)):
        raise ValueError(f"{filename}: unresolved Typst draft probe {probe[0]!r}")
    if actual != expected:
        position = next(
            (i for i, pair in enumerate(zip(expected, actual, strict=False)) if pair[0] != pair[1]),
            min(len(expected), len(actual)),
        )
        expected_excerpt = expected[position : position + 24]
        actual_excerpt = actual[position : position + 24]
        raise ValueError(
            f"{filename}: extracted text differs at character {position + 1}: "
            f"expected {expected_excerpt!r}, got {actual_excerpt!r}"
        )


def verify(dataset: Path) -> int:
    root = dataset.parent.resolve()
    checked = 0
    for location, row in read_rows(dataset):
        try:
            source = row.get("source")
            filename = row.get("filename")
            if source not in SOURCES:
                raise ValueError("expected a T2 source")
            check_filename(source, filename)
            if source not in FILE_SOURCES:
                continue
            path = (root / filename).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f"{filename}: file is outside the dataset directory")
            if not isinstance(row.get("text"), str):
                raise ValueError("text must be a string")
            check_extraction(filename, path.read_bytes(), row["text"])
        except (OSError, ValueError) as error:
            raise ValueError(f"{location}: {error}") from error
        checked += 1
    return checked


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    docx = commands.add_parser("docx", help="render a DOCX layout")
    docx.add_argument("layout", type=Path)
    docx.add_argument("output", type=Path)
    extract = commands.add_parser("extract", help="write the app's extracted text to stdout")
    extract.add_argument("file", type=Path)
    check = commands.add_parser("verify", help="check the document rows in a JSONL")
    check.add_argument("dataset", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "docx":
            check_filename("docx", args.output.name)
            if args.output.resolve() == args.layout.resolve():
                raise ValueError("output aliases the DOCX layout")
            data = render_docx(args.layout)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(data)
        elif args.command == "extract":
            check_filename(args.file.suffix.lower().lstrip("."), args.file.name)
            text = _extract(args.file.name, args.file.read_bytes())
            sys.stdout.buffer.write(text.encode("utf-8"))
        else:
            print(f"{args.dataset}: verified {verify(args.dataset)} file rows")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
