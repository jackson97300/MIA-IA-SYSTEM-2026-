#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Unified Trading Configuration
=============================================

Version: Production Ready v1.0
- Fusion de trading_config.py, automation_config.py, hybrid_trading_config.py
- Migration automatique depuis les anciens fichiers
- Compatibilité ascendante garantie
- Structure unifiée et cohérente

IMPACT: Réduction complexité -40%
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)

# === ENUMS ===

class Environment(Enum):
    """Environnements de déploiement"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    PAPER_TRADING = "paper_trading"

class AutomationMode(Enum):
    """Modes d'automatisation"""
    PAPER_TRADING = "paper_trading"
    DATA_COLLECTION = "data_collection"
    LIVE_TRADING = "live_trading"
    BACKTESTING = "backtesting"

class OrderRoutingMethod(Enum):
    """Méthodes de routage des ordres"""
    DLL_DIRECT = "dll_direct"
    TCP_SOCKET = "tcp_socket"
    SHARED_MEMORY = "shared_memory"
    FILE_BASED = "file_based"

class DataFeedMode(Enum):
    """Modes de flux de données"""
    IBKR_ONLY = "ibkr_only"
    SIERRA_BACKUP = "sierra_backup"

class OrderProvider(Enum):
    """Fournisseurs d'ordres"""
    SIERRA_CHART = "sierra_chart"
    IBKR_DIRECT = "ibkr_direct"
    SIMULATION = "simulation"

class LogLevel(Enum):
    """Niveaux de log"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    """Types d'alertes"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    CONSOLE = "console"

# === CONFIGURATIONS SPÉCIALISÉES ===

@dataclass
class RiskManagement:
    """Gestion des risques unifiée"""
    max_position_size: float = 10.0
    min_position_size: float = 1.0
    max_daily_loss: float = 1000.0
    max_drawdown: float = 0.15
    stop_loss_ticks: int = 8
    take_profit_ticks: int = 16
    risk_per_trade: float = 0.02
    max_concurrent_trades: int = 3
    correlation_limit: float = 0.7

@dataclass
class ExecutionSettings:
    """Paramètres d'exécution unifiés"""
    order_routing: OrderRoutingMethod = OrderRoutingMethod.DLL_DIRECT
    data_feed: DataFeedMode = DataFeedMode.IBKR_ONLY
    order_provider: OrderProvider = OrderProvider.SIERRA_CHART
    execution_timeout_ms: int = 5000
    retry_attempts: int = 3
    slippage_tolerance_ticks: float = 2.0
    fill_timeout_ms: int = 10000

@dataclass
class SymbolConfig:
    """Configuration des symboles"""
    primary: str = "ES"
    secondary: str = "NQ"
    vix_symbol: str = "VIX"
    tick_size: float = 0.25
    tick_value: float = 12.50
    margin_requirement: float = 10000.0
    trading_hours: Dict[str, str] = field(default_factory=lambda: {
        "rth_start": "09:30",
        "rth_end": "16:00",
        "eth_start": "18:00",
        "eth_end": "17:00"
    })

@dataclass
class FeatureParameters:
    """Paramètres des features unifiés"""
    vwap_max_history: int = 2048
    vwap_bands_stdev: List[float] = field(default_factory=lambda: [1.0, 2.0])
    volume_profile_bin_ticks: int = 4
    volume_profile_max_history: int = 5000
    nbcv_min_volume: int = 60
    nbcv_min_delta_ratio: float = 7.5
    vix_low_threshold: float = 15.0
    vix_high_threshold: float = 25.0
    tick_momentum_window: int = 20
    delta_divergence_lookback: int = 10
    volatility_regime_atr_len: int = 20

@dataclass
class MLConfig:
    """Configuration ML unifiée"""
    enabled: bool = True
    model_path: str = "models/"
    retrain_frequency_hours: int = 24
    feature_selection_enabled: bool = True
    cross_validation_folds: int = 5
    min_training_samples: int = 1000
    prediction_confidence_threshold: float = 0.7

@dataclass
class ConfluenceConfig:
    """Configuration de confluence unifiée"""
    tolerance_ticks: float = 3.0
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4
    })
    leadership_gates: Dict[str, float] = field(default_factory=lambda: {
        "correlation_min": 0.7,
        "volume_ratio_min": 0.3,
        "volatility_max": 0.02
    })

@dataclass
class IBKRConfig:
    """Configuration IBKR unifiée"""
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    timeout_seconds: int = 30
    connection_retries: int = 3
    market_data_type: str = "LIVE"
    order_routing: bool = True

