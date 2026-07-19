from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.gamification.schemas import (
    PromoCreate,
    PromoResponse,
    RedemptionConfirmResponse,
    RedemptionResponse,
    StampListResponse,
)
from app.modules.gamification.service import gamification_service
from app.modules.merchant.dependencies import require_merchant_ownership
from app.modules.merchant.models import Merchant

# Router untuk merchant mengelola promo
merchant_promo_router = APIRouter(prefix="/merchants", tags=["Bakul - Gamification"])

@merchant_promo_router.post(
    "/{id}/promos",
    response_model=PromoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_promo(
    id: UUID,
    promo_in: PromoCreate,
    current_user: User = Depends(get_current_user),
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Membuat promo baru yang membutuhkan stamp.
    """
    return await gamification_service.create_promo(db, merchant.id, promo_in)


@merchant_promo_router.post(
    "/{id}/promo-redemptions/{code}/confirm",
    response_model=RedemptionConfirmResponse,
)
async def confirm_redemption(
    id: UUID,
    code: str,
    current_user: User = Depends(get_current_user),
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Kasir merchant mengkonfirmasi kode redeem dari turis.
    """
    redemption = await gamification_service.confirm_redemption(db, merchant.id, code)
    return {"status": redemption.status}


# Router untuk turis mengumpulkan stamp dan claim promo
user_gamification_router = APIRouter(tags=["Dolan - Gamification"])

@user_gamification_router.get(
    "/users/me/stamps",
    response_model=StampListResponse,
)
async def get_my_stamps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Melihat seluruh stamp yang dimiliki wisatawan.
    """
    stamps = await gamification_service.get_user_stamps(db, current_user.id)
    total_stamps = len(stamps)

    stamps_list = [
        {
            "id": s.id,
            "merchant_name": s.merchant.name,
            "awarded_at": s.awarded_at
        }
        for s in stamps
    ]
    return {"total_stamps": total_stamps, "stamps": stamps_list}


@user_gamification_router.get(
    "/promos/available",
)
async def list_available_promos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Menampilkan promo aktif yang stamp-nya sudah cukup untuk diklaim.
    """
    promos, user_stamp_count = await gamification_service.list_available_promos(db, current_user.id)

    result = []
    for p in promos:
        result.append({
            "promo_id": p.id,
            "merchant_name": p.merchant.name,
            "title": p.title,
            "discount_type": p.discount_type,
            "discount_value": float(p.discount_value),
            "stamp_required_count": p.stamp_required_count,
            "user_stamp_count": user_stamp_count
        })
    return result


@user_gamification_router.post(
    "/promos/{id}/redeem",
    response_model=RedemptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def redeem_promo(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Menukar stamp dengan kode kupon promo (TTL 15 menit).
    Kode ini lalu ditunjukkan ke kasir.
    """
    redemption = await gamification_service.redeem_promo(db, current_user.id, id)
    return {
        "redemption_code": redemption.redemption_code,
        "expires_at": redemption.expires_at
    }
