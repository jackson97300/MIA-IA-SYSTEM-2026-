# -*- coding: utf-8 -*-
"""
quality/computations.py
Calculs dérivés fiables à partir des trades/quotes:
- VWAP (session-aware)
- Cumulative Delta (bid/ask aggressor)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Dict, Any, Tuple

import math


@dataclass
class SessionRules:
    """Règles de session pour reset VWAP.

    Attributes:
        rth_start_utc: heure de début RTH (HH:MM) en UTC
        rth_end_utc: heure de fin RTH (HH:MM) en UTC
        reset_on_session_change: si True, reset aux frontières RTH/ETH
    """
    rth_start_utc: str = "13:30"
    rth_end_utc: str = "20:00"
    reset_on_session_change: bool = True


def _parse_hhmm(hhmm: str) -> Tuple[int, int]:
    h, m = hhmm.split(":")
    return int(h), int(m)


def _is_rth(epoch_seconds: float, rules: SessionRules) -> bool:
    # Simplification: on évalue dans la même journée UTC (suffisant pour le reset logique)
    from datetime import datetime
    dt = datetime.utcfromtimestamp(epoch_seconds)
    hs, ms = _parse_hhmm(rules.rth_start_utc)
    he, me = _parse_hhmm(rules.rth_end_utc)
    start = dt.replace(hour=hs, minute=ms, second=0, microsecond=0)
    end = dt.replace(hour=he, minute=me, second=0, microsecond=0)
    return start <= dt <= end


def compute_vwap_from_trades(trades: Iterable[Dict[str, Any]], rules: Optional[SessionRules] = None) -> List[Dict[str, Any]]:
    """Calcule le VWAP cumulatif sur les trades.

    Args:
        trades: itérable de ticks avec au moins clés: 't' (epoch sec), 'p' (price), 'q' (size)
        rules: règles de session pour reset

    Returns:
        Liste de dicts {"t": ts, "vwap": vwap}
    """
    rules = rules or SessionRules()
    num = 0.0
    den = 0.0
    last_session_flag: Optional[bool] = None
    out: List[Dict[str, Any]] = []

    for tr in trades:
        t = float(tr.get("t", math.nan))
        p = float(tr.get("p", math.nan))
        q = float(tr.get("q", math.nan))
        if math.isnan(t) or math.isnan(p) or math.isnan(q) or q <= 0:
            continue

        session_flag = _is_rth(t, rules)
        if rules.reset_on_session_change and last_session_flag is not None and session_flag != last_session_flag:
            num = 0.0
            den = 0.0

        num += p * q
        den += q
        vwap = num / den if den > 0 else math.nan
        out.append({"t": t, "vwap": vwap})
        last_session_flag = session_flag

    return out


def compute_cum_delta_from_trades(trades: Iterable[Dict[str, Any]], tick_size: float = 0.25) -> List[Dict[str, Any]]:
    """Calcule le Cumulative Delta naïf: +q si trade au Ask, -q si au Bid.

    Args:
        trades: itérable avec 't','p','q','bid','ask' si possible; fallback: price movement
        tick_size: taille de tick (ES/NQ typiquement 0.25)

    Returns:
        Liste de dicts {"t": ts, "cum_delta": x}
    """
    cum = 0.0
    out: List[Dict[str, Any]] = []
    last_price: Optional[float] = None

    for tr in trades:
        t = float(tr.get("t", math.nan))
        p = float(tr.get("p", math.nan))
        q = float(tr.get("q", math.nan))
        if math.isnan(t) or math.isnan(p) or math.isnan(q) or q <= 0:
            continue

        bid = tr.get("bid")
        ask = tr.get("ask")
        sign = 0.0
        if bid is not None and ask is not None:
            try:
                b = float(bid)
                a = float(ask)
                # logique: si prix >= ask → aggressive buy; si prix <= bid → aggressive sell
                if not math.isnan(b) and not math.isnan(a):
                    if p >= a:
                        sign = 1.0
                    elif p <= b:
                        sign = -1.0
            except Exception:
                pass

        if sign == 0.0 and last_price is not None:
            # fallback: direction par rapport au dernier prix
            if p > last_price:
                sign = 1.0
            elif p < last_price:
                sign = -1.0

        cum += sign * q
        out.append({"t": t, "cum_delta": cum})
        last_price = p

    return out





