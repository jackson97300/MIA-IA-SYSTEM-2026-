"""
🎯 BIAS DIRECTIONNEL - Filtre TREND 1H/4H
Empêche trading contre-tendance

Architecture:
    - Analyse VWAP position
    - Analyse structure (ONH/ONL)
    - Analyse gamma_side
    - Détermine BIAS: BULLISH, BEARISH, ou NEUTRAL

Usage:
    from ml.bias_filter import BiasFilter

    bias_filter = BiasFilter()
    bias = bias_filter.get_bias(ml_data)

    if signal.side == "LONG" and bias != "BEARISH":
        → TRADE AUTORISÉ
    else:
        → TRADE REJETÉ (contre-tendance)

Version: 1.0
Date: 2025-11-11
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BiasFilter:
    """
    Filtre directionnel basé sur VWAP + Structure + Gamma

    Empêche le trading contre-tendance qui était la cause
    de 80% des pertes (WR 27% @ -$2,949)
    """

    def __init__(self):
        """Initialise le filtre de bias"""
        self.name = "BiasFilter"

        # Seuils pour détermination du bias
        self.bullish_vwap_min = 0.5  # ATR au-dessus VWAP
        self.bearish_vwap_max = -0.5  # ATR en-dessous VWAP

        self.bullish_position_min = 0.55  # Position dans ON range
        self.bearish_position_max = 0.45

        logger.info(f"✅ {self.name} initialisé (TREND filter 1H/4H)")

    def get_bias(self, ml_data: Dict) -> str:
        """
        Calcule le BIAS directionnel depuis ML_READY data

        Args:
            ml_data: Données ML_READY complètes

        Returns:
            "BULLISH": Autoriser LONG uniquement
            "BEARISH": Autoriser SHORT uniquement
            "NEUTRAL": Autoriser LONG ET SHORT (range)

        Logique (VERSION 2.0 - Multi-critères robuste):
            Priorité 1: mia_bullish_score (10 composantes)
            Priorité 2: Multi-critères (VWAP + Delta + OrderFlow + Gamma)

        Seuils:
            BULLISH: score > 0.25 OU (3/5 critères bullish)
            BEARISH: score < -0.25 OU (3/5 critères bearish)
            NEUTRAL: sinon
        """
        try:
            # ═══════════════════════════════════════════════════════════
            # PRIORITÉ 1: mia_bullish_score (SI DISPONIBLE)
            # ═══════════════════════════════════════════════════════════
            mia_score = ml_data.get('mia_bullish_score')

            if mia_score is not None:
                # Seuils ajustés pour plus de sensibilité
                if mia_score > 0.25:
                    logger.debug(f"📈 BIAS: BULLISH (MIA score={mia_score:+.2f})")
                    return "BULLISH"
                elif mia_score < -0.25:
                    logger.debug(f"📉 BIAS: BEARISH (MIA score={mia_score:+.2f})")
                    return "BEARISH"
                else:
                    logger.debug(f"↔️  BIAS: NEUTRAL (MIA score={mia_score:+.2f}, range)")
                    return "NEUTRAL"

            # ═══════════════════════════════════════════════════════════
            # PRIORITÉ 2: MULTI-CRITÈRES (FALLBACK SI MIA_SCORE ABSENT)
            # ═══════════════════════════════════════════════════════════
            logger.debug("⚠️ mia_bullish_score absent, utilisation multi-critères")

            mid = ml_data.get('mid')
            vwap = ml_data.get('vwap')
            atr = ml_data.get('atr', 1.0)

            if not mid or not vwap:
                logger.debug("⚠️ Bias: Données manquantes (mid ou VWAP)")
                return "NEUTRAL"

            # Distance VWAP en ATR
            d_vwap_atr = ml_data.get('d_vwap_atr', (mid - vwap) / atr if atr > 0 else 0)

            # Cumulative Delta (momentum)
            cum_delta = ml_data.get('cum_delta_session', 0)

            # OrderFlow instantané
            ask_pct = ml_data.get('askPct', 0.5)
            bid_pct = ml_data.get('bidPct', 0.5)

            # Gamma side
            gamma_side = ml_data.get('gamma_side', '')

            # Structure
            structure = ml_data.get('structure', {})
            onh = structure.get('onh')
            onl = structure.get('onl')

            # Position dans ON range
            if onh and onl and onh > onl:
                on_range = onh - onl
                position_in_on = (mid - onl) / on_range
            else:
                position_in_on = 0.5

            # ═══════════════════════════════════════════════════════════
            # CALCUL BULLISH (5 critères, besoin 3/5)
            # ═══════════════════════════════════════════════════════════
            bullish_vwap = d_vwap_atr > 0.5
            bullish_position = position_in_on > 0.55
            bullish_momentum = cum_delta > 500
            bullish_orderflow = bid_pct > 0.55
            bullish_gamma = gamma_side == 'below'  # En dessous gamma = bullish

            bullish_score = sum([
                bullish_vwap,
                bullish_position,
                bullish_momentum,
                bullish_orderflow,
                bullish_gamma
            ])

            if bullish_score >= 3:
                logger.debug(
                    f"📈 BIAS: BULLISH ({bullish_score}/5) "
                    f"[VWAP:{d_vwap_atr:+.1f}σ, Pos:{position_in_on:.0%}, "
                    f"ΔSession:{cum_delta:+}, Flow:{bid_pct:.0%}, Gamma:{gamma_side}]"
                )
                return "BULLISH"

            # ═══════════════════════════════════════════════════════════
            # CALCUL BEARISH (5 critères, besoin 3/5)
            # ═══════════════════════════════════════════════════════════
            bearish_vwap = d_vwap_atr < -0.5
            bearish_position = position_in_on < 0.45
            bearish_momentum = cum_delta < -500
            bearish_orderflow = ask_pct > 0.55
            bearish_gamma = gamma_side == 'above'  # Au dessus gamma = bearish

            bearish_score = sum([
                bearish_vwap,
                bearish_position,
                bearish_momentum,
                bearish_orderflow,
                bearish_gamma
            ])

            if bearish_score >= 3:
                logger.debug(
                    f"📉 BIAS: BEARISH ({bearish_score}/5) "
                    f"[VWAP:{d_vwap_atr:+.1f}σ, Pos:{position_in_on:.0%}, "
                    f"ΔSession:{cum_delta:+}, Flow:{ask_pct:.0%}, Gamma:{gamma_side}]"
                )
                return "BEARISH"

            # ═══════════════════════════════════════════════════════════
            # NEUTRAL (conditions mixtes)
            # ═══════════════════════════════════════════════════════════
            logger.debug(
                f"↔️  BIAS: NEUTRAL (Bull:{bullish_score}/5, Bear:{bearish_score}/5) "
                f"[VWAP:{d_vwap_atr:+.1f}σ, Pos:{position_in_on:.0%}, ΔSession:{cum_delta:+}]"
            )
            return "NEUTRAL"

        except Exception as e:
            logger.error(f"❌ Erreur BiasFilter.get_bias: {e}", exc_info=True)
            return "NEUTRAL"  # Sécurité: autoriser les deux en cas d'erreur

    def should_trade(self, signal_side: str, bias: str, signal_confidence: float = 0.0) -> bool:
        """
        Vérifie si le trade est autorisé selon le bias

        Args:
            signal_side: "LONG" ou "SHORT"
            bias: "BULLISH", "BEARISH", ou "NEUTRAL"
            signal_confidence: Confidence du signal (0.0 à 1.0)

        Returns:
            True si trade autorisé, False si contre-tendance

        Règles:
            BULLISH → Autoriser LONG uniquement (SHORT rejeté)
            BEARISH → Autoriser SHORT uniquement (LONG rejeté)
            NEUTRAL → Autoriser LONG ET SHORT (range)

            🔧 EXCEPTION HAUTE CONFIDENCE (2025-11-13 22:45):
            Si confidence ≥ 65%, autoriser même contre-tendance
            (opportunités qualitatives contre-tendance)
        """
        # 🔧 EXCEPTION: Haute confidence autorisée même contre-tendance
        if signal_confidence >= 0.65:
            logger.info(f"✅ BIAS FILTER OVERRIDE: Haute confidence {signal_confidence:.1%} → {signal_side} autorisé même en tendance {bias}")
            return True

        if bias == "NEUTRAL":
            return True  # Range, autoriser les deux directions

        if bias == "BULLISH" and signal_side == "LONG":
            return True  # ✅ Trade WITH trend

        if bias == "BEARISH" and signal_side == "SHORT":
            return True  # ✅ Trade WITH trend

        # ❌ CONTRE-TENDANCE INTERDIT (sauf haute confidence)
        return False

    def get_rejection_reason(self, signal_side: str, bias: str) -> str:
        """
        Génère un message de rejet clair

        Args:
            signal_side: "LONG" ou "SHORT"
            bias: "BULLISH", "BEARISH", ou "NEUTRAL"

        Returns:
            Message de rejet
        """
        if bias == "BULLISH":
            return f"BIAS FILTER: {signal_side} rejeté (Trend BULLISH → LONG uniquement)"
        elif bias == "BEARISH":
            return f"BIAS FILTER: {signal_side} rejeté (Trend BEARISH → SHORT uniquement)"
        else:
            return f"BIAS FILTER: {signal_side} autorisé (NEUTRAL range)"


def create_bias_filter():
    """
    Factory function pour créer une instance de BiasFilter

    Returns:
        BiasFilter instance
    """
    return BiasFilter()
