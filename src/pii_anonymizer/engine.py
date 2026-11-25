"""Local pseudonymization engine.

The regex rules of rules.py and a local model find the personal data, then each value is
replaced by a placeholder such as <PERSON_1>. The mapping table stays on the device.
"""

import functools
import json
import os
import re
from collections import Counter
from pathlib import Path

from pii_anonymizer import rules
from pii_anonymizer.spans import Span

# The folder of the detection model on this device: GLiNER2-PII as published while we
# develop, then our student (README, "Run the app").
MODEL_DIR = os.environ.get("PII_MODEL_DIR", "")
# The name that the app shows and that the feedback records.
MODEL = Path(MODEL_DIR).name or "no model"

# The model reads a few hundred words at a time and cuts longer texts itself. These chunks
# keep each call short, and the overlap keeps a value that falls on the edge of a chunk whole
# in the next one.
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200

# Each label that our models can return -> the type of its placeholder: the 42 labels of
# GLiNER2-PII's model card and the labels of our teacher (teacher_labels.py). A model with a
# label missing here does not load, so every value it finds gets a placeholder that
# restore() knows.
PLACEHOLDER_TYPES = {
    **dict.fromkeys(["person", "full_name", "first_name", "middle_name", "last_name"], "PERSON"),
    "date_of_birth": "DATE_OF_BIRTH",
    **dict.fromkeys(
        [
            "address",
            "street_address",
            "building_number",
            "city",
            "state_or_region",
            "postal_code",
            "country",
            "coordinates",
        ],
        "ADDRESS",
    ),
    "email": "EMAIL",
    "phone_number": "PHONE",
    "iban": "IBAN",
    **dict.fromkeys(
        [
            "government_id",
            "national_id_number",
            "passport_number",
            "drivers_license_number",
            "license_number",
            "tax_id",
            "tax_number",
            "employee_id",
        ],
        "ID_NUMBER",
    ),
    **dict.fromkeys(
        ["bank_account", "account_number", "routing_number", "swift_bic_code"], "BANK_ACCOUNT"
    ),
    **dict.fromkeys(["payment_card", "card_number", "card_expiry", "card_cvv"], "CARD"),
    **dict.fromkeys(["username", "account_id", "sensitive_account_id"], "USERNAME"),
    "ip_address": "IP_ADDRESS",
    **dict.fromkeys(
        ["password", "secret", "api_key", "access_token", "recovery_code", "pin"], "SECRET"
    ),
    **dict.fromkeys(
        [
            "date",
            "time",
            "sensitive_date",
            "document_date",
            "expiration_date",
            "transaction_date",
        ],
        "DATE",
    ),
    "company": "COMPANY",
    "title": "TITLE",
    "age": "AGE",
    **dict.fromkeys(["sex", "gender"], "GENDER"),
}
# The labels of rules.py.
RULE_LABELS = ["AVS", "IBAN", "PHONE", "EMAIL"]
MODEL_LABELS = sorted(set(PLACEHOLDER_TYPES.values()) - set(RULE_LABELS))

# Also matches the forms that a model writes instead of <PERSON_1>: PERSON_1, <person_1>, and
# inside brackets <PERSON-1>, <PERSON 1>. A space or a hyphen needs the brackets, so plain text
# such as "phone 1" is left alone.
_LABELS = "|".join([*RULE_LABELS, *MODEL_LABELS])
_PLACEHOLDER_LIKE = re.compile(
    rf"<?\b(?:{_LABELS})_\d+\b>?|<\s*(?:{_LABELS})[\s_-]*\d+\s*>", re.IGNORECASE
)


def _token_id(token: str) -> str:
    """PERSON_1 for <PERSON_1>, <person-1> or < PERSON 1 >: the number a token reserves."""
    return re.sub(r"[\s<>_-]+", "_", token).strip("_").upper()


def load_model(model_dir: Path):
    """Load the detection model of a local folder. Nothing else loads it, so the runtime of
    issue #72 only has to change this function.

    The folder holds GLiNER2-PII as published, a checkpoint of ours with its labels.json, or
    an int8 folder written by quantize_gliner2.py. Raises OSError if the folder is missing,
    ValueError if a label of the model has no placeholder type.
    """
    if not model_dir.is_dir():
        raise FileNotFoundError(f"No model folder at {model_dir}")
    labels_file = model_dir / "labels.json"
    if labels_file.is_file():
        labels = json.loads(labels_file.read_bytes())
    else:
        from pii_anonymizer.baselines import GLINER2_LABELS

        labels = GLINER2_LABELS  # GLiNER2-PII as published has no labels.json
    if not isinstance(labels, list) or not labels:
        raise ValueError(f"{labels_file} must hold a non-empty list of labels")
    if unknown := [label for label in labels if label not in PLACEHOLDER_TYPES]:
        raise ValueError(f"The model's labels {unknown} have no type in PLACEHOLDER_TYPES")

    # The model runs on this device: never ask the Hugging Face Hub for its files.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from pii_anonymizer.baselines import Gliner2Detector
    from pii_anonymizer.quantize_gliner2 import MANIFEST_FILE

    if (model_dir / MANIFEST_FILE).is_file():
        return Gliner2Detector(model_dir, labels=labels)
    return Gliner2Detector(checkpoint_dir=model_dir, labels=labels)


