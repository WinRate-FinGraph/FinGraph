from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id
from app.db.session import get_db
from app.models.qris import PaymentEvent
from app.models.user import User
from app.services.qris_serializers import payment_dict


router = APIRouter(prefix="/cross-border", tags=["Cross-Border QRIS Intelligence"])


def route_semantics(average_score: float, high_risk_count: int, transaction_count: int) -> tuple[str, str, float]:
    high_risk_rate = high_risk_count / transaction_count if transaction_count else 0.0
    if high_risk_count == 0 and average_score < 0.40:
        return "normal", "Tidak ada transaksi risiko tinggi; lintas wilayah hanya menjadi konteks.", high_risk_rate
    if average_score >= 0.70 or (high_risk_count >= 2 and high_risk_rate >= 0.25):
        return "high", "Skor rata-rata atau proporsi transaksi risiko tinggi melewati ambang rute.", high_risk_rate
    return "monitor", "Ada transaksi yang perlu ditinjau, tetapi rute tidak otomatis dianggap fraud.", high_risk_rate


def scoped_query(db: Session, user: User):
    query = db.query(PaymentEvent)
    scope = merchant_scope_id(user, db)
    return query.filter(PaymentEvent.merchant_id == scope) if scope else query


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = scoped_query(db, user); total = query.count(); cross_region = query.filter(PaymentEvent.is_cross_region.is_(True), PaymentEvent.is_cross_border.is_(False)).count(); cross_border = query.filter(PaymentEvent.is_cross_border.is_(True)).count()
    return {"total_payments": total, "domestic_same_region": total - cross_region - cross_border, "cross_region_payments": cross_region, "cross_border_payments": cross_border, "average_fraud_score": round(float(query.with_entities(func.avg(PaymentEvent.fraud_score)).scalar() or 0), 4), "high_risk_count": query.filter(PaymentEvent.risk_level == "high").count(), "total_value": float(query.with_entities(func.sum(PaymentEvent.amount)).scalar() or 0), "note": "Lintas wilayah atau negara adalah sinyal tambahan, bukan otomatis fraud."}


@router.get("/routes")
def routes(limit: int = Query(default=20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = scoped_query(db, user).filter((PaymentEvent.is_cross_region.is_(True)) | (PaymentEvent.is_cross_border.is_(True)))
    rows = query.with_entities(PaymentEvent.source_city, PaymentEvent.source_country, PaymentEvent.destination_city, PaymentEvent.destination_country, func.count(PaymentEvent.id).label("count"), func.sum(PaymentEvent.amount).label("volume"), func.avg(PaymentEvent.fraud_score).label("risk"), func.sum(case((PaymentEvent.risk_level == "high", 1), else_=0)).label("alerts")).group_by(PaymentEvent.source_city, PaymentEvent.source_country, PaymentEvent.destination_city, PaymentEvent.destination_country).order_by(func.sum(case((PaymentEvent.risk_level == "high", 1), else_=0)).desc(), func.count(PaymentEvent.id).desc()).limit(limit).all()
    items = []
    for row in rows:
        count = int(row.count)
        average = round(float(row.risk or 0), 4)
        high_count = int(row.alerts or 0)
        route_status, status_reason, high_rate = route_semantics(average, high_count, count)
        items.append({
            "route": f"{row.source_city}, {row.source_country} → {row.destination_city}, {row.destination_country}",
            "source_city": row.source_city,
            "source_country": row.source_country,
            "destination_city": row.destination_city,
            "destination_country": row.destination_country,
            "transaction_count": count,
            "total_amount": float(row.volume or 0),
            "average_fraud_score": average,
            "high_risk_count": high_count,
            "high_risk_rate": round(high_rate, 4),
            "route_status": route_status,
            "status_reason": status_reason,
        })
    return {"total": len(items), "items": items, "note": "Lintas kota atau negara bukan otomatis fraud."}


@router.get("/regions")
def regions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = scoped_query(db, user)
    rows = query.with_entities(PaymentEvent.source_region, PaymentEvent.source_country, func.count(PaymentEvent.id).label("count"), func.sum(PaymentEvent.amount).label("volume"), func.avg(PaymentEvent.fraud_score).label("risk"), func.sum(case((PaymentEvent.risk_level == "high", 1), else_=0)).label("high")).group_by(PaymentEvent.source_region, PaymentEvent.source_country).order_by(func.count(PaymentEvent.id).desc()).all()
    return {"items": [{"region": row.source_region, "country": row.source_country, "payment_count": int(row.count), "total_amount": float(row.volume or 0), "average_fraud_score": round(float(row.risk or 0), 4), "high_risk_count": int(row.high or 0)} for row in rows]}


@router.get("/countries")
def countries(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = scoped_query(db, user)
    rows = query.with_entities(PaymentEvent.source_country, func.count(PaymentEvent.id).label("count"), func.sum(PaymentEvent.amount).label("volume"), func.avg(PaymentEvent.fraud_score).label("risk")).group_by(PaymentEvent.source_country).order_by(func.count(PaymentEvent.id).desc()).all()
    return {"items": [{"country_code": row.source_country, "payment_count": int(row.count), "total_amount": float(row.volume or 0), "average_fraud_score": round(float(row.risk or 0), 4)} for row in rows]}


@router.get("/timeline")
def timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = scoped_query(db, user)
    rows = query.with_entities(func.date(PaymentEvent.transaction_time).label("date"), func.count(PaymentEvent.id).label("count"), func.sum(PaymentEvent.amount).label("volume"), func.avg(PaymentEvent.fraud_score).label("risk")).group_by(func.date(PaymentEvent.transaction_time)).order_by(func.date(PaymentEvent.transaction_time).asc()).all()
    return {"items": [{"date": str(row.date), "payment_count": int(row.count), "total_amount": float(row.volume or 0), "average_fraud_score": round(float(row.risk or 0), 4)} for row in rows]}


@router.get("/high-risk-payments")
@router.get("/high-risk-transactions", include_in_schema=False)
def high_risk(limit: int = Query(default=20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = scoped_query(db, user).filter((PaymentEvent.is_cross_region.is_(True)) | (PaymentEvent.is_cross_border.is_(True)), PaymentEvent.risk_level.in_(["medium", "high"])).order_by(PaymentEvent.fraud_score.desc(), PaymentEvent.transaction_time.desc()).limit(limit).all()
    return {"total": len(items), "items": [payment_dict(item) for item in items]}
