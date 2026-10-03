from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import update

from app.db.session import SessionLocal
from app.ml.graph.training import train_qris_graphsage
from app.ml.registry.model_registry import active_model_version, promote_model_artifact
from app.models.model_training_job import ModelTrainingJob


logger = logging.getLogger(__name__)
LEASE_SECONDS = 120
HEARTBEAT_SECONDS = 15
MAX_ATTEMPTS = 5


class TrainingInterrupted(Exception):
    pass


def _auto_promote_first_model(version: str, metrics: dict) -> tuple[bool, str]:
    try:
        if active_model_version("qris_graph") is not None:
            return False, "active_model_exists"
        test_pr_auc = (metrics.get("test") or {}).get("pr_auc")
        baseline_pr_auc = (metrics.get("baseline_test") or {}).get("pr_auc")
        if test_pr_auc is None or baseline_pr_auc is None:
            return False, "test_or_baseline_pr_auc_unavailable"
        if test_pr_auc < baseline_pr_auc:
            return False, "test_pr_auc_below_baseline"
        if promote_model_artifact("qris_graph", version) is not None:
            return True, "first_model_promoted"
    except Exception:
        logger.exception("Could not auto-promote first QRIS GraphSAGE model %s", version)
    return False, "auto_promotion_failed"


def _owned_update(job_id: UUID, owner_id: str, **values) -> bool:
    values["updated_at"] = datetime.utcnow()
    with SessionLocal() as db:
        result = db.execute(
            update(ModelTrainingJob)
            .where(
                ModelTrainingJob.id == job_id,
                ModelTrainingJob.status == "running",
                ModelTrainingJob.worker_id == owner_id,
            )
            .values(**values)
        )
        db.commit()
        return result.rowcount == 1


def run_qris_graphsage_job(
    job_id: str,
    data_path: str,
    parameters: dict,
    worker_id: str,
    shutdown_event: threading.Event | None = None,
) -> None:
    parsed_id = UUID(job_id)
    started = time.monotonic()
    heartbeat_stop = threading.Event()
    lease_lost = threading.Event()
    latest_progress: dict = {"phase": "starting", "epoch": 0, "epochs": parameters["epochs"]}

    def elapsed() -> int:
        return round(time.monotonic() - started)

    def heartbeat() -> None:
        while not heartbeat_stop.wait(HEARTBEAT_SECONDS):
            try:
                if not _owned_update(
                    parsed_id,
                    worker_id,
                    lease_expires_at=datetime.utcnow() + timedelta(seconds=LEASE_SECONDS),
                ):
                    lease_lost.set()
                    return
            except Exception:
                logger.warning("Could not renew GraphSAGE lease for job %s", job_id, exc_info=True)

    if not _owned_update(
        parsed_id,
        worker_id,
        progress=latest_progress,
        lease_expires_at=datetime.utcnow() + timedelta(seconds=LEASE_SECONDS),
    ):
        return

    heartbeat_thread = threading.Thread(target=heartbeat, name=f"gnn-heartbeat-{job_id[:8]}", daemon=True)
    heartbeat_thread.start()

    def report(progress: dict) -> None:
        if lease_lost.is_set():
            raise TrainingInterrupted("training lease was claimed by another worker")
        if shutdown_event and shutdown_event.is_set() and progress.get("phase") != "complete":
            raise TrainingInterrupted("worker shutting down; job returned to queue")
        latest_progress.update(progress)
        latest_progress["elapsed_seconds"] = elapsed()
        if not _owned_update(
            parsed_id,
            worker_id,
            progress=latest_progress,
            lease_expires_at=datetime.utcnow() + timedelta(seconds=LEASE_SECONDS),
        ):
            lease_lost.set()
            raise TrainingInterrupted("training lease was claimed by another worker")

    try:
        trained = train_qris_graphsage(data_path, progress_callback=report, **parameters)
    except TrainingInterrupted as exc:
        if shutdown_event and shutdown_event.is_set():
            latest_progress.update({"phase": "queued_after_shutdown", "elapsed_seconds": elapsed()})
            try:
                _owned_update(
                    parsed_id,
                    worker_id,
                    status="queued",
                    worker_id=None,
                    lease_expires_at=None,
                    progress=latest_progress,
                )
            except Exception:
                logger.exception("Could not requeue interrupted GraphSAGE job %s", job_id)
        else:
            logger.info("GraphSAGE job %s stopped after lease loss: %s", job_id, exc)
        return
    except Exception as exc:
        logger.exception("QRIS GraphSAGE training job failed: %s", job_id)
        try:
            _owned_update(
                parsed_id,
                worker_id,
                status="failed",
                finished_at=datetime.utcnow(),
                worker_id=None,
                lease_expires_at=None,
                progress={"phase": "failed", "elapsed_seconds": elapsed()},
                error=str(exc)[:1000],
            )
        except Exception:
            logger.exception("Could not persist GraphSAGE failure for job %s", job_id)
        return
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=HEARTBEAT_SECONDS + 1)

    metrics = dict(trained["metrics"])
    metrics.pop("graph_schema", None)
    auto_promoted, auto_promotion_reason = _auto_promote_first_model(trained["version"], metrics)
    try:
        _owned_update(
            parsed_id,
            worker_id,
            status="completed",
            finished_at=datetime.utcnow(),
            worker_id=None,
            lease_expires_at=None,
            progress={
                "phase": "complete",
                "epoch": metrics["epochs"],
                "epochs": parameters["epochs"],
                "elapsed_seconds": elapsed(),
            },
            result={
                "version": trained["version"],
                "created_at": trained["created_at"],
                "elapsed_seconds": elapsed(),
                "auto_promoted": auto_promoted,
                "auto_promotion_reason": auto_promotion_reason,
                "metrics": metrics,
            },
            error=None,
        )
    except Exception:
        # A saved candidate remains safe; an expired lease will retry if final status cannot persist.
        logger.exception("Could not persist GraphSAGE completion for job %s", job_id)
