"""
MIA_IA_SYSTEM - Configuration MenthorQ

Configuration centralisée pour l'intégration MenthorQ
- Réglages de collecte et fréquence
- Pondérations et seuils
- Règles d'exécution et risk management
- Adaptation dynamique VIX

Version: Configuration Finale
Performance: Optimisé pour production
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import time

# === CONFIGURATION GÉNÉRALE ===

@dataclass
class MenthorQGeneralConfig:
    """Configuration générale MenthorQ"""
    
    # Activation
    enabled: bool = True
    debug_mode: bool = False
    
    # Symboles supportés
    supported_symbols: List[str] = None
    
    # Graph source
    source_graph: int = 10
    
    # Study IDs
    gamma_study_id: int = 1
    blind_spots_study_id: int = 2
    swing_levels_study_id: int = 3
    
    def __post_init__(self):
        if self.supported_symbols is None:
            self.supported_symbols = ["ESZ5", "ESU25_FUT_CME", "NQZ5"]

# === CONFIGURATION DE COLLECTE ===

@dataclass
class MenthorQCollectionConfig:
    """Configuration de collecte MenthorQ"""
    
    # Fréquences de base
    default_update_interval_minutes: int = 30
    high_frequency_interval_minutes: int = 15
    low_frequency_interval_minutes: int = 60
    
    # Seuils VIX pour adaptation
    vix_high_threshold: float = 22.0
    vix_low_threshold: float = 15.0
    
    # Anti-spam et déduplication
    min_price_change_ticks: float = 1.0
    debounce_ticks: float = 2.0
    hysteresys_ticks: float = 1.0
    
    # Throttling par type
    gamma_min_gap_minutes: int = 5
    blind_spots_min_gap_minutes: int = 10
    swing_min_gap_minutes: int = 15
    max_writes_per_sg_per_15min: int = 1
    
    # Validation des données
    min_valid_price: float = 0.0
    max_valid_price: float = 100000.0
    stale_data_threshold_minutes: float = 5.0
    critical_data_threshold_minutes: float = 10.0

# === CONFIGURATION DES PONDÉRATIONS ===

@dataclass
class MenthorQWeightsConfig:
    """Configuration des pondérations MenthorQ"""
    
    # Pondérations principales
    battle_navale_weight: float = 0.6
    menthorq_weight: float = 0.4
    
    # Poids des niveaux MenthorQ
    gamma_weights: Dict[str, float] = None
    blind_spots_weight: float = 0.80
    swing_levels_weight: float = 0.75
    
    # Seuils de confluence
    confluence_threshold: float = 1.85
    high_confluence_threshold: float = 2.5
    
    def __post_init__(self):
        if self.gamma_weights is None:
            self.gamma_weights = {
                "Call Resistance": 0.95,
                "Put Support": 0.95,
                "HVL": 0.90,
                "1D Min": 0.85,
                "1D Max": 0.85,
                "Call Resistance 0DTE": 0.90,
                "Put Support 0DTE": 0.90,
                "HVL 0DTE": 0.85,
                "Gamma Wall 0DTE": 0.90,
                "GEX": 0.85  # Pour tous les GEX 1-10
            }

# === CONFIGURATION DES RÈGLES D'EXÉCUTION ===

@dataclass
class MenthorQExecutionConfig:
    """Configuration des règles d'exécution"""
    
    # Hard rules
    blind_spot_tolerance_ticks: float = 5.0
    gamma_level_tolerance_ticks: float = 3.0
    
    # Position sizing
    base_position_size: float = 1.0
    vix_multipliers: List[float] = None  # [VIX<15, 15≤VIX<22, VIX≥22]
    
    # Stops et Take Profits
    default_stop_ticks: int = 8
    default_tp1_ticks: int = 12
    default_tp2_ticks: int = 24
    default_trailing_ticks: int = 6
    
    # Multiplicateurs VIX pour stops
    vix_stop_multipliers: List[float] = None  # [VIX<15, 15≤VIX<22, VIX≥22]
    
    def __post_init__(self):
        if self.vix_multipliers is None:
            self.vix_multipliers = [1.0, 0.75, 0.5]
        if self.vix_stop_multipliers is None:
            self.vix_stop_multipliers = [1.0, 1.5, 2.0]

