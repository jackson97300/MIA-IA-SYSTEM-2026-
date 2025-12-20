"""
MIA_IA_SYSTEM - Constants Configuration
Centralisation de toutes les constantes et magic numbers
Version: Production Ready v2.1 (PRIORITÉ #2 APPLIQUÉE)

PRIORITÉ #2: RECALIBRAGE SEUILS APPLIQUÉ
- Nouveaux seuils Battle Navale: 0.25/-0.25 (vs 0.35/-0.35)
- Seuils confluence ajustés pour cohérence
- Paramètres optimisés pour +150% fréquence signaux
- Targets performance: +2-3% win rate

Ce fichier centralise TOUTES les constantes utilisées dans le système
pour éviter les magic numbers et faciliter la maintenance.
"""

from enum import Enum
from typing import Dict, Any

# === PRIORITÉ #2: NOUVEAUX SEUILS BATTLE NAVALE ===

# Seuils Battle Navale principaux
BATTLE_NAVALE_THRESHOLDS = {
    'priority_2_new': {
        'long_threshold': 0.25,     # NOUVEAU: Abaissé de 0.35
        'short_threshold': -0.25,   # NOUVEAU: Abaissé de -0.35
        'version': '2.1.0',
        'description': 'Seuils calibrés PRIORITÉ #2 pour +150% fréquence'
    },
    'legacy_original': {
        'long_threshold': 0.35,     # ANCIEN: Référence
        'short_threshold': -0.35,   # ANCIEN: Référence
        'version': '1.0.0',
        'description': 'Seuils originaux avant PRIORITÉ #2'
    },
    'adaptive': {
        'long_threshold_min': 0.20,
        'long_threshold_max': 0.40,
        'short_threshold_min': -0.40,
        'short_threshold_max': -0.20,
        'description': 'Seuils adaptatifs selon conditions marché'
    }
}

# Seuils qualité Battle Navale (PRIORITÉ #2: Ajustés)
BATTLE_NAVALE_QUALITY_THRESHOLDS = {
    'premium': 0.75,      # Signaux premium (>75%)
    'strong': 0.60,       # Signaux strong (60-75%)
    'moderate': 0.45,     # Signaux modérés (45-60%) - Abaissé de 0.50
    'weak': 0.30,         # Signaux faibles (30-45%) - Abaissé de 0.35
    'rejected': 0.15      # Seuil rejet (< 15%) - Abaissé de 0.20
}

# Targets performance PRIORITÉ #2
PRIORITY_2_TARGETS = {
    'frequency_boost_target_pct': 150.0,    # +150% fréquence signaux
    'frequency_boost_min_pct': 120.0,       # Minimum +120% acceptable
    'win_rate_boost_target_pct': 2.5,       # +2.5% win rate ciblé
    'win_rate_degradation_max_pct': 1.0,    # Max -1% win rate acceptable
    'signal_generation_rate_target': 25,     # 25 signaux/jour cible vs 10
    'confidence_threshold_adjustment': -0.05  # Seuils confidence abaissés de 5%
}

# === TRADING CONSTANTS ===

# Contract Specifications
ES_FUTURES = {
    'symbol': 'ES',
    'name': 'E-mini S&P 500',
    'tick_size': 0.25,
    'tick_value': 12.50,
    'multiplier': 50,
    'margin_initial': 13200,
    'margin_maintenance': 12000,
    'trading_hours': {
        'sunday_open': '18:00',
        'friday_close': '17:00',
        'daily_open': '09:30',
        'daily_close': '16:00'
    }
}

MES_FUTURES = {
    'symbol': 'MES',
    'name': 'Micro E-mini S&P 500',
    'tick_size': 0.25,
    'tick_value': 1.25,
    'multiplier': 5,
    'margin_initial': 1320,
    'margin_maintenance': 1200,
    'trading_hours': ES_FUTURES['trading_hours']  # Mêmes horaires
}

# === SIGNAL GENERATION THRESHOLDS (PRIORITÉ #2: AJUSTÉS) ===

