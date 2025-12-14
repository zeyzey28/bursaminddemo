"""
Şikayet Endpoint'leri - Vatandaş Paneli
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.complaint import Complaint, ComplaintImage, ComplaintStatus, ComplaintCategory, ComplaintPriority
from app.schemas.complaint import (
    ComplaintCreate, ComplaintResponse, ComplaintListResponse
)
from app.services.storage_service import storage_service
from app.services.complaint_ai_service import complaint_ai_service

router = APIRouter()


# ============================================
# PUBLIC ENDPOINTS (Authentication gerektirmez)
# ============================================

@router.get("/categories")
async def list_categories():
    """
    Şikayet kategorilerini listele (Frontend için - Public)
    """
    categories = [
        {"id": "road_damage", "name": "Yol Hasarı", "icon": "🛣️", "color": "#FF6B6B"},
        {"id": "lighting", "name": "Aydınlatma Sorunu", "icon": "💡", "color": "#FFD93D"},
        {"id": "traffic", "name": "Trafik Sorunu", "icon": "🚦", "color": "#4D96FF"},
        {"id": "parking", "name": "Park Sorunu", "icon": "🅿️", "color": "#9D84B7"},
        {"id": "noise", "name": "Gürültü", "icon": "🔊", "color": "#FF8E53"},
        {"id": "green_area", "name": "Yeşil Alan", "icon": "🌳", "color": "#4CAF50"},
        {"id": "water", "name": "Su/Kanalizasyon", "icon": "💧", "color": "#00BCD4"},
        {"id": "air_quality", "name": "Hava Kalitesi", "icon": "🌫️", "color": "#9E9E9E"},
        {"id": "safety", "name": "Güvenlik", "icon": "🚨", "color": "#F44336"},
        {"id": "other", "name": "Diğer", "icon": "📝", "color": "#607D8B"}
    ]
    
    return {
        "categories": categories,
        "total": len(categories)
    }


# ============================================
# AUTHENTICATED ENDPOINTS
# ============================================

@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    description: str = Form(...),
    category: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    title: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni şikayet oluştur (fotoğraf ile birlikte)
    
    Title opsiyonel - verilmezse description'dan otomatik oluşturulur
    """
    # Title oluştur (verilmemişse description'dan)
    if not title:
        title = description[:50] + "..." if len(description) > 50 else description
    
    # Kategori kontrolü
    try:
        category_enum = ComplaintCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz kategori. Geçerli kategoriler: {[c.value for c in ComplaintCategory]}"
        )
    
    # AI ile şikayeti sınıflandır ve skorla (async)
    ai_result = await complaint_ai_service.classify_complaint(
        title=title,
        description=description,
        user_category=category
    )
    
    # AI önerisi varsa kategoriyi güncelle
    if ai_result["ai_category_suggestion"]:
        try:
            suggested_category = ComplaintCategory(ai_result["ai_category_suggestion"])
            # Eğer AI güven skoru yüksekse, AI'nın önerisini kullan
            if ai_result["category_confidence"] > 0.7:
                category_enum = suggested_category
        except ValueError:
            pass  # AI önerisi geçersizse kullanıcının seçimini kullan
    
    # Priority'yi AI skoruna göre belirle
    priority_map = {
        "urgent": ComplaintPriority.URGENT,
        "high": ComplaintPriority.HIGH,
        "medium": ComplaintPriority.MEDIUM,
        "low": ComplaintPriority.LOW
    }
    priority = priority_map.get(ai_result["priority"], ComplaintPriority.MEDIUM)
    
    # Şikayet oluştur
    complaint = Complaint(
        user_id=int(current_user["user_id"]),
        title=title,
        description=description,
        category=category_enum,
        latitude=latitude,
        longitude=longitude,
        address=address,
        status=ComplaintStatus.PENDING,
        priority=priority,
        urgency_score=ai_result["urgency_score"],
        ai_verified=ai_result["ai_verified"],
        ai_verification_score=ai_result["ai_verification_score"],
        ai_category_suggestion=ai_result["ai_category_suggestion"]
    )
    
    db.add(complaint)
    await db.flush()
    
    # Fotoğrafları Supabase Storage'a kaydet
    if images:
        for image in images:
            if image.filename:
                try:
                    # Supabase Storage'a yükle
                    file_path, public_url = await storage_service.upload_image(
                        file=image,
                        folder=f"complaints/{complaint.id}"
                    )
                    
                    # Dosya boyutunu al
                    await image.seek(0)
                    content = await image.read()
                    file_size = len(content)
                    
                    # Veritabanına ekle
                    complaint_image = ComplaintImage(
                        complaint_id=complaint.id,
                        file_path=file_path,  # Supabase path
                        file_name=image.filename,
                        file_size=file_size,
                        mime_type=image.content_type
                    )
                    db.add(complaint_image)
                except Exception as e:
                    # Storage hatası durumunda yerel kaydet (fallback)
                    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
                    ext = os.path.splitext(image.filename)[1]
                    file_name = f"{uuid.uuid4()}{ext}"
                    local_path = os.path.join(settings.UPLOAD_DIR, file_name)
                    
                    await image.seek(0)
                    content = await image.read()
                    with open(local_path, "wb") as f:
                        f.write(content)
                    
                    complaint_image = ComplaintImage(
                        complaint_id=complaint.id,
                        file_path=local_path,
                        file_name=image.filename,
                        file_size=len(content),
                        mime_type=image.content_type
                    )
                    db.add(complaint_image)
    
    await db.flush()
    await db.refresh(complaint)
    
    # İlişkileri yükle
    result = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.images), selectinload(Complaint.feedbacks))
        .where(Complaint.id == complaint.id)
    )
    complaint = result.scalar_one()
    
    return ComplaintResponse.model_validate(complaint)


