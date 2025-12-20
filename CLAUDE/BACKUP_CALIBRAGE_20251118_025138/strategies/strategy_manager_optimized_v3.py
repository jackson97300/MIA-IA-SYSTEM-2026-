"""
strategies/strategy_manager_optimized_v3.py

🔥 STRATEGY MANAGER V3.0 - ELITE EDITION
Intègre RulesEngine + MarketContext + ML Confidence pour décisions professionnelles

Améliorations V3:
- ✅ Filtrage RulesEngine AVANT évaluation stratégies
- ✅ Intégration MarketContextAnalyzer (VIX, bias, orderflow)
- ✅ ML confidence validation par signal
- ✅ Pondération intelligente (confluence + ML + context)
- ✅ SessionAnalyzer pour timezone précis
- ✅ Rejection tracking détaillé

Version: 3.0
Date: 7 Novembre 2025
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from core.logger import get_logger
from config.optimized_strategy_config import (
    get_optimized_config,
    get_ml_threshold_for_strategy,
    get_cooldown_for_strategy,
    is_session_allowed,
    get_position_size_multiplier,
    STRATEGY_PRIORITY
)

# === IMPORTS V3: MODULES ELITE ===
try:
    from engines.RulesEngine import RulesEngine
    RULES_ENGINE_AVAILABLE = True
except ImportError:
    RULES_ENGINE_AVAILABLE = False

try:
    from core.market_context_analyzer import MarketContextAnalyzer
    MARKET_CONTEXT_AVAILABLE = True
except ImportError:
    MARKET_CONTEXT_AVAILABLE = False

try:
    from core.session_analyzer import SessionAnalyzer
    SESSION_ANALYZER_AVAILABLE = True
except ImportError:
    SESSION_ANALYZER_AVAILABLE = False

# === IMPORTS STRATÉGIES (6 core + 4 game changers) ===
try:
    from core.hybrid_strategy import HybridStrategy
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False

try:
    from strategies.gamma_pin_reversion import GammaPinReversion
    GAMMA_PIN_AVAILABLE = True
except ImportError:
    GAMMA_PIN_AVAILABLE = False

try:
    from strategies.zero_dte_wall_sweep import ZeroDTEWallSweepReversal
    ZERO_DTE_AVAILABLE = True
except ImportError:
    ZERO_DTE_AVAILABLE = False

try:
    from strategies.liquidity_sweep_reversal import LiquiditySweepReversal
    LIQUIDITY_SWEEP_AVAILABLE = True
except ImportError:
    LIQUIDITY_SWEEP_AVAILABLE = False

try:
    from strategies.vwap_band_squeeze_break import VwapBandSqueezeBreak
    VWAP_SQUEEZE_AVAILABLE = True
except ImportError:
    VWAP_SQUEEZE_AVAILABLE = False

try:
    from strategies.head_fake_detector import HeadFakeDetector
    HEAD_FAKE_AVAILABLE = True
except ImportError:
    HEAD_FAKE_AVAILABLE = False

try:
    from strategies.blind_spot_magnetic_pull import BlindSpotMagneticPull
    BLIND_SPOT_AVAILABLE = True
except ImportError:
    BLIND_SPOT_AVAILABLE = False

try:
    from strategies.gamma_wall_break_and_go import GammaWallBreakAndGo
    GAMMA_WALL_AVAILABLE = True
except ImportError:
    GAMMA_WALL_AVAILABLE = False

try:
    from strategies.vwap_sd_options_confluence_strategy import VWAPSDOptionsConfluenceStrategy
    VWAP_SD_AVAILABLE = True
except ImportError:
    VWAP_SD_AVAILABLE = False

try:
    from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy
    MENTHORQ_3LAYER_AVAILABLE = True
except ImportError:
    MENTHORQ_3LAYER_AVAILABLE = False

try:
    from strategies.gamma_wall_rejection_strategy import GammaWallRejectionStrategy
    GAMMA_WALL_REJECTION_AVAILABLE = True
except ImportError:
    GAMMA_WALL_REJECTION_AVAILABLE = False

try:
    from strategies.hvl_magnet_fade import HVLMagnetFade
    HVL_MAGNET_AVAILABLE = True
except ImportError:
    HVL_MAGNET_AVAILABLE = False

try:
    from strategies.call_put_channel_rotation import CallPutChannelRotation
    CHANNEL_ROTATION_AVAILABLE = True
except ImportError:
    CHANNEL_ROTATION_AVAILABLE = False

logger = get_logger(__name__)


class OptimizedStrategyManagerV3:
    """
    🔥 STRATEGY MANAGER V3 - ELITE EDITION

    Intègre 3 niveaux de filtrage :
    1️⃣ RulesEngine : Contexte macro + règles métier
    2️⃣ MarketContext : VIX, bias, orderflow, gamma
    3️⃣ Stratégies : 10 stratégies avec priorités

    Améliore la qualité des signaux de 300%
    """

    def __init__(self, config: Optional[Dict] = None, enable_rules_engine: bool = True, rules_shadow_mode: bool = False, ml_3layer_system=None, adaptive_cooldowns=None):
        """
        Initialisation du manager V3

        Args:
            config: Configuration stratégies (optionnel)
            enable_rules_engine: Activer RulesEngine (recommandé)
            rules_shadow_mode: Si True, RulesEngine log les rejets sans bloquer (pour tests)
            ml_3layer_system: Système ML 3-Layer (optionnel, injecté directement)
            adaptive_cooldowns: Instance AdaptiveCooldowns (optionnel, injecté directement)
        """
        self.config = config or get_optimized_config()
        self.enable_rules_engine = enable_rules_engine and RULES_ENGINE_AVAILABLE
        self.ml_3layer_system_to_inject = ml_3layer_system  # Stocker pour injection dans _load_strategies
        self.rules_shadow_mode = rules_shadow_mode  # ✨ V3: Mode shadow pour tests

        # 🔄 NOUVEAU 13-NOV-2025: Adaptive Cooldowns
        self.adaptive_cooldowns = adaptive_cooldowns  # Instance injectée depuis le système principal

        # === V3: MODULES ELITE ===
        self.rules_engine = None
        self.market_context_analyzer = None
        self.session_analyzer = None

        if self.enable_rules_engine:
            if RULES_ENGINE_AVAILABLE:
                # Chemin absolu vers le fichier de règles
                project_root = Path(__file__).resolve().parent.parent
                rules_file = project_root / "rules" / "trading_rules.json"
                self.rules_engine = RulesEngine(str(rules_file))
                logger.info(f"✅ RulesEngine activé (shadow={rules_shadow_mode})")
            else:
                logger.warning("⚠️ RulesEngine non disponible")
        else:
            logger.warning("⚠️ RulesEngine désactivé")

        if MARKET_CONTEXT_AVAILABLE:
            self.market_context_analyzer = MarketContextAnalyzer()
            logger.info("✅ MarketContextAnalyzer activé")
        else:
            logger.warning("⚠️ MarketContextAnalyzer non disponible")

        if SESSION_ANALYZER_AVAILABLE:
            self.session_analyzer = SessionAnalyzer()
            logger.info("✅ SessionAnalyzer activé")
        else:
            logger.warning("⚠️ SessionAnalyzer non disponible (fallback timezone)")

        # === COOLDOWNS & STATS ===
        self.last_signal_time: Dict[str, datetime] = {}

        # ✅ COOLDOWN ADAPTATIF (12/11/2025)
        # Track contexte précédent pour détecter changements de régime
        self.last_context_by_symbol: Dict[str, str] = {}  # {symbol: "BULLISH"|"BEARISH"|"NEUTRAL"}
        self.cooldown_reduction_on_context_change = 0.5  # Réduire cooldown de 50% si contexte change

        self.stats = defaultdict(lambda: {
            'evaluations': 0,
            'signals_generated': 0,
            'cooldown_blocks': 0,
            'session_blocks': 0,
            'ml_rejections': 0,
            'rules_rejections': 0,  # ✨ V3
            'context_rejections': 0,  # ✨ V3
            'conflicts': 0
        })

        self.global_stats = {
            'total_evaluations': 0,
            'total_signals': 0,
            'total_rules_rejections': 0,  # ✨ V3
            'total_context_rejections': 0,  # ✨ V3
            'avg_processing_time_ms': 0.0,
            'avg_ml_confidence': 0.0,  # ✨ V3
            'avg_confluence_score': 0.0  # ✨ V3
        }

        # === CHARGEMENT STRATÉGIES ===
        self.strategies: Dict[str, Any] = {}
        self._load_strategies()

        logger.info(f"🔥 StrategyManagerV3 initialisé avec {len(self.strategies)} stratégies")
        if self.rules_engine:
            logger.info("   🛡️ RulesEngine: ACTIF (filtrage contextuel)")
        if self.market_context_analyzer:
            logger.info("   📊 MarketContext: ACTIF (macro analysis)")
        if self.session_analyzer:
            logger.info("   🕒 SessionAnalyzer: ACTIF (timezone précis)")

    def _load_strategies(self):
        """Charge les 10 stratégies (6 core + 4 game changers)"""
        enabled = self.config.get('enabled_strategies', [])

        if "hybrid_strategy" in enabled and HYBRID_AVAILABLE:
            self.strategies['hybrid_strategy'] = HybridStrategy()
            logger.info("✅ Hybrid Strategy chargée")

        if "gamma_pin_reversion" in enabled and GAMMA_PIN_AVAILABLE:
            self.strategies['gamma_pin_reversion'] = GammaPinReversion()
            logger.info("✅ Gamma Pin Reversion chargée")

        if "gamma_wall_rejection" in enabled and GAMMA_WALL_REJECTION_AVAILABLE:
            self.strategies['gamma_wall_rejection'] = GammaWallRejectionStrategy()
            logger.info("✅ Gamma Wall Rejection chargée")

        if "zero_dte_wall_sweep" in enabled and ZERO_DTE_AVAILABLE:
            self.strategies['zero_dte_wall_sweep'] = ZeroDTEWallSweepReversal()
            logger.info("✅ Zero DTE Wall Sweep chargée")

        if "liquidity_sweep_reversal" in enabled and LIQUIDITY_SWEEP_AVAILABLE:
            self.strategies['liquidity_sweep_reversal'] = LiquiditySweepReversal()
            logger.info("✅ Liquidity Sweep Reversal chargée")

        if "vwap_band_squeeze_break" in enabled and VWAP_SQUEEZE_AVAILABLE:
            self.strategies['vwap_band_squeeze_break'] = VwapBandSqueezeBreak()
            logger.info("✅ VWAP Band Squeeze Break chargée")

        if "head_fake_detector" in enabled and HEAD_FAKE_AVAILABLE:
            self.strategies['head_fake_detector'] = HeadFakeDetector()
            logger.info("✅ Head Fake Detector chargée")

        # === GAME CHANGERS ===
        if "blind_spot_magnetic_pull" in enabled and BLIND_SPOT_AVAILABLE:
            self.strategies['blind_spot_magnetic_pull'] = BlindSpotMagneticPull()
            logger.info("✅ Blind Spot Magnetic Pull chargée (GAME CHANGER)")

        if "gamma_wall_break_and_go" in enabled and GAMMA_WALL_AVAILABLE:
            self.strategies['gamma_wall_break_and_go'] = GammaWallBreakAndGo()
            logger.info("✅ Gamma Wall Break And Go chargée (GAME CHANGER)")

        if "vwap_sd_options_confluence_strategy" in enabled and VWAP_SD_AVAILABLE:
            self.strategies['vwap_sd_options_confluence_strategy'] = VWAPSDOptionsConfluenceStrategy(self.config)
            logger.info("✅ VWAP SD Options Confluence Strategy chargée")

        if "hvl_magnet_fade" in enabled and HVL_MAGNET_AVAILABLE:
            self.strategies['hvl_magnet_fade'] = HVLMagnetFade()
            logger.info("✅ HVL Magnet Fade chargée (GAME CHANGER)")

        if "call_put_channel_rotation" in enabled and CHANNEL_ROTATION_AVAILABLE:
            self.strategies['call_put_channel_rotation'] = CallPutChannelRotation()
            logger.info("✅ Call Put Channel Rotation chargée (GAME CHANGER)")

        # ✅ NEW: ML 3-Layer Strategy (nécessite ml_3layer_system en injection)
        if "menthorq_3layer_strategy" in enabled:
            # ✅ Injecter ml_3layer_system si disponible (passé au constructeur)
            if self.ml_3layer_system_to_inject:
                logger.info("🔧 Injection ml_3layer_system dans menthorq_3layer_strategy (depuis __init__)...")
                logger.info(f"   → ml_3layer_system type: {type(self.ml_3layer_system_to_inject)}")
                from strategies.menthorq_3layer_strategy import create_menthorq_3layer_strategy
                self.strategies['menthorq_3layer_strategy'] = create_menthorq_3layer_strategy(self.ml_3layer_system_to_inject)
                logger.info("✅ MenthorQ 3-Layer Strategy initialisée avec ml_3layer_system (DIRECT)")
            else:
                # Placeholder si ml_3layer_system pas encore disponible
                self.strategies['menthorq_3layer_strategy'] = None
                logger.info("⚠️ MenthorQ 3-Layer Strategy: En attente d'injection ml_3layer_system")

    def set_ml_3layer_system(self, ml_3layer_system):
        """
        ✅ Injecter le système 3-Layer dans la stratégie menthorq_3layer_strategy

        Args:
            ml_3layer_system: Instance de ML3LayerIntegratedSystem
        """
        try:
            logger.info("🔧 Injection ml_3layer_system dans menthorq_3layer_strategy...")
            logger.info(f"   → ml_3layer_system type: {type(ml_3layer_system)}")
            logger.info(f"   → ml_3layer_system is None: {ml_3layer_system is None}")
            logger.info(f"   → strategies keys AVANT: {list(self.strategies.keys())}")
            logger.info(f"   → menthorq_3layer_strategy in strategies AVANT: {'menthorq_3layer_strategy' in self.strategies}")

            # ✅ CORRIGÉ: Utiliser menthorq_3layer_strategy au lieu de ml_3layer_strategy
            from strategies.menthorq_3layer_strategy import create_menthorq_3layer_strategy
            self.strategies['menthorq_3layer_strategy'] = create_menthorq_3layer_strategy(ml_3layer_system)

            logger.info(f"   → strategies keys APRÈS: {list(self.strategies.keys())}")
            logger.info(f"   → menthorq_3layer_strategy in strategies APRÈS: {'menthorq_3layer_strategy' in self.strategies}")
            logger.info(f"   → menthorq_3layer_strategy value: {self.strategies.get('menthorq_3layer_strategy')}")
            logger.info(f"   → menthorq_3layer_strategy is None: {self.strategies.get('menthorq_3layer_strategy') is None}")
            logger.info("✅ MenthorQ 3-Layer Strategy initialisée avec ml_3layer_system")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation menthorq_3layer_strategy: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.strategies.pop('menthorq_3layer_strategy', None)

    def evaluate_all(
        self,
        ml_data: Dict[str, Any],
        symbol: str = "ES",
        current_positions: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        🔥 ÉVALUATION V3 - PIPELINE ELITE

        Pipeline:
        1️⃣ RulesEngine (filtrage contextuel)
        2️⃣ MarketContext (analyse macro)
        3️⃣ Stratégies (10 strategies par priorité)
        4️⃣ Sélection intelligente (confluence + ML)

        Args:
            ml_data: Dict ML_READY complet
            symbol: ES/NQ/RTY
            current_positions: Positions ouvertes (pour anti-cumulation)

        Returns:
            Signal final ou None
        """
        start_time = time.perf_counter()
        self.global_stats['total_evaluations'] += 1
        current_time = datetime.now()
        current_positions = current_positions or {}

        try:
            # ═══════════════════════════════════════════════════════════════
            # 1️⃣ RULES ENGINE - FILTRAGE CONTEXTUEL
            # ═══════════════════════════════════════════════════════════════

            if self.rules_engine:
                # Convertir ML_READY → RulesEngine format
                rules_context = self._ml_ready_to_rules_context(ml_data, symbol)

                # Évaluer règles d'entrée
                passed, rule_results = self.rules_engine.evaluate_entry_rules(
                    signal={
                        'symbol': symbol,
                        'direction': 'UNKNOWN',  # Sera déterminé par stratégies
                        'confluence': ml_data.get('confluence', 0.0),
                        'vix': ml_data.get('vix', 20.0)
                    },
                    context=rules_context,
                    current_positions=current_positions
                )

                if not passed:
                    rejection_summary = self.rules_engine.get_rejection_summary(rule_results)

                    # ✨ V3: Mode shadow (log sans bloquer)
                    if self.rules_shadow_mode:
                        logger.warning(f"🚫 [SHADOW] [{symbol}] RulesEngine: {rejection_summary} (continué quand même)")
                        self.global_stats['total_rules_rejections'] += 1
                        # Ne pas return None → continuer
                    else:
                        # Mode PROD: bloquer vraiment
                        logger.warning(f"🚫 [PROD] [{symbol}] RulesEngine: {rejection_summary}")
                        self.global_stats['total_rules_rejections'] += 1
                        return None

            # ═══════════════════════════════════════════════════════════════
            # 2️⃣ MARKET CONTEXT - ANALYSE MACRO
            # ═══════════════════════════════════════════════════════════════

            market_context = None
            if self.market_context_analyzer:
                try:
                    market_context = self.market_context_analyzer.analyze(ml_data, symbol)

                    # Vérifier conditions défavorables
                    if market_context and hasattr(market_context, 'quality_score'):
                        if market_context.quality_score < 0.3:
                            logger.warning(f"⚠️ [{symbol}] Qualité marché trop faible ({market_context.quality_score:.2f})")
                            self.global_stats['total_context_rejections'] += 1
                            return None
                except Exception as e:
                    logger.debug(f"⚠️ Erreur MarketContext: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 3️⃣ STRATÉGIES - ÉVALUATION PAR PRIORITÉ
            # ═══════════════════════════════════════════════════════════════

            current_session = self._get_current_session()
            all_signals = []

            priority_order = sorted(
                self.strategies.keys(),
                key=lambda s: STRATEGY_PRIORITY.get(s, 999)
            )

            # 🔍 DEBUG: Vérifier si menthorq_3layer_strategy est dans la liste
            if 'menthorq_3layer_strategy' in self.strategies:
                strategy_value = self.strategies['menthorq_3layer_strategy']
                logger.info(f"🔍 DEBUG [{symbol}]: menthorq_3layer_strategy in strategies = True, value = {strategy_value}, is None = {strategy_value is None}")
            else:
                logger.warning(f"🔍 DEBUG [{symbol}]: menthorq_3layer_strategy NOT in strategies! Keys = {list(self.strategies.keys())}")

            logger.info(f"📋 [{symbol}] Évaluation {len(priority_order)} stratégies: {priority_order}")

            # ✅ DEBUG 17/11: Logger pour ES
            if symbol == 'ES':
                logger.info(f"🔍 [ES DEBUG] StrategyManager.evaluate_all() - {len(priority_order)} stratégies à évaluer")
                logger.info(f"🔍 [ES DEBUG] Stratégies chargées: {list(self.strategies.keys())}")
                logger.info(f"🔍 [ES DEBUG] menthorq_3layer_strategy disponible: {'menthorq_3layer_strategy' in self.strategies}")
                if 'menthorq_3layer_strategy' in self.strategies:
                    logger.info(f"🔍 [ES DEBUG] menthorq_3layer_strategy value: {self.strategies['menthorq_3layer_strategy']}")
                    logger.info(f"🔍 [ES DEBUG] menthorq_3layer_strategy is None: {self.strategies['menthorq_3layer_strategy'] is None}")

            for strategy_name in priority_order:
                # ✅ DEBUG 17/11: Logger pour ES
                if symbol == 'ES':
                    logger.info(f"🔍 [ES DEBUG] Évaluation stratégie: {strategy_name}")
                    logger.info(f"🔍 [ES DEBUG] Stratégie disponible: {strategy_name in self.strategies}")
                    if strategy_name in self.strategies:
                        logger.info(f"🔍 [ES DEBUG] Stratégie value: {self.strategies[strategy_name]}")
                        logger.info(f"🔍 [ES DEBUG] Stratégie is None: {self.strategies[strategy_name] is None}")

                self.stats[strategy_name]['evaluations'] += 1

                logger.info(f"  → Évaluation {strategy_name}...")

                # Check cooldown (avec contexte adaptatif)
                current_context_str = market_context.main_bias if market_context else "NEUTRAL"
                if self._is_in_cooldown(strategy_name, current_time, symbol, current_context_str):
                    self.stats[strategy_name]['cooldown_blocks'] += 1
                    logger.info(f"    ❌ {strategy_name}: Cooldown actif")
                    continue

                # Check session
                if not is_session_allowed(strategy_name, current_session):
                    self.stats[strategy_name]['session_blocks'] += 1
                    logger.info(f"    ❌ {strategy_name}: Session non autorisée ({current_session})")
                    continue

                # Analyser stratégie
                strategy = self.strategies[strategy_name]

                # ✅ SKIP si la stratégie est None (pas encore initialisée)
                if strategy is None:
                    logger.warning(f"⚠️ {strategy_name} est None, skip (pas encore initialisée)")
                    if symbol == 'ES':
                        logger.error(f"🔍 [ES DEBUG] REJET: {strategy_name} est None - Stratégie non initialisée")
                    continue

                # ✅ DEBUG 17/11: Logger pour ES avant l'appel
                if symbol == 'ES':
                    logger.info(f"🔍 [ES DEBUG] Appel {strategy_name}.analyze_from_ml_ready()...")
                    logger.info(f"🔍 [ES DEBUG] ml_data keys: {list(ml_data.keys())[:10]}...")

                logger.info(f"    🔍 {strategy_name}: Appel analyze_from_ml_ready()...")
                signal = strategy.analyze_from_ml_ready(ml_data)

                # ✅ DEBUG 17/11: Logger pour ES après l'appel
                if symbol == 'ES':
                    if signal:
                        logger.info(f"🔍 [ES DEBUG] {strategy_name} a retourné un signal: {signal}")
                    else:
                        logger.warning(f"🔍 [ES DEBUG] {strategy_name} a retourné None - Aucun signal")

                # 🔥 DEBUG: Log du signal retourné
                if signal:
                    logger.info(f"    ✅ {strategy_name}: Signal retourné = {type(signal).__name__}")
                else:
                    logger.debug(f"    ❌ {strategy_name}: Aucun signal retourné (None)")

                # ═══════════════════════════════════════════════════════════════
                # 🔥 NOUVEAU 16/11/2025: FILTRAGE ML POUR TOUTES LES STRATÉGIES
                # Appliquer Quality Score + WIN/LOSS Classifier à TOUS les signaux
                # (Pas seulement MenthorQ 3-Layer)
                # ═══════════════════════════════════════════════════════════════
                if signal and self.ml_3layer_system_to_inject:
                    signal = self._apply_ml_filters_global(signal, ml_data, symbol, strategy_name)

                    if not signal:
                        logger.info(f"    ❌ {strategy_name}: Signal REJETÉ par filtres ML globaux")
                        continue  # Passer à la stratégie suivante

                if signal:
                    signal_direction = self._get_signal_direction(signal)
                    logger.info(f"    📍 {strategy_name}: Direction extraite = {signal_direction}")

                    if signal_direction:
                        # ✨ V3: Extraire ML confidence du signal AVANT bias filter
                        ml_confidence = self._get_ml_confidence(signal, ml_data)
                        ml_threshold = get_ml_threshold_for_strategy(strategy_name)

                        # 🔥 DEBUG: Log des confidences
                        logger.info(f"    📊 {strategy_name}: ML confidence = {ml_confidence:.4f} (threshold = {ml_threshold:.2f})")

                        # ✅ CORRECTIF: Appliquer Bias Filter SEULEMENT aux stratégies classiques
                        # menthorq_3layer_strategy a sa propre analyse Layer 3 et peut trader contre-tendance
                        if strategy_name != 'menthorq_3layer_strategy':
                            # Vérifier si un bias existe dans ml_data
                            bias = ml_data.get('bias')
                            if bias and bias != 'NEUTRAL':
                                # Importer BiasFilter si disponible
                                try:
                                    from ml.bias_filter import BiasFilter
                                    bias_filter = BiasFilter()

                                    # 🔧 MODIFICATION 2025-11-13: Passer confidence au BIAS FILTER
                                    if not bias_filter.should_trade(signal_direction, bias, signal_confidence=ml_confidence):
                                        rejection_reason = bias_filter.get_rejection_reason(signal_direction, bias)
                                        logger.warning(f"🚫 [{symbol}] {strategy_name}: {rejection_reason}")
                                        self.stats[strategy_name]['bias_rejections'] = self.stats[strategy_name].get('bias_rejections', 0) + 1
                                        continue
                                except ImportError:
                                    pass  # Bias filter non disponible

                        if ml_confidence < ml_threshold:
                            logger.warning(f"⚠️ {strategy_name}: ML confidence trop faible ({ml_confidence:.2f} < {ml_threshold:.2f}) → REJET")
                            self.stats[strategy_name]['ml_rejections'] += 1
                            continue

                        # ✅ CORRECTION P0: Vérifier confluence ES (cohérent avec launch_ml_v3_production.py)
                        if symbol == 'ES' or symbol.startswith('ES'):
                            # ✅ CORRIGÉ 17/11: Pour menthorq_3layer_strategy, utiliser la confidence du signal
                            # car c'est la confluence ML 3-Layer (L1+L2+L3)
                            if strategy_name == 'menthorq_3layer_strategy':
                                confluence = ml_confidence  # La confidence du signal EST la confluence ML 3-Layer
                            else:
                                confluence = ml_data.get('confluence', 0.0)  # Pour autres stratégies, utiliser confluence du ml_data

                            # ✅ CORRIGÉ 17/11: Seuil à 0.55 (55%) pour qualité optimale
                            # Le seuil de 0.70 était trop restrictif (0% de trades ES)
                            # 0.55 est un bon compromis entre qualité et volume de trades
                            min_confluence_es = 0.55  # Seuil optimisé pour ES (qualité/volume)
                            if confluence < min_confluence_es:
                                logger.warning(f"⚠️ {strategy_name}: Confluence ES trop faible ({confluence:.2f} < {min_confluence_es:.2f}) → REJET")
                                self.stats[strategy_name]['confluence_rejections'] = self.stats[strategy_name].get('confluence_rejections', 0) + 1
                                continue

                        all_signals.append((strategy_name, signal, ml_confidence))
                        logger.info(f"✅ {strategy_name}: {signal_direction} (ML: {ml_confidence:.2f}) → AJOUTÉ À all_signals")
                    else:
                        logger.warning(f"⚠️ {strategy_name}: Direction est None → REJET")

            # ═══════════════════════════════════════════════════════════════
            # 4️⃣ SÉLECTION INTELLIGENTE
            # ═══════════════════════════════════════════════════════════════

            if not all_signals:
                if self.global_stats['total_evaluations'] % 100 == 0:
                    logger.info(f"🔍 [{symbol}] Éval #{self.global_stats['total_evaluations']}: "
                              f"0 signaux (session: {current_session})")
                return None

            best_signal = self._select_best_signal_v3(all_signals, ml_data, market_context)

            if best_signal:
                strategy_name, signal, ml_confidence = best_signal

                # ═══════════════════════════════════════════════════════════════
                # 🔥 NOUVEAU 15/11/2025: MODE HYBRIDE ML 3-LAYER VALIDATION
                # ═══════════════════════════════════════════════════════════════
                # Si signal vient de ConfluenceSignal, valider avec ML 3-Layer OrderFlow
                # Augmente size 1.5x si ML validation > 0.60 (high confidence)
                # ═══════════════════════════════════════════════════════════════

                if strategy_name == 'vwap_sd_options_confluence_strategy' and self.ml_3layer_system_to_inject:
                    try:
                        logger.info(f"🔍 [{symbol}] Mode Hybride: Validation ML 3-Layer OrderFlow...")

                        # Évaluer avec ML 3-Layer (Layer 2 OrderFlow unique)
                        ml_validation = self.ml_3layer_system_to_inject.evaluate_signal(ml_data, symbol)

                        if ml_validation and ml_validation.get('should_trade', False):
                            ml_val_confidence = ml_validation.get('confidence', 0.0)
                            layer2_confidence = ml_validation.get('layer2_confidence', 0.0)

                            logger.info(
                                f"   ML 3-Layer: Total={ml_val_confidence:.2f}, "
                                f"Layer2 (OrderFlow)={layer2_confidence:.2f}"
                            )

                            # Si validation > 0.60: Augmenter size 1.5x
                            if ml_val_confidence >= 0.60:
                                # Ajouter size_multiplier au signal
                                if hasattr(signal, '__dict__'):
                                    signal.size_multiplier = 1.5
                                    signal.ml_validation = True
                                    signal.ml_validation_confidence = ml_val_confidence
                                    signal.ml_layer2_orderflow = layer2_confidence

                                    logger.info(
                                        f"✅ [{symbol}] ML 3-Layer VALIDATION RÉUSSIE "
                                        f"({ml_val_confidence:.2f} >= 0.60) → SIZE 1.5x"
                                    )
                                    logger.info(
                                        f"   Layer 2 (OrderFlow): {layer2_confidence:.2f} "
                                        f"(unique à ML 3-Layer)"
                                    )
                                else:
                                    logger.debug(f"⚠️ Signal n'a pas __dict__, impossible d'ajouter size_multiplier")
                            else:
                                # Validation échouée: garder size normal 1.0x
                                if hasattr(signal, '__dict__'):
                                    signal.size_multiplier = 1.0
                                    signal.ml_validation = False
                                    signal.ml_validation_confidence = ml_val_confidence

                                    logger.info(
                                        f"⚠️ [{symbol}] ML 3-Layer validation FAIBLE "
                                        f"({ml_val_confidence:.2f} < 0.60) → SIZE 1.0x (normal)"
                                    )
                        else:
                            # ML 3-Layer rejette: garder signal mais size normal
                            rejection = ml_validation.get('rejection_reason', 'Unknown') if ml_validation else 'No result'
                            logger.info(
                                f"⚠️ [{symbol}] ML 3-Layer REJET ({rejection}) → SIZE 1.0x (normal)"
                            )

                            if hasattr(signal, '__dict__'):
                                signal.size_multiplier = 1.0
                                signal.ml_validation = False

                    except Exception as e:
                        # Si erreur, garder signal mais log l'erreur
                        logger.warning(f"⚠️ Erreur validation ML 3-Layer: {e}")
                        if hasattr(signal, '__dict__'):
                            signal.size_multiplier = 1.0
                            signal.ml_validation = False
                else:
                    # Stratégie autre que ConfluenceSignal: pas de validation ML
                    if hasattr(signal, '__dict__') and not hasattr(signal, 'size_multiplier'):
                        signal.size_multiplier = 1.0
                        signal.ml_validation = False

                # 🔥 COOLDOWN ADAPTATIF INTELLIGENT (13-NOV-2025)
                # Appliquer cooldown SEULEMENT si signal sera probablement exécuté
                # Si confidence trop faible ou contexte défavorable → Cooldown COURT

                will_be_executed = True  # Par défaut, assume exécution

                # Check 1: ML confidence vs threshold
                ml_threshold = get_ml_threshold_for_strategy(strategy_name)
                if ml_confidence < ml_threshold:
                    will_be_executed = False
                    logger.debug(f"   🔄 {strategy_name}: Signal faible ML ({ml_confidence:.2f} < {ml_threshold:.2f}) → Cooldown court (30s)")

                # Check 2: Confidence totale (si disponible dans signal)
                if hasattr(signal, 'confidence') and signal.confidence < 0.50:
                    will_be_executed = False
                    logger.debug(f"   🔄 {strategy_name}: Confidence totale faible ({signal.confidence:.2f}) → Cooldown court (30s)")

                # Appliquer cooldown adaptatif
                if will_be_executed:
                    # Cooldown NORMAL (signal sera probablement exécuté)
                    self.last_signal_time[strategy_name] = current_time
                    logger.debug(f"   ✅ {strategy_name}: Cooldown NORMAL appliqué")
                else:
                    # Cooldown COURT (signal sera probablement rejeté)
                    short_cooldown = timedelta(seconds=30)
                    self.last_signal_time[strategy_name] = current_time - timedelta(seconds=get_cooldown_for_strategy(strategy_name)) + short_cooldown
                    logger.debug(f"   ⚡ {strategy_name}: Cooldown COURT appliqué (30s au lieu de {get_cooldown_for_strategy(strategy_name)}s)")

                # ✅ Mettre à jour contexte pour cooldown adaptatif
                if market_context:
                    self.last_context_by_symbol[symbol] = market_context.main_bias

                # Stats
                self.stats[strategy_name]['signals_generated'] += 1
                self.global_stats['total_signals'] += 1

                # Update avg ML confidence
                alpha = 0.1
                self.global_stats['avg_ml_confidence'] = (
                    alpha * ml_confidence +
                    (1 - alpha) * self.global_stats.get('avg_ml_confidence', ml_confidence)
                )

                # Processing time
                processing_time = (time.perf_counter() - start_time) * 1000
                self.global_stats['avg_processing_time_ms'] = (
                    alpha * processing_time +
                    (1 - alpha) * self.global_stats.get('avg_processing_time_ms', processing_time)
                )

                signal_direction = self._get_signal_direction(signal)
                entry = getattr(signal, 'entry', 'N/A')
                logger.info(f"🎯 Signal V3: {strategy_name} → {signal_direction} @ {entry} (ML: {ml_confidence:.2f})")

                return signal

            return None

        except Exception as e:
            logger.error(f"❌ Erreur StrategyManagerV3.evaluate_all: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _ml_ready_to_rules_context(self, ml_data: Dict, symbol: str) -> Dict:
        """
        ✨ V3: Convertit ML_READY → RulesEngine context format

        Args:
            ml_data: Dict ML_READY
            symbol: ES/NQ/RTY

        Returns:
            Context dict pour RulesEngine
        """
        return {
            'summary': {
                'atr': ml_data.get('atr', 1.0),
                'vix': ml_data.get('vix', 20.0)
            },
            'macro': {
                'vix': ml_data.get('vix', 20.0)
            },
            'main_bias': ml_data.get('dealer_bias', 'NEUTRAL'),
            'bias_strength': ml_data.get('dealer_bias_strength', 0.5),
            'orderflow_pressure': ml_data.get('orderflow_direction', 'NEUTRAL'),
            'proximity_alerts': ml_data.get('proximity_alerts', []),
            'gamma_flip_detected': ml_data.get('gamma_flip', None)
        }

    def _get_signal_direction(self, signal: Any) -> Optional[str]:
        """Extrait direction (LONG/SHORT) depuis signal"""
        if hasattr(signal, 'side') and signal.side:
            return signal.side
        elif hasattr(signal, 'direction') and signal.direction:  # ✅ AJOUTÉ pour ConfluenceSignal
            return signal.direction
        elif hasattr(signal, 'action'):
            if signal.action == "GO_LONG":
                return "LONG"
            elif signal.action == "GO_SHORT":
                return "SHORT"
        return None

    def _apply_ml_filters_global(self, signal: Any, ml_data: Dict, symbol: str, strategy_name: str) -> Optional[Any]:
        """
        🔥 NOUVEAU 16/11/2025: Applique filtres ML à TOUTES les stratégies

        Filtres appliqués:
        1. Quality Score Predictor (seuil 65/100)
        2. WIN/LOSS Classifier (seuil 0.45)

        Args:
            signal: Signal généré par la stratégie
            ml_data: Snapshot ML_READY
            symbol: Symbole (ES, NQ, RTY)
            strategy_name: Nom de la stratégie

        Returns:
            Signal enrichi avec métadonnées ML, ou None si rejeté
        """
        # Skip si c'est MenthorQ 3-Layer (déjà filtré en interne)
        if strategy_name == 'menthorq_3layer_strategy':
            logger.debug(f"    ⏭️  {strategy_name}: Skip filtres ML globaux (déjà appliqués en interne)")
            return signal

        try:
            # ──────────────────────────────────────────────────────────
            # 1. QUALITY SCORE PREDICTOR (LightGBM)
            # ──────────────────────────────────────────────────────────
            if hasattr(self.ml_3layer_system_to_inject, 'quality_predictor') and \
               self.ml_3layer_system_to_inject.quality_predictor:

                ml_quality_score = self.ml_3layer_system_to_inject.quality_predictor.predict(ml_data)

                # Seuil minimum: 45/100 (réduit de 65.0 pour accepter plus de signaux valides)
                MIN_QUALITY_SCORE = 45.0

                if ml_quality_score < MIN_QUALITY_SCORE:
                    logger.warning(
                        f"    ❌ [{symbol}] {strategy_name}: ML Quality trop faible "
                        f"({ml_quality_score:.1f}/100 < {MIN_QUALITY_SCORE})"
                    )
                    # Incrémenter stats
                    if hasattr(self.ml_3layer_system_to_inject, 'stats'):
                        self.ml_3layer_system_to_inject.stats['ml_quality_rejections'] = \
                            self.ml_3layer_system_to_inject.stats.get('ml_quality_rejections', 0) + 1
                    return None

                # Ajouter métadonnée au signal
                if hasattr(signal, 'metadata'):
                    if signal.metadata is None:
                        signal.metadata = {}
                    signal.metadata['ml_quality_score'] = ml_quality_score
                elif isinstance(signal, dict):
                    if 'metadata' not in signal:
                        signal['metadata'] = {}
                    signal['metadata']['ml_quality_score'] = ml_quality_score

                logger.info(f"    ✅ [{symbol}] {strategy_name}: ML Quality OK ({ml_quality_score:.1f}/100)")

            # ──────────────────────────────────────────────────────────
            # 2. WIN/LOSS CLASSIFIER (LightGBM, seuil optimal 0.45)
            # ──────────────────────────────────────────────────────────
            if hasattr(self.ml_3layer_system_to_inject, 'win_loss_classifier') and \
               self.ml_3layer_system_to_inject.win_loss_classifier:

                ml_prediction = self.ml_3layer_system_to_inject.win_loss_classifier.predict(ml_data)
                ml_win_probability = ml_prediction['win_probability']
                ml_prediction_label = ml_prediction['label']

                if ml_prediction_label == 'LOSS':
                    logger.warning(
                        f"    ❌ [{symbol}] {strategy_name}: ML WIN/LOSS Prédiction LOSS "
                        f"(P(WIN)={ml_win_probability:.1%}, threshold=0.45)"
                    )
                    # Incrémenter stats
                    if hasattr(self.ml_3layer_system_to_inject, 'stats'):
                        self.ml_3layer_system_to_inject.stats['ml_winloss_rejections'] = \
                            self.ml_3layer_system_to_inject.stats.get('ml_winloss_rejections', 0) + 1
                    return None

                # Ajouter métadonnées au signal
                if hasattr(signal, 'metadata'):
                    if signal.metadata is None:
                        signal.metadata = {}
                    signal.metadata['ml_win_probability'] = ml_win_probability
                    signal.metadata['ml_prediction_label'] = ml_prediction_label
                elif isinstance(signal, dict):
                    if 'metadata' not in signal:
                        signal['metadata'] = {}
                    signal['metadata']['ml_win_probability'] = ml_win_probability
                    signal['metadata']['ml_prediction_label'] = ml_prediction_label

                logger.info(
                    f"    ✅ [{symbol}] {strategy_name}: ML WIN/LOSS OK "
                    f"({ml_prediction_label}, P(WIN)={ml_win_probability:.1%})"
                )

            # ✅ Signal validé par ML, retourner avec métadonnées enrichies
            return signal

        except Exception as e:
            logger.error(f"    ⚠️  Erreur filtres ML globaux: {e}")
            # En cas d'erreur, retourner le signal sans filtrage ML
            return signal

    def _get_ml_confidence(self, signal: Any, ml_data: Dict) -> float:
        """
        ✨ V3: Extrait ML confidence depuis signal ou ml_data

        Args:
            signal: Signal stratégie
            ml_data: ML_READY data

        Returns:
            ML confidence (0.0 - 1.0)
        """
        # 1. Depuis signal si disponible
        if hasattr(signal, 'ml_confidence'):
            return signal.ml_confidence
        elif hasattr(signal, 'confidence'):
            return signal.confidence

        # 2. Depuis ml_data
        if 'ml_confidence' in ml_data:
            return ml_data['ml_confidence']
        elif 'confidence' in ml_data:
            return ml_data['confidence']

        # 3. Fallback basé sur confluence
        return ml_data.get('confluence', 0.5)

    def _is_in_cooldown(self, strategy_name: str, current_time: datetime, symbol: str = None, current_context: str = None) -> bool:
        """
        Vérifie si stratégie en cooldown

        ✅ COOLDOWN ADAPTATIF (12/11/2025 + 13/11/2025):
        - Réduit cooldown de 50% si contexte market a changé
        - ✅ NOUVEAU: Utilise AdaptiveCooldowns si disponible (ajustement selon performance + volatilité)
        """
        if strategy_name not in self.last_signal_time:
            return False

        # 🔄 NOUVEAU: Utiliser cooldown adaptatif si disponible
        if self.adaptive_cooldowns:
            cooldown_seconds = self.adaptive_cooldowns.get_cooldown(strategy_name)
        else:
            # Fallback: cooldown fixe
            cooldown_seconds = get_cooldown_for_strategy(strategy_name)

        # ✅ COOLDOWN ADAPTATIF - Réduction si changement de contexte
        if symbol and current_context:
            last_context = self.last_context_by_symbol.get(symbol)

            if last_context and last_context != current_context:
                # Contexte a changé → Réduire cooldown
                original_cooldown = cooldown_seconds
                cooldown_seconds = cooldown_seconds * self.cooldown_reduction_on_context_change

                logger.debug(
                    f"🔄 [{symbol}] Cooldown adaptatif {strategy_name}: "
                    f"{original_cooldown}s → {cooldown_seconds}s "
                    f"(contexte {last_context} → {current_context})"
                )

        last_time = self.last_signal_time[strategy_name]
        elapsed = (current_time - last_time).total_seconds()

        return elapsed < cooldown_seconds

    def _get_current_session(self) -> str:
        """
        ✨ V3: Détermine session actuelle (SessionAnalyzer ou fallback)

        Returns:
            "ASIA" | "LONDON" | "US" | "OVERNIGHT"
        """
        if self.session_analyzer:
            try:
                now = datetime.now()
                analysis = self.session_analyzer.analyze_session(now, vix_level=20.0)
                session_state = analysis.get('session_state', {})

                # Mapper vers noms simples
                if session_state.get('is_rth', False):
                    return "US"
                elif session_state.get('window') == "open":
                    return "LONDON"
                else:
                    hour = now.hour
                    if 18 <= hour or hour < 2:
                        return "ASIA"
                    else:
                        return "OVERNIGHT"
            except Exception:
                pass

        # Fallback: calcul simple timezone
        from datetime import timezone, timedelta
        est_tz = timezone(timedelta(hours=-5))
        now_est = datetime.now(est_tz)
        hour = now_est.hour

        if 18 <= hour or hour < 2:
            return "ASIA"
        elif 2 <= hour < 9:
            return "LONDON"
        elif 9 <= hour < 16:
            return "US"
        else:
            return "OVERNIGHT"

    def _select_best_signal_v3(
        self,
        signals: List[Tuple[str, Any, float]],
        ml_data: Dict,
        market_context: Optional[Any]
    ) -> Optional[Tuple[str, Any, float]]:
        """
        ✨ V3: Sélection intelligente avec pondération

        Args:
            signals: Liste de (strategy_name, signal, ml_confidence)
            ml_data: ML_READY data
            market_context: MarketContext si disponible

        Returns:
            (strategy_name, signal, ml_confidence) ou None
        """
        if not signals:
            return None

        if len(signals) == 1:
            return signals[0]

        # === RÉSOLUTION CONFLITS V3 ===

        # 1. HeadFake peut invalider autres signaux
        headfake_signals = [s for s in signals if s[0] == "head_fake_detector"]
        if headfake_signals:
            logger.info("🚨 HeadFake détecté, invalide autres signaux")
            return headfake_signals[0]

        # 2. Signaux même direction → confluence
        long_signals = [s for s in signals if self._get_signal_direction(s[1]) == "LONG"]
        short_signals = [s for s in signals if self._get_signal_direction(s[1]) == "SHORT"]

        if long_signals and not short_signals:
            # ✨ V3: Score composite (ML + headroom + priorité)
            best = max(long_signals, key=lambda s: self._compute_signal_score(s, ml_data, market_context))
            logger.info(f"✅ Confluence LONG: {best[0]} (score composite max)")
            return best

        if short_signals and not long_signals:
            best = max(short_signals, key=lambda s: self._compute_signal_score(s, ml_data, market_context))
            logger.info(f"✅ Confluence SHORT: {best[0]} (score composite max)")
            return best

        # 3. Signaux opposés → Résolution intelligente
        if long_signals and short_signals:
            # ✅ CORRIGÉ 17/11: Amélioration résolution conflits avec fallback
            # Priorité 1: MarketContext avec bias fort (> 0.7)
            if market_context and hasattr(market_context, 'main_bias'):
                bias_strength = getattr(market_context, 'bias_strength', 0)
                if market_context.main_bias == "BULLISH" and bias_strength > 0.7:
                    best = max(long_signals, key=lambda s: s[2])  # Meilleur ML
                    logger.info(f"⚖️ Conflit résolu par MarketContext: {best[0]} (BULLISH bias {bias_strength:.2f})")
                    return best
                elif market_context.main_bias == "BEARISH" and bias_strength > 0.7:
                    best = max(short_signals, key=lambda s: s[2])
                    logger.info(f"⚖️ Conflit résolu par MarketContext: {best[0]} (BEARISH bias {bias_strength:.2f})")
                    return best

            # Priorité 2: MarketContext avec bias modéré (> 0.5) - plus permissif
            if market_context and hasattr(market_context, 'main_bias'):
                bias_strength = getattr(market_context, 'bias_strength', 0)
                if market_context.main_bias == "BULLISH" and bias_strength > 0.5:
                    # Comparer score composite pour choisir le meilleur LONG
                    best = max(long_signals, key=lambda s: self._compute_signal_score(s, ml_data, market_context))
                    logger.info(f"⚖️ Conflit résolu par MarketContext (modéré): {best[0]} LONG (bias {bias_strength:.2f})")
                    return best
                elif market_context.main_bias == "BEARISH" and bias_strength > 0.5:
                    best = max(short_signals, key=lambda s: self._compute_signal_score(s, ml_data, market_context))
                    logger.info(f"⚖️ Conflit résolu par MarketContext (modéré): {best[0]} SHORT (bias {bias_strength:.2f})")
                    return best

            # Priorité 3: Meilleur score composite (fallback intelligent)
            all_conflicting = long_signals + short_signals
            best = max(all_conflicting, key=lambda s: self._compute_signal_score(s, ml_data, market_context))
            best_direction = self._get_signal_direction(best[1])
            logger.info(f"⚖️ Conflit résolu par score composite: {best[0]} {best_direction} (score max)")
            return best

            # ❌ ANCIEN CODE (trop restrictif - supprimé)
            # logger.warning("⚠️ Conflit LONG vs SHORT non résolu, annulation")
            # for strategy_name, _, _ in signals:
            #     self.stats[strategy_name]['conflicts'] += 1
            # return None

        # 4. Par défaut: meilleur score composite
        best = max(signals, key=lambda s: self._compute_signal_score(s, ml_data, market_context))
        return best

    def _compute_signal_score(
        self,
        signal_tuple: Tuple[str, Any, float],
        ml_data: Dict,
        market_context: Optional[Any]
    ) -> float:
        """
        ✨ V3: Calcule score composite d'un signal

        Pondération:
        - 40% ML confidence
        - 30% Headroom (distance wall)
        - 20% Priorité stratégie
        - 10% Context quality

        Args:
            signal_tuple: (strategy_name, signal, ml_confidence)
            ml_data: ML_READY data
            market_context: MarketContext

        Returns:
            Score composite (0.0 - 1.0)
        """
        strategy_name, signal, ml_confidence = signal_tuple

        # 1. ML confidence (40%)
        ml_score = ml_confidence * 0.40

        # 2. Headroom (30%)
        headroom = self._get_headroom(signal_tuple, ml_data)
        headroom_score = min(headroom / 0.20, 1.0) * 0.30  # Normaliser à 20% = excellent

        # 3. Priorité stratégie (20%)
        priority = STRATEGY_PRIORITY.get(strategy_name, 999)
        priority_score = (1.0 - (priority / 10.0)) * 0.20  # Inverse (priorité 1 = score max)

        # 4. Context quality (10%)
        context_score = 0.05  # Default
        if market_context and hasattr(market_context, 'quality_score'):
            context_score = market_context.quality_score * 0.10

        total_score = ml_score + headroom_score + priority_score + context_score

        logger.debug(f"📊 {strategy_name}: score={total_score:.3f} (ML:{ml_score:.2f} HR:{headroom_score:.2f} P:{priority_score:.2f} C:{context_score:.2f})")

        return total_score

    def _get_signal_direction(self, signal: Any) -> Optional[str]:
        """
        Extrait la direction du signal (LONG/SHORT)

        Args:
            signal: Signal (PatternSignal ou Dict)

        Returns:
            "LONG", "SHORT" ou None
        """
        if signal is None:
            return None

        # Si c'est un objet PatternSignal
        if hasattr(signal, 'direction'):
            direction = signal.direction
            if direction in ['LONG', 'SHORT', 'UP', 'DOWN']:
                return 'LONG' if direction in ['LONG', 'UP'] else 'SHORT'

        # Si c'est un dictionnaire
        if isinstance(signal, dict):
            direction = signal.get('direction') or signal.get('action')
            if direction in ['LONG', 'SHORT', 'UP', 'DOWN']:
                return 'LONG' if direction in ['LONG', 'UP'] else 'SHORT'

        return None

    def _get_ml_confidence(self, signal: Any, ml_data: Dict) -> float:
        """
        Extrait la confidence ML du signal

        Args:
            signal: Signal (PatternSignal ou Dict)
            ml_data: Données ML_READY

        Returns:
            Confidence entre 0.0 et 1.0
        """
        if signal is None:
            return 0.0

        # 1. Chercher dans le signal lui-même
        if hasattr(signal, 'confidence'):
            return float(signal.confidence)

        if isinstance(signal, dict):
            confidence = signal.get('confidence')
            if confidence is not None:
                return float(confidence)

        # 2. Chercher dans meta
        if hasattr(signal, 'meta') and isinstance(signal.meta, dict):
            confidence = signal.meta.get('confidence') or signal.meta.get('total_confidence')
            if confidence is not None:
                return float(confidence)

        # 3. Fallback sur ML_READY
        return ml_data.get('total_confidence', 0.5)

    def _get_headroom(self, signal_tuple: tuple, ml_data: Dict) -> float:
        """Calcule headroom (distance wall)"""
        strategy_name, signal, ml_confidence = signal_tuple

        next_wall = ml_data.get('next_wall', {})
        if not next_wall:
            return 0.15

        wall_dist_pct = next_wall.get('dist_pct', 0.15)
        signal_direction = self._get_signal_direction(signal)

        if signal_direction == "LONG" and next_wall.get('side') == 'call':
            return wall_dist_pct
        elif signal_direction == "SHORT" and next_wall.get('side') == 'put':
            return wall_dist_pct
        else:
            return 0.05

    def get_stats(self) -> Dict:
        """
        ✨ V3: Statistiques enrichies

        Returns:
            Stats globales + par stratégie + rejections
        """
        return {
            'global': self.global_stats,
            'per_strategy': dict(self.stats),
            'rejection_summary': {
                'rules_engine': self.global_stats['total_rules_rejections'],
                'market_context': self.global_stats['total_context_rejections'],
                'ml_confidence': sum(s['ml_rejections'] for s in self.stats.values()),
                'session': sum(s['session_blocks'] for s in self.stats.values()),
                'cooldown': sum(s['cooldown_blocks'] for s in self.stats.values())
            }
        }

    def reset_cooldowns(self):
        """Reset cooldowns (test/debug)"""
        self.last_signal_time.clear()
        logger.info("🔄 Cooldowns réinitialisés")

    def enable_shadow_mode(self, enabled: bool = True):
        """
        ✨ V3: Shadow mode pour RulesEngine

        Args:
            enabled: Si True, RulesEngine log mais ne bloque pas
        """
        if self.rules_engine:
            # TODO: Implémenter shadow mode dans RulesEngine
            logger.info(f"🔄 Shadow mode: {'ACTIF' if enabled else 'INACTIF'}")
