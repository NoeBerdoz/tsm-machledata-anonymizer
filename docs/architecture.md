# Architecture

This page describes the two parts of the project: the application that pseudonymizes data on the user's device, and the MLOps pipeline that trains, delivers and monitors its model. Many details are still open. This page gives the structure, not the final choices.

The diagrams are in `docs/diagrams/`. The editable version is in Figma: [Schémas – anonymiseur PII](https://www.figma.com/design/EZFkhnWaznd3MO2BQZWDYB).

## Why our own interface and backend

We first planned to plug the anonymizer into Claude Code with hooks. We now build our own application instead: the user writes the prompt in our interface, we detect the personal data, we replace it, and we send the pseudonymized text to the OpenAI API through our backend.
1
- **Advantage:** we control the whole path, from the prompt to the response. This is much simpler than working around the limits of the hooks of an existing agent.
- **Drawback:** it only protects requests made through our interface. We assume that users send their LLM requests only through our application.

## 1. Main application architecture

![Main application architecture](diagrams/architecture.png)

The idea is simple: personal data never leaves the user's device. Only pseudonymized content goes to the cloud.

### On the user's device (private zone)

1. **User interface.** The user writes a prompt and can attach files (PDF, TXT, DOCX, CSV). We might implement feedback buttons letting the user rate each response. This feedback goes to monitoring.
2. **Local pseudonymization engine.** The engine finds personal data in the prompt and in the files. It has two parts that work together:
   - **Regex rules** for structured identifiers, which follow a fixed format.
   - **Our ML model** for contextual entities, such as names or addresses, which need context to be found. This is the model we train ourselves: a student distilled from a larger teacher and quantized, produced by the pipeline in part 2.
3. **Replacement.** Each value that the engine finds is replaced. The same value always gets the same replacement. We hesitate between two options, to be decided in a separate issue:
   - **Placeholders**, such as `<PERSON_1>` or `<IBAN_1>`. They are easy to find and restore exactly.
   - **Fake values**, such as a fake name (`Jean Martin`) in place of the real one. LLMs tend to work better with realistic text than with placeholders, but the restoration is harder: the LLM may change the fake value slightly, or the same fake value may already appear in the text.

   In both cases, the engine records each pair in a **mapping table** (replacement ↔ real value), which is kept on the device only.
4. **Privacy boundary.** Only the pseudonymized content goes past this point.

### In the cloud

5. **Backend API (FastAPI).** It receives the pseudonymized request and handles authentication and request control.
6. **OpenAI Responses API.** It processes the pseudonymized prompt and sends back a response. The response contains the replacements, never the real values.

### Back on the device

7. **Response restored locally.** The application reads the response, finds each replacement in it, and looks it up in the mapping table. It then swaps it back to the real value, for example `<PERSON_1>` or `Jean Martin` → `Marie Dupont`, and shows the restored response to the user.

The restoration happens on the device because the mapping table never leaves it. Neither the backend nor OpenAI ever sees the real values.

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
4. **Quantization.** Store the student's numbers with fewer bits, so that it is smaller and faster on a laptop.
5. **Evaluation and quality gates.** Measure the student on T2-dev, then compare the results with thresholds fixed in advance. The metrics cover detection quality (how much personal data is found, and how much is masked by mistake) and performance (size and speed). The gates use T2-dev only: T2-final is kept for the final report.

Two tools support every step:

- **DVC** versions the data, the models and the pipeline stages. Its remote storage is a Cloud Storage bucket.
- **MLflow** tracks each run: parameters, metrics and artifacts, so that runs can be compared.

### Release

- **PASS.** If every threshold is met, the model is published to the model registry (MLflow or Agent Platform, to decide).
- **FAIL.** If one threshold is not met, the model is rejected and is not delivered to users.

### Local application

The local application downloads the approved model from the registry and runs it on the device.

### Monitoring

Once the model runs in the application, we monitor how it behaves in real use with Sentry:

- **Response times**, to check that pseudonymization stays fast enough.
- **Errors**, in the application and in the backend.
- **User feedback**, from the feedback buttons in the interface (if implemented).


## Tools per block

| Block | Tool | Status |
|---|---|---|
| User interface | React JS | to decide |
| Regex rules | Python `re` | planned |
| ML model on the device | ONNX Runtime or PyTorch | to decide |
| Backend API | FastAPI | chosen |
| Backend hosting | Cloud Run | to decide |
| LLM | OpenAI Responses API | chosen |
| Code and CI | GitHub, GitHub Actions | in place |
| Data and model versioning | DVC, remote on Cloud Storage | in progress (#8) |
| Training | Agent Platform (custom training jobs) | chosen |
| Experiment tracking | MLflow | planned |
| Model registry | MLflow or Agent Platform | to decide |
| Monitoring | Sentry | planned |

## Still to decide

- Placeholders or fake values for the replacement (separate issue).
- The datasets, and the teacher and student models.
- The metrics and the values of the quality-gate thresholds.
- The tools marked "to decide" in the table above.
- How and when the local application checks for a new model.
- The exact measures that monitoring collects.
