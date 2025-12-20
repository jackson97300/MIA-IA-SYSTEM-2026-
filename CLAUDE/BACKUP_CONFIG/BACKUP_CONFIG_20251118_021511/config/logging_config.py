"""
MIA_IA_SYSTEM - Logging Configuration
Configuration centralisée et standardisée du logging
Version: Production Ready

Ce module configure le logging pour tout le système avec :
- Formats cohérents
- Rotation des logs
- Niveaux par module
- Handlers multiples (fichier, console, Discord)
"""

import os
import sys
from core.logger import get_logger
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import json
import colorlog  # Pour logs colorés en console

# === CONFIGURATION PATHS ===

# Base paths
LOG_BASE_DIR = Path(os.environ.get('MIA_LOG_DIR', 'logs'))
LOG_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Log files par catégorie
LOG_FILES = {
    'main': LOG_BASE_DIR / 'mia_trading.log',
    'trading': LOG_BASE_DIR / 'trading' / 'trading.log',
    'execution': LOG_BASE_DIR / 'trading' / 'execution.log',
    'signals': LOG_BASE_DIR / 'trading' / 'signals.log',
    'performance': LOG_BASE_DIR / 'performance' / 'performance.log',
    'risk': LOG_BASE_DIR / 'risk' / 'risk.log',
    'errors': LOG_BASE_DIR / 'errors' / 'errors.log',
    'system': LOG_BASE_DIR / 'system' / 'system.log',
    'ml': LOG_BASE_DIR / 'ml' / 'ml.log',
    'data': LOG_BASE_DIR / 'data' / 'data_collection.log',
    'monitoring': LOG_BASE_DIR / 'monitoring' / 'monitoring.log',
    'debug': LOG_BASE_DIR / 'debug' / 'debug.log'
}

# Créer tous les sous-dossiers
for log_file in LOG_FILES.values():
    log_file.parent.mkdir(parents=True, exist_ok=True)

# === LOG LEVELS PAR MODULE ===

MODULE_LOG_LEVELS = {
    # Core modules
    'core': logging.INFO,
    'core.battle_navale': logging.DEBUG,  # Plus de détails pour méthode signature
    'core.patterns_detector': logging.INFO,

    # Features
    'features': logging.INFO,
    'features.feature_calculator': logging.DEBUG,  # Debug pour optimization

    # Strategies
    'strategies': logging.INFO,
    'strategies.signal_generator': logging.DEBUG,  # Détails génération signaux

    # Execution
    'execution': logging.INFO,
    'execution.simple_trader': logging.DEBUG,  # Détails automation
    'execution.order_manager': logging.INFO,

    # Monitoring
    'monitoring': logging.INFO,
    'monitoring.discord_notifier': logging.INFO,

    # ML
    'ml': logging.INFO,
    'ml.simple_model': logging.DEBUG,

    # Performance
    'performance': logging.INFO,

    # External libraries
    'ib_insync': logging.WARNING,  # Réduire verbosité IBKR
    'urllib3': logging.WARNING,    # Réduire verbosité requests
    'asyncio': logging.WARNING     # Réduire verbosité async
}

# === FORMATS ===

# Format détaillé pour fichiers
DETAILED_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | %(message)s'

# Format simple pour console
SIMPLE_FORMAT = '%(asctime)s | %(levelname)-8s | %(message)s'

# Format coloré pour console
COLOR_FORMAT = '%(log_color)s%(asctime)s | %(levelname)-8s | %(message)s%(reset)s'

# Format JSON pour parsing automatique
JSON_FORMAT = {
    'timestamp': '%(asctime)s',
    'level': '%(levelname)s',
    'logger': '%(name)s',
    'function': '%(funcName)s',
    'line': '%(lineno)d',
    'message': '%(message)s'
}

# === CUSTOM FORMATTERS ===


