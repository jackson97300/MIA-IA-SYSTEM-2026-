# build_dataset.py
# -*- coding: utf-8 -*-
"""
Construire un dataset ML à partir des JSONL de 20251002 & 20251003 :
- Lecture récursive des fichiers
- Assemblage + tri
- Masques de disponibilité (NBCV, DOM, VWAP, PVWAP, VVA)
- Forward-fill limité des niveaux lents (Gamma/Blind/VVA/PVWAP)
- Labels H=5 (direction, touch VWAP/UP1/DN1, breakout up/down)
- Export Parquet
"""

import os
import sys
import glob
import math
import warnings
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# === CONFIG UTILISATEUR ===============================================
BASE_DIR = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\OCTOBRE"
YMD_LIST = ["20251002"]  # Temporairement seulement le 2 octobre
OUT_DIR = r"D:\MIA_IA_system\DATASET"
OUT_FILE = "dataset_20251002_only.parquet"
H = 5                      # horizon en barres/minutes pour les labels
RET_NEUTRAL_THR_ATR = 0.10 # zone neutre direction (±0.1 ATR)
PRESS_UP_THR = 0.40        # seuil pression_smooth pour breakout up
PRESS_DN_THR = -0.40       # seuil pression_smooth pour breakout down

# Colonnes par blocs (ajuste librement si besoin)
BLOCKS = {
    "nbcv": ["ask_volume","bid_volume","delta","trades","cumulative_delta","total_volume",
             "delta_ratio","ask_percent","bid_percent","bid_ask_ratio","ask_bid_ratio",
             "pressure_bullish","pressure_bearish","pressure","pressure_smooth"],
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
    "meta": ["sym","ts"]  # requis
}

# Colonnes "lentes" à forward-fill (limité)
SLOW_COLS = list(set(
    BLOCKS["gamma"] + BLOCKS["blind"] + BLOCKS["vva"] + BLOCKS["pvwap"]
))

# === OUTILS ============================================================

def find_jsonl_files(base_dir: str, ymd_list: List[str]) -> List[str]:
    files = []
    for ymd in ymd_list:
        # Cherche récursivement les fichiers qui contiennent la date dans leur nom
        pattern = os.path.join(base_dir, "**", f"*{ymd}*.jsonl")
        files.extend(glob.glob(pattern, recursive=True))
    # Un petit filtrage de sécurité (éviter metadata/quality json)
    files = [f for f in files if f.lower().endswith(".jsonl")]
    return sorted(set(files))

def read_many_jsonl(files: List[str]) -> pd.DataFrame:
    dfs = []
    for f in files:
        try:
            df = pd.read_json(f, lines=True, dtype=False)
            # Assure présence meta
            if "ts" not in df.columns:
                continue
            if "sym" not in df.columns and "symbol" in df.columns:
                df = df.rename(columns={"symbol": "sym"})
            if "sym" not in df.columns:
                continue
            dfs.append(df)
        except Exception as e:
            print(f"[WARN] Lecture échouée: {f} -> {e}")
    if not dfs:
        return pd.DataFrame(columns=BLOCKS["meta"])
    big = pd.concat(dfs, ignore_index=True, sort=False)
    return big

def coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    # Types utiles
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True).dt.tz_convert(None)
    for col in df.columns:
        if col in ("sym","session_id","l1_source"):
            df[col] = df[col].astype("string")
    return df

def dedup_sort(df: pd.DataFrame) -> pd.DataFrame:
    if not {"sym","ts"}.issubset(df.columns):
        return df
    df = df.drop_duplicates(subset=["sym","ts"]).sort_values(["sym","ts"]).reset_index(drop=True)
    return df

def add_availability_masks(df: pd.DataFrame) -> pd.DataFrame:
    for block_name, cols in BLOCKS.items():
        if block_name in ("meta","ohlc","vol","delta_cum","vola","corr","gamma","blind","pvwap","vva","vwap","dom","nbcv"):
            present = [c for c in cols if c in df.columns]
            if not present:
                continue
            mask_name = f"avail_{block_name}"
            df[mask_name] = (~df[present].isna().any(axis=1)).astype(np.int8)
    return df

