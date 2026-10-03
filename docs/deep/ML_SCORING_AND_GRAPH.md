# ML, Scoring, and Graph Deep Dive

## Executive truth

FinGraph contains multiple model experiments, but the QRIS MVP is safe without any trained artifact. Its live default is deterministic rules plus a PostgreSQL-derived graph heuristic. Optional logistic-regression and QRIS GraphSAGE artifacts can enrich the score. FedAvg remains a prototype.

## QRIS features

`build_behavior_features()` produces 22 numeric features:

- amount, expected amount, difference, and ratio;
- payment hour and callback delay;
- payment count in 10 minutes and failures in 30 minutes;
- payer transaction, fraud-label, and suspicious-label counts;
- merchant average and normalized amount deviation;
- new-payer, duplicate-reference, cross-region, and cross-border flags;
- merchant and outlet risk encodings;
- QRIS profile match;
- order age;
- payment velocity.

Features are built from the current payment plus PostgreSQL history. They are stored inside `scoring_explanation` for explainability and optional adaptive training.

## Deterministic rule layer

Each rule returns:

- stable code;
- human-readable Indonesian reason;
- contribution between `0` and `1`;
- severity;
- recommended action.

Critical/high rules include:

| Rule | Meaning | Contribution | Floor |
|---|---|---:|---:|
| `CALLBACK_NOT_FOUND` | Claimed paid without provider confirmation | 0.95 | 0.90 |
| `PAYMENT_NOT_SUCCESS` | Claimed paid but provider status is not success | 0.90 | 0.90 |
| `AMOUNT_MISMATCH` | Paid and expected amounts differ by at least Rp1 | 0.95 | 0.90 |
| `DUPLICATE_PROVIDER_REFERENCE` | Reference reuse | 0.92 | 0.90 |
| `MERCHANT_ID_MISMATCH` | Callback merchant does not match | 0.98 | 0.90 |
| `OUTLET_MISMATCH` | Callback outlet does not match | 0.95 | 0.90 |
| `QR_FINGERPRINT_MISMATCH` | Stored QR fingerprint does not match | 0.95 | 0.90 |
| `CALLBACK_REPLAY` | Timestamp/replay signal | 0.90 | 0.90 |
| `PAYMENT_REVERSED_AFTER_PROCESSING` | Reversal after fulfillment | 0.88 | 0.75 |

Medium signals include delayed callback, repeated failures, and rapid micro-transactions. Cross-border and cross-region are low-severity context only.

If no suspicious condition exists, `PAYMENT_VERIFIED` contributes `0.08`.

## Graph heuristic

For the payer pseudonym, the backend calculates:

- number of connected payments;
- number of distinct connected merchants;
- connected alert count;
- count and ratio of fraud-labeled neighbor payments.

The score is:

```text
0.04
+ min(degree, 20) × 0.01
+ min(merchant_count, 5) × 0.05
+ min(alert_count, 5) × 0.10
+ fraud_neighbor_ratio × 0.45
```

It is capped at `0.99`. The `suspicious_network` demo scenario enforces at least `0.86`.

This is transparent and useful for a demo, but it is not a learned GNN. It also performs several per-payment SQL queries, which is acceptable for MVP volume but should be replaced with aggregated features or a feature store at high throughput.

## Optional tabular model

`train_qris_demo_model()` creates 1,200 deterministic synthetic samples by default. Fraud labels are generated from amount mismatch, duplicate reference, repeated failures, and high small-payment velocity. A balanced logistic regression trains on an 80/20 stratified split.

Artifact dataset name: `qris_demo`.

When present, its `predict_proba()` result contributes 30% of the QRIS ensemble. When absent or invalid, scoring returns `None` and continues.

## Optional adaptive QRIS model

Labels accepted for binary training are `fraud` and `legitimate`; `suspicious` contributes to status counts but not the binary training rows.

Readiness requires:

