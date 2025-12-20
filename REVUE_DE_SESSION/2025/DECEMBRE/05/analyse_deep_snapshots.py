"""
ANALYSE PROFONDE DES SNAPSHOTS - TRADES 05/12/2025
====================================================

Objectif: Trouver la DIFFERENCE entre les trades gagnants et perdants
qui avaient les memes conditions de marche apparentes.

TRADES A ANALYSER:
- 20:00 SHORT WIN  (+$250)
- 20:13 SHORT LOSS (-$125)  <-- Pourquoi perdant?
- 20:23 SHORT WIN  (+$250)
- 20:32 SHORT WIN  (+$120)
- 20:50 SHORT LOSS (-$127)  <-- Pourquoi perdant?
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Pour eviter les erreurs d'encodage
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")

TRADES = [
    {"time": "20:00", "price": 25727.75, "result": "WIN", "pnl": 250},
    {"time": "20:13", "price": 25727.25, "result": "LOSS", "pnl": -125},
    {"time": "20:23", "price": 25726.75, "result": "WIN", "pnl": 250},
    {"time": "20:32", "price": 25720.00, "result": "WIN", "pnl": 120},
    {"time": "20:50", "price": 25710.88, "result": "LOSS", "pnl": -127},
]

# Champs importants a analyser
KEY_FIELDS = [
    # Prix et position
    "mid", "bid", "ask", "spread", "spread_ticks",

    # Niveaux MenthorQ
    "hvl", "vwap", "call_resistance", "put_support",
    "gex_1", "gex_2", "gex_3",

    # Distances
    "d_vwap_ticks", "d_vpoc_ticks", "d_vah_ticks", "d_val_ticks",

    # Delta et Volume
    "cum_delta_session", "delta", "deltaPct",
    "volume", "bidvol", "askvol", "askPct", "bidPct",

    # Momentum et Pression
    "tick_momentum", "mia_bullish_score",
    "institutional_pressure", "smart_money_flow",
    "pressure_strength", "pressure_strength_depth",

    # DOM (Order Book)
    "level1_imbalance", "depth_imbalance", "ob_center",
    "dom_bq1", "dom_aq1",

    # Structure
    "in_value_area", "position_in_range",
    "distance_to_high_pct", "distance_to_low_pct",

    # MenthorQ specifique
    "menthorq_impact_score", "menthorq_proximity_strength",
    "confluence_strength", "confluence_proximity",

    # Next Wall
    "next_wall",

    # Battle Navale
    "battle_navale_signal_strength", "battle_navale_confidence",

    # Volatilite
    "atr", "volatility_regime", "atr_ratio",

    # Intermarkets
    "intermarkets",

    # Gamma
    "gamma_side", "gamma_wall_level",
]


def load_snapshot_at_time(hour: int, minute: int, target_price: float) -> Optional[Dict]:
    """Charge le snapshot le plus proche du prix cible"""

    target_hour_utc = hour - 1
    target_ts = 1764892800 + (target_hour_utc * 3600) + (minute * 60)
    target_ts_start_ms = (target_ts - 180) * 1000  # -3 min
    target_ts_end_ms = (target_ts + 180) * 1000    # +3 min

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

    # Trouver le plus proche du prix
    closest = min(snapshots, key=lambda s: abs(s.get('mid', 0) - target_price))
    return closest


def format_value(v):
    """Formate une valeur pour l'affichage"""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, dict):
        return str(v)[:60] + "..." if len(str(v)) > 60 else str(v)
    return str(v)


def compare_snapshots(win_snaps: List[Dict], loss_snaps: List[Dict]):
    """Compare les snapshots gagnants vs perdants"""

    print("\n" + "="*100)
    print("COMPARAISON DETAILLEE: WINS vs LOSSES")
    print("="*100)

    # Calculer moyennes pour chaque groupe
    win_avgs = {}
    loss_avgs = {}

    for field in KEY_FIELDS:
        if field in ["next_wall", "intermarkets"]:
            continue  # Skip dict fields for averaging

        win_values = [s.get(field) for s in win_snaps if s.get(field) is not None and isinstance(s.get(field), (int, float))]
        loss_values = [s.get(field) for s in loss_snaps if s.get(field) is not None and isinstance(s.get(field), (int, float))]

        if win_values:
            win_avgs[field] = sum(win_values) / len(win_values)
        if loss_values:
            loss_avgs[field] = sum(loss_values) / len(loss_values)

    print("\n{:<35} {:>15} {:>15} {:>15}".format("CHAMP", "WINS (moy)", "LOSSES (moy)", "DIFFERENCE"))
    print("-"*100)

    differences = []

    for field in KEY_FIELDS:
        if field in ["next_wall", "intermarkets"]:
            continue

        win_val = win_avgs.get(field)
        loss_val = loss_avgs.get(field)

        if win_val is not None and loss_val is not None:
            diff = loss_val - win_val
            diff_pct = (diff / abs(win_val) * 100) if win_val != 0 else 0

            # Marquer les differences significatives
            marker = ""
            if abs(diff_pct) > 20:
                marker = " <-- SIGNIFICATIF!"
                differences.append((field, win_val, loss_val, diff, diff_pct))

            print("{:<35} {:>15.4f} {:>15.4f} {:>+15.4f}{}".format(
                field, win_val, loss_val, diff, marker
            ))

    return differences


