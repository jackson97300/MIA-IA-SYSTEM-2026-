#!/usr/bin/env python3
"""
Adaptive Cooldowns - Cooldowns Dynamiques
Ajuste cooldowns selon performance stratégie + régime marché

Sprint 4 - TODO Tasks 5a, 5b, 5c
Date: 13 Novembre 2025
"""

import logging
from typing import Dict, Optional
from collections import deque, defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformance:
    """Performance récente stratégie"""
    strategy_name: str
    trades_last_hour: int = 0
    wins_last_hour: int = 0
    win_rate_last_hour: float = 0.0
    avg_pnl_last_hour: float = 0.0
    last_trade_time: Optional[datetime] = None


class AdaptiveCooldowns:
    """
    Cooldowns Adaptatifs
    
    Ajuste cooldowns selon:
    1. Performance récente (win_rate)
    2. Régime marché (volatilité)
    3. Session (ASIA/LONDON/US)
    
    Logique :
    - Stratégie performante (WR > 70%) → Réduire cooldown
    - Stratégie sous-performante (WR < 30%) → Augmenter cooldown
    - Volatilité haute → Réduire cooldowns (+ opportunités)
    - Volatilité basse → Augmenter cooldowns (- opportunités)
    """
    
    def __init__(self, base_cooldowns: Dict[str, int]):
        """
        Args:
            base_cooldowns: Cooldowns de base par stratégie (secondes)
        """
        self.base_cooldowns = base_cooldowns
        
        # Historique trades
        self.trades_history = defaultdict(lambda: deque(maxlen=200))
        
        # Performance tracking
        self.performance = defaultdict(lambda: StrategyPerformance(strategy_name="unknown"))
        
        # Volatilité history
        self.volatility_history = deque(maxlen=100)
        self.volatility_median = None
        
        # Cooldowns actuels (dynamiques)
        self.current_cooldowns = base_cooldowns.copy()
        
        # Dernière mise à jour
        self.last_update = datetime.now()
        
        logger.info("🔄 AdaptiveCooldowns initialisé avec %d stratégies", len(base_cooldowns))
    
    def add_trade(
        self,
        strategy: str,
        win: bool,
        pnl: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Ajoute trade et recalcule cooldown
        
        Args:
            strategy: Nom stratégie
            win: Trade gagné?
            pnl: PnL trade
            timestamp: Timestamp trade (défaut: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Ajouter trade à historique
        self.trades_history[strategy].append({
            'timestamp': timestamp,
            'win': win,
            'pnl': pnl
        })
        
        # Mettre à jour performance
        self._update_performance(strategy)
        
        # Recalculer cooldown
        self._recalculate_cooldown(strategy)
    
    def update_volatility(self, atr: float):
        """
        Update volatilité
        
        Args:
            atr: ATR actuel
        """
        if atr > 0:
            self.volatility_history.append(atr)
            
            if len(self.volatility_history) >= 50:
                self.volatility_median = np.median(list(self.volatility_history))
    
    def _update_performance(self, strategy: str):
        """
        Met à jour performance stratégie (last hour)
        
        Args:
            strategy: Nom stratégie
        """
        perf = self.performance[strategy]
        perf.strategy_name = strategy
        
        # Trades last hour
        cutoff = datetime.now() - timedelta(hours=1)
        
        trades_last_hour = [
            t for t in self.trades_history[strategy]
            if t['timestamp'] >= cutoff
        ]
        
        perf.trades_last_hour = len(trades_last_hour)
        
        if trades_last_hour:
            perf.wins_last_hour = sum(1 for t in trades_last_hour if t['win'])
            perf.win_rate_last_hour = perf.wins_last_hour / perf.trades_last_hour
            perf.avg_pnl_last_hour = np.mean([t['pnl'] for t in trades_last_hour])
            perf.last_trade_time = max(t['timestamp'] for t in trades_last_hour)
        else:
            perf.win_rate_last_hour = 0.0
            perf.avg_pnl_last_hour = 0.0
    
    def _recalculate_cooldown(self, strategy: str):
        """
        Recalcule cooldown adaptatif
        
        Args:
            strategy: Nom stratégie
        """
        base_cooldown = self.base_cooldowns.get(strategy, 90)
        
        perf = self.performance[strategy]
        
        # Multiplier de base
        multiplier = 1.0
        
        # === AJUSTEMENT WIN RATE ===
        if perf.trades_last_hour >= 5:  # Min 5 trades pour ajuster
            if perf.win_rate_last_hour > 0.70:
                # Stratégie chaude → Réduire cooldown
                multiplier *= 0.5
                logger.debug(
                    "🔥 %s: WR=%.0f%% > 70%% → Cooldown réduit x0.5",
                    strategy,
                    perf.win_rate_last_hour * 100
                )
            elif perf.win_rate_last_hour < 0.30:
                # Stratégie froide → Augmenter cooldown
                multiplier *= 2.0
                logger.debug(
                    "❄️ %s: WR=%.0f%% < 30%% → Cooldown augmenté x2.0",
                    strategy,
                    perf.win_rate_last_hour * 100
                )
        
        # === AJUSTEMENT VOLATILITÉ ===
        if self.volatility_median:
            current_vol = self.volatility_history[-1] if self.volatility_history else self.volatility_median
            vol_ratio = current_vol / self.volatility_median
            
            if vol_ratio > 1.5:
                # Volatilité haute → Plus d'opportunités → Réduire cooldown
                vol_adjustment = 0.7
                multiplier *= vol_adjustment
                logger.debug(
                    "📈 Volatilité haute (%.1fx median) → Cooldown ajusté x%.1f",
                    vol_ratio,
                    vol_adjustment
                )
            elif vol_ratio < 0.7:
                # Volatilité basse → Moins d'opportunités → Augmenter cooldown
                vol_adjustment = 1.3
                multiplier *= vol_adjustment
                logger.debug(
                    "📉 Volatilité basse (%.1fx median) → Cooldown ajusté x%.1f",
                    vol_ratio,
                    vol_adjustment
                )
        
        # === AJUSTEMENT SESSION ===
        now = datetime.now()
        current_hour = now.hour
        
        if 0 <= current_hour < 8:
            # ASIA : Moins liquide → Augmenter cooldown
            session_mult = 1.2
        elif 8 <= current_hour < 14:
            # LONDON : Normal
            session_mult = 1.0
        else:
            # US : Haute liquidité → Réduire cooldown
            session_mult = 0.9
        
        multiplier *= session_mult
        
        # Calculer nouveau cooldown
        new_cooldown = int(base_cooldown * multiplier)
        
        # Cap min/max
        new_cooldown = max(10, min(new_cooldown, base_cooldown * 3))
        
        # Mettre à jour
        old_cooldown = self.current_cooldowns.get(strategy, base_cooldown)
        self.current_cooldowns[strategy] = new_cooldown
        
        if old_cooldown != new_cooldown:
            logger.info(
                "🔄 %s: Cooldown adapté %ds → %ds (x%.2f)",
                strategy,
                old_cooldown,
                new_cooldown,
                new_cooldown / base_cooldown
            )
    
    def get_cooldown(self, strategy: str) -> int:
        """
        Retourne cooldown actuel pour stratégie
        
        Args:
            strategy: Nom stratégie
            
        Returns:
            Cooldown en secondes
        """
        return self.current_cooldowns.get(
            strategy,
            self.base_cooldowns.get(strategy, 90)
        )
    
    def get_all_cooldowns(self) -> Dict[str, int]:
        """Retourne tous les cooldowns actuels"""
        return self.current_cooldowns.copy()
    
    def get_performance_summary(self) -> Dict:
        """Retourne résumé performances"""
        summary = {}
        
        for strategy_name, perf in self.performance.items():
            if perf.trades_last_hour > 0:
                summary[strategy_name] = {
                    'trades_last_hour': perf.trades_last_hour,
                    'win_rate_last_hour': perf.win_rate_last_hour,
                    'avg_pnl_last_hour': perf.avg_pnl_last_hour,
                    'current_cooldown': self.current_cooldowns.get(strategy_name, 90),
                    'base_cooldown': self.base_cooldowns.get(strategy_name, 90),
                    'multiplier': self.current_cooldowns.get(strategy_name, 90) / self.base_cooldowns.get(strategy_name, 90)
                }
        
        return summary
    
    def print_cooldowns_status(self):
        """Affiche status cooldowns"""
        print("\n" + "=" * 80)
        print("🔄 COOLDOWNS ADAPTATIFS STATUS")
        print("=" * 80)
        
        summary = self.get_performance_summary()
        
        if not summary:
            print("Aucun trade récent (dernière heure)")
            print("=" * 80 + "\n")
            return
        
        for strategy_name, data in sorted(summary.items()):
            base = data['base_cooldown']
            current = data['current_cooldown']
            mult = data['multiplier']
            wr = data['win_rate_last_hour'] * 100
            trades = data['trades_last_hour']
            
            # Emoji selon ajustement
            if mult < 0.8:
                emoji = "🔥"  # Réduit
            elif mult > 1.2:
                emoji = "❄️"  # Augmenté
            else:
                emoji = "➡️"  # Stable
            
            print(
                f"{emoji} {strategy_name:<30}: {base:>3}s → {current:>3}s (x{mult:.2f}) | "
                f"{trades} trades, WR={wr:.0f}%"
            )
        
        # Volatilité status
        if self.volatility_median:
            current_vol = self.volatility_history[-1] if self.volatility_history else self.volatility_median
            vol_ratio = current_vol / self.volatility_median
            print(f"\n📊 Volatilité actuelle: {vol_ratio:.2f}x median")
        
        print("=" * 80 + "\n")


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Cooldowns de base
    base_cooldowns = {
        "ml_3layer": 120,
        "vwap_sd": 60,
        "gamma_rejection": 45,
        "head_fake": 30
    }
    
    # Créer instance
    adaptive = AdaptiveCooldowns(base_cooldowns)
    
    print("📊 Simulation trades...\n")
    
    # Stratégie performante
    for i in range(10):
        win = i < 8  # 80% WR
        adaptive.add_trade("ml_3layer", win, 50 if win else -30)
    
    # Stratégie sous-performante
    for i in range(10):
        win = i < 2  # 20% WR
        adaptive.add_trade("vwap_sd", win, 50 if win else -30)
    
    # Update volatilité
    for _ in range(50):
        adaptive.update_volatility(5.0)
    
    # Spike volatilité
    for _ in range(10):
        adaptive.update_volatility(10.0)  # 2x median
    
    # Afficher status
    adaptive.print_cooldowns_status()
    
    # Summary
    import json
    print("\nPERFORMANCE SUMMARY:")
    print(json.dumps(adaptive.get_performance_summary(), indent=2))

