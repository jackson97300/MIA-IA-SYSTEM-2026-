"""
VWAP Band Squeeze Break (Tier 3) - ML_READY Optimized
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
    strategy: str
    timestamp: datetime
    side: Optional[str]
    confidence: float
    entry: float
    stop: float
    targets: list
    metadata: Dict[str, Any]
    processing_time_ms: float = 0.0

class VwapBandSqueezeBreak:
    """Tier 3: Squeeze VWAP + breakout sur relVol"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.min_relvol = self.config.get('min_relvol', 1.2)  # Réduit de 1.3 à 1.2
        self.stats = {'signals_generated': 0}
        logger.info("✅ VwapBandSqueezeBreak initialisé (Tier 3)")

    def analyze_from_ml_ready(self, ml_data: Dict[str, Any]) -> Optional[PatternSignal]:
        """Analyse ML_READY - VERSION CORRIGÉE"""
        start_time = time.perf_counter()

        try:
            # ❌ PROBLÈME: vwap_slope et volume_relative_5m n'existent pas
            # ✅ SOLUTION: Calculer squeeze depuis d_vwap_atr et volume

            mid = ml_data.get('mid', 0)
            vwap = ml_data.get('vwap', mid)
            d_vwap = ml_data.get('d_vwap', 0)
            d_vwap_atr = ml_data.get('d_vwap_atr', 0)
            atr = ml_data.get('atr', 1.0)

            # Calculer un proxy pour vwap_slope (changement de distance à VWAP)
            # Si d_vwap_atr change rapidement, c'est un breakout
            # On ne peut pas calculer une vraie slope sans historique, donc on utilise l'imbalance
            imbalance = ml_data.get('level1_imbalance', 0.0)

            # Volume relatif - OPTIMISÉ (volume adaptatif session/symbole)
            volume = ml_data.get('volume', 0)
            volume_is_high = _volume_is_high(ml_data)

            if not volume_is_high:
                return None  # Nécessite un volume élevé

            # Squeeze détecté si prix proche de VWAP (< 0.5 ATR)
            if abs(d_vwap_atr) > 0.5:
                return None  # Pas de squeeze si trop loin du VWAP

            # Breakout détecté via imbalance forte
            if imbalance > 0.12:
                side = "LONG"
            elif imbalance < -0.12:
                side = "SHORT"
            else:
                return None  # Pas de breakout clair

            # Tick size dynamique
            symbol = ml_data.get('sym', 'NQ')[:2]  # Extraire symbole de base
            tick_size = 0.25 if symbol in ['ES', 'NQ'] else 0.10

            # 🔧 SL OPTIMISÉ: Augmenté pour éviter stop hunting
            sl_min_ticks = {
                'ES': 20,  # $50 - était implicitement 8
                'NQ': 20,  # $100 - était implicitement 8
                'RT': 15   # $15 - était implicitement 8
            }

            sl_ticks = max(
                int(atr * 2.0 / tick_size),  # 2.0x ATR (était 1.5x)
                sl_min_ticks.get(symbol, 20)  # Minimum par symbole
            )

            if side == "LONG":
                stop = mid - (sl_ticks * tick_size)
                # 🎯 TP augmenté: 4-5x ATR (était 1-2x)
                tp1 = vwap + (atr * 2.0)
                tp2 = vwap + (atr * 5.0)
            else:
                stop = mid + (sl_ticks * tick_size)
                # 🎯 TP augmenté: 4-5x ATR (était 1-2x)
                tp1 = vwap - (atr * 2.0)
                tp2 = vwap - (atr * 5.0)

            # Confidence basée sur imbalance
            confidence = min(abs(imbalance) * 4.0, 1.0)

            signal = PatternSignal(
                strategy="vwap_band_squeeze_break",
                timestamp=datetime.now(),
                side=side,
                confidence=confidence,
                entry=mid,
                stop=stop,
                targets=[tp1, tp2],
                metadata={
                    'd_vwap_atr': d_vwap_atr,
                    'imbalance': imbalance,
                    'volume': volume,
                    'volume_is_high': volume_is_high,
                    'atr': atr,
                    'sl_ticks': sl_ticks,
                    'source': 'ML_READY',
                    'validation': 'VWAP_SQUEEZE_CALCULATED'
                },
                processing_time_ms=(time.perf_counter() - start_time) * 1000
            )

            self.stats['signals_generated'] += 1
            logger.info(f"✅ VwapSqueezeBreak: {side} @ {mid:.2f} (d_vwap_atr={d_vwap_atr:.2f}, imb={imbalance:.2f})")
            return signal

        except Exception as e:
            logger.error(f"❌ Erreur VwapSqueezeBreak: {e}")
            return None