# Confidence Thresholds par mode (PRIORITÉ #2: Abaissés)
CONFIDENCE_THRESHOLDS = {
    'data_collection': {
        'min_battle_navale': 0.25,      # ABAISSÉ: 0.35 → 0.25
        'min_confluence': 0.30,         # ABAISSÉ: 0.35 → 0.30
        'min_pattern_strength': 0.25,   # ABAISSÉ: 0.30 → 0.25
        'min_regime_confidence': 0.25   # ABAISSÉ: 0.30 → 0.25
    },
    'paper_trading': {
        'min_battle_navale': 0.60,      # ABAISSÉ: 0.65 → 0.60
        'min_confluence': 0.45,         # ABAISSÉ: 0.50 → 0.45
        'min_pattern_strength': 0.50,   # ABAISSÉ: 0.55 → 0.50
        'min_regime_confidence': 0.55   # ABAISSÉ: 0.60 → 0.55
    },
    'live_trading': {
        'min_battle_navale': 0.70,      # ABAISSÉ: 0.75 → 0.70
        'min_confluence': 0.60,         # ABAISSÉ: 0.65 → 0.60
        'min_pattern_strength': 0.65,   # ABAISSÉ: 0.70 → 0.65
        'min_regime_confidence': 0.65   # ABAISSÉ: 0.70 → 0.65
    },
    'conservative': {
        'min_battle_navale': 0.75,      # ABAISSÉ: 0.80 → 0.75
        'min_confluence': 0.65,         # ABAISSÉ: 0.70 → 0.65
        'min_pattern_strength': 0.70,   # ABAISSÉ: 0.75 → 0.70
        'min_regime_confidence': 0.70   # ABAISSÉ: 0.75 → 0.70
    },
    # NOUVEAU: Mode PRIORITÉ #2 spécifique
    'priority_2_optimized': {
        'min_battle_navale': 0.25,      # Seuils PRIORITÉ #2
        'min_confluence': 0.40,
        'min_pattern_strength': 0.45,
        'min_regime_confidence': 0.50
    }
}

# Pattern Detection Thresholds
PATTERN_THRESHOLDS = {
    'gamma_pin': {
        'min_gamma_exposure': 0.7,
        'min_distance_percentage': 0.002,  # 0.2%
        'max_distance_points': 10.0
    },
    'headfake': {
        'min_volume_spike': 1.5,  # 150% du volume moyen
        'min_reversal_ticks': 4,
        'max_time_seconds': 300  # 5 minutes
    },
    'microstructure': {
        'min_anomaly_score': 0.6,
        'min_imbalance_ratio': 0.7,
        'min_absorption_score': 0.65
    }
}

# === RISK MANAGEMENT CONSTANTS (PRIORITÉ #2: AJUSTÉS) ===

# Position Sizing (PRIORITÉ #2: Adaptations)
POSITION_SIZING = {
    'min_position_size': 1,
    'max_position_size': {
        'data_collection': 3,
        'paper_trading': 2,
        'live_trading': 1,
        'conservative': 1,
        'priority_2_mode': 2          # NOUVEAU: Mode PRIORITÉ #2
    },
    'kelly_fraction': {
        'aggressive': 0.25,
        'moderate': 0.20,
        'conservative': 0.15,
        'priority_2_adjusted': 0.18    # NOUVEAU: Fraction ajustée
    },
    # PRIORITÉ #2: Paramètres fréquence accrue
    'signal_frequency_multiplier': 2.5,  # +150% fréquence attendue
    'position_size_reduction_factor': 0.8 # Réduction taille car plus de trades
}

