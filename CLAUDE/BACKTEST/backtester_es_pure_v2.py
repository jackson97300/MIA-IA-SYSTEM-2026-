"""
🔬 BACKTESTER ES PURE MENTHORQ V2.2 - HYBRIDE
==============================================
Simulation complète avec SL/TP/Trail/BE

Version: 2.2 (HYBRIDE - Compromis optimal)
Date: 27 Novembre 2025

OPTIMISATIONS V2.2 (Hybride):
✅ SL: 18t → 16t (compromis)
✅ BE trigger: 8t → 7t (sauve MaxFav=7t)
✅ Trail: 12t → 10t (capture plus tôt)
✅ Near level: 10t → 8t (plus proche)
❌ hvl_magnet DÉSACTIVÉ (0% WR)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import sys
import os

# Ajouter le path pour importer la stratégie
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))  # Ajouter aussi le dossier BACKTEST

# Import de la stratégie
from es_pure_menthorq_v2 import (
    ESPureMenthorQV2,
    ES_CONFIG_V2,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION BACKTESTER
# ============================================================================

BACKTEST_CONFIG = {
    'initial_capital': 10000,
    'position_size': 1,
    'tick_size': 0.25,
    'tick_value': 12.50,
    'point_value': 50.00,

    # SL/TP/Trail (OPTIMISÉ V2.2 - HYBRIDE)
    'sl_base_ticks': 16,      # ⬇️ 18→16 (compromis)
    'sl_max_ticks': 20,       # Retour à 20
    'tp1_ticks': 12,
    'tp2_ticks': 20,
    'tp3_ticks': 30,

    # Trail settings (OPTIMISÉ V2.2)
    'trail_activation_ticks': 10,  # ⬇️ 12→10
    'trail_distance_ticks': 5,
    'breakeven_trigger_ticks': 7,  # ⬇️ 8→7 (sauve MaxFav=7t)
    'breakeven_buffer_ticks': 2,

    # Max trades
    'max_trades_per_day': 8,
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Position:
    """Position active"""
    entry_time: datetime
    entry_price: float
    direction: str  # 'LONG' or 'SHORT'
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    setup_type: str
    level_type: str
    level_price: float
    confidence: float

    # State tracking
    current_sl: float = 0.0
    breakeven_hit: bool = False
    trail_active: bool = False
    max_favorable: float = 0.0  # Max ticks in favor
    size: int = 1

    def __post_init__(self):
        self.current_sl = self.stop_loss


@dataclass
class Trade:
    """Trade complété"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str
    pnl_ticks: float
    pnl_usd: float
    setup_type: str
    level_type: str
    exit_reason: str  # 'SL', 'TP1', 'TP2', 'TP3', 'TRAIL', 'BE'
    max_favorable: float
    max_adverse: float
    duration_seconds: float
    session: str


@dataclass
class BacktestResult:
    """Résultat du backtest"""
    # Global metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L
    total_pnl_usd: float = 0.0
    total_pnl_ticks: float = 0.0
    avg_win_usd: float = 0.0
    avg_loss_usd: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_usd: float = 0.0

    # By setup
    by_setup: Dict[str, Dict] = field(default_factory=dict)

    # By level type
    by_level: Dict[str, Dict] = field(default_factory=dict)

    # By session
    by_session: Dict[str, Dict] = field(default_factory=dict)

    # By GEX rank
    by_gex: Dict[str, Dict] = field(default_factory=dict)

    # Exit reasons
    by_exit_reason: Dict[str, int] = field(default_factory=dict)

    # Trades list
    trades: List[Trade] = field(default_factory=list)


# ============================================================================
# BACKTESTER CLASS
# ============================================================================

