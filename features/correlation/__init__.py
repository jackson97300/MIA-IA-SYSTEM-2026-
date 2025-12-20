"""
🔗 Module Corrélation ES/NQ
===========================

Analyse la corrélation entre ES et NQ pour :
- Confirmer les signaux
- Détecter les divergences
- Identifier le leader

Usage:
    from features.correlation import ESNQCorrelationModule

    module = ESNQCorrelationModule()
    result = module.update(es_snapshot, nq_snapshot)

    if result.confirmation_signal:
        print("Signal confirmé!")
    if result.divergence_warning:
        print("Attention: divergence détectée!")
"""

from .es_nq_correlation import (
    ESNQCorrelationModule,
    CorrelationResult,
    CorrelationSnapshot,
    CorrelationStats,
    analyze_correlation_from_files,
    CORRELATION_THRESHOLDS,
    CONFIRMATION_THRESHOLDS
)

__all__ = [
    'ESNQCorrelationModule',
    'CorrelationResult',
    'CorrelationSnapshot',
    'CorrelationStats',
    'analyze_correlation_from_files',
    'CORRELATION_THRESHOLDS',
    'CONFIRMATION_THRESHOLDS'
]
