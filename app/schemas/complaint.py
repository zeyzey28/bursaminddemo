"""
Şikayet Şemaları
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ComplaintBase(BaseModel):
    """Temel şikayet şeması"""
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    category: str
    latitude: float
    longitude: float
    address: Optional[str] = None


class ComplaintCreate(ComplaintBase):
    """Şikayet oluşturma"""
    pass


class ComplaintUpdate(BaseModel):
    """Şikayet güncelleme (belediye için)"""
    status: Optional[str] = None
    priority: Optional[str] = None
    urgency_score: Optional[float] = None


class ComplaintImageResponse(BaseModel):
    """Şikayet görseli yanıtı"""
    id: int
    file_path: str
    file_name: str
    ai_analysis: Optional[str] = None
    ai_tags: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComplaintFeedbackCreate(BaseModel):
    """Geri bildirim oluşturma"""
    message: str = Field(..., min_length=5)
    new_status: Optional[str] = None


class ComplaintFeedbackResponse(BaseModel):
    """Geri bildirim yanıtı"""
    id: int
    message: str
    new_status: Optional[str] = None
    created_at: datetime
    municipality_user_id: int
    
    class Config:
        from_attributes = True


class ComplaintResponse(ComplaintBase):
    """Şikayet yanıt şeması"""
    id: int
    user_id: int
    status: str
    priority: str
    urgency_score: float
    ai_verified: bool
    ai_verification_score: Optional[float] = None
    ai_category_suggestion: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    images: List[ComplaintImageResponse] = []
    feedbacks: List[ComplaintFeedbackResponse] = []
    
    class Config:
        from_attributes = True


class ComplaintListResponse(BaseModel):
    """Şikayet listesi yanıtı"""
    items: List[ComplaintResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComplaintStats(BaseModel):
    """Şikayet istatistikleri"""
    total_complaints: int
    pending: int
    in_progress: int
    resolved: int
    rejected: int
    
    # Kategori bazlı
    by_category: dict
    
    # Öncelik bazlı
    by_priority: dict
    
    # Zaman bazlı
    today: int
    this_week: int
    this_month: int
    
    # Ortalama çözüm süresi (saat)
    avg_resolution_time_hours: Optional[float] = None

