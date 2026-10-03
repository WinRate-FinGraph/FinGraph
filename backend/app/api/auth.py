from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.qris import MerchantProfile
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.core.config import settings
from app.services.subscriptions import normalize_plan, plan_payload


router = APIRouter(prefix="/auth", tags=["Authentication"])

# A fixed dummy bcrypt hash keeps unknown-account and wrong-password work
# comparable, reducing account enumeration through response timing.
DUMMY_PASSWORD_HASH = "$2b$12$BO9e.bC7ICG/10bJd3iOIeBkTslxrpPr3xJin66NonPfrBTlqe75G"


def serialize_user(user: User) -> dict:
    merchant_id = str(user.merchant_profile.id) if getattr(user, "merchant_profile", None) else None
    subscription_plan = (
        normalize_plan(user.merchant_profile.subscription_plan)
        if getattr(user, "merchant_profile", None)
        else "premium"
    )
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "institution_name": user.institution_name,
        "merchant_id": merchant_id,
        "subscription_plan": subscription_plan,
        "subscription": plan_payload(subscription_plan),
    }


@router.post("/register", response_model=UserResponse)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    if not settings.PUBLIC_REGISTRATION_ENABLED:
        raise HTTPException(status_code=403, detail="Pendaftaran publik dinonaktifkan")
    if payload.role.lower() != "merchant":
        raise HTTPException(
            status_code=403,
            detail="Pendaftaran publik hanya tersedia untuk merchant",
        )

    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="merchant",
        institution_name=payload.institution_name,
    )

    db.add(user)
    db.flush()

    merchant = MerchantProfile(
        user_id=user.id,
        merchant_code=f"MRC-{str(user.id).replace('-', '')[:10].upper()}",
        name=payload.institution_name or payload.full_name,
        business_type="UMKM",
        owner_name=payload.full_name,
        address="Belum dilengkapi",
        city="Surakarta",
        province="Jawa Tengah",
        country_code="ID",
    )
    db.add(merchant)

    audit_log = AuditLog(
        actor=payload.email,
        actor_role="merchant",
        action="register_user",
        entity_type="user",
        entity_id=str(user.id),
        user_id=user.id,
        description="Merchant mendaftar melalui endpoint publik.",
    )
    db.add(audit_log)

    db.commit()
    db.refresh(user)
    db.refresh(merchant)

    return serialize_user(user)


@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()

    password_valid = verify_password(
        payload.password,
        user.hashed_password if user else DUMMY_PASSWORD_HASH,
    )
    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun pengguna dinonaktifkan")

    now = datetime.utcnow()
    user.last_login_at = now
    user.last_activity_at = now

    access_token = create_access_token(
        subject=str(user.id),
        extra_data={
            "email": user.email,
            "role": user.role,
        },
    )

    audit_log = AuditLog(
        actor=user.email,
        actor_role=user.role,
        action="login_user",
        entity_type="user",
        entity_id=str(user.id),
        user_id=user.id,
        merchant_id=user.merchant_profile.id if user.merchant_profile else None,
        description="Pengguna berhasil masuk.",
    )
    db.add(audit_log)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        user=serialize_user(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return serialize_user(current_user)
