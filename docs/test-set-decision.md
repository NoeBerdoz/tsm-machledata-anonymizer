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

The scan reads only the validation splits. The 25,448 Swiss rows it finds in OpenPII-1M (`region = CH`) are validation rows, so with option A they are T1, and we never train on them. The train split has 102,406 Swiss rows (dataset viewer statistics, not scanned). These are the ones that are useful for training.

## What else is missing

We wrote a pilot of 30 snippets with fake data, `data/test/t2_pilot.jsonl` (DVC), in the harness format (#3), with `kind` (`realistic` or `planted`) and `group` keys. Each snippet has its own people, phone numbers, streets and birth dates, so each one is its own group. A surname inside a business name, such as "Cabinet Clerc" or "Fiduciaria Fontana SA", is personal data, because it points to the owner: we label only the surname, as `PERSON`. A large company whose name no longer refers to a living person is not labelled. The pilot holds 20 realistic inputs (prompts, e-mails, PDF and DOCX extracts, CSV exports, pasted code and logs) and 10 with planted Swiss values. Compared with the samples from #4, the public sets lack:

- **Text extracted from files**: names cut across lines, merged columns, form labels, page footers.
- **Prompts** that mix an instruction with the user's own data, often in two languages.
- **Pasted code and logs**, with user names, secrets and IPs. OpenPII-1M has none of these types.
- **Swiss documents**: salary certificates, QR bills, leases, insurance forms.

Swiss values are rare even in realistic texts: none of our 20 realistic snippets has an AVS number or an IBAN. So T2 must plant them.

## Time per planted snippet

The pilot was written with Claude Code, so we have no human time yet. **Before closing #5**, one of us reviews the 10 planted snippets with a timer.

| Snippet | Review time (min) | Snippet | Review time (min) |
|---|---|---|---|
| t2-0021 Lohnausweis (PDF, DE) | | t2-0026 insured persons (CSV, DE) | |
| t2-0022 invoice with QR bill (PDF, FR) | | t2-0027 pasted JSON (prompt, EN) | |
| t2-0023 employment contract (DOCX, FR) | | t2-0028 pasted SQL (prompt, FR) | |
| t2-0024 AHV form help (prompt, DE) | | t2-0029 claim form (PDF, IT) | |
| t2-0025 IBAN change (e-mail, IT) | | t2-0030 letter to the AVS office (prompt, FR) | |

## Decision and cost

- **Training**: OpenPII-1M + Gretel. **T1**: OpenPII-1M validation. **Out-of-distribution**: Nemotron-PII, TAB, GraSCCo, SPY, BigCode PII.
- **T2, ours**: 80 realistic and 120 planted snippets, about 260 Swiss values in each of the dev and final splits. The PDF and DOCX snippets must come from the app's own text extractor, so that the offsets match what the detector receives.
- **Planted snippets**: we write about 40 templates by hand, and `src/pii_anonymizer/swiss.py` (#28) makes 3 variants of each with seeds 0, 1 and 2. It writes valid AVS, IBAN and phone values in several formats and keeps the offsets right. So the hand work goes to the 80 realistic snippets.
- **Effort (estimate)**: 4 to 6 minutes per hand-written snippet (80 realistic and 40 templates), about 2 hours for a small script that computes the offsets of the realistic snippets, 3 hours for PDF and DOCX files, and 2 hours for a second person to re-check 20 %. That is about 2 to 2.5 person-days. We replace it with the measured review times before closing the issue.

## How we split T2

- **Related snippets** share a `group` key in the JSONL file: all variants of a template, and snippets that share a person, a company, an address or a value. Apart from variants of one template, each snippet gets its own values, so most groups hold a single snippet.
- **Split**: by group, half of the snippets to dev and half to final (about 100 each). We stratify by input kind (prompt, e-mail, file extract, CSV, code or log) and by language, with seed 42.
- **When**: before any tuning. After the split, we never move a snippet between the two parts.
- **Hashes**: `t2-dev.jsonl` and `t2-final.jsonl` are tracked with DVC, so their `.dvc` files record the md5 of each version. We also write their SHA-256 in this note when we freeze them.
