import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.modules.auth.models import User, RefreshToken
from app.modules.auth.schemas import UserCreate, LoginRequest
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.core.logging import logger

def _generate_and_add_refresh_token(db: AsyncSession, user_id: str) -> str:
    """ Helper untuk generate token raw, hash, dan add ke session DB. Belum di-commit. """
    hex_str = secrets.token_hex(32)
    raw_token = f"{user_id}:{hex_str}"
    token_hash = get_password_hash(raw_token)
    
    expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.now(timezone.utc) + expires_delta
    
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_token)
    return raw_token

async def register_user(db: AsyncSession, user_in: UserCreate):
    # 1. Cek apakah email sudah dipakai
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar. Silakan gunakan email lain."
        )
    
    # 2. Buat user baru
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name
    )
    db.add(new_user)
    await db.flush() # flush agar kita mendapatkan new_user.id
    
    # 3. Generate token
    access_token = create_access_token(
        subject=new_user.id,
        role=new_user.role,
        has_merchant_profile=new_user.has_merchant_profile
    )
    refresh_token = _generate_and_add_refresh_token(db, new_user.id)
    
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"User baru berhasil mendaftar: {new_user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": new_user
    }

async def authenticate_user(db: AsyncSession, login_req: LoginRequest):
    # 1. Cari user berdasarkan email
    result = await db.execute(select(User).where(User.email == login_req.email))
    user = result.scalars().first()
    
    # 2. Validasi kredensial (pesan error disamakan demi keamanan)
    if not user or not verify_password(login_req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password yang Anda masukkan salah."
        )
        
    # 3. Generate tokens
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        has_merchant_profile=user.has_merchant_profile
    )
    refresh_token = _generate_and_add_refresh_token(db, user.id)
    
    await db.commit()
    logger.info(f"User berhasil login: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

async def refresh_access_token(db: AsyncSession, raw_refresh_token: str):
    # Ekstrak user_id dari format token (user_id:hex_string)
    try:
        user_id_str, _ = raw_refresh_token.split(":", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Format refresh token tidak valid")

    # Ambil semua token milik user tersebut
    result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id_str))
    tokens = result.scalars().all()
    
    valid_token_record = None
    for t in tokens:
        if verify_password(raw_refresh_token, t.token_hash):
            valid_token_record = t
            break
            
    if not valid_token_record:
        raise HTTPException(status_code=401, detail="Refresh token tidak ditemukan atau salah")
        
    # Cek kedaluwarsa (Expired)
    if valid_token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sesi Anda telah berakhir, silakan login kembali")
        
    # Cek pencurian sesi (Token Reuse Detection)
    # Jika token ini sudah pernah di-revoke tapi tetap dipakai lagi, ini tanda bahaya!
    if valid_token_record.revoked_at is not None:
        logger.warning(f"SECURITY ALERT: Token Reuse Terdeteksi untuk user_id {user_id_str}!")
        # Hukum: Revoke (cabut) SEMUA token milik user ini demi keamanan
        for t in tokens:
            t.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(
            status_code=401, 
            detail="Terdeteksi aktivitas mencurigakan pada sesi Anda. Anda telah dikeluarkan dari semua perangkat demi keamanan."
        )
        
    # Jika sah, matikan token lama (agar tidak bisa dipakai lagi)
    valid_token_record.revoked_at = datetime.now(timezone.utc)
    
    # Ambil data user
    result_user = await db.execute(select(User).where(User.id == user_id_str))
    user = result_user.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
        
    # Buat token rotasi yang baru
    new_access_token = create_access_token(
        subject=user.id,
        role=user.role,
        has_merchant_profile=user.has_merchant_profile
    )
    new_refresh_token = _generate_and_add_refresh_token(db, user.id)
    
    await db.commit()
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": user
    }

async def logout_user(db: AsyncSession, raw_refresh_token: str):
    try:
        user_id_str, _ = raw_refresh_token.split(":", 1)
    except ValueError:
        return # Abaikan jika salah format saat logout

    result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id_str))
    tokens = result.scalars().all()
    
    for t in tokens:
        if verify_password(raw_refresh_token, t.token_hash):
            t.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            return
