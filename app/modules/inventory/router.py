from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory import schemas, service
from app.modules.merchant.dependencies import require_merchant_owner

router = APIRouter(prefix="/merchants", tags=["Inventory Predictive Stock"])

@router.patch("/{merchant_id}/baseline-inventory", summary="Update baseline stok harian")
async def update_baseline_inventory(
    merchant_id: UUID,
    payload: schemas.BaselineInventoryUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    await require_merchant_owner(db, merchant_id, user.id)
    await service.update_baseline_inventory(db, merchant_id, payload.baseline_inventory)
    return {"message": "Baseline inventory berhasil diperbarui."}

@router.get("/{merchant_id}/inventory-recommendations/today", response_model=schemas.InventoryRecommendationResponse, summary="Dapatkan saran stok untuk hari ini")
async def get_today_recommendation(
    merchant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    await require_merchant_owner(db, merchant_id, user.id)
    today = datetime.now(timezone.utc).date()
    rec = await service.get_today_recommendation(db, merchant_id, today)
    return rec

admin_router = APIRouter(prefix="/admin/inventory-recommendations", tags=["Admin"])

@admin_router.post("/recalculate", summary="Trigger hitung ulang stok secara paksa", status_code=202)
async def trigger_recalculation(
    # Idealnya tambahkan dep admin only di sini
    user=Depends(get_current_user)
):
    await service.trigger_celery_recalc()
    return {"message": "Tugas perhitungan stok telah dikirim ke Celery.", "job_id": "async-celery"}
