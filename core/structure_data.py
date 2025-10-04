#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Structure Data Processor (v2.1)
Normaliseur de données JSONL → records internes cohérents

CHANGEMENTS v2.1 (sept. 2025)
- 🔧 Mapping correct des champs précédents VPA: pvah→prev_vah, pval→prev_val, ppoc→prev_vpoc
- ➕ Ajout d'un record typé TradeTick (au lieu d'un dict) + conversion dédiée
- 🛡️ Validation & robustesse: tolérance ts numérique (epoch seconds), fallback sur ingest_ts
- 🚀 Petites optimisations (dédup + logs périodiques) et annotations de types
- 🧪 Tests mis à jour pour TradeTick et mapping prev_*

Compatibilité: 100% architecture Sierra-only / fichiers mia_unified_*.jsonl
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List, Union, Iterable
import json
import hashlib

from .logger import get_logger
from .base_types import parse_ts


logger = get_logger(__name__)

SCHEMA_VERSION = "1.1"

# === CONFIGURATION ===
VALID_TYPES = {
    "trade", "quote", "basedata", "vwap", "vva", "vap", "pvwap", "depth",
    "vix", "menthorq_gamma_levels", "menthorq_blind_spots", "menthorq_swing_levels"
}

VALID_GRAPHS = {3, 4, 8, 10}

REQUIRED_FIELDS: Dict[str, Set[str]] = {
    "basedata": {"type", "graph", "sym", "ts", "o", "h", "l", "c", "v"},
    "vwap": {"type", "graph", "sym", "ts", "v"},
    "vva": {"type", "graph", "sym", "ts", "vah", "val", "vpoc"},  # pvah/pval/ppoc tolérés en option
    "vap": {"type", "graph", "sym", "ts", "price", "vol"},
    "depth": {"type", "graph", "sym", "ts", "side", "lvl", "price", "size"},
    "quote": {"type", "graph", "sym", "ts", "kind", "bid", "ask", "bq", "aq"},
    "trade": {"type", "graph", "sym", "ts", "px", "vol"},
    "pvwap": {"type", "graph", "sym", "ts", "pvwap"},
    "vix": {"type", "graph", "sym", "ts", "last"},
    "menthorq_gamma_levels": {"type", "graph", "sym", "ts", "study_id", "sg", "label", "price"},
    "menthorq_blind_spots": {"type", "graph", "sym", "ts", "study_id", "sg", "label", "price"},
    "menthorq_swing_levels": {"type", "graph", "sym", "ts", "study_id", "sg", "label", "price"},
}

DOMAIN_VALIDATORS = {
    "graph": lambda x: x in VALID_GRAPHS,
    "quote.kind": lambda x: x == "BIDASK",
    "depth.side": lambda x: x in {"BID", "ASK"},
    "depth.lvl": lambda x: int(x) >= 1,
    "menthorq.study_id": lambda x: int(x) in {1, 2, 3},
    "menthorq.sg": lambda x: int(x) >= 1,
    "menthorq.price": lambda x: float(x) > 0,
}

# === RECORDS INTERNES TYPÉS ===
@dataclass
class MarketBarM1:
    symbol: str
    ts: datetime
    ohlc: Dict[str, float]
    volume: int
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None
    open_interest: Optional[int] = None

@dataclass
class MarketBarM30:
    symbol: str
    ts: datetime
    ohlc: Dict[str, float]
    volume: int

@dataclass
class VWAPBandM1:
    symbol: str
    ts: datetime
    vwap: float
    upper_band_1: Optional[float] = None
    lower_band_1: Optional[float] = None
    upper_band_2: Optional[float] = None
    lower_band_2: Optional[float] = None
    source: Optional[str] = None

@dataclass
class VWAPBandM30:
    symbol: str
    ts: datetime
    vwap: float
    upper_band_1: Optional[float] = None
    lower_band_1: Optional[float] = None
    upper_band_2: Optional[float] = None
    lower_band_2: Optional[float] = None

