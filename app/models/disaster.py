"""
Afet Yönetimi Modelleri
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, Enum as SQLEnum
import enum

from app.core.database import Base


class DisasterType(str, enum.Enum):
    """Afet tipleri"""
    EARTHQUAKE = "earthquake"    # Deprem
    FLOOD = "flood"              # Sel
    FIRE = "fire"                # Yangın
    STORM = "storm"              # Fırtına
    LANDSLIDE = "landslide"      # Heyelan
    OTHER = "other"              # Diğer


class DisasterSeverity(str, enum.Enum):
    """Afet şiddeti"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DisasterMode(Base):
    """Afet modu durumu"""
    __tablename__ = "disaster_modes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Afet bilgileri
    disaster_type = Column(SQLEnum(DisasterType), nullable=False)
    severity = Column(SQLEnum(DisasterSeverity), default=DisasterSeverity.MEDIUM)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Etkilenen bölge (merkez ve yarıçap)
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    radius_km = Column(Float, default=5.0)
    
    # Durum
    is_active = Column(Boolean, default=True)
    
    # Zaman
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DisasterMode {self.disaster_type}: {self.title}>"


class SafeRoute(Base):
    """Güvenli tahliye rotaları"""
    __tablename__ = "safe_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rota koordinatları (GeoJSON LineString)
    coordinates = Column(Text, nullable=False)  # JSON array of [lon, lat]
    
    # Başlangıç ve bitiş noktaları
    start_name = Column(String(255), nullable=True)
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    
    end_name = Column(String(255), nullable=True)  # Toplanma alanı adı
    end_latitude = Column(Float, nullable=False)
    end_longitude = Column(Float, nullable=False)
    
    # Rota özellikleri
    distance_km = Column(Float, nullable=True)
    estimated_walk_time_min = Column(Float, nullable=True)
    capacity_people = Column(Integer, nullable=True)  # Kaç kişi geçebilir
    
    # Durum
    is_active = Column(Boolean, default=True)
    is_accessible = Column(Boolean, default=True)  # Engelli erişimine uygun mu
    
    # Afet modu ilişkisi
    disaster_mode_id = Column(Integer, nullable=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SafeRoute {self.name}>"


class BlockedRoad(Base):
    """Kapatılan yollar"""
    __tablename__ = "blocked_roads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    road_name = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    
    # Kapatılan segment koordinatları
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    end_latitude = Column(Float, nullable=False)
    end_longitude = Column(Float, nullable=False)
    
    # Alternatif rota önerisi
    alternative_route = Column(Text, nullable=True)  # JSON
    
    # Durum
    is_blocked = Column(Boolean, default=True)
    blocked_at = Column(DateTime, default=datetime.utcnow)
    unblocked_at = Column(DateTime, nullable=True)
    
    # Afet modu ilişkisi (opsiyonel)
    disaster_mode_id = Column(Integer, nullable=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BlockedRoad {self.road_name}>"


class AssemblyPoint(Base):
    """Afet Toplanma Alanları"""
    __tablename__ = "assembly_points"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Temel bilgiler
    name = Column(String(255), nullable=False)
    osm_id = Column(String(50), nullable=True, unique=True)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Adres bilgileri
    address = Column(String(500), nullable=True)
    district = Column(String(100), nullable=True)  # İlçe
    neighborhood = Column(String(100), nullable=True)  # Mahalle
    
    # Kapasite ve özellikler
    capacity = Column(Integer, nullable=True)  # Kaç kişi alabilir
    area_sqm = Column(Float, nullable=True)  # Alan (m²)
    
    # Erişilebilirlik
    is_accessible = Column(Boolean, default=True)  # Engelli erişimi
    has_lighting = Column(Boolean, default=True)  # Aydınlatma
    has_water = Column(Boolean, default=False)  # Su kaynağı
    has_toilet = Column(Boolean, default=False)  # Tuvalet
    
    # Durum
    is_active = Column(Boolean, default=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AssemblyPoint {self.name}>"

