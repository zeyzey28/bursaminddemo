"""
Yaz Modu (Gölge) Routing Servisi
Gölgeli yolları tercih eden routing algoritması
"""
from typing import List, Optional, Tuple
from geopy.distance import geodesic
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.osrm_service import osrm_service, RoutePoint, OSRMRoute
from app.models.road_shadow import RoadShadow


class ShadowModeRoutingService:
    """
    Yaz modu routing servisi
    
    Güneşli yaz günlerinde gölgeli yolları tercih eder.
    Özellikle yürüyüş rotaları için serinlik sağlar.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.min_shade_score = 0.3  # Minimum gölge skoru (0-1)
        self.sunny_penalty = 2.0  # Güneşli yol için mesafe cezası çarpanı
    
    async def get_shadow_for_point(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 50.0
    ) -> Optional[RoadShadow]:
        """
        Bir nokta için en yakın gölge bilgisini getir
        """
        query = select(RoadShadow)
        
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
    
    async def score_route_by_shade(
        self,
        route: OSRMRoute
    ) -> Tuple[float, int, float]:
        """
        Rotayı gölge açısından skorla
        
        Returns:
            (score, sunny_segment_count, avg_shade_score)
            - score: Düşük = daha iyi (daha az güneşli yol)
            - sunny_segment_count: Güneşli segment sayısı
            - avg_shade_score: Ortalama gölge skoru
        """
        if not route.geometry or not route.geometry.get("coordinates"):
            return (float('inf'), 0, 0.0)
        
        coordinates = route.geometry["coordinates"]
        sunny_count = 0
        total_score = 0.0
        checked_points = 0
        
        # Rota üzerindeki her 5. noktayı kontrol et (performans için)
        step = max(1, len(coordinates) // 20)  # Maksimum 20 nokta kontrol et
        
        for i in range(0, len(coordinates), step):
            lon, lat = coordinates[i]
            
            shadow = await self.get_shadow_for_point(lat, lon, radius_meters=50.0)
            
            if shadow:
                checked_points += 1
                total_score += shadow.shade_score
                
                # Güneşli yol (düşük gölge skoru)
                if shadow.shade_score < self.min_shade_score:
                    sunny_count += 1
                elif shadow.shade_score < 0.5:
                    sunny_count += 0.5  # Yarı ceza
        
        if checked_points == 0:
            return (float('inf'), 0, 0.0)
        
        avg_shade_score = total_score / checked_points
        
        # Skor: güneşli segment sayısı * ceza + (1 - ortalama gölge)
        # Düşük skor = daha gölgeli rota
        penalty = sunny_count * self.sunny_penalty
        shade_penalty = (1.0 - avg_shade_score) * 0.5
        
        final_score = penalty + shade_penalty
        
        return (final_score, int(sunny_count), avg_shade_score)
    
    async def get_shadow_mode_route(
        self,
        start: RoutePoint,
        end: RoutePoint,
        profile: str = "walking",
        max_alternatives: int = 3
    ) -> Optional[dict]:
        """
        Yaz modu için en iyi rotayı bul (gölgeli yolları tercih et)
        
        Önce normal rotayı al, sonra alternatifleri dene.
        Gölge açısından en iyi olanı seç.
        """
        # 1. Normal rota (en kısa)
        normal_route = await osrm_service.get_route(
            start, end, profile=profile, alternatives=False
        )
        
        if not normal_route:
            return None
        
        # 2. Tüm rotaları skorla
        routes_to_score = [normal_route]
        
        scored_routes = []
        
        for route in routes_to_score:
            score, sunny_count, avg_shade = await self.score_route_by_shade(route)
            
            scored_routes.append({
                "route": route,
                "shade_score": score,
                "sunny_segment_count": sunny_count,
                "avg_shade_score": avg_shade
            })
        
        # En iyi gölge skoruna sahip rotayı seç (düşük skor daha iyi)
        best_result = min(scored_routes, key=lambda x: x["shade_score"])
        
        # Eğer en iyi rota, normal rotadan çok daha uzunsa, normal rotayı tercih et
        max_route_deviation_factor = 1.5  # Maksimum %50 sapma
        if best_result["route"].distance_km > normal_route.distance_km * max_route_deviation_factor:
            return {
                "route": normal_route,
                "shade_analysis": {
                    "sunny_segment_count": (await self.score_route_by_shade(normal_route))[1],
                    "avg_shade_score": (await self.score_route_by_shade(normal_route))[2],
                    "is_shadow_mode_optimized": False
                }
            }
        
        return {
            "route": best_result["route"],
            "shade_analysis": {
                "sunny_segment_count": best_result["sunny_segment_count"],
                "avg_shade_score": best_result["avg_shade_score"],
                "is_shadow_mode_optimized": True
            }
        }

