#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Intraday Bracket Detector
=========================================
PRIORITÉ ABSOLUE - Détection des brackets/consolidations INTRADAY

PROBLÈME RÉSOLU:
- Le bot prenait des trades au MILIEU des brackets
- Le détecteur actuel regarde le range 1D (trop large)
- Ce module détecte les consolidations COURTES (10-60 min)

CRITÈRES DE DÉTECTION:
1. Taille: 12-50 ticks (pas micro, pas trop large)
2. Structure: utilise IBH/IBL ou high/low des N dernières barres
3. Position: calcule où le prix est dans le range
4. Bloque: trades au MILIEU (35-65%)

ZONES (conservatrices):
- BOTTOM (0-30%): LONG autorisé si bias pas BEARISH
- MIDDLE (30-70%): ❌ AUCUN TRADE - Zone élargie pour sécurité
- TOP (70-100%): SHORT autorisé si bias pas BULLISH

Version: 1.0.0 - 09/12/2025
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from core.logger import get_logger

logger = get_logger(__name__)


class BracketZone(Enum):
    """Zones du bracket"""
    BOTTOM = "BOTTOM"      # 0-35% - LONG zone
    MIDDLE = "MIDDLE"      # 35-65% - NO TRADE zone
    TOP = "TOP"            # 65-100% - SHORT zone
    OUTSIDE = "OUTSIDE"    # Hors du bracket


@dataclass
class BracketDetectionResult:
    """Résultat de la détection de bracket"""
    # Détection
    is_bracket: bool = False
    confidence: float = 0.0

    # Niveaux
    high: float = 0.0
    low: float = 0.0
    midpoint: float = 0.0
    range_ticks: float = 0.0

    # Position actuelle
    current_price: float = 0.0
    position_pct: float = 50.0
    zone: BracketZone = BracketZone.MIDDLE

    # Trading decision
    allow_long: bool = True
    allow_short: bool = True
    block_reason: str = ""

    # Contexte
    bias: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    source: str = ""  # "IBH_IBL", "RECENT_BARS", "SNAPSHOT"


