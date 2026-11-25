import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from pii_anonymizer.files import read_text

GENERATOR = Path(__file__).resolve().parents[1] / "scripts" / "generate_o2_prompts.py"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("o2") / "prompts"
    subprocess.run([sys.executable, str(GENERATOR), str(output)], check=True)
    lines = (output / "prompts.jsonl").read_text(encoding="utf-8").splitlines()
    return output, [json.loads(line) for line in lines]


def test_the_set_has_the_mix_the_issue_asks_for(generated):
    _, records = generated
    prompts = [r for r in records if not r["stress"]]
    assert len({r["id"] for r in records}) == len(records)
    assert Counter(r["lang"] for r in prompts) == {"fr": 5, "de": 5, "it": 5, "en": 5}
    assert sum(r["stress"] for r in records) == 5
    assert {r["task"] for r in prompts} == {"summary", "extraction", "table"}
    with_files = [r for r in prompts if r["files"]]
    assert len(with_files) >= 10
    suffixes = {Path(name).suffix for r in with_files for name in r["files"]}
    assert {".csv", ".pdf", ".docx"} <= suffixes
    assert any(r["repeated"] for r in prompts)


def test_every_check_is_well_formed(generated):
    _, records = generated
    for record in records:
        check = record["check"]
        if check["type"] == "exact":
            values = check["value"] if isinstance(check["value"], list) else [check["value"]]
            assert values and all(isinstance(v, str) and v.strip() for v in values)
        elif check["type"] == "json":
            assert check["fields"] and all(isinstance(v, str) for v in check["fields"].values())
        elif check["type"] == "label":
            assert len(check["options"]) >= 2 and check["expected"] in check["options"]
        else:
            pytest.fail(f"{record['id']}: unknown check type {check['type']!r}")


def test_files_extract_and_repeated_values_appear_in_two_sources(generated):
    output, records = generated
    names = [name for r in records for name in r["files"]]
    assert len(names) == len(set(names)), "a file name is used by two prompts"
    for record in records:
        sources = [record["prompt"]]
        for name in record["files"]:
            text = read_text(name, (output / name).read_bytes())
            assert text.strip(), f"{name} extracts no text"
            sources.append(text)
        for value in record["repeated"]:
            assert sum(value in source for source in sources) >= 2, (record["id"], value)


def test_the_generator_is_deterministic(generated, tmp_path):
    output, _ = generated
    subprocess.run([sys.executable, str(GENERATOR), str(tmp_path)], check=True)
    for path in output.iterdir():
        assert (tmp_path / path.name).read_bytes() == path.read_bytes(), path.name
