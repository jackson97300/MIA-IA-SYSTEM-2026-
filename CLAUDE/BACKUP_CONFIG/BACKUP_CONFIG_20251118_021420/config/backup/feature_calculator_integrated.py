#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Feature Calculator INTÉGRÉ avec Optimisations
🎯 VERSION INTÉGRÉE: VWAP Bands + Volume Imbalance dans confluence principale
Version: Production Ready v4.0 - OPTIMISATIONS COMPLÈTES

NOUVELLES FEATURES INTÉGRÉES :
1. 📊 VWAP Bands (SD1, SD2) - 8% confluence weight
2. 💰 Volume Imbalance - 5% confluence weight
3. 🧠 Smart Money Enhanced - intégré

CONFLUENCE_WEIGHTS OPTIMISÉS (100% TOTAL) :
- gamma_levels_proximity: 22% (était 25%)
- volume_confirmation: 16% (était 18%)
- vwap_trend_signal: 13% (était 15%)
- sierra_pattern_strength: 13% (était 15%)
- mtf_confluence_score: 10% (était 12%)
- smart_money_strength: 8% (était 10%)
- order_book_imbalance: 3% (inchangé)
- options_flow_bias: 2% (inchangé)
- 🆕 vwap_bands_signal: 8% (NOUVEAU)
- 🆕 volume_imbalance_signal: 5% (NOUVEAU)

