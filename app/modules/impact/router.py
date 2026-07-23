from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User, UserRole
from app.modules.merchant.models import Merchant
from app.modules.events.models import Event, EventStatus

router = APIRouter(prefix="/admin/impact", tags=["Admin Impact Dashboard"])

@router.get("/metrics")
async def get_impact_metrics(
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    # 1. Total Wisatawan Aktif
    wisatawan_query = select(func.count(User.id)).where(User.role == UserRole.WISATAWAN)
    total_wisatawan = (await db.execute(wisatawan_query)).scalar() or 0

    # 2. Total Pedagang Aktif
    pedagang_query = select(func.count(Merchant.id)).where(Merchant.is_active == True)
    total_pedagang = (await db.execute(pedagang_query)).scalar() or 0

    # 3. Jumlah Event Menunggu Persetujuan
    pending_event_query = select(func.count(Event.id)).where(Event.status == EventStatus.PENDING_REVIEW)
    pending_events = (await db.execute(pending_event_query)).scalar() or 0

    # 4. Total Event Terdaftar
    total_event_query = select(func.count(Event.id))
    total_events = (await db.execute(total_event_query)).scalar() or 0

    # Determine main condition based on some logic
    if pending_events > 10:
        condition = "Perlu Perhatian"
        recommendation = "Terdapat banyak event menunggu persetujuan. Segera lakukan review."
    else:
        condition = "Baik"
        recommendation = "Kondisi sistem stabil. Terus pantau pendaftaran pedagang dan event."

    return {
        "condition": condition,
        "recommendation": recommendation,
        "metrics": [
            {"label": "Total Wisatawan", "value": total_wisatawan},
            {"label": "Total Pedagang Aktif", "value": total_pedagang},
            {"label": "Event Menunggu Review", "value": pending_events},
            {"label": "Total Event", "value": total_events},
        ]
    }

@router.get("/action-logs")
async def get_action_logs(
    period: Optional[str] = Query("all", description="'all', 'today', 'week', 'month'"),
    status: Optional[str] = Query(None, description="Event status filter"),
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    # Base query for events which acts as our action logs
    query = select(Event)
    
    # Filter by period
    if period == "today":
        query = query.where(func.date(Event.created_at) == date.today())
    elif period == "week":
        query = query.where(Event.created_at >= (date.today() - timedelta(days=7)))
    elif period == "month":
        query = query.where(Event.created_at >= (date.today() - timedelta(days=30)))
        
    # Filter by status
    if status:
        query = query.where(Event.status == status)

    query = query.order_by(Event.created_at.desc())
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(evt.id),
                "name": evt.name,
                "category": evt.genre.value if evt.genre else "N/A",
                "status": evt.status.value,
                "priority": "High" if evt.status == EventStatus.PENDING_REVIEW else "Normal",
                "time": evt.created_at.isoformat(),
            } for evt in events
        ]
    }
