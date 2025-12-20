#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Range Manager (5M + 15M)
==========================================

Orchestrateur des 2 détecteurs de ranges:
- RANGE_5M: Scalping tactique (5 minutes minimum)
- RANGE_15M: Structure swing (15 minutes minimum)

Version: 1.0
Date: 10 Novembre 2025
"""

from typing import Dict, Optional, Any
from datetime import datetime
from core.logger import get_logger
from strategies.bracket_detector_ml_ready import BracketDetectorMLReady, Bracket

logger = get_logger(__name__)


class RangeManager:
    """
    Gestionnaire des ranges 5M et 15M.

    RANGE_5M (Tactique):
    - Durée: 5 minutes minimum
    - Usage: Fades rapides, scalping edges
    - Fréquence: 5-10 détections/jour

    RANGE_15M (Stratégique):
    - Durée: 15 minutes minimum
    - Usage: Structure marché, Layer 3 filter
    - Fréquence: 1-3 détections/jour
    """

    def __init__(self):
        """Initialise les 2 détecteurs de ranges"""

        # === RANGE 5M - CONFIGURATION TACTIQUE ===
        self.detector_5m = BracketDetectorMLReady(
            window_size=360,                    # 6 min d'historique @ 1tick/sec
            min_bars_in_bracket=180,            # Min 180 samples (3 min de données)
            min_duration_seconds=300.0,         # ✅ 5 MINUTES minimum
            min_touches_per_side=2,             # 2 touches suffisent (rapide)
            breakout_confirm_closes=2,          # 2 closes confirmation
            breakout_buffer_ticks=2             # 2 ticks buffer
        )

        # === RANGE 15M - CONFIGURATION STRATÉGIQUE ===
        self.detector_15m = BracketDetectorMLReady(
            window_size=1200,                   # 20 min d'historique @ 1tick/sec
            min_bars_in_bracket=600,            # Min 600 samples (10 min de données)
            min_duration_seconds=900.0,         # ✅ 15 MINUTES minimum
            min_touches_per_side=3,             # 3 touches pour robustesse
            breakout_confirm_closes=3,          # 3 closes confirmation (plus strict)
            breakout_buffer_ticks=3             # 3 ticks buffer
        )

        # Brackets actifs
        self.active_brackets = {
            'RANGE_5M': None,
            'RANGE_15M': None
        }

        # Statistiques
        self.stats = {
            'RANGE_5M': {
                'detected': 0,
                'breakouts': 0,
                'false_breakouts_rejected': 0,
                'last_detection': None
            },
            'RANGE_15M': {
                'detected': 0,
                'breakouts': 0,
                'false_breakouts_rejected': 0,
                'last_detection': None
            }
        }

        logger.info("✅ RangeManager initialisé (5M + 15M)")
        logger.info(f"   RANGE_5M: {self.detector_5m.min_duration_seconds/60:.0f} min | "
                   f"{self.detector_5m.min_bars_in_bracket} bars | "
                   f"{self.detector_5m.min_touches_per_side} touches")
        logger.info(f"   RANGE_15M: {self.detector_15m.min_duration_seconds/60:.0f} min | "
                   f"{self.detector_15m.min_bars_in_bracket} bars | "
                   f"{self.detector_15m.min_touches_per_side} touches")

    def update(self, ml_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour les 2 détecteurs et retourne les événements.

        Args:
            ml_data: Données ML_READY

        Returns:
            Dict avec événements détectés (brackets, breakouts)
        """
        events = {
            'new_brackets': [],
            'breakouts': [],
            'ranges_active': {}
        }

        try:
            # === RANGE 5M ===
            bracket_5m = self.detector_5m.detect_bracket(ml_data)

            if bracket_5m and bracket_5m.is_valid:
                # Nouveau bracket 5M
                if self.active_brackets['RANGE_5M'] is None:
                    self.active_brackets['RANGE_5M'] = bracket_5m
                    self.stats['RANGE_5M']['detected'] += 1
                    self.stats['RANGE_5M']['last_detection'] = datetime.now()

                    logger.info(f"📦 RANGE_5M détecté: {bracket_5m.lower:.2f} - {bracket_5m.upper:.2f} "
                               f"| Q={bracket_5m.quality_score:.2f} | {bracket_5m.duration_seconds:.0f}s")

                    events['new_brackets'].append({
                        'type': 'RANGE_5M',
                        'bracket': bracket_5m
                    })

            # Vérifier breakout 5M
            breakout_5m = self.detector_5m.check_breakout(ml_data)

            if breakout_5m:
                self.stats['RANGE_5M']['breakouts'] += 1
                self.active_brackets['RANGE_5M'] = None  # Invalider

                logger.info(f"🚀 RANGE_5M BREAKOUT {breakout_5m['direction']}: {breakout_5m['breakout_price']:.2f}")

                events['breakouts'].append({
                    'type': 'RANGE_5M',
                    'breakout': breakout_5m
                })

            # === RANGE 15M ===
            bracket_15m = self.detector_15m.detect_bracket(ml_data)

            if bracket_15m and bracket_15m.is_valid:
                # Nouveau bracket 15M
                if self.active_brackets['RANGE_15M'] is None:
                    self.active_brackets['RANGE_15M'] = bracket_15m
                    self.stats['RANGE_15M']['detected'] += 1
                    self.stats['RANGE_15M']['last_detection'] = datetime.now()

                    logger.info(f"📦 RANGE_15M détecté: {bracket_15m.lower:.2f} - {bracket_15m.upper:.2f} "
                               f"| Q={bracket_15m.quality_score:.2f} | {bracket_15m.duration_seconds:.0f}s")

                    events['new_brackets'].append({
                        'type': 'RANGE_15M',
                        'bracket': bracket_15m
                    })

            # Vérifier breakout 15M
            breakout_15m = self.detector_15m.check_breakout(ml_data)

            if breakout_15m:
                self.stats['RANGE_15M']['breakouts'] += 1
                self.active_brackets['RANGE_15M'] = None  # Invalider

                logger.info(f"🚀 RANGE_15M BREAKOUT {breakout_15m['direction']}: {breakout_15m['breakout_price']:.2f}")

                events['breakouts'].append({
                    'type': 'RANGE_15M',
                    'breakout': breakout_15m
                })

            # Ranges actifs
            if self.active_brackets['RANGE_5M']:
                events['ranges_active']['RANGE_5M'] = self.active_brackets['RANGE_5M']

            if self.active_brackets['RANGE_15M']:
                events['ranges_active']['RANGE_15M'] = self.active_brackets['RANGE_15M']

            return events

        except Exception as e:
            logger.error(f"❌ Erreur RangeManager.update: {e}")
            return events

    def is_in_range_5m(self, price: float, tolerance_pct: float = 0.0) -> bool:
        """
        Vérifie si le prix est dans le range 5M.

        Args:
            price: Prix à tester
            tolerance_pct: Tolérance en % (ex: 0.001 = 0.1%)

        Returns:
            True si dans le range
        """
        bracket = self.active_brackets.get('RANGE_5M')

        if not bracket:
            return False

        margin = price * tolerance_pct if tolerance_pct > 0 else 0
        return (bracket.lower - margin) <= price <= (bracket.upper + margin)

    def is_in_range_15m(self, price: float, tolerance_pct: float = 0.0) -> bool:
        """
        Vérifie si le prix est dans le range 15M.

        Args:
            price: Prix à tester
            tolerance_pct: Tolérance en % (ex: 0.001 = 0.1%)

        Returns:
            True si dans le range
        """
        bracket = self.active_brackets.get('RANGE_15M')

        if not bracket:
            return False

        margin = price * tolerance_pct if tolerance_pct > 0 else 0
        return (bracket.lower - margin) <= price <= (bracket.upper + margin)

    def get_distance_to_edge_5m(self, price: float, edge: str = 'nearest') -> Optional[float]:
        """
        Retourne la distance au bord du range 5M.

        Args:
            price: Prix actuel
            edge: 'upper', 'lower', ou 'nearest'

        Returns:
            Distance en dollars, ou None si pas de range
        """
        bracket = self.active_brackets.get('RANGE_5M')

        if not bracket:
            return None

        if edge == 'upper':
            return bracket.upper - price
        elif edge == 'lower':
            return price - bracket.lower
        else:  # nearest
            dist_upper = abs(bracket.upper - price)
            dist_lower = abs(price - bracket.lower)
            return min(dist_upper, dist_lower)

    def get_distance_to_edge_15m(self, price: float, edge: str = 'nearest') -> Optional[float]:
        """
        Retourne la distance au bord du range 15M.

        Args:
            price: Prix actuel
            edge: 'upper', 'lower', ou 'nearest'

        Returns:
            Distance en dollars, ou None si pas de range
        """
        bracket = self.active_brackets.get('RANGE_15M')

        if not bracket:
            return None

        if edge == 'upper':
            return bracket.upper - price
        elif edge == 'lower':
            return price - bracket.lower
        else:  # nearest
            dist_upper = abs(bracket.upper - price)
            dist_lower = abs(price - bracket.lower)
            return min(dist_upper, dist_lower)

    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques des 2 détecteurs"""

        # Statistiques internes détecteurs
        stats_5m = self.detector_5m.get_statistics()
        stats_15m = self.detector_15m.get_statistics()

        return {
            'RANGE_5M': {
                **self.stats['RANGE_5M'],
                'active': self.active_brackets['RANGE_5M'] is not None,
                'current_bracket': self.active_brackets['RANGE_5M'],
                **stats_5m
            },
            'RANGE_15M': {
                **self.stats['RANGE_15M'],
                'active': self.active_brackets['RANGE_15M'] is not None,
                'current_bracket': self.active_brackets['RANGE_15M'],
                **stats_15m
            }
        }

    def reset(self):
        """Reset complet des 2 détecteurs"""
        self.detector_5m.reset()
        self.detector_15m.reset()
        self.active_brackets = {'RANGE_5M': None, 'RANGE_15M': None}
        logger.info("🔄 RangeManager reset complet")


# === FACTORY ===

def create_range_manager() -> RangeManager:
    """Crée un RangeManager avec configuration par défaut"""
    return RangeManager()


# === TESTS ===

if __name__ == "__main__":
    import random

    logger.info("=== TEST RANGE MANAGER (5M + 15M) ===\n")

    # Créer manager
    manager = create_range_manager()

    # Simuler consolidation NQ (10 minutes = 600 samples @ 1/sec)
    base_ts = int(datetime.now().timestamp() * 1000)

    logger.info("📊 Phase 1: Accumulation range (10 min = 600 samples)")
    for i in range(600):
        ml_data_test = {
            'sym': 'NQZ25_FUT_CME',
            't_ms': base_ts + (i * 1000),
            'mid': 25342.5 + random.uniform(-2.5, 2.5),
            'high': 25345 + random.uniform(-1, 1),
            'low': 25340 + random.uniform(-1, 1),
            'volume': random.randint(30, 60),
            'atr': 12.5,
            'tick_rate_1s': random.uniform(1.5, 3.0),
            'trade_rate_1s': random.uniform(0.8, 1.5),
            'session_id': 'US'
        }

        events = manager.update(ml_data_test)

        # Afficher événements importants
        if events['new_brackets']:
            for bracket_event in events['new_brackets']:
                logger.info(f"\n✅ Nouveau bracket: {bracket_event['type']}")

        # À 5 min (300 samples): devrait détecter RANGE_5M
        if i == 299:
            logger.info("\n--- 5 MINUTES ÉCOULÉES ---")
            stats = manager.get_statistics()
            logger.info(f"RANGE_5M actif: {stats['RANGE_5M']['active']}")
            logger.info(f"RANGE_15M actif: {stats['RANGE_15M']['active']}")

        # À 10 min (600 samples): devrait AUSSI détecter RANGE_15M
        if i == 599:
            logger.info("\n--- 10 MINUTES ÉCOULÉES ---")
            stats = manager.get_statistics()
            logger.info(f"RANGE_5M actif: {stats['RANGE_5M']['active']}")
            logger.info(f"RANGE_15M actif: {stats['RANGE_15M']['active']}")

    # Tester méthodes helper
    logger.info("\n📊 Phase 2: Test méthodes helper")

    test_price = 25343.0
    logger.info(f"\nPrix test: {test_price:.2f}")
    logger.info(f"Dans RANGE_5M: {manager.is_in_range_5m(test_price)}")
    logger.info(f"Dans RANGE_15M: {manager.is_in_range_15m(test_price)}")

    dist_5m = manager.get_distance_to_edge_5m(test_price, 'nearest')
    dist_15m = manager.get_distance_to_edge_15m(test_price, 'nearest')

    if dist_5m:
        logger.info(f"Distance edge RANGE_5M: {dist_5m:.2f}$")
    if dist_15m:
        logger.info(f"Distance edge RANGE_15M: {dist_15m:.2f}$")

    # Simuler breakout
    logger.info("\n🚀 Phase 3: Test breakout (3 closes au-dessus)")

    for j in range(4):
        ml_data_breakout = {
            'sym': 'NQZ25_FUT_CME',
            't_ms': base_ts + 600000 + (j * 1000),
            'mid': 25348 + (j * 1.0),  # Monte progressivement
            'volume': 80,
            'atr': 12.5,
            'tick_rate_1s': 3.0,
            'delta_rate_1s': 0.8,
            'next_wall': {'price': 25370, 'dist_ticks': 88},
            'session_id': 'US'
        }

        events = manager.update(ml_data_breakout)

        if events['breakouts']:
            for breakout in events['breakouts']:
                logger.info(f"\n✅ BREAKOUT confirmé: {breakout['type']} {breakout['breakout']['direction']}")

    # Statistiques finales
    logger.info("\n📊 Statistiques finales:")
    final_stats = manager.get_statistics()

    for range_type in ['RANGE_5M', 'RANGE_15M']:
        logger.info(f"\n{range_type}:")
        logger.info(f"  Détectés: {final_stats[range_type]['detected']}")
        logger.info(f"  Breakouts: {final_stats[range_type]['breakouts']}")
        logger.info(f"  Faux breakouts rejetés: {final_stats[range_type]['false_breakouts_rejected']}")
        logger.info(f"  Actif: {final_stats[range_type]['active']}")

    logger.info("\n=== TEST TERMINÉ ===")
