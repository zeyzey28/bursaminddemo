"""
Kullanıcı Modeli
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """Kullanıcı rolleri"""
    CITIZEN = "citizen"          # Vatandaş
    MUNICIPALITY = "municipality" # Belediye personeli
    ADMIN = "admin"              # Yönetici


class User(Base):
    """Kullanıcı tablosu"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Kullanıcı adı (giriş için) - ZORUNLU
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profil bilgileri
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)  # Opsiyonel, sonra eklenebilir
    
    # Rol
    role = Column(SQLEnum(UserRole), default=UserRole.CITIZEN, nullable=False)
    
    # Durum
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Konum (opsiyonel - kullanıcının kayıtlı adresi)
    address = Column(String(500), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # İlişkiler
    complaints = relationship("Complaint", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"
