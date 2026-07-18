from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

class GenerateItineraryRequest(BaseModel):
    raw_query: str = Field(..., description="Permintaan natural language dari turis")
    current_lat: float = Field(..., description="Latitude saat ini (contoh: -6.175110)")
    current_lon: float = Field(..., description="Longitude saat ini (contoh: 106.827153)")

class ItineraryWaypoint(BaseModel):
    merchant_id: UUID
    name: str
    lat: float
    lon: float
    score: float
    order: int
    category: str
    predicted_stock: Optional[int] = None

class ItineraryResponse(BaseModel):
    id: UUID
    user_id: UUID
    raw_query: str
    parsed_constraints: Dict[str, Any]
    waypoints: List[ItineraryWaypoint]
    route_geojson: Dict[str, Any]
    estimated_duration_minutes: Optional[int] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
