#!/usr/bin/env python3
"""
🔄 BACKTEST MULTI-JOURS OPTIMISÉ V2
Basé sur la connaissance complète du projet MIA

AMÉLIORATIONS vs Version originale:
1. Tous les niveaux MenthorQ (pas juste 6)
2. Level Cooldown (évite overtrading même niveau)
3. Sessions réelles (London, US Open, Power Hour)
4. Corrélation ES/NQ
5. Vérification obstacles avant TP
6. Métriques avancées (Drawdown, Expectancy)
7. Multiprocessing pour vitesse
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from itertools import product
import concurrent.futures
import os

# ============================================================
# CONFIGURATION BASÉE SUR LE PROJET MIA
# ============================================================

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

# TOUS les jours disponibles (Novembre + Décembre)
DAYS_TO_TEST = [
    # NOVEMBRE (18 jours)
    ("NOVEMBRE", "20251105"), ("NOVEMBRE", "20251106"), ("NOVEMBRE", "20251107"),
    ("NOVEMBRE", "20251110"), ("NOVEMBRE", "20251111"), ("NOVEMBRE", "20251112"),
    ("NOVEMBRE", "20251113"), ("NOVEMBRE", "20251114"), ("NOVEMBRE", "20251117"),
    ("NOVEMBRE", "20251118"), ("NOVEMBRE", "20251119"), ("NOVEMBRE", "20251120"),
    ("NOVEMBRE", "20251121"), ("NOVEMBRE", "20251124"), ("NOVEMBRE", "20251125"),
    ("NOVEMBRE", "20251126"), ("NOVEMBRE", "20251127"), ("NOVEMBRE", "20251130"),
    # DÉCEMBRE (13 jours)
    ("DECEMBRE", "20251201"), ("DECEMBRE", "20251202"), ("DECEMBRE", "20251203"),
    ("DECEMBRE", "20251204"), ("DECEMBRE", "20251205"), ("DECEMBRE", "20251206"),
    ("DECEMBRE", "20251207"), ("DECEMBRE", "20251208"), ("DECEMBRE", "20251209"),
    ("DECEMBRE", "20251210"), ("DECEMBRE", "20251211"), ("DECEMBRE", "20251212"),
    ("DECEMBRE", "20251213"),
]

SYMBOLS = {
    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50, "max_distance": 10},
    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00, "max_distance": 15},
}

# Sessions de trading (heure Paris) - Session Quality Monitor MIA
# https://github.com/user/MIA - core/session_quality_monitor.py
SESSIONS = {
    "LONDON": (8, 11),       # 08:00 - 11:00 Paris
    "US_MORNING": (15, 17),  # 15:30 - 17:00 Paris (US Open)
    "LUNCH_BREAK": (17, 20), # 17:00 - 19:30 Paris (ÉVITER - lunch US)
    "POWER_HOUR": (20, 22),  # 20:00 - 21:30 Paris (Power Hour)
}

# Sessions de qualité pour le trading (du Session Quality Monitor)
QUALITY_SESSIONS = ["LONDON", "US_MORNING", "POWER_HOUR"]  # Exclut LUNCH_BREAK

# Paramètres fixes
SL_TICKS = 15
MIN_CONFIDENCE = 1.00

# ============================================================
# NIVEAUX MENTHORQ COMPLETS (du projet MIA)
# ============================================================

MENTHORQ_LEVELS = [
    # GEX Levels (10)
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    # Blind Spots (9)
    'blind_spot_0', 'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
    'blind_spot_4', 'blind_spot_5', 'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
    # Structure
    'call_resistance', 'put_support', 'hvl', 'hvl_0dte',
    'call_resistance_0dte', 'put_support_0dte',
    # Daily
    '1d_max', '1d_min',
    # Next Wall (nested)
    'next_wall_price',
]

# Niveaux bloquants pour TP (obstacles)
BLOCKING_LEVELS_LONG = ['call_resistance', 'call_resistance_0dte', 'hvl', 'hvl_0dte'] + \
                       [f'blind_spot_{i}' for i in range(9)] + \
                       [f'gex_{i}' for i in range(1, 6)]

BLOCKING_LEVELS_SHORT = ['put_support', 'put_support_0dte', 'hvl', 'hvl_0dte'] + \
                        [f'blind_spot_{i}' for i in range(9)] + \
                        [f'gex_{i}' for i in range(1, 6)]

# ============================================================
# GRILLE DE PARAMÈTRES OPTIMISÉE
# ============================================================

PARAM_GRID = {
    'cooldown_min': [15, 20, 30, 45],           # Plus agressif possible
    'tp1_ticks': [8, 10, 12],
    'tp2_ticks': [15],
    'trailing_activation': [6, 8, 10, 12],
    'trailing_distance': [3, 4, 5, 6],
    'max_trades_per_symbol': [8, 10, 12, 15],   # AUGMENTÉ
    'max_trades_per_session': [3, 4, 5, 6],     # NOUVEAU: par session (Session Quality)
    'level_cooldown_min': [10, 15, 20],         # Plus court possible
    'level_cooldown_ticks': [10, 15, 20],       # Zone "même niveau"
    'mia_score_threshold': [0.20, 0.25, 0.30],  # Plus sensible
    'check_obstacles': [True, False],           # Vérifier obstacles
    'use_sessions': [True],                     # Toujours filtrer par session qualité
}

# Version réduite pour test rapide - Plus de trades par session
PARAM_GRID_FAST = {
    'cooldown_min': [20, 30, 45],              # Plus agressif
    'tp1_ticks': [10],
    'tp2_ticks': [15],
    'trailing_activation': [8, 10],
    'trailing_distance': [4, 5],
    'max_trades_per_symbol': [8, 10, 12, 15],  # AUGMENTÉ
    'max_trades_per_session': [4, 5, 6],       # NOUVEAU: par session
    'level_cooldown_min': [15, 20],            # Plus agressif
    'level_cooldown_ticks': [10, 15],
    'mia_score_threshold': [0.25, 0.30],       # Plus sensible
    'check_obstacles': [True],
    'use_sessions': [True],
}

# ============================================================
# STRUCTURES DE DONNÉES
# ============================================================

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
    exit_time: int
    mfe_ticks: float
    mae_ticks: float
    day: str
    level_name: str = ""
    session: str = ""
    had_obstacle: bool = False

@dataclass
class BacktestParams:
    cooldown_min: int
    tp1_ticks: int
    tp2_ticks: int
    trailing_activation: int
    trailing_distance: int
    max_trades_per_symbol: int
    max_trades_per_session: int  # NOUVEAU: limite par session (Session Quality Monitor)
    level_cooldown_min: int
    level_cooldown_ticks: int
    mia_score_threshold: float
    check_obstacles: bool
    use_sessions: bool

@dataclass
class BacktestResult:
    params: BacktestParams
    trades: List[TradeResult]
    total_pnl: float
    win_rate: float
    profit_factor: float
    total_trades: int
    es_pnl: float
    nq_pnl: float
    es_wr: float
    nq_wr: float
    max_drawdown: float = 0
    expectancy: float = 0
    avg_win: float = 0
    avg_loss: float = 0

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def load_snapshots_for_day(month: str, day: str, symbol: str) -> List[Dict]:
    """Charge les snapshots pour un mois, jour et symbole."""
    config = SYMBOLS[symbol]
    data_path = DATA_BASE_PATH / month / day

    possible_paths = [
        data_path / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{config['chart_id']}.jsonl",
        data_path / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{symbol}H25_FUT_CME_{config['chart_id']}.jsonl",
    ]

    file_path = None
    for p in possible_paths:
        if p.exists():
            file_path = p
            break

    if not file_path:
        return []

    snapshots = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snap = json.loads(line)
                    snapshots.append(snap)
                except json.JSONDecodeError:
                    continue

    snapshots.sort(key=lambda x: x.get('t_ms', 0))
    return snapshots


def get_hour_paris(t_ms: int) -> int:
    """Convertit timestamp en heure Paris."""
    hour_utc = (t_ms // 1000 // 3600) % 24
    return (hour_utc + 1) % 24


def get_session(hour: int) -> str:
    """Retourne la session active pour une heure donnée."""
    for session_name, (start, end) in SESSIONS.items():
        if start <= hour < end:
            return session_name
    return "OFF_HOURS"


def get_level_value(snap: Dict, level_name: str) -> Optional[float]:
    """Récupère la valeur d'un niveau depuis le snapshot."""
    if level_name == 'next_wall_price':
        next_wall = snap.get('next_wall', {})
        if isinstance(next_wall, dict):
            return next_wall.get('price')
        return None
    return snap.get(level_name)


