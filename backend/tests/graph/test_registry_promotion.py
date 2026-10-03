from app.ml.registry import model_registry


def test_graph_candidate_is_inactive_until_promoted(tmp_path, monkeypatch):
    monkeypatch.setattr(model_registry, "ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(model_registry, "ACTIVE_QRIS_GRAPH_PATH", tmp_path / "active_qris_graph.json")

    assert model_registry.pin_active_model("qris_graph") is None
    metrics = model_registry.save_model_artifact(
        {"state_dict": {}, "model_kind": "test"},
        None,
        {"test": {"pr_auc": 0.5}},
        "qris_graph",
        "graphsage",
    )
    assert model_registry.load_latest_model_by_dataset("qris_graph") is None

    promoted = model_registry.promote_model_artifact("qris_graph", metrics["version"])
    assert promoted["version"] == metrics["version"]
    assert model_registry.load_latest_model_by_dataset("qris_graph")["model"]["model_kind"] == "test"
