"""Generate the O2 test prompts: 20 utility prompts and 5 stress prompts, with their files.

The format is in docs/evaluation.md ("O2 test prompts"). Every value is synthetic.
"""

import argparse
import csv
import json
import random
from decimal import Decimal
from pathlib import Path

from generate_o4_requests import write_docx, write_pdf

from pii_anonymizer.swiss import fake_value, format_iban, iban_number

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "test" / "o2_prompts"


def iban(rng: random.Random) -> str:
    return format_iban(iban_number(rng, country="CH"), "grouped")


def avs(rng: random.Random) -> str:
    return fake_value("AVS", rng, style="dots")


def phone(rng: random.Random) -> str:
    return fake_value("PHONE", rng, style="national")


def chf(amount: Decimal) -> str:
    """Swiss style, 1'284.50."""
    return f"{amount:,.2f}".replace(",", "'")


def write_csv(path: Path, rows: list[tuple], delimiter: str = ";") -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        csv.writer(target, delimiter=delimiter, lineterminator="\n").writerows(rows)


def exact(*values: str) -> dict:
    return {"type": "exact", "value": values[0] if len(values) == 1 else list(values)}


def fields(**expected: str) -> dict:
    return {"type": "json", "fields": expected}


def label(expected: str, *options: str) -> dict:
    return {"type": "label", "options": list(options), "expected": expected}


# Each writer gets the output folder and a seeded generator, writes its files and returns
# the record without id, lang and stress. `repeated` lists values that appear verbatim in
# the prompt and in a file, so they get one placeholder.


def fr_01(out, rng):
    name, account = "Chloé Vuilleumier", iban(rng)
    lines = [
        "Garage Morand SA - Route de Berne 22 - 1010 Lausanne",
        "",
        "FACTURE n° 2026-1187",
        f"Client : {name}",
        "Véhicule : VD 418 233",
        "",
        "Service des 60 000 km          CHF   640.00",
        "Pneus d'hiver (4)              CHF   560.00",
        "Main-d'oeuvre                  CHF    84.50",
        "Total                          CHF 1'284.50",
        "",
        f"Payable dans les 30 jours sur l'IBAN {account}",
    ]
    write_pdf(out / "facture_garage.pdf", lines)
    prompt = (
        f"Voici la facture du garage pour {name}. Sur quel IBAN dois-je payer ? "
        "Réponds uniquement avec l'IBAN."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=["facture_garage.pdf"],
        check=exact(account),
        repeated=[name],
    )


def fr_02(out, rng):
    rows = [
        ("Julien Rochat", "2.1", 1750, 180),
        ("Camille Baud", "2.2", 1620, 160),
        ("Noé Pittet", "3.1", 2100, 210),
        ("Léa Monnier", "3.2", 1980, 190),
        ("Hugo Bovet", "4.1", 2350, 230),
    ]
    write_csv(out / "loyers.csv", [("Locataire", "Appartement", "Loyer", "Charges"), *rows])
    name, _, rent, charges = rows[0]
    prompt = (
        f"Dans le tableau joint, combien {name} paie-t-il par mois, loyer et charges compris ? "
        "Réponds avec le montant seul, en francs."
    )
    return dict(
        task="table",
        prompt=prompt,
        files=["loyers.csv"],
        check=exact(str(rent + charges)),
        repeated=[name],
    )


def fr_03(out, rng):
    number = phone(rng)
    prompt = (
        "Résume ce courriel en JSON avec les clés expediteur, date (format JJ.MM.AAAA) "
        "et heure (format HH:MM).\n\n"
        "Bonjour à toutes et à tous,\n"
        "La séance de la commission des finances est déplacée au jeudi 10 décembre 2026 "
        "à 14:30, salle 3. En cas d'empêchement, appelez-moi au "
        f"{number}.\n"
        "Meilleures salutations,\nNathalie Perrin"
    )
    return dict(
        task="summary",
        prompt=prompt,
        files=[],
        check=fields(expediteur="Nathalie Perrin", date="10.12.2026", heure="14:30"),
        repeated=[],
    )


