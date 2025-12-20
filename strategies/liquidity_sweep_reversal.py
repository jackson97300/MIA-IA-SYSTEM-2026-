"""
Liquidity Sweep Reversal (Tier 2) - ML_READY Optimized
"""
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PatternSignal:
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0

class LiquiditySweepReversal:
    """Tier 2: Piège liquidité + reclaim"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.stats = {'signals_generated': 0}
        logger.info("✅ LiquiditySweepReversal initialisé (Tier 2)")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """Analyse ML_READY avec validation stricte des conditions de sweep"""
        start_time = time.perf_counter()

        try:
            # ═══════════════════════════════════════════════════════════
            # 🛡️ VALIDATION 1: POSITION DANS LE RANGE (< 15% des extrêmes)
            # ═══════════════════════════════════════════════════════════
            position_in_range = ml_data.get('position_in_range', 50.0)

            # Rejeter si trop au centre (entre 15% et 85%)
            if 15.0 < position_in_range < 85.0:
                return None  # ❌ Pas aux extrêmes du range

            # ═══════════════════════════════════════════════════════════
            # 🛡️ VALIDATION 2: VÉRIFIER QU'UN VRAI SWEEP A EU LIEU
            # ═══════════════════════════════════════════════════════════
            # Un vrai sweep = longue mèche (wick) qui dépasse puis revient
            upper_wick_ticks = ml_data.get('upper_wick_ticks', 0.0)
            lower_wick_ticks = ml_data.get('lower_wick_ticks', 0.0)
            total_range_ticks = ml_data.get('total_range_ticks', 1.0)

            # Ratio de la mèche par rapport au range total
            wick_ratio_upper = upper_wick_ticks / total_range_ticks if total_range_ticks > 0 else 0
            wick_ratio_lower = lower_wick_ticks / total_range_ticks if total_range_ticks > 0 else 0

            # Exiger au moins 40% de mèche (sweep significatif)
            min_wick_ratio = 0.40
            has_upper_sweep = wick_ratio_upper >= min_wick_ratio
            has_lower_sweep = wick_ratio_lower >= min_wick_ratio

            if not (has_upper_sweep or has_lower_sweep):
                return None  # ❌ Pas de vrai sweep

            # ═══════════════════════════════════════════════════════════
            # 🛡️ VALIDATION 3: LAYER 1 - MENTHORQ (50% du poids)
            # ═══════════════════════════════════════════════════════════
            # Exiger une confluence MenthorQ significative
            mq_impact = ml_data.get('menthorq_impact_score', 0.0)
            mq_proximity = ml_data.get('menthorq_proximity_strength', 0.0)
            confluence_strength = ml_data.get('confluence_strength', 0.0)

            # Layer 1: Score MenthorQ combiné
            layer1_score = (mq_impact * 0.40) + (mq_proximity * 0.30) + (confluence_strength * 0.30)

            if layer1_score < 0.15:
                return None  # ❌ Layer 1 MenthorQ insuffisant

            # ═══════════════════════════════════════════════════════════
            # 🛡️ VALIDATION 4: LAYER 2 - ORDER FLOW (30% du poids)
            # ═══════════════════════════════════════════════════════════
            smart_money = ml_data.get('smart_money_flow', 0.0)
            inst_pressure = ml_data.get('institutional_pressure', 0.0)
            delta_burst = ml_data.get('delta_burst', 0.0)

            # Layer 2: Score Order Flow
            layer2_score = (abs(smart_money) * 0.50) + (abs(inst_pressure) * 0.30) + (min(abs(delta_burst) / 100.0, 1.0) * 0.20)

            if layer2_score < 0.10:
                return None  # ❌ Layer 2 Order Flow insuffisant (BLOQUER SI = 0.00)

            # ═══════════════════════════════════════════════════════════
            # 🛡️ VALIDATION 5: LAYER 3 - CONTEXT (20% du poids)
            # ═══════════════════════════════════════════════════════════
            d_vwap_atr = abs(ml_data.get('d_vwap_atr', 0.0))
            atr_ratio = ml_data.get('atr_ratio', 0.0)
            volatility_regime = ml_data.get('volatility_regime_cont', 0.0)

            # Layer 3: Score Context
            layer3_score = (min(d_vwap_atr / 2.0, 1.0) * 0.40) + (min(atr_ratio / 20.0, 1.0) * 0.30) + (volatility_regime * 0.30)

            if layer3_score < 0.05:
                return None  # ❌ Layer 3 Context insuffisant (BLOQUER SI = 0.00)

            # ═══════════════════════════════════════════════════════════
            # 🛡️ VALIDATION 6: DÉTERMINER LA DIRECTION
            # ═══════════════════════════════════════════════════════════
            # Direction basée sur le sweep + smart money
            if has_lower_sweep and smart_money > 0.20:
                side = "LONG"  # Sweep du LOW puis reclaim bullish
            elif has_upper_sweep and smart_money < -0.20:
                side = "SHORT"  # Sweep du HIGH puis reclaim bearish
            else:
                return None  # ❌ Pas de confluence claire

            # ═══════════════════════════════════════════════════════════
            # ✅ CALCUL DE LA CONFLUENCE FINALE (PONDÉRÉE 3-LAYER)
            # ═══════════════════════════════════════════════════════════
            total_confidence = (layer1_score * 0.50) + (layer2_score * 0.30) + (layer3_score * 0.20)

            # ⚠️ SEUIL MINIMUM AUGMENTÉ À 0.70 (au lieu de 0.35)
            if total_confidence < 0.70:
                return None  # ❌ Confluence totale insuffisante

            # ═══════════════════════════════════════════════════════════
            # 📊 GÉNÉRATION DU SIGNAL
            # ═══════════════════════════════════════════════════════════
            mid = ml_data.get('mid', 0)
            vwap = ml_data.get('vwap', mid)
            atr = ml_data.get('atr', 1.0)
            symbol = ml_data.get('sym', 'UNKNOWN')

            # Tick size dynamique par symbole
            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # SL/TP basés sur ATR et niveaux MenthorQ
            sl_distance_ticks = max(int(atr * 1.5 / tick_size), 8)
            tp1_distance_ticks = max(int(atr * 2.0 / tick_size), 12)
            tp2_distance_ticks = max(int(atr * 3.5 / tick_size), 20)

            if side == "LONG":
                stop_loss = mid - (sl_distance_ticks * tick_size)
                tp1 = mid + (tp1_distance_ticks * tick_size)
                tp2 = mid + (tp2_distance_ticks * tick_size)
            else:
                stop_loss = mid + (sl_distance_ticks * tick_size)
                tp1 = mid - (tp1_distance_ticks * tick_size)
                tp2 = mid - (tp2_distance_ticks * tick_size)

            signal = PatternSignal(
                strategy="liquidity_sweep_reversal",
                timestamp=datetime.now(),
                side=side,
                confidence=total_confidence,
                entry=mid,
                stop=stop_loss,
                targets=[tp1, tp2],
                metadata={
                    'position_in_range': position_in_range,
                    'has_upper_sweep': has_upper_sweep,
                    'has_lower_sweep': has_lower_sweep,
                    'wick_ratio_upper': round(wick_ratio_upper, 3),
                    'wick_ratio_lower': round(wick_ratio_lower, 3),
                    'layer1_menthorq': round(layer1_score, 3),
                    'layer2_orderflow': round(layer2_score, 3),
                    'layer3_context': round(layer3_score, 3),
                    'smart_money_flow': smart_money,
                    'institutional_pressure': inst_pressure,
                    'menthorq_impact': mq_impact,
                    'menthorq_proximity': mq_proximity,
                    'confluence_strength': confluence_strength,
                    'atr': atr,
                    'sl_distance_ticks': sl_distance_ticks,
                    'tp1_distance_ticks': tp1_distance_ticks,
                    'tp2_distance_ticks': tp2_distance_ticks,
                    'source': 'ML_READY',
                    'validation': 'STRICT_3LAYER_SWEEP'
                },
                processing_time_ms=(time.perf_counter() - start_time) * 1000
            )

            self.stats['signals_generated'] += 1
            logger.info(f"✅ Liquidity Sweep {side} @ {mid:.2f} | Conf: {total_confidence:.3f} | L1={layer1_score:.2f} L2={layer2_score:.2f} L3={layer3_score:.2f}")
            return signal

        except Exception as e:
            logger.error(f"❌ Erreur LiquiditySweep: {e}")
            return None
