"""
Trafik Risk ve Segment Endpoint'leri
Belediye paneli için segment risk analizi ve what-if senaryoları
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_municipality
from app.models.traffic_risk import SegmentRisk, TrafficForecast, WhatIfScenario, RiskLevel
from app.schemas.traffic_risk import (
    SegmentRiskResponse, SegmentSeriesResponse, TrafficForecastResponse,
    WhatIfRequest, WhatIfResponse
)
import pandas as pd
import json
# Lazy import - sadece kullanıldığında yükle
# from app.services.traffic_risk_service import TrafficRiskService
# from app.services.traffic_whatif_service import TrafficWhatIfService

router = APIRouter()


@router.get("/segments/risk", response_model=List[SegmentRiskResponse])
async def get_segment_risks(
    segment_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),  # Son N saat
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Segment risk durumlarını getir (Belediye paneli - 3D harita için)
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(SegmentRisk).where(
        SegmentRisk.timestamp >= cutoff_time
    )
    
    if segment_id:
        query = query.where(SegmentRisk.segment_id == segment_id)
    
    if risk_level:
        try:
            risk_level_enum = RiskLevel(risk_level)
            query = query.where(SegmentRisk.risk_level == risk_level_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz risk seviyesi: {risk_level}"
            )
    
    query = query.order_by(desc(SegmentRisk.timestamp), desc(SegmentRisk.risk_score))
    
    result = await db.execute(query)
    risks = result.scalars().all()
    
    # Response formatına dönüştür
    responses = []
    for risk in risks:
        responses.append(SegmentRiskResponse(
            segment_id=risk.segment_id,
            timestamp=risk.timestamp,
            risk={
                "score": risk.risk_score,
                "level": risk.risk_level.value,
                "type": risk.risk_types or []
            },
            traffic={
                "current_density": risk.current_density,
                "expected_2h": risk.expected_2h
            },
            complaints={
                "count_24h": risk.complaint_count_24h,
                "avg_urgency_24h": risk.avg_urgency_24h
            },
            explanation=risk.explanation
        ))
    
    return responses


@router.get("/segments/{segment_id}/series", response_model=SegmentSeriesResponse)
async def get_segment_series(
    segment_id: str,
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Segment zaman serisi verilerini getir (Belediye paneli - grafik için)
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    result = await db.execute(
        select(SegmentRisk)
        .where(
            and_(
                SegmentRisk.segment_id == segment_id,
                SegmentRisk.timestamp >= cutoff_time
            )
        )
        .order_by(SegmentRisk.timestamp)
    )
    risks = result.scalars().all()
    
    series = []
    for risk in risks:
        series.append({
            "time": risk.timestamp,
            "traffic_density": risk.current_density,
            "risk_score": risk.risk_score
        })
    
    return SegmentSeriesResponse(
        segment_id=segment_id,
        series=series
    )


@router.post("/what-if", response_model=WhatIfResponse)
async def create_whatif_scenario(
    request: WhatIfRequest,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    What-if senaryosu oluştur (Belediye paneli - yol çalışması simülasyonu)
    """
    # Segment risk verilerini al
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(SegmentRisk)
        .where(
            and_(
                SegmentRisk.segment_id == request.segment_id,
                SegmentRisk.timestamp >= cutoff_time
            )
        )
        .order_by(SegmentRisk.timestamp)
    )
    risks = result.scalars().all()
    
    if not risks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment {request.segment_id} için risk verisi bulunamadı"
        )
    
    # DataFrame'e dönüştür
    df_data = []
    for risk in risks:
        df_data.append({
            "segment_id": risk.segment_id,
            "timestamp": risk.timestamp,
            "risk_score": risk.risk_score
        })
    df = pd.DataFrame(df_data)
    
    # What-if servisi (lazy import)
    from app.services.traffic_whatif_service import TrafficWhatIfService
    whatif_service = TrafficWhatIfService()
    
    # Spatial neighbors oluştur (bir kere, cache'lenebilir)
    # TODO: Bu kısmı optimize et - neighbors'ı cache'le
    # whatif_service.build_spatial_neighbors(segments_gdf)
    
    # Senaryoyu çalıştır
    scenario_result = whatif_service.what_if_road_work(
        seg_status_df=df,
        segment_id=request.segment_id,
        lane_closed=request.lane_closed,
        duration_hours=request.duration_hours,
        start_time=request.start_time,
        max_hops=5
    )
    
    # Veritabanına kaydet
    whatif = WhatIfScenario(
        scenario_type="road_work",
        segment_id=request.segment_id,
        lane_closed=request.lane_closed,
        duration_hours=request.duration_hours,
        start_time=request.start_time,
        affected_segments=scenario_result["affected_segments"],
        best_time_window=scenario_result["best_time_window"],
        summary=scenario_result["summary"],
        created_by=int(current_user["user_id"])
    )
    db.add(whatif)
    await db.commit()
    
    return WhatIfResponse(**scenario_result)


@router.get("/what-if", response_model=List[WhatIfResponse])
async def list_whatif_scenarios(
    segment_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    What-if senaryolarını listele (Belediye paneli)
    """
    query = select(WhatIfScenario).order_by(desc(WhatIfScenario.created_at))
    
    if segment_id:
        query = query.where(WhatIfScenario.segment_id == segment_id)
    
    result = await db.execute(query.limit(50))
    scenarios = result.scalars().all()
    
    responses = []
    for scenario in scenarios:
        responses.append(WhatIfResponse(
            scenario=scenario.scenario_type,
            segment_id=scenario.segment_id,
            impact={
                "lane_closed": scenario.lane_closed,
                "duration_hours": scenario.duration_hours
            },
            start_time=scenario.start_time,
            affected_segments=scenario.affected_segments or [],
            best_time_window=scenario.best_time_window or {"start": "00:00", "end": "00:00"},
            summary=scenario.summary or ""
        ))
    
    return responses

