#!/usr/bin/env python3
"""
Entraîne et sauvegarde les modèles T1 et T4 pour optimisation des seuils
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pickle
import logging
from typing import List, Tuple
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.preprocessing import StandardScaler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_and_prepare_data(data_path: str, test_dates: List[str]):
    """Charge et prépare les données"""
    df = pd.read_parquet(data_path)

    # Créer sl_ticks si nécessaire
    if 'stop' in df.columns and 'sl_ticks' not in df.columns:
        df['sl_ticks'] = abs(df['stop'] - df['entry_price']) * 4

    # Split train/test
    df_train = df[~df['date'].isin(test_dates)].copy()
    df_test = df[df['date'].isin(test_dates)].copy()

    return df_train, df_test


def get_features(df: pd.DataFrame):
    """Extrait les features ML"""
    # Exclure colonnes non-features
    exclude_cols = [
        'trade_id', 'symbol', 'date', 'entry_time', 'entry_idx', 'exit_idx',
        'direction', 'entry_price', 'exit_price', 'stop', 'target',
        'exit_reason', 'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
        'win', 'sl_ticks', 'pnl_ratio', 'quality_score', 'expected_value'
    ]

    feature_cols = [col for col in df.columns if col not in exclude_cols]
    X = df[feature_cols].copy()

    # Remplacer NaN
    X = X.fillna(0)

    # Remplacer inf
    X = X.replace([np.inf, -np.inf], 0)

    return X, feature_cols


def train_T1_binary_simple(df_train, df_test):
    """Entraîne T1: Binary Classification Simple"""
    logger.info("\n" + "="*70)
    logger.info("TRAINING T1_binary_simple")
    logger.info("="*70)

    # Générer target
    y_train = (df_train['pnl_ticks'] > 0).astype(int)
    y_test = (df_test['pnl_ticks'] > 0).astype(int)

    logger.info(f"   Train: {len(y_train):,} samples | WR={y_train.mean()*100:.1f}%")
    logger.info(f"   Test: {len(y_test):,} samples | WR={y_test.mean()*100:.1f}%")

    # Features
    X_train, feature_cols = get_features(df_train)
    X_test, _ = get_features(df_test)

    logger.info(f"   Features: {len(feature_cols)}")

    # Standardiser
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Convertir en DataFrame pour garder les noms
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_cols)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_cols)

    # Entraîner
    logger.info("\nTraining LGBMClassifier...")
    model = LGBMClassifier(
        objective='binary',
        num_leaves=100,
        max_depth=8,
        learning_rate=0.05,
        n_estimators=200,
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )

    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        eval_metric='binary_logloss',
        callbacks=[
            # LightGBM callbacks
        ]
    )

    # Prédictions
    y_pred_proba = model.predict_proba(X_test_scaled)
    y_pred = (y_pred_proba[:, 1] > 0.45).astype(int)

    accuracy = (y_pred == y_test).mean()
    logger.info(f"\n   Accuracy (0.45): {accuracy:.3f}")

    return model, scaler, feature_cols


def train_T4_pnl_ticks_capped(df_train, df_test):
    """Entraîne T4: Regression P&L Ticks Capped"""
    logger.info("\n" + "="*70)
    logger.info("TRAINING T4_pnl_ticks_capped")
    logger.info("="*70)

    # Générer target
    y_train = df_train['pnl_ticks'].clip(-20, +20)
    y_test = df_test['pnl_ticks'].clip(-20, +20)

    logger.info(f"   Train: {len(y_train):,} samples | Mean={y_train.mean():+.2f}t")
    logger.info(f"   Test: {len(y_test):,} samples | Mean={y_test.mean():+.2f}t")

    # Features
    X_train, feature_cols = get_features(df_train)
    X_test, _ = get_features(df_test)

    logger.info(f"   Features: {len(feature_cols)}")

    # Standardiser
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Convertir en DataFrame pour garder les noms
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_cols)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_cols)

    # Entraîner
    logger.info("\nTraining LGBMRegressor...")
    model = LGBMRegressor(
        objective='regression',
        num_leaves=100,
        max_depth=8,
        learning_rate=0.05,
        n_estimators=200,
        random_state=42,
        verbose=-1
    )

    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        eval_metric='rmse',
        callbacks=[]
    )

    # Prédictions
    y_pred = model.predict(X_test_scaled)
    mae = np.mean(np.abs(y_pred - y_test))
    logger.info(f"\n   MAE: {mae:.2f}t")

    return model, scaler, feature_cols


def save_model(model, scaler, feature_cols, output_path: str):
    """Sauvegarde le modèle"""
    data = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as f:
        pickle.dump(data, f)

    logger.info(f"\n   Modele sauvegarde: {output_path}")


def main():
    """Point d'entrée principal"""

    logger.info("\n" + "="*70)
    logger.info("TRAINING & SAVE MODELS T1 + T4")
    logger.info("="*70)

    # Configuration
    DATA_PATH = "ml/data/labeled_trades.parquet"
    TEST_DATES = ['20251113', '20251114']

    # Charger données
    logger.info(f"\nChargement: {DATA_PATH}")
    df_train, df_test = load_and_prepare_data(DATA_PATH, TEST_DATES)
    logger.info(f"   Train: {len(df_train):,} trades")
    logger.info(f"   Test: {len(df_test):,} trades")

    # Entraîner T1
    model_t1, scaler_t1, features_t1 = train_T1_binary_simple(df_train, df_test)
    save_model(model_t1, scaler_t1, features_t1, "ml/models/lightgbm_t1_binary_simple.pkl")

    # Entraîner T4
    model_t4, scaler_t4, features_t4 = train_T4_pnl_ticks_capped(df_train, df_test)
    save_model(model_t4, scaler_t4, features_t4, "ml/models/lightgbm_t4_pnl_ticks_capped.pkl")

    logger.info("\n" + "="*70)
    logger.info("TRAINING TERMINE")
    logger.info("="*70)
    logger.info("\nModeles sauvegardes:")
    logger.info("   ml/models/lightgbm_t1_binary_simple.pkl")
    logger.info("   ml/models/lightgbm_t4_pnl_ticks_capped.pkl")

    return 0


if __name__ == "__main__":
    sys.exit(main())
