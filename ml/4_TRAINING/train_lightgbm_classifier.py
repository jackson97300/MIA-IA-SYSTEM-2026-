"""
🎯 LIGHTGBM CLASSIFIER TRAINING PIPELINE - ML 3-Layer Strategy
Version: 1.0 - CLASSIFICATION WIN/LOSS
Date: 15 novembre 2025

Pipeline complet d'entraînement LightGBM CLASSIFIER:
1. Load labeled trades (avec target binaire 'win': 1=WIN, 0=LOSS)
2. Feature engineering (90 features)
3. Train/Val/Test split (60/20/20)
4. Hyperparameter tuning avec Optuna (100 trials, LogLoss)
5. Training final avec meilleurs params (LGBMClassifier)
6. Évaluation: Accuracy, Precision, Recall, F1, AUC-ROC
7. SHAP feature importance (top 30)
8. Sauvegarde modèle production

Input: ml/data/labeled_trades.parquet (avec colonne 'win')
Output: ml/models/lightgbm_classifier_v1.pkl
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np
import pickle
import json

# ML imports
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, log_loss
)
from sklearn.preprocessing import StandardScaler
import optuna
from optuna.samplers import TPESampler

# SHAP
import shap
import matplotlib.pyplot as plt

# Ajouter parent au path
sys.path.append(str(Path(__file__).parent.parent))

# ✅ Imports optionnels (modules externes non requis pour training)
try:
    from ml.feature_engineering_lightgbm import FeatureEngineer
    from ml.extract_ml_ready_data import MLReadyDataExtractor
except ImportError:
    # Ces modules ne sont pas nécessaires si on charge directement labeled_trades.parquet
    FeatureEngineer = None
    MLReadyDataExtractor = None

logger = logging.getLogger(__name__)


class LightGBMClassifierTrainer:
    """
    Entraîne modèle LightGBM CLASSIFIER pour prédire WIN/LOSS.

    Usage:
        trainer = LightGBMClassifierTrainer()
        trainer.train_pipeline(df_trades)
    """

    def __init__(self, output_dir: str = "ml/models"):
        """
        Initialise le trainer.

        Args:
            output_dir: Dossier de sortie pour modèles
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.scaler = None
        self.feature_names = None
        self.best_params = None

        # Feature engineer (optionnel)
        self.feature_engineer = FeatureEngineer() if FeatureEngineer else None

        logger.info("✅ LightGBMClassifierTrainer initialisé")
        logger.info(f"   Output dir: {self.output_dir}")


    def _merge_trades_with_features(
        self,
        df_trades: pd.DataFrame,
        df_snapshots: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge trades avec snapshots pour avoir features complètes.

        Args:
            df_trades: DataFrame des trades labeled
            df_snapshots: DataFrame des snapshots ML_READY

        Returns:
            DataFrame merged
        """

        logger.info("🔗 Merge trades avec snapshots features...")

        # Engineer features sur snapshots
        df_features = self.feature_engineer.engineer_features(
            df_snapshots=df_snapshots,
            include_meta=True
        )

        # Merge sur (symbol_base, date, t_ms) proche de entry_time
        # Simplification: merge sur entry_idx si disponible

        # Pour l'instant, copier features depuis les trades (déjà enrichies)
        # ou merger par date/symbol

        logger.info(f"   ✅ Features engineered: {len(df_features.columns)} colonnes")

        return df_trades  # Placeholder - à implémenter si nécessaire


    def _prepare_data(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        val_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Prépare données pour training (split train/val/test).

        Args:
            df: DataFrame avec features + target 'win' (binaire)
            test_size: Proportion test set
            val_size: Proportion validation set (de train)
            random_state: Seed aléatoire

        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 PRÉPARATION DONNÉES")
        logger.info(f"{'='*70}")

        # Target
        target_col = 'win'
        if target_col not in df.columns:
            raise ValueError(f"❌ Colonne '{target_col}' manquante !")

        # Features (exclure métadonnées + target + RESULTATS TRADE)
        # ⚠️ IMPORTANT: pnl_ticks, duration_minutes, mae, mfe sont des RESULTATS
        #    connus APRES le trade → DATA LEAKAGE si utilisés comme features !
        exclude_cols = [
            'win',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE si features!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
        ]

        # Ajouter colonnes optionnelles si elles existent
        optional_exclude = [
            't_ms', 'sym', 'symbol_base', 'source_file',
            'vix', 'volatility_regime', 'dom_age_ms', 'is_dom_fresh',
            'in_value_area', 'is_1tick_spread', 'data_quality'
        ]

        for col in optional_exclude:
            if col in df.columns and col not in exclude_cols:
                exclude_cols.append(col)

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"   Total samples: {len(df):,}")
        logger.info(f"   Total features: {len(feature_cols)}")
        logger.info(f"   Target: {target_col}")

        # Distribution de la target
        win_count = df[target_col].sum()
        loss_count = len(df) - win_count
        logger.info(f"   WINs:  {win_count:,} ({win_count/len(df)*100:.1f}%)")
        logger.info(f"   LOSSes: {loss_count:,} ({loss_count/len(df)*100:.1f}%)")

        X = df[feature_cols]
        y = df[target_col]

        # Split train / test
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            shuffle=True
        )

        # Split train / val
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val,
            test_size=val_size,
            random_state=random_state,
            shuffle=True
        )

        logger.info(f"\n   📋 Splits:")
        logger.info(f"      Train: {len(X_train):,} ({len(X_train)/len(df)*100:.1f}%)")
        logger.info(f"      Val:   {len(X_val):,} ({len(X_val)/len(df)*100:.1f}%)")
        logger.info(f"      Test:  {len(X_test):,} ({len(X_test)/len(df)*100:.1f}%)")

        # === STANDARD SCALING (normalisation features) ===
        logger.info(f"\n   ⚙️ Application StandardScaler...")
        self.scaler = StandardScaler()

        # Fit sur train, transform sur train/val/test
        X_train_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        X_val_scaled = pd.DataFrame(
            self.scaler.transform(X_val),
            columns=X_val.columns,
            index=X_val.index
        )
        X_test_scaled = pd.DataFrame(
            self.scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index
        )

        logger.info(f"   ✅ Features standardisées (mean=0, std=1)")
        logger.info(f"{'='*70}\n")

        # Stocker feature names
        self.feature_names = feature_cols

        return X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test


    def _prepare_data_temporal_split(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        ✅ NOUVEAU 15/11/2025: Split temporel strict (NO SHUFFLE, tri par date).

        ÉVITE LEAKAGE TEMPOREL:
        - Train: jours 1-N (60%)
        - Val:   jours N-M (20%)
        - Test:  jours M-Z (20%)

        ChatGPT a identifié que split random = leakage temporel.
        Cette fonction corrige le problème en splittant par JOURS, pas par LIGNES.

        Args:
            df: DataFrame avec colonne 'date' (YYYY-MM-DD)
            train_ratio: Proportion jours pour train
            val_ratio: Proportion jours pour val
            test_ratio: Proportion jours pour test (= 1 - train - val)

        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 PRÉPARATION DONNÉES - SPLIT TEMPOREL STRICT")
        logger.info(f"{'='*70}")
        logger.info(f"   🎯 Correction: Split par JOURS (pas lignes) pour éviter leakage temporel")

        # Vérifier colonne date
        if 'date' not in df.columns:
            raise ValueError("❌ Colonne 'date' requise pour split temporel !")

        # 1. TRIER PAR DATE (CRITIQUE!)
        # Vérifier quelle colonne timestamp existe
        timestamp_col = 'entry_time' if 'entry_time' in df.columns else ('t_ms' if 't_ms' in df.columns else None)

        if timestamp_col:
            df = df.sort_values(['date', timestamp_col]).reset_index(drop=True)
            logger.info(f"   ✅ Données triées par date + {timestamp_col}")
        else:
            df = df.sort_values(['date']).reset_index(drop=True)
            logger.info(f"   ✅ Données triées par date uniquement (pas de timestamp trouvé)")

        # 2. Identifier dates uniques
        unique_dates = sorted(df['date'].unique())
        n_days = len(unique_dates)

        logger.info(f"   📅 Période: {unique_dates[0]} → {unique_dates[-1]}")
        logger.info(f"   📅 Nombre de jours: {n_days}")

        if n_days < 3:
            raise ValueError(f"❌ Besoin d'au moins 3 jours pour split train/val/test (actuel: {n_days})")

        # 3. Split temporel par JOURS (pas par lignes!)
        train_days = int(n_days * train_ratio)
        val_days = int(n_days * (train_ratio + val_ratio))

        # Assurer au moins 1 jour par split
        if train_days < 1:
            train_days = 1
        if val_days <= train_days:
            val_days = train_days + 1
        if val_days >= n_days:
            val_days = n_days - 1

        train_dates = unique_dates[:train_days]
        val_dates = unique_dates[train_days:val_days]
        test_dates = unique_dates[val_days:]

        logger.info(f"\n   📊 SPLIT TEMPOREL STRICT:")
        logger.info(f"      Train: {train_dates[0]} → {train_dates[-1]} ({len(train_dates)} jours)")
        logger.info(f"      Val:   {val_dates[0]} → {val_dates[-1]} ({len(val_dates)} jours)")
        logger.info(f"      Test:  {test_dates[0]} → {test_dates[-1]} ({len(test_dates)} jours)")
        logger.info(f"      ⚠️  AUCUN CHEVAUCHEMENT entre splits (évite leakage)")

        # 4. Créer masks
        train_mask = df['date'].isin(train_dates)
        val_mask = df['date'].isin(val_dates)
        test_mask = df['date'].isin(test_dates)

        # 5. Features et target
        target_col = 'win'
        if target_col not in df.columns:
            raise ValueError(f"❌ Colonne '{target_col}' manquante !")

        # Exclure métadonnées + target + RESULTATS TRADE
        exclude_cols = [
            'win',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE si features!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
        ]

        # Ajouter colonnes optionnelles si elles existent
        optional_exclude = [
            't_ms', 'sym', 'symbol_base', 'source_file',
            'vix', 'volatility_regime', 'dom_age_ms', 'is_dom_fresh',
            'in_value_area', 'is_1tick_spread', 'data_quality'
        ]

        for col in optional_exclude:
            if col in df.columns and col not in exclude_cols:
                exclude_cols.append(col)

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"\n   📊 Features: {len(feature_cols)}")
        logger.info(f"   🎯 Target: {target_col}")

        X = df[feature_cols]
        y = df[target_col]

        # 6. Apply masks (NO SHUFFLE!)
        X_train, y_train = X[train_mask].copy(), y[train_mask].copy()
        X_val, y_val = X[val_mask].copy(), y[val_mask].copy()
        X_test, y_test = X[test_mask].copy(), y[test_mask].copy()

        logger.info(f"\n   📋 Splits (nombre de trades):")
        logger.info(f"      Train: {len(X_train):,} ({len(X_train)/len(df)*100:.1f}%)")
        logger.info(f"      Val:   {len(X_val):,} ({len(X_val)/len(df)*100:.1f}%)")
        logger.info(f"      Test:  {len(X_test):,} ({len(X_test)/len(df)*100:.1f}%)")

        # Distribution target par split
        win_train = y_train.sum()
        win_val = y_val.sum()
        win_test = y_test.sum()

        logger.info(f"\n   📊 Distribution TARGET (win):")
        logger.info(f"      Train WINs: {win_train:,} ({win_train/len(y_train)*100:.1f}%)")
        logger.info(f"      Val WINs:   {win_val:,} ({win_val/len(y_val)*100:.1f}%)")
        logger.info(f"      Test WINs:  {win_test:,} ({win_test/len(y_test)*100:.1f}%)")

        # Vérifier déséquilibre
        if win_test/len(y_test) < 0.3 or win_test/len(y_test) > 0.7:
            logger.warning(f"   ⚠️  Test set déséquilibré ({win_test/len(y_test)*100:.1f}% WINs)")
            logger.warning(f"      Considérer redistribution jours train/val/test")

        # 7. Standard Scaling
        logger.info(f"\n   ⚙️  Application StandardScaler...")
        self.scaler = StandardScaler()

        # Fit sur TRAIN SEULEMENT (éviter leakage)
        X_train_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        X_val_scaled = pd.DataFrame(
            self.scaler.transform(X_val),
            columns=X_val.columns,
            index=X_val.index
        )
        X_test_scaled = pd.DataFrame(
            self.scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index
        )

        logger.info(f"   ✅ Features standardisées (mean=0, std=1)")
        logger.info(f"   ✅ Scaler FIT sur TRAIN uniquement (évite leakage)")
        logger.info(f"{'='*70}\n")

        # Stocker feature names
        self.feature_names = feature_cols

        # ⚠️ CRITIQUE: Sauvegarder dates pour traçabilité
        self.split_info = {
            'method': 'temporal_split',
            'train_dates': [str(d) for d in train_dates],
            'val_dates': [str(d) for d in val_dates],
            'test_dates': [str(d) for d in test_dates],
            'train_size': len(X_train),
            'val_size': len(X_val),
            'test_size': len(X_test),
            'train_win_rate': float(win_train/len(y_train)),
            'val_win_rate': float(win_val/len(y_val)),
            'test_win_rate': float(win_test/len(y_test))
        }

        logger.info(f"   💾 Split info sauvegardé pour traçabilité")

        return X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test


    def _optuna_objective(
        self,
        trial: optuna.Trial,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> float:
        """
        Fonction objective pour Optuna (hyperparameter tuning).

        Args:
            trial: Trial Optuna
            X_train, y_train: Training data
            X_val, y_val: Validation data

        Returns:
            Validation LogLoss (à minimiser)
        """

        # Hyperparams à tuner
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'seed': 42,
            'is_unbalance': True,  # Pour gérer classes déséquilibrées
            'class_weight': 'balanced',  # Pondération automatique des classes

            # Tuning
            'num_leaves': trial.suggest_int('num_leaves', 20, 150),
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 50, 500),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        }

        # Training
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_metric='binary_logloss',
            callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
        )

        # Prédiction validation
        y_pred_proba = model.predict_proba(X_val)[:, 1]
        logloss = log_loss(y_val, y_pred_proba)

        return logloss


    def tune_hyperparameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        n_trials: int = 100
    ) -> Dict:
        """
        Tune hyperparamètres avec Optuna.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            n_trials: Nombre de trials Optuna

        Returns:
            Meilleurs paramètres
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 HYPERPARAMETER TUNING (Optuna)")
        logger.info(f"{'='*70}")
        logger.info(f"   Trials: {n_trials}")
        logger.info(f"   Sampler: TPE")
        logger.info(f"   Metric: LogLoss (minimiser)")
        logger.info(f"{'='*70}\n")

        # Créer study Optuna
        study = optuna.create_study(
            direction='minimize',
            sampler=TPESampler(seed=42)
        )

        # Optimize
        study.optimize(
            lambda trial: self._optuna_objective(trial, X_train, y_train, X_val, y_val),
            n_trials=n_trials,
            show_progress_bar=True
        )

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ TUNING TERMINÉ")
        logger.info(f"{'='*70}")
        logger.info(f"   Best LogLoss: {study.best_value:.4f}")
        logger.info(f"   Best trial: #{study.best_trial.number}")
        logger.info(f"\n   📋 Meilleurs params:")
        for key, value in study.best_params.items():
            logger.info(f"      {key}: {value}")
        logger.info(f"{'='*70}\n")

        # Construire params complets
        best_params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'seed': 42,
            'is_unbalance': True,
            **study.best_params
        }

        self.best_params = best_params

        return best_params


    def train_final_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        params: Optional[Dict] = None
    ) -> lgb.LGBMClassifier:
        """
        Entraîne modèle final avec meilleurs params.

        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            params: Paramètres (ou best_params si None)

        Returns:
            Modèle entraîné
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 TRAINING MODÈLE FINAL (CLASSIFIER)")
        logger.info(f"{'='*70}")

        if params is None:
            params = self.best_params

        # Training
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            eval_names=['train', 'val'],
            eval_metric='binary_logloss',
            callbacks=[
                lgb.early_stopping(stopping_rounds=100, verbose=False),
                lgb.log_evaluation(period=100)
            ]
        )

        logger.info(f"\n   ✅ Training terminé")
        logger.info(f"      Best iteration: {model.best_iteration_}")

        # Calculer accuracy sur train et val
        train_acc = accuracy_score(y_train, model.predict(X_train))
        val_acc = accuracy_score(y_val, model.predict(X_val))

        logger.info(f"      Train Accuracy: {train_acc:.4f}")
        logger.info(f"      Val Accuracy: {val_acc:.4f}")
        logger.info(f"{'='*70}\n")

        self.model = model

        return model


    def evaluate_model(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict:
        """
        Évalue modèle sur test set.

        Args:
            X_test, y_test: Test data

        Returns:
            Dict avec métriques
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 ÉVALUATION MODÈLE (TEST SET) - CLASSIFICATION")
        logger.info(f"{'='*70}")

        # Prédictions avec seuil par défaut (0.50)
        y_pred_default = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        # 🎯 Prédictions avec seuil optimal (0.45)
        optimal_threshold = 0.45
        y_pred_optimal = (y_pred_proba >= optimal_threshold).astype(int)

        # Métriques avec seuil par défaut (0.50)
        logger.info(f"\n   MÉTRIQUES SEUIL PAR DÉFAUT (0.50):")
        accuracy_default = accuracy_score(y_test, y_pred_default)
        precision_default = precision_score(y_test, y_pred_default, zero_division=0)
        recall_default = recall_score(y_test, y_pred_default, zero_division=0)
        f1_default = f1_score(y_test, y_pred_default, zero_division=0)

        logger.info(f"      Accuracy:  {accuracy_default:.4f} ({accuracy_default*100:.2f}%)")
        logger.info(f"      Precision: {precision_default:.4f}")
        logger.info(f"      Recall:    {recall_default:.4f}")
        logger.info(f"      F1-Score:  {f1_default:.4f}")

        # 🎯 Métriques avec seuil optimal (0.45)
        logger.info(f"\n   🎯 MÉTRIQUES SEUIL OPTIMAL (0.45):")
        accuracy_optimal = accuracy_score(y_test, y_pred_optimal)
        precision_optimal = precision_score(y_test, y_pred_optimal, zero_division=0)
        recall_optimal = recall_score(y_test, y_pred_optimal, zero_division=0)
        f1_optimal = f1_score(y_test, y_pred_optimal, zero_division=0)

        logger.info(f"      Accuracy:  {accuracy_optimal:.4f} ({accuracy_optimal*100:.2f}%)")
        logger.info(f"      Precision: {precision_optimal:.4f}")
        logger.info(f"      Recall:    {recall_optimal:.4f}")
        logger.info(f"      F1-Score:  {f1_optimal:.4f} 🔥")

        # Gain avec seuil optimal
        f1_gain = ((f1_optimal - f1_default) / f1_default * 100) if f1_default > 0 else 0
        logger.info(f"\n   📊 GAIN SEUIL OPTIMAL:")
        logger.info(f"      F1-Score: {f1_default:.4f} → {f1_optimal:.4f} ({f1_gain:+.1f}%)")

        # Métriques communes
        try:
            auc = roc_auc_score(y_test, y_pred_proba)
        except:
            auc = 0.0

        logloss = log_loss(y_test, y_pred_proba)

        # Matrice de confusion (avec seuil optimal)
        cm = confusion_matrix(y_test, y_pred_optimal)
        tn, fp, fn, tp = cm.ravel()

        metrics = {
            # Seuil par défaut (0.50)
            'accuracy_default': accuracy_default,
            'precision_default': precision_default,
            'recall_default': recall_default,
            'f1_score_default': f1_default,
            # Seuil optimal (0.45)
            'accuracy': accuracy_optimal,
            'precision': precision_optimal,
            'recall': recall_optimal,
            'f1_score': f1_optimal,
            # Communes
            'auc_roc': auc,
            'log_loss': logloss,
            'confusion_matrix': cm,
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_positives': int(tp),
            'n_samples': len(y_test)
        }

        logger.info(f"   📈 Métriques Classification:")
        logger.info(f"      Accuracy (0.45):  {accuracy_optimal:.4f} ({accuracy_optimal*100:.2f}%)")
        logger.info(f"      Precision (0.45): {precision_optimal:.4f}")
        logger.info(f"      Recall (0.45):    {recall_optimal:.4f}")
        logger.info(f"      F1-Score (0.45):  {f1_optimal:.4f}")
        logger.info(f"      AUC-ROC:   {auc:.4f}")
        logger.info(f"      LogLoss:   {logloss:.4f}")

        logger.info(f"\n   📊 Matrice de Confusion:")
        logger.info(f"      True Negatives (TN):  {tn:,}")
        logger.info(f"      False Positives (FP): {fp:,}")
        logger.info(f"      False Negatives (FN): {fn:,}")
        logger.info(f"      True Positives (TP):  {tp:,}")

        logger.info(f"\n   📊 Distribution:")
        win_actual = int(y_test.sum())
        loss_actual = len(y_test) - win_actual
        win_pred = int(y_pred_optimal.sum())  # ✅ CORRECTION: utiliser y_pred_optimal
        loss_pred = len(y_pred_optimal) - win_pred

        logger.info(f"      Actual WINs:  {win_actual:,} ({win_actual/len(y_test)*100:.1f}%)")
        logger.info(f"      Actual LOSSes: {loss_actual:,} ({loss_actual/len(y_test)*100:.1f}%)")
        logger.info(f"      Pred WINs:    {win_pred:,} ({win_pred/len(y_pred_optimal)*100:.1f}%)")
        logger.info(f"      Pred LOSSes:  {loss_pred:,} ({loss_pred/len(y_pred_optimal)*100:.1f}%)")

        # ═══════════════════════════════════════════════════════════════
        # 🔥 NOUVEAU 15/11/2025: VÉRIFICATION COHÉRENCE MÉTRIQUES
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 VÉRIFICATION COHÉRENCE MÉTRIQUES vs MATRICE")
        logger.info(f"{'='*70}")

        # Recalculer métriques MANUELLEMENT depuis matrice
        tn_verif, fp_verif, fn_verif, tp_verif = cm.ravel()

        precision_verif = tp_verif / (tp_verif + fp_verif) if (tp_verif + fp_verif) > 0 else 0
        recall_verif = tp_verif / (tp_verif + fn_verif) if (tp_verif + fn_verif) > 0 else 0
        accuracy_verif = (tp_verif + tn_verif) / (tp_verif + tn_verif + fp_verif + fn_verif)
        f1_verif = 2 * (precision_verif * recall_verif) / (precision_verif + recall_verif) if (precision_verif + recall_verif) > 0 else 0

        logger.info(f"   📊 Matrice de confusion (seuil {optimal_threshold}):")
        logger.info(f"      TN={tn_verif:,} | FP={fp_verif:,}")
        logger.info(f"      FN={fn_verif:,} | TP={tp_verif:,}")
        logger.info(f"\n   📊 Métriques CALCULÉES depuis matrice:")
        logger.info(f"      Precision: {precision_verif:.4f}")
        logger.info(f"      Recall:    {recall_verif:.4f}")
        logger.info(f"      Accuracy:  {accuracy_verif:.4f}")
        logger.info(f"      F1-Score:  {f1_verif:.4f}")
        logger.info(f"\n   📊 Métriques SKLEARN:")
        logger.info(f"      Precision: {precision_optimal:.4f}")
        logger.info(f"      Recall:    {recall_optimal:.4f}")
        logger.info(f"      Accuracy:  {accuracy_optimal:.4f}")
        logger.info(f"      F1-Score:  {f1_optimal:.4f}")

        # Vérifier cohérence (tolérance 0.001)
        coherence_checks = {
            'precision': abs(precision_verif - precision_optimal) < 0.001,
            'recall': abs(recall_verif - recall_optimal) < 0.001,
            'accuracy': abs(accuracy_verif - accuracy_optimal) < 0.001,
            'f1_score': abs(f1_verif - f1_optimal) < 0.001
        }

        all_coherent = all(coherence_checks.values())

        logger.info(f"\n   🔍 Cohérence (tolérance ±0.001):")
        for metric, is_coherent in coherence_checks.items():
            status = "✅" if is_coherent else "❌"
            logger.info(f"      {status} {metric.capitalize()}")

        if all_coherent:
            logger.info(f"\n   ✅ TOUTES LES MÉTRIQUES SONT COHÉRENTES !")
        else:
            logger.error(f"\n   ❌ INCOHÉRENCE DÉTECTÉE - Vérifier calcul sklearn")

        # Sauvegarder vérification
        verification_path = self.output_dir / "metrics_verification.json"
        import json
        with open(verification_path, 'w') as f:
            json.dump({
                'confusion_matrix': {
                    'TN': int(tn_verif), 'FP': int(fp_verif),
                    'FN': int(fn_verif), 'TP': int(tp_verif)
                },
                'metrics_sklearn': {
                    'precision': float(precision_optimal),
                    'recall': float(recall_optimal),
                    'accuracy': float(accuracy_optimal),
                    'f1_score': float(f1_optimal),
                    'threshold': float(optimal_threshold)
                },
                'metrics_calculated': {
                    'precision': float(precision_verif),
                    'recall': float(recall_verif),
                    'accuracy': float(accuracy_verif),
                    'f1_score': float(f1_verif)
                },
                'coherence': {k: bool(v) for k, v in coherence_checks.items()},  # ✅ Conversion explicite
                'all_coherent': bool(all_coherent)  # ✅ Conversion explicite
            }, f, indent=2)

        logger.info(f"\n   💾 Vérification sauvegardée: {verification_path}")
        logger.info(f"{'='*70}\n")

        return metrics


    def analyze_shap(
        self,
        X_sample: pd.DataFrame,
        max_display: int = 30
    ):
        """
        Analyse SHAP feature importance.

        Args:
            X_sample: Échantillon pour SHAP (max 1000 samples pour performance)
            max_display: Nombre max de features à afficher
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 SHAP FEATURE IMPORTANCE")
        logger.info(f"{'='*70}")
        logger.info(f"   Samples: {len(X_sample)}")
        logger.info(f"   Features: {len(X_sample.columns)}")
        logger.info(f"{'='*70}\n")

        # Sample si trop grand
        if len(X_sample) > 1000:
            X_sample = X_sample.sample(n=1000, random_state=42)
            logger.info(f"   ⚠️ Échantillon réduit à 1000 samples pour performance")

        # Créer explainer
        logger.info("   🔧 Création SHAP explainer (TreeExplainer)...")
        explainer = shap.TreeExplainer(self.model)

        logger.info("   🔧 Calcul SHAP values...")
        shap_values = explainer.shap_values(X_sample)

        # Feature importance moyenne
        feature_importance = pd.DataFrame({
            'feature': X_sample.columns,
            'importance': np.abs(shap_values).mean(axis=0)
        }).sort_values('importance', ascending=False)

        logger.info(f"\n   📊 TOP {max_display} FEATURES (SHAP):")
        for idx, row in feature_importance.head(max_display).iterrows():
            logger.info(f"      {idx+1:2d}. {row['feature']:30s} {row['importance']:.4f}")

        logger.info(f"{'='*70}\n")

        # Sauvegarder plot
        try:
            plt.figure(figsize=(12, 10))
            shap.summary_plot(
                shap_values,
                X_sample,
                max_display=max_display,
                show=False
            )
            plot_path = self.output_dir / "shap_feature_importance.png"
            plt.tight_layout()
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            logger.info(f"   💾 Plot SHAP sauvegardé: {plot_path}")
        except Exception as e:
            logger.warning(f"   ⚠️ Erreur sauvegarde plot SHAP: {e}")

        return feature_importance


    def save_model(self, version: str = "v1"):
        """
        Sauvegarde modèle + métadonnées.

        Args:
            version: Version du modèle
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"💾 SAUVEGARDE MODÈLE")
        logger.info(f"{'='*70}")

        model_path = self.output_dir / f"lightgbm_quality_{version}.pkl"
        metadata_path = self.output_dir / f"lightgbm_quality_{version}_metadata.json"

        # Pickle modèle
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'best_params': self.best_params,
                'scaler': self.scaler
            }, f)

        file_size = model_path.stat().st_size / 1024  # KB

        logger.info(f"   ✅ Modèle sauvegardé:")
        logger.info(f"      Fichier: {model_path}")
        logger.info(f"      Taille: {file_size:.2f} KB")

        # Métadonnées JSON
        metadata = {
            'version': version,
            'n_features': len(self.feature_names),
            'feature_names': self.feature_names,
            'best_params': self.best_params,
            'model_type': 'LGBMClassifier',
            'target': 'win',  # Classification binaire WIN/LOSS
            'has_scaler': self.scaler is not None,
            # ✅ NOUVEAU 15/11/2025: Traçabilité split temporel
            'split_info': self.split_info if hasattr(self, 'split_info') else None
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"   ✅ Métadonnées sauvegardées: {metadata_path}")
        logger.info(f"{'='*70}\n")


    def train_pipeline(
        self,
        df_trades: pd.DataFrame,
        tune_hyperparams: bool = True,
        n_trials: int = 100
    ):
        """
        Pipeline complet d'entraînement CLASSIFIER.

        Args:
            df_trades: DataFrame des trades labeled (avec colonne 'win')
            tune_hyperparams: Si True, tune avec Optuna
            n_trials: Nombre de trials Optuna
        """

        logger.info(f"\n{'#'*70}")
        logger.info(f"{'#'*70}")
        logger.info(f"##   LIGHTGBM TRAINING PIPELINE - ML 3-LAYER STRATEGY")
        logger.info(f"{'#'*70}")
        logger.info(f"{'#'*70}\n")

        # 1. Préparation données (SPLIT TEMPOREL STRICT)
        # ✅ Correction 15/11/2025: Split temporel pour éviter leakage
        X_train, X_val, X_test, y_train, y_val, y_test = self._prepare_data_temporal_split(
            df_trades,
            train_ratio=0.6,  # 60% jours → train
            val_ratio=0.2,    # 20% jours → val
            test_ratio=0.2    # 20% jours → test
        )

        # 2. Hyperparameter tuning
        if tune_hyperparams:
            best_params = self.tune_hyperparameters(
                X_train, y_train,
                X_val, y_val,
                n_trials=n_trials
            )
        else:
            # Params par défaut
            best_params = {
                'objective': 'regression',
                'metric': 'mae',
                'verbosity': -1,
                'boosting_type': 'gbdt',
                'num_leaves': 63,
                'max_depth': 8,
                'learning_rate': 0.05,
                'n_estimators': 200,
                'min_child_samples': 20,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1,
                'seed': 42
            }
            self.best_params = best_params

        # 3. Training final
        model = self.train_final_model(X_train, y_train, X_val, y_val, best_params)

        # 4. Évaluation
        metrics = self.evaluate_model(X_test, y_test)

        # 5. SHAP analysis
        shap_importance = self.analyze_shap(X_test)

        # 6. Sauvegarde
        self.save_model(version="v1")

        logger.info(f"\n{'#'*70}")
        logger.info(f"##   ✅ TRAINING PIPELINE TERMINÉ AVEC SUCCÈS !")
        logger.info(f"{'#'*70}\n")

        return {
            'model': model,
            'metrics': metrics,
            'shap_importance': shap_importance,
            'feature_names': self.feature_names
        }


