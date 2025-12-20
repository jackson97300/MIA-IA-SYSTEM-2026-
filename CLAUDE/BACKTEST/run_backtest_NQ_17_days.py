"""
🔬 BACKTEST MENTHORQ 3-LAYER STRATEGY - NQ - 17 JOURS AVEC FILTRE SESSION
===========================================================================
Backtest NQ avec filtrage horaire (Session Quality Monitor) + Bug Fixes 28 Nov

Créneaux autorisés (Paris time):
- London: 08:00-11:00
- US Morning: 15:50-17:00
- US Power Hour: 20:00-21:30

Bug fixes inclus:
- Exclusion key_level (28 Nov 23h22)
- Config distances unifiée: NQ 50t (28 Nov 23h22)
"""

import json
import sys
import io
import os
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import logging
import pytz

# ═══════════════════════════════════════════════════════════════
# CORRECTION STDOUT - S'assurer qu'il est ouvert
# ═══════════════════════════════════════════════════════════════
_original_stdout = sys.stdout
_original_stderr = sys.stderr

class SafeStdout:
    def __init__(self, original):
        self.original = original
        self.buffer = getattr(original, 'buffer', None)
        self.encoding = getattr(original, 'encoding', 'utf-8')
        self.errors = getattr(original, 'errors', 'replace')

    def write(self, text):
        try:
            if self.original and not self.original.closed:
                self.original.write(text)
                self.original.flush()
        except (ValueError, OSError):
            pass

    def flush(self):
        try:
            if self.original and not self.original.closed:
                self.original.flush()
        except (ValueError, OSError):
            pass

    def __getattr__(self, name):
        return getattr(self.original, name)

sys.stdout = SafeStdout(_original_stdout)
sys.stderr = SafeStdout(_original_stderr)

# Configurer logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

logging.getLogger('ml').setLevel(logging.ERROR)
logging.getLogger('strategies').setLevel(logging.ERROR)
logging.getLogger('core').setLevel(logging.ERROR)
logging.getLogger('config').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# Ajouter le path du projet pour les imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE")

DATES = [
    "20251105", "20251106", "20251107",
    "20251110", "20251111", "20251112", "20251113", "20251114",
    "20251117", "20251118", "20251119", "20251120", "20251121",
    "20251124", "20251125", "20251126", "20251127"
]

SYMBOL = "NQ"  # ✅ NQ pour ce backtest
CHART_ID = 9   # ✅ CHART_9 pour NQ

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

def is_trading_hour_allowed(t_ms: int) -> bool:
    """
    Vérifie si l'heure est dans un créneau autorisé (Session Quality Monitor).

    Args:
        t_ms: Timestamp en millisecondes

    Returns:
        bool: True si créneau autorisé
    """
    # Convertir timestamp en datetime UTC puis Paris
    dt_utc = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
    paris_tz = pytz.timezone('Europe/Paris')
    dt_paris = dt_utc.astimezone(paris_tz)

    hour = dt_paris.hour
    minute = dt_paris.minute

    # ═══════════════════════════════════════════════════════════
    # HARD BLOCKS (ABSOLU)
    # ═══════════════════════════════════════════════════════════

    # 1. POST-21:30 (CRITIQUE)
    if hour >= 22 or (hour == 21 and minute >= 30):
        return False

    # 2. OVERNIGHT (avant 08:00)
    if hour < 8:
        return False

    # 3. LUNCH US (17:00-19:30)
    if hour == 17 or hour == 18 or (hour == 19 and minute < 30):
        return False

    # 4. PRE-OPEN PAUSE (15:25-15:35)
    if hour == 15 and 25 <= minute < 35:
        return False

    # 5. OPR OBSERVE (15:35-15:50)
    if hour == 15 and 35 <= minute < 50:
        return False

    # ═══════════════════════════════════════════════════════════
    # SESSIONS VALIDES
    # ═══════════════════════════════════════════════════════════

    # London Session (08:00-11:00)
    if 8 <= hour < 11:
        return True

    # US Morning (15:50-17:00)
    if (hour == 15 and minute >= 50) or hour == 16:
        return True

    # US Afternoon/Power Hour (20:00-21:30)
    if hour == 20 or (hour == 21 and minute < 30):
        return True

    # Sinon, pas dans session valide
    return False

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

