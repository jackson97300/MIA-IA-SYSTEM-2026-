#!/usr/bin/env python3
"""
🚀 LAUNCHER ELITE PAPER TRADING - MIA_IA_SYSTEM
===============================================

Launcher spécialisé pour le paper trading avec le système Elite.
Intègre EliteUnifier + RobustUnifier + EliteTradingBridge pour un trading
complet basé sur les décisions Elite (NO_GO/SCOUT_GO/GO).

FONCTIONNALITÉS:
- ✅ Système Elite complet (MenthorQ, Battle Navale, OrderFlow, DOM Health)
- ✅ Paper trading avec exécution simulée
- ✅ Risk & Sizing Engine intégré
- ✅ Messaging standardisé
- ✅ Journaling JSONL des décisions
- ✅ Mode dev avec QC manquant autorisé

Author: MIA_IA_SYSTEM
Version: 1.0.0
Date: Janvier 2025
"""

import asyncio
import sys
import os
import time
import signal
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# === IMPORTS ELITE SYSTEM ===
try:
    from core.logger import get_logger
    from unifier.elite_unifier import EliteUnifier
    from unifier.robust_unifier import RobustUnifier
    from execution.elite_trading_bridge import EliteTradingBridge, create_elite_trading_bridge
    from execution.trading_executor import TradingExecutor
    from core.decision_messenger import DecisionMessenger
    ELITE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erreur import Elite System: {e}")
    ELITE_AVAILABLE = False

# === CONFIGURATION ELITE ===
ELITE_CONFIG = {
    # Elite System
    'elite_methods_enabled': True,
    'menthorq_elite_enabled': True,
    'battle_navale_elite_enabled': True,
    'orderflow_advanced_enabled': True,
    'dom_health_enabled': True,
    
    # Paper Trading
    'paper_trading': True,
    'send_messages': True,
    'verbose': True,
    
    # Dev Mode
    'qc_missing_allowed': True,  # Autorise QC manquant en dev
    
    # Performance
    'max_decisions_per_minute': 60,
    'processing_timeout_ms': 1000,
}

# === LOGGER ===
if ELITE_AVAILABLE:
    logger = get_logger(__name__)
else:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("ELITE_PAPER")

# === GESTIONNAIRE DE SIGNAUX ===
def signal_handler(signum, frame):
    """Gestionnaire de signaux pour arrêt propre"""
    logger.info(f"\n🛑 Signal {signum} reçu - Arrêt du système Elite...")
    sys.exit(0)

# === SYSTÈME ELITE PAPER TRADING ===

