"""
strategies/initial_balance_breakout.py

INITIAL BALANCE BREAKOUT/RETEST
Exploite les breakouts et retests de l'Initial Balance (first hour range)

Version: 1.0 ML_READY
Date: 18 Novembre 2025
Win Rate attendu: 60-65%
Fréquence: 1-3 setups/jour
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


class InitialBalanceBreakout:
    """
    INITIAL BALANCE BREAKOUT/RETEST

    IB = Range de la première heure (typiquement 09:30-10:30 ET)
    Setup classique institutionnel

    Triggers:
    - Prix break IB High ou IB Low
    - Reteste le niveau dans les 30-60 min
    - Rejection confirmée (wick, volume)

    Entry: @ rejection candle close
    SL: 30 ticks de l'autre côté
    TP1: Middle IB (50% range)
    TP2: Opposite IB level (full range)
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.name = "initial_balance_breakout"  # ✅ FIX 21/11 02:20: Ajout nom stratégie

        # Paramètres
        self.min_ib_range_ticks = {
            'ES': 30,   # 30 ticks = 7.5 pts minimum
            'NQ': 50,   # 50 ticks = 12.5 pts minimum
            'RTY': 40
        }

        self.max_retest_distance_ticks = 10  # Max 10 ticks du niveau
        self.min_rejection_wick_ticks = 3     # Minimum 3 ticks de mèche
        self.sl_ticks = 30

        # Track breakouts
        self.breakout_tracker = {}  # {symbol: {'side': 'high'/'low', 'time': timestamp}}
        self.retest_window_seconds = 1800  # 30 minutes

        # Cooldown
        self.last_signal_time = {}
        self.cooldown_seconds = 600  # 10 minutes

        # Stats
        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0,
            'ib_high_retests': 0,
            'ib_low_retests': 0
        }

        logger.info("✅ InitialBalanceBreakout initialisée")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Détecte breakout/retest IB
        """
        start_time = time.perf_counter()

        try:
            symbol = ml_data.get('symbol', 'UNKNOWN')
            if symbol not in ['ES', 'NQ', 'RTY']:
                return None

            # Vérifier structure disponible
            structure = ml_data.get('structure', {})
            if not structure:
                return None

            ibh = structure.get('ibh', 0)
            ibl = structure.get('ibl', 0)

            if ibh == 0 or ibl == 0:
                return None

            mid_price = ml_data.get('mid', 0)
            high = ml_data.get('high', mid_price)
            low = ml_data.get('low', mid_price)
            close = ml_data.get('close', mid_price)

            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # Vérifier IB range suffisant
            ib_range_ticks = (ibh - ibl) / tick_size
            min_range = self.min_ib_range_ticks.get(symbol, 30)

            if ib_range_ticks < min_range:
                return None

            # Cooldown
            current_time = time.time()
            if symbol in self.last_signal_time:
                if current_time - self.last_signal_time[symbol] < self.cooldown_seconds:
                    return None

            # ═══════════════════════════════════════════════════════════
            # DÉTECTER BREAKOUT
            # ═══════════════════════════════════════════════════════════

            # Breakout IB High
            if close > ibh and symbol not in self.breakout_tracker:
                self.breakout_tracker[symbol] = {
                    'side': 'high',
                    'time': current_time,
                    'level': ibh
                }
                logger.info(f"📈 [{symbol}] IB HIGH breakout @ {close:.2f} (IB: {ibh:.2f})")

            # Breakout IB Low
            elif close < ibl and symbol not in self.breakout_tracker:
                self.breakout_tracker[symbol] = {
                    'side': 'low',
                    'time': current_time,
                    'level': ibl
                }
                logger.info(f"📉 [{symbol}] IB LOW breakout @ {close:.2f} (IB: {ibl:.2f})")

            # ═══════════════════════════════════════════════════════════
            # DÉTECTER RETEST
            # ═══════════════════════════════════════════════════════════

            if symbol not in self.breakout_tracker:
                return None

            breakout = self.breakout_tracker[symbol]
            time_since_breakout = current_time - breakout['time']

            # Vérifier dans fenêtre retest
            if time_since_breakout > self.retest_window_seconds:
                # Trop tard, reset
                del self.breakout_tracker[symbol]
                return None

            level = breakout['level']
            distance_to_level = abs(mid_price - level) / tick_size

            # Pas encore assez proche
            if distance_to_level > self.max_retest_distance_ticks:
                return None

            # ═══════════════════════════════════════════════════════════
            # VÉRIFIER REJECTION
            # ═══════════════════════════════════════════════════════════

            signal_generated = False
            direction = None

            if breakout['side'] == 'high':
                # Breakout high, cherche retest + rejection = LONG
                # Prix doit avoir testé ibh et rejeté vers haut
                wick_top = (high - max(close, ml_data.get('open', close))) / tick_size

                # Conditions:
                # 1. High proche de ibh
                # 2. Close au-dessus de ibh (rejection confirmée)
                # 3. Wick top >= 3 ticks

                high_near_ib = abs(high - ibh) / tick_size <= 5
                close_above = close > ibh
                wick_ok = wick_top >= self.min_rejection_wick_ticks

                if high_near_ib and close_above and wick_ok:
                    direction = "LONG"
                    signal_generated = True
                    self.stats['ib_high_retests'] += 1
                    logger.info(f"✅ [{symbol}] IB HIGH retest + rejection (LONG)")

            elif breakout['side'] == 'low':
                # Breakout low, cherche retest + rejection = SHORT
                wick_bottom = (min(close, ml_data.get('open', close)) - low) / tick_size

                low_near_ib = abs(low - ibl) / tick_size <= 5
                close_below = close < ibl
                wick_ok = wick_bottom >= self.min_rejection_wick_ticks

                if low_near_ib and close_below and wick_ok:
                    direction = "SHORT"
                    signal_generated = True
                    self.stats['ib_low_retests'] += 1
                    logger.info(f"✅ [{symbol}] IB LOW retest + rejection (SHORT)")

            if not signal_generated:
                return None

            # ═══════════════════════════════════════════════════════════
            # GÉNÉRER SIGNAL
            # ═══════════════════════════════════════════════════════════

            entry_price = mid_price
            ib_middle = (ibh + ibl) / 2

            if direction == "LONG":
                stop_price = level - (self.sl_ticks * tick_size)
                target1 = ib_middle
                target2 = ibl  # Full range
            else:  # SHORT
                stop_price = level + (self.sl_ticks * tick_size)
                target1 = ib_middle
                target2 = ibh  # Full range

            # Confidence basée sur:
            # - Timing (plus tôt = mieux)
            # - IB range (plus large = mieux)
            base_confidence = 0.65

            # Bonus si retest rapide (<15 min)
            if time_since_breakout < 900:
                base_confidence += 0.05

            # Bonus si IB range large
            if ib_range_ticks > min_range * 1.5:
                base_confidence += 0.05

            confidence = min(base_confidence, 0.75)

            # Cleanup
            del self.breakout_tracker[symbol]
            self.last_signal_time[symbol] = current_time

            # Stats
            self.stats['signals_generated'] += 1
            if direction == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(f"🎯 [{symbol}] IB BREAKOUT/RETEST: {direction} @ {entry_price:.2f}")
            logger.info(f"   IB Range: {ibl:.2f} - {ibh:.2f} ({ib_range_ticks:.0f}t)")
            logger.info(f"   Confidence: {confidence:.2f}")
            logger.info(f"   SL: {stop_price:.2f} | TP1: {target1:.2f} | TP2: {target2:.2f}")

            return PatternSignal(
                strategy="initial_balance_breakout",
                timestamp=datetime.now(),
                side=direction,
                confidence=confidence,
                entry=entry_price,
                stop=stop_price,
                targets=[target1, target2],
                metadata={
                    'ibh': ibh,
                    'ibl': ibl,
                    'ib_range_ticks': ib_range_ticks,
                    'breakout_side': breakout['side'],
                    'time_since_breakout_sec': time_since_breakout
                },
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"❌ Erreur InitialBalanceBreakout: {e}")
            return None
