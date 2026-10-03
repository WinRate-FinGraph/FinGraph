import hashlib
import hmac
from pathlib import Path

from app.core.config import settings


def _signing_key() -> bytes:
    if not settings.ML_ARTIFACT_SIGNING_KEY:
        raise RuntimeError("ML_ARTIFACT_SIGNING_KEY belum dikonfigurasi")
    return settings.ML_ARTIFACT_SIGNING_KEY.encode("utf-8")


def signature_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.sha256")


def sign_artifact(path: Path) -> None:
    signature = hmac.new(_signing_key(), path.read_bytes(), hashlib.sha256).hexdigest()
    signature_path(path).write_text(signature, encoding="ascii")


def verify_artifact(path: Path) -> None:
    stored_path = signature_path(path)
    if not path.is_file() or path.is_symlink() or not stored_path.is_file():
        raise ValueError("Artifact model atau signature tidak valid")
    expected = hmac.new(_signing_key(), path.read_bytes(), hashlib.sha256).hexdigest()
    stored = stored_path.read_text(encoding="ascii").strip()
    if not hmac.compare_digest(expected, stored):
        raise ValueError("Integritas artifact model tidak valid")
