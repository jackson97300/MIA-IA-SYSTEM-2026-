#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Core Logger Module
Système de logging centralisé avec support UTF-8 pour Windows

Version: Production Ready v1.0
Responsabilité: Configuration et gestion centralisée des logs

FONCTIONNALITÉS:
1. Configuration UTF-8 automatique pour Windows
2. Formatage cohérent des logs
3. Rotation automatique des fichiers
4. Niveaux de log configurables
5. Support multi-handlers (console + fichier)
6. Thread-safe
"""

import sys
import io
import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
import threading

# === CONFIGURATION ENCODAGE UTF-8 POUR WINDOWS ===
# CRITICAL: Doit être fait AVANT tout autre import/utilisation
if sys.platform == "win32":
    # Forcer UTF-8 pour stdout et stderr
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Configurer l'encodage par défaut pour les fichiers
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            pass

# === CONSTANTS ===

# Niveaux de log
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Formats de log avec UTC et process/thread
FORMATS = {
    'console': '%(asctime)s %(levelname)s [%(process)d/%(threadName)s] %(name)s: %(message)s',
    'file': '%(asctime)s %(levelname)s [%(process)d/%(threadName)s] %(name)s: %(funcName)s:%(lineno)d - %(message)s',
    'json': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
}

# Configuration par défaut
DEFAULT_CONFIG = {
    'log_level': 'INFO',
    'console_enabled': True,  # ✅ RÉACTIVÉ: Logs dans terminal ET fichiers
    'file_enabled': True,
    'log_dir': 'logs',
    'max_bytes': 100 * 1024 * 1024,  # 100MB - Augmenté pour éviter rotation fréquente sur Windows
    'backup_count': 5,
    'format_type': 'console',
    'encoding': 'utf-8'
}

# === CUSTOM FORMATTER ===

class UTF8Formatter(logging.Formatter):
    """Formatter avec support UTF-8 et suppression emojis si nécessaire"""

    def __init__(self, fmt=None, datefmt=None, remove_emojis=False):
        super().__init__(fmt, datefmt)
        self.remove_emojis = remove_emojis

        # Mapping emojis vers texte (si suppression activée)
        self.emoji_map = {
            '🚀': '[LAUNCH]',
            '🧠': '[BRAIN]',
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARN]',
            '📊': '[STATS]',
            '💾': '[SAVE]',
            '🔄': '[SYNC]',
            '🎯': '[TARGET]',
            '🏁': '[FINISH]',
            '🛑': '[STOP]',
            '🔥': '[HOT]',
            '💰': '[MONEY]',
            '📈': '[UP]',
            '📉': '[DOWN]',
            '🤖': '[BOT]',
            '🎮': '[GAME]',
            '🔍': '[SEARCH]',
            '💡': '[IDEA]',
            '🚨': '[ALERT]'
        }

    def format(self, record):
        """Format avec gestion UTF-8"""
        try:
            msg = super().format(record)

            # Suppression emojis si activé
            if self.remove_emojis:
                for emoji, text in self.emoji_map.items():
                    msg = msg.replace(emoji, text)

            return msg

        except Exception as e:
            # Fallback en cas d'erreur
            return f"[LOG ERROR: {e}] {record.msg}"

class TradingJSONFormatter(logging.Formatter):
    """Formatter JSON spécialisé pour l'audit des décisions de trading"""

    def __init__(self):
        super().__init__()

    def format(self, record):
        """Format JSON structuré pour l'audit trading"""
        try:
            # Données de base
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "process_id": record.process,
                "thread": record.threadName
            }

            # Ajout des données de trading si disponibles
            if hasattr(record, 'method'):
                log_data["method"] = record.method
            if hasattr(record, 'vix_regime'):
                log_data["vix_regime"] = record.vix_regime
            if hasattr(record, 'signal_type'):
                log_data["signal_type"] = record.signal_type
            if hasattr(record, 'level_price'):
                log_data["level_price"] = record.level_price
            if hasattr(record, 'final_score'):
                log_data["final_score"] = record.final_score
            if hasattr(record, 'action'):
                log_data["action"] = record.action
            if hasattr(record, 'confidence'):
                log_data["confidence"] = record.confidence

            # Ajout des métadonnées de performance
            if hasattr(record, 'execution_time_ms'):
                log_data["execution_time_ms"] = record.execution_time_ms
            if hasattr(record, 'data_staleness_ms'):
                log_data["data_staleness_ms"] = record.data_staleness_ms

            return json.dumps(log_data, ensure_ascii=False)

        except Exception as e:
            # Fallback en cas d'erreur
            return json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "logger": "TradingJSONFormatter",
                "message": f"Formatter error: {e}",
                "original_message": str(record.msg)
            }, ensure_ascii=False)

