import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.modules.auth.models import User, UserRole
from app.modules.events.models import Event, EventGenre, EventStatus
from app.modules.events.schemas import EventCreate, EventReview
from app.modules.events.service import (
    create_event,
    get_event_public,
    list_events_admin,
    list_events_public,
    review_event,
)


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_admin():
    return User(
        id=uuid.uuid4(),
        email="admin@blusukan.com",
        role=UserRole.ADMIN,
        has_merchant_profile=False,
    )


@pytest.fixture
def future_event():
    now = datetime.now(timezone.utc)
    return Event(
        id=uuid.uuid4(),
        name="Festival Jawa",
        genre=EventGenre.FESTIVAL,
        venue_name="Alun-alun Kidul",
        estimated_attendee_count=5000,
        start_datetime=now + timedelta(days=7),
        end_datetime=now + timedelta(days=8),
        status=EventStatus.PENDING_REVIEW,
        reviewed_by_admin_id=None,
        created_at=now,
    )


@pytest.fixture
def approved_future_event():
    now = datetime.now(timezone.utc)
    return Event(
        id=uuid.uuid4(),
        name="Konser Rock",
        genre=EventGenre.CONCERT,
        venue_name="GOR Kota",
        estimated_attendee_count=10000,
        start_datetime=now + timedelta(days=3),
        end_datetime=now + timedelta(days=4),
        status=EventStatus.APPROVED,
        reviewed_by_admin_id=uuid.uuid4(),
        created_at=now,
    )


@pytest.fixture
def approved_past_event():
    now = datetime.now(timezone.utc)
    return Event(
        id=uuid.uuid4(),
        name="Event Lama",
        genre=EventGenre.CULTURAL,
        venue_name="Museum",
        estimated_attendee_count=200,
        start_datetime=now - timedelta(days=10),
        end_datetime=now - timedelta(days=9),
        status=EventStatus.APPROVED,
        reviewed_by_admin_id=uuid.uuid4(),
        created_at=now - timedelta(days=15),
    )


@pytest.mark.asyncio
async def test_create_event_success(mock_db, mock_admin):
    """Happy path: admin berhasil membuat event baru."""
    now = datetime.now(timezone.utc)

    event_in = EventCreate(
        name="Festival Batik",
        genre=EventGenre.CULTURAL,
        latitude=-7.797,
        longitude=110.370,
        venue_name="Kraton Yogyakarta",
        estimated_attendee_count=3000,
        start_datetime=now + timedelta(days=10),
        end_datetime=now + timedelta(days=11),
    )

    # Simulate db.refresh populating the event
    created_id = uuid.uuid4()

    async def mock_refresh(obj):
        obj.id = created_id
        obj.created_at = now
        obj.status = EventStatus.PENDING_REVIEW

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    result = await create_event(mock_db, event_in, mock_admin)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result.name == "Festival Batik"
    assert result.status == EventStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_create_event_invalid_date_range(mock_db, mock_admin):
    """Edge case: end_datetime sebelum start_datetime → 400 INVALID_DATE_RANGE."""
    now = datetime.now(timezone.utc)

    with pytest.raises(Exception) as exc_info:
        EventCreate(
            name="Event Salah",
            estimated_attendee_count=100,
            start_datetime=now + timedelta(days=5),
            end_datetime=now + timedelta(days=2),
        )

    assert "end_datetime" in str(exc_info.value).lower() or "start_datetime" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_event_without_location(mock_db, mock_admin):
    """Happy path: event tanpa koordinat (latitude/longitude None) tetap valid."""
    now = datetime.now(timezone.utc)

    event_in = EventCreate(
        name="Event Online",
        estimated_attendee_count=999,
        start_datetime=now + timedelta(days=1),
        end_datetime=now + timedelta(days=2),
    )

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = now
        obj.status = EventStatus.PENDING_REVIEW

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    result = await create_event(mock_db, event_in, mock_admin)
    assert result.status == EventStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_list_events_admin_no_filter(mock_db, future_event, approved_future_event):
    """Happy path: admin melihat semua event tanpa filter."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = [
        future_event,
        approved_future_event,
    ]

    result = await list_events_admin(mock_db)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_events_admin_filter_pending(mock_db, future_event):
    """Happy path: admin filter event pending_review."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = [future_event]

    result = await list_events_admin(mock_db, status_filter="pending_review")

    assert len(result) == 1
    assert result[0].status == EventStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_list_events_admin_invalid_status(mock_db):
    """Edge case: status filter tidak valid → 400 INVALID_STATUS_FILTER."""
    with pytest.raises(HTTPException) as exc_info:
        await list_events_admin(mock_db, status_filter="blahblah")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "INVALID_STATUS_FILTER"

