# train_baseline.py
# -*- coding: utf-8 -*-
"""
Entraîne XGBoost, LightGBM et CatBoost sur le dataset parquet.
- Split temporel (pivot = quantile temps)
- Support binaire (ex: y_touch_vwap) et multiclasses (ex: y_dir_h)
- Gère les NaN (arbres), garde les masques avail_*
- Sauvegarde modèles + rapport comparatif CSV
"""

import os
import sys
import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score,
    f1_score, log_loss, matthews_corrcoef, confusion_matrix, classification_report
)
from sklearn.model_selection import train_test_split

# --- Try imports for models ---------------------------------------------------
have_lgb = True
have_cat = True
try:
    from xgboost import XGBClassifier
except Exception as e:
    print("[ERREUR] xgboost manquant:", e); sys.exit(1)

try:
    from lightgbm import LGBMClassifier
except Exception as e:
    have_lgb = False
    print("[WARN] LightGBM indisponible:", e)

try:
    from catboost import CatBoostClassifier
except Exception as e:
    have_cat = False
    print("[WARN] CatBoost indisponible:", e)

# --- Config chemins -----------------------------------------------------------
DATASET_PATH = r"D:\MIA_IA_system\DATASET\dataset_20251002_20251003.parquet"
OUT_MODELS   = r"D:\MIA_IA_system\DATASET\models"
OUT_RESULTS  = r"D:\MIA_IA_system\DATASET\results"

os.makedirs(OUT_MODELS, exist_ok=True)
os.makedirs(OUT_RESULTS, exist_ok=True)

# --- Utils --------------------------------------------------------------------
def is_multiclass(y: np.ndarray) -> bool:
    """Détecte la multiclass (≥3 classes)."""
    return len(np.unique(y[~pd.isna(y)])) >= 3

