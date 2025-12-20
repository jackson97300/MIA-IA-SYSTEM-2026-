#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Head Fake Detector
Détecte les faux breakouts (head fakes) sur les brackets
Setup rare mais TRÈS puissant (RR 3:1 à 5:1)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from core.logger import get_logger
from strategies.bracket_detector import Bracket

logger = get_logger(__name__)


class HeadFakeType(Enum):
    """Type de head fake"""
    UPPER_REJECTION = "upper_rejection"  # Rejet borne haute → SHORT
    LOWER_REJECTION = "lower_rejection"  # Rejet borne basse → LONG


@dataclass
class HeadFakeSetup:
    """Un setup head fake détecté"""
    # Identification
    headfake_id: str
    timestamp: datetime
    symbol: str
    headfake_type: HeadFakeType

    # Bracket associé
    bracket_upper: float
    bracket_lower: float
    bracket_middle: float

    # Détails du fake
    breakout_price: float      # Prix max/min atteint
    breakout_distance: float   # Distance hors bracket (ticks)
    return_price: float        # Prix de retour

    # Validation
    wick_percent: float        # % de wick (rejet)
    volume_on_breakout: float  # Volume durant breakout
    volume_on_return: float    # Volume au retour
    volume_ratio: float        # ratio return/breakout

    # DOM
    dom_imbalance_before: float  # DOM avant fake
    dom_imbalance_after: float   # DOM après (flip?)
    dom_flipped: bool            # DOM a changé de côté?

    # Timing
    breakout_duration_bars: int  # Combien de bars hors bracket
    time_to_return: int          # Minutes pour revenir

    # Signal
    entry_price: float
    stop_loss: float
    take_profit_1: float  # Middle
    take_profit_2: float  # Opposé

    # Qualité
    quality_score: float
    confidence: float
    setup_strength: str   # WEAK / MODERATE / STRONG / VERY_STRONG