Author: MIA_IA_SYSTEM Team
Version: 4.0 - Production Ready
Date: Août 2025
"""

import time
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, OrderedDict
from core.logger import get_logger

# Import FeatureCalculator existant
try:
    from .feature_calculator import (
        FeatureCalculator as OriginalFeatureCalculator,
        FeatureCalculationResult,
        SignalQuality,
        TRADING_THRESHOLDS
    )
    ORIGINAL_CALCULATOR_AVAILABLE = True
except ImportError:
    ORIGINAL_CALCULATOR_AVAILABLE = False
    # Fallback enums
    class SignalQuality(Enum):
        PREMIUM = "premium"
        STRONG = "strong" 
        WEAK = "weak"
        NO_TRADE = "no_trade"

# Import nouvelles optimisations
try:
    from .vwap_bands_analyzer import (
        VWAPBandsAnalyzer,
        create_vwap_bands_analyzer,
        VWAPBandsData
    )
    VWAP_BANDS_AVAILABLE = True
except ImportError as e:
    VWAP_BANDS_AVAILABLE = False

try:
    from .volume_profile_imbalance import (
        VolumeProfileImbalanceDetector,
        create_volume_profile_imbalance_detector,
        VolumeProfileImbalanceResult
    )
    VOLUME_IMBALANCE_AVAILABLE = True
except ImportError:
    VOLUME_IMBALANCE_AVAILABLE = False

# Local imports
try:
    from core.base_types import MarketData, OrderFlowData, TradingFeatures
except ImportError:
    MarketData = Any
    OrderFlowData = Any
    TradingFeatures = Any

logger = get_logger(__name__)

# Log des imports après initialisation du logger
if VWAP_BANDS_AVAILABLE:
    logger.info("✅ VWAP Bands module importé avec succès")
else:
    logger.warning("❌ VWAP Bands module non disponible")

# === NOUVELLE CONFLUENCE WEIGHTS INTÉGRÉE ===

INTEGRATED_CONFLUENCE_WEIGHTS = {
    # Réduction proportionnelle pour faire place aux nouvelles features
    'gamma_levels_proximity': 0.22,      # 25% → 22% (-3%) - Options flow SpotGamma
    'volume_confirmation': 0.16,         # 18% → 16% (-2%) - Order flow + volume
    'vwap_trend_signal': 0.13,           # 15% → 13% (-2%) - VWAP slope + position
    'sierra_pattern_strength': 0.13,     # 15% → 13% (-2%) - Patterns tick reversal
    'mtf_confluence_score': 0.10,        # 12% → 10% (-2%) - TECHNIQUE #1 ELITE: MTF Confluence
    'smart_money_strength': 0.08,        # 10% → 8% (-2%) - TECHNIQUE #2 ELITE: Smart Money
    'order_book_imbalance': 0.03,        # 3% → 3% (inchangé) - Pression achat/vente
    'options_flow_bias': 0.02,           # 2% → 2% (inchangé) - Call/Put sentiment
    
    # ✅ NOUVELLES FEATURES INTÉGRÉES - OPTIMISATIONS
    'vwap_bands_signal': 0.08,           # 8% - VWAP Bands (SD1/SD2) zones de rejet
    'volume_imbalance_signal': 0.05,     # 5% - Volume Imbalance smart money detection
}

# Validation weights = 100%
assert abs(sum(INTEGRATED_CONFLUENCE_WEIGHTS.values()) - 1.0) < 0.001, \
    f"Weights must sum to 100%, got {sum(INTEGRATED_CONFLUENCE_WEIGHTS.values()):.3f}"

# === SEUILS TRADING OPTIMISÉS ===

OPTIMIZED_TRADING_THRESHOLDS = {
    'PREMIUM_SIGNAL': 0.38,    # 🔧 AJUSTÉ: 45% → 38% = Premium trade (size ×2.0)
    'STRONG_SIGNAL': 0.30,     # 🔧 AJUSTÉ: 35% → 30% = Strong trade (size ×1.5)
    'GOOD_SIGNAL': 0.25,       # 🔧 AJUSTÉ: 28% → 25% = Good trade (size ×1.0)
    'WEAK_SIGNAL': 0.18,       # 🔧 AJUSTÉ: 20% → 18% = Weak trade (size ×0.5)
    'NO_TRADE': 0.00,          # <18% = No trade (wait)
}

class OptimizedSignalQuality(Enum):
    """Qualité signal optimisée avec seuils OPTION 2"""
    PREMIUM = "premium"     # 38-100% - OPTION 2
    STRONG = "strong"       # 32-37%  - OPTION 2
    GOOD = "good"          # 28-31%  - OPTION 2
    WEAK = "weak"          # 18-27%  - OPTION 2
    NO_TRADE = "no_trade"  # 0-17%   - OPTION 2

# === ENHANCED RESULT DATACLASS ===

@dataclass
class IntegratedFeatureResult:
    """Résultat features avec optimisations intégrées dans confluence"""
    timestamp: pd.Timestamp
    
    # Features originales (0-1)
    gamma_levels_proximity: float = 0.0
    volume_confirmation: float = 0.0
    vwap_trend_signal: float = 0.0
    sierra_pattern_strength: float = 0.0
    mtf_confluence_score: float = 0.0
    smart_money_strength: float = 0.0
    order_book_imbalance: float = 0.0
    options_flow_bias: float = 0.0
    
    # 🆕 Nouvelles features optimisées (0-1)
    vwap_bands_signal: float = 0.0
    volume_imbalance_signal: float = 0.0
    
    # Scores finaux
    integrated_confluence_score: float = 0.0    # Score confluence intégré
    signal_quality: OptimizedSignalQuality = OptimizedSignalQuality.NO_TRADE
    position_multiplier: float = 0.0
    
    # Données brutes optimisations
    vwap_bands_data: Optional[VWAPBandsData] = None
    volume_imbalance_data: Optional[VolumeProfileImbalanceResult] = None
    
    # Performance
    calculation_time_ms: float = 0.0

# === MAIN INTEGRATED FEATURE CALCULATOR ===

class IntegratedFeatureCalculator:
    """
    Feature Calculator Intégré avec optimisations dans confluence principale
    
    INTÉGRATION COMPLÈTE :
    - VWAP Bands (8% weight) dans confluence
    - Volume Imbalance (5% weight) dans confluence  
    - Seuils trading optimisés
    - Performance <5ms garantie
    
    NOUVEAU SYSTÈME :
    Au lieu d'avoir confluence séparée + bonus, tout est intégré
    dans un seul score confluence de 0-100%
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation calculator intégré"""
        self.config = config or {}
        
        # FeatureCalculator original pour features existantes
        if ORIGINAL_CALCULATOR_AVAILABLE:
            self.original_calculator = OriginalFeatureCalculator(config)
            logger.info("✅ FeatureCalculator original chargé")
        else:
            self.original_calculator = None
            logger.warning("❌ FeatureCalculator original non disponible")
        
        # Nouvelles optimisations
        self.vwap_analyzer = None
        self.volume_imbalance_detector = None
        
        self._initialize_optimizations()
        
        # Cache et performance
        self.cache: OrderedDict = OrderedDict()
        self.cache_max_size = self.config.get('cache_size', 500)
        
        # Stats
        self.stats = {
            'calculations_count': 0,
            'avg_calc_time_ms': 0.0,
            'premium_signals_count': 0,
            'strong_signals_count': 0
        }
        
        logger.info(f"🚀 IntegratedFeatureCalculator initialisé - Features: {self._get_feature_count()}")
    
    def _initialize_optimizations(self):
        """Initialise les nouvelles optimisations"""
        
        # VWAP Bands Analyzer
        logger.info(f"🔍 DEBUG: VWAP_BANDS_AVAILABLE = {VWAP_BANDS_AVAILABLE}")
        if VWAP_BANDS_AVAILABLE:
            try:
                vwap_config = self.config.get('vwap_bands', {})
                self.vwap_analyzer = create_vwap_bands_analyzer(vwap_config)
                logger.info("✅ VWAP Bands Analyzer initialisé (8% confluence weight)")
            except Exception as e:
                logger.error(f"❌ Erreur initialisation VWAP Bands: {e}")
                self.vwap_analyzer = None
        else:
            logger.warning("❌ VWAP Bands non disponible")
        
        # Volume Profile Imbalance Detector
        if VOLUME_IMBALANCE_AVAILABLE:
            volume_config = self.config.get('volume_imbalance', {})
            self.volume_imbalance_detector = create_volume_profile_imbalance_detector(volume_config)
            logger.info("✅ Volume Profile Imbalance initialisé (5% confluence weight)")
        else:
            logger.warning("❌ Volume Profile Imbalance non disponible")
    
    async def calculate_integrated_features(self,
                                          market_data: MarketData,
                                          order_flow: Optional[OrderFlowData] = None,
                                          options_data: Optional[Any] = None,
                                          structure_data: Optional[Any] = None,
                                          **kwargs) -> IntegratedFeatureResult:
        """
        🎯 FONCTION PRINCIPALE - Calcul features intégrées
        
        Toutes les features (originales + nouvelles) calculées en parallèle
        et intégrées dans UNE SEULE confluence score
        """
        start_time = time.perf_counter()
        
        try:
            # 1. Calculs parallèles - toutes features
            tasks = []
            
            # Task features originales
            if self.original_calculator:
                original_task = asyncio.create_task(
                    self._calculate_original_features_async(
                        market_data, order_flow, options_data, structure_data, **kwargs
                    )
                )
                tasks.append(('original', original_task))
            
            # Task VWAP Bands
            if self.vwap_analyzer:
                vwap_task = asyncio.create_task(
                    self._calculate_vwap_bands_async(market_data)
                )
                tasks.append(('vwap_bands', vwap_task))
            
            # Task Volume Imbalance
            if self.volume_imbalance_detector:
                volume_task = asyncio.create_task(
                    self._calculate_volume_imbalance_async(market_data, order_flow)
                )
                tasks.append(('volume_imbalance', volume_task))
            
            # Exécution parallèle
            results = {}
            if tasks:
                completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
                
                for i, (name, _) in enumerate(tasks):
                    if not isinstance(completed_tasks[i], Exception):
                        results[name] = completed_tasks[i]
                    else:
                        logger.error(f"Erreur {name}: {completed_tasks[i]}")
                        results[name] = None
            
            # 2. Extraction features individuelles
            integrated_result = self._extract_and_combine_features(
                market_data.timestamp,
                results.get('original'),
                results.get('vwap_bands'),
                results.get('volume_imbalance')
            )
            
            # 3. Calcul confluence intégrée (toutes features ensemble)
            integrated_confluence = self._calculate_integrated_confluence_score(integrated_result)
            integrated_result.integrated_confluence_score = integrated_confluence
            
            # 4. Détermination qualité signal optimisée
            signal_quality = self._determine_optimized_signal_quality(integrated_confluence)
            integrated_result.signal_quality = signal_quality
            integrated_result.position_multiplier = self._get_position_multiplier(signal_quality)
            
            # 5. Performance
            calc_time = (time.perf_counter() - start_time) * 1000
            integrated_result.calculation_time_ms = calc_time
            
            # 6. Mise à jour stats
            self._update_stats(calc_time, signal_quality)
            
            logger.debug(f"Integrated Features: Score={integrated_confluence:.3f} | "
                        f"Quality={signal_quality.value} | Time={calc_time:.1f}ms")
            
            return integrated_result
            
        except Exception as e:
            logger.error(f"Erreur IntegratedFeatureCalculator: {e}")
            return self._create_default_result(market_data.timestamp)
    
    async def _calculate_original_features_async(self, market_data: MarketData,
                                               order_flow: Optional[OrderFlowData],
                                               options_data: Optional[Any],
                                               structure_data: Optional[Any],
                                               **kwargs) -> Optional[Any]:
        """Calcul features originales en async"""
        try:
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                lambda: self.original_calculator.calculate_all_features(
                    market_data, order_flow, options_data, structure_data, **kwargs
                )
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur original features: {e}")
            return None
    
    async def _calculate_vwap_bands_async(self, market_data: MarketData) -> Optional[VWAPBandsData]:
        """Calcul VWAP Bands en async"""
        try:
            if not self.vwap_analyzer:
                logger.warning("❌ VWAP Analyzer non initialisé")
                return None
                
            logger.debug("🔍 Calcul VWAP Bands en cours...")
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                lambda: self.vwap_analyzer.analyze_vwap_bands(market_data)
            )
            
            logger.debug(f"✅ VWAP Bands calculé: {result.rejection_signal:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur VWAP Bands: {e}")
            return None
    
    async def _calculate_volume_imbalance_async(self, market_data: MarketData,
                                              order_flow: Optional[OrderFlowData]) -> Optional[VolumeProfileImbalanceResult]:
        """Calcul Volume Imbalance en async"""
        try:
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                lambda: self.volume_imbalance_detector.detect_imbalances(market_data)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur Volume Imbalance: {e}")
            return None
    
    def _extract_and_combine_features(self, timestamp: pd.Timestamp,
                                    original_result: Optional[Any],
                                    vwap_bands: Optional[VWAPBandsData],
                                    volume_imbalance: Optional[VolumeProfileImbalanceResult]) -> IntegratedFeatureResult:
        """Extrait et combine toutes les features"""
        
        result = IntegratedFeatureResult(timestamp=timestamp)
        
        # Extraction features originales
        if original_result and hasattr(original_result, 'gamma_levels_proximity'):
            result.gamma_levels_proximity = original_result.gamma_levels_proximity
            result.volume_confirmation = original_result.volume_confirmation
            result.vwap_trend_signal = original_result.vwap_trend_signal
            result.sierra_pattern_strength = original_result.sierra_pattern_strength
            result.mtf_confluence_score = getattr(original_result, 'mtf_confluence_score', 0.0)
            result.smart_money_strength = getattr(original_result, 'smart_money_strength', 0.0)
            result.order_book_imbalance = getattr(original_result, 'order_book_imbalance', 0.0)
            result.options_flow_bias = getattr(original_result, 'options_flow_bias', 0.0)
        
        # 🆕 Extraction nouvelles features optimisées
        result.vwap_bands_signal = self._calculate_vwap_bands_signal(vwap_bands)
        result.volume_imbalance_signal = self._calculate_volume_imbalance_signal(volume_imbalance)
        
        # Stockage données brutes
        result.vwap_bands_data = vwap_bands
        result.volume_imbalance_data = volume_imbalance
        
        return result
    
    def _calculate_vwap_bands_signal(self, vwap_bands: Optional[VWAPBandsData]) -> float:
        """Calcul signal VWAP Bands optimisé (0-1)"""
        if not vwap_bands:
            return 0.0
        
        # Signal combiné : rejection + breakout + trend strength
        signal = (
            vwap_bands.rejection_signal * 0.4 +    # Zones de rejet SD2
            vwap_bands.breakout_signal * 0.3 +     # Breakouts SD1  
            vwap_bands.trend_strength * 0.3        # Force tendance
        )
        
        return min(signal, 1.0)
    
    def _calculate_volume_imbalance_signal(self, volume_imbalance: Optional[VolumeProfileImbalanceResult]) -> float:
        """Calcul signal Volume Imbalance optimisé (0-1)"""
        if not volume_imbalance:
            return 0.0
        
        # Signal combiné : imbalance strength + institutional sentiment + confidence
        signal = (
            volume_imbalance.imbalance_strength * 0.5 +           # Force déséquilibre
            abs(volume_imbalance.institutional_sentiment) * 0.3 + # Sentiment institutionnel
            volume_imbalance.confidence_score * 0.2               # Confiance détection
        )
        
        return min(signal, 1.0)
    
    def _calculate_integrated_confluence_score(self, result: IntegratedFeatureResult) -> float:
        """
        🎯 CALCUL CONFLUENCE INTÉGRÉE FINALE
        
        Toutes les features (originales + nouvelles) pondérées selon INTEGRATED_CONFLUENCE_WEIGHTS
        """
        features = {
            'gamma_levels_proximity': result.gamma_levels_proximity,
            'volume_confirmation': result.volume_confirmation,
            'vwap_trend_signal': result.vwap_trend_signal,
            'sierra_pattern_strength': result.sierra_pattern_strength,
            'mtf_confluence_score': result.mtf_confluence_score,
            'smart_money_strength': result.smart_money_strength,
            'order_book_imbalance': result.order_book_imbalance,
            'options_flow_bias': result.options_flow_bias,
            
            # 🆕 NOUVELLES FEATURES INTÉGRÉES
            'vwap_bands_signal': result.vwap_bands_signal,
            'volume_imbalance_signal': result.volume_imbalance_signal,
        }
        
        confluence_score = 0.0
        
        for feature_name, feature_value in features.items():
            weight = INTEGRATED_CONFLUENCE_WEIGHTS.get(feature_name, 0.0)
            confluence_score += feature_value * weight
        
        return max(0.0, min(1.0, confluence_score))
    
    def _determine_optimized_signal_quality(self, confluence_score: float) -> OptimizedSignalQuality:
        """Détermine qualité signal avec seuils optimisés"""
        
        if confluence_score >= OPTIMIZED_TRADING_THRESHOLDS['PREMIUM_SIGNAL']:
            return OptimizedSignalQuality.PREMIUM
        elif confluence_score >= OPTIMIZED_TRADING_THRESHOLDS['STRONG_SIGNAL']:
            return OptimizedSignalQuality.STRONG
        elif confluence_score >= OPTIMIZED_TRADING_THRESHOLDS['GOOD_SIGNAL']:
            return OptimizedSignalQuality.GOOD
        elif confluence_score >= OPTIMIZED_TRADING_THRESHOLDS['WEAK_SIGNAL']:
            return OptimizedSignalQuality.WEAK
        else:
            return OptimizedSignalQuality.NO_TRADE
    
    def _get_position_multiplier(self, signal_quality: OptimizedSignalQuality) -> float:
        """Retourne multiplicateur position selon qualité"""
        
        multipliers = {
            OptimizedSignalQuality.PREMIUM: 2.0,   # ×2.0 pour premium
            OptimizedSignalQuality.STRONG: 1.5,    # ×1.5 pour strong
            OptimizedSignalQuality.GOOD: 1.0,      # ×1.0 pour good
            OptimizedSignalQuality.WEAK: 0.5,      # ×0.5 pour weak
            OptimizedSignalQuality.NO_TRADE: 0.0   # ×0.0 pour no trade
        }
        
        return multipliers.get(signal_quality, 0.0)
    
    def _create_default_result(self, timestamp: pd.Timestamp) -> IntegratedFeatureResult:
        """Crée résultat par défaut en cas d'erreur"""
        return IntegratedFeatureResult(
            timestamp=timestamp,
            integrated_confluence_score=0.0,
            signal_quality=OptimizedSignalQuality.NO_TRADE,
            position_multiplier=0.0,
            calculation_time_ms=0.0
        )
    
    def _update_stats(self, calc_time: float, signal_quality: OptimizedSignalQuality):
        """Mise à jour statistiques"""
        self.stats['calculations_count'] += 1
        count = self.stats['calculations_count']
        
        # Moyenne mobile temps calcul
        prev_avg = self.stats['avg_calc_time_ms']
        self.stats['avg_calc_time_ms'] = ((prev_avg * (count - 1)) + calc_time) / count
        
        # Compteurs signaux
        if signal_quality == OptimizedSignalQuality.PREMIUM:
            self.stats['premium_signals_count'] += 1
        elif signal_quality == OptimizedSignalQuality.STRONG:
            self.stats['strong_signals_count'] += 1
    
    def _get_feature_count(self) -> int:
        """Retourne nombre de features disponibles"""
        count = 8  # Features originales de base
        
        if self.vwap_analyzer:
            count += 1
        if self.volume_imbalance_detector:
            count += 1
        
        return count
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Retourne statistiques performance"""
        
        # Taux signaux qualité
        total_calcs = max(self.stats['calculations_count'], 1)
        premium_rate = (self.stats['premium_signals_count'] / total_calcs) * 100
        strong_rate = (self.stats['strong_signals_count'] / total_calcs) * 100
        
        return {
            'calculations_count': self.stats['calculations_count'],
            'avg_calc_time_ms': self.stats['avg_calc_time_ms'],
            'premium_signal_rate': premium_rate,
            'strong_signal_rate': strong_rate,
            'feature_count': self._get_feature_count(),
            'optimizations_available': [
                'VWAP Bands' if self.vwap_analyzer else None,
                'Volume Imbalance' if self.volume_imbalance_detector else None
            ],
            'confluence_weights': INTEGRATED_CONFLUENCE_WEIGHTS,
            'trading_thresholds': OPTIMIZED_TRADING_THRESHOLDS
        }

# === COMPATIBILITY WRAPPER ===

class IntegratedCompatibilityWrapper:
    """
    Wrapper compatibilité pour remplacer FeatureCalculator original
    Interface identique mais avec nouvelles optimisations intégrées
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation wrapper"""
        self.integrated_calculator = IntegratedFeatureCalculator(config)
        logger.info("🔄 IntegratedCompatibilityWrapper initialisé")
    
    def calculate_all_features(self, market_data: MarketData, *args, **kwargs):
        """Interface compatible avec FeatureCalculator original"""
        
        # Exécution synchrone pour compatibilité
        import asyncio
        
        try:
            # Event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Calcul intégré
            integrated_result = loop.run_until_complete(
                self.integrated_calculator.calculate_integrated_features(market_data, *args, **kwargs)
            )
            
            # Conversion résultat compatible
            return self._convert_to_compatible_result(integrated_result)
            
        except Exception as e:
            logger.error(f"Erreur IntegratedCompatibilityWrapper: {e}")
            return self._create_fallback_result(market_data.timestamp)
    
    def _convert_to_compatible_result(self, integrated_result: IntegratedFeatureResult):
        """Convertit résultat intégré vers format compatible"""
        
        # Si FeatureCalculationResult disponible, l'utiliser
        if ORIGINAL_CALCULATOR_AVAILABLE:
            try:
                return FeatureCalculationResult(
                    timestamp=integrated_result.timestamp,
                    confluence_score=integrated_result.integrated_confluence_score,
                    signal_quality=integrated_result.signal_quality,
                    calculation_time_ms=integrated_result.calculation_time_ms
                )
            except:
                pass
        
        # Sinon retourner résultat intégré directement
        return integrated_result
    
    def _create_fallback_result(self, timestamp: pd.Timestamp):
        """Résultat fallback en cas d'erreur"""
        return IntegratedFeatureResult(
            timestamp=timestamp,
            integrated_confluence_score=0.0,
            signal_quality=OptimizedSignalQuality.NO_TRADE,
            calculation_time_ms=0.0
        )

