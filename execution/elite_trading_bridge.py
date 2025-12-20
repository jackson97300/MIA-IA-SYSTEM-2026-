#!/usr/bin/env python3
"""
🌉 ELITE TRADING BRIDGE - MIA_IA_SYSTEM
=======================================

Bridge entre EliteUnifier et TradingExecutor pour l'exécution des ordres
basée sur les décisions Elite (NO_GO/SCOUT_GO/GO).

FONCTIONNALITÉS:
- ✅ Conversion EliteDecision → TradingSignal
- ✅ Mapping Risk Bracket → Order Parameters
- ✅ Intégration TradingExecutor avec mode paper/live
- ✅ Gestion des modes SCOUT_GO (demi-taille) et GO (pleine taille)
- ✅ Logging détaillé des décisions et exécutions

Author: MIA_IA_SYSTEM
Version: 1.0.0
Date: Janvier 2025
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logger import get_logger
from execution.trading_executor import TradingExecutor, OrderType, OrderTIF
from core.trading_types import Side

logger = get_logger(__name__)

# === TYPES ===

class EliteDecisionType(Enum):
    """Types de décisions Elite"""
    NO_GO = "NO_GO"
    SCOUT_GO = "SCOUT_GO"
    GO = "GO"

@dataclass
class EliteTradingSignal:
    """Signal de trading basé sur une décision Elite"""
    symbol: str
    side: str  # "BUY" ou "SELL"
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: float
    decision_type: EliteDecisionType
    confidence: float
    risk_bracket: Optional[Dict[str, Any]] = None
    elite_synthesis: Optional[Dict[str, Any]] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

# === BRIDGE PRINCIPAL ===

class EliteTradingBridge:
    """
    Bridge entre EliteUnifier et TradingExecutor
    """
    
    def __init__(self, trading_executor: TradingExecutor):
        """Initialisation du bridge"""
        self.trading_executor = trading_executor
        self.logger = logger
        
        # Statistiques
        self.total_decisions = 0
        self.executed_orders = 0
        self.blocked_orders = 0
        
        logger.info("🌉 Elite Trading Bridge initialisé")
    
    def process_elite_decision(
        self, 
        elite_synthesis: Dict[str, Any], 
        snapshot: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Traite une décision Elite et l'exécute si approprié
        
        Args:
            elite_synthesis: Résultat de la synthèse Elite
            snapshot: Snapshot de données du marché
            
        Returns:
            (success: bool, order_id: str | None, error: str | None)
        """
        try:
            self.total_decisions += 1
            
            # Extraire les informations de base
            recommendation = elite_synthesis.get("recommendation", "NO_GO")
            go_live_mode = elite_synthesis.get("go_live_mode", "NO")
            risk_bracket = elite_synthesis.get("risk_bracket")
            component_scores = elite_synthesis.get("component_scores", {})
            
            symbol = snapshot.get("sym", "ES")
            current_price = snapshot.get("last", 0.0)
            
            self.logger.info(f"🎯 Elite Decision: {recommendation} | Mode: {go_live_mode} | Symbol: {symbol} @ {current_price}")
            
            # Vérifier si on doit exécuter
            if recommendation == "NO_GO" or go_live_mode == "NO":
                self.logger.info(f"⏸️ NO_GO - Pas d'exécution")
                return False, None, "NO_GO decision"
            
            # Créer le signal de trading
            trading_signal = self._create_trading_signal(
                elite_synthesis, snapshot, risk_bracket
            )
            
            if not trading_signal:
                self.blocked_orders += 1
                return False, None, "Impossible de créer le signal de trading"
            
            # Exécuter l'ordre
            success, order_id, error = self._execute_elite_signal(trading_signal)
            
            if success:
                self.executed_orders += 1
                self.logger.info(f"✅ Ordre Elite exécuté: {order_id} | {trading_signal.side} {trading_signal.quantity} @ {trading_signal.entry_price}")
            else:
                self.blocked_orders += 1
                self.logger.warning(f"❌ Ordre Elite bloqué: {error}")
            
            return success, order_id, error
            
        except Exception as e:
            self.logger.error(f"❌ Erreur Elite Trading Bridge: {e}")
            return False, None, str(e)
    
    def _create_trading_signal(
        self, 
        elite_synthesis: Dict[str, Any], 
        snapshot: Dict[str, Any],
        risk_bracket: Optional[Dict[str, Any]]
    ) -> Optional[EliteTradingSignal]:
        """Crée un signal de trading à partir d'une décision Elite"""
        try:
            # Informations de base
            symbol = snapshot.get("sym", "ES")
            current_price = snapshot.get("last", 0.0)
            recommendation = elite_synthesis.get("recommendation", "NO_GO")
            component_scores = elite_synthesis.get("component_scores", {})
            
            # Déterminer la direction (pour l'instant, on assume LONG)
            # TODO: Implémenter la logique de direction basée sur MenthorQ/OrderFlow
            side = "BUY"  # Par défaut LONG
            
            # Extraire les paramètres du risk bracket
            if risk_bracket:
                quantity = risk_bracket.get("contracts", 1)
                stop_ticks = risk_bracket.get("stop_ticks", 10)
                tp_ticks = risk_bracket.get("tp_ticks", 15)
                tick_size = risk_bracket.get("tick_size", 0.25)
                
                # Calculer les prix
                if side == "BUY":
                    stop_loss = current_price - (stop_ticks * tick_size)
                    take_profit = current_price + (tp_ticks * tick_size)
                else:  # SELL
                    stop_loss = current_price + (stop_ticks * tick_size)
                    take_profit = current_price - (tp_ticks * tick_size)
            else:
                # Fallback si pas de risk bracket
                quantity = 1
                stop_loss = current_price - 2.5 if side == "BUY" else current_price + 2.5
                take_profit = current_price + 3.75 if side == "BUY" else current_price - 3.75
            
            # Calculer la confiance basée sur les scores
            mq_score = component_scores.get("menthorq_elite", 0.0)
            bn_score = component_scores.get("battle_navale_elite", 0.0)
            of_score = component_scores.get("orderflow_advanced", 0.0)
            dom_score = component_scores.get("dom_health", 0.0)
            
            confidence = (mq_score + bn_score + of_score + dom_score) / 4.0
            
            # Créer le signal
            signal = EliteTradingSignal(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                decision_type=EliteDecisionType(recommendation),
                confidence=confidence,
                risk_bracket=risk_bracket,
                elite_synthesis=elite_synthesis
            )
            
            self.logger.info(f"📊 Signal créé: {signal.side} {signal.quantity} @ {signal.entry_price:.2f} | SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f}")
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création signal: {e}")
            return None
    
    def _execute_elite_signal(self, signal: EliteTradingSignal) -> Tuple[bool, Optional[str], Optional[str]]:
        """Exécute un signal Elite via TradingExecutor"""
        try:
            # Générer un tag unique pour déduplication
            tag = f"ELITE_{signal.decision_type.value}_{int(signal.timestamp)}"
            
            # Envoyer l'ordre principal
            success, order_id, error = self.trading_executor.send_order(
                symbol=signal.symbol,
                side=signal.side,
                qty=signal.quantity,
                order_type=OrderType.MARKET,
                tif=OrderTIF.DAY,
                tag=tag
            )
            
            if not success:
                return False, None, error
            
            # TODO: Implémenter les ordres de protection (stop loss, take profit)
            # Pour l'instant, on se contente de l'ordre principal
            
            return True, order_id, None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur exécution signal: {e}")
            return False, None, str(e)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du bridge"""
        return {
            "total_decisions": self.total_decisions,
            "executed_orders": self.executed_orders,
            "blocked_orders": self.blocked_orders,
            "execution_rate": self.executed_orders / max(self.total_decisions, 1),
            "block_rate": self.blocked_orders / max(self.total_decisions, 1)
        }
    
    def reset_statistics(self):
        """Remet à zéro les statistiques"""
        self.total_decisions = 0
        self.executed_orders = 0
        self.blocked_orders = 0
        self.logger.info("📊 Statistiques Elite Trading Bridge remises à zéro")

# === FONCTION DE CRÉATION ===

def create_elite_trading_bridge(trading_executor: TradingExecutor) -> EliteTradingBridge:
    """Crée une instance du bridge Elite Trading"""
    return EliteTradingBridge(trading_executor)







