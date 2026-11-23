"""Evaluate one detector on one test set.

Usage:
    uv run python -m pii_anonymizer.evaluate <detector> <dataset.jsonl> <out_dir>

Writes results.csv, recall_per_type.csv and summary.md into <out_dir>.
See docs/evaluation.md.
"""

import argparse
import datetime
import hashlib
import os
import platform
import tarfile
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from pii_anonymizer.baselines import (
    load_engine,
    load_engine_cpu,
    load_gliner2,
    load_gliner2_int8,
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
    sha256_file,
    summary_table,
)
from pii_anonymizer.spans import SWISS_KINDS, Detector, Example, load_dataset

# Detector name -> function that loads it. Loading happens here, outside the timed part.
# Each loader imports its heavy libraries itself, after main() has set the thread variables.
DETECTORS: dict[str, Callable[[], Detector]] = {
    "regex": load_regex,
    "presidio": load_presidio,
    "gliner2": load_gliner2,
    "gliner2-int8": load_gliner2_int8,
    "regex+gliner2": load_regex_gliner2,
    "privacy-filter": load_privacy_filter,
    "regex+privacy-filter": load_regex_privacy_filter,
    "engine": load_engine,
    "engine-cpu": load_engine_cpu,
}

LATENCY_IDS = Path(__file__).with_name("latency_ids.txt")


class ModelArchiveError(ValueError):
    """The supplied archive could not be verified against the detector's files."""


def _verified_model_sha256(model_file: Path, detector_files: Sequence[Path]) -> str:
    paths = [Path(os.path.abspath(path)) for path in detector_files]
    files = set()
    roots = []
    for path in paths:
        if path.is_dir():
            roots.append(path)
            files.update(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            roots.append(path.parent)
            files.add(path)
        else:
            raise ModelArchiveError(f"detector file is missing: {path}")
    if not files:
        raise ModelArchiveError("the detector has no model files to verify")

    root = Path(os.path.commonpath(roots))
    expected = {path.relative_to(root).as_posix(): path for path in files}
    try:
        with model_file.open("rb") as handle:
            with tarfile.open(fileobj=handle, mode="r|gz") as archive:
                for member in archive:
                    if member.isdir():
                        continue
                    loaded = expected.pop(PurePosixPath(member.name).as_posix(), None)
                    if loaded is None or not member.isfile():
                        raise ModelArchiveError(f"unexpected model archive entry: {member.name}")
                    with archive.extractfile(member) as archived:
                        digest = hashlib.file_digest(archived, "sha256").hexdigest()
                    if digest != sha256_file(loaded):
                        raise ModelArchiveError(f"model archive differs from {member.name}")
            if expected:
                raise ModelArchiveError(f"model archive is missing {min(expected)}")
            handle.seek(0)
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise ModelArchiveError(f"cannot verify model archive {model_file}: {exc}") from exc


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
    latency_ids: Path | None = LATENCY_IDS,
    *,
    benchmark_job: str = "",
    model_file: Path | None = None,
) -> dict[str, str]:
    """Score the detector, measure its size and latency, and write the results files."""
    model_sha256 = _verified_model_sha256(model_file, detector.files) if model_file else ""
    examples = load_dataset(dataset_path)
    predictions = [detect_example(detector, e.text, e.lang) for e in examples]
    scores = score(examples, predictions)

    size = size_on_disk(detector.files) if detector.files else None
    texts = latency_texts(examples, latency_ids) if latency_ids else []
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
        "dataset_sha256": sha256_file(dataset_path),
        "runtime": detector.runtime,
        "n_texts": cell(scores.n_texts),
        "n_entities": cell(scores.n_entities),
        "n_protected": cell(scores.n_protected),
        "strict_recall": cell(scores.strict_recall),
        "char_precision": cell(scores.char_precision),
        "correct_chars": cell(scores.correct_chars),
        "predicted_chars": cell(scores.predicted_chars),
        "size_bytes": cell(size),
        "size_mb": cell(size / 1e6 if size is not None else None, digits=1),
        "threads": cell(THREADS),
        "latency_inputs": cell(len(texts) if latency else None),
        "latency_calls": cell(latency.calls if latency else None),
        "latency_p50_ms": cell(latency.p50_ms if latency else None, digits=2),
        "latency_p95_ms": cell(latency.p95_ms if latency else None, digits=2),
        "latency_p95_ms_raw": str(latency.p95_ms) if latency else "",
        "latency_ids_sha256": sha256_file(latency_ids) if latency and latency_ids else "",
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
        "benchmark_job": benchmark_job,
        "model_sha256": model_sha256,
    }
    counts_by_type = scores.per_type
    if scores.per_swiss_kind:
        counts_by_type = {
            label: counts for label, counts in scores.per_type.items() if label not in SWISS_KINDS
        } | scores.per_swiss_kind
    per_type = [
        {
            "model": model,
            "dataset": dataset,
            "cpu": row["cpu"],
            "runtime": detector.runtime,
            "label": label,
            "n_entities": cell(total),
            "n_protected": cell(protected),
            "recall": cell(protected / total),
            "dataset_sha256": row["dataset_sha256"],
            "benchmark_job": benchmark_job,
            "model_sha256": model_sha256,
        }
        for label, (total, protected) in sorted(counts_by_type.items())
    ]

    results_csv = out_dir / "results.csv"
    # Quantization can change recall by CPU, and this detector accepts local checkpoints.
    key = ("model", "dataset", "cpu")
    if model == "gliner2-int8":
        key += ("runtime",)
    replace_rows(results_csv, RESULT_COLUMNS, [row], key=key)
    replace_rows(out_dir / "recall_per_type.csv", PER_TYPE_COLUMNS, per_type, key=key)
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
    parser.add_argument("--benchmark-job", default="", help="unique ID of this evaluation job")
    parser.add_argument("--model-file", type=Path, help="tar.gz of the detector's model files")
    args = parser.parse_args(argv)
    if args.detector not in DETECTORS:
        parser.error(f"unknown detector {args.detector!r}")

    set_thread_variables()
    detector = DETECTORS[args.detector]()
    try:
        row = evaluate(
            args.detector,
            detector,
            args.dataset,
            args.out_dir,
            args.latency_ids,
            benchmark_job=args.benchmark_job,
            model_file=args.model_file,
        )
    except ModelArchiveError as exc:
        parser.error(str(exc))
    print(
        f"{row['model']} on {row['dataset']}: strict recall {row['strict_recall']}, "
        f"char precision {row['char_precision'] or 'undefined'}, "
        f"p95 {row['latency_p95_ms'] or 'not measured'} ms"
    )
    if row["latency_calls"]:
        print(f"Warm-up {WARMUP_CALLS} calls, {RUNS_PER_INPUT} runs per input, {THREADS} threads")


if __name__ == "__main__":
    main()
