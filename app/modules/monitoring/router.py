from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import require_admin
from app.modules.monitoring.models import ActivityLog

router = APIRouter(prefix="/admin/monitoring", tags=["Admin Monitoring"])

@router.get("/stats")
async def get_monitoring_stats(
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    today = date.today()

    # 1. Total Active Users today (unique user_ids in activity log)
    active_users_query = select(func.count(func.distinct(ActivityLog.user_id))).where(
        func.date(ActivityLog.created_at) == today
    )
    active_users_result = await db.execute(active_users_query)
    active_users_count = active_users_result.scalar() or 0

    # 2. Total activities today
    total_activities_query = select(func.count(ActivityLog.id)).where(
        func.date(ActivityLog.created_at) == today
    )
    total_activities_result = await db.execute(total_activities_query)
    total_activities_count = total_activities_result.scalar() or 0

    # 3. Activity distribution by role
    distribution_query = select(
        ActivityLog.user_role,
        func.count(ActivityLog.id)
    ).where(
        func.date(ActivityLog.created_at) == today
    ).group_by(ActivityLog.user_role)

    distribution_result = await db.execute(distribution_query)
    role_distribution = {row[0] or "unknown": row[1] for row in distribution_result.all()}

    return {
        "active_users_today": active_users_count,
        "total_activities_today": total_activities_count,
        "distribution_by_role": role_distribution
    }

@router.get("/activities")
async def get_recent_activities(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    query = select(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(limit)
    result = await db.execute(query)
    activities = result.scalars().all()

    return {
        "activities": [
            {
                "id": str(act.id),
                "user_id": str(act.user_id) if act.user_id else None,
                "role": act.user_role,
                "action": act.action,
                "endpoint": act.endpoint,
                "method": act.method,
                "created_at": act.created_at.isoformat()
            } for act in activities
        ]
    }
