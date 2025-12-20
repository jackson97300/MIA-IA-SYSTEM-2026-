"""
Tracker de progression d'évaluation
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional
from enum import Enum

from .daily_stats import DailyStats
from .trade_stats import Trade, TradeStats
from ..config.prop_firm_rules import get_prop_firm_config, get_account_config


class EvaluationStatus(Enum):
    """Status de l'évaluation"""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED_DD = "FAILED_DD"           # Échec drawdown
    FAILED_DAILY_LOSS = "FAILED_DAILY_LOSS"  # Échec daily loss
    FAILED_RULES = "FAILED_RULES"     # Échec autres règles


@dataclass
class EvaluationProgress:
    """Progression vers le profit target"""
    profit_target: float
    current_pnl: float
    remaining: float
    percent_complete: float
    estimated_days: Optional[int]


@dataclass
class ConsistencyCheck:
    """Vérification de la règle de consistance"""
    rule_percent: Optional[float]  # Ex: 0.30 pour 30%
    max_allowed_daily_pnl: float
    highest_daily_pnl: float
    highest_daily_date: Optional[date]
    is_compliant: bool
    warning_message: Optional[str]


@dataclass
class Payout:
    """Représentation d'un payout"""
    payout_id: int
    date: date
    amount: float
    balance_before: float
    balance_after: float
    total_pnl_at_payout: float
    notes: str = ""


