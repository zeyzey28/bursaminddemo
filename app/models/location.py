"""
Konum Modelleri - Hastane, Eczane, Yol, Trafik
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, Enum as SQLEnum
import enum

from app.core.database import Base


class Hospital(Base):
    """Hastane tablosu"""
    __tablename__ = "hospitals"
    
    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String(50), unique=True, index=True)  # OpenStreetMap ID
    
    name = Column(String(255), nullable=False)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Detaylar
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Özellikler
    has_emergency = Column(Boolean, default=False)  # Acil servis var mı
    speciality = Column(String(255), nullable=True)  # Uzmanlık alanı
    operator = Column(String(255), nullable=True)  # İşletmeci
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Hospital {self.name}>"


class Pharmacy(Base):
    """Eczane tablosu"""
    __tablename__ = "pharmacies"
    
    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String(50), unique=True, index=True)
    
    name = Column(String(255), nullable=False)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Detaylar
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Nöbetçi durumu
    is_on_duty = Column(Boolean, default=False)
    duty_date = Column(DateTime, nullable=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Pharmacy {self.name}>"


class TrafficLevel(str, enum.Enum):
    """Trafik yoğunluk seviyeleri"""
    VERY_LOW = "very_low"      # Çok az - 😊
    LOW = "low"                # Az - 🙂
    MODERATE = "moderate"      # Orta - 😐
    HIGH = "high"              # Yoğun - 😟
    VERY_HIGH = "very_high"    # Çok yoğun - 😫


class TrafficPoint(Base):
    """Trafik yoğunluk noktaları"""
    __tablename__ = "traffic_points"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    road_name = Column(String(255), nullable=True)
    
    # Trafik durumu
    traffic_level = Column(SQLEnum(TrafficLevel), default=TrafficLevel.MODERATE)
    speed_kmh = Column(Float, nullable=True)  # Ortalama hız
    congestion_percent = Column(Float, default=0)  # 0-100 arası tıkanıklık
    
    # Duygu ikonu için
    emoji = Column(String(10), default="😐")
    
    # Zaman
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<TrafficPoint {self.road_name}: {self.traffic_level}>"


class Road(Base):
    """Yol segmentleri"""
    __tablename__ = "roads"
    
    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String(50), index=True)
    
    name = Column(String(255), nullable=True)
    road_type = Column(String(50), nullable=True)  # primary, secondary, etc.
    
    # Koordinatlar (GeoJSON LineString formatında)
    coordinates = Column(Text, nullable=False)  # JSON array of [lon, lat] pairs
    
    # Özellikler
    length_meters = Column(Float, nullable=True)
    lanes = Column(Integer, nullable=True)
    max_speed = Column(Integer, nullable=True)
    
    # Durum
    is_blocked = Column(Boolean, default=False)
    blocked_reason = Column(String(255), nullable=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Road {self.name}>"

