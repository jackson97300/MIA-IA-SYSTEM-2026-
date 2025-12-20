"""
config/unified_thresholds.py

🎯 SOURCE UNIQUE DE VÉRITÉ - SEUILS SYSTÈME MENTHORQ

⚠️ TOUS LES AUTRES MODULES DOIVENT IMPORTER D'ICI
   Plus de seuils hardcodés ailleurs!

Version: 1.0 - Phase 1 Fixes Critiques
Date: 18 Novembre 2025
"""

# ═══════════════════════════════════════════════════════════════════════
# MODE CALIBRAGE
# ═══════════════════════════════════════════════════════════════════════

CALIBRATION_MODE = True  # ⚠️ Mettre False en production

# ═══════════════════════════════════════════════════════════════════════
# SEUILS MINIMAUX DE CONFIDENCE (Unifiés)
# ═══════════════════════════════════════════════════════════════════════

if CALIBRATION_MODE:
    # ✅ MODE CALIBRAGE (Basé sur données réelles trades gagnants)
    # 📊 OPTIMISÉ 19/11/2025: Seuils basés sur analyse 482 trades (201 gagnants)
    #    Confluence moyenne gagnants: 0.666 (médiane: 0.750)
    #    Plus souple que durcis (0.75) mais fonctionnellement prouvé
    MIN_TOTAL_CONFIDENCE = {
        'ES': 0.24,    # ✅ MODIFIÉ 27/11: 0.30 → 0.24 (cohérent avec seuils individuels)
        'NQ': 0.24,    # ✅ MODIFIÉ 27/11: 0.30 → 0.24 (cohérent avec seuils individuels)
        'RTY': 0.24    # ✅ MODIFIÉ 27/11: 0.30 → 0.24 (cohérent avec seuils individuels)
    }

    # ✅ MODIFIÉ 27/11/2025: Seuils qualité améliorés pour trades de meilleure qualité
    #    MenthorQ: 0.30, OrderFlow: 0.17, Context: 0.20
    MIN_LAYER_CONFIDENCE = {
        'ES': {
            'layer1': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
            'layer2': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
            'layer3': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
        },
        'NQ': {
            'layer1': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
            'layer2': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
            'layer3': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
        },
        'RTY': {
            'layer1': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
            'layer2': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
            'layer3': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
        }
    }

else:
    # 🔒 MODE PRODUCTION (Strict)
    MIN_TOTAL_CONFIDENCE = {
        'ES': 0.24,    # ✅ MODIFIÉ 27/11: 0.30 → 0.24 (cohérent avec seuils individuels)
        'NQ': 0.24,    # ✅ MODIFIÉ 27/11: 0.30 → 0.24 (cohérent avec seuils individuels)
        'RTY': 0.24    # ✅ MODIFIÉ 27/11: 0.30 → 0.24 (cohérent avec seuils individuels)
    }

    MIN_LAYER_CONFIDENCE = {
        'ES': {
            'layer1': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
            'layer2': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
            'layer3': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
        },
        'NQ': {
            'layer1': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
            'layer2': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
            'layer3': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
        },
        'RTY': {
            'layer1': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
            'layer2': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
            'layer3': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
        }
    }

# ═══════════════════════════════════════════════════════════════════════
# POIDS DES LAYERS (50% + 30% + 20%)
# ═══════════════════════════════════════════════════════════════════════

LAYER_WEIGHTS = {
    "menthorq": 0.50,    # 50% - Signal primaire (Options data)
    "orderflow": 0.30,   # 30% - Validateur directionnel
    "context": 0.20      # 20% - Filtre contextuel
}

# ═══════════════════════════════════════════════════════════════════════
# POIDS DÉTAILLÉS LAYER 1 - MENTHORQ (Total: 50%)
# 🔥 OPTIMISÉ: next_wall 8%→15%, blind_spots 8%→10%, scores 6%→2%
# ═══════════════════════════════════════════════════════════════════════

