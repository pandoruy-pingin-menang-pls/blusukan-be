from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateMerchantException
from app.core.security import create_access_token
from app.modules.auth.models import RefreshToken, User, UserRole
from app.modules.auth.service import _generate_and_add_refresh_token
from app.modules.merchant.models import Merchant
from app.modules.merchant.schemas import MerchantCreate, MerchantResponse


async def register_merchant(
    db: AsyncSession, user: User, merchant_in: MerchantCreate, token_to_revoke: str
) -> dict:
    # 1. Cek apakah user sudah punya toko
    if user.has_merchant_profile:
        raise DuplicateMerchantException()

    # 2. Konversi Latitude & Longitude ke format WKT PostGIS (SRID 4326)
    # Format standard: POINT(lon lat)
    wkt_point = f"SRID=4326;POINT({merchant_in.longitude} {merchant_in.latitude})"

    # 3. Buat Merchant record
    new_merchant = Merchant(
        owner_id=user.id,
        name=merchant_in.name,
        description=merchant_in.description,
        category=merchant_in.category,
        address=merchant_in.address,
        location=wkt_point,
        is_redemption_partner=merchant_in.is_redemption_partner,
    )
    db.add(new_merchant)

    # 4. Update Role dan Status User
    user.role = UserRole.PEDAGANG
    user.has_merchant_profile = True
    db.add(user)

    # 5. Cabut (Revoke) token lama agar tidak bisa dipakai lagi (karena rolenya masih wisatawan)
    if token_to_revoke:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.execute(stmt)

    # 6. Generate Token Baru dengan Role Pedagang
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        has_merchant_profile=user.has_merchant_profile
    )
    new_refresh_token = _generate_and_add_refresh_token(db, str(user.id))

    await db.commit()
    await db.refresh(new_merchant)

    # Inject latitude dan longitude agar MerchantResponse terisi
    new_merchant.latitude = merchant_in.latitude
    new_merchant.longitude = merchant_in.longitude

    # Kembalikan response gabungan: Data Toko + Token Baru
    return {
        "merchant": MerchantResponse.model_validate(new_merchant),
        "tokens": {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    }
