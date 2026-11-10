# Evaluation

How we measure every model, from the first baseline to the quantized student, so that all our numbers can be compared. The code is in `src/pii_anonymizer/`: `spans.py` (the format and the interface), `metrics.py`, `benchmark.py` (size and latency), `results.py` and `evaluate.py`. Size and latency follow [benchmark-protocol.md](benchmark-protocol.md).

## Test set format

A test set is a JSONL file: one JSON record per line.

```json
{"id": "t2-0001", "text": "Pay to CH93 0076 2011 6238 5295 7 today.", "entities": [{"start": 7, "end": 33, "label": "IBAN"}]}
```

- `id` is unique in the file.
- `start` and `end` are Python string indices, so they count code points, not bytes. `end` is exclusive: `text[start:end]` is the entity.
- `label` is the type as the dataset writes it. The evaluation script does not map labels between datasets and detectors. The converters of each dataset do that.
- `lang` is optional: the language code of the text (`fr`, `de`, `it`, `en`). The evaluation script passes it to the detector.
- Other keys, such as `source` or `group`, are allowed. The evaluation script ignores them.

The loader refuses a file with a duplicate `id` or an entity that does not fit inside its text, and it gives the line number.

## Detector interface

A detector takes one text and returns the character spans to mask, each with a type (`Span(start, end, label)`). It also gives its runtime and version (`runtime`, for example `"torch 2.9.1"`) and the files it needs to run (`files`, used for the size). The `Detector` protocol in `spans.py` has the exact signature:

```python
class Detector(Protocol):
    runtime: str
    files: Sequence[Path]

    def detect(self, text: str, lang: str | None = None) -> list[Span]: ...
```

`lang` is the `lang` of the record. When a record has no `lang`, the script calls `detect(text)` and the detector gets `None`. The regex and GLiNER2 ignore the language. Presidio needs it, because it runs one spaCy model per language. So Presidio receives the true language of each text, which our app will not always know. This slightly favours Presidio in the comparison.

To make a detector available to the command line, add a function that loads it to the `DETECTORS` dict in `evaluate.py`. The script loads it once, before any timing. The function imports the detector's heavy libraries itself, so that the script can set the thread variables first. The baselines (`regex`, `presidio`, `gliner2`, and `regex+gliner2`, the union of the two) are in `baselines.py` and `rules.py`, and [baselines.md](baselines.md) describes them.

## Metrics

**Protected entity.** A gold entity is protected if every one of its characters is masked by a predicted span. The type of the predicted span does not matter: any mask protects. The predicted spans are merged first, so a gold entity covered by two overlapping or adjacent spans is protected. Whitespace inside a gold entity does not need to be masked. An IBAN masked group by group, with its spaces visible, is protected. An IBAN with its last digits visible is a leak.

**Strict recall** is the number of protected gold entities divided by the number of gold entities, over the whole test set (micro-average). One minus strict recall is the leak rate.

**Recall per type** is the same rule, grouped by the gold label.

**Character precision** is the share of masked characters that belong to a gold entity. We count only non-whitespace characters, and a character masked by two spans counts once. Over the whole test set, it is the number of masked characters inside a gold entity divided by the number of masked characters. A model that masks everything gets a low precision. When a detector masks nothing on the whole test set, precision is undefined, and its cell stays empty (never 0 or 1).

## Run it

```sh
uv run python -m pii_anonymizer.evaluate <detector> <test-set.jsonl> results/
```

The same command works on Linux, macOS and Windows, in bash, zsh, fish or PowerShell. The dataset name in the results is the file name without `.jsonl`, for example `t2-dev`. `--latency-ids` gives another list of snippet IDs for the latency sample. The default is `src/pii_anonymizer/latency_ids.txt`.

## Output files

The script writes three files into the output folder. Running a model again replaces its old rows, and the other rows are kept.

`results.csv` has one row per (model, dataset, cpu). Latency numbers only compare within one machine. The official numbers for the goals come from the reference laptop named in [benchmark-protocol.md](benchmark-protocol.md). Any teammate can add rows for their own laptop: the `cpu` column identifies them, and a rerun only replaces the row of the same CPU. The quality gate of the CI (#14) compares the student with the teacher in the same job (the quarter latency ratio, and the size), so it needs no reference machine.

| Column | Meaning |
|---|---|
| `model`, `dataset` | the detector name and the test set name |
| `dataset_sha256` | the hash of the test set file, to check that two rows used the same data |
| `runtime` | the runtime and its version |
| `n_texts`, `n_entities`, `n_protected` | the counts behind the recall |
| `strict_recall`, `char_precision` | the metrics above, between 0 and 1 |
| `size_bytes`, `size_mb` | the size on disk |
| `threads` | the thread count of the protocol |
| `latency_inputs`, `latency_calls` | the texts timed and the calls recorded |
| `latency_p50_ms`, `latency_p95_ms` | latency per call |
| `latency_p50_ms_per_100_words`, `latency_p95_ms_per_100_words` | latency per 100 words |
| `cpu` | the CPU model name, read from the operating system |
| `os`, `python`, `date` | the OS, the Python version and the day of the measurement |

An empty cell means "not measured" or "undefined", never zero.

`recall_per_type.csv` has one row per (model, dataset, label), because quality does not depend on the machine. Each row has the number of gold entities of that label, the number protected, and the recall.

`summary.md` is made from `results.csv`. It has one small Markdown table per CPU, with recall, precision, size and p95 latency for every row. The reference laptop's table comes first.
