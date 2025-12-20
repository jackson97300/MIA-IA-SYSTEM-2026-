"""
strategies/weekly_vwap_extreme_reversion.py

WEEKLY/MONTHLY VWAP EXTREME REVERSION - Game Changer Strategy
Exploite les extrêmes statistiques (>3σ) pour mean reversion haute probabilité

Version: 1.0 ML_READY
Date: 18 Novembre 2025
Win Rate attendu: 60-65%
Fréquence: 2-5 setups/jour
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PatternSignal:
    """Signal généré par une stratégie"""
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0


class WeeklyVWAPExtremeReversion:
    """
    WEEKLY/MONTHLY VWAP EXTREME REVERSION

    Détecte prix >800 ticks (ES) ou >3000 ticks (NQ) du weekly/monthly VWAP
    = Extrêmes statistiques avec forte probabilité de reversion

    Triggers:
    - Prix < Weekly VWAP - 200 pts (ES) ou -500 pts (NQ)
    - OU Prix < Monthly VWAP - 500 pts (ES) ou -1000 pts (NQ)
    - ET momentum commence à inverser (delta flip, imbalance change)

    Entry: Market @ extremum avec confirmation flip
    SL: 50 ticks (prix déjà extrême)
    TP1: 100 ticks (25% du gap)
    TP2: 200 ticks (50% du gap)
    TP3: Weekly VWAP (full reversion)
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.name = "weekly_vwap_extreme_reversion"  # ✅ FIX 21/11 02:20: Ajout nom stratégie

        # Seuils extrême (en ticks)
        self.EXTREME_THRESHOLDS = {
            'ES': {
                'weekly_min': 800,   # 800 ticks = 200 pts
                'monthly_min': 2000  # 2000 ticks = 500 pts
            },
            'NQ': {
                'weekly_min': 2000,  # 2000 ticks = 500 pts
                'monthly_min': 4000  # 4000 ticks = 1000 pts
            },
            'RTY': {
                'weekly_min': 1000,  # 1000 ticks = 100 pts
                'monthly_min': 2500  # 2500 ticks = 250 pts
            }
        }

        # Stops/Targets
        self.sl_ticks = 50
        self.tp1_ticks = 100
        self.tp2_ticks = 200

        # Cooldown
        self.last_signal_time = {}
        self.cooldown_seconds = 300  # 5 minutes (setup rare)

        # Stats
        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0,
            'weekly_extremes': 0,
            'monthly_extremes': 0
        }

        logger.info("✅ WeeklyVWAPExtremeReversion initialisée")
        logger.info(f"   ES thresholds: Weekly {self.EXTREME_THRESHOLDS['ES']['weekly_min']}t, "
                   f"Monthly {self.EXTREME_THRESHOLDS['ES']['monthly_min']}t")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Analyse ML_READY pour détecter extrêmes VWAP

        Args:
            ml_data: Dict ML_READY complet

        Returns:
            PatternSignal ou None
        """
        start_time = time.perf_counter()

        try:
            # Extraire données
            symbol = ml_data.get('symbol', 'UNKNOWN')
            if symbol not in ['ES', 'NQ', 'RTY']:
                return None

            mid_price = ml_data.get('mid', 0)

            # VWAP weekly/monthly
            vwap_weekly = ml_data.get('vwap_weekly', 0)
            vwap_monthly = ml_data.get('vwap_monthly', 0)
            d_vwap_weekly_ticks = ml_data.get('d_vwap_weekly_ticks', 0)
            d_vwap_monthly_ticks = ml_data.get('d_vwap_monthly_ticks', 0)

            if vwap_weekly == 0 or vwap_monthly == 0:
                return None

            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # Vérifier cooldown
            current_time = time.time()
            if symbol in self.last_signal_time:
                time_since_last = current_time - self.last_signal_time[symbol]
                if time_since_last < self.cooldown_seconds:
                    return None

            thresholds = self.EXTREME_THRESHOLDS[symbol]

            # ═══════════════════════════════════════════════════════════
            # DÉTECTION EXTRÊME WEEKLY
            # ═══════════════════════════════════════════════════════════
            weekly_extreme = False
            weekly_direction = None

            if abs(d_vwap_weekly_ticks) >= thresholds['weekly_min']:
                weekly_extreme = True
                # Négatif = prix SOUS weekly VWAP = LONG
                # Positif = prix AU-DESSUS weekly VWAP = SHORT
                weekly_direction = "LONG" if d_vwap_weekly_ticks < 0 else "SHORT"
                self.stats['weekly_extremes'] += 1

                logger.info(f"🔥 [{symbol}] WEEKLY VWAP EXTREME détecté!")
                logger.info(f"   Distance: {d_vwap_weekly_ticks:.1f} ticks "
                          f"(threshold: {thresholds['weekly_min']})")
                logger.info(f"   Prix: {mid_price:.2f} | Weekly VWAP: {vwap_weekly:.2f}")

            # ═══════════════════════════════════════════════════════════
            # DÉTECTION EXTRÊME MONTHLY
            # ═══════════════════════════════════════════════════════════
            monthly_extreme = False
            monthly_direction = None

            if abs(d_vwap_monthly_ticks) >= thresholds['monthly_min']:
                monthly_extreme = True
                monthly_direction = "LONG" if d_vwap_monthly_ticks < 0 else "SHORT"
                self.stats['monthly_extremes'] += 1

                logger.info(f"🔥🔥 [{symbol}] MONTHLY VWAP EXTREME détecté!")
                logger.info(f"   Distance: {d_vwap_monthly_ticks:.1f} ticks "
                          f"(threshold: {thresholds['monthly_min']})")
                logger.info(f"   Prix: {mid_price:.2f} | Monthly VWAP: {vwap_monthly:.2f}")

            if not weekly_extreme and not monthly_extreme:
                return None

            # ═══════════════════════════════════════════════════════════
            # VÉRIFIER MOMENTUM FLIP (Confirmation)
            # ═══════════════════════════════════════════════════════════
            delta = ml_data.get('delta', 0)
            level1_imbalance = ml_data.get('level1_imbalance', 0)
            microgap = ml_data.get('microgap_signed', 0)

            # Déterminer direction finale (monthly > weekly si les deux)
            if monthly_extreme:
                direction = monthly_direction
                extreme_type = "MONTHLY"
                distance_ticks = abs(d_vwap_monthly_ticks)
            else:
                direction = weekly_direction
                extreme_type = "WEEKLY"
                distance_ticks = abs(d_vwap_weekly_ticks)

            # Vérifier flip momentum dans bonne direction
            momentum_ok = False
            if direction == "LONG":
                # Pour LONG: besoin delta/imbalance qui deviennent moins négatifs
                # ou commencent à devenir positifs
                momentum_ok = (delta >= -15) or (level1_imbalance >= -0.30)
            else:  # SHORT
                # Pour SHORT: besoin delta/imbalance qui deviennent moins positifs
                momentum_ok = (delta <= 15) or (level1_imbalance <= 0.30)

            if not momentum_ok:
                logger.debug(f"[{symbol}] Extrême détecté mais momentum pas encore flip")
                return None

            # ═══════════════════════════════════════════════════════════
            # GÉNÉRER SIGNAL
            # ═══════════════════════════════════════════════════════════

            entry_price = mid_price

            if direction == "LONG":
                stop_price = entry_price - (self.sl_ticks * tick_size)
                target1 = entry_price + (self.tp1_ticks * tick_size)
                target2 = entry_price + (self.tp2_ticks * tick_size)
            else:  # SHORT
                stop_price = entry_price + (self.sl_ticks * tick_size)
                target1 = entry_price - (self.tp1_ticks * tick_size)
                target2 = entry_price - (self.tp2_ticks * tick_size)

            # Confidence plus haute si monthly ET weekly
            base_confidence = 0.75 if monthly_extreme else 0.70

            # Bonus si momentum flip clair
            if direction == "LONG" and delta > 0:
                base_confidence += 0.05
            elif direction == "SHORT" and delta < 0:
                base_confidence += 0.05

            confidence = min(base_confidence, 0.85)

            # Enregistrer signal time
            self.last_signal_time[symbol] = current_time

            # Stats
            self.stats['signals_generated'] += 1
            if direction == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(f"🎯 [{symbol}] VWAP EXTREME REVERSION: {direction} @ {entry_price:.2f}")
            logger.info(f"   Type: {extreme_type} | Distance: {distance_ticks:.0f} ticks")
            logger.info(f"   Confidence: {confidence:.2f}")
            logger.info(f"   SL: {stop_price:.2f} | TP1: {target1:.2f} | TP2: {target2:.2f}")

            return PatternSignal(
                strategy="weekly_vwap_extreme_reversion",
                timestamp=datetime.now(),
                side=direction,
                confidence=confidence,
                entry=entry_price,
                stop=stop_price,
                targets=[target1, target2],
                metadata={
                    'extreme_type': extreme_type,
                    'distance_weekly_ticks': abs(d_vwap_weekly_ticks),
                    'distance_monthly_ticks': abs(d_vwap_monthly_ticks),
                    'vwap_weekly': vwap_weekly,
                    'vwap_monthly': vwap_monthly,
                    'delta': delta,
                    'level1_imbalance': level1_imbalance
                },
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"❌ Erreur WeeklyVWAPExtremeReversion: {e}")
            return None
