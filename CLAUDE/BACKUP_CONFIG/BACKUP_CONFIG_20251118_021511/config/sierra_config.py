"""
MIA_IA_SYSTEM - Sierra Chart Configuration
Configuration pour l'intégration Sierra Chart + IBKR
Version: Production Ready

Architecture simplifiée :
- IBKR : Données uniquement (market data, order flow, options)
- Sierra Chart : Exécution des ordres uniquement
"""

import os
import sys
import platform
from core.logger import get_logger
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import json

logger = get_logger(__name__)

# === DÉTECTION PLATEFORME ===


def get_default_sierra_path() -> str:
    """Détermine le chemin Sierra Chart par défaut selon l'OS"""
    system = platform.system()

    if system == "Windows":
        # Chemins Windows typiques
        possible_paths = [
            r"C:\SierraChart",
            r"C:\Program Files\SierraChart",
            r"C:\Program Files (x86)\SierraChart",
            os.path.expanduser(r"~\SierraChart")
        ]

        # Chercher le premier qui existe
        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Par défaut si aucun trouvé
        return r"C:\SierraChart"

    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Applications/SierraChart")

    else:  # Linux
        return os.path.expanduser("~/SierraChart")


def get_dll_path() -> str:
    """Obtient le chemin de la DLL depuis l'environnement ou défaut"""
    # Priorité 1 : Variable environnement
    if dll_path := os.environ.get('SIERRA_DLL_PATH'):
        return dll_path

    # Priorité 2 : Chemin par défaut selon OS
    sierra_base = os.environ.get('SIERRA_CHART_PATH', get_default_sierra_path())

    if platform.system() == "Windows":
        return os.path.join(sierra_base, "Data", "IBKR_Plugin.dll")
    else:
        # Linux/Mac pourraient utiliser .so ou autre
        return os.path.join(sierra_base, "Data", "IBKR_Plugin.so")

# === ENUMS ===


class OrderRoutingMethod(Enum):
    """Méthodes de routage des ordres vers Sierra"""
    DLL_DIRECT = "dll_direct"        # Via DLL (Windows)
    TCP_SOCKET = "tcp_socket"        # Via socket TCP
    SHARED_MEMORY = "shared_memory"  # Via mémoire partagée
    FILE_BASED = "file_based"        # Via fichiers (backup)


class DataFeedMode(Enum):
    """Mode de flux de données"""
    IBKR_ONLY = "ibkr_only"          # IBKR pour toutes les données
    SIERRA_BACKUP = "sierra_backup"   # Sierra en backup si IBKR down


class OrderProvider(Enum):
    """Provider pour l'exécution des ordres"""
    SIERRA_CHART = "sierra_chart"    # Sierra Chart pour exécution
    IBKR_DIRECT = "ibkr_direct"      # IBKR direct (future)
    SIMULATION = "simulation"         # Simulation interne

# === CONFIGURATION CLASSES ===


@dataclass
class IBKRConfig:
    """Configuration IBKR pour les données uniquement"""
    # Connexion
    host: str = "127.0.0.1"
    port: int = 7497  # 7496 pour live, 7497 pour paper
    client_id: int = 1

    # Options connexion
    enable_connection: bool = True
    auto_reconnect: bool = True
    reconnect_attempts: int = 10
    reconnect_delay: int = 30
    connection_timeout: int = 30

    # Data subscriptions
    market_data_type: int = 3  # 1=Live, 2=Frozen, 3=Delayed, 4=Delayed frozen
    subscribe_positions: bool = True
    subscribe_orders: bool = False  # False car ordres via Sierra
    subscribe_account: bool = True

    # Rate limits
    max_requests_per_second: int = 50
    max_ticker_subscriptions: int = 100


@dataclass
class DTCConfig:
    """Configuration DTC Protocol pour Sierra Chart"""
    # Connexion
    host: str = "127.0.0.1"
    port: int = 11100  # 11099 pour live, 11100 pour paper
    client_id: int = 1

    # Options connexion
    enable_connection: bool = True
    auto_reconnect: bool = True
    reconnect_attempts: int = 10
    reconnect_delay: int = 30
    connection_timeout: int = 30

    # Trading
    trading_enabled: bool = True
    data_collection_enabled: bool = False
    auto_connect: bool = True

    # Rate limits
    max_requests_per_second: int = 50
    max_order_submissions: int = 100


