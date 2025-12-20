#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
            BACKTEST V8 - OPTIMISATION PAR SESSION × SYMBOLE
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF: Trouver les meilleurs paramètres pour CHAQUE combinaison:
   - London × ES
   - London × NQ  
   - US Morning × ES
   - US Morning × NQ
   - Power Hour × ES
   - Power Hour × NQ

📊 MÉTHODE: Optimisation en 2 passes pour éviter explosion combinatoire
   PASSE 1: Trouver meilleur TP/SL et Cooldown
   PASSE 2: Optimiser seuils (Confidence, Layer2, MIA)

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

# Sessions de qualité (heure Paris)
SESSIONS = {
    'LONDON': {'start': (8, 0), 'end': (11, 0), 'name': 'London 8h-11h'},
    'US_MORNING': {'start': (15, 50), 'end': (17, 0), 'name': 'US Morning 15:50-17h'},
    'POWER_HOUR': {'start': (20, 0), 'end': (21, 25), 'name': 'Power Hour 20h-21:25'},
}

MENTHORQ_LEVELS = [
    'gex_1', 'gex_2', 'gex_3', 'hvl', 'hvl_0dte',
    'gamma_wall_0dte', 'gamma_wall_level',
    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
    'call_resistance', 'put_support', 'vwap',
]

# ═══════════════════════════════════════════════════════════════════════════════
#              GRILLES DE PARAMÈTRES
# ═══════════════════════════════════════════════════════════════════════════════

# PASSE 1: TP/SL et Cooldown
TP_SL_GRID = {
    'ES': [(12, 12), (15, 15), (15, 12), (18, 15), (20, 15), (20, 20)],
    'NQ': [(25, 20), (30, 25), (31, 25), (35, 25), (38, 25), (40, 30)],
}

COOLDOWN_GRID = [15, 20, 25]

# PASSE 2: Seuils
CONFIDENCE_GRID = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 0.95, 1.00]
LAYER2_GRID = [0.15, 0.17, 0.20]
MIA_GRID = [0.20, 0.22, 0.25]

# Config de base
BASE_CONFIG = {
    'min_layer1': 0.30,
    'min_layer3': 0.20,
    'max_distance': {'ES': 10, 'NQ': 15},
    'max_trades_per_session': 10,
}

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


def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float, float]:
    mid = snapshot.get('mid', 0)
    tick_size = SYMBOLS[symbol]['tick_size']
    nearest_name, nearest_dist, nearest_price = "", float('inf'), 0

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

