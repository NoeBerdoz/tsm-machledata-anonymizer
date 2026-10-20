# SMART goals: a small on-device anonymizer for AI coding agents

Draft of 2026-10-20. The seminar talk is on 2026-11-16, and every threshold is frozen there.

## The project

A cloud AI agent such as Claude Code reads our files and command outputs, and it sends them to the provider, personal data included. The PrivAiTe README reports that Claude Code, run directly, sent 24 out of 24 planted values to the provider.

We build a small model that runs on the developer's machine. It detects sensitive entities in tool outputs and replaces them with consistent placeholders before the outputs are sent. When the agent calls a tool or answers, we restore the placeholders. So local tools receive the real values, and the developer sees a normal answer.

Our advanced topic is model optimization. We fine-tune a teacher, distill it into a small student, quantize the student, and measure what each step costs in protection.

PrivAiTe and HaS (Hide and Seek, 2023) already show that such an anonymizer can exist. Our question is: how small and fast can the detector be, while the leak stays low and the agent still works? We look at French, German and Italian, Swiss identifiers, and agent tool outputs.

## Models and test sets

The teacher is `fastino/gliner2-privacy-filter-PII-multi` (GLiNER2-PII). We fine-tune it on Swiss identifiers and on one of two candidate training sets, chosen at v0 (see [datasets.md](datasets.md)): ai4privacy OpenPII-1M plus Gretel, or the French, German and Italian rows of ai4privacy/open-pii-masking-500k.

We measured the published model from its safetensors header. It has 307M parameters in float32 (1.23 GB). 192M of them (63 %) are the word embeddings of its 250,112-token multilingual vocabulary.

Regular expressions handle the structured identifiers. These rules are the same in every comparison.

- **T1** is the validation split of the ai4privacy dataset chosen at v0 (OpenPII-1M or open-pii-masking-500k, see [datasets.md](datasets.md)), in French, German, Italian and English, which we never use for training.
- **T2** is our own agent set of about 200 snippets: code, logs, JSON, CSV, e-mails and command outputs. We plant values in them, including Swiss identifiers (AVS numbers starting with 756, Swiss IBANs, +41 phone numbers, postal codes). So we know the labels by construction. We also annotate any incidental sensitive entity that a snippet already contains. Before any tuning, we split T2 into two parts: a dev part, used for thresholds and the CI gates, and a frozen final-test part. Related snippets stay on the same side. We record the file hashes, and we run the final test only on the selected models.

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

The anonymizer does not mask so much that the agent stops working.

- **S.** We measure the student's character precision on T2-final. We also run 20 scripted Claude Code tasks, once with the anonymizer and once without, with the same agent model, environment and run limits. Each task has an oracle fixed in advance: tests pass, an expected file change, or an exact value.
- **M.** The precision threshold is **decided at v0**: it is the character precision GLiNER2-PII reaches on T2-dev. Agent utility is the number of tasks solved in both conditions divided by the number solved without the anonymizer, and it must be at least 90 %.
- **A.** The 20 tasks are small enough to run on every model version.
- **R.** O1 and O2 pull in opposite directions. The central result of the talk is where each compressed model sits between these two goals.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O3 Compression

The delivered student is at least 12 times smaller than the fp32 teacher and at least four times faster on a laptop CPU.

- **S.** Size counts all files needed to run the model, weights and tokenizer. We measure latency on one reference laptop CPU that we name at v0, with a benchmark protocol frozen at v0: the same texts, length counted in words of the input, fixed runtime and thread settings, a warm-up, and a fixed number of runs.
- **M.** The size target is a ratio of the measured 1.23 GB: at least 12× smaller, which is about 100 MB. That 100 MB is an estimate from parameter counts, not a measurement. We estimate about 150 MB for the pruned vocabulary with int8, 100 MB for a six-layer distilled student with int8 and 55 MB for int4, and we record the real size of each artifact when we produce it. The student's p95 latency must be at most a quarter of the fp32 teacher's. We publish a compression curve with at least three points (fp32, int8, distilled int8), and five when the options are done (pruned vocabulary, int4), each with its recall, size and latency.
- **A.** The embeddings are 63 % of the teacher, so pruning the vocabulary to our languages removes a large share of the weights before any distillation.
- **R.** The model runs on every turn of the agent, and agent CLIs resend the whole conversation. Also, the model has to run where the data is allowed to be.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O4 Claude Code integration

