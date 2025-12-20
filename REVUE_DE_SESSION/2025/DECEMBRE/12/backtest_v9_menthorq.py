#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
            BACKTEST V9 - OPTIMISATION SEUILS MENTHORQ
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF: Optimiser les seuils MenthorQ par Session × Symbole

📊 BASE: Configs optimales V8 (TP/SL, Cooldown, Confidence, Layer2, MIA)

🔧 PARAMÈTRES À OPTIMISER:
   1. MAX_DISTANCE:   Distance max au niveau MenthorQ [5, 8, 10, 12, 15, 17, 20, 25]
   2. MIN_CONFLUENCE: Nombre min de niveaux dans zone ±15 ticks [1, 2, 3]
   3. MIN_LEVEL_SCORE: Force min du niveau [0=any, 1=faible+, 2=moyen+, 3=fort]

📈 RÉSULTATS V8 (base):
   POWER_HOUR NQ: +$2,200 | WR 59% 🏆
   POWER_HOUR ES: +$2,100 | WR 56%
   LONDON ES:     +$1,350 | WR 48%
   US_MORNING ES: +$1,050 | WR 52%
   TOTAL:         +$6,875

Auteur: MIA IA System
Date: 13 Décembre 2025
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
from itertools import product
import sys

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

DAYS_TO_TEST = [
    # Novembre
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127",
    # Décembre
    "20251201", "20251202", "20251203", "20251204", "20251205",
    "20251208", "20251209", "20251210", "20251211", "20251212",
]

SYMBOLS = {
    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50, "contracts": ["ESZ25", "ESH25"]},
    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00, "contracts": ["NQZ25", "NQH25"]},
}

SESSIONS = {
    'LONDON': {'start': (8, 0), 'end': (11, 0), 'name': 'London 8h-11h'},
    'US_MORNING': {'start': (15, 50), 'end': (17, 0), 'name': 'US Morning 15:50-17h'},
    'POWER_HOUR': {'start': (20, 0), 'end': (21, 25), 'name': 'Power Hour 20h-21:25'},
}

# ═══════════════════════════════════════════════════════════════════════════════
#              CONFIGS V8 OPTIMALES (BASE)
# ═══════════════════════════════════════════════════════════════════════════════

V8_CONFIGS = {
    'LONDON_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.30, 'min_layer2': 0.15, 'mia_threshold': 0.20,
    },
    'LONDON_NQ': {
        'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20,
        'min_confidence': 0.65, 'min_layer2': 0.15, 'mia_threshold': 0.20,
    },
    'US_MORNING_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.60, 'min_layer2': 0.15, 'mia_threshold': 0.20,
    },
    'US_MORNING_NQ': {
        'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20,
        'min_confidence': 0.30, 'min_layer2': 0.15, 'mia_threshold': 0.25,
    },
    'POWER_HOUR_ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.70, 'min_layer2': 0.15, 'mia_threshold': 0.20,
    },
    'POWER_HOUR_NQ': {
        'tp_ticks': 40, 'sl_ticks': 30, 'cooldown_min': 20,
        'min_confidence': 0.70, 'min_layer2': 0.15, 'mia_threshold': 0.20,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#              NIVEAUX MENTHORQ - CLASSÉS PAR FORCE
# ═══════════════════════════════════════════════════════════════════════════════

# Score 3: Niveaux FORTS (institutionnels)
STRONG_LEVELS = ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap']

# Score 2: Niveaux MOYENS
MEDIUM_LEVELS = ['gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
                 'call_resistance', 'put_support', 'blind_spot_1', 'blind_spot_2']

# Score 1: Niveaux FAIBLES
WEAK_LEVELS = ['call_resistance_0dte', 'put_support_0dte', 'blind_spot_3',
               'vwap_up1', 'vwap_dn1', 'vwap_up2', 'vwap_dn2']

ALL_LEVELS = STRONG_LEVELS + MEDIUM_LEVELS + WEAK_LEVELS

def get_level_score(level_name: str) -> int:
    """Retourne le score de force d'un niveau (3=fort, 2=moyen, 1=faible, 0=inconnu)."""
    if level_name in STRONG_LEVELS:
        return 3
    elif level_name in MEDIUM_LEVELS:
        return 2
    elif level_name in WEAK_LEVELS:
        return 1
    return 0

# ═══════════════════════════════════════════════════════════════════════════════
#              GRILLE MENTHORQ À OPTIMISER
# ═══════════════════════════════════════════════════════════════════════════════

MAX_DISTANCE_GRID = [5, 8, 10, 12, 15, 17, 20, 25]  # 8 valeurs
MIN_CONFLUENCE_GRID = [1, 2, 3]                      # 3 valeurs
MIN_LEVEL_SCORE_GRID = [0, 1, 2, 3]                  # 4 valeurs (0=any)

# Total: 8 × 3 × 4 = 96 combinaisons par session/symbole
# × 6 = 576 backtests (gérable!)

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, prefix: str = "", length: int = 30):
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r{prefix} |{bar}| {percent*100:.0f}%")
    sys.stdout.flush()
    if current >= total:
        print()


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


