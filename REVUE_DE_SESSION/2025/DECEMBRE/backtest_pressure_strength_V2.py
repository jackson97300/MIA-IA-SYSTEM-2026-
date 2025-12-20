"""
🎯 BACKTEST PRESSURE_STRENGTH V2 - AVEC PROGRESSION
====================================================

AMÉLIORATIONS:
✅ Mode TEST sur 2 jours d'abord (pour valider que ça marche)
✅ Barre de progression visible
✅ Feedback en temps réel
✅ Statistiques intermédiaires

Usage:
  python backtest_pressure_strength_V2.py --test    # Test sur 2 jours
  python backtest_pressure_strength_V2.py --full    # Backtest complet

Date: 06/12/2025
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
import time
import argparse

# Fix encoding Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# BARRE DE PROGRESSION SIMPLE (sans dépendance externe)
# ============================================================================

class ProgressBar:
    """Barre de progression simple sans tqdm"""

    def __init__(self, total: int, desc: str = "", width: int = 50):
        self.total = total
        self.desc = desc
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, n: int = 1):
        self.current += n
        self._display()

    def _display(self):
        percent = self.current / max(self.total, 1)
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        elapsed = time.time() - self.start_time
        eta = (elapsed / max(self.current, 1)) * (self.total - self.current)

        sys.stdout.write(f"\r{self.desc} |{bar}| {self.current}/{self.total} ({percent*100:.1f}%) ETA: {eta:.0f}s")
        sys.stdout.flush()

    def close(self):
        elapsed = time.time() - self.start_time
        print(f" ✅ Terminé en {elapsed:.1f}s")


# ============================================================================
# CONFIGURATION PRODUCTION
# ============================================================================

MIN_TOTAL_CONFIDENCE = {'ES': 0.30, 'NQ': 0.30, 'RTY': 0.42}
MIN_LAYER_CONFIDENCE = {
    'ES': {'layer1': 0.50, 'layer2': 0.17, 'layer3': 0.14},
    'NQ': {'layer1': 0.30, 'layer2': 0.20, 'layer3': 0.16},
}
MAX_DISTANCE_TO_LEVEL = {'ES': 15, 'NQ': 25, 'RTY': 20}
LAYER_WEIGHTS = {"menthorq": 0.50, "orderflow": 0.30, "context": 0.20}
TP_SL_CONFIG = {
    'ES': {'tp_ticks': 40, 'sl_ticks': 20},
    'NQ': {'tp_ticks': 50, 'sl_ticks': 25},
}
TICK_VALUES = {'ES': 12.50, 'NQ': 5.00}
TICK_SIZES = {'ES': 0.25, 'NQ': 0.25}

TRADING_SESSIONS = {
    "LONDON": {"start": (8, 0), "end": (11, 0)},
    "US_MORNING": {"start": (15, 50), "end": (17, 0)},
    "POWER_HOUR": {"start": (20, 0), "end": (21, 30)}
}

COOLDOWN_MS = 300000  # 5 min
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")
CHART_MAPPING = {'ES': 3, 'NQ': 9}
MONTHS = ["NOVEMBRE", "DECEMBRE"]
SYMBOLS = ["ES", "NQ"]

# Seuils à tester
PRESSURE_THRESHOLDS = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Signal:
    timestamp: int
    symbol: str
    direction: str
    entry_price: float
    total_score: float
    pressure_strength: float
    delta: float
    distance_to_level: float

@dataclass
class TradeResult:
    signal: Signal
    result: str
    pnl_ticks: float
    pnl_usd: float

# ============================================================================
# FONCTIONS
# ============================================================================

def get_all_dates(limit: Optional[int] = None) -> List[Tuple[str, str, Path]]:
    """Récupère les dates disponibles"""
    dates = []
    for month in MONTHS:
        month_path = BASE_PATH / month
        if not month_path.exists():
            continue
        for date_dir in month_path.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
                dates.append((month, date_dir.name, date_dir))
    dates.sort(key=lambda x: x[1])
    if limit:
        dates = dates[:limit]
    return dates


def load_ml_ready(date_path: Path, symbol: str) -> List[Dict]:
    """Charge snapshots ML_READY"""
    chart_id = CHART_MAPPING.get(symbol)
    if not chart_id:
        return []

    ml_path = date_path / f"CHART_{chart_id}" / "ML_READY"
    if not ml_path.exists():
        return []

    files = list(ml_path.glob(f"ml_*{symbol}*.jsonl"))
    if not files:
        return []

    snapshots = []
    with open(files[0], 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snapshots.append(json.loads(line))
                except:
                    pass
    return snapshots


def ts_to_paris(ts_ms: int) -> Tuple[int, int]:
    """Timestamp -> heure Paris"""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) + timedelta(hours=1)
    return dt.hour, dt.minute


def is_in_session(ts_ms: int) -> Tuple[bool, str]:
    """Check si dans session trading"""
    h, m = ts_to_paris(ts_ms)
    t = h + m / 60
    for name, times in TRADING_SESSIONS.items():
        start = times["start"][0] + times["start"][1] / 60
        end = times["end"][0] + times["end"][1] / 60
        if start <= t <= end:
            return True, name
    return False, "CLOSED"


def get_distance_to_level(snap: Dict, price: float, symbol: str) -> float:
    """Distance au niveau le plus proche"""
    tick = TICK_SIZES.get(symbol, 0.25)
    min_dist = 9999

    for key in ['hvl', 'vah', 'val', 'poc', 'call_resistance', 'put_support', 'vwap']:
        val = snap.get(key)
        if val:
            dist = abs(price - val) / tick
            min_dist = min(min_dist, dist)

    for i in range(1, 11):
        val = snap.get(f'gex_{i}')
        if val:
            dist = abs(price - val) / tick
            min_dist = min(min_dist, dist)

    for i in range(0, 9):
        val = snap.get(f'blind_spot_{i}')
        if val:
            dist = abs(price - val) / tick
            min_dist = min(min_dist, dist)

    return min_dist


def calculate_score(snap: Dict, symbol: str) -> Tuple[float, str]:
    """Calcule score ML et direction"""
    # Scores existants ou approximation
    l1 = snap.get('layer1_score') or snap.get('menthorq_score', 0.3)
    l2 = snap.get('layer2_score') or snap.get('orderflow_score', 0.2)
    l3 = snap.get('layer3_score') or snap.get('context_score', 0.2)

    total = l1 * 0.5 + l2 * 0.3 + l3 * 0.2

    delta = snap.get('delta', 0)
    direction = "LONG" if delta > 0 else "SHORT" if delta < 0 else "NONE"

    return total, direction


def validate_signal(snap: Dict, symbol: str) -> Optional[Signal]:
    """Valide un signal"""
    ts = snap.get('t_ms', 0)
    in_session, _ = is_in_session(ts)
    if not in_session:
        return None

    mid = snap.get('mid', 0)
    if not mid:
        return None

    score, direction = calculate_score(snap, symbol)
    if direction == "NONE":
        return None

    # Seuils ML
    if score < MIN_TOTAL_CONFIDENCE.get(symbol, 0.30):
        return None

    # Distance
    dist = get_distance_to_level(snap, mid, symbol)
    if dist > MAX_DISTANCE_TO_LEVEL.get(symbol, 20):
        return None

    pressure = snap.get('pressure_strength', 0)
    delta = snap.get('delta', 0)

    return Signal(ts, symbol, direction, mid, score, pressure, delta, dist)


def simulate_trade(signal: Signal, snaps: List[Dict]) -> TradeResult:
    """Simule TP/SL"""
    cfg = TP_SL_CONFIG.get(signal.symbol, TP_SL_CONFIG['ES'])
    tick_val = TICK_VALUES.get(signal.symbol, 12.50)
    tick_sz = TICK_SIZES.get(signal.symbol, 0.25)

    if signal.direction == "LONG":
        tp = signal.entry_price + cfg['tp_ticks'] * tick_sz
        sl = signal.entry_price - cfg['sl_ticks'] * tick_sz
    else:
        tp = signal.entry_price - cfg['tp_ticks'] * tick_sz
        sl = signal.entry_price + cfg['sl_ticks'] * tick_sz

    max_ms = 30 * 60 * 1000
    for snap in snaps[:1000]:
        if snap.get('t_ms', 0) - signal.timestamp > max_ms:
            break

        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))

        if signal.direction == "LONG":
            if high >= tp:
                return TradeResult(signal, "WIN", cfg['tp_ticks'], cfg['tp_ticks'] * tick_val)
            if low <= sl:
                return TradeResult(signal, "LOSS", -cfg['sl_ticks'], -cfg['sl_ticks'] * tick_val)
        else:
            if low <= tp:
                return TradeResult(signal, "WIN", cfg['tp_ticks'], cfg['tp_ticks'] * tick_val)
            if high >= sl:
                return TradeResult(signal, "LOSS", -cfg['sl_ticks'], -cfg['sl_ticks'] * tick_val)

    return TradeResult(signal, "BE", 0, 0)


def run_backtest(all_data: Dict, threshold: float, show_progress: bool = True) -> Dict:
    """Backtest pour un seuil"""
    results = {
        "threshold": threshold,
        "signals": 0,
        "accepted": 0,
        "rejected": 0,
        "trades": [],
    }

    for symbol in SYMBOLS:
        if symbol not in all_data:
            continue

        last_time = 0

        for date_str, snaps in all_data[symbol]:
            for i, snap in enumerate(snaps):
                sig = validate_signal(snap, symbol)
                if not sig:
                    continue

                results["signals"] += 1

                if sig.timestamp - last_time < COOLDOWN_MS:
                    continue

                # FILTRE PRESSURE_STRENGTH
                if sig.pressure_strength < threshold:
                    results["rejected"] += 1
                    continue

                results["accepted"] += 1
                last_time = sig.timestamp

                subsequent = snaps[i+1:i+1001]
                trade = simulate_trade(sig, subsequent)
                results["trades"].append(trade)

    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Backtest pressure_strength")
    parser.add_argument('--test', action='store_true', help='Mode test (2 jours)')
    parser.add_argument('--full', action='store_true', help='Backtest complet')
    args = parser.parse_args()

    # Défaut: mode test
    if not args.full:
        args.test = True

    print("="*100)
    print("🎯 BACKTEST PRESSURE_STRENGTH V2")
    print("="*100)

    # Déterminer le nombre de jours
    if args.test:
        limit = 2
        print(f"\n🧪 MODE TEST: {limit} jours seulement")
    else:
        limit = None
        print(f"\n🚀 MODE COMPLET: Tous les jours disponibles")

    # 1. Charger les dates
    print(f"\n📅 Recherche des données...")
    dates = get_all_dates(limit)
    print(f"   ✅ {len(dates)} jour(s) trouvé(s)")

    if not dates:
        print("   ❌ Aucune donnée trouvée!")
        return

    for m, d, p in dates:
        print(f"      - {d} ({m})")

    # 2. Charger les snapshots avec progression
    print(f"\n📥 Chargement des snapshots...")
    all_data: Dict[str, List] = {s: [] for s in SYMBOLS}
    total_snaps = 0
    has_pressure = 0

    pbar = ProgressBar(len(dates) * len(SYMBOLS), "Chargement")

    for month, date_str, date_path in dates:
        for symbol in SYMBOLS:
            snaps = load_ml_ready(date_path, symbol)
            if snaps:
                all_data[symbol].append((date_str, snaps))
                total_snaps += len(snaps)
                for s in snaps:
                    if 'pressure_strength' in s and s['pressure_strength'] > 0:
                        has_pressure += 1
            pbar.update(1)

    pbar.close()

    print(f"\n📊 STATISTIQUES:")
    print(f"   Total snapshots: {total_snaps:,}")
    print(f"   Avec pressure_strength > 0: {has_pressure:,} ({100*has_pressure/max(1,total_snaps):.1f}%)")

    # Vérifier si des snapshots ont pressure_strength
    if has_pressure == 0:
        print("\n⚠️ ATTENTION: Aucun snapshot avec pressure_strength > 0!")
        print("   Vérifions les champs disponibles...")

        for symbol in SYMBOLS:
            if all_data[symbol]:
                _, snaps = all_data[symbol][0]
                if snaps:
                    print(f"\n   Exemple snapshot {symbol}:")
                    for k, v in list(snaps[0].items())[:20]:
                        print(f"      {k}: {v}")
                    break

        print("\n   Le champ 'pressure_strength' n'existe peut-être pas encore dans les données.")
        print("   Continuons quand même avec threshold=0 (accepte tout)...")

    # 3. Exécuter les backtests
    print(f"\n🔄 Exécution des backtests ({len(PRESSURE_THRESHOLDS)} seuils)...")

    all_results = []
    pbar = ProgressBar(len(PRESSURE_THRESHOLDS), "Backtest ")

    for threshold in PRESSURE_THRESHOLDS:
        result = run_backtest(all_data, threshold, show_progress=False)
        all_results.append(result)
        pbar.update(1)

    pbar.close()

    # 4. Afficher résultats
    print("\n" + "="*120)
    print("📊 RÉSULTATS")
    print("="*120)

    print(f"\n{'Seuil':<10} {'Signaux':<10} {'Acceptés':<10} {'Rejetés':<10} {'Trades':<8} {'Wins':<6} {'Loss':<6} {'WR%':<8} {'P&L':<15}")
    print("-"*100)

    for r in all_results:
        trades = r["trades"]
        wins = sum(1 for t in trades if t.result == "WIN")
        losses = sum(1 for t in trades if t.result == "LOSS")
        wr = (wins / len(trades) * 100) if trades else 0
        pnl = sum(t.pnl_usd for t in trades)

        pnl_str = f"${pnl:+,.2f}"
        if pnl > 0:
            pnl_str = f"✅ {pnl_str}"
        elif pnl < 0:
            pnl_str = f"❌ {pnl_str}"

        print(f"{r['threshold']:<10.2f} {r['signals']:<10} {r['accepted']:<10} {r['rejected']:<10} {len(trades):<8} {wins:<6} {losses:<6} {wr:<8.1f} {pnl_str}")

    # 5. Recommandation
    print("\n" + "="*120)
    print("🏆 RECOMMANDATION")
    print("="*120)

    # Trouver le meilleur
    valid = [r for r in all_results if len(r["trades"]) >= 3]
    if valid:
        best = max(valid, key=lambda x: sum(t.pnl_usd for t in x["trades"]))
        trades = best["trades"]
        wins = sum(1 for t in trades if t.result == "WIN")
        pnl = sum(t.pnl_usd for t in trades)
        wr = wins / len(trades) * 100 if trades else 0

        print(f"\n✅ MEILLEUR SEUIL: {best['threshold']:.2f}")
        print(f"   P&L: ${pnl:+,.2f}")
        print(f"   Win Rate: {wr:.1f}%")
        print(f"   Trades: {len(trades)}")
    else:
        print("\n⚠️ Pas assez de trades pour recommander un seuil")

    if args.test:
        print(f"\n💡 C'était un TEST sur {len(dates)} jour(s).")
        print(f"   Pour le backtest complet, lancez: python {Path(__file__).name} --full")

    print("\n" + "="*120)
    print("✅ BACKTEST TERMINÉ")
    print("="*120)


if __name__ == "__main__":
    main()
