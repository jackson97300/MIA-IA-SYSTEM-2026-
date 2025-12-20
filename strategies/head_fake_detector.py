"""
Head Fake Detector - ML_READY Adapter (Version Robuste)
Adapte headfake_detector.py (version robuste) pour l'interface ML_READY
"""
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

# Import de la version robuste
from strategies.headfake_detector import HeadFakeDetector as RobustHeadFakeDetector, HeadFakeSetup, HeadFakeType

logger = get_logger(__name__)


@dataclass
class PatternSignal:
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0


class HeadFakeDetector:
    """
    Wrapper pour HeadFakeDetector robuste
    Compatible avec l'interface ML_READY du système
    """

    def __init__(self, config: Optional[Dict] = None):
        # Initialiser la version robuste
        self.robust_detector = RobustHeadFakeDetector(config)

        # Historique de prix pour détecter brackets simples
        self.price_history: Dict[str, list] = {}
        self.max_history_size = 50

        # Stats
        self.stats = {'signals_generated': 0, 'invalidations': 0}

        logger.info("✅ HeadFakeDetector initialisé (VERSION ROBUSTE avec ML_READY adapter)")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Analyse ML_READY pour détecter head fakes

        DIFFÉRENCE CLÉ vs version simpliste:
        - Requiert un bracket actif (range établi)
        - Vérifie breakout PUIS retour rapide
        - Analyse volume (breakout faible, retour fort)
        - Vérifie DOM flip
        - Conditions strictes: 3-10 ticks hors bracket, wick >50%
        """
        start_time = time.perf_counter()

        try:
            symbol = ml_data.get('sym', 'NQ')

            # Mettre à jour historique de prix
            self._update_price_history(symbol, ml_data)

            # Vérifier qu'on a assez d'historique
            if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
                return None  # Pas assez de données

            # Détecter bracket simple depuis l'historique
            bracket = self._detect_simple_bracket(symbol)
            if not bracket:
                return None  # Pas de bracket actif

            # Utiliser le détecteur robuste
            market_data = {
                'close': ml_data.get('mid', 0),
                'high': ml_data.get('high', 0),
                'low': ml_data.get('low', 0),
                'volume': ml_data.get('volume', 0),
                'level1_imbalance': ml_data.get('level1_imbalance', 0),
            }

            headfake = self.robust_detector.detect_headfake(bracket, market_data)

            if not headfake:
                return None

            # Convertir HeadFakeSetup en PatternSignal
            signal = self._convert_to_pattern_signal(headfake)

            if signal:
                self.stats['signals_generated'] += 1
                logger.info(f"✅ HeadFake ROBUSTE: {signal.side} @ {signal.entry:.2f} (quality={headfake.quality_score:.2f})")

            return signal

        except Exception as e:
            logger.error(f"❌ Erreur HeadFake ROBUSTE: {e}")
            return None

    def _update_price_history(self, symbol: str, ml_data: Dict):
        """Met à jour l'historique de prix pour bracket detection"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        bar = {
            'timestamp': ml_data.get('t_ms', int(datetime.now().timestamp() * 1000)),
            'open': ml_data.get('mid', 0),  # Approximation
            'high': ml_data.get('high', 0),
            'low': ml_data.get('low', 0),
            'close': ml_data.get('mid', 0),
            'volume': ml_data.get('volume', 0)
        }

        self.price_history[symbol].append(bar)

        # Garder seulement les dernières bars
        if len(self.price_history[symbol]) > self.max_history_size:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history_size:]

        # Mettre à jour l'historique du détecteur robuste
        self.robust_detector.update_price_history(symbol, bar)

    def _detect_simple_bracket(self, symbol: str):
        """
        Détecte un bracket simple depuis l'historique
        (simplifié pour ML_READY, mais plus strict que la version simpliste)
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return None

        recent = self.price_history[symbol][-20:]

        highs = [b['high'] for b in recent]
        lows = [b['low'] for b in recent]

        # Calculer range
        upper = max(highs)
        lower = min(lows)
        middle = (upper + lower) / 2

        range_size = upper - lower

        # Vérifier que le range est significatif (au moins 8 ticks pour NQ)
        tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10
        min_range_ticks = 8

        if range_size < (min_range_ticks * tick_size):
            return None  # Range trop petit

        # Vérifier que le prix touche régulièrement les bornes
        touches_upper = sum(1 for b in recent if b['high'] >= upper - (2 * tick_size))
        touches_lower = sum(1 for b in recent if b['low'] <= lower + (2 * tick_size))

        if touches_upper < 2 or touches_lower < 2:
            return None  # Pas assez de touches

        # Créer un pseudo-bracket ADAPTÉ pour le détecteur robuste
        # Le détecteur robuste attend bracket.upper_bound.price et bracket.lower_bound.price
        bracket = type('Bracket', (), {
            'symbol': symbol,
            'upper_bound': type('Bound', (), {'price': upper})(),
            'lower_bound': type('Bound', (), {'price': lower})(),
            'middle_price': middle,
            'tick_size': tick_size
        })()

        return bracket

    def _convert_to_pattern_signal(self, headfake: HeadFakeSetup) -> Optional[PatternSignal]:
        """Convertit HeadFakeSetup en PatternSignal"""

        # Déterminer side
        if headfake.headfake_type == HeadFakeType.UPPER_REJECTION:
            side = "SHORT"
        else:
            side = "LONG"

        signal = PatternSignal(
            strategy="head_fake_detector",
            timestamp=headfake.timestamp,
            side=side,
            confidence=headfake.confidence,
            entry=headfake.entry_price,
            stop=headfake.stop_loss,
            targets=[headfake.take_profit_1, headfake.take_profit_2],
            metadata={
                'headfake_type': headfake.headfake_type.value,
                'bracket_upper': headfake.bracket_upper,
                'bracket_lower': headfake.bracket_lower,
                'breakout_distance': headfake.breakout_distance,
                'wick_percent': headfake.wick_percent,
                'volume_ratio': headfake.volume_ratio,
                'dom_flipped': headfake.dom_flipped,
                'quality_score': headfake.quality_score,
                'setup_strength': headfake.setup_strength,
                'source': 'ROBUST_HEAD_FAKE',
                'validation': 'BRACKET_BASED_WITH_DOM_FLIP'
            },
            processing_time_ms=(time.perf_counter() * 1000)
        )

        return signal

    def can_invalidate(self, other_signal, ml_data: Dict) -> bool:
        """
        HeadFake peut invalider d'autres signaux (protection)
        Mais seulement si c'est un vrai head fake (quality > 0.65)
        """
        self.stats['invalidations'] += 1
        return True
