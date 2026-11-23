"""Compile inline T2 marks into text and character spans."""

import argparse
import json
import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from pii_anonymizer.spans import SWISS_KINDS

FILE_SOURCES = ("pdf", "docx")
SOURCES = ("prompt", "email", "csv", "txt", *FILE_SOURCES)
_LANGUAGES = ("fr", "de", "it", "en")
_BRACKET = re.compile("[⟦⟧]")
_LABEL = r"[A-Za-z][A-Za-z0-9_-]*"
_LITERAL = re.compile(rf"({_LABEL})(?:@([A-Z]+))?")
_SLOT = re.compile(rf"@([A-Z]+)(?:/([a-z0-9_]+))?:({_LABEL})")
SLOT_NAME = r"[A-Za-z0-9_-]+"

type SlotResolver = Callable[[str, str | None, str], str]


def read_rows(path: Path) -> Iterator[tuple[str, dict]]:
    """Read JSONL rows with a location suitable for reporting authoring errors."""
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            location = f"{path}, line {line_number}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{location}: {error.msg} at column {error.colno}") from error
            if not isinstance(row, dict):
                raise ValueError(f"{location}: expected a JSON object")
            if "id" in row:
                location += f", row {row['id']!r}"
            yield location, row


def check_filename(source: str, filename: object) -> None:
    if source not in FILE_SOURCES:
        if filename is not None:
            raise ValueError("filename is only for PDF and DOCX rows")
        return
    if not isinstance(filename, str) or "\\" in filename or ":" in filename or "\x00" in filename:
        raise ValueError(f"expected a relative .{source} filename")
    path = PurePosixPath(filename)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != f".{source}":
        raise ValueError(f"expected a relative .{source} filename, got {filename!r}")


def read_marked(inputs: Sequence[Path], kind: str, output: Path) -> Iterator[tuple[str, dict]]:
    seen = set()
    for path in inputs:
        if path.resolve() == output.resolve():
            raise ValueError(f"output aliases input: {path}")
        for location, row in read_rows(path):
            try:
                for key in ("id", "group"):
                    if not isinstance(row.get(key), str) or not row[key].strip():
                        raise ValueError(f"{key} must be a nonempty string")
                if row.get("kind") != kind:
                    raise ValueError(f"expected kind {kind!r}")
                if row.get("lang") not in _LANGUAGES or row.get("source") not in SOURCES:
                    raise ValueError("expected a T2 language and source")
                if not isinstance(row.get("marked_text"), str):
                    raise ValueError("marked_text must be a string")
                check_filename(row["source"], row.get("filename"))
                if row["id"] in seen:
                    raise ValueError(f"duplicate id {row['id']!r}")
            except ValueError as error:
                raise ValueError(f"{location}: {error}") from error
            seen.add(row["id"])
            yield location, row


def _read_mark(mark: str, resolve_slot: SlotResolver | None) -> tuple[str, str | None, str]:
    header, separator, value = mark.partition("|")
    if not separator:
        raise ValueError("expected '|' after the mark header")
    if not value.strip():
        raise ValueError("nonempty value required")
    if header.startswith("@"):
        if resolve_slot is None:
            raise ValueError("Swiss slots require template mode")
        slot = _SLOT.fullmatch(header)
        if not slot or slot[1] not in SWISS_KINDS or not re.fullmatch(SLOT_NAME, value):
            raise ValueError(f"invalid Swiss slot {mark!r}")
        swiss, style, label = slot.groups()
        return label, swiss, resolve_slot(swiss, style, value)
    literal = _LITERAL.fullmatch(header)
    if not literal or (literal[2] is not None and literal[2] not in SWISS_KINDS):
        raise ValueError(f"invalid mark header {header!r}")
    label, swiss = literal.groups()
    return label, swiss, value


def compile_row(row: Mapping, location: str, resolve_slot: SlotResolver | None = None) -> dict:
    """Remove marks while counting code points in the text that will be written."""
    marked = row["marked_text"]
    pieces = []
    entities = []
    cursor = length = 0
    brackets = iter(_BRACKET.finditer(marked))
    for opening in brackets:
        try:
            if opening[0] == "⟧":
                raise ValueError("stray closing bracket")
            closing = next(brackets, None)
            if closing is None:
                raise ValueError("unclosed mark")
            if closing[0] == "⟦":
                raise ValueError("nested or unclosed mark")
            label, swiss, value = _read_mark(marked[opening.end() : closing.start()], resolve_slot)
        except ValueError as error:
            raise ValueError(f"{location}, character {opening.start() + 1}: {error}") from error
        plain = marked[cursor : opening.start()]
        start = length + len(plain)
        length = start + len(value)
        entity = {"start": start, "end": length, "label": label}
        if swiss is not None:
            entity["swiss"] = swiss
        entities.append(entity)
        pieces.extend((plain, value))
        cursor = closing.end()
    pieces.append(marked[cursor:])
    result = {
        "id": row["id"],
        "text": "".join(pieces),
        "entities": entities,
        "lang": row["lang"],
        "source": row["source"],
        "kind": row["kind"],
        "group": row["group"],
    }
    if row.get("filename") is not None:
        result["filename"] = row["filename"]
    return result


def write_dataset(
    output: Path, rows: Iterable[Mapping], documents: Mapping[Path, bytes] | None = None
) -> None:
    """Stage the batch and publish the JSONL after its documents are in place."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".t2-") as directory:
        stage = Path(directory)
        dataset = stage / "dataset.jsonl"
        with dataset.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        staged = []
        for index, (path, data) in enumerate((documents or {}).items()):
            temporary = stage / f"document-{index}"
            temporary.write_bytes(data)
            staged.append((temporary, path))
        for temporary, path in staged:
            temporary.replace(path)
        dataset.replace(output)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="compile marked realistic JSONL")
    build.add_argument("input", type=Path)
    build.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        rows = [
            compile_row(row, location)
            for location, row in read_marked([args.input], "realistic", args.output)
        ]
        write_dataset(args.output, rows)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
