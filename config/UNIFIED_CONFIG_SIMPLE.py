"""
═══════════════════════════════════════════════════════════════════════════════
                CONFIGURATION UNIFIÉE SIMPLIFIÉE - MIA IA SYSTEM
═══════════════════════════════════════════════════════════════════════════════

⚠️ CE FICHIER CONTIENT TOUS LES PARAMÈTRES EN UN SEUL ENDROIT!
   Plus de valeurs éparpillées dans 10 fichiers différents!

Date: 13 Décembre 2025
Version: 1.0 - Configuration Simplifiée

Objectif: 8-15 trades/jour avec WR > 55%

═══════════════════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════════════════════
#                           SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

# Confidence minimum pour accepter un signal
# 🔧 SIMPLIFIÉ: 1.00 → 0.50 (divisé par 2!)
MIN_CONFIDENCE = {
    'ES': 0.50,    # Était 1.00 (trop strict!)
    'NQ': 0.50,    # Était 1.00 (trop strict!)
    'RTY': 0.55,   # Légèrement plus strict
}

# Distance maximum au niveau MenthorQ le plus proche (en ticks)
# 🔧 SIMPLIFIÉ: ES 8→15, NQ 10→20
MAX_DISTANCE_TICKS = {
    'ES': 15,      # Était 8t (trop strict!) → 15t = 3.75 pts
    'NQ': 20,      # Était 10t (trop strict!) → 20t = 5 pts
    'RTY': 15,     # Était 12t → 15t
}


# ═══════════════════════════════════════════════════════════════════════════════
#                           TRADE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

# Stop Loss en ticks (gardé tel quel - bien calibré)
SL_TICKS = {
    'ES': 15,      # $187.50
    'NQ': 25,      # $125.00
    'RTY': 30,     # $150.00
}

# Take Profit en ticks (gardé tel quel - bien calibré)
TP_TICKS = {
    'ES': 15,      # $187.50 - R:R 1:1
    'NQ': 31,      # $155.00 - R:R 1.24:1
    'RTY': 40,     # $200.00 - R:R 1.33:1
}

# Tick size
TICK_SIZE = {
    'ES': 0.25,
    'NQ': 0.25,
    'RTY': 0.10,
}

# Tick value ($)
TICK_VALUE = {
    'ES': 12.50,
    'NQ': 5.00,
    'RTY': 5.00,
}


# ═══════════════════════════════════════════════════════════════════════════════
#                           SESSIONS DE TRADING
# ═══════════════════════════════════════════════════════════════════════════════

# Sessions de trading autorisées (heures Paris)
TRADING_SESSIONS = {
    # Session: (start_hour, start_minute, end_hour, end_minute)
    'London': (8, 0, 11, 0),           # 08:00 - 11:00
    'US Morning': (15, 50, 17, 0),     # 15:50 - 17:00
    'Power Hour': (20, 0, 21, 25),     # 20:00 - 21:25
}

# Périodes bloquées (ne JAMAIS trader)
BLOCKED_PERIODS = {
    'Overnight': (0, 0, 8, 0),         # 00:00 - 08:00
    'Pre-Market': (11, 0, 15, 50),     # 11:00 - 15:50
    'Lunch': (17, 0, 20, 0),           # 17:00 - 20:00
    'Post-Market': (21, 25, 24, 0),    # 21:25 - 00:00
}


# ═══════════════════════════════════════════════════════════════════════════════
#                           RISK MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

# Perte journalière max par symbole
DAILY_LOSS_LIMIT = {
    'ES': -500.0,   # Stop trading si -$500
    'NQ': -500.0,
    'RTY': -300.0,
}

# Max positions simultanées
MAX_POSITIONS = {
    'ES': 1,
    'NQ': 1,
    'RTY': 1,
}

# Cooldown après trade (secondes)
COOLDOWN_SECONDS = {
    'after_win': 180,    # 3 minutes après gain
    'after_loss': 300,   # 5 minutes après perte
}

# Max pertes consécutives avant pause
MAX_CONSECUTIVE_LOSSES = 3

# Pause après max pertes (minutes)
PAUSE_AFTER_LOSSES_MINUTES = 10

# VIX threshold pour arrêter de trader
VIX_STOP_THRESHOLD = 35.0


# ═══════════════════════════════════════════════════════════════════════════════
#                           FILTRES ACTIFS
# ═══════════════════════════════════════════════════════════════════════════════

# 5 filtres essentiels uniquement!
ACTIVE_FILTERS = {
    # ✅ FILTRES OBLIGATOIRES
    'ml_3layer_score': True,       # Cœur du système
    'menthorq_distance': True,     # Edge principal
    'session_hours': True,         # Évite périodes toxiques
    'vix_filter': True,            # Protection capitale
    'risk_manager': True,          # Limite pertes

    # ❌ FILTRES DÉSACTIVÉS (over-engineering)
    'pressure_strength': False,     # Trop restrictif
    'trend_direction': False,       # Bloque bons signaux
    'intraday_bracket': False,      # Complexe sans valeur
    'dual_mode_strategy': False,    # Ajoute complexité
    'level_context': False,         # Déjà fait par ML
    'session_quality_score': False, # Redondant
    'vwap_distance': False,         # Trop restrictif
}


# ═══════════════════════════════════════════════════════════════════════════════
#                           NIVEAUX MENTHORQ
# ═══════════════════════════════════════════════════════════════════════════════

# Niveaux à considérer pour entrée (par priorité)
MENTHORQ_ENTRY_LEVELS = {
    'priority_1': ['gex_1', 'gex_2', 'gex_3', 'hvl', 'gamma_wall_0dte'],
    'priority_2': ['gex_4', 'gex_5', 'hvl_0dte', 'call_resistance', 'put_support'],
    'priority_3': ['blind_spot_1', 'blind_spot_2', 'blind_spot_3', 'vwap'],
}

# Niveaux pour placement TP
MENTHORQ_TP_LEVELS = [
    'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    'call_resistance', 'put_support', 'hvl',
    'call_resistance_0dte', 'put_support_0dte', 'hvl_0dte',
]

# Niveaux pour placement SL (support)
MENTHORQ_SL_SUPPORT = [
    'gex_5', 'gex_4', 'gex_3', 'gex_2', 'gex_1',
    'put_support', 'hvl', 'vwap',
]

# Niveaux pour placement SL (résistance)
MENTHORQ_SL_RESISTANCE = [
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
    'call_resistance', 'hvl', 'vwap',
]


# ═══════════════════════════════════════════════════════════════════════════════
#                           HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_config(symbol: str) -> dict:
    """Retourne la config complète pour un symbole."""
    return {
        'min_confidence': MIN_CONFIDENCE.get(symbol, 0.50),
        'max_distance': MAX_DISTANCE_TICKS.get(symbol, 15),
        'sl_ticks': SL_TICKS.get(symbol, 15),
        'tp_ticks': TP_TICKS.get(symbol, 15),
        'tick_size': TICK_SIZE.get(symbol, 0.25),
        'tick_value': TICK_VALUE.get(symbol, 12.50),
        'daily_loss_limit': DAILY_LOSS_LIMIT.get(symbol, -500),
        'max_positions': MAX_POSITIONS.get(symbol, 1),
    }


def is_filter_active(filter_name: str) -> bool:
    """Vérifie si un filtre est actif."""
    return ACTIVE_FILTERS.get(filter_name, False)


def is_in_trading_session(hour: int, minute: int) -> tuple:
    """
    Vérifie si on est dans une session de trading.

    Returns:
        (is_in_session: bool, session_name: str or None)
    """
    time_minutes = hour * 60 + minute

    for session_name, (sh, sm, eh, em) in TRADING_SESSIONS.items():
        start = sh * 60 + sm
        end = eh * 60 + em

        if start <= time_minutes < end:
            return True, session_name

    return False, None


def is_blocked_period(hour: int, minute: int) -> tuple:
    """
    Vérifie si on est dans une période bloquée.

    Returns:
        (is_blocked: bool, period_name: str or None)
    """
    time_minutes = hour * 60 + minute

    for period_name, (sh, sm, eh, em) in BLOCKED_PERIODS.items():
        start = sh * 60 + sm
        end = eh * 60 + em

        if start <= time_minutes < end:
            return True, period_name

    return False, None


# ═══════════════════════════════════════════════════════════════════════════════
#                           AFFICHAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def print_config():
    """Affiche la configuration de manière lisible."""
    print("\n" + "=" * 70)
    print("          CONFIGURATION MIA IA SYSTEM - SIMPLIFIÉE")
    print("=" * 70)

    print("\n📊 SEUILS DE SIGNAL:")
    for sym in ['ES', 'NQ', 'RTY']:
        print(f"   {sym}: Confidence ≥ {MIN_CONFIDENCE[sym]:.0%}, "
              f"Distance ≤ {MAX_DISTANCE_TICKS[sym]}t")

    print("\n💰 TP/SL:")
    for sym in ['ES', 'NQ', 'RTY']:
        tp_usd = TP_TICKS[sym] * TICK_VALUE[sym]
        sl_usd = SL_TICKS[sym] * TICK_VALUE[sym]
        rr = TP_TICKS[sym] / SL_TICKS[sym]
        print(f"   {sym}: TP {TP_TICKS[sym]}t (${tp_usd:.0f}), "
              f"SL {SL_TICKS[sym]}t (${sl_usd:.0f}), R:R {rr:.2f}")

    print("\n⏰ SESSIONS:")
    for name, (sh, sm, eh, em) in TRADING_SESSIONS.items():
        print(f"   {name}: {sh:02d}:{sm:02d} - {eh:02d}:{em:02d}")

    print("\n✅ FILTRES ACTIFS:")
    for name, active in ACTIVE_FILTERS.items():
        status = "✅" if active else "❌"
        print(f"   {status} {name}")

    print("\n🛡️ RISK:")
    print(f"   Daily Loss: ${DAILY_LOSS_LIMIT['ES']:.0f}")
    print(f"   Max Positions: {MAX_POSITIONS['ES']}")
    print(f"   VIX Stop: >{VIX_STOP_THRESHOLD}")
    print(f"   Max Losses Consécutives: {MAX_CONSECUTIVE_LOSSES}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print_config()









