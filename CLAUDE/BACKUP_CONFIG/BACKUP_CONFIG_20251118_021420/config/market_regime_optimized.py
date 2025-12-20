"""
Market Regime Detector Optimisé
Ajout de cache pour les calculs de régime
"""

from functools import lru_cache
from typing import List, Tuple
import numpy as np
from collections import deque

from .market_regime import MarketRegimeDetector, RegimeAnalysis
from core.base_types import MarketData


class OptimizedMarketRegimeDetector(MarketRegimeDetector):
    """Version optimisée avec cache"""

    def __init__(self, config=None):
        super().__init__(config)
        self._regime_cache = {}
        self._cache_ttl = 60  # secondes

    @lru_cache(maxsize=100)
    def _detect_trend_pattern(self,
                              highs: Tuple[float, ...],
                              lows: Tuple[float, ...]) -> str:
        """Détection pattern avec cache"""
        highs_arr = np.array(highs)
        lows_arr = np.array(lows)

        # Calcul des patterns HH/HL/LL/LH
        hh_count = sum(highs_arr[i] > highs_arr[i-1] for i in range(1, len(highs_arr)))
        ll_count = sum(lows_arr[i] < lows_arr[i-1] for i in range(1, len(lows_arr)))

        if hh_count > len(highs) * 0.6:
            return "UPTREND"
        elif ll_count > len(lows) * 0.6:
            return "DOWNTREND"
        else:
            return "RANGE"

    @lru_cache(maxsize=50)
    def _calculate_volatility_regime(self,
                                     ranges: Tuple[float, ...]) -> float:
        """Calcul volatilité avec cache"""
        ranges_arr = np.array(ranges)

        # ATR-like calculation
        atr = np.mean(ranges_arr)
        volatility = np.std(ranges_arr)

        # Normaliser entre 0 et 1
        hist_vol = volatility / atr if atr > 0 else 0
        return min(1.0, hist_vol)

    def analyze_market_regime(self, market_data: MarketData) -> RegimeAnalysis:
        """Version optimisée de l'analyse"""
        # Convertir listes en tuples pour cache
        if len(self.price_history) >= self.lookback_periods:
            highs = tuple(md.high for md in self.price_history[-self.lookback_periods:])
            lows = tuple(md.low for md in self.price_history[-self.lookback_periods:])
            ranges = tuple(md.high - md.low for md in self.price_history[-self.lookback_periods:])

            # Utiliser versions cachées
            trend = self._detect_trend_pattern(highs, lows)
            volatility = self._calculate_volatility_regime(ranges)
        else:
            trend = "UNKNOWN"
            volatility = 0.5

        # Le reste utilise la logique parent
        return super().analyze_market_regime(market_data)
