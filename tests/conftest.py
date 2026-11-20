import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

_ISOLATED_CHILD = "PII_ANONYMIZER_QUANTIZATION_TEST_CHILD"


@pytest.fixture
def isolate_quantized_engine():
    """Keep engine changes in a child process when the initial engine cannot be restored."""


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if "isolate_quantized_engine" not in pyfuncitem.fixturenames or _ISOLATED_CHILD in os.environ:
        return None

    import torch

    backend = torch.backends.quantized
    if backend.engine in backend.supported_engines:
        return None

    config = pyfuncitem.config
    filename, separator, test = pyfuncitem.nodeid.partition("::")
    selector = f"{config.rootpath / filename}{separator}{test}"
    with TemporaryDirectory() as directory:
        outcome_path = Path(directory) / "outcome.json"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                selector,
                str(outcome_path),
                *config.invocation_params.args,
            ],
            cwd=config.invocation_params.dir,
            env={**os.environ, _ISOLATED_CHILD: "1"},
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode or not outcome_path.is_file():
            pytest.fail(
                f"Isolated pytest exited with code {result.returncode}.\n"
                f"{result.stdout}{result.stderr}",
                pytrace=False,
            )
        outcome, reason = json.loads(outcome_path.read_text(encoding="utf-8"))
    if outcome == "xfail":
        pytest.xfail(reason)
    if outcome == "skip":
        pytest.skip(reason)
    return True


class _SingleTestRun:
    def __init__(self, selector):
        self.selector = selector
        self.outcome = None

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        # Pytest has parsed all the parent's options. Replace only its node selection.
        session.config.args[:] = [self.selector]

    def pytest_runtest_logreport(self, report):
        if report.skipped:
            xfail = getattr(report, "wasxfail", None)
            if xfail is not None:
                self.outcome = ("xfail", xfail)
            else:
                _, _, reason = report.longrepr
                self.outcome = ("skip", reason.removeprefix("Skipped: "))
        elif report.when == "call" and report.passed:
            self.outcome = ("pass", "")


if __name__ == "__main__":
    selector, outcome_path, *args = sys.argv[1:]
    run = _SingleTestRun(selector)
    exit_code = pytest.main(args, plugins=[run])
    if run.outcome is not None:
        Path(outcome_path).write_text(json.dumps(run.outcome), encoding="utf-8")
    raise SystemExit(exit_code)
