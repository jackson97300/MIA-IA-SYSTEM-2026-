"""
MENTHORQ + BATTLE NAVALE V2 HYBRID
==================================

Méthode hybride combinant :
1. Méthode MenthorQ (décideur principal)
2. Battle Navale V2 (validateur avec votre expérience)

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

# Imports des méthodes
from core.battle_navale_v2 import BattleNavaleV2, BattleNavaleV2Result
from core.menthorq_distance_trading import MenthorQDistanceTrader
from features.leadership_zmom import LeadershipZMom

# === INTÉGRATION MENTHORQ DECISION ENGINE ===
from engines.MenthorQDecisionEngine import decide
from unifier.build_ctx import build_ctx

# Local imports
from core.base_types import (
    MarketData, OrderFlowData, TradingFeatures,
    ES_TICK_SIZE, ES_TICK_VALUE
)

logger = get_logger(__name__)

# === CONFIGURATION HYBRIDE ===
HYBRID_CONFIG = {
    "description": "Méthode hybride MenthorQ + Battle Navale V2",
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
    
    # === CONFIGURATION BATTLE NAVALE ===
    "battle_navale": {
        "bn_enter_eff": 0.65,
        "vix_mult": {"LOW": 1.05, "MID": 1.00, "HIGH": 0.90, "EXTREME": 0.85}
    }
}

class HybridMethodResult:
    """Résultat de la méthode hybride"""
    
    def __init__(self):
        self.timestamp = pd.Timestamp.now()
        self.method_used = None  # "menthorq" ou "battle_navale"
        self.signal_type = "NO_SIGNAL"
        self.confidence = 0.0
        self.menthorq_result = None
        self.battle_navale_result = None
        self.confluence_score = 0.0
        self.audit_data = {}

class MenthorQBattleNavaleHybrid:
    """
    MÉTHODE HYBRIDE MENTHORQ + BATTLE NAVALE V2
    
    Logique :
    1. MenthorQ (décideur principal) - Niveaux GEX/Gamma
    2. Battle Navale V2 (validateur) - Vikings vs Défenseurs
    3. Confluence - Les deux doivent être d'accord
    4. Votre expérience intégrée (zones, drawdown, patience, mèches)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialisation méthode hybride"""
        self.config = {**HYBRID_CONFIG, **(config or {})}
        
        # === COMPOSANTS ===
        self.menthorq_trader = MenthorQDistanceTrader()
        self.battle_navale_v2 = BattleNavaleV2()
        self.leadership_engine = LeadershipZMom()
        
        # === ÉTAT ===
        self.stats = {
            'menthorq_signals': 0,
            'battle_navale_signals': 0,
            'hybrid_signals': 0,
            'confluence_agreements': 0,
            'confluence_disagreements': 0
        }
        
        logger.info("Méthode hybride MenthorQ + Battle Navale V2 initialisée")

    def analyze_hybrid_opportunity(self, es_data: Dict, nq_data: Dict, config: Optional[Dict] = None) -> HybridMethodResult:
        """
        ANALYSE OPPORTUNITÉ HYBRIDE - INTÉGRÉE AVEC MENTHORQ DECISION ENGINE
        
        Processus :
        1. Construction du contexte unifié
        2. Décision via MenthorQDecisionEngine (intègre tout)
        3. Mapping vers le format hybride existant
        """
        start_time = time.perf_counter()
        result = HybridMethodResult()
        
        try:
            # === 1. CONSTRUCTION DU CONTEXTE UNIFIÉ ===
            # Utiliser les données ES comme base (sym="ES")
            snapshot = {
                "sym": "ES",
                "t": es_data.get("t", time.time()),
                "last": es_data.get("price", es_data.get("last", 0.0)),
                "phase": es_data.get("session", {}).get("phase", "MID"),
                "regime": es_data.get("session", {}).get("regime", "TREND"),
                "vix": es_data.get("vix", {}).get("value", 0.0),
                "vix_trend": es_data.get("vix", {}).get("trend", "flat"),
                "mentorq_gamma": es_data.get("mentorq", {}).get("gamma", {}),
                "mentorq_blind": es_data.get("mentorq", {}).get("blind_spots", {}),
                "vwap": es_data.get("micro", {}).get("vwap", {}),
                "vp": es_data.get("micro", {}).get("vp", {}),
                "ofdom": es_data.get("ofdom", {}),
                "lead": es_data.get("lead", {}),
                "cluster": es_data.get("cluster", {}),
                "mia_score": es_data.get("mia", {}).get("score", 50.0),
                "mia_state": es_data.get("mia", {}).get("state", "NEUTRE")
            }
            
            # === 2. DÉCISION VIA MENTHORQ DECISION ENGINE ===
            ctx = build_ctx(snapshot)
            decision = decide(ctx)
            
            # === 3. MAPPING VERS FORMAT HYBRIDE ===
            if decision and decision["action"] != "FLAT":
                result.menthorq_result = {
                    "action": decision["action"],
                    "side": decision["side"],
                    "confidence": decision["confidence"],
                    "entry": decision["entry"],
                    "stop": decision["stop"],
                    "tp1": decision["tp1"],
                    "tp2": decision["tp2"],
                    "scenario": decision["scenario"],
                    "label": decision["label"],
                    "reason": decision["reason"]
                }
                
                # Mise à jour des stats
                self.stats['menthorq_signals'] += 1
                self.stats['hybrid_signals'] += 1
                logger.info(f"🎯 MenthorQ Decision Engine: {decision['action']} {decision['side']} - {decision['reason']}")
                logger.info(f"   Entry: {decision['entry']}, Stop: {decision['stop']}, TP1: {decision['tp1']}")
                logger.info(f"   Confidence: {decision['confidence']:.2f}, Label: {decision['label']}")
            
            # === 4. AUDIT DATA ===
            result.audit_data = {
                'menthorq_decision_engine_used': True,
                'decision_available': decision is not None,
                'action': decision.get("action", "FLAT") if decision else "FLAT",
                'calculation_time_ms': (time.perf_counter() - start_time) * 1000
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur analyse hybride: {e}")
            result.audit_data['error'] = str(e)
            return result

    def _analyze_confluence(self, menthorq_result: Optional[Dict], battle_result: Optional[BattleNavaleV2Result]) -> float:
        """
        ANALYSE DE CONFLUENCE ENTRE MENTHORQ ET BATTLE NAVALE
        
        Score de confluence :
        - 1.0 = Parfaite confluence (les deux sont d'accord)
        - 0.5 = Confluence partielle (un seul signal)
        - 0.0 = Pas de confluence (pas de signal)
        """
        
        # Vérification disponibilité
        menthorq_available = menthorq_result is not None
        battle_available = battle_result is not None and battle_result.signal_type != "NO_SIGNAL"
        
        if not menthorq_available and not battle_available:
            return 0.0  # Aucun signal
        
        if menthorq_available and not battle_available:
            return 0.5  # Seulement MenthorQ
        
        if not menthorq_available and battle_available:
            return 0.5  # Seulement Battle Navale
        
        # Les deux sont disponibles - vérifier l'accord
        menthorq_action = menthorq_result.get('action', 'NO_SIGNAL')
        battle_action = battle_result.signal_type
        
        # Extraction du côté (LONG/SHORT)
        menthorq_side = None
        if 'GO_LONG' in menthorq_action:
            menthorq_side = 'LONG'
        elif 'GO_SHORT' in menthorq_action:
            menthorq_side = 'SHORT'
        
        battle_side = battle_action if battle_action in ['LONG', 'SHORT'] else None
        
        # Calcul confluence
        if menthorq_side == battle_side:
            # Parfait accord
            menthorq_confidence = menthorq_result.get('confidence', 0.0)
            battle_confidence = battle_result.signal_confidence
            confluence_score = (menthorq_confidence + battle_confidence) / 2
            return min(1.0, confluence_score)
        else:
            # Désaccord
            return 0.0

    def _should_take_hybrid_signal(self, menthorq_result: Optional[Dict], 
                                 battle_result: Optional[BattleNavaleV2Result], 
                                 confluence_score: float) -> bool:
        """
        DÉCIDE SI ON PREND LE SIGNAL HYBRIDE
        
        Conditions :
        1. Confluence score >= 0.7
        2. Au moins un des deux signaux disponible
        3. Pas de blocage (DOM, fenêtres sensibles, etc.)
        """
        
        # Seuil de confluence
        if confluence_score < 0.7:
            return False
        
        # Vérification blocages Battle Navale
        if battle_result:
            if battle_result.battle_status.value in ['dom_degraded', 'sensitive_window']:
                logger.debug("❌ Signal bloqué par Battle Navale (DOM dégradé ou fenêtre sensible)")
                return False
        
        # Vérification MenthorQ
        if menthorq_result:
            if menthorq_result.get('action') == 'NO_SIGNAL':
                return False
        
        return True

    def _generate_hybrid_signal(self, result: HybridMethodResult, es_data: Dict) -> HybridMethodResult:
        """
        GÉNÈRE LE SIGNAL HYBRIDE FINAL
        """
        
        # Priorité à MenthorQ (décideur principal)
        if result.menthorq_result:
            result.method_used = "menthorq"
            result.signal_type = result.menthorq_result.get('action', 'NO_SIGNAL')
            result.confidence = result.menthorq_result.get('confidence', 0.0)
        elif result.battle_navale_result:
            result.method_used = "battle_navale"
            result.signal_type = result.battle_navale_result.signal_type
            result.confidence = result.battle_navale_result.signal_confidence
        
        # Application de vos seuils
        result = self._apply_user_thresholds(result, es_data)
        
        return result

    def _apply_user_thresholds(self, result: HybridMethodResult, es_data: Dict) -> HybridMethodResult:
        """
        APPLIQUE VOS SEUILS (zones, drawdown, patience, mèches)
        """
        
        if result.signal_type == "NO_SIGNAL":
            return result
        
        # VIX pour adaptation
        vix_data = es_data.get('vix', {})
        vix_value = vix_data.get('value', 20)
        vix_regime = self._determine_vix_regime(vix_value)
        
        # Application de vos seuils
        result.audit_data.update({
            'user_thresholds_applied': {
                'zones_entree': '5 ticks partout',
                'drawdown': '7 ticks partout ($87.50)',
                'patience': f'{self.config["patience"]["minutes"][vix_regime]} minutes',
                'tolerance_meches': self._get_wick_tolerance(vix_value),
                'vix_regime': vix_regime
            }
        })
        
        return result

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

    def _get_wick_tolerance(self, vix_value: float) -> int:
        """Retourne la tolérance des mèches selon VIX"""
        if vix_value < 15:
            return 3  # BAS
        elif vix_value < 25:
            return 5  # MOYEN
        else:
            return 7  # ÉLEVÉ

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la méthode hybride"""
        return {
            'menthorq_signals': self.stats['menthorq_signals'],
            'battle_navale_signals': self.stats['battle_navale_signals'],
            'hybrid_signals': self.stats['hybrid_signals'],
            'confluence_agreements': self.stats['confluence_agreements'],
            'confluence_disagreements': self.stats['confluence_disagreements'],
            'confluence_rate': (
                self.stats['confluence_agreements'] / 
                max(1, self.stats['confluence_agreements'] + self.stats['confluence_disagreements'])
            ) * 100
        }


