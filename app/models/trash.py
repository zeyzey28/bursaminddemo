"""
Çöp Yönetimi Modelleri
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class TrashBinType(str, enum.Enum):
    """Çöp kutusu tipleri"""
    GENERAL = "general"        # Genel atık
    RECYCLABLE = "recyclable"  # Geri dönüşüm
    ORGANIC = "organic"        # Organik
    GLASS = "glass"            # Cam
    PAPER = "paper"            # Kağıt
    PLASTIC = "plastic"        # Plastik


class TrashBin(Base):
    """Çöp kutuları"""
    __tablename__ = "trash_bins"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    
    # Özellikler
    bin_type = Column(SQLEnum(TrashBinType), default=TrashBinType.GENERAL)
    capacity_liters = Column(Integer, default=240)  # Kapasite (litre)
    
    # Doluluk durumu
    fill_level = Column(Float, default=0)  # 0-100 arası doluluk yüzdesi
    last_fill_update = Column(DateTime, nullable=True)
    
    # Sensör bilgisi (IoT entegrasyonu için)
    sensor_id = Column(String(100), nullable=True, unique=True)
    has_sensor = Column(Boolean, default=False)
    
    # Durum
    is_active = Column(Boolean, default=True)
    needs_maintenance = Column(Boolean, default=False)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    collections = relationship("TrashCollection", back_populates="trash_bin")
    
    def __repr__(self):
        return f"<TrashBin {self.id}: {self.fill_level}%>"


class TrashCollection(Base):
    """Çöp toplama kayıtları"""
    __tablename__ = "trash_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    trash_bin_id = Column(Integer, ForeignKey("trash_bins.id"), nullable=False)
    
    # Toplama bilgileri
    collected_at = Column(DateTime, default=datetime.utcnow)
    fill_level_before = Column(Float, nullable=True)  # Toplama öncesi doluluk
    
    # Araç bilgisi
    vehicle_id = Column(String(50), nullable=True)
    route_id = Column(Integer, ForeignKey("trash_routes.id"), nullable=True)
    
    # İlişkiler
    trash_bin = relationship("TrashBin", back_populates="collections")
    route = relationship("TrashRoute", back_populates="collections")


class TrashRoute(Base):
    """Çöp toplama rotaları"""
    __tablename__ = "trash_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(255), nullable=False)
    
    # Rota detayları (JSON formatında waypoint'ler)
    waypoints = Column(Text, nullable=False)  # JSON array
    
    # Optimizasyon metrikleri
    total_distance_km = Column(Float, nullable=True)
    estimated_duration_min = Column(Float, nullable=True)
    estimated_fuel_liters = Column(Float, nullable=True)
    
    # Araç bilgisi
    vehicle_id = Column(String(50), nullable=True)
    vehicle_capacity_kg = Column(Float, default=5000)  # Araç kapasitesi
    
    # Durum
    is_active = Column(Boolean, default=True)
    is_optimized = Column(Boolean, default=False)
    
    # Zaman
    scheduled_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    collections = relationship("TrashCollection", back_populates="route")
    
    def __repr__(self):
        return f"<TrashRoute {self.name}>"

