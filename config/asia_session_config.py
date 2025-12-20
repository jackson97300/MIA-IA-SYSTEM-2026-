"""
Configuration spécifique pour session ASIA
Session ASIA: 00h-06h UTC (liquidité faible, spreads larges)

Date: 20 Novembre 2025
"""

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION ASIA - SESSION SPÉCIFIQUE
# ═══════════════════════════════════════════════════════════════════════

ASIA_CONFIG = {
    'thresholds': {
        'confluence': 0.50,      # ⬆️ de 0.68 à 0.50 - OPTIMISÉ 02/12/2025 (setups premium)
        'orderflow': 0.10,       # ⬆️ RÉACTIVÉ à 0.10 (évite dead zone 0.10-0.15)
        'context': 0.12,         # ⬆️ de 0.08 à 0.12 (contexte minimum décent)
        'menthorq': 0.35         # ⬆️ de 0.15 à 0.35 (niveau minimum décent)
    },

    'features': {
        'use_orderflow': True,   # ✅ Réactivé avec seuil 0.10
        'use_dom': False,        # ❌ DOM toujours désactivé (peu fiable)
        'use_menthorq': True,    # ✅ Principal indicateur
        'menthorq_ttl': 30       # TTL plus long (30s) pour stabilité
    },

    'risk_adjustments': {
        'sl_extra_ticks': 10,    # SL plus large (liquidité faible, spreads larges)
        'size_multiplier': 0.5,  # Position réduite de 50% (risque ASIA)
        'min_atr': 3.0,          # ATR minimum requis (éviter calme plat)
        'max_spread': 2.0        # Spread max toléré (éviter spreads excessifs)
    },

    'session_hours_utc': {
        'start': 0,              # 00h00 UTC
        'end': 6                 # 06h00 UTC
    }
}

# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def get_asia_config() -> dict:
    """Retourne la configuration ASIA"""
    return ASIA_CONFIG

def is_asia_session() -> bool:
    """Vérifie si on est en session ASIA"""
    from datetime import datetime, timezone
    current_hour = datetime.now(timezone.utc).hour
    return 0 <= current_hour < 6

def get_asia_thresholds() -> dict:
    """Retourne les seuils ASIA"""
    return ASIA_CONFIG['thresholds']

def get_asia_risk_adjustments() -> dict:
    """Retourne les ajustements de risque ASIA"""
    return ASIA_CONFIG['risk_adjustments']

__all__ = [
    'ASIA_CONFIG',
    'get_asia_config',
    'is_asia_session',
    'get_asia_thresholds',
    'get_asia_risk_adjustments'
]
