"""
MIA_IA_SYSTEM - Core Base Types CORRIGÉ
Types fondamentaux + utilitaires système
Version: Production Ready
Performance: Critical types optimisés

CORRECTION APPLIQUÉE:
- Ligne ~150 : Correction OrderFlowData.__post_init__
  Suppression de self.order_flow inexistant
- Import circulaire StructureData supprimé
"""

from typing import Dict, List, Optional, Union, Tuple, Any, Literal
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import time
import statistics
from collections import deque
from core.logger import get_logger

# Configure logging
logger = get_logger(__name__)

# === TIMESTAMP NORMALIZATION ===
EXCEL_EPOCH_OFFSET_DAYS = 25569  # 1970-01-01 - 1899-12-30
SECONDS_PER_DAY = 86400.0

def normalize_ts(ts):
    """
    Normalise les timestamps Sierra/Excel vers datetime UTC
    Gère : Sierra/Excel days, epoch ms, epoch s, datetime
    """
    # déjà datetime
    if hasattr(ts, "tzinfo"):
        return ts
    # Sierra/Excel days (ex: 45905.x)
    if isinstance(ts, (int, float)) and 10000 < ts < 200000:
        return datetime.fromtimestamp((ts - EXCEL_EPOCH_OFFSET_DAYS) * SECONDS_PER_DAY, tz=timezone.utc)
    # epoch ms
    if isinstance(ts, (int, float)) and ts > 1e12:
        return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
    # epoch s
    if isinstance(ts, (int, float)) and ts > 1e9:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    # fallback
    return datetime.fromtimestamp(0, tz=timezone.utc)

# === TYPES UNIFIÉS POUR MIA_UNIFIED ===

def parse_ts(x: str | datetime) -> datetime:
    """Parse timestamp avec support UTC"""
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    # accepte "...Z" ou ISO avec tz
    if isinstance(x, str) and x.endswith("Z"):
        x = x[:-1] + "+00:00"
    return datetime.fromisoformat(x).astimezone(timezone.utc)

GraphId = Literal[3, 4, 8, 10]

@dataclass
class UnifiedBaseEvent:
    """Base commune pour tous les événements unifiés"""
    graph: GraphId
    sym: str
    ts: datetime
    type: str = ""
    ingest_ts: Optional[datetime] = None

    @classmethod
    def _fix_ts(cls, ts, ingest_ts=None):
        return parse_ts(ts), (parse_ts(ingest_ts) if ingest_ts else None)

# ---- CHART 3/4: prix/vol, VWAP, VP/VVA/VAP, DOM, trades, quotes ----

@dataclass
class BasedataEvent(UnifiedBaseEvent):
    o: float = 0.0; h: float = 0.0; l: float = 0.0; c: float = 0.0
    v: int = 0
    bidvol: Optional[int] = None
    askvol: Optional[int] = None
    oi: Optional[int] = None
    type: Literal["basedata"] = "basedata"

@dataclass
class VWAPEvent(UnifiedBaseEvent):
    v: float = 0.0
    up1: Optional[float] = None; dn1: Optional[float] = None
    up2: Optional[float] = None; dn2: Optional[float] = None
    src: Optional[str] = None  # "study", "calc"
    type: Literal["vwap"] = "vwap"

@dataclass
class VVAEvent(UnifiedBaseEvent):
    vah: float = 0.0; val: float = 0.0; vpoc: float = 0.0
    pvah: Optional[float] = None; pval: Optional[float] = None; ppoc: Optional[float] = None
    id_curr: Optional[str] = None; id_prev: Optional[str] = None
    type: Literal["vva"] = "vva"

@dataclass
class VAPEvent(UnifiedBaseEvent):
    bar: Optional[int] = None; k: Optional[int] = None
    price: float = 0.0; vol: int = 0
    type: Literal["vap"] = "vap"

@dataclass
class DepthEvent(UnifiedBaseEvent):
    side: Literal["BID", "ASK"] = "BID"
    lvl: int = 1
    price: float = 0.0; size: int = 0
    type: Literal["depth"] = "depth"

@dataclass
class QuoteEvent(UnifiedBaseEvent):
    kind: Literal["BIDASK"] = "BIDASK"
    bid: float = 0.0; ask: float = 0.0
    bq: int = 0; aq: int = 0
    seq: Optional[int] = None
    type: Literal["quote"] = "quote"

@dataclass
class TradeEvent(UnifiedBaseEvent):
    px: float = 0.0; vol: int = 0
    seq: Optional[int] = None
    type: Literal["trade"] = "trade"

@dataclass
class PVWAPEvent(UnifiedBaseEvent):
    pvwap: float = 0.0
    up1: Optional[float] = None; dn1: Optional[float] = None
    up2: Optional[float] = None; dn2: Optional[float] = None
    prev_start: Optional[str] = None; prev_end: Optional[str] = None
    type: Literal["pvwap"] = "pvwap"