class JSONFormatter(logging.Formatter):
    """Formatter pour output JSON"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage()
        }

        # Ajouter exception si présente
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Ajouter données custom si présentes
        if hasattr(record, 'trade_id'):
            log_data['trade_id'] = record.trade_id
        if hasattr(record, 'signal_id'):
            log_data['signal_id'] = record.signal_id
        if hasattr(record, 'performance_metrics'):
            log_data['performance_metrics'] = record.performance_metrics

        return json.dumps(log_data)


class TradingFormatter(logging.Formatter):
    """Formatter spécialisé pour logs trading"""

    def format(self, record):
        # Ajouter symbole si présent
        if hasattr(record, 'symbol'):
            record.msg = f"[{record.symbol}] {record.msg}"

        # Ajouter prix si présent
        if hasattr(record, 'price'):
            record.msg = f"{record.msg} @ {record.price}"

        return super().format(record)

# === CUSTOM FILTERS ===


class ErrorOnlyFilter(logging.Filter):
    """Filtre pour capturer seulement les erreurs"""

    def filter(self, record):
        return record.levelno >= logging.ERROR


class TradingOnlyFilter(logging.Filter):
    """Filtre pour logs trading uniquement"""

    def filter(self, record):
        return record.name.startswith(('execution', 'strategies', 'core.battle_navale'))


class PerformanceFilter(logging.Filter):
    """Filtre pour logs performance"""

    def filter(self, record):
        return record.name.startswith('performance') or hasattr(record, 'performance_metrics')

# === CUSTOM HANDLERS ===


class DiscordLogHandler(logging.Handler):
    """Handler pour envoyer logs critiques sur Discord"""

    def __init__(self, min_level=logging.ERROR):
        super().__init__()
        self.min_level = min_level
        self.discord_notifier = None

    def emit(self, record):
        if record.levelno >= self.min_level:
            # Import tardif pour éviter dépendance circulaire
            if self.discord_notifier is None:
                try:
                    from monitoring.discord_notifier import create_discord_notifier
                    self.discord_notifier = create_discord_notifier()
                except Exception:
                    return

            # Formatter le message
            msg = self.format(record)

            # Envoyer sur Discord (async, donc on schedule)
            if self.discord_notifier:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(
                            self.discord_notifier.send_error(
                                f"Log {record.levelname}",
                                msg
                            )
                        )
                except Exception:
                    pass

# === CONFIGURATION FUNCTIONS ===


def setup_logging(
    level: str = "INFO",
    console_output: bool = True,
    file_output: bool = True,
    json_output: bool = False,
    discord_output: bool = True,
    colored_console: bool = True
) -> None:
    """
    Configure le logging pour tout le système

    Args:
        level: Niveau de log global (DEBUG, INFO, WARNING, ERROR)
        console_output: Activer output console
        file_output: Activer output fichiers
        json_output: Activer format JSON
        discord_output: Activer notifications Discord pour erreurs
        colored_console: Activer couleurs en console
    """

    # Niveau global
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Nettoyer handlers existants
    root_logger.handlers.clear()

    # === CONSOLE HANDLER ===
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        if colored_console and colorlog:
            console_formatter = colorlog.ColoredFormatter(
                COLOR_FORMAT,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            console_formatter = logging.Formatter(SIMPLE_FORMAT)

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # === FILE HANDLERS ===
    if file_output:
        # Handler principal avec rotation
        main_handler = logging.handlers.RotatingFileHandler(
            LOG_FILES['main'],
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)

        if json_output:
            main_handler.setFormatter(JSONFormatter())
        else:
            main_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))

        root_logger.addHandler(main_handler)

        # Handler erreurs séparé
        error_handler = logging.handlers.RotatingFileHandler(
            LOG_FILES['errors'],
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        error_handler.addFilter(ErrorOnlyFilter())
        root_logger.addHandler(error_handler)

        # Handler trading séparé
        trading_handler = logging.handlers.RotatingFileHandler(
            LOG_FILES['trading'],
            maxBytes=20*1024*1024,  # 20MB
            backupCount=5,
            encoding='utf-8'
        )
        trading_handler.setLevel(logging.INFO)
        trading_handler.setFormatter(TradingFormatter(DETAILED_FORMAT))
        trading_handler.addFilter(TradingOnlyFilter())
        root_logger.addHandler(trading_handler)

        # Handler performance séparé
        perf_handler = logging.handlers.RotatingFileHandler(
            LOG_FILES['performance'],
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        perf_handler.addFilter(PerformanceFilter())
        root_logger.addHandler(perf_handler)

    # === DISCORD HANDLER ===
    if discord_output:
        discord_handler = DiscordLogHandler(min_level=logging.ERROR)
        discord_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))
        root_logger.addHandler(discord_handler)

    # === CONFIGURE MODULE LEVELS ===
    for module_name, module_level in MODULE_LOG_LEVELS.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(module_level)

    # Log de démarrage
    logging.info("=" * 60)
    logging.info("MIA_IA_SYSTEM - Logging configuré")
    logging.info(f"Niveau global: {level}")
    logging.info(f"Console: {'ON' if console_output else 'OFF'}")
    logging.info(f"Fichiers: {'ON' if file_output else 'OFF'}")
    logging.info(f"JSON: {'ON' if json_output else 'OFF'}")
    logging.info(f"Discord: {'ON' if discord_output else 'OFF'}")
    logging.info("=" * 60)

# === HELPER FUNCTIONS ===


def get_logger(name: str) -> logging.Logger:
    """
    Obtient un logger configuré

    Args:
        name: Nom du module

    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


def log_trade(
    logger: logging.Logger,
    level: int,
    message: str,
    trade_id: Optional[str] = None,
    symbol: Optional[str] = None,
    price: Optional[float] = None,
    **kwargs
) -> None:
    """
    Log spécialisé pour trades

    Args:
        logger: Logger à utiliser
        level: Niveau de log
        message: Message principal
        trade_id: ID du trade
        symbol: Symbole tradé
        price: Prix d'exécution
        **kwargs: Données additionnelles
    """
    extra = {}
    if trade_id:
        extra['trade_id'] = trade_id
    if symbol:
        extra['symbol'] = symbol
    if price:
        extra['price'] = price
    extra.update(kwargs)

    logger.log(level, message, extra=extra)


