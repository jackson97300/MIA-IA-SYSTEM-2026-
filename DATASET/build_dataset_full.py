# build_dataset_full.py
# -*- coding: utf-8 -*-
"""
Builder complet avec toutes les sources (PVWAP, MenthorQ, etc.)
- Utilise le builder multisource avec asof join
- Intègre PVWAP, MenthorQ, VVA, Blind Spots
- Corrige les timestamps
- Génère les labels et masques
"""

import os, glob, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# === CONFIG =======================================================
BASE_DIR = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\OCTOBRE"
YMD_LIST = ["20251002"]
OUT_DIR  = r"D:\MIA_IA_system\DATASET"
OUT_FILE = "dataset_full_20251002.parquet"
H = 5  # horizon pour labels

# Patterns de détection des sources (ordre important - plus spécifique en premier)
SOURCE_PATTERNS = {
    "blind": r"blind_spots",
    "mentorq": r"menthorq_gamma",
    "pvwap": r"pvwap",
    "nbcv": r"nbcv",
    "vva": r"vva",
    "vwap": r"vwap",
    "atr": r"atr",
    "vix": r"vix",
    "corr": r"correlation",
    "dom": r"depth",
    "quote": r"quote",
    "trade": r"trade_summary",
    "trade_ind": r"trade(?!_summary)",
    "cum_delta": r"cumulative_delta",
    "basedata": r"basedata",
}

def find_jsonl_files(base_dir: str, ymd_list: list) -> list:
    files = []
    for ymd in ymd_list:
        files.extend(glob.glob(os.path.join(base_dir, "**", f"*{ymd}*.jsonl"), recursive=True))
    return sorted(set(files))

def detect_source(file_path: str) -> str:
    """Détecte la source d'un fichier"""
    filename = os.path.basename(file_path).lower()
    for source, pattern in SOURCE_PATTERNS.items():
        if pattern in filename:
            return source
    return "misc"

