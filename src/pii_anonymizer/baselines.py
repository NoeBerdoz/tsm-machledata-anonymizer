"""The off-the-shelf detectors of the baselines (issue #6): regex, Presidio, GLiNER2-PII and
OpenAI Privacy Filter, and `regex+gliner2` and `regex+privacy-filter`, the regex with a model.

Each `load_*` function imports its libraries itself, so that importing this module stays
light and the evaluation script can set the thread variables before a runtime starts.
Presidio and the two models need the `baselines` dependency group (`uv sync --group baselines`).
See docs/baselines.md.
"""

import os
from importlib.metadata import version
from pathlib import Path

from pii_anonymizer.spans import Span

# Presidio: one spaCy large model per language of our test sets.
SPACY_MODELS = {
    "en": "en_core_web_lg",
    "fr": "fr_core_news_lg",
    "de": "de_core_news_lg",
    "it": "it_core_news_lg",
}

GLINER2_MODEL = "fastino/gliner2-privacy-filter-PII-multi"
# The 42 labels listed on the model card, in its order. The model only looks for the labels
# it receives, so we give it all of them.
GLINER2_LABELS = [
    # Person and names
    "person",
    "full_name",
    "first_name",
    "middle_name",
    "last_name",
    "date_of_birth",
    # Contact and address
    "email",
    "phone_number",
    "address",
    "street_address",
    "city",
    "state_or_region",
    "postal_code",
    "country",
    # Government and tax IDs
    "government_id",
    "national_id_number",
    "passport_number",
    "drivers_license_number",
    "license_number",
    "tax_id",
    "tax_number",
    # Banking and payment
    "bank_account",
    "account_number",
    "routing_number",
    "iban",
    "payment_card",
    "card_number",
    "card_expiry",
    "card_cvv",
    # Digital identity
    "username",
    "ip_address",
    "account_id",
    "sensitive_account_id",
    # Secrets and credentials
    "password",
    "secret",
    "api_key",
    "access_token",
    "recovery_code",
    # Sensitive dates
    "sensitive_date",
    "document_date",
    "expiration_date",
    "transaction_date",
]
# The model card's default threshold.
GLINER2_THRESHOLD = 0.5
# The files the model needs to run: weights, configs and tokenizer (not the card or images).
GLINER2_FILES = ["*.json", "*.safetensors"]

PRIVACY_FILTER_MODEL = "openai/privacy-filter"
# The files the transformers route needs: the weights, the config and the tokenizer. The repo
# also holds ONNX exports and an `original/` copy of the weights, which we do not use.
PRIVACY_FILTER_FILES = [
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
]


def disable_hf_telemetry() -> None:
    """Turn off Hugging Face telemetry. Call it before any Hugging Face import."""
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def set_torch_threads(torch) -> None:
    """Apply the protocol's thread counts (docs/benchmark-protocol.md).

    torch accepts the inter-op count only once per process, so a second model loaded in the
    same process (as in the tests) skips it when it is already right.
    """
    torch.set_num_threads(4)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)


def load_regex():
    from pii_anonymizer.rules import RegexDetector

    return RegexDetector()


class PresidioDetector:
    """Presidio's AnalyzerEngine with its default recognizers and score threshold.

    Presidio needs the language of the text, so `detect` must receive `lang`.
    """

    def __init__(self) -> None:
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_analyzer.predefined_recognizers import CreditCardRecognizer

        languages = list(SPACY_MODELS)
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": k, "model_name": v} for k, v in SPACY_MODELS.items()],
        }
        nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()

        registry = RecognizerRegistry(supported_languages=languages)
        registry.load_predefined_recognizers(languages=languages, nlp_engine=nlp_engine)
        # The default configuration already gives the language-independent pattern
        # recognizers (e-mail, IBAN, phone, IP, URL, date, crypto...) to every language,
        # except the credit card, which it lists for English and Italian only.
        loaded = {(type(r).__name__, r.supported_language) for r in registry.recognizers}
        for lang in languages:
            if ("CreditCardRecognizer", lang) not in loaded:
                registry.add_recognizer(CreditCardRecognizer(supported_language=lang))

        self.analyzer = AnalyzerEngine(
            registry=registry, nlp_engine=nlp_engine, supported_languages=languages
        )
        self.runtime = f"presidio-analyzer {version('presidio-analyzer')}"
        self.files = [_package_dir(name) for name in SPACY_MODELS.values()]

    def detect(self, text: str, lang: str | None = None) -> list[Span]:
        if lang not in SPACY_MODELS:
            raise ValueError(f"Presidio needs a language among {list(SPACY_MODELS)}, got {lang!r}")
        results = self.analyzer.analyze(text=text, language=lang)
        return [Span(r.start, r.end, r.entity_type) for r in results]