class MenthorQ3LayerBacktester:
    """Backtester complet pour MenthorQ 3-Layer Strategy avec filtre session"""

    def __init__(self, use_session_filter: bool = True):
        from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
        from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy

        print("🚀 Initialisation ML 3-Layer Integrated System...")
        try:
            self.ml_system = ML3LayerIntegratedSystem(
                symbols=[SYMBOL],
                use_ml_models=False
            )
            print("✅ ML 3-Layer System initialisé")
        except Exception as e:
            print(f"⚠️ Erreur initialisation ML System: {e}")
            import traceback
            traceback.print_exc()
            self.ml_system = None
            raise

        print("🎯 Initialisation MenthorQ 3-Layer Strategy...")
        try:
            self.strategy = MenthorQ3LayerStrategy(ml_3layer_system=self.ml_system)
            print("✅ Stratégie initialisée\n")
        except Exception as e:
            print(f"⚠️ Erreur initialisation Strategy: {e}")
            import traceback
            traceback.print_exc()
            self.strategy = None
            raise

        # Configuration
        self.tick_size = 0.25
        self.tick_value = 5.00  # ✅ NQ: $5/tick (vs ES: $12.50)
        self.use_session_filter = use_session_filter

        # Trades
        self.trades: List[BacktestTrade] = []
        self.open_trade: Optional[BacktestTrade] = None

        # Tracking
        self.highest_price = 0.0
        self.lowest_price = 999999.0
        self.be_triggered = False
        self.last_trade_time = 0
        self.cooldown_ms = 120000  # 2 minutes

        # Stats filtrage
        self.ticks_processed = 0
        self.ticks_filtered = 0
        self.signals_generated = 0
        self.signals_filtered = 0

        # Config TP/SL depuis stratégie
        self.sl_ticks = self.strategy.sl_optimal_ticks.get(SYMBOL, 22)
        self.tp1_ticks = self.strategy.tp_optimal_ticks.get(SYMBOL, 30)

        # Trailing/Breakeven depuis stratégie
        self.trail_activation = 10
        self.trail_distance = 5
        self.be_trigger = 7
        self.be_buffer = 2

    def _check_exit(self, tick: Dict) -> Optional[Tuple[str, float]]:
        """Vérifie si le trade doit être fermé"""
        if not self.open_trade:
            return None

        mid = tick.get('mid', 0)
        high = tick.get('high', mid)
        low = tick.get('low', mid)
        trade = self.open_trade

        # Update tracking
        self.highest_price = max(self.highest_price, high)
        self.lowest_price = min(self.lowest_price, low)

        # Check SL
        if trade.direction == 'LONG':
            if low <= trade.stop_loss:
                return ('SL', trade.stop_loss)
        else:
            if high >= trade.stop_loss:
                return ('SL', trade.stop_loss)

        # Check BE
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

        # Check Trail
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

        # Check TP1
        if trade.direction == 'LONG':
            if high >= trade.take_profit_1:
                return ('TP1', trade.take_profit_1)
        else:
            if low <= trade.take_profit_1:
                return ('TP1', trade.take_profit_1)

        return None

    def _close_trade(self, tick: Dict, reason: str, price: float):
        """Ferme le trade"""
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
        """Ouvre un nouveau trade"""
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

    def process_tick(self, tick: Dict):
        """Traite un tick"""
        t_ms = tick.get('t_ms', 0)
        self.ticks_processed += 1

        # ✅ FILTRE SESSION: Vérifier si créneau autorisé
        if self.use_session_filter:
            if not is_trading_hour_allowed(t_ms):
                self.ticks_filtered += 1
                return  # Skip ce tick si hors créneau

        # Si trade ouvert, check exit
        if self.open_trade:
            result = self._check_exit(tick)
            if result:
                self._close_trade(tick, result[0], result[1])
                return

        # Cooldown
        if t_ms - self.last_trade_time < self.cooldown_ms:
            return

        # Chercher signal
        if not self.open_trade:
            signal = self.strategy.analyze_from_ml_ready(tick, symbol=SYMBOL)
            if signal:
                self.signals_generated += 1
                # ✅ FILTRE SESSION: Vérifier aussi au moment du signal
                if self.use_session_filter:
                    if not is_trading_hour_allowed(t_ms):
                        self.signals_filtered += 1
                        return  # Rejeter signal hors créneau
                self._open_trade(tick, signal)

    def run_backtest(self, data_path: str):
        """Lance le backtest"""
        print(f"\n📂 Chargement: {data_path}")
        snapshots = load_snapshots(Path(data_path))
        print(f"   {len(snapshots):,} snapshots chargés")

        for i, tick in enumerate(snapshots):
            self.process_tick(tick)
            if (i + 1) % 5000 == 0:
                print(f"   {i+1:,}/{len(snapshots):,} ({(i+1)/len(snapshots)*100:.0f}%)")

        # Fermer trade ouvert
        if self.open_trade and snapshots:
            self._close_trade(snapshots[-1], 'EOD', snapshots[-1].get('mid', 0))

        print(f"✅ {len(self.trades)} trades générés")
        if self.use_session_filter:
            filter_rate = (self.ticks_filtered / self.ticks_processed * 100) if self.ticks_processed > 0 else 0
            print(f"📊 Filtrage: {self.ticks_filtered:,}/{self.ticks_processed:,} ticks filtrés ({filter_rate:.1f}%)")
            print(f"📊 Signaux: {self.signals_filtered}/{self.signals_generated} signaux filtrés")

    def calculate_stats(self) -> Dict:
        """Calcule les stats"""
        if not self.trades:
            return {}

        wins = [t for t in self.trades if t.is_win]
        losses = [t for t in self.trades if not t.is_win]

        stats = {
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_pnl_ticks': sum(t.pnl_ticks for t in self.trades),
            'total_pnl_usd': sum(t.pnl_usd for t in self.trades),
            'avg_win_ticks': sum(t.pnl_ticks for t in wins) / len(wins) if wins else 0,
            'avg_loss_ticks': sum(t.pnl_ticks for t in losses) / len(losses) if losses else 0,
        }

        gross_win = sum(t.pnl_ticks for t in wins)
        gross_loss = abs(sum(t.pnl_ticks for t in losses))
        stats['profit_factor'] = gross_win / gross_loss if gross_loss > 0 else 999

        return stats

