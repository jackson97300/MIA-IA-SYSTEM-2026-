"""
strategies/vpoc_extreme_reversion.py

VPOC EXTREME REVERSION
Volume Point of Control comme aimant gravitationnel

Version: 1.0 ML_READY
Date: 18 Novembre 2025
Win Rate attendu: 70%+
Fréquence: 1-2 setups/SEMAINE (rare mais puissant)
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


class VPOCExtremeReversion:
    """
    VPOC EXTREME REVERSION

    VPOC = Point où le plus de volume a été échangé
    = Aimant gravitationnel TRÈS puissant

    Triggers:
    - |d_vpoc_ticks| > 1000 (très loin VPOC)
    - Prix près d'un autre niveau (VAL, support, gamma)
    - Momentum flip (delta change)

    Entry: @ momentum flip
    SL: 50 ticks (déjà extrême)
    TP1: 200 ticks (move vers VPOC)
    TP2: VAL/VAH (value area)
    TP3: VPOC (full reversion)
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation"""
        self.config = config or {}
        self.name = "vpoc_extreme_reversion"  # ✅ FIX 21/11 02:20: Ajout nom stratégie

        # Seuils extrême (en ticks)
        self.MIN_DISTANCE_TICKS = {
            'ES': 1000,   # 1000 ticks = 250 pts
            'NQ': 1500,   # 1500 ticks = 375 pts
            'RTY': 1200   # 1200 ticks = 120 pts
        }

        self.sl_ticks = 50
        self.tp1_ticks = 200
        self.tp2_ticks = 400

        # Cooldown long (setup rare)
        self.last_signal_time = {}
        self.cooldown_seconds = 3600  # 1 heure

        # Stats
        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0,
            'extreme_detected': 0
        }

        logger.info("✅ VPOCExtremeReversion initialisée")
        logger.info(f"   Min distances: ES={self.MIN_DISTANCE_TICKS['ES']}t, "
                   f"NQ={self.MIN_DISTANCE_TICKS['NQ']}t")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """
        Détecte extrêmes VPOC
        """
        start_time = time.perf_counter()

        try:
            symbol = ml_data.get('symbol', 'UNKNOWN')
            if symbol not in ['ES', 'NQ', 'RTY']:
                return None

            # VPOC data
            vpoc = ml_data.get('vpoc', 0)
            d_vpoc_ticks = ml_data.get('d_vpoc_ticks', 0)

            # Value Area
            vva = ml_data.get('vva', {})
            vah = vva.get('vah', 0)
            val = vva.get('val', 0)

            if vpoc == 0 or d_vpoc_ticks == 0:
                return None

            mid_price = ml_data.get('mid', 0)
            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # Cooldown
            current_time = time.time()
            if symbol in self.last_signal_time:
                if current_time - self.last_signal_time[symbol] < self.cooldown_seconds:
                    return None

            # Vérifier distance extrême
            min_distance = self.MIN_DISTANCE_TICKS.get(symbol, 1000)

            if abs(d_vpoc_ticks) < min_distance:
                return None

            self.stats['extreme_detected'] += 1

            logger.info(f"🔥 [{symbol}] VPOC EXTREME détecté!")
            logger.info(f"   Distance: {d_vpoc_ticks:.0f} ticks (min: {min_distance})")
            logger.info(f"   Prix: {mid_price:.2f} | VPOC: {vpoc:.2f}")

            # ═══════════════════════════════════════════════════════════
            # VÉRIFIER CONFLUENCE AVEC AUTRE NIVEAU
            # ═══════════════════════════════════════════════════════════

            # Chercher confluence avec VAL, VAH, ou gamma levels
            near_val = abs(mid_price - val) / tick_size <= 30 if val > 0 else False
            near_vah = abs(mid_price - vah) / tick_size <= 30 if vah > 0 else False

            # Check gamma levels si disponibles
            put_support = ml_data.get('put_support', 0)
            call_resistance = ml_data.get('call_resistance', 0)
            near_gamma = False

            if put_support > 0:
                near_gamma = abs(mid_price - put_support) / tick_size <= 50
            if not near_gamma and call_resistance > 0:
                near_gamma = abs(mid_price - call_resistance) / tick_size <= 50

            has_confluence = near_val or near_vah or near_gamma

            # ═══════════════════════════════════════════════════════════
            # VÉRIFIER MOMENTUM FLIP
            # ═══════════════════════════════════════════════════════════

            delta = ml_data.get('delta', 0)
            imbalance = ml_data.get('level1_imbalance', 0)

            # Déterminer direction
            if d_vpoc_ticks < 0:
                # Prix SOUS VPOC → setup LONG vers VPOC
                direction = "LONG"
                # Besoin momentum flip bullish
                momentum_flip = (delta >= -15) or (imbalance >= -0.30)
            else:
                # Prix AU-DESSUS VPOC → setup SHORT vers VPOC
                direction = "SHORT"
                momentum_flip = (delta <= 15) or (imbalance <= 0.30)

            if not momentum_flip:
                logger.debug(f"[{symbol}] VPOC extrême mais pas de momentum flip encore")
                return None

            # ═══════════════════════════════════════════════════════════
            # GÉNÉRER SIGNAL
            # ═══════════════════════════════════════════════════════════

            entry_price = mid_price

            if direction == "LONG":
                stop_price = entry_price - (self.sl_ticks * tick_size)
                target1 = entry_price + (self.tp1_ticks * tick_size)  # Partiel
                target2 = val if val > 0 else target1 + (self.tp2_ticks * tick_size)
                target3 = vpoc  # Full reversion
            else:  # SHORT
                stop_price = entry_price + (self.sl_ticks * tick_size)
                target1 = entry_price - (self.tp1_ticks * tick_size)
                target2 = vah if vah > 0 else target1 - (self.tp2_ticks * tick_size)
                target3 = vpoc

            # Confidence haute (setup rare)
            base_confidence = 0.75

            # Bonus si confluence
            if has_confluence:
                base_confidence += 0.05

            # Bonus si momentum flip clair
            if direction == "LONG" and delta > 0:
                base_confidence += 0.05
            elif direction == "SHORT" and delta < 0:
                base_confidence += 0.05

            confidence = min(base_confidence, 0.85)

            # Enregistrer
            self.last_signal_time[symbol] = current_time

            self.stats['signals_generated'] += 1
            if direction == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(f"🎯 [{symbol}] VPOC EXTREME REVERSION: {direction} @ {entry_price:.2f}")
            logger.info(f"   Distance VPOC: {abs(d_vpoc_ticks):.0f} ticks")
            logger.info(f"   Confluence: {has_confluence}")
            logger.info(f"   Confidence: {confidence:.2f}")
            logger.info(f"   SL: {stop_price:.2f} | TP1: {target1:.2f} | TP2: {target2:.2f} | TP3: {target3:.2f}")

            return PatternSignal(
                strategy="vpoc_extreme_reversion",
                timestamp=datetime.now(),
                side=direction,
                confidence=confidence,
                entry=entry_price,
                stop=stop_price,
                targets=[target1, target2, target3],
                metadata={
                    'vpoc': vpoc,
                    'distance_vpoc_ticks': abs(d_vpoc_ticks),
                    'val': val,
                    'vah': vah,
                    'has_confluence': has_confluence,
                    'near_val': near_val,
                    'near_vah': near_vah,
                    'near_gamma': near_gamma,
                    'delta': delta,
                    'imbalance': imbalance
                },
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"❌ Erreur VPOCExtremeReversion: {e}")
            return None
