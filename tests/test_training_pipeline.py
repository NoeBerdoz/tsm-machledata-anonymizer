import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
from google.api_core.exceptions import PreconditionFailed
from requests import Response, Timeout

from pii_anonymizer import cloud_training, training_pipeline

REPO = Path(__file__).resolve().parents[1]
SHA = "a" * 40


def test_lost_create_response_and_runner_retry_only_look_up_job(monkeypatch):
    session, bucket, stage_inputs = Mock(), Mock(), Mock()
    marker = bucket.blob.return_value
    marker.upload_from_string.side_effect = [None, PreconditionFailed("already claimed")]
    marker.download_as_text.return_value = SHA
    calls = []

    def request(_session, method, _url, **_kwargs):
        calls.append(method)
        if method == "POST":
            raise Timeout()
        return {}

    monkeypatch.setattr(cloud_training, "request", request)
    monkeypatch.setattr(cloud_training.time, "sleep", lambda _: None)

    for _ in range(2):
        with pytest.raises(
            cloud_training.TrainingError, match="No confirmed job for submission abc"
        ):
            cloud_training.submit_once(session, bucket, "abc", SHA, {}, stage_inputs)

    assert calls[0] == "POST"
    assert calls.count("POST") == 1
    assert calls.count("GET") == 12
    assert marker.upload_from_string.call_args.kwargs["if_generation_match"] == 0
    bucket.blob.assert_called_with("pipeline/abc/claim")
    stage_inputs.assert_called_once_with(bucket, "pipeline/inputs/abc")


@pytest.mark.parametrize("status", [400, 403, 429])
def test_create_rejection_reports_http_status_without_lookup(capsys, status):
    response = Response()
    response.status_code = status
    session = Mock()
    session.request.return_value = response

    with pytest.raises(
        cloud_training.TrainingError, match=f"rejected job creation \\(HTTP {status}\\)"
    ):
        cloud_training.submit_once(session, Mock(), "abc", SHA, {}, Mock())

    assert session.request.call_count == 1
    assert session.request.call_args.args[0] == "POST"
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("status", [408, 503])
def test_ambiguous_http_response_looks_up_the_job(status):
    error, found = Response(), Response()
    error.status_code = status
    found.status_code = 200
    found._content = b'{"customJobs": [{"name": "job-1"}]}'
    session = Mock()
    session.request.side_effect = [error, found]

    assert cloud_training.submit_once(session, Mock(), "abc", SHA, {}, Mock()) == "job-1"
    assert [call.args[0] for call in session.request.call_args_list] == ["POST", "GET"]


def test_ambiguous_create_can_resume_a_confirmed_job(monkeypatch):
    request = Mock(side_effect=[Timeout(), {}, {"customJobs": [{"name": "job-1"}]}])
    monkeypatch.setattr(cloud_training, "request", request)
    monkeypatch.setattr(cloud_training.time, "sleep", lambda _: None)

    assert cloud_training.submit_once(Mock(), Mock(), "abc", SHA, {}, Mock()) == "job-1"
    assert [call.args[1] for call in request.call_args_list] == ["POST", "GET", "GET"]


