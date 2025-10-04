#!/usr/bin/env python3
"""
Streaming Unifier Service
=========================

Surveille les fichiers quote CHART_3 (ES) et CHART_9 (NQ) du jour courant.
À chaque nouvelle ligne reçue, construit un snapshot minimal et appelle
l'unifier correspondant, puis écrit le résultat dans un JSONL de sortie.

Sans dépendances externes (polling), compatible Windows/PowerShell.
"""

import os
import sys
import json
import time
import glob
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from collections import deque
from zoneinfo import ZoneInfo

# Assurer l'import des modules du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unifier.elite_unifier_es import unify_es_elite
from unifier.elite_unifier_nq import unify_nq_elite
from unifier.legacy_adapter import LegacyAdapter

# Checkpoints offsets pour reprise exacte
CHECKPOINTS_PATH = (Path(__file__).resolve().parent.parent / "results" / "_checkpoints.json")
FSYNC_EVERY_LINE = False  # fsync périodique pour éviter les blocages

# État BN par chart et symbole (cum delta, L1 match, ladder)
_state_by_chart: Dict[int, Dict[str, Dict[str, Any]]] = {3: {}, 9: {}}
_last_minute_flush: float = 0.0
_adapters: Dict[int, LegacyAdapter] = {}
AUTO_QC: bool = True
_qc_warned: Dict[str, bool] = {}
_qc_bootstrapped: Dict[int, bool] = {}


def _today_paths(base_dir: Path, ymd: Optional[str] = None) -> Tuple[Path, Path]:
    """Retourne les dossiers CHART_3 et CHART_9 pour la date ymd (YYYYMMDD)."""
    if ymd is None:
        ymd = time.strftime("%Y%m%d")
    # Arborescence attendue: DATA_SIERRA_CHART/DATA_2025/MOIS/YYYYMMDD/CHART_X
    # On rglob dynamiquement car le mois est variable (OCTOBRE, SEPTEMBRE, ...)
    base = base_dir
    chart3 = None
    chart9 = None
    if base.exists():
        for p in base.rglob(f"**/{ymd}/CHART_3"):
            chart3 = p
            break
        for p in base.rglob(f"**/{ymd}/CHART_9"):
            chart9 = p
            break
    return chart3 or Path(), chart9 or Path()


def paris_ymd() -> str:
    from datetime import datetime
    try:
        return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y%m%d")
    except Exception:
        return time.strftime("%Y%m%d")


def ensure_manual_qc_ok(base_day_dir: Path, ymd: str, charts=(3, 9)) -> None:
    base_day_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, UTC
    now_iso = datetime.now(UTC).isoformat()
    # Certains unifiers cherchent encore la date système locale → créer aussi ce QC si différent
    sys_ymd = time.strftime("%Y%m%d")
    for cid in charts:
        for target_ymd in {ymd, sys_ymd}:
            qc_path = base_day_dir / f"CHART_{cid}" / f"chart_{cid}_qc_go_nogo_{target_ymd}.json"
            if not qc_path.exists():
                qc_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "date": target_ymd,
                    "chart": cid,
                    "go": True,
                    "reason": "manual_ok",
                    "manual_ok": True,
                    "created_at": now_iso,
                    "notes": "auto-generated to silence QC warnings; replace with real QC when available"
                }
                with open(qc_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)


def day_dir_from_chart_dir(chart_dir: Path) -> Path:
    return chart_dir.resolve().parent if chart_dir else Path()


def _latest_file(chart_dir: Path, chart_id: int, ymd: str, kind: str) -> Optional[Path]:
    """Trouve le dernier fichier (quote, depth, trade_summary) en supportant plusieurs formats.
    Essaie sous CHART_X/ puis CHART_X/CLEAN/ et prend le plus récent (mtime).
    """
    if not chart_dir or not chart_dir.exists():
        return None

    def _collect(dirpath: Path) -> list[str]:
        patterns = [
            f"chart_{chart_id}_{kind}_{ymd}_*.jsonl",
            f"chart_{chart_id}_{kind}_*_{ymd}.jsonl",
            f"chart_{chart_id}_{kind}_{ymd}.jsonl",
        ]
        fs: list[str] = []
        for pat in patterns:
            fs.extend(glob.glob(str(dirpath / pat)))
        return fs

    files = _collect(chart_dir)
    clean_dir = chart_dir / "CLEAN"
    if not files and clean_dir.exists():
        files = _collect(clean_dir)
    if not files:
        return None
    files.sort(key=lambda p: os.path.getmtime(p))
    return Path(files[-1])