def generate_signal(snapshot: Dict, symbol: str, params: Dict) -> Tuple[bool, str, float]:
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0

    # Distance au niveau
    level_name, level_price, distance = find_nearest_level(snapshot, symbol)
    max_dist = BASE_CONFIG['max_distance'].get(symbol, 15)
    if distance > max_dist:
        return False, "", 0

    # Layer 1: MenthorQ
    menthorq_score = max(0, 1 - distance / 25)
    if level_name in ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level']:
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

    # Vérifier seuils
    if layer1 < BASE_CONFIG['min_layer1'] * 0.50:
        return False, "", confidence
    if layer2 < params.get('min_layer2', 0.15) * 0.30:
        return False, "", confidence
    if layer3 < BASE_CONFIG['min_layer3'] * 0.20:
        return False, "", confidence
    if confidence < params.get('min_confidence', 0.50):
        return False, "", confidence

    # Direction
    mia_threshold = params.get('mia_threshold', 0.22)
    if mia_score > mia_threshold:
        direction = "LONG"
    elif mia_score < -mia_threshold:
        direction = "SHORT"
    else:
        return False, "", confidence

    return True, direction, confidence

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], tp_ticks: int, sl_ticks: int) -> Tuple[float, str]:

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    # Niveaux
    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp = entry - tp_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp = entry + tp_ticks * tick_size

    # Simulation
    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:  # Max 1h
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
#                           BACKTEST PAR SESSION × SYMBOLE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest_session_symbol(
    session_name: str, 
    symbol: str, 
    all_data: Dict, 
    params: Dict,
    tp_ticks: int,
    sl_ticks: int,
    cooldown_min: int
) -> Dict:
    """Backtest pour UNE session et UN symbole spécifique."""
    
    trades = []
    cooldown_ms = cooldown_min * 60 * 1000
    session = SESSIONS[session_name]

    for day, day_data in all_data.items():
        snapshots = day_data.get(symbol, [])
        if not snapshots:
            continue

        last_trade_time = 0
        session_trades = 0

        for i, snap in enumerate(snapshots):
            if session_trades >= BASE_CONFIG['max_trades_per_session']:
                break

            t_ms = snap.get('t_ms', 0)
            hour, minute = get_paris_time(t_ms)

            # Vérifier si dans LA session ciblée
            current_session = get_session(hour, minute)
            if current_session != session_name:
                continue

            if t_ms - last_trade_time < cooldown_ms:
                continue

            valid, direction, confidence = generate_signal(snap, symbol, params)

            if not valid:
                continue

            future = snapshots[i+1:i+301]
            if len(future) < 10:
                continue

            pnl, result = simulate_trade(snap, direction, symbol, future, tp_ticks, sl_ticks)

            trades.append({
                'pnl': pnl,
                'result': result,
                'confidence': confidence,
            })

            last_trade_time = t_ms
            session_trades += 1

    # Stats
    if not trades:
        return {'trades': 0, 'pnl': 0, 'wr': 0, 'pf': 0}

    total_pnl = sum(t['pnl'] for t in trades)
    winners = [t for t in trades if t['pnl'] > 0]
    losers = [t for t in trades if t['pnl'] < 0]

    wr = len(winners) / len(trades) * 100 if trades else 0

    gross_profit = sum(t['pnl'] for t in winners) if winners else 0
    gross_loss = abs(sum(t['pnl'] for t in losers)) if losers else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    return {
        'trades': len(trades),
        'pnl': total_pnl,
        'wr': wr,
        'pf': pf,
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("          🎯 BACKTEST V8 - OPTIMISATION PAR SESSION × SYMBOLE")
    print("=" * 100)
    print(f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  OBJECTIF: Trouver les meilleurs paramètres pour CHAQUE combinaison         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Session        │ ES Config │ NQ Config                                    │
│   ─────────────────────────────────────────                                 │
│   LONDON         │ #1        │ #2                                           │
│   US_MORNING     │ #3        │ #4                                           │
│   POWER_HOUR     │ #5        │ #6                                           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  MÉTHODE: Optimisation en 2 passes                                          │
│    PASSE 1: Trouver meilleur TP/SL + Cooldown                               │
│    PASSE 2: Optimiser seuils (Confidence, Layer2, MIA)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  PARAMÈTRES:                                                                │
│    Confidence: {CONFIDENCE_GRID}                                            │
│    Layer2:     {LAYER2_GRID}                                                │
│    MIA:        {MIA_GRID}                                                   │
│    Cooldown:   {COOLDOWN_GRID}                                              │
│    ES TP/SL:   {TP_SL_GRID['ES']}                                           │
│    NQ TP/SL:   {TP_SL_GRID['NQ']}                                           │
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

    # Stocker les résultats optimaux
    optimal_configs = {}

    # ═══════════════════════════════════════════════════════════════
    #                    BOUCLE PAR SESSION × SYMBOLE
    # ═══════════════════════════════════════════════════════════════

    for session_name in SESSIONS.keys():
        for symbol in ["ES", "NQ"]:
            combo_key = f"{session_name}_{symbol}"
            print(f"\n{'='*80}")
            print(f"🔍 OPTIMISATION: {session_name} × {symbol}")
            print(f"{'='*80}")

            # ═══ PASSE 1: TP/SL + COOLDOWN ═══
            print(f"\n   📊 PASSE 1: Recherche meilleur TP/SL + Cooldown...")
            
            tp_sl_options = TP_SL_GRID[symbol]
            passe1_combos = list(product(tp_sl_options, COOLDOWN_GRID))
            
            best_passe1 = None
            best_passe1_pnl = float('-inf')

            for idx, ((tp, sl), cooldown) in enumerate(passe1_combos):
                # Paramètres par défaut pour passe 1
                params = {
                    'min_confidence': 0.50,
                    'min_layer2': 0.17,
                    'mia_threshold': 0.22,
                }

                result = run_backtest_session_symbol(
                    session_name, symbol, all_data, params, tp, sl, cooldown
                )

                if result['pnl'] > best_passe1_pnl and result['trades'] >= 5:
                    best_passe1_pnl = result['pnl']
                    best_passe1 = {
                        'tp': tp, 'sl': sl, 'cooldown': cooldown,
                        'trades': result['trades'], 'pnl': result['pnl'],
                        'wr': result['wr'], 'pf': result['pf']
                    }

            if not best_passe1:
                print(f"   ⚠️ Aucune config rentable pour {combo_key}")
                continue

            print(f"   ✅ Meilleur TP/SL: {best_passe1['tp']}/{best_passe1['sl']} | Cooldown: {best_passe1['cooldown']}min")
            print(f"      → {best_passe1['trades']} trades | WR: {best_passe1['wr']:.1f}% | PnL: ${best_passe1['pnl']:+,.0f}")

            # ═══ PASSE 2: SEUILS ═══
            print(f"\n   📊 PASSE 2: Optimisation des seuils...")
            
            passe2_combos = list(product(CONFIDENCE_GRID, LAYER2_GRID, MIA_GRID))
            total_passe2 = len(passe2_combos)

            best_passe2 = None
            best_passe2_pnl = float('-inf')

            for idx, (conf, l2, mia) in enumerate(passe2_combos):
                if (idx + 1) % 20 == 0:
                    progress_bar(idx + 1, total_passe2, f"   {combo_key}")

                params = {
                    'min_confidence': conf,
                    'min_layer2': l2,
                    'mia_threshold': mia,
                }

                result = run_backtest_session_symbol(
                    session_name, symbol, all_data, params,
                    best_passe1['tp'], best_passe1['sl'], best_passe1['cooldown']
                )

                if result['pnl'] > best_passe2_pnl and result['trades'] >= 3:
                    best_passe2_pnl = result['pnl']
                    best_passe2 = {
                        'confidence': conf,
                        'layer2': l2,
                        'mia_threshold': mia,
                        'trades': result['trades'],
                        'pnl': result['pnl'],
                        'wr': result['wr'],
                        'pf': result['pf'],
                    }

            progress_bar(total_passe2, total_passe2, f"   {combo_key}")

            if best_passe2:
                optimal_configs[combo_key] = {
                    'session': session_name,
                    'symbol': symbol,
                    'tp': best_passe1['tp'],
                    'sl': best_passe1['sl'],
                    'cooldown': best_passe1['cooldown'],
                    'confidence': best_passe2['confidence'],
                    'layer2': best_passe2['layer2'],
                    'mia_threshold': best_passe2['mia_threshold'],
                    'trades': best_passe2['trades'],
                    'pnl': best_passe2['pnl'],
                    'wr': best_passe2['wr'],
                    'pf': best_passe2['pf'],
                }

                print(f"\n   🏆 CONFIG OPTIMALE {combo_key}:")
                print(f"      TP/SL: {best_passe1['tp']}/{best_passe1['sl']} | Cooldown: {best_passe1['cooldown']}min")
                print(f"      Confidence: {best_passe2['confidence']} | Layer2: {best_passe2['layer2']} | MIA: {best_passe2['mia_threshold']}")
                print(f"      → {best_passe2['trades']} trades | WR: {best_passe2['wr']:.1f}% | PnL: ${best_passe2['pnl']:+,.0f}")

    # ═══════════════════════════════════════════════════════════════
    #                    RÉSUMÉ FINAL
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 100)
    print("                    🏆 RÉSUMÉ - CONFIGS OPTIMALES PAR SESSION × SYMBOLE")
    print("=" * 100)

    print(f"\n{'Session':<15} {'Symbol':<6} {'TP/SL':<8} {'CD':<4} {'Conf':<6} {'L2':<6} {'MIA':<6} {'Trades':<7} {'WR%':<6} {'PnL':<12}")
    print("-" * 95)

    total_pnl = 0
    total_trades = 0

    for combo_key, cfg in optimal_configs.items():
        print(f"{cfg['session']:<15} {cfg['symbol']:<6} {cfg['tp']}/{cfg['sl']:<5} {cfg['cooldown']:<4} {cfg['confidence']:<6.2f} {cfg['layer2']:<6.2f} {cfg['mia_threshold']:<6.2f} {cfg['trades']:<7} {cfg['wr']:<5.1f}% ${cfg['pnl']:>+10,.0f}")
        total_pnl += cfg['pnl']
        total_trades += cfg['trades']

    print("-" * 95)
    print(f"{'TOTAL':<15} {'':<6} {'':<8} {'':<4} {'':<6} {'':<6} {'':<6} {total_trades:<7} {'':<6} ${total_pnl:>+10,.0f}")

    # ═══════════════════════════════════════════════════════════════
    #                    CODE PRODUCTION
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 100)
    print("                    🚀 CODE POUR PRODUCTION")
    print("=" * 100)

    print("""
# ═══════════════════════════════════════════════════════════════════════════════
#              CONFIG OPTIMISÉE PAR SESSION × SYMBOLE
# ═══════════════════════════════════════════════════════════════════════════════
""")

    print("OPTIMAL_CONFIGS = {")
    for combo_key, cfg in optimal_configs.items():
        print(f"""    '{combo_key}': {{
        'tp_ticks': {cfg['tp']},
        'sl_ticks': {cfg['sl']},
        'cooldown_min': {cfg['cooldown']},
        'min_confidence': {cfg['confidence']},
        'min_layer2': {cfg['layer2']},
        'mia_threshold': {cfg['mia_threshold']},
        # Performance: {cfg['trades']} trades, WR {cfg['wr']:.1f}%, PnL ${cfg['pnl']:+,.0f}
    }},""")
    print("}")

    print("""

# Utilisation dans le code:
def get_config(session: str, symbol: str) -> dict:
    key = f"{session}_{symbol}"
    return OPTIMAL_CONFIGS.get(key, OPTIMAL_CONFIGS['US_MORNING_NQ'])
""")

    # Sauvegarder CSV
    csv_path = Path("backtest_v8_session_symbol_results.csv")
    with open(csv_path, 'w') as f:
        f.write("Session,Symbol,TP,SL,Cooldown,Confidence,Layer2,MIA,Trades,WR,PF,PnL\n")
        for combo_key, cfg in optimal_configs.items():
            f.write(f"{cfg['session']},{cfg['symbol']},{cfg['tp']},{cfg['sl']},{cfg['cooldown']},{cfg['confidence']},{cfg['layer2']},{cfg['mia_threshold']},{cfg['trades']},{cfg['wr']:.1f},{cfg['pf']:.2f},{cfg['pnl']:.0f}\n")

    print(f"\n✅ Résultats sauvegardés: {csv_path}")
    print("\n✅ OPTIMISATION TERMINÉE!")


if __name__ == "__main__":
    main()
