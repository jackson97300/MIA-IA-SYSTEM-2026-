"""
🎯 BACKTEST PRESSURE_STRENGTH V3 - AVEC DEBUG
==============================================

Version avec debug pour comprendre pourquoi 0 signaux

Date: 06/12/2025
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import time
import argparse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# BARRE DE PROGRESSION
# ============================================================================

class ProgressBar:
    def __init__(self, total: int, desc: str = "", width: int = 40):
        self.total = total
        self.desc = desc
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, n: int = 1):
        self.current += n
        percent = self.current / max(self.total, 1)
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)
        eta = (time.time() - self.start_time) / max(self.current, 1) * (self.total - self.current)
        sys.stdout.write(f"\r{self.desc} |{bar}| {self.current}/{self.total} ETA:{eta:.0f}s")
        sys.stdout.flush()

    def close(self):
        print(f" ✅ {time.time()-self.start_time:.1f}s")


# ============================================================================
# CONFIGURATION - ASSOUPLIE POUR DEBUG
# ============================================================================

# Seuils TRÈS assouplis pour voir les signaux
MIN_TOTAL_CONFIDENCE = {'ES': 0.10, 'NQ': 0.10}  # Très bas pour debug
MAX_DISTANCE_TO_LEVEL = {'ES': 100, 'NQ': 150}   # Très large pour debug
TP_SL_CONFIG = {'ES': {'tp': 40, 'sl': 20}, 'NQ': {'tp': 50, 'sl': 25}}
TICK_VALUES = {'ES': 12.50, 'NQ': 5.00}
TICK_SIZES = {'ES': 0.25, 'NQ': 0.25}

# Sessions (heure Paris)
TRADING_SESSIONS = {
    "LONDON": (8, 11),
    "US_MORNING": (15, 17),
    "POWER_HOUR": (20, 22)
}

COOLDOWN_MS = 60000  # 1 min seulement pour debug
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")
CHART_MAPPING = {'ES': 3, 'NQ': 9}
SYMBOLS = ["ES", "NQ"]

PRESSURE_THRESHOLDS = [0.00, 0.05, 0.10, 0.15, 0.20]


# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class Signal:
    timestamp: int
    symbol: str
    direction: str
    price: float
    score: float
    pressure: float
    delta: float


@dataclass
class Trade:
    signal: Signal
    result: str
    pnl: float


# ============================================================================
# FONCTIONS
# ============================================================================

def get_dates(limit=None):
    dates = []
    for month in ["NOVEMBRE", "DECEMBRE"]:
        mp = BASE_PATH / month
        if mp.exists():
            for d in mp.iterdir():
                if d.is_dir() and d.name.isdigit():
                    dates.append((month, d.name, d))
    dates.sort(key=lambda x: x[1])
    return dates[:limit] if limit else dates


def load_snaps(path: Path, symbol: str):
    chart = CHART_MAPPING.get(symbol)
    ml = path / f"CHART_{chart}" / "ML_READY"
    if not ml.exists():
        return []
    files = list(ml.glob(f"ml_*{symbol}*.jsonl"))
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


def ts_to_hour(ts_ms):
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    # Paris = UTC+1
    return (dt.hour + 1) % 24


def is_session(ts_ms):
    h = ts_to_hour(ts_ms)
    for name, (start, end) in TRADING_SESSIONS.items():
        if start <= h < end:
            return True, name
    return False, "CLOSED"


def get_min_dist(snap, price, symbol):
    tick = TICK_SIZES.get(symbol, 0.25)
    min_d = 9999

    for k in ['hvl', 'vah', 'val', 'poc', 'vwap', 'call_resistance', 'put_support']:
        v = snap.get(k)
        if v and v > 0:
            min_d = min(min_d, abs(price - v) / tick)

    for i in range(1, 11):
        v = snap.get(f'gex_{i}')
        if v and v > 0:
            min_d = min(min_d, abs(price - v) / tick)

    for i in range(9):
        v = snap.get(f'blind_spot_{i}')
        if v and v > 0:
            min_d = min(min_d, abs(price - v) / tick)

    return min_d if min_d < 9999 else None


def check_signal(snap, symbol, debug=False):
    """
    Vérifie si un snapshot génère un signal.
    Retourne (Signal ou None, raison_rejet)
    """
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)
    pressure = snap.get('pressure_strength', 0)

    # Check basiques
    if not ts or not mid:
        return None, "pas_de_prix"

    # Check session
    in_session, session = is_session(ts)
    if not in_session:
        return None, f"hors_session_{session}"

    # Direction
    if delta == 0:
        return None, "delta_zero"
    direction = "LONG" if delta > 0 else "SHORT"

    # Score simplifié
    l1 = snap.get('layer1_score', 0) or snap.get('menthorq_score', 0) or 0.3
    l2 = snap.get('layer2_score', 0) or snap.get('orderflow_score', 0) or 0.2
    l3 = snap.get('layer3_score', 0) or snap.get('context_score', 0) or 0.2
    score = l1 * 0.5 + l2 * 0.3 + l3 * 0.2

    # Seuil score
    min_score = MIN_TOTAL_CONFIDENCE.get(symbol, 0.10)
    if score < min_score:
        return None, f"score_trop_bas_{score:.2f}"

    # Distance au niveau
    dist = get_min_dist(snap, mid, symbol)
    if dist is None:
        return None, "pas_de_niveau"

    max_dist = MAX_DISTANCE_TO_LEVEL.get(symbol, 100)
    if dist > max_dist:
        return None, f"trop_loin_{dist:.0f}t"

    return Signal(ts, symbol, direction, mid, score, pressure, delta), None


def sim_trade(sig: Signal, snaps: List[Dict]) -> Trade:
    cfg = TP_SL_CONFIG.get(sig.symbol, TP_SL_CONFIG['ES'])
    tick_v = TICK_VALUES.get(sig.symbol, 12.50)
    tick_s = TICK_SIZES.get(sig.symbol, 0.25)

    if sig.direction == "LONG":
        tp = sig.price + cfg['tp'] * tick_s
        sl = sig.price - cfg['sl'] * tick_s
    else:
        tp = sig.price - cfg['tp'] * tick_s
        sl = sig.price + cfg['sl'] * tick_s

    for s in snaps[:500]:
        h = s.get('high', s.get('mid', 0))
        l = s.get('low', s.get('mid', 0))

        if sig.direction == "LONG":
            if h >= tp:
                return Trade(sig, "WIN", cfg['tp'] * tick_v)
            if l <= sl:
                return Trade(sig, "LOSS", -cfg['sl'] * tick_v)
        else:
            if l <= tp:
                return Trade(sig, "WIN", cfg['tp'] * tick_v)
            if h >= sl:
                return Trade(sig, "LOSS", -cfg['sl'] * tick_v)

    return Trade(sig, "BE", 0)


def backtest(data, threshold):
    results = {"trades": [], "rejected": 0, "accepted": 0}

    for symbol in SYMBOLS:
        last_t = 0
        for _, snaps in data.get(symbol, []):
            for i, snap in enumerate(snaps):
                sig, reason = check_signal(snap, symbol)
                if not sig:
                    continue

                # Cooldown
                if sig.timestamp - last_t < COOLDOWN_MS:
                    continue

                # FILTRE PRESSURE
                if sig.pressure < threshold:
                    results["rejected"] += 1
                    continue

                results["accepted"] += 1
                last_t = sig.timestamp

                trade = sim_trade(sig, snaps[i+1:i+501])
                results["trades"].append(trade)

    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='2 jours')
    parser.add_argument('--full', action='store_true', help='Tout')
    parser.add_argument('--debug', action='store_true', help='Mode debug')
    args = parser.parse_args()

    limit = 2 if not args.full else None

    print("="*100)
    print("🎯 BACKTEST PRESSURE_STRENGTH V3 (avec debug)")
    print("="*100)

    # 1. Dates
    dates = get_dates(limit)
    print(f"\n📅 {len(dates)} jour(s) trouvé(s)")
    for m, d, _ in dates:
        print(f"   - {d}")

    # 2. Charger données
    print(f"\n📥 Chargement...")
    data = {s: [] for s in SYMBOLS}
    total = 0

    pbar = ProgressBar(len(dates) * len(SYMBOLS), "Load")
    for m, d, p in dates:
        for sym in SYMBOLS:
            snaps = load_snaps(p, sym)
            if snaps:
                data[sym].append((d, snaps))
                total += len(snaps)
            pbar.update()
    pbar.close()

    print(f"   Total: {total:,} snapshots")

    # 3. DEBUG: Analyser pourquoi pas de signaux
    print(f"\n🔍 ANALYSE DEBUG...")

    reasons = defaultdict(int)
    signals_found = 0
    sample_signals = []

    for sym in SYMBOLS:
        for _, snaps in data.get(sym, []):
            for snap in snaps[:1000]:  # Sample
                sig, reason = check_signal(snap, sym)
                if sig:
                    signals_found += 1
                    if len(sample_signals) < 5:
                        sample_signals.append(sig)
                else:
                    reasons[reason] += 1

    print(f"\n   📊 Raisons de rejet (sur échantillon):")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:10]:
        print(f"      {reason}: {count}")

    print(f"\n   ✅ Signaux trouvés: {signals_found}")

    if sample_signals:
        print(f"\n   📈 Exemples de signaux:")
        for s in sample_signals[:3]:
            print(f"      {s.symbol} {s.direction} @ {s.price:.2f}, score={s.score:.2f}, pressure={s.pressure:.3f}")

    # 4. Backtest
    print(f"\n🔄 Backtest ({len(PRESSURE_THRESHOLDS)} seuils)...")

    results = []
    pbar = ProgressBar(len(PRESSURE_THRESHOLDS), "Test")
    for th in PRESSURE_THRESHOLDS:
        r = backtest(data, th)
        results.append((th, r))
        pbar.update()
    pbar.close()

    # 5. Résultats
    print(f"\n{'='*100}")
    print(f"📊 RÉSULTATS")
    print(f"{'='*100}")

    print(f"\n{'Seuil':<8} {'Accept':<8} {'Reject':<8} {'Trades':<8} {'Wins':<6} {'Loss':<6} {'WR%':<8} {'P&L':<15}")
    print("-"*80)

    for th, r in results:
        trades = r["trades"]
        wins = sum(1 for t in trades if t.result == "WIN")
        losses = sum(1 for t in trades if t.result == "LOSS")
        wr = wins / len(trades) * 100 if trades else 0
        pnl = sum(t.pnl for t in trades)

        status = "✅" if pnl > 0 else "❌" if pnl < 0 else ""
        print(f"{th:<8.2f} {r['accepted']:<8} {r['rejected']:<8} {len(trades):<8} {wins:<6} {losses:<6} {wr:<8.1f} {status} ${pnl:+,.2f}")

    # Recommandation
    valid = [(th, r) for th, r in results if len(r["trades"]) >= 3]
    if valid:
        best_th, best_r = max(valid, key=lambda x: sum(t.pnl for t in x[1]["trades"]))
        pnl = sum(t.pnl for t in best_r["trades"])
        wr = sum(1 for t in best_r["trades"] if t.result == "WIN") / len(best_r["trades"]) * 100

        print(f"\n🏆 MEILLEUR SEUIL: {best_th:.2f}")
        print(f"   P&L: ${pnl:+,.2f} | WR: {wr:.1f}% | Trades: {len(best_r['trades'])}")

    if limit:
        print(f"\n💡 Pour le backtest complet: python {Path(__file__).name} --full")

    print(f"\n{'='*100}")


if __name__ == "__main__":
    main()
