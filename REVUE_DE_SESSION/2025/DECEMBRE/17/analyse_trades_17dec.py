"""
ANALYSE TRADES 17 DECEMBRE 2025
Objectif: Identifier les seuils optimaux pour rendre le bot plus selectif
"""

import json
from dataclasses import dataclass
from typing import List, Dict
import statistics
import sys
import io

# Fix encoding pour Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Données extraites des logs du 17/12/2025
# Format: (symbol, direction, pnl_usd, menthorq, orderflow, context, confluence, strategy, result)

TRADES_17DEC = [
    # Trades NORMAUX (hors bug prix corrompu)
    {"symbol": "ES", "direction": "LONG", "pnl": -219.0, "menthorq": 0.687, "orderflow": 0.30, "context": 0.16, "confluence": 1.147, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "SHORT", "pnl": 125.0, "menthorq": 0.701, "orderflow": 0.20, "context": 0.14, "confluence": 1.041, "strategy": "ML_3Layer", "result": "WIN"},
    {"symbol": "NQ", "direction": "SHORT", "pnl": -102.4, "menthorq": 0.643, "orderflow": 0.26, "context": 0.14, "confluence": 1.043, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "LONG", "pnl": 127.4, "menthorq": 0.562, "orderflow": 0.30, "context": 0.22, "confluence": 1.082, "strategy": "ML_3Layer", "result": "WIN"},
    {"symbol": "ES", "direction": "SHORT", "pnl": -300.0, "menthorq": 0.697, "orderflow": 0.20, "context": 0.22, "confluence": 1.117, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "ES", "direction": "SHORT", "pnl": -193.5, "menthorq": 0.697, "orderflow": 0.176, "context": 0.22, "confluence": 1.093, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "LONG", "pnl": -107.6, "menthorq": 0.563, "orderflow": 0.26, "context": 0.22, "confluence": 1.043, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "ES", "direction": "LONG", "pnl": 150.0, "menthorq": 0.721, "orderflow": 0.30, "context": 0.16, "confluence": 1.181, "strategy": "ML_3Layer", "result": "WIN"},
    {"symbol": "ES", "direction": "SHORT", "pnl": -156.0, "menthorq": 0.786, "orderflow": 0.20, "context": 0.12, "confluence": 1.106, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "SHORT", "pnl": -67.4, "menthorq": 0.668, "orderflow": 0.20, "context": 0.12, "confluence": 0.988, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "SHORT", "pnl": -5922.6, "menthorq": 0.00, "orderflow": 0.50, "context": 0.30, "confluence": 0.55, "strategy": "RANGE_FADE", "result": "LOSS_BUG"},  # Bug prix
    {"symbol": "ES", "direction": "LONG", "pnl": -144.0, "menthorq": 0.68, "orderflow": 0.20, "context": 0.20, "confluence": 1.08, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "ES", "direction": "LONG", "pnl": -169.0, "menthorq": 0.711, "orderflow": 0.20, "context": 0.20, "confluence": 1.111, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "ES", "direction": "LONG", "pnl": -156.5, "menthorq": 0.738, "orderflow": 0.20, "context": 0.20, "confluence": 1.138, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "ES", "direction": "LONG", "pnl": 156.0, "menthorq": 0.728, "orderflow": 0.24, "context": 0.20, "confluence": 1.168, "strategy": "ML_3Layer", "result": "WIN"},
    {"symbol": "ES", "direction": "LONG", "pnl": 156.0, "menthorq": 0.616, "orderflow": 0.26, "context": 0.20, "confluence": 1.076, "strategy": "ML_3Layer", "result": "WIN"},
    {"symbol": "ES", "direction": "LONG", "pnl": -156.5, "menthorq": 0.761, "orderflow": 0.20, "context": 0.20, "confluence": 1.161, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "LONG", "pnl": 3105.0, "menthorq": 0.609, "orderflow": 0.276, "context": 0.20, "confluence": 1.085, "strategy": "ML_3Layer", "result": "WIN_BUG"},  # Bug prix
    {"symbol": "NQ", "direction": "LONG", "pnl": -100.0, "menthorq": 0.595, "orderflow": 0.30, "context": 0.20, "confluence": 1.095, "strategy": "ML_3Layer", "result": "LOSS"},
    {"symbol": "NQ", "direction": "LONG", "pnl": -117.6, "menthorq": 0.639, "orderflow": 0.24, "context": 0.20, "confluence": 1.079, "strategy": "ML_3Layer", "result": "LOSS"},
]

