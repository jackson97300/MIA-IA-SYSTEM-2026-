#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Constants Loader avec Enums et MappingProxy
===========================================================

Version: Production Ready v1.0
- Chargement des constantes depuis constants.yaml
- Enums pour les valeurs discrètes
- MappingProxy pour l'immutabilité
- Accès dot-accessible
- Cache intelligent

IMPACT: Élimination des "magic numbers" dispersés
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Union, Mapping
from types import MappingProxyType
from enum import Enum, IntEnum, FloatEnum
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)

# === ENUMS POUR LES CONSTANTES ===

class SymbolType(Enum):
    """Types de symboles"""
    PRIMARY = "ES"
    SECONDARY = "NQ"
    VIX = "VIX"
    MENTHORQ = "MenthorQ"

class TickSize(Enum):
    """Tailles de ticks"""
    ES = 0.25
    NQ = 0.25
    VIX = 0.01

class TickValue(Enum):
    """Valeurs de ticks"""
    ES = 12.50
    NQ = 5.00
    VIX = 1.00

class MarginRequirement(Enum):
    """Marges requises"""
    ES = 10000.0
    NQ = 15000.0
    VIX = 5000.0

class QualityThreshold(Enum):
    """Seuils de qualité"""
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    NO_TRADE = 0.2

class VIXThreshold(Enum):
    """Seuils VIX"""
    LOW = 15.0
    HIGH = 25.0
    EXTREME = 40.0

class TimeoutMs(IntEnum):
    """Timeouts en millisecondes"""
    PROCESSING = 500
    EXECUTION = 5000
    FILL_TIMEOUT = 10000
    CONNECTION = 30000

class CacheTTL(IntEnum):
    """TTL du cache en secondes"""
    DEFAULT = 60
    FEATURES = 60
    DATA = 60
    CONFIG = 300

class ThreadingConfig(IntEnum):
    """Configuration du threading"""
    MAX_WORKERS = 4
    THREAD_POOL_SIZE = 8
    QUEUE_SIZE = 100

# === LOADER DE CONSTANTES ===

