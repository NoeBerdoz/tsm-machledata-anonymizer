"""Generate the synthetic requests used for the O4 app evaluation."""

import argparse
import csv
import json
import random
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from pii_anonymizer.files import read_text
from pii_anonymizer.swiss import fake_value, format_iban, iban_number

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "test" / "o4_requests"
LABELS = ("PERSON", "EMAIL", "PHONE", "AVS", "IBAN")

type Contact = tuple[str, str, str, str, str]


def write_pdf(path: Path, lines: list[str]) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    # Use hex strings so punctuation and accents survive the PDF content stream.
    commands = ["BT /F1 11 Tf 16 TL 45 795 Td"]
    commands.extend(f"<{line.encode('cp1252').hex()}> Tj T*" for line in lines)
    stream = DecodedStreamObject()
    stream.set_data("\n".join([*commands, "ET"]).encode("ascii"))
    page.replace_contents(stream)
    writer.write(path)


def write_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    # Repack with fixed ZIP timestamps and no compression for stable DVC hashes.
    with ZipFile(buffer) as saved, ZipFile(path, "w") as fixed:
        for name in sorted(saved.namelist()):
            entry = ZipInfo(name)
            entry.create_system = 0
            fixed.writestr(entry, saved.read(name))


def french_request(output: Path, rows: list[Contact]) -> tuple[str, list[Path]]:
    name, _, _, _, iban = rows[0]
    prompt = (
        f"Objet : suivi du virement de {name}.\n"
        f"Compare les deux pièces jointes. Le compte {iban} est-il confirmé pour {name} ? "
        "Recopie le code du modèle de suivi dans ta réponse."
    )
    notes = output / "suivi.txt"
    notes.write_text(
        f"Virement confirmé pour {name}.\nIBAN de référence : {iban}\n"
        "Code du modèle de suivi : <PERSON_1>\n",
        encoding="utf-8",
        newline="\n",
    )
    report = output / "virements.pdf"
    lines = ["Contrôle des virements"]
    for person, email, phone, avs, account in rows:
        lines.extend(
            [
                "",
                f"Bénéficiaire : {person}",
                f"Courriel : {email}   Tél. : {phone}",
                f"AVS : {avs}   IBAN : {account}",
            ]
        )
    write_pdf(report, lines)
    return prompt, [report, notes]


def german_request(output: Path, rows: list[Contact]) -> tuple[str, list[Path]]:
    name, email, _, _, _ = rows[0]
    prompt = (
        f"Stimmt die E-Mail-Adresse {email} von {name} mit der Aktennotiz überein? "
        "Gib auch die dazugehörige Telefonnummer an."
    )
    path = output / "aktennotiz.docx"
    paragraphs = ["Aktennotiz zur Prüfung der Personaldaten"]
    for person, address, phone, avs, iban in rows:
        paragraphs.append(
            f"Mitarbeitende Person: {person}\n"
            f"E-Mail: {address}\nTelefon: {phone}\nAHV-Nummer: {avs}\nIBAN: {iban}"
        )
    write_docx(path, paragraphs)
    return prompt, [path]


def italian_request(output: Path, rows: list[Contact]) -> tuple[str, list[Path]]:
    name, _, _, avs, _ = rows[0]
    prompt = (
        f"Nel registro allegato, il numero AVS {avs} corrisponde alla scheda di {name}? "
        "Indica anche l’IBAN registrato nella stessa riga."
    )
    path = output / "registro.csv"
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, delimiter=";", lineterminator="\n")
        writer.writerow(("Nome completo", "E-mail", "Telefono", "Numero AVS", "IBAN"))
        writer.writerows(rows)
    return prompt, [path]


def english_request(output: Path, rows: list[Contact]) -> tuple[str, list[Path]]:
    name, _, phone, _, _ = rows[0]
    prompt = (
        f"Check whether {phone} is the callback number for {name} in the handover. "
        "List the beneficiary and the account for each pending payment."
    )
    path = output / "handover.txt"
    lines = ["Payroll handover — pending payments"]
    for person, email, number, avs, iban in rows:
        lines.extend(
            [
                "",
                f"Beneficiary: {person}",
                f"Callback: {number} ({email})",
                f"Swiss social security number: {avs}",
                f"Payment account: {iban}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return prompt, [path]


def planted_values(request_id: str, rows: list[Contact], sources: dict[str, str]) -> list[dict]:
    values = []
    for row in rows:
        for label, value in zip(LABELS, row, strict=True):
            occurrences = [
                {"source": source, "start": match.start(), "end": match.end()}
                for source, content in sources.items()
                for match in re.finditer(re.escape(value), content)
            ]
            if not occurrences:
                raise ValueError(f"{request_id}: could not extract planted {label} {value!r}")
            values.append(
                {
                    "id": f"{request_id}-{len(values) + 1:03d}",
                    "label": label,
                    "value": value,
                    "occurrences": occurrences,
                }
            )
    return values


def generate(output: Path) -> None:
    scenarios = (
        (
            "fr",
            french_request,
            ("Élise Burnier", "Théo Vallot", "Maëlle Dutoit", "Luc Métral", "Anaïs Besson"),
        ),
        (
            "de",
            german_request,
            ("Léa Brütsch", "Jonas Rüegg", "Livia Küng", "Nils Bühler", "Mara Zbinden"),
        ),
        (
            "it",
            italian_request,
            ("Daria Bernasconi", "Luca Riva", "Eva Delcò", "Matteo Soldini", "Irene Cattaneo"),
        ),
        (
            "en",
            english_request,
            ("Avery Brooks", "Mila Tanner", "Ellis Clarke", "Nora Reeves", "Robin Fletcher"),
        ),
    )
    output.mkdir(parents=True, exist_ok=True)
    requests = []
    for lang, write_request, names in scenarios:
        rng = random.Random(f"75:{lang}")
        rows = []
        for name in names:
            mailbox = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
            email = mailbox.lower().replace(" ", ".") + f"@dossier-{lang}.example"
            iban = format_iban(iban_number(rng, country="CH"), "grouped")
            rows.append((name, email, fake_value("PHONE", rng), fake_value("AVS", rng), iban))

        prompt, files = write_request(output, rows)
        sources = {"prompt": prompt}
        sources.update({path.name: read_text(path.name, path.read_bytes()) for path in files})
        request_id = f"o4-{lang}"
        requests.append(
            {
                "id": request_id,
                "lang": lang,
                "prompt": prompt,
                "files": [path.name for path in files],
                "values": planted_values(request_id, rows, sources),
            }
        )

    manifest = output / "requests.jsonl"
    manifest.write_text(
        "".join(json.dumps(request, ensure_ascii=False) + "\n" for request in requests),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    generate(parser.parse_args().output)
