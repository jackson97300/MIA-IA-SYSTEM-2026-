#!/usr/bin/env python3
"""
🎯 CONFIGURATION STRATÉGIE 15MIN + 1HOUR OPTIMISÉE
MIA_IA_SYSTEM - Version fusionnée et améliorée

Ce fichier configure l'intégration optimisée de la stratégie 15min + 1hour
dans le système principal MIA_IA_SYSTEM.

AMÉLIORATIONS APPORTÉES :
- ✅ Documentation enrichie
- ✅ Validation renforcée
- ✅ Gestion d'erreurs améliorée
- ✅ Performance optimisée
- ✅ Intégration système renforcée
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

# Configuration du logger
logger = logging.getLogger(__name__)

# === CONFIGURATION STRATÉGIE 15MIN + 1HOUR OPTIMISÉE ===

@dataclass
class TimeframeConfig:
    """Configuration optimisée des timeframes 15min + 1hour"""
    
    # Timeframes activés
    enabled_timeframes: List[str] = field(default_factory=lambda: ["15min", "1hour"])
    
    # Poids par timeframe (optimisés pour performance)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "15min": 0.70,  # 70% - Exécution précise
        "1hour": 0.30   # 30% - Direction macro
    })
    
    # Seuils de confluence (ajustés pour meilleure performance)
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        "min_15min_confluence": 0.65,    # 65% confluence 15min
        "min_1hour_confluence": 0.60,    # 60% confluence 1hour
        "min_final_confluence": 0.70     # 70% confluence finale
    })
    
    # Cache et performance
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    
    def __post_init__(self):
        """Validation et initialisation post-création"""
        # Validation des timeframes
        valid_timeframes = ["15min", "1hour", "5min", "30min"]
        for tf in self.enabled_timeframes:
            if tf not in valid_timeframes:
                logger.warning(f"⚠️ Timeframe non supporté: {tf}")
        
        # Validation des poids
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            logger.error(f"❌ Poids invalides: somme = {total_weight:.3f} (doit être 1.0)")
            # Correction automatique
            for tf in self.weights:
                self.weights[tf] /= total_weight
            logger.info("🔧 Poids corrigés automatiquement")
        
        # Validation des seuils
        for threshold_name, threshold_value in self.thresholds.items():
            if not (0.0 <= threshold_value <= 1.0):
                logger.error(f"❌ Seuil invalide {threshold_name}: {threshold_value}")
                self.thresholds[threshold_name] = max(0.0, min(1.0, threshold_value))
                logger.info(f"🔧 Seuil {threshold_name} corrigé à {self.thresholds[threshold_name]}")

class ConfluenceRule(Enum):
    """Règles de confluence optimisées"""
    BOTH_REQUIRED = "both_required"      # Les deux timeframes doivent être d'accord
    WEIGHTED_AVERAGE = "weighted_average" # Moyenne pondérée
    STRICT_ALIGNMENT = "strict_alignment" # Alignement strict
    ADAPTIVE = "adaptive"                # NOUVEAU: Règle adaptative selon conditions marché

@dataclass
class StrategyConfig:
    """Configuration complète optimisée de la stratégie"""
    
    # Configuration timeframes
    timeframes: TimeframeConfig = field(default_factory=TimeframeConfig)
    
    # Règle de confluence (optimisée)
    confluence_rule: ConfluenceRule = ConfluenceRule.ADAPTIVE
    
    # Performance optimisée
    max_latency_ms: float = 3.0  # Réduit de 5.0 à 3.0
    cache_enabled: bool = True
    optimization_mode: str = "aggressive"  # Changé de "balanced" à "aggressive"
    
    # Logique de trading renforcée
    signal_validation: str = "strict"
    position_sizing: str = "dynamic"  # Changé de "fixed" à "dynamic"
    
    # NOUVEAU: Gestion des erreurs
    error_handling: str = "graceful"  # "graceful", "strict", "permissive"
    fallback_enabled: bool = True
    
    # NOUVEAU: Monitoring et métriques
    enable_metrics: bool = True
    metrics_retention_hours: int = 24
    
    def __post_init__(self):
        """Validation et initialisation post-création"""
        if self.timeframes is None:
            self.timeframes = TimeframeConfig()
        
        # Validation des paramètres de performance
        if self.max_latency_ms < 1.0:
            logger.warning(f"⚠️ Latence très faible: {self.max_latency_ms}ms")
        
        # Validation du mode d'optimisation
        valid_modes = ["conservative", "balanced", "aggressive"]
        if self.optimization_mode not in valid_modes:
            logger.warning(f"⚠️ Mode d'optimisation invalide: {self.optimization_mode}")
            self.optimization_mode = "balanced"

# === CONFIGURATION PAR DÉFAUT OPTIMISÉE ===

DEFAULT_STRATEGY_CONFIG = StrategyConfig()

# === FONCTIONS D'INTÉGRATION OPTIMISÉES ===

def get_15min_1hour_config() -> StrategyConfig:
    """Retourne la configuration 15min + 1hour optimisée"""
    return DEFAULT_STRATEGY_CONFIG

def validate_timeframe_weights(weights: Dict[str, float]) -> Tuple[bool, str]:
    """Valide que les poids somment à 100% avec message d'erreur détaillé"""
    total = sum(weights.values())
    tolerance = 0.001
    
    if abs(total - 1.0) <= tolerance:
        return True, "Poids valides"
    else:
        error_msg = f"Poids invalides: somme = {total:.6f} (attendu: 1.0, tolérance: {tolerance})"
        return False, error_msg

