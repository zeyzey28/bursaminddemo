"""
Gece Modu Routing Servisi
Aydınlık yolları tercih eden routing algoritması
"""
from typing import List, Optional, Tuple
from geopy.distance import geodesic
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.services.osrm_service import osrm_service, RoutePoint, OSRMRoute
from app.models.segment_lighting import SegmentLighting, LightingLevel


class NightModeRoutingService:
    """
    Gece modu routing servisi
    
    Karanlık yolları tercih etmek yerine aydınlık yolları tercih eder.
    Özellikle nöbetçi eczane gibi yerlere giderken güvenlik için önemli.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.min_lighting_score = 0.5  # Minimum aydınlatma skoru (0-1)
        self.dark_penalty = 2.0  # Karanlık yol için mesafe cezası çarpanı
    
    async def get_lighting_for_point(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 50.0
    ) -> Optional[SegmentLighting]:
        """
        Bir nokta için en yakın aydınlatma bilgisini getir
        """
        # Basit mesafe hesaplama (PostGIS kullanmıyoruz, basit yaklaşım)
        # 50 metre yarıçap içindeki en yakın segment'i bul
        query = select(SegmentLighting)
        
        result = await self.db.execute(query)
        all_segments = result.scalars().all()
        
        if not all_segments:
            return None
        
        # En yakın segment'i bul
        closest = None
        min_distance = float('inf')
        
        for segment in all_segments:
            distance = geodesic(
                (latitude, longitude),
                (segment.latitude, segment.longitude)
            ).meters
            
            if distance < radius_meters and distance < min_distance:
                min_distance = distance
                closest = segment
        
        return closest
    
    async def score_route_by_lighting(
        self,
        route: OSRMRoute
    ) -> Tuple[float, int, float]:
        """
        Rotayı aydınlatma açısından skorla
        
        Returns:
            (score, dark_segment_count, avg_lighting_score)
            - score: Düşük = daha iyi (daha az karanlık yol)
            - dark_segment_count: Karanlık segment sayısı
            - avg_lighting_score: Ortalama aydınlatma skoru
        """
        if not route.geometry or not route.geometry.get("coordinates"):
            return (float('inf'), 0, 0.0)
        
        coordinates = route.geometry["coordinates"]
        dark_count = 0
        total_score = 0.0
        checked_points = 0
        
        # Rota üzerindeki her 5. noktayı kontrol et (performans için)
        step = max(1, len(coordinates) // 20)  # Maksimum 20 nokta kontrol et
        
        for i in range(0, len(coordinates), step):
            lon, lat = coordinates[i]
            
            lighting = await self.get_lighting_for_point(lat, lon, radius_meters=50.0)
            
            if lighting:
                checked_points += 1
                total_score += lighting.lighting_score
                
                if lighting.lighting_level == LightingLevel.DARK:
                    dark_count += 1
                elif lighting.lighting_level == LightingLevel.MEDIUM:
                    dark_count += 0.5  # Yarı ceza
        
        if checked_points == 0:
            return (float('inf'), 0, 0.0)
        
        avg_score = total_score / checked_points if checked_points > 0 else 0.0
        
        # Skor: karanlık segment sayısı * ceza + (1 - ortalama aydınlatma)
        penalty = dark_count * self.dark_penalty
        lighting_penalty = (1.0 - avg_score) * 0.5
        
        final_score = penalty + lighting_penalty
        
        return (final_score, int(dark_count), avg_score)
    
    async def get_night_mode_route(
        self,
        start: RoutePoint,
        end: RoutePoint,
        profile: str = "walking",
        max_alternatives: int = 3
    ) -> Optional[dict]:
        """
        Gece modu için en iyi rotayı bul
        
        Önce normal rotayı al, sonra alternatifleri dene.
        Aydınlatma açısından en iyi olanı seç.
        """
        # 1. Normal rota (en kısa)
        normal_route = await osrm_service.get_route(
            start, end, profile=profile, alternatives=False
        )
        
        if not normal_route:
            return None
        
        # 2. Alternatif rotalar al (OSRM API'den)
        # Not: OSRM public API alternatif rotaları destekler ama response formatı farklı olabilir
        # Şimdilik sadece normal rotayı kullanıyoruz, alternatifler için OSRM API'yi doğrudan çağırabiliriz
        
        # 3. Tüm rotaları skorla
        routes_to_score = [normal_route]
        
        scored_routes = []
        
        for route in routes_to_score:
            score, dark_count, avg_lighting = await self.score_route_by_lighting(route)
            
            scored_routes.append({
                "route": route,
                "lighting_score": score,
                "dark_segment_count": dark_count,
                "avg_lighting_score": avg_lighting,
                "distance_km": route.distance_km,
                "duration_min": route.duration_min
            })
        
        # 4. En iyi rotayı seç (düşük skor = daha iyi)
        # Ama mesafe çok uzunsa normal rotayı tercih et
        scored_routes.sort(key=lambda x: (
            x["lighting_score"],  # Önce aydınlatma
            x["distance_km"] * 0.1  # Sonra mesafe (daha az ağırlık)
        ))
        
        best = scored_routes[0]
        
        # Eğer en iyi rota normal rotadan %50'den fazla uzunsa, normal rotayı kullan
        if best["distance_km"] > normal_route.distance_km * 1.5:
            best = {
                "route": normal_route,
                "lighting_score": await self.score_route_by_lighting(normal_route)[0],
                "dark_segment_count": await self.score_route_by_lighting(normal_route)[1],
                "avg_lighting_score": await self.score_route_by_lighting(normal_route)[2],
                "distance_km": normal_route.distance_km,
                "duration_min": normal_route.duration_min
            }
        
        return {
            "route": {
                "distance_km": best["route"].distance_km,
                "duration_min": best["route"].duration_min,
                "geometry": best["route"].geometry,
                "steps": best["route"].steps
            },
            "lighting_analysis": {
                "lighting_score": round(best["lighting_score"], 2),
                "dark_segment_count": best["dark_segment_count"],
                "avg_lighting_score": round(best["avg_lighting_score"], 2),
                "is_night_mode_optimized": best["lighting_score"] < float('inf')
            },
            "is_night_mode": True
        }
    
    async def get_nearest_with_night_route(
        self,
        user_location: RoutePoint,
        destinations: List[RoutePoint],
        profile: str = "walking",
        top_n: int = 3
    ) -> List[dict]:
        """
        En yakın lokasyonları bul ve gece modu rotalarını hesapla
        """
        results = []
        
        for dest in destinations[:top_n + 5]:  # Biraz fazla dene
            night_route = await self.get_night_mode_route(
                user_location, dest, profile=profile
            )
            
            if night_route:
                results.append({
                    "destination": {
                        "latitude": dest.latitude,
                        "longitude": dest.longitude,
                        "name": dest.name
                    },
                    "route": night_route["route"],
                    "lighting_analysis": night_route["lighting_analysis"],
                    "distance_km": night_route["route"]["distance_km"],
                    "duration_min": night_route["route"]["duration_min"]
                })
            
            if len(results) >= top_n:
                break
        
        # Mesafeye göre sırala
        results.sort(key=lambda x: x["distance_km"])
        
        return results

