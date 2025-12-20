"""
Validateur de proximité aux niveaux importants (COMPLET).

Rejette signaux trop loin de tout niveau clé.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


@dataclass
class PriceLevel:
    """Représente un niveau de prix important."""
    price: float
    type: str
    distance_ticks: float
    strength: float = 1.0
    description: str = ""
    priority: int = 50


class LevelProximityValidator:
    """
    Valide que le prix est suffisamment proche d'un niveau important.

    Niveaux considérés (LISTE COMPLÈTE):

    PRIORITÉ MAXIMUM (100):
    - HVL (MenthorQ High Volume Level)
    - VAH (Value Area High)
    - VAL (Value Area Low)
    - POC (Point of Control)
    - 1D MAX (High of Day)
    - 1D MIN (Low of Day)

    PRIORITÉ ÉLEVÉE (80-95):
    - Gamma walls (TOUS)
    - GEX levels 0DTE (TOUS)
    - Blind spots (TOUS)

    PRIORITÉ MOYENNE (60-80):
    - VWAP ± SD1/SD2/SD3

    Distance maximale:
    - ES: 15 ticks
    - NQ: 30 ticks
    - RTY: 12 ticks
    """

    # ✅ PHILOSOPHIE: PATIENCE = QUALITÉ > QUANTITÉ
    # Ne pas augmenter les distances pour avoir plus de trades
    # Attendre que le prix VIENNE À NOUS (près des niveaux)
    # Moins de trades mais de meilleure qualité = meilleur PNL
    #
    # 🔴 CORRIGÉ 10/12/2025: ALIGNÉ avec menthorq_3layer_strategy.py
    # Distance max STRICTE pour éviter trades trop loin des niveaux
    # - ES: 15 ticks max (était 80 - BUG!)
    # - NQ: 20 ticks max (était 250 - BUG!)
    # - RTY: 15 ticks max (était 50 - BUG!)
    MAX_DISTANCE = {
        'ES': 15,    # 🔴 FIX: Était 80t - permettait trades à 31t!
        'NQ': 20,    # 🔴 FIX: Était 250t - beaucoup trop laxe
        'RTY': 15    # 🔴 FIX: Était 50t - trop laxe
    }

    LEVEL_PRIORITY = {
        # Priorité maximum (100)
        'hvl': 100,
        'vah': 100,
        'val': 100,
        'poc': 100,
        '1d_max': 100,
        '1d_min': 100,

        # Priorité élevée (80-95)
        'gamma_wall': 90,
        'gex': 85,
        'blind_spot': 85,

        # Priorité moyenne (60-80)
        'vwap_sd3': 80,
        'vwap_sd2': 75,
        'vwap_sd1': 70,
        'vwap': 65,

        # Priorité basse (40-60)
        'support': 50,
        'resistance': 50,
        'other': 40
    }

    def __init__(self):
        self.tick_size = {
            'ES': 0.25,
            'NQ': 0.25,
            'RTY': 0.10
        }

    def _calculate_distance_ticks(self, price: float, level: float, symbol: str) -> float:
        """Calcule distance en ticks."""
        tick_size = self.tick_size.get(symbol, 0.25)
        distance = abs(price - level)
        return distance / tick_size

    def _extract_levels_from_snapshot(self,
                                     snapshot: Dict,
                                     price: float,
                                     symbol: str) -> List[PriceLevel]:
        """
        Extrait TOUS les niveaux importants du snapshot.
        """
        levels = []

        # ═══════════════════════════════════════════════════════════
        # PRIORITÉ MAXIMUM (100)
        # ═══════════════════════════════════════════════════════════

        # 1. HVL (MenthorQ High Volume Level)
        hvl = snapshot.get('hvl')
        if hvl:
            distance = self._calculate_distance_ticks(price, hvl, symbol)
            levels.append(PriceLevel(
                price=hvl,
                type='hvl',
                distance_ticks=distance,
                strength=1.0,
                priority=100,
                description=f"💎 HVL @ {hvl:.2f}"
            ))
            logger.debug(f"Level: HVL @ {hvl:.2f} ({distance:.0f}t)")

        # 2. VAH (Value Area High)
        vah = snapshot.get('vah') or snapshot.get('value_area_high')
        if not vah and 'vva' in snapshot and isinstance(snapshot['vva'], dict):
            vah = snapshot['vva'].get('vah')
        if vah:
            distance = self._calculate_distance_ticks(price, vah, symbol)
            levels.append(PriceLevel(
                price=vah,
                type='vah',
                distance_ticks=distance,
                strength=1.0,
                priority=100,
                description=f"💎 VAH @ {vah:.2f}"
            ))
            logger.debug(f"Level: VAH @ {vah:.2f} ({distance:.0f}t)")

        # 3. VAL (Value Area Low)
        val = snapshot.get('val') or snapshot.get('value_area_low')
        if not val and 'vva' in snapshot and isinstance(snapshot['vva'], dict):
            val = snapshot['vva'].get('val')
        if val:
            distance = self._calculate_distance_ticks(price, val, symbol)
            levels.append(PriceLevel(
                price=val,
                type='val',
                distance_ticks=distance,
                strength=1.0,
                priority=100,
                description=f"💎 VAL @ {val:.2f}"
            ))
            logger.debug(f"Level: VAL @ {val:.2f} ({distance:.0f}t)")

        # 4. POC (Point of Control)
        poc = snapshot.get('poc') or snapshot.get('point_of_control')
        if not poc and 'vva' in snapshot and isinstance(snapshot['vva'], dict):
            poc = snapshot['vva'].get('vpoc')
        if poc:
            distance = self._calculate_distance_ticks(price, poc, symbol)
            levels.append(PriceLevel(
                price=poc,
                type='poc',
                distance_ticks=distance,
                strength=1.0,
                priority=100,
                description=f"💎 POC @ {poc:.2f}"
            ))
            logger.debug(f"Level: POC @ {poc:.2f} ({distance:.0f}t)")

        # 5. 1D MAX (High of Day)
        day_max = snapshot.get('day_max') or snapshot.get('high_of_day') or snapshot.get('1d_max')
        if day_max:
            distance = self._calculate_distance_ticks(price, day_max, symbol)
            levels.append(PriceLevel(
                price=day_max,
                type='1d_max',
                distance_ticks=distance,
                strength=1.0,
                priority=100,
                description=f"💎 1D MAX @ {day_max:.2f}"
            ))
            logger.debug(f"Level: 1D MAX @ {day_max:.2f} ({distance:.0f}t)")

        # 6. 1D MIN (Low of Day)
        day_min = snapshot.get('day_min') or snapshot.get('low_of_day') or snapshot.get('1d_min')
        if day_min:
            distance = self._calculate_distance_ticks(price, day_min, symbol)
            levels.append(PriceLevel(
                price=day_min,
                type='1d_min',
                distance_ticks=distance,
                strength=1.0,
                priority=100,
                description=f"💎 1D MIN @ {day_min:.2f}"
            ))
            logger.debug(f"Level: 1D MIN @ {day_min:.2f} ({distance:.0f}t)")

        # ═══════════════════════════════════════════════════════════
        # PRIORITÉ ÉLEVÉE (80-95)
        # ═══════════════════════════════════════════════════════════

        # 7. Gamma Walls (TOUS!)
        # Format 1: Liste de dicts
        walls = snapshot.get('gamma_walls', [])
        for i, wall in enumerate(walls):  # TOUS les walls, pas seulement top 3
            wall_price = wall.get('price')
            if wall_price:
                distance = self._calculate_distance_ticks(price, wall_price, symbol)
                wall_type = wall.get('side', 'unknown')
                strength = wall.get('strength', 0.5)

                levels.append(PriceLevel(
                    price=wall_price,
                    type='gamma_wall',
                    distance_ticks=distance,
                    strength=strength,
                    priority=90,
                    description=f"⭐ {wall_type.upper()} wall @ {wall_price:.2f}"
                ))
                logger.debug(f"Level: Gamma wall #{i+1} @ {wall_price:.2f} ({distance:.0f}t)")

        # Format 2: Clés individuelles (call_resistance, put_support)
        if 'call_resistance' in snapshot:
            call_res = snapshot['call_resistance']
            if call_res:
                distance = self._calculate_distance_ticks(price, call_res, symbol)
                levels.append(PriceLevel(
                    price=call_res,
                    type='gamma_wall',
                    distance_ticks=distance,
                    strength=0.9,
                    priority=90,
                    description=f"⭐ CALL wall @ {call_res:.2f}"
                ))
                logger.debug(f"Level: Call resistance @ {call_res:.2f} ({distance:.0f}t)")

        if 'put_support' in snapshot:
            put_sup = snapshot['put_support']
            if put_sup:
                distance = self._calculate_distance_ticks(price, put_sup, symbol)
                levels.append(PriceLevel(
                    price=put_sup,
                    type='gamma_wall',
                    distance_ticks=distance,
                    strength=0.9,
                    priority=90,
                    description=f"⭐ PUT wall @ {put_sup:.2f}"
                ))
                logger.debug(f"Level: Put support @ {put_sup:.2f} ({distance:.0f}t)")

        # 8. GEX Levels (TOUS les 0DTE!)
        # Format 1: Liste de dicts
        gex_levels = snapshot.get('gex_levels', [])
        for i, gex in enumerate(gex_levels):  # TOUS les GEX
            gex_price = gex.get('price')
            if gex_price:
                distance = self._calculate_distance_ticks(price, gex_price, symbol)
                gex_volume = gex.get('volume', 0)

                levels.append(PriceLevel(
                    price=gex_price,
                    type='gex',
                    distance_ticks=distance,
                    strength=0.8,
                    priority=85,
                    description=f"⭐ GEX @ {gex_price:.2f} (vol={gex_volume})"
                ))
                logger.debug(f"Level: GEX #{i+1} @ {gex_price:.2f} ({distance:.0f}t)")

        # Format 2: Clés individuelles (gex_1, gex_2, etc.)
        for i in range(1, 11):  # gex_1 à gex_10
            gex_key = f'gex_{i}'
            if gex_key in snapshot:
                gex_price = snapshot[gex_key]
                if gex_price:
                    distance = self._calculate_distance_ticks(price, gex_price, symbol)
                    levels.append(PriceLevel(
                        price=gex_price,
                        type='gex',
                        distance_ticks=distance,
                        strength=0.8,
                        priority=85,
                        description=f"⭐ GEX_{i} @ {gex_price:.2f}"
                    ))
                    logger.debug(f"Level: GEX_{i} @ {gex_price:.2f} ({distance:.0f}t)")

        # 9. Blind Spots (TOUS!)
        # Format 1: Liste de dicts
        blind_spots = snapshot.get('blind_spots', [])
        for i, bs in enumerate(blind_spots):  # TOUS les blind spots
            bs_price = bs.get('price')
            if bs_price:
                distance = self._calculate_distance_ticks(price, bs_price, symbol)

                levels.append(PriceLevel(
                    price=bs_price,
                    type='blind_spot',
                    distance_ticks=distance,
                    strength=0.85,
                    priority=85,
                    description=f"⭐ Blind spot @ {bs_price:.2f}"
                ))
                logger.debug(f"Level: Blind spot #{i+1} @ {bs_price:.2f} ({distance:.0f}t)")

        # Format 2: Clés individuelles (blind_spot_0, blind_spot_1, etc.)
        for i in range(0, 10):  # blind_spot_0 à blind_spot_9
            bs_key = f'blind_spot_{i}'
            if bs_key in snapshot:
                bs_price = snapshot[bs_key]
                if bs_price:
                    distance = self._calculate_distance_ticks(price, bs_price, symbol)

                    levels.append(PriceLevel(
                        price=bs_price,
                        type='blind_spot',
                        distance_ticks=distance,
                        strength=0.85,
                        priority=85,
                        description=f"⭐ Blind spot {i} @ {bs_price:.2f}"
                    ))
                    logger.debug(f"Level: Blind spot_{i} @ {bs_price:.2f} ({distance:.0f}t)")

        # ═══════════════════════════════════════════════════════════
        # 9bis. NIVEAUX 0DTE (AJOUT 05/12/2025) - PRIORITÉ TRÈS ÉLEVÉE
        # ═══════════════════════════════════════════════════════════
        # Ces niveaux sont CRITIQUES pour le trading intraday (0DTE options)

        # Call Resistance 0DTE
        cr_0dte = snapshot.get('call_resistance_0dte')
        if cr_0dte:
            distance = self._calculate_distance_ticks(price, cr_0dte, symbol)
            levels.append(PriceLevel(
                price=cr_0dte,
                type='call_wall_0dte',
                distance_ticks=distance,
                strength=0.98,
                priority=98,
                description=f"🔥 CR 0DTE @ {cr_0dte:.2f}"
            ))
            logger.debug(f"Level: Call Resistance 0DTE @ {cr_0dte:.2f} ({distance:.0f}t)")

        # Put Support 0DTE
        ps_0dte = snapshot.get('put_support_0dte')
        if ps_0dte:
            distance = self._calculate_distance_ticks(price, ps_0dte, symbol)
            levels.append(PriceLevel(
                price=ps_0dte,
                type='put_wall_0dte',
                distance_ticks=distance,
                strength=0.98,
                priority=98,
                description=f"🔥 PS 0DTE @ {ps_0dte:.2f}"
            ))
            logger.debug(f"Level: Put Support 0DTE @ {ps_0dte:.2f} ({distance:.0f}t)")

        # HVL 0DTE
        hvl_0dte = snapshot.get('hvl_0dte')
        if hvl_0dte:
            distance = self._calculate_distance_ticks(price, hvl_0dte, symbol)
            levels.append(PriceLevel(
                price=hvl_0dte,
                type='hvl_0dte',
                distance_ticks=distance,
                strength=0.90,
                priority=92,
                description=f"🔥 HVL 0DTE @ {hvl_0dte:.2f}"
            ))
            logger.debug(f"Level: HVL 0DTE @ {hvl_0dte:.2f} ({distance:.0f}t)")

        # Gamma Wall 0DTE
        gw_0dte = snapshot.get('gamma_wall_0dte')
        if gw_0dte:
            distance = self._calculate_distance_ticks(price, gw_0dte, symbol)
            levels.append(PriceLevel(
                price=gw_0dte,
                type='gamma_wall_0dte',
                distance_ticks=distance,
                strength=0.95,
                priority=95,
                description=f"🔥 Gamma Wall 0DTE @ {gw_0dte:.2f}"
            ))
            logger.debug(f"Level: Gamma Wall 0DTE @ {gw_0dte:.2f} ({distance:.0f}t)")

        # ═══════════════════════════════════════════════════════════
        # 9ter. INITIAL BALANCE (IBH/IBL) - AJOUT 05/12/2025
        # ═══════════════════════════════════════════════════════════
        # UNIQUEMENT SESSION US (après 16:30 Paris = 10:30 ET)
        # L'IB est défini pendant la 1ère heure US (09:30-10:30 ET)
        # Note: datetime et pytz importés globalement en haut du fichier

        paris_tz = pytz.timezone('Europe/Paris')
        now_paris = datetime.now(paris_tz)
        hour_paris = now_paris.hour

        # Session US: 15:30-22:00 Paris (IB valide après 16:30)
        is_us_session = 16 <= hour_paris < 22

        structure = snapshot.get('structure', {})

        # IBH - Initial Balance High
        ibh = structure.get('ibh')
        if ibh and is_us_session:
            distance = self._calculate_distance_ticks(price, ibh, symbol)
            levels.append(PriceLevel(
                price=ibh,
                type='ibh',
                distance_ticks=distance,
                strength=0.90,
                priority=90,
                description=f"🟧 IBH (Initial Balance High) @ {ibh:.2f}"
            ))
            logger.debug(f"Level: IBH @ {ibh:.2f} ({distance:.0f}t) [US Session]")

        # IBL - Initial Balance Low
        ibl = structure.get('ibl')
        if ibl and is_us_session:
            distance = self._calculate_distance_ticks(price, ibl, symbol)
            levels.append(PriceLevel(
                price=ibl,
                type='ibl',
                distance_ticks=distance,
                strength=0.90,
                priority=90,
                description=f"🟧 IBL (Initial Balance Low) @ {ibl:.2f}"
            ))
            logger.debug(f"Level: IBL @ {ibl:.2f} ({distance:.0f}t) [US Session]")

        # ═══════════════════════════════════════════════════════════
        # PRIORITÉ MOYENNE (60-80)
        # ═══════════════════════════════════════════════════════════

        # 10. PVWAP (Previous VWAP) - Niveau Volume Profile important
        pvwap = snapshot.get('pvwap')
        if pvwap:
            distance = self._calculate_distance_ticks(price, pvwap, symbol)
            levels.append(PriceLevel(
                price=pvwap,
                type='pvwap',
                distance_ticks=distance,
                strength=0.70,
                priority=70,
                description=f"PVWAP @ {pvwap:.2f}"
            ))
            logger.debug(f"Level: PVWAP @ {pvwap:.2f} ({distance:.0f}t)")

            # PVWAP ± SD1
            if 'pvwap_up1' in snapshot:
                pvwap_up1 = snapshot['pvwap_up1']
                distance = self._calculate_distance_ticks(price, pvwap_up1, symbol)
                levels.append(PriceLevel(
                    price=pvwap_up1,
                    type='pvwap_sd1',
                    distance_ticks=distance,
                    strength=0.70,
                    priority=70,
                    description=f"PVWAP upper SD1 @ {pvwap_up1:.2f}"
                ))

            if 'pvwap_dn1' in snapshot:
                pvwap_dn1 = snapshot['pvwap_dn1']
                distance = self._calculate_distance_ticks(price, pvwap_dn1, symbol)
                levels.append(PriceLevel(
                    price=pvwap_dn1,
                    type='pvwap_sd1',
                    distance_ticks=distance,
                    strength=0.70,
                    priority=70,
                    description=f"PVWAP lower SD1 @ {pvwap_dn1:.2f}"
                ))

            # PVWAP ± SD2
            if 'pvwap_up2' in snapshot:
                pvwap_up2 = snapshot['pvwap_up2']
                distance = self._calculate_distance_ticks(price, pvwap_up2, symbol)
                levels.append(PriceLevel(
                    price=pvwap_up2,
                    type='pvwap_sd2',
                    distance_ticks=distance,
                    strength=0.75,
                    priority=75,
                    description=f"PVWAP upper SD2 @ {pvwap_up2:.2f}"
                ))

            if 'pvwap_dn2' in snapshot:
                pvwap_dn2 = snapshot['pvwap_dn2']
                distance = self._calculate_distance_ticks(price, pvwap_dn2, symbol)
                levels.append(PriceLevel(
                    price=pvwap_dn2,
                    type='pvwap_sd2',
                    distance_ticks=distance,
                    strength=0.75,
                    priority=75,
                    description=f"PVWAP lower SD2 @ {pvwap_dn2:.2f}"
                ))

        # 11-14. VWAP et écarts-types (SD1, SD2, SD3)
        vwap = snapshot.get('vwap')
        if vwap:
            # VWAP lui-même
            distance = self._calculate_distance_ticks(price, vwap, symbol)
            levels.append(PriceLevel(
                price=vwap,
                type='vwap',
                distance_ticks=distance,
                strength=0.65,
                priority=65,
                description=f"VWAP @ {vwap:.2f}"
            ))
            logger.debug(f"Level: VWAP @ {vwap:.2f} ({distance:.0f}t)")

            # VWAP ± SD1
            # Format 1: vwap_sd1 (valeur)
            vwap_sd1 = snapshot.get('vwap_sd1')
            if vwap_sd1:
                for sd_type, sd_price in [('upper', vwap + vwap_sd1),
                                         ('lower', vwap - vwap_sd1)]:
                    distance = self._calculate_distance_ticks(price, sd_price, symbol)
                    levels.append(PriceLevel(
                        price=sd_price,
                        type='vwap_sd1',
                        distance_ticks=distance,
                        strength=0.70,
                        priority=70,
                        description=f"VWAP {sd_type} SD1 @ {sd_price:.2f}"
                    ))

            # Format 2: vwap_up1, vwap_dn1 (clés directes)
            if 'vwap_up1' in snapshot:
                vwap_up1 = snapshot['vwap_up1']
                distance = self._calculate_distance_ticks(price, vwap_up1, symbol)
                levels.append(PriceLevel(
                    price=vwap_up1,
                    type='vwap_sd1',
                    distance_ticks=distance,
                    strength=0.70,
                    priority=70,
                    description=f"VWAP upper SD1 @ {vwap_up1:.2f}"
                ))

            if 'vwap_dn1' in snapshot:
                vwap_dn1 = snapshot['vwap_dn1']
                distance = self._calculate_distance_ticks(price, vwap_dn1, symbol)
                levels.append(PriceLevel(
                    price=vwap_dn1,
                    type='vwap_sd1',
                    distance_ticks=distance,
                    strength=0.70,
                    priority=70,
                    description=f"VWAP lower SD1 @ {vwap_dn1:.2f}"
                ))

            # VWAP ± SD2
            # Format 1: vwap_sd2 (valeur)
            vwap_sd2 = snapshot.get('vwap_sd2')
            if vwap_sd2:
                for sd_type, sd_price in [('upper', vwap + vwap_sd2),
                                         ('lower', vwap - vwap_sd2)]:
                    distance = self._calculate_distance_ticks(price, sd_price, symbol)
                    levels.append(PriceLevel(
                        price=sd_price,
                        type='vwap_sd2',
                        distance_ticks=distance,
                        strength=0.75,
                        priority=75,
                        description=f"VWAP {sd_type} SD2 @ {sd_price:.2f}"
                    ))

            # Format 2: vwap_up2, vwap_dn2 (clés directes)
            if 'vwap_up2' in snapshot:
                vwap_up2 = snapshot['vwap_up2']
                distance = self._calculate_distance_ticks(price, vwap_up2, symbol)
                levels.append(PriceLevel(
                    price=vwap_up2,
                    type='vwap_sd2',
                    distance_ticks=distance,
                    strength=0.75,
                    priority=75,
                    description=f"VWAP upper SD2 @ {vwap_up2:.2f}"
                ))

            if 'vwap_dn2' in snapshot:
                vwap_dn2 = snapshot['vwap_dn2']
                distance = self._calculate_distance_ticks(price, vwap_dn2, symbol)
                levels.append(PriceLevel(
                    price=vwap_dn2,
                    type='vwap_sd2',
                    distance_ticks=distance,
                    strength=0.75,
                    priority=75,
                    description=f"VWAP lower SD2 @ {vwap_dn2:.2f}"
                ))

            # VWAP ± SD3 (si disponible)
            # Format 1: vwap_sd3 (valeur)
            vwap_sd3 = snapshot.get('vwap_sd3')
            if vwap_sd3:
                for sd_type, sd_price in [('upper', vwap + vwap_sd3),
                                         ('lower', vwap - vwap_sd3)]:
                    distance = self._calculate_distance_ticks(price, sd_price, symbol)
                    levels.append(PriceLevel(
                        price=sd_price,
                        type='vwap_sd3',
                        distance_ticks=distance,
                        strength=0.80,
                        priority=80,
                        description=f"VWAP {sd_type} SD3 @ {sd_price:.2f}"
                    ))

            # Format 2: vwap_up3, vwap_dn3 (clés directes)
            if 'vwap_up3' in snapshot:
                vwap_up3 = snapshot['vwap_up3']
                distance = self._calculate_distance_ticks(price, vwap_up3, symbol)
                levels.append(PriceLevel(
                    price=vwap_up3,
                    type='vwap_sd3',
                    distance_ticks=distance,
                    strength=0.80,
                    priority=80,
                    description=f"VWAP upper SD3 @ {vwap_up3:.2f}"
                ))

            if 'vwap_dn3' in snapshot:
                vwap_dn3 = snapshot['vwap_dn3']
                distance = self._calculate_distance_ticks(price, vwap_dn3, symbol)
                levels.append(PriceLevel(
                    price=vwap_dn3,
                    type='vwap_sd3',
                    distance_ticks=distance,
                    strength=0.80,
                    priority=80,
                    description=f"VWAP lower SD3 @ {vwap_dn3:.2f}"
                ))

        # ═══════════════════════════════════════════════════════════
        # PRIORITÉ BASSE (40-60)
        # ═══════════════════════════════════════════════════════════

        # 14. Support levels
        supports = snapshot.get('support_levels', [])
        for sup in supports:
            distance = self._calculate_distance_ticks(price, sup, symbol)
            levels.append(PriceLevel(
                price=sup,
                type='support',
                distance_ticks=distance,
                strength=0.5,
                priority=50,
                description=f"Support @ {sup:.2f}"
            ))

        # 15. Resistance levels
        resistances = snapshot.get('resistance_levels', [])
        for res in resistances:
            distance = self._calculate_distance_ticks(price, res, symbol)
            levels.append(PriceLevel(
                price=res,
                type='resistance',
                distance_ticks=distance,
                strength=0.5,
                priority=50,
                description=f"Resistance @ {res:.2f}"
            ))

        return levels

    def find_nearest_level(self,
                          snapshot: Dict,
                          price: float,
                          symbol: str,
                          direction: str) -> Optional[PriceLevel]:
        """
        Trouve le niveau le plus proche et pertinent.
        """

        # Extraire TOUS les niveaux
        all_levels = self._extract_levels_from_snapshot(snapshot, price, symbol)

        if not all_levels:
            logger.warning(f"[{symbol}] ❌ Aucun niveau trouvé!")
            return None

        logger.info(f"[{symbol}] {len(all_levels)} niveaux détectés au total")

        # Trier par distance
        all_levels.sort(key=lambda x: x.distance_ticks)

        # Log tous les niveaux proches
        max_dist = self.MAX_DISTANCE.get(symbol, 15)
        close_levels = [l for l in all_levels if l.distance_ticks <= max_dist * 2]

        if close_levels:
            logger.info(f"[{symbol}] Niveaux proches (< {max_dist * 2:.0f}t):")
            for lvl in close_levels[:10]:  # Top 10
                priority_emoji = "💎" if lvl.priority == 100 else "⭐" if lvl.priority >= 80 else ""
                logger.info(
                    f"   {priority_emoji} {lvl.description} - {lvl.distance_ticks:.0f}t "
                    f"(priority={lvl.priority})"
                )

        # Retourner le niveau le plus proche avec meilleure priorité
        best_level = None
        best_score = -1

        for level in all_levels:
            # Score = (Priorité × Strength) / Distance
            # Favorise niveaux proches avec haute priorité
            score = (level.priority * level.strength) / max(level.distance_ticks, 0.5)

            if score > best_score:
                best_score = score
                best_level = level

        return best_level

    def validate_proximity(self,
                          snapshot: Dict,
                          price: float,
                          symbol: str,
                          direction: str) -> Tuple[bool, Optional[str], Optional[PriceLevel]]:
        """
        Valide que le prix est suffisamment proche d'un niveau important.

        Returns:
            tuple: (valide, raison_rejet, niveau_utilisé)
        """

        # Trouver niveau le plus proche
        nearest_level = self.find_nearest_level(snapshot, price, symbol, direction)

        if nearest_level is None:
            reason = "Aucun niveau important trouvé dans le snapshot"
            logger.warning(f"[{symbol}] ❌ Proximité: {reason}")
            return False, reason, None

        # Vérifier distance maximale
        max_dist = self.MAX_DISTANCE.get(symbol, 15)

        if nearest_level.distance_ticks > max_dist:
            reason = (
                f"Trop loin du niveau le plus proche ({nearest_level.description}) "
                f"- Distance: {nearest_level.distance_ticks:.0f}t > {max_dist}t max"
            )
            logger.warning(f"[{symbol}] ❌ Proximité REJETÉE: {reason}")

            # Log les 3 niveaux les plus proches pour debug
            all_levels = self._extract_levels_from_snapshot(snapshot, price, symbol)
            all_levels.sort(key=lambda x: x.distance_ticks)
            logger.info(f"[{symbol}] Top 3 niveaux les plus proches:")
            for lvl in all_levels[:3]:
                logger.info(f"   {lvl.description} - {lvl.distance_ticks:.0f}t")

            return False, reason, nearest_level

        # ✅ Valide!
        priority_emoji = "💎" if nearest_level.priority == 100 else "⭐" if nearest_level.priority >= 80 else "✓"
        logger.info(
            f"[{symbol}] ✅ Proximité OK: {priority_emoji} {nearest_level.description} "
            f"à {nearest_level.distance_ticks:.0f}t (< {max_dist}t max)"
        )

        return True, None, nearest_level


# Instance globale
level_proximity_validator = LevelProximityValidator()
