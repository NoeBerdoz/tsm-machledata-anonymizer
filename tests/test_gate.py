import hashlib
import json
from pathlib import Path

import pytest
import yaml

from pii_anonymizer import evaluate, gate, tracking
from pii_anonymizer.benchmark import Latency
from pii_anonymizer.results import PER_TYPE_COLUMNS, RESULT_COLUMNS, replace_rows
from pii_anonymizer.spans import Span

REPO = Path(__file__).resolve().parents[1]
SHA = "a" * 40
DATASET_HASH = "b" * 64
JOB = "gate-job-1"


@pytest.fixture
def gate_inputs(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", (tmp_path / "mlruns").as_uri())
    client = tracking.MlflowClient()
    experiment = client.create_experiment("tsm-gates")
    monkeypatch.setattr(tracking, "_tracking_client", lambda: client)

    package = tmp_path / "model.tar.gz"
    package.write_bytes(b"packaged model")
    pointer = tmp_path / "t2-dev.jsonl.dvc"
    pointer.write_text("outs: [{path: t2-dev.jsonl, md5: dddddddddddddddddddddddddddddddd}]\n")
    params = tmp_path / "params.yaml"
    config = yaml.safe_load((REPO / "params.yaml").read_text())
    config["quality_gate"]["t2_dev_sha256"] = DATASET_HASH
    config["quality_gate"]["release"].update(
        min_char_precision="891/900",
        min_published_recall="90/100",
    )
    config["quality_gate"]["demonstration"]["min_recall"] = "94/100"
    params.write_text(yaml.safe_dump(config))

    common = {
        "dataset": "t2-dev",
        "dataset_sha256": DATASET_HASH,
        "benchmark_job": JOB,
    }
    timing = {
        "cpu": "Test CPU",
        "latency_calls": "300",
        "latency_inputs": "30",
        "latency_ids_sha256": "c" * 64,
        "threads": "4",
    }
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    student = {
        **common,
        **timing,
        "model": "student",
        "model_sha256": digest,
        "n_protected": "950",
        "n_entities": "1000",
        "strict_recall": "0.9500",
        "correct_chars": "891",
        "predicted_chars": "900",
        "char_precision": "0.9900",
        "latency_p95_ms_raw": "20.0000",
        "latency_p95_ms": "20.00",
        "size_bytes": "155555553",
    }
    teacher = {
        **common,
        **timing,
        "model": "teacher",
        "n_protected": "1000",
        "n_entities": "1000",
        "latency_p95_ms_raw": "30.0000",
        "latency_p95_ms": "30.00",
    }
    swiss = [
        {
            **common,
            "model": "regex+student",
            "model_sha256": digest,
            "label": label,
            "n_protected": str(protected),
            "n_entities": str(total),
        }
        for label, protected, total in [("AVS", 9, 10), ("IBAN", 25, 25), ("PHONE", 65, 65)]
    ]

    def run(profile="release", model="student"):
        replace_rows(tmp_path / "results.csv", RESULT_COLUMNS, [student, teacher])
        replace_rows(tmp_path / "recall_per_type.csv", PER_TYPE_COLUMNS, swiss)
        argv = [
            model,
            "--model-file",
            str(package),
            "--thresholds",
            profile,
            "--benchmark-job",
            JOB,
            "--git-sha",
            SHA,
            "--data-pointer",
            str(pointer),
            "--params",
            str(params),
            "--results-dir",
            str(tmp_path),
        ]
        exit_code = 0
        try:
            gate.main(argv)
        except SystemExit as exc:
            exit_code = exc.code
        runs = client.search_runs([experiment])
        assert len(runs) == 1
        assert exit_code == (0 if runs[0].data.params["gate_status"] == "PASS" else 1)
        return runs[0]

    return student, teacher, swiss, params, run


def test_release_accepts_exact_boundaries_and_indexes_archive_hash(gate_inputs, capsys):
    student, _, _, params, run_gate = gate_inputs
    run = run_gate()
    output = capsys.readouterr().out
    assert output.count(": PASS") == 6
    assert "Swiss recall: PASS - 99/100" in output
    assert "character precision: PASS - 891/900" in output
    assert f"PASS (release), MLflow run {run.info.run_id}" in output
    assert run.info.status == "FINISHED"
    assert run.data.params["model_sha256"] == student["model_sha256"]
    assert run.data.params["gate_profile"] == "release"
    assert run.data.params["gate_status"] == "PASS"
    assert run.data.tags["mlflow.source.git.commit"] == SHA
    assert run.data.tags["params_sha256"] == hashlib.sha256(params.read_bytes()).hexdigest()

    matches = tracking.MlflowClient().search_runs(
        [run.info.experiment_id],
        f"params.model_sha256 = '{student['model_sha256']}' AND params.gate_profile = 'release'"
        " AND params.gate_status = 'PASS' AND attributes.status = 'FINISHED'",
    )
    assert [match.info.run_id for match in matches] == [run.info.run_id]


@pytest.mark.parametrize(
    ("check", "row", "key", "value"),
    [
        ("teacher recall", "student", "n_protected", "949"),
        ("published recall", "student", "n_protected", "899"),
        ("Swiss recall", "swiss", "n_protected", "8"),
        ("character precision", "student", "correct_chars", "890"),
        ("character precision", "student", "predicted_chars", ""),
        ("model size", "student", "size_bytes", "155555554"),
        ("p95 latency", "student", "latency_p95_ms_raw", "20.00001"),
        ("p95 latency", "teacher", "benchmark_job", "an-earlier-job"),
        ("p95 latency", "teacher", "latency_ids_sha256", "e" * 64),
    ],
)
def test_release_fails_a_missed_check(gate_inputs, capsys, check, row, key, value):
    student, teacher, swiss, _, run_gate = gate_inputs
    {"student": student, "teacher": teacher, "swiss": swiss[0]}[row][key] = value
    run = run_gate()
    assert run.data.params["gate_status"] == "FAIL"
    assert f"{check}: FAIL" in capsys.readouterr().out


@pytest.mark.parametrize(("protected", "result"), [("940", "PASS"), ("939", "FAIL")])
def test_demonstration_uses_its_own_recall_floor(gate_inputs, capsys, protected, result):
    student, _, _, _, run_gate = gate_inputs
    student["n_protected"] = protected
    run = run_gate("demonstration")
    assert run.data.params["gate_profile"] == "demonstration"
    assert run.data.params["gate_status"] == result
    assert f"demonstration recall: {result}" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("metadata", "value", "reason"),
    [
        ("dataset", "t2-final", "no T2-dev evaluation results"),
        ("model_sha256", "d" * 64, "mismatched model_sha256"),
        ("dataset_sha256", "d" * 64, "mismatched dataset_sha256"),
    ],
)
def test_wrong_evaluation_evidence_cannot_pass(gate_inputs, capsys, metadata, value, reason):
    student, _, _, _, run_gate = gate_inputs
    student[metadata] = value
    run = run_gate("demonstration")
    assert run.data.params["gate_status"] == "FAIL"
    assert reason in capsys.readouterr().out


