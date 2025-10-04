# build_dataset_multisrc.py
# -*- coding: utf-8 -*-
"""
Assembler un dataset multi-sources (ATR, VIX, VWAP, PVWAP, NBCV, MenthorQ, VVA, DOM, etc.)
- Lecture récursive des JSONL (gère "ts" et fallback "t")
- Tag "source" depuis le nom de fichier
- Merge asof par symbole (tolérance 1s) sur une base temporelle unifiée
- Recalcule NBCV pressure si manquante (normalisée + EMA par symbole)
- Masques avail_* et export Parquet
"""

import os, re, glob, sys, warnings
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# === CONFIG UTILISATEUR =======================================================
BASE_DIR = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\OCTOBRE"
YMD_LIST = ["20251002"]  # Temporairement seulement le 2 octobre
OUT_DIR  = r"D:\MIA_IA_system\DATASET"
OUT_FILE = "dataset_20251002_only.parquet"

ASOF_TOL = pd.Timedelta("1000ms")  # tolérance de join
H = 5  # horizon pour labels (si tu veux garder la logique de ton ancien builder)

# blocs pour masques de dispo (ajoute/retire librement)
BLOCKS = {
    "nbcv": ["ask_volume","bid_volume","delta","trades","cumulative_delta","total_volume",
             "delta_ratio","ask_percent","bid_percent",
             "bid_ask_ratio","ask_bid_ratio","pressure_bullish","pressure_bearish","pressure","pressure_smooth"],
    "dom":  ["quote_bid","quote_ask","has_l1","match_L1","valid","tol_ms","dt_ms_to_l1","l1_source",
             "l1_bbo_ratio","depth_imbalance","price","size"],
    "vwap": ["v","up1","dn1","up2","dn2","up3","dn3"],
    "pvwap":["prev_start","prev_end","pvwap","pv_up1","pv_dn1","pv_up2","pv_dn2"],
    "vva":  ["vah","val","vpoc","pvah","pval","ppoc","id_curr","id_prev"],
    "gamma":["gex_1","gex_2","gex_3","gex_4","gex_5","gex_6","gex_7","gex_8","gex_9","gex_10",
             "hvl","1d_max","1d_min","call_resistance","put_support","call_resistance_0dte",
             "put_support_0dte","hvl_0dte","gamma_wall_0dte"],
    "blind":[f"blind_spot_{i}" for i in range(9)],
    "ohlc": ["o","h","l","c"],
    "vol":  ["v","bidvol","askvol"],
    "delta_cum": ["cum_delta_day","cum_delta_session","session_id"],
    "vola": ["vix","atr"],
    "corr": ["cc"],
}

SLOW_COLS_HINT = set(BLOCKS["gamma"] + BLOCKS["blind"] + BLOCKS["vva"] + BLOCKS["pvwap"])

# === DÉTECTION SOURCE =========================================================
PATTERNS = [
    ("nbcv", r"nbcv"),
    ("mentorq", r"(menthorq|mentorq|gamma)"),
    ("blind", r"blind"),
    ("vva", r"vva|volume_profile"),
    ("pvwap", r"pvwap|prev.*vwap"),
    ("vwap", r"\bvwap\b|study_vwap"),
    ("dom", r"depth|orderbook|dom"),
    ("quote", r"quote|l1"),
    ("trade", r"trade_summary|trade"),
    ("atr", r"\batr\b"),
    ("vix", r"\bvix\b"),
    ("corr", r"correl|correlation|cc"),
    ("basedata", r"basedata|ohlc|bars"),
]
def guess_source(path: str) -> str:
    name = os.path.basename(path).lower()
    for key, pat in PATTERNS:
        if re.search(pat, name):
            return key
    return "misc"

# === LECTURE & NORMALISATION ==================================================
def find_jsonl_files(base_dir: str, ymd_list: List[str]) -> List[str]:
    files = []
    for ymd in ymd_list:
        files.extend(glob.glob(os.path.join(base_dir, "**", f"*{ymd}*.jsonl"), recursive=True))
    files = [f for f in files if f.lower().endswith(".jsonl")]
    return sorted(set(files))

