"""
Şikayet AI Sınıflandırma Servisi
Hybrid yaklaşım: Keyword (hızlı) + Gemini AI (akıllı)
"""
import re
import os
from typing import Dict, Optional, Tuple
from datetime import datetime
import httpx

# Local embedding için (Gemini yerine) - Lazy import
HAS_SENTENCE_TRANSFORMERS = False
SentenceTransformer = None

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"  # En yeni ve hızlı model


class ComplaintAIService:
    """Şikayet AI sınıflandırma servisi (maliyet-optimize)"""
    
    # Kategori bazlı aciliyet çarpanları (0.0 - 1.5 arası)
    # Gerçekten acil olabilecek kategorilerin çarpanı yüksek
    CATEGORY_URGENCY_MULTIPLIERS = {
        "water": 1.3,          # Su patlaması/basması gerçekten acil
        "road_damage": 1.2,     # Büyük çukur, yol çökmesi acil olabilir
        "safety": 1.2,          # Güvenlik sorunları acil
        "traffic": 1.0,         # Trafik önemli ama genelde acil değil
        "lighting": 0.7,        # Aydınlatma önemli ama nadiren acil
        "noise": 0.7,           # Gürültü rahatsız eder ama acil değil
        "parking": 0.6,         # Park sorunu acil değil
        "green_area": 0.6,      # Yeşil alan bakımı acil değil
        "air_quality": 0.9,     # Hava kirliliği orta aciliyet
        "other": 0.5            # Bilinmeyen/diğer → düşük aciliyet
    }
    
    # Kategori anahtar kelimeleri (Türkçe)
    CATEGORY_KEYWORDS = {
        "road_damage": [
            "çukur", "yol hasarı", "asfalt", "yol bozuk", "yol çatlak", "yol delik",
            "yol tamiri", "yol onarım", "yol bozulmuş", "yol kırık", "yol düzelt"
        ],
        "lighting": [
            "lamba", "ışık", "aydınlatma", "sokak lambası", "ışık yok", "karanlık",
            "lamba yanmıyor", "aydınlatma sorunu", "gece karanlık", "lamba bozuk"
        ],
        "traffic": [
            "trafik", "yoğunluk", "tıkanıklık", "trafik sıkışık", "araç kuyruğu",
            "trafik sorunu", "yol kapalı", "trafik kazası", "trafik lambası"
        ],
        "parking": [
            "park", "park yeri", "otopark", "park sorunu", "park yok",
            "araç park", "park alanı", "park yasağı", "park edemiyorum"
        ],
        "noise": [
            "gürültü", "ses", "yüksek ses", "gürültü kirliliği", "rahatsız edici ses",
            "gürültü yapıyor", "ses çok yüksek", "gürültü sorunu"
        ],
        "green_area": [
            "park", "yeşil alan", "ağaç", "çiçek", "bahçe", "yeşillik",
            "park bakım", "ağaç kesilmiş", "çim", "yeşil alan sorunu"
        ],
        "water": [
            "su", "su borusu", "su kaçağı", "kanalizasyon", "su patladı",
            "su akıyor", "su sorunu", "su kesintisi", "su basması"
        ],
        "air_quality": [
            "hava", "hava kirliliği", "duman", "koku", "hava kalitesi",
            "kötü koku", "dumanlı", "hava kirli", "nefes alamıyorum"
        ],
        "safety": [
            "güvenlik", "tehlikeli", "risk", "güvensiz", "kaza riski",
            "güvenlik sorunu", "tehlike", "riskli", "güvenli değil"
        ]
    }
    
    # Aciliyet belirleyici kelimeler
    URGENCY_KEYWORDS = {
        "high": [
            "acil", "çok acil", "hemen", "derhal", "tehlikeli", "risk", "kaza",
            "yangın", "patlama", "su basması", "çökme", "düşme", "yaralanma"
        ],
        "medium": [
            "önemli", "dikkat", "sorun", "rahatsız", "problem", "bozuk",
            "çalışmıyor", "yapılamıyor", "engel", "zorluk"
        ],
        "low": [
            "rahatsız", "istek", "öneri", "şikayet", "bilgi", "soru"
        ]
    }
    
    def __init__(self, use_gemini: bool = True):
        """
        Args:
            use_gemini: Gemini AI kullan (True) veya sadece keyword (False)
        """
        self.use_gemini = use_gemini and GEMINI_API_KEY is not None
        self.embedding_model = None
        
        if not self.use_gemini and use_gemini:
            print("⚠️ GEMINI_API_KEY bulunamadı. Keyword-only modda çalışılıyor.")
    
    def detect_category_from_keywords(self, text: str) -> Tuple[Optional[str], float]:
        """
        Keyword-based kategori tespiti
        
        Returns:
            (category, confidence) tuple
        """
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            if score > 0:
                scores[category] = score / len(keywords)
        
        if not scores:
            return None, 0.0
        
        best_category = max(scores.items(), key=lambda x: x[1])
        return best_category[0], min(best_category[1], 1.0)
    
    def calculate_urgency_score(
        self, 
        text: str, 
        detected_category: Optional[str] = None
    ) -> float:
        """
        Aciliyet skorunu hesapla (0-1 arası)
        Kategori bazlı ağırlıklandırma ile daha akıllı skorlama
        
        Args:
            text: Şikayet metni
            detected_category: AI'ın tespit ettiği kategori (None ise spam olabilir)
        
        Returns:
            0-1 arası urgency score
        """
        text_lower = text.lower()
        
        # Yüksek aciliyet kelimeleri
        high_count = sum(1 for kw in self.URGENCY_KEYWORDS["high"] if kw in text_lower)
        medium_count = sum(1 for kw in self.URGENCY_KEYWORDS["medium"] if kw in text_lower)
        low_count = sum(1 for kw in self.URGENCY_KEYWORDS["low"] if kw in text_lower)
        
        # Skorlama
        if high_count > 0:
            base_score = 0.7 + min(high_count * 0.1, 0.3)
        elif medium_count > 0:
            base_score = 0.4 + min(medium_count * 0.1, 0.3)
        elif low_count > 0:
            base_score = 0.2 + min(low_count * 0.05, 0.2)
        else:
            base_score = 0.3  # Varsayılan
        
        # Metin uzunluğu faktörü (daha detaylı şikayetler genelde daha acil)
        length_factor = min(len(text) / 200, 0.2)  # Max 0.2 ek puan
        
        initial_score = base_score + length_factor
        
        # ÖNEMLİ: Kategori bazlı ağırlıklandırma
        if detected_category is None:
            # AI kategori bulamadı → Muhtemelen spam veya anlamsız
            # "Acil" yazsa bile skorunu düşür
            category_multiplier = 0.4
        else:
            # Kategori bulundu → O kategorinin aciliyet çarpanını kullan
            category_multiplier = self.CATEGORY_URGENCY_MULTIPLIERS.get(
                detected_category, 
                0.5  # Bilinmeyen kategori için düşük çarpan
            )
        
        # Final skor = initial_score * category_multiplier
        final_score = min(initial_score * category_multiplier, 1.0)
        
        return round(final_score, 3)
    
    async def ask_gemini_ai(self, text: str) -> Dict:
        """
        Gemini AI'a sorarak şikayeti analiz et
        
        Args:
            text: Şikayet metni (title + description)
            
        Returns:
            {
                "is_valid_complaint": bool,  # Belediye kapsamında mı?
                "category": str,             # Önerilen kategori
                "urgency_level": str,        # "urgent", "high", "medium", "low"
                "reasoning": str,            # Karar gerekçesi
                "confidence": float          # 0-1 arası güven skoru
            }
        """
        if not self.use_gemini:
            return None
        
        prompt = f"""Sen bir belediye şikayet sistemi AI asistanısın. Aşağıdaki şikayeti analiz et:

Şikayet: "{text}"

Lütfen şu formatta JSON yanıt ver:
{{
  "is_valid_complaint": true/false,
  "category": "road_damage/lighting/trash/traffic/parking/noise/green_area/water/air_quality/safety/other",
  "urgency_level": "urgent/high/medium/low",
  "reasoning": "Kısa açıklama",
  "confidence": 0.0-1.0
}}

Değerlendirme kriterleri:
1. is_valid_complaint: Bu bir belediye hizmeti kapsamında mı? (kedi kurtarma, kayıp eşya, komşu kavgası HAYIR)
2. category: Hangi belediye birimine gitmeli?
3. urgency_level: Gerçek aciliyet nedir? (sadece "acil" kelimesine bakma, durumu değerlendir)
   - urgent: Hayati tehlike, su patlaması, yol çökmesi, yangın riski
   - high: Önemli sorun, kısa sürede çözülmeli (trafik kazası riski, büyük çukur)
   - medium: Rahatsız edici ama acil değil (çöp, gürültü, lamba)
   - low: Öneri, talep, küçük sorun
4. reasoning: Kararını kısaca açıkla (1 cümle)
5. confidence: Ne kadar eminsin? (0.0-1.0)

Sadece JSON yanıt ver, başka açıklama yapma."""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
                response = await client.post(
                    url,
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.2,  # Düşük = daha tutarlı
                            "maxOutputTokens": 200
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text_response = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # JSON parse et
                    import json
                    # JSON'u temizle (markdown code block varsa)
                    text_response = text_response.strip()
                    if text_response.startswith("```"):
                        text_response = text_response.split("```")[1]
                        if text_response.startswith("json"):
                            text_response = text_response[4:]
                    
                    gemini_result = json.loads(text_response.strip())
                    return gemini_result
                else:
                    print(f"⚠️ Gemini API Error: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"⚠️ Gemini AI hatası: {e}")
            return None
    
    def determine_priority(self, urgency_score: float) -> str:
        """
        Aciliyet skoruna göre priority belirle
        
        Returns:
            "urgent", "high", "medium", "low"
        """
        if urgency_score >= 0.8:
            return "urgent"  # Çok acil
        elif urgency_score >= 0.6:
            return "high"  # Acil
        elif urgency_score >= 0.4:
            return "medium"  # Acil değil (orta)
        else:
            return "low"  # Acil değil (düşük)
    
    async def classify_complaint(
        self,
        title: str,
        description: str,
        user_category: Optional[str] = None
    ) -> Dict:
        """
        Şikayeti sınıflandır ve skorla
        
        Args:
            title: Şikayet başlığı
            description: Şikayet açıklaması
            user_category: Kullanıcının seçtiği kategori (opsiyonel)
            
        Returns:
            {
                "category": "...",
                "category_confidence": 0.95,
                "urgency_score": 0.75,
                "priority": "high",
                "ai_verified": True,
                "ai_verification_score": 0.92
            }
        """
        full_text = f"{title} {description}".lower()
        
        # 🤖 ÖNCE GEMINI AI'A SOR (varsa)
        gemini_result = None
        if self.use_gemini:
            gemini_result = await self.ask_gemini_ai(full_text)
        
        # Gemini sonucu varsa onu kullan, yoksa keyword-based yap
        if gemini_result and gemini_result.get("confidence", 0) > 0.5:
            # Gemini AI'ın analizi güvenilir
            detected_category = gemini_result.get("category", "other")
            category_confidence = gemini_result.get("confidence", 0.8)
            
            # Urgency level'ı Gemini'den al
            urgency_level = gemini_result.get("urgency_level", "medium")
            urgency_map = {
                "urgent": 0.9,
                "high": 0.7,
                "medium": 0.5,
                "low": 0.3
            }
            urgency_score = urgency_map.get(urgency_level, 0.5)
            
            # Geçersiz şikayet mi?
            if not gemini_result.get("is_valid_complaint", True):
                # Spam/belediye kapsamı dışı
                detected_category = None
                category_confidence = 0.0
                urgency_score = 0.2  # Çok düşük
                
        else:
            # Gemini yok veya güvensiz → Keyword-based yap
            # 1. Kategori tespiti
            detected_category, category_confidence = self.detect_category_from_keywords(full_text)
            
            # 2. Aciliyet skoru (kategori ile birlikte değerlendir)
            urgency_score = self.calculate_urgency_score(full_text, detected_category)
        
        # Kullanıcı kategorisi ile karşılaştır
        if user_category:
            user_cat_lower = user_category.lower()
            if detected_category and detected_category == user_cat_lower:
                # Kullanıcı doğru seçmiş
                final_category = detected_category
                ai_verified = True
                ai_verification_score = category_confidence
            elif detected_category:
                # AI farklı bir kategori öneriyor
                final_category = detected_category
                ai_verified = False
                ai_verification_score = category_confidence
            else:
                # AI kategori bulamadı, kullanıcının seçimini kabul et
                final_category = user_cat_lower
                ai_verified = False
                ai_verification_score = 0.5
        else:
            # Kullanıcı kategori seçmemiş, AI'nın önerisini kullan
            final_category = detected_category or "other"
            ai_verified = detected_category is not None
            ai_verification_score = category_confidence if detected_category else 0.3
        
        # 3. Priority belirleme
        priority = self.determine_priority(urgency_score)
        
        result = {
            "category": final_category,
            "category_confidence": round(category_confidence, 3),
            "urgency_score": urgency_score,
            "priority": priority,
            "ai_verified": ai_verified,
            "ai_verification_score": round(ai_verification_score, 3),
            "ai_category_suggestion": detected_category
        }
        
        # Gemini sonucunu ekle (varsa)
        if gemini_result:
            result["gemini_analysis"] = {
                "is_valid": gemini_result.get("is_valid_complaint", True),
                "reasoning": gemini_result.get("reasoning", ""),
                "confidence": gemini_result.get("confidence", 0.0)
            }
        
        return result


# Singleton instance
# use_gemini=False: Sadece keyword-based (hızlı, ücretsiz, production-ready)
# use_gemini=True: Gemini AI + keyword fallback (daha akıllı ama API maliyeti var)
complaint_ai_service = ComplaintAIService(use_gemini=False)  # Production için False önerilir