def test_missing_results_are_logged_with_archive_hash(gate_inputs, capsys):
    student, _, _, _, run_gate = gate_inputs
    run = run_gate("demonstration", model="unevaluated")
    assert run.data.params["model_sha256"] == student["model_sha256"]
    assert run.data.params["gate_status"] == "FAIL"
    assert "T2-dev evaluation: FAIL" in capsys.readouterr().out


def test_unset_threshold_fails(gate_inputs, capsys):
    _, _, _, params, run_gate = gate_inputs
    config = yaml.safe_load(params.read_text())
    config["quality_gate"]["release"]["min_char_precision"] = None
    params.write_text(yaml.safe_dump(config))
    run = run_gate()
    assert run.data.params["gate_status"] == "FAIL"
    assert "character precision: FAIL - missing or invalid min_char_precision" in (
        capsys.readouterr().out
    )


def test_evaluator_writes_exact_evidence_for_one_job(tmp_path, monkeypatch):
    class Detector:
        runtime = "test"
        files = []

        def detect(self, text):
            return [Span(0, 3, "AVS")]

    dataset = tmp_path / "t2-dev.jsonl"
    dataset.write_text(
        json.dumps({"id": "1", "text": "abc", "entities": [{"start": 0, "end": 2, "label": "AVS"}]})
        + "\n"
    )
    archive = tmp_path / "model.tar.gz"
    archive.write_bytes(b"packaged model")
    ids = tmp_path / "ids.txt"
    ids.write_text("1\n")
    monkeypatch.setattr(evaluate, "measure_latency", lambda *args: Latency(10, 1.0, 1.2345, 0, 0))

    row = evaluate.evaluate(
        "regex+student", Detector(), dataset, tmp_path, ids, benchmark_job=JOB, model_file=archive
    )

    assert row["correct_chars"] == "2"
    assert row["predicted_chars"] == "3"
    assert row["latency_p95_ms"] == "1.23"
    assert row["latency_p95_ms_raw"] == "1.2345"
    assert row["latency_ids_sha256"] == hashlib.sha256(ids.read_bytes()).hexdigest()
    swiss = gate._job_rows(tmp_path / "recall_per_type.csv", JOB)
    assert len(swiss) == 1
    assert swiss[0]["model_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert swiss[0]["dataset_sha256"] == hashlib.sha256(dataset.read_bytes()).hexdigest()
