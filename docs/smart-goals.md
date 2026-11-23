# SMART goals: a small on-device PII pseudonymizer for cloud LLMs

Draft of 2026-10-20, updated on 2026-11-09 for the app design and on 2026-11-15 to make the goals realisable. The rules are frozen at the seminar talk on 2026-11-16. The numbers that depend on T2-dev are recorded on T2-dev before any tuning.

## The project

People send prompts and documents to cloud LLMs, and these texts often hold personal data. In our app, the user writes a prompt and can attach files (PDF, TXT, DOCX, CSV).

We build a small model that runs on the user's laptop. Together with regex rules, it detects sensitive entities in the prompt and in the text of the files. The app replaces them with consistent replacements before anything is sent, and it keeps the mapping table on the device. Only the pseudonymized text goes to our backend, which sends it to an LLM: the local Ollama by default, or a hosted model such as OpenAI or Claude. When the response comes back, the app restores the real values on the device. So the user sees a normal answer, and neither our backend nor the LLM sees the real values that the engine detects (see [architecture.md](architecture.md)).

The mapping table lets us put the real values back. So we call it pseudonymization, not anonymization: the data can still be linked to a person with extra information, here the mapping table kept on the device. The GDPR draws the same line between the two (Art. 4(5) and Recital 26).

Our advanced topic is model optimization. We fine-tune a teacher, distill it into a small student, quantize the student, and measure what each step costs in protection.

PrivAiTe and HaS (Hide and Seek, 2023) already show that such a pseudonymizer can exist. Our question is: how small and fast can the detector be, while the leak stays low and the answers stay useful? We look at French, German and Italian, Swiss identifiers, and prompts and attached files.

## Models and test sets

The teacher is `fastino/gliner2-privacy-filter-PII-multi` (GLiNER2-PII). We fine-tune it on our training set. The fine-tuning is mainly for the entities it misses: as published, it misses about 1 entity in 5 on T1 (80.6 % recall, 5,867 of 7,275 entities), and some types are weak (ages 5 %, titles 15 %, social security numbers 67 %). The regex already finds most Swiss numbers. Swiss identifiers stay in the fine-tuning data as a second net, for the formats the regex does not know. For example, the regex finds 0 of 12 AVS numbers written with dashes, and GLiNER2-PII finds 8 of 12.

The training data and T1 are decided (see [test-set-decision.md](test-set-decision.md)). We train on ai4privacy OpenPII-1M plus Gretel.

The training budget is a fixed, seeded subset of 50,000 rows in total, from both sources. The teacher, the student and the control student all train on it. Two epochs for each of the three models, plus one pass to compute the teacher's soft labels, take about 5.4 hours of T4 GPU, about USD 3.40. This estimate uses the 18 rows per second of our smoke run and USD 0.62 per hour, without startup, evaluation and retries (see [cloud-training.md](cloud-training.md)). On all French, German, Italian and English rows, one run of the three models would take about 50 hours of our one T4 GPU, about USD 30. The fixed subset keeps a run at about 5.4 hours, leaves room for retries within our USD 50 of credits, and gives the three models the same budget.

We measured the published model from its safetensors header. It has 307M parameters in float32 (1.23 GB). 192M of them (63 %) are the word embeddings of its 250,112-token multilingual vocabulary.

Regular expressions handle the structured identifiers. These rules are the same in every comparison.