class ElitePaperTradingSystem:
    """
    Système de paper trading basé sur Elite System
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation du système Elite Paper Trading"""
        self.config = config or ELITE_CONFIG
        self.logger = logger
        
        # Composants Elite
        self.elite_unifier = None
        self.robust_unifier = None
        self.trading_executor = None
        self.elite_trading_bridge = None
        self.decision_messenger = None
        
        # Statistiques
        self.total_decisions = 0
        self.executed_orders = 0
        self.blocked_orders = 0
        self.start_time = time.time()
        
        # Configuration des gestionnaires de signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("🚀 Elite Paper Trading System initialisé")
    
    async def initialize(self) -> bool:
        """Initialise tous les composants Elite"""
        try:
            if not ELITE_AVAILABLE:
                logger.error("❌ Modules Elite non disponibles")
                return False
            
            logger.info("🔄 Initialisation des composants Elite...")
            
            # Elite Unifier
            self.elite_unifier = EliteUnifier()
            logger.info("✅ Elite Unifier initialisé")
            
            # Robust Unifier
            self.robust_unifier = RobustUnifier()
            logger.info("✅ Robust Unifier initialisé")
            
            # Trading Executor (mode paper)
            self.trading_executor = TradingExecutor()
            logger.info("✅ Trading Executor initialisé (mode paper)")
            
            # Elite Trading Bridge
            self.elite_trading_bridge = create_elite_trading_bridge(self.trading_executor)
            logger.info("✅ Elite Trading Bridge initialisé")
            
            # Decision Messenger
            self.decision_messenger = DecisionMessenger()
            logger.info("✅ Decision Messenger initialisé")
            
            logger.info("🎯 Tous les composants Elite initialisés avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Elite System: {e}")
            return False
    
    async def run_paper_trading_loop(self):
        """Boucle principale de paper trading Elite"""
        logger.info("🔄 Démarrage boucle de paper trading Elite...")
        
        while True:
            try:
                # Simuler un snapshot de données (en production, ceci viendrait de Sierra Chart)
                snapshot = self._create_test_snapshot()
                
                # Analyse Elite
                start_time = time.perf_counter()
                elite_result = self.robust_unifier.unify_robust(snapshot)
                processing_time = (time.perf_counter() - start_time) * 1000
                
                self.total_decisions += 1
                
                # Extraire la synthèse Elite
                elite_synthesis = elite_result.get("elite_synthesis", {})
                recommendation = elite_synthesis.get("recommendation", "NO_GO")
                go_live_mode = elite_synthesis.get("go_live_mode", "NO")
                component_scores = elite_synthesis.get("component_scores", {})
                gates_status = elite_synthesis.get("gates_status", {})
                
                # Afficher la décision
                self._display_decision(snapshot, elite_synthesis, processing_time)
                
                # Traiter la décision si applicable
                if recommendation in ["SCOUT_GO", "GO"]:
                    success, order_id, error = self.elite_trading_bridge.process_elite_decision(
                        elite_synthesis, snapshot
                    )
                    
                    if success:
                        self.executed_orders += 1
                        logger.info(f"✅ Ordre paper exécuté: {order_id}")
                    else:
                        self.blocked_orders += 1
                        logger.warning(f"❌ Ordre paper bloqué: {error}")
                
                # Afficher les statistiques périodiquement
                if self.total_decisions % 10 == 0:
                    self._display_statistics()
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(1.0)  # 1 seconde entre les décisions
                
            except KeyboardInterrupt:
                logger.info("🛑 Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur boucle paper trading: {e}")
                await asyncio.sleep(5.0)  # Attendre 5 secondes en cas d'erreur
    
    def _create_test_snapshot(self) -> Dict[str, Any]:
        """Crée un snapshot de test pour la démonstration"""
        import random
        
        # Simuler des données de marché réalistes
        base_price = 4500.0 + random.uniform(-10.0, 10.0)
        
        return {
            "sym": "ESZ25_FUT_CME",
            "t": int(time.time()),
            "last": base_price,
            "phase": "REGULAR",
            "regime": "TREND",
            "vix": 18.5 + random.uniform(-2.0, 2.0),
            "vix_trend": "DECLINING",
            
            # MenthorQ data
            "type": "menthorq_gamma",
            "i": random.randint(900, 1000),
            "chart": 3,
            "gex_1": base_price + random.uniform(-5.0, 5.0),
            "gex_2": base_price + random.uniform(-5.0, 5.0),
            "gex_3": base_price + random.uniform(-5.0, 5.0),
            "gex_4": base_price + random.uniform(-5.0, 5.0),
            "gex_5": base_price + random.uniform(-5.0, 5.0),
            "hvl": base_price + random.uniform(-2.0, 2.0),
            "hvl_0dte": base_price + random.uniform(-2.0, 2.0),
            "call_resistance": base_price + random.uniform(5.0, 15.0),
            "put_support": base_price - random.uniform(5.0, 15.0),
            "gamma_wall_0dte": base_price + random.uniform(-3.0, 3.0),
            
            # VWAP data
            "vwap": base_price + random.uniform(-1.0, 1.0),
            "vwap_slope": random.uniform(-0.5, 0.5),
            
            # DOM data
            "best_bid": base_price - 0.25,
            "best_ask": base_price + 0.25,
            "spread": 0.5,
            "l1_bbo_ratio": random.uniform(0.8, 1.2),
            "depth_levels": random.randint(5, 15),
            
            # Trade summary data
            "trade_summary_current": {
                "buy_vol": random.uniform(1000, 5000),
                "sell_vol": random.uniform(1000, 5000),
                "cum_delta_session": random.uniform(-1000, 1000),
                "buy_trades": random.randint(50, 200),
                "sell_trades": random.randint(50, 200)
            },
            
            # OHLC pour ATR
            "price_highs": [base_price + random.uniform(0, 5) for _ in range(50)],
            "price_lows": [base_price - random.uniform(0, 5) for _ in range(50)],
            "price_closes": [base_price + random.uniform(-2, 2) for _ in range(50)],
        }
    
    def _display_decision(self, snapshot: Dict[str, Any], elite_synthesis: Dict[str, Any], processing_time: float):
        """Affiche la décision Elite de manière claire"""
        symbol = snapshot.get("sym", "ES")
        price = snapshot.get("last", 0.0)
        recommendation = elite_synthesis.get("recommendation", "NO_GO")
        go_live_mode = elite_synthesis.get("go_live_mode", "NO")
        component_scores = elite_synthesis.get("component_scores", {})
        gates_status = elite_synthesis.get("gates_status", {})
        
        # Scores des composants
        mq_score = component_scores.get("menthorq_elite", 0.0)
        bn_score = component_scores.get("battle_navale_elite", 0.0)
        of_score = component_scores.get("orderflow_advanced", 0.0)
        dom_score = component_scores.get("dom_health", 0.0)
        
        # Gates
        dom_ok = gates_status.get("dom_health_gate_ok", False)
        bn_ok = gates_status.get("battle_navale_gates_ok", False)
        overall_ok = gates_status.get("overall_gates_ok", False)
        
        # Affichage
        print(f"\n{'='*60}")
        print(f"🎯 ELITE DECISION - {symbol} @ {price:.2f}")
        print(f"📊 Recommendation: {recommendation} | Mode: {go_live_mode}")
        print(f"📈 Scores: MQ {mq_score:.3f} | BN {bn_score:.3f} | OF {of_score:.3f} | DOM {dom_score:.3f}")
        print(f"🚪 Gates: DOM {'✅' if dom_ok else '❌'} | BN {'✅' if bn_ok else '❌'} | Overall {'✅' if overall_ok else '❌'}")
        print(f"⏱️  Processing: {processing_time:.1f}ms")
        
        if recommendation != "NO_GO":
            risk_bracket = elite_synthesis.get("risk_bracket")
            if risk_bracket:
                print(f"💰 Risk Bracket: {risk_bracket.get('contracts', 1)} contracts | Stop: {risk_bracket.get('stop_ticks', 0)} ticks | TP: {risk_bracket.get('tp_ticks', 0)} ticks")
    
    def _display_statistics(self):
        """Affiche les statistiques du système"""
        runtime = time.time() - self.start_time
        decisions_per_minute = (self.total_decisions / runtime) * 60 if runtime > 0 else 0
        execution_rate = (self.executed_orders / max(self.total_decisions, 1)) * 100
        
        print(f"\n📊 STATISTIQUES ELITE PAPER TRADING")
        print(f"   • Décisions totales: {self.total_decisions}")
        print(f"   • Ordres exécutés: {self.executed_orders}")
        print(f"   • Ordres bloqués: {self.blocked_orders}")
        print(f"   • Taux d'exécution: {execution_rate:.1f}%")
        print(f"   • Décisions/min: {decisions_per_minute:.1f}")
        print(f"   • Runtime: {runtime/60:.1f} minutes")

# === FONCTION PRINCIPALE ===

async def main():
    """Fonction principale du launcher Elite Paper Trading"""
    print("🚀 ELITE PAPER TRADING SYSTEM")
    print("=" * 60)
    print("📊 Mode: Paper Trading avec décisions Elite")
    print("🎯 Système: MenthorQ + Battle Navale + OrderFlow + DOM Health")
    print("💰 Exécution: Simulée (pas d'ordres réels)")
    print("=" * 60)
    
    # Créer le système
    system = ElitePaperTradingSystem()
    
    # Initialiser
    if not await system.initialize():
        logger.error("❌ Échec initialisation - Arrêt du système")
        return
    
    logger.info("🎯 Système Elite Paper Trading opérationnel")
    logger.info("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        # Lancer la boucle de paper trading
        await system.run_paper_trading_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur système: {e}")
    finally:
        # Afficher les statistiques finales
        system._display_statistics()
        logger.info("✅ Système Elite Paper Trading arrêté")

if __name__ == "__main__":
    asyncio.run(main())





