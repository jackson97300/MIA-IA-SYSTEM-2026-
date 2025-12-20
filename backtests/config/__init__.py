"""
Configuration partagée pour les backtests
"""

from .backtest_config import (
    # Paths
    BASE_DATA_PATH, get_data_path, CHART_MAPPING,

    # Symboles
    SYMBOLS, ALL_SYMBOLS,

    # Sessions
    TRADING_SESSIONS, EXCLUDED_SESSIONS,

    # Seuils ML
    MIN_TOTAL_CONFIDENCE, MIN_LAYER_CONFIDENCE,

    # Distances
    MAX_DISTANCE_TO_LEVEL,
    PRIORITY_LEVELS, GAMMA_LEVELS, GEX_LEVELS, BLIND_SPOTS,

    # TP/SL
    TP_SL_CONFIG, TICK_VALUES, TICK_SIZES,

    # Pressure
    MIN_PRESSURE_BY_SESSION,

    # Cooldowns
    COOLDOWN_MS, MAX_TRADE_DURATION_MS, MAX_SNAPSHOTS_LOOKAHEAD,

    # Classes
    MLScores, Signal, TradeResult, BacktestStats,

    # Fonctions
    get_session, get_distance_to_level, load_snapshots
)

__all__ = [
    'BASE_DATA_PATH', 'get_data_path', 'CHART_MAPPING',
    'SYMBOLS', 'ALL_SYMBOLS',
    'TRADING_SESSIONS', 'EXCLUDED_SESSIONS',
    'MIN_TOTAL_CONFIDENCE', 'MIN_LAYER_CONFIDENCE',
    'MAX_DISTANCE_TO_LEVEL',
    'PRIORITY_LEVELS', 'GAMMA_LEVELS', 'GEX_LEVELS', 'BLIND_SPOTS',
    'TP_SL_CONFIG', 'TICK_VALUES', 'TICK_SIZES',
    'MIN_PRESSURE_BY_SESSION',
    'COOLDOWN_MS', 'MAX_TRADE_DURATION_MS', 'MAX_SNAPSHOTS_LOOKAHEAD',
    'MLScores', 'Signal', 'TradeResult', 'BacktestStats',
    'get_session', 'get_distance_to_level', 'load_snapshots'
]
