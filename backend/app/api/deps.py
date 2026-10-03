from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.qris import MerchantProfile


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_uuid = UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from None

    user = db.query(User).filter(User.id == user_uuid).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun pengguna dinonaktifkan",
        )

    now = datetime.utcnow()
    if user.last_activity_at is None or user.last_activity_at <= now - timedelta(minutes=1):
        user.last_activity_at = now
        db.commit()

    return user


def require_roles(*roles: str):
    allowed = {role.lower() for role in roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.lower() not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses tidak diizinkan untuk role ini")
        return current_user

    return dependency


def get_current_merchant(
    current_user: User = Depends(require_roles("merchant")),
    db: Session = Depends(get_db),
) -> MerchantProfile:
    merchant = db.query(MerchantProfile).filter(MerchantProfile.user_id == current_user.id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Profil merchant belum tersedia")
    return merchant


def merchant_scope_id(current_user: User, db: Session):
    if current_user.role.lower() != "merchant":
        return None
    merchant = db.query(MerchantProfile).filter(MerchantProfile.user_id == current_user.id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Profil merchant belum tersedia")
    return merchant.id
