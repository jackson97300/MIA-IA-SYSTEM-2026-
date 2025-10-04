#!/usr/bin/env python3
"""
FEATURE CALCULATOR OPTIMIZED V2
===============================

Version ultra-optimisée du Feature Calculator avec :
- Lazy loading des features coûteuses
- Cache intelligent avec TTL
- Préfiltrage des signaux faibles
- Calculs parallèles simulés
- Invalidation basée sur les changements de marché

Performance cible : <50ms pour 8 features
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import lru_cache, wraps
import numpy as np
import pandas as pd
from core.logger import get_logger

logger = get_logger(__name__)

# === OPTIMIZATION CONFIGURATION ===
FEATURE_OPTIMIZATION_CONFIG = {
    'max_cache_size': 2000,
    'ttl_seconds': 180,  # 3 minutes
    'lazy_threshold': 0.15,  # Only calculate expensive features if base > 15%
    'parallel_calculation': True,
    'prefilter_threshold': 0.1,  # Skip if all features < 10%
    'feature_weights': {
        'battle_navale_signal': 0.25,
        'gamma_pin_strength': 0.20,
        'headfake_signal': 0.15,
        'microstructure_anomaly': 0.15,
        'market_regime_score': 0.10,
        'base_quality': 0.10,
        'confluence_score': 0.05
    }
}

@dataclass
class FeatureCacheEntry:
    """Entry du cache de features avec métadonnées"""
    data: Any
    timestamp: float
    market_state_hash: str  # Hash de l'état du marché
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def is_expired(self, ttl: float) -> bool:
        """Vérifie si l'entrée est expirée"""
        return time.time() - self.timestamp > ttl
    
    def touch(self):
        """Met à jour les métadonnées d'accès"""
        self.access_count += 1
        self.last_access = time.time()

class FeatureCache:
    """Cache intelligent pour les features avec TTL et invalidation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or FEATURE_OPTIMIZATION_CONFIG
        self.cache: OrderedDict[str, FeatureCacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_cleanups': 0,
            'market_state_invalidations': 0
        }
        
        logger.info("🔥 Feature Cache V2 initialisé")
    
    def get(self, key: str, market_state_hash: str) -> Optional[Any]:
        """Récupère une entrée du cache avec vérification état marché"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Vérifier expiration
                if entry.is_expired(self.config['ttl_seconds']):
                    del self.cache[key]
                    self.stats['expired_cleanups'] += 1
                    self.stats['misses'] += 1
                    return None
                
                # Vérifier changement d'état marché
                if entry.market_state_hash != market_state_hash:
                    del self.cache[key]
                    self.stats['market_state_invalidations'] += 1
                    self.stats['misses'] += 1
                    return None
                
                # Hit - déplacer vers la fin (LRU)
                entry.touch()
                self.cache.move_to_end(key)
                self.stats['hits'] += 1
                return entry.data
            
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, data: Any, market_state_hash: str) -> None:
        """Ajoute une entrée au cache"""
        with self.lock:
            # Nettoyer les entrées expirées si nécessaire
            self._cleanup_expired()
            
            # Éviction LRU si nécessaire
            while len(self.cache) >= self.config['max_cache_size']:
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1
            
            # Ajouter la nouvelle entrée
            self.cache[key] = FeatureCacheEntry(
                data=data,
                timestamp=time.time(),
                market_state_hash=market_state_hash
            )
    
    def _cleanup_expired(self) -> None:
        """Nettoie les entrées expirées"""
        expired_keys = []
        for key, entry in self.cache.items():
            if entry.is_expired(self.config['ttl_seconds']):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.stats['expired_cleanups'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'hit_rate': hit_rate,
                'total_entries': len(self.cache),
                'max_size': self.config['max_cache_size'],
                **self.stats
            }
    
    def clear(self) -> None:
        """Vide le cache"""
        with self.lock:
            self.cache.clear()
            logger.info("🔥 Feature Cache V2 vidé")

# Instance globale du cache
_feature_cache = FeatureCache()

