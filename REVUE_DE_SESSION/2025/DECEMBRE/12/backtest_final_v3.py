#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    BACKTEST FINAL MIA IA SYSTEM V3
                    Avec SWEET_SPOT (6-7 trades/jour) + 21 niveaux MenthorQ
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF: Trouver le SWEET SPOT entre nombre de trades et win rate

📊 CONFIGS TESTÉES:
   1. CURRENT:       Config actuelle (over-engineered) → 0 trades
   2. SIMPLIFIED_V1: Validée (4 T/J, 60% WR, +$2,078)
   3. SWEET_SPOT:    🆕 Target 6-7 trades/jour
   4. SWEET_SPOT_V2: 🆕 Target 7-8 trades/jour
   5. BALANCED:      Target 8-10 trades/jour

⏰ SESSIONS (CORRIGÉES):
   - London:     08:00 - 11:00 (3h00)
   - US Morning: 15:50 - 17:00 (1h10) ← CORRIGÉ!
   - Power Hour: 20:00 - 21:25 (1h25)
   - TOTAL: 5h35/jour

📊 21 NIVEAUX MENTHORQ (NOMS CORRIGÉS):
   - GEX 1-5, gamma_wall_0dte, gamma_wall_level
   - HVL, HVL_0DTE
   - Blind Spots 1-3
   - Walls (call/put resistance/support + 0DTE)
   - VWAP + vwap_up1/dn1, vwap_up2/dn2

💰 1 CONTRAT MINI: ES=$12.50/tick, NQ=$5.00/tick

Auteur: Jackson Trading System + Claude
Date: 13 Décembre 2025
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import sys

# ═══════════════════════════════════════════════════════════════════════════════
#                           BARRE DE PROGRESSION
# ═══════════════════════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 40):
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r   {prefix} |{bar}| {percent*100:.1f}% {suffix}")
    sys.stdout.flush()
    if current >= total:
        print()

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION PATHS
# ═══════════════════════════════════════════════════════════════════════════════

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

NOVEMBER_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127", "20251130",
]

DECEMBER_DAYS = [
    "20251201", "20251202", "20251203", "20251204", "20251205",
    "20251206", "20251207", "20251208", "20251209", "20251210",
    "20251211", "20251212", "20251213",
]

DAYS_TO_TEST = NOVEMBER_DAYS + DECEMBER_DAYS

# ═══════════════════════════════════════════════════════════════════════════════
#                           SYMBOLES - 1 CONTRAT MINI
# ═══════════════════════════════════════════════════════════════════════════════

