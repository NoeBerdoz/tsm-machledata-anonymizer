"""The labels of the teacher v1: every type of our training data -> one GLiNER2 label.

GLiNER2 takes its labels as plain names, so we keep the label of GLiNER2-PII's model card
when it means the same thing, and add a new label when the card has none (title, age, sex,
gender, date and others). The table and its reasons are in docs/teacher.md.

Pure standard library, so the cloud training job can copy this file next to its script.
"""

from collections.abc import Iterable, Mapping

# The 19 types of OpenPII-1M (and of open-pii-masking-500k, which adds TIME).
OPENPII = {
    "GIVENNAME": "first_name",
    "SURNAME": "last_name",
    "TITLE": "title",
    "AGE": "age",
    "SEX": "sex",
    "GENDER": "gender",
    "DATE": "date",
    "TIME": "time",
    "EMAIL": "email",
    "TELEPHONENUM": "phone_number",
    "STREET": "street_address",
    "BUILDINGNUM": "building_number",
    "CITY": "city",
    "ZIPCODE": "postal_code",
    "IDCARDNUM": "government_id",
    "SOCIALNUM": "national_id_number",
    "PASSPORTNUM": "passport_number",
    "DRIVERLICENSENUM": "drivers_license_number",
    "TAXNUM": "tax_number",
    "CREDITCARDNUMBER": "card_number",
}

# The 29 types of gretelai/synthetic_pii_finance_multilingual.
GRETEL = {
    "name": "full_name",
    "first_name": "first_name",
    "last_name": "last_name",
    "company": "company",
    "date": "date",
    "date_of_birth": "date",
    "date_time": "date",
    "time": "time",
    "email": "email",
    "phone_number": "phone_number",
    "street_address": "street_address",
    "local_latlng": "coordinates",
    "ssn": "national_id_number",
    "passport_number": "passport_number",
    "driver_license_number": "drivers_license_number",
    "iban": "iban",
    "bban": "bank_account",
    "bank_routing_number": "routing_number",
    "swift_bic_code": "swift_bic_code",
    "credit_card_number": "card_number",
    "credit_card_security_code": "card_cvv",
    "account_pin": "pin",
    "customer_id": "account_id",
    "employee_id": "employee_id",
    "user_name": "username",
    "password": "password",
    "api_key": "api_key",
    "ipv4": "ip_address",
    "ipv6": "ip_address",
}

# The Swiss values of swiss_training.py (#42).
SWISS = {
    "AVS": "national_id_number",
    "PHONE": "phone_number",
    "IBAN": "iban",
}

LABELS: dict[str, str] = {**OPENPII, **GRETEL, **SWISS}
# What the teacher is asked to find, in a fixed order.
TARGETS: list[str] = sorted(set(LABELS.values()))
# The labels that GLiNER2-PII's model card does not have.
NEW_LABELS = frozenset(
    {
        "title",
        "age",
        "sex",
        "gender",
        "date",
        "time",
        "building_number",
        "company",
        "coordinates",
        "swift_bic_code",
        "pin",
        "employee_id",
    }
)


def gliner_label(label: str) -> str:
    """The teacher's label for a dataset label. Raises KeyError for an unknown one."""
    return LABELS[label]


def to_example(text: str, entities: Iterable[Mapping]) -> dict[str, list[str]]:
    """The entities of one row as GLiNER2 wants them: label -> the distinct values, in order.

    Every target label is present, empty when the row has none, so the row also teaches the
    model what is not there. Values lose their outer spaces: OpenPII-1M writes some phone
    numbers with a trailing space in the span.
    """
    out: dict[str, list[str]] = {label: [] for label in TARGETS}
    for entity in sorted(entities, key=lambda e: (e["start"], e["end"])):
        value = text[entity["start"] : entity["end"]].strip()
        values = out[gliner_label(entity["label"])]
        if value and value not in values:
            values.append(value)
    return out