@functools.cache
def _model():
    """The model of MODEL_DIR, loaded on the first call. A failed load is tried again."""
    if not MODEL_DIR:
        raise FileNotFoundError("Set PII_MODEL_DIR to the folder of the detection model")
    return load_model(Path(MODEL_DIR))


def ask_model(text: str) -> list[tuple[str, str]]:
    """Return the (placeholder type, value) pairs that the local model finds in a text.

    Raises if the model is missing or fails.
    """
    return [
        (PLACEHOLDER_TYPES[span.label], text[span.start : span.end])
        for span in _model().detect(text)
    ]


def _pattern(value: str) -> re.Pattern:
    """Find a value of the model in the text, whole words only, ignoring the case.

    Spaces and hyphens are interchangeable: Jean-Luc and Jean Luc, or a name that a PDF breaks
    over two lines.
    """
    words = [re.escape(word) for word in re.split(r"[\s-]+", value) if word]
    return re.compile(r"(?<!\w)" + r"[\s-]+".join(words) + r"(?!\w)", re.IGNORECASE)


def _spans(text: str, patterns: dict[str, tuple[re.Pattern, str]]) -> list[tuple[int, int, str]]:
    """Return the (start, end, label) of each value to hide. Regex matches come first."""
    spans = [(span.start, span.end, span.label) for span in rules.find_all(text)]
    for pattern, label in patterns.values():
        spans += [(m.start(), m.end(), label) for m in pattern.finditer(text)]
    return spans


def _detect(texts: list[str]) -> tuple[list[list[Span]], list[str]]:
    """Return the spans to hide in each text, and the values that the model found but that are
    not in the texts as it wrote them.

    A value that the model finds in one text is also searched in the others.
    """
    found = [
        pair
        for text in texts
        for start in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP)
        for pair in ask_model(text[start : start + CHUNK_SIZE])
    ]
    # The model sometimes returns empty values, which would match everywhere.
    values = {
        value: label
        for label, value in reversed(found)
        if len(value.strip()) > 1 and re.search(r"\w", value)
    }
    patterns = {value: (_pattern(value), label) for value, label in values.items()}

    # The model may have invented a value, or written a real one differently from the text
    # (Claire Favre for Favre Claire): the code cannot tell which, so the user has to check.
    matched = [v for v, (p, _) in patterns.items() if any(p.search(text) for text in texts)]
    missed = [
        value
        for value in patterns
        if value not in matched
        # A value cut by the edge of a chunk is whole in the next chunk.
        and not any(value.lower() in other.lower() for other in matched)
    ]

    detected = []
    for text in texts:
        merged: list[list] = []
        for start, end, label in sorted(_spans(text, patterns), key=lambda s: (s[0], -s[1])):
            if merged and start < merged[-1][1]:
                # A partly masked value is a leak, so overlapping spans become one.
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end, label])
        detected.append([Span(*span) for span in merged])
    return detected, missed


def detect(text: str) -> list[Span]:
    """Return the spans of personal data in one text, sorted and without overlaps, found by the
    model and the rules exactly as pseudonymize() finds them.
    """
    return _detect([text])[0][0]


def pseudonymize(texts: list[str]) -> tuple[list[str], dict[str, str], list[str]]:
    """Return the texts with their personal data replaced, {placeholder: real value}, and the
    values that the model found but that are not in the texts as it wrote them.

    The texts share one mapping, so a value gets the same placeholder in all of them, and a
    value that the model finds in one text is also hidden in the others. The key of a value is
    its label and its exact text, so restore() writes back exactly what was replaced: "Marie
    Dupont" and "MARIE DUPONT", or a name broken over two lines, get placeholders of their own.
    """
    detected, missed = _detect(texts)

    # A text about this project can already contain <PERSON_1> or <PERSON-1>: that number is
    # skipped, so the restoration never swaps the literal text for a real value.
    taken = {_token_id(m.group()) for text in texts for m in _PLACEHOLDER_LIKE.finditer(text)}

    placeholders: dict[tuple[str, str], str] = {}
    counts: Counter[str] = Counter()
    results = []
    for text, spans in zip(texts, detected, strict=True):
        parts, position = [], 0
        for start, end, label in ((span.start, span.end, span.label) for span in spans):
            key = (label, text[start:end])
            if key not in placeholders:
                counts[label] += 1
                while f"{label}_{counts[label]}" in taken:
                    counts[label] += 1
                placeholders[key] = f"<{label}_{counts[label]}>"
            parts += [text[position:start], placeholders[key]]
            position = end
        results.append("".join(parts) + text[position:])

    return results, {token: value for (_, value), token in placeholders.items()}, missed


def restore(response: str, mapping: dict[str, str], sent: list[str]) -> tuple[str, list[str]]:
    """Return the response with the real values put back, and the placeholders left as they are.

    A placeholder that was never sent (<PERSON_3>) or that the model changed (PERSON_1,
    <person_1>, <PERSON-1>, <PERSON 1>) stays as it is and is reported, unless it was already
    in the sent texts. One
    pass, so a real value that looks like a placeholder is never replaced in turn.
    """
    literal = {m.group() for text in sent for m in _PLACEHOLDER_LIKE.finditer(text)}
    unknown: list[str] = []

    def put_back(match: re.Match) -> str:
        token = match.group()
        if token in mapping:
            return mapping[token]
        if token not in literal and token not in unknown:
            unknown.append(token)
        return token

    return _PLACEHOLDER_LIKE.sub(put_back, response), unknown
