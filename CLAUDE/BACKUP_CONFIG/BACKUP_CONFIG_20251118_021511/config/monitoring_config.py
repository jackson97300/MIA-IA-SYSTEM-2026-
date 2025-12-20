#!/usr/bin/env python3
"""
MIA IA System - Monitoring Configuration
Version: 3.0.0
Date: 2025-01-27

Configuration centralisée pour le monitoring et la surveillance
du système de trading automatisé
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

class LogLevel(Enum):
    """Niveaux de log"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    """Types d'alertes"""
    TRADE_EXECUTION = "TRADE_EXECUTION"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    PERFORMANCE_ISSUE = "PERFORMANCE_ISSUE"
    DATA_QUALITY = "DATA_QUALITY"
    CONNECTION_LOST = "CONNECTION_LOST"
    RISK_THRESHOLD = "RISK_THRESHOLD"

@dataclass
class LoggingSettings:
    """Paramètres de logging"""
    # Niveaux
    CONSOLE_LEVEL: LogLevel = LogLevel.INFO
    FILE_LEVEL: LogLevel = LogLevel.DEBUG
    SYSTEM_LEVEL: LogLevel = LogLevel.WARNING
    
    # Fichiers
    MAIN_LOG_FILE: str = "logs/mia_system.log"
    TRADING_LOG_FILE: str = "logs/trading.log"
    ERROR_LOG_FILE: str = "logs/errors.log"
    PERFORMANCE_LOG_FILE: str = "logs/performance.log"
    
    # Rotation
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 5
    ROTATE_DAILY: bool = True
    
    # Format
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    
    # Performance
    BUFFER_SIZE: int = 8192
    FLUSH_INTERVAL: int = 5  # secondes

@dataclass
class AlertSettings:
    """Paramètres d'alertes"""
    # Types d'alertes activées
    ENABLE_TRADE_ALERTS: bool = True
    ENABLE_SYSTEM_ALERTS: bool = True
    ENABLE_PERFORMANCE_ALERTS: bool = True
    ENABLE_DATA_ALERTS: bool = True
    ENABLE_CONNECTION_ALERTS: bool = True
    ENABLE_RISK_ALERTS: bool = True
    
    # Seuils d'alertes
    TRADE_EXECUTION_THRESHOLD: int = 5  # Erreurs consécutives
    SYSTEM_ERROR_THRESHOLD: int = 3     # Erreurs consécutives
    PERFORMANCE_LATENCY_THRESHOLD: float = 1000.0  # ms
    DATA_QUALITY_THRESHOLD: float = 0.95  # 95% de qualité
    CONNECTION_TIMEOUT: int = 30  # secondes
    RISK_THRESHOLD: float = 0.8   # 80% du risque max
    
    # Cooldown entre alertes
    ALERT_COOLDOWN: int = 300  # 5 minutes
    
    # Destinations
    ENABLE_CONSOLE_ALERTS: bool = True
    ENABLE_FILE_ALERTS: bool = True
    ENABLE_EMAIL_ALERTS: bool = False
    ENABLE_SLACK_ALERTS: bool = False

@dataclass
class PerformanceMonitoring:
    """Monitoring des performances"""
    # Métriques système
    ENABLE_CPU_MONITORING: bool = True
    ENABLE_MEMORY_MONITORING: bool = True
    ENABLE_DISK_MONITORING: bool = True
    ENABLE_NETWORK_MONITORING: bool = True
    
    # Métriques trading
    ENABLE_LATENCY_MONITORING: bool = True
    ENABLE_THROUGHPUT_MONITORING: bool = True
    ENABLE_ERROR_RATE_MONITORING: bool = True
    ENABLE_SUCCESS_RATE_MONITORING: bool = True
    
    # Seuils de performance
    MAX_CPU_USAGE: float = 80.0  # %
    MAX_MEMORY_USAGE: float = 85.0  # %
    MAX_DISK_USAGE: float = 90.0  # %
    MAX_LATENCY: float = 1000.0  # ms
    MIN_THROUGHPUT: float = 100.0  # trades/min
    MAX_ERROR_RATE: float = 5.0  # %
    MIN_SUCCESS_RATE: float = 95.0  # %
    
    # Intervalle de collecte
    COLLECTION_INTERVAL: int = 60  # secondes
    RETENTION_PERIOD: int = 7 * 24 * 60 * 60  # 7 jours en secondes