def fr_04(out, rng):
    name = "Sophie Rey"
    paragraphs = [
        "Procès-verbal de l'assemblée de la PPE Les Tilleuls, 18 novembre 2026",
        "Présents : 14 copropriétaires sur 16.",
        "1. Comptes 2025 : approuvés à l'unanimité.",
        f"2. Proposition de {name} de remplacer la chaudière : refusée par 9 voix contre 5.",
        "3. Proposition du comité d'installer un local à vélos : acceptée par 12 voix contre 2.",
        "La séance est levée à 21 h 10.",
    ]
    write_docx(out / "pv_assemblee.docx", paragraphs)
    prompt = (
        f"D'après le procès-verbal joint, la proposition de {name} a-t-elle été acceptée "
        "ou refusée ? Réponds par un seul mot : acceptée ou refusée."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=["pv_assemblee.docx"],
        check=label("refusée", "acceptée", "refusée"),
        repeated=[name],
    )


def fr_05(out, rng):
    number = phone(rng)
    prompt = (
        "Notre nouveau collègue Marc Jaquier commence lundi. Son adresse est "
        f"marc.jaquier@ville-exemple.ch et son numéro {number}. Écris un court message "
        "de bienvenue que je pourrai lui envoyer, et termine par son adresse e-mail "
        "pour que je la vérifie."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=[],
        check=exact("marc.jaquier@ville-exemple.ch"),
        repeated=[],
    )


def de_01(out, rng):
    name = "Lukas Meier"
    rows = [
        (name, "12.10.2026", "Bahn", "80.00"),
        (name, "04.11.2026", "Hotel", "126.50"),
        ("Nina Frei", "06.11.2026", "Bahn", "64.00"),
        (name, "13.11.2026", "Verpflegung", "48.20"),
        ("Nina Frei", "20.11.2026", "Verpflegung", "22.80"),
        (name, "25.11.2026", "Bahn", "35.90"),
    ]
    write_csv(out / "spesen.csv", [("Mitarbeiter", "Datum", "Kategorie", "Betrag"), *rows])
    november = sum(Decimal(r[3]) for r in rows if r[0] == name and r[1].endswith(".11.2026"))
    prompt = (
        f"Wie hoch sind die gesamten Spesen von {name} im November 2026 laut der Tabelle? "
        "Antworte nur mit dem Betrag in Franken."
    )
    return dict(
        task="table",
        prompt=prompt,
        files=["spesen.csv"],
        check=exact(f"{november.normalize():f}"),
        repeated=[name],
    )


def de_02(out, rng):
    name = "Anna Keller"
    paragraphs = [
        "Arbeitsvertrag",
        f"Zwischen der Brunner Logistik AG, Zürich, und {name}, AHV-Nr. {avs(rng)}.",
        "1. Stelle: Disponentin, Pensum 80 %.",
        "2. Beginn des Arbeitsverhältnisses: 01.02.2027.",
        "3. Probezeit: drei Monate.",
        "4. Lohn: CHF 5'600.00 brutto pro Monat, 13 Monatslöhne.",
    ]
    write_docx(out / "arbeitsvertrag.docx", paragraphs)
    prompt = (
        f"Ab welchem Datum beginnt der Arbeitsvertrag von {name}? "
        "Antworte nur mit dem Datum im Format TT.MM.JJJJ."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=["arbeitsvertrag.docx"],
        check=exact("01.02.2027"),
        repeated=[name],
    )


def de_03(out, rng):
    account = iban(rng)
    prompt = (
        "Fasse diese Nachricht als JSON mit den Schlüsseln absender, betrag und frist "
        "(Format TT.MM.JJJJ) zusammen.\n\n"
        "Sehr geehrte Damen und Herren\n"
        "Die Nebenkostenabrechnung 2025 ergibt eine Nachzahlung von CHF 342.60. "
        f"Bitte überweisen Sie den Betrag bis zum 31.01.2027 auf das Konto {account}.\n"
        "Freundliche Grüsse\nPetra Huber, Verwaltung Huber AG"
    )
    return dict(
        task="summary",
        prompt=prompt,
        files=[],
        check=fields(absender="Petra Huber", betrag="342.6", frist="31.01.2027"),
        repeated=[],
    )


