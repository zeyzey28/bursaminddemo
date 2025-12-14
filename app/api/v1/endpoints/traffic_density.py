"""
Trafik Yoğunluğu Endpoint'leri
Herkes için trafik yoğunluğu ve tahmin verileri
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.models.traffic_risk import TrafficForecast
from app.schemas.traffic_risk import TrafficForecastResponse

router = APIRouter()


@router.get("/forecast", response_model=List[TrafficForecastResponse])
async def get_traffic_forecast(
    segment_id: Optional[str] = Query(None),
    signal_id: Optional[int] = Query(None),
    hours: int = Query(2, ge=1, le=24),  # Son N saat
    db: AsyncSession = Depends(get_db)
):
    """
    Trafik yoğunluğu ve tahmin verilerini getir (Herkes için)
    
    Eğer belirtilen saat içinde veri yoksa, en son mevcut verileri döner.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(TrafficForecast).where(
        TrafficForecast.timestamp >= cutoff_time
    )
    
    if segment_id:
        query = query.where(TrafficForecast.segment_id == segment_id)
    
    if signal_id:
        query = query.where(TrafficForecast.signal_id == signal_id)
    
    query = query.order_by(desc(TrafficForecast.timestamp))
    
    result = await db.execute(query)
    forecasts = result.scalars().all()
    
    # Eğer belirtilen saat içinde veri yoksa, en son verileri al (son 7 gün)
    if not forecasts:
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        query = select(TrafficForecast).where(
            TrafficForecast.timestamp >= cutoff_time
        )
        
        if segment_id:
            query = query.where(TrafficForecast.segment_id == segment_id)
        
        if signal_id:
            query = query.where(TrafficForecast.signal_id == signal_id)
        
        query = query.order_by(desc(TrafficForecast.timestamp))
        
        result = await db.execute(query)
        forecasts = result.scalars().all()
    
    return [TrafficForecastResponse.model_validate(f) for f in forecasts]


@router.get("/forecast/current", response_model=List[TrafficForecastResponse])
async def get_current_traffic(
    segment_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Şu anki trafik yoğunluğunu getir (Herkes için - 3D harita)
    
    En son trafik verilerini getirir. Eğer son 15 dakika içinde veri yoksa,
    en son mevcut verileri döner.
    """
    # Önce son 15 dakika içindeki verileri kontrol et
    cutoff_time = datetime.utcnow() - timedelta(minutes=15)
    
    query = select(TrafficForecast).where(
        TrafficForecast.timestamp >= cutoff_time
    )
    
    if segment_id:
        query = query.where(TrafficForecast.segment_id == segment_id)
    
    query = query.order_by(desc(TrafficForecast.timestamp))
    
    result = await db.execute(query)
    forecasts = result.scalars().all()
    
    # Eğer son 15 dakika içinde veri yoksa, en son verileri al (son 24 saat)
    if not forecasts:
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        query = select(TrafficForecast).where(
            TrafficForecast.timestamp >= cutoff_time
        )
        
        if segment_id:
            query = query.where(TrafficForecast.segment_id == segment_id)
        
        query = query.order_by(desc(TrafficForecast.timestamp))
        
        result = await db.execute(query)
        forecasts = result.scalars().all()
    
    # Segment/signal bazında grupla ve en son veriyi al
    seen_segments = set()
    unique_forecasts = []
    for forecast in forecasts:
        key = forecast.segment_id or f"signal_{forecast.signal_id}"
        if key not in seen_segments:
            seen_segments.add(key)
            unique_forecasts.append(forecast)
    
    return [TrafficForecastResponse.model_validate(f) for f in unique_forecasts]

