# 🏙️ Bursa Akıllı Şehir Backend

Naim Süleymanoğlu Bulvarı için iki panelli Akıllı Şehir sistemi backend'i.

## 📋 Özellikler

### Kullanıcı Paneli
- 🗺️ 3D harita üzerinde trafik yoğunluğu (duygu ikonları ile)
- 🌫️ Hava kirliliği heatmap
- 🌳 Gölgeli/aydınlık yürüyüş rotaları
- 🚨 Afet modunda güvenli yollar
- 📸 AI doğrulamalı şikayet sistemi
- 🏥 Yakındaki hastane ve eczaneler

### Belediye Paneli
- 📊 Şikayet analizi (günlük/haftalık/aylık)
- 💬 Geri bildirim sistemi
- 🎯 Aciliyet skorları (renklendirilmiş)
- 🗑️ Çöp doluluk takibi
- 🚛 Optimize çöp toplama rotaları (benzin/km)
- 🚧 Afet modu yönetimi

## 🚀 Hızlı Başlangıç

### Docker ile (Önerilen)

```bash
# Projeyi klonla
git clone <repo-url>
cd bursa_backend

# Docker ile başlat
docker-compose up -d

# Logları izle
docker-compose logs -f api
```

API şu adreste çalışacak: http://localhost:8000

### Manuel Kurulum

```bash
# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# PostgreSQL ve Redis'in çalıştığından emin ol
# .env dosyasını oluştur (env.example'dan kopyala)
cp env.example .env

# Veritabanını başlat
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"

# Demo verileri yükle (opsiyonel)
python scripts/seed_demo_data.py

# Sunucuyu başlat
uvicorn app.main:app --reload
```

## 📁 Proje Yapısı

