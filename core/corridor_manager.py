"""
MIA_IA_SYSTEM - Corridor GEX Manager
Gestion des corridors options (mur CALL ↔ mur PUT)

Version: 1.0 - GPT v3.0 Improvements
Date: 2 Novembre 2025
"""

from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ml_ready_helpers import extract_call_wall, extract_put_wall, get_corridor_info


class CorridorManager:
    """
    Gère le corridor GEX (zone entre mur CALL et mur PUT)

    Fonctionnalités:
    - Détection si prix dans corridor
    - Calcul headroom (marge jusqu'au mur)
    - Facteur de risque dynamique
    - Distance aux murs en % et ticks
    """

    def __init__(self, ml_data: Dict[str, Any]):
        """
        Initialise le gestionnaire de corridor

        Args:
            ml_data: Dictionnaire ML_READY complet
        """
        self.ml_data = ml_data
        self.price = ml_data.get('mid', 0)
        self.call_wall = extract_call_wall(ml_data)
        self.put_wall = extract_put_wall(ml_data)

        # Info corridor complète
        self._corridor_info = get_corridor_info(ml_data)

    def in_corridor(self) -> bool:
        """
        Prix est-il dans le corridor GEX ?

        Returns:
            True si put_wall <= price <= call_wall
        """
        if not (self.call_wall and self.put_wall and self.price):
            return False

        return self.put_wall <= self.price <= self.call_wall

    def headroom_pct(self, side: str) -> Optional[float]:
        """
        Calcule le headroom (marge) en % du prix

        Args:
            side: "LONG" ou "SHORT"

        Returns:
            Headroom en % (ex: 0.0015 = 0.15%)
        """
        if not self.price:
            return None

        if side.upper() == "LONG":
            if not self.call_wall:
                return None
            return (self.call_wall - self.price) / self.price

        else:  # SHORT
            if not self.put_wall:
                return None
            return (self.price - self.put_wall) / self.price

    def headroom_factor(self, side: str) -> float:
        """
        Facteur de risque basé sur le headroom

        Logique GPT:
        - < 0.12% : Penalty forte (0.85)
        - < 0.15% : Penalty modérée (0.90)
        - 0.15-0.30% : Normal à bonus (1.00 → 1.05)
        - > 0.30% : Bonus max (1.05)

        Args:
            side: "LONG" ou "SHORT"

        Returns:
            Facteur [0.85, 1.05]
        """
        headroom = self.headroom_pct(side)

        if headroom is None:
            return 1.0  # Neutre si pas de données

        # Convertir en % pour lisibilité
        headroom_pct_value = headroom * 100

        if headroom < 0.0012:  # < 0.12%
            return 0.85
        elif headroom < 0.0015:  # < 0.15%
            return 0.90
        elif headroom > 0.0030:  # > 0.30%
            return 1.05
        else:
            # Linéaire entre 0.15% et 0.30%
            # 1.00 + 0.05 * ((headroom - 0.0015) / 0.0015)
            factor = 1.00 + 0.05 * ((headroom - 0.0015) / 0.0015)
            return min(factor, 1.05)

    def distance_to_wall(self, wall_type: str) -> Optional[Dict[str, float]]:
        """
        Distance au mur en pts, ticks et %

        Args:
            wall_type: "CALL" ou "PUT"

        Returns:
            Dict avec pts, ticks, pct
        """
        if not self.price:
            return None

        wall_price = self.call_wall if wall_type.upper() == "CALL" else self.put_wall

        if not wall_price:
            return None

        dist_pts = abs(wall_price - self.price)
        dist_pct = dist_pts / self.price

        # Calculer ticks (ES/NQ = 0.25 par tick)
        tick_size = 0.25
        dist_ticks = dist_pts / tick_size

        return {
            'pts': dist_pts,
            'ticks': dist_ticks,
            'pct': dist_pct
        }

    def near_wall(self, wall_type: str, threshold_pct: float = 0.0018) -> bool:
        """
        Prix proche d'un mur ? (< 0.18% par défaut)

        Args:
            wall_type: "CALL" ou "PUT"
            threshold_pct: Seuil en % (défaut: 0.18%)

        Returns:
            True si proche
        """
        dist = self.distance_to_wall(wall_type)
        if not dist:
            return False

        return dist['pct'] <= threshold_pct

    def get_info(self) -> Dict[str, Any]:
        """
        Retourne toutes les infos du corridor

        Returns:
            Dict complet avec prix, murs, headroom, distances
        """
        return {
            'price': self.price,
            'call_wall': self.call_wall,
            'put_wall': self.put_wall,
            'in_corridor': self.in_corridor(),
            'headroom_long_pct': self.headroom_pct('LONG'),
            'headroom_short_pct': self.headroom_pct('SHORT'),
            'headroom_factor_long': self.headroom_factor('LONG'),
            'headroom_factor_short': self.headroom_factor('SHORT'),
            'dist_to_call': self.distance_to_wall('CALL'),
            'dist_to_put': self.distance_to_wall('PUT'),
            'near_call': self.near_wall('CALL'),
            'near_put': self.near_wall('PUT')
        }


if __name__ == "__main__":
    # Test avec données réelles GPT
    test_data = {
        'mid': 6882.13,
        'gex_1': 6900.00,
        'gex_3': 6870.00,
        'gex_4': 6890.00,
        'next_wall': {
            'price': 6890.00,
            'side': 'call',
            'dist_pts': 7.88
        }
    }

    print("=== CORRIDOR MANAGER TEST ===")
    corridor = CorridorManager(test_data)

    info = corridor.get_info()
    print(f"\nPrix: {info['price']}")
    print(f"Call Wall: {info['call_wall']}")
    print(f"Put Wall: {info['put_wall']}")
    print(f"In Corridor: {info['in_corridor']}")

    print(f"\n--- HEADROOM LONG ---")
    print(f"Headroom: {info['headroom_long_pct']*100:.3f}%")
    print(f"Factor: {info['headroom_factor_long']:.2f}")

    print(f"\n--- HEADROOM SHORT ---")
    print(f"Headroom: {info['headroom_short_pct']*100:.3f}%")
    print(f"Factor: {info['headroom_factor_short']:.2f}")

    print(f"\n--- DISTANCES ---")
    print(f"Distance CALL: {info['dist_to_call']['pts']:.2f} pts ({info['dist_to_call']['ticks']:.0f} ticks)")
    print(f"Distance PUT: {info['dist_to_put']['pts']:.2f} pts ({info['dist_to_put']['ticks']:.0f} ticks)")

    print(f"\n--- PROXIMITY ---")
    print(f"Near CALL: {info['near_call']}")
    print(f"Near PUT: {info['near_put']}")




