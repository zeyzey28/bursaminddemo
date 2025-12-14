"""
Segment Aydınlatma Modeli
Yol segmentlerinin aydınlatma bilgilerini saklar
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Enum as SQLEnum
import enum

from app.core.database import Base


class LightingLevel(str, enum.Enum):
    """Aydınlatma seviyeleri"""
    DARK = "dark"        # Karanlık (< 0.4)
    MEDIUM = "medium"    # Orta (0.4 - 0.7)
    BRIGHT = "bright"    # Aydınlık (> 0.7)


class SegmentLighting(Base):
    """Yol segmenti aydınlatma bilgileri"""
    __tablename__ = "segment_lighting"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Segment bilgisi
    segment_id = Column(String(50), nullable=False, index=True)
    
    # Konum (Point geometry)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Aydınlatma skorları
    lighting_score = Column(Float, nullable=False)  # 0-1 arası
    lighting_level = Column(SQLEnum(LightingLevel), nullable=False)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SegmentLighting {self.segment_id}: {self.lighting_level.value}>"

