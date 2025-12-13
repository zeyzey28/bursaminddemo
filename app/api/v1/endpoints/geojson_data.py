"""
GeoJSON Veri Endpoint'leri

Bursa Naim Süleymanoğlu Bulvarı bölgesi için hazır GeoJSON verileri
"""
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geopy.distance import geodesic

from app.core.database import get_db
from app.models.disaster import AssemblyPoint
from app.models.location import Pharmacy

router = APIRouter()

# Veri dizini
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "geojson"


def load_geojson(filename: str) -> dict:
    """GeoJSON dosyasını yükle"""
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"GeoJSON dosyası bulunamadı: {filename}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================
# BULVAR BUFFER (ÇALIŞMA ALANI)
# ============================================

@router.get("/buffer/1km")
async def get_buffer_1km():
    """
    Naim Süleymanoğlu Bulvarı 1km buffer alanı
    """
    return load_geojson("bulvar_buffer_1km4326.geojson")


@router.get("/buffer/1.5km")
async def get_buffer_1_5km():
    """
    Naim Süleymanoğlu Bulvarı 1.5km buffer alanı
    """
    return load_geojson("bulvar_buffer_1_5_4326.geojson")


# ============================================
# YOLLAR (HIGHWAY)
# ============================================

@router.get("/roads/naim-suleymanoglu")
async def get_naim_suleymanoglu_highway():
    """
    Naim Süleymanoğlu Bulvarı yol verileri
    """
    return load_geojson("naim_suleymanoglu_highway.geojson")


@router.get("/roads/in-buffer")
async def get_roads_in_buffer(
    buffer_km: float = Query(1.5, description="Buffer mesafesi (1 veya 1.5)")
):
    """
    Buffer alanı içindeki yollar
    """
    if buffer_km <= 1.0:
        return load_geojson("highway_in_1_buffer.geojson")
    else:
        return load_geojson("highway_in_1_5_buffer.geojson")


# ============================================
# ECZANELER
# ============================================

@router.get("/pharmacies/in-buffer")
async def get_pharmacies_in_buffer():
    """
    Buffer alanı içindeki eczaneler (GeoJSON)
    """
    return load_geojson("eczane_in_buffer.geojson")


@router.get("/pharmacies/list")
async def get_pharmacies_list():
    """
    Buffer alanı içindeki eczaneler (Liste formatında)
    """
    data = load_geojson("eczane_in_buffer.geojson")
    
    pharmacies = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        
        pharmacies.append({
            "name": props.get("eczane") or props.get("adi"),
            "address": props.get("adres"),
            "address_description": props.get("adresTarif"),
            "phone1": props.get("telefon1"),
            "phone2": props.get("telefon2"),
            "district": props.get("ilce"),
            "neighborhood": props.get("mahalle"),
            "latitude": float(props.get("latitude") or coords[1]) if coords else None,
            "longitude": float(props.get("longitude") or coords[0]) if coords else None
        })
    
    return {
        "total": len(pharmacies),
        "pharmacies": pharmacies
    }


# ============================================
# TOPLANMA ALANLARI
# ============================================

@router.get("/assembly-points/in-buffer")
async def get_assembly_points_in_buffer():
    """
    Buffer alanı içindeki afet toplanma alanları (GeoJSON)
    """
    return load_geojson("toplanma_alanı_in_buffer_centroid.geojson")


@router.get("/assembly-points/all")
async def get_all_assembly_points():
    """
    Tüm afet toplanma alanları (GeoJSON)
    """
    try:
        return load_geojson("toplanma_alanı_centroid.geojson")
    except:
        return load_geojson("toplanma_alanı_in_buffer_centroid.geojson")


@router.get("/assembly-points/list")
async def get_assembly_points_list():
    """
    Buffer alanı içindeki toplanma alanları (Liste formatında)
    """
    data = load_geojson("toplanma_alanı_in_buffer_centroid.geojson")
    
    points = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        
        points.append({
            "id": props.get("id"),
            "name": props.get("ad"),
            "city": props.get("il"),
            "district": props.get("ilce"),
            "neighborhood": props.get("mahalle"),
            "latitude": float(props.get("lat") or coords[1]) if coords else None,
            "longitude": float(props.get("lon") or coords[0]) if coords else None
        })
    
    return {
        "total": len(points),
        "assembly_points": points
    }


@router.get("/assembly-points/nearest")
async def find_nearest_assembly_point(
    latitude: float = Query(..., description="Kullanıcı enlemi"),
    longitude: float = Query(..., description="Kullanıcı boylamı"),
    limit: int = Query(5, ge=1, le=20)
):
    """
    En yakın toplanma alanlarını bul
    """
    data = load_geojson("toplanma_alanı_in_buffer_centroid.geojson")
    
    points = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        
        if not coords or len(coords) < 2:
            continue
        
        point_lat = float(props.get("lat") or coords[1])
        point_lon = float(props.get("lon") or coords[0])
        
        distance = geodesic(
            (latitude, longitude),
            (point_lat, point_lon)
        ).kilometers
        
        points.append({
            "id": props.get("id"),
            "name": props.get("ad"),
            "district": props.get("ilce"),
            "neighborhood": props.get("mahalle"),
            "latitude": point_lat,
            "longitude": point_lon,
            "distance_km": round(distance, 2)
        })
    
    # Mesafeye göre sırala
    points.sort(key=lambda x: x["distance_km"])
    
    return {
        "user_location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "nearest_points": points[:limit]
    }


