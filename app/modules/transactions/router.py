from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.merchant.dependencies import require_merchant_ownership
from app.modules.merchant.models import Merchant
from app.modules.transactions.schemas import (
    PaginatedTransactionResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionSummaryResponse,
)
from app.modules.transactions.service import transaction_service

router = APIRouter(prefix="/merchants", tags=["Bakul - POS & Transactions"])


@router.post(
    "/{id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_transaction(
    id: UUID,
    transaction_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Mencatat transaksi baru (POS).
    Jika ada linked_itinerary_id, otomatis memberikan stamp ke turis.
    Idempotent dengan client_reference_id.
    """
    transaction = await transaction_service.log_transaction(
        db=db,
        merchant_id=merchant.id,
        transaction_in=transaction_in,
        user_id=current_user.id,
    )
    return transaction


@router.get(
    "/{id}/transactions",
    response_model=PaginatedTransactionResponse,
)
async def list_transactions(
    id: UUID,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Melihat riwayat transaksi merchant (paginasi).
    """
    return await transaction_service.list_transactions(db, merchant.id, page, limit)


@router.get(
    "/{id}/transactions/summary",
    response_model=TransactionSummaryResponse,
)
async def get_transaction_summary(
    id: UUID,
    date: str = "today",
    current_user: User = Depends(get_current_user),
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Melihat ringkasan transaksi hari ini (total omzet & jumlah transaksi).
    """
    return await transaction_service.get_transaction_summary(db, merchant.id)
