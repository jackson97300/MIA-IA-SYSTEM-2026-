"""
Configuration pour intégration ML 3-Layer Filter dans launch_ml_v3_production.py

Version: 1.0
Date: 2025-11-09
"""

# ═══════════════════════════════════════════════════════════════════════
# CHEMINS DES MODÈLES 3-LAYER
# ═══════════════════════════════════════════════════════════════════════

MODEL_PATHS_3LAYER = {
    "ES": "ml/models_3layer/lgbm_3layer_ES_BINARY_latest.pkl",
    "NQ": "ml/models_3layer/lgbm_3layer_NQ_BINARY_latest.pkl",
    "RTY": "ml/models_3layer/lgbm_3layer_RTY_BINARY_latest.pkl"
}

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION 3-LAYER FILTER
# ═══════════════════════════════════════════════════════════════════════

CONFIG_3LAYER = {
    "enabled": True,  # Master switch
    "mode": "production",  # "production" ou "testing"

    # Seuils minimaux par layer
    "min_thresholds": {
        "menthorq": 0.20,    # 40% du max (0.50)
        "orderflow": 0.12,   # 40% du max (0.30)
        "context": 0.08,     # 40% du max (0.20)
        "total": 0.50        # 50% total minimum
    },

    # Mode par symbole et direction
    "modes": {
        "ES": {"UP": "advisory", "DOWN": "advisory"},   # CALIBRAGE
        "NQ": {"UP": "advisory", "DOWN": "advisory"},   # CALIBRAGE
        "RTY": {"UP": "advisory", "DOWN": "advisory"}   # CALIBRAGE
    },

    # Fallback sur MLDualFilter si modèles 3-Layer absents
    "use_dual_filter_fallback": True
}

# ═══════════════════════════════════════════════════════════════════════
# INTÉGRATION AVEC HARD RULES MENTHORQ
# ═══════════════════════════════════════════════════════════════════════

CONFIG_HARD_RULES = {
    "enabled": True,  # Appliquer hard rules après 3-Layer

    # Règles de blocage
    "blind_spot_max_distance_ticks": 5,   # Bloque si < 5 ticks d'un blind spot
    "gamma_wall_max_distance_ticks": 3,   # Bloque si < 3 ticks d'un gamma wall
    "vix_extreme_threshold": 50.0,        # Réduit size si VIX > 50
    "dealers_bias_min": -0.5,             # Bloque si dealers bias < -0.5

    # Ajustements soft
    "vix_high_multiplier": 0.8,           # x0.8 position si VIX > 25
    "confluence_boost": 1.2,              # x1.2 position si confluence > 0.80
    "leadership_boost": 1.1               # x1.1 position si leadership > 0.70
}

# ═══════════════════════════════════════════════════════════════════════
# INTÉGRATION AVEC MARKET CONTEXT ANALYZER
# ═══════════════════════════════════════════════════════════════════════

CONFIG_MARKET_CONTEXT = {
    "enabled": True,  # Utiliser MarketContextAnalyzer en complément

    # Pré-filtre (avant 3-Layer)
    "prefilter": {
        "min_quality_score": 0.40,        # Rejette si quality < 40%
        "max_proximity_alerts": 3         # Rejette si > 3 alertes
    },

    # Post-validation (après 3-Layer)
    "postvalidation": {
        "reject_opposite_bias": True,     # ✅ RESTAURÉ 17/11: Rejette trades contre-tendance (comme PIPELINE_COMPLET)
        "boost_aligned_plan": True,       # Boost +15% si trading plan aligné
        "boost_multiplier": 1.15,
        "min_plan_confidence": 0.75       # Plan must be > 75% confident
    }
}

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION PAR SESSION (ASIA/LONDON/US)
# ═══════════════════════════════════════════════════════════════════════

CONFIG_SESSIONS = {
    "ASIA": {
        "hours_est": "18:00-03:00",
        "min_confidence_boost": 1.1,      # +10% seuil en ASIA
        "position_size_mult": 0.6,
        "symbols_enabled": {
            "ES": True,
            "NQ": True,
            "RTY": False  # Désactivé en ASIA
        }
    },

    "LONDON": {
        "hours_est": "03:00-09:30",
        "min_confidence_boost": 1.05,     # +5% seuil en LONDON
        "position_size_mult": 0.8,
        "symbols_enabled": {
            "ES": True,
            "NQ": True,
            "RTY": True
        }
    },

    "US": {
        "hours_est": "09:30-16:00",
        "min_confidence_boost": 1.0,      # Seuils normaux en US
        "position_size_mult": 1.0,
        "symbols_enabled": {
            "ES": True,
            "NQ": True,
            "RTY": True
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════
# MÉTRIQUES ATTENDUES (RÉFÉRENCE)
# ═══════════════════════════════════════════════════════════════════════

EXPECTED_METRICS = {
    "ES": {
        "trades_per_day": "6-10",
        "win_rate": "75-82%",
        "pnl_per_trade": 235,
        "contribution": "55-65%"
    },

    "NQ": {
        "trades_per_day": "4-7",
        "win_rate": "74-78%",
        "pnl_per_trade": 165,
        "contribution": "25-30%"
    },

    "RTY": {
        "trades_per_day": "1-3",
        "win_rate": "70-75%",
        "pnl_per_trade": 95,
        "contribution": "5-10%"
    },

    "TOTAL": {
        "trades_per_day": "11-20",
        "win_rate": "74-80%",
        "daily_pnl": "$2160-3880"
    }
}

# ═══════════════════════════════════════════════════════════════════════
# LOGGING & MONITORING
# ═══════════════════════════════════════════════════════════════════════

CONFIG_LOGGING = {
    "log_layer_breakdown": True,          # Log détails par layer
    "log_hard_rules": True,               # Log hard rules rejections
    "log_market_context": True,           # Log market context analysis
    "save_rejected_signals": True,        # Sauvegarder signaux rejetés
    "rejection_log_path": "logs/3layer_rejections.jsonl"
}
