from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User
from app.services.activity_monitoring import activity_monitoring_payload


router = APIRouter(prefix="/admin", tags=["Admin Monitoring"])


@router.get("/activity-monitoring")
def activity_monitoring(
    period: str = Query(default="today", pattern="^(today|7d|30d|custom)$"),
    role: str | None = Query(default=None, pattern="^(merchant|analyst|admin|system)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    activity_category: str = Query(default="all", pattern="^(all|operational|authentication|payment|review|configuration|model|system)$"),
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return activity_monitoring_payload(
        db,
        period=period,
        role=role,
        date_from=date_from,
        date_to=date_to,
        recent_limit=limit,
        category=activity_category,
    )