MENTHORQ_WEIGHTS = {
    "next_wall": 0.15,        # 15% (était 0.08) ⚡ FIX CRITIQUE #1
    "gamma_walls": 0.10,      # 10% (call_resistance, put_support)
    "gex_levels": 0.10,       # 10% (gex_1 à gex_10)
    "blind_spots": 0.10,      # 10% (était 0.08) - Zones non hedgées importantes
    "distances": 0.08,        # 8% (hvl, vwap, etc.)
    "scores": 0.02            # 2% (était 0.06) - Scores dérivés
}
# Total: 55% → Ajusté dans ml_3layer_filter.py

# ═══════════════════════════════════════════════════════════════════════
# POIDS DÉTAILLÉS LAYER 2 - ORDERFLOW (Total: 30%)
# ═══════════════════════════════════════════════════════════════════════

ORDERFLOW_WEIGHTS = {
    "delta": 0.12,            # 12% - Delta cumulé
    "volume": 0.06,           # 6% - Volume profile
    "dom": 0.06,              # 6% - DOM imbalance
    "pressure": 0.04,         # 4% - Institutional pressure
    "battle_navale": 0.02     # 2% - Battle Navale score
}

# ═══════════════════════════════════════════════════════════════════════
# POIDS DÉTAILLÉS LAYER 3 - CONTEXT (Total: 20%)
# ═══════════════════════════════════════════════════════════════════════

CONTEXT_WEIGHTS = {
    "vwap": 0.08,             # 8% - VWAP distance/bands
    "value_area": 0.06,       # 6% - VAH/VAL/VPOC
    "structure": 0.04,        # 4% - Market structure
    "volatility": 0.02        # 2% - ATR/VIX regime
}

# ═══════════════════════════════════════════════════════════════════════
# TOLÉRANCES DISTANCES (Optimisées)
# ═══════════════════════════════════════════════════════════════════════

DISTANCE_TOLERANCE = {
    # next_wall (le plus critique)
    'next_wall': {
        'active_zone_min': 20,      # Min 20 ticks (trop près = breakout)
        'active_zone_max': 80,      # Max 80 ticks (zone oscillations)
        'influence_zone': 150,      # Jusqu'à 150 ticks influence (✅ MODIFIÉ CALIBRAGE: zone élargie)
        'score_active': 0.85,       # Score si dans zone active
        'score_influence': 0.60     # Score si dans zone influence
    },

    # GEX levels
    'gex_level': {
        'very_close': 30,           # < 30 ticks = très proche
        'close': 80,                # < 80 ticks = proche
        'medium': 150,              # < 150 ticks = moyen
        'score_very_close': 0.80,
        'score_close': 0.60,
        'score_medium': 0.40
    },

    # HVL
    'hvl': {
        'close': 50,                # < 50 ticks = proche
        'medium': 150,              # < 150 ticks = moyen
        'far': 300,                 # < 300 ticks = loin
        'score_close': 0.70,
        'score_medium': 0.50,
        'score_far': 0.30
    },

    # Gamma walls (call_resistance, put_support)
    'gamma_wall': {
        'close': 40,                # < 40 ticks
        'medium': 100,              # < 100 ticks
        'far': 200,                 # < 200 ticks
        'score_close': 0.75,
        'score_medium': 0.55,
        'score_far': 0.35
    },

    # Blind spots
    'blind_spot': {
        'nearby': 60,               # < 60 ticks = nearby
        'reachable': 150,           # < 150 ticks = reachable
        'score_nearby': 0.70,
        'score_reachable': 0.50
    }
}

# ═══════════════════════════════════════════════════════════════════════
# ORDERFLOW VALIDATION (Assouplissement)
# 🔥 FIX CRITIQUE #2: Tolérer delta légèrement opposé près de niveaux
# ═══════════════════════════════════════════════════════════════════════

