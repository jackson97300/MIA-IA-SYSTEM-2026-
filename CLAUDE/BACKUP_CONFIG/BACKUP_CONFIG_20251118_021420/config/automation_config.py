#!/usr/bin/env python3
"""
🔧 CONFIGURATION AUTOMATION CENTRALISÉE - MIA_IA_SYSTEM
=======================================================

Gestion centralisée de toutes les configurations du système automation:
- Trading parameters
- Risk management settings  
- ML ensemble configuration
- IBKR connection settings
- Performance monitoring
- Confluence formula parameters

Author: MIA_IA_SYSTEM
Version: 3.0.0
Date: Juillet 2025
"""

import os
import random
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

# Types d'environnement
class Environment(Enum):
    DEVELOPMENT = "development"
    PAPER_TRADING = "paper_trading"
    STAGING = "staging"
    PRODUCTION = "production"

class AutomationMode(Enum):
    PAPER_TRADING = "paper_trading"
    DATA_COLLECTION = "data_collection"
    LIVE_TRADING = "live_trading"
    BACKTESTING = "backtesting"

@dataclass
class TradingConfig:
    """Configuration paramètres trading"""
    
    # Position management
    max_position_size: int = 2
    max_positions_concurrent: int = 2
    position_risk_percent: float = 1.0  # % account per trade
    max_daily_trades: int = 20
    
    # Signal filtering
    min_signal_confidence: float = 0.70
    battle_navale_min_confidence: float = 0.65
    confluence_min_threshold: float = 0.25
    
    # Risk management
    stop_loss_ticks: int = 8  # 2 points ES (8 * 0.25)
    take_profit_ratio: float = 2.0  # 2:1 RR
    daily_loss_limit: float = 500.0
    daily_profit_target: float = 1000.0
    
    # Time filters
    trading_start_hour: int = 9
    trading_end_hour: int = 16
    avoid_news_minutes: int = 30
    
    # Instruments
    primary_instrument: str = "ES"
    tick_size: float = 0.25
    tick_value: float = 12.50
    minimum_tick_move: int = 1

@dataclass  
class MLConfig:
    """Configuration ML ensemble"""
    
    # Ensemble settings
    ensemble_enabled: bool = True
    min_ensemble_confidence: float = 0.65
    ensemble_models: List[str] = field(default_factory=lambda: [
        "random_forest", "gradient_boost", "neural_net"
    ])
    
    # Model training
    retrain_frequency_hours: int = 24
    min_training_samples: int = 1000
    validation_split: float = 0.2
    
    # Feature engineering
    feature_windows: List[int] = field(default_factory=lambda: [5, 15, 30, 60])
    feature_normalization: bool = True
    feature_selection_enabled: bool = True
    
    # Performance thresholds
    min_model_accuracy: float = 0.58
    max_model_age_hours: int = 48

@dataclass
class ConfluenceConfig:
    """Configuration nouvelle formule confluence"""
    
    # Seuils dynamiques
    base_threshold: float = 0.25
    adaptive_thresholds: bool = True
    volatility_adjustment: bool = True
    session_adjustment: bool = True
    
    # Pondérations features de base (60%)
    gamma_levels_weight: float = 0.20
    volume_confirmation_weight: float = 0.15
    options_flow_weight: float = 0.12
    order_book_imbalance_weight: float = 0.13
    
    # Pondérations features avancées (25%)
    tick_momentum_weight: float = 0.08
    delta_divergence_weight: float = 0.08
    smart_money_index_weight: float = 0.09
    
    # Multi-timeframe (15%)
    mtf_confluence_weight: float = 0.15
    mtf_timeframes: List[str] = field(default_factory=lambda: ["1m", "5m", "15m"])
    
    # Adjustements contextuels
    session_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "asia": 0.9,
        "london": 1.1,
        "ny_open": 1.2,
        "ny_lunch": 0.8,
        "ny_close": 1.1,
        "after_hours": 0.7
    })
    
    volatility_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "low_vol": 0.8,
        "normal_vol": 1.0,
        "high_vol": 1.4,
        "extreme_vol": 1.8
    })

@dataclass
class IBKRConfig:
    """Configuration IBKR connection"""
    
    # Connection settings
    host: str = "127.0.0.1"
    port: int = 7497  # Paper trading par défaut
    client_id: int = 1
    timeout_seconds: int = 30
    
    # Account settings
    account_id: str = ""
    market_data_type: int = 3  # Delayed = 3, Live = 1
    
    # Order settings
    default_order_type: str = "MKT"
    use_adaptive_orders: bool = True
    smart_routing: bool = True
    
    # Connection management
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    reconnect_delay_seconds: int = 30

