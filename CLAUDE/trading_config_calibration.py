"""
trading_config_calibration.py

CONFIGURATION MODE CALIBRAGE
Date: 18 Novembre 2025
Phase: Collecte de données de qualité
Durée: 30 jours minimum

OBJECTIF: Collecter 6000+ trades de qualité sur toutes les sessions
pour optimisation ultérieure du système.

IMPORTANT: Ne pas modifier cette config pendant les 30 jours!
"""

# ═══════════════════════════════════════════════════════
# SYMBOLES ET SESSIONS
# ═══════════════════════════════════════════════════════

# Symboles actifs
ACTIVE_SYMBOLS = ["ES", "NQ"]
# RTY ajouté après stabilisation ES/NQ

# Trading 24/7
TRADING_24H = True
TRADING_START_TIME = "00:00"
TRADING_END_TIME = "23:59"

# Définition des sessions (pour analytics)
SESSIONS = {
    "ASIA": {
        "start": "18:00",
        "end": "03:00",
        "target_trades_per_day": 40
    },
    "EUROPE": {
        "start": "03:00", 
        "end": "09:30",
        "target_trades_per_day": 30
    },
    "US": {
        "start": "09:30",
        "end": "16:00",
        "target_trades_per_day": 100
    },
    "AFTER": {
        "start": "16:00",
        "end": "18:00",
        "target_trades_per_day": 30
    }
}

# ═══════════════════════════════════════════════════════
# MODE CALIBRAGE - PAS DE LIMITES
# ═══════════════════════════════════════════════════════

# Pas de limites journalières
MAX_DAILY_LOSS = None  # Aucune limite
MAX_DAILY_PROFIT = None  # Aucune limite
MAX_CONSECUTIVE_LOSSES = None  # Pas d'arrêt automatique

# Mais kill switch manuel disponible
MANUAL_KILL_SWITCH_ENABLED = True
EMERGENCY_STOP_LOSS_MULTIPLIER = 10  # Seulement si problème technique grave

# Mode
CALIBRATION_MODE = True
CALIBRATION_TARGET_TRADES = 6000
CALIBRATION_START_DATE = "2025-11-18"
CALIBRATION_MIN_DAYS = 30

# ═══════════════════════════════════════════════════════
# PARAMÈTRES DE TRADING (AJUSTÉS POUR QUALITÉ)
# ═══════════════════════════════════════════════════════

# Stops et TP (légèrement élargis pour laisser respirer)
SYMBOL_PARAMS = {
    "NQ": {
        "stop_loss_ticks": 13,  # vs 10 en production
        "take_profit_ticks": 26,  # Ratio 1:2
        "trailing_stop_enabled": True,
        "trailing_stop_trigger_ticks": 12,
        "trailing_stop_distance_ticks": 6,
        "point_value": 20.0,
        "tick_size": 0.25,
        "max_spread_ticks": 2
    },
    "ES": {
        "stop_loss_ticks": 10,  # vs 8 en production
        "take_profit_ticks": 20,  # Ratio 1:2
        "trailing_stop_enabled": True,
        "trailing_stop_trigger_ticks": 8,
        "trailing_stop_distance_ticks": 4,
        "point_value": 50.0,
        "tick_size": 0.25,
        "max_spread_ticks": 2
    },
    "RTY": {  # Pour future utilisation
        "stop_loss_ticks": 12,
        "take_profit_ticks": 24,
        "trailing_stop_enabled": True,
        "trailing_stop_trigger_ticks": 10,
        "trailing_stop_distance_ticks": 5,
        "point_value": 50.0,
        "tick_size": 0.10,
        "max_spread_ticks": 3
    }
}

# ═══════════════════════════════════════════════════════
# SEUILS DE FILTRAGE (LÉGÈREMENT ASSOUPLIS)
# ═══════════════════════════════════════════════════════

# Confluence
MIN_CONFLUENCE_SCORE = 0.45  # vs 0.50 en production
CONFLUENCE_WEIGHT = 0.30

# MenthorQ
MIN_MENTHORQ_SCORE = 0.40  # vs 0.45 en production
MENTHORQ_WEIGHT = 0.25

# ML
ML_ENABLED = True
ML_MIN_CONFIDENCE = 0.52  # vs 0.55 en production
ML_WEIGHT = 0.25
ML_VETO_ENABLED = True  # ML peut rejeter un signal

# OrderFlow
MIN_ORDERFLOW_SCORE = 0.20  # Pas de filtrage strict
ORDERFLOW_WEIGHT = 0.10

# Context
MIN_CONTEXT_SCORE = 0.20  # Pas de filtrage strict
CONTEXT_WEIGHT = 0.10

# ═══════════════════════════════════════════════════════
# RISK MANAGEMENT
# ═══════════════════════════════════════════════════════

# Sizing
RISK_PER_TRADE_USD = 100  # Risk fixe par trade
POSITION_SIZING_METHOD = "risk_based"  # vs "fixed"

# Positions
MAX_POSITIONS_PER_SYMBOL = 1
MAX_TOTAL_POSITIONS = 2  # 1 ES + 1 NQ max simultanément