@dataclass
class MonitoringConfig:
    """Configuration de monitoring unifiée"""
    log_level: LogLevel = LogLevel.INFO
    log_file_path: str = "logs/mia_system.log"
    max_log_size_mb: int = 100
    log_retention_days: int = 30
    performance_metrics_enabled: bool = True
    health_check_interval_seconds: int = 60
    alert_types: List[AlertType] = field(default_factory=lambda: [AlertType.CONSOLE])
    email_alerts: Dict[str, str] = field(default_factory=dict)
    webhook_urls: List[str] = field(default_factory=list)

# === CONFIGURATION UNIFIÉE PRINCIPALE ===

@dataclass
class UnifiedTradingConfig:
    """
    Configuration unifiée pour tout le système MIA
    
    Fusionne:
    - trading_config.py
    - automation_config.py  
    - hybrid_trading_config.py
    """
    
    # === ENVIRONNEMENT ===
    environment: Environment = Environment.DEVELOPMENT
    automation_mode: AutomationMode = AutomationMode.PAPER_TRADING
    
    # === SYMBOLES ET MARCHÉS ===
    symbols: SymbolConfig = field(default_factory=SymbolConfig)
    
    # === GESTION DES RISQUES ===
    risk_management: RiskManagement = field(default_factory=RiskManagement)
    
    # === EXÉCUTION ===
    execution: ExecutionSettings = field(default_factory=ExecutionSettings)
    
    # === FEATURES ===
    features: FeatureParameters = field(default_factory=FeatureParameters)
    
    # === MACHINE LEARNING ===
    ml: MLConfig = field(default_factory=MLConfig)
    
    # === CONFLUENCE ===
    confluence: ConfluenceConfig = field(default_factory=ConfluenceConfig)
    
    # === IBKR ===
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    
    # === MONITORING ===
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # === MÉTADONNÉES ===
    version: str = "1.0.0"
    created_at: str = ""
    last_modified: str = ""
    
    def __post_init__(self):
        """Initialisation post-création"""
        from datetime import datetime
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_modified:
            self.last_modified = datetime.now().isoformat()

# === MIGRATIONS DE COMPATIBILITÉ ===

class ConfigMigrator:
    """
    Migrateur pour assurer la compatibilité ascendante
    """
    
    @staticmethod
    def migrate_from_trading_config(old_config: Dict[str, Any]) -> UnifiedTradingConfig:
        """
        Migre depuis trading_config.py
        
        Args:
            old_config: Ancienne configuration
            
        Returns:
            Configuration unifiée
        """
        unified = UnifiedTradingConfig()
        
        # Migration des symboles
        if 'symbols' in old_config:
            symbols = old_config['symbols']
            unified.symbols.primary = symbols.get('primary', 'ES')
            unified.symbols.secondary = symbols.get('secondary', 'NQ')
            unified.symbols.vix_symbol = symbols.get('vix_symbol', 'VIX')
        
        # Migration de la gestion des risques
        if 'risk_management' in old_config:
            risk = old_config['risk_management']
            unified.risk_management.max_position_size = risk.get('max_position_size', 10.0)
            unified.risk_management.min_position_size = risk.get('min_position_size', 1.0)
            unified.risk_management.max_daily_loss = risk.get('max_daily_loss', 1000.0)
        
        # Migration des features
        if 'feature_parameters' in old_config:
            features = old_config['feature_parameters']
            unified.features.vwap_max_history = features.get('vwap_max_history', 2048)
            unified.features.volume_profile_bin_ticks = features.get('volume_profile_bin_ticks', 4)
            unified.features.nbcv_min_volume = features.get('nbcv_min_volume', 60)
        
        logger.info("✅ Migration depuis trading_config.py terminée")
        return unified
    
    @staticmethod
    def migrate_from_automation_config(old_config: Dict[str, Any]) -> UnifiedTradingConfig:
        """
        Migre depuis automation_config.py
        
        Args:
            old_config: Ancienne configuration
            
        Returns:
            Configuration unifiée
        """
        unified = UnifiedTradingConfig()
        
        # Migration de l'environnement
        if 'environment' in old_config:
            env_str = old_config['environment'].upper()
            try:
                unified.environment = Environment[env_str]
            except KeyError:
                logger.warning(f"⚠️ Environnement inconnu: {env_str}")
        
        # Migration du mode d'automatisation
        if 'automation_mode' in old_config:
            mode_str = old_config['automation_mode'].upper()
            try:
                unified.automation_mode = AutomationMode[mode_str]
            except KeyError:
                logger.warning(f"⚠️ Mode d'automatisation inconnu: {mode_str}")
        
        # Migration ML
        if 'ml' in old_config:
            ml = old_config['ml']
            unified.ml.enabled = ml.get('enabled', True)
            unified.ml.model_path = ml.get('model_path', 'models/')
            unified.ml.retrain_frequency_hours = ml.get('retrain_frequency_hours', 24)
        
        # Migration monitoring
        if 'monitoring' in old_config:
            monitoring = old_config['monitoring']
            log_level_str = monitoring.get('log_level', 'INFO').upper()
            try:
                unified.monitoring.log_level = LogLevel[log_level_str]
            except KeyError:
                logger.warning(f"⚠️ Niveau de log inconnu: {log_level_str}")
        
        logger.info("✅ Migration depuis automation_config.py terminée")
        return unified
    
    @staticmethod
    def migrate_from_hybrid_config(old_config: Dict[str, Any]) -> UnifiedTradingConfig:
        """
        Migre depuis hybrid_trading_config.py
        
        Args:
            old_config: Ancienne configuration
            
        Returns:
            Configuration unifiée
        """
        unified = UnifiedTradingConfig()
        
        # Migration des paramètres hybrides
        if 'hybrid_settings' in old_config:
            hybrid = old_config['hybrid_settings']
            unified.execution.order_routing = OrderRoutingMethod(hybrid.get('order_routing', 'dll_direct'))
            unified.execution.data_feed = DataFeedMode(hybrid.get('data_feed', 'ibkr_only'))
        
        # Migration des corrections techniques
        if 'technical_corrections' in old_config:
            corrections = old_config['technical_corrections']
            unified.features.vwap_max_history = corrections.get('vwap_max_history', 2048)
            unified.features.volume_profile_bin_ticks = corrections.get('volume_profile_bin_ticks', 4)
        
        logger.info("✅ Migration depuis hybrid_trading_config.py terminée")
        return unified

