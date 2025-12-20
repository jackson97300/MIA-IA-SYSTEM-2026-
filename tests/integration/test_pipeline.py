#!/usr/bin/env python3
"""
Tests d'intégration pour la pipeline complète
VERSION CORRIGÉE - Basée sur le code réel
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.risk_manager import RiskManager
from core.session_quality_monitor import SessionQualityMonitor
from ml.ml_3layer_filter import ML3LayerFilter, TradeDecision


class TestPipelineComponents:
    """Tests que tous les composants s'initialisent"""

    def test_risk_manager_init(self):
        """RiskManager doit s'initialiser"""
        rm = RiskManager()
        assert rm is not None

    def test_session_monitor_init(self):
        """SessionQualityMonitor doit s'initialiser"""
        sm = SessionQualityMonitor()
        assert sm is not None

    def test_ml_filter_init(self):
        """ML3LayerFilter doit s'initialiser"""
        ml = ML3LayerFilter()
        assert ml is not None


class TestPipelineFlow:
    """Tests du flux de la pipeline"""

    @pytest.fixture
    def complete_snapshot(self):
        """Snapshot complet pour tests d'intégration"""
        return {
            'symbol': 'ES',
            'mid': 6250.0,
            'tick_size': 0.25,
            # Liquidité
            'dom_bq1': 10,
            'dom_aq1': 10,
            'spread': 0.25,
            'spread_ticks': 1,
            'volume': 1000,
            'session_id': 'US',
            'progress01': 0.5,
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

    def test_session_then_ml_flow(self, complete_snapshot):
        """Session check puis ML filter"""
        # 1. Session check
        session_monitor = SessionQualityMonitor(test_mode=True)  # test_mode pour bypass horaires
        can_trade, reason, score = session_monitor.check_can_trade(complete_snapshot)

        assert can_trade == True  # test_mode autorise tout

        # 2. ML filter
        ml_filter = ML3LayerFilter()
        decision = ml_filter.evaluate_trade(complete_snapshot)

        assert isinstance(decision, TradeDecision)
        assert hasattr(decision, 'should_trade')

    def test_ml_then_risk_flow(self, complete_snapshot):
        """ML filter puis Risk Manager"""
        # 1. ML filter
        ml_filter = ML3LayerFilter()
        decision = ml_filter.evaluate_trade(complete_snapshot)

        # 2. Risk Manager
        risk_manager = RiskManager()

        signal = {
            'symbol': 'ES',
            'direction': 'LONG',
            'entry_price': 6250.0,
            'stop_loss': 6245.0,
            'take_profit': 6260.0,
            'confidence': decision.total_confidence
        }

        result = risk_manager.evaluate_signal("ES", signal, complete_snapshot)

        assert isinstance(result, dict)
        assert 'approved' in result


class TestPipelineProtections:
    """Tests des protections de la pipeline"""

    def test_lunch_blocked(self):
        """Lunch doit bloquer le trading"""
        session_monitor = SessionQualityMonitor()

        snapshot = {
            'mid': 5000.0,
            'symbol': 'ES',
            'spread': 0.25,
            'spread_ticks': 1,
            'volume': 1000,
            'session_id': 'US',
            'progress01': 0.5,
            'vix': 15.0
        }

        # 18:00 Paris = Lunch
        paris_tz = ZoneInfo("Europe/Paris")
        now = datetime(2025, 12, 2, 18, 0, tzinfo=paris_tz)

        can_trade, reason, score = session_monitor.check_can_trade(snapshot, now=now)

        assert can_trade == False

    def test_risk_manager_not_halted_by_default(self):
        """RiskManager ne doit pas être halted par défaut"""
        rm = RiskManager()
        assert rm.is_halted == False


class TestPipelineIntegrity:
    """Tests d'intégrité de la pipeline"""

    def test_all_modules_have_required_methods(self):
        """Tous les modules doivent avoir les méthodes requises"""
        # RiskManager
        rm = RiskManager()
        assert hasattr(rm, 'evaluate_signal')
        assert callable(rm.evaluate_signal)

        # SessionQualityMonitor
        sm = SessionQualityMonitor()
        assert hasattr(sm, 'check_can_trade')
        assert callable(sm.check_can_trade)

        # ML3LayerFilter
        ml = ML3LayerFilter()
        assert hasattr(ml, 'evaluate_trade')
        assert callable(ml.evaluate_trade)
        assert hasattr(ml, 'validate_layer1_menthorq')
        assert callable(ml.validate_layer1_menthorq)
        assert hasattr(ml, 'validate_layer2_orderflow')
        assert callable(ml.validate_layer2_orderflow)
        assert hasattr(ml, 'validate_layer3_context')
        assert callable(ml.validate_layer3_context)


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TESTS D'INTÉGRATION - PIPELINE COMPLÈTE")
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
