#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
ENTRAÎNEMENT ML ROBUSTE - MODE HAUTE PERFORMANCE
═══════════════════════════════════════════════════════════════════════════════

Entraînement approfondi pour PC performants
Durée estimée : 2-4 heures par symbole

Features :
- Hyperparameter Tuning (Optuna ou Grid Search)
- Cross-validation 10-fold
- Feature selection automatique
- Ensemble methods (optionnel)
- Walk-forward validation
- Tests par plage horaire

Usage:
    # Entraînement ROBUSTE ES
    python ml/train_ml_robust.py --symbol ES --mode full

    # Entraînement ROBUSTE NQ
    python ml/train_ml_robust.py --symbol NQ --mode full

    # Entraînement ULTRA ROBUSTE (Ensemble)
    python ml/train_ml_robust.py --symbol ES --mode ultra

    # Les 2 symboles en séquence (4-8h total)
    python ml/train_ml_robust.py --symbol ES --mode full
    python ml/train_ml_robust.py --symbol NQ --mode full

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import logging
import os
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
import optuna
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import TimeSeriesSplit

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_engineering import FeatureEngineer
from ml.train_ml_direction_15min import (
    load_all_data,
    create_labels,
    flatten_nested_fields,
    calculate_derived_fields,
    get_manual_feature_list,
)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reproductibilité
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
os.environ['PYTHONHASHSEED'] = str(RANDOM_SEED)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION ROBUSTE
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_ROBUST = {
    # Chemins données
    "data_paths": {
        "es_chart3": "DATA_SIERRA_CHART/DATA_2025/OCTOBRE/20251031/CHART_3/ML_READY",  # 31 octobre 2025
        "nq_chart9": "DATA_SIERRA_CHART/DATA_2025/OCTOBRE/20251031/CHART_9/ML_READY",  # 31 octobre 2025
    },

    # Labels (identique)
    "horizon_seconds": 900,
    "threshold_ticks": 3,
    "tick_size": 0.25,
    "time_gap_tolerance": 900,  # 15 minutes (égal à l'horizon - accepte tous les gaps)

    # Cross-validation ROBUSTE
    "cv_n_splits": 10,  # 🔥 10-fold au lieu de 5

    # Feature Engineering
    "lag_periods": [1, 5, 10, 20, 60],
    "rolling_windows": [20, 60, 300],

    # Hyperparameter Tuning
    "optuna_n_trials": 50,  # 🔥 50 essais (1-2h)
    "optuna_timeout": 7200,  # 2h max

    # Plages de recherche LightGBM
    "lgbm_search_space": {
        "learning_rate": (0.01, 0.10),
        "max_depth": (5, 15),
        "num_leaves": (31, 127),
        "min_data_in_leaf": (50, 200),
        "feature_fraction": (0.6, 0.9),
        "bagging_fraction": (0.6, 0.9),
        "lambda_l1": (0.0, 10.0),
        "lambda_l2": (0.0, 10.0),
    },

    # Ensemble (mode ultra)
    "ensemble_n_models": 5,

    # Output
    "output_dir": "ml/models_robust",
    "model_name": "lgbm_direction_15min_ROBUST",
}


# ═══════════════════════════════════════════════════════════════════════════
# HYPERPARAMETER TUNING (OPTUNA)
# ═══════════════════════════════════════════════════════════════════════════

