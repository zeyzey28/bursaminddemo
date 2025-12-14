"""
API v1 Ana Router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    complaints,
    locations,
    traffic,
    # trash,      # Kaldırıldı
    # disaster,   # Kaldırıldı
    air_quality,
    shadow_routes,
    municipality,
    geojson_data,
    translations,
    traffic_risk,
    traffic_density
)

api_router = APIRouter()

# Kimlik doğrulama
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Kimlik Doğrulama"]
)

# Kullanıcı işlemleri
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Kullanıcılar"]
)

# Şikayetler (Vatandaş)
api_router.include_router(
    complaints.router,
    prefix="/complaints",
    tags=["Şikayetler"]
)

# Konum servisleri (Hastane, Eczane)
api_router.include_router(
    locations.router,
    prefix="/locations",
    tags=["Konumlar"]
)

# Trafik
api_router.include_router(
    traffic.router,
    prefix="/traffic",
    tags=["Trafik"]
)

# Çöp yönetimi (KALDIRILDI)
# api_router.include_router(
#     trash.router,
#     prefix="/trash",
#     tags=["Çöp Yönetimi"]
# )

# Afet modu (KALDIRILDI)
# api_router.include_router(
#     disaster.router,
#     prefix="/disaster",
#     tags=["Afet Yönetimi"]
# )

# Hava kalitesi
api_router.include_router(
    air_quality.router,
    prefix="/air-quality",
    tags=["Hava Kalitesi"]
)

# Gölgeli rotalar
api_router.include_router(
    shadow_routes.router,
    prefix="/shadow-routes",
    tags=["Gölgeli Rotalar"]
)

# Belediye paneli
api_router.include_router(
    municipality.router,
    prefix="/municipality",
    tags=["Belediye Paneli"]
)

# GeoJSON Verileri (Naim Süleymanoğlu Bulvarı)
api_router.include_router(
    geojson_data.router,
    prefix="/geojson",
    tags=["GeoJSON Verileri"]
)

# Çeviri servisi (Türkçe, İngilizce, Arapça)
api_router.include_router(
    translations.router,
    tags=["Çeviri"]
)

# Trafik yoğunluğu (Herkes için)
api_router.include_router(
    traffic_density.router,
    prefix="/traffic-density",
    tags=["Trafik Yoğunluğu"]
)

# Trafik risk analizi (isteğe bağlı - veri yoksa kapalı bırakılabilir)
# api_router.include_router(
#     traffic_risk.router,
#     prefix="/traffic-risk",
#     tags=["Trafik Risk Analizi"]
# )

