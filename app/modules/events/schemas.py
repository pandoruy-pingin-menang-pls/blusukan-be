from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.events.models import EventGenre, EventStatus

# ─── Request Schemas ──────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    name: str = Field(..., max_length=200)
    genre: Optional[EventGenre] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    venue_name: Optional[str] = Field(None, max_length=150)
    estimated_attendee_count: int = Field(..., gt=0)
    start_datetime: datetime
    end_datetime: datetime

    @model_validator(mode="after")
    def end_after_start(self) -> "EventCreate":
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime harus setelah start_datetime")
        return self


class ReviewAction(str):
    APPROVE = "approve"
    REJECT = "reject"


class EventReview(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    # Field opsional yang bisa diedit admin saat review
    name: Optional[str] = Field(None, max_length=200)
    genre: Optional[EventGenre] = None
    venue_name: Optional[str] = Field(None, max_length=150)
    estimated_attendee_count: Optional[int] = Field(None, gt=0)
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_edited_dates(self) -> "EventReview":
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValueError("end_datetime harus setelah start_datetime")
        return self


# ─── Response Schemas ─────────────────────────────────────────────────────────


class EventResponse(BaseModel):
    id: UUID
    name: str
    genre: Optional[EventGenre] = None
    venue_name: Optional[str] = None
    estimated_attendee_count: int
    start_datetime: datetime
    end_datetime: datetime
    status: EventStatus
    reviewed_by_admin_id: Optional[UUID] = None
    created_at: datetime
    # computed: apakah event sudah lewat
    is_expired: bool = False

    @field_validator("is_expired", mode="before")
    @classmethod
    def compute_is_expired(cls, v: bool) -> bool:  # noqa: ARG003
        return v

    model_config = {"from_attributes": True}


class EventCreateResponse(BaseModel):
    event_id: UUID
    status: EventStatus
