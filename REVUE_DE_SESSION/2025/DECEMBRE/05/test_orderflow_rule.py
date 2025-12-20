"""
TEST NOUVELLE REGLE ORDERFLOW
==============================

Regle: Pour un SHORT, bloquer si OrderFlow montre pression acheteuse:
- depth_imbalance > 0.10 (DOM biaise achat)
- delta > 0 (flux acheteur)
- ob_center > 0.15 (carnet biaise achat)

Objectif: Valider que cette regle aurait bloque les trades perdants
tout en laissant passer les gagnants.
"""

import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")

TRADES = [
    {"time": "20:00", "price": 25727.75, "direction": "SHORT", "result": "WIN", "pnl": 250},
    {"time": "20:13", "price": 25727.25, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "20:23", "price": 25726.75, "direction": "SHORT", "result": "WIN", "pnl": 250},
    {"time": "20:32", "price": 25720.00, "direction": "SHORT", "result": "WIN", "pnl": 120},
    {"time": "20:50", "price": 25710.88, "direction": "SHORT", "result": "LOSS", "pnl": -127},
]


def load_snapshot(hour: int, minute: int, target_price: float):
    """Charge le snapshot le plus proche"""
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


def check_orderflow_alignment(snapshot: dict, direction: str) -> tuple:
    """
    NOUVELLE REGLE: Verifie que l'OrderFlow est aligne avec la direction

    Pour SHORT: On veut pression VENDEUSE (valeurs negatives)
    Pour LONG: On veut pression ACHETEUSE (valeurs positives)

    Returns: (is_aligned, reason, details)
    """
    depth_imb = snapshot.get('depth_imbalance', 0)
    delta = snapshot.get('delta', 0)
    ob_center = snapshot.get('ob_center', 0)
    tick_mom = snapshot.get('tick_momentum', 0)
    l1_imb = snapshot.get('level1_imbalance', 0)

    details = {
        'depth_imbalance': depth_imb,
        'delta': delta,
        'ob_center': ob_center,
        'tick_momentum': tick_mom,
        'level1_imbalance': l1_imb
    }

    if direction == "SHORT":
        # Pour SHORT, on veut des signaux VENDEURS (negatifs)
        # BLOQUER si trop de signaux ACHETEURS

        buyer_pressure_count = 0
        reasons = []

        if depth_imb > 0.10:
            buyer_pressure_count += 1
            reasons.append(f"depth_imb={depth_imb:+.2f}>0.10")

        if delta > 0:
            buyer_pressure_count += 1
            reasons.append(f"delta={delta:+.0f}>0")

        if ob_center > 0.15:
            buyer_pressure_count += 1
            reasons.append(f"ob_center={ob_center:+.2f}>0.15")

        if tick_mom > 0.20:
            buyer_pressure_count += 1
            reasons.append(f"tick_mom={tick_mom:+.2f}>0.20")

        # BLOQUER si 2+ signaux acheteurs
        if buyer_pressure_count >= 2:
            return False, f"BLOQUER SHORT: {buyer_pressure_count} signaux acheteurs ({', '.join(reasons)})", details

        return True, f"OK SHORT: Pression vendeuse confirmee", details

    else:  # LONG
        # Pour LONG, on veut des signaux ACHETEURS (positifs)
        # BLOQUER si trop de signaux VENDEURS

        seller_pressure_count = 0
        reasons = []

        if depth_imb < -0.10:
            seller_pressure_count += 1
            reasons.append(f"depth_imb={depth_imb:+.2f}<-0.10")

        if delta < 0:
            seller_pressure_count += 1
            reasons.append(f"delta={delta:+.0f}<0")

        if ob_center < -0.15:
            seller_pressure_count += 1
            reasons.append(f"ob_center={ob_center:+.2f}<-0.15")

        if tick_mom < -0.20:
            seller_pressure_count += 1
            reasons.append(f"tick_mom={tick_mom:+.2f}<-0.20")

        # BLOQUER si 2+ signaux vendeurs
        if seller_pressure_count >= 2:
            return False, f"BLOQUER LONG: {seller_pressure_count} signaux vendeurs ({', '.join(reasons)})", details

        return True, f"OK LONG: Pression acheteuse confirmee", details


