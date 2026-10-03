# QRIS GraphSAGE implementation plan

## Requirements and fit

The hackathon needs an admin-run model that can be tuned and retrained, useful feedback while it runs, results that remain inspectable after leaving the page or restarting services, and a development branch that starts with the normal Docker Compose stack. The `GNN-implementation` branch intentionally uses an active model by default; the first model must meet the held-out baseline gate before auto-promotion, and later candidates require admin promotion.

The earlier plan covered the training controls, a PostgreSQL job row, polling, evaluation, saved candidates, and explicit promotion. Its important gap was execution: FastAPI `BackgroundTasks` run inside the API process. PostgreSQL kept the status, but a process shutdown killed the work and left a permanent `running` row. It also did not give admins a persisted view of previous failures and completed runs after a page reload.

## Revised design

1. The admin API validates bounded training settings and inserts one `queued` job into PostgreSQL. A partial unique index prevents a second active QRIS GraphSAGE job.
2. The internal `gnn-worker` Compose service claims queued or expired jobs in a short transaction using `FOR UPDATE SKIP LOCKED`, records its worker ID, attempt count, and lease, then runs training outside the transaction.
3. The worker renews its lease while loading/training and persists phase, epoch, loss, validation PR-AUC, elapsed time, parameters, and outcome. A graceful stop requeues at the next trainer progress boundary. A crashed worker stops renewing its lease; after expiry another worker reclaims and restarts the deterministic run. Five interrupted attempts end in a visible failed job.
4. Job records and results stay in PostgreSQL. Admin status returns the active job and recent completed/failed history, so polling and reporting work across API workers, browser reloads, and worker restarts.
5. Temporal evaluation builds train-only history. Validation/test payments are one-way query nodes and cannot alter historical node features or message back into history. Evaluation reports GraphSAGE and feature-only logistic-regression metrics on the same split, with class counts, confusion counts, warnings, settings, and best epoch.
6. A successful run writes a signed artifact. If no active version exists, the first run auto-promotes only when test PR-AUC is defined and at least the feature-only baseline. Otherwise, and for every later run, the artifact remains a candidate for explicit admin promotion. Runtime inference defaults on; the legacy ensemble remains fallback.

## What “persistent” means

Queue, settings, progress, attempts, and finished reports survive process/container shutdown because PostgreSQL is the source of truth. Training does not save optimizer/model checkpoints: an interrupted run restarts from epoch one with its stored seed and settings. An already-written candidate is still preserved and signed. This is deliberate for the current hackathon scale; add checkpoint/resume only if runs become long enough that full retries are costly.

## Components and checks

- API and admin ML dashboard: submit, poll, tune, inspect reports, promote.
- `model_training_jobs` migration/model: durable job state, active-job constraint, retry lease.
- `gnn-worker`: database-backed claim/heartbeat/recovery loop; no published port; shares dataset read-only and artifact volume with the API.
- Graph trainer and registry: temporal-safe graphs, validation-PR-AUC early stopping, same-split logistic baseline, signed candidate, explicit active pointer.
- Tests: query-node isolation, feature/label alignment, one-class metrics, candidate promotion, admin API access/polling, lease recovery, and graceful requeue.

Before using this branch, apply Alembic migrations and start the normal Compose stack, which includes `gnn-worker`. Use a representative labeled dataset for any performance claim; synthetic data demonstrates pipeline behavior only.
