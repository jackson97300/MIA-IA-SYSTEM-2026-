"""
===============================================================================
    BACKTEST V10.1 - CONFIG FINALE AVEC TOUS LES NIVEAUX

    Teste la configuration V10.1:
    - TOUS les niveaux premium (FORT + MOYEN + FAIBLE)
    - Layer 3 = 0.12 (au lieu de 0.20)
    - min_level_score = 0 (accepter tous les niveaux)
    - Split 80/20 Training/Validation

    Date: 16 Decembre 2025
===============================================================================
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# ===============================================================================
#                           CONFIGURATION DES DONNEES
# ===============================================================================

# CHEMIN ABSOLU
BASE_DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

# TRAINING SET (80%) - 22 jours
TRAINING_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127",
    "20251201", "20251202", "20251203", "20251204", "20251205",
]

# VALIDATION SET (20%) - 6 jours
VALIDATION_DAYS = [
    "20251208", "20251209", "20251210", "20251211", "20251212",
    "20251215",
]

# ===============================================================================
#                           SESSIONS
# ===============================================================================

SESSIONS = {
    'LONDON': {'start': (8, 0), 'end': (11, 0)},
    'US_MORNING': {'start': (15, 50), 'end': (17, 0)},
    'POWER_HOUR': {'start': (20, 0), 'end': (21, 25)},
}

SYMBOLS = ['ES', 'NQ']

# Mapping symbole -> Chart ID
CHART_MAPPING = {
    "ES": 3,
    "NQ": 9,
    "RTY": 1
}

# ===============================================================================
#                   NIVEAUX PREMIUM COMPLETS (CORRIGÉS)
# ===============================================================================

ALL_PREMIUM_LEVELS = [
    # FORT (Score 3) - Niveaux institutionnels majeurs
    'gex_1',
    'gex_2',
    'hvl',
    'gamma_wall_level',
    'vwap',

    # MOYEN (Score 2) - Niveaux importants
    'gex_3',
    'gex_4',
    'gex_5',
    'hvl_0dte',
    'call_resistance',
    'put_support',
    'blind_spot_1',
    'blind_spot_2',
    'gamma_wall_0dte',
    'vwap_up1',      # VWAP +1 SD
    'vwap_dn1',      # VWAP -1 SD

    # FAIBLE (Score 1) - Niveaux mineurs
    'call_resistance_0dte',
    'put_support_0dte',
    'blind_spot_3',
    'blind_spot_4',
    'vwap_up2',      # VWAP +2 SD
    'vwap_dn2',      # VWAP -2 SD
]

# CLASSIFICATION DES SCORES
LEVEL_SCORES = {
    # FORT (3)
    'gex_1': 3, 'gex_2': 3, 'hvl': 3,
    'gamma_wall_level': 3, 'vwap': 3,

    # MOYEN (2)
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2,
    'hvl_0dte': 2, 'gamma_wall_0dte': 2,
    'call_resistance': 2, 'put_support': 2,
    'blind_spot_1': 2, 'blind_spot_2': 2,
    'vwap_up1': 2, 'vwap_dn1': 2,

    # FAIBLE (1)
    'call_resistance_0dte': 1, 'put_support_0dte': 1,
    'blind_spot_3': 1, 'blind_spot_4': 1,
    'vwap_up2': 1, 'vwap_dn2': 1,
}

# ===============================================================================
#                   CONFIG V10.1 PAR SESSION
# ===============================================================================

V10_1_CONFIGS = {
    'LONDON_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,      # Permissif
        'max_distance': 15,       # Optimal V10
        'min_level_score': 0,     # TOUS les niveaux
        'min_layer1': 0.20,
        'min_layer2': 0.12,
        'min_layer3': 0.12,       # RÉDUIT (était 0.20)
        'enabled': True,
    },
    'LONDON_NQ': {
        'tp_ticks': 25,
        'sl_ticks': 20,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'enabled': False,          # DÉSACTIVÉ - toujours perdant
    },
    'US_MORNING_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,
        'max_distance': 12,
        'min_level_score': 0,     # TOUS les niveaux (était 3)
        'min_layer1': 0.20,
        'min_layer2': 0.10,
        'min_layer3': 0.12,       # RÉDUIT
        'enabled': True,
    },
    'US_MORNING_NQ': {
        'tp_ticks': 25,
        'sl_ticks': 20,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'min_confluence': 1,
        'max_distance': 5,        # Optimal V10
        'min_level_score': 0,     # TOUS les niveaux
        'min_layer1': 0.20,
        'min_layer2': 0.10,
        'min_layer3': 0.12,       # RÉDUIT
        'enabled': True,
    },
    'POWER_HOUR_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,
        'max_distance': 10,
        'min_level_score': 0,     # TOUS les niveaux
        'min_layer1': 0.20,
        'min_layer2': 0.10,
        'min_layer3': 0.12,       # RÉDUIT
        'enabled': True,
    },
    'POWER_HOUR_NQ': {
        'tp_ticks': 40,
        'sl_ticks': 30,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'min_confluence': 2,
        'max_distance': 15,
        'min_level_score': 0,     # TOUS les niveaux
        'min_layer1': 0.20,
        'min_layer2': 0.15,
        'min_layer3': 0.12,       # RÉDUIT
        'enabled': True,
    },
}

# Config V9 originale pour comparaison
V9_CONFIGS = {
    'LONDON_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'tick_size': 0.25, 'tick_value': 12.50,
        'min_confluence': 1, 'max_distance': 12, 'min_level_score': 2,
        'min_layer1': 0.30, 'min_layer2': 0.17, 'min_layer3': 0.20,
        'enabled': True,
    },
    'LONDON_NQ': {'enabled': False, 'tick_size': 0.25, 'tick_value': 5.00},
    'US_MORNING_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'tick_size': 0.25, 'tick_value': 12.50,
        'min_confluence': 1, 'max_distance': 5, 'min_level_score': 3,
        'min_layer1': 0.30, 'min_layer2': 0.17, 'min_layer3': 0.20,
        'enabled': True,
    },
    'US_MORNING_NQ': {
        'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20,
        'tick_size': 0.25, 'tick_value': 5.00,
        'min_confluence': 1, 'max_distance': 15, 'min_level_score': 0,
        'min_layer1': 0.30, 'min_layer2': 0.17, 'min_layer3': 0.20,
        'enabled': True,
    },
    'POWER_HOUR_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'tick_size': 0.25, 'tick_value': 12.50,
        'min_confluence': 1, 'max_distance': 10, 'min_level_score': 2,
        'min_layer1': 0.30, 'min_layer2': 0.17, 'min_layer3': 0.20,
        'enabled': True,
    },
    'POWER_HOUR_NQ': {
        'tp_ticks': 40, 'sl_ticks': 30, 'cooldown_min': 20,
        'tick_size': 0.25, 'tick_value': 5.00,
        'min_confluence': 1, 'max_distance': 15, 'min_level_score': 2,
        'min_layer1': 0.30, 'min_layer2': 0.17, 'min_layer3': 0.20,
        'enabled': True,
    },
}

# ===============================================================================
#                           FONCTIONS UTILITAIRES
# ===============================================================================

def get_level_score(level_name: str) -> int:
    """Retourne le score d'un niveau."""
    if level_name in LEVEL_SCORES:
        return LEVEL_SCORES[level_name]

    # GEX dynamique
    if level_name.startswith('gex_'):
        try:
            num = int(level_name.split('_')[1])
            return 3 if num <= 2 else (2 if num <= 5 else 1)
        except:
            return 1

    # Blind spots dynamique
    if level_name.startswith('blind_spot_'):
        try:
            num = int(level_name.split('_')[2])
            return 2 if num <= 2 else 1
        except:
            return 1

    return 0


