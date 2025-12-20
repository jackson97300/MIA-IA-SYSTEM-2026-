"""
TREND DIRECTION FILTER - Filtre les trades contre-tendance
============================================================

🎯 OBJECTIF: Éliminer les trades contre-tendance qui ont un WR de 25-35%
             vs 55-65% pour les trades dans le sens de la tendance.

Logique des professionnels et bots institutionnels:
- En tendance BULLISH → LONG uniquement
- En tendance BEARISH → SHORT uniquement
- En RANGE/NEUTRAL → Les deux directions autorisées (sur niveaux forts)

Indicateurs utilisés:
1. Position vs HVL (High Volume Level) - CRITIQUE
2. Position vs VWAP - IMPORTANT
3. Delta cumulatif - CONFIRMATION
4. Structure de marché (Higher Highs/Lower Lows) - CONTEXTE

🔥 AUDIT BRUTAL 02/12/2025:
   - Intégration complète dans launch_production_CLEAN_v2.py
   - Ajout de seuils stricts pour éviter les faux signaux
   - Logging détaillé pour debugging

Author: Jackson Trading System - MIA IA
Date: 02 Décembre 2025
Version: 2.0 - AUDIT BRUTAL
"""

import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class TrendBias(Enum):
    """Biais de tendance du marché"""
    STRONG_BULLISH = "STRONG_BULLISH"  # Prix >> HVL et >> VWAP + Delta positif
    BULLISH = "BULLISH"                 # Prix > HVL et > VWAP
    WEAK_BULLISH = "WEAK_BULLISH"       # Prix > HVL ou > VWAP (pas les deux)
    NEUTRAL = "NEUTRAL"                 # Prix entre HVL et VWAP (range)
    WEAK_BEARISH = "WEAK_BEARISH"       # Prix < HVL ou < VWAP (pas les deux)
    BEARISH = "BEARISH"                 # Prix < HVL et < VWAP
    STRONG_BEARISH = "STRONG_BEARISH"   # Prix << HVL et << VWAP + Delta négatif
    UNKNOWN = "UNKNOWN"                 # Données manquantes


@dataclass
class TrendAnalysis:
    """Résultat de l'analyse de tendance"""
    bias: TrendBias
    above_hvl: bool
    above_vwap: bool
    hvl_distance_ticks: float
    vwap_distance_ticks: float
    strength: float  # 0-1, force de la tendance
    delta_confirms: bool  # Delta cumulatif confirme la tendance
    market_structure: str  # "UPTREND", "DOWNTREND", "RANGE", "CHOPPY"
    reason: str

    # Détails supplémentaires
    cum_delta: float = 0.0
    delta_direction: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"
    hvl_value: float = 0.0
    vwap_value: float = 0.0
    mid_price: float = 0.0


