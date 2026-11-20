import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from pii_anonymizer.files import read_text
from pii_anonymizer.rules import ean13_ok, find_email, find_phone, iban_ok
from pii_anonymizer.spans import Span

GENERATOR = Path(__file__).resolve().parents[1] / "scripts" / "generate_o4_requests.py"


@pytest.fixture(scope="module")
def generated_requests(tmp_path_factory):
    output = tmp_path_factory.mktemp("o4") / "requests"
    subprocess.run([sys.executable, str(GENERATOR), str(output)], check=True)
    return output


def test_o4_manifest_covers_all_planted_occurrences(generated_requests):
    manifest = generated_requests / "requests.jsonl"
    requests = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert Counter(request["lang"] for request in requests) == {"fr": 1, "de": 1, "it": 1, "en": 1}
    assert len({request["id"] for request in requests}) == len(requests)

    ids = set()
    values = set()
    formats = set()
    labels = Counter()
    repeated_labels = set()
    literal_placeholder = False

    for request in requests:
        sources = {"prompt": request["prompt"]}
        for name in request["files"]:
            path = generated_requests / name
            formats.add(path.suffix)
            sources[name] = read_text(name, path.read_bytes())
        literal_placeholder |= any("<PERSON_1>" in content for content in sources.values())
        positions = set()

        for planted in request["values"]:
            identifier, label, value = planted["id"], planted["label"], planted["value"]
            assert identifier and identifier not in ids
            assert value and value not in values
            ids.add(identifier)
            values.add(value)
            labels[label] += 1

            occurrences = planted["occurrences"]
            assert occurrences
            assert len(occurrences) == sum(text.count(value) for text in sources.values())
            for occurrence in occurrences:
                source, start, end = occurrence["source"], occurrence["start"], occurrence["end"]
                text = sources[source]
                assert 0 <= start < end <= len(text), (identifier, occurrence)
                assert text[start:end] == value, (identifier, occurrence)
                assert (source, start, end) not in positions, (identifier, occurrence)
                positions.add((source, start, end))

            occurrence_sources = {occurrence["source"] for occurrence in occurrences}
            assert request["files"][0] in occurrence_sources, identifier
            if "prompt" in occurrence_sources and len(occurrence_sources) >= 3:
                repeated_labels.add(label)
            if label == "AVS":
                digits = "".join(char for char in value if char.isdigit())
                assert digits.startswith("756") and ean13_ok(digits)
            elif label == "IBAN":
                assert value.startswith("CH") and iban_ok(value)
            elif label == "EMAIL":
                assert value.endswith(".example")
                assert find_email(value) == [Span(0, len(value), "EMAIL")]
            elif label == "PHONE":
                assert find_phone(value) == [Span(0, len(value), "PHONE")]

    assert len(ids) == 100
    assert labels == {"PERSON": 20, "EMAIL": 20, "PHONE": 20, "AVS": 20, "IBAN": 20}
    assert formats == {".pdf", ".txt", ".docx", ".csv"}
    assert {"PERSON", "IBAN"} <= repeated_labels
    assert literal_placeholder
    assert "<PERSON_1>" not in values


def test_o4_requests_are_byte_reproducible(generated_requests, tmp_path):
    another_run = tmp_path / "requests"
    subprocess.run([sys.executable, str(GENERATOR), str(another_run)], check=True)
    assert {path.name: path.read_bytes() for path in another_run.iterdir()} == {
        path.name: path.read_bytes() for path in generated_requests.iterdir()
    }