def is_in_session(timestamp_ms: int, session_name: str) -> bool:
    """Verifie si le timestamp est dans la session."""
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
    """Extrait tous les niveaux du snapshot."""
    levels = []

    # Niveaux directs
    for key in ALL_PREMIUM_LEVELS:
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    # Blind spots avec prefixe blind_spot_X (commence à 1, pas 0)
    for i in range(1, 10):
        key = f'blind_spot_{i}'
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0 and (key, price, get_level_score(key)) not in levels:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    # GEX 1-10
    for i in range(1, 11):
        key = f'gex_{i}'
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0 and (key, price, get_level_score(key)) not in levels:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    return levels


def find_levels_in_range(mid: float, levels: List, max_distance: int,
                         min_score: int, tick_size: float = 0.25) -> List[Tuple]:
    """Trouve les niveaux dans le range specifie avec score minimum."""
    valid_levels = []

    for level_name, level_price, level_score in levels:
        # Verifier le score minimum
        if level_score < min_score:
            continue

        dist_ticks = abs(mid - level_price) / tick_size
        if dist_ticks <= max_distance:
            valid_levels.append((level_name, level_price, dist_ticks, level_score))

    return valid_levels


# ===============================================================================
#                   CALCUL DES LAYER SCORES
# ===============================================================================

