#!/usr/bin/env python3
"""
Tests unitaires pour SessionQualityMonitor
VERSION CORRIGÉE - Basée sur le code réel
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.session_quality_monitor import SessionQualityMonitor


class TestSessionQualityInitialization:
    """Tests d'initialisation"""

    def test_init_default(self):
        """Doit s'initialiser avec params par défaut"""
        monitor = SessionQualityMonitor()
        assert monitor is not None
        assert monitor.enable_london == True
        assert monitor.enable_us == True

    def test_init_london_disabled(self):
        """Doit pouvoir désactiver London"""
        monitor = SessionQualityMonitor(enable_london=False)
        assert monitor.enable_london == False
        assert monitor.enable_us == True

    def test_init_test_mode(self):
        """Doit pouvoir activer test_mode"""
        monitor = SessionQualityMonitor(test_mode=True)
        assert monitor.test_mode == True


class TestCheckCanTrade:
    """Tests de check_can_trade"""

    @pytest.fixture
    def monitor(self):
        return SessionQualityMonitor()

    @pytest.fixture
    def valid_snapshot(self):
        """Snapshot valide pour tests"""
        return {
            'mid': 5000.0,
            'symbol': 'ES',
            'spread': 0.25,
            'spread_ticks': 1,
            'volume': 1000,
            'session_id': 'US',
            'progress01': 0.5,
            'vix': 15.0
        }

    def test_check_returns_tuple(self, monitor, valid_snapshot):
        """check_can_trade doit retourner un tuple (bool, str, float)"""
        result = monitor.check_can_trade(valid_snapshot)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)  # can_trade
        assert isinstance(result[1], str)   # reason
        assert isinstance(result[2], (int, float))  # quality_score

    def test_check_with_now_param(self, monitor, valid_snapshot):
        """Doit accepter un paramètre now"""
        paris_tz = ZoneInfo("Europe/Paris")
        now = datetime(2025, 12, 2, 16, 0, tzinfo=paris_tz)  # Lundi 16h Paris

        result = monitor.check_can_trade(valid_snapshot, now=now)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_quality_score_range(self, monitor, valid_snapshot):
        """Quality score doit être entre 0 et 100"""
        can_trade, reason, score = monitor.check_can_trade(valid_snapshot)

        assert 0 <= score <= 100


class TestTestMode:
    """Tests du mode test"""

    def test_test_mode_bypasses_hours(self):
        """test_mode doit bypass les restrictions horaires"""
        monitor = SessionQualityMonitor(test_mode=True)

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

        # 03:00 Paris - normalement bloqué
        paris_tz = ZoneInfo("Europe/Paris")
        now = datetime(2025, 12, 2, 3, 0, tzinfo=paris_tz)

        can_trade, reason, score = monitor.check_can_trade(snapshot, now=now)

        # En test_mode, devrait autoriser
        assert can_trade == True


class TestTradingHours:
    """Tests des horaires de trading"""

    @pytest.fixture
    def monitor(self):
        return SessionQualityMonitor(enable_london=True, enable_us=True)

    @pytest.fixture
    def valid_snapshot(self):
        return {
            'mid': 5000.0,
            'symbol': 'ES',
            'spread': 0.25,
            'spread_ticks': 1,
            'volume': 1000,
            'session_id': 'US',
            'progress01': 0.5,
            'vix': 15.0
        }

    def test_us_morning_allowed(self, monitor, valid_snapshot):
        """US Morning (15:50-17:00 Paris) doit être autorisé"""
        paris_tz = ZoneInfo("Europe/Paris")
        now = datetime(2025, 12, 2, 16, 0, tzinfo=paris_tz)  # Lundi 16h Paris

        can_trade, reason, score = monitor.check_can_trade(valid_snapshot, now=now)

        # Devrait autoriser pendant US Morning
        assert can_trade == True or "spread" in reason.lower() or "volume" in reason.lower()

    def test_power_hour_allowed(self, monitor, valid_snapshot):
        """Power Hour (20:00-21:30 Paris) doit être autorisé"""
        paris_tz = ZoneInfo("Europe/Paris")
        now = datetime(2025, 12, 2, 20, 30, tzinfo=paris_tz)  # Lundi 20h30 Paris

        can_trade, reason, score = monitor.check_can_trade(valid_snapshot, now=now)

        # Devrait autoriser pendant Power Hour
        assert can_trade == True or "spread" in reason.lower() or "volume" in reason.lower()

    def test_lunch_blocked(self, monitor, valid_snapshot):
        """Lunch (17:00-19:30 Paris) doit être bloqué"""
        paris_tz = ZoneInfo("Europe/Paris")
        now = datetime(2025, 12, 2, 18, 0, tzinfo=paris_tz)  # Lundi 18h Paris

        can_trade, reason, score = monitor.check_can_trade(valid_snapshot, now=now)

        # Devrait bloquer pendant lunch
        assert can_trade == False


class TestDailyStats:
    """Tests des statistiques journalières"""

    def test_daily_stats_exists(self):
        """Doit avoir des stats journalières"""
        monitor = SessionQualityMonitor()
        assert hasattr(monitor, 'daily_stats')
        assert isinstance(monitor.daily_stats, dict)

    def test_total_checks_increments(self):
        """total_checks doit s'incrémenter"""
        monitor = SessionQualityMonitor()

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

        initial = monitor.daily_stats.get('total_checks', 0)
        monitor.check_can_trade(snapshot)
        assert monitor.daily_stats['total_checks'] == initial + 1


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TESTS UNITAIRES - SESSION QUALITY MONITOR")
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
