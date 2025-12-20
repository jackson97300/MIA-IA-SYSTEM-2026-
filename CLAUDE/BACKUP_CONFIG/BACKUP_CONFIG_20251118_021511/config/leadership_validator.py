#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Leadership Validator – version patchée
- Gestion NaN → 0.0
- Corrélation ES/NQ NaN‑safe + synchro stricte
- Mode calibration: seuils adoucis + SOFT_DOWNGRADE
- Multiplicateur de risque continu (borné)
- Logging aligné sur tes traces
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
import math

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("features.leadership_zmom")

@dataclass
class ValidationResult:
    is_valid: bool
    risk_multiplier: float
    reason: str
    decision_code: str  # "PASS", "HARD_REJECT", "SOFT_DOWNGRADE"
    leader: Optional[str]
    leader_strength: float
    persisted: bool
    corr_es_nq: float

def _nan_to_num(x: float) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (float, int)):
        try:
            if math.isnan(float(x)) or math.isinf(float(x)):
                return 0.0
            return float(x)
        except Exception:
            return 0.0
    try:
        xf = float(x)
        return 0.0 if (math.isnan(xf) or math.isinf(xf)) else xf
    except Exception:
        return 0.0

def _sync_prices(es: pd.DataFrame, nq: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    if es is None or nq is None or not len(es) or not len(nq):
        return pd.Series(dtype=float), pd.Series(dtype=float)
    es = es.copy()
    nq = nq.copy()
    for df in (es, nq):
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, errors="coerce")

    # colonne de close
    col = None
    for candidate in ("close", "Close", "last", "price"):
        if candidate in es.columns and candidate in nq.columns:
            col = candidate
            break
    if col is None:
        def first_num(cdf):
            for c in cdf.columns:
                if pd.api.types.is_numeric_dtype(cdf[c]):
                    return c
            return None
        c_es = first_num(es)
        c_nq = first_num(nq)
        if c_es is None or c_nq is None:
            return pd.Series(dtype=float), pd.Series(dtype=float)
        es_col, nq_col = c_es, c_nq
    else:
        es_col = nq_col = col

    idx = es.index.intersection(nq.index)
    if len(idx) == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    es_c = es.loc[idx, es_col].astype(float)
    nq_c = nq.loc[idx, nq_col].astype(float)
    es_c = es_c.replace([np.inf, -np.inf], np.nan).dropna()
    nq_c = nq_c.replace([np.inf, -np.inf], np.nan).dropna()
    idx2 = es_c.index.intersection(nq_c.index)
    return es_c.loc[idx2], nq_c.loc[idx2]

def _corr_es_nq(es: pd.DataFrame, nq: pd.DataFrame, lookback: int = 20) -> float:
    es_c, nq_c = _sync_prices(es, nq)
    if len(es_c) < 2 or len(nq_c) < 2:
        return 0.0
    es_tail = es_c.tail(lookback)
    nq_tail = nq_c.tail(lookback)
    if len(es_tail) != len(nq_tail) or len(es_tail) < 2:
        return 0.0
    corr = float(np.corrcoef(es_tail.values, nq_tail.values)[0, 1])
    if math.isnan(corr) or math.isinf(corr):
        return 0.0
    return max(-1.0, min(1.0, corr))

class LeadershipZMom:
    """
    Valide un biais/instrument en s’appuyant sur ES/NQ et quelques règles.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.corr_min = float(cfg.get("corr_min", 0.01))
        self.leader_strength_min = float(cfg.get("leader_strength_min", 0.05))
        self.calibration_mode = bool(cfg.get("calibration_mode", False))

    def validate(
        self,
        *,
        bias: str,
        instrument: str,
        es_df: Optional[pd.DataFrame],
        nq_df: Optional[pd.DataFrame],
        leader_hint: Optional[str] = None,
        lookback: int = 20,
    ) -> ValidationResult:
        bias = (bias or "").lower().strip()
        instrument = (instrument or "").upper().strip()

        # Corrélation NaN-safe
        corr = _corr_es_nq(es_df, nq_df, lookback=lookback)
        corr_intensity = abs(corr)

        # Détermination leader “naïve” (tu peux brancher ta logique réelle ici)
        leader = leader_hint
        if not leader:
            if instrument in ("ES", "MES"):
                leader = "ES"
            elif instrument in ("NQ", "MNQ"):
                leader = "NQ"
            else:
                leader = None

        # Force du leader (proxy simple sur corrélation)
        leader_strength = corr_intensity

        # Seuils (adoucis si calibration)
        corr_min = self.corr_min
        strength_min = self.leader_strength_min
        decision_code = "PASS"
        reason = ""

        if self.calibration_mode:
            corr_min = max(0.0, self.corr_min * 0.5)
            strength_min = max(0.0, self.leader_strength_min * 0.5)

        # Validation
        is_valid = True
        if corr_intensity < corr_min:
            is_valid = False
            reason = f"Corrélation insuffisante ({corr_intensity:.3f} < {corr_min:.2f})"
        elif leader_strength < strength_min:
            is_valid = False
            reason = f"Leader trop faible ({leader_strength:.3f} < {strength_min:.2f})"

        # Multiplicateur de risque continu
        # map |corr|∈[0,1] → risk∈[0.0,1.0] avec un “dead‑zone” doux sur corr_min
        if corr_intensity <= corr_min:
            risk = 0.0
        else:
            # démarre à 0.2 au seuil puis grimpe
            span = max(1e-6, 1.0 - corr_min)
            risk = 0.2 + 0.8 * ((corr_intensity - corr_min) / span)
        risk = max(0.0, min(1.0, risk))

        # Décision finale
        if not is_valid:
            if self.calibration_mode:
                # On évite de bloquer dur pendant la calibration
                decision_code = "SOFT_DOWNGRADE"
                # on conserve un petit risque pour laisser passer la confluence si elle est forte
                risk = min(risk, 0.15)
            else:
                decision_code = "HARD_REJECT"
                risk = 0.0

        # Log formaté comme tes traces
        logger.info(
            "❌ REJECT | Bias=%s | Instrument=%s | Leader=%s | Reason: %s"
            if decision_code != "PASS" else
            "✅ PASS | Bias=%s | Instrument=%s | Leader=%s | Risk=%.3f",
            bias, instrument, leader, reason if decision_code != "PASS" else risk
        )

        return ValidationResult(
            is_valid=is_valid and decision_code == "PASS",
            risk_multiplier=float(risk),
            reason=reason,
            decision_code=decision_code,
            leader=leader,
            leader_strength=float(leader_strength),
            persisted=False,
            corr_es_nq=float(corr),
        )
