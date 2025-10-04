#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate G3 JSONL outputs (schema + coherence rules), similar to validate_g4_outputs.py but adapted to Chart 3.
Usage:
    python validate_g3_outputs.py --dir "D:\\MIA_IA_system" --csv "g3_validation_report.csv"
"""
import argparse
from pathlib import Path
import json
import csv
import re
from collections import defaultdict

# ---------- Helpers ----------
def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield ln, json.loads(line)
            except Exception as e:
                yield ln, {"__parse_error__": str(e), "__raw__": line}

def is_number(x):
    try:
        float(x)
        return True
    except Exception:
        return False

def monotonic_non_decreasing(seq):
    prev = None
    for x in seq:
        if prev is not None and x < prev:
            return False
        prev = x
    return True

def _num(rec, key, errs):
    if key not in rec:
        errs.append(f"missing:{key}")
        return None
    if not is_number(rec[key]):
        errs.append(f"not_number:{key}={rec[key]}")
        return None
    return float(rec[key])

# ---------- Validation rules per file ----------
def validate_basedata(rec):
    """
    Expected minimal keys:
      sym, t, i, o, h, l, c, v
    Optional:
      bidvol, askvol
    Checks:
      l <= o,c <= h and h >= l
      v >= 0
      if bidvol/askvol present: bidvol+askvol <= v (+ small epsilon)
    """
    errs = []
    for k in ["sym","t","i","o","h","l","c","v"]:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs

    t  = _num(rec, "t", errs)
    i  = _num(rec, "i", errs)
    o  = _num(rec, "o", errs)
    h  = _num(rec, "h", errs)
    l  = _num(rec, "l", errs)
    c  = _num(rec, "c", errs)
    v  = _num(rec, "v", errs)
    if any(x is None for x in [t,i,o,h,l,c,v]): 
        return errs

    if h < l:
        errs.append(f"ohlc_order_invalid:h({h})<l({l})")
    if not (l <= o <= h):
        errs.append(f"open_out_of_range:o={o},l={l},h={h}")
    if not (l <= c <= h):
        errs.append(f"close_out_of_range:c={c},l={l},h={h}")
    if v < 0:
        errs.append(f"neg_volume:v={v}")

    # Optional bid/ask volumes
    if "bidvol" in rec and "askvol" in rec and is_number(rec["bidvol"]) and is_number(rec["askvol"]) and is_number(rec["v"]):
        bidvol = float(rec["bidvol"]); askvol = float(rec["askvol"]); total = float(rec["v"])
        if total + 1e-9 < (bidvol + askvol):
            errs.append(f"v_lt_bidvol+askvol: v={total}, bid+ask={bidvol+askvol}")
    return errs

def validate_trade(rec):
    """
    Expected minimal keys:
      sym, t, i, price, qty
    Optional/variants:
      side in ['B','S','BUY','SELL']
      tt (trade type), seq (sequence id)
    Checks:
      qty > 0
    """
    errs = []
    for k in ["sym","t","i","price","qty"]:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs

    # numeric checks
    _ = _num(rec, "t", errs)
    _ = _num(rec, "i", errs)
    price = _num(rec, "price", errs)
    qty = _num(rec, "qty", errs)
    if qty is not None and qty <= 0:
        errs.append(f"non_positive_qty:{qty}")

    # side check if present
    if "side" in rec:
        side = str(rec["side"]).upper()
        if side not in ("B","S","BUY","SELL"):
            errs.append(f"invalid_side:{rec['side']}")
    return errs

def validate_quote(rec):
    """
    Expected minimal keys:
      sym, t, i, bid, ask
    Optional:
      bidsz, asksz
    Checks:
      bid <= ask
      sizes >= 0 if present
    """
    errs = []
    for k in ["sym","t","i","bid","ask"]:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs

    _ = _num(rec, "t", errs)
    _ = _num(rec, "i", errs)
    bid = _num(rec, "bid", errs)
    ask = _num(rec, "ask", errs)

    if bid is not None and ask is not None and bid > ask:
        errs.append(f"bid_gt_ask: bid={bid}, ask={ask}")

    for k in ("bidsz","asksz"):
        if k in rec:
            v = _num(rec, k, errs)
            if v is not None and v < 0:
                errs.append(f"neg_size:{k}={v}")
    return errs

def validate_depth(rec):
    """
    Expected minimal keys (flexible as dumps can vary):
      sym, t, i, lvl, bid, ask, bidsz, asksz
    We only check numeric presence if keys exist; lvl optional but recommended.
    """
    errs = []
    for k in ["sym","t","i"]:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs

    _ = _num(rec, "t", errs)
    _ = _num(rec, "i", errs)
    # optional numeric fields
    for k in ["lvl","bid","ask","bidsz","asksz"]:
        if k in rec and not is_number(rec[k]):
            errs.append(f"not_number:{k}={rec[k]}")
    # if both bid/ask present, basic sanity
    if "bid" in rec and "ask" in rec:
        try:
            bid = float(rec["bid"]); ask = float(rec["ask"])
            if bid > ask:
                errs.append(f"bid_gt_ask_depth: bid={bid}, ask={ask}")
        except Exception:
            pass
    return errs

def validate_trade_summary(rec):
    """
    Expected keys (best-effort; summaries can vary):
      sym, t, i, trades, buy_count, sell_count, buy_vol, sell_vol
    Only require (sym,t,i,trades). Others optional but checked if present.
    """
    errs = []
    for k in ["sym","t","i","trades"]:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs

    _ = _num(rec, "t", errs)
    _ = _num(rec, "i", errs)
    trades = _num(rec, "trades", errs)
    if trades is not None and trades < 0:
        errs.append(f"neg_trades:{trades}")

    for k in ["buy_count","sell_count","buy_vol","sell_vol"]:
        if k in rec:
            v = _num(rec, k, errs)
            if v is not None and v < 0:
                errs.append(f"neg_value:{k}={v}")
    return errs

def validate_vwap(rec):
    errs = []
    required = ["sym","t","i","vwap","sd1","sd2","sd3","sd4","sd5","sd6"]
    for k in required:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs
    for k in ["t","i","vwap","sd1","sd2","sd3","sd4","sd5","sd6"]:
        if not is_number(rec[k]):
            errs.append(f"not_number:{k}={rec[k]}")
    return errs

def validate_pvwap(rec):
    errs = []
    required = ["sym","t","i","pvwap","psd1","psd2"]
    for k in required:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs
    for k in ["t","i","pvwap","psd1","psd2"]:
        if not is_number(rec[k]):
            errs.append(f"not_number:{k}={rec[k]}")
    return errs

def validate_vva(rec):
    errs = []
    required = ["sym","t","i","poc","vah","val"]
    for k in required:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs
    for k in ["t","i","poc","vah","val"]:
        if not is_number(rec[k]):
            errs.append(f"not_number:{k}={rec[k]}")
    try:
        val = float(rec["val"]); poc = float(rec["poc"]); vah = float(rec["vah"])
        if not (val <= poc <= vah):
            errs.append(f"order_guard_failed: val={val},poc={poc},vah={vah}")
    except Exception:
        pass
    return errs

# VVA previous validation removed - fields no longer used

def validate_nbcv(rec):
    errs = []
    required = ["sym","t","i","delta","askvol","bidvol","trades","totalvol"]
    for k in required:
        if k not in rec:
            errs.append(f"missing:{k}")
    if errs: return errs
    for k in ["t","i","delta","askvol","bidvol","trades","totalvol"]:
        if not is_number(rec[k]):
            errs.append(f"not_number:{k}={rec[k]}")
    # sanity: totalvol >= askvol + bidvol ? (total may include others; warn if smaller)
    try:
        total = float(rec["totalvol"]); ask = float(rec["askvol"]); bid = float(rec["bidvol"])
        if total + 1e-9 < (ask + bid):
            errs.append(f"totalvol_lt_ask+bid: total={total}, ask+bid={ask+bid}")
    except Exception:
        pass
    return errs

def validate_cumdelta(rec):
    """
    Validateur pour Cumulative Delta - MODIFIÉ pour accepter nos valeurs calculées
    
    Problème identifié : Sierra Chart avec configuration Tick Reversal produit des valeurs
    incohérentes. Notre calculateur interne utilise les données NBCV pour corriger.
    
    Nouvelles valeurs acceptées :
    - cumulative_delta.close : Valeur cumulative depuis 00:00
    - cumulative_delta.delta : Delta instantané de cette minute
    """
    errs = []
    
    # Vérifier la structure cumulative_delta
    if "cumulative_delta" not in rec:
        errs.append("missing:cumulative_delta")
        return errs
    
    cum_delta = rec["cumulative_delta"]
    
    # Accepter les deux formats : ancien (direct) et nouveau (objet)
    if isinstance(cum_delta, dict):
        # Format nouveau : {"close": value, "delta": value}
        if "close" not in cum_delta:
            errs.append("missing:cumulative_delta.close")
        elif not is_number(cum_delta["close"]):
            errs.append(f"not_number:cumulative_delta.close={cum_delta['close']}")
        
        # Delta instantané optionnel
        if "delta" in cum_delta and not is_number(cum_delta["delta"]):
            errs.append(f"not_number:cumulative_delta.delta={cum_delta['delta']}")
            
    elif isinstance(cum_delta, (int, float)):
        # Format ancien : valeur directe
        if not is_number(cum_delta):
            errs.append(f"not_number:cumulative_delta={cum_delta}")
    else:
        errs.append(f"invalid_type:cumulative_delta={type(cum_delta)}")
    
    # Vérifier les champs requis
    required = ["sym","t","i"]
    for k in required:
        if k not in rec:
            errs.append(f"missing:{k}")
        elif k in ["t","i"] and not is_number(rec[k]):
            errs.append(f"not_number:{k}={rec[k]}")
    
    return errs

# Map filename pattern -> validator
PATTERNS = [
    # Core market data
    (re.compile(r"chart_3_basedata_\d{8}\.jsonl$"), "basedata", validate_basedata),
    (re.compile(r"chart_3_trade_\d{8}\.jsonl$"), "trade", validate_trade),
    (re.compile(r"chart_3_quote_\d{8}\.jsonl$"), "quote", validate_quote),
    (re.compile(r"chart_3_depth_\d{8}\.jsonl$"), "depth", validate_depth),
    (re.compile(r"chart_3_trade_summary_\d{8}\.jsonl$"), "trade_summary", validate_trade_summary),
    # Studies
    (re.compile(r"chart_3_vwap_\d{8}\.jsonl$"), "vwap", validate_vwap),
    (re.compile(r"chart_3_pvwap_\d{8}\.jsonl$"), "pvwap", validate_pvwap),
    (re.compile(r"chart_3_vva_\d{8}\.jsonl$"), "vva", validate_vva),
    (re.compile(r"chart_3_vva_previous_\d{8}\.jsonl$"), "vva_previous", validate_vva_previous),
    (re.compile(r"chart_3_nbcv_\d{8}\.jsonl$"), "nbcv", validate_nbcv),
    (re.compile(r"chart_3_cumulative_delta_\d{8}\.jsonl$"), "cumulative_delta", validate_cumdelta),
    # Optional extras (best-effort names)
    (re.compile(r"chart_3_atr_\d{8}\.jsonl$"), "atr", lambda r: [] if all(k in r for k in ("sym","t","i")) else ["missing:sym/t/i"]),
    (re.compile(r"chart_3_correlation_\d{8}\.jsonl$"), "correlation", lambda r: [] if all(k in r for k in ("sym","t","i")) else ["missing:sym/t/i"]),
]

def detect_kind(path):
    s = str(path.name).lower()
    for rx, kind, validator in PATTERNS:
        if rx.search(s):
            return kind, validator
    return None, None

def main():
    ap = argparse.ArgumentParser(description="Validate G3 JSONL outputs (schema + coherence rules).")
    ap.add_argument("--dir", default="D:\\\\MIA_IA_system", help="Folder where chart_3_*.jsonl files are written")
    ap.add_argument("--csv", default="g3_validation_report.csv", help="Path of CSV report to write")
    args = ap.parse_args()

    base = Path(args.dir)
    if not base.exists():
        print(f"[ERROR] Directory not found: {base}")
        return 2

    files = sorted([p for p in base.glob("chart_3_*.jsonl")])
    if not files:
        print(f"[WARN] No chart_3_*.jsonl files found in {base}")
        return 0

    rows = []
    summary = defaultdict(lambda: {"files": 0, "records": 0, "errors": 0, "dedup_collisions": 0, "non_monotonic_ts": 0})

    for p in files:
        kind, validator = detect_kind(p)
        if not validator:
            # unknown file: skip
            continue
        seen_keys = set()
        last_t = None
        cnt = 0
        err_cnt = 0
        non_monotonic = 0
        dedup_collisions = 0

        for ln, rec in read_jsonl(p):
            cnt += 1
            if "__parse_error__" in rec:
                rows.append({"file": p.name, "line": ln, "kind": kind, "error": f"json_parse_error: {rec['__parse_error__']}", "sample": rec.get("__raw__","")[:200]})
                err_cnt += 1
                continue

            # (sym,t,i) dedup check
            sym = rec.get("sym","?")
            t = rec.get("t", None)
            i = rec.get("i", None)
            key = (sym, t, i)
            if key in seen_keys:
                rows.append({"file": p.name, "line": ln, "kind": kind, "error": f"duplicate_key:(sym,t,i)={key}"})
                dedup_collisions += 1
            else:
                seen_keys.add(key)

            # monotonic timestamp check per file
            try:
                if last_t is not None and float(t) < float(last_t):
                    non_monotonic += 1
                last_t = t
            except Exception:
                pass

            # content validation
            errs = validator(rec)
            for e in errs:
                rows.append({"file": p.name, "line": ln, "kind": kind, "error": e})

        err_cnt = err_cnt + sum(1 for r in rows if r["file"] == p.name and r["kind"] == kind)
        summary[kind]["files"] += 1
        summary[kind]["records"] += cnt
        summary[kind]["errors"] += err_cnt
        summary[kind]["dedup_collisions"] += dedup_collisions
        summary[kind]["non_monotonic_ts"] += non_monotonic

    # Write CSV
    out_csv = Path(args.csv)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file","line","kind","error","sample"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Print a concise summary
    print("=== G3 VALIDATION SUMMARY ===")
    for kind, stats in summary.items():
        print(f"- {kind:16s} | files={stats['files']:3d} | records={stats['records']:7d} | errors={stats['errors']:6d} | dup_keys={stats['dedup_collisions']:5d} | non_monotonic_ts={stats['non_monotonic_ts']:5d}")
    print(f"\nDetailed errors saved to: {out_csv.resolve()}")

if __name__ == "__main__":
    raise SystemExit(main())
