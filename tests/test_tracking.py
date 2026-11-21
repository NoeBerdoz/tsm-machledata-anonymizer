import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import mlflow
import pytest

from pii_anonymizer import tracking

SHA = "a" * 40
DIGEST = "46fafb36a9b05bee9d58a075e206c3cb"
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "https://tracking.example")
    monkeypatch.setenv("MLFLOW_TRACKING_USERNAME", "training")
    monkeypatch.setenv("MLFLOW_TRACKING_PASSWORD", "test-placeholder")
    monkeypatch.setenv("MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT", "true")


@pytest.fixture
def inputs(tmp_path):
    pointer = tmp_path / "t2_pilot.jsonl.dvc"
    pointer.write_text(f"outs:\n- path: t2_pilot.jsonl\n  hash: md5\n  md5: {DIGEST}\n")
    params = tmp_path / "params.yaml"
    params.write_bytes(
        b"tracking:\n  experiments:\n    laptop: tsm-team\n    training: tsm-training\n"
        b"    gate: tsm-gates\ntrain:\n  max_tokens: 384\n"
    )
    return pointer, params


@pytest.fixture
def client(monkeypatch, credentials):
    client = Mock()
    client.get_experiment_by_name.return_value = SimpleNamespace(experiment_id="17")
    run = SimpleNamespace(info=SimpleNamespace(run_id="run-id", experiment_id="17"))
    client.create_run.return_value = run
    active = None

    def start_run(run_id):
        nonlocal active
        assert run_id == run.info.run_id
        active = run
        return run

    def end_run(status):
        nonlocal active
        active = None
        client.set_terminated(run.info.run_id, status)

    monkeypatch.setattr(tracking, "MlflowClient", Mock(return_value=client))
    monkeypatch.setattr(mlflow, "active_run", lambda: active)
    monkeypatch.setattr(mlflow, "start_run", start_run)
    monkeypatch.setattr(mlflow, "end_run", end_run)
    monkeypatch.setattr(mlflow, "log_metric", Mock())
    return client


def test_tracked_run_records_multiple_pointers_and_hashes_raw_yaml(inputs, client):
    pointer, params = inputs
    other = pointer.with_name("other.dvc")
    other.write_text(f"outs: [{{path: train-data, md5: {DIGEST}.dir}}]\n")
    first = params.read_bytes()
    with tracking.tracked_run("training", [pointer, other], params, SHA) as run:
        assert run.info.run_id == "run-id"

    client.get_experiment_by_name.assert_called_once_with("tsm-training")
    client.create_run.assert_called_once_with(
        "17",
        tags={
            "mlflow.source.git.commit": SHA,
            "data.0.dvc_path": "t2_pilot.jsonl",
            "data.0.dvc_hash_algorithm": "md5",
            "data.0.dvc_hash": DIGEST,
            "data.1.dvc_path": "train-data",
            "data.1.dvc_hash_algorithm": "md5",
            "data.1.dvc_hash": f"{DIGEST}.dir",
            "params_sha256": hashlib.sha256(first).hexdigest(),
        },
    )
    client.log_param.assert_any_call("run-id", "train.max_tokens", 384, synchronous=True)
    client.set_terminated.assert_called_once_with("run-id", "FINISHED")

    second = first + b"# Same settings, different file bytes\r\n"
    params.write_bytes(second)
    with tracking.tracked_run("training", *inputs, SHA):
        pass
    assert client.create_run.call_args.kwargs["tags"]["params_sha256"] == (
        hashlib.sha256(second).hexdigest()
    )


def test_synthetic_gate_uses_its_own_experiment(inputs, client):
    pointer, params = inputs
    params.write_text(
        params.read_text().replace(
            "    gate: tsm-gates\n", "    gate: tsm-gates\n    gate_proof: tsm-gates-proof\n"
        )
    )
    with tracking.tracked_run("gate", pointer, params, SHA, proof_gate=True):
        pass
    client.get_experiment_by_name.assert_called_once_with("tsm-gates-proof")


@pytest.mark.parametrize("key", ["max_tokens", "special_tokens", "tokenizer"])
def test_tracking_logs_model_parameter_names(inputs, client, key):
    _, params = inputs
    params.write_text(params.read_text().replace("max_tokens: 384", f"{key}: model-setting"))
    with tracking.tracked_run("training", *inputs, SHA):
        pass
    client.log_param.assert_any_call("run-id", f"train.{key}", "model-setting", synchronous=True)


