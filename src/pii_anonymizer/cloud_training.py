"""Submit one capped Agent Platform job and recover its outputs."""

import hashlib
import json
import math
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import google.auth
import yaml
from google.api_core.exceptions import GoogleAPICallError, PreconditionFailed
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from requests import RequestException
from requests.exceptions import HTTPError

from pii_anonymizer.tracking import validate_tracking_uri
from pii_anonymizer.training_pipeline import validate_dataset, validate_gate_inputs

JOB_DIR = Path("scripts/cloud-smoke")
PARAMS = Path("params.yaml")
OUTPUT = Path(".pipeline")
PROJECT = "tsmmachledata-projet"
REGION = "europe-west4"
BUCKET = "tsm-machledata-anonymizer-training"
SERVICE_ACCOUNT = f"mlflow-training@{PROJECT}.iam.gserviceaccount.com"
JOB_ENDPOINT = f"https://{REGION}-aiplatform.googleapis.com/v1"
JOBS = f"{JOB_ENDPOINT}/projects/{PROJECT}/locations/{REGION}/customJobs"
SUBMISSION_LABEL = "submission_id"
RUNNER_TIMEOUT_MINUTES = 90
SETUP_RESERVE_SECONDS = 10 * 60
QUEUE_WAIT_SECONDS = 20 * 60
FINISH_RESERVE_SECONDS = 15 * 60


class TrainingError(RuntimeError):
    pass


def cap_seconds(hours: object, *, runner_deadline: float | None = None) -> int:
    if type(hours) not in (int, float) or not 0 < hours <= 168:
        raise TrainingError("training.max_hours must be a positive number up to 168")
    remaining = RUNNER_TIMEOUT_MINUTES * 60 - SETUP_RESERVE_SECONDS
    if runner_deadline is not None:
        remaining = min(remaining, runner_deadline - time.monotonic())
    available = max(0, math.floor(remaining - QUEUE_WAIT_SECONDS - FINISH_RESERVE_SECONDS))
    seconds = math.ceil(hours * 3600)
    if seconds > available:
        raise TrainingError(
            f"training.max_hours exceeds the Actions runner budget ({available} seconds available "
            "after reserving time for setup, queueing, cancellation, evaluation and reporting)"
        )
    return seconds


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def submission_id() -> str:
    if run := os.getenv("GITHUB_RUN_ID"):
        key = f"github:{os.environ['GITHUB_REPOSITORY']}:{run}"
    elif local_id := os.getenv("TRAINING_SUBMISSION_ID"):
        key = f"local:{local_id}"
    else:
        raise TrainingError("Set TRAINING_SUBMISSION_ID and reuse it when retrying this run")
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def claim(marker, fingerprint: str) -> bool:
    try:
        marker.upload_from_string(fingerprint, if_generation_match=0, timeout=25, retry=None)
    except PreconditionFailed:
        return False
    return True


