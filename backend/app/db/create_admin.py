"""Create the first production administrator without enabling public registration.

Credentials are read from temporary environment variables so the password does
not need to be stored in the repository or passed as a command-line argument.
"""

from __future__ import annotations

import os
import sys

from email_validator import EmailNotValidError, validate_email

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} wajib diisi")
    return value


def create_admin() -> None:
    raw_email = _required_environment("FINGRAPH_ADMIN_EMAIL")
    full_name = _required_environment("FINGRAPH_ADMIN_NAME")
    password = _required_environment("FINGRAPH_ADMIN_PASSWORD")
    if len(password) < 12:
        raise ValueError("FINGRAPH_ADMIN_PASSWORD minimal 12 karakter")

    try:
        email = validate_email(raw_email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError(f"FINGRAPH_ADMIN_EMAIL tidak valid: {exc}") from exc

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.ADMIN:
                raise ValueError(
                    "Email sudah dimiliki role non-admin; bootstrap menolak eskalasi otomatis"
                )
            print(f"Admin {email} sudah ada; tidak ada perubahan.")
            return

        admin = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            institution_name="FinGraph QRIS",
            is_active=True,
        )
        db.add(admin)
        db.flush()
        db.add(
            AuditLog(
                actor="system",
                actor_role="system",
                action="bootstrap_admin",
                entity_type="user",
                entity_id=str(admin.id),
                user_id=admin.id,
                description="Administrator awal dibuat melalui bootstrap production.",
                metadata_json={"email": email},
            )
        )
        db.commit()
        print(f"Admin {email} berhasil dibuat.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        create_admin()
    except ValueError as exc:
        print(f"Bootstrap admin gagal: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
