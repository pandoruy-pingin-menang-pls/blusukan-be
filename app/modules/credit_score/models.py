import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.merchant.models import Merchant  # noqa: F401


class CreditScoreLog(Base):
    __tablename__ = "credit_score_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    merchant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period = Column(String(7), nullable=False)  # format: YYYY-MM
    score = Column(Integer, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    merchant = relationship("Merchant", backref="credit_score_logs")

    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "period",
            name="uq_merchant_credit_score_period",
        ),
    )
