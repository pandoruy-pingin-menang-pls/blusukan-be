from datetime import date
from typing import Dict
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InventoryRecommendationNotFoundException,
    MerchantNotFoundException,
)
from app.modules.inventory.models import InventoryRecommendation
from app.modules.merchant.models import Merchant


async def update_baseline_inventory(db: AsyncSession, merchant_id: UUID, baseline: Dict[str, int]):
    stmt = (
        update(Merchant)
        .where(Merchant.id == merchant_id)
        .values(baseline_inventory=baseline)
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        raise MerchantNotFoundException()
    await db.commit()

async def get_today_recommendation(db: AsyncSession, merchant_id: UUID, target_date: date) -> InventoryRecommendation:
    stmt = select(InventoryRecommendation).where(
        InventoryRecommendation.merchant_id == merchant_id,
        InventoryRecommendation.generated_for_date == target_date
    )
    res = await db.execute(stmt)
    rec = res.scalars().first()
    if not rec:
        raise InventoryRecommendationNotFoundException()
    return rec

async def trigger_celery_recalc():
    from app.workers.celery_app import celery_app  # Initialize Celery app with correct broker
    from app.workers.tasks_stock_recalc import calculate_daily_stock
    # Jalankan secara asynchronous di background worker celery
    calculate_daily_stock.delay()
