import csv
import json

from app.ml.graph.dataset import load_qris_dataset
from app.ml.synthetic_qris import calibrate_retail_reference, generate_synthetic_qris


def test_synthetic_qris_generator_is_reproducible(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest_a = generate_synthetic_qris(first, rows=200, seed=42)
    manifest_b = generate_synthetic_qris(second, rows=200, seed=42)
    assert manifest_a["files"]["qris_payments.csv"]["sha256"] == manifest_b["files"]["qris_payments.csv"]["sha256"]
    assert manifest_a["fraud_rows"] == 20
    with (first / "qris_payments.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 200
    assert "typology" not in rows[0]
    assert {row["label"] for row in rows} == {"0", "1"}
    assert all(float(row["amount"]).is_integer() for row in rows)
    assert [row["timestamp"] for row in rows] == sorted(row["timestamp"] for row in rows)
    assert json.loads((first / "dataset_manifest.json").read_text(encoding="utf-8"))["seed"] == 42
    assert len(load_qris_dataset(first)) == 200


def test_calibration_keeps_aggregate_qris_statistics_only(tmp_path):
    source = tmp_path / "reference.csv"
    source.write_text(
        "metode_pembayaran,total_penjualan,tanggal_transaksi,customer_id,store_id\n"
        "QRIS,10000,2024-01-01 09:00,CUST-A,STORE-A\n"
        "QRIS,30000,2024-01-02 10:00,CUST-A,STORE-A\n"
        "Transfer,50000,2024-01-03 11:00,CUST-B,STORE-B\n",
        encoding="utf-8",
    )
    profile = calibrate_retail_reference(source)
    assert profile["source_rows"] == 2
    assert profile["unique_customers"] == 1
    assert profile["amount_quantiles_idr_5pct"][0] == 10000
    assert profile["amount_quantiles_idr_5pct"][-1] == 30000
    assert "CUST-A" not in json.dumps(profile)
    assert "STORE-A" not in json.dumps(profile)
