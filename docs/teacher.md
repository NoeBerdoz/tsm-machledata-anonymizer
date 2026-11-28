# The teacher v1

Issue #46 fine-tunes GLiNER2-PII (`fastino/gliner2-privacy-filter-PII-multi`) on our training data to get the teacher v1. As published, it misses 1,408 of the 7,275 entities of T1 (80.65 % recall), mostly of types its model card has no label for (see [baselines.md](baselines.md)).

## The labels

GLiNER2 takes its labels as plain names, so the teacher can learn new ones. `src/pii_anonymizer/teacher_labels.py` gives every type of our training data one GLiNER2 label. Two rules:

- When the model card has a label with the same meaning, we keep it, so that the model starts from what it already knows.
- When it has none, we add a new label, named after the type. The new labels are in **bold** below.

### OpenPII-1M

The 19 types of its card, plus `TIME`, which open-pii-masking-500k also has.

| Type | Label | | Type | Label |
|---|---|---|---|---|
| `GIVENNAME` | `first_name` | | `CITY` | `city` |
| `SURNAME` | `last_name` | | `ZIPCODE` | `postal_code` |
| `TITLE` | **`title`** | | `EMAIL` | `email` |
| `AGE` | **`age`** | | `TELEPHONENUM` | `phone_number` |
| `SEX` | **`sex`** | | `IDCARDNUM` | `government_id` |
| `GENDER` | **`gender`** | | `SOCIALNUM` | `national_id_number` |
| `DATE` | **`date`** | | `PASSPORTNUM` | `passport_number` |
| `TIME` | **`time`** | | `DRIVERLICENSENUM` | `drivers_license_number` |
| `STREET` | `street_address` | | `TAXNUM` | `tax_number` |
| `BUILDINGNUM` | **`building_number`** | | `CREDITCARDNUMBER` | `card_number` |

### Gretel (`gretelai/synthetic_pii_finance_multilingual`)

The 29 types of its card.

| Type | Label | | Type | Label |
|---|---|---|---|---|
| `name` | `full_name` | | `iban` | `iban` |
| `first_name` | `first_name` | | `bban` | `bank_account` |
| `last_name` | `last_name` | | `bank_routing_number` | `routing_number` |
| `company` | **`company`** | | `swift_bic_code` | **`swift_bic_code`** |
| `date`, `date_of_birth`, `date_time` | **`date`** | | `credit_card_number` | `card_number` |
| `time` | **`time`** | | `credit_card_security_code` | `card_cvv` |
| `email` | `email` | | `account_pin` | **`pin`** |
| `phone_number` | `phone_number` | | `customer_id` | `account_id` |
| `street_address` | `street_address` | | `employee_id` | **`employee_id`** |
| `local_latlng` | **`coordinates`** | | `user_name` | `username` |
| `ssn` | `national_id_number` | | `password` | `password` |
| `passport_number` | `passport_number` | | `api_key` | `api_key` |
| `driver_license_number` | `drivers_license_number` | | `ipv4`, `ipv6` | `ip_address` |

### Swiss values

The values of `swiss_training.py` ([swiss-identifiers.md](swiss-identifiers.md)) keep the label of their kind: `AVS` is `national_id_number`, like `SOCIALNUM`, `PHONE` is `phone_number` and `IBAN` is `iban`. A Gretel `bban` that receives a Swiss IBAN becomes `iban`.

### Choices

- **One label for all dates.** OpenPII-1M labels every date `DATE`, birth dates included, while Gretel splits `date`, `date_of_birth` and `date_time`. With two labels, the same kind of birth date would be `date` in one dataset and `date_of_birth` in the other, so the model would learn two answers for one text. Our recall does not depend on the label (an entity counts when all its characters are masked), so one label loses nothing.
- **`building_number` apart from `street_address`.** OpenPII-1M labels the street and the house number as two entities. Giving them the same label would teach the model two touching spans of one type.
- **`IDCARDNUM` is `government_id` and `SOCIALNUM` is `national_id_number`**, as in the first cloud run ([cloud-training.md](cloud-training.md)).
- **`company` is kept.** It is the third type of Gretel by count, and GLiNER2-PII finds only 28 % of the company names of the Swiss set. A company name can identify a person, for example a one-person business.
- **The card labels without training data are dropped**, such as `address`, `person`, `country`, `card_expiry` or `access_token`. The teacher is asked for the 35 labels of `TARGETS` only, so we measure what we trained.

Of these 35 labels, 12 are new: `title`, `age`, `sex`, `gender`, `date`, `time`, `building_number`, `company`, `coordinates`, `swift_bic_code`, `pin` and `employee_id`.

## The training subset

`src/pii_anonymizer/teacher_data.py` writes `data/train/teacher-v1.jsonl`, versioned with DVC:

```sh
uv run --group baselines python -m pii_anonymizer.public_data data/test/
uv run python -m pii_anonymizer.swiss data/test/t1-openpii-1m.jsonl data/test/gretel-test-iban.jsonl data/test/t1-swiss.jsonl --seed 0
uv run --group baselines python -m pii_anonymizer.teacher_data data/train/teacher-v1.jsonl \
    --exclude data/test/t1-openpii-1m.jsonl --exclude data/test/t1-open-pii-500k.jsonl \
    --exclude data/test/gretel-test-iban.jsonl --exclude data/test/t1-swiss.jsonl \
    --exclude data/test/t2-dev.jsonl --exclude-manifest data/test/t2-final-holdout.json
```