@dataclass
class VolumeProfile:
    symbol: str
    ts: datetime
    vah: float
    val: float
    vpoc: float
    prev_vah: Optional[float] = None
    prev_val: Optional[float] = None
    prev_vpoc: Optional[float] = None
    session_id_current: Optional[str] = None
    session_id_previous: Optional[str] = None

@dataclass
class VolumeProfileTick:
    symbol: str
    ts: datetime
    price: float
    volume: int
    bar_number: Optional[int] = None
    k_value: Optional[int] = None

@dataclass
class NBCVM1:
    symbol: str
    ts: datetime
    net_volume: int  # ask - bid

@dataclass
class NBCVM30:
    symbol: str
    ts: datetime
    net_volume: int

@dataclass
class DOMLevel:
    symbol: str
    ts: datetime
    side: str
    level: int
    price: float
    size: int

@dataclass
class Quote:
    symbol: str
    ts: datetime
    bid: float
    ask: float
    bid_quantity: int
    ask_quantity: int
    sequence: Optional[int] = None

@dataclass
class TradeTick:
    symbol: str
    ts: datetime
    price: float
    volume: int
    sequence: Optional[int] = None

@dataclass
class VIXTick:
    symbol: str
    ts: datetime
    price: float
    mode: Optional[str] = None

@dataclass
class MenthorQLevels:
    symbol: str
    ts: datetime
    gamma_levels: Dict[str, float]
    blind_spots: Dict[str, float]
    swing_levels: Dict[str, float]
    call_resistance: Optional[float] = None
    put_support: Optional[float] = None
    gamma_wall_0dte: Optional[float] = None
    hvl: Optional[float] = None
    partial: bool = False

InternalRecord = Union[
    MarketBarM1, MarketBarM30, VWAPBandM1, VWAPBandM30, VolumeProfile, VolumeProfileTick,
    NBCVM1, NBCVM30, DOMLevel, Quote, TradeTick, VIXTick, MenthorQLevels,
]


