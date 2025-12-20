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
from zoneinfo import ZoneInfo  # ✅ FIX: Remplacer pytz par zoneinfo

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

    def __init__(self, enable_london: bool = True, enable_us: bool = True, test_mode: bool = False):
        """
        Initialize Session Quality Monitor.

        Args:
            enable_london: bool - Activer session London (08:00-11:00)?
            enable_us: bool - Activer sessions US (15:50-17:00 + 20:00-21:30)?
            test_mode: bool - MODE TEST: Bypass restrictions horaires pour tester la pipeline
        """

        # ═══════════════════════════════════════════════════════════════
        # MODE TEST (pour développement/tests)
        # ═══════════════════════════════════════════════════════════════

        self.test_mode = test_mode

        if self.test_mode:
            logger.warning("=" * 80)
            logger.warning("🧪 MODE TEST ACTIVÉ - Session Quality Monitor DÉSACTIVÉ")
            logger.warning("⚠️  ATTENTION: Tous les créneaux horaires sont autorisés")
            logger.warning("⚠️  NE PAS UTILISER EN PRODUCTION RÉELLE")
            logger.warning("=" * 80)

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

            # 🔴🔴 US OPEN VOLATILITY BLOCK - AUDIT BRUTAL 02/12/2025
            # 11 trades à 16h = WR 18.2% = -$1,650 de pertes!
            # BLOQUER 15:45-16:35 = période de volatilité extrême
            'us_open_block': {
                'blocked': True,  # 🔥 INTERDIT DE TRADER!
                'start_hour': 15,
                'start_minute': 45,
                'end_hour': 16,
                'end_minute': 35,
                'description': 'US OPEN VOLATILITY - BLOCKED!',
            },

            # US Morning (TRADE) - ✅ PRODUCTION: 15:50-17:00
            'us_morning': {
                'enabled': enable_us,
                'start_hour': 15,  # ✅ RÉTABLI: 15:50 (03/12/2025)
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

            # Hard stop - 🔥 AUDIT BRUTAL: 21:30 → 21:25 (éviter fin de session)
            'hard_stop_hour': 21,
            'hard_stop_minute': 25,
        }

        # ═══════════════════════════════════════════════════════════════
        # THRESHOLDS (non-redondants avec menthorq_3layer)
        # ═══════════════════════════════════════════════════════════════

        # Market quality (pas de check confluence/MenthorQ - redondant)
        self.MIN_VOLUME = 10  # contracts/barre minimum (snapshot = 1 barre)
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
================================================================================
SESSION QUALITY MONITOR INITIALIZED
================================================================================
Configuration:
  - London Session:     {'ENABLED' if enable_london else 'DISABLED'} (08:00-11:00)
  - US Sessions:        {'ENABLED' if enable_us else 'DISABLED'} (15:50-17:00 + 20:00-21:30)
  - Hard Stop:          21:30 Paris
  - Lunch Block:        17:00-19:30 Paris ✅ ACTIF

Thresholds:
  - Min Volume:         {self.MIN_VOLUME} contracts/min
  - Max Spread:         {self.MAX_SPREAD_TICKS} ticks
  - Max Session Prog:   {self.MAX_SESSION_PROGRESS:.0%}
  - Max Stop Hunts:     {self.MAX_CONSECUTIVE_STOP_HUNTS}

[INFO] Version NON-REDONDANTE:
  - Ne check PAS confluence (fait par menthorq_3layer)
  - Ne check PAS MenthorQ (fait par menthorq_3layer)
