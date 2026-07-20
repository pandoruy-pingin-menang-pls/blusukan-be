from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.credit_score.schemas import CreditScoreResponse
from app.modules.credit_score.service import calculate_credit_score
from app.modules.merchant.dependencies import require_merchant_ownership
from app.modules.merchant.models import Merchant

router = APIRouter(prefix="/merchants", tags=["Credit Score"])


@router.get(
    "/{merchant_id}/credit-score",
    response_model=CreditScoreResponse,
    summary="Get Merchant Credit Score",
)
async def get_merchant_credit_score(
    merchant_id: UUID,
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Mengambil skor kredit saat ini dari merchant beserta riwayatnya.
    Akses: Merchant Owner.
    """
    return await calculate_credit_score(merchant, db)