def log_performance(
    logger: logging.Logger,
    metrics: Dict[str, Any],
    message: str = "Performance Update"
) -> None:
    """
    Log spécialisé pour performance

    Args:
        logger: Logger à utiliser
        metrics: Métriques de performance
        message: Message principal
    """
    logger.info(message, extra={'performance_metrics': metrics})


def log_signal(
    logger: logging.Logger,
    signal_id: str,
    signal_type: str,
    confidence: float,
    message: str,
    **kwargs
) -> None:
    """
    Log spécialisé pour signaux

    Args:
        logger: Logger à utiliser
        signal_id: ID du signal
        signal_type: Type de signal
        confidence: Confiance du signal
        message: Message principal
        **kwargs: Données additionnelles
    """
    extra = {
        'signal_id': signal_id,
        'signal_type': signal_type,
        'confidence': confidence
    }
    extra.update(kwargs)

    logger.info(message, extra=extra)


def cleanup_old_logs(days_to_keep: int = 30) -> None:
    """
    Nettoie les vieux logs

    Args:
        days_to_keep: Nombre de jours à conserver
    """
    import glob
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    for log_dir in LOG_BASE_DIR.rglob("*.log.*"):
        try:
            if log_dir.stat().st_mtime < cutoff_date.timestamp():
                log_dir.unlink()
                logging.info(f"Supprimé vieux log: {log_dir}")
        except Exception as e:
            logging.error(f"Erreur suppression log {log_dir}: {e}")

# === DECORATORS ===


def log_execution_time(logger_name: Optional[str] = None):
    """Décorateur pour logger le temps d'exécution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds() * 1000

                if execution_time > 100:  # Log si > 100ms
                    logger.warning(
                        f"{func.__name__} took {execution_time:.1f}ms",
                        extra={'execution_time_ms': execution_time}
                    )
                else:
                    logger.debug(
                        f"{func.__name__} took {execution_time:.1f}ms",
                        extra={'execution_time_ms': execution_time}
                    )

                return result

            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(
                    f"{func.__name__} failed after {execution_time:.1f}ms: {e}",
                    extra={'execution_time_ms': execution_time},
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


def log_errors(logger_name: Optional[str] = None):
    """Décorateur pour logger automatiquement les erreurs"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator

# === INITIALIZATION ===

# Auto-configure au chargement du module


def auto_configure():
    """Configuration automatique au démarrage"""
    # Niveau depuis environnement
    log_level = os.environ.get('MIA_LOG_LEVEL', 'INFO')

    # Options depuis environnement
    console_output = os.environ.get('MIA_LOG_CONSOLE', 'true').lower() == 'true'
    file_output = os.environ.get('MIA_LOG_FILE', 'true').lower() == 'true'
    json_output = os.environ.get('MIA_LOG_JSON', 'false').lower() == 'true'
    discord_output = os.environ.get('MIA_LOG_DISCORD', 'true').lower() == 'true'

    # Configurer
    setup_logging(
        level=log_level,
        console_output=console_output,
        file_output=file_output,
        json_output=json_output,
        discord_output=discord_output
    )


# Auto-configure si importé directement
if __name__ != "__main__":
    auto_configure()

# === EXPORTS ===

__all__ = [
    # Main functions
    'setup_logging',
    'get_logger',

    # Specialized logging
    'log_trade',
    'log_performance',
    'log_signal',

    # Utilities
    'cleanup_old_logs',

    # Decorators
    'log_execution_time',
    'log_errors',

    # Formatters
    'JSONFormatter',
    'TradingFormatter',

    # Filters
    'ErrorOnlyFilter',
    'TradingOnlyFilter',
    'PerformanceFilter',

    # Handlers
    'DiscordLogHandler',

    # Constants
    'LOG_BASE_DIR',
    'LOG_FILES',
    'MODULE_LOG_LEVELS'
]

# === MAIN (pour tests) ===

if __name__ == "__main__":
    # Test configuration
    setup_logging(level="DEBUG", colored_console=True)

    # Test différents loggers
    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test log trading
    trading_logger = get_logger("execution.simple_trader")
    log_trade(
        trading_logger,
        logging.INFO,
        "Trade exécuté",
        trade_id="T001",
        symbol="ES",
        price=4500.25,
        quantity=2
    )

    # Test log performance
    perf_logger = get_logger("performance")
    log_performance(
        perf_logger,
        {
            'win_rate': 0.65,
            'profit_factor': 1.8,
            'sharpe_ratio': 1.5
        }
    )

    logger.info("\n[OK] Configuration logging testée avec succès")