def parse_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Parse les timestamps avec correction"""
    if "t" in df.columns:
        ts_values = df["t"].values
        
        # Les timestamps sont des secondes depuis minuit du 2025-10-02
        # Convertir en datetime correct
        base_date = pd.Timestamp("2025-10-02 00:00:00")
        df["ts"] = base_date + pd.to_timedelta(ts_values, unit="s")
        
        df = df.drop(columns=["t"])
    elif "ts" not in df.columns:
        return pd.DataFrame()
    
    return df

def read_source_files(files: list) -> dict:
    """Lit tous les fichiers par source"""
    sources = {}
    
    for file_path in files:
        source = detect_source(file_path)
        print(f"   Lecture {source}: {os.path.basename(file_path)}")
        
        try:
            df = pd.read_json(file_path, lines=True, dtype=False)
            if df.empty:
                continue
            
            # Parse timestamps
            df = parse_timestamp(df)
            if df.empty or "ts" not in df.columns:
                continue
            
            # Normaliser colonnes
            if "symbol" in df.columns and "sym" not in df.columns:
                df["sym"] = df["symbol"]
                df = df.drop(columns=["symbol"])
            
            if "sym" not in df.columns:
                continue
            
            # Ajouter source tag
            df["__source__"] = source
            
            # Stocker par source
            if source not in sources:
                sources[source] = []
            sources[source].append(df)
            
        except Exception as e:
            print(f"   [WARN] Erreur lecture {file_path}: {e}")
    
    # Concatener par source
    result = {}
    for source, dfs in sources.items():
        if dfs:
            combined = pd.concat(dfs, ignore_index=True, sort=False)
            combined = combined.dropna(subset=["ts", "sym"]).sort_values(["sym", "ts"])
            result[source] = combined
            print(f"   {source}: {combined.shape}")
    
    return result

def create_unified_timeline(sources: dict) -> pd.DataFrame:
    """Crée une timeline unifiée"""
    timelines = []
    for df in sources.values():
        if not df.empty:
            timelines.append(df[["sym", "ts"]])
    
    if not timelines:
        return pd.DataFrame(columns=["sym", "ts"])
    
    timeline = pd.concat(timelines, ignore_index=True)
    timeline = timeline.drop_duplicates().sort_values(["sym", "ts"]).reset_index(drop=True)
    return timeline

def merge_sources_asof(timeline: pd.DataFrame, sources: dict, tolerance: str = "5s") -> pd.DataFrame:
    """Merge toutes les sources avec asof join"""
    result = timeline.copy()
    tolerance_td = pd.Timedelta(tolerance)
    
    for source, df in sources.items():
        if df.empty:
            continue
        
        print(f"   Merge {source}...")
        
        # Préparer les colonnes (exclure __source__)
        cols_to_merge = [c for c in df.columns if c not in ["__source__"]]
        df_clean = df[["sym", "ts"] + [c for c in cols_to_merge if c not in ["sym", "ts"]]]
        
        # Merge par symbole
        merged_parts = []
        for sym in result["sym"].unique():
            timeline_sym = result[result["sym"] == sym].sort_values("ts")
            source_sym = df_clean[df_clean["sym"] == sym].sort_values("ts")
            
            if source_sym.empty:
                merged_parts.append(timeline_sym)
                continue
            
            # Merge asof
            merged = pd.merge_asof(
                timeline_sym, source_sym, 
                on="ts", direction="nearest", 
                tolerance=tolerance_td,
                suffixes=("", f"_{source}")
            )
            merged_parts.append(merged)
        
        if merged_parts:
            result = pd.concat(merged_parts, ignore_index=True)
            result = result.sort_values(["sym", "ts"]).reset_index(drop=True)
    
    return result

def add_labels_and_masks(df: pd.DataFrame, H: int = 5) -> pd.DataFrame:
    """Ajoute les labels ML et masques de disponibilité"""
    print("==> Génération des labels et masques...")
    
    df = df.copy()
    df = df.sort_values(["sym", "ts"]).reset_index(drop=True)
    
    # Labels de direction
    if {"sym", "ts", "c", "h", "l"}.issubset(df.columns):
        df["c_fwd"] = df.groupby("sym")["c"].shift(-H)
        df["ret_h"] = (df["c_fwd"] - df["c"]) / df["c"]
        
        # Normaliser par ATR si disponible
        if "atr" in df.columns:
            atr_safe = df["atr"].replace(0, np.nan)
            df["ret_h"] = (df["c_fwd"] - df["c"]) / atr_safe
        
        # Direction binaire avec seuils dynamiques basés sur VIX
        def dyn_thr(vix_val):
            """Seuils dynamiques basés sur le régime VIX"""
            if pd.isna(vix_val):
                vix_val = 20.0
            if vix_val < 15:  return 0.10  # calm
            if vix_val < 25:  return 0.08  # normal  
            if vix_val < 35:  return 0.07  # elevated
            return 0.06  # high
        
        # Appliquer seuils dynamiques si VIX disponible
        if "vix" in df.columns:
            thr_series = df["vix"].apply(dyn_thr)
        else:
            thr_series = pd.Series([0.08] * len(df), index=df.index)
        
        df["y_dir_h"] = np.select(
            [df["ret_h"] > thr_series, df["ret_h"] < -thr_series],
            [1, -1], default=0
        ).astype("int8")
        
        # High/Low dans la fenêtre
        df["hi_win"] = df.groupby("sym")["h"].transform(
            lambda s: s.rolling(H, min_periods=1).max().shift(-H+1)
        )
        df["lo_win"] = df.groupby("sym")["l"].transform(
            lambda s: s.rolling(H, min_periods=1).min().shift(-H+1)
        )
        
        # Labels de touch VWAP
        if "v" in df.columns:
            df["y_touch_vwap"] = (
                (df["hi_win"] >= df["v"]) & (df["lo_win"] <= df["v"])
            ).astype("int8")
        
        # Labels de touch VWAP bands
        if "up1" in df.columns and "dn1" in df.columns:
            df["y_touch_up1"] = (df["hi_win"] >= df["up1"]).astype("int8")
            df["y_touch_dn1"] = (df["lo_win"] <= df["dn1"]).astype("int8")
        
        # Labels de breakout
        if "pressure_smooth" in df.columns:
            if "y_touch_up1" in df.columns:
                df["y_breakout_up_h"] = (
                    (df["y_touch_up1"] == 1) & (df["pressure_smooth"] > 0.4)
                ).astype("int8")
            if "y_touch_dn1" in df.columns:
                df["y_breakout_dn1"] = (
                    (df["y_touch_dn1"] == 1) & (df["pressure_smooth"] < -0.4)
                ).astype("int8")
        
        # Supprimer lignes sans horizon complet
        df = df.dropna(subset=["c_fwd", "hi_win", "lo_win"])
    
    # Masques de disponibilité
    blocks = {
        "ohlc": ["o", "h", "l", "c"],
        "vwap": ["v", "up1", "dn1", "up2", "dn2"],
        "pvwap": ["pvwap", "pv_up1", "pv_dn1"],
        "nbcv": ["ask_volume", "bid_volume", "delta", "pressure"],
        "mentorq": ["gex_1", "gex_2", "hvl", "1d_max", "1d_min"],
        "blind": [f"blind_spot_{i}" for i in range(9)],
        "vva": ["vah", "val", "vpoc"],
    }
    
    for name, cols in blocks.items():
        present_cols = [c for c in cols if c in df.columns]
        if present_cols:
            df[f"avail_{name}"] = (~df[present_cols].isna().any(axis=1)).astype("int8")
    
    return df

def normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise le schéma (renommages, collisions)"""
    print("==> Normalisation du schéma...")
    
    # Renommages pour éviter les collisions
    rename_map = {
        "v": "vwap",  # VWAP principal
    }
    
    # Heuristique pour v vs volume
    if "v" in df.columns:
        if df["v"].median() < 1e6:  # Probablement du volume
            rename_map["v"] = "volume"
        else:  # Probablement du VWAP
            rename_map["v"] = "vwap"
    
    df = df.rename(columns=rename_map)
    
    # Calculer pressure_smooth si manquant
    if "pressure" in df.columns and "pressure_smooth" not in df.columns:
        print("   Calcul pressure_smooth...")
        alpha = 0.30
        df["pressure_smooth"] = np.nan
        
        for sym in df["sym"].unique():
            mask = df["sym"] == sym
            pressure = df.loc[mask, "pressure"].fillna(0.0)
            
            ema = []
            prev = 0.0
            for p in pressure:
                prev = alpha * p + (1.0 - alpha) * prev
                ema.append(prev)
            
            df.loc[mask, "pressure_smooth"] = ema
    
    return df