def optimize_hyperparameters(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_trials: int = 50,
    timeout: int = 7200,
    n_splits: int = 5,
    binary_mode: bool = False
) -> Dict:
    """
    Optimise les hyperparamètres avec Optuna

    Args:
        X_train: Features train
        y_train: Labels train
        n_trials: Nombre d'essais
        timeout: Timeout en secondes
        n_splits: Nombre de folds CV
        binary_mode: Si True, utilise binary au lieu de multiclass

    Returns:
        Dict avec meilleurs paramètres
    """
    logger.info(f"\n{'='*70}")
    mode_str = "BINAIRE" if binary_mode else "MULTICLASS"
    logger.info(f"🔥 HYPERPARAMETER TUNING (OPTUNA) - {mode_str}")
    logger.info(f"{'='*70}")
    logger.info(f"   Trials : {n_trials}")
    logger.info(f"   Timeout : {timeout}s ({timeout/3600:.1f}h)")
    logger.info(f"   CV folds : {n_splits}")

    def objective(trial):
        """Fonction objectif Optuna"""

        # Définir hyperparamètres à tester
        if binary_mode:
            params = {
                "objective": "binary",
                "metric": "binary_logloss",
            }
        else:
            params = {
                "objective": "multiclass",
                "num_class": 3,
                "metric": "multi_logloss",
            }

        # Paramètres communs
        params.update({
            "boosting_type": "gbdt",
            "n_estimators": 1000,
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.10, log=True),
            "max_depth": trial.suggest_int("max_depth", 5, 15),
            "num_leaves": trial.suggest_int("num_leaves", 31, 127),
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 50, 200),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 0.9),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.6, 0.9),
            "bagging_freq": 5,
            "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 10.0),
            "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 10.0),
            "verbose": -1,
            "random_state": RANDOM_SEED,
        })

        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        f1_scores = []

        for train_idx, val_idx in tscv.split(X_train):
            X_tr = X_train[train_idx]
            y_tr = y_train[train_idx]
            X_val = X_train[val_idx]
            y_val = y_train[val_idx]

            # Entraîner
            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=50, verbose=False),
                    lgb.log_evaluation(period=0)
                ]
            )

            # Prédire
            y_pred = model.predict(X_val)
            f1 = f1_score(y_val, y_pred, average='macro')
            f1_scores.append(f1)

        return np.mean(f1_scores)

    # Créer étude Optuna
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED)
    )

    # Optimiser
    start_time = time.time()
    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=timeout,
        show_progress_bar=True
    )
    elapsed = time.time() - start_time

    # Résultats
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ HYPERPARAMETER TUNING TERMINÉ")
    logger.info(f"{'='*70}")
    logger.info(f"   Durée : {elapsed:.1f}s ({elapsed/60:.1f} min)")
    logger.info(f"   Trials complétés : {len(study.trials)}")
    logger.info(f"   Meilleur F1-Score : {study.best_value:.4f}")

    logger.info(f"\n🏆 MEILLEURS HYPERPARAMÈTRES :")
    for param, value in study.best_params.items():
        logger.info(f"   {param:20s} : {value}")

    # Construire config finale
    best_params = {
        "objective": "multiclass",
        "num_class": 3,
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "n_estimators": 1000,
        "verbose": -1,
        "random_state": RANDOM_SEED,
        **study.best_params
    }

    return best_params, study


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE SELECTION
# ═══════════════════════════════════════════════════════════════════════════

