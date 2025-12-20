#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bracket Helper - Utilitaires pour ordres bracket avec calcul ticks

Facilite la création d'ordres bracket avec :
- Calcul automatique TP/SL en ticks
- Support MARKET et LIMIT
- Validation des prix
"""
from typing import Dict, Optional, Literal
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)


# === CONFIGURATION INSTRUMENTS ===

@dataclass
class InstrumentConfig:
    """Configuration d'un instrument"""
    tick_size: float      # Taille d'un tick en points
    tick_value: float     # Valeur d'un tick en dollars
    min_tick: float       # Tick minimum
    exchange: str         # Exchange


INSTRUMENTS = {
    "ES": InstrumentConfig(
        tick_size=0.25,
        tick_value=12.50,
        min_tick=0.25,
        exchange="CME"
    ),
    "NQ": InstrumentConfig(
        tick_size=0.25,
        tick_value=5.00,
        min_tick=0.25,
        exchange="CME"
    ),
    "YM": InstrumentConfig(
        tick_size=1.0,
        tick_value=5.00,
        min_tick=1.0,
        exchange="CBOT"
    ),
    "RTY": InstrumentConfig(
        tick_size=0.10,
        tick_value=5.00,
        min_tick=0.10,
        exchange="CME"
    ),
}


def get_instrument_config(symbol: str) -> InstrumentConfig:
    """
    Récupère la config d'un instrument depuis son symbole

    Args:
        symbol: Symbole (ESZ25-CME, NQ, etc)

    Returns:
        InstrumentConfig
    """
    # Extraire instrument depuis symbole
    for instrument in INSTRUMENTS.keys():
        if instrument in symbol.upper():
            return INSTRUMENTS[instrument]

    # Par défaut ES
    logger.warning(f"Instrument non reconnu dans {symbol}, utilisation config ES par défaut")
    return INSTRUMENTS["ES"]


def calculate_bracket_prices(
    entry_price: float,
    side: Literal["BUY", "SELL"],
    tp_ticks: int,
    sl_ticks: int,
    tick_size: float
) -> Dict[str, float]:
    """
    Calcule les prix TP et SL à partir des ticks

    Args:
        entry_price: Prix d'entrée
        side: "BUY" ou "SELL"
        tp_ticks: Nombre de ticks pour TP (toujours positif)
        sl_ticks: Nombre de ticks pour SL (toujours positif)
        tick_size: Taille d'un tick

    Returns:
        Dict avec tp_price, sl_price, tp_dollars, sl_dollars, risk_reward

    Examples:
        >>> calculate_bracket_prices(6900.0, "BUY", 100, 60, 0.25)
        {
            'tp_price': 6925.0,
            'sl_price': 6885.0,
            'tp_dollars': 312.5,
            'sl_dollars': 187.5,
            'risk_reward': 1.67
        }
    """
    if side.upper() == "BUY":
        tp_price = entry_price + (tp_ticks * tick_size)
        sl_price = entry_price - (sl_ticks * tick_size)
    else:  # SELL
        tp_price = entry_price - (tp_ticks * tick_size)
        sl_price = entry_price + (sl_ticks * tick_size)

    # Calcul valeur en dollars (approximatif, dépend de l'instrument)
    tp_dollars = tp_ticks * tick_size * 50  # Approximation pour ES
    sl_dollars = sl_ticks * tick_size * 50

    # Risk/Reward ratio
    risk_reward = tp_ticks / sl_ticks if sl_ticks > 0 else 0

    return {
        "tp_price": round(tp_price, 2),
        "sl_price": round(sl_price, 2),
        "tp_dollars": round(tp_dollars, 2),
        "sl_dollars": round(sl_dollars, 2),
        "risk_reward": round(risk_reward, 2)
    }


