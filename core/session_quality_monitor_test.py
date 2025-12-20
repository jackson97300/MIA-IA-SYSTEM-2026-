"""
Session Quality Monitor - VERSION COMPLÈTE ET ROBUSTE

Filtre qualité market avant chaque trade.
Horaires validés: London (optionnel) + US Morning + US Power Hour
Hard stops: 21:30, Lunch, Overnight

⚠️ VERSION NON-REDONDANTE:
- Ne check PAS confluence (déjà fait par menthorq_3layer_strategy.py)
- Ne check PAS MenthorQ (déjà fait par menthorq_3layer_strategy.py)
- Check uniquement: horaires, spread, volume, session progress, stop hunts

Author: Jackson Trading System
Date: 26 Novembre 2025
Version: 2.0 - Production Ready
"""

import logging
from datetime import datetime
from typing import Tuple, Dict, Optional
import pytz

logger = logging.getLogger(__name__)


class SessionQualityMonitor:
    """
    Session Quality Monitor - Gate Keeper.

    Filtre trading selon:
    1. Horaires validés (London optionnel + US)
    2. Conditions market (spread, volume, session progress)
    3. Stop hunts tracking

    Returns:
        (can_trade: bool, block_reason: str, quality_score: float)

    Exemple:
        monitor = SessionQualityMonitor(enable_london=True)
        can_trade, reason, score = monitor.check_can_trade(snapshot)
        if not can_trade:
            logger.info(f"⛔ Blocked: {reason}")
            return None
    """

    def __init__(self, enable_london: bool = True, enable_us: bool = True):
        """
        Initialize Session Quality Monitor.

        Args:
            enable_london: bool - Activer session London (08:00-11:00)?
            enable_us: bool - Activer sessions US (15:50-17:00 + 20:00-21:30)?
        """

        # ═══════════════════════════════════════════════════════════════
        # CONFIGURATION HORAIRES (Paris time)
        # ═══════════════════════════════════════════════════════════════

        self.enable_london = enable_london
        self.enable_us = enable_us

        # Horaires de trading (heures Paris)
        self.TRADING_HOURS = {
            # London (optionnel)
            'london': {
                'enabled': enable_london,
                'start_hour': 8,
                'start_minute': 0,
                'end_hour': 11,
                'end_minute': 0,
                'description': 'London Session',
            },

            # Pre-open pause (NE PAS trader)
            'pre_open_pause': {
                'start_hour': 15,
                'start_minute': 25,
                'end_hour': 15,
                'end_minute': 35,
                'description': 'Pre-Open Pause',
            },

            # OPR observe (NE PAS trader, sauf si OPR strategy active)
            'opr_observe': {
                'start_hour': 15,
                'start_minute': 35,
                'end_hour': 15,
                'end_minute': 50,
                'description': 'OPR Observe',
            },

            # US Morning (TRADE)
            'us_morning': {
                'enabled': enable_us,
                'start_hour': 15,
                'start_minute': 50,
                'end_hour': 17,
                'end_minute': 0,
                'description': 'US Morning',
            },

            # Lunch US (NE PAS trader)
            'lunch': {
                'start_hour': 17,
                'start_minute': 0,
                'end_hour': 19,
                'end_minute': 30,
                'description': 'Lunch US',
            },

            # US Afternoon / Power Hour (TRADE - MEILLEUR)
            'us_afternoon': {
                'enabled': enable_us,
                'start_hour': 20,
                'start_minute': 0,
                'end_hour': 21,
                'end_minute': 30,
                'description': 'US Power Hour',
            },

            # Hard stop
            'hard_stop_hour': 21,
            'hard_stop_minute': 30,
        }

        # ═══════════════════════════════════════════════════════════════
        # THRESHOLDS (non-redondants avec menthorq_3layer)
        # ═══════════════════════════════════════════════════════════════

        # Market quality (pas de check confluence/MenthorQ - redondant)
        self.MIN_VOLUME = 500  # contracts/min minimum
        self.MAX_SPREAD_TICKS = 3  # spread maximum acceptable
        self.MAX_SESSION_PROGRESS = 0.95  # 95% session terminée

        # Stop hunts tracking
        self.MAX_CONSECUTIVE_STOP_HUNTS = 3
        self.consecutive_stop_hunts = 0

        # ═══════════════════════════════════════════════════════════════
        # STATS TRACKING
        # ═══════════════════════════════════════════════════════════════

        self.daily_stats = {
            'total_checks': 0,
            'blocks': 0,
            'allows': 0,
            'block_reasons': {},
            'blocks_by_hour': {},  # Tracking blocks par heure
        }

        logger.info(f"""
╔══════════════════════════════════════════════════════════════
║ ✅ SESSION QUALITY MONITOR INITIALIZED
╠══════════════════════════════════════════════════════════════
║ Configuration:
║   • London Session:     {'ENABLED' if enable_london else 'DISABLED'} (08:00-11:00)
║   • US Sessions:        {'ENABLED' if enable_us else 'DISABLED'} (15:50-17:00 + 20:00-21:30)
║   • Hard Stop:          21:30 Paris
║   • Lunch Block:        17:00-19:30 Paris
║
║ Thresholds:
║   • Min Volume:         {self.MIN_VOLUME} contracts/min
║   • Max Spread:         {self.MAX_SPREAD_TICKS} ticks
║   • Max Session Prog:   {self.MAX_SESSION_PROGRESS:.0%}
║   • Max Stop Hunts:     {self.MAX_CONSECUTIVE_STOP_HUNTS}
║
║ ⚠️ Version NON-REDONDANTE:
║   • Ne check PAS confluence (fait par menthorq_3layer)
║   • Ne check PAS MenthorQ (fait par menthorq_3layer)
╚══════════════════════════════════════════════════════════════
        """)

    def check_can_trade(
        self,
        snapshot: Dict,
        now: Optional[datetime] = None,
        override_opr: bool = False
    ) -> Tuple[bool, str, float]:
        """
        Master check: Peut-on trader?

        Args:
            snapshot: Dict snapshot (format ML_READY ou standard)
            now: datetime optionnel (default = now Paris)
            override_opr: bool - Si True, ignore block OPR observe
                         (utilisé par OPR Strategy)

        Returns:
            (can_trade: bool, block_reason: str, quality_score: float)

        Exemple:
            can_trade, reason, score = monitor.check_can_trade(snapshot)
            if not can_trade:
                logger.info(f"⛔ Blocked: {reason} (score: {score:.0f}/100)")
                return None
        """

        # Initialize now
        if now is None:
            now = datetime.now(pytz.timezone('Europe/Paris'))

        # Ensure Paris timezone
        if now.tzinfo is None:
            now = pytz.timezone('Europe/Paris').localize(now)
        else:
            now = now.astimezone(pytz.timezone('Europe/Paris'))

        self.daily_stats['total_checks'] += 1

        # Calculate quality score
        quality_score = self._calculate_quality_score(snapshot, now)

        # ═══════════════════════════════════════════════════════════════
        # HARD BLOCKS (Non-négociables)
        # ═══════════════════════════════════════════════════════════════

        # 1. Horaires interdits
        block, reason = self._check_trading_hours(now, override_opr)
        if block:
            self._record_block(reason, now)
            return False, reason, quality_score

        # 2. Session progress > 95%
        progress = snapshot.get('session_progress', 0)
        if progress > self.MAX_SESSION_PROGRESS:
            reason = f"Session terminée ({progress:.1%} > {self.MAX_SESSION_PROGRESS:.0%})"
            self._record_block(reason, now)
            return False, reason, quality_score

        # 3. Liquidité insuffisante
        volume = snapshot.get('volume', 0)
        if volume < self.MIN_VOLUME:
            reason = f"Volume insuffisant ({volume} < {self.MIN_VOLUME})"
            self._record_block(reason, now)
            return False, reason, quality_score

        # 4. Spread trop large
        spread = snapshot.get('spread_ticks', 0)
        if spread > self.MAX_SPREAD_TICKS:
            reason = f"Spread large ({spread} > {self.MAX_SPREAD_TICKS} ticks)"
            self._record_block(reason, now)
            return False, reason, quality_score

        # 5. Stop hunts consécutifs
        if self.consecutive_stop_hunts >= self.MAX_CONSECUTIVE_STOP_HUNTS:
            reason = f"Stop hunts consécutifs ({self.consecutive_stop_hunts} >= {self.MAX_CONSECUTIVE_STOP_HUNTS})"
            self._record_block(reason, now)
            return False, reason, quality_score

        # ═══════════════════════════════════════════════════════════════
        # ALL CHECKS PASSED ✅
        # ═══════════════════════════════════════════════════════════════

        self.daily_stats['allows'] += 1

        logger.debug(f"✅ Quality OK - Score: {quality_score:.0f}/100, Session: {self._get_current_session_name(now)}")

        return True, "Quality OK", quality_score

    def _check_trading_hours(self, now: datetime, override_opr: bool = False) -> Tuple[bool, str]:
        """
        Check hard blocks horaires.

        Args:
            now: datetime Paris
            override_opr: bool - Ignore OPR observe block?

        Returns:
            (should_block: bool, reason: str)
        """

        hour = now.hour
        minute = now.minute

        # ═══════════════════════════════════════════════════════════════
        # HARD STOPS (ABSOLU)
        # ═══════════════════════════════════════════════════════════════

        # 1. POST-21:30 (CRITIQUE)
        if hour >= 22 or (hour == 21 and minute >= 30):
            return True, "🛑 POST-21:30 - Hard Stop"

        # 2. OVERNIGHT (avant 08:00)
        if hour < 8:
            return True, "⛔ OVERNIGHT - Market fermé"

        # 3. LUNCH US (17:00-19:30)
        if hour == 17 or hour == 18 or (hour == 19 and minute < 30):
            return True, "🍽️ LUNCH US (17:00-19:30) - Pause"

        # 4. PRE-OPEN PAUSE (15:25-15:35)
        if hour == 15 and 25 <= minute < 35:
            return True, "⏸️ PRE-OPEN PAUSE (15:25-15:35)"

        # 5. OPR OBSERVE (15:35-15:50) - Sauf si override
        if not override_opr:
            if hour == 15 and 35 <= minute < 50:
                return True, "👀 OPR OBSERVE (15:35-15:50) - Attendre setup"

        # ═══════════════════════════════════════════════════════════════
        # SESSIONS VALIDES
        # ═══════════════════════════════════════════════════════════════

        # Check si dans une session valide
        in_valid_session = False

        # London Session (08:00-11:00)
        if self.enable_london:
            if 8 <= hour < 11:
                in_valid_session = True

        # US Morning (15:50-17:00)
        if self.enable_us:
            if (hour == 15 and minute >= 50) or hour == 16:
                in_valid_session = True

        # US Afternoon/Power Hour (20:00-21:30)
        if self.enable_us:
            if hour == 20 or (hour == 21 and minute < 30):
                in_valid_session = True

        # Si pas dans session valide → block
        if not in_valid_session:
            return True, f"⏰ Hors horaires trading ({hour:02d}:{minute:02d})"

        # ═══════════════════════════════════════════════════════════════
        # TRADING AUTORISÉ ✅
        # ═══════════════════════════════════════════════════════════════

        return False, ""

    def _calculate_quality_score(self, snapshot: Dict, now: datetime) -> float:
        """
        Calculate quality score 0-100.

        Score basé sur:
        - Timing session (40pts)
        - Liquidité (30pts)
        - Market conditions (30pts)

        Note: On ne score PAS confluence/MenthorQ (redondant avec menthorq_3layer)

        Args:
            snapshot: Dict snapshot
            now: datetime Paris

        Returns:
            float: Score 0-100
        """

        score = 0.0

        # ══════════════════════════════════════════════════════════════
        # 1. TIMING SESSION (40 points)
        # ══════════════════════════════════════════════════════════════

        hour = now.hour
        minute = now.minute

        # US Power Hour (20:00-21:30) - MEILLEUR
        if hour == 20 or (hour == 21 and minute < 30):
            score += 40
            logger.debug(f"[Quality] Session: US Power Hour (+40pts)")

        # US Morning (15:50-17:00) - TRÈS BON
        elif (hour == 15 and minute >= 50) or hour == 16:
            score += 35
            logger.debug(f"[Quality] Session: US Morning (+35pts)")

        # London (08:00-11:00) - BON
        elif 8 <= hour < 11:
            score += 25
            logger.debug(f"[Quality] Session: London (+25pts)")

        # Pre-afternoon (19:30-20:00) - ACCEPTABLE
        elif hour == 19 and minute >= 30:
            score += 15
            logger.debug(f"[Quality] Session: Pre-Afternoon (+15pts)")

        # Bonus si début de session (plus de momentum)
        progress = snapshot.get('session_progress', 1.0)
        if progress < 0.50:
            score += 5
            logger.debug(f"[Quality] Session début (<50%) (+5pts)")

        # ══════════════════════════════════════════════════════════════
        # 2. LIQUIDITÉ (30 points)
        # ══════════════════════════════════════════════════════════════

        volume = snapshot.get('volume', 0)
        spread = snapshot.get('spread_ticks', 10)

        # Volume scoring
        if volume >= 2500:
            score += 15
            logger.debug(f"[Quality] Volume excellent ({volume}) (+15pts)")
        elif volume >= 1500:
            score += 12
            logger.debug(f"[Quality] Volume très bon ({volume}) (+12pts)")
        elif volume >= 1000:
            score += 8
            logger.debug(f"[Quality] Volume bon ({volume}) (+8pts)")
        elif volume >= 500:
            score += 4
            logger.debug(f"[Quality] Volume acceptable ({volume}) (+4pts)")

        # Spread scoring
        if spread <= 2:
            score += 15
            logger.debug(f"[Quality] Spread excellent ({spread}t) (+15pts)")
        elif spread == 3:
            score += 10
            logger.debug(f"[Quality] Spread acceptable ({spread}t) (+10pts)")
        elif spread <= 5:
            score += 5
            logger.debug(f"[Quality] Spread médiocre ({spread}t) (+5pts)")

        # ══════════════════════════════════════════════════════════════
        # 3. MARKET CONDITIONS (30 points)
        # ══════════════════════════════════════════════════════════════

        # Session progress (10pts)
        if progress < 0.25:
            score += 10
        elif progress < 0.50:
            score += 8
        elif progress < 0.75:
            score += 5
        elif progress < 0.95:
            score += 3

        # VIX volatility (10pts) - si disponible
        vix = snapshot.get('vix', None)
        if vix is not None:
            if 15 <= vix <= 25:
                score += 10  # Sweet spot volatility
            elif 12 <= vix < 15 or 25 < vix <= 30:
                score += 7   # Acceptable
            elif vix < 12 or vix > 30:
                score += 3   # Extrêmes
        else:
            score += 5  # Default si pas de VIX

        # Delta momentum (10pts) - si disponible
        delta = snapshot.get('delta', None)
        cum_delta = snapshot.get('cum_delta_day', None)

        if cum_delta is not None and abs(cum_delta) > 200:
            score += 10  # Fort momentum directionnel
        elif delta is not None and abs(delta) > 50:
            score += 7   # Momentum modéré
        else:
            score += 5   # Default

        return min(100, score)

    def _get_current_session_name(self, now: datetime) -> str:
        """Retourne nom session actuelle."""
        hour = now.hour
        minute = now.minute

        if hour == 20 or (hour == 21 and minute < 30):
            return "US Power Hour"
        elif (hour == 15 and minute >= 50) or hour == 16:
            return "US Morning"
        elif 8 <= hour < 11:
            return "London"
        elif hour == 19 and minute >= 30:
            return "Pre-Afternoon"
        else:
            return "Unknown"

    def _record_block(self, reason: str, now: datetime):
        """Record block pour stats."""
        self.daily_stats['blocks'] += 1

        # Count by reason
        if reason not in self.daily_stats['block_reasons']:
            self.daily_stats['block_reasons'][reason] = 0
        self.daily_stats['block_reasons'][reason] += 1

        # Count by hour
        hour = now.hour
        if hour not in self.daily_stats['blocks_by_hour']:
            self.daily_stats['blocks_by_hour'][hour] = 0
        self.daily_stats['blocks_by_hour'][hour] += 1

    def on_trade_result(self, was_stop_hunt: bool, was_win: bool, pnl: float = 0):
        """
        Callback après trade complété.

        Update stop hunts tracking.

        Args:
            was_stop_hunt: bool - Trade était un stop hunt?
            was_win: bool - Trade gagnant?
            pnl: float - P&L du trade (optionnel)
        """

        if was_stop_hunt:
            self.consecutive_stop_hunts += 1
            logger.warning(f"⚠️ Stop hunt #{self.consecutive_stop_hunts}")

            if self.consecutive_stop_hunts >= self.MAX_CONSECUTIVE_STOP_HUNTS:
                logger.error(f"""
╔══════════════════════════════════════════════════════════════
║ 🚨 ALERTE: {self.consecutive_stop_hunts} STOP HUNTS CONSÉCUTIFS
╠══════════════════════════════════════════════════════════════
║ Trading BLOQUÉ jusqu'à win ou reset manuel
║
║ Cause probable:
║   • Market structure cassée
║   • Algos agressifs actifs
║   • Pause recommandée: 30-60 minutes
╚══════════════════════════════════════════════════════════════
                """)

        elif was_win:
            # Reset stop hunts sur win
            if self.consecutive_stop_hunts > 0:
                logger.info(f"✅ Win trade - Reset stop hunts counter (was {self.consecutive_stop_hunts})")
            self.consecutive_stop_hunts = 0

        else:
            # Losing trade mais pas stop hunt
            # Décrémente légèrement
            self.consecutive_stop_hunts = max(0, self.consecutive_stop_hunts - 1)

    def get_stats(self) -> Dict:
        """
        Retourne stats du jour.

        Returns:
            Dict avec stats complètes
        """

        total = self.daily_stats['total_checks']
        blocks = self.daily_stats['blocks']
        allows = self.daily_stats['allows']

        block_rate = (blocks / total * 100) if total > 0 else 0
        allow_rate = (allows / total * 100) if total > 0 else 0

        return {
            'total_checks': total,
            'blocks': blocks,
            'allows': allows,
            'block_rate_pct': block_rate,
            'allow_rate_pct': allow_rate,
            'consecutive_stop_hunts': self.consecutive_stop_hunts,
            'block_reasons': self.daily_stats['block_reasons'].copy(),
            'blocks_by_hour': self.daily_stats['blocks_by_hour'].copy(),
        }

    def get_stats_report(self) -> str:
        """
        Retourne rapport stats formaté.

        Returns:
            str: Rapport formaté pour logging
        """

        stats = self.get_stats()

        report = f"""
╔══════════════════════════════════════════════════════════════
║ 📊 SESSION QUALITY MONITOR - DAILY STATS
╠══════════════════════════════════════════════════════════════
║ Total Checks:        {stats['total_checks']}
║ Blocks:              {stats['blocks']} ({stats['block_rate_pct']:.1f}%)
║ Allows:              {stats['allows']} ({stats['allow_rate_pct']:.1f}%)
║ Stop Hunts:          {stats['consecutive_stop_hunts']}
║
║ Block Reasons:
"""

        for reason, count in sorted(stats['block_reasons'].items(), key=lambda x: -x[1]):
            report += f"║   • {reason[:45]:<45} {count:>3}\n"

        if stats['blocks_by_hour']:
            report += "║\n║ Blocks by Hour (Paris):\n"
            for hour in sorted(stats['blocks_by_hour'].keys()):
                count = stats['blocks_by_hour'][hour]
                report += f"║   • {hour:02d}:00 - {hour:02d}:59  {count:>3} blocks\n"

        report += "╚══════════════════════════════════════════════════════════════"

        return report

    def reset_daily(self):
        """Reset stats pour nouveau jour."""
        self.daily_stats = {
            'total_checks': 0,
            'blocks': 0,
            'allows': 0,
            'block_reasons': {},
            'blocks_by_hour': {},
        }
        self.consecutive_stop_hunts = 0
        logger.info("🔄 SessionQualityMonitor: Reset daily")

    def reset_stop_hunts(self):
        """Reset stop hunts counter manuellement (si besoin)."""
        old_count = self.consecutive_stop_hunts
        self.consecutive_stop_hunts = 0
        logger.warning(f"🔄 Stop hunts counter RESET manuellement ({old_count} → 0)")


