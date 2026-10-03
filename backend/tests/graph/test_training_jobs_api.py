from datetime import datetime
from uuid import UUID

from app.db.session import SessionLocal
from app.ml.registry import model_registry
from app.models.model_training_job import ModelTrainingJob


def test_graphsage_training_job_is_admin_only_and_pollable(
    client, admin_headers, analyst_headers, monkeypatch, tmp_path
):
    monkeypatch.setattr(model_registry, "ARTIFACT_DIR", tmp_path)
    monkeypatch.setattr(model_registry, "ACTIVE_QRIS_GRAPH_PATH", tmp_path / "active_qris_graph.json")
    response = client.post(
        "/api/v1/ml/train/qris-graphsage?epochs=1&limit_rows=4",
        headers=admin_headers,
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]

    try:
        polled = client.get(f"/api/v1/ml/graphsage/jobs/{job_id}", headers=admin_headers)
        assert polled.status_code == 200
        assert polled.json()["status"] == "queued"
        assert polled.json()["parameters"]["epochs"] == 1

        status = client.get("/api/v1/ml/graphsage/status", headers=admin_headers)
        assert status.json()["active_job"]["job_id"] == job_id
        assert status.json()["gnn_final_weight"] == 0.5
        assert "qris_scoring_active" in status.json()

        denied = client.get(f"/api/v1/ml/graphsage/jobs/{job_id}", headers=analyst_headers)
        assert denied.status_code == 403
    finally:
        with SessionLocal() as db:
            job = db.get(ModelTrainingJob, UUID(job_id))
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            db.commit()
