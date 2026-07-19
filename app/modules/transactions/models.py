import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.auth.models import User  # noqa: F401
from app.modules.merchant.models import Merchant  # noqa: F401


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    merchant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: merchant bisa log walk-in tanpa user terdaftar
    tourist_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    nominal_value = Column(Numeric(12, 2), nullable=False)

    # Opsional: daftar item yang dibeli (format JSON bebas dari FE)
    item_reference = Column(JSONB, nullable=True)

    # FK ke itinerary wisatawan — digunakan untuk trigger stamp gamification
    linked_itinerary_id = Column(
        UUID(as_uuid=True),
        ForeignKey("itineraries.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Idempotency key dari FE: mencegah duplikasi saat network retry
    client_reference_id = Column(String(64), nullable=True)

    # Anti-fraud flag: nominal > 5.000.000 otomatis ditandai
    is_suspicious = Column(
        Boolean, default=False, server_default="false", nullable=False
    )

    logged_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relasi
    merchant = relationship("Merchant", backref="transactions")
    tourist = relationship("User", backref="transactions", foreign_keys=[tourist_user_id])

    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "client_reference_id",
            name="uq_merchant_client_ref",
        ),
    )