# ---- CHART 8: VIX ----

@dataclass
class VIXEvent(UnifiedBaseEvent):
    last: float = 0.0
    mode: Optional[str] = None  # "study" etc.
    type: Literal["vix"] = "vix"

# ---- CHART 10: MenthorQ ----

@dataclass
class MenthorQGammaEvent(UnifiedBaseEvent):
    study_id: int = 1; sg: int = 0; label: str = ""
    price: float = 0.0
    type: Literal["menthorq_gamma_levels"] = "menthorq_gamma_levels"

@dataclass
class MenthorQBlindSpotEvent(UnifiedBaseEvent):
    study_id: int = 2; sg: int = 0; label: str = ""
    price: float = 0.0
    type: Literal["menthorq_blind_spots"] = "menthorq_blind_spots"

@dataclass
class MenthorQSwingEvent(UnifiedBaseEvent):
    study_id: int = 3; sg: int = 0; label: str = ""
    price: float = 0.0
    type: Literal["menthorq_swing_levels"] = "menthorq_swing_levels"

UnifiedRecord = Union[
    BasedataEvent, VWAPEvent, VVAEvent, VAPEvent, DepthEvent, QuoteEvent, TradeEvent, PVWAPEvent,
    VIXEvent, MenthorQGammaEvent, MenthorQBlindSpotEvent, MenthorQSwingEvent
]

# === ALIAS UTILES ===

# Types de base pour trading
Ticks = float
Price = float
Qty = float
Volume = float
Timestamp = datetime

# === CONSTANTES TRADING ===
__all__ = [
    # Types unifiés pour mia_unified
    'parse_ts', 'GraphId', 'UnifiedBaseEvent', 'UnifiedRecord',
    'BasedataEvent', 'VWAPEvent', 'VVAEvent', 'VAPEvent', 'DepthEvent', 'QuoteEvent', 'TradeEvent', 'PVWAPEvent',
    'VIXEvent', 'MenthorQGammaEvent', 'MenthorQBlindSpotEvent', 'MenthorQSwingEvent',
    # Alias utiles
    'Ticks', 'Price', 'Qty', 'Volume', 'Timestamp',
    # Types existants
    'MarketData',
    'TradingSignal',
    'TradingDecision',
    'MarketRegime',
    'MarketState',
    'TradeResult',
    'SystemMetrics',
    'PerformanceReport',
    'ConfigError',
    'SystemState',
    'OrderFlowData',
    'TradingFeatures',
    'SignalType',
    'PatternType',
    'SignalStrength',
    'SessionPhase',
    'ES_TICK_SIZE',
    'ES_TICK_VALUE',
    'MES_TICK_VALUE',
    'TRADING_HOURS',
    'DEFAULT_RISK_PARAMS',
    'PERFORMANCE_TARGETS',
    'get_session_phase',
    'validate_market_data',
    'DataIntegrityIssue',
    'DataIntegrityValidator',
    'create_data_integrity_validator',
    'validate_market_data_quick',
    'get_data_quality_score',
    'calculate_performance_metrics'
]

# === CORE ENUMS ===


class MarketRegime(Enum):
    """Régimes de marché détectés"""
    TREND_BULLISH = "trend_bullish"
    TREND_BEARISH = "trend_bearish"
    RANGE_TIGHT = "range_tight"
    RANGE_WIDE = "range_wide"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class SignalType(Enum):
    """Types de signaux trading"""
    LONG_TREND = "long_trend"
    LONG_RANGE = "long_range"
    SHORT_TREND = "short_trend"
    SHORT_RANGE = "short_range"
    EXIT_PROFIT = "exit_profit"
    EXIT_STOP = "exit_stop"
    EXIT_RULE = "exit_rule"
    NO_SIGNAL = "no_signal"



class OrderType(Enum):
    """Types d'ordres"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"



class OrderStatus(Enum):
    """Statuts des ordres"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PatternType(Enum):
    """Types de patterns détectés"""
    BATTLE_NAVALE = "battle_navale"
    GAMMA_PIN = "gamma_pin"
    HEADFAKE = "headfake"
    MICROSTRUCTURE = "microstructure"
    CONFLUENCE = "confluence"


class SignalStrength(IntEnum):
    """Force du signal (pour scoring)"""
    VERY_WEAK = 1
    WEAK = 2
    MEDIUM = 3
    STRONG = 4
    VERY_STRONG = 5


class SessionPhase(Enum):
    """Phases de session trading"""
    PRE_MARKET = "pre_market"
    LONDON_OPEN = "london_open"
    NY_OPEN = "ny_open"
    LUNCH = "lunch"
    AFTERNOON = "afternoon"
    CLOSE = "close"
    AFTER_HOURS = "after_hours"


