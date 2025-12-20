"""
Backtest runner V4 - Production ready.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List

from .jsonl_loader import JSONLSnapshotLoader
from .trade_generator import SyntheticTradeGenerator
from .outcome_simulator import OutcomeSimulator

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Exécute backtest complet V4."""

    def __init__(
        self,
        base_path: str,
        dates: List[str],
        symbols: List[str] = ["NQ", "ES", "RTY"]
    ):
        """
        Args:
            base_path: D:/MIA_IA_system/.../NOVEMBRE
            dates: ["20251105", "20251106", ...]
            symbols: ["NQ", "ES", "RTY"]
        """
        self.base_path = base_path
        self.dates = dates
        self.symbols = symbols

        self.loader = JSONLSnapshotLoader(base_path)

        logger.info("=" * 80)
        logger.info("🚀 BACKTEST RUNNER V4 PRODUCTION")
        logger.info("=" * 80)
        logger.info(f"   Base path: {base_path}")
        logger.info(f"   Dates: {len(dates)} days")
        logger.info(f"   Symbols: {symbols}")


    def run(self) -> pd.DataFrame:
        """Exécute backtest complet."""
        all_trades = []

        for symbol in self.symbols:
            logger.info("")
            logger.info(f"{'='*80}")
            logger.info(f"📊 PROCESSING {symbol}")
            logger.info(f"{'='*80}")

            # Load snapshots
            try:
                snapshots = self.loader.load_date_range(symbol, self.dates)
            except Exception as e:
                logger.error(f"❌ Failed to load {symbol}: {e}")
                continue

            if not snapshots:
                logger.warning(f"⚠️ No snapshots for {symbol}")
                continue

            # Generate trades
            generator = SyntheticTradeGenerator(symbol, tick_size=0.25)
            trades = generator.generate_trades(snapshots)

            if not trades:
                logger.warning(f"⚠️ No trades generated for {symbol}")
                continue

            # Simulate outcomes
            logger.info(f"🔄 Simulating outcomes...")
            simulator = OutcomeSimulator(tick_size=0.25)

            for trade in trades:
                entry_idx = trade['snapshot_index']
                entry_time = trade['timestamp']

                post_snaps = [
                    s for s in snapshots[entry_idx+1:]
                    if s['t_ms'] > entry_time
                    and s['t_ms'] <= entry_time + 120000
                ]

                outcome = simulator.simulate_trade(trade, post_snaps)
                trade.update(outcome)
                trade.pop('snapshot', None)

            all_trades.extend(trades)
            logger.info(f"✅ {symbol}: {len(trades)} trades")

        # Results
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 FINAL RESULTS V4")
        logger.info("=" * 80)

        df = pd.DataFrame(all_trades)

        if len(df) == 0:
            logger.error("❌ No trades generated!")
            return df

        logger.info(f"Total trades: {len(df):,}")
        logger.info(f"\n📈 Distribution outcomes:")
        logger.info(df['outcome'].value_counts())
        logger.info(f"\n⚠️ Stop hunts: {df['is_stop_hunt'].sum()} ({df['is_stop_hunt'].mean():.1%})")

        # Validation
        stop_hunt_pct = df['is_stop_hunt'].mean()
        if 0.10 <= stop_hunt_pct <= 0.20:
            logger.info("✅ Distribution stop hunts OK (10-20%)")
        elif stop_hunt_pct < 0.10:
            logger.warning(f"⚠️ Stop hunts trop faibles: {stop_hunt_pct:.1%}")
        else:
            logger.warning(f"⚠️ Stop hunts trop élevés: {stop_hunt_pct:.1%}")

        return df
