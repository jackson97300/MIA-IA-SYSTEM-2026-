"""
Strategies module pour MIA_IA_SYSTEM
"""

from core.logger import get_logger

logger = get_logger(__name__)

# Safe imports
__all__ = []

def get_signal_now(market_data):
    """Fonction helper pour obtenir un signal rapidement"""
    try:
        from .signal_generator import create_signal_generator
        generator = create_signal_generator()
        return generator.generate_signal(market_data)  # Correction: generate_signal au lieu de get_signal
    except Exception as e:
        logger.error(f"Error getting signal: {e}")
        return None

# Import SignalGenerator et ses classes associées
try:
    from .signal_generator import (
        SignalGenerator, 
        create_signal_generator,
        SignalDecision,  # <-- AJOUT IMPORTANT
        SignalSource,    # <-- AJOUT OPTIONNEL
        QualityLevel,    # <-- AJOUT OPTIONNEL
        FinalSignal,     # <-- AJOUT OPTIONNEL
        SignalComponents # <-- AJOUT OPTIONNEL
    )
    __all__.extend([
        'SignalGenerator', 
        'create_signal_generator',
        'SignalDecision',
        'SignalSource',
        'QualityLevel',
        'FinalSignal',
        'SignalComponents'
    ])
except ImportError as e:
    logger.debug(f"[SKIP] signal_generator: {e}")  # ✅ Changed to debug

# Import TrendStrategy
try:
    from .trend_strategy import TrendStrategy, create_trend_strategy
    __all__.extend(['TrendStrategy', 'create_trend_strategy'])
except ImportError as e:
    logger.debug(f"[SKIP] trend_strategy: {e}")  # ✅ Changed to debug

# Import RangeStrategy
try:
    from .range_strategy import RangeStrategy, create_range_strategy
    __all__.extend(['RangeStrategy', 'create_range_strategy'])
except ImportError as e:
    logger.debug(f"[SKIP] range_strategy: {e}")  # ✅ Changed to debug

# Import StrategySelector
try:
    from .strategy_selector import StrategySelector, create_strategy_selector
    __all__.extend(['StrategySelector', 'create_strategy_selector'])
except ImportError as e:
    logger.debug(f"[SKIP] strategy_selector: {e}")  # ✅ Changed to debug

# Ajout de get_signal_now à __all__
__all__.append('get_signal_now')