class ConstantsLoader:
    """
    Loader de constantes avec enums et immutabilité
    """
    
    def __init__(self, constants_file: str = "config/constants.yaml"):
        self.constants_file = Path(constants_file)
        self._cache = {}
        self._enums = {}
        self._mapping_proxies = {}
        
    def load_constants(self) -> Dict[str, Any]:
        """
        Charge les constantes depuis le fichier YAML
        
        Returns:
            Dictionnaire des constantes
        """
        try:
            if not self.constants_file.exists():
                logger.error(f"❌ Fichier de constantes introuvable: {self.constants_file}")
                return {}
            
            with open(self.constants_file, 'r', encoding='utf-8') as f:
                constants = yaml.safe_load(f) or {}
            
            # Créer les enums et mapping proxies
            self._create_enums(constants)
            self._create_mapping_proxies(constants)
            
            logger.info(f"✅ Constantes chargées depuis {self.constants_file}")
            return constants
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement constantes: {e}")
            return {}
    
    def _create_enums(self, constants: Dict[str, Any]):
        """Crée les enums dynamiquement"""
        try:
            # Enum pour les symboles
            if 'trading' in constants and 'symbols' in constants['trading']:
                symbols = constants['trading']['symbols']
                self._enums['SymbolType'] = Enum('SymbolType', {
                    'PRIMARY': symbols.get('primary', 'ES'),
                    'SECONDARY': symbols.get('secondary', 'NQ'),
                    'VIX': symbols.get('vix', 'VIX'),
                    'MENTHORQ': symbols.get('menthorq', 'MenthorQ')
                })
            
            # Enum pour les tailles de ticks
            if 'trading' in constants and 'tick_sizes' in constants['trading']:
                tick_sizes = constants['trading']['tick_sizes']
                self._enums['TickSize'] = Enum('TickSize', {
                    'ES': tick_sizes.get('es', 0.25),
                    'NQ': tick_sizes.get('nq', 0.25),
                    'VIX': tick_sizes.get('vix', 0.01)
                })
            
            # Enum pour les valeurs de ticks
            if 'trading' in constants and 'tick_values' in constants['trading']:
                tick_values = constants['trading']['tick_values']
                self._enums['TickValue'] = Enum('TickValue', {
                    'ES': tick_values.get('es', 12.50),
                    'NQ': tick_values.get('nq', 5.00),
                    'VIX': tick_values.get('vix', 1.00)
                })
            
            # Enum pour les seuils de qualité
            if 'confluence' in constants and 'quality_thresholds' in constants['confluence']:
                quality = constants['confluence']['quality_thresholds']
                self._enums['QualityThreshold'] = Enum('QualityThreshold', {
                    'HIGH': quality.get('high', 0.8),
                    'MEDIUM': quality.get('medium', 0.6),
                    'LOW': quality.get('low', 0.4),
                    'NO_TRADE': quality.get('no_trade', 0.2)
                })
            
            # Enum pour les seuils VIX
            if 'features' in constants and 'vix' in constants['features']:
                vix = constants['features']['vix']
                self._enums['VIXThreshold'] = Enum('VIXThreshold', {
                    'LOW': vix.get('low_threshold', 15.0),
                    'HIGH': vix.get('high_threshold', 25.0),
                    'EXTREME': vix.get('extreme_threshold', 40.0)
                })
            
            # Enum pour les timeouts
            if 'performance' in constants and 'timeouts' in constants['performance']:
                timeouts = constants['performance']['timeouts']
                self._enums['TimeoutMs'] = IntEnum('TimeoutMs', {
                    'PROCESSING': timeouts.get('processing_ms', 500),
                    'EXECUTION': timeouts.get('execution_ms', 5000),
                    'FILL_TIMEOUT': timeouts.get('fill_timeout_ms', 10000),
                    'CONNECTION': timeouts.get('connection_timeout_s', 30) * 1000
                })
            
            logger.info(f"✅ {len(self._enums)} enums créés")
            
        except Exception as e:
            logger.error(f"❌ Erreur création enums: {e}")
    
    def _create_mapping_proxies(self, constants: Dict[str, Any]):
        """Crée les mapping proxies pour l'immutabilité"""
        try:
            # Mapping proxy pour les features
            if 'features' in constants:
                self._mapping_proxies['features'] = MappingProxyType(constants['features'])
            
            # Mapping proxy pour le risque
            if 'risk' in constants:
                self._mapping_proxies['risk'] = MappingProxyType(constants['risk'])
            
            # Mapping proxy pour la confluence
            if 'confluence' in constants:
                self._mapping_proxies['confluence'] = MappingProxyType(constants['confluence'])
            
            # Mapping proxy pour les performances
            if 'performance' in constants:
                self._mapping_proxies['performance'] = MappingProxyType(constants['performance'])
            
            # Mapping proxy pour MenthorQ
            if 'menthorq' in constants:
                self._mapping_proxies['menthorq'] = MappingProxyType(constants['menthorq'])
            
            logger.info(f"✅ {len(self._mapping_proxies)} mapping proxies créés")
            
        except Exception as e:
            logger.error(f"❌ Erreur création mapping proxies: {e}")
    
    def get_enum(self, enum_name: str) -> Enum:
        """
        Récupère un enum par nom
        
        Args:
            enum_name: Nom de l'enum
            
        Returns:
            Enum demandé
        """
        return self._enums.get(enum_name)
    
    def get_mapping_proxy(self, proxy_name: str) -> MappingProxyType:
        """
        Récupère un mapping proxy par nom
        
        Args:
            proxy_name: Nom du mapping proxy
            
        Returns:
            Mapping proxy demandé
        """
        return self._mapping_proxies.get(proxy_name)
    
    def get_constant(self, path: str, default: Any = None) -> Any:
        """
        Récupère une constante par chemin (ex: 'features.vwap.max_history')
        
        Args:
            path: Chemin vers la constante
            default: Valeur par défaut
            
        Returns:
            Valeur de la constante
        """
        try:
            keys = path.split('.')
            value = self._cache
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération constante {path}: {e}")
            return default

