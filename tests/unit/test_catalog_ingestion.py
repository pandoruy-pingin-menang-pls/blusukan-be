from unittest.mock import AsyncMock, patch

import pytest
from fastapi import UploadFile

import app.db.base  # noqa: F401
from app.core.exceptions import IngestLimitReachedException
from app.modules.catalog.schemas import CatalogConfirmItem, CatalogConfirmRequest
from app.modules.catalog.service import MAX_DAILY_INGEST, CatalogService
from app.modules.merchant.models import Merchant


@pytest.fixture
def mock_merchant():
    merchant = Merchant(
        id="12345678-1234-5678-1234-567812345678",
        name="Warung Test",
        daily_ingest_count=0,
        status="pending",
        ingest_count_reset_at=None
    )
    return merchant

@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Support async context manager if needed, but here we just mock methods
    return db

@pytest.mark.asyncio
async def test_ingest_menu_limit_reached(mock_merchant, mock_db):
    from datetime import date
    mock_merchant.daily_ingest_count = MAX_DAILY_INGEST
    mock_merchant.ingest_count_reset_at = date.today()

    file_mock = AsyncMock(spec=UploadFile)

    with pytest.raises(IngestLimitReachedException):
        await CatalogService.ingest_menu(mock_db, mock_merchant, file_mock)

@pytest.mark.asyncio
@patch("app.modules.catalog.service.gemini_client")
@patch("app.modules.catalog.service.supabase_storage")
async def test_ingest_menu_success(mock_supabase, mock_gemini, mock_merchant, mock_db):
    mock_merchant.ingest_count_reset_at = mock_merchant.ingest_count_reset_at
    mock_supabase.upload_menu_image = AsyncMock(return_value="http://fake-url.com/img.jpg")

    # Simulate Gemini returning valid parsed data
    mock_gemini.extract_menu_from_image = AsyncMock(return_value=[
        {"item_name": "Nasi Goreng", "price": 15000, "category": "culinary"}
    ])

    file_mock = AsyncMock(spec=UploadFile)
    file_mock.read.return_value = b"fakebytes"
    file_mock.content_type = "image/jpeg"

    response = await CatalogService.ingest_menu(mock_db, mock_merchant, file_mock)

    assert response.image_url == "http://fake-url.com/img.jpg"
    assert len(response.draft_items) == 1
    assert response.draft_items[0].item_name == "Nasi Goreng"
    assert mock_merchant.daily_ingest_count == 1

@pytest.mark.asyncio
@patch("app.modules.catalog.service.gemini_client")
@patch("app.modules.catalog.service.supabase_storage")
async def test_ingest_menu_malformed_json_fallback(mock_supabase, mock_gemini, mock_merchant, mock_db):
    mock_supabase.upload_menu_image = AsyncMock(return_value="http://fake-url.com/img.jpg")

    # Simulate Gemini returning empty list (e.g. from JSON parse failure caught in gemini_client)
    mock_gemini.extract_menu_from_image = AsyncMock(return_value=[])

    file_mock = AsyncMock(spec=UploadFile)
    file_mock.read.return_value = b"fakebytes"

    response = await CatalogService.ingest_menu(mock_db, mock_merchant, file_mock)

    assert len(response.draft_items) == 0
    # Should not crash, just return 0 items

@pytest.mark.asyncio
@patch("app.modules.catalog.service.gemini_client")
async def test_confirm_catalog_success(mock_gemini, mock_merchant, mock_db):
    mock_gemini.embed_text = AsyncMock(return_value=[0.1] * 768)

    request = CatalogConfirmRequest(
        image_url="http://fake-url.com/img.jpg",
        items=[
            CatalogConfirmItem(item_name="Nasi Goreng", price=15000, category="culinary", source_type="photo"),
            CatalogConfirmItem(item_name="Sate", price=None, category="culinary", source_type="manual") # NULL price
        ]
    )

    items = await CatalogService.confirm_catalog(mock_db, mock_merchant, request)

    assert len(items) == 2
    assert items[0].confidence == "high" # price is present
    assert items[1].confidence == "low"  # price is NULL
    assert items[0].embedding == [0.1] * 768
    assert mock_merchant.status == "active"
