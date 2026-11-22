import pytest

from pii_anonymizer.baselines import GLINER2_LABELS
from pii_anonymizer.swiss import KINDS
from pii_anonymizer.teacher_labels import (
    GRETEL,
    LABELS,
    NEW_LABELS,
    OPENPII,
    SWISS,
    TARGETS,
    gliner_label,
    to_example,
)

# From the dataset cards (Label Taxonomy of OpenPII-1M, Distinct PII Types of Gretel).
OPENPII_TYPES = {
    "DATE", "GIVENNAME", "SURNAME", "EMAIL", "CITY", "TITLE", "TELEPHONENUM", "AGE", "STREET",
    "BUILDINGNUM", "ZIPCODE", "IDCARDNUM", "CREDITCARDNUMBER", "DRIVERLICENSENUM", "GENDER",
    "TAXNUM", "SEX", "SOCIALNUM", "PASSPORTNUM",
}  # fmt: skip
GRETEL_TYPES = {
    "account_pin", "api_key", "bank_routing_number", "bban", "company", "credit_card_number",
    "credit_card_security_code", "customer_id", "date", "date_of_birth", "date_time",
    "driver_license_number", "email", "employee_id", "first_name", "iban", "ipv4", "ipv6",
    "last_name", "local_latlng", "name", "passport_number", "password", "phone_number", "ssn",
    "street_address", "swift_bic_code", "time", "user_name",
}  # fmt: skip


def test_every_type_of_our_data_has_a_label():
    assert OPENPII_TYPES | {"TIME"} == set(OPENPII)
    assert GRETEL_TYPES == set(GRETEL)
    assert set(KINDS.values()) == set(SWISS)


def test_the_issue_labels_are_new():
    assert {"title", "age", "sex", "gender", "date"} <= NEW_LABELS


def test_a_label_is_new_exactly_when_the_card_lacks_it():
    assert NEW_LABELS == set(TARGETS) - set(GLINER2_LABELS)


def test_targets_are_sorted_and_distinct():
    assert TARGETS == sorted(set(LABELS.values()))


def test_a_swiss_value_gets_the_label_of_its_kind():
    # A BBAN replaced by a Swiss IBAN becomes an IBAN, so only bban changes label.
    for gold, swiss in KINDS.items():
        if gold != "bban":
            assert gliner_label(gold) == gliner_label(swiss)
    assert gliner_label("bban") == "bank_account" and gliner_label("IBAN") == "iban"


def test_an_unknown_label_is_an_error():
    with pytest.raises(KeyError):
        gliner_label("FAVOURITECOLOUR")


def test_to_example():
    text = "Dr Anna Muster, 42, Anna again, 079 123 45 67"
    entities = [
        {"start": 32, "end": 45, "label": "PHONE"},
        {"start": 3, "end": 7, "label": "GIVENNAME"},
        {"start": 8, "end": 14, "label": "SURNAME"},
        {"start": 0, "end": 2, "label": "TITLE"},
        {"start": 16, "end": 18, "label": "AGE"},
        {"start": 20, "end": 24, "label": "GIVENNAME"},
    ]
    example = to_example(text, entities)
    assert list(example) == TARGETS
    assert example["first_name"] == ["Anna"]
    assert example["last_name"] == ["Muster"]
    assert example["title"] == ["Dr"]
    assert example["age"] == ["42"]
    assert example["phone_number"] == ["079 123 45 67"]
    assert sum(map(len, example.values())) == 5