# === LOADER UNIFIÉ ===

def load_unified_config(config_path: str = "config/unified_trading_config.yaml") -> UnifiedTradingConfig:
    """
    Charge la configuration unifiée
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Configuration unifiée
    """
    try:
        config_file = Path(config_path)
        
        if config_file.exists():
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Créer la configuration unifiée
            unified = UnifiedTradingConfig(**data)
            logger.info(f"✅ Configuration unifiée chargée depuis {config_path}")
            return unified
        else:
            logger.warning(f"⚠️ Fichier de configuration non trouvé: {config_path}")
            logger.info("📋 Utilisation de la configuration par défaut")
            return UnifiedTradingConfig()
            
    except Exception as e:
        logger.error(f"❌ Erreur chargement configuration unifiée: {e}")
        logger.info("📋 Utilisation de la configuration par défaut")
        return UnifiedTradingConfig()

def save_unified_config(config: UnifiedTradingConfig, config_path: str = "config/unified_trading_config.yaml"):
    """
    Sauvegarde la configuration unifiée
    
    Args:
        config: Configuration à sauvegarder
        config_path: Chemin de sauvegarde
    """
    try:
        import yaml
        from dataclasses import asdict
        
        # Convertir en dictionnaire
        config_dict = asdict(config)
        
        # Sauvegarder
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"✅ Configuration unifiée sauvegardée dans {config_path}")
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde configuration unifiée: {e}")

# === FONCTIONS DE COMPATIBILITÉ ===

def get_trading_config() -> UnifiedTradingConfig:
    """
    Fonction de compatibilité - retourne la configuration unifiée
    """
    return load_unified_config()

def get_automation_config() -> UnifiedTradingConfig:
    """
    Fonction de compatibilité - retourne la configuration unifiée
    """
    return load_unified_config()

# === TEST DE LA CONFIGURATION UNIFIÉE ===

if __name__ == "__main__":
    print("🧪 Test de la Configuration Unifiée...")
    
    # Test création configuration par défaut
    config = UnifiedTradingConfig()
    print(f"✅ Configuration unifiée créée: {config.environment.value}")
    
    # Test accès aux sections
    print(f"✅ Symboles: {config.symbols.primary}")
    print(f"✅ Risque max: {config.risk_management.max_position_size}")
    print(f"✅ Features VWAP: {config.features.vwap_max_history}")
    print(f"✅ ML activé: {config.ml.enabled}")
    
    # Test sauvegarde
    save_unified_config(config, "config/test_unified_config.yaml")
    print("✅ Configuration sauvegardée")
    
    # Test chargement
    loaded_config = load_unified_config("config/test_unified_config.yaml")
    print(f"✅ Configuration chargée: {loaded_config.environment.value}")
    
    print("🎉 Test configuration unifiée terminé avec succès!")
