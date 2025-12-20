"""
🎯 BACKTEST SEMAINE COMPLÈTE - CONDITIONS RÉELLES DU BOT
=========================================================

Rejoue la semaine 02-06 Décembre 2025 avec TOUS les filtres:
✅ Sessions de trading (London, US Morning, Power Hour)
✅ Seuils ML 3-Layer (Layer1, Layer2, Layer3)
✅ Distances aux niveaux MenthorQ
✅ Confluence et scores
✅ Pressure_strength par session (NOUVEAU)
✅ Cooldown entre trades
✅ TP/SL réalistes

Date: 06/12/2025
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# CONFIGURATION PRODUCTION EXACTE (unified_thresholds.py)
# ============================================================================

# Seuils ML 3-Layer (mode production 05/12/2025)
MIN_TOTAL_CONFIDENCE = {'ES': 0.30, 'NQ': 0.30, 'RTY': 0.42}

MIN_LAYER_CONFIDENCE = {
    'ES': {'layer1': 0.50, 'layer2': 0.17, 'layer3': 0.14},
    'NQ': {'layer1': 0.30, 'layer2': 0.20, 'layer3': 0.16},
    'RTY': {'layer1': 0.30, 'layer2': 0.20, 'layer3': 0.20}
}

# Distances maximales aux niveaux
MAX_DISTANCE_TO_LEVEL = {'ES': 15, 'NQ': 25, 'RTY': 20}

# 🆕 Pressure strength par session (backtest 06/12/2025)
MIN_PRESSURE_BY_SESSION = {
    'London': 0.10,
    'US Morning': 0.03,
    'US Power Hour': 0.10,
    'ASIA': 0.50,
    'Pre-US': 0.50,
    'Lunch': 0.50,
    'Closed': 0.50,
}

# TP/SL configuration
TP_SL_CONFIG = {
    'ES': {'tp_ticks': 30, 'sl_ticks': 22},  # Config optimisée 27/11
    'NQ': {'tp_ticks': 60, 'sl_ticks': 40},
    'RTY': {'tp_ticks': 45, 'sl_ticks': 30}
}

TICK_VALUES = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}
TICK_SIZES = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}

# Sessions (heure Paris)
TRADING_SESSIONS = {
    "London": {"start": (8, 0), "end": (11, 0)},
    "US Morning": {"start": (15, 50), "end": (17, 0)},
    "US Power Hour": {"start": (20, 0), "end": (21, 30)}
}

COOLDOWN_MS = 300000  # 5 minutes
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE")
CHART_MAPPING = {'ES': 3, 'NQ': 9, 'RTY': 1}
SYMBOLS = ["ES", "NQ"]

# Dates de la semaine à tester
WEEK_DATES = ["20251202", "20251203", "20251204", "20251205"]

# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class MLScores:
    layer1: float = 0.0
    layer2: float = 0.0
    layer3: float = 0.0
    total: float = 0.0

    def meets_thresholds(self, symbol: str) -> Tuple[bool, str]:
        """Vérifie si les scores passent les seuils"""
        min_l1 = MIN_LAYER_CONFIDENCE.get(symbol, {}).get('layer1', 0.30)
        min_l2 = MIN_LAYER_CONFIDENCE.get(symbol, {}).get('layer2', 0.15)
        min_l3 = MIN_LAYER_CONFIDENCE.get(symbol, {}).get('layer3', 0.10)
        min_total = MIN_TOTAL_CONFIDENCE.get(symbol, 0.30)

        if self.layer1 < min_l1:
            return False, f"L1 {self.layer1:.2f} < {min_l1:.2f}"
        if self.layer2 < min_l2:
            return False, f"L2 {self.layer2:.2f} < {min_l2:.2f}"
        if self.layer3 < min_l3:
            return False, f"L3 {self.layer3:.2f} < {min_l3:.2f}"
        if self.total < min_total:
            return False, f"Total {self.total:.2f} < {min_total:.2f}"
        return True, "OK"

@dataclass
class Signal:
    timestamp: int
    symbol: str
    direction: str
    price: float
    session: str
    ml_scores: MLScores
    pressure_strength: float
    distance_to_level: float
    nearest_level: str
    delta: float

@dataclass
class TradeResult:
    signal: Signal
    result: str  # WIN, LOSS, BE
    pnl_ticks: float
    pnl_usd: float
    exit_reason: str

@dataclass
class BacktestStats:
    signals_total: int = 0
    signals_in_session: int = 0
    rejected_ml: int = 0
    rejected_distance: int = 0
    rejected_pressure: int = 0
    rejected_cooldown: int = 0
    trades_executed: int = 0
    wins: int = 0
    losses: int = 0
    be: int = 0
    pnl_total: float = 0.0
    by_session: Dict = field(default_factory=lambda: defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0}))
    by_symbol: Dict = field(default_factory=lambda: defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0}))
    by_date: Dict = field(default_factory=lambda: defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0}))

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


def load_snapshots(date_str: str, symbol: str) -> List[Dict]:
    """Charge les snapshots ML_READY pour une date et symbole"""
    chart_id = CHART_MAPPING.get(symbol)
    path = BASE_PATH / date_str / f"CHART_{chart_id}" / "ML_READY"

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


def get_session(ts_ms: int) -> Tuple[bool, str]:
    """Retourne la session pour un timestamp"""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    h_paris = (dt.hour + 1) % 24  # UTC+1 approximation
    m = dt.minute

    # London (08:00-11:00)
    if 8 <= h_paris < 11:
        return True, "London"
    # US Morning (15:50-17:00)
    elif (h_paris == 15 and m >= 50) or h_paris == 16:
        return True, "US Morning"
    # US Power Hour (20:00-21:30)
    elif h_paris == 20 or (h_paris == 21 and m < 30):
        return True, "US Power Hour"
    else:
        return False, "Closed"


def get_distance_to_level(snap: Dict, price: float, symbol: str) -> Tuple[float, str]:
    """Calcule distance au niveau le plus proche"""
    tick = TICK_SIZES.get(symbol, 0.25)
    levels = []

    # Niveaux priorité haute
    for key in ['hvl', 'vah', 'val', 'poc', '1d_max', '1d_min']:
        val = snap.get(key)
        if val and val > 0:
            levels.append((abs(price - val) / tick, key))

    # Gamma walls
    for key in ['call_resistance', 'put_support']:
        val = snap.get(key)
        if val and val > 0:
            levels.append((abs(price - val) / tick, key))

    # GEX levels
    for i in range(1, 11):
        val = snap.get(f'gex_{i}')
        if val and val > 0:
            levels.append((abs(price - val) / tick, f'gex_{i}'))

    # Blind spots
    for i in range(0, 9):
        val = snap.get(f'blind_spot_{i}')
        if val and val > 0:
            levels.append((abs(price - val) / tick, f'blind_spot_{i}'))

    # VWAP
    val = snap.get('vwap')
    if val and val > 0:
        levels.append((abs(price - val) / tick, 'vwap'))

    if not levels:
        return 9999, "none"

    levels.sort(key=lambda x: x[0])
    return levels[0]


def calculate_ml_scores(snap: Dict, symbol: str) -> MLScores:
    """Calcule les scores ML comme le bot"""
    # Essayer d'abord les scores pré-calculés
    l1 = snap.get('layer1_score') or snap.get('menthorq_score', 0)
    l2 = snap.get('layer2_score') or snap.get('orderflow_score', 0)
    l3 = snap.get('layer3_score') or snap.get('context_score', 0)

    # Si pas de scores, approximer
    if l1 == 0 and l2 == 0 and l3 == 0:
        # Layer 1: basé sur présence de niveaux proches
        mid = snap.get('mid', 0)
        dist, _ = get_distance_to_level(snap, mid, symbol)
        l1 = max(0, min(1, 1 - dist / 100)) if dist < 9999 else 0.2

        # Layer 2: basé sur delta et pressure
        delta = abs(snap.get('delta', 0))
        pressure = snap.get('pressure_strength', 0)
        l2 = max(0, min(1, delta / 500 + pressure * 0.5))

        # Layer 3: basé sur VWAP distance
        vwap = snap.get('vwap')
        if vwap and mid:
            vwap_dist = abs(mid - vwap) / TICK_SIZES.get(symbol, 0.25)
            l3 = max(0, min(1, 1 - vwap_dist / 50))
        else:
            l3 = 0.3

    # Total pondéré (50% L1 + 30% L2 + 20% L3)
    total = l1 * 0.5 + l2 * 0.3 + l3 * 0.2

    return MLScores(layer1=l1, layer2=l2, layer3=l3, total=total)


def validate_signal(snap: Dict, symbol: str, use_pressure_filter: bool) -> Tuple[Optional[Signal], str]:
    """
    Valide un signal avec TOUS les filtres du bot.
    Retourne (Signal ou None, raison_rejet)
    """
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)
    pressure = snap.get('pressure_strength', 0)

    if not ts or not mid:
        return None, "no_price"

    # 1. FILTRE SESSION
    in_session, session = get_session(ts)
    if not in_session:
        return None, f"out_of_session"

    # 2. FILTRE DIRECTION (delta != 0)
    if delta == 0:
        return None, "delta_zero"
    direction = "LONG" if delta > 0 else "SHORT"

    # 3. FILTRE ML SCORES
    ml_scores = calculate_ml_scores(snap, symbol)
    ml_ok, ml_reason = ml_scores.meets_thresholds(symbol)
    if not ml_ok:
        return None, f"ml_{ml_reason}"

    # 4. FILTRE DISTANCE
    distance, nearest = get_distance_to_level(snap, mid, symbol)
    max_dist = MAX_DISTANCE_TO_LEVEL.get(symbol, 20)
    if distance > max_dist:
        return None, f"distance_{distance:.0f}t"

    # 5. 🆕 FILTRE PRESSURE_STRENGTH PAR SESSION
    if use_pressure_filter:
        min_pressure = MIN_PRESSURE_BY_SESSION.get(session, 0.10)
        if pressure < min_pressure:
            return None, f"pressure_{pressure:.3f}<{min_pressure}"

    return Signal(
        timestamp=ts,
        symbol=symbol,
        direction=direction,
        price=mid,
        session=session,
        ml_scores=ml_scores,
        pressure_strength=pressure,
        distance_to_level=distance,
        nearest_level=nearest,
        delta=delta
    ), "OK"


def simulate_trade(signal: Signal, subsequent: List[Dict]) -> TradeResult:
    """Simule TP/SL"""
    cfg = TP_SL_CONFIG.get(signal.symbol, TP_SL_CONFIG['ES'])
    tv = TICK_VALUES.get(signal.symbol, 12.50)
    ts = TICK_SIZES.get(signal.symbol, 0.25)

    if signal.direction == "LONG":
        tp = signal.price + cfg['tp_ticks'] * ts
        sl = signal.price - cfg['sl_ticks'] * ts
    else:
        tp = signal.price - cfg['tp_ticks'] * ts
        sl = signal.price + cfg['sl_ticks'] * ts

    max_duration_ms = 30 * 60 * 1000

    for snap in subsequent[:1000]:
        if snap.get('t_ms', 0) - signal.timestamp > max_duration_ms:
            break

        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))

        if signal.direction == "LONG":
            if high >= tp:
                return TradeResult(signal, "WIN", cfg['tp_ticks'], cfg['tp_ticks'] * tv, "TP_HIT")
            if low <= sl:
                return TradeResult(signal, "LOSS", -cfg['sl_ticks'], -cfg['sl_ticks'] * tv, "SL_HIT")
        else:
            if low <= tp:
                return TradeResult(signal, "WIN", cfg['tp_ticks'], cfg['tp_ticks'] * tv, "TP_HIT")
            if high >= sl:
                return TradeResult(signal, "LOSS", -cfg['sl_ticks'], -cfg['sl_ticks'] * tv, "SL_HIT")

    return TradeResult(signal, "BE", 0, 0, "TIMEOUT")


def run_backtest(all_data: Dict, use_pressure_filter: bool) -> BacktestStats:
    """Exécute le backtest complet"""
    stats = BacktestStats()

    for symbol in SYMBOLS:
        last_trade_time = 0

        for date_str, snaps in all_data.get(symbol, []):
            for i, snap in enumerate(snaps):
                stats.signals_total += 1

                # Valider signal
                signal, reason = validate_signal(snap, symbol, use_pressure_filter)

                if signal is None:
                    if "session" not in reason:
                        stats.signals_in_session += 1
                    if "ml_" in reason:
                        stats.rejected_ml += 1
                    elif "distance" in reason:
                        stats.rejected_distance += 1
                    elif "pressure" in reason:
                        stats.rejected_pressure += 1
                    continue

                stats.signals_in_session += 1

                # Cooldown
                if signal.timestamp - last_trade_time < COOLDOWN_MS:
                    stats.rejected_cooldown += 1
                    continue

                last_trade_time = signal.timestamp

                # Simuler trade
                subsequent = snaps[i+1:i+1001]
                trade = simulate_trade(signal, subsequent)

                # Stats
                stats.trades_executed += 1
                stats.pnl_total += trade.pnl_usd

                if trade.result == "WIN":
                    stats.wins += 1
                elif trade.result == "LOSS":
                    stats.losses += 1
                else:
                    stats.be += 1

                # Par session
                stats.by_session[signal.session]["trades"] += 1
                stats.by_session[signal.session]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    stats.by_session[signal.session]["wins"] += 1

                # Par symbole
                stats.by_symbol[symbol]["trades"] += 1
                stats.by_symbol[symbol]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    stats.by_symbol[symbol]["wins"] += 1

                # Par date
                stats.by_date[date_str]["trades"] += 1
                stats.by_date[date_str]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    stats.by_date[date_str]["wins"] += 1

    return stats


def print_comparison(stats_sans: BacktestStats, stats_avec: BacktestStats):
    """Affiche la comparaison des résultats"""

    print("\n" + "="*120)
    print("📊 COMPARAISON: SANS vs AVEC FILTRE PRESSURE_STRENGTH")
    print("="*120)

    # Résumé global
    print(f"\n{'Métrique':<25} {'SANS Filtre':<20} {'AVEC Filtre':<20} {'Différence':<20}")
    print("-"*85)

    wr_sans = stats_sans.wins / max(stats_sans.trades_executed, 1) * 100
    wr_avec = stats_avec.wins / max(stats_avec.trades_executed, 1) * 100

    print(f"{'Trades exécutés':<25} {stats_sans.trades_executed:<20} {stats_avec.trades_executed:<20} {stats_avec.trades_executed - stats_sans.trades_executed:+d}")
    print(f"{'Wins':<25} {stats_sans.wins:<20} {stats_avec.wins:<20} {stats_avec.wins - stats_sans.wins:+d}")
    print(f"{'Losses':<25} {stats_sans.losses:<20} {stats_avec.losses:<20} {stats_avec.losses - stats_sans.losses:+d}")
    print(f"{'Win Rate':<25} {wr_sans:<20.1f}% {wr_avec:<20.1f}% {wr_avec - wr_sans:+.1f}%")
    print(f"{'P&L Total':<25} ${stats_sans.pnl_total:<19,.2f} ${stats_avec.pnl_total:<19,.2f} ${stats_avec.pnl_total - stats_sans.pnl_total:+,.2f}")
    print(f"{'Rejetés (pressure)':<25} {stats_sans.rejected_pressure:<20} {stats_avec.rejected_pressure:<20}")

    # Par session
    print("\n" + "="*120)
    print("📊 COMPARAISON PAR SESSION")
    print("="*120)

    for session in ["London", "US Morning", "US Power Hour"]:
        s_sans = stats_sans.by_session[session]
        s_avec = stats_avec.by_session[session]

        wr_s = s_sans["wins"] / max(s_sans["trades"], 1) * 100
        wr_a = s_avec["wins"] / max(s_avec["trades"], 1) * 100

        print(f"\n🕐 {session}:")
        print(f"   SANS: {s_sans['trades']} trades, {s_sans['wins']} wins, {wr_s:.1f}% WR, ${s_sans['pnl']:+,.2f}")
        print(f"   AVEC: {s_avec['trades']} trades, {s_avec['wins']} wins, {wr_a:.1f}% WR, ${s_avec['pnl']:+,.2f}")
        diff = s_avec['pnl'] - s_sans['pnl']
        icon = "✅" if diff >= 0 else "❌"
        print(f"   DIFF: {icon} ${diff:+,.2f}")

    # Par jour
    print("\n" + "="*120)
    print("📊 COMPARAISON PAR JOUR")
    print("="*120)

    print(f"\n{'Date':<12} {'SANS Trades':<12} {'SANS P&L':<15} {'AVEC Trades':<12} {'AVEC P&L':<15} {'Diff P&L':<15}")
    print("-"*85)

    for date in sorted(set(list(stats_sans.by_date.keys()) + list(stats_avec.by_date.keys()))):
        s_sans = stats_sans.by_date[date]
        s_avec = stats_avec.by_date[date]
        diff = s_avec['pnl'] - s_sans['pnl']
        icon = "✅" if diff >= 0 else "❌"
        print(f"{date:<12} {s_sans['trades']:<12} ${s_sans['pnl']:<14,.2f} {s_avec['trades']:<12} ${s_avec['pnl']:<14,.2f} {icon} ${diff:+,.2f}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*120)
    print("🎯 BACKTEST SEMAINE COMPLÈTE - CONDITIONS RÉELLES DU BOT")
    print("="*120)
    print(f"\n📅 Période: 02-05 Décembre 2025 (4 jours)")
    print(f"📊 Symboles: {SYMBOLS}")
    print(f"\n📋 FILTRES ACTIFS:")
    print(f"   • Sessions: London (8h-11h), US Morning (15h50-17h), Power Hour (20h-21h30)")
    print(f"   • ML Seuils: ES L1≥0.50, L2≥0.17, L3≥0.14 | NQ L1≥0.30, L2≥0.20, L3≥0.16")
    print(f"   • Distance max: ES≤15t, NQ≤25t")
    print(f"   • Cooldown: 5 min")
    print(f"   • 🆕 Pressure: London≥0.10, US Morning≥0.03, Power Hour≥0.10")

    # Charger données
    print(f"\n📥 Chargement des données...")
    all_data = {s: [] for s in SYMBOLS}
    total_snaps = 0

    pbar = ProgressBar(len(WEEK_DATES) * len(SYMBOLS), "Load")
    for date in WEEK_DATES:
        for symbol in SYMBOLS:
            snaps = load_snapshots(date, symbol)
            if snaps:
                all_data[symbol].append((date, snaps))
                total_snaps += len(snaps)
            pbar.update()
    pbar.close()

    print(f"   Total: {total_snaps:,} snapshots")

    # Backtest SANS filtre pressure
    print(f"\n🔄 Backtest SANS filtre pressure_strength...")
    start = time.time()
    stats_sans = run_backtest(all_data, use_pressure_filter=False)
    print(f"   ✅ Terminé en {time.time()-start:.1f}s")

    # Backtest AVEC filtre pressure
    print(f"\n🔄 Backtest AVEC filtre pressure_strength...")
    start = time.time()
    stats_avec = run_backtest(all_data, use_pressure_filter=True)
    print(f"   ✅ Terminé en {time.time()-start:.1f}s")

    # Afficher comparaison
    print_comparison(stats_sans, stats_avec)

    # Recommandation finale
    diff_pnl = stats_avec.pnl_total - stats_sans.pnl_total
    diff_wr = (stats_avec.wins / max(stats_avec.trades_executed, 1) -
               stats_sans.wins / max(stats_sans.trades_executed, 1)) * 100

    print("\n" + "="*120)
    print("🏆 VERDICT FINAL")
    print("="*120)

    if diff_pnl > 0:
        print(f"\n✅ Le filtre PRESSURE_STRENGTH AMÉLIORE les résultats:")
        print(f"   • P&L: +${diff_pnl:,.2f}")
        print(f"   • Win Rate: +{diff_wr:.1f}%")
        print(f"   • Trades bloqués par pressure: {stats_avec.rejected_pressure}")
        print(f"\n   ➡️ RECOMMANDATION: ACTIVER le filtre pour lundi ! 🚀")
    else:
        print(f"\n⚠️ Le filtre PRESSURE_STRENGTH DÉGRADE les résultats:")
        print(f"   • P&L: ${diff_pnl:,.2f}")
        print(f"   • Win Rate: {diff_wr:.1f}%")
        print(f"\n   ➡️ RECOMMANDATION: Vérifier les seuils ou désactiver")

    print("\n" + "="*120)


if __name__ == "__main__":
    main()