def drop_leak_cols(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """Supprime colonnes futures/leaks et la target."""
    leaks = {
        "c_fwd", "ret_h", "hi_win", "lo_win",  # futures
    }
    # Toutes les colonnes de labels
    leaks |= set([c for c in df.columns if c.startswith("y_")])
    # Identifiants
    leaks |= {"ts", "sym"}
    # Retire target explicitement si présente
    leaks |= {target_col}
    keep = [c for c in df.columns if c not in leaks]
    return df[keep].copy()

def clean_features(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les features pour ML (supprime colonnes non-numériques)."""
    # Garder seulement les colonnes numériques
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Supprimer les colonnes avec trop de NaN (>50%)
    clean_cols = []
    for col in numeric_cols:
        if df[col].isna().mean() < 0.5:
            clean_cols.append(col)
    
    # Anti-fuite: vérifier qu'aucune feature de fuite n'est présente
    LEAK_PATTERNS = ("_fwd", "hi_win", "lo_win")
    LEAK_EXACT = {"ret_h"}
    bad = [c for c in clean_cols if c in LEAK_EXACT or any(p in c for p in LEAK_PATTERNS) or c.startswith("y_")]
    assert not bad, f"Leak features détectées: {bad}"
    
    print(f"   Features nettoyées: {len(clean_cols)}/{len(df.columns)} colonnes")
    return df[clean_cols].copy()

def temporal_split(df: pd.DataFrame, pivot_quantile: float = 0.7):
    """Split temporel simple: train = ancien, test = récent (pivot quantile)."""
    if "ts" not in df.columns:
        raise ValueError("Colonne ts manquante.")
    
    ts = pd.to_datetime(df["ts"])
    
    # Si les timestamps sont tous identiques (problème de parsing), utiliser l'index
    if ts.nunique() <= 1:
        print("   [WARN] Timestamps identiques, split par index")
        pivot_idx = int(len(df) * pivot_quantile)
        mask_train = df.index <= pivot_idx
        pivot_time = f"index_{pivot_idx}"
    else:
        # Pivot temporel normal
        pivot_time = ts.quantile(pivot_quantile)
        mask_train = ts < pivot_time
    
    return mask_train, ~mask_train, pivot_time

def scale_pos_weight_from_y(y_train: np.ndarray) -> float:
    """Pour binaire: ratio négatifs/positifs (évite déséquilibre)."""
    pos = np.sum(y_train == 1)
    neg = np.sum(y_train == 0)
    if pos == 0:
        return 1.0
    return float(neg) / float(pos)

def metrics_binary(y_true, proba):
    y_true_bin = (y_true == 1).astype(int)
    preds = (proba >= 0.5).astype(int)
    return {
        "ROC_AUC":  float(roc_auc_score(y_true_bin, proba)) if len(np.unique(y_true_bin))==2 else np.nan,
        "PR_AUC":   float(average_precision_score(y_true_bin, proba)) if np.any(y_true_bin==1) else np.nan,
        "ACC":      float(accuracy_score(y_true_bin, preds)),
        "F1":       float(f1_score(y_true_bin, preds, zero_division=0)),
        "MCC":      float(matthews_corrcoef(y_true_bin, preds)) if len(np.unique(y_true_bin))==2 else np.nan,
        "LogLoss":  float(log_loss(y_true_bin, np.vstack([1-proba, proba]).T, labels=[0,1]))
    }

def metrics_multiclass(y_true, proba, classes):
    preds = classes[np.argmax(proba, axis=1)]
    
    # Labels complets pour éviter les warnings
    LABELS = [0, 1, 2] if len(classes) == 3 else classes.tolist()
    
    # Métriques de base
    metrics = {
        "ACC":     float(accuracy_score(y_true, preds)),
        "F1_macro":float(f1_score(y_true, preds, average="macro", zero_division=0, labels=LABELS)),
        "LogLoss": float(log_loss(y_true, proba, labels=classes)),
        "MCC":     float(matthews_corrcoef(y_true, preds)),
    }
    
    # PR-AUC pour chaque classe (moyenne macro)
    try:
        pr_aucs = []
        for i, class_label in enumerate(classes):
            y_binary = (y_true == class_label).astype(int)
            if len(np.unique(y_binary)) > 1:  # Au moins 2 classes
                pr_auc = average_precision_score(y_binary, proba[:, i])
                pr_aucs.append(pr_auc)
        if pr_aucs:
            metrics["PR_AUC_macro"] = float(np.mean(pr_aucs))
        else:
            metrics["PR_AUC_macro"] = 0.0
    except Exception:
        metrics["PR_AUC_macro"] = 0.0
    
    return metrics

def save_json(d: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# --- Training wrappers --------------------------------------------------------
def train_xgb(Xtr, ytr, Xte, yte, multiclass=False, classes=None, binary_pos_label=1):
    if multiclass:
        num_class = len(classes)
        
        # Calculer les poids par classe pour rééquilibrer
        classes_unique, counts = np.unique(ytr, return_counts=True)
        class_weight = {int(c): float(len(ytr)) / (len(classes_unique) * cnt) for c, cnt in zip(classes_unique, counts)}
        sample_weight = np.array([class_weight[int(y)] for y in ytr], dtype=np.float32)
        
        print(f"   Poids par classe: {class_weight}")
        
        clf = XGBClassifier(
            n_estimators=600, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            reg_alpha=1e-3, reg_lambda=1e-2,
            objective="multi:softprob", num_class=num_class,
            eval_metric="mlogloss", tree_method="hist", verbosity=0
        )
        clf.fit(Xtr, ytr, sample_weight=sample_weight)
        proba = clf.predict_proba(Xte)
        m = metrics_multiclass(yte, proba, np.array(classes))
    else:
        spw = scale_pos_weight_from_y((ytr==binary_pos_label).astype(int))
        clf = XGBClassifier(
            n_estimators=400, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            reg_alpha=1e-3, reg_lambda=1e-2,
            objective="binary:logistic", eval_metric="logloss",
            scale_pos_weight=spw, tree_method="hist", verbosity=0
        )
        clf.fit(Xtr, (ytr==binary_pos_label).astype(int))
        proba = clf.predict_proba(Xte)[:,1]
        m = metrics_binary((yte==binary_pos_label).astype(int), proba)
    return clf, m

def train_lgbm(Xtr, ytr, Xte, yte, multiclass=False, classes=None, binary_pos_label=1):
    if not have_lgb: 
        return None, {"ACC": np.nan}
    if multiclass:
        num_class = len(classes)
        
        # Calculer les poids par classe pour LightGBM
        classes_unique, counts = np.unique(ytr, return_counts=True)
        class_weight = {int(c): float(len(ytr)) / (len(classes_unique) * cnt) for c, cnt in zip(classes_unique, counts)}
        
        print(f"   Poids par classe LGBM: {class_weight}")
        
        clf = LGBMClassifier(
            objective="multiclass", num_class=num_class,
            n_estimators=600, learning_rate=0.05, max_depth=-1,
            num_leaves=31, subsample=0.8, colsample_bytree=0.8,
            reg_alpha=1e-3, reg_lambda=1e-2, class_weight=class_weight, 
            random_state=42, n_jobs=-1
        )
        clf.fit(Xtr, ytr)
        proba = clf.predict_proba(Xte)
        m = metrics_multiclass(yte, proba, np.array(classes))
    else:
        # LGBM gère class_weight="balanced" proprement
        clf = LGBMClassifier(
            objective="binary", n_estimators=600, learning_rate=0.05,
            max_depth=-1, num_leaves=31, subsample=0.8, colsample_bytree=0.8,
            reg_alpha=1e-3, reg_lambda=1e-2, class_weight="balanced",
            random_state=42, n_jobs=-1
        )
        clf.fit(Xtr, (ytr==binary_pos_label).astype(int))
        proba = clf.predict_proba(Xte)[:,1]
        m = metrics_binary((yte==binary_pos_label).astype(int), proba)
    return clf, m

def train_cat(Xtr, ytr, Xte, yte, multiclass=False, classes=None, binary_pos_label=1):
    if not have_cat:
        return None, {"ACC": np.nan}
    if multiclass:
        clf = CatBoostClassifier(
            iterations=1000, learning_rate=0.03, depth=6,
            loss_function="MultiClass", eval_metric="MultiClass",
            random_seed=42, verbose=False
        )
        clf.fit(Xtr, ytr)
        proba = clf.predict_proba(Xte)
        m = metrics_multiclass(yte, proba, np.array(classes))
    else:
        clf = CatBoostClassifier(
            iterations=800, learning_rate=0.05, depth=6,
            loss_function="Logloss", eval_metric="Logloss",
            random_seed=42, class_weights=[1.0, 1.0],  # ajustable
            verbose=False
        )
        clf.fit(Xtr, (ytr==binary_pos_label).astype(int))
        proba = clf.predict_proba(Xte)[:,1]
        m = metrics_binary((yte==binary_pos_label).astype(int), proba)
    return clf, m

# --- Main ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=DATASET_PATH, type=str, help="Chemin du parquet")
    ap.add_argument("--target",  default="y_dir_h", type=str, help="Colonne cible")
    ap.add_argument("--pivotq",  default=0.7, type=float, help="Quantile temps pour split")
    ap.add_argument("--models",  default="xgb,lgb,cat", type=str, help="Liste: xgb,lgb,cat")
    args = ap.parse_args()

    if not os.path.exists(args.dataset):
        print("[ERREUR] Dataset introuvable:", args.dataset); sys.exit(1)

    print("==> Chargement dataset:", args.dataset)
    df = pd.read_parquet(args.dataset)

    if args.target not in df.columns:
        print(f"[ERREUR] Target {args.target} absente. Colonnes y_* dispo:",
              [c for c in df.columns if c.startswith("y_")])
        sys.exit(2)

    # Crée X et y
    y = df[args.target].values
    X = drop_leak_cols(df, args.target)
    X = clean_features(X)

    # Détecte config binaire vs multiclasses
    classes = np.sort(np.unique(y[~pd.isna(y)]))
    multi = is_multiclass(y)
    
    # Remapper les classes pour XGBoost (qui s'attend à [0, 1, 2, ...])
    if multi and classes[0] < 0:
        print(f"   Remapping classes: {classes} -> {np.arange(len(classes))}")
        class_map = {old: new for old, new in zip(classes, np.arange(len(classes)))}
        y = np.array([class_map.get(val, val) for val in y])
        classes = np.arange(len(classes))

    # Split temporel
    mask_tr, mask_te, pivot_time = temporal_split(df, args.pivotq)
    Xtr, Xte = X[mask_tr], X[mask_te]
    ytr, yte = y[mask_tr], y[mask_te]

    print(f"==> Target: {args.target} | Classes: {classes.tolist()} | Multiclass={multi}")
    print("==> Split temporel:", f"train={mask_tr.sum()} test={mask_te.sum()} | pivot={pivot_time}")

    results = []
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    want = set([m.strip().lower() for m in args.models.split(",") if m.strip()])

    # XGBoost
    if "xgb" in want:
        print("… XGBoost")
        clf, metr = train_xgb(Xtr.values, ytr, Xte.values, yte, multiclass=multi, classes=classes)
        model_path = os.path.join(OUT_MODELS, f"{args.target}_xgb_{ts_tag}.json")
        try:
            clf.save_model(model_path)  # booster natif
        except Exception:
            import joblib; joblib.dump(clf, model_path.replace(".json",".pkl"))
        metr["model"] = "xgb"; results.append(metr)

    # LightGBM
    if "lgb" in want:
        print("… LightGBM")
        clf, metr = train_lgbm(Xtr.values, ytr, Xte.values, yte, multiclass=multi, classes=classes)
        if clf is not None:
            model_path = os.path.join(OUT_MODELS, f"{args.target}_lgb_{ts_tag}.pkl")
            try:
                import joblib; joblib.dump(clf, model_path)
            except Exception as e:
                print("[WARN] Sauvegarde LGBM:", e)
        metr["model"] = "lgb"; results.append(metr)

    # CatBoost
    if "cat" in want:
        print("… CatBoost")
        clf, metr = train_cat(Xtr.values, ytr, Xte.values, yte, multiclass=multi, classes=classes)
        if clf is not None:
            model_path = os.path.join(OUT_MODELS, f"{args.target}_cat_{ts_tag}.cbm")
            try:
                clf.save_model(model_path)
            except Exception as e:
                print("[WARN] Sauvegarde CatBoost:", e)
        metr["model"] = "cat"; results.append(metr)

    # Tableau comparatif
    df_res = pd.DataFrame(results)
    out_csv = os.path.join(OUT_RESULTS, f"metrics_{args.target}_{ts_tag}.csv")
    df_res.to_csv(out_csv, index=False, encoding="utf-8")
    print("\n==> Résultats\n", df_res)
    print("==> Sauvegardé:", out_csv)

if __name__ == "__main__":
    main()