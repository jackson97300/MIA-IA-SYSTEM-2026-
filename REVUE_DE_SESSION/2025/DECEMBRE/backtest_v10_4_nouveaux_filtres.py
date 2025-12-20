# -*- coding: utf-8 -*-
"""
BACKTEST V10.4 - NOUVEAUX FILTRES ANTI-TRADES DE MERDE
======================================================
Filtres basés sur l'analyse des trades perdants:
1. Position in range (LONG > 70%, SHORT < 30%)
2. Distance selon score du niveau
3. (Heures toxiques - à tester séparément)
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Fix encoding Windows
sys.stdout.reconfigure(encoding='utf-8')

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")
SYMBOLS = ['ES', 'NQ']
CHART_MAPPING = {'ES': 3, 'NQ': 4}
TICK_SIZE = {'ES': 0.25, 'NQ': 0.25}
POINT_VALUE = {'ES': 50, 'NQ': 20}

# Sessions (heures Paris UTC+1)
SESSIONS = {
    'LONDON': {'start_h': 8, 'end_h': 11, 'start_m': 0, 'end_m': 0},
    'US_MORNING': {'start_h': 15, 'end_h': 17, 'start_m': 50, 'end_m': 0},
    'POWER_HOUR': {'start_h': 20, 'end_h': 21, 'start_m': 0, 'end_m': 30},
}

# Jours
TRAINING_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127", "20251201", "20251202", "20251203",
    "20251204", "20251205"
]

VALIDATION_DAYS = [
    "20251208", "20251209", "20251210", "20251211",
    "20251212", "20251215", "20251216", "20251217"
]

# =============================================================================
# NOUVEAUX FILTRES V10.4
# =============================================================================

# Filtre 1: Position in range
POSITION_FILTER = {
    'long_max': 70,   # Bloquer LONG si position > 70%
    'short_min': 30,  # Bloquer SHORT si position < 30%
}

# Filtre 2: Distance maximale selon score du niveau
MAX_DISTANCE_BY_SCORE = {
    1: 6,   # Score faible = doit être très proche
    2: 10,  # Score moyen = distance raisonnable
    3: 15,  # Score fort = plus de marge
}

# Niveaux premium et scores
ALL_PREMIUM_LEVELS = [
    'gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap', 'vpoc', '1d_max', '1d_min',
    'gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
    'call_resistance', 'put_support',
    'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
    'vwap_up1', 'vwap_dn1', 'vah', 'val', 'ibh', 'ibl',
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    'call_resistance_0dte', 'put_support_0dte',
    'blind_spot_3', 'blind_spot_4', 'blind_spot_5',
    'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
    'vwap_up2', 'vwap_dn2',
]

LEVEL_SCORES = {
    'gex_1': 3, 'gex_2': 3, 'hvl': 3, 'gamma_wall_level': 3, 'vwap': 3,
    'vpoc': 3, '1d_max': 3, '1d_min': 3,
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2, 'hvl_0dte': 2, 'gamma_wall_0dte': 2,
    'call_resistance': 2, 'put_support': 2,
    'blind_spot_0': 2, 'blind_spot_1': 2, 'blind_spot_2': 2,
    'vwap_up1': 2, 'vwap_dn1': 2, 'vah': 2, 'val': 2, 'ibh': 2, 'ibl': 2,
    'gex_6': 1, 'gex_7': 1, 'gex_8': 1, 'gex_9': 1, 'gex_10': 1,
    'call_resistance_0dte': 1, 'put_support_0dte': 1,
    'blind_spot_3': 1, 'blind_spot_4': 1, 'blind_spot_5': 1,
    'blind_spot_6': 1, 'blind_spot_7': 1, 'blind_spot_8': 1,
    'vwap_up2': 1, 'vwap_dn2': 1,
}

# Configurations à tester
CONFIGS_TO_TEST = {
    'V10.3_BASELINE': {
        'name': 'V10.3 Actuel (baseline)',
        'position_filter': False,
        'distance_by_score': False,
        'hour_filter': False,
    },
    'V10.4_POSITION': {
        'name': 'V10.4 Position Filter Only',
        'position_filter': True,
        'distance_by_score': False,
        'hour_filter': False,
    },
    'V10.4_DISTANCE': {
        'name': 'V10.4 Distance by Score Only',
        'position_filter': False,
        'distance_by_score': True,
        'hour_filter': False,
    },
    'V10.4_COMPLET': {
        'name': 'V10.4 Position + Distance',
        'position_filter': True,
        'distance_by_score': True,
        'hour_filter': False,
    },
}

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def progress_bar(current, total, prefix='', suffix='', length=40):
    percent = 100 * current / total if total > 0 else 0
    filled = int(length * current // total) if total > 0 else 0
    bar = '#' * filled + '-' * (length - filled)
    sys.stdout.write(f'\r   {prefix} [{bar}] {percent:.0f}% {suffix}')
    sys.stdout.flush()
    if current >= total:
        print()

def is_in_session(t_ms: int, session_name: str) -> bool:
    if t_ms == 0:
        return False
    session = SESSIONS.get(session_name)
    if not session:
        return False

    total_sec = t_ms // 1000
    total_min = total_sec // 60
    hour_utc = (total_min // 60) % 24
    minute = total_min % 60
    hour_paris = (hour_utc + 1) % 24

    start_min = session['start_h'] * 60 + session['start_m']
    end_min = session['end_h'] * 60 + session['end_m']
    current_min = hour_paris * 60 + minute

    return start_min <= current_min < end_min

def get_paris_hour(t_ms: int) -> int:
    total_sec = t_ms // 1000
    total_min = total_sec // 60
    hour_utc = (total_min // 60) % 24
    return (hour_utc + 1) % 24

def get_trend(snap: dict) -> str:
    mid = snap.get('mid', 0)
    hvl = snap.get('hvl', 0)
    vwap = snap.get('vwap', 0)

    if not hvl or not vwap:
        return 'NEUTRAL'

    above_hvl = mid > hvl
    above_vwap = mid > vwap

    if above_hvl and above_vwap:
        return 'BULLISH'
    elif not above_hvl and not above_vwap:
        return 'BEARISH'
    return 'NEUTRAL'

def get_level_score(level_name: str) -> int:
    return LEVEL_SCORES.get(level_name, 1)

def extract_levels_from_snapshot(snapshot: dict) -> List[Tuple[str, float, int]]:
    levels = []

    for key in ALL_PREMIUM_LEVELS:
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    # VVA
    vva = snapshot.get('vva', {})
    if vva:
        if vva.get('vpoc'):
            levels.append(('vpoc', float(vva['vpoc']), 3))
        if vva.get('vah'):
            levels.append(('vah', float(vva['vah']), 2))
        if vva.get('val'):
            levels.append(('val', float(vva['val']), 2))

    # Structure
    structure = snapshot.get('structure', {})
    if structure:
        if structure.get('ibh'):
            levels.append(('ibh', float(structure['ibh']), 2))
        if structure.get('ibl'):
            levels.append(('ibl', float(structure['ibl']), 2))

    return levels

def find_best_level(mid: float, levels: List[Tuple[str, float, int]], tick_size: float, max_distance: float = 15) -> Optional[Tuple[str, float, float, int]]:
    """Find best level (closest within max_distance)"""
    valid_levels = []

    for name, price, score in levels:
        dist_ticks = abs(mid - price) / tick_size
        if dist_ticks <= max_distance:
            valid_levels.append((name, price, dist_ticks, score))

    if not valid_levels:
        return None

    # Best = highest score, then closest
    return max(valid_levels, key=lambda x: (x[3], -x[2]))

def determine_direction(snap: dict) -> str:
    mia_score = snap.get('mia_bullish_score', 0.5)
    delta = snap.get('delta', 0)

    if mia_score > 0.55 and delta > 0:
        return 'LONG'
    elif mia_score < 0.45 and delta < 0:
        return 'SHORT'
    elif mia_score > 0.5:
        return 'LONG'
    else:
        return 'SHORT'

# =============================================================================
# FILTRES V10.4
# =============================================================================

def check_position_filter(direction: str, position_in_range: float) -> Tuple[bool, str]:
    """Filtre position in range - PATTERN #1 CRITIQUE"""
    if direction == 'LONG' and position_in_range > POSITION_FILTER['long_max']:
        return False, "LONG_HAUT_DU_RANGE"
    if direction == 'SHORT' and position_in_range < POSITION_FILTER['short_min']:
        return False, "SHORT_BAS_DU_RANGE"
    return True, "OK"