def calculate_layer1_score(snap: dict, levels_in_range: List) -> float:
    """Layer 1 = MenthorQ (50% du score total)"""
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
    """Layer 2 = OrderFlow (30% du score total)"""
    delta = abs(snap.get('delta', 0) or 0)
    cum_delta = abs(snap.get('cum_delta_session', snap.get('cum_delta', 0)) or 0)
    imbalance = abs(snap.get('level1_imbalance', snap.get('imbalance', 0)) or 0)

    delta_score = min(1.0, delta / 500.0)
    cum_score = min(1.0, cum_delta / 2000.0)
    imb_score = min(1.0, imbalance * 5.0)

    return delta_score * 0.4 + cum_score * 0.4 + imb_score * 0.2


def calculate_layer3_score(snap: dict, direction: str) -> float:
    """Layer 3 = Context (20% du score total)"""
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
    """Simule un trade de maniere realiste."""
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
    """Charge les snapshots pour les jours specifies."""
    snapshots = []
    chart_id = CHART_MAPPING.get(symbol, 3)

    MONTHS = {"11": "NOVEMBRE", "12": "DECEMBRE"}

    for day in days:
        try:
            month_num = day[4:6]
            month_name = MONTHS.get(month_num, "NOVEMBRE")

            contract_suffix = "H26" if day >= "20251211" else "Z25"

            jsonl_path = (
                BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                "ML_READY" / f"ml_{symbol}{contract_suffix}_FUT_CME_{chart_id}.jsonl"
            )

            if not jsonl_path.exists():
                jsonl_path = (
                    BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                    "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl"
                )

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
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            continue

    return snapshots


# ===============================================================================
#                           BACKTEST
# ===============================================================================

