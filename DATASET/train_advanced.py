# train_advanced.py
# -*- coding: utf-8 -*-
"""
Entraînement avancé avec XGBoost + LightGBM + CatBoost
Basé sur les recommandations ChatGPT pour données financières
"""

import os
import sys
import warnings
import pickle
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    average_precision_score, matthews_corrcoef
)
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

# === CONFIG =============================================================
DATASET_PATH = r"D:\MIA_IA_system\DATASET\dataset_20251002_20251003.parquet"
OUTPUT_DIR = r"D:\MIA_IA_system\DATASET\models_advanced"
RESULTS_DIR = r"D:\MIA_IA_system\DATASET\results_advanced"

# Configuration des modèles (recommandations ChatGPT)
XGB_PARAMS = {
    'n_estimators': 400,
    'max_depth': 5,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 1e-3,
    'reg_lambda': 1e-2,
    'random_state': 42,
    'n_jobs': -1,
    'tree_method': 'hist',
    'eval_metric': 'logloss'
}

LGB_PARAMS = {
    'objective': 'binary',
    'metric': 'binary_logloss',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_data_in_leaf': 20,
    'min_sum_hessian_in_leaf': 1e-3,
    'lambda_l1': 1e-3,
    'lambda_l2': 1e-2,
    'random_state': 42,
    'n_jobs': -1,
    'verbose': -1
}

CATBOOST_PARAMS = {
    'iterations': 1000,
    'learning_rate': 0.03,
    'depth': 6,
    'l2_leaf_reg': 3,
    'bootstrap_type': 'Bayesian',
    'random_strength': 1,
    'bagging_temperature': 1,
    'od_type': 'Iter',
    'od_wait': 20,
    'random_seed': 42,
    'verbose': False
}

# Targets prioritaires (recommandations ChatGPT)
PRIORITY_TARGETS = {
    'y_dir_h': 'Direction H=5 (3 classes)',
    'y_touch_vwap': 'Touch VWAP H=5 (binaire)',
    'y_touch_up1': 'Touch VWAP+1σ H=5 (binaire)',
    'y_touch_dn1': 'Touch VWAP-1σ H=5 (binaire)'
}

# === OUTILS =============================================================

def load_dataset(path: str) -> pd.DataFrame:
    """Charge le dataset depuis Parquet ou CSV"""
    if not os.path.exists(path):
        csv_path = path.replace(".parquet", ".csv")
        if os.path.exists(csv_path):
            print(f"Chargement CSV: {csv_path}")
            return pd.read_csv(csv_path)
        else:
            raise FileNotFoundError(f"Dataset non trouvé: {path}")
    
    print(f"Chargement Parquet: {path}")
    return pd.read_parquet(path)

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Prépare les features pour l'entraînement"""
    # Colonnes à exclure
    exclude_cols = [
        'ts', 'sym', 'c_fwd', 'hi_win', 'lo_win', 'ret_h',  # Métadonnées et futures
        '_source_file'  # Debug
    ]
    
    # Colonnes de labels
    label_cols = [col for col in df.columns if col.startswith('y_')]
    
    # Features disponibles
    feature_cols = [col for col in df.columns 
                   if col not in exclude_cols and col not in label_cols]
    
    # Sélectionner les features non manquantes
    X = df[feature_cols].copy()
    
    # Gérer les valeurs manquantes
    numeric_cols = X.select_dtypes(include=[np.number]).columns
    X[numeric_cols] = X[numeric_cols].fillna(0)
    
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns
    X[categorical_cols] = X[categorical_cols].fillna('unknown')
    
    print(f"✅ Features préparées: {X.shape[1]} colonnes")
    print(f"📊 Lignes: {X.shape[0]}")
    
    return X, feature_cols

def temporal_split(df: pd.DataFrame, test_ratio: float = 0.3) -> Tuple[np.ndarray, np.ndarray]:
    """Split temporel basé sur les timestamps"""
    if 'ts' not in df.columns:
        n_samples = len(df)
        split_idx = int(n_samples * (1 - test_ratio))
        train_idx = np.arange(split_idx)
        test_idx = np.arange(split_idx, n_samples)
        return train_idx, test_idx
    
    df_sorted = df.sort_values('ts')
    split_time = df_sorted['ts'].quantile(1 - test_ratio)
    
    train_mask = df_sorted['ts'] < split_time
    test_mask = df_sorted['ts'] >= split_time
    
    train_idx = df_sorted[train_mask].index.values
    test_idx = df_sorted[test_mask].index.values
    
    print(f"📅 Split temporel:")
    print(f"  Train: {len(train_idx)} échantillons")
    print(f"  Test: {len(test_idx)} échantillons")
    print(f"  Ratio test: {len(test_idx) / len(df):.1%}")
    
    return train_idx, test_idx

