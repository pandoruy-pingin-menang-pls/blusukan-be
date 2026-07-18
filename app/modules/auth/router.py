from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth import schemas, service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await service.register_user(db, user_in)

@router.post("/login", response_model=schemas.TokenResponse)
async def login(login_req: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    return await service.authenticate_user(db, login_req)

@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(refresh_req: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await service.refresh_access_token(db, refresh_req.refresh_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(refresh_req: schemas.RefreshRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await service.logout_user(db, refresh_req.refresh_token)
    return None

@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=schemas.UserResponse)
async def update_me(
    user_update: schemas.UserUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
        
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