def check_distance_by_score(distance: float, level_score: int) -> Tuple[bool, str]:
    """Filtre distance selon score du niveau"""
    max_dist = MAX_DISTANCE_BY_SCORE.get(level_score, 15)
    if distance > max_dist:
        return False, f"DISTANCE_{distance:.0f}t_>_MAX_{max_dist}t"
    return True, "OK"

def check_trend_filter(snap: dict, direction: str, level_score: int) -> Tuple[bool, str]:
    """Filtre contre-tendance V10.3"""
    trend = get_trend(snap)

    if level_score >= 2:
        return True, f"SCORE_{level_score}_ALLOWED"

    if trend == 'BEARISH' and direction == 'LONG':
        return False, "LONG_BLOCKED_BEARISH"
    if trend == 'BULLISH' and direction == 'SHORT':
        return False, "SHORT_BLOCKED_BULLISH"

    return True, "WITH_TREND"

# =============================================================================
# CHARGEMENT DES DONNÉES
# =============================================================================

def load_snapshots(days: List[str], symbol: str, session_name: str, show_progress: bool = False) -> List[Dict]:
    snapshots = []
    chart_id = CHART_MAPPING.get(symbol, 3)
    MONTHS = {"11": "NOVEMBRE", "12": "DECEMBRE"}

    for idx, day in enumerate(days):
        if show_progress:
            progress_bar(idx + 1, len(days), f'Loading {symbol}', f'{day}')

        try:
            month_num = day[4:6]
            month_name = MONTHS.get(month_num, "DECEMBRE")
            contract_suffix = "H26" if day >= "20251211" else "Z25"

            jsonl_path = (BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                          "ML_READY" / f"ml_{symbol}{contract_suffix}_FUT_CME_{chart_id}.jsonl")

            if not jsonl_path.exists():
                jsonl_path = (BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                              "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl")

            if jsonl_path.exists():
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                snap = json.loads(line)
                                t_ms = snap.get('t_ms', 0)
                                if is_in_session(t_ms, session_name):
                                    snap['_day'] = day
                                    snap['_hour'] = get_paris_hour(t_ms)
                                    snapshots.append(snap)
                            except:
                                continue
        except:
            continue

    return snapshots

