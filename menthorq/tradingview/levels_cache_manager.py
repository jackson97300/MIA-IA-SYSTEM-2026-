"""Gestionnaire de cache pour les snapshots TradingView LEVELS_SNAPSHOT.

Objectifs :
- Lire les événements normalisés (tv_bus.jsonl) via l'unifier
- Stocker les derniers niveaux connus par symbole dans des fichiers JSON locaux
- Fournir une interface simple pour charger/récupérer les niveaux (pour Battle Navale ou autres modules)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "levels_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class LevelsSnapshot:
    symbol: str
    timestamp: datetime
    levels: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "levels": self.levels,
        }

    @classmethod
    def from_event(cls, event: Dict[str, Any]) -> "LevelsSnapshot":
        raw = event.get("raw", {})
        symbol = event.get("_exec_symbol") or event.get("ticker") or "UNKNOWN"
        ts = event.get("time") or raw.get("time") or raw.get("timestamp")
        timestamp = datetime.fromisoformat(str(ts).replace("Z", "+00:00")) if ts else datetime.utcnow()
        levels_payload = raw.get("levels") or {}
        levels: Dict[str, float] = {}
        for key, val in levels_payload.items():
            num = _to_float(val)
            if num is not None:
                levels[key.lower()] = num
        return cls(symbol=symbol, timestamp=timestamp, levels=levels)

    @classmethod
    def load(cls, symbol: str) -> Optional["LevelsSnapshot"]:
        path = CACHE_DIR / f"{symbol.upper()}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data["timestamp"])
        return cls(symbol=data["symbol"], timestamp=ts, levels=data.get("levels", {}))

    def save(self) -> None:
        path = CACHE_DIR / f"{self.symbol.upper()}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def update_cache_from_event(event: Dict[str, Any]) -> Optional[LevelsSnapshot]:
    if (event.get("name") or "") != "levels_snapshot":
        return None
    snapshot = LevelsSnapshot.from_event(event)
    if snapshot.levels:
        snapshot.save()
    return snapshot


def get_levels(symbol: str) -> Dict[str, float]:
    snap = LevelsSnapshot.load(symbol)
    return snap.levels if snap else {}












