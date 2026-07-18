from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import MerchantNotFoundException, MerchantOwnershipException
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User, UserRole
from app.modules.merchant.models import Merchant


async def require_merchant_ownership(
    id: Annotated[UUID, Path(...)],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Merchant:
    """
    Dependency to verify that the current user owns the merchant profile they are trying to access,
    or is an admin. Returns the Merchant model if successful.
    """
    result = await db.execute(select(Merchant).where(Merchant.id == id))
    merchant = result.scalars().first()

    if not merchant:
        raise MerchantNotFoundException()
        
    if current_user.role != UserRole.ADMIN and merchant.owner_id != current_user.id:
        raise MerchantOwnershipException()

    return merchant
