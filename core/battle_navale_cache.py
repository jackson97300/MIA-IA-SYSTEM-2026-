#!/usr/bin/env python3
"""
BATTLE NAVALE CACHE OPTIMIZER
=============================

Cache intelligent pour Battle Navale V2 avec :
- Cache DOM analysis (calculs coûteux)
- Cache leadership calculations
- Lazy loading des features structure
- Invalidation basée sur le temps et les changements de prix

Performance cible : <30ms pour Battle Navale
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
BATTLE_NAVALE_CACHE_CONFIG = {
    'max_size': 500,  # Maximum entries in cache
    'ttl_seconds': 60,  # 1 minute TTL (DOM changes frequently)
    'dom_analysis_ttl': 30,  # 30 seconds for DOM analysis
    'leadership_ttl': 120,  # 2 minutes for leadership
    'structure_ttl': 300,  # 5 minutes for structure
    'price_change_threshold': 2.0,  # Invalidate if price changes > 2 ticks
}

@dataclass
class BattleNavaleCacheEntry:
    """Entry du cache Battle Navale avec métadonnées spécialisées"""
    data: Any
    timestamp: float
    price_at_cache: float
    cache_type: str  # 'dom', 'leadership', 'structure'
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def is_expired(self, ttl: float) -> bool:
        """Vérifie si l'entrée est expirée"""
        return time.time() - self.timestamp > ttl
    
    def is_price_stale(self, current_price: float, threshold: float) -> bool:
        """Vérifie si le prix a trop changé"""
        return abs(current_price - self.price_at_cache) > threshold
    
    def touch(self):
        """Met à jour les métadonnées d'accès"""
        self.access_count += 1
        self.last_access = time.time()

class BattleNavaleCache:
    """Cache intelligent pour Battle Navale avec TTL spécialisés"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or BATTLE_NAVALE_CACHE_CONFIG
        self.cache: OrderedDict[str, BattleNavaleCacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_cleanups': 0,
            'price_stale_cleanups': 0
        }
        
        logger.info("⚔️ Battle Navale Cache initialisé")
    
    def get(self, key: str, current_price: float = None) -> Optional[Any]:
        """Récupère une entrée du cache avec vérification prix"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Vérifier expiration
                ttl = self._get_ttl_for_type(entry.cache_type)
                if entry.is_expired(ttl):
                    del self.cache[key]
                    self.stats['expired_cleanups'] += 1
                    self.stats['misses'] += 1
                    return None
                
                # Vérifier staleness du prix
                if current_price is not None and entry.is_price_stale(
                    current_price, self.config['price_change_threshold']
                ):
                    del self.cache[key]
                    self.stats['price_stale_cleanups'] += 1
                    self.stats['misses'] += 1
                    return None
                
                # Hit - déplacer vers la fin (LRU)
                entry.touch()
                self.cache.move_to_end(key)
                self.stats['hits'] += 1
                return entry.data
            
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, data: Any, cache_type: str, current_price: float) -> None:
        """Ajoute une entrée au cache avec métadonnées"""
        with self.lock:
            # Nettoyer les entrées expirées si nécessaire
            self._cleanup_expired()
            
            # Éviction LRU si nécessaire
            while len(self.cache) >= self.config['max_size']:
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1
            
            # Ajouter la nouvelle entrée
            self.cache[key] = BattleNavaleCacheEntry(
                data=data,
                timestamp=time.time(),
                price_at_cache=current_price,
                cache_type=cache_type
            )
    
    def _get_ttl_for_type(self, cache_type: str) -> float:
        """Retourne le TTL approprié pour le type de cache"""
        ttl_map = {
            'dom': self.config['dom_analysis_ttl'],
            'leadership': self.config['leadership_ttl'],
            'structure': self.config['structure_ttl']
        }
        return ttl_map.get(cache_type, self.config['ttl_seconds'])
    
    def _cleanup_expired(self) -> None:
        """Nettoie les entrées expirées"""
        expired_keys = []
        for key, entry in self.cache.items():
            ttl = self._get_ttl_for_type(entry.cache_type)
            if entry.is_expired(ttl):
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
            logger.info("⚔️ Battle Navale Cache vidé")

# Instance globale du cache
_battle_navale_cache = BattleNavaleCache()

