#!/usr/bin/env python3
"""
🔄 BACKTEST RÉALISTE MIA IA SYSTEM - VERSION COMPLÈTE
======================================================

Compare 3 configurations:
- CURRENT: Config actuelle (over-engineered)
- SIMPLIFIED: Config simplifiée proposée
- OPTIMAL: Recherche des meilleurs paramètres

Configuration:
- 1 contrat MINI (ES = $12.50/tick, NQ = $5.00/tick)
- Sessions EXACTES du session_quality_monitor.py
- Paramètres à optimiser

Sessions de trading (Paris):
- London:     08:00 - 11:00 (3h)
- US Morning: 16:35 - 17:00 (25 min, après US Open Block)
- Power Hour: 20:00 - 21:25 (1h25)
Total: ~4h50 de trading/jour

Auteur: Jackson Trading System - MIA IA
Date: 13 Décembre 2025
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from itertools import product
from collections import defaultdict

# ============================================================
# CONFIGURATION PATHS
# ============================================================

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")
CALIBRAGE_PATH = Path("D:/MIA_IA_system/CALIBRAGE_PHASE/SNAPSHOTS")

# Jours disponibles
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

# ============================================================
# CONFIGURATION SYMBOLES - 1 CONTRAT MINI
# ============================================================

SYMBOLS = {
    "ES": {
        "chart_id": 3,
        "tick_size": 0.25,
        "tick_value": 12.50,  # 1 contrat MINI ES
        "contracts": ["ESZ25", "ESH25"],
    },
    "NQ": {
        "chart_id": 9,
        "tick_size": 0.25,
        "tick_value": 5.00,   # 1 contrat MINI NQ
        "contracts": ["NQZ25", "NQH25"],
    },
}

# ============================================================
# SESSIONS DE TRADING (Exactement comme session_quality_monitor.py)
# ============================================================

TRADING_SESSIONS = {
    # Format: (start_hour, start_min, end_hour, end_min)
    'london': (8, 0, 11, 0),           # 08:00 - 11:00 Paris
    'us_morning': (16, 35, 17, 0),     # 16:35 - 17:00 (après US Open Block)
    'power_hour': (20, 0, 21, 25),     # 20:00 - 21:25 Paris
}

# Périodes BLOQUÉES
BLOCKED_PERIODS = {
    'pre_open': (15, 25, 15, 35),
    'opr_observe': (15, 35, 15, 50),
    'us_open_block': (15, 45, 16, 35),  # 🔥 CRITIQUE!
    'lunch': (17, 0, 19, 30),
}

# ============================================================
# NIVEAUX MENTHORQ À UTILISER
# ============================================================

MENTHORQ_LEVELS = [
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    'hvl', 'hvl_0dte',
    'blind_spot_0', 'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
    'blind_spot_4', 'blind_spot_5', 'blind_spot_6',
    'blind_spot_7', 'blind_spot_8',
    'call_resistance', 'put_support',
    'call_resistance_0dte', 'put_support_0dte',
]

# ============================================================
# CONFIGURATIONS À COMPARER
# ============================================================

CONFIGS_TO_COMPARE = {
    # Configuration ACTUELLE (over-engineered)
    'CURRENT': {
        'name': '⛔ Config Actuelle (Trop Stricte)',
        'min_confidence': {'ES': 1.00, 'NQ': 1.00},
        'max_distance': {'ES': 8, 'NQ': 10},
        'min_pressure_strength': {'ES': 0.20, 'NQ': 0.03},
        'enable_pressure_filter': True,
        'enable_trend_filter': True,
        'mia_score_threshold': 0.30,
        'cooldown_min': 5,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'max_trades_per_day': 50,
    },

    # Configuration SIMPLIFIÉE (proposée)
    'SIMPLIFIED': {
        'name': '✅ Config Simplifiée (Proposée)',
        'min_confidence': {'ES': 0.50, 'NQ': 0.50},
        'max_distance': {'ES': 15, 'NQ': 20},
        'min_pressure_strength': {'ES': 0.0, 'NQ': 0.0},
        'enable_pressure_filter': False,
        'enable_trend_filter': False,
        'mia_score_threshold': 0.25,
        'cooldown_min': 30,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'max_trades_per_day': 15,
    },

    # Configuration MINIMALE (tout passe)
    'MINIMAL': {
        'name': '🔓 Config Minimale (Référence)',
        'min_confidence': {'ES': 0.30, 'NQ': 0.30},
        'max_distance': {'ES': 50, 'NQ': 60},
        'min_pressure_strength': {'ES': 0.0, 'NQ': 0.0},
        'enable_pressure_filter': False,
        'enable_trend_filter': False,
        'mia_score_threshold': 0.15,
        'cooldown_min': 20,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'max_trades_per_day': 50,
    },
}

# ============================================================
# GRILLE DE PARAMÈTRES POUR OPTIMISATION
# ============================================================

PARAM_GRID = {
    # Cooldown entre trades (minutes)
    'cooldown_min': [20, 30, 45],

    # Distance max du niveau MenthorQ
    'max_distance_es': [10, 12, 15],
    'max_distance_nq': [15, 18, 20],

    # Take Profits
    'tp1_ticks': [8, 10, 12],      # TP partiel (50%)
    'tp2_ticks': [15],              # TP final

    # Trailing Stop
    'trailing_activation': [6, 8, 10],
    'trailing_distance': [4, 5, 6],

    # Stop Loss
    'sl_ticks': [15],

    # Max trades par jour
    'max_trades_per_day': [10, 12, 15],

    # Seuil MIA score pour direction
    'mia_score_threshold': [0.20, 0.25, 0.30],

    # Confidence minimum
    'min_confidence': [0.40, 0.50, 0.60],
}

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class TradeResult:
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    result: str  # WIN, LOSS, PARTIAL, TRAILING, TIMEOUT
    pnl_usd: float
    tp1_hit: bool
    entry_time: int
    duration_sec: float
    mfe_ticks: float  # Maximum Favorable Excursion
    mae_ticks: float  # Maximum Adverse Excursion
    session: str
    day: str
    confidence: float
    distance_to_level: float
    level_name: str

@dataclass
class BacktestResult:
    config_name: str
    trades: List[TradeResult]
    total_pnl: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trades_per_day: float
    es_pnl: float
    nq_pnl: float
    es_trades: int
    nq_trades: int
    signals_generated: int
    signals_rejected: int
    rejection_rate: float
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    by_session: Dict = field(default_factory=dict)

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def get_month_folder(day: str) -> str:
    """Retourne le dossier du mois."""
    month = day[4:6]
    return "NOVEMBRE" if month == "11" else "DECEMBRE"

def find_data_file(day: str, symbol: str) -> Optional[Path]:
    """Trouve le fichier de données pour un jour et symbole."""
    config = SYMBOLS[symbol]
    month_folder = get_month_folder(day)

    for contract in config["contracts"]:
        path = DATA_BASE_PATH / month_folder / day / f"CHART_{config['chart_id']}" / "ML_READY" / f"ml_{contract}_FUT_CME_{config['chart_id']}.jsonl"
        if path.exists():
            return path
    return None

def load_snapshots(file_path: Path) -> List[Dict]:
    """Charge les snapshots depuis un fichier JSONL."""
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

    # Trier par timestamp
    snapshots.sort(key=lambda x: x.get('t_ms', 0))
    return snapshots

def get_paris_time(t_ms: int) -> Tuple[int, int]:
    """Retourne (heure, minute) en heure Paris depuis timestamp ms."""
    total_minutes = (t_ms // 1000 // 60) % 1440
    hour_utc = total_minutes // 60
    minute = total_minutes % 60
    hour_paris = (hour_utc + 1) % 24  # UTC+1 en hiver
    return hour_paris, minute

def is_in_session(hour: int, minute: int) -> Tuple[bool, str]:
    """
    Vérifie si on est dans une session de trading valide.

    Returns:
        (is_valid, session_name)
    """
    time_val = hour * 60 + minute

    # Vérifier d'abord les périodes bloquées
    for name, (sh, sm, eh, em) in BLOCKED_PERIODS.items():
        start = sh * 60 + sm
        end = eh * 60 + em
        if start <= time_val < end:
            return False, f"BLOCKED_{name}"

    # Vérifier les sessions actives
    for name, (sh, sm, eh, em) in TRADING_SESSIONS.items():
        start = sh * 60 + sm
        end = eh * 60 + em
        if start <= time_val < end:
            return True, name

    return False, "OFF_HOURS"

# ============================================================
# LOGIQUE DE SIGNAL (Reproduit la vraie logique du bot)
# ============================================================

def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float, float]:
    """
    Trouve le niveau MenthorQ le plus proche.

    Returns:
        (level_name, level_price, distance_ticks)
    """
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return "", 0, 999

    tick_size = SYMBOLS[symbol]['tick_size']

    nearest_name = ""
    nearest_dist = float('inf')
    nearest_price = 0

    # Vérifier tous les niveaux MenthorQ
    for level_name in MENTHORQ_LEVELS:
        price = snapshot.get(level_name)
        if price and price > 0:
            dist = abs(mid - price) / tick_size
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_name = level_name
                nearest_price = price

    # Vérifier aussi menthor_distances si disponible
    menthor_distances = snapshot.get('menthor_distances', {})
    for key in ['near_gex_up', 'near_gex_dn', 'hvl0', 'near_blind']:
        dist = menthor_distances.get(key)
        if dist is not None and abs(dist) < nearest_dist:
            nearest_dist = abs(dist)
            nearest_name = key

    return nearest_name, nearest_price, nearest_dist

def calculate_confidence(snapshot: Dict) -> float:
    """
    Calcule la confidence comme le fait le ML 3-Layer.

    Returns:
        Confidence score (0-2)
    """
    # Layer 1: MenthorQ (50%)
    l1 = snapshot.get('layer1_confidence',
         snapshot.get('menthorq_score', 0.5))

    # Layer 2: OrderFlow (30%)
    l2 = snapshot.get('layer2_confidence',
         snapshot.get('orderflow_score', 0.3))

    # Layer 3: Context (20%)
    l3 = snapshot.get('layer3_confidence',
         snapshot.get('context_score', 0.2))

    # Pondération officielle
    confidence = l1 * 0.50 + l2 * 0.30 + l3 * 0.20

    # Si pas de scores ML, utiliser le mia_bullish_score
    if confidence == 0:
        bullish = abs(snapshot.get('mia_bullish_score', 0))
        confidence = 0.5 + bullish * 0.5

    return confidence

def check_signal(snapshot: Dict, symbol: str, config: Dict) -> Tuple[bool, str, float, str, str]:
    """
    Vérifie si un signal valide existe selon la configuration.

    Returns:
        (is_valid, direction, confidence, level_name, rejection_reason)
    """
    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "", "NO_PRICE"

    # 1. Distance au niveau MenthorQ
    max_dist = config['max_distance'].get(symbol, 15)
    level_name, level_price, distance = find_nearest_level(snapshot, symbol)

    if distance > max_dist:
        return False, "", 0, "", f"DISTANCE_TOO_FAR ({distance:.0f}t > {max_dist}t)"

    # 2. Confidence
    confidence = calculate_confidence(snapshot)
    min_conf = config['min_confidence'].get(symbol, 0.50)

    if confidence < min_conf:
        return False, "", confidence, level_name, f"LOW_CONFIDENCE ({confidence:.2f} < {min_conf})"

    # 3. Pressure strength (si activé)
    if config.get('enable_pressure_filter', False):
        pressure = snapshot.get('pressure_strength', 0.5)
        min_pressure = config['min_pressure_strength'].get(symbol, 0.0)

        if pressure < min_pressure:
            return False, "", confidence, level_name, f"LOW_PRESSURE ({pressure:.3f} < {min_pressure})"

    # 4. Direction basée sur mia_bullish_score
    mia_score = snapshot.get('mia_bullish_score', 0)
    threshold = config.get('mia_score_threshold', 0.25)

    if mia_score > threshold:
        direction = "LONG"
    elif mia_score < -threshold:
        direction = "SHORT"
    else:
        return False, "", confidence, level_name, f"NEUTRAL_DIRECTION ({mia_score:.2f})"

    # 5. Trend filter (si activé)
    if config.get('enable_trend_filter', False):
        hvl = snapshot.get('hvl', 0)
        vwap = snapshot.get('vwap', 0)

        if hvl > 0 and vwap > 0:
            above_hvl = mid > hvl
            above_vwap = mid > vwap

            if direction == "LONG" and not above_hvl and not above_vwap:
                return False, "", confidence, level_name, "TREND_FILTER_BLOCKED_LONG"

            if direction == "SHORT" and above_hvl and above_vwap:
                return False, "", confidence, level_name, "TREND_FILTER_BLOCKED_SHORT"

    # Signal valide!
    return True, direction, confidence, level_name, "OK"

# ============================================================
# SIMULATION DE TRADE
# ============================================================

def simulate_trade(
    entry_snap: Dict,
    direction: str,
    symbol: str,
    future_snaps: List[Dict],
    config: Dict,
    session: str,
    day: str,
    confidence: float,
    level_name: str,
    distance: float,
) -> TradeResult:
    """
    Simule un trade avec TP partiel + trailing stop.

    Logique:
    - TP1 à 50% de la position
    - TP2 pour le reste avec trailing stop
    - SL fixe
    """

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    # Paramètres SL/TP
    sl_ticks = config.get('sl_ticks', 15)
    tp1_ticks = config.get('tp1_ticks', 10)
    tp2_ticks = config.get('tp2_ticks', 15)
    trailing_activation = config.get('trailing_activation', 8)
    trailing_distance = config.get('trailing_distance', 5)

    # Calcul des prix SL/TP
    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp1 = entry - tp1_ticks * tick_size
        tp2 = entry - tp2_ticks * tick_size
    else:  # LONG
        sl = entry - sl_ticks * tick_size
        tp1 = entry + tp1_ticks * tick_size
        tp2 = entry + tp2_ticks * tick_size

    # Variables de simulation
    tp1_hit = False
    trailing = None
    best_profit = 0
    pnl = 0
    result = "TIMEOUT"
    exit_price = entry
    exit_time = entry_time
    high_reached = entry
    low_reached = entry

    # Simuler avec les snapshots futurs (max 5 min = 300 snapshots)
    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)

        # Timeout après 1h
        if t_ms - entry_time > 3600_000:
            break

        high = snap.get('high') or snap.get('mid', entry)
        low = snap.get('low') or snap.get('mid', entry)

        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        if direction == "SHORT":
            profit_ticks = (entry - low) / tick_size

            # TP1 (50%)
            if not tp1_hit and low <= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * 0.5

            # Trailing stop update
            if profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trailing_activation:
                    trailing = entry - (profit_ticks - trailing_distance) * tick_size

            # SL touché
            if high >= sl:
                pnl += -sl_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break

            # Trailing touché
            if trailing and high >= trailing:
                trail_profit = (entry - trailing) / tick_size
                pnl += trail_profit * tick_value * (0.5 if tp1_hit else 1.0)
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break

            # TP2 touché
            if low <= tp2:
                pnl += tp2_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break

        else:  # LONG
            profit_ticks = (high - entry) / tick_size

            # TP1 (50%)
            if not tp1_hit and high >= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * 0.5

            # Trailing stop update
            if profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trailing_activation:
                    trailing = entry + (profit_ticks - trailing_distance) * tick_size

            # SL touché
            if low <= sl:
                pnl += -sl_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break

            # Trailing touché
            if trailing and low <= trailing:
                trail_profit = (trailing - entry) / tick_size
                pnl += trail_profit * tick_value * (0.5 if tp1_hit else 1.0)
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break

            # TP2 touché
            if high >= tp2:
                pnl += tp2_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break

    # Calculer MAE/MFE
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
        tp1_hit=tp1_hit,
        entry_time=entry_time,
        duration_sec=(exit_time - entry_time) / 1000,
        mfe_ticks=mfe,
        mae_ticks=mae,
        session=session,
        day=day,
        confidence=confidence,
        distance_to_level=distance,
        level_name=level_name,
    )

# ============================================================
# BACKTEST ENGINE
# ============================================================

def run_backtest_config(config: Dict, all_data: Dict) -> BacktestResult:
    """Exécute le backtest avec une configuration donnée."""

    all_trades = []
    rejection_reasons = defaultdict(int)
    signals_generated = 0
    signals_rejected = 0
    days_with_data = 0

    cooldown_ms = config.get('cooldown_min', 30) * 60 * 1000
    max_trades_per_day = config.get('max_trades_per_day', 15)

    for day, day_data in all_data.items():
        day_has_trades = False
        day_trade_count = 0

        for symbol in ["ES", "NQ"]:
            snapshots = day_data.get(symbol, [])
            if not snapshots:
                continue

            last_trade_time = 0

            for i, snap in enumerate(snapshots):
                # Max trades par jour atteint?
                if day_trade_count >= max_trades_per_day:
                    break

                t_ms = snap.get('t_ms', 0)
                hour, minute = get_paris_time(t_ms)

                # Vérifier session
                in_session, session_name = is_in_session(hour, minute)
                if not in_session:
                    continue

                # Cooldown
                if t_ms - last_trade_time < cooldown_ms:
                    continue

                signals_generated += 1

                # Check signal
                valid, direction, confidence, level_name, reason = check_signal(snap, symbol, config)

                if not valid:
                    signals_rejected += 1
                    rejection_reasons[reason] += 1
                    continue

                # Distance au niveau
                _, _, distance = find_nearest_level(snap, symbol)

                # Simuler trade
                future = snapshots[i+1:i+301]
                if len(future) < 10:
                    continue

                trade = simulate_trade(
                    snap, direction, symbol, future, config,
                    session_name, day, confidence, level_name, distance
                )
                all_trades.append(trade)

                last_trade_time = t_ms
                day_trade_count += 1
                day_has_trades = True

        if day_has_trades:
            days_with_data += 1

    # Calculer métriques
    if not all_trades:
        return BacktestResult(
            config_name=config.get('name', 'Unknown'),
            trades=[],
            total_pnl=0,
            win_rate=0,
            profit_factor=0,
            total_trades=0,
            avg_trades_per_day=0,
            es_pnl=0,
            nq_pnl=0,
            es_trades=0,
            nq_trades=0,
            signals_generated=signals_generated,
            signals_rejected=signals_rejected,
            rejection_rate=100.0,
            rejection_reasons=dict(rejection_reasons),
        )

    total_pnl = sum(t.pnl_usd for t in all_trades)
    profitable = [t for t in all_trades if t.pnl_usd > 0]
    win_rate = len(profitable) / len(all_trades) * 100

    gross_profit = sum(t.pnl_usd for t in all_trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in all_trades if t.pnl_usd < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999

    es_trades = [t for t in all_trades if t.symbol == "ES"]
    nq_trades = [t for t in all_trades if t.symbol == "NQ"]

    rejection_rate = (signals_rejected / signals_generated * 100) if signals_generated > 0 else 0

    # Par session
    by_session = {}
    for session in ['london', 'us_morning', 'power_hour']:
        sess_trades = [t for t in all_trades if t.session == session]
        if sess_trades:
            by_session[session] = {
                'trades': len(sess_trades),
                'pnl': sum(t.pnl_usd for t in sess_trades),
                'wr': len([t for t in sess_trades if t.pnl_usd > 0]) / len(sess_trades) * 100
            }

    return BacktestResult(
        config_name=config.get('name', 'Unknown'),
        trades=all_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        profit_factor=pf,
        total_trades=len(all_trades),
        avg_trades_per_day=len(all_trades) / max(1, days_with_data),
        es_pnl=sum(t.pnl_usd for t in es_trades),
        nq_pnl=sum(t.pnl_usd for t in nq_trades),
        es_trades=len(es_trades),
        nq_trades=len(nq_trades),
        signals_generated=signals_generated,
        signals_rejected=signals_rejected,
        rejection_rate=rejection_rate,
        rejection_reasons=dict(rejection_reasons),
        by_session=by_session,
    )

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("🔄 BACKTEST RÉALISTE MIA IA SYSTEM")
    print("=" * 80)
    print(f"""