@dataclass
class HealthCheckSettings:
    """Paramètres de health check"""
    # Composants à vérifier
    ENABLE_SIERRA_CHECK: bool = True
    ENABLE_IBKR_CHECK: bool = True
    ENABLE_DATA_FEED_CHECK: bool = True
    ENABLE_FEATURE_CALCULATOR_CHECK: bool = True
    ENABLE_CONFLUENCE_CHECK: bool = True
    ENABLE_ML_MODEL_CHECK: bool = True
    
    # Fréquence des vérifications
    HEALTH_CHECK_INTERVAL: int = 30  # secondes
    QUICK_CHECK_INTERVAL: int = 10   # secondes
    
    # Timeouts
    COMPONENT_TIMEOUT: int = 5  # secondes
    DATA_FEED_TIMEOUT: int = 10  # secondes
    
    # Seuils de santé
    MIN_HEALTH_SCORE: float = 0.8
    CRITICAL_HEALTH_SCORE: float = 0.5

@dataclass
class MetricsSettings:
    """Paramètres de métriques"""
    # Métriques de trading
    ENABLE_TRADE_METRICS: bool = True
    ENABLE_PNL_METRICS: bool = True
    ENABLE_RISK_METRICS: bool = True
    ENABLE_PERFORMANCE_METRICS: bool = True
    
    # Métriques de système
    ENABLE_SYSTEM_METRICS: bool = True
    ENABLE_RESOURCE_METRICS: bool = True
    ENABLE_NETWORK_METRICS: bool = True
    
    # Stockage des métriques
    METRICS_STORAGE_PATH: str = "metrics/"
    METRICS_RETENTION_DAYS: int = 30
    
    # Export des métriques
    ENABLE_CSV_EXPORT: bool = True
    ENABLE_JSON_EXPORT: bool = True
    EXPORT_INTERVAL: int = 3600  # 1 heure

@dataclass
class MonitoringConfig:
    """Configuration complète de monitoring"""
    logging: LoggingSettings
    alerts: AlertSettings
    performance: PerformanceMonitoring
    health_check: HealthCheckSettings
    metrics: MetricsSettings
    
    def __post_init__(self):
        """Validation post-initialisation"""
        # Validation des seuils
        assert 0.0 <= self.performance.MAX_CPU_USAGE <= 100.0
        assert 0.0 <= self.performance.MAX_MEMORY_USAGE <= 100.0
        assert 0.0 <= self.performance.MAX_DISK_USAGE <= 100.0
        assert 0.0 <= self.performance.MAX_ERROR_RATE <= 100.0
        assert 0.0 <= self.performance.MIN_SUCCESS_RATE <= 100.0
        
        # Validation des intervalles
        assert self.performance.COLLECTION_INTERVAL > 0
        assert self.health_check.HEALTH_CHECK_INTERVAL > 0
        assert self.metrics.EXPORT_INTERVAL > 0

# Configuration par défaut
DEFAULT_MONITORING_CONFIG = MonitoringConfig(
    logging=LoggingSettings(),
    alerts=AlertSettings(),
    performance=PerformanceMonitoring(),
    health_check=HealthCheckSettings(),
    metrics=MetricsSettings()
)

