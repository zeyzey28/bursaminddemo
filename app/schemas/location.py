"""
Konum Şemaları
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class HospitalResponse(BaseModel):
    """Hastane yanıt şeması"""
    id: int
    osm_id: Optional[str] = None
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    has_emergency: bool
    speciality: Optional[str] = None
    operator: Optional[str] = None
    distance_km: Optional[float] = None  # Kullanıcıya uzaklık
    
    class Config:
        from_attributes = True


class PharmacyResponse(BaseModel):
    """Eczane yanıt şeması"""
    id: int
    osm_id: Optional[str] = None
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    is_on_duty: bool
    duty_date: Optional[datetime] = None
    distance_km: Optional[float] = None
    
    class Config:
        from_attributes = True


class TrafficPointResponse(BaseModel):
    """Trafik noktası yanıtı"""
    id: int
    latitude: float
    longitude: float
    road_name: Optional[str] = None
    traffic_level: str
    speed_kmh: Optional[float] = None
    congestion_percent: float
    emoji: str
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class TrafficPointCreate(BaseModel):
    """Trafik noktası oluşturma"""
    latitude: float
    longitude: float
    road_name: Optional[str] = None
    traffic_level: str
    speed_kmh: Optional[float] = None
    congestion_percent: float = 0


class NearbyLocationResponse(BaseModel):
    """Yakındaki konumlar yanıtı"""
    hospitals: List[HospitalResponse]
    pharmacies: List[PharmacyResponse]
    user_latitude: float
    user_longitude: float
    search_radius_km: float


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature"""
    type: str = "Feature"
    properties: dict
    geometry: dict


class GeoJSONResponse(BaseModel):
    """GeoJSON yanıtı"""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]

