"""
unifier/unify_chart3_day.py
Unifie les fichiers du CHART 3 (ES) pour une journée donnée.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import math
import numpy as np
import sys

# Seuils d'alerte VWAP (en pourcentage)
P95_THRESH = 0.10
P99_THRESH = 0.15

# Seuils d'alerte NBCV cum_delta (ABS en contrats)
ABS_CUM_P95_THRESH = 200.0
ABS_CUM_P99_THRESH = 400.0

# Seuils d'alerte pour les resets de session (en contrats)
SESSION_RESET_THRESH = 100.0

# Définition des sessions UTC
SESSIONS_UTC = {
    "Asia": ("23:00", "07:00"),
    "London": ("07:00", "13:30"),
    "US": ("13:30", "23:00"),
}

# Assurer que le projet racine est dans sys.path pour les imports locaux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

try:
	from quality.computations import compute_vwap_from_trades, SessionRules
except Exception as e:
	print(f"[WARN] Import quality.computations impossible: {e}")
	compute_vwap_from_trades = None
	SessionRules = None

try:
	from utils.clean_jsonl import clean_symbol_file
except Exception:
	clean_symbol_file = None


def _compute_vwap_simple(ticks: List[Dict[str, float]]) -> List[Dict[str, float]]:
	"""Fallback simple: VWAP cumulatif sans reset de session."""
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
	return out


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
	validation = {
		"session_transitions": 0,
		"reset_warnings": [],
		"session_stats": {},
		"status": "OK"
	}
	if not rows:
		return validation
	sessions = {}
	for row in rows:
		session_id = row.get("session_id")
		if session_id and session_id in SESSIONS_UTC:
			if session_id not in sessions:
				sessions[session_id] = []
			sessions[session_id].append(row)
	for session_id, session_rows in sessions.items():
		if not session_rows:
			continue
		session_rows.sort(key=lambda x: float(x.get('t', 0)))
		cum_delta_session_values = [float(r.get('cum_delta_session', 0)) for r in session_rows]
		cum_delta_day_values = [float(r.get('cum_delta_day', 0)) for r in session_rows]
		session_stats = {
			"count": len(session_rows),
			"cum_delta_session": {
				"min": min(cum_delta_session_values) if cum_delta_session_values else 0,
				"max": max(cum_delta_session_values) if cum_delta_session_values else 0,
				"final": cum_delta_session_values[-1] if cum_delta_session_values else 0
			},
			"cum_delta_day": {
				"min": min(cum_delta_day_values) if cum_delta_day_values else 0,
				"max": max(cum_delta_day_values) if cum_delta_day_values else 0,
				"final": cum_delta_day_values[-1] if cum_delta_day_values else 0
			}
		}
		first_cum_delta_session = cum_delta_session_values[0] if cum_delta_session_values else 0
		if abs(first_cum_delta_session) > SESSION_RESET_THRESH:
			warning = f"Session {session_id}: reset suspect (première valeur cum_delta_session = {first_cum_delta_session:.1f})"
			validation["reset_warnings"].append(warning)
			validation["status"] = "WARN"
		validation["session_stats"][session_id] = session_stats
	session_ids = [r.get("session_id") for r in rows if r.get("session_id")]
	transitions = 0
	for i in range(1, len(session_ids)):
		if session_ids[i] != session_ids[i-1]:
			transitions += 1
	validation["session_transitions"] = transitions
	return validation


def _check_study_inventory(root: Path, ymd: str) -> None:
	candidates = [
		root / f"study_inventory_chart_3_{ymd}.jsonl",
		Path(f"study_inventory_chart_3_{ymd}.jsonl"),
	]
	inv_rows: List[Dict[str, Any]] = []
	for fp in candidates:
		if fp.exists():
			inv_rows = _read_jsonl(fp)
			break
	if not inv_rows:
		print("[WARN] Study inventory introuvable (optional)")
		return
	vwap_study = None
	for r in inv_rows:
		if r.get("study_id") == 1 or str(r.get("name", "")).lower().startswith("volume weighted average price"):
			vwap_study = r
			break
	if vwap_study is None:
		print("[WARN] Study VWAP absente dans l'inventaire (study_id=1)")
		return
	# Optionnel: checks subgraphs


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


def _validate_dom(depth_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
	total_depth = 0
	kept_depth = 0
	match_depth = 0
	valid_depth = 0
	tol_values: List[float] = []
	for r in depth_rows:
		if r.get("type") != "depth":
			continue
		total_depth += 1
		has_quotes = ("quote_bid" in r and "quote_ask" in r)
		if has_quotes:
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


def _extract_trade_fields(r: Dict[str, Any]) -> Tuple[float, float, float] | None:
	# timestamp keys
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


def _dedupe_series_by_t_value(rows: List[Dict[str, float]], t_key: str, v_key: str) -> List[Dict[str, float]]:
	last_by_t: Dict[float, Dict[str, float]] = {}
	for r in rows:
		last_by_t[float(r[t_key])] = r
	deduped = []
	prev_val = None
	for t in sorted(last_by_t.keys()):
		val = last_by_t[t][v_key]
		if prev_val is not None and val == prev_val:
			continue
		deduped.append({t_key: t, v_key: val})
		prev_val = val
	return deduped


def unify_chart3_day(root: Path, ymd: str, symbol: str | None = None) -> int:
	_check_study_inventory(root, ymd)

	base_fp = root / f"CHART_3/chart_3_basedata_{ymd}.jsonl"
	vwap_fp = root / f"CHART_3/chart_3_vwap_{ymd}.jsonl"
	trade_fp = root / f"CHART_3/chart_3_trade_{ymd}.jsonl"
	nbcv_fp = root / f"CHART_3/chart_3_nbcv_{ymd}.jsonl"

	if symbol and clean_symbol_file is not None:
		clean_dir = root / "CHART_3" / "CLEAN"
		clean_dir.mkdir(parents=True, exist_ok=True)
		base_clean = clean_dir / f"chart_3_basedata_{ymd}_{symbol}.jsonl"
		vwap_clean = clean_dir / f"chart_3_vwap_{ymd}_{symbol}.jsonl"
		trade_clean = clean_dir / f"chart_3_trade_{ymd}_{symbol}.jsonl"
		nbcv_clean = clean_dir / f"chart_3_nbcv_{ymd}_{symbol}.jsonl"
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

	basedata_rows = _read_jsonl(base_fp)
	vwap_rows = _read_jsonl(vwap_fp)
	depth_fp = root / f"CHART_3/chart_3_depth_{ymd}.jsonl"
	depth_rows = _read_jsonl(depth_fp)

	print(f"[INFO] basedata lignes: {len(basedata_rows)}  | vwap lignes: {len(vwap_rows)}")
	if len(basedata_rows) == 0:
		print("[ERROR] Aucune ligne dans basedata. Abandon.")
		return 2

	vwap_deduped, vwap_dupes_removed = _dedupe_vwap_study(vwap_rows)
	basedata_final, base_removed, base_revisions, base_v_decrease = _consolidate_basedata(basedata_rows)

	vwap_by_i = {r.get('i'): r for r in vwap_deduped}
	derived_vwap_by_time: List[Dict[str, Any]] = []
	parsed_ticks = 0
	nbcv_cum_by_time: List[Dict[str, float]] = []
	own_cum_by_time: List[Dict[str, float]] = []
	cum_delta_by_time: List[Dict[str, float]] = []

	# Trades -> dvwap + own cum delta
	trade_rows: List[Dict[str, Any]] = []
	if trade_fp.exists():
		print(f"[INFO] trade fichier present: {trade_fp}")
		trade_rows = _read_jsonl(trade_fp)
		print(f"[INFO] trade lignes: {len(trade_rows)} | moteur_quality={'OK' if compute_vwap_from_trades is not None else 'ABSENT'}")
		session_validation = _validate_session_resets(trade_rows)
		if session_validation["session_transitions"] > 0:
			print(f"[INFO] Sessions détectées: {list(session_validation['session_stats'].keys())}")
			print(f"[INFO] Transitions de session: {session_validation['session_transitions']}")
		if session_validation["reset_warnings"]:
			for warning in session_validation["reset_warnings"]:
				print(f"[WARN] {warning}")
		seen = set()
		ticks = []
		cum = 0.0
		series_trade_cd: List[Dict[str, float]] = []
		for tr in trade_rows:
			extracted = _extract_trade_fields(tr)
			if extracted is None:
				continue
			t, p, q = extracted
			try:
				if not (math.isnan(t) or math.isnan(p) or math.isnan(q)) and q > 0:
					k = (t, p, q)
					if k not in seen:
						seen.add(k)
						ticks.append({"t": t, "p": p, "q": q})
					side = str(tr.get('side') or '').upper()
					if side == 'BUY':
						cum += float(q)
					elif side == 'SELL':
						cum -= float(q)
					series_trade_cd.append({'t': float(t), 'cum_delta': float(cum)})
			except Exception:
				continue
		if ticks:
			ticks.sort(key=lambda r: r["t"])
		try:
			if compute_vwap_from_trades is not None:
				rules = SessionRules(rth_start_utc="13:30", rth_end_utc="20:00", reset_on_session_change=True)
				derived_vwap_by_time = compute_vwap_from_trades(ticks, rules=rules)
				print(f"[INFO] dvwap via quality: ticks utilises: {len(ticks)} | dvwap points: {len(derived_vwap_by_time)}")
			else:
				derived_vwap_by_time = _compute_vwap_simple(ticks)
				print(f"[INFO] dvwap via fallback: ticks utilises: {len(ticks)} | dvwap points: {len(derived_vwap_by_time)}")
			if derived_vwap_by_time:
				derived_vwap_by_time.sort(key=lambda r: r["t"])
		except Exception as e:
			print(f"[WARN] Echec calcul dvwap: {e}")
		if series_trade_cd:
			series_trade_cd.sort(key=lambda r: r['t'])
			own_cum_by_time = _dedupe_series_by_t_value(series_trade_cd, 't', 'cum_delta')

	# NBCV
	nbcv_bad_delta = 0
	nbcv_bad_total = 0
	if nbcv_fp.exists():
		nbcv_rows = _read_jsonl(nbcv_fp)
		print(f"[INFO] nbcv fichier present: {nbcv_fp} | lignes: {len(nbcv_rows)}")
		series = []
		cum = None
		for r in nbcv_rows:
			if r.get('type') != 'nbcv':
				continue
			try:
				av = float(r.get('ask_volume', 0) or 0)
				bv = float(r.get('bid_volume', 0) or 0)
				v = float(r.get('total_volume', av + bv) or (av + bv))
				d = float(r.get('delta', av - bv) or (av - bv))
				if round(av - bv) != round(d):
					nbcv_bad_delta += 1
				if round(av + bv) != round(v):
					nbcv_bad_total += 1
				t = float(r.get('t'))
				if 'cumulative_delta' in r and r['cumulative_delta'] is not None:
					cum = float(r['cumulative_delta'])
				else:
					cum = (0.0 if cum is None else cum) + (av - bv)
				series.append({'t': t, 'cum_delta': float(cum)})
			except Exception:
				continue
		if series:
			series.sort(key=lambda r: r['t'])
			nbcv_cum_by_time = _dedupe_series_by_t_value(series, 't', 'cum_delta')
			print(f"[INFO] NBCV validations: bad_delta={nbcv_bad_delta} bad_total={nbcv_bad_total}")

	# cum_delta source
	if nbcv_cum_by_time:
		cum_delta_by_time = nbcv_cum_by_time
	elif own_cum_by_time:
		cum_delta_by_time = own_cum_by_time
	else:
		cum = 0.0
		series = []
		for r in sorted(basedata_final, key=lambda x: float(x.get('t') or 0)):
			bidv = float(r.get('bidvol', 0) or 0)
			askv = float(r.get('askvol', 0) or 0)
			cum += (askv - bidv)
			series.append({'t': float(r.get('t') or 0), 'cum_delta': float(cum)})
		cum_delta_by_time = _dedupe_series_by_t_value(series, 't', 'cum_delta')
		own_cum_by_time = cum_delta_by_time

	dv_idx = 0
	cd_idx = 0
	unified: List[Dict[str, Any]] = []
	for r in basedata_final:
		i = r.get('i')
		w = vwap_by_i.get(i)
		out = {
			"chart": r.get('chart', 3),
			"i": i,
			"t": r.get('t'),
			"o": r.get('o'), "h": r.get('h'), "l": r.get('l'), "c": r.get('c'),
			"v": r.get('v'), "bidvol": r.get('bidvol'), "askvol": r.get('askvol'),
		}
		if w is not None:
			out["study_vwap"] = w.get('v')
		if derived_vwap_by_time:
			try:
				t_bar = float(r.get('t'))
				while dv_idx + 1 < len(derived_vwap_by_time) and float(derived_vwap_by_time[dv_idx + 1]['t']) <= t_bar:
					dv_idx += 1
				if dv_idx < len(derived_vwap_by_time) and float(derived_vwap_by_time[dv_idx]['t']) <= t_bar:
					out["derived_vwap"] = derived_vwap_by_time[dv_idx]['vwap']
			except Exception:
				pass
		if cum_delta_by_time:
			try:
				t_bar = float(r.get('t'))
				while cd_idx + 1 < len(cum_delta_by_time) and float(cum_delta_by_time[cd_idx + 1]['t']) <= t_bar:
					cd_idx += 1
				if cd_idx < len(cum_delta_by_time) and float(cum_delta_by_time[cd_idx]['t']) <= t_bar:
					out["cum_delta"] = cum_delta_by_time[cd_idx]['cum_delta']
			except Exception:
				pass
		# copier champs sessions si dispo
		if trade_rows:
			try:
				t_bar = float(r.get('t'))
				closest_trade = None
				min_time_diff = float('inf')
				for tr in trade_rows:
					tr_time = float(tr.get('t', 0))
					time_diff = abs(tr_time - t_bar)
					if time_diff < min_time_diff:
						min_time_diff = time_diff
						closest_trade = tr
				if closest_trade:
					if 'cum_delta_day' in closest_trade:
						out["cum_delta_day"] = closest_trade['cum_delta_day']
					if 'cum_delta_session' in closest_trade:
						out["cum_delta_session"] = closest_trade['cum_delta_session']
					if 'session_id' in closest_trade:
						out["session_id"] = closest_trade['session_id']
			except Exception:
				pass
		unified.append(out)

	vol_issues = _validate_volumes_per_bar(unified)
	out_fp = root / f"CHART_3/chart_3_unified_{ymd}.jsonl"
	out_fp.parent.mkdir(parents=True, exist_ok=True)
	with open(out_fp, 'w', encoding='utf-8') as f:
		for r in unified:
			f.write(json.dumps(r, ensure_ascii=False) + "\n")

	print(f"[OK] Unification CHART_3 terminee -> {out_fp}")
	print(f"VWAP study: doublons supprimés = {vwap_dupes_removed}")
	print(f"Basedata: lignes supprimées (intermédiaires) = {base_removed}, révisions = {base_revisions}, v_recul={base_v_decrease}")
	print(f"Volumes: negatifs = {vol_issues['negatives']}, bid+ask!=v = {vol_issues['sum_mismatch']}, non_integer = {vol_issues['non_integer']}")

	# VWAP dev
	dev = []
	for r in unified:
		sv = r.get('study_vwap')
		dv = r.get('derived_vwap')
		if sv is None or dv is None:
			continue
		try:
			if dv != 0:
				dev.append(abs(float(sv) - float(dv)) / abs(float(dv)))
		except Exception:
			continue
	if dev:
		v = np.array(dev, dtype=float) * 100.0
		p95, p99 = float(np.nanpercentile(v, 95)), float(np.nanpercentile(v, 99))
		mx = float(np.nanmax(v))
		print(f"Ecart VWAP study vs derived: p95={p95:.3f}% p99={p99:.3f}% max={mx:.3f}% n={len(v)}")
		status = "[OK]" if (p95 <= P95_THRESH and p99 <= P99_THRESH) else "[WARN]"
		print(f"{status} Seuils: p95<= {P95_THRESH:.2f}% ; p99<= {P99_THRESH:.2f}%")
	else:
		print("[INFO] Aucune comparaison study vs derived (derived_vwap absent)")

	# Sessions
	if 'session_validation' in locals() and session_validation["session_stats"]:
		print(f"\n[INFO] === STATS SESSIONS CUMULATIVE DELTA ===")
		print(f"[INFO] Transitions de session: {session_validation['session_transitions']}")
		print(f"[INFO] Status global: {session_validation['status']}")
		for session_id, stats in session_validation["session_stats"].items():
			print(f"[INFO] Session {session_id}:")
			print(f"   - Records: {stats['count']}")
			print(f"   - Cum Delta Day: {stats['cum_delta_day']['final']:.1f}")
			print(f"   - Cum Delta Session: {stats['cum_delta_session']['final']:.1f}")
			print(f"   - Range Session: {stats['cum_delta_session']['max'] - stats['cum_delta_session']['min']:.1f}")
	else:
		print("[INFO] Sessions cumulative delta non détectées")

	# DOM
	if depth_rows:
		dom_stats = _validate_dom(depth_rows)
		print(f"[INFO] DOM events: {dom_stats['count_total']}")
		if dom_stats['ratio_match'] is not None:
			print(f"[INFO] DOM ratio_match (L1==BBO): {dom_stats['count_match']}/{dom_stats['count_total']} = {dom_stats['ratio_match']:.2%}")
		else:
			print("[INFO] DOM ratio_match: NA")
		if dom_stats['ratio_kept'] is not None:
			print(f"[INFO] DOM ratio_kept: {dom_stats['count_kept']}/{dom_stats['count_total']} = {dom_stats['ratio_kept']:.2%}")
		if dom_stats['ratio_valid'] is not None:
			print(f"[INFO] DOM ratio_valid: {dom_stats['count_valid']}/{dom_stats['count_total']} = {dom_stats['ratio_valid']:.2%}")
		if dom_stats['tol_min'] is not None and dom_stats['tol_max'] is not None:
			print(f"[INFO] tol_ms_used: {dom_stats['tol_min']} – {dom_stats['tol_max']} ms")
		if dom_stats["status"] != "OK":
			print(f"[WARN] DOM status = {dom_stats['status']}")
	else:
		print("[INFO] Pas de fichier depth pour cette journée")

	# QC DOM
	qc_report_fp = root / f"CHART_3/chart_3_qc_dom_{ymd}.json"
	if depth_rows:
		dom_stats = _validate_dom(depth_rows)
		with open(qc_report_fp, "w", encoding="utf-8") as f:
			json.dump(dom_stats, f, indent=2)
		print(f"[OK] Rapport DOM sauvegardé -> {qc_report_fp}")

	# QC summary
	qc_summary = {
		"chart": 3,
		"date": ymd,
		"counts": {
			"basedata": len(basedata_rows),
			"vwap": len(vwap_rows),
			"trades": len(trade_rows) if isinstance(trade_rows, list) else 0,
			"nbcv": int(nbcv_fp.exists())
		},
		"vwap_deviation": {},
		"nbcv": {
			"bad_delta": int(locals().get('nbcv_bad_delta', 0)),
			"bad_total": int(locals().get('nbcv_bad_total', 0))
		},
		"sessions": locals().get('session_validation', {}),
		"dom": dom_stats if depth_rows else None,
	}
	if dev:
		qc_summary["vwap_deviation"] = {
			"p95_pct": float(np.nanpercentile(np.array(dev, dtype=float)*100.0, 95)),
			"p99_pct": float(np.nanpercentile(np.array(dev, dtype=float)*100.0, 99)),
			"max_pct": float(np.nanmax(np.array(dev, dtype=float)*100.0)),
			"n": len(dev),
		}
	qc_summary_fp = root / f"CHART_3/chart_3_qc_summary_{ymd}.json"
	with open(qc_summary_fp, "w", encoding="utf-8") as f:
		json.dump(qc_summary, f, indent=2)
	print(f"[OK] QC summary sauvegardé -> {qc_summary_fp}")

	return 0


def main():
	import argparse
	ap = argparse.ArgumentParser()
	ap.add_argument("--root", required=True, help="Dossier racine de la journée (…/YYYYMMDD)")
	ap.add_argument("--date", required=True, help="YYYYMMDD")
	ap.add_argument("--symbol", required=False, help="Symbole strict à garder (ex: ESZ25-CME ou NQZ25-CME)")
	ap.add_argument("--vwap_p95", type=float, required=False, help="Seuil p95 VWAP en % (defaut 0.10)")
	ap.add_argument("--vwap_p99", type=float, required=False, help="Seuil p99 VWAP en % (defaut 0.15)")
	ap.add_argument("--session_reset", type=float, required=False, help="Seuil reset session cum_delta (defaut 100.0)")
	args = ap.parse_args()
	global P95_THRESH, P99_THRESH, SESSION_RESET_THRESH
	if args.vwap_p95 is not None:
		P95_THRESH = float(args.vwap_p95)
	if args.vwap_p99 is not None:
		P99_THRESH = float(args.vwap_p99)
	if args.session_reset is not None:
		SESSION_RESET_THRESH = float(args.session_reset)
	return unify_chart3_day(Path(args.root), args.date, symbol=args.symbol)


if __name__ == "__main__":
	raise SystemExit(main())



