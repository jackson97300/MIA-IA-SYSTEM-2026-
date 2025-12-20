"""
Logger Structuré MIA_IA_SYSTEM
==============================

Système de logging structuré avec JSON et métriques intégrées.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory

from core.logger import get_logger as get_base_logger
from .metrics_collector import get_metrics_collector

# Configuration structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


class StructuredLogger:
    """Logger structuré avec métriques intégrées"""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = structlog.get_logger(name)
        self.metrics = get_metrics_collector()

        # Configuration
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_file = self.config.get('log_file')
        self.enable_metrics = self.config.get('enable_metrics', True)

        # Setup du handler
        self._setup_handlers()

        # Compteurs de logs
        self.log_counts = {
            'DEBUG': 0,
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'CRITICAL': 0
        }

    def _setup_handlers(self):
        """Configure les handlers de logging"""
        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))

        # Handler fichier (si configuré)
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(getattr(logging, self.log_level))

            # Créer le dossier si nécessaire
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

        # Formatter JSON pour fichier
        json_formatter = logging.Formatter(
            '%(message)s'  # structlog gère déjà le formatage JSON
        )

        # Formatter console (plus lisible)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        console_handler.setFormatter(console_formatter)
        if self.log_file:
            file_handler.setFormatter(json_formatter)

        # Configurer le logger
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.log_level))
        logger.addHandler(console_handler)

        if self.log_file:
            logger.addHandler(file_handler)

    def _log_with_metrics(self, level: str, message: str, **kwargs):
        """Log avec métriques intégrées"""
        # Incrémenter le compteur
        self.log_counts[level] += 1

        # Enregistrer la métrique
        if self.enable_metrics:
            self.metrics.increment_counter(
                'logs_generated',
                labels={'level': level, 'logger': self.name}
            )

        # Log structuré
        log_data = {
            'message': message,
            'logger': self.name,
            'level': level,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **kwargs
        }

        # Envoyer au logger
        getattr(self.logger, level.lower())(**log_data)

    def debug(self, message: str, **kwargs):
        """Log debug"""
        self._log_with_metrics('DEBUG', message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info"""
        self._log_with_metrics('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning"""
        self._log_with_metrics('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error"""
        self._log_with_metrics('ERROR', message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical"""
        self._log_with_metrics('CRITICAL', message, **kwargs)

    # === MÉTHODES SPÉCIALISÉES ===

    def log_signal(self, strategy: str, side: str, confidence: float, **kwargs):
        """Log spécialisé pour les signaux"""
        self.info(
            f"Signal généré: {strategy} {side}",
            strategy=strategy,
            side=side,
            confidence=confidence,
            event_type='signal_generated',
            **kwargs
        )
        # Note: un seul log info ici pour compatibilité tests observabilité

        # Métrique spécialisée
        if self.enable_metrics:
            self.metrics.record_signal_generated(strategy, side, confidence)

    def log_trade(self, strategy: str, side: str, result: str, pnl: float, **kwargs):
        """Log spécialisé pour les trades"""
        self.info(
            f"Trade exécuté: {strategy} {side} {result}",
            strategy=strategy,
            side=side,
            result=result,
            pnl=pnl,
            event_type='trade_executed',
            **kwargs
        )
        # Note: un seul log info ici pour compatibilité tests observabilité

        # Métrique spécialisée
        if self.enable_metrics:
            self.metrics.record_trade_executed(strategy, side, result, pnl)

    def log_kill_switch(self, reason: str, state: str, **kwargs):
        """Log spécialisé pour le kill switch"""
        self.warning(
            f"Kill switch activé: {reason}",
            reason=reason,
            state=state,
            event_type='kill_switch_activation',
            **kwargs
        )
        # Info complémentaire pour intégration (sans double-compter la métrique)
        self.info(
            f"Kill switch consigné: {reason}",
            reason=reason,
            state=state,
            event_type='kill_switch_recorded',
            **kwargs
        )
        # Métrique spécialisée (déduplication gérée côté MetricsCollector)
        if self.enable_metrics:
            try:
                self.metrics.record_kill_switch_activation(reason)
            except Exception:
                pass

    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log spécialisé pour les performances"""
        self.info(
            f"Performance: {operation} took {duration:.3f}s",
            operation=operation,
            duration=duration,
            event_type='performance',
            **kwargs
        )

        # Métrique spécialisée
        if self.enable_metrics:
            self.metrics.record_processing_time(operation, duration)

    def log_data_quality(self, source: str, latency: float, stale: bool, **kwargs):
        """Log spécialisé pour la qualité des données"""
        level = 'WARNING' if stale else 'INFO'
        message = f"Data quality: {source} latency={latency:.3f}s stale={stale}"

        self._log_with_metrics(
            level,
            message,
            source=source,
            latency=latency,
            stale=stale,
            event_type='data_quality',
            **kwargs
        )

        # Métrique spécialisée
        if self.enable_metrics:
            self.metrics.update_data_latency(source, latency)

    def log_system_health(self, component: str, health: float, **kwargs):
        """Log spécialisé pour la santé du système"""
        level = 'ERROR' if health < 0.5 else 'WARNING' if health < 0.8 else 'INFO'
        message = f"System health: {component} = {health:.2f}"

        self._log_with_metrics(
            level,
            message,
            component=component,
            health=health,
            event_type='system_health',
            **kwargs
        )

        # Métrique spécialisée
        if self.enable_metrics:
            self.metrics.update_system_health(component, health)

    def get_log_counts(self) -> Dict[str, int]:
        """Retourne les compteurs de logs"""
        return self.log_counts.copy()

    def reset_log_counts(self):
        """Remet à zéro les compteurs de logs"""
        self.log_counts = {level: 0 for level in self.log_counts}


# === FONCTIONS UTILITAIRES ===

def get_structured_logger(name: str, config: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """Retourne un logger structuré"""
    return StructuredLogger(name, config)


def setup_structured_logging(config: Optional[Dict[str, Any]] = None):
    """Configure le logging structuré global"""
    config = config or {}

    # Configuration globale
    log_level = config.get('log_level', 'INFO')
    log_dir = config.get('log_dir', 'logs')

    # Créer le dossier de logs
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Configuration des loggers principaux
    loggers_config = {
        'mia_ia_system': {
            'log_file': f'{log_dir}/system.log',
            'log_level': log_level,
            'enable_metrics': True
        },
        'mia_ia_system.trading': {
            'log_file': f'{log_dir}/trading.log',
            'log_level': log_level,
            'enable_metrics': True
        },
        'mia_ia_system.collector': {
            'log_file': f'{log_dir}/collector.log',
            'log_level': log_level,
            'enable_metrics': True
        },
        'mia_ia_system.safety': {
            'log_file': f'{log_dir}/safety.log',
            'log_level': log_level,
            'enable_metrics': True
        }
    }

    # Créer les loggers
    loggers = {}
    for name, logger_config in loggers_config.items():
        loggers[name] = get_structured_logger(name, logger_config)

    return loggers


# === CONTEXTE MANAGER ===

class LogContext:
    """Contexte de logging avec métriques automatiques"""

    def __init__(self, logger: StructuredLogger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now(timezone.utc)
        self.logger.info(
            f"Début: {self.operation}",
            operation=self.operation,
            event_type='operation_start',
            **self.context
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.log_performance(self.operation, duration, **self.context)
        else:
            self.logger.error(
                f"Erreur: {self.operation}",
                operation=self.operation,
                duration=duration,
                error=str(exc_val),
                event_type='operation_error',
                **self.context
            )


def log_context(logger: StructuredLogger, operation: str, **context):
    """Décorateur de contexte de logging"""
    return LogContext(logger, operation, **context)
