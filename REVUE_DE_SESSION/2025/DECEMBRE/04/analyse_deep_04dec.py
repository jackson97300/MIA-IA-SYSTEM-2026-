"""
ANALYSE PROFONDE - SESSION 04/12/2025
=====================================

Objectif: Trouver les patterns des trades perdants et tester notre nouvelle regle
"""

import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Chemins des donnees
NQ_DATA = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251204\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")
ES_DATA = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251204\CHART_3\ML_READY\ml_ESZ25_FUT_CME_3.jsonl")

# Trades perdants du 04/12 - NQ US Open (la zone problematique)
TRADES_NQ_US_OPEN = [
    {"time": "15:55", "price": 25592.13, "direction": "SHORT", "result": "LOSS", "pnl": -127},
    {"time": "16:05", "price": 25581.00, "direction": "SHORT", "result": "LOSS", "pnl": -327},
    {"time": "16:09", "price": 25582.25, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "16:17", "price": 25580.38, "direction": "SHORT", "result": "LOSS", "pnl": -127},
    {"time": "16:26", "price": 25530.50, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "16:31", "price": 25589.50, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "16:34", "price": 25594.75, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "16:36", "price": 25599.00, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "16:48", "price": 25599.25, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "16:53", "price": 25585.88, "direction": "SHORT", "result": "LOSS", "pnl": -127},
]

# Trades gagnants pour comparaison
TRADES_NQ_WINS = [
    {"time": "16:21", "price": 25588.75, "direction": "SHORT", "result": "WIN", "pnl": 20},
    {"time": "16:28", "price": 25580.88, "direction": "SHORT", "result": "WIN", "pnl": 937},
    {"time": "16:51", "price": 25589.38, "direction": "SHORT", "result": "WIN", "pnl": 12},
    {"time": "16:57", "price": 25581.13, "direction": "SHORT", "result": "WIN", "pnl": 252},
]


def load_snapshot(data_path: Path, hour: int, minute: int, target_price: float):
    """Charge le snapshot le plus proche"""
    # Timestamp pour 04/12/2025
    # Base: Premier snapshot du fichier est ~1764802802000 ms (23:00 UTC 03/12)
    # 04/12/2025 00:00 UTC = 1764806400 secondes
    BASE_TS = 1764806400
    target_hour_utc = hour - 1  # Paris = UTC+1
    target_ts = BASE_TS + (target_hour_utc * 3600) + (minute * 60)
    target_ts_start_ms = (target_ts - 180) * 1000
    target_ts_end_ms = (target_ts + 180) * 1000

    snapshots = []
    with open(data_path, 'r', encoding='utf-8') as f:
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
    return min(snapshots, key=lambda s: abs(s.get('mid', 0) - target_price))


def check_orderflow_alignment(snapshot: dict, direction: str) -> tuple:
    """Notre nouvelle regle"""
    depth_imb = snapshot.get('depth_imbalance', 0)
    delta = snapshot.get('delta', 0)
    ob_center = snapshot.get('ob_center', 0)
    tick_mom = snapshot.get('tick_momentum', 0)

    DEPTH_IMB_THRESHOLD = 0.10
    OB_CENTER_THRESHOLD = 0.15
    TICK_MOM_THRESHOLD = 0.20

    if direction == "SHORT":
        counter_signals = 0
        reasons = []

        if depth_imb > DEPTH_IMB_THRESHOLD:
            counter_signals += 1
            reasons.append(f"depth_imb={depth_imb:+.2f}>+{DEPTH_IMB_THRESHOLD}")

        if delta > 0:
            counter_signals += 1
            reasons.append(f"delta={delta:+.0f}>0")

        if ob_center > OB_CENTER_THRESHOLD:
            counter_signals += 1
            reasons.append(f"ob_center={ob_center:+.2f}>+{OB_CENTER_THRESHOLD}")

        if tick_mom > TICK_MOM_THRESHOLD:
            counter_signals += 1
            reasons.append(f"tick_mom={tick_mom:+.2f}>+{TICK_MOM_THRESHOLD}")

        if counter_signals >= 2:
            return False, f"BLOQUER: {counter_signals} signaux acheteurs ({', '.join(reasons)})", counter_signals

        return True, "OK: Pression vendeuse", counter_signals

    else:  # LONG
        counter_signals = 0
        reasons = []

        if depth_imb < -DEPTH_IMB_THRESHOLD:
            counter_signals += 1
            reasons.append(f"depth_imb={depth_imb:+.2f}")
        if delta < 0:
            counter_signals += 1
            reasons.append(f"delta={delta:+.0f}")
        if ob_center < -OB_CENTER_THRESHOLD:
            counter_signals += 1
            reasons.append(f"ob_center={ob_center:+.2f}")
        if tick_mom < -TICK_MOM_THRESHOLD:
            counter_signals += 1
            reasons.append(f"tick_mom={tick_mom:+.2f}")

        if counter_signals >= 2:
            return False, f"BLOQUER: {counter_signals} signaux vendeurs ({', '.join(reasons)})", counter_signals

        return True, "OK: Pression acheteuse", counter_signals


