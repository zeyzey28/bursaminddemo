"""
Admin Kullanıcı Oluşturma Script'i

Kullanıcı adı + Şifre ile giriş sistemi

Kullanım:
    python scripts/create_admin.py
    python scripts/create_admin.py --all
    python scripts/create_admin.py admin sifre123 "Admin Adı"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole


async def create_admin(
    username: str = "admin",
    password: str = "admin123",
    full_name: str = "Sistem Yöneticisi"
):
    """Admin kullanıcı oluştur"""
    
    print("=" * 50)
    print("Bursa Akıllı Şehir - Admin Oluşturma")
    print("=" * 50)
    
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Mevcut kontrol
        result = await session.execute(
            select(User).where(User.username == username)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"\n⚠️  Bu kullanıcı adı zaten kayıtlı: {username}")
            print(f"    Rol: {existing.role.value}")
            print(f"    Aktif: {'Evet' if existing.is_active else 'Hayır'}")
            return
        
        # Admin oluştur
        admin = User(
            username=username,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        session.add(admin)
        await session.commit()
        
        print(f"\n✅ Admin kullanıcı oluşturuldu!")
        print("-" * 30)
        print(f"   Kullanıcı Adı: {username}")
        print(f"   Şifre: {password}")
        print(f"   Ad: {full_name}")
        print(f"   Rol: ADMIN")
        print("-" * 30)
        print("\n📌 Bu bilgilerle PERSONEL GİRİŞİ'nden giriş yapabilirsiniz.")


async def create_default_users():
    """Varsayılan kullanıcıları oluştur (test için)"""
    
    print("=" * 50)
    print("Bursa Akıllı Şehir - Varsayılan Kullanıcılar")
    print("=" * 50)
    
    await init_db()
    
    users_to_create = [
        {
            "username": "admin",
            "password": "admin123",
            "full_name": "Sistem Yöneticisi",
            "role": UserRole.ADMIN
        },
        {
            "username": "personel1",
            "password": "personel123",
            "full_name": "Ahmet Yılmaz",
            "role": UserRole.MUNICIPALITY
        },
        {
            "username": "personel2",
            "password": "personel123",
            "full_name": "Ayşe Demir",
            "role": UserRole.MUNICIPALITY
        },
        {
            "username": "vatandas1",
            "password": "vatandas123",
            "full_name": "Mehmet Kaya",
            "role": UserRole.CITIZEN
        }
    ]
    
    async with AsyncSessionLocal() as session:
        created = 0
        
        for user_data in users_to_create:
            # Mevcut kontrol
            result = await session.execute(
                select(User).where(User.username == user_data["username"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⏭️  Atlandı (mevcut): {user_data['username']}")
                continue
            
            # Oluştur
            user = User(
                username=user_data["username"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True,
                is_verified=True
            )
            
            session.add(user)
            created += 1
            print(f"✅ Oluşturuldu: {user_data['username']} ({user_data['role'].value})")
        
        await session.commit()
        
        print("\n" + "=" * 50)
        print(f"Toplam {created} kullanıcı oluşturuldu")
        print("=" * 50)
        
        print("\n📋 Giriş Bilgileri:")
        print("-" * 40)
        print("PERSONEL GİRİŞİ:")
        print("  Admin     → admin / admin123")
        print("  Personel  → personel1 / personel123")
        print("  Personel  → personel2 / personel123")
        print("")
        print("KULLANICI GİRİŞİ:")
        print("  Vatandaş  → vatandas1 / vatandas123")
        print("-" * 40)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Tüm varsayılan kullanıcıları oluştur
            asyncio.run(create_default_users())
        else:
            # Özel admin oluştur
            username = sys.argv[1]
            password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
            full_name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
            asyncio.run(create_admin(username, password, full_name))
    else:
        # Varsayılan admin
        asyncio.run(create_admin())
