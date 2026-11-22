# Publish a gated archive

Run publication by hand with the exact archive evaluated by the gate, its MLflow
gate run ID, and the intended target. Use the tracked pipeline gate record,
which includes the training run ID. The CLI checks the active, finished PASS in
the real gate experiment and matches its logged thresholds, frozen T2-dev
SHA-256 and file SHA-256 against the approved `params.yaml`. The linked,
finished training run must have logged the same archive SHA-256.

## Access

Follow the [MLflow deployment guide](gcp-setup.md#mlflow-tracking-and-model-registry).
An MLflow admin creates the required model names once and grants the publishing
login `EDIT` on those names. The login also needs `READ` on the real gate and
training experiments, as the `team` login has. Supply the HTTPS tracking URL and
Basic Auth credentials through `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME`
and `MLFLOW_TRACKING_PASSWORD`.

| Target | Gate profile | Registered models |
| --- | --- | --- |
| `demo` | `demonstration` | `pii-student-demo`, `pii-teacher-demo` |
| `release` | `release` | `pii-student`, `pii-teacher` |

The gate and training runs use the same private GCS bucket. On the publishing
machine, configure Google Application Default Credentials with
`storage.objects.get` and `storage.objects.create` for archives under the
training artifact prefix, and `storage.objects.create` under
`runs/registry-publications/` for reservations. Keep the archive generations
and reservation objects available. Reserve deletion for administrators. The
publisher reads and writes archive bytes directly in GCS.

## Publish

From the repository root, using its trusted experiment configuration, run:

```sh
uv run --locked python -m pii_anonymizer.registry \
  --archive .pipeline/model.tar.gz \
  --gate-run-id "<finished gate run ID>" \
  --model student \
  --target demo
```

For a historical gate, extract the Git-tracked `params.yaml` from the approved
revision with `git show <approved-revision>:params.yaml` and pass that exact
file with `--params`.

The command prints a `models:/<name>/<version>` registry identifier. The version source is
`<training run artifact_uri>/models/<sha256>/`, and the archive is
`model.tar.gz` beneath it. The version records the exact `archive_uri`,
`archive_generation` and `model_sha256` plus the gate and training run IDs and
their respective Git, data and configuration provenance.

Exact retrieval uses `archive_uri` and `archive_generation` together. Read that
generation directly in GCS with `storage.objects.get` and verify
`model_sha256` over the raw bytes. Treat a missing generation or hash mismatch
as a failure. MLflow's ordinary artifact reader resolves the live object.

## Retry

Retry with the same inputs. The command reuses a matching version after verifying
its recorded generation. Before creating a version, the publisher claims
`runs/registry-publications/<registered-model>/<gate-run-id>.json` with a GCS
create-only precondition. An overlapping caller returns the verified version
when available or reports that publication is pending.

If a reservation stays pending, an administrator should check the registry for
the gate run ID and determine from the publisher and MLflow request logs whether
a create was sent or could still finish. When the request is confirmed to have
never reached MLflow or to have failed without creating a version, delete only
that reservation using its generation as the delete precondition, then retry.
Keep the reservation when the outcome is uncertain or a version exists.