def de_04(out, rng):
    name, number = "Sandra Graf", avs(rng)
    gross = Decimal("6850.00")
    deductions = [
        ("AHV/IV/EO", Decimal("363.05")),
        ("ALV", Decimal("75.35")),
        ("BVG", Decimal("485.40")),
    ]
    net = gross - sum(amount for _, amount in deductions)
    lines = [
        "Brunner Logistik AG - Lohnabrechnung November 2026",
        "",
        f"Mitarbeiterin: {name}",
        f"AHV-Nummer: {number}",
        f"Konto: {iban(rng)}",
        "",
        f"Bruttolohn                    CHF {chf(gross)}",
        *(f"{what:<30}CHF -{chf(amount)}" for what, amount in deductions),
        f"Nettolohn                     CHF {chf(net)}",
    ]
    write_pdf(out / "lohnabrechnung.pdf", lines)
    prompt = (
        f"Lies die Lohnabrechnung von {name}. Gib die AHV-Nummer und den Nettolohn als JSON "
        "mit den Schlüsseln ahv_nummer und nettolohn an."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=["lohnabrechnung.pdf"],
        check=fields(ahv_nummer=number, nettolohn=f"{net.normalize():f}"),
        repeated=[name],
    )


def de_05(out, rng):
    prompt = (
        "Hier ist der Schichtplan der Pflegestation für nächste Woche:\n\n"
        "| Tag | Frühschicht | Spätschicht | Nachtschicht |\n"
        "|---|---|---|---|\n"
        "| Montag | Jonas Weber | Laura Schmid | Reto Baumann |\n"
        "| Dienstag | Laura Schmid | Reto Baumann | Mia Steiner |\n"
        "| Mittwoch | Mia Steiner | Jonas Weber | Laura Schmid |\n"
        "| Donnerstag | Reto Baumann | Mia Steiner | Jonas Weber |\n\n"
        "Wer hat am Mittwoch Nachtschicht? Antworte nur mit dem Namen."
    )
    return dict(task="table", prompt=prompt, files=[], check=exact("Laura Schmid"), repeated=[])


def it_01(out, rng):
    name = "Giulia Bernasconi"
    rows = [
        (name, "settembre", 8),
        (name, "ottobre", 23),
        (name, "novembre", 11),
        ("Marco Pedrazzini", "ottobre", 6),
        ("Elisa Ghisletta", "ottobre", 15),
    ]
    write_csv(out / "straordinari.csv", [("Dipendente", "Mese", "Ore straordinarie"), *rows])
    prompt = (
        f"Quante ore di straordinario ha fatto {name} in ottobre, secondo la tabella? "
        "Rispondi solo con il numero."
    )
    return dict(
        task="table",
        prompt=prompt,
        files=["straordinari.csv"],
        check=exact("23"),
        repeated=[name],
    )


def it_02(out, rng):
    name = "Marco Ferrari"
    lines = [
        "Studio medico Centro Lugano - Via Nassa 5 - 6900 Lugano",
        "",
        "Conferma di appuntamento",
        f"Paziente: {name}",
        f"Telefono: {phone(rng)}",
        "Data: 15.01.2027, ore 09:15",
        "Visita: controllo annuale",
        "",
        "In caso di disdetta, avvisare almeno 24 ore prima.",
    ]
    write_pdf(out / "conferma_appuntamento.pdf", lines)
    prompt = f"Quando è l'appuntamento di {name}? Rispondi solo con la data nel formato GG.MM.AAAA."
    return dict(
        task="extraction",
        prompt=prompt,
        files=["conferma_appuntamento.pdf"],
        check=exact("15.01.2027"),
        repeated=[name],
    )


def it_03(out, rng):
    paragraphs = [
        "Verbale della riunione del comitato, 20 novembre 2026",
        "Presenti: Chiara Rossi, Davide Lurati, Sofia Fontana.",
        "1. Festa di fine anno: si terrà il 19 dicembre al ristorante Al Porto.",
        "2. Budget approvato: CHF 1'800.",
        "3. Responsabile dell'organizzazione: Davide Lurati.",
        "4. Le iscrizioni vanno inviate entro il 05.12.2026.",
    ]
    write_docx(out / "verbale.docx", paragraphs)
    prompt = (
        "Riassumi il verbale allegato in JSON con le chiavi responsabile, budget "
        "e scadenza_iscrizioni (formato GG.MM.AAAA)."
    )
    return dict(
        task="summary",
        prompt=prompt,
        files=["verbale.docx"],
        check=fields(responsabile="Davide Lurati", budget="1800", scadenza_iscrizioni="05.12.2026"),
        repeated=[],
    )


def it_04(out, rng):
    account = iban(rng)
    prompt = (
        f"Ciao, sono Paolo Rinaldi. Il mio nuovo conto è {account}. Scrivi una breve e-mail "
        "all'ufficio stipendi per chiedere di versare lo stipendio su questo conto da gennaio. "
        "Riporta l'IBAN nell'e-mail."
    )
    return dict(task="extraction", prompt=prompt, files=[], check=exact(account), repeated=[])


