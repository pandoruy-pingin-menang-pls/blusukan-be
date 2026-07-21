import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MerchantCatalogItem(Base):
    __tablename__ = "merchant_catalog_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)

    item_name = Column(String(150), nullable=False)
    price = Column(Numeric(10, 2), nullable=True) # NULL if AI couldn't read
    category = Column(String(50), nullable=True)
    description_raw = Column(Text, nullable=True)

    # pgvector embedding: 768 dimensions for Gemini models
    embedding = Column(Vector(768), nullable=True)

    image_url = Column(Text, nullable=True)

    # We removed 'voice' to simplify MVP as per user request
    source_type = Column(
        ENUM("photo", "manual", name="catalog_source_type_enum", create_type=False),
        nullable=False,
    )

    confidence = Column(
        ENUM("high", "low", name="catalog_confidence_enum", create_type=False),
        nullable=False,
        default="high",
        server_default="high"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", backref="catalog_items")
