# -*- coding: utf-8 -*-
"""
unifier/unify_core.py
Coer commun: normalisation prix/tick, validations (VVA, NBCV, spreads),
et génération d'un QC summary GO/NO-GO.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
import json
from pathlib import Path


# --- Normalisation prix / tick ---

TICK_BY_SYMBOL: Dict[str, float] = {
    "ES": 0.25,
    "NQ": 0.25,
    # étendre si besoin (YM, RTY, CL, GC, etc.)
}


def detect_tick_size(symbol: str) -> float:
    s = (symbol or "").upper()
    for k, v in TICK_BY_SYMBOL.items():
        if k in s:
            return v
    return 0.25  # fallback sûr pour ES/NQ


def is_multiple_of_tick(value: float, tick: float, eps: float = 1e-6) -> bool:
    if tick <= 0:
        return True
    k = round(value / tick)
    return abs(value - k * tick) <= eps


def normalize_price(value: float, scale_used: float = 1.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    return v / scale_used if (scale_used and scale_used != 1.0) else v


# --- Validations ---

def validate_vva_order(vva: Dict[str, Any]) -> bool:
    try:
        # current requis
        if not all(k in vva for k in ("val", "vpoc", "vah")):
            return False
        val, vpoc, vah = float(vva["val"]), float(vva["vpoc"]), float(vva["vah"])
        
        # Tolérer les valeurs 0.0 au début de session (Volume Profile pas encore construit)
        if val == 0.0 and vpoc == 0.0 and vah == 0.0:
            return True  # VVA current pas encore disponible, c'est OK
        
        if not (val < vpoc < vah):
            return False
            
        # previous requis
        if not all(k in vva for k in ("pval", "ppoc", "pvah")):
            return False
        pval, ppoc, pvah = float(vva["pval"]), float(vva["ppoc"]), float(vva["pvah"])
        
        # Tolérer les valeurs 0.0 pour previous (première session)
        if pval == 0.0 and ppoc == 0.0 and pvah == 0.0:
            return True  # VVA previous pas disponible, c'est OK
            
        return (pval < ppoc < pvah)
    except Exception:
        return False


def validate_nbcv_row(r: Dict[str, Any], total_tol: int = 3) -> Tuple[bool, bool]:
    try:
        av = float(r.get('ask_volume', 0) or 0)
        bv = float(r.get('bid_volume', 0) or 0)
        tv = float(r.get('total_volume', av + bv) or (av + bv))
        d  = float(r.get('delta', av - bv) or (av - bv))
        ok_delta = (d == av - bv)
        ok_total = (abs((av + bv) - tv) <= total_tol)
        return ok_total, ok_delta
    except Exception:
        return False, False


@dataclass
class QCSummary:
    symbol: str
    chart: int
    date: str
    spread_nonneg_ratio: float
    tick_size: float
    vva_valid_count: int
    vva_total: int
    nbcv_bad_total: int
    nbcv_bad_delta: int
    vwap_p95_ticks: Optional[float] = None
    vwap_p99_ticks: Optional[float] = None
    scale_used: Optional[float] = None
    unknown_sessions: int = 0
    # champs optionnels supplémentaires
    spread_multiple_ratio: Optional[float] = None
    price_plausible: Optional[bool] = None
    # seuils paramétrables
    min_spread_ratio: float = 0.999
    max_vwap_p99_ticks: float = 2.0
    max_unknown_sessions: int = 0

    def go_nogo(self) -> bool:
        if self.vva_total > 0 and self.vva_valid_count != self.vva_total:
            return False
        if self.spread_nonneg_ratio < self.min_spread_ratio:
            return False
        if self.nbcv_bad_total != 0 or self.nbcv_bad_delta != 0:
            return False
        if self.vwap_p99_ticks is not None and self.vwap_p99_ticks > self.max_vwap_p99_ticks:
            return False
        if self.unknown_sessions > self.max_unknown_sessions:
            return False
        return True


def write_qc_summary(path: Path, qc: QCSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({**asdict(qc), "go": qc.go_nogo()}, f, ensure_ascii=False, indent=2)


# --- Validations additionnelles utiles ---

def validate_spreads_vs_tick(bids: List[float], asks: List[float], tick: float, eps: float = 1e-6) -> Tuple[float, float]:
    if not bids or not asks:
        return 1.0, tick
    ok = 0
    tot = 0
    for b, a in zip(bids, asks):
        try:
            if b is None or a is None:
                continue
            s = float(a) - float(b)
            if s >= -eps and is_multiple_of_tick(max(s, 0.0), tick, eps):
                ok += 1
            tot += 1
        except Exception:
            continue
    ratio = ok / tot if tot else 1.0
    return ratio, tick


def check_price_plausibility(prices: List[float], min_px: float = 1.0, max_px: float = 1e7) -> bool:
    if not prices:
        return True
    try:
        mn = min(prices)
        mx = max(prices)
        return (mn >= min_px) and (mx <= max_px)
    except Exception:
        return False


