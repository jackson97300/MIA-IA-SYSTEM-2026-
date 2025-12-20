"""
Configuration SIMPLIFIÉE - 4 Stratégies Core
Version Pro : Focus qualité > quantité

Date: 13 Novembre 2025
Version: 3.1 - SIMPLIFIED PRO + Gamma Wall Rejection
"""

from typing import Dict, Any

# === 4 STRATÉGIES CORE ===
ENABLED_STRATEGIES_SIMPLE = [
    "ml_3layer_strategy",                    # Générateur principal (3-layer filter)
    "vwap_sd_options_confluence_strategy",   # Générateur secondaire (mean reversion)
    "gamma_wall_rejection",                  # Générateur tertiaire (rejection gamma walls)
    "head_fake_detector"                     # Filtre invalidateur (protection)
]

# === PRIORITÉS ===
STRATEGY_PRIORITY_SIMPLE = {
    "ml_3layer_strategy": 1,                 # Évalué EN PREMIER
    "vwap_sd_options_confluence_strategy": 2, # Évalué EN SECOND
    "gamma_wall_rejection": 3,               # Évalué EN TROISIÈME
    "head_fake_detector": 4                  # Évalué EN DERNIER (invalidation)
}

# === COOLDOWNS OPTIMISÉS ===
COOLDOWN_SIMPLE = {
    "ml_3layer_strategy": 120,               # 2 min (réduit de 3 min)
    "vwap_sd_options_confluence_strategy": 60, # 1 min (réduit de 1.5 min)
    "gamma_wall_rejection": 45,              # 45 sec (rejections rapides)
    "head_fake_detector": 30                  # 30 sec (ultra-réactif)
}

# === SEUILS ASSOUPLIS ===
ML_3LAYER_PARAMS_RELAXED = {
    # Layer 1 (MenthorQ)
    "min_layer1_confidence": 0.08,           # 8% (au lieu de 15%)

    # Layer 2 (OrderFlow)
    "min_layer2_confidence": 0.05,           # 5% (au lieu de 8%)
    "accept_neutral_flow": True,             # ✅ Accepte flow neutre

    # Layer 3 (Context)
    "max_vwap_distance_atr": {
        "LONDON": 10.0,                      # 10 ATR (au lieu de 3)
        "US": 8.0,                           # 8 ATR (au lieu de 3)
        "ASIA": 12.0                         # 12 ATR (au lieu de 4)
    },
    "max_warnings": {
        "LONDON": 5,                         # 5 warnings autorisés
        "US": 4,
        "ASIA": 6
    },

    # Confidence totale
    "min_total_confidence": 0.30             # 30% (au lieu de 50%)
}

VWAP_SD_PARAMS_RELAXED = {
    # Zones de bounce élargies (ticks)
    "bounce_zones": {
        "ES": {"sd1": 30, "sd2": 50},        # ES: 30t SD1, 50t SD2
        "NQ": {"sd1": 60, "sd2": 100},       # NQ: 60t SD1, 100t SD2
        "RTY": {"sd1": 25, "sd2": 40}        # RTY: 25t SD1, 40t SD2
    },

    # Confluence thresholds
    "confluence_max_distance": {
        "ES": {"vwap_hvl": 40, "vwap_wall": 80},
        "NQ": {"vwap_hvl": 80, "vwap_wall": 150},
        "RTY": {"vwap_hvl": 20, "vwap_wall": 50}
    },

    # Risk/Reward minimum
    "min_rr_ratio": 1.2                      # 1.2:1 (au lieu de 1.5:1)
}

GAMMA_WALL_REJECTION_PARAMS = {
    # Distance max au mur gamma (ticks)
    "max_distance_to_wall": {
        "ES": 8,                             # 8 ticks ES (au lieu de 5)
        "NQ": 12,                            # 12 ticks NQ (au lieu de 8)
        "RTY": 5                             # 5 ticks RTY
    },

    # Wall strength minimum
    "min_wall_strength": 0.20,               # 0.20 (au lieu de 0.25)

    # Rejection pattern
    "min_rejection_range_ticks": 2,          # 2 ticks minimum (au lieu de 3)
    "require_wick_rejection": True,          # Mèche de rejet requise
    "require_imbalance_flip": False,         # Flip DOM pas obligatoire

    # Entry
    "entry_on_close": True,                  # Entry sur close de rejection
    "sl_beyond_wall_ticks": 3,               # SL 3 ticks au-delà du mur

    # Targets
    "tp1_target": "vwap",                    # TP1 = VWAP
    "tp2_target": "opposite_wall",           # TP2 = Mur opposé
    "min_rr_ratio": 1.5                      # R/R minimum 1.5:1
}

HEAD_FAKE_PARAMS = {
    "wick_ratio_min": 0.50,                  # 50% (au lieu de 60%)
    "reentry_bars_max": 4,                   # 4 barres (au lieu de 3)
    "require_volume_climax": False           # Pas obligatoire
}

# === CONFIGURATION COMPLÈTE ===
SIMPLE_CONFIG: Dict[str, Any] = {
    "enabled_strategies": ENABLED_STRATEGIES_SIMPLE,
    "strategy_priority": STRATEGY_PRIORITY_SIMPLE,
    "cooldown_per_strategy": COOLDOWN_SIMPLE,

    # Paramètres stratégies
    "ml_3layer_params": ML_3LAYER_PARAMS_RELAXED,
    "vwap_sd_params": VWAP_SD_PARAMS_RELAXED,
    "gamma_wall_rejection_params": GAMMA_WALL_REJECTION_PARAMS,
    "head_fake_params": HEAD_FAKE_PARAMS,

    # Mode
    "simplified_mode": True,
    "use_ml_ready_direct": True,
    "enable_live_trading": True,

    # Risk Management
    "max_daily_loss": 500,                   # $500 max loss/jour
    "max_consecutive_losses": 3,             # 3 pertes consécutives → pause
    "position_size_base": 1                  # 1 contrat de base
}

def get_simple_config() -> Dict[str, Any]:
    """Retourne la configuration simplifiée"""
    return SIMPLE_CONFIG.copy()
