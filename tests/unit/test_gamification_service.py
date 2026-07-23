import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    DuplicateStampException,
    InsufficientStampsException,
    MerchantOwnershipException,
    PromoExpiredException,
    RedemptionAlreadyUsedException,
    RedemptionCodeExpiredException,
)
from app.modules.auth.models import User
from app.modules.gamification.models import (
    DiscountType,
    Promo,
    PromoRedemption,
    RedemptionStatus,
)
from app.modules.gamification.schemas import PromoCreate
from app.modules.gamification.service import gamification_service
from app.modules.merchant.models import Merchant


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.add = MagicMock()
    return session

@pytest.fixture
def mock_merchant():
    return Merchant(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Toko Test",
    )

@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        email="user@test.com",
    )

@pytest.mark.asyncio
async def test_award_stamp_success(mock_db, mock_user, mock_merchant):
    """Happy path: award stamp berhasil."""
    tx_id = uuid.uuid4()

    result = await gamification_service.award_stamp(mock_db, mock_user.id, mock_merchant.id, tx_id)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result.user_id == mock_user.id
    assert result.merchant_id == mock_merchant.id
    assert result.transaction_id == tx_id

@pytest.mark.asyncio
async def test_award_stamp_duplicate(mock_db, mock_user, mock_merchant):
    """Edge case: stamp sudah ada untuk transaksi ini (idempotent)."""
    tx_id = uuid.uuid4()

    # Simulate integrity error
    mock_db.commit.side_effect = IntegrityError("duplicate key", params=[], orig=Exception())

    with pytest.raises(DuplicateStampException):
        await gamification_service.award_stamp(mock_db, mock_user.id, mock_merchant.id, tx_id)

    mock_db.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_create_promo_success(mock_db, mock_merchant):
    """Happy path: membuat promo."""
    valid_until = datetime.now(timezone.utc) + timedelta(days=7)
    promo_in = PromoCreate(
        title="Diskon 20K",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=20000,
        stamp_required_count=5,
        valid_until=valid_until
    )

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    result = await gamification_service.create_promo(mock_db, mock_merchant.id, promo_in)

    assert result.title == "Diskon 20K"
    assert result.stamp_required_count == 5
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_redeem_promo_success(mock_db, mock_user):
    """Happy path: redeem promo berhasil."""
    promo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    promo = Promo(
        id=promo_id,
        merchant_id=uuid.uuid4(),
        stamp_required_count=3,
        is_active=True,
        valid_until=now + timedelta(days=1)
    )

    # Mock urutan eksekusi:
    # 1. Total stamp = 5
    # 2. Promo = promo
    # 3. Used stamp = 0
    mock_db.execute.side_effect = [
        MagicMock(), # User lock
        MagicMock(scalar_one=MagicMock(return_value=5)), # User stamp count
        MagicMock(scalar_one=MagicMock(return_value=0)), # Used stamp count
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=promo)))), # Promo
    ]

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    result = await gamification_service.redeem_promo(mock_db, mock_user.id, promo_id)

    assert result.status == RedemptionStatus.PENDING
    assert len(result.redemption_code) == 8
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_redeem_promo_insufficient_stamps(mock_db, mock_user):
    """Edge case: stamp tidak cukup."""
    promo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    promo = Promo(
        id=promo_id,
        stamp_required_count=5,
        is_active=True,
        valid_until=now + timedelta(days=1)
    )

    # User cuma punya 2 stamp
    mock_db.execute.side_effect = [
        MagicMock(), # User lock
        MagicMock(scalar_one=MagicMock(return_value=2)), # User stamp count
        MagicMock(scalar_one=MagicMock(return_value=0)), # Used stamp count
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=promo)))), # Promo
    ]

    with pytest.raises(InsufficientStampsException):
        await gamification_service.redeem_promo(mock_db, mock_user.id, promo_id)

@pytest.mark.asyncio
async def test_redeem_promo_expired(mock_db, mock_user):
    """Edge case: promo expired."""
    promo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    promo = Promo(
        id=promo_id,
        stamp_required_count=1,
        is_active=True,
        valid_until=now - timedelta(days=1)
    )

    mock_db.execute.side_effect = [
        MagicMock(), # User lock
        MagicMock(scalar_one=MagicMock(return_value=5)),
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=promo)))),
    ]

    with pytest.raises(PromoExpiredException):
        await gamification_service.redeem_promo(mock_db, mock_user.id, promo_id)

@pytest.mark.asyncio
async def test_confirm_redemption_success(mock_db, mock_merchant):
    """Happy path: merchant confirm redemption."""
    code = "ABCDEF12"
    now = datetime.now(timezone.utc)

    redemption = PromoRedemption(
        id=uuid.uuid4(),
        promo_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        redemption_code=code,
        status=RedemptionStatus.PENDING,
        expires_at=now + timedelta(minutes=10)
    )
    redemption.promo = Promo(merchant_id=mock_merchant.id)

    mock_db.execute.return_value.scalars.return_value.first.return_value = redemption

    result = await gamification_service.confirm_redemption(mock_db, mock_merchant.id, code)

    assert result.status == RedemptionStatus.REDEEMED
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_confirm_redemption_wrong_merchant(mock_db):
    """Edge case: merchant confirm kode punya merchant lain."""
    code = "ABCDEF12"
    merchant_id = uuid.uuid4()

    redemption = PromoRedemption(
        id=uuid.uuid4(),
        status=RedemptionStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    # Promo dimiliki merchant lain
    redemption.promo = Promo(merchant_id=uuid.uuid4())

    mock_db.execute.return_value.scalars.return_value.first.return_value = redemption

    with pytest.raises(MerchantOwnershipException):
        await gamification_service.confirm_redemption(mock_db, merchant_id, code)

@pytest.mark.asyncio
async def test_confirm_redemption_already_used(mock_db, mock_merchant):
    """Edge case: kode sudah terpakai."""
    code = "ABCDEF12"

    redemption = PromoRedemption(
        id=uuid.uuid4(),
        status=RedemptionStatus.REDEEMED,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    redemption.promo = Promo(merchant_id=mock_merchant.id)

    mock_db.execute.return_value.scalars.return_value.first.return_value = redemption

    with pytest.raises(RedemptionAlreadyUsedException):
        await gamification_service.confirm_redemption(mock_db, mock_merchant.id, code)

@pytest.mark.asyncio
async def test_confirm_redemption_expired(mock_db, mock_merchant):
    """Edge case: kode sudah TTL expired."""
    code = "ABCDEF12"
    now = datetime.now(timezone.utc)

    redemption = PromoRedemption(
        id=uuid.uuid4(),
        status=RedemptionStatus.PENDING,
        expires_at=now - timedelta(minutes=1) # Sudah lewat
    )
    redemption.promo = Promo(merchant_id=mock_merchant.id)

    mock_db.execute.return_value.scalars.return_value.first.return_value = redemption

    with pytest.raises(RedemptionCodeExpiredException):
        await gamification_service.confirm_redemption(mock_db, mock_merchant.id, code)

    # Pastikan status di-update ke EXPIRED
    assert redemption.status == RedemptionStatus.EXPIRED
    mock_db.commit.assert_called_once()