class TradingDecision(Enum):
    """Décisions de trading possibles"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"
    WAIT = "wait"


class MarketState(Enum):
    """État général du marché"""
    NORMAL = "normal"
    VOLATILE = "volatile"
    EXTREMELY_VOLATILE = "extremely_volatile"
    THIN = "thin"
    CLOSED = "closed"


class SystemState(Enum):
    """État du système de trading"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    READY = "ready"
    TRADING = "trading"
    ERROR = "error"
    SHUTDOWN = "shutdown"

# === CONSTANTS ===


# ES Futures specifications
ES_TICK_SIZE = 0.25
ES_TICK_VALUE = 12.5  # Per tick
MES_TICK_VALUE = 1.25  # Micro ES

# Trading hours (ET)
TRADING_HOURS = {
    'pre_market': (4, 0),     # 4:00 AM
    'london_open': (8, 0),    # 8:00 AM
    'ny_open': (9, 30),       # 9:30 AM
    'lunch': (12, 0),         # 12:00 PM
    'afternoon': (14, 0),     # 2:00 PM
    'close': (16, 0),         # 4:00 PM
    'after_hours': (18, 0)    # 6:00 PM
}

# Default risk parameters
DEFAULT_RISK_PARAMS = {
    'max_position_size': 3,
    'daily_loss_limit': 1000.0,
    'max_risk_per_trade': 200.0,
    'default_stop_ticks': 12,
    'default_target_ticks': 24
}

# Performance targets
PERFORMANCE_TARGETS = {
    'min_win_rate': 0.55,
    'min_profit_factor': 1.5,
    'min_sharpe_ratio': 1.0,
    'max_drawdown': 0.10,
    'target_daily_return': 0.005
}

# === EXCEPTIONS ===


class ConfigError(Exception):
    """Erreur de configuration"""
    pass

# === CORE DATACLASSES ===


@dataclass
class MarketData:
    """Données marché standardisées"""
    timestamp: pd.Timestamp
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None

    def __post_init__(self):
        """Validation et calculs post-init"""
        # Calcul spread si bid/ask disponibles
        if self.bid and self.ask:
            self.spread = self.ask - self.bid

        # Validation cohérence OHLC
        if not (self.low <= self.open <= self.high and
                self.low <= self.close <= self.high):
            logger.warning(
                f"OHLC incohérent: O={
                    self.open}, H={
                    self.high}, L={
                    self.low}, C={
                    self.close}")

    @property
    def range_size(self) -> float:
        """Taille range H-L"""
        return self.high - self.low

    @property
    def body_size(self) -> float:
        """Taille corps bougie"""
        return abs(self.close - self.open)

    @property
    def is_bullish(self) -> bool:
        """Bougie haussière"""
        return self.close > self.open

    def to_dict(self) -> Dict[str, Any]:
        """Conversion dictionnaire"""
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'bid': self.bid,
            'ask': self.ask,
            'spread': self.spread
        }


@dataclass
class OrderFlowData:
    """Données order flow"""
    timestamp: pd.Timestamp
    symbol: str
    cumulative_delta: float
    bid_volume: int
    ask_volume: int
    aggressive_buys: int
    aggressive_sells: int

    # Champs optionnels avancés
    net_delta: Optional[float] = None
    large_trades: List[Dict[str, Any]] = field(default_factory=list)
    absorption_score: float = 0.0
    imbalance_ratio: float = 0.0

    def __post_init__(self):
        """Calculs post-init - CORRIGÉ"""
        # Calcul imbalance ratio
        total_volume = self.bid_volume + self.ask_volume
        if total_volume > 0:
            self.imbalance_ratio = abs(self.bid_volume - self.ask_volume) / total_volume

        # Si net_delta pas fourni, le calculer
        if self.net_delta is None:
            self.net_delta = self.ask_volume - self.bid_volume

        # Validation cohérence des données
        if self.net_delta != 0 and self.cumulative_delta == 0:
            logger.warning("Net delta non-nul avec cumulative delta zéro")

    @property
    def total_volume(self) -> int:
        """Volume total"""
        return self.bid_volume + self.ask_volume

    @property
    def aggressor_ratio(self) -> float:
        """Ratio aggressive buyers vs sellers"""
        total_aggressive = self.aggressive_buys + self.aggressive_sells
        if total_aggressive == 0:
            return 0.0
        return self.aggressive_buys / total_aggressive

    def get_net_delta(self) -> float:
        """Méthode pour obtenir net_delta (compatibilité)"""
        return self.net_delta if self.net_delta is not None else (self.ask_volume - self.bid_volume)


