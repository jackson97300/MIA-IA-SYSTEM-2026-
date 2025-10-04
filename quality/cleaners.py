# -*- coding: utf-8 -*-
"""
quality/cleaners.py
Nettoyages: dédoublonnage, filtres quotes lock, normalisation types.
"""

from __future__ import annotations

from typing import Iterable, Dict, Any, List, Tuple


def dedupe_by_keys(rows: Iterable[Dict[str, Any]], keys: Tuple[str, ...]) -> List[Dict[str, Any]]:
    """Supprime les doublons stricts selon un tuple de clés, conserve la 1ère occurrence."""
    seen = set()
    out: List[Dict[str, Any]] = []
    for r in rows:
        signature = tuple(r.get(k) for k in keys)
        if signature in seen:
            continue
        seen.add(signature)
        out.append(r)
    return out


def filter_locked_quotes(rows: Iterable[Dict[str, Any]], max_persist_ms: int = 1) -> List[Dict[str, Any]]:
    """Filtre les séquences où bid == ask qui persistent au-delà de max_persist_ms."""
    last_equal_t = None
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            t = float(r.get("t"))
            b = float(r.get("b", r.get("bid")))
            a = float(r.get("a", r.get("ask")))
        except Exception:
            continue
        if a == b:
            if last_equal_t is None:
                last_equal_t = t
            # on retient si durée courte
            if (t - last_equal_t) * 1000.0 <= max_persist_ms:
                out.append(r)
            # sinon drop
        else:
            last_equal_t = None
            out.append(r)
    return out