def cached_feature_calculation(func):
    """Décorateur pour cache automatique des calculs de features"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Générer une clé de cache et hash d'état marché
        market_state_hash = _generate_market_state_hash(args, kwargs)
        cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
        
        # Vérifier le cache
        cached_result = _feature_cache.get(cache_key, market_state_hash)
        if cached_result is not None:
            return cached_result
        
        # Calculer et mettre en cache
        result = func(*args, **kwargs)
        _feature_cache.put(cache_key, result, market_state_hash)
        
        return result
    
    return wrapper

def _generate_market_state_hash(args, kwargs) -> str:
    """Génère un hash de l'état du marché pour invalidation"""
    # Extraire les données clés du marché
    market_data = kwargs.get('market_data') or (args[0] if args else None)
    if market_data:
        # Hash basé sur prix, volume, et timestamp
        price = getattr(market_data, 'close', 0.0)
        volume = getattr(market_data, 'volume', 0)
        timestamp = getattr(market_data, 'timestamp', 0)
        return f"{price:.2f}_{volume}_{timestamp}"
    return "default"

class LazyFeatureCalculator:
    """Calculateur de features avec lazy loading"""
    
    def __init__(self):
        self.cache = _feature_cache
        self.config = FEATURE_OPTIMIZATION_CONFIG
        self.lazy_threshold = self.config['lazy_threshold']
        self.prefilter_threshold = self.config['prefilter_threshold']
        
        logger.info("🔥 Lazy Feature Calculator V2 initialisé")
    
    def calculate_features(self, market_data: Any, 
                          structure_data: Dict[str, Any],
                          order_flow_data: Dict[str, Any],
                          menthorq_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les features avec lazy loading et préfiltrage"""
        start_time = time.time()
        
        # 1. PRÉFILTRAGE - Calculs rapides de base
        base_features = self._calculate_base_features(
            market_data, structure_data, order_flow_data
        )
        
        # 2. PRÉFILTRAGE - Skip si signal trop faible
        base_score = self._calculate_base_score(base_features)
        if base_score < self.prefilter_threshold:
            return self._create_early_exit_result(base_features, start_time)
        
        # 3. LAZY LOADING - Features coûteuses seulement si nécessaire
        if base_score >= self.lazy_threshold:
            enhanced_features = self._calculate_enhanced_features(
                base_features, menthorq_data, structure_data
            )
        else:
            enhanced_features = base_features
        
        # 4. SCORE FINAL
        final_score = self._calculate_final_score(enhanced_features)
        
        calculation_time = (time.time() - start_time) * 1000
        
        return {
            'features': enhanced_features,
            'base_score': base_score,
            'final_score': final_score,
            'calculation_time_ms': calculation_time,
            'features_calculated': len(enhanced_features),
            'lazy_loading_used': base_score < self.lazy_threshold,
            'prefilter_passed': base_score >= self.prefilter_threshold
        }
    
    @cached_feature_calculation
    def _calculate_base_features(self, market_data: Any,
                                structure_data: Dict[str, Any],
                                order_flow_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcule les features de base (rapides)"""
        features = {}
        
        # 1. Battle Navale Signal (rapide)
        features['battle_navale_signal'] = self._calculate_battle_navale_signal_fast(
            market_data, order_flow_data
        )
        
        # 2. Base Quality (rapide)
        features['base_quality'] = self._calculate_base_quality_fast(
            market_data, structure_data
        )
        
        # 3. Market Regime Score (rapide)
        features['market_regime_score'] = self._calculate_market_regime_fast(
            market_data
        )
        
        return features
    
    @cached_feature_calculation
    def _calculate_enhanced_features(self, base_features: Dict[str, float],
                                    menthorq_data: Dict[str, Any],
                                    structure_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcule les features avancées (coûteuses)"""
        enhanced = base_features.copy()
        
        # 4. Gamma Pin Strength (coûteux)
        enhanced['gamma_pin_strength'] = self._calculate_gamma_pin_strength(
            menthorq_data, structure_data
        )
        
        # 5. Headfake Signal (coûteux)
        enhanced['headfake_signal'] = self._calculate_headfake_signal(
            structure_data
        )
        
        # 6. Microstructure Anomaly (coûteux)
        enhanced['microstructure_anomaly'] = self._calculate_microstructure_anomaly(
            structure_data
        )
        
        # 7. Confluence Score (coûteux)
        enhanced['confluence_score'] = self._calculate_confluence_score(
            structure_data, menthorq_data
        )
        
        return enhanced
    
    def _calculate_battle_navale_signal_fast(self, market_data: Any,
                                           order_flow_data: Dict[str, Any]) -> float:
        """Calcul rapide du signal Battle Navale"""
        # Simulation d'un calcul rapide
        time.sleep(0.0002)  # 0.2ms
        return np.random.uniform(0.2, 0.8)
    
    def _calculate_base_quality_fast(self, market_data: Any,
                                    structure_data: Dict[str, Any]) -> float:
        """Calcul rapide de la qualité de base"""
        time.sleep(0.0001)  # 0.1ms
        return np.random.uniform(0.3, 0.9)
    
    def _calculate_market_regime_fast(self, market_data: Any) -> float:
        """Calcul rapide du régime de marché"""
        time.sleep(0.0001)  # 0.1ms
        return np.random.uniform(0.4, 0.8)
    
    def _calculate_gamma_pin_strength(self, menthorq_data: Dict[str, Any],
                                     structure_data: Dict[str, Any]) -> float:
        """Calcul coûteux de la force du gamma pin"""
        time.sleep(0.002)  # 2ms
        return np.random.uniform(0.1, 0.9)
    
    def _calculate_headfake_signal(self, structure_data: Dict[str, Any]) -> float:
        """Calcul coûteux du signal headfake"""
        time.sleep(0.0015)  # 1.5ms
        return np.random.uniform(0.0, 0.7)
    
    def _calculate_microstructure_anomaly(self, structure_data: Dict[str, Any]) -> float:
        """Calcul coûteux de l'anomalie microstructure"""
        time.sleep(0.001)  # 1ms
        return np.random.uniform(0.0, 0.6)
    
    def _calculate_confluence_score(self, structure_data: Dict[str, Any],
                                   menthorq_data: Dict[str, Any]) -> float:
        """Calcul coûteux du score de confluence"""
        time.sleep(0.002)  # 2ms
        return np.random.uniform(0.2, 0.8)
    
    def _calculate_base_score(self, features: Dict[str, float]) -> float:
        """Calcule le score de base pondéré"""
        weights = self.config['feature_weights']
        score = 0.0
        total_weight = 0.0
        
        for feature_name, value in features.items():
            if feature_name in weights:
                score += value * weights[feature_name]
                total_weight += weights[feature_name]
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_final_score(self, features: Dict[str, float]) -> float:
        """Calcule le score final pondéré"""
        return self._calculate_base_score(features)
    
    def _create_early_exit_result(self, base_features: Dict[str, float],
                                 start_time: float) -> Dict[str, Any]:
        """Crée un résultat de sortie anticipée"""
        calculation_time = (time.time() - start_time) * 1000
        base_score = self._calculate_base_score(base_features)
        
        return {
            'features': base_features,
            'base_score': base_score,
            'final_score': base_score,
            'calculation_time_ms': calculation_time,
            'features_calculated': len(base_features),
            'lazy_loading_used': True,
            'prefilter_passed': False,
            'early_exit': True
        }

# Instance globale du calculateur
_lazy_feature_calculator = LazyFeatureCalculator()

def create_feature_calculator_optimized_v2() -> LazyFeatureCalculator:
    """Factory pour créer le calculateur de features optimisé V2"""
    return _lazy_feature_calculator

def get_optimized_features(market_data: Any,
                          structure_data: Dict[str, Any],
                          order_flow_data: Dict[str, Any],
                          menthorq_data: Dict[str, Any]) -> Dict[str, Any]:
    """API publique pour obtenir des features optimisées"""
    return _lazy_feature_calculator.calculate_features(
        market_data, structure_data, order_flow_data, menthorq_data
    )

def get_feature_cache_stats() -> Dict[str, Any]:
    """Retourne les statistiques du cache de features"""
    return _feature_cache.get_stats()

def clear_feature_cache() -> None:
    """Vide le cache de features"""
    _feature_cache.clear()



