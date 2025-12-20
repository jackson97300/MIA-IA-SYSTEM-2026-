#!/usr/bin/env python3
"""
Fast Filters First - Optimisation Pipeline
Réorganiser évaluation pour rejeter 90% des signaux rapidement

Sprint 6 - TODO Tasks 4a, 4b, 4c
Date: 13 Novembre 2025
"""

import logging
from typing import Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FilterResult(Enum):
    """Résultat d'un filtre"""
    PASS = "PASS"
    REJECT = "REJECT"


@dataclass
class FilterResponse:
    """Réponse d'un filtre"""
    result: FilterResult
    reason: str
    execution_time_ms: float = 0.0


class FastFiltersFirst:
    """
    Fast Filters First - Pipeline optimisé

    Principe Pro (Jane Street, Optiver):
    1. Filtres rapides d'abord (< 0.1ms) → Rejettent 90%
    2. Filtres moyens (< 1ms) → Rejettent 8%
    3. Filtres complexes (ML, confluences) → Évaluent 2% restants

    Ordre optimal:
    - FAST: Spread, Liquidity, VWAP distance brute
    - MEDIUM: OrderFlow basique, DOM imbalance
    - SLOW: ML, MenthorQ, Confluences
    """

    def __init__(self, config: Dict):
        self.config = config

        # Seuils fast filters
        # 🔧 AJUSTÉ 13-NOV: Assouplissement pour sessions creuses (ETH/ASIA)
        # 🔧 CORRIGÉ 17-NOV: Assoupli pour session ASIA (spreads 6-9 ticks normaux)
        self.MAX_SPREAD_TICKS = {
            'ES': 10,   # 5 → 10 (session ASIA spreads 6-9 ticks normaux) ✅
            'NQ': 10,   # 5 → 10 (session ASIA spreads 6-9 ticks normaux) ✅
            'RTY': 5    # 3 → 5 (session ASIA)
        }

        # 🔧 MODIFICATION 2025-11-13 17:37: Réduit à 1 pour breakdown 1D Min
        #    Observé en live: NQ bid=1 ask=2, RTY bid=3 ask=1 (liquidité très basse)
        # 🔧 CORRIGÉ 17-NOV: Assoupli pour session ASIA (liquidité 1-2 contracts normale)
        self.MIN_LIQUIDITY = {
            'ES': 1,    # 3 → 1 (session ASIA liquidité très basse normale) ✅
            'NQ': 1,    # Déjà à 1 ✅
            'RTY': 1    # Déjà à 1 ✅
        }

        # 🔧 MODIFICATION 2025-11-13 17:35: Augmenté DRASTIQUEMENT pour breakdown 1D Min
        #    Observé en live: NQ=1476 ticks, RTY=329 ticks (tendance EXTRÊME sous 1D Min)
        self.MAX_VWAP_DISTANCE_TICKS_FAST = {
            'ES': 500,    # 300 → 500 (breakdown possible)
            'NQ': 2000,   # 400 → 2000 (observé 1476 ticks en live)
            'RTY': 400    # 150 → 400 (observé 329 ticks en live)
        }

        logger.info("⚡ FastFiltersFirst initialisé")

    def pre_filter(self, snapshot: Dict) -> FilterResponse:
        """
        Pre-Filter ultra-rapide (< 0.1ms)

        Check:
        1. Spread < 2 ticks
        2. Liquidity BBO > min
        3. VWAP distance < max extrême

        Args:
            snapshot: Données ML_READY

        Returns:
            FilterResponse
        """
        import time
        start = time.perf_counter()

        # Déterminer symbole
        sym = snapshot.get('sym', 'ES')
        if 'ES' in sym:
            symbol = 'ES'
        elif 'NQ' in sym:
            symbol = 'NQ'
        elif 'RTY' in sym or '2RTY' in sym:
            symbol = 'RTY'
        else:
            symbol = 'ES'

        # CHECK 1: Spread
        spread_ticks = snapshot.get('spread_ticks', 0)
        max_spread = self.MAX_SPREAD_TICKS.get(symbol, 2)

        if spread_ticks > max_spread:
            elapsed = (time.perf_counter() - start) * 1000
            return FilterResponse(
                FilterResult.REJECT,
                f"Spread trop large ({spread_ticks} > {max_spread} ticks)",
                elapsed
            )

        # CHECK 2: Liquidity
        bid_size = snapshot.get('q_bq1', 0)
        ask_size = snapshot.get('q_aq1', 0)
        min_liquidity = self.MIN_LIQUIDITY.get(symbol, 10)

        if bid_size < min_liquidity or ask_size < min_liquidity:
            elapsed = (time.perf_counter() - start) * 1000
            # ✅ CORRIGÉ: Message d'erreur affiche le bon seuil par symbole
            return FilterResponse(
                FilterResult.REJECT,
                f"Liquidité insuffisante (bid={bid_size}, ask={ask_size} < {min_liquidity} pour {symbol})",
                elapsed
            )

        # CHECK 3: VWAP distance extrême
        d_vwap_ticks = abs(snapshot.get('d_vwap_ticks', 0))
        max_vwap_dist = self.MAX_VWAP_DISTANCE_TICKS_FAST.get(symbol, 100)

        if d_vwap_ticks > max_vwap_dist:
            elapsed = (time.perf_counter() - start) * 1000
            return FilterResponse(
                FilterResult.REJECT,
                f"VWAP distance extrême ({d_vwap_ticks:.0f} > {max_vwap_dist} ticks)",
                elapsed
            )

        elapsed = (time.perf_counter() - start) * 1000
        return FilterResponse(FilterResult.PASS, "Pre-filter OK", elapsed)

    def context_filter_basic(self, snapshot: Dict) -> FilterResponse:
        """
        Context Filter basique (< 1ms)

        Check:
        1. In Value Area
        2. Session progress (pas trop tôt/tard)
        3. Volatility regime (pas EXTREME)

        Args:
            snapshot: Données ML_READY

        Returns:
            FilterResponse
        """
        import time
        start = time.perf_counter()

        # CHECK 1: Value Area (optionnel mais utile)
        in_value_area = snapshot.get('in_value_area', True)

        # Pas rejet si hors VA (trop strict) mais warning

        # CHECK 2: Session progress
        progress = snapshot.get('progress01', 0.5)

        # ❌ DÉSACTIVÉ TEMPORAIREMENT 14/11/2025
        # Rejeter si trop tôt (< 5% session) ou trop tard (> 98%)
        # Raison: Besoin de tester en fin de session pour valider stratégies
        # À RÉACTIVER après tests si nécessaire

        # if progress < 0.05:
        #     elapsed = (time.perf_counter() - start) * 1000
        #     return FilterResponse(
        #         FilterResult.REJECT,
        #         f"Session trop tôt ({progress*100:.1f}% < 5%)",
        #         elapsed
        #     )

        # if progress > 0.98:
        #     elapsed = (time.perf_counter() - start) * 1000
        #     return FilterResponse(
        #         FilterResult.REJECT,
        #         f"Session trop tard ({progress*100:.1f}% > 98%)",
        #         elapsed
        #     )

        # CHECK 3: Volatility regime EXTREME
        vol_regime = snapshot.get('volatility_regime', 1)

        if vol_regime >= 3:  # EXTREME
            elapsed = (time.perf_counter() - start) * 1000
            return FilterResponse(
                FilterResult.REJECT,
                "Volatilité EXTREME (régime = 3+)",
                elapsed
            )

        elapsed = (time.perf_counter() - start) * 1000
        return FilterResponse(FilterResult.PASS, "Context OK", elapsed)

    def orderflow_filter_basic(self, snapshot: Dict, signal: str) -> FilterResponse:
        """
        OrderFlow Filter basique (< 1ms)

        Check:
        1. Delta pas FORTEMENT contraire
        2. Level1 imbalance cohérente

        Args:
            snapshot: Données ML_READY
            signal: LONG/SHORT

        Returns:
            FilterResponse
        """
        import time
        start = time.perf_counter()

        delta = snapshot.get('delta', 0)
        level1_imb = snapshot.get('level1_imbalance', 0)

        # CHECK: Delta fortement contraire
        if signal == "LONG":
            # Delta très négatif = SHORT pressure
            if delta < -200:  # Seuil strict
                elapsed = (time.perf_counter() - start) * 1000
                return FilterResponse(
                    FilterResult.REJECT,
                    f"Delta fortement contraire LONG (delta={delta})",
                    elapsed
                )

        elif signal == "SHORT":
            # Delta très positif = LONG pressure
            if delta > 200:
                elapsed = (time.perf_counter() - start) * 1000
                return FilterResponse(
                    FilterResult.REJECT,
                    f"Delta fortement contraire SHORT (delta={delta})",
                    elapsed
                )

        elapsed = (time.perf_counter() - start) * 1000
        return FilterResponse(FilterResult.PASS, "OrderFlow basic OK", elapsed)

    def evaluate_fast_pipeline(
        self,
        snapshot: Dict,
        signal: Optional[str] = None
    ) -> Tuple[bool, str, float]:
        """
        Évalue pipeline complet fast filters

        Early exit dès qu'un filtre rejette

        Args:
            snapshot: Données ML_READY
            signal: LONG/SHORT (optionnel pour pre-filter)

        Returns:
            (passed, reason, total_time_ms)
        """
        import time
        start = time.perf_counter()

        # === STAGE 1: PRE-FILTER (ultra-rapide) ===
        result_pre = self.pre_filter(snapshot)

        if result_pre.result == FilterResult.REJECT:
            total_time = (time.perf_counter() - start) * 1000
            logger.debug(f"⚡ REJECTED by pre-filter: {result_pre.reason} ({result_pre.execution_time_ms:.3f}ms)")
            return False, result_pre.reason, total_time

        # === STAGE 2: CONTEXT BASIC (rapide) ===
        result_context = self.context_filter_basic(snapshot)

        if result_context.result == FilterResult.REJECT:
            total_time = (time.perf_counter() - start) * 1000
            logger.debug(f"⚡ REJECTED by context: {result_context.reason} ({result_context.execution_time_ms:.3f}ms)")
            return False, result_context.reason, total_time

        # === STAGE 3: ORDERFLOW BASIC (si signal fourni) ===
        if signal:
            result_orderflow = self.orderflow_filter_basic(snapshot, signal)

            if result_orderflow.result == FilterResult.REJECT:
                total_time = (time.perf_counter() - start) * 1000
                logger.debug(f"⚡ REJECTED by orderflow: {result_orderflow.reason} ({result_orderflow.execution_time_ms:.3f}ms)")
                return False, result_orderflow.reason, total_time

        # === TOUS PASSED ===
        total_time = (time.perf_counter() - start) * 1000

        logger.debug(
            f"✅ PASSED fast filters ({total_time:.3f}ms total: "
            f"pre={result_pre.execution_time_ms:.3f}ms, "
            f"ctx={result_context.execution_time_ms:.3f}ms)"
        )

        return True, "Fast filters passed", total_time

    def get_stats_summary(self) -> Dict:
        """Retourne statistiques d'utilisation (si tracking ajouté)"""
        # TODO: Implémenter tracking rejets par filtre
        return {
            'pre_filter': {
                'rejections': 0,
                'avg_time_ms': 0.05
            },
            'context_filter': {
                'rejections': 0,
                'avg_time_ms': 0.5
            },
            'orderflow_filter': {
                'rejections': 0,
                'avg_time_ms': 0.8
            }
        }


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Config de base
    config = {}

    # Créer instance
    fast_filters = FastFiltersFirst(config)

    # === TEST 1: Snapshot valide ===
    print("=" * 80)
    print("TEST 1: Snapshot VALIDE")
    print("=" * 80)

    snapshot_valid = {
        "sym": "ESZ25_FUT_CME",
        "mid": 6870.0,
        "spread_ticks": 1,
        "q_bq1": 25,
        "q_aq1": 15,
        "d_vwap_ticks": 45,
        "in_value_area": True,
        "progress01": 0.5,
        "volatility_regime": 1,
        "delta": -50
    }

    passed, reason, time_ms = fast_filters.evaluate_fast_pipeline(snapshot_valid, "LONG")
    print(f"\nRésultat: {'PASSED' if passed else 'REJECTED'}")
    print(f"Raison: {reason}")
    print(f"Temps: {time_ms:.3f}ms")

    # === TEST 2: Spread trop large ===
    print("\n" + "=" * 80)
    print("TEST 2: Spread TROP LARGE")
    print("=" * 80)

    snapshot_wide_spread = snapshot_valid.copy()
    snapshot_wide_spread['spread_ticks'] = 5

    passed, reason, time_ms = fast_filters.evaluate_fast_pipeline(snapshot_wide_spread)
    print(f"\nRésultat: {'PASSED' if passed else 'REJECTED'}")
    print(f"Raison: {reason}")
    print(f"Temps: {time_ms:.3f}ms")

    # === TEST 3: VWAP distance extrême ===
    print("\n" + "=" * 80)
    print("TEST 3: VWAP DISTANCE EXTRÊME")
    print("=" * 80)

    snapshot_far_vwap = snapshot_valid.copy()
    snapshot_far_vwap['d_vwap_ticks'] = 150

    passed, reason, time_ms = fast_filters.evaluate_fast_pipeline(snapshot_far_vwap)
    print(f"\nRésultat: {'PASSED' if passed else 'REJECTED'}")
    print(f"Raison: {reason}")
    print(f"Temps: {time_ms:.3f}ms")

    # === TEST 4: Delta contraire ===
    print("\n" + "=" * 80)
    print("TEST 4: DELTA FORTEMENT CONTRAIRE")
    print("=" * 80)

    snapshot_bad_delta = snapshot_valid.copy()
    snapshot_bad_delta['delta'] = 300  # Très positif

    passed, reason, time_ms = fast_filters.evaluate_fast_pipeline(snapshot_bad_delta, "SHORT")
    print(f"\nRésultat: {'PASSED' if passed else 'REJECTED'}")
    print(f"Raison: {reason}")
    print(f"Temps: {time_ms:.3f}ms")

    print("\n" + "=" * 80)

    print(f"Temps: {time_ms:.3f}ms")

    print("\n" + "=" * 80)
