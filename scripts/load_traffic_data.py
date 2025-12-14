"""
Trafik Verilerini Yükle
- Segment series JSON'dan segment risk verilerini yükle
- Signal forecast CSV'den trafik tahmin verilerini yükle
"""
import asyncio
import json
import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.traffic_risk import SegmentRisk, TrafficForecast, RiskLevel


def calculate_risk_level(risk_score: float) -> RiskLevel:
    """Risk score'dan risk level'a çevir"""
    if risk_score >= 0.7:
        return RiskLevel.HIGH
    elif risk_score >= 0.4:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


async def load_segment_series_from_json(json_path: Path):
    """Segment series JSON'dan segment risk verilerini yükle"""
    if not json_path.exists():
        print(f"❌ JSON dosyası bulunamadı: {json_path}")
        return
    
    async with AsyncSessionLocal() as session:
        # Mevcut veriyi temizle (opsiyonel - yorum satırından çıkarabilirsiniz)
        # await session.execute(text("TRUNCATE segment_risks RESTART IDENTITY"))
        # await session.commit()
        
        count = 0
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for segment_data in data:
            segment_id = segment_data.get("segment_id")
            series = segment_data.get("series", [])
            
            if not segment_id or not series:
                continue
            
            for item in series:
                try:
                    timestamp_str = item.get("time")
                    traffic_density = float(item.get("traffic_density", 0))
                    risk_score = float(item.get("risk_score", 0))
                    
                    # Timestamp'i parse et
                    if "T" in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    else:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    # Risk level hesapla
                    risk_level = calculate_risk_level(risk_score)
                    
                    # Segment risk kaydı oluştur
                    segment_risk = SegmentRisk(
                        segment_id=segment_id,
                        timestamp=timestamp,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        risk_types=["traffic"],  # Varsayılan
                        current_density=traffic_density,
                        expected_2h=traffic_density,  # JSON'da yoksa mevcut değeri kullan
                        current_vehicle=None,
                        complaint_count_24h=0,
                        avg_urgency_24h=0.0,
                        max_urgency_24h=0.0,
                        noise_ratio_24h=0.0,
                        explanation=None
                    )
                    
                    session.add(segment_risk)
                    count += 1
                    
                    # Her 1000 kayıtta bir commit
                    if count % 1000 == 0:
                        await session.commit()
                        print(f"  ✓ {count} segment risk kaydı yüklendi...")
                
                except Exception as e:
                    print(f"  ⚠️ Hata (segment {segment_id}): {e}")
                    continue
        
        await session.commit()
        print(f"✅ {count} segment risk kaydı yüklendi")


async def load_signal_forecasts_from_csv(csv_path: Path):
    """Signal forecast CSV'den trafik tahmin verilerini yükle"""
    if not csv_path.exists():
        print(f"❌ CSV dosyası bulunamadı: {csv_path}")
        return
    
    async with AsyncSessionLocal() as session:
        # Mevcut veriyi temizle (opsiyonel)
        # await session.execute(text("TRUNCATE traffic_forecasts RESTART IDENTITY"))
        # await session.commit()
        
        count = 0
        
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    signal_id = int(row["signal_id"]) if row.get("signal_id") else None
                    ts_str = row.get("timestamp")
                    
                    # Timestamp parse
                    try:
                        timestamp = datetime.fromisoformat(ts_str)
                    except:
                        timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    
                    vehicle_count = float(row["vehicle_count"]) if row.get("vehicle_count") else None
                    traffic_density = float(row["traffic_density"])
                    expected_2h = float(row["expected_2h"])
                    
                    forecast = TrafficForecast(
                        signal_id=signal_id,
                        segment_id=None,  # CSV'de yok
                        timestamp=timestamp,
                        vehicle_count=vehicle_count,
                        traffic_density=traffic_density,
                        expected_2h=expected_2h
                    )
                    
                    session.add(forecast)
                    count += 1
                    
                    # Her 1000 kayıtta bir commit
                    if count % 1000 == 0:
                        await session.commit()
                        print(f"  ✓ {count} trafik tahmin kaydı yüklendi...")
                
                except Exception as e:
                    print(f"  ⚠️ Hata (satır {count + 1}): {e}")
                    continue
        
        await session.commit()
        print(f"✅ {count} trafik tahmin kaydı yüklendi")


async def main():
    """Ana fonksiyon"""
    segment_series_path = Path("/Users/zeynepogulcan/Desktop/cagri_son/segment_series.json")
    signal_forecast_path = Path("/Users/zeynepogulcan/Desktop/cagri_son/signal_forecast_2h.csv")
    
    print("=" * 50)
    print("🚀 Trafik Verileri Yükleniyor...")
    print("=" * 50)
    
    print("\n📊 Segment Series JSON yükleniyor...")
    await load_segment_series_from_json(segment_series_path)
    
    print("\n📈 Signal Forecast CSV yükleniyor...")
    await load_signal_forecasts_from_csv(signal_forecast_path)
    
    print("=" * 50)
    print("✅ Tüm trafik verileri başarıyla yüklendi!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

