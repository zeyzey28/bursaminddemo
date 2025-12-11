"""
GeoJSON Veri Yükleme Servisi
Hastane, Eczane ve diğer konum verilerini GeoJSON dosyalarından yükler
"""
import json
from typing import List, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.location import Hospital, Pharmacy
from app.core.database import AsyncSessionLocal


class GeoJSONLoader:
    """GeoJSON dosyalarından veri yükleyici"""
    
    @staticmethod
    async def load_hospitals_from_geojson(file_path: str) -> int:
        """
        Hastane verilerini GeoJSON dosyasından yükle
        
        Args:
            file_path: GeoJSON dosya yolu
            
        Returns:
            Yüklenen hastane sayısı
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        loaded_count = 0
        
        async with AsyncSessionLocal() as session:
            for feature in features:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                # Koordinatları al
                coordinates = geometry.get('coordinates', [])
                if len(coordinates) < 2:
                    continue
                
                longitude, latitude = coordinates[0], coordinates[1]
                
                # OSM ID
                osm_id = properties.get('@id', properties.get('id', ''))
                
                # Mevcut kaydı kontrol et
                existing = await session.execute(
                    select(Hospital).where(Hospital.osm_id == osm_id)
                )
                if existing.scalar_one_or_none():
                    continue
                
                # Hastane oluştur
                hospital = Hospital(
                    osm_id=osm_id,
                    name=properties.get('name', 'İsimsiz Hastane'),
                    latitude=latitude,
                    longitude=longitude,
                    phone=properties.get('phone'),
                    website=properties.get('website'),
                    has_emergency=properties.get('emergency') == 'yes',
                    speciality=properties.get('healthcare:speciality'),
                    operator=properties.get('operator')
                )
                
                # Adres bilgisi varsa ekle
                addr_parts = []
                if properties.get('addr:street'):
                    addr_parts.append(properties.get('addr:street'))
                if properties.get('addr:housenumber'):
                    addr_parts.append(properties.get('addr:housenumber'))
                if properties.get('addr:neighbourhood'):
                    addr_parts.append(properties.get('addr:neighbourhood'))
                if properties.get('addr:district'):
                    addr_parts.append(properties.get('addr:district'))
                if properties.get('addr:city'):
                    addr_parts.append(properties.get('addr:city'))
                
                if addr_parts:
                    hospital.address = ', '.join(addr_parts)
                
                session.add(hospital)
                loaded_count += 1
            
            await session.commit()
        
        return loaded_count
    
    @staticmethod
    async def load_pharmacies_from_geojson(file_path: str) -> int:
        """
        Eczane verilerini GeoJSON dosyasından yükle
        
        Args:
            file_path: GeoJSON dosya yolu
            
        Returns:
            Yüklenen eczane sayısı
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        loaded_count = 0
        
        async with AsyncSessionLocal() as session:
            for feature in features:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                coordinates = geometry.get('coordinates', [])
                if len(coordinates) < 2:
                    continue
                
                longitude, latitude = coordinates[0], coordinates[1]
                osm_id = properties.get('@id', properties.get('id', ''))
                
                # Mevcut kaydı kontrol et
                existing = await session.execute(
                    select(Pharmacy).where(Pharmacy.osm_id == osm_id)
                )
                if existing.scalar_one_or_none():
                    continue
                
                # Eczane oluştur
                pharmacy = Pharmacy(
                    osm_id=osm_id,
                    name=properties.get('name', 'İsimsiz Eczane'),
                    latitude=latitude,
                    longitude=longitude,
                    phone=properties.get('phone')
                )
                
                session.add(pharmacy)
                loaded_count += 1
            
            await session.commit()
        
        return loaded_count
    
    @staticmethod
    def parse_geojson_to_dict(file_path: str) -> dict:
        """
        GeoJSON dosyasını dict olarak oku (frontend'e direkt gönderim için)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def get_bounds_from_geojson(file_path: str) -> dict:
        """
        GeoJSON dosyasından sınır koordinatlarını hesapla
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        
        min_lat, max_lat = float('inf'), float('-inf')
        min_lon, max_lon = float('inf'), float('-inf')
        
        for feature in features:
            geometry = feature.get('geometry', {})
            geom_type = geometry.get('type')
            coordinates = geometry.get('coordinates', [])
            
            if geom_type == 'Point':
                lon, lat = coordinates
                min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
                min_lon, max_lon = min(min_lon, lon), max(max_lon, lon)
            elif geom_type in ['LineString', 'MultiPoint']:
                for coord in coordinates:
                    lon, lat = coord
                    min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
                    min_lon, max_lon = min(min_lon, lon), max(max_lon, lon)
            elif geom_type == 'Polygon':
                for ring in coordinates:
                    for coord in ring:
                        lon, lat = coord
                        min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
                        min_lon, max_lon = min(min_lon, lon), max(max_lon, lon)
            elif geom_type == 'MultiPolygon':
                for polygon in coordinates:
                    for ring in polygon:
                        for coord in ring:
                            lon, lat = coord
                            min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
                            min_lon, max_lon = min(min_lon, lon), max(max_lon, lon)
        
        return {
            "min_latitude": min_lat,
            "max_latitude": max_lat,
            "min_longitude": min_lon,
            "max_longitude": max_lon,
            "center_latitude": (min_lat + max_lat) / 2,
            "center_longitude": (min_lon + max_lon) / 2
        }


# CLI için yardımcı fonksiyonlar
async def load_all_data(hospitals_path: str = None, pharmacies_path: str = None):
    """
    Tüm GeoJSON verilerini yükle
    """
    results = {}
    
    if hospitals_path:
        count = await GeoJSONLoader.load_hospitals_from_geojson(hospitals_path)
        results['hospitals'] = count
        print(f"✓ {count} hastane yüklendi")
    
    if pharmacies_path:
        count = await GeoJSONLoader.load_pharmacies_from_geojson(pharmacies_path)
        results['pharmacies'] = count
        print(f"✓ {count} eczane yüklendi")
    
    return results


if __name__ == "__main__":
    import asyncio
    
    # Örnek kullanım
    asyncio.run(load_all_data(
        hospitals_path="data/hastane.geojson",
        pharmacies_path="data/eczane.geojson"
    ))

