# Swiss identifiers

How we measure the Swiss part of goal O1 before T2 exists, and how we get Swiss rows for training. The script `src/pii_anonymizer/swiss.py` (and its training wrapper `swiss_training.py`) takes public rows and replaces some of their values with valid fake Swiss values of the same kind. The labels stay right by construction.

## Why

Goal O1 in [smart-goals.md](smart-goals.md) asks that Swiss structured identifiers, caught by the regular expressions and the model together, reach 99 % recall. Public data cannot measure that:

- Neither T1 sample has an IBAN gold entity. OpenPII-1M has no IBAN type at all.
- Of the 47 AVS-shaped `SOCIALNUM` values in our OpenPII-1M sample, only 4 have a valid check digit.
- Most phone numbers are random, in formats that are not Swiss.
- Gretel's test split has `iban` and `bban` entities, but none of them is Swiss.

The scan of the full public datasets in `notebooks/scan_swiss_ids.py` finds the same: no labelled Swiss IBAN, and about 90 % of OpenPII-1M's AVS numbers with an invalid check digit. See docs/test-set-decision.md (PR #24).

The v1 teacher is fine-tuned on Swiss identifiers, so training needs such rows too.

Public rows give us many valid Swiss values. T2 also covers text extracted from files, prompts that
mix instructions with personal data, and pasted code or logs. The [T2 template mode](test-set-decision.md#authoring-and-file-checks)
reuses these generators for explicit slots. It writes all three seeds in one output, keeps the policy
label with a separate `swiss` kind, and keeps the whole template group together.

## What

The script looks for entities whose gold label has the right kind, and gives each one a new Swiss value:

| Gold label | New value | New label |
|---|---|---|
| `SOCIALNUM` (OpenPII-1M) | AVS number | `AVS` |
| `TELEPHONENUM` (OpenPII-1M), `phone_number` (Gretel) | Swiss phone number | `PHONE` |
| `iban`, `bban` (Gretel) | CH IBAN, or LI in 10 % of cases | `IBAN` |

We replace a value only by one of the same kind. A sentence about a social security number keeps an AVS number, so the text stays natural. The other entities keep their labels, and their offsets move with the new text.

**The values.**

- AVS: 756, then nine random digits, then the EAN-13 check digit.
- IBAN: the country code, the two mod-97 check digits, a 5-digit bank number and a 12-digit account number.
- Phone: a mobile number (075 to 079), or a landline with a real area code (021, 022, 024, 026, 027, 031, 032, 041, 043, 044, 052, 055, 056, 058, 061, 062, 071, 081, 091).

Every AVS number and IBAN passes the validators of `rules.py`, and the tests check it.

**The written formats.** Each value is written in one of the formats people use, chosen at random with fixed weights.

| Type | Formats (weight) |
|---|---|
| AVS | `756.1234.5678.97` (6), `7561234567897` (2), `756 1234 5678 97` (1), `756-1234-5678-97` (1) |
| IBAN | `CH93 0076 2011 6238 5295 7` (6), `CH9300762011623852957` (3), `ch93 0076 2011 6238 5295 7` (1) |
| Phone | `+41 79 123 45 67` (3), `079 123 45 67` (3), `+41791234567` (1), `0041 79 123 45 67` (1), `+41 (0)79 123 45 67` (1), `079/123 45 67` (1) |

The AVS number with dashes, the lowercase IBAN and the phone number with a slash come from the review of PR #19: people write them, and the app's rules missed them.

**Small rules.**

- Spaces around a gold value stay in the text, outside the new entity.
- When Gretel puts the word `IBAN:` inside the span, the word stays in the text and only the number is replaced.
- When a document repeats the same value, it gets the same new value each time.
- An entity that overlaps another entity is left as it is, because its text cannot be replaced cleanly. This happens twice, in one Gretel document.
- After the replacement, the script checks that the text at the offsets of every entity is the value it should be.

## How to run

```sh
uv run python -m pii_anonymizer.public_data data/test/
uv run python -m pii_anonymizer.swiss data/test/t1-openpii-1m.jsonl data/test/gretel-test-iban.jsonl data/test/t1-swiss.jsonl --seed 0
```

The first command writes the two T1 samples and `gretel-test-iban.jsonl`: up to 100 documents per language (FR, DE, IT, EN) of the Gretel **test** split that hold an `iban` or `bban` entity, drawn with a fixed seed (42). It needs the `baselines` dependency group. The second command uses the standard library only. It writes only the rows that received at least one Swiss value, and adds `-ch` to their id.

Each row gets its own random generator, seeded from `--seed` and the row id. So a fixed seed gives the same file on every machine, and a row's values do not depend on the other rows.

## Rules

- Test rows come only from validation or test splits: the OpenPII-1M validation split and the Gretel test split.
- Training rows come only from train splits.
- The same source row never goes into both. A test row and a training row with fake values from the same source row would leak the text of the test set into training.

## The training rows

`src/pii_anonymizer/swiss_training.py` wraps the same injection for the v1 Teacher training subset (NoeBerdoz/tsm-machledata-anonymizer#46). Use the manifest exported during the [T2 freeze](test-set-decision.md#how-we-split-t2):

```sh
uv run python -m pii_anonymizer.swiss_training <train.jsonl> <out.jsonl> \
    --exclude data/test/t1-openpii-1m.jsonl --exclude data/test/t1-open-pii-500k.jsonl \
    --exclude data/test/gretel-test-iban.jsonl --exclude data/test/t1-swiss.jsonl \
    --exclude data/test/t2-dev.jsonl --exclude-manifest data/test/t2-final-holdout.json
```

It differs from the test set in three ways:

- **Every row is kept.** Rows without an entity of a Swiss kind are written as they are.
- **Only a share of the rows of a Swiss kind gets Swiss values: 20 %**, drawn row by row with the seed. The other 80 % keep their foreign AVS-like numbers, phone numbers and IBANs. The app must mask foreign values too, so the model must keep seeing them. About 46 % of the OpenPII-1M rows have a `SOCIALNUM` or a `TELEPHONENUM` (459 of the 1,000 rows of T1), so 20 % of them gives about 4,500 Swiss rows in a subset of 50,000. That is several thousand AVS numbers and phone numbers in every written format, which is enough for the model to learn the formats, while Swiss values stay a minority of their types. The share is the `--share` option, if #46 shows that the teacher needs more.
- **Other seeds.** Training defaults to seed 3. Seeds 0, 1 and 2 are reserved for Swiss test data. Each training row's generator also uses a `train:` prefix.

Keep the raw final T2 JSONL on the freeze side. Pass its manifest to training and use raw `--exclude` files for the T1 samples, the Gretel test sample, the Swiss test set and T2-dev. Before writing, the CLI checks both source rows and rows after injection for matching source IDs or matching SHA-256 digests of the exact UTF-8 text. Source IDs drop legacy `-ch` suffixes and map T2 variants to their template base ID. Training rows come from train splits only.

The new labels are `AVS`, `PHONE` and `IBAN`, as in the test set, while the untouched rows keep `SOCIALNUM`, `TELEPHONENUM`, `phone_number`, `iban` and `bban`. The label list of #46 maps both to the same GLiNER2 labels.

## The Swiss test set

`t1-swiss.jsonl` holds 634 rows: 459 from the OpenPII-1M T1 sample (the rows with `SOCIALNUM` or `TELEPHONENUM`) and 175 from the Gretel sample.

| Language | Rows | AVS | PHONE | IBAN |
|---|---|---|---|---|
| FR | 131 | 42 | 106 | 17 |
| DE | 146 | 40 | 95 | 39 |
| IT | 146 | 44 | 98 | 31 |
| EN | 211 | 42 | 100 | 127 |
| **Total** | **634** | **168** | **399** | **214** |

The Gretel sample has 176 documents: 16 FR, 34 DE, 26 IT and 100 EN. One English document has only overlapping bank spans, so it received no Swiss value. The other entities of every row stay in the file with their own labels, so the overall recall is also measured, but the three Swiss types are what this set is for.

## Results

We ran the detectors with `uv run python -m pii_anonymizer.evaluate <detector> data/test/t1-swiss.jsonl results/`, on the same development machine as [baselines.md](baselines.md). `regex+gliner2` and `regex+privacy-filter` mask every span that either of the two finds, because O1 measures the regex and the model together.

Recall on the three Swiss types:

| Detector | AVS (168) | IBAN (214) | PHONE (399) | All three (781) |
|---|---|---|---|---|
| regex | 92.9 % | 88.8 % | 100 % | 95.4 % |
| presidio | 7.7 % | 99.1 % | 100 % | 79.9 % |
| gliner2 | 75.6 % | 79.9 % | 91.2 % | 84.8 % |
| regex+gliner2 | 97.6 % | 99.1 % | 100 % | **99.2 %** |
| privacy-filter | 99.4 % | 79.4 % | 96.7 % | 92.6 % |
| regex+privacy-filter | 100 % | 98.1 % | 100 % | **99.5 %** |

Over all entities of the file (the Swiss ones and the others), the strict recall is 19.7 % for the regex, 57.7 % for Presidio, 78.3 % for GLiNER2, 80.3 % for `regex+gliner2`, 76.7 % for Privacy Filter and 78.1 % for `regex+privacy-filter`. The full rows are in `results/results.csv` and `results/recall_per_type.csv`.

What each detector misses:

- **regex**: every AVS number with dashes (12 of 12) and every lowercase IBAN (21 of 21). It also misses 3 IBANs glued to other text in Gretel's fixed-width records, such as `MartineCH57 2623 ...`, because the rule wanted a word boundary. Issue #45 added these three cases to `rules.py`, after this measurement: the `regex` and `regex+gliner2` rows still have to be measured again.
- **presidio**: almost every AVS number (it has no Swiss recognizer). It finds the 12 of 28 compact ones only, as other numbers. Its IBAN recognizer finds the lowercase IBANs too, and misses the same 2 glued ones as the regex. It finds every phone number.
- **gliner2**: about a quarter of the AVS numbers in every format, and a fifth of the IBANs, mostly inside SWIFT messages (`:25:CH29 2205 ...`) and XML (`<identifier>CH52...</identifier>`). It misses every phone number written `+41 (0)55 923 54 99` (0 of 35), and finds all the other phone formats.
- **regex+gliner2**: 6 values left, 4 AVS numbers with dashes and 2 glued IBANs. The two detectors cover each other's gaps: the regex finds what GLiNER2 misses in every other format, and GLiNER2 finds 8 of the 12 dashed AVS numbers and all lowercase IBANs.
- **privacy-filter**: one AVS number, a compact one of which it masks only the middle digits. It misses a fifth of the IBANs (44 of 214), all in Gretel's documents, mostly inside SWIFT messages (19) and XML (13), and a few glued to other text. It finds 33 of the 35 phone numbers written `+41 (0)55 923 54 99`, which GLiNER2 misses, and misses 13 phone numbers in all, in no single format.
- **regex+privacy-filter**: 4 values left, all IBANs: 2 lowercase ones and the 2 glued ones that the regex also misses. Every AVS number and every phone number is masked.

With 99.2 %, the combined detector just reaches the 99 % of O1 on this set. `regex+privacy-filter` reaches 99.5 %. Adding dashes to the AVS rule should close most of the gap. Issue #45 did it, and the new numbers are still to be measured.

On the two T1 samples, `regex+gliner2` gives almost the same strict recall as GLiNER2 alone (80.7 % against 80.6 % on OpenPII-1M, 81.8 % for both on 500k), because those samples have almost no valid Swiss values for the regex to add. `regex+privacy-filter` adds 0.2 points to Privacy Filter (79.0 % against 78.8 % on OpenPII-1M, 70.0 % against 69.8 % on 500k).

Privacy Filter's recall on this set by language, over all entities: 84.0 % in French, 75.7 % in German, 78.1 % in Italian and 71.5 % in English. The English rows include most of the Gretel documents, where it misses the IBANs in SWIFT and XML and many company names.

## Two sets of rules, until issue #66

Since issue #45, `rules.py` accepts AVS numbers with dashes, lowercase IBANs and IBANs glued to the word before them, so it finds every format the engine's rules find. Two sets remain, on purpose, until the engine runs our own model (issue #66):

- `rules.py` is the `regex` baseline and the regex half of `regex+gliner2`. It only looks for Swiss identifiers and e-mail addresses, and checks every AVS number and IBAN, so that O1 measures the Swiss types.
- The rules in `engine.py` are wider, because `qwen3:4b` only looks for names, addresses, birth dates and health data. They also mask foreign IBANs, foreign phone numbers and AVS-shaped numbers with a wrong check digit, which the app must not send either.

When issue #66 puts our model behind `detect()`, the model finds the foreign values, and the engine uses `rules.py` instead of its own copy.

## Limits

- The text around the values is still synthetic. It comes from generated datasets, not from real documents or prompts.
- The regex looks almost perfect on these values, because the values and the regex both come from our own idea of the formats. Its misses were the two formats from the review of PR #19 and 3 IBANs glued to other text, which issue #45 added. So the numbers that matter are the models' and the combined `regex+gliner2`.
- The values are random fake numbers. Any match with a real AVS number or a real account is by chance and is never tied to a real person.
- OpenPII-1M already holds some Swiss-looking values. We saw a Swiss company number `CHE-274.594.068` labelled `TAXNUM`, and Swiss places such as Jaun with the postcode 4524. The script leaves them as they are. The scan of the public datasets for Swiss identifiers is in docs/test-set-decision.md (PR #24).
