# On-device PII anonymizer for AI agents

Group project for the course TSM_MachLeData (MLOps), MSE HES-SO, autumn 2026.

## What is PII?

PII means *Personally Identifiable Information*: any data that can tell who a person is. For example a name, an AVS number, an IBAN, an e-mail address or a phone number.

## Project idea

AI agents are used more and more to automate work. These agents read documents, files and tool outputs, and they send them to a model provider in the cloud. This often includes personal data: names, AVS numbers, IBANs, phone numbers, health information.

We are building a small model that runs locally, on the machine where the data lives. It finds the personal data and hides it behind placeholders, such as `<PERSON_1>`, before anything leaves the machine. When the answer comes back, it puts the real values back. The agent can still do its job, and the provider never sees the real data. We will test it first with Claude Code.

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
├── src/pii_anonymizer/          our code, as a Python package
├── tests/                       the tests
├── notebooks/                   explorations
├── data/                        the data, versioned with DVC
├── .github/workflows/ci.yml     lint and tests on every pull request
├── docs/
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

You also need [DVC](https://dvc.org/doc/install) to get the data. See [docs/development.md](docs/development.md) for the project layout, the parameters and the daily commands.

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
