"""
Statistiques journalières
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List

from .trade_stats import Trade, TradeStats, TradeResult, TradeDirection


@dataclass
class DailyStats:
    """Statistiques complètes d'une journée de trading"""

    trading_date: date

    # Balance
    starting_balance: float = 0.0
    ending_balance: float = 0.0
    high_balance: float = 0.0
    low_balance: float = 0.0

    # Trades
    trades: List[Trade] = field(default_factory=list)

    # PnL
    gross_pnl: float = 0.0
    commissions: float = 0.0
    net_pnl: float = 0.0

    # Par session
    london_trades: int = 0
    london_pnl: float = 0.0
    us_morning_trades: int = 0
    us_morning_pnl: float = 0.0
    power_hour_trades: int = 0
    power_hour_pnl: float = 0.0

    # Par symbole
    es_trades: int = 0
    es_pnl: float = 0.0
    nq_trades: int = 0
    nq_pnl: float = 0.0
    rty_trades: int = 0
    rty_pnl: float = 0.0

    # Streaks du jour
    current_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0

    @property
    def trade_stats(self) -> TradeStats:
        """Retourne les stats agrégées des trades du jour"""
        return TradeStats(trades=self.trades)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return len([t for t in self.trades if t.result == TradeResult.WIN])

    @property
    def losses(self) -> int:
        return len([t for t in self.trades if t.result == TradeResult.LOSS])

    @property
    def win_rate(self) -> float:
        closed = len([t for t in self.trades if t.result != TradeResult.OPEN])
        if closed == 0:
            return 0.0
        return (self.wins / closed) * 100

    @property
    def max_intraday_dd(self) -> float:
        """Drawdown intraday maximum"""
        return self.high_balance - self.low_balance if self.high_balance > 0 else 0.0

    @property
    def longs(self) -> int:
        return len([t for t in self.trades if t.direction == TradeDirection.LONG])

    @property
    def shorts(self) -> int:
        return len([t for t in self.trades if t.direction == TradeDirection.SHORT])

    def add_trade(self, trade: Trade):
        """Ajoute un trade aux stats du jour"""
        self.trades.append(trade)

        # Mettre à jour les compteurs
        if trade.result == TradeResult.WIN:
            if self.current_streak > 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
            self.max_win_streak = max(self.max_win_streak, self.current_streak)
        elif trade.result == TradeResult.LOSS:
            if self.current_streak < 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1
            self.max_loss_streak = max(self.max_loss_streak, abs(self.current_streak))

        # PnL
        self.gross_pnl += trade.pnl
        self.commissions += trade.commissions
        self.net_pnl += trade.net_pnl

        # Par session
        if trade.session == "LONDON":
            self.london_trades += 1
            self.london_pnl += trade.net_pnl
        elif trade.session == "US_MORNING":
            self.us_morning_trades += 1
            self.us_morning_pnl += trade.net_pnl
        elif trade.session == "POWER_HOUR":
            self.power_hour_trades += 1
            self.power_hour_pnl += trade.net_pnl

        # Par symbole
        if trade.symbol in ["ES", "MES"]:
            self.es_trades += 1
            self.es_pnl += trade.net_pnl
        elif trade.symbol in ["NQ", "MNQ"]:
            self.nq_trades += 1
            self.nq_pnl += trade.net_pnl
        elif trade.symbol in ["RTY", "M2K"]:
            self.rty_trades += 1
            self.rty_pnl += trade.net_pnl

    def update_balance(self, current_balance: float):
        """Met à jour les balances high/low"""
        if current_balance > self.high_balance:
            self.high_balance = current_balance
        if current_balance < self.low_balance or self.low_balance == 0:
            self.low_balance = current_balance
        self.ending_balance = current_balance

    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return {
            "date": str(self.trading_date),
            "starting_balance": self.starting_balance,
            "ending_balance": self.ending_balance,
            "net_pnl": self.net_pnl,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "longs": self.longs,
            "shorts": self.shorts,
            "max_intraday_dd": self.max_intraday_dd,
            "max_win_streak": self.max_win_streak,
            "max_loss_streak": self.max_loss_streak,
            "sessions": {
                "london": {"trades": self.london_trades, "pnl": self.london_pnl},
                "us_morning": {"trades": self.us_morning_trades, "pnl": self.us_morning_pnl},
                "power_hour": {"trades": self.power_hour_trades, "pnl": self.power_hour_pnl},
            },
            "symbols": {
                "es": {"trades": self.es_trades, "pnl": self.es_pnl},
                "nq": {"trades": self.nq_trades, "pnl": self.nq_pnl},
                "rty": {"trades": self.rty_trades, "pnl": self.rty_pnl},
            },
        }

