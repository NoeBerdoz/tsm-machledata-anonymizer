"""Evaluate one detector on one test set.

Usage:
    uv run python -m pii_anonymizer.evaluate <detector> <dataset.jsonl> <out_dir>

Writes results.csv, recall_per_type.csv and summary.md into <out_dir>.
See docs/evaluation.md.
"""

import argparse
import datetime
import hashlib
import platform
from collections.abc import Callable, Sequence
from pathlib import Path

from pii_anonymizer.baselines import (
    load_engine,
    load_engine_cpu,
    load_gliner2,
    load_presidio,
    load_privacy_filter,
    load_regex,
    load_regex_gliner2,
    load_regex_privacy_filter,
)
from pii_anonymizer.benchmark import (
    RUNS_PER_INPUT,
    THREADS,
    WARMUP_CALLS,
    cpu_name,
    measure_latency,
    set_thread_variables,
    size_on_disk,
)
from pii_anonymizer.metrics import score
from pii_anonymizer.results import (
    PER_TYPE_COLUMNS,
    RESULT_COLUMNS,
    cell,
    replace_rows,
    summary_table,
)
from pii_anonymizer.spans import Detector, Example, load_dataset

# Detector name -> function that loads it. Loading happens here, outside the timed part.
# Each loader imports its heavy libraries itself, after main() has set the thread variables.
DETECTORS: dict[str, Callable[[], Detector]] = {
    "regex": load_regex,
    "presidio": load_presidio,
    "gliner2": load_gliner2,
    "regex+gliner2": load_regex_gliner2,
    "privacy-filter": load_privacy_filter,
    "regex+privacy-filter": load_regex_privacy_filter,
    "engine": load_engine,
    "engine-cpu": load_engine_cpu,
}

LATENCY_IDS = Path(__file__).with_name("latency_ids.txt")


def read_ids(path: Path) -> list[str]:
    """One snippet ID per line. Blank lines and lines starting with # are ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def detect_example(detector: Detector, text: str, lang: str | None) -> list:
    """Call the detector, with the language only when the test set gives one."""
    if lang is None:
        return detector.detect(text)
    return detector.detect(text, lang=lang)


def latency_texts(examples: Sequence[Example], ids_path: Path) -> list[str]:
    """The texts of the latency sample, or an empty list if this dataset does not hold it.

    The sample is a list of T2-dev IDs, so other datasets get no latency numbers.
    """
    if not ids_path.exists():
        return []
    ids = read_ids(ids_path)
    by_id = {example.id: example.text for example in examples}
    found = [i for i in ids if i in by_id]
    if not found:
        return []
    if len(found) != len(ids):
        missing = sorted(set(ids) - set(found))
        raise ValueError(f"dataset holds only part of the latency sample, missing {missing}")
    return [by_id[i] for i in ids]


def evaluate(
    model: str,
    detector: Detector,
    dataset_path: Path,
    out_dir: Path,
    latency_ids: Path = LATENCY_IDS,
) -> dict[str, str]:
    """Score the detector, measure its size and latency, and write the results files."""
    examples = load_dataset(dataset_path)
    predictions = [detect_example(detector, e.text, e.lang) for e in examples]
    scores = score(examples, predictions)

    size = size_on_disk(detector.files) if detector.files else None
    texts = latency_texts(examples, latency_ids)
    lang_of_text = {e.text: e.lang for e in examples}
    latency = (
        measure_latency(lambda t: detect_example(detector, t, lang_of_text[t]), texts)
        if texts
        else None
    )

    dataset = dataset_path.stem
    row = {
        "model": model,
        "dataset": dataset,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "runtime": detector.runtime,
        "n_texts": cell(scores.n_texts),
        "n_entities": cell(scores.n_entities),
        "n_protected": cell(scores.n_protected),
        "strict_recall": cell(scores.strict_recall),
        "char_precision": cell(scores.char_precision),
        "size_bytes": cell(size),
        "size_mb": cell(size / 1e6 if size is not None else None, digits=1),
        "threads": cell(THREADS),
        "latency_inputs": cell(len(texts) if latency else None),
        "latency_calls": cell(latency.calls if latency else None),
        "latency_p50_ms": cell(latency.p50_ms if latency else None, digits=2),
        "latency_p95_ms": cell(latency.p95_ms if latency else None, digits=2),
        "latency_p50_ms_per_100_words": cell(
            latency.p50_ms_per_100_words if latency else None, digits=2
        ),
        "latency_p95_ms_per_100_words": cell(
            latency.p95_ms_per_100_words if latency else None, digits=2
        ),
        "cpu": cpu_name(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "date": datetime.date.today().isoformat(),
    }
    per_type = [
        {
            "model": model,
            "dataset": dataset,
            "label": label,
            "n_entities": cell(total),
            "n_protected": cell(protected),
            "recall": cell(protected / total),
        }
        for label, (total, protected) in sorted(scores.per_type.items())
    ]

    results_csv = out_dir / "results.csv"
    # Latency depends on the machine, so each CPU keeps its own row.
    replace_rows(results_csv, RESULT_COLUMNS, [row], key=("model", "dataset", "cpu"))
    # Quality does not depend on the machine.
    replace_rows(out_dir / "recall_per_type.csv", PER_TYPE_COLUMNS, per_type)
    (out_dir / "summary.md").write_text(summary_table(results_csv), encoding="utf-8")
    return row


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate one detector on one test set.")
    parser.add_argument("detector", help=f"one of: {', '.join(sorted(DETECTORS)) or 'none yet'}")
    parser.add_argument("dataset", type=Path, help="test set in JSONL")
    parser.add_argument("out_dir", type=Path, help="folder for the results, usually results/")
    parser.add_argument(
        "--latency-ids",
        type=Path,
        default=LATENCY_IDS,
        help="file with the snippet IDs of the latency sample",
    )
    args = parser.parse_args(argv)
    if args.detector not in DETECTORS:
        parser.error(f"unknown detector {args.detector!r}")

    set_thread_variables()
    detector = DETECTORS[args.detector]()
    row = evaluate(args.detector, detector, args.dataset, args.out_dir, args.latency_ids)
    print(
        f"{row['model']} on {row['dataset']}: strict recall {row['strict_recall']}, "
        f"char precision {row['char_precision'] or 'undefined'}, "
        f"p95 {row['latency_p95_ms'] or 'not measured'} ms"
    )
    if row["latency_calls"]:
        print(f"Warm-up {WARMUP_CALLS} calls, {RUNS_PER_INPUT} runs per input, {THREADS} threads")


if __name__ == "__main__":
    main()
