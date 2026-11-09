# Baselines

What off-the-shelf detectors already reach, before we train anything (issue #6). We ran three detectors through the evaluation script of [evaluation.md](evaluation.md) on samples of the two candidate T1 validation splits named in [datasets.md](datasets.md).

These are **T1 candidate numbers only**. T2-dev does not exist yet (issue #5), so the T2-dev rows, the latency and the two v0 thresholds of [smart-goals.md](smart-goals.md) come later. All rows below were measured on a development machine (Apple M5 Max), **not on the reference laptop**. Quality does not depend on the machine, but the wall times below only say how long a run takes here.

## The detectors

- **regex** (`src/pii_anonymizer/rules.py`): our rules for Swiss identifiers, pure Python. AVS numbers (756 and 10 digits, EAN-13 check digit), CH and LI IBANs (mod-97 checksum), Swiss phone numbers (+41, 0041 or 0, then nine digits in the usual groups) and e-mail addresses. Labels `AVS`, `IBAN`, `PHONE`, `EMAIL`.
- **presidio**: Presidio's `AnalyzerEngine` 2.2.366 with the spaCy large models for English, French, German and Italian, the default recognizers and the default score threshold. The default configuration already gives the language-independent pattern recognizers (e-mail, IBAN, phone, IP, URL, date) to every language. We add the credit card recognizer to French and German, because the default lists it only for English and Italian. Presidio receives the true language of each text, which slightly favours it (see [evaluation.md](evaluation.md)).
- **gliner2**: `fastino/gliner2-privacy-filter-PII-multi` as published, on the CPU, with the 42 labels of its model card and the card's threshold of 0.5. Texts go through `extract_entities_long`, the library's way to handle long texts. Our texts are short (at most 177 words), so each text fits in one chunk. On a long Gretel document, the library gave the last word an end one character past the text. We clip such a span to the text.
- **regex+gliner2**: the two detectors together. It masks every span that either of them finds, because goal O1 measures the Swiss identifiers caught by the regex and the model together. Its size is the size of GLiNER2, since the regex has no files.

The code of the detectors is in `src/pii_anonymizer/baselines.py`. They need the `baselines` dependency group ([development.md](development.md)).

## The samples

`uv run python -m pii_anonymizer.public_data data/test/` writes two T1 files (and the Gretel sample of [swiss-identifiers.md](swiss-identifiers.md)). Each T1 file holds 250 rows per language (FR, DE, IT, EN) of a validation split, drawn with a fixed seed (42). The labels stay as the datasets write them.

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

`regex+gliner2` gives the same numbers as GLiNER2 alone, rounded: the samples have almost no valid Swiss values for the regex to add. It protects 5 more entities on OpenPII-1M, among them 2 `SOCIALNUM` and 2 `EMAIL`, and 1 more `TELEPHONENUM` on 500k.

The size of Presidio is the four spaCy models. The size of GLiNER2 is its weights in fp32, its configs and its tokenizer. The full rows are in `results/results.csv` and `results/recall_per_type.csv`.

Recall per type for the main types (OpenPII-1M first, then 500k):

| Type | Gold (1M / 500k) | regex | presidio | gliner2 |
|---|---|---|---|---|
| GIVENNAME | 858 / 771 | 0 / 0 % | 79 / 79 % | 95 / 90 % |
| SURNAME | 764 / 307 | 0 / 0 % | 78 / 78 % | 95 / 93 % |
| DATE | 871 / 106 | 0 / 0 % | 46 / 58 % | 86 / 92 % |
| EMAIL | 511 / 123 | 100 / 100 % | 100 / 100 % | 99 / 100 % |
| CITY | 506 / 158 | 0 / 0 % | 83 / 87 % | 88 / 80 % |
| TELEPHONENUM | 376 / 147 | 13 / 14 % | 45 / 48 % | 99 / 99 % |
| STREET | 339 / 103 | 0 / 0 % | 59 / 55 % | 96 / 93 % |
| BUILDINGNUM | 330 / 93 | 0 / 0 % | 12 / 16 % | 94 / 89 % |
| ZIPCODE | 294 / 43 | 0 / 0 % | 19 / 19 % | 94 / 79 % |
| IDCARDNUM | 241 / 89 | 0 / 0 % | 29 / 36 % | 92 / 81 % |
| CREDITCARDNUMBER | 232 / 16 | 0 / 0 % | 24 / 12 % | 90 / 94 % |
| SOCIALNUM | 168 / 17 | 5 / 12 % | 44 / 47 % | 67 / 88 % |
| TITLE | 461 / 85 | 0 / 0 % | 51 / 47 % | 15 / 26 % |
| AGE | 379 / 50 | 0 / 0 % | 15 / 14 % | 5 / 14 % |
| TIME | 0 / 98 | (none) / 0 % | (none) / 17 % | (none) / 0 % |

Wall time for one run of 1,000 texts on this machine, loading included: regex about 1 s, Presidio 16 s (OpenPII-1M) and 12 s (500k), GLiNER2 134 s and 105 s.

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

## Which split for T1

Both splits give GLiNER2 the same recall (81 % and 82 %). Presidio does better on 500k (64 % against 54 %), because 500k is mostly short texts full of names: a third of its entities are given names. OpenPII-1M is harder and more varied. Its texts are longer, they hold three times as many entities per text, and its types are more balanced (dates, addresses, ID numbers, cards).

We also found a data problem in 500k: 6 of its 1,000 texts still contain generator placeholders, such as `CITYPlaceHolder_14` or `ORGANISATIONPLACEHOLDER_17`. We found none in OpenPII-1M.

So the numbers support the recommendation of [datasets.md](datasets.md): OpenPII-1M as the training set and its validation split as T1. It is the harder test and the cleaner data. The license and the size were the first reasons, and these runs do not contradict them.

## Swiss identifiers

These samples cannot measure the Swiss part of O1: they have no Swiss IBAN and almost no valid AVS number. So we built a Swiss test set, `t1-swiss.jsonl`, by putting valid fake AVS numbers, IBANs and phone numbers into public rows from validation and test splits. On it, the regex alone reaches 95.4 % on the three Swiss types, GLiNER2 alone 84.8 %, and `regex+gliner2` 99.2 %. See [swiss-identifiers.md](swiss-identifiers.md).

## Next steps

- Run the three detectors on T2-dev when it exists (issue #5), and write the latency sample `src/pii_anonymizer/latency_ids.txt`.
- Measure the latency on the reference laptop.
- Compute the two v0 thresholds on T2-dev.
