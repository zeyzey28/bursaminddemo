"""
Konum Endpoint'leri - Hastane, Eczane, Kütüphane, Park + OSRM Routing
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from geopy.distance import geodesic

from app.core.database import get_db
from app.models.location import Hospital, Pharmacy, Library, Park
from app.schemas.location import (
    HospitalResponse, PharmacyResponse, LibraryResponse, ParkResponse,
    NearbyLocationResponse, GeoJSONResponse, GeoJSONFeature,
    RouteRequest, NearestLocationRequest, LocationSearchRequest,
    RouteResponse, NearestWithRouteResponse
)
from app.services.osrm_service import osrm_service, RoutePoint

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


@router.get("/pharmacies/on-duty/nearest")
async def find_nearest_on_duty_pharmacy(
    latitude: float = Query(..., description="Kullanıcı enlemi"),
    longitude: float = Query(..., description="Kullanıcı boylamı"),
    profile: str = Query("driving", description="Ulaşım türü: driving, walking"),
    night_mode: bool = Query(False, description="Gece modu: Aydınlık yolları tercih et"),
    db: AsyncSession = Depends(get_db)
):
    """
    🚨 NÖBETÇİ ECZANE BUL - En yakın nöbetçi eczaneyi bul ve yol tarifi al
    
    Bu endpoint "Nöbetçi Eczane Bul" butonuna basıldığında çağrılır.
    Kullanıcının konumundan en yakın nöbetçi eczaneyi bulur ve
    gerçek yol rotasını hesaplar.
    
    Gece modu (night_mode=true) aktifse, aydınlık yolları tercih eder.
    """
    from app.services.osrm_service import osrm_service, RoutePoint
    from app.services.night_mode_routing import NightModeRoutingService
    
    # Nöbetçi eczaneleri getir
    result = await db.execute(
        select(Pharmacy).where(Pharmacy.is_on_duty == True)
    )
    on_duty_pharmacies = result.scalars().all()
    
    if not on_duty_pharmacies:
        return {
            "found": False,
            "message": "Şu anda nöbetçi eczane bulunamadı",
            "pharmacy": None,
            "route": None
        }
    
    # Kullanıcı konumu
    user_location = RoutePoint(
        latitude=latitude,
        longitude=longitude,
        name="Konumunuz"
    )
    
    # Gece modu aktifse
    if night_mode:
        night_service = NightModeRoutingService(db)
        
        # Tüm nöbetçi eczaneleri RoutePoint'e çevir
        pharmacy_points = [
            RoutePoint(
                latitude=p.latitude,
                longitude=p.longitude,
                name=p.name
            )
            for p in on_duty_pharmacies
        ]
        
        # Gece modu ile en yakın eczaneyi bul
        results = await night_service.get_nearest_with_night_route(
            user_location, pharmacy_points, profile=profile, top_n=1
        )
        
        if not results:
            return {
                "found": False,
                "message": "Gece modu rotası hesaplanamadı",
                "pharmacy": None,
                "route": None
            }
        
        best_result = results[0]
        best_pharmacy = next(
            p for p in on_duty_pharmacies
            if p.latitude == best_result["destination"]["latitude"]
            and p.longitude == best_result["destination"]["longitude"]
        )
        
        return {
            "found": True,
            "fallback": False,
            "night_mode": True,
            "message": f"En yakın nöbetçi eczane (Aydınlık Yol): {best_pharmacy.name}",
            "pharmacy": {
                "id": best_pharmacy.id,
                "name": best_pharmacy.name,
                "address": best_pharmacy.address,
                "phone": best_pharmacy.phone,
                "latitude": best_pharmacy.latitude,
                "longitude": best_pharmacy.longitude,
                "is_on_duty": True,
                "icon": "💊"
            },
            "distance_km": best_result["distance_km"],
            "duration_min": best_result["duration_min"],
            "route": best_result["route"],
            "lighting_analysis": best_result["lighting_analysis"]
        }
    
    # Normal mod (en kısa yol)
    best_pharmacy = None
    best_route = None
    best_distance = float('inf')
    
    for pharmacy in on_duty_pharmacies:
        pharmacy_point = RoutePoint(
            latitude=pharmacy.latitude,
            longitude=pharmacy.longitude,
            name=pharmacy.name
        )
        
        # OSRM ile gerçek rota hesapla
        route = await osrm_service.get_route(user_location, pharmacy_point, profile=profile)
        
        if route and route.distance_km < best_distance:
            best_distance = route.distance_km
            best_pharmacy = pharmacy
            best_route = route
    
    if not best_pharmacy:
        # Fallback: Kuş uçuşu en yakın
        best_pharmacy = min(
            on_duty_pharmacies,
            key=lambda p: geodesic(
                (latitude, longitude),
                (p.latitude, p.longitude)
            ).kilometers
        )
        straight_distance = geodesic(
            (latitude, longitude),
            (best_pharmacy.latitude, best_pharmacy.longitude)
        ).kilometers
        
        return {
            "found": True,
            "fallback": True,
            "message": "Rota hesaplanamadı, kuş uçuşu mesafe gösteriliyor",
            "pharmacy": {
                "id": best_pharmacy.id,
                "name": best_pharmacy.name,
                "address": best_pharmacy.address,
                "phone": best_pharmacy.phone,
                "latitude": best_pharmacy.latitude,
                "longitude": best_pharmacy.longitude,
                "is_on_duty": True,
                "icon": "💊"
            },
            "distance_km": round(straight_distance, 2),
            "route": None
        }
    
    return {
        "found": True,
        "fallback": False,
        "night_mode": False,
        "message": f"En yakın nöbetçi eczane: {best_pharmacy.name}",
        "pharmacy": {
            "id": best_pharmacy.id,
            "name": best_pharmacy.name,
            "address": best_pharmacy.address,
            "phone": best_pharmacy.phone,
            "latitude": best_pharmacy.latitude,
            "longitude": best_pharmacy.longitude,
            "is_on_duty": True,
            "duty_date": best_pharmacy.duty_date.isoformat() if best_pharmacy.duty_date else None,
            "icon": "💊"
        },
        "distance_km": best_route.distance_km,
        "duration_min": best_route.duration_min,
        "profile": profile,
        "route": {
            "geometry": best_route.geometry,
            "steps": best_route.steps
        },
        "navigation_instructions": [
            {
                "step": i + 1,
                "instruction": step.get("instruction") or step.get("name", "Devam et"),
                "distance_m": step.get("distance_m", 0),
                "road_name": step.get("name", "")
            }
            for i, step in enumerate(best_route.steps[:10])  # İlk 10 adım
        ]
    }


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
    
    # Kütüphaneler
    libraries_result = await db.execute(select(Library).where(Library.is_active == True))
    all_libraries = libraries_result.scalars().all()
    
    nearby_libraries = []
    for library in all_libraries:
        distance = geodesic(
            (latitude, longitude),
            (library.latitude, library.longitude)
        ).kilometers
        
        if distance <= radius_km:
            library_dict = LibraryResponse.model_validate(library).model_dump()
            library_dict["distance_km"] = round(distance, 2)
            nearby_libraries.append(LibraryResponse(**library_dict))
    
    nearby_libraries.sort(key=lambda x: x.distance_km or 999)
    
    # Parklar
    parks_result = await db.execute(select(Park).where(Park.is_active == True))
    all_parks = parks_result.scalars().all()
    
    nearby_parks = []
    for park in all_parks:
        distance = geodesic(
            (latitude, longitude),
            (park.latitude, park.longitude)
        ).kilometers
        
        if distance <= radius_km:
            park_dict = ParkResponse.model_validate(park).model_dump()
            park_dict["distance_km"] = round(distance, 2)
            nearby_parks.append(ParkResponse(**park_dict))
    
    nearby_parks.sort(key=lambda x: x.distance_km or 999)
    
    return NearbyLocationResponse(
        hospitals=nearby_hospitals[:10],
        pharmacies=nearby_pharmacies[:10],
        libraries=nearby_libraries[:10],
        parks=nearby_parks[:10],
        user_latitude=latitude,
        user_longitude=longitude,
        search_radius_km=radius_km
    )


# ============================================
# KÜTÜPHANE ENDPOİNT'LERİ
# ============================================

@router.get("/libraries", response_model=List[LibraryResponse])
async def list_libraries(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(5.0),
    has_wifi: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Kütüphaneleri listele
    """
    query = select(Library).where(Library.is_active == True)
    
    if has_wifi is not None:
        query = query.where(Library.has_wifi == has_wifi)
    
    query = query.limit(limit)
    result = await db.execute(query)
    libraries = result.scalars().all()
    
    response_list = []
    for library in libraries:
        library_dict = LibraryResponse.model_validate(library).model_dump()
        
        if latitude and longitude:
            distance = geodesic(
                (latitude, longitude),
                (library.latitude, library.longitude)
            ).kilometers
            library_dict["distance_km"] = round(distance, 2)
            
            if distance > radius_km:
                continue
        
        response_list.append(LibraryResponse(**library_dict))
    
    if latitude and longitude:
        response_list.sort(key=lambda x: x.distance_km or 999)
    
    return response_list


