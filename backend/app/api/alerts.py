from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id, require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.user import User
from app.models.qris import PaymentEvent
from app.schemas.qris import AlertStatusUpdate
from app.services.audit import add_audit
from app.services.qris_serializers import alert_dict
from app.api.pagination import page_response


router = APIRouter(prefix="/alerts", tags=["Fraud Alerts"])


def scoped_alert(db: Session, user: User, alert_id: UUID) -> Alert:
    query = db.query(Alert).filter(Alert.id == alert_id)
    scope = merchant_scope_id(user, db)
    if scope:
        query = query.filter(Alert.merchant_id == scope)
    alert = query.first()
    if not alert:
        raise HTTPException(status_code=404, detail="Peringatan tidak ditemukan")
    return alert


@router.get("")
def get_alerts(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
    status: str | None = None, severity: str | None = None,
    search: str | None = Query(default=None, max_length=120), outlet_id: UUID | None = None,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = db.query(Alert)
    scope = merchant_scope_id(current_user, db)
    if scope: query = query.filter(Alert.merchant_id == scope)
    if severity: query = query.filter(Alert.severity == severity)
    if outlet_id: query = query.filter(Alert.payment_event.has(PaymentEvent.outlet_id == outlet_id))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(Alert.reason.ilike(pattern) | Alert.recommendation.ilike(pattern) | Alert.alert_type.ilike(pattern))
    status_counts = {
        "open": query.filter(Alert.status == "open").count(),
        "investigating": query.filter(Alert.status == "investigating").count(),
        "completed": query.filter(Alert.status.in_(["resolved", "dismissed"])).count(),
    }
    if status == "active": query = query.filter(Alert.status.in_(["open", "investigating"]))
    elif status == "completed": query = query.filter(Alert.status.in_(["resolved", "dismissed"]))
    elif status: query = query.filter(Alert.status == status)
    total = query.count()
    alerts = query.order_by(Alert.created_at.desc(), Alert.id.desc()).offset(offset).limit(limit).all()
    response = page_response(total=total, limit=limit, offset=offset, items=[alert_dict(alert) for alert in alerts])
    response["status_counts"] = status_counts
    return response


@router.get("/{alert_id}")
def get_alert_detail(alert_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return alert_dict(scoped_alert(db, current_user, alert_id))


@router.patch("/{alert_id}/status")
def update_alert_status(alert_id: UUID, payload: AlertStatusUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = scoped_alert(db, current_user, alert_id)
    if current_user.role == "merchant" and payload.status in {"resolved", "dismissed"}:
        raise HTTPException(
            status_code=403,
            detail="Penyelesaian peringatan memerlukan tinjauan analyst atau admin",
        )
    if current_user.role == "merchant" and payload.assigned_to is not None:
        raise HTTPException(status_code=403, detail="Merchant tidak dapat menetapkan analyst")
    old_status = alert.status
    alert.status = payload.status
    if payload.assigned_to is not None: alert.assigned_to = payload.assigned_to
    alert.resolved_at = datetime.utcnow() if payload.status in {"resolved", "dismissed"} else None
    add_audit(db, action="update_alert_status", entity_type="alert", entity_id=str(alert.id), description=f"Status peringatan berubah dari {old_status} menjadi {payload.status}. {payload.notes or ''}".strip(), user=current_user, merchant_id=alert.merchant_id)
    db.commit(); db.refresh(alert)
    return {"message": "Status peringatan diperbarui", "alert": alert_dict(alert)}


@router.patch("/{alert_id}/assign")
def assign_alert(alert_id: UUID, assigned_to: str = Query(min_length=2, max_length=120), current_user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db)):
    alert = scoped_alert(db, current_user, alert_id)
    alert.assigned_to = assigned_to; alert.status = "investigating"
    add_audit(db, action="assign_alert", entity_type="alert", entity_id=str(alert.id), description=f"Peringatan ditetapkan kepada {assigned_to}.", user=current_user, merchant_id=alert.merchant_id)
    db.commit(); db.refresh(alert)
    return alert_dict(alert)
