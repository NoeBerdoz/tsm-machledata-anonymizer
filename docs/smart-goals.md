# SMART goals: a small on-device PII pseudonymizer for cloud LLMs

Draft of 2026-10-20, updated on 2026-11-09 for the app design and on 2026-11-15 to make the goals realisable. The rules are frozen at the seminar talk on 2026-11-16. The numbers that depend on T2-dev are recorded on T2-dev before any tuning.

## The project

People send prompts and documents to cloud LLMs, and these texts often hold personal data. In our app, the user writes a prompt and can attach files (PDF, TXT, DOCX, CSV).

We build a small model that runs on the user's laptop. Together with regex rules, it detects sensitive entities in the prompt and in the text of the files. The app replaces them with consistent replacements before anything is sent, and it keeps the mapping table on the device. Only the pseudonymized text goes to our backend, which calls the OpenAI Responses API. When the response comes back, the app restores the real values on the device. So the user sees a normal answer, and neither our backend nor OpenAI sees the real values that the engine detects (see [architecture.md](architecture.md)).

The mapping table lets us put the real values back. So we call it pseudonymization, not anonymization: the data can still be linked to a person with extra information, here the mapping table kept on the device. The GDPR draws the same line between the two (Art. 4(5) and Recital 26).

Our advanced topic is model optimization. We fine-tune a teacher, distill it into a small student, quantize the student, and measure what each step costs in protection.

PrivAiTe and HaS (Hide and Seek, 2023) already show that such a pseudonymizer can exist. Our question is: how small and fast can the detector be, while the leak stays low and the answers stay useful? We look at French, German and Italian, Swiss identifiers, and prompts and attached files.

## Models and test sets

The teacher is `fastino/gliner2-privacy-filter-PII-multi` (GLiNER2-PII). We fine-tune it on our training set. The fine-tuning is mainly for the entities it misses: as published, it misses about 1 entity in 5 on T1 (80.7 % recall), and some types are weak (ages 5 %, titles 15 %, social security numbers 67 %). The regex already finds most Swiss numbers. Swiss identifiers stay in the fine-tuning data as a second net, for the formats the regex does not know. For example, the regex finds 0 of 12 AVS numbers written with dashes, and GLiNER2-PII finds 8 of 12.

The training data and T1 are decided (see [test-set-decision.md](test-set-decision.md)). We train on ai4privacy OpenPII-1M plus Gretel.

The training budget is a fixed, seeded subset of 50,000 rows in total, from both sources. The teacher, the student and the control student all train on it. Two epochs for each of the three models, plus one pass to compute the teacher's soft labels, take about 5.4 hours of T4 GPU, about USD 3.40. This estimate uses the 18 rows per second of our smoke run and USD 0.62 per hour, without startup, evaluation and retries (see [cloud-training.md](cloud-training.md)). All of OpenPII-1M and Gretel would cost about USD 80, more than our USD 50 of credits.

We measured the published model from its safetensors header. It has 307M parameters in float32 (1.23 GB). 192M of them (63 %) are the word embeddings of its 250,112-token multilingual vocabulary.

Regular expressions handle the structured identifiers. These rules are the same in every comparison.

