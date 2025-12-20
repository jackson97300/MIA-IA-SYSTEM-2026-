#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
            BACKTEST LONDON ES + NQ - SANS FILTRES
═══════════════════════════════════════════════════════════════════════════════
Date: 15 Décembre 2025
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import sys

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

DAYS_TO_TEST = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127",
    "20251201", "20251202", "20251203", "20251204", "20251205",
    "20251208", "20251209", "20251210", "20251211", "20251212",
]

SYMBOLS = {
    "ES": {"chart_id": 3, "tick_size": 0.25, "tick_value": 12.50, "contracts": ["ESZ25", "ESH25"]},
    "NQ": {"chart_id": 9, "tick_size": 0.25, "tick_value": 5.00, "contracts": ["NQZ25", "NQH25"]},
}

# Configs V9 pour LONDON
LONDON_CONFIGS = {
    'ES': {
        'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
        'min_confidence': 0.30, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 12, 'min_confluence': 1, 'min_level_score': 2,
    },
    'NQ': {
        'tp_ticks': 25, 'sl_ticks': 20, 'cooldown_min': 20,
        'min_confidence': 0.65, 'min_layer2': 0.15, 'mia_threshold': 0.20,
        'max_distance': 5, 'min_confluence': 3, 'min_level_score': 0,
    },
}

# Niveaux MenthorQ
STRONG_LEVELS = ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap']
MEDIUM_LEVELS = ['gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
                 'call_resistance', 'put_support', 'blind_spot_1', 'blind_spot_2']
WEAK_LEVELS = ['call_resistance_0dte', 'put_support_0dte', 'blind_spot_3',
               'vwap_up1', 'vwap_dn1', 'vwap_up2', 'vwap_dn2']
ALL_LEVELS = STRONG_LEVELS + MEDIUM_LEVELS + WEAK_LEVELS

def get_level_score(level_name: str) -> int:
    if level_name in STRONG_LEVELS: return 3
    elif level_name in MEDIUM_LEVELS: return 2
    elif level_name in WEAK_LEVELS: return 1
    return 0

def get_month_folder(day: str) -> str:
    return "NOVEMBRE" if day[4:6] == "11" else "DECEMBRE"

def find_data_file(day: str, symbol: str) -> Optional[Path]:
    cfg = SYMBOLS[symbol]
    month_folder = get_month_folder(day)
    for contract in cfg["contracts"]:
        path = DATA_BASE_PATH / month_folder / day / f"CHART_{cfg['chart_id']}" / "ML_READY" / f"ml_{contract}_FUT_CME_{cfg['chart_id']}.jsonl"
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

def is_london_session(hour: int, minute: int) -> bool:
    time_val = hour * 60 + minute
    return 8 * 60 <= time_val < 11 * 60

def analyze_menthorq(snapshot: Dict, symbol: str, zone_ticks: int = 15) -> Dict:
    mid = snapshot.get('mid', 0)
    tick_size = SYMBOLS[symbol]['tick_size']
    if mid <= 0:
        return {'nearest_distance': float('inf'), 'confluence_count': 0, 'max_score_in_zone': 0}

    levels_in_zone = []
    nearest_distance = float('inf')
    max_score = 0

    for level_name in ALL_LEVELS:
        price = snapshot.get(level_name)
        if not price or price <= 0:
            continue

        distance = abs(mid - price) / tick_size
        score = get_level_score(level_name)

        if distance <= zone_ticks:
            levels_in_zone.append({'name': level_name, 'distance': distance, 'score': score})
            max_score = max(max_score, score)

        if distance < nearest_distance:
            nearest_distance = distance

    return {
        'nearest_distance': nearest_distance,
        'confluence_count': len(levels_in_zone),
        'max_score_in_zone': max_score,
    }

def generate_signal(snapshot: Dict, symbol: str, config: Dict) -> Tuple[bool, str, float, str]:
    """Signal SANS DUAL-MODE et SANS OBSTACLE."""
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "NO_PRICE"

    mq = analyze_menthorq(snapshot, symbol)

    if mq['nearest_distance'] > config['max_distance']:
        return False, "", 0, "V9_DISTANCE"

    if mq['confluence_count'] < config['min_confluence']:
        return False, "", 0, "V9_CONFLUENCE"

    if mq['max_score_in_zone'] < config['min_level_score']:
        return False, "", 0, "V9_LEVEL_SCORE"

    menthorq_score = max(0, 1 - mq['nearest_distance'] / 25)
    layer1 = menthorq_score * 0.50

    delta = snapshot.get('delta', 0) or 0
    cum_delta = snapshot.get('cum_delta_session', 0) or 0
    of_score = min(1.0, (abs(delta) / 400 + abs(cum_delta) / 800) / 2) * 0.5 + 0.3
    layer2 = of_score * 0.30

    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    ctx_score = min(1.0, abs(mia_score) * 2.5)
    layer3 = ctx_score * 0.20

    confidence = layer1 + layer2 + layer3

    if confidence < config['min_confidence']:
        return False, "", confidence, "V9_CONFIDENCE"

    if mia_score > config['mia_threshold']:
        direction = "LONG"
    elif mia_score < -config['mia_threshold']:
        direction = "SHORT"
    else:
        return False, "", confidence, "NEUTRAL"

    return True, direction, confidence, ""

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], tp_ticks: int, sl_ticks: int) -> Tuple[float, str]:
    cfg = SYMBOLS[symbol]
    tick_size = cfg['tick_size']
    tick_value = cfg['tick_value']

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

