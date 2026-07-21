"""
Admin router — semua endpoint di sini membutuhkan role 'admin'.
Hanya Maintainer yang menambahkan router ini ke app/main.py.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User
from app.modules.events import service as event_service
from app.modules.events.schemas import (
    EventCreate,
    EventCreateResponse,
    EventResponse,
    EventReview,
)

router = APIRouter(prefix="/admin", tags=["Admin — Events (HITL)"])


@router.post(
    "/events",
    response_model=EventCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_event(
    event_in: EventCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin: Buat event baru secara manual.
    Status otomatis menjadi `APPROVED` karena dibuat langsung oleh Admin.
    """
    event = await event_service.create_event(db, event_in, admin)
    return EventCreateResponse(event_id=event.id, status=event.status)


@router.get("/events", response_model=list[EventResponse])
async def admin_list_events(
    status: Optional[str] = Query(
        None,
        description="Filter status: pending_review | approved | rejected",
    ),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin: Daftar semua event. Bisa difilter berdasarkan status.
    """
    return await event_service.list_events_admin(db, status_filter=status)


@router.patch("/events/{event_id}/review", response_model=EventResponse)
async def admin_review_event(
    event_id: UUID,
    review_in: EventReview,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin: Approve atau reject event, dengan opsi edit field tertentu.
    Action: `approve` | `reject`
    """
    return await event_service.review_event(db, event_id, review_in, admin)
