import pytest

from pii_anonymizer.rules import RegexDetector, ean13_ok, find_all, iban_ok


def found(text):
    return [(s.label, text[s.start : s.end]) for s in find_all(text)]


@pytest.mark.parametrize("avs", ["756.9217.0769.85", "7569217076985", "756 9217 0769 85"])
def test_valid_avs_matches(avs):
    assert found(f"AVS {avs}, merci") == [("AVS", avs)]


@pytest.mark.parametrize(
    "text",
    [
        "756.9217.0769.86",  # wrong check digit
        "757.9217.0769.85",  # not 756
        "756.9217.0769.851",  # one digit too many
        "1756.9217.0769.85",  # part of a longer number
    ],
)
def test_invalid_avs_does_not_match(text):
    assert [label for label, _ in found(text)] == []


def test_ean13_check_digit():
    assert ean13_ok("7569217076985")
    assert not ean13_ok("7569217076984")
    assert not ean13_ok("756921707698")


@pytest.mark.parametrize(
    "iban",
    [
        "CH93 0076 2011 6238 5295 7",
        "CH9300762011623852957",
        "LI21 0881 0000 2324 013A A",
    ],
)
def test_valid_iban_matches(iban):
    assert found(f"Pay to {iban} today.") == [("IBAN", iban)]


@pytest.mark.parametrize(
    "text",
    [
        "CH94 0076 2011 6238 5295 7",  # wrong checksum
        "CH93 0076 2011 6238 5295",  # too short
        "DE89 3704 0044 0532 0130 00",  # not CH or LI
    ],
)
def test_invalid_iban_does_not_match(text):
    assert [label for label, _ in found(text) if label == "IBAN"] == []


def test_iban_checksum():
    assert iban_ok("CH93 0076 2011 6238 5295 7")
    assert not iban_ok("CH93 0076 2011 6238 5295 8")


@pytest.mark.parametrize(
    "phone",
    [
        "+41 79 123 45 67",
        "0041 79 123 45 67",
        "079 123 45 67",
        "021/123 45 67",
        "+41 (0)21 123 45 67",
        "079.123.45.67",
        "0791234567",
        "+41791234567",
    ],
)
def test_swiss_phone_matches(phone):
    assert found(f"Tel. {phone}.") == [("PHONE", phone)]


@pytest.mark.parametrize(
    "text",
    [
        "date 01.02.2023 12",  # a date, not a phone
        "+33 6 12 34 56 78",  # French number
        "079 123 45",  # too short
        "+41 07 123 45 67",  # no 0 after the country code
    ],
)
def test_other_numbers_are_not_phones(text):
    assert [label for label, _ in found(text) if label == "PHONE"] == []


def test_email():
    text = "Write to anna.meier+cv@uni-bern.ch, or to bob@example.org."
    assert found(text) == [("EMAIL", "anna.meier+cv@uni-bern.ch"), ("EMAIL", "bob@example.org")]
    assert found("not an address: anna@localhost") == []


def test_detector_ignores_the_language():
    text = "AVS 756.9217.0769.85"
    detector = RegexDetector()
    assert detector.detect(text) == detector.detect(text, lang="fr")
    assert detector.files == []
    assert detector.runtime.startswith("python-re ")


def test_email_with_accents_before_the_at():
    text = "Mail: noémie.d'arc@protonmail.com"
    assert found(text) == [("EMAIL", "noémie.d'arc@protonmail.com")]
