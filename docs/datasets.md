# Datasets for the anonymizer

We checked these facts on 2026-10-19 and 2026-10-20. Our sources are the Hugging Face dataset cards, the Zenodo and GitHub pages, and the PrivAiTe page on PyPI. "Unverified" means that we could not confirm the point from a primary source. The counts come from the cards, not from our own downloads.

## 1. Training (labelled)

| Dataset | Size | Languages | Entity types | Licence and access | URL |
|---|---|---|---|---|---|
| ai4privacy OpenPII-1M | 1,428,143 synthetic examples: train 1,143,397, validation 284,746 | 23, including EN, FR, DE and IT (the card's language list names all four) | 19 | CC BY 4.0, copyright 2026 Ai Suisse SA. Open, no gate. The card metadata says `license: other` with name cc-by-4.0, the card body says CC-BY-4.0. | https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1m |
| ai4privacy open-pii-masking-500k | About 580k rows: train 464k, validation 116k. Card counts over all rows: FR 112,136, DE 82,384, IT 68,824, EN 150,693 | 8: EN, FR, DE, ES, IT, NL, plus HI and TE (experimental) | 19 (examples on the card include GIVENNAME, SURNAME, IDCARDNUM, TAXNUM, ZIPCODE) | The metadata says cc-by-4.0, but the Licensing section says it was built with Llama 3.1 and 3.3 and is subject to the Llama Community License: "Built with Llama" attribution, a model trained on it and distributed must start its name with "Llama", the Llama Acceptable Use Policy applies. The card also says commercial use or redistribution may need written permission. Open, no gate. | https://huggingface.co/datasets/ai4privacy/open-pii-masking-500k-ai4privacy |
| Gretel synthetic_pii_finance_multilingual | 55,940 full documents (train 50.3k, test 5.59k), average 1,357 characters, 100 financial document formats | 7 on the card: EN, ES, SV, DE, IT, NL, FR (not 6 as in our list: Swedish is there, Spanish is there) | 29 | Apache 2.0. Open, no gate. | https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual |
| NVIDIA Nemotron-PII | 100,000 records (train 50k, test 50k), forms, invoices, e-mails and free text, 50+ industries | English, with US and international locales | 55+ PII and PHI categories | CC BY 4.0. Open, no gate. | https://huggingface.co/datasets/nvidia/Nemotron-PII |

Notes.

- The ai4privacy card for the 500k points to newer releases: OpenPII-1M (23 languages) and OpenPII-1.5M (1.6M samples, 30 languages). We did not check OpenPII-1.5M.
- We checked that the validation split of OpenPII-1M exists (284,746 rows), and that EN, FR, DE and IT are all among its 23 languages.
- We did not count the FR, DE and IT rows of OpenPII-1M (unverified).
- We did not check any Swiss identifier format in any of these datasets.

## 2. Unlabelled text for distillation

| Dataset | Size | Languages | Licence and access | URL |
|---|---|---|---|---|
| Loghub | Several system-log collections, from 2.4 MiB (Proxifier) to 29.6 GiB (Thunderbird); up to 211 million lines | Log text, English | No open licence. The README says: "The datasets are freely available for research or academic work", refers any usage or distribution to the repository, and asks for a citation of the Loghub paper. The maintainers do not sanitize the logs, so real personal data can be in them. Our use is academic research, which fits; we do not assume that redistribution is allowed. A separate LICENSE file is linked, which we could not read (unverified). Download via Zenodo. | https://github.com/logpai/loghub , Zenodo https://zenodo.org/records/8196385 |
| Enron Email Dataset | About 0.5M messages from about 150 users, 1.7 GB tar.gz (May 2015 version), no attachments | English | No licence. The CMU page distributes it "as a resource for researchers" and asks users to respect the privacy of the people involved. The data was published by the FERC and cleaned by MIT and SRI. The page reports an April 2026 finding that users could be impersonated in it, and links two papers questioning its authenticity. Real names and addresses are in it: do not redistribute, and do not publish samples. | https://www.cs.cmu.edu/~enron/ |
| Code (which corpus) | Not chosen yet | Code | Unverified. If we take open repositories, each file carries its own licence; the corpus must be named before v0. | none |

## 3. Out-of-distribution benchmarks (reported only, no threshold)

| Dataset | Size | Languages | Entity types | Licence and access | URL |
|---|---|---|---|---|---|
| SPY (Fastino's benchmark) | 4,491 medical consultations and 4,197 legal questions, synthetic | English | 7: url, email, username, address, name, phone number, id_num | CC BY 4.0. Not gated, but the loading needs `trust_remote_code=True` (loading script). | https://huggingface.co/datasets/mks-logic/SPY |
| TAB (Text Anonymization Benchmark) | 1,268 ECHR cases annotated by hand; the viewer shows 2,208 rows because some documents have several annotators; train 1.11k, validation 541, test 555 rows | English | Direct and quasi-identifiers (the types are not listed on the card page we read) | MIT. Open. | https://huggingface.co/datasets/ildpil/text-anonymization-benchmark |
| GraSCCo_PHI | German synthetic hospital discharge letters. Our earlier note says 63 documents (first release); the card of the latest release does not state the number (unverified for v2) | German | PII annotations, called PHI before (XMI and JSON exports, guideline); categories not listed on the page | Latest release GraSCCo_PII_V2, 2025-09-07: CC BY 4.0. Open. Our earlier note said the base corpus is CC0. | https://zenodo.org/records/15747389 |
| BigCode PII | 12,099 samples of about 50 lines of code, 31 programming languages | Code, with English comments | Names, usernames, e-mails, IP addresses, keys, passwords, IDs (subtypes such as EMAIL_EXAMPLE, NAME_LICENSE, AMBIGUOUS) | **Gated, manual approval.** You accept conditions and fill a linked form. Terms: use only to train or evaluate PII-removal models, no sharing of the dataset or any modified version, as is, no liability. The card names no licence for the dataset itself. Request access early, each member who needs the data must request it. | https://huggingface.co/datasets/bigcode/bigcode-pii-dataset |
| privaite-bench | About 92 documents and 300 PII entries in total; 64 documents for precision and recall; the comparison uses 120 documents with 458 items from ai4privacy `pii-masking-200k` (DE, EN, FR, IT) plus 14 clean documents | FR, EN, DE, ES, IT (latency tests up to 7 languages) | Not stated | **It exists.** It is a small benchmark suite for PrivAiTe, not a large dataset: synthetic samples written by the author, DLP Test and Enedis report extracts, ai4privacy documents, plus Claude Code and Codex agent runs with planted secrets. **No licence is stated** in the repository: cite it, do not redistribute. It runs from a sibling PrivAiTe checkout. | https://github.com/crp4222/privaite-bench |

## 4. Our own sets

| Set | Size | Languages | Entity types | Licence and access | Where |
|---|---|---|---|---|---|
| T1 | The validation split of the training dataset we choose at v0: 284,746 rows if OpenPII-1M (we sample FR, DE, IT and EN from it), 116k rows if open-pii-masking-500k (FR, DE, IT, EN only) | FR, DE, IT, EN | The 19 ai4privacy types | The licence of the source dataset. Never used for training. | see section 1 |
| T2 | About 200 snippets (code, logs, JSON, CSV, e-mails, command outputs), split into dev and a frozen final test | Mostly FR, DE, IT, EN with Swiss identifiers | Planted values (AVS 756..., Swiss IBAN, +41 phone numbers, postal codes) and incidental entities | Ours. No public dataset has Swiss identifiers in tool outputs. Synthetic, so it can be published. | to be built before v0 |

## What to watch

- **BigCode PII** is the only gated set. Its terms forbid sharing the data or anything made from it. So it must never go into our repository, our data storage or an artifact. We report scores only.
- **Llama licence** on open-pii-masking-500k: if we distribute a student fine-tuned on it, its name must start with "Llama", and it must carry "Built with Llama". The metadata says CC BY 4.0, but that is not the whole story.
- **Enron and Loghub** have no open licence, and they contain real personal data. We use them only for pseudo-labelling (the teacher labels them, and the student learns from these labels). We do not redistribute them, and we do not print their content in the report.
- **privaite-bench** is small and has no licence. It is a point of comparison with PrivAiTe, not a benchmark we can rely on.
- The 464k figure in [smart-goals.md](smart-goals.md) is the whole train split of open-pii-masking-500k, in all 8 languages. The 500k has 263,344 FR, DE and IT rows over train and validation together (card counts). So about 80 % of them are in train (the card does not give the split by language, unverified).

## Open decision: teacher fine-tuning data

The team has not chosen between two options yet. We choose at v0.

**Option A: OpenPII-1M plus Gretel**, with T1 = the OpenPII-1M validation split.

- Licences: CC BY 4.0 and Apache 2.0. So there is no naming or attribution rule on the models we publish.
- Far more rows: 1.14M in train, 23 languages, and a newer release.
- Gretel adds long financial documents with 29 types in FR, DE and IT.
- Weak points: the FR, DE and IT counts are not verified, and neither dataset has Swiss identifiers.

**Option B: open-pii-masking-500k, only the FR, DE and IT rows** (this is what [smart-goals.md](smart-goals.md) says today).

- About 264k rows over both splits before filtering. We have already counted them.
- Smaller, so faster to train.
- Weak points: the Llama Community License puts "Built with Llama" and a "Llama" model name on our published student. The control student would also have fewer rows.

Both candidates are synthetic and in-distribution (they look like the training data). So T1 is optimistic whichever we take, and the real evidence comes from the OOD benchmarks and T2.

Our recommendation is A, for the licence and the size. A short v0 run of the baselines on both validation splits will confirm it or not.
