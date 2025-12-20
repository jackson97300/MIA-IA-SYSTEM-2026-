"""
Classes pour les trades et leurs statistiques
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from ..config.contract_specs import get_contract_spec, calculate_pnl_from_ticks


class TradeDirection(Enum):
    """Direction du trade"""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeResult(Enum):
    """Résultat du trade"""
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"


@dataclass
class Trade:
    """Représentation complète d'un trade"""

    # Identification
    trade_id: str

    # Exécution
    symbol: str
    direction: TradeDirection
    contracts: int
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None

    # Résultat
    pnl: float = 0.0
    pnl_ticks: int = 0
    commissions: float = 0.0
    net_pnl: float = 0.0
    result: TradeResult = TradeResult.OPEN

    # Contexte
    session: str = ""           # LONDON, US_MORNING, POWER_HOUR
    strategy: str = ""          # Nom de la stratégie
    confidence: float = 0.0     # Confidence du signal
    level_type: str = ""        # Type de niveau (GEX, HVL, etc.)
    level_score: int = 0        # Score du niveau

    # Risk management
    initial_stop_ticks: int = 0
    initial_target_ticks: int = 0
    actual_rr: float = 0.0
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0    # MAE

    # Notes
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def close(self, exit_price: float, exit_time: datetime, commissions: float = 0.0):
        """Ferme le trade et calcule les métriques"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.commissions = commissions

        spec = get_contract_spec(self.symbol)

        # Calcul PnL en ticks selon direction
        if self.direction == TradeDirection.LONG:
            self.pnl_ticks = int((exit_price - self.entry_price) / spec.tick_size)
        else:
            self.pnl_ticks = int((self.entry_price - exit_price) / spec.tick_size)

        # Calcul PnL en $
        self.pnl = calculate_pnl_from_ticks(self.symbol, self.pnl_ticks, self.contracts)
        self.net_pnl = self.pnl - self.commissions

        # Résultat
        if self.net_pnl > 0:
            self.result = TradeResult.WIN
        elif self.net_pnl < 0:
            self.result = TradeResult.LOSS
        else:
            self.result = TradeResult.BREAKEVEN

        # Calculer R:R réel si on avait un stop initial
        if self.initial_stop_ticks > 0:
            self.actual_rr = abs(self.pnl_ticks / self.initial_stop_ticks)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Durée du trade en secondes"""
        if self.exit_time and self.entry_time:
            return (self.exit_time - self.entry_time).total_seconds()
        return None

    @property
    def duration_str(self) -> str:
        """Durée du trade formatée"""
        seconds = self.duration_seconds
        if seconds is None:
            return "OPEN"

        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    @property
    def is_micro(self) -> bool:
        """True si le contrat est un micro"""
        return get_contract_spec(self.symbol).is_micro

    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "contracts": self.contracts,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "pnl": self.pnl,
            "pnl_ticks": self.pnl_ticks,
            "net_pnl": self.net_pnl,
            "result": self.result.value,
            "session": self.session,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "duration": self.duration_str,
            "actual_rr": self.actual_rr,
        }

    def __str__(self) -> str:
        """Représentation string du trade"""
        result_emoji = {
            TradeResult.WIN: "✅",
            TradeResult.LOSS: "❌",
            TradeResult.BREAKEVEN: "⚪",
            TradeResult.OPEN: "🔄",
        }

        return (f"{result_emoji[self.result]} #{self.trade_id} "
                f"{self.direction.value} {self.contracts}x{self.symbol} "
                f"@ {self.entry_price} → {self.exit_price or 'OPEN'} "
                f"PnL: ${self.net_pnl:+.2f} ({self.pnl_ticks:+d}t) "
                f"[{self.duration_str}]")


@dataclass
class TradeStats:
    """Statistiques agrégées d'un ensemble de trades"""

    trades: List[Trade] = field(default_factory=list)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def closed_trades(self) -> List[Trade]:
        return [t for t in self.trades if t.result != TradeResult.OPEN]

    @property
    def wins(self) -> int:
        return len([t for t in self.trades if t.result == TradeResult.WIN])

    @property
    def losses(self) -> int:
        return len([t for t in self.trades if t.result == TradeResult.LOSS])

    @property
    def breakevens(self) -> int:
        return len([t for t in self.trades if t.result == TradeResult.BREAKEVEN])

    @property
    def long_trades(self) -> int:
        return len([t for t in self.trades if t.direction == TradeDirection.LONG])

    @property
    def short_trades(self) -> int:
        return len([t for t in self.trades if t.direction == TradeDirection.SHORT])

    @property
    def win_rate(self) -> float:
        closed = len(self.closed_trades)
        if closed == 0:
            return 0.0
        return (self.wins / closed) * 100

    @property
    def total_pnl(self) -> float:
        return sum(t.net_pnl for t in self.trades)

    @property
    def gross_profit(self) -> float:
        return sum(t.net_pnl for t in self.trades if t.net_pnl > 0)

    @property
    def gross_loss(self) -> float:
        return abs(sum(t.net_pnl for t in self.trades if t.net_pnl < 0))

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float('inf') if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss

    @property
    def avg_win(self) -> float:
        winning = [t.net_pnl for t in self.trades if t.result == TradeResult.WIN]
        return sum(winning) / len(winning) if winning else 0.0

    @property
    def avg_loss(self) -> float:
        losing = [t.net_pnl for t in self.trades if t.result == TradeResult.LOSS]
        return sum(losing) / len(losing) if losing else 0.0

    @property
    def avg_rr(self) -> float:
        if self.avg_loss == 0:
            return 0.0
        return abs(self.avg_win / self.avg_loss)

    @property
    def largest_win(self) -> float:
        wins = [t.net_pnl for t in self.trades if t.result == TradeResult.WIN]
        return max(wins) if wins else 0.0

    @property
    def largest_loss(self) -> float:
        losses = [t.net_pnl for t in self.trades if t.result == TradeResult.LOSS]
        return min(losses) if losses else 0.0

    @property
    def max_win_streak(self) -> int:
        max_streak = 0
        current_streak = 0
        for t in self.trades:
            if t.result == TradeResult.WIN:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        return max_streak

    @property
    def max_loss_streak(self) -> int:
        max_streak = 0
        current_streak = 0
        for t in self.trades:
            if t.result == TradeResult.LOSS:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        return max_streak

    @property
    def avg_duration_seconds(self) -> float:
        durations = [t.duration_seconds for t in self.closed_trades if t.duration_seconds]
        return sum(durations) / len(durations) if durations else 0.0

    def get_by_session(self, session: str) -> 'TradeStats':
        """Filtre les trades par session"""
        filtered = [t for t in self.trades if t.session == session]
        return TradeStats(trades=filtered)

    def get_by_symbol(self, symbol: str) -> 'TradeStats':
        """Filtre les trades par symbole"""
        filtered = [t for t in self.trades if t.symbol == symbol]
        return TradeStats(trades=filtered)

    def get_by_direction(self, direction: TradeDirection) -> 'TradeStats':
        """Filtre les trades par direction"""
        filtered = [t for t in self.trades if t.direction == direction]
        return TradeStats(trades=filtered)

    def get_summary(self) -> dict:
        """Retourne un résumé des statistiques"""
        return {
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "breakevens": self.breakevens,
            "win_rate": self.win_rate,
            "long_trades": self.long_trades,
            "short_trades": self.short_trades,
            "total_pnl": self.total_pnl,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_rr": self.avg_rr,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "max_win_streak": self.max_win_streak,
            "max_loss_streak": self.max_loss_streak,
        }

