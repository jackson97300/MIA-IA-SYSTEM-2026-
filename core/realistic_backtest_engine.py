#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REALISTIC BACKTEST ENGINE - Modèle Slippage & Fill Probability
================================================================

Simule conditions réelles de trading :
- Slippage variable (volatilité, volume, spread)
- Fill probability (queue position, distance prix)
- Market impact (gros ordres bougent le prix)

Author: MIA System + Claude Sonnet 4.5
Date: 4 Novembre 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class BacktestConfig:
    """Configuration backtest réaliste"""
    base_slippage_ticks: float = 1.0  # Slippage minimum (ticks)
    volatility_multiplier: float = 0.5  # Impact volatilité sur slippage
    volume_multiplier: float = 0.3  # Impact volume sur slippage
    spread_multiplier: float = 0.2  # Impact spread sur slippage
    base_fill_prob: float = 0.70  # Probabilité fill par défaut
    max_slippage_ticks: float = 5.0  # Slippage maximum
    market_impact_factor: float = 0.001  # Impact par contrat (% du prix)
    fees_per_contract: float = 2.40  # Fees par contrat (USD)

@dataclass
class BacktestTrade:
    """Trade backtest avec conditions réalistes"""
    timestamp: datetime
    symbol: str
    direction: str  # 'UP' ou 'DOWN'
    entry_price: float
    exit_price: float
    entry_slippage_ticks: float
    exit_slippage_ticks: float
    entry_filled: bool
    exit_filled: bool
    pnl_gross: float  # PnL brut
    pnl_net: float  # PnL après slippage + fees
    win: bool  # Trade gagnant ?
    metadata: Dict = None

@dataclass
class BacktestResult:
    """Résultats backtest complets"""
    trades: List[BacktestTrade]
    total_trades: int
    filled_trades: int
    fill_rate: float
    win_rate: float
    profit_factor: float
    total_pnl_gross: float
    total_pnl_net: float
    total_slippage_cost: float
    total_fees: float
    sharpe_ratio: float
    max_drawdown: float
    avg_slippage_ticks: float

# ═══════════════════════════════════════════════════════════════
# REALISTIC BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════