def validate_bracket_prices(
    entry_price: float,
    side: Literal["BUY", "SELL"],
    tp_price: float,
    sl_price: float
) -> bool:
    """
    Valide que les prix TP/SL sont cohérents avec le side

    Args:
        entry_price: Prix d'entrée
        side: "BUY" ou "SELL"
        tp_price: Prix Take Profit
        sl_price: Prix Stop Loss

    Returns:
        True si valide, False sinon

    Examples:
        >>> validate_bracket_prices(6900, "BUY", 6925, 6885)
        True
        >>> validate_bracket_prices(6900, "BUY", 6885, 6925)  # Inversé!
        False
    """
    if side.upper() == "BUY":
        # Pour BUY: TP > entry, SL < entry
        if tp_price <= entry_price:
            logger.error(f"BUY: TP {tp_price} doit être > entry {entry_price}")
            return False
        if sl_price >= entry_price:
            logger.error(f"BUY: SL {sl_price} doit être < entry {entry_price}")
            return False
        return True
    else:  # SELL
        # Pour SELL: TP < entry, SL > entry
        if tp_price >= entry_price:
            logger.error(f"SELL: TP {tp_price} doit être < entry {entry_price}")
            return False
        if sl_price <= entry_price:
            logger.error(f"SELL: SL {sl_price} doit être > entry {entry_price}")
            return False
        return True


def create_bracket_params(
    symbol: str,
    side: Literal["BUY", "SELL"],
    entry_price: float,
    tp_ticks: int,
    sl_ticks: int,
    qty: float = 1.0,
    entry_kind: Literal["MARKET", "LIMIT"] = "MARKET",
    client_tag: Optional[str] = None
) -> Dict[str, any]:
    """
    Crée les paramètres complets pour un ordre bracket

    Args:
        symbol: Symbole (ESZ25-CME, NQZ25-CME)
        side: "BUY" ou "SELL"
        entry_price: Prix d'entrée (utilisé pour calcul TP/SL)
        tp_ticks: Take Profit en ticks
        sl_ticks: Stop Loss en ticks
        qty: Quantité (défaut 1.0)
        entry_kind: "MARKET" ou "LIMIT"
        client_tag: Tag personnalisé (optionnel)

    Returns:
        Dict prêt pour place_parent_then_children()

    Example:
        >>> params = create_bracket_params(
        ...     symbol="ESZ25-CME",
        ...     side="BUY",
        ...     entry_price=6900.0,
        ...     tp_ticks=100,
        ...     sl_ticks=60
        ... )
        >>> await connector.place_parent_then_children(**params)
    """
    # Récupérer config instrument
    config = get_instrument_config(symbol)

    # Calculer prix TP/SL
    prices = calculate_bracket_prices(
        entry_price=entry_price,
        side=side,
        tp_ticks=tp_ticks,
        sl_ticks=sl_ticks,
        tick_size=config.tick_size
    )

    tp_price = prices["tp_price"]
    sl_price = prices["sl_price"]

    # Valider
    if not validate_bracket_prices(entry_price, side, tp_price, sl_price):
        raise ValueError(f"Prix bracket invalides: entry={entry_price}, tp={tp_price}, sl={sl_price}")

    # Tag par défaut
    if client_tag is None:
        instrument = "ES" if "ES" in symbol else "NQ" if "NQ" in symbol else "UNK"
        client_tag = f"{instrument}_{entry_kind}"

    # Construire paramètres
    params = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "entry_kind": entry_kind,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "client_tag": client_tag,
        "children_mode": "separate"
    }

    # Ajouter entry_price si LIMIT
    if entry_kind.upper() == "LIMIT":
        params["entry_price"] = entry_price
    else:
        params["entry_price"] = None

    # Logger info
    logger.info(f"🎯 Bracket params: {symbol} {side} @ {entry_price:.2f}")
    logger.info(f"   TP: {tp_price:.2f} (+{tp_ticks} ticks = ${prices['tp_dollars']:.2f})")
    logger.info(f"   SL: {sl_price:.2f} (-{sl_ticks} ticks = ${prices['sl_dollars']:.2f})")
    logger.info(f"   R/R: {prices['risk_reward']:.2f}:1")

    return params


