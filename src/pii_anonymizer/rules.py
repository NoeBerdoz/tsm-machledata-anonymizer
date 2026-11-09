"""Regular expressions for Swiss identifiers, with their checksums.

Pure standard library. Labels: AVS, IBAN, PHONE, EMAIL.

- AVS: the Swiss social security number, 756 then 10 digits, written plain or with dots or
  spaces (756.1234.5678.97). The last digit is an EAN-13 check digit.
- IBAN: Swiss (CH) and Liechtenstein (LI) IBANs, 21 characters, spaces allowed between
  characters (CH93 0076 2011 6238 5295 7). The mod-97 checksum must hold.
- PHONE: Swiss numbers starting with +41, 0041 or a national 0, then nine digits in the usual
  groups (079 123 45 67, +41 79 123 45 67, +41 (0)79 123 45 67), separated by spaces, dots,
  dashes or slashes.
- EMAIL: e-mail addresses. The part before the @ may hold accented letters (noémie@...),
  the domain is ASCII.
"""

import re
import sys

from pii_anonymizer.spans import Span

_SEP = r"[ .]?"
_AVS = re.compile(rf"(?<![\d.])756{_SEP}\d{{4}}{_SEP}\d{{4}}{_SEP}\d{{2}}(?![\d])")

_IBAN = re.compile(r"(?<![0-9A-Za-z])(?:CH|LI)\d{2}(?: ?[0-9A-Z]){17}(?![0-9A-Za-z])")

_PHONE_SEP = r"[ ./-]?"
_PHONE_GROUPS = rf"[1-9]\d{_PHONE_SEP}\d{{3}}{_PHONE_SEP}\d{{2}}{_PHONE_SEP}\d{{2}}"
_PHONE = re.compile(
    rf"(?<![\w+])(?:(?:\+|00)41{_PHONE_SEP}(?:\(0\){_PHONE_SEP})?|\b0){_PHONE_GROUPS}(?!\d)"
)

_EMAIL = re.compile(
    r"(?<![\w.%+'-])[\w.%+'-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
    r"(?![\w-])"
)


def ean13_ok(digits: str) -> bool:
    """True if the 13th digit is the EAN-13 check digit of the first 12."""
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == int(digits[12])


def iban_ok(iban: str) -> bool:
    """True if the IBAN (spaces removed) passes the ISO 13616 mod-97 check."""
    iban = iban.replace(" ", "").upper()
    if len(iban) < 5 or not iban.isalnum():
        return False
    rearranged = iban[4:] + iban[:4]
    number = "".join(str(int(c, 36)) for c in rearranged)
    return int(number) % 97 == 1


def find_avs(text: str) -> list[Span]:
    spans = []
    for match in _AVS.finditer(text):
        if ean13_ok(re.sub(r"[ .]", "", match.group())):
            spans.append(Span(match.start(), match.end(), "AVS"))
    return spans


def find_iban(text: str) -> list[Span]:
    spans = []
    for match in _IBAN.finditer(text):
        if iban_ok(match.group()):
            spans.append(Span(match.start(), match.end(), "IBAN"))
    return spans


def find_phone(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "PHONE") for m in _PHONE.finditer(text)]


def find_email(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "EMAIL") for m in _EMAIL.finditer(text)]


def find_all(text: str) -> list[Span]:
    """Every identifier found in the text, sorted by position."""
    spans = find_avs(text) + find_iban(text) + find_phone(text) + find_email(text)
    return sorted(spans, key=lambda s: (s.start, s.end))


class RegexDetector:
    """The rules above as a detector. It has no model files, so its size stays empty."""

    runtime = f"python-re {sys.version_info.major}.{sys.version_info.minor}"
    files: list = []

    def detect(self, text: str, lang: str | None = None) -> list[Span]:
        return find_all(text)
