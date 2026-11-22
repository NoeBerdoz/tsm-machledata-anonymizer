"""Publish an exact archive after checking its authoritative MLflow gate."""

import argparse
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import mlflow
import yaml
from google.api_core.exceptions import GoogleAPIError, NotFound, PreconditionFailed
from google.auth.exceptions import GoogleAuthError
from google.cloud import storage
from mlflow.entities import Run
from mlflow.entities.model_registry import ModelVersion
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from pii_anonymizer.results import sha256_file
from pii_anonymizer.tracking import (
    TrackingInputError,
    _parameter_leaves,
    _UniqueKeysLoader,
    validate_tracking_uri,
)

_PROFILES = {"demo": "demonstration", "release": "release"}
_GIT_SHA = r"(?:[0-9a-f]{40}|[0-9a-f]{64})"
_SHA256 = r"[0-9a-f]{64}"
_GENERATION = r"[1-9][0-9]*"
_NOT_FOUND = "RESOURCE_DOES_NOT_EXIST"


class PublicationError(ValueError):
    """Publication could not be verified or completed."""


@dataclass(frozen=True)
class _Policy:
    experiments: dict[str, str]
    profile: str
    params_sha256: str
    dataset_sha256: str
    thresholds: dict[str, str]


def _approved_policy(params: Path, profile: str) -> _Policy:
    try:
        raw = params.read_bytes()
        config = yaml.load(raw, Loader=_UniqueKeysLoader)
        experiments = config["tracking"]["experiments"]
        names = {kind: experiments[kind] for kind in ("gate", "gate_proof", "training")}
        gate = config["quality_gate"]
        dataset_sha = gate["t2_dev_sha256"]
        thresholds = gate[profile]
    except (OSError, yaml.YAMLError, KeyError, TypeError):
        raise PublicationError("Cannot read the approved gate configuration") from None
    if not all(isinstance(name, str) and name.strip() for name in names.values()) or len(
        set(names.values())
    ) != len(names):
        raise PublicationError("Configure distinct gate, proof and training experiments")
    if not isinstance(dataset_sha, str) or not re.fullmatch(_SHA256, dataset_sha):
        raise PublicationError("Approved params.yaml needs the frozen T2-dev SHA-256")
    if gate.get("synthetic_proof") or not isinstance(thresholds, dict) or not thresholds:
        raise PublicationError("Approved params.yaml needs a real gate policy for this target")
    prefix = ("quality_gate", profile)
    logged = {".".join(path): str(value) for path, value in _parameter_leaves(thresholds, prefix)}
    return _Policy(names, profile, hashlib.sha256(raw).hexdigest(), dataset_sha, logged)


def _finished_run(client: MlflowClient, run_id: str, experiment_name: str, kind: str) -> Run:
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise PublicationError(f"Missing or invalid {kind} run ID")
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None or experiment.lifecycle_stage != "active":
        raise PublicationError(f"The configured {kind} experiment must exist and be active")
    try:
        run = client.get_run(run_id)
    except MlflowException as exc:
        if exc.error_code == _NOT_FOUND:
            raise PublicationError(f"The {kind} run does not exist") from None
        raise
    if run.info.experiment_id != experiment.experiment_id:
        raise PublicationError(f"The run is outside the configured {kind} experiment")
    if run.info.lifecycle_stage != "active" or run.info.status != "FINISHED":
        raise PublicationError(f"The {kind} run must be active and FINISHED")
    flags = (
        run.data.tags.get("synthetic_proof", "false"),
        run.data.params.get("quality_gate.synthetic_proof", "false"),
    )
    if (
        any(flag.lower() != "false" for flag in flags)
        or run.data.tags.get("client_kind") == "actions-proof"
    ):
        raise PublicationError("Synthetic proof runs cannot authorize publication")
    return run