@dataclass
class MonitoringConfig:
    """Configuration monitoring et logging"""
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_rotation_mb: int = 10
    log_retention_days: int = 30
    
    # Performance monitoring
    performance_update_interval: int = 60  # seconds
    health_check_interval: int = 30  # seconds
    stats_save_interval: int = 300  # 5 minutes
    
    # Alerting
    alert_on_system_error: bool = True
    alert_on_poor_performance: bool = True
    alert_win_rate_threshold: float = 45.0  # Alert si < 45%
    alert_drawdown_threshold: float = 300.0  # Alert si > $300
    
    # Metrics collection
    detailed_logging: bool = True
    track_execution_latency: bool = True
    save_market_data: bool = True

@dataclass
class AutomationConfig:
    """Configuration principale automation"""
    
    # Environment
    environment: Environment = Environment.PAPER_TRADING
    automation_mode: AutomationMode = AutomationMode.PAPER_TRADING
    config_version: str = "3.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    
    # Sub-configurations
    trading: TradingConfig = field(default_factory=TradingConfig)
    ml: MLConfig = field(default_factory=MLConfig)
    confluence: ConfluenceConfig = field(default_factory=ConfluenceConfig)
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Global settings
    debug_mode: bool = False
    simulation_mode: bool = True  # True pour tests
    enable_safety_checks: bool = True
    
    def __post_init__(self):
        """Post-initialization adjustments"""
        # Ajustements par environnement
        if self.environment == Environment.PRODUCTION:
            self.ibkr.port = 7496  # Live trading
            self.ibkr.market_data_type = 1  # Live data
            self.simulation_mode = False
            self.trading.daily_loss_limit = 200.0  # Plus conservateur
            
        elif self.environment == Environment.STAGING:
            self.ibkr.port = 7497  # Paper trading
            self.trading.max_position_size = 1
            
        # Validation automatique
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validation configuration"""
        
        # Trading validations
        assert self.trading.max_position_size > 0, "Position size must be > 0"
        assert self.trading.daily_loss_limit > 0, "Daily loss limit must be > 0"
        assert 0 < self.trading.min_signal_confidence < 1, "Signal confidence must be 0-1"
        assert self.trading.stop_loss_ticks > 0, "Stop loss ticks must be > 0"
        
        # ML validations
        if self.ml.ensemble_enabled:
            assert len(self.ml.ensemble_models) > 0, "Need at least 1 ML model"
            assert 0 < self.ml.min_ensemble_confidence < 1, "ML confidence must be 0-1"
        
        # IBKR validations
        assert self.ibkr.port in [7496, 7497], "IBKR port must be 7496 (live) or 7497 (paper)"
        assert self.ibkr.client_id > 0, "Client ID must be > 0"
        
        # Confluence validations
        total_base_weight = (
            self.confluence.gamma_levels_weight +
            self.confluence.volume_confirmation_weight +
            self.confluence.options_flow_weight +
            self.confluence.order_book_imbalance_weight
        )
        assert abs(total_base_weight - 0.60) < 0.01, f"Base weights must sum to 0.60, got {total_base_weight}"


# Factory functions pour configurations prédéfinies

def create_paper_trading_config() -> AutomationConfig:
    """Configuration paper trading conservative"""
    
    config = AutomationConfig(
        environment=Environment.PAPER_TRADING,
        automation_mode=AutomationMode.PAPER_TRADING
    )
    
    # Settings conservateurs
    config.trading.max_position_size = 1
    config.trading.min_signal_confidence = 0.75
    config.trading.daily_loss_limit = 200.0
    config.trading.stop_loss_ticks = 10  # Plus conservateur
    
    # IBKR paper
    config.ibkr.port = 7497
    config.ibkr.market_data_type = 3
    
    # Monitoring renforcé
    config.monitoring.detailed_logging = True
    config.monitoring.health_check_interval = 15
    
    return config

def create_data_collection_config() -> AutomationConfig:
    """Configuration pour collection de données"""
    
    config = AutomationConfig(
        environment=Environment.DEVELOPMENT,
        automation_mode=AutomationMode.DATA_COLLECTION
    )
    
    # Focus sur collection données
    config.trading.max_position_size = 0  # Pas de trading
    config.ml.ensemble_enabled = False  # Pas de ML
    
    # Monitoring data
    config.monitoring.save_market_data = True
    config.monitoring.performance_update_interval = 30
    
    return config

def create_staging_config() -> AutomationConfig:
    """Configuration staging pour tests"""
    
    config = AutomationConfig(
        environment=Environment.STAGING,
        automation_mode=AutomationMode.PAPER_TRADING
    )
    
    # Settings réalistes mais sécurisés
    config.trading.max_position_size = 2
    config.trading.min_signal_confidence = 0.70
    config.trading.daily_loss_limit = 300.0
    
    # ML activé pour tests
    config.ml.ensemble_enabled = True
    config.ml.min_ensemble_confidence = 0.65
    
    return config

def create_production_config() -> AutomationConfig:
    """Configuration production live trading"""
    
    config = AutomationConfig(
        environment=Environment.PRODUCTION,
        automation_mode=AutomationMode.LIVE_TRADING
    )
    
    # Settings production optimisés
    config.trading.max_position_size = 3
    config.trading.min_signal_confidence = 0.70
    config.trading.daily_loss_limit = 500.0
    config.trading.take_profit_ratio = 2.0
    
    # ML complet
    config.ml.ensemble_enabled = True
    config.ml.min_ensemble_confidence = 0.70
    
    # IBKR live
    config.ibkr.port = 7496
    config.ibkr.market_data_type = 1
    
    # Monitoring production
    config.monitoring.alert_on_system_error = True
    config.monitoring.alert_on_poor_performance = True
    
    return config

def create_conservative_config() -> AutomationConfig:
    """Configuration ultra-conservative pour déploiement initial"""
    
    config = create_production_config()
    
    # Ultra conservateur
    config.trading.max_position_size = 1
    config.trading.min_signal_confidence = 0.80
    config.trading.daily_loss_limit = 150.0
    config.trading.stop_loss_ticks = 6  # Plus serré
    
    # ML très strict
    config.ml.min_ensemble_confidence = 0.75
    
    # Confluence strict
    config.confluence.base_threshold = 0.35
    
    return config


# 🔧 AJOUT : Fonctions manquantes pour résoudre les erreurs d'import

def get_automation_config() -> Dict[str, Any]:
    """Configuration automation par défaut - FONCTION MANQUANTE AJOUTÉE"""
    return {
        'max_position_size': 2,
        'daily_loss_limit': 500.0,
        'min_confidence': 0.35,
        'enable_ml_ensemble': True,
        'enable_gamma_cycles': True,
        'confluence_threshold': 0.25,
        'automation_mode': 'paper_trading',
        'trading_hours': {
            'start': 9,
            'end': 16
        },
        'risk_management': {
            'stop_loss_ticks': 8,
            'take_profit_ratio': 2.0
        }
    }

def get_feature_config() -> Dict[str, Any]:
    """Configuration features par défaut - FONCTION MANQUANTE AJOUTÉE"""
    return {
        'features_enabled': [
            'gamma_levels_proximity',
            'volume_confirmation', 
            'options_flow_bias',
            'order_book_imbalance',
            'tick_momentum',
            'delta_divergence',
            'smart_money_index',
            'mtf_confluence'
        ],
        'feature_weights': {
            'gamma_levels_weight': 0.20,
            'volume_confirmation_weight': 0.15,
            'options_flow_weight': 0.12,
            'order_book_imbalance_weight': 0.13,
            'tick_momentum_weight': 0.08,
            'delta_divergence_weight': 0.08,
            'smart_money_index_weight': 0.09,
            'mtf_confluence_weight': 0.15
        },
        'confluence_config': {
            'base_threshold': 0.25,
            'adaptive_thresholds': True,
            'volatility_adjustment': True,
            'session_adjustment': True
        }
    }


# Gestion fichiers configuration

class ConfigManager:
    """Gestionnaire configurations avec sauvegarde/chargement"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
    def save_config(self, config: AutomationConfig, name: str) -> None:
        """Sauvegarde configuration"""
        config_file = self.config_dir / f"{name}.json"
        
        # Conversion en dict
        config_dict = asdict(config)
        
        # Serialization datetime
        if 'created_at' in config_dict:
            config_dict['created_at'] = config_dict['created_at'].isoformat()
        
        # Sauvegarde
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        print(f"✅ Configuration sauvée: {config_file}")
    
    def load_config(self, name: str) -> AutomationConfig:
        """Chargement configuration"""
        config_file = self.config_dir / f"{name}.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration non trouvée: {config_file}")
        
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        
        # Reconstruction datetime
        if 'created_at' in config_dict:
            config_dict['created_at'] = datetime.fromisoformat(config_dict['created_at'])
        
        # Reconstruction objets
        return self._dict_to_config(config_dict)
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> AutomationConfig:
        """Conversion dict vers AutomationConfig"""
        
        # Reconstruction des sous-configs
        trading_config = TradingConfig(**config_dict.get('trading', {}))
        ml_config = MLConfig(**config_dict.get('ml', {}))
        confluence_config = ConfluenceConfig(**config_dict.get('confluence', {}))
        ibkr_config = IBKRConfig(**config_dict.get('ibkr', {}))
        monitoring_config = MonitoringConfig(**config_dict.get('monitoring', {}))
        
        # Config principale
        main_config = {k: v for k, v in config_dict.items() 
                      if k not in ['trading', 'ml', 'confluence', 'ibkr', 'monitoring']}
        
        return AutomationConfig(
            trading=trading_config,
            ml=ml_config,
            confluence=confluence_config,
            ibkr=ibkr_config,
            monitoring=monitoring_config,
            **main_config
        )
    
    def list_configs(self) -> List[str]:
        """Liste configurations disponibles"""
        return [f.stem for f in self.config_dir.glob("*.json")]