class HeadFakeDetector:
    """Détecteur de head fakes (faux breakouts)"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()

        # Historique de prix pour détecter les fakes
        self.price_history: Dict[str, List[Dict]] = {}  # {symbol: [bars]}
        self.max_history_bars = 20

        # Head fakes détectés
        self.active_headfakes: Dict[str, HeadFakeSetup] = {}

        # Statistiques
        self.headfakes_detected_today = 0
        self.headfakes_traded_today = 0

        logger.info("⚡ HeadFakeDetector initialisé")
        logger.info(f"  - Min breakout: {self.config['min_breakout_ticks']} ticks")
        logger.info(f"  - Min wick: {self.config['min_wick_percent']}%")
        logger.info(f"  - Require DOM flip: {self.config['require_dom_flip']}")

    def _default_config(self) -> Dict:
        """Configuration par défaut"""
        return {
            'min_breakout_ticks': 3,           # Min 3 ticks hors bracket
            'max_breakout_ticks': 10,          # Max 10 ticks (sinon vraie cassure)
            'max_duration_bars': 3,            # Max 3 bars
            'min_wick_percent': 50,            # Wick > 50% de la bar
            'volume_threshold': 0.7,           # Volume breakout < 70% moyenne
            'min_volume_ratio': 1.3,           # Volume return > 1.3× breakout
            'require_dom_flip': True,          # DOM doit flip
            'min_dom_imbalance_change': 0.3,   # DOM change > 30%
            'max_return_time_bars': 2,         # Retour en 2 bars max
            'min_quality_score': 0.65          # Quality minimum pour trader
        }

    def update_price_history(self, symbol: str, bar_data: Dict):
        """Met à jour l'historique de prix"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append({
            'timestamp': datetime.now(),
            'open': float(bar_data.get('open', 0)),
            'high': float(bar_data.get('high', 0)),
            'low': float(bar_data.get('low', 0)),
            'close': float(bar_data.get('close', 0)),
            'volume': float(bar_data.get('volume', 0))
        })

        # Garder seulement les dernières bars
        if len(self.price_history[symbol]) > self.max_history_bars:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history_bars:]

    def detect_headfake(self, bracket: Bracket, market_data: Dict) -> Optional[HeadFakeSetup]:
        """
        Détecte un head fake sur un bracket

        Args:
            bracket: Bracket actif
            market_data: Données de marché actuelles

        Returns:
            HeadFakeSetup si détecté, None sinon
        """
        try:
            symbol = bracket.symbol
            current_price = float(market_data.get('close', 0))

            # Vérifier si on a assez d'historique
            if symbol not in self.price_history or len(self.price_history[symbol]) < 3:
                return None

            recent_bars = self.price_history[symbol][-5:]  # 5 dernières bars

            # Vérifier head fake UPPER (borne haute)
            headfake_upper = self._check_upper_headfake(bracket, recent_bars, market_data)
            if headfake_upper:
                return headfake_upper

            # Vérifier head fake LOWER (borne basse)
            headfake_lower = self._check_lower_headfake(bracket, recent_bars, market_data)
            if headfake_lower:
                return headfake_lower

            return None

        except Exception as e:
            logger.error(f"❌ Erreur détection head fake: {e}")
            return None

    def _check_upper_headfake(self, bracket: Bracket, recent_bars: List[Dict],
                              market_data: Dict) -> Optional[HeadFakeSetup]:
        """Vérifie head fake sur borne haute (SHORT setup)"""

        upper_bound = bracket.upper_bound.price
        tick_size = 0.25

        # Chercher une bar avec breakout au-dessus de la borne
        for i in range(len(recent_bars) - 1, max(0, len(recent_bars) - 4), -1):
            bar = recent_bars[i]

            # Check si breakout
            high = bar['high']
            close = bar['close']
            low = bar['low']

            breakout_distance_ticks = (high - upper_bound) / tick_size

            # Doit sortir du bracket (3-10 ticks)
            if not (self.config['min_breakout_ticks'] <= breakout_distance_ticks <= self.config['max_breakout_ticks']):
                continue

            # Close doit être RETOURNÉ dans le bracket
            if close > upper_bound:
                continue  # Pas encore retourné

            # Calculer wick percent
            bar_range = high - low
            if bar_range <= 0:
                continue

            wick_size = high - max(bar['open'], close)
            wick_percent = (wick_size / bar_range) * 100

            if wick_percent < self.config['min_wick_percent']:
                continue  # Wick trop petit

            # Volume check
            avg_volume = np.mean([b['volume'] for b in recent_bars])
            volume_ratio_breakout = bar['volume'] / avg_volume if avg_volume > 0 else 1.0

            if volume_ratio_breakout > self.config['volume_threshold']:
                continue  # Volume trop élevé (pas un fake)

            # Volume au retour (bar suivante)
            if i < len(recent_bars) - 1:
                next_bar = recent_bars[i + 1]
                volume_ratio_return = next_bar['volume'] / bar['volume'] if bar['volume'] > 0 else 1.0

                if volume_ratio_return < self.config['min_volume_ratio']:
                    continue  # Pas assez de volume au retour
            else:
                volume_ratio_return = 1.0

            # DOM check
            dom_before = self._get_dom_imbalance(market_data)
            # TODO: Comparer avec DOM historique si disponible
            dom_flipped = False  # Simplification

            # Créer head fake setup
            headfake = self._create_headfake_setup(
                symbol=bracket.symbol,
                headfake_type=HeadFakeType.UPPER_REJECTION,
                bracket=bracket,
                breakout_price=high,
                breakout_distance=breakout_distance_ticks,
                return_price=close,
                wick_percent=wick_percent,
                volume_on_breakout=bar['volume'],
                volume_on_return=next_bar['volume'] if i < len(recent_bars) - 1 else bar['volume'],
                volume_ratio=volume_ratio_return,
                dom_imbalance_before=0.0,  # Simplification
                dom_imbalance_after=dom_before,
                dom_flipped=dom_flipped,
                breakout_duration_bars=1,
                time_to_return=1
            )

            # Valider qualité
            if headfake and headfake.quality_score >= self.config['min_quality_score']:
                self.headfakes_detected_today += 1
                logger.info(f"⚡ HEAD FAKE UPPER détecté: {bracket.symbol} @ {high:.2f} → {close:.2f}")
                return headfake

        return None

    def _check_lower_headfake(self, bracket: Bracket, recent_bars: List[Dict],
                              market_data: Dict) -> Optional[HeadFakeSetup]:
        """Vérifie head fake sur borne basse (LONG setup)"""

        lower_bound = bracket.lower_bound.price
        tick_size = 0.25

        # Chercher une bar avec breakout en-dessous de la borne
        for i in range(len(recent_bars) - 1, max(0, len(recent_bars) - 4), -1):
            bar = recent_bars[i]

            # Check si breakout
            low = bar['low']
            close = bar['close']
            high = bar['high']

            breakout_distance_ticks = (lower_bound - low) / tick_size

            # Doit sortir du bracket (3-10 ticks)
            if not (self.config['min_breakout_ticks'] <= breakout_distance_ticks <= self.config['max_breakout_ticks']):
                continue

            # Close doit être RETOURNÉ dans le bracket
            if close < lower_bound:
                continue  # Pas encore retourné

            # Calculer wick percent
            bar_range = high - low
            if bar_range <= 0:
                continue

            wick_size = min(bar['open'], close) - low
            wick_percent = (wick_size / bar_range) * 100

            if wick_percent < self.config['min_wick_percent']:
                continue  # Wick trop petit

            # Volume check
            avg_volume = np.mean([b['volume'] for b in recent_bars])
            volume_ratio_breakout = bar['volume'] / avg_volume if avg_volume > 0 else 1.0

            if volume_ratio_breakout > self.config['volume_threshold']:
                continue  # Volume trop élevé (pas un fake)

            # Volume au retour
            if i < len(recent_bars) - 1:
                next_bar = recent_bars[i + 1]
                volume_ratio_return = next_bar['volume'] / bar['volume'] if bar['volume'] > 0 else 1.0

                if volume_ratio_return < self.config['min_volume_ratio']:
                    continue  # Pas assez de volume au retour
            else:
                volume_ratio_return = 1.0

            # DOM check
            dom_before = self._get_dom_imbalance(market_data)
            dom_flipped = False  # Simplification

            # Créer head fake setup
            headfake = self._create_headfake_setup(
                symbol=bracket.symbol,
                headfake_type=HeadFakeType.LOWER_REJECTION,
                bracket=bracket,
                breakout_price=low,
                breakout_distance=breakout_distance_ticks,
                return_price=close,
                wick_percent=wick_percent,
                volume_on_breakout=bar['volume'],
                volume_on_return=next_bar['volume'] if i < len(recent_bars) - 1 else bar['volume'],
                volume_ratio=volume_ratio_return,
                dom_imbalance_before=0.0,
                dom_imbalance_after=dom_before,
                dom_flipped=dom_flipped,
                breakout_duration_bars=1,
                time_to_return=1
            )

            # Valider qualité
            if headfake and headfake.quality_score >= self.config['min_quality_score']:
                self.headfakes_detected_today += 1
                logger.info(f"⚡ HEAD FAKE LOWER détecté: {bracket.symbol} @ {low:.2f} → {close:.2f}")
                return headfake

        return None

    def _create_headfake_setup(self, symbol: str, headfake_type: HeadFakeType,
                               bracket: Bracket, **kwargs) -> HeadFakeSetup:
        """Crée un HeadFakeSetup complet avec calculs"""

        tick_size = 0.25

        # Calculer entry, stop, TP
        if headfake_type == HeadFakeType.UPPER_REJECTION:
            # SHORT setup
            entry_price = kwargs['return_price']
            stop_loss = bracket.upper_bound.price + (kwargs['breakout_distance'] + 2) * tick_size
            tp1 = bracket.middle_price
            tp2 = bracket.lower_bound.price
        else:
            # LONG setup
            entry_price = kwargs['return_price']
            stop_loss = bracket.lower_bound.price - (kwargs['breakout_distance'] + 2) * tick_size
            tp1 = bracket.middle_price
            tp2 = bracket.upper_bound.price

        # Calculer quality score
        quality_score = self._calculate_quality_score(
            wick_percent=kwargs['wick_percent'],
            volume_ratio=kwargs['volume_ratio'],
            breakout_distance=kwargs['breakout_distance'],
            dom_flipped=kwargs['dom_flipped']
        )

        # Déterminer strength
        if quality_score >= 0.85:
            strength = "VERY_STRONG"
        elif quality_score >= 0.75:
            strength = "STRONG"
        elif quality_score >= 0.65:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        return HeadFakeSetup(
            headfake_id=f"{symbol}_{datetime.now().strftime('%H%M%S')}",
            timestamp=datetime.now(),
            symbol=symbol,
            headfake_type=headfake_type,
            bracket_upper=bracket.upper_bound.price,
            bracket_lower=bracket.lower_bound.price,
            bracket_middle=bracket.middle_price,
            breakout_price=kwargs['breakout_price'],
            breakout_distance=kwargs['breakout_distance'],
            return_price=kwargs['return_price'],
            wick_percent=kwargs['wick_percent'],
            volume_on_breakout=kwargs['volume_on_breakout'],
            volume_on_return=kwargs['volume_on_return'],
            volume_ratio=kwargs['volume_ratio'],
            dom_imbalance_before=kwargs['dom_imbalance_before'],
            dom_imbalance_after=kwargs['dom_imbalance_after'],
            dom_flipped=kwargs['dom_flipped'],
            breakout_duration_bars=kwargs['breakout_duration_bars'],
            time_to_return=kwargs['time_to_return'],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            quality_score=quality_score,
            confidence=min(quality_score * 1.15, 1.0),
            setup_strength=strength
        )

    def _calculate_quality_score(self, wick_percent: float, volume_ratio: float,
                                  breakout_distance: float, dom_flipped: bool) -> float:
        """Calcule le score de qualité du head fake"""
        score = 0.0

        # Wick size (0.4 points max)
        wick_score = min(wick_percent / 80, 1.0)  # 80% = parfait
        score += wick_score * 0.4

        # Volume ratio (0.3 points max)
        volume_score = min((volume_ratio - 1.0) / 1.0, 1.0)  # 2.0 = parfait
        score += volume_score * 0.3

        # Breakout distance (0.2 points)
        # Plus c'est petit, mieux c'est (moins ils sont allés loin)
        distance_score = 1.0 - min(breakout_distance / 10, 1.0)
        score += distance_score * 0.2

        # DOM flip (0.1 points)
        if dom_flipped:
            score += 0.1

        return min(score, 1.0)

    def _get_dom_imbalance(self, market_data: Dict) -> float:
        """Calcule le déséquilibre DOM"""
        try:
            bid_depth = sum([market_data.get(f'dom_bid_{i}', 0) for i in range(1, 11)])
            ask_depth = sum([market_data.get(f'dom_ask_{i}', 0) for i in range(1, 11)])

            total = bid_depth + ask_depth
            if total == 0:
                return 0.0

            return (bid_depth - ask_depth) / total

        except Exception:
            return 0.0

    def create_signal_from_headfake(self, headfake: HeadFakeSetup) -> Dict:
        """Crée un signal de trading à partir d'un head fake"""

        direction = "SHORT" if headfake.headfake_type == HeadFakeType.UPPER_REJECTION else "LONG"

        return {
            'strategy': 'headfake',
            'setup_type': 'HEAD_FAKE_' + headfake.headfake_type.value.upper(),
            'symbol': headfake.symbol,
            'action': direction,
            'entry_price': headfake.entry_price,
            'stop_loss': headfake.stop_loss,
            'take_profit_1': headfake.take_profit_1,
            'take_profit_2': headfake.take_profit_2,
            'quality_score': headfake.quality_score,
            'confidence': headfake.confidence,
            'setup_strength': headfake.setup_strength,
            'wick_percent': headfake.wick_percent,
            'volume_ratio': headfake.volume_ratio,
            'breakout_distance': headfake.breakout_distance,
            'rr_ratio': abs(headfake.take_profit_1 - headfake.entry_price) / abs(headfake.stop_loss - headfake.entry_price)
        }


# === FACTORY ===

def create_headfake_detector(config: Optional[Dict] = None) -> HeadFakeDetector:
    """Factory pour créer un HeadFakeDetector"""
    return HeadFakeDetector(config)


# === EXPORTS ===

__all__ = [
    'HeadFakeType',
    'HeadFakeSetup',
    'HeadFakeDetector',
    'create_headfake_detector'
]