class ESPureV2Backtester:
    """Backtester pour ES Pure MenthorQ V2"""

    def __init__(self, data_file: str, config: Dict = None):
        self.data_file = data_file
        self.config = config or BACKTEST_CONFIG

        # Stratégie
        self.strategy = ESPureMenthorQV2()

        # État
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.daily_trades = 0
        self.current_date = None

        # Stats
        self.signals_generated = 0
        self.signals_rejected = 0

        # Tracking
        self.equity_curve = []
        self.current_equity = self.config['initial_capital']
        self.peak_equity = self.config['initial_capital']
        self.max_drawdown = 0.0

    def load_data(self) -> List[Dict]:
        """Charge les données JSONL"""
        data = []
        with open(self.data_file, 'r') as f:
            for line in f:
                try:
                    row = json.loads(line.strip())
                    data.append(row)
                except:
                    continue
        logger.info(f"Loaded {len(data)} snapshots from {self.data_file}")
        return data

    def build_market_data(self, row: Dict) -> Dict:
        """Convertit un row JSONL en market_data pour la stratégie"""

        # Extraire VAH/VAL/VPOC du nested object
        vva = row.get('vva', {})

        # Construire les niveaux enrichis
        market_data = {
            # Prix
            'price': row.get('mid', 0),
            'bid': row.get('best_bid', 0),
            'ask': row.get('best_ask', 0),
            'high': row.get('high', 0),
            'low': row.get('low', 0),

            # Timestamp
            'timestamp': row.get('t_ms', 0),
            'session': row.get('session_id', 'Unknown'),

            # VWAP
            'vwap': row.get('vwap', 0),
            'vwap_up1': row.get('vwap_up1', 0),
            'vwap_dn1': row.get('vwap_dn1', 0),
            'vwap_up2': row.get('vwap_up2', 0),
            'vwap_dn2': row.get('vwap_dn2', 0),
            'pvwap': row.get('pvwap', 0),

            # Value Area
            'vah': vva.get('vah', 0),
            'val': vva.get('val', 0),
            'vpoc': vva.get('vpoc', 0),

            # GEX Levels (1-10)
            'gex_1': row.get('gex_1', 0),
            'gex_2': row.get('gex_2', 0),
            'gex_3': row.get('gex_3', 0),
            'gex_4': row.get('gex_4', 0),
            'gex_5': row.get('gex_5', 0),
            'gex_6': row.get('gex_6', 0),
            'gex_7': row.get('gex_7', 0),
            'gex_8': row.get('gex_8', 0),
            'gex_9': row.get('gex_9', 0),
            'gex_10': row.get('gex_10', 0),

            # Gamma Structure
            'call_resistance': row.get('call_resistance', 0),
            'put_support': row.get('put_support', 0),
            'hvl': row.get('hvl', 0),
            'gamma_wall_level': row.get('gamma_wall_level', 0),
            'gamma_side': row.get('gamma_side', 'neutral'),
            '1d_max': row.get('1d_max', 0),
            '1d_min': row.get('1d_min', 0),

            # Blind Spots
            'blind_spot_0': row.get('blind_spot_0', 0),
            'blind_spot_1': row.get('blind_spot_1', 0),
            'blind_spot_2': row.get('blind_spot_2', 0),
            'blind_spot_3': row.get('blind_spot_3', 0),
            'blind_spot_4': row.get('blind_spot_4', 0),
            'blind_spot_5': row.get('blind_spot_5', 0),
            'blind_spot_6': row.get('blind_spot_6', 0),
            'blind_spot_7': row.get('blind_spot_7', 0),
            'blind_spot_8': row.get('blind_spot_8', 0),

            # OrderFlow
            'delta': row.get('delta', 0),
            'deltaPct': row.get('deltaPct', 0),
            'askPct': row.get('askPct', 0.5),
            'bidPct': row.get('bidPct', 0.5),
            'cum_delta_day': row.get('cum_delta_day', 0),
            'mia_bullish_score': row.get('mia_bullish_score', 0),
            'pressure': row.get('pressure', 0),

            # DOM/Depth
            'depth_imbalance': row.get('depth_imbalance', 0),
            'ob_center': row.get('ob_center', 0),
            'level1_imbalance': row.get('level1_imbalance', 0),

            # Volatility
            'atr': row.get('atr', 0),
            'volatility_regime': row.get('volatility_regime', 1),
            'vix': row.get('vix', 15),

            # Volume
            'volume': row.get('volume', 0),
            'bidvol': row.get('bidvol', 0),
            'askvol': row.get('askvol', 0),

            # Structure
            'ibh': row.get('structure', {}).get('ibh', 0),
            'ibl': row.get('structure', {}).get('ibl', 0),
        }

        return market_data

    def build_orderflow(self, row: Dict) -> Dict:
        """Construit les données orderflow"""
        return {
            'delta': row.get('delta', 0),
            'deltaPct': row.get('deltaPct', 0),
            'askPct': row.get('askPct', 0.5),
            'bidPct': row.get('bidPct', 0.5),
            'depth_imbalance': row.get('depth_imbalance', 0),
            'mia_bullish_score': row.get('mia_bullish_score', 0),
            'cum_delta_day': row.get('cum_delta_day', 0),
            'pressure': row.get('pressure', 0),
            'ob_center': row.get('ob_center', 0),
            'level1_imbalance': row.get('level1_imbalance', 0),
        }

    def price_to_ticks(self, price_diff: float) -> float:
        """Convertit une différence de prix en ticks"""
        return price_diff / self.config['tick_size']

    def update_position(self, row: Dict) -> Optional[Trade]:
        """Met à jour une position ouverte, retourne Trade si fermée"""
        if not self.position:
            return None

        price = row.get('mid', 0)
        high = row.get('high', 0)
        low = row.get('low', 0)
        ts = datetime.fromtimestamp(row['t_ms'] / 1000)

        pos = self.position
        tick_size = self.config['tick_size']

        # Calculer le mouvement en ticks
        if pos.direction == 'LONG':
            current_ticks = self.price_to_ticks(price - pos.entry_price)
            max_favorable = self.price_to_ticks(high - pos.entry_price)
            max_adverse = self.price_to_ticks(pos.entry_price - low)
        else:  # SHORT
            current_ticks = self.price_to_ticks(pos.entry_price - price)
            max_favorable = self.price_to_ticks(pos.entry_price - low)
            max_adverse = self.price_to_ticks(high - pos.entry_price)

        # Update max favorable
        pos.max_favorable = max(pos.max_favorable, max_favorable)

        # --- CHECK EXIT CONDITIONS ---
        exit_reason = None
        exit_price = None

        # 1. Stop Loss hit?
        if pos.direction == 'LONG':
            if low <= pos.current_sl:
                exit_reason = 'SL'
                exit_price = pos.current_sl
        else:
            if high >= pos.current_sl:
                exit_reason = 'SL'
                exit_price = pos.current_sl

        # 2. Take Profit 1 hit? (on utilise TP1 pour simplicité)
        if not exit_reason:
            if pos.direction == 'LONG':
                if high >= pos.take_profit_1:
                    exit_reason = 'TP1'
                    exit_price = pos.take_profit_1
            else:
                if low <= pos.take_profit_1:
                    exit_reason = 'TP1'
                    exit_price = pos.take_profit_1

        # 3. Breakeven check
        if not exit_reason and not pos.breakeven_hit:
            be_trigger = self.config['breakeven_trigger_ticks']
            if max_favorable >= be_trigger:
                be_buffer = self.config['breakeven_buffer_ticks']
                if pos.direction == 'LONG':
                    pos.current_sl = pos.entry_price + (be_buffer * tick_size)
                else:
                    pos.current_sl = pos.entry_price - (be_buffer * tick_size)
                pos.breakeven_hit = True
                logger.debug(f"BE activated @ {pos.current_sl:.2f}")

        # 4. Trail check
        if not exit_reason and pos.breakeven_hit:
            trail_act = self.config['trail_activation_ticks']
            trail_dist = self.config['trail_distance_ticks']

            if max_favorable >= trail_act:
                pos.trail_active = True
                # Update trailing stop
                if pos.direction == 'LONG':
                    new_trail = high - (trail_dist * tick_size)
                    pos.current_sl = max(pos.current_sl, new_trail)
                else:
                    new_trail = low + (trail_dist * tick_size)
                    pos.current_sl = min(pos.current_sl, new_trail)

        # --- CLOSE POSITION IF EXIT ---
        if exit_reason:
            # Calculer P&L
            if pos.direction == 'LONG':
                pnl_pts = exit_price - pos.entry_price
            else:
                pnl_pts = pos.entry_price - exit_price

            pnl_ticks = self.price_to_ticks(pnl_pts)
            pnl_usd = pnl_ticks * self.config['tick_value']

            # Créer le trade
            trade = Trade(
                entry_time=pos.entry_time,
                exit_time=ts,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                direction=pos.direction,
                pnl_ticks=pnl_ticks,
                pnl_usd=pnl_usd,
                setup_type=pos.setup_type,
                level_type=pos.level_type,
                exit_reason=exit_reason,
                max_favorable=pos.max_favorable,
                max_adverse=max_adverse,
                duration_seconds=(ts - pos.entry_time).total_seconds(),
                session=row.get('session_id', 'Unknown')
            )

            # Reset position
            self.position = None

            # Update equity
            self.current_equity += pnl_usd
            self.equity_curve.append({
                'time': ts,
                'equity': self.current_equity,
                'trade_pnl': pnl_usd
            })

            # Update drawdown
            if self.current_equity > self.peak_equity:
                self.peak_equity = self.current_equity
            dd = self.peak_equity - self.current_equity
            self.max_drawdown = max(self.max_drawdown, dd)

            return trade

        return None

    def open_position(self, signal: Dict, row: Dict) -> bool:
        """Ouvre une nouvelle position"""
        if self.position:
            return False

        ts = datetime.fromtimestamp(row['t_ms'] / 1000)
        price = row.get('mid', 0)
        tick_size = self.config['tick_size']

        # Direction du signal
        direction = signal.get('action', 'LONG')

        # Utiliser SL/TP du signal si disponible
        sl = signal.get('stop_loss')
        tp1 = signal.get('take_profit_1')
        tp2 = signal.get('take_profit_2')
        tp3 = signal.get('take_profit_3')

        # Sinon calculer
        if not sl:
            if direction == 'LONG':
                sl = price - (self.config['sl_base_ticks'] * tick_size)
            else:
                sl = price + (self.config['sl_base_ticks'] * tick_size)

        if not tp1:
            if direction == 'LONG':
                tp1 = price + (self.config['tp1_ticks'] * tick_size)
                tp2 = price + (self.config['tp2_ticks'] * tick_size)
                tp3 = price + (self.config['tp3_ticks'] * tick_size)
            else:
                tp1 = price - (self.config['tp1_ticks'] * tick_size)
                tp2 = price - (self.config['tp2_ticks'] * tick_size)
                tp3 = price - (self.config['tp3_ticks'] * tick_size)

        # Extraire level_type du key_level
        key_level = signal.get('key_level', '')
        level_type = 'UNKNOWN'
        level_price = 0.0

        # Parser key_level (format: "ESLevel(type=X, price=Y, ...)")
        if 'GEX_' in key_level:
            # Extraire GEX_X
            import re
            match = re.search(r'(GEX_\d+)', key_level)
            if match:
                level_type = match.group(1)
        elif 'CALL_RESISTANCE' in key_level:
            level_type = 'CALL_RESISTANCE'
        elif 'PUT_SUPPORT' in key_level:
            level_type = 'PUT_SUPPORT'
        elif 'HVL' in key_level:
            level_type = 'HVL'
        elif 'VWAP' in key_level:
            level_type = 'VWAP'
        elif 'GAMMA_WALL' in key_level:
            level_type = 'GAMMA_WALL'

        self.position = Position(
            entry_time=ts,
            entry_price=price,
            direction=direction,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2 or tp1 + 8*tick_size,
            take_profit_3=tp3 or tp1 + 18*tick_size,
            setup_type=signal.get('setup_type', 'UNKNOWN'),
            level_type=level_type,
            level_price=level_price,
            confidence=signal.get('confidence', 0.5)
        )

        self.daily_trades += 1
        logger.debug(f"Opened {direction} @ {price:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f}")

        return True

    def run(self) -> BacktestResult:
        """Lance le backtest complet"""

        # Charger données
        data = self.load_data()

        if not data:
            logger.error("No data loaded!")
            return BacktestResult()

        logger.info(f"Starting backtest with {len(data)} snapshots...")

        # Tracking
        last_signal_time = 0
        min_signal_interval_ms = 60000  # 1 minute entre signaux

        for i, row in enumerate(data):
            ts_ms = row.get('t_ms', 0)
            ts = datetime.fromtimestamp(ts_ms / 1000)

            # Nouveau jour?
            date = ts.date()
            if date != self.current_date:
                self.current_date = date
                self.daily_trades = 0
                logger.info(f"New day: {date}")

            # 1. Update position si ouverte
            if self.position:
                trade = self.update_position(row)
                if trade:
                    self.trades.append(trade)
                    logger.info(f"Trade closed: {trade.direction} {trade.exit_reason} | P&L: ${trade.pnl_usd:.2f}")

            # 2. Chercher nouveau signal si pas de position
            if not self.position and self.daily_trades < self.config['max_trades_per_day']:
                # Rate limit signaux
                if ts_ms - last_signal_time < min_signal_interval_ms:
                    continue

                # Construire market_data et orderflow
                market_data = self.build_market_data(row)

                # Générer signal (la stratégie prend le tick complet)
                try:
                    signal = self.strategy.generate_signal(row)  # Utiliser row directement

                    if signal:
                        self.signals_generated += 1
                        logger.info(f"🎯 SIGNAL: {signal.get('action')} {signal.get('setup_type')} @ {row['mid']:.2f}")

                        # Ouvrir position
                        if self.open_position(signal, row):
                            last_signal_time = ts_ms
                            logger.info(f"✅ Position opened @ {row['mid']:.2f}")

                except Exception as e:
                    if 'Signal error' not in str(e):
                        logger.warning(f"Signal error: {e}")
                    continue

            # Progress log
            if i % 2000 == 0:
                pct = (i / len(data)) * 100
                logger.info(f"Progress: {pct:.1f}% | Trades: {len(self.trades)} | Signals: {self.signals_generated}")

        # Compiler résultats
        return self.compile_results()

    def compile_results(self) -> BacktestResult:
        """Compile les statistiques finales"""

        result = BacktestResult()
        result.trades = self.trades
        result.total_trades = len(self.trades)

        if not self.trades:
            return result

        # Win/Loss
        winners = [t for t in self.trades if t.pnl_usd > 0]
        losers = [t for t in self.trades if t.pnl_usd <= 0]

        result.winning_trades = len(winners)
        result.losing_trades = len(losers)
        result.win_rate = len(winners) / len(self.trades) * 100 if self.trades else 0

        # P&L
        result.total_pnl_usd = sum(t.pnl_usd for t in self.trades)
        result.total_pnl_ticks = sum(t.pnl_ticks for t in self.trades)
        result.avg_win_usd = sum(t.pnl_usd for t in winners) / len(winners) if winners else 0
        result.avg_loss_usd = sum(t.pnl_usd for t in losers) / len(losers) if losers else 0

        # Profit Factor
        gross_profit = sum(t.pnl_usd for t in winners)
        gross_loss = abs(sum(t.pnl_usd for t in losers))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Max Drawdown
        result.max_drawdown_usd = self.max_drawdown

        # By Setup
        for setup in set(t.setup_type for t in self.trades):
            setup_trades = [t for t in self.trades if t.setup_type == setup]
            setup_winners = [t for t in setup_trades if t.pnl_usd > 0]
            result.by_setup[setup] = {
                'trades': len(setup_trades),
                'wins': len(setup_winners),
                'win_rate': len(setup_winners) / len(setup_trades) * 100,
                'pnl_usd': sum(t.pnl_usd for t in setup_trades),
                'avg_pnl': sum(t.pnl_usd for t in setup_trades) / len(setup_trades)
            }

        # By Level Type
        for level in set(t.level_type for t in self.trades):
            level_trades = [t for t in self.trades if t.level_type == level]
            level_winners = [t for t in level_trades if t.pnl_usd > 0]
            result.by_level[level] = {
                'trades': len(level_trades),
                'wins': len(level_winners),
                'win_rate': len(level_winners) / len(level_trades) * 100,
                'pnl_usd': sum(t.pnl_usd for t in level_trades)
            }

        # By Session
        for session in set(t.session for t in self.trades):
            sess_trades = [t for t in self.trades if t.session == session]
            sess_winners = [t for t in sess_trades if t.pnl_usd > 0]
            result.by_session[session] = {
                'trades': len(sess_trades),
                'wins': len(sess_winners),
                'win_rate': len(sess_winners) / len(sess_trades) * 100,
                'pnl_usd': sum(t.pnl_usd for t in sess_trades)
            }

        # By GEX rank (extract from level_type)
        for trade in self.trades:
            if trade.level_type.startswith('GEX_'):
                gex = trade.level_type
                if gex not in result.by_gex:
                    result.by_gex[gex] = {'trades': 0, 'wins': 0, 'pnl_usd': 0}
                result.by_gex[gex]['trades'] += 1
                if trade.pnl_usd > 0:
                    result.by_gex[gex]['wins'] += 1
                result.by_gex[gex]['pnl_usd'] += trade.pnl_usd

        # Calculate win rates for GEX
        for gex in result.by_gex:
            g = result.by_gex[gex]
            g['win_rate'] = g['wins'] / g['trades'] * 100 if g['trades'] > 0 else 0

        # By Exit Reason
        for reason in set(t.exit_reason for t in self.trades):
            result.by_exit_reason[reason] = len([t for t in self.trades if t.exit_reason == reason])

        return result


