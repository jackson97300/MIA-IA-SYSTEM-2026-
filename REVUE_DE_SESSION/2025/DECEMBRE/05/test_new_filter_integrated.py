"""
TEST FINAL - NOUVELLE REGLE ORDERFLOW INTEGREE
===============================================

Test que la nouvelle regle dans ml_3layer_filter.py fonctionne correctement.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from ml.ml_3layer_filter import ML3LayerFilter, TradeSignal

DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")

TRADES = [
    {"time": "20:00", "price": 25727.75, "direction": "SHORT", "result": "WIN", "pnl": 250},
    {"time": "20:13", "price": 25727.25, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "20:23", "price": 25726.75, "direction": "SHORT", "result": "WIN", "pnl": 250},
    {"time": "20:32", "price": 25720.00, "direction": "SHORT", "result": "WIN", "pnl": 120},
    {"time": "20:50", "price": 25710.88, "direction": "SHORT", "result": "LOSS", "pnl": -127},
]


def load_snapshot(hour: int, minute: int, target_price: float):
    target_hour_utc = hour - 1
    target_ts = 1764892800 + (target_hour_utc * 3600) + (minute * 60)
    target_ts_start_ms = (target_ts - 180) * 1000
    target_ts_end_ms = (target_ts + 180) * 1000

    snapshots = []
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
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


def main():
    print("="*100)
    print("TEST FINAL - NOUVELLE REGLE ORDERFLOW INTEGREE")
    print("="*100)

    ml_filter = ML3LayerFilter()

    results = []

    for trade in TRADES:
        hour, minute = map(int, trade["time"].split(":"))
        snap = load_snapshot(hour, minute, trade["price"])

        if not snap:
            print(f"\n[ERROR] Snapshot non trouve pour {trade['time']}")
            continue

        # Tester la nouvelle methode directement
        signal = TradeSignal.SHORT if trade["direction"] == "SHORT" else TradeSignal.LONG

        is_aligned, reason, counter_count = ml_filter._check_orderflow_alignment(snap, signal)

        # Calculer si la decision est correcte
        actual_win = trade["result"] == "WIN"
        rule_correct = (is_aligned == actual_win)

        print(f"\n{'='*80}")
        print(f"TRADE {trade['time']} - {trade['direction']} @ {trade['price']}")
        print(f"Resultat reel: {trade['result']} ({trade['pnl']:+}$)")
        print(f"-"*50)
        print(f"   depth_imb:   {snap.get('depth_imbalance', 0):+.3f}")
        print(f"   delta:       {snap.get('delta', 0):+.0f}")
        print(f"   ob_center:   {snap.get('ob_center', 0):+.3f}")
        print(f"   tick_mom:    {snap.get('tick_momentum', 0):+.3f}")
        print(f"-"*50)
        print(f"   Signaux contre: {counter_count}")
        print(f"   Decision: {'AUTORISER' if is_aligned else 'BLOQUER'}")
        print(f"   Raison: {reason}")
        print(f"   VERDICT: {'CORRECT!' if rule_correct else 'ERREUR'}")

        results.append({
            'trade': trade,
            'is_aligned': is_aligned,
            'actual_win': actual_win,
            'rule_correct': rule_correct,
            'counter_count': counter_count
        })

    # Resume
    print("\n" + "="*100)
    print("RESUME FINAL")
    print("="*100)

    correct_count = sum(1 for r in results if r['rule_correct'])
    total = len(results)

    print(f"\n   Decisions correctes: {correct_count}/{total} ({100*correct_count/total:.0f}%)")

    # Calculer impact P&L
    wins_allowed = sum(r['trade']['pnl'] for r in results if r['is_aligned'] and r['actual_win'])
    losses_blocked = sum(abs(r['trade']['pnl']) for r in results if not r['is_aligned'] and not r['actual_win'])
    losses_allowed = sum(abs(r['trade']['pnl']) for r in results if r['is_aligned'] and not r['actual_win'])
    wins_blocked = sum(r['trade']['pnl'] for r in results if not r['is_aligned'] and r['actual_win'])

    print(f"\n   [GAINS]")
    print(f"   Wins autorises:    +${wins_allowed}")
    print(f"   Losses bloques:    +${losses_blocked} (evites)")
    print(f"\n   [PERTES]")
    print(f"   Losses autorises:  -${losses_allowed}")
    print(f"   Wins bloques:      -${wins_blocked} (manques)")

    net_impact = wins_allowed + losses_blocked - losses_allowed - wins_blocked
    print(f"\n   IMPACT NET: {'+' if net_impact >= 0 else ''}{net_impact}$")

    if net_impact > 0:
        print("\n   [SUCCESS] La nouvelle regle FONCTIONNE et AMELIORE les resultats!")
        print("   >>> IMPLEMENTATION VALIDEE <<<")
    else:
        print("\n   [WARNING] La regle n'ameliore pas les resultats")


if __name__ == "__main__":
    main()

