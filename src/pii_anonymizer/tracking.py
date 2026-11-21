"""Record run provenance and prove connectivity to the tracking server."""

import argparse
import hashlib
import logging
import os
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import mlflow
import yaml
from mlflow.entities import Run
from mlflow.tracking import MlflowClient
from yaml.nodes import MappingNode

_KINDS = ("laptop", "training", "gate")
_PROOF_KINDS = {"laptop": "laptop", "training": "training", "actions": "gate"}
_POINTER = Path("data/test/t2_pilot.jsonl.dvc")
_CREDENTIAL_KEY = re.compile(
    r"(?:^|[\W_])(?:(?:private|access|api)[\W_]+key|password|passwd|secret|token|credentials?"
    r"|authorization|passphrase|cookie)$",
    re.IGNORECASE,
)
_URL_USER_INFO = re.compile(r"//[^/\s?#]*@")
_EXPERIMENT_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
_PROOF_PARAMS = {f"tracking.experiments.{kind}" for kind in _KINDS}


class TrackingInputError(ValueError):
    """A tracking configuration error with a message safe to print."""


class _UniqueKeysLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict:
        mapping = super().construct_mapping(node, deep=deep)
        if len(mapping) != len(node.value):
            raise TrackingInputError("YAML mapping contains duplicate keys")
        return mapping


def _reject_url_user_info(value: str) -> None:
    if _URL_USER_INFO.search(value):
        raise TrackingInputError("Remove user info from URLs before logging parameters")


def _data_provenance(pointer: Path) -> dict[str, str]:
    data = yaml.load(pointer.read_bytes(), Loader=_UniqueKeysLoader)
    outs = data.get("outs") if isinstance(data, dict) else None
    if not isinstance(outs, list) or len(outs) != 1 or not isinstance(outs[0], dict):
        raise TrackingInputError("The DVC pointer must have exactly one output")

    output = outs[0]
    path = output.get("path")
    # Older .dvc files can specify md5 without a hash field.
    algorithm = output.get("hash", "md5")
    if not isinstance(path, str) or not path.strip() or not isinstance(algorithm, str):
        raise TrackingInputError("The DVC output needs a path and hash algorithm")
    _reject_url_user_info(path)
    try:
        hash_size = hashlib.new(algorithm, usedforsecurity=False).digest_size
    except ValueError:
        raise TrackingInputError("The DVC output needs a supported hash algorithm") from None
    digest = output.get(algorithm)
    if (
        not hash_size
        or not isinstance(digest, str)
        or not re.fullmatch(rf"[0-9a-fA-F]{{{hash_size * 2}}}(?:\.dir)?", digest)
    ):
        raise TrackingInputError("The DVC output needs a valid hash digest for its algorithm")
    return {"dvc_path": path, "dvc_hash_algorithm": algorithm, "dvc_hash": digest}


