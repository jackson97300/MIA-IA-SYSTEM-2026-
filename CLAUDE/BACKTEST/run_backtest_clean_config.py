"""
🔬 BACKTEST CONFIG CLEAN - Seuils Backtest + Session Quality Minimal
=====================================================================
Configuration:
- Base: Seuils backtest 85% WR (confidence 0.60/0.30, distances, etc.)
- + Session Quality: London 08:00-11:00, US 15:50-17:00 + 20:00-21:30
- + Lunch Block: 17:00-19:30
- + Hard Stop: 21:30-08:00
- + Risk Management minimal (4 validations)

Total: 19 validations (vs 47 live, vs 12 backtest original)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, time
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import logging

# Configuration logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

logging.getLogger('ml').setLevel(logging.ERROR)
logging.getLogger('strategies').setLevel(logging.ERROR)
logging.getLogger('core').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# Paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE")

DATES = [
    "20251105", "20251106", "20251107",
    "20251110", "20251111", "20251112", "20251113", "20251114",
    "20251117", "20251118", "20251119", "20251120", "20251121",
    "20251124", "20251125", "20251126", "20251127"
]

SYMBOL = "ES"
CHART_ID = 3

def find_data_file(date: str) -> Path:
    file_path = (
        BASE_PATH / date / f"CHART_{CHART_ID}" / "ML_READY" /
        f"ml_{SYMBOL}Z25_FUT_CME_{CHART_ID}.jsonl"
    )
    return file_path if file_path.exists() else None

def load_snapshots(file_path: Path) -> list:
    snapshots = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snapshots.append(json.loads(line))
                except:
                    continue
    return snapshots

@dataclass
class BacktestTrade:
    entry_time: int
    entry_price: float
    direction: str
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    setup_type: str
    confidence: float
    session: str = "UNKNOWN"

    exit_time: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_ticks: Optional[float] = None
    pnl_usd: Optional[float] = None
    mae_ticks: Optional[float] = None
    mfe_ticks: Optional[float] = None
    duration_seconds: Optional[int] = None
    is_win: Optional[bool] = None

class SessionQualityChecker:
    """Session Quality Minimal - 3 validations seulement"""

    def __init__(self):
        self.stats = {
            'total_checks': 0,
            'blocks_hours': 0,
            'blocks_lunch': 0,
            'blocks_overnight': 0,
            'allowed': 0
        }

    def check_session(self, tick: Dict) -> Tuple[bool, str]:
        """
        Vérifie si on peut trader selon l'heure (Paris time)

        Returns:
            (can_trade: bool, reason: str)
        """
        self.stats['total_checks'] += 1

        # Extraire timestamp
        t_ms = tick.get('t_ms', 0)
        if not t_ms:
            return False, "No timestamp"

        # Convertir en datetime Paris
        from datetime import timezone, timedelta
        paris_tz = timezone(timedelta(hours=1))  # UTC+1 (approximation)
        dt = datetime.fromtimestamp(t_ms / 1000, tz=paris_tz)
        hour = dt.hour
        minute = dt.minute

        # 1. HARD STOP: 21:30 → 08:00
        if hour >= 21 and minute >= 30:
            self.stats['blocks_overnight'] += 1
            return False, f"Hard Stop (21:30+) - {hour:02d}:{minute:02d}"
        if hour < 8:
            self.stats['blocks_overnight'] += 1
            return False, f"Overnight - {hour:02d}:{minute:02d}"

        # 2. LUNCH BLOCK: 17:00 → 19:30
        if (hour == 17 and minute >= 0) or (hour == 18) or (hour == 19 and minute < 30):
            self.stats['blocks_lunch'] += 1
            return False, f"Lunch Block - {hour:02d}:{minute:02d}"

        # 3. TRADING HOURS
        # London: 08:00 → 11:00
        if 8 <= hour < 11:
            self.stats['allowed'] += 1
            return True, "London Session"

        # US Morning: 15:50 → 17:00
        if (hour == 15 and minute >= 50) or (hour == 16):
            self.stats['allowed'] += 1
            return True, "US Morning"

        # US Power Hour: 20:00 → 21:30
        if hour == 20 or (hour == 21 and minute < 30):
            self.stats['allowed'] += 1
            return True, "US Power Hour"

        # Hors heures
        self.stats['blocks_hours'] += 1
        return False, f"Hors heures - {hour:02d}:{minute:02d}"

class CleanConfigBacktester:
    """Backtester avec config clean (19 validations)"""

    def __init__(self):
        # Initialiser stratégie
        from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
        from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy

        print("🚀 Initialisation ML 3-Layer System...")
        self.ml_system = ML3LayerIntegratedSystem(
            symbols=[SYMBOL],
            use_ml_models=False  # ✅ Désactivé (comme backtest)
        )
        print("✅ ML System initialisé")

        print("🎯 Initialisation Strategy...")
        self.strategy = MenthorQ3LayerStrategy(ml_3layer_system=self.ml_system)
        print("✅ Stratégie initialisée\n")

        # Session Quality Checker
        self.session_checker = SessionQualityChecker()

        # Config
        self.tick_size = 0.25
        self.tick_value = 12.50

        # Trades
        self.trades: List[BacktestTrade] = []
        self.open_trade: Optional[BacktestTrade] = None

        # Tracking
        self.highest_price = 0.0
        self.lowest_price = 999999.0
        self.be_triggered = False
        self.last_trade_time = 0
        self.cooldown_ms = 120000  # 2 min (comme backtest)

        # TP/SL (comme backtest)
        self.sl_ticks = self.strategy.sl_optimal_ticks.get(SYMBOL, 22)
        self.tp1_ticks = self.strategy.tp_optimal_ticks.get(SYMBOL, 30)

        # Trailing/BE (comme backtest)
        self.trail_activation = 10
        self.trail_distance = 5
        self.be_trigger = 7
        self.be_buffer = 2

        # Stats
        self.stats = {
            'total_snapshots': 0,
            'session_blocked': 0,
            'strategy_signals': 0,
            'cooldown_blocked': 0,
            'trades_opened': 0
        }

    def _check_exit(self, tick: Dict) -> Optional[Tuple[str, float]]:
        """Vérifie exit (identique backtest original)"""
        if not self.open_trade:
            return None

        mid = tick.get('mid', 0)
        high = tick.get('high', mid)
        low = tick.get('low', mid)
        trade = self.open_trade

        self.highest_price = max(self.highest_price, high)
        self.lowest_price = min(self.lowest_price, low)

        # SL
        if trade.direction == 'LONG':
            if low <= trade.stop_loss:
                return ('SL', trade.stop_loss)
        else:
            if high >= trade.stop_loss:
                return ('SL', trade.stop_loss)

        # BE
        if not self.be_triggered:
            if trade.direction == 'LONG':
                profit = (high - trade.entry_price) / self.tick_size
                if profit >= self.be_trigger:
                    trade.stop_loss = trade.entry_price + self.be_buffer * self.tick_size
                    self.be_triggered = True
            else:
                profit = (trade.entry_price - low) / self.tick_size
                if profit >= self.be_trigger:
                    trade.stop_loss = trade.entry_price - self.be_buffer * self.tick_size
                    self.be_triggered = True

        # Trail
        if trade.direction == 'LONG':
            profit = (self.highest_price - trade.entry_price) / self.tick_size
            if profit >= self.trail_activation:
                new_sl = self.highest_price - self.trail_distance * self.tick_size
                if new_sl > trade.stop_loss:
                    trade.stop_loss = new_sl
                if low <= trade.stop_loss:
                    return ('TRAIL', trade.stop_loss)
        else:
            profit = (trade.entry_price - self.lowest_price) / self.tick_size
            if profit >= self.trail_activation:
                new_sl = self.lowest_price + self.trail_distance * self.tick_size
                if new_sl < trade.stop_loss:
                    trade.stop_loss = new_sl
                if high >= trade.stop_loss:
                    return ('TRAIL', trade.stop_loss)

        # TP
        if trade.direction == 'LONG':
            if high >= trade.take_profit_1:
                return ('TP1', trade.take_profit_1)
        else:
            if low <= trade.take_profit_1:
                return ('TP1', trade.take_profit_1)

        return None

    def _close_trade(self, tick: Dict, reason: str, price: float):
        """Ferme trade (identique backtest original)"""
        if not self.open_trade:
            return

        trade = self.open_trade
        t_ms = tick.get('t_ms', 0)

        if trade.direction == 'LONG':
            pnl_ticks = (price - trade.entry_price) / self.tick_size
            mae = (trade.entry_price - self.lowest_price) / self.tick_size
            mfe = (self.highest_price - trade.entry_price) / self.tick_size
        else:
            pnl_ticks = (trade.entry_price - price) / self.tick_size
            mae = (self.highest_price - trade.entry_price) / self.tick_size
            mfe = (trade.entry_price - self.lowest_price) / self.tick_size

        trade.exit_time = t_ms
        trade.exit_price = price
        trade.exit_reason = reason
        trade.pnl_ticks = pnl_ticks
        trade.pnl_usd = pnl_ticks * self.tick_value
        trade.mae_ticks = mae
        trade.mfe_ticks = mfe
        trade.duration_seconds = (t_ms - trade.entry_time) // 1000 if trade.entry_time else 0
        trade.is_win = pnl_ticks > 0

        self.trades.append(trade)

        # Reset
        self.open_trade = None
        self.highest_price = 0.0
        self.lowest_price = 999999.0
        self.be_triggered = False
        self.last_trade_time = t_ms

    def _open_trade(self, tick: Dict, signal: Dict):
        """Ouvre trade (identique backtest original)"""
        t_ms = tick.get('t_ms', 0)

        self.open_trade = BacktestTrade(
            entry_time=t_ms,
            entry_price=signal['entry'],
            direction=signal['action'],
            stop_loss=signal['stop'],
            take_profit_1=signal['targets'][0] if signal.get('targets') else signal['entry'] + self.tp1_ticks * self.tick_size,
            take_profit_2=signal['targets'][1] if signal.get('targets') and len(signal['targets']) > 1 else None,
            setup_type=signal.get('strategy', 'menthorq_3layer'),
            confidence=signal.get('confidence', 0.0),
            session=tick.get('session', tick.get('session_id', 'UNKNOWN'))
        )

        mid = tick.get('mid', signal['entry'])
        self.highest_price = mid
        self.lowest_price = mid
        self.be_triggered = False
        self.stats['trades_opened'] += 1

    def process_tick(self, tick: Dict):
        """Traite un tick avec Session Quality Check"""
        self.stats['total_snapshots'] += 1
        t_ms = tick.get('t_ms', 0)

        # Check exit si trade ouvert
        if self.open_trade:
            result = self._check_exit(tick)
            if result:
                self._close_trade(tick, result[0], result[1])
                return

        # ✅ NOUVEAU: Session Quality Check
        can_trade, reason = self.session_checker.check_session(tick)
        if not can_trade:
            self.stats['session_blocked'] += 1
            return

        # Cooldown
        if t_ms - self.last_trade_time < self.cooldown_ms:
            self.stats['cooldown_blocked'] += 1
            return

        # Chercher signal
        if not self.open_trade:
            signal = self.strategy.analyze_from_ml_ready(tick, symbol=SYMBOL)
            if signal:
                self.stats['strategy_signals'] += 1
                self._open_trade(tick, signal)

    def run_backtest(self):
        """Lance backtest complet"""
        print("=" * 70)
        print("🔬 BACKTEST CONFIG CLEAN - 17 JOURS")
        print("=" * 70)
        print(f"Symbole: {SYMBOL}")
        print(f"Config: Seuils Backtest + Session Quality Minimal")
        print(f"Validations: 19 (vs 47 live, vs 12 backtest original)")
        print("=" * 70)
        print()

        total_snapshots_loaded = 0

        for date in DATES:
            file_path = find_data_file(date)
            if not file_path:
                print(f"⚠️ {date}: Fichier non trouvé")
                continue

            snapshots = load_snapshots(file_path)
            total_snapshots_loaded += len(snapshots)
            print(f"📅 {date}: {len(snapshots):,} snapshots chargés")

            for tick in snapshots:
                self.process_tick(tick)

        print()
        print("=" * 70)
        print("📊 STATISTIQUES DE FILTRAGE")
        print("=" * 70)
        print(f"Total snapshots chargés:     {total_snapshots_loaded:,}")
        print(f"Total snapshots traités:     {self.stats['total_snapshots']:,}")
        print(f"Bloqués par Session Quality: {self.stats['session_blocked']:,} ({self.stats['session_blocked']/self.stats['total_snapshots']*100:.1f}%)")
        print(f"  - Hors heures:             {self.session_checker.stats['blocks_hours']:,}")
        print(f"  - Lunch block:             {self.session_checker.stats['blocks_lunch']:,}")
        print(f"  - Overnight:               {self.session_checker.stats['blocks_overnight']:,}")
        print(f"Autorisés par Session:       {self.session_checker.stats['allowed']:,} ({self.session_checker.stats['allowed']/self.stats['total_snapshots']*100:.1f}%)")
        print(f"Signaux stratégie générés:   {self.stats['strategy_signals']:,}")
        print(f"Bloqués par cooldown:        {self.stats['cooldown_blocked']:,}")
        print(f"Trades ouverts:              {self.stats['trades_opened']:,}")
        print()

        # Calcul résultats
        if not self.trades:
            print("❌ Aucun trade généré!")
            return

        wins = [t for t in self.trades if t.is_win]
        losses = [t for t in self.trades if not t.is_win]

        total_pnl_ticks = sum(t.pnl_ticks for t in self.trades)
        total_pnl_usd = sum(t.pnl_usd for t in self.trades)

        win_rate = len(wins) / len(self.trades) * 100

        winning_ticks = sum(t.pnl_ticks for t in wins) if wins else 0
        losing_ticks = sum(abs(t.pnl_ticks) for t in losses) if losses else 0
        profit_factor = winning_ticks / losing_ticks if losing_ticks > 0 else 0

        print("=" * 70)
        print("📊 RÉSULTATS FINAUX - CONFIG CLEAN")
        print("=" * 70)
        print()
        print(f"Total Trades: {len(self.trades)}")
        print(f"Wins: {len(wins)} | Losses: {len(losses)}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"P&L: {total_pnl_ticks:+.1f} ticks (${total_pnl_usd:+,.2f})")
        print(f"Avg Win: {sum(t.pnl_ticks for t in wins)/len(wins):.1f}t" if wins else "N/A")
        print(f"Avg Loss: {sum(t.pnl_ticks for t in losses)/len(losses):.1f}t" if losses else "N/A")
        print(f"Profit Factor: {profit_factor:.2f}")
        print()
        print("=" * 70)
        print()
        print("✅ Backtest terminé!")

if __name__ == "__main__":
    backtester = CleanConfigBacktester()
    backtester.run_backtest()
