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

So no public set can measure the 99 % recall on Swiss identifiers that O1 asks for. OpenPII-1M does have 25,448 Swiss rows (`region = CH`, FR/DE/IT), which are useful for training.

## What else is missing

We wrote a pilot of 30 snippets with fake data, `data/raw/t2_pilot/t2_pilot.jsonl` (DVC), in the harness format (#3): 20 realistic inputs (prompts, e-mails, PDF and DOCX extracts, CSV exports, pasted code and logs) and 10 with planted Swiss values. Compared with the samples from #4, the public sets lack:

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
- **Effort (estimate)**: half a day to set up a tool that computes offsets and check digits (an annotation tool or a small script), then 4 to 6 minutes per snippet, plus about 3 hours for PDF and DOCX files and 3 hours for a second person to re-check 20 %. That is about 2.5 to 3.5 person-days. We replace it with the measured review times before closing the issue.
