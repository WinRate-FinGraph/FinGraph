from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def add_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None,
    description: str,
    user: User | None = None,
    merchant_id=None,
    actor: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        actor=actor or (user.email if user else "system"),
        actor_role=user.role if user else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        user_id=user.id if user else None,
        merchant_id=merchant_id,
        metadata_json=metadata,
    )
    db.add(log)
    return log
