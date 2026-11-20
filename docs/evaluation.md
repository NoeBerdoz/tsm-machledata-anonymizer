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

## Scripted O4 requests

The O4 fixtures live in `data/test/o4_requests/`, versioned together in DVC. Its UTF-8 manifest, `requests.jsonl`, has one line per request. This example uses a shortened prompt and a single attachment.

```json
{"id":"o4-fr","lang":"fr","prompt":"Vérifie Élise Burnier.","files":["suivi.txt"],"values":[{"id":"o4-fr-001","label":"PERSON","value":"Élise Burnier","occurrences":[{"source":"prompt","start":8,"end":21},{"source":"suivi.txt","start":23,"end":36}]}]}
```

- `files` lists the attachments in upload order, as paths relative to the manifest. The app uses their filenames.
- `values` holds 100 distinct planted values across the manifest. Each has a globally unique `id`, an entity type (`label`), and the exact `value`. All repetitions of that value in the request share its ID.
- Each occurrence identifies its source as `prompt` or the attachment's filename. Offsets are zero-based Python string indices with an exclusive `end`. Use the manifest prompt verbatim and extract each attachment with `pii_anonymizer.files.read_text(filename, bytes)`. Every `text[start:end]` slice must equal `value`.
- The French request repeats a name and IBAN across the prompt and two files. Its notes contain the literal `<PERSON_1>` as fixture text outside the planted values.

Generate the files locally with `uv run python scripts/generate_o4_requests.py`. The test in `tests/test_o4_requests.py` generates its own copy in a temporary directory, so it runs without a DVC download.

### Leak and restoration checks

With the `gliner2-tests` dependencies and the published GLiNER2-PII checkpoint already available locally, run:

```sh
uv run --no-sync python scripts/generate_o4_requests.py
HF_HUB_OFFLINE=1 uv run --no-sync python -m pii_anonymizer.o4 gliner2 data/test/o4_requests/requests.jsonl
```

For the delivered student, set `GLINER2_INT8_DIR` to its checkpoint folder and use `gliner2-int8` in place of `gliner2`.

The harness drives the Streamlit app with the fixture uploads and runs the real file extraction, regex rules, masking and restoration. It supplies the selected model's spans in place of the app's Ollama detector. The harness maps model labels to the app's restorable labels, using `PERSON` as a fallback for categories without an app equivalent. The adapter keeps every span's original offsets. The harness captures the client request, forwards it through the backend route in process, and captures the current backend's Ollama payload. A fake reply echoes every placeholder occurrence, including literal placeholder text, so the harness can compare each displayed value with the local mapping after normalizing whitespace. The Sentry capture is reserved for the monitoring integration.

The JSON report traces occurrences and mask spans by source and offset. A planted ID is detected when all its occurrences meet the coverage rule below. The harness checks every planted ID against the captures from the entire run and compares IBANs without whitespace within each decoded field. Each detected ID whose full value appears in any capture counts once as an app leak. The overall leak count includes all detector misses, including partial matches. `restored` and `intact` give the restoration counts for generated placeholders. Changed literal tokens appear in the per-request restoration failures.

Published GLiNER2-PII with the app rules detected 100 of 100 planted IDs, recorded zero app leaks and detector misses, and restored all 112 intact placeholders. See the [O4 results](../results/o4.md).

## Detector interface

A detector takes one text and returns the character spans to mask, each with a type (`Span(start, end, label)`). It also gives its runtime and version (`runtime`, for example `"torch 2.9.1"`) and the files it needs to run (`files`, used for the size). The `Detector` protocol in `spans.py` has the exact signature:

```python
class Detector(Protocol):
    runtime: str
    files: Sequence[Path]

    def detect(self, text: str, lang: str | None = None) -> list[Span]: ...
```

`lang` is the `lang` of the record. When a record has no `lang`, the script calls `detect(text)` and the detector gets `None`. The regex and GLiNER2 ignore the language. Presidio needs it, because it runs one spaCy model per language. So Presidio receives the true language of each text, which our app will not always know. This slightly favours Presidio in the comparison.