# Risk Limits par mode (PRIORITÉ #2: Ajustés pour fréquence accrue)
RISK_LIMITS = {
    'data_collection': {
        'daily_loss_limit': 5000.0,
        'max_daily_trades': 100,
        'stop_loss_ticks': 20,
        'take_profit_ticks': 40,
        'max_risk_per_trade': 500.0
    },
    'paper_trading': {
        'daily_loss_limit': 1000.0,
        'max_daily_trades': 30,          # AUGMENTÉ: 20 → 30 pour PRIORITÉ #2
        'stop_loss_ticks': 12,
        'take_profit_ticks': 24,
        'max_risk_per_trade': 160.0      # RÉDUIT: 200 → 160 (plus de trades)
    },
    'live_trading': {
        'daily_loss_limit': 500.0,
        'max_daily_trades': 15,          # AUGMENTÉ: 10 → 15 pour PRIORITÉ #2
        'stop_loss_ticks': 8,
        'take_profit_ticks': 16,
        'max_risk_per_trade': 80.0       # RÉDUIT: 100 → 80 (plus de trades)
    },
    'conservative': {
        'daily_loss_limit': 300.0,
        'max_daily_trades': 8,           # AUGMENTÉ: 5 → 8 pour PRIORITÉ #2
        'stop_loss_ticks': 6,
        'take_profit_ticks': 12,
        'max_risk_per_trade': 60.0       # RÉDUIT: 75 → 60 (plus de trades)
    },
    # NOUVEAU: Risk limits PRIORITÉ #2
    'priority_2_optimized': {
        'daily_loss_limit': 800.0,
        'max_daily_trades': 25,          # Cible fréquence accrue
        'stop_loss_ticks': 10,
        'take_profit_ticks': 20,
        'max_risk_per_trade': 120.0
    }
}

# Stop Loss & Take Profit Rules
STOP_TAKE_PROFIT_RULES = {
    'min_risk_reward_ratio': 1.2,
    'breakeven_trigger_ticks': 8,
    'trailing_stop_activation_ticks': 12,
    'trailing_stop_distance_ticks': 6,
    'max_stop_loss_ticks': 20,
    'emergency_stop_ticks': 40,
    # PRIORITÉ #2: Ajustements
    'priority_2_min_rr_ratio': 1.1,     # RR ratio réduit car plus de trades
    'priority_2_breakeven_trigger': 6   # Breakeven plus rapide
}

# === PERFORMANCE TARGETS (PRIORITÉ #2: AJUSTÉS) ===

PERFORMANCE_METRICS = {
    'target_win_rate': 0.62,            # AUGMENTÉ: 0.60 → 0.62 (+2% cible)
    'min_acceptable_win_rate': 0.57,    # AUGMENTÉ: 0.55 → 0.57
    'target_profit_factor': 1.5,
    'min_profit_factor': 1.3,
    'target_sharpe_ratio': 1.5,
    'min_sharpe_ratio': 1.0,
    'max_drawdown_percent': 10.0,       # 10%
    'daily_profit_target': 500.0,
    'weekly_profit_target': 2000.0,
    'monthly_profit_target': 8000.0,
    # PRIORITÉ #2: Nouveaux targets
    'priority_2_win_rate_target': 0.63,    # +3% win rate cible
    'priority_2_signal_frequency_target': 25,  # 25 signaux/jour vs 10
    'priority_2_daily_profit_target': 600.0    # Augmenté avec fréquence
}

# Latency Targets (millisecondes) - PRIORITÉ #2: Optimisés
LATENCY_TARGETS = {
    'max_signal_generation_ms': 40,      # RÉDUIT: 50 → 40 pour fréquence
    'max_feature_calculation_ms': 15,    # RÉDUIT: 20 → 15 pour fréquence
    'max_order_execution_ms': 100,
    'max_end_to_end_ms': 180,           # RÉDUIT: 200 → 180
    'warning_latency_ms': 120,          # RÉDUIT: 150 → 120
    'critical_latency_ms': 250,         # RÉDUIT: 300 → 250
    'analysis_frequency_ms': 800,       # RÉDUIT: 1000 → 800 pour réactivité
    # PRIORITÉ #2: Targets spécifiques
    'priority_2_signal_gen_target_ms': 30,
    'priority_2_total_latency_target_ms': 150
}

# === FEATURE CALCULATION CONSTANTS (PRIORITÉ #2: AJUSTÉS) ===

# Feature Weights pour confluence (PRIORITÉ #2: Repondération)
FEATURE_WEIGHTS = {
    'battle_navale_signal': 0.30,       # AUGMENTÉ: 0.25 → 0.30 (plus important)
    'gamma_pin_strength': 0.15,
    'market_regime_alignment': 0.15,
    'headfake_signal': 0.10,
    'microstructure_score': 0.10,
    'volume_confirmation': 0.08,        # RÉDUIT: 0.10 → 0.08
    'trend_strength': 0.08,             # RÉDUIT: 0.10 → 0.08
    'session_context': 0.04             # RÉDUIT: 0.05 → 0.04
}

