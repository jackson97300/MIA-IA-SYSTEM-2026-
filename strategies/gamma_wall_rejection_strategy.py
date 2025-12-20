"""
strategies/gamma_wall_rejection_strategy.py

GAMMA WALL REJECTION - Tier 1 Strategy
Exploite les rejets de prix sur les gamma walls (Call Resistance / Put Support)

Version: 1.0 ML_READY
Date: 12 Novembre 2025
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


class GammaWallRejectionStrategy:
    """
    GAMMA WALL REJECTION (Tier 1)

    Détecte les rejets sur Call Resistance (SHORT) et Put Support (LONG)

    Triggers depuis ML_READY:
    - Prix proche gamma wall (<= 5 ticks)
    - Force gamma wall >= 0.25
    - Bougie de rejet (range >= 3 ticks, close opposé au wall)
    - Volume spike (> 1.5x moyenne)

    Entry: Market @ rejection
    SL: De l'autre côté du wall (5-8 ticks)
    TP1: 10 ticks
    TP2: 20 ticks
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.name = "gamma_wall_rejection"  # ✅ FIX 21/11 02:20: Ajout nom stratégie
        # 🔥 FIX 21/11 13:50: Augmenté à 12 ticks pour détecter plus de rejets
        self.max_distance_ticks = self.config.get('max_distance_ticks', 12)  # FIX 21/11 (was 8)
        self.min_wall_strength = self.config.get('min_wall_strength', 0.20)  # FIX 21/11 (was 0.25)
        self.min_rejection_range_ticks = self.config.get('min_rejection_range_ticks', 2)  # FIX 21/11 (was 3)
        self.volume_spike_threshold = self.config.get('volume_spike_threshold', 1.3)  # FIX 21/11 (was 1.5)
        self.sl_ticks = self.config.get('sl_ticks', 7)

        # Cooldown pour éviter spam de signaux
        self.last_signal_time = {}  # {symbol: timestamp}
        # 🔥 MODE CALIBRAGE (18/11/2025): Cooldown réduit de 60 à 45 secondes
        self.cooldown_seconds = self.config.get('cooldown_seconds', 45)  # MODE CALIBRAGE (was 60)

        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0,
            'rejections_detected': 0,
            'rejections_call': 0,
            'rejections_put': 0
        }

        logger.info("✅ GammaWallRejectionStrategy initialisé (Tier 1)")
        logger.info(f"   Max distance: {self.max_distance_ticks} ticks")
        logger.info(f"   Min wall strength: {self.min_wall_strength}")
        logger.info(f"   Min rejection range: {self.min_rejection_range_ticks} ticks")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        🔥 Analyse depuis ML_READY - Détection rejection gamma wall

        Args:
            ml_data: Dict ML_READY complet

        Returns:
            PatternSignal ou None
        """
        start_time = time.perf_counter()

        try:
            # === LIRE ML_READY ===
            symbol = ml_data.get('symbol', 'UNKNOWN')
            mid_price = ml_data.get('mid', 0)
            close_price = ml_data.get('close', mid_price)
            open_price = ml_data.get('open', close_price)  # Fallback to close si absent
            high_price = ml_data.get('high', 0)
            low_price = ml_data.get('low', 0)

            call_resistance = ml_data.get('call_resistance', 0)
            put_support = ml_data.get('put_support', 0)

            volume = ml_data.get('volume', 0)
            avg_volume = ml_data.get('avg_volume', 0)

            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # Vérifier cooldown
            current_time = time.time()
            if symbol in self.last_signal_time:
                time_since_last = current_time - self.last_signal_time[symbol]
                if time_since_last < self.cooldown_seconds:
                    return None

            # ═══════════════════════════════════════════════════════════════
            # 🔍 DÉTECTION REJET CALL RESISTANCE (SHORT)
            # ═══════════════════════════════════════════════════════════════
            rejection_call = False
            if call_resistance > 0:
                dist_to_call = abs(mid_price - call_resistance) / tick_size

                if dist_to_call <= self.max_distance_ticks:
                    # Vérifier bougie de rejet
                    candle_range = (high_price - low_price) / tick_size
                    wick_top = (high_price - max(close_price, open_price)) / tick_size
                    body_size = abs(close_price - open_price) / tick_size

                    # Conditions rejet CALL (SHORT):
                    # 1. High proche call resistance (< 5 ticks) - FIX 21/11: Assoupli de 3 → 5
                    # 2. Close loin du high (wick top >= 1.5 ticks) - FIX 21/11: Assoupli de 2 → 1.5
                    # 3. Range suffisant (>= 2 ticks) - FIX 21/11: Assoupli de 3 → 2
                    high_near_call = abs(high_price - call_resistance) / tick_size <= 5  # FIX 21/11
                    wick_rejection = wick_top >= 1.5  # FIX 21/11
                    range_sufficient = candle_range >= self.min_rejection_range_ticks

                    if high_near_call and wick_rejection and range_sufficient:
                        rejection_call = True
                        self.stats['rejections_call'] += 1
                        logger.info(f"🔴 [{symbol}] Call Resistance REJECTION détectée @ {call_resistance:.2f}")
                        logger.info(f"   High: {high_price:.2f} | Close: {close_price:.2f} | Wick: {wick_top:.1f}t")

            # ═══════════════════════════════════════════════════════════════
            # 🔍 DÉTECTION REJET PUT SUPPORT (LONG)
            # ═══════════════════════════════════════════════════════════════
            rejection_put = False
            if put_support > 0:
                dist_to_put = abs(mid_price - put_support) / tick_size

                if dist_to_put <= self.max_distance_ticks:
                    # Vérifier bougie de rejet
                    candle_range = (high_price - low_price) / tick_size
                    wick_bottom = (min(close_price, open_price) - low_price) / tick_size

                    # Conditions rejet PUT (LONG):
                    # 1. Low proche put support (< 5 ticks) - FIX 21/11: Assoupli de 3 → 5
                    # 2. Close loin du low (wick bottom >= 1.5 ticks) - FIX 21/11: Assoupli de 2 → 1.5
                    # 3. Range suffisant (>= 2 ticks) - FIX 21/11: Assoupli de 3 → 2
                    low_near_put = abs(low_price - put_support) / tick_size <= 5  # FIX 21/11
                    wick_rejection = wick_bottom >= 1.5  # FIX 21/11
                    range_sufficient = candle_range >= self.min_rejection_range_ticks

                    if low_near_put and wick_rejection and range_sufficient:
                        rejection_put = True
                        self.stats['rejections_put'] += 1
                        logger.info(f"🟢 [{symbol}] Put Support REJECTION détectée @ {put_support:.2f}")
                        logger.info(f"   Low: {low_price:.2f} | Close: {close_price:.2f} | Wick: {wick_bottom:.1f}t")

            # ═══════════════════════════════════════════════════════════════
            # 🎯 GÉNÉRER SIGNAL SI REJET DÉTECTÉ
            # ═══════════════════════════════════════════════════════════════
            if not rejection_call and not rejection_put:
                return None

            # Vérifier volume spike (optionnel)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            has_volume_spike = volume_ratio >= self.volume_spike_threshold

            # Décider direction
            if rejection_call:
                side = "SHORT"
                entry_price = mid_price
                stop_price = call_resistance + (self.sl_ticks * tick_size)
                target1 = entry_price - (10 * tick_size)
                target2 = entry_price - (20 * tick_size)
                wall_price = call_resistance
                wall_type = "Call Resistance"
            elif rejection_put:
                side = "LONG"
                entry_price = mid_price
                stop_price = put_support - (self.sl_ticks * tick_size)
                target1 = entry_price + (10 * tick_size)
                target2 = entry_price + (20 * tick_size)
                wall_price = put_support
                wall_type = "Put Support"

            # Calculer confidence
            base_confidence = 0.70

            # Bonus volume spike
            if has_volume_spike:
                base_confidence += 0.10

            # Bonus range important
            if candle_range >= 5:
                base_confidence += 0.05

            confidence = min(base_confidence, 0.95)

            # Enregistrer dernière signal time
            self.last_signal_time[symbol] = current_time

            # Stats
            self.stats['signals_generated'] += 1
            if side == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(f"🎯 [{symbol}] GAMMA WALL REJECTION: {side} @ {entry_price:.2f}")
            logger.info(f"   Wall: {wall_type} @ {wall_price:.2f}")
            logger.info(f"   Confidence: {confidence:.2f} | Volume ratio: {volume_ratio:.2f}x")
            logger.info(f"   SL: {stop_price:.2f} | TP1: {target1:.2f} | TP2: {target2:.2f}")

            return PatternSignal(
                strategy="gamma_wall_rejection",
                timestamp=datetime.now(),
                side=side,
                confidence=confidence,
                entry=entry_price,
                stop=stop_price,
                targets=[target1, target2],
                metadata={
                    'wall_type': wall_type,
                    'wall_price': wall_price,
                    'distance_ticks': dist_to_call if rejection_call else dist_to_put,
                    'candle_range_ticks': candle_range,
                    'volume_ratio': volume_ratio,
                    'volume_spike': has_volume_spike
                },
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"❌ Erreur GammaWallRejectionStrategy: {e}")
            return None
