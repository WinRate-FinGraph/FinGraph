from pathlib import Path
from functools import lru_cache

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Response, status
from neo4j import GraphDatabase
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal


router = APIRouter(prefix="/health", tags=["Health"])


@lru_cache(maxsize=1)
def expected_migration_head() -> str:
    backend_root = Path(__file__).resolve().parents[2]
    config = AlembicConfig(str(backend_root / "alembic.ini"))
    return ScriptDirectory.from_config(config).get_current_head()


@router.get("/live")
def live():
    return {"status": "alive", "service": "fingraph-qris-backend"}


@router.get("/ready")
def ready(response: Response):
    database = "unavailable"
    migration_revision = None
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            migration_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
            database = "ready"
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": database, "migration_revision": migration_revision, "neo4j": "unchecked", "model": "unchecked"}

    expected_revision = expected_migration_head()
    if migration_revision != expected_revision:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "database": database,
            "migration_revision": migration_revision,
            "expected_migration_revision": expected_revision,
            "neo4j": "unchecked",
            "model": "unchecked",
        }

    neo4j = "unavailable"
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=2,
        )
        driver.verify_connectivity()
        driver.close()
        neo4j = "ready"
    except Exception:
        neo4j = "unavailable"

    artifact_dir = Path(settings.ML_ARTIFACT_DIR).expanduser()
    model = "ready" if artifact_dir.exists() and any(artifact_dir.glob("*.joblib")) else "degraded"
    degraded = neo4j != "ready" or model != "ready"
    if settings.NEO4J_REQUIRED and neo4j != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": database, "migration_revision": migration_revision, "neo4j": neo4j, "model": model}
    return {
        "status": "degraded" if degraded else "ready",
        "database": database,
        "migration_revision": migration_revision,
        "neo4j": neo4j,
        "model": model,
        "optional_components_degraded": degraded,
    }
