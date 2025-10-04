#!/usr/bin/env python3
"""
ELITE DECISION ORCHESTRATOR - Orchestrateur de décision avec méthodes Elite
==========================================================================

Orchestrateur principal qui combine les méthodes Elite pour prendre des décisions
de trading et générer des messages clairs et sympas.

Intègre :
- MenthorQ Elite
- Battle Navale Elite
- Mode Override sécurisé
- Decision Messenger
- Flow de décision complet

Version: 1.0.0
Date: Janvier 2025
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Ajouter le répertoire racine au path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Imports des méthodes Elite
try:
    from core.menthorq_elite import MenthorQElite, MenthorQEliteResult
    from core.battle_navale_elite import BattleNavaleElite, BattleNavaleEliteResult
    from core.decision_messenger import DecisionMessenger, create_decision_messenger
    ELITE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Modules Elite non disponibles: {e}")
    ELITE_MODULES_AVAILABLE = False

@dataclass
class EliteDecision:
    """Structure de décision Elite"""
    mode: str                    # "LIVE" ou "PAPER"
    symbol: str                  # "ES", "NQ", etc.
    direction: int               # 1 = LONG, -1 = SHORT
    menthorq: Dict[str, Any]     # Résultat MenthorQ Elite
    battle_navale: Dict[str, Any] # Résultat Battle Navale Elite
    final: Dict[str, Any]        # Décision finale
    plan: Optional[Dict[str, Any]] = None  # Plan d'exécution si trade
    context: Dict[str, Any] = None         # Contexte (VIX, latence, etc.)
    timestamp: float = 0.0       # Timestamp de la décision

class EliteDecisionOrchestrator:
    """
    Orchestrateur de décision avec méthodes Elite
    
    Fonctionnalités :
    - Intégration MenthorQ Elite + Battle Navale Elite
    - Mode Override sécurisé
    - Génération de messages clairs
    - Flow de décision complet
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation de l'orchestrateur Elite"""
        self.config = config or {
            "mode": "PAPER",                    # Mode par défaut
            "final_threshold": 0.75,            # Seuil final pour exécution
            "override_enabled": True,           # Mode override activé
            "override_menthorq_min": 0.80,      # Seuil MQ minimum pour override
            "override_battle_navale_min": 0.50, # Seuil BN minimum pour override
            "messenger_config": {
                "verbose": True,
                "save_history": True,
                "cooldown_seconds": 2
            }
        }
        
        # Initialiser les composants
        if ELITE_MODULES_AVAILABLE:
            self.menthorq_elite = MenthorQElite()
            self.battle_navale_elite = BattleNavaleElite()
            self.decision_messenger = create_decision_messenger(self.config["messenger_config"])
        else:
            self.menthorq_elite = None
            self.battle_navale_elite = None
            self.decision_messenger = None
        
        # Statistiques
        self.stats = {
            "total_decisions": 0,
            "execute_decisions": 0,
            "wait_decisions": 0,
            "override_decisions": 0,
            "last_decision_time": 0
        }
        
        print("🎯 Elite Decision Orchestrator initialisé")
        if ELITE_MODULES_AVAILABLE:
            print("✅ Tous les modules Elite disponibles")
        else:
            print("⚠️ Modules Elite non disponibles - Mode fallback")
    
    def process_tick(self, unified_data: Dict[str, Any], mode: str = None) -> EliteDecision:
        """
        Traite un tick et prend une décision
        
        Args:
            unified_data: Données unifiées du tick
            mode: Mode de trading ("LIVE" ou "PAPER")
            
        Returns:
            EliteDecision avec la décision prise
        """
        if not ELITE_MODULES_AVAILABLE:
            return self._create_fallback_decision(unified_data, mode)
        
        try:
            # Déterminer le mode
            current_mode = mode or self.config["mode"]
            
            # Extraire les données de base
            symbol = unified_data.get("symbol", "ES")
            current_price = unified_data.get("current_price", 0.0)
            timestamp = unified_data.get("timestamp", time.time())
            
            # === 1. MENTHORQ ELITE ===
            menthorq_result = self._process_menthorq_elite(unified_data)
            
            # === 2. BATTLE NAVALE ELITE ===
            battle_navale_result = self._process_battle_navale_elite(unified_data)
            
            # === 3. DÉCISION FINALE ===
            final_decision = self._make_final_decision(
                menthorq_result, battle_navale_result, current_mode
            )
            
            # === 4. PLAN D'EXÉCUTION ===
            execution_plan = None
            if final_decision["execute"]:
                execution_plan = self._create_execution_plan(
                    unified_data, menthorq_result, battle_navale_result
                )
            
            # === 5. CONTEXTE ===
            context = self._build_context(unified_data)
            
            # === 6. CRÉER LA DÉCISION ===
            decision = EliteDecision(
                mode=current_mode,
                symbol=symbol,
                direction=1 if menthorq_result.get("signal", False) else -1,
                menthorq=menthorq_result,
                battle_navale=battle_navale_result,
                final=final_decision,
                plan=execution_plan,
                context=context,
                timestamp=timestamp
            )
            
            # === 7. ENVOYER LE MESSAGE ===
            if self.decision_messenger:
                self.decision_messenger.send_decision(decision.__dict__)
            
            # === 8. METTRE À JOUR LES STATS ===
            self._update_stats(decision)
            
            return decision
            
        except Exception as e:
            print(f"❌ Erreur traitement tick: {e}")
            return self._create_error_decision(unified_data, mode, str(e))
    
    def _process_menthorq_elite(self, unified_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite MenthorQ Elite"""
        try:
            # Construire les données MenthorQ
            menthorq_data = {
                'gamma': unified_data.get('mentorq', {}).get('gamma', {}),
                'blind_spots': unified_data.get('mentorq', {}).get('blind', {}),
                'dealers_bias': unified_data.get('dealers_bias', {}),
                'vwap': unified_data.get('micro', {}).get('vwap', {}),
                'vix': unified_data.get('macro', {}).get('vix', 20.0)
            }
            
            qc = unified_data.get('qc_context', {})
            current_price = unified_data.get('current_price', 0.0)
            symbol = unified_data.get('symbol', 'ES')
            intended_direction = 1  # Par défaut LONG
            
            result = self.menthorq_elite.calculate_menthorq_elite(
                menthorq_data, current_price, symbol, intended_direction, qc
            )
            
            return {
                "score": result.menthorq_score,
                "raw_score": result.raw_score,
                "vix_multiplier": result.vix_multiplier,
                "signal": result.is_signal,
                "strength": result.signal_strength,
                "risk_multiplier": result.risk_multiplier,
                "patience_minutes": result.patience_minutes,
                "components": {
                    "gamma_levels": result.gamma_levels,
                    "blind_spots": result.blind_spots,
                    "dealers_bias": result.dealers_bias,
                    "vwap_confluence": result.vwap_confluence,
                    "vix_regime": result.vix_regime
                }
            }
        except Exception as e:
            return {"error": str(e), "score": 0.0, "signal": False}
    
    def _process_battle_navale_elite(self, unified_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite Battle Navale Elite"""
        try:
            # Construire les données DOM
            dom_data = {
                'best_bid': unified_data.get('best_bid', 0),
                'best_ask': unified_data.get('best_ask', 0),
                'l1_bbo_ratio': unified_data.get('l1_bbo_ratio', 1.0),
                'l1_bbo_ratio_rolling': unified_data.get('l1_bbo_ratio_rolling', 1.0),
                'depth_levels': unified_data.get('depth_levels', 10)
            }
            
            # Construire les données OrderFlow
            orderflow_data = {
                'current': unified_data.get('trade_summary_current', {}),
                'history': unified_data.get('trade_summary_history', []),
                'intended_direction': 1  # Par défaut LONG
            }
            
            # Construire les données Structure
            structure_data = {
                'price': unified_data.get('current_price', 0.0),
                'vwap': unified_data.get('micro', {}).get('vwap', {}).get('vwap', 0.0),
                'vpoc': unified_data.get('micro', {}).get('vp', {}).get('vpoc', 0.0),
                'val': unified_data.get('micro', {}).get('vp', {}).get('val', 0.0),
                'vah': unified_data.get('micro', {}).get('vp', {}).get('vah', 0.0),
                'menthorq_levels': unified_data.get('menthorq_levels', []),
                'symbol': unified_data.get('symbol', 'ES'),
                'vwap_qc_p95': unified_data.get('qc_context', {}).get('vwap_qc_p95', 0.0)
            }
            
            # Construire les données Patterns
            patterns_data = unified_data.get('sierra_patterns', {})
            
            # Construire les données Microstructure
            micro_data = {
                'iceberg_confirmed': unified_data.get('iceberg_confirmed', False),
                'large_prints': unified_data.get('large_prints', [])
            }
            
            # Données ATR
            atr_data = {
                'current_atr': unified_data.get('qc_context', {}).get('atr_per_bar', 1.0),
                'atr_median_20d': unified_data.get('qc_context', {}).get('atr_relative', 1.0)
            }
            
            vix_level = unified_data.get('macro', {}).get('vix', 20.0)
            symbol = unified_data.get('symbol', 'ES')
            
            result = self.battle_navale_elite.calculate_battle_navale_elite(
                dom_data=dom_data,
                orderflow_data=orderflow_data,
                structure_data=structure_data,
                patterns_data=patterns_data,
                micro_data=micro_data,
                symbol=symbol,
                vix_level=vix_level,
                atr_data=atr_data
            )
            
            return {
                "score": result.bn_score,
                "gates_ok": result.gates_ok,
                "gates_detail": result.gates_detail,
                "blocked_by": result.blocked_by,
                "components": result.components,
                "regime": result.regime,
                "tolerance": result.tolerance,
                "calculation_time_ms": result.calculation_time_ms
            }
        except Exception as e:
            return {"error": str(e), "score": 0.0, "gates_ok": False}
    
    def _make_final_decision(self, menthorq_result: Dict, battle_navale_result: Dict, mode: str) -> Dict[str, Any]:
        """Prend la décision finale"""
        try:
            mq_score = menthorq_result.get("score", 0.0)
            bn_score = battle_navale_result.get("score", 0.0)
            bn_gates_ok = battle_navale_result.get("gates_ok", False)
            
            # Score composite (pondération)
            composite_score = 0.6 * mq_score + 0.4 * bn_score
            
            # Décision de base
            base_execute = composite_score >= self.config["final_threshold"] and bn_gates_ok
            
            # Mode Override
            override_status = "off"
            if self.config["override_enabled"]:
                mq_strong = mq_score >= self.config["override_menthorq_min"]
                bn_minimum = bn_score >= self.config["override_battle_navale_min"]
                
                if mq_strong and bn_minimum and not base_execute:
                    override_status = "active"
                    base_execute = True
                elif not bn_gates_ok:
                    override_status = "blocked"
            
            return {
                "score": composite_score,
                "execute": base_execute,
                "override": override_status,
                "composite_breakdown": {
                    "menthorq_weight": 0.6,
                    "battle_navale_weight": 0.4,
                    "menthorq_contribution": 0.6 * mq_score,
                    "battle_navale_contribution": 0.4 * bn_score
                }
            }
        except Exception as e:
            return {
                "score": 0.0,
                "execute": False,
                "override": "error",
                "error": str(e)
            }
    
    def _create_execution_plan(self, unified_data: Dict, menthorq_result: Dict, battle_navale_result: Dict) -> Dict[str, Any]:
        """Crée le plan d'exécution"""
        try:
            current_price = unified_data.get('current_price', 0.0)
            symbol = unified_data.get('symbol', 'ES')
            
            # Calculer les niveaux
            # Entrée : prix actuel
            entry = current_price
            
            # Stop : basé sur ATR ou structure
            atr = unified_data.get('qc_context', {}).get('atr_per_bar', 1.0)
            stop_distance = atr * 2.0  # 2 ATR
            stop = entry - stop_distance  # Pour un LONG
            
            # Take Profit : basé sur R/R
            risk_reward = 1.5  # R/R de 1.5
            tp1 = entry + (stop_distance * risk_reward)
            
            # Taille : basée sur le score et le risque
            base_size = 1
            if menthorq_result.get("strength") == "STRONG":
                base_size = 2
            elif menthorq_result.get("strength") == "MODERATE":
                base_size = 1
            
            return {
                "entry": entry,
                "stop": stop,
                "tp1": tp1,
                "size": base_size,
                "rr": risk_reward,
                "risk_ticks": int(stop_distance / 0.25),  # Pour ES
                "risk_dollars": stop_distance * 50 * base_size  # Pour ES
            }
        except Exception as e:
            return {
                "entry": 0.0,
                "stop": 0.0,
                "tp1": 0.0,
                "size": 1,
                "rr": 1.0,
                "error": str(e)
            }
    
    def _build_context(self, unified_data: Dict[str, Any]) -> Dict[str, Any]:
        """Construit le contexte"""
        return {
            "vix": unified_data.get('macro', {}).get('vix', 20.0),
            "options_age_min": unified_data.get('qc_context', {}).get('options_snapshot_age_min', 0),
            "latency_ms": unified_data.get('latency_ms', 0.0),
            "session_phase": unified_data.get('session', {}).get('phase', 'unknown'),
            "data_quality": unified_data.get('qc_context', {}).get('data_quality_score', 1.0)
        }
    
    def _update_stats(self, decision: EliteDecision):
        """Met à jour les statistiques"""
        self.stats["total_decisions"] += 1
        self.stats["last_decision_time"] = decision.timestamp
        
        if decision.final["execute"]:
            self.stats["execute_decisions"] += 1
        else:
            self.stats["wait_decisions"] += 1
        
        if decision.final.get("override") == "active":
            self.stats["override_decisions"] += 1
    
    def _create_fallback_decision(self, unified_data: Dict, mode: str) -> EliteDecision:
        """Crée une décision de fallback"""
        return EliteDecision(
            mode=mode or "PAPER",
            symbol=unified_data.get("symbol", "ES"),
            direction=0,
            menthorq={"score": 0.0, "signal": False, "error": "Modules Elite non disponibles"},
            battle_navale={"score": 0.0, "gates_ok": False, "error": "Modules Elite non disponibles"},
            final={"score": 0.0, "execute": False, "override": "off"},
            context={"error": "Modules Elite non disponibles"},
            timestamp=time.time()
        )
    
    def _create_error_decision(self, unified_data: Dict, mode: str, error: str) -> EliteDecision:
        """Crée une décision d'erreur"""
        return EliteDecision(
            mode=mode or "PAPER",
            symbol=unified_data.get("symbol", "ES"),
            direction=0,
            menthorq={"score": 0.0, "signal": False, "error": error},
            battle_navale={"score": 0.0, "gates_ok": False, "error": error},
            final={"score": 0.0, "execute": False, "override": "error"},
            context={"error": error},
            timestamp=time.time()
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return {
            **self.stats,
            "config": self.config,
            "modules_available": ELITE_MODULES_AVAILABLE
        }

def create_elite_decision_orchestrator(config: Optional[Dict[str, Any]] = None) -> EliteDecisionOrchestrator:
    """Factory function pour créer un Elite Decision Orchestrator"""
    return EliteDecisionOrchestrator(config)

if __name__ == "__main__":
    # Test de l'Elite Decision Orchestrator
    print("🧪 Test Elite Decision Orchestrator...")
    
    # Données de test
    test_unified_data = {
        "symbol": "ESZ25_FUT_CME",
        "current_price": 6715.75,
        "timestamp": time.time(),
        "mentorq": {
            "gamma": {
                "gamma_max": 6715.0,
                "call_wall": 6720.0,
                "put_wall": 6710.0
            },
            "blind": {
                "blind_spot_1": 6715.0
            }
        },
        "micro": {
            "vwap": {"vwap": 6715.0},
            "vp": {
                "vpoc": 6715.0,
                "val": 6710.0,
                "vah": 6720.0
            }
        },
        "macro": {"vix": 18.5},
        "qc_context": {
            "options_snapshot_age_min": 2,
            "atr_per_bar": 2.5,
            "data_quality_score": 1.0
        },
        "best_bid": 6715.50,
        "best_ask": 6715.75,
        "l1_bbo_ratio_rolling": 0.95,
        "depth_levels": 15
    }
    
    # Configuration de test
    config = {
        "mode": "PAPER",
        "final_threshold": 0.70,
        "override_enabled": True,
        "messenger_config": {
            "verbose": True,
            "save_history": True,
            "cooldown_seconds": 0
        }
    }
    
    orchestrator = create_elite_decision_orchestrator(config)
    
    # Test du traitement d'un tick
    decision = orchestrator.process_tick(test_unified_data, "PAPER")
    
    print(f"\n📊 Décision prise:")
    print(f"   Mode: {decision.mode}")
    print(f"   Symbole: {decision.symbol}")
    print(f"   Direction: {decision.direction}")
    print(f"   Exécution: {decision.final['execute']}")
    print(f"   Score final: {decision.final['score']:.3f}")
    
    if decision.plan:
        print(f"   Plan: Entrée {decision.plan['entry']:.2f}, Stop {decision.plan['stop']:.2f}, TP1 {decision.plan['tp1']:.2f}")
    
    print(f"\n📈 Statistiques:")
    stats = orchestrator.get_stats()
    print(f"   Décisions totales: {stats['total_decisions']}")
    print(f"   Exécutions: {stats['execute_decisions']}")
    print(f"   Attentes: {stats['wait_decisions']}")
    
    print("✅ Test Elite Decision Orchestrator terminé")





