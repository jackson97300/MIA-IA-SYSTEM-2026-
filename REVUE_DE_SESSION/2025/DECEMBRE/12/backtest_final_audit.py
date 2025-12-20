#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    BACKTEST FINAL MIA IA SYSTEM
                    Intègre Audit Cursor + Sessions Réelles
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF: Prouver que la SIMPLIFICATION améliore les résultats

📊 COMPARE 3 CONFIGS:
   1. CURRENT:    Config actuelle (39 filtres, MIN_CONF=1.00, DIST=8t)
   2. SIMPLIFIED: Config proposée (5 filtres, MIN_CONF=0.50, DIST=15t)
   3. MINIMAL:    Référence (tout passe)

⏰ SESSIONS RÉELLES (session_quality_monitor.py):
   - London:     08:00 - 11:00 Paris (3h)
   - US Morning: 16:35 - 17:00 Paris (25 min)
   - Power Hour: 20:00 - 21:25 Paris (1h25)
   - TOTAL: ~4h50 de trading/jour

💰 1 CONTRAT MINI:
   - ES: $12.50/tick
   - NQ: $5.00/tick

Auteur: Jackson Trading System + Claude
Date: 13 Décembre 2025
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from itertools import product
from collections import defaultdict
import sys

# ═══════════════════════════════════════════════════════════════════════════════
#                           BARRE DE PROGRESSION
# ═══════════════════════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 40):
    """Affiche une barre de progression."""
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    sys.stdout.write(f"\r   {prefix} |{bar}| {percent*100:.1f}% {suffix}")
    sys.stdout.flush()
    if current >= total:
        print()

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION PATHS
# ═══════════════════════════════════════════════════════════════════════════════

DATA_BASE_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

# Jours disponibles (d'après tes screenshots)
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

# ═══════════════════════════════════════════════════════════════════════════════
#                           SYMBOLES - 1 CONTRAT MINI
# ═══════════════════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════════════════
#                    SESSIONS EXACTES (session_quality_monitor.py)
# ═══════════════════════════════════════════════════════════════════════════════

TRADING_SESSIONS = {
    'london': {
        'start': (8, 0),    # 08:00 Paris
        'end': (11, 0),     # 11:00 Paris (3h)
        'enabled': True,
    },
    'us_morning': {
        'start': (15, 50),  # 15:50 Paris - CORRIGÉ! (était 16:35)
        'end': (17, 0),     # 17:00 Paris (1h10)
        'enabled': True,
    },
    'power_hour': {
        'start': (20, 0),   # 20:00 Paris
        'end': (21, 25),    # 21:25 Paris (1h25)
        'enabled': True,
    },
}
# TOTAL: 5h35 de trading/jour

# Périodes BLOQUÉES (session_quality_monitor.py) - SIMPLIFIÉES
BLOCKED_PERIODS = {
    'overnight': ((0, 0), (8, 0)),
    'pre_open_pause': ((15, 25), (15, 50)),  # Fusionné pre_open + opr
    # us_open_block SUPPRIMÉ - on trade dès 15:50!
    'lunch': ((17, 0), (19, 30)),
    'hard_stop': ((21, 25), (24, 0)),
}

# ═══════════════════════════════════════════════════════════════════════════════
#              CONFIGURATIONS À COMPARER (D'après audit Cursor)
# ═══════════════════════════════════════════════════════════════════════════════

