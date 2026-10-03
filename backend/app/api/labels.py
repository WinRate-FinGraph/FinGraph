from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id
from app.db.session import get_db
from app.models.alert import Alert
from app.models.label import Label
from app.models.qris import PaymentEvent
from app.models.user import User
from app.schemas.qris import LabelQRISCreate
from app.services.audit import add_audit


router = APIRouter(prefix="/labels", tags=["Feedback QRIS"])


def serialize_label(label: Label) -> dict:
    return {"id": str(label.id), "payment_event_id": str(label.payment_event_id) if label.payment_event_id else None, "transaction_id": str(label.transaction_id) if label.transaction_id else None, "merchant_id": str(label.merchant_id) if label.merchant_id else None, "label": label.label, "merchant_decision": label.merchant_decision, "labelled_by": label.labelled_by, "notes": label.notes, "created_at": label.created_at}


@router.get("")
def list_labels(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Label)
    scope = merchant_scope_id(user, db)
    if scope: query = query.filter(Label.merchant_id == scope)
    total = query.count(); items = query.order_by(Label.created_at.desc(), Label.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [serialize_label(item) for item in items]}


@router.post("", status_code=201)
def create_label(payload: LabelQRISCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(PaymentEvent).filter(PaymentEvent.id == payload.payment_event_id)
    scope = merchant_scope_id(user, db)
    if scope: query = query.filter(PaymentEvent.merchant_id == scope)
    payment = query.first()
    if not payment: raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    label = Label(payment_event_id=payment.id, merchant_id=payment.merchant_id, created_by_user_id=user.id, label=payload.label, merchant_decision=payload.merchant_decision, labelled_by=user.email, notes=payload.notes)
    db.add(label)
    # Feedback is evidence for review/adaptive learning, not proof of payment.
    # Only a verified provider callback may transition an order to `paid`.
    if payload.merchant_decision in {"hold", "report"} and payment.order: payment.order.status = "held"
    alert = db.query(Alert).filter(Alert.payment_event_id == payment.id, Alert.status.in_(["open", "investigating"])).first()
    if (
        alert
        and user.role in {"analyst", "admin"}
        and payload.merchant_decision == "approve"
        and payload.label == "legitimate"
    ):
        alert.status = "dismissed"
    elif alert and payload.merchant_decision == "report": alert.status = "investigating"
    add_audit(db, action="create_payment_feedback", entity_type="payment_event", entity_id=str(payment.id), description=f"Feedback {payload.label}/{payload.merchant_decision} disimpan.", user=user, merchant_id=payment.merchant_id)
    db.commit(); db.refresh(label)
    return {"message": "Feedback tersimpan", "label": serialize_label(label), "payment_status": payment.payment_status, "order_status": payment.order.status if payment.order else None, "alert_status": alert.status if alert else None}


@router.get("/{label_id}")
def get_label(label_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Label).filter(Label.id == label_id); scope = merchant_scope_id(user, db)
    if scope: query = query.filter(Label.merchant_id == scope)
    label = query.first()
    if not label: raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    return serialize_label(label)