@router.get("/libraries/geojson", response_model=GeoJSONResponse)
async def get_libraries_geojson(db: AsyncSession = Depends(get_db)):
    """Kütüphaneleri GeoJSON formatında getir"""
    result = await db.execute(select(Library).where(Library.is_active == True))
    libraries = result.scalars().all()
    
    features = []
    for library in libraries:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": library.id,
                "name": library.name,
                "library_type": library.library_type,
                "has_wifi": library.has_wifi,
                "opening_hours": library.opening_hours,
                "phone": library.phone,
                "type": "library"
            },
            geometry={
                "type": "Point",
                "coordinates": [library.longitude, library.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


# ============================================
# PARK ENDPOİNT'LERİ
# ============================================

@router.get("/parks", response_model=List[ParkResponse])
async def list_parks(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(5.0),
    has_playground: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Parkları listele
    """
    query = select(Park).where(Park.is_active == True)
    
    if has_playground is not None:
        query = query.where(Park.has_playground == has_playground)
    
    query = query.limit(limit)
    result = await db.execute(query)
    parks = result.scalars().all()
    
    response_list = []
    for park in parks:
        park_dict = ParkResponse.model_validate(park).model_dump()
        
        if latitude and longitude:
            distance = geodesic(
                (latitude, longitude),
                (park.latitude, park.longitude)
            ).kilometers
            park_dict["distance_km"] = round(distance, 2)
            
            if distance > radius_km:
                continue
        
        response_list.append(ParkResponse(**park_dict))
    
    if latitude and longitude:
        response_list.sort(key=lambda x: x.distance_km or 999)
    
    return response_list


@router.get("/parks/geojson", response_model=GeoJSONResponse)
async def get_parks_geojson(db: AsyncSession = Depends(get_db)):
    """Parkları GeoJSON formatında getir"""
    result = await db.execute(select(Park).where(Park.is_active == True))
    parks = result.scalars().all()
    
    features = []
    for park in parks:
        feature = GeoJSONFeature(
            type="Feature",
            properties={
                "id": park.id,
                "name": park.name,
                "park_type": park.park_type,
                "has_playground": park.has_playground,
                "has_sports_area": park.has_sports_area,
                "type": "park"
            },
            geometry={
                "type": "Point",
                "coordinates": [park.longitude, park.latitude]
            }
        )
        features.append(feature)
    
    return GeoJSONResponse(type="FeatureCollection", features=features)


# ============================================
# ARAMA ENDPOİNT'İ
# ============================================

@router.get("/search")
async def search_locations(
    query: str = Query(..., min_length=2, description="Arama sorgusu"),
    latitude: float = Query(..., description="Kullanıcı enlemi"),
    longitude: float = Query(..., description="Kullanıcı boylamı"),
    location_type: Optional[str] = Query(None, description="hospital, pharmacy, library, park"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Lokasyon arama - İsme göre arama yaparak en yakın sonuçları döndür
    
    Örnek: "Nilüfer Halk Kütüphanesi", "Bursa Devlet Hastanesi"
    """
    results = []
    search_term = f"%{query.lower()}%"
    
    # Hastaneler
    if location_type is None or location_type == "hospital":
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.name.ilike(search_term)).limit(limit)
        )
        for h in hospital_result.scalars().all():
            distance = geodesic((latitude, longitude), (h.latitude, h.longitude)).kilometers
            results.append({
                "id": h.id,
                "name": h.name,
                "type": "hospital",
                "latitude": h.latitude,
                "longitude": h.longitude,
                "address": h.address,
                "phone": h.phone,
                "distance_km": round(distance, 2),
                "icon": "🏥"
            })
    
    # Eczaneler
    if location_type is None or location_type == "pharmacy":
        pharmacy_result = await db.execute(
            select(Pharmacy).where(Pharmacy.name.ilike(search_term)).limit(limit)
        )
        for p in pharmacy_result.scalars().all():
            distance = geodesic((latitude, longitude), (p.latitude, p.longitude)).kilometers
            results.append({
                "id": p.id,
                "name": p.name,
                "type": "pharmacy",
                "latitude": p.latitude,
                "longitude": p.longitude,
                "address": p.address,
                "phone": p.phone,
                "distance_km": round(distance, 2),
                "is_on_duty": p.is_on_duty,
                "icon": "💊"
            })
    
    # Kütüphaneler
    if location_type is None or location_type == "library":
        library_result = await db.execute(
            select(Library).where(
                Library.is_active == True,
                Library.name.ilike(search_term)
            ).limit(limit)
        )
        for l in library_result.scalars().all():
            distance = geodesic((latitude, longitude), (l.latitude, l.longitude)).kilometers
            results.append({
                "id": l.id,
                "name": l.name,
                "type": "library",
                "latitude": l.latitude,
                "longitude": l.longitude,
                "address": l.address,
                "phone": l.phone,
                "distance_km": round(distance, 2),
                "has_wifi": l.has_wifi,
                "icon": "📚"
            })
    
    # Parklar
    if location_type is None or location_type == "park":
        park_result = await db.execute(
            select(Park).where(
                Park.is_active == True,
                Park.name.ilike(search_term)
            ).limit(limit)
        )
        for p in park_result.scalars().all():
            distance = geodesic((latitude, longitude), (p.latitude, p.longitude)).kilometers
            results.append({
                "id": p.id,
                "name": p.name,
                "type": "park",
                "latitude": p.latitude,
                "longitude": p.longitude,
                "address": p.address,
                "distance_km": round(distance, 2),
                "has_playground": p.has_playground,
                "icon": "🌳"
            })
    
    # Mesafeye göre sırala
    results.sort(key=lambda x: x["distance_km"])
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results[:limit]
    }


