from uuid import UUID
from pydantic import BaseModel, Field


class LabelCreate(BaseModel):
    transaction_id: UUID
    label: str = Field(..., description="fraud, legitimate, suspicious")
    labelled_by: str = "Valen Yanto"
    notes: str | None = None


class LabelResponse(BaseModel):
    message: str
    label_id: str
    transaction_id: str
    label: str
    alert_updated: bool