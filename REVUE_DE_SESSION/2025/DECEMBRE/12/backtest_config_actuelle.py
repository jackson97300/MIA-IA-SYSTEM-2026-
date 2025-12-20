#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    BACKTEST CONFIG ACTUELLE - 13 DEC 2025
═══════════════════════════════════════════════════════════════════════════════

Paramètres testés:
- MIN_TOTAL_CONFIDENCE: 70%
- Layer2 (OrderFlow): 17%
- ORDERFLOW_ALIGNMENT_BLOCK: OFF
- BRACKET_BLOCK: OFF
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys

# ═══════════════════════════════════════════════════════════════════════════════
#                           BARRE DE PROGRESSION
# ═══════════════════════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 40):
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r   {prefix} |{bar}| {percent*100:.1f}% {suffix}")
    sys.stdout.flush()
    if current >= total:
        print()

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

NOVEMBER_DAYS = [
    "20251105", "20251106", "20251107", "20251110", "20251111",
    "20251112", "20251113", "20251114", "20251117", "20251118",
    "20251119", "20251120", "20251121", "20251124", "20251125",
    "20251126", "20251127", "20251130",
]

DECEMBER_DAYS = [
    "20251201", "20251202", "20251203", "20251204", "20251205",
    "20251206", "20251207", "20251208", "20251209", "20251210",
    "20251211", "20251212", "20251213",
]

DAYS_TO_TEST = NOVEMBER_DAYS + DECEMBER_DAYS

