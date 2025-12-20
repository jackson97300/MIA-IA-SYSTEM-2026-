"""
MENTHORQ FIRST METHOD
====================

Méthode basée sur le fichier "NOUVELLE METHODE DE MIA MONTOR Q .txt"

Philosophie :
- **Décideur principal :** MenthorQ/GEX (call/put walls, gamma flip, HVL, extrêmes D1)
- **Validateur :** Orderflow (CVD/NBCV, stacked imbalance, absorption, wicks)
- **Contexte :** VWAP/Volume Profile, VIX, MIA Bullish, Leadership ES/NQ
- **Exécution :** E/U/L structurels, risk management simple

Configuration finale intégrée :
✅ Zones d'entrée : 5 ticks partout
✅ Drawdown : 7 ticks partout ($87.50)
✅ Patience : 15/20/25/30 minutes selon VIX
✅ Tolérance mèches : 3/5/7 ticks selon VIX
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from core.logger import get_logger
from collections import deque

# Imports des composants
from core.menthorq_distance_trading import MenthorQDistanceTrader
from features.leadership_zmom import LeadershipZMom
from core.mia_bullish import BullishScorer
# Import direct pour éviter les problèmes de dépendances
try:
    from automation_modules.orderflow_analyzer import OrderFlowAnalyzer
    ORDERFLOW_AVAILABLE = True
except ImportError:
    OrderFlowAnalyzer = None
    ORDERFLOW_AVAILABLE = False

# Local imports
from core.base_types import (
    MarketData, OrderFlowData, TradingFeatures,
    ES_TICK_SIZE, ES_TICK_VALUE
)
from core.unified_stops import calculate_unified_stops, UNIFIED_STOP_CONFIG

logger = get_logger(__name__)

# === CONFIGURATION MENTHORQ FIRST ===
MENTHORQ_FIRST_CONFIG = {
    "description": "Méthode MenthorQ First basée sur l'expérience utilisateur",
    "version": "1.0.0",

    # === VOS SEUILS INTÉGRÉS ===
    "zones": {
        "width_ticks": {
            "LOW": 5, "MID": 5, "HIGH": 5, "EXTREME": 5
        }
    },
    "drawdown": {
        "max_ticks": {
            "LOW": 7, "MID": 7, "HIGH": 7, "EXTREME": 7
        },
        "max_dollars": {
            "LOW": 87.50, "MID": 87.50, "HIGH": 87.50, "EXTREME": 87.50
        }
    },
    "patience": {
        "minutes": {
            "LOW": 15, "MID": 20, "HIGH": 25, "EXTREME": 30
        }
    },
    "wick_tolerance": {
        "vix_bands": {
            "BAS": {"tolerance_ticks": 3},
            "MOYEN": {"tolerance_ticks": 5},
            "ÉLEVÉ": {"tolerance_ticks": 7}
        }
    },

    # === CONFIGURATION MENTHORQ ===
    "menthorq": {
        "weights": {"mq": 0.55, "of": 0.30, "structure": 0.15},
        "thresholds": {"enter_eff": 0.70},
        "mia": {"gate_long": 0.20, "gate_short": -0.20},
        "leadership": {
            "corr_min": {"LOW": 0.30, "MID": 0.30, "HIGH": 0.45, "EXTREME": 0.60},
            "veto_abs": {"LOW": 1.40, "MID": 1.30, "HIGH": 1.10, "EXTREME": 1.00},
            "bonus_abs": {"LOW": 0.30, "MID": 0.45, "HIGH": 0.60, "EXTREME": 0.75}
        }
    },

    # === CONFIGURATION ORDERFLOW ===
    "orderflow": {
        "min_confirmations": {"LOW": 2, "MID": 2, "HIGH": 3, "EXTREME": 3},
        "fallback_ok": True
    },

    # === CONFIGURATION STRUCTURE ===
    "structure": {
        "buffers": {
            "LOW": {"vwap": 1, "profile": 1},
            "MID": {"vwap": 1, "profile": 1},
            "HIGH": {"vwap": 2, "profile": 2},
            "EXTREME": {"vwap": 3, "profile": 3}
        }
    }
}

class MenthorQFirstResult:
    """Résultat de la méthode MenthorQ First"""

    def __init__(self):
        self.timestamp = pd.Timestamp.now()

        # === ATTRIBUTS PRINCIPAUX ===
        self.action = "NO_SIGNAL"  # Compatible avec script de comparaison
        self.signal_type = "NO_SIGNAL"  # Ancien attribut (rétrocompatibilité)
        self.score = 0.0  # Score final (compatible avec script)
        self.confidence = 0.0  # Ancien attribut (rétrocompatibilité)

        # === SCORES DÉTAILLÉS ===
        self.mq_score = 0.0  # Score MenthorQ (compatible avec script)
        self.menthorq_score = 0.0  # Ancien attribut (rétrocompatibilité)
        self.of_score = 0.0  # Score OrderFlow (compatible avec script)
        self.orderflow_score = 0.0  # Ancien attribut (rétrocompatibilité)
        self.st_score = 0.0  # Score Structure (compatible avec script)
        self.structure_score = 0.0  # Ancien attribut (rétrocompatibilité)
        self.final_score = 0.0  # Score final (rétrocompatibilité)

        # === DONNÉES CONTEXTUELLES ===
        self.mia_bullish = 0.0  # Score MIA Bullish (compatible avec script)
        self.vix_regime = "MID"  # Régime VIX (compatible avec script)
        self.mq_level = {}  # Niveau MenthorQ (compatible avec script)
        self.eul = {}  # Entry/Unwind/Loss (compatible avec script)

        # === AUDIT ET MÉTADONNÉES ===
        self.audit_data = {}
        self.eul_levels = {}  # Ancien attribut (rétrocompatibilité)
        self.calculation_time_ms = 0.0

class MenthorQFirstMethod:
    """
    MÉTHODE MENTHORQ FIRST

    Hiérarchie décisionnelle (ordre strict) :
    1. Trigger MenthorQ (décideur)
    2. Gate Biais — MIA Bullish
    3. Gate Macro — Leadership ES/NQ
    4. Régime VIX (adaptation)
    5. Validation Orderflow (obligatoire)
    6. Contexte Structurel
    7. Fusion & Seuil
    8. Exécution (E/U/L) & Risque
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation méthode MenthorQ First"""
        self.config = {**MENTHORQ_FIRST_CONFIG, **(config or {})}

        # === COMPOSANTS ===
        self.menthorq_trader = MenthorQDistanceTrader()
        self.leadership_engine = LeadershipZMom()
        self.mia_bullish = BullishScorer()
        # Initialisation conditionnelle de l'OrderFlowAnalyzer
        if ORDERFLOW_AVAILABLE:
            self.orderflow_analyzer = OrderFlowAnalyzer({})
        else:
            self.orderflow_analyzer = None

        # === ÉTAT ===
        self.stats = {
            'menthorq_triggers': 0,
            'mia_gates_passed': 0,
            'leadership_gates_passed': 0,
            'orderflow_validations': 0,
            'structure_validations': 0,
            'final_signals': 0
        }

        logger.info("Méthode MenthorQ First initialisée")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> MenthorQFirstResult:
        """
        🔥 NOUVELLE MÉTHODE - Analyse MenthorQ depuis ML_READY

        Exploite directement les scores précalculés :
        - menthorq_confluence (score final)
        - near_gex_2_5 (distance au trigger)
        - dealers_bias (biais dealers)
        - smart_money_flow (validation OrderFlow)
        - institutional_pressure (validation OF)

        AVANTAGES :
        - Pas de recalcul (déjà fait par dumper)
        - Performance < 5ms
        - Source unique de vérité

        Args:
            ml_data: Dict ML_READY complet

        Returns:
            MenthorQFirstResult avec action et scores
        """
        start_time = time.perf_counter()
        result = MenthorQFirstResult()

        try:
            # === LIRE SCORES PRÉCALCULÉS ===
            confluence = ml_data.get('menthorq_confluence', 0.0)
            near_gex = ml_data.get('near_gex_2_5', 999)
            dealers_bias = ml_data.get('dealers_bias', 0.0)
            smart_money_flow = ml_data.get('smart_money_flow', 0.0)
            institutional_pressure = ml_data.get('institutional_pressure', 0.0)

            # === DÉTERMINER ACTION ===
            # Trigger MenthorQ : confluence >= 0.70 ET near_gex <= 10
            if confluence >= 0.70 and near_gex <= 10:
                # Direction depuis dealers_bias
                if dealers_bias > 0.1:
                    action = "GO_LONG"
                elif dealers_bias < -0.1:
                    action = "GO_SHORT"
                else:
                    action = "WAIT"  # Biais neutre

                # Validation OrderFlow (au moins 1 des 2 positif)
                orderflow_ok = (smart_money_flow > 0.1) or (institutional_pressure > 0.1)

                if not orderflow_ok and action != "WAIT":
                    action = "WAIT"  # OrderFlow invalide
            else:
                action = "NO_SIGNAL"

            # === REMPLIR RÉSULTAT ===
            result.action = action
            result.signal_type = action
            result.score = confluence
            result.confidence = confluence

            # Scores détaillés
            result.mq_score = confluence
            result.menthorq_score = confluence
            result.of_score = (smart_money_flow + institutional_pressure) / 2
            result.orderflow_score = result.of_score
            result.st_score = 0.5  # Structure score (default ML_READY)
            result.structure_score = result.st_score
            result.final_score = confluence

            # Données contextuelles
            result.mia_bullish = 0.5 if dealers_bias > 0 else -0.5
            result.vix_regime = self._determine_vix_regime(ml_data.get('vix', 20))

            # MQ level (depuis ML_READY)
            result.mq_level = {
                'level': near_gex,
                'distance': near_gex,
                'type': 'gex_2_5',
                'confluence': confluence
            }

            # EUL levels (simplifiés depuis ML_READY)
            mid_price = ml_data.get('mid', 0)
            result.eul = {
                'entry': mid_price,
                'upside': ml_data.get('next_wall', {}).get('price', mid_price + 10),
                'limit': ml_data.get('put_support', mid_price - 10)
            }
            result.eul_levels = result.eul

            # Audit data
            result.audit_data = {
                'confluence': confluence,
                'near_gex': near_gex,
                'dealers_bias': dealers_bias,
                'smart_money_flow': smart_money_flow,
                'institutional_pressure': institutional_pressure,
                'source': 'ML_READY'
            }

            # Performance
            result.calculation_time_ms = (time.perf_counter() - start_time) * 1000

            # === TRACKING ===
            if action not in ["NO_SIGNAL", "WAIT"]:
                self.stats['final_signals'] += 1
                logger.debug(f"🚀 ML_READY MenthorQ Signal: {action} @ confluence={confluence:.3f}")

            return result

        except Exception as e:
            logger.error(f"❌ Erreur analyze_from_ml_ready: {e}")
            result.audit_data = {'error': str(e), 'source': 'ML_READY_ERROR'}
            result.calculation_time_ms = (time.perf_counter() - start_time) * 1000
            return result

    def analyze_menthorq_first_opportunity(self, es_data: Dict, nq_data: Dict, config: Optional[Dict] = None) -> MenthorQFirstResult:
        """
        ANALYSE OPPORTUNITÉ MENTHORQ FIRST

        Processus en 8 étapes selon votre fichier .txt
        """
        start_time = time.perf_counter()
        result = MenthorQFirstResult()

        try:
            # === 1. TRIGGER MENTHORQ (DÉCIDEUR) ===
            menthorq_result = self.menthorq_trader.decide_mq_distance_integrated(
                es_data, nq_data, config
            )

            if not menthorq_result or menthorq_result.get('action') == 'NO_SIGNAL':
                logger.debug("❌ Pas de trigger MenthorQ")
                return result

            result.menthorq_score = menthorq_result.get('confidence', 0.0)
            self.stats['menthorq_triggers'] += 1
            logger.debug(f"🎯 Trigger MenthorQ: {menthorq_result.get('action')}")

            # === 2. GATE BIAIS — MIA BULLISH ===
            ok_mia, mia_score = self._check_mia_bullish_gate(es_data, menthorq_result)
            if not ok_mia:
                logger.debug("❌ Gate MIA Bullish échoué")
                return result

            self.stats['mia_gates_passed'] += 1
            logger.debug("✅ Gate MIA Bullish passé")

            # === 3. GATE MACRO — LEADERSHIP ES/NQ ===
            leadership_gate = self._check_leadership_gate(es_data, nq_data, menthorq_result)
            if not leadership_gate['allow']:
                logger.debug(f"❌ Gate Leadership échoué: {leadership_gate['reason']}")
                return result

            self.stats['leadership_gates_passed'] += 1
            logger.debug("✅ Gate Leadership passé")

            # === 4. RÉGIME VIX (ADAPTATION) ===
            vix_multiplier = self._get_vix_multiplier(es_data)

            # === 5. VALIDATION ORDERFLOW (OBLIGATOIRE) ===
            orderflow_score = self._validate_orderflow(es_data, menthorq_result)
            if orderflow_score < 0.3:  # Seuil minimum OrderFlow
                logger.debug(f"❌ Validation OrderFlow échouée: {orderflow_score:.3f}")
                return result

            self.stats['orderflow_validations'] += 1
            logger.debug(f"✅ Validation OrderFlow: {orderflow_score:.3f}")

            # === 6. CONTEXTE STRUCTUREL ===
            structure_score = self._analyze_structure_context(es_data, menthorq_result)
            self.stats['structure_validations'] += 1

            # === 7. FUSION & SEUIL ===
            final_score = self._calculate_final_score(
                menthorq_result, mia_score, orderflow_score, structure_score, vix_multiplier
            )

            # === 8. EXÉCUTION (E/U/L) & RISQUE ===
            eul_levels = self._calculate_eul_levels(es_data, menthorq_result)

            # === REMPLIR LE RÉSULTAT ===
            result.action = menthorq_result.get('action', 'NO_SIGNAL')
            result.signal_type = result.action  # Rétrocompatibilité
            result.score = final_score
            result.confidence = final_score  # Rétrocompatibilité

            # Scores détaillés
            result.mq_score = menthorq_result.get('confidence', 0.0)
            result.menthorq_score = result.mq_score  # Rétrocompatibilité
            result.of_score = orderflow_score
            result.orderflow_score = orderflow_score  # Rétrocompatibilité
            result.st_score = structure_score
            result.structure_score = structure_score  # Rétrocompatibilité
            result.final_score = final_score

            # Données contextuelles
            result.mia_bullish = mia_score
            result.vix_regime = self._determine_vix_regime(es_data.get('vix', {}).get('value', 20))
            result.mq_level = menthorq_result.get('mq_level', {})
            result.eul = eul_levels
            result.eul_levels = eul_levels  # Rétrocompatibilité

            # Audit et métadonnées
            result.audit_data = {
                'menthorq_result': menthorq_result,
                'mia_score': mia_score,
                'orderflow_score': orderflow_score,
                'structure_score': structure_score,
                'vix_multiplier': vix_multiplier,
                'leadership_gate': leadership_gate
            }

            # Performance
            result.calculation_time_ms = (time.perf_counter() - start_time) * 1000

            self.stats['final_signals'] += 1
            logger.info(f"🎯 Signal MenthorQ First: {result.action} (score: {result.score:.3f})")

            return result

        except Exception as e:
            logger.error(f"Erreur analyse MenthorQ First: {e}")
            result.audit_data['error'] = str(e)
            result.calculation_time_ms = (time.perf_counter() - start_time) * 1000
            return result

    def _get_vix_multiplier(self, es_data: Dict) -> float:
        """Récupère le multiplicateur VIX"""
        vix_data = es_data.get('vix', {})
        vix_value = vix_data.get('value', 20)
        vix_regime = self._determine_vix_regime(vix_value)
        return self.config['vix_multipliers'].get(vix_regime, 1.0)

    def _validate_orderflow(self, es_data: Dict, menthorq_result: Dict) -> float:
        """Valide l'OrderFlow"""
        if not self.orderflow_analyzer:
            return 0.5  # Score neutre si pas d'OrderFlow

        try:
            of_result = self.orderflow_analyzer.analyze_orderflow(es_data)
            return of_result.get('composite_score', 0.5)
        except Exception as e:
            logger.warning(f"Erreur validation OrderFlow: {e}")
            return 0.5

    def _determine_vix_regime(self, vix_value: float) -> str:
        """Détermine le régime VIX"""
        if vix_value < 15:
            return "LOW"
        elif vix_value < 22:
            return "MID"
        elif vix_value < 35:
            return "HIGH"
        else:
            return "EXTREME"

    def _check_mia_bullish_gate(self, es_data: Dict, menthorq_result: Dict) -> Tuple[bool, float]:
        """
        GATE BIAIS — MIA BULLISH

        LONG si mia ≥ +0.20 ; SHORT si mia ≤ −0.20
        Retourne (ok, score) pour le multiplicateur
        """
        try:
            # Calcul MIA Bullish
            mia_score = self.mia_bullish.calculate_bullish_score(es_data)

            # Extraction du côté MenthorQ
            action = menthorq_result.get('action', 'NO_SIGNAL')
            if 'GO_LONG' in action:
                required_mia = self.config['menthorq']['mia']['gate_long']
                return (mia_score >= required_mia, mia_score)
            elif 'GO_SHORT' in action:
                required_mia = self.config['menthorq']['mia']['gate_short']
                return (mia_score <= required_mia, mia_score)

            return (False, mia_score)

        except Exception as e:
            logger.error(f"Erreur gate MIA Bullish: {e}")
            return (False, 0.0)

    def _check_leadership_gate(self, es_data: Dict, nq_data: Dict, menthorq_result: Dict) -> Dict:
        """
        GATE MACRO — LEADERSHIP ES/NQ (LS)

        Calcul LS (NQ vs ES) + corr roulante 30s
        Applique veto contre-trend + bonus si |LS| ≥ seuil
        """
        try:
            # Calcul Leadership
            leadership_snapshot = self.leadership_engine.update_from_unified_rows(es_data, nq_data)

            if not leadership_snapshot:
                return {"allow": True, "reason": "leadership_unavailable", "bonus": 1.0}

            # VIX pour adaptation
            vix_data = es_data.get('vix', {})
            vix_value = vix_data.get('value', 20)
            vix_regime = self._determine_vix_regime(vix_value)

            # Extraction des valeurs
            corr = float(leadership_snapshot.get('roll_corr_30s', 0.0))
            ls = float(leadership_snapshot.get('ls', 0.0))
            action = menthorq_result.get('action', 'NO_SIGNAL')
            side = 'LONG' if 'GO_LONG' in action else 'SHORT' if 'GO_SHORT' in action else 'UNKNOWN'

            # Vérification corrélation minimale
            corr_min = self.config['menthorq']['leadership']['corr_min'][vix_regime]
            if corr < corr_min:
                return {"allow": True, "reason": f"low_corr({corr:.2f})", "bonus": 1.0}

            # Veto contre-trend
            veto_abs = float(self.config['menthorq']['leadership']['veto_abs'][vix_regime])
            if (side == 'LONG' and ls <= -veto_abs) or (side == 'SHORT' and ls >= veto_abs):
                return {"allow": False, "reason": f"veto |LS|={abs(ls):.2f}≥{veto_abs:.2f}", "bonus": 1.0}

            # Bonus si |LS| ≥ seuil
            bonus_abs = float(self.config['menthorq']['leadership']['bonus_abs'][vix_regime])
            bonus = 1.05 if abs(ls) >= bonus_abs else 1.0

            return {"allow": True, "reason": "ok", "bonus": bonus}

        except Exception as e:
            logger.error(f"Erreur gate Leadership: {e}")
            return {"allow": True, "reason": f"error:{e}", "bonus": 1.0}

    def _get_vix_multiplier(self, es_data: Dict) -> float:
        """
        RÉGIME VIX (ADAPTATION)

        LOW < 15 → mult ×1.05
        MID 15–22 → ×1.00
        HIGH ≥ 22 → ×0.90
        EXTREME ≥ 35 → ×0.85
        """
        vix_data = es_data.get('vix', {})
        vix_value = vix_data.get('value', 20)
        vix_regime = self._determine_vix_regime(vix_value)

        multipliers = {
            "LOW": 1.05,
            "MID": 1.00,
            "HIGH": 0.90,
            "EXTREME": 0.85
        }

        return multipliers.get(vix_regime, 1.0)

    def _validate_orderflow(self, es_data: Dict, menthorq_result: Dict) -> float:
        """
        VALIDATION ORDERFLOW (OBLIGATOIRE) - VERSION SIMPLIFIÉE

        Confirmer via ≥ min OF parmi : CVD dir, stacked imbalance, absorption au niveau, wick
        """
        try:
            # VIX pour adaptation
            vix_data = es_data.get('vix', {})
            vix_value = vix_data.get('value', 20)
            vix_regime = self._determine_vix_regime(vix_value)

            # Analyse Orderflow
            if self.orderflow_analyzer:
                # Utiliser l'OrderFlowAnalyzer si disponible
                of_signal = self.orderflow_analyzer.analyze_orderflow(es_data)

                if not of_signal:
                    return 0.0

                # Utiliser le score de confiance du signal
                score = of_signal.confidence if hasattr(of_signal, 'confidence') else 0.0

                # Vérification seuil minimum basé sur la force du signal
                min_confirmations = self.config['orderflow']['min_confirmations'][vix_regime]
                min_score = min_confirmations / 4.0  # Normaliser sur 4 confirmations max

                if score < min_score:
                    return 0.0

                return score
            else:
                # Fallback : analyse simplifiée basée sur les données disponibles
                confirmations = 0
                total_confirmations = 4

                # 1. CVD directionnel (NBCV)
                nbcv_data = es_data.get('nbcv', {})
                if nbcv_data.get('trend') in ['bullish', 'bearish']:
                    confirmations += 1

                # 2. Cumulative Delta
                cum_delta_data = es_data.get('cumulative_delta', {})
                if cum_delta_data.get('trend') in ['bullish', 'bearish']:
                    confirmations += 1

                # 3. Stacked imbalance (DOM)
                depth_data = es_data.get('depth', {})
                if depth_data.get('bid_levels') and depth_data.get('ask_levels'):
                    # Vérification basique de l'imbalance
                    bid_total = sum(level.get('size', 0) for level in depth_data['bid_levels'])
                    ask_total = sum(level.get('size', 0) for level in depth_data['ask_levels'])
                    if bid_total > 0 and ask_total > 0:
                        imbalance_ratio = abs(bid_total - ask_total) / max(bid_total, ask_total)
                        if imbalance_ratio > 0.1:  # Seuil d'imbalance
                            confirmations += 1

                # 4. Volume confirmation
                volume_data = es_data.get('basedata', {})
                if volume_data.get('volume', 0) > 0:
                    confirmations += 1

                # Score normalisé
                score = confirmations / total_confirmations

                # Vérification seuil minimum
                min_confirmations = self.config['orderflow']['min_confirmations'][vix_regime]
                min_score = min_confirmations / total_confirmations

                if score < min_score:
                    return 0.0

                return score

        except Exception as e:
            logger.error(f"Erreur validation Orderflow: {e}")
            return 0.0

    def _analyze_structure_context(self, es_data: Dict, menthorq_result: Dict) -> float:
        """
        CONTEXTE STRUCTUREL

        Buffers : éviter d'entrer sur VWAP/S±1 ou VAH/VAL/VPOC/HVN
        """
        try:
            # VIX pour adaptation
            vix_data = es_data.get('vix', {})
            vix_value = vix_data.get('value', 20)
            vix_regime = self._determine_vix_regime(vix_value)

            # Buffers structurels
            buffers = self.config['structure']['buffers'][vix_regime]
            tick = 0.25  # ES tick size
            px = es_data.get('basedata', {}).get('close')

            if px is None:
                return 0.5

            # Score de base
            score = 0.5

            # Vérification buffers VWAP
            vwap_data = es_data.get('vwap', {})
            if vwap_data:
                vwap = vwap_data.get('value')
                if vwap is not None:
                    vwap_buffer = buffers.get('vwap', 1)
                    if abs(px - vwap) / tick <= vwap_buffer:
                        score -= 0.15

            # Vérification buffers Volume Profile
            vp_data = es_data.get('volume_profile', {})
            if vp_data:
                profile_buffer = buffers.get('profile', 1)
                for key in ('vah', 'val', 'vpoc'):
                    level = vp_data.get(key)
                    if level is not None:
                        if abs(px - level) / tick <= profile_buffer:
                            score -= 0.15

            return float(max(0.0, min(1.0, score)))

        except Exception as e:
            logger.error(f"Erreur analyse structure: {e}")
            return 0.5

    def _calculate_final_score(self, menthorq_score: float, orderflow_score: float,
                             structure_score: float, vix_multiplier: float,
                             leadership_bonus: float, mia_score: float = 0.0) -> float:
        """
        FUSION & SEUIL

        raw = 0.55 * mq_gex_score + 0.30 * orderflow_score + 0.15 * structure_score
        eff = raw * vix_mult * mia_mult * leadership_bonus
        """
        weights = self.config['menthorq']['weights']

        raw_score = (
            weights['mq'] * menthorq_score +
            weights['of'] * orderflow_score +
            weights['structure'] * structure_score
        )

        # MIA boost si |MIA| ≥ seuil
        mia_boost_thr = self.config['menthorq']['mia'].get('boost_abs', 0.35)
        mia_mult = 1.05 if abs(mia_score) >= mia_boost_thr else 1.0

        effective_score = raw_score * vix_multiplier * leadership_bonus * mia_mult

        return min(1.0, effective_score)

    def _generate_menthorq_first_signal(self, result: MenthorQFirstResult,
                                      menthorq_result: Dict, es_data: Dict) -> MenthorQFirstResult:
        """
        GÉNÈRE LE SIGNAL MENTHORQ FIRST FINAL
        """
        # Signal type
        action = menthorq_result.get('action', 'NO_SIGNAL')
        if 'GO_LONG' in action:
            result.signal_type = 'LONG'
        elif 'GO_SHORT' in action:
            result.signal_type = 'SHORT'
        else:
            result.signal_type = 'NO_SIGNAL'

        # Confidence
        result.confidence = result.final_score

        # E/U/L levels
        result.eul_levels = self._calculate_eul_levels(es_data, menthorq_result)

        return result

    def _calculate_eul_levels(self, es_data: Dict, menthorq_result: Dict) -> Dict:
        """
        CALCUL E/U/L (ENTRY/UNWIND/LOSS) - VERSION UNIFIÉE

        Utilise le système unifié de stops (7 ticks partout)
        Entry : MKT/LMT si L1 == BBO ; marge ±1 tick vs niveau
        Stop : 7 ticks fixes derrière le niveau MQ
        TP : TP1 = +2R (14 ticks), TP2 = +3R (21 ticks)
        """
        try:
            # Niveau MenthorQ et action
            menthorq_level = menthorq_result.get('level_price', 0)
            action = menthorq_result.get('action', 'NO_SIGNAL')

            if not menthorq_level or action == 'NO_SIGNAL':
                return {}

            # Prix d'entrée (±4 ticks du niveau MenthorQ)
            if 'GO_LONG' in action:
                entry_price = menthorq_level + (4 * ES_TICK_SIZE)  # +4 ticks
                side = "LONG"
            elif 'GO_SHORT' in action:
                entry_price = menthorq_level - (4 * ES_TICK_SIZE)  # -4 ticks
                side = "SHORT"
            else:
                return {}

            # Utiliser le système unifié (entrée 4 ticks, stop 7 ticks)
            unified_stops = calculate_unified_stops(
                entry_price=entry_price,
                side=side,
                level_price=menthorq_level,
                use_fixed=True  # Force l'utilisation des stops fixes (entrée 4, stop 7)
            )

            if not unified_stops:
                logger.error("❌ Échec calcul unified stops")
                return {}

            # Log pour audit
            logger.info(f"📊 E/U/L Unifié: {side} @ {entry_price} → "
                       f"Stop={unified_stops['stop']} ({unified_stops['risk_ticks']}T), "
                       f"TP1={unified_stops['target1']} ({unified_stops['reward_ticks']}T)")

            return {
                'entry': unified_stops['entry'],
                'stop': unified_stops['stop'],
                'tp1': unified_stops['target1'],
                'tp2': unified_stops['target2'],
                'risk_ticks': unified_stops['risk_ticks'],
                'risk_dollars': unified_stops['risk_dollars'],
                'reward_ticks': unified_stops['reward_ticks'],
                'reward_dollars': unified_stops['reward_dollars'],
                'risk_reward_ratio': unified_stops['risk_reward_ratio'],
                'method': unified_stops['method']
            }

        except Exception as e:
            logger.error(f"Erreur calcul E/U/L: {e}")
            return {}

    def _determine_vix_regime(self, vix_value: float) -> str:
        """Détermine le régime VIX"""
        if vix_value < 15:
            return "LOW"
        elif vix_value < 22:
            return "MID"
        elif vix_value < 35:
            return "HIGH"
        else:
            return "EXTREME"

    def _vix_band(self, v: float) -> str:
        """Helper VIX band (alias pour _determine_vix_regime)"""
        return self._determine_vix_regime(v)

    def _true_breakout_up(self, level: float, high: float, low: float, close: float, tick: float, vix_value: float) -> bool:
        """Vraie cassure haussière avec tolérance mèche selon VIX"""
        band = self._vix_band(vix_value)
        tol = self.config['user_experience']['wick_tolerance']['ticks_by_band'][band]
        wick_below = max(0, int(round((level - low) / tick)))
        return (close >= level + tol * tick) and (wick_below <= tol)

    def _true_breakdown_down(self, level: float, high: float, low: float, close: float, tick: float, vix_value: float) -> bool:
        """Vraie cassure baissière avec tolérance mèche selon VIX"""
        band = self._vix_band(vix_value)
        tol = self.config['user_experience']['wick_tolerance']['ticks_by_band'][band]
        wick_above = max(0, int(round((high - level) / tick)))
        return (close <= level - tol * tick) and (wick_above <= tol)

    def _is_true_break(self, es_data: Dict, level_price: float, side: str, vix_value: float) -> bool:
        """
        Règle "Cassure vraie = Close au-delà du niveau + mèche dans la tolérance"

        Args:
            es_data: Données ES avec OHLC
            level_price: Prix du niveau MenthorQ
            side: 'LONG' (cassure au-dessus) ou 'SHORT' (cassure au-dessous)
            vix_value: Valeur VIX pour tolérance

        Returns:
            bool: True si vraie cassure
        """
        try:
            basedata = es_data.get('basedata', {})
            open_price = basedata.get('open', 0)
            high_price = basedata.get('high', 0)
            low_price = basedata.get('low', 0)
            close_price = basedata.get('close', 0)

            if not all([open_price, high_price, low_price, close_price]):
                return False

            band = self._vix_band(vix_value)
            tol = self.config['user_experience']['wick_tolerance']['ticks_by_band'][band]
            tick = 0.25  # ES tick size

            if side == "LONG":
                # Cassure haussière : close > niveau ET mèche en dessous ≤ tolérance
                close_ok = close_price > level_price
                wick_ok = (low_price >= level_price - tol * tick)
                return close_ok and wick_ok
            else:
                # Cassure baissière : close < niveau ET mèche au-dessus ≤ tolérance
                close_ok = close_price < level_price
                wick_ok = (high_price <= level_price + tol * tick)
                return close_ok and wick_ok

        except Exception as e:
            logger.error(f"Erreur vérification cassure vraie: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la méthode MenthorQ First"""
        return {
            'menthorq_triggers': self.stats['menthorq_triggers'],
            'mia_gates_passed': self.stats['mia_gates_passed'],
            'leadership_gates_passed': self.stats['leadership_gates_passed'],
            'orderflow_validations': self.stats['orderflow_validations'],
            'structure_validations': self.stats['structure_validations'],
            'final_signals': self.stats['final_signals'],
            'success_rate': (
                self.stats['final_signals'] /
                max(1, self.stats['menthorq_triggers'])
            ) * 100
        }