class RealisticBacktestEngine:
    """
    Moteur backtest réaliste avec :
    - Slippage variable (volatilité, volume, spread)
    - Fill probability (queue position)
    - Market impact
    """

    def __init__(self, config: BacktestConfig = None, tick_size: float = 0.25):
        """
        Initialisation

        Args:
            config: Configuration backtest
            tick_size: Taille du tick (ES/NQ: 0.25)
        """
        self.config = config or BacktestConfig()
        self.tick_size = tick_size
        self.trades = []
        logger.info("🎯 Realistic Backtest Engine initialisé")

    def calculate_slippage(self,
                          current_volatility: float,
                          avg_volatility: float,
                          current_volume: float,
                          avg_volume: float,
                          spread_ticks: float) -> float:
        """
        Calcule slippage réaliste

        Args:
            current_volatility: ATR actuel
            avg_volatility: ATR moyen
            current_volume: Volume actuel
            avg_volume: Volume moyen
            spread_ticks: Spread en ticks

        Returns:
            Slippage en ticks
        """
        # Composante volatilité
        vol_ratio = current_volatility / max(avg_volatility, 1e-6)
        vol_component = vol_ratio * self.config.volatility_multiplier

        # Composante volume (faible volume → plus de slippage)
        volume_ratio = current_volume / max(avg_volume, 1)
        volume_component = (1 / volume_ratio) * self.config.volume_multiplier if volume_ratio > 0 else 1.0

        # Composante spread
        spread_component = (spread_ticks / 2.0) * self.config.spread_multiplier

        # Slippage total
        total_slippage = (
            self.config.base_slippage_ticks +
            vol_component +
            volume_component +
            spread_component
        )

        # Limiter au maximum
        return min(total_slippage, self.config.max_slippage_ticks)

    def calculate_fill_probability(self,
                                   order_price: float,
                                   market_price: float,
                                   spread_ticks: float,
                                   queue_position_pct: float = 0.5) -> float:
        """
        Calcule probabilité de fill

        Args:
            order_price: Prix ordre
            market_price: Prix marché (mid)
            spread_ticks: Spread en ticks
            queue_position_pct: Position dans la file (0-1)

        Returns:
            Probabilité fill (0-1)
        """
        price_diff_ticks = abs(order_price - market_price) / self.tick_size

        # Si ordre limit à market price
        if price_diff_ticks < 0.5:
            # Dépend de la position dans la queue
            base_prob = 0.60
            queue_bonus = (1 - queue_position_pct) * 0.30
            return base_prob + queue_bonus

        # Si ordre 1 tick better que market
        elif price_diff_ticks <= 1.5:
            return 0.85

        # Si ordre 2+ ticks better que market
        elif price_diff_ticks <= 3.0:
            return 0.95

        # Ordre loin du marché
        else:
            return 0.98

    def calculate_market_impact(self,
                                order_size: int,
                                avg_volume: float,
                                price: float) -> float:
        """
        Calcule impact marché (gros ordres bougent le prix)

        Args:
            order_size: Taille ordre (contrats)
            avg_volume: Volume moyen
            price: Prix actuel

        Returns:
            Impact en dollars
        """
        # Impact proportionnel à la taille relative de l'ordre
        size_ratio = order_size / max(avg_volume, 1)
        impact_pct = size_ratio * self.config.market_impact_factor
        return price * impact_pct

    def simulate_trade(self,
                      entry_signal: Dict,
                      exit_signal: Dict,
                      direction: str,
                      market_data: Dict) -> BacktestTrade:
        """
        Simule un trade avec conditions réalistes

        Args:
            entry_signal: Signal d'entrée (timestamp, price, etc.)
            exit_signal: Signal de sortie
            direction: 'UP' ou 'DOWN'
            market_data: Données marché (volatility, volume, spread)

        Returns:
            BacktestTrade avec résultats
        """
        # Données entrée
        entry_price = entry_signal['price']
        entry_volatility = market_data.get('entry_volatility', 1.0)
        entry_volume = market_data.get('entry_volume', 1000)
        entry_spread_ticks = market_data.get('entry_spread_ticks', 1.0)

        # Données sortie
        exit_price = exit_signal['price']
        exit_volatility = market_data.get('exit_volatility', 1.0)
        exit_volume = market_data.get('exit_volume', 1000)
        exit_spread_ticks = market_data.get('exit_spread_ticks', 1.0)

        # Moyennes
        avg_volatility = market_data.get('avg_volatility', 1.0)
        avg_volume = market_data.get('avg_volume', 1000)

        # Calculer slippage
        entry_slippage = self.calculate_slippage(
            entry_volatility, avg_volatility,
            entry_volume, avg_volume,
            entry_spread_ticks
        )
        exit_slippage = self.calculate_slippage(
            exit_volatility, avg_volatility,
            exit_volume, avg_volume,
            exit_spread_ticks
        )

        # Calculer probabilité fill
        entry_fill_prob = self.calculate_fill_probability(
            entry_price, entry_price, entry_spread_ticks
        )
        exit_fill_prob = self.calculate_fill_probability(
            exit_price, exit_price, exit_spread_ticks
        )

        # Simuler fills (random)
        entry_filled = np.random.random() < entry_fill_prob
        exit_filled = np.random.random() < exit_fill_prob if entry_filled else False

        # Si pas filled, pas de trade
        if not entry_filled or not exit_filled:
            return BacktestTrade(
                timestamp=entry_signal['timestamp'],
                symbol=entry_signal['symbol'],
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_slippage_ticks=entry_slippage,
                exit_slippage_ticks=exit_slippage,
                entry_filled=entry_filled,
                exit_filled=exit_filled,
                pnl_gross=0,
                pnl_net=0,
                win=False
            )

        # Appliquer slippage au prix
        if direction == 'UP':
            entry_price_with_slippage = entry_price + (entry_slippage * self.tick_size)
            exit_price_with_slippage = exit_price - (exit_slippage * self.tick_size)
        else:  # DOWN
            entry_price_with_slippage = entry_price - (entry_slippage * self.tick_size)
            exit_price_with_slippage = exit_price + (exit_slippage * self.tick_size)

        # Calculer PnL brut
        if direction == 'UP':
            pnl_gross = exit_price - entry_price
        else:
            pnl_gross = entry_price - exit_price

        # Calculer PnL net (après slippage + fees)
        slippage_cost = (entry_slippage + exit_slippage) * self.tick_size
        fees_cost = self.config.fees_per_contract * 2  # Entrée + sortie
        pnl_net = pnl_gross - slippage_cost - fees_cost

        # Trade gagnant ?
        win = pnl_net > 0

        return BacktestTrade(
            timestamp=entry_signal['timestamp'],
            symbol=entry_signal['symbol'],
            direction=direction,
            entry_price=entry_price_with_slippage,
            exit_price=exit_price_with_slippage,
            entry_slippage_ticks=entry_slippage,
            exit_slippage_ticks=exit_slippage,
            entry_filled=entry_filled,
            exit_filled=exit_filled,
            pnl_gross=pnl_gross,
            pnl_net=pnl_net,
            win=win,
            metadata={'entry_fill_prob': entry_fill_prob, 'exit_fill_prob': exit_fill_prob}
        )

    def run_backtest(self, signals: List[Dict], market_data: pd.DataFrame) -> BacktestResult:
        """
        Lance backtest complet

        Args:
            signals: Liste signaux (entry + exit)
            market_data: DataFrame avec colonnes volatility, volume, spread

        Returns:
            BacktestResult complet
        """
        trades = []

        for signal in signals:
            # Extraire données marché pour ce signal
            entry_ts = signal['entry_timestamp']
            exit_ts = signal['exit_timestamp']

            entry_row = market_data[market_data['timestamp'] == entry_ts].iloc[0]
            exit_row = market_data[market_data['timestamp'] == exit_ts].iloc[0]

            market_context = {
                'entry_volatility': entry_row.get('atr', 1.0),
                'entry_volume': entry_row.get('volume', 1000),
                'entry_spread_ticks': entry_row.get('spread_ticks', 1.0),
                'exit_volatility': exit_row.get('atr', 1.0),
                'exit_volume': exit_row.get('volume', 1000),
                'exit_spread_ticks': exit_row.get('spread_ticks', 1.0),
                'avg_volatility': market_data['atr'].mean(),
                'avg_volume': market_data['volume'].mean()
            }

            # Simuler trade
            trade = self.simulate_trade(
                entry_signal={'timestamp': entry_ts, 'price': signal['entry_price'], 'symbol': signal['symbol']},
                exit_signal={'timestamp': exit_ts, 'price': signal['exit_price']},
                direction=signal['direction'],
                market_data=market_context
            )

            trades.append(trade)

        # Calculer métriques
        return self._calculate_metrics(trades)

    def _calculate_metrics(self, trades: List[BacktestTrade]) -> BacktestResult:
        """Calcule métriques backtest"""
        filled_trades = [t for t in trades if t.entry_filled and t.exit_filled]

        if not filled_trades:
            return BacktestResult(
                trades=trades,
                total_trades=len(trades),
                filled_trades=0,
                fill_rate=0,
                win_rate=0,
                profit_factor=0,
                total_pnl_gross=0,
                total_pnl_net=0,
                total_slippage_cost=0,
                total_fees=0,
                sharpe_ratio=0,
                max_drawdown=0,
                avg_slippage_ticks=0
            )

        # Métriques de base
        fill_rate = len(filled_trades) / len(trades)
        winners = [t for t in filled_trades if t.win]
        win_rate = len(winners) / len(filled_trades)

        # PnL
        total_pnl_gross = sum(t.pnl_gross for t in filled_trades)
        total_pnl_net = sum(t.pnl_net for t in filled_trades)

        # Slippage & fees
        total_slippage_ticks = sum(t.entry_slippage_ticks + t.exit_slippage_ticks for t in filled_trades)
        avg_slippage_ticks = total_slippage_ticks / len(filled_trades)
        total_slippage_cost = total_slippage_ticks * self.tick_size
        total_fees = len(filled_trades) * self.config.fees_per_contract * 2

        # Profit Factor
        gross_profits = sum(t.pnl_net for t in winners)
        gross_losses = abs(sum(t.pnl_net for t in filled_trades if not t.win))
        profit_factor = gross_profits / max(gross_losses, 1)

        # Sharpe Ratio (simplifié)
        returns = [t.pnl_net for t in filled_trades]
        sharpe_ratio = np.mean(returns) / max(np.std(returns), 1e-6) * np.sqrt(252) if len(returns) > 1 else 0

        # Max Drawdown
        cumulative_pnl = np.cumsum([t.pnl_net for t in filled_trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

        return BacktestResult(
            trades=trades,
            total_trades=len(trades),
            filled_trades=len(filled_trades),
            fill_rate=fill_rate,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_pnl_gross=total_pnl_gross,
            total_pnl_net=total_pnl_net,
            total_slippage_cost=total_slippage_cost,
            total_fees=total_fees,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_slippage_ticks=avg_slippage_ticks
        )


# ═══════════════════════════════════════════════════════════════
# FONCTION HELPER
# ═══════════════════════════════════════════════════════════════

def create_realistic_backtest_engine(symbol: str = 'ES') -> RealisticBacktestEngine:
    """
    Factory function pour créer backtest engine

    Args:
        symbol: ES ou NQ

    Returns:
        RealisticBacktestEngine configuré
    """
    tick_size = 0.25  # ES et NQ
    config = BacktestConfig()

    return RealisticBacktestEngine(config=config, tick_size=tick_size)


if __name__ == "__main__":
    # Test simple
    logging.basicConfig(level=logging.INFO)

    engine = create_realistic_backtest_engine('NQ')

    # Signal test
    signal = {
        'entry_timestamp': datetime.now(),
        'exit_timestamp': datetime.now(),
        'entry_price': 16000.0,
        'exit_price': 16010.0,
        'direction': 'UP',
        'symbol': 'NQ'
    }

    market_data = {
        'entry_volatility': 15.0,
        'entry_volume': 1500,
        'entry_spread_ticks': 1.0,
        'exit_volatility': 16.0,
        'exit_volume': 1200,
        'exit_spread_ticks': 1.5,
        'avg_volatility': 14.0,
        'avg_volume': 1400
    }

    trade = engine.simulate_trade(
        {'timestamp': signal['entry_timestamp'], 'price': signal['entry_price'], 'symbol': 'NQ'},
        {'timestamp': signal['exit_timestamp'], 'price': signal['exit_price']},
        'UP',
        market_data
    )

    print(f"✅ Trade simulé:")
    print(f"   Entry filled: {trade.entry_filled}")
    print(f"   Exit filled: {trade.exit_filled}")
    print(f"   Slippage entry: {trade.entry_slippage_ticks:.2f} ticks")
    print(f"   Slippage exit: {trade.exit_slippage_ticks:.2f} ticks")
    print(f"   PnL gross: ${trade.pnl_gross:.2f}")
    print(f"   PnL net: ${trade.pnl_net:.2f}")
    print(f"   Win: {trade.win}")


