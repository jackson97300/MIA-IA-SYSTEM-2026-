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
    strategy: str = "vwap_sd_options_confluence_strategy"  # ✅ CORRIGÉ: Ajout attribut strategy


class VWAPSDOptionsConfluenceStrategy:
    """
    Stratégie de confluence VWAP Standard Deviation + Options
    """

    def __init__(self, config: dict):
        self.config = config
        self.name = "vwap_sd_options_confluence"

        # Seuils de distance pour confluence (en ticks)
        # 📊 OPTIMISÉ 19/11/2025: Seuils assouplis basés sur analyse trades gagnants
        #    ATR moyen gagnants: 79.6 ticks → seuils assouplis de ~25% pour plus de flexibilité
        self.CONFLUENCE_THRESHOLDS = {
            "ES": {"vwap_hvl": 40, "vwap_wall": 79, "vwap_gex": 93},     # 📊 OPTIMISÉ: +25% (32→40, 63→79, 74→93)
            "NQ": {"vwap_hvl": 93, "vwap_wall": 145, "vwap_gex": 175},   # 📊 OPTIMISÉ: +25% (74→93, 116→145, 140→175)
            "RTY": {"vwap_hvl": 26, "vwap_wall": 61, "vwap_gex": 79}     # 📊 OPTIMISÉ: +25% (21→26, 49→61, 63→79)
        }

        # Zones de bounce VWAP (distance max pour considérer un bounce)
        # 📊 OPTIMISÉ 21/11/2025 14:00: Zones assouplies +30% pour augmenter volume signaux
        #    Objectif: Passer de 2-3 signaux/jour à 8-15 signaux/jour
        self.VWAP_BOUNCE_ZONES = {
            "ES": {"sd1": 56, "sd2": 91},    # 🔥 FIX 21/11: +30% (43→56, 70→91)
            "NQ": {"sd1": 109, "sd2": 164},  # 🔥 FIX 21/11: +30% (84→109, 126→164)
            "RTY": {"sd1": 46, "sd2": 79}    # 🔥 FIX 21/11: +30% (35→46, 61→79)
        }

        logger.info(f"✅ Stratégie {self.name} initialisée avec Bible MenthorQ v2.0")

    def _validate_signal_quality(self, signal: ConfluenceSignal, symbol: str,
                                 confidence: float, rr_ratio: float,
                                 context: Dict = None) -> Optional[ConfluenceSignal]:
        """
        Valide qualité signal AVANT retour.

        Rejette si:
        - WIN probability < 15%
        - Expectancy < $10
        - Trop loin d'un niveau important

        Args:
            signal: Signal à valider
            symbol: Symbole
            confidence: Confidence totale
            rr_ratio: Risk/Reward ratio
            context: Contexte marché (optionnel)

        Returns:
            Signal validé ou None si rejeté
        """
        from core.signal_quality_validator import signal_quality_validator
        from core.level_proximity_validator import level_proximity_validator

        if context is None:
            context = {}

        # ═══════════════════════════════════════════════════════════
        # VALIDATION PROXIMITÉ NIVEAU (CORRIGÉE)
        # ═══════════════════════════════════════════════════════════
        if 'snapshot' in context:
            snapshot = context['snapshot']
            entry_price = signal.entry_price

            is_valid, reject_reason, nearest_level = level_proximity_validator.validate_proximity(
                snapshot=snapshot,
                price=entry_price,
                symbol=symbol,
                direction=signal.direction
            )

            if not is_valid:
                logger.warning(f"[{symbol}] ❌ Signal rejeté: {reject_reason}")
                return None

            # Trade justifié par ce niveau
            logger.info(
                f"[{symbol}] ✅ Trade justifié par: {nearest_level.description} "
                f"({nearest_level.distance_ticks:.0f}t)"
            )

        # Valider qualité
        quality_result = signal_quality_validator.validate_signal_quality(
            confidence=confidence,
            rr_ratio=rr_ratio,
            context=context,
            symbol=symbol
        )

        if quality_result is None:
            logger.warning(f"[{symbol}] Signal rejeté par quality validator")
            return None

        logger.info(
            f"[{symbol}] ✅ Quality validation passed: "
            f"WIN={quality_result['win_probability']:.1%}, "
            f"EXP=${quality_result['expectancy']:.2f}"
        )

        return signal

    def _validate_catastrophic_trade_filters(self, signal: ConfluenceSignal,
                                             snapshot: dict, symbol: str) -> Optional[ConfluenceSignal]:
        """
        Valide les filtres critiques pour empêcher trades catastrophiques.

        Ajouté 20/11/2025 pour bloquer trades comme NQ_20251120_002007:
        - MenthorQ UNKNOWN
        - 1D Proximity excessive
        - Scores insuffisants
        - Session ASIA filtres stricts
        """
        # ═══════════════════════════════════════════════════════════
        # VALIDATION MENTHORQ (ajouté 20/11/2025)
        # ✅ CORRIGÉ 20/11: Calculer depuis niveaux disponibles
        # ═══════════════════════════════════════════════════════════

        # ✅ CORRECTION: Calculer le niveau le plus proche au lieu de chercher un champ inexistant
        price = signal.entry_price
        tick_size = 0.25  # ES et NQ

        # Trouver le niveau MenthorQ le plus proche
        menthorq_level = None
        menthorq_distance = 9999

        # Priorité 1: HVL
        hvl = snapshot.get('hvl')
        if hvl:
            dist = abs(price - hvl) / tick_size
            if dist < menthorq_distance:
                menthorq_distance = dist
                menthorq_level = 'HVL'

        # Priorité 2: Blind Spots (souvent les plus proches)
        for i in range(9):
            blind = snapshot.get(f'blind_spot_{i}')
            if blind:
                dist = abs(price - blind) / tick_size
                if dist < menthorq_distance:
                    menthorq_distance = dist
                    menthorq_level = f'BLIND_SPOT_{i}'

        # Priorité 3: 1D MAX/MIN
        day_max = snapshot.get('1d_max')
        if day_max:
            dist = abs(price - day_max) / tick_size
            if dist < menthorq_distance:
                menthorq_distance = dist
                menthorq_level = '1D_MAX'

        day_min = snapshot.get('1d_min')
        if day_min:
            dist = abs(price - day_min) / tick_size
            if dist < menthorq_distance:
                menthorq_distance = dist
                menthorq_level = '1D_MIN'

        # Priorité 4: GEX levels
        for i in range(1, 11):
            gex = snapshot.get(f'gex_{i}')
            if gex:
                dist = abs(price - gex) / tick_size
                if dist < menthorq_distance:
                    menthorq_distance = dist
                    menthorq_level = f'GEX_{i}'

        # Priorité 5: Call Resistance / Put Support
        call_res = snapshot.get('call_resistance')
        if call_res:
            dist = abs(price - call_res) / tick_size
            if dist < menthorq_distance:
                menthorq_distance = dist
                menthorq_level = 'CALL_RESISTANCE'

        put_sup = snapshot.get('put_support')
        if put_sup:
            dist = abs(price - put_sup) / tick_size
            if dist < menthorq_distance:
                menthorq_distance = dist
                menthorq_level = 'PUT_SUPPORT'

        # Bloquer si aucun niveau trouvé
        if menthorq_level is None:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: Aucun niveau MenthorQ trouvé dans le snapshot"
            )
            return None

        # Bloquer si trop loin de MenthorQ (> 100t pour NQ, 50t pour ES)
        max_distance_menthorq = 100 if symbol == 'NQ' else 50
        if menthorq_distance > max_distance_menthorq:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: MenthorQ trop loin - "
                f"Distance: {menthorq_distance:.0f}t > {max_distance_menthorq}t max "
                f"(Niveau: {menthorq_level})"
            )
            return None

        logger.info(
            f"[{symbol}] ✅ MenthorQ OK: {menthorq_level} @ "
            f"{menthorq_distance:.0f}t"
        )

        # ═══════════════════════════════════════════════════════════
        # VALIDATION PRIX AU-DESSUS DU 1D MAX (ajouté 20/11/2025)
        # Rejeter si prix trop au-dessus du max (faux breakout)
        # ═══════════════════════════════════════════════════════════

        day_max = snapshot.get('1d_max')
        if day_max and price > day_max:
            distance_above_max = (price - day_max) / tick_size

            max_above_max = {
                'ES': 20,   # 5 points
                'NQ': 20,   # 5 points
                'RTY': 15   # 1.5 points
            }

            max_dist = max_above_max.get(symbol, 20)

            if distance_above_max > max_dist:
                logger.warning(
                    f"[{symbol}] ❌ Signal REJETÉ: Prix trop au-dessus du 1D MAX - "
                    f"Distance: {distance_above_max:.0f}t > {max_dist}t max "
                    f"(Prix: {price:.2f} > Max: {day_max:.2f})"
                )
                return None

            logger.info(
                f"[{symbol}] ✅ Prix au-dessus du 1D MAX mais acceptable: "
                f"{distance_above_max:.0f}t < {max_dist}t"
            )

        # ═══════════════════════════════════════════════════════════
        # VALIDATION 1D PROXIMITY (ajouté 20/11/2025)
        # ✅ CORRIGÉ 20/11: Calculer depuis 1d_max et 1d_min
        # ═══════════════════════════════════════════════════════════

        # ✅ CORRECTION: Calculer la distance au 1D high/low au lieu de chercher un champ inexistant
        day_min = snapshot.get('1d_min')

        proximity_1d = 9999

        if day_max:
            dist_max = abs(price - day_max) / tick_size
            if dist_max < proximity_1d:
                proximity_1d = dist_max

        if day_min:
            dist_min = abs(price - day_min) / tick_size
            if dist_min < proximity_1d:
                proximity_1d = dist_min

        # 🔧 DÉSACTIVÉ: Permettre trades même si 1D MIN/MAX cassé (breakouts)
        # max_proximity_1d = {
        #     'ES': 50,    # ticks
        #     'NQ': 1500,  # ticks
        #     'RTY': 40    # ticks
        # }
        # max_prox = max_proximity_1d.get(symbol, 50)
        # if proximity_1d > max_prox:
        #     logger.warning(
        #         f"[{symbol}] ❌ Signal REJETÉ: Trop loin du 1D high/low - "
        #         f"Distance: {proximity_1d:.0f}t > {max_prox}t max"
        #     )
        #     return None
        # logger.info(
        #     f"[{symbol}] ✅ 1D Proximity OK: {proximity_1d:.0f}t < {max_prox}t"
        # )

        # ✅ PERMIS: Breakouts autorisés (1D MIN/MAX peut être cassé)
        logger.info(
            f"[{symbol}] ✅ 1D Proximity: {proximity_1d:.0f}t (breakouts autorisés)"
        )

        # ═══════════════════════════════════════════════════════════
        # VALIDATION SCORES MINIMUM (ajouté 20/11/2025)
        # Corrige: OrderFlow=0.13, Context=0.06 qui ont passé!
        # ═══════════════════════════════════════════════════════════

        # Seuils stricts
        min_scores = {
            'confluence': 0.75,  # ⚠️ Augmenté de 0.60 → 0.75
            'menthorq': 0.50,
            'orderflow': 0.20,
            'context': 0.15
        }

        # Vérifier confluence
        if signal.confidence < min_scores['confluence']:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: Confluence insuffisante - "
                f"{signal.confidence:.2f} < {min_scores['confluence']:.2f}"
            )
            return None

        # Vérifier MenthorQ score
        menthorq_score = snapshot.get('menthorq_score', 0.0)
        if menthorq_score < min_scores['menthorq']:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: MenthorQ score insuffisant - "
                f"{menthorq_score:.2f} < {min_scores['menthorq']:.2f}"
            )
            return None

        # Vérifier OrderFlow
        orderflow = snapshot.get('orderflow_score', 0.0)
        if orderflow < min_scores['orderflow']:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: OrderFlow insuffisant - "
                f"{orderflow:.2f} < {min_scores['orderflow']:.2f}"
            )
            return None

        # Vérifier Context
        context = snapshot.get('context_score', 0.0)
        if context < min_scores['context']:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: Context insuffisant - "
                f"{context:.2f} < {min_scores['context']:.2f}"
            )
            return None

        logger.info(
            f"[{symbol}] ✅ Scores OK: "
            f"C={signal.confidence:.2f}, M={menthorq_score:.2f}, "
            f"O={orderflow:.2f}, Ctx={context:.2f}"
        )

        # ═══════════════════════════════════════════════════════════
        # PROTECTION SESSION ASIA (ajouté 20/11/2025)
        # Filtres 2× plus stricts en ASIA
        # ═══════════════════════════════════════════════════════════

        session = snapshot.get('session', 'UNKNOWN')

        if session == 'ASIA':
            # Filtres plus stricts pour ASIA
            if signal.confidence < 0.80:  # vs 0.75 normal
                logger.warning(
                    f"[{symbol}] ❌ Signal REJETÉ: ASIA - Confluence insuffisante - "
                    f"{signal.confidence:.2f} < 0.80"
                )
                return None

            if orderflow < 0.30:  # vs 0.20 normal
                logger.warning(
                    f"[{symbol}] ❌ Signal REJETÉ: ASIA - OrderFlow insuffisant - "
                    f"{orderflow:.2f} < 0.30"
                )
                return None

            if context < 0.20:  # vs 0.15 normal
                logger.warning(
                    f"[{symbol}] ❌ Signal REJETÉ: ASIA - Context insuffisant - "
                    f"{context:.2f} < 0.20"
                )
                return None

            logger.info(
                f"[{symbol}] ✅ Session ASIA: Filtres stricts passés"
            )

        return signal

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

        # ═══════════════════════════════════════════════════════════
        # VALIDATIONS CRITIQUES DÉSACTIVÉES (20/11/2025 23:45)
        # Ajoutées après backup fonctionnel, trop strictes, bloquent 100% des signaux
        # ═══════════════════════════════════════════════════════════
        # validation_result = self._validate_catastrophic_trade_filters(
        #     best_signal, data, symbol
        # )
        # if validation_result is None:
        #     logger.warning(f"[{symbol}] ❌ Signal rejeté par validations critiques")
        #     return None

        logger.info(f"✅ [{symbol}] Validations catastrophiques DÉSACTIVÉES (mode recovery)")

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
        # 🔥 CORRIGÉ 21/11 05:55: SL augmenté pour réduire stop hunts
        # ES: SL 20t → 30t (+50%) pour aligner avec MenthorQ strategy
        # NQ: SL 22t → 35t (+59%) pour aligner avec MenthorQ strategy
        # ═══════════════════════════════════════════════════════════════
        # Base SL selon symbole (AUGMENTÉ pour réduire stop hunts)
        base_sl_ticks = {'ES': 30, 'NQ': 35, 'RTY': 30}.get(symbol, 30)

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
        # 🔥 FIX 21/11/2025: R:R MINIMUM assoupli 2.0→1.5 pour augmenter volume signaux
        # ═══════════════════════════════════════════════════════════════
        min_rr = 1.5 if confidence >= 0.80 else 1.8  # Setup fort: 1.5, moyen/faible: 1.8
        if rr_ratio < min_rr:
            return None

        signal = ConfluenceSignal(
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

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
        # ═══════════════════════════════════════════════════════════════
        return self._validate_signal_quality(
            signal, symbol, confidence, rr_ratio,
            context={'direction': direction, 'snapshot': data}
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
        # ✅ FIX 21/11 05:55: SL augmenté pour cohérence avec VWAP SD
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 20, 'NQ': 25, 'RTY': 25}.get(symbol, 20)  # ✅ Augmenté (NQ 12→25)

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
        # 🔥 FIX 21/11/2025: R:R MINIMUM assoupli pour augmenter volume signaux
        # ═══════════════════════════════════════════════════════════════
        min_rr = 1.5 if confidence >= 0.85 else 1.8  # CORRIGÉ: Setup fort: 1.5, moyen: 1.8
        if rr_ratio < min_rr:
            return None

        signal = ConfluenceSignal(
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

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
        # ═══════════════════════════════════════════════════════════════
        return self._validate_signal_quality(
            signal, symbol, min(confidence, 0.95), rr_ratio,
            context={'direction': direction}
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
        # ✅ FIX 21/11 05:55: SL augmenté pour cohérence avec VWAP SD
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 20, 'NQ': 25, 'RTY': 25}.get(symbol, 20)  # ✅ Augmenté (NQ 12→25)

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
        # 🔥 FIX 21/11/2025 14:00: Assouplir condition VWAP (50 → 80 ticks)
        #    Objectif: Accepter plus de setups Next Wall (actuellement 1-2/jour)
        if d_vwap > 80 or d_wall > thresholds["vwap_wall"]:
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
        # ✨ NOUVEAU 21/11 05:55: TP INTELLIGENT ajusté pour R:R 1.5:1
        # Base TP: 30 ticks ES, 50 ticks NQ (au lieu de 20 ticks fixe)
        # ═══════════════════════════════════════════════════════════════
        base_tp_ticks = {'ES': 45, 'NQ': 50, 'RTY': 45}.get(symbol, 50)  # ← R:R 1.5:1

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
        # 🔥 FIX 21/11/2025: R:R MINIMUM assoupli pour augmenter volume signaux
        # ═══════════════════════════════════════════════════════════════
        min_rr = 1.5 if confidence >= 0.80 else 1.8  # Setup fort: 1.5, moyen: 1.8
        if rr_ratio < min_rr:
            return None

        signal = ConfluenceSignal(
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

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
        # ═══════════════════════════════════════════════════════════════
        return self._validate_signal_quality(
            signal, symbol, min(confidence, 0.92), rr_ratio,
            context={'direction': direction}
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
        # ✅ FIX 21/11 05:55: SL augmenté pour cohérence avec VWAP SD
        # ═══════════════════════════════════════════════════════════════
        atr = data.get('atr', 0)
        atr_ticks = atr / tick_size if atr > 0 else 20

        base_sl_ticks = {'ES': 20, 'NQ': 25, 'RTY': 25}.get(symbol, 20)  # ✅ Augmenté (NQ 12→25)

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
        # 🔥 FIX 21/11/2025: R:R MINIMUM assoupli pour augmenter volume signaux
        # ═══════════════════════════════════════════════════════════════
        min_rr = 1.5 if confidence >= 0.85 else 1.8  # CORRIGÉ: Setup fort: 1.5, moyen: 1.8
        if rr_ratio < min_rr:
            return None

        signal = ConfluenceSignal(
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

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
        # ═══════════════════════════════════════════════════════════════
        return self._validate_signal_quality(
            signal, symbol, min(confidence, 0.88), rr_ratio,
            context={'direction': direction}
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

        base_sl_ticks = {'ES': 15, 'NQ': 20, 'RTY': 20}.get(symbol, 15)  # ✅ FIX 21/11 05:55: Augmenté (NQ 12→20) - Plus serré (triple confluence)

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
        # 🔥 CORRIGÉ 19/11/2025: R:R MINIMUM 1.8:1 (setup très fort mais toujours strict)
        # ═══════════════════════════════════════════════════════════════
        min_rr = 1.8  # CORRIGÉ: Triple confluence mais R:R minimum maintenu
        if rr_ratio < min_rr:
            return None

        signal = ConfluenceSignal(
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

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
        # ═══════════════════════════════════════════════════════════════
        return self._validate_signal_quality(
            signal, symbol, min(confidence, 0.98), rr_ratio,
            context={'direction': direction}
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

        base_sl_ticks = {'ES': 25, 'NQ': 30, 'RTY': 30}.get(symbol, 25)  # ✅ FIX 21/11 05:55: Augmenté (NQ 18→30) - Plus large (breakout)

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

            signal = ConfluenceSignal(
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

            # ═══════════════════════════════════════════════════════════════
            # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
            # ═══════════════════════════════════════════════════════════════
            return self._validate_signal_quality(
                signal, symbol, confidence, rr_ratio,
                context={'direction': direction}
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

        # Seuil minimum: 1.5 ATR (🔥 FIX 21/11: Réduit de 2.0 pour plus de signaux)
        if distance_vwap_atr < 1.5:
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

        # 🔥 CORRIGÉ 19/11/2025: R:R minimum 1.8 (setup très fort mais toujours strict)
        min_rr = 1.8  # CORRIGÉ: Setup très fort mais R:R minimum maintenu
        if rr_ratio < min_rr:
            return None

        signal = ConfluenceSignal(
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

        # ═══════════════════════════════════════════════════════════════
        # VALIDATION QUALITÉ PRÉ-SIGNAL (NOUVEAU! 🔥 DURCI 19/11/2025)
        # ═══════════════════════════════════════════════════════════════
        return self._validate_signal_quality(
            signal, symbol, confidence, rr_ratio,
            context={'direction': direction, 'snapshot': data}
        )


# ═══════════════════════════════════════════════════════════════════════════
# FONCTION D'INTÉGRATION DANS LE BOT
# ═══════════════════════════════════════════════════════════════════════════

def create_strategy(config: dict):
    """Factory function pour créer la stratégie"""
    return VWAPSDOptionsConfluenceStrategy(config)