def request(session, method: str, url: str, **kwargs) -> dict:
    response = session.request(method, url, timeout=25, allow_redirects=False, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def find_job(session, submission: str) -> str | None:
    params = {"filter": f"labels.{SUBMISSION_LABEL}={submission}", "pageSize": 2}
    result = request(session, "GET", JOBS, params=params)
    jobs = result.get("customJobs", [])
    if len(jobs) > 1 or result.get("nextPageToken"):
        raise TrainingError(f"Multiple job records for submission {submission}")
    return jobs[0]["name"] if jobs else None


def submit_once(session, bucket, submission: str, fingerprint: str, job: dict, stage_inputs) -> str:
    marker = bucket.blob(f"pipeline/{submission}/claim")
    if claim(marker, fingerprint):
        stage_inputs(bucket, f"pipeline/inputs/{submission}")
        try:
            return request(session, "POST", JOBS, json=job)["name"]
        except (RequestException, ValueError, KeyError) as exc:
            if isinstance(exc, HTTPError) and exc.response is not None:
                status = exc.response.status_code
                if 400 <= status < 500 and status != 408:
                    raise TrainingError(
                        f"Agent Platform rejected job creation (HTTP {status})"
                    ) from None
            # The service may still accept the request. Never send it again.
            print(f"Create response unavailable. Looking up submission {submission}.", flush=True)
    elif marker.download_as_text(timeout=25) != fingerprint:
        raise TrainingError(f"Submission {submission} belongs to different inputs")

    for attempt in range(6):
        if attempt:
            time.sleep(5)
        try:
            if name := find_job(session, submission):
                return name
        except RequestException:
            continue
    raise TrainingError(f"No confirmed job for submission {submission}. Reconcile by label.")


def wait_for_job(session, name: str, seconds: int, *, runner_deadline: float | None = None) -> None:
    url = f"{JOB_ENDPOINT}/{name}"
    deadline = time.monotonic() + seconds + QUEUE_WAIT_SECONDS
    if runner_deadline is not None:
        deadline = min(deadline, runner_deadline - FINISH_RESERVE_SECONDS)
    while time.monotonic() < deadline:
        try:
            job = request(session, "GET", url)
        except RequestException:
            time.sleep(10)
            continue
        state = job["state"]
        if state == "JOB_STATE_SUCCEEDED":
            return
        if state in {
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
            "JOB_STATE_PARTIALLY_SUCCEEDED",
        }:
            if reached_cap(job, seconds):
                raise TrainingError(f"Training cap of {seconds} seconds reached. Job {name}")
            raise TrainingError(f"Agent Platform job ended in {state}. Job {name}")
        time.sleep(10)
    try:
        request(session, "POST", f"{url}:cancel")
    except RequestException:
        raise TrainingError(f"Runner wait limit reached. Check and cancel job {name}") from None
    raise TrainingError(f"Runner wait limit reached. Requested cancellation of job {name}")


def reached_cap(job: dict, seconds: int) -> bool:
    started = job.get("startTime")
    if not started:
        return False
    if job.get("error", {}).get("code") == 4:
        return True
    if job["state"] == "JOB_STATE_EXPIRED" and (ended := job.get("endTime")):
        elapsed = datetime.fromisoformat(ended) - datetime.fromisoformat(started)
        return elapsed.total_seconds() >= seconds
    return False


def staged_paths() -> tuple[Path, ...]:
    return JOB_DIR / "train.py", PARAMS, Path(__file__).with_name("tracking.py")


def submission_fingerprint(job: dict) -> str:
    sources = [hashlib.sha256(path.read_bytes()).hexdigest() for path in staged_paths()]
    payload = json.dumps({"job": job, "sources": sources}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def stage_inputs(bucket, prefix: str) -> None:
    for path in staged_paths():
        bucket.blob(f"{prefix}/{path.name}").upload_from_filename(
            path, if_generation_match=0, timeout=30
        )


def download_outputs(bucket, submission: str, revision: str, name: str) -> None:
    prefix = f"pipeline/outputs/{submission}"
    metadata = json.loads(bucket.blob(f"{prefix}/training.json").download_as_text(timeout=30))
    if metadata.get("git_sha") != revision or not metadata.get("run_id"):
        raise TrainingError(f"Missing matching training metadata for job {name}")

    temporary = OUTPUT / "model.download"
    try:
        bucket.blob(f"{prefix}/model.tar.gz").download_to_filename(temporary, timeout=120)
        with temporary.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != metadata.get("model_sha256"):
            raise TrainingError(f"Archive checksum does not match job {name}")
        temporary.replace(OUTPUT / "model.tar.gz")
    finally:
        temporary.unlink(missing_ok=True)

    metadata.update(job=name, submission_id=submission)
    (OUTPUT / "training.json").write_text(json.dumps(metadata) + "\n")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    status = OUTPUT / "training-status.txt"
    status.unlink(missing_ok=True)
    identifier = "unassigned"
    try:
        config = yaml.safe_load(PARAMS.read_bytes())
        validate_dataset(validate_gate_inputs(config))
        runner_deadline = None
        if started := os.getenv("TRAINING_RUNNER_STARTED_AT"):
            remaining = int(started) + RUNNER_TIMEOUT_MINUTES * 60 - time.time()
            runner_deadline = time.monotonic() + remaining
        hours = config["training"]["max_hours"]
        seconds = cap_seconds(hours, runner_deadline=runner_deadline)
        revision = git_sha()
        identifier = submission_id()
        uri = os.environ["MLFLOW_TRACKING_URI"]
        validate_tracking_uri(uri)
        settings = yaml.safe_load((JOB_DIR / "job.yaml").read_bytes())
        container = settings["workerPoolSpecs"][0]["containerSpec"]
        settings["serviceAccount"] = SERVICE_ACCOUNT
        settings["scheduling"] = {"timeout": f"{seconds}s", "disableRetries": True}
        container["args"] = [
            f"/gcs/{BUCKET}/pipeline/inputs/{identifier}",
            f"/gcs/{BUCKET}/pipeline/outputs/{identifier}",
            revision,
            uri,
        ]
        job = {
            "displayName": f"card14-{identifier}",
            "labels": {SUBMISSION_LABEL: identifier},
            "jobSpec": settings,
        }
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        bucket = storage.Client(project=PROJECT, credentials=credentials).bucket(BUCKET)

        def stage_and_check_budget(bucket, prefix):
            stage_inputs(bucket, prefix)
            cap_seconds(hours, runner_deadline=runner_deadline)

        # Disallow automatic replays of the non-idempotent create request, even on 401.
        with AuthorizedSession(credentials, max_refresh_attempts=0) as session:
            fingerprint = submission_fingerprint(job)
            name = submit_once(
                session, bucket, identifier, fingerprint, job, stage_and_check_budget
            )
            status.write_text(f"Agent Platform job {name}\n")
            print(f"Agent Platform job {name}", flush=True)
            wait_for_job(session, name, seconds, runner_deadline=runner_deadline)
            download_outputs(bucket, identifier, revision, name)
    except (
        GoogleAPICallError,
        TrainingError,
        KeyError,
        ValueError,
        OSError,
        RequestException,
    ) as exc:
        message = str(exc) if isinstance(exc, (TrainingError, ValueError)) else type(exc).__name__
        status.write_text(f"{message} (submission {identifier})\n")
        raise SystemExit(f"{message} (submission {identifier})") from None


if __name__ == "__main__":
    main()
