# -*- coding: utf-8 -*-
"""
Signal Explainer - Wrapper pour compatibilité
Redirige vers signal_explainer_ml_ready.py
"""

# Import depuis la version ML Ready
from .signal_explainer_ml_ready import SignalExplainerMLReady

# Alias pour compatibilité
SignalExplainer = SignalExplainerMLReady

def create_signal_explainer(*args, **kwargs):
    """Factory function pour créer un SignalExplainer"""
    return SignalExplainerMLReady(*args, **kwargs)

__all__ = ['SignalExplainer', 'SignalExplainerMLReady', 'create_signal_explainer']
