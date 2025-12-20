"""
TEST PRESSURE_STRENGTH SUR TRADES RÉELS 05/12/2025
===================================================

Vérifie l'impact du filtre sur les 6 trades réels de la session.
Teste les seuils: 0.10, 0.15, 0.20 (recommandation du backtest)
"""

import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Chemins vers les données
DATA_NQ = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")
DATA_ES = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_3\ML_READY\ml_ESZ25_FUT_CME_3.jsonl")

BASE_TS = 1733356800  # 05/12/2025 00:00 UTC (corrigé)

# Trades réels du 05/12/2025 (de la revue de session)
TRADES_05DEC = [
    # London session
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


def load_snapshot(symbol: str, hour: int, minute: int, target_price: float):
    """Charge le snapshot le plus proche"""
    data_path = DATA_NQ if symbol == "NQ" else DATA_ES

    if not data_path.exists():
        return None

    # Convertir heure Paris -> UTC (Paris = UTC+1)
    target_hour_utc = hour - 1
    target_ts = BASE_TS + (target_hour_utc * 3600) + (minute * 60)
    target_ts_start_ms = (target_ts - 300) * 1000  # ±5 min
    target_ts_end_ms = (target_ts + 300) * 1000

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

    # Trouver le snapshot le plus proche du prix
    return min(snapshots, key=lambda s: abs(s.get('mid', 0) - target_price))


def test_threshold(threshold: float, results: list):
    """Teste un seuil donné"""
    trades_avec = 0
    pnl_avec = 0
    pertes_evitees = 0
    gains_manques = 0

    for r in results:
        if r['pressure'] >= threshold:
            trades_avec += 1
            pnl_avec += r['trade']['pnl']
        else:
            if r['trade']['result'] == "LOSS":
                pertes_evitees += abs(r['trade']['pnl'])
            else:
                gains_manques += r['trade']['pnl']

    return {
        'trades': trades_avec,
        'pnl': pnl_avec,
        'pertes_evitees': pertes_evitees,
        'gains_manques': gains_manques,
        'impact_net': pnl_avec + pertes_evitees - gains_manques
    }


def main():
    print("="*100)
    print("🎯 TEST PRESSURE_STRENGTH SUR TRADES RÉELS - 05/12/2025")
    print("="*100)
    print("\n📊 Résultat réel de la session: +$627.60 (8 trades)")
    print("🎯 Objectif: Vérifier si pressure_strength améliore les résultats\n")

    # Collecter les données
    results = []

    print("-"*100)
    print(f"{'Heure':<8} {'Symbol':<6} {'Dir':<6} {'Résultat':<8} {'P&L':<12} {'Pressure':<12} {'Snapshot'}")
    print("-"*100)

    for trade in TRADES_05DEC:
        hour, minute = map(int, trade["time"].split(":"))

        snap = load_snapshot(trade["symbol"], hour, minute, trade["price"])

        if snap:
            pressure = snap.get('pressure_strength', 0)
            mid = snap.get('mid', 0)
            status = "✅"
        else:
            pressure = 0
            mid = 0
            status = "❌ Non trouvé"

        pnl_str = f"${trade['pnl']:+.2f}"
        if trade['result'] == "WIN":
            pnl_str = f"✅ {pnl_str}"
        else:
            pnl_str = f"❌ {pnl_str}"

        print(f"{trade['time']:<8} {trade['symbol']:<6} {trade['direction']:<6} {trade['result']:<8} {pnl_str:<12} {pressure:<12.4f} {status}")

        if snap:
            results.append({
                'trade': trade,
                'pressure': pressure,
                'snap': snap
            })

    if not results:
        print("\n❌ Aucune donnée trouvée!")
        return

    # Calculer P&L sans filtre
    pnl_sans_filtre = sum(r['trade']['pnl'] for r in results)
    trades_sans_filtre = len(results)

    print("\n" + "="*100)
    print("📊 COMPARAISON DES SEUILS")
    print("="*100)

    print(f"\n{'Seuil':<10} {'Trades':<8} {'P&L':<12} {'Pertes Évitées':<16} {'Gains Manqués':<16} {'Impact Net':<15}")
    print("-"*90)

    # Sans filtre
    print(f"{'Aucun':<10} {trades_sans_filtre:<8} ${pnl_sans_filtre:+.2f}{'':7} $0.00{'':13} $0.00{'':13} $0.00")

    # Tester différents seuils
    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    best_threshold = None
    best_impact = float('-inf')

    for th in thresholds:
        r = test_threshold(th, results)

        pnl_str = f"${r['pnl']:+.2f}"
        evite_str = f"${r['pertes_evitees']:+.2f}"
        manque_str = f"${r['gains_manques']:+.2f}"

        # Impact = P&L avec filtre + pertes évitées
        impact = r['pnl'] + r['pertes_evitees']
        impact_str = f"${impact - pnl_sans_filtre:+.2f}"

        if impact > best_impact:
            best_impact = impact
            best_threshold = th

        status = "🏆" if th == 0.20 else ""  # Recommandation du backtest
        print(f"{th:<10.2f} {r['trades']:<8} {pnl_str:<12} {evite_str:<16} {manque_str:<16} {impact_str:<15} {status}")

    # Résumé
    print("\n" + "="*100)
    print("🏆 RECOMMANDATION")
    print("="*100)

    # Détail pour seuil 0.20
    r020 = test_threshold(0.20, results)

    print(f"\n📈 SEUIL RECOMMANDÉ: pressure_strength >= 0.20")
    print(f"\n   SANS le filtre:")
    print(f"      Trades: {trades_sans_filtre}")
    print(f"      P&L: ${pnl_sans_filtre:+.2f}")

    print(f"\n   AVEC le filtre (>= 0.20):")
    print(f"      Trades: {r020['trades']}")
    print(f"      P&L pris: ${r020['pnl']:+.2f}")
    print(f"      Pertes évitées: ${r020['pertes_evitees']:+.2f}")
    print(f"      Gains manqués: ${r020['gains_manques']:+.2f}")

    impact_020 = r020['pnl'] + r020['pertes_evitees'] - pnl_sans_filtre

    if impact_020 > 0:
        print(f"\n   ✅ IMPACT POSITIF: +${impact_020:.2f}")
    elif impact_020 < 0:
        print(f"\n   ⚠️ IMPACT NÉGATIF: ${impact_020:.2f}")
    else:
        print(f"\n   ➖ IMPACT NEUTRE")

    # Afficher détail des décisions
    print("\n" + "="*100)
    print("📋 DÉTAIL DES DÉCISIONS (seuil 0.20)")
    print("="*100)

    print(f"\n{'Heure':<8} {'Résultat':<8} {'Pressure':<10} {'Décision':<12} {'Impact'}")
    print("-"*70)

    for r in results:
        trade = r['trade']
        pressure = r['pressure']

        if pressure >= 0.20:
            decision = "✅ PRENDRE"
            if trade['result'] == "WIN":
                impact = f"+${trade['pnl']:.0f} (GAGNÉ)"
            else:
                impact = f"-${abs(trade['pnl']):.0f} (PERDU)"
        else:
            decision = "❌ BLOQUER"
            if trade['result'] == "LOSS":
                impact = f"+${abs(trade['pnl']):.0f} (ÉVITÉ!)"
            else:
                impact = f"-${trade['pnl']:.0f} (MANQUÉ!)"

        print(f"{trade['time']:<8} {trade['result']:<8} {pressure:<10.4f} {decision:<12} {impact}")

    print("\n" + "="*100)


if __name__ == "__main__":
    main()
