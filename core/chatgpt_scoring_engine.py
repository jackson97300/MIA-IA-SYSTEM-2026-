"""
CHATGPT SCORING ENGINE

Moteur de scoring validé par ChatGPT basé sur l'analyse historique.
Pondérations optimisées pour ES/NQ.

Scoring Weights:
- Options Confluence: 30%
- VWAP Trend & Bands: 20%
- OrderFlow Imbalance + Delta: 20%
- Relative Volume: 15%
- ES↔NQ Relative Strength: 10%
- Timing (Session): 5%
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Force du signal"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class ScoringResult:
    """Résultat du scoring"""
    score: float  # 0.0 à 1.0
    signal_strength: SignalStrength
    components: Dict[str, float]  # Scores individuels des composantes
    multipliers: Dict[str, float]  # Multiplicateurs appliqués
    final_score: float  # Score après multiplicateurs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "signal_strength": self.signal_strength.value,
            "final_score": self.final_score,
            "components": self.components,
            "multipliers": self.multipliers
        }


class ChatGPTScoringEngine:
    """
    Moteur de scoring ChatGPT

    Calcule un score pondéré basé sur:
    1. Options Confluence (30%)
    2. VWAP Trend & Bands (20%)
    3. OrderFlow Imbalance + Delta (20%)
    4. Relative Volume (15%)
    5. ES↔NQ Relative Strength (10%)
    6. Timing/Session (5%)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Pondérations (total = 1.0)
        self.weights = {
            'options_confluence': 0.30,
            'vwap_trend_bands': 0.20,
            'orderflow_imbalance_delta': 0.20,
            'relative_volume': 0.15,
            'es_nq_relative_strength': 0.10,
            'timing_session': 0.05
        }

        # Seuils de décision
        self.thresholds = {
            'strong_buy': 0.75,
            'buy': 0.60,
            'sell': 0.40,
            'strong_sell': 0.25
        }

        logger.info("🎯 ChatGPT Scoring Engine initialisé")
        logger.info(f"   Weights: {self.weights}")

    def normalize_options_confluence(self, features: Dict[str, Any]) -> float:
        """
        Normalise le score Options Confluence

        Composantes:
        - Dealer's Bias aligné
        - Distance mur gamma (headroom)
        - Proximité niveau options

        Returns:
            Score 0.0 à 1.0
        """
        score = 0.5  # Neutre

        # Dealer's Bias
        bias = features.get('dealers_bias', 0)
        trade_direction = features.get('trade_direction', 'LONG')

        if trade_direction == 'LONG' and bias > 0:
            score += 0.3
        elif trade_direction == 'SHORT' and bias < 0:
            score += 0.3
        elif (trade_direction == 'LONG' and bias < 0) or (trade_direction == 'SHORT' and bias > 0):
            score -= 0.3

        # Headroom (distance mur gamma)
        headroom_pct = features.get('gamma_wall_distance_pct', 0.20)
        if headroom_pct >= 0.15:
            score += 0.2
        elif headroom_pct < 0.10:
            score -= 0.2  # Bloqué

        # Proximité niveau options (pour reversals)
        proximity_pct = features.get('options_proximity_pct', 1.0)
        if proximity_pct <= 0.20:
            score += 0.1  # Proche d'un niveau

        return max(0.0, min(1.0, score))

    def normalize_vwap_trend_bands(self, features: Dict[str, Any]) -> float:
        """
        Normalise le score VWAP Trend & Bands

        Composantes:
        - VWAP slope
        - Distance VWAP (d_vwap)
        - Position dans les bandes (SD1/SD2)

        Returns:
            Score 0.0 à 1.0
        """
        score = 0.5

        trade_direction = features.get('trade_direction', 'LONG')
        vwap_slope = features.get('vwap_slope', 0)
        d_vwap = features.get('d_vwap', 0)

        # VWAP slope aligné
        if (trade_direction == 'LONG' and vwap_slope > 0) or (trade_direction == 'SHORT' and vwap_slope < 0):
            score += 0.3
        elif (trade_direction == 'LONG' and vwap_slope < 0) or (trade_direction == 'SHORT' and vwap_slope > 0):
            score -= 0.3

        # Distance VWAP
        if trade_direction == 'LONG':
            if d_vwap >= 0:  # Au-dessus VWAP
                score += 0.2
            else:
                score -= 0.2
        else:  # SHORT
            if d_vwap <= 0:  # Sous VWAP
                score += 0.2
            else:
                score -= 0.2

        # Position dans bandes (bonus si dans SD1)
        sd_position = features.get('vwap_sd_position', 0)  # -2 à +2
        if abs(sd_position) <= 1:
            score += 0.1  # Dans ±SD1

        return max(0.0, min(1.0, score))

    def normalize_orderflow_imbalance_delta(self, features: Dict[str, Any]) -> float:
        """
        Normalise le score OrderFlow

        Composantes:
        - DOM Imbalance L1
        - Delta 10s
        - Cohérence flux

        Returns:
            Score 0.0 à 1.0
        """
        score = 0.5

        trade_direction = features.get('trade_direction', 'LONG')
        level1_imb = features.get('level1_imbalance', 0)
        delta_10s = features.get('delta_10s', 0)
        symbol = features.get('sym', 'ES')

        # Seuils selon symbole
        threshold = 0.12 if 'ES' in symbol else 0.10

        # DOM Imbalance aligné
        if trade_direction == 'LONG':
            if level1_imb >= threshold:
                score += 0.4
            elif level1_imb < 0:
                score -= 0.3
        else:  # SHORT
            if level1_imb <= -threshold:
                score += 0.4
            elif level1_imb > 0:
                score -= 0.3

        # Delta 10s aligné
        if (trade_direction == 'LONG' and delta_10s > 0) or (trade_direction == 'SHORT' and delta_10s < 0):
            score += 0.2

        return max(0.0, min(1.0, score))

    def normalize_relative_volume(self, features: Dict[str, Any]) -> float:
        """
        Normalise le score Volume Relatif

        Formule: clamp(vol(1m)/MA(5m), 0.8..1.6) → [0..1]

        Returns:
            Score 0.0 à 1.0
        """
        vol_relative = features.get('volume_relative_5m', 1.0)

        # Clamper entre 0.8 et 1.6
        clamped = max(0.8, min(1.6, vol_relative))

        # Normaliser [0.8..1.6] → [0..1]
        normalized = (clamped - 0.8) / (1.6 - 0.8)

        return normalized

    def normalize_es_nq_relative_strength(self, features: Dict[str, Any]) -> float:
        """
        Normalise le score Relative Strength ES↔NQ

        Returns:
            1.0 si leader aligné avec trade, 0.0 sinon
        """
        rs = features.get('es_nq_relative_strength', 0)
        trade_direction = features.get('trade_direction', 'LONG')
        symbol = features.get('sym', 'ES')

        # Pour LONG: on veut RS positif (symbole > autre)
        # Pour SHORT: on veut RS négatif (symbole < autre)

        if trade_direction == 'LONG':
            return 1.0 if rs > 0 else 0.0
        else:  # SHORT
            return 1.0 if rs < 0 else 0.0

    def normalize_timing_session(self, features: Dict[str, Any]) -> float:
        """
        Normalise le score Timing/Session

        Returns:
            1.0 pour OB/PH, 0.5 sinon
        """
        session = features.get('session_id', 'UNKNOWN')

        if session in ['OPENING_BELL', 'POWER_HOUR']:
            return 1.0
        elif session == 'LUNCH':
            return 0.3
        elif session == 'ASIA':
            return 0.2
        else:
            return 0.5

    def calculate_score(self, features: Dict[str, Any]) -> ScoringResult:
        """
        Calcule le score total pondéré

        Args:
            features: Dict normalisé avec toutes les composantes

        Returns:
            ScoringResult avec score et signal strength
        """
        # Normaliser chaque composante
        components = {
            'options_confluence': self.normalize_options_confluence(features),
            'vwap_trend_bands': self.normalize_vwap_trend_bands(features),
            'orderflow_imbalance_delta': self.normalize_orderflow_imbalance_delta(features),
            'relative_volume': self.normalize_relative_volume(features),
            'es_nq_relative_strength': self.normalize_es_nq_relative_strength(features),
            'timing_session': self.normalize_timing_session(features)
        }

        # Calculer score pondéré
        base_score = sum(
            components[key] * self.weights[key]
            for key in self.weights.keys()
        )

        # Multiplicateurs contextuels
        multipliers = {}

        # Session
        session = features.get('session_id', 'UNKNOWN')
        if session in ['OPENING_BELL', 'POWER_HOUR']:
            multipliers['session'] = 1.2
        elif session == 'LUNCH':
            multipliers['session'] = 0.8
        elif session == 'ASIA':
            multipliers['session'] = 0.5
        else:
            multipliers['session'] = 1.0

        # Volatilité
        vol_regime = features.get('vol_regime', 'normal')
        if vol_regime == 'high':
            multipliers['volatility'] = 0.9
        elif vol_regime == 'low':
            multipliers['volatility'] = 1.1
        else:
            multipliers['volatility'] = 1.0

        # Headroom
        headroom_blocked = features.get('headroom_blocked', False)
        if headroom_blocked:
            multipliers['headroom'] = 0.7
        else:
            multipliers['headroom'] = 1.0

        # Score final
        final_score = base_score
        for mult_value in multipliers.values():
            final_score *= mult_value

        # Clamper entre 0 et 1
        final_score = max(0.0, min(1.0, final_score))

        # Déterminer signal strength
        if final_score >= self.thresholds['strong_buy']:
            signal_strength = SignalStrength.STRONG_BUY
        elif final_score >= self.thresholds['buy']:
            signal_strength = SignalStrength.BUY
        elif final_score <= self.thresholds['strong_sell']:
            signal_strength = SignalStrength.STRONG_SELL
        elif final_score <= self.thresholds['sell']:
            signal_strength = SignalStrength.SELL
        else:
            signal_strength = SignalStrength.NEUTRAL

        return ScoringResult(
            score=base_score,
            signal_strength=signal_strength,
            components=components,
            multipliers=multipliers,
            final_score=final_score
        )