📊 CONFIGURATION:
   - 1 contrat MINI ES ($12.50/tick)
   - 1 contrat MINI NQ ($5.00/tick)

📅 SESSIONS (Paris time):
   - London:     08:00 - 11:00 (3h)
   - US Morning: 16:35 - 17:00 (25 min)
   - Power Hour: 20:00 - 21:25 (1h25)
   - Total: ~4h50 de trading/jour

🚫 BLOQUÉ:
   - Pre-Open:      15:25 - 15:35
   - US Open Block: 15:45 - 16:35
   - Lunch:         17:00 - 19:30
   - After:         21:25+
""")

    # Charger données
    print("📂 Chargement des données...")
    all_data = {}
    days_loaded = 0

    for day in DAYS_TO_TEST:
        all_data[day] = {}
        has_data = False

        for symbol in ["ES", "NQ"]:
            file_path = find_data_file(day, symbol)
            if file_path:
                snapshots = load_snapshots(file_path)
                all_data[day][symbol] = snapshots
                if snapshots:
                    has_data = True

        if has_data:
            days_loaded += 1
            es_count = len(all_data[day].get('ES', []))
            nq_count = len(all_data[day].get('NQ', []))
            print(f"   ✅ {day}: ES={es_count:,} NQ={nq_count:,}")

    print(f"\n   📊 {days_loaded} jours chargés")

    if days_loaded == 0:
        print("\n❌ Aucune donnée! Vérifie DATA_BASE_PATH")
        return

    # ============================================================
    # PARTIE 1: COMPARER CURRENT vs SIMPLIFIED vs MINIMAL
    # ============================================================

    print("\n" + "=" * 80)
    print("📊 COMPARAISON DES CONFIGURATIONS")
    print("=" * 80)

    comparison_results = {}

    for config_key, config in CONFIGS_TO_COMPARE.items():
        print(f"\n   ▶ Test {config['name']}...")
        result = run_backtest_config(config, all_data)
        comparison_results[config_key] = result

    # Afficher comparaison
    print("\n" + "-" * 80)
    print(f"{'Config':<40} {'Trades':>7} {'WR%':>7} {'PnL':>12} {'Rej%':>7}")
    print("-" * 80)

    for config_key, result in comparison_results.items():
        print(f"{result.config_name:<40} {result.total_trades:>7} "
              f"{result.win_rate:>6.1f}% ${result.total_pnl:>10,.0f} {result.rejection_rate:>6.1f}%")

    # Top 5 raisons de rejet par config
    print("\n📊 RAISONS DE REJET:")
    for config_key, result in comparison_results.items():
        print(f"\n   {result.config_name}:")
        for reason, count in sorted(result.rejection_reasons.items(), key=lambda x: -x[1])[:5]:
            pct = count / result.signals_generated * 100 if result.signals_generated > 0 else 0
            print(f"      • {reason}: {count} ({pct:.1f}%)")

    # ============================================================
    # PARTIE 2: OPTIMISATION DES PARAMÈTRES
    # ============================================================

    print("\n" + "=" * 80)
    print("🔬 OPTIMISATION DES PARAMÈTRES")
    print("=" * 80)

    # Générer toutes les combinaisons
    combinations = list(product(
        PARAM_GRID['cooldown_min'],
        PARAM_GRID['max_distance_es'],
        PARAM_GRID['max_distance_nq'],
        PARAM_GRID['tp1_ticks'],
        PARAM_GRID['tp2_ticks'],
        PARAM_GRID['trailing_activation'],
        PARAM_GRID['trailing_distance'],
        PARAM_GRID['sl_ticks'],
        PARAM_GRID['max_trades_per_day'],
        PARAM_GRID['mia_score_threshold'],
        PARAM_GRID['min_confidence'],
    ))

    print(f"\n🧪 Test de {len(combinations)} combinaisons...")

    optimization_results = []
    best = None
    best_pnl = float('-inf')

    for i, combo in enumerate(combinations):
        config = {
            'name': f'Combo_{i+1}',
            'cooldown_min': combo[0],
            'max_distance': {'ES': combo[1], 'NQ': combo[2]},
            'min_confidence': {'ES': combo[10], 'NQ': combo[10]},
            'min_pressure_strength': {'ES': 0.0, 'NQ': 0.0},
            'enable_pressure_filter': False,
            'enable_trend_filter': False,
            'tp1_ticks': combo[3],
            'tp2_ticks': combo[4],
            'trailing_activation': combo[5],
            'trailing_distance': combo[6],
            'sl_ticks': combo[7],
            'max_trades_per_day': combo[8],
            'mia_score_threshold': combo[9],
        }

        result = run_backtest_config(config, all_data)

        # Stocker avec paramètres
        result.params = combo
        optimization_results.append(result)

        if result.total_pnl > best_pnl and result.total_trades >= 20:
            best_pnl = result.total_pnl
            best = result

        if (i + 1) % 100 == 0:
            print(f"   ⏳ {i+1}/{len(combinations)} - Best: ${best_pnl:+,.0f}")

    # Trier par P&L
    optimization_results.sort(key=lambda x: x.total_pnl, reverse=True)

    # Top 15
    print("\n" + "-" * 100)
    print("🏆 TOP 15 CONFIGURATIONS")
    print("-" * 100)
    print(f"{'#':>2} {'PnL':>10} {'WR%':>6} {'PF':>5} {'Trades':>6} {'CD':>3} {'Dist':>7} {'TP1':>3} {'Trail':>5} {'MIA':>5} {'Conf':>5}")
    print("-" * 100)

    for i, r in enumerate(optimization_results[:15], 1):
        p = r.params
        dist = f"{p[1]}/{p[2]}"
        trail = f"{p[5]}/{p[6]}"
        print(f"{i:>2} ${r.total_pnl:>+8,.0f} {r.win_rate:>5.1f}% {r.profit_factor:>4.2f} "
              f"{r.total_trades:>6} {p[0]:>3} {dist:>7} {p[3]:>3} {trail:>5} {p[9]:>5.2f} {p[10]:>5.2f}")

    # Meilleure config
    if best:
        p = best.params
        print(f"""
{'='*80}
🥇 MEILLEURE CONFIGURATION TROUVÉE
{'='*80}
╔══════════════════════════════════════════════════════════════════╗
║  📊 PARAMÈTRES OPTIMAUX                                          ║
╠══════════════════════════════════════════════════════════════════╣
║  Cooldown:            {p[0]:>3} minutes                               ║
║  Distance ES:         {p[1]:>3} ticks                                 ║
║  Distance NQ:         {p[2]:>3} ticks                                 ║
║  Confidence Min:      {p[10]:>4.2f}                                    ║
║  MIA Score Seuil:     {p[9]:>4.2f}                                    ║
║  TP1 (50%):           {p[3]:>3} ticks                                 ║
║  TP2 (50%):           {p[4]:>3} ticks                                 ║
║  Trailing:            {p[5]:>3}t activation / {p[6]}t distance           ║
║  Stop Loss:           {p[7]:>3} ticks                                 ║
║  Max Trades/Jour:     {p[8]:>3}                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  📈 PERFORMANCE ({days_loaded} jours):                                    ║
║  PnL Total:     ${best.total_pnl:>+10,.2f}                                ║
║  Win Rate:      {best.win_rate:>10.1f}%                                   ║
║  Profit Factor: {best.profit_factor:>10.2f}                                   ║
║  Total Trades:  {best.total_trades:>10}                                   ║
║  Trades/Jour:   {best.avg_trades_per_day:>10.1f}                                   ║
║  Taux Rejet:    {best.rejection_rate:>10.1f}%                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  📊 PAR SYMBOLE:                                                 ║
║  ES: {best.es_trades:>4} trades | ${best.es_pnl:>+8,.0f}                              ║
║  NQ: {best.nq_trades:>4} trades | ${best.nq_pnl:>+8,.0f}                              ║
╚══════════════════════════════════════════════════════════════════╝
""")

        # Par session
        if best.by_session:
            print("\n📊 PAR SESSION:")
            for sess, data in best.by_session.items():
                print(f"   {sess:>12}: {data['trades']:>3} trades | ${data['pnl']:>+7,.0f} | WR: {data['wr']:.0f}%")

        # Code pour production
        print(f"""
{'='*80}
🚀 CODE POUR PRODUCTION
{'='*80}