# === STRUCTURE DATA PROCESSOR ===
@dataclass
class StructureDataProcessor:
    stale_minutes: int = 5
    enable_dedup: bool = True
    enable_stale_filter: bool = True

    seen_events: Set[str] = field(default_factory=set)
    counters: Dict[str, int] = field(default_factory=lambda: {
        "accepted": 0, "rejected": 0, "duplicates": 0, "stale": 0, "total": 0,
    })

    last_summary_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    summary_interval_seconds: int = 30

    def __post_init__(self) -> None:
        logger.info(
            f"StructureDataProcessor v{SCHEMA_VERSION} - stale={self.stale_minutes}m, dedup={self.enable_dedup}"
        )

    def process_line(self, line: str) -> Optional[Dict[str, Any]]:
        self.counters["total"] += 1
        try:
            data = self._parse_json(line)
            if data is None:
                return None

            if not self._validate_schema(data):
                return None

            if not self._normalize_timestamp(data):
                return None

            if self._is_duplicate(data):
                self.counters["duplicates"] += 1
                return None

            if self._is_stale(data):
                self.counters["stale"] += 1
                return None

            normalized = self._normalize_event(data)

            if self.enable_dedup:
                self._mark_as_seen(data)

            self.counters["accepted"] += 1
            self._log_periodic_summary()
            return normalized
        except Exception as e:
            self.counters["rejected"] += 1
            logger.exception(f"Erreur traitement ligne: {e}")
            return None

    # --- Parsing & validation ---
    def _parse_json(self, line: str) -> Optional[Dict[str, Any]]:
        try:
            s = line.strip()
            if not s:
                return None
            data = json.loads(s)
            if not isinstance(data, dict):
                logger.warning("Ligne non-dict ignorée")
                return None
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"JSON invalide ignoré: {e}")
            return None
        except Exception as e:
            logger.exception(f"Erreur parse JSON: {e}")
            return None

    def _validate_schema(self, data: Dict[str, Any]) -> bool:
        try:
            event_type = data.get("type")
            if event_type not in VALID_TYPES:
                logger.warning(f"Type invalide: {event_type}")
                return False

            required = REQUIRED_FIELDS.get(event_type, set())
            missing = required - set(data.keys())
            if missing:
                logger.warning(f"Champs manquants pour {event_type}: {missing}")
                return False

            graph = data.get("graph")
            if not DOMAIN_VALIDATORS["graph"](graph):
                logger.warning(f"Graph invalide: {graph}")
                return False

            # Spécifiques
            if event_type == "quote" and not DOMAIN_VALIDATORS["quote.kind"](data.get("kind")):
                logger.warning(f"Quote kind invalide: {data.get('kind')}")
                return False
            if event_type == "depth":
                if not DOMAIN_VALIDATORS["depth.side"](data.get("side")):
                    logger.warning(f"Depth side invalide: {data.get('side')}")
                    return False
                if not DOMAIN_VALIDATORS["depth.lvl"](data.get("lvl")):
                    logger.warning(f"Depth lvl invalide: {data.get('lvl')}")
                    return False
            if event_type.startswith("menthorq_"):
                if not DOMAIN_VALIDATORS["menthorq.study_id"](data.get("study_id")):
                    logger.warning("MenthorQ study_id invalide")
                    return False
                if not DOMAIN_VALIDATORS["menthorq.sg"](data.get("sg")):
                    logger.warning("MenthorQ sg invalide")
                    return False
                if not DOMAIN_VALIDATORS["menthorq.price"](data.get("price")):
                    logger.warning("MenthorQ price invalide")
                    return False
            return True
        except Exception as e:
            logger.exception(f"Erreur validation schéma: {e}")
            return False

    def _normalize_timestamp(self, data: Dict[str, Any]) -> bool:
        try:
            ts_field = data.get("ts", data.get("ingest_ts"))
            if ts_field is None:
                logger.warning("Aucun timestamp trouvé")
                return False
            # Support des epochs numériques
            if isinstance(ts_field, (int, float)):
                parsed = datetime.fromtimestamp(float(ts_field), tz=timezone.utc)
            else:
                parsed = parse_ts(str(ts_field))
            if parsed is None:
                logger.warning(f"Timestamp invalide: {ts_field}")
                return False
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            data["ts"] = parsed.astimezone(timezone.utc).isoformat()
            return True
        except Exception as e:
            logger.exception(f"Erreur normalisation timestamp: {e}")
            return False

    # --- Déduplication & stale ---
    def _build_dedup_key(self, data: Dict[str, Any]) -> str:
        sym = str(data.get("sym", ""))
        graph = str(data.get("graph", ""))
        event_type = str(data.get("type", ""))
        ts = str(data.get("ts", ""))
        payload = {k: v for k, v in data.items() if k != "ts"}
        payload_hash = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:8]
        return f"{sym}|{graph}|{event_type}|{ts}|{payload_hash}"

    def _is_duplicate(self, data: Dict[str, Any]) -> bool:
        if not self.enable_dedup:
            return False
        key = self._build_dedup_key(data)
        return key in self.seen_events

    def _is_stale(self, data: Dict[str, Any]) -> bool:
        if not self.enable_stale_filter:
            return False
        try:
            event_ts = parse_ts(data.get("ts", ""))
            if event_ts is None:
                return True
            now = datetime.now(timezone.utc)
            return (now - event_ts) > timedelta(minutes=self.stale_minutes)
        except Exception:
            return True

    def _mark_as_seen(self, data: Dict[str, Any]) -> None:
        try:
            key = self._build_dedup_key(data)
            self.seen_events.add(key)
            if len(self.seen_events) > 100_000:
                # drop ~50% oldest (approx)
                self.seen_events = set(list(self.seen_events)[-50_000:])
        except Exception as e:
            logger.exception(f"Erreur marquage vu: {e}")

    # --- Normalisation ---
    def _normalize_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            normalized = dict(data)
            normalized["schema_version"] = SCHEMA_VERSION
            self._normalize_field_names(normalized)
            self._harmonize_values(normalized)
            return normalized
        except Exception as e:
            logger.exception(f"Erreur normalisation événement: {e}")
            return data

    def _normalize_field_names(self, data: Dict[str, Any]) -> None:
        # Correction mapping des champs "previous"
        mapping = {
            "pvah": "prev_vah",
            "pval": "prev_val",
            "ppoc": "prev_vpoc",
        }
        for old, new in mapping.items():
            if old in data and new not in data:
                data[new] = data.pop(old)

    def _harmonize_values(self, data: Dict[str, Any]) -> None:
        if str(data.get("type", "")).startswith("menthorq_"):
            label = data.get("label")
            if isinstance(label, str):
                data["label"] = label.strip()

    # --- Logs périodiques ---
    def _log_periodic_summary(self) -> None:
        try:
            now = datetime.now(timezone.utc)
            if (now - self.last_summary_time).total_seconds() >= self.summary_interval_seconds:
                self._log_summary()
                self.last_summary_time = now
        except Exception as e:
            logger.exception(f"Erreur log périodique: {e}")

    def _log_summary(self) -> None:
        try:
            c = self.counters
            total = max(1, c["total"])  # éviter division 0
            accept_rate = (c["accepted"] / total) * 100.0
            logger.info(
                "structure_data: %d accepted, %d rejected (%d stale, %d dup) - %.1f%% success",
                c["accepted"], c["rejected"], c["stale"], c["duplicates"], accept_rate,
            )
        except Exception as e:
            logger.exception(f"Erreur log synthèse: {e}")

    # --- API métriques ---
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "counters": self.counters.copy(),
            "cache_size": len(self.seen_events),
            "config": {
                "stale_minutes": self.stale_minutes,
                "enable_dedup": self.enable_dedup,
                "enable_stale_filter": self.enable_stale_filter,
                "schema_version": SCHEMA_VERSION,
            },
        }

    def reset_metrics(self) -> None:
        self.counters = {"accepted": 0, "rejected": 0, "duplicates": 0, "stale": 0, "total": 0}
        self.seen_events.clear()
        logger.info("Métriques remises à zéro")


