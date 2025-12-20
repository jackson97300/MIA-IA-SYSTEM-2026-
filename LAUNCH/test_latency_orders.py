#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TEST LATENCE PASSAGE D'ORDRES                              ║
║                    MIA Trading System - Diagnostic                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Ce script mesure:                                                            ║
║  1. Latence connexion DTC                                                     ║
║  2. Latence envoi ordre market                                                ║
║  3. Latence confirmation fill                                                 ║
║  4. Latence totale (signal → fill)                                           ║
║                                                                               ║
║  ⚠️ ATTENTION: Ce test peut passer de VRAIS ordres!                          ║
║  Utiliser uniquement sur compte SIMULATION (Sim1, Sim2)                       ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import statistics

# Setup path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class LatencyTestConfig:
    """Configuration du test de latence"""

    # DTC Connection
    DTC_HOST = "localhost"
    DTC_PORT = 11099

    # Symboles à tester
    SYMBOLS = ["ES", "NQ"]

    # Comptes simulation
    TRADE_ACCOUNTS = {
        "ES": "Sim1",
        "NQ": "Sim2"
    }

    # Nombre de tests par symbole
    NUM_TESTS = 5

    # Délai entre tests (secondes)
    DELAY_BETWEEN_TESTS = 2

    # Mode (True = simulation sans ordre réel)
    DRY_RUN = True  # ⚠️ Mettre False pour vrais ordres


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE DE TEST
# ═══════════════════════════════════════════════════════════════════════════════

