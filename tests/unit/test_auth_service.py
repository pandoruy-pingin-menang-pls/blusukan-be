import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta

from app.modules.auth.schemas import UserCreate, LoginRequest
from app.modules.auth.service import (
    register_user,
    authenticate_user,
    refresh_access_token,
    logout_user
)
from app.modules.auth.models import User, RefreshToken, UserRole
from app.core.security import get_password_hash

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Hasil dari await db.execute() adalah object synchronous, jadi kita mock dengan MagicMock
    session.execute.return_value = MagicMock()
    return session

@pytest.mark.asyncio
async def test_register_user_success(mock_db_session):
    # Skenario: User belum ada di database
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None
    
    user_in = UserCreate(email="test@example.com", password="password123", full_name="Test User")
    
    result = await register_user(mock_db_session, user_in)
    
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"].email == "test@example.com"
    mock_db_session.add.assert_called()
    mock_db_session.commit.assert_called()

@pytest.mark.asyncio
async def test_register_user_email_exists(mock_db_session):
    # Skenario: Email sudah dipakai orang lain
    mock_user = User(email="test@example.com")
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_user
    
    user_in = UserCreate(email="test@example.com", password="password123")
    
    with pytest.raises(HTTPException) as exc_info:
        await register_user(mock_db_session, user_in)
        
    assert exc_info.value.status_code == 400
    assert "terdaftar" in exc_info.value.detail

@pytest.mark.asyncio
async def test_authenticate_user_success(mock_db_session):
    # Skenario: Login sukses
    mock_user = User(
        id="123", 
        email="test@example.com", 
        hashed_password=get_password_hash("password123"), 
        role=UserRole.WISATAWAN, 
        has_merchant_profile=False
    )
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_user
    
    login_req = LoginRequest(email="test@example.com", password="password123")
    
    result = await authenticate_user(mock_db_session, login_req)
    
    assert "access_token" in result
    assert "refresh_token" in result
    
@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(mock_db_session):
    # Skenario: Password salah
    mock_user = User(email="test@example.com", hashed_password=get_password_hash("password123"))
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_user
    
    login_req = LoginRequest(email="test@example.com", password="wrongpassword")
    
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(mock_db_session, login_req)
        
    assert exc_info.value.status_code == 401
    assert "salah" in exc_info.value.detail

@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(mock_db_session):
    # Skenario: Hacker menggunakan refresh token yang sudah di-revoke (logout)
    raw_refresh_token = "user123:somehex"
    
    mock_token = RefreshToken(
        user_id="user123", 
        token_hash=get_password_hash(raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=datetime.now(timezone.utc) # STATUSNYA SUDAH MATI / REVOKED
    )
    
    # Mocking agar `db.execute(...).scalars().all()` mengembalikan mock_token kita
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_token]
    
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(mock_db_session, raw_refresh_token)
        
    assert exc_info.value.status_code == 401
    assert "mencurigakan" in exc_info.value.detail.lower()
