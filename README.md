# 🏙️ Bursa Akıllı Şehir Backend API

Naim Süleymanoğlu Bulvarı için iki panelli Akıllı Şehir sistemi backend API'si.

**Base URL:** `http://localhost:8000`  
**API Version:** `v1`  
**API Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## 📋 İçindekiler

1. [Hızlı Başlangıç](#-hızlı-başlangıç)
2. [Authentication (Kimlik Doğrulama)](#-authentication-kimlik-doğrulama)
3. [Kullanıcı Paneli Endpoint'leri](#-kullanıcı-paneli-endpointleri)
4. [Belediye Paneli Endpoint'leri](#-belediye-paneli-endpointleri)
5. [3D Harita Entegrasyonu](#-3d-harita-entegrasyonu)
6. [Şikayet Sistemi Detayları](#-şikayet-sistemi-detayları)
7. [Trafik Verileri](#-trafik-verileri)
8. [Hata Yönetimi](#-hata-yönetimi)
9. [Örnek Kodlar](#-örnek-kodlar)

---

## 🚀 Hızlı Başlangıç

### API'yi Başlatma

```bash
# Virtual environment aktif et
source venv/bin/activate

# API'yi başlat
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API şu adreste çalışacak: `http://localhost:8000`

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "environment": "production",
  "debug": false
}
```

---

## 🔐 Authentication (Kimlik Doğrulama)

### Token Yapısı

Backend **JWT (JSON Web Token)** kullanır. Token'ı her authenticated request'te header'a eklemen gerekir:

```
Authorization: Bearer <access_token>
```

**Token Süresi:** 30 dakika (süre dolunca yeniden login gerekir)

---

### 1. Vatandaş Kaydı

**Endpoint:** `POST /api/v1/auth/citizen/register`

**Request Body (JSON):**
```json
{
  "username": "ahmet123",
  "password": "güvenlişifre123",
  "full_name": "Ahmet Yılmaz",
  "phone": "+905551234567",
  "email": "ahmet@example.com"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "ahmet123",
    "full_name": "Ahmet Yılmaz",
    "role": "citizen",
    "is_active": true
  }
}
```

**JavaScript Örneği:**
```javascript
const register = async (userData) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/citizen/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Kayıt başarısız');
  }
  
  const data = await response.json();
  // Token'ı localStorage'a kaydet
  localStorage.setItem('access_token', data.access_token);
  return data;
};
```

---

### 2. Vatandaş Girişi

**Endpoint:** `POST /api/v1/auth/citizen/login`

**Request Body (JSON):**
```json
{
  "username": "ahmet123",
  "password": "güvenlişifre123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "ahmet123",
    "full_name": "Ahmet Yılmaz",
    "role": "citizen"
  }
}
```

**JavaScript Örneği:**
```javascript
const login = async (username, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/citizen/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Giriş başarısız');
  }
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  return data;
};
```

---

### 3. Mevcut Kullanıcı Bilgisi

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "ahmet123",
  "full_name": "Ahmet Yılmaz",
  "role": "citizen",
  "is_active": true
}
```

---

## 👤 Kullanıcı Paneli Endpoint'leri

### 📸 Şikayet Sistemi

#### 1. Kategorileri Listele (Public - Auth Gerektirmez)

**Endpoint:** `GET /api/v1/complaints/categories`

**Response:**
```json
{
  "categories": [
    {
      "id": "road_damage",
      "name": "Yol Hasarı",
      "icon": "🛣️",
      "color": "#FF6B6B"
    },
    {
      "id": "lighting",
      "name": "Aydınlatma Sorunu",
      "icon": "💡",
      "color": "#FFD93D"
    },
    {
      "id": "traffic",
      "name": "Trafik Sorunu",
      "icon": "🚦",
      "color": "#4D96FF"
    },
    {
      "id": "parking",
      "name": "Park Sorunu",
      "icon": "🅿️",
      "color": "#9D84B7"
    },
    {
      "id": "noise",
      "name": "Gürültü",
      "icon": "🔊",
      "color": "#FF8E53"
    },
    {
      "id": "green_area",
      "name": "Yeşil Alan",
      "icon": "🌳",
      "color": "#4CAF50"
    },
    {
      "id": "water",
      "name": "Su/Kanalizasyon",
      "icon": "💧",
      "color": "#00BCD4"
    },
    {
      "id": "air_quality",
      "name": "Hava Kalitesi",
      "icon": "🌫️",
      "color": "#9E9E9E"
    },
    {
      "id": "safety",
      "name": "Güvenlik",
      "icon": "🚨",
      "color": "#F44336"
    },
    {
      "id": "other",
      "name": "Diğer",
      "icon": "📝",
      "color": "#607D8B"
    }
  ],
  "total": 10
}
```

**JavaScript Örneği:**
```javascript
const getCategories = async () => {
  const response = await fetch('http://localhost:8000/api/v1/complaints/categories');
  const data = await response.json();
  return data.categories;
};
```

---

#### 2. Şikayet Oluştur

**Endpoint:** `POST /api/v1/complaints/`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Form Data:**
- `description` (string, **zorunlu**): Şikayet açıklaması
- `category` (string, **zorunlu**): Kategori ID (örn: "road_damage")
- `latitude` (float, **zorunlu**): Enlem
- `longitude` (float, **zorunlu**): Boylam
- `title` (string, **opsiyonel**): Başlık (verilmezse description'dan otomatik oluşturulur)
- `address` (string, **opsiyonel**): Adres
- `images[]` (file[], **opsiyonel**): Fotoğraflar (birden fazla gönderilebilir)

**AI Özellikleri:**
- Şikayet otomatik olarak AI tarafından analiz edilir
- Kategori düzeltilir (yanlış seçilmişse)
- Aciliyet skoru hesaplanır (0-1 arası)
- Priority belirlenir (low, medium, high, urgent)

**Response (201 Created):**
```json
{
  "id": 123,
  "user_id": 1,
  "title": "Yolda büyük çukur var",
  "description": "Naim Süleymanoğlu Bulvarı'nda büyük bir çukur oluşmuş, araçlar zorlanıyor.",
  "category": "road_damage",
  "latitude": 40.1828,
  "longitude": 29.0665,
  "address": "Naim Süleymanoğlu Bulvarı, Bursa",
  "status": "pending",
  "priority": "high",
  "urgency_score": 0.85,
  "ai_verified": true,
  "ai_verification_score": 0.92,
  "ai_category_suggestion": "road_damage",
  "created_at": "2025-01-14T10:30:00Z",
  "updated_at": "2025-01-14T10:30:00Z",
  "resolved_at": null,
  "images": [
    {
      "id": 456,
      "file_path": "complaints/123/image1.jpg",
      "file_name": "image1.jpg",
      "file_size": 245678,
      "mime_type": "image/jpeg",
      "uploaded_at": "2025-01-14T10:30:05Z"
    }
  ],
  "feedbacks": [],
  "has_images": true,
  "image_count": 1
}
```

**JavaScript Örneği (FormData ile):**
```javascript
const createComplaint = async (complaintData, images = []) => {
  const formData = new FormData();
  
  formData.append('description', complaintData.description);
  formData.append('category', complaintData.category);
  formData.append('latitude', complaintData.latitude.toString());
  formData.append('longitude', complaintData.longitude.toString());
  
  if (complaintData.title) {
    formData.append('title', complaintData.title);
  }
  if (complaintData.address) {
    formData.append('address', complaintData.address);
  }
  
  // Fotoğrafları ekle
  images.forEach((image, index) => {
    formData.append('images', image);
  });
  
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8000/api/v1/complaints/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
      // Content-Type header'ını EKLEME - browser otomatik ekler (multipart/form-data)
    },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Şikayet oluşturulamadı');
  }
  
  return await response.json();
};

// Kullanım:
const complaint = await createComplaint(
  {
    description: "Yolda büyük çukur var",
    category: "road_damage",
    latitude: 40.1828,
    longitude: 29.0665,
    address: "Naim Süleymanoğlu Bulvarı"
  },
  [imageFile1, imageFile2] // File objeleri
);
```

**React Örneği:**
```jsx
import { useState } from 'react';

const ComplaintForm = () => {
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [images, setImages] = useState([]);
  const [location, setLocation] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!location) {
      alert('Konum bilgisi alınamadı');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('description', description);
      formData.append('category', category);
      formData.append('latitude', location.lat);
      formData.append('longitude', location.lng);
      
      images.forEach((image) => {
        formData.append('images', image);
      });

      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/v1/complaints/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        alert('Şikayetiniz başarıyla oluşturuldu!');
        console.log('AI Analiz:', {
          priority: data.priority,
          urgency_score: data.urgency_score,
          ai_verified: data.ai_verified
        });
      }
    } catch (error) {
      console.error('Hata:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Şikayet açıklaması"
        required
      />
      <select value={category} onChange={(e) => setCategory(e.target.value)} required>
        <option value="">Kategori seçin</option>
        {/* Kategoriler buraya */}
      </select>
      <input
        type="file"
        multiple
        accept="image/*"
        onChange={(e) => setImages(Array.from(e.target.files))}
      />
      <button type="submit">Gönder</button>
    </form>
  );
};
```

---

#### 3. Şikayetleri Listele (Kendi Şikayetlerim)

**Endpoint:** `GET /api/v1/complaints/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page` (int, default: 1): Sayfa numarası
- `page_size` (int, default: 20): Sayfa başına kayıt
- `status` (string, optional): Filtre (pending, in_progress, resolved, rejected)
- `category` (string, optional): Kategori filtresi

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "title": "Yolda büyük çukur var",
      "description": "...",
      "category": "road_damage",
      "status": "pending",
      "priority": "high",
      "urgency_score": 0.85,
      "created_at": "2025-01-14T10:30:00Z",
      "has_images": true,
      "image_count": 2
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 🗺️ Konum Servisleri (Public - Auth Gerektirmez)

#### 1. Yakındaki Eczaneler

**Endpoint:** `GET /api/v1/locations/pharmacies`

**Query Parameters:**
- `latitude` (float, **zorunlu**): Kullanıcı enlemi
- `longitude` (float, **zorunlu**): Kullanıcı boylamı
- `radius_km` (float, default: 5.0): Arama yarıçapı (km)
- `limit` (int, default: 50): Maksimum sonuç sayısı

**Response:**
```json
[
  {
    "id": 1,
    "name": "Merkez Eczanesi",
    "latitude": 40.1830,
    "longitude": 29.0670,
    "address": "Naim Süleymanoğlu Bulvarı No:123",
    "phone": "+905551234567",
    "is_on_duty": true,
    "distance_km": 0.5
  }
]
```

**JavaScript Örneği:**
```javascript
const getNearbyPharmacies = async (lat, lng, radius = 5) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/locations/pharmacies?latitude=${lat}&longitude=${lng}&radius_km=${radius}`
  );
  return await response.json();
};
```

---

#### 2. Yakındaki Hastaneler

**Endpoint:** `GET /api/v1/locations/hospitals`

**Query Parameters:** (eczanelerle aynı)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Bursa Devlet Hastanesi",
    "latitude": 40.1850,
    "longitude": 29.0700,
    "address": "...",
    "phone": "+905551234567",
    "has_emergency": true,
    "distance_km": 1.2
  }
]
```

---

### 🚦 Trafik Yoğunluğu (Public - Auth Gerektirmez)

#### 1. Anlık Trafik (3D Harita İçin)

**Endpoint:** `GET /api/v1/traffic-density/forecast/current`

**Query Parameters:**
- `segment_id` (string, optional): Belirli bir segment için

**Response:**
```json
[
  {
    "id": 1,
    "signal_id": 304,
    "segment_id": "segment_123",
    "timestamp": "2025-01-14T10:30:00Z",
    "vehicle_count": 271.0,
    "traffic_density": 0.75,
    "expected_2h": 0.82
  }
]
```

**Önemli Alanlar:**
- `traffic_density`: 0-1 arası yoğunluk (0 = boş, 1 = tıkalı)
- `expected_2h`: 2 saat sonrası tahmin (0-1 arası)
- `segment_id` veya `signal_id`: Haritada gösterim için ID

---

#### 2. Trafik Tahmini (Son N Saat)

**Endpoint:** `GET /api/v1/traffic-density/forecast`

**Query Parameters:**
- `segment_id` (string, optional)
- `signal_id` (int, optional)
- `hours` (int, default: 2, min: 1, max: 24): Son N saat

**Response:** (aynı format, birden fazla kayıt)

---

### 🌫️ Hava Kalitesi (Public)

**Endpoint:** `GET /api/v1/air-quality/current`

**Response:**
```json
{
  "pm25": 45.2,
  "pm10": 62.8,
  "aqi": 65,
  "quality": "moderate",
  "latitude": 40.1828,
  "longitude": 29.0665,
  "timestamp": "2025-01-14T10:30:00Z"
}
```

---

### 🌳 Gölgeli Rotalar (Public)

**Endpoint:** `GET /api/v1/shadow-routes/`

**Query Parameters:**
- `shaded_only` (bool): Sadece gölgeli rotalar
- `lit_only` (bool): Sadece aydınlatmalı rotalar

---

### 🌍 Çeviri Servisi (Public)

#### Desteklenen Diller

**Endpoint:** `GET /api/v1/translations/supported`

**Response:**
```json
{
  "languages": [
    {"code": "tr", "name": "Türkçe"},
    {"code": "en", "name": "English"},
    {"code": "ar", "name": "العربية"}
  ]
}
```

#### Metin Çevirisi

**Endpoint:** `POST /api/v1/translations/translate`

**Request Body:**
```json
{
  "text": "Merhaba",
  "source_lang": "tr",
  "target_lang": "en"
}
```

**Response:**
```json
{
  "translated_text": "Hello",
  "source_lang": "tr",
  "target_lang": "en"
}
```

---

## 🏛️ Belediye Paneli Endpoint'leri

**Not:** Belediye paneli endpoint'leri için `municipality` veya `admin` rolü gereklidir.

### 📊 Şikayet Yönetimi

#### 1. Tüm Şikayetleri Listele

**Endpoint:** `GET /api/v1/municipality/complaints`

**Headers:**
```
Authorization: Bearer <municipality_token>
```

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 20)
- `status_filter` (string): pending, in_progress, resolved, rejected
- `category_filter` (string): road_damage, lighting, vb.
- `priority_filter` (string): low, medium, high, urgent
- `date_from` (datetime): Başlangıç tarihi
- `date_to` (datetime): Bitiş tarihi
- `sort_by` (string): created_at, urgency_score, priority
- `sort_order` (string): asc, desc

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "user_id": 1,
      "title": "Yolda büyük çukur var",
      "description": "...",
      "category": "road_damage",
      "status": "pending",
      "priority": "high",
      "urgency_score": 0.85,
      "ai_verified": true,
      "ai_verification_score": 0.92,
      "created_at": "2025-01-14T10:30:00Z",
      "images": [...],
      "feedbacks": []
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

---

#### 2. Şikayet Detayı

**Endpoint:** `GET /api/v1/municipality/complaints/{complaint_id}`

**Response:** (Tek bir şikayet objesi, tüm detaylarla)

---

#### 3. Şikayet Durumunu Güncelle

**Endpoint:** `PUT /api/v1/municipality/complaints/{complaint_id}`

**Request Body:**
```json
{
  "status": "in_progress",  // pending, in_progress, resolved, rejected
  "priority": "urgent",     // low, medium, high, urgent
  "urgency_score": 0.9      // 0-1 arası (opsiyonel)
}
```

**Response:** (Güncellenmiş şikayet objesi)

---

#### 4. Şikayete Geri Bildirim Ekle

**Endpoint:** `POST /api/v1/municipality/complaints/{complaint_id}/feedback`

**Request Body:**
```json
{
  "message": "Şikayetiniz alınmıştır. İlgili birimimize iletildi.",
  "template_id": null  // veya hazır şablon ID'si (opsiyonel)
}
```

**Hazır Şablonlar:**
- `GET /api/v1/municipality/feedback/templates` - Tüm şablonları listele

**Response:**
```json
{
  "id": 789,
  "complaint_id": 123,
  "message": "Şikayetiniz alınmıştır...",
  "created_at": "2025-01-14T11:00:00Z",
  "created_by": "Belediye Personeli"
}
```

---

#### 5. Şikayetleri JSON Olarak İndir

**Endpoint:** `GET /api/v1/municipality/complaints/export`

**Query Parameters:** (listeleme ile aynı filtreler)

**Response:** (JSON dosyası, Content-Type: application/json)

**JavaScript Örneği:**
```javascript
const exportComplaints = async (filters = {}) => {
  const token = localStorage.getItem('access_token');
  const queryParams = new URLSearchParams(filters);
  
  const response = await fetch(
    `http://localhost:8000/api/v1/municipality/complaints/export?${queryParams}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `sikayetler_${new Date().toISOString()}.json`;
  a.click();
};
```

---

#### 6. Şikayetler GeoJSON Formatında

**Endpoint:** `GET /api/v1/municipality/complaints/geojson`

**Query Parameters:** (listeleme ile aynı filtreler)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [29.0665, 40.1828]
      },
      "properties": {
        "id": 123,
        "title": "Yolda büyük çukur var",
        "category": "road_damage",
        "status": "pending",
        "priority": "high",
        "urgency_score": 0.85
      }
    }
  ]
}
```