def create_chatgpt_scoring_engine(config: Optional[Dict] = None) -> ChatGPTScoringEngine:
    """Factory pour créer un ChatGPT Scoring Engine"""
    return ChatGPTScoringEngine(config)


if __name__ == "__main__":
    # Test du scoring engine
    logging.basicConfig(level=logging.INFO)

    engine = create_chatgpt_scoring_engine()

    # Test case: LONG continuation
    test_features = {
        'trade_direction': 'LONG',
        'dealers_bias': 0.5,
        'gamma_wall_distance_pct': 0.20,
        'vwap_slope': 0.1,
        'd_vwap': 0.5,
        'level1_imbalance': 0.15,
        'delta_10s': 100,
        'volume_relative_5m': 1.3,
        'es_nq_relative_strength': 0.05,
        'session_id': 'OPENING_BELL',
        'sym': 'ESZ25',
        'vol_regime': 'normal',
        'headroom_blocked': False
    }

    result = engine.calculate_score(test_features)

    print("\n" + "="*70)
    print("TEST CHATGPT SCORING ENGINE")
    print("="*70)
    print(f"\nBase Score: {result.score:.3f}")
    print(f"Final Score: {result.final_score:.3f}")
    print(f"Signal Strength: {result.signal_strength.value}")
    print(f"\nComponents:")
    for comp, score in result.components.items():
        print(f"  {comp}: {score:.3f} (weight: {engine.weights[comp]:.2f})")
    print(f"\nMultipliers:")
    for mult, value in result.multipliers.items():
        print(f"  {mult}: {value:.2f}")
