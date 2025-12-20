"""
🎯 LIGHTGBM TRAINING PIPELINE - ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Pipeline complet d'entraînement LightGBM:
1. Load labeled trades (avec quality_score target)
2. Feature engineering (90 features)
3. Train/Val/Test split (60/20/20)
4. Hyperparameter tuning avec Optuna (100 trials)
5. Training final avec meilleurs params
6. Évaluation: MAE, RMSE, R², distribution
7. SHAP feature importance (top 30)
8. Sauvegarde modèle production

Input: ml/data/labeled_trades.parquet
Output: ml/models/lightgbm_quality_v1.pkl
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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import optuna
from optuna.samplers import TPESampler

# SHAP
import shap
import matplotlib.pyplot as plt

# Ajouter parent au path
sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_engineering_lightgbm import FeatureEngineer
from ml.extract_ml_ready_data import MLReadyDataExtractor

logger = logging.getLogger(__name__)


class LightGBMTrainer:
    """
    Entraîne modèle LightGBM pour prédire quality_score.

    Usage:
        trainer = LightGBMTrainer()
        trainer.train_pipeline(df_trades, df_snapshots)
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

        # Feature engineer
        self.feature_engineer = FeatureEngineer()

        logger.info("✅ LightGBMTrainer initialisé")
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
            df: DataFrame avec features + quality_score
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
        target_col = 'quality_score'
        if target_col not in df.columns:
            raise ValueError(f"❌ Colonne '{target_col}' manquante !")

        # Features (exclure métadonnées + target + RESULTATS TRADE)
        # ⚠️ IMPORTANT: pnl_ticks, duration_minutes, mae, mfe sont des RESULTATS
        #    connus APRES le trade → DATA LEAKAGE si utilisés comme features !
        exclude_cols = [
            'quality_score',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE si features!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
            # === METADATA ===
            't_ms', 'sym', 'symbol_base', 'source_file'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"   Total samples: {len(df):,}")
        logger.info(f"   Total features: {len(feature_cols)}")
        logger.info(f"   Target: {target_col}")
        logger.info(f"   Target range: [{df[target_col].min():.1f}, {df[target_col].max():.1f}]")
        logger.info(f"   Target mean: {df[target_col].mean():.1f}")

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
            Validation MAE (à minimiser)
        """

        # Hyperparams à tuner
        params = {
            'objective': 'regression',
            'metric': 'mae',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'seed': 42,

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
        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_metric='mae',
            callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
        )

        # Prédiction validation
        y_pred = model.predict(X_val)
        mae = mean_absolute_error(y_val, y_pred)

        return mae


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
        logger.info(f"   Metric: MAE (minimiser)")
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
        logger.info(f"   Best MAE: {study.best_value:.4f}")
        logger.info(f"   Best trial: #{study.best_trial.number}")
        logger.info(f"\n   📋 Meilleurs params:")
        for key, value in study.best_params.items():
            logger.info(f"      {key}: {value}")
        logger.info(f"{'='*70}\n")

        # Construire params complets
        best_params = {
            'objective': 'regression',
            'metric': 'mae',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'seed': 42,
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
    ) -> lgb.LGBMRegressor:
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
        logger.info(f"🎯 TRAINING MODÈLE FINAL")
        logger.info(f"{'='*70}")

        if params is None:
            params = self.best_params

        # Training
        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            eval_names=['train', 'val'],
            eval_metric='mae',
            callbacks=[
                lgb.early_stopping(stopping_rounds=100, verbose=False),
                lgb.log_evaluation(period=100)
            ]
        )

        logger.info(f"\n   ✅ Training terminé")
        logger.info(f"      Best iteration: {model.best_iteration_}")
        logger.info(f"      Train MAE: {model.best_score_['train']['l1']:.4f}")
        logger.info(f"      Val MAE: {model.best_score_['val']['l1']:.4f}")
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
        logger.info(f"📊 ÉVALUATION MODÈLE (TEST SET)")
        logger.info(f"{'='*70}")

        # Prédictions
        y_pred = self.model.predict(X_test)

        # Métriques
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        # Erreur relative
        mape = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-8))) * 100

        metrics = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'mape': mape,
            'n_samples': len(y_test)
        }

        logger.info(f"   📈 Métriques:")
        logger.info(f"      MAE:  {mae:.4f} points")
        logger.info(f"      RMSE: {rmse:.4f} points")
        logger.info(f"      R²:   {r2:.4f}")
        logger.info(f"      MAPE: {mape:.2f}%")
        logger.info(f"\n   📊 Distribution prédictions:")
        logger.info(f"      Min:    {y_pred.min():.1f}")
        logger.info(f"      Q25:    {np.percentile(y_pred, 25):.1f}")
        logger.info(f"      Médian: {np.median(y_pred):.1f}")
        logger.info(f"      Q75:    {np.percentile(y_pred, 75):.1f}")
        logger.info(f"      Max:    {y_pred.max():.1f}")
        logger.info(f"\n   📊 Distribution réelle:")
        logger.info(f"      Min:    {y_test.min():.1f}")
        logger.info(f"      Médian: {y_test.median():.1f}")
        logger.info(f"      Max:    {y_test.max():.1f}")
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
            'model_type': 'LGBMRegressor',
            'has_scaler': self.scaler is not None
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
        Pipeline complet d'entraînement.

        Args:
            df_trades: DataFrame des trades labeled (avec quality_score)
            tune_hyperparams: Si True, tune avec Optuna
            n_trials: Nombre de trials Optuna
        """

        logger.info(f"\n{'#'*70}")
        logger.info(f"{'#'*70}")
        logger.info(f"##   LIGHTGBM TRAINING PIPELINE - ML 3-LAYER STRATEGY")
        logger.info(f"{'#'*70}")
        logger.info(f"{'#'*70}\n")

        # 1. Préparation données
        X_train, X_val, X_test, y_train, y_val, y_test = self._prepare_data(df_trades)

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

    trainer = LightGBMTrainer(output_dir="ml/models")

    results = trainer.train_pipeline(
        df_trades=df_trades,
        tune_hyperparams=True,  # Activer Optuna
        n_trials=100            # 100 trials
    )

    logger.info("\n✅ Training terminé avec succès !")
    logger.info(f"   Modèle sauvegardé: ml/models/lightgbm_quality_v1.pkl")
    logger.info(f"   MAE test: {results['metrics']['mae']:.4f}")
    logger.info(f"   R² test: {results['metrics']['r2']:.4f}")



