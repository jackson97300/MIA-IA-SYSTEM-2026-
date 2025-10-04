# -*- coding: utf-8 -*-
"""
data_quality_scanner.py
Scanner qualité pour datasets Sierra Chart + MentorQ
- Couvre CHART_3 (ES) et CHART_9 (NQ)
- Gère gros fichiers .jsonl (quote/depth) via lecture streaming
- Vérifications:
  1) Gaps temporels
  2) Outliers (basedata, VIX, MentorQ)
  3) Anomalies MentorQ (gamma/blind)
  4) Synchronisation inter-charts (3 vs 9)
  5) Cohérence VWAP ↔ Prix (seuil adaptatif)
  6) Cohérence L1 Quote ↔ Depth (best bid/ask)
  7) Spread sanity (ratio de ticks avec spread > 2 ticks)
- Rapport: data_quality_scan_report_YYYYMMDD.json

Usage:
  python data_quality_scanner.py --data "D:\\MIA_IA_system" --date 20250923
"""

import json
import math
import sys
import time
import csv
from glob import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Iterable, List

import pandas as pd
import numpy as np

# Quality modules (recalc & gates)
try:
    from quality.computations import compute_vwap_from_trades, compute_cum_delta_from_trades, SessionRules
    from quality.validators import summarize_vwap_deviation_percent, check_vwap_thresholds, Thresholds
except Exception:
    # Modules optionnels; le scanner principal JSONL reste utilisable sans eux
    compute_vwap_from_trades = None
    compute_cum_delta_from_trades = None
    SessionRules = None
    summarize_vwap_deviation_percent = None
    check_vwap_thresholds = None
    Thresholds = None


def _safe_float(x, default=np.nan):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x, default=0):
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