# === SINGLETON LOGGER MANAGER ===

class LoggerManager:
    """Gestionnaire singleton des loggers"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialisation du manager"""
        if self._initialized:
            return

        self._initialized = True
        self.config = DEFAULT_CONFIG.copy()
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: Dict[str, logging.Handler] = {}

        # Création répertoire logs
        self.log_dir = Path(self.config['log_dir'])
        self.log_dir.mkdir(exist_ok=True)

        # Configuration racine
        self._setup_root_logger()

    def _setup_root_logger(self):
        """Configuration logger racine"""
        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVELS[self.config['log_level']])

        # Suppression handlers existants
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def get_logger(self, name: str, **kwargs) -> logging.Logger:
        """
        Obtenir ou créer un logger

        Args:
            name: Nom du logger
            **kwargs: Options (level, format_type, etc.)

        Returns:
            Logger configuré
        """
        if name in self.loggers:
            return self.loggers[name]

        # Création nouveau logger
        logger = logging.getLogger(name)

        # Configuration niveau
        level = kwargs.get('level', self.config['log_level'])
        logger.setLevel(LOG_LEVELS.get(level, logging.INFO))

        # Vérifier si le logger a déjà des handlers pour éviter la multiplication
        if not logger.handlers:
            # Ajout handlers seulement si aucun handler existant
            if self.config['console_enabled']:
                console_handler = self._get_console_handler()
                logger.addHandler(console_handler)

            if self.config['file_enabled']:
                file_handler = self._get_file_handler(name)
                logger.addHandler(file_handler)

        # ✅ ACTIVER propagation pour que les logs remontent au root_logger
        # Cela permet d'écrire dans le fichier configuré au niveau root
        logger.propagate = True

        # Stockage
        self.loggers[name] = logger

        return logger

    def _get_console_handler(self) -> logging.Handler:
        """Handler console avec UTF-8"""
        if 'console' not in self.handlers:
            handler = logging.StreamHandler(sys.stdout)

            # Formatter UTF-8
            remove_emojis = sys.platform == "win32" and not self._check_emoji_support()
            formatter = UTF8Formatter(
                FORMATS[self.config['format_type']],
                remove_emojis=remove_emojis
            )
            handler.setFormatter(formatter)

            # Niveau
            handler.setLevel(LOG_LEVELS[self.config['log_level']])

            self.handlers['console'] = handler

        return self.handlers['console']

    def _get_file_handler(self, logger_name: str) -> logging.Handler:
        """Handler fichier avec rotation"""
        handler_key = f'file_{logger_name}'

        if handler_key not in self.handlers:
            # Nom fichier basé sur date et logger
            today = datetime.now(timezone.utc).strftime('%Y%m%d')
            log_file = self.log_dir / f"{logger_name}_{today}.log"

            # Handler avec rotation
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config['max_bytes'],
                backupCount=self.config['backup_count'],
                encoding=self.config['encoding']
            )

            # Formatter (pas d'emojis dans fichiers)
            formatter = UTF8Formatter(FORMATS['file'], remove_emojis=True)
            handler.setFormatter(formatter)

            # Niveau
            handler.setLevel(LOG_LEVELS[self.config['log_level']])

            self.handlers[handler_key] = handler

        return self.handlers[handler_key]

    def _check_emoji_support(self) -> bool:
        """Vérifier support emojis dans terminal"""
        try:
            # Test écriture emoji
            test_emoji = "🚀"
            sys.stdout.write(test_emoji)
            sys.stdout.flush()
            return True
        except:
            return False

    def update_config(self, **kwargs):
        """Mise à jour configuration"""
        self.config.update(kwargs)

        # Reconfiguration loggers existants
        for logger in self.loggers.values():
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

            if self.config['console_enabled']:
                logger.addHandler(self._get_console_handler())

            if self.config['file_enabled']:
                logger.addHandler(self._get_file_handler(logger.name))

    def enable_trading_audit(self, logger_name: str = None):
        """Activer le format JSON pour l'audit des décisions de trading"""
        if logger_name:
            # Logger spécifique
            if logger_name in self.loggers:
                logger = self.loggers[logger_name]
                # Remplacer le formatter du handler fichier
                for handler in logger.handlers:
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        handler.setFormatter(TradingJSONFormatter())
        else:
            # Tous les loggers
            for logger in self.loggers.values():
                for handler in logger.handlers:
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        handler.setFormatter(TradingJSONFormatter())