class IntradayBracketDetector:
    """
    Détecteur de brackets intraday optimisé pour MIA

    Utilise plusieurs sources de données:
    1. structure.ibh/ibl (Initial Balance)
    2. high/low des dernières barres
    3. Données du snapshot (volatility_regime, mia_bullish_score)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Configuration par symbole
        # 🔴 09/12: Zones CONSERVATRICES pour éviter faux breakouts
        # MIDDLE élargi à 30-70% = plus de protection
        self.symbol_config = {
            'ES': {
                'tick_size': 0.25,
                'min_range_ticks': 12,
                'max_range_ticks': 120,  # 🔧 FIX 09/12: 50→120 pour capter IBH/IBL larges
                'bottom_zone_pct': 30,  # 0-30% = BOTTOM (proche support)
                'top_zone_pct': 70,     # 70-100% = TOP (proche résistance)
                'vol_regime_max': 1.5,  # Max volatility pour bracket
            },
            'NQ': {
                'tick_size': 0.25,
                'min_range_ticks': 15,
                'max_range_ticks': 500,  # 🔧 FIX 09/12: 60→500 pour NQ (ranges plus larges)
                'bottom_zone_pct': 30,
                'top_zone_pct': 70,
                'vol_regime_max': 1.5,
            },
            'RTY': {
                'tick_size': 0.10,
                'min_range_ticks': 20,
                'max_range_ticks': 80,
                'bottom_zone_pct': 30,
                'top_zone_pct': 70,
                'vol_regime_max': 1.5,
            }
        }

        # Statistiques
        self.stats = {
            'brackets_detected': 0,
            'trades_blocked_middle': 0,
            'trades_allowed_fade': 0,
        }

        logger.info("IntradayBracketDetector initialisé (CONSERVATEUR)")
        logger.info(f"   Zones: BOTTOM <30% | MIDDLE 30-70% | TOP >70%")

    def detect_from_snapshot(self, snapshot: Dict, symbol: str) -> BracketDetectionResult:
        """
        Détection de bracket depuis un snapshot MIA

        MÉTHODE PRINCIPALE - Utilise toutes les données disponibles
        """
        config = self.symbol_config.get(symbol, self.symbol_config['ES'])
        tick_size = config['tick_size']

        # Prix actuel
        mid_price = snapshot.get('mid', 0)
        if not mid_price:
            mid_price = (snapshot.get('best_bid', 0) + snapshot.get('best_ask', 0)) / 2

        if not mid_price:
            return BracketDetectionResult(is_bracket=False, block_reason="Pas de prix")

        # === SOURCE 1: Initial Balance (structure.ibh/ibl) ===
        structure = snapshot.get('structure', {})
        ibh = structure.get('ibh', 0)
        ibl = structure.get('ibl', 0)

        # === SOURCE 2: High/Low récents (si disponible) ===
        recent_high = snapshot.get('high', 0)
        recent_low = snapshot.get('low', 0)

        # === DÉTERMINER LES NIVEAUX DU BRACKET ===
        bracket_high = 0
        bracket_low = 0
        source = ""

        # Priorité: IBH/IBL si valides
        if ibh and ibl and ibh > ibl:
            ib_range = (ibh - ibl) / tick_size
            if config['min_range_ticks'] <= ib_range <= config['max_range_ticks']:
                bracket_high = ibh
                bracket_low = ibl
                source = "IBH_IBL"

        # Fallback: recent high/low
        if not bracket_high and recent_high and recent_low and recent_high > recent_low:
            rl_range = (recent_high - recent_low) / tick_size
            if config['min_range_ticks'] <= rl_range <= config['max_range_ticks']:
                bracket_high = recent_high
                bracket_low = recent_low
                source = "RECENT_BARS"

        # Pas de bracket détecté
        if not bracket_high or not bracket_low:
            return BracketDetectionResult(
                is_bracket=False,
                current_price=mid_price,
                block_reason="Pas de bracket valide détecté"
            )

        # === CALCULS ===
        range_ticks = (bracket_high - bracket_low) / tick_size
        midpoint = (bracket_high + bracket_low) / 2

        # Position dans le range (0-100%)
        if bracket_high != bracket_low:
            position_pct = ((mid_price - bracket_low) / (bracket_high - bracket_low)) * 100
        else:
            position_pct = 50.0

        # Limiter à 0-100%
        position_pct = max(0, min(100, position_pct))

        # === DÉTERMINER LA ZONE ===
        if position_pct < config['bottom_zone_pct']:
            zone = BracketZone.BOTTOM
        elif position_pct > config['top_zone_pct']:
            zone = BracketZone.TOP
        else:
            zone = BracketZone.MIDDLE

        # === VÉRIFIER VOLATILITÉ ===
        vol_regime = snapshot.get('volatility_regime', 2)
        is_low_vol = vol_regime <= config['vol_regime_max'] if vol_regime else True

        # Si volatilité trop haute, pas de bracket
        if not is_low_vol:
            return BracketDetectionResult(
                is_bracket=False,
                current_price=mid_price,
                high=bracket_high,
                low=bracket_low,
                range_ticks=range_ticks,
                position_pct=position_pct,
                zone=zone,
                block_reason=f"Volatilité trop haute ({vol_regime})"
            )

        # === DÉTERMINER LE BIAS ===
        mia_score = snapshot.get('mia_bullish_score', 0)
        if mia_score and mia_score > 0.25:
            bias = "BULLISH"
        elif mia_score and mia_score < -0.25:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        # === DÉCISION DE TRADING ===
        allow_long = True
        allow_short = True
        block_reason = ""

        # RÈGLE PRINCIPALE: BLOQUER AU MILIEU!
        if zone == BracketZone.MIDDLE:
            allow_long = False
            allow_short = False
            block_reason = f"MILIEU du bracket ({position_pct:.0f}%) - Attendre extrême"
            self.stats['trades_blocked_middle'] += 1

        # RÈGLES FADE
        elif zone == BracketZone.BOTTOM:
            # En bas: LONG autorisé sauf si BEARISH fort
            if bias == "BEARISH":
                allow_long = False
                block_reason = f"BAS du range mais bias BEARISH"
            else:
                allow_short = False  # Pas de SHORT en bas
                self.stats['trades_allowed_fade'] += 1

        elif zone == BracketZone.TOP:
            # En haut: SHORT autorisé sauf si BULLISH fort
            if bias == "BULLISH":
                allow_short = False
                block_reason = f"HAUT du range mais bias BULLISH"
            else:
                allow_long = False  # Pas de LONG en haut
                self.stats['trades_allowed_fade'] += 1

        self.stats['brackets_detected'] += 1

        # Log
        logger.info(f"📊 [{symbol}] BRACKET DÉTECTÉ ({source}):")
        logger.info(f"   Range: {bracket_low:.2f} - {bracket_high:.2f} ({range_ticks:.0f}t)")
        logger.info(f"   Prix: {mid_price:.2f} | Position: {position_pct:.0f}% | Zone: {zone.value}")
        logger.info(f"   Bias: {bias} | Vol: {vol_regime}")
        logger.info(f"   LONG: {'✅' if allow_long else '❌'} | SHORT: {'✅' if allow_short else '❌'}")
        if block_reason:
            logger.warning(f"   ⚠️ {block_reason}")

        return BracketDetectionResult(
            is_bracket=True,
            confidence=0.7 + (0.1 if source == "IBH_IBL" else 0),
            high=bracket_high,
            low=bracket_low,
            midpoint=midpoint,
            range_ticks=range_ticks,
            current_price=mid_price,
            position_pct=position_pct,
            zone=zone,
            allow_long=allow_long,
            allow_short=allow_short,
            block_reason=block_reason,
            bias=bias,
            source=source
        )

    def should_block_trade(self, snapshot: Dict, symbol: str, direction: str) -> Tuple[bool, str]:
        """
        Méthode simplifiée: le trade doit-il être bloqué?

        Returns:
            (should_block, reason)
        """
        # 🔧 13/12: DÉSACTIVÉ - Ce filtre bloquait 265 trades!
        # Le blocage en zone TOP/BOTTOM était trop strict
        # TODO: Réactiver seulement en RANGE confirmé avec range > 30 ticks
        result = self.detect_from_snapshot(snapshot, symbol)

        # Log informatif seulement (pas de blocage)
        logger.info(f"ℹ️ [{symbol}] BRACKET INFO: is_bracket={result.is_bracket}, "
                   f"zone={result.zone.value if result.is_bracket else 'N/A'}, "
                   f"position={result.position_pct:.1f}%, range={result.range_ticks:.0f}t "
                   f"(non bloquant)")

        # Toujours autoriser le trade (filtre désactivé)
        return False, f"Bracket check désactivé - zone={result.zone.value if result.is_bracket else 'N/A'}"

    def get_statistics(self) -> Dict:
        """Retourne les statistiques"""
        return self.stats.copy()


# === TEST ===
if __name__ == "__main__":
    print("=" * 70)
    print("TEST INTRADAY BRACKET DETECTOR")
    print("=" * 70)

    detector = IntradayBracketDetector()

    # Test avec le snapshot du trade perdant
    test_snapshot = {
        'mid': 6860.38,  # Entry price
        'best_bid': 6860.25,
        'best_ask': 6860.50,
        'structure': {
            'ibh': 6865.00,  # High du bracket
            'ibl': 6854.00,  # Low du bracket
        },
        'high': 6865.50,
        'low': 6852.00,
        'volatility_regime': 1.0,
        'mia_bullish_score': -0.63,  # BEARISH
    }

    print("\n--- TEST TRADE ES LONG @ 6860.38 ---")
    result = detector.detect_from_snapshot(test_snapshot, "ES")

    print(f"\nRésultat:")
    print(f"  Bracket détecté: {result.is_bracket}")
    print(f"  Range: {result.low:.2f} - {result.high:.2f} ({result.range_ticks:.0f}t)")
    print(f"  Position: {result.position_pct:.0f}%")
    print(f"  Zone: {result.zone.value}")
    print(f"  LONG autorisé: {result.allow_long}")
    print(f"  SHORT autorisé: {result.allow_short}")
    print(f"  Raison blocage: {result.block_reason}")

    # Test should_block_trade
    print("\n--- TEST should_block_trade ---")
    should_block, reason = detector.should_block_trade(test_snapshot, "ES", "LONG")
    print(f"LONG bloqué: {should_block}")
    print(f"Raison: {reason}")

    should_block, reason = detector.should_block_trade(test_snapshot, "ES", "SHORT")
    print(f"SHORT bloqué: {should_block}")
    print(f"Raison: {reason}")

    # Test en bas du range
    print("\n--- TEST EN BAS DU RANGE ---")
    test_snapshot_bottom = test_snapshot.copy()
    test_snapshot_bottom['mid'] = 6855.00  # 25% du range
    test_snapshot_bottom['mia_bullish_score'] = 0.1  # Légèrement bullish

    result_bottom = detector.detect_from_snapshot(test_snapshot_bottom, "ES")
    print(f"Position: {result_bottom.position_pct:.0f}% | Zone: {result_bottom.zone.value}")
    print(f"LONG autorisé: {result_bottom.allow_long}")

    # Statistiques
    print("\n--- STATISTIQUES ---")
    print(detector.get_statistics())
