# On-device PII pseudonymizer for cloud LLMs

Group project for the course TSM_MachLeData (MLOps), MSE HES-SO, autumn 2026.

## What is PII?

PII means *Personally Identifiable Information*: any data that can tell who a person is. For example a name, an AVS number, an IBAN, an e-mail address or a phone number.

## Project idea

People send more and more prompts and documents to LLMs in the cloud. These prompts and files often hold personal data: names, AVS numbers, IBANs, phone numbers, health information.

We are building our own application. The user writes a prompt in our interface and can attach files (PDF, TXT, DOCX, CSV). A local engine finds the personal data in the prompt and in the files. It uses regex rules for structured identifiers and our own small ML model for the rest. It replaces each value, for example with a placeholder such as `<PERSON_1>` or with a fake name (we decide in issue #17), and it keeps the mapping table on the device only. Only the pseudonymized text goes to our backend (FastAPI), which calls the OpenAI Responses API. When the response comes back, the application puts the real values back on the device. OpenAI and our backend never see the real data. See [docs/architecture.md](docs/architecture.md).

The mapping table lets us put the real values back. So we call it pseudonymization, not anonymization: the data can still be linked to a person with extra information, here the mapping table kept on the device. The GDPR draws the same line between the two (Art. 4(5) and Recital 26).

The repository and the Python package keep their names (`tsm-machledata-anonymizer`, `pii_anonymizer`), while the method is pseudonymization. Renaming the package now would conflict with the open branches that add code to it, and the DVC bucket `tsm-machledata-anonymizer-dvc` cannot be renamed.

To make the model small and fast, we will use two techniques:

- **Distillation**: a small "student" model learns to copy a large "teacher" model.
- **Quantization**: we store the numbers inside the model with fewer bits, so the model takes less space and runs faster.

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
├── .github/workflows/ci.yml     lint and tests on every pull request
├── docs/
│   ├── architecture.md          the app, the backend and the MLOps pipeline
│   ├── smart-goals.md           our goals, thresholds and test sets
│   ├── datasets.md              the datasets we plan to use, with their licences
│   ├── benchmark-protocol.md    how we will measure model size and speed
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
