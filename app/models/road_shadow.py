"""
Yol Gölge Modeli
Yaz modu routing için yol segmentlerinin gölge bilgileri
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base


class RoadShadow(Base):
    """Yol segmentlerinin gölge verileri"""
    __tablename__ = "road_shadows"

    id = Column(Integer, primary_key=True, index=True)
    
    # Segment bilgisi
    segment_id = Column(String(50), nullable=True, index=True)
    road_id = Column(Integer, nullable=True, index=True)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Gölge bilgisi
    shade_score = Column(Float, nullable=False)  # 0-1 arası gölge skoru (yüksek = daha gölgeli)
    shade_percentage = Column(Float, nullable=True)  # Gölge yüzdesi (0-100)
    
    # İstatistikler (statistics.geojson'dan)
    shade_mean = Column(Float, nullable=True)
    shade_max = Column(Float, nullable=True)
    shade_min = Column(Float, nullable=True)
    
    # GeoJSON geometry (LineString veya Point)
    geometry = Column(JSON, nullable=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index'ler
    __table_args__ = (
        Index('idx_road_shadow_location', 'latitude', 'longitude'),
    )
    
    def __repr__(self):
        return f"<RoadShadow {self.segment_id or self.road_id}: shade={self.shade_score:.2f}>"

