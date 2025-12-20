"""
Outcome simulator V3 - Labeling précis avec sl_in_confluence_zone.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class OutcomeSimulator:
    """Simule outcomes + labeling stop hunt précis."""

    def __init__(self, tick_size: float = 0.25):
        self.tick_size = tick_size
        self.max_duration_seconds = 120
        self.post_sl_window_seconds = 30


    def simulate_trade(
        self,
        trade: Dict,
        post_snapshots: List[Dict]
    ) -> Dict:
        """Simule outcome d'un trade."""

        entry_time = trade['timestamp']
        entry_price = trade['entry_price']
        sl_price = trade['sl_price']
        tp_price = trade['tp_price']
        direction = trade['direction']

        sl_hit = False
        tp_hit = False
        exit_time = None
        exit_price = None
        sl_hit_time = None

        for snap in post_snapshots:
            t = snap['t_ms']

            if (t - entry_time) / 1000 > self.max_duration_seconds:
                break

            high = snap.get('high', snap['mid'])
            low = snap.get('low', snap['mid'])

            if direction == 'LONG':
                if low <= sl_price and not sl_hit:
                    sl_hit = True
                    sl_hit_time = t
                    exit_time = t
                    exit_price = sl_price
                    break

                if high >= tp_price and not tp_hit:
                    tp_hit = True
                    exit_time = t
                    exit_price = tp_price
                    break

            else:  # SHORT
                if high >= sl_price and not sl_hit:
                    sl_hit = True
                    sl_hit_time = t
                    exit_time = t
                    exit_price = sl_price
                    break

                if low <= tp_price and not tp_hit:
                    tp_hit = True
                    exit_time = t
                    exit_price = tp_price
                    break

        duration_s = (exit_time - entry_time) / 1000 if exit_time else self.max_duration_seconds

        # Labeling stop hunt
        is_stop_hunt = 0
        max_after_sl = 0
        min_after_sl = 0

        if sl_hit and duration_s < self.max_duration_seconds:
            post_sl_snaps = [
                s for s in post_snapshots
                if s['t_ms'] > sl_hit_time
                and s['t_ms'] <= sl_hit_time + (self.post_sl_window_seconds * 1000)
            ]

            if post_sl_snaps:
                max_after_sl = max([s.get('high', s['mid']) for s in post_sl_snaps])
                min_after_sl = min([s.get('low', s['mid']) for s in post_sl_snaps])

                reversed_to_tp = False
                if direction == 'LONG':
                    reversed_to_tp = (max_after_sl >= tp_price)
                else:
                    reversed_to_tp = (min_after_sl <= tp_price)

                if reversed_to_tp:
                    is_stop_hunt = self._check_sl_in_confluence_zone(
                        sl_price,
                        trade['snapshot']
                    )

        # Outcome
        if tp_hit:
            outcome = 'WIN'
        elif sl_hit:
            outcome = 'STOP_HUNT' if is_stop_hunt else 'LOSS'
        else:
            outcome = 'TIMEOUT'

        return {
            'outcome': outcome,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'duration_seconds': duration_s,
            'is_stop_hunt': is_stop_hunt,
            'sl_hit': sl_hit,
            'tp_hit': tp_hit,
            'max_price_after_sl': max_after_sl,
            'min_price_after_sl': min_after_sl
        }


    def _check_sl_in_confluence_zone(
        self,
        sl_price: float,
        snapshot: Dict
    ) -> int:
        """
        Check si SL dans zone confluence.

        Returns:
            1 si dans zone, 0 sinon
        """

        # Check HVL
        hvl = snapshot.get('hvl', 0)
        if hvl > 0:
            dist_hvl_ticks = abs(sl_price - hvl) / self.tick_size
            if dist_hvl_ticks < 10:
                return 1

        # Check GEX (1-10)
        gex_levels = [
            snapshot.get(f'gex_{i}', 0)
            for i in range(1, 11)
            if snapshot.get(f'gex_{i}', 0) > 0
        ]
        for gex in gex_levels:
            dist_gex_ticks = abs(sl_price - gex) / self.tick_size
            if dist_gex_ticks < 10:
                return 1

        # Check blind spots
        blind_spots = [
            snapshot.get(f'blind_spot_{i}', 0)
            for i in range(9)
            if snapshot.get(f'blind_spot_{i}', 0) > 0
        ]
        confluence_strength = snapshot.get('confluence_strength', 0)

        for bs in blind_spots:
            dist_bs_ticks = abs(sl_price - bs) / self.tick_size
            if dist_bs_ticks < 10 and confluence_strength > 0.7:
                return 1

        return 0
