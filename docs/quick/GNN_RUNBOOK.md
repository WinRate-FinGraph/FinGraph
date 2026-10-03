# QRIS GNN Runbook

On the `GNN-implementation` branch, GraphSAGE inference is enabled by default when an active artifact is available. Missing artifacts and inference errors safely use the legacy scoring path. The included benchmark is synthetic and does not establish real-world QRIS detection quality.

## Generate the synthetic benchmark

The repository includes a reproducible generator. It uses aggregate calibration values only; it does not copy source rows or identities:

```bash
cd backend
python -m app.ml.synthetic_qris \
  --rows 50000 \
  --seed 42 \
  --output ./datasets/generated-qris
```

The output contains `qris_payments.csv`, `qris_ground_truth.csv`, `dataset_manifest.json`, and `SHA256SUMS`. The small, reviewed v2 benchmark is also checked into the dataset branch at `datasets/synthetic-qris-v2/`; keep downloaded reference data and model artifacts outside Git.

The default benchmark contains 50,000 rows over roughly six months, about 10% synthetic fraud-like labels, 8,984 payers, 250 merchants, 500 outlets/QRIS profiles, 6,090 devices, and 8 PJPs. Fraud typologies are shared-device rings, velocity bursts, merchant hopping, amount anomalies, and cross-border clusters. These labels are generated test scenarios, not observed QRIS incidents.

## Mount data

With the local production env, the generated files live in the configured
dataset directory on the host; the backend sees them as `/app/data/raw/qris`.
For another host, set `QRIS_GNN_HOST_DATA_DIR` and keep
`QRIS_GNN_DATA_DIR=/app/data/raw/qris`. Do not commit downloaded reference
data or model artifacts. The adapter accepts aliases for `payment_id`,
`timestamp`, `payer_id`, `merchant_id`, `outlet_id`, `qris_id`, `amount`,
`payment_status`, and `label`. Optional columns include device, PJP, region,
and country identifiers. Labels map `fraud`/`illicit`/`1` to fraud and
`legitimate`/`licit`/`0` to legitimate.

## Train

Apply the Alembic migration with the repository's normal `migrate` deployment step before starting this version; it creates the persisted training-job table.

Docker Compose starts `gnn-worker` on the internal network only, sharing the read-only dataset mount and ML artifact volume with the API. It publishes no port.

```bash
curl -X POST 'http://127.0.0.1:8080/api/v1/ml/train/qris-graphsage?epochs=10&limit_rows=50000&hidden_dim=64&learning_rate=0.003&dropout=0.2&weight_decay=0.0001&patience=5&seed=42' \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

The admin endpoint returns `202` and a `job_id`. Poll it for phase, epoch, training loss, validation PR-AUC, and elapsed time:

```bash
curl http://127.0.0.1:8080/api/v1/ml/graphsage/jobs/$JOB_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

The same settings are editable in the Indonesian admin ML dashboard. PostgreSQL stores the queue, settings, progress, retries, and result. The internal `gnn-worker` service claims jobs with a database lock and renewable lease; graceful shutdown requeues the run, while a crash lets another worker retry it after the lease expires. Retries restart the deterministic run from the beginning (optimizer checkpoints are not stored), up to five attempts. Only one QRIS GraphSAGE job may be queued/running. If there is no active model, the first completed run is auto-promoted only when test PR-AUC is defined and at least the feature-only logistic-regression baseline. Otherwise it remains a candidate for admin review. Later runs remain candidates and require explicit promotion from the dashboard or:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/ml/graphsage/$VERSION/promote \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Training uses a temporal split when every row has a timestamp. Validation and test payments are one-way query nodes: they receive messages from historical graph nodes but cannot update historical entity features or send messages back. Test sees training and validation history, never later test rows. Missing timestamps trigger a seeded random split and the warning `timestamps_missing_random_split_not_production_evidence`. Both training and validation must contain both labels; a one-class test split reports undefined AUCs and a warning. The decision threshold is selected by validation F1, then reused unchanged on the test split; it is not forced to `0.5`.

Synthetic scores validate the pipeline and known synthetic scenarios only; they are not evidence of real-world QRIS fraud performance.

## Inspect and enable

```bash
curl http://127.0.0.1:8080/api/v1/ml/graphsage/status \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Set these variables, then restart the backend:

```text
QRIS_GNN_ENABLED=true
QRIS_GNN_BLEND_WEIGHT=0.50
QRIS_GNN_MAX_NODES=500
```

`QRIS_GNN_BLEND_WEIGHT` is the GNN share of the final base score (default `0.50`), not a share inside the graph term. Rules still impose critical floors. Missing artifacts or inference errors report a fallback reason and use the legacy ensemble.

This branch defaults `QRIS_GNN_ENABLED=true`. A fresh artifact volume still needs a training run before GraphSAGE can contribute. The ML dashboard shows whether the active transaction path actually used GNN or fell back. Existing local `.env` values override repository defaults.

## Judge answer

“We implemented a QRIS-specific GraphSAGE path with temporal evaluation, signed artifacts, bounded neighborhood inference, and a legacy fallback. In this demo branch it contributes half of the risk score when an active artifact is available. The benchmark is synthetic, so these metrics show the pipeline and generated scenarios—not real-world QRIS accuracy.”