def _dvc_data(tags: dict[str, str]) -> dict[str, str]:
    data = {}
    for key, path in tags.items():
        if not re.fullmatch(r"data\.[0-9]+\.dvc_path", key):
            continue
        prefix = key.removesuffix("dvc_path")
        algorithm = tags.get(prefix + "dvc_hash_algorithm", "")
        digest = tags.get(prefix + "dvc_hash", "")
        try:
            size = hashlib.new(algorithm, usedforsecurity=False).digest_size
        except ValueError:
            size = 0
        if (
            not path.strip()
            or not size
            or not re.fullmatch(rf"[0-9a-fA-F]{{{2 * size}}}(\.dir)?", digest)
        ):
            raise PublicationError("Invalid run DVC data provenance")
        data.update(
            {key: path, prefix + "dvc_hash_algorithm": algorithm, prefix + "dvc_hash": digest}
        )
    return data


def _provenance(run: Run, kind: str) -> dict[str, str]:
    tags = run.data.tags
    git_sha = tags.get("mlflow.source.git.commit", "")
    params_sha = tags.get("params_sha256", "")
    if not re.fullmatch(_GIT_SHA, git_sha) or not re.fullmatch(_SHA256, params_sha):
        raise PublicationError(f"The {kind} run needs Git and params.yaml provenance")

    data = _dvc_data(tags)
    if kind == "gate":
        dataset_sha = run.data.params.get("quality_gate.t2_dev_sha256", "")
        if data.get("data.0.dvc_path") != "t2-dev.jsonl" or not re.fullmatch(_SHA256, dataset_sha):
            raise PublicationError("The gate run needs frozen T2-dev data provenance")
        data["dataset_sha256"] = dataset_sha
    else:
        source = {
            "source.name": r"[\w.-]+/[\w.-]+",
            "source.revision": r"[0-9a-f]{40}",
            "source.split": r"[\w.-]+",
        }
        if any(key in tags for key in source):
            if not all(re.fullmatch(pattern, tags.get(key, "")) for key, pattern in source.items()):
                raise PublicationError("The training run needs a pinned upstream data source")
            data.update({key: tags[key] for key in source})
        if not data:
            raise PublicationError("The training run needs training data provenance")
        if "source.sample_sha256" in tags:
            if not re.fullmatch(_SHA256, tags["source.sample_sha256"]):
                raise PublicationError("Invalid training sample SHA-256")
            data["source.sample_sha256"] = tags["source.sample_sha256"]

    return {
        f"{kind}.{key}": value
        for key, value in {
            "git_sha": git_sha,
            "params_sha256": params_sha,
            **data,
        }.items()
    }


def _evidence(
    client: MlflowClient, policy: _Policy, gate_run_id: str, digest: str
) -> tuple[str, str, dict[str, str]]:
    gate = _finished_run(client, gate_run_id, policy.experiments["gate"], "gate")
    params = gate.data.params
    if params.get("gate_status") != "PASS":
        raise PublicationError("The gate run did not record PASS")
    if params.get("gate_profile") != policy.profile:
        raise PublicationError(f"Publication requires the {policy.profile} gate profile")
    if params.get("model_sha256") != digest:
        raise PublicationError("The archive SHA-256 does not match the gate")
    if not params.get("benchmark_job", "").strip():
        raise PublicationError("The gate run needs a benchmark job ID")
    gate_tags = _provenance(gate, "gate")
    if gate_tags["gate.dataset_sha256"] != policy.dataset_sha256:
        raise PublicationError("The gate T2-dev SHA-256 differs from approved params.yaml")
    if any(params.get(key) != value for key, value in policy.thresholds.items()):
        raise PublicationError("The gate thresholds differ from approved params.yaml")
    if gate_tags["gate.params_sha256"] != policy.params_sha256:
        raise PublicationError("The gate params.yaml SHA-256 differs from the approved file")

    training_run_id = gate.data.tags.get("training_run_id", "")
    training = _finished_run(client, training_run_id, policy.experiments["training"], "training")
    if training.data.params.get("model_sha256") != digest:
        raise PublicationError("The linked training run did not record this archive SHA-256")

    return (
        training.info.artifact_uri,
        gate.info.artifact_uri,
        {
            "gate_run_id": gate_run_id,
            "gate_profile": policy.profile,
            "gate_status": "PASS",
            "benchmark_job": params["benchmark_job"],
            "model_sha256": digest,
            "training_run_id": training_run_id,
            **gate_tags,
            **_provenance(training, "training"),
            **{
                key: value
                for key, value in gate.data.tags.items()
                if key.startswith(("dvc.train.", "dvc.evaluate."))
            },
        },
    )


