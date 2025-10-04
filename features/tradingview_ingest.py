"""TradingView alerts ingestion -> normalized bus (tv_bus.jsonl).

Fonctionnalités principales :
- Lecture continue de `tv_alerts.jsonl`
- Protection contre les données obsolètes (stale guard)
- Filtrage Intraday sur futures (ES/NQ) pour ne conserver que l'EOD
- Routage symbole (target_symbol + fichier YAML externe)
- TTL par catégorie et déduplication temporelle
- Écriture normalisée dans `tv_bus.jsonl` pour l'unifier Python
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# === Chemins & configuration ===
ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config" / "tradingview_ingest.yaml"
ROUTER_PATH = ROOT / "config" / "symbol_router.yaml"
DATA_DIR = ROOT / "data" / "tradingview"
ALERTS_DEFAULT = DATA_DIR / "tv_alerts.jsonl"
BUS_DEFAULT = DATA_DIR / "tv_bus.jsonl"
STATE_PATH = DATA_DIR / ".tv_ingest_state.json"


def load_yaml_safe(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or fallback
    except Exception:
        return fallback


DEFAULT_CFG = {
    "stale": {"max_age_hours": 6, "warn_age_hours": 2},
    "futures": {"enforce_eod_only": True, "symbols_regex": r"^(ES|NQ)[A-Z0-9!]*$"},
    "ttl_minutes": {"INTRADAY_STRONG": 15, "INTRADAY_WEAK": 5, "EOD": 1500},
}

TV_CFG = load_yaml_safe(CFG_PATH, DEFAULT_CFG)
STALE_MAX_H = int(TV_CFG["stale"]["max_age_hours"])
STALE_WARN_H = int(TV_CFG["stale"]["warn_age_hours"])
FUT_EOD_ONLY = bool(TV_CFG["futures"]["enforce_eod_only"])
FUT_REGEX = re.compile(TV_CFG["futures"]["symbols_regex"])
TTL_MIN = TV_CFG["ttl_minutes"]

ROUTER = load_yaml_safe(ROUTER_PATH, {"route": {}}).get("route", {})

# category, priority, name
EVENT_MAP: Dict[str, tuple[str, int, str]] = {
    "ES:BLIND_SPOT_TOUCH": ("INTRADAY_WEAK", 1, "blind_spot_touch"),
    "ES:HVL_BREAK": ("INTRADAY_STRONG", 2, "hvl_break"),
    "ES:DAY_MAX_TOUCH": ("INTRADAY_WEAK", 1, "day_max_touch"),
    "ES:DAY_MIN_TOUCH": ("INTRADAY_WEAK", 1, "day_min_touch"),
    "ES:LEVELS_SNAPSHOT": ("EOD", 0, "levels_snapshot"),
    "NQ:BLIND_SPOT_TOUCH": ("INTRADAY_WEAK", 1, "blind_spot_touch"),
    "NQ:HVL_BREAK": ("INTRADAY_STRONG", 2, "hvl_break"),
    "NQ:DAY_MAX_TOUCH": ("INTRADAY_WEAK", 1, "day_max_touch"),
    "NQ:DAY_MIN_TOUCH": ("INTRADAY_WEAK", 1, "day_min_touch"),
    "NQ:LEVELS_SNAPSHOT": ("EOD", 0, "levels_snapshot"),
    "SPX:SWING_TOUCH": ("EOD", 1, "swing_touch"),
    "SPX:SWING_BREAK_UP": ("EOD", 2, "swing_break_up"),
    "SPX:SWING_BREAK_DOWN": ("EOD", 2, "swing_break_down"),
}


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _parse_tv_time(tv_time: Any) -> datetime:
    if tv_time is None:
        return datetime.now(timezone.utc)
    s = str(tv_time).strip()
    if s.isdigit():
        try:
            value = int(s)
            if value < 10 ** 12:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
        except Exception:
            pass
    try:
        s = s.replace(" ", "T").replace("Z", "+00:00")
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def reject_if_stale(event_dt: datetime, now_dt: datetime) -> tuple[bool, str]:
    age_h = (now_dt - event_dt).total_seconds() / 3600.0
    if age_h >= STALE_MAX_H:
        return True, f"TV_STALE_DATA age_h={age_h:.2f} >= {STALE_MAX_H}"
    if age_h >= STALE_WARN_H:
        return False, f"TV_STALE_WARN age_h={age_h:.2f} >= {STALE_WARN_H}"
    return False, ""


def enforce_eod_on_futures(evt: dict, category: str) -> tuple[bool, str]:
    ticker = (evt.get("ticker") or "").upper()
    event = (evt.get("event") or "").upper()
    is_future = bool(FUT_REGEX.match(ticker)) or event.startswith("ES:") or event.startswith("NQ:")
    if FUT_EOD_ONLY and is_future and category.startswith("INTRADAY"):
        return True, f"TV_UNSUPPORTED_INTRADAY_FUT ticker={ticker} event={event} cat={category}"
    return False, ""


def resolve_exec_symbol(evt: dict) -> str:
    src = (evt.get("ticker") or "").upper()
    target = (evt.get("target_symbol") or "").upper()
    if target:
        return target
    return (ROUTER.get(src) or src).upper()


def ttl_for_category(category: str) -> int:
    return int(TTL_MIN.get(category, 60))


def dedup_key(evt: dict) -> str:
    sym = evt.get("_exec_symbol", "")
    event = evt.get("event", "")
    price = evt.get("price")
    try:
        price_r = round(float(price), 2) if price is not None else None
    except Exception:
        price_r = None
    dt = evt.get("_dt")
    minute = dt.replace(second=0, microsecond=0).isoformat() if isinstance(dt, datetime) else ""
    return f"{sym}|{event}|{price_r}|{minute}"


@dataclass
class DedupState:
    seen: Dict[str, float]

    @classmethod
    def load(cls, path: Path) -> "DedupState":
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return cls(seen=data.get("seen", {}))
            except Exception:
                pass
        return cls(seen={})

    def prune(self, now_epoch: float) -> None:
        cutoff = now_epoch - 2 * 3600
        self.seen = {k: exp for k, exp in self.seen.items() if exp >= cutoff}

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"seen": self.seen}), encoding="utf-8")


def process_event(raw: dict, now_utc: datetime, state: DedupState, out_fp: io.TextIOBase, verbose: bool = False) -> bool:
    evt_dt = _parse_tv_time(raw.get("time") or raw.get("timestamp"))
    reject, msg = reject_if_stale(evt_dt, now_utc)
    if reject:
        log(msg + f" | drop | evt={raw}")
        return False
    elif msg:
        log(msg + f" | warn | evt={raw}")

    event_name = (raw.get("event") or "").upper()
    category, priority, name = EVENT_MAP.get(event_name, ("EOD", 0, "unknown"))

    reject_fut, msg_fut = enforce_eod_on_futures(raw, category)
    if reject_fut:
        log(msg_fut + f" | drop | evt={raw}")
        return False

    exec_symbol = resolve_exec_symbol(raw)
    ttl_m = ttl_for_category(category)
    expiry = (now_utc + timedelta(minutes=ttl_m)).timestamp()

    norm = {
        "src": (raw.get("src") or "tradingview"),
        "vendor": (raw.get("vendor") or "MentorQ"),
        "ticker": (raw.get("ticker") or "").upper(),
        "_exec_symbol": exec_symbol,
        "event": event_name,
        "category": category,
        "priority": priority,
        "name": name,
        "price": raw.get("price"),
        "time": raw.get("time") or raw.get("timestamp"),
        "_dt": evt_dt,
        "_expiry": expiry,
        "raw": raw,
    }

    key = dedup_key(norm)
    now_epoch = now_utc.timestamp()
    state.prune(now_epoch)
    if key in state.seen and state.seen[key] > now_epoch:
        if verbose:
            log(f"TV_DEDUP_SKIP key={key}")
        return False
    state.seen[key] = now_epoch + 300
    state.save(STATE_PATH)

    norm["_dt"] = evt_dt.isoformat()
    out_fp.write(json.dumps(norm, ensure_ascii=False) + "\n")
    out_fp.flush()
    log(f"TV_OK sym={exec_symbol} evt={event_name} cat={category} ttl={ttl_m}m")
    return True


class TailFile:
    def __init__(self, path: Path, start_at_end: bool = True):
        self.path = path
        self.start_at_end = start_at_end
        self.fp: Optional[io.TextIOWrapper] = None
        self.ino: Optional[int] = None

    def _open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fp = self.path.open("r", encoding="utf-8")
        self.ino = os.fstat(self.fp.fileno()).st_ino
        if self.start_at_end:
            self.fp.seek(0, os.SEEK_END)

    def lines(self):
        if not self.path.exists():
            self.path.touch()
        if self.fp is None:
            self._open()
        while True:
            line = self.fp.readline()
            if line:
                yield line
            else:
                try:
                    cur_ino = os.stat(self.path).st_ino
                    if cur_ino != self.ino:
                        self.fp.close()
                        self._open()
                except FileNotFoundError:
                    time.sleep(0.1)
                time.sleep(0.05)


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingView -> tv_bus.jsonl ingestor")
    parser.add_argument("--alerts", default=str(ALERTS_DEFAULT), help="Entrée tv_alerts.jsonl")
    parser.add_argument("--out", default=str(BUS_DEFAULT), help="Sortie tv_bus.jsonl")
    parser.add_argument("--since-start", action="store_true", help="Lire depuis le début du fichier")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    alerts_path = Path(args.alerts)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tail = TailFile(alerts_path, start_at_end=(not args.since_start))
    state = DedupState.load(STATE_PATH)

    with out_path.open("a", encoding="utf-8") as out_fp:
        for line in tail.lines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except Exception:
                log(f"TV_JSON_ERROR skip: {line[:160]}")
                continue
            now_utc = datetime.now(timezone.utc)
            try:
                process_event(evt, now_utc, state, out_fp, verbose=args.verbose)
            except Exception as exc:
                log(f"TV_PROC_ERROR {exc} | evt={evt}")


def _cli() -> None:
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    _cli()