class DataQualityScanner:
    def __init__(self, data_path: str=".", ymd: str=None):
        self.data_path = Path(data_path)
        self.ymd = ymd or datetime.utcnow().strftime("%Y%m%d")
        self.results: Dict[str, Any] = {
            "gaps": {},
            "outliers": {},
            "menthorq_anomalies": {},
            "synchronization_issues": {},
            "data_consistency": {},
            "summary": {}
        }
        # fichiers attendus par chart
        self.expected = {
            3: [f"chart_3_basedata_{self.ymd}.jsonl", f"chart_3_quote_{self.ymd}.jsonl",
                f"chart_3_trade_{self.ymd}.jsonl", f"chart_3_depth_{self.ymd}.jsonl",
                f"chart_3_vwap_{self.ymd}.jsonl", f"chart_3_vva_{self.ymd}.jsonl",
                f"chart_3_pvwap_{self.ymd}.jsonl", f"chart_3_cumulative_delta_{self.ymd}.jsonl",
                f"chart_3_vix_{self.ymd}.jsonl", f"chart_3_menthorq_gamma_{self.ymd}.jsonl",
                f"chart_3_menthorq_blind_spots_{self.ymd}.jsonl"],
            9: [f"chart_9_basedata_{self.ymd}.jsonl", f"chart_9_quote_{self.ymd}.jsonl",
                f"chart_9_trade_{self.ymd}.jsonl", f"chart_9_depth_{self.ymd}.jsonl",
                f"chart_9_vwap_{self.ymd}.jsonl", f"chart_9_vva_{self.ymd}.jsonl",
                f"chart_9_pvwap_{self.ymd}.jsonl", f"chart_9_cumulative_delta_{self.ymd}.jsonl",
                f"chart_9_vix_{self.ymd}.jsonl", f"chart_9_menthorq_gamma_{self.ymd}.jsonl",
                f"chart_9_menthorq_blind_spots_{self.ymd}.jsonl"]
        }

    # ------------------------ PUBLIC API ------------------------

    def scan_all_data(self):
        print(f"== DATA QUALITY SCAN {self.ymd} ==")
        self._check_presence()
        self.scan_temporal_gaps()
        self.scan_outliers()
        self.scan_menthorq_anomalies()
        self.scan_synchronization_issues()
        self.scan_consistency()
        self._summarize()

    def save_report(self, output_file: str=None):
        output_file = output_file or f"data_quality_scan_report_{self.ymd}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Rapport sauvegardé → {output_file}")

    # ------------------------ PRESENCE ------------------------

    def _check_presence(self):
        print("\n📦 0. PRÉSENCE DES FICHIERS")
        missing = {}
        for chart_id, files in self.expected.items():
            miss = []
            for file in files:
                if not (self.data_path / file).exists():
                    miss.append(file)
                    print(f"  ⚠️  Manquant (chart {chart_id}): {file}")
            if miss:
                missing[f"chart_{chart_id}"] = miss
        self.results["summary"]["missing_files"] = missing

    # ------------------------ GAPS ------------------------

    def scan_temporal_gaps(self):
        print("\n📊 1. ANALYSE DES GAPS TEMPORELS")
        for chart_id, files in self.expected.items():
            print(f"\n  📈 CHART {chart_id}:")
            chart_gaps = {}
            for file in files:
                fp = self.data_path / file
                if not fp.exists():
                    continue
                gaps = self._analyze_file_gaps(fp, chart_id)
                if gaps and gaps.get("total_gaps", 0) > 0:
                    chart_gaps[file] = gaps
                    print(f"    📄 {file}: {gaps['total_gaps']} gaps (max {gaps['max_gap_seconds']:.2f}s)")
            self.results["gaps"][f"chart_{chart_id}"] = chart_gaps

    def _analyze_file_gaps(self, fp: Path, chart_id: int) -> Optional[Dict[str, Any]]:
        last_t = None
        total_gaps = 0
        max_gap = 0.0
        line_count = 0
        try:
            with open(fp, "r") as f:
                for ln in f:
                    try:
                        rec = json.loads(ln)
                    except Exception:
                        continue
                    t = _safe_float(rec.get("t"))
                    if math.isnan(t):
                        continue
                    if last_t is not None:
                        gap = t - last_t
                        if gap > 1.5:  # considérer >1.5 sec comme gap
                            total_gaps += 1
                            max_gap = max(max_gap, gap)
                    last_t = t
                    line_count += 1
        except Exception as e:
            return {"error": str(e)}
        return {"total_gaps": total_gaps, "max_gap_seconds": max_gap, "lines": line_count}

    # ------------------------ OUTLIERS ------------------------

    def scan_outliers(self):
        print("\n🔍 2. OUTLIERS & VALEURS ABERRANTES")
        for chart_id in (3, 9):
            self._scan_basedata_outliers(chart_id)
            self._scan_vix_outliers(chart_id)
            self._scan_menthorq_outliers(chart_id)

    def _scan_basedata_outliers(self, chart_id: int):
        fp = self.data_path / f"chart_{chart_id}_basedata_{self.ymd}.jsonl"
        if not fp.exists():
            return
        prices, vols = [], []
        with open(fp, "r") as f:
            for ln in f:
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                if r.get("type") not in ("basedata", None):
                    continue
                c = _safe_float(r.get("c"))
                v = _safe_float(r.get("v"))
                if not math.isnan(c):
                    prices.append(c)
                if not math.isnan(v):
                    vols.append(v)
        if not prices:
            return
        pr = pd.Series(prices)
        q1, q3 = pr.quantile(0.25), pr.quantile(0.75)
        iqr = max(1e-9, q3 - q1)
        low, high = q1 - 3 * iqr, q3 + 3 * iqr
        outliers = int(((pr < low) | (pr > high)).sum())
        self.results["outliers"].setdefault(f"chart_{chart_id}", {})["basedata_price"] = {
            "count": len(prices),
            "outliers": outliers,
            "low": float(low),
            "high": float(high)
        }
        if vols:
            vs = pd.Series(vols)
            vq1, vq3 = vs.quantile(0.25), vs.quantile(0.75)
            viqr = max(1e-9, vq3 - vq1)
            vlow, vhigh = vq1 - 3 * viqr, vq3 + 3 * viqr
            v_out = int(((vs < vlow) | (vs > vhigh)).sum())
            self.results["outliers"][f"chart_{chart_id}"]["basedata_volume"] = {
                "count": len(vols),
                "outliers": v_out,
                "low": float(vlow),
                "high": float(vhigh)
            }

    def _scan_vix_outliers(self, chart_id: int):
        fp = self.data_path / f"chart_{chart_id}_vix_{self.ymd}.jsonl"
        if not fp.exists():
            return
        vals = []
        with open(fp, "r") as f:
            for ln in f:
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                v = _safe_float(r.get("v"))
                if not math.isnan(v):
                    vals.append(v)
        if not vals:
            return
        v = pd.Series(vals)
        bad = int(((v < 5) | (v > 150)).sum())
        self.results["outliers"].setdefault(f"chart_{chart_id}", {})["vix"] = {
            "count": len(vals),
            "out_of_range": bad,
            "min": float(v.min()),
            "max": float(v.max())
        }

    def _scan_menthorq_outliers(self, chart_id: int):
        # gamme raisonnable de prix (approx) pour sanity check
        # ES ~ [3000..7000], NQ ~ [9000..22000] — ajustables
        fp = self.data_path / f"chart_{chart_id}_menthorq_gamma_{self.ymd}.jsonl"
        if not fp.exists():
            return
        prices = []
        with open(fp, "r") as f:
            for ln in f:
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                p = _safe_float(r.get("level_price"))
                if not math.isnan(p):
                    prices.append(p)
        if not prices:
            return
        lo, hi = (3000, 7000) if chart_id == 3 else (9000, 22000)
        bad = int(((pd.Series(prices) < lo) | (pd.Series(prices) > hi)).sum())
        self.results["outliers"].setdefault(f"chart_{chart_id}", {})["menthorq_gamma_price_range"] = {
            "count": len(prices),
            "out_of_range": bad,
            "low": lo,
            "high": hi
        }

    # ------------------------ ANOMALIES MENTORQ ------------------------

    def scan_menthorq_anomalies(self):
        print("\n🧩 3. ANOMALIES MentorQ")
        anomalies = {}
        for chart_id in (3, 9):
            for kind in ("menthorq_gamma", "menthorq_blind_spots"):
                fp = self.data_path / f"chart_{chart_id}_{kind}_{self.ymd}.jsonl"
                if not fp.exists():
                    continue
                rows = []
                with open(fp, "r") as f:
                    for ln in f:
                        try:
                            rows.append(json.loads(ln))
                        except Exception:
                            continue
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                miss = {col: {"count": int(df[col].isna().sum()),
                              "percentage": float(df[col].isna().mean() * 100.0)}
                        for col in df.columns}
                anomalies[f"chart_{chart_id}_{kind}"] = {
                    "missing": miss, "count": int(len(df))
                }
        self.results["menthorq_anomalies"] = anomalies

    # ------------------------ SYNCHRO 3 vs 9 ------------------------

    def scan_synchronization_issues(self):
        print("\n⏱️ 4. SYNCHRONISATION ES (3) vs NQ (9)")
        def first_last_ts(fp: Path):
            mn = mx = None
            n = 0
            if not fp.exists():
                return None
            with open(fp, "r") as f:
                for ln in f:
                    try:
                        rec = json.loads(ln)
                    except Exception:
                        continue
                    t = _safe_float(rec.get("t"))
                    if math.isnan(t):
                        continue
                    n += 1
                    mn = t if mn is None else min(mn, t)
                    mx = t if mx is None else max(mx, t)
            if n == 0:
                return None
            return {"min_ts": mn, "max_ts": mx, "count": n}

        charts = {}
        for chart_id in (3, 9):
            fp = self.data_path / f"chart_{chart_id}_basedata_{self.ymd}.jsonl"
            r = first_last_ts(fp)
            if r:
                charts[chart_id] = r

        sync = {}
        if 3 in charts and 9 in charts:
            sync["chart_9_vs_chart_3"] = {
                "start_offset_seconds": charts[9]["min_ts"] - charts[3]["min_ts"],
                "end_offset_seconds": charts[9]["max_ts"] - charts[3]["max_ts"],
                "counts": {"c3": charts[3]["count"], "c9": charts[9]["count"]}
            }
        self.results["synchronization_issues"] = sync

    # ------------------------ CONSISTENCY ------------------------

    def scan_consistency(self):
        print("\n🧪 5. TESTS DE COHÉRENCE")
        issues: Dict[str, Any] = {}
        self._check_vwap_price_consistency(issues)
        self._check_l1_quote_vs_depth_consistency(issues)
        self._check_spread_sanity(issues)
        self.results["data_consistency"] = issues

    def _check_vwap_price_consistency(self, issues: Dict[str, Any]):
        for chart_id in (3, 9):
            vwap_fp = self.data_path / f"chart_{chart_id}_vwap_{self.ymd}.jsonl"
            base_fp = self.data_path / f"chart_{chart_id}_basedata_{self.ymd}.jsonl"
            if not vwap_fp.exists() or not base_fp.exists():
                continue
            vwap_rows, base_rows = [], []
            with open(vwap_fp, "r") as f:
                for ln in f:
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    # compatible avec formats possibles
                    if r.get('type') in ('vwap', None) and ('v' in r or 'vwap' in r):
                        vwap_rows.append({"i": r.get("i"), "t": r.get("t"), "v": r.get("v", r.get("vwap"))})
            with open(base_fp, "r") as f:
                for ln in f:
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    if r.get('type') in ('basedata', None) and ('c' in r or 'close' in r):
                        base_rows.append({"i": r.get("i"), "t": r.get("t"), "c": r.get("c", r.get("close"))})
            if not vwap_rows or not base_rows:
                continue
            vwap_df = pd.DataFrame(vwap_rows).dropna(subset=["i","v"])
            base_df = pd.DataFrame(base_rows).dropna(subset=["i","c"])
            merged = pd.merge(vwap_df, base_df, on="i", how="inner", suffixes=("_vw","_px"))
            if len(merged) == 0:
                continue
            merged["v"] = pd.to_numeric(merged["v"], errors="coerce")
            merged["c"] = pd.to_numeric(merged["c"], errors="coerce")
            merged = merged.dropna(subset=["v","c"])
            if len(merged) == 0:
                continue
            v = (merged["v"] - merged["c"]).abs()
            px = merged["c"].replace(0, np.nan)
            std = merged["c"].std()
            mean = merged["c"].mean()
            thr = min(0.05, (3 * std / max(mean, 1e-9)))  # seuil adaptatif
            ratio = (v / px)
            outliers = int((ratio > thr).sum())
            issues[f"vwap_price_chart_{chart_id}"] = {
                "outliers": outliers,
                "total_records": int(len(merged)),
                "outlier_rate_pct": float(outliers / len(merged) * 100.0),
                "max_deviation_pct": float(ratio.max() * 100.0),
                "threshold_pct": float(thr * 100.0)
            }

    # ---- NEW: L1 Quote vs Depth consistency ----

    def _check_l1_quote_vs_depth_consistency(self, issues: Dict[str, Any], sample_target:int=200_000):
        """
        Compare best bid/ask du fichier quote vs depth.
        On échantillonne pour éviter RAM/CPU excessifs.
        Résultat: proportion de mismatches > 1 tick.
        """
        for chart_id in (3, 9):
            quote_fp = self.data_path / f"chart_{chart_id}_quote_{self.ymd}.jsonl"
            depth_fp = self.data_path / f"chart_{chart_id}_depth_{self.ymd}.jsonl"
            if not quote_fp.exists() or not depth_fp.exists():
                continue

            # 1) Sample Quotes: (t, bid, ask)
            q_sample = []
            step = max(1, self._estimate_step(quote_fp, target=sample_target))
            with open(quote_fp, "r") as f:
                for idx, ln in enumerate(f):
                    if idx % step != 0:
                        continue
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    t = _safe_float(r.get("t"))
                    b = _safe_float(r.get("b", r.get("bid")))
                    a = _safe_float(r.get("a", r.get("ask")))
                    if not (math.isnan(t) or math.isnan(b) or math.isnan(a)):
                        q_sample.append((t, b, a))
            if not q_sample:
                continue
            q_df = pd.DataFrame(q_sample, columns=["t", "qb", "qa"])

            # 2) Sample Depth: (t, best_bid, best_ask)
            d_sample = []
            step_d = max(1, self._estimate_step(depth_fp, target=sample_target))
            with open(depth_fp, "r") as f:
                for idx, ln in enumerate(f):
                    if idx % step_d != 0:
                        continue
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    t = _safe_float(r.get("t"))
                    # tentatives multi-clés
                    bb = _safe_float(r.get("bb", r.get("best_bid", r.get("bid"))))
                    ba = _safe_float(r.get("ba", r.get("best_ask", r.get("ask"))))
                    # sinon, si snapshot: listes d'orders → on prend max bids / min asks
                    if math.isnan(bb) or math.isnan(ba):
                        bids = r.get("bids") or r.get("B")
                        asks = r.get("asks") or r.get("A")
                        if isinstance(bids, list) and bids:
                            try:
                                bb = max(_safe_float(x[0]) for x in bids if isinstance(x, (list, tuple)) and len(x) >= 1)
                            except Exception:
                                pass
                        if isinstance(asks, list) and asks:
                            try:
                                ba = min(_safe_float(x[0]) for x in asks if isinstance(x, (list, tuple)) and len(x) >= 1)
                            except Exception:
                                pass
                    if not (math.isnan(t) or math.isnan(bb) or math.isnan(ba)):
                        d_sample.append((t, bb, ba))
            if not d_sample:
                continue
            d_df = pd.DataFrame(d_sample, columns=["t", "db", "da"])

            # 3) Join by nearest time (tolerance)
            # On fait un merge approximatif via arrondi millisecondes → secondes
            q_df["ts"] = (q_df["t"]).round().astype(np.int64)
            d_df["ts"] = (d_df["t"]).round().astype(np.int64)
            merged = pd.merge_asof(q_df.sort_values("ts"), d_df.sort_values("ts"), on="ts", direction="nearest", tolerance=1)

            merged = merged.dropna(subset=["qb","qa","db","da"])
            if len(merged) == 0:
                continue

            # 4) Tick size (0.25)
            tick = 0.25
            bid_diff_ticks = ((merged["qb"] - merged["db"]).abs() / tick).round()
            ask_diff_ticks = ((merged["qa"] - merged["da"]).abs() / tick).round()
            # mismatch si > 1 tick
            mism = ((bid_diff_ticks > 1) | (ask_diff_ticks > 1)).astype(int)
            mismatch_rate = float(mism.mean() * 100.0)

            issues[f"l1_quote_vs_depth_chart_{chart_id}"] = {
                "compared_points": int(len(merged)),
                "mismatch_rate_pct": mismatch_rate,
                "bid_diff_ticks_max": float(bid_diff_ticks.max()),
                "ask_diff_ticks_max": float(ask_diff_ticks.max())
            }

    def _estimate_step(self, fp: Path, target: int=200_000) -> int:
        """Estime un pas d'échantillonnage pour limiter le nombre de lignes lues."""
        try:
            # estimation naïve via taille fichier (bytes) / taille moyenne d'une ligne
            size = fp.stat().st_size
            # supposer ~80 bytes/ligne en moyenne (très grossier)
            est_lines = max(1, size // 80)
            step = max(1, int(est_lines // target))
            return step
        except Exception:
            return 1

    # ---- NEW: Spread sanity ----

    def _check_spread_sanity(self, issues: Dict[str, Any], spread_warn_ticks:int=2):
        """
        Mesure la proportion de quotes avec un spread > spread_warn_ticks (par défaut 2 ticks).
        """
        tick = 0.25
        for chart_id in (3, 9):
            quote_fp = self.data_path / f"chart_{chart_id}_quote_{self.ymd}.jsonl"
            if not quote_fp.exists():
                continue
            total = 0
            bad = 0
            max_spread_ticks = 0.0
            step = max(1, self._estimate_step(quote_fp, target=400_000))
            with open(quote_fp, "r") as f:
                for idx, ln in enumerate(f):
                    if idx % step != 0:
                        continue
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    b = _safe_float(r.get("b", r.get("bid")))
                    a = _safe_float(r.get("a", r.get("ask")))
                    if math.isnan(b) or math.isnan(a) or a <= 0 or b <= 0:
                        continue
                    sp = (a - b) / tick
                    total += 1
                    max_spread_ticks = max(max_spread_ticks, sp)
                    if sp > spread_warn_ticks:
                        bad += 1
            rate = float(bad / total * 100.0) if total > 0 else 0.0
            issues[f"spread_sanity_chart_{chart_id}"] = {
                "checked_quotes": int(total),
                "over_{0}_ticks_pct".format(spread_warn_ticks): rate,
                "max_spread_ticks": float(max_spread_ticks)
            }

    # ------------------------ SUMMARY ------------------------

    def _summarize(self):
        # Récapitulatif court pour lecture humaine rapide
        summ = {}
        for k in ("gaps", "outliers", "menthorq_anomalies", "synchronization_issues", "data_consistency"):
            summ[k] = list(self.results.get(k, {}).keys())
        self.results["summary"]["sections"] = summ


# ------------------------ CLI ------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".", help="Chemin des fichiers .jsonl")
    ap.add_argument("--date", default=None, help="YYYYMMDD (défaut: aujourd'hui UTC)")
    # Mode CSV simplifié (recalc VWAP/CumDelta)
    ap.add_argument("--csv", default=None, help="CSV Sierra (minute ou tick) pour calculs VWAP/CumDelta")
    ap.add_argument("--sym", default="ES", choices=["ES", "NQ"], help="Symbole pour règles de session")
    ap.add_argument("--export", default=None, help="Chemin CSV de sortie avec colonnes ajoutées (VWAP,CumDelta)")
    args = ap.parse_args()

    # Mode CSV: recalculs rapides (sans impacter le mode JSONL historique)
    if args.csv:
        return run_csv_mode(args.csv, args.sym)

    # Mode JSONL (historique)
    scanner = DataQualityScanner(data_path=args.data, ymd=args.date)
    scanner.scan_all_data()
    scanner.save_report()
    return 0


def _read_sierra_csv(path: str) -> List[Dict[str, Any]]:
    """Lit un CSV Sierra (minute ou tick).
    Colonnes acceptées: Date, Time, Open, High, Low, Last, Volume, NumberOfTrades, BidVolume, AskVolume.
    Retour: liste ordonnée de dicts {t,p,q,bidv,askv,trades}.
    """
    rows: List[Dict[str, Any]] = []
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for i, d in enumerate(r, start=1):
            try:
                price = float(d.get("Last"))
                vol = float(d.get("Volume"))
            except Exception:
                continue
            bidv = d.get("BidVolume"); askv = d.get("AskVolume"); trades = d.get("NumberOfTrades")
            try:
                bidv_f = float(bidv) if bidv not in (None, "") else 0.0
            except Exception:
                bidv_f = 0.0
            try:
                askv_f = float(askv) if askv not in (None, "") else 0.0
            except Exception:
                askv_f = 0.0
            try:
                trades_i = int(trades) if trades not in (None, "") else 0
            except Exception:
                trades_i = 0
            if not (vol is not None and vol >= 0 and not math.isnan(price)):
                continue
            rows.append({"t": float(i), "p": price, "q": vol, "bidv": bidv_f, "askv": askv_f, "trades": trades_i})
    return rows


def run_csv_mode(csv_path: str, symbol: str, export_path: Optional[str] = None) -> int:
    if compute_vwap_from_trades is None:
        print("⚠️ Modules quality indisponibles: impossible de recalculer VWAP/CumDelta dans ce mode.")
        return 2
    ticks = _read_sierra_csv(csv_path)
    if not ticks:
        print("❌ Aucune donnée lue depuis:", csv_path)
        return 1

    # Règles de session RTH en UTC (adapter si timestamps non-UTC côté exports)
    rules = SessionRules(rth_start_utc="13:30", rth_end_utc="20:00", reset_on_session_change=True)
    vwap_series = compute_vwap_from_trades(ticks, rules=rules)
    cum_delta_series = compute_cum_delta_from_trades(ticks)

    vols = [tr["q"] for tr in ticks]
    neg_vols = [q for q in vols if q < 0]
    non_int = [q for q in vols if abs(q - round(q)) > 1e-9]
    # Somme Bid/Ask vs Volume si dispo
    has_bidask = any((tr.get("bidv", 0) or tr.get("askv", 0)) for tr in ticks)
    bad_bidask = 0
    if has_bidask:
        for tr in ticks:
            bidv = float(tr.get("bidv", 0.0) or 0.0)
            askv = float(tr.get("askv", 0.0) or 0.0)
            if abs((bidv + askv) - tr["q"]) > 1e-9:
                bad_bidask += 1
    # NumberOfTrades contrôle simple
    has_trades = any(tr.get("trades", 0) for tr in ticks)
    bad_trades = 0
    if has_trades:
        for tr in ticks:
            if tr["trades"] < 0:
                bad_trades += 1

    last_vwap = vwap_series[-1]['vwap'] if vwap_series else float('nan')
    last_cd = cum_delta_series[-1]['cum_delta'] if cum_delta_series else float('nan')

    print(f"✅ Fichier: {csv_path}")
    print(f"→ Lignes: {len(ticks)} | Volume total: {int(sum(vols))}")
    print(f"→ Volumes négatifs: {len(neg_vols)} | Volumes non-entiers: {len(non_int)}")
    if has_bidask:
        print(f"→ Lignes Bid+Ask≠Volume: {bad_bidask}")
    if has_trades:
        print(f"→ Lignes NumberOfTrades négatif: {bad_trades}")
    print(f"→ VWAP (dernier): {last_vwap:.4f} | CumDelta (dernier): {last_cd:.0f}")

    # Export enrichi si demandé
    if export_path:
        try:
            # Relire brut pour conserver colonnes d'origine, puis ajouter VWAP/CumDelta
            with open(csv_path, newline='', encoding='utf-8') as f_in, open(export_path, 'w', newline='', encoding='utf-8') as f_out:
                r = csv.DictReader(f_in)
                fieldnames = list(r.fieldnames or [])
                for extra in ("VWAP", "CumDelta"):
                    if extra not in fieldnames:
                        fieldnames.append(extra)
                w = csv.DictWriter(f_out, fieldnames=fieldnames)
                w.writeheader()
                idx = 0
                for row in r:
                    if idx < len(vwap_series):
                        row["VWAP"] = f"{vwap_series[idx]['vwap']:.6f}"
                    if idx < len(cum_delta_series):
                        row["CumDelta"] = f"{cum_delta_series[idx]['cum_delta']:.0f}"
                    w.writerow(row)
                    idx += 1
            print(f"✅ Export enrichi écrit → {export_path}")
        except Exception as e:
            print(f"⚠️ Échec export enrichi: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
