import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
from app.core.config import settings
from app.ml.artifact_security import sign_artifact, verify_artifact


ARTIFACT_DIR = Path(settings.ML_ARTIFACT_DIR).expanduser().resolve()
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_MODEL_PATH = ARTIFACT_DIR / "active_tabular_model.joblib"
ACTIVE_METRICS_PATH = ARTIFACT_DIR / "active_tabular_metrics.json"
ACTIVE_QRIS_GRAPH_PATH = ARTIFACT_DIR / "active_qris_graph.json"


def save_model_artifact(
    model: Any,
    preprocessor: Any,
    metrics: dict[str, Any],
    dataset_name: str,
    model_name: str,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    version = f"{dataset_name}_{model_name}_{timestamp}"

    model_path = ARTIFACT_DIR / f"{version}.joblib"
    metrics_path = ARTIFACT_DIR / f"{version}_metrics.json"

    artifact = {
        "model": model,
        "preprocessor": preprocessor,
        "dataset_name": dataset_name,
        "model_name": model_name,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_list": metrics.get("features", []),
        "metrics": metrics,
    }

    joblib.dump(artifact, model_path)
    sign_artifact(model_path)

    metrics_payload = {
        **metrics,
        "dataset_name": dataset_name,
        "model_name": model_name,
        "version": version,
        "model_path": str(model_path),
        "created_at": artifact["created_at"],
    }

    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(metrics_payload, file, indent=2)

    if dataset_name == "paysim":
        joblib.dump(artifact, ACTIVE_MODEL_PATH)
        sign_artifact(ACTIVE_MODEL_PATH)

        with open(ACTIVE_METRICS_PATH, "w", encoding="utf-8") as file:
            json.dump(metrics_payload, file, indent=2)

    return metrics_payload


def load_active_model() -> dict[str, Any] | None:
    if not ACTIVE_MODEL_PATH.exists():
        return None

    verify_artifact(ACTIVE_MODEL_PATH)
    return joblib.load(ACTIVE_MODEL_PATH)


def get_active_metrics() -> dict[str, Any] | None:
    if not ACTIVE_METRICS_PATH.exists():
        return None

    with open(ACTIVE_METRICS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def list_model_artifacts() -> list[dict[str, Any]]:
    metrics_files = sorted(ARTIFACT_DIR.glob("*_metrics.json"), reverse=True)
    items: list[dict[str, Any]] = []

    for path in metrics_files:
        if path.name == ACTIVE_METRICS_PATH.name:
            continue

        with open(path, "r", encoding="utf-8") as file:
            items.append(json.load(file))

    return items


def _artifact_for_version(dataset_name: str, version: str) -> dict[str, Any] | None:
    for path in ARTIFACT_DIR.glob("*_metrics.json"):
        if path.name == ACTIVE_METRICS_PATH.name:
            continue
        with open(path, "r", encoding="utf-8") as file:
            metrics = json.load(file)
        if metrics.get("dataset_name") != dataset_name or metrics.get("version") != version:
            continue
        model_path = Path(str(metrics.get("model_path") or "")).expanduser().resolve()
        if model_path.parent != ARTIFACT_DIR or model_path.suffix != ".joblib" or not model_path.is_file():
            return None
        verify_artifact(model_path)
        return {"metrics": metrics, "artifact": joblib.load(model_path)}
    return None


def _latest_version(dataset_name: str) -> str | None:
    for path in sorted(ARTIFACT_DIR.glob("*_metrics.json"), reverse=True):
        if path.name == ACTIVE_METRICS_PATH.name:
            continue
        with open(path, "r", encoding="utf-8") as file:
            metrics = json.load(file)
        if metrics.get("dataset_name") == dataset_name:
            return metrics.get("version")
    return None


def active_model_version(dataset_name: str) -> str | None:
    if dataset_name != "qris_graph":
        return _latest_version(dataset_name)
    if ACTIVE_QRIS_GRAPH_PATH.exists():
        with open(ACTIVE_QRIS_GRAPH_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
        version = payload.get("version")
        return version if payload.get("dataset_name") == dataset_name and isinstance(version, str) else None
    # Existing deployments treated newest QRIS graph artifact as active.
    return _latest_version(dataset_name)


def pin_active_model(dataset_name: str) -> str | None:
    """Freeze pre-existing latest artifact before creating a new candidate."""
    if dataset_name != "qris_graph":
        return _latest_version(dataset_name)
    if ACTIVE_QRIS_GRAPH_PATH.exists():
        return active_model_version(dataset_name)
    version = _latest_version(dataset_name)
    _write_active_qris_graph(version)
    return version


def _write_active_qris_graph(version: str | None) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    descriptor, temp_path = tempfile.mkstemp(prefix="active_qris_graph.", suffix=".tmp", dir=ARTIFACT_DIR)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump({"dataset_name": "qris_graph", "version": version}, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, ACTIVE_QRIS_GRAPH_PATH)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def promote_model_artifact(dataset_name: str, version: str) -> dict[str, Any] | None:
    artifact = _artifact_for_version(dataset_name, version)
    if artifact is None:
        return None
    if dataset_name == "qris_graph":
        _write_active_qris_graph(version)
    return artifact["metrics"]


def load_latest_model_by_dataset(dataset_name: str) -> dict[str, Any] | None:
    version = active_model_version(dataset_name)
    artifact = _artifact_for_version(dataset_name, version) if version else None
    return artifact["artifact"] if artifact else None
