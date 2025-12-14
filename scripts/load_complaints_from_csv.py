"""
CSV'den Şikayet Verilerini Yükle
"""
import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintCategory, ComplaintStatus, ComplaintPriority

# CSV'deki kategori isimlerini DB enum'larına map
CATEGORY_MAP = {
    "Yol Hasarı": ComplaintCategory.ROAD_DAMAGE,
    "road_damage": ComplaintCategory.ROAD_DAMAGE,
    "Aydınlatma Sorunu": ComplaintCategory.LIGHTING,
    "lighting": ComplaintCategory.LIGHTING,
    "Çöp/Temizlik": ComplaintCategory.TRASH,
    "trash": ComplaintCategory.TRASH,
    "Trafik Sorunu": ComplaintCategory.TRAFFIC,
    "traffic": ComplaintCategory.TRAFFIC,
    "Park Sorunu": ComplaintCategory.PARKING,
    "parking": ComplaintCategory.PARKING,
    "Gürültü": ComplaintCategory.NOISE,
    "noise": ComplaintCategory.NOISE,
    "Yeşil Alan": ComplaintCategory.GREEN_AREA,
    "green_area": ComplaintCategory.GREEN_AREA,
    "Su/Kanalizasyon": ComplaintCategory.WATER,
    "water": ComplaintCategory.WATER,
    "Hava Kalitesi": ComplaintCategory.AIR_QUALITY,
    "air_quality": ComplaintCategory.AIR_QUALITY,
    "Güvenlik": ComplaintCategory.SAFETY,
    "safety": ComplaintCategory.SAFETY,
    "Diğer": ComplaintCategory.OTHER,
    "other": ComplaintCategory.OTHER,
}


def urgency_to_priority(urgency_score: float) -> ComplaintPriority:
    """Urgency score'dan priority'ye çevir"""
    if urgency_score >= 80:
        return ComplaintPriority.URGENT
    elif urgency_score >= 60:
        return ComplaintPriority.HIGH
    elif urgency_score >= 40:
        return ComplaintPriority.MEDIUM
    else:
        return ComplaintPriority.LOW


async def get_or_create_demo_user(session: AsyncSession) -> User:
    """Demo kullanıcıyı al veya oluştur"""
    result = await session.execute(
        select(User).where(User.email == "vatandas@example.com")
    )
    user = result.scalar_one_or_none()
    
    if not user:
        from app.core.security import get_password_hash
        user = User(
            username="vatandas",
            email="vatandas@example.com",
            hashed_password=get_password_hash("vatandas123"),
            full_name="Demo Vatandaş",
            role=UserRole.CITIZEN,
            is_verified=True
        )
        session.add(user)
        await session.flush()
    
    return user


async def load_complaints_from_csv(csv_path: Path):
    """CSV'den şikayet verilerini yükle"""
    if not csv_path.exists():
        print(f"❌ CSV dosyası bulunamadı: {csv_path}")
        return
    
    async with AsyncSessionLocal() as session:
        # Demo kullanıcıyı al
        user = await get_or_create_demo_user(session)
        
        count = 0
        skipped = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Kategoriyi map et
                    true_category = row.get("true_category_tr") or row.get("true_category_id", "").lower()
                    category = CATEGORY_MAP.get(true_category)
                    
                    if not category:
                        # Fallback: user_category_tr'ye bak
                        user_category = row.get("user_category_tr", "")
                        category = CATEGORY_MAP.get(user_category, ComplaintCategory.OTHER)
                    
                    # Urgency score'u al (0-100'den 0-1'e çevir)
                    urgency_score = float(row.get("urgency_score", 50)) / 100.0
                    urgency_score = max(0.0, min(1.0, urgency_score))  # Clamp to 0-1
                    
                    # Priority'yi urgency'den belirle
                    priority = urgency_to_priority(float(row.get("urgency_score", 50)))
                    
                    # Başlık oluştur (description'dan ilk 50 karakter)
                    description = row.get("text", "").strip()
                    if not description:
                        skipped += 1
                        continue
                    
                    title = description[:50] + ("..." if len(description) > 50 else "")
                    
                    # Zaman damgası (rastgele son 30 gün içinde)
                    import random
                    from datetime import timedelta
                    days_ago = random.randint(0, 30)
                    created_at = datetime.utcnow() - timedelta(days=days_ago)
                    
                    complaint = Complaint(
                        user_id=user.id,
                        title=title,
                        description=description,
                        category=category,
                        latitude=float(row.get("lat", 40.2175)),
                        longitude=float(row.get("lon", 28.9750)),
                        address=None,
                        status=ComplaintStatus.PENDING,
                        priority=priority,
                        urgency_score=urgency_score,
                        ai_verified=False,
                        ai_verification_score=None,
                        ai_category_suggestion=category.value,
                        created_at=created_at,
                        updated_at=created_at
                    )
                    
                    session.add(complaint)
                    count += 1
                    
                    # Her 100 kayıtta bir commit
                    if count % 100 == 0:
                        await session.commit()
                        print(f"  ✓ {count} şikayet yüklendi...")
                
                except Exception as e:
                    print(f"  ⚠️ Hata (satır {count + skipped + 1}): {e}")
                    skipped += 1
                    continue
        
        await session.commit()
        print(f"\n✅ {count} şikayet başarıyla yüklendi")
        if skipped > 0:
            print(f"⚠️ {skipped} şikayet atlandı")


async def main():
    """Ana fonksiyon"""
    csv_path = Path("/Users/zeynepogulcan/Desktop/cagri/bursa_complaints_dev.csv")
    
    print("=" * 50)
    print("🚀 Şikayet Verileri Yükleniyor...")
    print("=" * 50)
    
    await load_complaints_from_csv(csv_path)
    
    print("=" * 50)
    print("✅ İşlem tamamlandı!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

