"""
Gölgeli/Aydınlık Yürüyüş Rotaları Endpoint'leri
"""
from typing import List
from datetime import datetime, time
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.shadow import ShadowRoute
from app.schemas.shadow import ShadowRouteResponse, ShadowRouteRequest, RoutePreference
from app.schemas.location import GeoJSONResponse, GeoJSONFeature

router = APIRouter()


@router.get("/", response_model=List[ShadowRouteResponse])
async def list_shadow_routes(
    shaded_only: bool = Query(False, description="Sadece gölgeli rotalar"),
    lit_only: bool = Query(False, description="Sadece aydınlatmalı rotalar"),
    accessible_only: bool = Query(False, description="Sadece engelli erişimine uygun"),
    db: AsyncSession = Depends(get_db)
):
    """
    Gölgeli/aydınlık yürüyüş rotalarını listele
    """
    query = select(ShadowRoute).where(ShadowRoute.is_active == True)
    
    if shaded_only:
        query = query.where(ShadowRoute.is_shaded_route == True)
    
    if lit_only:
        query = query.where(ShadowRoute.is_lit_route == True)
    
    if accessible_only:
        query = query.where(ShadowRoute.is_accessible == True)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    return [ShadowRouteResponse.model_validate(r) for r in routes]


@router.get("/geojson", response_model=GeoJSONResponse)
async def get_shadow_routes_geojson(
    route_type: str = Query("all", description="all, shaded, lit"),
    db: AsyncSession = Depends(get_db)
):
    """
    Gölgeli rotaları GeoJSON formatında getir (harita için)
    """
    query = select(ShadowRoute).where(ShadowRoute.is_active == True)
    
    if route_type == "shaded":
        query = query.where(ShadowRoute.is_shaded_route == True)
    elif route_type == "lit":
        query = query.where(ShadowRoute.is_lit_route == True)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    features = []
    for route in routes:
        import json
        try:
            coords = json.loads(route.coordinates)
        except:
            coords = []
        
        # Renk belirleme
        if route.is_shaded_route and route.shade_percentage >= 70:
            color = "#228B22"  # Koyu yeşil - çok gölgeli
        elif route.is_shaded_route:
            color = "#90EE90"  # Açık yeşil - orta gölgeli
        elif route.is_lit_route:
            color = "#FFD700"  # Altın - aydınlatmalı
        else:
            color = "#808080"  # Gri - normal
        
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": route.id,
                "name": route.name,
                "description": route.description,
                "shade_percentage": route.shade_percentage,
                "is_shaded_route": route.is_shaded_route,
                "is_lit_route": route.is_lit_route,
                "is_accessible": route.is_accessible,
                "distance_km": route.distance_km,
                "estimated_walk_time_min": route.estimated_walk_time_min,
                "color": color,
                "type": "shadow_route"
            },
            geometry={
                "type": "LineString",
                "coordinates": coords
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.post("/find")
async def find_best_route(
    request: ShadowRouteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    İki nokta arasında en uygun gölgeli/aydınlık rotayı bul
    """
    from geopy.distance import geodesic
    
    query = select(ShadowRoute).where(ShadowRoute.is_active == True)
    
    # Tercihlere göre filtrele
    if request.preferences.prefer_shade:
        query = query.where(ShadowRoute.is_shaded_route == True)
    
    if request.preferences.prefer_lit:
        query = query.where(ShadowRoute.is_lit_route == True)
    
    if request.preferences.accessible_only:
        query = query.where(ShadowRoute.is_accessible == True)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    if not routes:
        return {
            "found": False,
            "message": "Kriterlere uygun rota bulunamadı",
            "routes": []
        }
    
    # Başlangıç ve bitiş noktalarına en yakın rotaları bul
    scored_routes = []
    
    for route in routes:
        # Başlangıç noktasına uzaklık
        start_dist = geodesic(
            (request.start_latitude, request.start_longitude),
            (route.start_latitude, route.start_longitude)
        ).kilometers
        
        # Bitiş noktasına uzaklık
        end_dist = geodesic(
            (request.end_latitude, request.end_longitude),
            (route.end_latitude, route.end_longitude)
        ).kilometers
        
        # Toplam sapma
        total_deviation = start_dist + end_dist
        
        # Mesafe filtresi
        if request.preferences.max_distance_km:
            if route.distance_km and route.distance_km > request.preferences.max_distance_km:
                continue
        
        # Skor hesapla (düşük sapma + yüksek gölge = iyi)
        shade_bonus = route.shade_percentage / 100 if request.preferences.prefer_shade else 0
        score = total_deviation - shade_bonus
        
        scored_routes.append({
            "route": ShadowRouteResponse.model_validate(route),
            "start_deviation_km": round(start_dist, 2),
            "end_deviation_km": round(end_dist, 2),
            "total_deviation_km": round(total_deviation, 2),
            "score": round(score, 3)
        })
    
    # Skora göre sırala
    scored_routes.sort(key=lambda x: x["score"])
    
    return {
        "found": len(scored_routes) > 0,
        "total_routes": len(scored_routes),
        "routes": scored_routes[:5]  # En iyi 5 rota
    }


@router.get("/recommendations")
async def get_route_recommendations(
    latitude: float = Query(..., description="Kullanıcı enlemi"),
    longitude: float = Query(..., description="Kullanıcı boylamı"),
    time_of_day: str = Query("day", description="day veya night"),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcının konumuna ve zamana göre rota önerileri
    """
    from geopy.distance import geodesic
    
    query = select(ShadowRoute).where(ShadowRoute.is_active == True)
    
    # Gündüz gölgeli, gece aydınlık rotalar
    if time_of_day == "night":
        query = query.where(ShadowRoute.is_lit_route == True)
    else:
        query = query.where(ShadowRoute.is_shaded_route == True)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    # Yakınlığa göre sırala
    nearby_routes = []
    for route in routes:
        dist = geodesic(
            (latitude, longitude),
            (route.start_latitude, route.start_longitude)
        ).kilometers
        
        if dist <= 5:  # 5 km içindeki rotalar
            nearby_routes.append({
                "route": ShadowRouteResponse.model_validate(route),
                "distance_km": round(dist, 2)
            })
    
    nearby_routes.sort(key=lambda x: x["distance_km"])
    
    recommendation_text = (
        "Gece yürüyüşü için aydınlatmalı rotalar önerilir." 
        if time_of_day == "night" 
        else "Gündüz yürüyüşü için gölgeli rotalar serin kalmanızı sağlar."
    )
    
    return {
        "time_of_day": time_of_day,
        "recommendation": recommendation_text,
        "nearby_routes": nearby_routes[:5]
    }

