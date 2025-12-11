"""
Afet Yönetimi Şemaları
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DisasterModeCreate(BaseModel):
    """Afet modu oluşturma"""
    disaster_type: str
    severity: str = "medium"
    title: str
    description: Optional[str] = None
    center_latitude: float
    center_longitude: float
    radius_km: float = 5.0


class DisasterModeUpdate(BaseModel):
    """Afet modu güncelleme"""
    severity: Optional[str] = None
    description: Optional[str] = None
    radius_km: Optional[float] = None
    is_active: Optional[bool] = None


class DisasterModeResponse(BaseModel):
    """Afet modu yanıtı"""
    id: int
    disaster_type: str
    severity: str
    title: str
    description: Optional[str] = None
    center_latitude: float
    center_longitude: float
    radius_km: float
    is_active: bool
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SafeRouteCreate(BaseModel):
    """Güvenli rota oluşturma"""
    name: str
    description: Optional[str] = None
    coordinates: str  # JSON string of [[lon, lat], ...]
    start_name: Optional[str] = None
    start_latitude: float
    start_longitude: float
    end_name: Optional[str] = None
    end_latitude: float
    end_longitude: float
    distance_km: Optional[float] = None
    estimated_walk_time_min: Optional[float] = None
    capacity_people: Optional[int] = None
    is_accessible: bool = True


class SafeRouteResponse(BaseModel):
    """Güvenli rota yanıtı"""
    id: int
    name: str
    description: Optional[str] = None
    coordinates: str
    start_name: Optional[str] = None
    start_latitude: float
    start_longitude: float
    end_name: Optional[str] = None
    end_latitude: float
    end_longitude: float
    distance_km: Optional[float] = None
    estimated_walk_time_min: Optional[float] = None
    capacity_people: Optional[int] = None
    is_active: bool
    is_accessible: bool
    
    class Config:
        from_attributes = True


class BlockedRoadCreate(BaseModel):
    """Kapatılan yol oluşturma"""
    road_name: str
    reason: Optional[str] = None
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    alternative_route: Optional[str] = None


class BlockedRoadUpdate(BaseModel):
    """Kapatılan yol güncelleme"""
    is_blocked: Optional[bool] = None
    reason: Optional[str] = None
    alternative_route: Optional[str] = None


class BlockedRoadResponse(BaseModel):
    """Kapatılan yol yanıtı"""
    id: int
    road_name: str
    reason: Optional[str] = None
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    alternative_route: Optional[str] = None
    is_blocked: bool
    blocked_at: datetime
    unblocked_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DisasterDashboard(BaseModel):
    """Afet durumu dashboard"""
    active_disasters: List[DisasterModeResponse]
    blocked_roads_count: int
    safe_routes_count: int
    affected_area_km2: float
    
    # Harita verileri
    blocked_roads: List[BlockedRoadResponse]
    safe_routes: List[SafeRouteResponse]

