"""
═══════════════════════════════════════════════════════════════════════════════
                    CONFIGURATION CENTRALISÉE DU TRADING
═══════════════════════════════════════════════════════════════════════════════

⚠️  CE FICHIER EST LA SOURCE UNIQUE DE VÉRITÉ!
    Tous les autres fichiers importent depuis ici.

    MODIFIEZ UNIQUEMENT CE FICHIER pour changer les paramètres de trading.

═══════════════════════════════════════════════════════════════════════════════
"""

# ═══════════════════════════════════════════════════════════════════════════════
#                           PARAMÈTRES PAR SYMBOLE
# ═══════════════════════════════════════════════════════════════════════════════

TRADING_CONFIG = {

    # ═══════════════════════════════════════════════════════════════════════════
    # ES - E-mini S&P 500
    # ═══════════════════════════════════════════════════════════════════════════
    'ES': {
        # Caractéristiques du contrat
        'tick_size': 0.25,
        'tick_value': 12.50,        # $ par tick
        'point_value': 50.00,       # $ par point

        # 🎯 TP/SL - Optimisé 13/12/2025 (backtest V8 - sessions)
        # Note: Valeurs par défaut, remplacées dynamiquement par get_session_config()
        'tp_ticks': 12,             # Take Profit en ticks (défaut session)
        'sl_ticks': 12,             # Stop Loss en ticks (défaut session)

        # 📍 Distance maximale au niveau MenthorQ pour entrer
        'max_entry_distance_ticks': 8,

        # 🛡️ Buffers pour SL/TP adaptatif
        'sl_buffer_ticks': 3,       # Buffer sous le niveau support
        'tp_buffer_ticks': 2,       # Buffer avant la résistance

        # Limites SL
        'min_sl_ticks': 10,
        'max_sl_ticks': 25,

        # R:R minimum - 🔧 10/12: Réduit de 0.9 à 0.7 pour permettre TP adaptatif sous résistances (HVL)
        'min_rr_ratio': 0.7,

        # Trailing stop
        'trailing_activation_ticks': 20,
        'trailing_distance_ticks': 8,

        # Circuit breaker
        'max_consecutive_losses': 3,
        'cooldown_after_losses_ms': 1800000,  # 30 min
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # NQ - E-mini Nasdaq 100
    # ═══════════════════════════════════════════════════════════════════════════
    'NQ': {
        # Caractéristiques du contrat
        'tick_size': 0.25,
        'tick_value': 5.00,         # $ par tick
        'point_value': 20.00,       # $ par point

        # 🎯 TP/SL - Optimisé 13/12/2025 (backtest V8 - sessions)
        # Note: Valeurs par défaut, remplacées dynamiquement par get_session_config()
        'tp_ticks': 25,             # Take Profit en ticks (défaut session)
        'sl_ticks': 20,             # Stop Loss en ticks (défaut session)

        # 📍 Distance maximale au niveau MenthorQ pour entrer
        'max_entry_distance_ticks': 10,  # 🎯 10/12: Réduit de 15 à 10

        # 🛡️ Buffers pour SL/TP adaptatif
        'sl_buffer_ticks': 5,       # Buffer sous le niveau support
        'tp_buffer_ticks': 3,       # Buffer avant la résistance

        # Limites SL - 🔧 10/12: Réduit min de 15 à 10 pour permettre SL adaptatif
        'min_sl_ticks': 10,  # Aligné avec max_entry_distance_ticks
        'max_sl_ticks': 35,

        # R:R minimum - 🔧 10/12: Réduit pour permettre TP adaptatif sous résistances
        'min_rr_ratio': 0.7,

        # Trailing stop
        'trailing_activation_ticks': 35,
        'trailing_distance_ticks': 10,

        # Circuit breaker
        'max_consecutive_losses': 2,
        'cooldown_after_losses_ms': 2700000,  # 45 min
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # RTY - E-mini Russell 2000
    # ═══════════════════════════════════════════════════════════════════════════
    'RTY': {
        # Caractéristiques du contrat
        'tick_size': 0.10,
        'tick_value': 5.00,         # $ par tick
        'point_value': 50.00,       # $ par point

        # 🎯 TP/SL - Valeurs originales
        'tp_ticks': 40,             # Take Profit en ticks
        'sl_ticks': 30,             # Stop Loss en ticks

        # 📍 Distance maximale au niveau MenthorQ pour entrer
        'max_entry_distance_ticks': 12,

        # 🛡️ Buffers pour SL/TP adaptatif
        'sl_buffer_ticks': 3,
        'tp_buffer_ticks': 3,

        # Limites SL
        'min_sl_ticks': 20,
        'max_sl_ticks': 60,

        # R:R minimum
        'min_rr_ratio': 1.0,

        # Trailing stop
        'trailing_activation_ticks': 40,
        'trailing_distance_ticks': 15,

        # Circuit breaker
        'max_consecutive_losses': 3,
        'cooldown_after_losses_ms': 1800000,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def get_tp_ticks(symbol: str) -> int:
    """Retourne le TP en ticks pour un symbole."""
    return TRADING_CONFIG.get(symbol, {}).get('tp_ticks', 20)

def get_sl_ticks(symbol: str) -> int:
    """Retourne le SL en ticks pour un symbole."""
    return TRADING_CONFIG.get(symbol, {}).get('sl_ticks', 20)

def get_max_entry_distance(symbol: str) -> int:
    """Retourne la distance max d'entrée en ticks."""
    return TRADING_CONFIG.get(symbol, {}).get('max_entry_distance_ticks', 10)

def get_tick_size(symbol: str) -> float:
    """Retourne la taille du tick."""
    return TRADING_CONFIG.get(symbol, {}).get('tick_size', 0.25)

def get_tick_value(symbol: str) -> float:
    """Retourne la valeur du tick en $."""
    return TRADING_CONFIG.get(symbol, {}).get('tick_value', 12.50)

def get_config(symbol: str) -> dict:
    """Retourne toute la config pour un symbole."""
    return TRADING_CONFIG.get(symbol, TRADING_CONFIG['ES'])


# ═══════════════════════════════════════════════════════════════════════════════
#                           DICTIONNAIRES LEGACY
#           (Pour compatibilité avec le code existant)
# ═══════════════════════════════════════════════════════════════════════════════

# Ces dictionnaires sont générés automatiquement depuis TRADING_CONFIG
# pour maintenir la compatibilité avec le code existant

TP_TICKS = {sym: cfg['tp_ticks'] for sym, cfg in TRADING_CONFIG.items()}
SL_TICKS = {sym: cfg['sl_ticks'] for sym, cfg in TRADING_CONFIG.items()}
MAX_DISTANCE_TO_LEVEL = {sym: cfg['max_entry_distance_ticks'] for sym, cfg in TRADING_CONFIG.items()}
TICK_SIZE = {sym: cfg['tick_size'] for sym, cfg in TRADING_CONFIG.items()}
TICK_VALUE = {sym: cfg['tick_value'] for sym, cfg in TRADING_CONFIG.items()}

# Pour backtest_config.py
TP_SL_CONFIG = {
    sym: {'tp_ticks': cfg['tp_ticks'], 'sl_ticks': cfg['sl_ticks']}
    for sym, cfg in TRADING_CONFIG.items()
}


# ═══════════════════════════════════════════════════════════════════════════════
#                           AFFICHAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def print_config():
    """Affiche la configuration actuelle."""
    print("\n" + "="*60)
    print("         CONFIGURATION TRADING ACTUELLE")
    print("="*60)
    for sym, cfg in TRADING_CONFIG.items():
        print(f"\n  {sym}:")
        print(f"    TP: {cfg['tp_ticks']}t (${cfg['tp_ticks'] * cfg['tick_value']:.2f})")
        print(f"    SL: {cfg['sl_ticks']}t (${cfg['sl_ticks'] * cfg['tick_value']:.2f})")
        print(f"    Entry MAX: {cfg['max_entry_distance_ticks']}t")
        print(f"    R:R min: {cfg['min_rr_ratio']}")
    print("\n" + "="*60)


# ═══════════════════════════════════════════════════════════════════════════════
#                           SEUILS ML 3-LAYER
# ═══════════════════════════════════════════════════════════════════════════════

# Confidence totale minimum pour accepter un trade
# 🔧 12/12/2025: Ajusté basé sur analyse WR
# - 0.30 = trop permissif (laisse passer mauvais trades)
# - 0.80 = trop strict (bloque bons trades)
# - 0.50 = équilibré (filtre mauvais, garde bons)
MIN_TOTAL_CONFIDENCE = {
    'ES': 0.35,    # 🔧 13/12: RESTAURÉ valeur qui marchait (11-12 déc matin)
    'NQ': 0.35,    # 🔧 13/12: RESTAURÉ
    'RTY': 0.35,   # 🔧 13/12: RESTAURÉ
}

# Confidence minimum par layer
# ⚠️ V10.2 16/12/2025: L2 = 0.15 PARTOUT (OrderFlow plus impactant)
# Ces seuils globaux sont utilisés par le ML filter
MIN_LAYER_CONFIDENCE = {
    'ES': {
        'layer1': 0.20,  # 🔧 V10.3: MenthorQ permissif
        'layer2': 0.17,  # 🔥 V10.3: OrderFlow = 0.17 (augmenté de 0.15)
        'layer3': 0.12,  # 🔧 V10.1: Context permissif
    },
    'NQ': {
        'layer1': 0.20,  # 🔧 V10.3: MenthorQ permissif
        'layer2': 0.17,  # 🔥 V10.3: OrderFlow = 0.17 (augmenté de 0.15)
        'layer3': 0.12,  # 🔧 V10.1: Context permissif
    },
    'RTY': {
        'layer1': 0.20,  # 🔧 V10.3: MenthorQ permissif
        'layer2': 0.17,  # 🔥 V10.3: OrderFlow = 0.17 (augmenté de 0.15)
        'layer3': 0.12,  # 🔧 V10.1: Context permissif
    },
}


def get_min_confidence(symbol: str) -> float:
    """Retourne confidence totale minimale pour un symbole."""
    return MIN_TOTAL_CONFIDENCE.get(symbol, 0.30)


def get_layer_min_confidence(symbol: str, layer: str) -> float:
    """Retourne confidence minimale pour un layer d'un symbole."""
    symbol_conf = MIN_LAYER_CONFIDENCE.get(symbol, MIN_LAYER_CONFIDENCE['ES'])
    return symbol_conf.get(layer, 0.10)


# ═══════════════════════════════════════════════════════════════════════════════
#                           PARAMÈTRES GLOBAUX (non par symbole)
# ═══════════════════════════════════════════════════════════════════════════════

GLOBAL_CONFIG = {
    # 📊 Age maximum des données acceptées (en secondes)
    # 🔧 10/12: Augmenté de 5s à 60s pour éviter blocages hors heures actives
    # Le marché futures trade 23h/24 mais le volume est faible la nuit
    'max_data_age_seconds': 60,

    # 📊 Age pour log Discord (ne log que si > cette valeur)
    'data_stale_log_threshold_seconds': 30,

    # 🔒 Lock après ouverture de position
    'opening_lock_ms': 5000,

    # 🔒 Lock après fermeture - WIN vs LOSS
    'post_close_lock_win_ms': 15000,
    'post_close_lock_loss_ms': 30000,
}


def get_max_data_age() -> int:
    """Retourne l'âge max des données en secondes."""
    return GLOBAL_CONFIG['max_data_age_seconds']


# ═══════════════════════════════════════════════════════════════════════════════
#              🏆 CONFIG HYBRIDE V10.1 - 16 DÉC 2025
#
#              ⚠️ LAYER 3 = 0.12 PARTOUT (0.20 bloquait tout!)
#              ⚠️ MENTHORQ = NOTRE EDGE (toujours une distance max!)
#
#              P&L Attendu: $7,082/6j
# ═══════════════════════════════════════════════════════════════════════════════
#
# 📊 CLASSIFICATION DES NIVEAUX MENTHORQ:
#    FORT (3):   gex_1, gex_2, hvl, gamma_wall_level, vwap
#    MOYEN (2):  gex_3-5, hvl_0dte, call/put_resist, blind_spot_1-2
#    FAIBLE (1): vwap_bands, blind_spot_3+, 0dte walls
#
# ═══════════════════════════════════════════════════════════════════════════════

OPTIMAL_SESSION_CONFIGS = {

    # ═══════════════════════════════════════════════════════════════════════════
    # LONDON_ES - V10.2 (16/12/2025: max_distance 12→15)
    # Backtest validation: $2,957 (66.1% WR, 56 trades)
    # ═══════════════════════════════════════════════════════════════════════════
    'LONDON_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,
        'max_distance': 15,  # 🔧 16/12: 12→15 pour capturer GEX proches
        'min_level_score': 2,      # MOYEN+ seulement
        'min_layer1': 0.20,
        'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
        'min_layer3': 0.12,        # ⚠️ V10.1: Réduit de 0.20!
        'enabled': True,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # LONDON_NQ - ACTIVÉ 16/12/2025 | 🔧 20/12: Distance 15→6 (analyse 18-19 déc)
    # ═══════════════════════════════════════════════════════════════════════════
    'LONDON_NQ': {
        'tp_ticks': 25,
        'sl_ticks': 20,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'min_confluence': 1,
        'max_distance': 6,         # 🔥 20/12: 15→6 (WR 60% à ≤6t vs 36% à >6t)
        'min_level_score': 2,      # 🔧 18/12: 0→2 (NQ moins fiable, GEX dérivé QQQ)
        'min_layer1': 0.20,
        'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
        'min_layer3': 0.12,
        'enabled': True,  # ✅ ACTIVÉ 16/12/2025
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # US_MORNING_ES - V10.2 | 🔧 18/12: Score 0→2 (hedging actif)
    # Backtest: +$750 (59.3% WR) vs V9 -$600
    # ═══════════════════════════════════════════════════════════════════════════
    'US_MORNING_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,
        'max_distance': 12,
        'min_level_score': 2,      # 🔧 18/12: 0→2 (PRO: "dealers adjusting fast")
        'min_layer1': 0.20,
        'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
        'min_layer3': 0.12,
        'enabled': True,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # US_MORNING_NQ - V10.2 | 🔧 20/12: Distance 15→6 (analyse 18-19 déc)
    # Backtest: $575 (70.0% WR)
    # ═══════════════════════════════════════════════════════════════════════════
    'US_MORNING_NQ': {
        'tp_ticks': 25,
        'sl_ticks': 20,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'min_confluence': 1,       # ✅ Au moins 1 niveau
        'max_distance': 6,         # 🔥 20/12: 15→6 (WR 60% à ≤6t vs 36% à >6t)
        'min_level_score': 2,      # 🔧 18/12: 0→2 (hedging actif + NQ moins fiable)
        'min_layer1': 0.20,        # ✅ Garder Layer 1 (MenthorQ)
        'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
        'min_layer3': 0.12,
        'enabled': True,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER_HOUR_ES - V10.2
    # Backtest: $900 (71.4% WR)
    # ═══════════════════════════════════════════════════════════════════════════
    'POWER_HOUR_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,
        'max_distance': 10,
        'min_level_score': 0,      # TOUS les niveaux
        'min_layer1': 0.20,
        'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
        'min_layer3': 0.12,
        'enabled': True,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER_HOUR_NQ - V10.1 | 🔧 20/12: Distance 15→6 (analyse 18-19 déc)
    # Backtest: $1,900 (84.6% WR!) 🔥
    # ═══════════════════════════════════════════════════════════════════════════
    'POWER_HOUR_NQ': {
        'tp_ticks': 40,
        'sl_ticks': 30,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'min_confluence': 1,
        'max_distance': 6,         # 🔥 20/12: 15→6 (WR 60% à ≤6t vs 36% à >6t)
        'min_level_score': 2,      # MOYEN+ seulement
        'min_layer1': 0.20,
        'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
        'min_layer3': 0.12,        # ⚠️ V10.1: Réduit de 0.20!
        'enabled': True,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # OFF_HOURS - 🧪 MODE TEST UNIQUEMENT (16/12/2025)
    # Permet de trader hors sessions pour tester le système
    # ⚠️ DÉSACTIVER EN PRODUCTION!
    # ═══════════════════════════════════════════════════════════════════════════
    'OFF_HOURS_ES': {
        'tp_ticks': 12,
        'sl_ticks': 12,
        'cooldown_min': 15,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'min_confluence': 1,
        'max_distance': 15,
        'min_level_score': 0,      # Tous les niveaux pour test
        'min_layer1': 0.20,
        'min_layer2': 0.17,
        'min_layer3': 0.12,
        'enabled': True,           # 🧪 ACTIVÉ POUR TEST
    },
    'OFF_HOURS_NQ': {
        'tp_ticks': 25,
        'sl_ticks': 20,
        'cooldown_min': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'min_confluence': 1,
        'max_distance': 6,         # 🔥 20/12: RÉDUIT 15→6 (analyse 18-19 déc)
        'min_level_score': 2,      # 🔥 20/12: Score ≥ 2 obligatoire
        'min_layer1': 0.20,
        'min_layer2': 0.17,
        'min_layer3': 0.12,
        'enabled': True,           # 🧪 ACTIVÉ POUR TEST
    },
}

# ===============================================================================
#                   NIVEAUX PREMIUM COMPLETS (MenthorQ)
# ===============================================================================

ALL_PREMIUM_LEVELS = [
    # FORT (Score 3)
    'gex_1', 'gex_2', 'hvl', 'gamma_wall_level', 'vwap',

    # MOYEN (Score 2)
    'gex_3', 'gex_4', 'gex_5', 'hvl_0dte',
    # call_resistance/put_support → Score 3 (voir LEVEL_SCORES)
    'blind_spot_1', 'blind_spot_2',
    'gamma_wall_0dte', 'vwap_up1', 'vwap_dn1',

    # FAIBLE (Score 1)
    # call_resistance_0dte/put_support_0dte → Score 2 (voir LEVEL_SCORES)
    'blind_spot_3', 'blind_spot_4',
    'vwap_up2', 'vwap_dn2',
]

# Classification des niveaux par score
LEVEL_SCORES = {
    # ═══════════════════════════════════════════════════════════════
    # 🔧 16/12/2025: SCORES COMPLETS - Tous les niveaux du snapshot
    # ═══════════════════════════════════════════════════════════════

    # FORT (score 3) - Niveaux institutionnels majeurs
    'gex_1': 3, 'gex_2': 3,
    'hvl': 3,
    'vwap': 3,
    'gamma_wall_level': 3,
    'vpoc': 3,              # Value Area POC
    # 🔥 18/12/2025: Call/Put Walls promus Score 3 (SpotGamma: "Holds 83%", "Breached 8%")
    'call_resistance': 3, 'put_support': 3,
    '1d_max': 3,            # Daily High
    '1d_min': 3,            # Daily Low

    # MOYEN (score 2) - Niveaux importants secondaires
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2,
    'hvl_0dte': 2,
    'gamma_wall_0dte': 2,
    # 🔥 18/12/2025: 0DTE Walls promus Score 2 (étaient Score 1, trop bas pour leur impact)
    'call_resistance_0dte': 2, 'put_support_0dte': 2,
    'blind_spot_0': 2, 'blind_spot_1': 2, 'blind_spot_2': 2,  # Snapshot: 0-8
    'vwap_up1': 2, 'vwap_dn1': 2,
    'vah': 2, 'val': 2,     # Value Area High/Low
    'ibh': 2, 'ibl': 2,     # Initial Balance

    # FAIBLE (score 1) - Niveaux mineurs
    'gex_6': 1, 'gex_7': 1, 'gex_8': 1, 'gex_9': 1, 'gex_10': 1,
    # call_resistance_0dte/put_support_0dte promus en Score 2
    'blind_spot_3': 1, 'blind_spot_4': 1, 'blind_spot_5': 1,
    'blind_spot_6': 1, 'blind_spot_7': 1, 'blind_spot_8': 1,
    'vwap_up2': 1, 'vwap_dn2': 1,
}

# Config par défaut (utilisée hors sessions ou si session désactivée)
DEFAULT_SESSION_CONFIG = {
    'tp_ticks': 12,
    'sl_ticks': 12,
    'cooldown_min': 15,
    'min_confidence': 0.50,
    'min_layer2': 0.17,        # 🔥 V10.3: Augmenté de 0.15 → 0.17
    'mia_threshold': 0.20,
    'max_distance': 10,
    'min_confluence': 1,
    'min_level_score': 1,
    'enabled': True,
}


def get_session_config(session: str, symbol: str) -> dict:
    """
    Retourne la config optimale pour une session et un symbole.

    Args:
        session: 'LONDON', 'US_MORNING', 'POWER_HOUR' ou 'OFF_HOURS'
        symbol: 'ES', 'NQ', 'RTY'

    Returns:
        dict avec tp_ticks, sl_ticks, cooldown_min, min_confidence, etc.
        Retourne DEFAULT si session désactivée ou non trouvée.
    """
    key = f"{session}_{symbol}"
    config = OPTIMAL_SESSION_CONFIGS.get(key, DEFAULT_SESSION_CONFIG)

    # Si la config est désactivée, retourner la config par défaut
    if not config.get('enabled', True):
        return DEFAULT_SESSION_CONFIG

    return config


def is_session_enabled(session: str, symbol: str) -> bool:
    """
    Vérifie si une session/symbole est activée pour le trading.

    Returns:
        True si activée, False si désactivée (ex: LONDON_NQ)
    """
    key = f"{session}_{symbol}"
    config = OPTIMAL_SESSION_CONFIGS.get(key)
    if config is None:
        return False
    return config.get('enabled', True)


def get_level_score(level_name: str) -> int:
    """
    Retourne le score d'un niveau MenthorQ.

    Args:
        level_name: Nom du niveau (ex: 'gex_1', 'hvl', 'blind_spot_2')

    Returns:
        3 = FORT, 2 = MOYEN, 1 = FAIBLE, 0 = inconnu
    """
    # Gestion des niveaux avec suffixes (gex_6, blind_spot_5, etc.)
    base_name = level_name.lower()

    # Vérifier d'abord le nom exact
    if base_name in LEVEL_SCORES:
        return LEVEL_SCORES[base_name]

    # Pour les GEX > 5, score = 1 (faible)
    if base_name.startswith('gex_'):
        try:
            num = int(base_name.split('_')[1])
            if num <= 2:
                return 3  # FORT
            elif num <= 5:
                return 2  # MOYEN
            else:
                return 1  # FAIBLE
        except:
            return 1

    # Pour les blind_spots > 4, score = 1
    if base_name.startswith('blind_spot_'):
        try:
            num = int(base_name.split('_')[2])
            if num <= 1:
                return 2  # MOYEN
            else:
                return 1  # FAIBLE
        except:
            return 1

    return 0  # Inconnu


def validate_menthorq_level(
    level_name: str,
    level_price: float,
    entry_price: float,
    symbol: str,
    session: str,
    tick_size: float = 0.25
) -> tuple:
    """
    Valide si un niveau MenthorQ est acceptable selon les critères V9.

    Args:
        level_name: Nom du niveau (ex: 'gex_1')
        level_price: Prix du niveau
        entry_price: Prix d'entrée potentiel
        symbol: 'ES' ou 'NQ'
        session: 'LONDON', 'US_MORNING', 'POWER_HOUR'
        tick_size: Taille du tick (0.25 pour ES/NQ)

    Returns:
        (is_valid, reason, distance_ticks, level_score)
    """
    config = get_session_config(session, symbol)

    # Calculer la distance en ticks
    distance_ticks = abs(entry_price - level_price) / tick_size

    # Vérifier la distance max
    max_distance = config.get('max_distance', 10)
    if distance_ticks > max_distance:
        return (False, f"Distance {distance_ticks:.0f}t > max {max_distance}t", distance_ticks, 0)

    # Vérifier le score du niveau
    level_score = get_level_score(level_name)
    min_score = config.get('min_level_score', 0)

    if level_score < min_score:
        score_names = {0: 'any', 1: 'faible+', 2: 'moyen+', 3: 'FORT'}
        return (False, f"Score {level_score} < min {min_score} ({score_names.get(min_score, '?')})", distance_ticks, level_score)

    return (True, "OK", distance_ticks, level_score)


def get_current_session(hour: int, minute: int) -> str:
    """
    Détermine la session actuelle basée sur l'heure Paris.

    Args:
        hour: Heure (0-23) en heure Paris
        minute: Minute (0-59)

    Returns:
        'LONDON', 'US_MORNING', 'POWER_HOUR' ou 'OFF_HOURS'
    """
    time_val = hour * 60 + minute

    # London: 8h00 - 11h00
    if 8 * 60 <= time_val < 11 * 60:
        return 'LONDON'

    # US Morning: 15h50 - 17h00
    if 15 * 60 + 50 <= time_val < 17 * 60:
        return 'US_MORNING'

    # Power Hour: 20h00 - 21h25
    if 20 * 60 <= time_val < 21 * 60 + 25:
        return 'POWER_HOUR'

    return 'OFF_HOURS'


# ═══════════════════════════════════════════════════════════════════════════════
#                    V10.4 FILTRES - VALIDÉS PAR BACKTEST 18/12/2025
# ═══════════════════════════════════════════════════════════════════════════════

# 📐 FILTRE POSITION IN RANGE (Mean Reversion)
# - Bloque LONG si prix en haut du range (>70%)
# - Bloque SHORT si prix en bas du range (<30%)
# Impact backtest: +6.1% WinRate!
V10_4_POSITION_FILTER = {
    'enabled': True,
    'long_max_position': 70,   # Bloquer LONG si position > 70%
    'short_min_position': 30,  # Bloquer SHORT si position < 30%
}

# 📏 FILTRE DISTANCE BY SCORE (différencié par symbole)
# Plus le niveau est faible, plus on doit être proche
# ES = moins volatil → distances plus serrées
# NQ = 🔥 20/12/2025: Distances STRICTES suite analyse 18-19 déc
#      WR 60% à dist≤6t vs 36% à dist>6t
V10_4_MAX_DISTANCE_BY_SCORE = {
    'ES': {1: 6, 2: 10, 3: 15},    # ES: strict (volatilité basse)
    'NQ': {1: 6, 2: 6, 3: 10},     # 🔥 20/12: RÉDUIT! Analyse 18-19 déc: WR 60% à ≤6t
    'RTY': {1: 8, 2: 12, 3: 18},   # RTY: intermédiaire
}

# Fonction helper pour obtenir la distance max
def get_max_distance_for_score(symbol: str, level_score: int) -> int:
    """Retourne la distance max en ticks selon le symbole et le score du niveau."""
    symbol_distances = V10_4_MAX_DISTANCE_BY_SCORE.get(symbol, V10_4_MAX_DISTANCE_BY_SCORE['ES'])
    return symbol_distances.get(level_score, 15)


if __name__ == "__main__":
    print_config()
    print(f"\nGLOBAL_CONFIG:")
    for k, v in GLOBAL_CONFIG.items():
        print(f"  {k}: {v}")

    print(f"\n🏆 OPTIMAL_SESSION_CONFIGS:")
    for key, cfg in OPTIMAL_SESSION_CONFIGS.items():
        print(f"  {key}: TP={cfg['tp_ticks']}, SL={cfg['sl_ticks']}, Conf={cfg['min_confidence']}")
