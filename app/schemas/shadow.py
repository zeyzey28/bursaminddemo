"""
Gölge/Aydınlık Rota Şemaları
"""
from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel


class ShadowRouteCreate(BaseModel):
    """Gölgeli rota oluşturma"""
    name: str
    description: Optional[str] = None
    coordinates: str  # JSON string
    start_name: Optional[str] = None
    start_latitude: float
    start_longitude: float
    end_name: Optional[str] = None
    end_latitude: float
    end_longitude: float
    distance_km: Optional[float] = None
    estimated_walk_time_min: Optional[float] = None
    shade_percentage: float = 0
    is_shaded_route: bool = False
    is_lit_route: bool = False
    is_accessible: bool = True


class ShadowRouteResponse(BaseModel):
    """Gölgeli rota yanıtı"""
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
    shade_percentage: float
    is_shaded_route: bool
    is_lit_route: bool
    best_shade_start_time: Optional[time] = None
    best_shade_end_time: Optional[time] = None
    shade_sources: Optional[str] = None
    is_active: bool
    is_accessible: bool
    
    class Config:
        from_attributes = True


class RoutePreference(BaseModel):
    """Rota tercihi"""
    prefer_shade: bool = True
    prefer_lit: bool = False  # Gece için
    accessible_only: bool = False
    max_distance_km: Optional[float] = None


class ShadowRouteRequest(BaseModel):
    """Gölgeli rota isteği"""
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    preferences: RoutePreference = RoutePreference()
    current_time: Optional[datetime] = None  # Gölge hesaplaması için

