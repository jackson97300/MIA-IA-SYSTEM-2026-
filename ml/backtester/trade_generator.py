"""
Trade generator V3 - Règles optimisées post-audits 17-18 nov.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SyntheticTradeGenerator:
    """Génère trades selon règles MenthorQ V3."""

    def __init__(self, symbol: str, tick_size: float = 0.25):
        self.symbol = symbol
        self.tick_size = tick_size

        # Paramètres V3 (optimisés post-audits)
        self.min_confluence = 0.75
        self.max_dist_hvl_ticks = 15
        self.min_depth_imbalance_long = 0.4
        self.min_depth_imbalance_short = -0.4
        self.min_delta_pct_long = 0.1
        self.min_delta_pct_short = -0.1
        self.max_dist_vwap_ticks = 15
        self.min_trade_interval_seconds = 120
        self.exclude_opening_range = True
        self.opening_range_seconds = 900

        self.last_trade_time = 0

        logger.info(f"🎯 TradeGenerator V3 [{symbol}]")
        logger.info(f"   Confluence: ≥{self.min_confluence}")
        logger.info(f"   Depth imbalance: ≥±{self.min_depth_imbalance_long}")
        logger.info(f"   Delta pct: ≥±{self.min_delta_pct_long}")
        logger.info(f"   Opening range: EXCLUDED")


    def should_enter_long(self, snapshot: Dict) -> bool:
        """Règles LONG V3 strictes."""

        # 1. Confluence
        confluence = snapshot.get('confluence_strength', 0) or 0
        if confluence < self.min_confluence:
            return False

        # 2. Près HVL
        hvl = snapshot.get('hvl', 0) or 0
        mid = snapshot.get('mid', 0) or 0
        if hvl > 0 and mid > 0:
            dist_hvl_ticks = abs(mid - hvl) / self.tick_size
            if dist_hvl_ticks > self.max_dist_hvl_ticks:
                return False

        # 3. DOM aligné (strict)
        depth_imb = snapshot.get('depth_imbalance', 0) or 0
        if depth_imb < self.min_depth_imbalance_long:
            return False

        # 4. Pas blind spot
        if snapshot.get('blind_spot_confluence', False):
            return False

        # 5. Flow positif (strict)
        delta_pct = snapshot.get('deltaPct', 0) or 0
        if delta_pct < self.min_delta_pct_long:
            return False

        # 6. Près VWAP (strict)
        d_vwap_ticks = snapshot.get('d_vwap_ticks', 0) or 0
        if d_vwap_ticks < -self.max_dist_vwap_ticks:
            return False

        # 7. Volatility OK
        vol_regime = snapshot.get('volatility_regime', 1) or 1
        if vol_regime > 2:
            return False

        # 8. Éviter opening range
        if self.exclude_opening_range:
            session_elapsed = snapshot.get('session_elapsed_s', 1000) or 1000
            if session_elapsed < self.opening_range_seconds:
                return False

        return True


    def should_enter_short(self, snapshot: Dict) -> bool:
        """Règles SHORT V3 (symétrique)."""

        confluence = snapshot.get('confluence_strength', 0) or 0
        if confluence < self.min_confluence:
            return False

        hvl = snapshot.get('hvl', 0) or 0
        mid = snapshot.get('mid', 0) or 0
        if hvl > 0 and mid > 0:
            dist_hvl_ticks = abs(mid - hvl) / self.tick_size
            if dist_hvl_ticks > self.max_dist_hvl_ticks:
                return False

        depth_imb = snapshot.get('depth_imbalance', 0) or 0
        if depth_imb > self.min_depth_imbalance_short:
            return False

        if snapshot.get('blind_spot_confluence', False):
            return False

        delta_pct = snapshot.get('deltaPct', 0) or 0
        if delta_pct > self.min_delta_pct_short:
            return False

        d_vwap_ticks = snapshot.get('d_vwap_ticks', 0) or 0
        if d_vwap_ticks > self.max_dist_vwap_ticks:
            return False

        vol_regime = snapshot.get('volatility_regime', 1) or 1
        if vol_regime > 2:
            return False

        if self.exclude_opening_range:
            session_elapsed = snapshot.get('session_elapsed_s', 1000) or 1000
            if session_elapsed < self.opening_range_seconds:
                return False

        return True


    def calculate_sl_tp(
        self,
        entry: float,
        direction: str,
        snapshot: Dict
    ) -> Tuple[float, float]:
        """Calcul SL/TP V3 optimisé."""

        # Base distances (augmentées)
        sl_ticks = 20
        tp_ticks = 20

        # Ajuster selon ATR
        atr = snapshot.get('atr', 5.0)
        atr_ticks = atr / self.tick_size
        if atr_ticks > 25:
            sl_ticks = 25
            tp_ticks = 25

        MIN_SL_TICKS = 15
        sl_ticks = max(sl_ticks, MIN_SL_TICKS)

        if direction == "LONG":
            sl_base = entry - (sl_ticks * self.tick_size)
            tp = entry + (tp_ticks * self.tick_size)

            # Ajuster si trop près zones danger (10 ticks)
            hvl = snapshot.get('hvl', 0)
            if hvl > 0 and abs(sl_base - hvl) < 10 * self.tick_size:
                sl_base -= 10 * self.tick_size

            # Check TOUS GEX walls
            gex_levels = [
                snapshot.get(f'gex_{i}', 0)
                for i in range(1, 11)
                if snapshot.get(f'gex_{i}', 0) > 0
            ]
            for gex in gex_levels:
                if abs(sl_base - gex) < 10 * self.tick_size:
                    sl_base -= 10 * self.tick_size
                    break

            # Check blind spots
            blind_spots = [
                snapshot.get(f'blind_spot_{i}', 0)
                for i in range(9)
                if snapshot.get(f'blind_spot_{i}', 0) > 0
            ]
            for bs in blind_spots:
                if abs(sl_base - bs) < 10 * self.tick_size:
                    sl_base -= 12 * self.tick_size
                    break

            sl = sl_base

        else:  # SHORT
            sl_base = entry + (sl_ticks * self.tick_size)
            tp = entry - (tp_ticks * self.tick_size)

            hvl = snapshot.get('hvl', 0)
            if hvl > 0 and abs(sl_base - hvl) < 10 * self.tick_size:
                sl_base += 10 * self.tick_size

            gex_levels = [
                snapshot.get(f'gex_{i}', 0)
                for i in range(1, 11)
                if snapshot.get(f'gex_{i}', 0) > 0
            ]
            for gex in gex_levels:
                if abs(sl_base - gex) < 10 * self.tick_size:
                    sl_base += 10 * self.tick_size
                    break

            blind_spots = [
                snapshot.get(f'blind_spot_{i}', 0)
                for i in range(9)
                if snapshot.get(f'blind_spot_{i}', 0) > 0
            ]
            for bs in blind_spots:
                if abs(sl_base - bs) < 10 * self.tick_size:
                    sl_base += 12 * self.tick_size
                    break

            sl = sl_base

        return sl, tp


    def generate_trades(self, snapshots: List[Dict]) -> List[Dict]:
        """Génère trades depuis snapshots."""
        trades = []
        self.last_trade_time = 0

        logger.info(f"🔄 Generating trades from {len(snapshots):,} snapshots...")

        for i, snapshot in enumerate(snapshots):
            t_ms = snapshot.get('t_ms', 0)

            # Cooldown
            if (t_ms - self.last_trade_time) / 1000 < self.min_trade_interval_seconds:
                continue

            # Check LONG
            if self.should_enter_long(snapshot):
                entry = snapshot.get('mid', 0) or 0
                if entry <= 0:
                    continue
                sl, tp = self.calculate_sl_tp(entry, "LONG", snapshot)

                trade = {
                    'trade_id': len(trades) + 1,
                    'timestamp': t_ms,
                    'symbol': self.symbol,
                    'direction': 'LONG',
                    'entry_price': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'snapshot_index': i,
                    'snapshot': snapshot
                }

                trades.append(trade)
                self.last_trade_time = t_ms
                continue

            # Check SHORT
            if self.should_enter_short(snapshot):
                entry = snapshot.get('mid', 0) or 0
                if entry <= 0:
                    continue
                sl, tp = self.calculate_sl_tp(entry, "SHORT", snapshot)

                trade = {
                    'trade_id': len(trades) + 1,
                    'timestamp': t_ms,
                    'symbol': self.symbol,
                    'direction': 'SHORT',
                    'entry_price': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'snapshot_index': i,
                    'snapshot': snapshot
                }

                trades.append(trade)
                self.last_trade_time = t_ms

        logger.info(f"✅ Generated {len(trades)} trades")
        return trades