- **T1** is a fixed sample of the OpenPII-1M validation split: `data/test/t1-openpii-1m.jsonl`, 1,000 texts, 250 in each of French, German, Italian and English, drawn with seed 42 from a pinned commit of the dataset. Its SHA-256 is recorded in `results/results.csv`. We never train on the validation split.
- **T2** is our own set of about 200 snippets of what users send through our app: prompts, e-mails, documents, tables (CSV), pasted code or logs. For an attached file, the snippet is the text extracted from it, because that is what the detector receives. The snippets are stored in one JSONL file with character offsets (format in issue #5). We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes). So we know the labels by construction. We also annotate any incidental sensitive entity that a snippet already contains. By 30 November (v1), before any tuning, we freeze T2's annotation policy, its groups, its mix of types and formats, and the file hashes. The policy treats personal attributes as personal data, titles, ages, sex and gender included, so a model that masks them is not counted as over-masking. Before any tuning, we split T2 into two parts: a dev part, used for thresholds and the CI gates, and a frozen final-test part. Related snippets stay on the same side. We record the file hashes, and we run the final test only on the selected models.

Both sets carry gold character offsets (the exact position of each true entity). **An entity counts as protected only if every character except spaces is masked.** So a partly masked IBAN is a leak.

- **Recall** is the micro-average of this rule over the gold entities. We also report it per entity type. It is the primary metric, because one minus recall is the leak rate.
- **Character precision** is the share of masked characters that belong to a gold entity. It shows over-masking: a model that masks everything fails it.

## The goals

### O1 Protection

The quantized student keeps at least 95 % of the fine-tuned teacher's recall on T1 and on T2-final, and never falls below GLiNER2-PII as published. With the regex, the app's detector reaches at least 99 % recall on Swiss structured identifiers.

- **S.** We compare the delivered student (v3, distilled and quantized) with the fine-tuned teacher (v1) on T1 and on T2-final, each set separately. All comparisons use the same entity types. The 95 % ratio and the floor compare the models alone, without the regex rules, on each test set, so that they measure what compression costs. The Swiss line measures the app's detector: the regex and the model together. The Swiss structured identifiers are AVS numbers, IBANs and phone numbers. We also report the recall of the regex and the model together, as the app runs them, and: the student's absolute recall, overall and per type; GLiNER2-PII's recall per type; and a control student. The control has the same architecture, data and budget, but it learns from the gold labels only (alpha = 0). It answers the question "does distillation help?", whatever the answer is. If time allows, we also report recall and character precision on out-of-distribution sets: SPY, TAB, GraSCCo_PHI and BigCode PII (see [datasets.md](datasets.md) for their licences; BigCode PII is gated and is never redistributed). These sets are optional.
- **M.** Student recall divided by teacher recall must be at least 0.95 on each test set, both models alone. On each test set, the student's overall recall must also be at least GLiNER2-PII's as published, alone and under the same conditions (80.6 % on T1, 5,867 of 7,275 entities). On T2-final, the regex and the student together must reach at least 99 % recall on the Swiss types. The 99 % is pooled over AVS numbers, IBANs and phone numbers, and we report each type's counts. Every pass or fail decision uses the unrounded counts, never rounded percentages.
- **A.** Compression always costs some recall. We accept a loss of at most 5 % of the teacher's recall for a model 8 times smaller. With half the layers, DistilBERT kept 97 % of BERT's score (Sanh et al., 2019). On our Swiss test set, the regex plus GLiNER2-PII already protect 775 of 781 values (99.2 %), so the goal checks that compression does not break this. This pooled figure hides AVS numbers at 164 of 168 (97.6 %). On T1, a fine-tuned teacher at 85 % makes the 80.6 % floor follow from the 95 % rule (95 % of 85 % is 80.75 %). On T2-final, the same holds once the teacher reaches GLiNER2-PII's recall on that set divided by 0.95. Two thirds of GLiNER2-PII's misses on T1 are four types it has no label for (titles, ages, sex and gender), and our training data labels them. Our baselines make these targets plausible, not proven. The cloud test of 2026-11-09 covered only 13 of the 19 types: it shows that training works, not the final protection.
- **R.** This goal measures what compression costs in protection, which is the core of our advanced topic.
- **T.** We evaluate it at the final talk, in week 14 of the course plan (mid-December 2026).

### O2 Utility

The pseudonymization does not mask so much that the answers get worse.

- **S.** We measure the student's character precision on T2-final. We also write 20 test prompts with their answer checks: summaries, value extraction and questions on tables, in our four languages, at least 10 of them with an attached file (CSV, PDF or DOCX), with values repeated across the prompt and the files. A test prompt is a prompt, with or without an attached file, and an answer check (oracle) fixed in advance, for example an exact value, expected fields in a JSON answer, or a label. We also write 5 stress prompts that need to link two forms of one person, for example a salary question about "Marie Dupont" on a table where her first name and surname sit in two cells. Linking is out of scope (issue #31), so they are reported apart. Every prompt runs through our app (engine, backend, LLM, restoration), with and without pseudonymization. We pin the LLM endpoint, its model version and its settings. Each prompt runs 3 times in each condition. It counts as solved in a condition when its answer check passes at least 2 of the 3 times. We keep every result. The replacement is a placeholder such as `<PERSON_1>` (issue #17), so the gap between the two conditions also shows what placeholders cost.
- **M.** We first run the 20 test prompts without pseudonymization: at least 18 must be solved, or we fix the set. Then we freeze the prompts and their checks (a hash of the file is committed). We freeze the results without pseudonymization, so which prompts are solved, before any run with it. Utility is the number of test prompts solved in both conditions divided by the number solved without pseudonymization. It must be at least 90 %. We report both counts, and the 5 stress prompts with their own counts, outside the 90 %. The student's character precision on T2-final must be at least GLiNER2-PII's on T2-final. For the development gate, GLiNER2-PII's character precision on T2-dev is recorded before any tuning.
- **A.** The 20 test prompts are small enough to run on every model version. The prompts in scope need no linking of names, and a repeated value always gets the same placeholder, so 90 % is plausible, but it stays unverified until the first paired run. 90 % means: with 20 solved prompts, at most 2 may break. With 18 or 19, at most 1 may break (17 of 18, 18 of 19, 18 of 20). That is 120 calls per model version, 150 with the 5 stress prompts.
- **R.** O1 alone can be met by masking everything, so O2 checks that the answers stay useful. The precision floor limits how much is masked by mistake. O1 and O2 pull in opposite directions, and the central result of the talk is where each compressed model sits between them.
- **T.** The prompts are frozen with T2, by v1 (30 November). We evaluate it at the final talk, in week 14 of the course plan (mid-December 2026).

### O3 Compression

The delivered student is at least 8 times smaller and at least 1.5 times faster than the fp32 teacher on a laptop CPU.

- **S.** Size counts all files needed to run the model, weights and tokenizer. We measure the p95 latency of every model on the reference laptop CPU, an Intel Core i5-1130G7, with the frozen protocol of [benchmark-protocol.md](benchmark-protocol.md): 30 texts, 10 runs each, so 300 calls per model. We measure the teacher on the same laptop. The 30 latency texts are drawn from T2-dev with a fixed seed, across its sources, before any timing. We record each model's runtime and its version. When the student's runtime can also run the teacher, we time both in it. Otherwise the ratio is the speedup of the deployed system, and we name both runtimes.
- **M.** The size ratio uses the exact bytes. The teacher measures 1,244,444,426 bytes (1,244 MB), so the student must weigh at most one eighth of it, about 155.6 MB. The student's p95 latency must be at most two thirds of the teacher's p95, which means at least 1.5 times faster. We publish a compression curve with one point per step, at least 4, each with its recall, size and latency: the fp32 teacher, the teacher with the pruned vocabulary, the same in int8, and the distilled student in int8 with the pruned vocabulary. The options add 2 more points: int4 embeddings, and rare tokens dropped.
- **A.** Our projection for six layers, a pruned vocabulary and int8 weight storage is about 150 MB, giving about 6 MB of estimated margin. Pruning the vocabulary mainly saves space. On the Intel Core i7-1355U, the published model with mixed activations ran 1.38 times as fast as fp32 at p95 (1,372.40 ÷ 996.72), short of the 1.5 times target. The speed target still rests on halving the layers. DistilBERT used half of BERT's layers and ran 1.63 times as fast in the CPU benchmark. NoeBerdoz/tsm-machledata-anonymizer#73 measures the reference laptop. [GLiNER2 baselines](baselines.md#gliner2-int8) · [Sanh et al. (2019), Table 3](https://arxiv.org/html/1910.01108#S4.T3)
- **R.** The model runs before every request, on the user's laptop, and attached files can be long, so its speed matters to the user. Also, the model has to run where the data is allowed to be. Each curve point shows what one step costs in recall, size and latency, which is our advanced topic.
- **T.** We evaluate it at the final talk, in week 14 of the course plan (mid-December 2026).

We apply post-training quantization (PTQ) first. The PTQ student is the int8 student that meets the O3 size limit. We run quantization-aware training (QAT, NoeBerdoz/tsm-machledata-anonymizer#74) only if that PTQ student fails the O1 rule on T1 or T2-dev. We reserve T2-final for the final evaluation. The mixed PTQ policy lost about one recall point on the published model on OpenPII-1M T1. The student's own measurements decide whether we run QAT. We withdrew the earlier conclusion that QAT was likely on [2026-11-18](baselines.md#why-we-changed-the-int8-policy-2026-11-18).

### O4 End-to-end protection in our app

In scripted requests through our app, the app adds no leak, restoration is exact, and the app never fails silently.

- **S.** We send scripted requests through our app, with prompts and attached files that hold 100 planted values, each with an ID. In test runs only, we capture everything that leaves the device, the request to our backend and the events sent to Sentry, and the payload that the backend sends to the LLM. The planted values are fake. In the same run, we record the detector's spans, and we trace each gold occurrence and each detected span into these captures by source position. A planted value that the detector found only partly, or not at all, is a detector miss: it belongs to O1, and we report it here too. A detected value found in any of the captures is an app leak.
- **M.** The app adds 0 leaks. Every repeated occurrence is checked, and each leaked ID counts once. We report the detected denominator and all leaks, detector misses included, for the student and for GLiNER2-PII. On normal test responses, 100 % of the intact placeholders must be restored exactly on screen, to the stored value: the detected text with its spaces normalized. This includes the same entity repeated in the prompt and the files, distinct entities, and text that already looks like a replacement. In separate failure tests, we inject bad replacements into the response, from a list of corruptions written in advance. Every one must be flagged to the user and never shown as a real value. If the LLM swaps one valid placeholder for another valid one, for example `<PERSON_2>` instead of `<PERSON_1>`, the app cannot see it. This case is outside the guarantee. Flagging does not count as a successful restoration. If the engine fails (model missing, file text that cannot be extracted, error, timeout), the request is not sent and the user is told. We inject such failures on purpose, and 0 requests may reach the backend unpseudonymized. Aliases of one person, such as "Mme Dupont" and "Marie", are out of scope.
- **A.** These are software checks on a fixed set of 100 planted values. A found value is masked or it is not, and a placeholder is restored exactly or it is not. We own the app and the backend, so we can capture what leaves the device and what the backend sends. The existing tests already cover masking, repeated values and restoration (`tests/test_engine.py`, `tests/test_app.py`). The path to the cloud still needs tests.
- **R.** O1 counts the detector's misses. O4 finds what the app itself adds, for example text lost in file extraction, masking, restoration and failures.
- **T.** We evaluate it at the final talk, in week 14 of the course plan (mid-December 2026).

### O5 MLOps pipeline, cloud deployment and monitoring

The kickoff requires three things: model training or fine-tuning, deployment in the cloud, and monitoring. On 2026-10-19 the teachers confirmed that on-device inference is enough, as long as the training pipeline runs in the cloud. We meet all three:

- A cloud pipeline trains and evaluates the students, and it publishes only those that pass the gates.
- The app deploys them on the device.
- We monitor them without collecting content.

- **S.** A merge to main runs the tests. The full training run on Agent Platform starts by hand, or when the training code, the data or `params.yaml` change. A model is published to the MLflow model registry, with a version, only if it meets the gate thresholds on T2-dev. The 20 test prompts of O2 are measured separately, not in the gate. MLflow also tracks each run, and each model records its code, data and config versions. The backend runs in the cloud. On-device inference stays the main mode: the app gets the latest approved version through the backend and shows which version it uses. Sentry monitors response times and errors in the app and the backend, without any prompt or response content. Development gates use T2-dev. The demonstration thresholds and the release thresholds are two separate, versioned configurations: an approval in the demonstration does not release a model to users.
- **M.** The 0 is a count. Every model version the app installs must have a passing gate record in MLflow for the same file hash. We count the installed versions without one, over the whole project: the target is 0. The final student does not exist on 7 December: v2 and v3 come around 10 December. So the demonstration uses demonstration thresholds, written in `params.yaml` before the demonstration. On 7 December, five scenarios must all pass:
  1. A degraded model fails the frozen recall threshold, and its recall on T2-dev is at least 3 points below the good model's (for example an earlier checkpoint).
  2. A model without evaluation results is refused.
  3. A good model is published, and the app installs it and shows its version.
  4. When a download fails, the app keeps its last approved version.
  5. An injected slowdown fires the alert.

  Sentry records the on-device pseudonymization time separately from the full response time. The alert fires when the p95 of the pseudonymization time over a fixed window exceeds a threshold. The window and the threshold are also written in `params.yaml` before the demonstration. Two items are optional and not in the 7 December checklist: user feedback sent to monitoring, and a smoke run of the pipeline on every merge. The final student is accepted after v3, against the frozen thresholds of O1 to O3.
- **A.** Cloud training already works (2026-11-09, see [cloud-training.md](cloud-training.md)). The gate reuses the O1 to O3 evaluation scripts. The extra refusal cases use the same path and need no extra training.
- **R.** Quality gates are how we stop a compressed model that leaks from reaching users.
- **T.** By 2026-12-07, 22 days after 2026-11-15. The gate and the monitoring must work before the final student arrives.

## Thresholds

The rules are frozen at the seminar talk. Some numbers depend on T2, which does not exist yet. A fixed rule gives them later: on T2-dev before any tuning for the development gate, on T2-final for the final checks, or in `params.yaml` before the demonstration. Every pass or fail decision uses the unrounded counts, never rounded percentages.

| Goal | Fixed today | Recorded later by a fixed rule |
|---|---|---|
| O1 | Models alone: recall at least 95 % of the fine-tuned teacher's, on T1 and on T2-final, and never below GLiNER2-PII as published (80.6 % on T1). Regex and model together: Swiss IDs at least 99 % on T2-final, pooled, with each type's counts | Nothing |
| O2 | Utility through the app at least 90 % (paired) on 20 frozen test prompts, at least 18 of them solved without pseudonymization. Each prompt runs 3 times per condition, solved when 2 of 3 pass, with a pinned LLM endpoint and model version. 5 stress prompts reported apart | Character precision: GLiNER2-PII's on T2-final; for the gate, on T2-dev before tuning |
| O3 | At least 8 times smaller in exact bytes (at most about 155.6 MB), at least 1.5 times faster (p95 at most two thirds of the teacher's), at least 4 curve points | The 30-text latency sample, drawn from T2-dev with a fixed seed before any timing |
| O4 | 0 leaks added by the app, in everything that leaves the device and in the backend's payload to the LLM. 100 % exact restoration, every listed corruption flagged, 0 silent failures | Nothing |
| O5 | 0 installed model versions without a passing gate record in MLflow. By 2026-12-07, five scenarios: a degraded model (at least 3 recall points lower) and a model without results refused, a good one published and installed, the last approved version kept when a download fails, one alert | Demonstration thresholds, alert window and alert threshold, in `params.yaml` before the demonstration |
| Data | Decided: OpenPII-1M plus Gretel, 50,000 training rows. T1 = a fixed 1,000-text sample of the OpenPII-1M validation split | T2's annotation policy, groups, mix of types and formats, and file hashes, frozen by v1 (30 November) |

## Milestones

| Version | Content | Date |
|---|---|---|
| v0 | Baselines measured (regex, Presidio, GLiNER2-PII, OpenAI Privacy Filter) | Done on 2026-11-09 and 10, before the seminar talk on 2026-11-16 |
| v1 | Fine-tuned teacher; T2 built, frozen and split; the 20 test prompts of O2 frozen | 2026-11-30 |
| v2 | Distilled student and the gold-label control | Around 2026-12-10 |
| v3 | Quantized student | Around 2026-12-10 |
| Final | Final talk with the quantitative analysis, then the report (8 pages at most) | Week 14 of the course plan, mid-December 2026 |

## Minimum deliverable and options

The minimum deliverable is the baselines, the fine-tuned teacher, the vocabulary pruned to our four languages, the distilled student in int8, the app with its backend, the CI gate and the monitoring. The options are int4 embeddings, dropping rare tokens and the out-of-distribution sets of O1, which we add if time allows. If v3 is late, we present the iterations we finished and mark the targets we did not meet. Our stretch goals go beyond O3: 12 times smaller and 2 times faster than the teacher. They are not commitments. Owners and effort live on our kanban and Gantt chart.

## Known limits

- The training data is synthetic. So scores on T1 will be optimistic, and real performance will be lower.
- O1's 95 % is relative to the teacher: a teacher at 90 % allows a student at 85.5 %. So we also report the absolute recall.
- It only protects requests sent through our app. We assume that users send their LLM requests only through it.
- The model handles text only: the text extracted from the files. So scanned PDFs and images are not covered.
- If the LLM swaps one valid placeholder for another valid one, for example `<PERSON_2>` instead of `<PERSON_1>`, the app cannot see it. This case is outside the guarantee of O4.
- The exact day of the final talk, in week 14, is not confirmed yet.