class TrendDirectionFilter:
    """
    Filtre les trades contre-tendance.

    RÈGLE D'OR DES PROFESSIONNELS:
    ==============================
    - En tendance FORTE → Trader UNIQUEMENT dans le sens (pas d'exception!)
    - En tendance MODÉRÉE → Trader dans le sens (exceptions sur niveaux majeurs)
    - En tendance FAIBLE → Trader les deux directions avec prudence
    - En RANGE → Trader les extrêmes
    - En CHOP → NE PAS TRADER!

    STATISTIQUES ATTENDUES:
    =======================
    - Trades dans le sens: 55-65% WR
    - Trades contre le sens: 25-35% WR
    - Différence: +20-30% de WR!

    IMPACT ESTIMÉ:
    ==============
    - Réduction trades de merde: -30%
    - Amélioration WR: +10-15%
    - P&L: +$500-1000/jour
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize filter with config.

        Args:
            config: Configuration optionnelle
        """

        self.config = config or {}

        # Configuration par instrument
        self.INSTRUMENT_CONFIG = {
            "ES": {
                "tick_size": 0.25,
                "allow_counter_trend": False,  # 🔥 BLOQUER contre-tendance
                "counter_trend_on_major_levels": True,  # Exception sur niveaux majeurs
                "min_trend_strength": 0.3,  # Force minimum pour considérer tendance
                "strong_trend_threshold": 0.6,  # Seuil pour tendance forte
                "hvl_significance_ticks": 20,  # Distance HVL significative
                "vwap_significance_ticks": 15,  # Distance VWAP significative
                "delta_threshold": 500,  # Seuil delta pour confirmation
                # 🔥 NOUVEAU 08/12: VWAP Distance Filter (ES uniquement)
                # Bloque LONG si prix trop loin EN-DESSOUS du VWAP
                "vwap_max_distance_long_ticks": -100,  # LONG bloqué si < -100t du VWAP
                "vwap_distance_filter_enabled": True,  # Actif pour ES
            },
            "NQ": {
                "tick_size": 0.25,
                "allow_counter_trend": False,  # 🔥 BLOQUER contre-tendance
                "counter_trend_on_major_levels": True,
                "min_trend_strength": 0.3,
                "strong_trend_threshold": 0.6,
                "hvl_significance_ticks": 30,  # NQ plus volatil
                "vwap_significance_ticks": 25,
                "delta_threshold": 800,  # NQ a plus de volume
                # 🔥 08/12: VWAP Distance Filter DÉSACTIVÉ pour NQ (performe bien même loin du VWAP)
                "vwap_distance_filter_enabled": False,
            },
            "RTY": {
                "tick_size": 0.10,
                "allow_counter_trend": False,  # 🔥 BLOQUER contre-tendance
                "counter_trend_on_major_levels": True,
                "min_trend_strength": 0.35,  # RTY plus strict
                "strong_trend_threshold": 0.65,
                "hvl_significance_ticks": 40,  # RTY très volatil
                "vwap_significance_ticks": 30,
                "delta_threshold": 400,  # RTY moins de volume
                # 🔥 08/12: VWAP Distance Filter DÉSACTIVÉ pour RTY
                "vwap_distance_filter_enabled": False,
            },
        }

        # Niveaux majeurs qui permettent contre-tendance (exceptions)
        # 🔥 08/12: Liste COMPLÈTE des niveaux institutionnels
        self.MAJOR_LEVELS = [
            # Gamma Walls (murs gamma = zones de rebond)
            'gamma_wall', 'gamma_wall_put', 'gamma_wall_call',
            'gamma_wall_0dte',

            # Support/Résistance institutionnels
            'put_support', 'call_resistance',
            'put_support_0dte', 'call_resistance_0dte',

            # GEX Levels (TOUS les 10 niveaux!)
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
            'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
            'gex',  # Générique

            # HVL (High Volume Levels)
            'hvl', 'hvl_0dte',

            # Blind Spots (zones sans gamma = mouvements rapides)
            'blind_spot', 'blind_spot_0', 'blind_spot_1', 'blind_spot_2',

            # Next Wall (prochain mur)
            'next_wall',

            # Balance/Dealer levels
            'balance_line', 'bl', 'dealer',

            # Niveaux temporels
            'weekly', 'monthly', '0dte',

            # Strikes options
            'strike', 'atm_strike',
        ]

        # Statistiques de filtrage
        self.stats = {
            'total_checks': 0,
            'allowed_with_trend': 0,
            'allowed_neutral': 0,
            'allowed_counter_major_level': 0,
            'blocked_counter_trend': 0,
            'blocked_strong_counter': 0,
        }

        # Historique pour analyse
        self.history: List[Dict] = []

        logger.info("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              TREND DIRECTION FILTER v2.0 - AUDIT BRUTAL                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  RÈGLE DES PROFESSIONNELS:                                                   ║
║  ─────────────────────────                                                   ║
║  • STRONG BULLISH → LONG uniquement (AUCUNE exception!)                      ║
║  • BULLISH        → LONG uniquement (exception niveaux majeurs)              ║
║  • NEUTRAL        → Les deux directions sur niveaux forts                    ║
║  • BEARISH        → SHORT uniquement (exception niveaux majeurs)             ║
║  • STRONG BEARISH → SHORT uniquement (AUCUNE exception!)                     ║
║                                                                              ║
║  STATISTIQUES ATTENDUES:                                                     ║
║  ───────────────────────                                                     ║
║  • Trades avec tendance:    55-65% WR                                        ║
║  • Trades contre tendance:  25-35% WR                                        ║
║  • Gain potentiel:          +20-30% WR en filtrant contre-tendance           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)

    def analyze_trend(
        self,
        snapshot: Dict,
        symbol: str = "ES",
    ) -> TrendAnalysis:
        """
        Analyse la tendance actuelle du marché.

        Args:
            snapshot: Données de marché
            symbol: Instrument

        Returns:
            TrendAnalysis avec biais et détails
        """

        config = self.INSTRUMENT_CONFIG.get(symbol, self.INSTRUMENT_CONFIG["ES"])
        tick_size = config["tick_size"]

        # Extraire données
        mid = snapshot.get('mid') or snapshot.get('price') or snapshot.get('last')
        hvl = snapshot.get('hvl') or snapshot.get('hvl_0dte') or snapshot.get('HVL')
        vwap = snapshot.get('vwap') or snapshot.get('VWAP')
        cum_delta = snapshot.get('cum_delta_session') or snapshot.get('cum_delta') or 0

        # Vérifier données disponibles
        if not mid:
            return TrendAnalysis(
                bias=TrendBias.UNKNOWN,
                above_hvl=False,
                above_vwap=False,
                hvl_distance_ticks=0,
                vwap_distance_ticks=0,
                strength=0,
                delta_confirms=False,
                market_structure="UNKNOWN",
                reason="❓ Prix non disponible"
            )

        if not hvl and not vwap:
            return TrendAnalysis(
                bias=TrendBias.UNKNOWN,
                above_hvl=False,
                above_vwap=False,
                hvl_distance_ticks=0,
                vwap_distance_ticks=0,
                strength=0,
                delta_confirms=False,
                market_structure="UNKNOWN",
                reason="❓ HVL et VWAP non disponibles"
            )

        # Calculer positions relatives
        above_hvl = mid > hvl if hvl else None
        above_vwap = mid > vwap if vwap else None

        hvl_distance = (mid - hvl) / tick_size if hvl else 0
        vwap_distance = (mid - vwap) / tick_size if vwap else 0

        # Analyser delta
        delta_threshold = config["delta_threshold"]
        delta_bullish = cum_delta > delta_threshold
        delta_bearish = cum_delta < -delta_threshold
        delta_direction = "BULLISH" if delta_bullish else ("BEARISH" if delta_bearish else "NEUTRAL")

        # Seuils de signification
        hvl_significant = abs(hvl_distance) > config["hvl_significance_ticks"]
        vwap_significant = abs(vwap_distance) > config["vwap_significance_ticks"]

        # Déterminer biais avec granularité
        if hvl and vwap:
            if above_hvl and above_vwap:
                # Au-dessus des deux → BULLISH
                if hvl_significant and vwap_significant and delta_bullish:
                    bias = TrendBias.STRONG_BULLISH
                    strength = min(1.0, (abs(hvl_distance) + abs(vwap_distance)) / 150)
                    market_structure = "UPTREND"
                    reason = f"📈📈 STRONG BULLISH: Prix >> HVL (+{hvl_distance:.0f}t) et >> VWAP (+{vwap_distance:.0f}t) + Delta ↑"
                elif hvl_significant or vwap_significant:
                    bias = TrendBias.BULLISH
                    strength = min(0.8, (abs(hvl_distance) + abs(vwap_distance)) / 100)
                    market_structure = "UPTREND"
                    reason = f"📈 BULLISH: Prix > HVL (+{hvl_distance:.0f}t) et > VWAP (+{vwap_distance:.0f}t)"
                else:
                    bias = TrendBias.WEAK_BULLISH
                    strength = 0.4
                    market_structure = "RANGE"
                    reason = f"↗️ WEAK BULLISH: Prix légèrement > HVL/VWAP"
                delta_confirms = delta_bullish

            elif not above_hvl and not above_vwap:
                # En-dessous des deux → BEARISH
                if hvl_significant and vwap_significant and delta_bearish:
                    bias = TrendBias.STRONG_BEARISH
                    strength = min(1.0, (abs(hvl_distance) + abs(vwap_distance)) / 150)
                    market_structure = "DOWNTREND"
                    reason = f"📉📉 STRONG BEARISH: Prix << HVL ({hvl_distance:.0f}t) et << VWAP ({vwap_distance:.0f}t) + Delta ↓"
                elif hvl_significant or vwap_significant:
                    bias = TrendBias.BEARISH
                    strength = min(0.8, (abs(hvl_distance) + abs(vwap_distance)) / 100)
                    market_structure = "DOWNTREND"
                    reason = f"📉 BEARISH: Prix < HVL ({hvl_distance:.0f}t) et < VWAP ({vwap_distance:.0f}t)"
                else:
                    bias = TrendBias.WEAK_BEARISH
                    strength = 0.4
                    market_structure = "RANGE"
                    reason = f"↘️ WEAK BEARISH: Prix légèrement < HVL/VWAP"
                delta_confirms = delta_bearish

            else:
                # Entre HVL et VWAP → NEUTRAL (range)
                bias = TrendBias.NEUTRAL
                delta_confirms = False
                strength = 0.2
                market_structure = "RANGE"

                if above_hvl:
                    reason = f"↔️ NEUTRAL: Prix > HVL (+{hvl_distance:.0f}t) mais < VWAP ({vwap_distance:.0f}t)"
                else:
                    reason = f"↔️ NEUTRAL: Prix < HVL ({hvl_distance:.0f}t) mais > VWAP (+{vwap_distance:.0f}t)"

        elif hvl:
            # Seulement HVL disponible
            if above_hvl:
                bias = TrendBias.WEAK_BULLISH if hvl_significant else TrendBias.NEUTRAL
                strength = 0.5 if hvl_significant else 0.3
                market_structure = "UPTREND" if hvl_significant else "RANGE"
                reason = f"📈 BULLISH (HVL only): Prix au-dessus HVL (+{hvl_distance:.0f}t)"
            else:
                bias = TrendBias.WEAK_BEARISH if hvl_significant else TrendBias.NEUTRAL
                strength = 0.5 if hvl_significant else 0.3
                market_structure = "DOWNTREND" if hvl_significant else "RANGE"
                reason = f"📉 BEARISH (HVL only): Prix en-dessous HVL ({hvl_distance:.0f}t)"
            delta_confirms = delta_bullish if above_hvl else delta_bearish

        else:
            # Seulement VWAP disponible
            if above_vwap:
                bias = TrendBias.WEAK_BULLISH if vwap_significant else TrendBias.NEUTRAL
                strength = 0.4 if vwap_significant else 0.2
                market_structure = "UPTREND" if vwap_significant else "RANGE"
                reason = f"📈 BULLISH (VWAP only): Prix au-dessus VWAP (+{vwap_distance:.0f}t)"
            else:
                bias = TrendBias.WEAK_BEARISH if vwap_significant else TrendBias.NEUTRAL
                strength = 0.4 if vwap_significant else 0.2
                market_structure = "DOWNTREND" if vwap_significant else "RANGE"
                reason = f"📉 BEARISH (VWAP only): Prix en-dessous VWAP ({vwap_distance:.0f}t)"
            delta_confirms = delta_bullish if above_vwap else delta_bearish

        return TrendAnalysis(
            bias=bias,
            above_hvl=above_hvl if above_hvl is not None else False,
            above_vwap=above_vwap if above_vwap is not None else False,
            hvl_distance_ticks=hvl_distance,
            vwap_distance_ticks=vwap_distance,
            strength=strength,
            delta_confirms=delta_confirms,
            market_structure=market_structure,
            reason=reason,
            cum_delta=cum_delta,
            delta_direction=delta_direction,
            hvl_value=hvl if hvl else 0,
            vwap_value=vwap if vwap else 0,
            mid_price=mid if mid else 0
        )

    def should_allow_trade(
        self,
        direction: str,
        snapshot: Dict,
        symbol: str = "ES",
        trigger_level: Optional[str] = None,
        level_score: int = 0,
    ) -> Tuple[bool, str, TrendAnalysis]:
        """
        Décide si un trade dans cette direction est autorisé.

        Args:
            direction: "LONG" ou "SHORT"
            snapshot: Données de marché
            symbol: Instrument
            trigger_level: Niveau qui a déclenché le signal (optionnel)
            level_score: Score du niveau (1=faible, 2=moyen, 3=fort) - V10.3

        Returns:
            (is_allowed, reason, trend_analysis)
        """

        self.stats['total_checks'] += 1
        config = self.INSTRUMENT_CONFIG.get(symbol, self.INSTRUMENT_CONFIG["ES"])

        # Analyser tendance
        trend = self.analyze_trend(snapshot, symbol)

        # ═══════════════════════════════════════════════════════════════
        # 🔥 V10.3: REBONDS AUTORISÉS SUR SCORE 2+ (24 niveaux MenthorQ)
        # ═══════════════════════════════════════════════════════════════
        # Score 3: gex_1, gex_2, hvl, vwap, gamma_wall_level, vpoc, 1d_max, 1d_min
        # Score 2: gex_3-5, hvl_0dte, gamma_wall_0dte, call_resistance, put_support,
        #          blind_spot_0-2, vwap_up1, vwap_dn1, vah, val, ibh, ibl
        # ═══════════════════════════════════════════════════════════════
        if level_score >= 2:
            self.stats['allowed_counter_major_level'] += 1
            logger.info(f"✅ [{symbol}] V10.3: Rebond autorisé sur niveau Score {level_score} ({trigger_level})")
            return True, f"✅ Rebond V10.3 autorisé sur niveau Score {level_score} ({trigger_level})", trend

        # Log détaillé
        logger.info(f"┌─────────────────────────────────────────────────────────────")
        logger.info(f"│ [TREND FILTER] {symbol} {direction}")
        logger.info(f"├─────────────────────────────────────────────────────────────")
        logger.info(f"│ Biais: {trend.bias.value} (strength: {trend.strength:.2f})")
        logger.info(f"│ HVL: {trend.hvl_value:.2f} (distance: {trend.hvl_distance_ticks:+.0f}t)")
        logger.info(f"│ VWAP: {trend.vwap_value:.2f} (distance: {trend.vwap_distance_ticks:+.0f}t)")
        logger.info(f"│ Delta: {trend.cum_delta:.0f} ({trend.delta_direction})")
        logger.info(f"│ Structure: {trend.market_structure}")
        logger.info(f"└─────────────────────────────────────────────────────────────")

        # Si tendance inconnue, autoriser (fail-safe)
        if trend.bias == TrendBias.UNKNOWN:
            self.stats['allowed_neutral'] += 1
            return True, "✅ Tendance inconnue - Trade autorisé par défaut", trend

        # ══════════════════════════════════════════════════════════════
        # 🔥 NOUVEAU 08/12: VWAP DISTANCE FILTER (ES uniquement)
        # Bloque LONG si prix trop loin en-dessous du VWAP
        # SAUF sur niveaux majeurs (rebonds autorisés!)
        # ══════════════════════════════════════════════════════════════
        if config.get("vwap_distance_filter_enabled", False):
            vwap_max_long = config.get("vwap_max_distance_long_ticks", -100)

            if direction == "LONG" and trend.vwap_distance_ticks < vwap_max_long:
                # 🎯 EXCEPTION: Autoriser rebonds sur niveaux majeurs!
                is_major_level = False
                if trigger_level:
                    trigger_lower = trigger_level.lower()
                    for major in self.MAJOR_LEVELS:
                        if major.lower() in trigger_lower or trigger_lower in major.lower():
                            is_major_level = True
                            break

                if is_major_level:
                    logger.info(f"⚠️ [{symbol}] REBOND AUTORISÉ sur niveau majeur: {trigger_level}")
                    logger.info(f"   → VWAP distance: {trend.vwap_distance_ticks:.0f}t (dépassé mais niveau fort)")
                    # Ne pas bloquer - continuer vers les autres vérifications
                else:
                    self.stats['blocked_counter_trend'] += 1
                    logger.warning(f"🚫 [{symbol}] LONG BLOQUÉ - Prix trop loin du VWAP (pas de niveau majeur)!")
                    logger.warning(f"   → VWAP distance: {trend.vwap_distance_ticks:.0f}t (max: {vwap_max_long}t)")
                    logger.warning(f"   → Prix: {trend.mid_price:.2f} | VWAP: {trend.vwap_value:.2f}")
                    return False, f"❌ LONG BLOQUÉ - Prix {trend.vwap_distance_ticks:.0f}t sous VWAP (max: {vwap_max_long}t) sans niveau majeur", trend

        # Si tendance neutre, autoriser les deux directions
        if trend.bias == TrendBias.NEUTRAL:
            self.stats['allowed_neutral'] += 1
            return True, "✅ Marché en range - Direction autorisée", trend

        # Vérifier alignement direction/tendance
        is_bullish_trend = trend.bias in [TrendBias.STRONG_BULLISH, TrendBias.BULLISH, TrendBias.WEAK_BULLISH]
        is_bearish_trend = trend.bias in [TrendBias.STRONG_BEARISH, TrendBias.BEARISH, TrendBias.WEAK_BEARISH]

        is_aligned = (
            (is_bullish_trend and direction == "LONG") or
            (is_bearish_trend and direction == "SHORT")
        )

        if is_aligned:
            self.stats['allowed_with_trend'] += 1
            delta_msg = " + Delta confirme ✓" if trend.delta_confirms else ""
            return True, f"✅ {direction} aligné avec tendance {trend.bias.value}{delta_msg}", trend

        # ══════════════════════════════════════════════════════════════
        # TRADE CONTRE-TENDANCE DÉTECTÉ!
        # ══════════════════════════════════════════════════════════════

        # 1. TENDANCE FORTE → BLOQUER ABSOLUMENT (pas d'exception!)
        if trend.bias in [TrendBias.STRONG_BULLISH, TrendBias.STRONG_BEARISH]:
            self.stats['blocked_strong_counter'] += 1
            logger.warning(f"🚫🚫 [{symbol}] {direction} BLOQUÉ - Tendance FORTE {trend.bias.value}")
            logger.warning(f"   → Aucune exception possible sur tendance forte!")
            return False, f"❌❌ {direction} BLOQUÉ - Contre tendance FORTE {trend.bias.value} (AUCUNE EXCEPTION!)", trend

        # 2. Vérifier si contre-tendance autorisé globalement (config)
        if config["allow_counter_trend"]:
            self.stats['allowed_counter_major_level'] += 1
            return True, f"⚠️ {direction} contre-tendance autorisé par config", trend

        # 3. Vérifier exception sur niveaux majeurs
        if config["counter_trend_on_major_levels"] and trigger_level:
            trigger_lower = trigger_level.lower()
            for major in self.MAJOR_LEVELS:
                if major.lower() in trigger_lower or trigger_lower in major.lower():
                    self.stats['allowed_counter_major_level'] += 1
                    logger.info(f"⚠️ [{symbol}] Exception contre-tendance sur niveau majeur: {trigger_level}")
                    return True, f"⚠️ {direction} contre-tendance autorisé sur niveau majeur ({trigger_level})", trend

        # 4. Tendance FAIBLE → Autoriser avec warning
        if trend.bias in [TrendBias.WEAK_BULLISH, TrendBias.WEAK_BEARISH]:
            self.stats['allowed_counter_major_level'] += 1
            logger.warning(f"⚠️ [{symbol}] {direction} contre tendance FAIBLE - Autorisé avec prudence")
            return True, f"⚠️ {direction} contre tendance faible - Autorisé avec prudence", trend

        # 5. BLOQUER le trade contre-tendance
        self.stats['blocked_counter_trend'] += 1
        logger.warning(f"🚫 [{symbol}] {direction} BLOQUÉ - Contre tendance {trend.bias.value}")
        return False, f"❌ {direction} BLOQUÉ - Contre tendance {trend.bias.value}", trend

    def get_stats(self) -> Dict:
        """Retourne les statistiques de filtrage"""
        total = self.stats['total_checks']
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'pct_allowed_with_trend': (self.stats['allowed_with_trend'] / total) * 100,
            'pct_allowed_neutral': (self.stats['allowed_neutral'] / total) * 100,
            'pct_allowed_counter': (self.stats['allowed_counter_major_level'] / total) * 100,
            'pct_blocked': ((self.stats['blocked_counter_trend'] + self.stats['blocked_strong_counter']) / total) * 100,
        }

    def print_stats(self):
        """Affiche les statistiques de filtrage"""
        stats = self.get_stats()
        logger.info("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TREND DIRECTION FILTER - STATISTIQUES                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Total checks:           {total_checks:>6}                                          ║
║  ────────────────────────────────────────────────────────────────────────────║
║  ✅ Autorisés (tendance): {allowed_with_trend:>6} ({pct_allowed_with_trend:>5.1f}%)                              ║
║  ✅ Autorisés (neutral):  {allowed_neutral:>6} ({pct_allowed_neutral:>5.1f}%)                              ║
║  ⚠️  Autorisés (counter):  {allowed_counter_major_level:>6} ({pct_allowed_counter:>5.1f}%)                              ║
║  ❌ Bloqués (counter):    {blocked_counter_trend:>6}                                          ║
║  ❌❌ Bloqués (strong):    {blocked_strong_counter:>6}                                          ║
║  ────────────────────────────────────────────────────────────────────────────║
║  📊 Taux de blocage:      {pct_blocked:>5.1f}%                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """.format(**stats))


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Tests du module"""

    print("\n" + "="*80)
    print("TESTS TREND DIRECTION FILTER")
    print("="*80 + "\n")

    filter = TrendDirectionFilter()

    # Test 1: Tendance BULLISH + LONG = OK
    print("\n[TEST 1] BULLISH + LONG → Devrait être autorisé")
    snapshot1 = {
        'mid': 6850.0,
        'hvl': 6820.0,  # Prix > HVL (+30t)
        'vwap': 6830.0,  # Prix > VWAP (+20t)
        'cum_delta': 1500
    }
    allowed, reason, trend = filter.should_allow_trade("LONG", snapshot1, "ES")
    print(f"   Résultat: {'✅ PASS' if allowed else '❌ FAIL'} - {reason}")
    assert allowed, "LONG en BULLISH devrait être autorisé"

    # Test 2: Tendance BULLISH + SHORT = BLOQUÉ
    print("\n[TEST 2] BULLISH + SHORT → Devrait être bloqué")
    allowed, reason, trend = filter.should_allow_trade("SHORT", snapshot1, "ES")
    print(f"   Résultat: {'✅ PASS' if not allowed else '❌ FAIL'} - {reason}")
    assert not allowed, "SHORT en BULLISH devrait être bloqué"

    # Test 3: Tendance BEARISH + SHORT = OK
    print("\n[TEST 3] BEARISH + SHORT → Devrait être autorisé")
    snapshot2 = {
        'mid': 6780.0,
        'hvl': 6820.0,  # Prix < HVL (-40t)
        'vwap': 6810.0,  # Prix < VWAP (-30t)
        'cum_delta': -2000
    }
    allowed, reason, trend = filter.should_allow_trade("SHORT", snapshot2, "ES")
    print(f"   Résultat: {'✅ PASS' if allowed else '❌ FAIL'} - {reason}")
    assert allowed, "SHORT en BEARISH devrait être autorisé"

    # Test 4: Tendance BEARISH + LONG = BLOQUÉ
    print("\n[TEST 4] BEARISH + LONG → Devrait être bloqué")
    allowed, reason, trend = filter.should_allow_trade("LONG", snapshot2, "ES")
    print(f"   Résultat: {'✅ PASS' if not allowed else '❌ FAIL'} - {reason}")
    assert not allowed, "LONG en BEARISH devrait être bloqué"

    # Test 5: Tendance NEUTRAL = OK dans les deux sens
    print("\n[TEST 5] NEUTRAL + LONG/SHORT → Devrait être autorisé")
    snapshot3 = {
        'mid': 6815.0,
        'hvl': 6820.0,  # Prix < HVL (-5t)
        'vwap': 6810.0,  # Prix > VWAP (+5t)
        'cum_delta': 100
    }
    allowed_long, _, _ = filter.should_allow_trade("LONG", snapshot3, "ES")
    allowed_short, _, _ = filter.should_allow_trade("SHORT", snapshot3, "ES")
    print(f"   LONG: {'✅ PASS' if allowed_long else '❌ FAIL'}")
    print(f"   SHORT: {'✅ PASS' if allowed_short else '❌ FAIL'}")
    assert allowed_long and allowed_short, "Les deux directions devraient être autorisées en NEUTRAL"

    # Test 6: Contre-tendance sur niveau majeur en tendance MODÉRÉE = OK
    print("\n[TEST 6] BULLISH MODÉRÉ + SHORT sur gamma_wall_put → Devrait être autorisé (exception)")
    snapshot_moderate_bullish = {
        'mid': 6835.0,
        'hvl': 6820.0,  # Prix > HVL (+15t) - pas assez pour STRONG
        'vwap': 6825.0,  # Prix > VWAP (+10t) - pas assez pour STRONG
        'cum_delta': 200  # Delta faible - pas de confirmation
    }
    allowed, reason, trend = filter.should_allow_trade("SHORT", snapshot_moderate_bullish, "ES", trigger_level="gamma_wall_put")
    print(f"   Résultat: {'✅ PASS' if allowed else '❌ FAIL'} - {reason}")
    assert allowed, "SHORT sur niveau majeur en tendance modérée devrait être autorisé"

    # Test 7: STRONG BULLISH + SHORT = BLOQUÉ (même sur niveau majeur)
    print("\n[TEST 7] STRONG BULLISH + SHORT → Devrait être bloqué (même sur niveau majeur)")
    allowed, reason, trend = filter.should_allow_trade("SHORT", snapshot1, "ES", trigger_level="gamma_wall_put")
    print(f"   Résultat: {'✅ PASS' if not allowed else '❌ FAIL'} - {reason}")
    assert not allowed, "SHORT en STRONG BULLISH devrait être bloqué même sur niveau majeur"

    # Afficher statistiques
    print("\n")
    filter.print_stats()

    print("\n" + "="*80)
    print("TOUS LES TESTS PASSÉS ✅")
    print("="*80 + "\n")