# Feature Weights PRIORITÉ #2 (pondération optimisée)
PRIORITY_2_FEATURE_WEIGHTS = {
    'battle_navale_signal': 0.35,       # Poids maximal pour PRIORITÉ #2
    'confluence_score': 0.20,
    'market_regime_alignment': 0.15,
    'pattern_strength': 0.12,
    'volume_confirmation': 0.10,
    'session_context': 0.08
}

# Lookback Periods
LOOKBACK_PERIODS = {
    'vwap_period': 390,  # Minutes dans session régulière
    'trend_period': 20,   # Barres pour trend
    'volume_average': 20,  # Barres pour volume moyen
    'atr_period': 14,     # ATR standard
    'momentum_period': 10,  # Momentum
    # PRIORITÉ #2: Periods optimisés
    'priority_2_short_period': 8,   # Périodes plus courtes pour réactivité
    'priority_2_medium_period': 15,
    'priority_2_long_period': 25
}

# === BATTLE NAVALE CONSTANTS (PRIORITÉ #2: COMPLETS) ===

BATTLE_NAVALE_PARAMS = {
    # Paramètres principaux (PRIORITÉ #2)
    'long_threshold': BATTLE_NAVALE_THRESHOLDS['priority_2_new']['long_threshold'],
    'short_threshold': BATTLE_NAVALE_THRESHOLDS['priority_2_new']['short_threshold'],
    
    # Qualité bases
    'min_base_quality': 0.5,
    'min_base_size_ticks': 4,
    'max_base_size_ticks': 20,
    'min_touches_for_validation': 2,
    
    # Règle d'or
    'golden_rule_lookback_bars': 10,
    'trend_continuation_threshold': 0.7,
    'vikings_dominance_threshold': 0.65,
    
    # Timing
    'base_formation_time_min': 5,   # minutes
    'base_formation_time_max': 60,  # minutes
    
    # PRIORITÉ #2: Nouveaux paramètres
    'signal_strength_multiplier': 1.5,      # Amplification force signal
    'quality_threshold_reduction': 0.1,     # Réduction seuils qualité
    'frequency_boost_factor': 2.5,          # Facteur boost fréquence
    'validation_strictness': 0.8,           # Validation moins stricte
    
    # Vikings vs Défenseurs (PRIORITÉ #2: Ajustés)
    'vikings_min_strength': 0.55,           # RÉDUIT: Pour plus de signaux
    'defenders_min_strength': 0.55,         # RÉDUIT: Pour plus de signaux
    'battle_balance_threshold': 0.45,       # RÉDUIT: Plus de signaux équilibrés
    
    # Performance tracking
    'track_old_vs_new_signals': True,
    'compare_threshold_performance': True,
    'log_signal_frequency': True
}

# === CONFLUENCE THRESHOLDS (PRIORITÉ #2: AJUSTÉS) ===

CONFLUENCE_THRESHOLDS = {
    'premium': 0.75,     # Maintenu - Signaux premium
    'strong': 0.65,      # RÉDUIT: 0.70 → 0.65
    'moderate': 0.55,    # RÉDUIT: 0.60 → 0.55 
    'weak': 0.45,        # RÉDUIT: 0.50 → 0.45
    'minimum': 0.35,     # RÉDUIT: 0.40 → 0.35
    # PRIORITÉ #2: Seuils spécifiques
    'priority_2_premium': 0.70,
    'priority_2_strong': 0.60,
    'priority_2_moderate': 0.50,
    'priority_2_weak': 0.40
}

# === MONITORING & ALERTS (PRIORITÉ #2: ÉTENDUS) ===

MONITORING_PARAMS = {
    'health_check_interval_seconds': 60,
    'performance_update_interval_seconds': 300,  # 5 minutes
    'position_sync_interval_seconds': 10,
    'heartbeat_interval_seconds': 30,
    'metric_history_size': 1000,
    'alert_cooldown_seconds': 300,  # 5 minutes entre alertes similaires
    # PRIORITÉ #2: Monitoring spécifique
    'frequency_tracking_interval_seconds': 60,
    'threshold_comparison_interval_seconds': 180,
    'performance_alert_frequency_seconds': 600  # 10 minutes
}