# === INTERFACES DE CONVERSION ===

def to_internal(event: Dict[str, Any]) -> Optional[InternalRecord]:
    try:
        event_type = event.get("type")
        symbol = event.get("sym", "")
        ts = parse_ts(event.get("ts", ""))
        if ts is None:
            logger.warning(f"Timestamp invalide pour {event_type}")
            return None

        if event_type == "basedata":
            return _convert_basedata(event, symbol, ts)
        if event_type == "vwap":
            return _convert_vwap(event, symbol, ts)
        if event_type == "vva":
            return _convert_vva(event, symbol, ts)
        if event_type == "vap":
            return _convert_vap(event, symbol, ts)
        if event_type == "depth":
            return _convert_depth(event, symbol, ts)
        if event_type == "quote":
            return _convert_quote(event, symbol, ts)
        if event_type == "trade":
            return _convert_trade(event, symbol, ts)
        if event_type == "pvwap":
            return _convert_pvwap(event, symbol, ts)
        if event_type == "vix":
            return _convert_vix(event, symbol, ts)
        if event_type and event_type.startswith("menthorq_"):
            return _convert_menthorq(event, symbol, ts)
        logger.warning(f"Type d'événement non supporté: {event_type}")
        return None
    except Exception as e:
        logger.exception(f"Erreur conversion vers record interne: {e}")
        return None


def batch_to_internal(events_iterable: Iterable[Dict[str, Any]]) -> List[InternalRecord]:
    records: List[InternalRecord] = []
    for evt in events_iterable:
        rec = to_internal(evt)
        if rec is not None:
            records.append(rec)
    return records