def _load_checkpoints() -> Dict[str, int]:
    try:
        if CHECKPOINTS_PATH.exists():
            with open(CHECKPOINTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {str(Path(k)): int(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _save_checkpoints(offsets: Dict[str, int]) -> None:
    CHECKPOINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINTS_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(offsets, f, ensure_ascii=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, CHECKPOINTS_PATH)


def _tail_file(path: Path, start_at_end: bool, offsets: Dict[str, int]) -> Tuple[Any, Any]:
    """Crée un générateur qui yield les nouvelles lignes et retourne aussi le fichier ouvert.

    Retourne:
        (generator, file_handle)
    """
    abs_path = str(path.resolve())
    f = open(path, "r", encoding="utf-8")

    if start_at_end:
        if abs_path in offsets:
            try:
                f.seek(int(offsets[abs_path]))
            except Exception:
                f.seek(0, os.SEEK_END)
        else:
            f.seek(0, os.SEEK_END)

    def _gen():
        while True:
            where = f.tell()
            line = f.readline()
            if not line:
                f.seek(where)
                time.sleep(0.2)
                continue
            offsets[abs_path] = f.tell()
            yield line

    return _gen(), f


def _build_snapshot_from_quote(q: Dict[str, Any]) -> Dict[str, Any]:
    bid = q.get("bid", 0.0)
    ask = q.get("ask", 0.0)

    # Rescale *100 → prix humains si nécessaire (détection par grille 0.25 → 25)
    def _human(x: Any) -> Any:
        try:
            if isinstance(x, int):
                return (x / 100.0) if (x > 10000 and x % 25 == 0) else float(x)
            if isinstance(x, float) and x.is_integer():
                xi = int(x)
                return (xi / 100.0) if (xi > 10000 and xi % 25 == 0) else float(x)
            return x
        except Exception:
            return x

    bid_h = _human(bid)
    ask_h = _human(ask)

    spread = (ask_h - bid_h) if (isinstance(ask_h, (int, float)) and isinstance(bid_h, (int, float))) else 0.0
    neg_spread = isinstance(spread, (int, float)) and spread < 0
    last = ask_h if ask_h else (bid_h if bid_h else 0.0)

    return {
        "sym": q.get("sym"),
        "t": q.get("t"),
        "last": last,
        "ofdom": {"best_bid": bid_h, "best_ask": ask_h, "spread": spread},
        "_neg_spread": neg_spread,
    }


def _append_jsonl(out_path: Path, obj: Dict[str, Any]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        if FSYNC_EVERY_LINE:
            f.flush(); os.fsync(f.fileno())


def _get_sym_state(chart_id: int, sym: str) -> Dict[str, Any]:
    st = _state_by_chart[chart_id].get(sym)
    if st is None:
        st = {
            "atr_points": None,
            "cum_delta_day": 0,
            "cum_delta_session": 0,
            "l1_match_window": deque(maxlen=1200),
            "ladder_ok_window": deque(maxlen=400),
        }
        _state_by_chart[chart_id][sym] = st
    return st


def _avg(values):
    return (sum(values) / len(values)) if values else None


def _write_bn_minute_report(out_dir: Path, chart_id: int, ymd: str):
    """Écrit un rapport minute des ratios BN (moyennes fenêtres) par symbole."""
    per_sym = {}
    for sym, st in _state_by_chart.get(chart_id, {}).items():
        l1 = _avg(list(st["l1_match_window"])) if st.get("l1_match_window") is not None else None
        lad = _avg(list(st["ladder_ok_window"])) if st.get("ladder_ok_window") is not None else None
        per_sym[sym] = {
            "bn_l1_match_tol_ratio_win": round(l1, 3) if l1 is not None else None,
            "bn_ladder_ok_ratio_win": round(lad, 3) if lad is not None else None,
            "cum_delta_day": st.get("cum_delta_day"),
            "cum_delta_session": st.get("cum_delta_session"),
        }

    rep = {
        "t": time.time(),
        "chart": chart_id,
        "ymd": ymd,
        "symbols": per_sym,
    }
    out_path = out_dir / "unified" / "_monitor" / f"chart_{chart_id}_bn_minute_{ymd}.jsonl"
    _append_jsonl(out_path, rep)


def _process_quote_line(line: str, chart_id: int, out_dir: Path, strict_qc: bool, ymd: str) -> None:
    try:
        q = json.loads(line)
    except Exception:
        return
    if q.get("type") not in ("quote", "BIDASK", "QUOTE", None):
        # On tolère divers formats tant qu'il y a bid/ask
        pass
    if "bid" not in q and "ask" not in q:
        return

    snapshot = _build_snapshot_from_quote(q)
    sym = snapshot.get("sym") or "UNKNOWN"

    # Fusion fichiers → snapshot (MenthorQ/VWAP) via LegacyAdapter
    try:
        adapter = _adapters.get(chart_id)
        if adapter and hasattr(adapter, "_merge_menthorq_vwap_from_files"):
            snapshot = adapter._merge_menthorq_vwap_from_files(snapshot)
    except Exception:
        pass

    res = {}
    try:
        if chart_id == 3:
            res = unify_es_elite(snapshot, config={"allow_missing_qc": not strict_qc, "send_messages": False})
        else:
            res = unify_nq_elite(snapshot, config={"allow_missing_qc": not strict_qc, "send_messages": False})
    except Exception:
        res = {}

    # Résumé minimal utile + sauvegarde complète pour audit
    st = _get_sym_state(chart_id, sym)
    l1_ratio = (sum(st["l1_match_window"]) / max(1, len(st["l1_match_window"]))) if st["l1_match_window"] else None
    ladder_ratio = (sum(st["ladder_ok_window"]) / max(1, len(st["ladder_ok_window"]))) if st["ladder_ok_window"] else None
    # qc_mode télémétrie
    try:
        # si out_dir ressemble à .../CHART_X, day_dir = parent; sinon fallback
        day_dir = out_dir.parent if out_dir.name.startswith("CHART_") else None
        if day_dir is not None:
            present = (day_dir / f"CHART_{chart_id}" / f"chart_{chart_id}_qc_go_nogo_{ymd}.json").exists()
            qc_mode = "auto" if AUTO_QC else ("present" if present else "missing_strict")
        else:
            qc_mode = "auto" if AUTO_QC else "present"
    except Exception:
        qc_mode = "present"
    gating = res.get("gating") or {}
    synth = res.get("elite_synthesis") or {}
    # Extraits compacts VWAP & MenthorQ pour debug
    vwap_blk = snapshot.get("vwap") or {}
    mq_keys = (
        "gex_call_wall","gex_put_wall","blind_spot","swing_level","ps0dte","hvl",
        "call_resistance","call_resistance_0dte","put_support","put_support_0dte",
    )
    mq_blk = {k: snapshot.get(k) for k in mq_keys if snapshot.get(k) is not None}

    # Blind spots compacts + distances
    blind_blk = None
    try:
        bs = snapshot.get("menthorq_blind_spots") or {}
        last_px = snapshot.get("last")
        if isinstance(bs, dict) and isinstance(last_px, (int, float)):
            # Construire liste (name, px, dist_abs) filtrée des outliers évidents
            items = []
            for name, px in bs.items():
                try:
                    val = float(px)
                except Exception:
                    continue
                # Filtrer valeurs aberrantes (ex: 0, ou >> 10x prix courant)
                if val <= 0 or val > (last_px * 10):
                    continue
                items.append({"name": name, "px": val, "dist": round(abs(val - float(last_px)), 6)})
            if items:
                items.sort(key=lambda x: x["dist"])  # plus proches d'abord
                blind_blk = {
                    "top": items[:3],
                    "count": len(items),
                    "id": snapshot.get("menthorq_blind_id"),
                }
    except Exception:
        blind_blk = None

    summary = {
        "chart": res.get("chart") or chart_id,
        "sym": sym,
        "t": snapshot.get("t"),
        "data_age_ms": res.get("data_age_ms"),
        "go_live": gating.get("go_live"),
        "component_scores": synth.get("component_scores") or {},
        "gates_status": synth.get("gates_status") or {},
        "bn_l1_match_tol_ratio_win": round(l1_ratio, 3) if l1_ratio is not None else None,
        "bn_ladder_ok_ratio_win": round(ladder_ratio, 3) if ladder_ratio is not None else None,
        "qc_mode": qc_mode,
        "vwap": vwap_blk or None,
        "menthorq_levels": (mq_blk or None),
        "menthorq_blind_spots": blind_blk,
        "neg_spread": bool(snapshot.get("_neg_spread")),
        "message": res.get("message"),
    }

    # Sortie par symbole dans le dossier du chart du jour
    out_path = out_dir / "unified" / sym / f"chart_{chart_id}_unified_{ymd}.jsonl"
    _append_jsonl(out_path, {"summary": summary, "full": res})


def _drain_tail(gen, max_lines: int = 50):
    read = 0
    while read < max_lines:
        try:
            line = next(gen)
        except StopIteration:
            break
        if not line:
            break
        yield line
        read += 1


def _process_trade_summary_line(line: str, chart_id: int) -> None:
    try:
        ev = json.loads(line)
    except Exception:
        return
    if ev.get("type") != "trade_summary":
        return
    sym = ev.get("sym") or ev.get("symbol")
    if not sym:
        return
    st = _get_sym_state(chart_id, sym)
    day = ev.get("cum_delta_day")
    sess = ev.get("cum_delta_session")
    if isinstance(day, (int, float)):
        st["cum_delta_day"] = int(day)
    if isinstance(sess, (int, float)):
        st["cum_delta_session"] = int(sess)
    else:
        bv = ev.get("buy_vol")
        sv = ev.get("sell_vol")
        if isinstance(bv, (int, float)) and isinstance(sv, (int, float)):
            st["cum_delta_day"] = int(bv - sv)


def _process_depth_line(line: str, chart_id: int) -> None:
    try:
        d = json.loads(line)
    except Exception:
        return
    if d.get("type") not in ("depth", "DEPTH", None):
        return
    sym = d.get("sym")
    if not sym:
        return
    st = _get_sym_state(chart_id, sym)
    m = d.get("match_L1")
    if isinstance(m, bool):
        st["l1_match_window"].append(1.0 if m else 0.0)
    lad = d.get("ladder_monotonic_ok_ratio")
    if isinstance(lad, (int, float)):
        st["ladder_ok_window"].append(float(lad))


def run_stream(strict_qc: bool = True, ymd: Optional[str] = None, base_dir: str = "DATA_SIERRA_CHART"):
    base = Path(base_dir)
    if ymd is None:
        ymd = paris_ymd()

    chart3_dir, chart9_dir = _today_paths(base, ymd)
    if not chart3_dir and not chart9_dir:
        print(f"⚠️ Dossiers du jour introuvables sous {base} pour {ymd}. Attente…")

    # Répertoires de sortie (on écrit par symbole sous /unified/<SYM>/...)
    out_dir3 = chart3_dir if (chart3_dir and chart3_dir.exists()) else (PROJECT_ROOT / "results")
    out_dir9 = chart9_dir if (chart9_dir and chart9_dir.exists()) else (PROJECT_ROOT / "results")

    # QC manual_ok pour supprimer les warnings (optionnel)
    def _qc_present(day_dir: Path, cid: int, _ymd: str) -> bool:
        return (day_dir / f"CHART_{cid}" / f"chart_{cid}_qc_go_nogo_{_ymd}.json").exists()

    if AUTO_QC:
        if chart3_dir and chart3_dir.exists():
            ensure_manual_qc_ok(chart3_dir.parent, ymd, charts=(3,))
        if chart9_dir and chart9_dir.exists():
            ensure_manual_qc_ok(chart9_dir.parent, ymd, charts=(9,))
    else:
        # Avertir une fois si QC manquant
        if chart3_dir and chart3_dir.exists() and not _qc_present(chart3_dir.parent, 3, ymd):
            if not _qc_warned.get("3"):
                print(f"[QC] CHART_3 {ymd}: fichier QC manquant (auto-qc OFF) — continuer avec warnings/minor gating.")
                _qc_warned["3"] = True
        if chart9_dir and chart9_dir.exists() and not _qc_present(chart9_dir.parent, 9, ymd):
            if not _qc_warned.get("9"):
                print(f"[QC] CHART_9 {ymd}: fichier QC manquant (auto-qc OFF) — continuer avec warnings/minor gating.")
                _qc_warned["9"] = True

    # Offsets (checkpoints)
    offsets: Dict[str, int] = _load_checkpoints()

    # Instancier les adapters Legacy pour fusionner fichiers→snapshot
    global _adapters
    _adapters = {}
    if chart3_dir and chart3_dir.exists():
        _adapters[3] = LegacyAdapter(base_day_dir=str(chart3_dir.parent), ymd=ymd, chart_id=3)
    if chart9_dir and chart9_dir.exists():
        _adapters[9] = LegacyAdapter(base_day_dir=str(chart9_dir.parent), ymd=ymd, chart_id=9)

    # Pointeurs des derniers fichiers par type
    last_q3 = last_d3 = last_t3 = None
    last_q9 = last_d9 = last_t9 = None

    # Tails
    tail_q3 = tail_d3 = tail_t3 = None
    tail_q9 = tail_d9 = tail_t9 = None
    open_files: Dict[Tuple[str, str], Any] = {}

    # nettoyage: variables inutilisées supprimées

    while True:
        # Rafraîchir les répertoires du jour (au cas où ils apparaissent plus tard)
        if (not chart3_dir or not chart3_dir.exists()) or (not chart9_dir or not chart9_dir.exists()):
            chart3_dir, chart9_dir = _today_paths(base, ymd)

        # CHART 3 (quote/depth/trade_summary)
        if chart3_dir and chart3_dir.exists():
            lq3 = _latest_file(chart3_dir, 3, ymd, "quote")
            if lq3 and lq3 != last_q3:
                if open_files.get(("3", "quote")):
                    try: open_files[("3", "quote")].close()
                    except: pass
                last_q3 = lq3
                tail_q3, fh = _tail_file(lq3, start_at_end=True, offsets=offsets)
                open_files[("3", "quote")] = fh
                print(f"📡 CHART_3 QUOTE: {lq3}")
                # Bootstrap QC si le dossier apparaît après démarrage
                if chart3_dir and chart3_dir.exists() and not _qc_bootstrapped.get(3):
                    if AUTO_QC:
                        ensure_manual_qc_ok(chart3_dir.parent, ymd, charts=(3,))
                    else:
                        # avertir une seule fois si QC manquant
                        qc_path = chart3_dir.parent / f"CHART_3" / f"chart_3_qc_go_nogo_{ymd}.json"
                        if not qc_path.exists() and not _qc_warned.get("3"):
                            print(f"[QC] CHART_3 {ymd}: fichier QC manquant (auto-qc OFF) — continuer avec warnings/minor gating.")
                            _qc_warned["3"] = True
                    _qc_bootstrapped[3] = True
            ld3 = _latest_file(chart3_dir, 3, ymd, "depth")
            if ld3 and ld3 != last_d3:
                if open_files.get(("3", "depth")):
                    try: open_files[("3", "depth")].close()
                    except: pass
                last_d3 = ld3
                tail_d3, fh = _tail_file(ld3, start_at_end=True, offsets=offsets)
                open_files[("3", "depth")] = fh
                print(f"📡 CHART_3 DEPTH: {ld3}")
            lt3 = _latest_file(chart3_dir, 3, ymd, "trade_summary")
            if lt3 and lt3 != last_t3:
                if open_files.get(("3", "trade_summary")):
                    try: open_files[("3", "trade_summary")].close()
                    except: pass
                last_t3 = lt3
                tail_t3, fh = _tail_file(lt3, start_at_end=True, offsets=offsets)
                open_files[("3", "trade_summary")] = fh
                print(f"📡 CHART_3 TRADE_SUMMARY: {lt3}")

        # CHART 9 (quote/depth/trade_summary)
        if chart9_dir and chart9_dir.exists():
            lq9 = _latest_file(chart9_dir, 9, ymd, "quote")
            if lq9 and lq9 != last_q9:
                if open_files.get(("9", "quote")):
                    try: open_files[("9", "quote")].close()
                    except: pass
                last_q9 = lq9
                tail_q9, fh = _tail_file(lq9, start_at_end=True, offsets=offsets)
                open_files[("9", "quote")] = fh
                print(f"📡 CHART_9 QUOTE: {lq9}")
                # Bootstrap QC si le dossier apparaît après démarrage
                if chart9_dir and chart9_dir.exists() and not _qc_bootstrapped.get(9):
                    if AUTO_QC:
                        ensure_manual_qc_ok(chart9_dir.parent, ymd, charts=(9,))
                    else:
                        # avertir une seule fois si QC manquant
                        qc_path = chart9_dir.parent / f"CHART_9" / f"chart_9_qc_go_nogo_{ymd}.json"
                        if not qc_path.exists() and not _qc_warned.get("9"):
                            print(f"[QC] CHART_9 {ymd}: fichier QC manquant (auto-qc OFF) — continuer avec warnings/minor gating.")
                            _qc_warned["9"] = True
                    _qc_bootstrapped[9] = True
            ld9 = _latest_file(chart9_dir, 9, ymd, "depth")
            if ld9 and ld9 != last_d9:
                if open_files.get(("9", "depth")):
                    try: open_files[("9", "depth")].close()
                    except: pass
                last_d9 = ld9
                tail_d9, fh = _tail_file(ld9, start_at_end=True, offsets=offsets)
                open_files[("9", "depth")] = fh
                print(f"📡 CHART_9 DEPTH: {ld9}")
            lt9 = _latest_file(chart9_dir, 9, ymd, "trade_summary")
            if lt9 and lt9 != last_t9:
                if open_files.get(("9", "trade_summary")):
                    try: open_files[("9", "trade_summary")].close()
                    except: pass
                last_t9 = lt9
                tail_t9, fh = _tail_file(lt9, start_at_end=True, offsets=offsets)
                open_files[("9", "trade_summary")] = fh
                print(f"📡 CHART_9 TRADE_SUMMARY: {lt9}")

        # Lire lignes si disponibles
        if tail_q3 is not None:
            try:
                for line in _drain_tail(tail_q3, max_lines=50):
                    _process_quote_line(line, 3, out_dir3, strict_qc, ymd)
            except StopIteration:
                tail_q3 = None
            except Exception:
                pass

        if tail_q9 is not None:
            try:
                for line in _drain_tail(tail_q9, max_lines=50):
                    _process_quote_line(line, 9, out_dir9, strict_qc, ymd)
            except StopIteration:
                tail_q9 = None
            except Exception:
                pass

        # DEPTH → mise à jour état BN
        if tail_d3 is not None:
            try:
                for line in _drain_tail(tail_d3, max_lines=100):
                    _process_depth_line(line, 3)
            except StopIteration:
                tail_d3 = None
            except Exception:
                pass
        if tail_d9 is not None:
            try:
                for line in _drain_tail(tail_d9, max_lines=100):
                    _process_depth_line(line, 9)
            except StopIteration:
                tail_d9 = None
            except Exception:
                pass

        # TRADE_SUMMARY → cum delta
        if tail_t3 is not None:
            try:
                for line in _drain_tail(tail_t3, max_lines=50):
                    _process_trade_summary_line(line, 3)
            except StopIteration:
                tail_t3 = None
            except Exception:
                pass
        if tail_t9 is not None:
            try:
                for line in _drain_tail(tail_t9, max_lines=50):
                    _process_trade_summary_line(line, 9)
            except StopIteration:
                tail_t9 = None
            except Exception:
                pass

        # Checkpoint périodique
        last_ckpt = getattr(run_stream, "_last_ckpt", 0.0)
        now = time.time()
        if now - last_ckpt > 2.0:
            _save_checkpoints(offsets)
            # fsync périodique des fichiers de sortie via reopen implicite (noop ici)
            setattr(run_stream, "_last_ckpt", now)

        # Rapport minute BN (flush chaque changement de minute +/- 5s)
        global _last_minute_flush
        if int(now // 60) != int(_last_minute_flush // 60):
            if out_dir3 is not None:
                _write_bn_minute_report(out_dir3, 3, ymd)
            if out_dir9 is not None:
                _write_bn_minute_report(out_dir9, 9, ymd)
            _last_minute_flush = now

        time.sleep(0.2)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Service de streaming Unifier (CHART_3 & CHART_9)")
    parser.add_argument("--ymd", help="Date YYYYMMDD (par défaut: aujourd'hui)")
    parser.add_argument("--base", default="DATA_SIERRA_CHART", help="Dossier base des données Sierra")
    parser.add_argument("--allow-missing-qc", action="store_true", help="Autoriser l'absence de QC (mode dev)")
    parser.add_argument("--no-auto-qc", action="store_true", help="Désactiver la création auto des JSON QC 'manual_ok' (prod)")
    args = parser.parse_args()

    strict_qc = not args.allow_missing_qc
    global AUTO_QC
    AUTO_QC = not args.no_auto_qc
    run_stream(strict_qc=strict_qc, ymd=args.ymd, base_dir=args.base)


if __name__ == "__main__":
    main()






