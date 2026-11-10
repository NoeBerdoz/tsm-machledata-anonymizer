# SMART goals: a small on-device PII pseudonymizer for cloud LLMs

Draft of 2026-10-20, updated on 2026-11-09 for the app design. The seminar talk is on 2026-11-16, and every threshold is frozen there.

## The project

People send prompts and documents to cloud LLMs, and these texts often hold personal data. In our app, the user writes a prompt and can attach files (PDF, TXT, DOCX, CSV).

We build a small model that runs on the user's laptop. Together with regex rules, it detects sensitive entities in the prompt and in the text of the files. The app replaces them with consistent replacements before anything is sent, and it keeps the mapping table on the device. Only the pseudonymized text goes to our backend, which calls the OpenAI Responses API. When the response comes back, the app restores the real values on the device. So the user sees a normal answer, and neither our backend nor OpenAI sees the real values (see [architecture.md](architecture.md)).

The mapping table lets us put the real values back. So we call it pseudonymization, not anonymization: the data can still be linked to a person with extra information, here the mapping table kept on the device. The GDPR draws the same line between the two (Art. 4(5) and Recital 26).

Our advanced topic is model optimization. We fine-tune a teacher, distill it into a small student, quantize the student, and measure what each step costs in protection.

PrivAiTe and HaS (Hide and Seek, 2023) already show that such a pseudonymizer can exist. Our question is: how small and fast can the detector be, while the leak stays low and the answers stay useful? We look at French, German and Italian, Swiss identifiers, and prompts and attached files.

## Models and test sets

The teacher is `fastino/gliner2-privacy-filter-PII-multi` (GLiNER2-PII). We fine-tune it on Swiss identifiers and on one of two candidate training sets, chosen at v0 (see [datasets.md](datasets.md)): ai4privacy OpenPII-1M plus Gretel, or the French, German and Italian rows of ai4privacy/open-pii-masking-500k.

We measured the published model from its safetensors header. It has 307M parameters in float32 (1.23 GB). 192M of them (63 %) are the word embeddings of its 250,112-token multilingual vocabulary.

Regular expressions handle the structured identifiers. These rules are the same in every comparison.

