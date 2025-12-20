"""
Système d'alertes pour la gestion des risques
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional
from enum import Enum


class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "INFO"
    WARNING = "WARNING"
    DANGER = "DANGER"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Types d'alertes"""
    DRAWDOWN = "DRAWDOWN"
    DAILY_LOSS = "DAILY_LOSS"
    LOSS_STREAK = "LOSS_STREAK"
    MAX_TRADES = "MAX_TRADES"
    CONSISTENCY = "CONSISTENCY"
    TARGET_REACHED = "TARGET_REACHED"
    CUSTOM = "CUSTOM"


@dataclass
class Alert:
    """Représentation d'une alerte"""
    timestamp: datetime
    level: AlertLevel
    alert_type: AlertType
    title: str
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    action_required: str = ""


class RiskAlertManager:
    """
    Gestionnaire d'alertes de risque
    """

    def __init__(self, on_alert: Callable[[Alert], None] = None):
        self.on_alert = on_alert
        self.alerts: List[Alert] = []
        self.alert_history: List[Alert] = []

        # Cooldown pour éviter le spam
        self.last_alerts: dict = {}  # type -> last_timestamp
        self.cooldown_seconds = 60

    def check_drawdown(self, dd_percent: float, thresholds: dict = None):
        """
        Vérifie le niveau de drawdown

        thresholds: {"warning": 50, "danger": 75, "critical": 90}
        """
        if thresholds is None:
            thresholds = {"warning": 50, "danger": 75, "critical": 90}

        if dd_percent >= thresholds["critical"]:
            self._create_alert(
                AlertLevel.CRITICAL,
                AlertType.DRAWDOWN,
                "⛔ DRAWDOWN CRITIQUE",
                f"Drawdown à {dd_percent:.1f}% - STOP TRADING!",
                dd_percent,
                thresholds["critical"],
                "Arrêter immédiatement le trading"
            )
        elif dd_percent >= thresholds["danger"]:
            self._create_alert(
                AlertLevel.DANGER,
                AlertType.DRAWDOWN,
                "🔴 DRAWDOWN DANGER",
                f"Drawdown à {dd_percent:.1f}%",
                dd_percent,
                thresholds["danger"],
                "Réduire la taille des positions"
            )
        elif dd_percent >= thresholds["warning"]:
            self._create_alert(
                AlertLevel.WARNING,
                AlertType.DRAWDOWN,
                "🟡 DRAWDOWN WARNING",
                f"Drawdown à {dd_percent:.1f}%",
                dd_percent,
                thresholds["warning"],
                "Trader avec prudence"
            )

    def check_daily_loss(self, daily_loss: float, limit: float):
        """Vérifie le daily loss"""
        percent_used = (daily_loss / limit * 100) if limit > 0 else 0

        if daily_loss >= limit:
            self._create_alert(
                AlertLevel.CRITICAL,
                AlertType.DAILY_LOSS,
                "⛔ DAILY LOSS LIMIT ATTEINT",
                f"Perte journalière: ${daily_loss:.2f} (limite: ${limit:.2f})",
                daily_loss,
                limit,
                "STOP TRADING POUR AUJOURD'HUI"
            )
        elif percent_used >= 75:
            self._create_alert(
                AlertLevel.DANGER,
                AlertType.DAILY_LOSS,
                "🔴 DAILY LOSS PROCHE",
                f"Perte journalière: ${daily_loss:.2f} ({percent_used:.0f}% de la limite)",
                daily_loss,
                limit,
                "Dernier trade autorisé"
            )
        elif percent_used >= 50:
            self._create_alert(
                AlertLevel.WARNING,
                AlertType.DAILY_LOSS,
                "🟡 DAILY LOSS 50%",
                f"Perte journalière: ${daily_loss:.2f} (50% de la limite)",
                daily_loss,
                limit,
                "Trader avec prudence"
            )

    def check_loss_streak(self, streak: int, max_streak: int = 5):
        """Vérifie les séries de pertes"""
        if streak >= max_streak:
            self._create_alert(
                AlertLevel.CRITICAL,
                AlertType.LOSS_STREAK,
                f"⛔ {streak} PERTES CONSÉCUTIVES",
                f"Série de {streak} pertes - arrêter le trading",
                streak,
                max_streak,
                "STOP TRADING - faire une pause"
            )
        elif streak >= max_streak - 1:
            self._create_alert(
                AlertLevel.DANGER,
                AlertType.LOSS_STREAK,
                f"🔴 {streak} PERTES CONSÉCUTIVES",
                f"Série de {streak} pertes",
                streak,
                max_streak,
                "Dernier trade avant stop obligatoire"
            )
        elif streak >= max_streak - 2:
            self._create_alert(
                AlertLevel.WARNING,
                AlertType.LOSS_STREAK,
                f"🟡 {streak} PERTES CONSÉCUTIVES",
                f"Attention: {streak} pertes d'affilée",
                streak,
                max_streak,
                "Revoir la stratégie"
            )

    def check_max_trades(self, trades_today: int, max_trades: int):
        """Vérifie le nombre de trades"""
        if trades_today >= max_trades:
            self._create_alert(
                AlertLevel.CRITICAL,
                AlertType.MAX_TRADES,
                "⛔ MAX TRADES ATTEINT",
                f"{trades_today} trades aujourd'hui (max: {max_trades})",
                trades_today,
                max_trades,
                "PAS DE NOUVEAU TRADE AUJOURD'HUI"
            )
        elif trades_today >= max_trades - 1:
            self._create_alert(
                AlertLevel.WARNING,
                AlertType.MAX_TRADES,
                "🟡 DERNIER TRADE",
                f"{trades_today}/{max_trades} trades",
                trades_today,
                max_trades,
                "Dernier trade autorisé"
            )

    def check_consistency(self, daily_pnl: float, max_allowed: float, rule_percent: float):
        """Vérifie la règle de consistance"""
        if daily_pnl > max_allowed:
            self._create_alert(
                AlertLevel.DANGER,
                AlertType.CONSISTENCY,
                f"🔴 RÈGLE {rule_percent*100:.0f}% VIOLÉE",
                f"PnL du jour: ${daily_pnl:.2f} > limite ${max_allowed:.2f}",
                daily_pnl,
                max_allowed,
                "Les profits excédentaires peuvent être annulés"
            )
        elif daily_pnl > max_allowed * 0.8:
            self._create_alert(
                AlertLevel.WARNING,
                AlertType.CONSISTENCY,
                f"🟡 PROCHE RÈGLE {rule_percent*100:.0f}%",
                f"PnL du jour: ${daily_pnl:.2f} proche de limite ${max_allowed:.2f}",
                daily_pnl,
                max_allowed,
                "Considérer arrêter pour aujourd'hui"
            )

    def notify_target_reached(self, target: float, current_pnl: float):
        """Notification quand le target est atteint"""
        self._create_alert(
            AlertLevel.INFO,
            AlertType.TARGET_REACHED,
            "🎯 PROFIT TARGET ATTEINT!",
            f"PnL: ${current_pnl:.2f} / Target: ${target:.2f}",
            current_pnl,
            target,
            "Vérifier les jours minimum et la consistance"
        )

    def _create_alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        title: str,
        message: str,
        value: float,
        threshold: float,
        action: str
    ):
        """Crée et envoie une alerte"""
        # Vérifier le cooldown
        key = f"{alert_type.value}_{level.value}"
        now = datetime.now()

        if key in self.last_alerts:
            elapsed = (now - self.last_alerts[key]).total_seconds()
            if elapsed < self.cooldown_seconds:
                return  # Skip - trop récent

        self.last_alerts[key] = now

        alert = Alert(
            timestamp=now,
            level=level,
            alert_type=alert_type,
            title=title,
            message=message,
            value=value,
            threshold=threshold,
            action_required=action,
        )

        self.alerts.append(alert)
        self.alert_history.append(alert)

        # Callback
        if self.on_alert:
            self.on_alert(alert)

    def get_active_alerts(self) -> List[Alert]:
        """Retourne les alertes actives"""
        return self.alerts

    def clear_alerts(self):
        """Efface les alertes actives (pas l'historique)"""
        self.alerts = []

    def get_alert_summary(self) -> dict:
        """Résumé des alertes"""
        return {
            "active_count": len(self.alerts),
            "critical": len([a for a in self.alerts if a.level == AlertLevel.CRITICAL]),
            "danger": len([a for a in self.alerts if a.level == AlertLevel.DANGER]),
            "warning": len([a for a in self.alerts if a.level == AlertLevel.WARNING]),
            "history_count": len(self.alert_history),
        }

