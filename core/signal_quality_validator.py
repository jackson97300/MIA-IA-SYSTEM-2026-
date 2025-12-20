"""
Validateur de qualité des signaux AVANT génération.

Économise calculs ML en rejetant signaux faibles en amont.

Version: 1.0
Date: 19 Novembre 2025
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SignalQualityValidator:
    """Valide qualité signal avant passage au ML."""

    def __init__(self):
        self.avg_win = 136.35
        self.avg_loss = 84.01
        self.avg_stop_hunt = 74.08

    def estimate_win_probability(self,
                                 confidence: float,
                                 rr_ratio: float,
                                 context: Dict) -> float:
        """
        Estime probabilité WIN basé sur confidence et contexte.

        Formule empirique basée sur données historiques:
        - Confidence 0.80+: 45-50% WIN
        - Confidence 0.70-0.80: 35-40% WIN
        - Confidence 0.60-0.70: 25-30% WIN
        - Confidence <0.60: 15-20% WIN

        Ajustements:
        - R:R >2.0: +5%
        - Hot zone: +5%
        - Momentum fort: +5%
        - Contre-tendance: -10%

        Args:
            confidence: Confidence totale signal
            rr_ratio: Risk/Reward ratio
            context: Contexte marché

        Returns:
            float: Probabilité WIN estimée (0.0-1.0)
        """

        # Base selon confidence
        if confidence >= 0.80:
            base_win = 0.475
        elif confidence >= 0.75:
            base_win = 0.425
        elif confidence >= 0.70:
            base_win = 0.375
        elif confidence >= 0.65:
            base_win = 0.30
        elif confidence >= 0.60:
            base_win = 0.25
        else:
            base_win = 0.175

        # Ajustements
        adjustments = 0.0

        # R:R élevé
        if rr_ratio >= 2.0:
            adjustments += 0.05
            logger.debug(f"Quality: High R:R {rr_ratio:.1f} (+5%)")

        # Hot zone
        session = context.get('session', {})
        if session.get('hot_zone', False):
            adjustments += 0.05
            logger.debug(f"Quality: Hot zone (+5%)")

        # Momentum
        bullish_score = context.get('bullish_score', 0.0)
        if abs(bullish_score) >= 0.15:
            adjustments += 0.05
            logger.debug(f"Quality: Strong momentum (+5%)")

        # Contre-tendance
        direction = context.get('direction', 'LONG')
        if (direction == 'LONG' and bullish_score < -0.05) or \
           (direction == 'SHORT' and bullish_score > 0.05):
            adjustments -= 0.10
            logger.debug(f"Quality: Counter-trend (-10%)")

        win_prob = max(0.0, min(1.0, base_win + adjustments))

        logger.info(
            f"Quality: Estimated WIN probability = {win_prob:.1%} "
            f"(base={base_win:.1%}, adj={adjustments:+.1%})"
        )

        return win_prob

    def calculate_expectancy(self,
                            win_prob: float,
                            rr_ratio: float) -> float:
        """
        Calcule expectancy (P&L moyen attendu).

        Args:
            win_prob: Probabilité WIN
            rr_ratio: Risk/Reward ratio

        Returns:
            float: Expectancy en $
        """

        # Probabilités estimées
        loss_prob = (1 - win_prob) * 0.60  # 60% des pertes = LOSS
        stop_hunt_prob = (1 - win_prob) * 0.35  # 35% des pertes = STOP_HUNT
        timeout_prob = (1 - win_prob) * 0.05  # 5% = TIMEOUT (neutre)

        # Calcul expectancy
        expectancy = (
            win_prob * self.avg_win * rr_ratio +
            loss_prob * (-self.avg_loss) +
            stop_hunt_prob * (-self.avg_stop_hunt) +
            timeout_prob * 0
        )

        logger.debug(
            f"Quality: Expectancy = ${expectancy:.2f} "
            f"(WIN={win_prob:.1%}, RR={rr_ratio:.1f})"
        )

        return expectancy

    def validate_signal_quality(self,
                                confidence: float,
                                rr_ratio: float,
                                context: Dict,
                                symbol: str) -> Optional[Dict]:
        """
        Valide qualité signal AVANT génération.

        Rejette si:
        - WIN probability < 15%
        - Expectancy < $10

        Args:
            confidence: Confidence signal
            rr_ratio: Risk/Reward
            context: Contexte
            symbol: Symbole

        Returns:
            Dict avec validation ou None si rejeté
        """

        # Estimer WIN
        win_prob = self.estimate_win_probability(
            confidence,
            rr_ratio,
            context
        )

        # Vérifier seuil WIN
        from config.unified_thresholds import MIN_WIN_PROBABILITY
        min_win = MIN_WIN_PROBABILITY.get(symbol, 0.15)

        if win_prob < min_win:
            logger.warning(
                f"[{symbol}] ❌ Signal rejeté: WIN probability trop faible "
                f"({win_prob:.1%} < {min_win:.1%})"
            )
            return None

        # Calculer expectancy
        expectancy = self.calculate_expectancy(win_prob, rr_ratio)

        # Vérifier seuil expectancy
        from config.unified_thresholds import MIN_EXPECTANCY
        min_exp = MIN_EXPECTANCY.get(symbol, 10.0)

        if expectancy < min_exp:
            logger.warning(
                f"[{symbol}] ❌ Signal rejeté: Expectancy trop faible "
                f"(${expectancy:.2f} < ${min_exp:.2f})"
            )
            return None

        # Signal acceptable
        logger.info(
            f"[{symbol}] ✅ Signal quality OK: "
            f"WIN={win_prob:.1%}, EXP=${expectancy:.2f}"
        )

        return {
            'win_probability': win_prob,
            'expectancy': expectancy,
            'validated': True
        }


# Instance globale
signal_quality_validator = SignalQualityValidator()

















