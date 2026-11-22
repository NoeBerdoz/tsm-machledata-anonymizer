"""Launch the training of the teacher v1 (#46) on Agent Platform, from a laptop.

Usage:
    MLFLOW_TRACKING_URI=<tracking HTTPS URL> \\
        uv run python -m pii_anonymizer.teacher_job --trial --id <name>
    MLFLOW_TRACKING_URI=<tracking HTTPS URL> \\
        uv run python -m pii_anonymizer.teacher_job --full --id <name>

The CI launcher (cloud_training.py) needs the frozen T2-dev and caps a job at 45 minutes,
the time left in a GitHub Actions runner. The teacher needs neither, so this launcher runs
from a laptop with the group's Google login (`gcloud auth application-default login`). It
reuses the job creation and recovery of cloud_training.py:

1. it checks that the working tree is clean and HEAD is pushed, and that the training subset
   matches its DVC pointer,
2. it uploads the job's files to `pipeline/inputs/<id>/` of the training bucket and creates
   one job, capped at `teacher.max_hours` (or `teacher.trial.max_hours`),
3. it waits for the job, then downloads its outputs into `.pipeline/teacher/<id>/`.

Running it again with the same `--id` does not create a second job: it finds the first one
and waits for it. See docs/teacher.md.
"""

import argparse
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

import yaml

from pii_anonymizer import cloud_training
from pii_anonymizer.cloud_training import (
    BUCKET,
    PROJECT,
    SERVICE_ACCOUNT,
    SUBMISSION_LABEL,
    TrainingError,
)
from pii_anonymizer.tracking import validate_tracking_uri

JOB_DIR = Path("scripts/teacher")
PARAMS = Path("params.yaml")
PACKAGE = Path(__file__).parent
OUTPUT = Path(".pipeline/teacher")
OUTPUT_FILES = ("training.json", "model.tar.gz", "epoch-1.json", "epoch-1.tar.gz")


def settings_for(params: dict, mode: str) -> dict:
    """The teacher settings of params.yaml, with the trial values in trial mode."""
    settings = dict(params["teacher"])
    trial = settings.pop("trial")
    if mode == "trial":
        settings.update(trial)
    return settings


def cap_seconds(hours: object) -> int:
    if type(hours) not in (int, float) or not 0 < hours <= 12:
        raise TrainingError("teacher.max_hours must be a positive number up to 12")
    return math.ceil(hours * 3600)


def submission_id(name: str, mode: str) -> str:
    return hashlib.sha256(f"teacher:{mode}:{name}".encode()).hexdigest()[:32]


def staged_paths(pointer: Path) -> tuple[Path, ...]:
    """The files the job copies next to train.py (see scripts/teacher/job.yaml)."""
    return (
        JOB_DIR / "train.py",
        PARAMS,
        PACKAGE / "tracking.py",
        PACKAGE / "teacher_labels.py",
        pointer.with_suffix(""),
        pointer,
    )


def check_data(pointer: Path) -> None:
    """Raise TrainingError if the subset is missing or does not match its DVC pointer."""
    data = pointer.with_suffix("")
    if not data.is_file():
        raise TrainingError(f"{data} is missing: run `uv run dvc pull {pointer}`")
    expected = yaml.safe_load(pointer.read_bytes())["outs"][0]["md5"]
    with data.open("rb") as handle:
        digest = hashlib.file_digest(handle, "md5").hexdigest()
    if digest != expected:
        raise TrainingError(f"{data} does not match its DVC pointer")


def check_git() -> str:
    """The HEAD commit, after checking that the tree is clean and the commit is pushed."""
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], text=True
    )
    if dirty.strip():
        raise TrainingError("Commit your changes first: the run records the commit")
    revision = cloud_training.git_sha()
    remote = subprocess.run(
        ["git", "branch", "-r", "--contains", revision], capture_output=True, text=True
    )
    if not remote.stdout.strip():
        raise TrainingError("Push the commit first, so the run points to a commit others see")
    return revision


