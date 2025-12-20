#!/usr/bin/env python3
"""
Performance Metrics - Dashboard Temps Réel
Calcul Sharpe, Sortino, Profit Factor, Expectancy

Sprint 1 - TODO Tasks 3a, 3b, 3c, 3d
Date: 13 Novembre 2025
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Trade individuel"""
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str  # LONG/SHORT
    entry_price: float
    exit_price: float
    pnl: float
    pnl_r: float  # En R multiples
    win: bool
    duration_seconds: float


@dataclass
class StrategyStats:
    """Statistiques par stratégie"""
    name: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy_r: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_consecutive: int = 0
    last_result: Optional[bool] = None


class PerformanceMetrics:
    """
    Calcul métriques performance temps réel
    
    Métriques :
    - Sharpe Ratio (rolling 24h)
    - Sortino Ratio (focus downside)
    - Profit Factor (gross_profit / gross_loss)
    - Expectancy (expected value par trade)
    - Win Rate, Avg Win/Loss
    - Breakdown par stratégie
    """
    
    def __init__(self, window_hours: int = 24):
        self.window_hours = window_hours
        self.window_seconds = window_hours * 3600
        
        # Historique trades
        self.trades: deque = deque(maxlen=10000)
        
        # Stats par stratégie
        self.strategy_stats: Dict[str, StrategyStats] = defaultdict(
            lambda: StrategyStats(name="unknown")
        )
        
        # Métriques globales
        self.total_trades = 0
        self.total_wins = 0
        self.total_losses = 0
        self.total_pnl = 0.0
        
        # Dernière mise à jour console
        self.last_console_update = datetime.now()
        self.console_update_interval = 300  # 5 min
        
        logger.info("📊 PerformanceMetrics initialisé (window=%dh)", window_hours)
    
    def add_trade(self, trade: Trade):
        """Ajoute un trade et met à jour statistiques"""
        self.trades.append(trade)
        self.total_trades += 1
        
        if trade.win:
            self.total_wins += 1
        else:
            self.total_losses += 1
        
        self.total_pnl += trade.pnl
        
        # Mise à jour stats stratégie
        self._update_strategy_stats(trade)
        
        # Log trade
        logger.info(
            "📈 TRADE: %s %s %s | PnL: $%.2f (%.2fR) | Strategy: %s",
            trade.symbol,
            trade.direction,
            "WIN ✅" if trade.win else "LOSS ❌",
            trade.pnl,
            trade.pnl_r,
            trade.strategy
        )
    
    def _update_strategy_stats(self, trade: Trade):
        """Met à jour statistiques stratégie"""
        stats = self.strategy_stats[trade.strategy]
        stats.name = trade.strategy
        stats.trades += 1
        stats.total_pnl += trade.pnl
        
        if trade.win:
            stats.wins += 1
            # Consecutive tracking
            if stats.last_result == True:
                stats.current_consecutive += 1
            else:
                stats.current_consecutive = 1
            stats.max_consecutive_wins = max(
                stats.max_consecutive_wins,
                stats.current_consecutive
            )
        else:
            stats.losses += 1
            # Consecutive tracking
            if stats.last_result == False:
                stats.current_consecutive += 1
            else:
                stats.current_consecutive = 1
            stats.max_consecutive_losses = max(
                stats.max_consecutive_losses,
                stats.current_consecutive
            )
        
        stats.last_result = trade.win
        
        # Recalculer métriques
        self._recalculate_strategy_metrics(stats, trade)
    
    def _recalculate_strategy_metrics(self, stats: StrategyStats, trade: Trade):
        """Recalcule métriques stratégie"""
        # Win rate
        if stats.trades > 0:
            stats.win_rate = stats.wins / stats.trades
        
        # Avg win/loss
        wins_pnl = [t.pnl for t in self.trades if t.strategy == stats.name and t.win]
        losses_pnl = [t.pnl for t in self.trades if t.strategy == stats.name and not t.win]
        
        if wins_pnl:
            stats.avg_win = np.mean(wins_pnl)
        if losses_pnl:
            stats.avg_loss = np.mean(losses_pnl)
        
        # Profit Factor
        gross_profit = sum(wins_pnl) if wins_pnl else 0
        gross_loss = abs(sum(losses_pnl)) if losses_pnl else 0
        
        if gross_loss > 0:
            stats.profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            stats.profit_factor = 999.0  # Infini (pas de pertes)
        
        # Expectancy (en R)
        r_wins = [t.pnl_r for t in self.trades if t.strategy == stats.name and t.win]
        r_losses = [t.pnl_r for t in self.trades if t.strategy == stats.name and not t.win]
        
        if r_wins or r_losses:
            avg_r_win = np.mean(r_wins) if r_wins else 0
            avg_r_loss = np.mean(r_losses) if r_losses else 0
            stats.expectancy_r = (stats.win_rate * avg_r_win) - ((1 - stats.win_rate) * abs(avg_r_loss))
    
    def get_sharpe_ratio(self) -> float:
        """
        Calcul Sharpe Ratio (rolling window)
        
        Sharpe = mean(returns) / std(returns) * sqrt(252)
        """
        trades_window = self._get_trades_in_window()
        
        if len(trades_window) < 2:
            return 0.0
        
        returns = [t.pnl for t in trades_window]
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualisé (252 jours trading)
        sharpe = (mean_return / std_return) * np.sqrt(252)
        
        return sharpe
    
    def get_sortino_ratio(self) -> float:
        """
        Calcul Sortino Ratio (focus downside risk)
        
        Sortino = mean(returns) / downside_std * sqrt(252)
        """
        trades_window = self._get_trades_in_window()
        
        if len(trades_window) < 2:
            return 0.0
        
        returns = [t.pnl for t in trades_window]
        
        mean_return = np.mean(returns)
        
        # Downside deviation (seulement pertes)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return 999.0  # Pas de downside
        
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return 0.0
        
        # Annualisé
        sortino = (mean_return / downside_std) * np.sqrt(252)
        
        return sortino
    
    def get_profit_factor(self) -> float:
        """
        Calcul Profit Factor global
        
        PF = gross_profit / gross_loss
        Target: > 1.5
        """
        trades_window = self._get_trades_in_window()
        
        if not trades_window:
            return 0.0
        
        gross_profit = sum(t.pnl for t in trades_window if t.win)
        gross_loss = abs(sum(t.pnl for t in trades_window if not t.win))
        
        if gross_loss == 0:
            return 999.0 if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def get_expectancy(self) -> float:
        """
        Calcul Expectancy (en R multiples)
        
        Expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
        Target: > 0.5R
        """
        trades_window = self._get_trades_in_window()
        
        if not trades_window:
            return 0.0
        
        wins = [t for t in trades_window if t.win]
        losses = [t for t in trades_window if not t.win]
        
        win_rate = len(wins) / len(trades_window) if trades_window else 0
        loss_rate = 1 - win_rate
        
        avg_win_r = np.mean([t.pnl_r for t in wins]) if wins else 0
        avg_loss_r = np.mean([t.pnl_r for t in losses]) if losses else 0
        
        expectancy = (win_rate * avg_win_r) - (loss_rate * abs(avg_loss_r))
        
        return expectancy
    
    def _get_trades_in_window(self) -> List[Trade]:
        """Retourne trades dans la fenêtre rolling"""
        if not self.trades:
            return []
        
        cutoff_time = datetime.now() - timedelta(seconds=self.window_seconds)
        
        return [t for t in self.trades if t.timestamp >= cutoff_time]
    
    def get_win_rate(self) -> float:
        """Win rate global"""
        if self.total_trades == 0:
            return 0.0
        return self.total_wins / self.total_trades
    
    def print_dashboard(self, force: bool = False):
        """
        Affiche dashboard console
        
        Args:
            force: Force l'affichage même si interval pas écoulé
        """
        now = datetime.now()
        elapsed = (now - self.last_console_update).total_seconds()
        
        if not force and elapsed < self.console_update_interval:
            return
        
        self.last_console_update = now
        
        # Métriques window
        trades_window = self._get_trades_in_window()
        
        if not trades_window:
            logger.info("📊 Pas encore de trades dans la fenêtre %dh", self.window_hours)
            return
        
        sharpe = self.get_sharpe_ratio()
        sortino = self.get_sortino_ratio()
        pf = self.get_profit_factor()
        expectancy = self.get_expectancy()
        wr = self.get_win_rate()
        
        # Header
        print("\n" + "=" * 80)
        print(f"📊 PERFORMANCE METRICS (Last {self.window_hours}h)")
        print("=" * 80)
        
        # Global stats
        print(f"Trades: {len(trades_window)} | Win Rate: {wr*100:.1f}% | PnL: ${self.total_pnl:+.2f}")
        print(f"Sharpe Ratio: {sharpe:.2f} | Sortino: {sortino:.2f}")
        print(f"Profit Factor: {pf:.2f} | Expectancy: {expectancy:.2f}R")
        
        # Breakdown par stratégie
        print("\nBREAKDOWN BY STRATEGY:")
        
        for strategy_name, stats in sorted(
            self.strategy_stats.items(),
            key=lambda x: x[1].trades,
            reverse=True
        ):
            if stats.trades == 0:
                continue
            
            print(
                f"  {strategy_name:<30}: {stats.trades:>3} trades, "
                f"{stats.win_rate*100:>5.1f}% WR, PF={stats.profit_factor:>4.1f}, "
                f"E={stats.expectancy_r:>+5.2f}R"
            )
        
        print("=" * 80 + "\n")
    
    def get_strategy_performance(self, strategy_name: str) -> Optional[StrategyStats]:
        """Retourne performance d'une stratégie"""
        return self.strategy_stats.get(strategy_name)
    
    def get_summary(self) -> Dict:
        """Retourne résumé métriques"""
        return {
            "total_trades": self.total_trades,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "win_rate": self.get_win_rate(),
            "total_pnl": self.total_pnl,
            "sharpe_ratio": self.get_sharpe_ratio(),
            "sortino_ratio": self.get_sortino_ratio(),
            "profit_factor": self.get_profit_factor(),
            "expectancy_r": self.get_expectancy(),
            "strategies": {
                name: {
                    "trades": stats.trades,
                    "win_rate": stats.win_rate,
                    "profit_factor": stats.profit_factor,
                    "expectancy_r": stats.expectancy_r
                }
                for name, stats in self.strategy_stats.items()
                if stats.trades > 0
            }
        }


# === TEST ===
if __name__ == "__main__":
    import time
    
    logging.basicConfig(level=logging.INFO)
    
    # Créer instance
    metrics = PerformanceMetrics(window_hours=24)
    
    # Simuler trades
    test_trades = [
        Trade(datetime.now(), "ES", "ml_3layer", "LONG", 6870, 6880, 50, 2.5, True, 300),
        Trade(datetime.now(), "ES", "vwap_sd", "SHORT", 6880, 6870, 50, 2.0, True, 180),
        Trade(datetime.now(), "NQ", "ml_3layer", "LONG", 25600, 25580, -100, -2.0, False, 240),
        Trade(datetime.now(), "ES", "gamma_rejection", "SHORT", 6870, 6875, -25, -1.0, False, 120),
        Trade(datetime.now(), "ES", "vwap_sd", "LONG", 6865, 6885, 100, 4.0, True, 600),
    ]
    
    for trade in test_trades:
        metrics.add_trade(trade)
        time.sleep(0.1)
    
    # Afficher dashboard
    metrics.print_dashboard(force=True)
    
    # Summary
    summary = metrics.get_summary()
    print("\nSUMMARY:")
    import json
    print(json.dumps(summary, indent=2))

