#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
            BACKTEST OPTIMISATION COMPLÈTE - CONFIG RESTAURÉE
═══════════════════════════════════════════════════════════════════════════════

Base: Config qui marchait (11-12 déc matin): +$838 sur 2 jours

Tests:
- MIN_TOTAL_CONFIDENCE: 0.25, 0.30, 0.35, 0.40, 0.45, 0.50
- Layer2 (OrderFlow): 0.15, 0.17, 0.20
- TP/SL ES: 12/12, 15/15, 15/12, 18/15
- Sessions: London, US Morning, Power Hour

Auteur: MIA IA System
Date: 13 Décembre 2025
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
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
QUALITY_SESSIONS = {
    'london': {'start': (8, 0), 'end': (11, 0)},
    'us_morning': {'start': (15, 50), 'end': (17, 0)},
    'power_hour': {'start': (20, 0), 'end': (21, 25)},
}

MENTHORQ_LEVELS = [
    'gex_1', 'gex_2', 'gex_3', 'hvl', 'hvl_0dte',
    'gamma_wall_0dte', 'gamma_wall_level',
    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
    'call_resistance', 'put_support', 'vwap',
]

# ═══════════════════════════════════════════════════════════════════════════════
#              GRILLE DE PARAMÈTRES À TESTER
# ═══════════════════════════════════════════════════════════════════════════════

PARAM_GRID = {
    'min_confidence': [0.25, 0.30, 0.35, 0.40, 0.45, 0.50],
    'min_layer2': [0.15, 0.17, 0.20],
    'es_tp_sl': [(12, 12), (15, 15), (15, 12), (18, 15)],  # (TP, SL)
    'mia_threshold': [0.20, 0.22, 0.25],
    'cooldown_min': [15, 20, 25],
}

