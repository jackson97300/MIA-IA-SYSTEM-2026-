#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Bracket Trading Configuration
Configuration complète pour le trading de ranges/brackets
Paramètres validés par l'utilisateur le 31 octobre 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import time

@dataclass
class BracketConfig:
    """Configuration pour la détection et le trading de brackets"""

    # === DÉTECTION ===
    min_touches_per_side: int = 2          # Minimum 2 touches par borne
    optimal_touches: int = 3                # 3 touches = bracket confirmé

    # Taille minimum du bracket (en ticks)
    min_width_ticks: Dict[str, int] = field(default_factory=lambda: {
        'ES': 20,
        'NQ': 50,
        'MES': 20,
        'MNQ': 50
    })

    # Taille optimale du bracket (en ticks)
    optimal_width_ticks: Dict[str, int] = field(default_factory=lambda: {
        'ES': 30,
        'NQ': 80,
        'MES': 30,
        'MNQ': 80
    })

    # === VOLUME ===
    volume_ratio_min: float = 1.5          # Volume bornes > middle × 1.5
    min_volume_per_bar: Dict[str, int] = field(default_factory=lambda: {
        'ES': 50,
        'NQ': 30,
        'MES': 20,
        'MNQ': 15
    })

    # === DOM ===
    dom_imbalance_min: float = 0.2         # 20% déséquilibre minimum aux bornes
    min_dom_depth: int = 100               # 100 contracts sur 10 levels

    # === TIMEFRAME ===
    detection_timeframe: str = '5min'      # Détection sur 5 min
    confirmation_timeframe: str = '15min'  # Confirmation sur 15 min
    entry_timeframe: str = '1min'          # Entry précise sur 1 min

    # === DURÉE ===
    min_duration_minutes: int = 10         # Bracket doit tenir 10min minimum
    max_duration_minutes: int = 120        # Expire après 2 heures

    # === ENTRY ===
    entry_distance_ticks: int = 2          # Entrer à 2 ticks de la borne
    require_confirmation_pattern: bool = True  # Attendre pattern de rejet

    # === STOP LOSS ===
    stop_distance: Dict[str, int] = field(default_factory=lambda: {
        'small_bracket': 5,     # < 30 ticks
        'medium_bracket': 8,    # 30-50 ticks
        'large_bracket': 12     # > 50 ticks
    })

    # Ajustements volatilité
    use_volatility_adjustment: bool = True
    vix_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'low': 1.0,      # VIX < 15
        'normal': 1.3,   # VIX 15-25
        'high': 1.6      # VIX 25-30
    })
    atr_multiplier: float = 1.2
    max_stop_cap: int = 15                 # JAMAIS plus de 15 ticks
    no_trade_vix_threshold: float = 30.0  # Pas de bracket si VIX > 30

    # === TAKE PROFIT ===
    tp_strategy: str = 'hybrid'            # 'middle', 'opposite', 'hybrid'
    tp_hybrid_split: Dict[str, float] = field(default_factory=lambda: {
        'middle': 0.50,    # 50% au middle
        'opposite': 0.50   # 50% à la borne opposée
    })
    min_rr_ratio: float = 1.5              # Minimum 1.5:1

    # === TRADE MANAGEMENT ===
    max_trades_per_bracket: int = 3        # Maximum 3 trades par bracket
    phase_1_trades: int = 2                # Trades 1-2: Full size
    phase_2_trades: int = 1                # Trade 3: 50% size
    phase_3_action: str = 'STOP'           # Trade 4+: Arrêter

    size_adjustment: Dict[str, float] = field(default_factory=lambda: {
        'trade_1_2': 1.0,   # 100% size
        'trade_3': 0.5,     # 50% size
        'trade_4+': 0.0     # STOP
    })

    # === SESSIONS ===
    # Qualité du bracket selon la session (1-5 étoiles)
    session_quality: Dict[str, int] = field(default_factory=lambda: {
        'asian': 5,        # Excellent
        'london_pre': 2,   # Prudent
        'london': 3,       # Moyen
        'ny_open': 2,      # Prudent
        'ny_am': 3,        # Moyen
        'lunch': 4,        # Bon
        'ny_pm': 4,        # Bon
        'close': 2         # Prudent
    })

    min_session_quality: int = 3           # Ne trader que qualité >= 3

    # === CONFLUENCE ===
    require_level_confluence: bool = True  # Bornes doivent être sur niveaux
    confluence_types: List[str] = field(default_factory=lambda: [
        'gex',           # GEX levels
        'vwap_bands',    # VWAP bands
        'blind_spots',   # Blind spots
        'vah_val',       # Value Area
        'round_numbers'  # 6900, 6950, 7000...
    ])
    min_confluences: int = 2               # Minimum 2 confluences par borne

    # === INVALIDATION ===
    breakout_threshold_ticks: int = 10     # Cassure > 10 ticks = invalidation

    # Signaux de fatigue (arrêter le bracket)
    fatigue_signals: Dict[str, any] = field(default_factory=lambda: {
        'volume_declining': True,          # Volume décroissant
        'touches_frequency_min': 5,        # Touches < 5min = fatigue
        'dom_imbalance_weak_threshold': 0.15,  # DOM < 15% = faible
        'duration_total_max': 90,          # > 90min = fatigue
        'wick_sizes_small': True           # Wicks petits = faible rejet
    })

    # Conditions de reset (redémarrer compteur)
    reset_conditions: Dict[str, any] = field(default_factory=lambda: {
        'bracket_widens': True,            # Bracket s'élargit
        'new_session': True,               # Nouvelle session
        'pause_duration_min': 30,          # Pause > 30min
        'volume_spike': True,              # Volume spike
        'confluence_reinforced': True      # Nouvelle confluence
    })

    # === CONTEXTE MACRO ===
    # Ne PAS trader bracket si:
    no_trade_conditions: Dict[str, any] = field(default_factory=lambda: {
        'strong_trend': True,              # Trend fort du jour
        'news_upcoming_minutes': 30,       # News dans 30min
        'vix_threshold': 30.0,             # VIX > 30
        'es_nq_divergence': 0.3            # Divergence ES/NQ > 30%
    })

    # === LIQUIDITÉ ===
    min_liquidity: Dict[str, int] = field(default_factory=lambda: {
        'bid_depth_total': 100,            # 100 contracts bid
        'ask_depth_total': 100,            # 100 contracts ask
        'min_volume_bar': 50               # 50 contracts par bar
    })

    # === SCALING ===
    use_scaling: bool = True
    scaling_in: Dict[str, float] = field(default_factory=lambda: {
        'initial': 0.50,       # 50% à 2 ticks de la borne
        'confirmation': 0.50   # 50% après pattern
    })

    scaling_out: Dict[str, float] = field(default_factory=lambda: {
        'middle': 0.33,        # 33% au middle
        'three_quarters': 0.33,  # 33% à 75% du range
        'opposite': 0.34       # 34% à la borne opposée
    })

    # === PATTERNS DE REJET ===
    rejection_patterns: List[str] = field(default_factory=lambda: [
        'pin_bar',         # Pin bar (long wick)
        'engulfing',       # Engulfing
        'double_top_bottom',  # Double top/bottom
        'volume_spike'     # Volume spike + rejet
    ])

    # === LIMITES ===
    max_concurrent_brackets: int = 1       # Maximum 1 bracket à la fois
    max_brackets_per_day: int = 5          # Maximum 5 brackets par jour
    max_loss_per_bracket: float = 500.0    # $500 perte max par bracket


