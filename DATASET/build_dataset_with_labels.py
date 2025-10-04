# build_dataset_with_labels.py
# -*- coding: utf-8 -*-
"""
Version améliorée du builder avec labels ML et timestamps corrigés
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
OUT_FILE = "dataset_with_labels_20251002.parquet"
H = 5  # horizon pour labels

def find_jsonl_files(base_dir: str, ymd_list: list) -> list:
    files = []
    for ymd in ymd_list:
        files.extend(glob.glob(os.path.join(base_dir, "**", f"*{ymd}*.jsonl"), recursive=True))
    return sorted(set(files))

def read_simple_jsonl(file_path: str) -> pd.DataFrame:
    """Lecture simple d'un fichier JSONL avec timestamps corrigés"""
    try:
        df = pd.read_json(file_path, lines=True, dtype=False)
        if df.empty:
            return pd.DataFrame()
        
        # Corriger les timestamps - essayer différentes unités
        if "t" in df.columns:
            # Les timestamps semblent être en nanosecondes depuis 2025-10-02
            # Convertir en timestamp Unix puis en datetime
            try:
                # Essayer nanosecondes
                ts = pd.to_datetime(df["t"], unit="ns", errors="coerce")
                # Si les dates sont dans le futur (après 2030), essayer millisecondes
                if ts.dt.year.max() > 2030:
                    ts = pd.to_datetime(df["t"], unit="ms", errors="coerce")
                # Si encore dans le futur, essayer secondes
                if ts.dt.year.max() > 2030:
                    ts = pd.to_datetime(df["t"], unit="s", errors="coerce")
                
                df["ts"] = ts
                df = df.drop(columns=["t"])
            except:
                df["ts"] = pd.to_datetime(df["t"], errors="coerce")
                df = df.drop(columns=["t"])
        elif "ts" not in df.columns:
            return pd.DataFrame()
        
        # Normaliser les colonnes de symbole
        if "symbol" in df.columns and "sym" not in df.columns:
            df["sym"] = df["symbol"]
            df = df.drop(columns=["symbol"])
        
        return df.dropna(subset=["ts", "sym"])
        
    except Exception as e:
        print(f"[WARN] Lecture échouée {os.path.basename(file_path)}: {e}")
        return pd.DataFrame()

def add_labels(df: pd.DataFrame, H: int = 5) -> pd.DataFrame:
    """Ajouter les labels ML"""
    print("==> Génération des labels ML…")
    
    if not {"sym", "ts", "c", "h", "l"}.issubset(df.columns):
        print("   [WARN] Colonnes manquantes pour labels")
        return df
    
    df = df.copy()
    df = df.sort_values(["sym", "ts"]).reset_index(drop=True)
    
    # Labels de direction (H=5)
    df["c_fwd"] = df.groupby("sym")["c"].shift(-H)
    df["ret_h"] = (df["c_fwd"] - df["c"]) / df["c"]
    
    # Normaliser par ATR si disponible
    if "atr" in df.columns:
        atr_safe = df["atr"].replace(0, np.nan)
        df["ret_h"] = (df["c_fwd"] - df["c"]) / atr_safe
    
    # Direction binaire (seuil 0.1%)
    thr = 0.001
    df["y_dir_h"] = np.select(
        [df["ret_h"] > thr, df["ret_h"] < -thr],
        [1, -1], 
        default=0
    ).astype("int8")
    
    # High/Low dans la fenêtre H (toujours créer ces colonnes)
    df["hi_win"] = df.groupby("sym")["h"].transform(
        lambda s: s.rolling(H, min_periods=1).max().shift(-H+1)
    )
    df["lo_win"] = df.groupby("sym")["l"].transform(
        lambda s: s.rolling(H, min_periods=1).min().shift(-H+1)
    )
    
    # Labels de touch VWAP
    if "v" in df.columns:  # VWAP
        df["y_touch_vwap"] = (
            (df["hi_win"] >= df["v"]) & (df["lo_win"] <= df["v"])
        ).astype("int8")
    
    # Labels de touch VWAP bands
    if "up1" in df.columns and "dn1" in df.columns:
        df["y_touch_up1"] = (df["hi_win"] >= df["up1"]).astype("int8")
        df["y_touch_dn1"] = (df["lo_win"] <= df["dn1"]).astype("int8")
    
    # Labels de breakout avec pressure
    if "pressure_smooth" in df.columns:
        if "y_touch_up1" in df.columns:
            df["y_breakout_up_h"] = (
                (df["y_touch_up1"] == 1) & (df["pressure_smooth"] > 0.4)
            ).astype("int8")
        if "y_touch_dn1" in df.columns:
            df["y_breakout_dn_h"] = (
                (df["y_touch_dn1"] == 1) & (df["pressure_smooth"] < -0.4)
            ).astype("int8")
    
    # Supprimer les lignes sans horizon complet
    df = df.dropna(subset=["c_fwd", "hi_win", "lo_win"])
    
    print(f"   Labels générés: {df.shape[0]} lignes")
    return df

