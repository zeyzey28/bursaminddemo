"""
Kullanıcı Endpoint'leri
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı profilini getir
    """
    result = await db.execute(
        select(User).where(User.id == int(current_user["user_id"]))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )
    
    return UserResponse.model_validate(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı profilini güncelle
    
    Güncellenebilir alanlar:
    - full_name: Ad Soyad
    - phone: Telefon
    - email: Email (opsiyonel)
    - address: Adres
    - latitude/longitude: Konum
    """
    result = await db.execute(
        select(User).where(User.id == int(current_user["user_id"]))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )
    
    # Güncelle
    if update_data.full_name is not None:
        user.full_name = update_data.full_name
    if update_data.phone is not None:
        user.phone = update_data.phone
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.address is not None:
        user.address = update_data.address
    if update_data.latitude is not None:
        user.latitude = str(update_data.latitude)
    if update_data.longitude is not None:
        user.longitude = str(update_data.longitude)
    
    await db.flush()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)
