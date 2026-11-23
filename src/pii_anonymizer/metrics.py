"""Detection metrics: strict recall, recall per type and character precision.

The definitions are in docs/evaluation.md.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from pii_anonymizer.spans import Example, Span, check_span


def coverage(text: str, spans: Sequence[Span]) -> list[bool]:
    """Mark each character of the text that falls inside at least one span.

    Overlapping spans are merged this way, so no character is counted twice.
    """
    covered = [False] * len(text)
    for span in spans:
        check_span(span, text)
        covered[span.start : span.end] = [True] * (span.end - span.start)
    return covered


def is_protected(text: str, entity: Span, masked: list[bool]) -> bool:
    """True if every non-whitespace character of the entity is masked.

    Whitespace is skipped so that an IBAN masked group by group, with its spaces left
    visible, still counts as protected.
    """
    return all(masked[i] or text[i].isspace() for i in range(entity.start, entity.end))


@dataclass
class Scores:
    """Counts over a whole test set, from which the metrics are computed."""

    n_texts: int = 0
    n_entities: int = 0
    n_protected: int = 0
    predicted_chars: int = 0
    correct_chars: int = 0
    # gold label -> [entities, protected entities]
    per_type: dict[str, list[int]] = field(default_factory=dict)

    @property
    def strict_recall(self) -> float | None:
        """Protected gold entities / all gold entities, or None without gold entities."""
        return self.n_protected / self.n_entities if self.n_entities else None

    @property
    def char_precision(self) -> float | None:
        """Share of masked characters that belong to a gold entity.

        None when nothing was masked: precision is undefined, not 0 or 1.
        """
        return self.correct_chars / self.predicted_chars if self.predicted_chars else None

    def recall_per_type(self) -> dict[str, float]:
        """Strict recall for each gold label."""
        return {label: protected / total for label, (total, protected) in self.per_type.items()}


def score(examples: Sequence[Example], predictions: Sequence[Sequence[Span]]) -> Scores:
    """Compare the predicted spans of each example with its gold entities.

    The type of a predicted span does not matter: any mask protects.
    """
    if len(examples) != len(predictions):
        raise ValueError("there must be one list of predictions per example")
    scores = Scores()
    for example, predicted in zip(examples, predictions, strict=True):
        text = example.text
        masked = coverage(text, predicted)
        gold = coverage(text, example.entities)
        scores.n_texts += 1
        for entity in example.entities:
            protected = is_protected(text, entity, masked)
            counts = scores.per_type.setdefault(entity.label, [0, 0])
            counts[0] += 1
            counts[1] += protected
            scores.n_entities += 1
            scores.n_protected += protected
        for i, char in enumerate(text):
            if masked[i] and not char.isspace():
                scores.predicted_chars += 1
                scores.correct_chars += gold[i]
    return scores
