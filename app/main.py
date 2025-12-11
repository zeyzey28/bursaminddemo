"""
Bursa Akıllı Şehir API - Ana Uygulama
Naim Süleymanoğlu Bulvarı Akıllı Şehir Sistemi Backend
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü"""
    # Başlangıç
    print("🚀 Bursa Akıllı Şehir API başlatılıyor...")
    
    # Veritabanı tablolarını oluştur
    await init_db()
    print("✓ Veritabanı hazır")
    
    # Upload dizinini oluştur
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"✓ Upload dizini: {settings.UPLOAD_DIR}")
    
    yield
    
    # Kapanış
    print("👋 Uygulama kapatılıyor...")
    await close_db()


# FastAPI uygulaması
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Bursa Akıllı Şehir API
    
    Naim Süleymanoğlu Bulvarı için iki panelli Akıllı Şehir sistemi backend'i.
    
    ### Özellikler
    
    **Kullanıcı Paneli:**
    - 🗺️ 3D harita üzerinde trafik yoğunluğu (duygu ikonları)
    - 🌫️ Hava kirliliği heatmap
    - 🌳 Gölgeli/aydınlık yürüyüş rotaları
    - 🚨 Afet modunda güvenli yollar
    - 📸 AI doğrulamalı şikayet sistemi
    - 🏥 Yakındaki hastane ve eczaneler
    
    **Belediye Paneli:**
    - 📊 Şikayet analizi (günlük/haftalık/aylık)
    - 💬 Geri bildirim sistemi
    - 🎯 Aciliyet skorları
    - 🗑️ Çöp doluluk takibi
    - 🚛 Optimize çöp toplama rotaları
    - 🚧 Afet modu yönetimi
    
    ### API Versiyonu
    v1.0.0
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (uploads)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API Router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API durumu"""
    return {
        "message": "Bursa Akıllı Şehir API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "active"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Sağlık kontrolü"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }


# Hata yakalama
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global hata yakalayıcı"""
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Sunucu hatası oluştu",
            "error": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