# === FONCTIONS CONVENIENCE ===

def create_market_bracket(
    symbol: str,
    side: Literal["BUY", "SELL"],
    current_price: float,
    tp_ticks: int,
    sl_ticks: int,
    qty: float = 1.0
) -> Dict[str, any]:
    """
    Crée un bracket MARKET (exécution immédiate)

    Args:
        symbol: Symbole
        side: "BUY" ou "SELL"
        current_price: Prix actuel du marché
        tp_ticks: TP en ticks
        sl_ticks: SL en ticks
        qty: Quantité

    Returns:
        Paramètres pour place_parent_then_children()
    """
    return create_bracket_params(
        symbol=symbol,
        side=side,
        entry_price=current_price,
        tp_ticks=tp_ticks,
        sl_ticks=sl_ticks,
        qty=qty,
        entry_kind="MARKET"
    )


def create_limit_bracket(
    symbol: str,
    side: Literal["BUY", "SELL"],
    limit_price: float,
    tp_ticks: int,
    sl_ticks: int,
    qty: float = 1.0
) -> Dict[str, any]:
    """
    Crée un bracket LIMIT (exécution au prix spécifié)

    Args:
        symbol: Symbole
        side: "BUY" ou "SELL"
        limit_price: Prix limite d'entrée
        tp_ticks: TP en ticks
        sl_ticks: SL en ticks
        qty: Quantité

    Returns:
        Paramètres pour place_parent_then_children()
    """
    return create_bracket_params(
        symbol=symbol,
        side=side,
        entry_price=limit_price,
        tp_ticks=tp_ticks,
        sl_ticks=sl_ticks,
        qty=qty,
        entry_kind="LIMIT"
    )


# === EXEMPLES D'USAGE ===

if __name__ == "__main__":
    print("="*60)
    print("BRACKET HELPER - Exemples d'usage")
    print("="*60)

    # Exemple 1: Calcul simple
    print("\n1️⃣ Calcul bracket BUY ES:")
    prices = calculate_bracket_prices(
        entry_price=6900.0,
        side="BUY",
        tp_ticks=100,
        sl_ticks=60,
        tick_size=0.25
    )
    print(f"   Entry: 6900.00")
    print(f"   TP: {prices['tp_price']} (${prices['tp_dollars']})")
    print(f"   SL: {prices['sl_price']} (${prices['sl_dollars']})")
    print(f"   R/R: {prices['risk_reward']}:1")

    # Exemple 2: Validation
    print("\n2️⃣ Validation:")
    print(f"   BUY 6900, TP 6925, SL 6885: {validate_bracket_prices(6900, 'BUY', 6925, 6885)}")
    print(f"   BUY 6900, TP 6885, SL 6925: {validate_bracket_prices(6900, 'BUY', 6885, 6925)} (ERREUR)")

    # Exemple 3: Paramètres complets
    print("\n3️⃣ Paramètres bracket LIMIT:")
    params = create_limit_bracket(
        symbol="ESZ25-CME",
        side="BUY",
        limit_price=6900.0,
        tp_ticks=100,
        sl_ticks=60,
        qty=2.0
    )
    print(f"   {params}")

    # Exemple 4: Usage avec connecteur
    print("\n4️⃣ Usage avec connecteur:")
    print("""
    from execution.sierra_dtc_connector import create_sierra_dtc_connector
    from execution.bracket_helper import create_limit_bracket

    connector = create_sierra_dtc_connector()

    # Créer bracket LIMIT +100/-60 ticks
    params = create_limit_bracket(
        symbol="ESZ25-CME",
        side="BUY",
        limit_price=6900.0,
        tp_ticks=100,
        sl_ticks=60
    )

    # Envoyer
    result = await connector.place_parent_then_children(**params)
    """)

    print("\n" + "="*60)
