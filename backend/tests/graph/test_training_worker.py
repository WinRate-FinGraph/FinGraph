from datetime import datetime, timedelta
from threading import Event
from uuid import UUID

import pytest

from app.db.session import SessionLocal
from app.ml.graph import training_jobs
from app.ml.graph.worker import claim_next_job
from app.models.model_training_job import ModelTrainingJob


def _new_job() -> str:
    with SessionLocal() as db:
        job = ModelTrainingJob(
            dataset_name="qris_graph",
            status="queued",
            parameters={"epochs": 2},
            progress={"phase": "queued"},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return str(job.id)


def test_worker_reclaims_expired_job_after_restart():
    job_id = _new_job()
    first = claim_next_job("worker-one")
    assert first == (job_id, {"epochs": 2})

    with SessionLocal() as db:
        job = db.get(ModelTrainingJob, UUID(job_id))
        job.lease_expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()

    reclaimed = claim_next_job("worker-two")
    assert reclaimed == (job_id, {"epochs": 2})
    with SessionLocal() as db:
        job = db.get(ModelTrainingJob, UUID(job_id))
        assert job.worker_id == "worker-two"
        assert job.attempts == 2
        assert job.progress["phase"] == "resuming"
        job.status = "failed"
        job.finished_at = datetime.utcnow()
        job.worker_id = None
        job.lease_expires_at = None
        db.commit()


def test_graceful_worker_shutdown_requeues_current_job(monkeypatch):
    job_id = _new_job()
    claim_next_job("worker-stop")
    stop = Event()
    stop.set()

    def interrupt_at_progress(_path, progress_callback, **_parameters):
        progress_callback({"phase": "training", "epoch": 1})

    monkeypatch.setattr(training_jobs, "train_qris_graphsage", interrupt_at_progress)
    training_jobs.run_qris_graphsage_job(
        job_id,
        "/unused",
        {"epochs": 2},
        "worker-stop",
        stop,
    )

    with SessionLocal() as db:
        job = db.get(ModelTrainingJob, UUID(job_id))
        assert job.status == "queued"
        assert job.worker_id is None
        assert job.lease_expires_at is None
        assert job.progress["phase"] == "queued_after_shutdown"
        job.status = "failed"
        job.finished_at = datetime.utcnow()
        db.commit()


@pytest.mark.parametrize(
    ("active_version", "test_pr_auc", "baseline_pr_auc", "expected_promoted", "expected_reason"),
    [
        (None, 0.8, 0.7, True, "first_model_promoted"),
        (None, 0.6, 0.7, False, "test_pr_auc_below_baseline"),
        ("existing-model", 0.9, 0.7, False, "active_model_exists"),
        (None, None, 0.7, False, "test_or_baseline_pr_auc_unavailable"),
    ],
)
def test_auto_promotes_only_first_model_when_it_meets_baseline(
    monkeypatch, active_version, test_pr_auc, baseline_pr_auc, expected_promoted, expected_reason
):
    job_id = _new_job()
    claim_next_job("worker-auto")
    promoted = []

    def trained(_path, progress_callback, **_parameters):
        progress_callback({"phase": "training", "epoch": 1})
        return {
            "version": "qris_graph_graphsage_test",
            "created_at": "2026-10-02T00:00:00+00:00",
            "metrics": {
                "epochs": 1,
                "test": {"pr_auc": test_pr_auc},
                "baseline_test": {"pr_auc": baseline_pr_auc},
            },
        }

    monkeypatch.setattr(training_jobs, "train_qris_graphsage", trained)
    monkeypatch.setattr(training_jobs, "active_model_version", lambda _dataset: active_version)
    monkeypatch.setattr(
        training_jobs,
        "promote_model_artifact",
        lambda _dataset, version: promoted.append(version) or {"version": version},
    )
    training_jobs.run_qris_graphsage_job(job_id, "/unused", {"epochs": 1}, "worker-auto")

    with SessionLocal() as db:
        job = db.get(ModelTrainingJob, UUID(job_id))
        assert job.status == "completed"
        assert job.result["auto_promoted"] is expected_promoted
        assert job.result["auto_promotion_reason"] == expected_reason
    assert bool(promoted) is expected_promoted