Version: 1.0
Date: 15 novembre 2025

Pipeline complet d'entraînement LightGBM:
1. Load labeled trades (avec quality_score target)
2. Feature engineering (90 features)
3. Train/Val/Test split (60/20/20)
4. Hyperparameter tuning avec Optuna (100 trials)
5. Training final avec meilleurs params
6. Évaluation: MAE, RMSE, R², distribution
7. SHAP feature importance (top 30)
8. Sauvegarde modèle production

Input: ml/data/labeled_trades.parquet
Output: ml/models/lightgbm_quality_v1.pkl
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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import optuna
from optuna.samplers import TPESampler

# SHAP
import shap
import matplotlib.pyplot as plt

# Ajouter parent au path
sys.path.append(str(Path(__file__).parent.parent))

from ml.feature_engineering_lightgbm import FeatureEngineer
from ml.extract_ml_ready_data import MLReadyDataExtractor

logger = logging.getLogger(__name__)


class LightGBMTrainer:
    """
    Entraîne modèle LightGBM pour prédire quality_score.

    Usage:
        trainer = LightGBMTrainer()
        trainer.train_pipeline(df_trades, df_snapshots)
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

        # Feature engineer
        self.feature_engineer = FeatureEngineer()

        logger.info("✅ LightGBMTrainer initialisé")
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
            df: DataFrame avec features + quality_score
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
        target_col = 'quality_score'
        if target_col not in df.columns:
            raise ValueError(f"❌ Colonne '{target_col}' manquante !")

        # Features (exclure métadonnées + target + RESULTATS TRADE)
        # ⚠️ IMPORTANT: pnl_ticks, duration_minutes, mae, mfe sont des RESULTATS
        #    connus APRES le trade → DATA LEAKAGE si utilisés comme features !
        exclude_cols = [
            'quality_score',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE si features!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
            # === METADATA ===
            't_ms', 'sym', 'symbol_base', 'source_file'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"   Total samples: {len(df):,}")
        logger.info(f"   Total features: {len(feature_cols)}")
        logger.info(f"   Target: {target_col}")
        logger.info(f"   Target range: [{df[target_col].min():.1f}, {df[target_col].max():.1f}]")
        logger.info(f"   Target mean: {df[target_col].mean():.1f}")

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
            Validation MAE (à minimiser)
        """

        # Hyperparams à tuner
        params = {
            'objective': 'regression',
            'metric': 'mae',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'seed': 42,

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
        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_metric='mae',
            callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
        )

        # Prédiction validation
        y_pred = model.predict(X_val)
        mae = mean_absolute_error(y_val, y_pred)

        return mae


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
        logger.info(f"   Metric: MAE (minimiser)")
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
        logger.info(f"   Best MAE: {study.best_value:.4f}")
        logger.info(f"   Best trial: #{study.best_trial.number}")
        logger.info(f"\n   📋 Meilleurs params:")
        for key, value in study.best_params.items():
            logger.info(f"      {key}: {value}")
        logger.info(f"{'='*70}\n")

        # Construire params complets
        best_params = {
            'objective': 'regression',
            'metric': 'mae',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'seed': 42,
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
    ) -> lgb.LGBMRegressor:
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
        logger.info(f"🎯 TRAINING MODÈLE FINAL")
        logger.info(f"{'='*70}")

        if params is None:
            params = self.best_params

        # Training
        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            eval_names=['train', 'val'],
            eval_metric='mae',
            callbacks=[
                lgb.early_stopping(stopping_rounds=100, verbose=False),
                lgb.log_evaluation(period=100)
            ]
        )

        logger.info(f"\n   ✅ Training terminé")
        logger.info(f"      Best iteration: {model.best_iteration_}")
        logger.info(f"      Train MAE: {model.best_score_['train']['l1']:.4f}")
        logger.info(f"      Val MAE: {model.best_score_['val']['l1']:.4f}")
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
        logger.info(f"📊 ÉVALUATION MODÈLE (TEST SET)")
        logger.info(f"{'='*70}")

        # Prédictions
        y_pred = self.model.predict(X_test)

        # Métriques
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        # Erreur relative
        mape = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-8))) * 100

        metrics = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'mape': mape,
            'n_samples': len(y_test)
        }

        logger.info(f"   📈 Métriques:")
        logger.info(f"      MAE:  {mae:.4f} points")
        logger.info(f"      RMSE: {rmse:.4f} points")
        logger.info(f"      R²:   {r2:.4f}")
        logger.info(f"      MAPE: {mape:.2f}%")
        logger.info(f"\n   📊 Distribution prédictions:")
        logger.info(f"      Min:    {y_pred.min():.1f}")
        logger.info(f"      Q25:    {np.percentile(y_pred, 25):.1f}")
        logger.info(f"      Médian: {np.median(y_pred):.1f}")
        logger.info(f"      Q75:    {np.percentile(y_pred, 75):.1f}")
        logger.info(f"      Max:    {y_pred.max():.1f}")
        logger.info(f"\n   📊 Distribution réelle:")
        logger.info(f"      Min:    {y_test.min():.1f}")
        logger.info(f"      Médian: {y_test.median():.1f}")
        logger.info(f"      Max:    {y_test.max():.1f}")
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
            'model_type': 'LGBMRegressor',
            'has_scaler': self.scaler is not None
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
        Pipeline complet d'entraînement.

        Args:
            df_trades: DataFrame des trades labeled (avec quality_score)
            tune_hyperparams: Si True, tune avec Optuna
            n_trials: Nombre de trials Optuna
        """

        logger.info(f"\n{'#'*70}")
        logger.info(f"{'#'*70}")
        logger.info(f"##   LIGHTGBM TRAINING PIPELINE - ML 3-LAYER STRATEGY")
        logger.info(f"{'#'*70}")
        logger.info(f"{'#'*70}\n")

        # 1. Préparation données
        X_train, X_val, X_test, y_train, y_val, y_test = self._prepare_data(df_trades)

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

    trainer = LightGBMTrainer(output_dir="ml/models")

    results = trainer.train_pipeline(
        df_trades=df_trades,
        tune_hyperparams=True,  # Activer Optuna
        n_trials=100            # 100 trials
    )

    logger.info("\n✅ Training terminé avec succès !")
    logger.info(f"   Modèle sauvegardé: ml/models/lightgbm_quality_v1.pkl")
    logger.info(f"   MAE test: {results['metrics']['mae']:.4f}")
    logger.info(f"   R² test: {results['metrics']['r2']:.4f}")





