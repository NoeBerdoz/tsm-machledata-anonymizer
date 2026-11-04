# Datasets for the Anonymizer

Our sources are the Hugging Face dataset cards and dataset viewer, the Zenodo and GitHub pages, and the PrivAiTe page on PyPI. "Unverified" means that we could not confirm the point from a primary source. Counts come from the cards, or from the Hugging Face dataset viewer statistics (computed over the full split), not from our own downloads. Every "20 rows read" check below means the first 20 English rows, read by hand.

## 1. Summary table

Label format: "offsets" = character offsets (start/end) in the text; "inline" = the masked text carries the label (for example `[GIVENNAME_1]`), no offsets. The ai4privacy datasets have both: the masked text is inline, and the `privacy_mask` field gives the offsets. So T1 gets the gold character offsets that [smart-goals.md](smart-goals.md) asks for.

| Dataset | License | FR / DE / IT / EN | Size | Entity types | Label format | Text style | Swiss identifiers | 20 rows read | URL |
|---|---|---|---|---|---|---|---|---|---|
| OpenPII-1M (ai4privacy) | CC BY 4.0 | All four among 23 languages. FR 131,173, DE 120,105, IT 89,304, EN 179,419 (train and validation) | 1,428,143 rows: train 1,143,397, validation 284,746 | 19 (DATE, GIVENNAME, SURNAME, EMAIL, CITY, ...) | Offsets with value, in `privacy_mask`: `{"label": "CITY", "start": 35, "end": 41, "value": "Ruswil"}`. Also inline (`[CITY_1]`) | E-mails and short messages | Not on the card's type list. Not searched in the rows (unverified) | Yes, see 2.1 | https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m |
| open-pii-masking-500k (ai4privacy) | Metadata says CC BY 4.0, but the Llama Community License applies (see section 5) | FR 112,136, DE 82,384, IT 68,824, EN 150,693 (train and validation) | About 580k rows: train 464,150, validation 116,077 | 19 (GIVENNAME, SURNAME, IDCARDNUM, TAXNUM, ZIPCODE, ...) | Same as OpenPII-1M: offsets with value in `privacy_mask`, plus inline | Not checked | Not on the card's examples. Not searched in the rows (unverified) | No | https://huggingface.co/datasets/ai4privacy/open-pii-masking-500k-ai4privacy |
| Gretel synthetic_pii_finance_multilingual | Apache 2.0 | 7 languages: EN 28,910 documents, 6 others (ES, SV, DE, IT, NL, FR) about 4,500 each | 55,940 documents: train 50.3k, test 5.59k, average 1,357 characters | 29 (mostly name, date, company, street address, time, email) | Offsets, `{"start": 119, "end": 141, "label": "date"}` | 100 financial document formats, long documents | Not on the card's type list. Not searched in the rows (unverified) | Yes, see 2.2 | https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual |
| Nemotron-PII (NVIDIA) | CC BY 4.0 | EN only (US and international locales) | 100,000 records: train 50k, test 50k (see note below) | 55+ PII and PHI categories | Offsets with text, `{'start': 3, 'end': 8, 'text': 'Jason', 'label': 'first_name'}` | Structured and unstructured documents (forms, invoices, e-mails, free text), 50+ industries | Not searched (unverified). SSNs are US | Yes, see 2.3 | https://huggingface.co/datasets/nvidia/Nemotron-PII |
| SPY | CC BY 4.0. Loading needs `trust_remote_code=True` | EN only | 4,491 medical consultations and 4,197 legal questions | 7 (url, email, username, address, name, phone number, id_num) | Inline, type with index | Prose | Not searched (unverified) | No, could not inspect, see 2.4 | https://huggingface.co/datasets/mks-logic/SPY |
| TAB (Text Anonymization Benchmark) | MIT | EN only | 1,268 ECHR cases, hand-annotated. The viewer shows 2,208 rows (several annotators): train 1.11k, validation 541, test 555 | Direct and quasi-identifiers (types not listed on the card page we read) | Not checked | Court judgments (prose) | Not expected (ECHR cases). Not searched (unverified) | No | https://huggingface.co/datasets/ildpil/text-anonymization-benchmark |
| GraSCCo_PHI / PII_V2 | CC BY 4.0 (release 2025-09-07). Earlier note: base corpus CC0 | DE only | 63 documents in the first release. Not stated for v2 (unverified) | PII annotations, categories not listed on the page | XMI and JSON exports. Offsets not confirmed | Synthetic hospital discharge letters (prose) | No (German corpus, not Swiss). Not searched (unverified) | No | https://zenodo.org/records/15747389 |
| BigCode PII | Gated, manual approval. No license named for the dataset (see section 5) | Code, with English comments | 12,099 samples of about 50 lines, 31 programming languages | Names, usernames, e-mails, IP addresses, keys, passwords, IDs (subtypes such as EMAIL_EXAMPLE, NAME_LICENSE, AMBIGUOUS) | Not checked | Code | Not searched (unverified) | No. Access must be requested first | https://huggingface.co/datasets/bigcode/bigcode-pii-dataset |
| privaite-bench | None stated: cite it, do not redistribute | FR, EN, DE, ES, IT | About 92 documents and 300 PII entries. The comparison uses 120 documents with 458 items from ai4privacy `pii-masking-200k` plus 14 clean documents | Not stated | Not checked | Mixed: synthetic samples, DLP Test and Enedis report extracts, agent runs with planted secrets | Not checked | No | https://github.com/crp4222/privaite-bench |

