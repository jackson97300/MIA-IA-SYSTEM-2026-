#!/usr/bin/env python3
"""
🎯 MIA_HYBRID_FINAL_PLUS - Configuration Hybride avec Adaptateur IV
Configuration professionnelle avec seuils dynamiques pilotés par volatilité implicite
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# ===== CONFIGURATION MIA_HYBRID_FINAL_PLUS =====

MIA_HYBRID_FINAL_PLUS = {
    # 1) Base configuration (héritée)
    "base_config": {
        "system_name": "MIA_HYBRID_FINAL_PLUS",
        "version": "1.0.0",
        "description": "Configuration hybride avec adaptateur IV dynamique",
        "environment": "production",
        "trading_mode": "hybrid",  # fast/standard/hybrid
        "session_adaptation": True,
    },

    # 2) Workflow hybrides (Fast/Standard/Hybrid) + seuils dynamiques par VIX **ET IV**
    "workflow_modes": {
        "session_adaptation": True,
        "fast_track_threshold_base": 0.70,
        "standard_track_threshold_base": 0.80,
        "vix_buckets": {  # on laisse pour compat, mais on va prioriser IV ci-dessous
            "LOW":  {"vix_max": 18, "fast_mult": 1.00, "std_mult": 1.00},
            "MID":  {"vix_max": 24, "fast_mult": 1.05, "std_mult": 0.98},
            "HIGH": {"vix_max": 99, "fast_mult": 1.10, "std_mult": 0.95}
        }
    },

    # 👇 NOUVEAU : Adaptateur Volatilité Implicite (IV)
    "iv_adapter": {
        "enabled": True,
        "source": {            # quelle courbe d'IV alimenter selon l'actif
            "ES": "SPX_IV30",  # pour ES on lit l'IV 30j du SPX (snapshot options)
            "NQ": "NDX_IV30"   # pour NQ on lit l'IV 30j du NDX
        },
        "rank_window_days": 252,     # IV rank/percentile sur 1 an glissant
        "bands": {                   # bornes en percentile d'IV
            "LOW":  {"pmax": 0.20, "fast_mult": 0.95, "std_mult": 1.02, "votes_delta": -0},
            "MID":  {"pmin": 0.20, "pmax": 0.60, "fast_mult": 1.00, "std_mult": 1.00, "votes_delta": 0},
            "HIGH": {"pmin": 0.60, "fast_mult": 1.08, "std_mult": 0.96, "votes_delta": +1}
        },
        "sizing": {                  # adaptation taille/risque par IV band
            "LOW":  {"size_mult": 1.10, "atr_mult": 1.0, "beyond_sd2_size_factor": 0.60},
            "MID":  {"size_mult": 1.00, "atr_mult": 1.1, "beyond_sd2_size_factor": 0.50},
            "HIGH": {"size_mult": 0.80, "atr_mult": 1.3, "beyond_sd2_size_factor": 0.40}
        },
        "guardrails": {              # bornes par 'expected move' journalier
            "use_expected_move": True,
            "expected_move_days": 1, # calc 1D: S * IV * sqrt(T)
            "tp_cap_em_mult": 1.50,  # cap TP total à 1.5x expected move (évite l'over-greed)
            "sl_floor_em_mult": 0.40 # stop mini = 0.4x expected move (évite stops trop serrés)
        },
        "skew_bias": {               # lecture simple du skew
            "enabled": True,
            "put25_minus_call25_bps": 300,   # si skew > 3% ⇒ biais vendeur
            "bias_weight_bump": 0.02         # +2% sur confluence côté direction du skew
        },
        "term_structure": {          # contango/backwardation simple
            "enabled": True,
            "short_iv_minus_long_iv_bps": 150,  # si IV30 - IV90 > 1.5% ⇒ short-term stress
            "fast_track_hard_off_in_high": True # coupe fast-track si HIGH + backwardation
        }
    },

    # 3) Confluence weights (adaptées par IV)
    "confluence_weights": {
        "base_weights": {
            "gamma_levels_proximity": 0.22,    # 22% - Gamma SpotGamma style
            "volume_confirmation": 0.16,       # 16% - Volume OrderFlow
            "vwap_trend_signal": 0.13,         # 13% - VWAP direction
            "sierra_pattern_strength": 0.13,   # 13% - Patterns Sierra
            "mtf_confluence_score": 0.10,      # 10% - Multi-timeframe
            "smart_money_strength": 0.08,      # 8%  - Smart Money (100/500)
            "order_book_imbalance": 0.03,      # 3%  - Depth 5 imbalance
            "options_flow_bias": 0.02,         # 2%  - Options sentiment
            "vwap_bands_signal": 0.08,         # 8%  - VWAP Bands (SD1/SD2)
            "volume_imbalance_signal": 0.05,   # 5%  - Volume Profile
        },
        "iv_adaptation": {
            "enabled": True,
            "low_iv_boost": {  # IV bas = plus d'agressivité
                "gamma_levels_proximity": 1.15,
                "volume_confirmation": 1.10,
                "vwap_trend_signal": 1.05
            },
            "high_iv_boost": {  # IV haut = plus de prudence
                "smart_money_strength": 1.20,
                "order_book_imbalance": 1.15,
                "options_flow_bias": 1.10
            }
        }
    },

    # 4) Leadership engine (remplace es_nq_correlation)
    "leadership_engine": {
        "enabled": True,
        "correlation_threshold": 0.15,  # Corrélation ES/NQ minimum
        "persistence_bars": 2,          # Persistance requise
        "adaptive_windows": [5, 15, 30], # Fenêtres adaptatives
        "anti_ping_pong": True,         # Éviter les changements rapides
        "compensation": {
            "strong_leadership": 0.05,   # +5% confluence si leadership fort
            "weak_leadership": -0.03,    # -3% confluence si leadership faible
            "no_leadership": 0.00        # Pas de compensation
        }
    },

    # 5) Gates microstructure & ADN MIA — on gardera les tiens,
    # mais ils seront modulés par 'iv_adapter.sizing' au runtime.
    "gates": {
        "no_trade_near_poc_norm": 0.15,
        "beyond_sd2_size_factor": 0.5,  # valeur de base (overridable par iv_adapter)
        "min_dom_depth_mult": 2.0,
        "max_spread_ticks": 1,
        "vwap_slope_confirm": True,
        "stale_data_max_minutes": 5,    # Données max 5 minutes
        "min_volume_threshold": 100,    # Volume minimum
        "max_volatility_threshold": 0.50, # Volatilité max 50%
    },

    # 6) Votes — l'IV peut ajouter +1 vote requis en HIGH
    "votes": {
        "base_required": 2,
        "rules": [
            {"when": "VIX>24 or SESSION in ['ASIA','LONDON']", "required": 3},
            {"when": "leadership_ok and confluence>=0.60", "required": 2},
            {"when": "leadership_no_signal and confluence<0.30", "required": 3},
            {"when": "IV_BAND=='HIGH'", "required": "+1"},  # IV HIGH = +1 vote
            {"when": "IV_BAND=='LOW' and confluence>=0.75", "required": "-1"}  # IV LOW + forte confluence = -1 vote
        ],
        "borderline_tolerance": 0.05,   # Tolérance pour votes borderline
        "leadership_compensation": True  # Compensation leadership
    },

    # 7) Exits — on garde ta logique (POC/VAL/VAH, trail SD1) ;
    # l'IV pilotera atr_mult + caps EM.
    "exits": {
        "reversion": {
            "long_from_VAL": {"tp1": "POC", "tp2": "VAH"},
            "short_from_VAH": {"tp1": "POC", "tp2": "VAL"}
        },
        "breakout": {
            "trail_anchor": "VWAP_SD1",
            "partials_on": "volume_nodes"
        },
        "stops": {
            "mode": "footprint_or_atr",
            "atr_window_sec": 30,
            "atr_mult": 1.2   # valeur de base (overridable par iv_adapter)
        },
        "partials": {
            "enabled": True,
            "first_partial_pct": 0.50,  # 50% à TP1
            "second_partial_pct": 0.30, # 30% à TP2
            "trail_remaining": True     # Trail le reste
        }
    },

    # 8) Risk Management adaptatif
    "risk_management": {
        "position_sizing": {
            "base_size": 1,
            "max_size": 3,
            "iv_adaptation": True,      # Adaptation par IV
            "session_adaptation": True, # Adaptation par session
            "confluence_boost": True    # Boost par confluence
        },
        "daily_limits": {
            "max_loss": 500.0,
            "max_trades": 10,
            "max_drawdown": 0.05,       # 5%
            "profit_target": 1000.0
        },
        "per_trade_limits": {
            "max_risk_pct": 0.02,       # 2% par trade
            "min_risk_reward": 1.5,     # 1.5:1 minimum
            "max_duration_hours": 4     # 4h max par trade
        }
    },

    # 9) Session Management
    "session_management": {
        "sessions": {
            "US_OPEN": {
                "hours": "09:30-16:00",
                "risk_multiplier": 1.0,
                "threshold_multiplier": 1.0,
                "options_available": True
            },
            "ASIA": {
                "hours": "18:00-03:00",
                "risk_multiplier": 0.8,
                "threshold_multiplier": 1.1,
                "options_available": False,
                "use_saved_snapshots": True
            },
            "LONDON": {
                "hours": "03:00-09:30",
                "risk_multiplier": 0.9,
                "threshold_multiplier": 1.05,
                "options_available": False,
                "use_saved_snapshots": True
            }
        },
        "snapshot_management": {
            "collect_during_us": True,
            "snapshot_freshness_max_hours": 24,
            "fallback_to_historical": True
        }
    },

    # 10) Monitoring & Alerts
    "monitoring": {
        "performance_tracking": True,
        "real_time_alerts": True,
        "metrics": [
            "win_rate",
            "profit_factor",
            "max_drawdown",
            "sharpe_ratio",
            "iv_adaptation_effectiveness"
        ],
        "alerts": {
            "high_iv_alert": True,
            "leadership_change_alert": True,
            "confluence_drop_alert": True,
            "risk_limit_alert": True
        }
    }
}

# ===== HELPERS IV =====

def iv_percentile(iv_series):
    """Calcule le percentile de la dernière valeur IV"""
    import pandas as pd
    # retourne dernier percentile de la série (0..1)
    s = iv_series.dropna()
    if len(s) < 20: 
        return 0.5
    last = s.iloc[-1]
    rank = (s <= last).mean()
    return float(rank)

def expected_move(spot, iv_annual, days=1):
    """Calcule l'expected move: EM ≈ S * IV * sqrt(T)"""
    import math
    # EM ≈ S * IV * sqrt(T)
    T = max(days, 1) / 252.0
    return float(spot) * float(iv_annual) * math.sqrt(T)

