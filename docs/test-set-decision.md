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
| prompt | 6 | 6 | 6 | 6 | 24 | 3 | 3 | 3 | 3 | 12 |
| email | 4 | 4 | 4 | 4 | 16 | 2 | 2 | 2 | 2 | 8 |
| pdf | 2 | 2 | 2 | 2 | 8 | 1 | 1 | 1 | 1 | 4 |
| docx | 2 | 2 | 2 | 2 | 8 | 1 | 1 | 1 | 1 | 4 |
| csv | 2 | 2 | 2 | 2 | 8 | 2 | 2 | 2 | 2 | 8 |
| txt | 4 | 4 | 4 | 4 | 16 | 1 | 1 | 1 | 1 | 4 |
| **Total** | **20** | **20** | **20** | **20** | **80** | **10** | **10** | **10** | **10** | **40** |

- Keep the text of `t2-0001` through `t2-0007`, `t2-0013` through `t2-0017`, and `t2-0019` and `t2-0020`.
  Keep the `t2-0018` scenario and replace provider-shaped tokens with visibly inert placeholders.
  Rebuild `t2-0008` through `t2-0012` from documents. Use `t2-0021` through `t2-0030` as template
  starting points, including the four file layouts. Review every row under the published policy.
- Audit pilot groups across sources. Check Muster AG and Régie du Lac in `t2-0008`, `t2-0009`,
  `t2-0015` and `t2-0021`, and Fintech SA in `t2-0011` and `t2-0023`.
- Plan 14 AVS, 12 IBAN and 16 PHONE slot occurrences per language. This gives 168 AVS, 144 IBAN
  and 192 PHONE spans after expansion. Aim for about 252 planted Swiss spans per half, including
  84 AVS, 72 IBAN and 96 PHONE. Around 16 natural Swiss spans across the realistic rows bring each
  half to about 260. Count occurrences after review and check the mix with groups intact.

### Authoring and file checks

Write each original as a UTF-8 JSONL record with `id`, `marked_text`, `lang`, `source`, `kind` and `group`.
For PDF and DOCX rows add `filename` relative to the dataset directory. Copy `⟦label|value⟧` to
mark a literal span. Add `@KIND` to the label for every Swiss value in realistic text, for example
`⟦phone_number@PHONE|+41 79 123 45 67⟧`. Keep the policy label on every span.
Use `⟦@AVS:national_id_number|worker⟧` for a slot. Add a format with
`⟦@AVS/dashes:national_id_number|worker⟧` or `⟦@IBAN/lower:iban|salary⟧`.
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
Use a distinct default probe for each Typst input, for example
`sys.inputs.at("worker", default: "PROBE_WORKER")`, or a DOCX cell such as `{{worker}}`.
Render the draft, extract it and replace each probe in the extracted text with its slot mark.
Template mode passes the generated slot values to the layout and checks each variant's extraction.

## How we split T2

- **Inputs** are `t2-realistic.jsonl`, `t2-files.jsonl` and `t2-planted.jsonl` under `data/test/`,
  with separate DVC pointers. Keep `t2-templates.jsonl` as a separate DVC input. Track the documents
  and recipes in `t2-file-assets/` and `t2-planted-assets/`. Noé pushes the data to DVC.
- **Review** uses an index of 80 realistic IDs and 40 template base IDs with their source files.
  Give Michael the index and per-group source, kind, language and Swiss counts. Draw 24 distinct originals.
- **Swiss counts** use the entity's `swiss` kind. Preserve it and the policy label through the split.

- **Related snippets** share a `group` key in the JSONL file: all variants of a template, and snippets that share a person, a company, an address or a value. Apart from variants of one template, each snippet gets its own values, so most groups hold a single snippet.
- **Split**: by group, half of the snippets to dev and half to final (about 100 each). We stratify by `source` (`prompt`, `email`, `pdf`, `docx`, `csv`, `txt`), by `kind` (`realistic` or `planted`) and by language, with seed 42.
- **When**: by 30 November (v1), before any tuning, we freeze the annotation policy, the groups, the mix of types and formats, and the file hashes. The policy treats personal attributes as personal data, titles, ages, sex and gender included, so a model that masks them is not counted as over-masking. After the split, we never move a snippet between the two parts.
- **Hashes**: `t2-dev.jsonl` and `t2-final.jsonl` are tracked with DVC, so their `.dvc` files record the md5 of each version. We also write their SHA-256 in this note when we freeze them.

After splitting T2, export the Teacher exclusion manifest on the freeze side:

```sh
uv run python -m pii_anonymizer.t2_holdout data/test/t2-final.jsonl data/test/t2-final-holdout.json
```

Track the manifest as a separate DVC artifact so training can fetch it independently. It contains sorted, deduplicated source IDs and SHA-256 digests of the exact UTF-8 row texts. Source IDs drop legacy `-ch` suffixes and map T2 variants to their template base ID. Give the [Teacher training command](swiss-identifiers.md#the-training-rows) the manifest and keep the raw final split on the freeze side.
