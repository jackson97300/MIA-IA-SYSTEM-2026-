#!/usr/bin/env python3
"""
MIA IA System - Confluence Configuration
Version: 3.0.0
Date: 2025-01-27

Configuration centralisée pour le système de confluence
Intègre MenthorQ, Advanced Features et Leadership
"""

from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class ConfluenceThresholds:
    """Seuils de confluence"""
    # Seuils de base
    MIN_CONFLUENCE_SCORE: float = 0.6
    STRONG_CONFLUENCE_SCORE: float = 0.8
    VERY_STRONG_CONFLUENCE_SCORE: float = 0.9
    
    # Seuils MenthorQ
    MENTHORQ_STRONG_THRESHOLD: float = 0.7
    MENTHORQ_MODERATE_THRESHOLD: float = 0.4
    
    # Seuils Advanced Features
    ADVANCED_FEATURES_STRONG_THRESHOLD: float = 0.6
    ADVANCED_FEATURES_MODERATE_THRESHOLD: float = 0.3
    
    # Seuils Leadership
    LEADERSHIP_STRONG_THRESHOLD: float = 0.8
    LEADERSHIP_MODERATE_THRESHOLD: float = 0.5

@dataclass
class ConfluenceWeights:
    """Pondérations des composants de confluence"""
    # Composants de base
    MTF_CONFLUENCE_WEIGHT: float = 0.16
    SMART_MONEY_WEIGHT: float = 0.12
    ORDER_BOOK_WEIGHT: float = 0.10
    VOLUME_PROFILE_WEIGHT: float = 0.10
    VWAP_WEIGHT: float = 0.06
    VIX_WEIGHT: float = 0.06
    NBCV_WEIGHT: float = 0.03
    
    # Composants avancés
    MENTHORQ_WEIGHT: float = 0.14
    ADVANCED_FEATURES_WEIGHT: float = 0.09
    LEADERSHIP_WEIGHT: float = 0.10

@dataclass
class ConfluenceMultipliers:
    """Multiplicateurs de confluence"""
    # Multiplicateurs MenthorQ
    MENTHORQ_STRONG_MULTIPLIER: float = 1.5
    MENTHORQ_MODERATE_MULTIPLIER: float = 1.2
    MENTHORQ_WEAK_MULTIPLIER: float = 1.0
    
    # Multiplicateurs Advanced Features
    ADVANCED_FEATURES_STRONG_MULTIPLIER: float = 1.3
    ADVANCED_FEATURES_MODERATE_MULTIPLIER: float = 1.1
    ADVANCED_FEATURES_WEAK_MULTIPLIER: float = 1.0
    
    # Multiplicateurs Leadership
    LEADERSHIP_STRONG_MULTIPLIER: float = 1.4
    LEADERSHIP_MODERATE_MULTIPLIER: float = 1.1
    LEADERSHIP_WEAK_MULTIPLIER: float = 1.0

@dataclass
class ConfluenceSettings:
    """Paramètres de confluence"""
    # Général
    ENABLE_MENTHORQ: bool = True
    ENABLE_ADVANCED_FEATURES: bool = True
    ENABLE_LEADERSHIP: bool = True
    
    # Calculs
    USE_WEIGHTED_AVERAGE: bool = True
    USE_MULTIPLIERS: bool = True
    USE_RISK_ADJUSTMENT: bool = True
    
    # Validation
    REQUIRE_MINIMUM_COMPONENTS: int = 3
    MAX_CONFLUENCE_SCORE: float = 1.0
    MIN_CONFLUENCE_SCORE: float = 0.0