# === CONFIGURATION DE L'ADAPTATION VIX ===

@dataclass
class MenthorQVIXConfig:
    """Configuration de l'adaptation VIX"""
    
    # Périodes de haute volatilité
    high_volatility_periods: List[Tuple[time, time]] = None
    
    # Règles d'adaptation
    vix_adaptation_rules: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.high_volatility_periods is None:
            self.high_volatility_periods = [
                (time(15, 30), time(16, 30)),  # Open
                (time(21, 0), time(22, 0))     # Close
            ]
        
        if self.vix_adaptation_rules is None:
            self.vix_adaptation_rules = {
                "vix_high": {
                    "condition": "vix >= 22",
                    "update_interval": 15,
                    "position_multiplier": 0.5,
                    "stop_multiplier": 2.0
                },
                "vix_medium": {
                    "condition": "15 <= vix < 22",
                    "update_interval": 30,
                    "position_multiplier": 0.75,
                    "stop_multiplier": 1.5,
                    "high_vol_periods": 15
                },
                "vix_low": {
                    "condition": "vix < 15",
                    "update_interval": 60,
                    "position_multiplier": 1.0,
                    "stop_multiplier": 1.0,
                    "high_vol_periods": 15
                }
            }

# === CONFIGURATION DES NIVEAUX MENTHORQ ===

@dataclass
class MenthorQLevelsConfig:
    """Configuration des niveaux MenthorQ"""
    
    # Gamma Levels (Study ID 1)
    gamma_levels: Dict[int, str] = None
    
    # Blind Spots (Study ID 2)
    blind_spots: Dict[int, str] = None
    
    # Swing Levels (Study ID 3)
    swing_levels: Dict[int, str] = None
    
    def __post_init__(self):
        if self.gamma_levels is None:
            self.gamma_levels = {
                1: "Call Resistance",
                2: "Put Support",
                3: "HVL",
                4: "1D Min",
                5: "1D Max",
                6: "Call Resistance 0DTE",
                7: "Put Support 0DTE",
                8: "HVL 0DTE",
                9: "Gamma Wall 0DTE",
                10: "GEX 1",
                11: "GEX 2",
                12: "GEX 3",
                13: "GEX 4",
                14: "GEX 5",
                15: "GEX 6",
                16: "GEX 7",
                17: "GEX 8",
                18: "GEX 9",
                19: "GEX 10"
            }
        
        if self.blind_spots is None:
            self.blind_spots = {
                i: f"BL {i}" for i in range(1, 11)
            }
        
        if self.swing_levels is None:
            self.swing_levels = {
                i: f"SG{i}" for i in range(1, 10)
            }

# === CONFIGURATION DU MONITORING ===

@dataclass
class MenthorQMonitoringConfig:
    """Configuration du monitoring MenthorQ"""
    
    # Health checks
    health_check_interval_seconds: int = 30
    stale_threshold_minutes: float = 5.0
    critical_threshold_minutes: float = 10.0
    
    # Alertes
    alert_cooldown_minutes: int = 5
    max_alerts_history: int = 50
    
    # Logs synthétiques
    synthetic_log_interval_minutes: int = 15
    
    # Métriques
    metrics_history_size: int = 100
    processing_rate_threshold: float = 0.1  # par seconde
    error_rate_threshold: float = 0.1  # 10%

# === CONFIGURATION DU BACKTEST ===

@dataclass
class MenthorQBacktestConfig:
    """Configuration du backtest MenthorQ"""
    
    # Capital initial
    initial_capital: float = 100000.0
    
    # Coûts
    commission_per_trade: float = 2.0
    slippage_per_trade: float = 0.25  # 1 tick
    
    # Critères d'acceptation
    min_winrate_improvement: float = 0.02  # +2%
    min_profit_factor_improvement: float = 0.1  # +0.1
    max_drawdown_degradation: float = 0.05  # -5%
    min_bl_filter_reduction: float = 0.25  # -25% des chop trades
    
    # Modes de test
    backtest_modes: List[str] = None
    
    def __post_init__(self):
        if self.backtest_modes is None:
            self.backtest_modes = [
                "baseline",
                "menthorq_full",
                "menthorq_no_bl",
                "menthorq_no_gex",
                "menthorq_no_swing"
            ]

