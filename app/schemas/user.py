"""
Kullanıcı Şemaları
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Temel kullanıcı şeması"""
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None  # Opsiyonel


class UserCreate(UserBase):
    """Kullanıcı oluşturma (Vatandaş kaydı)"""
    password: str = Field(..., min_length=6)
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class UserLogin(BaseModel):
    """Giriş şeması"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Kullanıcı yanıt şeması"""
    id: int
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Kullanıcı güncelleme"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Token(BaseModel):
    """JWT Token yanıtı"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
