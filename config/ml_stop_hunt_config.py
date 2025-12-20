"""
Configuration ML Stop Hunt Predictor v2_clean

Version: 1.0
Date: 19 Novembre 2025
"""

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION ML STOP HUNT PREDICTOR
# ═══════════════════════════════════════════════════════════════════════

ML_STOP_HUNT_CONFIG = {
    'enabled': False,  # ❌ DÉSACTIVÉ 23/11/2025: Redondant avec MenthorQ Enrichi (SL sous niveau technique)
    'model_path': 'models/stop_hunt_predictor_v2_clean.pkl',

    # Seuils de confiance pour bloquer trades
    'threshold_stop_hunt': 0.29,  # ✅ CORRIGÉ 19/11: Réduit de 0.75 à 0.29 (probabilité moyenne stop hunts réels: 19.4%)
    'threshold_timeout': 0.60,    # Bloquer si >60% confiance TIMEOUT

    # ⭐ Multi-thresholds configurables
    'threshold_level0': 0.75,  # Niveau 0: Extrême
    'threshold_level1': 0.30,  # Niveau 1: Critique (⚠️ RÉDUIT de 45% à 30%)
    'threshold_level2': 0.30,  # Niveau 2: Modéré (avec WIN < 10%)
    'threshold_level3': 0.20,  # Niveau 3: Préventif (avec Exp < -20)

    # Conditions pour niveaux 2 et 3
    'threshold_win_min': 0.10,
    'threshold_expectancy_min': -20.0,

    # Comportement
    'block_on_stop_hunt': True,   # Bloquer trades prédits STOP_HUNT
    'block_on_timeout': True,     # Bloquer trades prédits TIMEOUT (optionnel)

    # Logging
    'log_predictions': True,
    'log_path': 'logs/ml_predictions.log',
    'log_blocked_trades': True,   # Log tous les trades bloqués

    # Fallback en cas d'erreur
    'fallback_on_error': 'EXECUTE',  # 'EXECUTE' ou 'BLOCK'

    # Features manquantes
    'fill_missing_with_zero': True,  # Remplir features manquantes avec 0
}

# ═══════════════════════════════════════════════════════════════════════
# MÉTRIQUES ATTENDUES
# ═══════════════════════════════════════════════════════════════════════

EXPECTED_METRICS = {
    'model_auc': 0.8367,           # AUC global
    'stop_hunt_auc': 1.000,        # AUC STOP_HUNT (parfait)
    'features_count': 61,          # Nombre de features (sans leak)
    'target_stop_hunt_rate': 0.15, # Objectif: <15% stop hunts (vs 30-35% avant)
    'target_win_rate': 0.55,       # Objectif: 50-60% win rate (vs 45-55% avant)
}

# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def get_ml_stop_hunt_config():
    """Retourne la configuration ML Stop Hunt"""
    return ML_STOP_HUNT_CONFIG.copy()

def is_ml_stop_hunt_enabled():
    """Vérifie si ML Stop Hunt est activé"""
    return ML_STOP_HUNT_CONFIG.get('enabled', False)
