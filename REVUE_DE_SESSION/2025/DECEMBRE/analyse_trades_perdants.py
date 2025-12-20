# -*- coding: utf-8 -*-
"""
ANALYSE DES TRADES PERDANTS - IDENTIFICATION DES PATTERNS
==========================================================
Objectif: Trouver pourquoi certains trades passent les filtres et perdent
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Fix encoding Windows
sys.stdout.reconfigure(encoding='utf-8')

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")
SYMBOLS = ['ES', 'NQ']
CHART_MAPPING = {'ES': 3, 'NQ': 4}
TICK_SIZE = {'ES': 0.25, 'NQ': 0.25}
POINT_VALUE = {'ES': 50, 'NQ': 20}

# Sessions en heures Paris (UTC+1)
SESSIONS = {
    'LONDON': {'start_h': 8, 'end_h': 11, 'start_m': 0, 'end_m': 0},
    'US_MORNING': {'start_h': 15, 'end_h': 17, 'start_m': 50, 'end_m': 0},
    'POWER_HOUR': {'start_h': 20, 'end_h': 21, 'start_m': 0, 'end_m': 30},
}

def is_in_session(t_ms: int, session_name: str) -> bool:
    """Check if timestamp is within session (Paris time UTC+1)"""
    if t_ms == 0:
        return False
    session = SESSIONS.get(session_name)
    if not session:
        return False

    # Convert to Paris time (UTC+1)
    total_sec = t_ms // 1000
    total_min = total_sec // 60
    hour_utc = (total_min // 60) % 24
    minute = total_min % 60
    hour_paris = (hour_utc + 1) % 24  # UTC+1

    start_min = session['start_h'] * 60 + session['start_m']
    end_min = session['end_h'] * 60 + session['end_m']
    current_min = hour_paris * 60 + minute

    return start_min <= current_min < end_min

# Jours d'analyse
ALL_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127", "20251201", "20251202", "20251203",
    "20251204", "20251205", "20251208", "20251209", "20251210",
    "20251211", "20251212", "20251215", "20251216", "20251217"
]

# Niveaux et scores
ALL_PREMIUM_LEVELS = [
    'gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap', 'vpoc', '1d_max', '1d_min',
    'gex_3', 'gex_4', 'gex_5', 'hvl_0dte', 'gamma_wall_0dte',
    'call_resistance', 'put_support',
    'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
    'vwap_up1', 'vwap_dn1', 'vah', 'val', 'ibh', 'ibl',
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    'call_resistance_0dte', 'put_support_0dte',
    'blind_spot_3', 'blind_spot_4', 'blind_spot_5',
    'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
    'vwap_up2', 'vwap_dn2',
]

LEVEL_SCORES = {
    'gex_1': 3, 'gex_2': 3, 'hvl': 3, 'gamma_wall_level': 3, 'vwap': 3,
    'vpoc': 3, '1d_max': 3, '1d_min': 3,
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2, 'hvl_0dte': 2, 'gamma_wall_0dte': 2,
    'call_resistance': 2, 'put_support': 2,
    'blind_spot_0': 2, 'blind_spot_1': 2, 'blind_spot_2': 2,
    'vwap_up1': 2, 'vwap_dn1': 2, 'vah': 2, 'val': 2, 'ibh': 2, 'ibl': 2,
    'gex_6': 1, 'gex_7': 1, 'gex_8': 1, 'gex_9': 1, 'gex_10': 1,
    'call_resistance_0dte': 1, 'put_support_0dte': 1,
    'blind_spot_3': 1, 'blind_spot_4': 1, 'blind_spot_5': 1,
    'blind_spot_6': 1, 'blind_spot_7': 1, 'blind_spot_8': 1,
    'vwap_up2': 1, 'vwap_dn2': 1,
}

def get_level_score(level_name: str) -> int:
    return LEVEL_SCORES.get(level_name, 1)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def progress_bar(current, total, prefix='', suffix='', length=40):
    percent = 100 * current / total if total > 0 else 0
    filled = int(length * current // total) if total > 0 else 0
    bar = '#' * filled + '-' * (length - filled)
    sys.stdout.write(f'\r   {prefix} [{bar}] {percent:.0f}% {suffix}')
    sys.stdout.flush()
    if current >= total:
        print()

def get_trend(snap: dict) -> str:
    """Determine market trend from snapshot"""
    mid = snap.get('mid', 0)
    hvl = snap.get('hvl', 0)
    vwap = snap.get('vwap', 0)

    if not hvl or not vwap:
        return 'NEUTRAL'

    above_hvl = mid > hvl
    above_vwap = mid > vwap

    if above_hvl and above_vwap:
        return 'BULLISH'
    elif not above_hvl and not above_vwap:
        return 'BEARISH'
    return 'NEUTRAL'

def extract_levels_from_snapshot(snapshot: dict) -> List[Tuple[str, float, int]]:
    """Extract all premium levels from snapshot"""
    levels = []

    # Direct levels
    for key in ALL_PREMIUM_LEVELS:
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    # VVA
    vva = snapshot.get('vva', {})
    if vva:
        if vva.get('vpoc'):
            levels.append(('vpoc', float(vva['vpoc']), 3))
        if vva.get('vah'):
            levels.append(('vah', float(vva['vah']), 2))
        if vva.get('val'):
            levels.append(('val', float(vva['val']), 2))

    # Structure
    structure = snapshot.get('structure', {})
    if structure:
        if structure.get('ibh'):
            levels.append(('ibh', float(structure['ibh']), 2))
        if structure.get('ibl'):
            levels.append(('ibl', float(structure['ibl']), 2))

    return levels

def find_closest_level(mid: float, levels: List[Tuple[str, float, int]], tick_size: float) -> Optional[Tuple[str, float, float, int]]:
    """Find closest level to price"""
    if not levels:
        return None

    closest = None
    min_dist = float('inf')

    for name, price, score in levels:
        dist_ticks = abs(mid - price) / tick_size
        if dist_ticks < min_dist:
            min_dist = dist_ticks
            closest = (name, price, dist_ticks, score)

    return closest

def load_snapshots(days: List[str], symbol: str, session_name: str) -> List[Dict]:
    """Load snapshots for analysis with correct path structure"""
    snapshots = []
    chart_id = CHART_MAPPING.get(symbol, 3)
    MONTHS = {"11": "NOVEMBRE", "12": "DECEMBRE"}

    for idx, day in enumerate(days):
        progress_bar(idx + 1, len(days), f'Loading {symbol}', f'{day}')

        try:
            month_num = day[4:6]
            month_name = MONTHS.get(month_num, "DECEMBRE")
            contract_suffix = "H26" if day >= "20251211" else "Z25"

            # Correct path structure
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
                                    # Add metadata
                                    total_sec = t_ms // 1000
                                    total_min = total_sec // 60
                                    hour_utc = (total_min // 60) % 24
                                    minute = total_min % 60
                                    hour_paris = (hour_utc + 1) % 24

                                    snap['_hour'] = hour_paris
                                    snap['_minute'] = minute
                                    snap['_day'] = day
                                    snap['_session'] = session_name
                                    snapshots.append(snap)
                            except:
                                continue
        except Exception as e:
            continue

    return snapshots

def simulate_trade_outcome(snapshots: List[Dict], entry_idx: int, symbol: str, direction: str) -> Dict:
    """Simulate trade outcome using subsequent price action"""
    if entry_idx >= len(snapshots):
        return {'is_win': False, 'pnl_ticks': 0, 'pnl_usd': 0}

    entry_snap = snapshots[entry_idx]
    mid = entry_snap.get('mid', 0)
    tick_size = TICK_SIZE[symbol]
    point_value = POINT_VALUE[symbol]

    # TP/SL settings (20 ticks each)
    tp_ticks = 20
    sl_ticks = 20

    if direction == 'LONG':
        tp_price = mid + (tp_ticks * tick_size)
        sl_price = mid - (sl_ticks * tick_size)
    else:
        tp_price = mid - (tp_ticks * tick_size)
        sl_price = mid + (sl_ticks * tick_size)

    # Check next 100 bars for TP/SL hit
    for i in range(entry_idx + 1, min(entry_idx + 100, len(snapshots))):
        bar = snapshots[i]
        high = bar.get('high', bar.get('mid', mid))
        low = bar.get('low', bar.get('mid', mid))

        if direction == 'LONG':
            # Check SL first (worst case)
            if low <= sl_price:
                return {'is_win': False, 'pnl_ticks': -sl_ticks, 'pnl_usd': -sl_ticks * tick_size * point_value, 'bars_held': i - entry_idx}
            # Check TP
            if high >= tp_price:
                return {'is_win': True, 'pnl_ticks': tp_ticks, 'pnl_usd': tp_ticks * tick_size * point_value, 'bars_held': i - entry_idx}
        else:  # SHORT
            # Check SL first (worst case)
            if high >= sl_price:
                return {'is_win': False, 'pnl_ticks': -sl_ticks, 'pnl_usd': -sl_ticks * tick_size * point_value, 'bars_held': i - entry_idx}
            # Check TP
            if low <= tp_price:
                return {'is_win': True, 'pnl_ticks': tp_ticks, 'pnl_usd': tp_ticks * tick_size * point_value, 'bars_held': i - entry_idx}

    # No TP/SL hit within 100 bars - close at current price
    last_snap = snapshots[min(entry_idx + 99, len(snapshots) - 1)]
    exit_price = last_snap.get('mid', mid)
    pnl_pts = (exit_price - mid) if direction == 'LONG' else (mid - exit_price)
    pnl_ticks = pnl_pts / tick_size

    return {
        'is_win': pnl_ticks > 0,
        'pnl_ticks': pnl_ticks,
        'pnl_usd': pnl_ticks * tick_size * point_value,
        'bars_held': 100
    }

def analyze_trade(snapshots: List[Dict], entry_idx: int, symbol: str, direction: str, level_info: Tuple) -> Dict:
    """Analyze a single trade with all metrics"""
    snap = snapshots[entry_idx]
    mid = snap.get('mid', 0)
    tick_size = TICK_SIZE[symbol]

    # Get trend
    trend = get_trend(snap)

    # Level info
    level_name, level_price, distance, level_score = level_info if level_info else ('unknown', 0, 0, 0)

    # Extract scores (simulate ML layers)
    layer1 = snap.get('confluence_strength', 0.3)
    layer2 = abs(snap.get('smart_money_flow', 0)) + abs(snap.get('institutional_pressure', 0))
    layer3 = snap.get('volatility_regime_cont', 0.1)

    # Position in range
    position_in_range = snap.get('position_in_range', 50)

    # Other metrics
    mia_score = snap.get('mia_bullish_score', 0.5)
    delta = snap.get('delta', 0)
    cum_delta = snap.get('cum_delta_day', 0)

    # Simulate trade outcome using subsequent bars
    trade_result = simulate_trade_outcome(snapshots, entry_idx, symbol, direction)

    return {
        'symbol': symbol,
        'direction': direction,
        'trend': trend,
        'level_name': level_name,
        'level_score': level_score,
        'distance_ticks': distance,
        'layer1': layer1,
        'layer2': layer2,
        'layer3': layer3,
        'position_in_range': position_in_range,
        'mia_score': mia_score,
        'delta': delta,
        'cum_delta': cum_delta,
        'hour': snap.get('_hour', 0),
        'minute': snap.get('_minute', 0),
        'session': snap.get('_session', ''),
        'day': snap.get('_day', ''),
        'is_win': trade_result['is_win'],
        'pnl_ticks': trade_result['pnl_ticks'],
        'pnl_usd': trade_result['pnl_usd'],
        'entry_price': mid,
        'bars_held': trade_result.get('bars_held', 0),
        # Counter-trend detection
        'is_counter_trend': (direction == 'LONG' and trend == 'BEARISH') or (direction == 'SHORT' and trend == 'BULLISH'),
    }

def determine_direction(snap: dict) -> str:
    """Determine trade direction from snapshot signals"""
    mia_score = snap.get('mia_bullish_score', 0.5)
    delta = snap.get('delta', 0)

    # Simple direction logic
    if mia_score > 0.55 and delta > 0:
        return 'LONG'
    elif mia_score < 0.45 and delta < 0:
        return 'SHORT'
    elif mia_score > 0.5:
        return 'LONG'
    else:
        return 'SHORT'

# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def main():
    print("=" * 100)
    print("   ANALYSE DES TRADES PERDANTS - IDENTIFICATION DES PATTERNS")
    print("=" * 100)

    all_trades = []

    for session_name in SESSIONS.keys():
        print(f"\n{'='*80}")
        print(f"   SESSION: {session_name}")
        print(f"{'='*80}")

        for symbol in SYMBOLS:
            print(f"\n   [{symbol}] Chargement...")

            snaps = load_snapshots(ALL_DAYS, symbol, session_name)
            print(f"   -> {len(snaps)} snapshots charges")

            if len(snaps) < 100:
                continue

            tick_size = TICK_SIZE[symbol]

            # Sample trades (every 50 snapshots to simulate entry opportunities)
            trade_count = 0
            last_trade_idx = -50  # Cooldown between trades

            for i, snap in enumerate(snaps):
                if i - last_trade_idx < 50:  # Cooldown
                    continue
                if i >= len(snaps) - 100:  # Need future bars for simulation
                    continue

                # Get levels
                levels = extract_levels_from_snapshot(snap)
                mid = snap.get('mid', 0)

                closest = find_closest_level(mid, levels, tick_size)
                if not closest or closest[2] > 15:  # Max 15 ticks distance
                    continue

                # Determine direction
                direction = determine_direction(snap)

                # Analyze trade with future bars for outcome
                trade = analyze_trade(snaps, i, symbol, direction, closest)
                all_trades.append(trade)
                trade_count += 1
                last_trade_idx = i

            print(f"   -> {trade_count} trades analyses")

    # ==========================================================================
    # ANALYSE DES RESULTATS
    # ==========================================================================

    print("\n" + "=" * 100)
    print("   RESULTATS DE L'ANALYSE")
    print("=" * 100)

    if not all_trades:
        print("   [ERREUR] Aucun trade a analyser!")
        return

    # Separer gagnants/perdants
    winners = [t for t in all_trades if t['is_win']]
    losers = [t for t in all_trades if not t['is_win']]

    total = len(all_trades)
    win_count = len(winners)
    loss_count = len(losers)
    winrate = 100 * win_count / total if total > 0 else 0

    print(f"\n   TOTAL TRADES: {total}")
    print(f"   GAGNANTS: {win_count} ({winrate:.1f}%)")
    print(f"   PERDANTS: {loss_count} ({100-winrate:.1f}%)")

    # ==========================================================================
    # PATTERNS DES PERDANTS
    # ==========================================================================

    print(f"\n" + "-" * 80)
    print("   PATTERNS DES TRADES PERDANTS")
    print("-" * 80)

    if losers:
        # 1. Counter-trend
        ct_losers = [t for t in losers if t['is_counter_trend']]
        ct_pct = 100 * len(ct_losers) / len(losers) if losers else 0
        print(f"\n   [CONTRE-TENDANCE]")
        print(f"   -> {len(ct_losers)}/{len(losers)} perdants ({ct_pct:.1f}%) sont contre-tendance")

        ct_long_bearish = [t for t in losers if t['direction'] == 'LONG' and t['trend'] == 'BEARISH']
        ct_short_bullish = [t for t in losers if t['direction'] == 'SHORT' and t['trend'] == 'BULLISH']
        print(f"   -> LONG en BEARISH: {len(ct_long_bearish)}")
        print(f"   -> SHORT en BULLISH: {len(ct_short_bullish)}")

        # 2. Level score
        score1_losers = [t for t in losers if t['level_score'] == 1]
        score2_losers = [t for t in losers if t['level_score'] == 2]
        score3_losers = [t for t in losers if t['level_score'] == 3]
        print(f"\n   [SCORE DES NIVEAUX]")
        print(f"   -> Score 1 (faible): {len(score1_losers)} ({100*len(score1_losers)/len(losers):.1f}%)")
        print(f"   -> Score 2 (moyen):  {len(score2_losers)} ({100*len(score2_losers)/len(losers):.1f}%)")
        print(f"   -> Score 3 (fort):   {len(score3_losers)} ({100*len(score3_losers)/len(losers):.1f}%)")

        # 3. Distance
        far_losers = [t for t in losers if t['distance_ticks'] > 10]
        print(f"\n   [DISTANCE AU NIVEAU]")
        print(f"   -> Distance > 10 ticks: {len(far_losers)} ({100*len(far_losers)/len(losers):.1f}%)")
        avg_dist_losers = sum(t['distance_ticks'] for t in losers) / len(losers)
        avg_dist_winners = sum(t['distance_ticks'] for t in winners) / len(winners) if winners else 0
        print(f"   -> Distance moyenne perdants: {avg_dist_losers:.1f} ticks")
        print(f"   -> Distance moyenne gagnants: {avg_dist_winners:.1f} ticks")

        # 4. Layer2 (OrderFlow)
        low_l2_losers = [t for t in losers if t['layer2'] < 0.15]
        print(f"\n   [LAYER2 (OrderFlow)]")
        print(f"   -> Layer2 < 0.15: {len(low_l2_losers)} ({100*len(low_l2_losers)/len(losers):.1f}%)")
        avg_l2_losers = sum(t['layer2'] for t in losers) / len(losers)
        avg_l2_winners = sum(t['layer2'] for t in winners) / len(winners) if winners else 0
        print(f"   -> Layer2 moyen perdants: {avg_l2_losers:.3f}")
        print(f"   -> Layer2 moyen gagnants: {avg_l2_winners:.3f}")

        # 5. Position in range
        print(f"\n   [POSITION IN RANGE]")
        long_losers = [t for t in losers if t['direction'] == 'LONG']
        short_losers = [t for t in losers if t['direction'] == 'SHORT']

        if long_losers:
            high_long = [t for t in long_losers if t['position_in_range'] > 70]
            avg_pos_long = sum(t['position_in_range'] for t in long_losers) / len(long_losers)
            print(f"   -> LONG perdants avec position > 70%: {len(high_long)} ({100*len(high_long)/len(long_losers):.1f}%)")
            print(f"   -> Position moyenne LONG perdants: {avg_pos_long:.1f}%")

        if short_losers:
            low_short = [t for t in short_losers if t['position_in_range'] < 30]
            avg_pos_short = sum(t['position_in_range'] for t in short_losers) / len(short_losers)
            print(f"   -> SHORT perdants avec position < 30%: {len(low_short)} ({100*len(low_short)/len(short_losers):.1f}%)")
            print(f"   -> Position moyenne SHORT perdants: {avg_pos_short:.1f}%")

        # 6. Heures toxiques
        print(f"\n   [HEURES TOXIQUES]")
        hours_loss = defaultdict(lambda: {'wins': 0, 'losses': 0})
        for t in all_trades:
            h = t['hour']
            if t['is_win']:
                hours_loss[h]['wins'] += 1
            else:
                hours_loss[h]['losses'] += 1

        toxic_hours = []
        for h in sorted(hours_loss.keys()):
            total_h = hours_loss[h]['wins'] + hours_loss[h]['losses']
            if total_h >= 5:  # Min 5 trades
                loss_rate = 100 * hours_loss[h]['losses'] / total_h
                if loss_rate > 55:
                    toxic_hours.append((h, loss_rate, total_h))
                print(f"   -> {h:02d}h: {loss_rate:.1f}% loss rate ({total_h} trades)")

        # 7. MIA Score
        print(f"\n   [MIA SCORE]")
        avg_mia_losers = sum(t['mia_score'] for t in losers) / len(losers)
        avg_mia_winners = sum(t['mia_score'] for t in winners) / len(winners) if winners else 0
        print(f"   -> MIA moyen perdants: {avg_mia_losers:.3f}")
        print(f"   -> MIA moyen gagnants: {avg_mia_winners:.3f}")

        bad_mia_long = [t for t in long_losers if t['mia_score'] < 0.45]
        bad_mia_short = [t for t in short_losers if t['mia_score'] > 0.55]
        if long_losers:
            print(f"   -> LONG avec MIA < 0.45: {len(bad_mia_long)} ({100*len(bad_mia_long)/len(long_losers):.1f}%)")
        if short_losers:
            print(f"   -> SHORT avec MIA > 0.55: {len(bad_mia_short)} ({100*len(bad_mia_short)/len(short_losers):.1f}%)")

    # ==========================================================================
    # RECOMMANDATIONS
    # ==========================================================================

    print(f"\n" + "=" * 100)
    print("   RECOMMANDATIONS DE FILTRES")
    print("=" * 100)

    recommendations = []

    # Counter-trend
    if ct_pct > 30:
        recommendations.append(f"[CRITIQUE] Renforcer filtre contre-tendance ({ct_pct:.0f}% des pertes)")

    # Score 1
    if score1_losers and len(score1_losers) / len(losers) > 0.4:
        recommendations.append(f"[IMPORTANT] Exiger Score 2+ ({100*len(score1_losers)/len(losers):.0f}% des pertes sur Score 1)")

    # Distance
    if avg_dist_losers > avg_dist_winners + 2:
        recommendations.append(f"[IMPORTANT] Reduire max_distance (perdants: {avg_dist_losers:.1f}t vs gagnants: {avg_dist_winners:.1f}t)")

    # Layer2
    if avg_l2_losers < avg_l2_winners - 0.05:
        recommendations.append(f"[MODERE] Augmenter seuil Layer2 (perdants: {avg_l2_losers:.3f} vs gagnants: {avg_l2_winners:.3f})")

    # Toxic hours
    if toxic_hours:
        hours_str = ", ".join([f"{h[0]}h" for h in toxic_hours[:3]])
        recommendations.append(f"[MODERE] Bloquer heures toxiques: {hours_str}")

    # Position in range
    if long_losers and high_long and len(high_long) / len(long_losers) > 0.3:
        recommendations.append(f"[MODERE] Bloquer LONG si position > 70% ({100*len(high_long)/len(long_losers):.0f}% des LONG perdants)")

    for i, rec in enumerate(recommendations, 1):
        print(f"\n   {i}. {rec}")

    # ==========================================================================
    # CODE DES FILTRES PROPOSES
    # ==========================================================================

    print(f"\n" + "=" * 100)
    print("   CODE DES FILTRES PROPOSES")
    print("=" * 100)

    print("""
   # FILTRES ADDITIONNELS PROPOSES (a tester en backtest)

   def additional_filters(snap, direction, level_score, distance_ticks):
       rejections = []

       # 1. Contre-tendance renforcee
       trend = get_trend(snap)
       if level_score < 2:  # Seulement Score 1
           if direction == 'LONG' and trend == 'BEARISH':
               rejections.append("LONG_CONTRE_TENDANCE_SCORE1")
           if direction == 'SHORT' and trend == 'BULLISH':
               rejections.append("SHORT_CONTRE_TENDANCE_SCORE1")

       # 2. Distance maximale selon score
       max_dist = {1: 6, 2: 10, 3: 15}
       if distance_ticks > max_dist.get(level_score, 15):
           rejections.append(f"DISTANCE_TROP_GRANDE_{distance_ticks:.0f}t")

       # 3. Position in range
       position = snap.get('position_in_range', 50)
       if direction == 'LONG' and position > 75:
           rejections.append("LONG_HAUT_DU_RANGE")
       if direction == 'SHORT' and position < 25:
           rejections.append("SHORT_BAS_DU_RANGE")

       # 4. MIA Score alignment
       mia = snap.get('mia_bullish_score', 0.5)
       if direction == 'LONG' and mia < 0.40:
           rejections.append("LONG_MIA_BEARISH")
       if direction == 'SHORT' and mia > 0.60:
           rejections.append("SHORT_MIA_BULLISH")

       return rejections
    """)

    print("\n" + "=" * 100)
    print("   ANALYSE TERMINEE")
    print("=" * 100)

if __name__ == "__main__":
    main()
