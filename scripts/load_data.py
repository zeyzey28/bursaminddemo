"""
Veri Yükleme Script'i
GeoJSON dosyalarından veritabanına veri yükler
"""
import asyncio
import sys
import os
from pathlib import Path

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geojson_loader import GeoJSONLoader
from app.core.database import init_db


async def main():
    """Ana fonksiyon"""
    print("=" * 50)
    print("Bursa Akıllı Şehir - Veri Yükleme")
    print("=" * 50)
    
    # Veritabanını başlat
    print("\n📦 Veritabanı tabloları oluşturuluyor...")
    await init_db()
    print("✓ Veritabanı hazır")
    
    # Veri dosyalarının yolları
    data_dir = Path(__file__).parent.parent / "data"
    
    # Alternatif yollar (Downloads klasörü)
    downloads_dir = Path.home() / "Downloads"
    
    # Hastane verisi
    hospital_paths = [
        data_dir / "hastane.geojson",
        downloads_dir / "hastane.geojson"
    ]
    
    for path in hospital_paths:
        if path.exists():
            print(f"\n🏥 Hastane verileri yükleniyor: {path}")
            count = await GeoJSONLoader.load_hospitals_from_geojson(str(path))
            print(f"✓ {count} hastane yüklendi")
            break
    else:
        print("\n⚠️ Hastane GeoJSON dosyası bulunamadı")
    
    # Eczane verisi
    pharmacy_paths = [
        data_dir / "eczane.geojson",
        downloads_dir / "eczane.geojson"
    ]
    
    for path in pharmacy_paths:
        if path.exists():
            print(f"\n💊 Eczane verileri yükleniyor: {path}")
            count = await GeoJSONLoader.load_pharmacies_from_geojson(str(path))
            print(f"✓ {count} eczane yüklendi")
            break
    else:
        print("\n⚠️ Eczane GeoJSON dosyası bulunamadı")
    
    print("\n" + "=" * 50)
    print("Veri yükleme tamamlandı!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