ORDERFLOW_VALIDATION = {
    # ✅ MODIFIÉ CALIBRAGE 18/11: Delta validation ultra-permissive
    'delta': {
        'strong_confirmation': 5,        # ✅ MODIFIÉ: 10 → 5 (plus permissif)
        'weak_confirmation': -5,         # ✅ MODIFIÉ: 0 → -5 (accepter delta légèrement négatif)
        'tolerable_opposite': -25,        # ✅ MODIFIÉ: -15 → -25 (plus tolérant)
        'min_distance_for_tolerance': 120  # ✅ MODIFIÉ: 80 → 120 (zone tolérance élargie)
    },

    # Imbalance validation
    'imbalance': {
        'strong': 0.30,                  # |imbalance| > 0.30 = fort
        'moderate': 0.15,                # |imbalance| > 0.15 = modéré
        'weak': 0.05,                    # |imbalance| > 0.05 = faible
        'flip_threshold': -0.30          # imbalance > -0.30 = flip possible
    },

    # Momentum flip detection
    'momentum_flip': {
        'use_microgap': True,            # Utiliser microgap pour détecter flip
        'microgap_threshold': 0.05,      # |microgap| > 0.05 = significatif
        'delta_rate_threshold': 5        # |delta_rate| > 5 = momentum change
    }
}

# ═══════════════════════════════════════════════════════════════════════
# CONFLUENCE DETECTION (Nouveau)
# ═══════════════════════════════════════════════════════════════════════

CONFLUENCE_CONFIG = {
    'enabled': True,                     # Activer détection confluence
    'tolerance_ticks': 15,               # 15 ticks = confluence
    'min_levels': 2,                     # Minimum 2 niveaux
    'bonus_per_level': 0.10,             # +10% par niveau additionnel
    'max_bonus': 0.25,                   # Max +25% bonus confluence

    # Importance par type de niveau (pour pondération)
    'level_importance': {
        'next_wall': 1.0,                # Très important
        'gamma_wall': 0.9,               # Très important
        'hvl': 0.9,                      # Très important
        'gex_level': 0.8,                # Important (top 3 = 0.9)
        'blind_spot': 0.7,               # Important
        'vwap': 0.7,                     # Moyen
        'value_area': 0.6                # Moyen
    }
}

# ═══════════════════════════════════════════════════════════════════════
# NOUVEAUX SEUILS QUALITÉ (19/11/2025)
# ═══════════════════════════════════════════════════════════════════════

# Expectancy minimum (P&L attendu positif)
# 📊 OPTIMISÉ 19/11/2025: Réduit de $10 → $5 (plus souple, basé sur P&L moyen gagnants: $113.09)
MIN_EXPECTANCY = {
    'ES': 5.0,    # 📊 OPTIMISÉ: 10.0 → 5.0 (plus souple, basé sur données réelles)
    'NQ': 5.0,    # 📊 OPTIMISÉ: 10.0 → 5.0 (plus souple, basé sur données réelles)
    'RTY': 5.0    # 📊 OPTIMISÉ: 10.0 → 5.0 (plus souple, basé sur données réelles)
}

# WIN probability minimum (nouvelle règle)
# 📊 OPTIMISÉ 19/11/2025: Gardé à 15% (déjà bas, win rate réel: 41.7%)
MIN_WIN_PROBABILITY = {
    'ES': 0.15,   # 15% minimum (basé sur win rate réel: 41.7%)
    'NQ': 0.15,   # 15% minimum (basé sur win rate réel: 41.7%)
    'RTY': 0.15   # 15% minimum (basé sur win rate réel: 41.7%)
}

# Session quality score minimum
# 🔥 CORRIGÉ 20/11/2025: Réduit à 20% pour permettre des trades (sessions actuelles: 20-30%)
#    Le calcul de session quality est très strict (hot zone 40% + VIX + volume + momentum)
#    En dehors de la hot zone, le score max est ~60%, donc 50% était trop restrictif
MIN_SESSION_QUALITY = {
    'ES': 0.20,   # 🔥 CORRIGÉ: 0.50 → 0.20 (permet trades hors hot zone)
    'NQ': 0.20,   # 🔥 CORRIGÉ: 0.50 → 0.20 (permet trades hors hot zone)
    'RTY': 0.20   # 🔥 CORRIGÉ: 0.50 → 0.20 (permet trades hors hot zone)
}

