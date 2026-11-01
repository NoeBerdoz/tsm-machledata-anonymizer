# Architecture

This page describes the two parts of the project: the application that anonymizes data on the user's device, and the MLOps pipeline that trains and delivers its model. Many details are still open. This page gives the structure, not the final choices.

## 1. Main application architecture

![Main application architecture](diagrams/architecture.png)

The idea is simple: personal data never leaves the user's device. Only anonymized content goes to the cloud.

### On the user's device (private zone)

1. **User interface.** The user writes a prompt and can attach files (PDF, TXT, DOCX, CSV).
2. **Local anonymization engine.** The engine finds personal data in the prompt and in the files. It has two parts that work together:
   - **Regex rules** for structured identifiers, which follow a fixed format.
   - **An ML model** for contextual entities, such as names or addresses, which need context to be found.
3. **Replacement with placeholders.** Each value that the engine finds is replaced by a placeholder, such as `<PERSON_1>` or `<IBAN_1>`. The mapping between each placeholder and its real value is stored locally, on the device only.
4. **Privacy boundary.** Only the anonymized content goes past this point.

### In the cloud

5. **Backend API (FastAPI).** It receives the anonymized request and handles authentication and request control.
6. **OpenAI Responses API.** It processes the anonymized prompt and sends back a response. This response still contains placeholders only.

### Back on the device

7. **Response restored locally.** The application uses the local mapping to put the real values back in place of the placeholders, then shows the response to the user.

The restoration happens on the device because the mapping never leaves it. Neither the backend nor OpenAI ever sees the real values.

## 2. Training and deployment pipeline (MLOps)

![Training and deployment pipeline](diagrams/mlops.png)

This pipeline produces the ML model used by the local anonymization engine. Training happens in the cloud. The model then runs on the user's device.

### Source and automation

1. **GitHub.** It holds the code and the configuration of the project.
2. **GitHub Actions.** It runs the automated tests and triggers the training pipeline.

### Training on Google Cloud (Agent Platform)

The pipeline runs on Agent Platform, Google Cloud's platform for training and managing models. It has five steps:

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
