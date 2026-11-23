import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import mlflow
import pytest
import yaml
from google.api_core.exceptions import NotFound, PreconditionFailed
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from pii_anonymizer import gate, registry, tracking
from pii_anonymizer.results import RESULT_COLUMNS, replace_rows

ARCHIVE = b"small test archive"
DIGEST = hashlib.sha256(ARCHIVE).hexdigest()
DATASET_SHA = "e" * 64
GATE_TAGS = {
    "mlflow.source.git.commit": "a" * 40,
    "data.0.dvc_path": "t2-dev.jsonl",
    "data.0.dvc_hash_algorithm": "md5",
    "data.0.dvc_hash": "c" * 32,
}
TRAINING_TAGS = {
    "mlflow.source.git.commit": "d" * 40,
    "params_sha256": "f" * 64,
    "source.name": "org/dataset",
    "source.revision": "1" * 40,
    "source.split": "train",
    "source.sample_sha256": "2" * 64,
}


class FixtureBucket:
    """Emulate the GCS object operations used by the publisher and MLflow reader."""

    def __init__(self, path):
        self.path = path
        self.generation = 123
        self.uploads = []
        self.downloads = []
        self.retained = {}

    def object(self, name):
        return self.path / name

    def get_blob(self, name):
        if self.object(name).is_file():
            return SimpleNamespace(generation=self.generation)
        return None

    def replace(self, name, contents, *, retain):
        if retain:
            self.retained[name, self.generation] = self.object(name).read_bytes()
        self.object(name).write_bytes(contents)
        self.generation += 1

    def blob(self, name, generation=None, **kwargs):
        path = self.object(name)

        def upload(filename, *, content_type, if_generation_match):
            assert content_type == "application/gzip"
            assert if_generation_match == 0
            self.uploads.append(name)
            if path.exists():
                raise PreconditionFailed("object already exists")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(Path(filename).read_bytes())

        def reserve(contents, *, content_type, if_generation_match, timeout, retry):
            assert content_type == "application/json"
            assert if_generation_match == 0
            assert timeout and retry is None
            assert json.loads(contents)["gate_run_id"] == path.stem
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("x") as handle:
                    handle.write(contents)
            except FileExistsError:
                raise PreconditionFailed("reservation already exists") from None

        def download(filename, *, if_generation_match=None, raw_download=False, timeout=None):
            if generation is not None:
                assert generation == if_generation_match
                assert raw_download
            self.downloads.append((name, generation))
            if generation in (None, self.generation):
                contents = path.read_bytes()
            elif (name, generation) in self.retained:
                contents = self.retained[name, generation]
            else:
                raise NotFound("generation is gone")
            Path(filename).write_bytes(contents)

        return SimpleNamespace(
            upload_from_filename=upload,
            upload_from_string=reserve,
            download_to_filename=download,
        )

    def list_blobs(self, *, prefix, delimiter):
        # MLflow lists a prefix when checking whether its requested file is a directory.
        assert delimiter == "/"
        assert prefix.endswith("/model.tar.gz/")

        class EmptyListing(list):
            pages = [SimpleNamespace(prefixes=[])]

        return EmptyListing()