def run_backtest(snapshots: List[Dict], config: Dict, ignore_menthorq: bool = False) -> Dict:
    """Execute un backtest avec la config donnee."""

    if not config.get('enabled', True):
        return {'n_trades': 0, 'n_wins': 0, 'n_losses': 0, 'pnl_ticks': 0,
                'pnl_usd': 0, 'winrate': 0, 'enabled': False}

    tick_size = config.get('tick_size', 0.25)
    tick_value = config.get('tick_value', 12.50)
    tp_ticks = config.get('tp_ticks', 12)
    sl_ticks = config.get('sl_ticks', 12)
    cooldown_ms = config.get('cooldown_min', 15) * 60 * 1000

    min_confluence = config.get('min_confluence', 1)
    max_distance = config.get('max_distance', 15)
    min_level_score = config.get('min_level_score', 0)
    min_layer1 = config.get('min_layer1', 0.30)
    min_layer2 = config.get('min_layer2', 0.15)
    min_layer3 = config.get('min_layer3', 0.12)

    results = {
        'n_trades': 0, 'n_wins': 0, 'n_losses': 0,
        'pnl_ticks': 0, 'pnl_usd': 0, 'enabled': True,
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

        mia_score = snap.get('mia_bullish_score', 0) or 0
        direction = 'LONG' if mia_score > 0 else 'SHORT'

        levels = extract_levels_from_snapshot(snap)
        valid_levels = find_levels_in_range(mid, levels, max_distance, min_level_score, tick_size)

        layer1_score = calculate_layer1_score(snap, valid_levels)
        layer2_score = calculate_layer2_score(snap)
        layer3_score = calculate_layer3_score(snap, direction)

        if not ignore_menthorq:
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
    print("="*70)
    print("   BACKTEST V10.1 - CONFIG FINALE AVEC TOUS LES NIVEAUX")
    print("="*70)
    print(f"\n  Training: {len(TRAINING_DAYS)} jours")
    print(f"  Validation: {len(VALIDATION_DAYS)} jours")
    print(f"  Layer 3: 0.12 (réduit de 0.20)")
    print(f"  min_level_score: 0 (tous les niveaux)")

    all_results = {}

    for session_name in SESSIONS.keys():
        for symbol in SYMBOLS:
            key = f"{session_name}_{symbol}"

            print(f"\n{'='*60}")
            print(f"  {key}")
            print(f"{'='*60}")

            # Charger les snapshots
            train_snaps = load_snapshots(TRAINING_DAYS, symbol, session_name)
            val_snaps = load_snapshots(VALIDATION_DAYS, symbol, session_name)

            print(f"  Training: {len(train_snaps)} snapshots")
            print(f"  Validation: {len(val_snaps)} snapshots")

            if len(train_snaps) < 100:
                print(f"  ⚠️ Pas assez de données")
                continue

            # Config V10.1
            config_v10_1 = V10_1_CONFIGS.get(key, {'enabled': False})

            # Config V9
            config_v9 = V9_CONFIGS.get(key, {'enabled': False})

            # === TRAINING ===
            print(f"\n  --- TRAINING ({len(TRAINING_DAYS)} jours) ---")

            train_v10_1 = run_backtest(train_snaps, config_v10_1)
            train_v9 = run_backtest(train_snaps, config_v9)
            train_ml = run_backtest(train_snaps, config_v10_1, ignore_menthorq=True)

            print(f"  V10.1:   {train_v10_1['n_trades']:>4} trades, WR {train_v10_1['winrate']:>5.1f}%, ${train_v10_1['pnl_usd']:>8,.0f}")
            print(f"  V9:      {train_v9['n_trades']:>4} trades, WR {train_v9['winrate']:>5.1f}%, ${train_v9['pnl_usd']:>8,.0f}")
            print(f"  ML seul: {train_ml['n_trades']:>4} trades, WR {train_ml['winrate']:>5.1f}%, ${train_ml['pnl_usd']:>8,.0f}")

            # === VALIDATION ===
            if len(val_snaps) > 0:
                print(f"\n  --- VALIDATION ({len(VALIDATION_DAYS)} jours) ---")

                val_v10_1 = run_backtest(val_snaps, config_v10_1)
                val_v9 = run_backtest(val_snaps, config_v9)
                val_ml = run_backtest(val_snaps, config_v10_1, ignore_menthorq=True)

                print(f"  V10.1:   {val_v10_1['n_trades']:>4} trades, WR {val_v10_1['winrate']:>5.1f}%, ${val_v10_1['pnl_usd']:>8,.0f}")
                print(f"  V9:      {val_v9['n_trades']:>4} trades, WR {val_v9['winrate']:>5.1f}%, ${val_v9['pnl_usd']:>8,.0f}")
                print(f"  ML seul: {val_ml['n_trades']:>4} trades, WR {val_ml['winrate']:>5.1f}%, ${val_ml['pnl_usd']:>8,.0f}")

                # Meilleur
                best_pnl = max(val_v10_1['pnl_usd'], val_v9['pnl_usd'], val_ml['pnl_usd'])
                if best_pnl == val_v10_1['pnl_usd']:
                    print(f"  ✅ MEILLEUR: V10.1")
                elif best_pnl == val_v9['pnl_usd']:
                    print(f"  ✅ MEILLEUR: V9")
                else:
                    print(f"  ✅ MEILLEUR: ML seul")

                all_results[key] = {
                    'train': {'v10_1': train_v10_1, 'v9': train_v9, 'ml': train_ml},
                    'val': {'v10_1': val_v10_1, 'v9': val_v9, 'ml': val_ml},
                }

    # ===============================================================================
    #                           RÉSUMÉ FINAL
    # ===============================================================================

    print("\n" + "="*70)
    print("   RÉSUMÉ VALIDATION - P&L PAR CONFIG")
    print("="*70)

    totals = {'v10_1': 0, 'v9': 0, 'ml': 0}

    print(f"\n{'Session':<20} {'V10.1':>12} {'V9':>12} {'ML seul':>12} {'Meilleur':>12}")
    print("-"*70)

    for key, data in all_results.items():
        val = data.get('val', {})
        v10_1_pnl = val.get('v10_1', {}).get('pnl_usd', 0)
        v9_pnl = val.get('v9', {}).get('pnl_usd', 0)
        ml_pnl = val.get('ml', {}).get('pnl_usd', 0)

        totals['v10_1'] += v10_1_pnl
        totals['v9'] += v9_pnl
        totals['ml'] += ml_pnl

        best = max(v10_1_pnl, v9_pnl, ml_pnl)
        best_name = 'V10.1' if best == v10_1_pnl else ('V9' if best == v9_pnl else 'ML')

        print(f"{key:<20} ${v10_1_pnl:>10,.0f} ${v9_pnl:>10,.0f} ${ml_pnl:>10,.0f} {best_name:>12}")

    print("-"*70)
    print(f"{'TOTAL':<20} ${totals['v10_1']:>10,.0f} ${totals['v9']:>10,.0f} ${totals['ml']:>10,.0f}")

    # Déterminer le gagnant global
    best_total = max(totals.values())
    if best_total == totals['v10_1']:
        winner = "V10.1"
    elif best_total == totals['v9']:
        winner = "V9"
    else:
        winner = "ML seul"

    print(f"\n🏆 GAGNANT GLOBAL: {winner} (${best_total:,.0f})")

    # Sauvegarder les résultats
    output = {
        'date': datetime.now().isoformat(),
        'config': 'V10.1 avec tous les niveaux',
        'training_days': len(TRAINING_DAYS),
        'validation_days': len(VALIDATION_DAYS),
        'results': all_results,
        'totals': totals,
        'winner': winner,
    }

    output_path = Path(__file__).parent / "backtest_v10_1_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Résultats sauvegardés: {output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
