"""
Loader V4 - Adapté à structure réelle du système.

Structure:
D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/
  └─ {DATE}/
      └─ CHART_{ID}/
          └─ ML_READY/
              └─ ml_{SYMBOL}Z25_FUT_CME_{ID}.jsonl
"""

import json
from pathlib import Path
from typing import List, Dict
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class JSONLSnapshotLoader:
    """
    Loader adapté à structure réelle du système.

    Path: D:/MIA_IA_system/.../NOVEMBRE/{DATE}/CHART_{ID}/ML_READY/
    File: ml_{SYMBOL}Z25_FUT_CME_{ID}.jsonl
    """

    def __init__(self, base_path: str):
        """
        Args:
            base_path: D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/NOVEMBRE
        """
        self.base_path = Path(base_path)

        # Mapping symbol → chart_id (VALIDÉ)
        self.chart_mapping = {
            "ES": 3,
            "NQ": 9,
            "RTY": 1
        }

        logger.info(f"📁 JSONLSnapshotLoader V4 initialized")
        logger.info(f"   Base path: {self.base_path}")
        logger.info(f"   Chart mapping: {self.chart_mapping}")


    def load_day(self, symbol: str, date: str) -> List[Dict]:
        """
        Charge snapshots pour 1 symbole, 1 jour.

        Args:
            symbol: "ES", "NQ", "RTY"
            date: "20251105" (YYYYMMDD)

        Returns:
            Liste de snapshots (dicts)

        Raises:
            FileNotFoundError: Si fichier absent
        """
        chart_id = self.chart_mapping.get(symbol)
        if not chart_id:
            raise ValueError(f"Unknown symbol: {symbol}")

        # Construire path EXACT selon structure réelle
        file_path = (
            self.base_path /
            date /
            f"CHART_{chart_id}" /
            "ML_READY" /
            f"ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl"
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Snapshot file not found: {file_path}\n"
                f"Expected: ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl"
            )

        logger.info(f"📂 Loading: {date}/{symbol} ({file_path.name})")

        # Charger snapshots
        snapshots = []
        line_count = 0
        error_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line_count = i
                try:
                    snapshot = json.loads(line.strip())
                    snapshots.append(snapshot)
                except json.JSONDecodeError as e:
                    error_count += 1
                    if error_count <= 5:  # Log premiers 5 seulement
                        logger.warning(f"⚠️ Skipping line {i}: {e}")

        logger.info(f"✅ Loaded {len(snapshots):,} snapshots ({line_count:,} lines, {error_count} errors)")
        return snapshots


    def load_date_range(
        self,
        symbol: str,
        dates: List[str]
    ) -> List[Dict]:
        """
        Charge snapshots pour une liste de dates.

        Args:
            symbol: "ES", "NQ", "RTY"
            dates: ["20251105", "20251106", ...]

        Returns:
            Liste de tous snapshots chronologiques
        """
        all_snapshots = []

        for date in dates:
            try:
                day_snapshots = self.load_day(symbol, date)
                all_snapshots.extend(day_snapshots)
                logger.info(f"   {date}: {len(day_snapshots):,} snapshots")
            except FileNotFoundError as e:
                logger.warning(f"   {date}: File not found, skipping")
            except Exception as e:
                logger.error(f"   {date}: Error - {e}")

        logger.info(f"📊 Total snapshots loaded: {len(all_snapshots):,}")
        return all_snapshots
