#!/usr/bin/env python3
"""
Test simplifié lecture parallèle snapshots
"""
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.ml_ready_reader import MLReadyReader

async def test():
    print("=" * 80)
    print("⚡ TEST LECTURE SNAPSHOTS - SÉQUENTIEL vs PARALLÈLE")
    print("=" * 80)
    print()

    reader = MLReadyReader(
        data_dir="D:\\MIA_IA_system\\DATA_SIERRA_CHART\\DATA_2025\\NOVEMBRE\\20251129"
    )
    symbols = ["ES", "NQ"]

    print(f"📋 Symboles: {', '.join(symbols)}")
    print()

    # Test séquentiel
    print("1️⃣  SÉQUENTIEL:")
    seq_times = []
    for _ in range(5):
        start = time.perf_counter()
        for sym in symbols:
            reader.read_latest_snapshot(sym)
        elapsed = (time.perf_counter() - start) * 1000
        seq_times.append(elapsed)
        print(f"   {elapsed:6.2f}ms")
    seq_avg = sum(seq_times) / len(seq_times)
    print(f"   Moyenne: {seq_avg:.2f}ms\n")

    # Test parallèle
    print("2️⃣  PARALLÈLE:")
    async def read_parallel():
        async def _read_one(sym):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, reader.read_latest_snapshot, sym)
        tasks = [_read_one(sym) for sym in symbols]
        return await asyncio.gather(*tasks)

    par_times = []
    for _ in range(5):
        start = time.perf_counter()
        await read_parallel()
        elapsed = (time.perf_counter() - start) * 1000
        par_times.append(elapsed)
        print(f"   {elapsed:6.2f}ms")
    par_avg = sum(par_times) / len(par_times)
    print(f"   Moyenne: {par_avg:.2f}ms\n")

    # Résultats
    gain = seq_avg - par_avg
    gain_pct = (gain / seq_avg) * 100

    print("=" * 80)
    print(f"🎯 GAIN: {gain:.2f}ms ({gain_pct:.1f}% plus rapide)")
    print(f"   Séquentiel: {seq_avg:.2f}ms")
    print(f"   Parallèle:  {par_avg:.2f}ms")
    print("=" * 80)

    if gain >= 10:
        print("\n✅ RECOMMANDATION: Gain significatif - IMPLÉMENTÉ dans launcher!")
    else:
        print("\n⚠️  Gain faible (< 10ms)")

if __name__ == "__main__":
    asyncio.run(test())
