from pathlib import Path

import pytest
import yaml

from pii_anonymizer import teacher_job
from pii_anonymizer.cloud_training import TrainingError
from pii_anonymizer.teacher_job import (
    build_job,
    cap_seconds,
    check_data,
    fingerprint,
    settings_for,
    staged_paths,
    submission_id,
)

PARAMS = yaml.safe_load(Path("params.yaml").read_bytes())
SHA = "0" * 40
URI = "https://mlflow.example"


def test_trial_settings_override_the_full_ones():
    full = settings_for(PARAMS, "full")
    trial = settings_for(PARAMS, "trial")
    assert "trial" not in full and "trial" not in trial
    assert full["rows"] is None and trial["rows"] == 2000
    assert trial["data"].endswith("teacher-v1-candidate.jsonl.dvc")
    assert full["data"].endswith("teacher-v1.jsonl.dvc")
    assert trial["max_hours"] < full["max_hours"]
    assert trial["epochs"] == full["epochs"] == 2


def test_the_job_script_reads_the_same_settings():
    # train.py runs in the job, without our package, so it has its own copy of settings_for.
    source = Path("scripts/teacher/train.py").read_text(encoding="utf-8")
    assert 'trial = settings.pop("trial")' in source


def test_cap():
    assert cap_seconds(0.34) == 1224
    for wrong in (0, -1, 13, "1", None, True):
        with pytest.raises(TrainingError):
            cap_seconds(wrong)


def test_submission_ids_differ_by_name_and_mode():
    ids = {submission_id(n, m) for n in ("a", "b") for m in ("trial", "full")}
    assert len(ids) == 4
    assert submission_id("a", "trial") == submission_id("a", "trial")


def test_job():
    job = build_job("abc", "trial", SHA, URI, 1224)
    spec = job["jobSpec"]
    args = spec["workerPoolSpecs"][0]["containerSpec"]["args"]
    assert args[2:] == [SHA, URI, "trial"]
    assert args[0].endswith("/pipeline/inputs/abc") and args[1].endswith("/pipeline/outputs/abc")
    assert spec["scheduling"] == {"timeout": "1224s", "disableRetries": True}
    assert job["labels"]["submission_id"] == "abc"


def test_the_job_copies_every_staged_file():
    command = yaml.safe_load(Path("scripts/teacher/job.yaml").read_bytes())
    script = command["workerPoolSpecs"][0]["containerSpec"]["command"][2]
    pointer = Path("data/train/teacher-v1-candidate.jsonl.dvc")
    paths = staged_paths(pointer)
    assert paths["teacher-v1.jsonl"] == pointer.with_suffix("")
    assert paths["teacher-v1.jsonl.dvc"] == pointer
    for name in paths:
        assert name in script


def test_fingerprint_changes_with_the_files(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("1")
    b.write_text("2")
    job = build_job("abc", "trial", SHA, URI, 1224)
    assert fingerprint(job, (a,)) != fingerprint(job, (b,))
    assert fingerprint(job, (a,)) == fingerprint(job, (a,))


def test_check_data(tmp_path):
    data = tmp_path / "rows.jsonl"
    data.write_bytes(b"x\n")
    pointer = tmp_path / "rows.jsonl.dvc"
    pointer.write_text("outs:\n- md5: 401b30e3b8b5d629635a5c613cdb7919\n  path: rows.jsonl\n")
    check_data(pointer)
    for reference_md5 in (None, "0" * 32):
        with pytest.raises(TrainingError, match="T2-validated"):
            check_data(pointer, mode="full", reference_md5=reference_md5)
    check_data(pointer, mode="full", reference_md5="401b30e3b8b5d629635a5c613cdb7919")
    data.write_bytes(b"y\n")
    with pytest.raises(TrainingError, match="does not match"):
        check_data(pointer)
    data.unlink()
    with pytest.raises(TrainingError, match="missing"):
        check_data(pointer)


def test_a_dirty_tree_is_refused(monkeypatch):
    monkeypatch.setattr(teacher_job.subprocess, "check_output", lambda *a, **k: " M params.yaml")
    with pytest.raises(TrainingError, match="Commit"):
        teacher_job.check_git()
