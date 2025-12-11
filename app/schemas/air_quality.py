"""
Hava Kalitesi Şemaları
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AirQualityCreate(BaseModel):
    """Hava kalitesi ölçümü oluşturma"""
    latitude: float
    longitude: float
    station_name: Optional[str] = None
    aqi: int
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    o3: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None


class AirQualityResponse(BaseModel):
    """Hava kalitesi yanıtı"""
    id: int
    latitude: float
    longitude: float
    station_name: Optional[str] = None
    aqi: int
    level: str
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    o3: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    color_code: str
    recorded_at: datetime
    
    # İnsan okunabilir açıklama
    level_description: Optional[str] = None
    health_advice: Optional[str] = None
    
    class Config:
        from_attributes = True


class AirQualityHeatmapPoint(BaseModel):
    """Heatmap için tek nokta"""
    latitude: float
    longitude: float
    aqi: int
    color: str
    intensity: float  # 0-1 arası yoğunluk


class AirQualityHeatmapResponse(BaseModel):
    """Hava kalitesi heatmap yanıtı"""
    points: List[AirQualityHeatmapPoint]
    min_aqi: int
    max_aqi: int
    average_aqi: float
    timestamp: datetime
    
    # Renk skalası
    color_scale: dict = {
        "good": "#00E400",
        "moderate": "#FFFF00",
        "unhealthy_sensitive": "#FF7E00",
        "unhealthy": "#FF0000",
        "very_unhealthy": "#8F3F97",
        "hazardous": "#7E0023"
    }


class AirQualityStats(BaseModel):
    """Hava kalitesi istatistikleri"""
    current_average_aqi: float
    current_level: str
    
    # Son 24 saat
    last_24h_average: float
    last_24h_max: int
    last_24h_min: int
    
    # Trend
    trend: str  # "improving", "stable", "worsening"
    trend_percentage: float
    
    # Kirletici ortalamaları
    avg_pm25: Optional[float] = None
    avg_pm10: Optional[float] = None

