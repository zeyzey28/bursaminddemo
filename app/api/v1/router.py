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
    trash,
    disaster,
    air_quality,
    shadow_routes,
    municipality
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

# Çöp yönetimi
api_router.include_router(
    trash.router,
    prefix="/trash",
    tags=["Çöp Yönetimi"]
)

# Afet modu
api_router.include_router(
    disaster.router,
    prefix="/disaster",
    tags=["Afet Yönetimi"]
)

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