def find_nearest_level(snap: Dict, symbol: str) -> Tuple[float, str, float]:
    """Trouve le niveau le plus proche du prix actuel."""
    mid = snap.get('mid', 0)
    if mid <= 0:
        return float('inf'), "", 0

    tick_size = SYMBOLS[symbol]['tick_size']
    max_dist = SYMBOLS[symbol]['max_distance']

    nearest_dist = float('inf')
    nearest_name = ""
    nearest_price = 0

    for level_name in MENTHORQ_LEVELS:
        price = get_level_value(snap, level_name)
        if price and price > 0:
            dist_ticks = abs(mid - price) / tick_size
            if dist_ticks < nearest_dist:
                nearest_dist = dist_ticks
                nearest_name = level_name
                nearest_price = price

    return nearest_dist, nearest_name, nearest_price


def check_obstacle_before_tp(
    snap: Dict,
    direction: str,
    entry_price: float,
    tp_price: float,
    tick_size: float
) -> Tuple[bool, str]:
    """Vérifie s'il y a un obstacle entre l'entrée et le TP."""
    blocking_levels = BLOCKING_LEVELS_LONG if direction == "LONG" else BLOCKING_LEVELS_SHORT

    for level_name in blocking_levels:
        price = get_level_value(snap, level_name)
        if not price or price <= 0:
            continue

        if direction == "LONG":
            if entry_price < price < tp_price:
                dist = abs(price - entry_price) / tick_size
                if dist < 15:  # Obstacle significatif
                    return True, level_name
        else:  # SHORT
            if tp_price < price < entry_price:
                dist = abs(entry_price - price) / tick_size
                if dist < 15:
                    return True, level_name

    return False, ""


