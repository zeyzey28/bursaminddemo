"""
Bursa Naim Süleymanoğlu Bulvarı Veri Yükleme Script'i

Bu script GeoJSON dosyalarından verileri veritabanına yükler:
- Eczaneler
- Toplanma Alanları (Afet)
- Yollar (Highway)
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime


# Proje root'una göre import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models.location import Pharmacy, Road
from app.models.disaster import SafeRoute

# Timeout'u artırılmış engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_timeout=60,
    connect_args={"timeout": 60}
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

DATA_DIR = Path(__file__).parent.parent / "data" / "geojson"


async def load_pharmacies():
    """Eczaneleri yükle"""
    file_path = DATA_DIR / "eczane_in_buffer.geojson"
    
    if not file_path.exists():
        print(f"❌ Dosya bulunamadı: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    async with AsyncSessionLocal() as db:
        count = 0
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            
            if not coords or len(coords) < 2:
                continue
            
            # Zaten var mı kontrol et
            existing = await db.execute(
                select(Pharmacy).where(Pharmacy.name == props.get("eczane"))
            )
            if existing.scalar_one_or_none():
                continue
            
            pharmacy = Pharmacy(
                name=props.get("eczane") or props.get("adi"),
                latitude=float(props.get("latitude") or coords[1]),
                longitude=float(props.get("longitude") or coords[0]),
                address=props.get("adres"),
                phone=props.get("telefon1"),
                is_on_duty=False,  # Varsayılan
                osm_id=f"bursa_{count}"
            )
            db.add(pharmacy)
            count += 1
        
        await db.commit()
        print(f"✅ {count} eczane yüklendi")


async def load_safe_zones():
    """Afet toplanma alanlarını yükle"""
    file_path = DATA_DIR / "toplanma_alanı_in_buffer_centroid.geojson"
    
    if not file_path.exists():
        print(f"❌ Dosya bulunamadı: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    async with AsyncSessionLocal() as db:
        count = 0
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            
            if not coords or len(coords) < 2:
                continue
            
            # Zaten var mı kontrol et
            existing = await db.execute(
                select(SafeRoute).where(SafeRoute.name == props.get("ad"))
            )
            if existing.scalar_one_or_none():
                continue
            
            safe_zone = SafeRoute(
                name=props.get("ad"),
                route_type="safe_zone",
                start_latitude=float(coords[1]),
                start_longitude=float(coords[0]),
                end_latitude=float(coords[1]),  # Nokta olduğu için aynı
                end_longitude=float(coords[0]),
                description=f"{props.get('mahalle', '')} Mahallesi - {props.get('ilce', 'NİLÜFER')}",
                is_active=True,
                capacity=500,  # Varsayılan kapasite
                coordinates=json.dumps([[coords[0], coords[1]]])
            )
            db.add(safe_zone)
            count += 1
        
        await db.commit()
        print(f"✅ {count} toplanma alanı yüklendi")


async def load_roads():
    """Naim Süleymanoğlu Bulvarı yollarını yükle"""
    file_path = DATA_DIR / "naim_suleymanoglu_highway.geojson"
    
    if not file_path.exists():
        print(f"❌ Dosya bulunamadı: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    async with AsyncSessionLocal() as db:
        count = 0
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            
            if geom.get("type") != "LineString":
                continue
            
            osm_id = props.get("osm_id")
            
            # Zaten var mı kontrol et
            existing = await db.execute(
                select(Road).where(Road.osm_id == osm_id)
            )
            if existing.scalar_one_or_none():
                continue
            
            road = Road(
                osm_id=osm_id,
                name=props.get("name", "Naim Süleymanoğlu Bulvarı"),
                road_type=props.get("highway", "secondary"),
                coordinates=json.dumps(geom.get("coordinates", [])),
                max_speed=int(props.get("maxspeed")) if props.get("maxspeed") else 50,
                is_blocked=False
            )
            db.add(road)
            count += 1
        
        await db.commit()
        print(f"✅ {count} yol segmenti yüklendi")


async def load_all_data():
    """Tüm verileri yükle"""
    print("=" * 50)
    print("🚀 Bursa Naim Süleymanoğlu Bulvarı Verileri Yükleniyor...")
    print("=" * 50)
    
    await load_pharmacies()
    await load_safe_zones()
    await load_roads()
    
    print("=" * 50)
    print("✅ Tüm veriler başarıyla yüklendi!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(load_all_data())