================================================================================
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
        paris_tz = ZoneInfo('Europe/Paris')
        if now is None:
            now = datetime.now(paris_tz)

        # Ensure Paris timezone
        if now.tzinfo is None:
            now = now.replace(tzinfo=paris_tz)
        else:
            now = now.astimezone(paris_tz)

        self.daily_stats['total_checks'] += 1

        # Calculate quality score
        quality_score = self._calculate_quality_score(snapshot, now)

        # ═══════════════════════════════════════════════════════════════
        # MODE TEST: Bypass toutes les vérifications horaires
        # ═══════════════════════════════════════════════════════════════

        if self.test_mode:
            logger.info(f"🧪 [MODE TEST] Session Quality Check BYPASSED - Score: {quality_score:.0f}/100")
            logger.info(f"🧪 [MODE TEST] Heure actuelle: {now.strftime('%H:%M')} Paris (normalement bloqué en OVERNIGHT)")
            logger.info(f"🧪 [MODE TEST] Trading autorisé pour TESTS uniquement")
            return True, "TEST MODE - All checks bypassed", quality_score

        # ═══════════════════════════════════════════════════════════════
        # HARD BLOCKS (Non-négociables)
        # ═══════════════════════════════════════════════════════════════

        # 1. Horaires interdits
        block, reason = self._check_trading_hours(now, override_opr)
        if block:
            self._record_block(reason, now)

            # 🆕 CALCULER PROCHAINE SESSION
            next_session_time, next_session_name = self._get_next_trading_session(now)
            hours_until = (next_session_time - now).total_seconds() / 3600

            # 🆕 LOG PLUS EXPLICITE AVEC PROCHAINE SESSION
            logger.info("=" * 80)
            logger.info(f"🚫 SESSION QUALITY BLOCK: {reason}")
            logger.info("=" * 80)
            logger.info(f"⏰ Heure actuelle: {now.strftime('%A %d %B %Y - %H:%M')} Paris")
            logger.info(f"📅 Créneaux autorisés:")
            if self.enable_london:
                logger.info(f"   • London:        08:00-11:00")
            if self.enable_us:
                logger.info(f"   • US Morning:    15:50-17:00")
                logger.info(f"   • US Power Hour: 20:00-21:30")
            logger.info(f"   • LUNCH BLOQUÉ:  17:00-19:30 ✅")
            logger.info("=" * 80)
            logger.info(f"⏭️  PROCHAINE SESSION: {next_session_name}")
            logger.info(f"📍 {next_session_time.strftime('%A %d %B %Y à %H:%M')} Paris")
            logger.info(f"⏳ Dans {hours_until:.1f} heures")
            logger.info("=" * 80)
            logger.info(f"💡 Pour tester malgré tout: activer test_mode=True")
            logger.info("=" * 80)

            return False, reason, quality_score

        # 2. Session progress > 95%
        # ⚠️ DÉSACTIVÉ: Le session_progress du dumper C++ représente la session US/Asia
        # On utilise notre propre vérification des horaires Paris (ligne 358-374)
        # progress = snapshot.get('session_progress', 0)
        # if progress > self.MAX_SESSION_PROGRESS:
        #     reason = f"Session terminée ({progress:.1%} > {self.MAX_SESSION_PROGRESS:.0%})"
        #     self._record_block(reason, now)
        #     return False, reason, quality_score

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

        # 1. POST-21:25 (CRITIQUE) - 🔥 AUDIT BRUTAL: 21:30 → 21:25
        if hour >= 22 or (hour == 21 and minute >= 25):
            next_session_info = self._get_next_session_info(now)
            return True, f"[STOP] POST-21:25 - Hard Stop. {next_session_info}"

        # 2. OVERNIGHT (avant 08:00) - ✅ RÉACTIVÉ après test ASIA (02/12/2025)
        if hour < 8:
            next_session_info = self._get_next_session_info(now)
            return True, f"[BLOCK] OVERNIGHT - Market fermé. {next_session_info}"

        # 3. LUNCH US (17:00-19:30) - ✅ RÉACTIVÉ après analyse du 01/12/2025
        #    Résultat: ES LUNCH = 22 trades, 41% WR, -$588 P&L → BLOQUER
        if hour == 17 or hour == 18 or (hour == 19 and minute < 30):
            next_session_info = self._get_next_session_info(now)
            return True, f"[LUNCH] LUNCH US (17:00-19:30) - Pause. {next_session_info}"

        # 4. 🔴 PRE-MARKET US BLOCK (15:00-15:50) - AUDIT 05/12/2025
        #    Données: 6 trades à 15h → 33% WR, -$1,120 P&L = TOXIQUE !
        #    US Morning commence à 15:50, pas avant.
        if hour == 15 and minute < 50:
            next_session_info = self._get_next_session_info(now)
            return True, f"[🔴 PRE-MARKET] BLOC 15:00-15:50 (volatilité pré-open). {next_session_info}"

        # 6. 🔥🔥 US OPEN VOLATILITY BLOCK (15:45-16:35) - DÉSACTIVÉ 03/12/2025
        #    ⚠️ TROP RESTRICTIF: Bloquait toute la session US Morning (15:50-17:00)
        #    ✅ RETOUR À LA NORMALE: Trading autorisé de 15:50 jusqu'au lunch (17:00)
        # if (hour == 15 and minute >= 45) or (hour == 16 and minute < 35):
        #     next_session_info = self._get_next_session_info(now)
        #     return True, f"[🔴 US OPEN BLOCK] Volatilité extrême (15:45-16:35). {next_session_info}"

        # ═══════════════════════════════════════════════════════════════
        # SESSIONS VALIDES
        # ═══════════════════════════════════════════════════════════════

        # Check si dans une session valide
        in_valid_session = False

        # London Session (08:00-11:00) - HORAIRE PRODUCTION
        if self.enable_london:
            if 8 <= hour < 11:
                in_valid_session = True

        # US Morning (15:50-17:00) - ✅ RÉTABLI 03/12/2025
        if self.enable_us:
            if (hour == 15 and minute >= 50) or hour == 16:
                in_valid_session = True

        # ✅ LUNCH 17:00-19:30 maintenant BLOQUÉ (voir ligne 340-344)
        # Raison: ES LUNCH = 22 trades, 41% WR, -$588 P&L → Session perdante

        # US Afternoon/Power Hour (20:00-21:25) - 🔥 AUDIT BRUTAL: 21:30 → 21:25
        if self.enable_us:
            if hour == 20 or (hour == 21 and minute < 25):
                in_valid_session = True

        # Si pas dans session valide → block
        if not in_valid_session:
            next_session_info = self._get_next_session_info(now)
            return True, f"[HORAIRE] Hors horaires trading ({hour:02d}:{minute:02d}). {next_session_info}"

        # ═══════════════════════════════════════════════════════════════
        # TRADING AUTORISÉ ✅
        # ═══════════════════════════════════════════════════════════════

        return False, ""

    def _get_next_session_info(self, now: datetime) -> str:
        """
        Calcule le temps jusqu'au prochain créneau de trading.

        Args:
            now: datetime Paris

        Returns:
            str: Info type "Prochain créneau: London Session dans 7h25min (08:00)"
        """
        from datetime import timedelta

        hour = now.hour
        minute = now.minute

        # Définir les créneaux possibles
        sessions = []

        # London Session (08:00-11:00)
        if self.enable_london:
            sessions.append({
                'name': 'London Session',
                'start_hour': 8,
                'start_minute': 0,
                'end_hour': 11,
                'end_minute': 0
            })

        # US Morning (15:50-17:00) - ✅ PRODUCTION
        if self.enable_us:
            sessions.append({
                'name': 'US Morning',
                'start_hour': 15,  # ✅ PROD: 15:50
                'start_minute': 50,
                'end_hour': 17,
                'end_minute': 0
            })

        # US Power Hour (20:00-21:30)
        if self.enable_us:
            sessions.append({
                'name': 'US Power Hour',
                'start_hour': 20,
                'start_minute': 0,
                'end_hour': 21,
                'end_minute': 30
            })

        # Trouver la prochaine session
        current_time = now.hour * 60 + now.minute  # Minutes depuis minuit
        next_session = None
        min_delta = float('inf')

        for session in sessions:
            session_start = session['start_hour'] * 60 + session['start_minute']

            # Si la session est plus tard aujourd'hui
            if session_start > current_time:
                delta = session_start - current_time
                if delta < min_delta:
                    min_delta = delta
                    next_session = session
            # Sinon, c'est demain
            else:
                delta = (24 * 60 - current_time) + session_start
                if delta < min_delta:
                    min_delta = delta
                    next_session = session

        if next_session:
            hours = int(min_delta // 60)
            minutes = int(min_delta % 60)

            time_str = ""
            if hours > 0:
                time_str = f"{hours}h{minutes:02d}min"
            else:
                time_str = f"{minutes}min"

            start_time = f"{next_session['start_hour']:02d}:{next_session['start_minute']:02d}"

            return f"⏰ Prochain créneau: {next_session['name']} dans {time_str} ({start_time})"

        return "Aucun créneau disponible"

    def _get_next_trading_session(self, now: datetime) -> tuple:
        """
        Calcule la prochaine session de trading avec datetime exact.

        Args:
            now: datetime Paris

        Returns:
            tuple: (next_session_datetime, session_name)
        """
        from datetime import timedelta

        hour = now.hour
        minute = now.minute
        weekday = now.weekday()  # 0=Lundi, 6=Dimanche

        # Définir les créneaux possibles
        sessions = []

        # London Session (08:00-11:00)
        if self.enable_london:
            sessions.append(('London Session', 8, 0))

        # US Morning (15:50-17:00) - ✅ PRODUCTION
        if self.enable_us:
            sessions.append(('US Morning', 15, 50))  # ✅ PROD: 15:50

        # US Power Hour (20:00-21:30)
        if self.enable_us:
            sessions.append(('US Power Hour', 20, 0))

        # Trouver la prochaine session
        current_minutes = hour * 60 + minute

        # Chercher aujourd'hui
        for session_name, start_hour, start_minute in sessions:
            session_minutes = start_hour * 60 + start_minute
            if session_minutes > current_minutes:
                next_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                return (next_time, session_name)

        # Si aucune session aujourd'hui, chercher demain
        tomorrow = now + timedelta(days=1)

        # Si on est vendredi soir (>= 21:30) ou samedi/dimanche, aller au lundi
        if weekday == 4 and (hour >= 21 and minute >= 30):  # Vendredi soir
            days_to_add = 3  # Aller à lundi
            tomorrow = now + timedelta(days=days_to_add)
        elif weekday == 5:  # Samedi
            days_to_add = 2  # Aller à lundi
            tomorrow = now + timedelta(days=days_to_add)
        elif weekday == 6:  # Dimanche
            days_to_add = 1  # Aller à lundi
            tomorrow = now + timedelta(days=days_to_add)

        # Première session du lendemain
        if sessions:
            session_name, start_hour, start_minute = sessions[0]
            next_time = tomorrow.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            return (next_time, session_name)

        return (now, "Aucune session disponible")

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

        # US Morning (15:50-17:00) - ✅ PRODUCTION - TRÈS BON
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
        """
        Retourne nom session actuelle basé sur l'heure Paris.

        Sessions:
        - ASIA: 00:00-08:00 (nuit européenne)
        - London: 08:00-11:00
        - Pre-Afternoon: 11:00-15:25 (pause/pré-market)
        - US Pre-Open: 15:25-15:50 ✅ PRODUCTION
        - US Morning: 15:50-17:00 ✅ PRODUCTION
        - Lunch US: 17:00-19:30
        - Pre-Afternoon: 19:30-20:00
        - US Power Hour: 20:00-21:30
        - Closed: 21:30-00:00
        """
        hour = now.hour
        minute = now.minute

        # ASIA Session (00:00-08:00 Paris)
        if 0 <= hour < 8:
            return "ASIA"
        # London Session (08:00-11:00)
        elif 8 <= hour < 11:
            return "London"
        # Pre-US / Pré-Market (11:00-15:25)
        elif 11 <= hour < 15 or (hour == 15 and minute < 25):
            return "Pre-US"
        # Pre-Open Pause (15:25-15:35)
        elif hour == 15 and 25 <= minute < 35:
            return "Pre-Open"
        # OPR Observe (15:35-15:50) - ✅ PRODUCTION
        elif hour == 15 and 35 <= minute < 50:
            return "OPR Observe"
        # US Morning (15:50-17:00) - ✅ PRODUCTION
        elif (hour == 15 and minute >= 50) or hour == 16:
            return "US Morning"
        # Lunch US (17:00-19:30)
        elif hour == 17 or hour == 18 or (hour == 19 and minute < 30):
            return "Lunch"
        # Pre-Afternoon (19:30-20:00)
        elif hour == 19 and minute >= 30:
            return "Pre-Afternoon"
        # US Power Hour (20:00-21:30)
        elif hour == 20 or (hour == 21 and minute < 30):
            return "US Power Hour"
        # Closed (21:30-00:00)
        else:
            return "Closed"

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
            logger.warning(f"[WARN] Stop hunt #{self.consecutive_stop_hunts}")

            if self.consecutive_stop_hunts >= self.MAX_CONSECUTIVE_STOP_HUNTS:
                logger.error(f"""
================================================================================
[ALERT] {self.consecutive_stop_hunts} STOP HUNTS CONSECUTIFS
================================================================================
Trading BLOQUE jusqu'a win ou reset manuel

Cause probable:
  - Market structure cassee
  - Algos agressifs actifs
  - Pause recommandee: 30-60 minutes
================================================================================
                """)

        elif was_win:
            # Reset stop hunts sur win
            if self.consecutive_stop_hunts > 0:
                logger.info(f"[OK] Win trade - Reset stop hunts counter (was {self.consecutive_stop_hunts})")
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
================================================================================
SESSION QUALITY MONITOR - DAILY STATS
================================================================================
Total Checks:        {stats['total_checks']}
Blocks:              {stats['blocks']} ({stats['block_rate_pct']:.1f}%)
Allows:              {stats['allows']} ({stats['allow_rate_pct']:.1f}%)
Stop Hunts:          {stats['consecutive_stop_hunts']}

Block Reasons:
"""

        for reason, count in sorted(stats['block_reasons'].items(), key=lambda x: -x[1]):
            report += f"  - {reason[:60]:<60} {count:>3}\n"

        if stats['blocks_by_hour']:
            report += "\nBlocks by Hour (Paris):\n"
            for hour in sorted(stats['blocks_by_hour'].keys()):
                count = stats['blocks_by_hour'][hour]
                report += f"  - {hour:02d}:00 - {hour:02d}:59  {count:>3} blocks\n"

        report += "="*80

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
    enable_us: bool = True,
    test_mode: bool = False
) -> SessionQualityMonitor:
    """
    Factory pour créer SessionQualityMonitor.

    Args:
        enable_london: bool - Activer London session? (default: True)
        enable_us: bool - Activer US sessions? (default: True)
        test_mode: bool - MODE TEST: Bypass restrictions horaires pour tester la pipeline (default: False)

    Returns:
        SessionQualityMonitor instance

    Exemple:
        # Avec London + US
        monitor = create_session_quality_monitor(enable_london=True, enable_us=True)

        # US uniquement
        monitor = create_session_quality_monitor(enable_london=False, enable_us=True)

        # MODE TEST (pour développement/tests)
        monitor = create_session_quality_monitor(enable_london=True, enable_us=True, test_mode=True)
    """
    return SessionQualityMonitor(enable_london=enable_london, enable_us=enable_us, test_mode=test_mode)


# ═══════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Tests unitaires du Session Quality Monitor.

    import pytz
    from datetime import datetime

    print("\n" + "="*70)
    print("TESTS SESSION QUALITY MONITOR")
    print("="*70)

    # Test 1: Création
    print("\n[TEST 1] Création monitor...")
    monitor = create_session_quality_monitor(enable_london=True, enable_us=True)
    print("[OK] Monitor cree")

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
    print(f"[OK] Blocked: {reason}")

    # Test 3: US Power Hour OK
    print("\n[TEST 3] US Power Hour (20:30)...")
    now_2030 = datetime(2025, 11, 26, 20, 30, 0, tzinfo=paris_tz)

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_2030)
    assert can_trade == True, "Should allow during Power Hour"
    print(f"[OK] Allowed: {reason}, Score: {score:.0f}/100")

    # Test 4: Lunch Block
    print("\n[TEST 4] Lunch US (18:00)...")
    now_1800 = datetime(2025, 11, 26, 18, 0, 0, tzinfo=paris_tz)

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_1800)
    assert can_trade == False, "Should block during lunch"
    assert "LUNCH" in reason
    print(f"[OK] Blocked: {reason}")

    # Test 5: Spread trop large
    print("\n[TEST 5] Spread trop large...")
    snapshot_bad_spread = snapshot_test.copy()
    snapshot_bad_spread['spread_ticks'] = 5

    now_ok = datetime(2025, 11, 26, 20, 30, 0, tzinfo=paris_tz)
    can_trade, reason, score = monitor.check_can_trade(snapshot_bad_spread, now_ok)
    assert can_trade == False, "Should block with large spread"
    assert "Spread" in reason
    print(f"[OK] Blocked: {reason}")

    # Test 6: Volume insuffisant
    print("\n[TEST 6] Volume insuffisant...")
    snapshot_low_vol = snapshot_test.copy()
    snapshot_low_vol['volume'] = 300

    can_trade, reason, score = monitor.check_can_trade(snapshot_low_vol, now_ok)
    assert can_trade == False, "Should block with low volume"
    assert "Volume" in reason
    print(f"[OK] Blocked: {reason}")

    # Test 7: Stop hunts tracking
    print("\n[TEST 7] Stop hunts tracking...")
    monitor.on_trade_result(was_stop_hunt=True, was_win=False)
    monitor.on_trade_result(was_stop_hunt=True, was_win=False)
    monitor.on_trade_result(was_stop_hunt=True, was_win=False)

    can_trade, reason, score = monitor.check_can_trade(snapshot_test, now_ok)
    assert can_trade == False, "Should block after 3 stop hunts"
    assert "Stop hunts" in reason
    print(f"[OK] Blocked: {reason}")

    # Reset stop hunts
    monitor.on_trade_result(was_stop_hunt=False, was_win=True)
    assert monitor.consecutive_stop_hunts == 0
    print("[OK] Stop hunts reset on win")

    # Test 8: Stats report
    print("\n[TEST 8] Stats report...")
    stats_report = monitor.get_stats_report()
    print(stats_report)

    print("\n" + "="*70)
    print("[OK] TOUS LES TESTS PASSES")
    print("="*70)
