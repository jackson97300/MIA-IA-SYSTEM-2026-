#!/usr/bin/env python3
"""
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
DUAL-MODE STRATEGY V2.0 - SEUILS OPTIMISÃ‰S
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Version: 2.0 (09/12/2025)
Changements vs V1:
  - bias_threshold: 0.25 â†’ 0.30 ES / 0.28 NQ (moins de blocages contre-trend)
  - middle_zone: 30-70% â†’ 33-67% ES / 32-68% NQ (zone rÃ©duite)
  - NOUVEAU: override si wall_strength >= 0.75 ES / 0.70 NQ

Impact attendu:
  - PrÃ©cision filtre: 72.7% â†’ 90.9%
  - Gagnants bloquÃ©s: 9 â†’ 1 (-89%)
  - P&L: +$250 vs V1

Emplacement: strategies/dual_mode_strategy.py
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from enum import Enum
from core.logger import get_logger

# ðŸŽ¯ CONFIG CENTRALISÃ‰E - Source unique de vÃ©ritÃ©
from config.trading_params import TRADING_CONFIG, get_config

logger = get_logger(__name__)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ENUMS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MarketMode(Enum):
    """Mode de marchÃ© dÃ©tectÃ©"""
    TREND = "TREND"    # VolatilitÃ© haute OU bias directionnel fort
    RANGE = "RANGE"    # VolatilitÃ© basse ET bias neutre
    UNCLEAR = "UNCLEAR"


class RangeZone(Enum):
    """Zone dans le range"""
    BOTTOM = "BOTTOM"   # 0-33% (ES) / 0-32% (NQ) â†’ LONG autorisÃ©
    MIDDLE = "MIDDLE"   # 33-67% (ES) / 32-68% (NQ) â†’ BLOQUÃ‰
    TOP = "TOP"         # 67-100% (ES) / 68-100% (NQ) â†’ SHORT autorisÃ©
    OUTSIDE = "OUTSIDE"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DATACLASS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

@dataclass
class TradePlan:
    """Plan de trade gÃ©nÃ©rÃ© par DualModeStrategy"""
    allowed: bool = False
    direction: str = ""
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    sl_ticks: float = 0.0
    tp_ticks: float = 0.0
    rr_ratio: float = 0.0
    mode: MarketMode = MarketMode.UNCLEAR
    zone: RangeZone = RangeZone.OUTSIDE
    block_reason: str = ""
    confidence: float = 0.0
    range_info: Optional[Dict] = None
    override_applied: bool = False  # NOUVEAU V2.0: indique si override a Ã©tÃ© appliquÃ©


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# CONFIGURATION V2.0 OPTIMISÃ‰E
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SYMBOL_CONFIG - TP/SL importÃ©s depuis config/trading_params.py
# âš ï¸ MODIFIER trading_params.py pour changer TP/SL!
# Les autres params (bias_threshold, zones, etc.) sont spÃ©cifiques Ã  dual_mode
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _build_symbol_config():
    """Construit SYMBOL_CONFIG en important TP/SL depuis trading_params.py"""
    config = {}

    # ES
    es_cfg = get_config('ES')
    config['ES'] = {
        'tick_size': es_cfg['tick_size'],
        'tick_value': es_cfg['tick_value'],
        'trend_sl_ticks': es_cfg['sl_ticks'],  # ImportÃ© depuis trading_params
        'trend_tp_ticks': es_cfg['tp_ticks'],  # ImportÃ© depuis trading_params
        'range_sl_buffer_ticks': 6,
        'range_tp_pct': 0.60,
        'vol_regime_trend': 1.5,
        'bias_threshold': 0.30,
        'bottom_zone_pct': 33,
        'top_zone_pct': 67,
        'override_threshold': 0.75,
        'min_range_ticks': 20,         # ðŸ”§ CORRIGÃ‰ 12/12: 12 â†’ 20 (min ~5 points)
        'max_range_ticks': 500,        # ðŸ”§ CORRIGÃ‰ 12/12: 50 â†’ 500 (max ~125 points, range journalier normal)
    }

    # NQ - ðŸ”§ CORRIGÃ‰ 11/12/2025: Seuils adaptÃ©s Ã  la volatilitÃ© NQ
    nq_cfg = get_config('NQ')
    config['NQ'] = {
        'tick_size': nq_cfg['tick_size'],
        'tick_value': nq_cfg['tick_value'],
        'trend_sl_ticks': nq_cfg['sl_ticks'],  # ImportÃ© depuis trading_params
        'trend_tp_ticks': nq_cfg['tp_ticks'],  # ImportÃ© depuis trading_params
        'range_sl_buffer_ticks': 8,
        'range_tp_pct': 0.60,
        'vol_regime_trend': 1.5,
        'bias_threshold': 0.40,       # ðŸ”§ CORRIGÃ‰: 0.28 â†’ 0.40 (moins de blocages contre-trend)
        'bottom_zone_pct': 32,
        'top_zone_pct': 68,
        'override_threshold': 0.65,   # ðŸ”§ CORRIGÃ‰: 0.70 â†’ 0.65 (plus de trades haute confiance)
        'min_range_ticks': 30,        # ðŸ”§ CORRIGÃ‰: 15 â†’ 30 (NQ plus volatile)
        'max_range_ticks': 800,       # ðŸ”§ CORRIGÃ‰ 12/12: 150 â†’ 800 (NQ range journalier peut Ãªtre 200+ pts = 800t)
    }

    # RTY
    rty_cfg = get_config('RTY')
    config['RTY'] = {
        'tick_size': rty_cfg['tick_size'],
        'tick_value': rty_cfg['tick_value'],
        'trend_sl_ticks': rty_cfg['sl_ticks'],  # ImportÃ© depuis trading_params
        'trend_tp_ticks': rty_cfg['tp_ticks'],  # ImportÃ© depuis trading_params
        'range_sl_buffer_ticks': 10,
        'range_tp_pct': 0.60,
        'vol_regime_trend': 1.5,
        'bias_threshold': 0.30,
        'bottom_zone_pct': 33,
        'top_zone_pct': 67,
        'override_threshold': 0.70,
        'min_range_ticks': 20,
        'max_range_ticks': 400,       # ðŸ”§ CORRIGÃ‰ 12/12: 80 â†’ 400 (RTY range journalier ~40 pts = 400t)
    }

    return config

# Construire la config au chargement du module
SYMBOL_CONFIG = _build_symbol_config()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DUAL-MODE STRATEGY CLASS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class DualModeStrategy:
    """
    StratÃ©gie DUAL-MODE V2.0: Adapte le trading selon TREND vs RANGE

    MODE TREND (vol > 1.5 OU |bias| > threshold):
        - SL/TP fixes (R:R 2:1)
        - Bloque les trades contre le bias (sauf override)

    MODE RANGE (vol <= 1.5 ET |bias| < threshold):
        - SL/TP adaptatifs au range
        - FADE: LONG en BOTTOM, SHORT en TOP
        - BLOQUE la zone MIDDLE (sauf override)

    Version 2.0: Ajoute override si wall_strength >= threshold
    """

    def __init__(self, custom_config: Optional[Dict] = None):
        """
        Initialise la stratÃ©gie

        Args:
            custom_config: Configuration personnalisÃ©e (optionnel)
        """
        self.config = SYMBOL_CONFIG.copy()

        if custom_config:
            for symbol, params in custom_config.items():
                if symbol in self.config:
                    self.config[symbol].update(params)

        # Statistiques
        self.stats = {
            'total_signals': 0,
            'trend_signals': 0,
            'range_signals': 0,
            'blocked_middle': 0,
            'blocked_counter_trend': 0,
            'blocked_counter_bias': 0,
            'override_applied': 0,  # ðŸ”´ NOUVEAU V2.0
        }

        logger.info("=" * 60)
        logger.info("DualModeStrategy V2.0 initialisÃ©")
        logger.info("=" * 60)
        logger.info("   MODE TREND: SL fixe, TP fixe, R:R 2:1, AVEC le trend")
        logger.info("   MODE RANGE: SL hors bracket, TP 60% range, FADE extrÃªmes")
        logger.info("   ðŸ”´ V2.0: Override si wall_strength >= threshold")
        logger.info(f"   ES: bias={self.config['ES']['bias_threshold']}, zones={self.config['ES']['bottom_zone_pct']}-{self.config['ES']['top_zone_pct']}%, override={self.config['ES']['override_threshold']}")
        logger.info(f"   NQ: bias={self.config['NQ']['bias_threshold']}, zones={self.config['NQ']['bottom_zone_pct']}-{self.config['NQ']['top_zone_pct']}%, override={self.config['NQ']['override_threshold']}")
        logger.info("=" * 60)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # DÃ‰TECTION DE MODE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def detect_market_mode(self, snapshot: Dict, symbol: str) -> Tuple[MarketMode, str]:
        """
        DÃ©tecte si le marchÃ© est en TREND ou RANGE

        TREND si:
            - volatility_regime > 1.5 (vol haute)
            - OU |mia_bullish_score| > bias_threshold (directionnel)

        RANGE si:
            - volatility_regime <= 1.5 (vol basse)
            - ET |mia_bullish_score| < bias_threshold (neutre)

        Returns:
            (MarketMode, reason)
        """
        cfg = self.config.get(symbol, self.config['ES'])

        vol_regime = snapshot.get('volatility_regime', 1.0) or 1.0
        mia_score = snapshot.get('mia_bullish_score', 0) or 0

        is_high_vol = vol_regime > cfg['vol_regime_trend']
        is_directional = abs(mia_score) > cfg['bias_threshold']

        if is_high_vol:
            return MarketMode.TREND, f"Vol haute ({vol_regime:.1f} > {cfg['vol_regime_trend']})"
        elif is_directional:
            bias = "BULLISH" if mia_score > 0 else "BEARISH"
            return MarketMode.TREND, f"Bias fort {bias} ({mia_score:.2f})"
        else:
            return MarketMode.RANGE, f"Vol basse ({vol_regime:.1f}) + Bias neutre ({mia_score:.2f})"

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # DÃ‰TECTION DE ZONE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def detect_range_zone(self, snapshot: Dict, symbol: str) -> Tuple[bool, RangeZone, Dict]:
        """
        DÃ©tecte la zone dans le range (BOTTOM/MIDDLE/TOP)

        Utilise:
            1. structure.ibh/ibl (Initial Balance) si disponible
            2. Sinon 1d_max/1d_min (range du jour)
            3. Sinon position_in_range directement

        Returns:
            (is_valid_range, zone, range_info)
        """
        cfg = self.config.get(symbol, self.config['ES'])
        tick_size = cfg['tick_size']

        mid = snapshot.get('mid', 0)
        if not mid:
            return False, RangeZone.OUTSIDE, {}

        # Source 1: Initial Balance (BRACKET) - Prioritaire
        structure = snapshot.get('structure', {})
        ibh = structure.get('ibh') if structure else None
        ibl = structure.get('ibl') if structure else None
        using_bracket = bool(ibh and ibl and ibh > ibl)

        # Source 2: Day range (FALLBACK - pas de validation de taille!)
        if not using_bracket:
            ibh = snapshot.get('1d_max', 0)
            ibl = snapshot.get('1d_min', 0)

        # Source 3: Position in range directe
        position_pct = snapshot.get('position_in_range', 50) or 50

        # Calculer si on a des bornes valides
        if ibh and ibl and ibh > ibl:
            range_ticks = (ibh - ibl) / tick_size

            # ðŸ”§ FIX 12/12/2025: Valider SEULEMENT si bracket (IBH/IBL)
            # Le range journalier (1d_max/1d_min) ne doit PAS Ãªtre validÃ© avec min/max
            # Car le range journalier peut faire 100+ points = normal!
            if using_bracket:
                if range_ticks < cfg['min_range_ticks'] or range_ticks > cfg['max_range_ticks']:
                    return False, RangeZone.OUTSIDE, {
                        'reason': f"Bracket invalide ({range_ticks:.0f}t, requis: {cfg['min_range_ticks']}-{cfg['max_range_ticks']})"
                    }

            # Calculer la position
            position_pct = ((mid - ibl) / (ibh - ibl)) * 100
            position_pct = max(0, min(100, position_pct))
        else:
            range_ticks = 0

        # DÃ©terminer la zone
        if position_pct < cfg['bottom_zone_pct']:
            zone = RangeZone.BOTTOM
        elif position_pct > cfg['top_zone_pct']:
            zone = RangeZone.TOP
        else:
            zone = RangeZone.MIDDLE

        range_info = {
            'ibh': ibh,
            'ibl': ibl,
            'range_ticks': range_ticks,
            'position_pct': position_pct,
            'midpoint': (ibh + ibl) / 2 if ibh and ibl else mid,
            'zone': zone.value,
        }

        return True, zone, range_info

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # CHECK OVERRIDE (NOUVEAU V2.0)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def should_override(self, snapshot: Dict, symbol: str, ml_confidence: float = 0.0) -> Tuple[bool, str]:
        """
        ðŸ”´ V2.1 (11/12/2025): Override amÃ©liorÃ© avec confiance ML

        Override si:
            - wall_strength >= override_threshold
            - OU ml_confidence >= 1.2 (trÃ¨s haute confiance)

        Cela permet de laisser passer les signaux trÃ¨s forts mÃªme si
        ils sont contre-trend ou dans la zone MIDDLE.

        Returns:
            (should_override, reason)
        """
        cfg = self.config.get(symbol, self.config['ES'])

        # ðŸ”§ NOUVEAU V2.1: Override si ML confidence trÃ¨s haute
        if ml_confidence >= 1.2:
            return True, f"ML confidence trÃ¨s haute ({ml_confidence:.2f} >= 1.2)"

        next_wall = snapshot.get('next_wall', {})
        if not next_wall or not isinstance(next_wall, dict):
            return False, ""

        wall_strength = next_wall.get('strength', 0) or 0

        if wall_strength >= cfg['override_threshold']:
            return True, f"Wall strength fort ({wall_strength:.2f} >= {cfg['override_threshold']})"

        return False, ""

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # GÃ‰NÃ‰RATION DU PLAN DE TRADE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def generate_trade_plan(self, snapshot: Dict, symbol: str,
                           signal_direction: str, ml_confidence: float = 0.0) -> TradePlan:
        """
        GÃ©nÃ¨re un plan de trade adaptÃ© au mode de marchÃ©

        Args:
            snapshot: Snapshot de marchÃ© complet
            symbol: 'ES', 'NQ', 'RTY'
            signal_direction: 'LONG' ou 'SHORT' (du signal ML)
            ml_confidence: Confiance ML du signal (pour override si >= 1.2)

        Returns:
            TradePlan avec allowed=True/False et SL/TP adaptÃ©s
        """
        self.stats['total_signals'] += 1

        cfg = self.config.get(symbol, self.config['ES'])
        mid = snapshot.get('mid', 0)

        if not mid:
            return TradePlan(allowed=False, block_reason="Pas de prix mid")

        # DÃ©tecter le mode
        mode, mode_reason = self.detect_market_mode(snapshot, symbol)
        logger.info(f"ðŸ“Š [{symbol}] Mode dÃ©tectÃ©: {mode.value} ({mode_reason})")

        # ðŸ”´ V2.1: VÃ©rifier l'override (avec ML confidence)
        override, override_reason = self.should_override(snapshot, symbol, ml_confidence)

        if mode == MarketMode.TREND:
            return self._generate_trend_plan(snapshot, symbol, signal_direction,
                                            cfg, mid, mode_reason, override, override_reason)
        else:
            return self._generate_range_plan(snapshot, symbol, signal_direction,
                                            cfg, mid, mode_reason, override, override_reason)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PLAN TREND
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _generate_trend_plan(self, snapshot: Dict, symbol: str, direction: str,
                             cfg: Dict, mid: float, mode_reason: str,
                             override: bool, override_reason: str) -> TradePlan:
        """
        GÃ©nÃ¨re un plan pour MODE TREND

        - SL/TP fixes (R:R 2:1)
        - Bloque contre-trend (sauf override)
        - ðŸ”¥ FIX 12/12: Bloque SHORT en bas du range / LONG en haut
        """
        self.stats['trend_signals'] += 1

        tick_size = cfg['tick_size']
        mia_score = snapshot.get('mia_bullish_score', 0) or 0

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # ðŸ”¥ FIX 12/12: BLOQUER TRADES CONTRE-ZONE (mÃªme en TREND)
        # SHORT en bas du range = PUNITIF (pas de place pour descendre)
        # LONG en haut du range = PUNITIF (pas de place pour monter)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        is_valid, zone, range_info = self.detect_range_zone(snapshot, symbol)
        if is_valid:
            position_pct = range_info.get('position_pct', 50)

            # SHORT en bas du range (< 35%) = BLOQUÃ‰ SAUF si tendance baissiÃ¨re
            # ðŸ”§ FIX 13/12/2025: Ne pas bloquer SHORT en BAS si bias BEARISH (suivre la tendance)
            if direction == "SHORT" and zone == RangeZone.BOTTOM:
                # Si tendance baissiÃ¨re forte, AUTORISER le SHORT (suivre la tendance)
                if mia_score < -0.30:  # Bias bearish significatif
                    logger.info(f"âœ… [{symbol}] SHORT en BAS autorisÃ© (tendance BEARISH {mia_score:.2f})")
                elif not override:
                    self.stats['blocked_short_at_bottom'] = self.stats.get('blocked_short_at_bottom', 0) + 1
                    logger.warning(f"ðŸš« [{symbol}] SHORT en BAS du range ({position_pct:.0f}%) - BLOQUÃ‰ (bias neutre)")
                    return TradePlan(
                        allowed=False,
                        direction=direction,
                        entry=mid,
                        mode=MarketMode.TREND,
                        zone=zone,
                        block_reason=f"SHORT interdit en BAS ({position_pct:.0f}%) - Attendre rebond ou cassure",
                        range_info=range_info
                    )
                else:
                    logger.info(f"âš¡ OVERRIDE: SHORT autorisÃ© en BAS - {override_reason}")

            # LONG en haut du range (> 65%) = BLOQUÃ‰ SAUF si tendance haussiÃ¨re
            # ðŸ”§ FIX 13/12/2025: Ne pas bloquer LONG en HAUT si bias BULLISH (suivre la tendance)
            if direction == "LONG" and zone == RangeZone.TOP:
                # Si tendance haussiÃ¨re forte, AUTORISER le LONG (suivre la tendance)
                if mia_score > 0.30:  # Bias bullish significatif
                    logger.info(f"âœ… [{symbol}] LONG en HAUT autorisÃ© (tendance BULLISH {mia_score:.2f})")
                elif not override:
                    self.stats['blocked_long_at_top'] = self.stats.get('blocked_long_at_top', 0) + 1
                    logger.warning(f"ðŸš« [{symbol}] LONG en HAUT du range ({position_pct:.0f}%) - BLOQUÃ‰ (bias neutre)")
                    return TradePlan(
                        allowed=False,
                        direction=direction,
                        entry=mid,
                        mode=MarketMode.TREND,
                        zone=zone,
                        block_reason=f"LONG interdit en HAUT ({position_pct:.0f}%) - Attendre rejet ou cassure",
                        range_info=range_info
                    )
                else:
                    logger.info(f"âš¡ OVERRIDE: LONG autorisÃ© en HAUT - {override_reason}")

        trend_bullish = mia_score > 0
        trend_bearish = mia_score < 0

        # VÃ©rifier contre-trend
        if direction == "LONG" and trend_bearish and abs(mia_score) > cfg['bias_threshold']:
            # ðŸ”´ V2.0: VÃ©rifier override
            if not override:
                self.stats['blocked_counter_trend'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.TREND,
                    block_reason=f"TREND: LONG contre bias BEARISH ({mia_score:.2f})"
                )
            else:
                self.stats['override_applied'] += 1
                logger.info(f"âš¡ OVERRIDE: LONG autorisÃ© malgrÃ© bias BEARISH - {override_reason}")

        if direction == "SHORT" and trend_bullish and abs(mia_score) > cfg['bias_threshold']:
            if not override:
                self.stats['blocked_counter_trend'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.TREND,
                    block_reason=f"TREND: SHORT contre bias BULLISH ({mia_score:.2f})"
                )
            else:
                self.stats['override_applied'] += 1
                logger.info(f"âš¡ OVERRIDE: SHORT autorisÃ© malgrÃ© bias BULLISH - {override_reason}")

        # Calculer SL/TP fixes
        sl_ticks = cfg['trend_sl_ticks']
        tp_ticks = cfg['trend_tp_ticks']

        if direction == "LONG":
            sl = mid - (sl_ticks * tick_size)
            tp = mid + (tp_ticks * tick_size)
        else:
            sl = mid + (sl_ticks * tick_size)
            tp = mid - (tp_ticks * tick_size)

        rr_ratio = tp_ticks / sl_ticks

        # Confiance basÃ©e sur l'alignement
        if (direction == "LONG" and trend_bullish) or (direction == "SHORT" and trend_bearish):
            confidence = 0.7 + (abs(mia_score) * 0.3)
        else:
            confidence = 0.5

        logger.info(f"ðŸ“ˆ [{symbol}] TREND PLAN: {direction}")
        logger.info(f"   Reason: {mode_reason}")
        logger.info(f"   Entry: {mid:.2f} | SL: {sl:.2f} ({sl_ticks}t) | TP: {tp:.2f} ({tp_ticks}t)")
        logger.info(f"   R:R = {rr_ratio:.1f}:1")
        if override:
            logger.info(f"   âš¡ OVERRIDE APPLIED: {override_reason}")

        return TradePlan(
            allowed=True,
            direction=direction,
            entry=mid,
            sl=sl,
            tp=tp,
            sl_ticks=sl_ticks,
            tp_ticks=tp_ticks,
            rr_ratio=rr_ratio,
            mode=MarketMode.TREND,
            confidence=min(1.0, confidence),
            override_applied=override
        )

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PLAN RANGE
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _generate_range_plan(self, snapshot: Dict, symbol: str, direction: str,
                             cfg: Dict, mid: float, mode_reason: str,
                             override: bool, override_reason: str) -> TradePlan:
        """
        GÃ©nÃ¨re un plan pour MODE RANGE

        - FADE: LONG en BOTTOM, SHORT en TOP
        - BLOQUE MIDDLE (sauf override)
        - SL hors du range, TP 60% du range
        """
        self.stats['range_signals'] += 1

        tick_size = cfg['tick_size']
        mia_score = snapshot.get('mia_bullish_score', 0) or 0

        # DÃ©tecter la zone
        is_range, zone, range_info = self.detect_range_zone(snapshot, symbol)

        if not is_range:
            reason = range_info.get('reason', 'Pas de bracket valide')
            return TradePlan(
                allowed=False,
                mode=MarketMode.RANGE,
                block_reason=f"RANGE: {reason}"
            )

        ibh = range_info.get('ibh', 0)
        ibl = range_info.get('ibl', 0)
        position_pct = range_info.get('position_pct', 50)

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # ZONE MIDDLE = BLOQUÃ‰ (sauf override)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        if zone == RangeZone.MIDDLE:
            if not override:
                self.stats['blocked_middle'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.RANGE,
                    zone=zone,
                    block_reason=f"RANGE MIDDLE ({position_pct:.0f}%) - Attendre extrÃªme",
                    range_info=range_info
                )
            else:
                self.stats['override_applied'] += 1
                logger.info(f"âš¡ OVERRIDE: Trade autorisÃ© en MIDDLE - {override_reason}")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # ZONE BOTTOM = LONG seulement (FADE)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        if zone == RangeZone.BOTTOM:
            if direction == "SHORT":
                self.stats['blocked_counter_bias'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.RANGE,
                    zone=zone,
                    block_reason=f"RANGE BOTTOM ({position_pct:.0f}%): SHORT interdit, FADE = LONG",
                    range_info=range_info
                )

            # VÃ©rifier le bias
            if mia_score < -cfg['bias_threshold']:
                self.stats['blocked_counter_bias'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.RANGE,
                    zone=zone,
                    block_reason=f"RANGE BOTTOM: LONG interdit (bias BEARISH {mia_score:.2f})",
                    range_info=range_info
                )

            # SL/TP pour LONG en BOTTOM
            sl = ibl - (cfg['range_sl_buffer_ticks'] * tick_size)
            range_size = ibh - ibl
            tp = ibl + (range_size * cfg['range_tp_pct'])
            final_direction = "LONG"

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # ZONE TOP = SHORT seulement (FADE)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        elif zone == RangeZone.TOP:
            if direction == "LONG":
                self.stats['blocked_counter_bias'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.RANGE,
                    zone=zone,
                    block_reason=f"RANGE TOP ({position_pct:.0f}%): LONG interdit, FADE = SHORT",
                    range_info=range_info
                )

            if mia_score > cfg['bias_threshold']:
                self.stats['blocked_counter_bias'] += 1
                return TradePlan(
                    allowed=False,
                    direction=direction,
                    entry=mid,
                    mode=MarketMode.RANGE,
                    zone=zone,
                    block_reason=f"RANGE TOP: SHORT interdit (bias BULLISH {mia_score:.2f})",
                    range_info=range_info
                )

            sl = ibh + (cfg['range_sl_buffer_ticks'] * tick_size)
            range_size = ibh - ibl
            tp = ibh - (range_size * cfg['range_tp_pct'])
            final_direction = "SHORT"

        # Zone MIDDLE avec override
        elif zone == RangeZone.MIDDLE and override:
            # Utiliser SL/TP fixes comme en TREND
            sl_ticks = cfg['trend_sl_ticks']
            tp_ticks = cfg['trend_tp_ticks']
            if direction == "LONG":
                sl = mid - (sl_ticks * tick_size)
                tp = mid + (tp_ticks * tick_size)
            else:
                sl = mid + (sl_ticks * tick_size)
                tp = mid - (tp_ticks * tick_size)
            final_direction = direction

        else:
            return TradePlan(
                allowed=False,
                mode=MarketMode.RANGE,
                zone=zone,
                block_reason="RANGE: Zone invalide"
            )

        # Calculer les ticks et ratio
        sl_ticks = abs(mid - sl) / tick_size
        tp_ticks = abs(tp - mid) / tick_size
        rr_ratio = tp_ticks / sl_ticks if sl_ticks > 0 else 0

        logger.info(f"ðŸ”„ [{symbol}] RANGE PLAN: {final_direction}")
        logger.info(f"   Reason: {mode_reason}")
        logger.info(f"   Bracket: {ibl:.2f} - {ibh:.2f} ({range_info.get('range_ticks', 0):.0f}t)")
        logger.info(f"   Zone: {zone.value} ({position_pct:.0f}%)")
        logger.info(f"   Entry: {mid:.2f} | SL: {sl:.2f} ({sl_ticks:.0f}t) | TP: {tp:.2f} ({tp_ticks:.0f}t)")
        logger.info(f"   R:R = {rr_ratio:.1f}:1")
        if override:
            logger.info(f"   âš¡ OVERRIDE APPLIED: {override_reason}")

        return TradePlan(
            allowed=True,
            direction=final_direction,
            entry=mid,
            sl=sl,
            tp=tp,
            sl_ticks=sl_ticks,
            tp_ticks=tp_ticks,
            rr_ratio=rr_ratio,
            mode=MarketMode.RANGE,
            zone=zone,
            confidence=0.6,
            range_info=range_info,
            override_applied=override
        )

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # UTILITAIRES
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return self.stats.copy()

    def reset_stats(self):
        """RÃ©initialise les statistiques"""
        for key in self.stats:
            self.stats[key] = 0

    def get_config(self, symbol: str) -> Dict:
        """Retourne la configuration pour un symbole"""
        return self.config.get(symbol, self.config['ES']).copy()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TEST STANDALONE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

if __name__ == "__main__":
    # Test rapide
    strategy = DualModeStrategy()

    print("â•" * 60)
    print("TEST DUAL-MODE STRATEGY V2.0")
    print("â•" * 60)

    # Test 1: MODE TREND avec override
    snapshot = {
        'mid': 6080.00,
        'volatility_regime': 2.0,
        'mia_bullish_score': -0.40,  # BEARISH fort
        'next_wall': {'strength': 0.80, 'side': 'put', 'dist_ticks': 5},
    }
    plan = strategy.generate_trade_plan(snapshot, 'ES', 'LONG')
    print(f"\nTest 1 - TREND + LONG vs BEARISH + wall_strength=0.80:")
    print(f"  Allowed: {plan.allowed}")
    print(f"  Override: {plan.override_applied}")
    print(f"  Reason: {plan.block_reason}")

    # Test 2: MODE RANGE MIDDLE avec override
    snapshot = {
        'mid': 6085.00,
        'volatility_regime': 1.0,
        'mia_bullish_score': 0.10,
        'position_in_range': 50,
        '1d_max': 6090.00,
        '1d_min': 6080.00,
        'next_wall': {'strength': 0.80, 'side': 'put', 'dist_ticks': 5},
    }
    plan = strategy.generate_trade_plan(snapshot, 'ES', 'LONG')
    print(f"\nTest 2 - RANGE MIDDLE + wall_strength=0.80:")
    print(f"  Allowed: {plan.allowed}")
    print(f"  Override: {plan.override_applied}")
    print(f"  Reason: {plan.block_reason}")

    # Test 3: MODE RANGE MIDDLE sans override
    snapshot['next_wall']['strength'] = 0.50
    plan = strategy.generate_trade_plan(snapshot, 'ES', 'LONG')
    print(f"\nTest 3 - RANGE MIDDLE + wall_strength=0.50:")
    print(f"  Allowed: {plan.allowed}")
    print(f"  Override: {plan.override_applied}")
    print(f"  Reason: {plan.block_reason}")

    print(f"\nðŸ“Š Stats: {strategy.get_stats()}")
