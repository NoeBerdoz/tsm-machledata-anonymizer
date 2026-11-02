# Architecture

This page describes the two parts of the project: the application that anonymizes data on the user's device, and the MLOps pipeline that trains, delivers and monitors its model. Many details are still open. This page gives the structure, not the final choices.

## 1. Main application architecture

![Main application architecture](diagrams/architecture.png)

The idea is simple: personal data never leaves the user's device. Only anonymized content goes to the cloud.

### On the user's device (private zone)

1. **User interface.** The user writes a prompt and can attach files (PDF, TXT, DOCX, CSV).
2. **Local anonymization engine.** The engine finds personal data in the prompt and in the files. It has two parts that work together:
   - **Regex rules** for structured identifiers, which follow a fixed format.
   - **Our ML model** for contextual entities, such as names or addresses, which need context to be found. This is the model we train ourselves: a student distilled from a larger teacher and quantized, produced by the pipeline in part 2.
3. **Replacement with placeholders.** Each value that the engine finds is replaced by a placeholder, such as `<PERSON_1>` or `<IBAN_1>`. The same value always gets the same placeholder. The engine records each pair in a **mapping table** (placeholder ↔ real value), which is kept on the device only.
4. **Privacy boundary.** Only the anonymized content goes past this point.

### In the cloud

5. **Backend API (FastAPI).** It receives the anonymized request and handles authentication and request control.
6. **OpenAI Responses API.** It processes the anonymized prompt and sends back a response. The model works with the placeholders as if they were normal words, so its response contains placeholders too, never real values.

### Back on the device

7. **Response restored locally.** The application reads the response, finds each placeholder in it, and looks it up in the mapping table. It then replaces the placeholder with the real value, for example `<PERSON_1>` → `Marie Dupont`, and shows the restored response to the user.

The restoration happens on the device because the mapping table never leaves it. Neither the backend nor OpenAI ever sees the real values.

## 2. Training and deployment pipeline (MLOps)

![Training and deployment pipeline](diagrams/mlops.png)

This pipeline produces the ML model used by the local anonymization engine. Training happens in the cloud. The model then runs on the user's device, and its use is monitored.

### Source and automation

1. **GitHub.** It holds the code and the configuration of the project.
2. **GitHub Actions.** It runs the automated tests and triggers the training pipeline.

### Training on Google Cloud (Agent Platform)

The pipeline runs on Agent Platform, Google Cloud's platform for training and managing models (formerly Vertex AI). It has five steps:

1. **Data preparation.** Collect the datasets, clean them and split them into training and test sets.
2. **Teacher fine-tuning.** Fine-tune a large PII detection model on our data. This large model is the "teacher".
3. **Distillation.** Train a smaller "student" model to copy the teacher.
4. **Quantization.** Store the student's numbers with fewer bits, so that it is smaller and faster on a laptop.
5. **Evaluation and quality gates.** Measure the student on test data that it has never seen, then compare the results with thresholds fixed in advance. The metrics cover detection quality (how much personal data is found, and how much is masked by mistake) and performance (size and speed).

### Release

- **PASS.** If every threshold is met, the model is published to the model registry.
- **FAIL.** If one threshold is not met, the model is rejected and is not delivered to users.

### Local application

The local application downloads and installs the approved model from the registry.

### Monitoring

Once the model runs in the application, we monitor how it behaves in real use, for example with Sentry:

- **Response times**, to check that anonymization stays fast enough.
- **Errors**, in the application and in the backend.
- **User feedback**, to know whether users are satisfied with the results.

Monitoring must never collect personal data: no prompts, no files, no responses, and no values from the mapping table. Only technical measures and anonymous feedback are sent.

What we learn from monitoring feeds the next iteration: changes to the code, the data or the configuration go back to GitHub, and the pipeline runs again.

## Still to decide

- The datasets, and the teacher and student models.
- The metrics and the values of the quality-gate thresholds.
- Where the backend API is hosted.
- How and when the local application checks for a new model.
- The monitoring tool and the exact measures it collects.
