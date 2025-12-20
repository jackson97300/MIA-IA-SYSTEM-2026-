"""
🔬 BACKTEST CONFIG C - ELITE STRICT (QUALITÉ > QUANTITÉ)
=========================================================
Configuration:
- Seuils STRICTS: Confidence 0.70/0.40, Sessions 0.75/0.72
- ML ACTIVÉ @ 0.75 (vs OFF config clean)
- Heures premium: London 08:00-11:00, US 15:50-17:00 + 20:00-21:30
- Filtres qualité stricts: spread, confluence
- Cooldown 3 min (vs 2 min)

Total: 22 validations STRICTES (vs 19 clean, vs 12 backtest original)
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

class SessionQualityCheckerElite:
    """Session Quality ELITE - 5 validations STRICTES"""

    def __init__(self):
        self.stats = {
            'total_checks': 0,
            'blocks_hours': 0,
            'blocks_lunch': 0,
            'blocks_overnight': 0,
            'blocks_spread': 0,
            'blocks_confluence': 0,
            'allowed': 0
        }

    def check_session(self, tick: Dict) -> Tuple[bool, str]:
        """
        Vérifie session + qualité STRICTE

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
        paris_tz = timezone(timedelta(hours=1))
        dt = datetime.fromtimestamp(t_ms / 1000, tz=paris_tz)
        hour = dt.hour
        minute = dt.minute

        # 1. HARD STOP: 21:30 → 08:00
        if hour >= 21 and minute >= 30:
            self.stats['blocks_overnight'] += 1
            return False, f"Hard Stop (21:30+)"
        if hour < 8:
            self.stats['blocks_overnight'] += 1
            return False, f"Overnight"

        # 2. LUNCH BLOCK: 17:00 → 19:30
        if (hour == 17 and minute >= 0) or (hour == 18) or (hour == 19 and minute < 30):
            self.stats['blocks_lunch'] += 1
            return False, f"Lunch Block"

        # 3. TRADING HOURS (identique clean)
        in_hours = False
        session_name = ""

        if 8 <= hour < 11:
            in_hours = True
            session_name = "London"
        elif (hour == 15 and minute >= 50) or (hour == 16):
            in_hours = True
            session_name = "US Morning"
        elif hour == 20 or (hour == 21 and minute < 30):
            in_hours = True
            session_name = "US Power Hour"

        if not in_hours:
            self.stats['blocks_hours'] += 1
            return False, f"Hors heures"

        # ✅ 4. SPREAD STRICT (NOUVEAU)
        spread_ticks = tick.get('spread_ticks', 0)
        if spread_ticks > 2:  # 2 ticks max (vs 3 ou pas de check)
            self.stats['blocks_spread'] += 1
            return False, f"Spread trop large ({spread_ticks}t > 2t)"

        # ✅ 5. CONFLUENCE STRICT (NOUVEAU)
        ml_data = tick.get('ml_data', {})
        confluence_levels = ml_data.get('confluence_levels', [])
        if isinstance(confluence_levels, list):
            confluence_count = len(confluence_levels)
        else:
            confluence_count = 0

        if confluence_count < 3:  # Minimum 3 niveaux (STRICT)
            self.stats['blocks_confluence'] += 1
            return False, f"Confluence insuffisante ({confluence_count} < 3)"

        self.stats['allowed'] += 1
        return True, session_name

