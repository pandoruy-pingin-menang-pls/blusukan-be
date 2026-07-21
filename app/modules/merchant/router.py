from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import MerchantNotFoundException
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, security
from app.modules.auth.models import User
from app.modules.merchant.models import Merchant
from app.modules.merchant.schemas import MerchantCreate, MerchantResponse
from app.modules.merchant.service import register_merchant

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_merchant_profile(
    merchant_in: MerchantCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    token_creds: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Mendaftarkan toko baru.
    Akan mengembalikan data toko beserta access_token dan refresh_token baru
    yang sudah ter-update dengan role 'pedagang'.
    """
    token = token_creds.credentials if token_creds else None
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")

    return await register_merchant(db, current_user, merchant_in, token)


@router.get("/me", response_model=MerchantResponse)
async def get_my_merchant_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Melihat profil toko milik user yang sedang login.
    """
    if not current_user.has_merchant_profile:
        raise MerchantNotFoundException()

    stmt = select(
        Merchant,
        func.ST_Y(Merchant.location).label("lat"),
        func.ST_X(Merchant.location).label("lon")
    ).where(Merchant.owner_id == current_user.id)

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise MerchantNotFoundException()

    merchant = row[0]
    merchant.latitude = row.lat
    merchant.longitude = row.lon

    if not merchant:
        raise MerchantNotFoundException()

    return merchant
