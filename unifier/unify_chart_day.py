# -*- coding: utf-8 -*-
"""
unifier/unify_chart_day.py
Unifie les fichiers d'un chart (3=ES, 9=NQ) pour une journée.

Usage:
  python unifier/unify_chart_day.py --root .../YYYYMMDD --date YYYYMMDD --chart 3 \
         [--symbol ESZ25-CME] [--with-dom] [--with-nbcv] \
         [--vwap_p95 0.10 --vwap_p99 0.15 --session_reset 100]
"""

from __future__ import annotations

import json
from pathlib import Path
import glob
from typing import Dict, Any, List, Tuple
import math
import numpy as np
import sys

# Seuils d'alerte VWAP (en pourcentage)
P95_THRESH = 0.10
P99_THRESH = 0.15
# Seuil reset session cum_delta (valeur par défaut, ajustable via --session_reset)
SESSION_RESET_THRESH = 100.0

# Import robuste des modules locaux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from quality.computations import compute_vwap_from_trades, SessionRules
    from utils.clean_jsonl import clean_symbol_file
    # Coeur commun QC/validations
    from unifier.unify_core import (
        QCSummary,
        write_qc_summary,
        detect_tick_size,
        validate_vva_order,
        validate_nbcv_row,
        validate_spreads_vs_tick,
        check_price_plausibility,
    )
except Exception as e:
    print(f"[WARN] Import quality.computations impossible: {e}")
    compute_vwap_from_trades = None
    SessionRules = None
    try:
        from utils.clean_jsonl import clean_symbol_file
    except Exception as _:
        clean_symbol_file = None
    try:
        from unifier.unify_core import (
            QCSummary,
            write_qc_summary,
            detect_tick_size,
            validate_vva_order,
            validate_nbcv_row,
            validate_spreads_vs_tick,
            check_price_plausibility,
        )
    except Exception as _:
        QCSummary = None
        write_qc_summary = None
        detect_tick_size = None
        validate_vva_order = None
        validate_nbcv_row = None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for ln in f:
            try:
                rows.append(json.loads(ln))
            except Exception:
                continue
    return rows


