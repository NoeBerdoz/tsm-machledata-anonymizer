# On-device PII pseudonymizer for cloud LLMs

Group project for the course TSM_MachLeData (MLOps), MSE HES-SO, autumn 2026.

## What is PII?

PII means *Personally Identifiable Information*: any data that can tell who a person is. For example a name, an AVS number, an IBAN, an e-mail address or a phone number.

## Project idea

People send more and more prompts and documents to LLMs in the cloud. These prompts and files often hold personal data: names, AVS numbers, IBANs, phone numbers, health information.

We are building our own application. The user writes a prompt in our interface and can attach files (PDF, TXT, DOCX, CSV). A local engine finds the personal data in the prompt and in the files. It uses regex rules for structured identifiers and our own small ML model for the rest. It replaces each value with a placeholder such as `<PERSON_1>` (decided in issue #17), and it keeps the mapping table on the device only. Only the pseudonymized text goes to our backend (FastAPI), which sends it to an LLM through the OpenAI-compatible Chat Completions API: the local Ollama by default, or a hosted model such as OpenAI or Claude. When the response comes back, the application puts the real values back on the device. Neither the LLM nor our backend sees the real values that the engine detects. See [docs/architecture.md](docs/architecture.md).

The mapping table lets us put the real values back. So we call it pseudonymization, not anonymization: the data can still be linked to a person with extra information, here the mapping table kept on the device. The GDPR draws the same line between the two (Art. 4(5) and Recital 26).

The repository and the Python package keep their names (`tsm-machledata-anonymizer`, `pii_anonymizer`), while the method is pseudonymization. Renaming the package now would conflict with the open branches that add code to it, and the DVC bucket `tsm-machledata-anonymizer-dvc` cannot be renamed.

To make the model small and fast, we will use two techniques:

- **Distillation**: a small "student" model learns to copy a large "teacher" model.
- **Quantization**: we store the numbers inside the model with fewer bits, so the model takes less space and can run faster.

## Repository structure

```
.
├── README.md                    this page
├── .gitignore                   files that git does not track (PDFs, node_modules, ...)
├── pyproject.toml               the Python project and its dependencies
├── uv.lock                      the exact version of every dependency
├── src/pii_anonymizer/          our code as a Python package: the app, the pseudonymization engine and the pipeline
├── tests/                       the tests
├── notebooks/                   explorations
├── data/                        the data, versioned with DVC
├── results/                     evaluation results, one row per model, test set and machine
├── .github/workflows/ci.yml     lint and tests on every pull request
├── docs/
│   ├── architecture.md          the app, the backend and the MLOps pipeline
│   ├── smart-goals.md           our goals, thresholds and test sets
│   ├── datasets.md              the datasets we plan to use, with their licences
│   ├── test-set-decision.md     why we build our own test set T2, and its format
│   ├── benchmark-protocol.md    how we will measure model size and speed
│   ├── evaluation.md            the test set format, the metrics and the results files
│   ├── baselines.md             what off-the-shelf detectors reach on the T1 candidates
│   ├── swiss-identifiers.md     the Swiss test set: valid fake AVS, IBAN and phone values
│   ├── development.md           how the code is organised, and why
│   └── project-management.md    how we plan and share the work
├── report/
│   ├── README.md                how to build the report
│   ├── main.typ                 the report, written in Typst
│   └── refs.bib                 the references of the report
└── slides/
    ├── README.md                how to run and export the slides
    ├── package.json             the Slidev tools that the slides need
    ├── seminar/slides.md        the seminar talk
    └── final/slides.md          the final talk
```

## Set up the project and run the tests

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). It installs Python 3.13 and every dependency for you. From the repository root:

```sh
uv sync                  # creates .venv with the right Python and dependencies
uv run pytest            # runs the tests
uv run ruff check        # checks the code style
```

DVC comes with `uv sync`. To get the data, log in once per machine with the group's dedicated Google account (`gcloud auth application-default login`) and run `uv run dvc pull`. See [docs/development.md](docs/development.md) for the details, the project layout, the parameters and the daily commands.

## Run the local interface

You need [Ollama](https://ollama.com) with the model `qwen3:4b`. The app uses it to detect personal data until our own model is trained, and the backend uses it to answer. Ollama must run with a context of 16384 tokens: set `OLLAMA_CONTEXT_LENGTH=16384` in the environment of the Ollama server, then restart it. Without it, Ollama cuts long content from the backend without any error. The app only sends pseudonymized content to our backend (FastAPI), which returns the response. Both read the same shared token from `PII_BACKEND_TOKEN`; choose any long random string. From the repository root, in two terminals:

```sh
ollama pull qwen3:4b                          # first time only
export PII_BACKEND_TOKEN=change-me            # PowerShell: $env:PII_BACKEND_TOKEN = "change-me"
uv run python -m pii_anonymizer.backend       # terminal 1: the backend on http://127.0.0.1:8000
uv run python -m pii_anonymizer               # terminal 2: opens the interface in your browser
```

The app finds the backend at `PII_BACKEND_URL` (default `http://127.0.0.1:8000`). The backend refuses every request without the token, and it never logs a prompt or a response.

The same backend also runs on Cloud Run. To use it instead of the local one, skip terminal 1 and set `PII_BACKEND_URL` and `PII_BACKEND_TOKEN` as described in [docs/gcp-setup.md](docs/gcp-setup.md#use-it-from-the-app). It cannot reach your local Ollama, so it answers with an error until it is set to a hosted LLM.

Write a prompt, attach files (PDF, TXT, DOCX, CSV) and press **Pseudonymize and answer**. The page shows the pseudonymized content, the response with the response time, and the mapping table. You can rate the response from 1 to 5 stars. The rating and the times go to `feedback.jsonl` in the current folder, without any prompt or response text.

The app sends nothing when the local model fails, when a file cannot be read or holds no text, or when the model found a value that it cannot place in the text. It tells the user instead.

By default the backend asks `qwen3:4b` through the local Ollama, so nothing leaves your machine, and the response keeps its placeholders. Start the interface with this command and not with `streamlit run`: it keeps the page on your machine and turns off Streamlit's usage statistics.

### Use a hosted LLM

The backend talks to any endpoint of the OpenAI-compatible Chat Completions API. Three variables in the backend's environment choose it, and the code does not change:

| Variable | Default | Example for OpenAI | Example for Claude |
|---|---|---|---|
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` (local Ollama) | `https://api.openai.com/v1` | `https://api.anthropic.com/v1/` |
| `LLM_MODEL` | `qwen3:4b` | the chosen model | the chosen model |
| `LLM_API_KEY` | empty, Ollama needs none | the API key | the API key |

The key stays on the backend side: it is never in the app, and it is sent only when it is set. A hosted model costs money for each request, so set a spending limit with the provider. The backend still refuses content longer than 14,000 characters, the limit measured for the local model.

## Build the report

You need [Typst](https://typst.app). From the repository root:

```sh
typst compile report/main.typ
```

This writes `report/main.pdf`.

## Run the slides

You need [Node.js](https://nodejs.org). The slides use [Slidev](https://sli.dev).

```sh
cd slides
npm install            # first time only
npm run dev:seminar    # opens the seminar talk in your browser
```

Use `npm run dev:final` for the final talk.

## Deliverables

| What | When |
|---|---|
| Seminar talk (8 min + 3 min questions) | 2026-11-16 |
| Final talk (8 min + 3 min questions) | About mid-December 2026, date to confirm |
| Report (8 pages at most) | About mid-December 2026, date to confirm |