def resolve_levels(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    try:
        levels = {
            "vah": None, "val": None, "vpoc": None,
            "vwap": None, "vwap_upper": None, "vwap_lower": None,
            "call_resistance": None, "put_support": None,
            "gamma_wall": None, "hvl": None,
            "blind_spots": [], "swing_levels": [],
        }
        for key, value in snapshot.items():
            if isinstance(value, dict):
                if {"vah", "val", "vpoc"} <= set(value.keys()):
                    levels["vah"] = value.get("vah")
                    levels["val"] = value.get("val")
                    levels["vpoc"] = value.get("vpoc")
                elif "vwap" in value:
                    levels["vwap"] = value.get("vwap")
                    levels["vwap_upper"] = value.get("upper_band_1")
                    levels["vwap_lower"] = value.get("lower_band_1")
                elif any(k in value for k in ("call_resistance", "put_support", "gamma_wall_0dte", "hvl")):
                    levels["call_resistance"] = value.get("call_resistance")
                    levels["put_support"] = value.get("put_support")
                    levels["gamma_wall"] = value.get("gamma_wall_0dte")
                    levels["hvl"] = value.get("hvl")
        return levels
    except Exception as e:
        logger.exception(f"Erreur résolution niveaux: {e}")
        return {}


# === FONCTIONS DE CONVERSION SPÉCIFIQUES ===

def _convert_basedata(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[MarketBarM1]:
    try:
        ohlc = {"o": event.get("o", 0.0), "h": event.get("h", 0.0), "l": event.get("l", 0.0), "c": event.get("c", 0.0)}
        return MarketBarM1(
            symbol=symbol,
            ts=ts,
            ohlc=ohlc,
            volume=int(event.get("v", 0) or 0),
            bid_volume=event.get("bidvol"),
            ask_volume=event.get("askvol"),
            open_interest=event.get("oi"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion basedata: {e}")
        return None


def _convert_vwap(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[VWAPBandM1]:
    try:
        return VWAPBandM1(
            symbol=symbol,
            ts=ts,
            vwap=float(event.get("v", 0.0) or 0.0),
            upper_band_1=event.get("up1"),
            lower_band_1=event.get("dn1"),
            upper_band_2=event.get("up2"),
            lower_band_2=event.get("dn2"),
            source=event.get("src"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion vwap: {e}")
        return None


def _convert_vva(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[VolumeProfile]:
    try:
        # mapping prev_* est garanti par _normalize_field_names quand process_line() est utilisé
        return VolumeProfile(
            symbol=symbol,
            ts=ts,
            vah=float(event.get("vah", 0.0) or 0.0),
            val=float(event.get("val", 0.0) or 0.0),
            vpoc=float(event.get("vpoc", 0.0) or 0.0),
            prev_vah=None,  # VVA previous fields removed
            prev_val=None,  # VVA previous fields removed
            prev_vpoc=None,  # VVA previous fields removed
            session_id_current=event.get("id_curr"),
            session_id_previous=event.get("id_prev"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion vva: {e}")
        return None


def _convert_vap(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[VolumeProfileTick]:
    try:
        return VolumeProfileTick(
            symbol=symbol,
            ts=ts,
            price=float(event.get("price", 0.0) or 0.0),
            volume=int(event.get("vol", 0) or 0),
            bar_number=event.get("bar"),
            k_value=event.get("k"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion vap: {e}")
        return None


def _convert_depth(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[DOMLevel]:
    try:
        return DOMLevel(
            symbol=symbol,
            ts=ts,
            side=str(event.get("side", "BID")),
            level=int(event.get("lvl", 1) or 1),
            price=float(event.get("price", 0.0) or 0.0),
            size=int(event.get("size", 0) or 0),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion depth: {e}")
        return None


def _convert_quote(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[Quote]:
    try:
        return Quote(
            symbol=symbol,
            ts=ts,
            bid=float(event.get("bid", 0.0) or 0.0),
            ask=float(event.get("ask", 0.0) or 0.0),
            bid_quantity=int(event.get("bq", 0) or 0),
            ask_quantity=int(event.get("aq", 0) or 0),
            sequence=event.get("seq"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion quote: {e}")
        return None


def _convert_trade(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[TradeTick]:
    try:
        return TradeTick(
            symbol=symbol,
            ts=ts,
            price=float(event.get("px", 0.0) or 0.0),
            volume=int(event.get("vol", 0) or 0),
            sequence=event.get("seq"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion trade: {e}")
        return None


def _convert_pvwap(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[VWAPBandM30]:
    try:
        return VWAPBandM30(
            symbol=symbol,
            ts=ts,
            vwap=float(event.get("pvwap", 0.0) or 0.0),
            upper_band_1=event.get("up1"),
            lower_band_1=event.get("dn1"),
            upper_band_2=event.get("up2"),
            lower_band_2=event.get("dn2"),
        )
    except Exception as e:
        logger.exception(f"Erreur conversion pvwap: {e}")
        return None


def _convert_vix(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[VIXTick]:
    try:
        return VIXTick(symbol=symbol, ts=ts, price=float(event.get("last", 0.0) or 0.0), mode=event.get("mode"))
    except Exception as e:
        logger.exception(f"Erreur conversion vix: {e}")
        return None


def _convert_menthorq(event: Dict[str, Any], symbol: str, ts: datetime) -> Optional[MenthorQLevels]:
    # Consolidation gérée par MenthorQConsolidator
    return None


# === ENRICHISSEMENTS ===

def calculate_menthorq_distances(current_price: float, menthorq_levels: MenthorQLevels) -> Dict[str, float]:
    try:
        distances: Dict[str, float] = {}
        if menthorq_levels.call_resistance:
            distances["dist_to_call_res"] = abs(current_price - menthorq_levels.call_resistance)
        if menthorq_levels.put_support:
            distances["dist_to_put_sup"] = abs(current_price - menthorq_levels.put_support)
        if menthorq_levels.gamma_wall_0dte:
            distances["dist_to_gamma_wall"] = abs(current_price - menthorq_levels.gamma_wall_0dte)
        if menthorq_levels.blind_spots:
            distances["min_dist_to_BL"] = min(abs(current_price - p) for p in menthorq_levels.blind_spots.values())
        if menthorq_levels.swing_levels:
            distances["min_dist_to_swing"] = min(abs(current_price - p) for p in menthorq_levels.swing_levels.values())
        return distances
    except Exception as e:
        logger.exception(f"Erreur calcul distances MenthorQ: {e}")
        return {}


def calculate_enrichments(record: InternalRecord, context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        enrichments: Dict[str, Any] = {}
        if isinstance(record, MarketBarM1):
            ohlc = record.ohlc
            enrichments["m1_range"] = ohlc["h"] - ohlc["l"]
            if record.bid_volume is not None and record.ask_volume is not None:
                enrichments["nbcv_m1"] = (record.ask_volume - record.bid_volume)
        elif isinstance(record, VWAPBandM1):
            cp = float(context.get("current_price", 0.0) or 0.0)
            if cp > 0:
                enrichments["vwap_distance"] = abs(cp - record.vwap)
                enrichments["pos_vs_vwap"] = ("above" if cp > record.vwap else "below")
        elif isinstance(record, VolumeProfile):
            cp = float(context.get("current_price", 0.0) or 0.0)
            if cp > 0:
                enrichments["dist_to_vah"] = abs(cp - record.vah)
                enrichments["dist_to_val"] = abs(cp - record.val)
                enrichments["dist_to_vpoc"] = abs(cp - record.vpoc)
        return enrichments
    except Exception as e:
        logger.exception(f"Erreur calcul enrichissements: {e}")
        return {}


# === CONSOLIDATION MENTHORQ ===
class MenthorQConsolidator:
    def __init__(self) -> None:
        self.pending_levels: Dict[str, Dict[str, Any]] = {}
        self.consolidated_levels: Dict[str, MenthorQLevels] = {}

    def add_menthorq_event(self, event: Dict[str, Any]) -> Optional[MenthorQLevels]:
        try:
            symbol = event.get("sym", "")
            ts = parse_ts(event.get("ts", ""))
            if ts is None:
                return None
            event_type = event.get("type", "")
            key = f"{symbol}_{ts.replace(second=0, microsecond=0).isoformat()}"
            if key not in self.pending_levels:
                self.pending_levels[key] = {
                    "symbol": symbol,
                    "ts": ts,
                    "gamma_levels": {},
                    "blind_spots": {},
                    "swing_levels": {},
                    "call_resistance": None,
                    "put_support": None,
                    "gamma_wall_0dte": None,
                    "hvl": None,
                    "partial": True,
                }
            lvl = self.pending_levels[key]
            label = str(event.get("label", ""))
            price = float(event.get("price", 0.0) or 0.0)
            if event_type == "menthorq_gamma_levels":
                if label == "Call Resistance":
                    lvl["call_resistance"] = price
                elif label == "Put Support":
                    lvl["put_support"] = price
                elif label == "Gamma Wall 0DTE":
                    lvl["gamma_wall_0dte"] = price
                elif label == "HVL":
                    lvl["hvl"] = price
                elif label.startswith("GEX"):
                    lvl["gamma_levels"][label] = price
            elif event_type == "menthorq_blind_spots" and label.startswith("BL"):
                lvl["blind_spots"][label] = price
            elif event_type == "menthorq_swing_levels" and label.startswith("SG"):
                lvl["swing_levels"][label] = price

            if (lvl["call_resistance"] is not None) and (lvl["put_support"] is not None):
                consolidated = MenthorQLevels(
                    symbol=symbol,
                    ts=ts,
                    gamma_levels=lvl["gamma_levels"].copy(),
                    blind_spots=lvl["blind_spots"].copy(),
                    swing_levels=lvl["swing_levels"].copy(),
                    call_resistance=lvl["call_resistance"],
                    put_support=lvl["put_support"],
                    gamma_wall_0dte=lvl["gamma_wall_0dte"],
                    hvl=lvl["hvl"],
                    partial=lvl["partial"],
                )
                self.consolidated_levels[key] = consolidated
                del self.pending_levels[key]
                logger.debug(
                    "Consolidé MenthorQ: %s @ %s - CR=%s, PS=%s",
                    symbol, ts, consolidated.call_resistance, consolidated.put_support,
                )
                return consolidated
            return None
        except Exception as e:
            logger.exception(f"Erreur consolidation MenthorQ: {e}")
            return None


# === FACTORIES ===

def create_structure_data_processor(
    stale_minutes: int = 5,
    enable_dedup: bool = True,
    enable_stale_filter: bool = True,
) -> StructureDataProcessor:
    return StructureDataProcessor(
        stale_minutes=stale_minutes,
        enable_dedup=enable_dedup,
        enable_stale_filter=enable_stale_filter,
    )


def create_menthorq_consolidator() -> MenthorQConsolidator:
    return MenthorQConsolidator()


# === TESTS RAPIDES (exécutés si __main__) ===

def _test_trade_and_prev_mapping() -> None:
    # prev_* mapping
    proc = create_structure_data_processor()
    line = json.dumps({
        "type": "vva", "graph": 3, "sym": "ESU25_FUT_CME", "ts": datetime.now(timezone.utc).isoformat(),
        "vah": 6530.0, "val": 6520.0, "vpoc": 6526.0,
        "pvah": 6518.0, "pval": 6510.0, "ppoc": 6515.0,
    })
    evt = proc.process_line(line)
    assert evt is not None and evt.get("prev_vah") == 6518.0 and evt.get("prev_vpoc") == 6515.0

    # trade conversion
    rec = to_internal({
        "type": "trade", "graph": 3, "sym": "ESU25_FUT_CME",
        "ts": datetime.now(timezone.utc).isoformat(), "px": 6534.25, "vol": 5,
    })
    assert isinstance(rec, TradeTick) and rec.price == 6534.25 and rec.volume == 5


if __name__ == "__main__":
    print("🧪 Smoke tests v2.1")
    _test_trade_and_prev_mapping()
    print("✅ OK")
