"""
Trafik Verisi İşleme Servisi
XLSX ve KML dosyalarını işleyerek trafik verilerini hazırlar
"""
import os
import re
from typing import List, Optional
from pathlib import Path
import pandas as pd
import geopandas as gpd
import xml.etree.ElementTree as ET
import numpy as np


class TrafficDataProcessor:
    """Trafik verilerini işleyen sınıf"""
    
    MONTH_TR = {
        "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, 
        "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7, 
        "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
        "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12
    }
    
    def __init__(self, traffic_dir: str, kml_path: Optional[str] = None):
        """
        Args:
            traffic_dir: XLSX dosyalarının bulunduğu dizin
            kml_path: KML dosyasının yolu (opsiyonel)
        """
        self.traffic_dir = Path(traffic_dir)
        self.kml_path = Path(kml_path) if kml_path else None
    
    def parse_date_from_filename(self, fname: str) -> pd.Timestamp:
        """Dosya adından tarih parse eder"""
        s = os.path.basename(fname).lower()
        m = re.search(r"\(\s*(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})\s*\)", s, flags=re.IGNORECASE)
        if not m:
            raise ValueError(f"Tarih parse edilemedi: {fname}")
        day = int(m.group(1))
        month_name = m.group(2).strip()
        year = int(m.group(3))
        month = self.MONTH_TR.get(month_name, None)
        if month is None:
            raise ValueError(f"Ay ismi tanınmadı: {month_name} (dosya: {fname})")
        return pd.Timestamp(year=year, month=month, day=day)
    
    def parse_signal_id_from_filename(self, fname: str) -> int:
        """Dosya adından sinyal ID parse eder"""
        s = os.path.basename(fname)
        m = re.search(r"\b(\d{3})\b", s)
        if not m:
            raise ValueError(f"signal_id parse edilemedi: {fname}")
        return int(m.group(1))
    
    def find_time_col(self, df: pd.DataFrame) -> str:
        """Zaman kolonunu bulur"""
        for c in df.columns:
            cl = str(c).strip().lower()
            if cl in ["time", "saat", "zaman"]:
                return c
        return df.columns[0]
    
    def find_vehicle_col(self, df: pd.DataFrame) -> str:
        """Araç sayısı kolonunu bulur"""
        for c in df.columns:
            cl = str(c).strip().lower()
            if "toplam" in cl and ("taşıt" in cl or "tasit" in cl):
                return c
            if "vehicle" in cl and "count" in cl:
                return c
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            raise ValueError("Araç sayısı kolonu bulunamadı.")
        return num_cols[-1]
    
    def normalize_time_to_hhmmss(self, x) -> Optional[str]:
        """Zamanı HH:MM:SS formatına normalize eder"""
        if pd.isna(x):
            return None
        if hasattr(x, "strftime"):
            return x.strftime("%H:%M:%S")
        s = str(x).strip()
        if re.fullmatch(r"\d{1,2}:\d{2}", s):
            return s + ":00"
        if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", s):
            return s
        return s
    
    def process_xlsx_files(self) -> pd.DataFrame:
        """XLSX dosyalarını işleyerek trafik verisi DataFrame'i oluşturur"""
        xlsx_files = sorted(self.traffic_dir.glob("*.xlsx"))
        if not xlsx_files:
            raise FileNotFoundError(f"XLSX dosyası bulunamadı: {self.traffic_dir}")
        
        all_rows = []
        for f in xlsx_files:
            signal_id = self.parse_signal_id_from_filename(str(f))
            date = self.parse_date_from_filename(str(f))
            
            raw = pd.read_excel(f)
            time_col = self.find_time_col(raw)
            veh_col = self.find_vehicle_col(raw)
            
            tmp = raw[[time_col, veh_col]].copy()
            tmp.columns = ["time_raw", "vehicle_count"]
            tmp["signal_id"] = signal_id
            tmp["date"] = date
            
            tmp["time"] = tmp["time_raw"].apply(self.normalize_time_to_hhmmss)
            tmp = tmp.dropna(subset=["time", "vehicle_count"])
            
            tmp["timestamp"] = pd.to_datetime(
                tmp["date"].dt.strftime("%Y-%m-%d") + " " + tmp["time"], 
                errors="coerce"
            )
            tmp = tmp.dropna(subset=["timestamp"])
            
            tmp["vehicle_count"] = pd.to_numeric(tmp["vehicle_count"], errors="coerce")
            tmp = tmp.dropna(subset=["vehicle_count"])
            
            all_rows.append(tmp[["signal_id", "timestamp", "vehicle_count"]])
        
        traffic_15min = (
            pd.concat(all_rows, ignore_index=True)
            .sort_values(["signal_id", "timestamp"])
            .reset_index(drop=True)
        )
        
        return traffic_15min
    
    def parse_kml_signals(self) -> pd.DataFrame:
        """KML dosyasından sinyalizasyon noktalarını parse eder"""
        if not self.kml_path or not self.kml_path.exists():
            raise FileNotFoundError(f"KML dosyası bulunamadı: {self.kml_path}")
        
        tree = ET.parse(self.kml_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        
        placemarks = root.findall(".//kml:Placemark", ns)
        rows = []
        for pm in placemarks:
            name_el = pm.find("kml:name", ns)
            desc_el = pm.find("kml:description", ns)
            name = (name_el.text or "").strip() if name_el is not None else ""
            desc = (desc_el.text or "").strip() if desc_el is not None else ""
            
            txt = name + " " + desc
            m = re.search(r"\b(\d{3})\b", txt)
            if not m:
                continue
            signal_id = int(m.group(1))
            
            coord_el = pm.find(".//kml:coordinates", ns)
            if coord_el is None or not coord_el.text:
                continue
            
            coord_text = coord_el.text.strip()
            first = coord_text.split()[0]
            parts = first.split(",")
            if len(parts) < 2:
                continue
            
            lon = float(parts[0])
            lat = float(parts[1])
            
            rows.append({"signal_id": signal_id, "lat": lat, "lon": lon, "name": name})
        
        return (
            pd.DataFrame(rows)
            .drop_duplicates(subset=["signal_id"])
            .sort_values("signal_id")
            .reset_index(drop=True)
        )
    
    def fill_traffic_grid(self, traffic_15min: pd.DataFrame) -> pd.DataFrame:
        """15 dakikalık grid'i doldurur (eksik zamanları ekler)"""
        traffic = traffic_15min.copy()
        traffic["timestamp"] = pd.to_datetime(traffic["timestamp"])
        traffic["date"] = traffic["timestamp"].dt.normalize()
        
        base = traffic[["signal_id", "date"]].drop_duplicates().copy()
        minutes = pd.DataFrame({"minute": range(0, 24 * 60, 15)})
        
        base["key"] = 1
        minutes["key"] = 1
        grid = base.merge(minutes, on="key").drop(columns=["key"])
        grid["timestamp"] = grid["date"] + pd.to_timedelta(grid["minute"], unit="m")
        grid = grid.drop(columns=["minute"])
        
        traffic_full = grid.merge(
            traffic[["signal_id", "timestamp", "vehicle_count"]],
            on=["signal_id", "timestamp"],
            how="left"
        ).sort_values(["signal_id", "timestamp"]).reset_index(drop=True)
        
        # Forward fill ile eksik değerleri doldur
        traffic_full["vehicle_count"] = traffic_full.groupby("signal_id")["vehicle_count"].ffill()
        
        return traffic_full