- **T1** is the validation split of the ai4privacy dataset chosen at v0 (OpenPII-1M or open-pii-masking-500k, see [datasets.md](datasets.md)), in French, German, Italian and English, which we never use for training.
- **T2** is our own set of about 200 snippets of what users send through our app: prompts, e-mails, documents, tables (CSV), pasted code or logs. For an attached file, the snippet is the text extracted from it, because that is what the detector receives. The snippets are stored in one JSONL file with character offsets (format in issue #5). We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes). So we know the labels by construction. We also annotate any incidental sensitive entity that a snippet already contains. Before any tuning, we split T2 into two parts: a dev part, used for thresholds and the CI gates, and a frozen final-test part. Related snippets stay on the same side. We record the file hashes, and we run the final test only on the selected models.

Both sets carry gold character offsets (the exact position of each true entity). **An entity counts as protected only if all its characters are masked.** So a partly masked IBAN is a leak.

- **Recall** is the micro-average of this rule over the gold entities. We also report it per entity type. It is the primary metric, because one minus recall is the leak rate.
- **Character precision** is the share of masked characters that belong to a gold entity. It shows over-masking: a model that masks everything fails it.

## The goals

### O1 Protection

The quantized student keeps at least 95 % of the fine-tuned teacher's recall on T1 and on T2-final, and it reaches at least 99 % recall on Swiss structured identifiers.

- **S.** We compare the delivered student (v3, quantized) with the fine-tuned teacher (v1) on T1 and T2-final separately. We also train a control student with the same architecture, the same gold data and the same training budget as the distilled student, but trained directly on the gold labels (if we take open-pii-masking-500k, its train split has 464k labelled rows; if we take OpenPII-1M, 1.14M, and we then fix the budget at v0). Distillation earns its place only if it beats this control. We report structured identifiers and free-text entities separately. We also report, with no threshold, the recall and character precision of the teacher and the student on out-of-distribution benchmarks: SPY, TAB, GraSCCo_PHI and BigCode PII (see [datasets.md](datasets.md) for their licences; BigCode PII is gated and is never redistributed).
- **M.** The ratio student recall ÷ teacher recall must be at least 0.95 on each test set, and Swiss structured identifiers, caught by the regular expressions and the model together, must reach 99 %. The per-type floor is **decided at v0**: no type may fall below the recall that the best v0 baseline reaches on that type on T2-dev. The student must also beat GLiNER2-PII as published, which means a higher micro recall on T2-final at equal or better character precision.
- **A.** We do not train a teacher from scratch. GLiNER2-PII is already multilingual, Apache 2.0, and covers 42 types, including `national_id_number`, `iban` and `api_key`.
- **R.** This goal measures what compression costs in protection, which is the core of our advanced topic.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O2 Utility

The pseudonymization does not mask so much that the answers get worse.

- **S.** We measure the student's character precision on T2-final. We also run 20 scripted utility tasks through our app (engine, backend, OpenAI, restoration), once with pseudonymization and once without, with the same OpenAI model and settings. Each task has an oracle fixed in advance, for example an exact value, expected fields in a JSON answer, or a label. The replacement is a placeholder such as `<PERSON_1>` (issue #17), so the gap between the two runs also shows what placeholders cost.
- **M.** The precision threshold is **decided at v0**: it is the character precision GLiNER2-PII reaches on T2-dev. Utility is the number of tasks solved in both conditions divided by the number solved without pseudonymization, and it must be at least 90 %.
- **A.** The 20 tasks are small enough to run on every model version.
- **R.** O1 and O2 pull in opposite directions. The central result of the talk is where each compressed model sits between these two goals.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O3 Compression

The delivered student is at least 12 times smaller than the fp32 teacher and at least four times faster on a laptop CPU.

- **S.** Size counts all files needed to run the model, weights and tokenizer. We measure latency on one reference laptop CPU that we name at v0, with a benchmark protocol frozen at v0: the same texts, length counted in words of the input, fixed runtime and thread settings, a warm-up, and a fixed number of runs.
- **M.** The size target is a ratio of the measured 1.23 GB: at least 12× smaller, which is about 100 MB. That 100 MB is an estimate from parameter counts, not a measurement. We estimate about 150 MB for the pruned vocabulary with int8, 100 MB for a six-layer distilled student with int8 and 55 MB for int4, and we record the real size of each artifact when we produce it. The student's p95 latency must be at most a quarter of the fp32 teacher's. We publish a compression curve with at least three points (fp32, int8, distilled int8), and five when the options are done (pruned vocabulary, int4), each with its recall, size and latency.
- **A.** The embeddings are 63 % of the teacher, so pruning the vocabulary to our languages removes a large share of the weights before any distillation.
- **R.** The model runs before every request, on the user's laptop, and attached files can be long. Also, the model has to run where the data is allowed to be.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O4 End-to-end protection in our app

In scripted requests through our app, almost no planted value reaches OpenAI, restoration is exact, and the app never fails silently.

- **S.** We send scripted requests through our app, with prompts and attached files that hold 100 planted values, each with an ID. We measure leaks on what the backend sends to OpenAI. In test runs only, we capture this outgoing payload for measurement. The planted values are fake.
- **M.** A planted value counts as leaked if any of its characters reaches OpenAI unmasked, as in O1. We count each planted ID once. The leak budget is **decided at v0**: half the distinct values that leak with GLiNER2-PII in the same requests, rounded down. On normal test responses, 100 % of the replacements must be restored exactly to the real value on screen. This includes the same entity repeated in the prompt and the files, distinct entities, and text that already looks like a replacement. The app must never fail silently. If the engine fails (model missing, file text that cannot be extracted, error, timeout), the request is not sent and the user is told. We inject such failures on purpose, and zero requests may reach the backend unpseudonymized. In separate failure tests, we inject unknown and altered replacements into the response. Every one must be flagged to the user and never shown as a real value. Flagging does not count as a successful restoration. Aliases of one person, such as "Mme Dupont" and "Marie", are out of scope.
- **A.** We own the app and the backend, so we can capture the outgoing payload.
- **R.** This goal tests the use case end to end, including leaks that a detector score cannot show, for example text lost in file extraction.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O5 MLOps pipeline, cloud deployment and monitoring

The kickoff requires three things: model training or fine-tuning, deployment in the cloud, and monitoring. On 2026-10-19 the teachers confirmed that on-device inference is enough, as long as the training pipeline runs in the cloud. We meet all three:

- A cloud pipeline trains and evaluates the students, and it publishes only those that pass the gates.
- The app deploys them on the device.
- We monitor them without collecting content.

- **S.** A merge to main runs the tests and a small smoke run of the pipeline. The full training run on Agent Platform starts by hand, or when the training code, the data or `params.yaml` change. A model is published to the MLflow model registry, with a version, only if it meets on T2-dev the O1 detection thresholds, the O2 character-precision threshold and the O3 size and latency thresholds. The 20 app tasks of O2 are measured separately, not in the gate. MLflow also tracks each run, and each model records its code, data and config versions. The backend runs in the cloud. On-device inference stays the main mode: the app gets the latest approved version through the backend and shows which version it uses. Sentry monitors response times and errors in the app and the backend, without any prompt or response content. User feedback from the interface also goes to monitoring.
- **M.** The demonstration shows a degraded model refused and a good model published, which the app then installs and whose version it reports. Sentry records the on-device pseudonymization time separately from the full response time. The alert fires when the p95 of the pseudonymization time over a fixed window exceeds a threshold. The window and the threshold are decided at v0. We trigger the alert on purpose.
- **A.** The gates reuse the O1 to O3 evaluation scripts.
- **R.** Quality gates are how we stop a compressed model that leaks from reaching users.
- **T.** By 2026-12-07, the pipeline, the gate and the monitoring work with the best model available then. The final model is accepted after v3.

## Thresholds

The rules below are computed on T2-dev at v0, their outcome replaces any draft value, and all thresholds are frozen at the seminar talk.

| Goal | Fixed today | Decided at v0, with its rule |
|---|---|---|
| O1 | Recall ≥ 95 % of teacher's, Swiss IDs ≥ 99 %, beats GLiNER2-PII | Per-type floor: best baseline's recall per type |
| O2 | Utility through the app ≥ 90 % (paired) | Character precision: GLiNER2-PII's on T2-dev |
| O3 | ≥ 12× smaller, p95 ≤ ¼ of teacher, ≥ 3 curve points (5 with the options) | Reference CPU and benchmark protocol |
| O4 | 100 % exact restoration, 100 % of injected bad replacements flagged, 0 silent failures | Leak budget: half of GLiNER2-PII's leaks, rounded down |
| O5 | Refusal and publication demo in MLflow, app installs it, one alert, 2026-12-07 | Alert window and threshold on the pseudonymization time |
| Data | Nothing | Teacher training data and T1: OpenPII-1M plus Gretel, or open-pii-masking-500k FR/DE/IT (trade-offs in [datasets.md](datasets.md)) |

## Milestones

| Version | Content | Date |
|---|---|---|
| v0 | Baselines measured (regex, Presidio, GLiNER2-PII, OpenAI Privacy Filter), T2 built and split | Before the seminar talk on 2026-11-16 |
| v1 | Fine-tuned teacher | End of November 2026 |
| v2 | Distilled student and the gold-label control | Around 2026-12-10 |
| v3 | Quantized student | Around 2026-12-10 |
| Final | Final talk with the quantitative analysis, then the report (8 pages at most) | Around mid-December 2026, to confirm |

## Minimum deliverable and options

The minimum deliverable is the baselines, the fine-tuned teacher, the distilled student in int8, the app with its backend, the CI gate and the monitoring. Vocabulary pruning and int4 are options that we add if time allows. Owners and effort live on our kanban and Gantt chart.

## Known limits

- The training data is synthetic. So scores on T1 will be optimistic, and real performance will be lower.
- It only protects requests sent through our app. We assume that users send their LLM requests only through it.
- The model handles text only: the text extracted from the files. So scanned PDFs and images are not covered.
- The date of the final talk is not confirmed yet.
