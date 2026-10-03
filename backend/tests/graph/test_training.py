from datetime import datetime, timedelta

import pytest
import numpy as np

from app.ml.graph.dataset import CanonicalPayment, GraphBuilder
from app.ml.graph.model import build_model
from app.ml.graph.training import _metrics, _payment_features, _select_threshold, train_qris_graphsage


def test_qris_graphsage_training_round_trip(tmp_path):
    pytest.importorskip("torch_geometric")
    dataset = tmp_path / "qris.csv"
    dataset.write_text(
        "payment_id,timestamp,payer_id,merchant_id,outlet_id,qris_id,amount,payment_status,label\n"
        + "\n".join(
            f"p{i},{(datetime(2026, 1, 1) + timedelta(days=i)).isoformat()},p{i % 2},m1,o1,q1,{1000 + i},success,{i % 2}"
            for i in range(40)
        ),
        encoding="utf-8",
    )
    result = train_qris_graphsage(dataset, epochs=1)
    assert result["dataset_name"] == "qris_graph"
    assert result["metrics"]["split_strategy"] == "temporal"
    assert result["metrics"]["test"]["pr_auc"] is not None
    assert result["metrics"]["baseline_test"]["pr_auc"] is not None
    assert result["metrics"]["best_epoch"] == 1


def test_qris_graphsage_training_homogeneous_fallback(tmp_path):
    pytest.importorskip("torch_geometric")
    dataset = tmp_path / "qris-fallback.csv"
    dataset.write_text(
        "payment_id,timestamp,payer_id,merchant_id,outlet_id,qris_id,amount,payment_status,label\n"
        + "\n".join(
            f"p{i},{(datetime(2026, 1, 1) + timedelta(days=i)).isoformat()},,,,,{1000 + i},success,{i % 2}"
            for i in range(40)
        ),
        encoding="utf-8",
    )
    result = train_qris_graphsage(dataset, epochs=1)
    assert result["metrics"]["model_kind"] == "homogeneous_graphsage"


def test_training_parameter_validation_does_not_need_pyg(tmp_path):
    with pytest.raises(ValueError, match="epochs"):
        train_qris_graphsage(tmp_path / "missing.csv", epochs=0)


def test_single_class_evaluation_marks_auc_undefined():
    metrics = _metrics(np.array([1, 1]), np.array([0.7, 0.8]))
    assert metrics["pr_auc"] is None
    assert metrics["roc_auc"] is None


def test_threshold_is_selected_from_validation_scores():
    threshold = _select_threshold(
        np.array([0, 0, 0, 1, 1]),
        np.array([0.51, 0.52, 0.53, 0.54, 0.80]),
    )
    assert threshold == 0.54
    assert _metrics(
        np.array([0, 0, 0, 1, 1]),
        np.array([0.51, 0.52, 0.53, 0.54, 0.80]),
        threshold,
    )["f1"] == 1.0


def test_homogeneous_baseline_features_keep_labels_aligned():
    rows = [
        CanonicalPayment(
            payment_id=f"payment-{index}",
            timestamp=None,
            payer_id=None,
            merchant_id=None,
            outlet_id=None,
            qris_id=None,
            amount=10_000 + index,
            payment_status="success",
            label=index % 2,
        )
        for index in range(8)
    ]
    snapshot = GraphBuilder(rows).build(rows)
    _, labels = _payment_features(snapshot, {row.payment_id for row in rows})
    assert labels.tolist() == [row.label for row in rows]


def test_inference_graph_keeps_optional_trained_node_types_empty():
    pytest.importorskip("torch_geometric")
    import torch

    rows = [
        CanonicalPayment(
            payment_id=f"payment-{index}",
            timestamp=None,
            payer_id="payer-1",
            merchant_id="merchant-1",
            outlet_id="outlet-1",
            qris_id="qris-1",
            amount=10_000 + index,
            payment_status="success",
            device_id="device-1",
            pjp_id="provider-1",
            label=index % 2,
        )
        for index in range(8)
    ]
    training_snapshot = GraphBuilder(rows).build(rows)
    query_rows = [
        CanonicalPayment(
            payment_id=f"payment-{index}",
            timestamp=None,
            payer_id="payer-1",
            merchant_id="merchant-1",
            outlet_id="outlet-1",
            qris_id="qris-1",
            amount=10_000 + index,
            payment_status="success",
            label=None,
        )
        for index in range(8)
    ]
    inference_snapshot = GraphBuilder.from_schema(training_snapshot.schema).build(query_rows)
    assert inference_snapshot.x_dict["device"].shape == (0, 4)
    assert inference_snapshot.x_dict["pjp"].shape == (0, 4)
    model = build_model(training_snapshot.schema, hidden_dim=8, dropout=0)
    logits = model(inference_snapshot.x_dict, inference_snapshot.edge_index_dict)
    assert logits.shape == (8, 2)
    assert torch.isfinite(logits).all()
