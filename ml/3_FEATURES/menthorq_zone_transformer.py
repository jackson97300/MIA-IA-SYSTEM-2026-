"""
Module pour transformer les niveaux MenthorQ/Options en ZONES de proximité.

Au lieu de considérer les niveaux comme des points exacts, on crée des zones
autour de chaque niveau (±N ticks) pour capturer le comportement proche du niveau.

Exemple:
    GEX niveau exact: 6775.00
    → Zone GEX: 6770.00 - 6780.00 (±5 ticks)
    → Si prix = 6773 → "dans la zone GEX" (feature booléenne + proximité)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


class MenthorQZoneTransformer:
    """
    Transforme les niveaux MenthorQ exacts en zones de proximité.
    """

    def __init__(
        self,
        gex_zone_ticks: int = 5,
        blind_zone_ticks: int = 3,
        hvl_zone_ticks: int = 10,
        call_put_zone_ticks: int = 20
    ):
        """
        Args:
            gex_zone_ticks: Largeur zone GEX en ticks (±5 ticks = zone de 10 ticks)
            blind_zone_ticks: Largeur zone blind spot (±3 ticks)
            hvl_zone_ticks: Largeur zone HVL (±10 ticks)
            call_put_zone_ticks: Largeur zone call/put resistance/support (±20 ticks)
        """
        self.gex_zone_ticks = gex_zone_ticks
        self.blind_zone_ticks = blind_zone_ticks
        self.hvl_zone_ticks = hvl_zone_ticks
        self.call_put_zone_ticks = call_put_zone_ticks

        self.tick_size = 0.25  # ES/NQ tick size

    def _in_zone(self, price: float, level: float, zone_ticks: int) -> bool:
        """Check si prix dans la zone du niveau."""
        distance_ticks = abs(price - level) / self.tick_size
        return distance_ticks <= zone_ticks

    def _zone_proximity(self, price: float, level: float, zone_ticks: int) -> float:
        """
        Calcule proximité normalisée (0-1).

        Returns:
            1.0 si dans la zone, décroît linéairement jusqu'à 0 à 3x la zone
        """
        distance_ticks = abs(price - level) / self.tick_size

        if distance_ticks <= zone_ticks:
            # Dans la zone: proximité = 1.0 - (distance / zone_width)
            return 1.0 - (distance_ticks / zone_ticks)
        elif distance_ticks <= zone_ticks * 3:
            # Hors zone mais proche: décroissance linéaire
            return (zone_ticks * 3 - distance_ticks) / (zone_ticks * 2)
        else:
            # Trop loin
            return 0.0

    def transform_gex_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforme les 10 niveaux GEX en features de proximité.

        Features créées:
            - in_gex_zone: bool (dans une zone GEX)
            - closest_gex_proximity: float (proximité 0-1 au GEX le plus proche)
            - gex_count_nearby: int (nombre de GEX dans un rayon de 3x zone)
            - gex_sandwich: bool (prix entre 2 GEX proches)
        """

        mid = df['mid']

        # 1. Trouver le GEX le plus proche et sa proximité
        gex_cols = [f'gex_{i}' for i in range(1, 11)]

        proximities = []
        for col in gex_cols:
            if col in df.columns:
                prox = df.apply(
                    lambda row: self._zone_proximity(row['mid'], row[col], self.gex_zone_ticks),
                    axis=1
                )
                proximities.append(prox)

        if proximities:
            proximities_df = pd.concat(proximities, axis=1)
            df['closest_gex_proximity'] = proximities_df.max(axis=1)
            df['in_gex_zone'] = (df['closest_gex_proximity'] >= 0.5).astype(int)

            # Compte combien de GEX sont "proches"
            df['gex_count_nearby'] = (proximities_df > 0.3).sum(axis=1)
        else:
            df['closest_gex_proximity'] = 0.0
            df['in_gex_zone'] = 0
            df['gex_count_nearby'] = 0

        # 2. Détecte si prix est "sandwich" entre 2 GEX proches
        df['gex_sandwich'] = 0
        for idx, row in df.iterrows():
            gex_levels = [row[col] for col in gex_cols if col in df.columns and row[col] > 0]
            gex_levels_sorted = sorted(gex_levels)

            mid_price = row['mid']
            for i in range(len(gex_levels_sorted) - 1):
                gex_below = gex_levels_sorted[i]
                gex_above = gex_levels_sorted[i + 1]

                # Si prix entre 2 GEX ET distance entre les 2 GEX < 50 ticks
                if gex_below < mid_price < gex_above:
                    gap_ticks = (gex_above - gex_below) / self.tick_size
                    if gap_ticks < 50:  # GEX proches
                        df.at[idx, 'gex_sandwich'] = 1
                        break

        return df

    def transform_blind_spots(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforme les blind spots en features de proximité.

        Features créées:
            - in_blind_zone: bool
            - closest_blind_proximity: float (0-1)
            - blind_count_nearby: int
        """

        blind_cols = [f'blind_spot_{i}' for i in range(9)]

        proximities = []
        for col in blind_cols:
            if col in df.columns:
                prox = df.apply(
                    lambda row: self._zone_proximity(row['mid'], row[col], self.blind_zone_ticks),
                    axis=1
                )
                proximities.append(prox)

        if proximities:
            proximities_df = pd.concat(proximities, axis=1)
            df['closest_blind_proximity'] = proximities_df.max(axis=1)
            df['in_blind_zone'] = (df['closest_blind_proximity'] >= 0.5).astype(int)
            df['blind_count_nearby'] = (proximities_df > 0.3).sum(axis=1)
        else:
            df['closest_blind_proximity'] = 0.0
            df['in_blind_zone'] = 0
            df['blind_count_nearby'] = 0

        return df

    def transform_hvl(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforme HVL en proximité.

        Features créées:
            - in_hvl_zone: bool
            - hvl_proximity: float (0-1)
            - hvl_side: int (-1=below, 0=in, +1=above)
        """

        if 'hvl' not in df.columns:
            df['in_hvl_zone'] = 0
            df['hvl_proximity'] = 0.0
            df['hvl_side'] = 0
            return df

        df['hvl_proximity'] = df.apply(
            lambda row: self._zone_proximity(row['mid'], row['hvl'], self.hvl_zone_ticks),
            axis=1
        )

        df['in_hvl_zone'] = (df['hvl_proximity'] >= 0.5).astype(int)

        # Side: -1 si en-dessous, 0 si dans zone, +1 si au-dessus
        df['hvl_side'] = df.apply(
            lambda row: 0 if row['in_hvl_zone'] == 1 else (1 if row['mid'] > row['hvl'] else -1),
            axis=1
        )

        return df

    def transform_call_put_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforme call_resistance et put_support en proximités.

        Features créées:
            - in_call_zone: bool
            - call_proximity: float (0-1)
            - in_put_zone: bool
            - put_proximity: float (0-1)
            - in_strike_sandwich: bool (entre call et put)
        """

        if 'call_resistance' in df.columns:
            df['call_proximity'] = df.apply(
                lambda row: self._zone_proximity(row['mid'], row['call_resistance'], self.call_put_zone_ticks),
                axis=1
            )
            df['in_call_zone'] = (df['call_proximity'] >= 0.5).astype(int)
        else:
            df['call_proximity'] = 0.0
            df['in_call_zone'] = 0

        if 'put_support' in df.columns:
            df['put_proximity'] = df.apply(
                lambda row: self._zone_proximity(row['mid'], row['put_support'], self.call_put_zone_ticks),
                axis=1
            )
            df['in_put_zone'] = (df['put_proximity'] >= 0.5).astype(int)
        else:
            df['put_proximity'] = 0.0
            df['in_put_zone'] = 0

        # Sandwich entre call et put
        if 'call_resistance' in df.columns and 'put_support' in df.columns:
            df['in_strike_sandwich'] = (
                (df['mid'] > df['put_support']) &
                (df['mid'] < df['call_resistance'])
            ).astype(int)
        else:
            df['in_strike_sandwich'] = 0

        return df

    def transform_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applique toutes les transformations de zones.

        Returns:
            DataFrame avec 15 nouvelles features de proximité + les originales conservées
        """

        df = df.copy()

        # Appliquer toutes les transformations
        df = self.transform_gex_levels(df)
        df = self.transform_blind_spots(df)
        df = self.transform_hvl(df)
        df = self.transform_call_put_levels(df)

        return df

    def get_zone_features(self) -> List[str]:
        """Retourne la liste des features de zones créées."""
        return [
            # GEX
            'in_gex_zone',
            'closest_gex_proximity',
            'gex_count_nearby',
            'gex_sandwich',
            # Blind spots
            'in_blind_zone',
            'closest_blind_proximity',
            'blind_count_nearby',
            # HVL
            'in_hvl_zone',
            'hvl_proximity',
            'hvl_side',
            # Call/Put
            'in_call_zone',
            'call_proximity',
            'in_put_zone',
            'put_proximity',
            'in_strike_sandwich'
        ]


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("="*80)
    print("MODULE MENTHORQ ZONE TRANSFORMER")
    print("="*80)
    print("\nTransforme niveaux MenthorQ exacts en ZONES de proximité\n")

    transformer = MenthorQZoneTransformer(
        gex_zone_ticks=5,       # ±5 ticks autour GEX
        blind_zone_ticks=3,     # ±3 ticks autour blind spots
        hvl_zone_ticks=10,      # ±10 ticks autour HVL
        call_put_zone_ticks=20  # ±20 ticks autour call/put
    )

    print("Configuration:")
    print(f"  GEX zone: ±{transformer.gex_zone_ticks} ticks")
    print(f"  Blind spot zone: ±{transformer.blind_zone_ticks} ticks")
    print(f"  HVL zone: ±{transformer.hvl_zone_ticks} ticks")
    print(f"  Call/Put zone: ±{transformer.call_put_zone_ticks} ticks")

    print(f"\n15 nouvelles features de zones créées:")
    for i, feat in enumerate(transformer.get_zone_features(), 1):
        print(f"  {i:2d}. {feat}")

    print("\nAvantages:")
    print("  - Plus robuste qu'un niveau exact")
    print("  - Capture le comportement AUTOUR du niveau")
    print("  - Détecte les zones de confluence (sandwich, multi-GEX)")
    print("  - Normalise la proximité (0-1) pour ML")
