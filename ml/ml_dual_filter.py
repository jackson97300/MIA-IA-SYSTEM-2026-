#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
ML DUAL FILTER - Filtre ML asymétrique par symbole et sens
═══════════════════════════════════════════════════════════════════════════════

Utilise la complémentarité des modèles ES/NQ/RTY (Phase 3) :
- ES  : 63.8% Accuracy | PF 6.35  | 40 features ES-specific
- NQ  : 68.8% Accuracy | PF 19.02 | 46 features NQ-specific
- RTY : 66.2% Accuracy | PF 14.62 | 40 features RTY-specific

Usage:
    filter = MLDualFilter(
        model_path_es="ml/models/lgbm_ES_latest.pkl",
        model_path_nq="ml/models/lgbm_NQ_latest.pkl",
        model_path_rty="ml/models/lgbm_RTY_latest.pkl",
        thresholds={
            "ES": {"UP": 0.64, "DOWN": None},  # None = pass-through
            "NQ": {"UP": None, "DOWN": 0.60},
            "RTY": {"UP": 0.65, "DOWN": 0.65}
        },
        modes={
            "ES": {"UP": "required", "DOWN": "advisory"},
            "NQ": {"UP": "advisory", "DOWN": "required"},
            "RTY": {"UP": "required", "DOWN": "required"}
        }
    )

Auteur : MIA_IA_SYSTEM
Date : 06 Novembre 2025 (Phase 3 - RTY intégré)
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

logger = logging.getLogger(__name__)


@dataclass
class MLPrediction:
    """Prédiction ML avec confiance"""
    direction: str  # "UP" ou "DOWN"
    confidence: float  # Probabilité [0-1]
    binary_proba: Tuple[float, float]  # (P(DOWN), P(UP))


@dataclass
class MLDecision:
    """Décision finale du filtre"""
    accepted: bool
    reason: str
    prediction: Optional[MLPrediction] = None
    threshold_used: Optional[float] = None
    mode: str = "required"  # "required" ou "advisory"
    latency_ms: float = 0.0