**Harita Entegrasyonu:**
```javascript
const loadComplaintsGeoJSON = async () => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(
    'http://localhost:8000/api/v1/municipality/complaints/geojson',
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const geojson = await response.json();
  
  // Leaflet/Mapbox ile göster
  L.geoJSON(geojson, {
    pointToLayer: (feature, latlng) => {
      const color = getColorByPriority(feature.properties.priority);
      return L.circleMarker(latlng, { color, radius: 8 });
    }
  }).addTo(map);
};
```

---

#### 7. İstatistikler

**Endpoint:** `GET /api/v1/municipality/complaints/stats/overview`

**Response:**
```json
{
  "total": 150,
  "pending": 45,
  "in_progress": 30,
  "resolved": 70,
  "rejected": 5,
  "by_category": {
    "road_damage": 50,
    "lighting": 30,
    "traffic": 20
  },
  "by_priority": {
    "urgent": 10,
    "high": 40,
    "medium": 80,
    "low": 20
  },
  "avg_urgency_score": 0.65
}
```

---

### 🚦 Trafik Risk Analizi (Belediye)

**Endpoint:** `GET /api/v1/traffic-risk/segments`

**Response:**
```json
[
  {
    "segment_id": "segment_123",
    "risk_score": 0.85,
    "risk_level": "high",
    "current_density": 0.75,
    "expected_2h": 0.82,
    "complaint_count_24h": 5,
    "avg_urgency_24h": 0.8
  }
]
```

