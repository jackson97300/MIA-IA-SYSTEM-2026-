#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    SEUILS DYNAMIQUES BASÉS SUR ATR
═══════════════════════════════════════════════════════════════════════════════

Version: 1.0 (11/12/2025)
Auteur: MIA IA System

Philosophie PRO:
  - Marché calme → Seuils serrés (précision)
  - Marché volatile → Seuils larges (anticipation)

Formule: MAX_DISTANCE = BASE × (1 + ATR_RATIO / DIVISOR)

Usage:
    from config.dynamic_thresholds import DynamicThresholds

    max_range = DynamicThresholds.get_max_range('NQ', atr_ratio=28.6)
    # Retourne: 107 (vs 60 en seuil fixe)

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Tuple
from core.logger import get_logger

logger = get_logger(__name__)


class DynamicThresholds:
    """
    Seuils dynamiques basés sur la volatilité (ATR Ratio)

    Avantages:
    - Adaptatif à la volatilité du marché
    - Évite les rejets inutiles en haute volatilité
    - Bornes MIN/MAX pour éviter les extrêmes
    - Approche utilisée par les institutions
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURATION DE BASE PAR SYMBOLE
    # ═══════════════════════════════════════════════════════════════════════════

    # Distance de BASE pour le range (en ticks)
    BASE_RANGE = {
        'ES': 30,   # ES moins volatile
        'NQ': 50,   # NQ plus volatile (2-3x ES)
        'RTY': 40,  # RTY intermédiaire
    }

    # MINIMUM absolu (même en basse volatilité)
    MIN_RANGE = {
        'ES': 20,
        'NQ': 30,
        'RTY': 25,
    }

    # MAXIMUM absolu (même en haute volatilité)
    MAX_RANGE = {
        'ES': 100,   # ~25 points ES max
        'NQ': 200,   # ~50 points NQ max
        'RTY': 150,  # ~15 points RTY max
    }

    # Distance de BASE pour les niveaux MenthorQ (en ticks)
    BASE_LEVEL_DISTANCE = {
        'ES': 10,
        'NQ': 20,
        'RTY': 15,
    }

    # MINIMUM pour distance aux niveaux
    MIN_LEVEL_DISTANCE = {
        'ES': 8,
        'NQ': 15,
        'RTY': 10,
    }

    # MAXIMUM pour distance aux niveaux
    MAX_LEVEL_DISTANCE = {
        'ES': 40,
        'NQ': 80,
        'RTY': 50,
    }

    # Diviseur pour le multiplicateur (ajuste la sensibilité)
    # Plus petit = plus sensible à la volatilité
    VOLATILITY_DIVISOR = 25

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES POUR LE RANGE
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def get_max_range(cls, symbol: str, atr_ratio: float) -> int:
        """
        Calcule le range MAXIMUM dynamique pour un symbole.

        Args:
            symbol: 'ES', 'NQ', ou 'RTY'
            atr_ratio: Ratio ATR du snapshot (typiquement 5-50)

        Returns:
            Range maximum en ticks

        Example:
            >>> DynamicThresholds.get_max_range('NQ', 28.6)
            107
        """
        base = cls.BASE_RANGE.get(symbol, 40)
        min_range = cls.MIN_RANGE.get(symbol, 25)
        max_range = cls.MAX_RANGE.get(symbol, 150)

        # Calcul du multiplicateur
        multiplier = 1.0 + (atr_ratio / cls.VOLATILITY_DIVISOR)

        # Calcul du range
        dynamic_range = base * multiplier

        # Appliquer les bornes
        result = int(max(min_range, min(max_range, dynamic_range)))

        logger.debug(f"[{symbol}] Range dynamique: base={base}, mult={multiplier:.2f}, "
                    f"calc={dynamic_range:.0f}, final={result} (ATR={atr_ratio:.1f})")

        return result

    @classmethod
    def get_min_range(cls, symbol: str, atr_ratio: float) -> int:
        """
        Calcule le range MINIMUM dynamique (pour éviter les micro-ranges).
        Typiquement 30% du max.
        """
        max_range = cls.get_max_range(symbol, atr_ratio)
        min_range = cls.MIN_RANGE.get(symbol, 25)

        dynamic_min = int(max_range * 0.3)
        return max(min_range, dynamic_min)

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES POUR LES DISTANCES AUX NIVEAUX
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def get_max_level_distance(cls, symbol: str, atr_ratio: float) -> int:
        """
        Calcule la distance MAX aux niveaux MenthorQ.

        En haute volatilité, on peut être plus loin d'un niveau car
        le prix "traverse" les niveaux plus rapidement.

        Args:
            symbol: 'ES', 'NQ', ou 'RTY'
            atr_ratio: Ratio ATR du snapshot

        Returns:
            Distance maximale en ticks
        """
        base = cls.BASE_LEVEL_DISTANCE.get(symbol, 15)
        min_dist = cls.MIN_LEVEL_DISTANCE.get(symbol, 10)
        max_dist = cls.MAX_LEVEL_DISTANCE.get(symbol, 50)

        multiplier = 1.0 + (atr_ratio / cls.VOLATILITY_DIVISOR)
        dynamic_dist = base * multiplier

        return int(max(min_dist, min(max_dist, dynamic_dist)))

    @classmethod
    def get_entry_zone(cls, symbol: str, atr_ratio: float) -> int:
        """
        Zone d'entrée IMMÉDIATE (plus serrée).
        Typiquement 60% de la distance max.

        C'est la zone où le signal est très fort.
        """
        max_dist = cls.get_max_level_distance(symbol, atr_ratio)
        return int(max_dist * 0.6)

    @classmethod
    def get_alert_zone(cls, symbol: str, atr_ratio: float) -> int:
        """
        Zone d'ALERTE (surveillance).
        Typiquement 150% de la distance max.

        C'est la zone où on surveille le niveau sans trader.
        """
        max_dist = cls.get_max_level_distance(symbol, atr_ratio)
        return int(max_dist * 1.5)

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def get_all_thresholds(cls, symbol: str, atr_ratio: float) -> Dict:
        """
        Retourne TOUS les seuils dynamiques pour un symbole.

        Returns:
            {
                'range_min': Range minimum,
                'range_max': Range maximum,
                'level_entry': Zone d'entrée,
                'level_max': Distance max aux niveaux,
                'level_alert': Zone d'alerte,
                'multiplier': Multiplicateur appliqué,
                'atr_ratio': ATR ratio utilisé,
            }
        """
        multiplier = 1.0 + (atr_ratio / cls.VOLATILITY_DIVISOR)

        return {
            'range_min': cls.get_min_range(symbol, atr_ratio),
            'range_max': cls.get_max_range(symbol, atr_ratio),
            'level_entry': cls.get_entry_zone(symbol, atr_ratio),
            'level_max': cls.get_max_level_distance(symbol, atr_ratio),
            'level_alert': cls.get_alert_zone(symbol, atr_ratio),
            'multiplier': round(multiplier, 2),
            'atr_ratio': atr_ratio,
        }

    @classmethod
    def is_range_valid(cls, symbol: str, atr_ratio: float, range_ticks: float) -> Tuple[bool, str]:
        """
        Vérifie si un range est valide selon la volatilité actuelle.

        Returns:
            (is_valid, reason)
        """
        min_range = cls.get_min_range(symbol, atr_ratio)
        max_range = cls.get_max_range(symbol, atr_ratio)

        if range_ticks < min_range:
            return False, f"Range trop petit ({range_ticks:.0f}t < {min_range}t min)"

        if range_ticks > max_range:
            return False, f"Range trop grand ({range_ticks:.0f}t > {max_range}t max)"

        return True, f"Range valide ({range_ticks:.0f}t dans [{min_range}-{max_range}]t)"

    @classmethod
    def is_near_level(cls, symbol: str, atr_ratio: float, distance_ticks: float) -> Tuple[bool, str, str]:
        """
        Vérifie si une distance est dans une zone tradable.

        Returns:
            (is_valid, zone_name, details)

        Example:
            >>> DynamicThresholds.is_near_level('NQ', 28.6, 33)
            (True, 'MAX', 'dist=33t dans zone MAX (26-43t)')
        """
        entry = cls.get_entry_zone(symbol, atr_ratio)
        max_dist = cls.get_max_level_distance(symbol, atr_ratio)
        alert = cls.get_alert_zone(symbol, atr_ratio)

        abs_dist = abs(distance_ticks)

        if abs_dist <= entry:
            return True, 'ENTRY', f"dist={abs_dist:.0f}t dans zone ENTRY (0-{entry}t)"

        if abs_dist <= max_dist:
            return True, 'MAX', f"dist={abs_dist:.0f}t dans zone MAX ({entry}-{max_dist}t)"

        if abs_dist <= alert:
            return False, 'ALERT', f"dist={abs_dist:.0f}t dans zone ALERT ({max_dist}-{alert}t)"

        return False, 'FAR', f"dist={abs_dist:.0f}t trop loin (> {alert}t)"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST SEUILS DYNAMIQUES")
    print("=" * 60)

    # Test avec différents ATR
    for symbol in ['ES', 'NQ', 'RTY']:
        print(f"\n{symbol}:")
        for atr in [5, 15, 25, 35, 50]:
            thresholds = DynamicThresholds.get_all_thresholds(symbol, atr)
            print(f"  ATR={atr:2d} → Range: {thresholds['range_min']}-{thresholds['range_max']}t | "
                  f"Level: {thresholds['level_max']}t | mult={thresholds['multiplier']:.2f}")

    print("\n" + "=" * 60)
    print("EXEMPLE NQ avec ATR=28.6 (comme le 11/12/2025):")
    print("=" * 60)
    thresholds = DynamicThresholds.get_all_thresholds('NQ', 28.6)
    for k, v in thresholds.items():
        print(f"  {k}: {v}")

    # Test is_range_valid
    print("\nValidation range NQ 409 ticks avec ATR=28.6:")
    valid, reason = DynamicThresholds.is_range_valid('NQ', 28.6, 409)
    print(f"  {reason} → {'✅ VALIDE' if valid else '❌ INVALIDE'}")

    # Avec seuil fixe ancien (60t max)
    print("\nAvec ancien seuil FIXE (60t max):")
    print(f"  409t > 60t → ❌ REJETÉ (ancien système)")