def analyze_trades(trades: list, data_path: Path, label: str):
    """Analyse un groupe de trades"""
    print(f"\n{'='*100}")
    print(f"{label}")
    print(f"{'='*100}")

    results = []
    all_snapshots = []

    for trade in trades:
        hour, minute = map(int, trade["time"].split(":"))
        snap = load_snapshot(data_path, hour, minute, trade["price"])

        if not snap:
            print(f"\n[ERROR] Snapshot non trouve pour {trade['time']}")
            continue

        all_snapshots.append(snap)

        is_aligned, reason, counter = check_orderflow_alignment(snap, trade["direction"])

        actual_win = trade["result"] == "WIN"
        rule_correct = (is_aligned == actual_win)

        print(f"\n{'-'*80}")
        print(f"TRADE {trade['time']} - {trade['direction']} @ {trade['price']}")
        print(f"Resultat: {trade['result']} ({trade['pnl']:+}$)")
        print(f"   depth_imb:   {snap.get('depth_imbalance', 0):+.3f}")
        print(f"   delta:       {snap.get('delta', 0):+.0f}")
        print(f"   ob_center:   {snap.get('ob_center', 0):+.3f}")
        print(f"   tick_mom:    {snap.get('tick_momentum', 0):+.3f}")
        print(f"   Signaux contre: {counter}")
        print(f"   Decision: {'AUTORISER' if is_aligned else 'BLOQUER'} | {reason}")
        print(f"   VERDICT: {'CORRECT' if rule_correct else 'ERREUR'}")

        results.append({
            'trade': trade,
            'snap': snap,
            'is_aligned': is_aligned,
            'actual_win': actual_win,
            'rule_correct': rule_correct,
            'counter': counter
        })

    return results, all_snapshots


