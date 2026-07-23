from datetime import datetime
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.gamification.models import DiscountType, RedemptionStatus


class PromoCreate(BaseModel):
    title: str = Field(..., max_length=150, description="Judul promo")
    discount_type: DiscountType = Field(..., description="Tipe diskon: percentage atau fixed_amount")
    discount_value: float = Field(..., gt=0, description="Nilai diskon")
    stamp_required_count: int = Field(..., gt=0, description="Jumlah stamp yang dibutuhkan")
    valid_until: datetime = Field(..., description="Batas waktu promo")


class PromoResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    title: str
    discount_type: DiscountType
    discount_value: float
    stamp_required_count: int
    is_active: bool
    valid_until: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class StampResponse(BaseModel):
    id: UUID
    merchant_name: str
    awarded_at: datetime


class StampListResponse(BaseModel):
    total_stamps: int
    stamps: List[StampResponse]


class PromoAvailableResponse(BaseModel):
    promo_id: UUID
    merchant_name: str
    title: str
    discount_type: DiscountType
    discount_value: float
    stamp_required_count: int
    user_stamp_count: int


class GlobalPromoItemResponse(BaseModel):
    promo_id: UUID
    merchant_id: UUID
    merchant_name: str
    merchant_category: str | None
    title: str
    discount_type: DiscountType
    discount_value: float
    stamp_required_count: int
    is_active: bool
    status: Literal["active", "expired"]
    valid_until: datetime
    created_at: datetime


class GlobalPromoPaginatedResponse(BaseModel):
    items: List[GlobalPromoItemResponse]
    total: int
    page: int
    limit: int


class RedemptionResponse(BaseModel):
    redemption_code: str
    expires_at: datetime


class RedemptionConfirmResponse(BaseModel):
    status: RedemptionStatus
