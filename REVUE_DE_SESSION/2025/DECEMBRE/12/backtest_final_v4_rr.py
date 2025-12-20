#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    BACKTEST FINAL MIA IA SYSTEM V4
                    Focus sur RISK:REWARD optimal
═══════════════════════════════════════════════════════════════════════════════

🎯 PROBLÈME V3: WR 63% mais P&L négatif! 
   → Le R:R était mauvais (TP1=10, TP2=15, SL=15 = 0.83:1)

📊 SOLUTION V4: Tester différents R:R
   - TIGHT_SL:    SL=8, TP=12  → R:R 1.5:1
   - WIDE_TP:     SL=10, TP=20 → R:R 2:1
   - NO_PARTIAL:  SL=10, TP=15, pas de TP1 → R:R 1.5:1
   - SCALPER:     SL=6, TP=10  → R:R 1.67:1

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
#                    SESSIONS (CORRIGÉES)
# ═══════════════════════════════════════════════════════════════════════════════

TRADING_SESSIONS = {
    'london': {
        'start': (8, 0),
        'end': (11, 0),
        'enabled': True,
    },
    'us_morning': {
        'start': (15, 50),
        'end': (17, 0),
        'enabled': True,
    },
    'power_hour': {
        'start': (20, 0),
        'end': (21, 25),
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
#              CONFIGURATIONS R:R À TESTER
# ═══════════════════════════════════════════════════════════════════════════════

CONFIGS = {
    # V3 Original (pour comparaison) - R:R = 0.83:1
    'V3_ORIGINAL': {
        'name': '🔴 V3 Original (R:R 0.83)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 20,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'tp1_pct': 0.50,
        'use_trailing': True,
        'trailing_activation': 7,
        'trailing_distance': 5,
    },

    # ═══════════════════════════════════════════════════════════════
    # 🆕 TP UNIQUE - Le plus SIMPLE: juste TP ou SL, c'est tout!
    # ═══════════════════════════════════════════════════════════════

    # TP UNIQUE 1:1 - SL=10, TP=10
    'TP_UNIQUE_1_1': {
        'name': '🎯 TP_UNIQUE 1:1 (10/10)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 20,
        'tp1_ticks': 10,
        'tp2_ticks': 10,          # TP unique = TP1 = TP2
        'sl_ticks': 10,
        'tp1_pct': 1.00,          # 100% = pas de partial!
        'use_trailing': False,    # Pas de trailing!
        'trailing_activation': 999,
        'trailing_distance': 999,
    },

    # TP UNIQUE 1.5:1 - SL=8, TP=12
    'TP_UNIQUE_1_5': {
        'name': '🎯 TP_UNIQUE 1.5:1 (12/8)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 20,
        'tp1_ticks': 12,
        'tp2_ticks': 12,
        'sl_ticks': 8,
        'tp1_pct': 1.00,
        'use_trailing': False,
        'trailing_activation': 999,
        'trailing_distance': 999,
    },

    # TP UNIQUE 2:1 - SL=8, TP=16
    'TP_UNIQUE_2_1': {
        'name': '🎯 TP_UNIQUE 2:1 (16/8)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 20,
        'tp1_ticks': 16,
        'tp2_ticks': 16,
        'sl_ticks': 8,
        'tp1_pct': 1.00,
        'use_trailing': False,
        'trailing_activation': 999,
        'trailing_distance': 999,
    },

    # TP UNIQUE 2.5:1 - SL=6, TP=15
    'TP_UNIQUE_2_5': {
        'name': '🎯 TP_UNIQUE 2.5:1 (15/6)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 20,
        'tp1_ticks': 15,
        'tp2_ticks': 15,
        'sl_ticks': 6,
        'tp1_pct': 1.00,
        'use_trailing': False,
        'trailing_activation': 999,
        'trailing_distance': 999,
    },

    # TP UNIQUE 3:1 - SL=5, TP=15
    'TP_UNIQUE_3_1': {
        'name': '🎯 TP_UNIQUE 3:1 (15/5)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 22,
        'max_trades_per_day': 20,
        'tp1_ticks': 15,
        'tp2_ticks': 15,
        'sl_ticks': 5,
        'tp1_pct': 1.00,
        'use_trailing': False,
        'trailing_activation': 999,
        'trailing_distance': 999,
    },

    # ═══════════════════════════════════════════════════════════════
    # Autres configs pour comparaison
    # ═══════════════════════════════════════════════════════════════

    # SCALPER - Petits TP/SL rapides
    'SCALPER': {
        'name': '⚡ SCALPER (8/5)',
        'min_confidence': {'ES': 0.46, 'NQ': 0.46},
        'max_distance': {'ES': 17, 'NQ': 22},
        'mia_threshold': 0.22,
        'cooldown_min': 15,
        'max_trades_per_day': 25,
        'tp1_ticks': 8,
        'tp2_ticks': 8,
        'sl_ticks': 5,
        'tp1_pct': 1.00,
        'use_trailing': False,
        'trailing_activation': 999,
        'trailing_distance': 999,
    },

    # CONSERVATIVE - Filtres stricts + bon R:R
    'CONSERVATIVE': {
        'name': '🛡️ CONSERVATIVE (14/7)',
        'min_confidence': {'ES': 0.50, 'NQ': 0.50},
        'max_distance': {'ES': 12, 'NQ': 15},
        'mia_threshold': 0.25,
        'cooldown_min': 25,
        'max_trades_per_day': 15,
        'tp1_ticks': 14,
        'tp2_ticks': 14,
        'sl_ticks': 7,
        'tp1_pct': 1.00,
        'use_trailing': False,
        'trailing_activation': 999,
        'trailing_distance': 999,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#              21 NIVEAUX MENTHORQ
# ═══════════════════════════════════════════════════════════════════════════════

MENTHORQ_LEVELS = [
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
    'gamma_wall_0dte', 'gamma_wall_level',
    'hvl', 'hvl_0dte',
    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
    'call_resistance', 'put_support',
    'call_resistance_0dte', 'put_support_0dte',
    'vwap', 'vwap_up1', 'vwap_dn1', 'vwap_up2', 'vwap_dn2',
]

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

@dataclass
class BacktestResult:
    config_name: str
    trades: List[TradeResult]
    total_pnl: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trades_per_day: float
    avg_win: float
    avg_loss: float
    es_stats: Dict
    nq_stats: Dict
    by_session: Dict

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_month_folder(day: str) -> str:
    return "NOVEMBRE" if day[4:6] == "11" else "DECEMBRE"


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
    
    in_session, session_name = is_in_trading_session(hour, minute)
    if not in_session:
        return False, "", 0, session_name, {}
    
    level_name, level_price, distance = find_nearest_level(snapshot, symbol)
    max_dist = config['max_distance'].get(symbol, 15)
    
    if distance > max_dist:
        return False, "", 0, f"DIST", {'distance': distance}
    
    # Confidence
    menthorq_score = max(0, 1 - distance / 25)
    if level_name in ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap']:
        menthorq_score = min(1.0, menthorq_score * 1.25)
    
    delta = snapshot.get('delta', 0) or 0
    orderflow_score = min(1.0, abs(delta) / 500) * 0.5 + 0.25
    
    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    context_score = min(1.0, abs(mia_score) * 2)
    
    confidence = menthorq_score * 0.50 + orderflow_score * 0.30 + context_score * 0.20
    
    min_conf = config['min_confidence'].get(symbol, 0.50)
    if confidence < min_conf:
        return False, "", confidence, "CONF", {}
    
    # Direction
    threshold = config['mia_threshold']
    if mia_score > threshold:
        direction = "LONG"
    elif mia_score < -threshold:
        direction = "SHORT"
    else:
        return False, "", confidence, "MIA_NEUTRAL", {}
    
    details = {
        'confidence': confidence,
        'distance': distance,
        'level': level_name,
        'session': session_name,
    }
    
    return True, direction, confidence, "OK", details

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION DE TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], config: Dict,
                   session: str, day: str) -> TradeResult:
    
    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']
    
    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)
    
    tp1_ticks = config['tp1_ticks']
    tp2_ticks = config['tp2_ticks']
    sl_ticks = config['sl_ticks']
    tp1_pct = config.get('tp1_pct', 0.50)
    use_trailing = config.get('use_trailing', True)
    trail_act = config.get('trailing_activation', 8)
    trail_dist = config.get('trailing_distance', 4)
    
    # Calculer niveaux
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
            
            # TP1
            if not tp1_hit and low <= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * tp1_pct
            
            # Trailing
            if use_trailing and profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trail_act:
                    trailing = entry - (profit_ticks - trail_dist) * tick_size
            
            # SL
            if high >= sl:
                remaining_pct = (1.0 - tp1_pct) if tp1_hit else 1.0
                pnl += -sl_ticks * tick_value * remaining_pct
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break
            
            # Trailing exit
            if trailing and high >= trailing:
                trail_profit = (entry - trailing) / tick_size
                remaining_pct = (1.0 - tp1_pct) if tp1_hit else 1.0
                pnl += trail_profit * tick_value * remaining_pct
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break
            
            # TP2
            if low <= tp2:
                remaining_pct = (1.0 - tp1_pct) if tp1_hit else 1.0
                pnl += tp2_ticks * tick_value * remaining_pct
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break
        
        else:  # LONG
            profit_ticks = (high - entry) / tick_size
            
            # TP1
            if not tp1_hit and high >= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * tp1_pct
            
            # Trailing
            if use_trailing and profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trail_act:
                    trailing = entry + (profit_ticks - trail_dist) * tick_size
            
            # SL
            if low <= sl:
                remaining_pct = (1.0 - tp1_pct) if tp1_hit else 1.0
                pnl += -sl_ticks * tick_value * remaining_pct
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break
            
            # Trailing exit
            if trailing and low <= trailing:
                trail_profit = (trailing - entry) / tick_size
                remaining_pct = (1.0 - tp1_pct) if tp1_hit else 1.0
                pnl += trail_profit * tick_value * remaining_pct
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break
            
            # TP2
            if high >= tp2:
                remaining_pct = (1.0 - tp1_pct) if tp1_hit else 1.0
                pnl += tp2_ticks * tick_value * remaining_pct
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break
    
    # MAE/MFE
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
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(config: Dict, all_data: Dict, show_progress: bool = False) -> BacktestResult:
    all_trades = []
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
                
                valid, direction, confidence, reason, details = generate_signal(
                    snap, symbol, config, hour, minute
                )
                
                if not valid:
                    continue
                
                future = snapshots[i+1:i+301]
                if len(future) < 10:
                    continue
                
                trade = simulate_trade(
                    snap, direction, symbol, future, config,
                    details.get('session', 'UNKNOWN'), day
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
            avg_win=0,
            avg_loss=0,
            es_stats={},
            nq_stats={},
            by_session={},
        )
    
    # Stats
    total_pnl = sum(t.pnl_usd for t in all_trades)
    winners = [t for t in all_trades if t.pnl_usd > 0]
    losers = [t for t in all_trades if t.pnl_usd < 0]
    
    win_rate = len(winners) / len(all_trades) * 100
    
    avg_win = sum(t.pnl_usd for t in winners) / len(winners) if winners else 0
    avg_loss = sum(t.pnl_usd for t in losers) / len(losers) if losers else 0
    
    gross_profit = sum(t.pnl_usd for t in winners)
    gross_loss = abs(sum(t.pnl_usd for t in losers))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999
    
    # Par symbole
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
    
    # Par session
    by_session = {}
    for session in ['london', 'us_morning', 'power_hour']:
        sess_trades = [t for t in all_trades if t.session == session]
        if sess_trades:
            by_session[session] = {
                'trades': len(sess_trades),
                'pnl': sum(t.pnl_usd for t in sess_trades),
                'wr': len([t for t in sess_trades if t.pnl_usd > 0]) / len(sess_trades) * 100,
            }
    
    return BacktestResult(
        config_name=config['name'],
        trades=all_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        profit_factor=pf,
        total_trades=len(all_trades),
        avg_trades_per_day=len(all_trades) / max(1, days_with_data),
        avg_win=avg_win,
        avg_loss=avg_loss,
        es_stats=es_stats,
        nq_stats=nq_stats,
        by_session=by_session,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("          🎯 BACKTEST V4 - TP UNIQUE + RISK:REWARD")
    print("=" * 100)
    print(f"""
🔍 PROBLÈME V3: WR 63% mais PnL négatif!
   → R:R était 0.83:1 (TP1=10, TP2=15, SL=15)
   → Le TP partiel créait des PARTIAL perdants!

📊 SOLUTION V4: TP UNIQUE (pas de partial, pas de trailing)
   
   ┌─────────────────────────────────────────────────────────┐
   │  Config         │  TP  │  SL  │  R:R  │ WR min rentable │
   ├─────────────────────────────────────────────────────────┤
   │  TP_UNIQUE_1_1  │  10  │  10  │  1:1  │     50.0%       │
   │  TP_UNIQUE_1_5  │  12  │   8  │ 1.5:1 │     40.0%       │
   │  TP_UNIQUE_2_1  │  16  │   8  │  2:1  │     33.3%       │
   │  TP_UNIQUE_2_5  │  15  │   6  │ 2.5:1 │     28.6%       │
   │  TP_UNIQUE_3_1  │  15  │   5  │  3:1  │     25.0%       │
   │  SCALPER        │   8  │   5  │ 1.6:1 │     38.5%       │
   │  CONSERVATIVE   │  14  │   7  │  2:1  │     33.3%       │
   └─────────────────────────────────────────────────────────┘

💰 1 contrat MINI: ES=$12.50/tick, NQ=$5.00/tick
""")
    
    # Charger données
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
    
    print(f"\n   📊 {days_loaded} jours | {total_snapshots:,} snapshots")
    
    if days_loaded == 0:
        print("\n❌ Aucune donnée!")
        return
    
    # Backtests
    print("\n" + "=" * 100)
    print("                    🧪 EXÉCUTION DES BACKTESTS")
    print("=" * 100)
    
    results = {}
    for config_name, config in CONFIGS.items():
        print(f"\n▶ {config['name']}...")
        result = run_backtest(config, all_data, show_progress=True)
        results[config_name] = result
        print(f"   ✅ {result.total_trades} trades | WR: {result.win_rate:.1f}% | PnL: ${result.total_pnl:+,.0f} | PF: {result.profit_factor:.2f}")
    
    # Résultats
    print("\n" + "=" * 100)
    print("                    📊 RÉSULTATS COMPARATIFS")
    print("=" * 100)
    
    print(f"\n{'Config':<30} {'Trades':>6} {'T/J':>5} {'WR%':>6} {'AvgWin':>8} {'AvgLoss':>9} {'PnL':>12} {'PF':>6}")
    print("-" * 95)
    
    for name, r in results.items():
        marker = "🏆" if r.total_pnl > 0 and r.total_pnl == max(x.total_pnl for x in results.values()) else "  "
        print(f"{marker}{r.config_name:<28} {r.total_trades:>6} {r.avg_trades_per_day:>4.1f} {r.win_rate:>5.1f}% ${r.avg_win:>+6.0f} ${r.avg_loss:>+7.0f} ${r.total_pnl:>+10,.0f} {r.profit_factor:>5.2f}")
    
    print("-" * 95)
    
    # Analyse R:R
    print("\n" + "=" * 100)
    print("                    📈 ANALYSE RISK:REWARD")
    print("=" * 100)
    
    for name, r in results.items():
        if r.total_trades == 0:
            continue
        
        cfg = CONFIGS[name]
        theoretical_rr = cfg['tp2_ticks'] / cfg['sl_ticks']
        actual_rr = abs(r.avg_win / r.avg_loss) if r.avg_loss != 0 else 0
        breakeven_wr = 100 / (1 + actual_rr) if actual_rr > 0 else 50
        
        status = "✅ RENTABLE" if r.total_pnl > 0 else "❌ PERTE"
        
        print(f"\n{r.config_name}")
        print(f"   Théorique R:R: {theoretical_rr:.2f}:1 (TP{cfg['tp2_ticks']}/SL{cfg['sl_ticks']})")
        print(f"   Réel R:R:      {actual_rr:.2f}:1 (AvgWin ${r.avg_win:+.0f} / AvgLoss ${r.avg_loss:.0f})")
        print(f"   WR Breakeven:  {breakeven_wr:.1f}%")
        print(f"   WR Actuel:     {r.win_rate:.1f}%")
        print(f"   Marge:         {r.win_rate - breakeven_wr:+.1f}%")
        print(f"   Status:        {status}")
    
    # Meilleure config
    best = max([(name, r) for name, r in results.items() if r.total_trades > 0], 
               key=lambda x: x[1].total_pnl, default=(None, None))
    
    if best[0] and best[1].total_pnl > 0:
        name, r = best
        cfg = CONFIGS[name]
        
        print("\n" + "=" * 100)
        print("                    🏆 MEILLEURE CONFIG RENTABLE")
        print("=" * 100)
        print(f"""
┌────────────────────────────────────────────────────────────────────┐
│  {r.config_name:<64} │
├────────────────────────────────────────────────────────────────────┤
│  Trades/jour: {r.avg_trades_per_day:<5.1f}                                           │
│  Win Rate:    {r.win_rate:<5.1f}%                                          │
│  Avg Win:     ${r.avg_win:<+8.0f}                                        │
│  Avg Loss:    ${r.avg_loss:<+8.0f}                                        │
│  P&L Total:   ${r.total_pnl:<+10,.0f}                                      │
│  Profit Factor: {r.profit_factor:<5.2f}                                       │
└────────────────────────────────────────────────────────────────────┘

🚀 PARAMÈTRES POUR PRODUCTION:
────────────────────────────────
TP1_TICKS = {cfg['tp1_ticks']}
TP2_TICKS = {cfg['tp2_ticks']}
SL_TICKS  = {cfg['sl_ticks']}
TP1_PCT   = {cfg.get('tp1_pct', 0.5)} ({int(cfg.get('tp1_pct', 0.5)*100)}% au TP1)
""")
    else:
        print("\n⚠️ AUCUNE CONFIG RENTABLE! Besoin d'ajuster les paramètres de signal.")
    
    # CSV
    csv_path = Path("backtest_v4_rr_results.csv")
    with open(csv_path, 'w') as f:
        f.write("Config,Trades,T/J,WR,AvgWin,AvgLoss,PnL,PF,ES_PnL,NQ_PnL\n")
        for name, r in results.items():
            f.write(f"{name},{r.total_trades},{r.avg_trades_per_day:.1f},{r.win_rate:.1f},{r.avg_win:.2f},{r.avg_loss:.2f},{r.total_pnl:.2f},{r.profit_factor:.2f},{r.es_stats.get('pnl',0):.2f},{r.nq_stats.get('pnl',0):.2f}\n")
    
    print(f"\n✅ Résultats: {csv_path}")
    print("\n✅ BACKTEST TERMINÉ!")


if __name__ == "__main__":
    main()
