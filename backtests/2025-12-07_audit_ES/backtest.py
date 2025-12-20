"""
🔍 AUDIT APPROFONDI ES - POURQUOI LES PERTES ?
===============================================

ES est un indice propre qui respecte les structures.
L'options flow est pertinent.
MAIS les trades sont perdants.

Objectif: Identifier le problème et rendre ES rentable.

Date: 07/12/2025
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKTESTS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKTESTS_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from config.backtest_config import (
    MIN_TOTAL_CONFIDENCE, MIN_LAYER_CONFIDENCE,
    MAX_DISTANCE_TO_LEVEL, TP_SL_CONFIG, TICK_VALUES, TICK_SIZES,
    COOLDOWN_MS, MAX_TRADE_DURATION_MS, MAX_SNAPSHOTS_LOOKAHEAD,
    MIN_PRESSURE_BY_SESSION,
    MLScores, get_session, get_distance_to_level, load_snapshots
)

# ============================================================================
# CONFIGURATION
# ============================================================================

DATE_RANGE = ["20251202", "20251203", "20251204", "20251205"]
DATA_MONTH = "DECEMBRE"
DATA_YEAR = 2025
SYMBOL = "ES"

# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class TradeAnalysis:
    timestamp: int
    direction: str
    entry_price: float
    exit_price: float
    result: str  # WIN, LOSS, BE
    pnl_ticks: float
    pnl_usd: float

    # Contexte au moment du trade
    session: str
    delta: float
    pressure: float
    distance_to_level: float
    nearest_level: str
    layer1: float
    layer2: float
    layer3: float
    total_conf: float

    # Analyse post-trade
    max_favorable: float = 0  # MFE en ticks
    max_adverse: float = 0    # MAE en ticks
    time_to_exit_ms: int = 0
    exit_reason: str = ""

# ============================================================================
# FONCTIONS
# ============================================================================

def calculate_ml_scores(snap: Dict) -> MLScores:
    l1 = snap.get('layer1_score') or snap.get('menthorq_score', 0)
    l2 = snap.get('layer2_score') or snap.get('orderflow_score', 0)
    l3 = snap.get('layer3_score') or snap.get('context_score', 0)

    if l1 == 0 and l2 == 0 and l3 == 0:
        mid = snap.get('mid', 0)
        dist, _ = get_distance_to_level(snap, mid, SYMBOL)
        l1 = max(0, min(1, 1 - dist / 100)) if dist < 9999 else 0.2
        delta = abs(snap.get('delta', 0))
        pressure = snap.get('pressure_strength', 0)
        l2 = max(0, min(1, delta / 500 + pressure * 0.5))
        l3 = 0.3

    total = l1 * 0.5 + l2 * 0.3 + l3 * 0.2
    return MLScores(layer1=l1, layer2=l2, layer3=l3, total=total)


def validate_signal(snap: Dict) -> Tuple[bool, str, dict]:
    """Valide un signal et retourne les détails"""
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)
    pressure = snap.get('pressure_strength', 0)

    if not ts or not mid:
        return False, "no_price", {}

    in_session, session = get_session(ts)
    if not in_session:
        return False, "out_of_session", {}

    if delta == 0:
        return False, "delta_zero", {}

    direction = "LONG" if delta > 0 else "SHORT"

    ml_scores = calculate_ml_scores(snap)
    ml_ok, ml_reason = ml_scores.meets_thresholds(SYMBOL)
    if not ml_ok:
        return False, f"ml_{ml_reason}", {}

    distance, level_name = get_distance_to_level(snap, mid, SYMBOL)
    max_dist = MAX_DISTANCE_TO_LEVEL.get(SYMBOL, 15)
    if distance > max_dist:
        return False, f"distance_{distance:.0f}t", {}

    # Pressure filter
    min_pressure = MIN_PRESSURE_BY_SESSION.get(session, 0.10)
    if pressure < min_pressure:
        return False, f"pressure_{pressure:.3f}", {}

    context = {
        'direction': direction,
        'session': session,
        'delta': delta,
        'pressure': pressure,
        'distance': distance,
        'level_name': level_name,
        'layer1': ml_scores.layer1,
        'layer2': ml_scores.layer2,
        'layer3': ml_scores.layer3,
        'total_conf': ml_scores.total,
    }

    return True, "OK", context


def simulate_trade_detailed(entry_snap: Dict, subsequent: List[Dict], direction: str, context: dict) -> TradeAnalysis:
    """Simule un trade avec analyse détaillée MFE/MAE"""
    cfg = TP_SL_CONFIG.get(SYMBOL)
    tv = TICK_VALUES.get(SYMBOL)
    ts = TICK_SIZES.get(SYMBOL)
    tp_ticks = cfg['tp_ticks']
    sl_ticks = cfg['sl_ticks']

    entry_price = entry_snap.get('mid', 0)
    entry_time = entry_snap.get('t_ms', 0)

    if direction == "LONG":
        tp = entry_price + tp_ticks * ts
        sl = entry_price - sl_ticks * ts
    else:
        tp = entry_price - tp_ticks * ts
        sl = entry_price + sl_ticks * ts

    mfe = 0  # Max Favorable Excursion
    mae = 0  # Max Adverse Excursion
    exit_price = entry_price
    exit_time = entry_time
    result = "BE"
    exit_reason = "TIMEOUT"

    for snap in subsequent[:MAX_SNAPSHOTS_LOOKAHEAD]:
        current_time = snap.get('t_ms', 0)
        if current_time - entry_time > MAX_TRADE_DURATION_MS:
            break

        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))
        mid = snap.get('mid', 0)

        # Calculer MFE/MAE
        if direction == "LONG":
            favorable = (high - entry_price) / ts
            adverse = (entry_price - low) / ts
        else:
            favorable = (entry_price - low) / ts
            adverse = (high - entry_price) / ts

        mfe = max(mfe, favorable)
        mae = max(mae, adverse)

        # Check TP/SL
        if direction == "LONG":
            if high >= tp:
                result = "WIN"
                exit_price = tp
                exit_time = current_time
                exit_reason = "TP_HIT"
                break
            if low <= sl:
                result = "LOSS"
                exit_price = sl
                exit_time = current_time
                exit_reason = "SL_HIT"
                break
        else:
            if low <= tp:
                result = "WIN"
                exit_price = tp
                exit_time = current_time
                exit_reason = "TP_HIT"
                break
            if high >= sl:
                result = "LOSS"
                exit_price = sl
                exit_time = current_time
                exit_reason = "SL_HIT"
                break

    pnl_ticks = tp_ticks if result == "WIN" else (-sl_ticks if result == "LOSS" else 0)
    pnl_usd = pnl_ticks * tv

    return TradeAnalysis(
        timestamp=entry_time,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        result=result,
        pnl_ticks=pnl_ticks,
        pnl_usd=pnl_usd,
        session=context['session'],
        delta=context['delta'],
        pressure=context['pressure'],
        distance_to_level=context['distance'],
        nearest_level=context['level_name'],
        layer1=context['layer1'],
        layer2=context['layer2'],
        layer3=context['layer3'],
        total_conf=context['total_conf'],
        max_favorable=mfe,
        max_adverse=mae,
        time_to_exit_ms=exit_time - entry_time,
        exit_reason=exit_reason
    )


def run_audit():
    """Exécute l'audit complet"""
    print("="*100)
    print("🔍 AUDIT APPROFONDI ES - POURQUOI LES PERTES ?")
    print("="*100)
    print(f"\n📅 Période: {DATE_RANGE[0]} → {DATE_RANGE[-1]} (4 jours)")
    print(f"📊 Symbole: {SYMBOL}")
    print(f"\n📋 Config actuelle:")
    print(f"   TP = {TP_SL_CONFIG[SYMBOL]['tp_ticks']} ticks")
    print(f"   SL = {TP_SL_CONFIG[SYMBOL]['sl_ticks']} ticks")
    print(f"   Distance max = {MAX_DISTANCE_TO_LEVEL[SYMBOL]} ticks")

    # Charger données
    print(f"\n📥 Chargement des données...")
    all_snaps = []
    for date in DATE_RANGE:
        snaps = load_snapshots(date, SYMBOL, DATA_MONTH, DATA_YEAR)
        if snaps:
            all_snaps.extend([(date, i, s) for i, s in enumerate(snaps)])

    print(f"   Total: {len(all_snaps):,} snapshots")

    # Analyser les trades
    print(f"\n🔄 Analyse des trades...")
    trades: List[TradeAnalysis] = []
    last_trade_time = 0

    for date, idx, snap in all_snaps:
        valid, reason, context = validate_signal(snap)
        if not valid:
            continue

        ts = snap.get('t_ms', 0)
        if ts - last_trade_time < COOLDOWN_MS:
            continue

        last_trade_time = ts

        # Trouver les snapshots suivants
        subsequent = [s for d, i, s in all_snaps if d == date and i > idx][:MAX_SNAPSHOTS_LOOKAHEAD]

        trade = simulate_trade_detailed(snap, subsequent, context['direction'], context)
        trades.append(trade)

    print(f"   Total trades: {len(trades)}")

    # =========================================================================
    # ANALYSE DES RÉSULTATS
    # =========================================================================

    wins = [t for t in trades if t.result == "WIN"]
    losses = [t for t in trades if t.result == "LOSS"]
    be = [t for t in trades if t.result == "BE"]

    total_pnl = sum(t.pnl_usd for t in trades)
    win_rate = len(wins) / max(len(trades), 1) * 100

    print(f"\n{'='*100}")
    print(f"📊 RÉSULTATS GLOBAUX")
    print(f"{'='*100}")
    print(f"   Trades: {len(trades)} | Wins: {len(wins)} | Losses: {len(losses)} | BE: {len(be)}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   P&L Total: ${total_pnl:+,.2f}")

    # =========================================================================
    # ANALYSE MFE/MAE (Clé du problème!)
    # =========================================================================

    print(f"\n{'='*100}")
    print(f"🔍 ANALYSE MFE/MAE (Max Favorable/Adverse Excursion)")
    print(f"{'='*100}")

    # Trades perdants qui auraient pu être gagnants
    could_have_won = [t for t in losses if t.max_favorable >= TP_SL_CONFIG[SYMBOL]['tp_ticks']]

    print(f"\n   📈 MFE moyen (tous trades): {sum(t.max_favorable for t in trades)/max(len(trades),1):.1f} ticks")
    print(f"   📉 MAE moyen (tous trades): {sum(t.max_adverse for t in trades)/max(len(trades),1):.1f} ticks")

    print(f"\n   🔥 Trades PERDANTS qui ont touché le TP avant le SL: {len(could_have_won)}/{len(losses)}")
    if could_have_won:
        print(f"      → Ces trades auraient rapporté: ${len(could_have_won) * TP_SL_CONFIG[SYMBOL]['tp_ticks'] * TICK_VALUES[SYMBOL]:+,.2f}")

    # MFE des perdants
    if losses:
        avg_mfe_losses = sum(t.max_favorable for t in losses) / len(losses)
        print(f"\n   📊 MFE moyen des PERDANTS: {avg_mfe_losses:.1f} ticks")
        print(f"      → Le prix allait en notre faveur de {avg_mfe_losses:.1f} ticks avant de se retourner")

        if avg_mfe_losses > 15:
            print(f"      ⚠️ PROBLÈME: Le MFE est élevé → On pourrait prendre des profits partiels!")

    # MAE des gagnants
    if wins:
        avg_mae_wins = sum(t.max_adverse for t in wins) / len(wins)
        print(f"\n   📊 MAE moyen des GAGNANTS: {avg_mae_wins:.1f} ticks")
        print(f"      → Drawdown moyen avant de gagner: {avg_mae_wins:.1f} ticks")

    # =========================================================================
    # ANALYSE PAR SESSION
    # =========================================================================

    print(f"\n{'='*100}")
    print(f"🕐 ANALYSE PAR SESSION")
    print(f"{'='*100}")

    by_session = defaultdict(list)
    for t in trades:
        by_session[t.session].append(t)

    print(f"\n{'Session':<15} {'Trades':<8} {'Wins':<8} {'WR %':<8} {'P&L':<15} {'Avg MFE':<10} {'Avg MAE':<10}")
    print("-"*80)

    for session in ["London", "US Morning", "US Power Hour"]:
        session_trades = by_session.get(session, [])
        if not session_trades:
            continue

        s_wins = len([t for t in session_trades if t.result == "WIN"])
        s_pnl = sum(t.pnl_usd for t in session_trades)
        s_wr = s_wins / len(session_trades) * 100
        s_mfe = sum(t.max_favorable for t in session_trades) / len(session_trades)
        s_mae = sum(t.max_adverse for t in session_trades) / len(session_trades)

        icon = "✅" if s_pnl > 0 else "❌"
        print(f"{icon} {session:<13} {len(session_trades):<8} {s_wins:<8} {s_wr:<8.1f} ${s_pnl:<14,.2f} {s_mfe:<10.1f} {s_mae:<10.1f}")

    # =========================================================================
    # ANALYSE PAR DIRECTION
    # =========================================================================

    print(f"\n{'='*100}")
    print(f"↕️ ANALYSE PAR DIRECTION")
    print(f"{'='*100}")

    longs = [t for t in trades if t.direction == "LONG"]
    shorts = [t for t in trades if t.direction == "SHORT"]

    for direction, dir_trades in [("LONG", longs), ("SHORT", shorts)]:
        if not dir_trades:
            continue

        d_wins = len([t for t in dir_trades if t.result == "WIN"])
        d_pnl = sum(t.pnl_usd for t in dir_trades)
        d_wr = d_wins / len(dir_trades) * 100

        icon = "✅" if d_pnl > 0 else "❌"
        print(f"\n{icon} {direction}: {len(dir_trades)} trades, {d_wins} wins, {d_wr:.1f}% WR, ${d_pnl:+,.2f}")

    # =========================================================================
    # ANALYSE PAR NIVEAU DE DISTANCE
    # =========================================================================

    print(f"\n{'='*100}")
    print(f"📏 ANALYSE PAR DISTANCE AU NIVEAU")
    print(f"{'='*100}")

    dist_buckets = {
        "0-5t": [t for t in trades if t.distance_to_level <= 5],
        "5-10t": [t for t in trades if 5 < t.distance_to_level <= 10],
        "10-15t": [t for t in trades if 10 < t.distance_to_level <= 15],
    }

    print(f"\n{'Distance':<12} {'Trades':<8} {'Wins':<8} {'WR %':<8} {'P&L':<15}")
    print("-"*55)

    for bucket, bucket_trades in dist_buckets.items():
        if not bucket_trades:
            continue

        b_wins = len([t for t in bucket_trades if t.result == "WIN"])
        b_pnl = sum(t.pnl_usd for t in bucket_trades)
        b_wr = b_wins / len(bucket_trades) * 100

        icon = "✅" if b_pnl > 0 else "❌"
        print(f"{icon} {bucket:<10} {len(bucket_trades):<8} {b_wins:<8} {b_wr:<8.1f} ${b_pnl:<14,.2f}")

    # =========================================================================
    # ANALYSE PAR DELTA
    # =========================================================================

    print(f"\n{'='*100}")
    print(f"📊 ANALYSE PAR FORCE DU DELTA")
    print(f"{'='*100}")

    delta_buckets = {
        "0-100": [t for t in trades if abs(t.delta) <= 100],
        "100-200": [t for t in trades if 100 < abs(t.delta) <= 200],
        "200-300": [t for t in trades if 200 < abs(t.delta) <= 300],
        "300+": [t for t in trades if abs(t.delta) > 300],
    }

    print(f"\n{'Delta':<12} {'Trades':<8} {'Wins':<8} {'WR %':<8} {'P&L':<15}")
    print("-"*55)

    for bucket, bucket_trades in delta_buckets.items():
        if not bucket_trades:
            continue

        b_wins = len([t for t in bucket_trades if t.result == "WIN"])
        b_pnl = sum(t.pnl_usd for t in bucket_trades)
        b_wr = b_wins / len(bucket_trades) * 100

        icon = "✅" if b_pnl > 0 else "❌"
        print(f"{icon} {bucket:<10} {len(bucket_trades):<8} {b_wins:<8} {b_wr:<8.1f} ${b_pnl:<14,.2f}")

    # =========================================================================
    # DIAGNOSTIC FINAL
    # =========================================================================

    print(f"\n{'='*100}")
    print(f"🏥 DIAGNOSTIC - POURQUOI ES PERD ?")
    print(f"{'='*100}")

    issues = []
    recommendations = []

    # Issue 1: Win Rate trop bas
    if win_rate < 30:
        issues.append(f"❌ Win Rate trop bas: {win_rate:.1f}% (cible: >35%)")

        # Vérifier si c'est le TP trop loin
        if wins:
            avg_mfe_wins = sum(t.max_favorable for t in wins) / len(wins)
            if avg_mfe_wins < TP_SL_CONFIG[SYMBOL]['tp_ticks'] * 0.7:
                recommendations.append(f"💡 Réduire le TP de {TP_SL_CONFIG[SYMBOL]['tp_ticks']}t → {int(avg_mfe_wins * 1.2)}t")

    # Issue 2: Trades qui touchent le TP puis se retournent
    if could_have_won and len(could_have_won) > len(losses) * 0.3:
        issues.append(f"❌ {len(could_have_won)} trades ont touché le TP avant le SL mais ont perdu")
        recommendations.append(f"💡 Problème d'exécution ou de timing - Vérifier les données")

    # Issue 3: MAE trop élevé
    if losses:
        avg_mae = sum(t.max_adverse for t in losses) / len(losses)
        if avg_mae > TP_SL_CONFIG[SYMBOL]['sl_ticks'] * 1.5:
            issues.append(f"❌ Le marché va trop contre nous (MAE moyen: {avg_mae:.1f}t)")

    # Issue 4: Session problématique
    worst_session = None
    worst_pnl = 0
    for session, session_trades in by_session.items():
        s_pnl = sum(t.pnl_usd for t in session_trades)
        if s_pnl < worst_pnl:
            worst_pnl = s_pnl
            worst_session = session

    if worst_session and worst_pnl < -1000:
        issues.append(f"❌ Session {worst_session} très perdante: ${worst_pnl:,.2f}")
        recommendations.append(f"💡 Considérer désactiver ES pendant {worst_session}")

    # Issue 5: Delta faible = pertes
    weak_delta = delta_buckets.get("0-100", [])
    if weak_delta:
        weak_pnl = sum(t.pnl_usd for t in weak_delta)
        if weak_pnl < -500:
            issues.append(f"❌ Trades avec delta faible (<100) perdent: ${weak_pnl:,.2f}")
            recommendations.append(f"💡 Augmenter le delta minimum pour ES à 100+")

    # Afficher diagnostic
    print("\n🔴 PROBLÈMES IDENTIFIÉS:")
    for issue in issues:
        print(f"   {issue}")

    print("\n🟢 RECOMMANDATIONS:")
    for rec in recommendations:
        print(f"   {rec}")

    # Recommandations supplémentaires basées sur l'analyse
    print(f"\n{'='*100}")
    print(f"🎯 PLAN D'ACTION POUR RENDRE ES RENTABLE")
    print(f"{'='*100}")

    print("""
    1. 📉 RÉDUIRE LE TP
       → Actuel: 30 ticks
       → Suggéré: 20-25 ticks (capturer les gains avant retournement)

    2. 📊 AUGMENTER LE DELTA MINIMUM
       → Actuel: 0
       → Suggéré: 200-300 (ne trader que les mouvements forts)

    3. 🕐 FILTRER LES SESSIONS
       → Identifier la session la plus perdante
       → Soit la désactiver, soit augmenter les seuils

    4. 📏 RESSERRER LA DISTANCE
       → Actuel: 15 ticks
       → Tester: 8-10 ticks (plus proche = plus précis)

    5. ⚡ TRAILING STOP
       → Activer un trailing à +15 ticks
       → Protéger les gains avant retournement
    """)

    # Sauvegarder
    output = {
        "audit_date": datetime.now().isoformat(),
        "symbol": SYMBOL,
        "total_trades": len(trades),
        "win_rate": win_rate,
        "pnl_total": total_pnl,
        "issues": issues,
        "recommendations": recommendations,
        "trades_detail": [
            {
                "direction": t.direction,
                "result": t.result,
                "pnl": t.pnl_usd,
                "session": t.session,
                "delta": t.delta,
                "distance": t.distance_to_level,
                "mfe": t.max_favorable,
                "mae": t.max_adverse
            }
            for t in trades
        ]
    }

    output_path = Path(__file__).parent / "audit_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Audit sauvegardé: {output_path}")


if __name__ == "__main__":
    run_audit()