In scripted agent sessions, almost no planted value reaches the provider, restoration is exact, and the system never fails silently.

- **S.** We run 20 scripted Claude Code sessions over a repository that holds 100 planted values, each with an ID, in files and command outputs. PostToolUse replaces the tool output before Claude sees it, PreToolUse restores real values in tool arguments, and MessageDisplay restores them on screen. A recording proxy captures what reaches the provider, and we use it for measurement only.
- **M.** Only values that the sessions actually expose count, and a leak is a distinct exposed ID found in the decoded provider-bound payload. The leak budget is **decided at v0**: half the distinct values that leak with GLiNER2-PII in the same sessions, rounded down. A silent fallback happens when a replaced output of a built-in tool does not match the output schema, because Claude Code then uses the original. We inject malformed hook outputs on purpose and require zero silent fallbacks in the recording. Every typed prompt with a detected entity must be blocked (100 %). Restoration must be 100 % correct in tool arguments and displayed answers, on round trips with the same entity repeated across files and turns, distinct entities, and text that looks like a placeholder. Aliases of one person, such as "Mme Dupont" and "Marie", are out of scope.
- **A.** We verified each of these hooks on the Claude Code documentation.
- **R.** This goal tests the use case end to end, including leaks that a detector score cannot show.
- **T.** We evaluate it at the final talk, around mid-December 2026.

### O5 MLOps pipeline, cloud deployment and monitoring

The kickoff requires three things: model training or fine-tuning, deployment in the cloud, and monitoring. On 2026-10-19 the teachers confirmed that on-device inference is enough, as long as the training pipeline runs in the cloud. We meet all three:

- A cloud pipeline trains and evaluates the students, and it publishes only those that pass the gates.
- The add-on deploys them on the device.
- We monitor them without collecting content.

- **S.** A CI pipeline on GCP retrains and evaluates on every merge to main, and it publishes a versioned student only if the O1 to O3 gates pass on T2-dev. Each model records its code, data and config versions. On-device inference stays the main mode, and the on-device add-on pulls the published version. Before a release, the CI runs an integration smoke test with the candidate student. Opt-in, content-free telemetry reports latency p50 and p95, entities per type, model version and hook failures.
- **M.** The demonstration shows a degraded model refused and a good model published, which the add-on then installs and whose version it reports. The dashboard has one alert, which fires when p95 latency over a fixed window exceeds the O3 budget, and we trigger it on purpose.
- **A.** The gates reuse the O1 to O3 evaluation scripts.
- **R.** Quality gates are how we stop a compressed model that leaks from reaching users.
- **T.** By 2026-12-07, the pipeline, the gate and the dashboard work with the best model available then. The final model is accepted after v3.

## Thresholds

The rules below are computed on T2-dev at v0, their outcome replaces any draft value, and all thresholds are frozen at the seminar talk.

| Goal | Fixed today | Decided at v0, with its rule |
|---|---|---|
| O1 | Recall ≥ 95 % of teacher's, Swiss IDs ≥ 99 %, beats GLiNER2-PII | Per-type floor: best baseline's recall per type |
| O2 | Utility ≥ 90 % (paired) | Character precision: GLiNER2-PII's on T2-dev |
| O3 | ≥ 12× smaller, p95 ≤ ¼ of teacher, ≥ 3 curve points (5 with the options) | Reference CPU and benchmark protocol |
| O4 | 0 silent fallbacks, 100 % blocking of detected entities in typed prompts, 100 % restoration | Leak budget: half of GLiNER2-PII's leaks, rounded down |
| O5 | Refusal and publication demo, one alert, 2026-12-07 | Nothing |
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

The minimum deliverable is the baselines, the fine-tuned teacher, the distilled student in int8, the hooks integration, the CI gate and the dashboard. Vocabulary pruning, int4, the proxy mode and a Cloud Run gateway are options that we add if time allows. Owners and effort live on our kanban and Gantt chart.

## Known limits

- The training data is synthetic. So scores on T1 will be optimistic, and real performance will be lower.
- Hooks cannot rewrite a typed prompt. UserPromptSubmit can only block it or add context. So hooks do not anonymize typed prompts or CLAUDE.md. Only a proxy between the agent and the provider would cover them.
- The model handles text only.
- The date of the final talk is not confirmed yet.