Note on Nemotron-PII: our first note said 200k rows, the later check says 100,000 records (50k train, 50k test). We use 100,000 until we re-check the card.

Notes.

- The 500k card points to newer releases: OpenPII-1M (23 languages) and OpenPII-1.5M (1.6M samples, 30 languages). We did not check OpenPII-1.5M.
- Rows per language, from the dataset viewer statistics (train / validation):

  | Language | OpenPII-1M | open-pii-masking-500k |
  |---|---|---|
  | FR | 105,227 / 25,946 | 89,670 / 22,466 |
  | DE | 96,179 / 23,926 | 65,899 / 16,485 |
  | IT | 71,362 / 17,942 | 55,004 / 13,820 |
  | EN | 143,515 / 35,904 | 120,533 / 30,160 |

  The 500k totals match the counts on its card.
- We did not check any Swiss identifier format in any of these datasets. "Not searched" means that none appears on the cards, not that we confirmed it by searching the rows. This must be done before we write "no" in the table (to do).
- The 464k figure in [smart-goals.md](smart-goals.md) is the whole train split of open-pii-masking-500k, in all 8 languages. Its FR, DE, and IT rows are 263,344 over both splits, of which 210,573 (80 %) are in train.

## 2. What we saw in the rows

### 2.1 OpenPII-1M

After reading the first 20 English rows, we found a few false positives: text that is not PII is masked. Example: "we kindly ask you to fill out the attached taste profile, including your age (2)" becomes "... including your age ([AGE_1])". "age (2)" is not PII and should not be encoded as `[AGE_1]`. There are a few other false positives. We did not find any PII that was not masked.

### 2.2 Gretel

The spans give the start and end characters and the type. This makes it a lot harder for a human to check the labels without running code. The dataset provides several scores, such as a conformance score and a quality score.

### 2.3 Nemotron-PII

Spans carry the text and the label, which is better than Gretel's format: a human can check them by eye. Mixing structured and unstructured documents is a good idea and will probably make models trained on it more robust. We found no false positives in the first 20 rows.

### 2.4 SPY

We were unable to inspect this dataset. We will most likely not use it for training, because of its small size. We keep it as an out-of-distribution benchmark.

### 2.5 TAB, GraSCCo, BigCode PII, privaite-bench, open-pii-masking-500k

