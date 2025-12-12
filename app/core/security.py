"""
Güvenlik ve Kimlik Doğrulama
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifre doğrulama"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Şifre hashleme"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT token oluşturma"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Token süresi: 15 dakika (güvenlik için kısa tutuldu)
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """JWT token çözme"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Mevcut kullanıcıyı al ve veritabanından doğrula
    
    Her istekte kullanıcının:
    - Hala var olduğunu
    - Aktif olduğunu
    kontrol eder. Böylece silinen/deaktif edilen kullanıcılar
    token geçerli olsa bile erişemez.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Veritabanından kullanıcıyı kontrol et (Double Check)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == int(user_id))
        )
        user = result.scalar_one_or_none()
        
        # Kullanıcı silinmiş mi?
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Kullanıcı bulunamadı. Hesabınız silinmiş olabilir.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Kullanıcı deaktif edilmiş mi?
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hesabınız devre dışı bırakılmış. Yönetici ile iletişime geçin.",
            )
    
    return {"user_id": user_id, "role": payload.get("role", "citizen")}


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Sadece admin kullanıcıları için"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok"
        )
    return current_user


async def get_current_municipality(current_user: dict = Depends(get_current_user)) -> dict:
    """Belediye personeli için"""
    if current_user.get("role") not in ["admin", "municipality"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için belediye yetkisi gerekli"
        )
    return current_user