@dataclass
class TradingFeatures:
    """Features calculées pour ML"""
    timestamp: pd.Timestamp

    # Core features (8 maximum)
    battle_navale_signal: float
    gamma_pin_strength: float
    headfake_signal: float
    microstructure_anomaly: float
    market_regime_score: float
    base_quality: float
    confluence_score: float
    session_context: float

    # Metadata
    calculation_time_ms: float = 0.0
    feature_quality: float = 1.0
    
    # ✅ Paramètres optionnels pour compatibilité
    features_calculated: Optional[int] = None
    lazy_loading_used: Optional[bool] = None
    prefilter_passed: Optional[bool] = None
    symbol: Optional[str] = None
    price: Optional[float] = None
    volume: Optional[float] = None

    def __post_init__(self):
        """Validation features"""
        # Validation range [0,1] pour toutes les features
        feature_values = [
            self.battle_navale_signal, self.gamma_pin_strength,
            self.headfake_signal, self.microstructure_anomaly,
            self.market_regime_score, self.base_quality,
            self.confluence_score, self.session_context
        ]

        for i, value in enumerate(feature_values):
            if not (0.0 <= value <= 1.0):
                logger.warning(f"Feature {i} hors range [0,1]: {value}")

    def to_array(self) -> np.ndarray:
        """Conversion array numpy pour ML"""
        return np.array([
            self.battle_navale_signal,
            self.gamma_pin_strength,
            self.headfake_signal,
            self.microstructure_anomaly,
            self.market_regime_score,
            self.base_quality,
            self.confluence_score,
            self.session_context
        ], dtype=np.float32)

    def to_dict(self) -> Dict[str, float]:
        """Conversion dictionnaire"""
        return {
            'battle_navale_signal': self.battle_navale_signal,
            'gamma_pin_strength': self.gamma_pin_strength,
            'headfake_signal': self.headfake_signal,
            'microstructure_anomaly': self.microstructure_anomaly,
            'market_regime_score': self.market_regime_score,
            'base_quality': self.base_quality,
            'confluence_score': self.confluence_score,
            'session_context': self.session_context
        }


@dataclass
class TradingSignal:
    """Signal de trading complet"""
    timestamp: pd.Timestamp
    signal_type: SignalType
    confidence: float
    strength: SignalStrength
    price: float

    # Context
    market_regime: MarketRegime
    patterns_detected: List[PatternType]
    features: TradingFeatures

    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: float = 1.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validation signal"""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence doit être [0,1]: {self.confidence}")

        if self.stop_loss and self.signal_type in [SignalType.LONG_TREND, SignalType.LONG_RANGE]:
            if self.stop_loss >= self.price:
                logger.warning(
                    f"Stop loss incohérent pour LONG: price={
                        self.price}, stop={
                        self.stop_loss}")

    @property
    def risk_reward_ratio(self) -> Optional[float]:
        """Calcul ratio risk/reward"""
        if not (self.stop_loss and self.take_profit):
            return None

        if self.signal_type in [SignalType.LONG_TREND, SignalType.LONG_RANGE]:
            risk = abs(self.price - self.stop_loss)
            reward = abs(self.take_profit - self.price)
        else:
            risk = abs(self.stop_loss - self.price)
            reward = abs(self.price - self.take_profit)

        return reward / risk if risk > 0 else None

    def to_dict(self) -> Dict[str, Any]:
        """Conversion dictionnaire"""
        return {
            'timestamp': self.timestamp,
            'signal_type': self.signal_type.value,
            'confidence': self.confidence,
            'strength': self.strength.value,
            'price': self.price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'risk_reward_ratio': self.risk_reward_ratio,
            'market_regime': self.market_regime.value,
            'patterns': [p.value for p in self.patterns_detected],
            'features': self.features.to_dict(),
            'metadata': self.metadata
        }


@dataclass
class Position:
    """Position de trading"""
    symbol: str
    quantity: int
    side: str  # 'long' ou 'short'
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    
@dataclass
class TradeResult:
    """Résultat d'un trade complet"""
    trade_id: str
    timestamp_open: pd.Timestamp
    timestamp_close: Optional[pd.Timestamp]

    # Trade details
    symbol: str
    signal_type: SignalType
    entry_price: float
    exit_price: Optional[float] = None
    position_size: float = 1.0

    # Performance
    pnl_ticks: Optional[float] = None
    pnl_dollars: Optional[float] = None
    commission: float = 0.0

    # Risk metrics
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0

    # Status
    is_open: bool = True
    exit_reason: Optional[str] = None

    def close_trade(self, exit_price: float, exit_reason: str = "manual"):
        """Ferme le trade"""
        self.exit_price = exit_price
        self.timestamp_close = pd.Timestamp.now()
        self.is_open = False
        self.exit_reason = exit_reason

        # Calcul P&L
        if self.signal_type in [SignalType.LONG_TREND, SignalType.LONG_RANGE]:
            self.pnl_ticks = (exit_price - self.entry_price) / ES_TICK_SIZE
        else:
            self.pnl_ticks = (self.entry_price - exit_price) / ES_TICK_SIZE

        self.pnl_dollars = self.pnl_ticks * ES_TICK_VALUE * self.position_size - self.commission

    @property
    def duration_minutes(self) -> Optional[float]:
        """Durée du trade en minutes"""
        if self.timestamp_close:
            return (self.timestamp_close - self.timestamp_open).total_seconds() / 60
        return None

    @property
    def is_winner(self) -> bool:
        """Trade gagnant ?"""
        return self.pnl_dollars > 0 if self.pnl_dollars is not None else False