@pytest.fixture
def publication(tmp_path, monkeypatch):
    uri = (tmp_path / "mlruns").as_uri()
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_REGISTRY_URI", uri)
    monkeypatch.setenv("MLFLOW_ENABLE_TELEMETRY", "false")
    monkeypatch.setenv("MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT", "true")
    client = MlflowClient(tracking_uri=uri, registry_uri=uri)
    params = tmp_path / "params.yaml"
    config = yaml.safe_load((Path(__file__).resolve().parents[1] / "params.yaml").read_text())
    config["quality_gate"]["t2_dev_sha256"] = DATASET_SHA
    config["quality_gate"]["demonstration"]["min_recall"] = "1/2"
    config["quality_gate"]["release"].update(min_published_recall="9/10", min_char_precision="9/10")
    params.write_text(yaml.safe_dump(config))
    params_sha = hashlib.sha256(params.read_bytes()).hexdigest()
    experiments = config["tracking"]["experiments"]
    ids = {
        kind: client.create_experiment(
            experiments[kind], artifact_location=f"gs://test-bucket/runs/{kind}"
        )
        for kind in ("gate", "gate_proof")
    }
    training_id = client.create_experiment(
        experiments["training"], artifact_location="gs://test-bucket/runs/training"
    )
    training = client.create_run(training_id, tags=TRAINING_TAGS)
    client.log_param(training.info.run_id, "model_sha256", DIGEST)
    client.set_terminated(training.info.run_id, "FINISHED")

    archive = tmp_path / "candidate.tar.gz"
    archive.write_bytes(ARCHIVE)
    bucket = FixtureBucket(tmp_path / "gcs")
    monkeypatch.setattr(
        registry.storage, "Client", lambda: SimpleNamespace(bucket=lambda _: bucket)
    )
    registered_models = ("pii-student", "pii-student-demo")
    for name in registered_models:
        client.create_registered_model(name)

    def record_gate(
        profile="release",
        status="FINISHED",
        verdict="PASS",
        kind="gate",
        extra_tags=None,
        extra_params=None,
    ):
        tags = (
            GATE_TAGS
            | {
                "params_sha256": params_sha,
                "training_run_id": training.info.run_id,
            }
            | (extra_tags or {})
        )
        run_id = client.create_run(ids[kind], tags=tags).info.run_id
        for key, value in {
            "gate_profile": profile,
            "gate_status": verdict,
            "model_sha256": DIGEST,
            "benchmark_job": "evaluation-job",
            "quality_gate.t2_dev_sha256": DATASET_SHA,
            **{
                f"quality_gate.{profile}.{key}": value
                for key, value in config["quality_gate"][profile].items()
            },
            **(extra_params or {}),
        }.items():
            client.log_param(run_id, key, value)
        if status != "RUNNING":
            client.set_terminated(run_id, status)
        return run_id

    def publish(run_id, target="release", approved_params=params):
        return registry._publish(client, archive, run_id, target, "student", approved_params)

    object_name = f"runs/training/{training.info.run_id}/artifacts/models/{DIGEST}/model.tar.gz"
    return SimpleNamespace(
        client=client,
        archive=archive,
        params=params,
        params_sha=params_sha,
        training=training,
        gate_id=ids["gate"],
        bucket=bucket,
        object_name=object_name,
        record_gate=record_gate,
        publish=publish,
    )


def test_release_round_trip_and_retry(publication, tmp_path):
    p = publication
    run_id = p.record_gate()
    gate_tags = p.client.get_run(run_id).data.tags
    version = p.publish(run_id)
    assert version.name == "pii-student"
    assert version.run_id == p.training.info.run_id
    expected_uri = f"gs://test-bucket/{p.object_name}"
    assert version.source == expected_uri.removesuffix("/model.tar.gz")
    assert version.tags == {
        "archive_generation": "123",
        "archive_uri": expected_uri,
        "benchmark_job": "evaluation-job",
        "gate_status": "PASS",
        "gate_profile": "release",
        "gate_run_id": run_id,
        "gate.git_sha": GATE_TAGS["mlflow.source.git.commit"],
        "gate.params_sha256": p.params_sha,
        "gate.data.0.dvc_path": "t2-dev.jsonl",
        "gate.data.0.dvc_hash": GATE_TAGS["data.0.dvc_hash"],
        "gate.data.0.dvc_hash_algorithm": "md5",
        "gate.dataset_sha256": DATASET_SHA,
        "model_sha256": DIGEST,
        "training_run_id": p.training.info.run_id,
        "training.git_sha": TRAINING_TAGS["mlflow.source.git.commit"],
        "training.params_sha256": TRAINING_TAGS["params_sha256"],
        **{f"training.{k}": v for k, v in TRAINING_TAGS.items() if k.startswith("source.")},
    }
    assert p.bucket.downloads == [(p.object_name, 123)]
    fetched = mlflow.artifacts.download_artifacts(
        artifact_uri=f"models:/{version.name}/{version.version}/model.tar.gz",
        dst_path=str(tmp_path),
    )
    assert Path(fetched).read_bytes() == ARCHIVE

    assert p.publish(run_id).version == version.version
    assert p.bucket.uploads == [p.object_name]
    assert len(p.client.search_model_versions()) == 1
    unchanged_gate = p.client.get_run(run_id)
    assert unchanged_gate.info.status == "FINISHED"
    assert unchanged_gate.data.tags == gate_tags
    marker = p.bucket.object(f"runs/registry-publications/pii-student/{run_id}.json")
    assert json.loads(marker.read_text())["archive_generation"] == "123"


