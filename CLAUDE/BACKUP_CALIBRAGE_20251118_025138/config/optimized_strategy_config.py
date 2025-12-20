"""
Configuration Optimisée - 11 Stratégies ML_READY

Cette configuration active les 11 stratégies sélectionnées
qui exploitent directement les données ML_READY sans recalculs.

✅ NEW (10 Nov 2025): ml_3layer_strategy ajoutée (Tier 1, priorité 1)
  - Générateur de signaux direct depuis Layer 3
  - Correctifs critiques appliqués (RTY, t_ms, SL cap)
  - Version 1.1 avec Hard Rules intégrées

Date: 10 Novembre 2025
Version: 2.1 - ML_READY Optimized + ML 3-Layer Strategy
"""

from typing import Dict, Any, List

# === 🎯 3 STRATÉGIES CORE (SIMPLIFICATION 13/11/2025) ===
# Gardé uniquement les stratégies Tier 1 fonctionnelles
# ⚠️ hybrid_strategy DÉSACTIVÉE temporairement (direction=None bug)
ENABLED_STRATEGIES = [
    # ✅ TIER 1 - HAUTE QUALITÉ - FONCTIONNELLES
    "menthorq_3layer_strategy",                # Priorité 1 - Layer 3 direct (utilise ML 3-Layer System)
    # "hybrid_strategy",                       # Priorité 2 - ❌ DÉSACTIVÉ - direction=None bug
    "gamma_wall_rejection",                    # Priorité 3 - Rejet gamma walls
    "vwap_sd_options_confluence_strategy",     # Priorité 4 - Mean reversion VWAP bands
]

# === STRATÉGIES DÉSACTIVÉES (SIMPLIFICATION 13/11/2025) ===
# Retirées pour focus qualité vs quantité
# - hybrid_strategy: ❌ TEMPORAIRE - Bug direction=None (à corriger)
# - gamma_pin_reversion: Doublon avec gamma_wall_rejection
# - liquidity_sweep_reversal: Tier 2 (qualité moyenne)
# - head_fake_detector: Tier 3 (protection uniquement)
# - gamma_wall_break_and_go: Overlapping avec rejection
# - hvl_magnet_fade: Tier 2 (fade exhaustion)
# - call_put_channel_rotation: Tier 3 (rare, régime change)

# === PRIORITÉS (ordre d'évaluation) ===
STRATEGY_PRIORITY = {
    "menthorq_3layer_strategy": 1,       # ✅ Layer 3 EN PREMIER (haute qualité) - CORRIGÉ: nom correct
    "hybrid_strategy": 2,                # Évalué EN SECOND (priorité haute)
    "gamma_wall_rejection": 3,           # ✅ Rejet gamma walls (priorité haute)
    "vwap_sd_options_confluence_strategy": 4,  # ✅ VWAP SD Confluence
}

# === COOLDOWNS PAR STRATÉGIE (secondes) ===
# 🔧 MODIFICATION 2025-11-13 18:00: MODE CONSERVATEUR QUALITÉ
#    ml_3layer_strategy → 0s (pas de cooldown, les seuils 55% filtrent la qualité)
COOLDOWN_PER_STRATEGY = {
    # ✅ 4 STRATÉGIES CORE
    "menthorq_3layer_strategy": 0,                 # 30 → 0s (MODE QUALITÉ: seuil 28% filtre) - CORRIGÉ: nom correct
    "hybrid_strategy": 60,                         # 1 min (haute confluence)
    "gamma_wall_rejection": 30,                    # 60 → 30s (rejet = opportunité rapide)
    "vwap_sd_options_confluence_strategy": 30,     # 60 → 30s (mean reversion = opportunités rapides)
}

# === SESSIONS AUTORISÉES PAR STRATÉGIE ===
# ✅ TOUTES STRATÉGIES → ALL SESSIONS
SESSION_FILTERS = {
    # ✅ 4 STRATÉGIES CORE
    "menthorq_3layer_strategy": ["ALL"],           # CORRIGÉ: nom correct
    "hybrid_strategy": ["ALL"],
    "gamma_wall_rejection": ["ALL"],
    "vwap_sd_options_confluence_strategy": ["ALL"],
}

# === ML THRESHOLDS PAR TIER ===
# 🔧 MODIFICATION 2025-11-13: Abaissé pour permettre plus de signaux (mode DATA COLLECTION)
ML_THRESHOLD_BY_TIER = {
    "tier1": 0.48,  # 0.55 → 0.48 (aligné avec MIN_TOTAL_CONFIDENCE=0.45)
    "tier2": 0.60,  # 0.65 → 0.60
    "tier3": 0.65   # 0.70 → 0.65
}

