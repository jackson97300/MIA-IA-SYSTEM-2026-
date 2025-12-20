# -*- coding: utf-8 -*-
"""
===============================================================================
    BACKTEST V10.3.1 - VERSION COMPLETE CORRIGÉE

    CORRECTIONS APPLIQUÉES:
    ✅ Filtre contre-tendance V10.3 (Score 2+ exception)
    ✅ VPOC, VAH, VAL extraits de snap['vva']
    ✅ IBH, IBL extraits de snap['structure']
    ✅ blind_spot_0 à blind_spot_8
    ✅ min_level_score par session
    ✅ V10.3 comme baseline de comparaison
    ✅ Affichage des rejections par type

    Seuils à tester:
    - MenthorQ  >= 0.50
    - OrderFlow >= 0.20
    - Context   >= 0.14

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

# Barre de progression simple
def progress_bar(current, total, prefix='', suffix='', length=40):
    percent = 100 * current / total if total > 0 else 0
    filled = int(length * current // total) if total > 0 else 0
    bar = '#' * filled + '-' * (length - filled)
    sys.stdout.write(f'\r   {prefix} [{bar}] {percent:.0f}% {suffix}')
    sys.stdout.flush()
    if current >= total:
        print()

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

# VALIDATION SET (20%) - 8 jours
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
#                    CONFIG PAR SESSION (V10.3)
# ===============================================================================

SESSION_CONFIGS = {
    'LONDON_ES': {'min_level_score': 2, 'max_distance': 15, 'enabled': True},
    'LONDON_NQ': {'min_level_score': 2, 'max_distance': 15, 'enabled': False},  # Désactivé
    'US_MORNING_ES': {'min_level_score': 0, 'max_distance': 12, 'enabled': True},
    'US_MORNING_NQ': {'min_level_score': 0, 'max_distance': 15, 'enabled': True},
    'POWER_HOUR_ES': {'min_level_score': 0, 'max_distance': 10, 'enabled': True},
    'POWER_HOUR_NQ': {'min_level_score': 2, 'max_distance': 15, 'enabled': True},
}

# ===============================================================================
#                   NIVEAUX PREMIUM COMPLETS (39 niveaux)
# ===============================================================================

ALL_PREMIUM_LEVELS = [
    # SCORE 3 - FORTS (8 niveaux)
    'gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap',
    'vpoc', '1d_max', '1d_min',

    # SCORE 2 - MOYENS (16 niveaux)
    'gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
    'call_resistance', 'put_support',
    'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
    'vwap_up1', 'vwap_dn1',
    'vah', 'val', 'ibh', 'ibl',

    # SCORE 1 - FAIBLES (15 niveaux)
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    'call_resistance_0dte', 'put_support_0dte',
    'blind_spot_3', 'blind_spot_4', 'blind_spot_5',
    'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
    'vwap_up2', 'vwap_dn2',
]

LEVEL_SCORES = {
    # SCORE 3
    'gex_1': 3, 'gex_2': 3, 'hvl': 3, 'gamma_wall_level': 3, 'vwap': 3,
    'vpoc': 3, '1d_max': 3, '1d_min': 3,

    # SCORE 2
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2, 'hvl_0dte': 2, 'gamma_wall_0dte': 2,
    'call_resistance': 2, 'put_support': 2,
    'blind_spot_0': 2, 'blind_spot_1': 2, 'blind_spot_2': 2,
    'vwap_up1': 2, 'vwap_dn1': 2,
    'vah': 2, 'val': 2, 'ibh': 2, 'ibl': 2,

    # SCORE 1
    'gex_6': 1, 'gex_7': 1, 'gex_8': 1, 'gex_9': 1, 'gex_10': 1,
    'call_resistance_0dte': 1, 'put_support_0dte': 1,
    'blind_spot_3': 1, 'blind_spot_4': 1, 'blind_spot_5': 1,
    'blind_spot_6': 1, 'blind_spot_7': 1, 'blind_spot_8': 1,
    'vwap_up2': 1, 'vwap_dn2': 1,
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
    'V10.3_BASELINE': {
        'name': 'V10.3 Actuel (baseline)',
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.20,   # MenthorQ
        'min_layer2': 0.17,   # OrderFlow
        'min_layer3': 0.12,   # Context
    },
    'NOUVEAUX_SEUILS': {
        'name': 'Nouveaux Seuils (analyse trades gagnants)',
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.50,   # MenthorQ >= 0.50
        'min_layer2': 0.20,   # OrderFlow >= 0.20
        'min_layer3': 0.14,   # Context >= 0.14
    },
    'MODERE': {
        'name': 'Seuils Modérés (entre les deux)',
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.35,
        'min_layer2': 0.18,
        'min_layer3': 0.13,
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

# ===============================================================================
#              EXTRACTION DES NIVEAUX CORRIGÉE (VVA + STRUCTURE)
# ===============================================================================

def extract_levels_from_snapshot(snapshot: dict) -> List[Tuple[str, float, int]]:
    """Extrait TOUS les niveaux, y compris VVA et STRUCTURE."""
    levels = []
    added = set()  # Pour éviter les doublons

    # 1. Niveaux directs
    for key in ALL_PREMIUM_LEVELS:
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0 and key not in added:
                    levels.append((key, price, get_level_score(key)))
                    added.add(key)
            except:
                pass

    # 2. VVA (Value Area) - VPOC, VAH, VAL
    vva = snapshot.get('vva', {})
    if isinstance(vva, dict):
        if vva.get('vpoc') and 'vpoc' not in added:
            try:
                levels.append(('vpoc', float(vva['vpoc']), 3))
                added.add('vpoc')
            except:
                pass
        if vva.get('vah') and 'vah' not in added:
            try:
                levels.append(('vah', float(vva['vah']), 2))
                added.add('vah')
            except:
                pass
        if vva.get('val') and 'val' not in added:
            try:
                levels.append(('val', float(vva['val']), 2))
                added.add('val')
            except:
                pass

    # 3. Structure (IBH, IBL, ONH, ONL)
    structure = snapshot.get('structure', {})
    if isinstance(structure, dict):
        if structure.get('ibh') and 'ibh' not in added:
            try:
                levels.append(('ibh', float(structure['ibh']), 2))
                added.add('ibh')
            except:
                pass
        if structure.get('ibl') and 'ibl' not in added:
            try:
                levels.append(('ibl', float(structure['ibl']), 2))
                added.add('ibl')
            except:
                pass

    # 4. Blind spots (0 à 8)
    for i in range(9):
        key = f'blind_spot_{i}'
        if key in snapshot and snapshot[key] and key not in added:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
                    added.add(key)
            except:
                pass

    # 5. GEX (1 à 10)
    for i in range(1, 11):
        key = f'gex_{i}'
        if key in snapshot and snapshot[key] and key not in added:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
                    added.add(key)
            except:
                pass

    return levels

def find_levels_in_range(mid: float, levels: List, max_distance: int,
                         tick_size: float = 0.25, min_level_score: int = 0) -> List[Tuple]:
    """Trouve les niveaux dans le range avec filtre min_level_score."""
    valid_levels = []
    for level_name, level_price, level_score in levels:
        # Filtre par score minimum
        if level_score < min_level_score:
            continue
        dist_ticks = abs(mid - level_price) / tick_size
        if dist_ticks <= max_distance:
            valid_levels.append((level_name, level_price, dist_ticks, level_score))
    return valid_levels

# ===============================================================================
#              FILTRE CONTRE-TENDANCE V10.3
# ===============================================================================

def check_trend_filter(snap: dict, direction: str, level_score: int) -> Tuple[bool, str]:
    """
    Filtre contre-tendance V10.3:
    - Score 2+ = rebonds autorisés (24 niveaux MenthorQ)
    - Score 1 = filtre tendance actif
    """
    mid = snap.get('mid', 0)
    hvl = snap.get('hvl', 0)
    vwap = snap.get('vwap', 0)

    if not hvl or not vwap or not mid:
        return True, "NO_HVL_VWAP"

    above_hvl = mid > hvl
    above_vwap = mid > vwap

    # Déterminer tendance
    if above_hvl and above_vwap:
        trend = 'BULLISH'
    elif not above_hvl and not above_vwap:
        trend = 'BEARISH'
    else:
        trend = 'NEUTRAL'

    # ✅ V10.3: Score 2+ = rebonds autorisés
    if level_score >= 2:
        return True, f"SCORE_{level_score}_ALLOWED"

    # Score 1: Filtre actif (bloque contre-tendance)
    if trend == 'BEARISH' and direction == 'LONG':
        return False, "LONG_BLOCKED_BEARISH"
    if trend == 'BULLISH' and direction == 'SHORT':
        return False, "SHORT_BLOCKED_BULLISH"

    return True, "WITH_TREND"

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

def load_snapshots(days: List[str], symbol: str, session_name: str, show_progress: bool = False) -> List[Dict]:
    snapshots = []
    chart_id = CHART_MAPPING.get(symbol, 3)
    MONTHS = {"11": "NOVEMBRE", "12": "DECEMBRE"}

    for idx, day in enumerate(days):
        if show_progress:
            progress_bar(idx + 1, len(days), f'Loading {symbol}', f'{day}')
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
#                           BACKTEST COMPLET V10.3.1
# ===============================================================================

def run_backtest(snapshots: List[Dict], symbol: str, session_name: str, params: Dict) -> Dict:
    cfg = BASE_CONFIG[symbol]
    tick_size = cfg['tick_size']
    tick_value = cfg['tick_value']
    tp_ticks = cfg['tp_ticks']
    sl_ticks = cfg['sl_ticks']
    cooldown_ms = cfg['cooldown_min'] * 60 * 1000

    # Config session
    session_key = f"{session_name}_{symbol}"
    session_cfg = SESSION_CONFIGS.get(session_key, {})
    min_level_score = session_cfg.get('min_level_score', 0)
    max_distance = session_cfg.get('max_distance', params.get('max_distance', 15))

    min_confluence = params.get('min_confluence', 1)
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

        # Extraire TOUS les niveaux (y compris VVA et structure)
        levels = extract_levels_from_snapshot(snap)

        # Trouver niveaux dans le range avec min_level_score
        valid_levels = find_levels_in_range(mid, levels, max_distance, tick_size, min_level_score)

        # Calculer les scores
        layer1_score = calculate_layer1_score(snap, valid_levels)
        layer2_score = calculate_layer2_score(snap)
        layer3_score = calculate_layer3_score(snap, direction)

        # Trouver le meilleur niveau
        if valid_levels:
            best_level = max(valid_levels, key=lambda x: (x[3], -x[2]))
            best_level_score = best_level[3]
        else:
            best_level_score = 0

        # ✅ FILTRE CONTRE-TENDANCE V10.3
        trend_ok, trend_reason = check_trend_filter(snap, direction, best_level_score)
        if not trend_ok:
            results['rejections']['trend_filter'] += 1
            continue

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
    print("   BACKTEST V10.3.1 - VERSION COMPLETE CORRIGÉE")
    print("=" * 100)
    print(f"\n   [OK] Corrections appliquees:")
    print(f"   - Filtre contre-tendance V10.3 (Score 2+ exception)")
    print(f"   - VPOC, VAH, VAL extraits de snap['vva']")
    print(f"   - IBH, IBL extraits de snap['structure']")
    print(f"   - blind_spot_0 a blind_spot_8")
    print(f"   - min_level_score par session")
    print(f"\n   Seuils à tester:")
    print(f"   - V10.3 Baseline: L1=0.20, L2=0.17, L3=0.12")
    print(f"   - Nouveaux:       L1=0.50, L2=0.20, L3=0.14")
    print(f"\n   Training: {len(TRAINING_DAYS)} jours | Validation: {len(VALIDATION_DAYS)} jours")
    print("=" * 100)

    all_results = {}

    # Test par session
    for session_name in SESSIONS.keys():
        print(f"\n{'='*80}")
        print(f"   SESSION: {session_name}")
        print(f"{'='*80}")

        for symbol in SYMBOLS:
            session_key = f"{session_name}_{symbol}"
            session_cfg = SESSION_CONFIGS.get(session_key, {})

            if not session_cfg.get('enabled', True):
                print(f"\n   [{symbol}] [SKIP] DESACTIVE (min_level_score={session_cfg.get('min_level_score', 0)})")
                continue

            print(f"\n   [{symbol}] Chargement (min_level_score={session_cfg.get('min_level_score', 0)})...")

            train_snaps = load_snapshots(TRAINING_DAYS, symbol, session_name, show_progress=True)
            val_snaps = load_snapshots(VALIDATION_DAYS, symbol, session_name, show_progress=True)

            print(f"   -> Training: {len(train_snaps)} snapshots | Validation: {len(val_snaps)} snapshots")

            if len(train_snaps) < 100:
                print(f"   [WARN] Pas assez de donnees")
                continue

            # Test de chaque configuration
            print(f"\n   {'CONFIG':<20} | {'TRAIN':>8} | {'TR_WR':>7} | {'TR_P&L':>10} | {'VAL':>6} | {'V_WR':>7} | {'V_P&L':>10}")
            print(f"   {'-'*85}")

            for config_name, params in CONFIGS_TO_TEST.items():
                train_res = run_backtest(train_snaps, symbol, session_name, params)
                val_res = run_backtest(val_snaps, symbol, session_name, params) if len(val_snaps) > 50 else {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0}

                print(f"   {config_name:<20} | {train_res['n_trades']:>8} | {train_res['winrate']:>6.1f}% | ${train_res['pnl_usd']:>9,.0f} | {val_res['n_trades']:>6} | {val_res['winrate']:>6.1f}% | ${val_res['pnl_usd']:>9,.0f}")

                key = f"{session_name}_{symbol}"
                if key not in all_results:
                    all_results[key] = {}
                all_results[key][config_name] = {
                    'train': train_res,
                    'val': val_res,
                }

            # Afficher rejections pour config NOUVEAUX_SEUILS
            print(f"\n   Rejections (NOUVEAUX_SEUILS):")
            ns_res = all_results.get(f"{session_name}_{symbol}", {}).get('NOUVEAUX_SEUILS', {}).get('train', {})
            if ns_res:
                rej = ns_res.get('rejections', {})
                print(f"   - Confluence: {rej.get('confluence', 0)}")
                print(f"   - Layer1 (MQ<0.50): {rej.get('layer1', 0)}")
                print(f"   - Layer2 (OF<0.20): {rej.get('layer2', 0)}")
                print(f"   - Layer3 (CTX<0.14): {rej.get('layer3', 0)}")
                print(f"   - Trend Filter: {rej.get('trend_filter', 0)}")

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

    print(f"\n   {'CONFIG':<20} | {'TRAIN':>8} | {'TR_WR':>8} | {'TR_P&L':>12} | {'VAL':>6} | {'V_WR':>7} | {'V_P&L':>10}")
    print(f"   {'-'*90}")

    for config_name, totals_data in totals.items():
        train_wr = (totals_data['train_wins'] / totals_data['train_trades'] * 100) if totals_data['train_trades'] > 0 else 0
        val_wr = (totals_data['val_wins'] / totals_data['val_trades'] * 100) if totals_data['val_trades'] > 0 else 0

        print(f"   {config_name:<20} | {totals_data['train_trades']:>8} | {train_wr:>7.1f}% | ${totals_data['train_pnl']:>10,.0f} | {totals_data['val_trades']:>6} | {val_wr:>6.1f}% | ${totals_data['val_pnl']:>9,.0f}")

    # Recommandation
    print(f"\n{'='*100}")
    print("   RECOMMANDATION")
    print(f"{'='*100}")

    # Trouver la meilleure config sur validation
    best_config = None
    best_val_pnl = -999999

    for config_name, data in totals.items():
        if data['val_trades'] >= 5 and data['val_pnl'] > best_val_pnl:
            best_val_pnl = data['val_pnl']
            best_config = config_name

    if best_config:
        cfg = CONFIGS_TO_TEST[best_config]
        data = totals[best_config]
        train_wr = (data['train_wins'] / data['train_trades'] * 100) if data['train_trades'] > 0 else 0
        val_wr = (data['val_wins'] / data['val_trades'] * 100) if data['val_trades'] > 0 else 0

        print(f"\n   [GAGNANT] {best_config}")
        print(f"   {cfg['name']}")
        print(f"\n   Seuils:")
        print(f"   - MenthorQ  >= {cfg['min_layer1']:.2f}")
        print(f"   - OrderFlow >= {cfg['min_layer2']:.2f}")
        print(f"   - Context   >= {cfg['min_layer3']:.2f}")
        print(f"\n   Performance:")
        print(f"   - Training:   {data['train_trades']} trades | WR: {train_wr:.1f}% | P&L: ${data['train_pnl']:,.0f}")
        print(f"   - Validation: {data['val_trades']} trades | WR: {val_wr:.1f}% | P&L: ${data['val_pnl']:,.0f}")

    print(f"\n{'='*100}")

if __name__ == "__main__":
    main()