def calculate_scale_pos_weight(y_train: pd.Series) -> float:
    """Calcule scale_pos_weight pour gérer le déséquilibre des classes"""
    if len(y_train.unique()) == 2:
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        if pos_count > 0:
            return neg_count / pos_count
    return 1.0

def train_xgboost(X_train: pd.DataFrame, y_train: pd.Series, 
                  X_test: pd.DataFrame, y_test: pd.Series, target_name: str) -> Dict[str, Any]:
    """Entraîne un modèle XGBoost avec calibration"""
    print(f"🌳 Entraînement XGBoost pour {target_name}...")
    
    # Adapter les paramètres selon le type de problème
    params = XGB_PARAMS.copy()
    if len(y_train.unique()) == 2:
        params['objective'] = 'binary:logistic'
        params['eval_metric'] = 'logloss'
        params['scale_pos_weight'] = calculate_scale_pos_weight(y_train)
    else:
        params['objective'] = 'multi:softprob'
        params['eval_metric'] = 'mlogloss'
        params['num_class'] = len(y_train.unique())
    
    # Entraînement
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train)
    
    # Calibration des probabilités
    calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv=3)
    calibrated_model.fit(X_train, y_train)
    
    # Prédictions
    y_pred = calibrated_model.predict(X_test)
    y_pred_proba = calibrated_model.predict_proba(X_test)
    
    return {
        'model': calibrated_model,
        'model_name': 'XGBoost',
        'y_pred': y_pred,
        'y_pred_proba': y_pred_proba,
        'params': params
    }

def train_lightgbm(X_train: pd.DataFrame, y_train: pd.Series, 
                   X_test: pd.DataFrame, y_test: pd.Series, target_name: str) -> Dict[str, Any]:
    """Entraîne un modèle LightGBM avec calibration"""
    print(f"💡 Entraînement LightGBM pour {target_name}...")
    
    # Adapter les paramètres
    params = LGB_PARAMS.copy()
    if len(y_train.unique()) == 2:
        params['objective'] = 'binary'
        params['metric'] = 'binary_logloss'
        params['scale_pos_weight'] = calculate_scale_pos_weight(y_train)
    else:
        params['objective'] = 'multiclass'
        params['metric'] = 'multi_logloss'
        params['num_class'] = len(y_train.unique())
    
    # Entraînement
    train_data = lgb.Dataset(X_train, label=y_train)
    model = lgb.train(params, train_data, num_boost_round=400, verbose_eval=False)
    
    # Wrapper pour compatibilité sklearn
    class LightGBMWrapper:
        def __init__(self, model):
            self.model = model
            self.classes_ = np.unique(y_train)
        
        def predict(self, X):
            pred = self.model.predict(X)
            if len(self.classes_) == 2:
                return (pred > 0.5).astype(int)
            else:
                return np.argmax(pred, axis=1)
        
        def predict_proba(self, X):
            pred = self.model.predict(X)
            if len(self.classes_) == 2:
                return np.column_stack([1-pred, pred])
            else:
                return pred
    
    wrapper = LightGBMWrapper(model)
    
    # Calibration
    calibrated_model = CalibratedClassifierCV(wrapper, method='isotonic', cv=3)
    calibrated_model.fit(X_train, y_train)
    
    # Prédictions
    y_pred = calibrated_model.predict(X_test)
    y_pred_proba = calibrated_model.predict_proba(X_test)
    
    return {
        'model': calibrated_model,
        'model_name': 'LightGBM',
        'y_pred': y_pred,
        'y_pred_proba': y_pred_proba,
        'params': params
    }

