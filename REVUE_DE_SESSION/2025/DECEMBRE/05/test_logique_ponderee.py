"""
TEST LOGIQUE PONDEREE vs LOGIQUE BINAIRE
=========================================

Objectif: Verifier que la nouvelle logique ponderee:
1. Bloque toujours les trades perdants du 05/12
2. Ne bloque pas les trades gagnants
3. Aurait laisse passer le trade +$937 du 04/12
"""

import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Donnees 05/12/2025
DATA_05DEC = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")
BASE_TS_05DEC = 1764892800  # 05/12/2025 00:00 UTC

# Donnees 04/12/2025
DATA_04DEC = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251204\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")
BASE_TS_04DEC = 1764806400  # 04/12/2025 00:00 UTC

# Trades 05/12/2025
TRADES_05DEC = [
    {"time": "20:00", "price": 25727.75, "direction": "SHORT", "result": "WIN", "pnl": 250},
    {"time": "20:13", "price": 25727.25, "direction": "SHORT", "result": "LOSS", "pnl": -125},
    {"time": "20:23", "price": 25726.75, "direction": "SHORT", "result": "WIN", "pnl": 250},
    {"time": "20:32", "price": 25720.00, "direction": "SHORT", "result": "WIN", "pnl": 120},
    {"time": "20:50", "price": 25710.88, "direction": "SHORT", "result": "LOSS", "pnl": -127},
]

# Trade bloque a tort le 04/12
TRADE_04DEC_BLOCKED = {"time": "16:28", "price": 25580.88, "direction": "SHORT", "result": "WIN", "pnl": 937}


def load_snapshot(data_path: Path, base_ts: int, hour: int, minute: int, target_price: float):
    """Charge le snapshot le plus proche"""
    target_hour_utc = hour - 1
    target_ts = base_ts + (target_hour_utc * 3600) + (minute * 60)
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


def check_binary_rule(snapshot: dict, direction: str) -> tuple:
    """ANCIENNE REGLE: Compte binaire (2+ signaux contre = bloquer)"""
    depth_imb = snapshot.get('depth_imbalance', 0)
    delta = snapshot.get('delta', 0)
    ob_center = snapshot.get('ob_center', 0)
    tick_mom = snapshot.get('tick_momentum', 0)

    if direction == "SHORT":
        counter = 0
        if depth_imb > 0.10: counter += 1
        if delta > 0: counter += 1
        if ob_center > 0.15: counter += 1
        if tick_mom > 0.20: counter += 1

        return counter < 2, f"Binaire: {counter} signaux contre"
    else:
        counter = 0
        if depth_imb < -0.10: counter += 1
        if delta < 0: counter += 1
        if ob_center < -0.15: counter += 1
        if tick_mom < -0.20: counter += 1

        return counter < 2, f"Binaire: {counter} signaux contre"


def check_weighted_rule(snapshot: dict, direction: str) -> tuple:
    """NOUVELLE REGLE: Score pondere par intensite"""
    depth_imb = snapshot.get('depth_imbalance', 0)
    delta = snapshot.get('delta', 0)
    ob_center = snapshot.get('ob_center', 0)
    tick_mom = snapshot.get('tick_momentum', 0)

    # Normaliser les valeurs
    DEPTH_NORM = 0.20
    DELTA_NORM = 100
    OB_NORM = 0.50
    TICK_NORM = 0.50

    if direction == "SHORT":
        # Score acheteur (contre SHORT)
        buyer_score = (
            max(0, depth_imb) / DEPTH_NORM +
            max(0, delta) / DELTA_NORM +
            max(0, ob_center) / OB_NORM +
            max(0, tick_mom) / TICK_NORM
        )

        # Score vendeur (pour SHORT)
        seller_score = (
            abs(min(0, depth_imb)) / DEPTH_NORM +
            abs(min(0, delta)) / DELTA_NORM +
            abs(min(0, ob_center)) / OB_NORM +
            abs(min(0, tick_mom)) / TICK_NORM
        )

        # Bloquer seulement si score acheteur > score vendeur * 1.5
        ratio = buyer_score / max(seller_score, 0.01)
        is_aligned = ratio < 1.5

        return is_aligned, f"Pondere: buyer={buyer_score:.2f}, seller={seller_score:.2f}, ratio={ratio:.2f}"

    else:  # LONG
        seller_score = (
            abs(min(0, depth_imb)) / DEPTH_NORM +
            abs(min(0, delta)) / DELTA_NORM +
            abs(min(0, ob_center)) / OB_NORM +
            abs(min(0, tick_mom)) / TICK_NORM
        )

        buyer_score = (
            max(0, depth_imb) / DEPTH_NORM +
            max(0, delta) / DELTA_NORM +
            max(0, ob_center) / OB_NORM +
            max(0, tick_mom) / TICK_NORM
        )

        ratio = seller_score / max(buyer_score, 0.01)
        is_aligned = ratio < 1.5

        return is_aligned, f"Pondere: seller={seller_score:.2f}, buyer={buyer_score:.2f}, ratio={ratio:.2f}"


