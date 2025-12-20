"""
TEST PRESSURE_STRENGTH SUR TRADES RÉELS 05/12/2025 - V2
========================================================
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Chemins
DATA_NQ = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")
DATA_ES = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_3\ML_READY\ml_ESZ25_FUT_CME_3.jsonl")

# Trades réels du 05/12/2025
TRADES = [
    # London (heure Paris)
    {"time": "08:12", "symbol": "NQ", "direction": "SHORT", "price": 25712.00, "pnl": -125.00, "result": "LOSS"},
    {"time": "08:22", "symbol": "NQ", "direction": "SHORT", "price": 25711.88, "pnl": -137.40, "result": "LOSS"},
    # US Morning
    {"time": "16:48", "symbol": "ES", "direction": "SHORT", "price": 6897.63, "pnl": -256.00, "result": "LOSS"},
    # Power Hour
    {"time": "20:01", "symbol": "NQ", "direction": "SHORT", "price": 25727.75, "pnl": 250.00, "result": "WIN"},
    {"time": "20:13", "symbol": "NQ", "direction": "SHORT", "price": 25727.25, "pnl": -125.00, "result": "LOSS"},
    {"time": "20:23", "symbol": "NQ", "direction": "SHORT", "price": 25726.75, "pnl": 250.00, "result": "WIN"},
    {"time": "20:32", "symbol": "NQ", "direction": "SHORT", "price": 25720.00, "pnl": 120.00, "result": "WIN"},
    {"time": "20:50", "symbol": "NQ", "direction": "SHORT", "price": 25710.88, "pnl": -127.40, "result": "LOSS"},
]


def load_all_snapshots(symbol: str):
    """Charge tous les snapshots"""
    path = DATA_NQ if symbol == "NQ" else DATA_ES
    if not path.exists():
        return []

    snaps = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snaps.append(json.loads(line))
                except:
                    pass
    return snaps


def find_snapshot(snaps: list, hour_paris: int, minute: int, target_price: float):
    """Trouve le snapshot correspondant"""
    # Paris = UTC+1, donc 20h Paris = 19h UTC
    hour_utc = hour_paris - 1

    # Filtrer par heure
    matching = []
    for s in snaps:
        dt = datetime.fromtimestamp(s['t_ms'] / 1000, tz=timezone.utc)
        if dt.hour == hour_utc and abs(dt.minute - minute) <= 5:
            matching.append(s)

    if not matching:
        return None

    # Trouver le plus proche du prix
    return min(matching, key=lambda s: abs(s.get('mid', 0) - target_price))


def main():
    print("="*100)
    print("🎯 TEST PRESSURE_STRENGTH - TRADES RÉELS 05/12/2025")
    print("="*100)

    # Charger données
    print("\n📥 Chargement des données...")
    snaps_nq = load_all_snapshots("NQ")
    snaps_es = load_all_snapshots("ES")
    print(f"   NQ: {len(snaps_nq):,} snapshots")
    print(f"   ES: {len(snaps_es):,} snapshots")

    # Analyser chaque trade
    print("\n" + "-"*100)
    print(f"{'Heure':<8} {'Sym':<4} {'Résultat':<8} {'P&L':<12} {'Pressure':<12} {'Snapshot'}")
    print("-"*100)

    results = []

    for trade in TRADES:
        hour, minute = map(int, trade["time"].split(":"))
        snaps = snaps_nq if trade["symbol"] == "NQ" else snaps_es

        snap = find_snapshot(snaps, hour, minute, trade["price"])

        if snap:
            pressure = snap.get('pressure_strength', 0)
            mid = snap.get('mid', 0)
            status = f"✅ mid={mid:.2f}"
        else:
            pressure = -1  # Non trouvé
            status = "❌ Non trouvé"

        pnl_str = f"${trade['pnl']:+.2f}"
        if trade['result'] == "WIN":
            pnl_str = f"✅ {pnl_str}"
        else:
            pnl_str = f"❌ {pnl_str}"

        press_str = f"{pressure:.4f}" if pressure >= 0 else "N/A"

        print(f"{trade['time']:<8} {trade['symbol']:<4} {trade['result']:<8} {pnl_str:<12} {press_str:<12} {status}")

        if snap:
            results.append({
                'trade': trade,
                'pressure': pressure
            })

    if not results:
        print("\n❌ Aucune donnée trouvée!")
        return

    # Analyse des seuils
    pnl_total = sum(r['trade']['pnl'] for r in results)

    print("\n" + "="*100)
    print("📊 ANALYSE DES SEUILS")
    print("="*100)

    print(f"\n{'Seuil':<10} {'Trades':<8} {'Wins':<6} {'Loss':<6} {'P&L':<12} {'Évité':<10} {'Manqué':<10} {'Δ P&L'}")
    print("-"*90)

    # Sans filtre
    wins = sum(1 for r in results if r['trade']['result'] == "WIN")
    losses = sum(1 for r in results if r['trade']['result'] == "LOSS")
    print(f"{'Aucun':<10} {len(results):<8} {wins:<6} {losses:<6} ${pnl_total:+.2f}{'':4} $0{'':8} $0{'':8} $0")

    for th in [0.02, 0.03, 0.04, 0.05, 0.10, 0.15, 0.20]:
        accepted = [r for r in results if r['pressure'] >= th]
        rejected = [r for r in results if r['pressure'] < th]

        pnl_acc = sum(r['trade']['pnl'] for r in accepted)
        wins_acc = sum(1 for r in accepted if r['trade']['result'] == "WIN")
        loss_acc = sum(1 for r in accepted if r['trade']['result'] == "LOSS")

        evite = sum(abs(r['trade']['pnl']) for r in rejected if r['trade']['result'] == "LOSS")
        manque = sum(r['trade']['pnl'] for r in rejected if r['trade']['result'] == "WIN")

        delta = pnl_acc + evite - pnl_total
        delta_str = f"${delta:+.2f}"
        if delta > 0:
            delta_str = f"✅ {delta_str}"
        elif delta < 0:
            delta_str = f"❌ {delta_str}"

        print(f"{th:<10.2f} {len(accepted):<8} {wins_acc:<6} {loss_acc:<6} ${pnl_acc:+.2f}{'':4} ${evite:.0f}{'':6} ${manque:.0f}{'':6} {delta_str}")

    # Détail pour seuil optimal
    print("\n" + "="*100)
    print("📋 DÉTAIL PAR TRADE (seuil 0.03)")
    print("="*100)

    print(f"\n{'Heure':<8} {'Résultat':<8} {'Pressure':<10} {'Décision':<12} {'Impact'}")
    print("-"*70)

    th = 0.03
    for r in results:
        trade = r['trade']
        p = r['pressure']

        if p >= th:
            decision = "✅ PRENDRE"
            if trade['result'] == "WIN":
                impact = f"+${trade['pnl']:.0f} ✓"
            else:
                impact = f"-${abs(trade['pnl']):.0f} ✗"
        else:
            decision = "🚫 BLOQUER"
            if trade['result'] == "LOSS":
                impact = f"+${abs(trade['pnl']):.0f} ÉVITÉ!"
            else:
                impact = f"-${trade['pnl']:.0f} MANQUÉ!"

        print(f"{trade['time']:<8} {trade['result']:<8} {p:<10.4f} {decision:<12} {impact}")

    print("\n" + "="*100)


if __name__ == "__main__":
    main()
