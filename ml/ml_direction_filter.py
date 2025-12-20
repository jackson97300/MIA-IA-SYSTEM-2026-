#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
ML DIRECTION FILTER - FILTRE ADDITIONNEL POUR VALIDATION SIGNAUX
═══════════════════════════════════════════════════════════════════════════════

Filtre ML qui valide/invalide les signaux des stratégies de trading

Fonctionnement :
1. Une stratégie génère un signal (LONG ou SHORT)
2. Les garde-fous globaux valident le signal
3. Le MLDirectionFilter prédit la direction du marché dans 15 min
4. Si ML confirme la direction → Signal accepté
5. Sinon → Signal rejeté

Intégration dans launch_optimized_ml_ready.py :
    from ml.ml_direction_filter import MLDirectionFilter

    self.ml_filter = MLDirectionFilter(
        model_path="ml/models/lgbm_direction_15min_latest.pkl",
        features_path="ml/models/lgbm_direction_15min_features_latest.json",
        confidence_threshold=0.65,
        enabled=True
    )

    # Dans process_signal()
    if self.ml_filter.enabled:
        if not self.ml_filter.validate_signal(signal, ml_ready_data):
            logger.info(f"❌ ML rejette {signal.strategy_name}")
            return None

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml.feature_engineering import RealtimeFeatureCalculator

logger = logging.getLogger(__name__)


@dataclass
class MLPrediction:
    """Résultat d'une prédiction ML"""
    direction: str  # 'UP', 'DOWN', 'FLAT'
    confidence: float  # 0.0 - 1.0
    probabilities: Dict[str, float]  # {'DOWN': 0.1, 'FLAT': 0.2, 'UP': 0.7}
    timestamp: float
    latency_ms: float


@dataclass
class MLFilterDecision:
    """Décision du filtre ML"""
    accepted: bool
    reason: str
    prediction: MLPrediction


