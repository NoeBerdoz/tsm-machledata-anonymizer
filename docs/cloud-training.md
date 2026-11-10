# Cloud training: first run on Google Cloud

Issue #7. Goal: show that we can fine-tune GLiNER2-PII on Google Cloud, what it gives and
roughly what it costs. Nothing more: no pipeline, no experiment tracking.

**Result: it works.** On 2026-11-09, a fine-tuning of GLiNER2-PII on 900 rows ran on Agent
Platform (formerly Vertex AI) with one NVIDIA T4 in europe-west4. Training took 2 minutes, the
whole job about 13 minutes, for about USD 0.13.

## What the test does

`scripts/cloud-smoke/train.py` takes 1,000 rows of ai4privacy OpenPII-1M (train split only,
EN, FR, DE, IT), keeps 100 aside, and:

1. measures the recall of the published GLiNER2-PII (`fastino/gliner2-privacy-filter-PII-multi`)
   on the 100 rows;
2. fine-tunes it on the 900 others (2 epochs, batch size 8, fp16);
3. measures the recall again, prints a `SUMMARY` line and saves the model.

Recall = share of the PII entities whose characters are all masked (as in
[smart-goals.md](smart-goals.md)). ai4privacy labels are mapped to GLiNER2-PII labels with a
small draft mapping in the script.

It runs as an Agent Platform **custom job** (`scripts/cloud-smoke/job.yaml`): one
n1-standard-4 machine with one T4, using Google's prebuilt PyTorch image. There is no Docker
image to build: the job installs the libraries, then runs the script, which it reads from a
Cloud Storage bucket (mounted at `/gcs/` in the job).

## What we did, step by step

All commands were run in PowerShell on Windows, from the root of the repository, with the
group account **tsmmachledata@gmail.com**.

### 1. Install the Google Cloud CLI

`gcloud` was not installed. We installed it with:

```sh
winget install --id Google.CloudSDK
```

(or with the official installer: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe)