def train_catboost(X_train: pd.DataFrame, y_train: pd.Series, 
                   X_test: pd.DataFrame, y_test: pd.Series, target_name: str) -> Dict[str, Any]:
    """Entraîne un modèle CatBoost avec calibration"""
    print(f"🐱 Entraînement CatBoost pour {target_name}...")
    
    # Adapter les paramètres
    params = CATBOOST_PARAMS.copy()
    if len(y_train.unique()) == 2:
        params['loss_function'] = 'Logloss'
        params['scale_pos_weight'] = calculate_scale_pos_weight(y_train)
    else:
        params['loss_function'] = 'MultiClass'
        params['classes_count'] = len(y_train.unique())
    
    # Entraînement
    model = CatBoostClassifier(**params)
    model.fit(X_train, y_train, eval_set=(X_test, y_test), verbose=False)
    
    # Calibration
    calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv=3)
    calibrated_model.fit(X_train, y_train)
    
    # Prédictions
    y_pred = calibrated_model.predict(X_test)
    y_pred_proba = calibrated_model.predict_proba(X_test)
    
    return {
        'model': calibrated_model,
        'model_name': 'CatBoost',
        'y_pred': y_pred,
        'y_pred_proba': y_pred_proba,
        'params': params
    }

def calculate_metrics(y_test: pd.Series, y_pred: np.ndarray, y_pred_proba: np.ndarray, 
                     target_name: str) -> Dict[str, float]:
    """Calcule toutes les métriques recommandées par ChatGPT"""
    metrics = {}
    
    # Métriques de base
    if len(y_test.unique()) == 2:
        # Classification binaire
        metrics['auc'] = roc_auc_score(y_test, y_pred_proba[:, 1])
        metrics['ap'] = average_precision_score(y_test, y_pred_proba[:, 1])
        metrics['mcc'] = matthews_corrcoef(y_test, y_pred)
    else:
        # Classification multi-classes
        metrics['auc'] = roc_auc_score(y_test, y_pred_proba, multi_class='ovr', average='macro')
        metrics['ap'] = average_precision_score(y_test, y_pred_proba, average='macro')
        metrics['mcc'] = matthews_corrcoef(y_test, y_pred)
    
    # Rapport de classification
    report = classification_report(y_test, y_pred, output_dict=True)
    metrics['classification_report'] = report
    
    # Matrice de confusion
    metrics['confusion_matrix'] = confusion_matrix(y_test, y_pred)
    
    return metrics

def create_ensemble_predictions(all_results: Dict[str, Dict]) -> Dict[str, Any]:
    """Crée des prédictions d'ensemble (moyenne des probabilités)"""
    ensemble_results = {}
    
    for target_name, models_results in all_results.items():
        if len(models_results) >= 2:
            # Moyenne des probabilités
            proba_avg = np.mean([result['y_pred_proba'] for result in models_results.values()], axis=0)
            
            # Prédiction finale
            if proba_avg.shape[1] == 2:
                pred_avg = (proba_avg[:, 1] > 0.5).astype(int)
            else:
                pred_avg = np.argmax(proba_avg, axis=1)
            
            ensemble_results[target_name] = {
                'model_name': 'Ensemble',
                'y_pred': pred_avg,
                'y_pred_proba': proba_avg
            }
    
    return ensemble_results