def test_actions_submission_id_ignores_run_attempt(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    first = cloud_training.submission_id()
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    assert cloud_training.submission_id() == first


@pytest.mark.parametrize("value", [None, True, "0.5", 0, -1, float("inf"), float("nan")])
def test_invalid_caps_are_refused(value):
    with pytest.raises(cloud_training.TrainingError, match="training.max_hours"):
        cloud_training.cap_seconds(value)


def test_training_cap_reserves_time_outside_the_gpu_job():
    assert cloud_training.cap_seconds(0.75) == 45 * 60
    for hours in (0.76, 2):
        with pytest.raises(cloud_training.TrainingError, match="Actions runner budget"):
            cloud_training.cap_seconds(hours)


def test_slow_setup_reduces_the_remaining_training_cap(monkeypatch):
    monkeypatch.setattr(cloud_training.time, "monotonic", lambda: 1000)
    deadline = 1000 + 60 * 60
    assert cloud_training.cap_seconds(25 / 60, runner_deadline=deadline) == 25 * 60
    with pytest.raises(cloud_training.TrainingError, match="1500 seconds available"):
        cloud_training.cap_seconds(0.5, runner_deadline=deadline)


def test_runner_deadline_reserves_time_to_cancel(monkeypatch):
    monkeypatch.setattr(cloud_training.time, "monotonic", lambda: 1000)
    request = Mock()
    monkeypatch.setattr(cloud_training, "request", request)
    deadline = 1000 + cloud_training.FINISH_RESERVE_SECONDS
    with pytest.raises(cloud_training.TrainingError, match="Requested cancellation"):
        cloud_training.wait_for_job(Mock(), "job-1", 1800, runner_deadline=deadline)
    assert request.call_count == 1
    assert request.call_args.args[1:] == ("POST", f"{cloud_training.JOB_ENDPOINT}/job-1:cancel")


@pytest.mark.parametrize("staging_minutes", [0, 30])
def test_submission_respects_budget_after_staging(tmp_path, monkeypatch, staging_minutes):
    now = 1000
    monkeypatch.chdir(REPO)
    monkeypatch.setattr(cloud_training, "OUTPUT", tmp_path)
    monkeypatch.setattr(cloud_training, "validate_dataset", Mock())
    monkeypatch.setattr(cloud_training, "validate_gate_inputs", Mock())
    monkeypatch.setattr(cloud_training, "git_sha", lambda: SHA)
    monkeypatch.setattr(cloud_training, "submission_id", lambda: "abc")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "https://mlflow.example")
    monkeypatch.setenv("TRAINING_RUNNER_STARTED_AT", "1000")
    monkeypatch.setattr(cloud_training.time, "time", lambda: 1000)
    monkeypatch.setattr(cloud_training.time, "monotonic", lambda: now)
    monkeypatch.setattr(cloud_training.google.auth, "default", Mock(return_value=(Mock(), None)))
    monkeypatch.setattr(cloud_training.storage, "Client", Mock())
    session = Mock()
    session_manager = Mock()
    response = Response()
    response.status_code = 200
    response._content = b'{"name":"job-1"}'
    session.request.return_value = response
    session_manager.__enter__ = Mock(return_value=session)
    session_manager.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(cloud_training, "AuthorizedSession", Mock(return_value=session_manager))
    monkeypatch.setattr(cloud_training, "wait_for_job", Mock())
    monkeypatch.setattr(cloud_training, "download_outputs", Mock())

    def stage_inputs(_bucket, prefix):
        nonlocal now
        assert prefix == "pipeline/inputs/abc"
        now += staging_minutes * 60

    monkeypatch.setattr(cloud_training, "stage_inputs", stage_inputs)
    if staging_minutes:
        with pytest.raises(SystemExit, match="Actions runner budget"):
            cloud_training.main()
        session.request.assert_not_called()
    else:
        cloud_training.main()
        job = session.request.call_args.kwargs["json"]["jobSpec"]
        assert job["scheduling"]["timeout"] == "1800s"
        args = job["workerPoolSpecs"][0]["containerSpec"]["args"]
        assert args[:2] == [
            f"/gcs/{cloud_training.BUCKET}/pipeline/inputs/abc",
            f"/gcs/{cloud_training.BUCKET}/pipeline/outputs/abc",
        ]


def test_agent_platform_deadline_reports_the_configured_cap(monkeypatch):
    request = Mock(
        return_value={
            "state": "JOB_STATE_FAILED",
            "error": {"code": 4},
            "startTime": "2026-11-21T12:00:00Z",
        }
    )
    monkeypatch.setattr(cloud_training, "request", request)
    with pytest.raises(cloud_training.TrainingError, match="Training cap of 1800 seconds reached"):
        cloud_training.wait_for_job(Mock(), "job-1", cloud_training.cap_seconds(0.5))


@pytest.mark.parametrize("invalid", ["../other.json", "/tmp/other.json", "symlink"])
def test_archive_validation_precedes_extraction(tmp_path, invalid):
    path = tmp_path / "model.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        safe = tarfile.TarInfo("config.json")
        safe.size = 2
        archive.addfile(safe, io.BytesIO(b"{}"))
        bad = tarfile.TarInfo(invalid)
        if invalid == "symlink":
            bad.type = tarfile.SYMTYPE
            bad.linkname = "config.json"
        archive.addfile(bad)

    with pytest.raises(ValueError, match="Invalid checkpoint archive entry"):
        training_pipeline.unpack_checkpoint(path, tmp_path)
    assert not (tmp_path / "config.json").exists()