def get_session(hour: int, minute: int) -> Optional[str]:
    time_val = time_to_minutes(hour, minute)
    for session_name, session in SESSIONS.items():
        s = time_to_minutes(session['start'][0], session['start'][1])
        e = time_to_minutes(session['end'][0], session['end'][1])
        if s <= time_val < e:
            return session_name
    return None

# ═══════════════════════════════════════════════════════════════════════════════
#              ANALYSE MENTHORQ (CONFLUENCE + NIVEAU)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_menthorq(snapshot: Dict, symbol: str, zone_ticks: int = 15) -> Dict:
    """
    Analyse complète des niveaux MenthorQ autour du prix.
    
    Retourne:
    - nearest_level: Nom du niveau le plus proche
    - nearest_distance: Distance en ticks
    - nearest_score: Score du niveau le plus proche
    - confluence_count: Nombre de niveaux dans la zone
    - max_score_in_zone: Score max des niveaux dans la zone
    - levels_in_zone: Liste détaillée
    """
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return {
            'nearest_level': '', 'nearest_distance': float('inf'),
            'nearest_score': 0, 'confluence_count': 0, 'max_score_in_zone': 0
        }
    
    tick_size = SYMBOLS[symbol]['tick_size']
    
    levels_in_zone = []
    nearest_level = ""
    nearest_distance = float('inf')
    nearest_score = 0
    max_score = 0
    
    for level_name in ALL_LEVELS:
        price = snapshot.get(level_name)
        if not price or price <= 0:
            continue
        
        distance = abs(mid - price) / tick_size
        score = get_level_score(level_name)
        
        # Niveau dans la zone?
        if distance <= zone_ticks:
            levels_in_zone.append({
                'name': level_name,
                'distance': distance,
                'score': score,
            })
            max_score = max(max_score, score)
        
        # Niveau le plus proche?
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_level = level_name
            nearest_score = score
    
    return {
        'nearest_level': nearest_level,
        'nearest_distance': nearest_distance,
        'nearest_score': nearest_score,
        'confluence_count': len(levels_in_zone),
        'max_score_in_zone': max_score,
        'levels_in_zone': levels_in_zone,
    }

