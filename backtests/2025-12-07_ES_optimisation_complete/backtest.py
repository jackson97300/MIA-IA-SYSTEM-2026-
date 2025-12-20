"""
🎯 OPTIMISATION COMPLÈTE ES - TROUVER TOUS LES PARAMÈTRES OPTIMAUX
===================================================================

Analyse en profondeur de TOUTES les données collectées pour trouver
la configuration optimale pour ES.

Distance gardée à 15t comme demandé.

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
from itertools import product

PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKTESTS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKTESTS_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from config.backtest_config import (
    TICK_VALUES, TICK_SIZES, COOLDOWN_MS, MAX_TRADE_DURATION_MS,
    MAX_SNAPSHOTS_LOOKAHEAD, get_session, get_distance_to_level, load_snapshots
)

# ============================================================================
# CONFIGURATION
# ============================================================================

DATE_RANGE = ["20251202", "20251203", "20251204", "20251205"]
DATA_MONTH = "DECEMBRE"
DATA_YEAR = 2025
SYMBOL = "ES"
MAX_DISTANCE = 15  # Fixé à 15 ticks

# ============================================================================
# PARAMÈTRES À OPTIMISER
# ============================================================================

# TP/SL à tester
TP_VALUES = [15, 18, 20, 22, 25, 28, 30, 35]
SL_VALUES = [12, 15, 18, 20, 22, 25]

# Delta minimum à tester
DELTA_MIN_VALUES = [0, 50, 100, 150, 200, 250, 300, 400]

# Pressure minimum à tester
PRESSURE_MIN_VALUES = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

# Seuils Layer à tester
LAYER1_MIN_VALUES = [0.30, 0.40, 0.50, 0.60]
LAYER2_MIN_VALUES = [0.10, 0.15, 0.20, 0.25]
LAYER3_MIN_VALUES = [0.10, 0.14, 0.18, 0.22]

# Directions à tester
DIRECTIONS = ["BOTH", "LONG_ONLY", "SHORT_ONLY"]

# Sessions à tester
SESSIONS_CONFIGS = [
    {"name": "ALL", "sessions": ["London", "US Morning", "US Power Hour"]},
    {"name": "NO_LONDON", "sessions": ["US Morning", "US Power Hour"]},
    {"name": "US_ONLY", "sessions": ["US Morning"]},
    {"name": "POWER_ONLY", "sessions": ["US Power Hour"]},
    {"name": "US_MORNING_POWER", "sessions": ["US Morning", "US Power Hour"]},
]

# ============================================================================
# CLASSES
# ============================================================================

@dataclass
class TradeData:
    timestamp: int
    direction: str
    entry_price: float
    session: str
    delta: float
    pressure: float
    distance: float
    layer1: float
    layer2: float
    layer3: float
    total_conf: float
    subsequent_snaps: List[Dict] = field(default_factory=list)

@dataclass
class BacktestResult:
    config_name: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float

# ============================================================================
# FONCTIONS
# ============================================================================

def calculate_ml_scores(snap: Dict) -> Tuple[float, float, float, float]:
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
    return l1, l2, l3, total


def extract_all_potential_trades(all_snaps: List[Tuple]) -> List[TradeData]:
    """Extrait TOUS les trades potentiels avec leurs données complètes"""
    trades = []
    last_trade_time = 0

    for date, idx, snap in all_snaps:
        ts = snap.get('t_ms', 0)
        mid = snap.get('mid', 0)
        delta = snap.get('delta', 0)
        pressure = snap.get('pressure_strength', 0)

        if not ts or not mid or delta == 0:
            continue

        # Cooldown
        if ts - last_trade_time < COOLDOWN_MS:
            continue

        in_session, session = get_session(ts)
        if not in_session:
            continue

        distance, level_name = get_distance_to_level(snap, mid, SYMBOL)
        if distance > MAX_DISTANCE:
            continue

        l1, l2, l3, total = calculate_ml_scores(snap)
        direction = "LONG" if delta > 0 else "SHORT"

        # Récupérer les snapshots suivants
        subsequent = [s for d, i, s in all_snaps if d == date and i > idx][:MAX_SNAPSHOTS_LOOKAHEAD]

        trade = TradeData(
            timestamp=ts,
            direction=direction,
            entry_price=mid,
            session=session,
            delta=abs(delta),
            pressure=pressure,
            distance=distance,
            layer1=l1,
            layer2=l2,
            layer3=l3,
            total_conf=total,
            subsequent_snaps=subsequent
        )
        trades.append(trade)
        last_trade_time = ts

    return trades


def simulate_trade(trade: TradeData, tp_ticks: int, sl_ticks: int) -> Tuple[str, float]:
    """Simule un trade et retourne (result, pnl_usd)"""
    tv = TICK_VALUES.get(SYMBOL)
    ts = TICK_SIZES.get(SYMBOL)

    entry = trade.entry_price
    if trade.direction == "LONG":
        tp = entry + tp_ticks * ts
        sl = entry - sl_ticks * ts
    else:
        tp = entry - tp_ticks * ts
        sl = entry + sl_ticks * ts

    for snap in trade.subsequent_snaps:
        if snap.get('t_ms', 0) - trade.timestamp > MAX_TRADE_DURATION_MS:
            break

        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))

        if trade.direction == "LONG":
            if high >= tp:
                return "WIN", tp_ticks * tv
            if low <= sl:
                return "LOSS", -sl_ticks * tv
        else:
            if low <= tp:
                return "WIN", tp_ticks * tv
            if high >= sl:
                return "LOSS", -sl_ticks * tv

    return "BE", 0


def run_backtest_config(trades: List[TradeData], config: Dict) -> BacktestResult:
    """Exécute un backtest avec une configuration spécifique"""
    tp = config['tp']
    sl = config['sl']
    delta_min = config['delta_min']
    pressure_min = config['pressure_min']
    l1_min = config['l1_min']
    l2_min = config['l2_min']
    l3_min = config['l3_min']
    direction_filter = config['direction']
    allowed_sessions = config['sessions']

    results = []

    for trade in trades:
        # Filtres
        if trade.session not in allowed_sessions:
            continue
        if trade.delta < delta_min:
            continue
        if trade.pressure < pressure_min:
            continue
        if trade.layer1 < l1_min:
            continue
        if trade.layer2 < l2_min:
            continue
        if trade.layer3 < l3_min:
            continue
        if direction_filter == "LONG_ONLY" and trade.direction != "LONG":
            continue
        if direction_filter == "SHORT_ONLY" and trade.direction != "SHORT":
            continue

        result, pnl = simulate_trade(trade, tp, sl)
        results.append((result, pnl))

    if not results:
        return BacktestResult(config['name'], 0, 0, 0, 0, 0, 0, 0, 0)

    wins = [r for r in results if r[0] == "WIN"]
    losses = [r for r in results if r[0] == "LOSS"]

    total_win = sum(r[1] for r in wins)
    total_loss = abs(sum(r[1] for r in losses))

    return BacktestResult(
        config_name=config['name'],
        trades=len(results),
        wins=len(wins),
        losses=len(losses),
        win_rate=len(wins) / len(results) * 100 if results else 0,
        pnl=sum(r[1] for r in results),
        avg_win=total_win / len(wins) if wins else 0,
        avg_loss=total_loss / len(losses) if losses else 0,
        profit_factor=total_win / total_loss if total_loss > 0 else 0
    )


def main():
    print("="*120)
    print("🎯 OPTIMISATION COMPLÈTE ES - RECHERCHE PARAMÈTRES OPTIMAUX")
    print("="*120)
    print(f"\n📅 Période: {DATE_RANGE[0]} → {DATE_RANGE[-1]} (4 jours)")
    print(f"📊 Symbole: {SYMBOL}")
    print(f"📏 Distance max: {MAX_DISTANCE} ticks (fixé)")

    # Charger données
    print(f"\n📥 Chargement des données...")
    all_snaps = []
    for date in DATE_RANGE:
        snaps = load_snapshots(date, SYMBOL, DATA_MONTH, DATA_YEAR)
        if snaps:
            all_snaps.extend([(date, i, s) for i, s in enumerate(snaps)])

    print(f"   Total snapshots: {len(all_snaps):,}")

    # Extraire tous les trades potentiels
    print(f"\n🔄 Extraction des trades potentiels...")
    all_trades = extract_all_potential_trades(all_snaps)
    print(f"   Trades potentiels: {len(all_trades)}")

    # =========================================================================
    # PHASE 1: Optimisation TP/SL
    # =========================================================================
    print(f"\n{'='*120}")
    print("📊 PHASE 1: OPTIMISATION TP/SL")
    print("="*120)

    tp_sl_results = []
    base_config = {
        'delta_min': 0, 'pressure_min': 0,
        'l1_min': 0.30, 'l2_min': 0.10, 'l3_min': 0.10,
        'direction': 'BOTH',
        'sessions': ["London", "US Morning", "US Power Hour"]
    }

    for tp in TP_VALUES:
        for sl in SL_VALUES:
            if tp <= sl:  # TP doit être > SL pour un RR positif
                continue
            config = {**base_config, 'tp': tp, 'sl': sl, 'name': f"TP{tp}_SL{sl}"}
            result = run_backtest_config(all_trades, config)
            if result.trades > 0:
                tp_sl_results.append(result)

    tp_sl_results.sort(key=lambda x: x.pnl, reverse=True)

    print(f"\n🏆 TOP 10 TP/SL:")
    print(f"{'Config':<15} {'Trades':<8} {'Wins':<8} {'WR%':<8} {'P&L':<12} {'PF':<8}")
    print("-"*65)
    for r in tp_sl_results[:10]:
        icon = "✅" if r.pnl > 0 else "❌"
        print(f"{icon} {r.config_name:<13} {r.trades:<8} {r.wins:<8} {r.win_rate:<8.1f} ${r.pnl:<11,.2f} {r.profit_factor:<8.2f}")

    best_tp_sl = tp_sl_results[0] if tp_sl_results else None
    best_tp = int(best_tp_sl.config_name.split('_')[0].replace('TP', '')) if best_tp_sl else 25
    best_sl = int(best_tp_sl.config_name.split('_')[1].replace('SL', '')) if best_tp_sl else 18

    # =========================================================================
    # PHASE 2: Optimisation Delta
    # =========================================================================
    print(f"\n{'='*120}")
    print("📊 PHASE 2: OPTIMISATION DELTA MINIMUM")
    print("="*120)

    delta_results = []
    for delta_min in DELTA_MIN_VALUES:
        config = {
            **base_config,
            'tp': best_tp, 'sl': best_sl,
            'delta_min': delta_min,
            'name': f"DELTA_{delta_min}"
        }
        result = run_backtest_config(all_trades, config)
        if result.trades > 0:
            delta_results.append((delta_min, result))

    print(f"\n{'Delta Min':<12} {'Trades':<8} {'Wins':<8} {'WR%':<8} {'P&L':<12}")
    print("-"*50)
    for delta_min, r in sorted(delta_results, key=lambda x: x[1].pnl, reverse=True):
        icon = "✅" if r.pnl > 0 else "❌"
        print(f"{icon} {delta_min:<10} {r.trades:<8} {r.wins:<8} {r.win_rate:<8.1f} ${r.pnl:<11,.2f}")

    best_delta = max(delta_results, key=lambda x: x[1].pnl)[0] if delta_results else 0

    # =========================================================================
    # PHASE 3: Optimisation Pressure
    # =========================================================================
    print(f"\n{'='*120}")
    print("📊 PHASE 3: OPTIMISATION PRESSURE MINIMUM")
    print("="*120)

    pressure_results = []
    for pressure_min in PRESSURE_MIN_VALUES:
        config = {
            **base_config,
            'tp': best_tp, 'sl': best_sl,
            'delta_min': best_delta,
            'pressure_min': pressure_min,
            'name': f"PRESS_{pressure_min}"
        }
        result = run_backtest_config(all_trades, config)
        if result.trades > 0:
            pressure_results.append((pressure_min, result))

    print(f"\n{'Pressure Min':<14} {'Trades':<8} {'Wins':<8} {'WR%':<8} {'P&L':<12}")
    print("-"*52)
    for pressure_min, r in sorted(pressure_results, key=lambda x: x[1].pnl, reverse=True):
        icon = "✅" if r.pnl > 0 else "❌"
        print(f"{icon} {pressure_min:<12.2f} {r.trades:<8} {r.wins:<8} {r.win_rate:<8.1f} ${r.pnl:<11,.2f}")

    best_pressure = max(pressure_results, key=lambda x: x[1].pnl)[0] if pressure_results else 0.10

    # =========================================================================
    # PHASE 4: Optimisation Direction
    # =========================================================================
    print(f"\n{'='*120}")
    print("📊 PHASE 4: OPTIMISATION DIRECTION")
    print("="*120)

    direction_results = []
    for direction in DIRECTIONS:
        config = {
            **base_config,
            'tp': best_tp, 'sl': best_sl,
            'delta_min': best_delta,
            'pressure_min': best_pressure,
            'direction': direction,
            'name': direction
        }
        result = run_backtest_config(all_trades, config)
        if result.trades > 0:
            direction_results.append((direction, result))

    print(f"\n{'Direction':<15} {'Trades':<8} {'Wins':<8} {'WR%':<8} {'P&L':<12}")
    print("-"*55)
    for direction, r in sorted(direction_results, key=lambda x: x[1].pnl, reverse=True):
        icon = "✅" if r.pnl > 0 else "❌"
        print(f"{icon} {direction:<13} {r.trades:<8} {r.wins:<8} {r.win_rate:<8.1f} ${r.pnl:<11,.2f}")

    best_direction = max(direction_results, key=lambda x: x[1].pnl)[0] if direction_results else "BOTH"

    # =========================================================================
    # PHASE 5: Optimisation Sessions
    # =========================================================================
    print(f"\n{'='*120}")
    print("📊 PHASE 5: OPTIMISATION SESSIONS")
    print("="*120)

    session_results = []
    for sess_config in SESSIONS_CONFIGS:
        config = {
            **base_config,
            'tp': best_tp, 'sl': best_sl,
            'delta_min': best_delta,
            'pressure_min': best_pressure,
            'direction': best_direction,
            'sessions': sess_config['sessions'],
            'name': sess_config['name']
        }
        result = run_backtest_config(all_trades, config)
        if result.trades > 0:
            session_results.append((sess_config['name'], result))

    print(f"\n{'Sessions':<20} {'Trades':<8} {'Wins':<8} {'WR%':<8} {'P&L':<12}")
    print("-"*60)
    for sess_name, r in sorted(session_results, key=lambda x: x[1].pnl, reverse=True):
        icon = "✅" if r.pnl > 0 else "❌"
        print(f"{icon} {sess_name:<18} {r.trades:<8} {r.wins:<8} {r.win_rate:<8.1f} ${r.pnl:<11,.2f}")

    best_sessions_name = max(session_results, key=lambda x: x[1].pnl)[0] if session_results else "ALL"
    best_sessions = next((s['sessions'] for s in SESSIONS_CONFIGS if s['name'] == best_sessions_name),
                         ["London", "US Morning", "US Power Hour"])

    # =========================================================================
    # PHASE 6: Optimisation Layers ML
    # =========================================================================
    print(f"\n{'='*120}")
    print("📊 PHASE 6: OPTIMISATION SEUILS ML LAYERS")
    print("="*120)

    layer_results = []
    # Test combinaisons (limité pour éviter explosion)
    for l1 in LAYER1_MIN_VALUES:
        for l2 in LAYER2_MIN_VALUES:
            for l3 in LAYER3_MIN_VALUES:
                config = {
                    'tp': best_tp, 'sl': best_sl,
                    'delta_min': best_delta,
                    'pressure_min': best_pressure,
                    'l1_min': l1, 'l2_min': l2, 'l3_min': l3,
                    'direction': best_direction,
                    'sessions': best_sessions,
                    'name': f"L1_{l1}_L2_{l2}_L3_{l3}"
                }
                result = run_backtest_config(all_trades, config)
                if result.trades >= 5:  # Minimum 5 trades pour être significatif
                    layer_results.append((l1, l2, l3, result))

    layer_results.sort(key=lambda x: x[3].pnl, reverse=True)

    print(f"\n🏆 TOP 10 Combinaisons Layers:")
    print(f"{'L1':<6} {'L2':<6} {'L3':<6} {'Trades':<8} {'WR%':<8} {'P&L':<12}")
    print("-"*50)
    for l1, l2, l3, r in layer_results[:10]:
        icon = "✅" if r.pnl > 0 else "❌"
        print(f"{icon} {l1:<5.2f} {l2:<5.2f} {l3:<5.2f} {r.trades:<8} {r.win_rate:<8.1f} ${r.pnl:<11,.2f}")

    best_l1, best_l2, best_l3 = layer_results[0][:3] if layer_results else (0.50, 0.17, 0.14)

    # =========================================================================
    # CONFIGURATION OPTIMALE FINALE
    # =========================================================================
    print(f"\n{'='*120}")
    print("🏆 CONFIGURATION OPTIMALE ES")
    print("="*120)

    final_config = {
        'tp': best_tp, 'sl': best_sl,
        'delta_min': best_delta,
        'pressure_min': best_pressure,
        'l1_min': best_l1, 'l2_min': best_l2, 'l3_min': best_l3,
        'direction': best_direction,
        'sessions': best_sessions,
        'name': 'OPTIMAL'
    }

    final_result = run_backtest_config(all_trades, final_config)

    # Config actuelle pour comparaison
    current_config = {
        'tp': 30, 'sl': 22,
        'delta_min': 0,
        'pressure_min': 0.10,
        'l1_min': 0.50, 'l2_min': 0.17, 'l3_min': 0.14,
        'direction': 'BOTH',
        'sessions': ["London", "US Morning", "US Power Hour"],
        'name': 'ACTUEL'
    }
    current_result = run_backtest_config(all_trades, current_config)

    print(f"\n{'Paramètre':<25} {'ACTUEL':<20} {'OPTIMAL':<20}")
    print("-"*65)
    print(f"{'TP (ticks)':<25} {30:<20} {best_tp:<20}")
    print(f"{'SL (ticks)':<25} {22:<20} {best_sl:<20}")
    print(f"{'Delta minimum':<25} {0:<20} {best_delta:<20}")
    print(f"{'Pressure minimum':<25} {0.10:<20.2f} {best_pressure:<20.2f}")
    print(f"{'Layer 1 minimum':<25} {0.50:<20.2f} {best_l1:<20.2f}")
    print(f"{'Layer 2 minimum':<25} {0.17:<20.2f} {best_l2:<20.2f}")
    print(f"{'Layer 3 minimum':<25} {0.14:<20.2f} {best_l3:<20.2f}")
    print(f"{'Direction':<25} {'BOTH':<20} {best_direction:<20}")
    print(f"{'Sessions':<25} {'ALL':<20} {best_sessions_name:<20}")

    print(f"\n{'='*120}")
    print("📊 COMPARAISON RÉSULTATS")
    print("="*120)

    print(f"\n{'Métrique':<20} {'ACTUEL':<20} {'OPTIMAL':<20} {'GAIN':<20}")
    print("-"*80)
    print(f"{'Trades':<20} {current_result.trades:<20} {final_result.trades:<20} {final_result.trades - current_result.trades:+d}")
    print(f"{'Wins':<20} {current_result.wins:<20} {final_result.wins:<20} {final_result.wins - current_result.wins:+d}")
    print(f"{'Win Rate %':<20} {current_result.win_rate:<20.1f} {final_result.win_rate:<20.1f} {final_result.win_rate - current_result.win_rate:+.1f}%")
    print(f"{'P&L':<20} ${current_result.pnl:<19,.2f} ${final_result.pnl:<19,.2f} ${final_result.pnl - current_result.pnl:+,.2f}")
    print(f"{'Profit Factor':<20} {current_result.profit_factor:<20.2f} {final_result.profit_factor:<20.2f}")

    gain = final_result.pnl - current_result.pnl
    print(f"\n{'='*120}")
    if gain > 0:
        print(f"✅ GAIN POTENTIEL: +${gain:,.2f} sur 4 jours")
        print(f"   → Projection mensuelle: +${gain * 5:,.2f}")
    else:
        print(f"⚠️ Configuration optimale similaire à l'actuelle")
    print("="*120)

    # Sauvegarder
    output = {
        "audit_date": datetime.now().isoformat(),
        "symbol": SYMBOL,
        "optimal_config": {
            "TP": best_tp,
            "SL": best_sl,
            "delta_min": best_delta,
            "pressure_min": best_pressure,
            "layer1_min": best_l1,
            "layer2_min": best_l2,
            "layer3_min": best_l3,
            "direction": best_direction,
            "sessions": best_sessions,
        },
        "current_result": {
            "trades": current_result.trades,
            "wins": current_result.wins,
            "win_rate": current_result.win_rate,
            "pnl": current_result.pnl
        },
        "optimal_result": {
            "trades": final_result.trades,
            "wins": final_result.wins,
            "win_rate": final_result.win_rate,
            "pnl": final_result.pnl
        },
        "gain": gain
    }

    output_path = Path(__file__).parent / "optimal_config.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Config optimale sauvegardée: {output_path}")


if __name__ == "__main__":
    main()
