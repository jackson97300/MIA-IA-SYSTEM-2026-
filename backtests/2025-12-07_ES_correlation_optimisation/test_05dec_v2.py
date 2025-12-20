"""
🧪 TEST CORRÉLATION ES/NQ - JOURNÉE 05/12/2025 (v2 - corrigé)
===============================================================

Test détaillé avec recherche NQ corrigée.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import bisect

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import logging
logging.disable(logging.INFO)

# ============================================================================
# CONFIGURATION
# ============================================================================

DATE = "20251205"
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE")
CHART_ES = 3
CHART_NQ = 9

ES_CONFIG = {
    'tick_size': 0.25,
    'tick_value': 12.50,
    'tp_ticks': 20,
    'sl_ticks': 20,
    'min_delta': 100,
    'min_pressure': 0.20,
}

MIN_CORRELATION_SCORE = 50
SYNC_TOLERANCE_MS = 5000
COOLDOWN_MS = 300000

SESSIONS = {
    'London': {'start': 8, 'end': 11},
    'US_Morning': {'start': 15, 'end': 17},
    'Power_Hour': {'start': 20, 'end': 22},
}

# ============================================================================
# FONCTIONS
# ============================================================================

def load_snapshots(symbol: str) -> List[Dict]:
    chart_id = CHART_ES if symbol == "ES" else CHART_NQ
    path = BASE_PATH / DATE / f"CHART_{chart_id}" / "ML_READY"

    if not path.exists():
        return []

    files = list(path.glob(f"ml_*{symbol}*.jsonl"))
    if not files:
        return []

    snaps = []
    with open(files[0], 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snaps.append(json.loads(line))
                except:
                    pass
    return snaps


def get_session(hour: int) -> Optional[str]:
    for name, times in SESSIONS.items():
        if times['start'] <= hour < times['end']:
            return name
    return None


def get_direction(delta: float) -> str:
    if delta > 100:
        return "LONG"
    elif delta < -100:
        return "SHORT"
    return "NEUTRAL"


def find_closest_nq(es_time: int, nq_snaps: List[Dict], nq_times: List[int]) -> Optional[Dict]:
    """Trouve le snapshot NQ le plus proche en temps"""
    if not nq_times:
        return None

    # Binary search pour trouver l'index le plus proche
    idx = bisect.bisect_left(nq_times, es_time)

    candidates = []
    if idx > 0:
        candidates.append(idx - 1)
    if idx < len(nq_times):
        candidates.append(idx)

    best_idx = None
    best_diff = float('inf')

    for i in candidates:
        diff = abs(nq_times[i] - es_time)
        if diff < best_diff and diff <= SYNC_TOLERANCE_MS:
            best_diff = diff
            best_idx = i

    if best_idx is not None:
        return nq_snaps[best_idx]
    return None


def calculate_correlation_score(es_delta: float, nq_delta: float,
                                 es_pressure: float, nq_pressure: float) -> float:
    score = 0

    # Delta même direction (0-40 points)
    if (es_delta > 0 and nq_delta > 0) or (es_delta < 0 and nq_delta < 0):
        ratio = min(abs(es_delta), abs(nq_delta)) / max(abs(es_delta), abs(nq_delta), 1)
        score += 40 * ratio

    # Force NQ (0-30 points)
    nq_strength = min(abs(nq_delta) / 200, 1)
    score += 30 * nq_strength

    # Pressure (0-30 points)
    avg_pressure = (es_pressure + nq_pressure) / 2
    score += 30 * min(avg_pressure * 2, 1)

    return min(100, score)


def simulate_trade(entry_price: float, direction: str, snapshots: List[Dict],
                   start_time: int) -> Dict:
    tp_ticks = ES_CONFIG['tp_ticks']
    sl_ticks = ES_CONFIG['sl_ticks']
    tick_size = ES_CONFIG['tick_size']
    tick_value = ES_CONFIG['tick_value']

    if direction == "LONG":
        tp_price = entry_price + tp_ticks * tick_size
        sl_price = entry_price - sl_ticks * tick_size
    else:
        tp_price = entry_price - tp_ticks * tick_size
        sl_price = entry_price + sl_ticks * tick_size

    future_snaps = [s for s in snapshots if s.get('t_ms', 0) > start_time]

    for snap in future_snaps[:500]:
        price = snap.get('mid', 0)

        if direction == "LONG":
            if price >= tp_price:
                return {'result': 'WIN', 'pnl': tp_ticks * tick_value, 'exit': tp_price}
            elif price <= sl_price:
                return {'result': 'LOSS', 'pnl': -sl_ticks * tick_value, 'exit': sl_price}
        else:
            if price <= tp_price:
                return {'result': 'WIN', 'pnl': tp_ticks * tick_value, 'exit': tp_price}
            elif price >= sl_price:
                return {'result': 'LOSS', 'pnl': -sl_ticks * tick_value, 'exit': sl_price}

    return {'result': 'SCRATCH', 'pnl': 0, 'exit': entry_price}


def main():
    print("="*100)
    print("[TEST] CORRELATION ES/NQ - JOURNEE 05/12/2025 (v2)")
    print("="*100)
    print(f"\nSeuil correlation: >= {MIN_CORRELATION_SCORE}")

    # Charger
    print("\n[LOAD] Chargement...")
    es_snaps = load_snapshots("ES")
    nq_snaps = load_snapshots("NQ")
    print(f"   ES: {len(es_snaps):,} snapshots")
    print(f"   NQ: {len(nq_snaps):,} snapshots")

    # Indexer NQ par temps pour recherche binaire
    nq_times = [s.get('t_ms', 0) for s in nq_snaps]

    # Scanner
    print("\n[SCAN] Analyse des signaux ES...")
    signals = []
    last_signal_time = 0

    for es_snap in es_snaps:
        es_time = es_snap.get('t_ms', 0)
        es_delta = es_snap.get('delta', 0)
        es_mid = es_snap.get('mid', 0)
        es_pressure = es_snap.get('pressure_strength', 0)

        dt = datetime.fromtimestamp(es_time / 1000)
        hour = dt.hour
        session = get_session(hour)
        if session is None:
            continue

        direction = get_direction(es_delta)
        if direction == "NEUTRAL":
            continue

        if es_pressure < ES_CONFIG['min_pressure']:
            continue

        if es_time - last_signal_time < COOLDOWN_MS:
            continue

        last_signal_time = es_time

        # Trouver NQ le plus proche
        nq_snap = find_closest_nq(es_time, nq_snaps, nq_times)

        nq_delta = nq_snap.get('delta', 0) if nq_snap else 0
        nq_pressure = nq_snap.get('pressure_strength', 0) if nq_snap else 0
        nq_direction = get_direction(nq_delta)

        corr_score = calculate_correlation_score(es_delta, nq_delta, es_pressure, nq_pressure)
        trade_result = simulate_trade(es_mid, direction, es_snaps, es_time)

        signals.append({
            'time': dt.strftime('%H:%M'),
            'session': session,
            'direction': direction,
            'entry': es_mid,
            'es_delta': es_delta,
            'nq_delta': nq_delta,
            'nq_direction': nq_direction,
            'corr_score': corr_score,
            'result': trade_result['result'],
            'pnl': trade_result['pnl'],
            'would_take': corr_score >= MIN_CORRELATION_SCORE,
        })

    print(f"   Signaux: {len(signals)}")

    # Afficher
    print("\n" + "="*100)
    print("[SIGNALS] TOUS LES SIGNAUX DU 05/12/2025")
    print("="*100)
    print(f"\n{'Heure':<7} {'Session':<12} {'Dir':<6} {'Entry':<10} {'ES d':<8} {'NQ d':<8} "
          f"{'NQ Dir':<8} {'Score':<7} {'Result':<8} {'P&L':<10} {'Filtre':<10}")
    print("-"*100)

    for s in signals:
        take = "[OK]" if s['would_take'] else "[SKIP]"
        pnl_str = f"${s['pnl']:+.2f}" if s['pnl'] != 0 else "$0"

        print(f"{s['time']:<7} {s['session']:<12} {s['direction']:<6} {s['entry']:<10.2f} "
              f"{s['es_delta']:<8.0f} {s['nq_delta']:<8.0f} {s['nq_direction']:<8} "
              f"{s['corr_score']:<7.0f} {s['result']:<8} {pnl_str:<10} {take:<10}")

    print("-"*100)

    # Stats
    print("\n" + "="*100)
    print("[COMPARE] COMPARAISON")
    print("="*100)

    # Sans filtre
    wins_all = sum(1 for s in signals if s['result'] == 'WIN')
    losses_all = sum(1 for s in signals if s['result'] == 'LOSS')
    pnl_all = sum(s['pnl'] for s in signals)

    print(f"\n[SANS FILTRE] Tous les trades:")
    print(f"   Trades: {len(signals)}")
    print(f"   Wins: {wins_all} | Losses: {losses_all}")
    print(f"   Win Rate: {wins_all/(wins_all+losses_all)*100:.1f}%" if (wins_all+losses_all) > 0 else "")
    print(f"   P&L: ${pnl_all:,.2f}")

    # Avec filtre
    filtered = [s for s in signals if s['would_take']]
    wins_filt = sum(1 for s in filtered if s['result'] == 'WIN')
    losses_filt = sum(1 for s in filtered if s['result'] == 'LOSS')
    pnl_filt = sum(s['pnl'] for s in filtered)

    print(f"\n[AVEC FILTRE score >= {MIN_CORRELATION_SCORE}]:")
    print(f"   Trades: {len(filtered)} (skipped: {len(signals) - len(filtered)})")
    print(f"   Wins: {wins_filt} | Losses: {losses_filt}")
    if (wins_filt + losses_filt) > 0:
        print(f"   Win Rate: {wins_filt/(wins_filt+losses_filt)*100:.1f}%")
    print(f"   P&L: ${pnl_filt:,.2f}")

    # Impact
    delta_pnl = pnl_filt - pnl_all
    print(f"\n[IMPACT]:")
    print(f"   Difference P&L: ${delta_pnl:+,.2f}")

    # Trades skippés
    skipped = [s for s in signals if not s['would_take']]
    if skipped:
        skip_wins = sum(1 for s in skipped if s['result'] == 'WIN')
        skip_losses = sum(1 for s in skipped if s['result'] == 'LOSS')
        skip_pnl = sum(s['pnl'] for s in skipped)

        print(f"\n[TRADES SKIPPES] (score < {MIN_CORRELATION_SCORE}):")
        print(f"   Count: {len(skipped)}")
        print(f"   Wins evites: {skip_wins} | Losses evites: {skip_losses}")
        print(f"   P&L evite: ${skip_pnl:,.2f}")

    # Verdict
    print("\n" + "="*100)
    print("[VERDICT]")
    print("="*100)

    if delta_pnl > 0:
        print(f"\n   [OK] Le filtre correlation >= {MIN_CORRELATION_SCORE} AMELIORE le resultat")
        print(f"   Gain: +${delta_pnl:,.2f}")
    elif delta_pnl < 0:
        print(f"\n   [X] Le filtre correlation >= {MIN_CORRELATION_SCORE} DEGRADE le resultat")
        print(f"   Perte: ${delta_pnl:,.2f}")
    else:
        print(f"\n   [=] Le filtre n'a pas d'impact")


if __name__ == "__main__":
    main()