No rows read yet (to do before v0, tracked in Issue #20). For BigCode PII, request access first; each member who needs the data must request it.

All the rows we read so far are English, but we train on FR, DE, and IT. We will check rows in these languages with an agent and an LLM as a judge (same issue).

## 3. Unlabelled text for distillation

| Dataset | Size | Languages | License and access | URL |
|---|---|---|---|---|
| Loghub | Several system-log collections, from 2.4 MiB (Proxifier) to 29.6 GiB (Thunderbird); up to 211 million lines | Log text, English | No open license. The README says the datasets are freely available for research or academic work, refers any usage or distribution to the repository, and asks for a citation of the Loghub paper. The maintainers do not sanitize the logs, so real personal data can be in them. Our use is academic research, which fits; we do not assume that redistribution is allowed. A separate LICENSE file is linked, which we could not read (unverified). Download via Zenodo. | https://github.com/logpai/loghub , Zenodo https://zenodo.org/records/8196385 |
| Enron Email Dataset | About 0.5M messages from about 150 users, 1.7 GB tar.gz (May 2015 version), no attachments | English | No license. The CMU page distributes it as a resource for researchers and asks users to respect the privacy of the people involved. The data was published by the FERC and cleaned by MIT and SRI. The page reports an April 2026 finding that users could be impersonated in it, and links two papers questioning its authenticity. Real names and addresses are in it: do not redistribute, and do not publish samples. | https://www.cs.cmu.edu/~enron/ |
| Code (which corpus) | Not chosen yet | Code | Unverified. If we take open repositories, each file carries its own license. The corpus must be named before v0. | none |

## 4. Our own sets

| Set | Size | Languages | Entity types | License and access | Where |
|---|---|---|---|---|---|
| T1 | The validation split of the training dataset we choose at v0: 284,746 rows if OpenPII-1M (we sample FR, DE, IT, and EN from it), 116k rows if open-pii-masking-500k (FR, DE, IT, EN only) | FR, DE, IT, EN | The 19 ai4privacy types | The license of the source dataset. Never used for training. | see section 1 |
| T2 | About 200 snippets (code, logs, JSON, CSV, e-mails, command outputs), split into dev and a frozen final test | Mostly FR, DE, IT, EN with Swiss identifiers | Planted values (AVS 756..., Swiss IBAN, +41 phone numbers, postal codes) and incidental entities | Ours. No public dataset has Swiss identifiers in tool outputs. Synthetic, so it can be published. | to be built before v0 |

## 5. What to watch

- **BigCode PII** is the only gated set. Its terms allow use only to train or evaluate PII-removal models, and forbid sharing the data or any modified version. So it must never go into our repository, our data storage or an artifact. We report scores only.
- **Llama license** on open-pii-masking-500k: it was built with Llama 3.1 and 3.3. If we distribute a student fine-tuned on it, its name must start with "Llama", and it must carry "Built with Llama". The Llama Acceptable Use Policy applies, and the card says commercial use or redistribution may need written permission. The metadata says CC BY 4.0, but that is not the whole story.
- **OpenPII-1M license metadata** says `license: other` with the name cc-by-4.0, while the card body says CC BY 4.0 (copyright 2026 Ai Suisse SA). We treat it as CC BY 4.0.
- **Enron and Loghub** have no open license, and they contain real personal data. We use them only for pseudo-labelling (the teacher labels them, and the student learns from these labels). We do not redistribute them, and we do not print their content in the report.
- **privaite-bench** is small and has no license. It is a point of comparison with PrivAiTe, not a benchmark we can rely on. It runs from a sibling PrivAiTe checkout.

## 6. Recommendation

### Training set (open decision, we choose at v0)

**Option A: OpenPII-1M plus Gretel**, with T1 = the OpenPII-1M validation split.

- Licenses: CC BY 4.0 and Apache 2.0. CC BY 4.0 requires attribution, and Apache 2.0 requires us to keep its license notice, so we credit both datasets in the model card and the report. Unlike the Llama license, they put no rule on how we name the models we publish.
- Far more rows: 1.14M in train, 23 languages, and a newer release. Its train split has 272,768 FR, DE, and IT rows, against 210,573 for option B.
- Gretel adds long financial documents with 29 types in FR, DE, and IT.
- Weak point: neither dataset has Swiss identifiers.

**Option B: open-pii-masking-500k, only the FR, DE, and IT rows** (this is what [smart-goals.md](smart-goals.md) says today).

- 263,344 rows over both splits before filtering, 210,573 of them in train.
- Smaller, so faster to train.
- Weak points: the Llama Community License puts "Built with Llama" and a "Llama" model name on our published student. The control student would also have fewer rows.

**Our recommendation is A**, for the license and the size. A short v0 run of the baselines on both validation splits will confirm it or not.

### Test sets

- **T1** = the validation split of the chosen training dataset (OpenPII-1M validation under Option A), sampled in FR, DE, IT, and EN. Never used for training. It is synthetic and in-distribution, so T1 is optimistic whichever option we take.
- **Out-of-distribution benchmarks**, reported only, with no pass/fail threshold: TAB (EN), GraSCCo (DE), SPY (EN), Nemotron-PII (EN, test split: structured and unstructured documents; we do not train on it because it is English only), BigCode PII (code, scores only, never shared), and privaite-bench (small, as a point of comparison).
- **T2** (our own, with Swiss identifiers) is the main real evidence. It must be built before v0.