# Exposure
MAX_EXPOSURE_PERCENTAGE = 5.0  # 5% du compte max

# ═══════════════════════════════════════════════════════
# DATA COLLECTION (CRITIQUE!)
# ═══════════════════════════════════════════════════════

# Snapshots
SAVE_ENTRY_SNAPSHOT = True
SAVE_EXIT_SNAPSHOT = True
SAVE_REJECTED_SNAPSHOTS = True  # IMPORTANT!
SAVE_ML_PREDICTIONS = True
SAVE_ALL_SCORES = True

# Format
SNAPSHOT_FORMAT = "JSON"
SNAPSHOT_COMPRESSION = False  # Pas de compression pour faciliter analyse

# Fréquence
SNAPSHOT_FREQUENCY = "ON_EVENT"  # À chaque décision
BACKUP_FREQUENCY = "HOURLY"

# Chemins
CALIBRATION_DATA_PATH = "D:/MIA_IA_system/CALIBRAGE_PHASE"
TRADES_PATH = f"{CALIBRATION_DATA_PATH}/TRADES"
SNAPSHOTS_PATH = f"{CALIBRATION_DATA_PATH}/SNAPSHOTS"
ANALYTICS_PATH = f"{CALIBRATION_DATA_PATH}/ANALYTICS"

# ═══════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════

# Niveau de logging
LOG_LEVEL = "DEBUG"  # Maximum de détails

# Logs à activer
LOG_ALL_DECISIONS = True
LOG_ALL_SIGNALS = True
LOG_ALL_REJECTIONS = True
LOG_ALL_SCORES = True
LOG_ALL_FEATURES = True
LOG_ALL_ML_PREDICTIONS = True
LOG_MARKET_CONTEXT = True
LOG_PERFORMANCE_METRICS = True

# Rotation des logs
LOG_ROTATION = "DAILY"
LOG_MAX_SIZE_MB = 100
LOG_RETENTION_DAYS = 90  # Garder 3 mois de logs

# ═══════════════════════════════════════════════════════
# MONITORING & NOTIFICATIONS
# ═══════════════════════════════════════════════════════

# Discord
DISCORD_ENABLED = True
DISCORD_WEBHOOK_URL = "YOUR_WEBHOOK_URL"  # À remplir

# Notifications (ajustées pour calibrage)
DISCORD_NOTIFY_TRADE_OPEN = False  # Trop de spam
DISCORD_NOTIFY_TRADE_CLOSE = False  # Trop de spam
DISCORD_NOTIFY_HOURLY_SUMMARY = True  # Résumé horaire
DISCORD_NOTIFY_SESSION_SUMMARY = True  # Fin de chaque session
DISCORD_NOTIFY_DAILY_SUMMARY = True  # Fin de journée
DISCORD_NOTIFY_WEEKLY_SUMMARY = True  # Dimanche soir

# Alertes importantes
DISCORD_ALERT_LARGE_LOSS_USD = 500  # Trade individuel > $500 perte
DISCORD_ALERT_TECHNICAL_ISSUE = True
DISCORD_ALERT_DATA_QUALITY_ISSUE = True
DISCORD_ALERT_CONNECTION_LOST = True

# Format des résumés
DISCORD_SUMMARY_INCLUDE_CHARTS = False  # Texte seulement
DISCORD_SUMMARY_INCLUDE_TOP_TRADES = True
DISCORD_SUMMARY_INCLUDE_WORST_TRADES = True

# ═══════════════════════════════════════════════════════
# DATA QUALITY CHECKS
# ═══════════════════════════════════════════════════════

# Fraîcheur des données
CHECK_DATA_FRESHNESS = True
MAX_DATA_AGE_MS = 2000  # 2 secondes max
REJECT_STALE_DATA = True

# Complétude
CHECK_DATA_COMPLETENESS = True
REQUIRED_FEATURES = [
    "mid", "spread", "d_vwap", "atr", "vix",
    "confluence", "gamma_wall", "dom_features"
]

# Sanity checks
CHECK_SPREAD_BEFORE_ENTRY = True
CHECK_VOLUME_BEFORE_ENTRY = True
MIN_VOLUME_CONTRACTS = 50

# Connexion
CHECK_DTC_CONNECTION = True
RECONNECT_ON_DISCONNECT = True
MAX_RECONNECT_ATTEMPTS = 5

# ═══════════════════════════════════════════════════════
# STRATÉGIES ET ML
# ═══════════════════════════════════════════════════════

# Stratégies actives (garder toutes actives pour collecte)
ACTIVE_STRATEGIES = [
    "menthorq_3layer_strategy",
    "vwap_sd_options_confluence_strategy",
    "gamma_wall_rejection_strategy",
    # Ajouter autres stratégies si disponibles
]

# ML Models
ML_MODELS = [
    "ml_3layer_metier_rules",
    "lightgbm_predictor",
    # Autres modèles
]

# Ensemble
ML_ENSEMBLE_METHOD = "weighted_average"
ML_ENSEMBLE_WEIGHTS = "auto"  # Basé sur accuracy historique

