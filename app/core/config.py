"""
Uygulama Konfigürasyonu
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Uygulama ayarları"""
    
    # Uygulama
    APP_NAME: str = "Bursa Akıllı Şehir API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/bursa_smart_city"
    DATABASE_SYNC_URL: str = "postgresql://user:password@localhost:5432/bursa_smart_city"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI Service
    AI_SERVICE_URL: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Bursa City Center
    CITY_CENTER_LAT: float = 40.1885
    CITY_CENTER_LON: float = 29.0610
    CITY_RADIUS_KM: float = 30.0
    
    # Naim Süleymanoğlu Bulvarı koordinatları (yaklaşık)
    BOULEVARD_START_LAT: float = 40.2150
    BOULEVARD_START_LON: float = 28.9500
    BOULEVARD_END_LAT: float = 40.2200
    BOULEVARD_END_LON: float = 29.0000
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


settings = get_settings()