def analyze_next_wall(snap: Dict, label: str):
    """Analyse le next_wall"""
    nw = snap.get('next_wall', {})
    if nw:
        print(f"\n   NEXT WALL ({label}):")
        print(f"      Price: {nw.get('price', 'N/A')}")
        print(f"      Side: {nw.get('side', 'N/A')}")
        print(f"      Distance: {nw.get('dist_ticks', 'N/A')}t")
        print(f"      Strength: {nw.get('strength', 'N/A')}")


def analyze_single_trade(trade: Dict, snap: Dict):
    """Analyse complete d'un trade"""

    print(f"\n{'='*100}")
    print(f"TRADE {trade['time']} - {trade['result']} ({trade['pnl']:+}$)")
    print(f"{'='*100}")

    if not snap:
        print("   [ERREUR] Snapshot non trouve")
        return

    mid = snap.get('mid', 0)

    # Section 1: Prix et Position
    print("\n[1] PRIX ET POSITION")
    print(f"   Mid: {mid:.2f}")
    print(f"   Bid: {snap.get('best_bid', snap.get('bid', 'N/A'))}")
    print(f"   Ask: {snap.get('best_ask', snap.get('ask', 'N/A'))}")
    print(f"   Spread: {snap.get('spread_ticks', 'N/A')} ticks")

    # Section 2: Niveaux MenthorQ
    print("\n[2] NIVEAUX MENTHORQ")
    hvl = snap.get('hvl', 0)
    vwap = snap.get('vwap', 0)
    print(f"   HVL: {hvl:.2f} (distance: {(mid-hvl)/0.25:+.0f}t)")
    print(f"   VWAP: {vwap:.2f} (distance: {(mid-vwap)/0.25:+.0f}t)")
    print(f"   Call Resistance: {snap.get('call_resistance', 'N/A')}")
    print(f"   Put Support: {snap.get('put_support', 'N/A')}")
    print(f"   GEX 1-3: {snap.get('gex_1', 'N/A')}, {snap.get('gex_2', 'N/A')}, {snap.get('gex_3', 'N/A')}")

    # Section 3: Delta et Volume
    print("\n[3] DELTA ET VOLUME")
    print(f"   Cum Delta Session: {snap.get('cum_delta_session', 'N/A')}")
    print(f"   Delta Instantane: {snap.get('delta', 'N/A')}")
    print(f"   Delta %: {snap.get('deltaPct', 'N/A')}")
    print(f"   Volume: {snap.get('volume', 'N/A')}")
    print(f"   Bid Vol: {snap.get('bidvol', 'N/A')} | Ask Vol: {snap.get('askvol', 'N/A')}")
    print(f"   Bid %: {snap.get('bidPct', 'N/A'):.2%} | Ask %: {snap.get('askPct', 'N/A'):.2%}")

    # Section 4: Momentum et Pression
    print("\n[4] MOMENTUM ET PRESSION")
    print(f"   Tick Momentum: {snap.get('tick_momentum', 'N/A')}")
    print(f"   MIA Bullish Score: {snap.get('mia_bullish_score', 'N/A')}")
    print(f"   Institutional Pressure: {snap.get('institutional_pressure', 'N/A')}")
    print(f"   Smart Money Flow: {snap.get('smart_money_flow', 'N/A')}")
    print(f"   Pressure Strength: {snap.get('pressure_strength', 'N/A')}")

    # Section 5: Order Book
    print("\n[5] ORDER BOOK (DOM)")
    print(f"   Level 1 Imbalance: {snap.get('level1_imbalance', 'N/A')}")
    print(f"   Depth Imbalance: {snap.get('depth_imbalance', 'N/A')}")
    print(f"   OB Center: {snap.get('ob_center', 'N/A')}")
    print(f"   DOM BQ1/AQ1: {snap.get('dom_bq1', 'N/A')}/{snap.get('dom_aq1', 'N/A')}")

    # Section 6: Position dans le Range
    print("\n[6] POSITION DANS LE RANGE")
    print(f"   In Value Area: {snap.get('in_value_area', 'N/A')}")
    print(f"   Position in Range: {snap.get('position_in_range', 'N/A'):.1f}%")
    print(f"   Distance to High: {snap.get('distance_to_high_pct', 'N/A'):.2%}")
    print(f"   Distance to Low: {snap.get('distance_to_low_pct', 'N/A'):.2%}")

    # Section 7: MenthorQ Specifique
    print("\n[7] MENTHORQ SCORING")
    print(f"   Impact Score: {snap.get('menthorq_impact_score', 'N/A')}")
    print(f"   Proximity Strength: {snap.get('menthorq_proximity_strength', 'N/A')}")
    print(f"   Confluence Strength: {snap.get('confluence_strength', 'N/A')}")
    print(f"   Confluence Proximity: {snap.get('confluence_proximity', 'N/A')}")

    # Section 8: Next Wall
    analyze_next_wall(snap, trade['time'])

    # Section 9: Battle Navale
    print("\n[8] BATTLE NAVALE")
    print(f"   Signal Strength: {snap.get('battle_navale_signal_strength', 'N/A')}")
    print(f"   Confidence: {snap.get('battle_navale_confidence', 'N/A')}")

    # Section 10: Volatilite
    print("\n[9] VOLATILITE")
    print(f"   ATR: {snap.get('atr', 'N/A')}")
    print(f"   Volatility Regime: {snap.get('volatility_regime', 'N/A')}")
    print(f"   ATR Ratio: {snap.get('atr_ratio', 'N/A')}")

    # Section 11: Gamma
    print("\n[10] GAMMA")
    print(f"   Gamma Side: {snap.get('gamma_side', 'N/A')}")
    print(f"   Gamma Wall Level: {snap.get('gamma_wall_level', 'N/A')}")

    # Section 12: Intermarkets
    inter = snap.get('intermarkets', {})
    if inter:
        print("\n[11] INTERMARKETS")
        print(f"   ES-NQ Lead: {inter.get('es_nq_lead_ms_120s', 'N/A')}")
        print(f"   NQ-ES RS Z: {inter.get('nq_es_rs_z_120s', 'N/A')}")
        print(f"   Divergence Flag: {inter.get('divergence_flag', 'N/A')}")

    return snap