# === FACTORY FUNCTIONS ===

def create_integrated_feature_calculator(config: Optional[Dict[str, Any]] = None) -> IntegratedFeatureCalculator:
    """Factory function pour IntegratedFeatureCalculator"""
    return IntegratedFeatureCalculator(config)

def create_integrated_compatibility_wrapper(config: Optional[Dict[str, Any]] = None) -> IntegratedCompatibilityWrapper:
    """Factory function pour wrapper compatibilité"""
    return IntegratedCompatibilityWrapper(config)

# === EXPORTS ===

__all__ = [
    'IntegratedFeatureCalculator',
    'IntegratedFeatureResult', 
    'IntegratedCompatibilityWrapper',
    'OptimizedSignalQuality',
    'INTEGRATED_CONFLUENCE_WEIGHTS',
    'OPTIMIZED_TRADING_THRESHOLDS',
    'create_integrated_feature_calculator',
    'create_integrated_compatibility_wrapper'
]

# === ALIAS POUR COMPATIBILITÉ ===
FeatureCalculatorIntegrated = IntegratedFeatureCalculator

if __name__ == "__main__":
    # Test rapide
    logger.info("Test IntegratedFeatureCalculator...")
    
    calculator = create_integrated_feature_calculator()
    stats = calculator.get_performance_stats()
    logger.info(f"Features disponibles: {stats['feature_count']}")
    logger.info(f"Confluence weights: {len(INTEGRATED_CONFLUENCE_WEIGHTS)} features")
    logger.info("✅ IntegratedFeatureCalculator opérationnel")
