#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
STRATÉGIE VWAP STANDARD DEVIATION + OPTIONS CONFLUENCE
═══════════════════════════════════════════════════════════════════════════════

📖 BASÉE SUR : Bible MenthorQ v2.0
🎯 CONCEPT : Confluence des bandes VWAP (±1σ, ±2σ) avec niveaux options

LOGIQUE :
─────────
1. VWAP Bands définissent les zones de support/résistance statistiques
2. Niveaux Options (HVL, GEX, Next Wall) = zones magnétiques gamma
3. Confluence des deux = setups haute probabilité

SCÉNARIOS :
───────────
✅ Scenario 1 : VWAP Mean Reversion (Prix @ ±1σ ou ±2σ)
✅ Scenario 2 : VWAP/HVL Sandwich (Prix entre VWAP et HVL)
✅ Scenario 3 : VWAP/Next Wall Confluence (Support/Résistance renforcé)
✅ Scenario 4 : VWAP/GEX Bounce (Rejection sur confluence)
✅ Scenario 5 : Triple Confluence (VWAP + HVL + Next Wall)
✅ Scenario 6 : VWAP Band Breakout + Gamma Flip

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VWAPZone(Enum):
    """Zones VWAP Standard Deviation"""
    EXTREME_OVERBOUGHT = "VWAP+2σ"     # Prix > VWAP +2σ
    OVERBOUGHT = "VWAP+1σ"              # Prix entre VWAP+1σ et VWAP+2σ
    ABOVE_MEAN = "VWAP_ABOVE"           # Prix entre VWAP et VWAP+1σ
    AT_MEAN = "VWAP"                    # Prix proche VWAP (±10 ticks)
    BELOW_MEAN = "VWAP_BELOW"           # Prix entre VWAP-1σ et VWAP
    OVERSOLD = "VWAP-1σ"                # Prix entre VWAP-2σ et VWAP-1σ
    EXTREME_OVERSOLD = "VWAP-2σ"        # Prix < VWAP -2σ


class ConfluenceType(Enum):
    """Types de confluence"""
    VWAP_HVL_SANDWICH = "VWAP/HVL Sandwich"
    VWAP_NEXTWALL = "VWAP/Next Wall"
    VWAP_GEX = "VWAP/GEX Level"
    VWAP_CALL_PUT = "VWAP/Call-Put Channel"
    TRIPLE_CONFLUENCE = "Triple Confluence"
    VWAP_BAND_BOUNCE = "VWAP Band Bounce"


@dataclass
class VWAPBands:
    """Structure des bandes VWAP"""
    vwap: float
    vwap_up1: float  # +1σ
    vwap_up2: float  # +2σ
    vwap_dn1: float  # -1σ
    vwap_dn2: float  # -2σ
    current_zone: VWAPZone
    distance_to_mean: float  # En ticks
    distance_to_mean_atr: float  # En ATR


@dataclass
class OptionsLevels:
    """Niveaux options MenthorQ"""
    hvl: float
    next_wall_price: float
    next_wall_side: str  # "call" ou "put"
    next_wall_strength: float
    gex_levels: List[float]
    call_resistance: float
    put_support: float
    blind_spots: List[float]


@dataclass
class ConfluenceSignal:
    """Signal de confluence détecté"""
    type: ConfluenceType
    direction: str  # "LONG" ou "SHORT"
    confidence: float  # 0.0 - 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    vwap_zone: VWAPZone
    confluence_description: str
    triggers: List[str]