# Configuration optimisée pour la production
PRODUCTION_MONITORING_CONFIG = MonitoringConfig(
    logging=LoggingSettings(
        CONSOLE_LEVEL=LogLevel.WARNING,
        FILE_LEVEL=LogLevel.INFO,
        SYSTEM_LEVEL=LogLevel.ERROR,
        MAX_FILE_SIZE=20 * 1024 * 1024,  # 20MB
        BACKUP_COUNT=10,
        ROTATE_DAILY=True
    ),
    alerts=AlertSettings(
        ENABLE_TRADE_ALERTS=True,
        ENABLE_SYSTEM_ALERTS=True,
        ENABLE_PERFORMANCE_ALERTS=True,
        ENABLE_DATA_ALERTS=True,
        ENABLE_CONNECTION_ALERTS=True,
        ENABLE_RISK_ALERTS=True,
        TRADE_EXECUTION_THRESHOLD=3,
        SYSTEM_ERROR_THRESHOLD=2,
        PERFORMANCE_LATENCY_THRESHOLD=500.0,
        DATA_QUALITY_THRESHOLD=0.98,
        CONNECTION_TIMEOUT=15,
        RISK_THRESHOLD=0.75,
        ALERT_COOLDOWN=180,  # 3 minutes
        ENABLE_CONSOLE_ALERTS=True,
        ENABLE_FILE_ALERTS=True,
        ENABLE_EMAIL_ALERTS=True,
        ENABLE_SLACK_ALERTS=True
    ),
    performance=PerformanceMonitoring(
        ENABLE_CPU_MONITORING=True,
        ENABLE_MEMORY_MONITORING=True,
        ENABLE_DISK_MONITORING=True,
        ENABLE_NETWORK_MONITORING=True,
        ENABLE_LATENCY_MONITORING=True,
        ENABLE_THROUGHPUT_MONITORING=True,
        ENABLE_ERROR_RATE_MONITORING=True,
        ENABLE_SUCCESS_RATE_MONITORING=True,
        MAX_CPU_USAGE=75.0,
        MAX_MEMORY_USAGE=80.0,
        MAX_DISK_USAGE=85.0,
        MAX_LATENCY=500.0,
        MIN_THROUGHPUT=200.0,
        MAX_ERROR_RATE=2.0,
        MIN_SUCCESS_RATE=98.0,
        COLLECTION_INTERVAL=30,
        RETENTION_PERIOD=14 * 24 * 60 * 60  # 14 jours
    ),
    health_check=HealthCheckSettings(
        ENABLE_SIERRA_CHECK=True,
        ENABLE_IBKR_CHECK=True,
        ENABLE_DATA_FEED_CHECK=True,
        ENABLE_FEATURE_CALCULATOR_CHECK=True,
        ENABLE_CONFLUENCE_CHECK=True,
        ENABLE_ML_MODEL_CHECK=True,
        HEALTH_CHECK_INTERVAL=15,
        QUICK_CHECK_INTERVAL=5,
        COMPONENT_TIMEOUT=3,
        DATA_FEED_TIMEOUT=5,
        MIN_HEALTH_SCORE=0.85,
        CRITICAL_HEALTH_SCORE=0.6
    ),
    metrics=MetricsSettings(
        ENABLE_TRADE_METRICS=True,
        ENABLE_PNL_METRICS=True,
        ENABLE_RISK_METRICS=True,
        ENABLE_PERFORMANCE_METRICS=True,
        ENABLE_SYSTEM_METRICS=True,
        ENABLE_RESOURCE_METRICS=True,
        ENABLE_NETWORK_METRICS=True,
        METRICS_STORAGE_PATH="metrics/production/",
        METRICS_RETENTION_DAYS=60,
        ENABLE_CSV_EXPORT=True,
        ENABLE_JSON_EXPORT=True,
        EXPORT_INTERVAL=1800  # 30 minutes
    )
)

