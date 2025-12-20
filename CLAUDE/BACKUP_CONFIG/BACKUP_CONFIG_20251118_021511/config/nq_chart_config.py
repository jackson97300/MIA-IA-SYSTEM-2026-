#!/usr/bin/env python3
"""
Configuration pour la collecte de données NQ sur Chart 4
Basé sur la duplication du Chart 3 existant
"""

# Configuration Chart NQ
NQ_CHART_CONFIG = {
    "chart_number": 4,
    "symbol": "NQU25_FUT_CME",
    "description": "E-mini NASDAQ 100 Futures",
    
    # Paramètres de trading
    "tick_size": 0.25,
    "tick_value": 5.00,  # NQ = 5$ par tick vs ES = 12.50$
    "contract_size": 20,  # NQ = 20x l'indice vs ES = 50x
    
    # Volatilité relative (NQ ~1.5x plus volatil que ES)
    "volatility_multiplier": 1.5,
    
    # Position sizing adapté
    "base_position_size": 1,
    "max_position_size": 2,  # Réduit vs ES (3)
    "risk_per_trade_percent": 0.3,  # Réduit vs ES (0.5%)
    
    # Fichiers de données
    "data_files": {
        "basedata": "chart_4_basedata_{date}.jsonl",
        "vwap": "chart_4_vwap_{date}.jsonl", 
        "vva": "chart_4_vva_{date}.jsonl",
        "depth": "chart_4_depth_{date}.jsonl",
        "pvwap": "chart_4_pvwap_{date}.jsonl"
    }
}

# Configuration MenthorQ pour NQ
NQ_MENTHORQ_CONFIG = {
    "chart_number": 4,
    "study_id": 4,  # Même study ID que ES
    "subgraphs_count": 10,
    
    # Niveaux spécifiques NQ
    "gamma_levels": {
        "call_resistance": "Call Resistance",
        "put_support": "Put Support", 
        "gamma_wall_0dte": "Gamma Wall 0DTE",
        "hvl": "HVL"
    },
    
    "blind_spots": {
        "prefix": "BL",
        "count": 10
    },
    
    "swing_levels": {
        "prefix": "SG", 
        "count": 10
    }
}

# Configuration options NDX pour NQ
NQ_OPTIONS_CONFIG = {
    "underlying_symbol": "NDX",  # Options NDX pour NQ
    "options_symbol": "NDX",
    "expiry_dates": ["weekly", "monthly"],
    
    # Métriques calculées
    "metrics": {
        "pcr_oi": "put_call_ratio_oi",
        "pcr_volume": "put_call_ratio_volume", 
        "iv_skew": "implied_volatility_skew",
        "gamma_exposure": "gamma_exposure"
    }
}

# Configuration corrélation ES/NQ
ES_NQ_CORRELATION_CONFIG = {
    "correlation_threshold": 0.8,  # Limite de corrélation
    "max_correlated_positions": 1,  # Max 1 position corrélée
    "correlation_window": 20,  # 20 périodes pour calcul
    "rebalance_frequency": "daily"
}






