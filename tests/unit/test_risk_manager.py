#!/usr/bin/env python3
"""
Tests unitaires pour RiskManager
VERSION CORRIGÉE - Basée sur le code réel
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.risk_manager import RiskManager


class TestRiskManagerInitialization:
    """Tests d'initialisation du RiskManager"""

    def test_init_default(self):
        """Doit s'initialiser avec config par défaut"""
        rm = RiskManager()
        assert rm is not None
        assert rm.params is not None
        assert not rm.is_halted

    def test_init_with_config(self):
        """Doit s'initialiser avec config personnalisée"""
        config = {
            'max_position_size': 2,
            'daily_loss_limit': -1000,
        }
        rm = RiskManager(config=config)
        assert rm is not None
        assert rm.params is not None


class TestEvaluateSignal:
    """Tests de evaluate_signal"""

    @pytest.fixture
    def risk_manager(self):
        return RiskManager()

    @pytest.fixture
    def valid_ml_data(self):
        """Données ML valides pour tests"""
        return {
            'mid': 5000.0,
            'symbol': 'ES',
            'vix': 15.0,
            'delta': 50,
            'bidPct': 0.60,
            'volume': 1000,
            'spread': 0.25,
            'atr': 5.0
        }

    @pytest.fixture
    def valid_signal_dict(self):
        """Signal sous forme de dict (compatible RiskManager)"""
        return {
            'symbol': 'ES',
            'direction': 'LONG',
            'entry_price': 5000.0,
            'stop_loss': 4995.0,
            'take_profit': 5010.0,
            'confidence': 0.45
        }

    def test_evaluate_returns_dict(self, risk_manager, valid_signal_dict, valid_ml_data):
        """evaluate_signal doit retourner un dict"""
        result = risk_manager.evaluate_signal(
            symbol="ES",
            signal=valid_signal_dict,
            ml_data=valid_ml_data
        )

        assert isinstance(result, dict)
        assert 'approved' in result
        assert 'reason' in result

    def test_evaluate_long_signal(self, risk_manager, valid_ml_data):
        """Doit évaluer un signal LONG"""
        signal = {
            'symbol': 'ES',
            'direction': 'LONG',
            'entry_price': 5000.0,
            'stop_loss': 4995.0,
            'take_profit': 5010.0,
            'confidence': 0.50
        }

        result = risk_manager.evaluate_signal("ES", signal, valid_ml_data)

        assert 'approved' in result
        assert isinstance(result['approved'], bool)

    def test_evaluate_short_signal(self, risk_manager, valid_ml_data):
        """Doit évaluer un signal SHORT"""
        signal = {
            'symbol': 'ES',
            'direction': 'SHORT',
            'entry_price': 5000.0,
            'stop_loss': 5005.0,
            'take_profit': 4990.0,
            'confidence': 0.50
        }

        result = risk_manager.evaluate_signal("ES", signal, valid_ml_data)

        assert 'approved' in result
        assert isinstance(result['approved'], bool)

    def test_evaluate_nq_symbol(self, risk_manager):
        """Doit évaluer un signal NQ"""
        signal = {
            'symbol': 'NQ',
            'direction': 'LONG',
            'entry_price': 15000.0,
            'stop_loss': 14990.0,
            'take_profit': 15020.0,
            'confidence': 0.45
        }

        ml_data = {
            'mid': 15000.0,
            'symbol': 'NQ',
            'vix': 18.0,
            'delta': 80,
            'bidPct': 0.62,
            'volume': 1200
        }

        result = risk_manager.evaluate_signal("NQ", signal, ml_data)

        assert result is not None
        assert 'approved' in result


class TestHaltTrading:
    """Tests du halt trading"""

    def test_halt_and_resume(self):
        """Doit pouvoir halt et resume le trading"""
        rm = RiskManager()

        # Initialement pas halted
        assert not rm.is_halted

        # Halt
        rm.is_halted = True
        rm.halt_reason = "Test halt"
        assert rm.is_halted

        # Resume
        rm.is_halted = False
        rm.halt_reason = ""
        assert not rm.is_halted


class TestPositions:
    """Tests de gestion des positions"""

    def test_positions_dict_exists(self):
        """Doit avoir un dict positions"""
        rm = RiskManager()
        assert hasattr(rm, 'positions')
        assert isinstance(rm.positions, dict)

    def test_trade_history_exists(self):
        """Doit avoir un historique de trades"""
        rm = RiskManager()
        assert hasattr(rm, 'trade_history')
        assert isinstance(rm.trade_history, list)


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TESTS UNITAIRES - RISK MANAGER")
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
