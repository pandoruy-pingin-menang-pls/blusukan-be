import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import DuplicateMerchantException
from app.modules.auth.models import User, UserRole
from app.modules.merchant.schemas import MerchantCreate
from app.modules.merchant.service import register_merchant


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    session.add = MagicMock()

    async def mock_refresh(obj):
        from datetime import datetime
        if not hasattr(obj, "id") or not obj.id:
            obj.id = uuid.uuid4()
        obj.is_verified = False
        obj.is_active = True
        obj.created_at = datetime.now()

    session.refresh = AsyncMock(side_effect=mock_refresh)
    return session


@pytest.mark.asyncio
async def test_register_merchant_success(mock_db_session):
    # Skenario: User belum punya toko (has_merchant_profile=False)
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        role=UserRole.WISATAWAN,
        has_merchant_profile=False
    )

    merchant_in = MerchantCreate(
        name="Warung Kopi",
        category="Minuman",
        address="Jl. Sudirman",
        latitude=-7.5,
        longitude=110.8
    )

    result = await register_merchant(
        db=mock_db_session,
        user=mock_user,
        merchant_in=merchant_in,
        token_to_revoke="old_token"
    )

    # Pastikan data merchant kembali
    assert "merchant" in result
    assert result["merchant"].name == "Warung Kopi"

    # Pastikan token baru dicetak
    assert "tokens" in result
    assert "access_token" in result["tokens"]

    # Pastikan status user di-update
    assert mock_user.role == UserRole.PEDAGANG
    assert mock_user.has_merchant_profile is True

    # Cek pemanggilan db
    assert mock_db_session.add.call_count == 3  # 1 for merchant, 1 for user, 1 for refresh_token
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_merchant_duplicate(mock_db_session):
    # Skenario: User sudah punya profil toko
    mock_user = User(
        id=uuid.uuid4(),
        email="test2@example.com",
        role=UserRole.PEDAGANG,
        has_merchant_profile=True
    )

    merchant_in = MerchantCreate(
        name="Toko Kedua",
        category="Makanan",
        latitude=-7.5,
        longitude=110.8
    )

    with pytest.raises(DuplicateMerchantException) as exc_info:
        await register_merchant(
            db=mock_db_session,
            user=mock_user,
            merchant_in=merchant_in,
            token_to_revoke="old_token"
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "MERCHANT_ALREADY_EXISTS"

    # DB tidak boleh di-commit
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()
