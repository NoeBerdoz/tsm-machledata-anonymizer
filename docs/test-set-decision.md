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
- **Planted snippets** use about 40 marked templates. Template mode writes three variants per template with seeds 0, 1 and 2. It generates valid AVS, IBAN and phone values in several formats and computes the offsets.
- **Effort**: 9.5 minutes per hand-written snippet (measured, see above) for 80 realistic snippets and 40 templates, about 19 hours. Then about 4 hours for a second person to re-check 20 % (24 snippets), 2 hours for a small script that computes the offsets of the realistic snippets, and 3 hours for PDF and DOCX files. That is about 28 hours, so at least 3.5 person-days: we measured review, not writing.

## T2 mix proposal

Michael may rebalance this proposal in NoeBerdoz/tsm-machledata-anonymizer#60. Use the main language
for bilingual prompts. Some prompts mix an instruction and personal data in two languages. Use
`prompt` for code or logs with an instruction and `txt` for standalone text, code and logs. Use fake
usernames, credentials and IP addresses in code and log cases.

| Source | Real FR | DE | IT | EN | Total | Templates FR | DE | IT | EN | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| prompt | 6 | 6 | 6 | 6 | 24 | 2 | 2 | 2 | 2 | 8 |
| email | 4 | 4 | 4 | 4 | 16 | 2 | 2 | 2 | 2 | 8 |
| pdf | 2 | 2 | 2 | 2 | 8 | 2 | 2 | 2 | 2 | 8 |
| docx | 2 | 2 | 2 | 2 | 8 | 2 | 2 | 2 | 2 | 8 |
| csv | 2 | 2 | 2 | 2 | 8 | 2 | 2 | 2 | 2 | 8 |
| txt | 4 | 4 | 4 | 4 | 16 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **20** | **20** | **20** | **20** | **80** | **10** | **10** | **10** | **10** | **40** |

- Keep the text of `t2-0001` through `t2-0007`, `t2-0013` through `t2-0017`, and `t2-0019` and `t2-0020`.
  Keep the `t2-0018` scenario and replace provider-shaped tokens with visibly inert placeholders.
  Rebuild `t2-0008` through `t2-0012` from documents. Use `t2-0021` through `t2-0030` as template
  starting points, including the four file layouts. Review every row under the published policy.
- Keep realistic counts even for each source and language. Give each template its own group. Use
  distinct people, companies, addresses and identifying values in each template. When adapting pilot
  templates, replace details shared with other snippets. Audit related realistic rows separately.
- Match the slot counts within each template pair. In AVS, IBAN and PHONE order, plan 1/1/2 per
  prompt, 1/2/1 per email, 2/1/2 per PDF, 2/1/1 per DOCX and 1/1/2 per CSV. Each half gets five
  templates per language and three variants each. That gives 84 AVS, 72 IBAN and 96 PHONE spans
  per half. About eight realistic spans with these labels per half bring the total to about 260.
  Check the actual counts after review with groups intact.

Across 120 variants, `data/test/t2-planted.jsonl` contains 168 AVS, 144 IBAN and 192 PHONE spans.
Of the IBANs, 129 have country code CH and 15 have country code LI.
We will record the counts for each half after the split in #60.

| Label | Format | Spans |
| --- | --- | ---: |
| AVS | Dotted | 48 |
| AVS | Compact | 35 |
| AVS | Space-separated | 39 |
| AVS | Dashed | 46 |
| IBAN | Grouped uppercase | 54 |
| IBAN | Compact uppercase | 48 |
| IBAN | Grouped lowercase | 42 |
| PHONE | International with `+41` | 33 |
| PHONE | National with spaces | 41 |
| PHONE | Compact international | 32 |
| PHONE | International with `0041` | 28 |
| PHONE | International with `+41 (0)` | 28 |
| PHONE | National with a slash | 30 |

### Authoring and file checks

Write each original as a UTF-8 JSONL record with `id`, `marked_text`, `lang`, `source`, `kind` and `group`.
Keep pilot realistic IDs `t2-0001` through `t2-0020`. Assign new realistic rows `t2-0061`
through `t2-0120` across both realistic files. Reserve `t2-0021` through `t2-0060` for templates,
including the ten pilot templates. A variant adds the seed, as in `t2-0031-s0-ch`. The holdout
manifest uses the template base ID for all its variants.

For PDF and DOCX rows add `filename` relative to the dataset directory. Copy `⟦label|value⟧`
and use the policy label, as in `⟦full_name|Élise Exemple⟧` or `⟦PHONE|+41 79 123 45 67⟧`.
Put surrounding whitespace outside the mark. Keep any line breaks inside the value.
Use `⟦@AVS|worker⟧`, `⟦@IBAN/lower|salary⟧` or `⟦@PHONE|contact⟧` for generated values.
Each slot uses its kind as the label. Use `⟦@AVS/dashes|worker⟧` for a dashed AVS number.
Repeat the same slot name and kind to repeat a value. Use the same format setting on every occurrence.
Keep the Unicode brackets for marks. The builder preserves all other text and computes code-point offsets.