# ============================================
# OSRM ROTA HESAPLAMA ENDPOİNT'LERİ
# ============================================

@router.post("/route/night-mode")
async def calculate_night_mode_route(
    request: RouteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    🌙 Gece Modu Routing - Aydınlık yolları tercih eden rota
    
    İki nokta arasında gece modu rotası hesaplar.
    Karanlık yolları tercih etmek yerine aydınlık yolları tercih eder.
    """
    from app.services.osrm_service import RoutePoint
    from app.services.night_mode_routing import NightModeRoutingService
    
    start = RoutePoint(latitude=request.start_latitude, longitude=request.start_longitude, name="Başlangıç")
    end = RoutePoint(latitude=request.end_latitude, longitude=request.end_longitude, name="Bitiş")
    
    profile = request.profile or "walking"
    
    night_service = NightModeRoutingService(db)
    result = await night_service.get_night_mode_route(start, end, profile=profile)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gece modu rotası hesaplanamadı"
        )
    
    return result


@router.post("/route")
async def calculate_route(request: RouteRequest):
    """
    İki nokta arasında rota hesapla (OSRM)
    
    Gerçek yol ağı üzerinden mesafe ve süre hesaplar.
    Kuş uçuşu değil!
    """
    start = RoutePoint(
        latitude=request.start_latitude,
        longitude=request.start_longitude,
        name="Başlangıç"
    )
    end = RoutePoint(
        latitude=request.end_latitude,
        longitude=request.end_longitude,
        name="Hedef"
    )
    
    route = await osrm_service.get_route(start, end, profile=request.profile)
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rota hesaplanamadı. Lütfen koordinatları kontrol edin."
        )
    
    return {
        "found": True,
        "distance_km": route.distance_km,
        "duration_min": route.duration_min,
        "geometry": route.geometry,
        "steps": route.steps,
        "profile": request.profile
    }


@router.post("/nearest-with-route")
async def find_nearest_with_route(
    request: NearestLocationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    En yakın lokasyonu bul ve rota hesapla
    
    Kullanıcının konumundan en yakın hastane/eczane/kütüphane/park'ı
    bulur ve gerçek yol rotasını hesaplar.
    """
    # Lokasyon türüne göre veritabanından çek
    if request.location_type == "hospital":
        result = await db.execute(select(Hospital))
        locations = result.scalars().all()
        icon = "🏥"
    elif request.location_type == "pharmacy":
        result = await db.execute(select(Pharmacy))
        locations = result.scalars().all()
        icon = "💊"
    elif request.location_type == "library":
        result = await db.execute(select(Library).where(Library.is_active == True))
        locations = result.scalars().all()
        icon = "📚"
    elif request.location_type == "park":
        result = await db.execute(select(Park).where(Park.is_active == True))
        locations = result.scalars().all()
        icon = "🌳"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz lokasyon türü. hospital, pharmacy, library, park olmalı."
        )
    
    if not locations:
        return {
            "location_type": request.location_type,
            "results": [],
            "message": "Bu türde lokasyon bulunamadı"
        }
    
    # RoutePoint listesi oluştur
    user_location = RoutePoint(
        latitude=request.latitude,
        longitude=request.longitude,
        name="Konumunuz"
    )
    
    destinations = [
        RoutePoint(
            latitude=loc.latitude,
            longitude=loc.longitude,
            name=loc.name
        )
        for loc in locations
    ]
    
    # OSRM ile en yakın lokasyonları ve rotalarını bul
    nearest_results = await osrm_service.get_nearest_with_route(
        user_location=user_location,
        destinations=destinations,
        profile=request.profile,
        top_n=request.limit
    )
    
    # Lokasyon detaylarını ekle
    for result in nearest_results:
        dest_name = result["destination"]["name"]
        for loc in locations:
            if loc.name == dest_name:
                result["destination"]["id"] = loc.id
                result["destination"]["address"] = getattr(loc, "address", None)
                result["destination"]["phone"] = getattr(loc, "phone", None)
                result["destination"]["icon"] = icon
                break
    
    return {
        "location_type": request.location_type,
        "profile": request.profile,
        "user_location": {
            "latitude": request.latitude,
            "longitude": request.longitude
        },
        "results": nearest_results
    }