```
bursa_backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoint'leri
│   │       └── router.py       # Ana router
│   ├── core/
│   │   ├── config.py          # Konfigürasyon
│   │   ├── database.py        # Veritabanı bağlantısı
│   │   └── security.py        # JWT & Auth
│   ├── models/                # SQLAlchemy modelleri
│   ├── schemas/               # Pydantic şemaları
│   ├── services/              # İş mantığı servisleri
│   │   ├── ai_service.py      # AI görüntü analizi
│   │   ├── geojson_loader.py  # GeoJSON veri yükleme
│   │   └── route_optimizer.py # Rota optimizasyonu
│   └── main.py               # FastAPI uygulaması
├── scripts/
│   ├── load_data.py          # GeoJSON veri yükleme
│   ├── seed_demo_data.py     # Demo veri oluşturma
│   └── create_admin.py       # Admin kullanıcı oluşturma
├── data/                     # GeoJSON dosyaları
├── alembic/                  # Veritabanı migration'ları
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 🔌 API Endpoint'leri

### Kimlik Doğrulama
- `POST /api/v1/auth/register` - Kayıt
- `POST /api/v1/auth/login` - Giriş
- `GET /api/v1/auth/me` - Mevcut kullanıcı

### Şikayetler
- `POST /api/v1/complaints/` - Şikayet oluştur (fotoğraf ile)
- `GET /api/v1/complaints/` - Şikayetlerimi listele
- `GET /api/v1/complaints/{id}` - Şikayet detayı

### Konumlar
- `GET /api/v1/locations/hospitals` - Hastaneler
- `GET /api/v1/locations/pharmacies` - Eczaneler
- `GET /api/v1/locations/nearby` - Yakındaki yerler
- `GET /api/v1/locations/hospitals/geojson` - GeoJSON formatı

### Trafik
- `GET /api/v1/traffic/` - Trafik noktaları
- `GET /api/v1/traffic/geojson` - GeoJSON (duygu ikonları)
- `GET /api/v1/traffic/summary` - Trafik özeti

### Hava Kalitesi
- `GET /api/v1/air-quality/current` - Güncel veriler
- `GET /api/v1/air-quality/heatmap` - Heatmap verisi
- `GET /api/v1/air-quality/stats` - İstatistikler

### Gölgeli Rotalar
- `GET /api/v1/shadow-routes/` - Rota listesi
- `GET /api/v1/shadow-routes/geojson` - GeoJSON
- `POST /api/v1/shadow-routes/find` - Rota bul

### Afet Yönetimi
- `GET /api/v1/disaster/status` - Afet durumu
- `GET /api/v1/disaster/safe-routes` - Güvenli rotalar
- `GET /api/v1/disaster/blocked-roads` - Kapalı yollar
- `GET /api/v1/disaster/dashboard` - Dashboard

### Çöp Yönetimi
- `GET /api/v1/trash/bins` - Çöp kutuları
- `GET /api/v1/trash/bins/geojson` - GeoJSON
- `POST /api/v1/trash/routes/optimize` - Rota optimize et
- `GET /api/v1/trash/dashboard` - Dashboard

### Belediye Paneli
- `GET /api/v1/municipality/complaints` - Tüm şikayetler
- `PUT /api/v1/municipality/complaints/{id}` - Şikayet güncelle
- `POST /api/v1/municipality/complaints/{id}/feedback` - Geri bildirim
- `GET /api/v1/municipality/complaints/stats/overview` - İstatistikler
- `GET /api/v1/municipality/dashboard` - Dashboard

## 📊 Veritabanı Şeması

### Ana Tablolar
- `users` - Kullanıcılar (vatandaş, belediye, admin)
- `complaints` - Şikayetler
- `complaint_images` - Şikayet görselleri
- `complaint_feedbacks` - Geri bildirimler
- `hospitals` - Hastaneler
- `pharmacies` - Eczaneler
- `traffic_points` - Trafik noktaları
- `trash_bins` - Çöp kutuları
- `trash_routes` - Çöp toplama rotaları
- `air_quality_readings` - Hava kalitesi ölçümleri
- `shadow_routes` - Gölgeli rotalar
- `disaster_modes` - Afet modları
- `safe_routes` - Güvenli rotalar
- `blocked_roads` - Kapalı yollar

## 🔐 Kullanıcı Rolleri

| Rol | Açıklama |
|-----|----------|
| `citizen` | Vatandaş - Şikayet oluşturma, harita görüntüleme |
| `municipality` | Belediye personeli - Şikayet yönetimi, dashboard |
| `admin` | Yönetici - Tüm yetkiler |

## 📦 GeoJSON Veri Yükleme

```bash
# Hastane ve eczane verilerini yükle
python scripts/load_data.py

# Veya manuel olarak
python -c "
from app.services.geojson_loader import GeoJSONLoader
import asyncio

async def load():
    await GeoJSONLoader.load_hospitals_from_geojson('data/hastane.geojson')
    await GeoJSONLoader.load_pharmacies_from_geojson('data/eczane.geojson')

asyncio.run(load())
"
```

## 🧪 Test

```bash
# Test'leri çalıştır
pytest

# Coverage ile
pytest --cov=app
```

## 📝 Ortam Değişkenleri

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `DATABASE_URL` | PostgreSQL bağlantı URL'i | - |
| `REDIS_URL` | Redis bağlantı URL'i | - |
| `SECRET_KEY` | JWT secret key | - |
| `AI_API_KEY` | OpenAI API key (opsiyonel) | - |
| `DEBUG` | Debug modu | `true` |

## 🚀 Deployment

### Production için

```bash
# .env dosyasını production değerleriyle güncelle
# docker-compose.prod.yml kullan
docker-compose -f docker-compose.prod.yml up -d
```

## 📄 Lisans

MIT License

## 👥 Katkıda Bulunanlar

- Backend Geliştirici: [İsim]
- Frontend Geliştirici: [İsim]

---

**Yarışma:** Akıllı Şehir Hackathon 2025
**Proje:** Naim Süleymanoğlu Bulvarı Akıllı Şehir Sistemi

