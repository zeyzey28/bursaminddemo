"""
LibreTranslate Çeviri Servisi
Kullanıcı arayüzü için Türkçe, İngilizce ve Arapça çeviri desteği
"""
import httpx
from typing import Optional, Dict, List
from enum import Enum


class Language(str, Enum):
    """Desteklenen diller"""
    TURKISH = "tr"
    ENGLISH = "en"
    ARABIC = "ar"


class TranslationService:
    """LibreTranslate API ile çeviri servisi"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.supported_languages = [Language.TURKISH, Language.ENGLISH, Language.ARABIC]
        
        # Önceden tanımlı UI metinleri (fallback için)
        self.ui_texts = {
            Language.TURKISH: {
                # Auth
                "login": "Giriş Yap",
                "register": "Kayıt Ol",
                "logout": "Çıkış Yap",
                "username": "Kullanıcı Adı",
                "password": "Şifre",
                "confirm_password": "Şifre Tekrar",
                "email": "E-posta",
                "phone": "Telefon",
                "forgot_password": "Şifremi Unuttum",
                "reset_password": "Şifre Sıfırla",
                "new_password": "Yeni Şifre",
                
                # Errors
                "invalid_credentials": "Geçersiz kullanıcı adı veya şifre",
                "user_exists": "Bu kullanıcı adı zaten kullanılıyor",
                "password_mismatch": "Şifreler eşleşmiyor",
                "required_field": "Bu alan zorunludur",
                "invalid_email": "Geçersiz e-posta adresi",
                
                # Success
                "login_success": "Giriş başarılı",
                "register_success": "Kayıt başarılı",
                "password_reset_success": "Şifre başarıyla sıfırlandı",
                
                # General
                "welcome": "Hoş Geldiniz",
                "loading": "Yükleniyor...",
                "error": "Hata",
                "success": "Başarılı",
                "cancel": "İptal",
                "save": "Kaydet",
                "delete": "Sil",
                "edit": "Düzenle",
                "back": "Geri",
                "next": "İleri",
                "submit": "Gönder",
                "search": "Ara",
                "filter": "Filtrele",
                "clear": "Temizle",
                "yes": "Evet",
                "no": "Hayır",
                "or": "veya",
                "and": "ve",
            },
            Language.ENGLISH: {
                # Auth
                "login": "Login",
                "register": "Register",
                "logout": "Logout",
                "username": "Username",
                "password": "Password",
                "confirm_password": "Confirm Password",
                "email": "Email",
                "phone": "Phone",
                "forgot_password": "Forgot Password",
                "reset_password": "Reset Password",
                "new_password": "New Password",
                
                # Errors
                "invalid_credentials": "Invalid username or password",
                "user_exists": "This username is already taken",
                "password_mismatch": "Passwords do not match",
                "required_field": "This field is required",
                "invalid_email": "Invalid email address",
                
                # Success
                "login_success": "Login successful",
                "register_success": "Registration successful",
                "password_reset_success": "Password reset successfully",
                
                # General
                "welcome": "Welcome",
                "loading": "Loading...",
                "error": "Error",
                "success": "Success",
                "cancel": "Cancel",
                "save": "Save",
                "delete": "Delete",
                "edit": "Edit",
                "back": "Back",
                "next": "Next",
                "submit": "Submit",
                "search": "Search",
                "filter": "Filter",
                "clear": "Clear",
                "yes": "Yes",
                "no": "No",
                "or": "or",
                "and": "and",
            },
            Language.ARABIC: {
                # Auth
                "login": "تسجيل الدخول",
                "register": "تسجيل",
                "logout": "تسجيل الخروج",
                "username": "اسم المستخدم",
                "password": "كلمة المرور",
                "confirm_password": "تأكيد كلمة المرور",
                "email": "البريد الإلكتروني",
                "phone": "الهاتف",
                "forgot_password": "نسيت كلمة المرور",
                "reset_password": "إعادة تعيين كلمة المرور",
                "new_password": "كلمة المرور الجديدة",
                
                # Errors
                "invalid_credentials": "اسم المستخدم أو كلمة المرور غير صحيحة",
                "user_exists": "اسم المستخدم مستخدم بالفعل",
                "password_mismatch": "كلمات المرور غير متطابقة",
                "required_field": "هذا الحقل مطلوب",
                "invalid_email": "عنوان البريد الإلكتروني غير صالح",
                
                # Success
                "login_success": "تم تسجيل الدخول بنجاح",
                "register_success": "تم التسجيل بنجاح",
                "password_reset_success": "تم إعادة تعيين كلمة المرور بنجاح",
                
                # General
                "welcome": "مرحباً",
                "loading": "جاري التحميل...",
                "error": "خطأ",
                "success": "نجاح",
                "cancel": "إلغاء",
                "save": "حفظ",
                "delete": "حذف",
                "edit": "تعديل",
                "back": "رجوع",
                "next": "التالي",
                "submit": "إرسال",
                "search": "بحث",
                "filter": "تصفية",
                "clear": "مسح",
                "yes": "نعم",
                "no": "لا",
                "or": "أو",
                "and": "و",
            }
        }
    
    async def translate(
        self, 
        text: str, 
        source: Language, 
        target: Language
    ) -> Optional[str]:
        """
        LibreTranslate API kullanarak metin çevirir
        
        Args:
            text: Çevrilecek metin
            source: Kaynak dil
            target: Hedef dil
            
        Returns:
            Çevrilmiş metin veya None (hata durumunda)
        """
        if source == target:
            return text
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/translate",
                    data={
                        "q": text,
                        "source": source.value,
                        "target": target.value,
                        "format": "text"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("translatedText")
                else:
                    print(f"Translation API error: {response.status_code}")
                    return None
                    
        except httpx.ConnectError:
            print("LibreTranslate server not running, using fallback")
            return None
        except Exception as e:
            print(f"Translation error: {e}")
            return None
    
    async def translate_batch(
        self,
        texts: List[str],
        source: Language,
        target: Language
    ) -> List[str]:
        """
        Birden fazla metni toplu çevirir
        """
        results = []
        for text in texts:
            translated = await self.translate(text, source, target)
            results.append(translated or text)
        return results
    
    def get_ui_text(self, key: str, language: Language) -> str:
        """
        Önceden tanımlı UI metnini döndürür (fallback)
        
        Args:
            key: Metin anahtarı (örn: "login", "password")
            language: Hedef dil
            
        Returns:
            Çevrilmiş UI metni
        """
        lang_texts = self.ui_texts.get(language, self.ui_texts[Language.TURKISH])
        return lang_texts.get(key, key)
    
    def get_all_ui_texts(self, language: Language) -> Dict[str, str]:
        """
        Belirtilen dildeki tüm UI metinlerini döndürür
        """
        return self.ui_texts.get(language, self.ui_texts[Language.TURKISH])
    
    async def detect_language(self, text: str) -> Optional[str]:
        """
        Metnin dilini algılar
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/detect",
                    data={"q": text}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result and len(result) > 0:
                        return result[0].get("language")
                return None
                
        except Exception as e:
            print(f"Language detection error: {e}")
            return None
    
    async def check_health(self) -> bool:
        """
        LibreTranslate sunucusunun çalışıp çalışmadığını kontrol eder
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/languages")
                return response.status_code == 200
        except:
            return False


# Singleton instance
translation_service = TranslationService()