def test_demo_cli_uses_actual_gate_record(publication, tmp_path, monkeypatch, capsys):
    p = publication
    monkeypatch.setattr(tracking, "_tracking_client", lambda: p.client)
    monkeypatch.setattr(registry, "_client", lambda: p.client)
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "7")
    monkeypatch.setenv("MLFLOW_ALLOW_HTTP_REDIRECTS", "true")

    replace_rows(
        tmp_path / "results.csv",
        RESULT_COLUMNS,
        [
            {
                "dataset": "t2-dev",
                "benchmark_job": "job-1",
                "model": "checkpoint",
                "dataset_sha256": DATASET_SHA,
                "model_sha256": DIGEST,
                "n_protected": "2",
                "n_entities": "3",
            }
        ],
    )
    pointer = tmp_path / "t2-dev.jsonl.dvc"
    pointer.write_text(f"outs: [{{path: t2-dev.jsonl, md5: {GATE_TAGS['data.0.dvc_hash']}}}]\n")
    lock = tmp_path / "dvc.lock"
    lock.write_text(
        "stages:\n"
        "  train:\n"
        "    outs: [{path: .pipeline/model.tar.gz, hash: md5, md5: train-digest}]\n"
        "  evaluate:\n"
        "    outs: [{path: .pipeline/evaluation, hash: md5, md5: evaluate-digest}]\n"
    )
    training_metadata = tmp_path / "training.json"
    training_metadata.write_text(json.dumps({"run_id": p.training.info.run_id}))
    gate.main(
        [
            "checkpoint",
            "--model-file",
            str(p.archive),
            "--thresholds",
            "demonstration",
            "--benchmark-job",
            "job-1",
            "--git-sha",
            GATE_TAGS["mlflow.source.git.commit"],
            "--data-pointer",
            str(pointer),
            "--params",
            str(p.params),
            "--results-dir",
            str(tmp_path),
            "--report",
            str(tmp_path / "gate.json"),
            "--dvc-lock",
            str(lock),
            "--training-metadata",
            str(training_metadata),
        ]
    )
    [run] = p.client.search_runs([p.gate_id])
    capsys.readouterr()
    registry.main(
        [
            "--archive",
            str(p.archive),
            "--gate-run-id",
            run.info.run_id,
            "--target",
            "demo",
            "--model",
            "student",
            "--params",
            str(p.params),
        ]
    )
    assert capsys.readouterr().out == "models:/pii-student-demo/1\n"
    [version] = p.client.search_model_versions()
    assert version.name == "pii-student-demo"
    assert version.tags["gate_profile"] == "demonstration"
    assert version.tags["dvc.train..pipeline/model.tar.gz.md5"] == "train-digest"
    assert version.tags["dvc.evaluate..pipeline/evaluation.md5"] == "evaluate-digest"
    assert version.tags["gate.params_sha256"] == hashlib.sha256(p.params.read_bytes()).hexdigest()
    with pytest.raises(registry.PublicationError, match="requires the release gate"):
        p.publish(run.info.run_id)
    assert len(p.client.search_model_versions()) == 1


@pytest.mark.parametrize(
    ("options", "target", "message"),
    [
        ({"verdict": "FAIL"}, "release", "did not record PASS"),
        ({"status": "FAILED"}, "release", "must be active and FINISHED"),
        ({"status": "RUNNING"}, "release", "must be active and FINISHED"),
        ({"kind": "gate_proof", "profile": "demonstration"}, "demo", "outside the configured gate"),
        ({"extra_tags": {"synthetic_proof": "true"}}, "release", "Synthetic proof"),
        ({"profile": "demonstration"}, "release", "requires the release gate"),
        ({}, "demo", "requires the demonstration gate"),
        ({"extra_tags": {"training_run_id": ""}}, "release", "training run ID"),
        ({"extra_tags": {"params_sha256": ""}}, "release", "needs Git and params"),
        ({"extra_tags": {"data.0.dvc_hash": ""}}, "release", "Invalid run DVC"),
        (
            {"extra_params": {"quality_gate.release.min_char_precision": "1/10"}},
            "release",
            "gate thresholds differ",
        ),
        (
            {
                "extra_params": {"quality_gate.demonstration.min_recall": "1/10"},
                "profile": "demonstration",
            },
            "demo",
            "gate thresholds differ",
        ),
        (
            {"extra_params": {"quality_gate.t2_dev_sha256": "9" * 64}},
            "release",
            "gate T2-dev SHA-256 differs",
        ),
        ({"extra_tags": {"params_sha256": "b" * 64}}, "release", "differs from the approved file"),
    ],
)
def test_refuses_unsuitable_gate_without_creating_version(publication, options, target, message):
    p = publication
    with pytest.raises(registry.PublicationError, match=message):
        p.publish(p.record_gate(**options), target)
    assert not p.client.search_model_versions()
    assert not p.bucket.uploads