# =============================================================================
# BACKTEST
# =============================================================================

def run_backtest(snapshots: List[Dict], symbol: str, session_name: str, config: Dict) -> Dict:
    """Execute backtest with V10.4 filters"""

    tick_size = TICK_SIZE[symbol]
    point_value = POINT_VALUE[symbol]
    tp_ticks = 20
    sl_ticks = 20

    results = {
        'n_trades': 0,
        'wins': 0,
        'losses': 0,
        'pnl_ticks': 0,
        'pnl_usd': 0,
        'rejections': defaultdict(int),
    }

    last_trade_idx = -50

    for i, snap in enumerate(snapshots):
        # Cooldown
        if i - last_trade_idx < 50:
            continue
        if i >= len(snapshots) - 100:
            continue

        mid = snap.get('mid', 0)
        if mid <= 0:
            continue

        # Get levels
        levels = extract_levels_from_snapshot(snap)
        best_level = find_best_level(mid, levels, tick_size)

        if not best_level:
            continue

        level_name, level_price, distance, level_score = best_level

        # Determine direction
        direction = determine_direction(snap)

        # =====================================================
        # FILTRES V10.4
        # =====================================================

        # Filtre 1: Position in range
        if config.get('position_filter', False):
            position_in_range = snap.get('position_in_range', 50)
            ok, reason = check_position_filter(direction, position_in_range)
            if not ok:
                results['rejections']['position_filter'] += 1
                results['rejections'][reason] += 1
                continue

        # Filtre 2: Distance selon score
        if config.get('distance_by_score', False):
            ok, reason = check_distance_by_score(distance, level_score)
            if not ok:
                results['rejections']['distance_by_score'] += 1
                results['rejections'][reason] += 1
                continue

        # Filtre 3: Contre-tendance V10.3
        ok, reason = check_trend_filter(snap, direction, level_score)
        if not ok:
            results['rejections']['trend_filter'] += 1
            continue

        # =====================================================
        # SIMULATION DU TRADE
        # =====================================================

        if direction == 'LONG':
            tp_price = mid + (tp_ticks * tick_size)
            sl_price = mid - (sl_ticks * tick_size)
        else:
            tp_price = mid - (tp_ticks * tick_size)
            sl_price = mid + (sl_ticks * tick_size)

        # Check next 100 bars
        trade_result = None
        for j in range(i + 1, min(i + 100, len(snapshots))):
            bar = snapshots[j]
            high = bar.get('high', bar.get('mid', mid))
            low = bar.get('low', bar.get('mid', mid))

            if direction == 'LONG':
                if low <= sl_price:
                    trade_result = 'LOSS'
                    break
                if high >= tp_price:
                    trade_result = 'WIN'
                    break
            else:
                if high >= sl_price:
                    trade_result = 'LOSS'
                    break
                if low <= tp_price:
                    trade_result = 'WIN'
                    break

        if trade_result is None:
            continue

        # Record trade
        results['n_trades'] += 1
        last_trade_idx = i

        if trade_result == 'WIN':
            results['wins'] += 1
            results['pnl_ticks'] += tp_ticks
            results['pnl_usd'] += tp_ticks * tick_size * point_value
        else:
            results['losses'] += 1
            results['pnl_ticks'] -= sl_ticks
            results['pnl_usd'] -= sl_ticks * tick_size * point_value

    # Calculate winrate
    results['winrate'] = 100 * results['wins'] / results['n_trades'] if results['n_trades'] > 0 else 0

    return results

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 100)
    print("   BACKTEST V10.4 - NOUVEAUX FILTRES ANTI-TRADES DE MERDE")
    print("=" * 100)

    print("""
   FILTRES TESTES:
   1. Position Filter: LONG bloque si position_in_range > 70%
                       SHORT bloque si position_in_range < 30%
   2. Distance by Score: Score 1 = max 6t, Score 2 = max 10t, Score 3 = max 15t
   3. Trend Filter V10.3: Contre-tendance bloque si score < 2

   Note: Heures toxiques (8h-9h) a tester separement via Session Quality
    """)

    all_results = {}

    for session_name in SESSIONS.keys():
        print(f"\n{'='*80}")
        print(f"   SESSION: {session_name}")
        print(f"{'='*80}")

        for symbol in SYMBOLS:
            print(f"\n   [{symbol}] Chargement...")

            train_snaps = load_snapshots(TRAINING_DAYS, symbol, session_name, show_progress=True)
            val_snaps = load_snapshots(VALIDATION_DAYS, symbol, session_name, show_progress=True)

            print(f"   -> Training: {len(train_snaps)} | Validation: {len(val_snaps)} snapshots")

            if len(train_snaps) < 100:
                print(f"   [WARN] Pas assez de donnees")
                continue

            print(f"\n   {'CONFIG':<25} | {'TR_N':>6} | {'TR_WR':>7} | {'TR_P&L':>10} | {'VAL_N':>6} | {'VAL_WR':>7} | {'VAL_P&L':>10}")
            print(f"   {'-'*90}")

            for config_name, config in CONFIGS_TO_TEST.items():
                train_res = run_backtest(train_snaps, symbol, session_name, config)
                val_res = run_backtest(val_snaps, symbol, session_name, config) if len(val_snaps) > 50 else {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0}

                print(f"   {config_name:<25} | {train_res['n_trades']:>6} | {train_res['winrate']:>6.1f}% | ${train_res['pnl_usd']:>9,.0f} | {val_res['n_trades']:>6} | {val_res['winrate']:>6.1f}% | ${val_res['pnl_usd']:>9,.0f}")

                key = f"{session_name}_{symbol}"
                if key not in all_results:
                    all_results[key] = {}
                all_results[key][config_name] = {
                    'train': train_res,
                    'val': val_res,
                }

            # Afficher rejections détaillées pour V10.4_COMPLET
            print(f"\n   Rejections V10.4_COMPLET (Training):")
            complet_res = all_results.get(f"{session_name}_{symbol}", {}).get('V10.4_COMPLET', {}).get('train', {})
            if complet_res:
                rej = complet_res.get('rejections', {})
                print(f"   - Position Filter: {rej.get('position_filter', 0)}")
                print(f"     -> LONG_HAUT_DU_RANGE: {rej.get('LONG_HAUT_DU_RANGE', 0)}")
                print(f"     -> SHORT_BAS_DU_RANGE: {rej.get('SHORT_BAS_DU_RANGE', 0)}")
                print(f"   - Distance by Score: {rej.get('distance_by_score', 0)}")
                print(f"   - Trend Filter: {rej.get('trend_filter', 0)}")

    # ==========================================================================
    # RESUME FINAL
    # ==========================================================================

    print(f"\n{'='*100}")
    print("   RESUME FINAL - COMPARAISON DES CONFIGURATIONS")
    print(f"{'='*100}")

    # Aggregate results
    totals = defaultdict(lambda: {'train_n': 0, 'train_wins': 0, 'train_pnl': 0, 'val_n': 0, 'val_wins': 0, 'val_pnl': 0})

    for key, configs in all_results.items():
        for config_name, data in configs.items():
            totals[config_name]['train_n'] += data['train']['n_trades']
            totals[config_name]['train_wins'] += data['train']['wins']
            totals[config_name]['train_pnl'] += data['train']['pnl_usd']
            totals[config_name]['val_n'] += data['val']['n_trades']
            totals[config_name]['val_wins'] += data['val']['wins']
            totals[config_name]['val_pnl'] += data['val']['pnl_usd']

    print(f"\n   {'CONFIG':<25} | {'TR_N':>6} | {'TR_WR':>7} | {'TR_P&L':>10} | {'VAL_N':>6} | {'VAL_WR':>7} | {'VAL_P&L':>10}")
    print(f"   {'-'*90}")

    for config_name in CONFIGS_TO_TEST.keys():
        t = totals[config_name]
        train_wr = 100 * t['train_wins'] / t['train_n'] if t['train_n'] > 0 else 0
        val_wr = 100 * t['val_wins'] / t['val_n'] if t['val_n'] > 0 else 0
        print(f"   {config_name:<25} | {t['train_n']:>6} | {train_wr:>6.1f}% | ${t['train_pnl']:>9,.0f} | {t['val_n']:>6} | {val_wr:>6.1f}% | ${t['val_pnl']:>9,.0f}")

    # Recommandation
    print(f"\n{'='*100}")
    print("   RECOMMANDATION")
    print(f"{'='*100}")

    # Find best config based on validation P&L
    best_config = max(totals.items(), key=lambda x: x[1]['val_pnl'])
    best_name = best_config[0]
    best_data = best_config[1]

    print(f"""
   [MEILLEURE CONFIG] {best_name}

   Training:   {best_data['train_n']} trades | WR: {100*best_data['train_wins']/best_data['train_n'] if best_data['train_n'] > 0 else 0:.1f}% | P&L: ${best_data['train_pnl']:,.0f}
   Validation: {best_data['val_n']} trades | WR: {100*best_data['val_wins']/best_data['val_n'] if best_data['val_n'] > 0 else 0:.1f}% | P&L: ${best_data['val_pnl']:,.0f}

   COMPARAISON V10.3 vs V10.4_COMPLET:
   """)

    baseline = totals['V10.3_BASELINE']
    complet = totals['V10.4_COMPLET']

    baseline_wr = 100 * baseline['train_wins'] / baseline['train_n'] if baseline['train_n'] > 0 else 0
    complet_wr = 100 * complet['train_wins'] / complet['train_n'] if complet['train_n'] > 0 else 0

    print(f"   V10.3: {baseline['train_n']} trades | WR: {baseline_wr:.1f}% | P&L: ${baseline['train_pnl']:,.0f}")
    print(f"   V10.4: {complet['train_n']} trades | WR: {complet_wr:.1f}% | P&L: ${complet['train_pnl']:,.0f}")
    print(f"")
    print(f"   Delta trades: {complet['train_n'] - baseline['train_n']}")
    print(f"   Delta WR: {complet_wr - baseline_wr:+.1f}%")
    print(f"   Delta P&L: ${complet['train_pnl'] - baseline['train_pnl']:+,.0f}")

    print(f"\n{'='*100}")

if __name__ == "__main__":
    main()

