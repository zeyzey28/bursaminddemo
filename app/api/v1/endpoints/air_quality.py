"""
Hava Kalitesi Endpoint'leri
"""
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.air_quality import AirQualityReading, AirQualityLevel
from app.schemas.air_quality import (
    AirQualityResponse, AirQualityHeatmapResponse, 
    AirQualityHeatmapPoint, AirQualityStats
)
from app.schemas.location import GeoJSONResponse, GeoJSONFeature

router = APIRouter()

# Seviye açıklamaları
LEVEL_DESCRIPTIONS = {
    AirQualityLevel.GOOD: "Hava kalitesi iyi. Açık hava aktiviteleri için uygun.",
    AirQualityLevel.MODERATE: "Hava kalitesi kabul edilebilir. Hassas bireyler dikkatli olmalı.",
    AirQualityLevel.UNHEALTHY_SENSITIVE: "Hassas gruplar (çocuklar, yaşlılar, solunum hastaları) için sağlıksız.",
    AirQualityLevel.UNHEALTHY: "Herkes için sağlıksız. Uzun süreli açık hava aktivitelerinden kaçının.",
    AirQualityLevel.VERY_UNHEALTHY: "Çok sağlıksız. Dışarı çıkmaktan kaçının.",
    AirQualityLevel.HAZARDOUS: "Tehlikeli! Acil sağlık uyarısı. Dışarı çıkmayın."
}

HEALTH_ADVICE = {
    AirQualityLevel.GOOD: "Açık hava aktivitelerinin keyfini çıkarın.",
    AirQualityLevel.MODERATE: "Hassas bireyler uzun süreli açık hava aktivitelerini sınırlandırmalı.",
    AirQualityLevel.UNHEALTHY_SENSITIVE: "Hassas gruplar açık hava aktivitelerini azaltmalı. Maske kullanımı önerilir.",
    AirQualityLevel.UNHEALTHY: "Herkes açık hava aktivitelerini sınırlandırmalı. N95 maske kullanın.",
    AirQualityLevel.VERY_UNHEALTHY: "Tüm açık hava aktivitelerini iptal edin. Evde kalın.",
    AirQualityLevel.HAZARDOUS: "ACİL: Dışarı çıkmayın! Pencere ve kapıları kapalı tutun."
}


@router.get("/current", response_model=List[AirQualityResponse])
async def get_current_air_quality(
    db: AsyncSession = Depends(get_db)
):
    """
    Güncel hava kalitesi verilerini getir
    """
    # Son 1 saatteki veriler
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await db.execute(
        select(AirQualityReading)
        .where(AirQualityReading.recorded_at >= one_hour_ago)
        .order_by(AirQualityReading.recorded_at.desc())
    )
    readings = result.scalars().all()
    
    response_list = []
    for reading in readings:
        reading_dict = AirQualityResponse.model_validate(reading).model_dump()
        reading_dict["level_description"] = LEVEL_DESCRIPTIONS.get(reading.level, "")
        reading_dict["health_advice"] = HEALTH_ADVICE.get(reading.level, "")
        response_list.append(AirQualityResponse(**reading_dict))
    
    return response_list


