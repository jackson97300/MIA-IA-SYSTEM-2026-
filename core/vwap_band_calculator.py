"""
core/vwap_band_calculator.py

🎯 CALCULATEUR VWAP BAND WIDTH - PHASE 2 OPTIMISATION

Remplace ATR 1-minute par VWAP band width pour:
- Volatilité STRUCTURELLE vs court-terme
- Distances plus stables
- Moins de rejets sur mouvements passagers

VWAP Band Width = (vwap_up1 - vwap) OU (vwap - vwap_dn1)
= Mesure de volatilité basée sur distribution volume (meilleure que ATR)

Version: 1.0
Date: 18 Novembre 2025
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VWAPBandCalculator:
    """
    Calcule et utilise VWAP band width au lieu d'ATR
    """

    def __init__(self):
        """Initialise le calculateur"""
        self.fallback_atr_used = 0
        self.vwap_band_used = 0

        logger.info("✅ VWAPBandCalculator initialisé")

    def get_band_width(self, data: Dict) -> float:
        """
        Calcule VWAP band width depuis ML_READY

        Args:
            data: Données ML_READY

        Returns:
            Band width en points (fallback ATR si VWAP indisponible)
        """
        vwap = data.get('vwap', 0)
        vwap_up1 = data.get('vwap_up1', 0)
        vwap_dn1 = data.get('vwap_dn1', 0)

        # Méthode 1: VWAP up band
        if vwap > 0 and vwap_up1 > 0:
            band_width = abs(vwap_up1 - vwap)
            if band_width > 0.5:  # Sanity check
                self.vwap_band_used += 1
                return band_width

        # Méthode 2: VWAP down band
        if vwap > 0 and vwap_dn1 > 0:
            band_width = abs(vwap - vwap_dn1)
            if band_width > 0.5:
                self.vwap_band_used += 1
                return band_width

        # Fallback: ATR
        atr = data.get('atr', 1.0)
        self.fallback_atr_used += 1

        if self.fallback_atr_used == 1:
            logger.warning("⚠️ VWAP bands non disponibles, fallback ATR")

        return max(atr, 1.0)

    def normalize_distance(self, distance_pts: float, data: Dict) -> float:
        """
        Normalise une distance en points par le band width

        Args:
            distance_pts: Distance en points
            data: ML_READY data

        Returns:
            Distance normalisée (en "bands")
        """
        band_width = self.get_band_width(data)
        return distance_pts / band_width

    def get_stats(self) -> Dict:
        """Retourne statistiques d'utilisation"""
        total = self.vwap_band_used + self.fallback_atr_used
        if total == 0:
            return {'vwap_pct': 0, 'atr_pct': 0}

        return {
            'vwap_band_used': self.vwap_band_used,
            'fallback_atr_used': self.fallback_atr_used,
            'vwap_pct': (self.vwap_band_used / total) * 100,
            'atr_pct': (self.fallback_atr_used / total) * 100
        }


# ═══════════════════════════════════════════════════════════════════════
# INSTANCE GLOBALE (Singleton)
# ═══════════════════════════════════════════════════════════════════════

_global_calculator: Optional[VWAPBandCalculator] = None

def get_vwap_calculator() -> VWAPBandCalculator:
    """Retourne l'instance globale (singleton)"""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = VWAPBandCalculator()
    return _global_calculator


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_structural_volatility(data: Dict) -> float:
    """
    Retourne volatilité structurelle (VWAP band width)

    Args:
        data: ML_READY data

    Returns:
        Volatilité en points
    """
    calc = get_vwap_calculator()
    return calc.get_band_width(data)


def normalize_distance_structural(distance_pts: float, data: Dict) -> float:
    """
    Normalise distance par volatilité structurelle

    Args:
        distance_pts: Distance en points
        data: ML_READY data

    Returns:
        Distance normalisée
    """
    calc = get_vwap_calculator()
    return calc.normalize_distance(distance_pts, data)


# ═══════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    'VWAPBandCalculator',
    'get_vwap_calculator',
    'get_structural_volatility',
    'normalize_distance_structural'
]
