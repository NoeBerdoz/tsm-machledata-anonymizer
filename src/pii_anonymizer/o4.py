"""Run the scripted O4 requests through the app without calling the backend or LLM over HTTP."""

import argparse
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from pii_anonymizer import backend, client, engine
from pii_anonymizer.baselines import load_gliner2, load_gliner2_int8
from pii_anonymizer.metrics import coverage, is_protected
from pii_anonymizer.spans import Detector, Span, check_span

APP = Path(engine.__file__).with_name("app.py")
PLACEHOLDER = re.compile(r"<[A-Z_]+_\d+>")
SEPARATOR = "\n--- O4 ---\n"
BOUNDARIES = ("backend", "sentry", "llm")
RESTORABLE_LABELS = {*engine.RULES, *engine.MODEL_LABELS}
LABELS = {
    "full_name": "PERSON",
    "first_name": "PERSON",
    "middle_name": "PERSON",
    "last_name": "PERSON",
    "phone_number": "PHONE",
    "street_address": "ADDRESS",
}


@dataclass
class Upload:
    name: str
    data: bytes

    def getvalue(self) -> bytes:
        return self.data


@dataclass
class RequestRun:
    request: dict
    sources: dict[str, str]
    detected: dict[str, list[Span]]
    captures: dict[str, list[dict]]
    restoration: dict


def placeholder_label(label: str) -> str:
    adapted = LABELS.get(label.lower(), label.upper())
    # The app has no generic token. Use a restorable label for the remaining categories.
    return adapted if adapted in RESTORABLE_LABELS else "PERSON"


def strings(value: object) -> Iterator[str]:
    """Read decoded JSON strings separately, so a hit cannot span two fields."""
    if isinstance(value, str):
        yield " ".join(value.split())
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(key)
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def trace(
    request: dict, sources: dict[str, str], detected: dict[str, list[Span]], captures: dict
) -> dict:
    masked = {name: coverage(text, detected[name]) for name, text in sources.items()}
    captured_strings = {name: list(strings(payloads)) for name, payloads in captures.items()}

    def found_in(text, label):
        value = " ".join(text.split())
        compact = label == "IBAN"
        if compact:
            value = value.replace(" ", "")
        return [
            name
            for name, fields in captured_strings.items()
            if value
            and any(value in (field.replace(" ", "") if compact else field) for field in fields)
        ]

    values = []
    for planted in request["values"]:
        occurrences = []
        for occurrence in planted["occurrences"]:
            name = occurrence["source"]
            span = Span(occurrence["start"], occurrence["end"], planted["label"])
            text = sources[name]
            check_span(span, text)
            if text[span.start : span.end] != planted["value"]:
                raise ValueError(f"{planted['id']}: value does not match its occurrence in {name}")
            occurrences.append({**occurrence, "detected": is_protected(text, span, masked[name])})
        values.append(
            {
                "id": planted["id"],
                "detected": all(item["detected"] for item in occurrences),
                "occurrences": occurrences,
                "found_in": found_in(planted["value"], planted["label"]),
            }
        )
    return {
        "values": values,
        "spans": {
            name: [
                {
                    "start": span.start,
                    "end": span.end,
                    "label": span.label,
                    "found_in": found_in(sources[name][span.start : span.end], span.label),
                }
                for span in spans
            ]
            for name, spans in detected.items()
        },
    }


def expected_restorations(source: str, spans: list[Span], masked: str) -> Iterator[tuple[str, str]]:
    """Read generated tokens at the replacement positions in the masked text."""
    source_end = masked_end = 0
    for span in spans:
        unchanged = source[source_end : span.start]
        token = PLACEHOLDER.match(masked, masked_end + len(unchanged))
        if token is None or not masked.startswith(unchanged, masked_end):
            raise ValueError("Masked text does not match the recorded mask spans")
        yield token.group(), source[span.start : span.end]
        source_end, masked_end = span.end, token.end()
    if masked[masked_end:] != source[source_end:]:
        raise ValueError("Masked text has changes after the last recorded mask span")


def check_restoration(tokens: list[str], displayed: str, expected: dict[str, str]) -> dict:
    # Separators keep each occurrence testable even if a stored value contains line breaks.
    parts = displayed.split(SEPARATOR)
    failures = [
        token
        for index, token in enumerate(tokens)
        if index >= len(parts)
        or " ".join(parts[index].split()) != " ".join(expected.get(token, token).split())
    ]
    if len(parts) > max(1, len(tokens)):
        raise ValueError("The displayed response contains extra restoration segments")
    intact = sum(token in expected for token in tokens)
    return {
        "intact": intact,
        "restored": intact - sum(token in expected for token in failures),
        "failures": failures,
    }