@pytest.mark.parametrize("failure", ["missing", "deleted", "changed_bytes", "wrong_training"])
def test_refuses_missing_or_changed_evidence(publication, failure):
    p = publication
    run_id = p.record_gate()
    if failure == "missing":
        run_id, message = "0" * 32, "gate run does not exist"
    elif failure == "deleted":
        p.client.delete_run(run_id)
        message = "must be active and FINISHED"
    elif failure == "changed_bytes":
        p.archive.write_bytes(ARCHIVE + b" changed")
        message = "does not match the gate"
    else:
        other = p.client.create_run(p.training.info.experiment_id, tags=TRAINING_TAGS)
        p.client.log_param(other.info.run_id, "model_sha256", "f" * 64)
        p.client.set_terminated(other.info.run_id, "FINISHED")
        p.client.set_tag(run_id, "training_run_id", other.info.run_id)
        message = "did not record this archive SHA-256"
    with pytest.raises(registry.PublicationError, match=message):
        p.publish(run_id)
    assert not p.client.search_model_versions()
    assert not p.bucket.uploads


def test_refuses_existing_object_with_wrong_bytes(publication):
    p = publication
    path = p.bucket.object(p.object_name)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"wrong bytes")
    with pytest.raises(registry.PublicationError, match="stored archive SHA-256"):
        p.publish(p.record_gate())
    assert not p.client.search_model_versions()
    assert not p.bucket.uploads
    assert path.read_bytes() == b"wrong bytes"


@pytest.mark.parametrize("retain", [True, False])
def test_retry_reads_recorded_generation_after_live_object_replacement(publication, retain):
    p = publication
    run_id = p.record_gate()
    first = p.publish(run_id)
    p.bucket.replace(p.object_name, ARCHIVE if not retain else b"replacement", retain=retain)
    if retain:
        second = p.publish(run_id)
        assert first.version == second.version
        assert second.tags["archive_generation"] == "123"
    else:
        with pytest.raises(registry.PublicationError, match="archive generation is unavailable"):
            p.publish(run_id)
    assert p.bucket.downloads == [(p.object_name, 123), (p.object_name, 123)]
    assert len(p.client.search_model_versions()) == 1
    assert p.bucket.uploads == [p.object_name]


@pytest.mark.parametrize("committed", [False, True])
def test_retry_after_registry_creation_error(publication, monkeypatch, committed):
    p = publication
    run_id = p.record_gate()
    create_version = p.client.create_model_version

    def failed_response(*args, **kwargs):
        if committed:
            create_version(*args, **kwargs)
        raise MlflowException("simulated lost registry response")

    with monkeypatch.context() as patch:
        patch.setattr(p.client, "create_model_version", failed_response)
        with pytest.raises(registry.PublicationError, match="Check whether the request finished"):
            p.publish(run_id)
    assert len(p.client.search_model_versions()) == int(committed)
    if not committed:
        with pytest.raises(registry.PublicationError, match="Publication is pending"):
            p.publish(run_id)
        assert not p.client.search_model_versions()
        # Simulate admin reconciliation after establishing the create never reached MLflow.
        p.bucket.object(f"runs/registry-publications/pii-student/{run_id}.json").unlink()
    assert p.publish(run_id).version == 1
    assert len(p.client.search_model_versions()) == 1
    assert p.bucket.uploads == [p.object_name]


def test_concurrent_publishers_share_one_registry_creation(publication, monkeypatch):
    p = publication
    run_id = p.record_gate()
    create_version = p.client.create_model_version
    claimed = Event()
    finish = Event()
    calls = []

    def hold_create(*args, **kwargs):
        calls.append(args[0])
        claimed.set()
        assert finish.wait(5)
        return create_version(*args, **kwargs)

    monkeypatch.setattr(p.client, "create_model_version", hold_create)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(p.publish, run_id)
        try:
            assert claimed.wait(5)
            with pytest.raises(registry.PublicationError, match="Publication is pending"):
                p.publish(run_id)
            assert p.client.search_model_versions() == []
        finally:
            finish.set()
        version = first.result(timeout=5)
    assert p.publish(run_id).version == version.version
    assert calls == ["pii-student"]
    assert len(p.client.search_model_versions()) == 1


def test_publish_with_historical_approved_params(publication, tmp_path):
    p = publication
    run_id = p.record_gate()
    historical = tmp_path / "approved-at-gate.yaml"
    historical.write_bytes(p.params.read_bytes())
    config = yaml.safe_load(p.params.read_bytes())
    config["quality_gate"]["release"]["min_published_recall"] = "99/100"
    p.params.write_text(yaml.safe_dump(config))

    with pytest.raises(registry.PublicationError, match="gate thresholds differ"):
        p.publish(run_id)
    assert not p.client.search_model_versions()
    assert not p.bucket.uploads
    assert p.publish(run_id, approved_params=historical).tags["gate.params_sha256"] == p.params_sha