# Configuration de test
TEST_MONITORING_CONFIG = MonitoringConfig(
    logging=LoggingSettings(
        CONSOLE_LEVEL=LogLevel.DEBUG,
        FILE_LEVEL=LogLevel.DEBUG,
        SYSTEM_LEVEL=LogLevel.INFO,
        MAIN_LOG_FILE="logs/test_mia_system.log",
        TRADING_LOG_FILE="logs/test_trading.log",
        ERROR_LOG_FILE="logs/test_errors.log",
        PERFORMANCE_LOG_FILE="logs/test_performance.log"
    ),
    alerts=AlertSettings(
        ENABLE_TRADE_ALERTS=False,
        ENABLE_SYSTEM_ALERTS=True,
        ENABLE_PERFORMANCE_ALERTS=False,
        ENABLE_DATA_ALERTS=False,
        ENABLE_CONNECTION_ALERTS=False,
        ENABLE_RISK_ALERTS=False,
        ENABLE_CONSOLE_ALERTS=True,
        ENABLE_FILE_ALERTS=False,
        ENABLE_EMAIL_ALERTS=False,
        ENABLE_SLACK_ALERTS=False
    ),
    performance=PerformanceMonitoring(
        ENABLE_CPU_MONITORING=False,
        ENABLE_MEMORY_MONITORING=False,
        ENABLE_DISK_MONITORING=False,
        ENABLE_NETWORK_MONITORING=False,
        ENABLE_LATENCY_MONITORING=True,
        ENABLE_THROUGHPUT_MONITORING=False,
        ENABLE_ERROR_RATE_MONITORING=True,
        ENABLE_SUCCESS_RATE_MONITORING=False,
        COLLECTION_INTERVAL=300,  # 5 minutes
        RETENTION_PERIOD=24 * 60 * 60  # 1 jour
    ),
    health_check=HealthCheckSettings(
        ENABLE_SIERRA_CHECK=False,
        ENABLE_IBKR_CHECK=False,
        ENABLE_DATA_FEED_CHECK=False,
        ENABLE_FEATURE_CALCULATOR_CHECK=True,
        ENABLE_CONFLUENCE_CHECK=True,
        ENABLE_ML_MODEL_CHECK=False,
        HEALTH_CHECK_INTERVAL=60,
        QUICK_CHECK_INTERVAL=30
    ),
    metrics=MetricsSettings(
        ENABLE_TRADE_METRICS=False,
        ENABLE_PNL_METRICS=False,
        ENABLE_RISK_METRICS=False,
        ENABLE_PERFORMANCE_METRICS=True,
        ENABLE_SYSTEM_METRICS=False,
        ENABLE_RESOURCE_METRICS=False,
        ENABLE_NETWORK_METRICS=False,
        METRICS_STORAGE_PATH="metrics/test/",
        METRICS_RETENTION_DAYS=1,
        ENABLE_CSV_EXPORT=True,
        ENABLE_JSON_EXPORT=False,
        EXPORT_INTERVAL=7200  # 2 heures
    )
)

# Fonction pour obtenir la configuration active
def get_monitoring_config(environment: str = "production") -> MonitoringConfig:
    """Récupère la configuration de monitoring selon l'environnement"""
    configs = {
        "production": PRODUCTION_MONITORING_CONFIG,
        "development": DEFAULT_MONITORING_CONFIG,
        "test": TEST_MONITORING_CONFIG
    }
    
    return configs.get(environment, DEFAULT_MONITORING_CONFIG)

# Fonction pour valider une configuration
def validate_monitoring_config(config: MonitoringConfig) -> bool:
    """Valide une configuration de monitoring"""
    try:
        # Validation des seuils de performance
        if not (0.0 <= config.performance.MAX_CPU_USAGE <= 100.0):
            return False
        if not (0.0 <= config.performance.MAX_MEMORY_USAGE <= 100.0):
            return False
        if not (0.0 <= config.performance.MAX_DISK_USAGE <= 100.0):
            return False
        if not (0.0 <= config.performance.MAX_ERROR_RATE <= 100.0):
            return False
        if not (0.0 <= config.performance.MIN_SUCCESS_RATE <= 100.0):
            return False
            
        # Validation des intervalles
        if config.performance.COLLECTION_INTERVAL <= 0:
            return False
        if config.health_check.HEALTH_CHECK_INTERVAL <= 0:
            return False
        if config.metrics.EXPORT_INTERVAL <= 0:
            return False
            
        return True
        
    except Exception:
        return False

if __name__ == "__main__":
    # Test de la configuration
    print("🔧 Test de la configuration de monitoring...")
    
    # Test configuration par défaut
    default_config = get_monitoring_config("development")
    print(f"✅ Configuration par défaut: {type(default_config).__name__}")
    
    # Test configuration production
    prod_config = get_monitoring_config("production")
    print(f"✅ Configuration production: {type(prod_config).__name__}")
    
    # Test validation
    is_valid = validate_monitoring_config(prod_config)
    print(f"✅ Validation: {is_valid}")
    
    print("🎉 Test terminé avec succès!")