def ffill_slow_levels(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    cols = [c for c in SLOW_COLS if c in df.columns]
    if not cols:
        return df
    def _ff(sym_df: pd.DataFrame) -> pd.DataFrame:
        sym_df[cols] = sym_df[cols].ffill(limit=limit)
        return sym_df
    return df.groupby("sym", group_keys=False).apply(_ff)

def build_labels(df: pd.DataFrame, H: int = 5,
                 atr_col: str = "atr", close_col: str = "c",
                 press_col: str = "pressure_smooth",
                 v_col: str = "v", up1_col: str = "up1", dn1_col: str = "dn1",
                 thr_neutral_atr: float = 0.10,
                 press_up_thr: float = 0.40, press_dn_thr: float = -0.40) -> pd.DataFrame:
    if "sym" not in df.columns or close_col not in df.columns:
        return df

    out = df.copy()

    # Futures (direction)
    out["c_fwd"] = out.groupby("sym")[close_col].shift(-H)
    # Eviter division 0
    atr_safe = out[atr_col].replace(0, np.nan) if atr_col in out.columns else np.nan
    out["ret_h"] = (out["c_fwd"] - out[close_col]) / atr_safe

    # Direction 3 classes (1, 0, -1)
    if "ret_h" in out.columns:
        out["y_dir_h"] = np.select(
            [
                out["ret_h"] > thr_neutral_atr,
                out["ret_h"] < -thr_neutral_atr
            ],
            [1, -1], default=0
        ).astype(np.int8)

    # Fenêtre high/low futur (approx) pour touch niveaux
    def rolling_max_shifted(s: pd.Series, w: int) -> pd.Series:
        return s.rolling(w, min_periods=1).max().shift(-w+1)
    def rolling_min_shifted(s: pd.Series, w: int) -> pd.Series:
        return s.rolling(w, min_periods=1).min().shift(-w+1)

    if "h" in out.columns and "l" in out.columns:
        out["hi_win"] = out.groupby("sym")["h"].transform(lambda s: rolling_max_shifted(s, H))
        out["lo_win"] = out.groupby("sym")["l"].transform(lambda s: rolling_min_shifted(s, H))

    # Touch VWAP/UP1/DN1
    if all(c in out.columns for c in (v_col, "hi_win", "lo_win")):
        out["y_touch_vwap"] = ((out["hi_win"] >= out[v_col]) & (out["lo_win"] <= out[v_col])).astype(np.int8)
    if all(c in out.columns for c in (up1_col, "hi_win")):
        out["y_touch_up1"]  = (out["hi_win"] >= out[up1_col]).astype(np.int8)
    if all(c in out.columns for c in (dn1_col, "lo_win")):
        out["y_touch_dn1"]  = (out["lo_win"] <= out[dn1_col]).astype(np.int8)

    # Breakout confirmé par pression
    if ("y_touch_up1" in out.columns) and (press_col in out.columns):
        out["y_breakout_up_h"] = ((out["y_touch_up1"] == 1) & (out[press_col] >= press_up_thr)).astype(np.int8)
    if ("y_touch_dn1" in out.columns) and (press_col in out.columns):
        out["y_breakout_dn_h"] = ((out["y_touch_dn1"] == 1) & (out[press_col] <= press_dn_thr)).astype(np.int8)

    # Drop dernières lignes incomplètes (pas de futur)
    if "c_fwd" in out.columns and "hi_win" in out.columns and "lo_win" in out.columns:
        out = out.dropna(subset=["c_fwd","hi_win","lo_win"]).copy()

    return out

def basic_qc_report(df_before: pd.DataFrame, df_after: pd.DataFrame) -> Dict[str, float]:
    rep = {}
    rep["rows_before"] = float(len(df_before))
    rep["rows_after"]  = float(len(df_after))
    rep["kept_ratio"]  = float(len(df_after)) / max(1.0, float(len(df_before)))
    # petit compteur de NaN par grand bloc
    for bname, cols in BLOCKS.items():
        present = [c for c in cols if c in df_after.columns]
        if not present:
            continue
        rep[f"nan_ratio_{bname}"] = float(df_after[present].isna().any(axis=1).mean())
    return rep

def ensure_outdir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)

# === MAIN ====================================================================

def main():
    print("==> Recherche des JSONL…")
    files = find_jsonl_files(BASE_DIR, YMD_LIST)
    if not files:
        print("[ERREUR] Aucun fichier JSONL trouvé pour", YMD_LIST, "dans", BASE_DIR)
        sys.exit(1)
    print(f"   Fichiers trouvés: {len(files)}")

    print("==> Lecture/assemblage…")
    df_raw = read_many_jsonl(files)
    if df_raw.empty:
        print("[ERREUR] Lecture vide.")
        sys.exit(2)

    df = coerce_dtypes(df_raw)
    df = dedup_sort(df)

    # Colonnes minimales
    if not {"sym","ts","c"}.issubset(df.columns):
        print("[ERREUR] Colonnes minimales manquantes (sym, ts, c).")
        print("Colonnes disponibles:", list(df.columns)[:50])
        sys.exit(3)

    print("==> Ajout des masques de disponibilité…")
    df = add_availability_masks(df)

    print("==> Forward-fill limité des niveaux lents…")
    df = ffill_slow_levels(df, limit=10)

    print("==> Génération des labels (H=5)…")
    df_labeled = build_labels(df, H=H,
                              atr_col="atr", close_col="c",
                              press_col="pressure_smooth",
                              v_col="v", up1_col="up1", dn1_col="dn1",
                              thr_neutral_atr=RET_NEUTRAL_THR_ATR,
                              press_up_thr=PRESS_UP_THR, press_dn_thr=PRESS_DN_THR)

    # QC
    print("==> QC…")
    rep = basic_qc_report(df, df_labeled)
    for k, v in rep.items():
        if "ratio" in k:
            print(f"   {k}: {v:.3f}")
        else:
            print(f"   {k}: {v}")

    # Export
    ensure_outdir(OUT_DIR)
    out_path = os.path.join(OUT_DIR, OUT_FILE)
    print("==> Export Parquet:", out_path)

    # Optimisation mémoire légère : float32
    for col in df_labeled.select_dtypes(include=["float64"]).columns:
        df_labeled[col] = df_labeled[col].astype("float32")
    for col in df_labeled.select_dtypes(include=["int64"]).columns:
        df_labeled[col] = df_labeled[col].astype("int32")

    try:
        import pyarrow  # noqa
        df_labeled.to_parquet(out_path, index=False)
    except Exception as e:
        print(f"[WARN] Parquet indisponible ({e}), fallback CSV")
        csv_path = out_path.replace(".parquet", ".csv")
        df_labeled.to_csv(csv_path, index=False, encoding="utf-8")
        print("   Export CSV:", csv_path)

    print("==> Terminé. Shape finale:", df_labeled.shape)

if __name__ == "__main__":
    main()