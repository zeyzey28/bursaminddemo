"""
Afet Yönetimi Endpoint'leri
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, get_current_municipality
from app.models.disaster import DisasterMode, SafeRoute, BlockedRoad
from app.schemas.disaster import (
    DisasterModeCreate, DisasterModeUpdate, DisasterModeResponse,
    SafeRouteCreate, SafeRouteResponse,
    BlockedRoadCreate, BlockedRoadUpdate, BlockedRoadResponse,
    DisasterDashboard
)
from app.schemas.location import GeoJSONResponse, GeoJSONFeature

router = APIRouter()


@router.get("/status")
async def get_disaster_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Aktif afet durumunu kontrol et (herkes erişebilir)
    """
    result = await db.execute(
        select(DisasterMode).where(DisasterMode.is_active == True)
    )
    active_disasters = result.scalars().all()
    
    if not active_disasters:
        return {
            "is_disaster_mode": False,
            "message": "Şu anda aktif afet durumu bulunmamaktadır.",
            "disasters": []
        }
    
    return {
        "is_disaster_mode": True,
        "message": "DİKKAT: Aktif afet durumu mevcut!",
        "disasters": [DisasterModeResponse.model_validate(d) for d in active_disasters]
    }


@router.get("/modes", response_model=List[DisasterModeResponse])
async def list_disaster_modes(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Afet modlarını listele
    """
    query = select(DisasterMode)
    
    if active_only:
        query = query.where(DisasterMode.is_active == True)
    
    query = query.order_by(DisasterMode.started_at.desc())
    
    result = await db.execute(query)
    modes = result.scalars().all()
    
    return [DisasterModeResponse.model_validate(m) for m in modes]


@router.post("/modes", response_model=DisasterModeResponse, status_code=status.HTTP_201_CREATED)
async def create_disaster_mode(
    data: DisasterModeCreate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni afet modu oluştur (Belediye yetkisi gerekli)
    """
    disaster = DisasterMode(
        disaster_type=data.disaster_type,
        severity=data.severity,
        title=data.title,
        description=data.description,
        center_latitude=data.center_latitude,
        center_longitude=data.center_longitude,
        radius_km=data.radius_km,
        is_active=True
    )
    
    db.add(disaster)
    await db.flush()
    await db.refresh(disaster)
    
    return DisasterModeResponse.model_validate(disaster)


@router.put("/modes/{mode_id}", response_model=DisasterModeResponse)
async def update_disaster_mode(
    mode_id: int,
    data: DisasterModeUpdate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Afet modunu güncelle
    """
    result = await db.execute(
        select(DisasterMode).where(DisasterMode.id == mode_id)
    )
    disaster = result.scalar_one_or_none()
    
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Afet modu bulunamadı"
        )
    
    if data.severity is not None:
        disaster.severity = data.severity
    if data.description is not None:
        disaster.description = data.description
    if data.radius_km is not None:
        disaster.radius_km = data.radius_km
    if data.is_active is not None:
        disaster.is_active = data.is_active
        if not data.is_active:
            disaster.ended_at = datetime.utcnow()
    
    await db.flush()
    await db.refresh(disaster)
    
    return DisasterModeResponse.model_validate(disaster)


@router.delete("/modes/{mode_id}")
async def end_disaster_mode(
    mode_id: int,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Afet modunu sonlandır
    """
    result = await db.execute(
        select(DisasterMode).where(DisasterMode.id == mode_id)
    )
    disaster = result.scalar_one_or_none()
    
    if not disaster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Afet modu bulunamadı"
        )
    
    disaster.is_active = False
    disaster.ended_at = datetime.utcnow()
    await db.flush()
    
    return {"message": "Afet modu sonlandırıldı"}


# Güvenli Rotalar
@router.get("/safe-routes", response_model=List[SafeRouteResponse])
async def list_safe_routes(
    accessible_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """
    Güvenli tahliye rotalarını listele
    """
    query = select(SafeRoute).where(SafeRoute.is_active == True)
    
    if accessible_only:
        query = query.where(SafeRoute.is_accessible == True)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    return [SafeRouteResponse.model_validate(r) for r in routes]


@router.get("/safe-routes/geojson", response_model=GeoJSONResponse)
async def get_safe_routes_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Güvenli rotaları GeoJSON formatında getir (harita için)
    """
    result = await db.execute(
        select(SafeRoute).where(SafeRoute.is_active == True)
    )
    routes = result.scalars().all()
    
    features = []
    for route in routes:
        # LineString için koordinatlar
        import json
        try:
            coords = json.loads(route.coordinates)
        except:
            coords = []
        
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": route.id,
                "name": route.name,
                "description": route.description,
                "distance_km": route.distance_km,
                "estimated_walk_time_min": route.estimated_walk_time_min,
                "is_accessible": route.is_accessible,
                "end_name": route.end_name,  # Toplanma alanı
                "type": "safe_route",
                "color": "#00FF00"  # Yeşil
            },
            geometry={
                "type": "LineString",
                "coordinates": coords
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.post("/safe-routes", response_model=SafeRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_safe_route(
    data: SafeRouteCreate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Güvenli rota oluştur
    """
    route = SafeRoute(
        name=data.name,
        description=data.description,
        coordinates=data.coordinates,
        start_name=data.start_name,
        start_latitude=data.start_latitude,
        start_longitude=data.start_longitude,
        end_name=data.end_name,
        end_latitude=data.end_latitude,
        end_longitude=data.end_longitude,
        distance_km=data.distance_km,
        estimated_walk_time_min=data.estimated_walk_time_min,
        capacity_people=data.capacity_people,
        is_accessible=data.is_accessible
    )
    
    db.add(route)
    await db.flush()
    await db.refresh(route)
    
    return SafeRouteResponse.model_validate(route)


# Kapatılan Yollar
@router.get("/blocked-roads", response_model=List[BlockedRoadResponse])
async def list_blocked_roads(
    db: AsyncSession = Depends(get_db)
):
    """
    Kapatılan yolları listele
    """
    result = await db.execute(
        select(BlockedRoad).where(BlockedRoad.is_blocked == True)
    )
    roads = result.scalars().all()
    
    return [BlockedRoadResponse.model_validate(r) for r in roads]


@router.get("/blocked-roads/geojson", response_model=GeoJSONResponse)
async def get_blocked_roads_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Kapatılan yolları GeoJSON formatında getir
    """
    result = await db.execute(
        select(BlockedRoad).where(BlockedRoad.is_blocked == True)
    )
    roads = result.scalars().all()
    
    features = []
    for road in roads:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": road.id,
                "road_name": road.road_name,
                "reason": road.reason,
                "alternative_route": road.alternative_route,
                "blocked_at": road.blocked_at.isoformat() if road.blocked_at else None,
                "type": "blocked_road",
                "color": "#FF0000"  # Kırmızı
            },
            geometry={
                "type": "LineString",
                "coordinates": [
                    [road.start_longitude, road.start_latitude],
                    [road.end_longitude, road.end_latitude]
                ]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.post("/blocked-roads", response_model=BlockedRoadResponse, status_code=status.HTTP_201_CREATED)
async def create_blocked_road(
    data: BlockedRoadCreate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Yol kapatma kaydı oluştur
    """
    road = BlockedRoad(
        road_name=data.road_name,
        reason=data.reason,
        start_latitude=data.start_latitude,
        start_longitude=data.start_longitude,
        end_latitude=data.end_latitude,
        end_longitude=data.end_longitude,
        alternative_route=data.alternative_route
    )
    
    db.add(road)
    await db.flush()
    await db.refresh(road)
    
    return BlockedRoadResponse.model_validate(road)


@router.put("/blocked-roads/{road_id}", response_model=BlockedRoadResponse)
async def update_blocked_road(
    road_id: int,
    data: BlockedRoadUpdate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Kapatılan yol bilgisini güncelle
    """
    result = await db.execute(
        select(BlockedRoad).where(BlockedRoad.id == road_id)
    )
    road = result.scalar_one_or_none()
    
    if not road:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yol kaydı bulunamadı"
        )
    
    if data.is_blocked is not None:
        road.is_blocked = data.is_blocked
        if not data.is_blocked:
            road.unblocked_at = datetime.utcnow()
    
    if data.reason is not None:
        road.reason = data.reason
    
    if data.alternative_route is not None:
        road.alternative_route = data.alternative_route
    
    await db.flush()
    await db.refresh(road)
    
    return BlockedRoadResponse.model_validate(road)


@router.get("/dashboard", response_model=DisasterDashboard)
async def get_disaster_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Afet durumu dashboard (herkes erişebilir)
    """
    # Aktif afetler
    disasters_result = await db.execute(
        select(DisasterMode).where(DisasterMode.is_active == True)
    )
    active_disasters = disasters_result.scalars().all()
    
    # Kapatılan yollar
    blocked_result = await db.execute(
        select(BlockedRoad).where(BlockedRoad.is_blocked == True)
    )
    blocked_roads = blocked_result.scalars().all()
    
    # Güvenli rotalar
    safe_result = await db.execute(
        select(SafeRoute).where(SafeRoute.is_active == True)
    )
    safe_routes = safe_result.scalars().all()
    
    # Toplam etkilenen alan (yaklaşık)
    import math
    total_area = sum(math.pi * (d.radius_km ** 2) for d in active_disasters)
    
    return DisasterDashboard(
        active_disasters=[DisasterModeResponse.model_validate(d) for d in active_disasters],
        blocked_roads_count=len(blocked_roads),
        safe_routes_count=len(safe_routes),
        affected_area_km2=round(total_area, 2),
        blocked_roads=[BlockedRoadResponse.model_validate(r) for r in blocked_roads],
        safe_routes=[SafeRouteResponse.model_validate(r) for r in safe_routes]
    )