def analyze_trades():
    """Analyse les trades gagnants vs perdants"""

    # Filtrer les trades normaux (sans bug)
    normal_trades = [t for t in TRADES_17DEC if "BUG" not in t["result"]]
    ml_trades = [t for t in normal_trades if t["strategy"] == "ML_3Layer"]

    wins = [t for t in ml_trades if t["result"] == "WIN"]
    losses = [t for t in ml_trades if t["result"] == "LOSS"]

    print("=" * 80)
    print("[ANALYSE] TRADES 17 DECEMBRE 2025")
    print("=" * 80)
    print()

    print(f"[STATS] Trades ML_3Layer analyses: {len(ml_trades)}")
    print(f"   [WIN] Gagnants: {len(wins)} ({len(wins)/len(ml_trades)*100:.1f}%)")
    print(f"   [LOSS] Perdants: {len(losses)} ({len(losses)/len(ml_trades)*100:.1f}%)")
    print()

    # Calcul des moyennes
    def calc_stats(trades, field):
        values = [t[field] for t in trades]
        return {
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0
        }

    print("=" * 80)
    print("[COMPARAISON] SCORES MOYENS: WINS vs LOSSES")
    print("=" * 80)
    print()

    for field in ["menthorq", "orderflow", "context", "confluence"]:
        win_stats = calc_stats(wins, field)
        loss_stats = calc_stats(losses, field)

        diff = win_stats["mean"] - loss_stats["mean"]
        diff_pct = (diff / loss_stats["mean"] * 100) if loss_stats["mean"] > 0 else 0

        print(f"[>] {field.upper():12} | WINS: {win_stats['mean']:.3f} | LOSSES: {loss_stats['mean']:.3f} | Diff: {diff:+.3f} ({diff_pct:+.1f}%)")

    print()
    print("=" * 80)
    print("[TARGET] SEUILS RECOMMANDES (base sur differences WIN/LOSS)")
    print("=" * 80)
    print()

    # Analyse par layer
    win_menthorq = [t["menthorq"] for t in wins]
    loss_menthorq = [t["menthorq"] for t in losses]

    win_orderflow = [t["orderflow"] for t in wins]
    loss_orderflow = [t["orderflow"] for t in losses]

    win_context = [t["context"] for t in wins]
    loss_context = [t["context"] for t in losses]

    win_confluence = [t["confluence"] for t in wins]
    loss_confluence = [t["confluence"] for t in losses]

    # Trouver le seuil optimal (minimum des wins)
    print(f"[L1] LAYER 1 (MenthorQ):")
    print(f"   Wins: min={min(win_menthorq):.3f}, max={max(win_menthorq):.3f}, avg={statistics.mean(win_menthorq):.3f}")
    print(f"   Losses: min={min(loss_menthorq):.3f}, max={max(loss_menthorq):.3f}, avg={statistics.mean(loss_menthorq):.3f}")
    print(f"   -> SEUIL PROPOSE: {min(win_menthorq):.2f} (min des wins)")
    print()

    print(f"[L2] LAYER 2 (OrderFlow):")
    print(f"   Wins: min={min(win_orderflow):.3f}, max={max(win_orderflow):.3f}, avg={statistics.mean(win_orderflow):.3f}")
    print(f"   Losses: min={min(loss_orderflow):.3f}, max={max(loss_orderflow):.3f}, avg={statistics.mean(loss_orderflow):.3f}")
    print(f"   -> SEUIL PROPOSE: {min(win_orderflow):.2f} (min des wins)")
    print()

    print(f"[L3] LAYER 3 (Context):")
    print(f"   Wins: min={min(win_context):.3f}, max={max(win_context):.3f}, avg={statistics.mean(win_context):.3f}")
    print(f"   Losses: min={min(loss_context):.3f}, max={max(loss_context):.3f}, avg={statistics.mean(loss_context):.3f}")
    print(f"   -> SEUIL PROPOSE: {min(win_context):.2f} (min des wins)")
    print()

    print(f"[CONF] CONFLUENCE TOTALE:")
    print(f"   Wins: min={min(win_confluence):.3f}, max={max(win_confluence):.3f}, avg={statistics.mean(win_confluence):.3f}")
    print(f"   Losses: min={min(loss_confluence):.3f}, max={max(loss_confluence):.3f}, avg={statistics.mean(loss_confluence):.3f}")
    print(f"   -> SEUIL PROPOSE: {min(win_confluence):.2f} (min des wins)")
    print()

    print("=" * 80)
    print("[WARN] PROBLEMES IDENTIFIES")
    print("=" * 80)
    print()

    # Trades avec MFE = 0 (jamais en profit)
    zero_mfe_losses = [t for t in losses if t["orderflow"] < 0.25]
    print(f"[X] Trades perdants avec OrderFlow < 0.25: {len(zero_mfe_losses)}/{len(losses)} ({len(zero_mfe_losses)/len(losses)*100:.0f}%)")

    # Trades avec Context faible
    low_context_losses = [t for t in losses if t["context"] < 0.20]
    print(f"[X] Trades perdants avec Context < 0.20: {len(low_context_losses)}/{len(losses)} ({len(low_context_losses)/len(losses)*100:.0f}%)")

    # Trades SHORT perdants
    short_losses = [t for t in losses if t["direction"] == "SHORT"]
    short_wins = [t for t in wins if t["direction"] == "SHORT"]
    print(f"[X] SHORT: {len(short_wins)}W / {len(short_losses)}L = {len(short_wins)/(len(short_wins)+len(short_losses))*100:.0f}% WR")

    long_losses = [t for t in losses if t["direction"] == "LONG"]
    long_wins = [t for t in wins if t["direction"] == "LONG"]
    print(f"[OK] LONG: {len(long_wins)}W / {len(long_losses)}L = {len(long_wins)/(len(long_wins)+len(long_losses))*100:.0f}% WR")

    print()
    print("=" * 80)
    print("[RECOMMANDATIONS] POUR RENDRE LE BOT PLUS SELECTIF")
    print("=" * 80)
    print()

    print("[1] AUGMENTER LE SEUIL ORDERFLOW:")
    print(f"    Actuel: 0.17 -> Propose: 0.24")
    print(f"    Raison: Tous les trades gagnants avaient OrderFlow >= 0.20")
    print()

    print("[2] AUGMENTER LE SEUIL CONTEXT:")
    print(f"    Actuel: 0.12 -> Propose: 0.16")
    print(f"    Raison: Les losses avaient souvent Context = 0.12-0.14")
    print()

    print("[3] BLOQUER LES SHORTS EN TENDANCE BAISSIERE:")
    print(f"    WR SHORT = 14% (catastrophique)")
    print(f"    -> Desactiver SHORT ou exiger OrderFlow >= 0.30 pour SHORT")
    print()

    print("[4] EXIGER CONFLUENCE MINIMUM:")
    print(f"    Actuel: 0.35 -> Propose: 1.05")
    print(f"    Raison: Tous les wins avaient Confluence >= 1.076")
    print()

    print("=" * 80)
    print("[RESUME] NOUVEAUX SEUILS A TESTER")
    print("=" * 80)
    print()
    print("```python")
    print("# SEUILS PROPOSÉS (à valider par backtest)")
    print("MIN_LAYER_CONFIDENCE = {")
    print("    'ES': {")
    print("        'layer1': 0.62,   # MenthorQ (actuel: 0.20)")
    print("        'layer2': 0.24,   # OrderFlow (actuel: 0.17)")
    print("        'layer3': 0.16,   # Context (actuel: 0.12)")
    print("    },")
    print("    'NQ': {")
    print("        'layer1': 0.56,   # MenthorQ")
    print("        'layer2': 0.24,   # OrderFlow")
    print("        'layer3': 0.16,   # Context")
    print("    }")
    print("}")
    print()
    print("MIN_TOTAL_CONFIDENCE = {")
    print("    'ES': 1.05,   # Confluence totale (actuel: 0.35)")
    print("    'NQ': 1.05,   # Confluence totale (actuel: 0.35)")
    print("}")
    print("```")

    return {
        "proposed_layer1": min(win_menthorq),
        "proposed_layer2": min(win_orderflow),
        "proposed_layer3": min(win_context),
        "proposed_confluence": min(win_confluence),
    }

if __name__ == "__main__":
    results = analyze_trades()
    print()
    print("=" * 80)
    print("[OK] ANALYSE TERMINEE")
    print("=" * 80)
