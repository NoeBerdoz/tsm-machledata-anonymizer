# Development

How the code is organised, and the commands we use every day. The README has the short version to get started.

## Project layout

```
.
├── pyproject.toml          the project, its dependencies, and the ruff and pytest settings
├── uv.lock                 the exact version of every dependency (do not edit by hand)
├── .python-version         the Python version (3.13)
├── params.yaml             the parameters of the pipeline stages (comes with the first stage)
├── dvc.yaml                the pipeline stages (comes with the first stage)
├── src/pii_anonymizer/     our code, as a Python package
├── tests/                  the tests, run by pytest
├── notebooks/              explorations, not used by the pipeline
├── data/                   the data, versioned with DVC, not with git
└── .github/workflows/      the checks that run on every pull request
```

## Why a package and not plain scripts

In the MLOps guide of homework 1, the code was a few scripts called directly: `python src/train.py data/prepared model`. Here the code is a package, `src/pii_anonymizer/`, and a stage runs it as a module: `uv run python -m pii_anonymizer.train data/prepared model`.

The reason is that our code is shared. The same pieces (the list of PII labels, the placeholders such as `<PERSON_1>`, the code that puts the real values back) are used by several pipeline stages, by the tests, by the notebooks and by the Claude Code hook. With a package, all of them write `from pii_anonymizer.labels import LABELS` and it works from any folder. With plain scripts, Python only finds the other files if you start it from the right folder, so the tests and the notebooks need path tricks.

What stays the same as in the guide: one file per stage (`prepare.py`, `train.py`, `evaluate.py`, ...), and each stage takes its input and output folders as arguments.

## Parameters

We keep the guide's setup. All the parameters live in `params.yaml` at the root, with one section per stage:

```yaml
prepare:
  seed: 42
  split: 0.2
train:
  lr: 0.0001
  epochs: 3
```

In `dvc.yaml`, each stage lists the sections it uses:

```yaml
stages:
  train:
    cmd: uv run python -m pii_anonymizer.train data/prepared model
    deps:
      - data/prepared
      - src/pii_anonymizer/train.py
    params:
      - train
    outs:
      - model
```

And the stage reads its section:

```python
train_params = yaml.safe_load(open("params.yaml"))["train"]
```

This gives us three things for free:

- `dvc repro` reruns a stage only when its code, its data or its parameters change.
- `dvc.lock` records the exact values used for each run.
- `dvc params diff main` shows the changed values in a pull request, next to `dvc metrics diff main`.

The file is at the root and named `params.yaml` because that is where DVC looks by default. Anywhere else, we would have to give its path in every stage and in every `dvc params` command.

## Data

The data never goes into git. `data/raw/` holds the datasets as downloaded, and `data/prepared/` the output of the `prepare` stage. Git only keeps the small `.dvc` files that point to the data. The DVC remote storage will be set up once we choose it in [#1](https://github.com/NoeBerdoz/tsm-machledata-anonymizer/issues/1).

## Dependencies

We use [uv](https://docs.astral.sh/uv/). `uv run <command>` runs a command inside the project's environment, so there is nothing to activate.

| Task | Command |
|---|---|
| Install or update the environment after a pull | `uv sync` |
| Add a library | `uv add transformers` |
| Add a tool only needed for development | `uv add --dev <name>` |
| Remove a library | `uv remove <name>` |

`uv add` and `uv remove` also update `uv.lock`. Commit both `pyproject.toml` and `uv.lock`.

## Checks

The same checks run on every pull request (`.github/workflows/ci.yml`). Run them before you push:

```sh
uv run ruff check        # lint
uv run ruff format       # format the code (CI only checks it)
uv run pytest            # tests
```

`uv run ruff check --fix` fixes most lint errors on its own.
