from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.alert import Alert
from app.models.qris import MerchantProfile, Order, PaymentEvent
from app.models.user import User
from app.services.qris_serializers import alert_dict


router = APIRouter(prefix="/dashboard", tags=["Analyst Overview"])


@router.get("/summary")
def summary(user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db)):
    total = db.query(PaymentEvent).count()
    return {
        "total_payments": total, "total_merchants": db.query(MerchantProfile).count(),
        "total_orders": db.query(Order).count(), "total_alerts": db.query(Alert).filter(Alert.payment_event_id.isnot(None)).count(),
        "open_alerts": db.query(Alert).filter(Alert.payment_event_id.isnot(None), Alert.status.in_(["open", "investigating"])).count(),
        "high_risk_payments": db.query(PaymentEvent).filter(PaymentEvent.risk_level == "high").count(),
        "average_fraud_score": round(float(db.query(func.avg(PaymentEvent.fraud_score)).scalar() or 0), 4),
        "risk_distribution": {level: db.query(PaymentEvent).filter(PaymentEvent.risk_level == level).count() for level in ("low", "medium", "high")},
        "payment_status_distribution": {status: db.query(PaymentEvent).filter(PaymentEvent.payment_status == status).count() for status in ("pending", "success", "failed", "expired", "reversed", "refunded")},
        "demo_mode": True,
    }


@router.get("/recent-alerts")
def recent_alerts(user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db)):
    items = db.query(Alert).filter(Alert.payment_event_id.isnot(None)).order_by(Alert.created_at.desc()).limit(10).all()
    return [alert_dict(item) for item in items]