# Fonctions utilitaires

def get_environment_config() -> AutomationConfig:
    """Configuration basée sur variable environnement"""
    
    env = os.getenv('MIA_ENVIRONMENT', 'paper_trading').lower()
    
    if env == 'production':
        return create_production_config()
    elif env == 'staging':
        return create_staging_config()
    elif env == 'data_collection':
        return create_data_collection_config()
    elif env == 'conservative':
        return create_conservative_config()
    else:
        return create_paper_trading_config()

def validate_all_configs() -> Dict[str, bool]:
    """Validation toutes configurations prédéfinies"""
    
    results = {}
    
    try:
        configs = {
            'paper_trading': create_paper_trading_config(),
            'data_collection': create_data_collection_config(),
            'staging': create_staging_config(),
            'production': create_production_config(),
            'conservative': create_conservative_config()
        }
        
        for name, config in configs.items():
            try:
                config._validate_config()
                results[name] = True
            except Exception as e:
                print(f"❌ {name}: {e}")
                results[name] = False
                
    except Exception as e:
        print(f"❌ Erreur validation globale: {e}")
    
    return results

def get_config_summary(config: Optional[AutomationConfig] = None) -> Dict[str, Any]:
    """Résumé configuration"""
    
    if config is None:
        config = get_environment_config()
    
    return {
        'environment': config.environment.value,
        'automation_mode': config.automation_mode.value,
        'max_positions': config.trading.max_position_size,
        'daily_loss_limit': config.trading.daily_loss_limit,
        'min_confidence': config.trading.min_signal_confidence,
        'ml_enabled': config.ml.ensemble_enabled,
        'ibkr_port': config.ibkr.port,
        'simulation_mode': config.simulation_mode,
        'confluence_threshold': config.confluence.base_threshold
    }


