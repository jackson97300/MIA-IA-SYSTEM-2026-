#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Configuration Optimisation Latence
[PLUG] OPTIMISATIONS LATENCE POUR PERFORMANCE MAXIMALE

🔧 OPTIMISATIONS APPLIQUÉES :
- ✅ Cache intelligent pour Battle Navale
- ✅ Pré-calcul features Confluence
- ✅ Connection pooling IBKR
- ✅ Async processing optimisé
- ✅ Monitoring latence temps réel

Author: MIA_IA_SYSTEM
Version: 1.0.0
Date: Juillet 2025
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# === LATENCY OPTIMIZATION CONFIG ===

@dataclass
class LatencyOptimizationConfig:
    """Configuration optimisations latence"""
    
    # Cache settings
    enable_battle_navale_cache: bool = True
    battle_navale_cache_size: int = 1000
    battle_navale_cache_ttl_seconds: int = 300  # 5 minutes
    
    enable_confluence_cache: bool = True
    confluence_cache_size: int = 500
    confluence_cache_ttl_seconds: int = 180  # 3 minutes
    
    # Pre-calculation
    pre_calculate_features: bool = True
    feature_precalc_window_minutes: int = 30
    enable_parallel_processing: bool = True
    
    # IBKR optimizations
    enable_connection_pooling: bool = True
    max_connection_pool_size: int = 3
    connection_timeout_ms: int = 5000
    enable_keepalive: bool = True
    keepalive_interval_seconds: int = 30
    
    # Async optimizations
    max_concurrent_requests: int = 10
    request_timeout_ms: int = 2000
    enable_request_batching: bool = True
    batch_size: int = 5
    
    # Monitoring
    enable_latency_monitoring: bool = True
    latency_alert_threshold_ms: int = 150
    latency_critical_threshold_ms: int = 200
    monitoring_interval_seconds: int = 5

# === LATENCY TARGETS BY STRATEGY ===

LATENCY_TARGETS_BY_STRATEGY = {
    'scalping': {
        'max_signal_generation_ms': 20,
        'max_order_execution_ms': 50,
        'max_total_latency_ms': 100,
        'priority': 'critical'
    },
    'day_trading': {
        'max_signal_generation_ms': 35,
        'max_order_execution_ms': 80,
        'max_total_latency_ms': 150,
        'priority': 'high'
    },
    'swing_trading': {
        'max_signal_generation_ms': 50,
        'max_order_execution_ms': 120,
        'max_total_latency_ms': 200,
        'priority': 'medium'
    }
}

# === CACHE CONFIGURATIONS ===

BATTLE_NAVALE_CACHE_CONFIG = {
    'enable': True,
    'max_size': 1000,
    'ttl_seconds': 300,
    'preload_patterns': True,
    'cache_pattern_validation': True,
    'cache_signal_strength': True
}

CONFLUENCE_CACHE_CONFIG = {
    'enable': True,
    'max_size': 500,
    'ttl_seconds': 180,
    'cache_mtf_data': True,
    'cache_feature_weights': True,
    'cache_thresholds': True
}

# === IBKR CONNECTION OPTIMIZATIONS ===

IBKR_CONNECTION_OPTIMIZATIONS = {
    'enable_connection_pooling': True,
    'pool_size': 3,
    'connection_timeout_ms': 5000,
    'enable_keepalive': True,
    'keepalive_interval_seconds': 30,
    'enable_auto_reconnect': True,
    'max_reconnect_attempts': 5,
    'reconnect_delay_seconds': 2
}

# === ASYNC PROCESSING OPTIMIZATIONS ===

ASYNC_PROCESSING_CONFIG = {
    'max_concurrent_requests': 10,
    'request_timeout_ms': 2000,
    'enable_request_batching': True,
    'batch_size': 5,
    'enable_priority_queue': True,
    'priority_queue_size': 100
}

# === MONITORING CONFIGURATIONS ===

LATENCY_MONITORING_CONFIG = {
    'enable_monitoring': True,
    'alert_threshold_ms': 150,
    'critical_threshold_ms': 200,
    'monitoring_interval_seconds': 5,
    'enable_alerting': True,
    'enable_logging': True,
    'enable_metrics_export': True
}

# === PERFORMANCE TARGETS ===

PERFORMANCE_TARGETS = {
    'target_latency_ms': 120,
    'max_acceptable_latency_ms': 180,
    'target_throughput_signals_per_minute': 30,
    'max_memory_usage_mb': 512,
    'target_cpu_usage_percent': 70
}

# === OPTIMIZATION FUNCTIONS ===

def get_latency_targets_for_strategy(strategy: str) -> Dict[str, int]:
    """Retourne les cibles de latence pour une stratégie"""
    return LATENCY_TARGETS_BY_STRATEGY.get(strategy, LATENCY_TARGETS_BY_STRATEGY['day_trading'])

def is_latency_acceptable(actual_latency_ms: float, strategy: str = 'day_trading') -> bool:
    """Vérifie si la latence est acceptable pour la stratégie"""
    targets = get_latency_targets_for_strategy(strategy)
    return actual_latency_ms <= targets['max_total_latency_ms']

def get_optimization_priority(strategy: str) -> str:
    """Retourne la priorité d'optimisation pour une stratégie"""
    targets = get_latency_targets_for_strategy(strategy)
    return targets.get('priority', 'medium')

# === DEFAULT CONFIGURATION ===

DEFAULT_LATENCY_CONFIG = LatencyOptimizationConfig()

def create_latency_config(overrides: Optional[Dict[str, Any]] = None) -> LatencyOptimizationConfig:
    """Crée une configuration de latence avec overrides optionnels"""
    config = LatencyOptimizationConfig()
    
    if overrides:
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return config 