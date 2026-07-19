from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MerchantBase(BaseModel):
    name: str = Field(..., max_length=100, description="Nama warung atau toko")
    description: Optional[str] = Field(None, description="Deskripsi toko")
    category: Optional[str] = Field(None, max_length=50, description="Kategori toko (misal: Makanan, Minuman)")
    address: Optional[str] = Field(None, description="Alamat teks lengkap")


class MerchantCreate(MerchantBase):
    latitude: float = Field(..., ge=-90, le=90, description="Garis Lintang (Latitude)")
    longitude: float = Field(..., ge=-180, le=180, description="Garis Bujur (Longitude)")


class MerchantResponse(MerchantBase):
    id: UUID
    owner_id: UUID
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}