---

## 🗺️ 3D Harita Entegrasyonu

### Trafik Yoğunluğu Görselleştirme

**Adım 1: Veriyi Al**
```javascript
const loadTrafficData = async () => {
  const response = await fetch(
    'http://localhost:8000/api/v1/traffic-density/forecast/current'
  );
  const forecasts = await response.json();
  return forecasts;
};
```

**Adım 2: Renklendirme**
```javascript
const getColorByDensity = (density) => {
  // 0 = yeşil, 0.5 = sarı, 1 = kırmızı
  if (density < 0.3) return '#4CAF50'; // Yeşil
  if (density < 0.6) return '#FFD93D'; // Sarı
  if (density < 0.8) return '#FF8E53'; // Turuncu
  return '#F44336'; // Kırmızı
};
```

**Adım 3: 3D Haritada Göster (Three.js Örneği)**
```javascript
const visualizeTraffic = async () => {
  const forecasts = await loadTrafficData();
  
  forecasts.forEach(forecast => {
    // Segment koordinatlarını al (segment_id'den)
    const segment = getSegmentCoordinates(forecast.segment_id);
    
    // 3D çizgi oluştur
    const geometry = new THREE.BufferGeometry().setFromPoints(
      segment.coordinates.map(coord => new THREE.Vector3(...coord))
    );
    
    const color = getColorByDensity(forecast.traffic_density);
    const material = new THREE.LineBasicMaterial({ color });
    const line = new THREE.Line(geometry, material);
    
    scene.add(line);
  });
};
```

