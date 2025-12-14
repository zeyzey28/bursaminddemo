"""
Trafik What-If Senaryo Servisi
Çeşitli senaryolar için trafik etkisi hesaplama
LightGBM modeli ile gerçekçi trafik simülasyonu
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path


class ScenarioType(str, Enum):
    """What-if senaryo türleri"""
    ROAD_WORK = "road_work"  # Yol çalışması (şerit kapatma)
    PIPE_BURST = "pipe_burst"  # Boru patlaması (yol kapatma + acil müdahale)
    ACCIDENT = "accident"  # Trafik kazası (kısa süreli kapatma)
    EVENT = "event"  # Etkinlik (trafik artışı)
    WEATHER = "weather"  # Hava durumu (kar, yağmur - kapasite azalması)


class TrafficWhatIfService:
    """
    What-if senaryo servisi
    
    Belediye panelinde çeşitli senaryoları simüle eder:
    - "Bu yolu kapatırsak ne olur?" (yol çalışması)
    - "Boru patlarsa ne olur?" (acil durum)
    - "Kaza olursa ne olur?" (kısa süreli kapatma)
    - "Etkinlik olursa ne olur?" (trafik artışı)
    - "Kar yağarsa ne olur?" (kapasite azalması)
    
    Her senaryo için:
    - Hangi yollar etkilenecek
    - Yoğunluk ne kadar artacak
    - En az zarar veren saat hangisi
    """
    
    def __init__(self, use_model: bool = True):
        """
        Args:
            use_model: LightGBM modelini kullan (True) veya basit algoritma (False)
        """
        # Segment komşuluk matrisi (cache'lenebilir)
        self.segment_neighbors: Dict[str, List[str]] = {}
        
        # Trafik tahmin modeli (lazy load)
        self.traffic_model = None
        self.use_model = use_model
        if use_model:
            self._load_traffic_model()
        
        # Senaryo bazlı katsayılar
        self.scenario_impact_multipliers = {
            ScenarioType.ROAD_WORK: {
                "capacity_reduction": 0.3,  # Her şerit %30 kapasite azalması
                "diversion_factor": 0.4,  # %40 trafik yönlenir
                "radius_km": 2.0  # 2 km yarıçap etkilenir
            },
            ScenarioType.PIPE_BURST: {
                "capacity_reduction": 0.8,  # %80 kapasite azalması (yol tamamen kapatılabilir)
                "diversion_factor": 0.7,  # %70 trafik yönlenir
                "radius_km": 3.0,  # 3 km yarıçap etkilenir
                "urgency_bonus": 1.5  # Acil durum - daha fazla etki
            },
            ScenarioType.ACCIDENT: {
                "capacity_reduction": 0.5,  # %50 kapasite azalması
                "diversion_factor": 0.5,  # %50 trafik yönlenir
                "radius_km": 1.5,  # 1.5 km yarıçap etkilenir
                "duration_multiplier": 0.5  # Kısa süreli - etki azalır
            },
            ScenarioType.EVENT: {
                "capacity_reduction": 0.0,  # Kapasite azalmaz, trafik artar
                "traffic_increase": 0.4,  # %40 trafik artışı
                "radius_km": 5.0,  # 5 km yarıçap etkilenir (etkinlik alanı)
                "diversion_factor": -0.3  # Negatif = trafik çekilir
            },
            ScenarioType.WEATHER: {
                "capacity_reduction": 0.2,  # %20 kapasite azalması (kar/yağmur)
                "diversion_factor": 0.1,  # %10 trafik yönlenir
                "radius_km": 10.0,  # 10 km yarıçap etkilenir (bölgesel)
                "weather_severity": 1.0  # Hava durumu şiddeti
            }
        }
        
        self.diversion_factor = 0.4  # Genel yönlenme faktörü
    
    def _load_traffic_model(self):
        """Trafik tahmin modelini yükle"""
        try:
            from app.services.traffic_model import TrafficDensityModel
            model_path = Path(__file__).parent.parent.parent / "lgbm_density_tplus2h.pkl"
            if model_path.exists():
                self.traffic_model = TrafficDensityModel(model_path=str(model_path))
                print(f"✅ Trafik modeli yüklendi: {model_path}")
            else:
                print(f"⚠️ Model dosyası bulunamadı: {model_path}, basit algoritma kullanılacak")
                self.use_model = False
        except Exception as e:
            print(f"⚠️ Model yüklenemedi: {e}, basit algoritma kullanılacak")
            self.use_model = False
    
    def build_spatial_neighbors(self, segments_gdf):
        """
        Segment komşuluk matrisi oluştur
        (GeoDataFrame'den segment ilişkilerini çıkar)
        
        Şimdilik basit bir yaklaşım kullanıyoruz.
        Gerçek uygulamada OSM verilerinden yol ağı grafiği oluşturulmalı.
        """
        # TODO: Gerçek yol ağı grafiği oluştur
        # Şimdilik NSB segmentleri için basit komşuluk varsayımı
        for i in range(1, 50):
            seg_id = f"NSB_{i:03d}"
            neighbors = []
            if i > 1:
                neighbors.append(f"NSB_{i-1:03d}")
            if i < 49:
                neighbors.append(f"NSB_{i+1:03d}")
            self.segment_neighbors[seg_id] = neighbors
    
    def run_scenario(
        self,
        scenario_type: str,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        lane_closed: int = 1,
        duration_hours: int = 6,
        start_time: Optional[str] = None,
        max_hops: int = 5,
        **kwargs  # Senaryo bazlı ek parametreler
    ) -> Dict:
        """
        Genel what-if senaryo çalıştırıcı
        
        Args:
            scenario_type: Senaryo türü (road_work, pipe_burst, accident, event, weather)
            seg_status_df: Segment durum DataFrame'i
            segment_id: Etkilenen segment
            lane_closed: Kapatılan şerit sayısı (road_work, pipe_burst, accident için)
            duration_hours: Süre (saat)
            start_time: Başlangıç saati
            max_hops: Maksimum komşuluk derinliği
            **kwargs: Senaryo bazlı ek parametreler
                - weather_severity: Hava durumu şiddeti (0-1) (weather için)
                - event_attendance: Etkinlik katılımcı sayısı (event için)
        
        Returns:
            Senaryo sonuçları dict'i
        """
        scenario_enum = ScenarioType(scenario_type)
        multipliers = self.scenario_impact_multipliers[scenario_enum]
        
        # Senaryo bazlı hesaplama
        if scenario_type == ScenarioType.ROAD_WORK:
            return self._run_road_work_scenario(
                seg_status_df, segment_id, lane_closed, duration_hours, start_time, max_hops
            )
        elif scenario_type == ScenarioType.PIPE_BURST:
            return self._run_pipe_burst_scenario(
                seg_status_df, segment_id, duration_hours, start_time, max_hops
            )
        elif scenario_type == ScenarioType.ACCIDENT:
            return self._run_accident_scenario(
                seg_status_df, segment_id, duration_hours, start_time, max_hops
            )
        elif scenario_type == ScenarioType.EVENT:
            event_attendance = kwargs.get("event_attendance", 1000)
            return self._run_event_scenario(
                seg_status_df, segment_id, event_attendance, duration_hours, start_time, max_hops
            )
        elif scenario_type == ScenarioType.WEATHER:
            weather_severity = kwargs.get("weather_severity", 0.5)
            return self._run_weather_scenario(
                seg_status_df, segment_id, weather_severity, duration_hours, start_time, max_hops
            )
        else:
            raise ValueError(f"Bilinmeyen senaryo türü: {scenario_type}")
    
    def what_if_road_work(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        lane_closed: int = 1,
        duration_hours: int = 6,
        start_time: Optional[str] = None,
        max_hops: int = 5
    ) -> Dict:
        """Yol çalışması senaryosu (geriye dönük uyumluluk için)"""
        return self._run_road_work_scenario(
            seg_status_df, segment_id, lane_closed, duration_hours, start_time, max_hops
        )
    
    def _run_road_work_scenario(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        lane_closed: int,
        duration_hours: int,
        start_time: Optional[str],
        max_hops: int
    ) -> Dict:
        """
        Yol çalışması what-if senaryosu
        
        Args:
            seg_status_df: Segment durum DataFrame'i (segment_id, timestamp, risk_score)
            segment_id: Kapatılacak segment
            lane_closed: Kapatılan şerit sayısı
            duration_hours: Çalışma süresi (saat)
            start_time: Başlangıç saati ("HH:MM" formatı)
            max_hops: Maksimum komşuluk derinliği
        
        Returns:
            Senaryo sonuçları dict'i
        """
        # Segment komşularını bul
        if not self.segment_neighbors:
            self._init_default_neighbors()
        
        # Etkilenen segmentleri bul (BFS ile)
        affected_segments = self._find_affected_segments(
            segment_id, max_hops=max_hops
        )
        
        # Mevcut trafik yoğunluğunu hesapla
        current_density = self._get_current_density(seg_status_df, segment_id)
        
        # Etki hesaplama (model kullanılıyorsa daha gerçekçi)
        impact_results = []
        
        if self.use_model and self.traffic_model:
            # Model tabanlı simülasyon
            impact_results = self._calculate_impact_with_model(
                seg_status_df, affected_segments, segment_id, lane_closed, current_density
            )
        else:
            # Basit algoritma (fallback)
            for affected_seg in affected_segments:
                if affected_seg == segment_id:
                    delay_increase = self._calculate_direct_impact(
                        current_density, lane_closed
                    )
                else:
                    delay_increase = self._calculate_indirect_impact(
                        affected_seg, segment_id, current_density, lane_closed
                    )
                
                impact_results.append({
                    "segment_id": affected_seg,
                    "delay_increase_pct": int(delay_increase)
                })
        
        # En iyi zaman penceresini bul
        best_window = self._find_best_time_window(
            seg_status_df, segment_id, duration_hours
        )
        
        # Özet oluştur
        summary = self._generate_summary(
            segment_id, lane_closed, duration_hours,
            impact_results, best_window
        )
        
        return {
            "scenario": "road_work",
            "segment_id": segment_id,
            "impact": {
                "lane_closed": lane_closed,
                "duration_hours": duration_hours
            },
            "start_time": start_time,
            "affected_segments": impact_results,
            "best_time_window": best_window,
            "summary": summary
        }
    
    def _run_pipe_burst_scenario(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        duration_hours: int,
        start_time: Optional[str],
        max_hops: int
    ) -> Dict:
        """
        Boru patlaması senaryosu
        
        Yol tamamen kapatılır, acil müdahale gerekir.
        Etki daha geniş alana yayılır.
        """
        if not self.segment_neighbors:
            self._init_default_neighbors()
        
        affected_segments = self._find_affected_segments(segment_id, max_hops=max_hops + 2)
        current_density = self._get_current_density(seg_status_df, segment_id)
        
        multipliers = self.scenario_impact_multipliers[ScenarioType.PIPE_BURST]
        
        impact_results = []
        for affected_seg in affected_segments:
            if affected_seg == segment_id:
                # Boru patlaması = yol tamamen kapatılır
                delay_increase = self._calculate_direct_impact(
                    current_density, lane_closed=3  # Tüm şeritler kapatılmış gibi
                ) * multipliers["urgency_bonus"]
            else:
                delay_increase = self._calculate_indirect_impact(
                    affected_seg, segment_id, current_density, lane_closed=3
                ) * multipliers["urgency_bonus"]
            
            impact_results.append({
                "segment_id": affected_seg,
                "delay_increase_pct": int(min(100, delay_increase))
            })
        
        best_window = self._find_best_time_window(seg_status_df, segment_id, duration_hours)
        
        summary = (
            f"🚨 {segment_id} segmentinde boru patlaması ({duration_hours}s) "
            f"acil müdahale gerektirir. {len(impact_results)} segment etkilenecek. "
            f"En az etki için {best_window['start']}-{best_window['end']} aralığında müdahale önerilir."
        )
        
        return {
            "scenario": "pipe_burst",
            "segment_id": segment_id,
            "impact": {
                "duration_hours": duration_hours,
                "urgency": "high"
            },
            "start_time": start_time,
            "affected_segments": impact_results,
            "best_time_window": best_window,
            "summary": summary
        }
    
    def _run_accident_scenario(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        duration_hours: int,
        start_time: Optional[str],
        max_hops: int
    ) -> Dict:
        """
        Trafik kazası senaryosu
        
        Kısa süreli kapatma, acil müdahale.
        Etki daha lokal kalır.
        """
        if not self.segment_neighbors:
            self._init_default_neighbors()
        
        affected_segments = self._find_affected_segments(segment_id, max_hops=max_hops - 1)
        current_density = self._get_current_density(seg_status_df, segment_id)
        
        multipliers = self.scenario_impact_multipliers[ScenarioType.ACCIDENT]
        
        impact_results = []
        for affected_seg in affected_segments:
            if affected_seg == segment_id:
                delay_increase = self._calculate_direct_impact(
                    current_density, lane_closed=1
                ) * multipliers["duration_multiplier"]
            else:
                delay_increase = self._calculate_indirect_impact(
                    affected_seg, segment_id, current_density, lane_closed=1
                ) * multipliers["duration_multiplier"]
            
            impact_results.append({
                "segment_id": affected_seg,
                "delay_increase_pct": int(min(50, delay_increase))  # Kaza için max %50
            })
        
        best_window = {"start": "00:00", "end": "23:59"}  # Kaza için zaman seçeneği yok
        
        summary = (
            f"⚠️ {segment_id} segmentinde trafik kazası ({duration_hours}s) "
            f"acil müdahale gerektirir. {len(impact_results)} segment etkilenecek. "
            f"Maksimum gecikme artışı %{max((s['delay_increase_pct'] for s in impact_results), default=0)}."
        )
        
        return {
            "scenario": "accident",
            "segment_id": segment_id,
            "impact": {
                "duration_hours": duration_hours,
                "urgency": "high"
            },
            "start_time": start_time,
            "affected_segments": impact_results,
            "best_time_window": best_window,
            "summary": summary
        }
    
    def _run_event_scenario(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        event_attendance: int,
        duration_hours: int,
        start_time: Optional[str],
        max_hops: int
    ) -> Dict:
        """
        Etkinlik senaryosu
        
        Trafik artışı (kapasite azalmaz, trafik yoğunluğu artar).
        Etkinlik alanı çevresinde trafik yoğunlaşır.
        """
        if not self.segment_neighbors:
            self._init_default_neighbors()
        
        affected_segments = self._find_affected_segments(segment_id, max_hops=max_hops + 3)
        current_density = self._get_current_density(seg_status_df, segment_id)
        
        multipliers = self.scenario_impact_multipliers[ScenarioType.EVENT]
        
        # Etkinlik trafik artışı = katılımcı sayısına bağlı
        traffic_increase_base = min(0.5, event_attendance / 10000)  # 10k kişi = %50 artış
        
        impact_results = []
        for affected_seg in affected_segments:
            hops = self._get_hop_distance(segment_id, affected_seg)
            
            # Etkinlik alanına yakın segmentlerde daha fazla artış
            distance_factor = 1.0 / (hops + 1)
            traffic_increase = traffic_increase_base * distance_factor * 100
            
            impact_results.append({
                "segment_id": affected_seg,
                "delay_increase_pct": int(min(80, traffic_increase))  # Max %80
            })
        
        # Etkinlik için en iyi zaman = trafiğin en az olduğu saatler
        best_window = self._find_best_time_window(seg_status_df, segment_id, duration_hours)
        
        summary = (
            f"🎉 {segment_id} segmentinde etkinlik ({event_attendance} kişi, {duration_hours}s) "
            f"{len(impact_results)} segment etkilenecek. "
            f"En az etki için {best_window['start']}-{best_window['end']} saatleri önerilir."
        )
        
        return {
            "scenario": "event",
            "segment_id": segment_id,
            "impact": {
                "event_attendance": event_attendance,
                "duration_hours": duration_hours
            },
            "start_time": start_time,
            "affected_segments": impact_results,
            "best_time_window": best_window,
            "summary": summary
        }
    
    def _run_weather_scenario(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        weather_severity: float,
        duration_hours: int,
        start_time: Optional[str],
        max_hops: int
    ) -> Dict:
        """
        Hava durumu senaryosu (kar, yağmur, buz)
        
        Bölgesel kapasite azalması, tüm segmentler etkilenir.
        """
        if not self.segment_neighbors:
            self._init_default_neighbors()
        
        # Hava durumu bölgesel etki gösterir
        affected_segments = self._find_affected_segments(segment_id, max_hops=max_hops + 5)
        current_density = self._get_current_density(seg_status_df, segment_id)
        
        multipliers = self.scenario_impact_multipliers[ScenarioType.WEATHER]
        
        impact_results = []
        for affected_seg in affected_segments:
            # Hava durumu etkisi = şiddet * kapasite azalması
            capacity_reduction = multipliers["capacity_reduction"] * weather_severity
            delay_increase = capacity_reduction * current_density * 100
            
            impact_results.append({
                "segment_id": affected_seg,
                "delay_increase_pct": int(min(60, delay_increase))  # Max %60
            })
        
        # Hava durumu için zaman penceresi yok (bölgesel)
        best_window = {"start": "00:00", "end": "23:59"}
        
        severity_text = "hafif" if weather_severity < 0.3 else "orta" if weather_severity < 0.7 else "şiddetli"
        
        summary = (
            f"🌧️ {severity_text.capitalize()} hava durumu ({duration_hours}s) "
            f"{len(impact_results)} segment etkilenecek. "
            f"Bölgesel kapasite azalması bekleniyor."
        )
        
        return {
            "scenario": "weather",
            "segment_id": segment_id,
            "impact": {
                "weather_severity": weather_severity,
                "duration_hours": duration_hours
            },
            "start_time": start_time,
            "affected_segments": impact_results,
            "best_time_window": best_window,
            "summary": summary
        }
    
    def _init_default_neighbors(self):
        """Varsayılan segment komşulukları (NSB segmentleri için)"""
        for i in range(1, 50):
            seg_id = f"NSB_{i:03d}"
            neighbors = []
            if i > 1:
                neighbors.append(f"NSB_{i-1:03d}")
            if i < 49:
                neighbors.append(f"NSB_{i+1:03d}")
            self.segment_neighbors[seg_id] = neighbors
    
    def _find_affected_segments(
        self,
        segment_id: str,
        max_hops: int = 5
    ) -> List[str]:
        """
        BFS ile etkilenen segmentleri bul
        """
        affected = {segment_id}
        queue = [(segment_id, 0)]  # (segment_id, hop_count)
        
        while queue:
            current_seg, hops = queue.pop(0)
            
            if hops >= max_hops:
                continue
            
            neighbors = self.segment_neighbors.get(current_seg, [])
            for neighbor in neighbors:
                if neighbor not in affected:
                    affected.add(neighbor)
                    queue.append((neighbor, hops + 1))
        
        return list(affected)
    
    def _get_current_density(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str
    ) -> float:
        """Segment'in mevcut trafik yoğunluğunu al"""
        seg_data = seg_status_df[seg_status_df["segment_id"] == segment_id]
        
        if seg_data.empty:
            return 0.5  # Varsayılan
        
        # En son risk skorunu kullan (risk_score trafik yoğunluğu ile ilişkili)
        latest = seg_data.sort_values("timestamp").iloc[-1]
        return latest.get("risk_score", 0.5)
    
    def _calculate_direct_impact(
        self,
        current_density: float,
        lane_closed: int
    ) -> float:
        """
        Kapatılan segment için direkt etki
        
        Kapasite azalması = lane_closed * lane_capacity_reduction
        Yoğunluk artışı = kapasite azalması * mevcut yoğunluk
        """
        capacity_reduction = lane_closed * self.lane_capacity_reduction
        density_increase = capacity_reduction * current_density * 100
        
        return min(100, density_increase)  # Maksimum %100
    
    def _calculate_indirect_impact(
        self,
        affected_seg: str,
        closed_seg: str,
        closed_density: float,
        lane_closed: int
    ) -> float:
        """
        Komşu segmentler için dolaylı etki
        
        Kapatılan segment'ten gelen trafiğin bir kısmı bu segment'e yönlenir.
        """
        # Komşuluk mesafesi (hop sayısı)
        hops = self._get_hop_distance(closed_seg, affected_seg)
        
        if hops == 0:
            return 0
        
        # Her hop'ta trafik azalır
        diversion_rate = self.diversion_factor / (hops ** 1.5)
        
        # Etki = yönlenen trafik * kapasite azalması
        impact = closed_density * diversion_rate * lane_closed * 20
        
        return min(50, impact)  # Maksimum %50 dolaylı etki
    
    def _get_hop_distance(self, seg1: str, seg2: str) -> int:
        """İki segment arasındaki hop mesafesi"""
        if seg1 == seg2:
            return 0
        
        visited = set()
        queue = [(seg1, 0)]
        
        while queue:
            current, hops = queue.pop(0)
            
            if current == seg2:
                return hops
            
            if current in visited:
                continue
            visited.add(current)
            
            neighbors = self.segment_neighbors.get(current, [])
            for neighbor in neighbors:
                if neighbor not in visited:
                    queue.append((neighbor, hops + 1))
        
        return 10  # Çok uzak
    
    def _find_best_time_window(
        self,
        seg_status_df: pd.DataFrame,
        segment_id: str,
        duration_hours: int
    ) -> Dict[str, str]:
        """
        En az zarar veren zaman penceresini bul
        
        Trafik yoğunluğunun en düşük olduğu saatleri bulur.
        """
        seg_data = seg_status_df[seg_status_df["segment_id"] == segment_id].copy()
        
        if seg_data.empty:
            return {"start": "01:00", "end": "07:00"}  # Varsayılan gece saatleri
        
        # Saat bazında ortalama yoğunluk hesapla
        seg_data["hour"] = pd.to_datetime(seg_data["timestamp"]).dt.hour
        hourly_avg = seg_data.groupby("hour")["risk_score"].mean()
        
        # En düşük yoğunluklu saatleri bul
        sorted_hours = hourly_avg.sort_values().index.tolist()
        
        # Sürekli en düşük yoğunluklu saat aralığını bul
        best_start = sorted_hours[0]
        best_end = (best_start + duration_hours) % 24
        
        return {
            "start": f"{best_start:02d}:00",
            "end": f"{best_end:02d}:00"
        }
    
    def _calculate_impact_with_model(
        self,
        seg_status_df: pd.DataFrame,
        affected_segments: List[str],
        closed_segment_id: str,
        lane_closed: int,
        base_density: float
    ) -> List[Dict]:
        """
        Model tabanlı etki hesaplama (LightGBM ile)
        
        Her etkilenen segment için:
        1. Mevcut trafik verilerini hazırla (model için feature'lar)
        2. Senaryo etkisini uygula (kapasite azalması, yönlenme)
        3. Model ile 2 saat sonrası yoğunluğu tahmin et
        4. Senaryo öncesi ve sonrası tahminleri karşılaştır
        5. Gecikme artışını hesapla
        
        Not: Model signal_id bazlı çalışıyor, segment_id için mapping gerekebilir
        """
        impact_results = []
        
        for affected_seg in affected_segments:
            try:
                # Senaryo öncesi: Mevcut durum
                seg_data = seg_status_df[seg_status_df["segment_id"] == affected_seg]
                
                if seg_data.empty:
                    # Veri yoksa basit algoritma kullan
                    if affected_seg == closed_segment_id:
                        delay_increase = self._calculate_direct_impact(base_density, lane_closed)
                    else:
                        delay_increase = self._calculate_indirect_impact(
                            affected_seg, closed_segment_id, base_density, lane_closed
                        )
                else:
                    # Senaryo etkisini hesapla
                    current_density = seg_data["risk_score"].iloc[-1]
                    
                    if affected_seg == closed_segment_id:
                        # Kapatılan segment: kapasite azalır
                        capacity_reduction = lane_closed * self.lane_capacity_reduction
                        scenario_density = min(1.0, current_density / (1 - capacity_reduction))
                    else:
                        # Komşu segmentler: yönlenen trafik
                        hops = self._get_hop_distance(closed_segment_id, affected_seg)
                        diversion = self.diversion_factor / (hops + 1)
                        diverted_traffic = base_density * diversion
                        scenario_density = min(1.0, current_density + diverted_traffic * 0.3)
                    
                    # Model ile tahmin yapmak için feature'ları hazırla
                    # Not: Model signal_id bekliyor, segment_id için dummy signal_id kullanıyoruz
                    # Gerçek uygulamada segment_id -> signal_id mapping gerekir
                    try:
                        # Senaryo öncesi tahmin (mevcut verilerle)
                        # Model için gerekli feature'ları oluştur
                        model_input = self._prepare_model_features(
                            seg_data, current_density, scenario_density
                        )
                        
                        if model_input is not None and self.traffic_model:
                            # Senaryo öncesi tahmin
                            before_pred = self.traffic_model.predict(model_input["before"])
                            # Senaryo sonrası tahmin (yoğunluk değişmiş)
                            after_pred = self.traffic_model.predict(model_input["after"])
                            
                            # Tahmin farkı = etki
                            density_increase = (after_pred - before_pred) * 100
                            delay_increase = density_increase * 1.5  # Yoğunluk -> gecikme
                        else:
                            # Model kullanılamazsa basit hesaplama
                            density_increase = (scenario_density - current_density) * 100
                            delay_increase = density_increase * 1.5
                    except Exception as model_error:
                        # Model hatası: basit algoritma
                        density_increase = (scenario_density - current_density) * 100
                        delay_increase = density_increase * 1.5
                
            except Exception as e:
                # Genel hata: basit algoritma
                if affected_seg == closed_segment_id:
                    delay_increase = self._calculate_direct_impact(base_density, lane_closed)
                else:
                    delay_increase = self._calculate_indirect_impact(
                        affected_seg, closed_segment_id, base_density, lane_closed
                    )
            
            impact_results.append({
                "segment_id": affected_seg,
                "delay_increase_pct": int(min(100, max(0, delay_increase)))
            })
        
        return impact_results
    
    def _prepare_model_features(
        self,
        seg_data: pd.DataFrame,
        current_density: float,
        scenario_density: float
    ) -> Optional[Dict]:
        """
        Model için feature'ları hazırla
        
        Model signal_id bazlı çalışıyor, segment_id için dummy signal_id kullanıyoruz.
        Gerçek uygulamada segment_id -> signal_id mapping tablosu gerekir.
        """
        if seg_data.empty or len(seg_data) < 2:
            return None
        
        try:
            # Son 24 veriyi al (model için gerekli)
            recent_data = seg_data.tail(24).copy()
            recent_data["timestamp"] = pd.to_datetime(recent_data["timestamp"])
            
            # Senaryo öncesi: mevcut yoğunluk
            before_df = recent_data.copy()
            before_df["traffic_density"] = current_density
            before_df["vehicle_count"] = current_density * 100  # Dummy (model için)
            before_df["signal_id"] = 1  # Dummy signal_id (segment_id -> signal_id mapping gerekir)
            
            # Senaryo sonrası: değişmiş yoğunluk
            after_df = recent_data.copy()
            after_df["traffic_density"] = scenario_density
            after_df["vehicle_count"] = scenario_density * 100  # Dummy
            after_df["signal_id"] = 1  # Dummy
            
            return {
                "before": before_df,
                "after": after_df
            }
        except Exception:
            return None
    
    def _generate_summary(
        self,
        segment_id: str,
        lane_closed: int,
        duration_hours: int,
        affected_segments: List[Dict],
        best_window: Dict[str, str]
    ) -> str:
        """Senaryo özeti oluştur"""
        affected_count = len(affected_segments)
        max_impact = max(
            (seg["delay_increase_pct"] for seg in affected_segments),
            default=0
        )
        
        method = "model tabanlı" if self.use_model and self.traffic_model else "algoritma tabanlı"
        
        return (
            f"{segment_id} segmentinde {lane_closed} şerit kapatma ({duration_hours}s) "
            f"en düşük etki için {best_window['start']}-{best_window['end']} aralığında önerilir. "
            f"{affected_count} segment etkilenecek, maksimum gecikme artışı %{max_impact}. "
            f"(Hesaplama: {method})"
        )

