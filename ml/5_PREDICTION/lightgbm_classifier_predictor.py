"""
Predictor optimisé pour le classifier LightGBM WIN/LOSS.
Utilise seuil de décision optimal (0.45) au lieu de 0.50.
"""

import pickle
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Optional
import importlib
import sys

# Initialiser logger AVANT le try/except
logger = logging.getLogger(__name__)

# ✅ CORRIGÉ: Import FeatureEngineer pour calculer features engineered
try:
    feature_eng_module = importlib.import_module('ml.3_FEATURES.feature_engineering_lightgbm')
    FeatureEngineer = feature_eng_module.FeatureEngineer
    FEATURE_ENGINEERING_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ FeatureEngineer non disponible: {e}")
    FEATURE_ENGINEERING_AVAILABLE = False
    # Fallback: créer une classe simple si module manquant
    class FeatureEngineer:
        def engineer_features(self, df, include_meta=False):
            return df


class LightGBMClassifierPredictor:
    """Predictor avec seuil optimal et contexte MenthorQ."""

    def __init__(self, model_path: str = "ml/models/lightgbm_quality_v1.pkl", threshold: float = 0.45):
        """
        Initialise le predictor.

        Args:
            model_path: Chemin vers le modèle .pkl
            threshold: Seuil de décision (optimal: 0.45, défaut sklearn: 0.50)
        """
        self.model_path = Path(model_path)
        self.threshold = threshold
        self.model = None
        self.scaler = None
        self.feature_names = None

        # ✅ CORRIGÉ: Initialiser FeatureEngineer pour calculer features engineered
        if FEATURE_ENGINEERING_AVAILABLE:
            self.feature_engineer = FeatureEngineer()
            logger.debug("✅ FeatureEngineer initialisé pour classifier")
        else:
            self.feature_engineer = None
            logger.warning("⚠️ FeatureEngineer non disponible - features engineered manquantes")

        # Charger modèle
        self._load_model()

        logger.info(f"✅ LightGBMClassifierPredictor initialisé")
        logger.info(f"   Seuil décision: {self.threshold:.2f}")
        logger.info(f"   Features: {len(self.feature_names)}")
        logger.info(f"   Feature Engineering: {'ACTIF' if self.feature_engineer else 'INACTIF'}")

    def _load_model(self):
        """Charge modèle + scaler + metadata."""

        if not self.model_path.exists():
            raise FileNotFoundError(f"Modèle introuvable: {self.model_path}")

        with open(self.model_path, 'rb') as f:
            saved = pickle.load(f)

        self.model = saved['model']
        self.scaler = saved.get('scaler')
        self.feature_names = saved['feature_names']

        logger.info(f"📂 Modèle chargé: {self.model_path}")

    def predict(self, snapshot: Dict, return_proba: bool = False) -> Dict:
        """
        Prédit WIN/LOSS pour un snapshot.

        Args:
            snapshot: Dict avec features du snapshot ML_READY brut
            return_proba: Si True, retourne aussi la probabilité

        Returns:
            Dict avec 'prediction' (0/1), 'confidence', 'win_proba'
        """

        # ✅ CORRIGÉ: Appliquer feature engineering AVANT extraction features
        # Convertir snapshot dict en DataFrame pour FeatureEngineer
        df_snapshot = pd.DataFrame([snapshot])

        # Appliquer feature engineering si disponible
        if self.feature_engineer:
            try:
                df_engineered = self.feature_engineer.engineer_features(df_snapshot, include_meta=False)
                # Convertir DataFrame en dict pour extraction features
                snapshot_engineered = df_engineered.iloc[0].to_dict()
            except Exception as e:
                logger.warning(f"⚠️ Erreur feature engineering: {e} - utiliser snapshot brut")
                snapshot_engineered = snapshot
        else:
            snapshot_engineered = snapshot

        # Construire DataFrame depuis snapshot avec features engineered
        df = pd.DataFrame([snapshot_engineered])

        # Filtrer features
        exclude_cols = [
            'win', 'pnl_ticks', 'duration_minutes', 'mae', 'mfe',
            'outcome', 'quality_score', 'entry_time', 'exit_time',
            'symbol', 'action', 'entry_price', 'sl_price', 'tp1_price', 'tp2_price'
        ]

        X = df[[c for c in df.columns if c in self.feature_names and c not in exclude_cols]]

        # Vérifier features manquantes
        missing = set(self.feature_names) - set(X.columns)
        if missing:
            # ✅ CORRIGÉ: Logger seulement si > 5 features manquantes (éviter spam)
            if len(missing) > 5:
                logger.warning(f"⚠️ Features manquantes ({len(missing)}): {list(missing)[:5]}...")
            else:
                logger.debug(f"⚠️ Features manquantes: {missing}")
            for feat in missing:
                X[feat] = 0.0

        # Réordonner colonnes
        X = X[self.feature_names]

        # Scaler
        if self.scaler:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X.values

        # Prédiction probabilités
        y_proba = self.model.predict_proba(X_scaled)[0]
        win_proba = y_proba[1]

        # Prédiction avec seuil custom
        prediction = 1 if win_proba >= self.threshold else 0

        # Confidence = distance au seuil
        confidence = abs(win_proba - self.threshold)

        result = {
            'prediction': prediction,
            'label': 'WIN' if prediction == 1 else 'LOSS',
            'win_probability': float(win_proba),
            'loss_probability': float(y_proba[0]),
            'confidence': float(confidence),
            'threshold': self.threshold
        }

        return result

    def batch_predict(self, snapshots: list) -> pd.DataFrame:
        """
        Prédictions sur batch de snapshots.

        Args:
            snapshots: Liste de dicts avec features

        Returns:
            DataFrame avec colonnes: prediction, win_proba, confidence
        """

        results = []
        for snap in snapshots:
            pred = self.predict(snap)
            results.append(pred)

        return pd.DataFrame(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test predictor
    predictor = LightGBMClassifierPredictor(threshold=0.45)

    print(f"\n✅ Predictor prêt avec seuil optimal: {predictor.threshold}")
    print(f"   Features: {len(predictor.feature_names)}")
    print(f"\nGain attendu:")
    print(f"   Seuil 0.50 (défaut) → Accuracy: 59.7%, F1: 30.4%")
    print(f"   Seuil 0.45 (optimal) → Accuracy: 55.3%, F1: 65.5% 🔥")