class VWAPSDOptionsConfluenceStrategy:
    """
    Stratégie de confluence VWAP Standard Deviation + Options
    """

    def __init__(self, config: dict):
        self.config = config
        self.name = "vwap_sd_options_confluence"

        # Seuils de distance pour confluence (en ticks)
        # 🔧 OPTIMISATION 17/11/2025: Augmentation des seuils pour accepter plus de signaux
        #    Problème: 90% des signaux rejetés car seuils trop stricts
        #    Solution: Augmenter seuils de +50% à +100%
        self.CONFLUENCE_THRESHOLDS = {
            "ES": {"vwap_hvl": 30, "vwap_wall": 60, "vwap_gex": 75},  # +50% à +100%
            "NQ": {"vwap_hvl": 75, "vwap_wall": 120, "vwap_gex": 150},  # +50% à +100%
            "RTY": {"vwap_hvl": 15, "vwap_wall": 45, "vwap_gex": 60}  # +50% à +100%
        }

        # Zones de bounce VWAP (distance max pour considérer un bounce)
        # 🔧 OPTIMISATION 2025-11-18: Encore plus permissif pour capter plus de setups
        #    Problème: 80% des setups manqués (zones trop strictes)
        #    Solution: Augmenter zones bounce de +50% à +67%
        self.VWAP_BOUNCE_ZONES = {
            "ES": {"sd1": 30, "sd2": 50},   # 20→30 (+50%), 30→50 (+67%)
            "NQ": {"sd1": 60, "sd2": 100},  # 40→60 (+50%), 60→100 (+67%)
            "RTY": {"sd1": 25, "sd2": 40}   # 15→25 (+67%), 25→40 (+60%)
        }

        logger.info(f"✅ Stratégie {self.name} initialisée avec Bible MenthorQ v2.0")

    def _get_tick_size(self, symbol: str) -> float:
        """Retourne la taille du tick selon le symbole"""
        if "ES" in symbol.upper():
            return 0.25
        elif "NQ" in symbol.upper():
            return 0.25
        elif "RTY" in symbol.upper() or "RTY" in symbol.upper():
            return 0.10
        return 0.25

    def _detect_symbol(self, data: dict) -> str:
        """Détecte le symbole à partir des données"""
        sym = data.get("sym", "")
        if "ES" in sym.upper():
            return "ES"
        elif "NQ" in sym.upper():
            return "NQ"
        elif "RTY" in sym.upper() or "2RTY" in sym.upper():
            return "RTY"
        return "ES"

    def _calculate_vwap_bands(self, data: dict) -> VWAPBands:
        """
        Calcule les bandes VWAP et détermine la zone actuelle
        """
        mid = data.get("mid", 0)
        vwap = data.get("vwap", 0)
        vwap_up1 = data.get("vwap_up1", 0)
        vwap_up2 = data.get("vwap_up2", 0)
        vwap_dn1 = data.get("vwap_dn1", 0)
        vwap_dn2 = data.get("vwap_dn2", 0)
        atr = data.get("atr", 1.0)

        symbol = self._detect_symbol(data)
        tick_size = self._get_tick_size(symbol)

        # Distance au VWAP
        d_vwap_ticks = (mid - vwap) / tick_size
        d_vwap_atr = abs(mid - vwap) / atr if atr > 0 else 0

        # Déterminer la zone VWAP
        current_zone = self._get_vwap_zone(mid, vwap, vwap_up1, vwap_up2, vwap_dn1, vwap_dn2, tick_size)

        return VWAPBands(
            vwap=vwap,
            vwap_up1=vwap_up1,
            vwap_up2=vwap_up2,
            vwap_dn1=vwap_dn1,
            vwap_dn2=vwap_dn2,
            current_zone=current_zone,
            distance_to_mean=d_vwap_ticks,
            distance_to_mean_atr=d_vwap_atr
        )

    def _get_vwap_zone(self, mid: float, vwap: float, vwap_up1: float,
                       vwap_up2: float, vwap_dn1: float, vwap_dn2: float,
                       tick_size: float) -> VWAPZone:
        """
        Détermine dans quelle zone VWAP le prix se trouve
        """
        tolerance_ticks = 10  # ±10 ticks = "proche du VWAP"

        if mid >= vwap_up2:
            return VWAPZone.EXTREME_OVERBOUGHT
        elif mid >= vwap_up1:
            return VWAPZone.OVERBOUGHT
        elif mid > vwap + (tolerance_ticks * tick_size):
            return VWAPZone.ABOVE_MEAN
        elif mid >= vwap - (tolerance_ticks * tick_size):
            return VWAPZone.AT_MEAN
        elif mid >= vwap_dn1:
            return VWAPZone.BELOW_MEAN
        elif mid >= vwap_dn2:
            return VWAPZone.OVERSOLD
        else:
            return VWAPZone.EXTREME_OVERSOLD

    def _extract_options_levels(self, data: dict) -> OptionsLevels:
        """
        Extrait les niveaux options des données MenthorQ
        """
        next_wall = data.get("next_wall", {})

        gex_levels = []
        for i in range(1, 11):
            gex = data.get(f"gex_{i}")
            if gex:
                gex_levels.append(gex)

        blind_spots = []
        for i in range(10):
            blind = data.get(f"blind_spot_{i}")
            if blind:
                blind_spots.append(blind)

        return OptionsLevels(
            hvl=data.get("hvl", 0),
            next_wall_price=next_wall.get("price", 0) if next_wall else 0,
            next_wall_side=next_wall.get("side", "call") if next_wall else "call",
            next_wall_strength=next_wall.get("strength", 0) if next_wall else 0,
            gex_levels=gex_levels,
            call_resistance=data.get("call_resistance", 0),
            put_support=data.get("put_support", 0),
            blind_spots=blind_spots
        )

    def analyze_from_ml_ready(self, data: dict) -> Optional[ConfluenceSignal]:
        """
        Analyse principale : détecte les scénarios de confluence

        Retourne un signal si confluence détectée, None sinon
        """
        symbol = self._detect_symbol(data)
        tick_size = self._get_tick_size(symbol)
        mid = data.get("mid", 0)

        # Calcul des bandes VWAP
        vwap_bands = self._calculate_vwap_bands(data)

        # Extraction niveaux options
        options_levels = self._extract_options_levels(data)

        logger.info("════════════════════════════════════════════════════════════")
        logger.info(f"🎯 VWAP SD + OPTIONS CONFLUENCE ANALYSIS [{symbol}]")
        logger.info("════════════════════════════════════════════════════════════")
        logger.info(f"   Prix actuel : {mid:.2f}")
        logger.info(f"   VWAP Zone   : {vwap_bands.current_zone.value}")
        logger.info(f"   Distance    : {vwap_bands.distance_to_mean:.1f} ticks ({vwap_bands.distance_to_mean_atr:.2f} ATR)")
        logger.info("────────────────────────────────────────────────────────────")
        logger.info(f"   VWAP        : {vwap_bands.vwap:.2f}")
        logger.info(f"   VWAP +1σ    : {vwap_bands.vwap_up1:.2f}")
        logger.info(f"   VWAP +2σ    : {vwap_bands.vwap_up2:.2f}")
        logger.info(f"   VWAP -1σ    : {vwap_bands.vwap_dn1:.2f}")
        logger.info(f"   VWAP -2σ    : {vwap_bands.vwap_dn2:.2f}")
        logger.info("────────────────────────────────────────────────────────────")
        logger.info(f"   HVL         : {options_levels.hvl:.2f}")
        logger.info(f"   Next Wall   : {options_levels.next_wall_price:.2f} ({options_levels.next_wall_side})")
        logger.info(f"   Call Resist : {options_levels.call_resistance:.2f}")
        logger.info(f"   Put Support : {options_levels.put_support:.2f}")
        logger.info("════════════════════════════════════════════════════════════")

        # ANALYSE DES 7 SCÉNARIOS (ajout du scénario 7: VWAP pur)
        scenarios = [
            self._scenario_1_vwap_mean_reversion(data, vwap_bands, options_levels, symbol, tick_size),
            self._scenario_2_vwap_hvl_sandwich(data, vwap_bands, options_levels, symbol, tick_size),
            self._scenario_3_vwap_next_wall_confluence(data, vwap_bands, options_levels, symbol, tick_size),
            self._scenario_4_vwap_gex_bounce(data, vwap_bands, options_levels, symbol, tick_size),
            self._scenario_5_triple_confluence(data, vwap_bands, options_levels, symbol, tick_size),
            self._scenario_6_vwap_band_breakout(data, vwap_bands, options_levels, symbol, tick_size),
            self._scenario_7_vwap_pure(data, vwap_bands, options_levels, symbol, tick_size),  # 🆕 NOUVEAU
        ]

        # Filtrer les signaux valides
        valid_signals = [s for s in scenarios if s is not None]

        if not valid_signals:
            logger.info("❌ Aucun scénario de confluence détecté")
            return None

        # Retourner le signal avec la meilleure confiance
        best_signal = max(valid_signals, key=lambda s: s.confidence)

        logger.info("═══════════════════════════════════════════════════════════")
        logger.info(f"✅ SIGNAL CONFLUENCE DÉTECTÉ : {best_signal.type.value}")
        logger.info("═══════════════════════════════════════════════════════════")
        logger.info(f"   Direction   : {best_signal.direction}")
        logger.info(f"   Confidence  : {best_signal.confidence:.2%}")
        logger.info(f"   Entry       : {best_signal.entry_price:.2f}")
        logger.info(f"   Stop Loss   : {best_signal.stop_loss:.2f}")
        logger.info(f"   Take Profit : {best_signal.take_profit:.2f}")
        logger.info(f"   R/R Ratio   : {best_signal.risk_reward_ratio:.2f}")
        logger.info(f"   VWAP Zone   : {best_signal.vwap_zone.value}")
        logger.info("───────────────────────────────────────────────────────────")
        logger.info(f"   📋 {best_signal.confluence_description}")
        logger.info("───────────────────────────────────────────────────────────")
        for trigger in best_signal.triggers:
            logger.info(f"   ✓ {trigger}")
        logger.info("═══════════════════════════════════════════════════════════")

        return best_signal

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 1 : VWAP MEAN REVERSION
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_1_vwap_mean_reversion(self, data: dict, vwap_bands: VWAPBands,
                                        options_levels: OptionsLevels,
                                        symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 1 : Mean Reversion sur bandes VWAP ±1σ ou ±2σ

        LOGIQUE :
        ─────────
        - Prix touche VWAP +1σ/+2σ → SHORT (retour vers moyenne)
        - Prix touche VWAP -1σ/-2σ → LONG (retour vers moyenne)

        CONFLUENCE RENFORCÉE SI :
        ──────────────────────────
        - HVL proche (< 50 ticks)
        - Next Wall dans la direction opposée
        - GEX Level proche

        ✨ OPTIMISATIONS 15/11/2025:
        ────────────────────────────
        - SL adaptatif selon ATR (évite stop hunts)
        - TP intelligent (distance dynamique 60-80% vers VWAP)
        - R:R minimum 2.0:1 (vs 1.5:1)
        """
        mid = data.get("mid", 0)
        bounce_zones = self.VWAP_BOUNCE_ZONES[symbol]

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: SL ADAPTATIF SELON ATR
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20  # Default 20t

        # ═══════════════════════════════════════════════════════════════
        # ✅ CONFIGURATION OPTIMALE 15/11/2025 - VALIDÉE PAR 485 COMBINAISONS
        # ES: TP 16t / SL 12t (R:R 1.33:1) → +0.397 t/trade
        # NQ: TP 23t / SL 12t (R:R 1.92:1) → +1.528 t/trade
        # ═══════════════════════════════════════════════════════════════
        # Base SL selon symbole (FIXE pour test 1 semaine)
        base_sl_ticks = {'ES': 12, 'NQ': 12, 'RTY': 20}.get(symbol, 15)

        # Ajustement selon volatilité
        if atr_ticks > 50:  # Haute volatilité
            sl_adjustment = 3  # +3 ticks
        elif atr_ticks < 20:  # Basse volatilité
            sl_adjustment = -2  # -2 ticks (plus serré)
        else:
            sl_adjustment = 0

        sl_ticks = base_sl_ticks + sl_adjustment

        # Vérifier si prix proche d'une bande
        d_to_up1 = abs(mid - vwap_bands.vwap_up1) / tick_size
        d_to_up2 = abs(mid - vwap_bands.vwap_up2) / tick_size
        d_to_dn1 = abs(mid - vwap_bands.vwap_dn1) / tick_size
        d_to_dn2 = abs(mid - vwap_bands.vwap_dn2) / tick_size

        direction = None
        entry = mid
        stop_loss = 0
        take_profit = 0
        triggers = []
        confidence = 0.0
        target_zone = ""

        # SCENARIO 1A : Bounce sur VWAP +1σ (SHORT)
        if d_to_up1 <= bounce_zones["sd1"]:
            direction = "SHORT"
            stop_loss = vwap_bands.vwap_up1 + (sl_ticks * tick_size)  # ✅ SL adaptatif
            confidence = 0.70
            target_zone = "VWAP +1σ"
            triggers.append("Prix proche VWAP +1σ → Mean Reversion SHORT")
            if sl_adjustment != 0:
                triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")

        # SCENARIO 1B : Bounce sur VWAP +2σ (SHORT fort)
        elif d_to_up2 <= bounce_zones["sd2"]:
            direction = "SHORT"
            stop_loss = vwap_bands.vwap_up2 + ((sl_ticks + 5) * tick_size)  # +5t car +2σ plus extrême
            confidence = 0.85
            target_zone = "VWAP +2σ"
            triggers.append("Prix proche VWAP +2σ → Mean Reversion SHORT FORT")
            if sl_adjustment != 0:
                triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")

        # SCENARIO 1C : Bounce sur VWAP -1σ (LONG)
        elif d_to_dn1 <= bounce_zones["sd1"]:
            direction = "LONG"
            stop_loss = vwap_bands.vwap_dn1 - (sl_ticks * tick_size)  # ✅ SL adaptatif
            confidence = 0.70
            target_zone = "VWAP -1σ"
            triggers.append("Prix proche VWAP -1σ → Mean Reversion LONG")
            if sl_adjustment != 0:
                triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")

        # SCENARIO 1D : Bounce sur VWAP -2σ (LONG fort)
        elif d_to_dn2 <= bounce_zones["sd2"]:
            direction = "LONG"
            stop_loss = vwap_bands.vwap_dn2 - ((sl_ticks + 5) * tick_size)  # +5t car -2σ plus extrême
            confidence = 0.85
            target_zone = "VWAP -2σ"
            triggers.append("Prix proche VWAP -2σ → Mean Reversion LONG FORT")
            if sl_adjustment != 0:
                triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")

        if direction is None:
            return None

        # ═══════════════════════════════════════════════════════════════
        # ✅ TP OPTIMAL 15/11/2025 - CONFIGURATION FIXE POUR TEST 1 SEMAINE
        # ES: 16 ticks | NQ: 23 ticks (Validé par optimisation exhaustive)
        # ═══════════════════════════════════════════════════════════════
        TP_OPTIMAL = {'ES': 16, 'NQ': 23, 'RTY': 25}
        tp_distance_ticks = TP_OPTIMAL.get(symbol, 20)

        # Note: TP dynamique désactivé temporairement pour test
        # Calculer distance théorique vers VWAP (pour référence)
        # distance_to_vwap_ticks = abs(mid - vwap_bands.vwap) / tick_size

        # TP selon confidence (setup fort = 80%, setup moyen = 60%)
        # if confidence >= 0.85:  # ±2σ = setup fort
        #     tp_factor = 0.80  # Viser 80% du chemin vers VWAP
        # else:  # ±1σ = setup moyen
        #     tp_factor = 0.60  # Viser 60% du chemin vers VWAP

        # tp_distance_ticks = distance_to_vwap_ticks * tp_factor

        # Limiter TP (éviter targets irréalistes)
        # MAX_TP_TICKS = {'ES': 25, 'NQ': 30, 'RTY': 35}.get(symbol, 25)
        # tp_distance_ticks = min(tp_distance_ticks, MAX_TP_TICKS)

        # TP final
        if direction == "SHORT":
            take_profit = mid - (tp_distance_ticks * tick_size)
        else:  # LONG
            take_profit = mid + (tp_distance_ticks * tick_size)

        triggers.append(f"TP optimal: {tp_distance_ticks:.0f}t (Config validée 15/11)")


        # Bonus de confiance si confluence avec niveaux options
        d_hvl = abs(mid - options_levels.hvl) / tick_size if options_levels.hvl else 999
        if d_hvl < 50:
            confidence += 0.10
            triggers.append(f"HVL proche ({d_hvl:.0f} ticks) → Confluence renforcée")

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: R:R MINIMUM 2.0:1 (vs 1.5:1)
        # ═══════════════════════════════════════════════════════════════
        min_rr = 2.0 if confidence < 0.80 else 1.8  # Setup fort: 1.8, moyen/faible: 2.0
        if rr_ratio < min_rr:
            return None

        return ConfluenceSignal(
            type=ConfluenceType.VWAP_BAND_BOUNCE,
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            vwap_zone=vwap_bands.current_zone,
            confluence_description=f"Mean Reversion depuis {target_zone} vers VWAP",
            triggers=triggers
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 2 : VWAP/HVL SANDWICH
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_2_vwap_hvl_sandwich(self, data: dict, vwap_bands: VWAPBands,
                                      options_levels: OptionsLevels,
                                      symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 2 : Prix entre VWAP et HVL (Sandwich)

        LOGIQUE :
        ─────────
        - Prix ENTRE VWAP et HVL
        - Double support/résistance
        - Entry anticipative du rebond

        EXEMPLE (Trade RTY @ 2462.25) :
        ────────────────────────────────
        VWAP : 2461.65
        Prix : 2462.25  ← ENTRY LONG
        HVL  : 2460.00  ← Support

        ✨ OPTIMISATIONS 15/11/2025:
        ────────────────────────────
        - SL adaptatif selon ATR
        - TP intelligent (50% distance VWAP, max 25t)
        - R:R minimum 2.0:1
        """
        mid = data.get("mid", 0)
        vwap = vwap_bands.vwap
        hvl = options_levels.hvl

        if not hvl or hvl == 0:
            return None

        thresholds = self.CONFLUENCE_THRESHOLDS[symbol]

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: SL ADAPTATIF SELON ATR
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 12, 'NQ': 12, 'RTY': 20}.get(symbol, 15)

        if atr_ticks > 50:
            sl_adjustment = 3
        elif atr_ticks < 20:
            sl_adjustment = -2
        else:
            sl_adjustment = 0

        sl_ticks = base_sl_ticks + sl_adjustment

        # Distances
        d_vwap = abs(mid - vwap) / tick_size
        d_hvl = abs(mid - hvl) / tick_size

        # 🔧 OPTIMISATION 17/11/2025: Assouplir condition géométrique
        # Prix doit être entre VWAP et HVL OU proche de l'un des deux
        between = (min(vwap, hvl) <= mid <= max(vwap, hvl))
        near_vwap = d_vwap <= thresholds["vwap_hvl"] * 1.5  # +50% tolérance
        near_hvl = d_hvl <= thresholds["vwap_hvl"] * 1.5  # +50% tolérance

        # Accepter si entre OU proche de l'un des deux
        if not (between or (near_vwap and near_hvl)):
            return None

        # Distance max : Augmenté de +50%
        max_distance = thresholds["vwap_hvl"] * 1.5
        if d_vwap > max_distance or d_hvl > max_distance:
            return None

        # Déterminer direction
        if hvl < vwap:
            # HVL en-dessous = Support → LONG
            direction = "LONG"
            entry = mid
            stop_loss = hvl - (sl_ticks * tick_size)  # ✅ SL adaptatif
        else:
            # HVL au-dessus = Résistance → SHORT
            direction = "SHORT"
            entry = mid
            stop_loss = hvl + (sl_ticks * tick_size)  # ✅ SL adaptatif

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: TP INTELLIGENT (50% distance VWAP)
        # ═══════════════════════════════════════════════════════════════
        # TP = 50% du chemin vers VWAP (plus réaliste que symétrique)
        tp_distance_ticks = d_vwap * 0.5

        # Limiter TP
        MAX_TP_TICKS = {'ES': 25, 'NQ': 30, 'RTY': 35}.get(symbol, 25)
        tp_distance_ticks = min(tp_distance_ticks, MAX_TP_TICKS)

        # TP final
        if direction == "LONG":
            take_profit = mid + (tp_distance_ticks * tick_size)
        else:  # SHORT
            take_profit = mid - (tp_distance_ticks * tick_size)

        # Confidence basée sur la proximité
        proximity_score = 1 - ((d_vwap + d_hvl) / (2 * thresholds["vwap_hvl"]))
        confidence = 0.75 + (proximity_score * 0.20)

        triggers = [
            f"Prix entre VWAP ({vwap:.2f}) et HVL ({hvl:.2f})",
            f"Distance VWAP: {d_vwap:.0f} ticks",
            f"Distance HVL: {d_hvl:.0f} ticks",
            f"Setup: VWAP/HVL Sandwich → {direction}"
        ]

        if sl_adjustment != 0:
            triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")
        triggers.append(f"TP: 50% vers VWAP ({tp_distance_ticks:.1f}t)")

        # Bonus si Next Wall dans la bonne direction
        if options_levels.next_wall_price:
            if direction == "LONG" and options_levels.next_wall_side == "call":
                confidence += 0.05
                triggers.append(f"Next Wall Call @ {options_levels.next_wall_price:.2f} → Confluence TP")
            elif direction == "SHORT" and options_levels.next_wall_side == "put":
                confidence += 0.05
                triggers.append(f"Next Wall Put @ {options_levels.next_wall_price:.2f} → Confluence TP")

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: R:R MINIMUM 2.0:1
        # ═══════════════════════════════════════════════════════════════
        min_rr = 2.0 if confidence < 0.85 else 1.8
        if rr_ratio < min_rr:
            return None

        return ConfluenceSignal(
            type=ConfluenceType.VWAP_HVL_SANDWICH,
            direction=direction,
            confidence=min(confidence, 0.95),
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            vwap_zone=vwap_bands.current_zone,
            confluence_description=f"Prix sandwich entre VWAP et HVL → Double support/résistance",
            triggers=triggers
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 3 : VWAP + NEXT WALL CONFLUENCE
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_3_vwap_next_wall_confluence(self, data: dict, vwap_bands: VWAPBands,
                                              options_levels: OptionsLevels,
                                              symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 3 : Confluence VWAP + Next Wall

        LOGIQUE Bible MenthorQ v2.0 :
        ──────────────────────────────
        - Put Wall = Support → LONG (rebond UP)
        - Call Wall = Resistance → SHORT (rebond DOWN)

        CONFLUENCE SI :
        ───────────────
        - Prix proche VWAP (±30 ticks)
        - Next Wall proche (< 80 ticks)
        - Wall Strength > 0.20

        ✨ OPTIMISATIONS 15/11/2025:
        ────────────────────────────
        - SL adaptatif selon ATR
        - TP intelligent (basé wall strength, max 25t)
        - R:R minimum 2.0:1
        """
        mid = data.get("mid", 0)
        vwap = vwap_bands.vwap
        wall_price = options_levels.next_wall_price
        wall_side = options_levels.next_wall_side
        wall_strength = options_levels.next_wall_strength

        if not wall_price or wall_price == 0:
            return None

        thresholds = self.CONFLUENCE_THRESHOLDS[symbol]

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: SL ADAPTATIF SELON ATR
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 12, 'NQ': 12, 'RTY': 20}.get(symbol, 15)

        if atr_ticks > 50:
            sl_adjustment = 3
        elif atr_ticks < 20:
            sl_adjustment = -2
        else:
            sl_adjustment = 0

        sl_ticks = base_sl_ticks + sl_adjustment

        d_vwap = abs(mid - vwap) / tick_size
        d_wall = abs(mid - wall_price) / tick_size

        # Vérifier confluence
        # 🔧 OPTIMISATION 17/11/2025: Assouplir condition VWAP (30 → 50 ticks)
        if d_vwap > 50 or d_wall > thresholds["vwap_wall"]:
            return None

        if wall_strength < 0.20:
            return None

        # Logique MenthorQ
        direction = None
        entry = mid

        if wall_side == "put":
            # Put Wall = Support → LONG
            direction = "LONG"
            stop_loss = min(vwap, wall_price) - (sl_ticks * tick_size)  # ✅ SL adaptatif
        else:
            # Call Wall = Resistance → SHORT
            direction = "SHORT"
            stop_loss = max(vwap, wall_price) + (sl_ticks * tick_size)  # ✅ SL adaptatif

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: TP INTELLIGENT (selon wall strength)
        # ═══════════════════════════════════════════════════════════════
        # Base TP: 20 ticks (réduit de 30t)
        base_tp_ticks = 20

        # Ajustement selon wall strength
        if wall_strength > 0.50:
            tp_factor = 1.2  # +20% si wall fort
        else:
            tp_factor = 0.8  # -20% si wall faible

        tp_distance_ticks = base_tp_ticks * tp_factor

        # Limiter TP
        MAX_TP_TICKS = {'ES': 25, 'NQ': 30, 'RTY': 35}.get(symbol, 25)
        tp_distance_ticks = min(tp_distance_ticks, MAX_TP_TICKS)

        # TP final
        if direction == "LONG":
            take_profit = mid + (tp_distance_ticks * tick_size)
        else:  # SHORT
            take_profit = mid - (tp_distance_ticks * tick_size)

        # Confidence basée sur wall strength et proximité
        proximity_score = 1 - (d_wall / thresholds["vwap_wall"])
        confidence = 0.70 + (wall_strength * 0.15) + (proximity_score * 0.10)

        triggers = [
            f"Confluence VWAP ({vwap:.2f}) + Next Wall {wall_side.upper()} ({wall_price:.2f})",
            f"Wall Strength: {wall_strength:.2f}",
            f"Distance Wall: {d_wall:.0f} ticks",
            f"Logique MenthorQ: {wall_side.title()} Wall → {direction}"
        ]

        if sl_adjustment != 0:
            triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")
        triggers.append(f"TP: {tp_distance_ticks:.1f}t (wall strength {wall_strength:.2f})")

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: R:R MINIMUM 2.0:1
        # ═══════════════════════════════════════════════════════════════
        min_rr = 2.0 if confidence < 0.80 else 1.8
        if rr_ratio < min_rr:
            return None

        return ConfluenceSignal(
            type=ConfluenceType.VWAP_NEXTWALL,
            direction=direction,
            confidence=min(confidence, 0.92),
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            vwap_zone=vwap_bands.current_zone,
            confluence_description=f"VWAP + Next Wall {wall_side.upper()} → Support/Résistance renforcé",
            triggers=triggers
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 4 : VWAP + GEX BOUNCE
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_4_vwap_gex_bounce(self, data: dict, vwap_bands: VWAPBands,
                                    options_levels: OptionsLevels,
                                    symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 4 : Bounce sur VWAP Band + GEX Level proche

        LOGIQUE :
        ─────────
        - Prix près VWAP ±1σ
        - GEX Level proche (< 100 ticks)
        - Confluence = Double support/résistance

        ✨ OPTIMISATIONS 15/11/2025:
        ────────────────────────────
        - SL adaptatif selon ATR
        - TP intelligent 70% vers VWAP (vs VWAP fixe)
        - R:R minimum 2.0:1
        """
        mid = data.get("mid", 0)
        gex_levels = options_levels.gex_levels

        if not gex_levels:
            return None

        thresholds = self.CONFLUENCE_THRESHOLDS[symbol]

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: SL ADAPTATIF SELON ATR
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 12, 'NQ': 12, 'RTY': 20}.get(symbol, 15)

        if atr_ticks > 50:
            sl_adjustment = 3
        elif atr_ticks < 20:
            sl_adjustment = -2
        else:
            sl_adjustment = 0

        sl_ticks = base_sl_ticks + sl_adjustment

        # Trouver GEX le plus proche
        closest_gex = min(gex_levels, key=lambda g: abs(g - mid))
        d_gex = abs(mid - closest_gex) / tick_size

        if d_gex > thresholds["vwap_gex"]:
            return None

        # Vérifier si près d'une bande VWAP
        d_up1 = abs(mid - vwap_bands.vwap_up1) / tick_size
        d_dn1 = abs(mid - vwap_bands.vwap_dn1) / tick_size

        direction = None
        entry = mid
        vwap_band = ""

        if d_up1 < 15:
            # Près VWAP +1σ + GEX → SHORT
            direction = "SHORT"
            stop_loss = max(vwap_bands.vwap_up1, closest_gex) + (sl_ticks * tick_size)  # ✅ SL adaptatif
            vwap_band = "VWAP +1σ"
        elif d_dn1 < 15:
            # Près VWAP -1σ + GEX → LONG
            direction = "LONG"
            stop_loss = min(vwap_bands.vwap_dn1, closest_gex) - (sl_ticks * tick_size)  # ✅ SL adaptatif
            vwap_band = "VWAP -1σ"
        else:
            return None

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: TP INTELLIGENT (70% vers VWAP)
        # ═══════════════════════════════════════════════════════════════
        # Distance vers VWAP
        distance_to_vwap_ticks = abs(mid - vwap_bands.vwap) / tick_size

        # TP = 70% du chemin vers VWAP (plus réaliste que 100%)
        tp_distance_ticks = distance_to_vwap_ticks * 0.7

        # Limiter TP
        MAX_TP_TICKS = {'ES': 25, 'NQ': 30, 'RTY': 35}.get(symbol, 25)
        tp_distance_ticks = min(tp_distance_ticks, MAX_TP_TICKS)

        # TP final
        if direction == "SHORT":
            take_profit = mid - (tp_distance_ticks * tick_size)
        else:  # LONG
            take_profit = mid + (tp_distance_ticks * tick_size)

        confidence = 0.72 + (1 - d_gex / thresholds["vwap_gex"]) * 0.15

        triggers = [
            f"Prix près {vwap_band} + GEX Level ({closest_gex:.2f})",
            f"Distance GEX: {d_gex:.0f} ticks",
            f"Setup: VWAP Band + GEX Confluence → {direction}"
        ]

        if sl_adjustment != 0:
            triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")
        triggers.append(f"TP: 70% vers VWAP ({tp_distance_ticks:.1f}t)")

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: R:R MINIMUM 2.0:1
        # ═══════════════════════════════════════════════════════════════
        min_rr = 2.0 if confidence < 0.85 else 1.8
        if rr_ratio < min_rr:
            return None

        return ConfluenceSignal(
            type=ConfluenceType.VWAP_GEX,
            direction=direction,
            confidence=min(confidence, 0.88),
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            vwap_zone=vwap_bands.current_zone,
            confluence_description=f"{vwap_band} + GEX Level → Double barrière",
            triggers=triggers
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 5 : TRIPLE CONFLUENCE (HOLY GRAIL)
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_5_triple_confluence(self, data: dict, vwap_bands: VWAPBands,
                                      options_levels: OptionsLevels,
                                      symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 5 : Triple Confluence (VWAP + HVL + Next Wall)

        C'EST LE SETUP PARFAIT !

        LOGIQUE :
        ─────────
        - VWAP proche (< 30 ticks)
        - HVL proche (< 30 ticks)
        - Next Wall proche (< 100 ticks)
        - Tous alignés dans la même zone

        ✨ OPTIMISATIONS 15/11/2025:
        ────────────────────────────
        - SL adaptatif selon ATR
        - TP intelligent 30t (vs 50t fixe)
        - R:R minimum 1.8:1 (setup très fort)
        """
        mid = data.get("mid", 0)
        vwap = vwap_bands.vwap
        hvl = options_levels.hvl
        wall_price = options_levels.next_wall_price
        wall_side = options_levels.next_wall_side

        if not hvl or not wall_price:
            return None

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: SL ADAPTATIF SELON ATR
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 10, 'NQ': 12, 'RTY': 15}.get(symbol, 10)  # Plus serré (triple confluence)

        if atr_ticks > 50:
            sl_adjustment = 2  # +2t (moins que normal, setup fort)
        elif atr_ticks < 20:
            sl_adjustment = -2
        else:
            sl_adjustment = 0

        sl_ticks = base_sl_ticks + sl_adjustment

        # Distances
        d_vwap = abs(mid - vwap) / tick_size
        d_hvl = abs(mid - hvl) / tick_size
        d_wall = abs(mid - wall_price) / tick_size

        # Seuils stricts pour triple confluence
        if d_vwap > 30 or d_hvl > 30 or d_wall > 100:
            return None

        # Vérifier alignement (tous du même côté)
        all_above = all(x > mid for x in [vwap, hvl, wall_price])
        all_below = all(x < mid for x in [vwap, hvl, wall_price])

        if not (all_above or all_below):
            # Pas parfaitement alignés, mais vérifier si 2/3 sont du même côté
            above_count = sum(1 for x in [vwap, hvl, wall_price] if x > mid)
            if above_count not in [0, 3]:
                return None

        # Déterminer direction
        if all_below or sum(1 for x in [vwap, hvl, wall_price] if x < mid) >= 2:
            direction = "LONG"
            entry = mid
            support_level = min(vwap, hvl, wall_price)
            stop_loss = support_level - (sl_ticks * tick_size)  # ✅ SL adaptatif
        else:
            direction = "SHORT"
            entry = mid
            resistance_level = max(vwap, hvl, wall_price)
            stop_loss = resistance_level + (sl_ticks * tick_size)  # ✅ SL adaptatif

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: TP INTELLIGENT (30t vs 50t fixe)
        # ═══════════════════════════════════════════════════════════════
        # TP = 30 ticks (réduit de 50t, plus réaliste)
        tp_distance_ticks = 30

        # Ajuster selon symbole
        tp_distance_ticks = {'ES': 25, 'NQ': 30, 'RTY': 35}.get(symbol, 30)

        # TP final
        if direction == "LONG":
            take_profit = entry + (tp_distance_ticks * tick_size)
        else:  # SHORT
            take_profit = entry - (tp_distance_ticks * tick_size)

        # Confidence élevée pour triple confluence
        proximity_avg = (d_vwap + d_hvl + d_wall) / 3
        confidence = 0.90 + (1 - proximity_avg / 50) * 0.08

        triggers = [
            "🏆 TRIPLE CONFLUENCE DÉTECTÉE !",
            f"VWAP: {vwap:.2f} (distance: {d_vwap:.0f}t)",
            f"HVL: {hvl:.2f} (distance: {d_hvl:.0f}t)",
            f"Next Wall {wall_side.upper()}: {wall_price:.2f} (distance: {d_wall:.0f}t)",
            f"Setup: Triple support/résistance → {direction}"
        ]

        if sl_adjustment != 0:
            triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")
        triggers.append(f"TP: {tp_distance_ticks}t (setup très fort)")

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: R:R MINIMUM 1.8:1 (setup très fort)
        # ═══════════════════════════════════════════════════════════════
        min_rr = 1.8  # Plus bas car confidence très élevée (triple confluence)
        if rr_ratio < min_rr:
            return None

        return ConfluenceSignal(
            type=ConfluenceType.TRIPLE_CONFLUENCE,
            direction=direction,
            confidence=min(confidence, 0.98),
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            vwap_zone=vwap_bands.current_zone,
            confluence_description="🏆 TRIPLE CONFLUENCE : VWAP + HVL + Next Wall alignés → Setup parfait",
            triggers=triggers
        )

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 6 : VWAP BAND BREAKOUT + GAMMA FLIP
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_6_vwap_band_breakout(self, data: dict, vwap_bands: VWAPBands,
                                       options_levels: OptionsLevels,
                                       symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 6 : Breakout VWAP Band + Gamma Flip

        LOGIQUE :
        ─────────
        - Prix casse VWAP ±1σ avec momentum
        - Gamma Wall dans la direction du breakout
        - Continuation attendue

        ✨ OPTIMISATIONS 15/11/2025:
        ────────────────────────────
        - SL adaptatif selon ATR
        - TP basé sur ATR (vs fixe)
        - R:R minimum 2.0:1 maintenu
        """
        mid = data.get("mid", 0)
        gamma_side = data.get("gamma_side", "")

        # ═══════════════════════════════════════════════════════════════
        # ✨ NOUVEAU 15/11/2025: SL ADAPTATIF SELON ATR
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 15, 'NQ': 18, 'RTY': 25}.get(symbol, 18)  # Plus large (breakout)

        if atr_ticks > 50:
            sl_adjustment = 5  # +5t (breakout haute volatilité)
        elif atr_ticks < 20:
            sl_adjustment = 0  # Pas de réduction (breakout nécessite SL large)
        else:
            sl_adjustment = 2

        sl_ticks = base_sl_ticks + sl_adjustment

        # Détecter breakout
        if vwap_bands.current_zone in [VWAPZone.EXTREME_OVERBOUGHT, VWAPZone.EXTREME_OVERSOLD]:
            # Prix au-delà de ±2σ = breakout confirmé

            if vwap_bands.current_zone == VWAPZone.EXTREME_OVERBOUGHT:
                # Breakout haussier
                direction = "LONG"
                entry = mid
                stop_loss = vwap_bands.vwap_up1 - (sl_ticks * tick_size)  # ✅ SL adaptatif

                if gamma_side != "above":
                    return None  # Gamma doit être favorable

            else:
                # Breakout baissier
                direction = "SHORT"
                entry = mid
                stop_loss = vwap_bands.vwap_dn1 + (sl_ticks * tick_size)  # ✅ SL adaptatif

                if gamma_side != "below":
                    return None

            # ═══════════════════════════════════════════════════════════════
            # ✨ NOUVEAU 15/11/2025: TP BASÉ SUR ATR (vs fixe)
            # ═══════════════════════════════════════════════════════════════
            # TP = 1.5x ATR (momentum breakout)
            tp_distance_ticks = atr_ticks * 1.5

            # Limiter TP
            MAX_TP_TICKS = {'ES': 30, 'NQ': 35, 'RTY': 40}.get(symbol, 35)
            MIN_TP_TICKS = {'ES': 20, 'NQ': 25, 'RTY': 30}.get(symbol, 25)
            tp_distance_ticks = max(MIN_TP_TICKS, min(tp_distance_ticks, MAX_TP_TICKS))

            # TP final
            if direction == "LONG":
                take_profit = entry + (tp_distance_ticks * tick_size)
            else:  # SHORT
                take_profit = entry - (tp_distance_ticks * tick_size)

            confidence = 0.75

            triggers = [
                f"Breakout VWAP {vwap_bands.current_zone.value}",
                f"Gamma Side: {gamma_side} → Favorable au {direction}",
                "Setup: Continuation post-breakout"
            ]

            if sl_adjustment != 0:
                triggers.append(f"SL ajusté: {sl_adjustment:+.0f}t (ATR: {atr_ticks:.1f}t)")
            triggers.append(f"TP: 1.5x ATR ({tp_distance_ticks:.1f}t)")

            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
            rr_ratio = reward / risk if risk > 0 else 0

            # ═══════════════════════════════════════════════════════════════
            # ✨ MAINTENU: R:R MINIMUM 2.0:1 (déjà optimal)
            # ═══════════════════════════════════════════════════════════════
            if rr_ratio < 2.0:  # R/R strict pour breakout
                return None

            return ConfluenceSignal(
                type=ConfluenceType.VWAP_BAND_BOUNCE,
                direction=direction,
                confidence=confidence,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=rr_ratio,
                vwap_zone=vwap_bands.current_zone,
                confluence_description=f"Breakout VWAP Band + Gamma Flip → Continuation {direction}",
                triggers=triggers
            )

        return None

    # ═══════════════════════════════════════════════════════════════════════
    # SCENARIO 7 : VWAP PUR (Sans confluence options requise)
    # ═══════════════════════════════════════════════════════════════════════

    def _scenario_7_vwap_pure(self, data: dict, vwap_bands: VWAPBands,
                              options_levels: OptionsLevels,
                              symbol: str, tick_size: float) -> Optional[ConfluenceSignal]:
        """
        SCENARIO 7 : VWAP Pur - Mean Reversion sans confluence options requise

        🆕 NOUVEAU 17/11/2025: Accepter signaux avec distance VWAP > 2.0 ATR
        même sans confluence parfaite avec niveaux options.

        LOGIQUE :
        ─────────
        - Prix éloigné de VWAP (> 2.0 ATR) → Mean Reversion probable
        - Confluence options = BONUS (pas requis)
        - Utilise seulement la distance VWAP comme critère principal

        ✨ OBJECTIF :
        ─────────────
        - Récupérer les signaux valides rejetés par les autres scénarios
        - Accepter setups avec bonne distance VWAP même si options éloignées
        """
        mid = data.get("mid", 0)
        vwap = vwap_bands.vwap
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        # ═══════════════════════════════════════════════════════════════
        # CRITÈRE PRINCIPAL: Distance VWAP > 2.0 ATR
        # ═══════════════════════════════════════════════════════════════
        distance_vwap_ticks = abs(mid - vwap) / tick_size
        distance_vwap_atr = vwap_bands.distance_to_mean_atr

        # Seuil minimum: 2.0 ATR
        if distance_vwap_atr < 2.0:
            return None

        # ═══════════════════════════════════════════════════════════════
        # DÉTERMINER DIRECTION (Mean Reversion vers VWAP)
        # ═══════════════════════════════════════════════════════════════
        if mid > vwap:
            # Prix au-dessus VWAP → SHORT (retour vers moyenne)
            direction = "SHORT"
            entry = mid
            stop_loss = mid + (12 * tick_size)  # SL 12 ticks au-dessus
        else:
            # Prix en-dessous VWAP → LONG (retour vers moyenne)
            direction = "LONG"
            entry = mid
            stop_loss = mid - (12 * tick_size)  # SL 12 ticks en-dessous

        # ═══════════════════════════════════════════════════════════════
        # TP OPTIMAL (même config que Scenario 1)
        # ═══════════════════════════════════════════════════════════════
        TP_OPTIMAL = {'ES': 16, 'NQ': 23, 'RTY': 25}
        tp_distance_ticks = TP_OPTIMAL.get(symbol, 20)

        if direction == "SHORT":
            take_profit = mid - (tp_distance_ticks * tick_size)
        else:  # LONG
            take_profit = mid + (tp_distance_ticks * tick_size)

        # ═══════════════════════════════════════════════════════════════
        # CONFIDENCE: Base + Bonus si confluence options
        # ═══════════════════════════════════════════════════════════════
        # Base confidence selon distance (plus loin = plus fort)
        if distance_vwap_atr >= 3.0:
            base_confidence = 0.75  # Très éloigné = setup fort
        elif distance_vwap_atr >= 2.5:
            base_confidence = 0.70  # Éloigné = setup moyen-fort
        else:
            base_confidence = 0.65  # Minimum (2.0 ATR)

        confidence = base_confidence

        triggers = [
            f"VWAP Pure: Distance {distance_vwap_atr:.2f} ATR ({distance_vwap_ticks:.0f} ticks)",
            f"Mean Reversion {direction} vers VWAP ({vwap:.2f})",
            f"TP optimal: {tp_distance_ticks:.0f}t"
        ]

        # ═══════════════════════════════════════════════════════════════
        # BONUS: Confluence options (si disponible)
        # ═══════════════════════════════════════════════════════════════
        thresholds = self.CONFLUENCE_THRESHOLDS[symbol]
        bonus_applied = False

        # Bonus HVL
        if options_levels.hvl:
            d_hvl = abs(mid - options_levels.hvl) / tick_size
            if d_hvl < thresholds["vwap_hvl"]:
                confidence += 0.05
                triggers.append(f"Bonus: HVL proche ({d_hvl:.0f} ticks)")
                bonus_applied = True

        # Bonus Next Wall
        if options_levels.next_wall_price:
            d_wall = abs(mid - options_levels.next_wall_price) / tick_size
            if d_wall < thresholds["vwap_wall"]:
                confidence += 0.05
                triggers.append(f"Bonus: Next Wall proche ({d_wall:.0f} ticks)")
                bonus_applied = True

        if not bonus_applied:
            triggers.append("Confluence options: Aucune (VWAP pur)")

        # Limiter confidence max
        confidence = min(confidence, 0.85)

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION R:R
        # ═══════════════════════════════════════════════════════════════
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        # R:R minimum: 1.8 (plus permissif que les autres scénarios)
        min_rr = 1.8
        if rr_ratio < min_rr:
            return None

        return ConfluenceSignal(
            type=ConfluenceType.VWAP_BAND_BOUNCE,
            direction=direction,
            confidence=confidence,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            vwap_zone=vwap_bands.current_zone,
            confluence_description=f"VWAP Pure: Mean Reversion {direction} (distance {distance_vwap_atr:.2f} ATR)",
            triggers=triggers
        )


# ═══════════════════════════════════════════════════════════════════════════
# FONCTION D'INTÉGRATION DANS LE BOT
# ═══════════════════════════════════════════════════════════════════════════

def create_strategy(config: dict):
    """Factory function pour créer la stratégie"""
    return VWAPSDOptionsConfluenceStrategy(config)
