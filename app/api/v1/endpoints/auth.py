"""
Kimlik Doğrulama Endpoint'leri

Kullanıcı Adı + Şifre ile giriş sistemi

Akış:
1. Vatandaş: Kayıt olabilir + Giriş yapabilir
2. Belediye Personeli: Sadece giriş (Admin tarafından oluşturulur)
3. Admin: Personel oluşturabilir + Tüm yetkiler
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    get_current_user,
    get_current_admin
)
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()


# ============================================
# VATANDAŞ (Citizen) Endpoint'leri
# ============================================

@router.post("/citizen/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def citizen_register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Vatandaş kaydı - Herkes kayıt olabilir
    
    - username: Kullanıcı adı (benzersiz, min 3 karakter)
    - password: Şifre (min 6 karakter)
    - full_name: Ad Soyad (opsiyonel)
    - phone: Telefon (opsiyonel)
    """
    # Kullanıcı adı kontrolü
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten kullanılıyor"
        )
    
    # Yeni vatandaş oluştur
    new_user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        email=user_data.email,
        address=user_data.address,
        latitude=str(user_data.latitude) if user_data.latitude else None,
        longitude=str(user_data.longitude) if user_data.longitude else None,
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True
    )
    
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    # Token oluştur
    access_token = create_access_token(
        data={"sub": str(new_user.id), "role": new_user.role.value}
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/citizen/login", response_model=Token)
async def citizen_login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Vatandaş girişi
    
    - username: Kullanıcı adı
    - password: Şifre
    """
    # Kullanıcıyı bul
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    
    # Kullanıcı yok veya şifre yanlış
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre"
        )
    
    # Vatandaş mı kontrol et
    if user.role != UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu giriş sadece vatandaşlar içindir. Personel girişini kullanın."
        )
    
    # Hesap aktif mi
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )
    
    # Son giriş zamanını güncelle
    user.last_login = datetime.utcnow()
    await db.flush()
    
    # Token oluştur
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


# ============================================
# PERSONEL (Municipality Staff) Endpoint'leri
# ============================================

@router.post("/staff/login", response_model=Token)
async def staff_login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Belediye personeli girişi
    
    - username: Kullanıcı adı (admin tarafından verilir)
    - password: Şifre (admin tarafından verilir)
    
    Not: Personel kaydı admin tarafından yapılır.
    """
    # Kullanıcıyı bul
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    
    # Kullanıcı yok veya şifre yanlış
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre"
        )
    
    # Personel veya admin mi kontrol et
    if user.role not in [UserRole.MUNICIPALITY, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu giriş sadece belediye personeli içindir."
        )
    
    # Hesap aktif mi
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış. Yöneticinizle iletişime geçin."
        )
    
    # Son giriş zamanını güncelle
    user.last_login = datetime.utcnow()
    await db.flush()
    
    # Token oluştur
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


# ============================================
# ADMIN Endpoint'leri - Personel Yönetimi
# ============================================

class StaffCreate(BaseModel):
    """Personel oluşturma şeması"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class StaffResponse(BaseModel):
    """Personel yanıt şeması"""
    id: int
    username: str
    full_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


@router.post("/admin/create-staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    staff_data: StaffCreate,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Belediye personeli oluştur (Sadece Admin)
    
    Admin, yeni belediye personeli ekler.
    Personel bu kullanıcı adı ve şifre ile giriş yapabilir.
    """
    # Kullanıcı adı kontrolü
    result = await db.execute(
        select(User).where(User.username == staff_data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten kullanılıyor"
        )
    
    # Yeni personel oluştur
    new_staff = User(
        username=staff_data.username,
        hashed_password=get_password_hash(staff_data.password),
        full_name=staff_data.full_name,
        phone=staff_data.phone,
        email=staff_data.email,
        role=UserRole.MUNICIPALITY,
        is_active=True,
        is_verified=True
    )
    
    db.add(new_staff)
    await db.flush()
    await db.refresh(new_staff)
    
    return StaffResponse.model_validate(new_staff)


@router.get("/admin/staff-list", response_model=list[StaffResponse])
async def list_staff(
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Tüm belediye personelini listele (Sadece Admin)
    """
    result = await db.execute(
        select(User).where(User.role == UserRole.MUNICIPALITY)
    )
    staff_list = result.scalars().all()
    
    return [StaffResponse.model_validate(s) for s in staff_list]


@router.put("/admin/staff/{staff_id}/deactivate")
async def deactivate_staff(
    staff_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Personel hesabını devre dışı bırak (Sadece Admin)
    """
    result = await db.execute(
        select(User).where(User.id == staff_id, User.role == UserRole.MUNICIPALITY)
    )
    staff = result.scalar_one_or_none()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personel bulunamadı"
        )
    
    staff.is_active = False
    await db.flush()
    
    return {"message": f"{staff.full_name} hesabı devre dışı bırakıldı"}


@router.put("/admin/staff/{staff_id}/activate")
async def activate_staff(
    staff_id: int,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Personel hesabını aktifleştir (Sadece Admin)
    """
    result = await db.execute(
        select(User).where(User.id == staff_id, User.role == UserRole.MUNICIPALITY)
    )
    staff = result.scalar_one_or_none()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personel bulunamadı"
        )
    
    staff.is_active = True
    await db.flush()
    
    return {"message": f"{staff.full_name} hesabı aktifleştirildi"}


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6)


@router.put("/admin/staff/{staff_id}/reset-password")
async def reset_staff_password(
    staff_id: int,
    data: PasswordReset,
    current_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Personel şifresini sıfırla (Sadece Admin)
    """
    result = await db.execute(
        select(User).where(User.id == staff_id, User.role == UserRole.MUNICIPALITY)
    )
    staff = result.scalar_one_or_none()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personel bulunamadı"
        )
    
    staff.hashed_password = get_password_hash(data.new_password)
    await db.flush()
    
    return {"message": f"{staff.full_name} şifresi sıfırlandı"}


# ============================================
# ORTAK Endpoint'ler
# ============================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mevcut kullanıcı bilgilerini getir
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


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Token yenileme
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
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout():
    """
    Çıkış yap
    
    Not: JWT stateless olduğu için sunucu tarafında bir işlem yapılmaz.
    Frontend token'ı silmelidir.
    """
    return {
        "message": "Başarıyla çıkış yapıldı",
        "note": "Lütfen token'ı client tarafında silin"
    }


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


@router.put("/change-password")
async def change_password(
    data: ChangePassword,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kendi şifresini değiştir (Tüm kullanıcılar)
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
    
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre yanlış"
        )
    
    user.hashed_password = get_password_hash(data.new_password)
    await db.flush()
    
    return {"message": "Şifreniz başarıyla değiştirildi"}
