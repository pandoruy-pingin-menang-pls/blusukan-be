import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text('gen_random_uuid()'))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Input asli turis sebelum diproses NLP
    raw_query = Column(String, nullable=False)

    # Hasil parsing dari Gemini API
    # Contoh isi: {"time_limit_minutes": 120, "budget_idr": 50000, "search_radius_meter": 2000, "interest_categories": "bakso, es teh", "avoid_crowds": true}
    parsed_constraints = Column(JSONB, nullable=False)

    # Data waypoint merchant yang telah dihitung menggunakan SAW Algorithm
    # Array of objects: [{"merchant_id": "...", "name": "...", "score": 0.85, "score_breakdown": {...}, "order": 1}]
    waypoints = Column(JSONB, nullable=False)

    # Hasil mentah dari OSRM (LineString, distance, duration) yang akan di-render di peta Frontend
    route_geojson = Column(JSONB, nullable=False)

    # Estimasi total durasi rute (termasuk waktu singgah di setiap toko) dalam menit
    estimated_duration_minutes = Column(Integer, nullable=True)

    # Status dari itinerary
    status = Column(ENUM('draft', 'active', 'completed', name='itinerary_status_enum', create_type=True), server_default='draft', nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
