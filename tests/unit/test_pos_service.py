import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import InvalidTransactionException, ItineraryOwnershipException
from app.modules.routing.models import Itinerary
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import TransactionCreate
from app.modules.transactions.service import (
    SUSPICIOUS_TRANSACTION_THRESHOLD,
    transaction_service,
)


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_log_transaction_success(mock_db):
    """Happy path: log transaksi berhasil (tanpa itinerary)."""
    merchant_id = uuid.uuid4()
    tx_in = TransactionCreate(
        nominal_value=15000,
        item_reference={"nasi": 1}
    )

    # Idempotency check return None
    mock_db.execute.return_value.scalars.return_value.first.return_value = None

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    result = await transaction_service.log_transaction(mock_db, merchant_id, tx_in)

    assert result.nominal_value == 15000
    assert result.is_suspicious is False
    assert result.stamp_awarded is False
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_log_transaction_invalid_nominal(mock_db):
    """Edge case: nominal <= 0."""
    merchant_id = uuid.uuid4()
    tx_in = TransactionCreate(nominal_value=0)

    with pytest.raises(InvalidTransactionException):
        await transaction_service.log_transaction(mock_db, merchant_id, tx_in)


@pytest.mark.asyncio
async def test_log_transaction_suspicious(mock_db):
    """Edge case: nominal sangat besar."""
    merchant_id = uuid.uuid4()
    tx_in = TransactionCreate(nominal_value=SUSPICIOUS_TRANSACTION_THRESHOLD + 1000)

    mock_db.execute.return_value.scalars.return_value.first.return_value = None

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    result = await transaction_service.log_transaction(mock_db, merchant_id, tx_in)

    assert result.is_suspicious is True


@pytest.mark.asyncio
async def test_log_transaction_idempotent(mock_db):
    """Edge case: transaksi dikirim ulang oleh FE (client_reference_id sama)."""
    merchant_id = uuid.uuid4()
    tx_in = TransactionCreate(
        nominal_value=15000,
        client_reference_id="REQ_123"
    )

    existing_tx = Transaction(
        id=uuid.uuid4(),
        nominal_value=15000,
        client_reference_id="REQ_123",
        linked_itinerary_id=None
    )

    # Simulate DB return existing
    mock_db.execute.return_value.scalars.return_value.first.return_value = existing_tx

    result = await transaction_service.log_transaction(mock_db, merchant_id, tx_in)

    assert result.id == existing_tx.id
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.transactions.service.gamification_service")
async def test_log_transaction_with_itinerary(mock_gamification, mock_db):
    """Happy path: ada itinerary, trigger stamp gamification."""
    merchant_id = uuid.uuid4()
    itinerary_id = uuid.uuid4()
    tourist_id = uuid.uuid4()

    tx_in = TransactionCreate(
        nominal_value=15000,
        linked_itinerary_id=itinerary_id
    )

    # Mock itinerary ada di DB
    itinerary = Itinerary(id=itinerary_id, user_id=tourist_id)
    # Query itinerary -> itinerary
    mock_db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=itinerary))))
    ]

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    # Mock gamification return success
    mock_gamification.award_stamp = AsyncMock()

    result = await transaction_service.log_transaction(mock_db, merchant_id, tx_in)

    assert result.stamp_awarded is True
    assert result.tourist_user_id == tourist_id
    mock_gamification.award_stamp.assert_called_once()


@pytest.mark.asyncio
async def test_log_transaction_itinerary_not_found(mock_db):
    """Edge case: linked_itinerary_id dikirim tapi tidak ada di DB."""
    merchant_id = uuid.uuid4()
    itinerary_id = uuid.uuid4()

    tx_in = TransactionCreate(
        nominal_value=15000,
        linked_itinerary_id=itinerary_id
    )

    # First query -> None, Second query -> None
    mock_db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))
    ]

    with pytest.raises(ItineraryOwnershipException):
        await transaction_service.log_transaction(mock_db, merchant_id, tx_in)


@pytest.mark.asyncio
async def test_get_transaction_summary(mock_db):
    """Happy path: summary omzet harian."""
    merchant_id = uuid.uuid4()

    mock_row = MagicMock()
    mock_row.total_omzet = 150000
    mock_row.total_transaksi = 10

    mock_db.execute.return_value.first.return_value = mock_row

    result = await transaction_service.get_transaction_summary(mock_db, merchant_id)

    assert result["total_omzet"] == 150000
    assert result["total_transaksi"] == 10