ALERT_THRESHOLDS = {
    'cpu_usage_warning': 80,  # %
    'cpu_usage_critical': 95,
    'memory_usage_warning': 80,
    'memory_usage_critical': 95,
    'disk_space_warning_gb': 5,
    'disk_space_critical_gb': 1,
    'consecutive_errors_warning': 5,
    'consecutive_errors_critical': 10,
    'loss_alert_threshold': 100.0,  # $
    'drawdown_alert_percent': 5.0,
    # PRIORITÉ #2: Alertes spécifiques
    'frequency_miss_alert_percent': 20.0,     # Alert si fréquence < target -20%
    'win_rate_degradation_alert_percent': 2.0, # Alert si win rate baisse > 2%
    'signal_generation_rate_low': 15,         # Alert si < 15 signaux/jour
    'threshold_performance_deviation': 10.0   # Alert si performance dévie > 10%
}

# === ML CONSTANTS ===

ML_PARAMETERS = {
    'min_training_samples': 1000,
    'max_training_samples': 10000,
    'train_test_split': 0.2,
    'cross_validation_folds': 5,
    'feature_importance_threshold': 0.05,
    'model_accuracy_threshold': 0.65,
    'retraining_frequency_trades': 500,
    'model_decay_days': 30,
    'max_features_to_use': 8,
    'random_state': 42,  # Pour reproductibilité
    # PRIORITÉ #2: ML adaptations
    'include_threshold_features': True,
    'battle_navale_feature_weight': 0.35,
    'priority_2_model_suffix': '_p2'
}

# === DATA COLLECTION CONSTANTS ===

DATA_PARAMS = {
    'snapshot_compression': True,
    'snapshot_format': 'parquet',
    'max_snapshots_per_file': 1000,
    'data_retention_days': 90,
    'backup_frequency_hours': 24,
    'min_data_quality_score': 0.8,
    'outlier_z_score_threshold': 3.0,
    'missing_data_threshold_percent': 5.0,
    # PRIORITÉ #2: Data requirements
    'track_signal_frequency_data': True,
    'store_threshold_comparisons': True,
    'performance_data_retention_days': 180  # Plus long pour analyse
}

# === SIERRA CHART CONSTANTS ===

SIERRA_PARAMS = {
    'order_timeout_seconds': 30,
    'order_confirmation_timeout_ms': 5000,
    'max_order_retries': 3,
    'retry_delay_ms': 1000,
    'position_mismatch_tolerance': 0,
    'price_tolerance_ticks': 2,
    'max_slippage_ticks': 3
}

# === SESSION TIMING CONSTANTS ===

TRADING_SESSIONS = {
    'asian': {
        'start': '18:00',
        'end': '03:00',
        'volatility_multiplier': 0.7,
        'priority_2_signal_multiplier': 0.8  # NOUVEAU: Moins de signaux en Asie
    },
    'london': {
        'start': '03:00',
        'end': '09:30',
        'volatility_multiplier': 1.2,
        'priority_2_signal_multiplier': 1.1  # NOUVEAU: Plus de signaux Londres
    },
    'ny_morning': {
        'start': '09:30',
        'end': '12:00',
        'volatility_multiplier': 1.5,
        'priority_2_signal_multiplier': 1.3  # NOUVEAU: Maximum signaux NY
    },
    'lunch': {
        'start': '12:00',
        'end': '14:00',
        'volatility_multiplier': 0.8,
        'priority_2_signal_multiplier': 0.9  # NOUVEAU: Moins de signaux lunch
    },
    'ny_afternoon': {
        'start': '14:00',
        'end': '16:00',
        'volatility_multiplier': 1.3,
        'priority_2_signal_multiplier': 1.2  # NOUVEAU: Fort signaux PM
    },
    'close': {
        'start': '15:45',
        'end': '16:15',
        'volatility_multiplier': 1.8,
        'priority_2_signal_multiplier': 1.4  # NOUVEAU: Très fort à la clôture
    }
}

# === COMMISSION & FEES ===