def _parameter_leaves(
    value, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], object]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not key:
                raise TrackingInputError("Parameter keys must be nonempty strings")
            _reject_url_user_info(key)
            words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
            if _CREDENTIAL_KEY.search(words):
                raise TrackingInputError("Keep credential keys out of params.yaml")
            yield from _parameter_leaves(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _parameter_leaves(child, (*path, str(index)))
    elif value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            _reject_url_user_info(value)
        yield path, value
    else:
        raise TrackingInputError("Parameters must use scalar values, sequences or mappings")


def _tracking_client() -> MlflowClient:
    uri = mlflow.get_tracking_uri()
    try:
        url = urlsplit(uri)
        valid = (
            url.scheme == "https"
            and url.hostname
            and url.username is None
            and not url.query
            and not url.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise TrackingInputError("Set MLFLOW_TRACKING_URI to an HTTPS URL without user info")
    if not os.environ.get("MLFLOW_TRACKING_USERNAME") or not os.environ.get(
        "MLFLOW_TRACKING_PASSWORD"
    ):
        raise TrackingInputError("Set MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD")
    return MlflowClient(tracking_uri=uri)


@contextmanager
def _run(
    client: MlflowClient,
    kind: str,
    data_pointers: Sequence[str | Path] | str | Path,
    params_path: Path,
    git_sha: str,
    *,
    proof_kind: str | None = None,
) -> Iterator[Run]:
    if kind not in _KINDS:
        raise TrackingInputError("Use tracking kind laptop, training or gate")
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", git_sha):
        raise TrackingInputError("Pass the full Git commit SHA")
    if mlflow.active_run() is not None:
        raise TrackingInputError("End the active MLflow run before starting a tracked run")

    pointers = [data_pointers] if isinstance(data_pointers, (str, Path)) else data_pointers
    if not pointers:
        raise TrackingInputError("Pass at least one DVC pointer")
    tags = {"mlflow.source.git.commit": git_sha}
    for index, pointer in enumerate(pointers):
        provenance = _data_provenance(Path(pointer))
        tags.update({f"data.{index}.{key}": value for key, value in provenance.items()})
    raw_params = params_path.read_bytes()
    tags["params_sha256"] = hashlib.sha256(raw_params).hexdigest()
    params = yaml.load(raw_params, Loader=_UniqueKeysLoader)

    logged_params = {}
    for path, value in _parameter_leaves(params):
        key = ".".join(path)
        if key in logged_params:
            raise TrackingInputError("Parameter keys must have unique dotted paths")
        logged_params[key] = value
    try:
        experiment_name = params["tracking"]["experiments"][kind]
    except (KeyError, TypeError) as exc:
        raise TrackingInputError(f"Set tracking.experiments.{kind} in params.yaml") from exc
    if not isinstance(experiment_name, str) or not _EXPERIMENT_NAME.fullmatch(experiment_name):
        raise TrackingInputError(f"Set tracking.experiments.{kind} to an experiment name")
    if proof_kind is not None:
        tags["client_kind"] = proof_kind
        logged_params = {key: value for key, value in logged_params.items() if key in _PROOF_PARAMS}
        if logged_params.keys() != _PROOF_PARAMS or not all(
            isinstance(value, str) and _EXPERIMENT_NAME.fullmatch(value)
            for value in logged_params.values()
        ):
            raise TrackingInputError("Set the three tracking experiment names in params.yaml")

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise TrackingInputError("The configured tracking experiment does not exist")
    run = client.create_run(experiment.experiment_id, tags=tags)
    run_id = run.info.run_id
    try:
        for key, value in logged_params.items():
            client.log_param(run_id, key, value, synchronous=True)
        active = mlflow.start_run(run_id=run_id)
        yield active
        if mlflow.active_run() is not active:
            raise RuntimeError("The tracked run must remain active until the context exits")
        mlflow.end_run("FINISHED")
    except BaseException:
        try:
            active = mlflow.active_run()
            if active is not None and active.info.run_id == run_id:
                mlflow.end_run("FAILED")
            else:
                client.set_terminated(run_id, "FAILED")
        except Exception:
            logging.getLogger(__name__).warning("Could not mark run %s as failed", run_id)
        raise


@contextmanager
def tracked_run(
    kind: str,
    data_pointers: Sequence[str | Path] | str | Path,
    params_path: str | Path,
    git_sha: str,
) -> Iterator[Run]:
    """Open a precreated experiment run for a laptop, training or gate caller.

    The run is active for fluent logging. Keep credentials in the environment.
    Pass the .dvc files in input order. Outputs in dvc.lock come with
    NoeBerdoz/tsm-machledata-anonymizer#14.
    """
    with _run(_tracking_client(), kind, data_pointers, Path(params_path), git_sha) as run:
        yield run


def main() -> None:
    parser = argparse.ArgumentParser(description="Write one MLflow connectivity proof.")
    parser.add_argument("kind", choices=_PROOF_KINDS)
    parser.add_argument("git_sha")
    args = parser.parse_args()

    os.environ["MLFLOW_SUPPRESS_PRINTING_URL_TO_STDOUT"] = "true"
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    pointer = _POINTER if _POINTER.is_file() else Path(_POINTER.name)
    try:
        with _run(
            _tracking_client(),
            _PROOF_KINDS[args.kind],
            [pointer],
            Path("params.yaml"),
            args.git_sha,
            proof_kind=args.kind,
        ) as run:
            mlflow.log_metric("connectivity", 1, synchronous=True)
    except TrackingInputError as exc:
        parser.error(str(exc))
    except Exception as exc:
        parser.exit(
            1, f"MLflow proof failed ({type(exc).__name__}). Check the inputs and connection.\n"
        )
    print(f"Experiment ID: {run.info.experiment_id}\nRun ID: {run.info.run_id}")


if __name__ == "__main__":
    main()