PowerShell then refused to run `gcloud` ("l'exécution de scripts est désactivée sur ce
système"), because `gcloud` is a PowerShell script. We allowed local scripts for our Windows
user, then reopened PowerShell:

```sh
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

If this is not allowed on a machine, use `gcloud.cmd` instead of `gcloud` in every command.

### 2. Log in with the group account and select the project

```sh
gcloud auth login tsmmachledata@gmail.com
gcloud config set project tsmmachledata-projet
gcloud auth list      # the active account (*) must be tsmmachledata@gmail.com
gcloud config list    # account = tsmmachledata@gmail.com, project = tsmmachledata-projet
```

### 3. Enable the Agent Platform API

```sh
gcloud services enable aiplatform.googleapis.com
gcloud services list --enabled --filter="config.name:aiplatform.googleapis.com"
```

The second command shows `aiplatform.googleapis.com  Agent Platform API`.

### 4. Get the GPU quota for training

The first job was refused with:

```
429 RESOURCE_EXHAUSTED: The following quota metrics exceed quota limits:
aiplatform.googleapis.com/custom_model_training_nvidia_t4_gpus
```

Agent Platform training jobs have their **own GPU quotas**, separate from Compute Engine. The
project had `NVIDIA_T4_GPUS` = 1 (Compute Engine, for VMs we would manage ourselves), but
`custom_model_training_nvidia_t4_gpus` = 0. We asked for 1:

1. Console → *IAM & Admin* → *Quotas & System Limits*
   (https://console.cloud.google.com/iam-admin/quotas?project=tsmmachledata-projet).
2. Filter on `custom_model_training_nvidia_t4_gpus`, tick the row **region : europe-west4**.
3. *Edit quotas*, new value **1**, justification:
   > Master's project (HES-SO MSE, TSM MachLeData): fine-tuning a small NER model
   > (GLiNER2-PII) for PII pseudonymization. One T4 GPU for short training runs.
4. Submit.

The request is free. It was accepted within about 20 minutes: the quota now reads
*Custom model training Nvidia T4 GPUs per region, europe-west4: 1*.

### 5. Create a bucket and upload the script

```sh
gcloud storage buckets create gs://tsm-machledata-anonymizer-training --location=europe-west4
gcloud storage cp scripts/cloud-smoke/train.py gs://tsm-machledata-anonymizer-training/smoke/train.py
gcloud storage ls gs://tsm-machledata-anonymizer-training/smoke/
```

### 6. Choose the PyTorch image

We listed Google's prebuilt PyTorch GPU images:

```sh
gcloud artifacts docker images list europe-docker.pkg.dev/vertex-ai/training --include-tags --filter="package~pytorch-gpu" --format="value(package,tags)"
```

The newest one is `pytorch-gpu.2-4.py310:latest` (PyTorch 2.4, Python 3.10). All of them are
marked *deprecated*, but they still run.

### 7. Launch the job and follow it

```sh
gcloud ai custom-jobs create --region=europe-west4 --display-name=gliner2-smoke --config=scripts/cloud-smoke/job.yaml
gcloud ai custom-jobs stream-logs projects/517094606847/locations/europe-west4/customJobs/<JOB_ID>
```

In the console: *Agent Platform* → *Training* → *Custom jobs*. Check that the region selector
shows **europe-west4**, otherwise the list looks empty.

It took three attempts:

| Job ID | Result | Cause and fix |
|---|---|---|
| `7388277303211458560` | Failed | The current `transformers` needs PyTorch ≥ 2.6, the image has 2.4. Fix: install PyTorch 2.6 first. |
| `4951829904804020224` | Failed | The image's torchvision (0.19) only works with PyTorch 2.4 (`operator torchvision::nms does not exist`). Fix: install torch 2.6.0, torchvision 0.21.0 and torchaudio 2.6.0 together. |
| `4829106814958174208` | **Succeeded** | |

The first attempt waited about 6 minutes for Agent Platform to set up the first job of the
project. Later jobs started much faster. The `pip` warnings about `protobuf`, `pydantic` and
other packages of the image are harmless.

## Results

Successful run on **2026-11-09**, job `4829106814958174208`:

| | |
|---|---|
| Machine | n1-standard-4 + 1 × NVIDIA T4, europe-west4 |
| Data | 900 training rows, 100 test rows |
| Job duration (submitted → completed) | about 13 min (09:54 → 10:07) |
| Script (data, scores, training, saving) | 3.2 min |
| Training (2 epochs, 224 steps, about 18 samples/s) | 2.0 min |
| Training loss, epoch 1 → epoch 2 | 66.7 → 32.1 |
| GPU memory used (out of 16 GB) | 10.5 GB |
| **Recall on the 100 test rows, before → after** | **0.765 → 0.954** |
| Model saved | `gs://tsm-machledata-anonymizer-training/smoke/output/final/` (1.2 GB, 307M parameters), deleted on 2026-11-10 |

Log line printed at the end:

```
SUMMARY {"train_rows": 900, "test_rows": 100, "recall_before": 0.765, "recall_after": 0.954, "train_minutes": 2.0, "total_minutes": 3.2, "gpu_max_memory_gb": 10.5}
```

Most of the job time is spent starting the machine and installing the libraries, not
training.

The recall gain only shows that training works. The 100 test rows come from the same
synthetic dataset as the training rows, and part of the gain probably comes from the model
learning our label names and span boundaries. It is not a result to report.

## Cost

List prices for custom training ([pricing page](https://cloud.google.com/vertex-ai/pricing),
checked on 2026-11-09):

| Resource | USD per hour |
|---|---|
| n1-standard-4 | 0.219 |
| NVIDIA T4 | 0.4025 |
| **Total** | **≈ 0.62** |

| | Estimate |
|---|---|
| Successful run (about 13 min) | ≈ USD 0.13 |
| Whole test, with the two failed attempts (about 10 min each) | ≈ USD 0.30 to 0.40 |
| Storage of the saved model (1.2 GB) | ≈ USD 0.02 per month |
| Real cost of the three jobs of 2026-11-09 (*Billing* -> *Reports*, project `tsmmachledata-projet`, before credits) | **USD 0.20** (T4 0.12, n1-standard-4 0.07, disk 0.01) |

The real cost is lower than the estimate because only the running time of the jobs is billed
(9 + 3 + 6 = 18 min of T4, about USD 0.19 at list price, plus the disk), not the time from
submission to completion. The education credits covered all of it (USD 0.00 after credits).

This is well within our USD 50 of credits. Delete the saved model when it is no longer needed:

```sh
gcloud storage rm -r gs://tsm-machledata-anonymizer-training/smoke/output
```

## Run it again

The account, project, API, quota and bucket are set up. Only these commands are needed:

```sh
gcloud auth list    # check: tsmmachledata@gmail.com
gcloud storage cp scripts/cloud-smoke/train.py gs://tsm-machledata-anonymizer-training/smoke/train.py
gcloud ai custom-jobs create --region=europe-west4 --display-name=gliner2-smoke --config=scripts/cloud-smoke/job.yaml
```