@pytest.mark.parametrize(
    ("pointer_text", "error"),
    [
        ("outs: []\n", "exactly one output"),
        ("outs: [{path: first}, {path: second}]\n", "exactly one output"),
        ("outs: [{hash: md5}]\n", "path and hash algorithm"),
        ("outs: [{path: data, hash: md5}]\n", "valid hash digest"),
        ("outs: [{path: data, md5: pending}]\n", "valid hash digest"),
        (f"outs: [{{path: data, hash: sha256, sha256: {DIGEST}}}]\n", "valid hash digest"),
        ("outs: [{path: data, md5: first, md5: second}]\n", "duplicate keys"),
    ],
)
def test_invalid_dvc_provenance_never_opens_run(inputs, client, pointer_text, error):
    pointer, _ = inputs
    pointer.write_text(pointer_text)
    with pytest.raises(ValueError, match=error), tracking.tracked_run("gate", *inputs, SHA):
        pytest.fail("invalid provenance opened a run")
    client.get_experiment_by_name.assert_not_called()
    client.create_run.assert_not_called()


def test_missing_pointer_never_opens_run(inputs, client):
    inputs[0].unlink()
    with pytest.raises(FileNotFoundError), tracking.tracked_run("gate", *inputs, SHA):
        pytest.fail("missing pointer opened a run")
    client.create_run.assert_not_called()


def test_missing_experiment_is_not_created(inputs, client):
    client.get_experiment_by_name.return_value = None
    with (
        pytest.raises(ValueError, match="does not exist"),
        tracking.tracked_run("gate", *inputs, SHA),
    ):
        pytest.fail("missing experiment opened a run")
    client.create_run.assert_not_called()
    client.create_experiment.assert_not_called()


def test_logging_failure_marks_run_failed_and_keeps_original_error(inputs, client):
    client.log_param.side_effect = RuntimeError("cannot log")
    client.set_terminated.side_effect = RuntimeError("cannot terminate")
    with (
        pytest.raises(RuntimeError, match="cannot log"),
        tracking.tracked_run("gate", *inputs, SHA),
    ):
        pytest.fail("logging failed before yielding")
    client.set_terminated.assert_called_once_with("run-id", "FAILED")


def test_caller_failure_marks_run_failed(inputs, client):
    with (
        pytest.raises(RuntimeError, match="training failed"),
        tracking.tracked_run("training", *inputs, SHA),
    ):
        raise RuntimeError("training failed")
    client.set_terminated.assert_called_once_with("run-id", "FAILED")