def run_backtest(all_data: Dict, symbol: str, config: Dict) -> Dict:
    trades = []
    trades_by_day = defaultdict(list)
    rejects = defaultdict(int)
    cooldown_ms = config['cooldown_min'] * 60 * 1000

    for day, snapshots in all_data.items():
        if not snapshots:
            continue

        last_trade_time = 0
        session_trades = 0

        for i, snap in enumerate(snapshots):
            if session_trades >= 10:
                break

            t_ms = snap.get('t_ms', 0)
            hour, minute = get_paris_time(t_ms)

            if not is_london_session(hour, minute):
                continue

            if t_ms - last_trade_time < cooldown_ms:
                continue

            valid, direction, confidence, reject_reason = generate_signal(snap, symbol, config)

            if not valid:
                if reject_reason:
                    rejects[reject_reason] += 1
                continue

            future = snapshots[i+1:i+301]
            if len(future) < 10:
                continue

            pnl, result = simulate_trade(snap, direction, symbol, future,
                                         config['tp_ticks'], config['sl_ticks'])

            trade = {'pnl': pnl, 'result': result, 'direction': direction, 'day': day}
            trades.append(trade)
            trades_by_day[day].append(trade)
            last_trade_time = t_ms
            session_trades += 1

    if not trades:
        return {'trades': 0, 'pnl': 0, 'wr': 0, 'wins': 0, 'losses': 0,
                'rejects': dict(rejects), 'trades_by_day': {}}

    total_pnl = sum(t['pnl'] for t in trades)
    winners = [t for t in trades if t['pnl'] > 0]
    losers = [t for t in trades if t['pnl'] < 0]
    wr = len(winners) / len(trades) * 100 if trades else 0

    return {
        'trades': len(trades),
        'pnl': total_pnl,
        'wr': wr,
        'wins': len(winners),
        'losses': len(losers),
        'rejects': dict(rejects),
        'trades_by_day': {d: len(t) for d, t in trades_by_day.items()},
        'avg_trades_per_day': len(trades) / len([d for d in all_data if all_data[d]]),
    }

