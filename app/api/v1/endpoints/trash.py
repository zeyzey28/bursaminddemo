"""
Çöp Yönetimi Endpoint'leri
"""
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_municipality
from app.models.trash import TrashBin, TrashRoute, TrashCollection
from app.schemas.trash import (
    TrashBinResponse, TrashBinCreate, TrashBinUpdate,
    TrashRouteResponse, TrashRouteCreate,
    TrashRouteOptimizeRequest, TrashRouteOptimizeResponse,
    TrashDashboardStats
)
from app.schemas.location import GeoJSONResponse, GeoJSONFeature

router = APIRouter()


def get_fill_color(fill_level: float) -> str:
    """Doluluk seviyesine göre renk"""
    if fill_level < 25:
        return "#00FF00"  # Yeşil
    elif fill_level < 50:
        return "#90EE90"  # Açık yeşil
    elif fill_level < 75:
        return "#FFFF00"  # Sarı
    elif fill_level < 90:
        return "#FFA500"  # Turuncu
    else:
        return "#FF0000"  # Kırmızı


@router.get("/bins", response_model=List[TrashBinResponse])
async def list_trash_bins(
    min_fill_level: float = Query(None, ge=0, le=100),
    needs_collection: bool = Query(False, description="Sadece toplanması gerekenler (%80+)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Çöp kutularını listele
    """
    query = select(TrashBin).where(TrashBin.is_active == True)
    
    if min_fill_level is not None:
        query = query.where(TrashBin.fill_level >= min_fill_level)
    
    if needs_collection:
        query = query.where(TrashBin.fill_level >= 80)
    
    result = await db.execute(query)
    bins = result.scalars().all()
    
    response_list = []
    for bin in bins:
        bin_dict = TrashBinResponse.model_validate(bin).model_dump()
        bin_dict["fill_color"] = get_fill_color(bin.fill_level)
        response_list.append(TrashBinResponse(**bin_dict))
    
    return response_list


@router.get("/bins/geojson", response_model=GeoJSONResponse)
async def get_trash_bins_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Çöp kutularını GeoJSON formatında getir
    """
    result = await db.execute(
        select(TrashBin).where(TrashBin.is_active == True)
    )
    bins = result.scalars().all()
    
    features = []
    for bin in bins:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": bin.id,
                "bin_type": bin.bin_type.value,
                "fill_level": bin.fill_level,
                "fill_color": get_fill_color(bin.fill_level),
                "capacity_liters": bin.capacity_liters,
                "needs_maintenance": bin.needs_maintenance,
                "has_sensor": bin.has_sensor,
                "type": "trash_bin"
            },
            geometry={
                "type": "Point",
                "coordinates": [bin.longitude, bin.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.get("/bins/{bin_id}", response_model=TrashBinResponse)
async def get_trash_bin(
    bin_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Tek bir çöp kutusunun detayını getir
    """
    result = await db.execute(
        select(TrashBin).where(TrashBin.id == bin_id)
    )
    bin = result.scalar_one_or_none()
    
    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Çöp kutusu bulunamadı"
        )
    
    bin_dict = TrashBinResponse.model_validate(bin).model_dump()
    bin_dict["fill_color"] = get_fill_color(bin.fill_level)
    return TrashBinResponse(**bin_dict)


@router.put("/bins/{bin_id}", response_model=TrashBinResponse)
async def update_trash_bin(
    bin_id: int,
    update_data: TrashBinUpdate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Çöp kutusu bilgilerini güncelle (IoT sensör güncellemesi için)
    """
    result = await db.execute(
        select(TrashBin).where(TrashBin.id == bin_id)
    )
    bin = result.scalar_one_or_none()
    
    if not bin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Çöp kutusu bulunamadı"
        )
    
    if update_data.fill_level is not None:
        bin.fill_level = update_data.fill_level
        from datetime import datetime
        bin.last_fill_update = datetime.utcnow()
    
    if update_data.needs_maintenance is not None:
        bin.needs_maintenance = update_data.needs_maintenance
    
    if update_data.is_active is not None:
        bin.is_active = update_data.is_active
    
    await db.flush()
    await db.refresh(bin)
    
    bin_dict = TrashBinResponse.model_validate(bin).model_dump()
    bin_dict["fill_color"] = get_fill_color(bin.fill_level)
    return TrashBinResponse(**bin_dict)


@router.get("/routes", response_model=List[TrashRouteResponse])
async def list_routes(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Çöp toplama rotalarını listele
    """
    query = select(TrashRoute)
    
    if active_only:
        query = query.where(TrashRoute.is_active == True)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    return [TrashRouteResponse.model_validate(r) for r in routes]


@router.post("/routes/optimize", response_model=TrashRouteOptimizeResponse)
async def optimize_route(
    request: TrashRouteOptimizeRequest,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Çöp toplama rotası optimize et (benzin ve km açısından)
    """
    # Çöp kutularını getir
    result = await db.execute(
        select(TrashBin).where(TrashBin.id.in_(request.bin_ids))
    )
    bins = result.scalars().all()
    
    if len(bins) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="En az 2 çöp kutusu gerekli"
        )
    
    # Basit nearest neighbor algoritması
    # (Gerçek projede OR-Tools ile daha gelişmiş optimizasyon yapılabilir)
    from geopy.distance import geodesic
    
    current_pos = (request.start_latitude, request.start_longitude)
    remaining_bins = list(bins)
    optimized_order = []
    waypoints = [{"lat": request.start_latitude, "lon": request.start_longitude, "bin_id": None}]
    total_distance = 0
    total_waste = 0
    
    while remaining_bins:
        # En yakın çöp kutusunu bul
        nearest = None
        nearest_dist = float('inf')
        
        for bin in remaining_bins:
            dist = geodesic(current_pos, (bin.latitude, bin.longitude)).kilometers
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = bin
        
        # Rotaya ekle
        optimized_order.append(nearest.id)
        waypoints.append({
            "lat": nearest.latitude,
            "lon": nearest.longitude,
            "bin_id": nearest.id
        })
        total_distance += nearest_dist
        
        # Tahmini atık miktarı (doluluk * kapasite)
        estimated_waste = (nearest.fill_level / 100) * nearest.capacity_liters * 0.5  # kg cinsinden
        total_waste += estimated_waste
        
        current_pos = (nearest.latitude, nearest.longitude)
        remaining_bins.remove(nearest)
    
    # Başlangıç noktasına dönüş
    return_dist = geodesic(current_pos, (request.start_latitude, request.start_longitude)).kilometers
    total_distance += return_dist
    waypoints.append({"lat": request.start_latitude, "lon": request.start_longitude, "bin_id": None})
    
    # Tahmini süre (ortalama 30 km/h hız + her durakta 3 dakika)
    estimated_duration = (total_distance / 30) * 60 + len(bins) * 3
    
    # Tahmini yakıt
    estimated_fuel = total_distance * request.fuel_consumption_per_km
    
    return TrashRouteOptimizeResponse(
        optimized_order=optimized_order,
        waypoints=waypoints,
        total_distance_km=round(total_distance, 2),
        estimated_duration_min=round(estimated_duration, 0),
        estimated_fuel_liters=round(estimated_fuel, 2),
        total_waste_kg=round(total_waste, 1)
    )


@router.get("/dashboard", response_model=TrashDashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Çöp yönetimi dashboard istatistikleri
    """
    # Toplam kutular
    total_result = await db.execute(select(func.count(TrashBin.id)))
    total_bins = total_result.scalar()
    
    # Aktif kutular
    active_result = await db.execute(
        select(func.count(TrashBin.id)).where(TrashBin.is_active == True)
    )
    active_bins = active_result.scalar()
    
    # Toplanması gerekenler (%80+)
    needs_collection_result = await db.execute(
        select(func.count(TrashBin.id)).where(
            TrashBin.is_active == True,
            TrashBin.fill_level >= 80
        )
    )
    bins_needing_collection = needs_collection_result.scalar()
    
    # Bakım gerektirenler
    needs_maintenance_result = await db.execute(
        select(func.count(TrashBin.id)).where(TrashBin.needs_maintenance == True)
    )
    bins_needing_maintenance = needs_maintenance_result.scalar()
    
    # Doluluk dağılımı
    bins_result = await db.execute(
        select(TrashBin).where(TrashBin.is_active == True)
    )
    all_bins = bins_result.scalars().all()
    
    fill_distribution = {"0-25": 0, "25-50": 0, "50-75": 0, "75-90": 0, "90-100": 0}
    total_fill = 0
    
    for bin in all_bins:
        total_fill += bin.fill_level
        if bin.fill_level < 25:
            fill_distribution["0-25"] += 1
        elif bin.fill_level < 50:
            fill_distribution["25-50"] += 1
        elif bin.fill_level < 75:
            fill_distribution["50-75"] += 1
        elif bin.fill_level < 90:
            fill_distribution["75-90"] += 1
        else:
            fill_distribution["90-100"] += 1
    
    avg_fill = total_fill / len(all_bins) if all_bins else 0
    
    # Bugünkü toplama sayısı
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    collections_result = await db.execute(
        select(func.count(TrashCollection.id)).where(
            TrashCollection.collected_at >= today_start
        )
    )
    collections_today = collections_result.scalar()
    
    return TrashDashboardStats(
        total_bins=total_bins,
        active_bins=active_bins,
        bins_needing_collection=bins_needing_collection,
        bins_needing_maintenance=bins_needing_maintenance,
        fill_distribution=fill_distribution,
        collections_today=collections_today,
        average_fill_level=round(avg_fill, 1)
    )