@dataclass
class SierraChartConfig:
    """Configuration Sierra Chart pour exécution uniquement"""
    # Chemins - Utilise la fonction helper
    dll_path: str = field(default_factory=get_dll_path)
    sierra_exe_path: Optional[str] = None
    data_folder: Optional[str] = None

    # Méthode de communication
    routing_method: OrderRoutingMethod = OrderRoutingMethod.DLL_DIRECT

    # Si TCP Socket - Ajout des attributs manquants
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 5555
    server_address: str = "127.0.0.1"  # Alias pour tcp_host (compatibilité)
    server_port: int = 5555  # Alias pour tcp_port (compatibilité)

    # Options plugin
    enable_plugin: bool = True
    plugin_timeout_ms: int = 5000
    order_confirmation_required: bool = True

    # Trading control - AJOUT DE L'ATTRIBUT MANQUANT
    trading_enabled: bool = True  # Active/désactive le trading via Sierra Chart
    
    # Validation ordres
    enable_order_validation: bool = True
    max_order_size: int = 10
    allowed_order_types: List[str] = field(default_factory=lambda: ["LIMIT", "MARKET", "STOP"])
    
    # Daily limits
    daily_loss_limit: float = 1000.0  # Ajout pour compatibilité

    # Monitoring Sierra
    enable_position_tracking: bool = True
    position_sync_interval: int = 5  # secondes

    # Rejection handling
    order_rejection_retry: bool = True
    max_rejection_retries: int = 3
    rejection_retry_delay: int = 1000  # ms

    # Stop orders
    use_stop_orders: bool = True
    stop_order_offset_ticks: int = 2

    def __post_init__(self):
        """Validation post-init"""
        # Ajuster selon l'OS
        if platform.system() != "Windows" and self.routing_method == OrderRoutingMethod.DLL_DIRECT:
            logger.warning("DLL routing non disponible sur cet OS, bascule vers TCP")
            self.routing_method = OrderRoutingMethod.TCP_SOCKET
        
        # Synchroniser les alias
        self.server_address = self.tcp_host
        self.server_port = self.tcp_port


@dataclass
class RiskConfig:
    """Configuration gestion du risque"""
    # Position sizing
    max_position_size: int = 3
    position_size_method: str = "fixed"

    # Daily limits
    daily_loss_limit: float = 1000.0
    daily_profit_target: float = 500.0
    max_daily_trades: int = 20

    # Per trade
    stop_loss_default: int = 12  # ticks
    take_profit_default: int = 24  # ticks
    max_slippage_ticks: int = 2

    # Order management
    use_bracket_orders: bool = True
    auto_breakeven_enabled: bool = False
    breakeven_trigger_ticks: int = 8

    # Emergency
    kill_switch_enabled: bool = True
    kill_switch_trigger: float = 500.0  # perte max avant arrêt