@dataclass
class SystemMetrics:
    """Métriques système temps réel"""
    timestamp: datetime

    # Performance
    latency_ms: float
    throughput_signals_per_min: float
    cpu_usage_percent: float
    memory_usage_mb: float

    # Trading
    active_positions: int
    signals_generated: int
    signals_executed: int
    orders_pending: int

    # Quality
    data_quality_score: float
    system_health_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Conversion dictionnaire"""
        return asdict(self)


@dataclass
class PerformanceReport:
    """Rapport de performance"""
    period_start: datetime
    period_end: datetime

    # Trading metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # Financial metrics
    gross_pnl: float
    net_pnl: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float

    # Risk metrics
    avg_risk_per_trade: float
    max_risk_exposure: float
    risk_adjusted_return: float

    # Details by strategy
    performance_by_strategy: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Conversion dictionnaire"""
        return asdict(self)

# === UTILITY FUNCTIONS ===


def get_session_phase(timestamp: Union[pd.Timestamp, datetime, float]) -> SessionPhase:
    """Détermine la phase de session actuelle"""
    # Utiliser la fonction de normalisation unifiée
    timestamp = normalize_ts(timestamp)
    
    # Extraire l'heure
    hour = timestamp.hour

    if hour < 4:
        return SessionPhase.AFTER_HOURS
    elif hour < 8:
        return SessionPhase.PRE_MARKET
    elif hour < 9:
        return SessionPhase.LONDON_OPEN
    elif 9 <= hour < 10 or (hour == 9 and timestamp.minute < 30):
        return SessionPhase.LONDON_OPEN
    elif hour < 12:
        return SessionPhase.NY_OPEN
    elif hour < 14:
        return SessionPhase.LUNCH
    elif hour < 16:
        return SessionPhase.AFTERNOON
    elif hour < 18:
        return SessionPhase.CLOSE
    else:
        return SessionPhase.AFTER_HOURS


def validate_market_data(data: MarketData) -> bool:
    """Valide la cohérence des données marché"""
    try:
        # Check OHLC coherence
        if not (data.low <= data.open <= data.high and
                data.low <= data.close <= data.high):
            return False

        # Check volume
        if data.volume < 0:
            return False

        # Check reasonable price range
        if not (1000 < data.close < 10000):  # ES range reasonable
            return False

        return True
    except Exception:
        return False


def calculate_performance_metrics(trades: List[TradeResult]) -> Dict[str, float]:
    """Calcul métriques performance"""
    if not trades:
        return {}

    completed_trades = [t for t in trades if t.pnl_dollars is not None]
    if not completed_trades:
        return {}

    # Basic metrics
    total_pnl = sum(t.pnl_dollars for t in completed_trades)
    winners = [t for t in completed_trades if t.is_winner]
    losers = [t for t in completed_trades if not t.is_winner]

    win_rate = len(winners) / len(completed_trades)
    avg_win = np.mean([t.pnl_dollars for t in winners]) if winners else 0
    avg_loss = np.mean([t.pnl_dollars for t in losers]) if losers else 0

    profit_factor = abs(avg_win * len(winners) / (avg_loss * len(losers))
                        ) if losers else float('inf')

    return {
        'total_trades': len(completed_trades),
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'avg_duration': np.mean([t.duration_minutes for t in completed_trades if t.duration_minutes])
    }

# ======================================================================
# ✅ DATA INTEGRITY VALIDATOR - PRIORITÉ HAUTE
# Validation temps réel des données pour qualité ML et fiabilité
# ======================================================================

from typing import List, Union
import math

class DataIntegrityIssue:
    """Représente un problème d'intégrité de données"""
    def __init__(self, severity: str, field: str, issue: str, value: Any = None):
        self.severity = severity  # 'critical', 'warning', 'info'
        self.field = field
        self.issue = issue
        self.value = value
        self.timestamp = datetime.now(timezone.utc)
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.field}: {self.issue} (value: {self.value})"