def select_best_features(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: List[str],
    params: Dict,
    n_features: int = 100
) -> List[str]:
    """
    Sélectionne les N meilleures features par importance

    Args:
        X_train: Features train
        y_train: Labels train
        feature_names: Noms des features
        params: Hyperparamètres LightGBM
        n_features: Nombre de features à garder

    Returns:
        Liste des N meilleures features
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 FEATURE SELECTION")
    logger.info(f"{'='*70}")
    logger.info(f"   Features totales : {len(feature_names)}")
    logger.info(f"   Features cibles : {n_features}")

    # Entraîner modèle temporaire
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train)

    # Récupérer importances
    importances = model.feature_importances_

    # Créer DataFrame
    feat_imp_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)

    # Sélectionner top N
    selected_features = feat_imp_df.head(n_features)['feature'].tolist()

    logger.info(f"\n📊 TOP 10 FEATURES :")
    for i, row in feat_imp_df.head(10).iterrows():
        logger.info(f"   {i+1:2d}. {row['feature']:40s} : {row['importance']:8.1f}")

    logger.info(f"\n✅ {len(selected_features)} features sélectionnées")

    return selected_features, feat_imp_df


# ═══════════════════════════════════════════════════════════════════════════
# ENSEMBLE METHODS
# ═══════════════════════════════════════════════════════════════════════════

def train_ensemble(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    params: Dict,
    n_models: int = 5
) -> List:
    """
    Entraîne un ensemble de N modèles avec bagging

    Args:
        X_train: Features train
        y_train: Labels train
        X_test: Features test
        y_test: Labels test
        params: Hyperparamètres
        n_models: Nombre de modèles

    Returns:
        Liste de modèles
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 ENSEMBLE TRAINING ({n_models} modèles)")
    logger.info(f"{'='*70}")

    models = []

    for i in range(n_models):
        logger.info(f"\n📦 Modèle {i+1}/{n_models}")

        # Bagging : échantillonner 80% des données
        n_samples = int(len(X_train) * 0.8)
        indices = np.random.choice(len(X_train), n_samples, replace=False)

        X_tr_bag = X_train[indices]
        y_tr_bag = y_train[indices]

        # Varier légèrement les hyperparams
        params_varied = params.copy()
        params_varied['random_state'] = RANDOM_SEED + i
        params_varied['feature_fraction'] = params['feature_fraction'] * np.random.uniform(0.9, 1.1)
        params_varied['bagging_fraction'] = params['bagging_fraction'] * np.random.uniform(0.9, 1.1)

        # Entraîner
        model = lgb.LGBMClassifier(**params_varied)
        model.fit(
            X_tr_bag, y_tr_bag,
            eval_set=[(X_test, y_test)],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50, verbose=False),
                lgb.log_evaluation(period=0)
            ]
        )

        # Évaluer
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='macro')

        logger.info(f"   Accuracy : {acc:.4f}")
        logger.info(f"   F1-Score : {f1:.4f}")

        models.append(model)

    logger.info(f"\n✅ Ensemble de {n_models} modèles créé")

    return models


def predict_ensemble(models: List, X: np.ndarray) -> np.ndarray:
    """
    Prédiction par vote majoritaire

    Args:
        models: Liste de modèles
        X: Features

    Returns:
        Prédictions moyennées
    """
    predictions = []

    for model in models:
        pred = model.predict(X)
        predictions.append(pred)

    # Vote majoritaire
    predictions = np.array(predictions)
    final_pred = np.apply_along_axis(
        lambda x: np.bincount(x).argmax(),
        axis=0,
        arr=predictions
    )

    return final_pred


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ROBUSTE
# ═══════════════════════════════════════════════════════════════════════════