CONFIGS = {
    # Configuration ACTUELLE (identifiée par Cursor comme TROP STRICTE)
    'CURRENT': {
        'name': '🔴 ACTUELLE (Over-engineered)',
        'min_confidence': {'ES': 1.00, 'NQ': 1.00},
        'max_distance': {'ES': 8, 'NQ': 10},
        'mia_threshold': 0.30,
        'cooldown_min': 30,
        'max_trades_per_day': 15,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'enable_pressure_filter': True,
        'pressure_threshold': {'ES': 0.20, 'NQ': 0.03},
        'enable_trend_filter': True,
        'enable_orderflow_filter': True,
        'orderflow_threshold': 200,
    },

    # Configuration SIMPLIFIÉE V1 (précédente)
    'SIMPLIFIED_V1': {
        'name': '✅ SIMPLIFIÉE V1 (12 trades)',
        'min_confidence': {'ES': 0.50, 'NQ': 0.50},
        'max_distance': {'ES': 15, 'NQ': 20},
        'mia_threshold': 0.25,
        'cooldown_min': 30,
        'max_trades_per_day': 12,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 15,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🎯 OPTIMISÉE V2 - Target 20 trades/jour + meilleur WR
    'OPTIMIZED_V2': {
        'name': '🎯 OPTIMISÉE V2 (20 trades)',
        'min_confidence': {'ES': 0.45, 'NQ': 0.45},     # Un peu plus bas
        'max_distance': {'ES': 12, 'NQ': 15},            # Plus strict = meilleur WR
        'mia_threshold': 0.20,                           # Plus de signaux
        'cooldown_min': 15,                              # Cooldown réduit!
        'max_trades_per_day': 20,
        'tp1_ticks': 8,                                  # TP1 plus rapide
        'tp2_ticks': 15,
        'sl_ticks': 12,                                  # SL plus serré
        'trailing_activation': 6,                        # Trail plus tôt
        'trailing_distance': 4,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🔥 AGGRESSIVE - Plus de trades, distance stricte
    'AGGRESSIVE': {
        'name': '🔥 AGGRESSIVE (25 trades)',
        'min_confidence': {'ES': 0.40, 'NQ': 0.40},
        'max_distance': {'ES': 10, 'NQ': 12},            # Distance stricte = meilleur WR
        'mia_threshold': 0.15,                           # Seuil bas = plus de signaux
        'cooldown_min': 10,                              # Cooldown court
        'max_trades_per_day': 25,
        'tp1_ticks': 8,
        'tp2_ticks': 12,
        'sl_ticks': 10,                                  # SL très serré
        'trailing_activation': 5,
        'trailing_distance': 3,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 💎 SNIPER - Moins de trades mais WR élevé
    'SNIPER': {
        'name': '💎 SNIPER (High WR)',
        'min_confidence': {'ES': 0.55, 'NQ': 0.55},     # Confiance haute
        'max_distance': {'ES': 8, 'NQ': 10},             # Très proche du niveau
        'mia_threshold': 0.30,                           # Signal fort requis
        'cooldown_min': 20,
        'max_trades_per_day': 15,
        'tp1_ticks': 10,
        'tp2_ticks': 15,
        'sl_ticks': 10,
        'trailing_activation': 6,
        'trailing_distance': 4,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🏆 BALANCED - Équilibre parfait
    'BALANCED': {
        'name': '🏆 BALANCED (Best R:R)',
        'min_confidence': {'ES': 0.48, 'NQ': 0.48},
        'max_distance': {'ES': 10, 'NQ': 14},
        'mia_threshold': 0.22,
        'cooldown_min': 12,
        'max_trades_per_day': 20,
        'tp1_ticks': 10,
        'tp2_ticks': 18,
        'sl_ticks': 12,
        'trailing_activation': 8,
        'trailing_distance': 5,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🧠 GAMMA_AWARE - Utilise gamma_flip + nouveaux niveaux
    'GAMMA_AWARE': {
        'name': '🧠 GAMMA_AWARE (Smart)',
        'min_confidence': {'ES': 0.42, 'NQ': 0.42},     # Bonus niveaux compense
        'max_distance': {'ES': 12, 'NQ': 15},
        'mia_threshold': 0.18,                           # Plus de signaux
        'cooldown_min': 10,                              # Cooldown court
        'max_trades_per_day': 18,
        'tp1_ticks': 8,
        'tp2_ticks': 14,
        'sl_ticks': 10,
        'trailing_activation': 6,
        'trailing_distance': 4,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },

    # 🎰 HIGH_FREQ - Max trades avec filtres intelligents
    'HIGH_FREQ': {
        'name': '🎰 HIGH_FREQ (15-20/jour)',
        'min_confidence': {'ES': 0.38, 'NQ': 0.38},
        'max_distance': {'ES': 15, 'NQ': 18},            # Plus large
        'mia_threshold': 0.15,                           # Seuil bas
        'cooldown_min': 8,                               # Très court
        'max_trades_per_day': 25,
        'tp1_ticks': 6,                                  # TP1 rapide
        'tp2_ticks': 12,
        'sl_ticks': 8,                                   # SL serré
        'trailing_activation': 4,
        'trailing_distance': 3,
        'enable_pressure_filter': False,
        'pressure_threshold': {'ES': 0.0, 'NQ': 0.0},
        'enable_trend_filter': False,
        'enable_orderflow_filter': False,
        'orderflow_threshold': 999,
    },
}

# Niveaux MenthorQ OPTIMISÉS (21 niveaux clés)
MENTHORQ_LEVELS = [
    # ═══ GEX PRIORITAIRES (5) ═══
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',

    # ═══ GAMMA NIVEAUX CLÉS (2) ═══
    'gamma_wall_0dte',
    'gamma_flip',        # 🆕 Changement de régime!

    # ═══ HVL (2) ═══
    'hvl', 'hvl_0dte',

    # ═══ BLIND SPOTS (3) ═══
    'blind_spot_1', 'blind_spot_2', 'blind_spot_3',

    # ═══ WALLS (4) ═══
    'call_resistance', 'put_support',
    'call_resistance_0dte', 'put_support_0dte',

    # ═══ VWAP + SD BANDS (5) ═══
    'vwap',
    'vwap_sd_plus1', 'vwap_sd_minus1',   # ±1 SD
    'vwap_sd_plus2', 'vwap_sd_minus2',   # ±2 SD (extrêmes)
]

# 📊 LOGIQUE GAMMA_FLIP:
# Prix AU-DESSUS → Gamma POSITIF → Mean reversion (fade les extrêmes)
# Prix EN-DESSOUS → Gamma NÉGATIF → Momentum/Trending (follow)

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
    tp1_hit: bool
    entry_time: int
    duration_sec: float
    mfe_ticks: float
    mae_ticks: float
    session: str
    day: str
    confidence: float
    distance: float

@dataclass
class BacktestResult:
    config_name: str
    trades: List[TradeResult]
    total_pnl: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trades_per_day: float
    signals_generated: int
    signals_rejected: int
    rejection_rate: float
    rejection_reasons: Dict[str, int]
    es_stats: Dict
    nq_stats: Dict
    by_session: Dict

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_month_folder(day: str) -> str:
    month = day[4:6]
    return "NOVEMBRE" if month == "11" else "DECEMBRE"


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
    """Retourne (heure, minute) en heure Paris (UTC+1)."""
    total_sec = t_ms // 1000
    total_min = total_sec // 60
    hour_utc = (total_min // 60) % 24
    minute = total_min % 60
    hour_paris = (hour_utc + 1) % 24
    return hour_paris, minute


def time_to_minutes(h: int, m: int) -> int:
    return h * 60 + m


def is_in_trading_session(hour: int, minute: int) -> Tuple[bool, str]:
    """Vérifie si on est dans une session de trading autorisée."""
    time_val = time_to_minutes(hour, minute)

    # Vérifier périodes bloquées d'abord
    for name, (start, end) in BLOCKED_PERIODS.items():
        s = time_to_minutes(start[0], start[1])
        e = time_to_minutes(end[0], end[1])
        if s <= time_val < e:
            return False, f"BLOCKED_{name}"

    # Vérifier sessions actives
    for name, session in TRADING_SESSIONS.items():
        if not session['enabled']:
            continue
        s = time_to_minutes(session['start'][0], session['start'][1])
        e = time_to_minutes(session['end'][0], session['end'][1])
        if s <= time_val < e:
            return True, name

    return False, "OFF_HOURS"


def find_nearest_level(snapshot: Dict, symbol: str) -> Tuple[str, float, float]:
    """Trouve le niveau MenthorQ le plus proche."""
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
#                           LOGIQUE DE SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signal(snapshot: Dict, symbol: str, config: Dict, hour: int, minute: int) -> Tuple[bool, str, float, str, Dict]:
    """
    Génère un signal en appliquant les filtres de la config.
    Utilise gamma_flip pour déterminer le régime du marché.

    Returns:
        (is_valid, direction, confidence, rejection_reason, details)
    """
    rejection_reasons = []

    mid = snapshot.get('mid', 0)
    if mid <= 0:
        return False, "", 0, "NO_PRICE", {}

    # 1. Vérifier session
    in_session, session_name = is_in_trading_session(hour, minute)
    if not in_session:
        return False, "", 0, session_name, {}

    # 2. Trouver niveau proche
    level_name, level_price, distance = find_nearest_level(snapshot, symbol)
    max_dist = config['max_distance'].get(symbol, 15)

    if distance > max_dist:
        return False, "", 0, f"DISTANCE_{distance:.0f}t>{max_dist}t", {'distance': distance}

    # 3. Déterminer le RÉGIME avec gamma_flip
    gamma_flip = snapshot.get('gamma_flip', 0)
    gamma_regime = "POSITIVE" if mid > gamma_flip and gamma_flip > 0 else "NEGATIVE"
    # POSITIVE = Mean reversion (fade les extrêmes)
    # NEGATIVE = Momentum/Trending (follow)

    # 4. Calculer confidence (simuler ML 3-Layer)
    # Layer 1: MenthorQ (50%)
    menthorq_score = snapshot.get('menthorq_proximity_strength', 0.5)
    if menthorq_score == 0:
        menthorq_score = max(0, 1 - distance / 20)  # Score basé sur distance

    # Bonus si proche d'un niveau VWAP ou gamma_flip
    if level_name in ['vwap', 'gamma_flip', 'hvl', 'gex_1']:
        menthorq_score = min(1.0, menthorq_score * 1.2)  # +20% bonus

    # Layer 2: OrderFlow (30%)
    delta = snapshot.get('delta', 0) or 0
    orderflow_score = min(1.0, abs(delta) / 500) * 0.5 + 0.25

    # Layer 3: Context (20%)
    mia_score = snapshot.get('mia_bullish_score', 0) or 0
    context_score = min(1.0, abs(mia_score) * 2)

    # Confidence totale
    confidence = menthorq_score * 0.50 + orderflow_score * 0.30 + context_score * 0.20

    min_conf = config['min_confidence'].get(symbol, 0.50)
    if confidence < min_conf:
        return False, "", confidence, f"CONF_{confidence:.2f}<{min_conf}", {'confidence': confidence}

    # 5. Direction basée sur mia_score + régime gamma
    threshold = config['mia_threshold']

    # Direction de base
    if mia_score > threshold:
        base_direction = "LONG"
    elif mia_score < -threshold:
        base_direction = "SHORT"
    else:
        return False, "", confidence, f"MIA_NEUTRAL_{mia_score:.2f}", {'mia_score': mia_score}

    # Ajuster selon le régime gamma (optionnel - améliore le WR)
    direction = base_direction

    # En régime POSITIF (mean reversion), favoriser les reversals sur VWAP SD bands
    if gamma_regime == "POSITIVE" and level_name in ['vwap_sd_plus2', 'vwap_sd_minus2']:
        # Reversal sur ±2SD en régime positif = signal fort
        confidence = min(1.0, confidence * 1.15)  # +15% bonus

    # 5. Filtres optionnels (les "39 blocages" de l'audit)

    # Filtre Pressure
    if config.get('enable_pressure_filter', False):
        pressure = snapshot.get('pressure', 0) or 0
        buy_pct = snapshot.get('bidPct', 0.5) or 0.5

        pressure_threshold = config['pressure_threshold'].get(symbol, 0.0)
        pressure_val = abs(buy_pct - 0.5)

        if pressure_val < pressure_threshold:
            return False, "", confidence, f"PRESSURE_{pressure_val:.2f}<{pressure_threshold}", {}

    # Filtre OrderFlow contradictoire
    if config.get('enable_orderflow_filter', False):
        of_threshold = config.get('orderflow_threshold', 200)
        if direction == "SHORT" and delta > of_threshold:
            return False, "", confidence, f"ORDERFLOW_CONTRA_SHORT_delta={delta}", {}
        if direction == "LONG" and delta < -of_threshold:
            return False, "", confidence, f"ORDERFLOW_CONTRA_LONG_delta={delta}", {}

    # Filtre Trend (position in range)
    if config.get('enable_trend_filter', False):
        position_range = snapshot.get('position_in_range', 50) or 50
        hvl = snapshot.get('hvl', 0)

        if hvl and mid:
            above_hvl = mid > hvl
            if direction == "LONG" and position_range > 75 and not above_hvl:
                return False, "", confidence, "TREND_LONG_TOP_BEARISH", {}
            if direction == "SHORT" and position_range < 25 and above_hvl:
                return False, "", confidence, "TREND_SHORT_BOTTOM_BULLISH", {}

    # Signal valide!
    details = {
        'confidence': confidence,
        'distance': distance,
        'level': level_name,
        'mia_score': mia_score,
        'session': session_name,
    }

    return True, direction, confidence, "OK", details

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIMULATION DE TRADE
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(entry_snap: Dict, direction: str, symbol: str,
                   future_snaps: List[Dict], config: Dict,
                   session: str, day: str, confidence: float, distance: float) -> TradeResult:
    """Simule un trade avec TP partiel + trailing."""

    tick_size = SYMBOLS[symbol]['tick_size']
    tick_value = SYMBOLS[symbol]['tick_value']

    entry = entry_snap.get('mid')
    entry_time = entry_snap.get('t_ms', 0)

    tp1_ticks = config['tp1_ticks']
    tp2_ticks = config['tp2_ticks']
    sl_ticks = config['sl_ticks']
    trail_act = config['trailing_activation']
    trail_dist = config['trailing_distance']

    if direction == "SHORT":
        sl = entry + sl_ticks * tick_size
        tp1 = entry - tp1_ticks * tick_size
        tp2 = entry - tp2_ticks * tick_size
    else:
        sl = entry - sl_ticks * tick_size
        tp1 = entry + tp1_ticks * tick_size
        tp2 = entry + tp2_ticks * tick_size

    tp1_hit = False
    trailing = None
    best_profit = 0
    pnl = 0
    result = "TIMEOUT"
    exit_price = entry
    exit_time = entry_time
    high_reached = entry
    low_reached = entry

    for snap in future_snaps[:300]:
        t_ms = snap.get('t_ms', 0)
        if t_ms - entry_time > 3600_000:  # Max 1h
            break

        high = snap.get('high') or snap.get('mid', entry)
        low = snap.get('low') or snap.get('mid', entry)

        high_reached = max(high_reached, high)
        low_reached = min(low_reached, low)

        if direction == "SHORT":
            profit_ticks = (entry - low) / tick_size

            if not tp1_hit and low <= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * 0.5

            if profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trail_act:
                    trailing = entry - (profit_ticks - trail_dist) * tick_size

            if high >= sl:
                pnl += -sl_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break

            if trailing and high >= trailing:
                trail_profit = (entry - trailing) / tick_size
                pnl += trail_profit * tick_value * (0.5 if tp1_hit else 1.0)
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break

            if low <= tp2:
                pnl += tp2_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "WIN"
                exit_price = tp2
                exit_time = t_ms
                break

        else:  # LONG
            profit_ticks = (high - entry) / tick_size

            if not tp1_hit and high >= tp1:
                tp1_hit = True
                pnl += tp1_ticks * tick_value * 0.5

            if profit_ticks > best_profit:
                best_profit = profit_ticks
                if profit_ticks >= trail_act:
                    trailing = entry + (profit_ticks - trail_dist) * tick_size

            if low <= sl:
                pnl += -sl_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "PARTIAL" if tp1_hit else "LOSS"
                exit_price = sl
                exit_time = t_ms
                break

            if trailing and low <= trailing:
                trail_profit = (trailing - entry) / tick_size
                pnl += trail_profit * tick_value * (0.5 if tp1_hit else 1.0)
                result = "TRAILING"
                exit_price = trailing
                exit_time = t_ms
                break

            if high >= tp2:
                pnl += tp2_ticks * tick_value * (0.5 if tp1_hit else 1.0)
                result = "WIN"
                exit_price = tp2
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
        tp1_hit=tp1_hit,
        entry_time=entry_time,
        duration_sec=(exit_time - entry_time) / 1000,
        mfe_ticks=mfe,
        mae_ticks=mae,
        session=session,
        day=day,
        confidence=confidence,
        distance=distance,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(config: Dict, all_data: Dict, show_progress: bool = False) -> BacktestResult:
    """Exécute le backtest avec une configuration donnée."""

    all_trades = []
    rejection_counts = defaultdict(int)
    signals_generated = 0
    signals_rejected = 0
    cooldown_ms = config['cooldown_min'] * 60 * 1000
    days_with_data = 0

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
            symbol_trade_count = 0

            for i, snap in enumerate(snapshots):
                if day_trade_count >= config['max_trades_per_day']:
                    break

                t_ms = snap.get('t_ms', 0)
                hour, minute = get_paris_time(t_ms)

                # Cooldown
                if t_ms - last_trade_time < cooldown_ms:
                    continue

                # Générer signal
                signals_generated += 1
                valid, direction, confidence, reason, details = generate_signal(
                    snap, symbol, config, hour, minute
                )

                if not valid:
                    signals_rejected += 1
                    rejection_counts[reason] += 1
                    continue

                # Simuler trade
                future = snapshots[i+1:i+301]
                if len(future) < 10:
                    continue

                trade = simulate_trade(
                    snap, direction, symbol, future, config,
                    details.get('session', 'UNKNOWN'), day,
                    confidence, details.get('distance', 0)
                )

                all_trades.append(trade)
                last_trade_time = t_ms
                day_trade_count += 1
                symbol_trade_count += 1
                day_has_trades = True

        if day_has_trades:
            days_with_data += 1

    # Calculer métriques
    if not all_trades:
        return BacktestResult(
            config_name=config['name'],
            trades=[],
            total_pnl=0,
            win_rate=0,
            profit_factor=0,
            total_trades=0,
            avg_trades_per_day=0,
            signals_generated=signals_generated,
            signals_rejected=signals_rejected,
            rejection_rate=100 if signals_generated > 0 else 0,
            rejection_reasons=dict(rejection_counts),
            es_stats={},
            nq_stats={},
            by_session={},
        )

    total_pnl = sum(t.pnl_usd for t in all_trades)
    profitable = [t for t in all_trades if t.pnl_usd > 0]
    win_rate = len(profitable) / len(all_trades) * 100

    gross_profit = sum(t.pnl_usd for t in all_trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in all_trades if t.pnl_usd < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999

    # Stats par symbole
    es_trades = [t for t in all_trades if t.symbol == "ES"]
    nq_trades = [t for t in all_trades if t.symbol == "NQ"]

    es_stats = {
        'trades': len(es_trades),
        'pnl': sum(t.pnl_usd for t in es_trades),
        'wr': len([t for t in es_trades if t.pnl_usd > 0]) / len(es_trades) * 100 if es_trades else 0,
    }

    nq_stats = {
        'trades': len(nq_trades),
        'pnl': sum(t.pnl_usd for t in nq_trades),
        'wr': len([t for t in nq_trades if t.pnl_usd > 0]) / len(nq_trades) * 100 if nq_trades else 0,
    }

    # Stats par session
    by_session = {}
    for session in ['london', 'us_morning', 'power_hour']:
        sess_trades = [t for t in all_trades if t.session == session]
        if sess_trades:
            by_session[session] = {
                'trades': len(sess_trades),
                'pnl': sum(t.pnl_usd for t in sess_trades),
                'wr': len([t for t in sess_trades if t.pnl_usd > 0]) / len(sess_trades) * 100,
            }

    rejection_rate = signals_rejected / signals_generated * 100 if signals_generated > 0 else 0

    return BacktestResult(
        config_name=config['name'],
        trades=all_trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        profit_factor=pf,
        total_trades=len(all_trades),
        avg_trades_per_day=len(all_trades) / max(1, days_with_data),
        signals_generated=signals_generated,
        signals_rejected=signals_rejected,
        rejection_rate=rejection_rate,
        rejection_reasons=dict(rejection_counts),
        es_stats=es_stats,
        nq_stats=nq_stats,
        by_session=by_session,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("                    🎯 BACKTEST FINAL MIA IA SYSTEM")
    print("                    Compare CURRENT vs SIMPLIFIED vs MINIMAL")
    print("=" * 100)
    print(f"""
📊 CONTEXTE (Audit Cursor 13 Déc):
   - Config actuelle: 39 points de blocage, MIN_CONF=1.00 (100%!), DIST=8t
   - Taux de rejet estimé: ~99%
   - Proposition: Simplifier à 5 filtres essentiels

⏰ SESSIONS CORRIGÉES:
   - London:     08:00 - 11:00 (3h00)
   - US Morning: 15:50 - 17:00 (1h10) ✅ CORRIGÉ!
   - Power Hour: 20:00 - 21:25 (1h25)
   - TOTAL: ~5h35/jour (+45min vs avant!)

💰 1 contrat MINI:
   - ES: $12.50/tick
   - NQ: $5.00/tick
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

    print(f"\n   📊 {days_loaded} jours chargés | {total_snapshots:,} snapshots")

    if days_loaded == 0:
        print("\n❌ Aucune donnée! Vérifie DATA_BASE_PATH")
        return

    # Exécuter backtests
    print("\n" + "=" * 100)
    print("                    🧪 EXÉCUTION DES BACKTESTS")
    print("=" * 100)

    results = {}
    config_list = list(CONFIGS.items())
    for idx, (config_name, config) in enumerate(config_list):
        print(f"\n▶ Backtest: {config['name']}...")
        progress_bar(0, 100, "Analyse", "Démarrage...")
        result = run_backtest(config, all_data, show_progress=True)
        results[config_name] = result
        print(f"   ✅ {result.total_trades} trades | WR: {result.win_rate:.1f}% | PnL: ${result.total_pnl:+,.0f}")

    # Afficher résultats comparatifs
    print("\n" + "=" * 100)
    print("                    📊 RÉSULTATS COMPARATIFS")
    print("=" * 100)

    print(f"\n{'Config':<35} {'Trades':>8} {'T/Jour':>7} {'WR%':>7} {'PnL':>12} {'PF':>6} {'Rejet%':>8}")
    print("-" * 100)

    for name, r in results.items():
        print(f"{r.config_name:<35} {r.total_trades:>8} {r.avg_trades_per_day:>6.1f} {r.win_rate:>6.1f}% ${r.total_pnl:>+10,.0f} {r.profit_factor:>5.2f} {r.rejection_rate:>7.1f}%")

    print("-" * 100)

    # Détails par config
    for name, r in results.items():
        print(f"\n{'─'*50}")
        print(f"📊 {r.config_name}")
        print(f"{'─'*50}")

        if r.total_trades > 0:
            print(f"   Trades: {r.total_trades} sur {days_loaded} jours ({r.avg_trades_per_day:.1f}/jour)")
            print(f"   Win Rate: {r.win_rate:.1f}%")
            print(f"   P&L: ${r.total_pnl:+,.2f}")
            print(f"   Profit Factor: {r.profit_factor:.2f}")

            print(f"\n   📈 Par Symbole:")
            if r.es_stats:
                print(f"      ES: {r.es_stats['trades']} trades | WR: {r.es_stats['wr']:.0f}% | PnL: ${r.es_stats['pnl']:+,.0f}")
            if r.nq_stats:
                print(f"      NQ: {r.nq_stats['trades']} trades | WR: {r.nq_stats['wr']:.0f}% | PnL: ${r.nq_stats['pnl']:+,.0f}")

            if r.by_session:
                print(f"\n   ⏰ Par Session:")
                for sess, data in r.by_session.items():
                    print(f"      {sess:<12}: {data['trades']:>3} trades | WR: {data['wr']:.0f}% | PnL: ${data['pnl']:+,.0f}")

        # Top raisons de rejet
        if r.rejection_reasons:
            print(f"\n   🚫 Top Raisons de Rejet:")
            sorted_reasons = sorted(r.rejection_reasons.items(), key=lambda x: -x[1])[:5]
            for reason, count in sorted_reasons:
                pct = count / r.signals_generated * 100 if r.signals_generated > 0 else 0
                print(f"      • {reason[:40]:<40}: {count:>5} ({pct:.1f}%)")

    # Conclusion
    print("\n" + "=" * 100)
    print("                    🎯 CONCLUSION")
    print("=" * 100)

    current = results.get('CURRENT')
    simplified = results.get('SIMPLIFIED')

    if current and simplified:
        trade_diff = simplified.total_trades - current.total_trades
        pnl_diff = simplified.total_pnl - current.total_pnl

        print(f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  IMPACT DE LA SIMPLIFICATION                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Trades:      {current.total_trades:>4} → {simplified.total_trades:>4}  ({trade_diff:+d} trades)                              │
│  Win Rate:    {current.win_rate:>5.1f}% → {simplified.win_rate:>5.1f}%                                          │
│  P&L:         ${current.total_pnl:>+8,.0f} → ${simplified.total_pnl:>+8,.0f}  (${pnl_diff:+,.0f})                     │
│  Rejet:       {current.rejection_rate:>5.1f}% → {simplified.rejection_rate:>5.1f}%                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  VERDICT: {'✅ SIMPLIFIER!' if pnl_diff > 0 else '⚠️ Ajuster paramètres'}                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
""")

    # Code pour production si SIMPLIFIED est meilleur
    if simplified and simplified.total_pnl > 0 and simplified.win_rate > 50:
        print("""
🚀 CODE POUR PRODUCTION (config/trading_params.py):
─────────────────────────────────────────────────────

# SEUILS SIMPLIFIÉS (validés par backtest)
MIN_TOTAL_CONFIDENCE = {
    'ES': 0.50,
    'NQ': 0.50,
}

MAX_DISTANCE_TO_LEVEL = {
    'ES': 15,  # ticks
    'NQ': 20,  # ticks
}

# DÉSACTIVER les filtres over-engineered
MIN_PRESSURE_STRENGTH_BY_SYMBOL = {'ES': 0.0, 'NQ': 0.0, 'RTY': 0.0}
ENABLE_TREND_FILTER = False
ENABLE_ORDERFLOW_CONTRA_FILTER = False
""")

    # Sauvegarder CSV
    csv_path = Path("backtest_comparison_results.csv")
    with open(csv_path, 'w') as f:
        f.write("Config,Trades,TradesPerDay,WinRate,PnL,PF,RejectRate,ES_Trades,ES_PnL,NQ_Trades,NQ_PnL\n")
        for name, r in results.items():
            es_t = r.es_stats.get('trades', 0) if r.es_stats else 0
            es_p = r.es_stats.get('pnl', 0) if r.es_stats else 0
            nq_t = r.nq_stats.get('trades', 0) if r.nq_stats else 0
            nq_p = r.nq_stats.get('pnl', 0) if r.nq_stats else 0
            f.write(f"{name},{r.total_trades},{r.avg_trades_per_day:.1f},{r.win_rate:.1f},{r.total_pnl:.2f},{r.profit_factor:.2f},{r.rejection_rate:.1f},{es_t},{es_p:.2f},{nq_t},{nq_p:.2f}\n")

    print(f"\n✅ Résultats sauvegardés: {csv_path}")
    print("\n✅ BACKTEST TERMINÉ!")


if __name__ == "__main__":
    main()