def main():
    print("=" * 90)
    print("     🎯 BACKTEST LONDON ES + NQ - SANS FILTRES (Config actuelle)")
    print("=" * 90)

    # Charger données par symbole
    all_data = {'ES': {}, 'NQ': {}}

    print("\n📂 Chargement des données...")
    for symbol in ['ES', 'NQ']:
        days_loaded = 0
        for day in DAYS_TO_TEST:
            file_path = find_data_file(day, symbol)
            if file_path:
                snapshots = load_snapshots(file_path)
                if snapshots:
                    all_data[symbol][day] = snapshots
                    days_loaded += 1
        print(f"   {symbol}: {days_loaded} jours chargés")

    # Backtest ES
    print("\n" + "=" * 90)
    print("🔬 LONDON_ES - SANS DUAL-MODE, SANS OBSTACLE")
    print("=" * 90)

    result_es = run_backtest(all_data['ES'], 'ES', LONDON_CONFIGS['ES'])

    print(f"""
   Config: TP={LONDON_CONFIGS['ES']['tp_ticks']}t, SL={LONDON_CONFIGS['ES']['sl_ticks']}t,
           Cooldown={LONDON_CONFIGS['ES']['cooldown_min']}min, Confidence={LONDON_CONFIGS['ES']['min_confidence']:.0%}
           MaxDistance={LONDON_CONFIGS['ES']['max_distance']}t, MinScore={LONDON_CONFIGS['ES']['min_level_score']}

   RÉSULTATS:
   ─────────────────────────────────────
   Trades:           {result_es['trades']}
   Trades/jour:      {result_es.get('avg_trades_per_day', 0):.1f}
   Wins:             {result_es['wins']}
   Losses:           {result_es['losses']}
   Win Rate:         {result_es['wr']:.1f}%
   P&L:              ${result_es['pnl']:+,.0f}
   P&L/trade:        ${result_es['pnl']/result_es['trades'] if result_es['trades'] else 0:+,.0f}
""")

    # Distribution par jour
    if result_es['trades_by_day']:
        trades_list = list(result_es['trades_by_day'].values())
        print(f"   Distribution trades/jour: min={min(trades_list)}, max={max(trades_list)}, avg={sum(trades_list)/len(trades_list):.1f}")

    # Backtest NQ
    print("\n" + "=" * 90)
    print("🔬 LONDON_NQ - SANS DUAL-MODE, SANS OBSTACLE")
    print("=" * 90)

    result_nq = run_backtest(all_data['NQ'], 'NQ', LONDON_CONFIGS['NQ'])

    print(f"""
   Config: TP={LONDON_CONFIGS['NQ']['tp_ticks']}t, SL={LONDON_CONFIGS['NQ']['sl_ticks']}t,
           Cooldown={LONDON_CONFIGS['NQ']['cooldown_min']}min, Confidence={LONDON_CONFIGS['NQ']['min_confidence']:.0%}
           MaxDistance={LONDON_CONFIGS['NQ']['max_distance']}t, MinConfluence={LONDON_CONFIGS['NQ']['min_confluence']}

   RÉSULTATS:
   ─────────────────────────────────────
   Trades:           {result_nq['trades']}
   Trades/jour:      {result_nq.get('avg_trades_per_day', 0):.1f}
   Wins:             {result_nq['wins']}
   Losses:           {result_nq['losses']}
   Win Rate:         {result_nq['wr']:.1f}%
   P&L:              ${result_nq['pnl']:+,.0f}
   P&L/trade:        ${result_nq['pnl']/result_nq['trades'] if result_nq['trades'] else 0:+,.0f}
""")

    if result_nq['trades_by_day']:
        trades_list = list(result_nq['trades_by_day'].values())
        print(f"   Distribution trades/jour: min={min(trades_list)}, max={max(trades_list)}, avg={sum(trades_list)/len(trades_list):.1f}")

    # Résumé total
    print("\n" + "=" * 90)
    print("                    📊 RÉSUMÉ SESSION LONDON (ES + NQ)")
    print("=" * 90)

    total_trades = result_es['trades'] + result_nq['trades']
    total_wins = result_es['wins'] + result_nq['wins']
    total_losses = result_es['losses'] + result_nq['losses']
    total_pnl = result_es['pnl'] + result_nq['pnl']
    total_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    print(f"""
┌────────────────────────────────────────────────────────────────────────────────┐
│                          LONDON_ES            LONDON_NQ           TOTAL        │
├────────────────────────────────────────────────────────────────────────────────┤
│  Trades:              {result_es['trades']:>6}                  {result_nq['trades']:>6}              {total_trades:>6}       │
│  Trades/jour:         {result_es.get('avg_trades_per_day', 0):>6.1f}                  {result_nq.get('avg_trades_per_day', 0):>6.1f}              {total_trades/27:>6.1f}       │
│  Win Rate:            {result_es['wr']:>5.1f}%                  {result_nq['wr']:>5.1f}%             {total_wr:>5.1f}%       │
│  P&L:                ${result_es['pnl']:>+7,.0f}                ${result_nq['pnl']:>+7,.0f}            ${total_pnl:>+7,.0f}       │
└────────────────────────────────────────────────────────────────────────────────┘
""")

    # Analyse critique
    print("\n" + "=" * 90)
    print("                    ⚠️ ANALYSE CRITIQUE")
    print("=" * 90)

    es_trades_per_day = result_es.get('avg_trades_per_day', 0)
    nq_trades_per_day = result_nq.get('avg_trades_per_day', 0)

    print(f"""
   🔍 LONDON_ES: {es_trades_per_day:.1f} trades/jour
      → Session de 3h avec cooldown 15min = max 12 trades théoriques
      → {es_trades_per_day:.1f} trades = {es_trades_per_day/12*100:.0f}% de capacité utilisée
      → P&L/trade = ${result_es['pnl']/result_es['trades'] if result_es['trades'] else 0:+,.0f}

   🔍 LONDON_NQ: {nq_trades_per_day:.1f} trades/jour
      → Session de 3h avec cooldown 20min = max 9 trades théoriques
      → {nq_trades_per_day:.1f} trades = {nq_trades_per_day/9*100:.0f}% de capacité utilisée
      → P&L/trade = ${result_nq['pnl']/result_nq['trades'] if result_nq['trades'] else 0:+,.0f}
""")

    # Recommandations
    print("\n" + "=" * 90)
    print("                    💡 RECOMMANDATIONS")
    print("=" * 90)

    if result_nq['pnl'] < 0 or result_nq['wr'] < 45:
        print(f"""
   🔴 LONDON_NQ: DÉSACTIVER ou augmenter les seuils
      - WR: {result_nq['wr']:.1f}% < 45% = non rentable
      - P&L: ${result_nq['pnl']:+,.0f} négatif
      - Config NQ trop permissive (confidence={LONDON_CONFIGS['NQ']['min_confidence']:.0%})
""")

    if result_es['pnl'] > 0 and result_es['wr'] > 48:
        print(f"""
   🟢 LONDON_ES: GARDER
      - WR: {result_es['wr']:.1f}% > 48% = rentable
      - P&L: ${result_es['pnl']:+,.0f} positif
      - {es_trades_per_day:.1f} trades/jour = volume acceptable
""")


if __name__ == "__main__":
    main()
