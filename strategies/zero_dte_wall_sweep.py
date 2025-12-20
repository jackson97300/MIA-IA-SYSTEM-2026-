"""
strategies/zero_dte_wall_sweep.py

ZERO DTE WALL SWEEP REVERSAL - Tier 1 Strategy
Reversal sur mur 0DTE avec sweep raté + blind spot

Version: 1.0 ML_READY
Date: 31 Octobre 2025
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)


# === HELPER FUNCTION: Volume Adaptif par Session/Symbole ===
def _volume_is_high(ml_data: Dict[str, Any]) -> bool:
    """Détermine si le volume est élevé selon la session et le symbole."""
    vol = ml_data.get('volume', 0)
    sess = ml_data.get('session_id', 'US')
    sym = (ml_data.get('sym', '') or '').upper()
    base = 35 if sess == 'Asia' else (45 if sess == 'EU' else 55)
    if 'NQ' in sym: base -= 3
    if 'RTY' in sym: base -= 5
    if ml_data.get('tick_rate_1s', 0) >= 1 or ml_data.get('trade_rate_1s', 0) >= 1:
        return vol >= base
    return vol >= (base + 5)

@dataclass
class PatternSignal:
    """Signal généré par une stratégie de pattern"""
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0


class ZeroDTEWallSweepReversal:
    """
    ZERO DTE WALL SWEEP REVERSAL (Tier 1)

    Triggers depuis ML_READY :
    - next_wall.dist_ticks <= 8-12
    - sweep raté (mèche + climax vol)
    - blind_spot derrière mur
    - flip imbalance

    SL : au-delà du mur + 2-3 ticks
    TP1 : VWAP
    TP2 : VA / Wall opposé
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.max_wall_dist_ticks = self.config.get('max_wall_dist_ticks', 15)  # Augmenté de 12 à 15
        self.min_wick_ratio = self.config.get('min_wick_ratio', 0.40)  # Réduit de 0.60 à 0.40

        self.stats = {'signals_generated': 0, 'long_signals': 0, 'short_signals': 0}
        logger.info("✅ ZeroDTEWallSweepReversal initialisé (Tier 1)")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """Analyse depuis ML_READY - VERSION AMÉLIORÉE"""
        start_time = time.perf_counter()

        try:
            # Vérifier next_wall
            next_wall = ml_data.get('next_wall', {})

            # 🔧 CORRECTION: Utiliser abs() pour distance (peut être négative)
            wall_dist_ticks = abs(next_wall.get('dist_ticks', 999))

            if not next_wall or wall_dist_ticks > self.max_wall_dist_ticks:
                return None

            # Vérifier sweep raté
            wall_side = next_wall.get('side', 'unknown')

            # ✅ CORRECTIF: Calculer wick_ratio depuis upper_wick_ticks / total_range_ticks
            upper_wick = ml_data.get('upper_wick_ticks', 0)
            lower_wick = ml_data.get('lower_wick_ticks', 0)
            total_range = ml_data.get('total_range_ticks', 0)

            # 🔒 PROTECTION: Éviter division par zéro
            if total_range == 0 or total_range is None:
                return None  # Pas de range, impossible de calculer ratio

            wick_ratio = (upper_wick / total_range) if wall_side == 'call' else (lower_wick / total_range)

            # ✅ CORRECTIF: Volume climax - OPTIMISÉ (volume adaptatif session/symbole)
            volume_climax = _volume_is_high(ml_data)

            if wick_ratio < self.min_wick_ratio:
                return None  # Sweep pas assez significatif

            # Volume climax optionnel (ne pas bloquer si absent)
            has_volume_spike = volume_climax

            # Blind spot derrière mur
            blind_spots = [ml_data.get(f'blind_spot_{i}', None) for i in range(9)]
            has_blind_spot = any(bs is not None and bs > 0 for bs in blind_spots)

            if not has_blind_spot:
                return None

            # Flip imbalance (seuil réduit de 0.10 à 0.08)
            imbalance = ml_data.get('level1_imbalance', 0.0)

            if wall_side == 'call' and imbalance < -0.08:
                side = "SHORT"  # Sweep du call wall raté, bearish
            elif wall_side == 'put' and imbalance > 0.08:
                side = "LONG"  # Sweep du put wall raté, bullish
            else:
                return None

            # Entry/Stop/Targets
            mid_price = ml_data.get('mid', 0)
            wall_price = next_wall.get('price', mid_price)
            vwap = ml_data.get('vwap', mid_price)
            atr = ml_data.get('atr', 1.0)

            # Tick size dynamique
            symbol = ml_data.get('sym', 'NQ')[:2]  # Extraire symbole de base
            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            entry = mid_price

            # 🔧 SL OPTIMISÉ: Augmenté pour éviter stop hunting (analyse losing trades)
            # NQ: 20 ticks min | ES: 20 ticks | RTY: 15 ticks
            sl_min_ticks = {
                'ES': 20,  # $50 (20 * 0.25 * $50) - était 12
                'NQ': 20,  # $100 (20 * 0.25 * $20) - était 10
                'RT': 15   # $15 (15 * 0.10 * $10) - était 8
            }

            sl_ticks = max(
                int(atr * 2.5 / tick_size),  # 2.5x ATR (était 2.0x)
                sl_min_ticks.get(symbol, 20)  # Minimum par symbole (augmenté)
            )

            if side == "LONG":
                stop = entry - (sl_ticks * tick_size)
                # 🎯 TP1: VWAP | TP2: Call resistance ou 5x ATR (augmenté de 3x pour 1:2.5 ratio)
                tp1 = vwap
                tp2 = ml_data.get('call_resistance', vwap + (atr * 5.0))
            else:
                stop = entry + (sl_ticks * tick_size)
                # 🎯 TP1: VWAP | TP2: Put support ou 5x ATR (augmenté de 3x pour 1:2.5 ratio)
                tp1 = vwap
                tp2 = ml_data.get('put_support', vwap - (atr * 5.0))

            # Confidence basée sur wick_ratio + volume spike
            confidence = wick_ratio * (1.2 if has_volume_spike else 1.0)
            confidence = min(confidence, 1.0)

            signal = PatternSignal(
                strategy="zero_dte_wall_sweep",
                timestamp=datetime.now(),
                side=side,
                confidence=confidence,
                entry=entry,
                stop=stop,
                targets=[tp1, tp2],
                metadata={
                    'wall_dist_ticks': next_wall['dist_ticks'],
                    'wall_price': wall_price,
                    'wall_side': wall_side,
                    'wick_ratio': wick_ratio,
                    'volume_climax': has_volume_spike,
                    'imbalance': imbalance,
                    'atr': atr,
                    'sl_ticks': sl_ticks,
                    'source': 'ML_READY',
                    'validation': 'WALL_SWEEP_CALCULATED'
                },
                processing_time_ms=(time.perf_counter() - start_time) * 1000
            )

            self.stats['signals_generated'] += 1
            if side == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            logger.info(f"✅ ZeroDTEWallSweep: {side} @ {entry:.2f} (wick={wick_ratio:.2f}, wall_dist={next_wall['dist_ticks']}t)")
            return signal

        except Exception as e:
            logger.error(f"❌ Erreur ZeroDTEWallSweep: {e}")
            return None