def test_normal_preflight_checks_frozen_inputs_before_pulling(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = yaml.safe_load((REPO / "params.yaml").read_bytes())
    training_pipeline.PARAMS.write_text(yaml.safe_dump(config))
    fetch = Mock()
    monkeypatch.setattr(training_pipeline, "dvc", fetch)

    with pytest.raises(ValueError, match="frozen .*dvc is missing"):
        training_pipeline.prepare(False)

    training_pipeline.POINTER.parent.mkdir(parents=True)
    training_pipeline.POINTER.touch()
    with pytest.raises(ValueError, match="frozen T2-dev SHA-256 and demonstration recall floor"):
        training_pipeline.prepare(False)
    fetch.assert_not_called()

    settings = config["quality_gate"]
    settings["t2_dev_sha256"] = "a" * 64
    settings["demonstration"]["min_recall"] = "95/100"
    training_pipeline.PARAMS.write_text(yaml.safe_dump(config))
    training_pipeline.DATASET.write_text("bad data\n")
    with pytest.raises(ValueError, match="does not match the frozen SHA-256"):
        training_pipeline.prepare(False)


def test_synthetic_preflight_uses_its_own_fixture_floor_and_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    shutil.copyfile(REPO / "params.yaml", "params.yaml")
    fixture = REPO / training_pipeline.FIXTURE
    monkeypatch.setattr(training_pipeline, "FIXTURE", fixture)
    data = fixture.read_bytes()
    calls = []

    def dvc(*args):
        calls.append(args)
        if args[0] == "add":
            training_pipeline.POINTER.write_text(
                yaml.safe_dump(
                    {
                        "outs": [
                            {
                                "path": "t2-dev.jsonl",
                                "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
                            }
                        ]
                    }
                )
            )

    monkeypatch.setattr(training_pipeline, "dvc", dvc)
    training_pipeline.prepare(True)

    config = yaml.safe_load(training_pipeline.PARAMS.read_bytes())
    assert config["quality_gate"]["synthetic_proof"] is True
    assert config["quality_gate"]["demonstration"]["min_recall"] == "0/1"
    assert training_pipeline.DATASET.read_bytes() == data
    assert calls[1][-1].endswith("/pipeline-proof")


def test_action_triggers_and_credentials_stay_separate():
    workflows = REPO / ".github/workflows"
    training = yaml.load((workflows / "training.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(training["on"]) == {"push", "workflow_dispatch"}
    assert training["on"]["push"]["branches"] == ["main"]
    paths = training["on"]["push"]["paths"]
    assert not any(path.startswith(("docs/", "tests/")) for path in paths)
    job = training["jobs"]["train-and-evaluate"]
    assert int(job["timeout-minutes"]) == cloud_training.RUNNER_TIMEOUT_MINUTES
    assert job["environment"] == "training-gate"
    assert "refs/heads/main" in job["if"]
    assert "MLFLOW_GATE_PASSWORD" in (workflows / "training.yml").read_text()
    proof = (workflows / "mlflow-proof.yml").read_text()
    assert "MLFLOW_PROOF_PASSWORD" in proof
    assert "secrets.MLFLOW_GATE_PASSWORD" not in proof
    assert "secrets.MLFLOW_TRACKING_PASSWORD" not in proof


def test_dvc_reuses_completed_stages_in_a_fresh_checkout(tmp_path):
    env = {
        **os.environ,
        "DVC_SITE_CACHE_DIR": str(tmp_path / "site-cache"),
        "DVC_NO_ANALYTICS": "true",
    }
    graph = yaml.safe_load((REPO / "dvc.yaml").read_text())
    remote = tmp_path / "remote"
    remote.mkdir()

    def run_dvc(workspace, *args):
        result = subprocess.run(
            [sys.executable, "-m", "dvc", *args],
            cwd=workspace,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def create_workspace(name, gate_floor):
        workspace = tmp_path / name
        workspace.mkdir()
        run_dvc(workspace, "init", "--no-scm")
        run_dvc(workspace, "remote", "add", "-d", "cache", str(remote))
        config = yaml.safe_load((REPO / "params.yaml").read_text())
        config["quality_gate"]["demonstration"]["min_recall"] = gate_floor
        for stage in graph["stages"].values():
            for item in stage["deps"]:
                source = REPO / item
                if source.is_file():
                    destination = workspace / item
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
        (workspace / "params.yaml").write_text(yaml.safe_dump(config))
        dataset = workspace / training_pipeline.DATASET
        dataset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / training_pipeline.FIXTURE, dataset)
        run_dvc(workspace, "add", str(training_pipeline.DATASET))
        # Keep the production graph and substitute only its external stage commands.
        for name, stage in graph["stages"].items():
            stage["cmd"] = f"{sys.executable} stage.py {name}"
        (workspace / "dvc.yaml").write_text(yaml.safe_dump(graph))
        (workspace / "stage.py").write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "stage = sys.argv[1]\n"
            "with Path('executed').open('a') as log:\n"
            "    print(stage, file=log)\n"
            "out = Path('.pipeline')\n"
            "out.mkdir(exist_ok=True)\n"
            "if stage == 'train':\n"
            "    (out / 'model.tar.gz').write_text('model')\n"
            "    (out / 'training.json').write_text('training')\n"
            "elif stage == 'evaluate':\n"
            "    (out / 'evaluation').mkdir()\n"
            "    (out / 'evaluation/metrics').write_text('metrics')\n"
            "else:\n"
            "    lock = Path('dvc.lock').read_text()\n"
            "    assert 'model.tar.gz' in lock and 'evaluation' in lock\n"
            "    (out / 'gate.json').write_text('{}')\n"
        )
        return workspace

    first = create_workspace("first", "0/1")
    run_dvc(first, "repro", "--pull")
    run_dvc(first, "repro", "--pull")
    assert (first / "executed").read_text().splitlines() == ["train", "evaluate", "gate"]
    run_dvc(first, "push", "--run-cache", "train", "evaluate", "gate")

    second = create_workspace("second", "1/1")
    run_dvc(second, "repro", "--pull")
    assert (second / "executed").read_text().splitlines() == ["gate"]
    lock = yaml.safe_load((second / "dvc.lock").read_text())
    assert training_pipeline.DATASET.as_posix() in {
        item["path"] for item in lock["stages"]["evaluate"]["deps"]
    }
    assert json.loads((second / ".pipeline/gate.json").read_text()) == {}
