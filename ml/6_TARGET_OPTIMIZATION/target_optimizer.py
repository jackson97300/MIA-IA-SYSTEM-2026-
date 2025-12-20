"""
Target Optimizer - Système de comparaison de targets ML

Ce module implémente un framework pour tester empiriquement
différentes définitions de target et sélectionner celle qui
maximise le P&L net en out-of-sample.

Architecture:
1. Générateurs de targets (T1-T8)
2. Training adaptatif (Classification/Regression/Multiclass)
3. Backtesting avec logiques de décision spécifiques
4. Sélection multi-critères
5. Reporting et visualisation

Auteur: MIA Trading System
Date: 15 novembre 2025
"""

import logging
import json
import pickle
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, mean_squared_error, mean_absolute_error
)
from lightgbm import LGBMClassifier, LGBMRegressor
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TargetConfig:
    """Configuration d'une target à tester"""
    name: str
    mode: str  # 'classification', 'regression', 'multiclass'
    params: Dict[str, Any]
    description: str


@dataclass
class TargetResult:
    """Résultats du backtest pour une target"""
    target_name: str
    pnl_net: float
    pnl_gross: float
    pnl_per_trade: float
    n_trades: int
    winrate: float
    sharpe: float
    max_dd: float
    metrics: Dict[str, float]  # F1, RMSE, etc selon mode

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sauvegarde JSON"""
        return {
            'target_name': self.target_name,
            'pnl_net': self.pnl_net,
            'pnl_gross': self.pnl_gross,
            'pnl_per_trade': self.pnl_per_trade,
            'n_trades': self.n_trades,
            'winrate': self.winrate,
            'sharpe': self.sharpe,
            'max_dd': self.max_dd,
            'metrics': self.metrics
        }



# ═══════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE: TargetOptimizer
# ═══════════════════════════════════════════════════════════════════════

class TargetOptimizer:
    """
    Optimiseur de targets ML

    Teste empiriquement différentes définitions de target
    et sélectionne celle qui maximise le P&L net.
    """

    def __init__(
        self,
        data_path: str,
        output_dir: str,
        fees_per_trade: float = 0.62,
        scaler: Optional[StandardScaler] = None
    ):
        """
        Initialise l'optimiseur

        Args:
            data_path: Chemin vers labeled_trades.parquet
            output_dir: Dossier de sortie pour résultats
            fees_per_trade: Fees par trade en ticks
            scaler: Scaler pré-fitted (optionnel)
        """
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.fees_per_trade = fees_per_trade
        self.scaler = scaler or StandardScaler()

        self.df_trades = None
        self.feature_names = None
        self.split_info = {}

        logger.info(f"✅ TargetOptimizer initialisé")
        logger.info(f"   Data: {self.data_path}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"   Fees: {self.fees_per_trade}t/trade")


    # ═══════════════════════════════════════════════════════════════════════
    # DATA LOADING & PREPARATION
    # ═══════════════════════════════════════════════════════════════════════

    def _load_data(self) -> pd.DataFrame:
        """
        Charge les données labellisées

        Returns:
            DataFrame avec trades labellisés
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📂 CHARGEMENT DONNÉES")
        logger.info(f"{'='*70}")

        if not self.data_path.exists():
            raise FileNotFoundError(f"❌ Fichier introuvable: {self.data_path}")

        df = pd.read_parquet(self.data_path)
        logger.info(f"   ✅ Chargé: {len(df):,} trades")

        # Validation colonnes requises (renommer stop -> sl_ticks si nécessaire)
        required_cols = [
            'pnl_ticks', 'entry_price', 'exit_price',
            'direction', 'date'
        ]

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"❌ Colonnes manquantes: {missing}")

        # Adapter les noms de colonnes si nécessaire
        if 'stop' in df.columns and 'sl_ticks' not in df.columns:
            # Calculer sl_ticks depuis stop et entry_price
            df['sl_ticks'] = abs(df['stop'] - df['entry_price']) * 4  # ES: 1 point = 4 ticks
            logger.info(f"   ✅ Colonne 'sl_ticks' créée depuis 'stop'")

        if 'closest_blind_proximity' not in df.columns:
            df['closest_blind_proximity'] = 999.0  # Valeur par défaut
            logger.info(f"   ⚠️  Colonne 'closest_blind_proximity' absente, valeur par défaut")

        logger.info(f"   ✅ Colonnes requises présentes")
        logger.info(f"   📅 Période: {df['date'].min()} → {df['date'].max()}")

        # Statistiques P&L
        win_rate = (df['pnl_ticks'] > 0).mean()
        avg_pnl = df['pnl_ticks'].mean()

        logger.info(f"   📊 WinRate: {win_rate*100:.1f}%")
        logger.info(f"   📊 P&L moyen: {avg_pnl:+.2f} ticks")
        logger.info(f"{'='*70}\n")

        self.df_trades = df
        return df


    def _temporal_split(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Split temporel strict par JOURS (évite leakage)

        Réutilise la logique de train_lightgbm_classifier.py

        Args:
            df: DataFrame complète
            train_ratio: Proportion jours pour train
            val_ratio: Proportion jours pour val
            test_ratio: Proportion jours pour test

        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 SPLIT TEMPOREL STRICT")
        logger.info(f"{'='*70}")
        logger.info(f"   🎯 Split par JOURS (pas lignes) pour éviter leakage")

        # 1. Trier par date
        df = df.sort_values('date').reset_index(drop=True)

        # 2. Identifier dates uniques
        unique_dates = sorted(df['date'].unique())
        n_days = len(unique_dates)

        logger.info(f"   📅 Période: {unique_dates[0]} → {unique_dates[-1]}")
        logger.info(f"   📅 Nombre de jours: {n_days}")

        if n_days < 3:
            raise ValueError(f"❌ Besoin d'au moins 3 jours (actuel: {n_days})")

        # 3. Split temporel par JOURS
        train_days = int(n_days * train_ratio)
        val_days = int(n_days * (train_ratio + val_ratio))

        # Assurer au moins 1 jour par split
        train_days = max(1, train_days)
        val_days = max(train_days + 1, val_days)
        val_days = min(val_days, n_days - 1)

        train_dates = unique_dates[:train_days]
        val_dates = unique_dates[train_days:val_days]
        test_dates = unique_dates[val_days:]

        logger.info(f"\n   📊 SPLIT TEMPOREL:")
        logger.info(f"      Train: {train_dates[0]} → {train_dates[-1]} ({len(train_dates)} jours)")
        logger.info(f"      Val:   {val_dates[0]} → {val_dates[-1]} ({len(val_dates)} jours)")
        logger.info(f"      Test:  {test_dates[0]} → {test_dates[-1]} ({len(test_dates)} jours)")
        logger.info(f"      ⚠️  AUCUN CHEVAUCHEMENT (évite leakage)")

        # 4. Créer masks
        train_mask = df['date'].isin(train_dates)
        val_mask = df['date'].isin(val_dates)
        test_mask = df['date'].isin(test_dates)

        # 5. Features et target (sera overridden par generate_target)
        exclude_cols = [
            'win', 'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction', 'entry_price', 'exit_price',
            'stop', 'target', 'exit_reason', 'pnl', 'pnl_ticks', 'mae', 'mfe',
            'duration_minutes', 't_ms', 'sym', 'symbol_base', 'source_file',
            'vix', 'volatility_regime', 'dom_age_ms', 'is_dom_fresh',
            'in_value_area', 'is_1tick_spread', 'data_quality', 'sl_ticks'
        ]

        self.feature_names = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"\n   📊 Features: {len(self.feature_names)}")
        logger.info(f"   📊 Splits (trades):")
        logger.info(f"      Train: {train_mask.sum():,} ({train_mask.sum()/len(df)*100:.1f}%)")
        logger.info(f"      Val:   {val_mask.sum():,} ({val_mask.sum()/len(df)*100:.1f}%)")
        logger.info(f"      Test:  {test_mask.sum():,} ({test_mask.sum()/len(df)*100:.1f}%)")

        # 6. Sauvegarder split info
        self.split_info = {
            'method': 'temporal_split',
            'train_dates': [str(d) for d in train_dates],
            'val_dates': [str(d) for d in val_dates],
            'test_dates': [str(d) for d in test_dates],
            'train_size': int(train_mask.sum()),
            'val_size': int(val_mask.sum()),
            'test_size': int(test_mask.sum())
        }

        logger.info(f"{'='*70}\n")

        # Retourner DataFrames (pas scaled, fait plus tard)
        X_train = df[train_mask][self.feature_names].copy()
        X_val = df[val_mask][self.feature_names].copy()
        X_test = df[test_mask][self.feature_names].copy()

        # y sera généré par generate_target()
        y_train = None
        y_val = None
        y_test = None

        return X_train, X_val, X_test, y_train, y_val, y_test


    def _normalize_metric(
        self,
        value: float,
        min_val: float,
        max_val: float,
        reverse: bool = False
    ) -> float:
        """
        Normalise une métrique entre 0 et 100

        Utilisé pour le score multi-objectif.

        Args:
            value: Valeur à normaliser
            min_val: Valeur minimum de la plage
            max_val: Valeur maximum de la plage
            reverse: Si True, inverse l'échelle (utile pour max_dd)

        Returns:
            Valeur normalisée 0-100
        """
        if max_val == min_val:
            return 50.0

        normalized = (value - min_val) / (max_val - min_val)
        normalized = np.clip(normalized, 0.0, 1.0)

        if reverse:
            normalized = 1.0 - normalized

        return normalized * 100.0


    # ═══════════════════════════════════════════════════════════════════════
    # GÉNÉRATEURS DE TARGETS (T1-T8)
    # ═══════════════════════════════════════════════════════════════════════

    def generate_target_T1_binary_simple(self, df: pd.DataFrame) -> pd.Series:
        """
        T1: Binary Classification Simple

        Target: y = 1 si pnl_ticks > 0, sinon 0

        Baseline actuelle, pour comparaison.

        Args:
            df: DataFrame avec colonne 'pnl_ticks'

        Returns:
            Series d'entiers (0 ou 1)
        """
        y = (df['pnl_ticks'] > 0).astype(int)

        win_rate = y.mean()
        logger.info(f"   📊 T1 Binary Simple: WR={win_rate*100:.1f}%")

        return y


    def generate_target_T2_binary_strong(self, df: pd.DataFrame) -> pd.Series:
        """
        T2: Binary Classification Strong

        Target: y = 1 si pnl_ratio >= 0.5 (P&L > 50% du SL)

        Plus strict que T1, évite les petits wins.

        Args:
            df: DataFrame avec colonnes 'pnl_ticks', 'sl_ticks'

        Returns:
            Series d'entiers (0 ou 1)
        """
        pnl_ratio = df['pnl_ticks'] / df['sl_ticks']
        y = (pnl_ratio >= 0.5).astype(int)

        win_rate = y.mean()
        avg_pnl_winners = df[y == 1]['pnl_ticks'].mean() if y.sum() > 0 else 0

        logger.info(f"   📊 T2 Binary Strong: WR={win_rate*100:.1f}% | Avg WIN={avg_pnl_winners:.2f}t")

        return y


    def generate_target_T3_pnl_ratio_reg(self, df: pd.DataFrame) -> pd.Series:
        """
        T3: Regression on P&L Ratio

        Target: pnl_ratio = pnl_ticks / sl_ticks, clippé à [-2.0, 3.0]

        Prédit directement le multiple de risque (R-multiple).

        Args:
            df: DataFrame avec colonnes 'pnl_ticks', 'sl_ticks'

        Returns:
            Series de floats
        """
        pnl_ratio = df['pnl_ticks'] / df['sl_ticks']
        y = np.clip(pnl_ratio, -2.0, 3.0)

        mean_ratio = y.mean()
        median_ratio = y.median()

        logger.info(f"   📊 T3 P&L Ratio Reg: Mean={mean_ratio:.2f}R | Median={median_ratio:.2f}R")

        return y


    def generate_target_T4_pnl_ticks_capped(self, df: pd.DataFrame) -> pd.Series:
        """
        T4: Regression on P&L Ticks (capped)

        Target: pnl_ticks clippé à [-20, 20]

        Prédit directement le P&L en ticks, robuste aux outliers.

        Args:
            df: DataFrame avec colonne 'pnl_ticks'

        Returns:
            Series de floats
        """
        y = np.clip(df['pnl_ticks'], -20, 20)

        mean_pnl = y.mean()
        median_pnl = y.median()

        logger.info(f"   📊 T4 P&L Ticks Capped: Mean={mean_pnl:+.2f}t | Median={median_pnl:+.2f}t")

        return y


    def generate_target_T5_multiclass(self, df: pd.DataFrame) -> pd.Series:
        """
        T5: Multiclass Classification (BAD / NEUTRAL / GOOD)

        Target:
        - 0 (BAD): pnl_ratio <= -0.5 (perte >= 50% du SL)
        - 1 (NEUTRAL): -0.5 < pnl_ratio < 0.5
        - 2 (GOOD): pnl_ratio >= 0.5 (gain >= 50% du SL)

        Args:
            df: DataFrame avec colonnes 'pnl_ticks', 'sl_ticks'

        Returns:
            Series d'entiers (0, 1, ou 2)
        """
        pnl_ratio = df['pnl_ticks'] / df['sl_ticks']

        y = np.zeros(len(df), dtype=int)
        y[pnl_ratio >= 0.5] = 2   # GOOD
        y[(pnl_ratio > -0.5) & (pnl_ratio < 0.5)] = 1  # NEUTRAL
        y[pnl_ratio <= -0.5] = 0  # BAD

        class_counts = pd.Series(y).value_counts().sort_index()
        logger.info(f"   📊 T5 Multiclass:")
        logger.info(f"      BAD (0):     {class_counts.get(0, 0)} ({class_counts.get(0, 0)/len(y)*100:.1f}%)")
        logger.info(f"      NEUTRAL (1): {class_counts.get(1, 0)} ({class_counts.get(1, 0)/len(y)*100:.1f}%)")
        logger.info(f"      GOOD (2):    {class_counts.get(2, 0)} ({class_counts.get(2, 0)/len(y)*100:.1f}%)")

        return pd.Series(y, index=df.index)


    def generate_target_T6_quality_simplified(self, df: pd.DataFrame) -> pd.Series:
        """
        T6: Regression on Quality Score (simplified)

        Target: quality = (pnl_ratio + 2) * 20, clippé à [0, 100]

        Transforme P&L ratio en score de qualité 0-100.
        - pnl_ratio = -2 → quality = 0
        - pnl_ratio =  0 → quality = 40
        - pnl_ratio = +3 → quality = 100

        Args:
            df: DataFrame avec colonnes 'pnl_ticks', 'sl_ticks'

        Returns:
            Series de floats (0-100)
        """
        pnl_ratio = df['pnl_ticks'] / df['sl_ticks']
        quality = (pnl_ratio + 2) * 20
        y = np.clip(quality, 0, 100)

        mean_quality = y.mean()
        median_quality = y.median()

        logger.info(f"   📊 T6 Quality Simplified: Mean={mean_quality:.1f} | Median={median_quality:.1f}")

        return y


    def generate_target_T7_expected_value(self, df: pd.DataFrame) -> pd.Series:
        """
        T7: Expected Value Direct (context-aware)

        Target: EV basé sur closest_blind_proximity

        Logique:
        - Proche Blind Spot (<5t): EV élevé (p_win=0.65, avg_win=12t)
        - Moyen (5-10t): EV moyen (p_win=0.50, avg_win=8t)
        - Loin (>10t): EV faible (p_win=0.40, avg_win=5t)

        Args:
            df: DataFrame avec colonnes 'closest_blind_proximity', 'sl_ticks'

        Returns:
            Series de floats (Expected Value en ticks)
        """
        # Simuler closest_blind_proximity si pas présent (pour debug)
        if 'closest_blind_proximity' not in df.columns:
            logger.warning("   ⚠️  'closest_blind_proximity' absent, simulation random")
            df['closest_blind_proximity'] = np.random.uniform(0, 20, len(df))

        proximity = df['closest_blind_proximity']
        sl_ticks = df['sl_ticks']

        # Calculer EV selon proximité
        ev = np.zeros(len(df))

        # Proche (<5t): EV = 0.65 * 12 - 0.35 * sl = 7.8 - 0.35 * sl
        mask_close = proximity < 5
        ev[mask_close] = 0.65 * 12 - 0.35 * sl_ticks[mask_close]

        # Moyen (5-10t): EV = 0.50 * 8 - 0.50 * sl = 4.0 - 0.50 * sl
        mask_medium = (proximity >= 5) & (proximity < 10)
        ev[mask_medium] = 0.50 * 8 - 0.50 * sl_ticks[mask_medium]

        # Loin (>10t): EV = 0.40 * 5 - 0.60 * sl = 2.0 - 0.60 * sl
        mask_far = proximity >= 10
        ev[mask_far] = 0.40 * 5 - 0.60 * sl_ticks[mask_far]

        y = pd.Series(ev, index=df.index)

        mean_ev = y.mean()
        median_ev = y.median()

        logger.info(f"   📊 T7 Expected Value: Mean={mean_ev:+.2f}t | Median={median_ev:+.2f}t")

        return y


    def generate_target_T8_sharpe_simplified(self, df: pd.DataFrame) -> pd.Series:
        """
        T8: Sharpe Ratio Simplified (per-trade)

        Target: (pnl - avg_daily_pnl) / std_daily_pnl, clippé à [-3, +3]

        Normalise le P&L par la volatilité daily.

        Args:
            df: DataFrame avec colonnes 'pnl_ticks', 'date'

        Returns:
            Series de floats (-3 à +3)
        """
        # Calculer P&L moyen et std par jour
        if 'date' not in df.columns:
            logger.warning("   ⚠️  'date' absent, simulation uniform")
            df['date'] = pd.date_range('2025-11-01', periods=len(df), freq='5min').date

        daily_stats = df.groupby('date')['pnl_ticks'].agg(['mean', 'std']).reset_index()
        daily_stats.columns = ['date', 'avg_daily', 'std_daily']

        # Merge avec df original
        df_merged = df.merge(daily_stats, on='date', how='left')

        # Calculer Sharpe per-trade
        sharpe = (df_merged['pnl_ticks'] - df_merged['avg_daily']) / df_merged['std_daily'].replace(0, 1)
        y = np.clip(sharpe, -3, 3)

        mean_sharpe = y.mean()
        median_sharpe = y.median()

        logger.info(f"   📊 T8 Sharpe Simplified: Mean={mean_sharpe:+.2f} | Median={median_sharpe:+.2f}")

        return pd.Series(y.values, index=df.index)


    def generate_target(
        self,
        df: pd.DataFrame,
        config: TargetConfig
    ) -> Tuple[pd.Series, str]:
        """
        Dispatcher pour générer une target selon config

        Args:
            df: DataFrame complet
            config: Configuration de la target (T1-T8)

        Returns:
            (y, task_type) où task_type = 'binary', 'regression', 'multiclass'
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 GÉNÉRATION TARGET: {config.name}")
        logger.info(f"{'='*70}")
        logger.info(f"   📝 Description: {config.description}")
        logger.info(f"   🎛️  Mode: {config.mode}")

        # Dispatcher
        generators = {
            'T1_binary_simple': self.generate_target_T1_binary_simple,
            'T2_binary_strong': self.generate_target_T2_binary_strong,
            'T3_pnl_ratio_reg': self.generate_target_T3_pnl_ratio_reg,
            'T4_pnl_ticks_capped': self.generate_target_T4_pnl_ticks_capped,
            'T5_multiclass': self.generate_target_T5_multiclass,
            'T6_quality_simplified': self.generate_target_T6_quality_simplified,
            'T7_expected_value': self.generate_target_T7_expected_value,
            'T8_sharpe_simplified': self.generate_target_T8_sharpe_simplified
        }

        if config.name not in generators:
            raise ValueError(f"❌ Target inconnue: {config.name}")

        generator = generators[config.name]
        y = generator(df)

        # Déterminer task_type
        if config.mode == 'classification':
            task_type = 'binary'
        elif config.mode == 'multiclass':
            task_type = 'multiclass'
        else:  # regression
            task_type = 'regression'

        logger.info(f"   ✅ Target générée: {len(y)} samples, task_type={task_type}")
        logger.info(f"{'='*70}\n")

        return y, task_type


    # ═══════════════════════════════════════════════════════════════════════
    # TRAINING ADAPTATIF
    # ═══════════════════════════════════════════════════════════════════════

    def train_model_adaptive(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        config: TargetConfig
    ) -> Any:
        """Training adaptatif selon type de target"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🧠 TRAINING ADAPTATIF: {config.name}")
        logger.info(f"{'='*70}")

        # Hyperparams optimaux (Optuna trial 78)
        best_params = {
            'num_leaves': 128,
            'max_depth': 8,
            'learning_rate': 0.0833,
            'n_estimators': 381,
            'min_child_samples': 19,
            'subsample': 0.8158,
            'colsample_bytree': 0.5439,
            'reg_alpha': 0.000114,
            'reg_lambda': 0.8095,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1
        }

        # Créer modèle selon mode
        if config.mode == 'classification':
            logger.info(f"   🎯 Mode: Binary Classification")
            model = LGBMClassifier(
                **best_params,
                objective='binary',
                class_weight='balanced',
                is_unbalance=True
            )
        elif config.mode == 'multiclass':
            logger.info(f"   🎯 Mode: Multiclass Classification (3 classes)")
            model = LGBMClassifier(
                **best_params,
                objective='multiclass',
                num_class=3,
                class_weight='balanced'
            )
        else:  # regression
            logger.info(f"   🎯 Mode: Regression")
            model = LGBMRegressor(
                **best_params,
                objective='regression'
            )

        # Scaling + Training
        logger.info(f"   🔧 Standardisation features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        logger.info(f"   🚀 Training...")
        start_time = datetime.now()

        model.fit(
            X_train_scaled,
            y_train,
            eval_set=[(X_val_scaled, y_val)],
            eval_metric='binary_logloss' if config.mode != 'regression' else 'rmse'
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"   ✅ Training terminé en {elapsed:.1f}s")
        logger.info(f"{'='*70}\n")

        return model


    # ═══════════════════════════════════════════════════════════════════════
    # LOGIQUES DE DÉCISION TRADE/SKIP
    # ═══════════════════════════════════════════════════════════════════════

    def _make_trading_decision_classification(self, pred_proba: float, threshold: float) -> bool:
        """Décision TRADE/SKIP pour classification binaire"""
        return pred_proba >= threshold

    def _make_trading_decision_regression(self, pred_value: float, min_threshold: float) -> bool:
        """Décision TRADE/SKIP pour régression"""
        return pred_value >= min_threshold

    def _make_trading_decision_multiclass(self, pred_proba_classes: np.ndarray, min_good_proba: float = 0.60) -> bool:
        """Décision TRADE/SKIP pour multiclass"""
        p_good = pred_proba_classes[2]  # Classe 2 = GOOD
        return p_good >= min_good_proba


    # ═══════════════════════════════════════════════════════════════════════
    # BACKTEST OUT-OF-SAMPLE
    # ═══════════════════════════════════════════════════════════════════════

    def backtest_model(self, model: Any, config: TargetConfig, X_test: pd.DataFrame, df_test: pd.DataFrame) -> TargetResult:
        """Backtest out-of-sample d'un modèle"""
        logger.info(f"\n{'='*70}")
        logger.info(f"💰 BACKTEST: {config.name}")
        logger.info(f"{'='*70}")

        # 1. Prédictions
        X_test_scaled = self.scaler.transform(X_test)

        if config.mode == 'classification':
            pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            preds = pred_proba
            threshold = config.params.get('threshold', 0.50)
            trade_mask = [self._make_trading_decision_classification(p, threshold) for p in pred_proba]
        elif config.mode == 'multiclass':
            pred_proba = model.predict_proba(X_test_scaled)
            preds = pred_proba
            min_good_proba = config.params.get('min_good_proba', 0.60)
            trade_mask = [self._make_trading_decision_multiclass(p, min_good_proba) for p in pred_proba]
        else:
            pred_values = model.predict(X_test_scaled)
            preds = pred_values
            min_threshold = config.params.get('min_threshold', 0.0)
            trade_mask = [self._make_trading_decision_regression(v, min_threshold) for v in pred_values]

        trade_mask = np.array(trade_mask)
        df_traded = df_test[trade_mask].copy()
        n_trades = len(df_traded)

        if n_trades == 0:
            logger.warning(f"   ⚠️  AUCUN TRADE PRIS!")
            return TargetResult(
                target_name=config.name, pnl_net=0.0, pnl_gross=0.0, pnl_per_trade=0.0,
                n_trades=0, winrate=0.0, sharpe=0.0, max_dd=0.0, metrics={}
            )

        # 2. Calcul P&L + Métriques
        pnl_gross = df_traded['pnl_ticks'].sum()
        fees_total = n_trades * self.fees_per_trade
        pnl_net = pnl_gross - fees_total
        pnl_per_trade = pnl_net / n_trades
        winrate = (df_traded['pnl_ticks'] > 0).mean()
        sharpe = self._calculate_sharpe_ratio(df_traded)
        max_dd = self._calculate_max_drawdown(df_traded)

        # 3. Métriques ML
        metrics = {}
        if config.mode == 'classification':
            y_true = (df_test['pnl_ticks'] > 0).astype(int)[trade_mask]
            y_pred = (preds[trade_mask] >= threshold).astype(int)
            metrics = {
                'accuracy': accuracy_score(y_true, y_pred),
                'precision': precision_score(y_true, y_pred, zero_division=0),
                'recall': recall_score(y_true, y_pred, zero_division=0),
                'f1_score': f1_score(y_true, y_pred, zero_division=0)
            }
        elif config.mode == 'regression':
            y_true = df_test['pnl_ticks'][trade_mask]
            y_pred = preds[trade_mask]
            metrics = {'mae': mean_absolute_error(y_true, y_pred), 'rmse': np.sqrt(mean_squared_error(y_true, y_pred))}

        logger.info(f"   📊 Trades: {n_trades:,} / {len(df_test):,} ({n_trades/len(df_test)*100:.1f}%)")
        logger.info(f"   💰 P&L net: {pnl_net:+,.1f}t | P&L/trade: {pnl_per_trade:+,.2f}t")
        logger.info(f"   📈 WR: {winrate*100:.1f}% | Sharpe: {sharpe:.2f} | MaxDD: {max_dd:.1f}%")
        logger.info(f"{'='*70}\n")

        return TargetResult(
            target_name=config.name,
            pnl_net=float(pnl_net),
            pnl_gross=float(pnl_gross),
            pnl_per_trade=float(pnl_per_trade),
            n_trades=int(n_trades),
            winrate=float(winrate),
            sharpe=float(sharpe),
            max_dd=float(max_dd),
            metrics=metrics
        )

    def _calculate_sharpe_ratio(self, df_trades: pd.DataFrame) -> float:
        """Calcule Sharpe Ratio daily annualisé"""
        if 'date' not in df_trades.columns or len(df_trades) < 2:
            return 0.0
        daily_pnl = df_trades.groupby('date')['pnl_ticks'].sum()
        if len(daily_pnl) < 2:
            return 0.0
        mean_daily = daily_pnl.mean()
        std_daily = daily_pnl.std()
        if std_daily == 0:
            return 0.0
        sharpe_daily = mean_daily / std_daily
        return sharpe_daily * np.sqrt(252)

    def _calculate_max_drawdown(self, df_trades: pd.DataFrame) -> float:
        """Calcule Max Drawdown en %"""
        cumulative_pnl = df_trades['pnl_ticks'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = running_max - cumulative_pnl
        max_dd_ticks = drawdown.max()
        if running_max.max() == 0:
            return 0.0
        return (max_dd_ticks / running_max.max()) * 100


    # ═══════════════════════════════════════════════════════════════════════
    # SÉLECTION MEILLEURE TARGET
    # ═══════════════════════════════════════════════════════════════════════

    def calculate_multi_objective_score(self, result: TargetResult, all_results: List[TargetResult]) -> float:
        """Calcule score multi-objectif normalisé 0-100 (50% P&L + 20% Sharpe + 15% Trades + 15% DD)"""
        pnl_nets = [r.pnl_net for r in all_results]
        sharpes = [r.sharpe for r in all_results]
        n_trades_list = [r.n_trades for r in all_results]
        max_dds = [r.max_dd for r in all_results]

        score_pnl = self._normalize_metric(result.pnl_net, min(pnl_nets), max(pnl_nets))
        score_sharpe = self._normalize_metric(result.sharpe, min(sharpes), max(sharpes))
        score_trades = self._normalize_metric(result.n_trades, min(n_trades_list), max(n_trades_list))
        score_dd = self._normalize_metric(result.max_dd, min(max_dds), max(max_dds), reverse=True)

        return 0.50 * score_pnl + 0.20 * score_sharpe + 0.15 * score_trades + 0.15 * score_dd

    def select_best_target(self, results: List[TargetResult], method: str = 'multi_objective') -> TargetResult:
        """Sélectionne la meilleure target"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🏆 SÉLECTION MEILLEURE TARGET")
        logger.info(f"{'='*70}")

        if method == 'multi_objective':
            for result in results:
                score = self.calculate_multi_objective_score(result, results)
                result.metrics['multi_objective_score'] = score
            results_sorted = sorted(results, key=lambda r: r.metrics['multi_objective_score'], reverse=True)
            best = results_sorted[0]
            logger.info(f"\n   📊 TOP 3:")
            for i, r in enumerate(results_sorted[:3], 1):
                logger.info(f"      {i}. {r.target_name}: Score={r.metrics['multi_objective_score']:.1f} | P&L={r.pnl_net:+,.0f}t")
        else:
            results_sorted = sorted(results, key=lambda r: r.pnl_net, reverse=True)
            best = results_sorted[0]

        logger.info(f"\n   🏆 MEILLEURE: {best.target_name} | P&L: {best.pnl_net:+,.1f}t | P&L/trade: {best.pnl_per_trade:+.2f}t")
        logger.info(f"{'='*70}\n")
        return best

    def validate_robustness(self, target_config: TargetConfig, n_splits: int = 3) -> Dict[str, float]:
        """Valide robustesse d'une target sur plusieurs splits temporels"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🔄 VALIDATION ROBUSTESSE: {target_config.name}")
        logger.info(f"{'='*70}")

        pnl_nets = []
        for i in range(n_splits):
            train_ratio = 0.55 + (i * 0.05)
            df = self._load_data()
            X_train, X_val, X_test, _, _, _ = self._temporal_split(df, train_ratio=train_ratio, val_ratio=0.20)

            y_train, _ = self.generate_target(df.loc[X_train.index], target_config)
            y_val, _ = self.generate_target(df.loc[X_val.index], target_config)

            model = self.train_model_adaptive(X_train, y_train, X_val, y_val, target_config)
            result = self.backtest_model(model, target_config, X_test, df.loc[X_test.index])
            pnl_nets.append(result.pnl_net)
            logger.info(f"      Split {i+1}/{n_splits}: P&L={result.pnl_net:+,.1f}t")

        mean_pnl = np.mean(pnl_nets)
        std_pnl = np.std(pnl_nets)
        logger.info(f"\n   📊 P&L moyen: {mean_pnl:+,.1f}t (±{std_pnl:.1f}t) | Stabilité: {std_pnl/abs(mean_pnl)*100:.1f}%")
        logger.info(f"{'='*70}\n")

        return {
            'mean_pnl_net': float(mean_pnl),
            'std_pnl_net': float(std_pnl),
            'min_pnl_net': float(np.min(pnl_nets)),
            'max_pnl_net': float(np.max(pnl_nets)),
            'stability_pct': float(std_pnl / abs(mean_pnl) * 100) if mean_pnl != 0 else 0.0
        }

    def run_optimization_pipeline(self, targets_to_test: Optional[List[TargetConfig]] = None) -> Tuple[List[TargetResult], TargetResult, Dict]:
        """Pipeline complet d'optimisation"""
        targets = targets_to_test or ALL_TARGETS
        logger.info(f"\n{'#'*70}")
        logger.info(f"##   🚀 PIPELINE OPTIMISATION TARGET - {len(targets)} targets")
        logger.info(f"{'#'*70}\n")

        df = self._load_data()
        X_train, X_val, X_test, _, _, _ = self._temporal_split(df)
        all_results = []

        for i, config in enumerate(targets, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"🎯 TARGET {i}/{len(targets)}: {config.name}")
            logger.info(f"{'='*70}")
            try:
                y_train, _ = self.generate_target(df.loc[X_train.index], config)
                y_val, _ = self.generate_target(df.loc[X_val.index], config)
                model = self.train_model_adaptive(X_train, y_train, X_val, y_val, config)
                result = self.backtest_model(model, config, X_test, df.loc[X_test.index])
                all_results.append(result)
            except Exception as e:
                logger.error(f"❌ Erreur: {e}")
                continue

        best_target = self.select_best_target(all_results)
        best_config = next(t for t in targets if t.name == best_target.target_name)
        validation_results = self.validate_robustness(best_config, n_splits=3)
        self.save_results(all_results, best_target, validation_results)

        logger.info(f"\n{'#'*70}")
        logger.info(f"##   ✅ PIPELINE TERMINÉ !")
        logger.info(f"{'#'*70}\n")
        return all_results, best_target, validation_results

    def save_results(self, all_results: List[TargetResult], best_target: TargetResult, validation_results: Dict):
        """Sauvegarde tous les résultats"""
        logger.info(f"\n{'='*70}")
        logger.info(f"💾 SAUVEGARDE RÉSULTATS")
        logger.info(f"{'='*70}")

        output_json = self.output_dir / "all_results.json"
        with open(output_json, 'w') as f:
            json.dump({
                'all_results': [r.to_dict() for r in all_results],
                'best_target': best_target.to_dict(),
                'validation': validation_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        logger.info(f"   ✅ {output_json}")

        best_json = self.output_dir / "best_target.json"
        with open(best_json, 'w') as f:
            json.dump({**best_target.to_dict(), 'validation': validation_results}, f, indent=2)
        logger.info(f"   ✅ {best_json}")

        df_comparison = self.generate_comparison_table(all_results)
        csv_path = self.output_dir / "comparison_table.csv"
        df_comparison.to_csv(csv_path, index=False)
        logger.info(f"   ✅ {csv_path}")
        logger.info(f"{'='*70}\n")

    def generate_comparison_table(self, results: List[TargetResult]) -> pd.DataFrame:
        """Génère tableau comparatif des résultats"""
        data = []
        for r in results:
            data.append({
                'Target': r.target_name,
                'P&L Net (t)': r.pnl_net,
                'P&L/Trade (t)': r.pnl_per_trade,
                'Trades': r.n_trades,
                'WinRate (%)': r.winrate * 100,
                'Sharpe': r.sharpe,
                'MaxDD (%)': r.max_dd,
                'Score': r.metrics.get('multi_objective_score', 0.0)
            })
        df = pd.DataFrame(data)
        return df.sort_values('Score', ascending=False).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════
# CONSTANTE: ALL_TARGETS (Catalogue des 8 targets à tester)
# ═══════════════════════════════════════════════════════════════════════

ALL_TARGETS = [
    TargetConfig(
        name='T1_binary_simple',
        mode='classification',
        params={'threshold': 0.45},
        description='Binary Classification Simple: y = (pnl_ticks > 0). Baseline actuelle.'
    ),
    TargetConfig(
        name='T2_binary_strong',
        mode='classification',
        params={'threshold': 0.50},
        description='Binary Classification Strong: y = (pnl_ratio >= 0.5). Évite petits wins.'
    ),
    TargetConfig(
        name='T3_pnl_ratio_reg',
        mode='regression',
        params={'min_threshold': 0.3},
        description='Regression P&L Ratio: Prédit R-multiple (-2 à +3). Trade si pred > 0.3R.'
    ),
    TargetConfig(
        name='T4_pnl_ticks_capped',
        mode='regression',
        params={'min_threshold': 2.0},
        description='Regression P&L Ticks: Prédit P&L (-20 à +20t). Trade si pred > 2t.'
    ),
    TargetConfig(
        name='T5_multiclass',
        mode='multiclass',
        params={'min_good_proba': 0.60},
        description='Multiclass (BAD/NEUTRAL/GOOD): Trade si P(GOOD) > 0.60.'
    ),
    TargetConfig(
        name='T6_quality_simplified',
        mode='regression',
        params={'min_threshold': 60},
        description='Regression Quality Score (0-100): Trade si quality > 60.'
    ),
    TargetConfig(
        name='T7_expected_value',
        mode='regression',
        params={'min_threshold': 1.0},
        description='Expected Value Direct: Trade si EV > 1.0 tick.'
    ),
    TargetConfig(
        name='T8_sharpe_simplified',
        mode='regression',
        params={'min_threshold': 0.5},
        description='Sharpe Ratio Simplified: Trade si sharpe_score > 0.5.'
    )
]
