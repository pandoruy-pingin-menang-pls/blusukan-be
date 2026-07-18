"""
Business logic untuk modul Events.

Semua operasi admin (CRUD) dan operasi publik (list approved) ada di sini.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.events.models import Event, EventStatus
from app.modules.events.schemas import EventCreate, EventResponse, EventReview

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _to_wkt(latitude: float, longitude: float) -> str:
    """Konversi lat/lon ke format WKT PostGIS SRID 4326."""
    return f"SRID=4326;POINT({longitude} {latitude})"


def _build_event_response(event: Event) -> EventResponse:
    """
    Konversi SQLAlchemy Event → EventResponse.
    Menghitung field is_expired secara dinamis.
    """
    now = datetime.now(timezone.utc)
    is_expired = event.end_datetime.replace(tzinfo=timezone.utc) < now

    return EventResponse(
        id=event.id,
        name=event.name,
        genre=event.genre,
        venue_name=event.venue_name,
        estimated_attendee_count=event.estimated_attendee_count,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        status=event.status,
        reviewed_by_admin_id=event.reviewed_by_admin_id,
        created_at=event.created_at,
        is_expired=is_expired,
    )


# ─── Admin: Create ────────────────────────────────────────────────────────────


async def create_event(db: AsyncSession, event_in: EventCreate, admin: User) -> Event:  # noqa: ARG001
    """
    Admin membuat event baru. Status selalu 'pending_review'.
    Admin ID disimpan sebagai reviewer kandidat (nullable).
    """
    location = None
    if event_in.latitude is not None and event_in.longitude is not None:
        location = _to_wkt(event_in.latitude, event_in.longitude)

    new_event = Event(
        name=event_in.name,
        genre=event_in.genre,
        location=location,
        venue_name=event_in.venue_name,
        estimated_attendee_count=event_in.estimated_attendee_count,
        start_datetime=event_in.start_datetime,
        end_datetime=event_in.end_datetime,
        status=EventStatus.PENDING_REVIEW,
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    return new_event


# ─── Admin: List ─────────────────────────────────────────────────────────────


async def list_events_admin(
    db: AsyncSession,
    status_filter: Optional[str] = None,
) -> list[EventResponse]:
    """
    Admin melihat semua event, opsional filter berdasarkan status.
    """
    stmt = select(Event).order_by(Event.created_at.desc())

    if status_filter:
        try:
            parsed_status = EventStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_STATUS_FILTER",
                    "message": f"Status '{status_filter}' tidak valid. Pilihan: pending_review, approved, rejected",
                },
            ) from None
        stmt = stmt.where(Event.status == parsed_status)

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [_build_event_response(e) for e in events]


# ─── Admin: Review (Approve / Reject) ────────────────────────────────────────


async def review_event(
    db: AsyncSession,
    event_id: UUID,
    review_in: EventReview,
    admin: User,
) -> EventResponse:
    """
    Admin menyetujui atau menolak event, dengan opsi edit field tertentu.

    Edge cases:
    - Event tidak ditemukan → 404
    - Event sudah di-review sebelumnya → masih bisa diubah (admin bisa koreksi)
    """
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalars().first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EVENT_NOT_FOUND",
                "message": f"Event dengan ID {event_id} tidak ditemukan.",
            },
        )

    # Terapkan edited_fields jika ada
    if review_in.name is not None:
        event.name = review_in.name
    if review_in.genre is not None:
        event.genre = review_in.genre
    if review_in.venue_name is not None:
        event.venue_name = review_in.venue_name
    if review_in.estimated_attendee_count is not None:
        event.estimated_attendee_count = review_in.estimated_attendee_count

    # Validasi tanggal baru kalau salah satu diedit
    new_start = review_in.start_datetime or event.start_datetime
    new_end = review_in.end_datetime or event.end_datetime
    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_DATE_RANGE",
                "message": "end_datetime harus setelah start_datetime.",
            },
        )
    event.start_datetime = new_start
    event.end_datetime = new_end

    # Terapkan action
    if review_in.action == "approve":
        event.status = EventStatus.APPROVED
    else:
        event.status = EventStatus.REJECTED

    event.reviewed_by_admin_id = admin.id

    await db.commit()
    await db.refresh(event)
    return _build_event_response(event)


# ─── Public: List Approved Events ────────────────────────────────────────────


async def list_events_public(
    db: AsyncSession,
    upcoming_only: bool = False,
) -> list[EventResponse]:
    """
    Publik hanya melihat event dengan status 'approved'.
    Jika upcoming=true, hanya event yang end_datetime >= sekarang.
    """
    now = datetime.now(timezone.utc)

    stmt = select(Event).where(Event.status == EventStatus.APPROVED)

    if upcoming_only:
        stmt = stmt.where(Event.end_datetime >= now)

    stmt = stmt.order_by(Event.start_datetime.asc())

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [_build_event_response(e) for e in events]


# ─── Public: Get Event by ID ──────────────────────────────────────────────────


async def get_event_public(db: AsyncSession, event_id: UUID) -> EventResponse:
    """
    Publik mengakses detail event. Hanya event approved yang bisa diakses.
    Event yang sudah lewat tapi masih approved tetap ditampilkan (dengan is_expired=True).
    """
    result = await db.execute(
        select(Event).where(
            Event.id == event_id,
            Event.status == EventStatus.APPROVED,
        )
    )
    event = result.scalars().first()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "EVENT_NOT_FOUND",
                "message": f"Event dengan ID {event_id} tidak ditemukan atau belum disetujui.",
            },
        )

    return _build_event_response(event)