class EvaluationTracker:
    """
    Tracker complet pour évaluations et comptes funded
    """

    def __init__(
        self,
        prop_firm: str,
        account_size: str,
        mode: str = "EVALUATION"
    ):
        self.prop_firm = prop_firm
        self.account_size = account_size
        self.mode = mode

        # Configuration
        self.firm_config = get_prop_firm_config(prop_firm)
        self.account_config = get_account_config(prop_firm, account_size)

        # Objectifs
        self.profit_target = self.account_config["profit_target"]
        self.trailing_dd = self.account_config["trailing_dd"]
        self.min_trading_days = self.firm_config.get("min_trading_days", 0)
        self.consistency_rule = self.firm_config.get("consistency_rule")

        # État
        self.starting_balance = self.account_config["starting_balance"]
        self.current_balance = self.starting_balance
        self.total_pnl = 0.0

        # Dates
        self.start_date: Optional[date] = None
        self.end_date: Optional[date] = None
        self.status = EvaluationStatus.NOT_STARTED

        # Historique
        self.daily_stats: Dict[date, DailyStats] = {}
        self.all_trades: List[Trade] = []
        self.payouts: List[Payout] = []

        # Compteurs
        self.trading_days = 0

    def start(self):
        """Démarre l'évaluation"""
        self.start_date = date.today()
        self.status = EvaluationStatus.IN_PROGRESS

    def record_trade(self, trade: Trade) -> Dict:
        """
        Enregistre un trade et met à jour toutes les stats

        Returns:
            Dict avec le status actuel
        """
        if self.status == EvaluationStatus.NOT_STARTED:
            self.start()

        today = date.today()

        # Créer les stats du jour si nécessaire
        if today not in self.daily_stats:
            self.daily_stats[today] = DailyStats(
                trading_date=today,
                starting_balance=self.current_balance,
                high_balance=self.current_balance,
                low_balance=self.current_balance,
            )
            self.trading_days += 1

        daily = self.daily_stats[today]

        # Ajouter le trade
        daily.add_trade(trade)
        self.all_trades.append(trade)

        # Mettre à jour les balances
        self.total_pnl += trade.net_pnl
        self.current_balance += trade.net_pnl
        daily.update_balance(self.current_balance)

        # Vérifier le status
        self._check_status()

        return self.get_status()

    def _check_status(self):
        """Vérifie si l'évaluation est passée ou échouée"""
        if self.status not in [EvaluationStatus.IN_PROGRESS]:
            return

        # Vérifier si passé
        if self.total_pnl >= self.profit_target and self.trading_days >= self.min_trading_days:
            # Vérifier la règle de consistance
            consistency = self.check_consistency()
            if consistency.is_compliant:
                self.status = EvaluationStatus.PASSED
                self.end_date = date.today()

    def mark_failed(self, reason: EvaluationStatus):
        """Marque l'évaluation comme échouée"""
        self.status = reason
        self.end_date = date.today()

    def get_progress(self) -> EvaluationProgress:
        """Retourne la progression vers le target"""
        remaining = self.profit_target - self.total_pnl
        percent = (self.total_pnl / self.profit_target * 100) if self.profit_target > 0 else 0

        # Estimation des jours restants
        estimated_days = None
        if self.trading_days > 0 and self.total_pnl > 0:
            avg_daily_pnl = self.total_pnl / self.trading_days
            if avg_daily_pnl > 0:
                estimated_days = max(1, int(remaining / avg_daily_pnl))

        return EvaluationProgress(
            profit_target=self.profit_target,
            current_pnl=self.total_pnl,
            remaining=remaining,
            percent_complete=percent,
            estimated_days=estimated_days,
        )

    def check_consistency(self) -> ConsistencyCheck:
        """Vérifie la règle de consistance (30% ou 50%)"""
        if not self.consistency_rule:
            return ConsistencyCheck(
                rule_percent=None,
                max_allowed_daily_pnl=float('inf'),
                highest_daily_pnl=0,
                highest_daily_date=None,
                is_compliant=True,
                warning_message=None,
            )

        # Max autorisé = rule% du profit total
        max_allowed = self.total_pnl * self.consistency_rule

        # Trouver le jour le plus profitable
        highest_pnl = 0
        highest_date = None
        for d, stats in self.daily_stats.items():
            if stats.net_pnl > highest_pnl:
                highest_pnl = stats.net_pnl
                highest_date = d

        is_compliant = highest_pnl <= max_allowed

        warning = None
        if not is_compliant:
            warning = f"⚠️ Le {highest_date}: ${highest_pnl:.2f} > {self.consistency_rule*100:.0f}% du total (${max_allowed:.2f})"
        elif highest_pnl > max_allowed * 0.8:
            warning = f"💡 Attention: ${highest_pnl:.2f} proche de la limite (${max_allowed:.2f})"

        return ConsistencyCheck(
            rule_percent=self.consistency_rule,
            max_allowed_daily_pnl=max_allowed,
            highest_daily_pnl=highest_pnl,
            highest_daily_date=highest_date,
            is_compliant=is_compliant,
            warning_message=warning,
        )

    def record_payout(self, amount: float, notes: str = "") -> Payout:
        """Enregistre un payout"""
        payout = Payout(
            payout_id=len(self.payouts) + 1,
            date=date.today(),
            amount=amount,
            balance_before=self.current_balance,
            balance_after=self.current_balance - amount,
            total_pnl_at_payout=self.total_pnl,
            notes=notes,
        )

        self.payouts.append(payout)
        self.current_balance -= amount

        return payout

    def get_status(self) -> Dict:
        """Retourne le status complet"""
        progress = self.get_progress()
        consistency = self.check_consistency()
        trade_stats = TradeStats(trades=self.all_trades)

        return {
            # Identification
            "prop_firm": self.prop_firm,
            "account_size": self.account_size,
            "mode": self.mode,
            "status": self.status.value,

            # Dates
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "trading_days": self.trading_days,
            "min_trading_days": self.min_trading_days,
            "days_remaining": max(0, self.min_trading_days - self.trading_days),

            # Balance
            "starting_balance": self.starting_balance,
            "current_balance": self.current_balance,
            "total_pnl": self.total_pnl,

            # Progression
            "progress": {
                "target": progress.profit_target,
                "current": progress.current_pnl,
                "remaining": progress.remaining,
                "percent": progress.percent_complete,
                "estimated_days": progress.estimated_days,
            },

            # Consistance
            "consistency": {
                "rule": consistency.rule_percent,
                "max_allowed": consistency.max_allowed_daily_pnl,
                "highest_day": consistency.highest_daily_pnl,
                "is_compliant": consistency.is_compliant,
                "warning": consistency.warning_message,
            },

            # Trade stats
            "trades": {
                "total": trade_stats.total_trades,
                "wins": trade_stats.wins,
                "losses": trade_stats.losses,
                "win_rate": trade_stats.win_rate,
                "profit_factor": trade_stats.profit_factor,
                "avg_rr": trade_stats.avg_rr,
            },

            # Payouts
            "payouts": {
                "count": len(self.payouts),
                "total": sum(p.amount for p in self.payouts),
            },
        }

