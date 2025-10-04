#!/usr/bin/env python3
"""
MENTHORQ CACHE OPTIMIZER
========================

Cache intelligent pour les calculs MenthorQ avec :
- Précalculs des niveaux gamma/blind spots
- Cache LRU avec TTL
- Lazy loading des features coûteuses
- Invalidation intelligente

Performance cible : <50ms pour calculs MenthorQ
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

# === CACHE CONFIGURATION ===
CACHE_CONFIG = {
    'max_size': 1000,  # Maximum entries in cache
    'ttl_seconds': 300,  # 5 minutes TTL
    'gamma_precompute_range': 50,  # Precompute ±50 ticks around current price
    'blind_spots_precompute_range': 30,  # Precompute ±30 ticks
    'lazy_load_threshold': 0.1,  # Only load if confidence > 10%
}

@dataclass
class CacheEntry:
    """Entry du cache avec métadonnées"""
    data: Any
    timestamp: float
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def is_expired(self, ttl: float) -> bool:
        """Vérifie si l'entrée est expirée"""
        return time.time() - self.timestamp > ttl
    
    def touch(self):
        """Met à jour les métadonnées d'accès"""
        self.access_count += 1
        self.last_access = time.time()

class MenthorQCache:
    """Cache intelligent pour MenthorQ avec LRU et TTL"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or CACHE_CONFIG
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_cleanups': 0
        }
        
        logger.info("🧠 MenthorQ Cache initialisé")
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une entrée du cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_expired(self.config['ttl_seconds']):
                    # Expiré - supprimer
                    del self.cache[key]
                    self.stats['expired_cleanups'] += 1
                    self.stats['misses'] += 1
                    return None
                
                # Hit - déplacer vers la fin (LRU)
                entry.touch()
                self.cache.move_to_end(key)
                self.stats['hits'] += 1
                return entry.data
            
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, data: Any) -> None:
        """Ajoute une entrée au cache"""
        with self.lock:
            # Nettoyer les entrées expirées si nécessaire
            self._cleanup_expired()
            
            # Éviction LRU si nécessaire
            while len(self.cache) >= self.config['max_size']:
                self.cache.popitem(last=False)  # Supprime le plus ancien
                self.stats['evictions'] += 1
            
            # Ajouter la nouvelle entrée
            self.cache[key] = CacheEntry(
                data=data,
                timestamp=time.time()
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
                'max_size': self.config['max_size'],
                **self.stats
            }
    
    def clear(self) -> None:
        """Vide le cache"""
        with self.lock:
            self.cache.clear()
            logger.info("🧠 MenthorQ Cache vidé")

# Instance globale du cache
_menthorq_cache = MenthorQCache()

def cached_menthorq_calculation(func):
    """Décorateur pour cache automatique des calculs MenthorQ"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Générer une clé de cache basée sur les arguments
        cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
        
        # Vérifier le cache
        cached_result = _menthorq_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Calculer et mettre en cache
        result = func(*args, **kwargs)
        _menthorq_cache.put(cache_key, result)
        
        return result
    
    return wrapper

