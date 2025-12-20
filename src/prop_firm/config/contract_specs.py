"""
Spécifications des contrats futures
Tick size, tick value, point value pour ES, NQ, RTY et leurs versions micro
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class ContractSpec:
    """Spécification d'un contrat futures"""
    symbol: str
    name: str
    exchange: str
    tick_size: float          # Plus petit mouvement de prix
    tick_value: float         # Valeur en $ d'un tick
    point_value: float        # Valeur en $ d'un point (= tick_value / tick_size)
    is_micro: bool            # True si micro contract
    mini_equivalent: str      # Symbole du contrat mini équivalent (ou None)
    micro_equivalent: str     # Symbole du contrat micro équivalent (ou None)
    trading_hours: str        # Heures de trading
    margin_intraday: float    # Margin approximatif intraday
    margin_overnight: float   # Margin overnight


# ═══════════════════════════════════════════════════════════════════════════════
# SPÉCIFICATIONS DES CONTRATS
# ═══════════════════════════════════════════════════════════════════════════════

CONTRACT_SPECS: Dict[str, ContractSpec] = {

    # ─────────────────────────────────────────────────────────────────────────────
    # S&P 500 (ES / MES)
    # ─────────────────────────────────────────────────────────────────────────────
    "ES": ContractSpec(
        symbol="ES",
        name="E-mini S&P 500",
        exchange="CME",
        tick_size=0.25,
        tick_value=12.50,
        point_value=50.00,
        is_micro=False,
        mini_equivalent=None,
        micro_equivalent="MES",
        trading_hours="Sun 18:00 - Fri 17:00 ET",
        margin_intraday=500,
        margin_overnight=12000,
    ),

    "MES": ContractSpec(
        symbol="MES",
        name="Micro E-mini S&P 500",
        exchange="CME",
        tick_size=0.25,
        tick_value=1.25,
        point_value=5.00,
        is_micro=True,
        mini_equivalent="ES",
        micro_equivalent=None,
        trading_hours="Sun 18:00 - Fri 17:00 ET",
        margin_intraday=50,
        margin_overnight=1200,
    ),

    # ─────────────────────────────────────────────────────────────────────────────
    # NASDAQ 100 (NQ / MNQ)
    # ─────────────────────────────────────────────────────────────────────────────
    "NQ": ContractSpec(
        symbol="NQ",
        name="E-mini Nasdaq 100",
        exchange="CME",
        tick_size=0.25,
        tick_value=5.00,
        point_value=20.00,
        is_micro=False,
        mini_equivalent=None,
        micro_equivalent="MNQ",
        trading_hours="Sun 18:00 - Fri 17:00 ET",
        margin_intraday=500,
        margin_overnight=16000,
    ),

    "MNQ": ContractSpec(
        symbol="MNQ",
        name="Micro E-mini Nasdaq 100",
        exchange="CME",
        tick_size=0.25,
        tick_value=0.50,
        point_value=2.00,
        is_micro=True,
        mini_equivalent="NQ",
        micro_equivalent=None,
        trading_hours="Sun 18:00 - Fri 17:00 ET",
        margin_intraday=50,
        margin_overnight=1600,
    ),

    # ─────────────────────────────────────────────────────────────────────────────
    # RUSSELL 2000 (RTY / M2K)
    # ─────────────────────────────────────────────────────────────────────────────
    "RTY": ContractSpec(
        symbol="RTY",
        name="E-mini Russell 2000",
        exchange="CME",
        tick_size=0.10,
        tick_value=5.00,
        point_value=50.00,
        is_micro=False,
        mini_equivalent=None,
        micro_equivalent="M2K",
        trading_hours="Sun 18:00 - Fri 17:00 ET",
        margin_intraday=500,
        margin_overnight=7000,
    ),

    "M2K": ContractSpec(
        symbol="M2K",
        name="Micro E-mini Russell 2000",
        exchange="CME",
        tick_size=0.10,
        tick_value=0.50,
        point_value=5.00,
        is_micro=True,
        mini_equivalent="RTY",
        micro_equivalent=None,
        trading_hours="Sun 18:00 - Fri 17:00 ET",
        margin_intraday=50,
        margin_overnight=700,
    ),
}


def get_contract_spec(symbol: str) -> ContractSpec:
    """Récupère les specs d'un contrat"""
    symbol = symbol.upper()
    if symbol not in CONTRACT_SPECS:
        raise ValueError(f"Contrat '{symbol}' non supporté. Options: {list(CONTRACT_SPECS.keys())}")
    return CONTRACT_SPECS[symbol]


def calculate_pnl_from_ticks(symbol: str, ticks: int, contracts: int = 1) -> float:
    """Calcule le PnL en $ à partir du nombre de ticks"""
    spec = get_contract_spec(symbol)
    return ticks * spec.tick_value * contracts


def calculate_ticks_from_price(symbol: str, entry_price: float, exit_price: float) -> int:
    """Calcule le nombre de ticks entre deux prix"""
    spec = get_contract_spec(symbol)
    return int((exit_price - entry_price) / spec.tick_size)


def get_micro_equivalent(symbol: str) -> str:
    """Retourne le symbole micro équivalent"""
    spec = get_contract_spec(symbol)
    if spec.is_micro:
        return symbol
    return spec.micro_equivalent


def get_mini_equivalent(symbol: str) -> str:
    """Retourne le symbole mini équivalent"""
    spec = get_contract_spec(symbol)
    if not spec.is_micro:
        return symbol
    return spec.mini_equivalent


def convert_to_micros(symbol: str, mini_contracts: int) -> tuple:
    """Convertit des minis en micros (1 mini = 10 micros)"""
    spec = get_contract_spec(symbol)
    if spec.is_micro:
        return (symbol, mini_contracts)
    return (spec.micro_equivalent, mini_contracts * 10)

