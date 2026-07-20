import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import CREDIT_SCORE_MAX_SCORE
from app.modules.credit_score.service import calculate_credit_score
from app.modules.merchant.models import Merchant


@pytest.mark.asyncio
async def test_credit_score_insufficient_data():
    db = AsyncMock()

    mock_history_result = MagicMock()
    mock_history_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_history_result

    # Umur < 30 hari (misal 10 hari)
    merchant = Merchant(
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=10),
    )

    response = await calculate_credit_score(merchant, db)

    assert response.current_score is None
    assert response.data_status == "insufficient_data"
    assert response.history == []


@pytest.mark.asyncio
async def test_credit_score_calculation():
    db = AsyncMock()

    mock_tx_result = MagicMock()
    mock_tx_result.fetchone.return_value = (15, 25000000.0)

    mock_history_result = MagicMock()
    mock_history_result.scalars.return_value.all.return_value = []

    db.execute.side_effect = [mock_tx_result, mock_history_result]

    merchant = Merchant(
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=90),
        baseline_rating=4.5,
        review_count=10,
    )

    response = await calculate_credit_score(merchant, db)

    assert response.data_status == "sufficient"
    # A: 15/30 * 1000 = 500. B: 25M/50M * 1000 = 500. C: 90/180 * 1000 = 500. D: 4.5/5.0 * 1000 = 900
    # Total: 500*0.4 + 500*0.3 + 500*0.2 + 900*0.1 = 200 + 150 + 100 + 90 = 540
    assert response.current_score == 540


@pytest.mark.asyncio
async def test_credit_score_zero_reviews():
    db = AsyncMock()

    mock_tx_result = MagicMock()
    mock_tx_result.fetchone.return_value = (15, 25000000.0)

    mock_history_result = MagicMock()
    mock_history_result.scalars.return_value.all.return_value = []

    db.execute.side_effect = [mock_tx_result, mock_history_result]

    merchant = Merchant(
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=90),
        baseline_rating=0.0,  # should be overridden because review_count=0
        review_count=0,
    )

    response = await calculate_credit_score(merchant, db)

    # Rating 4.0 -> score_d = (4.0/5.0)*1000 = 800
    # Total: 500*0.4 + 500*0.3 + 500*0.2 + 800*0.1 = 200 + 150 + 100 + 80 = 530
    assert response.current_score == 530


@pytest.mark.asyncio
async def test_credit_score_max_cap():
    db = AsyncMock()

    mock_tx_result = MagicMock()
    # Exceed logic thresholds
    mock_tx_result.fetchone.return_value = (50, 100000000.0)

    mock_history_result = MagicMock()
    mock_history_result.scalars.return_value.all.return_value = []

    db.execute.side_effect = [mock_tx_result, mock_history_result]

    merchant = Merchant(
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=365),  # 1 year
        baseline_rating=5.0,
        review_count=100,
    )

    response = await calculate_credit_score(merchant, db)

    assert response.data_status == "sufficient"
    assert response.current_score == CREDIT_SCORE_MAX_SCORE  # capped at 1000
