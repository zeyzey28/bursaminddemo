"""
Çöp Yönetimi Şemaları
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TrashBinBase(BaseModel):
    """Temel çöp kutusu şeması"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    bin_type: str = "general"
    capacity_liters: int = 240


class TrashBinCreate(TrashBinBase):
    """Çöp kutusu oluşturma"""
    sensor_id: Optional[str] = None
    has_sensor: bool = False


class TrashBinUpdate(BaseModel):
    """Çöp kutusu güncelleme"""
    fill_level: Optional[float] = Field(None, ge=0, le=100)
    needs_maintenance: Optional[bool] = None
    is_active: Optional[bool] = None


class TrashBinResponse(TrashBinBase):
    """Çöp kutusu yanıtı"""
    id: int
    fill_level: float
    last_fill_update: Optional[datetime] = None
    sensor_id: Optional[str] = None
    has_sensor: bool
    is_active: bool
    needs_maintenance: bool
    created_at: datetime
    
    # Renk kodu (doluluk seviyesine göre)
    fill_color: Optional[str] = None
    
    class Config:
        from_attributes = True


class TrashCollectionResponse(BaseModel):
    """Çöp toplama kaydı yanıtı"""
    id: int
    trash_bin_id: int
    collected_at: datetime
    fill_level_before: Optional[float] = None
    vehicle_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class TrashRouteCreate(BaseModel):
    """Çöp toplama rotası oluşturma"""
    name: str
    vehicle_id: Optional[str] = None
    vehicle_capacity_kg: float = 5000
    scheduled_date: Optional[datetime] = None
    bin_ids: List[int]  # Rota üzerindeki çöp kutuları


class TrashRouteResponse(BaseModel):
    """Çöp toplama rotası yanıtı"""
    id: int
    name: str
    waypoints: str  # JSON string
    total_distance_km: Optional[float] = None
    estimated_duration_min: Optional[float] = None
    estimated_fuel_liters: Optional[float] = None
    vehicle_id: Optional[str] = None
    vehicle_capacity_kg: float
    is_active: bool
    is_optimized: bool
    scheduled_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TrashRouteOptimizeRequest(BaseModel):
    """Rota optimizasyon isteği"""
    bin_ids: List[int]
    start_latitude: float
    start_longitude: float
    vehicle_capacity_kg: float = 5000
    fuel_consumption_per_km: float = 0.15  # Litre/km


class TrashRouteOptimizeResponse(BaseModel):
    """Rota optimizasyon yanıtı"""
    optimized_order: List[int]  # Optimize edilmiş çöp kutusu sırası
    waypoints: List[dict]  # [{lat, lon, bin_id}, ...]
    total_distance_km: float
    estimated_duration_min: float
    estimated_fuel_liters: float
    total_waste_kg: float


class TrashDashboardStats(BaseModel):
    """Çöp yönetimi dashboard istatistikleri"""
    total_bins: int
    active_bins: int
    bins_needing_collection: int  # %80+ dolu
    bins_needing_maintenance: int
    
    # Doluluk dağılımı
    fill_distribution: dict  # {"0-25": 10, "25-50": 20, ...}
    
    # Bugünkü toplama
    collections_today: int
    
    # Ortalama doluluk
    average_fill_level: float