# === FONCTIONS PUBLIQUES ===

def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Obtenir un logger configuré

    Args:
        name: Nom du logger (généralement __name__)
        **kwargs: Options additionnelles

    Returns:
        Logger configuré avec UTF-8

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("🚀 Starting system...")
    """
    manager = LoggerManager()
    return manager.get_logger(name, **kwargs)

def setup_logging(config: Optional[Dict[str, Any]] = None):
    """
    Configuration globale du logging

    Args:
        config: Configuration personnalisée

    Example:
        >>> setup_logging({
        ...     'log_level': 'DEBUG',
        ...     'file_enabled': True,
        ...     'log_dir': 'logs/debug'
        ... })
    """
    manager = LoggerManager()
    if config:
        manager.update_config(**config)

def get_logger_config() -> Dict[str, Any]:
    """Obtenir configuration actuelle"""
    manager = LoggerManager()
    return manager.config.copy()

def enable_trading_audit_logging(logger_name: str = None):
    """
    Activer le format JSON pour l'audit des décisions de trading

    Args:
        logger_name: Nom du logger spécifique (optionnel, tous si None)

    Example:
        >>> enable_trading_audit_logging('core.menthorq_distance_trading')
        >>> logger = get_logger('core.menthorq_distance_trading')
        >>> logger.info("Signal généré", extra={
        ...     'method': 'MenthorQ_First',
        ...     'vix_regime': 'MID',
        ...     'signal_type': 'GO_SHORT',
        ...     'level_price': 4500.25,
        ...     'final_score': 0.614
        ... })
    """
    manager = LoggerManager()
    manager.enable_trading_audit(logger_name)

def test_logging():
    """Test du système de logging"""
    logger = get_logger('test')

    logger.debug("Debug message - Détails techniques")
    logger.info("🚀 Info message - Démarrage système")
    logger.warning("⚠️ Warning message - Attention requise")
    logger.error("❌ Error message - Erreur détectée")
    logger.critical("🚨 Critical message - Erreur critique!")

    # Test avec données complexes
    test_data = {
        'price': 4500.25,
        'signal': 'LONG',
        'confidence': 0.85,
        'emojis': '📈 📊 💰'
    }
    logger.info(f"Test données: {test_data}")

# === EXPORTS ===

__all__ = [
    'get_logger',
    'setup_logging',
    'get_logger_config',
    'enable_trading_audit_logging',
    'LoggerManager',
    'UTF8Formatter',
    'TradingJSONFormatter',
    'LOG_LEVELS',
    'FORMATS'
]

# === CONFIGURATION AUTOMATIQUE ===

# Si exécuté directement ou première importation
if __name__ == "__main__" or not hasattr(sys.modules[__name__], '_initialized'):
    # Marquer comme initialisé
    sys.modules[__name__]._initialized = True

    # Configuration de base (console activée par défaut)
    setup_logging({
        'console_enabled': True,  # ✅ RÉACTIVÉ: Logs dans terminal ET fichiers
        'file_enabled': True
    })

    # Log de démarrage
    logger = get_logger('core.logger')
    logger.info("🚀 Core Logger System initialized with UTF-8 support")

# === TEST SI EXÉCUTÉ DIRECTEMENT ===

if __name__ == "__main__":
    print("\n=== MIA_IA_SYSTEM Core Logger Test ===\n")

    test_logging()

    print("\n✅ Logger system ready!")
    print(f"📁 Log directory: {LoggerManager().log_dir}")
    print(f"🔧 Configuration: {get_logger_config()}")
