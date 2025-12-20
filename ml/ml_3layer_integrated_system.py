"""
Wrapper d'intégration ML 3-Layer + Hard Rules + Market Context + ML Predictors

Combine:
- ML3LayerFilter (MenthorQ 50% + OrderFlow 30% + Context 20%)
- MenthorQ Execution Rules (Hard Rules)
- MarketContextAnalyzer (Contexte macro)
- LightGBM Predictors (Quality Score + WIN/LOSS Classifier)

Version: 2.0
Date: 2025-11-16
"""

import logging
from typing import Dict, Optional, Any
from pathlib import Path

from ml.ml_3layer_filter import ML3LayerFilter, TradeDecision, TradeSignal
from ml.ml_mia_qscore import MIAQScore  # ✅ NOUVEAU 21/11 05:15: Q-Score MIA
from core.menthorq_execution_rules import evaluate_execution_rules
from core.market_context_analyzer import MarketContextAnalyzer
from config.ml_3layer_integration_config import (
    CONFIG_3LAYER,
    CONFIG_HARD_RULES,
    CONFIG_MARKET_CONTEXT,
    MODEL_PATHS_3LAYER
)

# ═══════════════════════════════════════════════════════════════
# ✅ NOUVEAUX IMPORTS: ML PREDICTORS (16/11/2025)
# ═══════════════════════════════════════════════════════════════
from ml.lightgbm_predictor import LightGBMPredictor

# Import du classifier - chemin corrigé
try:
    # Python n'aime pas les dossiers qui commencent par des chiffres dans les imports
    # Solution: import dynamique
    import importlib
    import sys
    classifier_module = importlib.import_module('ml.5_PREDICTION.lightgbm_classifier_predictor')
    LightGBMClassifierPredictor = classifier_module.LightGBMClassifierPredictor
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️  LightGBMClassifierPredictor non disponible: {e}")
    LightGBMClassifierPredictor = None

logger = logging.getLogger(__name__)


