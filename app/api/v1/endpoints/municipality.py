"""
Belediye Paneli Endpoint'leri
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_municipality
from app.models.complaint import Complaint, ComplaintFeedback, ComplaintImage, ComplaintStatus, ComplaintPriority
from app.models.user import User
from app.schemas.complaint import (
    ComplaintResponse, ComplaintUpdate, ComplaintListResponse,
    ComplaintFeedbackCreate, ComplaintFeedbackResponse, ComplaintStats
)
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/complaints", response_model=ComplaintListResponse)
async def list_all_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    category_filter: Optional[str] = Query(None),
    priority_filter: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_by: str = Query("created_at", description="created_at, urgency_score, priority"),
    sort_order: str = Query("desc", description="asc veya desc"),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Tüm şikayetleri listele (Belediye paneli)
    """
    query = select(Complaint)
    count_query = select(func.count(Complaint.id))
    
    # Filtreler
    filters = []
    
    if status_filter:
        filters.append(Complaint.status == status_filter)
    if category_filter:
        filters.append(Complaint.category == category_filter)
    if priority_filter:
        filters.append(Complaint.priority == priority_filter)
    if date_from:
        filters.append(Complaint.created_at >= date_from)
    if date_to:
        filters.append(Complaint.created_at <= date_to)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Sıralama
    if sort_by == "urgency_score":
        order_col = Complaint.urgency_score
    elif sort_by == "priority":
        order_col = Complaint.priority
    else:
        order_col = Complaint.created_at
    
    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    # Toplam
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Sayfalama
    offset = (page - 1) * page_size
    query = query.options(
        selectinload(Complaint.images),
        selectinload(Complaint.feedbacks)
    ).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    complaints = result.scalars().all()
    
    return ComplaintListResponse(
        items=[ComplaintResponse.model_validate(c) for c in complaints],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint_detail(
    complaint_id: int,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayet detayını getir
    """
    result = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.images), selectinload(Complaint.feedbacks))
        .where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Şikayet bulunamadı"
        )
    
    return ComplaintResponse.model_validate(complaint)


@router.put("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: int,
    update_data: ComplaintUpdate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayet durumunu güncelle
    """
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Şikayet bulunamadı"
        )
    
    if update_data.status:
        complaint.status = update_data.status
        if update_data.status == "resolved":
            complaint.resolved_at = datetime.utcnow()
    
    if update_data.priority:
        complaint.priority = update_data.priority
    
    if update_data.urgency_score is not None:
        complaint.urgency_score = update_data.urgency_score
    
    await db.flush()
    
    # Yeniden yükle
    result = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.images), selectinload(Complaint.feedbacks))
        .where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one()
    
    return ComplaintResponse.model_validate(complaint)


