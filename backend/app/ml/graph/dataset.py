from __future__ import annotations

import csv
import hashlib
import hmac
import math
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import torch

from app.core.config import settings


_ALIASES = {
    "payment_id": ("payment_id", "transaction_id", "transaction_reference", "transaction"),
    "timestamp": ("timestamp", "transaction_time", "created_at", "time"),
    "payer_id": ("payer_id", "payer", "payer_pseudonym", "customer_id"),
    "merchant_id": ("merchant_id", "merchant", "merchant_code"),
    "outlet_id": ("outlet_id", "outlet"),
    "qris_id": ("qris_id", "qris_profile_id", "qris", "nmid"),
    "amount": ("amount", "transaction_amount", "payment_amount"),
    "payment_status": ("payment_status", "status", "transaction_status"),
    "label": ("label", "fraud_label", "is_fraud", "target", "class"),
    "device_id": ("device_id", "device", "device_fingerprint"),
    "pjp_id": ("pjp_id", "provider", "acquirer", "acquirer_name"),
    "source_region": ("source_region", "region", "origin_region"),
    "source_country": ("source_country", "country", "origin_country"),
    "destination_region": ("destination_region", "merchant_region"),
    "destination_country": ("destination_country", "merchant_country"),
}


@dataclass(frozen=True)
class CanonicalPayment:
    payment_id: str
    timestamp: datetime | None
    payer_id: str | None
    merchant_id: str | None
    outlet_id: str | None
    qris_id: str | None
    amount: float
    payment_status: str
    label: int | None = None
    device_id: str | None = None
    pjp_id: str | None = None
    source_region: str | None = None
    source_country: str | None = None
    destination_region: str | None = None
    destination_country: str | None = None


@dataclass
class SplitResult:
    train_ids: set[str]
    validation_ids: set[str]
    test_ids: set[str]
    strategy: str
    warning: str | None = None


@dataclass
class GraphSnapshot:
    mode: str
    x_dict: dict[str, torch.Tensor]
    edge_index_dict: dict[tuple[str, str, str], torch.Tensor]
    payment_ids: list[str]
    payment_indices: dict[str, int]
    labels: torch.Tensor
    label_mask: torch.Tensor
    schema: dict[str, Any]