# ═══════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════

def create_session_quality_monitor(
    enable_london: bool = True,
    enable_us: bool = True
) -> SessionQualityMonitor:
    """
    Factory pour créer SessionQualityMonitor.

    Args:
        enable_london: bool - Activer London session? (default: True)
        enable_us: bool - Activer US sessions? (default: True)

    Returns:
        SessionQualityMonitor instance

    Exemple:
        # Avec London + US
        monitor = create_session_quality_monitor(enable_london=True, enable_us=True)

        # US uniquement
        monitor = create_session_quality_monitor(enable_london=False, enable_us=True)
    """
    return SessionQualityMonitor(enable_london=enable_london, enable_us=enable_us)


# ═══════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Tests unitaires du Session Quality Monitor."""

    import pytz
    from datetime import datetime

    print("\n" + "="*70)
    print("TESTS SESSION QUALITY MONITOR")
    print("="*70)

    # Test 1: Création
    print("\n[TEST 1] Création monitor...")
    monitor = create_session_quality_monitor(enable_london=True, enable_us=True)
    print("✅ Monitor créé")

    # Test 2: Hard Stop 21:30
    print("\n[TEST 2] Hard Stop 21:30...")
    paris_tz = pytz.timezone('Europe/Paris')
    now_2130 = datetime(2025, 11, 26, 21, 35, 0, tzinfo=paris_tz)

    snapshot_test = {
        'mid': 25000,
        'volume': 1000,
        'spread_ticks': 2,
        'session_progress': 0.50,
    }

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_2130)
    assert can_trade == False, "Should block after 21:30"
    assert "21:30" in reason or "Hard Stop" in reason
    print(f"✅ Blocked: {reason}")

    # Test 3: US Power Hour OK
    print("\n[TEST 3] US Power Hour (20:30)...")
    now_2030 = datetime(2025, 11, 26, 20, 30, 0, tzinfo=paris_tz)

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_2030)
    assert can_trade == True, "Should allow during Power Hour"
    print(f"✅ Allowed: {reason}, Score: {score:.0f}/100")

    # Test 4: Lunch Block
    print("\n[TEST 4] Lunch US (18:00)...")
    now_1800 = datetime(2025, 11, 26, 18, 0, 0, tzinfo=paris_tz)

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_1800)
    assert can_trade == False, "Should block during lunch"
    assert "LUNCH" in reason
    print(f"✅ Blocked: {reason}")

    # Test 5: Spread trop large
    print("\n[TEST 5] Spread trop large...")
    snapshot_bad_spread = snapshot_test.copy()
    snapshot_bad_spread['spread_ticks'] = 5

    now_ok = datetime(2025, 11, 26, 20, 30, 0, tzinfo=paris_tz)
    can_trade, reason, score = monitor.check_can_trade(snapshot_bad_spread, now_ok)
    assert can_trade == False, "Should block with large spread"
    assert "Spread" in reason
    print(f"✅ Blocked: {reason}")

    # Test 6: Volume insuffisant
    print("\n[TEST 6] Volume insuffisant...")
    snapshot_low_vol = snapshot_test.copy()
    snapshot_low_vol['volume'] = 300

    can_trade, reason, score = monitor.check_can_trade(snapshot_low_vol, now_ok)
    assert can_trade == False, "Should block with low volume"
    assert "Volume" in reason
    print(f"✅ Blocked: {reason}")

    # Test 7: Stop hunts tracking
    print("\n[TEST 7] Stop hunts tracking...")
    monitor.on_trade_result(was_stop_hunt=True, was_win=False)
    monitor.on_trade_result(was_stop_hunt=True, was_win=False)
    monitor.on_trade_result(was_stop_hunt=True, was_win=False)

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_ok)
    assert can_trade == False, "Should block after 3 stop hunts"
    assert "Stop hunts" in reason
    print(f"✅ Blocked: {reason}")

    # Reset stop hunts
    monitor.on_trade_result(was_stop_hunt=False, was_win=True)
    assert monitor.consecutive_stop_hunts == 0
    print("✅ Stop hunts reset on win")

    # Test 8: Stats report
    print("\n[TEST 8] Stats report...")
    stats_report = monitor.get_stats_report()
    print(stats_report)

    print("\n" + "="*70)
    print("✅ TOUS LES TESTS PASSÉS")
    print("="*70)
