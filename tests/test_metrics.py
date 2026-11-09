import pytest

from pii_anonymizer.metrics import score
from pii_anonymizer.spans import Example, Span

IBAN = "CH93 0076 2011 6238 5295 7"
TEXT = f"Pay to {IBAN} today."
START = TEXT.index(IBAN)
END = START + len(IBAN)


def example(text=TEXT, entities=None):
    if entities is None:
        entities = (Span(START, END, "IBAN"),)
    return Example("t-1", text, tuple(entities))


def test_fully_masked_entity_is_protected():
    scores = score([example()], [[Span(START, END, "IBAN")]])
    assert scores.strict_recall == 1.0
    assert scores.char_precision == 1.0


def test_partly_masked_iban_is_a_leak():
    # The last digits "7" and "5295" stay visible.
    visible = len("5295 7")
    scores = score([example()], [[Span(START, END - visible, "IBAN")]])
    assert scores.n_protected == 0
    assert scores.strict_recall == 0.0


def test_iban_masked_group_by_group_is_protected():
    groups = []
    position = START
    for group in IBAN.split(" "):
        groups.append(Span(position, position + len(group), "IBAN"))
        position += len(group) + 1
    scores = score([example()], [groups])
    assert scores.strict_recall == 1.0
    assert scores.char_precision == 1.0


def test_span_of_another_type_still_protects():
    scores = score([example()], [[Span(START, END, "PHONE")]])
    assert scores.strict_recall == 1.0


def test_overlapping_predictions_are_merged():
    middle = START + 10
    scores = score([example()], [[Span(START, middle + 3, "IBAN"), Span(middle, END, "IBAN")]])
    assert scores.strict_recall == 1.0
    # Overlapping characters are counted once.
    assert scores.predicted_chars == len(IBAN.replace(" ", ""))
    assert scores.char_precision == 1.0


def test_over_masking_lowers_character_precision():
    # Mask the whole text: "Pay to " and " today." are not PII.
    scores = score([example()], [[Span(0, len(TEXT), "IBAN")]])
    assert scores.strict_recall == 1.0
    iban_chars = len(IBAN.replace(" ", ""))
    all_chars = len(TEXT.replace(" ", ""))
    assert scores.char_precision == pytest.approx(iban_chars / all_chars)
    assert scores.char_precision < 1.0


def test_no_predictions_gives_undefined_precision():
    scores = score([example(), example()], [[], []])
    assert scores.strict_recall == 0.0
    assert scores.char_precision is None


def test_recall_per_type():
    text = "Anna Muster, 756.1234.5678.97, Hans Meier"
    anna = Span(0, 11, "PERSON")
    avs = Span(13, 29, "AVS")
    hans = Span(31, 41, "PERSON")
    examples = [Example("t-1", text, (anna, avs, hans))]
    # Anna and the AVS number are masked, Hans is missed.
    predictions = [[Span(0, 11, "PERSON"), Span(13, 29, "AVS")]]
    scores = score(examples, predictions)
    assert scores.recall_per_type() == {"PERSON": 0.5, "AVS": 1.0}
    assert scores.strict_recall == pytest.approx(2 / 3)


def test_recall_is_micro_over_the_dataset():
    other = Example("t-2", "no entity here", ())
    scores = score([example(), other], [[Span(START, END, "IBAN")], [Span(0, 2, "X")]])
    assert scores.strict_recall == 1.0
    assert scores.char_precision == pytest.approx(21 / 23)


def test_prediction_outside_the_text_is_refused():
    with pytest.raises(ValueError):
        score([example()], [[Span(0, len(TEXT) + 1, "IBAN")]])