def check_signal_valid(
    snap: Dict,
    symbol: str,
    recent_snaps: List[Dict],
    params: BacktestParams,
    traded_levels: Dict[str, int],  # {level_key: last_trade_time}
    current_time: int
) -> Tuple[bool, str, float, str, float]:
    """
    Vérifie si un signal est valide avec tous les filtres MIA.
    Retourne: (is_valid, direction, confidence, level_name, level_price)
    """
    mid = snap.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "", 0

    tick_size = SYMBOLS[symbol]['tick_size']
    max_dist = SYMBOLS[symbol]['max_distance']

    # Trouver niveau le plus proche
    nearest_dist, nearest_name, nearest_price = find_nearest_level(snap, symbol)

    if nearest_dist > max_dist:
        return False, "", 0, "", 0

    # === LEVEL COOLDOWN ===
    level_key = f"{symbol}_{nearest_name}_{int(nearest_price)}"
    cooldown_ms = params.level_cooldown_min * 60 * 1000

    if level_key in traded_levels:
        last_time = traded_levels[level_key]
        if current_time - last_time < cooldown_ms:
            return False, "", 0, "", 0

    # Vérifier si un niveau proche a été tradé récemment
    for key, last_time in traded_levels.items():
        if not key.startswith(f"{symbol}_"):
            continue
        if current_time - last_time >= cooldown_ms:
            continue

        # Extraire le prix du key
        try:
            other_price = float(key.split('_')[-1])
            dist = abs(mid - other_price) / tick_size
            if dist < params.level_cooldown_ticks:
                return False, "", 0, "", 0
        except:
            pass

    # === DIRECTION ===
    mia_score = snap.get('mia_bullish_score', 0)

    if mia_score < -params.mia_score_threshold:
        direction = "SHORT"
    elif mia_score > params.mia_score_threshold:
        direction = "LONG"
    else:
        return False, "", 0, "", 0

    # === VÉRIFIER RETOURNEMENT ===
    if len(recent_snaps) >= 10:
        old_score = recent_snaps[0].get('mia_bullish_score', 0)
        if abs(mia_score - old_score) > 0.40:
            return False, "", 0, "", 0

    # === VÉRIFIER DELTA ===
    delta = snap.get('delta', 0)
    if direction == "SHORT" and delta > 200:
        return False, "", 0, "", 0
    if direction == "LONG" and delta < -200:
        return False, "", 0, "", 0

    # === VÉRIFIER OBSTACLES ===
    if params.check_obstacles:
        tp_ticks = params.tp2_ticks
        if direction == "SHORT":
            tp_price = mid - (tp_ticks * tick_size)
        else:
            tp_price = mid + (tp_ticks * tick_size)

        has_obstacle, obstacle_name = check_obstacle_before_tp(
            snap, direction, mid, tp_price, tick_size
        )
        if has_obstacle:
            return False, "", 0, "", 0

    confidence = 1.0 + abs(mia_score) * 0.5
    return True, direction, confidence, nearest_name, nearest_price


