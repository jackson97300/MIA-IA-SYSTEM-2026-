"""
strategies/pvwap_magnetic_bounce.py

PVWAP MAGNETIC LEVELS
Prior VWAP bands comme support/resistance magnétiques

Version: 1.0 ML_READY
Date: 18 Novembre 2025
Win Rate attendu: 55-60%
Fréquence: 3-8 setups/jour
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PatternSignal:
    """Signal généré"""
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0


class PVWAPMagneticBounce:
    """
    PVWAP MAGNETIC LEVELS

    Prior VWAP (PVWAP) et ses bands = niveaux institutionnels

    Triggers:
    - Prix à < 50 ticks de PVWAP_DN1 ou PVWAP_UP1
    - Rejection candle (wick >= 3 ticks)
    - OrderFlow flip (delta change)

    Entry: @ rejection
    SL: 30-40 ticks de l'autre côté
    TP1: PVWAP (mean)
    TP2: PVWAP opposite band
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.name = "pvwap_magnetic_bounce"  # ✅ FIX 21/11 02:20: Ajout nom stratégie

        # Paramètres
        self.max_distance_ticks = {
            'ES': 50,   # Max 50 ticks du band
            'NQ': 80,   # Max 80 ticks du band
            'RTY': 40
        }

        self.min_rejection_wick_ticks = 3
        self.sl_ticks = 35

        # Cooldown
        self.last_signal_time = {}
        self.cooldown_seconds = 120  # 2 minutes

        # Stats
        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0,
            'pvwap_dn1_bounces': 0,
            'pvwap_up1_bounces': 0
        }

        logger.info("✅ PVWAPMagneticBounce initialisée")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Détecte bounces sur PVWAP bands
        """
        start_time = time.perf_counter()

        try:
            symbol = ml_data.get('symbol', 'UNKNOWN')
            if symbol not in ['ES', 'NQ', 'RTY']:
                return None

            # PVWAP levels
            pvwap = ml_data.get('pvwap', 0)
            pvwap_up1 = ml_data.get('pvwap_up1', 0)
            pvwap_dn1 = ml_data.get('pvwap_dn1', 0)

            if pvwap == 0 or pvwap_up1 == 0 or pvwap_dn1 == 0:
                return None

            mid_price = ml_data.get('mid', 0)
            high = ml_data.get('high', mid_price)
            low = ml_data.get('low', mid_price)
            close = ml_data.get('close', mid_price)
            open_price = ml_data.get('open', close)

            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # Cooldown
            current_time = time.time()
            if symbol in self.last_signal_time:
                if current_time - self.last_signal_time[symbol] < self.cooldown_seconds:
                    return None

            max_dist = self.max_distance_ticks.get(symbol, 50)

            # ═══════════════════════════════════════════════════════════
            # CHECK PVWAP_DN1 BOUNCE (LONG)
            # ═══════════════════════════════════════════════════════════

            dist_to_dn1 = abs(mid_price - pvwap_dn1) / tick_size

            if dist_to_dn1 <= max_dist:
                # Proche de PVWAP_DN1 (support)

                # Vérifier rejection
                wick_bottom = (min(close, open_price) - low) / tick_size
                low_near_dn1 = abs(low - pvwap_dn1) / tick_size <= 10
                close_above_dn1 = close > pvwap_dn1
                wick_ok = wick_bottom >= self.min_rejection_wick_ticks

                # OrderFlow flip check
                delta = ml_data.get('delta', 0)
                imbalance = ml_data.get('level1_imbalance', 0)
                orderflow_improving = (delta >= -10) or (imbalance >= -0.25)

                if low_near_dn1 and close_above_dn1 and wick_ok and orderflow_improving:
                    # LONG signal
                    direction = "LONG"
                    level_name = "PVWAP_DN1"

                    entry_price = mid_price
                    stop_price = pvwap_dn1 - (self.sl_ticks * tick_size)
                    target1 = pvwap  # Mean reversion
                    target2 = pvwap_up1  # Opposite band

                    confidence = 0.60

                    # Bonus si wick très prononcé
                    if wick_bottom >= 5:
                        confidence += 0.05

                    # Bonus si orderflow clairement positif
                    if delta > 5:
                        confidence += 0.05

                    self.stats['pvwap_dn1_bounces'] += 1

                    logger.info(f"🟢 [{symbol}] PVWAP_DN1 BOUNCE détecté @ {pvwap_dn1:.2f}")
                    logger.info(f"   Distance: {dist_to_dn1:.1f}t | Wick: {wick_bottom:.1f}t")

                    # Generate signal
                    self.last_signal_time[symbol] = current_time
                    self.stats['signals_generated'] += 1
                    self.stats['long_signals'] += 1

                    processing_time_ms = (time.perf_counter() - start_time) * 1000

                    logger.info(f"🎯 [{symbol}] PVWAP MAGNETIC: {direction} @ {entry_price:.2f}")
                    logger.info(f"   Level: {level_name} ({pvwap_dn1:.2f})")
                    logger.info(f"   SL: {stop_price:.2f} | TP1: {target1:.2f} | TP2: {target2:.2f}")

                    return PatternSignal(
                        strategy="pvwap_magnetic_bounce",
                        timestamp=datetime.now(),
                        side=direction,
                        confidence=confidence,
                        entry=entry_price,
                        stop=stop_price,
                        targets=[target1, target2],
                        metadata={
                            'level_name': level_name,
                            'level_price': pvwap_dn1,
                            'distance_ticks': dist_to_dn1,
                            'wick_size_ticks': wick_bottom,
                            'delta': delta,
                            'imbalance': imbalance
                        },
                        processing_time_ms=processing_time_ms
                    )

            # ═══════════════════════════════════════════════════════════
            # CHECK PVWAP_UP1 BOUNCE (SHORT)
            # ═══════════════════════════════════════════════════════════

            dist_to_up1 = abs(mid_price - pvwap_up1) / tick_size

            if dist_to_up1 <= max_dist:
                # Proche de PVWAP_UP1 (resistance)

                wick_top = (high - max(close, open_price)) / tick_size
                high_near_up1 = abs(high - pvwap_up1) / tick_size <= 10
                close_below_up1 = close < pvwap_up1
                wick_ok = wick_top >= self.min_rejection_wick_ticks

                delta = ml_data.get('delta', 0)
                imbalance = ml_data.get('level1_imbalance', 0)
                orderflow_worsening = (delta <= 10) or (imbalance <= 0.25)

                if high_near_up1 and close_below_up1 and wick_ok and orderflow_worsening:
                    # SHORT signal
                    direction = "SHORT"
                    level_name = "PVWAP_UP1"

                    entry_price = mid_price
                    stop_price = pvwap_up1 + (self.sl_ticks * tick_size)
                    target1 = pvwap
                    target2 = pvwap_dn1

                    confidence = 0.60

                    if wick_top >= 5:
                        confidence += 0.05
                    if delta < -5:
                        confidence += 0.05

                    self.stats['pvwap_up1_bounces'] += 1

                    logger.info(f"🔴 [{symbol}] PVWAP_UP1 BOUNCE détecté @ {pvwap_up1:.2f}")
                    logger.info(f"   Distance: {dist_to_up1:.1f}t | Wick: {wick_top:.1f}t")

                    self.last_signal_time[symbol] = current_time
                    self.stats['signals_generated'] += 1
                    self.stats['short_signals'] += 1

                    processing_time_ms = (time.perf_counter() - start_time) * 1000

                    logger.info(f"🎯 [{symbol}] PVWAP MAGNETIC: {direction} @ {entry_price:.2f}")
                    logger.info(f"   Level: {level_name} ({pvwap_up1:.2f})")
                    logger.info(f"   SL: {stop_price:.2f} | TP1: {target1:.2f} | TP2: {target2:.2f}")

                    return PatternSignal(
                        strategy="pvwap_magnetic_bounce",
                        timestamp=datetime.now(),
                        side=direction,
                        confidence=confidence,
                        entry=entry_price,
                        stop=stop_price,
                        targets=[target1, target2],
                        metadata={
                            'level_name': level_name,
                            'level_price': pvwap_up1,
                            'distance_ticks': dist_to_up1,
                            'wick_size_ticks': wick_top,
                            'delta': delta,
                            'imbalance': imbalance
                        },
                        processing_time_ms=processing_time_ms
                    )

            return None

        except Exception as e:
            logger.error(f"❌ Erreur PVWAPMagneticBounce: {e}")
            return None