# Test et démonstration
if __name__ == "__main__":
    print("🔧 === CONFIGURATION AUTOMATION SYSTEM ===")
    
    # Test toutes configurations
    print("\n📋 Validation configurations...")
    validation_results = validate_all_configs()
    
    for name, valid in validation_results.items():
        status = "✅" if valid else "❌"
        print(f"{status} {name}: {'OK' if valid else 'ERREUR'}")
    
    print(f"\n📊 Score validation: {sum(validation_results.values())}/{len(validation_results)}")
    
    # Exemple usage
    print("\n🎯 Exemple configurations:")
    
    configs = {
        'Paper Trading': create_paper_trading_config(),
        'Production': create_production_config(),
        'Conservative': create_conservative_config()
    }
    
    for name, config in configs.items():
        summary = get_config_summary(config)
        print(f"\n{name}:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
    
    # Test sauvegarde/chargement
    print("\n💾 Test sauvegarde/chargement...")
    try:
        manager = ConfigManager()
        
        # Sauvegarde
        test_config = create_paper_trading_config()
        manager.save_config(test_config, "test_config")
        
        # Chargement
        loaded_config = manager.load_config("test_config")
        print("✅ Sauvegarde/chargement OK")
        
        # Liste configs
        configs_list = manager.list_configs()
        print(f"📁 Configurations disponibles: {configs_list}")
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")
    
    print("\n🚀 Configuration système prête !")
    
    # 🔧 AJOUT : Test des nouvelles fonctions
    print("\n🔧 Test des fonctions ajoutées...")
    try:
        automation_config = get_automation_config()
        print(f"✅ get_automation_config(): {len(automation_config)} paramètres")
        
        feature_config = get_feature_config()
        print(f"✅ get_feature_config(): {len(feature_config['features_enabled'])} features")
        
        print("✅ Toutes les fonctions manquantes ajoutées avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur test nouvelles fonctions: {e}")