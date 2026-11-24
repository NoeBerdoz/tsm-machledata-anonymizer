from pathlib import Path

import pytest
import yaml

from pii_anonymizer import cloud_training
from pii_anonymizer.cloud_training import (
    TrainingError,
    build_job,
    cap_seconds,
    check_data,
    parse_args,
    settings_for,
    staged_paths,
    submission_fingerprint,
    submission_id,
)

PARAMS = yaml.safe_load(Path("params.yaml").read_bytes())
SHA = "0" * 40
URI = "https://mlflow.example"


def test_every_mode_shares_the_training_values():
    ci, trial, full = (settings_for(PARAMS, mode) for mode in cloud_training.MODES)
    assert "modes" not in ci
    assert full["rows"] is None and trial["rows"] == 2000 and ci["rows"] == 1000
    assert ci["epochs"] == trial["epochs"] == full["epochs"] == 2
    assert ci["data"] == full["data"]


def test_the_job_script_reads_the_same_settings():
    # train.py runs in the job, without our package, so it has its own copy of settings_for.
    source = Path("scripts/training/train.py").read_text(encoding="utf-8")
    assert 'settings.update(settings.pop("modes")[mode])' in source


def test_the_ci_cap_fits_the_runner():
    cap_seconds(settings_for(PARAMS, "ci")["max_hours"])


def test_laptop_caps_skip_the_runner_budget():
    assert cap_seconds(4, runner=False) == 4 * 3600
    with pytest.raises(TrainingError, match="Actions runner budget"):
        cap_seconds(4)


def test_laptop_submissions_differ_by_name_and_mode():
    ids = {submission_id(m, n) for n in ("a", "b") for m in ("trial", "full")}
    assert len(ids) == 4
    assert submission_id("trial", "a") == submission_id("trial", "a")


def test_arguments():
    assert parse_args([]).mode == "ci"
    assert parse_args(["--full", "--id", "x"]).mode == "full"
    for wrong in (["--trial"], ["--id", "x"], ["--trial", "--full", "--id", "x"]):
        with pytest.raises(SystemExit):
            parse_args(wrong)


def test_job():
    job = build_job("abc", "trial", SHA, URI, 1224)
    spec = job["jobSpec"]
    args = spec["workerPoolSpecs"][0]["containerSpec"]["args"]
    assert args[2:] == [SHA, URI, "trial"]
    assert args[0].endswith("/pipeline/inputs/abc") and args[1].endswith("/pipeline/outputs/abc")
    assert spec["scheduling"] == {"timeout": "1224s", "disableRetries": True}
    assert job["labels"]["submission_id"] == "abc"


def test_the_job_copies_every_staged_file():
    command = yaml.safe_load(Path("scripts/training/job.yaml").read_bytes())
    script = command["workerPoolSpecs"][0]["containerSpec"]["command"][2]
    for path in staged_paths(Path(PARAMS["training"]["data"])):
        assert path.name in script


def test_fingerprint_changes_with_the_files(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("1")
    b.write_text("2")
    job = build_job("abc", "trial", SHA, URI, 1224)
    assert submission_fingerprint(job, (a,)) != submission_fingerprint(job, (b,))
    assert submission_fingerprint(job, (a,)) == submission_fingerprint(job, (a,))


def test_check_data(tmp_path):
    data = tmp_path / "rows.jsonl"
    data.write_bytes(b"x\n")
    pointer = tmp_path / "rows.jsonl.dvc"
    pointer.write_text("outs:\n- md5: 401b30e3b8b5d629635a5c613cdb7919\n  path: rows.jsonl\n")
    check_data(pointer)
    data.write_bytes(b"y\n")
    with pytest.raises(TrainingError, match="does not match"):
        check_data(pointer)
    data.unlink()
    with pytest.raises(TrainingError, match="missing"):
        check_data(pointer)


def test_a_dirty_tree_is_refused(monkeypatch):
    monkeypatch.setattr(cloud_training.subprocess, "check_output", lambda *a, **k: " M params.yaml")
    with pytest.raises(TrainingError, match="Commit"):
        cloud_training.check_git()