def merge_results(all_results: list) -> Dict:
    """Fusionne les résultats"""
    merged = {
        'trades': [],
        'total_trades': 0,
        'wins': 0,
        'losses': 0,
        'win_rate': 0.0,
        'total_pnl_usd': 0.0,
        'total_pnl_ticks': 0.0,
        'profit_factor': 0.0
    }

    for result in all_results:
        merged['trades'].extend(result['trades'])

    if merged['trades']:
        wins = [t for t in merged['trades'] if t.is_win]
        losses = [t for t in merged['trades'] if not t.is_win]

        merged['total_trades'] = len(merged['trades'])
        merged['wins'] = len(wins)
        merged['losses'] = len(losses)
        merged['win_rate'] = len(wins) / len(merged['trades']) * 100
        merged['total_pnl_usd'] = sum(t.pnl_usd for t in merged['trades'])
        merged['total_pnl_ticks'] = sum(t.pnl_ticks for t in merged['trades'])

        gross_win = sum(t.pnl_usd for t in wins)
        gross_loss = abs(sum(t.pnl_usd for t in losses))
        merged['profit_factor'] = gross_win / gross_loss if gross_loss > 0 else 999

    return merged

def main():
    """Lance le backtest sur 17 jours avec et sans filtre session"""
    print("\n" + "="*70)
    print("BACKTEST MENTHORQ 3-LAYER STRATEGY - 17 JOURS")
    print("AVEC FILTRE SESSION (Session Quality Monitor)")
    print("="*70 + "\n")

    if not BASE_PATH.exists():
        print(f"❌ ERREUR: Le chemin {BASE_PATH} n'existe pas!")
        return

    # ═══════════════════════════════════════════════════════════
    # BACKTEST AVEC FILTRE SESSION
    # ═══════════════════════════════════════════════════════════

    print("\n" + "="*70)
    print("📊 BACKTEST AVEC FILTRE SESSION")
    print("="*70 + "\n")
    print("Créneaux autorisés (Paris time):")
    print("  • London: 08:00-11:00")
    print("  • US Morning: 15:50-17:00")
    print("  • US Power Hour: 20:00-21:30")
    print()

    all_results_filtered = []
    daily_results_filtered = {}
    backtester_filtered = MenthorQ3LayerBacktester(use_session_filter=True)

    for date in DATES:
        file_path = find_data_file(date)

        if not file_path:
            logger.warning(f"⚠️ Fichier non trouvé pour {date}")
            continue

        logger.info(f"📅 Processing {date}...")

        # Réinitialiser les trades pour ce jour
        backtester_filtered.trades = []
        backtester_filtered.open_trade = None
        backtester_filtered.last_trade_time = 0
        backtester_filtered.ticks_processed = 0
        backtester_filtered.ticks_filtered = 0
        backtester_filtered.signals_generated = 0
        backtester_filtered.signals_filtered = 0

        # Lancer backtest
        backtester_filtered.run_backtest(str(file_path))

        # Calculer stats
        stats = backtester_filtered.calculate_stats()
        stats['trades'] = backtester_filtered.trades.copy()
        stats['ticks_filtered'] = backtester_filtered.ticks_filtered
        stats['ticks_processed'] = backtester_filtered.ticks_processed
        stats['signals_filtered'] = backtester_filtered.signals_filtered
        stats['signals_generated'] = backtester_filtered.signals_generated

        all_results_filtered.append(stats)
        daily_results_filtered[date] = stats

        logger.info(f"   ✅ {stats['total_trades']} trades | WR: {stats['win_rate']:.1f}% | P&L: ${stats['total_pnl_usd']:.2f}")

    # Fusionner résultats
    logger.info(f"\n📊 Merging results from {len(all_results_filtered)} days...")
    merged_filtered = merge_results(all_results_filtered)

    # Afficher résultats
    print("\n" + "="*70)
    print("📊 RÉSULTATS GLOBAUX - 17 JOURS (AVEC FILTRE SESSION)")
    print("="*70 + "\n")
    print(f"Total Trades: {merged_filtered['total_trades']}")
    print(f"Wins: {merged_filtered['wins']} | Losses: {merged_filtered['losses']}")
    print(f"Win Rate: {merged_filtered['win_rate']:.1f}%")
    print(f"P&L: {merged_filtered['total_pnl_ticks']:+.1f} ticks (${merged_filtered['total_pnl_usd']:+.2f})")
    print(f"Avg Win: {merged_filtered.get('avg_win_ticks', 0):+.1f}t | Avg Loss: {merged_filtered.get('avg_loss_ticks', 0):.1f}t")
    print(f"Profit Factor: {merged_filtered['profit_factor']:.2f}")
    print("\n" + "="*70 + "\n")

    print(f"✅ Backtest terminé!")
    print(f"   Total trades: {merged_filtered['total_trades']}")

if __name__ == "__main__":
    main()
