#!/usr/bin/env python3
"""
SIGNAL EXPLAINER ML_READY - Version adaptée pour nouvelle architecture
=======================================================================

Version: 3.0 - Compatible ML_READY
Date: Novembre 2025

Adapte SignalExplainer v2.0 pour fonctionner avec TradingSignal et ML_READY data.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

# === CONSTANTS ===

# Traffic-light mapping
TRAFFIC_LIGHT = {
    "NO_TRADE": "🔴",
    "NEUTRAL": "🟡",
    "LONG": "🟢",
    "SHORT": "🔴",
    "GO": "🟢"
}

# Bullish score emojis
BULLISH_EMOJI = {
    "bullish": "🟢",
    "neutral": "🟡",
    "bearish": "🔴"
}

# === MAIN CLASS ===

class SignalExplainerMLReady:
    """Expliqueur de signaux adapté pour ML_READY"""

    def __init__(self):
        self.explain_count = 0
        logger.debug("✅ SignalExplainerMLReady initialisé")

    def explain_signal(self,
                       signal: Any,  # TradingSignal ou PatternSignal
                       ml_data: Dict[str, Any],
                       bullish_score: Optional[float] = None) -> Dict[str, Any]:
        """
        Explique un signal de trading avec ML_READY data

        Args:
            signal: TradingSignal ou PatternSignal
            ml_data: Données ML_READY complètes
            bullish_score: Score bullish/bearish (-1 à +1)

        Returns:
            Dict avec explication structurée
        """
        start_time = time.time()
        self.explain_count += 1

        try:
            # 1. Extraire les infos du signal
            # ✅ CORRIGÉ: Gérer dict ET objet
            if isinstance(signal, dict):
                symbol = signal.get('symbol', 'ES')
                action = signal.get('action', signal.get('side', 'NEUTRAL'))
                confidence = signal.get('confidence', 0.0)
                strategy = signal.get('strategy', signal.get('name', 'unknown'))
                entry_price = signal.get('entry_price', ml_data.get('mid', 0))
            else:
                symbol = getattr(signal, 'symbol', 'ES')
                action = getattr(signal, 'action', None) or getattr(signal, 'side', 'NEUTRAL')
                confidence = getattr(signal, 'confidence', 0.0)
                strategy = getattr(signal, 'strategy', 'unknown')
                entry_price = getattr(signal, 'entry_price', ml_data.get('mid', 0))

            # 2. Traffic light
            traffic_light = TRAFFIC_LIGHT.get(action, "🟡")

            # 3. Bullish emoji
            bullish_emoji = self._get_bullish_emoji(bullish_score)

            # 4. Construire le message brief
            brief = self._build_brief(
                symbol=symbol,
                action=action,
                confidence=confidence,
                strategy=strategy,
                ml_data=ml_data,
                bullish_score=bullish_score,
                bullish_emoji=bullish_emoji
            )

            # 5. Construire le message full
            full = self._build_full(
                symbol=symbol,
                action=action,
                confidence=confidence,
                strategy=strategy,
                entry_price=entry_price,
                signal=signal,
                ml_data=ml_data,
                bullish_score=bullish_score,
                bullish_emoji=bullish_emoji
            )

            # 6. Retourner l'explication
            explanation = {
                "brief": brief,
                "full": full,
                "traffic_light": traffic_light,
                "bullish_emoji": bullish_emoji,
                "bullish_score": bullish_score,
                "timestamp": datetime.now().isoformat(),
                "explanation_id": f"exp_{self.explain_count}_{int(time.time())}"
            }

            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"⚡ Explication générée en {elapsed:.1f}ms")

            return explanation

        except Exception as e:
            logger.error(f"❌ Erreur explication: {e}")
            return self._fallback_explanation(str(e))

    def _get_bullish_emoji(self, bullish_score: Optional[float]) -> str:
        """Retourne l'emoji bullish approprié"""
        if bullish_score is None:
            return "🟡"

        if bullish_score > 0.3:
            return "🟢"
        elif bullish_score < -0.3:
            return "🔴"
        else:
            return "🟡"

    def _build_brief(self,
                     symbol: str,
                     action: str,
                     confidence: float,
                     strategy: str,
                     ml_data: Dict[str, Any],
                     bullish_score: Optional[float],
                     bullish_emoji: str) -> str:
        """
        Construit un message brief ≤ 280 chars

        Format:
        🟢 [ES] LONG 0.75 | Strategy: hybrid | Bullish: 🟢 +0.62 | VWAP: above | GEX: 5300 (8t)
        """
        parts = []

        # Action + Symbol
        parts.append(f"[{symbol}] {action} {confidence:.2f}")

        # Strategy
        parts.append(f"Strat: {strategy[:15]}")

        # Bullish score
        if bullish_score is not None:
            parts.append(f"Bullish: {bullish_emoji} {bullish_score:+.2f}")

        # VWAP position
        vwap_pos = "above" if ml_data.get('mid', 0) > ml_data.get('vwap', 0) else "below"
        parts.append(f"VWAP: {vwap_pos}")

        # MenthorQ - GEX closest
        gex_levels = [
            ('gex_0', ml_data.get('gex_0')),
            ('gex_1', ml_data.get('gex_1')),
            ('gex_2', ml_data.get('gex_2'))
        ]
        closest_gex = None
        min_dist = float('inf')
        mid = ml_data.get('mid', 0)

        for name, price in gex_levels:
            if price:
                dist = abs(mid - price)
                if dist < min_dist:
                    min_dist = dist
                    closest_gex = (name, price, dist / 0.25)  # ticks

        if closest_gex:
            parts.append(f"GEX: {closest_gex[1]:.2f} ({closest_gex[2]:.0f}t)")

        brief = " | ".join(parts)
        return brief[:280]

    def _build_full(self,
                    symbol: str,
                    action: str,
                    confidence: float,
                    strategy: str,
                    entry_price: float,
                    signal: Any,
                    ml_data: Dict[str, Any],
                    bullish_score: Optional[float],
                    bullish_emoji: str) -> str:
        """
        Construit un message full ≤ 10 lignes

        Format:
        **[ES] LONG** Conf: 0.75
        Strategy: hybrid_strategy
        Bullish: 🟢 +0.62 (OF:+0.5, VWAP:+0.3, Corridor:0.85)
        Entry: 5300.00 | SL: 5295.00 | TP: 5310.00
        VWAP: 5298.50 (above) | GEX: 5300 (8t)
        Dealers Bias: +0.15 | VIX: 18.5 (MID)
        """
        lines = []

        # Ligne 1: Décision principale
        lines.append(f"**[{symbol}] {action}** Conf: {confidence:.2f}")

        # Ligne 2: Strategy
        lines.append(f"Strategy: {strategy}")

        # Ligne 3: Bullish score avec détails
        if bullish_score is not None:
            # Essayer de récupérer les composantes depuis metadata
            metadata = getattr(signal, 'metadata', {})
            bullish_details = metadata.get('bullish_details', {})

            if bullish_details:
                of_score = bullish_details.get('orderflow_score', 0)
                vwap_score = bullish_details.get('vwap_score', 0)
                headroom = bullish_details.get('headroom_factor', 1.0)
                lines.append(f"Bullish: {bullish_emoji} {bullish_score:+.2f} (OF:{of_score:+.1f}, VWAP:{vwap_score:+.1f}, Corridor:{headroom:.2f})")
            else:
                lines.append(f"Bullish: {bullish_emoji} {bullish_score:+.2f}")

        # Ligne 4: Entry/SL/TP
        sl = getattr(signal, 'stop_loss', None)
        tp = getattr(signal, 'take_profit', None)
        if sl and tp:
            lines.append(f"Entry: {entry_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")

        # Ligne 5: VWAP
        vwap = ml_data.get('vwap', 0)
        mid = ml_data.get('mid', 0)
        vwap_pos = "above" if mid > vwap else "below"
        lines.append(f"VWAP: {vwap:.2f} ({vwap_pos})")

        # Ligne 6: MenthorQ (GEX closest)
        gex_levels = [
            ('gex_0', ml_data.get('gex_0')),
            ('gex_1', ml_data.get('gex_1')),
            ('gex_2', ml_data.get('gex_2'))
        ]
        closest_gex = None
        min_dist = float('inf')

        for name, price in gex_levels:
            if price:
                dist = abs(mid - price)
                if dist < min_dist:
                    min_dist = dist
                    closest_gex = (name, price, dist / 0.25)  # ticks

        if closest_gex:
            lines.append(f"GEX closest: {closest_gex[1]:.2f} ({closest_gex[2]:.0f}t)")

        # Ligne 7: Dealers Bias & VIX
        dealers_bias = ml_data.get('dealers_bias', 0)
        vix = ml_data.get('vix', 0)
        lines.append(f"Dealers Bias: {dealers_bias:+.2f} | VIX: {vix:.1f}")

        # Ligne 8: Context
        session = ml_data.get('session', 'UNKNOWN')
        rel_vol = ml_data.get('relvol_1m5m', 1.0)
        lines.append(f"Session: {session} | RelVol: {rel_vol:.2f}")

        return "\n".join(lines[:10])

    def _fallback_explanation(self, error: str) -> Dict[str, Any]:
        """Explication de fallback en cas d'erreur"""
        return {
            "brief": f"ERROR — {error[:100]}",
            "full": f"**ERROR**\nErreur d'explication: {error}",
            "traffic_light": "🔴",
            "bullish_emoji": "🟡",
            "bullish_score": None,
            "timestamp": datetime.now().isoformat(),
            "explanation_id": f"error_{int(time.time())}"
        }

    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques"""
        return {
            "total_explanations": self.explain_count
        }

# === FACTORY FUNCTION ===

def create_signal_explainer_ml_ready() -> SignalExplainerMLReady:
    """Factory function"""
    return SignalExplainerMLReady()

# === TEST FUNCTION ===

if __name__ == "__main__":
    from dataclasses import dataclass

    @dataclass
    class TestSignal:
        symbol: str
        action: str
        confidence: float
        strategy: str
        entry_price: float
        stop_loss: float
        take_profit: float
        metadata: dict = None

    logger.info("=== TEST SIGNAL EXPLAINER ML_READY ===")

    explainer = create_signal_explainer_ml_ready()

    # Test signal
    signal = TestSignal(
        symbol="ES",
        action="LONG",
        confidence=0.75,
        strategy="hybrid_strategy",
        entry_price=5300.0,
        stop_loss=5295.0,
        take_profit=5310.0,
        metadata={
            "bullish_details": {
                "orderflow_score": 0.5,
                "vwap_score": 0.3,
                "headroom_factor": 0.85
            }
        }
    )

    # Test ML_READY data
    ml_data = {
        "mid": 5300.0,
        "vwap": 5298.5,
        "gex_0": 5300.0,
        "gex_1": 5310.0,
        "gex_2": 5290.0,
        "dealers_bias": 0.15,
        "vix": 18.5,
        "session": "NY_OPEN",
        "relvol_1m5m": 1.35
    }

    # Générer l'explication
    explanation = explainer.explain_signal(
        signal=signal,
        ml_data=ml_data,
        bullish_score=0.62
    )

    logger.info(f"\n{'='*60}")
    logger.info("BRIEF:")
    logger.info(f"{explanation['traffic_light']} {explanation['brief']}")
    logger.info(f"\n{'='*60}")
    logger.info("FULL:")
    logger.info(f"\n{explanation['full']}")
    logger.info(f"\n{'='*60}")
    logger.info(f"Bullish: {explanation['bullish_emoji']} {explanation['bullish_score']}")

    logger.info("✅ Test réussi!")
