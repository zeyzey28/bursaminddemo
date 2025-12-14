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
    
    # Dosyaları kontrol et (toplanma alanları kaldırıldı)
    files = [
        ("bulvar_buffer_1km4326.geojson", "1km Buffer Alanı", "polygon"),
        ("bulvar_buffer_1_5_4326.geojson", "1.5km Buffer Alanı", "polygon"),
        ("naim_suleymanoglu_highway.geojson", "Naim Süleymanoğlu Bulvarı", "linestring"),
        ("highway_in_1_buffer.geojson", "1km Buffer Yolları", "linestring"),
        ("highway_in_1_5_buffer.geojson", "1.5km Buffer Yolları", "linestring"),
        ("eczane_in_buffer.geojson", "Eczaneler", "point"),
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
    
    Bu endpoint eczane verilerini
    GeoJSON dosyalarından okuyarak veritabanına ekler.
    """
    results = {
        "pharmacies": {"loaded": 0, "skipped": 0, "errors": []}
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
    
    return {
        "success": True,
        "message": "Veriler veritabanına yüklendi",
        "results": results
    }

