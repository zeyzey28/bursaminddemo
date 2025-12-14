"""
Gölge Verilerini GeoJSON'dan Yükle
road_building_intersection.geojson ve statistics.geojson dosyalarından gölge verilerini yükler
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.road_shadow import RoadShadow
from pyproj import Transformer

# EPSG:3857'den WGS84'e dönüştürücü
transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


async def load_shadow_from_road_building_intersection(geojson_path: Path):
    """road_building_intersection.geojson'dan gölge verilerini yükle"""
    if not geojson_path.exists():
        print(f"❌ GeoJSON bulunamadı: {geojson_path}")
        return
    
    async with AsyncSessionLocal() as session:
        # Mevcut veriyi temizle
        await session.execute(text("TRUNCATE road_shadows RESTART IDENTITY"))
        await session.commit()
        
        count = 0
        
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            
            if not geom or geom.get("type") != "LineString":
                continue
            
            coordinates = geom.get("coordinates", [])
            if not coordinates:
                continue
            
            # İlk ve son koordinatların ortalamasını al (merkez nokta)
            if len(coordinates) > 0:
                # EPSG:3857'den WGS84'e dönüştür
                lon_3857, lat_3857 = coordinates[len(coordinates) // 2]  # Orta nokta
                lon_4326, lat_4326 = transformer.transform(lon_3857, lat_3857)
            else:
                continue
            
            # Gölge skorunu hesapla (properties'den)
            # Eğer shade_percentage varsa kullan, yoksa varsayılan değer
            shade_percentage = props.get("shade_percentage") or props.get("shade") or 0.0
            shade_score = shade_percentage / 100.0 if shade_percentage > 1 else shade_percentage
            shade_score = max(0.0, min(1.0, shade_score))  # Clamp to 0-1
            
            # Road ID veya segment ID
            road_id = props.get("road_id") or props.get("id")
            segment_id = props.get("segment_id")
            
            shadow = RoadShadow(
                segment_id=segment_id,
                road_id=road_id,
                latitude=lat_4326,
                longitude=lon_4326,
                shade_score=shade_score,
                shade_percentage=shade_percentage if shade_percentage > 1 else shade_percentage * 100,
                shade_mean=None,
                shade_max=None,
                shade_min=None,
                geometry=json.dumps(geom) if geom else None
            )
            
            session.add(shadow)
            count += 1
            
            # Her 1000 kayıtta bir commit
            if count % 1000 == 0:
                await session.commit()
                print(f"  ✓ {count} gölge kaydı yüklendi...")
        
        await session.commit()
        print(f"✅ {count} gölge kaydı yüklendi (road_building_intersection)")


async def load_shadow_from_statistics(geojson_path: Path):
    """statistics.geojson'dan istatistik verilerini yükle ve mevcut kayıtları güncelle"""
    if not geojson_path.exists():
        print(f"❌ GeoJSON bulunamadı: {geojson_path}")
        return
    
    async with AsyncSessionLocal() as session:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated_count = 0
        
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            road_id = props.get("id")
            
            if not road_id:
                continue
            
            # İstatistikleri al
            shade_mean = props.get("mean")
            shade_max = props.get("max")
            shade_min = props.get("min")
            
            # Bu road_id'ye sahip kayıtları güncelle
            result = await session.execute(
                select(RoadShadow).where(RoadShadow.road_id == road_id)
            )
            shadows = result.scalars().all()
            
            for shadow in shadows:
                if shade_mean is not None:
                    shadow.shade_mean = shade_mean
                if shade_max is not None:
                    shadow.shade_max = shade_max
                if shade_min is not None:
                    shadow.shade_min = shade_min
                
                # Eğer shade_score yoksa, mean'den hesapla
                if shadow.shade_score == 0.0 and shade_mean is not None:
                    shadow.shade_score = max(0.0, min(1.0, shade_mean))
                    shadow.shade_percentage = shade_mean * 100 if shade_mean <= 1 else shade_mean
                
                updated_count += 1
            
            # Her 100 kayıtta bir commit
            if updated_count % 100 == 0:
                await session.commit()
                print(f"  ✓ {updated_count} kayıt güncellendi...")
        
        await session.commit()
        print(f"✅ {updated_count} gölge kaydı güncellendi (statistics)")


async def main():
    """Ana fonksiyon"""
    road_building_path = Path("/Users/zeynepogulcan/Desktop/golgeli_yol/road_building_intersection.geojson")
    statistics_path = Path("/Users/zeynepogulcan/Desktop/golgeli_yol/statistics.geojson")
    
    print("=" * 50)
    print("🌳 Gölge Verileri Yükleniyor...")
    print("=" * 50)
    
    print("\n📊 Road Building Intersection yükleniyor...")
    await load_shadow_from_road_building_intersection(road_building_path)
    
    print("\n📈 Statistics güncelleniyor...")
    await load_shadow_from_statistics(statistics_path)
    
    print("=" * 50)
    print("✅ Tüm gölge verileri başarıyla yüklendi!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