def print_results(result: BacktestResult):
    """Affiche les résultats du backtest"""

    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS - ES PURE MENTHORQ V2")
    print("="*70)

    print(f"\n🎯 GLOBAL METRICS:")
    print(f"   Total Trades:    {result.total_trades}")
    print(f"   Winning:         {result.winning_trades}")
    print(f"   Losing:          {result.losing_trades}")
    print(f"   Win Rate:        {result.win_rate:.1f}%")
    print(f"   Total P&L:       ${result.total_pnl_usd:.2f}")
    print(f"   Total Ticks:     {result.total_pnl_ticks:.1f}")
    print(f"   Avg Win:         ${result.avg_win_usd:.2f}")
    print(f"   Avg Loss:        ${result.avg_loss_usd:.2f}")
    print(f"   Profit Factor:   {result.profit_factor:.2f}")
    print(f"   Max Drawdown:    ${result.max_drawdown_usd:.2f}")

    if result.by_setup:
        print(f"\n📈 BY SETUP:")
        for setup, stats in sorted(result.by_setup.items(), key=lambda x: -x[1]['trades']):
            print(f"   {setup:25} | {stats['trades']:3} trades | {stats['win_rate']:5.1f}% WR | ${stats['pnl_usd']:8.2f}")

    if result.by_level:
        print(f"\n🎯 BY LEVEL TYPE:")
        for level, stats in sorted(result.by_level.items(), key=lambda x: -x[1]['trades']):
            print(f"   {level:25} | {stats['trades']:3} trades | {stats['win_rate']:5.1f}% WR | ${stats['pnl_usd']:8.2f}")

    if result.by_gex:
        print(f"\n🔢 BY GEX RANK:")
        for gex in sorted(result.by_gex.keys()):
            stats = result.by_gex[gex]
            print(f"   {gex:10} | {stats['trades']:3} trades | {stats['win_rate']:5.1f}% WR | ${stats['pnl_usd']:8.2f}")

    if result.by_session:
        print(f"\n⏰ BY SESSION:")
        for session, stats in sorted(result.by_session.items()):
            print(f"   {session:15} | {stats['trades']:3} trades | {stats['win_rate']:5.1f}% WR | ${stats['pnl_usd']:8.2f}")

    if result.by_exit_reason:
        print(f"\n🚪 EXIT REASONS:")
        for reason, count in sorted(result.by_exit_reason.items(), key=lambda x: -x[1]):
            print(f"   {reason:10} | {count:3} trades")

    # Trade list
    if result.trades:
        print(f"\n📝 LAST 10 TRADES:")
        for trade in result.trades[-10:]:
            emoji = "✅" if trade.pnl_usd > 0 else "❌"
            print(f"   {emoji} {trade.direction:5} {trade.setup_type:25} | {trade.exit_reason:5} | ${trade.pnl_usd:7.2f} | MaxFav: {trade.max_favorable:.0f}t")

    print("\n" + "="*70)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Backtest ES Pure MenthorQ V2')
    parser.add_argument('--data', default='/home/claude/ml_ESZ25_FUT_CME_3.jsonl',
                        help='Path to JSONL data file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run backtest
    backtester = ESPureV2Backtester(args.data)
    result = backtester.run()

    # Print results
    print_results(result)