def it_05(out, rng):
    prompt = (
        "Ecco gli ordini di oggi:\n\n"
        "| Cliente | Ordine | Stato |\n"
        "|---|---|---|\n"
        "| Luca Galli | 40817 | spedito |\n"
        "| Sara Colombo | 40818 | annullato |\n"
        "| Anna Ricci | 40819 | in attesa |\n\n"
        "Qual è lo stato dell'ordine di Sara Colombo? "
        "Rispondi solo con: spedito, in attesa o annullato."
    )
    return dict(
        task="table",
        prompt=prompt,
        files=[],
        check=label("annullato", "spedito", "in attesa", "annullato"),
        repeated=[],
    )


def en_01(out, rng):
    name = "Oliver Bennett"
    rows = [
        (name, 46, 41),
        (name, 47, 38.5),
        ("Grace Holloway", 46, 40),
        ("Grace Holloway", 47, 42.5),
        ("Samuel Price", 47, 36),
    ]
    write_csv(out / "timesheet.csv", [("employee", "week", "hours"), *rows], delimiter=",")
    prompt = (
        f"According to the attached timesheet, how many hours did {name} log in week 47? "
        "Answer with the number only."
    )
    return dict(
        task="table",
        prompt=prompt,
        files=["timesheet.csv"],
        check=exact("38.5"),
        repeated=[name],
    )


def en_02(out, rng):
    lines = [
        "Incident report IR-2026-031",
        "",
        "Reported by: Rachel Moore",
        f"Phone: {phone(rng)}",
        "Date: 03.11.2026",
        "Location: Bahnhofstrasse 12, 8001 Zurich, 2nd floor kitchen",
        "",
        "A water pipe under the sink leaked overnight. The floor was dried and the",
        "plumber replaced the joint the same day. No equipment was damaged.",
    ]
    write_pdf(out / "incident_report.pdf", lines)
    prompt = (
        "Summarize the attached incident report as JSON with the keys reported_by, "
        "date (DD.MM.YYYY) and street."
    )
    return dict(
        task="summary",
        prompt=prompt,
        files=["incident_report.pdf"],
        check=fields(reported_by="Rachel Moore", date="03.11.2026", street="Bahnhofstrasse 12"),
        repeated=[],
    )


def en_03(out, rng):
    name, employee = "Hannah Clarke", "E-20431"
    write_docx(
        out / "onboarding.docx",
        [
            "Onboarding checklist",
            f"New hire: {name}",
            f"Employee number: {employee}",
            "Start date: 04.01.2027",
            "Team: Customer Support",
        ],
    )
    account = iban(rng)
    write_csv(
        out / "payroll_accounts.csv",
        [
            ("employee_number", "iban"),
            ("E-20388", iban(rng)),
            (employee, account),
            ("E-20457", iban(rng)),
        ],
        delimiter=",",
    )
    prompt = (
        f"Using both attached files, which IBAN should {name}'s salary be paid to? "
        "Answer with the IBAN only."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=["onboarding.docx", "payroll_accounts.csv"],
        check=exact(account),
        repeated=[name, employee],
    )


def en_04(out, rng):
    number = phone(rng)
    prompt = (
        "Summarize this voicemail transcript in one sentence, then give the number "
        "to call back.\n\n"
        '"Hi, this is Daniel Hughes from the building management. The lift in block B '
        "will be out of service on Friday morning for maintenance. If that is a problem "
        f'for your delivery, call me back on {number}. Thanks."'
    )
    return dict(task="summary", prompt=prompt, files=[], check=exact(number), repeated=[])


def en_05(out, rng):
    prompt = (
        "Here are our open invoices on 25.11.2026:\n\n"
        "| Customer | Invoice | Due date | Paid |\n"
        "|---|---|---|---|\n"
        "| Peter Walsh | 1042 | 30.11.2026 | no |\n"
        "| Lucy Turner | 1037 | 15.11.2026 | no |\n"
        "| Adam Hayes | 1031 | 10.11.2026 | yes |\n\n"
        "Which customer has an unpaid invoice that is already past its due date? "
        "Answer with the name only."
    )
    return dict(task="table", prompt=prompt, files=[], check=exact("Lucy Turner"), repeated=[])


# The stress prompts need to link two forms of one person, which the app does not do (#31).