class MenthorQPrecomputer:
    """Précalculateur intelligent pour MenthorQ"""
    
    def __init__(self):
        self.gamma_levels_cache: Dict[str, Dict[float, Any]] = {}
        self.blind_spots_cache: Dict[str, Dict[float, Any]] = {}
        self.last_precompute_price: Dict[str, float] = {}
        self.precompute_threshold = 10.0  # Recompute si prix change de 10 ticks
        
        logger.info("🧠 MenthorQ Precomputer initialisé")
    
    def should_precompute(self, symbol: str, current_price: float) -> bool:
        """Détermine si on doit précalculer pour ce prix"""
        if symbol not in self.last_precompute_price:
            return True
        
        price_change = abs(current_price - self.last_precompute_price[symbol])
        return price_change >= self.precompute_threshold
    
    def precompute_gamma_levels(self, symbol: str, current_price: float, 
                               gamma_data: Dict[str, Any]) -> Dict[float, Any]:
        """Précalcule les niveaux gamma autour du prix actuel"""
        if not self.should_precompute(symbol, current_price):
            return self.gamma_levels_cache.get(symbol, {})
        
        range_ticks = CACHE_CONFIG['gamma_precompute_range']
        min_price = current_price - (range_ticks * 0.25)  # ES tick size
        max_price = current_price + (range_ticks * 0.25)
        
        precomputed = {}
        for level_name, level_price in gamma_data.items():
            if min_price <= level_price <= max_price:
                # Précalculer les métriques pour ce niveau
                distance_ticks = abs(level_price - current_price) / 0.25
                strength = max(0, 1.0 - (distance_ticks / range_ticks))
                
                precomputed[level_price] = {
                    'name': level_name,
                    'price': level_price,
                    'distance_ticks': distance_ticks,
                    'strength': strength,
                    'precomputed_at': time.time()
                }
        
        self.gamma_levels_cache[symbol] = precomputed
        self.last_precompute_price[symbol] = current_price
        
        logger.debug(f"🧠 Précalculé {len(precomputed)} niveaux gamma pour {symbol}")
        return precomputed
    
    def precompute_blind_spots(self, symbol: str, current_price: float,
                              blind_spots_data: Dict[str, Any]) -> Dict[float, Any]:
        """Précalcule les blind spots autour du prix actuel"""
        if not self.should_precompute(symbol, current_price):
            return self.blind_spots_cache.get(symbol, {})
        
        range_ticks = CACHE_CONFIG['blind_spots_precompute_range']
        min_price = current_price - (range_ticks * 0.25)
        max_price = current_price + (range_ticks * 0.25)
        
        precomputed = {}
        for spot_name, spot_price in blind_spots_data.items():
            if min_price <= spot_price <= max_price:
                distance_ticks = abs(spot_price - current_price) / 0.25
                strength = max(0, 1.0 - (distance_ticks / range_ticks))
                
                precomputed[spot_price] = {
                    'name': spot_name,
                    'price': spot_price,
                    'distance_ticks': distance_ticks,
                    'strength': strength,
                    'precomputed_at': time.time()
                }
        
        self.blind_spots_cache[symbol] = precomputed
        self.last_precompute_price[symbol] = current_price
        
        logger.debug(f"🧠 Précalculé {len(precomputed)} blind spots pour {symbol}")
        return precomputed

# Instance globale du précalculateur
_menthorq_precomputer = MenthorQPrecomputer()