@pytest.mark.asyncio
async def test_review_event_approve(mock_db, mock_admin, future_event):
    """Happy path: admin approve event."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = future_event

    async def mock_refresh(obj):
        pass

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    review_in = EventReview(action="approve")
    result = await review_event(mock_db, future_event.id, review_in, mock_admin)

    assert result.status == EventStatus.APPROVED
    assert result.reviewed_by_admin_id == mock_admin.id
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_review_event_reject(mock_db, mock_admin, future_event):
    """Happy path: admin reject event."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = future_event

    async def mock_refresh(obj):
        pass

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    review_in = EventReview(action="reject")
    result = await review_event(mock_db, future_event.id, review_in, mock_admin)

    assert result.status == EventStatus.REJECTED


@pytest.mark.asyncio
async def test_review_event_not_found(mock_db, mock_admin):
    """Edge case: event ID tidak ditemukan → 404 EVENT_NOT_FOUND."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = None

    review_in = EventReview(action="approve")

    with pytest.raises(HTTPException) as exc_info:
        await review_event(mock_db, uuid.uuid4(), review_in, mock_admin)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error_code"] == "EVENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_review_event_with_edited_fields(mock_db, mock_admin, future_event):
    """Happy path: admin approve sambil edit nama dan jumlah peserta."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = future_event

    async def mock_refresh(obj):
        pass

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    review_in = EventReview(
        action="approve",
        name="Festival Batik Edisi Special",
        estimated_attendee_count=9999,
    )
    result = await review_event(mock_db, future_event.id, review_in, mock_admin)

    assert result.status == EventStatus.APPROVED
    assert result.name == "Festival Batik Edisi Special"
    assert result.estimated_attendee_count == 9999


@pytest.mark.asyncio
async def test_review_event_invalid_date_range_on_edit(mock_db, mock_admin, future_event):
    """Edge case: admin mengedit tanggal tapi end_datetime < start_datetime.

    Validasi dilakukan di dua layer:
    1. Pydantic model_validator (EventReview) → ValidationError jika keduanya dikirim sekaligus
    2. Service layer → HTTPException jika hanya satu tanggal yang diubah

    Test ini memverifikasi Pydantic layer (fail-fast, tidak sampai service).
    """
    from pydantic import ValidationError

    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError) as exc_info:
        EventReview(
            action="approve",
            start_datetime=now + timedelta(days=10),
            end_datetime=now + timedelta(days=5),  # LEBIH AWAL dari start
        )

    assert "end_datetime" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_events_public_only_approved(mock_db, approved_future_event):
    """Happy path: publik hanya melihat event approved."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = [
        approved_future_event
    ]

    result = await list_events_public(mock_db)

    assert len(result) == 1
    assert result[0].status == EventStatus.APPROVED


@pytest.mark.asyncio
async def test_list_events_public_upcoming_filter(mock_db, approved_future_event):
    """Happy path: filter upcoming=true mengembalikan event yang belum berakhir."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = [
        approved_future_event
    ]

    result = await list_events_public(mock_db, upcoming_only=True)

    assert len(result) == 1
    assert result[0].is_expired is False


@pytest.mark.asyncio
async def test_list_events_public_empty(mock_db):
    """Edge case: tidak ada event approved → return list kosong."""
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    result = await list_events_public(mock_db)

    assert result == []


@pytest.mark.asyncio
async def test_get_event_public_success(mock_db, approved_future_event):
    """Happy path: akses detail event approved."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = (
        approved_future_event
    )

    result = await get_event_public(mock_db, approved_future_event.id)

    assert result.id == approved_future_event.id
    assert result.is_expired is False


@pytest.mark.asyncio
async def test_get_event_public_expired_shows_flag(mock_db, approved_past_event):
    """Edge case: event approved tapi sudah lewat → is_expired = True."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = (
        approved_past_event
    )

    result = await get_event_public(mock_db, approved_past_event.id)

    assert result.is_expired is True
    assert result.status == EventStatus.APPROVED


@pytest.mark.asyncio
async def test_get_event_public_not_found(mock_db):
    """Edge case: event tidak ditemukan atau belum approved → 404."""
    mock_db.execute.return_value.scalars.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_event_public(mock_db, uuid.uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error_code"] == "EVENT_NOT_FOUND"