def stress_fr(out, rng):
    rows = [
        ("Prénom", "Nom", "Fonction", "Salaire mensuel"),
        ("Marie", "Dupont", "Comptable", "6'250"),
        ("Pierre", "Favre", "Magasinier", "4'900"),
        ("Claire", "Dupont", "Assistante", "5'100"),
    ]
    write_csv(out / "salaires.csv", rows)
    prompt = (
        "Quel est le salaire mensuel de Marie Dupont dans le tableau joint ? "
        "Réponds avec le montant seul."
    )
    return dict(
        task="table", prompt=prompt, files=["salaires.csv"], check=exact("6250"), repeated=[]
    )


def stress_de(out, rng):
    number = phone(rng)
    write_docx(
        out / "brief_huber.docx",
        [
            "Betreff: Offerte Gartenpflege",
            "Gerne offerieren wir Ihnen die Pflege Ihres Gartens für CHF 1'450 pro Jahr.",
            f"Für Rückfragen erreichen Sie mich unter {number}.",
            "Freundliche Grüsse",
            "M. Huber",
        ],
    )
    prompt = (
        "Martin Huber hat uns den angehängten Brief geschickt. Unter welcher Telefonnummer "
        "erreiche ich Martin Huber? Antworte nur mit der Nummer."
    )
    return dict(
        task="extraction",
        prompt=prompt,
        files=["brief_huber.docx"],
        check=exact(number),
        repeated=[],
    )


def stress_it(out, rng):
    number = avs(rng)
    write_pdf(
        out / "scheda_moretti.pdf",
        [
            "Cassa di compensazione - Scheda assicurato",
            "",
            "Cognome e nome: Moretti Luca",
            f"Numero AVS: {number}",
            "Data di nascita: 14.06.1988",
        ],
    )
    prompt = "Qual è il numero AVS di Luca Moretti? Rispondi solo con il numero."
    return dict(
        task="extraction",
        prompt=prompt,
        files=["scheda_moretti.pdf"],
        check=exact(number),
        repeated=[],
    )


def stress_en_01(out, rng):
    write_csv(
        out / "staff.csv",
        [
            ("first_name", "last_name", "department"),
            ("Emma", "Walsh", "Logistics"),
            ("Liam", "Walsh", "Finance"),
            ("Emma", "Grant", "Marketing"),
        ],
        delimiter=",",
    )
    prompt = (
        "Which department does Emma Walsh work in, according to the attached list? "
        "Answer with the department only."
    )
    return dict(
        task="table", prompt=prompt, files=["staff.csv"], check=exact("Logistics"), repeated=[]
    )


def stress_en_02(out, rng):
    prompt = (
        "I got this note:\n\n"
        '"Please bring the signed forms to my office, room B-214, before Thursday. '
        'J. Porter"\n\n'
        "Which room should I go to, to hand the forms to James Porter? "
        "Answer with the room only."
    )
    return dict(task="extraction", prompt=prompt, files=[], check=exact("B-214"), repeated=[])


PROMPTS = [
    ("o2-fr-01", "fr", fr_01),
    ("o2-fr-02", "fr", fr_02),
    ("o2-fr-03", "fr", fr_03),
    ("o2-fr-04", "fr", fr_04),
    ("o2-fr-05", "fr", fr_05),
    ("o2-de-01", "de", de_01),
    ("o2-de-02", "de", de_02),
    ("o2-de-03", "de", de_03),
    ("o2-de-04", "de", de_04),
    ("o2-de-05", "de", de_05),
    ("o2-it-01", "it", it_01),
    ("o2-it-02", "it", it_02),
    ("o2-it-03", "it", it_03),
    ("o2-it-04", "it", it_04),
    ("o2-it-05", "it", it_05),
    ("o2-en-01", "en", en_01),
    ("o2-en-02", "en", en_02),
    ("o2-en-03", "en", en_03),
    ("o2-en-04", "en", en_04),
    ("o2-en-05", "en", en_05),
]
STRESS = [
    ("o2-stress-fr-01", "fr", stress_fr),
    ("o2-stress-de-01", "de", stress_de),
    ("o2-stress-it-01", "it", stress_it),
    ("o2-stress-en-01", "en", stress_en_01),
    ("o2-stress-en-02", "en", stress_en_02),
]


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for stress, prompts in ((False, PROMPTS), (True, STRESS)):
        for prompt_id, lang, write in prompts:
            record = write(output, random.Random(f"o2:{prompt_id}"))
            records.append({"id": prompt_id, "lang": lang, "stress": stress, **record})
    (output / "prompts.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    generate(parser.parse_args().output)