- **T1** is the validation split of OpenPII-1M, in French, German, Italian and English, which we never use for training.
- **T2** is our own set of about 200 snippets of what users send through our app: prompts, e-mails, documents, tables (CSV), pasted code or logs. For an attached file, the snippet is the text extracted from it, because that is what the detector receives. The snippets are stored in one JSONL file with character offsets (format in issue #5). We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes). So we know the labels by construction. We also annotate any incidental sensitive entity that a snippet already contains. Before any tuning, we split T2 into two parts: a dev part, used for thresholds and the CI gates, and a frozen final-test part. Related snippets stay on the same side. We record the file hashes, and we run the final test only on the selected models.

Both sets carry gold character offsets (the exact position of each true entity). **An entity counts as protected only if every character except spaces is masked.** So a partly masked IBAN is a leak.

- **Recall** is the micro-average of this rule over the gold entities. We also report it per entity type. It is the primary metric, because one minus recall is the leak rate.
- **Character precision** is the share of masked characters that belong to a gold entity. It shows over-masking: a model that masks everything fails it.

## The goals

### O1 Protection

The quantized student keeps at least 95 % of the fine-tuned teacher's recall on T1 and on T2-final, and it reaches at least 99 % recall on Swiss structured identifiers.

- **S.** We compare the delivered student (v3, distilled and quantized) with the fine-tuned teacher (v1) on T1 and on T2-final, each set separately. The Swiss structured identifiers are AVS numbers, IBANs and phone numbers, caught by the regex and the model together. We also report, with no threshold: the student's absolute recall, overall and per type; GLiNER2-PII as published; and a control student. The control has the same architecture, data and budget, but it learns from the gold labels only (alpha = 0). It answers the question "does distillation help?", whatever the answer is. We also report recall and character precision on out-of-distribution sets: SPY, TAB, GraSCCo_PHI and BigCode PII (see [datasets.md](datasets.md) for their licences; BigCode PII is gated and is never redistributed).
- **M.** Student recall divided by teacher recall must be at least 0.95 on each test set. The three Swiss types together must reach at least 99 % recall.
- **A.** Compression always costs some recall. We accept a loss of at most 5 % of the teacher's recall for a model 8 times smaller. With half the layers, DistilBERT kept 97 % of BERT's score (Sanh et al., 2019). On our Swiss test set, the regex plus GLiNER2-PII already protect 775 of 781 values (99.2 %), so the goal checks that compression does not break this. Fine-tuning works on our cloud GPU: on 2026-11-09, 2 minutes of training on 900 rows raised recall on 13 of the 19 types from 76.5 % to 95.4 % on 100 test rows. These rows come from the same dataset, so this is optimistic.
- **R.** This goal measures what compression costs in protection, which is the core of our advanced topic.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O2 Utility

The pseudonymization does not mask so much that the answers get worse.

- **S.** We measure the student's character precision on T2-final. We also run 20 scripted utility tasks through our app (engine, backend, OpenAI, restoration), once with pseudonymization and once without, with the same OpenAI model and settings. Each task has an oracle fixed in advance, for example an exact value, expected fields in a JSON answer, or a label. The replacement is a placeholder such as `<PERSON_1>` (issue #17), so the gap between the two runs also shows what placeholders cost.
- **M.** Utility is the number of tasks solved in both conditions divided by the number solved without pseudonymization. It must be at least 90 %. If all 20 tasks pass without pseudonymization, that means 18 of 20. Otherwise we use the real denominator and report both counts. The character precision on T2-final must be at least GLiNER2-PII's on T2-dev. The rule is frozen at the talk, and the number is recorded on T2-dev before any tuning.
- **A.** The 20 tasks are small enough to run on every model version. 90 % means that at most 2 of 20 solved tasks may break.
- **R.** O1 alone can be met by masking everything, so O2 checks that the answers stay useful. The precision floor limits how much is masked by mistake. O1 and O2 pull in opposite directions, and the central result of the talk is where each compressed model sits between them.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O3 Compression

The delivered student is at least 8 times smaller and at least 1.5 times faster than the fp32 teacher on a laptop CPU.

- **S.** Size counts all files needed to run the model, weights and tokenizer. We measure the p95 latency of every model on the reference laptop CPU, an Intel Core i5-1130G7, with the frozen protocol of [benchmark-protocol.md](benchmark-protocol.md): 30 texts, 10 runs each, so 300 calls per model. We measure the teacher on the same laptop.
- **M.** The teacher measures 1,244 MB, so the student must weigh at most 155.5 MB (1,244 / 8). The student's p95 latency must be at most two thirds of the teacher's p95, which means at least 1.5 times faster. We publish a compression curve with one point per step, at least 4, each with its recall, size and latency: the fp32 teacher, the teacher with the pruned vocabulary, the same in int8, and the distilled student in int8 with the pruned vocabulary. The options add 2 more points: int4 embeddings, and rare tokens dropped.
- **A.** Our estimate for the minimum deliverable (6 layers, our four languages' tokens, int8) is about 137 MB, 9.1 times smaller, so we have about 19 MB of margin ([baselines.md](baselines.md)). The word embeddings are 63 % of the teacher, and our four languages use 77,347 of its 250,112 tokens. The int8 step must also quantize the word embeddings: the default dynamic quantization of PyTorch leaves them in float32. With the pruned vocabulary, the student is then only about 4 times smaller instead of 9 (1,244 / (237.6 + 42.7 + 29.5 + 4.9) = 3.95). The student has half the teacher's layers. With half the layers, DistilBERT ran 1.63 times faster (Sanh et al., 2019: 668 s against 410 s). Int8 on a laptop CPU usually adds more speed, but we have not measured it on our model. So 1.5 times leaves a margin. We do not ask for more, because there is no measurement on the reference laptop yet, and the smaller dictionary saves space, not time: a lookup costs almost nothing. The first measurement on the reference laptop comes with the latency sample from T2-dev.
- **R.** The model runs before every request, on the user's laptop, and attached files can be long, so its speed matters to the user. Also, the model has to run where the data is allowed to be. Each curve point shows what one step costs in recall, size and latency, which is our advanced topic.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O4 End-to-end protection in our app

In scripted requests through our app, the app adds no leak, restoration is exact, and the app never fails silently.

- **S.** We send scripted requests through our app, with prompts and attached files that hold 100 planted values, each with an ID. In test runs only, we capture the payload that the backend sends to OpenAI. The planted values are fake. In the same run, we record the detector's spans, and we trace each gold occurrence and each detected span into the payload by source position. A planted value that the detector found only partly, or not at all, is a detector miss: it belongs to O1, and we report it here too. A detected span that is not fully masked in the payload is an app error.
- **M.** The app adds 0 leaks. Every repeated occurrence is checked, and each leaked ID counts once. We report the detected denominator and all leaks, detector misses included, for the student and for GLiNER2-PII. On normal test responses, 100 % of the intact placeholders must be restored exactly to the real value on screen. This includes the same entity repeated in the prompt and the files, distinct entities, and text that already looks like a replacement. In separate failure tests, we inject bad replacements into the response, from a list of corruptions written in advance. Every one must be flagged to the user and never shown as a real value. Flagging does not count as a successful restoration. If the engine fails (model missing, file text that cannot be extracted, error, timeout), the request is not sent and the user is told. We inject such failures on purpose, and 0 requests may reach the backend unpseudonymized. Aliases of one person, such as "Mme Dupont" and "Marie", are out of scope.
- **A.** These are software checks on a fixed set of 100 planted values. A found value is masked or it is not, and a placeholder is restored exactly or it is not. We own the app and the backend, so we can capture the outgoing payload. The existing tests already cover masking, repeated values and restoration (`tests/test_engine.py`, `tests/test_app.py`). The path to the cloud still needs tests.
- **R.** O1 counts the detector's misses. O4 finds what the app itself adds, for example text lost in file extraction, masking, restoration and failures.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O5 MLOps pipeline, cloud deployment and monitoring

The kickoff requires three things: model training or fine-tuning, deployment in the cloud, and monitoring. On 2026-10-19 the teachers confirmed that on-device inference is enough, as long as the training pipeline runs in the cloud. We meet all three:

- A cloud pipeline trains and evaluates the students, and it publishes only those that pass the gates.
- The app deploys them on the device.
- We monitor them without collecting content.

- **S.** A merge to main runs the tests and a small smoke run of the pipeline. The full training run on Agent Platform starts by hand, or when the training code, the data or `params.yaml` change. A model is published to the MLflow model registry, with a version, only if it meets the gate thresholds on T2-dev. The 20 app tasks of O2 are measured separately, not in the gate. MLflow also tracks each run, and each model records its code, data and config versions. The backend runs in the cloud. On-device inference stays the main mode: the app gets the latest approved version through the backend and shows which version it uses. Sentry monitors response times and errors in the app and the backend, without any prompt or response content. User feedback from the interface also goes to monitoring.
- **M.** The final student does not exist on 7 December: v2 and v3 come around 10 December. So the demonstration uses demonstration thresholds, written in `params.yaml` before the demonstration. It shows a degraded model refused and a good model published, which the app then installs and whose version it reports. Sentry records the on-device pseudonymization time separately from the full response time. The alert fires when the p95 of the pseudonymization time over a fixed window exceeds a threshold. The window and the threshold are also written in `params.yaml` before the demonstration. We trigger the alert on purpose. The final student is accepted after v3, against the frozen thresholds of O1 to O3.
- **A.** Cloud training already works (2026-11-09, see [cloud-training.md](cloud-training.md)). The gate reuses the O1 to O3 evaluation scripts.
- **R.** Quality gates are how we stop a compressed model that leaks from reaching users.
- **T.** By 2026-12-07, 22 days after 2026-11-15. The gate and the monitoring must work before the final student arrives.

## Thresholds

The rules are frozen at the seminar talk. Some numbers depend on T2-dev, which does not exist yet. A fixed rule gives them later: we record them on T2-dev before any tuning, or in `params.yaml` before the demonstration.

| Goal | Fixed today | Recorded later by a fixed rule |
|---|---|---|
| O1 | Recall at least 95 % of the fine-tuned teacher's, on T1 and on T2-final; Swiss IDs at least 99 % | Nothing |
| O2 | Utility through the app at least 90 % (paired) | Character precision: GLiNER2-PII's on T2-dev, before tuning |
| O3 | At least 8 times smaller (at most 155.5 MB), at least 1.5 times faster (p95 at most two thirds of the teacher's), at least 4 curve points | The 30-text latency sample from T2-dev |
| O4 | 0 leaks added by the app, 100 % exact restoration, every listed corruption flagged, 0 silent failures | Nothing |
| O5 | Refusal and publication demo in MLflow, app installs it, one alert, by 2026-12-07 | Demonstration thresholds, alert window and alert threshold, in `params.yaml` before the demonstration |
| Data | Decided: OpenPII-1M plus Gretel, T1 = OpenPII-1M validation, 50,000 training rows | Nothing |

## Milestones

| Version | Content | Date |
|---|---|---|
| v0 | Baselines measured (regex, Presidio, GLiNER2-PII, OpenAI Privacy Filter), T2 built and split | Before the seminar talk on 2026-11-16 |
| v1 | Fine-tuned teacher | End of November 2026 |
| v2 | Distilled student and the gold-label control | Around 2026-12-10 |
| v3 | Quantized student | Around 2026-12-10 |
| Final | Final talk with the quantitative analysis, then the report (8 pages at most) | Around mid-December 2026, to confirm |

## Minimum deliverable and options

The minimum deliverable is the baselines, the fine-tuned teacher, the vocabulary pruned to our four languages, the distilled student in int8, the app with its backend, the CI gate and the monitoring. The options are int4 embeddings and dropping rare tokens, which we add if time allows. Our stretch goals go beyond O3: 12 times smaller and 2 times faster than the teacher. They are not commitments. Owners and effort live on our kanban and Gantt chart.

## Known limits

- The training data is synthetic. So scores on T1 will be optimistic, and real performance will be lower.
- O1's 95 % is relative to the teacher: a teacher at 90 % allows a student at 85.5 %. So we also report the absolute recall.
- It only protects requests sent through our app. We assume that users send their LLM requests only through it.
- The model handles text only: the text extracted from the files. So scanned PDFs and images are not covered.
- The date of the final talk is not confirmed yet.
