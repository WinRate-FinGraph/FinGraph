from datetime import datetime

from app.ml.graph.dataset import CanonicalPayment, GraphBuilder, split_rows


def _rows(count=6):
    return [
        CanonicalPayment(
            payment_id=f"payment-{index}",
            timestamp=datetime(2026, 1, index + 1),
            payer_id=f"payer-{index % 2}",
            merchant_id="merchant-1",
            outlet_id="outlet-1",
            qris_id="qris-1",
            amount=10_000 + index,
            payment_status="success",
            label=index % 2,
        )
        for index in range(count)
    ]


def test_split_prefers_temporal_data():
    split = split_rows(_rows())
    assert split.strategy == "temporal"
    assert split.warning is None
    assert split.train_ids.isdisjoint(split.test_ids)


def test_missing_timestamps_warns_and_builds_heterogeneous_graph():
    rows = [row.__class__(**{**row.__dict__, "timestamp": None}) for row in _rows()]
    split = split_rows(rows)
    snapshot = GraphBuilder(rows).build(rows)
    assert split.strategy == "random"
    assert split.warning == "timestamps_missing_random_split_not_production_evidence"
    assert snapshot.mode == "heterogeneous"
    assert "payment" in snapshot.x_dict
    assert snapshot.labels.shape[0] == snapshot.x_dict["payment"].shape[0]


def test_missing_entity_ids_use_homogeneous_fallback():
    rows = [row.__class__(**{**row.__dict__, "payer_id": None, "merchant_id": None, "outlet_id": None, "qris_id": None}) for row in _rows()]
    snapshot = GraphBuilder(rows).build(rows)
    assert snapshot.mode == "homogeneous_fallback"
    assert list(snapshot.x_dict) == ["node"]
    assert snapshot.edge_index_dict


def test_query_payments_cannot_change_history_or_send_messages_back():
    rows = _rows(8)
    builder = GraphBuilder(rows[:6])
    history = builder.build(rows[:6])
    queries = {rows[6].payment_id, rows[7].payment_id}
    expanded = builder.build(rows, query_ids=queries)

    # Both queries share payer-0 with historical payments. Its degree feature
    # must remain based on history, not grow when holdout rows are added.
    assert expanded.x_dict["payer"][0, 0].item() == history.x_dict["payer"][0, 0].item()
    reverse_edges = expanded.edge_index_dict[("payment", "rev_payer_payment", "payer")]
    assert not queries.intersection(
        payment_id
        for payment_id, index in expanded.payment_indices.items()
        if index in reverse_edges[0].tolist()
    )
    assert ("payment", "payment_merchant", "merchant") in expanded.edge_index_dict
    merchant_edges = expanded.edge_index_dict[("payment", "payment_merchant", "merchant")]
    assert not queries.intersection(
        payment_id
        for payment_id, index in expanded.payment_indices.items()
        if index in merchant_edges[0].tolist()
    )
    assert expanded.schema["edge_types"] == history.schema["edge_types"]
    restored = GraphBuilder.from_schema(history.schema).build(rows)
    assert set(restored.edge_index_dict) == set(history.edge_index_dict)