class LazyMenthorQCalculator:
    """Calculateur MenthorQ avec lazy loading"""
    
    def __init__(self):
        self.cache = _menthorq_cache
        self.precomputer = _menthorq_precomputer
        self.lazy_threshold = CACHE_CONFIG['lazy_load_threshold']
        
        logger.info("🧠 Lazy MenthorQ Calculator initialisé")
    
    @cached_menthorq_calculation
    def calculate_menthorq_signal(self, symbol: str, current_price: float,
                                 gamma_data: Dict[str, Any],
                                 blind_spots_data: Dict[str, Any],
                                 order_flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule le signal MenthorQ avec lazy loading"""
        start_time = time.time()
        
        # Précalculer les niveaux
        gamma_levels = self.precomputer.precompute_gamma_levels(
            symbol, current_price, gamma_data
        )
        blind_spots = self.precomputer.precompute_blind_spots(
            symbol, current_price, blind_spots_data
        )
        
        # Calcul rapide de base
        base_signal = self._calculate_base_signal(
            current_price, gamma_levels, blind_spots
        )
        
        # Lazy loading des features coûteuses seulement si nécessaire
        if base_signal['confidence'] >= self.lazy_threshold:
            enhanced_signal = self._calculate_enhanced_signal(
                base_signal, order_flow_data, gamma_levels, blind_spots
            )
        else:
            enhanced_signal = base_signal
        
        calculation_time = (time.time() - start_time) * 1000
        enhanced_signal['calculation_time_ms'] = calculation_time
        
        logger.debug(f"🧠 MenthorQ signal calculé en {calculation_time:.1f}ms")
        return enhanced_signal
    
    def _calculate_base_signal(self, current_price: float,
                              gamma_levels: Dict[float, Any],
                              blind_spots: Dict[float, Any]) -> Dict[str, Any]:
        """Calcul rapide de base du signal"""
        # Trouver le niveau le plus proche
        closest_gamma = min(gamma_levels.values(), 
                          key=lambda x: x['distance_ticks'], 
                          default=None)
        closest_blind_spot = min(blind_spots.values(),
                               key=lambda x: x['distance_ticks'],
                               default=None)
        
        # Calcul de base
        gamma_strength = closest_gamma['strength'] if closest_gamma else 0.0
        blind_spot_strength = closest_blind_spot['strength'] if closest_blind_spot else 0.0
        
        base_confidence = (gamma_strength * 0.6 + blind_spot_strength * 0.4)
        
        return {
            'confidence': base_confidence,
            'gamma_strength': gamma_strength,
            'blind_spot_strength': blind_spot_strength,
            'closest_gamma': closest_gamma,
            'closest_blind_spot': closest_blind_spot,
            'signal_type': 'BASE'
        }
    
    def _calculate_enhanced_signal(self, base_signal: Dict[str, Any],
                                  order_flow_data: Dict[str, Any],
                                  gamma_levels: Dict[float, Any],
                                  blind_spots: Dict[float, Any]) -> Dict[str, Any]:
        """Calcul avancé avec features coûteuses"""
        # Features avancées seulement si base signal est prometteur
        enhanced = base_signal.copy()
        
        # Calculs coûteux (simulés)
        order_flow_strength = self._calculate_order_flow_strength(order_flow_data)
        confluence_bonus = self._calculate_confluence_bonus(gamma_levels, blind_spots)
        
        # Score final
        enhanced['confidence'] = min(1.0, 
            base_signal['confidence'] + order_flow_strength * 0.2 + confluence_bonus * 0.1
        )
        enhanced['order_flow_strength'] = order_flow_strength
        enhanced['confluence_bonus'] = confluence_bonus
        enhanced['signal_type'] = 'ENHANCED'
        
        return enhanced
    
    def _calculate_order_flow_strength(self, order_flow_data: Dict[str, Any]) -> float:
        """Calcule la force de l'order flow (simulé)"""
        # Simulation d'un calcul coûteux
        time.sleep(0.001)  # 1ms de simulation
        return np.random.uniform(0.3, 0.8)
    
    def _calculate_confluence_bonus(self, gamma_levels: Dict[float, Any],
                                   blind_spots: Dict[float, Any]) -> float:
        """Calcule le bonus de confluence (simulé)"""
        # Simulation d'un calcul coûteux
        time.sleep(0.001)  # 1ms de simulation
        return np.random.uniform(0.1, 0.3)

# Instance globale du calculateur lazy
_lazy_menthorq_calculator = LazyMenthorQCalculator()

def get_optimized_menthorq_signal(symbol: str, current_price: float,
                                 gamma_data: Dict[str, Any],
                                 blind_spots_data: Dict[str, Any],
                                 order_flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """API publique pour obtenir un signal MenthorQ optimisé"""
    return _lazy_menthorq_calculator.calculate_menthorq_signal(
        symbol, current_price, gamma_data, blind_spots_data, order_flow_data
    )

def get_cache_stats() -> Dict[str, Any]:
    """Retourne les statistiques du cache"""
    return _menthorq_cache.get_stats()

def clear_menthorq_cache() -> None:
    """Vide le cache MenthorQ"""
    _menthorq_cache.clear()



