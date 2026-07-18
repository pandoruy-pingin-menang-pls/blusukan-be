from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.models import UserRole


# -----------------
# USER SCHEMAS
# -----------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password minimal 8 karakter")

class UserUpdate(BaseModel):
    full_name: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    role: UserRole
    has_merchant_profile: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# -----------------
# AUTH SCHEMAS
# -----------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
