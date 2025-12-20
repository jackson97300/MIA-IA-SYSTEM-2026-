"""
Configuration module pour MIA_IA_SYSTEM
"""

from core.logger import get_logger
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logger = get_logger(__name__)

# --- Initialisations explicites (évite les NameError) ---
TradingConfig = None
get_trading_config = None
get_feature_config = None

AutomationConfig = None
get_automation_config = None

MLConfig = None
get_ml_config = None

SierraConfig = None
get_sierra_config = None

# --- Imports try/except ---
try:
    from .trading_config import TradingConfig, get_trading_config, get_feature_config
    TRADING_CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import trading_config: {e}")
    TRADING_CONFIG_AVAILABLE = False
    TradingConfig = None
    get_trading_config = None
    get_feature_config = None

try:
    from .automation_config import AutomationConfig, get_automation_config
    AUTOMATION_CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import automation_config: {e}")
    AUTOMATION_CONFIG_AVAILABLE = False
    AutomationConfig = None
    get_automation_config = None

try:
    from .ml_config import MLConfig, get_ml_config
    ML_CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import ml_config: {e}")
    ML_CONFIG_AVAILABLE = False
    MLConfig = None
    get_ml_config = None

try:
    from .sierra_config import SierraConfig, get_sierra_config
    SIERRA_CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import sierra_config: {e}")
    SIERRA_CONFIG_AVAILABLE = False
    SierraConfig = None
    get_sierra_config = None

# --- Exports seulement les imports OK ---
__all__ = []

if TRADING_CONFIG_AVAILABLE:
    __all__.extend(['TradingConfig', 'get_trading_config', 'get_feature_config'])
if AUTOMATION_CONFIG_AVAILABLE:
    __all__.extend(['AutomationConfig', 'get_automation_config'])
if ML_CONFIG_AVAILABLE:
    __all__.extend(['MLConfig', 'get_ml_config'])
if SIERRA_CONFIG_AVAILABLE:
    __all__.extend(['SierraConfig', 'get_sierra_config'])

# --- Fonction helper pour vérifier disponibilité ---
def is_module_available(module_name: str) -> bool:
    """Vérifie si un module de configuration est disponible"""
    availability_map = {
        'trading_config': TRADING_CONFIG_AVAILABLE,
        'automation_config': AUTOMATION_CONFIG_AVAILABLE,
        'ml_config': ML_CONFIG_AVAILABLE,
        'sierra_config': SIERRA_CONFIG_AVAILABLE,
        # Vérification par nom de classe aussi
        'TradingConfig': TRADING_CONFIG_AVAILABLE,
        'AutomationConfig': AUTOMATION_CONFIG_AVAILABLE,
        'MLConfig': ML_CONFIG_AVAILABLE,
        'SierraConfig': SIERRA_CONFIG_AVAILABLE,
    }
    
    # Vérifier dans le mapping
    if module_name in availability_map:
        return availability_map[module_name]
    
    # Vérifier dans globals pour d'autres noms
    return module_name in globals() and globals()[module_name] is not None

# Export la fonction helper
__all__.append('is_module_available')

# --- Log résumé des imports réussis ---
successful_imports = []
if TRADING_CONFIG_AVAILABLE:
    successful_imports.append('trading_config')
if AUTOMATION_CONFIG_AVAILABLE:
    successful_imports.append('automation_config')
if ML_CONFIG_AVAILABLE:
    successful_imports.append('ml_config')
if SIERRA_CONFIG_AVAILABLE:
    successful_imports.append('sierra_config')

if successful_imports:
    logger.debug(f"Config module loaded successfully: {', '.join(successful_imports)}")
else:
    logger.error("No configuration modules could be loaded!")

# --- Configuration par défaut si aucun module disponible ---
def get_default_config() -> Dict[str, Any]:
    """Retourne une configuration minimale par défaut"""
    return {
        'mode': 'simulation',
        'data_directory': 'data',
        'logs_directory': 'logs',
        'snapshots_directory': 'data/snapshots',
        'environment': 'development',
        'daily_loss_limit': 1000.0,
        'max_positions': 1,
        'trading': {
            'enabled': False,
            'mode': 'simulation'
        }
    }

# Export la fonction de config par défaut
__all__.append('get_default_config')

# --- Wrapper functions pour éviter les erreurs ---
def safe_get_trading_config():
    """Wrapper sécurisé pour get_trading_config"""
    if TRADING_CONFIG_AVAILABLE and get_trading_config:
        return get_trading_config()
    else:
        logger.warning("Trading config not available, returning default config")
        return get_default_config()

def safe_get_automation_config():
    """Wrapper sécurisé pour get_automation_config"""
    if AUTOMATION_CONFIG_AVAILABLE and get_automation_config:
        return get_automation_config()
    else:
        logger.warning("Automation config not available, returning default config")
        return get_default_config()

def safe_get_sierra_config():
    """Wrapper sécurisé pour get_sierra_config"""
    if SIERRA_CONFIG_AVAILABLE and get_sierra_config:
        return get_sierra_config()
    else:
        logger.warning("Sierra config not available, returning None")
        return None

# Export les wrappers sécurisés
__all__.extend(['safe_get_trading_config', 'safe_get_automation_config', 'safe_get_sierra_config'])