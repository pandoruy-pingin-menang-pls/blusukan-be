from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    nominal_value: float = Field(..., description="Nilai nominal transaksi")
    item_reference: Optional[Dict[str, Any]] = Field(None, description="Opsional: daftar item yang dibeli")
    linked_itinerary_id: Optional[UUID] = Field(None, description="FK ke itinerary jika terkait")
    client_reference_id: Optional[str] = Field(None, description="Idempotency key dari Frontend")


class TransactionResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    tourist_user_id: Optional[UUID] = None
    nominal_value: float
    item_reference: Optional[Dict[str, Any]] = None
    linked_itinerary_id: Optional[UUID] = None
    client_reference_id: Optional[str] = None
    is_suspicious: bool
    logged_at: datetime
    stamp_awarded: bool = False  # Derived field

    model_config = {"from_attributes": True}


class TransactionSummaryResponse(BaseModel):
    total_omzet: float
    total_transaksi: int


class PaginatedTransactionResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    limit: int