def _gcs_path(artifact_root: str) -> tuple[str, str]:
    root = urlsplit(artifact_root)
    path = root.path.strip("/")
    if (
        root.scheme != "gs"
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", root.netloc)
        or root.query
        or root.fragment
        or any(
            part in (".", "..") or not re.fullmatch(r"[\w.-]+", part) for part in path.split("/")
        )
    ):
        raise PublicationError("The gate and training runs need direct GCS artifact URIs")
    return root.netloc, path


def _stage_archive(bucket: storage.Bucket, object_name: str, archive: Path) -> str:
    blob = bucket.get_blob(object_name)
    if blob is None:
        try:
            bucket.blob(object_name).upload_from_filename(
                str(archive), content_type="application/gzip", if_generation_match=0
            )
        except PreconditionFailed:
            # A concurrent writer may have created the same content-addressed object.
            pass
        blob = bucket.get_blob(object_name)
    return str(blob.generation) if blob is not None else ""


def _verify_archive(
    bucket: storage.Bucket, object_name: str, generation: str, verified: Path, digest: str
) -> None:
    if not re.fullmatch(_GENERATION, generation):
        raise PublicationError("The archive object has no retrievable GCS generation")
    number = int(generation)
    try:
        bucket.blob(object_name, generation=number).download_to_filename(
            str(verified), raw_download=True, if_generation_match=number
        )
    except (NotFound, PreconditionFailed):
        raise PublicationError("The recorded GCS archive generation is unavailable") from None
    if sha256_file(verified) != digest:
        raise PublicationError("The stored archive SHA-256 does not match the gate")


def _reserve(bucket: storage.Bucket, name: str, tags: dict[str, str]) -> bool:
    marker = bucket.blob(f"runs/registry-publications/{name}/{tags['gate_run_id']}.json")
    record = {
        key: tags[key]
        for key in (
            "gate_run_id",
            "training_run_id",
            "archive_uri",
            "archive_generation",
            "model_sha256",
        )
    }
    try:
        marker.upload_from_string(
            json.dumps(record),
            content_type="application/json",
            if_generation_match=0,
            timeout=25,
            retry=None,
        )
    except PreconditionFailed:
        return False
    return True


def _existing_version(client: MlflowClient, name: str, gate_run_id: str) -> ModelVersion | None:
    match = None
    token = None
    while True:
        page = client.search_model_versions(f"name = '{name}'", page_token=token)
        for version in page:
            if version.tags.get("gate_run_id") == gate_run_id:
                if match is not None:
                    raise PublicationError(
                        "Multiple versions reference this gate. Inspect the registry"
                    )
                match = version
        token = page.token
        if not token:
            return match


def _verify_version(
    client: MlflowClient, version: ModelVersion, source: str, tags: dict[str, str]
) -> ModelVersion:
    if (
        version.status != "READY"
        or version.run_id != tags["training_run_id"]
        or version.source != source
        or any(version.tags.get(key) != value for key, value in tags.items())
        or client.get_model_version_download_uri(version.name, version.version) != source
    ):
        raise PublicationError("The registered version does not match the verified publication")
    return version


