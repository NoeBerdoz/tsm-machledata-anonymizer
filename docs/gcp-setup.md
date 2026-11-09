# GCP setup for cloud training

Part of issue #7. This note records the state of the GCP project before the
first fine-tuning run: project, billing, credits, enabled APIs and GPU quota.

Checked on **2026-11-02** in the Google Cloud console. Updated on **2026-11-09**
after the first training run (API, training quota and actions). The steps of that
run are in [cloud-training.md](cloud-training.md).

## Summary

| Item | Value | Status |
|---|---|---|
| Organisation | `tsmmachledata-org` | OK |
| Project | `tsmmachledata-projet` (number `517094606847`) | OK |
| Billing account | Billing Account for Education (paid account) | OK |
| Credits | "MachLeData sep26": **$50.00** left of $50.00, one-time | OK, but small |
| Credit validity | 2026-10-26 → **2027-09-29** | OK |
| Cost so far (Nov 2026) | $0.00 | OK |
| Training service | Agent Platform (formerly Vertex AI), managed training jobs | Decided |
| Region | `europe-west4` (Netherlands) | Decided |
| Target GPU | 1 × NVIDIA T4 (16 GB) or L4 (24 GB) | Decided |
| Compute Engine API | Enabled | OK |
| Vertex AI / Agent Platform API | Enabled on 2026-11-09 | OK |
| Agent Platform training quota (`custom_model_training_nvidia_t4_gpus` / `_l4_gpus`), europe-west4 | T4: 1 since 2026-11-09 (was 0). L4: not requested | OK |
| `NVIDIA_T4_GPUS`, europe-west4 (standard and preemptible) | 1 | OK |
| `NVIDIA_L4_GPUS`, europe-west4 (standard and preemptible) | 1 | OK |
| `GPUS_ALL_REGIONS` (global, Compute Engine) | 0 | Not needed (no VM) |
| Large GPUs (A100, H100, H200, B200), europe-west4 | 0 | Not needed |
| Quota request sent | T4 training quota, 1 GPU, accepted in about 20 min (2026-11-09) | Done |

## Findings

**Training service.** Training runs on **Agent Platform** (formerly Vertex AI)
as managed training jobs, not on a Compute Engine VM we manage ourselves. So the
quotas that matter are the **Agent Platform training quotas**, not the Compute
Engine ones.

**Agent Platform API.** The Vertex AI / Agent Platform API
(`aiplatform.googleapis.com`) was not enabled on 2026-11-02. Without it, training
jobs cannot run and their quotas do not appear in the console. We enabled it on
2026-11-09.

**Region and GPU.** We stay in europe-west4 (Netherlands). T4 and L4 GPUs are
available in zones a, b and c. A small model like GLiNER2-PII does not need a
large GPU: one T4 or one L4 is enough. The A100/H100 quotas are 0 and we do not
plan to request them.

**Compute Engine GPU quota.** `GPUS_ALL_REGIONS` is 0, so no GPU VM can start in
Compute Engine. This does not block managed training jobs. Request
`GPUS_ALL_REGIONS = 1` only if we ever need a GPU VM (e.g. for debugging).

**Budget.** $50 of credits is enough for the short test run of this issue, but
probably not for full teacher fine-tuning and distillation. Keep test runs
small, use the cheapest GPU that works (T4), and set a budget alert.

## Actions

- [x] Enable the Vertex AI / Agent Platform API (`aiplatform.googleapis.com`).
- [x] Check `custom_model_training_nvidia_t4_gpus` / `_l4_gpus` in europe-west4;
      request 1 if it is 0. Record date and status here.
- [ ] Set a budget alert on the billing account (50% and 90% of $50).
- [ ] Later, if we need a GPU VM: request `GPUS_ALL_REGIONS = 1` (Compute Engine).

## How to reproduce the check (console)

Select the project `tsmmachledata-projet` at the top left of
[console.cloud.google.com](https://console.cloud.google.com), then:

1. **Project**: Dashboard → *Project info* card (name, number, ID).
2. **Billing**: ☰ → *Billing* → *Overview* (billing account, cost this month).
   Billing account management → *Your projects* shows which billing account the
   project uses.
3. **Credits**: *Billing* → *Credits* (name, remaining value, start/end date).
4. **APIs**: ☰ → *APIs & Services* → *Enabled APIs & services*. Look for
   *Compute Engine API* and *Vertex AI API* (Agent Platform).
5. **Quotas**: ☰ → *IAM & Admin* → *Quotas & System Limits*. Filter on:
   - `custom_model_training_nvidia_t4_gpus` / `custom_model_training_nvidia_l4_gpus`
     + `europe-west4` (only listed once the Agent Platform API is enabled)
   - `NVIDIA_T4_GPUS` / `NVIDIA_L4_GPUS` + `europe-west4`
   - `GPUS_ALL_REGIONS`

## How to enable the Agent Platform API

☰ → *APIs & Services* → *Library*, search for "Vertex AI" (or "Agent Platform"),
open it and click **Enable**.

## How to request a quota increase

In *IAM & Admin* → *Quotas & System Limits*: filter on the quota, tick the row,
click **Edit quotas**, set the new value (ask for the smallest useful value: 1)
and add a short justification, for example:

> Master's project (HES-SO MSE, TSM MachLeData): fine-tuning a small NER model
> (GLiNER2-PII) for PII pseudonymization. One GPU for short training runs.

Approval can take from a few minutes to several days. Google may also ask for
some billing history on new accounts.

## How to set a budget alert

*Billing* → *Budgets & alerts* → *Create budget*: scope the project
`tsmmachledata-projet`, amount $50, alert thresholds at 50% and 90%, email to
the billing admins.

## After issue #7

- The first training run is done (2026-11-09), see [cloud-training.md](cloud-training.md).
- Its real cost goes in cloud-training.md once the billing report shows it (#27).
- Logging in MLflow moves to v1, when we fine-tune the teacher.