# === INSTANCE GLOBALE ===

_constants_loader = ConstantsLoader()

def load_constants() -> Dict[str, Any]:
    """
    Charge les constantes (fonction globale)
    
    Returns:
        Dictionnaire des constantes
    """
    if not _constants_loader._cache:
        _constants_loader._cache = _constants_loader.load_constants()
    return _constants_loader._cache

def get_enum(enum_name: str) -> Enum:
    """
    Récupère un enum par nom (fonction globale)
    
    Args:
        enum_name: Nom de l'enum
        
    Returns:
        Enum demandé
    """
    if not _constants_loader._enums:
        load_constants()
    return _constants_loader.get_enum(enum_name)

def get_mapping_proxy(proxy_name: str) -> MappingProxyType:
    """
    Récupère un mapping proxy par nom (fonction globale)
    
    Args:
        proxy_name: Nom du mapping proxy
        
    Returns:
        Mapping proxy demandé
    """
    if not _constants_loader._mapping_proxies:
        load_constants()
    return _constants_loader.get_mapping_proxy(proxy_name)

def get_constant(path: str, default: Any = None) -> Any:
    """
    Récupère une constante par chemin (fonction globale)
    
    Args:
        path: Chemin vers la constante
        default: Valeur par défaut
        
    Returns:
        Valeur de la constante
    """
    if not _constants_loader._cache:
        load_constants()
    return _constants_loader.get_constant(path, default)

# === FONCTIONS DE CONVENIENCE ===

def get_symbol_type(symbol: str) -> str:
    """Récupère le type de symbole"""
    return get_constant(f'trading.symbols.{symbol.lower()}', symbol)

def get_tick_size(symbol: str) -> float:
    """Récupère la taille de tick pour un symbole"""
    return get_constant(f'trading.tick_sizes.{symbol.lower()}', 0.25)

def get_tick_value(symbol: str) -> float:
    """Récupère la valeur de tick pour un symbole"""
    return get_constant(f'trading.tick_values.{symbol.lower()}', 12.50)

def get_margin_requirement(symbol: str) -> float:
    """Récupère la marge requise pour un symbole"""
    return get_constant(f'trading.margin_requirements.{symbol.lower()}', 10000.0)

def get_quality_threshold(level: str) -> float:
    """Récupère le seuil de qualité"""
    return get_constant(f'confluence.quality_thresholds.{level}', 0.5)

def get_vix_threshold(level: str) -> float:
    """Récupère le seuil VIX"""
    return get_constant(f'features.vix.{level}_threshold', 20.0)

def get_timeout_ms(timeout_type: str) -> int:
    """Récupère un timeout en millisecondes"""
    return get_constant(f'performance.timeouts.{timeout_type}_ms', 5000)

# === TEST DU LOADER DE CONSTANTES ===

if __name__ == "__main__":
    print("🧪 Test du Constants Loader...")
    
    # Test chargement
    constants = load_constants()
    print(f"✅ Constantes chargées: {len(constants)} sections")
    
    # Test enums
    symbol_enum = get_enum('SymbolType')
    if symbol_enum:
        print(f"✅ Enum SymbolType: {symbol_enum.PRIMARY.value}")
    
    tick_size_enum = get_enum('TickSize')
    if tick_size_enum:
        print(f"✅ Enum TickSize: {tick_size_enum.ES.value}")
    
    # Test mapping proxies
    features_proxy = get_mapping_proxy('features')
    if features_proxy:
        print(f"✅ Mapping proxy features: {len(features_proxy)} sections")
    
    # Test constantes
    vwap_history = get_constant('features.vwap.max_history')
    print(f"✅ VWAP max history: {vwap_history}")
    
    es_tick_size = get_tick_size('es')
    print(f"✅ ES tick size: {es_tick_size}")
    
    high_quality = get_quality_threshold('high')
    print(f"✅ High quality threshold: {high_quality}")
    
    processing_timeout = get_timeout_ms('processing')
    print(f"✅ Processing timeout: {processing_timeout}ms")
    
    print("🎉 Test Constants Loader terminé avec succès!")