SYMBOLS = {
    "ES": {
        "chart_id": 3,
        "tick_size": 0.25,
        "tick_value": 12.50,
        "contracts": ["ESZ25", "ESH25"],
    },
    "NQ": {
        "chart_id": 9,
        "tick_size": 0.25,
        "tick_value": 5.00,
        "contracts": ["NQZ25", "NQH25"],
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#                    SESSIONS EXACTES (CORRIGÉES!)
# ═══════════════════════════════════════════════════════════════════════════════

TRADING_SESSIONS = {
    'london': {
        'start': (8, 0),    # 08:00 Paris
        'end': (11, 0),     # 11:00 Paris (3h)
        'enabled': True,
    },
    'us_morning': {
        'start': (15, 50),  # 15:50 Paris ← CORRIGÉ!
        'end': (17, 0),     # 17:00 Paris (1h10)
        'enabled': True,
    },
    'power_hour': {
        'start': (20, 0),   # 20:00 Paris
        'end': (21, 25),    # 21:25 Paris (1h25)
        'enabled': True,
    },
}

BLOCKED_PERIODS = {
    'overnight': ((0, 0), (8, 0)),
    'pre_market': ((11, 0), (15, 50)),
    'lunch': ((17, 0), (20, 0)),
    'hard_stop': ((21, 25), (24, 0)),
}

# ═══════════════════════════════════════════════════════════════════════════════
#              CONFIGURATIONS À COMPARER
# ═══════════════════════════════════════════════════════════════════════════════

CONFIGS = {
    # Configuration ACTUELLE (TROP STRICTE - 0 trades!)
    'CURRENT': {
        'name': '🔴 ACTUELLE (0 trades)',
        'min_confidence': {'ES': 1.00, 'NQ': 1.00},
        'max_distance': {'ES': 8, 'NQ': 10},
        'mia_threshold': 0.30,
        'cooldown_min': 30,
        'max_trades_per_day': 15,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'enable_pressure_filter': True,
        'pressure_threshold': {'ES': 0.20, 'NQ': 0.03},
        'enable_trend_filter': True,
        'enable_orderflow_filter': True,
        'orderflow_threshold': 200,
    },

    # SIMPLIFIÉE V1 - VALIDÉE: 97 trades, 60% WR, +$2,078
    'SIMPLIFIED_V1': {
        'name': '✅ SIMPLIFIED V1 (4 T/J)',
        'min_confidence': {'ES': 0.50, 'NQ': 0.50},
        'max_distance': {'ES': 15, 'NQ': 20},
        'mia_threshold': 0.25,
        'cooldown_min': 30,
        'max_trades_per_day': 12,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🆕 SWEET_SPOT - Target 6-7 trades/jour
    'SWEET_SPOT': {
        'name': '🎯 SWEET_SPOT (6-7 T/J)',
        'min_confidence': {'ES': 0.48, 'NQ': 0.48},
        'max_distance': {'ES': 16, 'NQ': 21},
        'mia_threshold': 0.23,
        'cooldown_min': 25,
        'max_trades_per_day': 15,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🆕 SWEET_SPOT_V2 - Target 7-8 trades/jour
    'SWEET_SPOT_V2': {
        'name': '🎯 SWEET_SPOT V2 (7-8 T/J)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 16,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 14,
        'trailing_activation': 7,
        'trailing_distance': 5,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # BALANCED - Target 8-10 trades/jour
    'BALANCED': {
        'name': '🏆 BALANCED (8-10 T/J)',
        'min_confidence': {'ES': 0.45, 'NQ': 0.45},
        'max_distance': {'ES': 18, 'NQ': 23},
        'mia_threshold': 0.20,
        'cooldown_min': 20,
        'max_trades_per_day': 18,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 13,
        'trailing_activation': 7,
        'trailing_distance': 4,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#              21 NIVEAUX MENTHORQ - NOMS CORRIGÉS!
# ═══════════════════════════════════════════════════════════════════════════════

MENTHORQ_LEVELS = [
    # ═══ GEX PRIORITAIRES (5) ═══
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',

    # ═══ GAMMA NIVEAUX CLÉS (2) ═══
    'gamma_wall_0dte',
    'gamma_wall_level',     # ← CORRIGÉ! (était gamma_flip)

    # ═══ HVL (2) ═══
    'hvl', 'hvl_0dte',

    # ═══ BLIND SPOTS (3) ═══
    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',

    # ═══ WALLS STANDARD (2) ═══
    'call_resistance', 'put_support',

    # ═══ WALLS 0DTE (2) ═══
    'call_resistance_0dte', 'put_support_0dte',

    # ═══ VWAP + BANDS (5) - NOMS CORRIGÉS! ═══
    'vwap',
    'vwap_up1', 'vwap_dn1',   # ← CORRIGÉ! (était vwap_sd_plus1/minus1)
    'vwap_up2', 'vwap_dn2',   # ← CORRIGÉ! (était vwap_sd_plus2/minus2)
]

# TOTAL: 21 niveaux avec les VRAIS noms des champs!

# ═══════════════════════════════════════════════════════════════════════════════
#                           DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeResult:
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    result: str
    pnl_usd: float
    tp1_hit: bool
    entry_time: int
    duration_sec: float
    mfe_ticks: float
    mae_ticks: float
    session: str
    day: str
    confidence: float
    distance: float
    level_name: str = ""

@dataclass
class BacktestResult:
    config_name: str
    trades: List[TradeResult]
    total_pnl: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trades_per_day: float
    signals_generated: int
    signals_rejected: int
    rejection_rate: float
    rejection_reasons: Dict[str, int]
    es_stats: Dict
    nq_stats: Dict
    by_session: Dict

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_month_folder(day: str) -> str:
    month = day[4:6]
    return "NOVEMBRE" if month == "11" else "DECEMBRE"


def find_data_file(day: str, symbol: str) -> Optional[Path]:
    config = SYMBOLS[symbol]
    month_folder = get_month_folder(day)
    for contract in config["contracts"]:
        path = DATA_BASE_PATH / month_folder / day / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{contract}_FUT_CME_{config['chart_id']}.jsonl"
        if path.exists():
            return path
    return None


def load_snapshots(file_path: Path) -> List[Dict]:
    snapshots = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        snapshots.append(json.loads(line))
                    except:
                        continue
    except:
        return []
    snapshots.sort(key=lambda x: x.get('t_ms', 0))
    return snapshots


def get_paris_time(t_ms: int) -> Tuple[int, int]:
    total_sec = t_ms // 1000
    total_min = total_sec // 60
    hour_utc = (total_min // 60) % 24
    minute = total_min % 60
    hour_paris = (hour_utc + 1) % 24
    return hour_paris, minute


def time_to_minutes(h: int, m: int) -> int:
    return h * 60 + m


def is_in_trading_session(hour: int, minute: int) -> Tuple[bool, str]:
    time_val = time_to_minutes(hour, minute)

    for name, (start, end) in BLOCKED_PERIODS.items():
        s = time_to_minutes(start[0], start[1])
        e = time_to_minutes(end[0], end[1])
        if s <= time_val < e:
            return False, f"BLOCKED_{name}"

    for name, session in TRADING_SESSIONS.items():
        if not session['enabled']:
            continue
        s = time_to_minutes(session['start'][0], session['start'][1])
        e = time_to_minutes(session['end'][0], session['end'][1])
        if s <= time_val < e:
            return True, name

    return False, "OFF_HOURS"


def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float, float]:
    mid = snapshot.get('mid', 0)
    tick_size = SYMBOLS[symbol]['tick_size']

    nearest_name = ""
    nearest_dist = float('inf')
    nearest_price = 0

    for level_name in MENTHORQ_LEVELS:
        price = snapshot.get(level_name)
        if price and price > 0:
            dist = abs(mid - price) / tick_size
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_name = level_name
                nearest_price = price

    return nearest_name, nearest_price, nearest_dist

# ═══════════════════════════════════════════════════════════════════════════════
#                           LOGIQUE DE SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal(snapshot: Dict, symbol: str, config: Dict, hour: int, minute: int) -> Tuple[bool, str, float, str, Dict]:
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "NO_PRICE", {}

    # 1. Vérifier session
    in_session, session_name = is_in_trading_session(hour, minute)
    if not in_session:
        return False, "", 0, session_name, {}

    # 2. Trouver niveau proche
    level_name, level_price, distance = find_nearest_level(snapshot, symbol)
    max_dist = config['max_distance'].get(symbol, 15)

    if distance > max_dist:
        return False, "", 0, f"DIST_{distance:.0f}t>{max_dist}t", {'distance': distance}

    # 3. Calculer confidence avec bonus pour niveaux importants
    menthorq_score = max(0, 1 - distance / 25)

    # Bonus pour niveaux prioritaires
    if level_name in ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap']:
        menthorq_score = min(1.0, menthorq_score * 1.25)
    elif level_name in ['vwap_up2', 'vwap_dn2', 'gamma_wall_0dte']:
        menthorq_score = min(1.0, menthorq_score * 1.15)

    # Layer 2: OrderFlow
    delta = snapshot.get('delta', 0) or 0
    orderflow_score = min(1.0, abs(delta) / 500) * 0.5 + 0.25

    # Layer 3: Context
    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    context_score = min(1.0, abs(mia_score) * 2)

    # Confidence totale
    confidence = menthorq_score * 0.50 + orderflow_score * 0.30 + context_score * 0.20

    min_conf = config['min_confidence'].get(symbol, 0.50)
    if confidence < min_conf:
        return False, "", confidence, f"CONF_{confidence:.2f}<{min_conf}", {'confidence': confidence}

    # 4. Direction
    threshold = config['mia_threshold']
    if mia_score > threshold:
        direction = "LONG"
    elif mia_score < -threshold:
        direction = "SHORT"
    else:
        return False, "", confidence, f"MIA_NEUTRAL", {'mia_score': mia_score}

    # 5. Filtres optionnels
    if config.get('enable_pressure_filter', False):
        buy_pct = snapshot.get('bidPct', 0.5) or 0.5
        pressure_threshold = config['pressure_threshold'].get(symbol, 0.0)
        if abs(buy_pct - 0.5) < pressure_threshold:
            return False, "", confidence, "PRESSURE_LOW", {}

    if config.get('enable_orderflow_filter', False):
        of_threshold = config.get('orderflow_threshold', 200)
        if direction == "SHORT" and delta > of_threshold:
            return False, "", confidence, "OF_CONTRA_SHORT", {}
        if direction == "LONG" and delta < -of_threshold:
            return False, "", confidence, "OF_CONTRA_LONG", {}

    if config.get('enable_trend_filter', False):
        hvl = snapshot.get('hvl', 0)
        position_range = snapshot.get('position_in_range', 50) or 50
        if hvl and mid:
            above_hvl = mid > hvl
            if direction == "LONG" and position_range > 75 and not above_hvl:
                return False, "", confidence, "TREND_CONTRA", {}
            if direction == "SHORT" and position_range < 25 and above_hvl:
                return False, "", confidence, "TREND_CONTRA", {}

    details = {
        'confidence': confidence,
        'distance': distance,
        'level': level_name,
        'mia_score': mia_score,
        'session': session_name,
    }

    return True, direction, confidence, "OK", details

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION DE TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], config: Dict,
                   session: str, day: str, confidence: float,
                   distance: float, level_name: str) -> TradeResult:

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    tp1_ticks = config['tp1_ticks']
    tp2_ticks = config['tp2_ticks']
    sl_ticks = config['sl_ticks']
    trail_act = config['trailing_activation']
    trail_dist = config['trailing_distance']

    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp1 = entry - tp1_ticks * tick_size
        tp2 = entry - tp2_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp1 = entry + tp1_ticks * tick_size
        tp2 = entry + tp2_ticks * tick_size

    tp1_hit = False
    trailing = None
    best_profit = 0
    pnl = 0
    result = "TIMEOUT"
    exit_price = entry
    exit_time = entry_time
    high_reached = entry
    low_reached = entry

    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:
            break

        high = snap.get('high') or snap.get('mid', entry)
        low = snap.get('low') or snap.get('mid', entry)

        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        if direction == "SHORT":
            profit_ticks = (entry - low) / tick_size

            if not tp1_hit and low <= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * 0.5

            if profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trail_act:
                    trailing = entry - (profit_ticks - trail_dist) * tick_size

            if high >= sl:
                pnl += -sl_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break

            if trailing and high >= trailing:
                trail_profit = (entry - trailing) / tick_size
                pnl += trail_profit * tick_value * (0.5 if tp1_hit else 1.0)
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break

            if low <= tp2:
                pnl += tp2_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break

        else:  # LONG
            profit_ticks = (high - entry) / tick_size

            if not tp1_hit and high >= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * 0.5

            if profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trail_act:
                    trailing = entry + (profit_ticks - trail_dist) * tick_size

            if low <= sl:
                pnl += -sl_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break

            if trailing and low <= trailing:
                trail_profit = (trailing - entry) / tick_size
                pnl += trail_profit * tick_value * (0.5 if tp1_hit else 1.0)
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break

            if high >= tp2:
                pnl += tp2_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break

    if direction == "LONG":
        mae = (entry - low_reached) / tick_size
        mfe = (high_reached - entry) / tick_size
    else:
        mae = (high_reached - entry) / tick_size
        mfe = (entry - low_reached) / tick_size

    return TradeResult(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        exit_price=exit_price,
        result=result,
        pnl_usd=pnl,
        tp1_hit=tp1_hit,
        entry_time=entry_time,
        duration_sec=(exit_time - entry_time) / 1000,
        mfe_ticks=mfe,
        mae_ticks=mae,
        session=session,
        day=day,
        confidence=confidence,
        distance=distance,
        level_name=level_name,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(config: Dict, all_data: Dict, show_progress: bool = False) -> BacktestResult:
    all_trades = []
    rejection_counts = defaultdict(int)
    signals_generated = 0
    signals_rejected = 0
    cooldown_ms = config['cooldown_min'] * 60 * 1000
    days_with_data = 0

    days_list = list(all_data.items())
    total_days = len(days_list)

    for day_idx, (day, day_data) in enumerate(days_list):
        if show_progress:
            progress_bar(day_idx + 1, total_days, "Jours", f"{day}")

        day_has_trades = False
        day_trade_count = 0

        for symbol in ["ES", "NQ"]:
            snapshots = day_data.get(symbol, [])
            if not snapshots:
                continue

            last_trade_time = 0

            for i, snap in enumerate(snapshots):
                if day_trade_count >= config['max_trades_per_day']:
                    break

                t_ms = snap.get('t_ms', 0)
                hour, minute = get_paris_time(t_ms)

                if t_ms - last_trade_time < cooldown_ms:
                    continue

                signals_generated += 1
                valid, direction, confidence, reason, details = generate_signal(
                    snap, symbol, config, hour, minute
                )

                if not valid:
                    signals_rejected += 1
                    rejection_counts[reason] += 1
                    continue

                future = snapshots[i+1:i+301]
                if len(future) < 10:
                    continue

                trade = simulate_trade(
                    snap, direction, symbol, future, config,
                    details.get('session', 'UNKNOWN'), day,
                    confidence, details.get('distance', 0),
                    details.get('level', '')
                )

                all_trades.append(trade)
                last_trade_time = t_ms
                day_trade_count += 1
                day_has_trades = True

        if day_has_trades:
            days_with_data += 1

    if not all_trades:
        return BacktestResult(
            config_name=config['name'],
            trades=[],
            total_pnl=0,
            win_rate=0,
            profit_factor=0,
            total_trades=0,
            avg_trades_per_day=0,
            signals_generated=signals_generated,
            signals_rejected=signals_rejected,
            rejection_rate=100 if signals_generated > 0 else 0,
            rejection_reasons=dict(rejection_counts),
            es_stats={},
            nq_stats={},
            by_session={},
        )

    total_pnl = sum(t.pnl_usd for t in all_trades)
    profitable = [t for t in all_trades if t.pnl_usd > 0]
    win_rate = len(profitable) / len(all_trades) * 100

    gross_profit = sum(t.pnl_usd for t in all_trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in all_trades if t.pnl_usd < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999

    es_trades = [t for t in all_trades if t.symbol == "ES"]
    nq_trades = [t for t in all_trades if t.symbol == "NQ"]

    es_stats = {
        'trades': len(es_trades),
        'pnl': sum(t.pnl_usd for t in es_trades),
        'wr': len([t for t in es_trades if t.pnl_usd > 0]) / len(es_trades) * 100 if es_trades else 0,
    }

    nq_stats = {
        'trades': len(nq_trades),
        'pnl': sum(t.pnl_usd for t in nq_trades),
        'wr': len([t for t in nq_trades if t.pnl_usd > 0]) / len(nq_trades) * 100 if nq_trades else 0,
    }

    by_session = {}
    for session in ['london', 'us_morning', 'power_hour']:
        sess_trades = [t for t in all_trades if t.session == session]
        if sess_trades:
            by_session[session] = {
                'trades': len(sess_trades),
                'pnl': sum(t.pnl_usd for t in sess_trades),
                'wr': len([t for t in sess_trades if t.pnl_usd > 0]) / len(sess_trades) * 100,
            }

    rejection_rate = signals_rejected / signals_generated * 100 if signals_generated > 0 else 0

    return BacktestResult(
        config_name=config['name'],
        trades=all_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        profit_factor=pf,
        total_trades=len(all_trades),
        avg_trades_per_day=len(all_trades) / max(1, days_with_data),
        signals_generated=signals_generated,
        signals_rejected=signals_rejected,
        rejection_rate=rejection_rate,
        rejection_reasons=dict(rejection_counts),
        es_stats=es_stats,
        nq_stats=nq_stats,
        by_session=by_session,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("          🎯 BACKTEST FINAL V3 - SWEET SPOT + 21 NIVEAUX MENTHORQ")
    print("=" * 100)
    print(f"""
📊 OBJECTIF: Trouver le SWEET SPOT entre nombre de trades et win rate

📋 CONFIGS TESTÉES:
   1. CURRENT:       Over-engineered (0 trades)
   2. SIMPLIFIED_V1: 4 T/J, 60% WR, +$2,078 ✅ VALIDÉE
   3. SWEET_SPOT:    🆕 Target 6-7 T/J
   4. SWEET_SPOT_V2: 🆕 Target 7-8 T/J
   5. BALANCED:      Target 8-10 T/J

⏰ SESSIONS:
   - London:     08:00 - 11:00 (3h00)
   - US Morning: 15:50 - 17:00 (1h10) ✅
   - Power Hour: 20:00 - 21:25 (1h25)
   - TOTAL: 5h35/jour

📊 21 NIVEAUX MENTHORQ (NOMS CORRIGÉS):
   GEX 1-5, gamma_wall_0dte, gamma_wall_level, HVL, HVL_0DTE,
   Blind Spots 1-3, Walls, Walls 0DTE, VWAP + vwap_up1/dn1/up2/dn2

💰 1 contrat MINI: ES=$12.50/tick, NQ=$5.00/tick
""")

    print("📂 Chargement des données...")
    all_data = {}
    days_loaded = 0
    total_snapshots = 0

    for i, day in enumerate(DAYS_TO_TEST):
        progress_bar(i + 1, len(DAYS_TO_TEST), "Chargement", f"{day}")
        all_data[day] = {}
        has_data = False

        for symbol in ["ES", "NQ"]:
            file_path = find_data_file(day, symbol)
            if file_path:
                snapshots = load_snapshots(file_path)
                all_data[day][symbol] = snapshots
                total_snapshots += len(snapshots)
                if snapshots:
                    has_data = True

        if has_data:
            days_loaded += 1

    print(f"\n   📊 {days_loaded} jours chargés | {total_snapshots:,} snapshots")

    if days_loaded == 0:
        print("\n❌ Aucune donnée!")
        return

    print("\n" + "=" * 100)
    print("                    🧪 EXÉCUTION DES BACKTESTS")
    print("=" * 100)

    results = {}
    for config_name, config in CONFIGS.items():
        print(f"\n▶ {config['name']}...")
        result = run_backtest(config, all_data, show_progress=True)
        results[config_name] = result
        print(f"   ✅ {result.total_trades} trades | WR: {result.win_rate:.1f}% | PnL: ${result.total_pnl:+,.0f}")

    # Résultats
    print("\n" + "=" * 100)
    print("                    📊 RÉSULTATS COMPARATIFS")
    print("=" * 100)

    print(f"\n{'Config':<30} {'Trades':>7} {'T/J':>6} {'WR%':>7} {'PnL':>12} {'PF':>6}")
    print("-" * 80)

    for name, r in results.items():
        marker = "🏆" if r.total_pnl == max(x.total_pnl for x in results.values() if x.total_trades > 0) and r.total_pnl > 0 else "  "
        print(f"{marker}{r.config_name:<28} {r.total_trades:>7} {r.avg_trades_per_day:>5.1f} {r.win_rate:>6.1f}% ${r.total_pnl:>+10,.0f} {r.profit_factor:>5.2f}")

    print("-" * 80)

    # Détails par config
    for name, r in results.items():
        if r.total_trades == 0:
            continue

        print(f"\n{'─'*60}")
        print(f"📊 {r.config_name}")
        print(f"{'─'*60}")
        print(f"   Trades: {r.total_trades} ({r.avg_trades_per_day:.1f}/jour)")
        print(f"   Win Rate: {r.win_rate:.1f}% | PF: {r.profit_factor:.2f}")
        print(f"   P&L: ${r.total_pnl:+,.2f}")

        if r.es_stats and r.nq_stats:
            print(f"\n   📈 Par Symbole:")
            print(f"      ES: {r.es_stats['trades']} trades | WR: {r.es_stats['wr']:.0f}% | ${r.es_stats['pnl']:+,.0f}")
            print(f"      NQ: {r.nq_stats['trades']} trades | WR: {r.nq_stats['wr']:.0f}% | ${r.nq_stats['pnl']:+,.0f}")

        if r.by_session:
            print(f"\n   ⏰ Par Session:")
            for sess, data in r.by_session.items():
                print(f"      {sess:<12}: {data['trades']:>3} T | WR: {data['wr']:.0f}% | ${data['pnl']:+,.0f}")

    # Trouver la meilleure config
    best = max([(name, r) for name, r in results.items() if r.total_trades > 0],
               key=lambda x: x[1].total_pnl, default=(None, None))

    if best[0]:
        name, r = best
        cfg = CONFIGS[name]

        print("\n" + "=" * 100)
        print("                    🏆 MEILLEURE CONFIG")
        print("=" * 100)
        print(f"""
┌────────────────────────────────────────────────────────────────────┐
│  {r.config_name:<64} │
├────────────────────────────────────────────────────────────────────┤
│  Trades/jour: {r.avg_trades_per_day:<5.1f}                                           │
│  Win Rate:    {r.win_rate:<5.1f}%                                          │
│  P&L Total:   ${r.total_pnl:<+10,.0f}                                      │
│  Profit Factor: {r.profit_factor:<5.2f}                                       │
├────────────────────────────────────────────────────────────────────┤
│  ES: {r.es_stats.get('trades', 0)} trades, WR {r.es_stats.get('wr', 0):.0f}%, ${r.es_stats.get('pnl', 0):+,.0f}                          │
│  NQ: {r.nq_stats.get('trades', 0)} trades, WR {r.nq_stats.get('wr', 0):.0f}%, ${r.nq_stats.get('pnl', 0):+,.0f}                          │
└────────────────────────────────────────────────────────────────────┘

🚀 PARAMÈTRES POUR PRODUCTION:
────────────────────────────────
MIN_CONFIDENCE = {{'ES': {cfg['min_confidence']['ES']}, 'NQ': {cfg['min_confidence']['NQ']}}}
MAX_DISTANCE   = {{'ES': {cfg['max_distance']['ES']}, 'NQ': {cfg['max_distance']['NQ']}}}
MIA_THRESHOLD  = {cfg['mia_threshold']}
COOLDOWN_MIN   = {cfg['cooldown_min']}
MAX_TRADES_DAY = {cfg['max_trades_per_day']}
TP1_TICKS      = {cfg['tp1_ticks']}
TP2_TICKS      = {cfg['tp2_ticks']}
SL_TICKS       = {cfg['sl_ticks']}
""")

    # CSV
    csv_path = Path("backtest_sweetspot_results.csv")
    with open(csv_path, 'w') as f:
        f.write("Config,Trades,TradesPerDay,WinRate,PnL,PF,ES_Trades,ES_WR,ES_PnL,NQ_Trades,NQ_WR,NQ_PnL\n")
        for name, r in results.items():
            f.write(f"{name},{r.total_trades},{r.avg_trades_per_day:.1f},{r.win_rate:.1f},{r.total_pnl:.2f},{r.profit_factor:.2f},")
            f.write(f"{r.es_stats.get('trades',0)},{r.es_stats.get('wr',0):.1f},{r.es_stats.get('pnl',0):.2f},")
            f.write(f"{r.nq_stats.get('trades',0)},{r.nq_stats.get('wr',0):.1f},{r.nq_stats.get('pnl',0):.2f}\n")

    print(f"\n✅ Résultats: {csv_path}")
    print("\n✅ BACKTEST TERMINÉ!")


if __name__ == "__main__":
    main()