class MLDirectionFilter:
    """
    Filtre ML pour validation de signaux de trading

    Usage:
        # Initialisation
        ml_filter = MLDirectionFilter(
            model_path="ml/models/lgbm_direction_15min_latest.pkl",
            features_path="ml/models/lgbm_direction_15min_features_latest.json",
            confidence_threshold=0.65,
            enabled=True
        )

        # Validation d'un signal
        decision = ml_filter.validate_signal(
            signal={'strategy': 'hybrid', 'side': 'LONG'},
            ml_ready_snapshot=ml_ready_data
        )

        if decision.accepted:
            # Exécuter le trade
            execute_trade(signal)
        else:
            # Rejeter le trade
            logger.info(f"ML rejette : {decision.reason}")
    """

    def __init__(
        self,
        model_path: str,
        features_path: str,
        confidence_threshold: float = 0.65,
        enabled: bool = True,
        use_realtime_calculator: bool = True,
        log_predictions: bool = True
    ):
        """
        Initialise le filtre ML

        Args:
            model_path: Chemin vers modèle LightGBM (.pkl)
            features_path: Chemin vers liste features (.json)
            confidence_threshold: Seuil minimum de confidence (0.65 = 65%)
            enabled: Active/désactive le filtre (pour A/B testing)
            use_realtime_calculator: Utilise RealtimeFeatureCalculator
            log_predictions: Log toutes les prédictions
        """
        self.model_path = Path(model_path)
        self.features_path = Path(features_path)
        self.confidence_threshold = confidence_threshold
        self.enabled = enabled
        self.use_realtime_calculator = use_realtime_calculator
        self.log_predictions = log_predictions

        # Statistiques
        self.stats = {
            'n_predictions': 0,
            'n_accepted': 0,
            'n_rejected': 0,
            'n_rejected_confidence': 0,
            'n_rejected_direction': 0,
            'n_rejected_flat': 0,
            'total_latency_ms': 0.0,
        }

        # Historique prédictions (pour monitoring)
        self.prediction_history = []
        self.max_history_size = 1000

        # Charger modèle et features
        self._load_model()
        self._load_features()

        # Initialiser feature calculator si demandé
        if self.use_realtime_calculator:
            self._init_realtime_calculator()

        logger.info(f"\n{'='*70}")
        logger.info(f"🤖 ML DIRECTION FILTER INITIALISÉ")
        logger.info(f"{'='*70}")
        logger.info(f"   Modèle : {self.model_path}")
        logger.info(f"   Features : {len(self.feature_names)}")
        logger.info(f"   Seuil confidence : {self.confidence_threshold:.1%}")
        logger.info(f"   Statut : {'✅ ACTIVÉ' if self.enabled else '⚠️ DÉSACTIVÉ'}")
        logger.info(f"{'='*70}")

    def _load_model(self):
        """Charge le modèle LightGBM"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"❌ Modèle introuvable : {self.model_path}")

        logger.info(f"📂 Chargement modèle : {self.model_path}")

        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)

        logger.info(f"✅ Modèle chargé")

    def _load_features(self):
        """Charge la liste des features"""
        if not self.features_path.exists():
            raise FileNotFoundError(f"❌ Features introuvables : {self.features_path}")

        logger.info(f"📂 Chargement features : {self.features_path}")

        with open(self.features_path, 'r') as f:
            self.feature_names = json.load(f)

        logger.info(f"✅ {len(self.feature_names)} features chargées")

    def _init_realtime_calculator(self):
        """Initialise le RealtimeFeatureCalculator"""
        # Extraire les features de base (sans LAGs/Rolling)
        base_features = [
            feat for feat in self.feature_names
            if not ('_lag_' in feat or '_ma_' in feat or '_vs_ma_' in feat or '_slope' in feat)
        ]

        # Déterminer les features qui ont des LAGs/Rolling
        features_with_engineering = set()
        for feat in self.feature_names:
            if '_lag_' in feat:
                base_feat = feat.split('_lag_')[0]
                features_with_engineering.add(base_feat)
            elif '_ma_' in feat:
                base_feat = feat.split('_ma_')[0]
                features_with_engineering.add(base_feat)

        features_with_engineering = list(features_with_engineering)

        # Périodes LAG et Rolling (standards)
        lag_periods = [1, 5, 10, 20, 60]
        rolling_windows = [20, 60, 300]

        self.realtime_calculator = RealtimeFeatureCalculator(
            feature_names=features_with_engineering,
            lag_periods=lag_periods,
            rolling_windows=rolling_windows,
            buffer_size=300
        )

        logger.info(f"✅ RealtimeFeatureCalculator initialisé")
        logger.info(f"   Features trackées : {len(features_with_engineering)}")

    def predict(self, ml_ready_snapshot: dict) -> MLPrediction:
        """
        Fait une prédiction sur snapshot ML_READY

        Args:
            ml_ready_snapshot: Snapshot ML_READY actuel

        Returns:
            MLPrediction avec direction et confidence
        """
        start_time = time.time()

        # Calculer features dérivées si RealtimeCalculator activé
        if self.use_realtime_calculator:
            all_features = self.realtime_calculator.update(ml_ready_snapshot)
        else:
            all_features = ml_ready_snapshot

        # Extraire features nécessaires
        X = []
        missing_features = []

        for feat in self.feature_names:
            if feat in all_features:
                value = all_features[feat]

                # Gérer valeurs nested (dict)
                if isinstance(value, dict):
                    value = 0.0  # Fallback

                X.append(float(value) if value is not None else 0.0)
            else:
                missing_features.append(feat)
                X.append(0.0)  # Fallback

        if missing_features:
            logger.warning(f"⚠️ {len(missing_features)} features manquantes : {missing_features[:5]}...")

        X = np.array(X).reshape(1, -1)

        # Prédiction
        y_proba = self.model.predict_proba(X)[0]
        y_pred = np.argmax(y_proba)

        # Mapper classe → direction
        class_to_direction = {0: 'DOWN', 1: 'FLAT', 2: 'UP'}
        direction = class_to_direction[y_pred]
        confidence = y_proba[y_pred]

        probabilities = {
            'DOWN': float(y_proba[0]),
            'FLAT': float(y_proba[1]),
            'UP': float(y_proba[2])
        }

        # Latency
        latency_ms = (time.time() - start_time) * 1000

        # Créer objet prédiction
        prediction = MLPrediction(
            direction=direction,
            confidence=confidence,
            probabilities=probabilities,
            timestamp=time.time(),
            latency_ms=latency_ms
        )

        # Statistiques
        self.stats['n_predictions'] += 1
        self.stats['total_latency_ms'] += latency_ms

        # Historique
        if self.log_predictions:
            self.prediction_history.append(prediction)
            if len(self.prediction_history) > self.max_history_size:
                self.prediction_history.pop(0)

        return prediction

    def validate_signal(
        self,
        signal: dict,
        ml_ready_snapshot: dict
    ) -> MLFilterDecision:
        """
        Valide un signal de stratégie avec le filtre ML

        Args:
            signal: Signal de stratégie {'strategy': str, 'side': 'LONG'|'SHORT', ...}
            ml_ready_snapshot: Snapshot ML_READY actuel

        Returns:
            MLFilterDecision (accepted=True|False, reason, prediction)
        """
        # Si filtre désactivé → accepter automatiquement
        if not self.enabled:
            return MLFilterDecision(
                accepted=True,
                reason="ML filter disabled",
                prediction=None
            )

        # Prédiction ML
        prediction = self.predict(ml_ready_snapshot)

        # Extraire side du signal
        signal_side = signal.get('side', '').upper()

        if signal_side not in ['LONG', 'SHORT']:
            logger.warning(f"⚠️ Signal side invalide : {signal_side}")
            return MLFilterDecision(
                accepted=False,
                reason=f"Invalid signal side: {signal_side}",
                prediction=prediction
            )

        # Vérifier confidence
        if prediction.confidence < self.confidence_threshold:
            self.stats['n_rejected'] += 1
            self.stats['n_rejected_confidence'] += 1

            return MLFilterDecision(
                accepted=False,
                reason=f"ML confidence too low: {prediction.confidence:.1%} < {self.confidence_threshold:.1%}",
                prediction=prediction
            )

        # Vérifier direction
        # ML dit FLAT → rejeter (pas de conviction)
        if prediction.direction == 'FLAT':
            self.stats['n_rejected'] += 1
            self.stats['n_rejected_flat'] += 1

            return MLFilterDecision(
                accepted=False,
                reason=f"ML predicts FLAT (neutral market)",
                prediction=prediction
            )

        # Vérifier alignement ML direction <-> Signal side
        ml_aligned = (
            (signal_side == 'LONG' and prediction.direction == 'UP') or
            (signal_side == 'SHORT' and prediction.direction == 'DOWN')
        )

        if not ml_aligned:
            self.stats['n_rejected'] += 1
            self.stats['n_rejected_direction'] += 1

            return MLFilterDecision(
                accepted=False,
                reason=f"ML direction mismatch: signal={signal_side}, ML={prediction.direction}",
                prediction=prediction
            )

        # ✅ ACCEPTÉ : ML confirme le signal
        self.stats['n_accepted'] += 1

        return MLFilterDecision(
            accepted=True,
            reason=f"ML confirms: {prediction.direction} with {prediction.confidence:.1%} confidence",
            prediction=prediction
        )

    def get_stats(self) -> Dict:
        """
        Retourne les statistiques du filtre

        Returns:
            Dict avec statistiques
        """
        stats = self.stats.copy()

        # Taux
        if stats['n_predictions'] > 0:
            stats['acceptance_rate'] = stats['n_accepted'] / stats['n_predictions']
            stats['rejection_rate'] = stats['n_rejected'] / stats['n_predictions']
            stats['avg_latency_ms'] = stats['total_latency_ms'] / stats['n_predictions']
        else:
            stats['acceptance_rate'] = 0.0
            stats['rejection_rate'] = 0.0
            stats['avg_latency_ms'] = 0.0

        return stats

    def print_stats(self):
        """Affiche les statistiques"""
        stats = self.get_stats()

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 ML FILTER - STATISTIQUES")
        logger.info(f"{'='*70}")
        logger.info(f"   Prédictions totales : {stats['n_predictions']:,}")
        logger.info(f"   Acceptées           : {stats['n_accepted']:,} ({stats['acceptance_rate']:.1%})")
        logger.info(f"   Rejetées            : {stats['n_rejected']:,} ({stats['rejection_rate']:.1%})")
        logger.info(f"      └─ Confidence    : {stats['n_rejected_confidence']:,}")
        logger.info(f"      └─ Direction     : {stats['n_rejected_direction']:,}")
        logger.info(f"      └─ FLAT          : {stats['n_rejected_flat']:,}")
        logger.info(f"   Latence moyenne     : {stats['avg_latency_ms']:.2f}ms")
        logger.info(f"{'='*70}")

    def get_prediction_distribution(self) -> Dict:
        """
        Analyse la distribution des prédictions récentes

        Returns:
            Dict avec distribution
        """
        if not self.prediction_history:
            return {}

        # Compter directions
        directions = [p.direction for p in self.prediction_history]

        n_up = directions.count('UP')
        n_down = directions.count('DOWN')
        n_flat = directions.count('FLAT')
        n_total = len(directions)

        # Confidence moyenne
        avg_confidence = np.mean([p.confidence for p in self.prediction_history])

        return {
            'n_predictions': n_total,
            'up_count': n_up,
            'down_count': n_down,
            'flat_count': n_flat,
            'up_pct': n_up / n_total,
            'down_pct': n_down / n_total,
            'flat_pct': n_flat / n_total,
            'avg_confidence': avg_confidence,
        }

    def reset_stats(self):
        """Reset les statistiques"""
        self.stats = {
            'n_predictions': 0,
            'n_accepted': 0,
            'n_rejected': 0,
            'n_rejected_confidence': 0,
            'n_rejected_direction': 0,
            'n_rejected_flat': 0,
            'total_latency_ms': 0.0,
        }

        self.prediction_history = []

        if self.use_realtime_calculator:
            self.realtime_calculator.reset()

        logger.info("✅ Statistiques ML filter reset")

    def set_confidence_threshold(self, new_threshold: float):
        """
        Change le seuil de confidence

        Args:
            new_threshold: Nouveau seuil (0.0 - 1.0)
        """
        old_threshold = self.confidence_threshold
        self.confidence_threshold = new_threshold

        logger.info(f"🎯 Seuil confidence changé : {old_threshold:.1%} → {new_threshold:.1%}")

    def enable(self):
        """Active le filtre ML"""
        self.enabled = True
        logger.info("✅ ML filter ACTIVÉ")

    def disable(self):
        """Désactive le filtre ML"""
        self.enabled = False
        logger.info("⚠️ ML filter DÉSACTIVÉ")

    def log_decision(
        self,
        decision: MLFilterDecision,
        signal: dict,
        trade_result: Optional[str] = None
    ):
        """
        Log une décision du filtre (pour télémétrie)

        Args:
            decision: Décision du filtre
            signal: Signal de stratégie
            trade_result: Résultat du trade si exécuté ('TP1', 'SL', etc.)
        """
        log_entry = {
            'timestamp': time.time(),
            'strategy': signal.get('strategy', 'unknown'),
            'side': signal.get('side', 'unknown'),
            'accepted': decision.accepted,
            'reason': decision.reason,
        }

        if decision.prediction:
            log_entry.update({
                'ml_direction': decision.prediction.direction,
                'ml_confidence': decision.prediction.confidence,
                'ml_prob_up': decision.prediction.probabilities['UP'],
                'ml_prob_down': decision.prediction.probabilities['DOWN'],
                'ml_prob_flat': decision.prediction.probabilities['FLAT'],
                'ml_latency_ms': decision.prediction.latency_ms,
            })

        if trade_result:
            log_entry['trade_result'] = trade_result

        # Log JSON (parsable pour analyse)
        logger.info(f"ML_FILTER_DECISION: {json.dumps(log_entry)}")


# ═══════════════════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════════════════

def example_usage():
    """Exemple d'utilisation du MLDirectionFilter"""

    logger.info("\n" + "="*70)
    logger.info("🧪 EXEMPLE D'UTILISATION ML DIRECTION FILTER")
    logger.info("="*70)

    # 1. Initialiser le filtre
    ml_filter = MLDirectionFilter(
        model_path="ml/models/lgbm_direction_15min_latest.pkl",
        features_path="ml/models/lgbm_direction_15min_features_latest.json",
        confidence_threshold=0.65,
        enabled=True
    )

    # 2. Simuler un snapshot ML_READY
    ml_ready_snapshot = {
        'close': 6878.75,
        'mid': 6878.88,
        'level1_imbalance': -0.074,
        'smart_money_flow': -0.050,
        'delta': -239,
        'd_vwap': -17.72,
        'cum_delta_session': -16451,
        'battle_navale_signal_strength': 0.236,
        'pressure_strength': 0.353,
        'menthor_distances': {'call': -116, 'put': -316},
        'symbol_is_nq': 0,
        # ... (autres features)
    }

    # 3. Simuler un signal de stratégie
    signal = {
        'strategy': 'hybrid_strategy',
        'side': 'LONG',
        'entry_price': 6878.75,
        'confidence': 0.75,
    }

    # 4. Valider le signal
    decision = ml_filter.validate_signal(signal, ml_ready_snapshot)

    # 5. Traiter la décision
    if decision.accepted:
        logger.info(f"✅ Signal ACCEPTÉ : {decision.reason}")
        logger.info(f"   ML: {decision.prediction.direction} (conf={decision.prediction.confidence:.1%})")
        # → Exécuter le trade
    else:
        logger.info(f"❌ Signal REJETÉ : {decision.reason}")
        logger.info(f"   ML: {decision.prediction.direction} (conf={decision.prediction.confidence:.1%})")
        # → Skip le trade

    # 6. Log pour télémétrie
    ml_filter.log_decision(decision, signal)

    # 7. Statistiques
    ml_filter.print_stats()


if __name__ == '__main__':
    """Test du module"""
    logging.basicConfig(level=logging.INFO)

    try:
        example_usage()
    except FileNotFoundError as e:
        logger.warning(f"⚠️ Fichiers modèle non trouvés (normal si pas encore entraîné)")
        logger.info(f"💡 Lance d'abord : python ml/train_ml_direction_15min.py")