def test_fluent_metric_uses_the_active_run(inputs, tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", (tmp_path / "mlruns").as_uri())
    client = tracking.MlflowClient()
    experiment_id = client.create_experiment("tsm-training")
    monkeypatch.setattr(tracking, "_tracking_client", lambda: client)

    with tracking.tracked_run("training", *inputs, SHA) as run:
        assert mlflow.active_run().info.run_id == run.info.run_id
        mlflow.log_metric("check", 1, synchronous=True)

    assert mlflow.active_run() is None
    assert client.get_run(run.info.run_id).data.metrics == {"check": 1}
    assert [item.info.run_id for item in client.search_runs([experiment_id])] == [run.info.run_id]


@pytest.mark.parametrize(
    ("kind", "experiment"),
    [("laptop", "tsm-team"), ("training", "tsm-training"), ("actions", "tsm-gates")],
)
def test_proof_reads_repository_files(client, monkeypatch, capsys, kind, experiment):
    params = REPO / "params.yaml"
    monkeypatch.chdir(REPO)
    monkeypatch.setattr("sys.argv", ["tracking.py", kind, SHA])

    tracking.main()

    client.get_experiment_by_name.assert_called_once_with(experiment)
    tags = client.create_run.call_args.kwargs["tags"]
    assert tags["client_kind"] == kind
    assert tags["data.0.dvc_path"] == "t2_pilot.jsonl"
    assert tags["data.0.dvc_hash"] == DIGEST
    assert tags["params_sha256"] == hashlib.sha256(params.read_bytes()).hexdigest()
    assert "params_yaml" not in tags
    assert client.log_param.call_count == 3
    mlflow.log_metric.assert_called_once_with("connectivity", 1, synchronous=True)
    assert capsys.readouterr().out == "Experiment ID: 17\nRun ID: run-id\n"


def test_staged_proof_does_not_log_comments_or_other_values(inputs, client, monkeypatch):
    pointer, params = inputs
    with params.open("a") as handle:
        handle.write("# example comment\n  description: example value\n")
    monkeypatch.chdir(pointer.parent)
    monkeypatch.setattr("sys.argv", ["tracking.py", "training", SHA])
    tracking.main()

    tags = client.create_run.call_args.kwargs["tags"]
    assert tags["params_sha256"] == hashlib.sha256(params.read_bytes()).hexdigest()
    assert "params_yaml" not in tags
    assert client.log_param.call_count == 3
    assert all("tracking.experiments." in call.args[1] for call in client.log_param.call_args_list)


@pytest.mark.parametrize(
    ("line", "error"),
    [
        ("  options: [{api_key: null}]\n", "credential keys"),
        ("  checkpointToken: null\n", "credential keys"),
        ("  upstream_password: {}\n", "credential keys"),
        ("  private_key: null\n", "credential keys"),
        ("  aws_secret_access_key: null\n", "credential keys"),
        ("  storage_access_key: null\n", "credential keys"),
        ("  db_passwd: null\n", "credential keys"),
        ("  signing_secret: null\n", "credential keys"),
        ("  service_credential: null\n", "credential keys"),
        ("  service_credentials: []\n", "credential keys"),
        ("  headers: {Authorization: null}\n", "credential keys"),
        ("  signing_passphrase: null\n", "credential keys"),
        ("  headers: {session_COOKIE: null}\n", "credential keys"),
        ("  source: https://user@example.invalid/path\n", "Remove user info"),
    ],
)
def test_credential_parameters_are_rejected_before_creating_a_run(
    inputs, client, monkeypatch, capsys, line, error
):
    pointer, params = inputs
    with params.open("a") as handle:
        handle.write(line)
    with pytest.raises(ValueError, match=error), tracking.tracked_run("training", *inputs, SHA):
        pytest.fail("credential parameter opened a run")
    monkeypatch.chdir(pointer.parent)
    monkeypatch.setattr("sys.argv", ["tracking.py", "training", SHA])
    with pytest.raises(SystemExit, match="2"):
        tracking.main()
    assert error in capsys.readouterr().err
    client.get_experiment_by_name.assert_not_called()
    client.create_run.assert_not_called()


def test_proof_rejects_short_commit(client, monkeypatch, capsys):
    monkeypatch.chdir(REPO)
    monkeypatch.setattr("sys.argv", ["tracking.py", "laptop", SHA[:8]])
    with pytest.raises(SystemExit, match="2"):
        tracking.main()
    assert "full Git commit SHA" in capsys.readouterr().err
    client.create_run.assert_not_called()


def test_proof_error_hides_tracking_address(client, monkeypatch, capsys):
    monkeypatch.chdir(REPO)
    monkeypatch.setattr("sys.argv", ["tracking.py", "laptop", SHA])
    client.get_experiment_by_name.side_effect = RuntimeError("Failed: https://tracking.example")
    with pytest.raises(SystemExit, match="1"):
        tracking.main()
    captured = capsys.readouterr()
    assert "MLflow proof failed" in captured.err
    assert "tracking.example" not in captured.err + captured.out


@pytest.mark.parametrize("uri", ["http://tracking.example", "https://user@tracking.example"])
def test_both_entry_points_reject_unsafe_tracking_uri(inputs, client, monkeypatch, capsys, uri):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    with (
        pytest.raises(ValueError, match="HTTPS URL without user info"),
        tracking.tracked_run("laptop", *inputs, SHA),
    ):
        pytest.fail("unsafe URI opened a run")
    monkeypatch.setattr("sys.argv", ["tracking.py", "laptop", SHA])
    with pytest.raises(SystemExit, match="2"):
        tracking.main()
    captured = capsys.readouterr()
    assert "HTTPS URL without user info" in captured.err
    assert uri not in captured.err + captured.out
    tracking.MlflowClient.assert_not_called()
