import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.modules.auth.models import User  # noqa: F401
from app.modules.merchant.models import Merchant  # noqa: F401
from app.modules.transactions.models import Transaction  # noqa: F401


class Stamp(Base):
    __tablename__ = "stamps"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    merchant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 1 transaksi = max 1 stamp (cegah duplikasi award)
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    awarded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relasi
    user = relationship("User", backref="stamps")
    merchant = relationship("Merchant", backref="stamps")
    transaction = relationship("Transaction", backref="stamp")


class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class Promo(Base):
    __tablename__ = "promos"

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
    title = Column(String(150), nullable=False)
    discount_type = Column(
        Enum(DiscountType, name="discount_type_enum", create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    discount_value = Column(Numeric(10, 2), nullable=False)

    # Jumlah stamp yang dibutuhkan wisatawan untuk redeem promo ini
    stamp_required_count = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relasi
    merchant = relationship("Merchant", backref="promos")
    redemptions = relationship("PromoRedemption", back_populates="promo")


class RedemptionStatus(str, enum.Enum):
    PENDING = "pending"
    REDEEMED = "redeemed"
    EXPIRED = "expired"


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    promo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("promos.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Kode 8 karakter yang ditunjukkan wisatawan ke kasir merchant
    redemption_code = Column(String(8), unique=True, nullable=False, index=True)

    status = Column(
        Enum(RedemptionStatus, name="redemption_status_enum", create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=RedemptionStatus.PENDING,
        server_default="pending",
        nullable=False,
    )
    # TTL kode (default 15 menit dari saat generate)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # Waktu merchant confirm redeem (NULL sampai dikonfirmasi)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relasi
    promo = relationship("Promo", back_populates="redemptions")
    user = relationship("User", backref="promo_redemptions")