**Adım 4: Zaman Seçici (Şimdi / +2 Saat)**
```javascript
const [timeMode, setTimeMode] = useState('current'); // 'current' veya '2h'

const getDensityValue = (forecast) => {
  return timeMode === 'current' 
    ? forecast.traffic_density 
    : forecast.expected_2h;
};

// Buton:
<button onClick={() => setTimeMode(timeMode === 'current' ? '2h' : 'current')}>
  {timeMode === 'current' ? 'Şimdi' : '+2 Saat'}
</button>
```

---

## 📝 Şikayet Sistemi Detayları

### AI Özellikleri

Her şikayet oluşturulduğunda:

1. **Kategori Düzeltme:** AI, kullanıcının seçtiği kategoriyi kontrol eder. Yanlışsa düzeltir.
2. **Aciliyet Skoru:** 0-1 arası skor hesaplanır (0 = düşük, 1 = çok acil)
3. **Priority Belirleme:**
   - `urgent`: urgency_score > 0.8
   - `high`: urgency_score > 0.6
   - `medium`: urgency_score > 0.4
   - `low`: urgency_score <= 0.4

**Response'da AI Bilgileri:**
```json
{
  "ai_verified": true,
  "ai_verification_score": 0.92,
  "ai_category_suggestion": "road_damage",
  "urgency_score": 0.85,
  "priority": "high"
}
```

