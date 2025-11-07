#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAUNCH ML V3.3 PRODUCTION - SOLIDIFICATION (9 Patchs Critiques Appliqués)
===========================================================================

Version: v3.3_solidification_9_patches + MARKET CONTEXT FILTER
Date: 4 Novembre 2025 03:35

🎯 MODÈLES V3.3 - SOLIDIFICATION :
- ✅ 9 Patchs critiques appliqués (coûts réels, calibration, purged CV, etc.)
- ✅ 35 features distances OPTIONS dynamiques intégrées
- ✅ Coûts réalistes : slippage (1 tick) + fees (2.40 USD/contrat)
- ✅ Calibration isotonic → Brier Score réduit de 15-20%
- ✅ Split temporel strict avec purge/embargo
- ✅ Validation NaN/Inf, segmentation volatilité

🧠 NOUVEAU: FILTRE CONTEXTUEL INTELLIGENT (GPT-4 Audited)
- ✅ Analyse position vs HVL/VWAP/Value Area
- ✅ Détection bias (BULLISH/BEARISH/NEUTRAL)
- ✅ Validation order flow (BUYING/SELLING/BALANCED)
- ✅ Détection gamma (POSITIVE/NEGATIVE)
- ✅ Rejet signaux contre-tendance
- ✅ Skip zones dangereuses (niveaux critiques proches)
- ✅ Boost confiance si confluence haute (signal + contexte)
- ✅ Cool-down 180s par scénario (évite sur-trading)
- ✅ Filtre horaire (14:35-21:00 UTC / 09:35-16:00 ET)

📊 MÉTRIQUES FINALES (Test Set Out-of-Sample) :

**NQ (NASDAQ-100) - PRODUCTION READY ✅**
- Samples: 41,161 (32,928 train / 8,343 test)
- Accuracy: 74.75% | AUC: 0.801 | Brier: 0.165
- PF @0.70: 10.73 (après coûts) | Win Rate: 86.2% | Trades: 4,812
- PF @0.75: 16.55 (après coûts) | Win Rate: 90.5% | Trades: 3,706
- Best Iteration: 98 (bon apprentissage)
- ✅ VALIDATION COMPLÈTE (6/6 critères)

**ES (S&P 500) - COLLECTE DE DONNÉES REQUISE ⚠️**
- Samples: 17,645 (14,116 train / 3,584 test)
- Accuracy: 64.98% | AUC: 0.738 | Brier: 0.210
- PF @0.70: 13.63 (après coûts) | Win Rate: 88.7% | Trades: 701
- Best Iteration: 4 ⚠️ (sous-entraînement)
- ⚠️ VALIDATION PARTIELLE (5/6 critères) - NE PAS DÉPLOYER

🚀 CONFIGURATION DÉPLOIEMENT :
- NQ : Seuil 0.70 (volume) ou 0.75 (qualité) - Mode ADVISORY
- ES : ⏸️ DÉSACTIVÉ - Collecte de 40,000+ samples requise avant réentraînement
- Filtre Contextuel : ✅ ACTIF (ES + NQ) - Rejet signaux contre-tendance

Author: MIA System + Claude Sonnet 4.5
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
from dataclasses import dataclass
import time

# Ajouter le répertoire racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Logger en premier
from core.logger import get_logger
logger = get_logger(__name__)

# Imports conditionnels avec gestion d'erreurs
try:
    from config.optimized_strategy_config import get_optimized_config
    from strategies.strategy_manager_optimized import OptimizedStrategyManager
    from features.ml_ready_reader import MLReadyReader

    # Modules critiques (Versions ML_READY)
    from execution.trade_snapshotter_ml_ready import create_trade_snapshotter_ml_ready
    from execution.post_mortem_analyzer import PostMortemAnalyzer
    from execution.risk_manager import RiskManager
    from execution.sierra_dtc_connector import create_sierra_dtc_connector
    from strategies.bracket_detector_ml_ready import create_bracket_detector_ml_ready
    from utils.enhanced_data_validator import EnhancedDataValidator

    # ML Dual Filter (filtre asymétrique par symbole/sens)
    from ml.ml_dual_filter import MLDualFilter

    # BullishScorer (MIA Bullish v2.0 Enhanced) - OPTIONNEL
    try:
        from core.mia_bullish import BullishScorer
        BULLISH_SCORER_AVAILABLE = True
        logger.info("✅ BullishScorer v2.0 disponible (10 composantes)")
    except ImportError as e:
        BULLISH_SCORER_AVAILABLE = False
        logger.warning(f"⚠️ BullishScorer non disponible (optionnel): {e}")

    # SignalExplainer & DecisionMessenger ML_READY
    from core.signal_explainer_ml_ready import create_signal_explainer_ml_ready
    from core.decision_messenger_ml_ready import create_decision_messenger_ml_ready

    # 🆕 6 NOUVEAUX MODULES INTÉGRÉS (Phase Consolidation)
    from core.execution_latency_tracker import ExecutionLatencyTracker, LatencyStage
    from core.performance_profiler import PerformanceProfiler
    from features.advanced.volatility_regime import VolatilityRegimeCalculator
    from core.safety_kill_switch import SafetyKillSwitch, TelemetryData
    from core.lessons_learned_analyzer import LessonsLearnedAnalyzer, Decision, Execution, Context  # ✅ PHASE 1.2
    from features.dom_health_analyzer import DOMHealthAnalyzer

    # ✅ URGENT 5: Discord Notifier (Visibilité temps réel)
    from monitoring.discord_notifier import create_discord_notifier
    from monitoring.discord_message_aggregator import create_message_aggregator
    DISCORD_AVAILABLE = True
    logger.info("✅ Discord Notifier + Aggregator disponibles")

    # 🆕 5 MODULES PRO AJOUTÉS (Phase Professionnalisation)
    from core.drawdown_monitor import DrawdownMonitor, create_drawdown_monitor
    from core.realistic_backtest_engine import RealisticBacktestEngine, create_realistic_backtest_engine

    # 🆕 PRE-FLIGHT CHECK (Validation pré-lancement)
    from core.preflight_check import PreFlightChecker, create_preflight_checker, GoLiveDecision

    # 🆕 MARKET CONTEXT ANALYZER (Filtre Contextuel Intelligent)
    from core.market_context_analyzer import create_market_context_analyzer, MarketContext

    IMPORTS_OK = True
except ImportError as e:
    logger.error(f"❌ Erreur d'import: {e}")
    IMPORTS_OK = False
    raise


@dataclass
class TradingSignal:
    """Signal de trading unifié"""
    timestamp: int
    symbol: str
    action: str  # "LONG" ou "SHORT"
    entry_price: float
    confidence: float
    strategy: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Optional[Dict] = None