# ============================================
# TÜM VERİLER (ÖZET)
# ============================================

@router.get("/summary")
async def get_data_summary():
    """
    Mevcut GeoJSON verilerinin özeti
    """
    summary = {
        "area": "Naim Süleymanoğlu Bulvarı - Bursa/Nilüfer",
        "datasets": []
    }
    
    # Dosyaları kontrol et
    files = [
        ("bulvar_buffer_1km4326.geojson", "1km Buffer Alanı", "polygon"),
        ("bulvar_buffer_1_5_4326.geojson", "1.5km Buffer Alanı", "polygon"),
        ("naim_suleymanoglu_highway.geojson", "Naim Süleymanoğlu Bulvarı", "linestring"),
        ("highway_in_1_buffer.geojson", "1km Buffer Yolları", "linestring"),
        ("highway_in_1_5_buffer.geojson", "1.5km Buffer Yolları", "linestring"),
        ("eczane_in_buffer.geojson", "Eczaneler", "point"),
        ("toplanma_alanı_in_buffer_centroid.geojson", "Toplanma Alanları", "point"),
    ]
    
    for filename, name, geom_type in files:
        file_path = DATA_DIR / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                feature_count = len(data.get("features", []))
                summary["datasets"].append({
                    "name": name,
                    "file": filename,
                    "geometry_type": geom_type,
                    "feature_count": feature_count,
                    "available": True
                })
            except:
                summary["datasets"].append({
                    "name": name,
                    "file": filename,
                    "available": False,
                    "error": "Dosya okunamadı"
                })
        else:
            summary["datasets"].append({
                "name": name,
                "file": filename,
                "available": False
            })
    
    return summary


# ============================================
# VERİTABANINA YÜKLEME
# ============================================

@router.post("/load-to-database")
async def load_geojson_to_database(
    db: AsyncSession = Depends(get_db)
):
    """
    GeoJSON verilerini veritabanına yükle
    
    Bu endpoint eczane ve toplanma alanı verilerini
    GeoJSON dosyalarından okuyarak veritabanına ekler.
    """
    results = {
        "pharmacies": {"loaded": 0, "skipped": 0, "errors": []},
        "assembly_points": {"loaded": 0, "skipped": 0, "errors": []}
    }
    
    # Eczaneleri yükle
    try:
        pharmacy_data = load_geojson("eczane_in_buffer.geojson")
        for feature in pharmacy_data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            
            if not coords or len(coords) < 2:
                continue
            
            name = props.get("eczane") or props.get("adi")
            
            # Zaten var mı kontrol et
            existing = await db.execute(
                select(Pharmacy).where(Pharmacy.name == name)
            )
            if existing.scalar_one_or_none():
                results["pharmacies"]["skipped"] += 1
                continue
            
            pharmacy = Pharmacy(
                name=name,
                latitude=float(props.get("latitude") or coords[1]),
                longitude=float(props.get("longitude") or coords[0]),
                address=props.get("adres"),
                phone=props.get("telefon1"),
                is_on_duty=False,
                osm_id=f"bursa_eczane_{results['pharmacies']['loaded']}"
            )
            db.add(pharmacy)
            results["pharmacies"]["loaded"] += 1
        
        await db.commit()
    except Exception as e:
        results["pharmacies"]["errors"].append(str(e))
    
    # Toplanma alanlarını yükle
    try:
        assembly_data = load_geojson("toplanma_alanı_in_buffer_centroid.geojson")
        for feature in assembly_data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            
            if not coords or len(coords) < 2:
                continue
            
            name = props.get("ad")
            osm_id = str(props.get("id"))
            
            # Zaten var mı kontrol et
            existing = await db.execute(
                select(AssemblyPoint).where(AssemblyPoint.osm_id == osm_id)
            )
            if existing.scalar_one_or_none():
                results["assembly_points"]["skipped"] += 1
                continue
            
            point = AssemblyPoint(
                name=name,
                osm_id=osm_id,
                latitude=float(props.get("lat") or coords[1]),
                longitude=float(props.get("lon") or coords[0]),
                district=props.get("ilce"),
                neighborhood=props.get("mahalle"),
                is_active=True
            )
            db.add(point)
            results["assembly_points"]["loaded"] += 1
        
        await db.commit()
    except Exception as e:
        results["assembly_points"]["errors"].append(str(e))
    
    return {
        "success": True,
        "message": "Veriler veritabanına yüklendi",
        "results": results
    }

