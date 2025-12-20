"""
===============================================================================
    BACKTEST V10 - OPTIMISATION COMPLETE (6 ETAPES)

    Trouve les parametres OPTIMAUX pour chaque session x symbole:
    - min_confluence
    - max_distance
    - min_layer1 (MenthorQ)
    - min_layer2 (OrderFlow)
    - min_layer3 (Context)

    Avec split 80/20 pour eviter l'overfitting.

    CORRECTIONS APPLIQUEES:
    - Chemin absolu vers DATA_SIERRA_CHART
    - Calcul REEL des Layer scores (comme ml_3layer_integrated_system.py)
    - Simulation trade realiste (300 snapshots = 5 min)
    - Test ML seul = ignorer TOUS les filtres MenthorQ

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
import itertools

# ===============================================================================
#                           CONFIGURATION DES DONNEES
# ===============================================================================

# CHEMIN ABSOLU (corrige)
BASE_DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

# TRAINING SET (80%) - 22 jours
TRAINING_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127",
    "20251201", "20251202", "20251203", "20251204", "20251205",
]

# VALIDATION SET (20%) - 6 jours (inclut le 15 decembre!)
VALIDATION_DAYS = [
    "20251208", "20251209", "20251210", "20251211", "20251212",
    "20251215",  # Aujourd'hui ajoute!
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

# Mapping symbole -> Chart ID (selon ARCHITECTURE_DONNEES.md)
CHART_MAPPING = {
    "ES": 3,   # E-mini S&P 500 -> CHART_3
    "NQ": 9,   # E-mini NASDAQ -> CHART_9
    "RTY": 1   # E-mini Russell 2000 -> CHART_1
}

# ===============================================================================
#                           NIVEAUX PREMIUM
# ===============================================================================

ALL_PREMIUM_LEVELS = [
    # FORT (Score 3)
    'gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap',

    # MOYEN (Score 2)
    'gex_3', 'gex_4', 'gex_5',
    'hvl_0dte', 'gamma_wall_0dte',
    'call_resistance', 'put_support',
    'blind_spot_1', 'blind_spot_2',
    'vwap_up1', 'vwap_dn1',

    # FAIBLE (Score 1)
    'call_resistance_0dte', 'put_support_0dte',
    'blind_spot_3', 'blind_spot_4',
]

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
}

# ===============================================================================
#                           CONFIG DE BASE PAR SYMBOLE
# ===============================================================================

BASE_CONFIG = {
    'ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
    },
    'NQ': {
        'tp_ticks': 25,
        'sl_ticks': 20,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
    },
}

# ===============================================================================
#                           VALEURS A TESTER
# ===============================================================================

# Etape 1: Confluence
CONFLUENCE_VALUES = [1, 2, 3, 4, 5]

# Etape 2: Distance
DISTANCE_VALUES = [5, 8, 10, 12, 15, 20, 25]

# Etape 3: Layer 1 (MenthorQ)
LAYER1_VALUES = [0.20, 0.25, 0.30, 0.35, 0.40]

# Etape 4: Layer 2 (OrderFlow)
LAYER2_VALUES = [0.10, 0.12, 0.15, 0.17, 0.20, 0.25]

# Etape 5: Layer 3 (Context) - 0.20 bloquait tout!
LAYER3_VALUES = [0.10, 0.12, 0.15, 0.17, 0.20, 0.25]

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

    # Blind spots avec prefixe blind_spot_X
    for i in range(9):
        key = f'blind_spot_{i}'
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    # GEX 1-10
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


def find_levels_in_range(mid: float, levels: List, max_distance: int,
                         tick_size: float = 0.25) -> List[Tuple]:
    """Trouve les niveaux dans le range specifie."""
    valid_levels = []

    for level_name, level_price, level_score in levels:
        dist_ticks = abs(mid - level_price) / tick_size
        if dist_ticks <= max_distance:
            valid_levels.append((level_name, level_price, dist_ticks, level_score))

    return valid_levels


# ===============================================================================
#                   CALCUL REEL DES LAYER SCORES
# ===============================================================================

def calculate_layer1_score(snap: dict, levels_in_range: List) -> float:
    """
    Layer 1 = MenthorQ (50% du score total)
    Basé sur: distance au niveau + force du niveau
    """
    if not levels_in_range:
        return 0.0

    # Trouver le niveau le plus proche
    nearest = min(levels_in_range, key=lambda x: x[2])  # x[2] = distance en ticks
    dist = nearest[2]
    level_score = nearest[3]  # score du niveau (1, 2, ou 3)

    # Score basé sur distance (plus proche = meilleur)
    # 0 ticks = 1.0, 25 ticks = 0.0
    dist_score = max(0.0, 1.0 - dist / 25.0)

    # Boost basé sur force du niveau
    level_boost = 1.3 if level_score == 3 else (1.1 if level_score == 2 else 1.0)

    # Confluence bonus
    confluence_bonus = min(0.2, len(levels_in_range) * 0.05)

    return min(1.0, dist_score * level_boost + confluence_bonus)


def calculate_layer2_score(snap: dict) -> float:
    """
    Layer 2 = OrderFlow (30% du score total)
    Basé sur: delta, cumulative delta, imbalance
    """
    delta = abs(snap.get('delta', 0) or 0)
    cum_delta = abs(snap.get('cum_delta_session', snap.get('cum_delta', 0)) or 0)
    imbalance = abs(snap.get('level1_imbalance', snap.get('imbalance', 0)) or 0)

    # Score delta (0-500 = 0-1)
    delta_score = min(1.0, delta / 500.0)

    # Score cumulative delta (0-2000 = 0-1)
    cum_score = min(1.0, cum_delta / 2000.0)

    # Score imbalance (0-0.2 = 0-1)
    imb_score = min(1.0, imbalance * 5.0)

    # Poids: delta 40%, cum_delta 40%, imbalance 20%
    return delta_score * 0.4 + cum_score * 0.4 + imb_score * 0.2


def calculate_layer3_score(snap: dict, direction: str) -> float:
    """
    Layer 3 = Context (20% du score total)
    Basé sur: position dans le range + contexte directionnel
    """
    # Position dans le range (0-100)
    pos_range = snap.get('position_in_range', 50) or 50

    # MIA score
    mia = snap.get('mia_bullish_score', 0) or 0

    # Penalite si mauvaise position dans le range
    if direction == 'LONG' and pos_range > 70:
        return 0.10  # Proche du haut = mauvais pour LONG
    if direction == 'SHORT' and pos_range < 30:
        return 0.10  # Proche du bas = mauvais pour SHORT

    # Bonus si bonne position
    if direction == 'LONG' and pos_range < 40:
        return 0.25  # Proche du bas = bon pour LONG
    if direction == 'SHORT' and pos_range > 60:
        return 0.25  # Proche du haut = bon pour SHORT

    # Zone neutre - verifier coherence avec MIA
    if direction == 'LONG' and mia > 0.2:
        return 0.22
    if direction == 'SHORT' and mia < -0.2:
        return 0.22

    return 0.18  # Zone neutre sans signal clair


# ===============================================================================
#                   SIMULATION DE TRADE REALISTE
# ===============================================================================

def simulate_trade(entry: float, direction: str, tp_ticks: int, sl_ticks: int,
                   future_snapshots: List[Dict], tick_size: float) -> Dict:
    """
    Simule un trade de maniere realiste en parcourant les snapshots futurs.
    Regarde jusqu'a 300 snapshots (environ 5 minutes).
    """
    tp = entry + (tp_ticks * tick_size) if direction == 'LONG' else entry - (tp_ticks * tick_size)
    sl = entry - (sl_ticks * tick_size) if direction == 'LONG' else entry + (sl_ticks * tick_size)

    # Parcourir les snapshots futurs tick par tick
    for i, future_snap in enumerate(future_snapshots):
        high = future_snap.get('high', entry)
        low = future_snap.get('low', entry)

        if direction == 'LONG':
            # TP touche?
            if high >= tp:
                return {'win': True, 'pnl_ticks': tp_ticks, 'exit': 'TP', 'duration': i}
            # SL touche?
            if low <= sl:
                return {'win': False, 'pnl_ticks': -sl_ticks, 'exit': 'SL', 'duration': i}
        else:  # SHORT
            # TP touche?
            if low <= tp:
                return {'win': True, 'pnl_ticks': tp_ticks, 'exit': 'TP', 'duration': i}
            # SL touche?
            if high >= sl:
                return {'win': False, 'pnl_ticks': -sl_ticks, 'exit': 'SL', 'duration': i}

    # Timeout - calcul P&L a la fin
    if future_snapshots:
        last_mid = future_snapshots[-1].get('mid', entry)
        if direction == 'LONG':
            pnl = (last_mid - entry) / tick_size
        else:
            pnl = (entry - last_mid) / tick_size

        return {'win': pnl > 0, 'pnl_ticks': pnl, 'exit': 'TIMEOUT', 'duration': len(future_snapshots)}

    return {'win': False, 'pnl_ticks': 0, 'exit': 'NO_DATA', 'duration': 0}


# ===============================================================================
#                           CHARGEMENT DES DONNEES
# ===============================================================================

def load_snapshots(days: List[str], symbol: str, session_name: str) -> List[Dict]:
    """Charge les snapshots pour les jours specifies."""
    snapshots = []

    chart_id = CHART_MAPPING.get(symbol, 3)

    # Mapping date -> mois
    MONTHS = {
        "11": "NOVEMBRE",
        "12": "DECEMBRE",
    }

    for day in days:
        try:
            month_num = day[4:6]
            month_name = MONTHS.get(month_num, "NOVEMBRE")

            # Contrat Z25 avant rollover (11 dec), H26 apres rollover
            contract_suffix = "H26" if day >= "20251211" else "Z25"

            jsonl_path = (
                BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                "ML_READY" / f"ml_{symbol}{contract_suffix}_FUT_CME_{chart_id}.jsonl"
            )

            if not jsonl_path.exists():
                # Essayer avec Z25 si H26 n'existe pas
                jsonl_path = (
                    BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                    "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl"
                )

            if not jsonl_path.exists():
                # Dernier essai avec H25
                jsonl_path = (
                    BASE_DATA_PATH / month_name / day / f"CHART_{chart_id}" /
                    "ML_READY" / f"ml_{symbol}H25_FUT_CME_{chart_id}.jsonl"
                )

            if jsonl_path.exists():
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                snap = json.loads(line)
                                t_ms = snap.get('t_ms', 0)
                                if is_in_session(t_ms, session_name):
                                    snap['_file'] = str(jsonl_path)
                                    snap['_day'] = day
                                    snapshots.append(snap)
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"  Erreur chargement {day}/{symbol}: {e}")
            continue

    return snapshots


# ===============================================================================
#                           FONCTIONS DE BACKTEST
# ===============================================================================

def run_backtest(snapshots: List[Dict], symbol: str, params: Dict,
                 ignore_menthorq: bool = False) -> Dict:
    """
    Execute un backtest avec les parametres donnes.

    Args:
        snapshots: Liste des snapshots
        symbol: Symbole (ES, NQ)
        params: Parametres a tester
        ignore_menthorq: Si True, ignore tous les filtres MenthorQ (pour test ML seul)
    """
    cfg = BASE_CONFIG[symbol]
    tick_size = cfg['tick_size']
    tick_value = cfg['tick_value']
    tp_ticks = cfg['tp_ticks']
    sl_ticks = cfg['sl_ticks']
    cooldown_ms = cfg['cooldown_min'] * 60 * 1000

    # Parametres a tester
    min_confluence = params.get('min_confluence', 1)
    max_distance = params.get('max_distance', 15)
    min_layer1 = params.get('min_layer1', 0.30)
    min_layer2 = params.get('min_layer2', 0.15)
    min_layer3 = params.get('min_layer3', 0.15)

    results = {
        'n_trades': 0,
        'n_wins': 0,
        'n_losses': 0,
        'pnl_ticks': 0,
        'pnl_usd': 0,
        'signals_generated': 0,
        'rejections': defaultdict(int),
    }

    last_trade_time = 0

    for i, snap in enumerate(snapshots):
        t_ms = snap.get('t_ms', 0)
        mid = snap.get('mid', 0)

        if not mid or mid <= 0:
            continue

        # Cooldown
        if t_ms - last_trade_time < cooldown_ms:
            continue

        results['signals_generated'] += 1

        # Determiner la direction AVANT les calculs de layers
        mia_score = snap.get('mia_bullish_score', 0) or 0
        direction = 'LONG' if mia_score > 0 else 'SHORT'

        # Extraire les niveaux
        levels = extract_levels_from_snapshot(snap)

        # Trouver niveaux dans le range (utilise pour Layer 1)
        valid_levels = find_levels_in_range(mid, levels, max_distance, tick_size)

        # Calculer les VRAIS scores des layers
        layer1_score = calculate_layer1_score(snap, valid_levels)
        layer2_score = calculate_layer2_score(snap)
        layer3_score = calculate_layer3_score(snap, direction)

        # === VALIDATIONS ===

        if not ignore_menthorq:
            # Validation confluence
            if len(valid_levels) < min_confluence:
                results['rejections']['confluence'] += 1
                continue

        # Validation Layer 1 (seulement si on ne ignore pas MenthorQ)
        if not ignore_menthorq and layer1_score < min_layer1:
            results['rejections']['layer1'] += 1
            continue

        # Validation Layer 2
        if layer2_score < min_layer2:
            results['rejections']['layer2'] += 1
            continue

        # Validation Layer 3
        if layer3_score < min_layer3:
            results['rejections']['layer3'] += 1
            continue

        # === TRADE ACCEPTE ===

        # Simulation realiste: regarder 300 snapshots (~5 min)
        future_snaps = snapshots[i+1:i+301]

        if len(future_snaps) < 10:  # Pas assez de donnees
            continue

        # Simuler le trade
        trade = simulate_trade(mid, direction, tp_ticks, sl_ticks,
                              future_snaps, tick_size)

        results['n_trades'] += 1
        results['pnl_ticks'] += trade['pnl_ticks']

        if trade['win']:
            results['n_wins'] += 1
        else:
            results['n_losses'] += 1

        last_trade_time = t_ms

    # Calculer stats finales
    results['pnl_usd'] = results['pnl_ticks'] * tick_value
    results['winrate'] = (results['n_wins'] / results['n_trades'] * 100) if results['n_trades'] > 0 else 0

    return results


# ===============================================================================
#                           OPTIMISATION PAR ETAPE
# ===============================================================================

def optimize_step(snapshots: List[Dict], symbol: str, param_name: str,
                  param_values: List, fixed_params: Dict) -> Tuple[any, Dict]:
    """Optimise un parametre specifique."""
    best_value = param_values[0]
    best_pnl = -999999
    best_results = {}

    print(f"    Testing: {param_values}")

    for value in param_values:
        params = fixed_params.copy()
        params[param_name] = value

        results = run_backtest(snapshots, symbol, params)

        print(f"      {param_name}={value}: {results['n_trades']} trades, ${results['pnl_usd']:.0f}")

        if results['pnl_usd'] > best_pnl:
            best_pnl = results['pnl_usd']
            best_value = value
            best_results = results

    return best_value, best_results


def run_optimization(session_name: str, symbol: str) -> Dict:
    """Execute l'optimisation complete pour une session/symbole."""

    print(f"\n{'='*60}")
    print(f"  OPTIMISATION: {session_name}_{symbol}")
    print(f"{'='*60}")

    # Charger les snapshots d'entrainement
    print(f"\n  Chargement des snapshots d'entrainement...")
    train_snapshots = load_snapshots(TRAINING_DAYS, symbol, session_name)
    print(f"  -> {len(train_snapshots)} snapshots charges")

    if len(train_snapshots) < 100:
        print(f"  ⚠️ Pas assez de donnees pour optimiser")
        return None

    # Parametres initiaux
    optimal_params = {
        'min_confluence': 1,
        'max_distance': 15,
        'min_layer1': 0.30,
        'min_layer2': 0.15,
        'min_layer3': 0.15,
    }

    # ETAPE 1: Confluence
    print(f"\n  ETAPE 1: Optimisation CONFLUENCE...")
    best_conf, res = optimize_step(train_snapshots, symbol, 'min_confluence',
                                    CONFLUENCE_VALUES, optimal_params)
    optimal_params['min_confluence'] = best_conf
    print(f"    -> Meilleur: {best_conf} (P&L: ${res['pnl_usd']:.0f}, Trades: {res['n_trades']}, WR: {res['winrate']:.1f}%)")

    # ETAPE 2: Distance
    print(f"\n  ETAPE 2: Optimisation DISTANCE...")
    best_dist, res = optimize_step(train_snapshots, symbol, 'max_distance',
                                    DISTANCE_VALUES, optimal_params)
    optimal_params['max_distance'] = best_dist
    print(f"    -> Meilleur: {best_dist}t (P&L: ${res['pnl_usd']:.0f}, Trades: {res['n_trades']}, WR: {res['winrate']:.1f}%)")

    # ETAPE 3: Layer 1
    print(f"\n  ETAPE 3: Optimisation LAYER 1 (MenthorQ)...")
    best_l1, res = optimize_step(train_snapshots, symbol, 'min_layer1',
                                  LAYER1_VALUES, optimal_params)
    optimal_params['min_layer1'] = best_l1
    print(f"    -> Meilleur: {best_l1:.0%} (P&L: ${res['pnl_usd']:.0f}, Trades: {res['n_trades']}, WR: {res['winrate']:.1f}%)")

    # ETAPE 4: Layer 2
    print(f"\n  ETAPE 4: Optimisation LAYER 2 (OrderFlow)...")
    best_l2, res = optimize_step(train_snapshots, symbol, 'min_layer2',
                                  LAYER2_VALUES, optimal_params)
    optimal_params['min_layer2'] = best_l2
    print(f"    -> Meilleur: {best_l2:.0%} (P&L: ${res['pnl_usd']:.0f}, Trades: {res['n_trades']}, WR: {res['winrate']:.1f}%)")

    # ETAPE 5: Layer 3
    print(f"\n  ETAPE 5: Optimisation LAYER 3 (Context)...")
    best_l3, res = optimize_step(train_snapshots, symbol, 'min_layer3',
                                  LAYER3_VALUES, optimal_params)
    optimal_params['min_layer3'] = best_l3
    print(f"    -> Meilleur: {best_l3:.0%} (P&L: ${res['pnl_usd']:.0f}, Trades: {res['n_trades']}, WR: {res['winrate']:.1f}%)")

    # ETAPE 6: Validation out-of-sample
    print(f"\n  ETAPE 6: VALIDATION OUT-OF-SAMPLE...")
    val_snapshots = load_snapshots(VALIDATION_DAYS, symbol, session_name)
    print(f"  -> {len(val_snapshots)} snapshots de validation")

    val_results_v10 = {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0}
    val_results_ml = {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0}
    val_results_v9 = {'n_trades': 0, 'winrate': 0, 'pnl_usd': 0}

    if len(val_snapshots) > 0:
        # Test A: Parametres optimaux V10
        val_results_v10 = run_backtest(val_snapshots, symbol, optimal_params)

        # Test B: ML seul (ignorer TOUS les filtres MenthorQ)
        val_results_ml = run_backtest(val_snapshots, symbol, optimal_params, ignore_menthorq=True)

        # Test C: Config V9 originale
        v9_params = {
            'min_confluence': 1,
            'max_distance': 5 if session_name == 'US_MORNING' else 12,
            'min_layer1': 0.30,
            'min_layer2': 0.17,
            'min_layer3': 0.20,
        }
        val_results_v9 = run_backtest(val_snapshots, symbol, v9_params)

        print(f"\n  RESULTATS VALIDATION:")
        print(f"  {'-'*50}")
        print(f"  | Config          | Trades | WinRate | P&L     |")
        print(f"  {'-'*50}")
        print(f"  | V10 (optimal)   | {val_results_v10['n_trades']:>6} | {val_results_v10['winrate']:>6.1f}% | ${val_results_v10['pnl_usd']:>7,.0f} |")
        print(f"  | ML seul         | {val_results_ml['n_trades']:>6} | {val_results_ml['winrate']:>6.1f}% | ${val_results_ml['pnl_usd']:>7,.0f} |")
        print(f"  | V9 (original)   | {val_results_v9['n_trades']:>6} | {val_results_v9['winrate']:>6.1f}% | ${val_results_v9['pnl_usd']:>7,.0f} |")
        print(f"  {'-'*50}")

    return {
        'session': session_name,
        'symbol': symbol,
        'optimal_params': optimal_params,
        'training_results': res,
        'validation_results': {
            'v10': val_results_v10,
            'ml_only': val_results_ml,
            'v9': val_results_v9,
        },
    }