def parse_ts(df: pd.DataFrame) -> pd.DataFrame:
    if "ts" in df.columns:
        ts = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    elif "t" in df.columns:
        # Les timestamps semblent être en nanosecondes depuis epoch
        try:
            # Essayer directement en nanosecondes
            ts = pd.to_datetime(df["t"], unit="ns", errors="coerce", utc=True)
            # Vérifier si les timestamps sont raisonnables (après 2020)
            if ts.dt.year.min() < 2020:
                # Essayer en millisecondes
                ts = pd.to_datetime(df["t"], unit="ms", errors="coerce", utc=True)
                if ts.dt.year.min() < 2020:
                    # Essayer en secondes
                    ts = pd.to_datetime(df["t"], unit="s", errors="coerce", utc=True)
        except Exception:
            ts = pd.to_datetime(df["t"], errors="coerce", utc=True)
    else:
        return pd.DataFrame(columns=["sym","ts"])
    df = df.copy()
    df["ts"] = ts.dt.tz_convert(None)
    return df

def read_by_source(files: List[str]) -> Dict[str, pd.DataFrame]:
    buckets: Dict[str, List[pd.DataFrame]] = {}
    for f in files:
        try:
            df = pd.read_json(f, lines=True, dtype=False)
            df = parse_ts(df)
            if df.empty: 
                continue
            if "sym" not in df.columns and "symbol" in df.columns:
                df = df.rename(columns={"symbol":"sym"})
            if "sym" not in df.columns:
                continue
            df["__source__"] = guess_source(f)
            buckets.setdefault(df["__source__"].iloc[0], []).append(df)
        except Exception as e:
            print(f"[WARN] lecture échouée {os.path.basename(f)}: {e}")
    out = {}
    for src, parts in buckets.items():
        tmp = pd.concat(parts, ignore_index=True, sort=False)
        tmp = tmp.dropna(subset=["ts"]).sort_values(["sym","ts"]).reset_index(drop=True)
        out[src] = tmp
    return out