# === CONFIGURATION PRINCIPALE ===

@dataclass
class MenthorQConfig:
    """Configuration principale MenthorQ"""
    
    general: MenthorQGeneralConfig = None
    collection: MenthorQCollectionConfig = None
    weights: MenthorQWeightsConfig = None
    execution: MenthorQExecutionConfig = None
    vix: MenthorQVIXConfig = None
    levels: MenthorQLevelsConfig = None
    monitoring: MenthorQMonitoringConfig = None
    backtest: MenthorQBacktestConfig = None
    
    def __post_init__(self):
        if self.general is None:
            self.general = MenthorQGeneralConfig()
        if self.collection is None:
            self.collection = MenthorQCollectionConfig()
        if self.weights is None:
            self.weights = MenthorQWeightsConfig()
        if self.execution is None:
            self.execution = MenthorQExecutionConfig()
        if self.vix is None:
            self.vix = MenthorQVIXConfig()
        if self.levels is None:
            self.levels = MenthorQLevelsConfig()
        if self.monitoring is None:
            self.monitoring = MenthorQMonitoringConfig()
        if self.backtest is None:
            self.backtest = MenthorQBacktestConfig()

# === FONCTIONS UTILITAIRES ===

def get_menthorq_config() -> MenthorQConfig:
    """Retourne la configuration MenthorQ par défaut"""
    return MenthorQConfig()

def get_update_interval_for_vix(vix_level: float, config: MenthorQConfig) -> int:
    """
    Détermine l'intervalle de mise à jour selon le VIX
    
    Args:
        vix_level: Niveau VIX actuel
        config: Configuration MenthorQ
        
    Returns:
        Intervalle en minutes
    """
    if vix_level >= config.vix.vix_adaptation_rules["vix_high"]["update_interval"]:
        return config.vix.vix_adaptation_rules["vix_high"]["update_interval"]
    elif vix_level >= config.vix.vix_adaptation_rules["vix_medium"]["update_interval"]:
        return config.vix.vix_adaptation_rules["vix_medium"]["update_interval"]
    else:
        return config.vix.vix_adaptation_rules["vix_low"]["update_interval"]

def get_position_multiplier_for_vix(vix_level: float, config: MenthorQConfig) -> float:
    """
    Détermine le multiplicateur de position selon le VIX
    
    Args:
        vix_level: Niveau VIX actuel
        config: Configuration MenthorQ
        
    Returns:
        Multiplicateur de position
    """
    if vix_level >= config.vix.vix_adaptation_rules["vix_high"]["position_multiplier"]:
        return config.vix.vix_adaptation_rules["vix_high"]["position_multiplier"]
    elif vix_level >= config.vix.vix_adaptation_rules["vix_medium"]["position_multiplier"]:
        return config.vix.vix_adaptation_rules["vix_medium"]["position_multiplier"]
    else:
        return config.vix.vix_adaptation_rules["vix_low"]["position_multiplier"]

def is_high_volatility_period(current_time: time, config: MenthorQConfig) -> bool:
    """
    Vérifie si on est dans une période de haute volatilité
    
    Args:
        current_time: Heure actuelle
        config: Configuration MenthorQ
        
    Returns:
        True si période de haute volatilité
    """
    for start_time, end_time in config.vix.high_volatility_periods:
        if start_time <= current_time <= end_time:
            return True
    return False

def get_menthorq_weight(level_name: str, config: MenthorQConfig) -> float:
    """
    Retourne le poids d'un niveau MenthorQ
    
    Args:
        level_name: Nom du niveau
        config: Configuration MenthorQ
        
    Returns:
        Poids du niveau
    """
    # Vérifier les niveaux Gamma
    for name, weight in config.weights.gamma_weights.items():
        if level_name.startswith(name):
            return weight
    
    # Vérifier les GEX
    if level_name.startswith("GEX"):
        return config.weights.gamma_weights["GEX"]
    
    # Vérifier les Blind Spots
    if level_name.startswith("BL"):
        return config.weights.blind_spots_weight
    
    # Vérifier les Swing Levels
    if level_name.startswith("SG"):
        return config.weights.swing_levels_weight
    
    # Poids par défaut
    return 0.75

