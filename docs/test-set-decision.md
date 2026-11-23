# Do we need our own test set?

Issue #5, 2026-11-09. Users send a prompt and attached files (PDF, DOCX, CSV, TXT) through our app. Do the public datasets look like these texts, with Swiss identifiers in them?

**Yes, we need our own.** The public datasets do not cover these texts. We build our own test set T2 (200 snippets), and we reuse the public sets for training, T1 and out-of-distribution benchmarks.

## Swiss identifiers in the public datasets

We searched the rows for AVS numbers, Swiss IBANs and +41 phone numbers, and checked the AVS and IBAN check digits (`notebooks/scan_swiss_ids.py`).

| Dataset (rows) | AVS | Swiss IBAN | +41 phone |
|---|---|---|---|
| OpenPII-1M, validation (284,746) | 4,184, only 10 % with a valid check digit | 3, all the same specimen, unlabelled. No IBAN label at all | 2,163, a few mislabelled |
| open-pii-masking-500k, validation (116,077) | 428, 11 % valid | 0 | 742 |
| Gretel finance (55,940) | 0 | 5, unlabelled (its 1,814 IBANs are foreign) | 40 |
| Nemotron-PII (200,000) | 1 | 0 | 63 |

So no public set can measure the 99 % recall on Swiss identifiers that O1 asks for.

The scan reads only the validation splits. The 25,448 Swiss rows it finds in OpenPII-1M (`region = CH`) are validation rows, T1 is sampled from this split, and we never train on it. The train split has 102,406 Swiss rows (dataset viewer statistics, not scanned). These are the ones that are useful for training.

## What else is missing

