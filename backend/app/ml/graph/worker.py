from __future__ import annotations

import logging
import os
import signal
import socket
import threading
import time
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, or_

from app.core.config import settings
from app.db.session import SessionLocal
from app.ml.graph.training_jobs import LEASE_SECONDS, MAX_ATTEMPTS, run_qris_graphsage_job
from app.models.model_training_job import ModelTrainingJob


logger = logging.getLogger("fingraph.gnn_worker")
POLL_SECONDS = 2


def claim_next_job(worker_id: str) -> tuple[str, dict] | None:
    now = datetime.utcnow()
    with SessionLocal() as db:
        while True:
            job = (
                db.query(ModelTrainingJob)
                .filter(
                    ModelTrainingJob.dataset_name == "qris_graph",
                    or_(
                        ModelTrainingJob.status == "queued",
                        and_(
                            ModelTrainingJob.status == "running",
                            or_(
                                ModelTrainingJob.lease_expires_at.is_(None),
                                ModelTrainingJob.lease_expires_at <= now,
                            ),
                        ),
                    ),
                )
                .order_by(ModelTrainingJob.created_at)
                .with_for_update(skip_locked=True)
                .first()
            )
            if job is None:
                return None

            recovering = job.status == "running"
            if job.attempts >= MAX_ATTEMPTS:
                job.status = "failed"
                job.finished_at = now
                job.worker_id = None
                job.lease_expires_at = None
                job.error = f"Training stopped after {MAX_ATTEMPTS} worker attempts"
                job.progress = {"phase": "failed", "reason": "worker_attempt_limit"}
                job.updated_at = now
                db.commit()
                logger.error("Marked GraphSAGE job %s failed after repeated worker interruption", job.id)
                continue

            job.status = "running"
            job.attempts += 1
            job.worker_id = worker_id
            job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
            job.started_at = job.started_at or now
            job.finished_at = None
            job.error = None
            job.progress = {
                "phase": "resuming" if recovering or job.attempts > 1 else "starting",
                "epoch": 0,
                "epochs": job.parameters.get("epochs"),
                "attempt": job.attempts,
            }
            job.updated_at = now
            db.commit()
            logger.info("Claimed GraphSAGE job %s (attempt %s)", job.id, job.attempts)
            return str(job.id), dict(job.parameters)


def run_worker(shutdown_event: threading.Event | None = None, worker_id: str | None = None) -> None:
    shutdown_event = shutdown_event or threading.Event()
    worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    logger.info("QRIS GraphSAGE worker online: %s", worker_id)

    while not shutdown_event.is_set():
        try:
            job = claim_next_job(worker_id)
        except Exception:
            logger.exception("Could not claim a GraphSAGE job")
            shutdown_event.wait(POLL_SECONDS)
            continue
        if job is None:
            shutdown_event.wait(POLL_SECONDS)
            continue
        job_id, parameters = job
        run_qris_graphsage_job(
            job_id,
            settings.QRIS_GNN_DATA_DIR,
            parameters,
            worker_id,
            shutdown_event,
        )

    logger.info("QRIS GraphSAGE worker stopped: %s", worker_id)


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    shutdown_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: shutdown_event.set())
    signal.signal(signal.SIGINT, lambda *_: shutdown_event.set())
    run_worker(shutdown_event)


if __name__ == "__main__":
    main()