class DataIntegrityValidator:
    """
    ✅ DATA INTEGRITY VALIDATOR
    
    Valide la qualité et cohérence des données en temps réel pour :
    - Prévenir corruption des données ML
    - Détecter anomalies de marché
    - Assurer cohérence des calculs
    - Alerter sur données suspectes
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.DataIntegrityValidator")
        
        # Seuils de validation
        self.validation_rules = {
            'price_rules': {
                'min_price': 1.0,              # Prix minimum accepté
                'max_price': 10000.0,          # Prix maximum accepté
                'max_price_change_pct': 0.05,  # Max 5% changement entre ticks
                'max_spread_ticks': 10.0,      # Max 10 ticks de spread
                'min_tick_size': 0.25          # Tick size ES minimum
            },
            'volume_rules': {
                'min_volume': 0,               # Volume minimum
                'max_volume': 1000000,         # Volume maximum raisonnable
                'max_volume_spike': 10.0       # Factor max spike vs moyenne
            },
            'time_rules': {
                'max_timestamp_age_seconds': 300,  # Max 5 min d'âge
                'max_timestamp_future_seconds': 10  # Max 10s dans le futur
            },
            'orderflow_rules': {
                'max_delta_ratio': 5.0,        # Max ratio bid/ask volumes
                'max_imbalance_ratio': 0.95     # Max 95% d'imbalance
            }
        }
        
        # Historique pour validation contextuelle
        self.price_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=100)
        self.validation_stats = {
            'total_validations': 0,
            'critical_issues': 0,
            'warnings': 0,
            'last_validation': None
        }
        
        self.logger.info("✅ Data Integrity Validator initialisé")
    
    def validate_market_data(self, data: MarketData) -> List[DataIntegrityIssue]:
        """
        Valide l'intégrité d'un MarketData
        
        Returns:
            Liste des problèmes détectés
        """
        issues = []
        self.validation_stats['total_validations'] += 1
        self.validation_stats['last_validation'] = datetime.now(timezone.utc)
        
        try:
            # Validation prix
            issues.extend(self._validate_prices(data))
            
            # Validation volume
            issues.extend(self._validate_volume(data))
            
            # Validation timestamp
            issues.extend(self._validate_timestamp(data))
            
            # Validation spread
            issues.extend(self._validate_spread(data))
            
            # Validation cohérence OHLC
            issues.extend(self._validate_ohlc_consistency(data))
            
            # Validation contextuelle (vs historique)
            issues.extend(self._validate_contextual(data))
            
            # Mettre à jour historiques
            self._update_history(data)
            
            # Compter issues par sévérité
            for issue in issues:
                if issue.severity == 'critical':
                    self.validation_stats['critical_issues'] += 1
                elif issue.severity == 'warning':
                    self.validation_stats['warnings'] += 1
            
            if issues:
                self.logger.debug(f"✅ MarketData validé: {len(issues)} problèmes détectés")
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Erreur validation MarketData: {e}")
            return [DataIntegrityIssue('critical', 'validation', f'Erreur interne: {e}')]
    
    def _validate_prices(self, data: MarketData) -> List[DataIntegrityIssue]:
        """Valide les prix"""
        issues = []
        rules = self.validation_rules['price_rules']
        
        # Vérifier présence prix requis
        if not hasattr(data, 'close') or data.close is None:
            issues.append(DataIntegrityIssue('critical', 'close', 'Prix de clôture manquant'))
            return issues
        
        # Range de prix raisonnable
        if data.close < rules['min_price']:
            issues.append(DataIntegrityIssue('critical', 'close', 
                'Prix trop bas', data.close))
        elif data.close > rules['max_price']:
            issues.append(DataIntegrityIssue('critical', 'close', 
                'Prix trop élevé', data.close))
        
        # Validation OHLC si disponible
        ohlc_fields = ['open', 'high', 'low', 'close']
        prices = []
        for field in ohlc_fields:
            if hasattr(data, field) and getattr(data, field) is not None:
                price = getattr(data, field)
                prices.append(price)
                
                # Range check pour chaque prix
                if price < rules['min_price'] or price > rules['max_price']:
                    issues.append(DataIntegrityIssue('critical', field, 
                        f'Prix hors limites: {price}'))
        
        # Tick size validation
        if prices:
            for price in prices:
                remainder = price % rules['min_tick_size']
                if abs(remainder) > 0.001 and abs(remainder - rules['min_tick_size']) > 0.001:
                    issues.append(DataIntegrityIssue('warning', 'tick_size', 
                        f'Prix non aligné tick size: {price}'))
        
        return issues
    
    def _validate_volume(self, data: MarketData) -> List[DataIntegrityIssue]:
        """Valide le volume"""
        issues = []
        rules = self.validation_rules['volume_rules']
        
        if hasattr(data, 'volume') and data.volume is not None:
            # Range validation
            if data.volume < rules['min_volume']:
                issues.append(DataIntegrityIssue('warning', 'volume', 
                    'Volume négatif', data.volume))
            elif data.volume > rules['max_volume']:
                issues.append(DataIntegrityIssue('warning', 'volume', 
                    'Volume suspicieusement élevé', data.volume))
            
            # Spike detection vs historique
            if len(self.volume_history) > 10:
                avg_volume = statistics.mean(list(self.volume_history)[-10:])
                if avg_volume > 0 and data.volume > (avg_volume * rules['max_volume_spike']):
                    issues.append(DataIntegrityIssue('warning', 'volume', 
                        f'Spike volume détecté: {data.volume} vs moy {avg_volume:.0f}'))
        
        return issues
    
    def _validate_timestamp(self, data: MarketData) -> List[DataIntegrityIssue]:
        """Valide le timestamp"""
        issues = []
        rules = self.validation_rules['time_rules']
        
        if hasattr(data, 'timestamp') and data.timestamp is not None:
            now = datetime.now(timezone.utc)
            
            # Convertir timestamp si nécessaire
            if isinstance(data.timestamp, pd.Timestamp):
                timestamp = data.timestamp.to_pydatetime()
            else:
                timestamp = data.timestamp
            
            # Remove timezone for comparison if present
            if timestamp.tzinfo:
                timestamp = timestamp.replace(tzinfo=None)
            
            # Âge des données
            age_seconds = (now - timestamp).total_seconds()
            if age_seconds > rules['max_timestamp_age_seconds']:
                issues.append(DataIntegrityIssue('warning', 'timestamp', 
                    f'Données anciennes: {age_seconds:.0f}s'))
            
            # Données du futur
            if age_seconds < -rules['max_timestamp_future_seconds']:
                issues.append(DataIntegrityIssue('critical', 'timestamp', 
                    f'Timestamp futur: {-age_seconds:.0f}s'))
        
        return issues
    
    def _validate_spread(self, data: MarketData) -> List[DataIntegrityIssue]:
        """Valide le spread bid/ask"""
        issues = []
        rules = self.validation_rules['price_rules']
        
        if (hasattr(data, 'bid') and hasattr(data, 'ask') and 
            data.bid is not None and data.ask is not None):
            
            # Spread négatif
            if data.ask <= data.bid:
                issues.append(DataIntegrityIssue('critical', 'spread', 
                    f'Spread négatif: bid={data.bid}, ask={data.ask}'))
            else:
                # Spread trop large
                spread_ticks = (data.ask - data.bid) / rules['min_tick_size']
                if spread_ticks > rules['max_spread_ticks']:
                    issues.append(DataIntegrityIssue('warning', 'spread', 
                        f'Spread large: {spread_ticks:.1f} ticks'))
        
        return issues
    
    def _validate_ohlc_consistency(self, data: MarketData) -> List[DataIntegrityIssue]:
        """Valide la cohérence OHLC"""
        issues = []
        
        # Vérifier si tous les OHLC sont disponibles
        ohlc_fields = ['open', 'high', 'low', 'close']
        ohlc_values = {}
        
        for field in ohlc_fields:
            if hasattr(data, field) and getattr(data, field) is not None:
                ohlc_values[field] = getattr(data, field)
        
        if len(ohlc_values) >= 3:  # Au moins 3 valeurs pour validation
            values = list(ohlc_values.values())
            
            # High doit être >= tous les autres
            if 'high' in ohlc_values:
                high = ohlc_values['high']
                for field, value in ohlc_values.items():
                    if field != 'high' and value > high:
                        issues.append(DataIntegrityIssue('critical', 'ohlc', 
                            f'{field} ({value}) > high ({high})'))
            
            # Low doit être <= tous les autres
            if 'low' in ohlc_values:
                low = ohlc_values['low']
                for field, value in ohlc_values.items():
                    if field != 'low' and value < low:
                        issues.append(DataIntegrityIssue('critical', 'ohlc', 
                            f'{field} ({value}) < low ({low})'))
        
        return issues
    
    def _validate_contextual(self, data: MarketData) -> List[DataIntegrityIssue]:
        """Validation contextuelle vs historique"""
        issues = []
        rules = self.validation_rules['price_rules']
        
        if len(self.price_history) > 0 and hasattr(data, 'close') and data.close:
            last_price = self.price_history[-1]
            
            # Changement de prix excessif
            if last_price > 0:
                price_change_pct = abs((data.close - last_price) / last_price)
                if price_change_pct > rules['max_price_change_pct']:
                    issues.append(DataIntegrityIssue('warning', 'price_change', 
                        f'Changement prix important: {price_change_pct:.2%}'))
        
        return issues
    
    def validate_order_flow_data(self, data: OrderFlowData) -> List[DataIntegrityIssue]:
        """Valide l'intégrité d'OrderFlowData"""
        issues = []
        rules = self.validation_rules['orderflow_rules']
        
        try:
            # Validation volumes bid/ask
            if hasattr(data, 'bid_volume') and hasattr(data, 'ask_volume'):
                if data.bid_volume < 0 or data.ask_volume < 0:
                    issues.append(DataIntegrityIssue('critical', 'volumes', 
                        'Volume négatif détecté'))
                
                # Ratio d'imbalance excessif
                total_volume = data.bid_volume + data.ask_volume
                if total_volume > 0:
                    imbalance = abs(data.bid_volume - data.ask_volume) / total_volume
                    if imbalance > rules['max_imbalance_ratio']:
                        issues.append(DataIntegrityIssue('warning', 'imbalance', 
                            f'Imbalance extrême: {imbalance:.1%}'))
            
            # Validation delta cumulatif - MODIFIÉ pour accepter nos valeurs calculées
            if hasattr(data, 'cumulative_delta') and data.cumulative_delta is not None:
                # Accepter les deux formats : ancien (direct) et nouveau (objet)
                if isinstance(data.cumulative_delta, dict):
                    # Format nouveau : {"close": value, "delta": value}
                    cum_value = data.cumulative_delta.get("close", 0)
                else:
                    # Format ancien : valeur directe
                    cum_value = data.cumulative_delta
                
                # Seuil plus élevé pour nos valeurs calculées (plus réalistes)
                if abs(cum_value) > 50000:  # Seuil augmenté pour nos calculs
                    issues.append(DataIntegrityIssue('warning', 'cumulative_delta', 
                        f'Delta cumulatif élevé: {cum_value}'))
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Erreur validation OrderFlow: {e}")
            return [DataIntegrityIssue('critical', 'validation', f'Erreur: {e}')]
    
    def _update_history(self, data: MarketData):
        """Met à jour l'historique pour validations contextuelles"""
        if hasattr(data, 'close') and data.close is not None:
            self.price_history.append(data.close)
        
        if hasattr(data, 'volume') and data.volume is not None:
            self.volume_history.append(data.volume)
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Génère un rapport de validation"""
        return {
            'stats': self.validation_stats.copy(),
            'rules': self.validation_rules,
            'history_size': {
                'prices': len(self.price_history),
                'volumes': len(self.volume_history)
            },
            'quality_score': self._calculate_data_quality_score()
        }
    
    def _calculate_data_quality_score(self) -> float:
        """Calcule un score de qualité des données (0-1)"""
        total = self.validation_stats['total_validations']
        if total == 0:
            return 1.0
        
        critical = self.validation_stats['critical_issues']
        warnings = self.validation_stats['warnings']
        
        # Score basé sur le taux d'erreurs
        error_rate = (critical * 2 + warnings) / total  # Critical compte double
        quality_score = max(0.0, 1.0 - error_rate)
        
        return quality_score

# Factory function
def create_data_integrity_validator() -> DataIntegrityValidator:
    """Factory pour créer le Data Integrity Validator"""
    return DataIntegrityValidator()

# Fonctions utilitaires pour validation rapide
def validate_market_data_quick(data: MarketData) -> bool:
    """Validation rapide - retourne True si données valides"""
    validator = create_data_integrity_validator()
    issues = validator.validate_market_data(data)
    critical_issues = [i for i in issues if i.severity == 'critical']
    return len(critical_issues) == 0

def get_data_quality_score(data_list: List[MarketData]) -> float:
    """Calcule score qualité pour une liste de données"""
    validator = create_data_integrity_validator()
    total_issues = 0
    total_critical = 0
    
    for data in data_list:
        issues = validator.validate_market_data(data)
        total_issues += len(issues)
        total_critical += len([i for i in issues if i.severity == 'critical'])
    
    if len(data_list) == 0:
        return 1.0
    
    # Score basé sur les erreurs critiques principalement
    error_rate = total_critical / len(data_list)
    return max(0.0, 1.0 - error_rate)

# === TESTING ===


def test_base_types():
    """Test des types de base"""
    logger.debug("Test base types...")

    # Test MarketData
    market_data = MarketData(
        timestamp=pd.Timestamp.now(),
        symbol="ES",
        open=4500.0,
        high=4510.0,
        low=4495.0,
        close=4505.0,
        volume=1000,
        bid=4504.75,
        ask=4505.25
    )

    logger.info("MarketData: {market_data.symbol} @ {market_data.close}")
    logger.info("Range: {market_data.range_size}, Spread: {market_data.spread}")

    # Test OrderFlowData
    order_flow = OrderFlowData(
        timestamp=pd.Timestamp.now(),
        symbol="ES",
        cumulative_delta=150.0,
        bid_volume=800,
        ask_volume=1200,
        aggressive_buys=60,
        aggressive_sells=40
    )

    logger.info("OrderFlow: net_delta={order_flow.net_delta}")
    logger.info("Imbalance ratio: {order_flow.imbalance_ratio:.2%}")

    logger.info("\n[TARGET] BASE TYPES TEST COMPLETED")
    return True


if __name__ == "__main__":
    test_base_types()