def main():
    print("="*100)
    print("TEST NOUVELLE REGLE ORDERFLOW")
    print("="*100)
    print("\nRegle: Bloquer si 2+ indicateurs OrderFlow sont contre la direction du trade")
    print("Pour SHORT: depth_imb>0.10, delta>0, ob_center>0.15, tick_mom>0.20")
    print("Pour LONG: depth_imb<-0.10, delta<0, ob_center<-0.15, tick_mom<-0.20")

    results = []

    for trade in TRADES:
        hour, minute = map(int, trade["time"].split(":"))
        snap = load_snapshot(hour, minute, trade["price"])

        if not snap:
            print(f"\n[ERROR] Snapshot non trouve pour {trade['time']}")
            continue

        is_aligned, reason, details = check_orderflow_alignment(snap, trade["direction"])

        print(f"\n{'='*100}")
        print(f"TRADE {trade['time']} - {trade['direction']} @ {trade['price']}")
        print(f"Resultat reel: {trade['result']} ({trade['pnl']:+}$)")
        print("-"*50)
        print(f"   depth_imbalance: {details['depth_imbalance']:+.3f}")
        print(f"   delta:           {details['delta']:+.0f}")
        print(f"   ob_center:       {details['ob_center']:+.3f}")
        print(f"   tick_momentum:   {details['tick_momentum']:+.3f}")
        print(f"   level1_imbalance:{details['level1_imbalance']:+.3f}")
        print("-"*50)

        would_allow = is_aligned
        actual_win = trade["result"] == "WIN"

        # La regle est CORRECTE si:
        # - Elle autorise un trade gagnant (would_allow=True, actual_win=True)
        # - Elle bloque un trade perdant (would_allow=False, actual_win=False)
        rule_correct = (would_allow == actual_win)

        print(f"\n   DECISION NOUVELLE REGLE: {'AUTORISER' if would_allow else 'BLOQUER'}")
        print(f"   Raison: {reason}")
        print(f"   VERDICT: {'CORRECT!' if rule_correct else 'ERREUR'}")

        results.append({
            'trade': trade,
            'would_allow': would_allow,
            'actual_win': actual_win,
            'rule_correct': rule_correct,
            'details': details
        })

    # Resume
    print("\n" + "="*100)
    print("RESUME DU TEST")
    print("="*100)

    correct_count = sum(1 for r in results if r['rule_correct'])
    total = len(results)

    print(f"\n   Decisions correctes: {correct_count}/{total} ({100*correct_count/total:.0f}%)")

    # Calculer les gains
    wins_allowed = sum(r['trade']['pnl'] for r in results if r['would_allow'] and r['actual_win'])
    losses_blocked = sum(abs(r['trade']['pnl']) for r in results if not r['would_allow'] and not r['actual_win'])
    losses_allowed = sum(abs(r['trade']['pnl']) for r in results if r['would_allow'] and not r['actual_win'])
    wins_blocked = sum(r['trade']['pnl'] for r in results if not r['would_allow'] and r['actual_win'])

    print(f"\n   [GAINS]")
    print(f"   Wins autorises:    +${wins_allowed}")
    print(f"   Losses bloques:    +${losses_blocked} (evites)")
    print(f"\n   [PERTES]")
    print(f"   Losses autorises:  -${losses_allowed}")
    print(f"   Wins bloques:      -${wins_blocked} (manques)")

    net_impact = wins_allowed + losses_blocked - losses_allowed - wins_blocked
    print(f"\n   IMPACT NET: {'+' if net_impact >= 0 else ''}{net_impact}$")

    if net_impact > 0:
        print("\n   [SUCCESS] La nouvelle regle AMELIORE les resultats!")
    else:
        print("\n   [WARNING] La nouvelle regle n'ameliore pas les resultats")


if __name__ == "__main__":
    main()