class ML3LayerIntegratedSystem:
    """
    Système intégré: 3-Layer Filter + Hard Rules + Market Context + ML Predictors

    Pipeline (15/11/2025):
        1. Market Context (pré-filtre)
        2. ML 3-Layer Filter (rules-based)
        3. ML Quality Score Predictor (LightGBM) ← NOUVEAU
        4. ML WIN/LOSS Classifier (LightGBM) ← NOUVEAU
        5. Market Context (post-validation)
        6. MenthorQ Hard Rules
        7. Position Sizing
    """

    def __init__(self, symbols=["ES", "NQ", "RTY"], config: Optional[Dict] = None, use_ml_models: bool = True):
        """
        Initialise le système intégré

        Args:
            symbols: Liste des symboles à trader
            config: Configuration personnalisée (optionnel)
            use_ml_models: Si True, active les prédicteurs ML (quality_score, win/loss)
        """
        self.symbols = symbols
        self.config = config or CONFIG_3LAYER
        self.use_ml_models = use_ml_models

        logger.info("=" * 80)
        logger.info("🚀 INITIALISATION ML 3-LAYER INTEGRATED SYSTEM v2.0")
        logger.info("=" * 80)

        # === 1. ML 3-LAYER FILTER ===
        try:
            self.ml_3layer = ML3LayerFilter()
            logger.info("✅ ML3LayerFilter initialisé (MenthorQ 50% + OrderFlow 30% + Context 20%)")
        except Exception as e:
            logger.error(f"❌ Erreur ML3LayerFilter: {e}")
            self.ml_3layer = None

        # === 2. MARKET CONTEXT ANALYZERS ===
        self.market_context_analyzers = {}
        for symbol in symbols:
            try:
                self.market_context_analyzers[symbol] = MarketContextAnalyzer(symbol=symbol)
            except Exception as e:
                logger.error(f"❌ Erreur MarketContextAnalyzer [{symbol}]: {e}")

        logger.info(f"✅ MarketContextAnalyzer initialisés ({len(self.market_context_analyzers)} symboles)")

        # ═══════════════════════════════════════════════════════════════
        # ✅ NOUVEAUTÉ 15/11/2025: ML PREDICTORS
        # ═══════════════════════════════════════════════════════════════

        self.quality_predictor = None
        self.win_loss_classifier = None

        if self.use_ml_models:
            # Quality Score Predictor (0-100)
            try:
                quality_model_path = "ml/models/lightgbm_quality_v1.pkl"
                if Path(quality_model_path).exists():
                    self.quality_predictor = LightGBMPredictor.load(quality_model_path)
                    logger.info(f"✅ Quality Score Predictor chargé: {quality_model_path}")
                    logger.info(f"   Features: {len(self.quality_predictor.feature_names)}")
                else:
                    logger.warning(f"⚠️  Quality model non trouvé: {quality_model_path}")
            except Exception as e:
                logger.error(f"❌ Erreur chargement Quality Predictor: {e}")

            # WIN/LOSS Classifier (seuil optimal 0.45)
            try:
                classifier_model_path = "ml/models/lightgbm_t1_binary_simple.pkl"
                if Path(classifier_model_path).exists() and LightGBMClassifierPredictor is not None:
                    self.win_loss_classifier = LightGBMClassifierPredictor(
                        model_path=classifier_model_path,
                        threshold=0.30  # 🔧 TEST: Réduit de 0.45 → 0.30 pour permettre plus de trades
                    )
                    logger.info(f"✅ WIN/LOSS Classifier chargé: {classifier_model_path}")
                    logger.info(f"   Seuil décision optimal: 0.45 (F1: 65.5%)")
                else:
                    logger.warning(f"⚠️  Classifier model non trouvé ou classe non disponible: {classifier_model_path}")
            except Exception as e:
                logger.error(f"❌ Erreur chargement WIN/LOSS Classifier: {e}")

            logger.info(f"🧠 ML MODELS: {'ACTIVÉS' if (self.quality_predictor or self.win_loss_classifier) else 'DÉSACTIVÉS (fallback rules)'}")
        else:
            logger.info("🔧 ML MODELS: DÉSACTIVÉS (mode rules-only)")

        # === 3. STATISTIQUES ===
        self.stats = {
            'total_evaluations': 0,
            'layer1_rejections': 0,
            'layer2_rejections': 0,
            'layer3_rejections': 0,
            'context_prefilter_rejections': 0,
            'context_postfilter_rejections': 0,
            'hard_rules_rejections': 0,
            'ml_quality_rejections': 0,  # ← NOUVEAU
            'ml_winloss_rejections': 0,  # ← NOUVEAU
            'qscore_rejections': 0,  # ← NOUVEAU 23/11: Filtre Q-Score
            'trades_executed': 0
        }

        logger.info("=" * 80)

    def evaluate_signal(self, snapshot: Dict, symbol: str) -> Optional[Dict]:
        """
        Évalue un signal complet avec tous les filtres

        Args:
            snapshot: Snapshot ML_READY
            symbol: Symbole (ES, NQ, RTY)

        Returns:
            Dict avec décision finale ou None si rejeté
            {
                'action': 'LONG'|'SHORT',
                'confidence': 0.0-1.0,
                'size_multiplier': 0.0-1.0,
                'layer1_confidence': float,
                'layer2_confidence': float,
                'layer3_confidence': float,
                'market_context': MarketContext,
                'hard_rules_result': ExecutionRulesResult,
                'should_trade': bool,
                'rejection_reason': Optional[str]
            }
        """
        # ✅ DEBUG 17/11: Logger l'appel pour ES
        if symbol == 'ES':
            logger.info(f"🔍 [ES DEBUG] ml_3layer_integrated_system.evaluate_signal() appelé")
            logger.info(f"🔍 [ES DEBUG] ML 3-Layer disponible: {self.ml_3layer is not None}")
            logger.info(f"🔍 [ES DEBUG] Snapshot keys: {list(snapshot.keys())[:10]}...")

        self.stats['total_evaluations'] += 1

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 1: PRÉ-FILTRE MARKET CONTEXT
        # ═══════════════════════════════════════════════════════════════════

        market_context = None
        if CONFIG_MARKET_CONTEXT['enabled']:
            try:
                analyzer = self.market_context_analyzers.get(symbol)
                if analyzer:
                    market_context = analyzer.analyze(snapshot, symbol)

                    # Pré-filtre: Quality score
                    if market_context.quality_score < CONFIG_MARKET_CONTEXT['prefilter']['min_quality_score']:
                        self.stats['context_prefilter_rejections'] += 1
                        logger.warning(
                            f"❌ [{symbol}] PRÉ-FILTRE: Quality score trop faible "
                            f"({market_context.quality_score:.2f} < "
                            f"{CONFIG_MARKET_CONTEXT['prefilter']['min_quality_score']:.2f})"
                        )
                        return {
                            'should_trade': False,
                            'rejection_reason': 'Market Context: Quality score insufficient',
                            'market_context': market_context
                        }

                    # Pré-filtre: Trop d'alertes proximité
                    num_alerts = len(market_context.proximity_alerts)
                    max_alerts = CONFIG_MARKET_CONTEXT['prefilter']['max_proximity_alerts']
                    if num_alerts > max_alerts:
                        self.stats['context_prefilter_rejections'] += 1
                        logger.warning(
                            f"❌ [{symbol}] PRÉ-FILTRE: Trop d'alertes proximité "
                            f"({num_alerts} > {max_alerts})"
                        )
                        return {
                            'should_trade': False,
                            'rejection_reason': f'Market Context: {num_alerts} proximity alerts',
                            'market_context': market_context
                        }

                    logger.info(
                        f"✅ [{symbol}] PRÉ-FILTRE OK: Quality={market_context.quality_score:.2f}, "
                        f"Bias={market_context.main_bias}"
                    )
            except Exception as e:
                logger.error(f"⚠️ Erreur Market Context pré-filtre: {e}")

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 2: ML 3-LAYER FILTER
        # ═══════════════════════════════════════════════════════════════════

        if not self.ml_3layer:
            logger.error("❌ ML3LayerFilter non disponible")
            return {
                'should_trade': False,
                'rejection_reason': 'ML3LayerFilter not available'
            }

        # ✅ DEBUG 17/11: Logger pour ES avant l'évaluation ML 3-Layer
        if symbol == 'ES':
            logger.info(f"🔍 [ES DEBUG] Appel ml_3layer.evaluate_trade()...")
            logger.info(f"🔍 [ES DEBUG] ml_3layer disponible: {self.ml_3layer is not None}")

        decision = self.ml_3layer.evaluate_trade(snapshot)

        # ✅ DEBUG 17/11: Logger pour ES après l'évaluation
        if symbol == 'ES':
            if decision:
                logger.info(f"🔍 [ES DEBUG] ml_3layer.evaluate_trade() a retourné: should_trade={decision.should_trade}, action={getattr(decision, 'action', 'N/A')}, confidence={getattr(decision, 'total_confidence', 0):.3f}")
                if not decision.should_trade:
                    logger.warning(f"🔍 [ES DEBUG] REJET ML 3-Layer: {getattr(decision, 'rejection_reason', 'N/A')}")
            else:
                logger.error(f"🔍 [ES DEBUG] ml_3layer.evaluate_trade() a retourné None!")

        # Tracking rejections par layer
        if not decision.should_trade:
            if decision.rejection_reason and 'Layer 1' in decision.rejection_reason:
                self.stats['layer1_rejections'] += 1
            elif decision.rejection_reason and 'Layer 2' in decision.rejection_reason:
                self.stats['layer2_rejections'] += 1
            elif decision.rejection_reason and 'Layer 3' in decision.rejection_reason:
                self.stats['layer3_rejections'] += 1

            logger.info(f"❌ [{symbol}] 3-LAYER: {decision.rejection_reason}")
            if symbol == 'ES':
                logger.warning(f"🔍 [ES DEBUG] REJET: 3-LAYER - {decision.rejection_reason}")
            return {
                'should_trade': False,
                'rejection_reason': decision.rejection_reason,
                'decision': decision,
                'market_context': market_context
            }

        logger.info(
            f"✅ [{symbol}] 3-LAYER OK: {decision.action.value} @ {decision.total_confidence:.1%} "
            f"(L1={decision.layer1_confidence:.1%}, L2={decision.layer2_confidence:.1%}, "
            f"L3={decision.layer3_confidence:.1%})"
        )

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 3: ML PREDICTORS (Quality Score + WIN/LOSS) ← NOUVEAU 15/11
        # ═══════════════════════════════════════════════════════════════════

        ml_quality_score = None
        ml_win_probability = None
        ml_prediction_label = None

        if self.use_ml_models:
            # ───────────────────────────────────────────────────────────────
            # 3A. QUALITY SCORE PREDICTOR (0-100)
            # ───────────────────────────────────────────────────────────────
            if self.quality_predictor:
                try:
                    ml_quality_score = self.quality_predictor.predict(snapshot)

                    # ✅ 27/11: Seuil adaptatif par symbole (ES pas de ML, NQ a un ML)
                    MIN_QUALITY_SCORE_BY_SYMBOL = {
                        'ES': 0.0,   # ✅ Pas de modèle ML ES → Désactivé
                        'NQ': 40.0,  # ✅ Modèle ML NQ → Grade D minimum
                        'RTY': 0.0   # Pas de modèle ML RTY
                    }
                    MIN_QUALITY_SCORE = MIN_QUALITY_SCORE_BY_SYMBOL.get(symbol, 0.0)

                    logger.info(f"📊 [{symbol}] ML Quality seuil: {MIN_QUALITY_SCORE} (score={ml_quality_score:.1f})")

                    if ml_quality_score < MIN_QUALITY_SCORE:
                        self.stats['ml_quality_rejections'] += 1
                        logger.warning(
                            f"❌ [{symbol}] ML QUALITY: Score insuffisant "
                            f"({ml_quality_score:.1f}/100 < {MIN_QUALITY_SCORE})"
                        )
                        return {
                            'should_trade': False,
                            'rejection_reason': f'ML Quality Score: {ml_quality_score:.1f}/100 < {MIN_QUALITY_SCORE}',
                            'decision': decision,
                            'market_context': market_context,
                            'ml_quality_score': ml_quality_score
                        }

                    logger.info(f"✅ [{symbol}] ML QUALITY: {ml_quality_score:.1f}/100")

                    # ═══════════════════════════════════════════════════════════════
                    # 🔧 WARNING ML QUALITY (Optionnel)
                    # ═══════════════════════════════════════════════════════════════
                    if ml_quality_score < 50.0:
                        logger.warning("⚠️" * 40)
                        logger.warning(f"⚠️ [{symbol}] ML QUALITY FAIBLE: {ml_quality_score:.1f}/100")
                        logger.warning(f"   Features potentiellement mal calibrées")
                        logger.warning(f"   Recommandation: Vérifier feature engineering")
                        logger.warning("⚠️" * 40)

                except Exception as e:
                    logger.error(f"⚠️  Erreur Quality Predictor: {e}")

            # ───────────────────────────────────────────────────────────────
            # 3B. WIN/LOSS CLASSIFIER (Seuil optimal 0.45)
            # ───────────────────────────────────────────────────────────────
            if self.win_loss_classifier:
                try:
                    ml_prediction = self.win_loss_classifier.predict(snapshot)
                    ml_win_probability = ml_prediction['win_probability']
                    ml_prediction_label = ml_prediction['label']  # 'WIN' ou 'LOSS'

                    # ═══════════════════════════════════════════════════════════════
                    # 🔥 FILTRE KILLER #1: ML WIN PROBABILITY >= 50%
                    # ═══════════════════════════════════════════════════════════════
                    MIN_ML_WIN_PROBA = 0.50  # 50% minimum

                    if ml_win_probability < MIN_ML_WIN_PROBA:
                        self.stats['ml_winloss_rejections'] += 1
                        logger.error("=" * 80)
                        logger.error(f"❌ [{symbol}] TRADE REJETÉ: ML WIN Probability trop faible")
                        logger.error(f"   ML WIN Proba: {ml_win_probability:.1%}")
                        logger.error(f"   Minimum requis: {MIN_ML_WIN_PROBA:.1%}")
                        logger.error(f"   → Probabilité de PERDRE: {(1-ml_win_probability):.1%}")
                        logger.error("=" * 80)
                        return {
                            'should_trade': False,
                            'rejection_reason': f'ML WIN Probability trop faible: {ml_win_probability:.1%} (min: {MIN_ML_WIN_PROBA:.1%})',
                            'decision': decision,
                            'market_context': market_context,
                            'ml_quality_score': ml_quality_score,
                            'ml_win_probability': ml_win_probability,
                            'ml_prediction_label': ml_prediction_label
                        }

                    logger.info(f"✅ [{symbol}] ML WIN Proba acceptable: {ml_win_probability:.1%} >= {MIN_ML_WIN_PROBA:.1%}")

                    # Vérification label LOSS (seuil 0.45 pour backward compatibility)
                    if ml_prediction_label == 'LOSS':
                        self.stats['ml_winloss_rejections'] += 1
                        logger.warning(
                            f"❌ [{symbol}] ML WIN/LOSS: Prédiction LOSS "
                            f"(P(WIN)={ml_win_probability:.1%}, threshold=0.45)"
                        )
                        return {
                            'should_trade': False,
                            'rejection_reason': f'ML WIN/LOSS: Predicted LOSS (P(WIN)={ml_win_probability:.1%})',
                            'decision': decision,
                            'market_context': market_context,
                            'ml_quality_score': ml_quality_score,
                            'ml_win_probability': ml_win_probability,
                            'ml_prediction_label': ml_prediction_label
                        }

                    logger.info(
                        f"✅ [{symbol}] ML WIN/LOSS: {ml_prediction_label} "
                        f"(P(WIN)={ml_win_probability:.1%}, confidence={ml_prediction['confidence']:.2f})"
                    )

                except Exception as e:
                    logger.error(f"⚠️  Erreur WIN/LOSS Classifier: {e}")

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 4: POST-VALIDATION MARKET CONTEXT
        # ═══════════════════════════════════════════════════════════════════

        if market_context and CONFIG_MARKET_CONTEXT['postvalidation']['reject_opposite_bias']:
            # Vérifier alignement bias
            signal_direction = decision.action.value  # "LONG" ou "SHORT"

            if signal_direction == "LONG" and market_context.main_bias == "BEARISH":
                self.stats['context_postfilter_rejections'] += 1
                logger.warning(
                    f"❌ [{symbol}] POST-VALIDATION: Signal LONG mais bias BEARISH "
                    f"(strength={market_context.bias_strength:.2f})"
                )
                return {
                    'should_trade': False,
                    'rejection_reason': 'Market Context: Opposite bias (LONG vs BEARISH)',
                    'decision': decision,
                    'market_context': market_context
                }

            elif signal_direction == "SHORT" and market_context.main_bias == "BULLISH":
                self.stats['context_postfilter_rejections'] += 1
                logger.warning(
                    f"❌ [{symbol}] POST-VALIDATION: Signal SHORT mais bias BULLISH "
                    f"(strength={market_context.bias_strength:.2f})"
                )
                return {
                    'should_trade': False,
                    'rejection_reason': 'Market Context: Opposite bias (SHORT vs BULLISH)',
                    'decision': decision,
                    'market_context': market_context
                }

            logger.info(f"✅ [{symbol}] POST-VALIDATION OK: Bias aligné ({market_context.main_bias})")

            # Boost si trading plan aligné
            if CONFIG_MARKET_CONTEXT['postvalidation']['boost_aligned_plan']:
                aligned_plan = self._find_aligned_trading_plan(
                    signal_direction,
                    market_context.trading_plans
                )

                if aligned_plan and aligned_plan.confidence > CONFIG_MARKET_CONTEXT['postvalidation']['min_plan_confidence']:
                    boost = CONFIG_MARKET_CONTEXT['postvalidation']['boost_multiplier']
                    original_conf = decision.total_confidence
                    decision.total_confidence *= boost
                    logger.info(
                        f"🚀 [{symbol}] BOOST: Trading plan aligné ({aligned_plan.scenario.value}, "
                        f"conf={aligned_plan.confidence:.2f}) → "
                        f"Confidence {original_conf:.1%} → {decision.total_confidence:.1%}"
                    )

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 4: HARD RULES MENTHORQ
        # ═══════════════════════════════════════════════════════════════════

        hard_rules_result = None
        if CONFIG_HARD_RULES['enabled']:
            try:
                # Préparer levels pour hard rules
                levels = {
                    'gamma': snapshot.get('gamma_wall_level', 0),
                    'blind_spots': [snapshot.get(f'blind_spot_{i}', 0) for i in range(9)],
                    'gex': [snapshot.get(f'gex_{i}', 0) for i in range(1, 11)],
                    'last_update': snapshot.get('last_mq_update_ms', 0),
                    'stale': False
                }

                hard_rules_result = evaluate_execution_rules(
                    current_price=snapshot['mid'],
                    levels=levels,
                    vix_regime=snapshot.get('volatility_regime', 1),
                    dealers_bias=snapshot.get('dealers_bias', 0),
                    context=snapshot
                )

                if hard_rules_result.hard_block:
                    self.stats['hard_rules_rejections'] += 1
                    logger.warning(
                        f"🚫 [{symbol}] HARD RULES BLOCK: {', '.join(hard_rules_result.reasons)}"
                    )
                    return {
                        'should_trade': False,
                        'rejection_reason': f"Hard Rules: {', '.join(hard_rules_result.reasons)}",
                        'decision': decision,
                        'market_context': market_context,
                        'hard_rules_result': hard_rules_result
                    }

                logger.info(
                    f"✅ [{symbol}] HARD RULES OK (size_mult={hard_rules_result.size_multiplier:.2f})"
                )

            except Exception as e:
                logger.error(f"⚠️ Erreur Hard Rules: {e}")

        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 5: DÉCISION FINALE
        # ═══════════════════════════════════════════════════════════════════

        # Calculer size multiplier final
        final_size_mult = 1.0
        if hard_rules_result:
            final_size_mult *= hard_rules_result.size_multiplier

        # Appliquer ajustements confluence/VIX
        if CONFIG_HARD_RULES['enabled']:
            # Boost confluence
            if decision.total_confidence > 0.80:
                final_size_mult *= CONFIG_HARD_RULES['confluence_boost']
                logger.info(f"💎 [{symbol}] Confluence boost: x{CONFIG_HARD_RULES['confluence_boost']}")

            # Réduction VIX
            vix = snapshot.get('vix', 20.0)
            if vix > 25.0:
                final_size_mult *= CONFIG_HARD_RULES['vix_high_multiplier']
                logger.info(f"⚠️  [{symbol}] VIX high ({vix:.1f}): x{CONFIG_HARD_RULES['vix_high_multiplier']}")

        self.stats['trades_executed'] += 1

        logger.info("=" * 80)
        logger.info(f"🚀 [{symbol}] TRADE VALIDÉ: {decision.action.value}")
        logger.info(f"   Confidence: {decision.total_confidence:.1%}")
        logger.info(f"   Size Multiplier: {final_size_mult:.2f}")
        if ml_quality_score:
            logger.info(f"   ML Quality: {ml_quality_score:.1f}/100")
        if ml_win_probability:
            logger.info(f"   ML WIN Proba: {ml_win_probability:.1%}")
        logger.info("=" * 80)

        # ═══════════════════════════════════════════════════════════════
        # ✅ NOUVEAU 21/11 05:15: Calculer Q-Score MIA
        # ═══════════════════════════════════════════════════════════════
        qscore_data = MIAQScore.calculate(
            ml_3layer_result={
                'layer1_confidence': decision.layer1_confidence,
                'layer2_confidence': decision.layer2_confidence,
                'layer3_confidence': decision.layer3_confidence,
                'confluence': decision.total_confidence / 3.0  # Approximation
            },
            tick=snapshot,
            best_signal=None  # Pas de signal ici
        )

        qscore = qscore_data['qscore']
        qscore_grade = qscore_data['grade']

        logger.info(f"📊 [{symbol}] Q-Score MIA: {qscore:.1f} ({qscore_grade}) - {qscore_data['interpretation']}")

        # ═══════════════════════════════════════════════════════════════
        # 🔥 FILTRE KILLER #2: Q-SCORE MIA >= 50
        # ═══════════════════════════════════════════════════════════════
        # 🔧 12/12 14h: RÉACTIVÉ - Analyse montre que Grade F = 100% LOSS
        # QScore < 40 = Grade F = trades de mauvaise qualité
        MIN_QSCORE = 40.0  # 🔧 ACTIVÉ: Bloque Grade F (était 0.0)
        # MIN_QSCORE = 50.0  # Trop strict (bloquerait Grade D aussi)

        if qscore < MIN_QSCORE:
            self.stats['qscore_rejections'] += 1
            logger.error("=" * 80)
            logger.error(f"❌ [{symbol}] TRADE REJETÉ: Q-Score MIA trop faible")
            logger.error(f"   Q-Score: {qscore:.1f} ({qscore_grade})")
            logger.error(f"   Minimum requis: {MIN_QSCORE:.1f} (C)")
            logger.error(f"   → Qualité features insuffisante")
            logger.error("=" * 80)
            return {
                'should_trade': False,
                'rejection_reason': f'Q-Score MIA trop faible: {qscore:.1f} ({qscore_grade}), min: {MIN_QSCORE:.1f}',
                'decision': decision,
                'market_context': market_context,
                'hard_rules_result': hard_rules_result,
                'ml_quality_score': ml_quality_score,
                'ml_win_probability': ml_win_probability,
                'ml_prediction_label': ml_prediction_label,
                'qscore': qscore,
                'qscore_grade': qscore_grade
            }

        logger.info(f"✅ [{symbol}] Q-Score acceptable: {qscore:.1f} ({qscore_grade}) >= {MIN_QSCORE:.1f}")

        return {
            'should_trade': True,
            'action': decision.action.value,
            'confidence': decision.total_confidence,
            'size_multiplier': final_size_mult,
            'layer1_confidence': decision.layer1_confidence,
            'layer2_confidence': decision.layer2_confidence,
            'layer3_confidence': decision.layer3_confidence,
            'market_context': market_context,
            'hard_rules_result': hard_rules_result,
            'decision': decision,
            'rejection_reason': None,
            # ✅ NOUVELLES MÉTADONNÉES ML (15/11/2025)
            'ml_quality_score': ml_quality_score,
            'ml_win_probability': ml_win_probability,
            'ml_prediction_label': ml_prediction_label,
            # ✅ AJOUT 21/11 02:56: Transmettre layer1_reasons pour Discord
            # ✅ FIX 21/11 04:10: Layer1Result est un objet, pas un dict
            'layer1_reasons': getattr(decision.breakdown.get('layer1'), 'triggers', []) if hasattr(decision, 'breakdown') and decision.breakdown.get('layer1') else [],
            'menthorq_scenario': getattr(decision.breakdown.get('layer1'), 'reason', 'UNKNOWN') if hasattr(decision, 'breakdown') and decision.breakdown.get('layer1') else 'UNKNOWN',
            # ✅ NOUVEAU 21/11 05:15: Q-Score MIA
            'qscore': qscore_data['qscore'],
            'qscore_grade': qscore_data['grade'],
            'qscore_interpretation': qscore_data['interpretation'],
            'qscore_components': qscore_data['components']
        }

    def _find_aligned_trading_plan(self, signal_direction: str, trading_plans: list):
        """Trouve un trading plan aligné avec le signal"""
        if not trading_plans:
            return None

        for plan in trading_plans:
            if plan.direction == signal_direction and plan.priority == 1:
                return plan

        return None

    def get_stats(self) -> Dict:
        """Retourne statistiques d'utilisation"""
        total = self.stats['total_evaluations']
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'acceptance_rate': self.stats['trades_executed'] / total if total > 0 else 0,
            'layer1_rejection_rate': self.stats['layer1_rejections'] / total if total > 0 else 0,
            'layer2_rejection_rate': self.stats['layer2_rejections'] / total if total > 0 else 0,
            'layer3_rejection_rate': self.stats['layer3_rejections'] / total if total > 0 else 0,
            'context_prefilter_rate': self.stats['context_prefilter_rejections'] / total if total > 0 else 0,
            'context_postfilter_rate': self.stats['context_postfilter_rejections'] / total if total > 0 else 0,
            'hard_rules_rejection_rate': self.stats['hard_rules_rejections'] / total if total > 0 else 0
        }


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTION POUR INTÉGRATION
# ═══════════════════════════════════════════════════════════════════════

def create_ml_3layer_integrated_system(symbols=["ES", "NQ", "RTY"], config=None):
    """Factory function pour créer le système intégré"""
    return ML3LayerIntegratedSystem(symbols=symbols, config=config)
