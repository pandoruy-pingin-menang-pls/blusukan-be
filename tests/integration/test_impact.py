import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User, UserRole
from app.modules.events.models import EventStatus
from app.modules.events.schemas import EventGenre

mock_admin = User(
    id=uuid.uuid4(),
    email="admin_impact@test.com",
    role=UserRole.ADMIN,
    full_name="Admin Impact"
)

async def override_require_admin_success():
    return mock_admin

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_impact_metrics_returns_valid_data(mock_db_session):
    # Setup mock returns for the 4 queries
    mock_wisatawan = MagicMock()
    mock_wisatawan.scalar.return_value = 100

    mock_pedagang = MagicMock()
    mock_pedagang.scalar.return_value = 25

    mock_pending_events = MagicMock()
    mock_pending_events.scalar.return_value = 12

    mock_total_events = MagicMock()
    mock_total_events.scalar.return_value = 50

    mock_db_session.execute.side_effect = [
        mock_wisatawan,
        mock_pedagang,
        mock_pending_events,
        mock_total_events
    ]

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin_success

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/impact/metrics")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()

    # 12 pending events > 10, should trigger "Perlu Perhatian"
    assert data["condition"] == "Perlu Perhatian"
    assert len(data["metrics"]) == 4

    # Check values mapped correctly
    metrics_dict = {m["label"]: m["value"] for m in data["metrics"]}
    assert metrics_dict["Total Wisatawan"] == 100
    assert metrics_dict["Total Pedagang Aktif"] == 25
    assert metrics_dict["Event Menunggu Review"] == 12
    assert metrics_dict["Total Event"] == 50


@pytest.mark.asyncio
async def test_impact_action_logs_filters(mock_db_session):
    # Setup mock return for events query
    evt_mock = MagicMock()
    evt_mock.id = uuid.uuid4()
    evt_mock.name = "Pasar Malam"
    evt_mock.genre = EventGenre.CULTURAL
    evt_mock.status = EventStatus.PENDING_REVIEW
    evt_mock.created_at = datetime.now()

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [evt_mock]
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin_success

    # Test with filters
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/impact/action-logs?period=today&status=pending_review")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Pasar Malam"
    assert data["items"][0]["status"] == "pending_review"
    assert data["items"][0]["priority"] == "High"
