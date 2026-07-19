from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaselineInventoryUpdate(BaseModel):
    baseline_inventory: Dict[str, int]

class InventoryRecommendationResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    generated_for_date: date
    weather_condition: str
    nearby_events: Optional[List[Dict[str, Any]]] = None
    recommended_stock: Dict[str, int]
    ai_suggestion_text: str

    model_config = ConfigDict(from_attributes=True)
