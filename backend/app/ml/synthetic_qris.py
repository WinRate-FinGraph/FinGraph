"""Reproducible scenario-based QRIS-like graph data generator.

Generated labels are controlled test scenarios, not observed QRIS fraud.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any


PAYMENT_FIELDS = [
    "payment_id", "timestamp", "payer_id", "merchant_id", "outlet_id", "qris_id",
    "amount", "payment_status", "label", "device_id", "pjp_id", "source_region",
    "source_country", "destination_region", "destination_country",
]
PROVINCES = [
    "Aceh", "Bali", "Banten", "Bengkulu", "DI Yogyakarta", "DKI Jakarta", "Gorontalo",
    "Jambi", "Jawa Barat", "Jawa Tengah", "Jawa Timur", "Kalimantan Barat", "Kalimantan Selatan",
    "Kalimantan Timur", "Kepulauan Riau", "Lampung", "Maluku", "Nusa Tenggara Barat",
    "Papua", "Riau", "Sulawesi Selatan", "Sulawesi Utara", "Sumatera Barat", "Sumatera Utara",
]
FOREIGN_COUNTRIES = ["MY", "SG", "TH", "AU", "US"]
TYPOLOGY_WEIGHTS = {
    "shared_device_ring": 0.28,
    "velocity_burst": 0.25,
    "merchant_hopping": 0.20,
    "amount_anomaly": 0.17,
    "cross_border_cluster": 0.10,
}
DEFAULT_PROFILE = Path(__file__).resolve().parents[3] / "docs" / "data" / "synthetic_qris_calibration.json"


def _calibration(path: str | Path | None = None) -> dict[str, Any]:
    profile_path = Path(path) if path else DEFAULT_PROFILE
    if profile_path.exists():
        return json.loads(profile_path.read_text(encoding="utf-8"))
    return {"synthetic_scenario": {"default_label_rate": 0.10}}


def _percentile(sorted_values: list[float], fraction: float) -> float:
    position = (len(sorted_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def calibrate_retail_reference(reference_csv: str | Path) -> dict[str, Any]:
    """Extract aggregate QRIS-reference statistics without retaining source IDs or rows."""
    amounts: list[float] = []
    hours = [0] * 24
    weekdays = [0] * 7
    customers: Counter[str] = Counter()
    stores: Counter[str] = Counter()
    source_rows = 0

    with Path(reference_csv).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"metode_pembayaran", "total_penjualan", "tanggal_transaksi", "customer_id", "store_id"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Reference CSV missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            if row["metode_pembayaran"].strip().upper() != "QRIS":
                continue
            try:
                amount = float(row["total_penjualan"])
                timestamp = datetime.strptime(row["tanggal_transaksi"], "%Y-%m-%d %H:%M")
            except (TypeError, ValueError) as exc:
                raise ValueError("QRIS reference row has invalid amount or timestamp") from exc
            if amount < 0:
                continue
            source_rows += 1
            amounts.append(amount)
            hours[timestamp.hour] += 1
            weekdays[timestamp.weekday()] += 1
            customers[row["customer_id"]] += 1
            stores[row["store_id"]] += 1

    if not amounts:
        raise ValueError("Reference CSV contains no usable QRIS rows")
    amounts.sort()
    customer_activity = Counter(customers.values())
    quantiles = [round(_percentile(amounts, index / 20), 2) for index in range(21)]
    return {
        "source_name": "Retail Indonesia Omnichannel Sales QRIS subset",
        "source_license": "CC0",
        "source_is_synthetic": True,
        "source_rows": source_rows,
        "unique_customers": len(customers),
        "unique_stores": len(stores),
        "amount_quantiles_idr_5pct": quantiles,
        "hour_counts": hours,
        "weekday_counts_monday_first": weekdays,
        "transactions_per_customer_histogram": [
            [transactions, customer_activity[transactions]]
            for transactions in sorted(customer_activity)
        ],
        "store_transaction_counts": sorted(stores.values(), reverse=True),
    }


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    target = rng.random() * sum(weights.values())
    for name, weight in weights.items():
        target -= weight
        if target <= 0:
            return name
    return next(iter(weights))


def _weighted_index(rng: random.Random, weights: list[int | float]) -> int:
    if not weights or sum(weights) <= 0:
        return rng.randrange(len(weights)) if weights else 0
    return rng.choices(range(len(weights)), weights=weights, k=1)[0]


def _amount(rng: random.Random, reference: dict[str, Any]) -> float:
    quantiles = reference.get("amount_quantiles_idr_5pct", [])
    if len(quantiles) >= 2:
        position = rng.random() * (len(quantiles) - 1)
        lower = int(position)
        upper = min(lower + 1, len(quantiles) - 1)
        value = quantiles[lower] + (quantiles[upper] - quantiles[lower]) * (position - lower)
        return round(value)
    return round(rng.lognormvariate(12.4, 0.72))


def _timestamp(rng: random.Random, reference: dict[str, Any], start: date, days: int) -> datetime:
    weekday_counts = reference.get("weekday_counts_monday_first", [1] * 7)
    dates = [start + timedelta(days=offset) for offset in range(days)]
    date_weights = [weekday_counts[item.weekday()] for item in dates]
    picked_date = rng.choices(dates, weights=date_weights, k=1)[0] if sum(date_weights) else rng.choice(dates)
    hour_counts = reference.get("hour_counts", [0] * 24)
    hour = _weighted_index(rng, hour_counts) if sum(hour_counts) else rng.randrange(24)
    return datetime.combine(picked_date, time(hour, rng.randrange(60), rng.randrange(60)))


def _payer_schedule(rng: random.Random, rows: int, reference: dict[str, Any]) -> list[str]:
    histogram = reference.get("transactions_per_customer_histogram", [])
    activities = [int(item[0]) for item in histogram if len(item) == 2 and int(item[0]) > 0]
    weights = [int(item[1]) for item in histogram if len(item) == 2 and int(item[0]) > 0]
    schedule: list[str] = []
    payer_index = 0
    while len(schedule) < rows:
        activity = rng.choices(activities, weights=weights, k=1)[0] if activities and sum(weights) else 1
        schedule.extend([f"payer_{payer_index:06d}"] * activity)
        payer_index += 1
    schedule = schedule[:rows]
    rng.shuffle(schedule)
    return schedule


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_synthetic_qris(
    output_dir: str | Path,
    rows: int = 50_000,
    seed: int = 42,
    fraud_rate: float | None = None,
    calibration_path: str | Path | None = None,
) -> dict[str, Any]:
    if rows < 100:
        raise ValueError("rows must be at least 100")
    calibration = _calibration(calibration_path)
    reference = calibration.get("retail_qris_reference", {})
    scenario = calibration.get("synthetic_scenario", {})
    rate = float(scenario.get("default_label_rate", 0.10) if fraud_rate is None else fraud_rate)
    if not 0 < rate < 1:
        raise ValueError("fraud_rate must be greater than 0 and less than 1")

    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    start_date = date(2025, 1, 1)
    period_days = 180
    merchants = [f"merchant_{index:04d}" for index in range(250)]
    outlets = {merchant: [f"outlet_{index:04d}" for index in range(number * 2, number * 2 + 2)] for number, merchant in enumerate(merchants)}
    qris_profiles = {
        outlet: f"qris_{index:04d}"
        for index, outlet in enumerate(outlet_id for outlet_ids in outlets.values() for outlet_id in outlet_ids)
    }
    store_counts = reference.get("store_transaction_counts", [])
    archetype_count = len(store_counts) or 1
    merchant_group_sizes = Counter(index % archetype_count for index in range(len(merchants)))
    merchant_weights = [
        max(1, store_counts[index % archetype_count]) / merchant_group_sizes[index % archetype_count]
        if store_counts else 1
        for index in range(len(merchants))
    ]
    merchant_regions = {merchant: rng.choice(PROVINCES) for merchant in merchants}

    payer_schedule = _payer_schedule(rng, rows, reference)
    payer_counts = Counter(payer_schedule)
    payers = list(payer_counts)
    hot_payers = [payer for payer, _ in payer_counts.most_common(min(120, len(payers)))]
    device_count = max(1, round(len(payers) * 0.75))
    devices = [f"device_{index:06d}" for index in range(device_count)]
    payer_device = {payer: rng.choice(devices) for payer in payers}
    ring_devices = rng.sample(devices, min(100, len(devices)))
    ring_payers = [rng.sample(payers, min(20, len(payers))) for _ in ring_devices]
    ring_merchants = [[rng.choice(merchants) for _ in range(8)] for _ in ring_devices]
    pjps = [f"pjp_{index:02d}" for index in range(8)]

    fraud_count = round(rows * rate)
    fraud_indices = set(rng.sample(range(rows), fraud_count))
    typology_weights = scenario.get("typology_weights", TYPOLOGY_WEIGHTS)
    typology_by_index = {index: _weighted_choice(rng, typology_weights) for index in fraud_indices}
    velocity_anchor: dict[str, datetime] = {}
    velocity_offsets: defaultdict[str, int] = defaultdict(int)
    typologies = Counter()
    payments: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []

    for index in range(rows):
        fraud = index in fraud_indices
        typology = typology_by_index.get(index, "legitimate_baseline")
        payer = payer_schedule[index]
        merchant = rng.choices(merchants, weights=merchant_weights, k=1)[0]
        device = payer_device[payer]
        timestamp = _timestamp(rng, reference, start_date, period_days)
        source_country = "ID"

        if typology == "shared_device_ring":
            ring = rng.randrange(len(ring_devices))
            payer = rng.choice(ring_payers[ring])
            device = ring_devices[ring]
            merchant = rng.choice(ring_merchants[ring])
        elif typology == "velocity_burst":
            payer = rng.choice(hot_payers)
            device = payer_device[payer]
            if payer not in velocity_anchor:
                velocity_anchor[payer] = timestamp
            else:
                velocity_offsets[payer] += rng.randint(1, 3)
            timestamp = velocity_anchor[payer] + timedelta(minutes=velocity_offsets[payer])
        elif typology == "merchant_hopping":
            payer = rng.choice(hot_payers)
            device = payer_device[payer]
        elif not fraud and rng.random() < 0.015:
            # Legitimate shared-device cases make the graph motif non-exclusive to fraud.
            device = rng.choice(ring_devices)

        outlet = rng.choice(outlets[merchant])
        qris = qris_profiles[outlet]
        destination_region = merchant_regions[merchant]
        source_region = destination_region

        foreign_probability = 0.45 if typology == "cross_border_cluster" else 0.02
        if rng.random() < foreign_probability:
            source_country = rng.choice(FOREIGN_COUNTRIES)
            source_region = f"foreign_region_{source_country}"
        elif rng.random() < (0.18 if fraud else 0.10):
            source_region = rng.choice([region for region in PROVINCES if region != destination_region])

        amount = _amount(rng, reference)
        if (typology == "amount_anomaly" and rng.random() < 0.60) or (not fraud and rng.random() < 0.02):
            amount = round(amount * rng.choice([0.25, 2.5]))

        success_rate = 0.94 if fraud else 0.975
        status = rng.choices(["success", "failed", "reversed"], weights=[success_rate, 0.8 * (1 - success_rate), 0.2 * (1 - success_rate)])[0]
        payment_id = f"synthetic_payment_{index + 1:06d}"
        payments.append({
            "payment_id": payment_id,
            "timestamp": timestamp.isoformat(sep=" "),
            "payer_id": payer,
            "merchant_id": merchant,
            "outlet_id": outlet,
            "qris_id": qris,
            "amount": f"{amount:.0f}",
            "payment_status": status,
            "label": int(fraud),
            "device_id": device,
            "pjp_id": rng.choice(pjps),
            "source_region": source_region,
            "source_country": source_country,
            "destination_region": destination_region,
            "destination_country": "ID",
        })
        truth.append({"payment_id": payment_id, "label": int(fraud), "typology": typology})
        typologies[typology] += 1

    payments.sort(key=lambda row: (row["timestamp"], row["payment_id"]))
    truth_by_id = {row["payment_id"]: row for row in truth}
    truth = [truth_by_id[row["payment_id"]] for row in payments]
    payment_path = output / "qris_payments.csv"
    truth_path = output / "qris_ground_truth.csv"
    with payment_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAYMENT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(payments)
    with truth_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["payment_id", "label", "typology"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(truth)

    manifest = {
        "dataset_name": "synthetic_qris_graph_v2",
        "generator": "app.ml.synthetic_qris",
        "seed": seed,
        "rows": rows,
        "timestamp_start": payments[0]["timestamp"],
        "timestamp_end": payments[-1]["timestamp"],
        "fraud_rows": fraud_count,
        "fraud_rate": round(fraud_count / rows, 6),
        "typology_counts": dict(typologies),
        "status_counts": dict(Counter(row["payment_status"] for row in payments)),
        "entity_counts": {
            field: len({row[field] for row in payments})
            for field in ("payer_id", "merchant_id", "outlet_id", "qris_id", "device_id", "pjp_id")
        },
        "cross_region_rate": round(sum(row["source_region"] != row["destination_region"] for row in payments) / rows, 6),
        "cross_country_rate": round(sum(row["source_country"] != row["destination_country"] for row in payments) / rows, 6),
        "feature_columns": PAYMENT_FIELDS,
        "ground_truth_columns": ["payment_id", "label", "typology"],
        "calibration_profile": str(Path(calibration_path) if calibration_path else Path("docs/data") / DEFAULT_PROFILE.name),
        "calibration_source_rows": reference.get("source_rows", 0),
        "limitations": [
            "Retail calibration source is itself simulated and is not bank or QRIS operational data.",
            "Fraud labels and graph motifs are hand-designed test scenarios, not observed QRIS incidents.",
            "Metrics are engineering-benchmark results, not production performance.",
            "Merchant, outlet, device, PJP counts and fraud scenario rate are demo assumptions.",
        ],
        "files": {},
    }
    manifest["files"] = {
        payment_path.name: {"sha256": _checksum(payment_path), "rows": rows},
        truth_path.name: {"sha256": _checksum(truth_path), "rows": rows},
    }
    (output / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "SHA256SUMS").write_text(
        "".join(f"{details['sha256']}  {name}\n" for name, details in manifest["files"].items()),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate or generate a reproducible synthetic QRIS graph dataset")
    parser.add_argument("--output", help="Output directory outside Git or under datasets/")
    parser.add_argument("--rows", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fraud-rate", type=float, help="Synthetic label rate, not an estimate of QRIS fraud prevalence")
    parser.add_argument("--calibration", help="Calibration JSON to use for generation")
    parser.add_argument("--calibrate-from", help="Retail reference CSV; writes aggregate-only calibration profile")
    parser.add_argument("--calibration-output", help="Output JSON for --calibrate-from")
    args = parser.parse_args()

    if args.calibrate_from:
        profile = _calibration()
        profile["retail_qris_reference"] = calibrate_retail_reference(args.calibrate_from)
        output_path = Path(args.calibration_output) if args.calibration_output else DEFAULT_PROFILE
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        print(json.dumps({"calibration_output": str(output_path), **profile["retail_qris_reference"]}, indent=2))
        return
    if not args.output:
        parser.error("--output is required unless --calibrate-from is used")
    print(json.dumps(generate_synthetic_qris(args.output, args.rows, args.seed, args.fraud_rate, args.calibration), indent=2))


if __name__ == "__main__":
    main()
