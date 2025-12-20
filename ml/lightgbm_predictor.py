"""
🎯 LIGHTGBM PREDICTOR - ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Wrapper pour prédiction quality_score en temps réel.
Charge modèle LightGBM + feature engineering + prédiction rapide (<5ms).

Usage en production:
    predictor = LightGBMPredictor.load("ml/models/lightgbm_quality_v1.pkl")
    quality_score = predictor.predict(snapshot)
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Optional, List
import pickle
import numpy as np
import pandas as pd
import importlib

# Ajouter parent au path pour imports
sys.path.append(str(Path(__file__).parent.parent))

# Import conditionnel de FeatureEngineer (module avec chiffre nécessite importlib)
try:
    feature_eng_module = importlib.import_module('ml.3_FEATURES.feature_engineering_lightgbm')
    FeatureEngineer = feature_eng_module.FeatureEngineer
except (ImportError, ModuleNotFoundError):
    # Fallback: créer une classe simple si module manquant
    class FeatureEngineer:
        def engineer_features(self, df, include_meta=False):
            return df

logger = logging.getLogger(__name__)


class LightGBMPredictor:
    """
    Prédicteur LightGBM pour quality_score en temps réel.

    Usage:
        # Load modèle
        predictor = LightGBMPredictor.load("ml/models/lightgbm_quality_v1.pkl")

        # Prédiction
        quality_score = predictor.predict(snapshot_dict)

        # Batch prediction
        scores = predictor.predict_batch(list_of_snapshots)
    """

    def __init__(
        self,
        model,
        feature_names: List[str],
        best_params: Optional[Dict] = None,
        scaler=None
    ):
        """
        Initialise le prédicteur.

        Args:
            model: Modèle LightGBM entraîné
            feature_names: Liste des features attendues
            best_params: Paramètres du modèle
            scaler: Scaler sklearn (optionnel)
        """
        self.model = model
        self.feature_names = feature_names
        self.best_params = best_params
        self.scaler = scaler
        
        # Feature engineer pour calculer features engineered
        self.feature_engineer = FeatureEngineer()

        logger.info("✅ LightGBMPredictor initialisé")
        logger.info(f"   Features: {len(feature_names)}")
        logger.info(f"   Scaler: {scaler is not None}")


    @classmethod
    def load(cls, model_path: str) -> 'LightGBMPredictor':
        """
        Charge un modèle depuis fichier pickle.

        Args:
            model_path: Chemin vers .pkl

        Returns:
            Instance de LightGBMPredictor
        """

        model_file = Path(model_path)

        if not model_file.exists():
            raise FileNotFoundError(f"❌ Modèle non trouvé: {model_path}")

        logger.info(f"📂 Chargement modèle: {model_path}")

        with open(model_file, 'rb') as f:
            data = pickle.load(f)

        predictor = cls(
            model=data['model'],
            feature_names=data['feature_names'],
            best_params=data.get('best_params'),
            scaler=data.get('scaler')
        )

        logger.info(f"✅ Modèle chargé avec succès")

        return predictor


    def _engineer_features_snapshot(self, snapshot: Dict) -> Dict:
        """
        Applique feature engineering sur un snapshot brut.

        Args:
            snapshot: Dict snapshot ML_READY

        Returns:
            Dict avec 90 features engineered
        """

        # Helper: safe divide
        def safe_divide(num, den, default=0.0):
            return num / den if den != 0 else default

        features = {}

        # ═══════════════════════════════════════════════════════
        # 1. COPIER 70 CORE FEATURES (brutes)
        # ═══════════════════════════════════════════════════════

        core_features = [
            # Options (20)
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
            'call_resistance', 'put_support', 'hvl',
            'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
            'menthorq_impact_score', 'menthorq_proximity_strength',
            'confluence_strength', 'confluence_density', 'confluence_proximity',
            'vix', 'volatility_regime', 'atr_ratio',
            'gamma_wall_level',
            # OrderFlow (15)
            'delta', 'cum_delta_day', 'cum_delta_session',
            'deltaPct', 'smart_money_flow', 'institutional_pressure',
            'volume', 'bidvol', 'askvol',
            'bidPct', 'askPct',
            'depth_bid', 'depth_ask', 'depth_imbalance',
            'dom_age_ms',
            # Context (12)
            'vwap', 'd_vwap', 'd_vwap_ticks', 'd_vwap_atr',
            'atr', 'volatility_regime_cont',
            'session_progress', 'session_elapsed_s',
            'mid', 'spread_ticks', 'microprice', 'microgap_n',
            # Advanced (8)
            '1d_max', '1d_min',
            'd_vpoc_ticks', 'd_vah_ticks',
            # Engineered disponibles (10)
            'level1_imbalance', 'micro_imb',
            'corr',
            'mia_bullish_score',
            'distance_to_high_pct', 'distance_to_low_pct',
            'position_in_range',
            'tick_rate_1s', 'tick_rate_3s',
            'pressure_strength'
        ]

        for feat in core_features:
            features[feat] = snapshot.get(feat, 0.0)

        # Extraire nested dicts si nécessaire
        menthor_distances = snapshot.get('menthor_distances', {})
        dom_features = snapshot.get('dom_features', {})
        next_wall = snapshot.get('next_wall', {})

        features['next_wall_dist_ticks'] = next_wall.get('dist_ticks', 9999)
        features['next_wall_strength'] = next_wall.get('strength', 0.0)

        # ═══════════════════════════════════════════════════════
        # 2. CALCULER 20 FEATURES ENGINEERED
        # ═══════════════════════════════════════════════════════

        # RATIOS (10)
        features['delta_intensity'] = safe_divide(
            abs(features['delta']),
            features['volume']
        )

        features['depth_imbalance_ratio'] = safe_divide(
            features['depth_bid'],
            features['depth_ask'],
            default=1.0
        )

        atr_ticks = safe_divide(features['atr'], 0.25, default=20)
        features['vwap_atr_ratio'] = safe_divide(
            features['d_vwap_ticks'],
            atr_ticks
        )

        features['gamma_position'] = safe_divide(
            (features['mid'] - features['hvl']),
            features['atr']
        )

        features['flow_direction'] = features['bidPct'] - features['askPct']

        # GEX proximity min
        gex_distances = []
        for i in range(1, 6):
            gex_level = features.get(f'gex_{i}', 0)
            if gex_level > 0:
                gex_distances.append(abs(features['mid'] - gex_level))
        features['gex_proximity_min'] = min(gex_distances) if gex_distances else 9999.0

        # Range bias
        dist_1d_min = abs(features['mid'] - features['1d_min']) / 0.25
        dist_1d_max = abs(features['1d_max'] - features['mid']) / 0.25
        features['range_bias'] = safe_divide(
            dist_1d_min,
            (dist_1d_min + dist_1d_max),
            default=0.5
        )

        features['efficiency_ratio_placeholder'] = 0.0  # Post-trade only

        # DOM slope ratio
        slope_bid = dom_features.get('slope_bid_1_3', 1.0)
        slope_ask = dom_features.get('slope_ask_1_3', 1.0)
        features['dom_slope_ratio'] = safe_divide(slope_bid, slope_ask, default=1.0)

        features['confluence_delta'] = features['confluence_strength'] * abs(features['deltaPct'])

        # INTERACTIONS (10)
        features['layer1_layer2_interaction'] = (
            features['menthorq_impact_score'] * features['depth_imbalance']
        )

        features['next_wall_weighted'] = safe_divide(
            features['next_wall_strength'],
            abs(features['next_wall_dist_ticks']) + 1
        )

        blind_proximity = 1.0 / (features['gex_proximity_min'] / 10 + 1)
        features['blind_gex_confluence'] = blind_proximity * features['confluence_strength']

        # VWAP regime encoding
        if features['d_vwap_atr'] < -10:
            vwap_regime_encoded = -2
        elif features['d_vwap_atr'] < -5:
            vwap_regime_encoded = -1
        elif features['d_vwap_atr'] > 10:
            vwap_regime_encoded = 2
        elif features['d_vwap_atr'] > 5:
            vwap_regime_encoded = 1
        else:
            vwap_regime_encoded = 0

        # HVL regime encoding
        hvl_regime_encoded = 1 if features['mid'] > features['hvl'] else -1

        features['vwap_regime_encoded'] = vwap_regime_encoded
        features['hvl_regime_encoded'] = hvl_regime_encoded
        features['vwap_hvl_regime'] = vwap_regime_encoded * hvl_regime_encoded

        features['delta_session_ratio'] = safe_divide(
            features['delta'],
            abs(features['cum_delta_session']) + 1
        )

        features['volume_atr_intensity'] = features['volume'] * features['atr_ratio']

        features['approaching_1d_max'] = 1 if dist_1d_max < 50 else 0
        features['approaching_1d_min'] = 1 if dist_1d_min < 50 else 0

        features['range_expansion'] = safe_divide(
            (features['1d_max'] - features['1d_min']),
            features['atr'],
            default=1.0
        )

        features['vix_atr_volatility'] = features['vix'] * features['atr_ratio']

        return features


    def predict(
        self,
        snapshot: Dict,
        return_features: bool = False
    ) -> float:
        """
        Prédit quality_score pour un snapshot.

        Args:
            snapshot: Dict snapshot ML_READY brut
            return_features: Si True, retourne aussi les features engineered

        Returns:
            float: Quality score prédit (0-100)
            ou (score, features_dict) si return_features=True
        """

        # Convertir snapshot dict en DataFrame pour FeatureEngineer
        df_snapshot = pd.DataFrame([snapshot])
        
        # Appliquer feature engineering
        try:
            df_engineered = self.feature_engineer.engineer_features(df_snapshot, include_meta=False)
        except Exception as e:
            logger.warning(f"⚠️ Erreur feature engineering: {e}")
            df_engineered = df_snapshot  # Fallback sans features engineered
        
        # ⚠️ IMPORTANT: Exclure les RESULTATS trade si présents (data leakage)
        exclude_cols = [
            'quality_score',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
            # === METADATA ===
            't_ms', 'sym', 'symbol_base', 'source_file'
        ]
        
        # Construire input pour modèle (ordre features important)
        X_row = []
        for feat_name in self.feature_names:
            if feat_name in df_engineered.columns and feat_name not in exclude_cols:
                X_row.append(df_engineered[feat_name].iloc[0])
            else:
                X_row.append(0.0)  # Feature manquante = 0
        
        # ⚠️ FIX: Convertir en DataFrame avec noms de colonnes pour éviter warnings
        # Le scaler et le modèle ont été entraînés avec des DataFrames pandas
        X = pd.DataFrame([X_row], columns=self.feature_names)

        # Scaling si nécessaire
        if self.scaler is not None:
            X_scaled = self.scaler.transform(X)
            # Reconvertir en DataFrame pour conserver les noms de colonnes
            if isinstance(X_scaled, np.ndarray):
                X = pd.DataFrame(X_scaled, columns=self.feature_names)
            else:
                X = X_scaled

        # Prédiction
        # ⚠️ FIX 16/11/2025: Le modèle est un classifier, pas un regressor
        # On utilise la probabilité de WIN pour calculer le quality score
        if hasattr(self.model, 'predict_proba'):
            # Classifier: utiliser probabilité WIN (classe 1)
            proba_win = self.model.predict_proba(X)[0][1]  # 0.0 à 1.0
            score = proba_win * 100  # Convertir en 0-100
        else:
            # Regressor: utiliser prédiction directe
            score = self.model.predict(X)[0]

        # Clip entre 0-100
        score = np.clip(score, 0, 100)

        if return_features:
            return score, df_engineered.iloc[0].to_dict()
        else:
            return score


    def predict_batch(
        self,
        snapshots: List[Dict]
    ) -> np.ndarray:
        """
        Prédit quality_scores pour une liste de snapshots.

        Args:
            snapshots: Liste de dicts snapshots ML_READY

        Returns:
            Array des scores prédits
        """

        scores = []
        for snapshot in snapshots:
            score = self.predict(snapshot, return_features=False)
            scores.append(score)

        return np.array(scores)


    def get_model_info(self) -> Dict:
        """
        Retourne informations sur le modèle.

        Returns:
            Dict avec infos modèle
        """

        info = {
            'model_type': type(self.model).__name__,
            'n_features': len(self.feature_names),
            'feature_names': self.feature_names,
            'best_params': self.best_params,
            'has_scaler': self.scaler is not None
        }

        return info


# ═══════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Test du prédicteur."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    # ═══════════════════════════════════════════════════════════
    # 1. CHARGER MODÈLE
    # ═══════════════════════════════════════════════════════════

    MODEL_PATH = "ml/models/lightgbm_quality_v1.pkl"

    print(f"\n{'='*70}")
    print(f"🎯 TEST LIGHTGBM PREDICTOR")
    print(f"{'='*70}\n")

    if not Path(MODEL_PATH).exists():
        print(f"❌ Modèle non trouvé: {MODEL_PATH}")
        print(f"   Exécutez d'abord: python ml/train_lightgbm_model.py")
        exit(1)

    predictor = LightGBMPredictor.load(MODEL_PATH)

    # Afficher infos modèle
    info = predictor.get_model_info()
    print(f"📊 Infos modèle:")
    print(f"   Type: {info['model_type']}")
    print(f"   Features: {info['n_features']}")
    print(f"   Scaler: {info['has_scaler']}")
    print(f"\n{'='*70}\n")

    # ═══════════════════════════════════════════════════════════
    # 2. SNAPSHOT EXEMPLE (EXCELLENT SETUP)
    # ═══════════════════════════════════════════════════════════

    snapshot_excellent = {
        # Options
        'gex_1': 6010.00, 'gex_2': 6005.00, 'gex_3': 6015.00,
        'gex_4': 5995.00, 'gex_5': 6020.00,
        'call_resistance': 6020.00, 'put_support': 5980.00,
        'hvl': 5995.00, 'gamma_wall_level': 6020.00,
        'blind_spot_0': 6008.00, 'blind_spot_1': 6012.00, 'blind_spot_2': 6003.00,
        'menthorq_impact_score': 0.45, 'menthorq_proximity_strength': 0.38,
        'confluence_strength': 0.85, 'confluence_density': 0.72, 'confluence_proximity': 15.5,
        'vix': 18.5, 'volatility_regime': 1, 'atr_ratio': 15.2,

        # OrderFlow
        'delta': 850, 'cum_delta_day': 3200, 'cum_delta_session': 1800,
        'deltaPct': 0.15, 'smart_money_flow': 0.12, 'institutional_pressure': 0.15,
        'volume': 5800, 'bidvol': 3350, 'askvol': 2450,
        'bidPct': 0.578, 'askPct': 0.422,
        'depth_bid': 850, 'depth_ask': 520, 'depth_imbalance': 0.24,
        'dom_age_ms': 125,

        # Context
        'vwap': 6010.50, 'd_vwap': -10.50, 'd_vwap_ticks': -42.0, 'd_vwap_atr': -8.5,
        'atr': 4.95, 'volatility_regime_cont': 0.18,
        'session_progress': 0.45, 'session_elapsed_s': 14500,
        'mid': 6000.00, 'spread_ticks': 1, 'microprice': 6000.12, 'microgap_n': -0.002,

        # Advanced
        '1d_max': 6025.00, '1d_min': 5985.00,
        'd_vpoc_ticks': -35.0, 'd_vah_ticks': -80.0,

        # Engineered disponibles
        'level1_imbalance': -0.045, 'micro_imb': -0.048,
        'corr': 0.992,
        'mia_bullish_score': 0.65,
        'distance_to_high_pct': 0.42, 'distance_to_low_pct': 0.25,
        'position_in_range': 0.625,
        'tick_rate_1s': 1.2, 'tick_rate_3s': 1.1,
        'pressure_strength': 0.15,

        # Nested
        'next_wall': {'dist_ticks': -18, 'strength': 0.42, 'side': 'put'},
        'dom_features': {'slope_bid_1_3': 5.2, 'slope_ask_1_3': 3.1},
        'menthor_distances': {}
    }

    # ═══════════════════════════════════════════════════════════
    # 3. PRÉDICTION
    # ═══════════════════════════════════════════════════════════

    print("🔮 Prédiction EXCELLENT SETUP:\n")

    score, features = predictor.predict(snapshot_excellent, return_features=True)

    print(f"   Quality Score prédit: {score:.1f}/100\n")

    # Afficher quelques features engineered
    print(f"   📊 Features engineered (sample):")
    print(f"      delta_intensity: {features['delta_intensity']:.4f}")
    print(f"      depth_imbalance_ratio: {features['depth_imbalance_ratio']:.2f}")
    print(f"      vwap_atr_ratio: {features['vwap_atr_ratio']:.2f}")
    print(f"      gamma_position: {features['gamma_position']:.2f}")
    print(f"      gex_proximity_min: {features['gex_proximity_min']:.1f}")
    print(f"      confluence_delta: {features['confluence_delta']:.4f}")

    print(f"\n{'='*70}")
    print(f"✅ TEST TERMINÉ")
    print(f"{'='*70}\n")