@dataclass
class ConfluenceConfig:
    """Configuration complète de confluence"""
    thresholds: ConfluenceThresholds
    weights: ConfluenceWeights
    multipliers: ConfluenceMultipliers
    settings: ConfluenceSettings
    
    def __post_init__(self):
        """Validation post-initialisation"""
        # Validation des seuils
        assert 0.0 <= self.thresholds.MIN_CONFLUENCE_SCORE <= 1.0
        assert 0.0 <= self.thresholds.STRONG_CONFLUENCE_SCORE <= 1.0
        assert 0.0 <= self.thresholds.VERY_STRONG_CONFLUENCE_SCORE <= 1.0
        
        # Validation des pondérations
        total_weight = (
            self.weights.MTF_CONFLUENCE_WEIGHT +
            self.weights.SMART_MONEY_WEIGHT +
            self.weights.ORDER_BOOK_WEIGHT +
            self.weights.VOLUME_PROFILE_WEIGHT +
            self.weights.VWAP_WEIGHT +
            self.weights.VIX_WEIGHT +
            self.weights.NBCV_WEIGHT +
            self.weights.MENTHORQ_WEIGHT +
            self.weights.ADVANCED_FEATURES_WEIGHT +
            self.weights.LEADERSHIP_WEIGHT
        )
        assert abs(total_weight - 1.0) < 0.01, f"Pondérations doivent totaliser 1.0, actuel: {total_weight}"
        
        # Validation des multiplicateurs
        assert self.multipliers.MENTHORQ_STRONG_MULTIPLIER > 1.0
        assert self.multipliers.ADVANCED_FEATURES_STRONG_MULTIPLIER > 1.0
        assert self.multipliers.LEADERSHIP_STRONG_MULTIPLIER > 1.0

# Configuration par défaut
DEFAULT_CONFLUENCE_CONFIG = ConfluenceConfig(
    thresholds=ConfluenceThresholds(),
    weights=ConfluenceWeights(),
    multipliers=ConfluenceMultipliers(),
    settings=ConfluenceSettings()
)

# Configuration optimisée pour la production
PRODUCTION_CONFLUENCE_CONFIG = ConfluenceConfig(
    thresholds=ConfluenceThresholds(
        MIN_CONFLUENCE_SCORE=0.65,
        STRONG_CONFLUENCE_SCORE=0.85,
        VERY_STRONG_CONFLUENCE_SCORE=0.95,
        MENTHORQ_STRONG_THRESHOLD=0.75,
        MENTHORQ_MODERATE_THRESHOLD=0.45,
        ADVANCED_FEATURES_STRONG_THRESHOLD=0.65,
        ADVANCED_FEATURES_MODERATE_THRESHOLD=0.35,
        LEADERSHIP_STRONG_THRESHOLD=0.85,
        LEADERSHIP_MODERATE_THRESHOLD=0.55
    ),
    weights=ConfluenceWeights(
        MTF_CONFLUENCE_WEIGHT=0.14,
        SMART_MONEY_WEIGHT=0.11,
        ORDER_BOOK_WEIGHT=0.09,
        VOLUME_PROFILE_WEIGHT=0.09,
        VWAP_WEIGHT=0.05,
        VIX_WEIGHT=0.05,
        NBCV_WEIGHT=0.03,
        MENTHORQ_WEIGHT=0.15,
        ADVANCED_FEATURES_WEIGHT=0.10,
        LEADERSHIP_WEIGHT=0.11
    ),
    multipliers=ConfluenceMultipliers(
        MENTHORQ_STRONG_MULTIPLIER=1.6,
        MENTHORQ_MODERATE_MULTIPLIER=1.25,
        MENTHORQ_WEAK_MULTIPLIER=1.0,
        ADVANCED_FEATURES_STRONG_MULTIPLIER=1.35,
        ADVANCED_FEATURES_MODERATE_MULTIPLIER=1.15,
        ADVANCED_FEATURES_WEAK_MULTIPLIER=1.0,
        LEADERSHIP_STRONG_MULTIPLIER=1.45,
        LEADERSHIP_MODERATE_MULTIPLIER=1.15,
        LEADERSHIP_WEAK_MULTIPLIER=1.0
    ),
    settings=ConfluenceSettings(
        ENABLE_MENTHORQ=True,
        ENABLE_ADVANCED_FEATURES=True,
        ENABLE_LEADERSHIP=True,
        USE_WEIGHTED_AVERAGE=True,
        USE_MULTIPLIERS=True,
        USE_RISK_ADJUSTMENT=True,
        REQUIRE_MINIMUM_COMPONENTS=4,
        MAX_CONFLUENCE_SCORE=1.0,
        MIN_CONFLUENCE_SCORE=0.0
    )
)

