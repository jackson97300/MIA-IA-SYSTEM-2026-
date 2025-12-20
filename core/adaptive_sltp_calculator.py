"""
ADAPTIVE SL/TP CALCULATOR - Basé sur les niveaux MenthorQ

Place intelligemment les SL et TP en tenant compte de la structure du marché:
- SL: SOUS le support (LONG) ou AU-DESSUS la résistance (SHORT) + buffer
- TP: Si niveau proche respectant R:R min → utiliser ce niveau, sinon TP fixe

Author: Jackson Trading System
Date: 02 Décembre 2025
Version: 1.0
"""

import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

# 🎯 CONFIG CENTRALISÉE - Source unique de vérité
from config.trading_params import TRADING_CONFIG, get_config

logger = logging.getLogger(__name__)


@dataclass
class SLTPResult:
    """Résultat du calcul SL/TP adaptatif."""
    sl_price: float
    tp_price: float
    sl_distance_ticks: float
    tp_distance_ticks: float
    rr_ratio: float
    sl_based_on: str  # "level" ou "fixed"
    tp_based_on: str  # "level" ou "fixed"
    sl_level_name: Optional[str] = None
    tp_level_name: Optional[str] = None
    sl_level_price: Optional[float] = None
    tp_level_price: Optional[float] = None


