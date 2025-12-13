"""
Şikayet Modeli
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ComplaintCategory(str, enum.Enum):
    """Şikayet kategorileri"""
    ROAD_DAMAGE = "road_damage"           # Yol hasarı
    LIGHTING = "lighting"                  # Aydınlatma sorunu
    TRASH = "trash"                        # Çöp/temizlik
    TRAFFIC = "traffic"                    # Trafik sorunu
    PARKING = "parking"                    # Park sorunu
    NOISE = "noise"                        # Gürültü
    GREEN_AREA = "green_area"              # Yeşil alan
    WATER = "water"                        # Su/kanalizasyon
    AIR_QUALITY = "air_quality"            # Hava kalitesi
    SAFETY = "safety"                      # Güvenlik
    OTHER = "other"                        # Diğer


class ComplaintStatus(str, enum.Enum):
    """Şikayet durumları"""
    PENDING = "pending"                    # Beklemede
    RECEIVED = "received"                  # Alındı
    IN_PROGRESS = "in_progress"            # İşlemde
    RESOLVED = "resolved"                  # Çözüldü
    REJECTED = "rejected"                  # Reddedildi


class ComplaintPriority(str, enum.Enum):
    """Aciliyet seviyeleri"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Complaint(Base):
    """Şikayet tablosu"""
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Kullanıcı ilişkisi
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="complaints")
    
    # Şikayet detayları
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(ComplaintCategory), nullable=False)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    
    # Durum ve öncelik
    status = Column(SQLEnum(ComplaintStatus), default=ComplaintStatus.PENDING)
    priority = Column(SQLEnum(ComplaintPriority), default=ComplaintPriority.MEDIUM)
    urgency_score = Column(Float, default=0.5)  # 0-1 arası AI hesaplı skor
    
    # AI doğrulama
    ai_verified = Column(Boolean, default=False)
    ai_verification_score = Column(Float, nullable=True)  # AI'ın doğrulama güven skoru
    ai_category_suggestion = Column(String(50), nullable=True)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # İlişkiler
    images = relationship("ComplaintImage", back_populates="complaint", cascade="all, delete-orphan")
    feedbacks = relationship("ComplaintFeedback", back_populates="complaint", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Complaint {self.id}: {self.title}>"


class ComplaintImage(Base):
    """Şikayet görselleri"""
    __tablename__ = "complaint_images"
    
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    
    # Dosya bilgileri
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    
    # AI analiz sonuçları
    ai_analysis = Column(Text, nullable=True)  # JSON formatında AI analizi
    ai_tags = Column(String(500), nullable=True)  # Virgülle ayrılmış etiketler
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)  # Kayıt oluşturma zamanı
    uploaded_at = Column(DateTime, default=datetime.utcnow)  # Sisteme yüklenme zamanı
    
    # İlişki
    complaint = relationship("Complaint", back_populates="images")


class ComplaintFeedback(Base):
    """Belediye geri bildirimleri"""
    __tablename__ = "complaint_feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    
    # Geri bildirim veren
    municipality_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Mesaj
    message = Column(Text, nullable=False)
    new_status = Column(SQLEnum(ComplaintStatus), nullable=True)
    
    # Zaman
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    complaint = relationship("Complaint", back_populates="feedbacks")
    municipality_user = relationship("User", foreign_keys=[municipality_user_id])