def pick_iv_band(p):
    """Détermine la bande IV basée sur le percentile"""
    # p = percentile (0..1)
    if p < 0.20: 
        return "LOW"
    if p < 0.60: 
        return "MID"
    return "HIGH"

def apply_iv_adaptation(config, features):
    """Applique l'adaptation IV à la configuration"""
    iv_cfg = config["iv_adapter"]
    if not iv_cfg["enabled"]:
        return config
    
    # 1) lire IV 30j (depuis snapshot SPX/NDX le plus récent)
    iv30 = features.get("iv30_annual", 0.20)          # ex: 0.20 = 20%
    iv_pct = features.get("iv30_percentile", 0.50)    # pré-calculé côté snapshot loader
    iv_band = pick_iv_band(iv_pct)
    
    # 2) multipliers seuils
    b = iv_cfg["bands"][iv_band]
    fast_thr = config["workflow_modes"]["fast_track_threshold_base"] * b["fast_mult"]
    std_thr = config["workflow_modes"]["standard_track_threshold_base"] * b["std_mult"]
    
    # 3) votes extra si HIGH
    required_votes = config["votes"]["base_required"] + b.get("votes_delta", 0)
    
    # 4) sizing & guardrails
    sz = iv_cfg["sizing"][iv_band]
    size_mult = sz["size_mult"]
    atr_mult = config["exits"]["stops"]["atr_mult"] * sz["atr_mult"]
    
    # override beyond_sd2 factor dyn
    sd2_factor_base = config["gates"]["beyond_sd2_size_factor"]
    sd2_factor_dyn = min(sd2_factor_base, sz["beyond_sd2_size_factor"])
    
    # 5) expected move caps
    em_caps = {}
    if iv_cfg["guardrails"]["use_expected_move"]:
        em = expected_move(features.get("last_price", 0.0), iv30, iv_cfg["guardrails"]["expected_move_days"])
        tp_cap = em * iv_cfg["guardrails"]["tp_cap_em_mult"]
        sl_floor = em * iv_cfg["guardrails"]["sl_floor_em_mult"]
        em_caps = {"tp_cap": tp_cap, "sl_floor": sl_floor}
    
    # 6) skew bias (optionnel)
    skew_bias = {}
    if iv_cfg["skew_bias"]["enabled"]:
        skew_bps = features.get("skew_put25_minus_call25_bps", 0)  # + = put skew
        if skew_bps >= iv_cfg["skew_bias"]["put25_minus_call25_bps"]:
            skew_bias["confluence_bias_bump_short"] = iv_cfg["skew_bias"]["bias_weight_bump"]
        elif skew_bps <= -iv_cfg["skew_bias"]["put25_minus_call25_bps"]:
            skew_bias["confluence_bias_bump_long"] = iv_cfg["skew_bias"]["bias_weight_bump"]
    
    # 7) term structure guard
    fast_track_allowed = True
    if iv_cfg["term_structure"]["enabled"]:
        st_short = features.get("iv30_annual", iv30)
        st_long = features.get("iv90_annual", iv30)
        if (st_short - st_long) >= iv_cfg["term_structure"]["short_iv_minus_long_iv_bps"]/10000:
            if iv_band == "HIGH" and iv_cfg["term_structure"]["fast_track_hard_off_in_high"]:
                fast_track_allowed = False
    
    return {
        "iv_band": iv_band,
        "fast_threshold": fast_thr,
        "standard_threshold": std_thr,
        "required_votes": required_votes,
        "size_multiplier": size_mult,
        "atr_multiplier": atr_mult,
        "sd2_factor": sd2_factor_dyn,
        "expected_move_caps": em_caps,
        "skew_bias": skew_bias,
        "fast_track_allowed": fast_track_allowed
    }

# ===== VALIDATION =====

def validate_mia_hybrid_config(config):
    """Valide la configuration MIA_HYBRID_FINAL_PLUS"""
    required_keys = [
        "base_config", "workflow_modes", "iv_adapter", 
        "confluence_weights", "leadership_engine", "gates",
        "votes", "exits", "risk_management", "session_management"
    ]
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Configuration manquante: {key}")
    
    # Validation spécifique IV adapter
    iv_cfg = config["iv_adapter"]
    if iv_cfg["enabled"]:
        if "bands" not in iv_cfg:
            raise ValueError("IV adapter: bands manquantes")
        if "sizing" not in iv_cfg:
            raise ValueError("IV adapter: sizing manquant")
    
    return True

# ===== EXPORT =====

if __name__ == "__main__":
    # Test de validation
    try:
        validate_mia_hybrid_config(MIA_HYBRID_FINAL_PLUS)
        print("✅ Configuration MIA_HYBRID_FINAL_PLUS validée")
    except Exception as e:
        print(f"❌ Erreur validation: {e}")