def main():
    print("="*100)
    print("TEST: LOGIQUE BINAIRE vs LOGIQUE PONDEREE")
    print("="*100)

    print("\n" + "="*100)
    print("TRADES 05/12/2025 (aujourd'hui)")
    print("="*100)

    results_05dec = []

    for trade in TRADES_05DEC:
        hour, minute = map(int, trade["time"].split(":"))
        snap = load_snapshot(DATA_05DEC, BASE_TS_05DEC, hour, minute, trade["price"])

        if not snap:
            print(f"\n[ERROR] Snapshot non trouve pour {trade['time']}")
            continue

        binary_ok, binary_reason = check_binary_rule(snap, trade["direction"])
        weighted_ok, weighted_reason = check_weighted_rule(snap, trade["direction"])

        actual_win = trade["result"] == "WIN"
        binary_correct = (binary_ok == actual_win)
        weighted_correct = (weighted_ok == actual_win)

        print(f"\n{'-'*80}")
        print(f"TRADE {trade['time']} - {trade['direction']} @ {trade['price']} = {trade['result']} ({trade['pnl']:+}$)")
        print(f"   depth_imb={snap.get('depth_imbalance',0):+.3f}, delta={snap.get('delta',0):+.0f}, ob={snap.get('ob_center',0):+.3f}, tick_mom={snap.get('tick_momentum',0):+.3f}")
        print(f"   BINAIRE:  {'AUTORISER' if binary_ok else 'BLOQUER'} | {binary_reason} | {'CORRECT' if binary_correct else 'ERREUR'}")
        print(f"   PONDERE:  {'AUTORISER' if weighted_ok else 'BLOQUER'} | {weighted_reason} | {'CORRECT' if weighted_correct else 'ERREUR'}")

        results_05dec.append({
            'trade': trade,
            'binary_ok': binary_ok,
            'weighted_ok': weighted_ok,
            'binary_correct': binary_correct,
            'weighted_correct': weighted_correct,
            'actual_win': actual_win
        })

    # Trade 04/12 bloque a tort
    print("\n" + "="*100)
    print("TRADE 04/12/2025 BLOQUE A TORT (+$937)")
    print("="*100)

    trade = TRADE_04DEC_BLOCKED
    hour, minute = map(int, trade["time"].split(":"))
    snap = load_snapshot(DATA_04DEC, BASE_TS_04DEC, hour, minute, trade["price"])

    if snap:
        binary_ok, binary_reason = check_binary_rule(snap, trade["direction"])
        weighted_ok, weighted_reason = check_weighted_rule(snap, trade["direction"])

        print(f"\n{'-'*80}")
        print(f"TRADE {trade['time']} - {trade['direction']} @ {trade['price']} = {trade['result']} ({trade['pnl']:+}$)")
        print(f"   depth_imb={snap.get('depth_imbalance',0):+.3f}, delta={snap.get('delta',0):+.0f}, ob={snap.get('ob_center',0):+.3f}, tick_mom={snap.get('tick_momentum',0):+.3f}")
        print(f"   BINAIRE:  {'AUTORISER' if binary_ok else 'BLOQUER'} | {binary_reason}")
        print(f"   PONDERE:  {'AUTORISER' if weighted_ok else 'BLOQUER'} | {weighted_reason}")

        if weighted_ok and not binary_ok:
            print(f"\n   [SUCCESS] La logique PONDEREE aurait AUTORISE ce trade gagnant!")

    # Resume
    print("\n" + "="*100)
    print("RESUME COMPARATIF")
    print("="*100)

    binary_correct = sum(1 for r in results_05dec if r['binary_correct'])
    weighted_correct = sum(1 for r in results_05dec if r['weighted_correct'])
    total = len(results_05dec)

    print(f"\n   LOGIQUE BINAIRE:  {binary_correct}/{total} correct ({100*binary_correct/total:.0f}%)")
    print(f"   LOGIQUE PONDEREE: {weighted_correct}/{total} correct ({100*weighted_correct/total:.0f}%)")

    # Impact P&L
    binary_blocked_wins = sum(r['trade']['pnl'] for r in results_05dec if not r['binary_ok'] and r['actual_win'])
    binary_blocked_losses = sum(abs(r['trade']['pnl']) for r in results_05dec if not r['binary_ok'] and not r['actual_win'])

    weighted_blocked_wins = sum(r['trade']['pnl'] for r in results_05dec if not r['weighted_ok'] and r['actual_win'])
    weighted_blocked_losses = sum(abs(r['trade']['pnl']) for r in results_05dec if not r['weighted_ok'] and not r['actual_win'])

    print(f"\n   BINAIRE:")
    print(f"      Wins bloques: -${binary_blocked_wins}")
    print(f"      Losses bloques: +${binary_blocked_losses}")
    print(f"      Net: +${binary_blocked_losses - binary_blocked_wins}")

    print(f"\n   PONDERE:")
    print(f"      Wins bloques: -${weighted_blocked_wins}")
    print(f"      Losses bloques: +${weighted_blocked_losses}")
    print(f"      Net: +${weighted_blocked_losses - weighted_blocked_wins}")

    # Conclusion
    print("\n" + "="*100)
    print("CONCLUSION")
    print("="*100)

    if weighted_correct >= binary_correct:
        print("\n   [OK] La logique PONDEREE est au moins aussi bonne que la BINAIRE pour aujourd'hui")
    else:
        print("\n   [WARNING] La logique PONDEREE est moins bonne pour aujourd'hui!")


if __name__ == "__main__":
    main()

