"""
Drawdown Tracker pour Prop Firm
Gère les 3 types de drawdown: TRAILING, EOD, STATIC

PIÈGE #1: Le trailing drawdown!
"Your best trade becomes your worst enemy with intraday trailing.
Hit +$3,000? Your stop is now at +$500. Market pulls back to +$400?
Account terminated. You ended green but still failed."
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Callable
from enum import Enum

from ..config.prop_firm_rules import get_prop_firm_config, get_account_config, DrawdownType


class DrawdownStatus(Enum):
    """Status du drawdown"""
    SAFE = "SAFE"           # < 50% utilisé
    WARNING = "WARNING"     # 50-75% utilisé
    DANGER = "DANGER"       # 75-90% utilisé
    CRITICAL = "CRITICAL"   # > 90% utilisé
    BREACHED = "BREACHED"   # Compte terminé


@dataclass
class DrawdownState:
    """État actuel du drawdown"""
    drawdown_type: DrawdownType
    starting_balance: float
    current_balance: float
    high_water_mark: float
    trailing_dd_limit: float
    floor: float
    dd_used: float
    dd_used_percent: float
    dd_remaining: float
    distance_to_breach: float
    status: DrawdownStatus
    can_trade: bool
    last_update: datetime


@dataclass
class DrawdownEvent:
    """Événement de drawdown (pour historique)"""
    timestamp: datetime
    event_type: str  # "NEW_HIGH", "DD_INCREASE", "ALERT", "BREACH"
    balance_before: float
    balance_after: float
    hwm_before: float
    hwm_after: float
    dd_percent: float
    message: str


class DrawdownTracker:
    """
    Tracker de drawdown temps réel

    Supporte:
    - TRAILING: Se met à jour à chaque nouveau high (intraday) - PIÈGE!
    - EOD: Se met à jour seulement en fin de journée - Plus facile
    - STATIC: Fixe depuis le starting balance
    """

    # Seuils d'alerte
    WARNING_THRESHOLD = 50.0   # Alerte à 50% du DD utilisé
    DANGER_THRESHOLD = 75.0    # Danger à 75%
    CRITICAL_THRESHOLD = 90.0  # Critique à 90%

    def __init__(
        self,
        prop_firm: str,
        account_size: str,
        on_alert_callback: Callable[[str, str], None] = None
    ):
        self.prop_firm = prop_firm
        self.account_size = account_size
        self.on_alert = on_alert_callback

        # Charger la configuration
        self.firm_config = get_prop_firm_config(prop_firm)
        self.account_config = get_account_config(prop_firm, account_size)

        # Type de drawdown
        self.drawdown_type = self.firm_config["drawdown_type"]

        # État initial
        self.starting_balance = self.account_config["starting_balance"]
        self.current_balance = self.starting_balance
        self.high_water_mark = self.starting_balance
        self.trailing_dd_limit = self.account_config["trailing_dd"]

        # Daily loss (si applicable)
        self.daily_loss_limit = self.account_config.get("daily_loss_limit")
        self.daily_starting_balance = self.starting_balance
        self.daily_low = self.starting_balance

        # Historique
        self.events: List[DrawdownEvent] = []
        self.daily_highs: Dict[date, float] = {}

        # Status
        self.is_breached = False
        self.last_alert_status: Optional[DrawdownStatus] = None

    def update(self, new_balance: float, is_eod: bool = False) -> DrawdownState:
        """
        Met à jour le tracker avec une nouvelle balance

        Args:
            new_balance: Nouvelle balance du compte
            is_eod: True si c'est la mise à jour de fin de journée

        Returns:
            État actuel du drawdown
        """
        old_balance = self.current_balance
        old_hwm = self.high_water_mark

        self.current_balance = new_balance

        # Mise à jour du high water mark selon le type
        if self.drawdown_type == DrawdownType.TRAILING:
            # TRAILING: Se met à jour à chaque tick si nouveau high
            if new_balance > self.high_water_mark:
                self._record_event("NEW_HIGH", old_balance, new_balance, old_hwm, new_balance,
                                  f"Nouveau HWM: ${new_balance:,.2f}")
                self.high_water_mark = new_balance

        elif self.drawdown_type == DrawdownType.EOD:
            # EOD: Se met à jour seulement en fin de journée
            if is_eod and new_balance > self.high_water_mark:
                self._record_event("NEW_HIGH", old_balance, new_balance, old_hwm, new_balance,
                                  f"Nouveau HWM EOD: ${new_balance:,.2f}")
                self.high_water_mark = new_balance

        # STATIC: Ne se met jamais à jour (high_water_mark = starting_balance)

        # Vérifier les alertes
        state = self.get_state()
        self._check_alerts(state)

        return state

    def start_new_day(self):
        """Appelé au début de chaque journée de trading"""
        today = date.today()
        self.daily_starting_balance = self.current_balance
        self.daily_low = self.current_balance
        self.daily_highs[today] = self.current_balance

    def end_of_day(self):
        """Appelé en fin de journée - déclenche la mise à jour EOD"""
        today = date.today()
        self.daily_highs[today] = max(
            self.daily_highs.get(today, self.current_balance),
            self.current_balance
        )

        # Pour les comptes EOD, c'est ici que le HWM peut monter
        if self.drawdown_type == DrawdownType.EOD:
            self.update(self.current_balance, is_eod=True)

    def get_state(self) -> DrawdownState:
        """Retourne l'état actuel du drawdown"""
        # Calculer le floor selon le type
        if self.drawdown_type == DrawdownType.STATIC:
            floor = self.starting_balance - self.trailing_dd_limit
        else:
            floor = self.high_water_mark - self.trailing_dd_limit

        # Drawdown utilisé
        dd_used = max(0, self.high_water_mark - self.current_balance)
        dd_used_percent = (dd_used / self.trailing_dd_limit * 100) if self.trailing_dd_limit > 0 else 0
        dd_remaining = self.trailing_dd_limit - dd_used
        distance_to_breach = self.current_balance - floor

        # Déterminer le status
        if self.current_balance <= floor:
            status = DrawdownStatus.BREACHED
            self.is_breached = True
        elif dd_used_percent >= self.CRITICAL_THRESHOLD:
            status = DrawdownStatus.CRITICAL
        elif dd_used_percent >= self.DANGER_THRESHOLD:
            status = DrawdownStatus.DANGER
        elif dd_used_percent >= self.WARNING_THRESHOLD:
            status = DrawdownStatus.WARNING
        else:
            status = DrawdownStatus.SAFE

        can_trade = status not in [DrawdownStatus.BREACHED, DrawdownStatus.CRITICAL]

        return DrawdownState(
            drawdown_type=self.drawdown_type,
            starting_balance=self.starting_balance,
            current_balance=self.current_balance,
            high_water_mark=self.high_water_mark,
            trailing_dd_limit=self.trailing_dd_limit,
            floor=floor,
            dd_used=dd_used,
            dd_used_percent=dd_used_percent,
            dd_remaining=dd_remaining,
            distance_to_breach=distance_to_breach,
            status=status,
            can_trade=can_trade,
            last_update=datetime.now(),
        )

    def get_daily_loss_state(self) -> Optional[Dict]:
        """Retourne l'état du daily loss limit (si applicable)"""
        if not self.daily_loss_limit:
            return None

        daily_pnl = self.current_balance - self.daily_starting_balance
        daily_loss_used = max(0, -daily_pnl)
        daily_loss_percent = (daily_loss_used / self.daily_loss_limit * 100) if self.daily_loss_limit > 0 else 0

        return {
            "daily_loss_limit": self.daily_loss_limit,
            "daily_starting_balance": self.daily_starting_balance,
            "current_balance": self.current_balance,
            "daily_pnl": daily_pnl,
            "daily_loss_used": daily_loss_used,
            "daily_loss_percent": daily_loss_percent,
            "daily_loss_remaining": self.daily_loss_limit - daily_loss_used,
            "is_breached": daily_loss_used >= self.daily_loss_limit,
        }

    def _check_alerts(self, state: DrawdownState):
        """Vérifie et envoie les alertes si nécessaire"""
        # Ne pas répéter la même alerte
        if state.status == self.last_alert_status:
            return

        self.last_alert_status = state.status

        # Envoyer l'alerte
        if state.status == DrawdownStatus.BREACHED:
            self._send_alert("CRITICAL", f"⛔ COMPTE TERMINÉ! Drawdown breach à ${state.current_balance:,.2f}")
        elif state.status == DrawdownStatus.CRITICAL:
            self._send_alert("CRITICAL", f"🔴 CRITIQUE: {state.dd_used_percent:.1f}% DD utilisé! STOP TRADING!")
        elif state.status == DrawdownStatus.DANGER:
            self._send_alert("DANGER", f"🟠 DANGER: {state.dd_used_percent:.1f}% DD utilisé")
        elif state.status == DrawdownStatus.WARNING:
            self._send_alert("WARNING", f"🟡 WARNING: {state.dd_used_percent:.1f}% DD utilisé")

    def _send_alert(self, alert_type: str, message: str):
        """Envoie une alerte via le callback"""
        if self.on_alert:
            self.on_alert(alert_type, message)

        # Logger l'événement
        state = self.get_state()
        self._record_event("ALERT", self.current_balance, self.current_balance,
                         self.high_water_mark, self.high_water_mark,
                         message)

    def _record_event(self, event_type: str, bal_before: float, bal_after: float,
                     hwm_before: float, hwm_after: float, message: str):
        """Enregistre un événement dans l'historique"""
        state = self.get_state()
        event = DrawdownEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            balance_before=bal_before,
            balance_after=bal_after,
            hwm_before=hwm_before,
            hwm_after=hwm_after,
            dd_percent=state.dd_used_percent,
            message=message,
        )
        self.events.append(event)

    @property
    def available_drawdown(self) -> float:
        """Retourne le drawdown restant disponible"""
        state = self.get_state()
        return state.dd_remaining

    def get_summary(self) -> str:
        """Retourne un résumé textuel du drawdown"""
        state = self.get_state()

        status_emoji = {
            DrawdownStatus.SAFE: "🟢",
            DrawdownStatus.WARNING: "🟡",
            DrawdownStatus.DANGER: "🟠",
            DrawdownStatus.CRITICAL: "🔴",
            DrawdownStatus.BREACHED: "⛔",
        }

        return f"""
{status_emoji[state.status]} DRAWDOWN STATUS ({self.drawdown_type.value})
├── High Water Mark: ${state.high_water_mark:,.2f}
├── Balance actuelle: ${state.current_balance:,.2f}
├── Floor (breach): ${state.floor:,.2f}
├── DD utilisé: ${state.dd_used:,.2f} ({state.dd_used_percent:.1f}%)
├── DD restant: ${state.dd_remaining:,.2f}
├── Distance breach: ${state.distance_to_breach:,.2f}
└── Peut trader: {'✅ OUI' if state.can_trade else '❌ NON'}
"""