We wrote a pilot of 30 snippets with fake data, `data/test/t2_pilot.jsonl` (DVC), in the harness format (#3), with `kind` (`realistic` or `planted`) and `group` keys. Each snippet has its own people, phone numbers, streets and birth dates, so each one is its own group. A surname inside a business name, such as "Cabinet Clerc" or "Fiduciaria Fontana SA", is personal data, because it points to the owner: we label only the surname, as `PERSON`. A large company whose name no longer refers to a living person is not labelled. The pilot holds 20 realistic inputs (prompts, e-mails, PDF and DOCX extracts, CSV exports, pasted code and logs) and 10 with planted Swiss values. Compared with the samples from #4, the public sets lack:

- **Text extracted from files**: names cut across lines, merged columns, form labels, page footers.
- **Prompts** that mix an instruction with the user's own data, often in two languages.
- **Pasted code and logs**, with user names, secrets and IPs. OpenPII-1M has none of these types.
- **Swiss documents**: salary certificates, QR bills, leases, insurance forms.

Swiss values are rare even in realistic texts: none of our 20 realistic snippets has an AVS number or an IBAN. So T2 must plant them.

## Annotation policy

Issue #60, before the writers of #57, #58 and #59 start. Every T2 snippet follows it. The pilot was labelled before it and keeps its old labels.

### Labels

Where a type is in the label list of #46 ([teacher.md](teacher.md#the-labels)), T2 uses its name. `AVS`, `IBAN` and `PHONE` stay in capitals, as in the Swiss set and in #57 to #59, because the quality gate (`gate.py`) reads them by these names.

| What | T2 label | Pilot label |
|---|---|---|
| A whole name, `Chloé Vuilleumier` | `full_name` | `PERSON` |
| A first name alone, `Chloé` | `first_name` | `PERSON` |
| A surname alone, `Dufour` in `Mme Dufour` | `last_name` | `PERSON` |
| A title, `Mme`, `Dr`, `Sig.ra`, `Dekan` | `title` | not labelled |
| An age, `64`, `64 ans` | `age` | not labelled |
| Sex, `F`, `männlich` | `sex` | not labelled |
| Gender, `femme`, `non-binaire` | `gender` | not labelled |
| A date of a person (birth, hiring, a medical visit) | `date` | `DATE_OF_BIRTH` for birth dates |
| Street and house number, `Rue du Midi 14` | `street_address` | `STREET_ADDRESS` |
| Postcode | `postal_code` | `POSTCODE` |
| City | `city` | `CITY` |
| E-mail | `email` | `EMAIL` |
| Any phone number | `PHONE` | `PHONE` |
| An AVS number | `AVS` | `AVS` |
| Any IBAN | `IBAN` | `IBAN` |
| Other IDs: ID card, passport, driving licence, tax number, customer or employee number | `government_id`, `passport_number`, `drivers_license_number`, `tax_number`, `account_id`, `employee_id` | `ID_NUMBER` |
| User name | `username` | `USERNAME` |
| Password, PIN | `password`, `pin` | `SECRET` |
| API key or token | `api_key` | `SECRET` |
| IP address | `ip_address` | `IP_ADDRESS` |

Our recall does not depend on the label: an entity counts when all its characters are masked ([evaluation.md](evaluation.md)). The labels only sort the recall per type, so a writer who hesitates between two labels of the table loses nothing.

### What to label

- **Titles, ages, sex and gender are personal data.** A model that masks them is not over-masking.
- **Incidental data too**: a colleague in a CC line, a name in a signature, a code comment or a log line, a second person mentioned in passing. If it points to a living person, label it.
- **Business names**: a surname inside a business name, such as `Cabinet Clerc` or `Fiduciaria Fontana SA`, points to the owner, so we label the surname only, as `last_name`. A large company whose name no longer refers to a living person (`Migros`, `Nestlé`) is not labelled.
- **Dates**: only a date that belongs to a person. A document date, a deadline or `dès janvier` is not labelled.

### Spans

- A span covers the value only: no surrounding spaces, quotes or punctuation.
- A title is its own span, next to the name: `Mme` is `title`, `Dufour` is `last_name`.
- Street and house number are one `street_address` span. Postcode and city are two spans.
- A value cut across lines by the file extractor is one span, line break included.
- Offsets count characters of the text as the detector receives it, so for PDF and DOCX snippets, of the app's extractor output (#58).

## Time per planted snippet

One of us reviewed each planted snippet with a timer: checked every label and looked for unlabelled PII. Times are rounded up to the whole minute.

| Snippet | Review time (min) |
|---|---|
| t2-0021 Lohnausweis (PDF, DE) | 10 |
| t2-0022 invoice with QR bill (PDF, FR) | 8 |
| t2-0023 employment contract (DOCX, FR) | 9 |
| t2-0024 AHV form help (prompt, DE) | 12 |
| t2-0025 IBAN change (e-mail, IT) | 15 |
| t2-0026 insured persons (CSV, DE) | 11 |
| t2-0027 pasted JSON (prompt, EN) | 7 |
| t2-0028 pasted SQL (prompt, FR) | 6 |
| t2-0029 claim form (PDF, IT) | 11 |
| t2-0030 letter to the AVS office (prompt, FR) | 6 |

The average is 9.5 minutes (6 to 15), about twice our first estimate of 4 to 6 minutes. These snippets already existed, so writing a new one takes longer than this.

## Decision and cost

- **Training**: OpenPII-1M + Gretel. **T1**: a fixed sample of the OpenPII-1M validation split: `data/test/t1-openpii-1m.jsonl`, 1,000 texts, 250 in each of French, German, Italian and English, drawn with seed 42 from a pinned commit of the dataset. Its SHA-256 is recorded in `results/results.csv`. **Out-of-distribution**, optional, reported if time allows: Nemotron-PII, TAB, GraSCCo, SPY, BigCode PII.
- **T2, ours**: 80 realistic and 120 planted snippets, about 260 Swiss values in each of the dev and final splits. The PDF and DOCX snippets must come from the app's own text extractor, so that the offsets match what the detector receives.
- **Planted snippets**: we write about 40 templates by hand, and `src/pii_anonymizer/swiss.py` (#28) makes 3 variants of each with seeds 0, 1 and 2. It writes valid AVS, IBAN and phone values in several formats and keeps the offsets right. So the hand work goes to the 80 realistic snippets.
- **Effort**: 9.5 minutes per hand-written snippet (measured, see above) for 80 realistic snippets and 40 templates, about 19 hours. Then about 4 hours for a second person to re-check 20 % (24 snippets), 2 hours for a small script that computes the offsets of the realistic snippets, and 3 hours for PDF and DOCX files. That is about 28 hours, so at least 3.5 person-days: we measured review, not writing.

## How we split T2

- **Related snippets** share a `group` key in the JSONL file: all variants of a template, and snippets that share a person, a company, an address or a value. Apart from variants of one template, each snippet gets its own values, so most groups hold a single snippet.
- **Split**: by group, half of the snippets to dev and half to final (about 100 each). We stratify by `source` (`prompt`, `email`, `pdf`, `docx`, `csv`, `txt`), by `kind` (`realistic` or `planted`) and by language, with seed 42.
- **When**: by 30 November (v1), before any tuning, we freeze the annotation policy, the groups, the mix of types and formats, and the file hashes. The policy treats personal attributes as personal data, titles, ages, sex and gender included, so a model that masks them is not counted as over-masking. After the split, we never move a snippet between the two parts.
- **Hashes**: `t2-dev.jsonl` and `t2-final.jsonl` are tracked with DVC, so their `.dvc` files record the md5 of each version. We also write their SHA-256 in this note when we freeze them.

The second reader re-checks 24 units (20 %) drawn with seed 42 from the 80 realistic snippets and the templates. A template counts as one unit, all its variants together. Then the split writes both files and prints their mix as a table for this note:

```sh
uv run python -m pii_anonymizer.t2_split data/test/t2.jsonl --review
uv run python -m pii_anonymizer.t2_split data/test/t2.jsonl data/test/t2-dev.jsonl data/test/t2-final.jsonl
```

After splitting T2, export the Teacher exclusion manifest on the freeze side:

```sh
uv run python -m pii_anonymizer.t2_holdout data/test/t2-final.jsonl data/test/t2-final-holdout.json
```

Track the manifest as a separate DVC artifact so training can fetch it independently. It contains sorted, deduplicated source IDs with trailing `-ch` suffixes removed and SHA-256 digests of the exact UTF-8 row texts. Give the [Teacher training command](swiss-identifiers.md#the-training-rows) the manifest and keep the raw final split on the freeze side.
