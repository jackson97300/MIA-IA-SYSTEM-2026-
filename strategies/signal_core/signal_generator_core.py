"""
strategies/signal_core/signal_generator_core.py

Classe SignalGenerator principale refactorisée
Extrait et nettoyé du fichier original signal_generator.py (lignes 900-2200)
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import pandas as pd

from core.logger import get_logger
from core.base_types import MarketData, OrderFlowData, SignalType, MarketRegime

# Imports depuis les modules refactorisés
from .base_types import (
    SignalDecision, SignalSource, QualityLevel,
    MIN_BATTLE_NAVALE_SIGNAL_LONG, MIN_BATTLE_NAVALE_SIGNAL_SHORT,
    MIN_CONFLUENCE_SCORE, MIN_MTF_ELITE_SCORE
)
from .signal_components import SignalComponents, FinalSignal, create_no_trade_signal
from .technique_analyzers import TechniqueAnalyzers
from .confidence_calculator import ConfidenceCalculator
from .quality_validator import QualityValidator
from .stats_tracker import StatsTracker

# Imports des autres composants système
from features import create_feature_calculator, MarketRegimeDetector, ConfluenceAnalyzer
from features.market_regime import MarketRegimeData

# 🚀 NOUVELLES MÉTHODES ELITE
from core.battle_navale_elite import BattleNavaleElite
from core.menthorq_elite import MenthorQElite

from strategies.trend_strategy import TrendStrategy
from strategies.range_strategy import RangeStrategy

# 🆕 Import de la méthode MenthorQ-Distance avec Leadership (gardé pour compatibilité)
from features.leadership_zmom import LeadershipZMom
from core.menthorq_distance_trading import MenthorQDistanceTrader

logger = get_logger(__name__)

# ===== SIGNAL GENERATOR CORE =====

class SignalGenerator:
    """
    [BRAIN] CERVEAU CENTRAL - Générateur de signaux unifié REFACTORISÉ

    Workflow :
    1. Analyse tous les composants (bataille navale, features, confluence, etc.)
    2. 🆕 PHASE 3: Calcul Elite MTF Confluence multi-timeframes
    3. 🎯 TECHNIQUE #2: Analyse Smart Money institutional flows
    4. 🎯 TECHNIQUE #3: ML Ensemble Filter validation
    5. 🎯 TECHNIQUE #4: Gamma Cycles temporal optimization
    6. Détermine régime marché et stratégie appropriée
    7. Valide qualité et cohérence des signaux
    8. Génère 1 signal final unifié pour exécution

    Performance garantie : <5ms pour analyse complète
    NOUVEAU : <2ms avec cache activé
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation du générateur de signaux"""
        self.config = config or {}

        logger.info("[BRAIN] Initialisation SignalGenerator v3.6 REFACTORISÉ (TOUTES LES TECHNIQUES ELITE)...")

        # === COMPOSANTS SYSTÈME ===
        self.components = {}  # ✅ Dictionnaire pour stocker tous les composants
        self._initialize_core_components()
        self._initialize_strategies()
        
        # === MODULES REFACTORISÉS ===
        self.technique_analyzers = TechniqueAnalyzers(self.config)
        self.confidence_calculator = ConfidenceCalculator(self.config)
        self.quality_validator = QualityValidator(self.config)
        self.stats_tracker = StatsTracker(self.config)

        # === PARAMÈTRES GÉNÉRATION ===
        self._initialize_parameters()

        # === ÉTAT SYSTÈME ===
        self.last_signal: Optional[FinalSignal] = None
        self.signal_history: deque = deque(maxlen=100)
        self.current_regime: Optional[MarketRegimeData] = None

        # Log statut
        techniques_status = self.technique_analyzers.get_techniques_status()
        logger.info("SignalGenerator initialisé - Cerveau central prêt")
        logger.info(f"🎯 Techniques disponibles: MTF={techniques_status['mtf_enabled']}, "
                   f"Smart Money={techniques_status['smart_money_enabled']}, "
                   f"ML={techniques_status['ml_ensemble_enabled']}, "
                   f"Gamma={techniques_status['gamma_cycles_enabled']}")

    # ✅ Méthodes safe-getter pour accès robuste aux composants
    def _get_bn(self):
        """Accès tolérant aux différents noms/points d'injection Battle Navale"""
        return (
            getattr(self, "battle_navale", None)
            or getattr(self, "battle_navale_elite", None)
            or self.components.get("battle_navale")
            or self.components.get("battle_navale_elite")
        )

    def _get_mq(self):
        """Accès tolérant aux différents noms/points d'injection MenthorQ"""
        return (
            getattr(self, "menthorq", None)
            or getattr(self, "menthorq_elite", None)
            or self.components.get("menthorq")
            or self.components.get("menthorq_elite")
        )

    def _initialize_core_components(self):
        """Initialise les composants core du système"""
        
        # Feature Calculator avec cache optimisé
        cache_config = self.config.get('cache_config', {
            'cache_ttl': 60,     # 1 minute TTL
            'cache_size': 500    # 500 entrées max
        })

        self.feature_calculator = create_feature_calculator(config=cache_config)

        # Log du type de calculator utilisé
        calc_type = type(self.feature_calculator).__name__
        if calc_type == 'OptimizedFeatureCalculator' or hasattr(self.feature_calculator, 'cache'):
            logger.info("[OK] Feature Calculator OPTIMISÉ avec cache LRU activé")
            logger.info(f"  - Cache TTL: {cache_config.get('cache_ttl', 60)}s")
            logger.info(f"  - Cache size: {cache_config.get('cache_size', 500)} entrées")
        else:
            logger.warning("[WARN] Feature Calculator standard (sans cache)")

        # Autres composants
        self.confluence_analyzer = ConfluenceAnalyzer(self.config)
        self.market_regime = MarketRegimeDetector(self.config)
        
        # 🚀 NOUVELLES MÉTHODES ELITE
        self.battle_navale_elite = BattleNavaleElite()
        self.menthorq_elite = MenthorQElite()
        
        # ✅ Toujours définir les attributs pour compatibilité
        self.battle_navale = self.battle_navale_elite  # Alias pour compatibilité
        self.menthorq = self.menthorq_elite  # Alias pour compatibilité
        
        # ✅ Stocker dans le dictionnaire components
        self.components["battle_navale_elite"] = self.battle_navale_elite
        self.components["menthorq_elite"] = self.menthorq_elite
        self.components["battle_navale"] = self.battle_navale  # Alias
        self.components["menthorq"] = self.menthorq  # Alias
        
        logger.info("[OK] 🚀 Battle Navale Elite initialisé")
        logger.info("[OK] 🧠 MenthorQ Elite initialisé")

        # 🆕 PHASE 3: Connection MTF Elite avec Battle Navale Elite
        self.confluence_analyzer.set_battle_navale_analyzer(self.battle_navale_elite)
        logger.info("[OK] 🚀 Elite MTF Confluence connectée avec Battle Navale Elite")
        
        # 🆕 MenthorQ Distance Trader avec Leadership Z-Momentum (gardé pour compatibilité)
        self.menthorq_distance_trader = MenthorQDistanceTrader()
        logger.info("[OK] 🎯 MenthorQ Distance Trader avec Leadership Z-Momentum initialisé")

    def _initialize_strategies(self):
        """Initialise les stratégies de trading"""
        self.trend_strategy = TrendStrategy(self.config)
        self.range_strategy = RangeStrategy(self.config)

    def _initialize_parameters(self):
        """Initialise les paramètres de génération"""
        
        self.min_confidence = self.config.get('min_signal_confidence', 0.70)
        self.min_confluence = self.config.get('min_confluence_score', MIN_CONFLUENCE_SCORE)
        self.min_risk_reward = self.config.get('min_risk_reward', 1.5)
        self.max_position_size = self.config.get('max_position_size', 3.0)

        # === PRIORITÉ #2: PARAMÈTRES NOUVEAUX SEUILS ===
        self.battle_navale_long_threshold = self.config.get(
            'battle_long_threshold', MIN_BATTLE_NAVALE_SIGNAL_LONG)
        self.battle_navale_short_threshold = self.config.get(
            'battle_short_threshold', MIN_BATTLE_NAVALE_SIGNAL_SHORT)

        logger.info(f"🎯 PRIORITÉ #2: Seuils Battle Navale: LONG>{self.battle_navale_long_threshold}, SHORT<{self.battle_navale_short_threshold}")

    def generate_signal(self,
                        market_data: MarketData,
                        order_flow: Optional[OrderFlowData] = None,
                        options_data: Optional[Dict[str, Any]] = None,
                        structure_data: Optional[Dict[str, Any]] = None,
                        sierra_patterns: Optional[Dict[str, float]] = None) -> FinalSignal:
        """
        [TARGET] GÉNÉRATION SIGNAL PRINCIPAL REFACTORISÉ

        Workflow complet d'analyse et génération signal final
        """
        start_time = time.time()
        cache_hits_start = self._get_cache_hits()

        try:
            # 1. ANALYSE COMPLÈTE DE TOUS LES COMPOSANTS
            components = self._analyze_all_components(
                market_data, order_flow, options_data,
                structure_data, sierra_patterns
            )

            # 2. ANALYSE TOUTES LES TECHNIQUES ELITE
            technique_start = time.time()
            self.technique_analyzers.analyze_all_techniques(
                market_data, order_flow, components
            )
            technique_time = (time.time() - technique_start) * 1000
            logger.debug(f"🎯 Toutes techniques analysées en {technique_time:.2f}ms")

            # 3. VALIDATION QUALITÉ MINIMALE (TOUTES TECHNIQUES)
            if not self.quality_validator.validate_signal_quality_v6(components):
                return self._create_no_trade_signal(
                    market_data, components,
                    self.quality_validator.get_rejection_reason(components)
                )

            # 4. SÉLECTION STRATÉGIE SELON RÉGIME
            strategy_signal = self._select_and_execute_strategy(components, market_data)

            if not strategy_signal:
                return self._create_no_trade_signal(
                    market_data, components,
                    "Aucun signal stratégie valide"
                )

            # 5. VALIDATION CONFLUENCE FINALE (INCLUANT TOUTES TECHNIQUES)
            confluence_valid = self.quality_validator.validate_confluence_v3(
                components, strategy_signal
            )

            if not confluence_valid:
                return self._create_no_trade_signal(
                    market_data, components,
                    "Confluence insuffisante (incluant MTF + Smart Money + ML + Gamma)"
                )

            # 6. CONSTRUCTION SIGNAL FINAL
            final_signal = self._build_final_signal(
                market_data, components, strategy_signal
            )

            # 7. RISK MANAGEMENT VALIDATION
            if not self.quality_validator.validate_risk_parameters(final_signal):
                return self._create_no_trade_signal(
                    market_data, components,
                    "Paramètres risk invalides"
                )

            # 8. APPLY ELITE BONUSES
            self._apply_elite_bonuses(final_signal)

            # 9. FINALIZATION
            cache_hits_end = self._get_cache_hits()
            final_signal.cache_hits = cache_hits_end - cache_hits_start

            execution_time = (time.time() - start_time) * 1000
            final_signal.generation_time_ms = execution_time

            # 10. TRACKING ET STATS
            self.stats_tracker.track_signal_frequency_v5(components)
            self.stats_tracker.update_stats(final_signal, execution_time)
            self.stats_tracker.update_cache_stats_periodically(self.feature_calculator)

            self.last_signal = final_signal
            self.signal_history.append(final_signal)

            # Log performance complet
            self._log_signal_performance(final_signal, execution_time)

            return final_signal

        except Exception as e:
            logger.error(f"Erreur génération signal: {e}")
            return self._create_error_signal(market_data, str(e))

    # 🆕 MÉTHODE MENTHORQ-DISTANCE AVEC LEADERSHIP Z-MOMENTUM
    
    def decide_mq_distance(self, row_es: Dict[str, Any], row_nq: Dict[str, Any], config: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Méthode MenthorQ-Distance avec Leadership Z-Momentum intégrée
        
        Architecture :
        1. MenthorQ décide (décideur principal)
        2. MIA Bullish valide (biais interne bidirectionnel)
        3. Leadership Z-Momentum gate + bonus
        4. OrderFlow valide (timing)
        5. Structure contextuelle
        6. Fusion des scores + modulateurs
        7. E/U/L
        
        Args:
            row_es: Ligne unified ES (mia_unifier)
            row_nq: Ligne unified NQ (mia_unifier)
            config: Configuration avec tolérances, seuils, pondérations
            
        Returns:
            Dict avec signal final ou None si pas de trade
        """
        if not config:
            config = {
                "tick_size": 0.25,
                "mq_tolerance_ticks": {"gamma_wall": 3, "hvl": 5, "gex": 5},
                "mia_threshold": 0.20,
                "entry_threshold": 0.70,
                "weights": {"mq": 0.55, "of": 0.30, "structure": 0.15}
            }
        
        try:
            # Utiliser la méthode intégrée du MenthorQ Distance Trader
            signal = self.menthorq_distance_trader.decide_mq_distance_integrated(
                row_es=row_es,
                row_nq=row_nq,
                config=config
            )
            
            if signal:
                logger.info(f"🎯 Signal MenthorQ-Distance: {signal['action']} (Score: {signal['score']})")
                logger.info(f"   Leadership: LS={signal['leadership']['ls']}, Bonus={signal['leadership']['bonus']}")
                logger.info(f"   E/U/L: Entry={signal['eul']['entry']}, Stop={signal['eul']['stop']}")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Erreur dans decide_mq_distance: {e}")
            return None

    def _analyze_all_components(self,
                                market_data: MarketData,
                                order_flow: Optional[OrderFlowData],
                                options_data: Optional[Dict[str, Any]],
                                structure_data: Optional[Dict[str, Any]],
                                sierra_patterns: Optional[Dict[str, float]]) -> SignalComponents:
        """Analyse complète de tous les composants"""

        components = SignalComponents(timestamp=market_data.timestamp)

        try:
            # 1. CALCUL FEATURES AVEC CONFLUENCE (OPTIMISÉ)
            components.features = self.feature_calculator.calculate_all_features(
                market_data=market_data,
                order_flow=order_flow,
                options_data=options_data,
                structure_data=structure_data,
                sierra_patterns=sierra_patterns
            )

            # 2. ANALYSE BATAILLE NAVALE
            components.battle_navale = self.battle_navale.analyze_battle_navale(
                market_data, order_flow)

            # 3. DÉTECTION RÉGIME MARCHÉ
            components.market_regime = self.market_regime.analyze_market_regime(market_data)
            self.current_regime = components.market_regime

            # 4. ANALYSE CONFLUENCE MULTI-NIVEAUX
            if structure_data:
                components.confluence_analysis = self.confluence_analyzer.analyze_confluence(
                    market_data=market_data,
                    gamma_data=structure_data.get('gamma_data'),
                    market_profile_data=structure_data.get('market_profile_data'),
                    vwap_data=structure_data.get('vwap_data'),
                    volume_data=structure_data.get('volume_data'),
                    session_data=structure_data.get('session_data')
                )

            # 5. ÉVALUATION RISK
            components.risk_assessment = self._assess_risk_metrics(market_data, components)

        except Exception as e:
            logger.error(f"Erreur analyse composants: {e}")

        return components

    def _select_and_execute_strategy(self,
                                     components: SignalComponents,
                                     market_data: MarketData) -> Optional[Any]:
        """Sélection et exécution de la stratégie appropriée"""

        if not components.market_regime:
            return None

        regime = components.market_regime.regime

        # TREND STRATEGY
        if regime in [MarketRegime.TREND_BULLISH, MarketRegime.TREND_BEARISH]:
            return self.trend_strategy.analyze_trend_opportunity(
                market_data=market_data,
                regime_data=components.market_regime,
                features=components.features,
                battle_navale=components.battle_navale
            )

        # RANGE STRATEGY
        elif regime in [MarketRegime.RANGE_TIGHT, MarketRegime.RANGE_WIDE]:
            return self.range_strategy.analyze_range_opportunity(
                market_data=market_data,
                regime_data=components.market_regime,
                features=components.features,
                sierra_patterns=components.features  # Features incluent patterns
            )

        # TRANSITION - Plus conservateur
        else:
            logger.debug("Régime en transition - pas de signal")
            return None

    def _build_final_signal(self,
                            market_data: MarketData,
                            components: SignalComponents,
                            strategy_signal: Any) -> FinalSignal:
        """Construction du signal final complet"""

        # Déterminer décision finale
        decision, signal_type = self._determine_signal_decision(strategy_signal)

        # Calcul confidence finale avec toutes les techniques
        confidence = self.confidence_calculator.calculate_final_confidence_v4(
            components, strategy_signal
        )

        # Quality level avec toutes les techniques Elite
        quality_level = self.confidence_calculator.determine_quality_level_v4(
            confidence, components
        )

        # Position sizing avec toutes les techniques
        position_size = self.confidence_calculator.calculate_position_size_v3(
            confidence, components
        )

        # Risk parameters
        entry_price = getattr(strategy_signal, 'entry_price', market_data.close)
        stop_loss = getattr(strategy_signal, 'stop_loss', entry_price - 2.0)
        take_profit = getattr(strategy_signal, 'take_profit', entry_price + 4.0)

        # Risk/Reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0

        # Source avec priorités Elite
        source = self._determine_signal_source_v3(components, strategy_signal)

        return FinalSignal(
            timestamp=market_data.timestamp,
            decision=decision,
            signal_type=signal_type,
            confidence=confidence,
            quality_level=quality_level,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            source=source,
            regime=components.market_regime.regime if components.market_regime else MarketRegime.UNKNOWN,
            components=components,
            reasoning=self._generate_reasoning_v4(components, strategy_signal),
            risk_reward_ratio=risk_reward_ratio,
            max_risk_dollars=self._calculate_max_risk_dollars(position_size, risk),
            generation_time_ms=0,  # Sera mis à jour
            metadata=self._build_metadata(components)
        )

    def _determine_signal_decision(self, strategy_signal: Any) -> Tuple[SignalDecision, SignalType]:
        """Détermine la décision et le type de signal"""
        
        if hasattr(strategy_signal, 'signal_type'):
            if strategy_signal.signal_type in ['LONG_TREND', 'LONG_RANGE']:
                decision = SignalDecision.EXECUTE_LONG
                signal_type = SignalType.LONG_TREND if 'TREND' in strategy_signal.signal_type else SignalType.LONG_RANGE
            elif strategy_signal.signal_type in ['SHORT_TREND', 'SHORT_RANGE']:
                decision = SignalDecision.EXECUTE_SHORT
                signal_type = SignalType.SHORT_TREND if 'TREND' in strategy_signal.signal_type else SignalType.SHORT_RANGE
            else:
                decision = SignalDecision.NO_TRADE
                signal_type = SignalType.NO_SIGNAL
        else:
            decision = SignalDecision.NO_TRADE
            signal_type = SignalType.NO_SIGNAL
            
        return decision, signal_type

    def _determine_signal_source_v3(self, components: SignalComponents, strategy_signal: Any) -> SignalSource:
        """Détermine la source du signal avec priorités Elite"""
        
        # 🎯 TECHNIQUE #4: Gamma Cycle Optimized prioritaire si Ultimate Elite
        if (components.ml_ensemble_prediction and
            getattr(components.ml_ensemble_prediction, 'signal_approved', False) and
            getattr(components.ml_ensemble_prediction, 'confidence', 0) > 0.85 and
            components.mtf_confluence_score is not None and
            abs(components.mtf_confluence_score) > MIN_MTF_ELITE_SCORE and
            components.smart_money_institutional_score and
            components.smart_money_institutional_score > 0.7 and
            components.gamma_cycle_analysis and
            hasattr(components.gamma_cycle_analysis, 'gamma_phase')):
            
            from .base_types import GammaPhase
            if components.gamma_cycle_analysis.gamma_phase in [GammaPhase.GAMMA_PEAK, GammaPhase.GAMMA_MODERATE]:
                return SignalSource.GAMMA_CYCLE_OPTIMIZED

        # 🎯 TECHNIQUE #3: ML Ensemble Validated
        if (components.ml_ensemble_prediction and
            getattr(components.ml_ensemble_prediction, 'signal_approved', False) and
            getattr(components.ml_ensemble_prediction, 'confidence', 0) > 0.85):
            return SignalSource.ML_ENSEMBLE_VALIDATED

        # 🎯 TECHNIQUE #2: Smart Money Institutional
        if (components.smart_money_institutional_score and
            components.smart_money_institutional_score > 0.7):
            return SignalSource.SMART_MONEY_INSTITUTIONAL

        # 🆕 PHASE 3: MTF Elite
        if (components.mtf_confluence_score is not None and
            abs(components.mtf_confluence_score) > MIN_MTF_ELITE_SCORE):
            return SignalSource.MTF_ELITE_CONFLUENCE

        # Sources traditionnelles
        if components.battle_navale and getattr(components.battle_navale, 'battle_navale_signal', 0) > 0.7:
            return SignalSource.BATTLE_NAVALE
        elif hasattr(strategy_signal, 'signal_type') and 'TREND' in str(strategy_signal.signal_type):
            return SignalSource.TREND_STRATEGY
        else:
            return SignalSource.RANGE_STRATEGY

    def _generate_reasoning_v4(self, components: SignalComponents, strategy_signal: Any) -> str:
        """Génère le reasoning avec toutes les techniques"""
        
        reasons = []

        # Régime
        if components.market_regime:
            reasons.append(f"Régime: {components.market_regime.regime.value}")

        # Battle Navale
        if components.battle_navale:
            battle_signal = getattr(components.battle_navale, 'battle_navale_signal', 0)
            if battle_signal > self.battle_navale_long_threshold:
                reasons.append(f"Battle Navale LONG fort ({battle_signal:.3f}>{self.battle_navale_long_threshold})")
            elif battle_signal < self.battle_navale_short_threshold:
                reasons.append(f"Battle Navale SHORT fort ({battle_signal:.3f}<{self.battle_navale_short_threshold})")

        # Techniques Elite
        if components.mtf_confluence_score is not None:
            mtf_score = components.mtf_confluence_score
            if abs(mtf_score) > MIN_MTF_ELITE_SCORE:
                direction = "LONG" if mtf_score > 0 else "SHORT"
                reasons.append(f"🏆 MTF Elite {direction} ({mtf_score:.3f})")

        if components.smart_money_confidence and components.smart_money_confidence > 0.6:
            reasons.append(f"🎯 Smart Money détecté ({components.smart_money_confidence:.3f})")

        if components.ml_ensemble_prediction and getattr(components.ml_ensemble_prediction, 'signal_approved', False):
            ml_conf = getattr(components.ml_ensemble_prediction, 'confidence', 0)
            reasons.append(f"🎯 ML Ensemble validé ({ml_conf:.3f})")

        if components.gamma_cycle_analysis:
            gamma_phase = getattr(components.gamma_cycle_analysis, 'gamma_phase', None)
            if gamma_phase:
                reasons.append(f"🎯 Gamma Phase: {gamma_phase.value}")

        # Check signal Elite complet
        techniques_validated = self._count_validated_techniques(components)
        if techniques_validated >= 4:
            if techniques_validated == 5:
                reasons.append(f"🚀 SIGNAL ULTIMATE ELITE (5/5 techniques)")
            else:
                reasons.append(f"🏆 SIGNAL ELITE COMPLET ({techniques_validated}/5 techniques)")

        # Strategy
        if hasattr(strategy_signal, 'reasoning'):
            reasons.append(strategy_signal.reasoning)

        reasons.append(f"v3.6 Refactorisé: TOUTES TECHNIQUES ELITE activées")

        return " | ".join(reasons)

    def _count_validated_techniques(self, components: SignalComponents) -> int:
        """Compte le nombre de techniques Elite validées"""
        
        count = 0
        
        if components.battle_navale and getattr(components.battle_navale, 'battle_navale_signal', 0) > self.battle_navale_long_threshold:
            count += 1
        if components.mtf_confluence_score and abs(components.mtf_confluence_score) > MIN_MTF_ELITE_SCORE:
            count += 1
        if components.smart_money_institutional_score and components.smart_money_institutional_score > 0.7:
            count += 1
        if components.ml_ensemble_prediction and getattr(components.ml_ensemble_prediction, 'signal_approved', False):
            count += 1
        if components.gamma_cycle_analysis:
            from .base_types import GammaPhase
            gamma_phase = getattr(components.gamma_cycle_analysis, 'gamma_phase', None)
            if gamma_phase in [GammaPhase.GAMMA_PEAK, GammaPhase.GAMMA_MODERATE]:
                count += 1
                
        return count

    def _apply_elite_bonuses(self, signal: FinalSignal):
        """Applique tous les bonus Elite au signal"""
        
        # 🆕 PHASE 3: Bonus Elite MTF
        if signal.meets_mtf_elite_threshold():
            self._apply_mtf_elite_bonus(signal)

        # 🎯 TECHNIQUE #2: Bonus Smart Money
        if signal.is_institutional_signal():
            self._apply_smart_money_institutional_bonus(signal)

        if signal.has_smart_money_alignment():
            self._apply_smart_money_alignment_bonus(signal)

        # 🎯 TECHNIQUE #3: Bonus ML Ensemble
        if signal.has_ml_high_confidence():
            self._apply_ml_ensemble_high_confidence_bonus(signal)

        if signal.is_ml_validated_signal():
            self._apply_ml_validated_upgrade(signal)

        # 🎯 TECHNIQUE #4: Bonus Gamma Cycles
        if signal.meets_gamma_optimization_criteria():
            self._apply_gamma_cycles_optimization(signal)

        if signal.is_ultimate_elite_signal():
            self._apply_ultimate_elite_upgrade(signal)

    def _apply_mtf_elite_bonus(self, signal: FinalSignal):
        """Bonus MTF Elite"""
        if signal.quality_level != QualityLevel.ELITE:
            signal.quality_level = QualityLevel.ELITE
        original_confidence = signal.confidence
        signal.confidence = min(1.0, signal.confidence * 1.15)
        if signal.confidence > 0.85:
            signal.position_size = min(self.max_position_size, signal.position_size * 1.25)
        signal.metadata['mtf_elite_bonus'] = signal.confidence - original_confidence

    def _apply_smart_money_institutional_bonus(self, signal: FinalSignal):
        """Bonus Smart Money Institutional"""
        signal.quality_level = QualityLevel.INSTITUTIONAL
        original_confidence = signal.confidence
        institutional_score = signal.get_smart_money_institutional_score()
        boost_factor = 1.0 + (institutional_score * 0.12)
        signal.confidence = min(1.0, signal.confidence * boost_factor)
        if institutional_score > 0.8:
            signal.position_size = min(self.max_position_size, signal.position_size * 1.20)
        signal.metadata['smart_money_institutional_bonus'] = signal.confidence - original_confidence

    def _apply_smart_money_alignment_bonus(self, signal: FinalSignal):
        """Bonus Smart Money Alignment"""
        original_confidence = signal.confidence
        signal.confidence = min(1.0, signal.confidence * 1.15)
        signal.position_size = min(self.max_position_size, signal.position_size * 1.10)
        signal.metadata['smart_money_alignment_bonus'] = signal.confidence - original_confidence

    def _apply_ml_ensemble_high_confidence_bonus(self, signal: FinalSignal):
        """Bonus ML Ensemble High Confidence"""
        if signal.components.ml_ensemble_prediction:
            original_confidence = signal.confidence
            signal.confidence = min(1.0, signal.confidence * 1.08)
            ml_confidence = getattr(signal.components.ml_ensemble_prediction, 'confidence', 0)
            if ml_confidence > 0.85:
                signal.position_size = min(self.max_position_size, signal.position_size * 1.15)
            signal.metadata['ml_high_confidence_bonus'] = signal.confidence - original_confidence

    def _apply_ml_validated_upgrade(self, signal: FinalSignal):
        """Upgrade ML Validated"""
        signal.quality_level = QualityLevel.ML_VALIDATED
        signal.source = SignalSource.ML_ENSEMBLE_VALIDATED
        original_confidence = signal.confidence
        signal.confidence = min(1.0, signal.confidence * 1.05)
        signal.metadata['ml_validated_upgrade'] = signal.confidence - original_confidence

    def _apply_gamma_cycles_optimization(self, signal: FinalSignal):
        """Optimisation Gamma Cycles"""
        if signal.components.gamma_cycle_analysis:
            gamma_analysis = signal.components.gamma_cycle_analysis
            original_confidence = signal.confidence
            original_position_size = signal.position_size
            
            signal.confidence = min(1.0, signal.confidence * getattr(gamma_analysis, 'confidence_adjustment', 1.0))
            signal.position_size = min(self.max_position_size, 
                                     signal.position_size * getattr(gamma_analysis, 'position_size_adjustment', 1.0))
            
            from .base_types import GammaPhase
            if getattr(gamma_analysis, 'gamma_phase', None) == GammaPhase.GAMMA_PEAK:
                if signal.quality_level not in [QualityLevel.ML_VALIDATED, QualityLevel.ELITE, QualityLevel.ULTIMATE_ELITE]:
                    signal.quality_level = QualityLevel.GAMMA_OPTIMIZED
            
            signal.metadata['gamma_optimization'] = {
                'confidence_boost': signal.confidence - original_confidence,
                'position_boost': signal.position_size - original_position_size,
                'gamma_phase': getattr(gamma_analysis, 'gamma_phase', 'unknown').value if hasattr(getattr(gamma_analysis, 'gamma_phase', None), 'value') else 'unknown'
            }

    def _apply_ultimate_elite_upgrade(self, signal: FinalSignal):
        """Upgrade Ultimate Elite"""
        signal.quality_level = QualityLevel.ULTIMATE_ELITE
        signal.source = SignalSource.GAMMA_CYCLE_OPTIMIZED
        original_confidence = signal.confidence
        signal.confidence = min(1.0, signal.confidence * 1.10)
        signal.position_size = min(self.max_position_size, signal.position_size * 1.50)
        signal.metadata['ultimate_elite_upgrade'] = signal.confidence - original_confidence

    def _assess_risk_metrics(self, market_data: MarketData, components: SignalComponents) -> Dict[str, float]:
        """Évaluation métriques de risque"""
        
        risk_metrics = {
            'volatility': 0.5,
            'trend_strength': 0.5,
            'support_resistance_distance': 2.0,
            'time_of_day_risk': 0.5
        }

        if components.market_regime:
            risk_metrics['volatility'] = getattr(components.market_regime, 'volatility', 0.5)

        if components.confluence_analysis:
            if hasattr(components.confluence_analysis, 'nearest_support_zone'):
                support = getattr(components.confluence_analysis.nearest_support_zone, 'center_price', market_data.close)
                risk_metrics['support_resistance_distance'] = abs(market_data.close - support)

        # Time of day risk
        hour = market_data.timestamp.hour
        if hour < 10 or hour > 15:
            risk_metrics['time_of_day_risk'] = 0.7

        return risk_metrics

    def _calculate_max_risk_dollars(self, position_size: float, risk: float) -> float:
        """Calcule le risque maximum en dollars"""
        from core.base_types import ES_TICK_VALUE, ES_TICK_SIZE
        return position_size * risk * ES_TICK_VALUE / ES_TICK_SIZE

    def _build_metadata(self, components: SignalComponents) -> Dict[str, Any]:
        """Construit les métadonnées du signal"""
        
        return {
            'features_count': len(components.features.__dict__) if hasattr(components.features, '__dict__') else 0,
            'battle_navale_signal': getattr(components.battle_navale, 'battle_navale_signal', 0) if components.battle_navale else 0,
            'confluence_score': getattr(components.features, 'confluence_score', 0) if components.features else 0,
            'battle_long_threshold': self.battle_navale_long_threshold,
            'battle_short_threshold': self.battle_navale_short_threshold,
            'mtf_confluence_score': components.mtf_confluence_score,
            'smart_money_confidence': components.smart_money_confidence,
            'ml_ensemble_confidence': components.ml_ensemble_confidence,
            'gamma_adjustment_factor': components.gamma_adjustment_factor,
            'refactored': True,
            'version': 'v3.6_refactored'
        }

    def _create_no_trade_signal(self, market_data: MarketData, components: SignalComponents, reason: str) -> FinalSignal:
        """Création signal NO_TRADE avec raison"""
        return create_no_trade_signal(market_data.timestamp, reason)

    def _create_error_signal(self, market_data: MarketData, error: str) -> FinalSignal:
        """Signal d'erreur"""
        return create_no_trade_signal(market_data.timestamp, f"Erreur: {error}")

    def _get_cache_hits(self) -> int:
        """Récupère nombre total de cache hits"""
        if hasattr(self.feature_calculator, 'get_cache_stats'):
            stats = self.feature_calculator.get_cache_stats()
            return stats.get('cache_hits', 0)
        return 0

    def _log_signal_performance(self, signal: FinalSignal, execution_time: float):
        """Log performance complet du signal"""
        
        battle_strength = signal.get_battle_navale_strength()
        mtf_strength = signal.get_mtf_confluence_strength()
        smart_money_strength = signal.get_smart_money_strength()
        ml_confidence = signal.get_ml_ensemble_confidence()
        gamma_factor = signal.get_gamma_adjustment_factor()

        elite_status = "🏆 ULTIMATE_ELITE" if signal.is_ultimate_elite_signal() else \
                      "🏆 ML_VALIDATED" if signal.is_ml_validated_signal() else \
                      "🏆 ELITE" if signal.is_elite_signal() else \
                      "🎯 INSTITUTIONAL" if signal.is_institutional_signal() else \
                      "🎯 GAMMA_OPTIMIZED" if signal.meets_gamma_optimization_criteria() else \
                      "✅ STANDARD"

        logger.info(f"🎯 Signal {elite_status} généré en {execution_time:.2f}ms "
                    f"(Cache hits: {signal.cache_hits}): "
                    f"{signal.decision.value} "
                    f"(Confidence: {signal.confidence:.3f}, "
                    f"Battle: {battle_strength:.3f}, MTF: {mtf_strength:.3f}, "
                    f"Smart Money: {smart_money_strength:.3f}, ML: {ml_confidence:.3f}, "
                    f"Gamma: {gamma_factor:.2f})")

    # ===== MÉTHODES PUBLIQUES POUR COMPATIBILITÉ =====

    def get_performance_stats(self) -> Dict[str, Any]:
        """Statistiques performance complètes"""
        return self.stats_tracker.get_performance_stats(self.feature_calculator)

    def get_priority_2_summary(self) -> Dict[str, Any]:
        """Résumé PRIORITÉ #2"""
        return self.stats_tracker.get_priority_2_summary()

    def get_techniques_summary(self) -> Dict[str, Any]:
        """Résumé de toutes les techniques"""
        return self.stats_tracker.get_techniques_summary()

    def clear_cache(self):
        """Vide le cache"""
        if hasattr(self.feature_calculator, 'clear_cache'):
            self.feature_calculator.clear_cache()
            logger.info("[OK] Cache vidé dans SignalGenerator")

# ===== EXPORTS =====
__all__ = [
    'SignalGenerator'
]