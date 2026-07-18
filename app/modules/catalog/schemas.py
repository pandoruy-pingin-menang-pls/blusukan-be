from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DraftItem(BaseModel):
    item_name: str
    price: Optional[Decimal] = None
    category: str = "culinary"

class CatalogIngestResponse(BaseModel):
    message: str
    image_url: Optional[str] = None
    draft_items: List[DraftItem]

class CatalogConfirmItem(BaseModel):
    item_name: str = Field(..., min_length=2, max_length=150)
    price: Optional[Decimal] = Field(None, ge=0)
    category: str = Field("culinary", max_length=50)
    # The frontend tells us if this was modified/added manually or from the original photo
    source_type: str = Field("photo", description="Must be 'photo' or 'manual'")

class CatalogConfirmRequest(BaseModel):
    image_url: Optional[str] = None
    items: List[CatalogConfirmItem]

class CatalogItemResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    item_name: str
    price: Optional[Decimal]
    category: Optional[str]
    description_raw: Optional[str]
    image_url: Optional[str]
    source_type: str
    confidence: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
