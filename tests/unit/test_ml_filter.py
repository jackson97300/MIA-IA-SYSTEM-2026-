#!/usr/bin/env python3
"""
Tests unitaires pour ML3LayerFilter
VERSION CORRIGÉE - Basée sur le code réel
"""

import pytest
import sys
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.ml_3layer_filter import ML3LayerFilter, TradeSignal, Layer1Result, Layer2Result, Layer3Result, TradeDecision


class TestML3LayerInitialization:
    """Tests d'initialisation"""

    def test_init_creates_filter(self):
        """Doit initialiser le filtre correctement"""
        ml_filter = ML3LayerFilter()
        assert ml_filter is not None


class TestLayer1MenthorQ:
    """Tests Layer 1 (MenthorQ) - 50% du score"""

    @pytest.fixture
    def ml_filter(self):
        return ML3LayerFilter()

    @pytest.fixture
    def complete_snapshot(self):
        """Snapshot complet avec toutes les données MenthorQ"""
        return {
            'symbol': 'ES',
            'mid': 6250.0,
            'tick_size': 0.25,
            # Next wall
            'next_wall': {'side': 'call', 'dist_ticks': 50, 'strength': 0.8},
            # Distances MenthorQ
            'menthor_distances': {'call': 100, 'put': -500, 'hvl': -300},
            # Gamma
            'gamma_wall_level': 6300,
            'call_resistance': 6300,
            'put_support': 6150,
            'hvl': 6200,
            # Confluence
            'blind_spot_confluence': True,
            # GEX levels
            'gex_1': 6200, 'gex_2': 6250, 'gex_3': 6300,
            # Blind spots
            'blind_spot_0': 6180, 'blind_spot_1': 6220,
            # OrderFlow
            'delta': 150,
            'bidPct': 0.65,
            'askPct': 0.35,
            'deltaPct': 0.30,
            'level1_imbalance': 0.5,
            'depth_imbalance': 0.4,
            'institutional_pressure': 0.3,
            'smart_money_flow': 0.25,
            'battle_navale_signal_strength': 0.05,
            'battle_navale_confidence': 0.06,
            # Context
            'vwap': 6240.0,
            'd_vwap': 10.0,
            'd_vwap_ticks': 40,
            'vva': {'val': 6200, 'vah': 6280, 'vpoc': 6240},
            'in_value_area': True,
            'atr': 10.0,
            'd_vwap_atr': 1.0,
            'vix': 15.0
        }

    def test_validate_layer1_returns_layer1result(self, ml_filter, complete_snapshot):
        """validate_layer1_menthorq doit retourner Layer1Result"""
        result = ml_filter.validate_layer1_menthorq(complete_snapshot)

        assert isinstance(result, Layer1Result)
        assert hasattr(result, 'signal')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'triggers')
        assert hasattr(result, 'breakdown')

    def test_layer1_confidence_range(self, ml_filter, complete_snapshot):
        """Layer 1 confidence doit être entre 0 et 0.5 (50% max)"""
        result = ml_filter.validate_layer1_menthorq(complete_snapshot)

        assert 0.0 <= result.confidence <= 0.5


class TestLayer2OrderFlow:
    """Tests Layer 2 (OrderFlow) - 30% du score"""

    @pytest.fixture
    def ml_filter(self):
        return ML3LayerFilter()

    @pytest.fixture
    def orderflow_snapshot(self):
        """Snapshot avec données OrderFlow"""
        return {
            'symbol': 'ES',
            'mid': 6250.0,
            'tick_size': 0.25,
            # OrderFlow
            'delta': 150,
            'bidPct': 0.65,
            'askPct': 0.35,
            'deltaPct': 0.30,
            'level1_imbalance': 0.5,
            'depth_imbalance': 0.4,
            'institutional_pressure': 0.3,
            'smart_money_flow': 0.25,
            'battle_navale_signal_strength': 0.05,
            'battle_navale_confidence': 0.06,
            'volume': 1000
        }

    def test_validate_layer2_returns_layer2result(self, ml_filter, orderflow_snapshot):
        """validate_layer2_orderflow doit retourner Layer2Result"""
        # Layer 2 nécessite menthorq_signal de Layer 1
        menthorq_signal = TradeSignal.LONG

        result = ml_filter.validate_layer2_orderflow(orderflow_snapshot, menthorq_signal)

        assert isinstance(result, Layer2Result)
        assert hasattr(result, 'validated')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'validations')
        assert hasattr(result, 'metrics')

    def test_layer2_confidence_range(self, ml_filter, orderflow_snapshot):
        """Layer 2 confidence doit être entre 0 et 0.3 (30% max)"""
        result = ml_filter.validate_layer2_orderflow(orderflow_snapshot, TradeSignal.LONG)

        assert 0.0 <= result.confidence <= 0.3