def _publish(
    client: MlflowClient,
    archive: Path,
    gate_run_id: str,
    target: str,
    model: str,
    params: Path,
) -> ModelVersion:
    policy = _approved_policy(params, _PROFILES[target])
    name = f"pii-{model}" if target == "release" else f"pii-{model}-demo"
    with TemporaryDirectory(prefix="model-publication-") as directory:
        if not archive.is_file():
            raise PublicationError("Supply an existing archive file")
        snapshot = Path(directory) / "model.tar.gz"
        shutil.copyfile(archive, snapshot)
        digest = sha256_file(snapshot)
        evidence = _evidence(client, policy, gate_run_id, digest)
        training_root, gate_root, tags = evidence
        try:
            client.get_registered_model(name)
        except MlflowException as exc:
            if exc.error_code == _NOT_FOUND:
                raise PublicationError(f"Ask the MLflow admin to provision {name}") from None
            raise

        bucket_name, path = _gcs_path(training_root)
        if _gcs_path(gate_root)[0] != bucket_name:
            raise PublicationError("The gate and training artifacts need the same GCS bucket")
        bucket = storage.Client().bucket(bucket_name)
        object_name = f"{path}/models/{digest}/model.tar.gz"
        archive_uri = f"gs://{bucket_name}/{object_name}"
        source = archive_uri.removesuffix("/model.tar.gz")
        verified = snapshot.with_name("verified.tar.gz")
        existing = _existing_version(client, name, gate_run_id)
        generation = (
            existing.tags.get("archive_generation", "")
            if existing is not None
            else _stage_archive(bucket, object_name, snapshot)
        )
        _verify_archive(bucket, object_name, generation, verified, digest)
        if _evidence(client, policy, gate_run_id, digest) != evidence:
            raise PublicationError("Run provenance changed during publication")
        version_tags = tags | {"archive_uri": archive_uri, "archive_generation": generation}

        if existing is not None:
            return _verify_version(client, existing, source, version_tags)
        if not _reserve(bucket, name, version_tags):
            existing = _existing_version(client, name, gate_run_id)
            if existing is None:
                raise PublicationError("Publication is pending. A reservation already exists")
            recorded = existing.tags.get("archive_generation", "")
            if recorded != generation:
                _verify_archive(bucket, object_name, recorded, verified, digest)
                version_tags["archive_generation"] = recorded
            return _verify_version(client, existing, source, version_tags)

        try:
            version = client.create_model_version(
                name,
                source,
                run_id=tags["training_run_id"],
                tags=version_tags,
                await_creation_for=0,
            )
        except MlflowException as exc:
            raise PublicationError(
                f"MLflow version creation reported {exc.error_code}. "
                "Check whether the request finished before retrying the same publication"
            ) from None
        return _verify_version(client, version, source, version_tags)


def _client() -> MlflowClient:
    uri = mlflow.get_tracking_uri()
    validate_tracking_uri(uri)
    if not os.environ.get("MLFLOW_TRACKING_USERNAME") or not os.environ.get(
        "MLFLOW_TRACKING_PASSWORD"
    ):
        raise TrackingInputError("Set MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD")
    return MlflowClient(tracking_uri=uri, registry_uri=uri)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--gate-run-id", required=True)
    parser.add_argument("--target", choices=_PROFILES, required=True)
    parser.add_argument("--model", choices=("student", "teacher"), required=True)
    parser.add_argument("--params", type=Path, default=Path("params.yaml"))
    args = parser.parse_args(argv)
    # MLflow's HTTP retry policy also retries POSTs, which can create duplicate versions.
    os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "0"
    os.environ["MLFLOW_ALLOW_HTTP_REDIRECTS"] = "false"
    try:
        version = _publish(
            _client(), args.archive, args.gate_run_id, args.target, args.model, args.params
        )
    except (PublicationError, TrackingInputError) as exc:
        parser.exit(1, f"Publication failed. {exc}\n")
    except MlflowException as exc:
        parser.exit(1, f"Publication failed. MLflow reported {exc.error_code}\n")
    except (GoogleAPIError, GoogleAuthError, OSError) as exc:
        parser.exit(1, f"Publication failed. Archive access reported {type(exc).__name__}\n")
    print(f"models:/{version.name}/{version.version}")


if __name__ == "__main__":
    main()