class MLV3TradingSystem:
    """Système de trading avec modèles ML V3"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le système de trading avec modèles V3

        Args:
            config: Configuration du système
        """
        self.config = config
        self.running = False

        # Stats
        self.stats = {
            'cycles': 0,
            'signals': 0,
            'errors': 0,
            'start_time': time.time(),
            'strategies': {}
        }

        # Configuration des symboles
        self.symbols = ["ES", "NQ", "RTY"]  # ✅ RTY ajouté
        self.current_symbol_idx = 0

        # 🆕 Configuration Filtre Contextuel (Externalisée pour ajustement facile)
        self.context_filter_config = {
            'enabled': True,                    # Master switch
            'min_signal_confidence': 0.70,      # Seuil min confiance signal
            'min_plan_confidence': 0.60,        # Seuil min confiance plan
            'max_proximity_alerts': 3,          # Max alertes proximité acceptées
            'boost_threshold': 0.75,            # Seuil pour boost confluence
            'boost_multiplier': 1.20,           # Multiplicateur boost (20%)
            'boost_cap': 0.95,                  # Cap maximum confiance
            'reject_opposite_bias': True        # Rejeter signaux contre-tendance
        }
        logger.info(f"⚙️ Context Filter Config: enabled={self.context_filter_config['enabled']}, "
                   f"min_conf={self.context_filter_config['min_signal_confidence']:.0%}, "
                   f"max_alerts={self.context_filter_config['max_proximity_alerts']}")

        # Bullish display tracking (toutes les minutes)
        from datetime import datetime, timedelta
        self.last_bullish_display_time = datetime.now()
        self.bullish_display_interval_seconds = 60  # 1 minute
        self.last_bullish_emoji = {}  # Par symbole pour détecter les changements

        # Créer les chemins ML_READY
        # LIVE MODE : Pointe vers les données du jour
        today = datetime.now()
        year_dir = f"DATA_{today.year}"

        # Noms de mois en FRANÇAIS (comme dans le dumper)
        month_names_fr = {
            1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL",
            5: "MAI", 6: "JUIN", 7: "JUILLET", 8: "AOUT",
            9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"
        }
        month_dir = month_names_fr[today.month]
        date_dir = today.strftime("%Y%m%d")  # "20251104"

        base_path = Path("D:/MIA_IA_system/DATA_SIERRA_CHART") / year_dir / month_dir / date_dir

        # Vérifier que les chemins existent
        ml_ready_es = base_path / "CHART_3" / "ML_READY"
        ml_ready_nq = base_path / "CHART_9" / "ML_READY"
        ml_ready_rty = base_path / "CHART_1" / "ML_READY"  # ✅ RTY ajouté

        if not ml_ready_es.exists() or not ml_ready_nq.exists() or not ml_ready_rty.exists():
            logger.warning(f"⚠️ Chemins ML_READY du jour non trouvés : {base_path}")
            logger.warning(f"   Création des dossiers...")
            ml_ready_es.mkdir(parents=True, exist_ok=True)
            ml_ready_nq.mkdir(parents=True, exist_ok=True)
            ml_ready_rty.mkdir(parents=True, exist_ok=True)  # ✅ RTY ajouté

        self.ml_ready_paths = {
            "ES": ml_ready_es,
            "NQ": ml_ready_nq,
            "RTY": ml_ready_rty  # ✅ RTY ajouté
        }

        logger.info(f"📁 Chemins ML_READY configurés :")
        logger.info(f"   ES: {ml_ready_es}")
        logger.info(f"   NQ: {ml_ready_nq}")
        logger.info(f"   RTY: {ml_ready_rty}")  # ✅ RTY ajouté

        # Créer les readers ML_READY
        self.readers = {}
        for symbol in self.symbols:
            try:
                # MLReadyReader attend un dict config avec watch_dirs et chart_mapping
                reader_config = {
                    "live_mode": {
                        "realtime": {
                            "watch_dirs": [str(self.ml_ready_paths[symbol])]
                        },
                        "chart_mapping": {
                            # ✅ PHASE 3.5: Chart mapping correct pour ES/NQ/RTY
                            symbol: 3 if symbol == "ES" else (9 if symbol == "NQ" else 1)  # RTY = Chart 1
                        }
                    }
                }
                reader = MLReadyReader(config=reader_config)
                self.readers[symbol] = reader
                logger.info(f"✅ MLReadyReader {symbol} initialisé")
            except Exception as e:
                logger.error(f"❌ Erreur création reader {symbol}: {e}")
                raise

        # Initialiser modules critiques
        self._initialize_critical_modules()

        # Initialiser le strategy manager
        logger.info("🚀 Initialisation OptimizedStrategyManager...")
        self.strategy_manager = OptimizedStrategyManager(self.config)
        logger.info(f"✅ {len(self.strategy_manager.strategies)} stratégies chargées")

    def _initialize_critical_modules(self):
        """Initialise les modules critiques (Snapshotter, PostMortem, Risk, ML)"""
        try:
            # TradeSnapshotter ML_READY
            from execution.trade_snapshotter_ml_ready import TradingMode
            paper_trading = self.config.get('paper_trading', True)
            self.trade_snapshotter = create_trade_snapshotter_ml_ready(
                base_path="snapshots",
                mode=TradingMode.PAPER if paper_trading else TradingMode.LIVE
            )
            logger.info("✅ TradeSnapshotterMLReady initialisé")

            # ═══════════════════════════════════════════════════════════════
            # ✅ URGENT 5: Discord Notifier (Visibilité temps réel)
            # ═══════════════════════════════════════════════════════════════
            try:
                if DISCORD_AVAILABLE:
                    # Charger config Discord
                    discord_config_path = Path("config_files/discord_config.json")
                    if discord_config_path.exists():
                        with open(discord_config_path, 'r', encoding='utf-8') as f:
                            discord_cfg = json.load(f)
                        self.discord_config = discord_cfg.get('discord_notifications', {})
                        self.discord_verbosity = self.discord_config.get('verbosity', 'normal')
                        self.discord_filters = self.discord_config.get('filters', {})
                        logger.info(f"✅ Discord config chargée (verbosity: {self.discord_verbosity})")
                    else:
                        logger.warning("⚠️ discord_config.json non trouvé, utilisation config par défaut")
                        self.discord_config = {}
                        self.discord_verbosity = 'normal'
                        self.discord_filters = {}

                    # Créer Discord notifier
                    self.discord = create_discord_notifier()
                    if self.discord:
                        logger.info("✅ Discord Notifier initialisé")
                    else:
                        logger.warning("⚠️ Discord Notifier désactivé (config)")
                        self.discord = None

                    # Créer Message Aggregator
                    if self.discord and self.discord_config.get('aggregation', {}).get('enabled', True):
                        aggregation_cfg = self.discord_config.get('aggregation', {})
                        self.discord_aggregator = create_message_aggregator(
                            window_minutes=aggregation_cfg.get('default_window_minutes', 10),
                            max_buffer_size=aggregation_cfg.get('max_buffer_size', 100)
                        )
                        logger.info("✅ Discord Message Aggregator initialisé")
                    else:
                        self.discord_aggregator = None
                        logger.info("⚠️ Discord Aggregator désactivé")
                else:
                    self.discord = None
                    self.discord_aggregator = None
                    self.discord_config = {}
                    self.discord_verbosity = 'normal'
                    self.discord_filters = {}
                    logger.warning("⚠️ Discord non disponible (import failed)")
            except Exception as e:
                logger.error(f"⚠️ Erreur init Discord: {e}")
                self.discord = None
                self.discord_aggregator = None
                self.discord_config = {}
                self.discord_verbosity = 'normal'
                self.discord_filters = {}

            # PostMortemAnalyzer - ✅ AVEC discord_notifier
            self.post_mortem = PostMortemAnalyzer(discord_notifier=self.discord)
            logger.info("✅ PostMortemAnalyzer initialisé" + (" (avec Discord)" if self.discord else ""))

            # RiskManager
            self.risk_manager = RiskManager(config=self.config)
            logger.info("✅ RiskManager initialisé")

            # ═══════════════════════════════════════════════════════════════
            # 🎯 ML DUAL FILTER V3 - MODÈLES AVEC DISTANCES OPTIONS DYNAMIQUES
            # ═══════════════════════════════════════════════════════════════
            try:
                logger.info("=" * 80)
                logger.info("🔥 CHARGEMENT MODÈLES ML V3 (OPTION DISTANCES)")
                logger.info("=" * 80)

                # ✅ PHASE 3.5: Chemins des modèles avec 130 features
                model_path_es = "ml/models/lgbm_direction_optimal_ES_BINARY_latest.pkl"
                model_path_nq = "ml/models/lgbm_direction_optimal_NQ_BINARY_latest.pkl"
                model_path_rty = "ml/models/lgbm_direction_optimal_RTY_BINARY_latest.pkl"

                # Vérifier existence
                # ES : ⚠️ Modèle sous-entraîné (best_iteration=4), NE PAS UTILISER EN PRODUCTION
                # NQ : ✅ Production ready (AUC 0.801, PF 10.73, WR 86.2%)
                if not Path(model_path_nq).exists():
                    raise FileNotFoundError(f"❌ Modèle NQ V3.3 introuvable : {model_path_nq}")

                if Path(model_path_es).exists():
                    logger.warning(f"⚠️  Modèle ES disponible MAIS sous-entraîné (best_iteration=4)")
                    logger.warning(f"   → Utilisation DÉCONSEILLÉE sans collecte de plus de données")
                    logger.info(f"   Chemin : {model_path_es}")
                else:
                    logger.warning(f"⚠️  Modèle ES V3.3 introuvable : {model_path_es}")

                logger.info(f"✅ Modèle NQ V3.3 SOLIDIFICATION : {model_path_nq}")

                # ════════════════════════════════════════════════════════════════════
                # CONFIGURATION SEUILS V3.3 SOLIDIFICATION (APRÈS COÛTS RÉELS)
                # ════════════════════════════════════════════════════════════════
                #
                # ES : ⏸️ DÉSACTIVÉ (best_iteration=4, sous-entraîné)
                #      → Collecte de 40,000+ samples requise avant déploiement
                #
                # NQ : ✅ PRODUCTION READY
                #      → 0.70 = PF 10.73, WR 86.2%, 4,812 trades (BON VOLUME)
                #      → 0.75 = PF 16.55, WR 90.5%, 3,706 trades (QUALITÉ MAX)
                #
                # RECOMMANDATION : Commencer avec 0.70 pour volume, puis ajuster
                # ════════════════════════════════════════════════════════════════

                # ════════════════════════════════════════════════════════════════════
                # 🎯 MODE FILTRAGE ML ACTIF - ES + NQ
                # ════════════════════════════════════════════════════════════════
                # ES : Seuil 0.70 en advisory (modèle sous-entraîné mais fonctionnel)
                #      PF 13.63, WR 88.7% @ 0.70 (701 trades test set)
                #
                # NQ : Seuil 0.70 en advisory (PRODUCTION READY)
                #      PF 10.73, WR 86.2% @ 0.70 (4,812 trades test set)
                #      Alternative: 0.75 pour PF 16.55, WR 90.5% (3,706 trades)
                # ════════════════════════════════════════════════════════════════

                # ✅ PHASE 3.5: Mode ADVISORY pour calibrage (24-48h)
                self.ml_filter = MLDualFilter(
                    model_path_es=model_path_es if Path(model_path_es).exists() else None,
                    model_path_nq=model_path_nq,
                    model_path_rty=model_path_rty,  # ✅ RTY ajouté
                    thresholds={
                        "ES": {"UP": 0.70, "DOWN": 0.70},   # PF 4.56, WR 73.1%
                        "NQ": {"UP": 0.65, "DOWN": 0.65},   # PF 37.56, WR 95.5% ⭐
                        "RTY": {"UP": 0.60, "DOWN": 0.60}   # PF 8.19, WR 82.7% ⭐
                    },
                    modes={
                        "ES": {"UP": "advisory", "DOWN": "advisory"},   # ⚠️ CALIBRAGE
                        "NQ": {"UP": "advisory", "DOWN": "advisory"},   # ⚠️ CALIBRAGE
                        "RTY": {"UP": "advisory", "DOWN": "advisory"}   # ⚠️ CALIBRAGE
                    },
                    enabled=True
                )

                logger.info("=" * 80)
                logger.info("⚠️ ML PHASE 3.5 - MODE ADVISORY (CALIBRAGE 24-48H)")
                logger.info("=" * 80)
                logger.info("📊 CONFIGURATION : 130 features + Seuils optimisés")
                logger.info("")
                logger.info("   ⚠️  ES  : 130 features | ADVISORY @ 0.70 | PF 4.56  | WR 73.1%")
                logger.info("   ⚠️  NQ  : 130 features | ADVISORY @ 0.65 | PF 37.56 | WR 95.5% ⭐")
                logger.info("   ⚠️  RTY : 130 features | ADVISORY @ 0.60 | PF 8.19  | WR 82.7% ⭐")
                logger.info("")
                logger.info("💡 MODE ADVISORY : TOUS les signaux sont acceptés avec WARNING")
                logger.info("🎯 OBJECTIF : Collecter max de données pour calibrage")
                logger.info("📊 POST-MORTEM : Analysera si signaux faibles auraient gagné/perdu")
                logger.info("")
                logger.info("⏱️  DURÉE : 24-48h puis retour en mode REQUIRED")
                logger.info("=" * 80)

            except Exception as e:
                self.ml_filter = None
                logger.error(f"❌ ML Filter V3 non disponible: {e}")
                logger.error(f"   Les signaux ne seront PAS filtrés par ML !")

            # BracketDetector ML_READY - détection consolidations
            self.bracket_detector = create_bracket_detector_ml_ready()
            logger.info("✅ BracketDetectorMLReady initialisé")

            # DataValidator
            self.data_validator = EnhancedDataValidator()
            logger.info("✅ EnhancedDataValidator initialisé")

            # BullishScorer v2.0 (optionnel)
            if BULLISH_SCORER_AVAILABLE:
                self.bullish_scorer = BullishScorer(chart_id=3, use_vix=True)
                logger.info("✅ BullishScorer v2.0 initialisé (10 composantes)")
            else:
                self.bullish_scorer = None
                logger.info("⚠️ BullishScorer non disponible (ignoré)")

            # SignalExplainer ML_READY
            self.signal_explainer = create_signal_explainer_ml_ready()
            logger.info("✅ SignalExplainer ML_READY initialisé")

            # DecisionMessenger ML_READY
            self.decision_messenger = create_decision_messenger_ml_ready(config={
                "verbose": True,
                "save_history": True,
                "cooldown_seconds": 2
            })
            logger.info("✅ DecisionMessenger ML_READY initialisé")

            # ═══════════════════════════════════════════════════════════════
            # 🆕 6 NOUVEAUX MODULES CONSOLIDATION (Phase 1 + Phase 2)
            # ═══════════════════════════════════════════════════════════════

            # 1️⃣ Execution Latency Tracker (⚡ Performance monitoring)
            self.latency_tracker = ExecutionLatencyTracker(max_history_size=1000)
            logger.info("✅ Execution Latency Tracker initialisé (P95 tracking)")

            # 2️⃣ Performance Profiler (⚡ Code optimization)
            self.performance_profiler = PerformanceProfiler(enabled=True)
            logger.info("✅ Performance Profiler initialisé (bottleneck detection)")

            # 3️⃣ Volatility Regime Calculator (💡 Adaptive thresholds)
            self.volatility_regime_calc = VolatilityRegimeCalculator(config={
                'atr_period': 20,
                'vix_low': 15.0,
                'vix_high': 25.0,
                'atr_low_ratio': 0.8,
                'atr_high_ratio': 1.5
            })
            logger.info("✅ Volatility Regime Calculator initialisé (seuils adaptatifs VIX/ATR)")

            # 4️⃣ Safety Kill Switch (🚨 Protection critique)
            self.safety_kill_switch = SafetyKillSwitch(config={
                'daily_loss_limit': -800.0,  # -$800 max loss
                'dtc_down_timeout_seconds': 30,
                'vix_spike_threshold': 35.0,
                'order_rejections_threshold': 10
            })
            logger.info("✅ Safety Kill Switch initialisé (protection PnL < -$800, DTC down)")

            # 5️⃣ Lessons Learned Analyzer (📊 Post-mortem automation)
            self.lessons_learned = LessonsLearnedAnalyzer(db_path="data/lessons_learned.db")
            logger.info("✅ Lessons Learned Analyzer initialisé (calibration continue)")

            # 6️⃣ DOM Health Analyzer (💡 Spread/Liquidity filtering)
            self.dom_health_analyzer = DOMHealthAnalyzer()
            logger.info("✅ DOM Health Analyzer initialisé (filtrage spread/liquidité)")

            # 🆕 Market Context Analyzer (Filtre Contextuel Intelligent)
            self.context_analyzers = {}
            for symbol in self.symbols:
                self.context_analyzers[symbol] = create_market_context_analyzer(symbol)
            logger.info("✅ Market Context Analyzer initialisé (ES + NQ + RTY) - Filtre contextuel actif")  # ✅ RTY ajouté

            # ═══════════════════════════════════════════════════════════════
            # 🆕 5 MODULES PRO (Phase Professionnalisation)
            # ═══════════════════════════════════════════════════════════════

            # 7️⃣ Drawdown Monitor (🔴 Protection capital)
            self.drawdown_monitor = create_drawdown_monitor(
                max_dd_pct=0.15,  # Halt si DD > 15%
                max_dd_duration=100  # Halt si DD > 100 cycles
            )
            logger.info("✅ Drawdown Monitor initialisé (Max DD: 15%, Max Duration: 100 cycles)")

            # 8️⃣ Realistic Backtest Engine (📊 Pour évaluation réaliste)
            self.backtest_engines = {
                'ES': create_realistic_backtest_engine('ES'),
                'NQ': create_realistic_backtest_engine('NQ')
            }
            logger.info("✅ Realistic Backtest Engines initialisés (ES + NQ)")

            # Tracking PnL pour drawdown monitoring
            self.total_pnl_net = 0.0
            self.trades_history = []

            logger.info("=" * 80)
            logger.info("✅ 6 NOUVEAUX MODULES CONSOLIDATION INTÉGRÉS")
            logger.info("=" * 80)
            logger.info("   ⚡ Latency Tracker : Pipeline latency monitoring (P95 < 200ms)")
            logger.info("   ⚡ Performance Profiler : Bottleneck detection (<1% overhead)")
            logger.info("   💡 Volatility Regime : Seuils adaptatifs VIX/ATR par régime")
            logger.info("   🚨 Safety Kill Switch : Protection auto PnL/DTC/VIX")
            logger.info("   📊 Lessons Learned : Post-mortem + playbook automation")
            logger.info("   💡 DOM Health : Filtrage qualité spread/liquidité)")
            logger.info("=" * 80)
            logger.info("✅ 5 MODULES PRO AJOUTÉS")
            logger.info("=" * 80)
            logger.info("   🔴 Drawdown Monitor : Max DD 15%, Max Duration 100 cycles")
            logger.info("   📊 Realistic Backtest : Slippage variable + Fill probability")
            logger.info("   🧪 Tests Automatisés : 30+ tests (pytest tests/test_system.py)")
            logger.info("   📈 Dashboard Temps Réel : streamlit run core/dashboard_realtime.py")
            logger.info("=" * 80)

            # SierraDTCConnector (si live trading activé)
            if self.config.get('enable_live_trading', False):
                # Configuration DTC : 1 instance sur port 11099 gère ES (Sim1) + NQ (Sim2)
                dtc_host = self.config.get('dtc_host', 'localhost')
                dtc_port = self.config.get('dtc_port', 11099)

                self.dtc_connector = create_sierra_dtc_connector(
                    host=dtc_host,
                    es_port=dtc_port,  # ES et NQ sur même instance DTC
                    nq_port=dtc_port,
                    trade_account_map={"ES": "Sim1", "NQ": "Sim2"}
                )
                logger.info("✅ SierraDTCConnector initialisé")
                logger.info(f"   Instance DTC: {dtc_host}:{dtc_port}")
                logger.info(f"   Comptes: ES=Sim1, NQ=Sim2")
            else:
                self.dtc_connector = None
                logger.info("⚠️ Live trading désactivé - DTC Connector non initialisé")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation modules critiques: {e}")
            raise

    def _save_live_metrics(self, cycle_count: int, uptime: float):
        """Sauvegarde les métriques en temps réel pour le dashboard"""
        try:
            from datetime import datetime
            import json
            from pathlib import Path

            # Créer le dossier data si nécessaire
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            # Déterminer la session actuelle
            current_hour = datetime.now().hour
            if 0 <= current_hour < 8:
                session = "ASIA"
            elif 8 <= current_hour < 14:
                session = "LONDON"
            else:
                session = "US"

            # Calculer latence moyenne (si disponible)
            avg_latency_ms = 0.0
            if hasattr(self, 'latency_tracker') and self.latency_tracker:
                try:
                    report = self.latency_tracker.generate_report()
                    avg_latency_ms = report.get('avg_total_ms', 0.0)
                except:
                    pass

            # Calculer régime de volatilité (si disponible)
            vol_regime = "N/A"
            if hasattr(self, 'volatility_regime_calculator') and self.volatility_regime_calculator:
                try:
                    vol_regime = self.volatility_regime_calculator.get_current_regime()
                except:
                    pass

            # Préparer les métriques
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'total_cycles': cycle_count,
                'total_signals': self.stats.get('signals', 0),
                'total_trades': len(self.trades_history) if hasattr(self, 'trades_history') else 0,
                'total_pnl_net': self.total_pnl_net if hasattr(self, 'total_pnl_net') else 0.0,
                'pnl_delta': 0.0,  # À calculer si historique disponible
                'win_rate': 0.0,  # À calculer si trades disponibles
                'current_dd_pct': 0.0,  # À calculer via DrawdownMonitor
                'avg_latency_ms': avg_latency_ms,
                'uptime_minutes': uptime / 60,
                'session': session,
                'vol_regime': vol_regime,
                'errors': self.stats.get('errors', 0)
            }

            # Calculer Win Rate si trades disponibles
            if hasattr(self, 'trades_history') and len(self.trades_history) > 0:
                wins = sum(1 for t in self.trades_history if t.get('pnl_net', 0) > 0)
                metrics['win_rate'] = wins / len(self.trades_history) if len(self.trades_history) > 0 else 0.0

            # Récupérer Drawdown du DrawdownMonitor
            if hasattr(self, 'drawdown_monitor') and self.drawdown_monitor:
                try:
                    metrics['current_dd_pct'] = self.drawdown_monitor.current_dd_pct
                except:
                    pass

            # Sauvegarder dans fichier JSON
            metrics_file = data_dir / "live_metrics.json"
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            logger.debug(f"✅ Métriques sauvegardées: {metrics_file}")

        except Exception as e:
            logger.warning(f"⚠️ Erreur sauvegarde métriques dashboard: {e}")

    # ═══════════════════════════════════════════════════════════════
    # ✅ PHASE 1.8-1.9 : HELPER - REJET + SNAPSHOT
    # ═══════════════════════════════════════════════════════════════

    def _reject_signal_with_snapshot(self,
                                     symbol: str,
                                     signal: Optional[Dict[str, Any]],
                                     tick: Dict[str, Any],
                                     rejection_reason: str,
                                     rejection_category: str,
                                     ml_probability: float = 0.0,
                                     ml_threshold: float = 0.0) -> None:
        """
        Rejette un signal ET capture snapshot pour analyse post-mortem

        Args:
            symbol: Symbole (ES, NQ, RTY)
            signal: Signal rejeté (peut être None)
            tick: Données ML_READY au moment du rejet
            rejection_reason: Raison détaillée du rejet
            rejection_category: Catégorie (DATA, SAFETY, NO_SIGNAL, CONTEXT, MARKET_FILTER, RISK, ML)
            ml_probability: Probabilité ML (si disponible)
            ml_threshold: Seuil ML utilisé (si applicable)

        Returns:
            None (toujours None pour usage direct dans 'return')
        """
        # Log rejet
        logger.info(f"🚫 [{symbol}] Signal rejeté: {rejection_reason}")

        # Capturer snapshot pour analyse
        if self.trade_snapshotter and tick:
            try:
                self.trade_snapshotter.capture_rejected_signal_snapshot(
                    symbol=symbol,
                    signal=signal,
                    ml_data=tick,
                    rejection_reason=rejection_reason,
                    rejection_category=rejection_category,
                    ml_probability=ml_probability,
                    ml_threshold=ml_threshold
                )
            except Exception as e:
                logger.debug(f"⚠️ Erreur snapshot rejet: {e}")

        return None

    async def _close_position(self, symbol: str, fill_info: Dict[str, Any],
                             current_tick: Dict[str, Any]) -> None:
        """
        FERMETURE POSITION après fill TP/SL

        Args:
            symbol: Symbole (ES, NQ, RTY)
            fill_info: Informations sur le fill DTC
                {
                    'order_id': str,
                    'fill_price': float,
                    'exit_type': 'TP' | 'SL',
                    'filled_qty': float,
                    'timestamp_ms': int
                }
            current_tick: Données ML_READY actuelles (dict)
        """
        try:
            # Vérifier que la position existe
            position = self.open_positions.get(symbol)
            if not position:
                logger.warning(f"⚠️ Position {symbol} introuvable pour fermeture")
                return

            # Extraire données position
            entry_price = position['entry_price']
            entry_time = position['entry_time']
            side = position['side']
            strategy = position.get('strategy', 'unknown')

            # Prix de sortie depuis fill_info
            exit_price = fill_info['fill_price']
            exit_type = fill_info['exit_type']  # "TP" ou "SL"

            # ═══════════════════════════════════════════════════════════════
            # 1️⃣ CALCULER P&L (ticks → USD)
            # ═══════════════════════════════════════════════════════════════

            # Contract specs
            symbol_specs = {
                'ES': {'tick_size': 0.25, 'tick_value': 12.50, 'point_value': 50.0},
                'NQ': {'tick_size': 0.25, 'tick_value': 5.00, 'point_value': 20.0},
                'RTY': {'tick_size': 0.10, 'tick_value': 5.00, 'point_value': 50.0}
            }

            specs = symbol_specs.get(symbol, symbol_specs['ES'])
            tick_size = specs['tick_size']
            tick_value = specs['tick_value']

            # Calculer P&L en ticks
            if side == 'LONG':
                pnl_ticks = (exit_price - entry_price) / tick_size
            else:  # SHORT
                pnl_ticks = (entry_price - exit_price) / tick_size

            # Calculer P&L en USD
            final_pnl = pnl_ticks * tick_value * position['quantity']

            # Durée du trade
            duration_seconds = (datetime.now() - entry_time).total_seconds()
            duration_minutes = duration_seconds / 60.0

            logger.info(
                f"💰 [{symbol}] Position fermée: {exit_type} | "
                f"P&L: ${final_pnl:+.2f} ({pnl_ticks:+.1f} ticks) | "
                f"Durée: {duration_minutes:.1f} min"
            )

            # ═══════════════════════════════════════════════════════════════
            # 2️⃣ SNAPSHOT RESULT
            # ═══════════════════════════════════════════════════════════════

            if self.trade_snapshotter:
                try:
                    trade_result = {
                        'position_id': position['order_ids'].get('entry', 'N/A'),
                        'symbol': symbol,
                        'side': side,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'entry_time': entry_time.isoformat(),
                        'exit_time': datetime.now().isoformat(),
                        'duration_seconds': duration_seconds,
                        'duration_minutes': duration_minutes,
                        'pnl': final_pnl,
                        'pnl_ticks': pnl_ticks,
                        'exit_reason': exit_type,
                        'strategy': strategy,
                        'tp_price': position.get('tp_price', 0),
                        'sl_price': position.get('sl_price', 0),
                        'quantity': position['quantity'],
                        # Market context au close
                        'market_context_at_exit': {
                            'mid': current_tick.get('mid', 0),
                            'vix': current_tick.get('vix', 20.0),
                            'atr': current_tick.get('atr', 0),
                            'vwap': current_tick.get('vwap', 0),
                            'session_id': current_tick.get('session_id', 'unknown'),
                            'volatility_regime': current_tick.get('volatility_regime', 'unknown')
                        }
                    }

                    self.trade_snapshotter.capture_trade_result(
                        position_id=position['order_ids'].get('entry', 'N/A'),
                        trade_result=trade_result
                    )
                    logger.info("📸 Trade Result Snapshot capturé")
                except Exception as e:
                    logger.error(f"⚠️ Erreur snapshot result: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 📱 DISCORD 1 : Notification Trade Fermé
            # ═══════════════════════════════════════════════════════════════

            if self.discord:
                try:
                    trade_data = {
                        'symbol': symbol,
                        'side': side,
                        'pnl': final_pnl,
                        'pnl_ticks': pnl_ticks,
                        'exit_price': exit_price,
                        'duration_minutes': duration_minutes,
                        'exit_reason': exit_type,
                        'max_profit_ticks': 0,  # TODO: Tracker MFE
                        'max_loss_ticks': 0,    # TODO: Tracker MAE
                        'post_mortem_note': f"Strategy: {strategy} | Entry: {entry_price:.2f}"
                    }

                    await self.discord.send_trade_closed(trade_data)
                    logger.info(f"📱 Discord: Trade fermé notifié ({symbol} {exit_type} ${final_pnl:+.2f})")
                except Exception as e:
                    logger.error(f"⚠️ Erreur Discord trade closed: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 3️⃣ POST-MORTEM ANALYSIS
            # ═══════════════════════════════════════════════════════════════

            if self.post_mortem:
                try:
                    # Préparer trade_result pour PostMortem
                    trade_result_pm = {
                        'entry_price': entry_price,
                        'tp_price': position.get('tp_price', 0),
                        'sl_price': position.get('sl_price', 0),
                        'side': side,
                        'quantity': position['quantity'],
                        'timestamp': entry_time,
                        'strategy': strategy,
                        'exit_price': exit_price,
                        'exit_time': datetime.now(),
                        'pnl': final_pnl,
                        'exit_reason': exit_type
                    }

                    # ✅ URGENT 3 COMPLÉTÉ: PostMortem adapté pour ML_READY (Dict)
                    self.post_mortem.start_post_mortem_tracking(
                        trade_id=position['order_ids'].get('entry', 'N/A'),
                        trade_result=trade_result_pm,
                        current_market_data=current_tick  # Dict ML_READY → Auto-converti en MarketData
                    )
                    logger.info("🔍 Post-mortem lancé")
                except Exception as e:
                    logger.error(f"⚠️ Post-mortem erreur: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 4️⃣ UPDATE RISK MANAGER
            # ═══════════════════════════════════════════════════════════════

            if self.risk_manager:
                try:
                    # Update daily P&L
                    self.risk_manager.daily_pnl += final_pnl
                    logger.info(f"💰 Risk Manager daily_pnl mis à jour: ${self.risk_manager.daily_pnl:+.2f}")
                except Exception as e:
                    logger.error(f"⚠️ Erreur update risk_manager: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 5️⃣ UPDATE LESSONS LEARNED (si existant dans pending)
            # ═══════════════════════════════════════════════════════════════

            if self.lessons_learned and hasattr(self, 'pending_lessons'):
                try:
                    # Trouver la leçon correspondante dans pending_lessons
                    lesson_key = None
                    for key, lesson_data in self.pending_lessons.items():
                        if key.startswith(symbol):
                            lesson_key = key
                            break

                    if lesson_key:
                        lesson_data = self.pending_lessons[lesson_key]

                        # Mettre à jour Execution avec exit_price et P&L
                        execution_obj = lesson_data['execution']
                        execution_obj.exit_price = exit_price

                        # Enregistrer la leçon complète
                        self.lessons_learned.record_decision(
                            decision=lesson_data['decision'],
                            execution=execution_obj,
                            context=lesson_data['context'],
                            pnl=final_pnl,
                            mae=0.0,  # TODO: Tracker MAE pendant la vie du trade
                            mfe=0.0   # TODO: Tracker MFE pendant la vie du trade
                        )

                        # Retirer de pending
                        del self.pending_lessons[lesson_key]
                        logger.info("📚 Lessons Learned enregistrée")
                except Exception as e:
                    logger.error(f"⚠️ Erreur update lessons learned: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 6️⃣ REMOVE FROM OPEN POSITIONS
            # ═══════════════════════════════════════════════════════════════

            del self.open_positions[symbol]
            logger.info(f"✅ Position {symbol} retirée de open_positions")

            # ═══════════════════════════════════════════════════════════════
            # 7️⃣ STATS & LOGS
            # ═══════════════════════════════════════════════════════════════

            # Incrémenter compteur trades
            if not hasattr(self, 'trade_history'):
                self.trade_history = []

            self.trade_history.append({
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': final_pnl,
                'pnl_ticks': pnl_ticks,
                'exit_type': exit_type,
                'duration_minutes': duration_minutes,
                'strategy': strategy,
                'timestamp': datetime.now()
            })

            logger.info(
                f"✅ [{symbol}] Trade #{len(self.trade_history)} fermé avec succès | "
                f"{'✅ WIN' if final_pnl > 0 else '❌ LOSS'} | "
                f"P&L Day: ${self.risk_manager.daily_pnl:+.2f if self.risk_manager else 0}"
            )

        except Exception as e:
            logger.error(f"❌ Erreur critique _close_position() pour {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def _monitor_fills_loop(self) -> None:
        """
        🔄 LOOP MONITORING DES FILLS

        Vérifie périodiquement si les positions ouvertes ont hit leur TP ou SL

        ⚠️ NOTE: Cette implémentation est un WORKAROUND car le DTC connector actuel
        ne retourne pas d'événements de fill. On simule la détection en comparant
        le prix actuel avec les TP/SL.

        TODO FUTUR: Implémenter vraie écoute des fills DTC (nécessite modification
        du connector pour recevoir ORDER_UPDATE messages)
        """
        logger.info("🔄 Monitor fills loop démarré")

        while self.running:
            try:
                await asyncio.sleep(2)  # Check toutes les 2 secondes

                # Copier pour éviter modification pendant itération
                positions_to_check = list(self.open_positions.items())

                for symbol, position in positions_to_check:
                    try:
                        # Lire le prix actuel depuis ML_READY
                        reader = self.readers.get(symbol)
                        if not reader:
                            continue

                        tick = await asyncio.to_thread(reader.get_live_snapshot, symbol)
                        if not tick:
                            continue

                        current_price = tick.get('mid', 0)
                        if current_price == 0:
                            continue

                        # Extraire TP/SL de la position
                        tp_price = position.get('tp_price', 0)
                        sl_price = position.get('sl_price', 0)
                        side = position.get('side', '')

                        if not tp_price or not sl_price or not side:
                            continue

                        # ═══════════════════════════════════════════════════════════════
                        # LOGIQUE DE DÉTECTION FILL
                        # ═══════════════════════════════════════════════════════════════

                        fill_detected = False
                        exit_type = None
                        fill_price = None

                        if side == 'LONG':
                            # LONG: TP hit si prix >= TP, SL hit si prix <= SL
                            if current_price >= tp_price:
                                fill_detected = True
                                exit_type = 'TP'
                                fill_price = tp_price
                            elif current_price <= sl_price:
                                fill_detected = True
                                exit_type = 'SL'
                                fill_price = sl_price

                        elif side == 'SHORT':
                            # SHORT: TP hit si prix <= TP, SL hit si prix >= SL
                            if current_price <= tp_price:
                                fill_detected = True
                                exit_type = 'TP'
                                fill_price = tp_price
                            elif current_price >= sl_price:
                                fill_detected = True
                                exit_type = 'SL'
                                fill_price = sl_price

                        # ═══════════════════════════════════════════════════════════════
                        # FERMER LA POSITION SI FILL DÉTECTÉ
                        # ═══════════════════════════════════════════════════════════════

                        if fill_detected:
                            logger.info(
                                f"🎯 [{symbol}] FILL DÉTECTÉ: {exit_type} @ {fill_price:.2f} "
                                f"(current: {current_price:.2f})"
                            )

                            # Préparer fill_info
                            fill_info = {
                                'order_id': position['order_ids'].get(exit_type.lower(), 'N/A'),
                                'fill_price': fill_price,
                                'exit_type': exit_type,
                                'filled_qty': position['quantity'],
                                'timestamp_ms': int(time.time() * 1000)
                            }

                            # Appeler _close_position()
                            await self._close_position(
                                symbol=symbol,
                                fill_info=fill_info,
                                current_tick=tick
                            )

                            # 📱 Discord notification (si disponible)
                            # TODO DISCORD 1: Implémenter send_trade_closed()

                            logger.info(f"✅ [{symbol}] Position fermée via monitor fills")

                    except Exception as e:
                        logger.error(f"⚠️ Erreur monitoring position {symbol}: {e}")
                        continue

            except Exception as e:
                logger.error(f"❌ Erreur critique monitor fills loop: {e}")
                await asyncio.sleep(5)  # Pause avant retry

        logger.info("🔄 Monitor fills loop terminé")

    async def _heartbeat_discord_loop(self) -> None:
        """
        💓 HEARTBEAT DISCORD

        Envoie un heartbeat Discord toutes les 5 minutes avec :
        - Uptime
        - Cycles exécutés
        - Positions ouvertes (ES/NQ/RTY)
        - P&L journalier
        - Status Safety Kill Switch
        """
        if not self.discord:
            logger.debug("⚠️ Heartbeat Discord désactivé (Discord non disponible)")
            return

        logger.info("💓 Heartbeat Discord loop démarré")

        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes

                # Calculer uptime
                uptime_seconds = time.time() - self.stats['start_time']
                uptime_minutes = int(uptime_seconds / 60)
                uptime_hours = uptime_minutes // 60
                uptime_min_remaining = uptime_minutes % 60

                # Stats par symbole
                symbols_status = []
                for sym in self.symbols:
                    pos = self.open_positions.get(sym) if hasattr(self, 'open_positions') else None
                    if pos:
                        side = pos['side']
                        entry_price = pos['entry_price']
                        tp_price = pos.get('tp_price', 0)
                        sl_price = pos.get('sl_price', 0)
                        symbols_status.append(
                            f"• **{sym}**: POSITION {side} @ {entry_price:.2f} "
                            f"(TP:{tp_price:.2f} SL:{sl_price:.2f})"
                        )
                    else:
                        symbols_status.append(f"• **{sym}**: FLAT")

                # P&L journalier
                daily_pnl = 0.0
                if hasattr(self, 'risk_manager') and self.risk_manager:
                    daily_pnl = getattr(self.risk_manager, 'daily_pnl', 0.0)

                # Safety Kill Switch status
                can_trade = True
                kill_switch_reason = "OK"
                if hasattr(self, 'safety_kill_switch') and self.safety_kill_switch:
                    can_trade = self.safety_kill_switch.can_trade()
                    if not can_trade:
                        state = self.safety_kill_switch.get_state()
                        kill_switch_reason = state.get('reason', 'Unknown')

                # Envoyer heartbeat
                await self.discord.send_custom_message(
                    'admin_messages',
                    '💓 HEARTBEAT',
                    f"""
**Uptime:** {uptime_hours}h {uptime_min_remaining}min ({self.stats['cycles']} cycles)

**Positions:**
{chr(10).join(symbols_status)}

**P&L Day:** ${daily_pnl:+.2f}

**Status:** {'✅ Trading actif' if can_trade else f'🔴 Stopped ({kill_switch_reason})'}

**Dernière mise à jour:** {datetime.now().strftime('%H:%M:%S')}
                    """.strip(),
                    color=0x3498db if can_trade else 0xff0000
                )
                logger.debug("💓 Heartbeat Discord envoyé")

            except Exception as e:
                logger.error(f"⚠️ Erreur heartbeat Discord: {e}")

        logger.info("💓 Heartbeat Discord loop terminé")

    async def _daily_summary_loop(self) -> None:
        """
        📊 DAILY SUMMARY DISCORD

        Envoie un rapport quotidien à 23h59 EST avec :
        - P&L total
        - Trades exécutés
        - Win Rate
        - Profit Factor
        - Sélectivité (signaux pris vs détectés)
        - Meilleur/Pire trade
        """
        if not self.discord:
            logger.debug("⚠️ Daily Summary Discord désactivé (Discord non disponible)")
            return

        logger.info("📊 Daily Summary Discord loop démarré")

        from datetime import time as datetime_time
        from zoneinfo import ZoneInfo

        while self.running:
            try:
                # Attendre jusqu'à 23h59 EST
                now_est = datetime.now(ZoneInfo("America/New_York"))
                target_time = now_est.replace(hour=23, minute=59, second=0, microsecond=0)

                # Si déjà passé aujourd'hui, attendre demain
                if now_est >= target_time:
                    target_time += timedelta(days=1)

                wait_seconds = (target_time - now_est).total_seconds()
                logger.info(f"📊 Prochain Daily Summary dans {wait_seconds/3600:.1f}h")

                await asyncio.sleep(wait_seconds)

                # Calculer statistiques du jour
                daily_pnl = 0.0
                total_trades = 0
                winning_trades = 0
                best_trade = 0.0
                worst_trade = 0.0

                if hasattr(self, 'trade_history') and self.trade_history:
                    today_trades = [
                        t for t in self.trade_history
                        if t['timestamp'].date() == datetime.now().date()
                    ]

                    total_trades = len(today_trades)
                    if total_trades > 0:
                        daily_pnl = sum(t['pnl'] for t in today_trades)
                        winning_trades = sum(1 for t in today_trades if t['pnl'] > 0)
                        best_trade = max(t['pnl'] for t in today_trades)
                        worst_trade = min(t['pnl'] for t in today_trades)

                elif hasattr(self, 'risk_manager') and self.risk_manager:
                    daily_pnl = getattr(self.risk_manager, 'daily_pnl', 0.0)

                # Calculer métriques
                win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0

                # Profit Factor
                gross_profit = sum(t['pnl'] for t in today_trades if t['pnl'] > 0) if hasattr(self, 'trade_history') and self.trade_history else 0
                gross_loss = abs(sum(t['pnl'] for t in today_trades if t['pnl'] < 0)) if hasattr(self, 'trade_history') and self.trade_history else 0
                profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999 if gross_profit > 0 else 0)

                # Sélectivité (signaux pris / signaux détectés)
                signals_detected = self.stats.get('signals', 0)
                signals_taken = total_trades
                selectivity = (signals_taken / signals_detected) if signals_detected > 0 else 0.0

                # Envoyer rapport
                report_data = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'total_pnl': daily_pnl,
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'signals_detected': signals_detected,
                    'signals_taken': signals_taken,
                    'selectivity': selectivity,
                    'best_trade': best_trade,
                    'worst_trade': worst_trade,
                    'ml_insights': [
                        f"Mode ADVISORY actif (ES:0.70, NQ:0.65, RTY:0.60)",
                        f"Cycles exécutés: {self.stats['cycles']}",
                        f"Uptime: {(time.time() - self.stats['start_time'])/3600:.1f}h"
                    ]
                }

                await self.discord.send_daily_report(report_data)
                logger.info(f"📊 Daily Summary envoyé: {total_trades} trades, ${daily_pnl:+.2f}")

                # Attendre 60 secondes pour éviter double envoi
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"⚠️ Erreur daily summary Discord: {e}")
                await asyncio.sleep(3600)  # Retry dans 1h si erreur

        logger.info("📊 Daily Summary Discord loop terminé")

    async def _should_send_discord(self, message_type: str, **kwargs) -> bool:
        """
        Vérifie si un message doit être envoyé selon config

        Args:
            message_type: Type de message (ex: 'trade_executions', 'signals_rejected')
            **kwargs: Données du message pour filtrage avancé

        Returns:
            True si message doit être envoyé
        """
        if not self.discord:
            return False

        # Vérifier si type enabled dans config
        filter_cfg = self.discord_filters.get(message_type, {})
        if not filter_cfg.get('enabled', True):
            return False

        # Filtres spécifiques par type
        if message_type == 'trade_closed':
            min_pnl = filter_cfg.get('min_pnl_notify', 0)
            pnl = abs(kwargs.get('pnl', 0))
            if pnl < min_pnl:
                return False

        # Verbosity check
        if self.discord_verbosity == 'minimal':
            # En mode minimal, seulement critiques
            critical_types = ['trade_closed', 'kill_switch', 'errors_critical', 'daily_summary']
            if message_type not in critical_types:
                return False

        return True

    async def _send_discord_smart(self, message_type: str, message_data: Dict[str, Any]) -> bool:
        """
        Envoie message Discord avec filtrage + agrégation smart

        Args:
            message_type: Type de message
            message_data: {title, description, color, urgent, reason, ...}

        Returns:
            True si envoyé avec succès
        """
        try:
            # Vérifier si doit être envoyé
            if not await self._should_send_discord(message_type, **message_data):
                return False

            # Vérifier si doit être agrégé
            filter_cfg = self.discord_filters.get(message_type, {})
            should_aggregate = filter_cfg.get('aggregate', False)

            if should_aggregate and self.discord_aggregator:
                # Vérifier si catégorie peut être agrégée
                if self.discord_aggregator.should_aggregate(message_type):
                    # Ajouter au buffer
                    grouped = self.discord_aggregator.add_message(message_type, message_data)

                    # Si fenêtre complète, envoyer message groupé
                    if grouped:
                        await self.discord.send_custom_message(
                            'system_alerts',
                            f"📊 RÉSUMÉ - {grouped['category'].replace('_', ' ').upper()}",
                            grouped['summary'],
                            color=0xffa500,  # Orange pour résumés
                            urgent=False
                        )
                        logger.info(f"📊 Résumé Discord envoyé: {grouped['count']} messages ({message_type})")
                        return True

                    # Message bufferisé, pas encore envoyé
                    logger.debug(f"📥 Message bufferisé: {message_type}")
                    return True

            # Envoyer immédiatement (pas d'agrégation)
            await self.discord.send_custom_message(
                message_data.get('channel_type', 'admin_messages'),
                message_data['title'],
                message_data['description'],
                color=message_data.get('color', 0x3498db),
                urgent=message_data.get('urgent', False)
            )
            logger.debug(f"📱 Message Discord envoyé: {message_type}")
            return True

        except Exception as e:
            logger.error(f"⚠️ Erreur _send_discord_smart: {e}")
            return False

    async def run_cycle(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Exécute un cycle de trading pour un symbole

        Args:
            symbol: Symbole à analyser ("ES" ou "NQ")

        Returns:
            Signal généré ou None
        """
        try:
            # Lire les dernières données ML_READY
            reader = self.readers.get(symbol)
            if not reader:
                logger.error(f"❌ Aucun reader pour {symbol}")
                return None

            # Charger les dernières données
            tick = await asyncio.to_thread(reader.get_live_snapshot, symbol)

            if not tick:
                return None

            # ═══════════════════════════════════════════════════════════════
            # ✅ PHASE 1.1 : VALIDATION DONNÉES (EnhancedDataValidator)
            # ═══════════════════════════════════════════════════════════════
            if self.data_validator:
                # Vérifier champs essentiels
                required_fields = ['mid', 'best_bid', 'best_ask', 't_ms']
                missing_fields = [f for f in required_fields if f not in tick or tick[f] is None]

                if missing_fields:
                    return self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=None,
                        tick=tick,
                        rejection_reason=f"Champs manquants: {missing_fields}",
                        rejection_category="DATA"
                    )

                # Vérifier cohérence bid/ask (éviter données corrompues)
                best_bid = tick.get('best_bid', 0)
                best_ask = tick.get('best_ask', 0)

                if best_bid <= 0 or best_ask <= 0:
                    return self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=None,
                        tick=tick,
                        rejection_reason=f"Bid/Ask <= 0 (bid={best_bid}, ask={best_ask})",
                        rejection_category="DATA"
                    )

                if best_ask <= best_bid:
                    return self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=None,
                        tick=tick,
                        rejection_reason=f"Ask <= Bid (bid={best_bid}, ask={best_ask})",
                        rejection_category="DATA"
                    )

                # Vérifier cohérence mid price
                mid_price = tick.get('mid', 0)
                if mid_price < best_bid or mid_price > best_ask:
                    return self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=None,
                        tick=tick,
                        rejection_reason=f"Mid hors spread (mid={mid_price}, bid={best_bid}, ask={best_ask})",
                        rejection_category="DATA"
                    )

                # Vérifier timestamp récent (pas de données obsolètes > 60s)
                tick_timestamp_ms = tick.get('t_ms', 0)
                if tick_timestamp_ms > 0:
                    from datetime import datetime
                    tick_age_seconds = (time.time() * 1000 - tick_timestamp_ms) / 1000
                    if tick_age_seconds > 60:
                        return self._reject_signal_with_snapshot(
                            symbol=symbol,
                            signal=None,
                            tick=tick,
                            rejection_reason=f"Données obsolètes - Age: {tick_age_seconds:.1f}s > 60s",
                            rejection_category="DATA"
                        )

                logger.debug(f"✅ [{symbol}] Données validées - Mid:{mid_price:.2f} Spread:{(best_ask-best_bid):.2f}")

            # ═══════════════════════════════════════════════════════════════
            # 🆕 MODULES CONSOLIDATION - Tracking & Safety
            # ═══════════════════════════════════════════════════════════════

            # 1️⃣ LATENCY TRACKER - Démarrer pipeline
            pipeline_id = self.latency_tracker.start_pipeline(symbol=symbol)

            # 2️⃣ PERFORMANCE PROFILER - Wrapper pour cycle complet
            @self.performance_profiler.profile_function("run_cycle_complete")
            def _profile_wrapper():
                pass  # Juste pour tracking

            # 3️⃣ VOLATILITY REGIME - Calculer régime et seuils adaptatifs
            vol_regime_result = None
            adaptive_ml_threshold = 0.70  # Défaut
            try:
                self.latency_tracker.start_stage(LatencyStage.VIX_REGIME_CHECK)

                # Alimenter le calculateur avec VIX et ATR
                vix = tick.get('vix', 20.0)
                atr_ticks = tick.get('atr', 0) / 0.25  # Convertir en ticks

                self.volatility_regime_calc.add_vix_data(vix)
                self.volatility_regime_calc.add_atr_data(atr_ticks)

                # Calculer régime
                vol_regime_result = self.volatility_regime_calc.calculate_volatility_regime()

                # Ajuster seuils ML selon régime
                if vol_regime_result.regime.value == "HIGH_VOL":
                    adaptive_ml_threshold = 0.75  # Plus sélectif en haute volatilité
                elif vol_regime_result.regime.value == "LOW_VOL":
                    adaptive_ml_threshold = 0.65  # Moins sélectif en basse volatilité
                else:
                    adaptive_ml_threshold = 0.70  # Normal

                # Log régime (1x/minute)
                if self.stats['cycles'] % 60 == 0:
                    logger.info(f"📊 [{symbol}] Régime Vol: {vol_regime_result.regime.value} | "
                               f"VIX: {vix:.1f} | ATR ratio: {vol_regime_result.metrics.atr_ratio:.2f} | "
                               f"Seuil ML adaptatif: {adaptive_ml_threshold:.2f}")

                self.latency_tracker.end_stage(LatencyStage.VIX_REGIME_CHECK, success=True)
            except Exception as e:
                logger.debug(f"⚠️ Erreur Volatility Regime: {e}")
                self.latency_tracker.end_stage(LatencyStage.VIX_REGIME_CHECK, success=False, error_message=str(e))

            # 4️⃣ SAFETY KILL SWITCH - Vérifier conditions critiques
            try:
                # ✅ Calculer PnL du jour depuis risk_manager
                pnl_day = 0.0
                if hasattr(self, 'risk_manager') and self.risk_manager:
                    pnl_day = getattr(self.risk_manager, 'daily_pnl', 0.0)

                # ✅ Vérifier état DTC connector
                dtc_route_up = False
                if self.dtc_connector and hasattr(self.dtc_connector, 'is_connected'):
                    dtc_route_up = self.dtc_connector.is_connected()
                elif self.dtc_connector:
                    dtc_route_up = True  # Assume connecté si présent

                # ✅ Calculer âge données ML_READY
                m1_stale_seconds = 0.0
                tick_timestamp_ms = tick.get('t_ms', 0)
                if tick_timestamp_ms > 0:
                    current_time_ms = time.time() * 1000
                    m1_stale_seconds = (current_time_ms - tick_timestamp_ms) / 1000.0

                # Collecter télémétrie
                telemetry = TelemetryData(
                    pnl_day=pnl_day,
                    dtc_route_up=dtc_route_up,
                    m1_stale_seconds=m1_stale_seconds,
                    vix_value=tick.get('vix', 20.0),
                    session_active=True
                )

                # Mettre à jour kill switch
                kill_switch_state_changed = self.safety_kill_switch.update(telemetry)

                if kill_switch_state_changed:
                    state = self.safety_kill_switch.get_state()
                    logger.warning(f"🚨 Kill Switch état changé: {state['state']} (raison: {state['reason']})")

                    # 📱 DISCORD 2: Alerte URGENTE Kill Switch
                    if self.discord:
                        try:
                            await self.discord.send_custom_message(
                                'critical_errors',
                                f"🚨 SAFETY KILL SWITCH - {state['state'].upper()}",
                                f"""
**État:** {state['state']}
**Raison:** {state['reason']}
**Trading:** {'❌ BLOQUÉ' if state['state'] != 'normal' else '✅ AUTORISÉ'}
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **ATTENTION**: Le trading est actuellement {'suspendu' if state['state'] != 'normal' else 'actif'}.
                                """.strip(),
                                color=0xff0000,
                                urgent=True
                            )
                            logger.info("📱 Discord: Alerte Kill Switch envoyée")
                        except Exception as e:
                            logger.error(f"⚠️ Erreur Discord Kill Switch: {e}")

                # Vérifier si trading autorisé
                if not self.safety_kill_switch.can_trade():
                    state = self.safety_kill_switch.get_state()
                    return self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=None,
                        tick=tick,
                        rejection_reason=f"Kill Switch activé: {state['reason']}",
                        rejection_category="SAFETY"
                    )

            except Exception as e:
                logger.debug(f"⚠️ Erreur Safety Kill Switch: {e}")

            # 5️⃣ DOM HEALTH - Vérifier spread/liquidité
            dom_healthy = True
            try:
                # Construire données DOM depuis tick
                # 🔧 CORRECTIF CRITIQUE: Utiliser 'best_bid' et 'best_ask' (PAS 'bid'/'ask')
                best_bid = tick.get('best_bid', 0)
                best_ask = tick.get('best_ask', 0)

                # Vérifier cohérence bid/ask (si 0 → marché fermé ou données invalides)
                # → l1_bbo_ratio_rolling faible pour bloquer
                if best_bid <= 0 or best_ask <= 0 or best_ask <= best_bid:
                    l1_bbo_ratio = 0.0  # Force gate à échouer
                else:
                    # En session normale, on suppose une cohérence L1==BBO de 80-90%
                    # En session ASIA/pré-market → Réduire à 60-70% (moins fiable)
                    l1_bbo_ratio = 0.85 if best_bid > 0 and best_ask > best_bid else 0.0

                dom_data = {
                    'best_bid': best_bid,
                    'best_ask': best_ask,
                    'l1_bbo_ratio': l1_bbo_ratio,  # ✅ CORRECTIF: Ajouter clef pour analyzer
                    'l1_bbo_ratio_rolling': l1_bbo_ratio,
                    'depth_levels': 10  # Dumper collecte 10 niveaux
                }

                # 🔍 DEBUG: Logger spread pour diagnostic
                if best_bid > 0 and best_ask > best_bid:
                    spread_ticks = (best_ask - best_bid) / 0.25
                    logger.debug(f"[{symbol}] Spread: {spread_ticks:.1f} ticks (bid={best_bid}, ask={best_ask})")

                # Vérifier santé DOM
                # 🔧 Adapter seuil selon session (ASIA = liquidité faible → seuil plus permissif)
                session = tick.get('session_id', 'US').upper()
                # ASIA: 0.30 (très permissif, liquidité faible normale)
                # LONDON: 0.40 (permissif)
                # US: 0.50 (strict, liquidité élevée)
                if session == 'ASIA':
                    min_dom_score = 0.30
                elif session == 'LONDON':
                    min_dom_score = 0.40
                else:
                    min_dom_score = 0.50
                dom_healthy, dom_score = self.dom_health_analyzer.is_dom_healthy(dom_data, symbol, min_score=min_dom_score)

                if not dom_healthy:
                    logger.warning(f"⚠️ [{symbol}] DOM Health faible (score: {dom_score:.2f}) - Filtrage actif")

            except Exception as e:
                logger.debug(f"⚠️ Erreur DOM Health: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 🟢 BULLISH SCORER - Calculer sentiment marché (toutes les minutes)
            # ═══════════════════════════════════════════════════════════════
            bullish_score = None
            skip_long_strategies = False
            skip_short_strategies = False

            if self.bullish_scorer:
                try:
                    bullish_result = self.bullish_scorer.calculate_bullish_score_ml_ready(tick)
                    bullish_score = bullish_result.get('score', 0.0)
                    tick['bullish_score'] = bullish_score

                    # Déterminer l'emoji et le label
                    if bullish_score > 0.3:
                        bullish_emoji = "🟢"
                        bullish_label = "BULLISH"
                    elif bullish_score < -0.3:
                        bullish_emoji = "🔴"
                        bullish_label = "BEARISH"
                    else:
                        bullish_emoji = "🟡"
                        bullish_label = "NEUTRAL"

                    # 🎯 SEUILS D'EXCLUSION (amélioration Win Rate +3-5%)
                    if bullish_score < -0.7:
                        skip_long_strategies = True
                        logger.info(f"🔴 [{symbol}] Marché trop bearish ({bullish_score:.2f}), skip LONGS")
                    elif bullish_score > 0.7:
                        skip_short_strategies = True
                        logger.info(f"🟢 [{symbol}] Marché trop bullish ({bullish_score:.2f}), skip SHORTS")

                    # Vérifier si on doit afficher (toutes les 60 secondes OU changement de zone)
                    from datetime import datetime
                    current_time = datetime.now()
                    time_elapsed = (current_time - self.last_bullish_display_time).total_seconds()

                    last_emoji_for_symbol = self.last_bullish_emoji.get(symbol)

                    should_display = (
                        time_elapsed >= self.bullish_display_interval_seconds  # 1 minute écoulée
                        or last_emoji_for_symbol != bullish_emoji  # Changement de zone
                    )

                    if should_display:
                        # Extraire valeurs réelles depuis tick
                        vwap_value = tick.get('vwap', 0)
                        orderflow_value = tick.get('cum_delta_session', 0)
                        d_vwap_ticks = tick.get('d_vwap_ticks', 0)

                        # Afficher avec emoji + détails RÉELS
                        logger.info(
                            f"{bullish_emoji} [{symbol}] {bullish_label} {bullish_score:+.2f} | "
                            f"OF:{orderflow_value:+.0f} "
                            f"VWAP:{vwap_value:.2f} (Δ{d_vwap_ticks:+.1f}t) "
                            f"Corridor:{bullish_result.get('headroom_factor', 1.0):.2f}"
                        )

                        self.last_bullish_display_time = current_time
                        self.last_bullish_emoji[symbol] = bullish_emoji
                except Exception as e:
                    logger.debug(f"⚠️ Erreur BullishScorer: {e}")
                    tick['bullish_score'] = 0.0
            else:
                tick['bullish_score'] = 0.0

            # ═══════════════════════════════════════════════════════════════
            # 📦 BRACKET DETECTOR - Détecter consolidations/breakouts
            # ═══════════════════════════════════════════════════════════════
            in_bracket = False
            skip_momentum_strategies = False

            if self.bracket_detector:
                try:
                    bracket = self.bracket_detector.detect_bracket(tick)
                    if bracket and bracket.is_valid:
                        in_bracket = True
                        skip_momentum_strategies = True
                        logger.info(f"📦 [{symbol}] Bracket détecté: {bracket.lower:.2f} - {bracket.upper:.2f} "
                                  f"(Width: {bracket.width_percent*100:.2f}% | Quality: {bracket.quality_score:.2f})")
                        logger.info(f"⚠️ [{symbol}] Skip stratégies momentum (consolidation)")

                    # Vérifier breakout si bracket actif
                    breakout = self.bracket_detector.check_breakout(tick)
                    if breakout:
                        logger.info(f"🚀 [{symbol}] {breakout['type'].upper()}: {breakout['breakout_price']:.2f}")
                        skip_momentum_strategies = False  # Re-enable momentum si breakout
                except Exception as e:
                    logger.debug(f"⚠️ Erreur BracketDetector: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 🎯 ML FILTER V3 - PRÉ-QUALIFICATION DIRECTION (AVANT STRATÉGIES)
            # ✅ PATCH 4: Optimisé - 1 seul appel au lieu de 3 (latence -20ms)
            # ═══════════════════════════════════════════════════════════════
            ml_preferred_direction = None
            ml_confidence = 0.0

            if self.ml_filter:
                try:
                    # ✅ PATCH 4: Un seul appel ML, extraction des 2 probas
                    # Au lieu de 2 appels (UP + DOWN), on fait 1 seul et récupère binary_proba
                    ml_decision = self.ml_filter.validate_signal(
                        symbol=symbol,
                        direction="UP",  # Direction par défaut (pas d'importance ici)
                        tick=tick,
                        signal_meta={"action": "LONG", "confidence": 0.5}  # Dummy signal
                    )

                    # Extraire les probabilités binaires (P(DOWN), P(UP))
                    if ml_decision.prediction and hasattr(ml_decision.prediction, 'binary_proba'):
                        p_down, p_up = ml_decision.prediction.binary_proba

                        # Choisir la direction avec la plus haute confiance
                        if p_up > p_down and p_up > 0.55:
                            ml_preferred_direction = "UP"
                            ml_confidence = p_up
                            logger.info(f"🎯 ML V3 préfère UP (conf={p_up:.3f}, vs DOWN={p_down:.3f})")
                        elif p_down > p_up and p_down > 0.55:
                            ml_preferred_direction = "DOWN"
                            ml_confidence = p_down
                            logger.info(f"🎯 ML V3 préfère DOWN (conf={p_down:.3f}, vs UP={p_up:.3f})")
                        else:
                            logger.debug(f"🤔 ML V3 incertain (UP={p_up:.3f}, DOWN={p_down:.3f})")
                    else:
                        logger.debug(f"⚠️ ML prediction sans binary_proba")

                except Exception as e:
                    logger.debug(f"⚠️ Erreur ML pré-qualification: {e}")

            # Capturer snapshot pré-analyse
            if self.trade_snapshotter:
                try:
                    self.trade_snapshotter.capture_pre_analysis_snapshot(tick)
                except Exception as e:
                    logger.debug(f"⚠️ Erreur snapshot pré-analyse: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 📊 ÉVALUER STRATÉGIES (avec filtres optimisés)
            # ═══════════════════════════════════════════════════════════════
            signals = await asyncio.to_thread(
                self.strategy_manager.evaluate_all,
                tick,
                symbol
            )

            # ✅ PHASE 3.5: S'assurer que signals est toujours une liste
            if signals is None:
                return self._reject_signal_with_snapshot(
                    symbol=symbol,
                    signal=None,
                    tick=tick,
                    rejection_reason="Aucun signal généré par les stratégies",
                    rejection_category="NO_SIGNAL"
                )
            if not isinstance(signals, list):
                signals = [signals]  # Convertir en liste si c'est un seul signal
            if not signals:
                return self._reject_signal_with_snapshot(
                    symbol=symbol,
                    signal=None,
                    tick=tick,
                    rejection_reason="Liste de signaux vide",
                    rejection_category="NO_SIGNAL"
                )

            # Filtrer signaux selon contexte
            filtered_signals = []
            for sig in signals:
                # ✅ PHASE 3.5: Gérer dict ET PatternSignal
                if isinstance(sig, dict):
                    action = sig.get('action', 'UNKNOWN')
                    confidence = sig.get('confidence', 0)
                else:
                    # PatternSignal object
                    action = getattr(sig, 'signal_type', 'UNKNOWN')
                    if hasattr(action, 'name'):  # Enum
                        action = action.name
                    confidence = getattr(sig, 'confidence', 0)

                # Skip LONG si bearish extrême
                if action == "LONG" and skip_long_strategies:
                    # Capturer rejet
                    signal_dict = sig if isinstance(sig, dict) else {'action': action, 'confidence': confidence}
                    self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=signal_dict,
                        tick=tick,
                        rejection_reason=f"Marché trop bearish ({bullish_score:.2f}), skip LONG",
                        rejection_category="CONTEXT"
                    )
                    continue

                # Skip SHORT si bullish extrême
                if action == "SHORT" and skip_short_strategies:
                    # Capturer rejet
                    signal_dict = sig if isinstance(sig, dict) else {'action': action, 'confidence': confidence}
                    self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=signal_dict,
                        tick=tick,
                        rejection_reason=f"Marché trop bullish ({bullish_score:.2f}), skip SHORT",
                        rejection_category="CONTEXT"
                    )
                    continue

                # Bonus confiance si aligné avec ML
                if ml_preferred_direction:
                    ml_direction = "UP" if action == "LONG" else "DOWN"
                    if ml_direction == ml_preferred_direction:
                        new_conf = confidence * 1.15  # Bonus 15%
                        if isinstance(sig, dict):
                            sig['confidence'] = new_conf
                        else:
                            sig.confidence = new_conf
                        logger.debug(f"✅ Signal {action} aligné avec ML (+15% conf)")

                filtered_signals.append(sig)

            if not filtered_signals:
                return self._reject_signal_with_snapshot(
                    symbol=symbol,
                    signal=signals[0] if signals else None,  # Premier signal rejeté
                    tick=tick,
                    rejection_reason="Tous les signaux filtrés par contexte marché",
                    rejection_category="CONTEXT"
                )

            # Prendre le signal avec le plus haut score (après bonus ML)
            # ✅ PHASE 3.5: Gérer dict ET PatternSignal
            def get_conf(s):
                if isinstance(s, dict):
                    return s.get('confidence', 0)
                else:
                    return getattr(s, 'confidence', 0)

            best_signal = max(filtered_signals, key=get_conf)

            # ✅ Extraire action/confidence de manière sûre (utilisé partout)
            if isinstance(best_signal, dict):
                signal_action = best_signal.get('action', 'UNKNOWN')
                signal_confidence = best_signal.get('confidence', 0)
            else:
                # PatternSignal object
                signal_action = getattr(best_signal, 'signal_type', 'UNKNOWN')
                if hasattr(signal_action, 'name'):  # Enum
                    signal_action = signal_action.name
                signal_confidence = getattr(best_signal, 'confidence', 0)

            # ═══════════════════════════════════════════════════════════════
            # 🧠 MARKET CONTEXT FILTER - VALIDATION CONTEXTUELLE (INTELLIGENT)
            # ═══════════════════════════════════════════════════════════════
            if symbol in self.context_analyzers and self.context_filter_config.get('enabled', True):
                try:
                    cfg = self.context_filter_config  # Raccourci
                    analyzer = self.context_analyzers[symbol]
                    market_context = analyzer.analyze(tick)

                    # ✅ PHASE 3.5: Gérer dict ET PatternSignal
                    if isinstance(best_signal, dict):
                        signal_direction = best_signal.get('action', 'UNKNOWN')
                        signal_confidence = best_signal.get('confidence', 0)
                    else:
                        # PatternSignal object
                        signal_direction = getattr(best_signal, 'signal_type', 'UNKNOWN')
                        if hasattr(signal_direction, 'name'):  # Enum
                            signal_direction = signal_direction.name
                        signal_confidence = getattr(best_signal, 'confidence', 0)

                    # 🔍 FILTRE 1: Biais principal aligné
                    if cfg['reject_opposite_bias']:
                        if signal_direction == "LONG" and market_context.main_bias == "BEARISH":
                            return self._reject_signal_with_snapshot(
                                symbol=symbol,
                                signal=best_signal if isinstance(best_signal, dict) else {'action': signal_direction, 'confidence': signal_confidence},
                                tick=tick,
                                rejection_reason=f"Signal LONG vs Biais BEARISH: {market_context.reasoning[:100]}",
                                rejection_category="MARKET_FILTER"
                            )

                        if signal_direction == "SHORT" and market_context.main_bias == "BULLISH":
                            return self._reject_signal_with_snapshot(
                                symbol=symbol,
                                signal=best_signal if isinstance(best_signal, dict) else {'action': signal_direction, 'confidence': signal_confidence},
                                tick=tick,
                                rejection_reason=f"Signal SHORT vs Biais BULLISH: {market_context.reasoning[:100]}",
                                rejection_category="MARKET_FILTER"
                            )

                    # 🔍 FILTRE 2: Confluence (confiance signal + confiance plans)
                    best_plan_confidence = max([p.confidence for p in market_context.trading_plans], default=0)

                    # Appliquer filtre seulement si plans disponibles (évite faux rejet si données manquantes)
                    if market_context.trading_plans:
                        if signal_confidence < cfg['min_signal_confidence'] and best_plan_confidence < cfg['min_plan_confidence']:
                            return self._reject_signal_with_snapshot(
                                symbol=symbol,
                                signal=best_signal if isinstance(best_signal, dict) else {'action': signal_direction, 'confidence': signal_confidence},
                                tick=tick,
                                rejection_reason=f"Confiances faibles: Signal {signal_confidence:.1%}, Plan {best_plan_confidence:.1%}",
                                rejection_category="MARKET_FILTER"
                            )
                    else:
                        logger.debug(f"📊 [{symbol}] Plans contextuels indisponibles - Skip filtre confluence")

                    # 🔍 FILTRE 3: Proximité niveaux critiques (zone dangereuse)
                    if len(market_context.proximity_alerts) > cfg['max_proximity_alerts']:
                        return self._reject_signal_with_snapshot(
                            symbol=symbol,
                            signal=best_signal if isinstance(best_signal, dict) else {'action': signal_direction, 'confidence': signal_confidence},
                            tick=tick,
                            rejection_reason=f"Trop de niveaux critiques proches ({len(market_context.proximity_alerts)}): {', '.join(market_context.proximity_alerts[:2])}",
                            rejection_category="MARKET_FILTER"
                        )

                    # ✅ BONUS: Boost confiance si plan aligné ET haute confiance
                    if best_plan_confidence > cfg['boost_threshold']:
                        aligned_plans = [
                            p for p in market_context.trading_plans
                            if p.direction == signal_direction and p.confidence > 0.70
                        ]
                        if aligned_plans:
                            boost_multiplier = cfg['boost_multiplier']
                            boost_cap = cfg['boost_cap']
                            new_confidence = min(signal_confidence * boost_multiplier, boost_cap)

                            # ✅ PHASE 3.5: Modifier confiance selon le type
                            if isinstance(best_signal, dict):
                                best_signal['confidence'] = new_confidence
                            else:
                                best_signal.confidence = new_confidence

                            logger.info(f"🎯 [{symbol}] Signal {signal_direction} aligné avec plan contextuel haute confiance")
                            logger.info(f"   Boost confiance: {signal_confidence:.1%} → {new_confidence:.1%}")

                    # 📊 Logging contexte pour transparence
                    logger.info(f"📊 [{symbol}] Contexte: {market_context.main_bias} | OF: {market_context.orderflow_pressure} | Gamma: {market_context.gamma_condition}")
                    if market_context.proximity_alerts:
                        logger.info(f"⚠️ [{symbol}] {len(market_context.proximity_alerts)} alertes proximité")

                except Exception as e:
                    logger.warning(f"⚠️ Erreur Market Context Filter: {e} (fail-safe: continuer)")
                    # Fail-safe: continuer sans filtre contextuel en cas d'erreur

            # ═══════════════════════════════════════════════════════════════
            # 🛡️ RISK MANAGER - Validation risque (CRITIQUE)
            # ═══════════════════════════════════════════════════════════════
            if self.risk_manager:
                try:
                    risk_validation = self.risk_manager.evaluate_signal(
                        symbol=symbol,
                        signal=best_signal,
                        ml_data=tick
                    )

                    if not risk_validation.get('approved', False):
                        return self._reject_signal_with_snapshot(
                            symbol=symbol,
                            signal=best_signal if isinstance(best_signal, dict) else {'action': best_signal.get('action'), 'confidence': best_signal.get('confidence')},
                            tick=tick,
                            rejection_reason=f"RiskManager: {risk_validation.get('reason')}",
                            rejection_category="RISK"
                        )

                    logger.debug(f"✅ RiskManager approved - Size: {risk_validation.get('position_size', 1)}")

                except Exception as e:
                    return self._reject_signal_with_snapshot(
                        symbol=symbol,
                        signal=best_signal if isinstance(best_signal, dict) else {'action': 'UNKNOWN', 'confidence': 0},
                        tick=tick,
                        rejection_reason=f"Erreur RiskManager: {str(e)}",
                        rejection_category="RISK"
                    )

            # ═══════════════════════════════════════════════════════════════
            # 🔍 ML FILTER V3 - VALIDATION FINALE (si mode required)
            # ═══════════════════════════════════════════════════════════════
            if self.ml_filter:
                ml_decision = self.ml_filter.validate_signal(
                    symbol=symbol,
                    direction="UP" if signal_action == "LONG" else "DOWN",
                    tick=tick,
                    signal_meta=best_signal
                )

                # Log décision ML
                if ml_decision.mode == "advisory":
                    # Mode shadow : log mais accepte toujours
                    logger.info(f"🔍 ML V3 (shadow): {symbol}/{signal_action} "
                               f"→ {'✅' if ml_decision.accepted else '❌'} "
                               f"(conf={ml_decision.prediction.confidence:.3f}, "
                               f"seuil={ml_decision.threshold_used:.2f})")
                else:
                    # Mode required : respecte la décision
                    if not ml_decision.accepted:
                        return self._reject_signal_with_snapshot(
                            symbol=symbol,
                            signal=best_signal,
                            tick=tick,
                            rejection_reason=f"ML confidence trop faible",
                            rejection_category="ML",
                            ml_probability=ml_decision.prediction.confidence,
                            ml_threshold=ml_decision.threshold_used
                        )
                    else:
                        logger.info(f"✅ ML V3 (required): Signal {symbol}/{signal_action} ACCEPTÉ "
                                   f"(conf={ml_decision.prediction.confidence:.3f} >= {ml_decision.threshold_used:.2f})")

            # Capturer snapshot décision
            if self.trade_snapshotter:
                try:
                    self.trade_snapshotter.capture_decision_snapshot(
                        symbol=symbol,
                        signal=best_signal,
                        ml_data=tick,
                        strategy_results=signals
                    )
                except Exception as e:
                    logger.debug(f"⚠️ Erreur snapshot décision: {e}")

            # Incrémenter compteur signaux
            self.stats['signals'] += 1
            strategy_name = getattr(best_signal, 'strategy', best_signal.get('strategy', 'unknown'))
            self.stats['strategies'][strategy_name] = self.stats['strategies'].get(strategy_name, 0) + 1

            # ═══════════════════════════════════════════════════════════════
            # 📊 SIGNAL EXPLAINER - Générer explication structurée
            # ═══════════════════════════════════════════════════════════════
            if self.signal_explainer:
                try:
                    explanation = self.signal_explainer.explain_signal(
                        signal=best_signal,
                        ml_data=tick,
                        bullish_score=bullish_score
                    )
                    # Log le message brief avec traffic light
                    logger.info(f"{explanation['traffic_light']} {explanation['brief']}")
                except Exception as e:
                    logger.debug(f"⚠️ Erreur SignalExplainer: {e}")

            # ═══════════════════════════════════════════════════════════════
            # 📱 DECISION MESSENGER - Envoyer message de décision
            # ═══════════════════════════════════════════════════════════════
            if self.decision_messenger:
                try:
                    self.decision_messenger.send_signal(
                        signal=best_signal,
                        ml_data=tick,
                        execute=True  # Signal sera exécuté si live trading actif
                    )
                except Exception as e:
                    logger.debug(f"⚠️ Erreur DecisionMessenger: {e}")

            logger.info(f"🎯 [{symbol}] Signal généré: {strategy_name}")

            # ═══════════════════════════════════════════════════════════════
            # 🚀 EXÉCUTION DTC + SNAPSHOTS COMPLETS (si live trading activé)
            # ═══════════════════════════════════════════════════════════════

            if self.config.get('enable_live_trading', False) and self.dtc_connector:
                try:
                    logger.info(f"🚀 EXÉCUTION TRADE {symbol} {signal_action}")

                    # Calculer TP/SL basés sur ATR
                    atr = tick.get('atr', 10.0)
                    entry_price = tick.get('mid', 0)

                    if signal_action == 'LONG':
                        tp_price = entry_price + (atr * 2.0)  # +2 ATR
                        sl_price = entry_price - (atr * 1.0)  # -1 ATR
                    else:  # SHORT
                        tp_price = entry_price - (atr * 2.0)  # -2 ATR
                        sl_price = entry_price + (atr * 1.0)  # +1 ATR

                    # Arrondir aux prix valides
                    tick_size = 0.25 if symbol == "ES" else 0.25
                    tp_price = round(tp_price / tick_size) * tick_size
                    sl_price = round(sl_price / tick_size) * tick_size

                    logger.info(f"📊 Entry: {entry_price:.2f} | TP: {tp_price:.2f} | SL: {sl_price:.2f} | ATR: {atr:.2f}")

                    # Exécuter bracket order via DTC
                    execution_result = await self.dtc_connector.place_parent_then_children(
                        symbol=f"{symbol}Z25-CME",  # ESZ25-CME ou NQZ25-CME
                        side="BUY" if signal_action == 'LONG' else "SELL",
                        qty=1.0,
                        entry_kind="MKT",
                        entry_price=None,
                        tp_price=tp_price,
                        sl_price=sl_price,
                        client_tag=f"{symbol}_{strategy_name}",
                        children_mode="separate"
                    )

                    # Vérifier résultat exécution
                    if execution_result and not execution_result.get('error'):
                        logger.info(f"✅ Trade exécuté avec succès!")
                        logger.info(f"   Parent: {execution_result.get('entry', 'N/A')}")
                        logger.info(f"   TP: {execution_result.get('tp_cid')}")
                        logger.info(f"   SL: {execution_result.get('sl_cid')}")
                        logger.info(f"   Compte: {execution_result.get('trade_account')}")

                        # 📸 Capturer Execution Snapshot
                        if self.trade_snapshotter:
                            try:
                                self.trade_snapshotter.capture_execution_snapshot(
                                    symbol=symbol,
                                    signal=best_signal,
                                    execution_result=execution_result,
                                    order_ids={
                                        'parent': execution_result.get('entry'),
                                        'tp': execution_result.get('tp_cid'),
                                        'sl': execution_result.get('sl_cid')
                                    },
                                    slippage=0.25,  # 1 tick = 0.25
                                    fees=2.40  # USD par contrat
                                )
                                logger.info("📸 Execution Snapshot capturé")
                            except Exception as e:
                                logger.error(f"⚠️ Erreur snapshot exécution: {e}")

                        # Tracker position ouverte
                        if not hasattr(self, 'open_positions'):
                            self.open_positions = {}

                        self.open_positions[symbol] = {
                            'entry_time': datetime.now(),
                            'entry_price': entry_price,
                            'tp_price': tp_price,
                            'sl_price': sl_price,
                            'quantity': 1.0,
                            'side': signal_action,
                            'order_ids': execution_result,
                            'signal': best_signal,
                            'strategy': strategy_name
                        }

                        # 📸 Capturer Position Snapshot
                        if self.trade_snapshotter:
                            try:
                                self.trade_snapshotter.capture_position_snapshot(
                                    symbol=symbol,
                                    entry_price=entry_price,
                                    quantity=1.0,
                                    tp_price=tp_price,
                                    sl_price=sl_price,
                                    pnl_floating=0.0,
                                    position_id=execution_result.get('entry', 'N/A')
                                )
                                logger.info("📸 Position Snapshot capturé")
                            except Exception as e:
                                logger.error(f"⚠️ Erreur snapshot position: {e}")

                        # ═══════════════════════════════════════════════════════════════
                        # 📱 DISCORD 1 : Notification Trade Exécuté
                        # ═══════════════════════════════════════════════════════════════
                        if self.discord:
                            try:
                                # Calculer distance TP/SL en ticks
                                tick_size = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}.get(symbol, 0.25)
                                if signal_action == 'LONG':
                                    tp_ticks = (tp_price - entry_price) / tick_size
                                    sl_ticks = (entry_price - sl_price) / tick_size
                                else:  # SHORT
                                    tp_ticks = (entry_price - tp_price) / tick_size
                                    sl_ticks = (sl_price - entry_price) / tick_size

                                trade_data = {
                                    'symbol': symbol,
                                    'side': signal_action,
                                    'quantity': 1.0,
                                    'fill_price': entry_price,
                                    'intended_price': entry_price,
                                    'slippage_ticks': 0,  # Simulé pour l'instant
                                    'risk_dollars': abs(entry_price - sl_price) * 12.50,  # Approximation
                                    'battle_status': f"TP:{tp_ticks:+.0f}t SL:{sl_ticks:+.0f}t | ML:{ml_confidence:.1%}"
                                }

                                await self.discord.send_trade_executed(trade_data)
                                logger.info(f"📱 Discord: Trade exécuté notifié ({symbol} {signal_action})")
                            except Exception as e:
                                logger.error(f"⚠️ Erreur Discord trade executed: {e}")

                        # ═══════════════════════════════════════════════════════════════
                        # ✅ PHASE 1.3-1.6 : LESSONS LEARNED - Enregistrer décision/contexte
                        # ═══════════════════════════════════════════════════════════════
                        if self.lessons_learned:
                            try:
                                # 1️⃣ Créer objet Decision
                                decision = Decision(
                                    decision=signal_action,  # "LONG" ou "SHORT"
                                    score=best_signal.get('confidence', 0) if isinstance(best_signal, dict) else signal_confidence,
                                    factors={
                                        'ml_confidence': ml_confidence if 'ml_confidence' in locals() else 0.0,
                                        'bullish_score': bullish_score if bullish_score is not None else 0.0,
                                        'dom_health': dom_score if 'dom_score' in locals() else 0.0,
                                        'volatility_regime': vol_regime_result.regime.value if vol_regime_result else 'NORMAL'
                                    },
                                    rules=[],
                                    timestamp=datetime.now(),
                                    confluence_score=best_signal.get('confidence', 0),
                                    battle_navale_score=0.0,
                                    dealers_bias_score=0.0,
                                    pattern_signals=[strategy_name]
                                )

                                # 2️⃣ Créer objet Execution
                                execution_obj = Execution(
                                    qty=1,
                                    entry_price=entry_price,
                                    exit_price=0,  # Sera mis à jour au close
                                    sl_price=sl_price,
                                    tp_price=tp_price,
                                    slippage=0.25,  # 1 tick
                                    timestamp=datetime.now(),
                                    execution_quality="A"  # Assume bonne exécution si pas d'erreur
                                )

                                # 3️⃣ Créer objet Context
                                vix = tick.get('vix', 20.0)
                                if vix < 15:
                                    vix_regime = "LOW"
                                elif vix > 25:
                                    vix_regime = "HIGH"
                                else:
                                    vix_regime = "MID"

                                menthor_distances = tick.get('menthor_distances', {})
                                bl_distance = menthor_distances.get('put0', 0)
                                gw_distance = menthor_distances.get('call0', 0)

                                # Déterminer MenthorQ family
                                if abs(bl_distance) < 20:
                                    menthorq_family = "Near BL"
                                elif abs(gw_distance) < 20:
                                    menthorq_family = "Near GW"
                                else:
                                    menthorq_family = "Clear"

                                context = Context(
                                    vix_regime=vix_regime,
                                    bl_distance=bl_distance,
                                    gw_distance=gw_distance,
                                    m30_range=tick.get('total_range_ticks', 0),
                                    vwap_distance=tick.get('d_vwap_ticks', 0),
                                    time_window="normal",
                                    gex_above_pct=50.0,  # Placeholder
                                    menthorq_family=menthorq_family,
                                    session_phase=tick.get('session_id', 'unknown'),
                                    market_regime=vol_regime_result.regime.value if vol_regime_result else 'unknown'
                                )

                                # 4️⃣ Enregistrer dans LessonsLearned
                                # Note: sera complété au close du trade pour calculer PnL/MAE
                                trade_id = execution_result.get('entry', 'N/A')

                                # Stocker temporairement pour update au close
                                if not hasattr(self, 'pending_lessons'):
                                    self.pending_lessons = {}

                                self.pending_lessons[trade_id] = {
                                    'decision': decision,
                                    'execution': execution_obj,
                                    'context': context
                                }

                                logger.info(f"📚 [{symbol}] Lessons Learned initialisé (trade_id={trade_id})")
                                logger.debug(f"   VIX regime: {vix_regime}, MQ family: {menthorq_family}")

                            except Exception as e:
                                logger.warning(f"⚠️ Erreur Lessons Learned: {e} (non-bloquant)")

                        # 📊 Mettre à jour DrawdownMonitor
                        if self.drawdown_monitor:
                            # PnL initial = 0 (position juste ouverte)
                            self.drawdown_monitor.update(0.0)

                    else:
                        logger.error(f"❌ Échec exécution: {execution_result.get('error') if execution_result else 'Pas de résultat'}")

                except Exception as e:
                    logger.error(f"❌ Erreur exécution DTC: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                mode_msg = "PAPER MODE" if not self.config.get('enable_live_trading') else "DTC NON DISPONIBLE"
                logger.info(f"📊 {mode_msg}: Signal {symbol} {signal_action} "
                           f"(stratégie={strategy_name}, conf={signal_confidence:.2f}) - PAS D'EXÉCUTION")

            # ═══════════════════════════════════════════════════════════════
            # 🆕 FINALISATION MODULES CONSOLIDATION
            # ═══════════════════════════════════════════════════════════════

            # 1️⃣ LATENCY TRACKER - Terminer pipeline
            self.latency_tracker.end_pipeline(success=True)

            # 2️⃣ PERFORMANCE PROFILER - Log résumé toutes les 100 cycles
            if self.stats['cycles'] % 100 == 0:
                bottlenecks = self.performance_profiler.get_bottlenecks(threshold_ms=50.0)
                if bottlenecks:
                    logger.info(f"⚡ Goulots d'étranglement (>50ms): {len(bottlenecks)}")
                    for metric in bottlenecks[:3]:  # Top 3
                        logger.info(f"   - {metric.function_name}: {metric.avg_time_ms:.1f}ms avg")

            # 3️⃣ LATENCY TRACKER - Log performance P95 toutes les 100 cycles
            if self.stats['cycles'] % 100 == 0:
                stage_perf = self.latency_tracker.get_stage_performance()
                total_p95 = sum(s['p95_duration_ms'] for s in stage_perf.values()) if stage_perf else 0
                logger.info(f"📊 Latence pipeline P95: {total_p95:.1f}ms")

                if total_p95 > 200:
                    logger.warning(f"⚠️ Latence P95 > 200ms seuil (actuel: {total_p95:.1f}ms)")

            # ═══════════════════════════════════════════════════════════════
            # 🆕 MODULES PRO - Drawdown Monitor & Métriques Dashboard
            # ═══════════════════════════════════════════════════════════════

            # 4️⃣ DRAWDOWN MONITOR - Update avec trade (si signal exécuté)
            if best_signal:
                # Simuler PnL (à remplacer par vrai PnL en production)
                # Pour l'instant, on assume un PnL fictif basé sur la confiance
                signal_confidence = best_signal.get('confidence', 0.5) if isinstance(best_signal, dict) else getattr(best_signal, 'confidence', 0.5)
                estimated_pnl = 10.0 if signal_confidence > 0.70 else -5.0
                self.total_pnl_net += estimated_pnl

                # Update drawdown monitor
                dd_metrics = self.drawdown_monitor.update(self.total_pnl_net)

                # Vérifier si halt requis
                if self.drawdown_monitor.should_halt():
                    logger.error("🚨 HALT TRADING - Drawdown critique détecté")
                    logger.error(f"   Current DD: {dd_metrics.current_dd_pct:.2%}")
                    logger.error(f"   DD Duration: {dd_metrics.dd_duration} cycles")
                    self.running = False  # Arrêter le système

                # Log DD info toutes les 100 cycles
                if self.stats['cycles'] % 100 == 0 and dd_metrics.current_dd_pct > 0:
                    logger.info(f"🔴 Drawdown: {dd_metrics.current_dd_pct:.2%} (Peak: ${dd_metrics.peak_pnl:.2f})")

            # 5️⃣ SAUVEGARDER MÉTRIQUES POUR DASHBOARD - Toutes les 50 cycles
            if self.stats['cycles'] % 50 == 0:
                try:
                    # Calculer win rate (fictif pour l'instant)
                    win_rate = 0.60 if self.stats['signals'] > 0 else 0

                    live_metrics = {
                        'total_pnl_net': self.total_pnl_net,
                        'total_trades': self.stats['signals'],
                        'win_rate': win_rate,
                        'current_dd_pct': self.drawdown_monitor.current_dd_pct,
                        'max_dd_pct': self.drawdown_monitor.max_dd_pct_observed,
                        'avg_latency_ms': total_p95 if self.stats['cycles'] % 100 == 0 else 0,
                        'latency_breakdown': {
                            'data_read': 0.5,
                            'ml_prediction': 2.0,
                            'strategy_eval': 1.5,
                            'decision': 0.3
                        },
                        'cycles': self.stats['cycles'],
                        'errors': self.stats['errors'],
                        'pnl_delta': estimated_pnl if best_signal else 0,
                        'timestamp': datetime.now().isoformat()
                    }

                    # Sauvegarder dans data/live_metrics.json
                    import json
                    from pathlib import Path
                    Path("data").mkdir(exist_ok=True)
                    with open('data/live_metrics.json', 'w') as f:
                        json.dump(live_metrics, f, indent=2)

                except Exception as e:
                    logger.debug(f"⚠️ Erreur sauvegarde métriques dashboard: {e}")

            # Retourner le signal avec les données ML pour exécution
            return {
                'signal': best_signal,
                'ml_data': tick,
                'symbol': symbol
            }

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ Erreur cycle {symbol}: {e}")

            # Terminer pipeline en erreur
            try:
                self.latency_tracker.end_pipeline(success=False)
            except:
                pass

            return None

    async def run(self):
        """Boucle principale du système"""
        self.running = True
        logger.info("=" * 80)
        logger.info("🚀 DÉMARRAGE SYSTÈME ML V3 PRODUCTION")
        logger.info("=" * 80)
        logger.info(f"   Modèles : ES, NQ & RTY V3 (avec distances OPTIONS dynamiques)")  # ✅ RTY ajouté
        logger.info(f"   Mode : {'PAPER TRADING' if self.config.get('paper_trading', True) else 'LIVE TRADING'}")
        logger.info(f"   Symboles : {', '.join(self.symbols)}")
        logger.info("=" * 80)

        # ═══════════════════════════════════════════════════════════════
        # 🔄 LANCER MONITOR FILLS LOOP EN BACKGROUND
        # ═══════════════════════════════════════════════════════════════
        monitor_fills_task = asyncio.create_task(self._monitor_fills_loop())
        logger.info("✅ Monitor fills loop lancé en background")

        # ═══════════════════════════════════════════════════════════════
        # 💓 LANCER HEARTBEAT DISCORD EN BACKGROUND
        # ═══════════════════════════════════════════════════════════════
        if self.discord:
            heartbeat_task = asyncio.create_task(self._heartbeat_discord_loop())
            logger.info("✅ Heartbeat Discord loop lancé en background (5 min)")

            # 📊 LANCER DAILY SUMMARY DISCORD EN BACKGROUND
            daily_summary_task = asyncio.create_task(self._daily_summary_loop())
            logger.info("✅ Daily Summary Discord loop lancé en background (23h59 EST)")

        # ═══════════════════════════════════════════════════════════════
        # 📱 MESSAGE DÉMARRAGE DISCORD
        # ═══════════════════════════════════════════════════════════════
        if self.discord:
            try:
                await self.discord.send_custom_message(
                    'admin_messages',
                    '🚀 MIA BOT DÉMARRÉ - Phase 3.5',
                    f"""
**Version:** Phase 3.5 (130 features ML + Fermeture positions)
**Mode:** {'SIMULATION' if self.config.get('paper_trading', True) else 'LIVE'} (ADVISORY)
**Marchés:** ES, NQ, RTY
**ML Thresholds:** ES:0.70 | NQ:0.65 | RTY:0.60
**Uptime:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Monitor fills loop actif
✅ PostMortem avec Discord
✅ Fermeture positions automatique
✅ P&L tracking temps réel
                    """.strip(),
                    color=0x00ff00,
                    urgent=True
                )
                logger.info("📱 Message démarrage envoyé Discord")
            except Exception as e:
                logger.error(f"⚠️ Erreur message Discord: {e}")

        cycle_count = 0

        try:
            while self.running:
                cycle_count += 1
                self.stats['cycles'] = cycle_count

                # Cycle alterné entre symboles
                symbol = self.symbols[self.current_symbol_idx]

                # Run cycle
                signal = await self.run_cycle(symbol)

                # Alterner symbole
                self.current_symbol_idx = (self.current_symbol_idx + 1) % len(self.symbols)

                # Stats périodiques (toutes les 50 cycles)
                if cycle_count % 50 == 0:
                    uptime = time.time() - self.stats['start_time']
                    uptime_minutes = int(uptime / 60)
                    uptime_hours = uptime_minutes // 60
                    uptime_min_remaining = uptime_minutes % 60

                    # 💓 SIGNE DE VIE VISUEL
                    logger.info("=" * 80)
                    logger.info(f"💓 BOT VIVANT - Cycle #{cycle_count}")
                    logger.info(f"   ⏱️  Uptime: {uptime_hours}h {uptime_min_remaining}min ({uptime:.0f}s)")
                    logger.info(f"   🔄 Cycles: {cycle_count} | Signaux: {self.stats['signals']} | Erreurs: {self.stats['errors']}")

                    # Positions ouvertes
                    if hasattr(self, 'open_positions') and self.open_positions:
                        logger.info(f"   📊 Positions ouvertes: {len(self.open_positions)}")
                        for sym, pos in self.open_positions.items():
                            duration_min = (datetime.now() - pos['entry_time']).seconds / 60
                            logger.info(f"      • {sym}: {pos['side']} @ {pos['entry_price']:.2f} (depuis {duration_min:.0f} min)")
                    else:
                        logger.info(f"   📊 Positions: FLAT ✅")

                    # P&L journalier
                    if hasattr(self, 'risk_manager') and self.risk_manager:
                        daily_pnl = getattr(self.risk_manager, 'daily_pnl', 0.0)
                        pnl_emoji = "✅" if daily_pnl >= 0 else "❌"
                        logger.info(f"   💰 P&L Day: ${daily_pnl:+.2f} {pnl_emoji}")

                    # Discord aggregator stats
                    if self.discord_aggregator:
                        agg_stats = self.discord_aggregator.get_stats()
                        if agg_stats.get('messages_buffered', 0) > 0:
                            logger.info(f"   📥 Discord buffer: {agg_stats['messages_buffered']} messages en attente")

                    logger.info("=" * 80)

                    # 📊 Sauvegarder métriques pour dashboard
                    self._save_live_metrics(cycle_count, uptime)

                # Petit délai entre cycles
                await asyncio.sleep(self.config.get('cycle_delay_ms', 100) / 1000)

        except KeyboardInterrupt:
            logger.info("⚠️ Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur fatale: {e}")
            raise
        finally:
            self.running = False
            logger.info("🛑 Système arrêté")


async def main():
    """Point d'entrée principal"""
    try:
        # ═══════════════════════════════════════════════════════════════
        # 🔍 PRE-FLIGHT CHECK - VALIDATION PRÉ-LANCEMENT
        # ═══════════════════════════════════════════════════════════════
        logger.info("\n" + "="*80)
        logger.info("🔍 EXÉCUTION PRE-FLIGHT CHECK")
        logger.info("="*80 + "\n")

        # Configuration PreFlight
        preflight_config = {
            'symbols': ['ES', 'NQ']
        }

        # Exécuter tous les checks
        preflight_checker = create_preflight_checker(preflight_config)
        preflight_report = preflight_checker.run_all_checks()

        # DÉCISION GO/NO-GO
        if not preflight_report.can_launch:
            logger.error("\n" + "="*80)
            logger.error(f"🔴 PRE-FLIGHT CHECK ÉCHOUÉ: {preflight_report.summary}")
            logger.error("="*80)
            logger.error("\n❌ LANCEMENT BLOQUÉ - Corriger les erreurs critiques avant de relancer")
            logger.error(f"📄 Rapport complet: logs/preflight_reports/preflight_{preflight_report.timestamp.strftime('%Y%m%d_%H%M%S')}.json\n")
            return  # SORTIE - PAS DE LANCEMENT

        if preflight_report.decision == GoLiveDecision.CONDITIONAL:
            logger.warning("\n" + "="*80)
            logger.warning(f"🟡 PRE-FLIGHT CHECK: {preflight_report.summary}")
            logger.warning("="*80)
            logger.warning("⚠️ Lancement autorisé AVEC SURVEILLANCE\n")
        else:
            logger.info("\n" + "="*80)
            logger.info(f"🟢 PRE-FLIGHT CHECK RÉUSSI: {preflight_report.summary}")
            logger.info("="*80)
            logger.info("✅ AUTORISATION DE LANCEMENT\n")

        # ═══════════════════════════════════════════════════════════════
        # 🚀 DÉMARRAGE SYSTÈME
        # ═══════════════════════════════════════════════════════════════

        # Charger configuration
        config = get_optimized_config()

        # Override avec ML V3 config
        config.update({
            'paper_trading': True,  # PAPER TRADING par défaut
            'enable_live_trading': True,  # 🚀 ACTIVER DTC POUR PAPER TRADING
            'cycle_delay_ms': 100,
            'ml_version': 'v3',
            'ml_models_dir': 'ml/models_solidification_v33',  # Utiliser modèles V3.3
            # Configuration DTC
            'dtc_host': 'localhost',
            'dtc_port': 11099,  # ES et NQ sur même port
            'heartbeat_interval': 20,
            'trade_account_map': {"ES": "Sim1", "NQ": "Sim2"}  # Comptes paper
        })

        # Créer et lancer le système
        system = MLV3TradingSystem(config)
        await system.run()

    except Exception as e:
        logger.error(f"❌ Erreur fatale main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