@router.get("/navigate/{location_type}/{location_id}")
async def navigate_to_location(
    location_type: str,
    location_id: int,
    latitude: float = Query(..., description="Kullanıcı enlemi"),
    longitude: float = Query(..., description="Kullanıcı boylamı"),
    profile: str = Query("driving", description="driving, walking, cycling"),
    night_mode: bool = Query(False, description="Gece modu: Aydınlık yolları tercih et"),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir lokasyona navigasyon rotası
    
    Haritada bir lokasyona tıklandığında rota hesaplar.
    Gece modu aktifse, aydınlık yolları tercih eder.
    """
    from app.services.night_mode_routing import NightModeRoutingService
    
    # Lokasyonu bul
    if location_type == "hospital":
        result = await db.execute(select(Hospital).where(Hospital.id == location_id))
        location = result.scalar_one_or_none()
        icon = "🏥"
    elif location_type == "pharmacy":
        result = await db.execute(select(Pharmacy).where(Pharmacy.id == location_id))
        location = result.scalar_one_or_none()
        icon = "💊"
    elif location_type == "library":
        result = await db.execute(select(Library).where(Library.id == location_id))
        location = result.scalar_one_or_none()
        icon = "📚"
    elif location_type == "park":
        result = await db.execute(select(Park).where(Park.id == location_id))
        location = result.scalar_one_or_none()
        icon = "🌳"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz lokasyon türü"
        )
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lokasyon bulunamadı"
        )
    
    # Başlangıç ve bitiş noktaları
    start = RoutePoint(latitude=latitude, longitude=longitude, name="Konumunuz")
    end = RoutePoint(latitude=location.latitude, longitude=location.longitude, name=location.name)
    
    # Gece modu aktifse
    if night_mode:
        night_service = NightModeRoutingService(db)
        result = await night_service.get_night_mode_route(start, end, profile=profile)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gece modu rotası hesaplanamadı"
            )
        
        return {
            "location": {
                "id": location.id,
                "name": location.name,
                "type": location_type,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "icon": icon
            },
            "night_mode": True,
            "route": result["route"],
            "lighting_analysis": result["lighting_analysis"]
        }
    
    # Normal mod (en kısa yol)
    route = await osrm_service.get_route(start, end, profile=profile)
    
    if not route:
        # Fallback: Kuş uçuşu mesafe
        distance = geodesic((latitude, longitude), (location.latitude, location.longitude)).kilometers
        return {
            "found": False,
            "fallback": True,
            "night_mode": False,
            "destination": {
                "id": location.id,
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "icon": icon
            },
            "distance_km": round(distance, 2),
            "message": "OSRM rotası hesaplanamadı, kuş uçuşu mesafe gösteriliyor"
        }
    
    return {
        "found": True,
        "night_mode": False,
        "destination": {
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "address": getattr(location, "address", None),
            "phone": getattr(location, "phone", None),
            "icon": icon
        },
        "distance_km": route.distance_km,
        "duration_min": route.duration_min,
        "geometry": route.geometry,
        "steps": route.steps,
        "profile": profile
    }