TRADING_COSTS = {
    'es_futures': {
        'commission_per_side': 2.25,
        'exchange_fee': 1.18,
        'nfa_fee': 0.02,
        'total_per_side': 3.45,
        'total_round_trip': 6.90
    },
    'mes_futures': {
        'commission_per_side': 0.62,
        'exchange_fee': 0.32,
        'nfa_fee': 0.02,
        'total_per_side': 0.96,
        'total_round_trip': 1.92
    }
}

# === VALIDATION CONSTANTS ===

VALIDATION_RULES = {
    'min_price_es': 1000.0,
    'max_price_es': 10000.0,
    'min_volume': 100,
    'max_spread_ticks': 2,
    'max_gap_percent': 2.0,  # 2% gap max
    'min_liquidity_volume': 500,
    'max_order_age_seconds': 60,
    'stale_data_threshold_seconds': 5,
    # PRIORITÉ #2: Validations spécifiques
    'min_battle_navale_signal_quality': 0.25,
    'max_signal_generation_rate_per_minute': 5,
    'min_confidence_for_execution': 0.50
}

# === ERROR CODES ===


class ErrorCode(Enum):
    """Codes d'erreur standardisés"""
    SUCCESS = 0
    CONNECTION_ERROR = 1001
    DATA_ERROR = 1002
    VALIDATION_ERROR = 1003
    EXECUTION_ERROR = 2001
    RISK_LIMIT_ERROR = 2002
    POSITION_ERROR = 2003
    ORDER_REJECTED = 2004
    SYSTEM_ERROR = 3001
    CONFIG_ERROR = 3002
    CRITICAL_ERROR = 9999
    # PRIORITÉ #2: Nouveaux codes d'erreur
    THRESHOLD_VALIDATION_ERROR = 4001
    FREQUENCY_TARGET_MISS_ERROR = 4002
    PERFORMANCE_DEGRADATION_ERROR = 4003

# === HELPER FUNCTIONS ===


def get_risk_params_for_mode(mode: str) -> Dict[str, Any]:
    """Retourne les paramètres de risque pour un mode"""
    mode = mode.lower()
    if mode in RISK_LIMITS:
        return RISK_LIMITS[mode]
    return RISK_LIMITS['paper_trading']  # Default


def get_confidence_thresholds_for_mode(mode: str) -> Dict[str, float]:
    """Retourne les seuils de confiance pour un mode"""
    mode = mode.lower()
    if mode in CONFIDENCE_THRESHOLDS:
        return CONFIDENCE_THRESHOLDS[mode]
    return CONFIDENCE_THRESHOLDS['paper_trading']  # Default


def get_battle_navale_thresholds(priority_2_enabled: bool = True) -> Dict[str, float]:
    """
    PRIORITÉ #2: Retourne les seuils Battle Navale selon mode
    """
    if priority_2_enabled:
        return BATTLE_NAVALE_THRESHOLDS['priority_2_new']
    else:
        return BATTLE_NAVALE_THRESHOLDS['legacy_original']


def get_priority_2_feature_weights() -> Dict[str, float]:
    """
    PRIORITÉ #2: Retourne les poids features optimisés
    """
    return PRIORITY_2_FEATURE_WEIGHTS


def get_confluence_threshold(level: str, priority_2_enabled: bool = True) -> float:
    """
    PRIORITÉ #2: Retourne seuil confluence selon niveau et mode
    """
    level = level.lower()
    
    if priority_2_enabled:
        thresholds = {
            'premium': CONFLUENCE_THRESHOLDS['priority_2_premium'],
            'strong': CONFLUENCE_THRESHOLDS['priority_2_strong'],
            'moderate': CONFLUENCE_THRESHOLDS['priority_2_moderate'],
            'weak': CONFLUENCE_THRESHOLDS['priority_2_weak']
        }
    else:
        thresholds = {
            'premium': CONFLUENCE_THRESHOLDS['premium'],
            'strong': CONFLUENCE_THRESHOLDS['strong'],
            'moderate': CONFLUENCE_THRESHOLDS['moderate'],
            'weak': CONFLUENCE_THRESHOLDS['weak']
        }
    
    return thresholds.get(level, CONFLUENCE_THRESHOLDS['moderate'])