# ===============================================================================
#                           MAIN
# ===============================================================================

def main():
    print("="*70)
    print("   BACKTEST V10 - OPTIMISATION COMPLETE (6 ETAPES)")
    print("   Avec calcul REEL des Layer scores")
    print("="*70)
    print(f"\n  Training: {len(TRAINING_DAYS)} jours")
    print(f"  Validation: {len(VALIDATION_DAYS)} jours (inclut 15/12)")
    print(f"  Sessions: {list(SESSIONS.keys())}")
    print(f"  Symboles: {SYMBOLS}")
    print(f"  = {len(SESSIONS) * len(SYMBOLS)} combinaisons a optimiser")
    print(f"\n  Chemin donnees: {BASE_DATA_PATH}")

    all_results = {}

    for session_name in SESSIONS.keys():
        for symbol in SYMBOLS:
            key = f"{session_name}_{symbol}"
            result = run_optimization(session_name, symbol)
            if result:
                all_results[key] = result

    # Resume final
    print("\n" + "="*70)
    print("   RESUME FINAL - PARAMETRES OPTIMAUX V10")
    print("="*70)

    print(f"\n{'Session':<20} {'Conf':>5} {'Dist':>5} {'L1':>6} {'L2':>6} {'L3':>6} {'P&L Val':>10}")
    print("-"*70)

    for key, result in all_results.items():
        if result and result.get('optimal_params'):
            p = result['optimal_params']
            val_pnl = result.get('validation_results', {}).get('v10', {}).get('pnl_usd', 0)
            print(f"{key:<20} {p['min_confluence']:>5} {p['max_distance']:>5}t {p['min_layer1']:>5.0%} {p['min_layer2']:>5.0%} {p['min_layer3']:>5.0%} ${val_pnl:>9,.0f}")

    # Sauvegarder les resultats
    output = {
        'date': datetime.now().isoformat(),
        'training_days': TRAINING_DAYS,
        'validation_days': VALIDATION_DAYS,
        'results': {}
    }

    for k, v in all_results.items():
        if v:
            output['results'][k] = {
                'optimal_params': v['optimal_params'],
                'training_pnl': v['training_results']['pnl_usd'],
                'training_trades': v['training_results']['n_trades'],
                'training_winrate': v['training_results']['winrate'],
                'validation': {
                    'v10': v['validation_results']['v10'],
                    'ml_only': v['validation_results']['ml_only'],
                    'v9': v['validation_results']['v9'],
                }
            }

    output_path = Path(__file__).parent / "backtest_v10_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Resultats sauvegardes: {output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