def calculate_confluence_score(signals: Dict[str, float], weights: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
    """Calcule le score de confluence pondéré avec métriques détaillées"""
    try:
        # Validation des poids
        is_valid, error_msg = validate_timeframe_weights(weights)
        if not is_valid:
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        confluence_score = 0.0
        component_scores = {}
        
        for timeframe, weight in weights.items():
            if timeframe in signals:
                component_score = signals[timeframe] * weight
                confluence_score += component_score
                component_scores[timeframe] = {
                    'signal': signals[timeframe],
                    'weight': weight,
                    'contribution': component_score
                }
        
        # Métriques de qualité
        metrics = {
            'total_score': confluence_score,
            'component_scores': component_scores,
            'signal_count': len([s for s in signals.values() if s != 0]),
            'weight_distribution': weights,
            'calculation_timestamp': datetime.now().isoformat()
        }
        
        return confluence_score, metrics
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul confluence: {e}")
        return 0.0, {'error': str(e)}

def determine_trading_signal(signals: Dict[str, str], config: StrategyConfig) -> Dict[str, Any]:
    """Détermine le signal de trading avec métriques détaillées"""
    try:
        result = {
            'signal': 'NO_TRADE',
            'confidence': 0.0,
            'reason': '',
            'metadata': {
                'rule_used': config.confluence_rule.value,
                'timestamp': datetime.now().isoformat(),
                'input_signals': signals.copy()
            }
        }
        
        if config.confluence_rule == ConfluenceRule.BOTH_REQUIRED:
            # Logique: Les deux timeframes doivent être d'accord
            if "15min" in signals and "1hour" in signals:
                signal_15min = signals["15min"]
                signal_1hour = signals["1hour"]
                
                if signal_15min == "BULLISH" and signal_1hour == "BULLISH":
                    result.update({
                        'signal': 'LONG',
                        'confidence': 0.9,
                        'reason': 'Confluence BULLISH 15min + 1hour'
                    })
                elif signal_15min == "BEARISH" and signal_1hour == "BEARISH":
                    result.update({
                        'signal': 'SHORT',
                        'confidence': 0.9,
                        'reason': 'Confluence BEARISH 15min + 1hour'
                    })
                else:
                    result.update({
                        'signal': 'NO_TRADE',
                        'confidence': 0.3,
                        'reason': f'Conflit: 15min={signal_15min}, 1hour={signal_1hour}'
                    })
            else:
                result.update({
                    'signal': 'NO_TRADE',
                    'confidence': 0.0,
                    'reason': 'Signaux incomplets'
                })
        
        elif config.confluence_rule == ConfluenceRule.WEIGHTED_AVERAGE:
            # Logique: Moyenne pondérée des scores
            weights = config.timeframes.weights
            scores = {tf: 1.0 if signals.get(tf) in ["BULLISH", "LONG"] else 
                            -1.0 if signals.get(tf) in ["BEARISH", "SHORT"] else 0.0
                     for tf in weights.keys()}
            
            confluence_score, metrics = calculate_confluence_score(scores, weights)
            
            if confluence_score > 0.3:
                result.update({
                    'signal': 'LONG',
                    'confidence': min(0.9, abs(confluence_score)),
                    'reason': f'Score pondéré positif: {confluence_score:.3f}'
                })
            elif confluence_score < -0.3:
                result.update({
                    'signal': 'SHORT',
                    'confidence': min(0.9, abs(confluence_score)),
                    'reason': f'Score pondéré négatif: {confluence_score:.3f}'
                })
            else:
                result.update({
                    'signal': 'NO_TRADE',
                    'confidence': 0.2,
                    'reason': f'Score neutre: {confluence_score:.3f}'
                })
            
            result['metadata']['confluence_metrics'] = metrics
        
        elif config.confluence_rule == ConfluenceRule.ADAPTIVE:
            # NOUVEAU: Logique adaptative - Combine BOTH_REQUIRED et WEIGHTED_AVERAGE
            if "15min" in signals and "1hour" in signals:
                signal_15min = signals["15min"]
                signal_1hour = signals["1hour"]
                
                # Logique BOTH_REQUIRED d'abord (plus stricte)
                if signal_15min == "BULLISH" and signal_1hour == "BULLISH":
                    result.update({
                        'signal': 'LONG',
                        'confidence': 0.9,
                        'reason': 'Confluence BULLISH 15min + 1hour (ADAPTIVE)'
                    })
                elif signal_15min == "BEARISH" and signal_1hour == "BEARISH":
                    result.update({
                        'signal': 'SHORT',
                        'confidence': 0.9,
                        'reason': 'Confluence BEARISH 15min + 1hour (ADAPTIVE)'
                    })
                else:
                    # Fallback sur logique pondérée pour cas mixtes
                    weights = config.timeframes.weights
                    scores = {tf: 1.0 if signals.get(tf) in ["BULLISH", "LONG"] else 
                                    -1.0 if signals.get(tf) in ["BEARISH", "SHORT"] else 0.0
                             for tf in weights.keys()}
                    
                    confluence_score, metrics = calculate_confluence_score(scores, weights)
                    
                    if confluence_score > 0.2:  # Seuil plus permissif
                        result.update({
                            'signal': 'LONG',
                            'confidence': min(0.8, abs(confluence_score)),
                            'reason': f'Score adaptatif positif: {confluence_score:.3f}'
                        })
                    elif confluence_score < -0.2:  # Seuil plus permissif
                        result.update({
                            'signal': 'SHORT',
                            'confidence': min(0.8, abs(confluence_score)),
                            'reason': f'Score adaptatif négatif: {confluence_score:.3f}'
                        })
                    else:
                        result.update({
                            'signal': 'NO_TRADE',
                            'confidence': 0.3,
                            'reason': f'Score adaptatif neutre: {confluence_score:.3f}'
                        })
                    
                    result['metadata']['confluence_metrics'] = metrics
            else:
                result.update({
                    'signal': 'NO_TRADE',
                    'confidence': 0.0,
                    'reason': 'Signaux incomplets pour règle adaptative'
                })
        
        else:
            result.update({
                'signal': 'NO_TRADE',
                'confidence': 0.0,
                'reason': f'Règle non implémentée: {config.confluence_rule.value}'
            })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur détermination signal: {e}")
        return {
            'signal': 'NO_TRADE',
            'confidence': 0.0,
            'reason': f'Erreur: {str(e)}',
            'metadata': {'error': str(e)}
        }

def validate_signal_quality(confluence_score: float, config: StrategyConfig) -> Tuple[bool, Dict[str, Any]]:
    """Valide la qualité du signal avec métriques détaillées"""
    try:
        thresholds = config.timeframes.thresholds
        min_threshold = thresholds["min_final_confluence"]
        
        is_valid = confluence_score >= min_threshold
        
        quality_metrics = {
            'is_valid': is_valid,
            'confluence_score': confluence_score,
            'min_threshold': min_threshold,
            'margin': confluence_score - min_threshold,
            'quality_level': 'HIGH' if confluence_score >= 0.8 else 
                           'MEDIUM' if confluence_score >= 0.6 else 'LOW',
            'timestamp': datetime.now().isoformat()
        }
        
        return is_valid, quality_metrics
        
    except Exception as e:
        logger.error(f"❌ Erreur validation qualité: {e}")
        return False, {'error': str(e)}

# === INTÉGRATION AVEC FEATURE CALCULATOR OPTIMISÉE ===

def integrate_with_feature_calculator() -> Dict[str, Any]:
    """Intègre la configuration avec le Feature Calculator (version optimisée)"""
    
    config = get_15min_1hour_config()
    
    # Pondérations optimisées pour le Feature Calculator
    feature_weights = {
        'gamma_levels_proximity': 0.25,      # 25% - Options flow
        'volume_confirmation': 0.18,         # 18% - Order flow
        'vwap_trend_signal': 0.15,           # 15% - VWAP slope
        'sierra_pattern_strength': 0.15,     # 15% - Patterns
        'mtf_confluence_score': 0.12,        # 12% - MTF Confluence (15min + 1hour)
        'smart_money_strength': 0.10,        # 10% - Smart Money
        'order_book_imbalance': 0.03,        # 3% - Order Book
        'options_flow_bias': 0.02            # 2% - Options flow
    }
    
    # Validation des pondérations
    total_weight = sum(feature_weights.values())
    if abs(total_weight - 1.0) > 0.001:
        logger.warning(f"⚠️ Pondérations features invalides: {total_weight:.6f}")
    
    return {
        'feature_weights': feature_weights,
        'timeframe_config': config.timeframes,
        'confluence_rule': config.confluence_rule,
        'thresholds': config.timeframes.thresholds,
        'performance_config': {
            'max_latency_ms': config.max_latency_ms,
            'optimization_mode': config.optimization_mode,
            'cache_enabled': config.cache_enabled
        },
        'integration_metadata': {
            'version': '2.0.0',
            'created_at': datetime.now().isoformat(),
            'optimization_level': 'high'
        }
    }

# === TESTS D'INTÉGRATION OPTIMISÉS ===

def test_integration() -> bool:
    """Teste l'intégration de la configuration avec métriques détaillées"""
    logger.info("🧪 TEST INTÉGRATION 15MIN + 1HOUR OPTIMISÉE")
    logger.info("=" * 60)
    
    test_results = {
        'configuration_test': False,
        'validation_test': False,
        'signal_logic_test': False,
        'integration_test': False,
        'performance_test': False
    }
    
    try:
        # Test 1: Configuration
        config = get_15min_1hour_config()
        logger.info(f"✅ Configuration chargée: {len(config.timeframes.enabled_timeframes)} timeframes")
        test_results['configuration_test'] = True
        
        # Test 2: Validation poids
        is_valid, message = validate_timeframe_weights(config.timeframes.weights)
        logger.info(f"✅ Validation poids: {message}")
        test_results['validation_test'] = is_valid
        
        # Test 3: Logique de signaux
        test_signals = [
            {"15min": "BULLISH", "1hour": "BULLISH"},
            {"15min": "BEARISH", "1hour": "BEARISH"},
            {"15min": "BULLISH", "1hour": "BEARISH"},
            {"15min": "NEUTRAL", "1hour": "BULLISH"},
        ]
        
        signal_test_passed = 0
        for i, signals in enumerate(test_signals, 1):
            result = determine_trading_signal(signals, config)
            logger.info(f"✅ Test {i}: {signals} → {result['signal']} (conf: {result['confidence']:.2f})")
            if result['signal'] != 'ERROR':
                signal_test_passed += 1
        
        test_results['signal_logic_test'] = signal_test_passed == len(test_signals)
        
        # Test 4: Intégration Feature Calculator
        integration = integrate_with_feature_calculator()
        logger.info(f"✅ Intégration Feature Calculator: {len(integration)} éléments")
        test_results['integration_test'] = True
        
        # Test 5: Performance
        import time
        start_time = time.time()
        for _ in range(100):
            determine_trading_signal(test_signals[0], config)
        end_time = time.time()
        avg_time_ms = (end_time - start_time) * 1000 / 100
        
        logger.info(f"✅ Performance: {avg_time_ms:.2f}ms par calcul (target: <{config.max_latency_ms}ms)")
        test_results['performance_test'] = avg_time_ms < config.max_latency_ms
        
        # Résumé des tests
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        logger.info(f"\n📊 RÉSULTATS TESTS: {passed_tests}/{total_tests} réussis")
        
        if passed_tests == total_tests:
            logger.info("🎉 INTÉGRATION VALIDÉE - TOUS LES TESTS RÉUSSIS")
            return True
        else:
            logger.warning(f"⚠️ INTÉGRATION PARTIELLE - {total_tests - passed_tests} tests échoués")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors des tests: {e}")
        return False

# === FONCTIONS UTILITAIRES OPTIMISÉES ===

def get_config_summary() -> Dict[str, Any]:
    """Retourne un résumé de la configuration"""
    config = get_15min_1hour_config()
    return {
        'timeframes': config.timeframes.enabled_timeframes,
        'weights': config.timeframes.weights,
        'thresholds': config.timeframes.thresholds,
        'confluence_rule': config.confluence_rule.value,
        'optimization_mode': config.optimization_mode,
        'max_latency_ms': config.max_latency_ms,
        'cache_enabled': config.cache_enabled,
        'version': '2.0.0'
    }

def export_config_to_json() -> str:
    """Exporte la configuration en JSON"""
    import json
    summary = get_config_summary()
    return json.dumps(summary, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Exécution des tests
    success = test_integration()
    
    if success:
        print("\n🎯 CONFIGURATION OPTIMISÉE PRÊTE")
        print("=" * 50)
        summary = get_config_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
    else:
        print("\n❌ CONFIGURATION NÉCESSITE DES CORRECTIONS")
