from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import RoutingNoMerchantsException
from app.modules.merchant.models import Merchant
from app.modules.routing.service import routing_service


@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_merchant():
    m = Merchant(
        id=uuid4(),
        name="Test Merchant",
        category="kuliner",
        review_count=50,
        baseline_rating=4.5,
        is_redemption_partner=True
    )
    return m

@pytest.mark.asyncio
@patch("app.modules.routing.service.gemini_client")
@patch("app.modules.routing.service.osrm_client")
async def test_generate_itinerary_success(mock_osrm, mock_gemini, mock_db, mock_merchant):
    # Mock Gemini
    mock_gemini.parse_constraints = AsyncMock(return_value={
        "time_limit_minutes": 180,
        "budget_idr": 100000,
        "search_radius_meter": 2000,
        "interest_categories": "bebas",
        "avoid_crowds": False
    })

    # Mock DB Result for merchants
    mock_db_result = MagicMock()
    # Return 1 merchant with distance=1000, lon=106.0, lat=-6.0
    mock_db_result.all.return_value = [(mock_merchant, 1000.0, 106.0, -6.0)]
    mock_db.execute = AsyncMock(return_value=mock_db_result)

    # Mock OSRM
    mock_osrm.get_route = AsyncMock(return_value={
        "route_geojson": {"type": "LineString", "coordinates": [[106.0, -6.0]]},
        "duration_minutes": 30
    })

    user_id = uuid4()
    itinerary = await routing_service.generate_itinerary(
        db=mock_db,
        user_id=user_id,
        raw_query="Cari tempat makan bebas",
        current_lat=-6.1,
        current_lon=106.1
    )

    assert itinerary.user_id == user_id
    assert len(itinerary.waypoints) == 1
    assert itinerary.waypoints[0]["merchant_id"] == str(mock_merchant.id)
    assert itinerary.estimated_duration_minutes == 30
    assert itinerary.status == "active"

@pytest.mark.asyncio
@patch("app.modules.routing.service.gemini_client")
async def test_generate_itinerary_no_merchants(mock_gemini, mock_db):
    mock_gemini.parse_constraints = AsyncMock(return_value={})

    mock_db_result = MagicMock()
    mock_db_result.all.return_value = [] # Kosong
    mock_db.execute = AsyncMock(return_value=mock_db_result)

    with pytest.raises(RoutingNoMerchantsException):
        await routing_service.generate_itinerary(
            db=mock_db,
            user_id=uuid4(),
            raw_query="Test empty",
            current_lat=0,
            current_lon=0
        )

@pytest.mark.asyncio
@patch("app.modules.routing.service.gemini_client")
@patch("app.modules.routing.service.osrm_client")
async def test_generate_itinerary_with_vector(mock_osrm, mock_gemini, mock_db, mock_merchant):
    # Spesifik minat "kopi"
    mock_gemini.parse_constraints = AsyncMock(return_value={
        "interest_categories": "kopi"
    })
    mock_gemini.embed_text = AsyncMock(return_value=[0.1]*768)

    # Result 1: merchants
    mock_db_result_1 = MagicMock()
    mock_db_result_1.all.return_value = [(mock_merchant, 500.0, 106.0, -6.0)]

    # Result 2: vector distance
    mock_db_result_2 = MagicMock()
    class RowProxy:
        merchant_id = mock_merchant.id
        min_distance = 0.2

    mock_db_result_2.__iter__.return_value = [RowProxy()]

    # Kita perlu membuat db.execute merespon 2 query berbeda.
    mock_db.execute = AsyncMock(side_effect=[mock_db_result_1, mock_db_result_2])

    mock_osrm.get_route = AsyncMock(return_value={
        "route_geojson": {},
        "duration_minutes": 15
    })

    itinerary = await routing_service.generate_itinerary(
        db=mock_db,
        user_id=uuid4(),
        raw_query="Kopi enak",
        current_lat=0,
        current_lon=0
    )

    assert len(itinerary.waypoints) == 1
