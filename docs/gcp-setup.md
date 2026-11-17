# GCP setup for cloud training

This note records the state of the GCP project for the first fine-tuning run
(NoeBerdoz/tsm-machledata-anonymizer#7) and the steps to deploy MLflow.

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

## After the first training run

- The first training run is done (2026-11-09), see [cloud-training.md](cloud-training.md).
- Its real cost goes in cloud-training.md once the billing report shows it (NoeBerdoz/tsm-machledata-anonymizer#27).
- Run the MLflow proof below before teacher fine-tuning.

## MLflow tracking and model registry

Deploy NoeBerdoz/tsm-machledata-anonymizer#62 from the clean pull request head in Bash. Work through the numbered steps in order. Repeat the definitions whenever you open a new shell. Verify IAM, CPU quota, TLS issuance and the three client writes during deployment.

Every command uses a gcloud configuration named `tsm-machledata`, so your active configuration never changes. If you do not have it yet, create it once:

```bash
gcloud config configurations create tsm-machledata --no-activate
gcloud --configuration=tsm-machledata auth login tsmmachledata@gmail.com
gcloud --configuration=tsm-machledata config set project tsmmachledata-projet
```

### 1. Set the deployment variables

```bash
gc() { gcloud --configuration=tsm-machledata "$@"; }
remote() { gc compute ssh "$V" --tunnel-through-iap --zone="$Z" --command="$1" -- -T; }
https_rule() { gc compute firewall-rules list --filter='name=mlflow-https' --format='value(name)'; }
P=tsmmachledata-projet A=tsmmachledata@gmail.com R=us-central1 Z=us-central1-a V=mlflow
B=gs://tsmmachledata-projet-mlflow J="mlflow-training@$P.iam.gserviceaccount.com"
D="$HOME/.config/tsm-mlflow" REV=$(git rev-parse HEAD) DOMAIN=${DOMAIN:-sslip.io}
IP=$(gc compute addresses describe mlflow-ip --region="$R" --format='value(address)' 2>/dev/null) || IP=
DNS=${IP:+${IP//./-}.$DOMAIN} URI=${IP:+https://$DNS}
```

### 2. Enable APIs and create the VM and bucket

Before provisioning, check Billing for another `e2-micro` using this account’s shared Free Tier. Outside the allowance, the Iowa VM is about $6.11 for 730 hours, plus any paid disk usage. [Free Tier](https://docs.cloud.google.com/free/docs/free-cloud-features#compute), [Iowa VM pricing](https://cloud.google.com/products/compute/pricing/general-purpose).

```bash
test "$(gc config get-value core/account)" = "$A" &&
  test "$(gc config get-value core/project)" = "$P" &&
  gc services enable compute.googleapis.com iap.googleapis.com iam.googleapis.com \
    secretmanager.googleapis.com storage.googleapis.com aiplatform.googleapis.com &&
  (gc compute networks describe mlflow-net >/dev/null 2>&1 ||
    gc compute networks create mlflow-net --subnet-mode=auto) &&
  (gc compute addresses describe mlflow-ip --region="$R" >/dev/null 2>&1 ||
    gc compute addresses create mlflow-ip --region="$R")
```

Repeat step 1 to read back the reserved IPv4. Then create the VM and bucket.

```bash
# Keep the boot disk when the VM is deleted.
test -n "$IP" &&
  (gc compute instances describe "$V" --zone="$Z" >/dev/null 2>&1 ||
    gc compute instances create "$V" --zone="$Z" --network=mlflow-net --tags=mlflow \
      --machine-type=e2-micro --image-family=debian-12 --image-project=debian-cloud \
      --boot-disk-type=pd-standard --boot-disk-size=30GB --no-boot-disk-auto-delete \
      --address="$IP" --no-service-account --no-scopes) &&
  (gc storage buckets describe "$B" >/dev/null 2>&1 ||
    gc storage buckets create "$B" --location=europe-west4 --default-storage-class=STANDARD \
      --uniform-bucket-level-access --public-access-prevention)
```

### 3. Allow SSH through IAP

The IAM condition limits the tunnel to this VM and port 22. If a recreated VM has a different internal IP, remove the exact saved grant before recording and granting the new one. The firewall uses [Google’s IAP TCP forwarding range](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding#create-firewall-rule).

```bash
LAN=$(gc compute instances describe "$V" --zone="$Z" \
  --format='value(networkInterfaces[0].networkIP)') &&
  test -n "$LAN" &&
  IAP_EXPRESSION="destination.port == 22 && destination.ip == '$LAN'" &&
  (
    umask 077
    mkdir -p "$D" && chmod 700 "$D" || exit 1
    if [[ -e "$D/iap-condition" ]]; then
      IFS= read -r previous < "$D/iap-condition" && test -n "$previous" || exit 1
      if [[ $previous != "$IAP_EXPRESSION" ]]; then
        grants=$(gc projects get-iam-policy "$P" --flatten='bindings[].members' \
          --filter="bindings.role='roles/iap.tunnelResourceAccessor' AND bindings.members='user:$A' AND bindings.condition.title='mlflow-ssh'" \
          --format='value(bindings.condition.expression)') || exit 1
        if [[ $'\n'$grants$'\n' == *$'\n'"$previous"$'\n'* ]]; then
          gc projects remove-iam-policy-binding "$P" --member="user:$A" \
            --role=roles/iap.tunnelResourceAccessor \
            --condition="title=mlflow-ssh,expression=$previous" --quiet || exit 1
        fi
      fi
    fi
    temp=$(mktemp "$D/.iap-condition.XXXXXX") &&
    printf '%s\n' "$IAP_EXPRESSION" > "$temp" && mv -- "$temp" "$D/iap-condition") &&
  gc projects add-iam-policy-binding "$P" --member="user:$A" --role=roles/iap.tunnelResourceAccessor \
    --condition="title=mlflow-ssh,expression=$IAP_EXPRESSION" &&
  (gc compute firewall-rules describe mlflow-iap >/dev/null 2>&1 ||
    gc compute firewall-rules create mlflow-iap --network=mlflow-net --target-tags=mlflow \
      --allow=tcp:22 --source-ranges=35.235.240.0/20)
```

### 4. Make the passwords and grant job access

Generate the four passwords in mode-0600 files outside the checkout. Keep the admin password in Noé’s password manager. Keep the current files for reruns.

```bash
(
  umask 077
  set -o pipefail
  mkdir -p "$D" && chmod 700 "$D" || exit 1
  for u in admin team training actions; do
    test -s "$D/$u.pass" || openssl rand -hex 32 | tr -d '\n' > "$D/$u.pass" || exit 1
    chmod 600 "$D/$u.pass" || exit 1
  done
)
```

The job reads its secret and the named objects under `proof/`. It can create artifacts under `runs/`. The secret and its first version have separate checks so this step can resume after the secret is created. Remove any older unconditional bucket grants for this service account before using these bindings. [Cloud Storage IAM conditions](https://docs.cloud.google.com/storage/docs/access-control/iam#conditions).

```bash
OBJECTS="projects/_/buckets/${B#gs://}/objects"
(gc iam service-accounts describe "$J" >/dev/null 2>&1 ||
  gc iam service-accounts create mlflow-training) &&
  gc iam service-accounts add-iam-policy-binding "$J" --member="user:$A" \
    --role=roles/iam.serviceAccountUser &&
  (gc secrets describe mlflow-training-password >/dev/null 2>&1 ||
    gc secrets create mlflow-training-password --replication-policy=automatic) &&
  VERSION=$(gc secrets versions list mlflow-training-password --limit=1 --format='value(name)') &&
  { [[ -n $VERSION ]] || gc secrets versions add mlflow-training-password \
    --data-file="$D/training.pass"; } &&
  gc secrets add-iam-policy-binding mlflow-training-password --member="serviceAccount:$J" \
    --role=roles/secretmanager.secretAccessor &&
  gc storage buckets add-iam-policy-binding "$B" --member="serviceAccount:$J" \
    --role=roles/storage.objectViewer \
    --condition="title=read-proof,expression=resource.name.startsWith('$OBJECTS/proof/')" &&
  gc storage buckets add-iam-policy-binding "$B" --member="serviceAccount:$J" \
    --role=roles/storage.objectCreator \
    --condition="title=create-runs,expression=resource.name.startsWith('$OBJECTS/runs/')"
```

### 5. Install MLflow and open HTTPS

Check that any existing firewall rules match the settings in this guide. The installer uses the hashed server export and takes the passwords over IAP SSH stdin. MLflow runs with one worker and Basic Auth on loopback. Caddy for a new install starts after the installer reports success. Keep port 80 closed.

```bash
# Use the pinned server group with hashes from uv.lock.
test -n "$DNS" &&
  uv export --only-group mlflow-server --locked -o "$D/mlflow-server-requirements.txt" &&
  remote 'mkdir -p "$HOME/mlflow-setup"' &&
  gc compute scp --tunnel-through-iap --zone="$Z" \
    ops/mlflow/{install.sh,mlflow.service,Caddyfile} "$D/mlflow-server-requirements.txt" \
    "${V}:~/mlflow-setup/" &&
  RULE=$(https_rule) &&
  { if [[ -n $RULE ]]; then HTTPS_STATE=open; else HTTPS_STATE=closed; fi; } &&
  (set -o pipefail; awk 1 "$D"/{admin,team,training,actions}.pass |
    remote "sudo bash ~/mlflow-setup/install.sh '$DNS' '$HTTPS_STATE'") &&
  (gc compute firewall-rules describe mlflow-https >/dev/null 2>&1 ||
    gc compute firewall-rules create mlflow-https --network=mlflow-net --target-tags=mlflow \
      --allow=tcp:443 --source-ranges=0.0.0.0/0) &&
  remote 'if sudo systemctl is-active --quiet caddy; then sudo systemctl reload caddy; else sudo systemctl enable --now caddy; fi'
```

The installer rotates the admin password before opening HTTPS and checks the experiment grants. Each login can edit its own experiment. The `team` login also reads `tsm-training` and `tsm-gates`. Admin creates experiments and registered models in the default workspace.

Caddy obtains and renews the certificate using TLS-ALPN-01 on TCP 443. Wait for trusted HTTPS and a 401 for anonymous tracking access.

```bash
status=
for attempt in {1..30}; do
  status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 \
    --header 'Content-Type: application/json' --data '{}' \
    "$URI/api/2.0/mlflow/experiments/search") || status=
  if [[ $status == 401 ]]; then break; fi
  sleep 3
done
test "$status" = 401
```

### 6. Run the three proofs

Check the smoke image and CPU quota in `europe-west4` before submitting this billable job. It uses one CPU-only `n1-standard-4` and a 600-second limit. It downloads three named objects and reads its Secret Manager password as the job service account. The job name includes the commit so a rerun can reuse an active or successful submission.

```bash
JOB="mlflow-proof-$REV"
(
  set -o pipefail
  for f in src/pii_anonymizer/tracking.py params.yaml data/test/t2_pilot.jsonl.dvc; do
    git cat-file -e "$REV:$f" &&
      git show "$REV:$f" | gc storage cp - "$B/proof/$REV/${f##*/}" || exit 1
  done
) &&
  JOB_IDS=$(gc ai custom-jobs list --region=europe-west4 --format='value(name)' \
    --filter="displayName=$JOB AND NOT state:(JOB_STATE_FAILED JOB_STATE_CANCELLED JOB_STATE_EXPIRED)") &&
  if [[ -n $JOB_IDS ]]; then
    printf '%s\n' "$JOB_IDS"
  else
    gc ai custom-jobs create --region=europe-west4 --display-name="$JOB" \
      --service-account="$J" --config=ops/mlflow/proof-job.yaml --args="$REV,$URI"
  fi
```

Give a teammate the HTTPS URL and share the `team` password through the password manager. They use a clean checkout of the same commit and a local mode-0600 password file.

```bash
(
  export MLFLOW_TRACKING_URI='<tracking HTTPS URL>' MLFLOW_TRACKING_USERNAME=team
  MLFLOW_TRACKING_PASSWORD=$(cat "$HOME/.config/tsm-mlflow/team.pass") || exit 1
  export MLFLOW_TRACKING_PASSWORD
  uv run --locked python -m pii_anonymizer.tracking laptop "$(git rev-parse HEAD)"
)
```

Set both Actions secrets before opening, updating, reopening or marking the same-repository PR ready. Remove the old URI repository variable if it exists. Changes to the MLflow ops or workflow files trigger the exact PR head. Keep the PR open for review. Manual dispatch becomes available after the workflow reaches the default branch. [GitHub Actions events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request).

```bash
test -n "$URI" &&
  gh secret set MLFLOW_TRACKING_PASSWORD --repo NoeBerdoz/tsm-machledata-anonymizer < "$D/actions.pass" &&
  printf '%s' "$URI" | gh secret set MLFLOW_TRACKING_URI --repo NoeBerdoz/tsm-machledata-anonymizer
```

The proof prints experiment and run IDs. Open the matching runs in MLflow and keep the UI links privately. Check `connectivity=1`, the full commit SHA, each DVC path and hash, the parsed experiment parameters and the raw-file SHA-256.

### 7. Check the registry and restart

As admin, create `connectivity-proof` and set its `training_run_id` tag to the training proof’s run ID.

```bash
gc compute instances stop "$V" --zone="$Z" &&
  gc compute instances start "$V" --zone="$Z"
```

After boot, check the three run IDs, the registry tag and the grants. The `team` login should see all three runs. Each job login should see its own experiment only.

### Cost and recovery

| Resource | Estimated USD for 30 days |
|---|---|
| Iowa VM and disk | $0 within the shared Free Tier for the VM and 30 GB-month standard disk. [Free Tier](https://docs.cloud.google.com/free/docs/free-cloud-features#compute) |
| Static IPv4 | About $3.60 for 720 hours, including time attached to a stopped VM. [Network pricing](https://cloud.google.com/vpc/network-pricing#ipaddress) |
| European Cloud Storage | About $0.10 for 5 GiB-month of Standard storage, plus operations and downloads. [Storage pricing](https://cloud.google.com/storage/pricing) |
| Secret Manager and TLS | $0 within six secret versions and 10,000 accesses per month. Let’s Encrypt certificates are free. [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing), [Let’s Encrypt](https://letsencrypt.org/) |
| Total | About $3.70 before variable charges, optional snapshots and the one-off CPU proof, against $50 in credits. |

If the auth database is missing, run `bash ops/mlflow/teardown.sh --close-https` before restoring it or rerunning step 5. This closes ingress and stops Caddy. Step 5 reopens ingress after the installer succeeds.

Keep the boot disk and Caddy’s state across restarts. For a Let’s Encrypt limit, honor `Retry-After`. For a shared domain limit, set `DOMAIN=nip.io`, repeat step 1, rerun step 5 and update the client URLs and Actions secret. One DNS operator serves both names. If memory is tight, serialize writes and price an `e2-small` if needed. [Let’s Encrypt limits](https://letsencrypt.org/docs/rate-limits/), [DNS operator](https://nip.io/).

### Optional daily backups

Recommended because the registry and tracking database are the O5 record. Same-region Standard snapshots are incremental and cost about $0.05 per billed GiB-month, or $0.25 for a 5 GiB average. The policy takes a daily snapshot at 04:00 UTC and keeps it for seven days. [Snapshot pricing](https://cloud.google.com/compute/disks-image-pricing#disk).

```bash
(gc compute resource-policies describe mlflow-daily --region="$R" >/dev/null 2>&1 ||
  gc compute resource-policies create snapshot-schedule mlflow-daily --region="$R" \
    --daily-schedule --start-time=04:00 --max-retention-days=7 --storage-location="$R" \
    --on-source-disk-delete=apply-retention-policy) &&
  POLICIES=$(gc compute disks describe "$V" --zone="$Z" --format='value(resourcePolicies)') &&
  { [[ $POLICIES == *"/mlflow-daily"* ]] ||
    gc compute disks add-resource-policies "$V" --zone="$Z" --resource-policies=mlflow-daily; }
```

### Teardown

Export the O5 evidence, keep any needed model files and cancel active proof jobs. Run `bash ops/mlflow/teardown.sh`, then check Billing for any remaining snapshots and soft-deleted objects.
