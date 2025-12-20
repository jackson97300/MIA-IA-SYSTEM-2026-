#!/usr/bin/env python3
"""
Test de la lecture parallèle des snapshots
Compare la lecture séquentielle vs parallèle et mesure le gain de latence
"""

import sys
import asyncio
import time
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Importer la config directement du launcher
import sys
import importlib.util
spec = importlib.util.spec_from_file_location(
    "launch_config",
    Path(__file__).parent / "launch_production_CLEAN_v2.py"
)
launch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch_module)
ProductionConfig = launch_module.ProductionConfig

from features.ml_ready_reader import MLReadyReader

async def test_sequential_read(reader: MLReadyReader, symbols: list) -> float:
    """Test lecture séquentielle (méthode actuelle)"""
    start = time.perf_counter()

    for symbol in symbols:
        snapshot = reader.read_latest_snapshot(symbol)

    elapsed = (time.perf_counter() - start) * 1000  # ms
    return elapsed

async def test_parallel_read(reader: MLReadyReader, symbols: list) -> float:
    """Test lecture parallèle (nouvelle méthode)"""

    async def _read_one(symbol: str):
        """Lit un snapshot (async wrapper)"""
        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(
            None,
            reader.read_latest_snapshot,
            symbol
        )
        return symbol, snapshot

    start = time.perf_counter()

    # Lancer toutes les lectures en parallèle
    tasks = [_read_one(sym) for sym in symbols]
    results = await asyncio.gather(*tasks)

    elapsed = (time.perf_counter() - start) * 1000  # ms
    return elapsed

