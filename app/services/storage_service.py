"""
Supabase Storage Servisi

Fotoğrafları Supabase Storage'da saklar.
Belediye günlük/haftalık/aylık/yıllık raporlar için erişebilir.
"""
import os
import uuid
import httpx
from datetime import datetime
from typing import Optional, Tuple
from fastapi import UploadFile

from app.core.config import settings


class SupabaseStorageService:
    """Supabase Storage ile dosya yönetimi"""
    
    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.api_key = settings.SUPABASE_KEY
        self.bucket_name = settings.SUPABASE_BUCKET
        
    @property
    def headers(self):
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def upload_image(
        self, 
        file: UploadFile, 
        folder: str = "complaints"
    ) -> Tuple[str, str]:
        """
        Fotoğrafı Supabase Storage'a yükle
        
        Args:
            file: Yüklenecek dosya
            folder: Klasör adı (complaints, profiles, etc.)
            
        Returns:
            Tuple[file_path, public_url]
        """
        # Benzersiz dosya adı oluştur
        ext = os.path.splitext(file.filename)[1].lower()
        timestamp = datetime.now().strftime("%Y/%m/%d")
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = f"{folder}/{timestamp}/{unique_name}"
        
        # Dosya içeriğini oku
        content = await file.read()
        
        # Supabase Storage'a yükle
        async with httpx.AsyncClient() as client:
            upload_url = f"{self.base_url}/storage/v1/object/{self.bucket_name}/{file_path}"
            
            response = await client.post(
                upload_url,
                headers={
                    **self.headers,
                    "Content-Type": file.content_type or "application/octet-stream"
                },
                content=content
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Upload failed: {response.text}")
        
        # Public URL oluştur
        public_url = f"{self.base_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
        
        return file_path, public_url
    
    async def delete_image(self, file_path: str) -> bool:
        """
        Fotoğrafı Supabase Storage'dan sil
        
        Args:
            file_path: Silinecek dosyanın yolu
            
        Returns:
            Başarılı ise True
        """
        async with httpx.AsyncClient() as client:
            delete_url = f"{self.base_url}/storage/v1/object/{self.bucket_name}/{file_path}"
            
            response = await client.delete(
                delete_url,
                headers=self.headers
            )
            
            return response.status_code in [200, 204]
    
    async def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Geçici imzalı URL oluştur (private bucket için)
        
        Args:
            file_path: Dosya yolu
            expires_in: URL geçerlilik süresi (saniye)
            
        Returns:
            Signed URL
        """
        async with httpx.AsyncClient() as client:
            sign_url = f"{self.base_url}/storage/v1/object/sign/{self.bucket_name}/{file_path}"
            
            response = await client.post(
                sign_url,
                headers=self.headers,
                json={"expiresIn": expires_in}
            )
            
            if response.status_code == 200:
                data = response.json()
                return f"{self.base_url}/storage/v1{data['signedURL']}"
            
            raise Exception(f"Failed to create signed URL: {response.text}")
    
    def get_public_url(self, file_path: str) -> str:
        """
        Public URL döndür
        
        Args:
            file_path: Dosya yolu
            
        Returns:
            Public URL
        """
        return f"{self.base_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
    
    async def list_files(
        self, 
        folder: str = "", 
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        Klasördeki dosyaları listele
        
        Args:
            folder: Klasör yolu
            limit: Maksimum dosya sayısı
            offset: Başlangıç noktası
            
        Returns:
            Dosya listesi
        """
        async with httpx.AsyncClient() as client:
            list_url = f"{self.base_url}/storage/v1/object/list/{self.bucket_name}"
            
            response = await client.post(
                list_url,
                headers=self.headers,
                json={
                    "prefix": folder,
                    "limit": limit,
                    "offset": offset
                }
            )
            
            if response.status_code == 200:
                return response.json()
            
            return []


# Singleton instance
storage_service = SupabaseStorageService()

