from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import ItineraryNotFoundException
from app.modules.routing.models import Itinerary
from app.modules.routing.router import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)

# Bypass dependency injeksi get_current_user dan get_db
async def mock_get_current_user():
    class MockUser:
        id = uuid4()
    return MockUser()

async def mock_get_db():
    pass

from app.db.session import get_db  # noqa: E402
from app.modules.auth.dependencies import get_current_user  # noqa: E402

app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_db] = mock_get_db


@patch("app.modules.routing.router.routing_service")
def test_generate_itinerary_endpoint(mock_service):
    # Mock return Itinerary dari service
    mock_itinerary = Itinerary(
        id=uuid4(),
        user_id=uuid4(),
        raw_query="Coba",
        parsed_constraints={},
        waypoints=[],
        route_geojson={},
        status="active",
        created_at=datetime.now()
    )
    mock_service.generate_itinerary = AsyncMock(return_value=mock_itinerary)

    response = client.post(
        "/itineraries",
        json={
            "raw_query": "Coba cari tempat",
            "current_lat": -6.1,
            "current_lon": 106.1
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["raw_query"] == "Coba"


@patch("app.modules.routing.router.routing_service")
def test_generate_itinerary_endpoint_error(mock_service):
    mock_service.generate_itinerary = AsyncMock(side_effect=ValueError("Test error"))

    response = client.post(
        "/itineraries",
        json={
            "raw_query": "Error bang",
            "current_lat": 0,
            "current_lon": 0
        }
    )
    # Router menangkap Exception umum menjadi 500
    assert response.status_code == 500

@patch("app.modules.routing.router.select")
def test_get_itinerary_success(mock_select):

    # Mock db.execute di dependency adalah MagicMock, tidak semudah itu via FastAPI testclient
    # Kita butuh bypass AsyncSession dependency jika ingin test DB query di dalam router.
    # Namun demi simplicity dan code coverage hackathon, mari kita import router dan panggil as function.
    pass

@pytest.mark.asyncio
async def test_get_itinerary_direct():
    from app.modules.routing.router import get_itinerary, start_itinerary

    class MockUser:
        id = uuid4()

    mock_itinerary = Itinerary(
        id=uuid4(),
        user_id=uuid4(),
        raw_query="Coba",
        parsed_constraints={},
        waypoints=[],
        route_geojson={},
        status="draft",
        created_at=datetime.now()
    )

    class MockResult:
        def scalars(self):
            class ScalarResult:
                def first(self):
                    return mock_itinerary
            return ScalarResult()

    mock_db = AsyncMock()
    mock_db.execute.return_value = MockResult()

    result = await get_itinerary(itinerary_id=uuid4(), current_user=MockUser(), db=mock_db)
    assert result.status == "draft"

    # Test patch
    patch_res = await start_itinerary(itinerary_id=uuid4(), current_user=MockUser(), db=mock_db)
    assert patch_res["message"] == "Itinerary started"
    assert mock_itinerary.status == "active"

@pytest.mark.asyncio
async def test_get_itinerary_not_found():
    from app.modules.routing.router import get_itinerary, start_itinerary

    class MockUser:
        id = uuid4()

    class MockResultEmpty:
        def scalars(self):
            class ScalarResult:
                def first(self):
                    return None
            return ScalarResult()

    mock_db = AsyncMock()
    mock_db.execute.return_value = MockResultEmpty()

    with pytest.raises(ItineraryNotFoundException):
        await get_itinerary(itinerary_id=uuid4(), current_user=MockUser(), db=mock_db)

    with pytest.raises(ItineraryNotFoundException):
        await start_itinerary(itinerary_id=uuid4(), current_user=MockUser(), db=mock_db)