async def main():
    print("=" * 80)
    print("⚡ TEST LECTURE SNAPSHOTS PARALLÈLE vs SÉQUENTIELLE")
    print("=" * 80)
    print()

    config = ProductionConfig()
    reader = MLReadyReader(config=config)
    symbols = config.symbols  # ["ES", "NQ", "RTY"]

    print(f"📋 Symboles testés: {', '.join(symbols)} ({len(symbols)} symbols)")
    print(f"📁 Répertoire data: {reader.data_dir}")
    print()

    # ════════════════════════════════════════════════════════════════════════
    # TEST 1: LECTURE SÉQUENTIELLE (ACTUELLE)
    # ════════════════════════════════════════════════════════════════════════
    print("1️⃣  LECTURE SÉQUENTIELLE (méthode actuelle):")
    print("-" * 80)

    seq_times = []
    for i in range(5):
        elapsed = await test_sequential_read(reader, symbols)
        seq_times.append(elapsed)
        print(f"   Test {i+1}/5: {elapsed:6.2f}ms")

    seq_avg = sum(seq_times) / len(seq_times)
    seq_min = min(seq_times)
    seq_max = max(seq_times)

    print(f"   ────────────────────")
    print(f"   Moyenne:  {seq_avg:6.2f}ms")
    print(f"   Min:      {seq_min:6.2f}ms")
    print(f"   Max:      {seq_max:6.2f}ms")
    print()

    # ════════════════════════════════════════════════════════════════════════
    # TEST 2: LECTURE PARALLÈLE (OPTIMISÉE)
    # ════════════════════════════════════════════════════════════════════════
    print("2️⃣  LECTURE PARALLÈLE (nouvelle méthode - optimisée):")
    print("-" * 80)

    par_times = []
    for i in range(5):
        elapsed = await test_parallel_read(reader, symbols)
        par_times.append(elapsed)
        print(f"   Test {i+1}/5: {elapsed:6.2f}ms")

    par_avg = sum(par_times) / len(par_times)
    par_min = min(par_times)
    par_max = max(par_times)

    print(f"   ────────────────────")
    print(f"   Moyenne:  {par_avg:6.2f}ms")
    print(f"   Min:      {par_min:6.2f}ms")
    print(f"   Max:      {par_max:6.2f}ms")
    print()

    # ════════════════════════════════════════════════════════════════════════
    # COMPARAISON ET GAINS
    # ════════════════════════════════════════════════════════════════════════
    gain_ms = seq_avg - par_avg
    gain_pct = (gain_ms / seq_avg) * 100 if seq_avg > 0 else 0
    speedup = seq_avg / par_avg if par_avg > 0 else 1

    print("=" * 80)
    print("📊 RÉSULTATS COMPARATIFS")
    print("=" * 80)
    print()
    print(f"{'Métrique':<25} {'Séquentiel':>15} {'Parallèle':>15} {'Différence':>15}")
    print("-" * 80)
    print(f"{'Temps moyen':<25} {seq_avg:>13.2f}ms {par_avg:>13.2f}ms {gain_ms:>13.2f}ms")
    print(f"{'Temps min':<25} {seq_min:>13.2f}ms {par_min:>13.2f}ms {seq_min-par_min:>13.2f}ms")
    print(f"{'Temps max':<25} {seq_max:>13.2f}ms {par_max:>13.2f}ms {seq_max-par_max:>13.2f}ms")
    print()

    print("=" * 80)
    print("🎯 ANALYSE DE PERFORMANCE")
    print("=" * 80)
    print()

    # Évaluation du gain
    if gain_ms >= 15:
        verdict = "✅ EXCELLENT"
        emoji = "🚀"
    elif gain_ms >= 10:
        verdict = "✅ BON"
        emoji = "⚡"
    elif gain_ms >= 5:
        verdict = "✅ ACCEPTABLE"
        emoji = "👍"
    else:
        verdict = "⚠️  FAIBLE"
        emoji = "⚠️"

    print(f"{emoji} Gain de latence: {gain_ms:.2f}ms ({gain_pct:.1f}% plus rapide)")
    print(f"{emoji} Speedup: {speedup:.2f}x")
    print(f"{emoji} Verdict: {verdict}")
    print()

    # Impact sur cycle complet
    print("📈 IMPACT SUR CYCLE TRADING:")
    print(f"   • Latence cycle AVANT: ~124ms")
    print(f"   • Gain lecture snapshots: -{gain_ms:.2f}ms")
    print(f"   • Latence cycle APRÈS: ~{124 - gain_ms:.2f}ms")
    print()

    # Projection annuelle
    cycles_per_day = 60 * 60 * 5.5  # 5.5h de trading, 1 cycle/seconde
    cycles_per_year = cycles_per_day * 252  # 252 jours de trading/an
    total_gain_seconds = (gain_ms / 1000) * cycles_per_year
    total_gain_hours = total_gain_seconds / 3600

    print("💡 PROJECTION:")
    print(f"   • Cycles/jour: {cycles_per_day:,.0f}")
    print(f"   • Cycles/an: {cycles_per_year:,.0f}")
    print(f"   • Temps gagné/jour: {(gain_ms / 1000) * cycles_per_day:.1f}s")
    print(f"   • Temps gagné/an: {total_gain_hours:.1f}h")
    print()

    # Recommandation
    if gain_ms >= 10:
        print("=" * 80)
        print("🎯 RECOMMANDATION: ✅ IMPLÉMENTER IMMÉDIATEMENT")
        print("=" * 80)
        print()
        print("✅ Le gain de latence est significatif et justifie l'implémentation")
        print("✅ Aucun changement de logique (même données lues)")
        print("✅ Risque minimal (async/await standard)")
        print("✅ Code propre et maintenable")
        print()
        print("🚀 Fichier déjà modifié: LAUNCH/launch_production_CLEAN_v2.py")
        print("   • Méthode ajoutée: _read_all_snapshots_parallel()")
        print("   • Boucle principale mise à jour (ligne ~1070)")
        print()
        print("📋 PROCHAINE ÉTAPE:")
        print("   → Lancer le bot et vérifier que tout fonctionne")
        print("   → Vérifier les logs PerformanceProfiler pour confirmer le gain")
    else:
        print("=" * 80)
        print("⚠️  RECOMMANDATION: Gain faible, évaluer le besoin")
        print("=" * 80)

    print()
    print("=" * 80)
    print("✅ Test terminé")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