---

### Fotoğraf Yükleme

- **Maksimum Dosya Boyutu:** 10 MB
- **Desteklenen Formatlar:** JPEG, PNG, WebP
- **Maksimum Fotoğraf Sayısı:** 5
- **Storage:** Supabase Storage (public URL'ler döner)

**Fotoğraf URL'si:**
```
http://localhost:8000/uploads/complaints/{complaint_id}/{filename}
```

---

## 🚦 Trafik Verileri

### Veri Yapısı

**TrafficForecast Modeli:**
- `segment_id` (string): Segment ID (harita için)
- `signal_id` (int): Trafik ışığı ID
- `timestamp` (datetime): Veri zamanı
- `vehicle_count` (float): Araç sayısı
- `traffic_density` (float): 0-1 arası yoğunluk
- `expected_2h` (float): 2 saat sonrası tahmin (0-1)

**Not:** 4 saatlik tahmin verisi yok, sadece 2 saatlik mevcut.

---

## ⚠️ Hata Yönetimi

### Hata Formatı

Tüm hatalar şu formatta döner:

```json
{
  "detail": "Hata mesajı"
}
```

### HTTP Status Kodları

- `200 OK`: Başarılı
- `201 Created`: Oluşturuldu
- `400 Bad Request`: Geçersiz istek
- `401 Unauthorized`: Token eksik/geçersiz
- `403 Forbidden`: Yetki yok
- `404 Not Found`: Kayıt bulunamadı
- `422 Unprocessable Entity`: Validasyon hatası
- `500 Internal Server Error`: Sunucu hatası

### Token Süresi Doldu

**401 Unauthorized** hatası alırsan:

```javascript
const apiCall = async (url, options = {}) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.status === 401) {
    // Token süresi dolmuş, yeniden login
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    return;
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Bir hata oluştu');
  }
  
  return await response.json();
};
```

---

## 💻 Örnek Kodlar

### Axios ile API Client

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Token interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (401 handling)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Kullanım:
const complaints = await api.get('/complaints/');
const newComplaint = await api.post('/complaints/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
```

---

### React Hook Örneği

```jsx
import { useState, useEffect } from 'react';

const useComplaints = () => {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchComplaints = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('http://localhost:8000/api/v1/complaints/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) throw new Error('Yüklenemedi');
        
        const data = await response.json();
        setComplaints(data.items);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchComplaints();
  }, []);

  return { complaints, loading, error };
};
```

---

## 📚 Ek Kaynaklar

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## 🆘 Sorun Giderme

### API'ye Bağlanamıyorum

1. API'nin çalıştığından emin ol: `curl http://localhost:8000/health`
2. CORS hatası alıyorsan, backend'de CORS ayarlarını kontrol et
3. Port 8000'in kullanılabilir olduğundan emin ol

### 403 Forbidden Hatası

- Token'ın doğru gönderildiğinden emin ol
- Kullanıcı rolünün endpoint için yeterli olduğunu kontrol et
- Belediye endpoint'leri için `municipality` veya `admin` rolü gerekir

### Fotoğraf Yüklenemiyor

- Dosya boyutunun 10 MB'den küçük olduğundan emin ol
- Formatın JPEG/PNG/WebP olduğunu kontrol et
- FormData kullandığından emin ol (JSON değil)

---

## 📞 İletişim

Soruların için backend geliştiricisiyle iletişime geçebilirsin.

---

**Son Güncelleme:** 2025-01-14  
**API Versiyonu:** v1.0.0
