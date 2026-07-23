import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.modules.gamification.models import DiscountType
from app.modules.gamification.router import user_gamification_router
from app.modules.gamification.service import gamification_service


@pytest.fixture
def mock_db():
    session = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_list_all_promos_returns_paginated_global_promos(mock_db):
    now = datetime.now(timezone.utc)
    promo_id = uuid.uuid4()
    merchant_id = uuid.uuid4()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    rows_result = MagicMock()
    rows_result.mappings.return_value.all.return_value = [
        {
            "promo_id": promo_id,
            "merchant_id": merchant_id,
            "merchant_name": "Warung Soto Pak Darmo",
            "merchant_category": "KULINER_PANAS",
            "title": "Gratis Es Teh",
            "discount_type": DiscountType.FIXED_AMOUNT,
            "discount_value": 5000,
            "stamp_required_count": 3,
            "is_active": True,
            "valid_until": now + timedelta(days=7),
            "created_at": now,
        }
    ]

    mock_db.execute.side_effect = [count_result, rows_result]

    result = await gamification_service.list_all_promos(
        db=mock_db,
        status="active",
        merchant_id=merchant_id,
        q="soto",
        page=2,
        limit=10,
    )

    assert result["total"] == 1
    assert result["page"] == 2
    assert result["limit"] == 10
    assert len(result["items"]) == 1
    assert result["items"][0]["promo_id"] == promo_id
    assert result["items"][0]["merchant_id"] == merchant_id
    assert result["items"][0]["merchant_name"] == "Warung Soto Pak Darmo"
    assert result["items"][0]["merchant_category"] == "KULINER_PANAS"
    assert result["items"][0]["discount_value"] == 5000.0
    assert result["items"][0]["status"] == "active"
    assert mock_db.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_all_promos_marks_expired_status(mock_db):
    now = datetime.now(timezone.utc)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    rows_result = MagicMock()
    rows_result.mappings.return_value.all.return_value = [
        {
            "promo_id": uuid.uuid4(),
            "merchant_id": uuid.uuid4(),
            "merchant_name": "Batik Amanah",
            "merchant_category": "KERAJINAN",
            "title": "Diskon Batik",
            "discount_type": DiscountType.PERCENTAGE,
            "discount_value": 15,
            "stamp_required_count": 5,
            "is_active": True,
            "valid_until": now - timedelta(days=1),
            "created_at": now - timedelta(days=30),
        }
    ]

    mock_db.execute.side_effect = [count_result, rows_result]

    result = await gamification_service.list_all_promos(
        db=mock_db,
        status="expired",
    )

    assert result["items"][0]["status"] == "expired"


@pytest.mark.asyncio
async def test_list_all_promos_rejects_invalid_status(mock_db):
    with pytest.raises(ValueError):
        await gamification_service.list_all_promos(db=mock_db, status="pending")


def test_get_global_promos_endpoint_calls_service_with_filters():
    app = FastAPI()
    app.include_router(user_gamification_router)

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    client = TestClient(app)

    merchant_id = uuid.uuid4()
    promo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    payload = {
        "items": [
            {
                "promo_id": promo_id,
                "merchant_id": merchant_id,
                "merchant_name": "Jamu Gendhis",
                "merchant_category": "KULINER_DINGIN",
                "title": "Diskon Jamu",
                "discount_type": DiscountType.FIXED_AMOUNT,
                "discount_value": 3000,
                "stamp_required_count": 2,
                "is_active": True,
                "status": "active",
                "valid_until": now + timedelta(days=3),
                "created_at": now,
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 5,
    }

    with patch(
        "app.modules.gamification.router.gamification_service.list_all_promos",
        new_callable=AsyncMock,
        return_value=payload,
    ) as mock_list_all_promos:
        response = client.get(
            f"/promos?status=active&merchant_id={merchant_id}&q=jamu&page=1&limit=5"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["promo_id"] == str(promo_id)
    assert body["items"][0]["merchant_name"] == "Jamu Gendhis"
    mock_list_all_promos.assert_awaited_once()
    call_kwargs = mock_list_all_promos.await_args.kwargs
    assert call_kwargs["status"] == "active"
    assert call_kwargs["merchant_id"] == merchant_id
    assert call_kwargs["q"] == "jamu"
    assert call_kwargs["page"] == 1
    assert call_kwargs["limit"] == 5