@router.post("/complaints/{complaint_id}/feedback", response_model=ComplaintFeedbackResponse)
async def add_feedback(
    complaint_id: int,
    feedback_data: ComplaintFeedbackCreate,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayete geri bildirim ekle
    
    Örnek mesajlar:
    - "Şikayetiniz alınmıştır."
    - "Şikayetiniz işlemdedir."
    - "Şikayetiniz sonuçlanmıştır. İlginiz için teşekkür ederiz."
    """
    # Şikayeti kontrol et
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Şikayet bulunamadı"
        )
    
    # Geri bildirim oluştur
    feedback = ComplaintFeedback(
        complaint_id=complaint_id,
        municipality_user_id=int(current_user["user_id"]),
        message=feedback_data.message,
        new_status=feedback_data.new_status
    )
    
    db.add(feedback)
    
    # Durumu güncelle
    if feedback_data.new_status:
        complaint.status = feedback_data.new_status
        if feedback_data.new_status == "resolved":
            complaint.resolved_at = datetime.utcnow()
    
    await db.flush()
    await db.refresh(feedback)
    
    return ComplaintFeedbackResponse.model_validate(feedback)


@router.get("/complaints/stats/overview", response_model=ComplaintStats)
async def get_complaint_stats(
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayet istatistikleri - Günlük/Haftalık/Aylık analiz
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    
    # Toplam şikayetler
    total_result = await db.execute(select(func.count(Complaint.id)))
    total = total_result.scalar()
    
    # Durum bazlı
    status_counts = {}
    for status in ComplaintStatus:
        result = await db.execute(
            select(func.count(Complaint.id)).where(Complaint.status == status)
        )
        status_counts[status.value] = result.scalar()
    
    # Kategori bazlı
    category_result = await db.execute(
        select(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
    )
    by_category = {str(cat): count for cat, count in category_result.all()}
    
    # Öncelik bazlı
    priority_result = await db.execute(
        select(Complaint.priority, func.count(Complaint.id))
        .group_by(Complaint.priority)
    )
    by_priority = {str(pri): count for pri, count in priority_result.all()}
    
    # Bugün
    today_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.created_at >= today_start)
    )
    today_count = today_result.scalar()
    
    # Bu hafta
    week_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.created_at >= week_start)
    )
    week_count = week_result.scalar()
    
    # Bu ay
    month_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.created_at >= month_start)
    )
    month_count = month_result.scalar()
    
    # Ortalama çözüm süresi
    resolved_result = await db.execute(
        select(Complaint)
        .where(
            and_(
                Complaint.status == ComplaintStatus.RESOLVED,
                Complaint.resolved_at.isnot(None)
            )
        )
    )
    resolved_complaints = resolved_result.scalars().all()
    
    if resolved_complaints:
        total_hours = sum(
            (c.resolved_at - c.created_at).total_seconds() / 3600
            for c in resolved_complaints
        )
        avg_resolution = total_hours / len(resolved_complaints)
    else:
        avg_resolution = None
    
    return ComplaintStats(
        total_complaints=total,
        pending=status_counts.get("pending", 0),
        in_progress=status_counts.get("in_progress", 0),
        resolved=status_counts.get("resolved", 0),
        rejected=status_counts.get("rejected", 0),
        by_category=by_category,
        by_priority=by_priority,
        today=today_count,
        this_week=week_count,
        this_month=month_count,
        avg_resolution_time_hours=round(avg_resolution, 1) if avg_resolution else None
    )


@router.get("/complaints/urgent")
async def get_urgent_complaints(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Acil şikayetleri getir (yüksek aciliyet skoru)
    """
    result = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.images))
        .where(
            and_(
                Complaint.status.in_([ComplaintStatus.PENDING, ComplaintStatus.RECEIVED]),
                Complaint.urgency_score >= 0.7
            )
        )
        .order_by(Complaint.urgency_score.desc())
        .limit(limit)
    )
    complaints = result.scalars().all()
    
    return {
        "urgent_complaints": [ComplaintResponse.model_validate(c) for c in complaints],
        "total_urgent": len(complaints)
    }


@router.get("/complaints/heatmap")
async def get_complaints_heatmap(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Şikayet yoğunluk haritası verisi
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(Complaint)
        .where(Complaint.created_at >= start_date)
    )
    complaints = result.scalars().all()
    
    # Konum bazlı grupla
    heatmap_data = []
    for complaint in complaints:
        # Aciliyet skoruna göre yoğunluk
        intensity = complaint.urgency_score
        
        # Durum rengini belirle
        if complaint.status == ComplaintStatus.PENDING:
            color = "#FF0000"  # Kırmızı
        elif complaint.status == ComplaintStatus.IN_PROGRESS:
            color = "#FFA500"  # Turuncu
        elif complaint.status == ComplaintStatus.RESOLVED:
            color = "#00FF00"  # Yeşil
        else:
            color = "#808080"  # Gri
        
        heatmap_data.append({
            "latitude": complaint.latitude,
            "longitude": complaint.longitude,
            "intensity": intensity,
            "color": color,
            "category": complaint.category.value,
            "status": complaint.status.value
        })
    
    return {
        "heatmap_data": heatmap_data,
        "total_points": len(heatmap_data),
        "period_days": days
    }


@router.get("/dashboard")
async def get_municipality_dashboard(
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Belediye dashboard özeti
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Bugünkü yeni şikayetler
    new_today = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.created_at >= today_start)
    )
    
    # Bekleyen şikayetler
    pending = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == ComplaintStatus.PENDING)
    )
    
    # İşlemdeki şikayetler
    in_progress = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == ComplaintStatus.IN_PROGRESS)
    )
    
    # Bugün çözülenler
    resolved_today = await db.execute(
        select(func.count(Complaint.id)).where(
            and_(
                Complaint.resolved_at >= today_start,
                Complaint.status == ComplaintStatus.RESOLVED
            )
        )
    )
    
    # Acil şikayetler
    urgent = await db.execute(
        select(func.count(Complaint.id)).where(
            and_(
                Complaint.urgency_score >= 0.7,
                Complaint.status.in_([ComplaintStatus.PENDING, ComplaintStatus.RECEIVED])
            )
        )
    )
    
    return {
        "new_complaints_today": new_today.scalar(),
        "pending_complaints": pending.scalar(),
        "in_progress_complaints": in_progress.scalar(),
        "resolved_today": resolved_today.scalar(),
        "urgent_complaints": urgent.scalar(),
        "timestamp": now.isoformat()
    }