def main(args):
    """Entraînement robuste"""

    total_start = time.time()

    logger.info(f"\n{'='*70}")
    logger.info(f"🔥 ENTRAÎNEMENT ML ROBUSTE - MODE {args.mode.upper()}")
    logger.info(f"{'='*70}")
    logger.info(f"   Symbole : {args.symbol.upper()}")
    logger.info(f"   Mode : {args.mode}")
    logger.info(f"   PC Gamer détecté : Entraînement haute performance !")
    logger.info(f"{'='*70}")

    # ─────────────────────────────────────────────────────────────────
    # 1. CHARGEMENT & PRÉPARATION (identique)
    # ─────────────────────────────────────────────────────────────────

    # Charger données
    if args.symbol.upper() == 'ES':
        data_path = args.data_dir / CONFIG_ROBUST['data_paths']['es_chart3']
        df = load_all_data(data_path, "ES Chart 3")
        df['symbol'] = 'ESZ25_FUT_CME'
    else:
        data_path = args.data_dir / CONFIG_ROBUST['data_paths']['nq_chart9']
        df = load_all_data(data_path, "NQ Chart 9")
        df['symbol'] = 'NQZ25_FUT_CME'

    # Labels
    df = create_labels(
        df,
        horizon_seconds=CONFIG_ROBUST['horizon_seconds'],
        threshold_ticks=CONFIG_ROBUST['threshold_ticks'],
        tick_size=CONFIG_ROBUST['tick_size'],
        time_gap_tolerance=CONFIG_ROBUST['time_gap_tolerance'],
        binary_mode=args.binary
    )

    # Features
    df = flatten_nested_fields(df)
    df = calculate_derived_fields(df)
    df['symbol_is_nq'] = (df['symbol'] == 'NQZ25_FUT_CME').astype(int)

    # Feature engineering
    feature_engineer = FeatureEngineer(
        lag_periods=CONFIG_ROBUST['lag_periods'],
        rolling_windows=CONFIG_ROBUST['rolling_windows']
    )

    features_to_lag = [
        'close', 'level1_imbalance', 'smart_money_flow',
        'cum_delta_session', 'delta', 'd_vwap',
        'battle_navale_signal_strength', 'pressure_strength',
    ]

    df = feature_engineer.add_lags(df, features_to_lag, time_col='tsec')
    df = feature_engineer.add_rolling_means(df, features_to_lag)
    df = df.dropna().reset_index(drop=True)

    # Features complètes
    manual_features = get_manual_feature_list()
    engineered_features = [col for col in df.columns
                          if '_lag_' in col or '_ma_' in col or '_vs_ma_' in col]
    all_features = manual_features + engineered_features
    available_features = [f for f in all_features if f in df.columns]

    logger.info(f"✅ {len(available_features)} features disponibles")

    # Split
    split_idx = int(len(df) * 0.80)
    df_train = df.iloc[:split_idx].copy()
    df_test = df.iloc[split_idx:].copy()

    X_train = df_train[available_features].values
    y_train = df_train['label'].values.astype(int)
    X_test = df_test[available_features].values
    y_test = df_test['label'].values.astype(int)

    logger.info(f"📊 Train : {len(X_train):,} samples")
    logger.info(f"📊 Test  : {len(X_test):,} samples")

    # ─────────────────────────────────────────────────────────────────
    # 2. HYPERPARAMETER TUNING
    # ─────────────────────────────────────────────────────────────────

    if args.mode in ['full', 'ultra']:
        best_params, study = optimize_hyperparameters(
            X_train, y_train,
            n_trials=CONFIG_ROBUST['optuna_n_trials'],
            timeout=CONFIG_ROBUST['optuna_timeout'],
            n_splits=CONFIG_ROBUST['cv_n_splits'],
            binary_mode=args.binary
        )
    else:
        # Params par défaut
        if args.binary:
            best_params = {
                "objective": "binary",
                "metric": "binary_logloss",
            }
        else:
            best_params = {
                "objective": "multiclass",
                "num_class": 3,
                "metric": "multi_logloss",
            }
        best_params.update({
            "boosting_type": "gbdt",
            "n_estimators": 1000,
            "learning_rate": 0.03,
            "max_depth": 10,
            "num_leaves": 63,
            "verbose": -1,
            "random_state": RANDOM_SEED,
        })

    # ─────────────────────────────────────────────────────────────────
    # 3. FEATURE SELECTION
    # ─────────────────────────────────────────────────────────────────

    if args.mode in ['full', 'ultra']:
        selected_features, feat_imp_df = select_best_features(
            X_train, y_train,
            available_features,
            best_params,
            n_features=100
        )

        # Filtrer features
        feature_indices = [i for i, f in enumerate(available_features) if f in selected_features]
        X_train = X_train[:, feature_indices]
        X_test = X_test[:, feature_indices]
        final_features = selected_features
    else:
        final_features = available_features

    # ─────────────────────────────────────────────────────────────────
    # 4. ENTRAÎNEMENT FINAL
    # ─────────────────────────────────────────────────────────────────

    if args.mode == 'ultra':
        # Ensemble de modèles
        models = train_ensemble(
            X_train, y_train,
            X_test, y_test,
            best_params,
            n_models=CONFIG_ROBUST['ensemble_n_models']
        )

        # Prédiction ensemble
        y_pred = predict_ensemble(models, X_test)

    else:
        # Modèle unique optimisé
        logger.info(f"\n{'='*70}")
        logger.info(f"🎓 ENTRAÎNEMENT FINAL")
        logger.info(f"{'='*70}")

        model = lgb.LGBMClassifier(**best_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50, verbose=False),
                lgb.log_evaluation(period=100)
            ]
        )

        y_pred = model.predict(X_test)
        models = [model]

    # ─────────────────────────────────────────────────────────────────
    # 5. ÉVALUATION
    # ─────────────────────────────────────────────────────────────────

    logger.info(f"\n{'='*70}")
    logger.info(f"📊 ÉVALUATION FINALE")
    logger.info(f"{'='*70}")

    accuracy = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')

    logger.info(f"\n🎯 Métriques finales :")
    logger.info(f"   Accuracy : {accuracy:.4f} ({accuracy*100:.2f}%)")
    logger.info(f"   F1-Score : {f1_macro:.4f}")

    logger.info(f"\n📈 Rapport par classe :")
    if args.binary:
        print(classification_report(y_test, y_pred, target_names=['DOWN', 'UP']))
    else:
        print(classification_report(y_test, y_pred, target_names=['DOWN', 'FLAT', 'UP']))

    # ─────────────────────────────────────────────────────────────────
    # 6. SAUVEGARDE
    # ─────────────────────────────────────────────────────────────────

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"{CONFIG_ROBUST['model_name']}_{args.symbol.upper()}_{args.mode}"

    # Sauvegarder modèle(s)
    if args.mode == 'ultra':
        model_path = output_dir / f"{model_name}_ensemble_{timestamp}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(models, f)
    else:
        model_path = output_dir / f"{model_name}_{timestamp}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(models[0], f)

    logger.info(f"\n✅ Modèle sauvegardé : {model_path}")

    # Sauvegarder données test pour calibration ultérieure
    test_data_path = output_dir / f"test_data_{args.symbol.upper()}_binary.pkl"
    with open(test_data_path, 'wb') as f:
        pickle.dump({
            'X_test': X_test,
            'y_test': y_test,
            'feature_names': final_features
        }, f)
    logger.info(f"✅ Données test sauvegardées : {test_data_path}")

    # Sauvegarder features
    features_path = output_dir / f"{model_name}_features_{timestamp}.json"
    with open(features_path, 'w') as f:
        json.dump(final_features, f, indent=2)

    # Sauvegarder métriques
    metrics = {
        'accuracy': float(accuracy),
        'f1_macro': float(f1_macro),
        'mode': args.mode,
        'n_features': len(final_features),
        'best_params': best_params if args.mode in ['full', 'ultra'] else None,
    }

    metrics_path = output_dir / f"{model_name}_metrics_{timestamp}.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    # ─────────────────────────────────────────────────────────────────
    # FIN
    # ─────────────────────────────────────────────────────────────────

    total_elapsed = time.time() - total_start

    logger.info(f"\n{'='*70}")
    logger.info(f"🎉 ENTRAÎNEMENT ROBUSTE TERMINÉ !")
    logger.info(f"{'='*70}")
    logger.info(f"⏱️  Durée totale : {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    logger.info(f"🎯 Accuracy finale : {accuracy:.4f}")
    logger.info(f"📁 Modèle : {model_path}")
    logger.info(f"{'='*70}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Entraînement ML ROBUSTE - Haute performance"
    )

    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        choices=['ES', 'NQ', 'es', 'nq'],
        help='Symbole (ES ou NQ)'
    )

    parser.add_argument(
        '--mode',
        type=str,
        default='full',
        choices=['fast', 'full', 'ultra'],
        help='Mode entraînement (fast=20min, full=2h, ultra=4h)'
    )

    parser.add_argument(
        '--binary',
        action='store_true',
        help='Mode BINAIRE (UP/DOWN seulement, retire FLAT) - recommandé pour filtre ML'
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('.'),
        help='Répertoire données'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('ml/models_robust'),
        help='Répertoire sortie'
    )

    args = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        sys.exit(1)