# ═══════════════════════════════════════════════════════════════════════
# ML THRESHOLDS PAR TIER (Aligné avec MIN_TOTAL_CONFIDENCE)
# ═══════════════════════════════════════════════════════════════════════

if CALIBRATION_MODE:
    # ✅ MODIFIÉ CALIBRAGE 18/11: Seuils ML réduits pour plus de signaux
    ML_THRESHOLD_BY_TIER = {
        "tier1": 0.20,  # 🔧 TEST: Réduit de 0.25 → 0.20
        "tier2": 0.20,  # 🔧 TEST: Réduit de 0.25 → 0.20
        "tier3": 0.30   # 🔧 TEST: Réduit de 0.35 → 0.30
    }
else:
    ML_THRESHOLD_BY_TIER = {
        "tier1": 0.20,  # 🔧 TEST: Réduit de 0.25 → 0.20
        "tier2": 0.20,  # 🔧 TEST: Réduit de 0.25 → 0.20
        "tier3": 0.30   # 🔧 TEST: Réduit de 0.35 → 0.30
    }

# ═══════════════════════════════════════════════════════════════════════
# SEUILS DE VALIDATION DES SIGNAUX (ajouté 20/11/2025)
# ═══════════════════════════════════════════════════════════════════════

VALIDATION_THRESHOLDS = {
    'confluence': 0.50,  # 🔧 TEST: Réduit de 0.75 → 0.50
    'expectancy': 10.0,
    'win_estimate': 15.0,
    'session_score': 70.0,

    # Seuils par composante
    'menthorq_min': 0.50,
    'orderflow_min': 0.20,
    'context_min': 0.15,

    # Seuils par session (ajustés basés sur analyse 751 trades récents)
    # Analyse: P25 wins US=0.548, P50 wins US=0.71, P75 wins US=0.80
    # ✅ CONFIGURATION ASIA SPÉCIFIQUE 20/11: Seuils adaptés pour liquidité faible
    # Objectif: 60-70% des trades passent avec WR > 42% (plus permissif pour ASIA)
    'asia': {
        'confluence': 0.68,   # ✅ CONFIG ASIA: Juste milieu qualité/quantité (291 trades, évite 341 trades faibles 0.62-0.64)
        'orderflow': 0.00,   # ✅ CONFIG ASIA: Désactivé (pas fiable en ASIA)
        'context': 0.08,     # ✅ CONFIG ASIA: Maintenu à 0.08
        'menthorq': 0.15     # ✅ CONFIG ASIA: Nouveau seuil MenthorQ (indicateur principal)
    },
    'london': {
        'confluence': 0.65,   # ✅ ASSOUPLI: 0.68 → 0.65 (-0.03, plus permissif)
        'orderflow': 0.10,    # ✅ ASSOUPLI: 0.12 → 0.10 (-0.02)
        'context': 0.08,      # ✅ ASSOUPLI: 0.10 → 0.08 (-0.02)
        'menthorq': 0.35      # 🔥 CORRIGÉ 20/11: Ajouté seuil MenthorQ pour LONDON (plus permissif que US)
    },
    'us': {
        'confluence': 0.63,   # ✅ ASSOUPLI: 0.66 → 0.63 (-0.03, plus permissif)
        'orderflow': 0.08,    # ✅ ASSOUPLI: 0.10 → 0.08 (-0.02, scores souvent absents)
        'context': 0.06,      # ✅ ASSOUPLI: 0.08 → 0.06 (-0.02, scores souvent absents)
        'menthorq': 0.45      # 🔥 CORRIGÉ 20/11: Ajouté seuil MenthorQ pour US (0.50 par défaut trop strict)
    }
}

# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def get_min_confidence(symbol: str) -> float:
    """Retourne confidence minimale pour un symbole"""
    return MIN_TOTAL_CONFIDENCE.get(symbol, MIN_TOTAL_CONFIDENCE['ES'])

def get_layer_min_confidence(symbol: str, layer: str) -> float:
    """Retourne confidence minimale pour un layer d'un symbole"""
    symbol_conf = MIN_LAYER_CONFIDENCE.get(symbol, MIN_LAYER_CONFIDENCE['ES'])
    return symbol_conf.get(layer, 0.10)

def get_distance_score(level_type: str, distance_ticks: float) -> float:
    """Calcule score basé sur distance à un niveau"""
    if level_type not in DISTANCE_TOLERANCE:
        return 0.0

    config = DISTANCE_TOLERANCE[level_type]
    abs_dist = abs(distance_ticks)

    # next_wall (zones spéciales)
    if level_type == 'next_wall':
        if config['active_zone_min'] <= abs_dist <= config['active_zone_max']:
            return config['score_active']
        elif abs_dist <= config['influence_zone']:
            return config['score_influence']
        else:
            return 0.0

    # Autres niveaux (simple comparaison)
    if 'very_close' in config and abs_dist <= config['very_close']:
        return config.get('score_very_close', 0.80)
    elif 'close' in config and abs_dist <= config['close']:
        return config.get('score_close', 0.60)
    elif 'medium' in config and abs_dist <= config['medium']:
        return config.get('score_medium', 0.40)
    elif 'far' in config and abs_dist <= config.get('far', 999):
        return config.get('score_far', 0.20)
    else:
        return 0.0

def is_orderflow_valid(signal_side: str, delta: float, imbalance: float,
                       distance_to_level: float) -> bool:
    """
    Valide l'orderflow pour un signal

    🔥 ASSOUPLISSEMENT: Tolère delta légèrement opposé si près d'un niveau
    """
    of_config = ORDERFLOW_VALIDATION

    if signal_side == "LONG":
        # Pour LONG
        if delta > of_config['delta']['strong_confirmation']:
            return True  # Delta fortement positif
        elif delta > of_config['delta']['weak_confirmation']:
            return True  # Delta légèrement positif
        elif delta > of_config['delta']['tolerable_opposite']:
            # Delta légèrement négatif: tolérer si près niveau
            if distance_to_level < of_config['delta']['min_distance_for_tolerance']:
                # Vérifier imbalance improving
                if imbalance > of_config['imbalance']['flip_threshold']:
                    return True  # Flip possible

        return False

    else:  # SHORT
        # Pour SHORT (logique inversée)
        if delta < -of_config['delta']['strong_confirmation']:
            return True
        elif delta < -of_config['delta']['weak_confirmation']:
            return True
        elif delta < -of_config['delta']['tolerable_opposite']:
            if distance_to_level < of_config['delta']['min_distance_for_tolerance']:
                if imbalance < -of_config['imbalance']['flip_threshold']:
                    return True

        return False

# ═══════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    'CALIBRATION_MODE',
    'MIN_TOTAL_CONFIDENCE',
    'MIN_LAYER_CONFIDENCE',
    'MIN_EXPECTANCY',
    'MIN_WIN_PROBABILITY',
    'MIN_SESSION_QUALITY',
    'VALIDATION_THRESHOLDS',
    'LAYER_WEIGHTS',
    'MENTHORQ_WEIGHTS',
    'ORDERFLOW_WEIGHTS',
    'CONTEXT_WEIGHTS',
    'DISTANCE_TOLERANCE',
    'ORDERFLOW_VALIDATION',
    'CONFLUENCE_CONFIG',
    'ML_THRESHOLD_BY_TIER',
    'get_min_confidence',
    'get_layer_min_confidence',
    'get_distance_score',
    'is_orderflow_valid'
]
