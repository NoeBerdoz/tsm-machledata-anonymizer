"""The results files: one CSV row per (model, dataset), and a Markdown summary."""

import csv
from collections.abc import Sequence
from pathlib import Path

RESULT_COLUMNS = [
    "model",
    "dataset",
    "dataset_sha256",
    "runtime",
    "n_texts",
    "n_entities",
    "n_protected",
    "strict_recall",
    "char_precision",
    "size_bytes",
    "size_mb",
    "threads",
    "latency_inputs",
    "latency_calls",
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_p50_ms_per_100_words",
    "latency_p95_ms_per_100_words",
    "cpu",
    "os",
    "python",
    "date",
]

PER_TYPE_COLUMNS = ["model", "dataset", "label", "n_entities", "n_protected", "recall"]

# The CPU of the reference laptop (docs/benchmark-protocol.md), matched as a substring.
REFERENCE_CPU = "i5-1130G7"


def cell(value: object, digits: int = 4) -> str:
    """Write a value for the CSV. None becomes an empty cell, floats are rounded."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def replace_rows(
    path: Path,
    columns: Sequence[str],
    rows: Sequence[dict[str, str]],
    key: Sequence[str] = ("model", "dataset"),
) -> None:
    """Write the rows into the CSV, replacing the old rows with the same key.

    The other rows are kept, so each model can be rerun on its own.
    """

    def key_of(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(row.get(column, "") for column in key)

    new_keys = {key_of(row) for row in rows}
    kept = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            kept = [row for row in csv.DictReader(f) if key_of(row) not in new_keys]
    all_rows = sorted([*kept, *rows], key=key_of)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, restval="", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)


def summary_table(results_csv: Path) -> str:
    """Small Markdown tables with the main numbers, one table per CPU.

    Latency only compares within one machine, so each CPU gets its own table. The
    reference laptop comes first.
    """

    def percent(value: str) -> str:
        return f"{float(value) * 100:.1f} %" if value else ""

    by_cpu: dict[str, list[dict[str, str]]] = {}
    with open(results_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_cpu.setdefault(row.get("cpu") or "unknown", []).append(row)

    sections = []
    for cpu in sorted(by_cpu, key=lambda name: (REFERENCE_CPU not in name, name)):
        title = f"## {cpu} (reference)" if REFERENCE_CPU in cpu else f"## {cpu}"
        lines = [
            title,
            "",
            "| Model | Dataset | Strict recall | Char. precision | Size (MB) | p95 latency (ms) |",
            "|---|---|---|---|---|---|",
        ]
        for row in by_cpu[cpu]:
            lines.append(
                f"| {row['model']} | {row['dataset']} | {percent(row['strict_recall'])} "
                f"| {percent(row['char_precision'])} | {row['size_mb']} "
                f"| {row['latency_p95_ms']} |"
            )
        sections.append("\n".join(lines) + "\n")
    return "\n".join(sections)