def add_availability_masks(df: pd.DataFrame) -> pd.DataFrame:
    """Ajouter les masques de disponibilité"""
    print("==> Ajout des masques de disponibilité…")
    
    blocks = {
        "ohlc": ["o", "h", "l", "c"],
        "vwap": ["v", "up1", "dn1", "up2", "dn2"],
        "nbcv": ["ask_volume", "bid_volume", "delta", "pressure"],
        "pvwap": ["pvwap", "pv_up1", "pv_dn1"],
    }
    
    for name, cols in blocks.items():
        present_cols = [c for c in cols if c in df.columns]
        if present_cols:
            df[f"avail_{name}"] = (~df[present_cols].isna().any(axis=1)).astype("int8")
    
    return df

def main():
    print("==> Recherche JSONL…")
    files = find_jsonl_files(BASE_DIR, YMD_LIST)
    if not files:
        print("[ERREUR] Aucun fichier JSONL trouvé")
        sys.exit(1)
    print(f"   Fichiers trouvés: {len(files)}")
    
    # Lire les fichiers principaux
    print("==> Lecture des sources principales…")
    
    # Basedata (OHLC + volume)
    basedata_files = [f for f in files if "basedata" in f.lower()]
    print(f"   Basedata files: {len(basedata_files)}")
    
    basedata_dfs = []
    for f in basedata_files:
        df = read_simple_jsonl(f)
        if not df.empty:
            basedata_dfs.append(df)
    
    if not basedata_dfs:
        print("[ERREUR] Aucune donnée basedata valide")
        sys.exit(1)
    
    df_base = pd.concat(basedata_dfs, ignore_index=True)
    print(f"   Basedata: {df_base.shape}")
    
    # VWAP
    vwap_files = [f for f in files if "vwap" in f.lower()]
    print(f"   VWAP files: {len(vwap_files)}")
    
    vwap_dfs = []
    for f in vwap_files:
        df = read_simple_jsonl(f)
        if not df.empty:
            vwap_dfs.append(df)
    
    if vwap_dfs:
        df_vwap = pd.concat(vwap_dfs, ignore_index=True)
        print(f"   VWAP: {df_vwap.shape}")
    else:
        df_vwap = pd.DataFrame()
        print("   VWAP: Aucune donnée")
    
    # NBCV
    nbcv_files = [f for f in files if "nbcv" in f.lower()]
    print(f"   NBCV files: {len(nbcv_files)}")
    
    nbcv_dfs = []
    for f in nbcv_files:
        df = read_simple_jsonl(f)
        if not df.empty:
            nbcv_dfs.append(df)
    
    if nbcv_dfs:
        df_nbcv = pd.concat(nbcv_dfs, ignore_index=True)
        print(f"   NBCV: {df_nbcv.shape}")
    else:
        df_nbcv = pd.DataFrame()
        print("   NBCV: Aucune donnée")
    
    # Merge simple par timestamp le plus proche
    print("==> Merge des sources…")
    
    # Commencer avec basedata
    df_final = df_base.copy()
    
    # Ajouter VWAP si disponible
    if not df_vwap.empty:
        print("   Ajout VWAP…")
        merged_vwap = []
        for sym in df_final["sym"].unique():
            base_sym = df_final[df_final["sym"] == sym].sort_values("ts")
            vwap_sym = df_vwap[df_vwap["sym"] == sym].sort_values("ts")
            
            if not vwap_sym.empty:
                merge = pd.merge_asof(base_sym, vwap_sym, on="ts", direction="nearest", 
                                    tolerance=pd.Timedelta("5s"), suffixes=("", "_vwap"))
                merged_vwap.append(merge)
            else:
                merged_vwap.append(base_sym)
        
        df_final = pd.concat(merged_vwap, ignore_index=True)
        print(f"   Après VWAP: {df_final.shape}")
    
    # Ajouter NBCV si disponible
    if not df_nbcv.empty:
        print("   Ajout NBCV…")
        merged_nbcv = []
        for sym in df_final["sym"].unique():
            base_sym = df_final[df_final["sym"] == sym].sort_values("ts")
            nbcv_sym = df_nbcv[df_nbcv["sym"] == sym].sort_values("ts")
            
            if not nbcv_sym.empty:
                merge = pd.merge_asof(base_sym, nbcv_sym, on="ts", direction="nearest", 
                                    tolerance=pd.Timedelta("5s"), suffixes=("", "_nbcv"))
                merged_nbcv.append(merge)
            else:
                merged_nbcv.append(base_sym)
        
        df_final = pd.concat(merged_nbcv, ignore_index=True)
        print(f"   Après NBCV: {df_final.shape}")
    
    # Nettoyage final
    print("==> Nettoyage final…")
    
    # Renommer les colonnes problématiques
    rename_map = {
        "v": "vwap",  # Si c'est le VWAP
    }
    
    # Heuristique pour v vs volume
    if "v" in df_final.columns:
        if df_final["v"].median() < 1e6:  # Probablement du volume
            rename_map["v"] = "volume"
        else:  # Probablement du VWAP
            rename_map["v"] = "vwap"
    
    df_final = df_final.rename(columns=rename_map)
    
    # Calculer pressure_smooth si manquant
    if "pressure" in df_final.columns and "pressure_smooth" not in df_final.columns:
        print("   Calcul pressure_smooth…")
        alpha = 0.30
        df_final["pressure_smooth"] = np.nan
        
        for sym in df_final["sym"].unique():
            mask = df_final["sym"] == sym
            pressure = df_final.loc[mask, "pressure"].fillna(0.0)
            
            ema = []
            prev = 0.0
            for p in pressure:
                prev = alpha * p + (1.0 - alpha) * prev
                ema.append(prev)
            
            df_final.loc[mask, "pressure_smooth"] = ema
    
    # Ajouter les labels ML
    df_final = add_labels(df_final, H=H)
    
    # Ajouter les masques de disponibilité
    df_final = add_availability_masks(df_final)
    
    # Optimisation mémoire
    for col in df_final.select_dtypes(include=["float64"]).columns:
        df_final[col] = df_final[col].astype("float32")
    for col in df_final.select_dtypes(include=["int64"]).columns:
        df_final[col] = df_final[col].astype("int32")
    
    # Export
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(OUT_DIR, OUT_FILE)
    
    try:
        df_final.to_parquet(out_path, index=False)
        print(f"==> Export Parquet: {out_path}")
    except Exception as e:
        print(f"[WARN] Parquet indisponible: {e} → CSV")
        csv_path = out_path.replace(".parquet", ".csv")
        df_final.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"   Export CSV: {csv_path}")
    
    print(f"==> Terminé. Shape finale: {df_final.shape}")
    print(f"   Colonnes: {list(df_final.columns)}")
    
    # Rapport rapide
    print("\n=== RAPPORT RAPIDE ===")
    print(f"   Symboles: {df_final['sym'].value_counts().to_dict()}")
    print(f"   Période: {df_final['ts'].min()} → {df_final['ts'].max()}")
    print(f"   NaN ratio: {df_final.isna().mean().mean():.3f}")
    
    # Labels
    label_cols = [c for c in df_final.columns if c.startswith("y_")]
    if label_cols:
        print(f"   Labels: {label_cols}")
        for col in label_cols:
            if col in df_final.columns:
                dist = df_final[col].value_counts().sort_index()
                print(f"     {col}: {dict(dist)}")

if __name__ == "__main__":
    main()