```sh
uv run python -m pii_anonymizer.t2_marking build marked.jsonl data/test/t2-realistic.jsonl
uv run python -m pii_anonymizer.t2_marking build marked-files.jsonl data/test/t2-files.jsonl
uv run python -m pii_anonymizer.swiss data/test/t2-templates.jsonl data/test/t2-planted.jsonl \
    --template-slots --assets-dir data/test/t2-planted-assets
uv run python -m pii_anonymizer.t2_files verify data/test/t2-files.jsonl
uv run python -m pii_anonymizer.t2_files verify data/test/t2-planted.jsonl
```

Use Typst to make text PDFs. Keep the `.typ` source with each PDF and record the Typst version and font.
Use an embedded font such as Libertinus Serif with
`typst compile --ignore-system-fonts --creation-timestamp 0 layout.typ form.pdf`.
For DOCX, write a JSON array of paragraphs and tables, for example
`["Formulaire", {"table": [["Nom", "Élise Exemple"]]}]`.
Run `uv run python -m pii_anonymizer.t2_files docx layout.json form.docx` to render it.
Cover salary certificates, void QR bills, leases and insurance forms.
Use `uv run python -m pii_anonymizer.t2_files extract FILE` and mark the resulting text verbatim
before building the JSONL. The verification command reads the stored files with the app extractor.

For planted file rows, name the recipe by base ID, such as `t2-0021.typ` or `t2-0023.json`.
Set the template's `filename` to the base ID with its document extension in the asset directory.
Use a distinct default probe with prefix `PROBE_` for each Typst input, for example
`sys.inputs.at("worker", default: "PROBE_WORKER")`, or a DOCX cell such as `{{worker}}`.
Render the draft, extract it and replace each probe in the extracted text with its slot mark.
Template mode passes the generated slot values to the layout and checks each variant's extraction.
The PDF file check rejects leftover Typst probes.

Track each [split input](#how-we-split-t2) separately in DVC. Keep `t2-templates.jsonl` as a separate
DVC input and track documents and recipes in `t2-file-assets/` and `t2-planted-assets/`.
Give Michael an index of the 80 realistic IDs and 40 template base IDs with their files. Include the
template groups printed by the review command and the per-group source, kind, language and label counts.

## How we split T2

- **Related snippets** share a `group` key in the JSONL file: all variants of a template, and snippets that share a person, a company, an address or a value. Apart from variants of one template, each snippet gets its own values, so most groups hold a single snippet.
- **Split**: by group, half of the snippets to dev and half to final (about 100 each). We stratify by `source` (`prompt`, `email`, `pdf`, `docx`, `csv`, `txt`), by `kind` (`realistic` or `planted`) and by language, with seed 42.
- **When**: by 30 November (v1), before any tuning, we freeze the annotation policy, the groups, the mix of types and formats, and the file hashes. The policy treats personal attributes as personal data, titles, ages, sex and gender included, so a model that masks them is not counted as over-masking. After the split, we never move a snippet between the two parts.
- **Hashes**: `t2-dev.jsonl` and `t2-final.jsonl` are tracked with DVC, so their `.dvc` files record the md5 of each version. We also write their SHA-256 in this note when we freeze them.

#57, #58 and #59 each write their own file: `t2-realistic.jsonl`, `t2-files.jsonl` and `t2-planted.jsonl`. The second reader re-checks 24 units (20 %) drawn with seed 42 from the 80 realistic snippets and the templates. A template counts as one unit, all its variants together. Then the split writes both files and prints their mix as a table for this note. It stops if an `id` appears twice, and it sorts both outputs by `id`, so their SHA-256 does not depend on the order of the input files:

```sh
uv run python -m pii_anonymizer.t2_split data/test/t2-{realistic,files,planted}.jsonl --review
uv run python -m pii_anonymizer.t2_split data/test/t2-{realistic,files,planted}.jsonl \
    --dev data/test/t2-dev.jsonl --final data/test/t2-final.jsonl
```

**Re-check, 2026-11-23.** `--review` drew these 24 units: t2-0004, t2-0005, t2-0012, t2-0014, t2-0015, t2-0018, t2-0028, t2-0029, t2-0030, t2-0032, t2-0036, t2-0055, t2-0065, t2-0070, t2-0076, t2-0078, t2-0082, t2-0087, t2-0095, t2-0103, t2-0107, t2-0112, t2-0117 and t2-0118. Two reviewers who did not write them checked each unit against this policy. 20 units passed as they were. Four needed a fix:

- t2-0005: the date of the water damage is now a `date`, like the expert's visit in the same e-mail.
- t2-0078 and t2-0087: the address of a firm alone (a signature, an employer's office) is no longer marked.
- t2-0012: the meeting venue is no longer marked as a `city`.

After splitting T2, export the Teacher exclusion manifest on the freeze side:

```sh
uv run python -m pii_anonymizer.t2_holdout data/test/t2-final.jsonl data/test/t2-final-holdout.json
```

Track the manifest as a separate DVC artifact so training can fetch it independently. It contains sorted, deduplicated source IDs with trailing `-ch` suffixes removed and SHA-256 digests of the exact UTF-8 row texts. Give the [Teacher training command](swiss-identifiers.md#the-training-rows) the manifest and keep the raw final split on the freeze side.
