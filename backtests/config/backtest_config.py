"""
⚙️ CONFIGURATION PARTAGÉE BACKTESTS
====================================

Ce fichier centralise TOUTES les configurations utilisées dans les backtests.
Les valeurs DOIVENT correspondre exactement à config/unified_thresholds.py

Dernière mise à jour: 06/12/2025
"""

from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, field
from collections import defaultdict

# 🎯 CONFIG CENTRALISÉE - Source unique de vérité pour TP/SL/Distance
from config.trading_params import (
    TRADING_CONFIG,
    TP_SL_CONFIG as TRADING_TP_SL_CONFIG,
    MAX_DISTANCE_TO_LEVEL as TRADING_MAX_DISTANCE,
    TICK_VALUE as TRADING_TICK_VALUE,
    TICK_SIZE as TRADING_TICK_SIZE
)

# ============================================================================
# 📁 CHEMINS DES DONNÉES
# ============================================================================

BASE_DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART")

def get_data_path(year: int, month: str) -> Path:
    """Retourne le chemin des données pour un mois donné"""
    return BASE_DATA_PATH / f"DATA_{year}" / month.upper()

# Mapping chart Sierra Chart
CHART_MAPPING = {
    'ES': 3,    # ESZ25_FUT_CME
    'NQ': 9,    # NQZ25_FUT_CME
    'RTY': 1,   # RTYZ25_FUT_CME
    'GC': 2,    # Gold Futures
    'CL': 4,    # Crude Oil Futures
}

# ============================================================================
# 📊 SYMBOLES
# ============================================================================

SYMBOLS = ['ES', 'NQ']  # Symboles tradés en production actuellement
ALL_SYMBOLS = ['ES', 'NQ', 'RTY', 'GC', 'CL']  # Tous les symboles disponibles

# ============================================================================
# 🕐 SESSIONS DE TRADING (Heure Paris)
# ============================================================================

TRADING_SESSIONS = {
    "London": {"start": (8, 0), "end": (11, 0)},
    "US Morning": {"start": (15, 50), "end": (17, 0)},
    "US Power Hour": {"start": (20, 0), "end": (21, 30)}
}

# Sessions exclues
EXCLUDED_SESSIONS = ["ASIA", "Pre-US", "Lunch", "Closed"]

# ============================================================================
# 🧠 SEUILS ML 3-LAYER (Production 05/12/2025)
# ============================================================================

# Seuil de confiance total minimum
MIN_TOTAL_CONFIDENCE = {
    'ES': 0.30,
    'NQ': 0.30,
    'RTY': 0.42,
    'GC': 0.35,   # À optimiser via backtest
    'CL': 0.35,   # À optimiser via backtest
}

# Seuils par layer
MIN_LAYER_CONFIDENCE = {
    'ES': {'layer1': 0.40, 'layer2': 0.17, 'layer3': 0.14},  # 🔥 07/12: layer1 0.50→0.40 (compromis)
    'NQ': {'layer1': 0.30, 'layer2': 0.20, 'layer3': 0.16},
    'RTY': {'layer1': 0.30, 'layer2': 0.20, 'layer3': 0.20},
    'GC': {'layer1': 0.35, 'layer2': 0.20, 'layer3': 0.15},  # À optimiser
    'CL': {'layer1': 0.35, 'layer2': 0.20, 'layer3': 0.15},  # À optimiser
}

# ============================================================================
# 📏 DISTANCES AUX NIVEAUX - IMPORTÉ DEPUIS config/trading_params.py
# ⚠️ MODIFIER UNIQUEMENT trading_params.py POUR CHANGER CES VALEURS!
# ============================================================================

MAX_DISTANCE_TO_LEVEL = TRADING_MAX_DISTANCE.copy()
# Ajouter GC et CL s'ils n'existent pas
MAX_DISTANCE_TO_LEVEL.setdefault('GC', 20)
MAX_DISTANCE_TO_LEVEL.setdefault('CL', 20)

# Niveaux MenthorQ prioritaires
PRIORITY_LEVELS = ['hvl', 'vah', 'val', 'poc', '1d_max', '1d_min']
GAMMA_LEVELS = ['call_resistance', 'put_support']
GEX_LEVELS = [f'gex_{i}' for i in range(1, 11)]
BLIND_SPOTS = [f'blind_spot_{i}' for i in range(0, 9)]

# ============================================================================
# 💰 TP/SL CONFIGURATION - IMPORTÉ DEPUIS config/trading_params.py
# ⚠️ MODIFIER UNIQUEMENT trading_params.py POUR CHANGER CES VALEURS!
# ============================================================================

TP_SL_CONFIG = TRADING_TP_SL_CONFIG.copy()
# Ajouter GC et CL s'ils n'existent pas
TP_SL_CONFIG.setdefault('GC', {'tp_ticks': 30, 'sl_ticks': 20})
TP_SL_CONFIG.setdefault('CL', {'tp_ticks': 30, 'sl_ticks': 20})

