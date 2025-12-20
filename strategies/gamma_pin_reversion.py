"""
strategies/gamma_pin_reversion.py

GAMMA PIN REVERSION - Tier 1 Strategy
Exploite les reversals sur pins gamma (niveaux d'options densément négociés)

Version: 1.0 ML_READY
Date: 31 Octobre 2025
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PatternSignal:
    """Signal généré par une stratégie de pattern"""
    strategy: str
    timestamp: datetime
    side: Optional[str]  # LONG, SHORT, None
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0


class GammaPinReversion:
    """
    GAMMA PIN REVERSION (Tier 1)

    Triggers depuis ML_READY :
    - gamma_pin_strength >= 0.70
    - distance_gamma_pin_pct <= 0.12%
    - flip level1_imbalance vers le pin

    SL : pin ± 6-8 ticks
    TP1 : VWAP
    TP2 : ± SD1
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.pin_strength_threshold = self.config.get('pin_strength_threshold', 0.70)
        self.max_distance_pct = self.config.get('max_distance_pct', 0.12)
        self.sl_ticks = self.config.get('sl_ticks', 7)  # 6-8 ticks

        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0
        }

        logger.info("✅ GammaPinReversion initialisé (Tier 1)")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        🔥 Analyse depuis ML_READY - VERSION CORRIGÉE

        Calcule gamma_pin_strength et distance depuis les features disponibles

        Args:
            ml_data: Dict ML_READY complet

        Returns:
            PatternSignal ou None
        """
        start_time = time.perf_counter()

        try:
            # === LIRE ML_READY ===
            mid_price = ml_data.get('mid', 0)
            gamma_wall = ml_data.get('gamma_wall_level', 0)
            gamma_side_str = ml_data.get('gamma_side', 'unknown')  # "above" ou "below"
            imbalance = ml_data.get('level1_imbalance', 0.0)

            vwap = ml_data.get('vwap', mid_price)
            atr = ml_data.get('atr', 1.0)

            # 📚 Bible MenthorQ v2.0: Récupérer 1d_max/1d_min (Expected Move)
            day_max = ml_data.get('1d_max', 0)
            day_min = ml_data.get('1d_min', 0)

            # ✅ CORRECTIF: Calculer gamma_pin_strength depuis gamma_wall et price
            # Plus on est proche du gamma_wall, plus le pin est fort
            # 📚 Bible MenthorQ v2.0: Enrichir avec wall strength si disponible
            if gamma_wall == 0:
                return None

            distance_to_wall = abs(mid_price - gamma_wall)
            distance_pct = (distance_to_wall / mid_price) * 100 if mid_price > 0 else 999

            # 📚 Calculer position dans 1-Day range
            if day_max and day_min and mid_price and day_max > day_min:
                day_range = day_max - day_min
                position_pct = ((mid_price - day_min) / day_range) * 100
                near_1d_max = (position_pct >= 90)
                near_1d_min = (position_pct <= 10)
            else:
                near_1d_max = False
                near_1d_min = False
                position_pct = None
                day_range = None

            # Pin strength basé sur la proximité (inversé: plus proche = plus fort)
            # Max strength = 1.0 quand distance = 0, min = 0.0 quand distance > 1%
            base_pin_strength = max(0.0, 1.0 - (distance_pct / 1.0))

            # 📚 ENRICHISSEMENT BIBLE MENTHORQ: Pondérer par wall strength si disponible
            next_wall = ml_data.get('next_wall', {})
            wall_strength = next_wall.get('strength', 0.5) if isinstance(next_wall, dict) else 0.5

            # Pin strength final = proximité × force du wall
            pin_strength = base_pin_strength * (0.5 + (wall_strength * 0.5))  # Pondéré 50/50

            logger.info(f"📚 Pin Strength: base={base_pin_strength:.3f}, wall_strength={wall_strength:.3f}, final={pin_strength:.3f}")

            # 📚 Log 1-Day position
            if position_pct is not None:
                logger.info(f"📊 1-Day Position: {position_pct:.1f}% (near_max={near_1d_max}, near_min={near_1d_min})")

            # === VÉRIFIER TRIGGERS ===
            # Seuil réduit de 0.70 à 0.50 pour générer plus de signaux
            if pin_strength < 0.50:
                return None

            # Distance max augmentée de 0.12% à 0.25% (plus permissif)
            if distance_pct > 0.25:
                return None

            # Déterminer side depuis gamma_side et imbalance
            # 📚 BIBLE MENTHORQ V2.0 - CORRECTION CRITIQUE:
            # - gamma_side = "above" → Prix AU-DESSUS du gamma max → POSITIVE GAMMA (mean-revert) → BULLISH
            # - gamma_side = "below" → Prix AU-DESSOUS du gamma max → NEGATIVE GAMMA (directionnel) → BEARISH

            logger.info("📚 Bible MenthorQ v2.0: Analyse gamma_side")
            logger.info(f"   gamma_side={gamma_side_str}, imbalance={imbalance:.3f}")

            if gamma_side_str == 'above' and imbalance > 0.08:
                # ✅ CORRIGÉ: Prix au-dessus gamma = POSITIVE GAMMA (mean-revert) = BULLISH
                side = "LONG"
                pin_side = 'bullish_reversion'
                logger.info("   ✅ Régime POSITIVE GAMMA (above) + imbalance bullish → LONG")
            elif gamma_side_str == 'below' and imbalance < -0.08:
                # ✅ CORRIGÉ: Prix au-dessous gamma = NEGATIVE GAMMA (directionnel) = BEARISH
                side = "SHORT"
                pin_side = 'bearish_directional'
                logger.info("   ✅ Régime NEGATIVE GAMMA (below) + imbalance bearish → SHORT")
            else:
                logger.info(f"   ❌ Pas de confluence claire (gamma_side={gamma_side_str}, imb={imbalance:.3f})")
                return None  # Pas de confluence claire

            # === CALCUL ENTRY/STOP/TARGETS ===
            entry = mid_price

            # Tick size dynamique
            symbol = ml_data.get('sym', 'NQ')
            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # SL basé sur ATR (1.5x ATR minimum 8 ticks)
            sl_ticks = max(int(atr * 1.5 / tick_size), 8)

            if side == "LONG":
                stop = entry - (sl_ticks * tick_size)
                tp1 = vwap
                tp2 = vwap + (atr * 1.0)
            else:  # SHORT
                stop = entry + (sl_ticks * tick_size)
                tp1 = vwap
                tp2 = vwap - (atr * 1.0)

            # Confidence
            confidence = pin_strength * 0.95  # Base confidence from pin strength

            # 📚 Ajuster confidence si près des extremes (Bible MenthorQ v2.0)
            if near_1d_max and side == "LONG":
                confidence *= 0.9  # -10% si LONG près 1d_max (risque reversal)
                logger.info(f"   ⚠️ LONG près 1d_max → confidence ×0.9")
            elif near_1d_min and side == "SHORT":
                confidence *= 0.9  # -10% si SHORT près 1d_min (risque reversal)
                logger.info(f"   ⚠️ SHORT près 1d_min → confidence ×0.9")

            # === SIGNAL ===
            signal = PatternSignal(
                strategy="gamma_pin_reversion",
                timestamp=datetime.now(),
                side=side,
                confidence=confidence,
                entry=entry,
                stop=stop,
                targets=[tp1, tp2],
                metadata={
                    'pin_strength': float(pin_strength),
                    'distance_to_wall': float(distance_to_wall),
                    'distance_pct': float(distance_pct),
                    'gamma_side': gamma_side_str,
                    'imbalance': float(imbalance),
                    'pin_side': pin_side,
                    # 📚 Bible MenthorQ v2.0: 1-Day Max/Min
                    '1d_max': float(day_max) if day_max else None,
                    '1d_min': float(day_min) if day_min else None,
                    '1d_position_pct': float(position_pct) if position_pct is not None else None,
                    'near_1d_max': near_1d_max,
                    'near_1d_min': near_1d_min,
                    '1d_range': float(day_range) if day_range else None,
                    'gamma_wall': gamma_wall,
                    'atr': atr,
                    'sl_ticks': sl_ticks,
                    'source': 'ML_READY',
                    'validation': 'GAMMA_PIN_CALCULATED'
                },
                processing_time_ms=(time.perf_counter() - start_time) * 1000
            )

            self.stats['signals_generated'] += 1
            if side == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            logger.info(f"✅ GammaPinReversion: {side} @ {entry:.2f} (pin_strength={pin_strength:.3f}, dist={distance_pct:.2f}%)")

            return signal

        except Exception as e:
            logger.error(f"❌ Erreur GammaPinReversion: {e}")
            return None

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return self.stats.copy()