# Config de base (restaurée)
BASE_CONFIG = {
    'min_layer1': 0.30,
    'min_layer3': 0.20,
    'max_distance': {'ES': 10, 'NQ': 15},
    'nq_tp': 31,
    'nq_sl': 25,
    'max_trades_per_day': 20,
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


def is_in_quality_session(hour: int, minute: int) -> Tuple[bool, str]:
    time_val = time_to_minutes(hour, minute)
    for name, session in QUALITY_SESSIONS.items():
        s = time_to_minutes(session['start'][0], session['start'][1])
        e = time_to_minutes(session['end'][0], session['end'][1])
        if s <= time_val < e:
            return True, name
    return False, "OFF"


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

def generate_signal(snapshot: Dict, symbol: str, params: Dict, hour: int, minute: int) -> Tuple[bool, str, float, str]:
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "NO_PRICE"

    # Vérifier session qualité
    in_session, session = is_in_quality_session(hour, minute)
    if not in_session:
        return False, "", 0, "OFF_SESSION"

    # Distance au niveau
    level_name, level_price, distance = find_nearest_level(snapshot, symbol)
    max_dist = BASE_CONFIG['max_distance'].get(symbol, 15)
    if distance > max_dist:
        return False, "", 0, "DIST"

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
        return False, "", confidence, "L1"
    if layer2 < params['min_layer2'] * 0.30:
        return False, "", confidence, "L2"
    if layer3 < BASE_CONFIG['min_layer3'] * 0.20:
        return False, "", confidence, "L3"
    if confidence < params['min_confidence']:
        return False, "", confidence, "CONF"

    # Direction
    if mia_score > params['mia_threshold']:
        direction = "LONG"
    elif mia_score < -params['mia_threshold']:
        direction = "SHORT"
    else:
        return False, "", confidence, "NEUTRAL"

    return True, direction, confidence, session

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], params: Dict) -> Tuple[float, str]:

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    # TP/SL selon symbole
    if symbol == "ES":
        tp_ticks, sl_ticks = params['es_tp_sl']
    else:
        tp_ticks = BASE_CONFIG['nq_tp']
        sl_ticks = BASE_CONFIG['nq_sl']

    # Niveaux
    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp = entry - tp_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp = entry + tp_ticks * tick_size

    # Simulation
    for snap in future_snaps[:200]:
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
#                           BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(params: Dict, all_data: Dict) -> Dict:
    trades = []
    cooldown_ms = params['cooldown_min'] * 60 * 1000

    for day, day_data in all_data.items():
        day_trades = 0

        for symbol in ["ES", "NQ"]:
            snapshots = day_data.get(symbol, [])
            if not snapshots:
                continue

            last_trade_time = 0

            for i, snap in enumerate(snapshots):
                if day_trades >= BASE_CONFIG['max_trades_per_day']:
                    break

                t_ms = snap.get('t_ms', 0)
                hour, minute = get_paris_time(t_ms)

                if t_ms - last_trade_time < cooldown_ms:
                    continue

                valid, direction, confidence, session = generate_signal(
                    snap, symbol, params, hour, minute
                )

                if not valid:
                    continue

                future = snapshots[i+1:i+201]
                if len(future) < 10:
                    continue

                pnl, result = simulate_trade(snap, direction, symbol, future, params)

                trades.append({
                    'symbol': symbol,
                    'direction': direction,
                    'pnl': pnl,
                    'result': result,
                    'session': session,
                    'confidence': confidence,
                })

                last_trade_time = t_ms
                day_trades += 1

    # Stats
    if not trades:
        return {'total_trades': 0, 'pnl': 0, 'wr': 0, 'pf': 0}

    total_pnl = sum(t['pnl'] for t in trades)
    winners = [t for t in trades if t['pnl'] > 0]
    losers = [t for t in trades if t['pnl'] < 0]

    wr = len(winners) / len(trades) * 100 if trades else 0

    gross_profit = sum(t['pnl'] for t in winners) if winners else 0
    gross_loss = abs(sum(t['pnl'] for t in losers)) if losers else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    # Par session
    by_session = {}
    for session in ['london', 'us_morning', 'power_hour']:
        sess_trades = [t for t in trades if t['session'] == session]
        if sess_trades:
            by_session[session] = {
                'trades': len(sess_trades),
                'pnl': sum(t['pnl'] for t in sess_trades),
                'wr': len([t for t in sess_trades if t['pnl'] > 0]) / len(sess_trades) * 100
            }

    # Par symbole
    es_trades = [t for t in trades if t['symbol'] == 'ES']
    nq_trades = [t for t in trades if t['symbol'] == 'NQ']

    return {
        'total_trades': len(trades),
        'pnl': total_pnl,
        'wr': wr,
        'pf': pf,
        'by_session': by_session,
        'es_pnl': sum(t['pnl'] for t in es_trades),
        'nq_pnl': sum(t['pnl'] for t in nq_trades),
        'es_trades': len(es_trades),
        'nq_trades': len(nq_trades),
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("          🎯 BACKTEST OPTIMISATION - CONFIG RESTAURÉE")
    print("=" * 100)
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│  PARAMÈTRES TESTÉS                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  MIN_CONFIDENCE: {PARAM_GRID['min_confidence']}                     │
│  Layer2:         {PARAM_GRID['min_layer2']}                         │
│  ES TP/SL:       {PARAM_GRID['es_tp_sl']}                           │
│  MIA Threshold:  {PARAM_GRID['mia_threshold']}                      │
│  Cooldown:       {PARAM_GRID['cooldown_min']} min                   │
│                                                                     │
│  Sessions: London (8-11h), US Morning (15:50-17h), Power (20-21:25) │
└─────────────────────────────────────────────────────────────────────┘
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

    # Générer toutes les combinaisons
    combinations = list(product(
        PARAM_GRID['min_confidence'],
        PARAM_GRID['min_layer2'],
        PARAM_GRID['es_tp_sl'],
        PARAM_GRID['mia_threshold'],
        PARAM_GRID['cooldown_min'],
    ))

    print(f"\n🔄 Test de {len(combinations)} combinaisons...")

    results = []

    for i, (conf, l2, es_tpsl, mia, cd) in enumerate(combinations):
        progress_bar(i + 1, len(combinations), "Optimisation")

        params = {
            'min_confidence': conf,
            'min_layer2': l2,
            'es_tp_sl': es_tpsl,
            'mia_threshold': mia,
            'cooldown_min': cd,
        }

        result = run_backtest(params, all_data)
        result['params'] = params
        results.append(result)

    # Trier par P&L
    results.sort(key=lambda x: x['pnl'], reverse=True)

    # Afficher TOP 10
    print("\n" + "=" * 100)
    print("                    🏆 TOP 10 CONFIGURATIONS")
    print("=" * 100)

    print(f"\n{'Rank':<5} {'Conf%':<6} {'L2%':<5} {'TP/SL':<8} {'MIA':<5} {'CD':<4} {'Trades':<7} {'WR%':<6} {'PF':<5} {'PnL':<12}")
    print("-" * 80)

    for i, r in enumerate(results[:10]):
        p = r['params']
        tp, sl = p['es_tp_sl']
        print(f"{i+1:<5} {p['min_confidence']*100:<5.0f}% {p['min_layer2']*100:<4.0f}% {tp}/{sl:<5} {p['mia_threshold']:<5.2f} {p['cooldown_min']:<4} {r['total_trades']:<7} {r['wr']:<5.1f}% {r['pf']:<5.2f} ${r['pnl']:>+10,.0f}")

    # Meilleure config
    best = results[0]
    if best['pnl'] > 0:
        print("\n" + "=" * 100)
        print("                    🏆 MEILLEURE CONFIGURATION")
        print("=" * 100)

        p = best['params']
        tp, sl = p['es_tp_sl']

        print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│  PARAMÈTRES OPTIMAUX                                                │
├─────────────────────────────────────────────────────────────────────┤
│  MIN_TOTAL_CONFIDENCE: {p['min_confidence']*100:.0f}%                                       │
│  Layer2 (OrderFlow):   {p['min_layer2']*100:.0f}%                                       │
│  ES TP/SL:             {tp}/{sl} ticks                                    │
│  MIA Threshold:        {p['mia_threshold']}                                        │
│  Cooldown:             {p['cooldown_min']} min                                       │
├─────────────────────────────────────────────────────────────────────┤
│  RÉSULTATS                                                          │
├─────────────────────────────────────────────────────────────────────┤
│  Trades:        {best['total_trades']}                                               │
│  Win Rate:      {best['wr']:.1f}%                                            │
│  Profit Factor: {best['pf']:.2f}                                             │
│  P&L Total:     ${best['pnl']:+,.0f}                                         │
│  ES P&L:        ${best['es_pnl']:+,.0f}                                         │
│  NQ P&L:        ${best['nq_pnl']:+,.0f}                                         │
└─────────────────────────────────────────────────────────────────────┘
""")

        # Par session
        print("\n📊 Performance par Session:")
        for session, stats in best.get('by_session', {}).items():
            print(f"   {session.upper()}: {stats['trades']} trades | WR: {stats['wr']:.1f}% | ${stats['pnl']:+,.0f}")

        # Code pour production
        print(f"""
🚀 CODE POUR PRODUCTION (config/trading_params.py):
────────────────────────────────────────────────────
MIN_TOTAL_CONFIDENCE = {{
    'ES': {p['min_confidence']},
    'NQ': {p['min_confidence']},
    'RTY': {p['min_confidence']},
}}

MIN_LAYER_CONFIDENCE = {{
    'ES': {{'layer1': 0.30, 'layer2': {p['min_layer2']}, 'layer3': 0.20}},
    'NQ': {{'layer1': 0.30, 'layer2': {p['min_layer2']}, 'layer3': 0.20}},
}}

# ES TP/SL
'tp_ticks': {tp},
'sl_ticks': {sl},
""")

    else:
        print("\n⚠️ Aucune configuration rentable trouvée!")
        print("   Le marché était peut-être difficile sur cette période.")

    # Sauvegarder résultats
    csv_path = Path("backtest_optimisation_results.csv")
    with open(csv_path, 'w') as f:
        f.write("Conf,L2,TP,SL,MIA,CD,Trades,WR,PF,PnL,ES_PnL,NQ_PnL\n")
        for r in results:
            p = r['params']
            tp, sl = p['es_tp_sl']
            f.write(f"{p['min_confidence']},{p['min_layer2']},{tp},{sl},{p['mia_threshold']},{p['cooldown_min']},{r['total_trades']},{r['wr']:.1f},{r['pf']:.2f},{r['pnl']:.0f},{r.get('es_pnl',0):.0f},{r.get('nq_pnl',0):.0f}\n")

    print(f"\n✅ Résultats sauvegardés: {csv_path}")
    print("\n✅ OPTIMISATION TERMINÉE!")


if __name__ == "__main__":
    main()