@dataclass
class ContractsConfig:
    """Configuration des contrats tradables"""
    # Contrat principal
    primary_symbol: str = "ES"

    # Symboles autorisés
    enabled_symbols: List[str] = field(default_factory=lambda: ["ES", "MES"])

    # Mapping symboles IBKR -> Sierra
    symbol_mapping: Dict[str, str] = field(default_factory=lambda: {
        "ES": "ESM24",   # À updater selon expiration
        "MES": "MESM24"
    })

    # Contract specs
    contract_specs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "ES": {
            "multiplier": 50,
            "tick_size": 0.25,
            "tick_value": 12.50,
            "margin_requirement": 13200,
            "trading_hours": "08:30-15:15"
        },
        "MES": {
            "multiplier": 5,
            "tick_size": 0.25,
            "tick_value": 1.25,
            "margin_requirement": 1320,
            "trading_hours": "08:30-15:15"
        }
    })

    # Auto-roll
    enable_auto_rollover: bool = True
    rollover_days_before_expiry: int = 5

    def get_contract_spec(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retourne les specs d'un contrat"""
        return self.contract_specs.get(symbol)


@dataclass
class SyncConfig:
    """Configuration synchronisation IBKR/Sierra"""
    # Position sync
    enable_position_sync: bool = True
    position_sync_interval: int = 10  # secondes
    position_mismatch_threshold: int = 0  # 0 = exact match requis

    # Order sync
    enable_order_sync: bool = True
    order_status_check_interval: int = 2  # secondes

    # Data validation
    validate_prices: bool = True
    max_price_difference: float = 1.0  # ticks

    # Reconciliation
    auto_reconcile: bool = True
    reconcile_on_startup: bool = True
    reconcile_interval: int = 300  # 5 minutes


@dataclass
class SecurityConfig:
    """Configuration sécurité et limites"""
    # Validation ordres
    enable_order_validation: bool = True
    max_order_value: float = 100000.0
    min_order_value: float = 0.0

    # Position limits
    max_gross_position: int = 10
    max_net_position: int = 5

    # IP restrictions (si TCP)
    allowed_ips: List[str] = field(default_factory=lambda: ["127.0.0.1"])

    # Kill switches
    enable_kill_switch: bool = True
    kill_switch_loss_threshold: float = 1000.0
    kill_switch_error_count: int = 10

    # Fat finger protection
    enable_fat_finger_protection: bool = True
    fat_finger_multiplier: float = 5.0  # 5x taille normale = alerte

    # Monitoring
    enable_real_time_monitoring: bool = True
    alert_on_position_mismatch: bool = True
    alert_on_order_rejection: bool = True


@dataclass
class MonitoringConfig:
    """Configuration monitoring et alertes"""
    # Logging
    log_all_orders: bool = True
    log_all_fills: bool = True
    log_all_errors: bool = True

    # Performance tracking
    track_latency: bool = True
    latency_warning_ms: float = 100.0
    latency_critical_ms: float = 500.0

    # Health checks
    enable_health_checks: bool = True
    health_check_interval: int = 60  # secondes

    # Alerts
    enable_email_alerts: bool = False
    email_recipients: List[str] = field(default_factory=list)

    enable_sms_alerts: bool = False
    sms_recipients: List[str] = field(default_factory=list)


@dataclass
class SierraConfig:
    """Configuration complète Sierra Chart"""
    # Metadata
    config_name: str = "default"
    environment: str = "development"  # development, staging, production
    version: str = "1.0.0"
    
    # Providers - Ajout pour compatibilité
    data_provider: DataFeedMode = DataFeedMode.IBKR_ONLY
    order_provider: OrderProvider = OrderProvider.SIERRA_CHART

    # Sub-configurations
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    dtc: DTCConfig = field(default_factory=DTCConfig)
    sierra_chart: SierraChartConfig = field(default_factory=SierraChartConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    contracts: ContractsConfig = field(default_factory=ContractsConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    def validate(self) -> bool:
        """Valide la configuration complète"""
        validations = validate_config(self)
        return validations.get('overall', False)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return asdict(self)

    def save_to_file(self, filepath: str):
        """Sauvegarde dans fichier JSON"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'SierraConfig':
        """Charge depuis fichier JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SierraConfig':
        """Crée instance depuis dictionnaire avec parsing sécurisé"""
        # Parser chaque sous-config
        config = cls()

        # Metadata
        config.config_name = data.get('config_name', 'default')
        config.environment = data.get('environment', 'development')
        config.version = data.get('version', '1.0.0')
        
        # Providers avec parsing enum sécurisé
        if 'data_provider' in data:
            try:
                config.data_provider = DataFeedMode(data['data_provider'])
            except (ValueError, KeyError):
                logger.warning(f"Invalid data_provider: {data.get('data_provider')}, using default")
                config.data_provider = DataFeedMode.IBKR_ONLY
                
        if 'order_provider' in data:
            try:
                config.order_provider = OrderProvider(data['order_provider'])
            except (ValueError, KeyError):
                logger.warning(f"Invalid order_provider: {data.get('order_provider')}, using default")
                config.order_provider = OrderProvider.SIERRA_CHART

        # Sub-configs avec parsing enum interne
        if 'ibkr' in data:
            config.ibkr = IBKRConfig(**data['ibkr'])
            
        if 'sierra_chart' in data:
            sierra_data = data['sierra_chart'].copy()
            # Parser l'enum routing_method si présent
            if 'routing_method' in sierra_data:
                try:
                    sierra_data['routing_method'] = OrderRoutingMethod(sierra_data['routing_method'])
                except (ValueError, KeyError):
                    logger.warning(f"Invalid routing_method: {sierra_data.get('routing_method')}, using default")
                    sierra_data['routing_method'] = OrderRoutingMethod.DLL_DIRECT
            config.sierra_chart = SierraChartConfig(**sierra_data)
            
        if 'risk' in data:
            config.risk = RiskConfig(**data['risk'])
        if 'contracts' in data:
            config.contracts = ContractsConfig(**data['contracts'])
        if 'sync' in data:
            config.sync = SyncConfig(**data['sync'])
        if 'security' in data:
            config.security = SecurityConfig(**data['security'])
        if 'monitoring' in data:
            config.monitoring = MonitoringConfig(**data['monitoring'])

        return config

# === VALIDATION ===


def validate_config(config: SierraConfig) -> Dict[str, bool]:
    """Valide la configuration complète"""
    validations = {}

    # IBKR validation
    validations['ibkr_host'] = bool(config.ibkr.host)
    validations['ibkr_port'] = 1000 < config.ibkr.port < 65535

    # Sierra validation - Check selon OS
    if config.sierra_chart.routing_method == OrderRoutingMethod.DLL_DIRECT:
        if platform.system() == "Windows":
            dll_exists = os.path.exists(config.sierra_chart.dll_path)
            validations['sierra_dll'] = dll_exists
            if not dll_exists:
                logger.warning(f"DLL introuvable: {config.sierra_chart.dll_path}")
        else:
            validations['sierra_dll'] = False  # DLL pas supporté
    else:
        validations['sierra_dll'] = True  # Pas besoin de DLL

    # Risk validation
    validations['risk_limits'] = (
        config.risk.daily_loss_limit > 0 and
        config.risk.max_position_size > 0
    )

    # Contracts validation
    validations['primary_symbol'] = config.contracts.primary_symbol in config.contracts.enabled_symbols

    # Overall
    validations['overall'] = all(validations.values())

    return validations

# === FACTORY FUNCTIONS (RESTE DU CODE INCHANGÉ) ===


# Variable globale pour stocker la config active
_active_config: Optional[SierraConfig] = None


def set_sierra_config(config: SierraConfig) -> None:
    """Définit la configuration Sierra/IBKR active"""
    global _active_config
    _active_config = config
    logger.info(f"Configuration Sierra/IBKR activée: {config.config_name}")


def get_sierra_config() -> SierraConfig:
    """Récupère la configuration Sierra/IBKR active"""
    global _active_config
    if _active_config is None:
        _active_config = create_default_config()
    return _active_config


def create_default_config() -> SierraConfig:
    """Configuration par défaut (paper trading sécurisé)"""
    return create_paper_trading_config()


def create_paper_trading_config() -> SierraConfig:
    """Crée une configuration pour paper trading"""
    config = SierraConfig()
    config.config_name = "Paper Trading Config"
    config.environment = "paper"

    # IBKR Paper Trading
    config.ibkr.host = "127.0.0.1"
    config.ibkr.port = 7497  # Paper trading port
    config.ibkr.client_id = 1
    config.ibkr.market_data_type = 3  # Delayed data

    # Sierra Chart - Path depuis environnement
    config.sierra_chart.dll_path = get_dll_path()
    config.sierra_chart.enable_order_validation = True
    config.sierra_chart.trading_enabled = False  # Désactivé par défaut en paper

    # Risk conservateur
    config.risk.max_position_size = 2
    config.risk.daily_loss_limit = 1000.0

    # Contracts MES pour paper
    config.contracts.primary_symbol = "MES"
    config.contracts.enabled_symbols = ["MES"]

    return config


def create_live_trading_config() -> SierraConfig:
    """Crée une configuration pour live trading"""
    config = SierraConfig()
    config.config_name = "Live Trading Config"
    config.environment = "production"

    # IBKR Live
    config.ibkr.host = "127.0.0.1"
    config.ibkr.port = 7496  # Live trading port
    config.ibkr.client_id = 1
    config.ibkr.market_data_type = 1  # Live data

    # Sierra Chart Live
    config.sierra_chart.dll_path = get_dll_path()
    config.sierra_chart.enable_order_validation = True
    config.sierra_chart.use_stop_orders = True
    config.sierra_chart.trading_enabled = True  # Activé pour live

    # Risk strict
    config.risk.max_position_size = 1
    config.risk.daily_loss_limit = 500.0
    config.risk.use_bracket_orders = True

    # Sécurité maximale
    config.security.enable_kill_switch = True
    config.security.kill_switch_loss_threshold = 300.0
    config.security.enable_real_time_monitoring = True

    # Contracts MES uniquement au début
    config.contracts.primary_symbol = "MES"
    config.contracts.enabled_symbols = ["MES"]

    return config


def create_data_collection_config() -> SierraConfig:
    """Crée une configuration pour collecte de données"""
    config = create_paper_trading_config()  # Base sur paper
    config.config_name = "Data Collection Config"
    
    # Désactiver le trading pour data collection
    config.sierra_chart.trading_enabled = False

    # Paramètres permissifs
    config.risk.max_position_size = 3
    config.risk.daily_loss_limit = 5000.0
    config.risk.stop_loss_default = 20  # Stop large

    # Pas de filtres
    config.sierra_chart.order_rejection_retry = False

    # Sécurité minimale pour plus de trades
    config.security.enable_order_validation = False
    config.security.max_daily_trades = 100

    return config


def create_test_config() -> SierraConfig:
    """Configuration pour tests unitaires"""
    config = SierraConfig()
    config.config_name = "Test Config"
    config.environment = "test"

    # Tout en local/simulé
    config.ibkr.host = "localhost"
    config.ibkr.port = 9999
    config.ibkr.enable_connection = False  # Pas de vraie connexion

    config.sierra_chart.enable_plugin = False
    config.sierra_chart.trading_enabled = False
    config.contracts.primary_symbol = "TEST"

    return config

# === VALIDATION HELPERS ===


def validate_ibkr_connection(config: SierraConfig) -> bool:
    """Valide que la connexion IBKR est possible"""
    try:
        # Check basiques
        if not config.ibkr.enable_connection:
            return False

        if config.ibkr.port not in [7496, 7497]:
            logger.warning(f"Port IBKR non standard: {config.ibkr.port}")

        # Dans le futur, on pourrait tester un ping
        return True

    except Exception as e:
        logger.error(f"Erreur validation IBKR: {e}")
        return False


def validate_sierra_dll(config: SierraConfig) -> bool:
    """Valide que la DLL Sierra existe"""
    try:
        if not config.sierra_chart.enable_plugin:
            return True  # Pas besoin si désactivé

        if config.sierra_chart.routing_method != OrderRoutingMethod.DLL_DIRECT:
            return True  # Pas besoin de DLL

        dll_path = Path(config.sierra_chart.dll_path)
        return dll_path.exists() and dll_path.suffix in ['.dll', '.so']

    except Exception as e:
        logger.error(f"Erreur validation DLL: {e}")
        return False

# === EXPORT FUNCTIONS ===


def get_available_configs() -> Dict[str, SierraConfig]:
    """Retourne toutes les configurations disponibles"""
    return {
        'paper': create_paper_trading_config(),
        'live': create_live_trading_config(),
        'data_collection': create_data_collection_config(),
        'test': create_test_config()
    }


def load_config_by_name(name: str) -> SierraConfig:
    """Charge une configuration par son nom"""
    configs = get_available_configs()
    if name not in configs:
        logger.warning(f"Config '{name}' non trouvée, utilisation de 'paper'")
        return configs['paper']
    return configs[name]

# === EXPORTS ===


__all__ = [
    'SierraConfig',
    'IBKRConfig',
    'SierraChartConfig',
    'RiskConfig',
    'ContractsConfig',
    'SyncConfig',
    'SecurityConfig',
    'MonitoringConfig',
    'OrderRoutingMethod',
    'DataFeedMode',
    'OrderProvider',  # Ajout du nouvel enum
    'get_sierra_config',
    'set_sierra_config',
    'create_paper_trading_config',
    'create_live_trading_config',
    'create_data_collection_config',
    'create_test_config',
    'validate_config',
    'get_available_configs',
    'load_config_by_name',
    'get_dll_path',
    'get_default_sierra_path'
]


@dataclass
class ContractConfig:
    """Configuration contrat trading"""
    symbol: str = "ES"
    exchange: str = "CME"
    multiplier: float = 50.0
    tick_size: float = 0.25
    tick_value: float = 12.50
    trading_hours: str = "17:00-16:00"
    timezone: str = "America/Chicago"