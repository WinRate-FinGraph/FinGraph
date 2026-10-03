# Synthetic QRIS-like dataset v2

## What this is

This is a reproducible, scenario-based dataset for developing and demonstrating FinGraph's QRIS graph-learning pipeline. It is **not real QRIS data**, and its fraud labels are not evidence about actual QRIS fraud.

Version 2 improves the earlier prototype by sampling amounts, transaction hours, weekdays, customer activity, and merchant activity from aggregate statistics in an Indonesian retail dataset's QRIS subset. That source dataset is itself simulated. We use it as a local retail-shaped reference, not as observed banking behavior. The generator copies no source rows, customer IDs, or store IDs.

Fraud patterns remain hand-designed scenarios. The default positive-label rate is 10% so the demo has enough examples of both classes; this is a test setting, **not an estimate of QRIS fraud prevalence**. The scenarios include shared-device groups, short transaction bursts, merchant hopping, amount anomalies, and cross-border activity. Some benign transactions also have these signals, and some labeled scenarios lack their obvious signal, so no single field is intended to identify every label.

## Files in this folder

- `qris_payments.csv`: 50,000 timestamp-sorted payment rows; generator seed `42`.
- `qris_ground_truth.csv`: matching labels and simulator-only typology for each payment.
- `dataset_manifest.json`: row counts, entity counts, label mix, provenance, limitations, and SHA-256 hashes.
- `SHA256SUMS`: checksums for both CSV files.

Each generated file is under the Git server's 50 MB per-file limit. Do not add the downloaded reference datasets here.

## Column reference

| Column | Type in CSV | Meaning |
|---|---|---|
| `payment_id` | text | Unique generated payment identifier. |
| `timestamp` | text | Local synthetic event time, `YYYY-MM-DD HH:MM:SS`, with no timezone. |
| `payer_id` | text | Generated payer node; names carry no risk code. |
| `merchant_id` | text | Generated merchant node. |
| `outlet_id` | text | Generated outlet node, two per merchant. |
| `qris_id` | text | Generated QRIS profile, one per outlet. |
| `amount` | integer IDR | Payment amount in Indonesian rupiah. |
| `payment_status` | category | `success`, `failed`, or `reversed`. |
| `label` | integer | `0` baseline, `1` injected test scenario. Model target, not an input feature. |
| `device_id` | text | Generated device node; some devices connect multiple payers. |
| `pjp_id` | text | One of eight generated payment-provider IDs. |
| `source_region` | text | Synthetic payer-side region; may use `foreign_region_<country>`. |
| `source_country` | text | `ID` or synthetic foreign code (`MY`, `SG`, `TH`, `AU`, `US`). |
| `destination_region` | text | Generated merchant-side Indonesian region. |
| `destination_country` | text | Always `ID` in this prototype. |

`qris_ground_truth.csv` contains `payment_id`, `label`, and `typology`. Typology values are `legitimate_baseline`, `shared_device_ring`, `velocity_burst`, `merchant_hopping`, `amount_anomaly`, and `cross_border_cluster`. Typology is deliberately kept out of the payment features.

## How each label is assigned

The generator does **not** inspect a payment and decide afterward whether it looks fraudulent. It assigns labels by construction:

1. It calculates `round(number_of_rows × fraud_rate)` and uses the seeded random number generator to choose that many payment rows.
2. Chosen rows get `label=1`; every other row gets `label=0`.
3. Each `label=1` row receives one test typology, sampled using the configured weights: shared-device ring 28%, velocity burst 25%, merchant hopping 20%, amount anomaly 17%, cross-border cluster 10%.
4. The generator creates transaction attributes and graph connections for that typology. It also gives some `label=0` rows overlapping signals—for example, shared devices, cross-region activity, unusual amounts, and foreign sources.

So `label=1` means **injected synthetic scenario**, not confirmed fraud. `label=0` means **synthetic baseline control**, not verified genuine payment. A row's label comes from the generator's selected index, not from its amount, status, country, the reference data, or a trained model. The seed makes the selection and generated values reproducible.

For the checked-in 50,000-row dataset, `round(50,000 × 0.10)` gives 5,000 positive scenario rows and 45,000 baseline rows.

Use `label` in `qris_payments.csv` as the training target. Match `payment_id` to `qris_ground_truth.csv` to inspect the simulator-only typology. Do not pass `typology` to the model as a feature.

## Calibration and assumptions

The default calibration profile is [`../../docs/data/synthetic_qris_calibration.json`](../../docs/data/synthetic_qris_calibration.json). It contains aggregates from 6,116 QRIS-method rows in the CC0 [Retail Indonesia Omnichannel Sales dataset](https://www.kaggle.com/datasets/lycusbendln/indonesian-retail-sales-and-cost-dataset): amount quantiles, hour and weekday counts, customer transaction-frequency counts, and store transaction counts. The reference subset has 4,274 customers and 16 stores. Source IDs and rows are not retained in the profile.

The generator uses those aggregates to sample baseline values. It manually chooses 250 synthetic merchants, two outlets per merchant, eight providers, device sharing, and the fraud scenarios. Only source schema and design ideas—not rows or labels—from MoMTSim, MS-FFSD, and AMLNet are recorded as secondary references. Their fraud rates are not transferred to this dataset.

The model adapter uses the `label` column as target, four payment features (`amount`, status, region mismatch, country mismatch), and entity links as graph structure. The label and sidecar typology are not model features.

## Recreate or recalibrate

From the repository root:

```bash
cd backend
python -m app.ml.synthetic_qris \
  --calibrate-from /path/to/reference/retail_indonesia_55k.csv
python -m app.ml.synthetic_qris \
  --rows 50000 --seed 42 --output ../datasets/synthetic-qris-v2
```

Calibration stores aggregate statistics only. Generation is deterministic for a fixed seed and profile. Use `--fraud-rate 0.05` to change the synthetic label fraction; it does not change what the labels mean.

To verify files:

```bash
cd ../datasets/synthetic-qris-v2
sha256sum -c SHA256SUMS
```

The graph trainer can read this folder directly; it selects `qris_payments.csv` and ignores the sidecar label file.

## Limits and safe claims

- This is suitable for testing data loading, graph construction, and end-to-end training—not for claiming real-world fraud accuracy.
- A high score only means the model learned patterns created by this simulator. Compare against a non-graph baseline and run feature/graph ablations before claiming the GNN adds value.
- The current graph evaluation is preliminary: although rows are split by time, the test graph currently includes later-period transaction context. Do not describe its metrics as a clean online, forward-in-time result until that evaluation path is fixed.
- Real QRIS validation needs representative, appropriately authorized transactions and independently verified fraud labels.