def main():
    print("==> Recherche des fichiers JSONL...")
    files = find_jsonl_files(BASE_DIR, YMD_LIST)
    if not files:
        print("[ERREUR] Aucun fichier JSONL trouvé")
        sys.exit(1)
    print(f"   Fichiers trouvés: {len(files)}")
    
    print("==> Lecture par source...")
    sources = read_source_files(files)
    if not sources:
        print("[ERREUR] Aucune source valide")
        sys.exit(1)
    
    print("==> Timeline unifiée...")
    timeline = create_unified_timeline(sources)
    print(f"   Timeline: {timeline.shape}")
    
    print("==> Merge asof multi-sources...")
    df = merge_sources_asof(timeline, sources)
    print(f"   Après merge: {df.shape}")
    
    print("==> Normalisation du schéma...")
    df = normalize_schema(df)
    
    print("==> Labels et masques...")
    df = add_labels_and_masks(df, H=H)
    
    # Optimisation mémoire
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = df[col].astype("float32")
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = df[col].astype("int32")
    
    # Export
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(OUT_DIR, OUT_FILE)
    
    try:
        df.to_parquet(out_path, index=False)
        print(f"==> Export Parquet: {out_path}")
    except Exception as e:
        print(f"[WARN] Parquet indisponible: {e} → CSV")
        csv_path = out_path.replace(".parquet", ".csv")
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"   Export CSV: {csv_path}")
    
    print(f"==> Terminé. Shape finale: {df.shape}")
    print(f"   Colonnes: {len(df.columns)}")
    
    # Rapport rapide
    print("\n=== RAPPORT RAPIDE ===")
    print(f"   Symboles: {df['sym'].value_counts().to_dict()}")
    print(f"   Période: {df['ts'].min()} → {df['ts'].max()}")
    print(f"   NaN ratio: {df.isna().mean().mean():.3f}")
    
    # Labels
    label_cols = [c for c in df.columns if c.startswith("y_")]
    if label_cols:
        print(f"   Labels: {label_cols}")
        for col in label_cols:
            if col in df.columns:
                dist = df[col].value_counts().sort_index()
                print(f"     {col}: {dict(dist)}")
    
    # Sources disponibles
    avail_cols = [c for c in df.columns if c.startswith("avail_")]
    if avail_cols:
        print(f"   Sources disponibles:")
        for col in avail_cols:
            coverage = df[col].mean()
            print(f"     {col}: {coverage:.3f}")

if __name__ == "__main__":
    main()
