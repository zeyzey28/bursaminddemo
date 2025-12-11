"""
Rota Optimizasyon Servisi
Çöp toplama ve afet tahliye rotaları için optimizasyon
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass
import math
from geopy.distance import geodesic


@dataclass
class Location:
    """Konum verisi"""
    id: int
    latitude: float
    longitude: float
    name: Optional[str] = None
    priority: float = 1.0  # Öncelik (çöp doluluk, aciliyet vb.)


@dataclass
class RouteResult:
    """Rota sonucu"""
    ordered_locations: List[Location]
    total_distance_km: float
    estimated_duration_min: float
    waypoints: List[dict]


class RouteOptimizer:
    """
    Rota optimizasyon servisi
    
    Algoritmalar:
    - Nearest Neighbor (basit, hızlı)
    - 2-opt improvement (daha iyi sonuç)
    """
    
    def __init__(
        self,
        average_speed_kmh: float = 30,
        stop_time_min: float = 3,
        fuel_consumption_per_km: float = 0.15
    ):
        self.average_speed = average_speed_kmh
        self.stop_time = stop_time_min
        self.fuel_consumption = fuel_consumption_per_km
    
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """İki nokta arası mesafe (km)"""
        return geodesic(
            (loc1.latitude, loc1.longitude),
            (loc2.latitude, loc2.longitude)
        ).kilometers
    
    def nearest_neighbor(
        self,
        start: Location,
        locations: List[Location],
        return_to_start: bool = True
    ) -> RouteResult:
        """
        En yakın komşu algoritması
        Basit ve hızlı, küçük veri setleri için yeterli
        """
        if not locations:
            return RouteResult(
                ordered_locations=[],
                total_distance_km=0,
                estimated_duration_min=0,
                waypoints=[]
            )
        
        remaining = locations.copy()
        ordered = []
        current = start
        total_distance = 0
        
        waypoints = [{
            "lat": start.latitude,
            "lon": start.longitude,
            "id": start.id,
            "name": start.name,
            "type": "start"
        }]
        
        while remaining:
            # En yakın noktayı bul (öncelik ağırlıklı)
            nearest = None
            nearest_score = float('inf')
            
            for loc in remaining:
                dist = self.calculate_distance(current, loc)
                # Öncelik yüksekse mesafeyi "azalt" (daha çekici yap)
                score = dist / loc.priority
                
                if score < nearest_score:
                    nearest_score = score
                    nearest = loc
            
            # Rotaya ekle
            dist = self.calculate_distance(current, nearest)
            total_distance += dist
            ordered.append(nearest)
            
            waypoints.append({
                "lat": nearest.latitude,
                "lon": nearest.longitude,
                "id": nearest.id,
                "name": nearest.name,
                "distance_from_prev": round(dist, 2),
                "type": "stop"
            })
            
            current = nearest
            remaining.remove(nearest)
        
        # Başlangıca dön
        if return_to_start:
            return_dist = self.calculate_distance(current, start)
            total_distance += return_dist
            waypoints.append({
                "lat": start.latitude,
                "lon": start.longitude,
                "id": start.id,
                "name": start.name,
                "distance_from_prev": round(return_dist, 2),
                "type": "end"
            })
        
        # Süre hesapla
        travel_time = (total_distance / self.average_speed) * 60  # dakika
        stop_time = len(ordered) * self.stop_time
        total_time = travel_time + stop_time
        
        return RouteResult(
            ordered_locations=ordered,
            total_distance_km=round(total_distance, 2),
            estimated_duration_min=round(total_time, 0),
            waypoints=waypoints
        )
    
    def two_opt_improvement(
        self,
        route: List[Location],
        start: Location
    ) -> List[Location]:
        """
        2-opt algoritması ile rota iyileştirme
        Nearest neighbor sonucunu optimize eder
        """
        if len(route) < 4:
            return route
        
        improved = True
        best_route = route.copy()
        
        while improved:
            improved = False
            
            for i in range(len(best_route) - 1):
                for j in range(i + 2, len(best_route)):
                    # Mevcut mesafe
                    if i == 0:
                        d1 = self.calculate_distance(start, best_route[i])
                    else:
                        d1 = self.calculate_distance(best_route[i-1], best_route[i])
                    
                    d2 = self.calculate_distance(best_route[j-1], best_route[j])
                    
                    # Yeni mesafe (swap sonrası)
                    if i == 0:
                        d3 = self.calculate_distance(start, best_route[j-1])
                    else:
                        d3 = self.calculate_distance(best_route[i-1], best_route[j-1])
                    
                    d4 = self.calculate_distance(best_route[i], best_route[j])
                    
                    # İyileşme var mı?
                    if d3 + d4 < d1 + d2:
                        # Segment'i ters çevir
                        best_route[i:j] = reversed(best_route[i:j])
                        improved = True
        
        return best_route
    
    def optimize_trash_collection(
        self,
        depot: Location,
        bins: List[Location],
        vehicle_capacity_kg: float = 5000
    ) -> dict:
        """
        Çöp toplama rotası optimizasyonu
        
        Çöp kutusu önceliği = doluluk oranı
        """
        # Nearest neighbor
        initial_route = self.nearest_neighbor(depot, bins, return_to_start=True)
        
        # 2-opt improvement
        optimized_order = self.two_opt_improvement(
            initial_route.ordered_locations,
            depot
        )
        
        # Yeniden hesapla
        total_distance = 0
        current = depot
        waypoints = [{
            "lat": depot.latitude,
            "lon": depot.longitude,
            "id": depot.id,
            "name": "Depo",
            "type": "start"
        }]
        
        for loc in optimized_order:
            dist = self.calculate_distance(current, loc)
            total_distance += dist
            waypoints.append({
                "lat": loc.latitude,
                "lon": loc.longitude,
                "id": loc.id,
                "name": loc.name,
                "distance_from_prev": round(dist, 2),
                "priority": loc.priority,
                "type": "collection"
            })
            current = loc
        
        # Depoya dönüş
        return_dist = self.calculate_distance(current, depot)
        total_distance += return_dist
        waypoints.append({
            "lat": depot.latitude,
            "lon": depot.longitude,
            "id": depot.id,
            "name": "Depo",
            "distance_from_prev": round(return_dist, 2),
            "type": "end"
        })
        
        # Metrikler
        travel_time = (total_distance / self.average_speed) * 60
        stop_time = len(bins) * self.stop_time
        total_time = travel_time + stop_time
        fuel = total_distance * self.fuel_consumption
        
        return {
            "optimized_order": [loc.id for loc in optimized_order],
            "waypoints": waypoints,
            "total_distance_km": round(total_distance, 2),
            "estimated_duration_min": round(total_time, 0),
            "estimated_fuel_liters": round(fuel, 2),
            "total_stops": len(bins),
            "improvement_note": "2-opt optimizasyonu uygulandı"
        }
    
    def find_evacuation_route(
        self,
        start: Location,
        safe_zones: List[Location],
        blocked_segments: List[Tuple[Location, Location]] = None
    ) -> dict:
        """
        Afet durumunda en yakın güvenli bölgeye rota
        
        Args:
            start: Başlangıç noktası
            safe_zones: Güvenli toplanma alanları
            blocked_segments: Kapalı yol segmentleri
        """
        if not safe_zones:
            return {
                "found": False,
                "message": "Güvenli bölge bulunamadı"
            }
        
        # En yakın güvenli bölgeyi bul
        nearest_zone = None
        nearest_dist = float('inf')
        
        for zone in safe_zones:
            dist = self.calculate_distance(start, zone)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_zone = zone
        
        # Yürüyüş süresi (4 km/h ortalama yürüyüş hızı)
        walk_time = (nearest_dist / 4) * 60  # dakika
        
        return {
            "found": True,
            "destination": {
                "id": nearest_zone.id,
                "name": nearest_zone.name,
                "latitude": nearest_zone.latitude,
                "longitude": nearest_zone.longitude
            },
            "distance_km": round(nearest_dist, 2),
            "estimated_walk_time_min": round(walk_time, 0),
            "route": {
                "type": "LineString",
                "coordinates": [
                    [start.longitude, start.latitude],
                    [nearest_zone.longitude, nearest_zone.latitude]
                ]
            }
        }


# Singleton instance
route_optimizer = RouteOptimizer()