@router.get("/", response_model=ComplaintListResponse)
async def list_my_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    category_filter: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcının şikayetlerini listele
    """
    # Base query
    query = select(Complaint).where(
        Complaint.user_id == int(current_user["user_id"])
    )
    
    # Filtreler
    if status_filter:
        query = query.where(Complaint.status == status_filter)
    if category_filter:
        query = query.where(Complaint.category == category_filter)
    
    # Toplam sayı
    count_query = select(func.count(Complaint.id)).where(
        Complaint.user_id == int(current_user["user_id"])
    )
    if status_filter:
        count_query = count_query.where(Complaint.status == status_filter)
    if category_filter:
        count_query = count_query.where(Complaint.category == category_filter)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Sayfalama
    offset = (page - 1) * page_size
    query = query.options(
        selectinload(Complaint.images),
        selectinload(Complaint.feedbacks)
    ).order_by(Complaint.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    complaints = result.scalars().all()
    
    return ComplaintListResponse(
        items=[ComplaintResponse.model_validate(c) for c in complaints],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayet detayını getir
    """
    result = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.images), selectinload(Complaint.feedbacks))
        .where(
            and_(
                Complaint.id == complaint_id,
                Complaint.user_id == int(current_user["user_id"])
            )
        )
    )
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Şikayet bulunamadı"
        )
    
    return ComplaintResponse.model_validate(complaint)


@router.get("/image/{image_id}")
async def get_complaint_image(
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayet fotoğrafını getir (redirect to Supabase URL)
    """
    result = await db.execute(
        select(ComplaintImage).where(ComplaintImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fotoğraf bulunamadı"
        )
    
    # Supabase Storage URL'i oluştur
    if image.file_path.startswith("complaints/"):
        # Supabase'de kayıtlı
        public_url = storage_service.get_public_url(image.file_path)
        return RedirectResponse(url=public_url)
    else:
        # Yerel dosya (fallback)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fotoğraf yerel sunucuda. Supabase Storage kullanın."
        )

