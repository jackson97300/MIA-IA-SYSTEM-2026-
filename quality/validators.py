# -*- coding: utf-8 -*-
"""
quality/validators.py
Règles de validation (quality gates) avec seuils configurables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class Thresholds:
    vwap_p95_max_pct: float = 0.5
    vwap_p99_max_pct: float = 1.0
    vix_min_variance: float = 0.1
    locked_quote_max_pct: float = 0.1
    max_corrected_vol_pct: float = 1.0


def summarize_vwap_deviation_percent(deviations_pct: List[float]) -> Dict[str, Any]:
    if not deviations_pct:
        return {"count": 0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    import numpy as np
    v = np.array(deviations_pct, dtype=float)
    return {
        "count": int(v.size),
        "p95": float(np.nanpercentile(v, 95)),
        "p99": float(np.nanpercentile(v, 99)),
        "max": float(np.nanmax(v)),
    }


def check_vwap_thresholds(summary: Dict[str, Any], thr: Thresholds) -> bool:
    return (summary["p95"] <= thr.vwap_p95_max_pct and summary["p99"] <= thr.vwap_p99_max_pct)