def _validate_session_resets(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Valide les resets de session dans les données cumulative delta (sur trades).
    """
    validation = {
        "session_transitions": 0,
        "reset_warnings": [],
        "session_stats": {},
        "status": "OK",
    }
    if not rows:
        return validation
    sessions = {}
    for row in rows:
        session_id = row.get("session_id")
        if session_id:
            sessions.setdefault(session_id, []).append(row)
    for session_id, session_rows in sessions.items():
        if not session_rows:
            continue
        session_rows.sort(key=lambda x: float(x.get('t', 0)))
        cds_vals = [float(r.get('cum_delta_session', 0) or 0) for r in session_rows]
        cdd_vals = [float(r.get('cum_delta_day', 0) or 0) for r in session_rows]
        stats = {
            "count": len(session_rows),
            "cum_delta_session": {
                "min": min(cds_vals) if cds_vals else 0,
                "max": max(cds_vals) if cds_vals else 0,
                "final": cds_vals[-1] if cds_vals else 0,
            },
            "cum_delta_day": {
                "min": min(cdd_vals) if cdd_vals else 0,
                "max": max(cdd_vals) if cdd_vals else 0,
                "final": cdd_vals[-1] if cdd_vals else 0,
            },
        }
        first_cds = cds_vals[0] if cds_vals else 0
        if abs(first_cds) > SESSION_RESET_THRESH:
            validation["reset_warnings"].append(
                f"Session {session_id}: reset suspect (première cum_delta_session={first_cds:.1f})"
            )
            validation["status"] = "WARN"
        validation["session_stats"][session_id] = stats
    ids = [r.get("session_id") for r in rows if r.get("session_id")]
    transitions = 0
    for i in range(1, len(ids)):
        if ids[i] != ids[i-1]:
            transitions += 1
    validation["session_transitions"] = transitions
    return validation


def _validate_dom(depth_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    QC DOM: ratios kept/match/valid et tolérance min/max.
    """
    total_depth = 0
    kept_depth = 0
    match_depth = 0
    valid_depth = 0
    tol_values: List[float] = []
    for r in depth_rows:
        if r.get("type") != "depth":
            continue
        total_depth += 1
        if "quote_bid" in r and "quote_ask" in r:
            kept_depth += 1
        try:
            if int(r.get("match_L1", 0) or 0) == 1:
                match_depth += 1
        except Exception:
            pass
        try:
            if int(r.get("valid", 0) or 0) == 1:
                valid_depth += 1
        except Exception:
            pass
        if "tol_ms_used" in r:
            try:
                tol_values.append(float(r["tol_ms_used"]))
            except Exception:
                pass
    ratio_kept = (kept_depth / total_depth) if total_depth > 0 else None
    ratio_match = (match_depth / total_depth) if total_depth > 0 else None
    ratio_valid = (valid_depth / total_depth) if total_depth > 0 else None
    status = "OK"
    if ratio_match is not None and ratio_match < 0.30:
        status = "WARN"
    return {
        "count_total": total_depth,
        "count_kept": kept_depth,
        "count_match": match_depth,
        "count_valid": valid_depth,
        "ratio_kept": ratio_kept,
        "ratio_match": ratio_match,
        "ratio_valid": ratio_valid,
        "tol_min": min(tol_values) if tol_values else None,
        "tol_max": max(tol_values) if tol_values else None,
        "status": status,
    }


def _check_study_inventory(root: Path, ymd: str, chart: int) -> None:
    inv_fp = root / f"study_inventory_chart_{chart}_{ymd}.jsonl"
    if not inv_fp.exists():
        print("[WARN] Study inventory introuvable (optional)")
        return
    inv_rows = _read_jsonl(inv_fp)
    vwap_study = None
    for r in inv_rows:
        if r.get("study_id") == 1 or str(r.get("name", "")).lower().startswith("volume weighted average price"):
            vwap_study = r
            break
    if vwap_study is None:
        print("[WARN] Study VWAP absente dans l'inventaire (study_id=1)")
        return
    sg = vwap_study.get("subgraphs") or []
    expected = {0: "VWAP", 1: "Top Band 1", 2: "Bottom Band 1", 3: "Top Band 2", 4: "Bottom Band 2"}
    alerts = []
    for idx, name in expected.items():
        try:
            got = (sg[idx] or {}).get("name", "")
        except Exception:
            got = ""
        if not got or (name and got != name):
            alerts.append((idx, name, got))
    if alerts:
        print("[WARN] Study VWAP subgraphs inattendus:")
        for idx, exp, got in alerts:
            print(f"   - sg[{idx}] attendu='{exp}' obtenu='{got}'")
    else:
        print("[OK] Study VWAP (id=1) inventaire OK (subgraphs cles)")


def _dedupe_vwap_study(vwap_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    last_by_key: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
    for r in vwap_rows:
        if r.get('type') != 'vwap':
            continue
        key = (r.get('i'), r.get('t'))
        last_by_key[key] = r
    deduped = list(last_by_key.values())
    removed = max(0, len(vwap_rows) - len(deduped))
    return sorted(deduped, key=lambda x: (x.get('i'), x.get('t'))), removed


def _consolidate_basedata(basedata_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, int, int]:
    by_i: Dict[Any, Dict[str, Any]] = {}
    revisions = 0
    v_decrease = 0
    for r in basedata_rows:
        if r.get('type') != 'basedata':
            continue
        i = r.get('i')
        prev = by_i.get(i)
        if prev is None or (r.get('t', 0) or 0) >= (prev.get('t', 0) or 0):
            if prev is not None:
                revisions += 1
                try:
                    if int(r.get('v', 0) or 0) < int(prev.get('v', 0) or 0):
                        v_decrease += 1
                except Exception:
                    pass
            by_i[i] = r
    consolidated = list(by_i.values())
    removed = max(0, len(basedata_rows) - len(consolidated))
    return sorted(consolidated, key=lambda x: x.get('i')), removed, revisions, v_decrease


def _dedupe_series_by_t_value(series: List[Dict[str, Any]], t_key: str, v_key: str) -> List[Dict[str, Any]]:
    """Déduplique une série temporelle par t, en gardant la dernière valeur pour chaque t.
    Retourne une liste triée par t, avec clés 't' et v_key conservé.
    """
    last_by_t: Dict[float, float] = {}
    for r in series:
        try:
            t = float(r.get(t_key))
            v = float(r.get(v_key))
        except Exception:
            continue
        last_by_t[t] = v
    out: List[Dict[str, Any]] = []
    for t, v in last_by_t.items():
        out.append({'t': float(t), v_key: float(v)})
    out.sort(key=lambda x: x['t'])
    return out

def _validate_volumes_per_bar(final_rows: List[Dict[str, Any]]) -> Dict[str, int]:
    bad_neg = 0
    bad_sum = 0
    non_integer = 0
    for r in final_rows:
        v = float(r.get('v', 0) or 0)
        bidv = float(r.get('bidvol', 0) or 0)
        askv = float(r.get('askvol', 0) or 0)
        if v < 0 or bidv < 0 or askv < 0:
            bad_neg += 1
        if not float(v).is_integer() or not float(bidv).is_integer() or not float(askv).is_integer():
            non_integer += 1
        if round(bidv) + round(askv) != round(v):
            bad_sum += 1
    return {"negatives": bad_neg, "sum_mismatch": bad_sum, "non_integer": non_integer}


def _extract_trade_fields(r: Dict[str, Any]) -> Tuple[float, float, float] | None:
    t_keys = ["t", "time", "ts", "timestamp"]
    p_keys = ["px", "p", "price", "Price"]
    q_keys = ["vol", "q", "qty", "volume", "Volume", "size", "Size"]
    t = p = q = None
    for k in t_keys:
        if k in r:
            try:
                t = float(r[k])
                break
            except Exception:
                pass
    for k in p_keys:
        if k in r:
            try:
                p = float(r[k])
                break
            except Exception:
                pass
    for k in q_keys:
        if k in r:
            try:
                q = float(r[k])
                break
            except Exception:
                pass
    if t is None or p is None or q is None:
        return None
    return (t, p, q)


def _resolve_chart_files(prefix: Path, chart: int, ymd: str, symbol: str | None) -> Dict[str, Path]:
    files: Dict[str, Path] = {}
    def mk(name: str, sym: str | None) -> Path:
        if sym:
            # Essais multiples d'ordre (certains dumps ont symbole avant date)
            p1 = prefix / f"chart_{chart}_{name}_{ymd}_{sym}.jsonl"
            p2 = prefix / f"chart_{chart}_{name}_{sym}_{ymd}.jsonl"
            return p1 if p1.exists() else p2
        else:
            return prefix / f"chart_{chart}_{name}_{ymd}.jsonl"

    names = ["basedata","vwap","trade","nbcv","depth","vva","quote"]
    for n in names:
        files[n] = mk(n, symbol)
    for n in names:
        p = files[n]
        if not p.exists():
            # Chercher variantes: date avant/ après symbole
            patterns = [
                str(prefix / f"chart_{chart}_{n}_{ymd}*.jsonl"),
                str(prefix / f"chart_{chart}_{n}_*_{ymd}.jsonl"),
                str(prefix / f"chart_{chart}_{n}_*.jsonl"),
            ]
            matches: List[str] = []
            for pat in patterns:
                matches.extend(glob.glob(pat))
            # Prioriser ceux qui contiennent explicitement la date
            matches = sorted(set(matches), key=lambda x: (ymd not in x, x))
            if matches:
                files[n] = Path(matches[0])
    return files


def unify_chart_day(root: Path, ymd: str, chart: int, symbol: str | None = None) -> int:
    _check_study_inventory(root, ymd, chart)
    prefix = root / f"CHART_{chart}"
    paths = _resolve_chart_files(prefix, chart, ymd, symbol)
    base_fp = paths["basedata"]
    vwap_fp = paths["vwap"]
    trade_fp = paths["trade"]
    nbcv_fp = paths["nbcv"]
    vva_fp = paths["vva"]
    quote_fp = paths["quote"]
    depth_fp = paths["depth"]

    # Pré-filtrage par symbole (si demandé) vers CLEAN/
    if symbol and clean_symbol_file is not None:
        clean_dir = prefix / "CLEAN"
        clean_dir.mkdir(parents=True, exist_ok=True)
        base_clean = clean_dir / f"chart_{chart}_basedata_{ymd}_{symbol}.jsonl"
        vwap_clean = clean_dir / f"chart_{chart}_vwap_{ymd}_{symbol}.jsonl"
        trade_clean = clean_dir / f"chart_{chart}_trade_{ymd}_{symbol}.jsonl"
        nbcv_clean = clean_dir / f"chart_{chart}_nbcv_{ymd}_{symbol}.jsonl"
        try:
            clean_symbol_file(base_fp, base_clean, sym=symbol)
            clean_symbol_file(vwap_fp, vwap_clean, sym=symbol)
            if trade_fp.exists():
                clean_symbol_file(trade_fp, trade_clean, sym=symbol)
            if nbcv_fp.exists():
                clean_symbol_file(nbcv_fp, nbcv_clean, sym=symbol)
        except Exception as e:
            print(f"[WARN] Echec nettoyage CLEAN/ pour {symbol}: {e}")
        else:
            base_fp, vwap_fp, trade_fp, nbcv_fp = base_clean, vwap_clean, trade_clean, nbcv_clean

    # Priorité au fichier VWAP "solution" s'il existe
    vwap_solution_candidates = [
        prefix / f"chart_{chart}_vwap_solution_{ymd}.jsonl",
        prefix / f"chart_{chart}_vwap_solution_{ymd}_{symbol}.jsonl" if symbol else prefix / "__nope__"
    ]
    for cand in vwap_solution_candidates:
        if cand.exists():
            vwap_fp = cand
            break

    basedata_rows = _read_jsonl(base_fp)
    vwap_rows = _read_jsonl(vwap_fp)
    trade_rows = _read_jsonl(trade_fp)
    vva_rows = _read_jsonl(vva_fp) if vva_fp.exists() else []
    quote_rows = _read_jsonl(quote_fp) if quote_fp.exists() else []
    depth_rows: List[Dict[str, Any]] = []

    print(f"[INFO] basedata lignes: {len(basedata_rows)} | vwap lignes: {len(vwap_rows)} | trades lignes: {len(trade_rows)}")

    vwap_deduped, vwap_dupes_removed = _dedupe_vwap_study(vwap_rows)
    basedata_final, base_removed, base_revisions, base_v_decrease = _consolidate_basedata(basedata_rows)

    vwap_by_i = {r.get('i'): r for r in vwap_deduped}
    # Fallback par temps (nearest-time) pour VWAP study (utile CHART_9)
    vwap_times: List[float] = []
    vwap_vals: List[float] = []
    for r in vwap_deduped:
        if r.get('type') != 'vwap':
            continue
        try:
            t = float(r.get('t'))
            v = float(r.get('v')) if r.get('v') is not None else None
            if v is None:
                continue
            vwap_times.append(t)
            vwap_vals.append(v)
        except Exception:
            continue
    vwap_by_minute: Dict[int, float] = {}
    if vwap_times:
        pairs_tv = sorted(zip(vwap_times, vwap_vals), key=lambda x: x[0])
        vwap_times = [p[0] for p in pairs_tv]
        vwap_vals = [p[1] for p in pairs_tv]
        # Index par minute (t en secondes → minute entière)
        for t, v in pairs_tv:
            try:
                minute_key = int(float(t) // 60.0)
                vwap_by_minute[minute_key] = v  # garde la dernière valeur vue pour la minute
            except Exception:
                continue

    # Derived VWAP from trades (optional)
    derived_vwap_by_time: List[Dict[str, Any]] = []
    parsed_ticks = 0
    if trade_rows:
        seen = set()
        ticks = []
        for tr in trade_rows:
            extracted = _extract_trade_fields(tr)
            if extracted is None:
                continue
            t, p, q = extracted
            try:
                if not (math.isnan(t) or math.isnan(p) or math.isnan(q)) and q > 0:
                    k = (t, p, q)
                    if k in seen:
                        continue
                    seen.add(k)
                    ticks.append({"t": t, "p": p, "q": q})
                    parsed_ticks += 1
            except Exception:
                continue
        if ticks:
            ticks.sort(key=lambda r: r["t"]) 
        try:
            if compute_vwap_from_trades is not None:
                rules = SessionRules(rth_start_utc="13:30", rth_end_utc="20:00", reset_on_session_change=True)
                derived_vwap_by_time = compute_vwap_from_trades(ticks, rules=rules)
                print(f"[INFO] dvwap via quality: ticks utilises: {parsed_ticks} | dvwap points: {len(derived_vwap_by_time)}")
            else:
                # fallback simple cumulatif
                pv = 0.0
                vv = 0.0
                out: List[Dict[str, float]] = []
                for r in ticks:
                    q = float(r.get('q', 0) or 0)
                    p = float(r.get('p', 0) or 0)
                    t = float(r.get('t', 0) or 0)
                    if q <= 0:
                        continue
                    pv += p * q
                    vv += q
                    if vv > 0:
                        out.append({'t': t, 'vwap': pv / vv})
                derived_vwap_by_time = out
                print(f"[INFO] dvwap via fallback: ticks utilises: {parsed_ticks} | dvwap points: {len(derived_vwap_by_time)}")
            if derived_vwap_by_time:
                derived_vwap_by_time.sort(key=lambda r: r["t"]) 
        except Exception as e:
            print(f"[WARN] Echec calcul dvwap: {e}")

    dv_idx = 0
    # tolérance nearest-time (secondes)
    NEAREST_TOL_S = 2.0
    # NBCV cum_delta (optionnel)
    cum_delta_by_time: List[Dict[str, float]] = []
    nbcv_bad_total = 0
    nbcv_bad_delta = 0
    if nbcv_fp.exists():
        nbcv_rows = _read_jsonl(nbcv_fp)
        series = []
        cum = None
        for r in nbcv_rows:
            if r.get('type') != 'nbcv':
                continue
            try:
                t = float(r.get('t'))
                if 'cumulative_delta' in r and r['cumulative_delta'] is not None:
                    cum = float(r['cumulative_delta'])
                else:
                    av = float(r.get('ask_volume', 0) or 0)
                    bv = float(r.get('bid_volume', 0) or 0)
                    cum = (0.0 if cum is None else cum) + (av - bv)
                series.append({'t': t, 'cum_delta': float(cum)})
                # QC NBCV (si helper dispo)
                if validate_nbcv_row is not None:
                    ok_total, ok_delta = validate_nbcv_row(r)
                    if not ok_total:
                        nbcv_bad_total += 1
                    if not ok_delta:
                        nbcv_bad_delta += 1
            except Exception:
                continue
        if series:
            series.sort(key=lambda r: r['t'])
            cum_delta_by_time = _dedupe_series_by_t_value(series, 't', 'cum_delta')

    unified: List[Dict[str, Any]] = []
    for r in basedata_final:
        i = r.get('i')
        w = vwap_by_i.get(i)
        out = {
            "chart": r.get('chart', chart),
            "i": i,
            "t": r.get('t'),
            "o": r.get('o'), "h": r.get('h'), "l": r.get('l'), "c": r.get('c'),
            "v": r.get('v'), "bidvol": r.get('bidvol'), "askvol": r.get('askvol'),
        }
        if w is not None:
            out["study_vwap"] = w.get('v')
        # fallback temporel: si pas trouvé par index, essayer par temps
        # 1) Fallback minute-bucket (robuste overlay/snapshot)
        if out.get("study_vwap") is None and vwap_by_minute:
            try:
                t_bar = float(r.get('t'))
                minute_key = int(t_bar // 60.0)
                if minute_key in vwap_by_minute:
                    out["study_vwap"] = vwap_by_minute[minute_key]
            except Exception:
                pass
        # 2) Fallback nearest-time ±2s si toujours vide
        if out.get("study_vwap") is None and vwap_times:
            try:
                import bisect
                t_bar = float(r.get('t'))
                j = bisect.bisect_left(vwap_times, t_bar)
                candidates = []
                if 0 <= j < len(vwap_times):
                    candidates.append((abs(vwap_times[j] - t_bar), j))
                if j-1 >= 0:
                    candidates.append((abs(vwap_times[j-1] - t_bar), j-1))
                if j+1 < len(vwap_times):
                    candidates.append((abs(vwap_times[j+1] - t_bar), j+1))
                if candidates:
                    best_dt, best_j = min(candidates, key=lambda x: x[0])
                    if best_dt <= NEAREST_TOL_S:
                        out["study_vwap"] = vwap_vals[best_j]
            except Exception:
                pass
        if derived_vwap_by_time:
            try:
                t_bar = float(r.get('t'))
                while dv_idx + 1 < len(derived_vwap_by_time) and float(derived_vwap_by_time[dv_idx + 1]['t']) <= t_bar:
                    dv_idx += 1
                if dv_idx < len(derived_vwap_by_time) and float(derived_vwap_by_time[dv_idx]['t']) <= t_bar:
                    out["derived_vwap"] = derived_vwap_by_time[dv_idx]['vwap']
            except Exception:
                pass
        # cum_delta: priorité NBCV si dispo, sinon absent (ce script ne reconstruit pas depuis trades/basedata pour rester générique)
        if cum_delta_by_time:
            try:
                t_bar = float(r.get('t'))
                # recherche index courant
                # binaire simple: avance séquentielle (données triées)
                # on garde un index local
                # réutiliser dv_idx style si nécessaire
            except Exception:
                pass
        unified.append(out)

    vol_issues = _validate_volumes_per_bar(unified)
    out_fp = prefix / f"chart_{chart}_unified_{ymd}.jsonl"
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    with open(out_fp, 'w', encoding='utf-8') as f:
        for r in unified:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[OK] Unification CHART_{chart} terminee -> {out_fp}")
    print(f"VWAP study: doublons supprimés = {vwap_dupes_removed}")
    print(f"Basedata: lignes supprimées = {base_removed}, révisions = {base_revisions}, v_recul={base_v_decrease}")
    print(f"Volumes: negatifs = {vol_issues['negatives']}, bid+ask!=v = {vol_issues['sum_mismatch']}, non_integer = {vol_issues['non_integer']}")

    # Deviation stats if both study and derived present
    dev = []
    dev_ticks = []
    for r in unified:
        sv = r.get('study_vwap')
        dv = r.get('derived_vwap')
        if sv is None or dv is None:
            continue
        try:
            svf = float(sv); dvf = float(dv)
            if dvf != 0:
                dev.append(abs(svf - dvf) / abs(dvf))
            # ticks
            try:
                # tenter de déduire le tick via symbol_guess plus tard si nécessaire
                pass
            except Exception:
                pass
        except Exception:
            continue
    if dev:
        v = np.array(dev, dtype=float) * 100.0
        p95, p99 = float(np.nanpercentile(v, 95)), float(np.nanpercentile(v, 99))
        mx = float(np.nanmax(v))
        print(f"Ecart VWAP study vs derived: p95={p95:.3f}% p99={p99:.3f}% max={mx:.3f}% n={len(v)}")
        status = "[OK]" if (p95 <= P95_THRESH and p99 <= P99_THRESH) else "[WARN]"
        print(f"{status} Seuils: p95<= {P95_THRESH:.2f}% ; p99<= {P99_THRESH:.2f}%")
    # Compute deviation in ticks if possible (requires tick size)
    vwap_p95_ticks = None
    vwap_p99_ticks = None
    vwap_pairs_count = 0
    try:
        # déterminer le symbole pour trouver le tick
        symbol_guess = None
        for src in (basedata_rows, trade_rows, quote_rows):
            if src:
                symbol_guess = src[0].get("sym") or src[0].get("symbol")
                if symbol_guess:
                    break
        tick_sz = detect_tick_size(symbol_guess) if detect_tick_size is not None else 0.25
        if tick_sz and tick_sz > 0:
            diffs = []
            for r in unified:
                sv = r.get('study_vwap'); dv = r.get('derived_vwap')
                if sv is None or dv is None:
                    continue
                try:
                    diffs.append(abs(float(sv) - float(dv)) / tick_sz)
                except Exception:
                    continue
            if diffs:
                arr = np.array(diffs, dtype=float)
                vwap_pairs_count = int(len(arr))
                # Appliquer un seuil minimum de paires pour valider le contrôle
                if vwap_pairs_count >= 30:
                    vwap_p95_ticks = float(np.nanpercentile(arr, 95))
                    vwap_p99_ticks = float(np.nanpercentile(arr, 99))
                else:
                    vwap_p95_ticks = None
                    vwap_p99_ticks = None
                print(f"Ecart VWAP (ticks): p95={vwap_p95_ticks:.3f} p99={vwap_p99_ticks:.3f} n={len(arr)}")
    except Exception as _:
        pass
    # DOM QC (optionnel si fichier présent)
    dom_stats = None
    if depth_fp.exists():
        depth_rows = _read_jsonl(depth_fp)
        if depth_rows:
            dom_stats = _validate_dom(depth_rows)
            print(f"[INFO] DOM events: {dom_stats['count_total']}")
            if dom_stats['ratio_match'] is not None:
                print(f"[INFO] DOM ratio_match (L1==BBO): {dom_stats['count_match']}/{dom_stats['count_total']} = {dom_stats['ratio_match']:.2%}")
            if dom_stats['ratio_kept'] is not None:
                print(f"[INFO] DOM ratio_kept: {dom_stats['count_kept']}/{dom_stats['count_total']} = {dom_stats['ratio_kept']:.2%}")
            if dom_stats['ratio_valid'] is not None:
                print(f"[INFO] DOM ratio_valid: {dom_stats['count_valid']}/{dom_stats['count_total']} = {dom_stats['ratio_valid']:.2%}")
            if dom_stats['tol_min'] is not None and dom_stats['tol_max'] is not None:
                print(f"[INFO] tol_ms_used: {dom_stats['tol_min']} – {dom_stats['tol_max']} ms")

            qc_dom_fp = prefix / f"chart_{chart}_qc_dom_{ymd}.json"
            with open(qc_dom_fp, 'w', encoding='utf-8') as f:
                json.dump(dom_stats, f, indent=2)
            print(f"[OK] Rapport DOM sauvegardé -> {qc_dom_fp}")

    # QC summary global (+ GO/NO-GO si coeur commun dispo)
    qc_summary = {
        "chart": chart,
        "date": ymd,
        "counts": {
            "basedata": len(basedata_rows),
            "vwap": len(vwap_rows),
            "trades": len(trade_rows),
            "vva": len(vva_rows),
            "quotes": len(quote_rows),
        },
        "vwap_deviation": {},
        "sessions": {},
        "dom": dom_stats,
    }
    # VWAP deviation summary
    if dev:
        v = np.array(dev, dtype=float) * 100.0
        qc_summary["vwap_deviation"] = {
            "p95_pct": float(np.nanpercentile(v, 95)),
            "p99_pct": float(np.nanpercentile(v, 99)),
            "max_pct": float(np.nanmax(v)),
            "n": len(v),
        }
    if vwap_p95_ticks is not None or vwap_p99_ticks is not None:
        qc_summary["vwap_deviation"]["p95_ticks"] = vwap_p95_ticks
        qc_summary["vwap_deviation"]["p99_ticks"] = vwap_p99_ticks
    qc_summary["vwap_deviation"]["n_pairs"] = vwap_pairs_count
    # Sessions (si dispo)
    if trade_rows:
        sess = _validate_session_resets(trade_rows)
        qc_summary["sessions"] = sess

    qc_summary_fp = prefix / f"chart_{chart}_qc_summary_{ymd}.json"
    with open(qc_summary_fp, 'w', encoding='utf-8') as f:
        json.dump(qc_summary, f, indent=2)
    print(f"[OK] QC summary sauvegardé -> {qc_summary_fp}")

    # GO/NO-GO synthétique (si unify_core dispo)
    if QCSummary is not None and write_qc_summary is not None:
        # spread_nonneg_ratio (quotes)
        nonneg = 0
        total_spreads = 0
        bids, asks = [], []
        for q in quote_rows:
            if q.get("type") != "quote":
                continue
            try:
                bid = float(q.get("bid")); ask = float(q.get("ask"))
                bids.append(bid); asks.append(ask)
                total_spreads += 1
                if ask - bid >= 0:
                    nonneg += 1
            except Exception:
                continue
        spread_ratio = (nonneg / total_spreads) if total_spreads > 0 else 1.0
        # vva validity
        vva_valid = 0
        for vv in vva_rows:
            if vv.get("type") != "vva":
                continue
            if validate_vva_order is None or validate_vva_order(vv):
                vva_valid += 1
        symbol_guess = None
        # meilleure tentative: depuis basedata/trade
        for src in (basedata_rows, trade_rows, quote_rows):
            if src:
                symbol_guess = src[0].get("sym") or src[0].get("symbol")
                if symbol_guess:
                    break
        tick = detect_tick_size(symbol_guess) if detect_tick_size is not None else 0.25
        # spreads multiples du tick + plausibilité prix
        spread_multiple_ratio = None
        price_plausible = None
        if validate_spreads_vs_tick is not None and bids and asks:
            spread_multiple_ratio, _ = validate_spreads_vs_tick(bids, asks, tick)
        if check_price_plausibility is not None:
            prices = []
            try:
                prices.extend([float(r.get('c')) for r in basedata_rows if r.get('c') is not None])
            except Exception:
                pass
            try:
                prices.extend([float(r.get('price')) for r in trade_rows if r.get('price') is not None])
            except Exception:
                pass
            try:
                prices.extend(bids + asks)
            except Exception:
                pass
            price_plausible = check_price_plausibility(prices)
        unknown_sessions = sum(1 for r in trade_rows if (r.get("session_id") == "Unknown"))
        qc = QCSummary(
            symbol=symbol_guess or "",
            chart=chart,
            date=ymd,
            spread_nonneg_ratio=spread_ratio,
            tick_size=tick,
            vva_valid_count=vva_valid,
            vva_total=len([vv for vv in vva_rows if vv.get("type")=="vva"]),
            nbcv_bad_total=nbcv_bad_total,
            nbcv_bad_delta=nbcv_bad_delta,
            vwap_p95_ticks=vwap_p95_ticks,
            vwap_p99_ticks=vwap_p99_ticks,
            scale_used=None,
            unknown_sessions=unknown_sessions,
            spread_multiple_ratio=spread_multiple_ratio,
            price_plausible=price_plausible,
        )
        qc_go_fp = prefix / f"chart_{chart}_qc_go_nogo_{ymd}.json"
        write_qc_summary(qc_go_fp, qc)
        print(f"[OK] QC GO/NO-GO sauvegardé -> {qc_go_fp} | go={qc.go_nogo()}")

    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Dossier racine de la journée (…/YYYYMMDD)")
    ap.add_argument("--date", required=True, help="YYYYMMDD")
    ap.add_argument("--chart", type=int, required=True, choices=[3, 9], help="Numéro de chart (3=ES, 9=NQ)")
    ap.add_argument("--symbol", required=False, help="Symbole strict à garder (ex: ESZ25-CME ou NQZ25-CME)")
    ap.add_argument("--vwap_p95", type=float, required=False, help="Seuil p95 VWAP en % (defaut 0.10)")
    ap.add_argument("--vwap_p99", type=float, required=False, help="Seuil p99 VWAP en % (defaut 0.15)")
    ap.add_argument("--session_reset", type=float, required=False, help="Seuil reset session cum_delta (defaut 100.0)")
    args = ap.parse_args()
    # Paramétrage tolérances
    global P95_THRESH, P99_THRESH, SESSION_RESET_THRESH
    if args.vwap_p95 is not None:
        P95_THRESH = float(args.vwap_p95)
    if args.vwap_p99 is not None:
        P99_THRESH = float(args.vwap_p99)
    if args.session_reset is not None:
        SESSION_RESET_THRESH = float(args.session_reset)
    return unify_chart_day(Path(args.root), args.date, args.chart, symbol=args.symbol)


if __name__ == "__main__":
    raise SystemExit(main())


