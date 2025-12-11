"""
Gölge/Aydınlık Yürüyüş Rotası Modeli
"""
from datetime import datetime, time
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, Time
import enum

from app.core.database import Base


class ShadowRoute(Base):
    """Gölgeli/Aydınlık yürüyüş rotaları"""
    __tablename__ = "shadow_routes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rota koordinatları (GeoJSON LineString)
    coordinates = Column(Text, nullable=False)  # JSON array of [lon, lat]
    
    # Başlangıç ve bitiş
    start_name = Column(String(255), nullable=True)
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    
    end_name = Column(String(255), nullable=True)
    end_latitude = Column(Float, nullable=False)
    end_longitude = Column(Float, nullable=False)
    
    # Rota özellikleri
    distance_km = Column(Float, nullable=True)
    estimated_walk_time_min = Column(Float, nullable=True)
    
    # Gölge/Aydınlık bilgisi
    shade_percentage = Column(Float, default=0)  # 0-100 arası gölge yüzdesi
    is_shaded_route = Column(Boolean, default=False)  # Gölgeli rota mı?
    is_lit_route = Column(Boolean, default=False)  # Gece aydınlatmalı mı?
    
    # Zaman bazlı gölge bilgisi
    best_shade_start_time = Column(Time, nullable=True)  # En gölgeli olduğu başlangıç saati
    best_shade_end_time = Column(Time, nullable=True)    # En gölgeli olduğu bitiş saati
    
    # Ağaç/bina gölgesi kaynakları
    shade_sources = Column(Text, nullable=True)  # JSON: ["trees", "buildings", ...]
    
    # Durum
    is_active = Column(Boolean, default=True)
    is_accessible = Column(Boolean, default=True)  # Engelli erişimine uygun mu
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ShadowRoute {self.name}: {self.shade_percentage}% shade>"