# ═══════════════════════════════════════════════════════════════════════════════
#              GÉNÉRATION DE SIGNAL (avec filtres MenthorQ)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal(
    snapshot: Dict, 
    symbol: str, 
    base_config: Dict,
    max_distance: int,
    min_confluence: int,
    min_level_score: int
) -> Tuple[bool, str, float, Dict]:
    """
    Génère un signal avec les filtres MenthorQ.
    
    Retourne: (valid, direction, confidence, menthorq_info)
    """
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, {}
    
    # Analyser MenthorQ
    mq = analyze_menthorq(snapshot, symbol)
    
    # 🆕 FILTRE 1: MAX_DISTANCE
    if mq['nearest_distance'] > max_distance:
        return False, "", 0, {'reject': 'DISTANCE'}
    
    # 🆕 FILTRE 2: MIN_CONFLUENCE
    if mq['confluence_count'] < min_confluence:
        return False, "", 0, {'reject': 'CONFLUENCE'}
    
    # 🆕 FILTRE 3: MIN_LEVEL_SCORE
    if mq['max_score_in_zone'] < min_level_score:
        return False, "", 0, {'reject': 'LEVEL_SCORE'}
    
    # Layer 1: MenthorQ Score
    menthorq_score = max(0, 1 - mq['nearest_distance'] / 25)
    if mq['nearest_level'] in STRONG_LEVELS:
        menthorq_score = min(1.0, menthorq_score * 1.3)
    layer1 = menthorq_score * 0.50
    
    # Layer 2: OrderFlow
    delta = snapshot.get('delta', 0) or 0
    cum_delta = snapshot.get('cum_delta_session', 0) or 0
    of_score = min(1.0, (abs(delta) / 400 + abs(cum_delta) / 800) / 2) * 0.5 + 0.3
    layer2 = of_score * 0.30
    
    # Layer 3: Context
    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    ctx_score = min(1.0, abs(mia_score) * 2.5)
    layer3 = ctx_score * 0.20
    
    # Total confidence
    confidence = layer1 + layer2 + layer3
    
    # Vérifier seuils V8
    if layer1 < 0.30 * 0.50:
        return False, "", confidence, {'reject': 'L1'}
    if layer2 < base_config['min_layer2'] * 0.30:
        return False, "", confidence, {'reject': 'L2'}
    if layer3 < 0.20 * 0.20:
        return False, "", confidence, {'reject': 'L3'}
    if confidence < base_config['min_confidence']:
        return False, "", confidence, {'reject': 'CONF'}
    
    # Direction
    mia_threshold = base_config['mia_threshold']
    if mia_score > mia_threshold:
        direction = "LONG"
    elif mia_score < -mia_threshold:
        direction = "SHORT"
    else:
        return False, "", confidence, {'reject': 'NEUTRAL'}
    
    return True, direction, confidence, mq

# ═══════════════════════════════════════════════════════════════════════════════
#              SIMULATION TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], tp_ticks: int, sl_ticks: int) -> Tuple[float, str]:
    
    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']
    
    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)
    
    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp = entry - tp_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp = entry + tp_ticks * tick_size
    
    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:
            return 0, "TIMEOUT"
        
        high = snap.get('high') or snap.get('mid', entry)
        low = snap.get('low') or snap.get('mid', entry)
        
        if direction == "SHORT":
            if high >= sl:
                return -sl_ticks * tick_value, "LOSS"
            if low <= tp:
                return tp_ticks * tick_value, "WIN"
        else:
            if low <= sl:
                return -sl_ticks * tick_value, "LOSS"
            if high >= tp:
                return tp_ticks * tick_value, "WIN"
    
    return 0, "TIMEOUT"

