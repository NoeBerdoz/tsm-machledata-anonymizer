"""Decide whether a model's T2-dev results meet a versioned quality gate."""

import argparse
import csv
import hashlib
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import mlflow
import yaml

from pii_anonymizer.benchmark import RUNS_PER_INPUT
from pii_anonymizer.results import sha256_file
from pii_anonymizer.tracking import TrackingInputError, tracked_run

DATASET = "t2-dev"
SWISS_LABELS = ("AVS", "IBAN", "PHONE")
PROFILES = ("release", "demonstration")
LATENCY_INPUTS = 30


class GateInputError(ValueError):
    """Missing or invalid evidence for a gate check."""


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str

    @property
    def verdict(self) -> str:
        return "PASS" if self.passed else "FAIL"


def _job_rows(path: Path, benchmark_job: str) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return [
                row
                for row in csv.DictReader(handle)
                if row.get("dataset") == DATASET and row.get("benchmark_job") == benchmark_job
            ]
    except (OSError, UnicodeError, csv.Error):
        raise GateInputError(f"cannot read {path.name}") from None


def _one_row(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    matches = [row for row in rows if row.get(key) == value]
    if not matches:
        raise GateInputError(f"no T2-dev evaluation results for {value} in this job")
    if len(matches) != 1:
        raise GateInputError(f"multiple T2-dev evaluation rows for {value} in this job")
    return matches[0]


def _counts(row: dict[str, str], numerator: str, denominator: str) -> tuple[int, int]:
    try:
        top, bottom = int(row[numerator]), int(row[denominator])
    except (KeyError, ValueError, TypeError):
        raise GateInputError(f"missing or invalid {numerator}/{denominator}") from None
    if bottom <= 0 or not 0 <= top <= bottom:
        raise GateInputError(f"invalid {numerator}/{denominator}")
    return top, bottom


def _ratio(value: object, name: str) -> Fraction:
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise GateInputError(f"missing or invalid {name}") from None


def _minimum(check: str, counts: tuple[int, int], floor: Fraction) -> Check:
    top, bottom = counts
    return Check(check, Fraction(top, bottom) >= floor, f"{top}/{bottom} >= {floor}")


def _check(name: str, evaluate: Callable[[], Check]) -> Check:
    try:
        return evaluate()
    except GateInputError as exc:
        return Check(name, False, str(exc))


def _read_config(params: Path, profile: str, params_sha256: str) -> tuple[str, dict]:
    raw = params.read_bytes()
    if hashlib.sha256(raw).hexdigest() != params_sha256:
        raise GateInputError("params.yaml changed during the gate run")
    config = yaml.safe_load(raw)
    gate = config.get("quality_gate") if isinstance(config, dict) else None
    if not isinstance(gate, dict) or not isinstance(gate.get(profile), dict):
        raise GateInputError(f"set quality_gate.{profile} in params.yaml")
    dataset_hash = gate.get("t2_dev_sha256")
    if not isinstance(dataset_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", dataset_hash):
        raise GateInputError("set quality_gate.t2_dev_sha256 to the frozen T2-dev hash")
    return dataset_hash, gate[profile]


def _matching_hash(row: dict[str, str], column: str, expected: str) -> None:
    if row.get(column) != expected:
        raise GateInputError(f"{row['model']} evaluation has a missing or mismatched {column}")


def _evaluate_gate(
    args: argparse.Namespace, model_hash: str, run_tags: dict[str, str]
) -> list[Check]:
    try:
        rows = _job_rows(args.results_dir / "results.csv", args.benchmark_job)
        student = _one_row(rows, "model", args.model)
        _matching_hash(student, "model_sha256", model_hash)
        if run_tags.get("data.0.dvc_path") != f"{DATASET}.jsonl":
            raise GateInputError("use the DVC pointer for t2-dev.jsonl")
        dataset_hash, config = _read_config(args.params, args.thresholds, run_tags["params_sha256"])
        _matching_hash(student, "dataset_sha256", dataset_hash)
    except GateInputError as exc:
        return [Check("T2-dev evaluation", False, str(exc))]

    def threshold(key: str) -> Fraction:
        value = _ratio(config.get(key), key)
        if not 0 <= value <= 1:
            raise GateInputError(f"{key} must be between 0 and 1")
        return value

    def recall() -> tuple[int, int]:
        return _counts(student, "n_protected", "n_entities")

    if args.thresholds == "demonstration":
        name = "demonstration recall"
        return [_check(name, lambda: _minimum(name, recall(), threshold("min_recall")))]

    def teacher_row() -> dict[str, str]:
        if args.teacher == args.model:
            raise GateInputError("teacher and candidate evaluation names must differ")
        teacher = _one_row(rows, "model", args.teacher)
        _matching_hash(teacher, "dataset_sha256", dataset_hash)
        return teacher

    def teacher_recall() -> Check:
        protected, total = _counts(teacher_row(), "n_protected", "n_entities")
        counts = recall()
        if total != counts[1]:
            raise GateInputError("teacher and candidate evaluations differ in n_entities")
        if protected == 0:
            raise GateInputError("teacher recall is zero, so the recall ratio is undefined")
        floor = Fraction(protected, total) * threshold("min_teacher_recall_ratio")
        return _minimum("teacher recall", counts, floor)

    def swiss_recall() -> Check:
        rows = _job_rows(args.results_dir / "recall_per_type.csv", args.benchmark_job)
        combined = [row for row in rows if row.get("model") == f"regex+{args.model}"]
        protected = total = 0
        for label in SWISS_LABELS:
            row = _one_row(combined, "label", label)
            _matching_hash(row, "dataset_sha256", dataset_hash)
            _matching_hash(row, "model_sha256", model_hash)
            found, count = _counts(row, "n_protected", "n_entities")
            protected += found
            total += count
        return _minimum("Swiss recall", (protected, total), threshold("min_swiss_recall"))

    def size() -> Check:
        actual = _ratio(student.get("size_bytes"), "size_bytes")
        teacher_size = config.get("teacher_size_bytes")
        if type(teacher_size) is not int or teacher_size <= 0:
            raise GateInputError("missing or invalid teacher_size_bytes")
        if actual.denominator != 1 or actual <= 0:
            raise GateInputError("invalid size_bytes")
        limit = teacher_size * threshold("max_size_ratio")
        return Check("model size", actual <= limit, f"{actual} bytes <= {int(limit)} bytes")

    def latency() -> Check:
        teacher = teacher_row()
        for key in ("cpu", "threads", "latency_ids_sha256", "latency_inputs", "latency_calls"):
            if not student.get(key) or student[key] != teacher.get(key):
                raise GateInputError(f"teacher and candidate latency measurements differ in {key}")
        calls = LATENCY_INPUTS * RUNS_PER_INPUT
        if (student["latency_inputs"], student["latency_calls"]) != (
            str(LATENCY_INPUTS),
            str(calls),
        ):
            raise GateInputError(
                f"latency protocol requires {LATENCY_INPUTS} inputs and {calls} calls"
            )
        actual = _ratio(student.get("latency_p95_ms_raw"), "candidate p95")
        reference = _ratio(teacher.get("latency_p95_ms_raw"), "teacher p95")
        if actual <= 0 or reference <= 0:
            raise GateInputError("p95 latency must be positive")
        limit_ratio = threshold("max_p95_ratio")
        detail = f"{student['latency_p95_ms_raw']} ms <= {limit_ratio} of "
        detail += f"{teacher['latency_p95_ms_raw']} ms"
        return Check("p95 latency", actual <= reference * limit_ratio, detail)

    return [
        _check("teacher recall", teacher_recall),
        _check(
            "published recall",
            lambda: _minimum("published recall", recall(), threshold("min_published_recall")),
        ),
        _check("Swiss recall", swiss_recall),
        _check(
            "character precision",
            lambda: _minimum(
                "character precision",
                _counts(student, "correct_chars", "predicted_chars"),
                threshold("min_char_precision"),
            ),
        ),
        _check("model size", size),
        _check("p95 latency", latency),
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Check a model's T2-dev results.")
    parser.add_argument("model", help="candidate detector name in the evaluation results")
    parser.add_argument("--model-file", type=Path, required=True, help="archive to publish")
    parser.add_argument("--thresholds", choices=PROFILES, required=True)
    parser.add_argument("--benchmark-job", required=True, help="job ID in the evaluation results")
    parser.add_argument("--git-sha", required=True, help="full Git commit SHA")
    parser.add_argument("--teacher", default="teacher", help="fine-tuned teacher detector name")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--params", type=Path, default=Path("params.yaml"))
    parser.add_argument("--data-pointer", type=Path, default=Path("data/test/t2-dev.jsonl.dvc"))
    args = parser.parse_args(argv)
    if not args.benchmark_job.strip():
        parser.error("--benchmark-job must be nonempty")

    os.environ["MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT"] = "true"
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    try:
        model_hash = sha256_file(args.model_file)
    except OSError:
        parser.exit(1, "FAIL - cannot read the model archive\n")

    try:
        with tracked_run("gate", args.data_pointer, args.params, args.git_sha) as run:
            checks = _evaluate_gate(args, model_hash, run.data.tags)
            verdict = "PASS" if all(c.passed for c in checks) else "FAIL"
            mlflow.log_param("model_sha256", model_hash, synchronous=True)
            mlflow.log_param("gate_profile", args.thresholds, synchronous=True)
            mlflow.log_param("benchmark_job", args.benchmark_job, synchronous=True)
            for check in checks:
                key = check.name.lower().replace(" ", "_").replace("-", "_")
                mlflow.log_param(
                    f"gate_check.{key}", f"{check.verdict} - {check.detail}", synchronous=True
                )
            mlflow.log_param("gate_status", verdict, synchronous=True)
    except TrackingInputError as exc:
        parser.exit(1, f"FAIL - {exc}\n")
    except Exception as exc:
        parser.exit(
            1, f"FAIL - could not record the gate result in MLflow ({type(exc).__name__})\n"
        )

    for check in checks:
        print(f"{check.name}: {check.verdict} - {check.detail}")
    print(f"{verdict} ({args.thresholds}), MLflow run {run.info.run_id}")
    if verdict == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
