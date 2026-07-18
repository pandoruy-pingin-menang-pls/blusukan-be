from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.catalog.schemas import (
    CatalogConfirmRequest,
    CatalogIngestResponse,
    CatalogItemResponse,
)
from app.modules.catalog.service import catalog_service
from app.modules.merchant.dependencies import require_merchant_ownership
from app.modules.merchant.models import Merchant

router = APIRouter(prefix="/merchants", tags=["Catalog"])


@router.post(
    "/{id}/catalog/ingest",
    response_model=CatalogIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Menu Photo"
)
async def ingest_catalog(
    id: UUID,
    file: UploadFile = File(...),
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db)
):
    """
    Mengambil foto menu dari pedagang dan menggunakan AI (Gemini) untuk mengekstrak teksnya
    menjadi daftar menu yang terstruktur (Draft Items).
    """
    # Defensive check on file size before processing to save RAM/Quota
    # The framework usually streams it, but we can check if it's too large by its headers if possible,
    # but for now we proceed normally. The reverse proxy (Nginx) usually handles max body size.

    return await catalog_service.ingest_menu(db, merchant, file)


@router.post(
    "/{id}/catalog/confirm",
    response_model=List[CatalogItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Confirm Catalog Items"
)
async def confirm_catalog(
    id: UUID,
    request: CatalogConfirmRequest,
    merchant: Merchant = Depends(require_merchant_ownership),
    db: AsyncSession = Depends(get_db)
):
    """
    Menyimpan menu yang sudah disetujui/diedit oleh pedagang ke database,
    serta men-generate pgvector embeddings secara otomatis.
    """
    items = await catalog_service.confirm_catalog(db, merchant, request)
    return items
