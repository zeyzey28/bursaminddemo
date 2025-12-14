"""
Hazır Feedback Şablonları
"""
from typing import List, Dict, Optional

FEEDBACK_TEMPLATES: List[Dict[str, str]] = [
    {
        "id": "received",
        "title": "Şikayetiniz Alındı",
        "message": "Şikayetiniz tarafımıza ulaşmıştır. En kısa sürede değerlendirilerek ilgili birime iletilecektir.",
        "new_status": "received"
    },
    {
        "id": "in_progress",
        "title": "İşleme Alındı",
        "message": "Şikayetiniz ilgili ekibimiz tarafından incelenmeye başlanmıştır. Gelişmelerden haberdar olacaksınız.",
        "new_status": "in_progress"
    },
    {
        "id": "field_inspection",
        "title": "Saha İncelemesi Yapılıyor",
        "message": "Ekibimiz şikayet konusunu yerinde incelemek üzere harekete geçmiştir. İnceleme sonrası bilgilendirileceksiniz.",
        "new_status": "in_progress"
    },
    {
        "id": "resolved",
        "title": "Şikayetiniz Çözüldü",
        "message": "Bildirdiğiniz sorun çözülmüştür. Katkılarınız için teşekkür ederiz.",
        "new_status": "resolved"
    },
    {
        "id": "rejected_duplicate",
        "title": "Mükerrer Şikayet",
        "message": "Bu konuda daha önce alınmış bir şikayet bulunmaktadır. İlgili süreçten haberdar edileceksiniz.",
        "new_status": "rejected"
    },
    {
        "id": "rejected_invalid",
        "title": "Geçersiz Şikayet",
        "message": "Gönderdiğiniz şikayet konusu belediye hizmet kapsamı dışında kalmaktadır. İlgili kuruma yönlendirilmeniz önerilir.",
        "new_status": "rejected"
    },
    {
        "id": "needs_more_info",
        "title": "Ek Bilgi Gerekiyor",
        "message": "Konunun daha iyi anlaşılabilmesi için ek bilgi veya fotoğraf paylaşmanızı rica ederiz.",
        "new_status": "received"
    },
    {
        "id": "scheduled",
        "title": "Planlama Aşamasında",
        "message": "Bildirdiğiniz sorun için çözüm planlaması yapılmaktadır. Yakın zamanda müdahale edilecektir.",
        "new_status": "in_progress"
    },
    {
        "id": "budget_pending",
        "title": "Bütçe Onayı Bekleniyor",
        "message": "Çözüm için gerekli bütçe tahsisi işlemleri devam etmektedir. Onay sonrası işleme başlanacaktır.",
        "new_status": "in_progress"
    }
]

# Kategori → İlgili Birim Eşlemesi
CATEGORY_TO_UNIT = {
    "road_damage": "Yol Bakım ve Onarım Birimi",
    "lighting": "Aydınlatma Servisi",
    "traffic": "Trafik Yönetimi Birimi",
    "parking": "Park ve Bahçeler Müdürlüğü",
    "noise": "Çevre Koruma Müdürlüğü",
    "green_area": "Park ve Bahçeler Müdürlüğü",
    "water": "Su ve Kanalizasyon İdaresi (BUSKİ)",
    "air_quality": "Çevre Koruma Müdürlüğü",
    "safety": "Zabıta Müdürlüğü",
    "other": "Genel İşler Müdürlüğü"
}


def get_feedback_templates() -> List[Dict[str, str]]:
    """Tüm feedback şablonlarını döner"""
    return FEEDBACK_TEMPLATES


def get_feedback_template(template_id: str) -> Optional[Dict[str, str]]:
    """Belirli bir şablonu döner"""
    for template in FEEDBACK_TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def get_responsible_unit(category: str) -> str:
    """Kategori için ilgili birimi döner"""
    return CATEGORY_TO_UNIT.get(category, "Genel İşler Müdürlüğü")