class LatencyTester:
    """Testeur de latence pour les ordres DTC"""

    def __init__(self, config: LatencyTestConfig = None):
        self.config = config or LatencyTestConfig()
        self.results: Dict[str, List[Dict]] = {s: [] for s in self.config.SYMBOLS}
        self.dtc_connector = None

    async def run_full_test(self):
        """Lance le test complet de latence"""

        print("=" * 80)
        print("TEST DE LATENCE - PASSAGE D'ORDRES")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Symboles: {', '.join(self.config.SYMBOLS)}")
        print(f"Tests par symbole: {self.config.NUM_TESTS}")
        print(f"Delai entre tests: {self.config.DELAY_BETWEEN_TESTS}s")
        print(f"Mode: {'DRY RUN (simulation)' if self.config.DRY_RUN else 'ORDRES REELS'}")
        print("=" * 80)
        print()

        # Test 1: Latence connexion DTC
        await self._test_dtc_connection()

        # Test 2: Latence lecture snapshots
        await self._test_snapshot_latency()

        # Test 3: Latence ordres (si pas dry run)
        if not self.config.DRY_RUN:
            await self._test_order_latency()
        else:
            print("⏭️  Test ordres réels SKIPPÉ (DRY_RUN=True)")
            print()

        # Test 4: Latence interne pipeline
        await self._test_pipeline_latency()

        # Résumé
        self._print_summary()

    async def _test_dtc_connection(self):
        """Test latence connexion DTC"""

        print("=" * 60)
        print("TEST 1: LATENCE CONNEXION DTC")
        print("=" * 60)

        try:
            from execution.sierra_dtc_connector import SierraDTCConnector, DTCConfig

            connection_times = []

            for i in range(3):
                start = time.perf_counter()

                try:
                    dtc_config = DTCConfig(
                        host=self.config.DTC_HOST,
                        es_port=self.config.DTC_PORT,
                        nq_port=self.config.DTC_PORT,
                        trade_account_map=self.config.TRADE_ACCOUNTS
                    )
                    connector = SierraDTCConnector(config=dtc_config)

                    # Tenter connexion avec ensure_connected (fallback PAPER MODE)
                    connected = await asyncio.wait_for(
                        connector.ensure_connected("ES"),
                        timeout=5.0
                    )

                    elapsed = (time.perf_counter() - start) * 1000

                    if connected:
                        if connector.paper_mode:
                            # DTC non joignable -> PAPER MODE
                            print(f"   [PAPER] Test {i+1}: {elapsed:.2f}ms (DTC non joignable -> PAPER MODE)")
                        else:
                            # Vraie connexion DTC
                            connection_times.append(elapsed)
                            print(f"   [OK] Test {i+1}: {elapsed:.2f}ms (connexion reelle)")
                            await connector.disconnect()
                    else:
                        print(f"   [FAIL] Test {i+1}: Connexion echouee")

                except asyncio.TimeoutError:
                    print(f"   [FAIL] Test {i+1}: Timeout (>5s)")
                except Exception as e:
                    print(f"   [FAIL] Test {i+1}: Erreur - {e}")

                await asyncio.sleep(0.5)

            if connection_times:
                avg = statistics.mean(connection_times)
                min_t = min(connection_times)
                max_t = max(connection_times)
                print()
                print(f"   Moyenne: {avg:.2f}ms")
                print(f"   Min: {min_t:.2f}ms | Max: {max_t:.2f}ms")

                if avg < 100:
                    print(f"   [EXCELLENT] (<100ms)")
                elif avg < 500:
                    print(f"   [ACCEPTABLE] (<500ms)")
                else:
                    print(f"   [LENT] (>500ms)")
            else:
                print("   [FAIL] Aucune connexion reussie")
                print("   TIP: Verifiez que Sierra Chart est lance avec DTC active")

        except ImportError as e:
            print(f"   [FAIL] Module non disponible: {e}")

        print()

    async def _test_snapshot_latency(self):
        """Test latence lecture snapshots"""

        print("=" * 60)
        print("TEST 2: LATENCE LECTURE SNAPSHOTS")
        print("=" * 60)

        try:
            from features.ml_ready_reader import MLReadyReader

            # Configuration pour MLReadyReader
            reader_config = {
                "live_mode": {
                    "realtime": {
                        "watch_dirs": ["D:/MIA_IA_system/snapshots"]
                    },
                    "chart_mapping": {"ES": 3, "NQ": 9}
                }
            }

            for symbol in self.config.SYMBOLS:
                read_times = []

                print(f"\n   [{symbol}]")

                for i in range(5):
                    start = time.perf_counter()

                    try:
                        reader = MLReadyReader(config=reader_config)
                        snapshot = reader.get_live_snapshot(symbol)
                        elapsed = (time.perf_counter() - start) * 1000

                        if snapshot:
                            read_times.append(elapsed)
                            age_ms = int(time.time() * 1000) - snapshot.get('t_ms', 0)
                            print(f"      Test {i+1}: {elapsed:.2f}ms (age: {age_ms}ms)")
                        else:
                            print(f"      Test {i+1}: Pas de snapshot")

                    except Exception as e:
                        print(f"      Test {i+1}: Erreur - {e}")

                if read_times:
                    avg = statistics.mean(read_times)
                    print(f"      Moyenne: {avg:.2f}ms")

                    if avg < 10:
                        print(f"      [EXCELLENT] (<10ms)")
                    elif avg < 50:
                        print(f"      [ACCEPTABLE] (<50ms)")
                    else:
                        print(f"      [LENT] (>50ms)")

        except ImportError as e:
            print(f"   [FAIL] Module non disponible: {e}")

        print()

    async def _test_order_latency(self):
        """Test latence passage d'ordres REELS"""

        print("=" * 60)
        print("TEST 3: LATENCE PASSAGE D'ORDRES")
        print("=" * 60)
        print("ATTENTION: Ordres REELS sur compte simulation!")
        print()

        try:
            from execution.sierra_dtc_connector import SierraDTCConnector, DTCConfig

            dtc_config = DTCConfig(
                host=self.config.DTC_HOST,
                es_port=self.config.DTC_PORT,
                nq_port=self.config.DTC_PORT,
                trade_account_map=self.config.TRADE_ACCOUNTS
            )
            connector = SierraDTCConnector(config=dtc_config)

            for symbol in self.config.SYMBOLS:
                print(f"\n   [{symbol}]")

                # Connexion
                connected = await connector.connect(symbol)
                if not connected:
                    print(f"      [FAIL] Connexion echouee")
                    continue

                order_times = []

                for i in range(self.config.NUM_TESTS):
                    # Mesurer temps ordre
                    start = time.perf_counter()

                    try:
                        # Envoyer ordre market BUY
                        result = await connector.send_market_order(
                            symbol=symbol,
                            direction="LONG",
                            quantity=1
                        )

                        order_sent_time = (time.perf_counter() - start) * 1000

                        if result.get('success'):
                            # Attendre fill (timeout 2s)
                            fill_start = time.perf_counter()
                            fill_received = False

                            while (time.perf_counter() - fill_start) < 2.0:
                                # Check fill status
                                if result.get('filled'):
                                    fill_received = True
                                    break
                                await asyncio.sleep(0.01)

                            fill_time = (time.perf_counter() - fill_start) * 1000
                            total_time = order_sent_time + fill_time

                            order_times.append({
                                'order_sent': order_sent_time,
                                'fill_received': fill_time if fill_received else None,
                                'total': total_time if fill_received else order_sent_time
                            })

                            print(f"      Test {i+1}: Ordre={order_sent_time:.2f}ms, "
                                  f"Fill={'%.2fms' % fill_time if fill_received else 'N/A'}")

                            # Fermer position immédiatement
                            await connector.flatten(symbol)

                        else:
                            print(f"      Test {i+1}: Ordre échoué - {result}")

                    except Exception as e:
                        print(f"      Test {i+1}: Erreur - {e}")

                    await asyncio.sleep(self.config.DELAY_BETWEEN_TESTS)

                # Stats
                if order_times:
                    avg_order = statistics.mean([t['order_sent'] for t in order_times])
                    fills = [t['fill_received'] for t in order_times if t['fill_received']]
                    avg_fill = statistics.mean(fills) if fills else 0

                    print(f"\n      Moyenne ordre: {avg_order:.2f}ms")
                    print(f"      Moyenne fill: {avg_fill:.2f}ms")
                    print(f"      Total moyen: {avg_order + avg_fill:.2f}ms")

                await connector.disconnect()

        except ImportError as e:
            print(f"   [FAIL] Module non disponible: {e}")

        print()

    async def _test_pipeline_latency(self):
        """Test latence interne de la pipeline"""

        print("=" * 60)
        print("TEST 4: LATENCE PIPELINE INTERNE")
        print("=" * 60)

        try:
            from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy
            from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem
            from features.ml_ready_reader import MLReadyReader

            # Configuration pour MLReadyReader
            reader_config = {
                "live_mode": {
                    "realtime": {
                        "watch_dirs": ["D:/MIA_IA_system/snapshots"]
                    },
                    "chart_mapping": {"ES": 3, "NQ": 9}
                }
            }

            # Initialiser composants
            ml_system = ML3LayerIntegratedSystem(
                symbols=self.config.SYMBOLS,
                use_ml_models=False
            )

            reader = MLReadyReader(config=reader_config)

            for symbol in self.config.SYMBOLS:
                print(f"\n   [{symbol}]")

                # Lire snapshot
                snapshot = reader.get_live_snapshot(symbol)
                if not snapshot:
                    print(f"      [FAIL] Pas de snapshot disponible")
                    continue

                pipeline_times = []

                for i in range(5):
                    start = time.perf_counter()

                    try:
                        # Simuler pipeline complète
                        # 1. Validation snapshot
                        if snapshot.get('t_ms'):
                            pass

                        # 2. ML 3-Layer analysis
                        result = ml_system.analyze(symbol, snapshot)

                        elapsed = (time.perf_counter() - start) * 1000
                        pipeline_times.append(elapsed)

                        score = result.get('total_score', 0) if result else 0
                        print(f"      Test {i+1}: {elapsed:.2f}ms (score: {score:.2%})")

                    except Exception as e:
                        print(f"      Test {i+1}: Erreur - {e}")

                if pipeline_times:
                    avg = statistics.mean(pipeline_times)
                    print(f"\n      Moyenne pipeline: {avg:.2f}ms")

                    if avg < 5:
                        print(f"      [EXCELLENT] (<5ms)")
                    elif avg < 20:
                        print(f"      [ACCEPTABLE] (<20ms)")
                    else:
                        print(f"      [LENT] (>20ms)")

        except ImportError as e:
            print(f"   [FAIL] Module non disponible: {e}")

        print()

    def _print_summary(self):
        """Affiche le resume des tests"""

        print("=" * 80)
        print("RESUME DES TESTS DE LATENCE")
        print("=" * 80)
        print()
        print("   Composant               | Latence Typique | Objectif")
        print("   " + "-" * 60)
        print("   Connexion DTC           | 50-200ms        | <500ms")
        print("   Lecture Snapshot        | 1-10ms          | <50ms")
        print("   Pipeline ML 3-Layer     | 2-10ms          | <20ms")
        print("   Envoi Ordre             | 10-50ms         | <100ms")
        print("   Confirmation Fill       | 50-200ms        | <500ms")
        print("   " + "-" * 60)
        print("   TOTAL (signal->fill)    | 100-500ms       | <1000ms")
        print()
        print("=" * 80)
        print()
        print("RECOMMANDATIONS:")
        print()
        print("   1. Latence > 500ms total:")
        print("      -> Verifier connexion reseau")
        print("      -> Verifier charge CPU")
        print("      -> Reduire logging en production")
        print()
        print("   2. Snapshots lents:")
        print("      -> Verifier disque (SSD recommande)")
        print("      -> Reduire taille dossier snapshots")
        print()
        print("   3. Pipeline lente:")
        print("      -> Desactiver modules non essentiels")
        print("      -> Profiler avec PerformanceProfiler")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Point d'entrée"""

    print()
    print("=" * 80)
    print("                    TEST LATENCE - MIA TRADING SYSTEM                         ")
    print("=" * 80)
    print()

    tester = LatencyTester()
    await tester.run_full_test()

    print("[OK] Tests termines")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOP] Tests interrompus")
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        raise
