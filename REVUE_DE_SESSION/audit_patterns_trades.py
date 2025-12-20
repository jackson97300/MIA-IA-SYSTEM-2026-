"""
AUDIT DES PATTERNS CACHES DANS LES 216 TRADES
==============================================

Objectif: Trouver des patterns qui predisent les WINS
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Chemins
TRADES_DIR = Path(r"D:\MIA_IA_system\logs_advanced\trades")
DATA_DIR = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")

# Mapping
CHART_MAP = {'ES': 3, 'NQ': 9, 'RTY': 1}
TICK_SIZE = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}

# Features a analyser
FEATURES = [
    'depth_imbalance', 'delta', 'ob_center', 'tick_momentum',
    'level1_imbalance', 'cum_delta_session', 'mia_bullish_score',
    'position_in_range', 'atr_ratio', 'confluence_strength',
    'confluence_proximity', 'menthorq_impact_score', 'pressure_strength',
    'institutional_pressure', 'smart_money_flow', 'volatility_regime'
]


def parse_all_trades():
    """Parse tous les trades"""
    trades = []

    for log_file in sorted(TRADES_DIR.glob("trades_*.log")):
        date_match = re.search(r'trades_(\d{8})\.log', log_file.name)
        if not date_match:
            continue

        date_str = date_match.group(1)

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        entries = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse ENTRY
            entry_match = re.search(r'\[(\w+)\] ENTRY.*direction.*?[\'"](\w+)[\'"].*price.*?(\d+\.?\d*)', line)
            if entry_match:
                symbol = entry_match.group(1)
                direction = entry_match.group(2)
                price = float(entry_match.group(3))
                time_match = re.search(r'^(\d{2}):(\d{2})', line)
                hour = int(time_match.group(1)) if time_match else 0
                minute = int(time_match.group(2)) if time_match else 0

                entries[symbol] = {
                    'date': date_str,
                    'hour': hour,
                    'minute': minute,
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': price
                }

            # Parse EXIT
            exit_match = re.search(r'\[(\w+)\] EXIT.*pnl_usd.*?([-\d.]+)', line)
            if exit_match:
                symbol = exit_match.group(1)
                pnl = float(exit_match.group(2))

                if symbol in entries:
                    trade = entries[symbol].copy()
                    trade['pnl'] = pnl
                    trade['result'] = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append(trade)
                    del entries[symbol]

    return trades


def get_base_timestamp(date_str):
    """Retourne le timestamp de base pour une date"""
    # Format: YYYYMMDD
    # Base verifiee: 01/12/2025 00:00 Paris (23:00 UTC 30/11) = 1764543600
    BASE_01DEC = 1764543600

    day = int(date_str[6:8])
    month = int(date_str[4:6])

    if month == 12:
        return BASE_01DEC + (day - 1) * 86400
    elif month == 11:
        # Novembre: 30 jours avant le 01/12
        return BASE_01DEC - (30 - day + 1) * 86400
    else:
        return BASE_01DEC  # Fallback


def load_snapshot_for_trade(trade):
    """Charge le snapshot correspondant a un trade"""
    date_str = trade['date']
    symbol = trade['symbol']
    hour = trade['hour']
    minute = trade['minute']
    price = trade['entry_price']

    # Trouver le bon mois
    month = "DECEMBRE" if date_str.startswith("202512") else "NOVEMBRE"

    chart_id = CHART_MAP.get(symbol)
    if not chart_id:
        return None

    ml_ready_dir = DATA_DIR / month / date_str / f"CHART_{chart_id}" / "ML_READY"
    if not ml_ready_dir.exists():
        return None

    jsonl_files = list(ml_ready_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None

    # Calculer timestamp cible
    base_ts = get_base_timestamp(date_str)
    target_hour_utc = hour - 1  # Paris = UTC+1
    target_ts = base_ts + (target_hour_utc * 3600) + (minute * 60)
    target_ts_start_ms = (target_ts - 180) * 1000
    target_ts_end_ms = (target_ts + 180) * 1000

    # Chercher le snapshot
    snapshots = []
    with open(jsonl_files[0], 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                snap = json.loads(line)
                t_ms = snap.get('t_ms', 0)
                if target_ts_start_ms <= t_ms <= target_ts_end_ms:
                    snapshots.append(snap)
            except:
                continue

    if not snapshots:
        return None

    # Trouver le plus proche du prix
    return min(snapshots, key=lambda s: abs(s.get('mid', 0) - price))


def analyze_feature_distribution(trades_with_snaps):
    """Analyse la distribution des features pour WIN vs LOSS"""

    wins = [t for t in trades_with_snaps if t['result'] == 'WIN']
    losses = [t for t in trades_with_snaps if t['result'] == 'LOSS']

    print("\n" + "="*100)
    print("ANALYSE DISTRIBUTION FEATURES: WINS vs LOSSES")
    print("="*100)

    significant_features = []

    print(f"\n{'Feature':<25} {'WIN mean':<12} {'LOSS mean':<12} {'Diff':<12} {'Signif':<10}")
    print("-"*100)

    for feature in FEATURES:
        win_vals = [t['snap'].get(feature, 0) for t in wins if t['snap'].get(feature) is not None]
        loss_vals = [t['snap'].get(feature, 0) for t in losses if t['snap'].get(feature) is not None]

        if not win_vals or not loss_vals:
            continue

        win_mean = mean(win_vals)
        loss_mean = mean(loss_vals)
        diff = win_mean - loss_mean

        # Calculer significance
        if abs(win_mean) > 0.001:
            diff_pct = abs(diff / win_mean) * 100
        else:
            diff_pct = abs(diff) * 100

        signif = "***" if diff_pct > 50 else "**" if diff_pct > 30 else "*" if diff_pct > 15 else ""

        if signif:
            significant_features.append((feature, win_mean, loss_mean, diff, diff_pct))

        print(f"{feature:<25} {win_mean:<+12.4f} {loss_mean:<+12.4f} {diff:<+12.4f} {signif:<10}")

    return significant_features


def analyze_winning_conditions(trades_with_snaps):
    """Trouve les conditions optimales pour gagner"""

    wins = [t for t in trades_with_snaps if t['result'] == 'WIN']
    losses = [t for t in trades_with_snaps if t['result'] == 'LOSS']

    print("\n" + "="*100)
    print("ANALYSE CONDITIONS GAGNANTES")
    print("="*100)

    # Analyser par direction
    for direction in ['LONG', 'SHORT']:
        dir_wins = [t for t in wins if t['direction'] == direction]
        dir_losses = [t for t in losses if t['direction'] == direction]

        if not dir_wins or not dir_losses:
            continue

        print(f"\n--- {direction} ---")
        print(f"Wins: {len(dir_wins)}, Losses: {len(dir_losses)}, WR: {len(dir_wins)/(len(dir_wins)+len(dir_losses))*100:.0f}%")

        # Trouver les seuils discriminants
        for feature in ['depth_imbalance', 'delta', 'ob_center', 'tick_momentum', 'cum_delta_session']:
            win_vals = [t['snap'].get(feature, 0) for t in dir_wins if t['snap'].get(feature) is not None]
            loss_vals = [t['snap'].get(feature, 0) for t in dir_losses if t['snap'].get(feature) is not None]

            if not win_vals or not loss_vals:
                continue

            win_mean = mean(win_vals)
            loss_mean = mean(loss_vals)

            print(f"   {feature}: WIN={win_mean:+.2f}, LOSS={loss_mean:+.2f}")


def analyze_time_patterns(trades_with_snaps):
    """Analyse les patterns par heure"""

    print("\n" + "="*100)
    print("ANALYSE PATTERNS TEMPORELS")
    print("="*100)

    by_hour = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})

    for t in trades_with_snaps:
        hour = t['hour']
        if t['result'] == 'WIN':
            by_hour[hour]['wins'] += 1
        else:
            by_hour[hour]['losses'] += 1
        by_hour[hour]['pnl'] += t['pnl']

    print(f"\n{'Heure':<8} {'Trades':<8} {'Wins':<8} {'Losses':<8} {'WR':<8} {'P&L':<12}")
    print("-"*60)

    for hour in sorted(by_hour.keys()):
        data = by_hour[hour]
        total = data['wins'] + data['losses']
        wr = data['wins'] / total * 100 if total else 0
        print(f"{hour:02d}:00    {total:<8} {data['wins']:<8} {data['losses']:<8} {wr:<7.0f}% ${data['pnl']:>+10.2f}")


def find_winning_rules(trades_with_snaps):
    """Decouvre des regles de trading gagnantes"""

    print("\n" + "="*100)
    print("DECOUVERTE DE REGLES GAGNANTES")
    print("="*100)

    rules_tested = []

    # Tester differentes regles
    rules = [
        # (nom, condition pour SHORT, condition pour LONG)
        ("tick_momentum aligne",
         lambda s, d: s.get('tick_momentum', 0) < -0.2 if d == 'SHORT' else s.get('tick_momentum', 0) > 0.2),
        ("delta aligne",
         lambda s, d: s.get('delta', 0) < 0 if d == 'SHORT' else s.get('delta', 0) > 0),
        ("cum_delta aligne",
         lambda s, d: s.get('cum_delta_session', 0) < 0 if d == 'SHORT' else s.get('cum_delta_session', 0) > 0),
        ("mia_score aligne",
         lambda s, d: s.get('mia_bullish_score', 0) < -0.3 if d == 'SHORT' else s.get('mia_bullish_score', 0) > 0.3),
        ("ob_center aligne",
         lambda s, d: s.get('ob_center', 0) < 0 if d == 'SHORT' else s.get('ob_center', 0) > 0),
        ("depth_imbalance aligne",
         lambda s, d: s.get('depth_imbalance', 0) < 0 if d == 'SHORT' else s.get('depth_imbalance', 0) > 0),
        ("pressure_strength > 0.1",
         lambda s, d: s.get('pressure_strength', 0) > 0.1),
        ("confluence_strength > 0.05",
         lambda s, d: s.get('confluence_strength', 0) > 0.05),
        ("NOT in value area",
         lambda s, d: not s.get('in_value_area', True)),
        ("volatility_regime == 1",
         lambda s, d: s.get('volatility_regime', 0) == 1),
    ]

    print(f"\n{'Regle':<35} {'Trades':<8} {'Wins':<8} {'WR':<8} {'P&L':<12}")
    print("-"*80)

    for rule_name, condition in rules:
        matching = []
        for t in trades_with_snaps:
            try:
                if condition(t['snap'], t['direction']):
                    matching.append(t)
            except:
                pass

        if len(matching) < 10:
            continue

        wins = sum(1 for t in matching if t['result'] == 'WIN')
        pnl = sum(t['pnl'] for t in matching)
        wr = wins / len(matching) * 100 if matching else 0

        rules_tested.append((rule_name, len(matching), wins, wr, pnl))
        print(f"{rule_name:<35} {len(matching):<8} {wins:<8} {wr:<7.0f}% ${pnl:>+10.2f}")

    # Combiner les meilleures regles
    print("\n" + "-"*80)
    print("REGLES COMBINEES")
    print("-"*80)

    # Regle combinee: tick_momentum + delta alignes
    combined = []
    for t in trades_with_snaps:
        snap = t['snap']
        direction = t['direction']

        tick_mom = snap.get('tick_momentum', 0)
        delta = snap.get('delta', 0)

        if direction == 'SHORT':
            if tick_mom < 0 and delta < 0:
                combined.append(t)
        else:
            if tick_mom > 0 and delta > 0:
                combined.append(t)

    if combined:
        wins = sum(1 for t in combined if t['result'] == 'WIN')
        pnl = sum(t['pnl'] for t in combined)
        wr = wins / len(combined) * 100
        print(f"{'tick_mom + delta alignes':<35} {len(combined):<8} {wins:<8} {wr:<7.0f}% ${pnl:>+10.2f}")

    # Regle combinee: 3 indicateurs alignes
    combined3 = []
    for t in trades_with_snaps:
        snap = t['snap']
        direction = t['direction']

        tick_mom = snap.get('tick_momentum', 0)
        delta = snap.get('delta', 0)
        ob = snap.get('ob_center', 0)

        if direction == 'SHORT':
            if tick_mom < 0 and delta < 0 and ob < 0:
                combined3.append(t)
        else:
            if tick_mom > 0 and delta > 0 and ob > 0:
                combined3.append(t)

    if combined3:
        wins = sum(1 for t in combined3 if t['result'] == 'WIN')
        pnl = sum(t['pnl'] for t in combined3)
        wr = wins / len(combined3) * 100
        print(f"{'tick_mom + delta + ob alignes':<35} {len(combined3):<8} {wins:<8} {wr:<7.0f}% ${pnl:>+10.2f}")

    return rules_tested


def main():
    print("="*100)
    print("AUDIT PATTERNS CACHES - 216 TRADES")
    print("="*100)

    # 1. Parse les trades
    print("\n[1] CHARGEMENT DES TRADES...")
    trades = parse_all_trades()
    print(f"   {len(trades)} trades charges")

    # 2. Charger les snapshots
    print("\n[2] CHARGEMENT DES SNAPSHOTS...")
    trades_with_snaps = []
    no_snap_count = 0

    for i, trade in enumerate(trades):
        if i % 20 == 0:
            print(f"   Processing {i}/{len(trades)}...")

        snap = load_snapshot_for_trade(trade)
        if snap:
            trade['snap'] = snap
            trades_with_snaps.append(trade)
        else:
            no_snap_count += 1

    print(f"\n   {len(trades_with_snaps)} trades avec snapshots")
    print(f"   {no_snap_count} trades sans snapshot")

    if not trades_with_snaps:
        print("\n[ERREUR] Aucun trade avec snapshot!")
        return

    # 3. Analyses
    significant = analyze_feature_distribution(trades_with_snaps)
    analyze_winning_conditions(trades_with_snaps)
    analyze_time_patterns(trades_with_snaps)
    rules = find_winning_rules(trades_with_snaps)

    # Resume
    print("\n" + "="*100)
    print("PATTERNS CACHES DECOUVERTS")
    print("="*100)

    if significant:
        print("\n   FEATURES LES PLUS DISCRIMINANTES:")
        for feat, win_m, loss_m, diff, pct in sorted(significant, key=lambda x: -x[4])[:5]:
            print(f"      - {feat}: WIN={win_m:+.3f}, LOSS={loss_m:+.3f} ({pct:.0f}% diff)")

    # Meilleures regles par WR
    best_rules = sorted(rules, key=lambda x: x[3], reverse=True)[:5]
    if best_rules:
        print("\n   MEILLEURES REGLES PAR WIN RATE:")
        for name, n, wins, wr, pnl in best_rules:
            print(f"      - {name}: {wr:.0f}% WR ({wins}/{n} trades, ${pnl:+.0f})")

    # Meilleures regles par P&L
    best_pnl = sorted(rules, key=lambda x: x[4], reverse=True)[:5]
    if best_pnl:
        print("\n   MEILLEURES REGLES PAR P&L:")
        for name, n, wins, wr, pnl in best_pnl:
            print(f"      - {name}: ${pnl:+.0f} ({wr:.0f}% WR, {n} trades)")


if __name__ == "__main__":
    main()
