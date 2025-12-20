# -*- coding: utf-8 -*-
"""
===============================================================================
    BACKTEST V10 - TEST DES NOUVEAUX SEUILS

    Seuils à tester:
    - MenthorQ  >= 0.50
    - OrderFlow >= 0.20
    - Context   >= 0.14
    - Confluence >= 0.96

    Date: 18 Décembre 2025
===============================================================================
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# ===============================================================================
#                           CONFIGURATION DES DONNEES
# ===============================================================================

BASE_DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

# TRAINING SET (80%) - 22 jours
TRAINING_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127",
    "20251201", "20251202", "20251203", "20251204", "20251205",
]

# VALIDATION SET (20%) - 7 jours
VALIDATION_DAYS = [
    "20251208", "20251209", "20251210", "20251211", "20251212",
    "20251215", "20251216", "20251217",
]

# ===============================================================================
#                           SESSIONS ET SYMBOLES
# ===============================================================================

SESSIONS = {
    'LONDON': {'start': (8, 0), 'end': (11, 0)},
    'US_MORNING': {'start': (15, 50), 'end': (17, 0)},
    'POWER_HOUR': {'start': (20, 0), 'end': (21, 25)},
}

SYMBOLS = ['ES', 'NQ']

CHART_MAPPING = {"ES": 3, "NQ": 9, "RTY": 1}

# ===============================================================================
#                           NIVEAUX PREMIUM
# ===============================================================================

ALL_PREMIUM_LEVELS = [
    'gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap',
    'gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
    'call_resistance', 'put_support', 'blind_spot_1', 'blind_spot_2',
    'vwap_up1', 'vwap_dn1', 'call_resistance_0dte', 'put_support_0dte',
    'blind_spot_3', 'blind_spot_4',
]

LEVEL_SCORES = {
    'gex_1': 3, 'gex_2': 3, 'hvl': 3, 'gamma_wall_level': 3, 'vwap': 3,
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2, 'hvl_0dte': 2, 'gamma_wall_0dte': 2,
    'call_resistance': 2, 'put_support': 2, 'blind_spot_1': 2, 'blind_spot_2': 2,
    'vwap_up1': 2, 'vwap_dn1': 2, 'call_resistance_0dte': 1, 'put_support_0dte': 1,
    'blind_spot_3': 1, 'blind_spot_4': 1,
}

# ===============================================================================
#                           CONFIG DE BASE PAR SYMBOLE
# ===============================================================================

BASE_CONFIG = {
    'ES': {'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15, 'tick_size': 0.25, 'tick_value': 12.50},
    'NQ': {'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20, 'tick_size': 0.25, 'tick_value': 5.00},
}

# ===============================================================================
#                           CONFIGURATIONS A TESTER
# ===============================================================================

CONFIGS_TO_TEST = {
    'ACTUEL': {
        'name': 'Config Actuelle',
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.20,   # MenthorQ
        'min_layer2': 0.17,   # OrderFlow
        'min_layer3': 0.12,   # Context
    },
    'NOUVEAUX_SEUILS': {
        'name': 'Nouveaux Seuils (à tester)',
        'min_confluence': 1,   # Confluence >= 0.96 => min 1 niveau
        'max_distance': 15,
        'min_layer1': 0.50,   # MenthorQ >= 0.50
        'min_layer2': 0.20,   # OrderFlow >= 0.20
        'min_layer3': 0.14,   # Context >= 0.14
    },
    'MODERE': {
        'name': 'Seuils Modérés',
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.58,
        'min_layer2': 0.22,
        'min_layer3': 0.16,
    },
    'ORDERFLOW_FOCUS': {
        'name': 'Focus OrderFlow',
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.30,
        'min_layer2': 0.20,
        'min_layer3': 0.12,
    },
}

# ===============================================================================
#                           FONCTIONS UTILITAIRES
# ===============================================================================

def get_level_score(level_name: str) -> int:
    if level_name in LEVEL_SCORES:
        return LEVEL_SCORES[level_name]
    if level_name.startswith('gex_'):
        try:
            num = int(level_name.split('_')[1])
            return 3 if num <= 2 else (2 if num <= 5 else 1)
        except:
            return 1
    if level_name.startswith('blind_spot_'):
        try:
            num = int(level_name.split('_')[2])
            return 2 if num <= 2 else 1
        except:
            return 1
    return 0

def is_in_session(timestamp_ms: int, session_name: str) -> bool:
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        time_val = dt.hour * 60 + dt.minute
        session = SESSIONS.get(session_name)
        if not session:
            return False
        start = session['start'][0] * 60 + session['start'][1]
        end = session['end'][0] * 60 + session['end'][1]
        return start <= time_val < end
    except:
        return False

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
    for i in range(9):
        key = f'blind_spot_{i}'
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass
    for i in range(1, 11):
        key = f'gex_{i}'
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass
    return levels

def find_levels_in_range(mid: float, levels: List, max_distance: int, tick_size: float = 0.25) -> List[Tuple]:
    valid_levels = []
    for level_name, level_price, level_score in levels:
        dist_ticks = abs(mid - level_price) / tick_size
        if dist_ticks <= max_distance:
            valid_levels.append((level_name, level_price, dist_ticks, level_score))
    return valid_levels

# ===============================================================================
#                   CALCUL DES LAYER SCORES
# ===============================================================================

def calculate_layer1_score(snap: dict, levels_in_range: List) -> float:
    """Layer 1 = MenthorQ (50%)"""
    if not levels_in_range:
        return 0.0
    nearest = min(levels_in_range, key=lambda x: x[2])
    dist = nearest[2]
    level_score = nearest[3]
    dist_score = max(0.0, 1.0 - dist / 25.0)
    level_boost = 1.3 if level_score == 3 else (1.1 if level_score == 2 else 1.0)
    confluence_bonus = min(0.2, len(levels_in_range) * 0.05)
    return min(1.0, dist_score * level_boost + confluence_bonus)

def calculate_layer2_score(snap: dict) -> float:
    """Layer 2 = OrderFlow (30%)"""
    delta = abs(snap.get('delta', 0) or 0)
    cum_delta = abs(snap.get('cum_delta_session', snap.get('cum_delta', 0)) or 0)
    imbalance = abs(snap.get('level1_imbalance', snap.get('imbalance', 0)) or 0)
    delta_score = min(1.0, delta / 500.0)
    cum_score = min(1.0, cum_delta / 2000.0)
    imb_score = min(1.0, imbalance * 5.0)
    return delta_score * 0.4 + cum_score * 0.4 + imb_score * 0.2

def calculate_layer3_score(snap: dict, direction: str) -> float:
    """Layer 3 = Context (20%)"""
    pos_range = snap.get('position_in_range', 50) or 50
    mia = snap.get('mia_bullish_score', 0) or 0
    if direction == 'LONG' and pos_range > 70:
        return 0.10
    if direction == 'SHORT' and pos_range < 30:
        return 0.10
    if direction == 'LONG' and pos_range < 40:
        return 0.25
    if direction == 'SHORT' and pos_range > 60:
        return 0.25
    if direction == 'LONG' and mia > 0.2:
        return 0.22
    if direction == 'SHORT' and mia < -0.2:
        return 0.22
    return 0.18

# ===============================================================================
#                   SIMULATION DE TRADE
# ===============================================================================

def simulate_trade(entry: float, direction: str, tp_ticks: int, sl_ticks: int,
                   future_snapshots: List[Dict], tick_size: float) -> Dict:
    tp = entry + (tp_ticks * tick_size) if direction == 'LONG' else entry - (tp_ticks * tick_size)
    sl = entry - (sl_ticks * tick_size) if direction == 'LONG' else entry + (sl_ticks * tick_size)

    for i, future_snap in enumerate(future_snapshots):
        high = future_snap.get('high', entry)
        low = future_snap.get('low', entry)

        if direction == 'LONG':
            if high >= tp:
                return {'win': True, 'pnl_ticks': tp_ticks, 'exit': 'TP', 'duration': i}
            if low <= sl:
                return {'win': False, 'pnl_ticks': -sl_ticks, 'exit': 'SL', 'duration': i}
        else:
            if low <= tp:
                return {'win': True, 'pnl_ticks': tp_ticks, 'exit': 'TP', 'duration': i}
            if high >= sl:
                return {'win': False, 'pnl_ticks': -sl_ticks, 'exit': 'SL', 'duration': i}

    if future_snapshots:
        last_mid = future_snapshots[-1].get('mid', entry)
        pnl = (last_mid - entry) / tick_size if direction == 'LONG' else (entry - last_mid) / tick_size
        return {'win': pnl > 0, 'pnl_ticks': pnl, 'exit': 'TIMEOUT', 'duration': len(future_snapshots)}

    return {'win': False, 'pnl_ticks': 0, 'exit': 'NO_DATA', 'duration': 0}

# ===============================================================================
#                           CHARGEMENT DES DONNEES
# ===============================================================================

def load_snapshots(days: List[str], symbol: str, session_name: str) -> List[Dict]:
    snapshots = []
    chart_id = CHART_MAPPING.get(symbol, 3)
    MONTHS = {"11": "NOVEMBRE", "12": "DECEMBRE"}

    for day in days:
        try:
            month_num = day[4:6]
            month_name = MONTHS.get(month_num, "NOVEMBRE")
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
        except Exception as e:
            continue

    return snapshots

# ===============================================================================
#                           BACKTEST
# ===============================================================================

def run_backtest(snapshots: List[Dict], symbol: str, params: Dict) -> Dict:
    cfg = BASE_CONFIG[symbol]
    tick_size = cfg['tick_size']
    tick_value = cfg['tick_value']
    tp_ticks = cfg['tp_ticks']
    sl_ticks = cfg['sl_ticks']
    cooldown_ms = cfg['cooldown_min'] * 60 * 1000

    min_confluence = params.get('min_confluence', 1)
    max_distance = params.get('max_distance', 15)
    min_layer1 = params.get('min_layer1', 0.30)
    min_layer2 = params.get('min_layer2', 0.15)
    min_layer3 = params.get('min_layer3', 0.15)

    results = {
        'n_trades': 0, 'n_wins': 0, 'n_losses': 0,
        'pnl_ticks': 0, 'pnl_usd': 0, 'signals': 0,
        'rejections': defaultdict(int),
    }

    last_trade_time = 0

    for i, snap in enumerate(snapshots):
        t_ms = snap.get('t_ms', 0)
        mid = snap.get('mid', 0)

        if not mid or mid <= 0:
            continue

        if t_ms - last_trade_time < cooldown_ms:
            continue

        results['signals'] += 1

        mia_score = snap.get('mia_bullish_score', 0) or 0
        direction = 'LONG' if mia_score > 0 else 'SHORT'

        levels = extract_levels_from_snapshot(snap)
        valid_levels = find_levels_in_range(mid, levels, max_distance, tick_size)

        layer1_score = calculate_layer1_score(snap, valid_levels)
        layer2_score = calculate_layer2_score(snap)
        layer3_score = calculate_layer3_score(snap, direction)

        # Validations
        if len(valid_levels) < min_confluence:
            results['rejections']['confluence'] += 1
            continue
        if layer1_score < min_layer1:
            results['rejections']['layer1'] += 1
            continue
        if layer2_score < min_layer2:
            results['rejections']['layer2'] += 1
            continue
        if layer3_score < min_layer3:
            results['rejections']['layer3'] += 1
            continue

        # Trade accepté
        future_snaps = snapshots[i+1:i+301]
        if len(future_snaps) < 10:
            continue

        trade = simulate_trade(mid, direction, tp_ticks, sl_ticks, future_snaps, tick_size)

        results['n_trades'] += 1
        results['pnl_ticks'] += trade['pnl_ticks']

        if trade['win']:
            results['n_wins'] += 1
        else:
            results['n_losses'] += 1

        last_trade_time = t_ms

    results['pnl_usd'] = results['pnl_ticks'] * tick_value
    results['winrate'] = (results['n_wins'] / results['n_trades'] * 100) if results['n_trades'] > 0 else 0

    return results

# ===============================================================================
#                           MAIN
# ===============================================================================

def main():
    print("=" * 100)
    print("   BACKTEST V10 - TEST DES NOUVEAUX SEUILS")
    print("=" * 100)
    print(f"\n   Seuils à tester:")
    print(f"   - MenthorQ  >= 0.50")
    print(f"   - OrderFlow >= 0.20")
    print(f"   - Context   >= 0.14")
    print(f"   - Confluence >= 0.96 (min 1 niveau)")
    print(f"\n   Training: {len(TRAINING_DAYS)} jours | Validation: {len(VALIDATION_DAYS)} jours")
    print(f"   Sessions: {list(SESSIONS.keys())}")
    print("=" * 100)

    all_results = {}

    # Test par session
    for session_name in SESSIONS.keys():
        print(f"\n{'='*80}")
        print(f"   SESSION: {session_name}")
        print(f"{'='*80}")

        for symbol in SYMBOLS:
            print(f"\n   [{symbol}] Chargement des données...")

            train_snaps = load_snapshots(TRAINING_DAYS, symbol, session_name)
            val_snaps = load_snapshots(VALIDATION_DAYS, symbol, session_name)

            print(f"   -> Training: {len(train_snaps)} snapshots | Validation: {len(val_snaps)} snapshots")

            if len(train_snaps) < 100:
                print(f"   ⚠️ Pas assez de données")
                continue

            # Test de chaque configuration
            print(f"\n   {'CONFIG':<20} | {'TRAIN':>10} | {'TR_WR':>7} | {'TR_P&L':>10} | {'VAL':>8} | {'V_WR':>7} | {'V_P&L':>10}")
            print(f"   {'-'*90}")

            for config_name, params in CONFIGS_TO_TEST.items():
                train_res = run_backtest(train_snaps, symbol, params)
                val_res = run_backtest(val_snaps, symbol, params) if len(val_snaps) > 50 else {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0}

                print(f"   {config_name:<20} | {train_res['n_trades']:>10} | {train_res['winrate']:>6.1f}% | ${train_res['pnl_usd']:>9,.0f} | {val_res['n_trades']:>8} | {val_res['winrate']:>6.1f}% | ${val_res['pnl_usd']:>9,.0f}")

                key = f"{session_name}_{symbol}"
                if key not in all_results:
                    all_results[key] = {}
                all_results[key][config_name] = {
                    'train': train_res,
                    'val': val_res,
                }

    # ===============================================================================
    #                           RESUME FINAL
    # ===============================================================================

    print(f"\n{'='*100}")
    print("   RESUME FINAL - COMPARAISON DES CONFIGURATIONS")
    print(f"{'='*100}")

    # Calculer les totaux par config
    totals = defaultdict(lambda: {'train_trades': 0, 'train_wins': 0, 'train_pnl': 0,
                                   'val_trades': 0, 'val_wins': 0, 'val_pnl': 0})

    for session_symbol, configs in all_results.items():
        for config_name, results in configs.items():
            totals[config_name]['train_trades'] += results['train']['n_trades']
            totals[config_name]['train_wins'] += results['train']['n_wins']
            totals[config_name]['train_pnl'] += results['train']['pnl_usd']
            totals[config_name]['val_trades'] += results['val']['n_trades']
            totals[config_name]['val_wins'] += results['val']['n_wins']
            totals[config_name]['val_pnl'] += results['val']['pnl_usd']

    print(f"\n   {'CONFIG':<20} | {'TRAIN TRADES':>12} | {'TRAIN WR':>9} | {'TRAIN P&L':>12} | {'VAL TRADES':>10} | {'VAL WR':>8} | {'VAL P&L':>10}")
    print(f"   {'-'*100}")

    for config_name, totals_data in totals.items():
        train_wr = (totals_data['train_wins'] / totals_data['train_trades'] * 100) if totals_data['train_trades'] > 0 else 0
        val_wr = (totals_data['val_wins'] / totals_data['val_trades'] * 100) if totals_data['val_trades'] > 0 else 0

        print(f"   {config_name:<20} | {totals_data['train_trades']:>12} | {train_wr:>8.1f}% | ${totals_data['train_pnl']:>10,.0f} | {totals_data['val_trades']:>10} | {val_wr:>7.1f}% | ${totals_data['val_pnl']:>9,.0f}")

    # Recommandation
    print(f"\n{'='*100}")
    print("   RECOMMANDATION")
    print(f"{'='*100}")

    # Trouver la meilleure config
    best_config = max(totals.items(), key=lambda x: x[1]['val_pnl'] if x[1]['val_trades'] > 10 else x[1]['train_pnl'])

    print(f"\n   [GAGNANT] {best_config[0]}")
    print(f"   P&L Validation: ${best_config[1]['val_pnl']:,.0f}")

    # Afficher les seuils
    if best_config[0] in CONFIGS_TO_TEST:
        cfg = CONFIGS_TO_TEST[best_config[0]]
        print(f"\n   Seuils:")
        print(f"   - MenthorQ  >= {cfg['min_layer1']:.2f}")
        print(f"   - OrderFlow >= {cfg['min_layer2']:.2f}")
        print(f"   - Context   >= {cfg['min_layer3']:.2f}")

    print(f"\n{'='*100}")

if __name__ == "__main__":
    main()