def calculate_priority_2_signal_target(base_signals_per_day: int) -> int:
    """
    PRIORITÉ #2: Calcule target signaux selon boost fréquence
    """
    frequency_multiplier = PRIORITY_2_TARGETS['frequency_boost_target_pct'] / 100
    return int(base_signals_per_day * (1 + frequency_multiplier))


def get_session_signal_multiplier(session: str, priority_2_enabled: bool = True) -> float:
    """
    PRIORITÉ #2: Retourne multiplicateur signaux pour session
    """
    if not priority_2_enabled:
        return 1.0
    
    session_data = TRADING_SESSIONS.get(session, {})
    return session_data.get('priority_2_signal_multiplier', 1.0)


def validate_priority_2_performance(win_rate: float, signal_frequency: float) -> Dict[str, bool]:
    """
    PRIORITÉ #2: Validation performance selon targets
    """
    targets = PRIORITY_2_TARGETS
    
    frequency_target = targets['frequency_boost_target_pct'] / 100 + 1.0  # 2.5 = +150%
    win_rate_min = 0.60 + targets['win_rate_boost_target_pct'] / 100  # 0.625 = +2.5%
    
    return {
        'frequency_target_met': signal_frequency >= frequency_target,
        'win_rate_target_met': win_rate >= win_rate_min,
        'performance_acceptable': (
            signal_frequency >= (frequency_target * 0.8) and  # Au moins 80% du target
            win_rate >= (win_rate_min - 0.01)  # Max -1% win rate
        )
    }


def get_contract_specs(symbol: str) -> Dict[str, Any]:
    """Retourne les spécifications d'un contrat"""
    symbol = symbol.upper()
    if symbol == 'ES':
        return ES_FUTURES
    elif symbol == 'MES':
        return MES_FUTURES
    else:
        raise ValueError(f"Symbole non supporté: {symbol}")


def calculate_dollar_value(ticks: float, symbol: str = 'ES') -> float:
    """Calcule la valeur en dollars d'un mouvement en ticks"""
    specs = get_contract_specs(symbol)
    return ticks * specs['tick_value']


def calculate_ticks(price_change: float, symbol: str = 'ES') -> float:
    """Calcule le nombre de ticks pour un changement de prix"""
    specs = get_contract_specs(symbol)
    return price_change / specs['tick_size']

# === EXPORTS ===


__all__ = [
    # PRIORITÉ #2: Nouveaux exports
    'BATTLE_NAVALE_THRESHOLDS',
    'BATTLE_NAVALE_QUALITY_THRESHOLDS',
    'PRIORITY_2_TARGETS',
    'PRIORITY_2_FEATURE_WEIGHTS',
    'CONFLUENCE_THRESHOLDS',

    # Contracts
    'ES_FUTURES',
    'MES_FUTURES',

    # Thresholds
    'CONFIDENCE_THRESHOLDS',
    'PATTERN_THRESHOLDS',

    # Risk
    'POSITION_SIZING',
    'RISK_LIMITS',
    'STOP_TAKE_PROFIT_RULES',

    # Performance
    'PERFORMANCE_METRICS',
    'LATENCY_TARGETS',

    # Features
    'FEATURE_WEIGHTS',
    'LOOKBACK_PERIODS',

    # Battle Navale
    'BATTLE_NAVALE_PARAMS',

    # Monitoring
    'MONITORING_PARAMS',
    'ALERT_THRESHOLDS',

    # ML
    'ML_PARAMETERS',

    # Data
    'DATA_PARAMS',

    # Sierra
    'SIERRA_PARAMS',

    # Sessions
    'TRADING_SESSIONS',

    # Costs
    'TRADING_COSTS',

    # Validation
    'VALIDATION_RULES',

    # Errors
    'ErrorCode',

    # Helper functions
    'get_risk_params_for_mode',
    'get_confidence_thresholds_for_mode',
    'get_battle_navale_thresholds',
    'get_priority_2_feature_weights',
    'get_confluence_threshold',
    'calculate_priority_2_signal_target',
    'get_session_signal_multiplier',
    'validate_priority_2_performance',
    'get_contract_specs',
    'calculate_dollar_value',
    'calculate_ticks'
]