import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)

    # Koordinat geospasial menggunakan PostGIS (SRID 4326 untuk WGS 84 / GPS)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    address = Column(Text, nullable=True)

    is_verified = Column(
        Boolean, default=False, server_default="false", nullable=False
    )
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relasi ke User
    owner = relationship("User", backref="merchant_profile")
