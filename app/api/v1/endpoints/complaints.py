"""
Şikayet Endpoint'leri - Vatandaş Paneli
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
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

router = APIRouter()


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni şikayet oluştur (fotoğraf ile birlikte)
    """
    # Kategori kontrolü
    try:
        category_enum = ComplaintCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz kategori. Geçerli kategoriler: {[c.value for c in ComplaintCategory]}"
        )
    
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
        priority=ComplaintPriority.MEDIUM
    )
    
    db.add(complaint)
    await db.flush()
    
    # Fotoğrafları kaydet
    if images:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        for image in images:
            if image.filename:
                # Dosya adı oluştur
                ext = os.path.splitext(image.filename)[1]
                file_name = f"{uuid.uuid4()}{ext}"
                file_path = os.path.join(settings.UPLOAD_DIR, file_name)
                
                # Dosyayı kaydet
                content = await image.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                
                # Veritabanına ekle
                complaint_image = ComplaintImage(
                    complaint_id=complaint.id,
                    file_path=file_path,
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


@router.get("/categories/list")
async def list_categories():
    """
    Şikayet kategorilerini listele
    """
    categories = {
        "road_damage": "Yol Hasarı",
        "lighting": "Aydınlatma Sorunu",
        "trash": "Çöp/Temizlik",
        "traffic": "Trafik Sorunu",
        "parking": "Park Sorunu",
        "noise": "Gürültü",
        "green_area": "Yeşil Alan",
        "water": "Su/Kanalizasyon",
        "air_quality": "Hava Kalitesi",
        "safety": "Güvenlik",
        "other": "Diğer"
    }
    return categories