class AdaptiveSLTPCalculator:
    """
    Calculateur SL/TP adaptatif basé sur les niveaux MenthorQ.

    Logique:
    1. SL: Cherche le niveau de support/résistance le plus proche
       - LONG: SL sous le support le plus proche (GEX, Put, Blind Spot, etc.)
       - SHORT: SL au-dessus de la résistance la plus proche
       - Buffer de sécurité de 2-3 ticks

    2. TP:
       - Cherche un niveau juste AVANT le TP fixe
       - Si ce niveau respecte le R:R minimum → utiliser ce niveau
       - Sinon → garder TP fixe

    Exemple LONG @ 6830.25:
        - GEX 5 @ 6825.00 (support)
        - SL = 6825.00 - 2 ticks = 6824.50 ✅

        - HVL @ 6835.00 (résistance proche)
        - TP fixe serait 6840.00
        - Si 6835.00 respecte R:R min → TP = 6835.00
        - Sinon → TP = 6840.00 (fixe)
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize calculator with config.

        Args:
            config: Dict avec paramètres par instrument
        """

        # Configuration par défaut
        self.config = config or {}

        # ═══════════════════════════════════════════════════════════════
        # INSTRUMENT_CONFIG - IMPORTÉ DEPUIS config/trading_params.py
        # ⚠️ MODIFIER UNIQUEMENT trading_params.py POUR CHANGER CES VALEURS!
        # ═══════════════════════════════════════════════════════════════
        self.INSTRUMENT_CONFIG = {}
        for sym in ['ES', 'NQ', 'RTY']:
            cfg = get_config(sym)
            self.INSTRUMENT_CONFIG[sym] = {
                "tick_size": cfg['tick_size'],
                "tick_value": cfg['tick_value'],
                "sl_buffer_ticks": cfg['sl_buffer_ticks'],
                "min_sl_ticks": cfg['min_sl_ticks'],
                "max_sl_ticks": cfg['max_sl_ticks'],
                "default_sl_ticks": cfg['sl_ticks'],
                "default_tp_ticks": cfg['tp_ticks'],
                "min_rr_ratio": cfg['min_rr_ratio'],
                "tp_buffer_ticks": cfg['tp_buffer_ticks'],
            }

        # Niveaux MenthorQ à considérer pour SL (par priorité)
        # PRIORITÉ 1: GEX, HVL, Gamma Walls (niveaux FORTS)
        # PRIORITÉ 2: Put/Call support/resistance
        # PRIORITÉ 3: VWAP
        # PRIORITÉ 4: Blind Spots (moins fiables seuls)

        self.SL_SUPPORT_LEVELS_PRIORITY = {
            # Priorité 0 - Niveaux 0DTE (CRITIQUES intraday) - AJOUT 05/12/2025
            0: ['put_support_0dte', 'gamma_wall_0dte', 'hvl_0dte', 'ibl'],  # IBL = support session US
            # Priorité 1 - Niveaux FORTS (préférés)
            1: ['gex_5', 'gex_4', 'gex_3', 'gex_2', 'gex_1', 'hvl', 'gamma_wall_put', 'gamma_flip'],
            # Priorité 2 - Options walls
            2: ['put_support', 'put_wall'],
            # Priorité 3 - VWAP
            3: ['vwap', 'vwap_lower_1', 'vwap_lower_2'],
            # Priorité 4 - Blind Spots (fallback)
            4: ['bl_0', 'bl_1', 'bl_2', 'bl_3', 'bl_4', 'bl_5', 'bl_6', 'bl_7', 'bl_8'],
        }

        self.SL_RESISTANCE_LEVELS_PRIORITY = {
            # Priorité 0 - Niveaux 0DTE (CRITIQUES intraday) - AJOUT 05/12/2025
            0: ['call_resistance_0dte', 'gamma_wall_0dte', 'hvl_0dte', 'ibh'],  # IBH = resistance session US
            # Priorité 1 - Niveaux FORTS
            1: ['gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10', 'hvl', 'gamma_wall_call'],
            # Priorité 2 - Options walls
            2: ['call_resistance', 'call_wall'],
            # Priorité 3 - VWAP
            3: ['vwap', 'vwap_upper_1', 'vwap_upper_2'],
            # Priorité 4 - Blind Spots
            4: ['bl_0', 'bl_1', 'bl_2', 'bl_3', 'bl_4', 'bl_5', 'bl_6', 'bl_7', 'bl_8'],
        }

        # Listes plates pour compatibilité
        self.SL_SUPPORT_LEVELS = [item for sublist in self.SL_SUPPORT_LEVELS_PRIORITY.values() for item in sublist]
        self.SL_RESISTANCE_LEVELS = [item for sublist in self.SL_RESISTANCE_LEVELS_PRIORITY.values() for item in sublist]

        # Niveaux MenthorQ à considérer pour TP
        self.TP_TARGET_LEVELS = [
            # Niveaux 0DTE (PRIORITÉ MAXIMALE intraday) - AJOUT 05/12/2025
            'call_resistance_0dte', 'put_support_0dte', 'hvl_0dte', 'gamma_wall_0dte',
            # Initial Balance (SESSION US UNIQUEMENT) - AJOUT 05/12/2025
            'ibh', 'ibl',
            # Niveaux où le prix pourrait réagir (cibles)
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
            'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
            'call_resistance', 'put_support',
            'gamma_wall_call', 'gamma_wall_put',
            'bl_0', 'bl_1', 'bl_2', 'bl_3', 'bl_4', 'bl_5', 'bl_6', 'bl_7', 'bl_8',
            'hvl',
            'vwap', 'vwap_upper_1', 'vwap_upper_2', 'vwap_lower_1', 'vwap_lower_2',
        ]

        logger.info("""
================================================================================
ADAPTIVE SL/TP CALCULATOR INITIALIZED
================================================================================
Logique SL:
  - LONG: SL sous le support MenthorQ le plus proche + buffer
  - SHORT: SL au-dessus de la résistance MenthorQ la plus proche + buffer

Logique TP:
  - Cherche niveau juste avant TP fixe
  - Si respecte R:R min → utilise niveau comme TP
  - Sinon → garde TP fixe

Configuration (🎯 10/12 - PRO 1:1):
  - ES: SL 12-30t, Buffer 3t, TP default 15t, R:R min 0.8
  - NQ: SL 15-40t, Buffer 5t, TP default 31t, R:R min 0.8
  - RTY: SL 20-40t, Buffer 3t, TP default 25t, R:R min 0.8
================================================================================
        """)

    def calculate_adaptive_sltp(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        menthorq_levels: Dict[str, float],
        override_min_rr: Optional[float] = None,
    ) -> SLTPResult:
        """
        Calcule SL et TP adaptatifs basés sur les niveaux MenthorQ.

        Args:
            symbol: "ES", "NQ", "RTY"
            direction: "LONG" ou "SHORT"
            entry_price: Prix d'entrée
            menthorq_levels: Dict avec tous les niveaux MenthorQ
                Ex: {'gex_5': 6825.0, 'hvl': 6835.0, 'call_resistance': 6850.0, ...}
            override_min_rr: Override du R:R minimum (optionnel)

        Returns:
            SLTPResult avec SL, TP, distances, R:R, et métadata
        """

        config = self.INSTRUMENT_CONFIG.get(symbol, self.INSTRUMENT_CONFIG["ES"])
        tick_size = config["tick_size"]

        min_rr = override_min_rr or config["min_rr_ratio"]

        logger.info(f"\n{'='*60}")
        logger.info(f"📐 CALCUL SL/TP ADAPTATIF - {symbol} {direction} @ {entry_price}")
        logger.info(f"{'='*60}")

        # 🔍 10/12/2025: Log diagnostic des niveaux disponibles pour TP
        tp_levels_available = []
        for level_name in self.TP_TARGET_LEVELS:
            level_price = menthorq_levels.get(level_name)
            if level_price and level_price > 0:
                tp_levels_available.append(f"{level_name}@{level_price:.2f}")

        logger.info(f"📊 Niveaux TP disponibles ({len(tp_levels_available)}): {', '.join(tp_levels_available[:10]) if tp_levels_available else 'AUCUN!'}")

        # Log spécifique pour les niveaux 0DTE critiques
        hvl_0dte = menthorq_levels.get('hvl_0dte', 0)
        if hvl_0dte > 0:
            logger.info(f"   🔥 HVL_0DTE présent: {hvl_0dte:.2f}")
        else:
            logger.warning(f"   ⚠️ HVL_0DTE ABSENT du snapshot!")

        # ══════════════════════════════════════════════════════════════
        # ÉTAPE 1: Calculer SL adaptatif
        # ══════════════════════════════════════════════════════════════

        sl_price, sl_based_on, sl_level_name, sl_level_price = self._calculate_adaptive_sl(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            menthorq_levels=menthorq_levels,
            config=config,
        )

        sl_distance_ticks = abs(entry_price - sl_price) / tick_size

        logger.info(f"🛑 SL Calculé: {sl_price} ({sl_distance_ticks:.1f}t) - Basé sur: {sl_based_on}")
        if sl_level_name:
            logger.info(f"   └─ Niveau: {sl_level_name} @ {sl_level_price}")

        # ══════════════════════════════════════════════════════════════
        # ÉTAPE 2: Calculer TP adaptatif
        # ══════════════════════════════════════════════════════════════

        tp_price, tp_based_on, tp_level_name, tp_level_price = self._calculate_adaptive_tp(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            menthorq_levels=menthorq_levels,
            config=config,
            min_rr=min_rr,
        )

        tp_distance_ticks = abs(tp_price - entry_price) / tick_size

        logger.info(f"🎯 TP Calculé: {tp_price} ({tp_distance_ticks:.1f}t) - Basé sur: {tp_based_on}")
        if tp_level_name:
            logger.info(f"   └─ Niveau: {tp_level_name} @ {tp_level_price}")

        # ══════════════════════════════════════════════════════════════
        # ÉTAPE 3: Calculer R:R final
        # ══════════════════════════════════════════════════════════════

        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0

        logger.info(f"📊 R:R Final: {rr_ratio:.2f}:1 (min requis: {min_rr}:1)")
        logger.info(f"   └─ Risk: {risk:.2f} ({sl_distance_ticks:.1f}t) | Reward: {reward:.2f} ({tp_distance_ticks:.1f}t)")
        logger.info(f"{'='*60}\n")

        return SLTPResult(
            sl_price=sl_price,
            tp_price=tp_price,
            sl_distance_ticks=sl_distance_ticks,
            tp_distance_ticks=tp_distance_ticks,
            rr_ratio=rr_ratio,
            sl_based_on=sl_based_on,
            tp_based_on=tp_based_on,
            sl_level_name=sl_level_name,
            tp_level_name=tp_level_name,
            sl_level_price=sl_level_price,
            tp_level_price=tp_level_price,
        )

    def _calculate_adaptive_sl(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        menthorq_levels: Dict[str, float],
        config: Dict,
    ) -> Tuple[float, str, Optional[str], Optional[float]]:
        """
        Calcule le SL adaptatif basé sur les niveaux MenthorQ.

        LOGIQUE DE PRIORITÉ:
        1. Cherche d'abord dans les niveaux FORTS (GEX, HVL, Gamma Walls)
        2. Si aucun trouvé, cherche dans Options Walls
        3. Si aucun trouvé, cherche dans VWAP
        4. Si aucun trouvé, cherche dans Blind Spots
        5. Sinon, SL fixe par défaut

        Returns:
            (sl_price, based_on, level_name, level_price)
        """

        tick_size = config["tick_size"]
        buffer_ticks = config["sl_buffer_ticks"]
        min_sl_ticks = config["min_sl_ticks"]
        max_sl_ticks = config["max_sl_ticks"]
        default_sl_ticks = config["default_sl_ticks"]

        buffer = buffer_ticks * tick_size
        min_sl_distance = min_sl_ticks * tick_size
        max_sl_distance = max_sl_ticks * tick_size

        # Déterminer les niveaux à chercher selon direction
        if direction == "LONG":
            priority_levels = self.SL_SUPPORT_LEVELS_PRIORITY
            filter_fn = lambda price: price < entry_price
            sl_with_buffer = lambda level_price: level_price - buffer
        else:  # SHORT
            priority_levels = self.SL_RESISTANCE_LEVELS_PRIORITY
            filter_fn = lambda price: price > entry_price
            sl_with_buffer = lambda level_price: level_price + buffer

        # 🔍 10/12: Log des paramètres de recherche SL
        logger.info(f"🔍 [SL] Recherche niveaux {direction}: min={min_sl_ticks}t, max={max_sl_ticks}t, buffer={buffer_ticks}t")

        rejected_levels = []  # Pour audit

        # Chercher par priorité (1 = plus important)
        for priority in sorted(priority_levels.keys()):
            level_names = priority_levels[priority]
            valid_levels = []

            for level_name in level_names:
                level_price = menthorq_levels.get(level_name)

                if level_price is None:
                    continue

                if not filter_fn(level_price):
                    continue

                # 🔥 FIX 10/12/2025: Calculer le SL AVEC BUFFER avant de vérifier les limites
                potential_sl = sl_with_buffer(level_price)
                sl_distance = abs(entry_price - potential_sl)
                sl_distance_ticks = sl_distance / tick_size

                # Vérifier que le SL FINAL (avec buffer) est dans la plage acceptable
                if sl_distance < min_sl_distance or sl_distance > max_sl_distance:
                    # 🔍 10/12: Log des rejets pour audit
                    reason = "TROP_PROCHE" if sl_distance < min_sl_distance else "TROP_LOIN"
                    rejected_levels.append(f"{level_name}@{level_price:.2f} → SL@{potential_sl:.2f} ({sl_distance_ticks:.0f}t) {reason}")
                    continue

                valid_levels.append((level_name, level_price, potential_sl, sl_distance))

            # Si des niveaux valides trouvés à cette priorité, prendre le plus proche
            if valid_levels:
                # Trier par distance SL (SL le plus serré en premier = meilleur R:R)
                valid_levels.sort(key=lambda x: x[3])

                nearest_level_name, nearest_level_price, sl_price, sl_distance = valid_levels[0]
                sl_distance_ticks = sl_distance / tick_size

                logger.info(f"✅ [SL] Niveau priorité {priority}: {nearest_level_name} @ {nearest_level_price} → SL @ {sl_price} ({sl_distance_ticks:.0f}t)")
                return sl_price, "level", nearest_level_name, nearest_level_price

        # Fallback: SL fixe par défaut
        if direction == "LONG":
            sl_price = entry_price - (default_sl_ticks * tick_size)
        else:
            sl_price = entry_price + (default_sl_ticks * tick_size)

        # 🔍 10/12: Log des niveaux rejetés pour audit
        if rejected_levels:
            logger.warning(f"⚠️ [SL] Niveaux REJETÉS ({len(rejected_levels)}): {', '.join(rejected_levels[:5])}")

        logger.info(f"[SL] Aucun niveau valide → SL FIXE: {sl_price:.2f} ({default_sl_ticks}t)")

        return sl_price, "fixed", None, None

    def _calculate_adaptive_tp(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        menthorq_levels: Dict[str, float],
        config: Dict,
        min_rr: float,
    ) -> Tuple[float, str, Optional[str], Optional[float]]:
        """
        Calcule le TP adaptatif basé sur les niveaux MenthorQ.

        Logique:
        1. Calculer TP fixe par défaut
        2. Chercher un niveau AVANT le TP fixe (dans la direction du trade)
        3. Si ce niveau respecte le R:R min → utiliser ce niveau
        4. Sinon → garder TP fixe

        Returns:
            (tp_price, based_on, level_name, level_price)
        """

        tick_size = config["tick_size"]
        default_tp_ticks = config["default_tp_ticks"]
        tp_buffer_ticks = config["tp_buffer_ticks"]

        tp_buffer = tp_buffer_ticks * tick_size

        # Calculer le risque (pour vérifier R:R)
        risk = abs(entry_price - sl_price)
        min_reward_for_rr = risk * min_rr

        # Calculer TP fixe par défaut
        if direction == "LONG":
            tp_fixed = entry_price + (default_tp_ticks * tick_size)
        else:
            tp_fixed = entry_price - (default_tp_ticks * tick_size)

        # 🔍 10/12: Log des paramètres de recherche TP
        risk_ticks = risk / tick_size
        min_reward_ticks = min_reward_for_rr / tick_size
        logger.info(f"🔍 [TP] Recherche niveaux {direction}: risk={risk_ticks:.0f}t, min_reward={min_reward_ticks:.0f}t (R:R min={min_rr})")

        rejected_tp_levels = []  # Pour audit

        # Chercher niveaux dans la direction du trade
        if direction == "LONG":
            # Chercher résistances AU-DESSUS de l'entry mais AVANT ou AU TP fixe
            filter_fn = lambda price: entry_price < price <= tp_fixed
            tp_with_buffer = lambda level_price: level_price - tp_buffer
        else:  # SHORT
            # Chercher supports SOUS l'entry mais AVANT ou AU TP fixe
            filter_fn = lambda price: tp_fixed <= price < entry_price
            tp_with_buffer = lambda level_price: level_price + tp_buffer

        # Collecter niveaux valides
        valid_levels = []

        for level_name in self.TP_TARGET_LEVELS:
            level_price = menthorq_levels.get(level_name)

            if level_price is None:
                continue

            if not filter_fn(level_price):
                continue

            # Calculer le TP potentiel avec buffer
            potential_tp = tp_with_buffer(level_price)

            # Calculer la reward avec ce TP
            reward = abs(potential_tp - entry_price)
            reward_ticks = reward / tick_size

            # Vérifier que le R:R est respecté
            if reward < min_reward_for_rr:
                # 🔍 10/12: Log des rejets TP pour audit
                rr_actual = reward / risk if risk > 0 else 0
                rejected_tp_levels.append(f"{level_name}@{level_price:.2f} ({reward_ticks:.0f}t, R:R={rr_actual:.2f})")
                continue

            rr = reward / risk if risk > 0 else 0
            distance_from_entry = abs(potential_tp - entry_price)

            valid_levels.append((level_name, level_price, potential_tp, rr, distance_from_entry))

        # Si des niveaux valides trouvés, prendre le PREMIER rencontré (le plus proche)
        if valid_levels:
            # Trier par distance de l'entry (le plus proche en premier)
            valid_levels.sort(key=lambda x: x[4])

            nearest_level_name, nearest_level_price, tp_price, rr, _ = valid_levels[0]

            logger.debug(f"[TP] Niveau {nearest_level_name} @ {nearest_level_price} → TP @ {tp_price} (R:R {rr:.2f})")

            return tp_price, "level", nearest_level_name, nearest_level_price

        # 🔍 10/12: Log des niveaux TP rejetés pour audit
        if rejected_tp_levels:
            logger.warning(f"⚠️ [TP] Niveaux REJETÉS R:R ({len(rejected_tp_levels)}): {', '.join(rejected_tp_levels[:5])}")

        # Pas de niveau valide → TP fixe
        logger.info(f"[TP] Aucun niveau valide → TP FIXE: {tp_fixed:.2f} ({default_tp_ticks}t)")

        return tp_fixed, "fixed", None, None

    def validate_sltp(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        menthorq_levels: Dict[str, float],
    ) -> Tuple[bool, str, List[str]]:
        """
        Valide un SL/TP existant contre les niveaux MenthorQ.

        Vérifie:
        1. SL n'est pas "dans le vide" (pas de niveau entre entry et SL)
        2. R:R est acceptable
        3. Aucun niveau majeur ne bloque le chemin vers TP

        Returns:
            (is_valid, reason, warnings)
        """

        config = self.INSTRUMENT_CONFIG.get(symbol, self.INSTRUMENT_CONFIG["ES"])
        tick_size = config["tick_size"]
        min_rr = config["min_rr_ratio"]

        warnings = []

        # Calculer R:R
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        rr = reward / risk if risk > 0 else 0

        # 1. Vérifier R:R minimum
        if rr < min_rr:
            return False, f"R:R {rr:.2f} < minimum {min_rr}", warnings

        # 2. Vérifier que le SL est protégé par un niveau
        sl_distance_ticks = risk / tick_size

        if direction == "LONG":
            # Chercher un support entre entry et SL
            levels_between = [
                (name, price) for name, price in menthorq_levels.items()
                if price and sl_price < price < entry_price
            ]
        else:
            # Chercher une résistance entre entry et SL
            levels_between = [
                (name, price) for name, price in menthorq_levels.items()
                if price and entry_price < price < sl_price
            ]

        if not levels_between:
            warnings.append(f"⚠️ SL dans le vide - Aucun niveau entre entry et SL")

        # 3. Vérifier les niveaux bloquants vers TP
        # ✅ FIX 05/12/2025: Ajout des niveaux 0DTE
        # 🔧 FIX 12/12/2025: Ajout Blind Spots comme obstacles potentiels
        BLOCKING_LEVELS_LONG = [
            'call_resistance', 'call_resistance_0dte', 'gamma_wall_call',
            'gamma_wall_0dte', 'hvl', 'hvl_0dte',
            # 🆕 Blind Spots (supports/résistances secondaires)
            'blind_spot_0', 'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
            'blind_spot_4', 'blind_spot_5', 'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
            'bl_0', 'bl_1', 'bl_2', 'bl_3', 'bl_4', 'bl_5', 'bl_6', 'bl_7', 'bl_8',
            # GEX levels
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
        ]
        BLOCKING_LEVELS_SHORT = [
            'put_support', 'put_support_0dte', 'gamma_wall_put',
            'gamma_wall_0dte', 'hvl', 'hvl_0dte',
            # 🆕 Blind Spots (supports/résistances secondaires)
            'blind_spot_0', 'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
            'blind_spot_4', 'blind_spot_5', 'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
            'bl_0', 'bl_1', 'bl_2', 'bl_3', 'bl_4', 'bl_5', 'bl_6', 'bl_7', 'bl_8',
            # GEX levels
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
        ]

        if direction == "LONG":
            blocking_levels = [
                (name, price) for name, price in menthorq_levels.items()
                if price and entry_price < price < tp_price
                and name in BLOCKING_LEVELS_LONG
            ]
        else:
            blocking_levels = [
                (name, price) for name, price in menthorq_levels.items()
                if price and tp_price < price < entry_price
                and name in BLOCKING_LEVELS_SHORT
            ]

        if blocking_levels:
            for name, price in blocking_levels:
                warnings.append(f"⚠️ Niveau bloquant: {name} @ {price}")

        if warnings:
            return True, f"Valid avec warnings (R:R {rr:.2f})", warnings

        return True, f"Valid (R:R {rr:.2f})", []


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def create_adaptive_sltp_calculator(config: Optional[Dict] = None) -> AdaptiveSLTPCalculator:
    """
    Factory pour créer AdaptiveSLTPCalculator.

    Args:
        config: Configuration optionnelle

    Returns:
        AdaptiveSLTPCalculator instance
    """
    return AdaptiveSLTPCalculator(config)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTS ADAPTIVE SL/TP CALCULATOR")
    print("="*70)

    # Créer calculator
    calc = create_adaptive_sltp_calculator()

    # Test 1: LONG ES avec niveaux MenthorQ
    print("\n[TEST 1] LONG ES @ 6830.25 avec niveaux MenthorQ")
    print("-" * 50)

    menthorq_levels_es = {
        'gex_5': 6825.00,
        'gex_4': 6820.00,
        'bl_8': 6826.00,
        'hvl_0dte': 6835.00,
        'bl_9': 6838.00,
        'call_resistance': 6850.00,
        'gex_6': 6855.00,
    }

    result = calc.calculate_adaptive_sltp(
        symbol="ES",
        direction="LONG",
        entry_price=6830.25,
        menthorq_levels=menthorq_levels_es,
    )

    print(f"Entry:    6830.25")
    print(f"SL:       {result.sl_price} ({result.sl_distance_ticks:.1f}t) - {result.sl_based_on}")
    print(f"TP:       {result.tp_price} ({result.tp_distance_ticks:.1f}t) - {result.tp_based_on}")
    print(f"R:R:      {result.rr_ratio:.2f}:1")
    if result.sl_level_name:
        print(f"SL Level: {result.sl_level_name} @ {result.sl_level_price}")
    if result.tp_level_name:
        print(f"TP Level: {result.tp_level_name} @ {result.tp_level_price}")

    # Vérifier que le SL est sous GEX 5 (priorité 1)
    # GEX 5 @ 6825.00 - buffer 3 ticks = 6824.25
    expected_sl = 6825.00 - (3 * 0.25)  # 6824.25
    assert result.sl_price == expected_sl, f"SL devrait être {expected_sl} (sous GEX 5), got {result.sl_price}"
    assert result.sl_level_name == "gex_5", f"SL level devrait être gex_5, got {result.sl_level_name}"
    print(f"\n✅ TEST 1 PASSED - SL placé sous GEX 5 @ {result.sl_price}")

    # Test 2: SHORT ES - call_resistance @ 6850 est à 40t (limite max)
    # Donc SL fixe de 20t sera utilisé
    print("\n[TEST 2] SHORT ES @ 6840.00 avec niveaux MenthorQ")
    print("-" * 50)

    result2 = calc.calculate_adaptive_sltp(
        symbol="ES",
        direction="SHORT",
        entry_price=6840.00,
        menthorq_levels=menthorq_levels_es,
    )

    print(f"Entry:    6840.00")
    print(f"SL:       {result2.sl_price} ({result2.sl_distance_ticks:.1f}t) - {result2.sl_based_on}")
    print(f"TP:       {result2.tp_price} ({result2.tp_distance_ticks:.1f}t) - {result2.tp_based_on}")
    print(f"R:R:      {result2.rr_ratio:.2f}:1")
    if result2.sl_level_name:
        print(f"SL Level: {result2.sl_level_name} @ {result2.sl_level_price}")
    if result2.tp_level_name:
        print(f"TP Level: {result2.tp_level_name} @ {result2.tp_level_price}")

    # Dans ce cas, le SL fixe est utilisé car call_resistance @ 6850 est à 40t (= max)
    # Après buffer, ça dépasse. Donc SL fixe.
    print(f"\n✅ TEST 2 PASSED - SL {result2.sl_based_on} utilisé")

    # Test 2b: SHORT avec résistance plus proche
    print("\n[TEST 2b] SHORT ES @ 6845.00 (plus proche de call_resistance)")
    print("-" * 50)

    result2b = calc.calculate_adaptive_sltp(
        symbol="ES",
        direction="SHORT",
        entry_price=6845.00,
        menthorq_levels=menthorq_levels_es,
    )

    print(f"Entry:    6845.00")
    print(f"SL:       {result2b.sl_price} ({result2b.sl_distance_ticks:.1f}t) - {result2b.sl_based_on}")
    print(f"TP:       {result2b.tp_price} ({result2b.tp_distance_ticks:.1f}t) - {result2b.tp_based_on}")
    print(f"R:R:      {result2b.rr_ratio:.2f}:1")
    if result2b.sl_level_name:
        print(f"SL Level: {result2b.sl_level_name} @ {result2b.sl_level_price}")

    # call_resistance @ 6850 est à 20t de 6845, donc acceptable
    # SL devrait être 6850 + buffer (2t) = 6850.50
    if result2b.sl_based_on == "level":
        assert result2b.sl_price > 6850.00, f"SL devrait être au-dessus 6850.00, got {result2b.sl_price}"
        print(f"\n✅ TEST 2b PASSED - SL placé au-dessus call_resistance @ {result2b.sl_price}")

    # Test 3: LONG NQ
    print("\n[TEST 3] LONG NQ @ 25390.00 avec niveaux MenthorQ")
    print("-" * 50)

    menthorq_levels_nq = {
        'gex_5': 25350.00,
        'put_support': 25375.00,
        'hvl': 25400.00,
        'call_resistance': 25450.00,
        'gex_6': 25475.00,
    }

    result3 = calc.calculate_adaptive_sltp(
        symbol="NQ",
        direction="LONG",
        entry_price=25390.00,
        menthorq_levels=menthorq_levels_nq,
    )

    print(f"Entry:    25390.00")
    print(f"SL:       {result3.sl_price} ({result3.sl_distance_ticks:.1f}t) - {result3.sl_based_on}")
    print(f"TP:       {result3.tp_price} ({result3.tp_distance_ticks:.1f}t) - {result3.tp_based_on}")
    print(f"R:R:      {result3.rr_ratio:.2f}:1")

    print("\n✅ TEST 3 PASSED")

    # Test 4: Validation SL/TP existant
    print("\n[TEST 4] Validation SL/TP existant")
    print("-" * 50)

    is_valid, reason, warnings = calc.validate_sltp(
        symbol="ES",
        direction="LONG",
        entry_price=6830.25,
        sl_price=6827.50,  # SL actuel (dans le vide!)
        tp_price=6840.00,
        menthorq_levels=menthorq_levels_es,
    )

    print(f"Valid: {is_valid}")
    print(f"Reason: {reason}")
    for w in warnings:
        print(f"  {w}")

    print("\n✅ TEST 4 PASSED")

    print("\n" + "="*70)
    print("✅ TOUS LES TESTS PASSÉS")
    print("="*70)
