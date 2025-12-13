"""
OSRM Routing Servisi

Open Source Routing Machine kullanarak gerçek yol hesaplama.
Kuş uçuşu değil, gerçek yol ağı üzerinden rota hesaplar.

OSRM Public API: https://router.project-osrm.org
"""
import httpx
from typing import List, Tuple, Optional
from dataclasses import dataclass
from geopy.distance import geodesic


@dataclass
class RoutePoint:
    """Rota noktası"""
    latitude: float
    longitude: float
    name: Optional[str] = None


@dataclass
class OSRMRoute:
    """OSRM rota sonucu"""
    distance_km: float
    duration_min: float
    geometry: dict  # GeoJSON LineString
    waypoints: List[dict]
    steps: List[dict]  # Yol tarifleri


class OSRMService:
    """
    OSRM Routing Servisi
    
    Bursa için gerçek yol hesaplama yapar.
    Public OSRM API kullanır (ücretsiz).
    """
    
    def __init__(self, base_url: str = "https://router.project-osrm.org"):
        self.base_url = base_url
        self.profile = "driving"  # driving, walking, cycling
    
    async def get_route(
        self,
        start: RoutePoint,
        end: RoutePoint,
        profile: str = "driving",
        alternatives: bool = False
    ) -> Optional[OSRMRoute]:
        """
        İki nokta arasında rota hesapla
        
        Args:
            start: Başlangıç noktası
            end: Bitiş noktası
            profile: Ulaşım türü (driving, walking, cycling)
            alternatives: Alternatif rotalar göster
            
        Returns:
            OSRMRoute veya None
        """
        # OSRM koordinat formatı: longitude,latitude
        coordinates = f"{start.longitude},{start.latitude};{end.longitude},{end.latitude}"
        
        url = f"{self.base_url}/route/v1/{profile}/{coordinates}"
        
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "true",
            "alternatives": str(alternatives).lower()
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                
                if data.get("code") != "Ok" or not data.get("routes"):
                    return None
                
                route = data["routes"][0]
                
                # Yol tariflerini çıkar
                steps = []
                if route.get("legs"):
                    for leg in route["legs"]:
                        for step in leg.get("steps", []):
                            steps.append({
                                "instruction": step.get("maneuver", {}).get("instruction", ""),
                                "distance_m": step.get("distance", 0),
                                "duration_s": step.get("duration", 0),
                                "name": step.get("name", ""),
                                "mode": step.get("mode", profile)
                            })
                
                return OSRMRoute(
                    distance_km=round(route["distance"] / 1000, 2),
                    duration_min=round(route["duration"] / 60, 1),
                    geometry=route["geometry"],
                    waypoints=data.get("waypoints", []),
                    steps=steps
                )
                
        except Exception as e:
            print(f"OSRM Error: {e}")
            return None
    
    async def get_walking_route(
        self,
        start: RoutePoint,
        end: RoutePoint
    ) -> Optional[OSRMRoute]:
        """Yürüyüş rotası"""
        return await self.get_route(start, end, profile="foot")
    
    async def get_driving_route(
        self,
        start: RoutePoint,
        end: RoutePoint
    ) -> Optional[OSRMRoute]:
        """Araç rotası"""
        return await self.get_route(start, end, profile="driving")
    
    async def get_cycling_route(
        self,
        start: RoutePoint,
        end: RoutePoint
    ) -> Optional[OSRMRoute]:
        """Bisiklet rotası"""
        return await self.get_route(start, end, profile="cycling")
    
    async def get_nearest_with_route(
        self,
        user_location: RoutePoint,
        destinations: List[RoutePoint],
        profile: str = "driving",
        top_n: int = 3
    ) -> List[dict]:
        """
        En yakın N lokasyonu bul ve rotalarını hesapla
        
        Args:
            user_location: Kullanıcı konumu
            destinations: Hedef lokasyonlar listesi
            profile: Ulaşım türü
            top_n: Kaç sonuç döndürülsün
            
        Returns:
            En yakın lokasyonlar ve rotaları
        """
        # Önce kuş uçuşu mesafeye göre sırala (hız için)
        sorted_destinations = sorted(
            destinations,
            key=lambda d: geodesic(
                (user_location.latitude, user_location.longitude),
                (d.latitude, d.longitude)
            ).kilometers
        )
        
        # İlk N+5 için gerçek rota hesapla (bazıları başarısız olabilir)
        candidates = sorted_destinations[:top_n + 5]
        
        results = []
        for dest in candidates:
            route = await self.get_route(user_location, dest, profile)
            
            if route:
                results.append({
                    "destination": {
                        "latitude": dest.latitude,
                        "longitude": dest.longitude,
                        "name": dest.name
                    },
                    "distance_km": route.distance_km,
                    "duration_min": route.duration_min,
                    "geometry": route.geometry,
                    "steps": route.steps[:5]  # İlk 5 adım
                })
            
            if len(results) >= top_n:
                break
        
        # Mesafeye göre sırala
        results.sort(key=lambda x: x["distance_km"])
        
        return results
    
    async def get_distance_matrix(
        self,
        origins: List[RoutePoint],
        destinations: List[RoutePoint],
        profile: str = "driving"
    ) -> Optional[dict]:
        """
        Mesafe matrisi hesapla (çoklu başlangıç-bitiş)
        
        Çöp toplama rotası optimizasyonu için kullanılır.
        """
        # Tüm koordinatları birleştir
        all_points = origins + destinations
        coords = ";".join([f"{p.longitude},{p.latitude}" for p in all_points])
        
        # Sources ve destinations indeksleri
        sources = ";".join([str(i) for i in range(len(origins))])
        destinations_idx = ";".join([str(i) for i in range(len(origins), len(all_points))])
        
        url = f"{self.base_url}/table/v1/{profile}/{coords}"
        
        params = {
            "sources": sources,
            "destinations": destinations_idx,
            "annotations": "distance,duration"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                
                if data.get("code") != "Ok":
                    return None
                
                return {
                    "distances": data.get("distances", []),  # metre cinsinden
                    "durations": data.get("durations", [])   # saniye cinsinden
                }
                
        except Exception as e:
            print(f"OSRM Table Error: {e}")
            return None


# Singleton instance
osrm_service = OSRMService()