# Valeurs tick - IMPORTÉ DEPUIS config/trading_params.py
TICK_VALUES = TRADING_TICK_VALUE.copy()
TICK_VALUES.setdefault('GC', 10.00)
TICK_VALUES.setdefault('CL', 10.00)

TICK_SIZES = TRADING_TICK_SIZE.copy()
TICK_SIZES.setdefault('GC', 0.10)
TICK_SIZES.setdefault('CL', 0.01)

# ============================================================================
# 🆕 PRESSURE_STRENGTH PAR SESSION (Backtest 06/12/2025)
# ============================================================================

MIN_PRESSURE_BY_SESSION = {
    'London': 0.10,        # Session stricte
    'US Morning': 0.03,    # Session souple (très rentable)
    'US Power Hour': 0.10, # Session intermédiaire
    'ASIA': 0.50,          # Désactivé
    'Pre-US': 0.50,        # Désactivé
    'Lunch': 0.50,         # Désactivé
    'Closed': 0.50,        # Désactivé
}

# 🔥 AJOUTÉ 07/12/2025: Seuil pressure par SYMBOLE
MIN_PRESSURE_BY_SYMBOL = {
    'ES': 0.20,    # ES nécessite un pressure plus fort
    'NQ': 0.03,    # NQ reste souple
    'RTY': 0.10,   # Standard
    'GC': 0.10,    # Standard
    'CL': 0.10,    # Standard
}

# ============================================================================
# ⏱️ COOLDOWNS ET LIMITES
# ============================================================================

COOLDOWN_MS = 300000  # 5 minutes entre trades
MAX_TRADE_DURATION_MS = 30 * 60 * 1000  # 30 minutes max par trade
MAX_SNAPSHOTS_LOOKAHEAD = 1000  # Snapshots à analyser pour TP/SL

# ============================================================================
# 📊 CLASSES UTILITAIRES
# ============================================================================

@dataclass
class MLScores:
    """Scores ML 3-Layer"""
    layer1: float = 0.0
    layer2: float = 0.0
    layer3: float = 0.0
    total: float = 0.0

    def meets_thresholds(self, symbol: str) -> tuple:
        """Vérifie si les scores passent les seuils production"""
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
    """Signal de trading"""
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
    """Résultat d'un trade simulé"""
    signal: Signal
    result: str  # WIN, LOSS, BE
    pnl_ticks: float
    pnl_usd: float
    exit_reason: str


@dataclass
class BacktestStats:
    """Statistiques de backtest"""
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
    by_session: Dict = field(default_factory=lambda: defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0}))
    by_symbol: Dict = field(default_factory=lambda: defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0}))
    by_date: Dict = field(default_factory=lambda: defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0}))

    @property
    def win_rate(self) -> float:
        return self.wins / max(self.trades_executed, 1) * 100


# ============================================================================
# 🔧 FONCTIONS UTILITAIRES
# ============================================================================

def get_session(ts_ms: int) -> tuple:
    """
    Retourne (in_session, session_name) pour un timestamp
    Note: Approximation UTC+1 pour Paris
    """
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    h_paris = (dt.hour + 1) % 24  # Approximation UTC+1
    m = dt.minute

    if 8 <= h_paris < 11:
        return True, "London"
    elif (h_paris == 15 and m >= 50) or h_paris == 16:
        return True, "US Morning"
    elif h_paris == 20 or (h_paris == 21 and m < 30):
        return True, "US Power Hour"
    else:
        return False, "Closed"


def get_distance_to_level(snap: dict, price: float, symbol: str) -> tuple:
    """
    Calcule la distance au niveau le plus proche
    Retourne (distance_ticks, level_name)
    """
    tick = TICK_SIZES.get(symbol, 0.25)
    levels = []

    # Niveaux priorité haute
    for key in PRIORITY_LEVELS:
        val = snap.get(key)
        if val and val > 0:
            levels.append((abs(price - val) / tick, key))

    # Gamma walls
    for key in GAMMA_LEVELS:
        val = snap.get(key)
        if val and val > 0:
            levels.append((abs(price - val) / tick, key))

    # GEX levels
    for key in GEX_LEVELS:
        val = snap.get(key)
        if val and val > 0:
            levels.append((abs(price - val) / tick, key))

    # Blind spots
    for key in BLIND_SPOTS:
        val = snap.get(key)
        if val and val > 0:
            levels.append((abs(price - val) / tick, key))

    # VWAP
    val = snap.get('vwap')
    if val and val > 0:
        levels.append((abs(price - val) / tick, 'vwap'))

    if not levels:
        return 9999, "none"

    levels.sort(key=lambda x: x[0])
    return levels[0]


def load_snapshots(date_str: str, symbol: str, month: str = "DECEMBRE", year: int = 2025) -> list:
    """
    Charge les snapshots ML_READY pour une date et symbole
    date_str format: YYYYMMDD (ex: "20251205")
    """
    import json

    chart_id = CHART_MAPPING.get(symbol)
    if not chart_id:
        return []

    path = get_data_path(year, month) / date_str / f"CHART_{chart_id}" / "ML_READY"

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
