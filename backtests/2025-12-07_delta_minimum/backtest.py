"""
📊 BACKTEST #3: Delta Minimum
==============================

Teste différents seuils de delta minimum pour filtrer les signaux.
Objectif: Un delta fort = signal plus fiable ?

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
    MAX_DISTANCE_TO_LEVEL, TP_SL_CONFIG, TICK_VALUES, TICK_SIZES,
    COOLDOWN_MS, MAX_TRADE_DURATION_MS, MAX_SNAPSHOTS_LOOKAHEAD,
    MLScores, get_session, get_distance_to_level, load_snapshots
)

# ============================================================================
# 🎯 CONFIGURATION
# ============================================================================

TEST_NAME = "Delta Minimum"
TEST_DESCRIPTION = """
Teste différents seuils de delta absolu minimum.
Hypothèse: Un delta plus élevé indique une pression directionnelle plus forte.
"""

DATE_RANGE = ["20251202", "20251203", "20251204", "20251205"]
DATA_MONTH = "DECEMBRE"
DATA_YEAR = 2025
TEST_SYMBOLS = ['ES', 'NQ']
TEST_SAMPLE_SIZE = 5000
TEST_DATES = 1

# ============================================================================
# 🔧 DELTAS À TESTER
# ============================================================================

DELTA_VARIANTS = [
    {'name': 'DELTA_0_ACTUEL', 'min_delta': 0},      # Pas de filtre (actuel)
    {'name': 'DELTA_25', 'min_delta': 25},
    {'name': 'DELTA_50', 'min_delta': 50},
    {'name': 'DELTA_75', 'min_delta': 75},
    {'name': 'DELTA_100', 'min_delta': 100},
    {'name': 'DELTA_150', 'min_delta': 150},
    {'name': 'DELTA_200', 'min_delta': 200},
    {'name': 'DELTA_300', 'min_delta': 300},
    {'name': 'DELTA_500', 'min_delta': 500},
]

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


def validate_signal(snap: Dict, symbol: str, min_delta: int) -> Tuple[Optional[Signal], str]:
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)

    if not ts or not mid:
        return None, "no_price"

    in_session, session = get_session(ts)
    if not in_session:
        return None, "out_of_session"

    # Filtre delta minimum
    if abs(delta) < min_delta:
        return None, f"delta_too_low_{abs(delta):.0f}"

    if delta == 0:
        return None, "delta_zero"
    direction = "LONG" if delta > 0 else "SHORT"

    ml_scores = calculate_ml_scores(snap, symbol)
    ml_ok, _ = ml_scores.meets_thresholds(symbol)
    if not ml_ok:
        return None, "ml_reject"

    distance, _ = get_distance_to_level(snap, mid, symbol)
    max_dist = MAX_DISTANCE_TO_LEVEL.get(symbol, 20)
    if distance > max_dist:
        return None, "distance"

    return Signal(ts, symbol, direction, mid, session, delta), "OK"


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


def run_backtest_variant(all_data: Dict, symbol: str, min_delta: int) -> Dict:
    stats = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0, "deltas": []}
    last_trade_time = 0

    for date_str, snaps in all_data.get(symbol, []):
        for i, snap in enumerate(snaps):
            signal, _ = validate_signal(snap, symbol, min_delta)
            if signal is None:
                continue

            if signal.timestamp - last_trade_time < COOLDOWN_MS:
                continue

            last_trade_time = signal.timestamp
            subsequent = snaps[i+1:i+1+MAX_SNAPSHOTS_LOOKAHEAD]
            trade = simulate_trade(signal, subsequent)

            stats["trades"] += 1
            stats["pnl"] += trade.pnl_usd
            stats["deltas"].append(abs(signal.delta))

            if trade.result == "WIN":
                stats["wins"] += 1
            elif trade.result == "LOSS":
                stats["losses"] += 1

    stats["win_rate"] = stats["wins"] / max(stats["trades"], 1) * 100
    stats["avg_delta"] = sum(stats["deltas"]) / max(len(stats["deltas"]), 1)
    del stats["deltas"]
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
        print(f"🔄 Test delta minimum pour {symbol}...")
        print(f"{'='*60}")

        for variant in DELTA_VARIANTS:
            name = f"{symbol}_{variant['name']}"
            min_delta = variant['min_delta']

            stats = run_backtest_variant(all_data, symbol, min_delta)
            results[name] = {**stats, 'min_delta': min_delta, 'symbol': symbol}

            icon = "✅" if stats['pnl'] > 0 else "❌"
            print(f"   {icon} delta>={min_delta}: {stats['trades']} trades, {stats['win_rate']:.1f}% WR, avg_delta={stats['avg_delta']:.0f}, ${stats['pnl']:+,.2f}")

    # Classement
    for symbol in TEST_SYMBOLS:
        print(f"\n{'='*100}")
        print(f"🏆 CLASSEMENT {symbol} (par P&L)")
        print(f"{'='*100}")

        symbol_results = [(k, v) for k, v in results.items() if v['symbol'] == symbol]
        symbol_results.sort(key=lambda x: x[1]['pnl'], reverse=True)

        print(f"\n{'Rang':<6} {'Min Delta':<12} {'Trades':<8} {'WR %':<8} {'Avg Delta':<12} {'P&L':<15}")
        print("-"*70)

        for i, (name, stats) in enumerate(symbol_results, 1):
            icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{icon} {i:<4} {stats['min_delta']:<12} {stats['trades']:<8} {stats['win_rate']:<8.1f} {stats['avg_delta']:<12.0f} ${stats['pnl']:>12,.2f}")

        # Analyse
        best = symbol_results[0][1] if symbol_results else None
        if best and best['min_delta'] > 0:
            print(f"\n   💡 Un delta minimum de {best['min_delta']} semble optimal pour {symbol}")
        elif best:
            print(f"\n   💡 Pas de filtre delta nécessaire pour {symbol}")

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
