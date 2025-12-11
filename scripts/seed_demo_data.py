"""
Demo Veri Oluşturma Script'i
Test ve geliştirme için örnek veriler oluşturur
"""
import asyncio
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus, ComplaintCategory, ComplaintPriority
from app.models.location import TrafficPoint, TrafficLevel
from app.models.trash import TrashBin, TrashBinType
from app.models.air_quality import AirQualityReading, AirQualityLevel
from app.models.disaster import DisasterMode, SafeRoute, BlockedRoad, DisasterType, DisasterSeverity
from app.models.shadow import ShadowRoute


# Naim Süleymanoğlu Bulvarı yaklaşık koordinatları
BOULEVARD_CENTER = (40.2175, 28.9750)
BOULEVARD_BOUNDS = {
    "min_lat": 40.2100,
    "max_lat": 40.2250,
    "min_lon": 28.9500,
    "max_lon": 29.0000
}


def random_point_in_bounds():
    """Bulvar sınırları içinde rastgele nokta"""
    lat = random.uniform(BOULEVARD_BOUNDS["min_lat"], BOULEVARD_BOUNDS["max_lat"])
    lon = random.uniform(BOULEVARD_BOUNDS["min_lon"], BOULEVARD_BOUNDS["max_lon"])
    return lat, lon


async def create_users(session):
    """Örnek kullanıcılar oluştur"""
    print("\n👤 Kullanıcılar oluşturuluyor...")
    
    users = [
        User(
            email="admin@bursa.bel.tr",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin Kullanıcı",
            role=UserRole.ADMIN,
            is_verified=True
        ),
        User(
            email="belediye@bursa.bel.tr",
            hashed_password=get_password_hash("belediye123"),
            full_name="Belediye Personeli",
            role=UserRole.MUNICIPALITY,
            is_verified=True
        ),
        User(
            email="vatandas@example.com",
            hashed_password=get_password_hash("vatandas123"),
            full_name="Örnek Vatandaş",
            role=UserRole.CITIZEN,
            is_verified=True,
            phone="0532 123 45 67",
            address="Nilüfer, Bursa"
        )
    ]
    
    for user in users:
        session.add(user)
    
    await session.flush()
    print(f"✓ {len(users)} kullanıcı oluşturuldu")
    return users


