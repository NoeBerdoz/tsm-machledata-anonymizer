"""Prepare the DVC inputs and report the result of a training workflow."""

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from pii_anonymizer import evaluate, gate
from pii_anonymizer.baselines import load_gliner2_checkpoint
from pii_anonymizer.benchmark import set_thread_variables
from pii_anonymizer.results import sha256_file
from pii_anonymizer.teacher_labels import TARGETS
from pii_anonymizer.tracking import _data_provenance

PARAMS = Path("params.yaml")
DATASET = Path("data/test/t2-dev.jsonl")
POINTER = DATASET.with_suffix(".jsonl.dvc")
FIXTURE = Path("tests/fixtures/pipeline-synthetic.jsonl")
OUTPUT = Path(".pipeline")
ARCHIVE = OUTPUT / "model.tar.gz"
TRAINING = OUTPUT / "training.json"
RESULTS = OUTPUT / "evaluation"
REPORT = OUTPUT / "gate.json"
PREFLIGHT_STATUS = OUTPUT / "preflight-status.txt"
LOCK = Path("dvc.lock")
MODEL = "checkpoint"


def dvc(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "dvc", *args], check=True)


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def validate_gate_inputs(config: dict) -> str:
    try:
        settings = config["quality_gate"]
        expected = settings["t2_dev_sha256"]
        floor = Fraction(str(settings["demonstration"]["min_recall"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        raise ValueError("Set the frozen T2-dev SHA-256 and demonstration recall floor") from None
    if (
        not isinstance(expected, str)
        or len(expected) != 64
        or any(byte not in "0123456789abcdef" for byte in expected)
    ):
        raise ValueError("Set quality_gate.t2_dev_sha256 to the frozen T2-dev SHA-256")
    if not 0 <= floor <= 1:
        raise ValueError("The demonstration recall floor must be between 0 and 1")
    return expected


def validate_dataset(expected: str) -> None:
    if sha256_file(DATASET) != expected:
        raise ValueError("The T2-dev file does not match the frozen SHA-256")
    pointer = _data_provenance(POINTER)
    with DATASET.open("rb") as handle:
        algorithm = hashlib.new(pointer["dvc_hash_algorithm"], usedforsecurity=False)
        digest = hashlib.file_digest(handle, lambda: algorithm).hexdigest()
    if pointer["dvc_path"] != DATASET.name or pointer["dvc_hash"].lower() != digest:
        raise ValueError("The T2-dev file does not match its DVC pointer")


def prepare(proof: bool) -> None:
    config = yaml.safe_load(PARAMS.read_bytes())
    if proof:
        DATASET.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE, DATASET)
        dvc("add", str(DATASET))
        settings = config["quality_gate"]
        settings["t2_dev_sha256"] = sha256_file(DATASET)
        settings["demonstration"]["min_recall"] = "0/1"
        settings["synthetic_proof"] = True
        PARAMS.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        dvc(
            "remote",
            "add",
            "--local",
            "--default",
            "proof",
            "gs://tsm-machledata-anonymizer-dvc/pipeline-proof",
        )
    else:
        if config["quality_gate"].get("synthetic_proof"):
            raise ValueError("Use a clean checkout for the normal pipeline")
        if not POINTER.is_file():
            raise ValueError("The frozen data/test/t2-dev.jsonl.dvc is missing")
        validate_gate_inputs(config)
        dvc("pull", str(POINTER))
    # The training subset of the train stage, from the main remote even in proof mode.
    dvc("pull", "--remote", "data", config["training"]["data"])
    validate_dataset(validate_gate_inputs(config))


def unpack_checkpoint(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        names = set()
        for member in members:
            path = Path(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path in names
            ):
                raise ValueError(f"Invalid checkpoint archive entry: {member.name}")
            names.add(path)
        if Path("config.json") not in names:
            raise ValueError("The checkpoint archive has no config.json")
        archive.extractall(destination, members=members, filter="data")


def benchmark_id() -> str:
    return f"{sha256_file(ARCHIVE)}-{sha256_file(DATASET)}"


def run_evaluation() -> None:
    set_thread_variables()
    RESULTS.mkdir(parents=True, exist_ok=True)
    job = benchmark_id()
    with TemporaryDirectory() as temp:
        checkpoint = Path(temp)
        unpack_checkpoint(ARCHIVE, checkpoint)
        detector = load_gliner2_checkpoint(checkpoint, fallback_labels=TARGETS)
        evaluate.evaluate(
            MODEL,
            detector,
            DATASET,
            RESULTS,
            latency_ids=None,
            benchmark_job=job,
            model_file=ARCHIVE,
        )
    (RESULTS / "origin.json").write_text(json.dumps({"git_sha": git_sha()}) + "\n")


def run_gate() -> None:
    config = yaml.safe_load(PARAMS.read_bytes())
    validate_dataset(validate_gate_inputs(config))
    args = [
        MODEL,
        "--model-file",
        str(ARCHIVE),
        "--thresholds",
        "demonstration",
        "--benchmark-job",
        benchmark_id(),
        "--git-sha",
        git_sha(),
        "--results-dir",
        str(RESULTS),
        "--report",
        str(REPORT),
        "--dvc-lock",
        str(LOCK),
        "--training-metadata",
        str(TRAINING),
    ]
    if config["quality_gate"].get("synthetic_proof"):
        args.append("--proof")
    gate.main(args)


def push_cache() -> None:
    stages = []
    if TRAINING.is_file() and ARCHIVE.is_file():
        stages.append("train")
    if (RESULTS / "origin.json").is_file():
        stages.append("evaluate")
    if REPORT.is_file():
        stages.append("gate")
    if stages:
        dvc("push", "--run-cache", *stages)


def load_json(path: Path) -> dict:
    return json.loads(path.read_bytes()) if path.is_file() else {}


def summary(proof: bool) -> None:
    report = load_json(REPORT)
    training = load_json(TRAINING)
    evaluation = load_json(RESULTS / "origin.json")
    heading = "Synthetic proof" if proof else "Training quality gate"
    lines = [f"## {heading}", "", f"**Gate result:** {report.get('verdict', 'NOT RUN')}"]
    for check in report.get("checks", []):
        lines.append(f"- {check['name']}: {check['detail']}")
    metrics = report.get("metrics", {})
    if not report and evaluation:
        with (RESULTS / "results.csv").open(newline="") as handle:
            metrics = next(csv.DictReader(handle), {})
    if metrics:
        recall = metrics.get("strict_recall") or "undefined"
        precision = metrics.get("char_precision") or "undefined"
        lines.extend(
            [
                "",
                f"- Strict recall: {recall} ({metrics['n_protected']}/{metrics['n_entities']})",
                f"- Character precision: {precision} "
                f"({metrics['correct_chars']}/{metrics['predicted_chars']})",
                f"- Model size: {metrics['size_bytes']} bytes",
            ]
        )
    if training:
        lines.extend(
            [
                "",
                f"- Agent Platform job: `{training['job']}`",
                f"- MLflow training run: `{training['run_id']}`",
            ]
        )
    if report:
        lines.append(f"- MLflow gate run: `{report['run_id']}`")
    elif PREFLIGHT_STATUS.is_file():
        lines.extend(["", PREFLIGHT_STATUS.read_text().strip()])
    elif (status := OUTPUT / "training-status.txt").is_file():
        lines.extend(["", status.read_text().strip()])
    current = git_sha()
    for label, record in [("Training", training), ("Evaluation", evaluation), ("Gate", report)]:
        if origin := record.get("git_sha"):
            reused = " (reused)" if origin != current else ""
            lines.append(f"- {label} commit: `{origin}`{reused}")
    message = "\n".join(lines) + "\n"
    if destination := os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(destination).open("a", encoding="utf-8") as handle:
            handle.write(message)
    else:
        print(message, end="")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["prepare", "evaluate", "gate", "push-cache", "summary", "verdict"]
    )
    parser.add_argument("--proof", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        OUTPUT.mkdir(exist_ok=True)
        PREFLIGHT_STATUS.unlink(missing_ok=True)
        try:
            prepare(args.proof)
        except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
            message = str(exc) if isinstance(exc, ValueError) else "Could not prepare DVC inputs"
            PREFLIGHT_STATUS.write_text(f"Blocked: {message}\n", encoding="utf-8")
            parser.exit(1, f"Blocked: {message}\n")
    elif args.command == "evaluate":
        run_evaluation()
    elif args.command == "gate":
        run_gate()
    elif args.command == "push-cache":
        push_cache()
    elif args.command == "summary":
        summary(args.proof)
    elif load_json(REPORT).get("verdict") != "PASS":
        parser.exit(1, "The gate did not record PASS\n")


if __name__ == "__main__":
    main()