# config/trading_params.py

MIN_TOTAL_CONFIDENCE = {{
    'ES': {p[10]},
    'NQ': {p[10]},
    'RTY': {p[10]},
}}

MAX_DISTANCE_TO_LEVEL = {{
    'ES': {p[1]},
    'NQ': {p[2]},
    'RTY': 15,
}}

TRADING_CONFIG = {{
    'cooldown_seconds': {p[0] * 60},
    'max_trades_per_day': {p[8]},
    'mia_score_threshold': {p[9]},

    'ES': {{
        'sl_ticks': {p[7]},
        'tp1_ticks': {p[3]},
        'tp2_ticks': {p[4]},
        'tp1_portion': 0.5,
        'trailing_activation': {p[5]},
        'trailing_distance': {p[6]},
    }},

    'NQ': {{
        'sl_ticks': {p[7]},
        'tp1_ticks': {p[3]},
        'tp2_ticks': {p[4]},
        'tp1_portion': 0.5,
        'trailing_activation': {p[5]},
        'trailing_distance': {p[6]},
    }},
}}
""")

    # Sauvegarder CSV
    csv_path = Path("backtest_results_optimized.csv")
    with open(csv_path, 'w') as f:
        f.write("Rank,PnL,WinRate,PF,Trades,TradesPerDay,RejectRate,Cooldown,DistES,DistNQ,TP1,TP2,TrailAct,TrailDist,SL,MaxTrades,MIAThreshold,MinConf,ES_PnL,NQ_PnL\n")
        for i, r in enumerate(optimization_results[:50], 1):
            p = r.params
            f.write(f"{i},{r.total_pnl:.2f},{r.win_rate:.1f},{r.profit_factor:.2f},{r.total_trades},{r.avg_trades_per_day:.1f},{r.rejection_rate:.1f},{p[0]},{p[1]},{p[2]},{p[3]},{p[4]},{p[5]},{p[6]},{p[7]},{p[8]},{p[9]},{p[10]},{r.es_pnl:.2f},{r.nq_pnl:.2f}\n")

    print(f"\n✅ Résultats sauvegardés: {csv_path}")
    print("\n✅ Backtest terminé!")

    # Conclusion
    print(f"""
{'='*80}
💡 CONCLUSION
{'='*80}

COMPARAISON DES CONFIGS:
""")

    for config_key, result in comparison_results.items():
        print(f"   {result.config_name}:")
        print(f"      Trades: {result.total_trades} | WR: {result.win_rate:.1f}% | P&L: ${result.total_pnl:+,.0f} | Rejet: {result.rejection_rate:.1f}%")

    print(f"""

RECOMMANDATION:
   • Si SIMPLIFIED a plus de trades et WR similaire → ADOPTER
   • Si MINIMAL a WR > 50% → Le système filtre TROP
   • Paramètres optimaux suggérés ci-dessus
""")

if __name__ == "__main__":
    main()