# Configuration de test
TEST_CONFLUENCE_CONFIG = ConfluenceConfig(
    thresholds=ConfluenceThresholds(
        MIN_CONFLUENCE_SCORE=0.5,
        STRONG_CONFLUENCE_SCORE=0.7,
        VERY_STRONG_CONFLUENCE_SCORE=0.8
    ),
    weights=ConfluenceWeights(
        MTF_CONFLUENCE_WEIGHT=0.3,
        SMART_MONEY_WEIGHT=0.2,
        ORDER_BOOK_WEIGHT=0.15,
        VOLUME_PROFILE_WEIGHT=0.15,
        VWAP_WEIGHT=0.1,
        VIX_WEIGHT=0.1,
        NBCV_WEIGHT=0.0,
        MENTHORQ_WEIGHT=0.0,
        ADVANCED_FEATURES_WEIGHT=0.0,
        LEADERSHIP_WEIGHT=0.0
    ),
    multipliers=ConfluenceMultipliers(),
    settings=ConfluenceSettings(
        ENABLE_MENTHORQ=False,
        ENABLE_ADVANCED_FEATURES=False,
        ENABLE_LEADERSHIP=False,
        REQUIRE_MINIMUM_COMPONENTS=2
    )
)

# Fonction pour obtenir la configuration active
def get_confluence_config(environment: str = "production") -> ConfluenceConfig:
    """Récupère la configuration de confluence selon l'environnement"""
    configs = {
        "production": PRODUCTION_CONFLUENCE_CONFIG,
        "development": DEFAULT_CONFLUENCE_CONFIG,
        "test": TEST_CONFLUENCE_CONFIG
    }
    
    return configs.get(environment, DEFAULT_CONFLUENCE_CONFIG)

# Fonction pour valider une configuration
def validate_confluence_config(config: ConfluenceConfig) -> bool:
    """Valide une configuration de confluence"""
    try:
        # Validation des seuils
        if not (0.0 <= config.thresholds.MIN_CONFLUENCE_SCORE <= 1.0):
            return False
        if not (0.0 <= config.thresholds.STRONG_CONFLUENCE_SCORE <= 1.0):
            return False
        if not (0.0 <= config.thresholds.VERY_STRONG_CONFLUENCE_SCORE <= 1.0):
            return False
            
        # Validation des pondérations
        total_weight = (
            config.weights.MTF_CONFLUENCE_WEIGHT +
            config.weights.SMART_MONEY_WEIGHT +
            config.weights.ORDER_BOOK_WEIGHT +
            config.weights.VOLUME_PROFILE_WEIGHT +
            config.weights.VWAP_WEIGHT +
            config.weights.VIX_WEIGHT +
            config.weights.NBCV_WEIGHT +
            config.weights.MENTHORQ_WEIGHT +
            config.weights.ADVANCED_FEATURES_WEIGHT +
            config.weights.LEADERSHIP_WEIGHT
        )
        if abs(total_weight - 1.0) > 0.01:
            return False
            
        return True
        
    except Exception:
        return False

if __name__ == "__main__":
    # Test de la configuration
    print("🔧 Test de la configuration de confluence...")
    
    # Test configuration par défaut
    default_config = get_confluence_config("development")
    print(f"✅ Configuration par défaut: {type(default_config).__name__}")
    
    # Test configuration production
    prod_config = get_confluence_config("production")
    print(f"✅ Configuration production: {type(prod_config).__name__}")
    
    # Test validation
    is_valid = validate_confluence_config(prod_config)
    print(f"✅ Validation: {is_valid}")
    
    print("🎉 Test terminé avec succès!")
