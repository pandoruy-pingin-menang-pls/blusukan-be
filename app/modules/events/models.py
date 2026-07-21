import enum
import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class EventGenre(str, enum.Enum):
    CULTURAL = "cultural"
    SPORTS = "sports"
    CONVENTION = "convention"
    CONCERT = "concert"
    FESTIVAL = "festival"

class EventStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"

class Event(Base):
    __tablename__ = "events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name = Column(String(200), nullable=False)
    genre = Column(Enum(EventGenre, values_callable=lambda obj: [e.value for e in obj]), nullable=True)

    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    venue_name = Column(String(150), nullable=True)

    estimated_attendee_count = Column(Integer, nullable=False)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)

    status = Column(
        Enum(EventStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=EventStatus.PENDING_REVIEW,
        server_default="pending_review",
    )

    reviewed_by_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reviewed_by = relationship("User", foreign_keys=[reviewed_by_admin_id])