# === MAPPING STRATÉGIES → TIERS ===
STRATEGY_TIER_MAPPING = {
    # ✅ 4 STRATÉGIES CORE (Toutes Tier 1)
    "menthorq_3layer_strategy": "tier1",     # Haute qualité Layer 3 - CORRIGÉ: nom correct
    "hybrid_strategy": "tier1",              # MenthorQ + BN + ML
    "gamma_wall_rejection": "tier1",         # Rejet gamma wall = haute probabilité
    "vwap_sd_options_confluence_strategy": "tier1",  # Mean reversion VWAP bands
}

# === PARAMÈTRES GLOBAUX ===
GLOBAL_PARAMS = {
    # Options
    "options_headroom_min_pct": 0.15,  # Headroom minimum 0.15%

    # Imbalance DOM (ES vs NQ)
    "imbalance_l1": {
        "ES": 0.12,
        "NQ": 0.10,
        "high_vol_multiplier": 1.2  # x1.2 en haute volatilité
    },

    # Volume
    "relvol_min": 1.2,              # Volume relatif minimum
    "relvol_break_min": 1.3,        # Volume breakout minimum

    # Sessions (multipliers)
    "session_multipliers": {
        "OPENING_BELL": 1.2,        # 09:30-10:30 ET
        "POWER_HOUR": 1.2,          # 15:00-16:00 ET
        "LUNCH": 0.8,               # 12:00-14:00 ET
        "ASIA": 0.5                 # 23:00-08:00 ET
    }
}

# === SIZING PAR TIER ===
RISK_GRID = {
    "tier1": 1.0,   # Full size (100%)
    "tier2": 0.7,   # 70% size
    "tier3": 0.5    # 50% size
}

# === GESTION CONFLITS ===
CONFLICT_RESOLUTION = {
    "same_side_within_60s": "keep_best_headroom",  # Même side < 60s → garde meilleur headroom
    "opposite_sides": "cancel_both",               # Sides opposés → annule les 2
    "headfake_invalidation": True                  # HeadFake peut invalider autres signaux
}

# === STRATÉGIES DÉSACTIVÉES (13 - RETIRÉES) ===
DISABLED_STRATEGIES = [
    # Patterns (10)
    "dealer_flip_breakout",              # Doublon avec Hybrid
    "stacked_imbalance_continuation",    # Doublon Battle Navale
    "iceberg_tracker_follow",            # Données pas disponibles
    "cvd_divergence_trap",               # Recalcul CVD lourd
    "opening_drive_fail",                # Trop spécifique
    "profile_gap_fill",                  # Profile pas dans ML_READY

    # MenthorQ Patterns (3 RETIRÉES - 4 AJOUTÉES)
    "d1_extreme_trap",                   # D1 pas dans ML_READY
    "gex_cluster_mean_revert",           # Doublon Hybrid

    # Autres (6)
    "es_nq_lead_lag_mirror",             # ❌ RETIRÉ - Remplacé par Blind Spot
    "delta_divergence",                  # Recalcul delta
    "bracket_detector",                  # Range trading session spécifique
    "bracket_trader",                    # Idem
    "battle_navale_solo",                # Déjà dans Hybrid
    "menthorq_first_solo"                # Déjà dans Hybrid
]

# === CONFIGURATION FINALE COMPLÈTE ===
OPTIMIZED_CONFIG: Dict[str, Any] = {
    # Stratégies
    "enabled_strategies": ENABLED_STRATEGIES,
    "disabled_strategies": DISABLED_STRATEGIES,
    "strategy_priority": STRATEGY_PRIORITY,
    "priority": STRATEGY_PRIORITY,  # Alias pour compatibilité

    # Cooldowns & Sessions
    "cooldown_per_strategy": COOLDOWN_PER_STRATEGY,
    "session_filters": SESSION_FILTERS,

    # ML Filter
    "ml_filter_enabled": True,
    "ml_threshold_by_tier": ML_THRESHOLD_BY_TIER,
    "strategy_tier_mapping": STRATEGY_TIER_MAPPING,

    # Paramètres globaux (niveau racine pour compatibilité)
    "options_headroom_min_pct": 0.15,
    "imbalance_l1_es": 0.12,
    "imbalance_l1_nq": 0.10,
    "relvol_min": 1.2,

    # Paramètres globaux (sous-dictionnaire complet)
    "global_params": GLOBAL_PARAMS,
    "risk_grid": RISK_GRID,
    "conflict_resolution": CONFLICT_RESOLUTION,

    # Flags désactivation
    "pattern_strategies_enabled": False,      # Désactive les 10 patterns non sélectionnés
    "menthorq_patterns_enabled": False,       # Désactive les 6 MenthorQ non sélectionnés
    "reversal_patterns_enabled": True,        # Garde HeadFake
    "bracket_trading_enabled": False,         # Désactive bracket

    # Hybrid (contient BN + MQ)
    "hybrid_strategy_enabled": True,
    "hybrid_mode": "full",

    # Mode ML_READY (pas de recalculs)
    "use_ml_ready_direct": True,
    "disable_feature_recalculation": True,

    # Exécution (activée en paper trading Sim1)
    "enable_live_trading": True  # ✅ SAFE sur compte SIM
}