SYMBOLS = {
    "ES": {
        "chart_id": 3,
        "tick_size": 0.25,
        "tick_value": 12.50,
        "contracts": ["ESZ25", "ESH25"],
    },
    "NQ": {
        "chart_id": 9,
        "tick_size": 0.25,
        "tick_value": 5.00,
        "contracts": ["NQZ25", "NQH25"],
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#                    SESSIONS TRADING
# ═══════════════════════════════════════════════════════════════════════════════

TRADING_SESSIONS = {
    'london': {'start': (8, 0), 'end': (11, 0), 'enabled': True},
    'us_morning': {'start': (15, 50), 'end': (17, 0), 'enabled': True},
    'power_hour': {'start': (20, 0), 'end': (21, 25), 'enabled': True},
}

BLOCKED_PERIODS = {
    'overnight': ((0, 0), (8, 0)),
    'pre_market': ((11, 0), (15, 50)),
    'lunch': ((17, 0), (20, 0)),
    'hard_stop': ((21, 25), (24, 0)),
}

# ═══════════════════════════════════════════════════════════════════════════════
#              🎯 PARAMÈTRES ACTUELS À TESTER
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG_ACTUELLE = {
    'name': '🎯 CONFIG 70% (TP15/SL10 = R:R 1.5:1)',

    # Seuils ML
    'min_confidence': {'ES': 0.70, 'NQ': 0.70},  # MIN_TOTAL_CONFIDENCE = 70%
    'min_layer1': {'ES': 0.40, 'NQ': 0.30},      # MenthorQ
    'min_layer2': {'ES': 0.17, 'NQ': 0.17},      # OrderFlow = 17%
    'min_layer3': {'ES': 0.14, 'NQ': 0.16},      # Context

    # Distance niveau
    'max_distance': {'ES': 8, 'NQ': 10},

    # MIA score threshold
    'mia_threshold': 0.22,

    # Cooldown
    'cooldown_min': 20,

    # Max trades
    'max_trades_per_day': 20,

    # TP/SL - R:R 1.5:1 (plus réaliste)
    'tp_ticks': 15,
    'sl_ticks': 10,

    # Pas de trailing/partial
    'use_trailing': False,
}

# Config de comparaison
CONFIG_AVANT = {
    'name': '🔴 AVANT (12/12 - trop strict)',
    'min_confidence': {'ES': 1.00, 'NQ': 1.00},  # 100% !
    'min_layer1': {'ES': 0.40, 'NQ': 0.30},
    'min_layer2': {'ES': 0.18, 'NQ': 0.18},      # 18%
    'min_layer3': {'ES': 0.14, 'NQ': 0.16},
    'max_distance': {'ES': 8, 'NQ': 10},
    'mia_threshold': 0.22,
    'cooldown_min': 20,
    'max_trades_per_day': 20,
    'tp_ticks': 15,
    'sl_ticks': 15,  # R:R 1:1
    'use_trailing': False,
}

# Config avec R:R 1:1
CONFIG_RR_1_1 = {
    'name': '📊 70% + R:R 1:1 (TP10/SL10)',
    'min_confidence': {'ES': 0.70, 'NQ': 0.70},
    'min_layer1': {'ES': 0.40, 'NQ': 0.30},
    'min_layer2': {'ES': 0.17, 'NQ': 0.17},
    'min_layer3': {'ES': 0.14, 'NQ': 0.16},
    'max_distance': {'ES': 8, 'NQ': 10},
    'mia_threshold': 0.22,
    'cooldown_min': 20,
    'max_trades_per_day': 20,
    'tp_ticks': 10,
    'sl_ticks': 10,
    'use_trailing': False,
}

# Config avec 50% confidence
CONFIG_50_PCT = {
    'name': '📊 50% + R:R 1.5:1 (TP15/SL10)',
    'min_confidence': {'ES': 0.50, 'NQ': 0.50},
    'min_layer1': {'ES': 0.40, 'NQ': 0.30},
    'min_layer2': {'ES': 0.17, 'NQ': 0.17},
    'min_layer3': {'ES': 0.14, 'NQ': 0.16},
    'max_distance': {'ES': 8, 'NQ': 10},
    'mia_threshold': 0.22,
    'cooldown_min': 20,
    'max_trades_per_day': 20,
    'tp_ticks': 15,
    'sl_ticks': 10,
    'use_trailing': False,
}

CONFIGS = {
    'ACTUELLE': CONFIG_ACTUELLE,
    'RR_1_1': CONFIG_RR_1_1,
    'CONF_50': CONFIG_50_PCT,
    'AVANT': CONFIG_AVANT,
}

# ═══════════════════════════════════════════════════════════════════════════════
#              NIVEAUX MENTHORQ
# ═══════════════════════════════════════════════════════════════════════════════

MENTHORQ_LEVELS = [
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
    'gamma_wall_0dte', 'gamma_wall_level',
    'hvl', 'hvl_0dte',
    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
    'call_resistance', 'put_support',
    'call_resistance_0dte', 'put_support_0dte',
    'vwap', 'vwap_up1', 'vwap_dn1',
]

# ═══════════════════════════════════════════════════════════════════════════════
#                           DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeResult:
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    result: str
    pnl_usd: float
    entry_time: int
    duration_sec: float
    mfe_ticks: float
    mae_ticks: float
    session: str
    day: str
    confidence: float

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_month_folder(day: str) -> str:
    return "NOVEMBRE" if day[4:6] == "11" else "DECEMBRE"


def find_data_file(day: str, symbol: str) -> Optional[Path]:
    config = SYMBOLS[symbol]
    month_folder = get_month_folder(day)
    for contract in config["contracts"]:
        path = DATA_BASE_PATH / month_folder / day / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{contract}_FUT_CME_{config['chart_id']}.jsonl"
        if path.exists():
            return path
    return None


def load_snapshots(file_path: Path) -> List[Dict]:
    snapshots = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        snapshots.append(json.loads(line))
                    except:
                        continue
    except:
        return []
    snapshots.sort(key=lambda x: x.get('t_ms', 0))
    return snapshots


def get_paris_time(t_ms: int) -> Tuple[int, int]:
    total_sec = t_ms // 1000
    total_min = total_sec // 60
    hour_utc = (total_min // 60) % 24
    minute = total_min % 60
    hour_paris = (hour_utc + 1) % 24
    return hour_paris, minute


def time_to_minutes(h: int, m: int) -> int:
    return h * 60 + m


def is_in_trading_session(hour: int, minute: int) -> Tuple[bool, str]:
    time_val = time_to_minutes(hour, minute)

    for name, (start, end) in BLOCKED_PERIODS.items():
        s = time_to_minutes(start[0], start[1])
        e = time_to_minutes(end[0], end[1])
        if s <= time_val < e:
            return False, f"BLOCKED_{name}"

    for name, session in TRADING_SESSIONS.items():
        if not session['enabled']:
            continue
        s = time_to_minutes(session['start'][0], session['start'][1])
        e = time_to_minutes(session['end'][0], session['end'][1])
        if s <= time_val < e:
            return True, name

    return False, "OFF_HOURS"


def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float, float]:
    mid = snapshot.get('mid', 0)
    tick_size = SYMBOLS[symbol]['tick_size']

    nearest_name = ""
    nearest_dist = float('inf')
    nearest_price = 0

    for level_name in MENTHORQ_LEVELS:
        price = snapshot.get(level_name)
        if price and price > 0:
            dist = abs(mid - price) / tick_size
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_name = level_name
                nearest_price = price

    return nearest_name, nearest_price, nearest_dist

# ═══════════════════════════════════════════════════════════════════════════════
#                           LOGIQUE DE SIGNAL (SIMULE ML 3-LAYER)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal(snapshot: Dict, symbol: str, config: Dict, hour: int, minute: int) -> Tuple[bool, str, float, str, Dict]:
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "NO_PRICE", {}

    in_session, session_name = is_in_trading_session(hour, minute)
    if not in_session:
        return False, "", 0, session_name, {}

    level_name, level_price, distance = find_nearest_level(snapshot, symbol)
    max_dist = config['max_distance'].get(symbol, 15)

    if distance > max_dist:
        return False, "", 0, "DIST", {'distance': distance}

    # === LAYER 1: MenthorQ (50%) ===
    menthorq_score = max(0, 1 - distance / 25)
    if level_name in ['gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap']:
        menthorq_score = min(1.0, menthorq_score * 1.25)

    layer1_conf = menthorq_score * 0.50
    min_l1 = config['min_layer1'].get(symbol, 0.40)

    # === LAYER 2: OrderFlow (30%) ===
    delta = snapshot.get('delta', 0) or 0
    cum_delta = snapshot.get('cum_delta_session', 0) or 0
    orderflow_score = min(1.0, (abs(delta) / 500 + abs(cum_delta) / 1000) / 2) * 0.5 + 0.25

    layer2_conf = orderflow_score * 0.30
    min_l2 = config['min_layer2'].get(symbol, 0.17)

    # === LAYER 3: Context (20%) ===
    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    context_score = min(1.0, abs(mia_score) * 2)

    layer3_conf = context_score * 0.20
    min_l3 = config['min_layer3'].get(symbol, 0.14)

    # === TOTAL ===
    confidence = layer1_conf + layer2_conf + layer3_conf

    # Vérifier seuils par layer
    if layer1_conf < min_l1 * 0.50:  # Layer1 contribue 50%
        return False, "", confidence, "L1_LOW", {}
    if layer2_conf < min_l2 * 0.30:  # Layer2 contribue 30%
        return False, "", confidence, "L2_LOW", {}
    if layer3_conf < min_l3 * 0.20:  # Layer3 contribue 20%
        return False, "", confidence, "L3_LOW", {}

    # Vérifier seuil total
    min_conf = config['min_confidence'].get(symbol, 0.70)
    if confidence < min_conf:
        return False, "", confidence, "CONF_LOW", {}

    # Direction basée sur mia_score
    threshold = config['mia_threshold']
    if mia_score > threshold:
        direction = "LONG"
    elif mia_score < -threshold:
        direction = "SHORT"
    else:
        return False, "", confidence, "MIA_NEUTRAL", {}

    details = {
        'confidence': confidence,
        'distance': distance,
        'level': level_name,
        'session': session_name,
        'layer1': layer1_conf,
        'layer2': layer2_conf,
        'layer3': layer3_conf,
    }

    return True, direction, confidence, "OK", details

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION DE TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], config: Dict,
                   session: str, day: str, confidence: float) -> TradeResult:

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    tp_ticks = config['tp_ticks']
    sl_ticks = config['sl_ticks']

    # Calculer niveaux
    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp = entry - tp_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp = entry + tp_ticks * tick_size

    pnl = 0
    result = "TIMEOUT"
    exit_price = entry
    exit_time = entry_time
    high_reached = entry
    low_reached = entry

    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:
            break

        high = snap.get('high') or snap.get('mid', entry)
        low = snap.get('low') or snap.get('mid', entry)

        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        if direction == "SHORT":
            # SL
            if high >= sl:
                pnl = -sl_ticks * tick_value
                result = "LOSS"
                exit_price = sl
                exit_time = t_ms
                break
            # TP
            if low <= tp:
                pnl = tp_ticks * tick_value
                result = "WIN"
                exit_price = tp
                exit_time = t_ms
                break
        else:  # LONG
            # SL
            if low <= sl:
                pnl = -sl_ticks * tick_value
                result = "LOSS"
                exit_price = sl
                exit_time = t_ms
                break
            # TP
            if high >= tp:
                pnl = tp_ticks * tick_value
                result = "WIN"
                exit_price = tp
                exit_time = t_ms
                break

    # MAE/MFE
    if direction == "LONG":
        mae = (entry - low_reached) / tick_size
        mfe = (high_reached - entry) / tick_size
    else:
        mae = (high_reached - entry) / tick_size
        mfe = (entry - low_reached) / tick_size

    return TradeResult(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        exit_price=exit_price,
        result=result,
        pnl_usd=pnl,
        entry_time=entry_time,
        duration_sec=(exit_time - entry_time) / 1000,
        mfe_ticks=mfe,
        mae_ticks=mae,
        session=session,
        day=day,
        confidence=confidence,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(config: Dict, all_data: Dict, show_progress: bool = False) -> Dict:
    all_trades = []
    cooldown_ms = config['cooldown_min'] * 60 * 1000
    days_with_data = 0

    rejection_reasons = {}

    days_list = list(all_data.items())
    total_days = len(days_list)

    for day_idx, (day, day_data) in enumerate(days_list):
        if show_progress:
            progress_bar(day_idx + 1, total_days, "Jours", f"{day}")

        day_has_trades = False
        day_trade_count = 0

        for symbol in ["ES", "NQ"]:
            snapshots = day_data.get(symbol, [])
            if not snapshots:
                continue

            last_trade_time = 0

            for i, snap in enumerate(snapshots):
                if day_trade_count >= config['max_trades_per_day']:
                    break

                t_ms = snap.get('t_ms', 0)
                hour, minute = get_paris_time(t_ms)

                if t_ms - last_trade_time < cooldown_ms:
                    continue

                valid, direction, confidence, reason, details = generate_signal(
                    snap, symbol, config, hour, minute
                )

                if not valid:
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                    continue

                future = snapshots[i+1:i+301]
                if len(future) < 10:
                    continue

                trade = simulate_trade(
                    snap, direction, symbol, future, config,
                    details.get('session', 'UNKNOWN'), day, confidence
                )

                all_trades.append(trade)
                last_trade_time = t_ms
                day_trade_count += 1
                day_has_trades = True

        if day_has_trades:
            days_with_data += 1

    if not all_trades:
        return {
            'config_name': config['name'],
            'trades': [],
            'total_pnl': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'total_trades': 0,
            'avg_trades_per_day': 0,
            'rejection_reasons': rejection_reasons,
        }

    # Stats
    total_pnl = sum(t.pnl_usd for t in all_trades)
    winners = [t for t in all_trades if t.pnl_usd > 0]
    losers = [t for t in all_trades if t.pnl_usd < 0]

    win_rate = len(winners) / len(all_trades) * 100

    avg_win = sum(t.pnl_usd for t in winners) / len(winners) if winners else 0
    avg_loss = sum(t.pnl_usd for t in losers) / len(losers) if losers else 0

    gross_profit = sum(t.pnl_usd for t in winners)
    gross_loss = abs(sum(t.pnl_usd for t in losers))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999

    # Par symbole
    es_trades = [t for t in all_trades if t.symbol == "ES"]
    nq_trades = [t for t in all_trades if t.symbol == "NQ"]

    return {
        'config_name': config['name'],
        'trades': all_trades,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'profit_factor': pf,
        'total_trades': len(all_trades),
        'avg_trades_per_day': len(all_trades) / max(1, days_with_data),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'es_pnl': sum(t.pnl_usd for t in es_trades),
        'nq_pnl': sum(t.pnl_usd for t in nq_trades),
        'es_trades': len(es_trades),
        'nq_trades': len(nq_trades),
        'rejection_reasons': rejection_reasons,
    }

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("          🎯 BACKTEST CONFIG ACTUELLE vs AVANT")
    print("=" * 100)
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│  PARAMÈTRES TESTÉS                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  CONFIG ACTUELLE (13/12):                                           │
│    - MIN_TOTAL_CONFIDENCE: 70%                                      │
│    - Layer2 (OrderFlow): 17%                                        │
│    - TP: 15 ticks, SL: 6 ticks (R:R 2.5:1)                         │
│    - ORDERFLOW_ALIGNMENT_BLOCK: OFF                                 │
│    - BRACKET_BLOCK: OFF                                             │
│                                                                     │
│  CONFIG AVANT (12/12 - trop strict):                               │
│    - MIN_TOTAL_CONFIDENCE: 100%                                     │
│    - Layer2 (OrderFlow): 18%                                        │
│    - TP: 15 ticks, SL: 15 ticks (R:R 1:1)                          │
└─────────────────────────────────────────────────────────────────────┘
""")

    # Charger données
    print("📂 Chargement des données...")
    all_data = {}
    days_loaded = 0
    total_snapshots = 0

    for i, day in enumerate(DAYS_TO_TEST):
        progress_bar(i + 1, len(DAYS_TO_TEST), "Chargement", f"{day}")
        all_data[day] = {}
        has_data = False

        for symbol in ["ES", "NQ"]:
            file_path = find_data_file(day, symbol)
            if file_path:
                snapshots = load_snapshots(file_path)
                all_data[day][symbol] = snapshots
                total_snapshots += len(snapshots)
                if snapshots:
                    has_data = True

        if has_data:
            days_loaded += 1

    print(f"\n   📊 {days_loaded} jours | {total_snapshots:,} snapshots")

    if days_loaded == 0:
        print("\n❌ Aucune donnée!")
        return

    # Backtests
    print("\n" + "=" * 100)
    print("                    🧪 EXÉCUTION DES BACKTESTS")
    print("=" * 100)

    results = {}
    for config_name, config in CONFIGS.items():
        print(f"\n▶ {config['name']}...")
        result = run_backtest(config, all_data, show_progress=True)
        results[config_name] = result
        print(f"   ✅ {result['total_trades']} trades | WR: {result['win_rate']:.1f}% | PnL: ${result['total_pnl']:+,.0f} | PF: {result['profit_factor']:.2f}")

    # Résultats
    print("\n" + "=" * 100)
    print("                    📊 COMPARAISON")
    print("=" * 100)

    print(f"\n{'Config':<40} {'Trades':>7} {'T/J':>5} {'WR%':>6} {'AvgWin':>9} {'AvgLoss':>10} {'PnL':>12} {'PF':>6}")
    print("-" * 100)

    for name, r in results.items():
        marker = "🏆" if r['total_pnl'] > 0 and r['total_pnl'] == max(x['total_pnl'] for x in results.values()) else "  "
        avg_win = r.get('avg_win', 0)
        avg_loss = r.get('avg_loss', 0)
        print(f"{marker}{r['config_name']:<38} {r['total_trades']:>7} {r['avg_trades_per_day']:>4.1f} {r['win_rate']:>5.1f}% ${avg_win:>+7.0f} ${avg_loss:>+8.0f} ${r['total_pnl']:>+10,.0f} {r['profit_factor']:>5.2f}")

    print("-" * 100)

    # Détail par symbole
    print("\n📈 DÉTAIL PAR SYMBOLE:")
    for name, r in results.items():
        print(f"\n  {r['config_name']}:")
        print(f"    ES: {r['es_trades']} trades | ${r['es_pnl']:+,.0f}")
        print(f"    NQ: {r['nq_trades']} trades | ${r['nq_pnl']:+,.0f}")

    # Rejections
    print("\n" + "=" * 100)
    print("                    📋 RAISONS DE REJET")
    print("=" * 100)

    for name, r in results.items():
        print(f"\n  {r['config_name']}:")
        for reason, count in sorted(r['rejection_reasons'].items(), key=lambda x: -x[1])[:10]:
            print(f"    {reason}: {count}")

    # Conclusion
    print("\n" + "=" * 100)
    actuelle = results.get('ACTUELLE', {})
    avant = results.get('AVANT', {})

    if actuelle.get('total_pnl', 0) > avant.get('total_pnl', 0):
        print("🏆 CONFIG ACTUELLE EST MEILLEURE!")
        diff = actuelle['total_pnl'] - avant['total_pnl']
        print(f"   Gain supplémentaire: ${diff:+,.0f}")
    else:
        print("⚠️ CONFIG AVANT était meilleure (mais bloquait tout en réel!)")

    print("=" * 100)
    print("\n✅ BACKTEST TERMINÉ!")


if __name__ == "__main__":
    main()
