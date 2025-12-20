#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Core Trading Types
Types communs pour éviter imports circulaires entre modules execution
Version: v2.0 - Types standardisés pour signaux et exécution

Ce module contient les types de base utilisés par tous les modules
d'exécution pour éviter les dépendances circulaires.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Literal, Sequence
from enum import Enum

def utcnow() -> datetime:
    """Timestamp UTC actuel"""
    return datetime.now(timezone.utc)

# ---- Enums / aliases ----
Side = Literal["BUY", "SELL"]
SignalName = Literal["GO_LONG", "GO_SHORT", "NO_TRADE", "NEUTRAL"]
VIXRegime = Literal["LOW", "MID", "HIGH"]

class TradingMode(Enum):
    """Mode de trading unifié pour tout le système"""
    DATA_COLLECTION = "data_collection"
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"

class Position(Enum):
    """Position unifié pour tout le système"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    PENDING = "PENDING"

class AutomationStatus(Enum):
    """Statut automation unifié"""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

# ---- Contexte d'analyse ----
@dataclass
class SignalProbe:
    """Contexte pour l'analyse de signaux"""
    symbol: str
    last_price: float
    vix: Optional[float] = None
    vix_regime: Optional[VIXRegime] = None
    ts: datetime = field(default_factory=utcnow)

# ---- Décision/Signal standardisé ----
@dataclass
class Decision:
    """Décision standardisée pour MenthorQ + Battle Navale"""
    name: SignalName                 # e.g., "GO_LONG"
    score: float                     # [-1..+1]
    strength_bn: float               # force Battle Navale [0..1]
    strength_mq: float               # force MenthorQ [0..1]
    hard_rules_triggered: bool = False
    near_bl: bool = False
    d_bl_ticks: Optional[float] = None
    position_sizing: float = 0.0     # [0..1]
    rationale: list[str] = field(default_factory=list)
    ts: datetime = field(default_factory=utcnow)

# ---- Plan d'exécution (risk) ----
@dataclass
class ExecutionPlan:
    """Plan d'exécution avec gestion des risques"""
    side: Optional[Side] = None
    qty: float = 0.0
    entry: Optional[float] = None
    stop: Optional[float] = None
    take_profits: Sequence[float] = field(default_factory=tuple)
    reduce_only: bool = False
    ts: datetime = field(default_factory=utcnow)

# ---- Ordres / Fills ----
@dataclass
class OrderRequest:
    """Requête d'ordre vers Sierra DTC"""
    symbol: str
    side: Side
    qty: float
    kind: Literal["MKT", "LMT"] = "MKT"
    limit_price: Optional[float] = None
    client_tag: Optional[str] = None
    ts: datetime = field(default_factory=utcnow)

@dataclass
class OrderResult:
    """Résultat d'ordre depuis Sierra DTC"""
    ok: bool
    order_id: Optional[str]
    status: str
    raw: Optional[bytes] = None
    error: Optional[str] = None
    ts: datetime = field(default_factory=utcnow)

@dataclass
class OrderFill:
    """Fill d'ordre"""
    order_id: str
    symbol: str
    side: Side
    avg_px: float
    qty: float
    ts: datetime = field(default_factory=utcnow)

# ---- Position ----
@dataclass
class PositionState:
    """État de position"""
    symbol: str
    qty: float = 0.0
    avg_px: float = 0.0
    unrealized_pnl: float = 0.0
    ts: datetime = field(default_factory=utcnow)

# ---- Signal simplifié pour RiskManager ----
@dataclass
class TradingSignal:
    """Signal de trading simplifié pour RiskManager"""
    timestamp: datetime
    symbol: str
    action: str  # 'LONG', 'SHORT', etc.
    entry_price: float
    confidence: float = 0.5
    strategy: str = 'unknown'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: dict = field(default_factory=dict)

# Export control
__all__ = [
    # Enums existants
    'TradingMode', 'Position', 'AutomationStatus',
    # Types de signaux
    'Side', 'SignalName', 'VIXRegime', 'SignalProbe', 'Decision', 'TradingSignal',
    # Types d'exécution
    'ExecutionPlan', 'OrderRequest', 'OrderResult', 'OrderFill', 'PositionState',
    # Utilitaires
    'utcnow'
]

# Version info
__version__ = "2.0.0"