def get_optimized_config() -> Dict[str, Any]:
    """
    Retourne la configuration optimisée

    Returns:
        Dict avec toutes les configurations
    """
    return OPTIMIZED_CONFIG.copy()


def get_ml_threshold_for_strategy(strategy_name: str) -> float:
    """
    Retourne le threshold ML pour une stratégie

    Args:
        strategy_name: Nom de la stratégie

    Returns:
        Threshold ML (0.55, 0.65 ou 0.70)
    """
    tier = STRATEGY_TIER_MAPPING.get(strategy_name, "tier2")
    return ML_THRESHOLD_BY_TIER[tier]


def get_cooldown_for_strategy(strategy_name: str) -> int:
    """
    Retourne le cooldown pour une stratégie

    Args:
        strategy_name: Nom de la stratégie

    Returns:
        Cooldown en secondes
    """
    return COOLDOWN_PER_STRATEGY.get(strategy_name, 240)  # Default 4 min


def is_session_allowed(strategy_name: str, session: str) -> bool:
    """
    Vérifie si une session est autorisée pour une stratégie

    Args:
        strategy_name: Nom de la stratégie
        session: Session actuelle (ASIA, LONDON, US, etc.)

    Returns:
        True si autorisée
    """
    allowed_sessions = SESSION_FILTERS.get(strategy_name, ["ALL"])
    return "ALL" in allowed_sessions or session in allowed_sessions


def get_position_size_multiplier(strategy_name: str) -> float:
    """
    Retourne le multiplicateur de taille de position

    Args:
        strategy_name: Nom de la stratégie

    Returns:
        Multiplicateur (0.5, 0.7 ou 1.0)
    """
    tier = STRATEGY_TIER_MAPPING.get(strategy_name, "tier2")
    return RISK_GRID[tier]


