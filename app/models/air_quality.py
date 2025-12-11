"""
Hava Kalitesi Modeli
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Enum as SQLEnum
import enum

from app.core.database import Base


class AirQualityLevel(str, enum.Enum):
    """Hava kalitesi seviyeleri"""
    GOOD = "good"                    # İyi (0-50)
    MODERATE = "moderate"            # Orta (51-100)
    UNHEALTHY_SENSITIVE = "unhealthy_sensitive"  # Hassas gruplar için sağlıksız (101-150)
    UNHEALTHY = "unhealthy"          # Sağlıksız (151-200)
    VERY_UNHEALTHY = "very_unhealthy"  # Çok sağlıksız (201-300)
    HAZARDOUS = "hazardous"          # Tehlikeli (301+)


class AirQualityReading(Base):
    """Hava kalitesi ölçümleri"""
    __tablename__ = "air_quality_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Konum
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    station_name = Column(String(255), nullable=True)
    
    # AQI (Air Quality Index)
    aqi = Column(Integer, nullable=False)  # 0-500 arası
    level = Column(SQLEnum(AirQualityLevel), nullable=False)
    
    # Kirletici değerleri (µg/m³)
    pm25 = Column(Float, nullable=True)   # PM2.5
    pm10 = Column(Float, nullable=True)   # PM10
    o3 = Column(Float, nullable=True)     # Ozon
    no2 = Column(Float, nullable=True)    # Azot dioksit
    so2 = Column(Float, nullable=True)    # Kükürt dioksit
    co = Column(Float, nullable=True)     # Karbon monoksit
    
    # Heatmap için renk kodu
    color_code = Column(String(7), default="#00E400")  # Hex renk
    
    # Zaman
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AirQuality {self.station_name}: AQI {self.aqi}>"
    
    @staticmethod
    def get_color_for_aqi(aqi: int) -> str:
        """AQI değerine göre renk döndür"""
        if aqi <= 50:
            return "#00E400"  # Yeşil - İyi
        elif aqi <= 100:
            return "#FFFF00"  # Sarı - Orta
        elif aqi <= 150:
            return "#FF7E00"  # Turuncu - Hassas gruplar için sağlıksız
        elif aqi <= 200:
            return "#FF0000"  # Kırmızı - Sağlıksız
        elif aqi <= 300:
            return "#8F3F97"  # Mor - Çok sağlıksız
        else:
            return "#7E0023"  # Bordo - Tehlikeli
    
    @staticmethod
    def get_level_for_aqi(aqi: int) -> AirQualityLevel:
        """AQI değerine göre seviye döndür"""
        if aqi <= 50:
            return AirQualityLevel.GOOD
        elif aqi <= 100:
            return AirQualityLevel.MODERATE
        elif aqi <= 150:
            return AirQualityLevel.UNHEALTHY_SENSITIVE
        elif aqi <= 200:
            return AirQualityLevel.UNHEALTHY
        elif aqi <= 300:
            return AirQualityLevel.VERY_UNHEALTHY
        else:
            return AirQualityLevel.HAZARDOUS

