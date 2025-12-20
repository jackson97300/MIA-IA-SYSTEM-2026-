"""
🎯 ES MENTHORQ MAGNET V4.0 OPTIMIZED - DATA-DRIVEN STRATEGY
===========================================================
Version optimisée basée sur backtest 17 jours (136 trades)

OPTIMISATIONS APPLIQUÉES:
✅ TP augmenté: 12t → 18t (améliorer ratio gain/perte)
✅ SL réduit: 16t → 12t (limiter pertes)
✅ Filtrage GEX_1 et GEX_3 (sous-performants)
✅ Priorisation HVL et GEX_5 (meilleurs résultats)
✅ Trailing stop plus agressif
✅ Breakeven plus rapide
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION OPTIMISÉE
# ============================================================================

ES_CONFIG_V4_OPT = {
    'symbol': 'ES',
    'tick_size': 0.25,
    'point_value': 50.00,
    'tick_value': 12.50,

    # Stop Loss - RÉDUIT pour limiter pertes
    'sl_base_ticks': 12,      # Réduit de 16 → 12
    'sl_max_ticks': 16,       # Réduit de 20 → 16
    'sl_min_ticks': 10,       # Réduit de 12 → 10

    # Take Profit - AUGMENTÉ pour améliorer ratio
    'tp1_ticks': 18,          # Augmenté de 12 → 18 (R:R 1.5:1)
    'tp2_ticks': 28,          # Augmenté de 20 → 28
    'tp3_ticks': 40,          # Augmenté de 30 → 40

    # Trailing - PLUS AGRESSIF
    'trail_activation_ticks': 8,   # Plus rapide (10 → 8)
    'trail_distance_ticks': 4,     # Plus serré (5 → 4)
    'breakeven_trigger_ticks': 6,  # Plus rapide (7 → 6)
    'breakeven_buffer_ticks': 2,

    # 🔥 MAGNET ZONES - DATA-DRIVEN
    'magnet_entry_min_ticks': 5,
    'magnet_entry_max_ticks': 15,
    'magnet_optimal_ticks': 10,

    # Risk
    'max_trades_day': 8,
    'max_loss_day_usd': 500,
}

# 🔥 NIVEAUX MAGNET - FILTRÉS ET OPTIMISÉS
# Désactivé GEX_1 et GEX_3 (sous-performants: 53.3% et 58.3% WR)
MAGNET_LEVELS_OPT = {
    # Tier S (>82% bounce rate) - PRIORITÉ ABSOLUE
    'HVL': {'strength': 1.00, 'min_rr': 0.50, 'bounce_rate': 83.6, 'enabled': True},  # 87.5% WR réel
    'GEX_5': {'strength': 0.95, 'min_rr': 0.50, 'bounce_rate': 82.3, 'enabled': True},  # 66.7% WR réel

    # Tier A - GEX_2 conservé (69.1% WR, mais volume élevé)
    'GEX_2': {'strength': 0.85, 'min_rr': 0.55, 'bounce_rate': 82.0, 'enabled': True},  # 69.1% WR

    # Tier B - DÉSACTIVÉS (sous-performants)
    'GEX_1': {'strength': 0.70, 'min_rr': 0.60, 'bounce_rate': 82.1, 'enabled': False},  # 53.3% WR ❌
    'GEX_3': {'strength': 0.65, 'min_rr': 0.55, 'bounce_rate': 74.2, 'enabled': False},  # 58.3% WR ❌

    # Tier C - Support (conservés mais seuils plus stricts)
    'CALL_RESISTANCE': {'strength': 0.75, 'min_rr': 0.60, 'bounce_rate': 75.0, 'enabled': True},
    'PUT_SUPPORT': {'strength': 0.75, 'min_rr': 0.60, 'bounce_rate': 75.0, 'enabled': True},
    'GAMMA_WALL': {'strength': 0.70, 'min_rr': 0.55, 'bounce_rate': 70.0, 'enabled': True},
}

# Sessions
ES_SESSIONS_V4 = {
    'US_OPEN': {'hours': (14.5, 16), 'enabled': True, 'min_confluence': 0.55},
    'US_MID': {'hours': (16, 19.5), 'enabled': True, 'min_confluence': 0.60},
    'US_POWER_HOUR': {'hours': (19.5, 21), 'enabled': True, 'min_confluence': 0.55},
    'LONDON': {'hours': (8, 14), 'enabled': True, 'min_confluence': 0.60},
}

# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class MagnetLevel:
    """Niveau magnet avec métadonnées"""
    price: float
    type: str
    strength: float
    bounce_rate: float
    distance_ticks: float
    min_rr: float

    def __repr__(self):
        return f"{self.type}@{self.price:.2f} ({self.distance_ticks:.0f}t, BR:{self.bounce_rate:.0f}%)"


@dataclass
class MagnetSetup:
    """Setup MenthorQ Magnet"""
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float

    magnet_level: MagnetLevel
    confluence_score: float
    risk_reward: float
    entry_quality: float

    conditions: List[str]


# ============================================================================
# CLASSE PRINCIPALE OPTIMISÉE
# ============================================================================

class ESMenthorQMagnetV4Optimized:
    """
    🎯 ES MenthorQ Magnet V4.0 OPTIMIZED

    Optimisations basées sur backtest 17 jours:
    - TP: 18t (vs 12t) → R:R 1.5:1
    - SL: 12t (vs 16t) → Limiter pertes
    - Filtrage GEX_1/GEX_3 (sous-performants)
    - Priorisation HVL/GEX_5 (87.5% et 66.7% WR)
    - Trailing stop plus agressif
    """

    def __init__(self, config: Dict = None):
        self.config = config or ES_CONFIG_V4_OPT
        self.sessions = ES_SESSIONS_V4
        self.ts = self.config['tick_size']

        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'pnl': 0.0,
        }

        logger.info("="*70)
        logger.info("🎯 ES MENTHORQ MAGNET V4.0 OPTIMIZED")
        logger.info("="*70)
        logger.info("   OPTIMISATIONS: TP 18t, SL 12t, Filtrage GEX_1/3")
        logger.info("   FOCUS: HVL (87.5% WR) + GEX_5 (66.7% WR)")
        logger.info("="*70)

    # ========================================================================
    # EXTRACTION NIVEAUX MAGNET (FILTRÉS)
    # ========================================================================

    def _extract_magnet_levels(self, tick: Dict) -> List[MagnetLevel]:
        """Extrait UNIQUEMENT les niveaux magnet activés"""
        mid = tick.get('mid', 0)
        levels = []

        # HVL (87.5% WR réel - PRIORITÉ #1)
        if MAGNET_LEVELS_OPT['HVL']['enabled']:
            hvl = tick.get('hvl', 0)
            if hvl > 0:
                config = MAGNET_LEVELS_OPT['HVL']
                levels.append(MagnetLevel(
                    price=hvl, type='HVL',
                    strength=config['strength'],
                    bounce_rate=config['bounce_rate'],
                    distance_ticks=abs(mid - hvl) / self.ts,
                    min_rr=config['min_rr']
                ))

        # GEX_5 (66.7% WR réel - PRIORITÉ #2)
        if MAGNET_LEVELS_OPT['GEX_5']['enabled']:
            gex_5 = tick.get('gex_5', 0)
            if gex_5 > 0:
                config = MAGNET_LEVELS_OPT['GEX_5']
                levels.append(MagnetLevel(
                    price=gex_5, type='GEX_5',
                    strength=config['strength'],
                    bounce_rate=config['bounce_rate'],
                    distance_ticks=abs(mid - gex_5) / self.ts,
                    min_rr=config['min_rr']
                ))

        # GEX_2 (69.1% WR - conservé mais seuil plus strict)
        if MAGNET_LEVELS_OPT['GEX_2']['enabled']:
            gex_2 = tick.get('gex_2', 0)
            if gex_2 > 0:
                config = MAGNET_LEVELS_OPT['GEX_2']
                levels.append(MagnetLevel(
                    price=gex_2, type='GEX_2',
                    strength=config['strength'],
                    bounce_rate=config['bounce_rate'],
                    distance_ticks=abs(mid - gex_2) / self.ts,
                    min_rr=config['min_rr']
                ))

        # GEX_1 et GEX_3 DÉSACTIVÉS (sous-performants)
        # ❌ GEX_1: 53.3% WR
        # ❌ GEX_3: 58.3% WR

        # Call Resistance / Put Support
        if MAGNET_LEVELS_OPT['CALL_RESISTANCE']['enabled']:
            call_res = tick.get('call_resistance', 0)
            if call_res > 0:
                config = MAGNET_LEVELS_OPT['CALL_RESISTANCE']
                levels.append(MagnetLevel(
                    price=call_res, type='CALL_RESISTANCE',
                    strength=config['strength'],
                    bounce_rate=config['bounce_rate'],
                    distance_ticks=abs(mid - call_res) / self.ts,
                    min_rr=config['min_rr']
                ))

        if MAGNET_LEVELS_OPT['PUT_SUPPORT']['enabled']:
            put_sup = tick.get('put_support', 0)
            if put_sup > 0:
                config = MAGNET_LEVELS_OPT['PUT_SUPPORT']
                levels.append(MagnetLevel(
                    price=put_sup, type='PUT_SUPPORT',
                    strength=config['strength'],
                    bounce_rate=config['bounce_rate'],
                    distance_ticks=abs(mid - put_sup) / self.ts,
                    min_rr=config['min_rr']
                ))

        # Trier par (strength * bounce_rate) - HVL et GEX_5 en priorité
        levels.sort(key=lambda x: x.strength * x.bounce_rate, reverse=True)

        return levels

    def _is_in_magnet_zone(self, level: MagnetLevel) -> Tuple[bool, float]:
        """Vérifie si prix dans magnet zone (5-15 ticks)"""
        dist = level.distance_ticks

        min_dist = self.config['magnet_entry_min_ticks']
        max_dist = self.config['magnet_entry_max_ticks']
        optimal = self.config['magnet_optimal_ticks']

        if dist < min_dist or dist > max_dist:
            return False, 0.0

        # Quality based on distance to optimal
        if dist <= optimal:
            quality = 1.0
        else:
            quality = 1.0 - (dist - optimal) / (max_dist - optimal) * 0.4

        return True, quality

    # ========================================================================
    # ORDERFLOW VALIDATION (LÉGÈREMENT ASSOUPLIE)
    # ========================================================================

    def _validate_orderflow(self, tick: Dict, direction: str) -> Tuple[bool, float, str]:
        """OrderFlow validation (seuil légèrement assoupli: 0.58 vs 0.60)"""
        delta = tick.get('delta', 0)
        delta_pct = tick.get('deltaPct', 0)
        depth_imb = tick.get('depth_imbalance', 0)
        smart_money = tick.get('smart_money_flow', 0)
        mia_score = tick.get('mia_bullish_score', 0)

        score = 0.5
        reasons = []

        if direction == 'LONG':
            if delta > 0:
                score += 0.12
                reasons.append("Delta+")
            if delta_pct > 0.3:
                score += 0.08
            if depth_imb > 0.1:
                score += 0.08
                reasons.append("DOM+")
            if smart_money > 0:
                score += 0.08
                reasons.append("SMF+")
            if mia_score > 0.3:
                score += 0.12
                reasons.append(f"MIA+")
            elif mia_score < -0.3:
                score -= 0.10
        else:  # SHORT
            if delta < 0:
                score += 0.12
                reasons.append("Delta-")
            if delta_pct < -0.3:
                score += 0.08
            if depth_imb < -0.1:
                score += 0.08
                reasons.append("DOM-")
            if smart_money < 0:
                score += 0.08
                reasons.append("SMF-")
            if mia_score < -0.3:
                score += 0.12
                reasons.append(f"MIA-")
            elif mia_score > 0.3:
                score -= 0.10

        # Seuil légèrement assoupli (0.58 vs 0.60)
        is_valid = score >= 0.58
        reason = " | ".join(reasons) if reasons else "Neutre"

        return is_valid, score, reason

    # ========================================================================
    # SL CALCULATION (OPTIMISÉ)
    # ========================================================================

    def _calculate_sl(self, entry: float, direction: str, magnet: MagnetLevel, tick: Dict) -> Tuple[float, str]:
        """Calcule SL optimisé (max 12t)"""
        buffer = 3
        sl_base = self.config['sl_base_ticks']  # 12t
        sl_min = self.config['sl_min_ticks']    # 10t

        if direction == 'SHORT':
            sl_magnet = magnet.price + (buffer * self.ts)
            sl_default = entry + (sl_base * self.ts)
            sl = max(sl_magnet, sl_default)
            sl_ticks_from_entry = (sl - entry) / self.ts
            if sl_ticks_from_entry < sl_min:
                sl = entry + (sl_min * self.ts)
            reason = f"SL {abs(entry - sl) / self.ts:.0f}t au-dessus {magnet.type}"
        else:  # LONG
            sl_magnet = magnet.price - (buffer * self.ts)
            sl_default = entry - (sl_base * self.ts)
            sl = min(sl_magnet, sl_default)
            sl_ticks_from_entry = (entry - sl) / self.ts
            if sl_ticks_from_entry < sl_min:
                sl = entry - (sl_min * self.ts)
            reason = f"SL {abs(entry - sl) / self.ts:.0f}t en-dessous {magnet.type}"

        # Vérifier max
        sl_ticks = abs(entry - sl) / self.ts
        if sl_ticks > self.config['sl_max_ticks']:
            if direction == 'SHORT':
                sl = entry + (sl_base * self.ts)
            else:
                sl = entry - (sl_base * self.ts)
            reason = f"SL default {sl_base}t"

        return sl, reason

    def _calculate_rr(self, entry: float, sl: float, tp: float, direction: str) -> float:
        """Calcule Risk:Reward"""
        if direction == 'LONG':
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp

        return reward / risk if risk > 0 else 0.0

    # ========================================================================
    # SETUP GENERATION
    # ========================================================================

    def _generate_setup(self, tick: Dict, magnet: MagnetLevel, entry_quality: float) -> Optional[MagnetSetup]:
        """Génère setup optimisé"""
        mid = tick.get('mid', 0)

        # Direction (fade vers le niveau)
        if mid < magnet.price:
            direction = 'LONG'
        else:
            direction = 'SHORT'

        # OrderFlow
        of_valid, of_score, of_reason = self._validate_orderflow(tick, direction)
        if not of_valid:
            return None

        # SL
        sl, sl_reason = self._calculate_sl(mid, direction, magnet, tick)

        # TPs (augmentés: 18/28/40t)
        if direction == 'LONG':
            tp1 = mid + self.config['tp1_ticks'] * self.ts  # 18t
            tp2 = mid + self.config['tp2_ticks'] * self.ts  # 28t
            tp3 = mid + self.config['tp3_ticks'] * self.ts  # 40t
        else:
            tp1 = mid - self.config['tp1_ticks'] * self.ts
            tp2 = mid - self.config['tp2_ticks'] * self.ts
            tp3 = mid - self.config['tp3_ticks'] * self.ts

        # R:R
        rr = self._calculate_rr(mid, sl, tp1, direction)
        if rr < magnet.min_rr:
            return None

        # Confluence
        confluence = 0.4
        confluence += magnet.strength * 0.25
        confluence += (magnet.bounce_rate / 100) * 0.15
        confluence += of_score * 0.15
        confluence += entry_quality * 0.05

        setup = MagnetSetup(
            direction=direction,
            entry_price=mid,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            magnet_level=magnet,
            confluence_score=min(1.0, confluence),
            risk_reward=rr,
            entry_quality=entry_quality,
            conditions=[
                f"Magnet: {magnet}",
                sl_reason,
                f"R:R: {rr:.2f} (min: {magnet.min_rr:.2f})",
                f"OrderFlow: {of_reason} ({of_score:.2f})",
                f"Entry Quality: {entry_quality:.2f}",
                f"Bounce Rate: {magnet.bounce_rate:.1f}%"
            ]
        )

        return setup

    def _is_trading_allowed(self, tick: Dict) -> Tuple[bool, str]:
        """Vérifie si trading autorisé"""
        if self.daily_stats['trades'] >= self.config['max_trades_day']:
            return False, f"Max trades/day atteint ({self.config['max_trades_day']})"

        if self.daily_stats['pnl'] <= -self.config['max_loss_day_usd']:
            return False, f"Max loss/day atteint (${self.config['max_loss_day_usd']})"

        return True, "OK"

    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================

    def generate_signal(self, tick: Dict) -> Optional[Dict]:
        """Point d'entrée principal V4.0 OPTIMIZED"""
        allowed, reason = self._is_trading_allowed(tick)
        if not allowed:
            return None

        mid = tick.get('mid', 0)
        if mid <= 0:
            return None

        # Extraire niveaux magnet (filtrés)
        magnet_levels = self._extract_magnet_levels(tick)

        if not magnet_levels:
            return None

        # Trouver niveaux dans magnet zone
        in_zone = []
        for magnet in magnet_levels:
            is_in, quality = self._is_in_magnet_zone(magnet)
            if is_in:
                in_zone.append((magnet, quality))

        if not in_zone:
            return None

        # Trier par priorité (HVL et GEX_5 en premier)
        in_zone.sort(key=lambda x: x[0].strength * x[0].bounce_rate * x[1], reverse=True)

        # Essayer top 3
        for magnet, quality in in_zone[:3]:
            setup = self._generate_setup(tick, magnet, quality)

            if setup:
                logger.info("=" * 70)
                logger.info(f"🎯 ES MAGNET SIGNAL (OPT): {setup.direction} @ {setup.entry_price:.2f}")
                logger.info(f"   SL: {setup.stop_loss:.2f} | TP1: {setup.take_profit_1:.2f}")
                logger.info(f"   R:R: {setup.risk_reward:.2f} | Conf: {setup.confluence_score:.2f}")
                logger.info("=" * 70)

                return {
                    'symbol': 'ES',
                    'action': setup.direction,
                    'entry_price': setup.entry_price,
                    'stop_loss': setup.stop_loss,
                    'take_profit_1': setup.take_profit_1,
                    'take_profit_2': setup.take_profit_2,
                    'take_profit_3': setup.take_profit_3,
                    'confidence': setup.confluence_score,
                    'risk_reward': setup.risk_reward,
                    'setup_type': 'menthorq_magnet_opt',
                    'key_level': str(setup.magnet_level),
                    'entry_quality': setup.entry_quality,
                    'strategy': 'es_menthorq_magnet_v4_optimized',
                    'timestamp': tick.get('t_ms', 0),
                    'trail_config': {
                        'activation_ticks': self.config['trail_activation_ticks'],
                        'distance_ticks': self.config['trail_distance_ticks'],
                    },
                    'breakeven_config': {
                        'trigger_ticks': self.config['breakeven_trigger_ticks'],
                        'buffer_ticks': self.config['breakeven_buffer_ticks'],
                    }
                }

        return None

    def register_trade_result(self, result: str, pnl: float):
        """Enregistre résultat"""
        self.daily_stats['trades'] += 1
        self.daily_stats['pnl'] += pnl

        if result == 'WIN':
            self.daily_stats['wins'] += 1
        elif result == 'LOSS':
            self.daily_stats['losses'] += 1




