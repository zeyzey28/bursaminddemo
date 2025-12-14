"""
Trafik Risk Şemaları
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class RiskInfo(BaseModel):
    """Risk bilgisi"""
    score: float
    level: str
    type: List[str]


class TrafficInfo(BaseModel):
    """Trafik bilgisi"""
    current_density: float
    expected_2h: float


class ComplaintInfo(BaseModel):
    """Şikayet bilgisi"""
    count_24h: int
    avg_urgency_24h: float


class SegmentRiskResponse(BaseModel):
    """Segment risk yanıtı (Belediye paneli)"""
    segment_id: str
    timestamp: datetime
    risk: RiskInfo
    traffic: TrafficInfo
    complaints: ComplaintInfo
    explanation: Optional[str] = None
    
    class Config:
        from_attributes = True


class SegmentSeriesItem(BaseModel):
    """Zaman serisi öğesi"""
    time: datetime
    traffic_density: float
    risk_score: float


class SegmentSeriesResponse(BaseModel):
    """Segment zaman serisi"""
    segment_id: str
    series: List[SegmentSeriesItem]


class TrafficForecastResponse(BaseModel):
    """Trafik tahmin yanıtı (Herkes için)"""
    signal_id: Optional[int] = None
    segment_id: Optional[str] = None
    timestamp: datetime
    vehicle_count: Optional[float] = None
    traffic_density: float
    expected_2h: float
    
    class Config:
        from_attributes = True


class WhatIfRequest(BaseModel):
    """What-if senaryo isteği"""
    segment_id: str
    lane_closed: int = 1
    duration_hours: int = 6
    start_time: Optional[str] = None  # "HH:MM" formatı


class AffectedSegment(BaseModel):
    """Etkilenen segment"""
    segment_id: str
    delay_increase_pct: int


class TimeWindow(BaseModel):
    """Zaman penceresi"""
    start: str  # "HH:MM"
    end: str  # "HH:MM"


class WhatIfResponse(BaseModel):
    """What-if senaryo yanıtı"""
    scenario: str
    segment_id: str
    impact: Dict[str, int]
    start_time: Optional[str] = None
    affected_segments: List[AffectedSegment]
    best_time_window: TimeWindow
    summary: str