def build_job(submission: str, mode: str, revision: str, uri: str, seconds: int) -> dict:
    settings = yaml.safe_load((JOB_DIR / "job.yaml").read_bytes())
    settings["serviceAccount"] = SERVICE_ACCOUNT
    settings["scheduling"] = {"timeout": f"{seconds}s", "disableRetries": True}
    settings["workerPoolSpecs"][0]["containerSpec"]["args"] = [
        f"/gcs/{BUCKET}/pipeline/inputs/{submission}",
        f"/gcs/{BUCKET}/pipeline/outputs/{submission}",
        revision,
        uri,
        mode,
    ]
    return {
        "displayName": f"teacher-v1-{mode}-{submission[:8]}",
        "labels": {SUBMISSION_LABEL: submission, "model": "teacher-v1", "mode": mode},
        "jobSpec": settings,
    }


def fingerprint(job: dict, paths: tuple[Path, ...]) -> str:
    sources = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    payload = json.dumps({"job": job, "sources": sources}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def download_outputs(bucket, submission: str, revision: str) -> Path:
    """Download the job's outputs and check the archives against training.json."""
    prefix = f"pipeline/outputs/{submission}"
    folder = OUTPUT / submission
    folder.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_FILES:
        blob = bucket.blob(f"{prefix}/{name}")
        if blob.exists():
            blob.download_to_filename(folder / name, timeout=600)
    metadata = json.loads((folder / "training.json").read_text(encoding="utf-8"))
    if metadata.get("git_sha") != revision or not metadata.get("run_id"):
        raise TrainingError("The training metadata does not match this commit")
    expected = {"model.tar.gz": metadata["model_sha256"]}
    if metadata.get("epoch_1"):
        expected["epoch-1.tar.gz"] = metadata["epoch_1"]["sha256"]
    for name, digest in expected.items():
        with (folder / name).open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != digest:
                raise TrainingError(f"{name} does not match its SHA-256 in training.json")
    return folder


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch the teacher v1 training job.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--trial", action="store_const", const="trial", dest="mode")
    mode.add_argument("--full", action="store_const", const="full", dest="mode")
    parser.add_argument("--id", required=True, help="a name for this run, reused on a retry")
    args = parser.parse_args(argv)

    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    from google.cloud import storage

    try:
        params = yaml.safe_load(PARAMS.read_bytes())
        settings = settings_for(params, args.mode)
        seconds = cap_seconds(settings["max_hours"])
        pointer = Path(settings["data"])
        check_data(pointer)
        revision = check_git()
        uri = os.environ.get("MLFLOW_TRACKING_URI", "")
        validate_tracking_uri(uri)
        submission = submission_id(args.id, args.mode)
        job = build_job(submission, args.mode, revision, uri, seconds)
        paths = staged_paths(pointer)

        def stage_inputs(bucket, prefix):
            for path in paths:
                bucket.blob(f"{prefix}/{path.name}").upload_from_filename(
                    path, if_generation_match=0, timeout=300
                )

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        bucket = storage.Client(project=PROJECT, credentials=credentials).bucket(BUCKET)
        with AuthorizedSession(credentials, max_refresh_attempts=0) as session:
            name = cloud_training.submit_once(
                session, bucket, submission, fingerprint(job, paths), job, stage_inputs
            )
            print(f"Agent Platform job {name} (submission {submission}, cap {seconds} s)")
            print("Waiting for the job. Ctrl+C stops waiting, not the job.", flush=True)
            cloud_training.wait_for_job(session, name, seconds)
        folder = download_outputs(bucket, submission, revision)
    except TrainingError as exc:
        raise SystemExit(str(exc)) from None
    metadata = json.loads((folder / "training.json").read_text(encoding="utf-8"))
    print(json.dumps(metadata["metrics"], indent=2))
    print(f"Outputs in {folder}")


if __name__ == "__main__":
    main()