# === FACTORY FUNCTIONS ===

def create_default_bracket_config() -> BracketConfig:
    """Crée la configuration par défaut"""
    return BracketConfig()


def create_conservative_bracket_config() -> BracketConfig:
    """Configuration conservatrice (moins de trades, plus strict)"""
    config = BracketConfig()

    # Plus strict
    config.min_touches_per_side = 3
    config.optimal_touches = 4
    config.volume_ratio_min = 2.0
    config.dom_imbalance_min = 0.3
    config.max_trades_per_bracket = 2
    config.min_session_quality = 4
    config.min_confluences = 3
    config.require_confirmation_pattern = True

    return config


def create_aggressive_bracket_config() -> BracketConfig:
    """Configuration agressive (plus de trades, moins strict)"""
    config = BracketConfig()

    # Plus permissif
    config.min_touches_per_side = 2
    config.volume_ratio_min = 1.3
    config.dom_imbalance_min = 0.15
    config.max_trades_per_bracket = 4
    config.min_session_quality = 2
    config.min_confluences = 1
    config.require_confirmation_pattern = False

    return config


# === EXPORTS ===

__all__ = [
    'BracketConfig',
    'create_default_bracket_config',
    'create_conservative_bracket_config',
    'create_aggressive_bracket_config'
]


# === TESTING ===

if __name__ == "__main__":
    print("🧪 TEST BRACKET CONFIG...")

    # Config par défaut
    config = create_default_bracket_config()
    print(f"\n📊 Config par défaut:")
    print(f"  - Min touches: {config.min_touches_per_side}")
    print(f"  - Min width ES: {config.min_width_ticks['ES']} ticks")
    print(f"  - Max trades: {config.max_trades_per_bracket}")
    print(f"  - TP strategy: {config.tp_strategy}")

    # Config conservatrice
    conservative = create_conservative_bracket_config()
    print(f"\n📊 Config conservatrice:")
    print(f"  - Min touches: {conservative.min_touches_per_side}")
    print(f"  - Volume ratio: {conservative.volume_ratio_min}")
    print(f"  - Max trades: {conservative.max_trades_per_bracket}")

    # Config agressive
    aggressive = create_aggressive_bracket_config()
    print(f"\n📊 Config agressive:")
    print(f"  - Min touches: {aggressive.min_touches_per_side}")
    print(f"  - Volume ratio: {aggressive.volume_ratio_min}")
    print(f"  - Max trades: {aggressive.max_trades_per_bracket}")

    print("\n[OK] Tests bracket config terminés!")