The first two commands rebuild the T1 and Swiss test sets. `uv run dvc pull data/test/t2-dev.jsonl.dvc data/test/t2-final-holdout.json.dvc` gets T2-dev and the manifest of T2-final. The third command reads them to check that no training row is a test row. It reads T2-final only through its manifest, and refuses `t2-final.jsonl` itself.

| Source | Split | Rows | Per language (FR, DE, IT, EN) |
|---|---|---|---|
| OpenPII-1M | train | 40,000 | 10,000 |
| Gretel | train | 10,000 | 2,500 |

- **80 % OpenPII-1M, 20 % Gretel.** OpenPII-1M holds the types that GLiNER2-PII misses most (title, age, sex, gender). Gretel adds IBANs, company names and the document formats where GLiNER2-PII misses IBANs (SWIFT messages, XML). Its documents are about ten times longer, so its 10,000 documents weigh about as much text as the 40,000 OpenPII-1M rows.
- **Seed 1.** The rows are drawn with seed 1, sorted by uid (OpenPII-1M) or index (Gretel) first, so the draw does not depend on the file order. The test samples use seed 42 and come from the validation and test splits, so the splits already keep them apart. The Swiss values use seed 3, the training seed of `swiss_training.py`: seeds 0, 1 and 2 are kept for the Swiss test sets (see [swiss-identifiers.md](swiss-identifiers.md)).
- **Pinned data.** Both datasets are read from the pinned commits of `PARQUET_REVISIONS` in `public_data.py`.
- **Checks.** The script stops if an entity has a label without a teacher label, or if a training row has the id or the text of a test row.

The file written on 2026-11-22 (DVC md5 `467749555317968ee6a14428ff71129c`, 49,480,619 bytes):

- 50,000 rows: 10,000 OpenPII-1M rows and 2,500 Gretel documents per language. 26.3 million characters, 13.9 million from OpenPII-1M and 12.4 million from Gretel.
- No OpenPII-1M entity dropped. 76 Gretel entities dropped, because their span is empty, does not fit the text or has outer spaces (`convert_gretel_row` in `public_data.py`).
- 4,206 rows with Swiss values: 1,322 AVS numbers, 3,471 phone numbers and 121 IBANs. Every AVS number and IBAN passes the validators of `rules.py`.
- No training row has the source id or the text of a row of T1 (both samples), the Gretel test sample, the Swiss test set, T2-dev or T2-final, before and after the Swiss values. The check against the frozen T2 was added after the subset was built; the rebuild gave the same file, with the same md5.
- 665 OpenPII-1M phone numbers have a trailing space inside their span, as in the dataset. `to_example` strips it, so the teacher learns the number without the space.

The most frequent teacher labels are `date` (48,575 entities), `first_name` (34,013) and `last_name` (29,645). The rarest are Gretel's: `coordinates` (152) and `password` (142).

## The training job

One launcher, `src/pii_anonymizer/cloud_training.py`, runs every training job on Agent Platform. It has three modes, with the settings of `training.modes` in `params.yaml`:

| Mode | Started by | Rows | Cap | Outputs |
|---|---|---|---|---|
| `ci` | `dvc repro` in GitHub Actions | 1,000 (100 held out) | 30 min, inside the 90-minute runner | `.pipeline/` |
| `--trial` | a laptop | 2,000 (200 held out) | 30 min | `.pipeline/teacher/<id>/` |
| `--full` | a laptop | the 50,000 rows | 5 hours | `.pipeline/teacher/<id>/` |

```sh
gcloud auth application-default login   # once, with the group account
export MLFLOW_TRACKING_URI='<tracking HTTPS URL>'
uv run python -m pii_anonymizer.cloud_training --trial --id <name>   # the short run
uv run python -m pii_anonymizer.cloud_training --full --id <name>    # the teacher
```

- The launcher checks that the subset matches its DVC pointer. The `ci` mode also checks the frozen T2-dev and that the cap fits in the Actions runner; the laptop modes check that the tree is clean and the commit pushed. It uploads the job's files to `pipeline/inputs/<id>/` of the training bucket, creates one Agent Platform job, waits for it, and downloads the model and `training.json`, checked against their SHA-256. Running it again with the same `--id` (or the same Actions run) finds the first job instead of creating a second one.
- `scripts/training/job.yaml` is the machine of the first cloud run: one n1-standard-4 with one T4 in europe-west4, the same image and libraries.
- `scripts/training/train.py` fine-tunes GLiNER2-PII for 2 epochs (batches of 4 rows, 2 per update, fp16) and logs the run to MLflow, with the commit, `params.yaml` and the DVC hash of the subset. It writes `epoch-1.tar.gz` as soon as the first epoch ends, so a cap during the second epoch keeps it, then `model.tar.gz` and `training.json`. The laptop modes download `epoch-1.tar.gz` too.
- Both checkpoint archives include `labels.json`, the list of labels used in training. The `evaluate` stage reads this list. For older teacher archives, it uses `teacher_labels.TARGETS`.
- The `train` stage of `dvc.yaml` depends only on the shared values and `training.modes.ci`, so changing `--trial` or `--full` does not retrain in the CI. `training_pipeline prepare` pulls the subset with DVC.

**The short run.** `--trial` trains on 2,000 rows of the subset, with 200 more held out to measure the recall before and after, and a cap of 30 minutes (`training.modes.trial`). It measures the speed on our data: `training.json` gives the characters per second and `full_run_hours_estimate`, the training time of the full subset at that speed. Our rows are longer than those of the first cloud run, because of the Gretel documents, so its 18 rows per second does not apply.
