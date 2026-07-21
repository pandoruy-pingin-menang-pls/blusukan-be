from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.events import service
from app.modules.events.schemas import (
    EventResponse,
)

router = APIRouter(tags=["Events (Public)"])


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    upcoming: Optional[bool] = Query(None, description="Filter hanya event yang belum berakhir"),
    db: AsyncSession = Depends(get_db),
):
    """
    Publik: Daftar event yang sudah approved.
    Gunakan `?upcoming=true` untuk filter event yang belum berakhir.
    """
    return await service.list_events_public(db, upcoming_only=bool(upcoming))


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Publik: Detail event approved berdasarkan ID.
    Event yang sudah lewat masih dikembalikan dengan `is_expired=true`.
    """
    return await service.get_event_public(db, event_id)
