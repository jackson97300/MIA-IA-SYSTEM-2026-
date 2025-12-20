"""
📊 BACKTEST #2: Distance aux Niveaux
=====================================

Teste différentes distances maximales aux niveaux MenthorQ.
Objectif: Trouver la distance optimale pour chaque symbole.

Date: 07/12/2025
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKTESTS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKTESTS_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from config.backtest_config import (
    SYMBOLS, MIN_TOTAL_CONFIDENCE, MIN_LAYER_CONFIDENCE,
    TP_SL_CONFIG, TICK_VALUES, TICK_SIZES,
    COOLDOWN_MS, MAX_TRADE_DURATION_MS, MAX_SNAPSHOTS_LOOKAHEAD,
    MLScores, get_session, get_distance_to_level, load_snapshots
)

# ============================================================================
# 🎯 CONFIGURATION
# ============================================================================

TEST_NAME = "Distance aux Niveaux MenthorQ"
TEST_DESCRIPTION = """
Teste différentes distances maximales aux niveaux.
Plus proche = moins de trades mais potentiellement plus précis ?
"""

DATE_RANGE = ["20251202", "20251203", "20251204", "20251205"]
DATA_MONTH = "DECEMBRE"
DATA_YEAR = 2025
TEST_SYMBOLS = ['ES', 'NQ']
TEST_SAMPLE_SIZE = 5000
TEST_DATES = 1

# ============================================================================
# 🔧 DISTANCES À TESTER
# ============================================================================

DISTANCE_VARIANTS = {
    'ES': [
        {'name': 'ES_5t', 'max_dist': 5},
        {'name': 'ES_8t', 'max_dist': 8},
        {'name': 'ES_10t', 'max_dist': 10},
        {'name': 'ES_12t', 'max_dist': 12},
        {'name': 'ES_15t_ACTUEL', 'max_dist': 15},
        {'name': 'ES_18t', 'max_dist': 18},
        {'name': 'ES_20t', 'max_dist': 20},
        {'name': 'ES_25t', 'max_dist': 25},
    ],
    'NQ': [
        {'name': 'NQ_10t', 'max_dist': 10},
        {'name': 'NQ_15t', 'max_dist': 15},
        {'name': 'NQ_20t', 'max_dist': 20},
        {'name': 'NQ_25t_ACTUEL', 'max_dist': 25},
        {'name': 'NQ_30t', 'max_dist': 30},
        {'name': 'NQ_35t', 'max_dist': 35},
        {'name': 'NQ_40t', 'max_dist': 40},
    ]
}

# ============================================================================
# CLASSES & FONCTIONS
# ============================================================================

@dataclass
class Signal:
    timestamp: int
    symbol: str
    direction: str
    price: float
    session: str
    delta: float
    distance: float
    level_name: str

@dataclass
class TradeResult:
    signal: Signal
    result: str
    pnl_ticks: float
    pnl_usd: float


def calculate_ml_scores(snap: Dict, symbol: str) -> MLScores:
    l1 = snap.get('layer1_score') or snap.get('menthorq_score', 0)
    l2 = snap.get('layer2_score') or snap.get('orderflow_score', 0)
    l3 = snap.get('layer3_score') or snap.get('context_score', 0)

    if l1 == 0 and l2 == 0 and l3 == 0:
        mid = snap.get('mid', 0)
        dist, _ = get_distance_to_level(snap, mid, symbol)
        l1 = max(0, min(1, 1 - dist / 100)) if dist < 9999 else 0.2
        delta = abs(snap.get('delta', 0))
        pressure = snap.get('pressure_strength', 0)
        l2 = max(0, min(1, delta / 500 + pressure * 0.5))
        l3 = 0.3

    total = l1 * 0.5 + l2 * 0.3 + l3 * 0.2
    return MLScores(layer1=l1, layer2=l2, layer3=l3, total=total)


def validate_signal(snap: Dict, symbol: str, max_distance: int) -> Tuple[Optional[Signal], str]:
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)

    if not ts or not mid:
        return None, "no_price"

    in_session, session = get_session(ts)
    if not in_session:
        return None, "out_of_session"

    if delta == 0:
        return None, "delta_zero"
    direction = "LONG" if delta > 0 else "SHORT"

    ml_scores = calculate_ml_scores(snap, symbol)
    ml_ok, _ = ml_scores.meets_thresholds(symbol)
    if not ml_ok:
        return None, "ml_reject"

    distance, level_name = get_distance_to_level(snap, mid, symbol)
    if distance > max_distance:
        return None, f"distance_{distance:.0f}t"

    return Signal(ts, symbol, direction, mid, session, delta, distance, level_name), "OK"


def simulate_trade(signal: Signal, subsequent: List[Dict]) -> TradeResult:
    cfg = TP_SL_CONFIG.get(signal.symbol, TP_SL_CONFIG['ES'])
    tv = TICK_VALUES.get(signal.symbol, 12.50)
    ts = TICK_SIZES.get(signal.symbol, 0.25)
    tp_ticks = cfg['tp_ticks']
    sl_ticks = cfg['sl_ticks']

    if signal.direction == "LONG":
        tp = signal.price + tp_ticks * ts
        sl = signal.price - sl_ticks * ts
    else:
        tp = signal.price - tp_ticks * ts
        sl = signal.price + sl_ticks * ts

    for snap in subsequent[:MAX_SNAPSHOTS_LOOKAHEAD]:
        if snap.get('t_ms', 0) - signal.timestamp > MAX_TRADE_DURATION_MS:
            break

        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))

        if signal.direction == "LONG":
            if high >= tp:
                return TradeResult(signal, "WIN", tp_ticks, tp_ticks * tv)
            if low <= sl:
                return TradeResult(signal, "LOSS", -sl_ticks, -sl_ticks * tv)
        else:
            if low <= tp:
                return TradeResult(signal, "WIN", tp_ticks, tp_ticks * tv)
            if high >= sl:
                return TradeResult(signal, "LOSS", -sl_ticks, -sl_ticks * tv)

    return TradeResult(signal, "BE", 0, 0)


def run_backtest_variant(all_data: Dict, symbol: str, max_distance: int) -> Dict:
    stats = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0, "distances": []}
    last_trade_time = 0

    for date_str, snaps in all_data.get(symbol, []):
        for i, snap in enumerate(snaps):
            signal, _ = validate_signal(snap, symbol, max_distance)
            if signal is None:
                continue

            if signal.timestamp - last_trade_time < COOLDOWN_MS:
                continue

            last_trade_time = signal.timestamp
            subsequent = snaps[i+1:i+1+MAX_SNAPSHOTS_LOOKAHEAD]
            trade = simulate_trade(signal, subsequent)

            stats["trades"] += 1
            stats["pnl"] += trade.pnl_usd
            stats["distances"].append(signal.distance)

            if trade.result == "WIN":
                stats["wins"] += 1
            elif trade.result == "LOSS":
                stats["losses"] += 1

    stats["win_rate"] = stats["wins"] / max(stats["trades"], 1) * 100
    stats["avg_distance"] = sum(stats["distances"]) / max(len(stats["distances"]), 1)
    del stats["distances"]  # Pas besoin de sauvegarder toutes les distances
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()

    is_test = not args.full
    dates = DATE_RANGE[:TEST_DATES] if is_test else DATE_RANGE

    print("="*100)
    print(f"📊 BACKTEST: {TEST_NAME}")
    print(f"   {'🧪 MODE TEST' if is_test else '📊 MODE COMPLET'}")
    print("="*100)
    print(TEST_DESCRIPTION)
    print(f"\n📅 Période: {dates[0]} → {dates[-1]}")

    # Charger données
    print(f"\n📥 Chargement...")
    all_data = {s: [] for s in TEST_SYMBOLS}

    for date in dates:
        for symbol in TEST_SYMBOLS:
            snaps = load_snapshots(date, symbol, DATA_MONTH, DATA_YEAR)
            if is_test and len(snaps) > TEST_SAMPLE_SIZE:
                snaps = snaps[:TEST_SAMPLE_SIZE]
            if snaps:
                all_data[symbol].append((date, snaps))

    total = sum(len(s) for sym in all_data.values() for _, s in sym)
    print(f"   Total: {total:,} snapshots")

    results = {}

    for symbol in TEST_SYMBOLS:
        print(f"\n{'='*60}")
        print(f"🔄 Test distances pour {symbol}...")
        print(f"{'='*60}")

        for variant in DISTANCE_VARIANTS[symbol]:
            name = variant['name']
            max_dist = variant['max_dist']

            stats = run_backtest_variant(all_data, symbol, max_dist)
            results[name] = {**stats, 'max_dist': max_dist, 'symbol': symbol}

            icon = "✅" if stats['pnl'] > 0 else "❌"
            print(f"   {icon} {name}: max={max_dist}t → {stats['trades']} trades, {stats['win_rate']:.1f}% WR, ${stats['pnl']:+,.2f}")

    # Classement
    for symbol in TEST_SYMBOLS:
        print(f"\n{'='*100}")
        print(f"🏆 CLASSEMENT {symbol} (par P&L)")
        print(f"{'='*100}")

        symbol_results = [(k, v) for k, v in results.items() if v['symbol'] == symbol]
        symbol_results.sort(key=lambda x: x[1]['pnl'], reverse=True)

        print(f"\n{'Rang':<6} {'Config':<20} {'Max Dist':<10} {'Trades':<8} {'WR %':<8} {'Avg Dist':<10} {'P&L':<15}")
        print("-"*85)

        for i, (name, stats) in enumerate(symbol_results, 1):
            icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{icon} {i:<4} {name:<20} {stats['max_dist']:<10} {stats['trades']:<8} {stats['win_rate']:<8.1f} {stats['avg_distance']:<10.1f} ${stats['pnl']:>12,.2f}")

    # Sauvegarder
    output = {"test_name": TEST_NAME, "test_date": datetime.now().isoformat(), "results": results}
    output_path = Path(__file__).parent / f"results{'_test' if is_test else ''}.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Résultats: {output_path}")
    if is_test:
        print(f"\n🚀 Mode complet: python {Path(__file__).name} --full")


if __name__ == "__main__":
    main()
