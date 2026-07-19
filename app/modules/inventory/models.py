import uuid

from sqlalchemy import Column, Date, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base


class InventoryRecommendation(Base):
    __tablename__ = "inventory_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text('gen_random_uuid()'))
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)

    # Tanggal untuk rekomendasi stok (hanya 1 rekomendasi per hari per merchant)
    generated_for_date = Column(Date, nullable=False)

    # Cuaca harian yang memengaruhi rekomendasi
    weather_condition = Column(String, nullable=False)

    # Kumpulan event terdekat (id dan nama)
    nearby_events = Column(JSONB, nullable=True)

    # Hasil kalkulasi akhir dari engine deterministik
    # Format: {"hot_culinary": 65, "cold_beverage": 120}
    recommended_stock = Column(JSONB, nullable=False)

    # Saran berbentuk kalimat natural (NLG dari Gemini)
    ai_suggestion_text = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint('merchant_id', 'generated_for_date', name='uq_merchant_date_inventory'),
    )
