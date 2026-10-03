import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_merchant, get_current_user, merchant_scope_id, require_roles
from app.core.security import payload_fingerprint
from app.db.session import get_db
from app.models.alert import Alert
from app.models.qris import MerchantProfile, Outlet, QRISProfile
from app.models.user import User
from app.schemas.qris import MerchantUpdate, OutletCreate, QRISProfileCreate, QRISVerifyRequest, SubscriptionPlanUpdate
from app.services.audit import add_audit
from app.services.qris_serializers import merchant_dict, outlet_dict, qris_dict
from app.core.config import settings
from app.api.pagination import page_response
from app.services.impact_dashboard import build_impact_dashboard
from app.services.subscriptions import PLAN_CATALOG, normalize_plan, plan_payload


router = APIRouter(prefix="/merchants", tags=["Merchant QRIS"])


def _target_merchant(db: Session, user: User, merchant_id=None) -> MerchantProfile:
    scoped = merchant_scope_id(user, db)
    target_id = scoped or merchant_id
    if target_id is None:
        raise HTTPException(status_code=400, detail="merchant_id wajib untuk analyst/admin")
    merchant = db.query(MerchantProfile).filter(MerchantProfile.id == target_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant tidak ditemukan")
    return merchant


@router.get("")
def list_merchants(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
    status: str | None = None, search: str | None = Query(default=None, max_length=120),
    ordering: str = Query(default="name", pattern="^(name|newest|risk_desc)$"),
    user: User = Depends(require_roles("analyst", "admin")), db: Session = Depends(get_db),
):
    query = db.query(MerchantProfile)
    if status: query = query.filter(MerchantProfile.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(MerchantProfile.name.ilike(pattern) | MerchantProfile.merchant_code.ilike(pattern) | MerchantProfile.business_type.ilike(pattern) | MerchantProfile.owner_name.ilike(pattern) | MerchantProfile.city.ilike(pattern))
    total = query.count()
    order_columns = {
        "name": (MerchantProfile.name.asc(), MerchantProfile.id.asc()),
        "newest": (MerchantProfile.created_at.desc(), MerchantProfile.id.desc()),
        "risk_desc": (MerchantProfile.risk_level.desc(), MerchantProfile.name.asc(), MerchantProfile.id.asc()),
    }[ordering]
    items = query.order_by(*order_columns).offset(offset).limit(limit).all()
    return page_response(total=total, limit=limit, offset=offset, items=[merchant_dict(item) for item in items])


@router.get("/me")
def get_merchant_profile(merchant: MerchantProfile = Depends(get_current_merchant)):
    return merchant_dict(merchant)


@router.put("/me")
def update_merchant_profile(payload: MerchantUpdate, merchant: MerchantProfile = Depends(get_current_merchant), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(merchant, key, value)
    add_audit(db, action="update_merchant_profile", entity_type="merchant", entity_id=str(merchant.id), description="Profil merchant diperbarui.", user=user, merchant_id=merchant.id)
    db.commit(); db.refresh(merchant)
    return merchant_dict(merchant)


@router.get("/subscription")
def get_subscription(
    merchant: MerchantProfile = Depends(get_current_merchant),
):
    return {
        "current": plan_payload(merchant.subscription_plan),
        "status": merchant.subscription_status,
        "changed_at": merchant.plan_changed_at,
        "catalog": [dict(plan) for plan in PLAN_CATALOG.values()],
        "checkout_available": False,
        "demo_change_available": settings.demo_mode,
        "notice": (
            "Pergantian paket pada Mode Demo tidak memproses pembayaran."
            if settings.demo_mode
            else "Pembayaran mandiri belum tersedia. Hubungi tim FinGraph untuk perubahan paket."
        ),
    }


@router.patch("/subscription")
def update_subscription(
    payload: SubscriptionPlanUpdate,
    merchant: MerchantProfile = Depends(get_current_merchant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.demo_mode:
        raise HTTPException(
            status_code=409,
            detail="Checkout belum tersedia. Hubungi tim FinGraph untuk perubahan paket.",
        )
    previous = merchant.subscription_plan
    merchant.subscription_plan = payload.plan
    merchant.subscription_status = "active"
    merchant.plan_changed_at = datetime.utcnow()
    add_audit(
        db,
        action="change_subscription_plan",
        entity_type="merchant",
        entity_id=str(merchant.id),
        description=f"Paket demo diubah dari {previous} menjadi {payload.plan}.",
        user=user,
        merchant_id=merchant.id,
        metadata={"previous_plan": previous, "new_plan": payload.plan, "payment_processed": False},
    )
    db.commit()
    db.refresh(merchant)
    return {
        "current": plan_payload(merchant.subscription_plan),
        "status": merchant.subscription_status,
        "changed_at": merchant.plan_changed_at,
        "checkout_available": False,
        "demo_change_available": True,
        "notice": "Paket Mode Demo berhasil diubah tanpa transaksi pembayaran.",
    }


@router.get("/dashboard")
def merchant_dashboard(
    period: str = Query(default="today", pattern="^(today|7d|30d|month|custom)$"),
    outlet_id: uuid.UUID | None = None,
    priority: str | None = Query(default=None, pattern="^(rendah|sedang|tinggi)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    merchant: MerchantProfile = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    if outlet_id and not db.query(Outlet).filter(Outlet.id == outlet_id, Outlet.merchant_id == merchant.id).first():
        raise HTTPException(status_code=404, detail="Outlet bukan milik merchant ini")
    impact = build_impact_dashboard(
        db,
        merchant_id=merchant.id,
        period=period,
        outlet_id=outlet_id,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
        limit=8,
    )
    metrics = impact["metrics"]
    qris_profiles = merchant.qris_profiles
    if outlet_id:
        qris_profiles = [profile for profile in qris_profiles if profile.outlet_id == outlet_id]
    return {
        "merchant": merchant_dict(merchant), "demo_mode": settings.demo_mode,
        "tagline": "Pastikan pembayaran masuk sebelum barang keluar.",
        "today": {
            "payment_count": metrics["payment_count"],
            "transaction_value": metrics["transaction_value"],
            "verified_count": metrics["verified_count"],
            "review_count": metrics["review_count"],
            "high_risk_count": metrics["held_count"],
        },
        "impact": impact,
        "active_alerts": db.query(Alert).filter(Alert.merchant_id == merchant.id, Alert.status.in_(["open", "investigating"])).count(),
        "qris_status": [{"nmid": p.nmid, "outlet": p.outlet.name, "status": p.status, "last_verified_at": p.last_verified_at} for p in qris_profiles],
        "recent_payments": impact["items"],
        "security_tip": "Cocokkan nominal dan tunggu konfirmasi penyedia pembayaran sebelum menyerahkan barang.",
    }


@router.get("/outlets")
def list_outlets(merchant_id: uuid.UUID | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    merchant = _target_merchant(db, user, merchant_id)
    items = db.query(Outlet).filter(Outlet.merchant_id == merchant.id).order_by(Outlet.created_at.asc()).all()
    return {"total": len(items), "items": [outlet_dict(item) for item in items]}


@router.post("/outlets", status_code=201)
def create_outlet(payload: OutletCreate, merchant: MerchantProfile = Depends(get_current_merchant), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = PLAN_CATALOG[normalize_plan(merchant.subscription_plan)]
    outlet_limit = plan["outlet_limit"]
    current_outlets = db.query(Outlet).filter(Outlet.merchant_id == merchant.id).count()
    if outlet_limit is not None and current_outlets >= outlet_limit:
        raise HTTPException(
            status_code=409,
            detail=f"Paket {plan['name']} mendukung maksimal {outlet_limit} outlet.",
        )
    outlet = Outlet(merchant_id=merchant.id, outlet_code=f"OUT-{uuid.uuid4().hex[:10].upper()}", **payload.model_dump())
    db.add(outlet); db.flush()
    add_audit(db, action="create_outlet", entity_type="outlet", entity_id=str(outlet.id), description="Outlet merchant dibuat.", user=user, merchant_id=merchant.id)
    db.commit(); db.refresh(outlet)
    return outlet_dict(outlet)


@router.get("/qris-profiles")
def list_qris_profiles(merchant_id: uuid.UUID | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    merchant = _target_merchant(db, user, merchant_id)
    items = db.query(QRISProfile).filter(QRISProfile.merchant_id == merchant.id).order_by(QRISProfile.created_at.asc()).all()
    return {"total": len(items), "items": [qris_dict(item) for item in items], "demo_notice": "Tidak terhubung ke Bank Indonesia atau PJP nyata."}


@router.post("/qris-profiles", status_code=201)
def create_qris_profile(payload: QRISProfileCreate, merchant: MerchantProfile = Depends(get_current_merchant), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    outlet = db.query(Outlet).filter(Outlet.id == payload.outlet_id, Outlet.merchant_id == merchant.id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet bukan milik merchant ini")
    if db.query(QRISProfile).filter(QRISProfile.nmid == payload.nmid).first():
        raise HTTPException(status_code=409, detail="NMID sudah terdaftar")
    account = payload.settlement_account
    masked = f"****{account[-4:]}"
    profile = QRISProfile(merchant_id=merchant.id, outlet_id=outlet.id, nmid=payload.nmid, qris_type=payload.qris_type, acquirer_name=payload.acquirer_name, masked_settlement_account=masked, payload_hash=payload_fingerprint(payload.payload))
    db.add(profile); db.flush()
    add_audit(db, action="create_qris_profile", entity_type="qris_profile", entity_id=str(profile.id), description="Profil QRIS Mode Demo dibuat; rekening disimpan dalam bentuk masked.", user=user, merchant_id=merchant.id)
    db.commit(); db.refresh(profile)
    return qris_dict(profile)


@router.post("/qris-profiles/verify")
def verify_qris_payload(payload: QRISVerifyRequest, merchant: MerchantProfile = Depends(get_current_merchant), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fingerprint = payload_fingerprint(payload.payload)
    decoded = {}
    for segment in payload.payload.split("|"):
        if "=" in segment:
            key, value = segment.split("=", 1)
            decoded[key.strip().upper()] = value.strip()
    query = db.query(QRISProfile).filter(QRISProfile.merchant_id == merchant.id)
    if payload.qris_profile_id:
        query = query.filter(QRISProfile.id == payload.qris_profile_id)
    selected = db.query(QRISProfile).filter(QRISProfile.id == payload.qris_profile_id, QRISProfile.merchant_id == merchant.id).first() if payload.qris_profile_id else None
    profile = selected or query.filter(QRISProfile.payload_hash == fingerprint).first()
    checks = {
        "merchant_identifier": bool(profile and decoded.get("NMID") == profile.nmid),
        "outlet": bool(profile and decoded.get("OUTLET") == profile.outlet.outlet_code),
        "qris_type": bool(profile and decoded.get("TYPE") == profile.qris_type),
        "acquirer": bool(profile and decoded.get("ACQUIRER") == profile.acquirer_name),
        "fingerprint": bool(profile and fingerprint == profile.payload_hash),
    }
    if profile and all(checks.values()):
        status = "valid"; reasons = ["NMID, outlet, tipe QRIS, acquirer, dan fingerprint cocok dengan profil tersimpan."]
        profile.last_verified_at = datetime.utcnow()
    else:
        status = "mismatch" if selected else "unknown"
        failed = [name for name, matched in checks.items() if not matched]
        reasons = [f"Bagian yang tidak cocok: {', '.join(failed)}."] if selected else ["Payload QR belum dikenal pada profil merchant ini."]
    add_audit(db, action="verify_qris_payload", entity_type="qris_profile", entity_id=str(profile.id) if profile else None, description=f"Pemeriksaan payload QRIS menghasilkan {status}.", user=user, merchant_id=merchant.id, metadata={"result": status})
    db.commit()
    return {"status": status, "profile": qris_dict(profile) if profile else None, "checks": checks, "reasons": reasons, "notice": "Pemeriksaan dilakukan terhadap profil QRIS yang tersimpan pada sistem FinGraph Mode Demo."}
