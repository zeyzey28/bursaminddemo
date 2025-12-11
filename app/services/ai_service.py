"""
AI Görüntü Doğrulama Servisi
Şikayet fotoğraflarını AI ile analiz eder ve doğrular
"""
import base64
import json
from typing import Optional, Tuple, List
import httpx
from pathlib import Path

from app.core.config import settings


class AIImageAnalyzer:
    """AI tabanlı görüntü analiz servisi"""
    
    # Kategori anahtar kelimeleri (AI analizi için)
    CATEGORY_KEYWORDS = {
        "road_damage": ["çukur", "asfalt", "yol", "kaldırım", "kırık", "hasar", "pothole", "crack"],
        "lighting": ["lamba", "aydınlatma", "karanlık", "ışık", "direk", "ampul"],
        "trash": ["çöp", "atık", "kirlilik", "pislik", "çöp kutusu", "garbage", "waste"],
        "traffic": ["trafik", "işaret", "levha", "sinyal", "trafik lambası"],
        "parking": ["park", "araç", "otopark", "yanlış park"],
        "green_area": ["ağaç", "park", "yeşil", "çim", "bitki", "bahçe"],
        "water": ["su", "kanalizasyon", "rögar", "su birikintisi", "boru"],
        "safety": ["tehlike", "güvenlik", "risk", "kaza"]
    }
    
    def __init__(self):
        self.api_url = settings.AI_SERVICE_URL
        self.api_key = settings.AI_API_KEY
    
    async def analyze_image(self, image_path: str) -> dict:
        """
        Görüntüyü AI ile analiz et
        
        Returns:
            {
                "is_valid": bool,           # Geçerli şikayet görseli mi
                "confidence": float,        # Güven skoru (0-1)
                "detected_category": str,   # Tespit edilen kategori
                "description": str,         # AI açıklaması
                "tags": List[str],          # Tespit edilen etiketler
                "urgency_score": float      # Aciliyet skoru (0-1)
            }
        """
        # API key yoksa mock sonuç döndür (geliştirme için)
        if not self.api_key:
            return await self._mock_analysis(image_path)
        
        try:
            # Görüntüyü base64'e çevir
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Dosya uzantısına göre MIME type
            ext = Path(image_path).suffix.lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }.get(ext, "image/jpeg")
            
            # OpenAI Vision API çağrısı
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-vision-preview",
                        "messages": [
                            {
                                "role": "system",
                                "content": """Sen bir belediye şikayet sistemi için görüntü analiz asistanısın.
                                Gönderilen fotoğrafları analiz et ve şu bilgileri JSON formatında döndür:
                                - is_valid: Fotoğraf gerçek bir belediye şikayeti mi (true/false)
                                - category: Şikayet kategorisi (road_damage, lighting, trash, traffic, parking, green_area, water, safety, other)
                                - description: Kısa açıklama (Türkçe)
                                - tags: İlgili etiketler listesi
                                - urgency: Aciliyet seviyesi (low, medium, high, urgent)
                                - confidence: Analiz güven skoru (0-1)
                                
                                Sadece JSON döndür, başka açıklama ekleme."""
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{mime_type};base64,{image_data}"
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": "Bu fotoğrafı belediye şikayeti olarak analiz et."
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # JSON parse
                    try:
                        analysis = json.loads(content)
                        return self._format_analysis(analysis)
                    except json.JSONDecodeError:
                        return await self._mock_analysis(image_path)
                else:
                    return await self._mock_analysis(image_path)
                    
        except Exception as e:
            print(f"AI analiz hatası: {e}")
            return await self._mock_analysis(image_path)
    
    def _format_analysis(self, analysis: dict) -> dict:
        """AI yanıtını standart formata çevir"""
        urgency_map = {
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "urgent": 1.0
        }
        
        return {
            "is_valid": analysis.get("is_valid", True),
            "confidence": analysis.get("confidence", 0.8),
            "detected_category": analysis.get("category", "other"),
            "description": analysis.get("description", ""),
            "tags": analysis.get("tags", []),
            "urgency_score": urgency_map.get(analysis.get("urgency", "medium"), 0.5)
        }
    
    async def _mock_analysis(self, image_path: str) -> dict:
        """
        Mock analiz sonucu (API key olmadığında veya hata durumunda)
        Gerçek projede bu fonksiyon kaldırılabilir
        """
        import random
        
        categories = ["road_damage", "lighting", "trash", "traffic", "green_area", "water", "other"]
        
        return {
            "is_valid": True,
            "confidence": round(random.uniform(0.7, 0.95), 2),
            "detected_category": random.choice(categories),
            "description": "Görüntü analizi yapıldı (mock)",
            "tags": ["şikayet", "belediye"],
            "urgency_score": round(random.uniform(0.3, 0.8), 2)
        }
    
    async def verify_complaint_images(
        self, 
        image_paths: List[str], 
        claimed_category: str
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Şikayet görsellerini doğrula
        
        Args:
            image_paths: Görsel dosya yolları
            claimed_category: Kullanıcının belirttiği kategori
            
        Returns:
            (is_verified, confidence_score, suggested_category)
        """
        if not image_paths:
            return True, 1.0, None
        
        analyses = []
        for path in image_paths:
            analysis = await self.analyze_image(path)
            analyses.append(analysis)
        
        # Ortalama güven skoru
        avg_confidence = sum(a["confidence"] for a in analyses) / len(analyses)
        
        # Kategori uyumu kontrolü
        detected_categories = [a["detected_category"] for a in analyses]
        most_common = max(set(detected_categories), key=detected_categories.count)
        
        # Kullanıcının kategorisi ile uyuşuyor mu
        category_match = (
            most_common == claimed_category or 
            claimed_category == "other" or
            most_common == "other"
        )
        
        # Tüm görseller geçerli mi
        all_valid = all(a["is_valid"] for a in analyses)
        
        is_verified = all_valid and (category_match or avg_confidence < 0.6)
        suggested = most_common if not category_match else None
        
        return is_verified, avg_confidence, suggested
    
    async def calculate_urgency_score(
        self,
        image_paths: List[str],
        category: str,
        description: str
    ) -> float:
        """
        Şikayet için aciliyet skoru hesapla
        
        Faktörler:
        - AI görüntü analizi
        - Kategori (bazı kategoriler daha acil)
        - Açıklama içeriği
        """
        base_scores = {
            "safety": 0.9,
            "water": 0.7,
            "road_damage": 0.6,
            "lighting": 0.5,
            "traffic": 0.5,
            "trash": 0.4,
            "parking": 0.3,
            "green_area": 0.3,
            "noise": 0.3,
            "other": 0.4
        }
        
        # Temel skor
        base_score = base_scores.get(category, 0.4)
        
        # Görüntü analizi skoru
        if image_paths:
            analyses = []
            for path in image_paths:
                analysis = await self.analyze_image(path)
                analyses.append(analysis)
            
            ai_urgency = sum(a["urgency_score"] for a in analyses) / len(analyses)
        else:
            ai_urgency = 0.5
        
        # Açıklama analizi (acil kelimeler)
        urgent_keywords = ["acil", "tehlike", "risk", "kaza", "yaralı", "tehlikeli", "hemen"]
        description_lower = description.lower()
        keyword_bonus = 0.1 if any(kw in description_lower for kw in urgent_keywords) else 0
        
        # Final skor
        final_score = (base_score * 0.3) + (ai_urgency * 0.5) + keyword_bonus + 0.1
        
        return min(max(final_score, 0), 1)  # 0-1 arasında tut


# Singleton instance
ai_analyzer = AIImageAnalyzer()