def save_advanced_results(all_results: Dict[str, Dict], output_dir: str):
    """Sauvegarde tous les résultats avancés"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder les modèles
    models_dir = os.path.join(output_dir, "models")
    Path(models_dir).mkdir(exist_ok=True)
    
    # Rapport global
    report_path = os.path.join(output_dir, "advanced_training_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAPPORT D'ENTRAÎNEMENT AVANCÉ - MIA IA SYSTEM\n")
        f.write("Recommandations ChatGPT: XGBoost + LightGBM + CatBoost\n")
        f.write("=" * 80 + "\n\n")
        
        for target_name, models_results in all_results.items():
            f.write(f"🎯 {target_name}\n")
            f.write("-" * 40 + "\n")
            
            for model_name, results in models_results.items():
                if 'metrics' in results:
                    metrics = results['metrics']
                    f.write(f"  {model_name}:\n")
                    f.write(f"    AUC: {metrics['auc']:.3f}\n")
                    f.write(f"    AP: {metrics['ap']:.3f}\n")
                    f.write(f"    MCC: {metrics['mcc']:.3f}\n")
            
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("Rapport généré le: " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write("=" * 80 + "\n")

def main():
    """Fonction principale d'entraînement avancé"""
    print("🚀 ENTRAÎNEMENT AVANCÉ - MIA IA SYSTEM")
    print("Recommandations ChatGPT: XGBoost + LightGBM + CatBoost")
    print("=" * 60)
    
    try:
        # Chargement du dataset
        print("📁 Chargement du dataset...")
        df = load_dataset(DATASET_PATH)
        print(f"✅ Dataset chargé: {df.shape}")
        
        # Préparation des features
        print("🔧 Préparation des features...")
        X, feature_cols = prepare_features(df)
        
        # Split temporel
        print("📅 Split temporel...")
        train_idx, test_idx = temporal_split(df, test_ratio=0.3)
        
        # Entraînement pour chaque target prioritaire
        all_results = {}
        available_targets = [col for col in PRIORITY_TARGETS.keys() if col in df.columns]
        
        print(f"🎯 Targets prioritaires: {available_targets}")
        
        for target in available_targets:
            if target in df.columns:
                y = df[target].dropna()
                if len(y) > 100:
                    # Aligner X et y
                    common_idx = X.index.intersection(y.index)
                    X_aligned = X.loc[common_idx]
                    y_aligned = y.loc[common_idx]
                    
                    # Réajuster les indices
                    train_idx_aligned = [i for i in train_idx if i in common_idx]
                    test_idx_aligned = [i for i in test_idx if i in common_idx]
                    
                    if len(train_idx_aligned) > 50 and len(test_idx_aligned) > 20:
                        X_train, X_test = X_aligned.iloc[train_idx_aligned], X_aligned.iloc[test_idx_aligned]
                        y_train, y_test = y_aligned.iloc[train_idx_aligned], y_aligned.iloc[test_idx_aligned]
                        
                        print(f"\n🎯 Entraînement pour {PRIORITY_TARGETS[target]}...")
                        print(f"📊 Train: {len(X_train)}, Test: {len(X_test)}")
                        
                        # Entraîner les 3 modèles
                        models_results = {}
                        
                        # XGBoost
                        xgb_results = train_xgboost(X_train, y_train, X_test, y_test, target)
                        xgb_results['metrics'] = calculate_metrics(y_test, xgb_results['y_pred'], 
                                                                 xgb_results['y_pred_proba'], target)
                        models_results['XGBoost'] = xgb_results
                        
                        # LightGBM
                        lgb_results = train_lightgbm(X_train, y_train, X_test, y_test, target)
                        lgb_results['metrics'] = calculate_metrics(y_test, lgb_results['y_pred'], 
                                                                 lgb_results['y_pred_proba'], target)
                        models_results['LightGBM'] = lgb_results
                        
                        # CatBoost
                        cat_results = train_catboost(X_train, y_train, X_test, y_test, target)
                        cat_results['metrics'] = calculate_metrics(y_test, cat_results['y_pred'], 
                                                                 cat_results['y_pred_proba'], target)
                        models_results['CatBoost'] = cat_results
                        
                        # Ensemble
                        ensemble_results = create_ensemble_predictions({target: models_results})
                        if target in ensemble_results:
                            ensemble_results[target]['metrics'] = calculate_metrics(y_test, 
                                ensemble_results[target]['y_pred'], 
                                ensemble_results[target]['y_pred_proba'], target)
                            models_results['Ensemble'] = ensemble_results[target]
                        
                        all_results[target] = models_results
                        
                        # Afficher les résultats
                        print(f"\n📊 Résultats pour {target}:")
                        for model_name, results in models_results.items():
                            if 'metrics' in results:
                                metrics = results['metrics']
                                print(f"  {model_name}: AUC={metrics['auc']:.3f}, AP={metrics['ap']:.3f}, MCC={metrics['mcc']:.3f}")
                    else:
                        print(f"⚠️ Pas assez d'échantillons pour {target}")
                else:
                    print(f"⚠️ Target {target} a trop peu d'échantillons: {len(y)}")
        
        # Sauvegarde des résultats
        print("\n💾 Sauvegarde des résultats...")
        save_advanced_results(all_results, RESULTS_DIR)
        
        # Résumé final
        print("\n🎉 ENTRAÎNEMENT AVANCÉ TERMINÉ!")
        print("=" * 60)
        for target, models_results in all_results.items():
            print(f"\n🎯 {target}:")
            for model_name, results in models_results.items():
                if 'metrics' in results:
                    metrics = results['metrics']
                    print(f"  ✅ {model_name}: AUC={metrics['auc']:.3f}, AP={metrics['ap']:.3f}, MCC={metrics['mcc']:.3f}")
        
        print(f"\n📁 Résultats sauvegardés dans: {RESULTS_DIR}")
        print("📊 Consultez le rapport détaillé pour les comparaisons.")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