def validate_menthorq_config(config: MenthorQConfig) -> List[str]:
    """
    Valide la configuration MenthorQ
    
    Args:
        config: Configuration à valider
        
    Returns:
        List des erreurs de validation
    """
    errors = []
    
    # Vérifier les pondérations
    if config.weights.battle_navale_weight + config.weights.menthorq_weight != 1.0:
        errors.append("La somme des pondérations Battle Navale + MenthorQ doit être égale à 1.0")
    
    # Vérifier les seuils VIX
    if config.vix.vix_high_threshold <= config.vix.vix_low_threshold:
        errors.append("Le seuil VIX haut doit être supérieur au seuil VIX bas")
    
    # Vérifier les intervalles
    if config.collection.high_frequency_interval_minutes >= config.collection.default_update_interval_minutes:
        errors.append("L'intervalle haute fréquence doit être inférieur à l'intervalle par défaut")
    
    # Vérifier les multiplicateurs VIX
    if len(config.execution.vix_multipliers) != 3:
        errors.append("Il doit y avoir exactement 3 multiplicateurs VIX")
    
    return errors

# === CONFIGURATION PAR DÉFAUT ===

# Configuration par défaut pour production
DEFAULT_MENTHORQ_CONFIG = MenthorQConfig()

# Configuration pour développement/test
DEV_MENTHORQ_CONFIG = MenthorQConfig(
    general=MenthorQGeneralConfig(
        enabled=True,
        debug_mode=True
    ),
    collection=MenthorQCollectionConfig(
        default_update_interval_minutes=15,  # Plus fréquent pour les tests
        stale_data_threshold_minutes=2.0
    ),
    monitoring=MenthorQMonitoringConfig(
        health_check_interval_seconds=10,  # Plus fréquent pour les tests
        synthetic_log_interval_minutes=5
    )
)

# Configuration pour backtest
BACKTEST_MENTHORQ_CONFIG = MenthorQConfig(
    general=MenthorQGeneralConfig(
        enabled=True,
        debug_mode=False
    ),
    collection=MenthorQCollectionConfig(
        default_update_interval_minutes=60,  # Moins fréquent pour backtest
        stale_data_threshold_minutes=10.0
    ),
    backtest=MenthorQBacktestConfig(
        initial_capital=50000.0,  # Capital réduit pour backtest
        commission_per_trade=1.0
    )
)

# === EXPORT DES CONFIGURATIONS ===

__all__ = [
    'MenthorQConfig',
    'MenthorQGeneralConfig',
    'MenthorQCollectionConfig',
    'MenthorQWeightsConfig',
    'MenthorQExecutionConfig',
    'MenthorQVIXConfig',
    'MenthorQLevelsConfig',
    'MenthorQMonitoringConfig',
    'MenthorQBacktestConfig',
    'get_menthorq_config',
    'get_update_interval_for_vix',
    'get_position_multiplier_for_vix',
    'is_high_volatility_period',
    'get_menthorq_weight',
    'validate_menthorq_config',
    'DEFAULT_MENTHORQ_CONFIG',
    'DEV_MENTHORQ_CONFIG',
    'BACKTEST_MENTHORQ_CONFIG'
]

# === EXEMPLE D'UTILISATION ===

if __name__ == "__main__":
    # Charger la configuration par défaut
    config = get_menthorq_config()
    
    # Valider la configuration
    errors = validate_menthorq_config(config)
    if errors:
        print("Erreurs de configuration:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration MenthorQ valide ✅")
    
    # Exemples d'utilisation
    vix_level = 18.5
    update_interval = get_update_interval_for_vix(vix_level, config)
    position_multiplier = get_position_multiplier_for_vix(vix_level, config)
    
    print(f"VIX: {vix_level}")
    print(f"Intervalle de mise à jour: {update_interval} minutes")
    print(f"Multiplicateur de position: {position_multiplier}")
    
    # Vérifier période de haute volatilité
    from datetime import datetime
    current_time = datetime.now().time()
    is_high_vol = is_high_volatility_period(current_time, config)
    print(f"Période de haute volatilité: {is_high_vol}")
    
    # Obtenir le poids d'un niveau
    weight = get_menthorq_weight("Call Resistance", config)
    print(f"Poids Call Resistance: {weight}")
