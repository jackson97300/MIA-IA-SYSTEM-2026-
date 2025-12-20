"""
🎯 BACKTEST PRESSURE_STRENGTH - RÉSULTATS PAR SESSION
======================================================

Affiche les résultats pour chaque session de trading:
- LONDON: 08:00 - 11:00 (Paris)
- US_MORNING: 15:50 - 17:00 (Paris)
- POWER_HOUR: 20:00 - 21:30 (Paris)

Date: 06/12/2025
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")
CHART_MAPPING = {'ES': 3, 'NQ': 9}
SYMBOLS = ["ES", "NQ"]

# Sessions (heure Paris)
TRADING_SESSIONS = {
    "LONDON": (8, 11),
    "US_MORNING": (15, 17),
    "POWER_HOUR": (20, 22)
}

TP_SL = {'ES': {'tp': 40, 'sl': 20}, 'NQ': {'tp': 50, 'sl': 25}}
TICK_VAL = {'ES': 12.50, 'NQ': 5.00}
TICK_SZ = {'ES': 0.25, 'NQ': 0.25}

COOLDOWN_MS = 60000
PRESSURE_THRESHOLDS = [0.00, 0.02, 0.03, 0.05, 0.10, 0.15, 0.20]


# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class Signal:
    timestamp: int
    symbol: str
    direction: str
    price: float
    pressure: float
    session: str

@dataclass
class Trade:
    signal: Signal
    result: str
    pnl: float


# ============================================================================
# FONCTIONS
# ============================================================================

class ProgressBar:
    def __init__(self, total, desc=""):
        self.total = total
        self.current = 0
        self.desc = desc
        self.start = time.time()

    def update(self, n=1):
        self.current += n
        pct = self.current / max(self.total, 1)
        bar = "█" * int(40 * pct) + "░" * (40 - int(40 * pct))
        eta = (time.time() - self.start) / max(self.current, 1) * (self.total - self.current)
        sys.stdout.write(f"\r{self.desc} |{bar}| {self.current}/{self.total} ETA:{eta:.0f}s")
        sys.stdout.flush()

    def close(self):
        print(f" ✅ {time.time()-self.start:.1f}s")


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


def load_snaps(path, symbol):
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


def get_session(ts_ms):
    """Retourne la session pour un timestamp"""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    h_paris = (dt.hour + 1) % 24  # UTC+1

    for name, (start, end) in TRADING_SESSIONS.items():
        if start <= h_paris < end:
            return name
    return None


def get_dist(snap, price, symbol):
    tick = TICK_SZ.get(symbol, 0.25)
    min_d = 9999
    for k in ['hvl', 'vah', 'val', 'poc', 'vwap']:
        v = snap.get(k)
        if v and v > 0:
            min_d = min(min_d, abs(price - v) / tick)
    for i in range(1, 11):
        v = snap.get(f'gex_{i}')
        if v and v > 0:
            min_d = min(min_d, abs(price - v) / tick)
    return min_d if min_d < 9999 else None


def check_signal(snap, symbol):
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)
    pressure = snap.get('pressure_strength', 0)

    if not ts or not mid or delta == 0:
        return None

    session = get_session(ts)
    if not session:
        return None

    dist = get_dist(snap, mid, symbol)
    if dist is None or dist > 100:
        return None

    direction = "LONG" if delta > 0 else "SHORT"

    return Signal(ts, symbol, direction, mid, pressure, session)


def sim_trade(sig, snaps):
    cfg = TP_SL.get(sig.symbol, TP_SL['ES'])
    tv = TICK_VAL.get(sig.symbol, 12.50)
    ts = TICK_SZ.get(sig.symbol, 0.25)

    if sig.direction == "LONG":
        tp = sig.price + cfg['tp'] * ts
        sl = sig.price - cfg['sl'] * ts
    else:
        tp = sig.price - cfg['tp'] * ts
        sl = sig.price + cfg['sl'] * ts

    for s in snaps[:500]:
        h = s.get('high', s.get('mid', 0))
        l = s.get('low', s.get('mid', 0))

        if sig.direction == "LONG":
            if h >= tp:
                return Trade(sig, "WIN", cfg['tp'] * tv)
            if l <= sl:
                return Trade(sig, "LOSS", -cfg['sl'] * tv)
        else:
            if l <= tp:
                return Trade(sig, "WIN", cfg['tp'] * tv)
            if h >= sl:
                return Trade(sig, "LOSS", -cfg['sl'] * tv)

    return Trade(sig, "BE", 0)


def backtest(data, threshold):
    results = {
        "trades": [],
        "by_session": defaultdict(lambda: {"trades": [], "accepted": 0, "rejected": 0})
    }

    for symbol in SYMBOLS:
        last_t = 0
        for _, snaps in data.get(symbol, []):
            for i, snap in enumerate(snaps):
                sig = check_signal(snap, symbol)
                if not sig:
                    continue

                if sig.timestamp - last_t < COOLDOWN_MS:
                    continue

                # FILTRE PRESSURE
                if sig.pressure < threshold:
                    results["by_session"][sig.session]["rejected"] += 1
                    continue

                results["by_session"][sig.session]["accepted"] += 1
                last_t = sig.timestamp

                trade = sim_trade(sig, snaps[i+1:i+501])
                results["trades"].append(trade)
                results["by_session"][sig.session]["trades"].append(trade)

    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*120)
    print("🎯 BACKTEST PRESSURE_STRENGTH - RÉSULTATS PAR SESSION")
    print("="*120)

    # Charger données (tous les jours)
    dates = get_dates()
    print(f"\n📅 {len(dates)} jours de données")

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

    # Backtests
    print(f"\n🔄 Backtest...")

    all_results = {}
    pbar = ProgressBar(len(PRESSURE_THRESHOLDS), "Test")
    for th in PRESSURE_THRESHOLDS:
        all_results[th] = backtest(data, th)
        pbar.update()
    pbar.close()

    # Afficher résultats par SESSION
    print("\n" + "="*120)
    print("📊 RÉSULTATS PAR SESSION")
    print("="*120)

    for session in ["LONDON", "US_MORNING", "POWER_HOUR"]:
        times = TRADING_SESSIONS[session]
        print(f"\n{'='*100}")
        print(f"🕐 SESSION: {session} ({times[0]}h - {times[1]}h Paris)")
        print(f"{'='*100}")

        print(f"\n{'Seuil':<8} {'Accept':<8} {'Reject':<8} {'Trades':<8} {'Wins':<6} {'Loss':<6} {'WR%':<8} {'P&L':<15} {'P&L/Trade':<12}")
        print("-"*95)

        for th in PRESSURE_THRESHOLDS:
            r = all_results[th]
            sess_data = r["by_session"][session]
            trades = sess_data["trades"]

            accepted = sess_data["accepted"]
            rejected = sess_data["rejected"]
            wins = sum(1 for t in trades if t.result == "WIN")
            losses = sum(1 for t in trades if t.result == "LOSS")
            wr = wins / len(trades) * 100 if trades else 0
            pnl = sum(t.pnl for t in trades)
            pnl_per = pnl / len(trades) if trades else 0

            status = "✅" if pnl > 0 else "❌" if pnl < 0 else ""
            wr_icon = "🔥" if wr >= 40 else "✅" if wr >= 35 else "⚠️" if wr < 30 else ""

            print(f"{th:<8.2f} {accepted:<8} {rejected:<8} {len(trades):<8} {wins:<6} {losses:<6} {wr_icon}{wr:<7.1f} {status} ${pnl:+,.0f}{'':5} ${pnl_per:+.2f}")

    # Résumé global
    print("\n" + "="*120)
    print("📊 RÉSUMÉ GLOBAL (Toutes sessions)")
    print("="*120)

    print(f"\n{'Seuil':<8} {'Trades':<10} {'Wins':<8} {'Loss':<8} {'WR%':<10} {'P&L Total':<15} {'P&L/Trade':<12}")
    print("-"*85)

    best_th = None
    best_pnl = float('-inf')

    for th in PRESSURE_THRESHOLDS:
        r = all_results[th]
        trades = r["trades"]
        wins = sum(1 for t in trades if t.result == "WIN")
        losses = sum(1 for t in trades if t.result == "LOSS")
        wr = wins / len(trades) * 100 if trades else 0
        pnl = sum(t.pnl for t in trades)
        pnl_per = pnl / len(trades) if trades else 0

        if pnl > best_pnl:
            best_pnl = pnl
            best_th = th

        status = "✅" if pnl > 0 else "❌" if pnl < 0 else ""
        print(f"{th:<8.2f} {len(trades):<10} {wins:<8} {losses:<8} {wr:<10.1f} {status} ${pnl:+,.0f}{'':5} ${pnl_per:+.2f}")

    # Recommandation
    print("\n" + "="*120)
    print("🏆 RECOMMANDATION")
    print("="*120)

    print(f"\n✅ Meilleur seuil global: {best_th:.2f}")
    print(f"   P&L: ${best_pnl:+,.0f}")

    # Meilleur par session
    print(f"\n📈 Meilleur seuil PAR SESSION:")
    for session in ["LONDON", "US_MORNING", "POWER_HOUR"]:
        best_session_th = None
        best_session_pnl = float('-inf')

        for th in PRESSURE_THRESHOLDS:
            trades = all_results[th]["by_session"][session]["trades"]
            pnl = sum(t.pnl for t in trades)
            if pnl > best_session_pnl:
                best_session_pnl = pnl
                best_session_th = th

        print(f"   {session}: seuil {best_session_th:.2f} → ${best_session_pnl:+,.0f}")

    print("\n" + "="*120)


if __name__ == "__main__":
    main()
