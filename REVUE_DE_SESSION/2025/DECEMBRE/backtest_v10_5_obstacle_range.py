# -*- coding: utf-8 -*-
"""
BACKTEST V10.5 - OBSTACLE DETECTION & RANGE ADJUSTMENT
=======================================================
Test des solutions au problème HVL 0DTE identifié le 19/12/2025:
1. OBSTACLE DETECTION: Détecter niveaux entre Entry et TP
2. TP ADJUSTMENT: Ajuster TP AVANT l'obstacle
3. R:R VALIDATION: Rejeter si R:R < minimum après ajustement
4. RANGE DETECTION: Adapter les trades en contexte de range

CONFIGS TESTÉES:
- BASELINE: Configuration actuelle (sans obstacle check)
- OBSTACLE_BLOCK: Bloquer si obstacle entre entry et TP
- OBSTACLE_ADJUST: Ajuster TP avant obstacle + valider R:R
- RANGE_TP_BORNES: TP aux bornes du range détecté
- COMPLET: Obstacle adjust + Range bornes
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
    "20251212", "20251215", "20251216", "20251217", "20251218"
]

# =============================================================================
# NIVEAUX ET SCORES (Score 3 = Fort, 2 = Moyen, 1 = Faible)
# =============================================================================

# Niveaux qui peuvent être des OBSTACLES
OBSTACLE_LEVELS = {
    # SCORE 3 - FORTS (bloquent souvent le prix)
    'call_resistance': 3,
    'put_support': 3,
    'gamma_wall_level': 3,
    'hvl': 3,
    'gex_1': 3,
    'gex_2': 3,
    '1d_max': 3,
    '1d_min': 3,
    'vpoc': 3,

    # SCORE 2 - MOYENS (peuvent bloquer)
    'hvl_0dte': 2,
    'gamma_wall_0dte': 2,
    'call_resistance_0dte': 2,
    'put_support_0dte': 2,
    'gex_3': 2,
    'gex_4': 2,
    'gex_5': 2,
    'vwap': 2,
    'vah': 2,
    'val': 2,
    'ibh': 2,
    'ibl': 2,
    'vwap_up1': 2,
    'vwap_dn1': 2,

    # SCORE 1 - FAIBLES (rarement bloquants)
    'blind_spot_0': 1, 'blind_spot_1': 1, 'blind_spot_2': 1,
    'blind_spot_3': 1, 'blind_spot_4': 1, 'blind_spot_5': 1,
    'bl_0': 1, 'bl_1': 1, 'bl_2': 1, 'bl_3': 1, 'bl_4': 1,
    'bl_5': 1, 'bl_6': 1, 'bl_7': 1, 'bl_8': 1,
    'gex_6': 1, 'gex_7': 1, 'gex_8': 1,
}

# Niveaux qui peuvent être des TRIGGERS (pour entrer)
TRIGGER_LEVELS = list(OBSTACLE_LEVELS.keys())

# =============================================================================
# CONFIGURATIONS À TESTER
# =============================================================================

MIN_RR_DEFAULT = 0.7  # R:R minimum pour prendre un trade

CONFIGS_TO_TEST = {
    'BASELINE': {
        'name': 'V10.3 Actuel (sans obstacle)',
        'obstacle_check': False,
        'obstacle_adjust': False,
        'range_tp_bornes': False,
        'min_obstacle_score': 0,  # Pas utilisé
    },
    'OBSTACLE_BLOCK_ALL': {
        'name': 'Bloquer si obstacle (tous niveaux)',
        'obstacle_check': True,
        'obstacle_adjust': False,
        'range_tp_bornes': False,
        'min_obstacle_score': 1,  # Tous les niveaux
    },
    'OBSTACLE_BLOCK_S2': {
        'name': 'Bloquer si obstacle Score >= 2',
        'obstacle_check': True,
        'obstacle_adjust': False,
        'range_tp_bornes': False,
        'min_obstacle_score': 2,  # Score 2+ seulement
    },
    'OBSTACLE_BLOCK_S3': {
        'name': 'Bloquer si obstacle Score 3 (forts)',
        'obstacle_check': True,
        'obstacle_adjust': False,
        'range_tp_bornes': False,
        'min_obstacle_score': 3,  # Score 3 seulement
    },
    'OBSTACLE_ADJUST_ALL': {
        'name': 'Ajuster TP avant obstacle (tous)',
        'obstacle_check': False,
        'obstacle_adjust': True,
        'range_tp_bornes': False,
        'min_obstacle_score': 1,
        'tp_buffer_ticks': 2,  # TP = obstacle - 2 ticks
    },
    'OBSTACLE_ADJUST_S2': {
        'name': 'Ajuster TP avant obstacle (Score >= 2)',
        'obstacle_check': False,
        'obstacle_adjust': True,
        'range_tp_bornes': False,
        'min_obstacle_score': 2,
        'tp_buffer_ticks': 2,
    },
    'RANGE_TP_BORNES': {
        'name': 'TP aux bornes du range',
        'obstacle_check': False,
        'obstacle_adjust': False,
        'range_tp_bornes': True,
        'min_obstacle_score': 0,
        'range_buffer_ticks': 2,
    },
    'COMPLET_S2': {
        'name': 'Obstacle S2 adjust + Range bornes',
        'obstacle_check': False,
        'obstacle_adjust': True,
        'range_tp_bornes': True,
        'min_obstacle_score': 2,
        'tp_buffer_ticks': 2,
        'range_buffer_ticks': 2,
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

def get_level_score(level_name: str) -> int:
    return OBSTACLE_LEVELS.get(level_name, 0)

# =============================================================================
# EXTRACTION DES NIVEAUX
# =============================================================================

def extract_all_levels(snapshot: dict) -> List[Tuple[str, float, int]]:
    """Extrait tous les niveaux avec leur score."""
    levels = []

    # Niveaux directs
    for key, score in OBSTACLE_LEVELS.items():
        value = snapshot.get(key)
        if value and isinstance(value, (int, float)) and value > 0:
            levels.append((key, float(value), score))

    # VVA nested
    vva = snapshot.get('vva', {})
    if isinstance(vva, dict):
        if vva.get('vpoc'):
            levels.append(('vpoc', float(vva['vpoc']), 3))
        if vva.get('vah'):
            levels.append(('vah', float(vva['vah']), 2))
        if vva.get('val'):
            levels.append(('val', float(vva['val']), 2))

    # Structure nested
    structure = snapshot.get('structure', {})
    if isinstance(structure, dict):
        if structure.get('ibh'):
            levels.append(('ibh', float(structure['ibh']), 2))
        if structure.get('ibl'):
            levels.append(('ibl', float(structure['ibl']), 2))

    # Blind spots (bl_X)
    for i in range(9):
        bl_key = f'bl_{i}'
        bl_val = snapshot.get(bl_key)
        if bl_val and bl_val > 0:
            levels.append((bl_key, float(bl_val), 1))

    return levels

def find_trigger_level(mid: float, levels: List[Tuple[str, float, int]],
                       tick_size: float, max_distance: float = 15) -> Optional[Tuple[str, float, float, int]]:
    """Trouve le meilleur niveau déclencheur (le plus proche avec score max)."""
    valid_levels = []

    for name, price, score in levels:
        dist_ticks = abs(mid - price) / tick_size
        if dist_ticks <= max_distance:
            valid_levels.append((name, price, dist_ticks, score))

    if not valid_levels:
        return None

    # Meilleur = score max, puis distance min
    return max(valid_levels, key=lambda x: (x[3], -x[2]))

# =============================================================================
# DETECTION DES OBSTACLES
# =============================================================================

def find_obstacles_between(entry: float, tp: float, direction: str,
                           levels: List[Tuple[str, float, int]],
                           tick_size: float,
                           min_score: int = 1) -> List[Tuple[str, float, int, float]]:
    """
    Trouve les obstacles entre entry et TP.

    Returns:
        Liste de (name, price, score, distance_to_entry) triée par distance
    """
    obstacles = []

    for name, price, score in levels:
        if score < min_score:
            continue

        if direction == 'LONG':
            # Pour LONG: obstacles AU-DESSUS de entry et EN-DESSOUS de TP
            if entry < price < tp:
                dist = (price - entry) / tick_size
                obstacles.append((name, price, score, dist))
        else:
            # Pour SHORT: obstacles EN-DESSOUS de entry et AU-DESSUS de TP
            if tp < price < entry:
                dist = (entry - price) / tick_size
                obstacles.append((name, price, score, dist))

    # Trier par distance (le plus proche en premier)
    obstacles.sort(key=lambda x: x[3])
    return obstacles

# =============================================================================
# DETECTION DU RANGE
# =============================================================================

def detect_range(snapshot: dict, tick_size: float) -> Optional[Tuple[float, float, float]]:
    """
    Détecte si le prix est dans un range.

    Returns:
        (range_high, range_low, position_pct) ou None si pas de range
    """
    mid = snapshot.get('mid', 0)
    if not mid or mid <= 0:
        return None

    # Utiliser IBH/IBL comme bornes du range
    structure = snapshot.get('structure', {})
    if not isinstance(structure, dict):
        structure = {}
    ibh = structure.get('ibh', 0) or snapshot.get('ibh', 0) or 0
    ibl = structure.get('ibl', 0) or snapshot.get('ibl', 0) or 0

    # Ou utiliser HVL + BL comme dans l'exemple du 19/12
    hvl = snapshot.get('hvl_0dte', 0) or snapshot.get('hvl', 0) or 0

    # Borne basse
    range_low = hvl if hvl and hvl > 0 else (ibl if ibl and ibl > 0 else None)
    if not range_low:
        return None

    # Chercher la borne haute (bl_X le plus proche au-dessus)
    range_high = None
    for i in range(9):
        bl_val = snapshot.get(f'bl_{i}', 0)
        if bl_val and bl_val > mid:
            if range_high is None or bl_val < range_high:
                range_high = bl_val

    if not range_high:
        range_high = ibh if ibh and ibh > mid else None

    if not range_high or not range_low or range_high <= range_low:
        return None

    # Vérifier que le range est assez petit (< 50 ticks)
    range_size = (range_high - range_low) / tick_size
    if range_size > 50 or range_size < 8:
        return None

    # Calculer position dans le range
    position_pct = (mid - range_low) / (range_high - range_low) * 100

    return (range_high, range_low, position_pct)

# =============================================================================
# DETERMINATION DE LA DIRECTION
# =============================================================================

def determine_direction(snap: dict) -> str:
    """Détermine la direction du trade basé sur MIA score et delta."""
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
                                    snapshots.append(snap)
                            except:
                                continue
        except:
            continue

    return snapshots

# =============================================================================
# BACKTEST PRINCIPAL
# =============================================================================

def run_backtest(snapshots: List[Dict], symbol: str, session_name: str, config: Dict) -> Dict:
    """Execute backtest avec les filtres obstacle/range."""

    tick_size = TICK_SIZE[symbol]
    point_value = POINT_VALUE[symbol]
    default_tp_ticks = 12 if symbol == 'ES' else 15
    default_sl_ticks = 12 if symbol == 'ES' else 15

    results = {
        'n_trades': 0,
        'wins': 0,
        'losses': 0,
        'pnl_ticks': 0,
        'pnl_usd': 0,
        'rejections': defaultdict(int),
        'tp_adjustments': 0,
        'range_trades': 0,
        'avg_tp_ticks': [],
    }

    last_trade_idx = -50

    for i, snap in enumerate(snapshots):
        # Cooldown entre trades
        if i - last_trade_idx < 50:
            continue
        if i >= len(snapshots) - 100:
            continue

        mid = snap.get('mid', 0)
        if mid <= 0:
            continue

        # Extraire tous les niveaux
        levels = extract_all_levels(snap)

        # Trouver le niveau déclencheur
        trigger = find_trigger_level(mid, levels, tick_size, max_distance=15)
        if not trigger:
            continue

        trigger_name, trigger_price, trigger_dist, trigger_score = trigger

        # Déterminer direction
        direction = determine_direction(snap)

        # Calculer TP/SL par défaut
        if direction == 'LONG':
            tp_price = mid + (default_tp_ticks * tick_size)
            sl_price = mid - (default_sl_ticks * tick_size)
        else:
            tp_price = mid - (default_tp_ticks * tick_size)
            sl_price = mid + (default_sl_ticks * tick_size)

        tp_ticks = default_tp_ticks

        # =====================================================
        # FILTRE 1: OBSTACLE BLOCK
        # =====================================================
        if config.get('obstacle_check', False):
            min_score = config.get('min_obstacle_score', 1)
            obstacles = find_obstacles_between(mid, tp_price, direction, levels, tick_size, min_score)

            if obstacles:
                results['rejections']['obstacle_block'] += 1
                results['rejections'][f'blocked_by_{obstacles[0][0]}'] += 1
                continue

        # =====================================================
        # FILTRE 2: OBSTACLE ADJUST
        # =====================================================
        if config.get('obstacle_adjust', False):
            min_score = config.get('min_obstacle_score', 1)
            buffer = config.get('tp_buffer_ticks', 2)
            obstacles = find_obstacles_between(mid, tp_price, direction, levels, tick_size, min_score)

            if obstacles:
                # Prendre le premier obstacle (le plus proche)
                obstacle_name, obstacle_price, obstacle_score, obstacle_dist = obstacles[0]

                # Ajuster TP AVANT l'obstacle
                if direction == 'LONG':
                    new_tp = obstacle_price - (buffer * tick_size)
                else:
                    new_tp = obstacle_price + (buffer * tick_size)

                # Calculer nouveau R:R
                new_tp_ticks = abs(new_tp - mid) / tick_size
                sl_ticks_actual = abs(sl_price - mid) / tick_size
                new_rr = new_tp_ticks / sl_ticks_actual if sl_ticks_actual > 0 else 0

                # Vérifier R:R minimum
                if new_rr < MIN_RR_DEFAULT:
                    results['rejections']['rr_after_adjust'] += 1
                    results['rejections'][f'rr_{new_rr:.2f}_too_low'] += 1
                    continue

                # Accepter avec TP ajusté
                tp_price = new_tp
                tp_ticks = new_tp_ticks
                results['tp_adjustments'] += 1

        # =====================================================
        # FILTRE 3: RANGE TP BORNES
        # =====================================================
        if config.get('range_tp_bornes', False):
            range_info = detect_range(snap, tick_size)

            if range_info:
                range_high, range_low, position_pct = range_info
                buffer = config.get('range_buffer_ticks', 2)

                # Ajuster TP aux bornes du range
                if direction == 'LONG':
                    # TP = juste sous la borne haute
                    new_tp = range_high - (buffer * tick_size)
                    if new_tp > mid:  # Vérifier que TP est au-dessus de entry
                        new_tp_ticks = (new_tp - mid) / tick_size
                        sl_ticks_actual = abs(sl_price - mid) / tick_size
                        new_rr = new_tp_ticks / sl_ticks_actual if sl_ticks_actual > 0 else 0

                        if new_rr >= MIN_RR_DEFAULT:
                            tp_price = new_tp
                            tp_ticks = new_tp_ticks
                            results['range_trades'] += 1
                        else:
                            results['rejections']['range_rr_too_low'] += 1
                            continue
                else:
                    # TP = juste au-dessus de la borne basse
                    new_tp = range_low + (buffer * tick_size)
                    if new_tp < mid:  # Vérifier que TP est en-dessous de entry
                        new_tp_ticks = (mid - new_tp) / tick_size
                        sl_ticks_actual = abs(sl_price - mid) / tick_size
                        new_rr = new_tp_ticks / sl_ticks_actual if sl_ticks_actual > 0 else 0

                        if new_rr >= MIN_RR_DEFAULT:
                            tp_price = new_tp
                            tp_ticks = new_tp_ticks
                            results['range_trades'] += 1
                        else:
                            results['rejections']['range_rr_too_low'] += 1
                            continue

        # =====================================================
        # SIMULATION DU TRADE
        # =====================================================

        results['avg_tp_ticks'].append(tp_ticks)

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
            results['pnl_ticks'] -= default_sl_ticks
            results['pnl_usd'] -= default_sl_ticks * tick_size * point_value

    # Calculate stats
    results['winrate'] = 100 * results['wins'] / results['n_trades'] if results['n_trades'] > 0 else 0
    results['avg_tp'] = sum(results['avg_tp_ticks']) / len(results['avg_tp_ticks']) if results['avg_tp_ticks'] else 0

    return results

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 100)
    print("   BACKTEST V10.5 - OBSTACLE DETECTION & RANGE ADJUSTMENT")
    print("   Analyse du problème HVL 0DTE du 19/12/2025")
    print("=" * 100)

    print("""
   PROBLÈME IDENTIFIÉ:
   - Trade ES SHORT @ 6851.38 avec TP @ 6848.38
   - HVL 0DTE @ 6850.00 était ENTRE entry et TP
   - Le système n'a pas détecté cet obstacle

   SOLUTIONS TESTÉES:
   1. OBSTACLE_BLOCK: Bloquer si obstacle entre entry et TP
   2. OBSTACLE_ADJUST: Ajuster TP AVANT l'obstacle + valider R:R
   3. RANGE_TP_BORNES: Adapter TP aux bornes du range détecté
   4. COMPLET: Combiner obstacle adjust + range bornes
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
                print(f"   [WARN] Pas assez de données")
                continue

            print(f"\n   {'CONFIG':<28} | {'TR_N':>5} | {'TR_WR':>6} | {'TR_P&L':>9} | {'VAL_N':>5} | {'VAL_WR':>6} | {'VAL_P&L':>9} | {'ADJ':>4} | {'RNG':>4}")
            print(f"   {'-'*105}")

            for config_name, config in CONFIGS_TO_TEST.items():
                train_res = run_backtest(train_snaps, symbol, session_name, config)
                val_res = run_backtest(val_snaps, symbol, session_name, config) if len(val_snaps) > 50 else {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0, 'tp_adjustments': 0, 'range_trades': 0}

                print(f"   {config_name:<28} | {train_res['n_trades']:>5} | {train_res['winrate']:>5.1f}% | ${train_res['pnl_usd']:>8,.0f} | {val_res['n_trades']:>5} | {val_res['winrate']:>5.1f}% | ${val_res['pnl_usd']:>8,.0f} | {train_res.get('tp_adjustments', 0):>4} | {train_res.get('range_trades', 0):>4}")

                key = f"{session_name}_{symbol}"
                if key not in all_results:
                    all_results[key] = {}
                all_results[key][config_name] = {
                    'train': train_res,
                    'val': val_res,
                }

    # ==========================================================================
    # RESUME FINAL
    # ==========================================================================

    print(f"\n{'='*100}")
    print("   RESUME FINAL - TOUTES SESSIONS COMBINÉES")
    print(f"{'='*100}")

    # Aggreger les résultats
    totals = defaultdict(lambda: {'train_n': 0, 'train_wins': 0, 'train_pnl': 0,
                                   'val_n': 0, 'val_wins': 0, 'val_pnl': 0,
                                   'adjustments': 0, 'range_trades': 0})

    for key, configs in all_results.items():
        for config_name, data in configs.items():
            totals[config_name]['train_n'] += data['train']['n_trades']
            totals[config_name]['train_wins'] += data['train']['wins']
            totals[config_name]['train_pnl'] += data['train']['pnl_usd']
            totals[config_name]['val_n'] += data['val']['n_trades']
            totals[config_name]['val_wins'] += data['val']['wins']
            totals[config_name]['val_pnl'] += data['val']['pnl_usd']
            totals[config_name]['adjustments'] += data['train'].get('tp_adjustments', 0)
            totals[config_name]['range_trades'] += data['train'].get('range_trades', 0)

    print(f"\n   {'CONFIG':<28} | {'TR_N':>5} | {'TR_WR':>6} | {'TR_P&L':>10} | {'VAL_N':>5} | {'VAL_WR':>6} | {'VAL_P&L':>10}")
    print(f"   {'-'*95}")

    for config_name in CONFIGS_TO_TEST.keys():
        t = totals[config_name]
        train_wr = 100 * t['train_wins'] / t['train_n'] if t['train_n'] > 0 else 0
        val_wr = 100 * t['val_wins'] / t['val_n'] if t['val_n'] > 0 else 0
        print(f"   {config_name:<28} | {t['train_n']:>5} | {train_wr:>5.1f}% | ${t['train_pnl']:>9,.0f} | {t['val_n']:>5} | {val_wr:>5.1f}% | ${t['val_pnl']:>9,.0f}")

    # ==========================================================================
    # RECOMMANDATION
    # ==========================================================================

    print(f"\n{'='*100}")
    print("   RECOMMANDATION")
    print(f"{'='*100}")

    # Comparer BASELINE vs BEST
    baseline = totals['BASELINE']
    baseline_pnl = baseline['val_pnl']

    best_config = None
    best_improvement = 0

    for config_name, data in totals.items():
        if config_name == 'BASELINE':
            continue
        improvement = data['val_pnl'] - baseline_pnl
        if improvement > best_improvement:
            best_improvement = improvement
            best_config = config_name

    print(f"""
   BASELINE (actuel):
   - Training: {baseline['train_n']} trades | WR: {100*baseline['train_wins']/baseline['train_n'] if baseline['train_n'] > 0 else 0:.1f}% | P&L: ${baseline['train_pnl']:,.0f}
   - Validation: {baseline['val_n']} trades | WR: {100*baseline['val_wins']/baseline['val_n'] if baseline['val_n'] > 0 else 0:.1f}% | P&L: ${baseline['val_pnl']:,.0f}
    """)

    if best_config:
        best = totals[best_config]
        print(f"""
   MEILLEURE CONFIG: {best_config}
   - Training: {best['train_n']} trades | WR: {100*best['train_wins']/best['train_n'] if best['train_n'] > 0 else 0:.1f}% | P&L: ${best['train_pnl']:,.0f}
   - Validation: {best['val_n']} trades | WR: {100*best['val_wins']/best['val_n'] if best['val_n'] > 0 else 0:.1f}% | P&L: ${best['val_pnl']:,.0f}

   AMÉLIORATION:
   - Delta P&L Validation: ${best_improvement:+,.0f}
   - TP Adjustments: {best['adjustments']}
   - Range Trades: {best['range_trades']}
        """)
    else:
        print("""
   ⚠️ AUCUNE CONFIG N'AMÉLIORE LE BASELINE
   → Garder la config actuelle (sans obstacle check)
        """)

    print(f"\n{'='*100}")

if __name__ == "__main__":
    main()