def _package_dir(name: str) -> Path:
    """The installed folder of a Python package, for example a spaCy model."""
    from importlib.util import find_spec

    spec = find_spec(name)
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(name)
    return Path(spec.origin).parent


def load_presidio():
    return PresidioDetector()


class Gliner2Detector:
    """GLiNER2-PII as published, on the CPU, with the card's labels and threshold.

    Long texts go through `extract_entities_long`, the library's documented way: it scans
    overlapping word chunks and gives offsets into the whole text.
    """

    def __init__(self) -> None:
        disable_hf_telemetry()
        import torch
        from gliner2 import GLiNER2
        from huggingface_hub import snapshot_download

        set_torch_threads(torch)

        local_dir = Path(snapshot_download(GLINER2_MODEL, allow_patterns=GLINER2_FILES))
        self.model = GLiNER2.from_pretrained(str(local_dir))
        self.model.to("cpu")
        self.model.eval()
        self.runtime = f"torch {torch.__version__}"
        self.files = sorted(p for p in local_dir.rglob("*") if p.is_file())
        self._no_grad = torch.inference_mode

    def detect(self, text: str, lang: str | None = None) -> list[Span]:
        with self._no_grad():
            result = self.model.extract_entities_long(
                text, GLINER2_LABELS, threshold=GLINER2_THRESHOLD, include_spans=True
            )
        spans = []
        for label, found in result["entities"].items():
            for entity in found:
                # On a long text, the last word can come back with an end one past the
                # text (seen on a Gretel document ending in "P"). We clip it to the text.
                end = min(entity["end"], len(text))
                if entity["start"] < end:
                    spans.append(Span(entity["start"], end, label))
        return sorted(spans, key=lambda s: (s.start, s.end))


def load_gliner2():
    return Gliner2Detector()


def privacy_filter_spans(entities, text: str) -> list[Span]:
    """Turn the grouped output of the token-classification pipeline into clean spans.

    The pipeline's "simple" grouping knows the B- and I- tags only. The model writes BIOES
    tags, so the E- token of an entity comes out as a group of its own, right after the rest
    (" Harry" then " Potter"). We join groups of the same label that touch. The tokens also
    carry the space before a word, so we strip the spaces at both ends, and we clip the
    span to the text.
    """
    merged: list[list] = []
    for entity in sorted(entities, key=lambda e: (e["start"], e["end"])):
        start, end = int(entity["start"]), min(int(entity["end"]), len(text))
        label = entity["entity_group"]
        if merged and merged[-1][2] == label and merged[-1][1] == start:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end, label])
    spans = []
    for start, end, label in merged:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append(Span(start, end, label))
    return spans


class PrivacyFilterDetector:
    """OpenAI Privacy Filter as published, on the CPU, through the transformers pipeline.

    We use the documented token-classification pipeline with `aggregation_strategy="simple"`:
    it takes the most likely tag of each token and groups the tokens into spans with
    character offsets. It does not run the constrained Viterbi decoder of OpenAI's own repo,
    so the operating points of the model card are not available here.
    """

    def __init__(self) -> None:
        disable_hf_telemetry()
        import torch
        import transformers
        from huggingface_hub import snapshot_download
        from transformers import pipeline

        set_torch_threads(torch)

        local_dir = Path(
            snapshot_download(PRIVACY_FILTER_MODEL, allow_patterns=PRIVACY_FILTER_FILES)
        )
        self.pipeline = pipeline(
            "token-classification",
            model=str(local_dir),
            device="cpu",
            aggregation_strategy="simple",
        )
        self.runtime = f"transformers {transformers.__version__}"
        self.files = [local_dir / name for name in PRIVACY_FILTER_FILES]

    def detect(self, text: str, lang: str | None = None) -> list[Span]:
        if not text.strip():
            return []
        return privacy_filter_spans(self.pipeline(text), text)


def load_privacy_filter():
    return PrivacyFilterDetector()


class UnionDetector:
    """Several detectors run one after the other. It masks every span that any of them finds.

    Goal O1 measures the Swiss identifiers caught by the regex and the model together, so
    the union is what it scores. The size counts only the files of `files_from`, the
    detector that has model files (the regex has none).
    """

    def __init__(self, detectors, files_from) -> None:
        self.detectors = list(detectors)
        self.runtime = " + ".join(d.runtime for d in self.detectors)
        self.files = list(files_from.files)

    def detect(self, text: str, lang: str | None = None) -> list[Span]:
        spans = set()
        for detector in self.detectors:
            spans.update(detector.detect(text, lang=lang))
        return sorted(spans, key=lambda s: (s.start, s.end, s.label))


def load_regex_gliner2():
    gliner2 = load_gliner2()
    return UnionDetector([load_regex(), gliner2], files_from=gliner2)


def load_regex_privacy_filter():
    privacy_filter = load_privacy_filter()
    return UnionDetector([load_regex(), privacy_filter], files_from=privacy_filter)