To make a detector available to the command line, add a function that loads it to the `DETECTORS` dict in `evaluate.py`. The script loads it once, before any timing. The function imports the detector's heavy libraries itself, so that the script can set the thread variables first. The baselines are in `baselines.py` and `rules.py`. See [baselines.md](baselines.md) for the detectors and how to run them.

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

The script writes three files into the output folder. A rerun replaces rows for the same detector, dataset and CPU. For `gliner2-int8`, the runtime record also has to match, so each checkpoint and activation policy keeps its own rows.

`results.csv` has one row per detector, dataset and CPU, with separate runtime records for `gliner2-int8`. Latency numbers only compare within one machine. The official numbers for the goals come from the reference laptop named in [benchmark-protocol.md](benchmark-protocol.md). The quality gate of the CI (NoeBerdoz/tsm-machledata-anonymizer#14) compares the student with the teacher in the same job. It checks the size (at least 8 times smaller, O3) and the latency ratio (student p95 at most two thirds of the teacher's, O3). So it needs no reference machine.

| Column | Meaning |
|---|---|
| `model`, `dataset` | the detector name and the test set name |
| `dataset_sha256` | the hash of the test set file, to check that two rows used the same data |
| `runtime` | the runtime and its version. For `gliner2-int8`, it includes the engine, activation range, number of float-activation linears, source model and one SHA-256 digest covering the weights, tokenizer and inference configs |
| `n_texts`, `n_entities`, `n_protected` | the counts behind the recall |
| `strict_recall`, `char_precision` | the metrics above, between 0 and 1 |
| `size_bytes`, `size_mb` | the size on disk. For converted GLiNER2 checkpoints, the manifest lists the files counted |
| `threads` | the thread count of the protocol |
| `latency_inputs`, `latency_calls` | the texts timed and the calls recorded |
| `latency_p50_ms`, `latency_p95_ms` | latency per call |
| `latency_p50_ms_per_100_words`, `latency_p95_ms_per_100_words` | latency per 100 words |
| `cpu` | the CPU model name, read from the operating system |
| `os`, `python`, `date` | the OS, the Python version and the day of the measurement |

An empty cell means "not measured" or "undefined", never zero.

`recall_per_type.csv` uses the same keys as `results.csv` and adds the gold label. Quantized engines can change recall, so each CPU keeps its own counts. Older rows may have empty CPU and runtime fields. Each row has the number of gold entities of that label, the number protected, and the recall.

`summary.md` is made from `results.csv`. It has one small Markdown table per CPU, with recall, precision, size and p95 latency for every row. Local int8 rows show a short artifact digest beside the detector name. The reference laptop's table comes first.

## O4 response corruptions

Inject each example into a mocked backend response. The response on screen must keep the corrupt text as sent, and the app must show a warning identifying it. A warning counts as a flagged corruption only.

| Corruption | Example | Prior coverage |
|---|---|---|
| Unknown number | `<PERSON_3>` | Restoration and app |
| Missing angle brackets | `PERSON_1` | Restoration |
| Changed label case | `<person_1>` | Restoration |
| Missing closing bracket | `<PERSON_1` | Restoration |
| Square brackets | `[PERSON_2]` | Restoration |
| Hyphen separator | `<PERSON-1>` | Restoration |
| Space separator | `<PERSON 1>` | Restoration |
| Spaces inside brackets | `< PERSON_1 >` | Restoration |
| Changed case and separator on another label | `<email-1>` | Restoration |

The examples come from the restoration tests in NoeBerdoz/tsm-machledata-anonymizer#85 (`tests/test_engine.py`). The app test for the unknown number already used a mocked backend as of NoeBerdoz/tsm-machledata-anonymizer#84. The cases now run through the app in `tests/test_app.py`. For square brackets, the warning identifies the inner `PERSON_2` while the response keeps `[PERSON_2]`.

Swapping two valid placeholders from the same request is outside the guarantee. For example, the app has no way to tell that `<PERSON_2>` should have been `<PERSON_1>` when both were sent.
