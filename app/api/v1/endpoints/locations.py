"""
Konum Endpoint'leri - Hastane, Eczane
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geopy.distance import geodesic

from app.core.database import get_db
from app.models.location import Hospital, Pharmacy
from app.schemas.location import (
    HospitalResponse, PharmacyResponse, NearbyLocationResponse, GeoJSONResponse, GeoJSONFeature
)

router = APIRouter()


@router.get("/hospitals", response_model=List[HospitalResponse])
async def list_hospitals(
    latitude: Optional[float] = Query(None, description="Kullanıcı enlemi"),
    longitude: Optional[float] = Query(None, description="Kullanıcı boylamı"),
    radius_km: float = Query(5.0, description="Arama yarıçapı (km)"),
    has_emergency: Optional[bool] = Query(None, description="Sadece acil servisi olanlar"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Hastaneleri listele
    """
    query = select(Hospital).where(Hospital.id > 0)
    
    if has_emergency is not None:
        query = query.where(Hospital.has_emergency == has_emergency)
    
    query = query.limit(limit)
    result = await db.execute(query)
    hospitals = result.scalars().all()
    
    # Uzaklık hesapla
    response_list = []
    for hospital in hospitals:
        hospital_dict = HospitalResponse.model_validate(hospital).model_dump()
        
        if latitude and longitude:
            distance = geodesic(
                (latitude, longitude),
                (hospital.latitude, hospital.longitude)
            ).kilometers
            hospital_dict["distance_km"] = round(distance, 2)
            
            # Yarıçap filtresi
            if distance > radius_km:
                continue
        
        response_list.append(HospitalResponse(**hospital_dict))
    
    # Uzaklığa göre sırala
    if latitude and longitude:
        response_list.sort(key=lambda x: x.distance_km or 999)
    
    return response_list


@router.get("/hospitals/geojson", response_model=GeoJSONResponse)
async def get_hospitals_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Hastaneleri GeoJSON formatında getir (3D harita için)
    """
    result = await db.execute(select(Hospital))
    hospitals = result.scalars().all()
    
    features = []
    for hospital in hospitals:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": hospital.id,
                "name": hospital.name,
                "has_emergency": hospital.has_emergency,
                "phone": hospital.phone,
                "website": hospital.website,
                "operator": hospital.operator,
                "type": "hospital"
            },
            geometry={
                "type": "Point",
                "coordinates": [hospital.longitude, hospital.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.get("/pharmacies", response_model=List[PharmacyResponse])
async def list_pharmacies(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(3.0),
    on_duty_only: bool = Query(False, description="Sadece nöbetçi eczaneler"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Eczaneleri listele
    """
    query = select(Pharmacy).where(Pharmacy.id > 0)
    
    if on_duty_only:
        query = query.where(Pharmacy.is_on_duty == True)
    
    query = query.limit(limit)
    result = await db.execute(query)
    pharmacies = result.scalars().all()
    
    # Uzaklık hesapla
    response_list = []
    for pharmacy in pharmacies:
        pharmacy_dict = PharmacyResponse.model_validate(pharmacy).model_dump()
        
        if latitude and longitude:
            distance = geodesic(
                (latitude, longitude),
                (pharmacy.latitude, pharmacy.longitude)
            ).kilometers
            pharmacy_dict["distance_km"] = round(distance, 2)
            
            if distance > radius_km:
                continue
        
        response_list.append(PharmacyResponse(**pharmacy_dict))
    
    # Uzaklığa göre sırala
    if latitude and longitude:
        response_list.sort(key=lambda x: x.distance_km or 999)
    
    return response_list


@router.get("/pharmacies/geojson", response_model=GeoJSONResponse)
async def get_pharmacies_geojson(
    db: AsyncSession = Depends(get_db)
):
    """
    Eczaneleri GeoJSON formatında getir
    """
    result = await db.execute(select(Pharmacy))
    pharmacies = result.scalars().all()
    
    features = []
    for pharmacy in pharmacies:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": pharmacy.id,
                "name": pharmacy.name,
                "is_on_duty": pharmacy.is_on_duty,
                "phone": pharmacy.phone,
                "type": "pharmacy"
            },
            geometry={
                "type": "Point",
                "coordinates": [pharmacy.longitude, pharmacy.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


@router.get("/nearby", response_model=NearbyLocationResponse)
async def get_nearby_locations(
    latitude: float = Query(..., description="Kullanıcı enlemi"),
    longitude: float = Query(..., description="Kullanıcı boylamı"),
    radius_km: float = Query(3.0, description="Arama yarıçapı"),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcıya yakın hastane ve eczaneleri getir
    """
    # Hastaneler
    hospitals_result = await db.execute(select(Hospital))
    all_hospitals = hospitals_result.scalars().all()
    
    nearby_hospitals = []
    for hospital in all_hospitals:
        distance = geodesic(
            (latitude, longitude),
            (hospital.latitude, hospital.longitude)
        ).kilometers
        
        if distance <= radius_km:
            hospital_dict = HospitalResponse.model_validate(hospital).model_dump()
            hospital_dict["distance_km"] = round(distance, 2)
            nearby_hospitals.append(HospitalResponse(**hospital_dict))
    
    nearby_hospitals.sort(key=lambda x: x.distance_km or 999)
    
    # Eczaneler
    pharmacies_result = await db.execute(select(Pharmacy))
    all_pharmacies = pharmacies_result.scalars().all()
    
    nearby_pharmacies = []
    for pharmacy in all_pharmacies:
        distance = geodesic(
            (latitude, longitude),
            (pharmacy.latitude, pharmacy.longitude)
        ).kilometers
        
        if distance <= radius_km:
            pharmacy_dict = PharmacyResponse.model_validate(pharmacy).model_dump()
            pharmacy_dict["distance_km"] = round(distance, 2)
            nearby_pharmacies.append(PharmacyResponse(**pharmacy_dict))
    
    nearby_pharmacies.sort(key=lambda x: x.distance_km or 999)
    
    return NearbyLocationResponse(
        hospitals=nearby_hospitals[:10],
        pharmacies=nearby_pharmacies[:10],
        user_latitude=latitude,
        user_longitude=longitude,
        search_radius_km=radius_km
    )