# === ASSEMBLEUR MULTI-SOURCES ================================================
def unify_timeline(frames_by_src: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    # union des (sym, ts) de toutes sources
    bases = []
    for src, df in frames_by_src.items():
        print(f"   Debug {src}: cols={list(df.columns)[:5]}..., has_sym={'sym' in df.columns}, has_ts={'ts' in df.columns}, empty={df.empty}")
        if "sym" in df.columns and "ts" in df.columns and not df.empty:
            bases.append(df[["sym","ts"]])
        else:
            print(f"   [WARN] Source {src} ignorée (pas de sym/ts ou vide)")
    
    if not bases:
        print("   [ERREUR] Aucune source valide avec sym/ts")
        return pd.DataFrame(columns=["sym","ts"])
    
    base = pd.concat(bases, ignore_index=True).drop_duplicates().sort_values(["sym","ts"]).reset_index(drop=True)
    return base

def asof_merge_all(base: pd.DataFrame, frames_by_src: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    if base.empty:
        print("   [ERREUR] Base timeline vide")
        return pd.DataFrame()
    
    out = base.copy()
    for src, df in frames_by_src.items():
        if "sym" not in df.columns or "ts" not in df.columns or df.empty:
            print(f"   [WARN] Source {src} ignorée pour merge (pas de sym/ts ou vide)")
            continue
            
        cols = [c for c in df.columns if c not in ("__source__",)]
        df2 = df[["sym","ts"] + [c for c in cols if c not in ("sym","ts")]].sort_values(["sym","ts"])
        
        # merge par sous-groupes (asof ne supporte pas by= sur multi-join successifs de façon fiable → on boucle par sym)
        merged = []
        for sym, g in out.groupby("sym", sort=False):
            left = g.sort_values("ts")
            right = df2[df2["sym"] == sym].sort_values("ts")
            if right.empty:
                merged.append(left)
                continue
            m = pd.merge_asof(left, right, on="ts", direction="nearest", tolerance=ASOF_TOL)
            merged.append(m)
        
        if merged:
            out = pd.concat(merged, ignore_index=True, sort=False).sort_values(["sym","ts"]).reset_index(drop=True)
    
    return out

# === NBCV : pression pro-safe (si manquante) =================================
def _safediv(a, b, default=0.0):
    try:
        return a / b if (b and np.isfinite(b)) else default
    except Exception:
        return default

def compute_pressure_cols(df: pd.DataFrame, alpha=0.30, w_delta=0.7, w_imb=0.3, k_delta=0.02, k_imb=0.10):
    need = {"delta","total_volume","ask_volume","bid_volume"}
    if not need.issubset(df.columns): 
        return df
    df = df.copy()
    df["delta_norm"] = df.apply(lambda r: _safediv(float(r.get("delta",np.nan)), float(r.get("total_volume",np.nan)), 0.0), axis=1)
    df["imbalance"]  = df.apply(lambda r: _safediv(float(r.get("bid_volume",np.nan))-float(r.get("ask_volume",np.nan)),
                                                  float(r.get("total_volume",np.nan)), 0.0), axis=1)
    df["delta_term"] = np.tanh(df["delta_norm"] / k_delta)
    df["imb_term"]   = np.tanh(df["imbalance"]  / k_imb)
    df["pressure"]   = w_delta*df["delta_term"] + w_imb*df["imb_term"]
    df["pressure_bullish"] = df["pressure"].clip(lower=0.0)
    df["pressure_bearish"] = (-df["pressure"]).clip(lower=0.0)

    # EMA par symbole
    df["pressure_smooth"] = np.nan
    for sym, g in df.groupby("sym", sort=False):
        s = g["pressure"].astype("float32")
        ema = []
        prev = 0.0
        for x in s:
            prev = alpha * float(x) + (1.0 - alpha) * prev
            ema.append(prev)
        df.loc[g.index, "pressure_smooth"] = ema

    # Nettoyage colonnes intermédiaires
    return df.drop(columns=["delta_norm","imbalance","delta_term","imb_term"], errors="ignore")

# === MASQUES, FILL LENT, LABELS SIMPLES ======================================
def add_availability_masks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for name, cols in BLOCKS.items():
        present = [c for c in cols if c in df.columns]
        if not present:
            continue
        df[f"avail_{name}"] = (~df[present].isna().any(axis=1)).astype("int8")
    return df

def ffill_slow_levels(df: pd.DataFrame, limit=10) -> pd.DataFrame:
    cols = [c for c in df.columns if c in SLOW_COLS_HINT]
    if not cols: return df
    def _ff(g):
        g[cols] = g[cols].ffill(limit=limit)
        return g
    return df.groupby("sym", group_keys=False).apply(_ff)

# (Option) labels simples – garde si tu veux la même sortie que l'ancien builder
def add_basic_labels(df: pd.DataFrame, H=5) -> pd.DataFrame:
    if not {"sym","ts","c","h","l","atr","v","up1","dn1"}.issubset(df.columns):
        return df
    out = df.copy()
    out["c_fwd"] = out.groupby("sym")["c"].shift(-H)
    atr_safe = out["atr"].replace(0, np.nan)
    out["ret_h"] = (out["c_fwd"] - out["c"]) / atr_safe
    thr = 0.10
    out["y_dir_h"] = np.select([out["ret_h"]>thr, out["ret_h"]<-thr],[1,-1], default=0).astype("int8")

    def rmax(s,w): return s.rolling(w, min_periods=1).max().shift(-w+1)
    def rmin(s,w): return s.rolling(w, min_periods=1).min().shift(-w+1)
    out["hi_win"] = out.groupby("sym")["h"].transform(lambda s: rmax(s, H))
    out["lo_win"] = out.groupby("sym")["l"].transform(lambda s: rmin(s, H))
    out["y_touch_vwap"] = ((out["hi_win"]>=out["v"]) & (out["lo_win"]<=out["v"])).astype("int8")
    out["y_touch_up1"]  = (out["hi_win"]>=out["up1"]).astype("int8")
    out["y_touch_dn1"]  = (out["lo_win"]<=out["dn1"]).astype("int8")

    out = out.dropna(subset=["c_fwd","hi_win","lo_win"])
    return out

# === MAIN =====================================================================
def main():
    print("==> Recherche JSONL…")
    files = find_jsonl_files(BASE_DIR, YMD_LIST)
    if not files:
        print("[ERREUR] aucun JSONL"); sys.exit(1)
    print("   trouvés:", len(files))

    print("==> Lecture par source…")
    frames = read_by_source(files)
    if not frames:
        print("[ERREUR] lecture vide"); sys.exit(2)
    for k,v in frames.items():
        print(f"   {k:10s} rows={len(v)} cols={len(v.columns)}")

    print("==> Timeline unifiée…")
    # Debug timestamps avant unification
    for src, df in frames.items():
        if not df.empty and "ts" in df.columns:
            ts_sample = df["ts"].head(3)
            print(f"   {src:10s} ts sample: {ts_sample.tolist()}")
    
    base = unify_timeline(frames)
    print("   base:", base.shape)
    print("   base columns:", list(base.columns))
    if not base.empty:
        print("   base sample:", base.head())

    print("==> Merge asof multi-sources… (tolérance", ASOF_TOL, ")")
    df = asof_merge_all(base, frames)
    # assure types
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values(["sym","ts"]).reset_index(drop=True)

    # NBCV pressure si manquante
    has_press = {"pressure","pressure_smooth"}.issubset(df.columns)
    nb_inputs = {"delta","total_volume","ask_volume","bid_volume"}.issubset(df.columns)
    if not has_press and nb_inputs:
        print("==> Calcul NBCV pressure (pro-safe)…")
        df = compute_pressure_cols(df)

    print("==> Masques & ffill lent…")
    df = add_availability_masks(df)
    df = ffill_slow_levels(df, limit=10)

    # (option) labels
    print("==> Labels H=5…")
    df = add_basic_labels(df, H=H)

    # ==== Normalisation de schéma (renommages, collisions, ordre) ================
    print("==> Normalisation schéma (renommages, collisions)…")
    RENAME_MAP = {
        # VWAP / Volume
        "v": "vwap",                 # si c'était le VWAP
        # PVWAP
        "up1_pvwap": "pv_up1", "dn1_pvwap": "pv_dn1",
        "up2_pvwap": "pv_up2", "dn2_pvwap": "pv_dn2",
        # ou, si tes colonnes PVWAP s'appellent littéralement "up1"/"dn1" :
        # "up1": "pv_up1", "dn1": "pv_dn1", "up2": "pv_up2", "dn2": "pv_dn2",
        # DOM price-ratio explicite (si présent)
        "l1_ba_ratio_price": "l1_ba_price_ratio",
    }

    # Si tu détectes que "v" dans ton dataset courant est en fait le volume, force:
    if "v" in df.columns and ("o" in df.columns and "h" in df.columns and "l" in df.columns and "c" in df.columns):
        # Heuristique: si "v" est entier/faible (<= 10^6) alors c'est souvent le volume
        if np.issubdtype(df["v"].dtype, np.number) and (df["v"].median() < 1e6):
            RENAME_MAP["v"] = "volume"  # ici "v" = volume, pas vwap

    df = df.rename(columns={k: v for k, v in RENAME_MAP.items() if k in df.columns})

    # Ajouter pressure_smooth s'il manque (EMA simple à partir de pressure)
    if "pressure_smooth" not in df.columns and "pressure" in df.columns:
        alpha = 0.30
        df["pressure_smooth"] = np.nan
        for sym, g in df.groupby("sym", sort=False):
            s = g["pressure"].astype("float32").fillna(0.0)
            ema = []
            prev = 0.0
            for x in s:
                prev = alpha * float(x) + (1.0 - alpha) * prev
                ema.append(prev)
            df.loc[g.index, "pressure_smooth"] = ema

    # Assainir DOM: si tu n'as pas bid_size/ask_size mais un ratio prix, clarifie le nom
    if "l1_bbo_ratio" in df.columns and "bid_size" not in df.columns and "ask_size" not in df.columns:
        # Si ton ratio est prix/prix, renomme-le pour éviter l'ambiguïté
        if "l1_ba_price_ratio" not in df.columns:
            df["l1_ba_price_ratio"] = df["l1_bbo_ratio"]
            # (option) conserve l'ancien nom aussi, ou supprime l'un des deux

    # Dédupliquer session_id s'il vient de plusieurs blocs
    if "session_id" in df.columns:
        df["session_id"] = df["session_id"].astype("string")

    # ==== Ordre recommandé (exemple compact – ajuste selon tes colonnes) =========
    ORDER = [
        # Meta
        "ts","sym","session_id",
        # OHLC
        "o","h","l","c",
        # VWAP
        "vwap","up1","dn1","up2","dn2","up3","dn3",
        # PVWAP
        "prev_start","prev_end","pvwap","pv_up1","pv_dn1","pv_up2","pv_dn2",
        # VVA
        "vah","val","vpoc","pvah","pval","ppoc","id_curr",
        # Volume/Delta
        "volume","bidvol","askvol","cum_delta_day","cum_delta_session",
        # NBCV
        "ask_volume","bid_volume","delta","trades","cumulative_delta","total_volume",
        "delta_ratio","ask_percent","bid_percent","bid_ask_ratio","ask_bid_ratio",
        "pressure_bullish","pressure_bearish","pressure","pressure_smooth",
        # Gamma / Blind
        "gex_1","gex_2","gex_3","gex_4","gex_5","gex_6","gex_7","gex_8","gex_9","gex_10",
        "hvl","1d_max","1d_min","call_resistance","put_support","call_resistance_0dte",
        "put_support_0dte","hvl_0dte","gamma_wall_0dte",
        "blind_spot_0","blind_spot_1","blind_spot_2","blind_spot_3","blind_spot_4",
        "blind_spot_5","blind_spot_6","blind_spot_7","blind_spot_8",
        # DOM
        "quote_bid","quote_ask","bid_size","ask_size","price","size",
        "has_l1","match_L1","valid","tol_ms","dt_ms_to_l1","l1_source",
        "l1_bbo_ratio","l1_ba_price_ratio","depth_imbalance",
        # Volatilité / Corr
        "vix","atr","cc",
        # Engineered (placeholders — garde ta liste)
        # "dist_vwap", "dist_pvwap", "vva_pos", "dom_imbalance", ...
        # Labels si tu les ajoutes ici
        # "y_dir_h","y_touch_vwap","y_touch_up1","y_touch_dn1","y_breakout_up_h","y_breakout_dn_h",
    ]

    # Garde l'ordre si la colonne existe, puis ajoute le reste à la fin
    cols_existing = [c for c in ORDER if c in df.columns]
    cols_remaining = [c for c in df.columns if c not in cols_existing]
    df = df[cols_existing + cols_remaining]

    # Sanity check collisions
    dups = [c for c in ["vwap","volume","pv_up1","pv_dn1","pv_up2","pv_dn2"] if c in df.columns]
    print(f"   Colonnes renommées trouvées: {dups}")

    # Optim mémoire
    for c in df.select_dtypes(include=["float64"]).columns:
        df[c] = df[c].astype("float32")
    for c in df.select_dtypes(include=["int64"]).columns:
        df[c] = df[c].astype("int32")

    # Export
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(OUT_DIR, OUT_FILE)
    try:
        import pyarrow  # noqa
        df.to_parquet(out_path, index=False)
        print("==> Export Parquet:", out_path)
    except Exception as e:
        print("[WARN] Parquet indisponible:", e, "→ CSV")
        df.to_csv(out_path.replace(".parquet",".csv"), index=False, encoding="utf-8")

    print("Terminé. Shape:", df.shape)

if __name__ == "__main__":
    main()