@router.get("/heatmap", response_model=AirQualityHeatmapResponse)
async def get_air_quality_heatmap(
    db: AsyncSession = Depends(get_db)
):
    """
    Hava kalitesi heatmap verisi (harita görselleştirmesi için)
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await db.execute(
        select(AirQualityReading)
        .where(AirQualityReading.recorded_at >= one_hour_ago)
    )
    readings = result.scalars().all()
    
    if not readings:
        return AirQualityHeatmapResponse(
            points=[],
            min_aqi=0,
            max_aqi=0,
            average_aqi=0,
            timestamp=datetime.utcnow()
        )
    
    points = []
    aqi_values = []
    
    for reading in readings:
        # Yoğunluk hesapla (0-1 arası, AQI'ye göre)
        intensity = min(reading.aqi / 300, 1.0)
        
        point = AirQualityHeatmapPoint(
            latitude=reading.latitude,
            longitude=reading.longitude,
            aqi=reading.aqi,
            color=reading.color_code,
            intensity=intensity
        )
        points.append(point)
        aqi_values.append(reading.aqi)
    
    return AirQualityHeatmapResponse(
        points=points,
        min_aqi=min(aqi_values),
        max_aqi=max(aqi_values),
        average_aqi=sum(aqi_values) / len(aqi_values),
        timestamp=datetime.utcnow()
    )


@router.get("/geojson", response_model=GeoJSONResponse)
async def get_air_quality_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Hava kalitesi verilerini GeoJSON formatında getir
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await db.execute(
        select(AirQualityReading)
        .where(AirQualityReading.recorded_at >= one_hour_ago)
    )
    readings = result.scalars().all()
    
    features = []
    for reading in readings:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": reading.id,
                "station_name": reading.station_name,
                "aqi": reading.aqi,
                "level": reading.level.value,
                "color": reading.color_code,
                "pm25": reading.pm25,
                "pm10": reading.pm10,
                "recorded_at": reading.recorded_at.isoformat(),
                "type": "air_quality"
            },
            geometry={
                "type": "Point",
                "coordinates": [reading.longitude, reading.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.get("/stats", response_model=AirQualityStats)
async def get_air_quality_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Hava kalitesi istatistikleri
    """
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # Son 1 saatteki veriler (güncel)
    current_result = await db.execute(
        select(AirQualityReading)
        .where(AirQualityReading.recorded_at >= one_hour_ago)
    )
    current_readings = current_result.scalars().all()
    
    # Son 24 saatteki veriler
    daily_result = await db.execute(
        select(AirQualityReading)
        .where(AirQualityReading.recorded_at >= twenty_four_hours_ago)
    )
    daily_readings = daily_result.scalars().all()
    
    if not current_readings:
        return AirQualityStats(
            current_average_aqi=0,
            current_level="good",
            last_24h_average=0,
            last_24h_max=0,
            last_24h_min=0,
            trend="stable",
            trend_percentage=0
        )
    
    # Güncel ortalama
    current_avg = sum(r.aqi for r in current_readings) / len(current_readings)
    current_level = AirQualityReading.get_level_for_aqi(int(current_avg))
    
    # 24 saatlik istatistikler
    if daily_readings:
        daily_aqi = [r.aqi for r in daily_readings]
        daily_avg = sum(daily_aqi) / len(daily_aqi)
        daily_max = max(daily_aqi)
        daily_min = min(daily_aqi)
        
        # PM değerleri
        pm25_values = [r.pm25 for r in daily_readings if r.pm25]
        pm10_values = [r.pm10 for r in daily_readings if r.pm10]
        avg_pm25 = sum(pm25_values) / len(pm25_values) if pm25_values else None
        avg_pm10 = sum(pm10_values) / len(pm10_values) if pm10_values else None
    else:
        daily_avg = current_avg
        daily_max = int(current_avg)
        daily_min = int(current_avg)
        avg_pm25 = None
        avg_pm10 = None
    
    # Trend hesapla
    if daily_avg > 0:
        trend_pct = ((current_avg - daily_avg) / daily_avg) * 100
        if trend_pct < -5:
            trend = "improving"
        elif trend_pct > 5:
            trend = "worsening"
        else:
            trend = "stable"
    else:
        trend = "stable"
        trend_pct = 0
    
    return AirQualityStats(
        current_average_aqi=round(current_avg, 1),
        current_level=current_level.value,
        last_24h_average=round(daily_avg, 1),
        last_24h_max=daily_max,
        last_24h_min=daily_min,
        trend=trend,
        trend_percentage=round(trend_pct, 1),
        avg_pm25=round(avg_pm25, 1) if avg_pm25 else None,
        avg_pm10=round(avg_pm10, 1) if avg_pm10 else None
    )


@router.get("/history")
async def get_air_quality_history(
    hours: int = Query(24, ge=1, le=168, description="Geçmiş saat sayısı (max 7 gün)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Hava kalitesi geçmişi (grafik için)
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    result = await db.execute(
        select(AirQualityReading)
        .where(AirQualityReading.recorded_at >= start_time)
        .order_by(AirQualityReading.recorded_at)
    )
    readings = result.scalars().all()
    
    # Saatlik ortalamalar
    hourly_data = {}
    for reading in readings:
        hour_key = reading.recorded_at.strftime("%Y-%m-%d %H:00")
        if hour_key not in hourly_data:
            hourly_data[hour_key] = {"aqi_sum": 0, "count": 0}
        hourly_data[hour_key]["aqi_sum"] += reading.aqi
        hourly_data[hour_key]["count"] += 1
    
    history = []
    for hour, data in sorted(hourly_data.items()):
        avg_aqi = data["aqi_sum"] / data["count"]
        history.append({
            "timestamp": hour,
            "average_aqi": round(avg_aqi, 1),
            "level": AirQualityReading.get_level_for_aqi(int(avg_aqi)).value,
            "color": AirQualityReading.get_color_for_aqi(int(avg_aqi))
        })
    
    return {"history": history, "hours": hours}

