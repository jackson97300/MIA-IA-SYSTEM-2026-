"""
Target Optimization System - ML Target Comparator

Ce module permet de tester plusieurs définitions de target ML
et de sélectionner celle qui maximise le P&L net en production.

Approche:
- Garde features identiques (MenthorQ + OrderFlow)
- Teste 8 targets différentes (binary, regression, multiclass)
- Backteste out-of-sample pour chaque target
- Sélectionne la target avec meilleur P&L net

Auteur: MIA Trading System
Date: 15 novembre 2025
"""

from .target_optimizer import (
    TargetConfig,
    TargetResult,
    TargetOptimizer,
    ALL_TARGETS
)

__version__ = "1.0.0"
__all__ = [
    "TargetConfig",
    "TargetResult",
    "TargetOptimizer",
    "ALL_TARGETS"
]