def run_request(request: dict, directory: Path, detector: Detector) -> RequestRun:
    paths = [directory / file for file in request["files"]]
    uploads = [Upload(path.name, path.read_bytes()) for path in paths]
    sources: dict[str, str] = {}
    detected: dict[str, list[Span]] = {}
    # Connect the Sentry test transport to captures["sentry"].append when it lands.
    captures: dict[str, list[dict]] = {name: [] for name in BOUNDARIES}
    tokens: list[str] = []
    original_spans, original_detect = engine._spans, engine._detect

    def model_and_rules(text, patterns):
        spans = detector.detect(text, lang=request["lang"])
        for span in spans:
            check_span(span, text)
        # Supply offsets directly. The app still adds its own rules and merges overlaps.
        return original_spans(text, patterns) + [
            (span.start, span.end, placeholder_label(span.label)) for span in spans
        ]

    def record_detection(texts):
        spans, missed = original_detect(texts)
        names = (["prompt"] if request["prompt"].strip() else []) + [file.name for file in uploads]
        sources.update(zip(names, texts, strict=True))
        detected.update(zip(names, spans, strict=True))
        return spans, missed

    def send_to_backend(outgoing, timeout):
        captures["backend"].append(
            {
                "url": outgoing.full_url,
                "method": outgoing.get_method(),
                "headers": dict(outgoing.header_items()),
                "body": json.loads(outgoing.data),
            }
        )
        reply = api.request(
            outgoing.get_method(),
            urlsplit(outgoing.full_url).path,
            headers=outgoing.header_items(),
            content=outgoing.data,
        )
        reply.raise_for_status()
        return BytesIO(reply.content)

    def send_to_llm(outgoing, timeout):
        payload = json.loads(outgoing.data)
        captures["llm"].append(payload)
        for message in payload["messages"]:
            if message["role"] == "user":
                tokens.extend(PLACEHOLDER.findall(message["content"]))
        return BytesIO(json.dumps({"message": {"content": SEPARATOR.join(tokens)}}).encode())

    with (
        TestClient(backend.app) as api,
        patch.dict("os.environ", {"PII_BACKEND_TOKEN": "o4-test"}),
        patch.object(st, "file_uploader", return_value=uploads),
        patch.object(engine, "ask_model", return_value=[]),
        patch.object(engine, "_spans", model_and_rules),
        patch.object(engine, "_detect", record_detection),
        patch.object(client.urllib.request, "urlopen", send_to_backend),
        patch.object(engine._opener, "open", send_to_llm),
    ):
        page = AppTest.from_file(str(APP), default_timeout=120).run()
        page.text_area[0].set_value(request["prompt"])
        page.button[0].click().run()

    if page.exception or page.error or len(captures["backend"]) != 1 or len(captures["llm"]) != 1:
        errors = [element.value for element in [*page.exception, *page.error, *page.warning]]
        raise RuntimeError(
            f"{request['id']}: request did not complete through both boundaries: {errors}"
        )

    result = page.session_state["result"]
    expected = dict(
        pair
        for (name, source), masked in zip(sources.items(), result["texts"], strict=True)
        for pair in expected_restorations(source, detected[name], masked)
    )
    restoration = check_restoration(tokens, page.code[len(sources)].value, expected)
    return RequestRun(request, sources, detected, captures, restoration)


def run(manifest: Path, detector: Detector) -> dict:
    runs = [
        run_request(json.loads(line), manifest.parent, detector)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    captures = {
        name: [payload for item in runs for payload in item.captures[name]] for name in BOUNDARIES
    }
    requests = [
        {
            "id": item.request["id"],
            "capture_counts": {name: len(payloads) for name, payloads in item.captures.items()},
            **trace(item.request, item.sources, item.detected, captures),
            "restoration": item.restoration,
        }
        for item in runs
    ]
    values = [value for request in requests for value in request["values"]]
    if not values or len({value["id"] for value in values}) != len(values):
        raise ValueError("Expected unique planted IDs in a non-empty O4 manifest")
    misses = {value["id"] for value in values if not value["detected"]}
    app_leaks = {value["id"] for value in values if value["detected"] and value["found_in"]}
    intact = sum(request["restoration"]["intact"] for request in requests)
    restored = sum(request["restoration"]["restored"] for request in requests)
    return {
        "runtime": detector.runtime,
        "planted": len(values),
        "detected": len(values) - len(misses),
        "app_leaks": sorted(app_leaks),
        "detector_misses": sorted(misses),
        "all_leaks": sorted(misses | app_leaks),
        "restored": restored,
        "intact": intact,
        "requests": requests,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("detector", choices=["gliner2", "gliner2-int8"])
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    loader = load_gliner2 if args.detector == "gliner2" else load_gliner2_int8
    report = {"detector": args.detector, **run(args.manifest, loader())}
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
