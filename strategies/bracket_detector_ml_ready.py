#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Bracket Detector ML_READY
Version native ML_READY - Pas de DataFrame pandas
==========================================

Version: 3.0 - ML_READY Native
Date: 2 Novembre 2025

Détecte les brackets (consolidations/ranges) directement depuis ml_data
Utilise un historique simple de prix pour analyser les patterns

RESPONSABILITÉS:
1. Maintenir historique de prix ML_READY
2. Détecter consolidations (range étroit)
3. Compter touches sur support/résistance
4. Détecter breakouts
5. Qualité des brackets (volume, touches, durée)
"""

from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)

# === DATA STRUCTURES ===

@dataclass
class Bracket:
    """Un bracket détecté"""
    upper: float  # Résistance
    lower: float  # Support
    middle: float  # Point milieu
    width_dollars: float  # Largeur en dollars
    width_percent: float  # Largeur en %
    touches_upper: int  # Nombre de touches résistance
    touches_lower: int  # Nombre de touches support
    quality_score: float  # Score de qualité (0-1)
    detection_time: datetime  # Quand détecté
    bars_in_bracket: int  # Nombre de barres dans le bracket
    avg_volume: float  # Volume moyen dans le bracket
    is_valid: bool  # Si bracket est valide pour trading


# === MAIN CLASS ===

class BracketDetectorMLReady:
    """
    Détecteur de brackets en version ML_READY
    Pas de DataFrame - Utilise liste de dict ml_data
    """

    def __init__(self,
                 window_size: int = 100,
                 min_bars_in_bracket: int = 20,
                 max_width_percent: float = 0.003,  # 0.3%
                 min_touches_per_side: int = 2,
                 touch_threshold_percent: float = 0.0005):  # 0.05%
        """
        Initialisation du détecteur

        Args:
            window_size: Nombre de barres à garder en mémoire
            min_bars_in_bracket: Minimum de barres pour détecter un bracket
            max_width_percent: Largeur max du bracket (% du prix)
            min_touches_per_side: Minimum de touches support ET résistance
            touch_threshold_percent: Seuil pour considérer une "touche"
        """
        self.window_size = window_size
        self.min_bars_in_bracket = min_bars_in_bracket
        self.max_width_percent = max_width_percent
        self.min_touches_per_side = min_touches_per_side
        self.touch_threshold_percent = touch_threshold_percent

        # Historique de prix (deque pour performance)
        self.price_history: deque = deque(maxlen=window_size)

        # Bracket actif
        self.current_bracket: Optional[Bracket] = None

        # Statistics
        self.stats = {
            'brackets_detected': 0,
            'breakouts_detected': 0,
            'last_detection_time': None
        }

        logger.info(f"✅ BracketDetectorMLReady initialisé")
        logger.info(f"   Window: {window_size} | Min bars: {min_bars_in_bracket}")
        logger.info(f"   Max width: {max_width_percent*100:.2f}% | Min touches: {min_touches_per_side}")

    def update(self, ml_data: Dict[str, Any]):
        """
        Met à jour l'historique avec nouvelle donnée ML_READY

        Args:
            ml_data: Dictionnaire ML_READY complet
        """
        # Extraire les données nécessaires
        bar_data = {
            'timestamp': ml_data.get('t_ms', 0),
            'mid': ml_data.get('mid', 0),
            'high': ml_data.get('high', ml_data.get('mid', 0)),
            'low': ml_data.get('low', ml_data.get('mid', 0)),
            'volume': ml_data.get('volume', 0),
            'symbol': ml_data.get('symbol', 'UNKNOWN')
        }

        # Ajouter à l'historique
        self.price_history.append(bar_data)

    def detect_bracket(self, ml_data: Dict[str, Any]) -> Optional[Bracket]:
        """
        Détecte un bracket depuis les données ML_READY

        Args:
            ml_data: Données ML_READY actuelles

        Returns:
            Bracket si détecté, None sinon
        """
        # Mettre à jour l'historique
        self.update(ml_data)

        # Besoin d'au moins min_bars_in_bracket
        if len(self.price_history) < self.min_bars_in_bracket:
            return None

        # Analyser les dernières barres
        recent_bars = list(self.price_history)[-self.min_bars_in_bracket:]

        # Extraire highs et lows
        highs = [bar['high'] for bar in recent_bars]
        lows = [bar['low'] for bar in recent_bars]
        volumes = [bar['volume'] for bar in recent_bars]

        # Trouver support et résistance
        resistance = max(highs)
        support = min(lows)
        middle = (resistance + support) / 2

        # Prix actuel
        current_price = ml_data.get('mid', 0)

        # Vérifier si c'est un bracket valide

        # 1. Largeur en %
        width_dollars = resistance - support
        width_percent = width_dollars / current_price if current_price > 0 else 0

        if width_percent > self.max_width_percent:
            # Range trop large, pas un bracket
            return None

        # 2. Compter touches
        touch_threshold = current_price * self.touch_threshold_percent

        touches_upper = self._count_touches(highs, resistance, touch_threshold)
        touches_lower = self._count_touches(lows, support, touch_threshold)

        if touches_upper < self.min_touches_per_side or touches_lower < self.min_touches_per_side:
            # Pas assez de touches
            return None

        # 3. Volume moyen
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        # 4. Calculer score de qualité
        quality_score = self._calculate_quality_score(
            width_percent=width_percent,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
            bars_count=len(recent_bars),
            avg_volume=avg_volume
        )

        # 5. Créer bracket
        bracket = Bracket(
            upper=resistance,
            lower=support,
            middle=middle,
            width_dollars=width_dollars,
            width_percent=width_percent,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
            quality_score=quality_score,
            detection_time=datetime.now(),
            bars_in_bracket=len(recent_bars),
            avg_volume=avg_volume,
            is_valid=quality_score >= 0.6  # Seuil de qualité minimum
        )

        # Mettre à jour bracket actif
        self.current_bracket = bracket
        self.stats['brackets_detected'] += 1
        self.stats['last_detection_time'] = datetime.now()

        logger.debug(f"📦 Bracket détecté: {support:.2f} - {resistance:.2f} "
                    f"({width_percent*100:.2f}%) | Quality: {quality_score:.2f}")

        return bracket

    def check_breakout(self, ml_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Vérifie si le prix casse un bracket actif

        Args:
            ml_data: Données ML_READY actuelles

        Returns:
            Dict avec infos breakout si détecté, None sinon
        """
        if not self.current_bracket:
            return None

        current_price = ml_data.get('mid', 0)

        # Breakout résistance (bullish)
        if current_price > self.current_bracket.upper:
            breakout = {
                'type': 'bullish_breakout',
                'direction': 'LONG',
                'bracket_upper': self.current_bracket.upper,
                'bracket_lower': self.current_bracket.lower,
                'breakout_price': current_price,
                'bracket_width': self.current_bracket.width_dollars,
                'quality_score': self.current_bracket.quality_score,
                'timestamp': datetime.now()
            }

            self.stats['breakouts_detected'] += 1
            logger.info(f"🚀 BREAKOUT BULLISH détecté: {current_price:.2f} > {self.current_bracket.upper:.2f}")

            # Invalider bracket actif
            self.current_bracket = None

            return breakout

        # Breakout support (bearish)
        elif current_price < self.current_bracket.lower:
            breakout = {
                'type': 'bearish_breakout',
                'direction': 'SHORT',
                'bracket_upper': self.current_bracket.upper,
                'bracket_lower': self.current_bracket.lower,
                'breakout_price': current_price,
                'bracket_width': self.current_bracket.width_dollars,
                'quality_score': self.current_bracket.quality_score,
                'timestamp': datetime.now()
            }

            self.stats['breakouts_detected'] += 1
            logger.info(f"📉 BREAKOUT BEARISH détecté: {current_price:.2f} < {self.current_bracket.lower:.2f}")

            # Invalider bracket actif
            self.current_bracket = None

            return breakout

        return None

    def _count_touches(self, prices: List[float], level: float, threshold: float) -> int:
        """
        Compte le nombre de fois où le prix touche un niveau

        Args:
            prices: Liste de prix (highs ou lows)
            level: Niveau à tester (support ou résistance)
            threshold: Seuil de tolérance

        Returns:
            Nombre de touches
        """
        touches = 0
        for price in prices:
            if abs(price - level) <= threshold:
                touches += 1

        return touches

    def _calculate_quality_score(self,
                                 width_percent: float,
                                 touches_upper: int,
                                 touches_lower: int,
                                 bars_count: int,
                                 avg_volume: float) -> float:
        """
        Calcule un score de qualité pour le bracket

        Args:
            width_percent: Largeur du bracket en %
            touches_upper: Touches sur résistance
            touches_lower: Touches sur support
            bars_count: Nombre de barres dans le bracket
            avg_volume: Volume moyen

        Returns:
            Score de 0 à 1
        """
        score = 0.0

        # 1. Largeur (plus étroit = meilleur) - 30%
        # Idéal: 0.1% - 0.2%
        if 0.001 <= width_percent <= 0.002:
            score += 0.3
        elif 0.0005 <= width_percent <= 0.003:
            score += 0.2
        else:
            score += 0.1

        # 2. Touches (plus de touches = meilleur) - 40%
        total_touches = touches_upper + touches_lower
        if total_touches >= 8:
            score += 0.4
        elif total_touches >= 6:
            score += 0.3
        elif total_touches >= 4:
            score += 0.2
        else:
            score += 0.1

        # 3. Équilibre touches (support ~= résistance) - 20%
        touch_ratio = min(touches_upper, touches_lower) / max(touches_upper, touches_lower) if max(touches_upper, touches_lower) > 0 else 0
        score += touch_ratio * 0.2

        # 4. Durée (plus de barres = meilleur) - 10%
        if bars_count >= 30:
            score += 0.1
        elif bars_count >= 20:
            score += 0.07
        else:
            score += 0.05

        return min(score, 1.0)

    def get_current_bracket(self) -> Optional[Bracket]:
        """Retourne le bracket actuellement actif"""
        return self.current_bracket

    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du détecteur"""
        return {
            'brackets_detected': self.stats['brackets_detected'],
            'breakouts_detected': self.stats['breakouts_detected'],
            'last_detection_time': self.stats['last_detection_time'],
            'current_bracket_active': self.current_bracket is not None,
            'history_size': len(self.price_history)
        }

    def reset(self):
        """Reset le détecteur (historique + bracket actif)"""
        self.price_history.clear()
        self.current_bracket = None
        logger.info("🔄 BracketDetector reset")


# === FACTORY FUNCTION ===

def create_bracket_detector_ml_ready(**kwargs) -> BracketDetectorMLReady:
    """
    Factory pour créer un BracketDetector ML_READY

    Args:
        **kwargs: Arguments pour BracketDetectorMLReady

    Returns:
        BracketDetectorMLReady instance
    """
    return BracketDetectorMLReady(**kwargs)


# === TESTS ===

if __name__ == "__main__":
    logger.info("=== TEST BRACKET DETECTOR ML_READY ===")

    # Créer détecteur
    detector = create_bracket_detector_ml_ready()

    # Simuler consolidation (range 5299-5301)
    import random

    for i in range(30):
        ml_data_test = {
            'symbol': 'ES',
            't_ms': int(datetime.now().timestamp() * 1000) + i * 1000,
            'mid': 5300 + random.uniform(-1, 1),
            'high': 5301 + random.uniform(-0.5, 0.5),
            'low': 5299 + random.uniform(-0.5, 0.5),
            'volume': random.randint(800, 1200)
        }

        # Détecter bracket
        bracket = detector.detect_bracket(ml_data_test)

        if bracket and i == 29:  # Dernière barre
            logger.info(f"✅ Bracket détecté:")
            logger.info(f"   Support: {bracket.lower:.2f}")
            logger.info(f"   Résistance: {bracket.upper:.2f}")
            logger.info(f"   Largeur: {bracket.width_percent*100:.2f}%")
            logger.info(f"   Touches: {bracket.touches_lower} / {bracket.touches_upper}")
            logger.info(f"   Qualité: {bracket.quality_score:.2f}")

    # Simuler breakout bullish
    ml_data_breakout = {
        'symbol': 'ES',
        't_ms': int(datetime.now().timestamp() * 1000) + 31000,
        'mid': 5302,  # Au-dessus de la résistance
        'volume': 1500
    }

    breakout = detector.check_breakout(ml_data_breakout)
    if breakout:
        logger.info(f"✅ Breakout détecté: {breakout['type']}")

    # Statistiques
    stats = detector.get_statistics()
    logger.info(f"✅ Statistiques: {stats}")

    logger.info("=== TEST TERMINÉ ===")

