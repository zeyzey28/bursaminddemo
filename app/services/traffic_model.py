"""
Trafik Yoğunluğu Tahmin Modeli
LightGBM ile 2 saat sonrası trafik yoğunluğu tahmini
"""
import os
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Dict, Optional, List
from pathlib import Path


class TrafficDensityModel:
    """Trafik yoğunluğu tahmin modeli"""
    
    HORIZON = 8  # 15dk * 8 = 2 saat
    
    FEATURES = [
        "traffic_density",
        "lag_1", "lag_2", "lag_4", "lag_8", "lag_12", "lag_24",
        "rm_1h", "rm_2h", "trend_2h",
        "hour", "weekday", "is_peak", "hour_sin", "hour_cos",
        "signal_id"
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: Eğitilmiş model dosyasının yolu
        """
        self.model_path = Path(model_path) if model_path else None
        self.model: Optional[lgb.Booster] = None
        self.features: Optional[List[str]] = None
        
        if self.model_path and self.model_path.exists():
            self.load_model()
    
    def load_model(self):
        """Eğitilmiş modeli yükler"""
        if not self.model_path or not self.model_path.exists():
            raise FileNotFoundError(f"Model dosyası bulunamadı: {self.model_path}")
        
        bundle = joblib.load(self.model_path)
        self.model = bundle["model"]
        self.features = bundle["features"]
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Feature engineering yapar"""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["signal_id", "timestamp"]).reset_index(drop=True)
        
        # Traffic density hesapla
        max_per_signal = df.groupby("signal_id")["vehicle_count"].transform("max").replace(0, np.nan)
        df["traffic_density"] = (df["vehicle_count"] / max_per_signal).clip(0, 1).fillna(0)
        
        g = df.groupby("signal_id", group_keys=False)
        
        # LAG features
        df["lag_1"] = g["traffic_density"].shift(1)
        df["lag_2"] = g["traffic_density"].shift(2)
        df["lag_4"] = g["traffic_density"].shift(4)
        df["lag_8"] = g["traffic_density"].shift(8)
        df["lag_12"] = g["traffic_density"].shift(12)
        df["lag_24"] = g["traffic_density"].shift(24)
        
        # Rolling mean
        df["rm_1h"] = g["traffic_density"].rolling(4, min_periods=2).mean().reset_index(level=0, drop=True)
        df["rm_2h"] = g["traffic_density"].rolling(8, min_periods=3).mean().reset_index(level=0, drop=True)
        
        # Trend
        df["trend_2h"] = g["traffic_density"].diff(8)
        
        # Time features
        df["hour"] = df["timestamp"].dt.hour
        df["weekday"] = df["timestamp"].dt.weekday
        df["is_peak"] = df["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        
        # NaN doldur
        for c in ["lag_1", "lag_2", "lag_4", "lag_8", "lag_12", "lag_24", "rm_1h", "rm_2h", "trend_2h"]:
            df[c] = df[c].fillna(df["traffic_density"])
        
        # Categorical
        df["signal_id"] = df["signal_id"].astype("category")
        
        return df
    
    def train(
        self,
        traffic_full: pd.DataFrame,
        output_path: str,
        train_split: float = 0.8,
        num_boost_round: int = 3000,
        early_stopping_rounds: int = 150
    ) -> Dict:
        """
        Modeli eğitir
        
        Args:
            traffic_full: Doldurulmuş trafik verisi
            output_path: Model kayıt yolu
            train_split: Train/validation split oranı
            num_boost_round: Maksimum iterasyon sayısı
            early_stopping_rounds: Early stopping iterasyon sayısı
            
        Returns:
            Eğitim sonuçları dict'i
        """
        df = self.create_features(traffic_full)
        
        # Target: t+2h
        df["target_density_2h"] = df.groupby("signal_id", observed=False)["traffic_density"].shift(-self.HORIZON)
        train_df = df.dropna(subset=["target_density_2h"]).copy()
        
        # Per-signal split
        parts = []
        for sid, d in train_df.groupby("signal_id", observed=False):
            d = d.sort_values("timestamp")
            cut = int(len(d) * train_split)
            parts.append((d.iloc[:cut], d.iloc[cut:]))
        
        tr = pd.concat([p[0] for p in parts]).sort_values(["signal_id", "timestamp"])
        va = pd.concat([p[1] for p in parts]).sort_values(["signal_id", "timestamp"])
        
        X_tr, y_tr = tr[self.FEATURES], tr["target_density_2h"].astype(float)
        X_va, y_va = va[self.FEATURES], va["target_density_2h"].astype(float)
        
        dtrain = lgb.Dataset(X_tr, label=y_tr, categorical_feature=["signal_id"])
        dvalid = lgb.Dataset(X_va, label=y_va, reference=dtrain, categorical_feature=["signal_id"])
        
        params = dict(
            objective="regression",
            metric="mae",
            learning_rate=0.05,
            num_leaves=63,
            min_data_in_leaf=10,
            feature_fraction=0.9,
            bagging_fraction=0.9,
            bagging_freq=1,
            lambda_l2=1.0,
            seed=42,
            verbosity=-1
        )
        
        self.model = lgb.train(
            params,
            dtrain,
            num_boost_round=num_boost_round,
            valid_sets=[dtrain, dvalid],
            valid_names=["train", "valid"],
            callbacks=[
                lgb.early_stopping(early_stopping_rounds),
                lgb.log_evaluation(50)
            ]
        )
        
        self.features = self.FEATURES
        
        # Modeli kaydet
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "features": self.features}, output_path)
        self.model_path = output_path
        
        return {
            "best_iteration": self.model.best_iteration,
            "train_mae": self.model.best_score["train"]["l1"],
            "valid_mae": self.model.best_score["valid"]["l1"],
            "model_path": str(output_path)
        }
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tahmin yapar
        
        Args:
            df: Feature'ları içeren DataFrame
            
        Returns:
            expected_2h kolonu eklenmiş DataFrame
        """
        if self.model is None:
            raise ValueError("Model yüklenmemiş veya eğitilmemiş!")
        
        df = df.copy()
        df = self.create_features(df)
        
        predictions = self.model.predict(
            df[self.features],
            num_iteration=self.model.best_iteration
        ).clip(0, 1)
        
        df["expected_2h"] = predictions
        
        return df
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Feature importance DataFrame'i döner"""
        if self.model is None:
            raise ValueError("Model yüklenmemiş!")
        
        return pd.DataFrame({
            "feature": self.features,
            "importance_gain": self.model.feature_importance(importance_type="gain"),
            "importance_split": self.model.feature_importance(importance_type="split"),
        }).sort_values("importance_gain", ascending=False)