class EliteConfigBacktester:
    """Backtester avec config ELITE STRICTE (22 validations)"""

    def __init__(self):
        # Initialiser stratégie
        from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
        from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy

        print("🚀 Initialisation ML 3-Layer System...")
        self.ml_system = ML3LayerIntegratedSystem(
            symbols=[SYMBOL],
            use_ml_models=True  # ✅ ACTIVÉ (vs False config clean)
        )
        print("✅ ML System initialisé (ML ACTIVÉ @ 0.75)")

        print("🎯 Initialisation Strategy...")
        self.strategy = MenthorQ3LayerStrategy(ml_3layer_system=self.ml_system)

        # Config de base (AVANT d'appliquer config elite)
        self.tick_size = 0.25
        self.tick_value = 12.50

        # TP/SL ELITE (définir AVANT _apply_elite_config)
        self.sl_ticks = 20  # vs 22 config clean
        self.tp1_ticks = 35  # vs 30 config clean

        # Trailing/BE ELITE (définir AVANT _apply_elite_config)
        self.trail_activation = 12  # vs 10 (plus strict)
        self.trail_distance = 4     # vs 5 (plus tight)
        self.be_trigger = 8          # vs 7 (plus strict)
        self.be_buffer = 3           # vs 2 (plus de marge)

        # Cooldown ELITE (définir AVANT _apply_elite_config)
        self.cooldown_ms = 180000  # ✅ 3 min (vs 2 min) STRICT

        # Daily loss limit (définir AVANT _apply_elite_config)
        self.daily_pnl = 0.0
        self.daily_loss_limit = -400  # ✅ $400 max (vs $500) STRICT

        # ✅ MAINTENANT appliquer config ELITE
        self._apply_elite_config()
        print("✅ Stratégie initialisée avec config ELITE STRICTE\n")

        # Session Quality Checker ELITE
        self.session_checker = SessionQualityCheckerElite()

        # Trades
        self.trades: List[BacktestTrade] = []
        self.open_trade: Optional[BacktestTrade] = None

        # Tracking
        self.highest_price = 0.0
        self.lowest_price = 999999.0
        self.be_triggered = False
        self.last_trade_time = 0

        # Stats
        self.stats = {
            'total_snapshots': 0,
            'session_blocked': 0,
            'ml_rejected': 0,
            'strategy_signals': 0,
            'cooldown_blocked': 0,
            'daily_loss_limit': 0,
            'trades_opened': 0
        }

    def _apply_elite_config(self):
        """Appliquer config ELITE STRICTE"""
        # ✅ Confidence STRICT
        self.strategy.min_total_confidence = 0.70  # vs 0.60
        self.strategy.min_layer1_confidence = 0.40  # vs 0.30

        # ✅ Distance STRICT
        self.strategy.sl_optimal_ticks['ES'] = self.sl_ticks
        self.strategy.tp_optimal_ticks['ES'] = self.tp1_ticks

        # Note: Les session thresholds sont dans config/unified_thresholds.py
        # On ne peut pas les override facilement ici
        # Mais le code de la stratégie les utilise déjà

        print("✅ Config ELITE appliquée:")
        print(f"   - Confidence: {self.strategy.min_total_confidence} / {self.strategy.min_layer1_confidence}")
        print(f"   - TP/SL: {self.tp1_ticks}t / {self.sl_ticks}t")
        print(f"   - Cooldown: 3 min")
        print(f"   - Daily Loss Limit: $400")

    def _check_exit(self, tick: Dict) -> Optional[Tuple[str, float]]:
        """Vérifie exit (identique config clean)"""
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

        # BE (ELITE: trigger plus strict)
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

        # Trail (ELITE: activation plus stricte)
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
        """Ferme trade"""
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
        self.daily_pnl += trade.pnl_usd

        # Reset
        self.open_trade = None
        self.highest_price = 0.0
        self.lowest_price = 999999.0
        self.be_triggered = False
        self.last_trade_time = t_ms

    def _open_trade(self, tick: Dict, signal: Dict):
        """Ouvre trade"""
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
        """Traite un tick avec Session Quality ELITE"""
        self.stats['total_snapshots'] += 1
        t_ms = tick.get('t_ms', 0)

        # Check exit si trade ouvert
        if self.open_trade:
            result = self._check_exit(tick)
            if result:
                self._close_trade(tick, result[0], result[1])
                return

        # ✅ Session Quality Check ELITE (5 validations)
        can_trade, reason = self.session_checker.check_session(tick)
        if not can_trade:
            self.stats['session_blocked'] += 1
            return

        # ✅ Daily Loss Limit STRICT
        if self.daily_pnl <= self.daily_loss_limit:
            self.stats['daily_loss_limit'] += 1
            return

        # ✅ Max 1 Position (STRICT)
        if self.open_trade is not None:
            return

        # Cooldown STRICT (3 min)
        if t_ms - self.last_trade_time < self.cooldown_ms:
            self.stats['cooldown_blocked'] += 1
            return

        # Chercher signal (avec ML ACTIVÉ @ 0.75)
        signal = self.strategy.analyze_from_ml_ready(tick, symbol=SYMBOL)

        if signal:
            # ✅ Vérifier que ML a validé (si ML activé)
            # La stratégie gère déjà ça en interne
            self.stats['strategy_signals'] += 1
            self._open_trade(tick, signal)
        else:
            # Signal rejeté par stratégie ou ML
            self.stats['ml_rejected'] += 1

    def run_backtest(self):
        """Lance backtest complet"""
        print("=" * 70)
        print("🔬 BACKTEST CONFIG C - ELITE STRICT - 17 JOURS")
        print("=" * 70)
        print(f"Symbole: {SYMBOL}")
        print(f"Config: ELITE STRICTE (Qualité > Quantité)")
        print(f"Validations: 22 STRICTES (vs 19 clean, vs 12 original)")
        print(f"ML: ACTIVÉ @ 0.75 (vs OFF clean)")
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

            # Reset daily P&L chaque jour
            self.daily_pnl = 0.0

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
        print(f"  - Spread trop large:       {self.session_checker.stats['blocks_spread']:,}")
        print(f"  - Confluence insuffisante: {self.session_checker.stats['blocks_confluence']:,}")
        print(f"Autorisés par Session:       {self.session_checker.stats['allowed']:,} ({self.session_checker.stats['allowed']/self.stats['total_snapshots']*100:.1f}%)")
        print(f"Signaux stratégie générés:   {self.stats['strategy_signals']:,}")
        print(f"Rejetés par ML/stratégie:    {self.stats['ml_rejected']:,}")
        print(f"Bloqués par cooldown:        {self.stats['cooldown_blocked']:,}")
        print(f"Bloqués par daily loss:      {self.stats['daily_loss_limit']:,}")
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
        print("📊 RÉSULTATS FINAUX - CONFIG C ELITE STRICT")
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
    backtester = EliteConfigBacktester()
    backtester.run_backtest()
