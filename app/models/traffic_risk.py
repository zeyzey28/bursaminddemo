"""
Trafik Risk ve Segment Modelleri
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSON
import enum

from app.core.database import Base


class RiskLevel(str, enum.Enum):
    """Risk seviyeleri"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskType(str, enum.Enum):
    """Risk tipleri"""
    TRAFFIC = "traffic"
    INFRASTRUCTURE_RISK = "infrastructure_risk"
    MANUAL_REVIEW = "manual_review"


class SegmentRisk(Base):
    """Segment risk durumu (Belediye paneli için)"""
    __tablename__ = "segment_risks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Segment bilgisi
    segment_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Risk skorları
    risk_score = Column(Float, nullable=False)  # 0-1 arası
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    risk_types = Column(ARRAY(String), nullable=True)  # ["traffic", "infrastructure_risk"]
    
    # Trafik durumu
    current_density = Column(Float, nullable=False)  # 0-1 arası
    expected_2h = Column(Float, nullable=False)  # 2 saat sonrası tahmin
    current_vehicle = Column(Float, nullable=True)  # Araç sayısı
    
    # Şikayet durumu
    complaint_count_24h = Column(Integer, default=0)
    avg_urgency_24h = Column(Float, default=0.0)
    max_urgency_24h = Column(Float, default=0.0)
    noise_ratio_24h = Column(Float, default=0.0)
    
    # Açıklama
    explanation = Column(Text, nullable=True)
    
    # Zaman
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<SegmentRisk {self.segment_id}: {self.risk_level.value}>"


class TrafficForecast(Base):
    """Trafik tahmin verileri (Herkes için)"""
    __tablename__ = "traffic_forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Sinyal/segment bilgisi
    signal_id = Column(Integer, nullable=True, index=True)
    segment_id = Column(String(50), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Trafik verileri
    vehicle_count = Column(Float, nullable=True)
    traffic_density = Column(Float, nullable=False)  # 0-1 arası
    expected_2h = Column(Float, nullable=False)  # 2 saat sonrası tahmin
    
    # Zaman
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<TrafficForecast {self.segment_id or self.signal_id}: {self.traffic_density:.2f}>"


class WhatIfScenario(Base):
    """What-if senaryoları (Belediye paneli için)"""
    __tablename__ = "whatif_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Senaryo bilgisi
    scenario_type = Column(String(50), default="road_work")
    segment_id = Column(String(50), nullable=False, index=True)
    
    # Etki parametreleri
    lane_closed = Column(Integer, default=1)
    duration_hours = Column(Integer, default=6)
    start_time = Column(String(10), nullable=True)  # "HH:MM" formatı
    
    # Sonuçlar
    affected_segments = Column(JSON, nullable=True)  # [{"segment_id": "...", "delay_increase_pct": 26}]
    best_time_window = Column(JSON, nullable=True)  # {"start": "01:00", "end": "07:00"}
    summary = Column(Text, nullable=True)
    
    # Zaman
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_by = Column(Integer, nullable=True)  # Belediye kullanıcı ID
    
    def __repr__(self):
        return f"<WhatIfScenario {self.segment_id}: {self.scenario_type}>"