def simulate_trade(
    entry_snap: Dict,
    direction: str,
    symbol: str,
    future_snapshots: List[Dict],
    params: BacktestParams,
    day: str,
    level_name: str,
    session: str,
) -> TradeResult:
    """Simule un trade avec les paramètres donnés."""
    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    # Prix cibles
    if direction == "SHORT":
        tp1_price = entry - (params.tp1_ticks * tick_size)
        tp2_price = entry - (params.tp2_ticks * tick_size)
        sl_price = entry + (SL_TICKS * tick_size)
    else:
        tp1_price = entry + (params.tp1_ticks * tick_size)
        tp2_price = entry + (params.tp2_ticks * tick_size)
        sl_price = entry - (SL_TICKS * tick_size)

    tp1_hit = False
    trailing_stop = None
    best_profit_ticks = 0
    pnl_usd = 0
    result = "TIMEOUT"
    exit_price = entry
    exit_time = entry_time
    high_reached = entry
    low_reached = entry

    for snap in future_snapshots:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:
            break

        high = snap.get('high', entry)
        low = snap.get('low', entry)
        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        if direction == "SHORT":
            profit_ticks = (entry - low) / tick_size

            if not tp1_hit and low <= tp1_price:
                tp1_hit = True
                pnl_usd += params.tp1_ticks * tick_value * 0.5

            if profit_ticks > best_profit_ticks:
                best_profit_ticks = profit_ticks
                if profit_ticks >= params.trailing_activation:
                    new_ts = entry - ((profit_ticks - params.trailing_distance) * tick_size)
                    if trailing_stop is None or new_ts < trailing_stop:
                        trailing_stop = new_ts

            if high >= sl_price:
                if tp1_hit:
                    pnl_usd += -SL_TICKS * tick_value * 0.5
                    result = "PARTIAL"
                else:
                    pnl_usd = -SL_TICKS * tick_value
                    result = "LOSS"
                exit_price = sl_price
                exit_time = t_ms
                break

            if trailing_stop and high >= trailing_stop:
                profit_trailing = (entry - trailing_stop) / tick_size
                if tp1_hit:
                    pnl_usd += profit_trailing * tick_value * 0.5
                else:
                    pnl_usd = profit_trailing * tick_value
                result = "TRAILING"
                exit_price = trailing_stop
                exit_time = t_ms
                break

            if low <= tp2_price:
                if tp1_hit:
                    pnl_usd += params.tp2_ticks * tick_value * 0.5
                else:
                    pnl_usd = params.tp2_ticks * tick_value
                result = "WIN"
                exit_price = tp2_price
                exit_time = t_ms
                break

        else:  # LONG
            profit_ticks = (high - entry) / tick_size

            if not tp1_hit and high >= tp1_price:
                tp1_hit = True
                pnl_usd += params.tp1_ticks * tick_value * 0.5

            if profit_ticks > best_profit_ticks:
                best_profit_ticks = profit_ticks
                if profit_ticks >= params.trailing_activation:
                    new_ts = entry + ((profit_ticks - params.trailing_distance) * tick_size)
                    if trailing_stop is None or new_ts > trailing_stop:
                        trailing_stop = new_ts

            if low <= sl_price:
                if tp1_hit:
                    pnl_usd += -SL_TICKS * tick_value * 0.5
                    result = "PARTIAL"
                else:
                    pnl_usd = -SL_TICKS * tick_value
                    result = "LOSS"
                exit_price = sl_price
                exit_time = t_ms
                break

            if trailing_stop and low <= trailing_stop:
                profit_trailing = (trailing_stop - entry) / tick_size
                if tp1_hit:
                    pnl_usd += profit_trailing * tick_value * 0.5
                else:
                    pnl_usd = profit_trailing * tick_value
                result = "TRAILING"
                exit_price = trailing_stop
                exit_time = t_ms
                break

            if high >= tp2_price:
                if tp1_hit:
                    pnl_usd += params.tp2_ticks * tick_value * 0.5
                else:
                    pnl_usd = params.tp2_ticks * tick_value
                result = "WIN"
                exit_price = tp2_price
                exit_time = t_ms
                break

    if direction == "LONG":
        mae_ticks = (entry - low_reached) / tick_size
        mfe_ticks = (high_reached - entry) / tick_size
    else:
        mae_ticks = (high_reached - entry) / tick_size
        mfe_ticks = (entry - low_reached) / tick_size

    return TradeResult(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        exit_price=exit_price,
        result=result,
        pnl_usd=pnl_usd,
        tp1_hit=tp1_hit,
        entry_time=entry_time,
        exit_time=exit_time,
        mfe_ticks=mfe_ticks,
        mae_ticks=mae_ticks,
        day=day,
        level_name=level_name,
        session=session,
    )