def cached_battle_navale_calculation(cache_type: str):
    """Décorateur pour cache automatique des calculs Battle Navale"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extraire le prix actuel des arguments
            current_price = kwargs.get('current_price', 0.0)
            if not current_price and len(args) > 1:
                current_price = args[1]  # Assume second argument is price
            
            # Générer une clé de cache
            cache_key = f"{func.__name__}_{cache_type}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Vérifier le cache
            cached_result = _battle_navale_cache.get(cache_key, current_price)
            if cached_result is not None:
                return cached_result
            
            # Calculer et mettre en cache
            result = func(*args, **kwargs)
            _battle_navale_cache.put(cache_key, result, cache_type, current_price)
            
            return result
        
        return wrapper
    return decorator

class OptimizedDOMAnalyzer:
    """Analyseur DOM optimisé avec cache"""
    
    def __init__(self):
        self.cache = _battle_navale_cache
        logger.info("⚔️ Optimized DOM Analyzer initialisé")
    
    @cached_battle_navale_calculation('dom')
    def analyze_dom_health(self, dom_data: Dict[str, Any], 
                          current_price: float) -> Dict[str, Any]:
        """Analyse la santé du DOM avec cache"""
        start_time = time.time()
        
        # Calculs DOM optimisés
        spread_ticks = self._calculate_spread_ticks(dom_data)
        depth_levels = self._count_depth_levels(dom_data)
        l1_bbo_match = self._check_l1_bbo_match(dom_data)
        
        # Score de santé DOM
        health_score = self._calculate_dom_health_score(
            spread_ticks, depth_levels, l1_bbo_match
        )
        
        result = {
            'health_score': health_score,
            'spread_ticks': spread_ticks,
            'depth_levels': depth_levels,
            'l1_bbo_match': l1_bbo_match,
            'is_healthy': health_score >= 0.7,
            'calculation_time_ms': (time.time() - start_time) * 1000
        }
        
        logger.debug(f"⚔️ DOM health analysé en {result['calculation_time_ms']:.1f}ms")
        return result
    
    def _calculate_spread_ticks(self, dom_data: Dict[str, Any]) -> float:
        """Calcule le spread en ticks"""
        bid = dom_data.get('best_bid', 0.0)
        ask = dom_data.get('best_ask', 0.0)
        if bid > 0 and ask > 0:
            return (ask - bid) / 0.25  # ES tick size
        return 999.0  # Invalid spread
    
    def _count_depth_levels(self, dom_data: Dict[str, Any]) -> int:
        """Compte les niveaux de profondeur"""
        bids = dom_data.get('bids', [])
        asks = dom_data.get('asks', [])
        return len(bids) + len(asks)
    
    def _check_l1_bbo_match(self, dom_data: Dict[str, Any]) -> bool:
        """Vérifie si L1 = BBO"""
        # Simulation d'une vérification coûteuse
        time.sleep(0.0005)  # 0.5ms
        return np.random.random() > 0.3  # 70% match rate
    
    def _calculate_dom_health_score(self, spread_ticks: float, 
                                   depth_levels: int, l1_bbo_match: bool) -> float:
        """Calcule le score de santé DOM"""
        spread_score = max(0, 1.0 - (spread_ticks - 2) / 10)  # Optimal à 2 ticks
        depth_score = min(1.0, depth_levels / 10)  # Optimal à 10+ niveaux
        match_score = 1.0 if l1_bbo_match else 0.0
        
        return (spread_score * 0.4 + depth_score * 0.3 + match_score * 0.3)

class OptimizedLeadershipCalculator:
    """Calculateur de leadership optimisé avec cache"""
    
    def __init__(self):
        self.cache = _battle_navale_cache
        logger.info("⚔️ Optimized Leadership Calculator initialisé")
    
    @cached_battle_navale_calculation('leadership')
    def calculate_leadership_score(self, es_data: Dict[str, Any],
                                  nq_data: Dict[str, Any],
                                  current_price: float) -> Dict[str, Any]:
        """Calcule le score de leadership avec cache"""
        start_time = time.time()
        
        # Calculs de leadership optimisés
        correlation = self._calculate_correlation(es_data, nq_data)
        momentum_leadership = self._calculate_momentum_leadership(es_data, nq_data)
        volume_leadership = self._calculate_volume_leadership(es_data, nq_data)
        
        # Score final
        leadership_score = (
            correlation * 0.4 + 
            momentum_leadership * 0.3 + 
            volume_leadership * 0.3
        )
        
        result = {
            'leadership_score': leadership_score,
            'correlation': correlation,
            'momentum_leadership': momentum_leadership,
            'volume_leadership': volume_leadership,
            'is_leader': leadership_score >= 0.6,
            'calculation_time_ms': (time.time() - start_time) * 1000
        }
        
        logger.debug(f"⚔️ Leadership calculé en {result['calculation_time_ms']:.1f}ms")
        return result
    
    def _calculate_correlation(self, es_data: Dict[str, Any], 
                              nq_data: Dict[str, Any]) -> float:
        """Calcule la corrélation ES/NQ"""
        # Simulation d'un calcul coûteux
        time.sleep(0.001)  # 1ms
        return np.random.uniform(0.7, 0.95)
    
    def _calculate_momentum_leadership(self, es_data: Dict[str, Any],
                                      nq_data: Dict[str, Any]) -> float:
        """Calcule le leadership en momentum"""
        time.sleep(0.0005)  # 0.5ms
        return np.random.uniform(0.4, 0.9)
    
    def _calculate_volume_leadership(self, es_data: Dict[str, Any],
                                    nq_data: Dict[str, Any]) -> float:
        """Calcule le leadership en volume"""
        time.sleep(0.0005)  # 0.5ms
        return np.random.uniform(0.3, 0.8)

class OptimizedStructureAnalyzer:
    """Analyseur de structure optimisé avec cache"""
    
    def __init__(self):
        self.cache = _battle_navale_cache
        logger.info("⚔️ Optimized Structure Analyzer initialisé")
    
    @cached_battle_navale_calculation('structure')
    def analyze_structure_confluence(self, structure_data: Dict[str, Any],
                                    current_price: float) -> Dict[str, Any]:
        """Analyse la confluence de structure avec cache"""
        start_time = time.time()
        
        # Calculs de structure optimisés
        vwap_confluence = self._calculate_vwap_confluence(structure_data, current_price)
        profile_confluence = self._calculate_profile_confluence(structure_data, current_price)
        menthorq_confluence = self._calculate_menthorq_confluence(structure_data, current_price)
        
        # Score final
        confluence_score = (
            vwap_confluence * 0.4 + 
            profile_confluence * 0.35 + 
            menthorq_confluence * 0.25
        )
        
        result = {
            'confluence_score': confluence_score,
            'vwap_confluence': vwap_confluence,
            'profile_confluence': profile_confluence,
            'menthorq_confluence': menthorq_confluence,
            'is_confluent': confluence_score >= 0.7,
            'calculation_time_ms': (time.time() - start_time) * 1000
        }
        
        logger.debug(f"⚔️ Structure confluence analysée en {result['calculation_time_ms']:.1f}ms")
        return result
    
    def _calculate_vwap_confluence(self, structure_data: Dict[str, Any],
                                  current_price: float) -> float:
        """Calcule la confluence VWAP"""
        vwap_price = structure_data.get('vwap_price', 0.0)
        if vwap_price > 0:
            distance_ticks = abs(current_price - vwap_price) / 0.25
            return max(0, 1.0 - distance_ticks / 10)  # Optimal à 10 ticks
        return 0.0
    
    def _calculate_profile_confluence(self, structure_data: Dict[str, Any],
                                     current_price: float) -> float:
        """Calcule la confluence Volume Profile"""
        time.sleep(0.0005)  # 0.5ms
        return np.random.uniform(0.3, 0.8)
    
    def _calculate_menthorq_confluence(self, structure_data: Dict[str, Any],
                                      current_price: float) -> float:
        """Calcule la confluence MenthorQ"""
        time.sleep(0.0005)  # 0.5ms
        return np.random.uniform(0.4, 0.9)

# Instances globales
_dom_analyzer = OptimizedDOMAnalyzer()
_leadership_calculator = OptimizedLeadershipCalculator()
_structure_analyzer = OptimizedStructureAnalyzer()

def get_optimized_battle_navale_analysis(dom_data: Dict[str, Any],
                                        es_data: Dict[str, Any],
                                        nq_data: Dict[str, Any],
                                        structure_data: Dict[str, Any],
                                        current_price: float) -> Dict[str, Any]:
    """API publique pour obtenir une analyse Battle Navale optimisée"""
    start_time = time.time()
    
    # Analyses parallèles (simulées)
    dom_health = _dom_analyzer.analyze_dom_health(dom_data, current_price)
    leadership = _leadership_calculator.calculate_leadership_score(
        es_data, nq_data, current_price
    )
    structure = _structure_analyzer.analyze_structure_confluence(
        structure_data, current_price
    )
    
    # Score final Battle Navale
    battle_navale_score = (
        dom_health['health_score'] * 0.3 +
        leadership['leadership_score'] * 0.4 +
        structure['confluence_score'] * 0.3
    )
    
    total_time = (time.time() - start_time) * 1000
    
    return {
        'battle_navale_score': battle_navale_score,
        'dom_health': dom_health,
        'leadership': leadership,
        'structure': structure,
        'is_signal': battle_navale_score >= 0.65,
        'total_calculation_time_ms': total_time
    }

def get_battle_navale_cache_stats() -> Dict[str, Any]:
    """Retourne les statistiques du cache Battle Navale"""
    return _battle_navale_cache.get_stats()

def clear_battle_navale_cache() -> None:
    """Vide le cache Battle Navale"""
    _battle_navale_cache.clear()



