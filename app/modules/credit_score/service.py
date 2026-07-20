import datetime
from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CREDIT_SCORE_CONSISTENCY_DAYS,
    CREDIT_SCORE_MAX_AGE_DAYS,
    CREDIT_SCORE_MAX_SCORE,
    CREDIT_SCORE_MIN_AGE_DAYS,
    CREDIT_SCORE_VOLUME_THRESHOLD_IDR,
    CREDIT_SCORE_WEIGHT_AGE,
    CREDIT_SCORE_WEIGHT_FREQ,
    CREDIT_SCORE_WEIGHT_RATING,
    CREDIT_SCORE_WEIGHT_REVENUE,
)
from app.modules.credit_score.models import CreditScoreLog
from app.modules.credit_score.schemas import CreditScoreHistoryItem, CreditScoreResponse
from app.modules.merchant.models import Merchant
from app.modules.transactions.models import Transaction


async def _get_history(
    merchant_id: UUID, db: AsyncSession
) -> List[CreditScoreHistoryItem]:
    stmt = (
        select(CreditScoreLog)
        .where(CreditScoreLog.merchant_id == merchant_id)
        .order_by(CreditScoreLog.period.asc())
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [CreditScoreHistoryItem(period=log.period, score=log.score) for log in logs]


async def calculate_credit_score(
    merchant: Merchant, db: AsyncSession
) -> CreditScoreResponse:
    now_dt = datetime.datetime.now(datetime.timezone.utc)

    # Calculate merchant age
    age_days = 0
    if merchant.created_at:
        age_td = now_dt - merchant.created_at
        age_days = age_td.days

    if age_days < CREDIT_SCORE_MIN_AGE_DAYS:
        history = await _get_history(merchant.id, db)
        return CreditScoreResponse(
            current_score=None, data_status="insufficient_data", history=history
        )

    thirty_days_ago = now_dt - datetime.timedelta(days=30)

    # Query active days and total volume from the last 30 days
    # EXCLUDE suspicious transactions
    stmt = select(
        func.count(func.distinct(func.date_trunc("day", Transaction.logged_at))),
        func.sum(Transaction.nominal_value),
    ).where(
        Transaction.merchant_id == merchant.id,
        Transaction.logged_at >= thirty_days_ago,
        Transaction.is_suspicious.is_(False),
    )

    result = await db.execute(stmt)
    row = result.fetchone()
    active_days = row[0] if row and row[0] else 0
    total_volume = float(row[1]) if row and row[1] else 0.0

    # A. Konsistensi Transaksi
    score_a = (active_days / CREDIT_SCORE_CONSISTENCY_DAYS) * CREDIT_SCORE_MAX_SCORE

    # B. Volume Transaksi
    volume_ratio = min(total_volume / CREDIT_SCORE_VOLUME_THRESHOLD_IDR, 1.0)
    score_b = volume_ratio * CREDIT_SCORE_MAX_SCORE

    # C. Masa Aktif Merchant
    age_ratio = min(age_days / CREDIT_SCORE_MAX_AGE_DAYS, 1.0)
    score_c = age_ratio * CREDIT_SCORE_MAX_SCORE

    # D. Rating / Review Pelanggan
    rating = float(merchant.baseline_rating)
    if merchant.review_count == 0:
        rating = 4.0

    score_d = (rating / 5.0) * CREDIT_SCORE_MAX_SCORE

    # Final Score Calculation
    total_score = (
        (score_a * CREDIT_SCORE_WEIGHT_FREQ)
        + (score_b * CREDIT_SCORE_WEIGHT_REVENUE)
        + (score_c * CREDIT_SCORE_WEIGHT_AGE)
        + (score_d * CREDIT_SCORE_WEIGHT_RATING)
    )

    final_score = int(round(total_score))
    final_score = min(final_score, CREDIT_SCORE_MAX_SCORE)

    history = await _get_history(merchant.id, db)

    return CreditScoreResponse(
        current_score=final_score, data_status="sufficient", history=history
    )
