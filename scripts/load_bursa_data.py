"""
Bursa Naim Süleymanoğlu Bulvarı Veri Yükleme Script'i

Bu script GeoJSON dosyalarından verileri veritabanına yükler:
- Eczaneler
- Yollar (Highway)
- Trafik tahmini (2 saat) CSV
"""
import json
import asyncio
import csv
from pathlib import Path
from datetime import datetime


# Proje root'una göre import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models.location import Pharmacy, Road
from app.models.traffic_risk import TrafficForecast

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


async def load_signal_forecasts_from_csv(csv_path: Path):
    """2 saatlik trafik tahminlerini CSV'den yükle"""
    if not csv_path.exists():
        print(f"❌ CSV bulunamadı: {csv_path}")
        return
    
    async with AsyncSessionLocal() as db:
        # Mevcut veriyi temizle
        await db.execute(text("TRUNCATE traffic_forecasts RESTART IDENTITY"))
        await db.commit()
        
        count = 0
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_str = row.get("timestamp")
                try:
                    ts = datetime.fromisoformat(ts_str)
                except Exception:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                
                forecast = TrafficForecast(
                    signal_id=int(row["signal_id"]) if row.get("signal_id") else None,
                    segment_id=None,
                    timestamp=ts,
                    vehicle_count=float(row["vehicle_count"]) if row.get("vehicle_count") else None,
                    traffic_density=float(row["traffic_density"]),
                    expected_2h=float(row["expected_2h"])
                )
                db.add(forecast)
                count += 1
            
            await db.commit()
            print(f"✅ {count} trafik tahmin kaydı yüklendi (2h)")


async def load_all_data():
    """Tüm verileri yükle"""
    print("=" * 50)
    print("🚀 Bursa Naim Süleymanoğlu Bulvarı Verileri Yükleniyor...")
    print("=" * 50)
    
    await load_pharmacies()
    await load_roads()
    await load_signal_forecasts_from_csv(
        Path("/Users/zeynepogulcan/Desktop/cagri_son/signal_forecast_2h.csv")
    )
    
    print("=" * 50)
    print("✅ Tüm veriler başarıyla yüklendi!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(load_all_data())