# ═══════════════════════════════════════════════════════
# COMPTES DE TRADING
# ═══════════════════════════════════════════════════════

# Mode
TRADING_MODE = "PAPER"  # Ou "LIVE" selon setup

# Comptes Sierra Chart
ACCOUNTS = {
    "ES": "SIM1",
    "NQ": "SIM2",
    "RTY": "SIM3"
}

# ═══════════════════════════════════════════════════════
# ANALYTICS & REPORTING
# ═══════════════════════════════════════════════════════

# Calculs en temps réel
CALCULATE_MFE_MAE = True  # Maximum Favorable/Adverse Excursion
CALCULATE_EFFICIENCY = True
CALCULATE_POST_EXIT_PERFORMANCE = True  # Prix 5/15/30min après sortie

# Métriques par session
TRACK_SESSION_METRICS = True
TRACK_REGIME_METRICS = True
TRACK_STRATEGY_METRICS = True
TRACK_ML_METRICS = True

# Exports
EXPORT_DAILY_REPORT = True
EXPORT_WEEKLY_REPORT = True
EXPORT_FORMAT = "JSON"  # JSON + CSV disponibles

# ═══════════════════════════════════════════════════════
# CALIBRATION PROGRESS TRACKING
# ═══════════════════════════════════════════════════════

# Objectifs
CALIBRATION_OBJECTIVES = {
    "total_trades": 6000,
    "min_days": 30,
    "min_trades_per_session": {
        "ASIA": 1200,  # 40/jour × 30 jours
        "EUROPE": 900,  # 30/jour × 30 jours
        "US": 3000,  # 100/jour × 30 jours
        "AFTER": 900  # 30/jour × 30 jours
    },
    "min_trades_per_symbol": {
        "ES": 2400,  # 40% du total
        "NQ": 3600  # 60% du total
    },
    "min_trades_per_regime": {
        "trending": 1800,  # 30%
        "range": 1800,  # 30%
        "high_vol": 600  # 10%
    },
    "data_quality_threshold": 0.95  # 95% de snapshots complets
}

# Progress tracking
TRACK_CALIBRATION_PROGRESS = True
SAVE_PROGRESS_HOURLY = True
ALERT_ON_MILESTONE = True  # Alert quand 1000, 2000, etc. trades

# ═══════════════════════════════════════════════════════
# SÉCURITÉ & FAIL-SAFES
# ═══════════════════════════════════════════════════════

# Kill switches (problèmes techniques seulement)
EMERGENCY_STOP_ON_REPEATED_ERRORS = True
MAX_ERRORS_PER_HOUR = 100

EMERGENCY_STOP_ON_DATA_ISSUES = True
MAX_STALE_DATA_EVENTS_PER_HOUR = 50

EMERGENCY_STOP_ON_CONNECTION_LOSS = False  # Tentative de reconnexion
MAX_DISCONNECTION_MINUTES = 10  # Après 10min, stop

# Backups
AUTO_BACKUP_ENABLED = True
BACKUP_FREQUENCY_HOURS = 6
BACKUP_RETENTION_DAYS = 90

# ═══════════════════════════════════════════════════════
# CONFIGURATION VALIDATION
# ═══════════════════════════════════════════════════════

def validate_config():
    """Valide la configuration avant de démarrer"""
    
    errors = []
    warnings = []
    
    # Check symboles
    if not ACTIVE_SYMBOLS:
        errors.append("Aucun symbole actif!")
    
    # Check limites désactivées
    if MAX_DAILY_LOSS is not None:
        warnings.append("MAX_DAILY_LOSS activée - pas recommandé en calibrage")
    
    # Check logging
    if not LOG_ALL_DECISIONS:
        warnings.append("LOG_ALL_DECISIONS désactivé - données incomplètes")
    
    # Check snapshots
    if not SAVE_ENTRY_SNAPSHOT or not SAVE_EXIT_SNAPSHOT:
        errors.append("Snapshots entry/exit doivent être activés!")
    
    # Check data path
    import os
    if not os.path.exists(CALIBRATION_DATA_PATH):
        warnings.append(f"Path {CALIBRATION_DATA_PATH} n'existe pas - sera créé")
    
    return errors, warnings


if __name__ == "__main__":
    print("═" * 60)
    print(" CONFIGURATION MODE CALIBRAGE")
    print("═" * 60)
    print(f"Symboles: {', '.join(ACTIVE_SYMBOLS)}")
    print(f"Trading: 24/7")
    print(f"Objectif: {CALIBRATION_TARGET_TRADES} trades en {CALIBRATION_MIN_DAYS} jours")
    print(f"Data path: {CALIBRATION_DATA_PATH}")
    print("═" * 60)
    
    errors, warnings = validate_config()
    
    if errors:
        print("\n❌ ERREURS:")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print("\n⚠️  AVERTISSEMENTS:")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors:
        print("\n✅ Configuration valide!")
    else:
        print("\n❌ Configuration invalide - corriger les erreurs")
