import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User, UserRole

# Create a mock admin user
mock_admin = User(
    id=uuid.uuid4(),
    email="admin@test.com",
    role=UserRole.ADMIN,
    full_name="Admin User"
)

# Create a mock wisatawan user
mock_wisatawan = User(
    id=uuid.uuid4(),
    email="wisatawan@test.com",
    role=UserRole.WISATAWAN,
    full_name="Wisatawan User"
)

async def override_require_admin_success():
    return mock_admin

async def override_require_admin_forbidden():
    from fastapi import HTTPException
    raise HTTPException(status_code=403, detail="Akses ditolak")

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_monitoring_stats_admin_access(mock_db_session):
    # Setup mock returns for db.execute
    mock_active_users = MagicMock()
    mock_active_users.scalar.return_value = 15

    mock_total_act = MagicMock()
    mock_total_act.scalar.return_value = 45

    mock_dist = MagicMock()
    mock_dist.all.return_value = [("wisatawan", 30), ("pedagang", 15)]

    mock_db_session.execute.side_effect = [mock_active_users, mock_total_act, mock_dist]

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin_success

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/monitoring/stats")

    # Restore overrides
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["active_users_today"] == 15
    assert data["total_activities_today"] == 45
    assert data["distribution_by_role"]["wisatawan"] == 30
    assert data["distribution_by_role"]["pedagang"] == 15

@pytest.mark.asyncio
async def test_monitoring_rbac_rejection(mock_db_session):
    # Override dependencies to simulate non-admin access
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin_forbidden

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/monitoring/stats")

    app.dependency_overrides.clear()

    # Must be forbidden
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_monitoring_activities(mock_db_session):
    # Mock activities list
    from datetime import datetime
    act_mock = MagicMock()
    act_mock.id = uuid.uuid4()
    act_mock.user_id = uuid.uuid4()
    act_mock.user_role = "wisatawan"
    act_mock.action = "Accessed /api/test"
    act_mock.endpoint = "/api/test"
    act_mock.method = "POST"
    act_mock.created_at = datetime.now()

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [act_mock]
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin_success

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/admin/monitoring/activities")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
    assert len(data["activities"]) == 1
    assert data["activities"][0]["role"] == "wisatawan"
