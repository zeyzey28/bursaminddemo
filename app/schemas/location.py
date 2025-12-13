"""
Konum Şemaları
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class LibraryResponse(BaseModel):
    """Kütüphane yanıt şeması"""
    id: int
    osm_id: Optional[str] = None
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    library_type: Optional[str] = None
    opening_hours: Optional[str] = None
    has_wifi: bool = False
    has_study_room: bool = False
    has_children_section: bool = False
    distance_km: Optional[float] = None
    
    class Config:
        from_attributes = True


class LibraryCreate(BaseModel):
    """Kütüphane oluşturma"""
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    library_type: Optional[str] = None
    opening_hours: Optional[str] = None
    has_wifi: bool = False
    has_study_room: bool = False
    has_children_section: bool = False


class ParkResponse(BaseModel):
    """Park yanıt şeması"""
    id: int
    osm_id: Optional[str] = None
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    area_sqm: Optional[float] = None
    park_type: Optional[str] = None
    has_playground: bool = False
    has_sports_area: bool = False
    has_walking_path: bool = False
    has_parking: bool = False
    has_cafe: bool = False
    distance_km: Optional[float] = None
    
    class Config:
        from_attributes = True


class ParkCreate(BaseModel):
    """Park oluşturma"""
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    area_sqm: Optional[float] = None
    park_type: Optional[str] = None
    has_playground: bool = False
    has_sports_area: bool = False
    has_walking_path: bool = False
    has_parking: bool = False
    has_cafe: bool = False


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
    libraries: List[LibraryResponse]
    parks: List[ParkResponse]
    user_latitude: float
    user_longitude: float
    search_radius_km: float


# ============================================
# ROTA HESAPLAMA ŞEMALARI
# ============================================

class RouteRequest(BaseModel):
    """Rota hesaplama isteği"""
    start_latitude: float = Field(..., description="Başlangıç enlemi")
    start_longitude: float = Field(..., description="Başlangıç boylamı")
    end_latitude: float = Field(..., description="Bitiş enlemi")
    end_longitude: float = Field(..., description="Bitiş boylamı")
    profile: str = Field("driving", description="Ulaşım türü: driving, walking, cycling")


class NearestLocationRequest(BaseModel):
    """En yakın lokasyon isteği"""
    latitude: float = Field(..., description="Kullanıcı enlemi")
    longitude: float = Field(..., description="Kullanıcı boylamı")
    location_type: str = Field(..., description="Lokasyon türü: hospital, pharmacy, library, park")
    profile: str = Field("driving", description="Ulaşım türü: driving, walking, cycling")
    limit: int = Field(3, ge=1, le=10, description="Kaç sonuç döndürülsün")


class LocationSearchRequest(BaseModel):
    """Lokasyon arama isteği"""
    query: str = Field(..., min_length=2, description="Arama sorgusu")
    latitude: float = Field(..., description="Kullanıcı enlemi")
    longitude: float = Field(..., description="Kullanıcı boylamı")
    location_type: Optional[str] = Field(None, description="Lokasyon türü filtresi")
    limit: int = Field(10, ge=1, le=50)


class RouteStep(BaseModel):
    """Rota adımı"""
    instruction: str
    distance_m: float
    duration_s: float
    name: str
    mode: str


class RouteResponse(BaseModel):
    """Rota yanıtı"""
    found: bool
    distance_km: float
    duration_min: float
    geometry: dict  # GeoJSON LineString
    steps: List[RouteStep]
    destination: dict


class NearestWithRouteResponse(BaseModel):
    """En yakın lokasyon + rota yanıtı"""
    location_type: str
    results: List[dict]
    user_location: dict
    profile: str


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature"""
    type: str = "Feature"
    properties: dict
    geometry: dict


class GeoJSONResponse(BaseModel):
    """GeoJSON yanıtı"""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]

