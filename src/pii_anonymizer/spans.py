"""Character spans, the detector interface and the test set format."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Span:
    """A piece of text with a type.

    `start` and `end` are Python string indices (code points), `end` is exclusive.
    """

    start: int
    end: int
    label: str


@dataclass(frozen=True)
class Example:
    """One record of a test set: a text and its gold entities."""

    id: str
    text: str
    entities: tuple[Span, ...]
    # The language code of the record (`lang` key), when the test set gives one.
    lang: str | None = None


class Detector(Protocol):
    """What a model must provide to be evaluated.

    - `runtime`: the runtime and its version, for example "torch 2.9.1" or "python-re 3.13".
      A downloaded model adds the commit we score, for example "torch 2.9.1 model@1cb4166".
    - `files`: every file or folder the model needs to run (weights, tokenizer, config).
      Empty for pure rules.
    - `detect`: the spans to mask in one text, of any type. `lang` is the language code of
      the text when the test set gives one (`"fr"`, `"de"`, ...), else None. Most detectors
      ignore it. Presidio needs it.
    """

    runtime: str
    files: Sequence[Path]

    def detect(self, text: str, lang: str | None = None) -> list[Span]: ...


def check_span(span: Span, text: str) -> None:
    """Raise ValueError if the span does not fit inside the text."""
    if not 0 <= span.start < span.end <= len(text):
        raise ValueError(f"span {span} does not fit a text of length {len(text)}")


def load_dataset(path: Path) -> list[Example]:
    """Read a JSONL test set: one record per line with `id`, `text` and `entities`.

    `lang` is kept when present. Other keys in a record are ignored.
    """
    examples = []
    seen_ids = set()
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            try:
                entities = tuple(Span(e["start"], e["end"], e["label"]) for e in record["entities"])
                example = Example(str(record["id"]), record["text"], entities, record.get("lang"))
                for entity in entities:
                    check_span(entity, example.text)
            except (KeyError, ValueError) as error:
                raise ValueError(f"{path}, line {line_number}: {error}") from error
            if example.id in seen_ids:
                raise ValueError(f"{path}, line {line_number}: duplicate id {example.id}")
            seen_ids.add(example.id)
            examples.append(example)
    return examples