# ═══════════════════════════════════════════════════════════════════════════════
#              BACKTEST PAR SESSION × SYMBOLE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(
    session_name: str,
    symbol: str,
    all_data: Dict,
    base_config: Dict,
    max_distance: int,
    min_confluence: int,
    min_level_score: int
) -> Dict:
    """Backtest avec filtres MenthorQ."""
    
    trades = []
    cooldown_ms = base_config['cooldown_min'] * 60 * 1000
    tp_ticks = base_config['tp_ticks']
    sl_ticks = base_config['sl_ticks']
    
    for day, day_data in all_data.items():
        snapshots = day_data.get(symbol, [])
        if not snapshots:
            continue
        
        last_trade_time = 0
        session_trades = 0
        
        for i, snap in enumerate(snapshots):
            if session_trades >= 10:
                break
            
            t_ms = snap.get('t_ms', 0)
            hour, minute = get_paris_time(t_ms)
            
            current_session = get_session(hour, minute)
            if current_session != session_name:
                continue
            
            if t_ms - last_trade_time < cooldown_ms:
                continue
            
            valid, direction, confidence, mq_info = generate_signal(
                snap, symbol, base_config, max_distance, min_confluence, min_level_score
            )
            
            if not valid:
                continue
            
            future = snapshots[i+1:i+301]
            if len(future) < 10:
                continue
            
            pnl, result = simulate_trade(snap, direction, symbol, future, tp_ticks, sl_ticks)
            
            trades.append({
                'pnl': pnl,
                'result': result,
                'confluence': mq_info.get('confluence_count', 0),
                'level_score': mq_info.get('max_score_in_zone', 0),
            })
            
            last_trade_time = t_ms
            session_trades += 1
    
    # Stats
    if not trades:
        return {'trades': 0, 'pnl': 0, 'wr': 0, 'pf': 0, 'avg_confluence': 0, 'avg_score': 0}
    
    total_pnl = sum(t['pnl'] for t in trades)
    winners = [t for t in trades if t['pnl'] > 0]
    losers = [t for t in trades if t['pnl'] < 0]
    
    wr = len(winners) / len(trades) * 100 if trades else 0
    
    gross_profit = sum(t['pnl'] for t in winners) if winners else 0
    gross_loss = abs(sum(t['pnl'] for t in losers)) if losers else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    avg_confluence = sum(t['confluence'] for t in trades) / len(trades)
    avg_score = sum(t['level_score'] for t in trades) / len(trades)
    
    return {
        'trades': len(trades),
        'pnl': total_pnl,
        'wr': wr,
        'pf': pf,
        'avg_confluence': avg_confluence,
        'avg_score': avg_score,
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("          🎯 BACKTEST V9 - OPTIMISATION SEUILS MENTHORQ")
    print("=" * 100)
    print(f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  BASE: Configs V8 optimales (TP/SL, Cooldown, Confidence, Layer2, MIA)      │
├─────────────────────────────────────────────────────────────────────────────┤
│  PARAMÈTRES À OPTIMISER:                                                    │
│                                                                             │
│    MAX_DISTANCE:    {MAX_DISTANCE_GRID}              │
│    MIN_CONFLUENCE:  {MIN_CONFLUENCE_GRID}                                              │
│    MIN_LEVEL_SCORE: {MIN_LEVEL_SCORE_GRID} (0=any, 1=faible+, 2=moyen+, 3=fort)     │
│                                                                             │
│  Combinaisons: 8 × 3 × 4 = 96 par session/symbole                           │
│  Total: 576 backtests                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  CLASSIFICATION DES NIVEAUX:                                                │
│    FORT (3):   gex_1, gex_2, hvl, gamma_wall_level, vwap                    │
│    MOYEN (2):  gex_3-5, hvl_0dte, call/put_resist, blind_spot_1-2           │
│    FAIBLE (1): vwap_bands, blind_spot_3, 0dte walls                         │
└─────────────────────────────────────────────────────────────────────────────┘
""")

    # Charger données
    print("📂 Chargement des données...")
    all_data = {}
    days_loaded = 0
    
    for i, day in enumerate(DAYS_TO_TEST):
        progress_bar(i + 1, len(DAYS_TO_TEST), "Chargement")
        all_data[day] = {}
        has_data = False
        
        for symbol in ["ES", "NQ"]:
            file_path = find_data_file(day, symbol)
            if file_path:
                snapshots = load_snapshots(file_path)
                all_data[day][symbol] = snapshots
                if snapshots:
                    has_data = True
        
        if has_data:
            days_loaded += 1
    
    print(f"\n   📊 {days_loaded} jours chargés")
    
    if days_loaded == 0:
        print("❌ Aucune donnée!")
        return
    
    # Stocker résultats
    optimal_configs = {}
    v8_baseline = {}
    
    # Combinaisons MenthorQ
    mq_combos = list(product(MAX_DISTANCE_GRID, MIN_CONFLUENCE_GRID, MIN_LEVEL_SCORE_GRID))
    
    # ═══════════════════════════════════════════════════════════════
    #                    BOUCLE PAR SESSION × SYMBOLE
    # ═══════════════════════════════════════════════════════════════
    
    for session_name in SESSIONS.keys():
        for symbol in ["ES", "NQ"]:
            combo_key = f"{session_name}_{symbol}"
            base_config = V8_CONFIGS[combo_key]
            
            print(f"\n{'='*80}")
            print(f"🔍 OPTIMISATION: {combo_key}")
            print(f"   Base V8: TP={base_config['tp_ticks']}, SL={base_config['sl_ticks']}, Conf={base_config['min_confidence']}")
            print(f"{'='*80}")
            
            # D'abord, calculer baseline V8 (avec distance par défaut)
            baseline = run_backtest(
                session_name, symbol, all_data, base_config,
                max_distance=10 if symbol == "ES" else 15,
                min_confluence=1,
                min_level_score=0
            )
            v8_baseline[combo_key] = baseline
            print(f"   📊 Baseline V8: {baseline['trades']} trades | WR: {baseline['wr']:.1f}% | PnL: ${baseline['pnl']:+,.0f}")
            
            # Optimiser MenthorQ
            best_result = None
            best_pnl = float('-inf')
            
            for idx, (max_dist, min_conf, min_score) in enumerate(mq_combos):
                if (idx + 1) % 24 == 0:
                    progress_bar(idx + 1, len(mq_combos), f"   {combo_key}")
                
                result = run_backtest(
                    session_name, symbol, all_data, base_config,
                    max_dist, min_conf, min_score
                )
                
                # Score: PnL + bonus pour meilleur WR
                score = result['pnl'] + (result['wr'] - 50) * 10
                
                if score > best_pnl and result['trades'] >= 3:
                    best_pnl = score
                    best_result = {
                        'max_distance': max_dist,
                        'min_confluence': min_conf,
                        'min_level_score': min_score,
                        **result
                    }
            
            progress_bar(len(mq_combos), len(mq_combos), f"   {combo_key}")
            
            if best_result:
                optimal_configs[combo_key] = {
                    **base_config,
                    'max_distance': best_result['max_distance'],
                    'min_confluence': best_result['min_confluence'],
                    'min_level_score': best_result['min_level_score'],
                    'trades': best_result['trades'],
                    'pnl': best_result['pnl'],
                    'wr': best_result['wr'],
                    'pf': best_result['pf'],
                    'avg_confluence': best_result['avg_confluence'],
                    'avg_score': best_result['avg_score'],
                }
                
                improvement = best_result['pnl'] - baseline['pnl']
                
                print(f"\n   🏆 CONFIG OPTIMALE {combo_key}:")
                print(f"      MAX_DISTANCE: {best_result['max_distance']} ticks")
                print(f"      MIN_CONFLUENCE: {best_result['min_confluence']} niveaux")
                print(f"      MIN_LEVEL_SCORE: {best_result['min_level_score']} ({'any' if best_result['min_level_score']==0 else 'faible+' if best_result['min_level_score']==1 else 'moyen+' if best_result['min_level_score']==2 else 'FORT'})")
                print(f"      → {best_result['trades']} trades | WR: {best_result['wr']:.1f}% | PnL: ${best_result['pnl']:+,.0f}")
                print(f"      → Amélioration vs V8: ${improvement:+,.0f}")

    # ═══════════════════════════════════════════════════════════════
    #                    RÉSUMÉ FINAL
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 110)
    print("                    🏆 RÉSUMÉ - CONFIGS V9 OPTIMALES (MENTHORQ)")
    print("=" * 110)
    
    print(f"\n{'Session':<15} {'Sym':<4} {'Dist':<5} {'Conf':<5} {'Score':<6} {'Trades':<7} {'WR%':<6} {'PnL V9':<12} {'PnL V8':<12} {'Δ':<10}")
    print("-" * 110)
    
    total_pnl_v9 = 0
    total_pnl_v8 = 0
    total_trades = 0
    
    for combo_key, cfg in optimal_configs.items():
        session = combo_key.rsplit('_', 1)[0]
        symbol = combo_key.rsplit('_', 1)[1]
        baseline_pnl = v8_baseline[combo_key]['pnl']
        improvement = cfg['pnl'] - baseline_pnl
        
        score_label = ['any', 'faible+', 'moyen+', 'FORT'][cfg['min_level_score']]
        
        marker = "📈" if improvement > 0 else "📉" if improvement < 0 else "➖"
        
        print(f"{session:<15} {symbol:<4} {cfg['max_distance']:<5} {cfg['min_confluence']:<5} {score_label:<6} {cfg['trades']:<7} {cfg['wr']:<5.1f}% ${cfg['pnl']:>+10,.0f} ${baseline_pnl:>+10,.0f} {marker}${improvement:>+8,.0f}")
        
        total_pnl_v9 += cfg['pnl']
        total_pnl_v8 += baseline_pnl
        total_trades += cfg['trades']
    
    print("-" * 110)
    improvement_total = total_pnl_v9 - total_pnl_v8
    print(f"{'TOTAL':<15} {'':<4} {'':<5} {'':<5} {'':<6} {total_trades:<7} {'':<6} ${total_pnl_v9:>+10,.0f} ${total_pnl_v8:>+10,.0f} {'📈' if improvement_total > 0 else '📉'}${improvement_total:>+8,.0f}")

    # ═══════════════════════════════════════════════════════════════
    #                    ANALYSE PAR PARAMÈTRE
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("                    📊 ANALYSE PAR PARAMÈTRE")
    print("=" * 80)
    
    # Distance optimale
    dist_counts = defaultdict(int)
    for cfg in optimal_configs.values():
        dist_counts[cfg['max_distance']] += 1
    
    print("\n   MAX_DISTANCE optimal:")
    for dist, count in sorted(dist_counts.items()):
        bar = "█" * count
        print(f"      {dist:>2} ticks: {bar} ({count})")
    
    # Confluence optimale
    conf_counts = defaultdict(int)
    for cfg in optimal_configs.values():
        conf_counts[cfg['min_confluence']] += 1
    
    print("\n   MIN_CONFLUENCE optimal:")
    for conf, count in sorted(conf_counts.items()):
        bar = "█" * count
        print(f"      {conf} niveaux: {bar} ({count})")
    
    # Score optimal
    score_counts = defaultdict(int)
    for cfg in optimal_configs.values():
        score_counts[cfg['min_level_score']] += 1
    
    print("\n   MIN_LEVEL_SCORE optimal:")
    labels = {0: 'any', 1: 'faible+', 2: 'moyen+', 3: 'FORT'}
    for score, count in sorted(score_counts.items()):
        bar = "█" * count
        print(f"      {labels[score]:>7}: {bar} ({count})")

    # ═══════════════════════════════════════════════════════════════
    #                    CODE PRODUCTION
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 100)
    print("                    🚀 CODE POUR PRODUCTION (V9 COMPLET)")
    print("=" * 100)
    
    print("""
# ═══════════════════════════════════════════════════════════════════════════════
#              CONFIG V9 - OPTIMISÉE PAR SESSION × SYMBOLE (MENTHORQ INCLUS)
# ═══════════════════════════════════════════════════════════════════════════════
""")
    
    print("OPTIMAL_CONFIGS_V9 = {")
    for combo_key, cfg in optimal_configs.items():
        score_label = ['any', 'faible+', 'moyen+', 'FORT'][cfg['min_level_score']]
        print(f"""    '{combo_key}': {{
        # TP/SL (V8)
        'tp_ticks': {cfg['tp_ticks']},
        'sl_ticks': {cfg['sl_ticks']},
        'cooldown_min': {cfg['cooldown_min']},
        # Seuils (V8)
        'min_confidence': {cfg['min_confidence']},
        'min_layer2': {cfg['min_layer2']},
        'mia_threshold': {cfg['mia_threshold']},
        # MenthorQ (V9)
        'max_distance': {cfg['max_distance']},
        'min_confluence': {cfg['min_confluence']},
        'min_level_score': {cfg['min_level_score']},  # {score_label}
        # Performance: {cfg['trades']} trades, WR {cfg['wr']:.1f}%, PnL ${cfg['pnl']:+,.0f}
    }},""")
    print("}")
    
    # CSV
    csv_path = Path("backtest_v9_menthorq_results.csv")
    with open(csv_path, 'w') as f:
        f.write("Session,Symbol,TP,SL,Cooldown,Confidence,Layer2,MIA,MaxDist,MinConf,MinScore,Trades,WR,PF,PnL,AvgConf,AvgScore\n")
        for combo_key, cfg in optimal_configs.items():
            session = combo_key.rsplit('_', 1)[0]
            symbol = combo_key.rsplit('_', 1)[1]
            f.write(f"{session},{symbol},{cfg['tp_ticks']},{cfg['sl_ticks']},{cfg['cooldown_min']},{cfg['min_confidence']},{cfg['min_layer2']},{cfg['mia_threshold']},{cfg['max_distance']},{cfg['min_confluence']},{cfg['min_level_score']},{cfg['trades']},{cfg['wr']:.1f},{cfg['pf']:.2f},{cfg['pnl']:.0f},{cfg['avg_confluence']:.2f},{cfg['avg_score']:.2f}\n")
    
    print(f"\n✅ Résultats sauvegardés: {csv_path}")
    print("\n✅ OPTIMISATION V9 TERMINÉE!")


if __name__ == "__main__":
    main()
