from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import MerchantNotFoundException
from app.core.security import JWTBearer
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.merchant.models import Merchant
from app.modules.merchant.schemas import MerchantCreate, MerchantResponse
from app.modules.merchant.service import register_merchant

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_merchant_profile(
    merchant_in: MerchantCreate,
    current_user: User = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(JWTBearer(auto_error=False)),
):
    """
    Mendaftarkan toko baru.
    Akan mengembalikan data toko beserta access_token dan refresh_token baru
    yang sudah ter-update dengan role 'pedagang'.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")

    return await register_merchant(db, current_user, merchant_in, token)


@router.get("/me", response_model=MerchantResponse)
async def get_my_merchant_profile(
    current_user: User = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db),
):
    """
    Melihat profil toko milik user yang sedang login.
    """
    if not current_user.has_merchant_profile:
        raise MerchantNotFoundException()

    result = await db.execute(select(Merchant).where(Merchant.owner_id == current_user.id))
    merchant = result.scalars().first()

    if not merchant:
        raise MerchantNotFoundException()

    return merchant