def main():
    print("="*100)
    print("ANALYSE PROFONDE - SESSION 04/12/2025 - US OPEN NQ")
    print("="*100)
    print("\nObjectif: Tester notre nouvelle regle OrderFlow sur les trades perdants")

    # Analyser les trades perdants
    loss_results, loss_snaps = analyze_trades(
        TRADES_NQ_US_OPEN, NQ_DATA,
        "TRADES PERDANTS NQ - US OPEN (15:55-16:55)"
    )

    # Analyser les trades gagnants
    win_results, win_snaps = analyze_trades(
        TRADES_NQ_WINS, NQ_DATA,
        "TRADES GAGNANTS NQ - US OPEN (pour comparaison)"
    )

    # Resume global
    print("\n" + "="*100)
    print("RESUME GLOBAL")
    print("="*100)

    all_results = loss_results + win_results
    correct_count = sum(1 for r in all_results if r['rule_correct'])
    total = len(all_results)

    print(f"\n   Decisions correctes: {correct_count}/{total} ({100*correct_count/total:.0f}%)")

    # Impact financier
    losses_blocked = sum(abs(r['trade']['pnl']) for r in all_results
                         if not r['is_aligned'] and not r['actual_win'])
    wins_blocked = sum(r['trade']['pnl'] for r in all_results
                       if not r['is_aligned'] and r['actual_win'])
    losses_allowed = sum(abs(r['trade']['pnl']) for r in all_results
                         if r['is_aligned'] and not r['actual_win'])
    wins_allowed = sum(r['trade']['pnl'] for r in all_results
                       if r['is_aligned'] and r['actual_win'])

    print(f"\n   [GAINS]")
    print(f"   Wins autorises:    +${wins_allowed}")
    print(f"   Losses bloques:    +${losses_blocked} (evites)")
    print(f"\n   [PERTES]")
    print(f"   Losses autorises:  -${losses_allowed}")
    print(f"   Wins bloques:      -${wins_blocked} (manques)")

    net_impact = wins_allowed + losses_blocked - losses_allowed - wins_blocked
    print(f"\n   IMPACT NET: {'+' if net_impact >= 0 else ''}{net_impact}$")

    # Comparaison moyennes
    print("\n" + "="*100)
    print("COMPARAISON MOYENNES: WINS vs LOSSES")
    print("="*100)

    if loss_snaps and win_snaps:
        fields = ['depth_imbalance', 'delta', 'ob_center', 'tick_momentum',
                  'level1_imbalance', 'cum_delta_session', 'mia_bullish_score']

        print("\n{:<25} {:>15} {:>15} {:>15}".format("CHAMP", "WINS", "LOSSES", "DIFF"))
        print("-"*70)

        for field in fields:
            win_vals = [s.get(field, 0) for s in win_snaps if s.get(field) is not None]
            loss_vals = [s.get(field, 0) for s in loss_snaps if s.get(field) is not None]

            if win_vals and loss_vals:
                win_avg = sum(win_vals) / len(win_vals)
                loss_avg = sum(loss_vals) / len(loss_vals)
                diff = loss_avg - win_avg

                marker = " <--" if abs(diff) > abs(win_avg) * 0.3 else ""
                print("{:<25} {:>+15.2f} {:>+15.2f} {:>+15.2f}{}".format(
                    field, win_avg, loss_avg, diff, marker
                ))

    # Conclusion
    print("\n" + "="*100)
    print("CONCLUSION")
    print("="*100)

    blocked_losses = sum(1 for r in loss_results if not r['is_aligned'])
    total_losses = len(loss_results)

    print(f"\n   Trades perdants bloques: {blocked_losses}/{total_losses}")
    print(f"   Trades gagnants preserves: {sum(1 for r in win_results if r['is_aligned'])}/{len(win_results)}")

    if losses_blocked > 0:
        print(f"\n   [SUCCESS] La regle aurait evite ${losses_blocked} de pertes!")

    # Chercher d'autres patterns
    print("\n" + "="*100)
    print("AUTRES PATTERNS DETECTES")
    print("="*100)

    for r in all_results:
        snap = r['snap']
        trade = r['trade']

        cum_delta = snap.get('cum_delta_session', 0)
        position_range = snap.get('position_in_range', 50)
        in_va = snap.get('in_value_area', False)

        anomalies = []

        # Pattern 1: Position extreme dans le range
        if position_range > 80 or position_range < 20:
            anomalies.append(f"Position extreme: {position_range:.0f}%")

        # Pattern 2: Cum delta fort contre direction
        if trade['direction'] == 'SHORT' and cum_delta > 1000:
            anomalies.append(f"Cum delta BULLISH: {cum_delta:+.0f}")
        elif trade['direction'] == 'LONG' and cum_delta < -1000:
            anomalies.append(f"Cum delta BEARISH: {cum_delta:+.0f}")

        if anomalies and trade['result'] == 'LOSS':
            print(f"\n   {trade['time']} ({trade['result']}): {', '.join(anomalies)}")


if __name__ == "__main__":
    main()