# ============================================
# FOTOĞRAF YÖNETİMİ - Belediye
# ============================================

@router.get("/images/report")
async def get_images_report(
    period: str = Query("daily", description="daily, weekly, monthly, yearly"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    category: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Fotoğraf raporu - Günlük/Haftalık/Aylık/Yıllık
    
    Belediye bu endpoint ile belirli dönemdeki tüm şikayet
    fotoğraflarını listeleyebilir ve indirebilir.
    """
    now = datetime.utcnow()
    
    # Dönem hesapla
    if date_from and date_to:
        start_date = date_from
        end_date = date_to
    else:
        if period == "daily":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == "weekly":
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == "monthly":
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == "yearly":
            start_date = now - timedelta(days=365)
            end_date = now
        else:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
    
    # Şikayetleri ve fotoğrafları getir
    query = select(Complaint).options(
        selectinload(Complaint.images)
    ).where(
        and_(
            Complaint.created_at >= start_date,
            Complaint.created_at <= end_date
        )
    )
    
    if category:
        query = query.where(Complaint.category == category)
    
    result = await db.execute(query.order_by(Complaint.created_at.desc()))
    complaints = result.scalars().all()
    
    # Fotoğraf listesi oluştur
    images_data = []
    for complaint in complaints:
        for image in complaint.images:
            # Public URL oluştur
            if image.file_path.startswith("complaints/"):
                public_url = storage_service.get_public_url(image.file_path)
            else:
                public_url = None  # Yerel dosya
            
            images_data.append({
                "image_id": image.id,
                "complaint_id": complaint.id,
                "complaint_title": complaint.title,
                "category": complaint.category.value,
                "status": complaint.status.value,
                "file_name": image.file_name,
                "file_size": image.file_size,
                "mime_type": image.mime_type,
                "public_url": public_url,
                "created_at": image.created_at.isoformat() if image.created_at else None,
                "complaint_date": complaint.created_at.isoformat()
            })
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_complaints": len(complaints),
        "total_images": len(images_data),
        "images": images_data
    }


@router.get("/images/{image_id}")
async def get_image(
    image_id: int,
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Tek bir fotoğrafı getir (Belediye)
    """
    result = await db.execute(
        select(ComplaintImage)
        .options(selectinload(ComplaintImage.complaint))
        .where(ComplaintImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fotoğraf bulunamadı"
        )
    
    # Supabase Storage URL'i
    if image.file_path.startswith("complaints/"):
        public_url = storage_service.get_public_url(image.file_path)
        return RedirectResponse(url=public_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fotoğraf bulunamadı veya erişilemiyor"
        )


@router.get("/images/download-all")
async def get_download_urls(
    period: str = Query("daily", description="daily, weekly, monthly, yearly"),
    current_user: dict = Depends(get_current_municipality),
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli dönemdeki tüm fotoğrafların indirme linklerini getir
    
    Bu endpoint ile belediye tüm fotoğrafları toplu olarak
    indirebilir.
    """
    now = datetime.utcnow()
    
    if period == "daily":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        start_date = now - timedelta(days=7)
    elif period == "monthly":
        start_date = now - timedelta(days=30)
    elif period == "yearly":
        start_date = now - timedelta(days=365)
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Tüm fotoğrafları getir
    result = await db.execute(
        select(ComplaintImage)
        .join(Complaint)
        .where(Complaint.created_at >= start_date)
        .order_by(ComplaintImage.created_at.desc())
    )
    images = result.scalars().all()
    
    download_links = []
    for image in images:
        if image.file_path.startswith("complaints/"):
            download_links.append({
                "image_id": image.id,
                "file_name": image.file_name,
                "download_url": storage_service.get_public_url(image.file_path)
            })
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "total_images": len(download_links),
        "download_links": download_links
    }

