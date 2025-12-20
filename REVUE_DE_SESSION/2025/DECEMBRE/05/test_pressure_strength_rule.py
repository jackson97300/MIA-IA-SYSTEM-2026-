"""
TEST REGLE PRESSURE_STRENGTH SUR SESSION 05/12/2025
=====================================================

Session qui a fait +$627.60 avec 6 trades
Testons si pressure_strength > 0.1 aurait ameliore ou degrade
"""

import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")
BASE_TS = 1764892800  # 05/12/2025 00:00 UTC

# Trades reels du 05/12/2025 (de la revue de session)
TRADES_05DEC = [
    # London session
    {"time": "08:08", "symbol": "ES", "direction": "SHORT", "price": 6080.75, "pnl": -262.40, "result": "LOSS"},

    # Power Hour
    {"time": "20:00", "symbol": "NQ", "direction": "SHORT", "price": 25727.75, "pnl": 250, "result": "WIN"},
    {"time": "20:13", "symbol": "NQ", "direction": "SHORT", "price": 25727.25, "pnl": -125, "result": "LOSS"},
    {"time": "20:23", "symbol": "NQ", "direction": "SHORT", "price": 25726.75, "pnl": 250, "result": "WIN"},
    {"time": "20:32", "symbol": "NQ", "direction": "SHORT", "price": 25720.00, "pnl": 120, "result": "WIN"},
    {"time": "20:50", "symbol": "NQ", "direction": "SHORT", "price": 25710.88, "pnl": -127.40, "result": "LOSS"},
]


def load_snapshot(hour: int, minute: int, target_price: float):
    """Charge le snapshot le plus proche"""
    target_hour_utc = hour - 1
    target_ts = BASE_TS + (target_hour_utc * 3600) + (minute * 60)
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
    print("TEST REGLE PRESSURE_STRENGTH > 0.1 - SESSION 05/12/2025")
    print("="*100)
    print("\nResultat reel de la session: +$627.60 (6 trades)")
    print("Objectif: Verifier si pressure_strength > 0.1 ameliore ou degrade\n")

    MIN_PRESSURE = 0.10

    results = []

    for trade in TRADES_05DEC:
        hour, minute = map(int, trade["time"].split(":"))

        # Pour ES, on n'a pas les donnees NQ
        if trade["symbol"] == "ES":
            print(f"\n{'-'*80}")
            print(f"TRADE {trade['time']} - {trade['symbol']} {trade['direction']} = {trade['result']} ({trade['pnl']:+}$)")
            print(f"   [SKIP] Pas de snapshot ES disponible dans ce test")
            continue

        snap = load_snapshot(hour, minute, trade["price"])

        if not snap:
            print(f"\n{'-'*80}")
            print(f"TRADE {trade['time']} - {trade['symbol']} {trade['direction']} = {trade['result']} ({trade['pnl']:+}$)")
            print(f"   [ERROR] Snapshot non trouve")
            continue

        pressure = snap.get('pressure_strength', 0)
        pressure_ok = pressure > MIN_PRESSURE

        actual_win = trade["result"] == "WIN"

        # La regle est correcte si:
        # - Elle autorise un WIN (pressure_ok=True, actual_win=True)
        # - Elle bloque un LOSS (pressure_ok=False, actual_win=False)
        rule_correct = (pressure_ok == actual_win)

        print(f"\n{'-'*80}")
        print(f"TRADE {trade['time']} - {trade['symbol']} {trade['direction']} = {trade['result']} ({trade['pnl']:+}$)")
        print(f"   pressure_strength: {pressure:.4f}")
        print(f"   Seuil: {MIN_PRESSURE}")
        print(f"   Decision: {'AUTORISER' if pressure_ok else 'BLOQUER'}")
        print(f"   Verdict: {'CORRECT' if rule_correct else 'ERREUR'}")

        results.append({
            'trade': trade,
            'pressure': pressure,
            'pressure_ok': pressure_ok,
            'actual_win': actual_win,
            'rule_correct': rule_correct
        })

    # Resume
    print("\n" + "="*100)
    print("RESUME")
    print("="*100)

    if not results:
        print("\n   Pas de donnees a analyser")
        return

    correct = sum(1 for r in results if r['rule_correct'])
    total = len(results)

    print(f"\n   Decisions correctes: {correct}/{total} ({100*correct/total:.0f}%)")

    # Calculer P&L avec et sans la regle
    pnl_sans_regle = sum(r['trade']['pnl'] for r in results)

    # Avec la regle: on ne prend que les trades ou pressure > 0.1
    pnl_avec_regle = sum(r['trade']['pnl'] for r in results if r['pressure_ok'])
    trades_avec_regle = sum(1 for r in results if r['pressure_ok'])

    # Pertes evitees (trades LOSS bloques)
    pertes_evitees = sum(abs(r['trade']['pnl']) for r in results if not r['pressure_ok'] and not r['actual_win'])

    # Gains manques (trades WIN bloques)
    gains_manques = sum(r['trade']['pnl'] for r in results if not r['pressure_ok'] and r['actual_win'])

    print(f"\n   SANS la regle:")
    print(f"      Trades: {total}")
    print(f"      P&L: ${pnl_sans_regle:+.2f}")

    print(f"\n   AVEC la regle (pressure > {MIN_PRESSURE}):")
    print(f"      Trades: {trades_avec_regle}")
    print(f"      P&L: ${pnl_avec_regle:+.2f}")
    print(f"      Pertes evitees: ${pertes_evitees:+.2f}")
    print(f"      Gains manques: ${gains_manques:+.2f}")

    diff = pnl_avec_regle - pnl_sans_regle + pertes_evitees
    print(f"\n   IMPACT NET: ${diff:+.2f}")

    if diff > 0:
        print(f"\n   [SUCCESS] La regle AMELIORE les resultats de ${diff:.2f}!")
    elif diff < 0:
        print(f"\n   [ATTENTION] La regle DEGRADE les resultats de ${abs(diff):.2f}")
    else:
        print(f"\n   [NEUTRE] La regle ne change rien")

    # Detail par trade
    print("\n" + "="*100)
    print("DETAIL PAR TRADE")
    print("="*100)
    print(f"\n{'Heure':<8} {'Resultat':<8} {'Pressure':<10} {'Decision':<12} {'Impact':<15}")
    print("-"*60)

    for r in results:
        trade = r['trade']
        decision = "AUTORISER" if r['pressure_ok'] else "BLOQUER"

        if r['pressure_ok']:
            impact = f"{trade['pnl']:+.0f}$ (pris)"
        else:
            if r['actual_win']:
                impact = f"{trade['pnl']:+.0f}$ MANQUE!"
            else:
                impact = f"{abs(trade['pnl']):+.0f}$ EVITE!"

        print(f"{trade['time']:<8} {trade['result']:<8} {r['pressure']:<10.4f} {decision:<12} {impact:<15}")


if __name__ == "__main__":
    main()