class MLDualFilter:
    """
    Filtre ML avec seuils asymétriques par symbole et sens (Phase 3 : ES + NQ + RTY)

    Stratégie :
    - ES/UP : required (bloquant) avec seuil élevé
    - ES/DOWN : advisory (non-bloquant, shadow)
    - NQ/UP : advisory (non-bloquant, shadow)
    - NQ/DOWN : required (bloquant) avec seuil élevé
    - RTY/UP : required (bloquant)
    - RTY/DOWN : required (bloquant)
    """

    def __init__(
        self,
        model_path_es: str,
        model_path_nq: str,
        model_path_rty: str,
        thresholds: Dict[str, Dict[str, Optional[float]]],
        modes: Dict[str, Dict[str, str]],
        enabled: bool = True,
        feature_names_path: Optional[str] = None,
        base_threshold: float = 0.70,
        logger = None
    ):
        """
        Args:
            model_path_es: Chemin modèle ES
            model_path_nq: Chemin modèle NQ
            model_path_rty: Chemin modèle RTY (Phase 3)
            thresholds: Seuils par symbole/sens {"ES": {"UP": 0.64, "DOWN": None}, ...}
            modes: Modes par symbole/sens {"ES": {"UP": "required", "DOWN": "advisory"}, ...}
            enabled: Activer/désactiver globalement
            feature_names_path: Chemin feature_names (optionnel)
            base_threshold: Seuil de base (défaut 0.70)
            logger: Logger personnalisé (optionnel)
        """
        self.enabled = enabled
        self.thresholds = thresholds
        self.modes = modes
        self.base_threshold = base_threshold

        # Logger personnalisé ou global
        if logger:
            self.logger = logger
        else:
            import logging
            self.logger = logging.getLogger(__name__)

        # Charger modèles
        self.logger.info("🔥 Chargement MLDualFilter (Phase 3: ES + NQ + RTY)")
        self.model_es, self.feature_names_es = self._load_model(model_path_es)
        self.model_nq, self.feature_names_nq = self._load_model(model_path_nq)
        self.model_rty, self.feature_names_rty = self._load_model(model_path_rty)

        self.logger.info(f"✅ ES  : {len(self.feature_names_es)} features")
        self.logger.info(f"✅ NQ  : {len(self.feature_names_nq)} features")
        self.logger.info(f"✅ RTY : {len(self.feature_names_rty)} features")

        # Stats
        self.stats = {
            "ES": {"UP": {"total": 0, "accepted": 0, "rejected": 0, "advisory": 0},
                   "DOWN": {"total": 0, "accepted": 0, "rejected": 0, "advisory": 0}},
            "NQ": {"UP": {"total": 0, "accepted": 0, "rejected": 0, "advisory": 0},
                   "DOWN": {"total": 0, "accepted": 0, "rejected": 0, "advisory": 0}},
            "RTY": {"UP": {"total": 0, "accepted": 0, "rejected": 0, "advisory": 0},
                    "DOWN": {"total": 0, "accepted": 0, "rejected": 0, "advisory": 0}}
        }

        self.logger.info(f"✅ MLDualFilter initialisé (Phase 3)")
        self.logger.info(f"   ES/UP   : {modes['ES']['UP']} @ {thresholds['ES']['UP']}")
        self.logger.info(f"   ES/DOWN : {modes['ES']['DOWN']} @ {thresholds['ES'].get('DOWN', 'None')}")
        self.logger.info(f"   NQ/UP   : {modes['NQ']['UP']} @ {thresholds['NQ'].get('UP', 'None')}")
        self.logger.info(f"   NQ/DOWN : {modes['NQ']['DOWN']} @ {thresholds['NQ']['DOWN']}")
        self.logger.info(f"   RTY/UP  : {modes['RTY']['UP']} @ {thresholds['RTY']['UP']}")
        self.logger.info(f"   RTY/DOWN: {modes['RTY']['DOWN']} @ {thresholds['RTY']['DOWN']}")

    def _load_model(self, path: str):
        """Charge modèle pickle et extrait feature names"""
        try:
            with open(path, 'rb') as f:
                models = pickle.load(f)

            # Si c'est un ensemble (liste), extraire feature names du premier modèle
            if isinstance(models, list):
                # Gérer CalibratedClassifierCV
                first_model = models[0]
                if hasattr(first_model, 'calibrated_classifiers_'):
                    # CalibratedClassifierCV : accéder au modèle de base
                    base_model = first_model.calibrated_classifiers_[0].estimator
                    feature_names = list(base_model.booster_.feature_name())
                elif hasattr(first_model, 'booster_'):
                    # LightGBM direct
                    feature_names = list(first_model.booster_.feature_name())
                else:
                    raise ValueError(f"Type de modèle non supporté : {type(first_model)}")
                self.logger.info(f"✅ Ensemble de {len(models)} modèles chargé : {path}")
            else:
                # Gérer CalibratedClassifierCV
                if hasattr(models, 'calibrated_classifiers_'):
                    # CalibratedClassifierCV : accéder au modèle de base
                    base_model = models.calibrated_classifiers_[0].estimator
                    feature_names = list(base_model.booster_.feature_name())
                elif hasattr(models, 'booster_'):
                    # LightGBM direct
                    feature_names = list(models.booster_.feature_name())
                else:
                    raise ValueError(f"Type de modèle non supporté : {type(models)}")
                self.logger.info(f"✅ Modèle chargé : {path}")

            return models, feature_names
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement {path}: {e}")
            raise

    def _load_feature_names(self, path: str):
        """Charge feature names depuis JSON"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.feature_names_es = data.get("ES", None)
            self.feature_names_nq = data.get("NQ", None)
            self.feature_names_rty = data.get("RTY", None)
            self.logger.info(f"✅ Feature names chargés")
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de charger feature names: {e}")

    def validate_signal(
        self,
        signal: Dict,
        ml_ready_snapshot: Dict,
        log_json: bool = True
    ) -> MLDecision:
        """
        Valide un signal avec le filtre ML

        Args:
            signal: {"strategy": "...", "side": "UP"/"DOWN", "symbol": "ES"/"NQ"}
            ml_ready_snapshot: Snapshot ML_READY actuel
            log_json: Logger en JSON structuré

        Returns:
            MLDecision avec accepted, reason, prediction, etc.
        """
        t_start = time.perf_counter()

        if not self.enabled:
            return MLDecision(
                accepted=True,
                reason="ML filter disabled",
                mode="disabled",
                latency_ms=0.0
            )

        symbol = signal.get("symbol", "ES")
        side = signal["side"]  # "UP" ou "DOWN"

        # Récupérer seuil et mode
        threshold = self.thresholds.get(symbol, {}).get(side, None)
        mode = self.modes.get(symbol, {}).get(side, "advisory")

        # Si None → pass-through (advisory)
        if threshold is None:
            self.stats[symbol][side]["advisory"] += 1
            self.stats[symbol][side]["total"] += 1

            latency_ms = (time.perf_counter() - t_start) * 1000

            if log_json:
                self._log_json(symbol, signal, side, None, None, threshold, mode, True, latency_ms)

            return MLDecision(
                accepted=True,
                reason=f"{symbol}/{side} pass-through (advisory)",
                mode=mode,
                latency_ms=latency_ms
            )

        # Prédiction
        try:
            prediction = self._predict(symbol, ml_ready_snapshot)
        except Exception as e:
            logger.error(f"❌ Erreur prédiction ML: {e}")
            # En cas d'erreur, on accepte (fail-safe)
            return MLDecision(
                accepted=True,
                reason=f"ML error (fail-safe): {e}",
                mode="error",
                latency_ms=(time.perf_counter() - t_start) * 1000
            )

        # Vérifier confiance selon le sens
        if side == "UP":
            confidence = prediction.binary_proba[1]  # P(UP)
        else:  # DOWN
            confidence = prediction.binary_proba[0]  # P(DOWN)

        accepted = confidence >= threshold

        # Mise à jour stats
        self.stats[symbol][side]["total"] += 1
        if mode == "advisory":
            self.stats[symbol][side]["advisory"] += 1
        elif accepted:
            self.stats[symbol][side]["accepted"] += 1
        else:
            self.stats[symbol][side]["rejected"] += 1

        latency_ms = (time.perf_counter() - t_start) * 1000

        # Log JSON structuré
        if log_json:
            self._log_json(symbol, signal, side, prediction, confidence, threshold, mode, accepted, latency_ms)

        # En mode advisory, toujours accepter
        if mode == "advisory":
            return MLDecision(
                accepted=True,
                reason=f"{symbol}/{side} advisory (conf={confidence:.3f}, thr={threshold})",
                prediction=prediction,
                threshold_used=threshold,
                mode=mode,
                latency_ms=latency_ms
            )

        # En mode required, bloquer si conf < threshold
        if not accepted:
            return MLDecision(
                accepted=False,
                reason=f"{symbol}/{side} rejected: conf={confidence:.3f} < {threshold}",
                prediction=prediction,
                threshold_used=threshold,
                mode=mode,
                latency_ms=latency_ms
            )

        return MLDecision(
            accepted=True,
            reason=f"{symbol}/{side} accepted: conf={confidence:.3f} >= {threshold}",
            prediction=prediction,
            threshold_used=threshold,
            mode=mode,
            latency_ms=latency_ms
        )

    def _predict(self, symbol: str, ml_ready_snapshot: Dict) -> MLPrediction:
        """
        Prédit direction et confiance

        Args:
            symbol: "ES", "NQ" ou "RTY"
            ml_ready_snapshot: Snapshot ML_READY

        Returns:
            MLPrediction
        """
        # Sélectionner modèle et feature names
        if symbol == "ES":
            models = self.model_es
            feature_names = self.feature_names_es
        elif symbol == "NQ":
            models = self.model_nq
            feature_names = self.feature_names_nq
        elif symbol == "RTY":
            models = self.model_rty
            feature_names = self.feature_names_rty
        else:
            raise ValueError(f"Symbole non supporté : {symbol}")

        # Créer DataFrame directement depuis snapshot avec feature names
        # Extraire valeurs dans l'ordre des feature_names
        row = {}
        for fname in feature_names:
            # Chercher la valeur dans le snapshot (gérer nested dict avec '.')
            if '.' in fname:
                parts = fname.split('.')
                value = ml_ready_snapshot
                try:
                    for part in parts:
                        value = value.get(part, {})
                    row[fname] = float(value) if value != {} else 0.0
                except:
                    row[fname] = 0.0
            else:
                row[fname] = float(ml_ready_snapshot.get(fname, 0.0))

        X_df = pd.DataFrame([row], columns=feature_names)

        # Prédiction (gère ensemble ou modèle unique)
        if isinstance(models, list):
            # Ensemble : moyenne des prédictions
            probas = np.array([model.predict_proba(X_df)[0] for model in models])
            proba = probas.mean(axis=0)
        else:
            proba = models.predict_proba(X_df)[0]

        # Direction = classe avec max proba
        direction = "UP" if proba[1] > proba[0] else "DOWN"
        confidence = max(proba)

        return MLPrediction(
            direction=direction,
            confidence=confidence,
            binary_proba=(float(proba[0]), float(proba[1]))
        )

    def _extract_features(self, ml_ready_snapshot: Dict) -> List[float]:
        """
        Extrait features depuis snapshot ML_READY

        TODO: Adapter selon votre format exact
        """
        # Exemple simple : flatten toutes les valeurs numériques
        features = []

        # Ajouter features de base
        for key in ['mid', 'spread', 'volume', 'delta', 'vwap']:
            features.append(ml_ready_snapshot.get(key, 0.0))

        # Ajouter features avancées (adapter selon vos features)
        if 'dom_features' in ml_ready_snapshot:
            dom = ml_ready_snapshot['dom_features']
            features.extend([
                dom.get('imbalance_1_3', 0.0),
                dom.get('total_bid_volume', 0.0),
                dom.get('total_ask_volume', 0.0)
            ])

        # TODO: Ajouter toutes vos features (250+)
        # features.extend([...])

        return features

    def _log_json(
        self,
        symbol: str,
        signal: Dict,
        side: str,
        prediction: Optional[MLPrediction],
        confidence: Optional[float],
        threshold: Optional[float],
        mode: str,
        accepted: bool,
        latency_ms: float
    ):
        """Log JSON structuré pour analytics"""
        log_data = {
            "component": "ml_filter",
            "timestamp": time.time(),
            "symbol": symbol,
            "strategy": signal.get("strategy", "unknown"),
            "side": side,
            "ml_dir": prediction.direction if prediction else None,
            "prob_down": round(prediction.binary_proba[0], 4) if prediction else None,
            "prob_up": round(prediction.binary_proba[1], 4) if prediction else None,
            "confidence": round(confidence, 4) if confidence else None,
            "threshold": threshold,
            "mode": mode,
            "accepted": accepted,
            "latency_ms": round(latency_ms, 2)
        }
        logger.info(json.dumps(log_data))

    def get_stats(self) -> Dict:
        """Retourne stats d'utilisation"""
        return self.stats

    def print_stats(self):
        """Affiche stats formatées"""
        self.logger.info("\n" + "="*70)
        self.logger.info("📊 ML DUAL FILTER - STATISTIQUES (Phase 3)")
        self.logger.info("="*70)

        for symbol in ["ES", "NQ", "RTY"]:
            for side in ["UP", "DOWN"]:
                stats = self.stats[symbol][side]
                total = stats["total"]
                if total == 0:
                    continue

                accept_rate = stats["accepted"] / total * 100 if total > 0 else 0
                reject_rate = stats["rejected"] / total * 100 if total > 0 else 0
                advisory_rate = stats["advisory"] / total * 100 if total > 0 else 0

                self.logger.info(f"\n{symbol}/{side} :")
                self.logger.info(f"  Total : {total}")
                self.logger.info(f"  Accepted : {stats['accepted']} ({accept_rate:.1f}%)")
                self.logger.info(f"  Rejected : {stats['rejected']} ({reject_rate:.1f}%)")
                self.logger.info(f"  Advisory : {stats['advisory']} ({advisory_rate:.1f}%)")

        self.logger.info("="*70)