- at least `QRIS_ADAPTIVE_MIN_LABELS` usable labels;
- at least one fraud label;
- at least one legitimate label;
- stored feature payload on enough payments.

The prototype fits balanced logistic regression on all available rows and reports training-set metrics. Those metrics are optimistic and must not be presented as held-out performance.

Artifact dataset name: `qris_adaptive`.

## Ensemble and floors

```text
legacy_score = rule_score × 0.35
             + tabular_score × 0.30
             + graph_heuristic × 0.25
             + adaptive_score × 0.10

base_score = GraphSAGE × 0.50 + legacy_score × 0.50  # if GNN inference succeeds
base_score = legacy_score                         # otherwise
```

A missing optional legacy score contributes zero rather than re-normalizing its weights. The final score is the greater of `base_score` and the strongest severity floor, clamped to `0..1`. The effective GNN weight and `legacy_ensemble_score` are included in the scoring explanation.

Implication: fallback-mode scores are intentionally conservative and not probability calibrated. A verified normal payment can have a low numerical score because absent artifacts contribute zero. That is acceptable because the score is a risk index, not a probability.

## Recommendations

- Graph score at least `0.75`: `REPORT_AND_HOLD`.
- High risk: `DO_NOT_RELEASE_GOODS`.
- Medium with missing/failed callback: `HOLD`.
- Other medium: `VERIFY`.
- Low: `APPROVE`.

Frontend presentation applies additional consistency guards so an unsafe provider status cannot appear as safe even if stale data contains an inconsistent recommendation.

## Confidence

Available signal scores are collected and population standard deviation is measured:

```text
agreement = 1 - min(pstdev(signals) × 2, 1)
confidence = 0.55 + agreement × 0.45
```

Severity sets minimum confidence of `0.78` for medium, `0.90` for high, and `0.95` for critical.

This confidence means signal consistency. It is not classification accuracy, precision, recall, uncertainty calibration, or probability of fraud.

## Artifact registry and integrity

Artifacts are serialized with `joblib`, accompanied by JSON metrics, and signed with HMAC-SHA256. Loading verifies:

- artifact file exists and is not a symlink;
- signature file exists;
- HMAC matches;
- requested model path remains directly inside configured artifact directory;
- extension is `.joblib`.

This protects against accidental or unauthorized artifact replacement when the signing key is protected. It does not make Python pickle/joblib safe for untrusted third-party files.

## Other model pipelines

### PaySim

`train_paysim.py` expects a public PaySim CSV. It engineers balance deltas and ratios, one-hot encodes transaction type, and trains either:

- XGBoost with class weighting; or
- balanced logistic regression.

The legacy transaction API maps its entities into PaySim-like features. These inferred balances are synthetic approximations, not observed bank balances.

### Internal adaptive legacy model

`train_fingraph.py` learns from labels attached to legacy generic transactions using a random forest pipeline. For fewer than 20 samples, it evaluates on its training set with an explicit warning.

### Baseline random forest

`baseline_model.py` trains labels derived from an existing rule score threshold. Because its target is generated from the rule it is meant to complement, it demonstrates plumbing rather than independent fraud ground truth.

## QRIS GraphSAGE path

`app/ml/graph/` is the dataset-independent QRIS graph path. It accepts CSV data through a canonical adapter, keyed-HMAC pseudonymizes identifiers, and builds payment/entity relationships without storing raw IDs in the artifact.

The preferred graph is heterogeneous: payment, payer, merchant, outlet, QRIS, device, PJP, region, and country nodes. If typed IDs are missing, the adapter uses one homogeneous fallback graph and records that mode in the artifact. Splits are temporal when timestamps exist; otherwise training continues with an explicit random-split warning.

Training is an admin-only queued job. PostgreSQL stores its configuration, progress, retries, result, and status; the internal `gnn-worker` claims jobs with a lease and retries after worker restart:

```text
POST /api/v1/ml/train/qris-graphsage?epochs=10
GET  /api/v1/ml/graphsage/jobs/{job_id}
```

The trainer reports phase, epoch, loss, validation PR-AUC, and elapsed time. Completed jobs report train/validation/test metrics beside a feature-only logistic-regression baseline. The default QRIS run uses 10 epochs with early stopping patience 5. The decision threshold is selected for F1 on validation data and then reused for the untouched test split; it is not forced to `0.5`. Each artifact contains model state, feature/relation schema, split strategy, settings, and metrics, and is signed by the existing registry. If no active model exists, the first completed run auto-promotes only when test PR-AUC is defined and at least the feature-only baseline; otherwise it remains a candidate for admin review. Later runs always remain candidates. On `GNN-implementation`, runtime inference defaults on and a bounded PostgreSQL ego-neighborhood is scored when an active `qris_graph` artifact exists. `QRIS_GNN_BLEND_WEIGHT` (default `0.50`) is the GNN share of the final base score; the other half is the legacy ensemble. Critical rule floors remain unchanged, and missing/failed GNN inference falls back to the legacy ensemble.

The status endpoint distinguishes QRIS and legacy Elliptic artifacts. The UI reports enabled state separately from whether a usable active artifact is available. The benchmark is synthetic, so its held-out scores are not real-world QRIS accuracy evidence.

For the hackathon benchmark, `app/ml/synthetic_qris.py` generates deterministic QRIS-like payments from explicit graph-fraud scenarios. It samples amounts, time-of-day, weekday, customer activity, and store activity from aggregate statistics in the simulated Indonesian retail dataset's QRIS subset. MoMTSim, MS-FFSD, and AMLNet are schema/design references only; their rows and fraud labels are not used. The generated ground truth is synthetic and must be reported as engineering evidence, never as real-world QRIS accuracy.

## Legacy Elliptic GraphSAGE prototype

`train_elliptic_graphsage.py` implements two manual mean-aggregation GraphSAGE layers in PyTorch, followed by a two-class linear classifier.

It uses:

- Elliptic transaction features and edges;
- licit/illicit labeled nodes;
- standard scaling;
- class-stratified random splits;
- weighted cross-entropy;
- AdamW;
- validation-F1 model selection;
- ROC-AUC, PR-AUC, precision, recall, F1, confusion matrix, and classification report.

Important limitations:

1. Elliptic represents cryptocurrency transactions, not Indonesian QRIS.
2. Random node splitting can leak temporal/network context; a temporal split is more realistic.
3. Adjacency aggregation loops through Python lists, so it is not suitable for a large production graph.
4. It remains separate from the QRIS artifact path and is not used for QRIS inference.
5. It is a historical feasibility experiment, not QRIS evidence.

Correct presentation: “QRIS has a dataset-independent GraphSAGE training and inference path. This demo branch uses an active model by default, with a legacy scoring fallback. Evaluation currently uses synthetic labeled scenarios and does not establish real-world QRIS accuracy.”

## Federated learning prototype

FedAvg calculation for parameter index `j` is:

```text
global[j] = sum(local_node[j] × node_sample_count) / total_sample_count
```

Current local updates are deterministic synthetic offsets, not weights trained on local datasets. A demo metric increases according to node diversity/sample count; it is not measured validation performance.

Missing production pieces include local training agents, Flower, authenticated rounds, secure aggregation, update validation, poisoning defense, differential privacy, dropout handling, model-version negotiation, and governance.

## Evaluation evidence

Tests verify score range, critical floors, cross-region non-escalation, fallback without artifacts, confidence behavior, graph limits, and FedAvg arithmetic. They verify implementation invariants, not real-world fraud-detection effectiveness.

Real evaluation should use temporally split, representative data and report at least PR-AUC, recall at an acceptable false-positive rate, precision at operational review capacity, calibration, latency, drift, and subgroup/merchant stability.
