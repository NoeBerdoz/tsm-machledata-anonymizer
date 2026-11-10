# Baselines

What off-the-shelf detectors already reach, before we train anything (issue #6). We ran four detectors through the evaluation script of [evaluation.md](evaluation.md) on samples of the two candidate T1 validation splits named in [datasets.md](datasets.md).

These are **T1 candidate numbers only**. T2-dev does not exist yet (issue #5), so the T2-dev rows, the latency and the two v0 thresholds of [smart-goals.md](smart-goals.md) come later. All rows below were measured on a development machine (Apple M5 Max), **not on the reference laptop**. Quality does not depend on the machine, but the wall times below only say how long a run takes here.

## The detectors

- **regex** (`src/pii_anonymizer/rules.py`): our rules for Swiss identifiers, pure Python. AVS numbers (756 and 10 digits, EAN-13 check digit), CH and LI IBANs (mod-97 checksum), Swiss phone numbers (+41, 0041 or 0, then nine digits in the usual groups) and e-mail addresses. Labels `AVS`, `IBAN`, `PHONE`, `EMAIL`.
- **presidio**: Presidio's `AnalyzerEngine` 2.2.366 with the spaCy large models for English, French, German and Italian, the default recognizers and the default score threshold. The default configuration already gives the language-independent pattern recognizers (e-mail, IBAN, phone, IP, URL, date) to every language. We add the credit card recognizer to French and German, because the default lists it only for English and Italian. Presidio receives the true language of each text, which slightly favours it (see [evaluation.md](evaluation.md)).
- **gliner2**: `fastino/gliner2-privacy-filter-PII-multi` as published, on the CPU, with the 42 labels of its model card and the card's threshold of 0.5. Texts go through `extract_entities_long`, the library's way to handle long texts. Our texts are short (at most 177 words), so each text fits in one chunk. On a long Gretel document, the library gave the last word an end one character past the text. We clip such a span to the text.
- **regex+gliner2**: the two detectors together. It masks every span that either of them finds, because goal O1 measures the Swiss identifiers caught by the regex and the model together. Its size is the size of GLiNER2, since the regex has no files.
- **privacy-filter**: `openai/privacy-filter` as published, on the CPU, in its published bfloat16 weights. We run it through the token-classification pipeline of transformers 5.22.2 with `aggregation_strategy="simple"`, the documented way to get spans with character offsets. This takes the most likely tag of each token. It does not run the constrained Viterbi decoder of OpenAI's own repo, so the operating points of the model card are not used. The pipeline only knows B- and I- tags, and the model writes B-, I-, E- and S- tags, so the last token of an entity comes back as a separate span. We join spans of the same type that touch, and we strip the space that the tokens carry before a word. We checked the offsets by hand on accented and multilingual texts: they point at the right characters.
- **regex+privacy-filter**: the regex and Privacy Filter together, built like `regex+gliner2`.
- **engine**: the detector of our app today (issue #29), `engine.detect()`. It has its own regex rules (AVS, IBAN, e-mail, phone) and asks qwen3:4b, through Ollama, for names, addresses, birth dates and health data. The model stands in for our student until the pipeline delivers one. It runs as in the app, so Ollama chooses the device (the GPU on a Mac). **engine-cpu** is the same detector on the CPU with the protocol's 4 threads, for the latency (see below).

The code of the detectors is in `src/pii_anonymizer/baselines.py`. They need the `baselines` dependency group ([development.md](development.md)).

## The samples

`uv run python -m pii_anonymizer.public_data data/test/` writes two T1 files (and the Gretel sample of [swiss-identifiers.md](swiss-identifiers.md)). Each T1 file holds 250 rows per language (FR, DE, IT, EN) of a validation split, drawn with a fixed seed (42). The labels stay as the datasets write them. The script reads a pinned commit of each dataset (`PARQUET_REVISIONS` in `public_data.py`), so it rebuilds the same files byte for byte. The models are pinned the same way (`GLINER2_REVISION` and `PRIVACY_FILTER_REVISION` in `baselines.py`), and the `runtime` column of `results/results.csv` names the model commit that was scored.

| File | Source | Texts | Entities | Words per text (median, max) |
|---|---|---|---|---|
| `t1-openpii-1m.jsonl` | `ai4privacy/pii-masking-openpii-1m`, validation | 1,000 | 7,275 | 40, 177 |
| `t1-open-pii-500k.jsonl` | `ai4privacy/open-pii-masking-500k-ai4privacy`, validation | 1,000 | 2,324 | 17, 63 |

We checked every offset: for all 9,599 entities, `text[start:end]` equals the `value` of the dataset. So no entity was dropped. Neither sample has an IBAN label, and an AVS number is labelled `SOCIALNUM`.

## Results

| Detector | Sample | Strict recall | Char. precision | Size (MB) |
|---|---|---|---|---|
| regex | OpenPII-1M | 8.0 % | 99.4 % | (rules) |
| presidio | OpenPII-1M | 54.3 % | 85.7 % | 2,357 |
| gliner2 | OpenPII-1M | 80.7 % | 98.2 % | 1,244 |
| regex | 500k | 6.3 % | 99.96 % | (rules) |
| presidio | 500k | 63.5 % | 89.0 % | 2,357 |
| gliner2 | 500k | 81.8 % | 96.7 % | 1,244 |
| regex+gliner2 | OpenPII-1M | 80.7 % | 98.2 % | 1,244 |
| regex+gliner2 | 500k | 81.8 % | 96.7 % | 1,244 |
| privacy-filter | OpenPII-1M | 78.8 % | 97.3 % | 2,827 |
| privacy-filter | 500k | 69.8 % | 96.6 % | 2,827 |
| regex+privacy-filter | OpenPII-1M | 79.0 % | 97.3 % | 2,827 |
| regex+privacy-filter | 500k | 70.0 % | 96.6 % | 2,827 |

`regex+gliner2` gives the same numbers as GLiNER2 alone, rounded: the samples have almost no valid Swiss values for the regex to add. It protects 5 more entities on OpenPII-1M, among them 2 `SOCIALNUM` and 2 `EMAIL`, and 1 more `TELEPHONENUM` on 500k. The regex adds a little more to Privacy Filter: 13 entities on OpenPII-1M and 5 on 500k, mostly e-mails.

The size of Presidio is the four spaCy models. The size of GLiNER2 is its weights in fp32, its configs and its tokenizer. The size of Privacy Filter is its weights in bfloat16, its config and its tokenizer. The repo also holds ONNX exports and a second copy of the weights, which we do not count because we do not use them. The full rows are in `results/results.csv` and `results/recall_per_type.csv`.

Recall per type for the main types (OpenPII-1M first, then 500k):

| Type | Gold (1M / 500k) | regex | presidio | gliner2 | privacy-filter |
|---|---|---|---|---|---|
| GIVENNAME | 858 / 771 | 0 / 0 % | 79 / 79 % | 95 / 90 % | 85 / 73 % |
| SURNAME | 764 / 307 | 0 / 0 % | 78 / 78 % | 95 / 93 % | 87 / 78 % |
| DATE | 871 / 106 | 0 / 0 % | 46 / 58 % | 86 / 92 % | 96 / 92 % |
| EMAIL | 511 / 123 | 100 / 100 % | 100 / 100 % | 99 / 100 % | 98 / 97 % |
| CITY | 506 / 158 | 0 / 0 % | 83 / 87 % | 88 / 80 % | 68 / 49 % |
| TELEPHONENUM | 376 / 147 | 13 / 14 % | 45 / 48 % | 99 / 99 % | 97 / 95 % |
| STREET | 339 / 103 | 0 / 0 % | 59 / 55 % | 96 / 93 % | 80 / 72 % |
| BUILDINGNUM | 330 / 93 | 0 / 0 % | 12 / 16 % | 94 / 89 % | 75 / 68 % |
| ZIPCODE | 294 / 43 | 0 / 0 % | 19 / 19 % | 94 / 79 % | 84 / 65 % |
| IDCARDNUM | 241 / 89 | 0 / 0 % | 29 / 36 % | 92 / 81 % | 97 / 89 % |
| CREDITCARDNUMBER | 232 / 16 | 0 / 0 % | 24 / 12 % | 90 / 94 % | 94 / 100 % |
| SOCIALNUM | 168 / 17 | 5 / 12 % | 44 / 47 % | 67 / 88 % | 96 / 76 % |
| TITLE | 461 / 85 | 0 / 0 % | 51 / 47 % | 15 / 26 % | 70 / 51 % |
| AGE | 379 / 50 | 0 / 0 % | 15 / 14 % | 5 / 14 % | 4 / 2 % |
| TIME | 0 / 98 | (none) / 0 % | (none) / 17 % | (none) / 0 % | (none) / 5 % |

Wall time for one run of 1,000 texts on this machine, loading included: regex about 1 s, Presidio 16 s (OpenPII-1M) and 12 s (500k), GLiNER2 134 s and 105 s, Privacy Filter 184 s and 92 s (`regex+privacy-filter` 182 s and 92 s).

## The main misses

### regex

The regex only looks for four Swiss types, so its low recall is expected. It finds almost every e-mail. Its precision is close to 100 %.

- **E-mail**: it missed one address out of 634, `kde montena@hotmail.com`, which has a space inside and is not a valid address. Accented letters before the @ (`noémiaeghm@protonmail.com`) are allowed.
- **AVS numbers** (`SOCIALNUM`): the samples hold 47 numbers shaped like an AVS number (756 and 10 digits), but only 4 have a correct check digit. The others, such as `756.4960.4829.25`, are random digits. Our rule checks the digit, so it skips them. Real AVS numbers always have a correct digit, so the rule is right and the data is wrong.
- **Phones**: most phone numbers in the samples are not Swiss, or use odd groups (`+49.09.019-8629`, `(623)-4953269`, `05.9780 9444`). The rule only knows Swiss groups, so it finds 13 % of them.

### presidio

Presidio reaches 54 % and 64 %. Its pattern recognizers find every e-mail. Its spaCy models find most names and cities. It misses most of the rest.

- **Numbers without context**: building numbers (`820`, `2A`), postcodes (`34520`, `6024`) and ages (`27`) are almost never found. Presidio has no recognizer for them.
- **Credit cards** (24 % and 12 %): the recognizer checks the Luhn digit, and most card numbers in the samples are random, such as `3553304180453896`.
- **Phones** (45 %): it misses the odd formats, such as `+65-30.724-4208` or `0140-32.755.0117`.
- **Identity numbers, passports, tax numbers** (29 to 54 %): only the US and Italian recognizers exist for these. Swiss `CHE-674 087 803` tax numbers and AVS numbers such as `756.8530.6229.65` are missed.
- **Dates** (46 %): written dates such as `März 6., 1997`, `20º giugno 1943` or `Mai/54` are missed, mostly in German and Italian.
- **Titles and gender**: `Professeure`, `Mademoiselle`, `Weiblich` are missed half the time or more.
- **False positives**: words tagged as organisations or places, such as `Medicaid`, `Indirizzo` or `Cognome`. This is why its precision (86 %, 89 %) is the lowest.

Presidio's recall is lower in French and German (50 % and 47 % on OpenPII-1M) than in English (64 %).

### gliner2

GLiNER2 reaches 81 % and 82 %, with a precision of 97 to 98 %. It finds almost every phone number, e-mail, name, street and number type. Its recall is about the same in the four languages (79 to 84 %).

- **Attributes that are not on its label list**: titles (15 %, `Dekan`, `Sig.ra`), ages (5 %, `64`), gender and sex (43 to 53 %, `Weiblich`, `F`) and times (0 %, `5:38 AM`). The model card has no label for them, so the model does not look for them. Without these five types, its recall is 92 % on OpenPII-1M and 91 % on 500k.
- **Dates in ISO format**: `1999-07-19T00:00:00` and some `21/08/2002` are missed.
- **AVS numbers**: some are missed (`756.8602.4112.23`), and so are French social security numbers written in groups (`1 42 10 49647 462 12`).
- **Long city names**: only part of `Linz Urfahr` or `Swansea Three Crosses` is masked, so the entity counts as a leak.
- **False positives**: few. Common nouns as last names (`women`, `famiglia`), and words such as `credit card` tagged as `payment_card`.

### privacy-filter

OpenAI Privacy Filter is a model that OpenAI published under the Apache 2.0 license. It has 1.5 billion parameters, but it is a sparse mixture of experts: only about 50 million of them work on each token. So it is fast for its size, but it is not small on disk (2.8 GB). It knows 8 types: people, addresses, e-mails, phones, URLs, dates, account numbers and secrets. Its model card says it is primarily English.

It reaches 79 % on OpenPII-1M and 70 % on 500k, with a precision of 97 %. That is below GLiNER2 on both samples, and the gap is larger on 500k, where a third of the entities are given names. Without the five attribute types that neither model looks for (titles, ages, sex, gender, times), it reaches 88 % on OpenPII-1M and 77 % on 500k, against 92 % and 91 % for GLiNER2.

| Language | OpenPII-1M | 500k |
|---|---|---|
| FR | 82.1 % | 69.9 % |
| DE | 77.1 % | 70.5 % |
| IT | 78.9 % | 75.3 % |
| EN | 76.9 % | 64.5 % |

English is not its best language here, even though the card says it is primarily English. Without the five attribute types, English stays the lowest (85.2 % on OpenPII-1M, against 92.2 % in French, 89.4 % in Italian and 86.6 % in German). We have not found why yet.

- **Numbers and IDs**: it is better than GLiNER2 on structured values. It finds 96 % of the dates, 96 % of the `SOCIALNUM` values on OpenPII-1M (GLiNER2 67 %), and 94 to 97 % of the ID, passport, licence and card numbers. It labels almost all of them `account_number`.
- **Names and places**: it misses more names than GLiNER2 (85 % of given names against 95 %), and many cities, streets and building numbers (68 %, 80 % and 75 % on OpenPII-1M). Its card says the model keeps context that is not strongly linked to a person, which may explain part of these misses.
- **Titles**: it masks 70 % of them, against 15 % for GLiNER2, because it puts the title inside the person span (`Dr Nongluk Salihodzic`, `Mlle Marialucia Hivin Magagna`).
- **Attributes**: ages (4 %), sex (3 %), gender (11 %) and times (5 %) are almost never found. It has no type for them.
- **Spans**: the token-by-token choice sometimes cuts an entity. An e-mail can lose its `.com`, or a phone its `+41`. In one Italian text the span of `B@hotmail.com` starts one word too early and stops before `.com`. The constrained decoder of OpenAI's repo is meant to fix such boundaries, and we do not run it.

We also ran it in float32 on OpenPII-1M and on the Swiss set. The recall moved by less than 0.2 points, and the run was faster on this machine (134 s against 184 s on OpenPII-1M). We keep the published bfloat16 weights in the table.

## Which split for T1

Both splits give GLiNER2 the same recall (81 % and 82 %). Presidio does better on 500k (64 % against 54 %), because 500k is mostly short texts full of names: a third of its entities are given names. OpenPII-1M is harder and more varied. Its texts are longer, they hold three times as many entities per text, and its types are more balanced (dates, addresses, ID numbers, cards).

We also found a data problem in 500k: 6 of its 1,000 texts still contain generator placeholders, such as `CITYPlaceHolder_14` or `ORGANISATIONPLACEHOLDER_17`. We found none in OpenPII-1M.

So the numbers support the recommendation of [datasets.md](datasets.md): OpenPII-1M as the training set and its validation split as T1. It is the harder test and the cleaner data. The license and the size were the first reasons, and these runs do not contradict them.

## Swiss identifiers

These samples cannot measure the Swiss part of O1: they have no Swiss IBAN and almost no valid AVS number. So we built a Swiss test set, `t1-swiss.jsonl`, by putting valid fake AVS numbers, IBANs and phone numbers into public rows from validation and test splits. On it, the regex alone reaches 95.4 % on the three Swiss types, GLiNER2 alone 84.8 %, Privacy Filter alone 92.6 %, `regex+gliner2` 99.2 % and `regex+privacy-filter` 99.5 %. See [swiss-identifiers.md](swiss-identifiers.md).

## The app's engine, on 200 texts per set

A 4B model is slow, so we scored the engine on 200 texts per test set, 50 per language, drawn with a fixed seed by `uv run python -m pii_anonymizer.subset` (for example `data/test/t1-openpii-1m.jsonl data/test/t1-openpii-1m-200.jsonl`). Every other detector ran on the same 200 texts, so the table compares like with like. The engine ran on this Mac's GPU, as the app runs it. Quality does not depend on the device: on a probe, a CPU call and a GPU call returned the same answer. No call failed.

Strict recall / character precision on the two T1 samples, and recall on the three Swiss types (AVS, IBAN, PHONE) of the Swiss sample. The size counts every file the detector needs to run.

| Detector | OpenPII-1M, 200 texts | open-pii-500k, 200 texts | Swiss types, 251 values | Size |
|---|---|---|---|---|
| regex | 7.5 % / 100.0 % | 6.2 % / 99.8 % | 96.8 % | rules only |
| presidio | 55.0 % / 87.0 % | 65.9 % / 89.7 % | 77.3 % | 2,357 MB |
| gliner2 | 81.9 % / 98.5 % | 82.6 % / 98.1 % | 84.1 % | 1,244 MB |
| privacy-filter | 79.4 % / 97.5 % | 73.2 % / 97.1 % | 94.4 % | 2,827 MB |
| regex+gliner2 | 82.0 % / 98.5 % | 82.6 % / 98.1 % | 99.2 % | 1,244 MB |
| regex+privacy-filter | 79.5 % / 97.5 % | 73.4 % / 97.1 % | 100.0 % | 2,827 MB |
| engine | 62.4 % / 87.4 % | 63.5 % / 92.3 % | 100.0 % | 2,497 MB |

What the engine shows:

- It finds about 63 % of the entities, about 20 points below GLiNER2, and it masks more text that is not personal data (87.4 % character precision on OpenPII-1M against 98.5 %).
- Most of its misses are types it does not look for. On OpenPII-1M it finds 11 % of the credit card numbers, 15 to 27 % of the ID, passport, tax and driving licence numbers and 13 % of the ages, where GLiNER2 finds 85 to 96 % of the numbers. It finds 54 % of the dates, which it only asks for as birth dates, against 88 %.
- Its rules are its strength. They find all 251 Swiss values, more than our `rules.py` (96.8 %), because they already accept AVS numbers with dashes and lowercase IBANs (review of PR #19).
- Its model is already quantized to 4 bits (Q4_K_M, 4.0B parameters), and its files still weigh twice GLiNER2's.

200 texts is a small sample: one entity is 0.07 points on OpenPII-1M and 0.4 points of the Swiss column. The 1,000-text numbers above stay the reference for the other detectors.

## Latency: not measured yet

The protocol times 30 T2-dev snippets on a machine with no other heavy process running. Until T2-dev exists, `src/pii_anonymizer/latency_ids_t1.txt` holds a temporary sample: 30 texts of `t1-openpii-1m-200.jsonl`, seed 0, written by the same `subset` command with `--latency-ids`. `engine-cpu` passes `num_gpu` 0 and `num_thread` 4 to Ollama through `engine.OLLAMA_OPTIONS`, which the app leaves empty, so its latency compares with the CPU rows. A first probe on this Mac, with other heavy processes running, gave between 2 and 22 tokens per second for the same call. So we report no number until a run on a quiet machine:

```
uv run --group baselines python -m pii_anonymizer.evaluate <detector> data/test/t1-openpii-1m-200.jsonl results/ --latency-ids src/pii_anonymizer/latency_ids_t1.txt
```

## The vocabulary of our four languages

`uv run --group baselines python -m pii_anonymizer.vocab` tokenizes the 103,718 French, German, Italian and English texts of the OpenPII-1M validation split with GLiNER2-PII's tokenizer. They use 77,347 of its 250,112 tokens (30.9 %, special tokens included). Pruned to them, the word embeddings drop from 192.1M to 59.4M parameters, about 59 MB in int8. This is a lower bound: a real pruning also keeps the tokens of the training texts.

Many of these tokens are rare. Keeping only the tokens seen at least 10 times leaves 42,073 tokens (32.3M parameters), which still cover 98.8 % of the text. A word that loses its token would be cut into smaller tokens that remain, so recall must be measured after any pruning.

What this means for the size path, as estimates at one byte per parameter in int8 and half a byte in int4, with the GLiNER2 heads (29.5M) kept. O3 counts the tokenizer too, so the teacher weighs 1,244 MB with its 16 MB tokenizer. We assume that a pruned tokenizer shrinks with its vocabulary.

| Model | Parameters | Size | Smaller than 1,244 MB |
|---|---|---|---|
| Teacher, 12 layers, pruned vocabulary, int8 | 174M | about 179 MB | 7.0 times |
| Student, 6 layers, pruned vocabulary, int8 | 132M | about 137 MB | 9.1 times |
| Same student, embeddings in int4 | 132M | about 107 MB | 11.6 times |
| Same student, tokens seen fewer than 10 times dropped | 105M | about 108 MB | 11.6 times |
| Same student, both | 105M | about 91 MB | 13.6 times |
| O3 target | | about 104 MB | 12 times |

So int8, the pruned vocabulary and six layers give about 9 times. O3 needs both extra steps, or a smaller student, and recall must be measured after each step.

## Next steps

- Run the detectors on T2-dev when it exists (issue #5), and write the latency sample `src/pii_anonymizer/latency_ids.txt`.
- Measure the latency on a quiet machine with the temporary T1 sample, then on the reference laptop, `engine-cpu` included.
- Give `rules.py` the AVS numbers with dashes and the lowercase IBANs that the engine's rules already accept.
- Compute the two v0 thresholds on T2-dev.