async def create_complaints(session, user):
    """Örnek şikayetler oluştur"""
    print("\n📝 Şikayetler oluşturuluyor...")
    
    complaint_data = [
        ("Yol çukuru", "Bulvar üzerinde derin bir çukur var, araçlar için tehlikeli.", ComplaintCategory.ROAD_DAMAGE),
        ("Sokak lambası arızalı", "3 gündür yanmıyor, gece karanlık oluyor.", ComplaintCategory.LIGHTING),
        ("Çöp birikintisi", "Köşedeki çöp kutusu taşmış, koku yayılıyor.", ComplaintCategory.TRASH),
        ("Trafik işareti eksik", "Kavşakta dur işareti yok.", ComplaintCategory.TRAFFIC),
        ("Park sorunu", "Kaldırıma park eden araçlar yürüyüşü engelliyor.", ComplaintCategory.PARKING),
        ("Ağaç bakımı gerekli", "Ağaç dalları elektrik tellerine değiyor.", ComplaintCategory.GREEN_AREA),
        ("Su sızıntısı", "Ana borudan su sızıyor, yol ıslanmış.", ComplaintCategory.WATER),
    ]
    
    complaints = []
    for i, (title, desc, category) in enumerate(complaint_data):
        lat, lon = random_point_in_bounds()
        
        status = random.choice(list(ComplaintStatus))
        priority = random.choice(list(ComplaintPriority))
        
        complaint = Complaint(
            user_id=user.id,
            title=title,
            description=desc,
            category=category,
            latitude=lat,
            longitude=lon,
            status=status,
            priority=priority,
            urgency_score=random.uniform(0.3, 0.9),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        
        if status == ComplaintStatus.RESOLVED:
            complaint.resolved_at = datetime.utcnow() - timedelta(days=random.randint(0, 5))
        
        session.add(complaint)
        complaints.append(complaint)
    
    await session.flush()
    print(f"✓ {len(complaints)} şikayet oluşturuldu")
    return complaints


async def create_traffic_points(session):
    """Trafik noktaları oluştur"""
    print("\n🚗 Trafik noktaları oluşturuluyor...")
    
    road_names = [
        "Naim Süleymanoğlu Bulvarı",
        "Nilüfer Caddesi",
        "Atatürk Caddesi",
        "İstanbul Yolu"
    ]
    
    emojis = {
        TrafficLevel.VERY_LOW: "😊",
        TrafficLevel.LOW: "🙂",
        TrafficLevel.MODERATE: "😐",
        TrafficLevel.HIGH: "😟",
        TrafficLevel.VERY_HIGH: "😫"
    }
    
    points = []
    for _ in range(20):
        lat, lon = random_point_in_bounds()
        level = random.choice(list(TrafficLevel))
        
        point = TrafficPoint(
            latitude=lat,
            longitude=lon,
            road_name=random.choice(road_names),
            traffic_level=level,
            speed_kmh=random.uniform(10, 60),
            congestion_percent=random.uniform(0, 100),
            emoji=emojis[level],
            recorded_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
        )
        session.add(point)
        points.append(point)
    
    await session.flush()
    print(f"✓ {len(points)} trafik noktası oluşturuldu")
    return points


async def create_trash_bins(session):
    """Çöp kutuları oluştur"""
    print("\n🗑️ Çöp kutuları oluşturuluyor...")
    
    bins = []
    for i in range(15):
        lat, lon = random_point_in_bounds()
        
        bin = TrashBin(
            latitude=lat,
            longitude=lon,
            bin_type=random.choice(list(TrashBinType)),
            capacity_liters=random.choice([120, 240, 360]),
            fill_level=random.uniform(0, 100),
            has_sensor=random.choice([True, False]),
            sensor_id=f"SENSOR-{i+1:03d}" if random.choice([True, False]) else None,
            needs_maintenance=random.choice([True, False, False, False]),
            last_fill_update=datetime.utcnow() - timedelta(hours=random.randint(0, 24))
        )
        session.add(bin)
        bins.append(bin)
    
    await session.flush()
    print(f"✓ {len(bins)} çöp kutusu oluşturuldu")
    return bins


async def create_air_quality(session):
    """Hava kalitesi verileri oluştur"""
    print("\n🌫️ Hava kalitesi verileri oluşturuluyor...")
    
    readings = []
    for i in range(10):
        lat, lon = random_point_in_bounds()
        aqi = random.randint(20, 180)
        
        reading = AirQualityReading(
            latitude=lat,
            longitude=lon,
            station_name=f"İstasyon-{i+1}",
            aqi=aqi,
            level=AirQualityReading.get_level_for_aqi(aqi),
            pm25=random.uniform(5, 80),
            pm10=random.uniform(10, 120),
            o3=random.uniform(20, 100),
            no2=random.uniform(10, 60),
            color_code=AirQualityReading.get_color_for_aqi(aqi),
            recorded_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
        )
        session.add(reading)
        readings.append(reading)
    
    await session.flush()
    print(f"✓ {len(readings)} hava kalitesi ölçümü oluşturuldu")
    return readings


async def create_shadow_routes(session):
    """Gölgeli rotalar oluştur"""
    print("\n🌳 Gölgeli rotalar oluşturuluyor...")
    
    routes_data = [
        ("Park Yürüyüş Yolu", True, False, 75),
        ("Ağaçlı Cadde", True, True, 60),
        ("Gece Aydınlık Rota", False, True, 10),
        ("Kaldırım Yolu", True, True, 45),
    ]
    
    routes = []
    for name, is_shaded, is_lit, shade_pct in routes_data:
        start_lat, start_lon = random_point_in_bounds()
        end_lat, end_lon = random_point_in_bounds()
        
        # Basit LineString koordinatları
        import json
        coords = json.dumps([
            [start_lon, start_lat],
            [(start_lon + end_lon) / 2, (start_lat + end_lat) / 2],
            [end_lon, end_lat]
        ])
        
        route = ShadowRoute(
            name=name,
            description=f"{name} - {'Gölgeli' if is_shaded else ''} {'Aydınlık' if is_lit else ''} rota",
            coordinates=coords,
            start_latitude=start_lat,
            start_longitude=start_lon,
            end_latitude=end_lat,
            end_longitude=end_lon,
            distance_km=random.uniform(0.5, 2.0),
            estimated_walk_time_min=random.randint(5, 25),
            shade_percentage=shade_pct,
            is_shaded_route=is_shaded,
            is_lit_route=is_lit,
            is_accessible=random.choice([True, True, False])
        )
        session.add(route)
        routes.append(route)
    
    await session.flush()
    print(f"✓ {len(routes)} gölgeli rota oluşturuldu")
    return routes


async def create_safe_routes(session):
    """Güvenli tahliye rotaları oluştur"""
    print("\n🚨 Güvenli rotalar oluşturuluyor...")
    
    import json
    
    routes_data = [
        ("Toplanma Alanı 1 Rotası", "Nilüfer Meydanı"),
        ("Toplanma Alanı 2 Rotası", "Park Alanı"),
        ("Hastane Yolu", "Devlet Hastanesi"),
    ]
    
    routes = []
    for name, end_name in routes_data:
        start_lat, start_lon = random_point_in_bounds()
        end_lat, end_lon = random_point_in_bounds()
        
        coords = json.dumps([
            [start_lon, start_lat],
            [end_lon, end_lat]
        ])
        
        route = SafeRoute(
            name=name,
            description=f"{name} - Güvenli tahliye rotası",
            coordinates=coords,
            start_name="Başlangıç Noktası",
            start_latitude=start_lat,
            start_longitude=start_lon,
            end_name=end_name,
            end_latitude=end_lat,
            end_longitude=end_lon,
            distance_km=random.uniform(0.3, 1.5),
            estimated_walk_time_min=random.randint(3, 15),
            capacity_people=random.randint(100, 500),
            is_accessible=True
        )
        session.add(route)
        routes.append(route)
    
    await session.flush()
    print(f"✓ {len(routes)} güvenli rota oluşturuldu")
    return routes


async def main():
    """Ana fonksiyon"""
    print("=" * 50)
    print("Bursa Akıllı Şehir - Demo Veri Oluşturma")
    print("=" * 50)
    
    # Veritabanını başlat
    await init_db()
    
    async with AsyncSessionLocal() as session:
        try:
            # Kullanıcılar
            users = await create_users(session)
            citizen = users[2]  # Vatandaş kullanıcı
            
            # Şikayetler
            await create_complaints(session, citizen)
            
            # Trafik
            await create_traffic_points(session)
            
            # Çöp kutuları
            await create_trash_bins(session)
            
            # Hava kalitesi
            await create_air_quality(session)
            
            # Gölgeli rotalar
            await create_shadow_routes(session)
            
            # Güvenli rotalar
            await create_safe_routes(session)
            
            await session.commit()
            
            print("\n" + "=" * 50)
            print("✅ Tüm demo veriler başarıyla oluşturuldu!")
            print("=" * 50)
            
            print("\n📋 Giriş Bilgileri:")
            print("-" * 30)
            print("Admin: admin@bursa.bel.tr / admin123")
            print("Belediye: belediye@bursa.bel.tr / belediye123")
            print("Vatandaş: vatandas@example.com / vatandas123")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Hata: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())

