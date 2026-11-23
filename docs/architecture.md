# Architecture

This page describes the two parts of the project: the application that pseudonymizes data on the user's device, and the MLOps pipeline that trains, delivers and monitors its model. Many details are still open. This page gives the structure, not the final choices.

The diagrams are in `docs/diagrams/`. The editable version is in Figma: [Schémas – anonymiseur PII](https://www.figma.com/design/EZFkhnWaznd3MO2BQZWDYB).

## Why our own interface and backend

We first planned to plug the anonymizer into Claude Code with hooks. We now build our own application instead: the user writes the prompt in our interface, we detect the personal data, we replace it, and we send the pseudonymized text to an LLM through our backend.
- **Advantage:** we control the whole path, from the prompt to the response. This is much simpler than working around the limits of the hooks of an existing agent.
- **Drawback:** it only protects requests made through our interface. We assume that users send their LLM requests only through our application.

## 1. Main application architecture

![Main application architecture](diagrams/architecture.png)

The idea is simple: the personal data that the engine detects never leaves the user's device. Only pseudonymized content goes to the cloud.

### On the user's device (private zone)

1. **User interface.** The user writes a prompt and can attach files (PDF, TXT, DOCX, CSV). The user can rate each response from 1 to 5 stars. This feedback goes to monitoring (for now to a local file, without any prompt or response text).
2. **Local pseudonymization engine.** The engine finds personal data in the prompt and in the files. It has two parts that work together:
   - **Regex rules** for structured identifiers, which follow a fixed format.
   - **Our ML model** for contextual entities, such as names or addresses, which need context to be found. This is the model we train ourselves: a student distilled from a larger teacher and quantized, produced by the pipeline in part 2.

   The engine first finds the values (`detect()` in `engine.py`), then replaces them. The replacement (step 3) and the model can therefore change separately, and the evaluation script can measure `detect()` like any other detector.
3. **Replacement.** Each value that the engine finds is replaced by a placeholder, such as `<PERSON_1>` or `<IBAN_1>`. The same text of the same type always gets the same placeholder. We chose placeholders over fake values (a fake name such as `Jean Martin` in place of the real one) in issue #17, for three reasons:
   - They work the same way for every type. Fake values would need a generator for each type (names, AVS numbers, IBANs, phone numbers).
   - The restoration is exact. The LLM usually copies `<PERSON_1>` as it is, while it may shorten or change a fake name.
   - A miss stays visible. A placeholder left in an answer is obvious, while a fake name left in an answer looks real.

   The price is that LLMs tend to write better answers from realistic text, and a placeholder does not tell the LLM whether to write "he" or "she". Goal O2 measures this cost, because its 20 test prompts run with and without pseudonymization ([smart-goals.md](smart-goals.md)). Fake values remain a possible continuation of the project, and step 2 already keeps the replacement apart from detection.

   The engine records each pair in a **mapping table** (placeholder ↔ real value), which is kept on the device only. The key of a value is its type and its exact text, spaces and case included, so the restoration writes back exactly what was replaced: `Marie Dupont`, `MARIE DUPONT` and a name broken over two lines get three placeholders. A placeholder that the LLM damages, such as `<PERSON-1>` or `<PERSON 1>`, is not restored but shown as it is, with a warning.
4. **Privacy boundary.** Only the pseudonymized content goes past this point.

### In the cloud

5. **Backend API (FastAPI).** It receives the pseudonymized request and handles authentication and request control.
6. **The LLM.** By default the local Ollama, or a hosted model such as OpenAI or Claude when the backend is set to one (see the table below). It processes the pseudonymized prompt and sends back a response. The response contains the placeholders, not the real values that the engine detected.

### Back on the device

7. **Response restored locally.** The application reads the response, finds each placeholder in it, and looks it up in the mapping table. It then swaps it back to the real value, for example `<PERSON_1>` → `Marie Dupont`, and shows the restored response to the user.

The restoration happens on the device because the mapping table never leaves it. Neither the backend nor the LLM sees the real values that the engine detects.

## 2. Training and deployment pipeline (MLOps)

![Training and deployment pipeline](diagrams/mlops.png)

This pipeline produces the ML model used by the local pseudonymization engine. Training happens in the cloud. The model then runs on the user's device, and its use is monitored.

### Source and automation

1. **GitHub.** It holds the code, the configuration and the small DVC files that point to the data and the models.
2. **GitHub Actions.** It runs the automated tests on every pull request. The training run is expensive (distillation in particular uses a lot of GPU time and credits), so it does not run on every merge: it starts only by hand, or when the code, the data or the parameters of the pipeline change. DVC reruns only the stages whose inputs changed.

### Training on Google Cloud (Agent Platform)

The pipeline runs on Agent Platform, Google Cloud's platform for training and managing models (formerly Vertex AI). It has five steps:

1. **Data preparation.** Collect the training datasets, clean them and format them for training. The pipeline does not create the test sets: T1 and the split of T2 into T2-dev and T2-final are fixed in advance (see [smart-goals.md](smart-goals.md)) and versioned with DVC.
2. **Teacher fine-tuning.** Fine-tune a large PII detection model on our data. This large model is the "teacher".
3. **Distillation.** Train a smaller "student" model to copy the teacher.
4. **Quantization.** Store the student's numbers with fewer bits, so that it is smaller and can be faster on a laptop.
5. **Evaluation and quality gates.** Measure the student on T2-dev, then compare the results with thresholds fixed in advance. The metrics cover detection quality (how much personal data is found, and how much is masked by mistake) and performance (size and speed). The gates use T2-dev only: T2-final is kept for the final report.

Two tools support every step:

- **DVC** versions the data, the models and the pipeline stages. Its remote storage is a Cloud Storage bucket.
- **MLflow** tracks each run: parameters, metrics and artifacts, so that runs can be compared.

MLflow runs on a Debian VM in Iowa. The `e2-micro` and its 30 GB standard disk fit the shared Google Cloud Free Tier. Tracking and the model registry share a SQLite database on the retained disk. Authentication has its own SQLite database, and Caddy serves HTTPS.

Training jobs upload model files directly to a private Standard Cloud Storage bucket in `europe-west4`, where training runs. This keeps the roughly 1.2 GB teacher and 140 MB student transfers off the small Iowa VM. A run reserves `<run.artifact_uri>/models/<sha256>/model.tar.gz` for each model. The release step will record the Cloud Storage object generation and sign delivery after a PASS for the same hash. See [the MLflow setup](gcp-setup.md#mlflow-tracking-and-model-registry).

### Release

- **PASS.** If every threshold is met, the model is published to the MLflow model registry. Delivery requires a passing gate record for the same file hash.
- **FAIL.** If one threshold is not met, the model is rejected and is not delivered to users.

Only admin can create registered models. Before NoeBerdoz/tsm-machledata-anonymizer#15 publishes, admin creates `pii-teacher` and `pii-student` and grants the publishing login access to both.

The [operator guide](model-registry.md) lists the manual publication command and the separate demo model names.

### Local application

The registry identifies the approved model. The local application downloads the approved file from Cloud Storage through a signed URL and runs it on the device.

### Monitoring

Once the model runs in the application, we monitor how it behaves in real use with Sentry:

- **Response times**, to check that pseudonymization stays fast enough.
- **Errors**, in the application and in the backend.
- **User feedback**, from the star rating in the interface.


## Tools per block

| Block | Tool | Status |
|---|---|---|
| User interface | Streamlit (the engine is in Python, so the page calls it directly) | chosen |
| Regex rules | Python `re` | planned |
| ML model on the device | PyTorch CPU with eager int8. The folder reloads offline and stores the linear weights and word embeddings in 8 bits. The loader uses QNNPACK on ARM and prefers oneDNN on x86. The encoder's feed-forward output projections use float activations. The other linears use the activation range validated on that CPU. PyTorch has deprecated `torch.ao.quantization`. The app uses `qwen3:4b` with Ollama until the student is ready. | chosen |
| Backend API | FastAPI | chosen |
| Backend hosting | Cloud Run | to decide |
| LLM | Any endpoint of the OpenAI-compatible Chat Completions API, chosen with `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` on the backend. By default the local Ollama with `qwen3:4b`, so daily use costs nothing and nothing leaves the machine. A hosted model such as OpenAI or Claude only needs other values, for example for a demonstration. | chosen |
| Code and CI | GitHub, GitHub Actions | in place |
| Data and model versioning | DVC, remote on Cloud Storage | in progress (#8) |
| Training | Agent Platform (custom training jobs) | chosen |
| Experiment tracking | MLflow on Compute Engine, SQLite for runs, Cloud Storage for files | setup ready for cloud proof |
| Model registry | MLflow on the same VM and SQLite store | setup ready for cloud proof |
| Monitoring | Sentry | planned |

The x86 timing in NoeBerdoz/tsm-machledata-anonymizer#73 can reopen the runtime choice.

## Still to decide

Since 2026-11-02, we decided the datasets and T1 ([test-set-decision.md](test-set-decision.md)), the teacher GLiNER2-PII and the goals ([smart-goals.md](smart-goals.md)), the metrics ([evaluation.md](evaluation.md)) and the model registry, MLflow ([smart-goals.md](smart-goals.md), O5). These points are still open:

- How we build the student: how many layers it has, and how its weights start. The size estimates assume 6 layers.
- The values of the thresholds that depend on T2-dev.
- The tools marked "to decide" in the table above.
- How and when the local application checks for a new model.
- What monitoring measures beyond the pseudonymization time of O5.
