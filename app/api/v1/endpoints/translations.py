"""
Çeviri API Endpoint'leri
Kullanıcı arayüzü için Türkçe, İngilizce ve Arapça çeviri desteği
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict

from app.services.translation_service import (
    translation_service, 
    Language
)

router = APIRouter(prefix="/translations", tags=["Çeviri"])


# ============== Schemas ==============

class TranslateRequest(BaseModel):
    """Çeviri isteği"""
    text: str
    source: str  # tr, en, ar
    target: str  # tr, en, ar


class TranslateResponse(BaseModel):
    """Çeviri yanıtı"""
    original: str
    translated: str
    source: str
    target: str


class TranslateBatchRequest(BaseModel):
    """Toplu çeviri isteği"""
    texts: List[str]
    source: str
    target: str


class TranslateBatchResponse(BaseModel):
    """Toplu çeviri yanıtı"""
    translations: List[str]
    source: str
    target: str


class UITextsResponse(BaseModel):
    """UI metinleri yanıtı"""
    language: str
    texts: Dict[str, str]


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı"""
    libretranslate_available: bool
    fallback_available: bool
    supported_languages: List[str]


# ============== Endpoints ==============

@router.get("/health", response_model=HealthResponse)
async def check_translation_health():
    """
    Çeviri servisinin durumunu kontrol eder
    """
    is_available = await translation_service.check_health()
    
    return HealthResponse(
        libretranslate_available=is_available,
        fallback_available=True,  # Statik çeviriler her zaman mevcut
        supported_languages=["tr", "en", "ar"]
    )


@router.get("/languages")
async def get_supported_languages():
    """
    Desteklenen dilleri listeler
    """
    return {
        "languages": [
            {"code": "tr", "name": "Türkçe", "native_name": "Türkçe"},
            {"code": "en", "name": "English", "native_name": "English"},
            {"code": "ar", "name": "Arabic", "native_name": "العربية", "rtl": True}
        ]
    }


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Tek bir metni çevirir
    
    LibreTranslate sunucusu çalışmıyorsa hata döner.
    UI metinleri için /ui-texts endpoint'ini kullanın.
    """
    # Dil kodlarını validate et
    try:
        source_lang = Language(request.source)
        target_lang = Language(request.target)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dil. Desteklenen diller: tr, en, ar"
        )
    
    # Çeviri yap
    translated = await translation_service.translate(
        request.text, 
        source_lang, 
        target_lang
    )
    
    if translated is None:
        raise HTTPException(
            status_code=503,
            detail="Çeviri servisi şu anda kullanılamıyor. LibreTranslate sunucusunun çalıştığından emin olun."
        )
    
    return TranslateResponse(
        original=request.text,
        translated=translated,
        source=request.source,
        target=request.target
    )


@router.post("/translate/batch", response_model=TranslateBatchResponse)
async def translate_batch(request: TranslateBatchRequest):
    """
    Birden fazla metni toplu çevirir
    """
    try:
        source_lang = Language(request.source)
        target_lang = Language(request.target)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dil. Desteklenen diller: tr, en, ar"
        )
    
    translations = await translation_service.translate_batch(
        request.texts,
        source_lang,
        target_lang
    )
    
    return TranslateBatchResponse(
        translations=translations,
        source=request.source,
        target=request.target
    )


@router.get("/ui-texts", response_model=UITextsResponse)
async def get_ui_texts(
    language: str = Query("tr", description="Dil kodu: tr, en, ar")
):
    """
    Kullanıcı arayüzü için önceden tanımlı metinleri döndürür
    
    Bu endpoint LibreTranslate gerektirmez, statik çeviriler kullanır.
    Giriş, kayıt ve genel UI metinlerini içerir.
    """
    try:
        lang = Language(language)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dil. Desteklenen diller: tr, en, ar"
        )
    
    texts = translation_service.get_all_ui_texts(lang)
    
    return UITextsResponse(
        language=language,
        texts=texts
    )


@router.get("/ui-texts/{key}")
async def get_ui_text(
    key: str,
    language: str = Query("tr", description="Dil kodu: tr, en, ar")
):
    """
    Belirli bir UI metnini döndürür
    
    Örnek: /ui-texts/login?language=ar
    """
    try:
        lang = Language(language)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dil. Desteklenen diller: tr, en, ar"
        )
    
    text = translation_service.get_ui_text(key, lang)
    
    return {
        "key": key,
        "language": language,
        "text": text
    }


@router.post("/detect")
async def detect_language(text: str = Query(..., description="Dili algılanacak metin")):
    """
    Metnin dilini algılar
    
    LibreTranslate sunucusu gerektirir.
    """
    detected = await translation_service.detect_language(text)
    
    if detected is None:
        raise HTTPException(
            status_code=503,
            detail="Dil algılama servisi şu anda kullanılamıyor"
        )
    
    return {
        "text": text,
        "detected_language": detected
    }

