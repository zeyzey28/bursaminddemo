"""
Trafik Endpoint'leri
"""
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.location import TrafficPoint, TrafficLevel
from app.schemas.location import TrafficPointResponse, GeoJSONResponse, GeoJSONFeature

router = APIRouter()

# Emoji mapping
TRAFFIC_EMOJIS = {
    TrafficLevel.VERY_LOW: "😊",
    TrafficLevel.LOW: "🙂",
    TrafficLevel.MODERATE: "😐",
    TrafficLevel.HIGH: "😟",
    TrafficLevel.VERY_HIGH: "😫"
}

TRAFFIC_COLORS = {
    TrafficLevel.VERY_LOW: "#00FF00",   # Yeşil
    TrafficLevel.LOW: "#90EE90",         # Açık yeşil
    TrafficLevel.MODERATE: "#FFFF00",    # Sarı
    TrafficLevel.HIGH: "#FFA500",        # Turuncu
    TrafficLevel.VERY_HIGH: "#FF0000"    # Kırmızı
}


@router.get("/", response_model=List[TrafficPointResponse])
async def get_traffic_points(
    min_lat: float = Query(None),
    max_lat: float = Query(None),
    min_lon: float = Query(None),
    max_lon: float = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Trafik noktalarını getir
    """
    # Son 1 saatteki veriler
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    query = select(TrafficPoint).where(
        TrafficPoint.recorded_at >= one_hour_ago
    )
    
    # Bounding box filtresi
    if all([min_lat, max_lat, min_lon, max_lon]):
        query = query.where(
            and_(
                TrafficPoint.latitude >= min_lat,
                TrafficPoint.latitude <= max_lat,
                TrafficPoint.longitude >= min_lon,
                TrafficPoint.longitude <= max_lon
            )
        )
    
    result = await db.execute(query)
    points = result.scalars().all()
    
    return [TrafficPointResponse.model_validate(p) for p in points]


@router.get("/geojson", response_model=GeoJSONResponse)
async def get_traffic_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Trafik verilerini GeoJSON formatında getir (3D harita için duygu ikonları)
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await db.execute(
        select(TrafficPoint).where(TrafficPoint.recorded_at >= one_hour_ago)
    )
    points = result.scalars().all()
    
    features = []
    for point in points:
        emoji = TRAFFIC_EMOJIS.get(point.traffic_level, "😐")
        color = TRAFFIC_COLORS.get(point.traffic_level, "#FFFF00")
        
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": point.id,
                "road_name": point.road_name,
                "traffic_level": point.traffic_level.value,
                "emoji": emoji,
                "color": color,
                "speed_kmh": point.speed_kmh,
                "congestion_percent": point.congestion_percent,
                "recorded_at": point.recorded_at.isoformat(),
                "type": "traffic"
            },
            geometry={
                "type": "Point",
                "coordinates": [point.longitude, point.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.get("/summary")
async def get_traffic_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Trafik özeti - Naim Süleymanoğlu Bulvarı için
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await db.execute(
        select(TrafficPoint).where(TrafficPoint.recorded_at >= one_hour_ago)
    )
    points = result.scalars().all()
    
    if not points:
        return {
            "average_congestion": 0,
            "dominant_level": "moderate",
            "dominant_emoji": "😐",
            "total_points": 0,
            "levels_distribution": {}
        }
    
    # Ortalama tıkanıklık
    avg_congestion = sum(p.congestion_percent for p in points) / len(points)
    
    # Seviye dağılımı
    levels = {}
    for point in points:
        level = point.traffic_level.value
        levels[level] = levels.get(level, 0) + 1
    
    # Baskın seviye
    dominant_level = max(levels, key=levels.get)
    dominant_emoji = TRAFFIC_EMOJIS.get(TrafficLevel(dominant_level), "😐")
    
    return {
        "average_congestion": round(avg_congestion, 1),
        "dominant_level": dominant_level,
        "dominant_emoji": dominant_emoji,
        "total_points": len(points),
        "levels_distribution": levels
    }

