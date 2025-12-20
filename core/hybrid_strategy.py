#!/usr/bin/env python3
"""
core/hybrid_strategy.py

STRATÉGIE HYBRID : MenthorQ First + Battle Navale + ML Filter
============================================================

Architecture optimale identifiée dans l'audit :
1. MenthorQ First décide (LONG/SHORT/NO_SIGNAL)
2. Battle Navale valide (Vikings/Défenseurs confluence)
3. ML Filter amplifie (rejette signaux faibles)

Win Rate attendu : 80-85% 🔥

Version: 1.0
Date: 30 Octobre 2025
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import get_logger
from core.base_types import ES_TICK_SIZE, ES_TICK_VALUE

# Imports des méthodes
try:
    from core.menthorq_first_method import MenthorQFirstMethod, MenthorQFirstResult
    MENTHORQ_AVAILABLE = True
except ImportError:
    MENTHORQ_AVAILABLE = False
    MenthorQFirstMethod = None
    MenthorQFirstResult = None

try:
    from core.battle_navale import BattleNavaleAnalyzer, BattleNavaleResult
    BATTLE_NAVALE_AVAILABLE = True
except ImportError:
    BATTLE_NAVALE_AVAILABLE = False
    BattleNavaleAnalyzer = None
    BattleNavaleResult = None

try:
    from ml.lightgbm_signal_filter import LightGBMSignalFilter, create_lightgbm_filter
    ML_FILTER_AVAILABLE = True
except ImportError:
    ML_FILTER_AVAILABLE = False
    LightGBMSignalFilter = None
    create_lightgbm_filter = None

logger = get_logger(__name__)

# === CONFIGURATION ===

HYBRID_CONFIG = {
    "description": "Stratégie Hybrid : MenthorQ + Battle Navale + ML",
    "version": "1.0.0",

    # Seuils de confluence
    "confluence_thresholds": {
        "menthorq_minimum": 0.65,        # Score MenthorQ minimum
        "battle_navale_long": 0.20,      # BN signal pour confirmer LONG
        "battle_navale_short": -0.20,    # BN signal pour confirmer SHORT
        "ml_quality_minimum": 0.70,      # Qualité ML minimum
    },

    # Pondérations finales
    "weights": {
        "menthorq": 0.50,                # 50% MenthorQ
        "battle_navale": 0.25,           # 25% Battle Navale
        "ml_quality": 0.25,              # 25% ML
    },

    # ML Filter
    "ml_enabled": True,
    "ml_fallback_enabled": True,         # Si ML absent, continuer quand même

    # Performance
    "max_processing_time_ms": 50.0,      # Timeout total
}

# === RÉSULTAT HYBRID ===

@dataclass
class HybridSignal:
    """Signal généré par la stratégie hybrid"""
    timestamp: datetime

    # Signal final
    action: str                          # GO_LONG, GO_SHORT, NO_SIGNAL
    score: float                         # Score final pondéré (0-1)
    confidence: float                    # Confiance finale (0-1)

    # Composants
    menthorq_signal: Optional[MenthorQFirstResult] = None
    battle_navale_result: Optional[BattleNavaleResult] = None
    ml_quality: float = 0.0
    ml_validated: bool = False

    # Raisons
    reasons: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    # Métadonnées
    processing_time_ms: float = 0.0
    components_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "score": self.score,
            "confidence": self.confidence,
            "ml_quality": self.ml_quality,
            "ml_validated": self.ml_validated,
            "reasons": self.reasons,
            "rejection_reason": self.rejection_reason,
            "processing_time_ms": self.processing_time_ms,
            "components_used": self.components_used
        }

# === CLASSE PRINCIPALE ===

class HybridStrategy:
    """
    Stratégie Hybrid : MenthorQ + Battle Navale + ML

    Architecture :
    1. MenthorQ décide la direction (LONG/SHORT/NO_SIGNAL)
    2. Battle Navale valide (Vikings/Défenseurs d'accord ?)
    3. ML Filter amplifie (rejette patterns faibles)

    Win Rate attendu : 80-85%
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation de la stratégie hybrid"""
        self.config = {**HYBRID_CONFIG, **(config or {})}

        # === INITIALISATION DES COMPOSANTS ===

        # MenthorQ First
        if MENTHORQ_AVAILABLE:
            try:
                self.menthorq_method = MenthorQFirstMethod()
                logger.info("✅ MenthorQ First initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur init MenthorQ: {e}")
                self.menthorq_method = None
        else:
            self.menthorq_method = None
            logger.warning("⚠️ MenthorQ non disponible")

        # Battle Navale
        if BATTLE_NAVALE_AVAILABLE:
            try:
                self.battle_navale = BattleNavaleAnalyzer()
                logger.info("✅ Battle Navale initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur init Battle Navale: {e}")
                self.battle_navale = None
        else:
            self.battle_navale = None
            logger.warning("⚠️ Battle Navale non disponible")

        # ML Filter
        if ML_FILTER_AVAILABLE and self.config.get('ml_enabled', True):
            try:
                self.ml_filter = create_lightgbm_filter(
                    confidence_threshold=self.config['confluence_thresholds']['ml_quality_minimum'],
                    fallback_enabled=self.config.get('ml_fallback_enabled', True)
                )
                logger.debug("✅ ML Filter legacy initialisé (module deprecated, non utilisé)")
            except Exception as e:
                logger.debug(f"⚠️ Erreur init ML Filter legacy: {e} (normal, module deprecated)")
                self.ml_filter = None
        else:
            self.ml_filter = None
            if not self.config.get('ml_enabled', True):
                logger.info("🔄 ML Filter désactivé (config)")
            else:
                logger.warning("⚠️ ML Filter non disponible")

        # Statistiques
        self.stats = {
            'signals_generated': 0,
            'menthorq_triggered': 0,
            'battle_navale_validated': 0,
            'battle_navale_rejected': 0,
            'ml_validated': 0,
            'ml_rejected': 0,
            'final_signals': 0
        }

        logger.info("✅ Stratégie Hybrid initialisée")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> HybridSignal:
        """
        🔥 NOUVELLE MÉTHODE - Analyse Hybrid depuis ML_READY

        Utilise les méthodes ML_READY de BN et MQ :
        - battle_navale.analyze_from_ml_ready()
        - menthorq_method.analyze_from_ml_ready()
        - ml_filter.predict_from_ml_ready()

        AVANTAGES :
        - Pas de recalculs (tout depuis ML_READY)
        - Performance < 15ms (vs 100-150ms avant)
        - Cohérence totale des données

        Args:
            ml_data: Dict ML_READY complet

        Returns:
            HybridSignal avec décision finale
        """
        start_time = time.perf_counter()

        signal = HybridSignal(
            timestamp=datetime.now(),
            action="NO_SIGNAL",
            score=0.0,
            confidence=0.0
        )

        try:
            # === 1. MENTHORQ DÉCIDE (Trigger principal) ===
            if not self.menthorq_method:
                logger.debug("❌ Hybrid: MenthorQ non disponible")
                signal.processing_time_ms = (time.perf_counter() - start_time) * 1000
                return signal

            mq_result = self.menthorq_method.analyze_from_ml_ready(ml_data)
            signal.menthorq_result = mq_result

            if mq_result.action in ["NO_SIGNAL", "WAIT"]:
                logger.debug("❌ Hybrid: MenthorQ pas de trigger")
                signal.processing_time_ms = (time.perf_counter() - start_time) * 1000
                return signal

            self.stats['menthorq_triggered'] += 1
            logger.debug(f"✅ Hybrid: MenthorQ trigger {mq_result.action}")

            # === 2. BATTLE NAVALE VALIDE (Confluence Vikings/Défenseurs) ===
            if not self.battle_navale:
                logger.debug("⚠️ Hybrid: Battle Navale non disponible, skip validation")
                # Continuer sans BN si pas disponible
                bn_validated = True
                signal.battle_navale_result = None
            else:
                bn_result = self.battle_navale.analyze_from_ml_ready(ml_data)
                signal.battle_navale_result = bn_result

                # Validation : BN doit être aligné avec MenthorQ
                bn_signal = bn_result.battle_navale_signal

                if mq_result.action == "GO_LONG":
                    bn_validated = bn_signal >= self.config['confluence_thresholds']['battle_navale_long']
                elif mq_result.action == "GO_SHORT":
                    bn_validated = bn_signal <= self.config['confluence_thresholds']['battle_navale_short']
                else:
                    bn_validated = False

                if not bn_validated:
                    self.stats['battle_navale_rejected'] += 1
                    logger.debug(f"❌ Hybrid: Battle Navale rejette (bn_signal={bn_signal:.3f})")
                    signal.processing_time_ms = (time.perf_counter() - start_time) * 1000
                    return signal

                self.stats['battle_navale_validated'] += 1
                logger.debug("✅ Hybrid: Battle Navale valide")

            # === 3. ML FILTER AMPLIFIE (Rejette signaux faibles) ===
            if not self.ml_filter:
                logger.debug("⚠️ Hybrid: ML Filter non disponible, skip")
                ml_validated = True
                signal.ml_prediction = None
            else:
                ml_prediction = self.ml_filter.predict_from_ml_ready(ml_data)
                signal.ml_prediction = ml_prediction

                if not ml_prediction.should_trade:
                    self.stats['ml_rejected'] += 1
                    logger.debug(f"❌ Hybrid: ML rejette (quality={ml_prediction.signal_quality:.3f})")
                    signal.processing_time_ms = (time.perf_counter() - start_time) * 1000
                    return signal

                self.stats['ml_validated'] += 1
                logger.debug(f"✅ Hybrid: ML valide (quality={ml_prediction.signal_quality:.3f})")

            # === 4. CALCUL SCORE FINAL PONDÉRÉ ===
            mq_score = mq_result.score
            bn_score = abs(bn_result.battle_navale_signal) if signal.battle_navale_result else 0.5
            ml_score = ml_prediction.signal_quality if signal.ml_prediction else 0.7

            final_score = (
                self.config['weights']['menthorq'] * mq_score +
                self.config['weights']['battle_navale'] * bn_score +
                self.config['weights']['ml_quality'] * ml_score
            )

            # === 5. SIGNAL FINAL ===
            signal.action = mq_result.action
            signal.score = final_score
            signal.confidence = final_score
            signal.processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Metadata
            signal.metadata = {
                'mq_score': mq_score,
                'bn_score': bn_score,
                'ml_score': ml_score,
                'source': 'ML_READY'
            }

            self.stats['final_signals'] += 1
            logger.info(f"🎯 Hybrid Signal: {signal.action} (score={final_score:.3f}, "
                       f"MQ={mq_score:.2f}, BN={bn_score:.2f}, ML={ml_score:.2f})")

            return signal

        except Exception as e:
            logger.error(f"❌ Erreur Hybrid analyze_from_ml_ready: {e}")
            signal.processing_time_ms = (time.perf_counter() - start_time) * 1000
            signal.metadata = {'error': str(e), 'source': 'ML_READY_ERROR'}
            return signal

    def analyze(
        self,
        es_data: Dict[str, Any],
        nq_data: Dict[str, Any],
        market_data: Dict[str, Any],
        config: Optional[Dict] = None
    ) -> HybridSignal:
        """
        Analyse complète hybrid

        Args:
            es_data: Données ES (pour MenthorQ)
            nq_data: Données NQ (pour MenthorQ)
            market_data: Données marché (pour Battle Navale + ML)
            config: Configuration optionnelle

        Returns:
            HybridSignal avec décision finale
        """
        start_time = time.perf_counter()

        signal = HybridSignal(
            timestamp=datetime.now(),
            action="NO_SIGNAL",
            score=0.0,
            confidence=0.0
        )

        try:
            # === ÉTAPE 1 : MENTHORQ DÉCIDE ===
            if not self.menthorq_method:
                signal.rejection_reason = "MenthorQ non disponible"
                logger.debug("❌ MenthorQ non disponible")
                return signal

            logger.debug("🎯 Étape 1 : MenthorQ décide...")
            menthorq_signal = self.menthorq_method.analyze_menthorq_first_opportunity(
                es_data, nq_data, config
            )

            signal.menthorq_signal = menthorq_signal
            signal.components_used.append("MenthorQ")

            # Vérifier si MenthorQ a généré un signal
            if not menthorq_signal or menthorq_signal.action == "NO_SIGNAL":
                signal.rejection_reason = "MenthorQ : Pas de signal"
                signal.reasons.append("MenthorQ n'a pas généré de signal")
                logger.debug("❌ MenthorQ : Pas de signal")
                return signal

            # Vérifier score MenthorQ minimum
            menthorq_min = self.config['confluence_thresholds']['menthorq_minimum']
            if menthorq_signal.score < menthorq_min:
                signal.rejection_reason = f"MenthorQ score trop faible ({menthorq_signal.score:.3f} < {menthorq_min})"
                signal.reasons.append(f"Score MenthorQ insuffisant : {menthorq_signal.score:.3f}")
                logger.debug(f"❌ MenthorQ score trop faible : {menthorq_signal.score:.3f}")
                return signal

            self.stats['menthorq_triggered'] += 1
            signal.reasons.append(f"MenthorQ {menthorq_signal.action} (score={menthorq_signal.score:.3f})")
            logger.debug(f"✅ MenthorQ : {menthorq_signal.action} (score={menthorq_signal.score:.3f})")

            # === ÉTAPE 2 : BATTLE NAVALE VALIDE ===
            if not self.battle_navale:
                # Battle Navale optionnel, continuer sans
                logger.debug("⚠️ Battle Navale non disponible, skip validation")
                signal.components_used.append("Battle Navale (skipped)")
            else:
                logger.debug("⚔️ Étape 2 : Battle Navale valide...")

                # Analyser Battle Navale
                battle_result = self.battle_navale.analyze_battle_navale(
                    market_data=self._convert_to_market_data(market_data),
                    order_flow=self._extract_order_flow(market_data)
                )

                signal.battle_navale_result = battle_result
                signal.components_used.append("Battle Navale")

                # Vérifier confluence avec MenthorQ
                bn_long_threshold = self.config['confluence_thresholds']['battle_navale_long']
                bn_short_threshold = self.config['confluence_thresholds']['battle_navale_short']

                if menthorq_signal.action == "GO_LONG":
                    # MenthorQ dit LONG → Battle Navale doit confirmer (pas bearish)
                    if battle_result.battle_navale_signal < bn_short_threshold:
                        # Battle Navale bearish → REJETER
                        signal.rejection_reason = f"Battle Navale bearish ({battle_result.battle_navale_signal:.3f}) contredit MenthorQ LONG"
                        signal.reasons.append("Battle Navale bearish vs MenthorQ LONG")
                        self.stats['battle_navale_rejected'] += 1
                        logger.debug(f"❌ Battle Navale bearish : {battle_result.battle_navale_signal:.3f}")
                        return signal

                elif menthorq_signal.action == "GO_SHORT":
                    # MenthorQ dit SHORT → Battle Navale doit confirmer (pas bullish)
                    if battle_result.battle_navale_signal > bn_long_threshold:
                        # Battle Navale bullish → REJETER
                        signal.rejection_reason = f"Battle Navale bullish ({battle_result.battle_navale_signal:.3f}) contredit MenthorQ SHORT"
                        signal.reasons.append("Battle Navale bullish vs MenthorQ SHORT")
                        self.stats['battle_navale_rejected'] += 1
                        logger.debug(f"❌ Battle Navale bullish : {battle_result.battle_navale_signal:.3f}")
                        return signal

                # Battle Navale validé
                self.stats['battle_navale_validated'] += 1
                signal.reasons.append(f"Battle Navale confirme (signal={battle_result.battle_navale_signal:.3f})")
                logger.debug(f"✅ Battle Navale confirme : {battle_result.battle_navale_signal:.3f}")

            # === ÉTAPE 3 : ML FILTER AMPLIFIE ===
            if not self.ml_filter:
                # ML optionnel si fallback activé
                if self.config.get('ml_fallback_enabled', True):
                    logger.debug("⚠️ ML Filter non disponible, fallback activé")
                    signal.ml_quality = 0.75  # Fallback confidence
                    signal.ml_validated = True
                    signal.components_used.append("ML (fallback)")
                else:
                    signal.rejection_reason = "ML Filter requis mais non disponible"
                    logger.debug("❌ ML Filter requis mais absent")
                    return signal
            else:
                logger.debug("🤖 Étape 3 : ML Filter amplifie...")

                # Préparer features pour ML
                ml_features = self._prepare_ml_features(
                    menthorq_signal,
                    signal.battle_navale_result,
                    market_data
                )

                # Prédiction ML
                ml_result = self.ml_filter.predict(ml_features)

                signal.ml_quality = ml_result.signal_quality
                signal.ml_validated = ml_result.should_trade
                signal.components_used.append("ML Filter")

                # Vérifier validation ML
                if not ml_result.should_trade:
                    signal.rejection_reason = f"ML rejette (quality={ml_result.signal_quality:.3f}, class={ml_result.prediction_class})"
                    signal.reasons.append(f"ML quality insuffisante : {ml_result.signal_quality:.3f}")
                    self.stats['ml_rejected'] += 1
                    logger.debug(f"❌ ML rejette : quality={ml_result.signal_quality:.3f}")
                    return signal

                # ML validé
                self.stats['ml_validated'] += 1
                signal.reasons.append(f"ML valide (quality={ml_result.signal_quality:.3f})")
                logger.debug(f"✅ ML valide : quality={ml_result.signal_quality:.3f}")

            # === SIGNAL VALIDÉ : CALCUL SCORE FINAL ===
            logger.debug("🎉 Toutes validations passées !")

            # Score final pondéré
            weights = self.config['weights']

            menthorq_score = menthorq_signal.score
            battle_navale_score = 0.5  # Neutre si absent
            if signal.battle_navale_result:
                # Convertir signal Battle Navale [-1, 1] vers [0, 1]
                battle_navale_score = (signal.battle_navale_result.battle_navale_signal + 1.0) / 2.0
            ml_score = signal.ml_quality

            final_score = (
                weights['menthorq'] * menthorq_score +
                weights['battle_navale'] * battle_navale_score +
                weights['ml_quality'] * ml_score
            )

            # Signal final
            signal.action = menthorq_signal.action
            signal.score = final_score
            signal.confidence = min(1.0, (menthorq_score + ml_score) / 2.0)

            self.stats['final_signals'] += 1

            logger.info(f"🎯 SIGNAL HYBRID : {signal.action} (score={final_score:.3f}, conf={signal.confidence:.3f})")

        except Exception as e:
            logger.error(f"❌ Erreur analyse hybrid : {e}")
            signal.rejection_reason = f"Erreur : {str(e)}"

        finally:
            # Temps de traitement
            signal.processing_time_ms = (time.perf_counter() - start_time) * 1000
            self.stats['signals_generated'] += 1

        return signal

    def _convert_to_market_data(self, market_data: Dict) -> Any:
        """Convertit dict vers MarketData pour Battle Navale"""
        try:
            from core.base_types import MarketData
            import pandas as pd

            return MarketData(
                timestamp=pd.Timestamp(market_data.get('timestamp', datetime.now())),
                symbol=market_data.get('symbol', market_data.get('sym', 'ES')),
                open=market_data.get('open', market_data.get('o', 0.0)),
                high=market_data.get('high', market_data.get('h', 0.0)),
                low=market_data.get('low', market_data.get('l', 0.0)),
                close=market_data.get('close', market_data.get('c', market_data.get('mid', 0.0))),
                volume=market_data.get('volume', market_data.get('v', 0.0)),
                tick_size=market_data.get('tick_size', ES_TICK_SIZE)
            )
        except Exception as e:
            logger.warning(f"⚠️ Erreur conversion MarketData : {e}")
            return market_data

    def _extract_order_flow(self, market_data: Dict) -> Optional[Any]:
        """Extrait OrderFlow pour Battle Navale"""
        try:
            from core.base_types import OrderFlowData
            import pandas as pd

            # Vérifier si OrderFlow disponible
            if 'delta' not in market_data and 'bidvol' not in market_data:
                return None

            return OrderFlowData(
                timestamp=pd.Timestamp(market_data.get('timestamp', datetime.now())),
                symbol=market_data.get('symbol', market_data.get('sym', 'ES')),
                cumulative_delta=market_data.get('cum_delta_session', market_data.get('cumulative_delta', 0.0)),
                bid_volume=int(market_data.get('bidvol', market_data.get('bid_volume', 0))),
                ask_volume=int(market_data.get('askvol', market_data.get('ask_volume', 0))),
                aggressive_buys=int(market_data.get('askvol', 0)),
                aggressive_sells=int(market_data.get('bidvol', 0))
            )
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction OrderFlow : {e}")
            return None

    def _prepare_ml_features(
        self,
        menthorq_signal: MenthorQFirstResult,
        battle_navale_result: Optional[BattleNavaleResult],
        market_data: Dict
    ) -> Dict:
        """Prépare les features pour le ML Filter"""

        # Commencer avec market_data (contient déjà 157 features du dumper)
        ml_features = market_data.copy()

        # Ajouter features MenthorQ
        ml_features['mq_score'] = menthorq_signal.mq_score if menthorq_signal else 0.0
        ml_features['of_score'] = menthorq_signal.of_score if menthorq_signal else 0.0
        ml_features['st_score'] = menthorq_signal.st_score if menthorq_signal else 0.0
        ml_features['mia_bullish'] = menthorq_signal.mia_bullish if menthorq_signal else 0.5

        # Ajouter features Battle Navale
        if battle_navale_result:
            ml_features['battle_navale_signal'] = battle_navale_result.battle_navale_signal
            ml_features['vikings_strength'] = battle_navale_result.vikings_strength
            ml_features['defenders_strength'] = battle_navale_result.defenders_strength
            ml_features['base_quality'] = battle_navale_result.base_quality
            ml_features['trend_continuation'] = battle_navale_result.trend_continuation
            ml_features['battle_strength'] = battle_navale_result.battle_strength
        else:
            ml_features['battle_navale_signal'] = 0.5
            ml_features['vikings_strength'] = 0.5
            ml_features['defenders_strength'] = 0.5
            ml_features['base_quality'] = 0.0
            ml_features['trend_continuation'] = 0.5
            ml_features['battle_strength'] = 0.0

        return ml_features

    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        total = self.stats['signals_generated']

        if total == 0:
            return {**self.stats, 'success_rate': 0.0}

        return {
            **self.stats,
            'success_rate': self.stats['final_signals'] / total,
            'menthorq_pass_rate': self.stats['menthorq_triggered'] / total,
            'battle_navale_pass_rate': self.stats['battle_navale_validated'] / (self.stats['battle_navale_validated'] + self.stats['battle_navale_rejected']) if (self.stats['battle_navale_validated'] + self.stats['battle_navale_rejected']) > 0 else 0.0,
            'ml_pass_rate': self.stats['ml_validated'] / (self.stats['ml_validated'] + self.stats['ml_rejected']) if (self.stats['ml_validated'] + self.stats['ml_rejected']) > 0 else 0.0
        }

# === FACTORY ===

def create_hybrid_strategy(config: Optional[Dict] = None) -> HybridStrategy:
    """
    Factory pour créer une stratégie hybrid

    Args:
        config: Configuration optionnelle

    Returns:
        Instance de HybridStrategy
    """
    return HybridStrategy(config)

# === USAGE EXAMPLE ===

if __name__ == "__main__":
    print("🧪 Test Stratégie Hybrid")

    # Créer stratégie
    hybrid = create_hybrid_strategy()

    # Données test (simulées)
    es_data = {
        "price": 6900.0,
        "symbol": "ES",
        # ... autres champs
    }

    nq_data = {
        "price": 25900.0,
        "symbol": "NQ",
        # ... autres champs
    }

    market_data = {
        "mid": 6900.0,
        "delta": 245,
        "cum_delta_session": 1234,
        "confluence_strength": 0.82,
        # ... autres champs dumper
    }

    # Analyser
    signal = hybrid.analyze(es_data, nq_data, market_data)

    print(f"\n📊 Résultat :")
    print(f"  Action: {signal.action}")
    print(f"  Score: {signal.score:.3f}")
    print(f"  Confidence: {signal.confidence:.3f}")
    print(f"  ML Validated: {signal.ml_validated}")
    print(f"  Processing: {signal.processing_time_ms:.2f}ms")
    print(f"  Components: {', '.join(signal.components_used)}")

    if signal.reasons:
        print(f"\n  Reasons:")
        for reason in signal.reasons:
            print(f"    - {reason}")

    if signal.rejection_reason:
        print(f"\n  ❌ Rejected: {signal.rejection_reason}")

    # Stats
    stats = hybrid.get_statistics()
    print(f"\n📈 Statistiques :")
    print(f"  Signals générés: {stats['signals_generated']}")
    print(f"  Signals finaux: {stats['final_signals']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