def main():
    print("="*100)
    print("ANALYSE PROFONDE DES SNAPSHOTS - TRADES 05/12/2025")
    print("="*100)
    print("\nObjectif: Trouver ce qui DIFFERENCIE les trades gagnants des perdants")

    win_snapshots = []
    loss_snapshots = []
    all_snapshots = []

    for trade in TRADES:
        hour, minute = map(int, trade["time"].split(":"))
        snap = load_snapshot_at_time(hour, minute, trade["price"])

        if snap:
            all_snapshots.append((trade, snap))
            if trade["result"] == "WIN":
                win_snapshots.append(snap)
            else:
                loss_snapshots.append(snap)

            analyze_single_trade(trade, snap)

    # Comparaison globale
    if win_snapshots and loss_snapshots:
        differences = compare_snapshots(win_snapshots, loss_snapshots)

        print("\n" + "="*100)
        print("DIFFERENCES SIGNIFICATIVES DETECTEES (>20%)")
        print("="*100)

        if differences:
            for field, win_val, loss_val, diff, diff_pct in sorted(differences, key=lambda x: abs(x[4]), reverse=True):
                print(f"\n   {field}:")
                print(f"      WINS:  {win_val:.4f}")
                print(f"      LOSSES: {loss_val:.4f}")
                print(f"      Diff:   {diff:+.4f} ({diff_pct:+.1f}%)")
        else:
            print("\n   Aucune difference significative detectee!")
            print("   Les trades gagnants et perdants avaient des conditions TRES similaires.")
            print("   Le probleme est probablement lie au TIMING ou aux STOP LOSS.")

    # Conclusion
    print("\n" + "="*100)
    print("CONCLUSIONS")
    print("="*100)

    # Analyser les patterns
    print("\n[PATTERN ANALYSIS]")

    for trade, snap in all_snapshots:
        tick_mom = snap.get('tick_momentum', 0)
        mia_score = snap.get('mia_bullish_score', 0)
        delta = snap.get('cum_delta_session', 0)
        l1_imb = snap.get('level1_imbalance', 0)

        # Score composite
        bearish_score = 0
        if tick_mom < 0: bearish_score += 1
        if mia_score < 0: bearish_score += 1
        if delta < 0: bearish_score += 1
        if l1_imb < 0: bearish_score += 1

        print(f"\n   {trade['time']} ({trade['result']}): Bearish Score = {bearish_score}/4")
        print(f"      tick_mom={tick_mom:.2f}, mia={mia_score:.2f}, delta={delta:.0f}, l1_imb={l1_imb:.2f}")


if __name__ == "__main__":
    main()