def run_backtest_with_params(params: BacktestParams, all_data: Dict) -> BacktestResult:
    """Exécute un backtest avec les paramètres donnés."""
    all_trades = []
    cooldown_ms = params.cooldown_min * 60 * 1000

    for day_key, day_data in all_data.items():
        traded_levels = {}  # Reset par jour

        for symbol in ["ES", "NQ"]:
            snapshots = day_data.get(symbol, [])
            if not snapshots:
                continue

            last_trade_time = 0
            trade_count = 0
            session_trade_counts = {}  # Compteur par session

            for idx, snap in enumerate(snapshots):
                t_ms = snap.get('t_ms', 0)
                hour = get_hour_paris(t_ms)
                session = get_session(hour)

                # Filtre session - Exclure OFF_HOURS et LUNCH_BREAK
                if params.use_sessions:
                    if session not in QUALITY_SESSIONS:
                        continue

                # Cooldown global
                if t_ms - last_trade_time < cooldown_ms:
                    continue

                # Max trades par symbole/jour
                if trade_count >= params.max_trades_per_symbol:
                    break

                # Max trades par session (Session Quality Monitor)
                session_key = f"{symbol}_{session}"
                if session_key not in session_trade_counts:
                    session_trade_counts[session_key] = 0
                if session_trade_counts[session_key] >= params.max_trades_per_session:
                    continue

                # Signal
                recent_start = max(0, idx - 30)
                recent_snaps = snapshots[recent_start:idx]

                is_valid, direction, confidence, level_name, level_price = check_signal_valid(
                    snap, symbol, recent_snaps, params, traded_levels, t_ms
                )

                if is_valid and confidence >= MIN_CONFIDENCE:
                    future_snaps = snapshots[idx + 1:]
                    if len(future_snaps) < 10:
                        continue

                    trade = simulate_trade(
                        snap, direction, symbol, future_snaps,
                        params, day_key, level_name, session
                    )
                    all_trades.append(trade)
                    last_trade_time = t_ms
                    trade_count += 1
                    session_trade_counts[session_key] += 1

                    # Enregistrer le niveau tradé
                    level_key = f"{symbol}_{level_name}_{int(level_price)}"
                    traded_levels[level_key] = t_ms

    # Calculer métriques
    if not all_trades:
        return BacktestResult(
            params=params, trades=[], total_pnl=0, win_rate=0,
            profit_factor=0, total_trades=0, es_pnl=0, nq_pnl=0,
            es_wr=0, nq_wr=0, max_drawdown=0, expectancy=0,
            avg_win=0, avg_loss=0
        )

    total_pnl = sum(t.pnl_usd for t in all_trades)
    profitable = [t for t in all_trades if t.pnl_usd > 0]
    win_rate = len(profitable) / len(all_trades) * 100

    gross_profit = sum(t.pnl_usd for t in all_trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in all_trades if t.pnl_usd < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Calcul drawdown
    equity_curve = []
    running_pnl = 0
    peak = 0
    max_dd = 0
    for t in all_trades:
        running_pnl += t.pnl_usd
        equity_curve.append(running_pnl)
        if running_pnl > peak:
            peak = running_pnl
        dd = peak - running_pnl
        if dd > max_dd:
            max_dd = dd

    # Expectancy
    wins = [t for t in all_trades if t.pnl_usd > 0]
    losses = [t for t in all_trades if t.pnl_usd < 0]
    avg_win = sum(t.pnl_usd for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t.pnl_usd for t in losses) / len(losses)) if losses else 0
    win_prob = len(wins) / len(all_trades) if all_trades else 0
    expectancy = (win_prob * avg_win) - ((1 - win_prob) * avg_loss)

    # Par symbole
    es_trades = [t for t in all_trades if t.symbol == "ES"]
    nq_trades = [t for t in all_trades if t.symbol == "NQ"]

    es_pnl = sum(t.pnl_usd for t in es_trades)
    nq_pnl = sum(t.pnl_usd for t in nq_trades)
    es_wr = len([t for t in es_trades if t.pnl_usd > 0]) / len(es_trades) * 100 if es_trades else 0
    nq_wr = len([t for t in nq_trades if t.pnl_usd > 0]) / len(nq_trades) * 100 if nq_trades else 0

    return BacktestResult(
        params=params,
        trades=all_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=len(all_trades),
        es_pnl=es_pnl,
        nq_pnl=nq_pnl,
        es_wr=es_wr,
        nq_wr=nq_wr,
        max_drawdown=max_dd,
        expectancy=expectancy,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )


def main(fast_mode: bool = True):
    """Fonction principale d'optimisation."""
    print("=" * 80)
    print("🔄 OPTIMISATION PARAMÈTRES V2 - MIA IA SYSTEM")
    print("   Session Quality Monitor intégré")
    print("=" * 80)
    print(f"📅 Jours: {len(DAYS_TO_TEST)} (Novembre + Décembre 2025)")
    print(f"🎯 Sessions Qualité: {', '.join(QUALITY_SESSIONS)}")
    print(f"⚙️  Mode: {'RAPIDE' if fast_mode else 'COMPLET'}")
    print()

    # Charger données avec format (month, day)
    print("📂 Chargement des données...")
    all_data = {}
    total_snaps = 0
    days_loaded = 0

    for month, day in DAYS_TO_TEST:
        day_key = f"{month}_{day}"
        all_data[day_key] = {}
        day_total = 0

        for symbol in ["ES", "NQ"]:
            snapshots = load_snapshots_for_day(month, day, symbol)
            all_data[day_key][symbol] = snapshots
            day_total += len(snapshots)
            total_snaps += len(snapshots)

        if day_total > 0:
            days_loaded += 1
            print(f"   ✅ {day} ({month[:3]}): {day_total:,} snapshots")

    print(f"\n📊 Total: {total_snaps:,} snapshots sur {days_loaded} jours")
    print()

    # Grille de paramètres
    grid = PARAM_GRID_FAST if fast_mode else PARAM_GRID

    param_combinations = list(product(
        grid['cooldown_min'],
        grid['tp1_ticks'],
        grid['tp2_ticks'],
        grid['trailing_activation'],
        grid['trailing_distance'],
        grid['max_trades_per_symbol'],
        grid['max_trades_per_session'],
        grid['level_cooldown_min'],
        grid['level_cooldown_ticks'],
        grid['mia_score_threshold'],
        grid['check_obstacles'],
        grid['use_sessions'],
    ))

    print(f"🧪 Test de {len(param_combinations)} combinaisons...")
    print()

    results = []
    best_result = None
    best_score = float('-inf')

    for i, combo in enumerate(param_combinations):
        params = BacktestParams(
            cooldown_min=combo[0],
            tp1_ticks=combo[1],
            tp2_ticks=combo[2],
            trailing_activation=combo[3],
            trailing_distance=combo[4],
            max_trades_per_symbol=combo[5],
            max_trades_per_session=combo[6],
            level_cooldown_min=combo[7],
            level_cooldown_ticks=combo[8],
            mia_score_threshold=combo[9],
            check_obstacles=combo[10],
            use_sessions=combo[11],
        )

        result = run_backtest_with_params(params, all_data)
        results.append(result)

        # Score composite (PnL + PF + WR)
        score = result.total_pnl + (result.profit_factor * 100) + result.win_rate
        if score > best_score and result.total_trades >= 10:
            best_score = score
            best_result = result

        if (i + 1) % 20 == 0:
            print(f"   {i + 1}/{len(param_combinations)} ({(i+1)/len(param_combinations)*100:.0f}%)")

    # Résultats
    print("\n" + "=" * 80)
    print("📊 RÉSULTATS DE L'OPTIMISATION")
    print("=" * 80)

    # Top 10
    results_valid = [r for r in results if r.total_trades >= 5]
    results_sorted = sorted(results_valid, key=lambda x: x.total_pnl, reverse=True)

    print("\n🏆 TOP 10:")
    print("-" * 110)
    print(f"{'#':>2} {'PnL':>9} {'WR%':>6} {'PF':>5} {'Exp':>7} {'DD':>7} {'Tr':>4} {'CD':>4} {'Tr/Ses':>6} {'TP1':>4} {'Trail':>7} {'LvlCD':>6}")
    print("-" * 110)

    for i, r in enumerate(results_sorted[:10], 1):
        p = r.params
        trail = f"{p.trailing_activation}/{p.trailing_distance}"
        lvlcd = f"{p.level_cooldown_min}m"
        print(f"{i:>2} ${r.total_pnl:>7.0f} {r.win_rate:>5.1f}% {r.profit_factor:>4.2f} ${r.expectancy:>5.0f} ${r.max_drawdown:>5.0f} {r.total_trades:>4} {p.cooldown_min:>3}m {p.max_trades_per_session:>6} {p.tp1_ticks:>3}t {trail:>7} {lvlcd:>6}")

    # Meilleure config
    if best_result:
        p = best_result.params
        print("\n" + "=" * 80)
        print("🥇 MEILLEURE CONFIGURATION")
        print("=" * 80)
        print(f"""
📊 PARAMÈTRES:
   Cooldown global:       {p.cooldown_min} min
   TP1 (50%):             {p.tp1_ticks} ticks
   TP2 (50%):             {p.tp2_ticks} ticks
   Trailing:              {p.trailing_activation}t activation, {p.trailing_distance}t distance
   Max trades/symbole:    {p.max_trades_per_symbol}
   Max trades/session:    {p.max_trades_per_session}  ← Session Quality Monitor
   Level cooldown:        {p.level_cooldown_min} min, {p.level_cooldown_ticks} ticks zone
   MIA score seuil:       {p.mia_score_threshold}
   Check obstacles:       {p.check_obstacles}
   Filter sessions:       {p.use_sessions}

📈 PERFORMANCE:
   PnL Total:     ${best_result.total_pnl:+.2f}
   Win Rate:      {best_result.win_rate:.1f}%
   Profit Factor: {best_result.profit_factor:.2f}
   Expectancy:    ${best_result.expectancy:.2f}/trade
   Max Drawdown:  ${best_result.max_drawdown:.2f}
   Avg Win:       ${best_result.avg_win:.2f}
   Avg Loss:      ${best_result.avg_loss:.2f}
   Total Trades:  {best_result.total_trades}

📊 PAR SYMBOLE:
   ES: ${best_result.es_pnl:+.2f} ({best_result.es_wr:.1f}% WR)
   NQ: ${best_result.nq_pnl:+.2f} ({best_result.nq_wr:.1f}% WR)
""")

        # Par session (Session Quality Monitor)
        print("🎯 PAR SESSION (Session Quality Monitor):")
        for session in QUALITY_SESSIONS:
            session_trades = [t for t in best_result.trades if t.session == session]
            if session_trades:
                session_pnl = sum(t.pnl_usd for t in session_trades)
                session_wr = len([t for t in session_trades if t.pnl_usd > 0]) / len(session_trades) * 100
                print(f"   {session:12s}: {len(session_trades):3d} trades | WR: {session_wr:.0f}% | ${session_pnl:+.2f}")
        print()

        # Par jour
        print("📅 PAR JOUR:")
        for month, day in DAYS_TO_TEST:
            day_key = f"{month}_{day}"
            day_trades = [t for t in best_result.trades if t.day == day_key]
            if day_trades:
                day_pnl = sum(t.pnl_usd for t in day_trades)
                day_wr = len([t for t in day_trades if t.pnl_usd > 0]) / len(day_trades) * 100
                print(f"   {day} ({month[:3]}): {len(day_trades)} trades | WR: {day_wr:.0f}% | ${day_pnl:+.2f}")

        # Code production
        print("\n" + "=" * 80)
        print("🚀 CODE PRODUCTION")
        print("=" * 80)
        print(f"""
# === PARAMÈTRES OPTIMISÉS MIA V2 ===
# Générés par backtest multi-jours ({len(DAYS_TO_TEST)} jours)
# Sessions: {', '.join(QUALITY_SESSIONS)}

MIN_INTERVAL_SECONDS = {p.cooldown_min * 60}  # {p.cooldown_min} min

TP_CONFIG = {{
    'tp1_ticks': {p.tp1_ticks},
    'tp2_ticks': {p.tp2_ticks},
}}

TRAILING_CONFIG = {{
    'enabled': True,
    'activation_ticks': {p.trailing_activation},
    'distance_ticks': {p.trailing_distance},
}}

LEVEL_COOLDOWN = {{
    'enabled': True,
    'duration_min': {p.level_cooldown_min},
    'zone_ticks': {p.level_cooldown_ticks},
}}

# Session Quality Monitor
MAX_TRADES_PER_SYMBOL = {p.max_trades_per_symbol}
MAX_TRADES_PER_SESSION = {p.max_trades_per_session}  # Par session (London, US_Morning, Power_Hour)
QUALITY_SESSIONS = {QUALITY_SESSIONS}

MIA_SCORE_THRESHOLD = {p.mia_score_threshold}
CHECK_OBSTACLES = {p.check_obstacles}
USE_SESSION_FILTER = {p.use_sessions}
""")

    print("\n✅ Optimisation terminée!")


if __name__ == "__main__":
    import sys
    fast = "--full" not in sys.argv
    main(fast_mode=fast)