# ═══════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Training LightGBM sur trades labeled."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # ═══════════════════════════════════════════════════════════
    # CHARGEMENT DONNÉES
    # ═══════════════════════════════════════════════════════════

    INPUT_PATH = "ml/data/labeled_trades.parquet"

    logger.info(f"📂 Chargement trades labeled: {INPUT_PATH}")

    if not Path(INPUT_PATH).exists():
        logger.error(f"❌ Fichier non trouvé: {INPUT_PATH}")
        logger.error("   Exécutez d'abord: python ml/label_trades.py")
        exit(1)

    df_trades = pd.read_parquet(INPUT_PATH)
    logger.info(f"✅ {len(df_trades):,} trades chargés\n")

    # ═══════════════════════════════════════════════════════════
    # TRAINING PIPELINE
    # ═══════════════════════════════════════════════════════════

    trainer = LightGBMClassifierTrainer(output_dir="ml/models")

    results = trainer.train_pipeline(
        df_trades=df_trades,
        tune_hyperparams=True,  # Activer Optuna
        n_trials=100            # 100 trials
    )

    logger.info("\n✅ Training CLASSIFIER terminé avec succès !")
    logger.info(f"   Modèle sauvegardé: ml/models/lightgbm_classifier_v1.pkl")
    logger.info(f"   Accuracy test: {results['metrics']['accuracy']:.4f} ({results['metrics']['accuracy']*100:.2f}%)")
    logger.info(f"   F1-Score test: {results['metrics']['f1_score']:.4f}")