class TestLayer3Context:
    """Tests Layer 3 (Context) - 20% du score"""

    @pytest.fixture
    def ml_filter(self):
        return ML3LayerFilter()

    @pytest.fixture
    def context_snapshot(self):
        """Snapshot avec données Context"""
        return {
            'symbol': 'ES',
            'mid': 6250.0,
            'tick_size': 0.25,
            # Context
            'vwap': 6240.0,
            'd_vwap': 10.0,
            'd_vwap_ticks': 40,
            'vva': {'val': 6200, 'vah': 6280, 'vpoc': 6240},
            'in_value_area': True,
            'atr': 10.0,
            'd_vwap_atr': 1.0,
            'vix': 15.0
        }

    def test_validate_layer3_returns_layer3result(self, ml_filter, context_snapshot):
        """validate_layer3_context doit retourner Layer3Result"""
        result = ml_filter.validate_layer3_context(
            context_snapshot,
            menthorq_signal=TradeSignal.LONG,
            layer1_confidence=0.3,
            layer2_confidence=0.2
        )

        assert isinstance(result, Layer3Result)
        assert hasattr(result, 'favorable')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'warnings')

    def test_layer3_confidence_range(self, ml_filter, context_snapshot):
        """Layer 3 confidence doit être entre 0 et 0.2 (20% max)"""
        result = ml_filter.validate_layer3_context(
            context_snapshot,
            TradeSignal.LONG,
            0.3, 0.2
        )

        assert 0.0 <= result.confidence <= 0.2


class TestEvaluateTrade:
    """Tests de evaluate_trade (méthode principale)"""

    @pytest.fixture
    def ml_filter(self):
        return ML3LayerFilter()

    @pytest.fixture
    def complete_snapshot(self):
        """Snapshot complet pour évaluation avec liquidité"""
        return {
            'symbol': 'ES',
            'mid': 6250.0,
            'tick_size': 0.25,
            # Liquidité (pour passer fast filter)
            'dom_bq1': 10,
            'dom_aq1': 10,
            'spread_ticks': 1,
            # MenthorQ
            'next_wall': {'side': 'call', 'dist_ticks': 50, 'strength': 0.8},
            'menthor_distances': {'call': 100, 'put': -500, 'hvl': -300},
            'gamma_wall_level': 6300,
            'call_resistance': 6300,
            'put_support': 6150,
            'hvl': 6200,
            'blind_spot_confluence': True,
            'gex_1': 6200, 'gex_2': 6250, 'gex_3': 6300,
            'blind_spot_0': 6180, 'blind_spot_1': 6220,
            # OrderFlow
            'delta': 150,
            'bidPct': 0.65,
            'askPct': 0.35,
            'deltaPct': 0.30,
            'level1_imbalance': 0.5,
            'depth_imbalance': 0.4,
            'institutional_pressure': 0.3,
            'smart_money_flow': 0.25,
            'battle_navale_signal_strength': 0.05,
            'battle_navale_confidence': 0.06,
            'volume': 1000,
            # Context
            'vwap': 6240.0,
            'd_vwap': 10.0,
            'd_vwap_ticks': 40,
            'vva': {'val': 6200, 'vah': 6280, 'vpoc': 6240},
            'in_value_area': True,
            'atr': 10.0,
            'd_vwap_atr': 1.0,
            'vix': 15.0
        }

    def test_evaluate_trade_returns_trade_decision(self, ml_filter, complete_snapshot):
        """evaluate_trade doit retourner TradeDecision"""
        result = ml_filter.evaluate_trade(complete_snapshot)

        assert isinstance(result, TradeDecision)
        assert hasattr(result, 'should_trade')
        assert hasattr(result, 'action')  # action, pas signal
        assert hasattr(result, 'total_confidence')  # total_confidence, pas confidence

    def test_evaluate_trade_confidence_range(self, ml_filter, complete_snapshot):
        """Total confidence doit être entre 0 et 1"""
        result = ml_filter.evaluate_trade(complete_snapshot)

        assert 0.0 <= result.total_confidence <= 1.0


class TestTradeSignalEnum:
    """Tests de l'enum TradeSignal"""

    def test_trade_signal_values(self):
        """TradeSignal doit avoir LONG, SHORT, NONE"""
        assert hasattr(TradeSignal, 'LONG')
        assert hasattr(TradeSignal, 'SHORT')
        assert hasattr(TradeSignal, 'NONE')


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TESTS UNITAIRES - ML 3-LAYER FILTER")
    print("=" * 80)

    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-ra",
        "--color=yes"
    ])

    print()
    print("=" * 80)
    if exit_code == 0:
        print("✅ TOUS LES TESTS PASSENT")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
    print("=" * 80)

    sys.exit(exit_code)
