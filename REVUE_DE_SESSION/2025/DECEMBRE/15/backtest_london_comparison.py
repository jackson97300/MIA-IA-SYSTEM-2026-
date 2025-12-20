#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
            COMPARAISON LONDON_ES: AVEC vs SANS FILTRES
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF: Comparer les résultats LONDON_ES:
   - AVEC DUAL-MODE + OBSTACLE (comme ce matin = 0 trades)
   - SANS ces filtres (comme V9 original)

Date: 15 Décembre 2025
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import sys

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

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
}

# Config LONDON_ES V9
LONDON_ES_CONFIG = {
    'tp_ticks': 12, 'sl_ticks': 12, 'cooldown_min': 15,
    'min_confidence': 0.30, 'min_layer2': 0.15, 'mia_threshold': 0.20,
    'max_distance': 12, 'min_confluence': 1, 'min_level_score': 2,
}

# DUAL-MODE Config
DUAL_MODE_CONFIG = {
    'bias_threshold': 0.30,
    'bottom_zone_pct': 33,
    'top_zone_pct': 67,
    'vol_regime_trend': 1.5,
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

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_month_folder(day: str) -> str:
    return "NOVEMBRE" if day[4:6] == "11" else "DECEMBRE"

def find_data_file(day: str) -> Optional[Path]:
    month_folder = get_month_folder(day)
    for contract in ["ESZ25", "ESH25"]:
        path = DATA_BASE_PATH / month_folder / day / "CHART_3" / "ML_READY" / f"ml_{contract}_FUT_CME_3.jsonl"
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

# ═══════════════════════════════════════════════════════════════════════════════
#                           FILTRES
# ═══════════════════════════════════════════════════════════════════════════════

def check_dual_mode_block(snapshot: Dict, direction: str) -> Tuple[bool, str]:
    """Vérifie si DUAL-MODE bloque ce trade."""
    cfg = DUAL_MODE_CONFIG

    vol_regime = snapshot.get('vol_regime', 1.0) or 1.0
    mia_score = snapshot.get('mia_bullish_score', 0) or 0

    # Mode TREND = pas de blocage
    if vol_regime >= cfg['vol_regime_trend'] or abs(mia_score) >= cfg['bias_threshold']:
        return False, ""

    # Mode RANGE - calculer position
    ibh = snapshot.get('ibh') or snapshot.get('1d_max') or 0
    ibl = snapshot.get('ibl') or snapshot.get('1d_min') or 0
    mid = snapshot.get('mid', 0)

    if ibh > ibl and mid > 0:
        position_pct = ((mid - ibl) / (ibh - ibl)) * 100
        position_pct = max(0, min(100, position_pct))
    else:
        position_pct = 50

    # Vérifier zones
    if direction == "LONG" and position_pct > cfg['top_zone_pct']:
        return True, f"RANGE TOP ({position_pct:.0f}%)"
    if direction == "SHORT" and position_pct < cfg['bottom_zone_pct']:
        return True, f"RANGE BOTTOM ({position_pct:.0f}%)"
    if cfg['bottom_zone_pct'] <= position_pct <= cfg['top_zone_pct']:
        return True, f"RANGE MIDDLE ({position_pct:.0f}%)"

    return False, ""

def check_obstacle(snapshot: Dict, direction: str, entry_price: float, tp_ticks: int) -> Tuple[bool, str]:
    """Vérifie si obstacle entre entry et TP."""
    tick_size = 0.25

    if direction == "LONG":
        tp_price = entry_price + tp_ticks * tick_size
        for level_name in ALL_LEVELS:
            level_price = snapshot.get(level_name)
            if not level_price or level_price <= 0:
                continue
            if entry_price < level_price < tp_price:
                distance_to_obstacle = (level_price - entry_price) / tick_size
                if distance_to_obstacle < tp_ticks * 0.8:
                    return True, f"{level_name} @ {level_price:.2f}"

    elif direction == "SHORT":
        tp_price = entry_price - tp_ticks * tick_size
        for level_name in ALL_LEVELS:
            level_price = snapshot.get(level_name)
            if not level_price or level_price <= 0:
                continue
            if tp_price < level_price < entry_price:
                distance_to_obstacle = (entry_price - level_price) / tick_size
                if distance_to_obstacle < tp_ticks * 0.8:
                    return True, f"{level_name} @ {level_price:.2f}"

    return False, ""

def analyze_menthorq(snapshot: Dict, zone_ticks: int = 15) -> Dict:
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return {'nearest_distance': float('inf'), 'confluence_count': 0, 'max_score_in_zone': 0}

    levels_in_zone = []
    nearest_distance = float('inf')
    max_score = 0

    for level_name in ALL_LEVELS:
        price = snapshot.get(level_name)
        if not price or price <= 0:
            continue

        distance = abs(mid - price) / 0.25
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

# ═══════════════════════════════════════════════════════════════════════════════
#                           GÉNÉRATION SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal(snapshot: Dict, config: Dict, use_dual_mode: bool, use_obstacle: bool) -> Tuple[bool, str, float, str]:
    """
    Génère un signal.
    Retourne: (valid, direction, confidence, reject_reason)
    """
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "NO_PRICE"

    # Analyser MenthorQ
    mq = analyze_menthorq(snapshot)

    # Filtre V9: Distance
    if mq['nearest_distance'] > config['max_distance']:
        return False, "", 0, "V9_DISTANCE"

    # Filtre V9: Confluence
    if mq['confluence_count'] < config['min_confluence']:
        return False, "", 0, "V9_CONFLUENCE"

    # Filtre V9: Level Score
    if mq['max_score_in_zone'] < config['min_level_score']:
        return False, "", 0, "V9_LEVEL_SCORE"

    # Calcul confidence
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

    # Direction
    if mia_score > config['mia_threshold']:
        direction = "LONG"
    elif mia_score < -config['mia_threshold']:
        direction = "SHORT"
    else:
        return False, "", confidence, "NEUTRAL"

    # Filtre DUAL-MODE (optionnel)
    if use_dual_mode:
        blocked, reason = check_dual_mode_block(snapshot, direction)
        if blocked:
            return False, "", confidence, f"DUAL_MODE:{reason}"

    # Filtre OBSTACLE (optionnel)
    if use_obstacle:
        has_obstacle, info = check_obstacle(snapshot, direction, mid, config['tp_ticks'])
        if has_obstacle:
            return False, "", confidence, f"OBSTACLE:{info}"

    return True, direction, confidence, ""

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, future_snaps: List[Dict],
                   tp_ticks: int, sl_ticks: int) -> Tuple[float, str]:
    tick_size = 0.25
    tick_value = 12.50

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
#                           BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(all_data: Dict, config: Dict, use_dual_mode: bool, use_obstacle: bool) -> Dict:
    """Exécute le backtest avec ou sans les filtres."""

    trades = []
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

            valid, direction, confidence, reject_reason = generate_signal(
                snap, config, use_dual_mode, use_obstacle
            )

            if not valid:
                if reject_reason:
                    rejects[reject_reason.split(':')[0]] += 1
                continue

            future = snapshots[i+1:i+301]
            if len(future) < 10:
                continue

            pnl, result = simulate_trade(snap, direction, future,
                                         config['tp_ticks'], config['sl_ticks'])

            trades.append({'pnl': pnl, 'result': result, 'direction': direction})
            last_trade_time = t_ms
            session_trades += 1

    # Stats
    if not trades:
        return {'trades': 0, 'pnl': 0, 'wr': 0, 'wins': 0, 'losses': 0, 'rejects': dict(rejects)}

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
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("     🎯 COMPARAISON LONDON_ES: AVEC vs SANS FILTRES")
    print("=" * 80)

    # Charger données
    print("\n📂 Chargement des données LONDON_ES...")
    all_data = {}
    days_loaded = 0

    for day in DAYS_TO_TEST:
        file_path = find_data_file(day)
        if file_path:
            snapshots = load_snapshots(file_path)
            if snapshots:
                all_data[day] = snapshots
                days_loaded += 1
                print(f"   {day}: {len(snapshots)} snapshots")

    print(f"\n   📊 {days_loaded} jours chargés")

    if days_loaded == 0:
        print("❌ Aucune donnée!")
        return

    # ═══════════════════════════════════════════════════════════════
    #                    BACKTEST 1: AVEC FILTRES (comme ce matin)
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("🔬 BACKTEST 1: AVEC DUAL-MODE + OBSTACLE (comme ce matin)")
    print("=" * 80)

    result_with_filters = run_backtest(all_data, LONDON_ES_CONFIG,
                                        use_dual_mode=True, use_obstacle=True)

    print(f"""
   Trades:  {result_with_filters['trades']}
   Wins:    {result_with_filters['wins']}
   Losses:  {result_with_filters['losses']}
   WR:      {result_with_filters['wr']:.1f}%
   P&L:     ${result_with_filters['pnl']:+,.0f}

   Rejets:
""")
    for reject_type, count in sorted(result_with_filters['rejects'].items(), key=lambda x: -x[1]):
        print(f"      {reject_type}: {count}")

    # ═══════════════════════════════════════════════════════════════
    #                    BACKTEST 2: SANS FILTRES (config actuelle)
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("🔬 BACKTEST 2: SANS DUAL-MODE, SANS OBSTACLE (config actuelle)")
    print("=" * 80)

    result_without_filters = run_backtest(all_data, LONDON_ES_CONFIG,
                                           use_dual_mode=False, use_obstacle=False)

    print(f"""
   Trades:  {result_without_filters['trades']}
   Wins:    {result_without_filters['wins']}
   Losses:  {result_without_filters['losses']}
   WR:      {result_without_filters['wr']:.1f}%
   P&L:     ${result_without_filters['pnl']:+,.0f}

   Rejets:
""")
    for reject_type, count in sorted(result_without_filters['rejects'].items(), key=lambda x: -x[1]):
        print(f"      {reject_type}: {count}")

    # ═══════════════════════════════════════════════════════════════
    #                    COMPARAISON
    # ═══════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("                    📊 COMPARAISON LONDON_ES")
    print("=" * 80)

    diff_trades = result_without_filters['trades'] - result_with_filters['trades']
    diff_pnl = result_without_filters['pnl'] - result_with_filters['pnl']

    print(f"""
┌────────────────────────────────────────────────────────────────────────────┐
│                          AVEC FILTRES              SANS FILTRES            │
│                     (DUAL-MODE+OBSTACLE)         (Config actuelle)         │
├────────────────────────────────────────────────────────────────────────────┤
│  Trades:           {result_with_filters['trades']:>8}                    {result_without_filters['trades']:>8}              │
│  Wins:             {result_with_filters['wins']:>8}                    {result_without_filters['wins']:>8}              │
│  Losses:           {result_with_filters['losses']:>8}                    {result_without_filters['losses']:>8}              │
│  Win Rate:         {result_with_filters['wr']:>7.1f}%                   {result_without_filters['wr']:>7.1f}%             │
│  P&L:              ${result_with_filters['pnl']:>+8,.0f}                  ${result_without_filters['pnl']:>+8,.0f}            │
├────────────────────────────────────────────────────────────────────────────┤
│  DIFFÉRENCE:       +{diff_trades} trades                  ${diff_pnl:+,.0f}             │
└────────────────────────────────────────────────────────────────────────────┘
""")

    # Verdict
    if diff_pnl > 0:
        print("✅ VERDICT: DÉSACTIVER les filtres = MEILLEUR RÉSULTAT!")
        print(f"   Gain de ${diff_pnl:+,.0f} et +{diff_trades} trades")
    else:
        print("⚠️ VERDICT: Les filtres étaient bénéfiques")
        print(f"   Perte de ${diff_pnl:,.0f} sans les filtres")


if __name__ == "__main__":
    main()