# === PARAMÈTRES DÉTAILLÉS PAR STRATÉGIE (GPT Enhanced) ===
# Configuration granulaire pour chaque stratégie avec triggers précis
STRATEGY_PARAMS_DETAILED = {
    # === ✅ NEW: ML 3-LAYER STRATEGY ===
    "ml_3layer_strategy": {
        "min_total_confidence": 0.40,        # ✅ RÉDUIT: 40% (était 50%) - Capture plus de setups
        "min_layer1_confidence": 0.10,       # ✅ RÉDUIT: 10% (était 15%) - Layer 1 moins strict
        "sl_min_ticks": {"ES": 20, "NQ": 20, "RTY": 15},  # Min SL par symbole
        "sl_max_ticks": {"ES": 40, "NQ": 48, "RTY": 40},  # Max SL par symbole
        "tp_atr_multiplier": 5.0,            # 5x ATR pour TP
        "require_spread_ok": True,           # Spread <= 2 ticks
        "require_liquidity_ok": True,        # Liquidité minimale au BBO
        "tp1_target": "menthorq_level",      # Call resistance / Put support
        "tp2_target": "atr_or_gex",          # 5x ATR ou prochain GEX
        "version": "1.2"                     # Version 1.2: Thresholds optimisés
    },

    # === CORE STRATEGIES ===
    "hybrid_strategy": {
        "menthorq_confluence_min": 0.75,
        "battle_navale_signal_min": 0.60,
        "ml_confidence_min": 0.60,
        "relvol_min": 1.2,
        "headroom_min_pct": 0.15,
        "require_all_confluences": True,
        "tp1_r_multiple": 1.5,
        "tp2_target": "wall_or_va",  # mur, VA, ou SD2
    },

    "gamma_pin_reversion": {
        "pin_strength_min": 0.70,
        "dist_to_pin_pct_max": 0.12,
        "imbalance_flip_ticks": 2,
        "require_level1_flip": True,
        "sl_buffer_ticks": 8,  # 6-8 ticks
        "tp1_target": "vwap",
        "tp2_target": "sd1",
    },

    "zero_dte_wall_sweep": {
        "wall_dist_ticks_max": 12,
        "sweep_wick_ratio_min": 0.60,
        "require_climax_volume": True,
        "require_blind_spot_behind": True,
        "imbalance_flip_ticks": 3,
        "sl_beyond_wall_ticks": 3,
        "tp1_target": "vwap",
        "tp2_target": "opposite_wall_or_va",
    },

    "liquidity_sweep_reversal": {
        "reclaim_window_seconds_max": 40,
        "price_displacement_pct_max": 0.12,
        "smart_money_flow_flip_min": 0.30,  # De -0.20 à +0.10
        "thin_liquidity_threshold": 0.30,
        "sl_beyond_sweep_ticks": 3,
        "tp1_target": "vwap",
        "tp2_target": "next_wall",
    },

    "vwap_band_squeeze_break": {
        "squeeze_min_minutes": 8,
        "squeeze_max_minutes": 12,
        "squeeze_range": "vwap_sd1",  # [VWAP±SD1]
        "slope_neutral_band": 0.05,
        "relvol_break_min": 1.35,
        "require_imbalance_aligned": True,
        "sl_target": "opposite_band",
        "tp1_target": "sd2",
        "tp2_target": "va_or_wall",
    },

    "head_fake_detector": {
        "wick_ratio_min": 0.60,
        "reentry_bars_max": 3,
        "require_volume_climax": True,
        "range_breakout_min_pct": 0.15,
        "sl_beyond_wick_ticks": 3,
        "tp1_target": "range_mid",
        "tp2_target": "opposite_band",
    },

    # === GAME CHANGERS ===
    "blind_spot_magnetic_pull": {
        "dist_to_blindspot_pct_max": 0.12,
        "require_sweep_in_blindspot": True,
        "reclaim_bars_max": 3,
        "institutional_pressure_min": 0.40,
        "smart_money_flow_min": 0.30,
        "sl_beyond_blindspot_ticks": 3,
        "tp1_target": "vwap",
        "tp2_target": "va_or_wall",
        "tp_r_multiple": 2.0,
    },

    "gamma_wall_break_and_go": {
        "dist_to_wall_pct_max": 0.18,
        "relvol_break_min": 1.35,
        "no_reject_wick_pct": 0.05,
        "pullback_bars_max": 3,
        "require_bias_aligned": True,
        "require_clean_break": True,  # Pas de mèches de rejet
        "entry_type": "pullback_retest",
        "sl_beyond_wall_ticks": 3,
        "tp1_r_multiple": 1.2,  # Sortie rapide momentum
        "tp2_target": "next_wall_or_sd2",
    },

    "hvl_magnet_fade": {
        "hvl_dist_pct_min": 0.12,
        "bias_abs_max": 0.20,  # Dealers bias dans [-0.2, +0.2]
        "exhaustion_wick_min": 0.60,
        "require_volume_climax": True,
        "reclaim_bars_max": 3,
        "absorption_required": True,
        "sl_beyond_extension_ticks": 3,
        "tp1_target": "hvl",
        "tp2_target": "vwap",
        "tp_r_multiple": 2.0,
    },

    "call_put_channel_rotation": {
        "flip_confirm_bars": 3,
        "channel_conf_min": 0.70,
        "flow_ratio_long_min": 1.30,
        "flow_ratio_short_max": 0.77,
        "headroom_pct_min": 0.20,
        "price_acceptance_required": True,  # 3 barres au-dessus/dessous flip
        "no_wall_blocking": True,
        "flip_cooldown_sec": 600,  # 10 min entre flips
        "sl_target": "mid_channel",
        "tp1_r_multiple": 1.5,
        "tp2_target": "opposite_channel_edge",
    },
}


def get_strategy_params(strategy_name: str) -> Dict[str, Any]:
    """
    Retourne les paramètres détaillés pour une stratégie donnée

    Args:
        strategy_name: Nom de la stratégie

    Returns:
        Dict des paramètres de la stratégie (vide si non trouvée)
    """
    return STRATEGY_PARAMS_DETAILED.get(strategy_name, {})


def get_all_strategy_params() -> Dict[str, Dict[str, Any]]:
    """
    Retourne tous les paramètres détaillés de toutes les stratégies

    Returns:
        Dict complet des paramètres par stratégie
    """
    return STRATEGY_PARAMS_DETAILED


if __name__ == "__main__":
    # Test de la config
    config = get_optimized_config()

    print("="*70)
    print("CONFIGURATION OPTIMISÉE ML_READY")
    print("="*70)

    print(f"\n✅ Stratégies activées: {len(config['enabled_strategies'])}")
    for strategy in config['enabled_strategies']:
        tier = STRATEGY_TIER_MAPPING[strategy]
        cooldown = COOLDOWN_PER_STRATEGY[strategy]
        ml_threshold = ML_THRESHOLD_BY_TIER[tier]
        print(f"   - {strategy} (Tier: {tier}, Cooldown: {cooldown}s, ML: {ml_threshold})")

    print(f"\n❌ Stratégies désactivées: {len(config['disabled_strategies'])}")

    print(f"\n🎯 ML Filter: {'ACTIVÉ' if config['ml_filter_enabled'] else 'DÉSACTIVÉ'}")
    print(f"📊 Mode ML_READY Direct: {'OUI' if config['use_ml_ready_direct'] else 'NON'}")

    print("\n" + "="*70)