def _pseudonym(value: Any, namespace: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    key = settings.PAYER_PSEUDONYM_KEY.encode() or b"qris-local-key"
    digest = hmac.new(key, f"{namespace}:{raw}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{namespace}_{digest}"


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def _label(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "fraud", "fraudulent", "illicit", "yes"}:
        return 1
    if text in {"0", "false", "legitimate", "licit", "normal", "no", "genuine"}:
        return 0
    return None


def _column(row: dict[str, Any], name: str) -> Any:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for alias in _ALIASES[name]:
        if alias in lowered:
            return lowered[alias]
    return None


def _canonical(row: dict[str, Any], index: int) -> CanonicalPayment:
    payment_id = _pseudonym(_column(row, "payment_id") or f"row-{index}", "payment")
    amount_text = _column(row, "amount")
    try:
        amount = float(amount_text or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return CanonicalPayment(
        payment_id=payment_id or f"payment_{index}",
        timestamp=_timestamp(_column(row, "timestamp")),
        payer_id=_pseudonym(_column(row, "payer_id"), "payer"),
        merchant_id=_pseudonym(_column(row, "merchant_id"), "merchant"),
        outlet_id=_pseudonym(_column(row, "outlet_id"), "outlet"),
        qris_id=_pseudonym(_column(row, "qris_id"), "qris"),
        amount=amount,
        payment_status=str(_column(row, "payment_status") or "unknown").strip().lower(),
        label=_label(_column(row, "label")),
        device_id=_pseudonym(_column(row, "device_id"), "device"),
        pjp_id=_pseudonym(_column(row, "pjp_id"), "pjp"),
        source_region=_pseudonym(_column(row, "source_region"), "region"),
        source_country=_pseudonym(_column(row, "source_country"), "country"),
        destination_region=_pseudonym(_column(row, "destination_region"), "region"),
        destination_country=_pseudonym(_column(row, "destination_country"), "country"),
    )


def load_qris_dataset(path: str | Path, limit_rows: int | None = None) -> list[CanonicalPayment]:
    root = Path(path).expanduser()
    if root.is_file():
        files = [root]
    else:
        payments = root / "qris_payments.csv"
        files = [payments] if payments.is_file() else sorted(root.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No QRIS CSV dataset found at {root}")
    rows: list[CanonicalPayment] = []
    for file in files:
        with file.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            columns = {str(column).strip().lower() for column in (reader.fieldnames or [])}
            for required in ("payment_id", "amount", "payment_status"):
                if not any(alias in columns for alias in _ALIASES[required]):
                    raise ValueError(f"QRIS dataset missing required column: {required}")
            for index, row in enumerate(reader):
                rows.append(_canonical(row, len(rows)))
                if limit_rows and len(rows) >= limit_rows:
                    return rows
    if not rows:
        raise ValueError(f"QRIS dataset is empty: {root}")
    return rows


def split_rows(rows: Iterable[CanonicalPayment], seed: int = 42) -> SplitResult:
    rows = list(rows)
    ids = [row.payment_id for row in rows]
    if all(row.timestamp is not None for row in rows):
        ordered = sorted(rows, key=lambda row: row.timestamp or datetime.min)
        first = max(1, int(len(ordered) * 0.70))
        second = max(first + 1, int(len(ordered) * 0.85))
        second = min(second, len(ordered) - 1) if len(ordered) > 2 else len(ordered)
        return SplitResult(
            {row.payment_id for row in ordered[:first]},
            {row.payment_id for row in ordered[first:second]},
            {row.payment_id for row in ordered[second:]},
            "temporal",
        )
    shuffled = ids[:]
    random.Random(seed).shuffle(shuffled)
    first = max(1, int(len(shuffled) * 0.70))
    second = max(first + 1, int(len(shuffled) * 0.85))
    second = min(second, len(shuffled) - 1) if len(shuffled) > 2 else len(shuffled)
    return SplitResult(
        set(shuffled[:first]),
        set(shuffled[first:second]),
        set(shuffled[second:]),
        "random",
        "timestamps_missing_random_split_not_production_evidence",
    )


class GraphBuilder:
    ENTITY_TYPES = ("payer", "merchant", "outlet", "qris", "device", "pjp", "region", "country")

    def __init__(self, train_rows: Iterable[CanonicalPayment] = (), mode: str | None = None):
        self.mode = mode
        self.edge_types: tuple[tuple[str, str, str], ...] | None = None
        rows = list(train_rows)
        amounts = [max(0.0, row.amount) for row in rows]
        logs = [math.log1p(value) for value in amounts]
        mean = sum(logs) / len(logs) if logs else 0.0
        variance = sum((value - mean) ** 2 for value in logs) / max(len(logs), 1)
        self.feature_stats = {"amount_log_mean": mean, "amount_log_std": math.sqrt(variance) or 1.0}

    @classmethod
    def from_schema(cls, schema: dict[str, Any]) -> "GraphBuilder":
        builder = cls()
        builder.mode = schema.get("mode")
        base_edge_types = schema.get("base_edge_types")
        if base_edge_types is None:
            base_edge_types = [edge for edge in schema.get("edge_types", []) if not str(edge[1]).startswith("rev_")]
        builder.edge_types = tuple(tuple(edge) for edge in base_edge_types)
        builder.feature_stats = schema.get("feature_stats", builder.feature_stats)
        return builder

    def _payment_features(self, row: CanonicalPayment) -> list[float]:
        amount = (math.log1p(max(0.0, row.amount)) - self.feature_stats["amount_log_mean"]) / self.feature_stats["amount_log_std"]
        status = {"success": 1.0, "paid": 1.0, "failed": -1.0, "reversed": -1.0, "refunded": -1.0}.get(row.payment_status, 0.0)
        cross_region = float(bool(row.source_region and row.destination_region and row.source_region != row.destination_region))
        cross_country = float(bool(row.source_country and row.destination_country and row.source_country != row.destination_country))
        return [amount, status, cross_region, cross_country]

    def build(self, rows: Iterable[CanonicalPayment], query_ids: set[str] | None = None) -> GraphSnapshot:
        rows = list(rows)
        query_ids = query_ids or set()
        typed = all(row.payer_id and row.merchant_id and row.outlet_id and row.qris_id for row in rows)
        mode = self.mode or ("heterogeneous" if typed else "homogeneous_fallback")
        self.mode = mode
        node_ids: dict[str, dict[str, int]] = {}
        features: dict[str, list[list[float]]] = {}
        payment_ids: list[str] = []
        payment_indices: dict[str, int] = {}
        edges: dict[tuple[str, str, str], list[tuple[int, int]]] = {}
        query_edges: dict[tuple[str, str, str], list[tuple[int, int]]] = {}

        def node(kind: str, value: str, feature: list[float]) -> int:
            node_ids.setdefault(kind, {})
            features.setdefault(kind, [])
            if value not in node_ids[kind]:
                node_ids[kind][value] = len(features[kind])
                features[kind].append(feature)
            return node_ids[kind][value]

        def edge(source_kind: str, source: str, relation: str, target_kind: str, target: str, *, query: bool = False):
            src_kind, dst_kind = (source_kind, target_kind) if mode == "heterogeneous" else ("node", "node")
            src_value = f"{source_kind}:{source}" if mode != "heterogeneous" else source
            dst_value = f"{target_kind}:{target}" if mode != "heterogeneous" else target
            src = node(src_kind, src_value, [0.0, 1.0, 0.0, 0.0])
            dst = node(dst_kind, dst_value, [0.0, 1.0, 0.0, 0.0])
            key = (src_kind, relation if mode == "heterogeneous" else "rel", dst_kind)
            (query_edges if query else edges).setdefault(key, []).append((src, dst))

        for row in rows:
            query = row.payment_id in query_ids
            payment_kind = "payment" if mode == "heterogeneous" else "node"
            payment_value = row.payment_id if mode == "heterogeneous" else f"payment:{row.payment_id}"
            payment_index = node(payment_kind, payment_value, self._payment_features(row))
            payment_ids.append(row.payment_id)
            payment_indices[row.payment_id] = payment_index
            for kind, value, relation in (
                ("payer", row.payer_id, "payer_payment"),
                ("merchant", row.merchant_id, "merchant_payment"),
                ("outlet", row.outlet_id, "outlet_payment"),
                ("qris", row.qris_id, "qris_payment"),
                ("device", row.device_id, "device_payment"),
                ("pjp", row.pjp_id, "pjp_payment"),
                ("region", row.source_region, "source_region_payment"),
                ("region", row.destination_region, "destination_region_payment"),
                ("country", row.source_country, "source_country_payment"),
                ("country", row.destination_country, "destination_country_payment"),
            ):
                if value:
                    edge(kind, value, relation, "payment", row.payment_id, query=query)
            if row.merchant_id and not query:
                edge("payment", row.payment_id, "payment_merchant", "merchant", row.merchant_id)
            if row.merchant_id and row.outlet_id and not query:
                edge("merchant", row.merchant_id, "merchant_outlet", "outlet", row.outlet_id)
            if row.outlet_id and row.qris_id and not query:
                edge("outlet", row.outlet_id, "outlet_qris", "qris", row.qris_id)

        if mode == "homogeneous_fallback":
            base_key = ("node", "rel", "node")
            edges.setdefault(base_key, [])
            edge_pairs = set(edges[base_key])
            edge_pairs.update((index, index) for index in range(len(features.get("node", []))))
            edges[base_key] = list(edge_pairs)
        elif self.edge_types:
            for source_kind, _, target_kind in self.edge_types:
                node_ids.setdefault(source_kind, {})
                node_ids.setdefault(target_kind, {})
                features.setdefault(source_kind, [])
                features.setdefault(target_kind, [])
        degrees: dict[str, list[int]] = {kind: [0] * len(values) for kind, values in features.items()}
        for (source_kind, _, target_kind), pairs in edges.items():
            for source, target in pairs:
                degrees[source_kind][source] += 1
                degrees[target_kind][target] += 1
        if mode == "heterogeneous":
            entity_kinds = [kind for kind in features if kind != "payment"]
            for kind in entity_kinds:
                for index, degree in enumerate(degrees[kind]):
                    features[kind][index][0] = math.log1p(degree)
        else:
            for value, index in node_ids.get("node", {}).items():
                if not value.startswith("payment:"):
                    features["node"][index][0] = math.log1p(degrees["node"][index])
        edge_index_dict: dict[tuple[str, str, str], torch.Tensor] = {}
        if self.edge_types is None:
            self.edge_types = tuple(sorted(edges.keys() | query_edges.keys()))
        for key in self.edge_types:
            pairs = edges.get(key, []) + query_edges.get(key, [])
            forward = torch.tensor(pairs, dtype=torch.long).t().contiguous() if pairs else torch.empty((2, 0), dtype=torch.long)
            reverse_key = (key[2], f"rev_{key[1]}", key[0])
            history = edges.get(key, [])
            reverse_pairs = torch.tensor(history, dtype=torch.long).t().contiguous() if history else torch.empty((2, 0), dtype=torch.long)
            reverse = reverse_pairs.flip(0)
            edge_index_dict[key] = forward
            edge_index_dict[reverse_key] = reverse
        x_dict = {kind: torch.tensor(values, dtype=torch.float32).reshape(-1, 4) for kind, values in features.items()}
        payment_kind = "payment" if mode == "heterogeneous" else "node"
        labels = torch.full((len(features.get(payment_kind, [])),), -1, dtype=torch.long)
        for row in rows:
            index = payment_indices[row.payment_id]
            labels[index] = row.label if row.label is not None else -1
        label_mask = labels >= 0
        schema = {
            "mode": mode,
            "node_types": list(x_dict),
            "base_edge_types": [list(key) for key in self.edge_types],
            "edge_types": [list(key) for key in edge_index_dict],
            "feature_stats": self.feature_stats,
            "feature_names": ["amount_log_z", "payment_status", "cross_region", "cross_country"],
        }
        return GraphSnapshot(mode, x_dict, edge_index_dict, payment_ids, payment_indices, labels, label_mask, schema)
