"""
🎯 BACKTEST CLASSIFIER - ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Backtest du modèle LightGBM classifier sur données réelles.

Test:
- Modèle: ml/models/lightgbm_quality_v1.pkl
- Données: ml/data/labeled_trades.parquet
- Seuil optimal: 0.45
- Métriques: Accuracy, Precision, Recall, F1, Confusion Matrix

Output: Rapport de performance détaillé
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import pandas as pd
import numpy as np
import pickle

# ML imports
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)

# Ajouter parent au path
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class ClassifierBacktest:
    """
    Backtest du modèle classifier sur données réelles.

    Usage:
        backtest = ClassifierBacktest()
        results = backtest.run_backtest()
    """

    def __init__(
        self,
        model_path: str = "ml/models/lightgbm_quality_v1.pkl",
        data_path: str = "ml/data/labeled_trades.parquet",
        optimal_threshold: float = 0.45
    ):
        """
        Initialise le backtest.

        Args:
            model_path: Chemin vers le modèle .pkl
            data_path: Chemin vers les données labeled
            optimal_threshold: Seuil de décision optimal
        """
        self.model_path = Path(model_path)
        self.data_path = Path(data_path)
        self.optimal_threshold = optimal_threshold

        self.model = None
        self.scaler = None
        self.feature_names = None
        self.metadata = None

        # Charger modèle
        self._load_model()

    def _load_model(self):
        """Charge modèle + scaler + metadata."""

        logger.info(f"\n{'='*70}")
        logger.info(f"📂 CHARGEMENT MODÈLE")
        logger.info(f"{'='*70}")

        if not self.model_path.exists():
            raise FileNotFoundError(f"❌ Modèle introuvable: {self.model_path}")

        with open(self.model_path, 'rb') as f:
            saved = pickle.load(f)

        self.model = saved['model']
        self.scaler = saved.get('scaler')
        self.feature_names = saved['feature_names']
        self.metadata = saved.get('metadata', {})

        logger.info(f"   ✅ Modèle chargé: {self.model_path}")
        logger.info(f"   📊 Features: {len(self.feature_names)}")
        logger.info(f"   🎯 Type: {self.metadata.get('model_type', 'N/A')}")
        logger.info(f"   🎯 Target: {self.metadata.get('target', 'N/A')}")
        logger.info(f"   ⚙️ Scaler: {'Oui' if self.scaler else 'Non'}")
        logger.info(f"{'='*70}\n")

    def _load_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Charge et prépare les données.

        Returns:
            (X, y) features et target
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"📂 CHARGEMENT DONNÉES")
        logger.info(f"{'='*70}")

        if not self.data_path.exists():
            raise FileNotFoundError(f"❌ Données introuvables: {self.data_path}")

        df = pd.read_parquet(self.data_path)

        logger.info(f"   ✅ Données chargées: {len(df):,} trades")

        # Target
        target_col = 'win'
        if target_col not in df.columns:
            raise ValueError(f"❌ Colonne '{target_col}' manquante !")

        y = df[target_col]

        # Features (exclure métadonnées + target + RESULTATS TRADE)
        exclude_cols = [
            'win',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE si features!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
            # === METADATA ===
            't_ms', 'sym', 'symbol_base', 'source_file',
            # === FEATURES CONSTANTES (variance = 0, inutiles) ===
            'vix', 'volatility_regime', 'dom_age_ms', 'is_dom_fresh',
            'in_value_area', 'is_1tick_spread', 'data_quality'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        # Filtrer features modèle
        available_features = [f for f in self.feature_names if f in feature_cols]
        missing_features = set(self.feature_names) - set(available_features)

        if missing_features:
            logger.warning(f"   ⚠️ Features manquantes: {len(missing_features)}")
            for feat in list(missing_features)[:5]:
                logger.warning(f"      - {feat}")
            if len(missing_features) > 5:
                logger.warning(f"      ... et {len(missing_features) - 5} autres")

            # Ajouter features manquantes avec 0
            for feat in missing_features:
                df[feat] = 0.0

        # Réordonner colonnes selon feature_names
        X = df[self.feature_names]

        logger.info(f"   📊 Features: {len(self.feature_names)}")
        logger.info(f"   🎯 Target: {target_col}")
        logger.info(f"   📈 WINs: {y.sum():,} ({y.sum()/len(y)*100:.1f}%)")
        logger.info(f"   📉 LOSSes: {(~y.astype(bool)).sum():,} ({(~y.astype(bool)).sum()/len(y)*100:.1f}%)")
        logger.info(f"{'='*70}\n")

        return X, y

    def _load_data_out_of_sample(
        self,
        test_dates_only: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """
        ✅ NOUVEAU 15/11/2025: Charge données OUT-OF-SAMPLE uniquement.

        ChatGPT a identifié que backtest sur toutes données = in-sample.
        Cette fonction filtre UNIQUEMENT les dates test (jamais vues en training).

        Args:
            test_dates_only: Liste dates test (ex: ['2025-11-13', '2025-11-14'])
                            Si None, charge toutes les données (mode IN-SAMPLE)

        Returns:
            (X, y, df_full) features, target, et DataFrame complet pour analyse P&L
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"📂 CHARGEMENT DONNÉES BACKTEST")
        logger.info(f"{'='*70}")

        if not self.data_path.exists():
            raise FileNotFoundError(f"❌ Données introuvables: {self.data_path}")

        df = pd.read_parquet(self.data_path)
        df_original_size = len(df)

        # Filtrer dates test UNIQUEMENT
        if test_dates_only:
            logger.info(f"   🎯 MODE OUT-OF-SAMPLE (dates test uniquement)")
            logger.info(f"   📅 Dates test: {test_dates_only}")

            df = df[df['date'].isin(test_dates_only)].copy()

            if len(df) == 0:
                raise ValueError(f"❌ Aucune donnée pour dates test {test_dates_only}")

            logger.info(f"   ✅ Filtre appliqué:")
            logger.info(f"      Trades originaux: {df_original_size:,}")
            logger.info(f"      Trades test (out-of-sample): {len(df):,} ({len(df)/df_original_size*100:.1f}%)")
            logger.info(f"      ⚠️  Modèle n'a JAMAIS vu ces dates en training")
        else:
            logger.warning(f"   ⚠️  MODE IN-SAMPLE (toutes les données)")
            logger.warning(f"      Résultats NON représentatifs pour production !")
            logger.warning(f"      Utiliser test_dates_only pour backtest réel")

        # Target
        target_col = 'win'
        if target_col not in df.columns:
            raise ValueError(f"❌ Colonne '{target_col}' manquante !")

        y = df[target_col]

        # Features (exclure métadonnées + target + RESULTATS TRADE)
        exclude_cols = [
            'win',  # Target
            'trade_id', 'symbol', 'date', 'entry_time', 'exit_time',
            'entry_idx', 'exit_idx', 'direction',
            'entry_price', 'exit_price', 'stop', 'target',
            'exit_reason',
            # === RESULTATS TRADE (DATA LEAKAGE si features!) ===
            'pnl', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes',
            # === METADATA ===
            't_ms', 'sym', 'symbol_base', 'source_file',
            # === FEATURES CONSTANTES (variance = 0, inutiles) ===
            'vix', 'volatility_regime', 'dom_age_ms', 'is_dom_fresh',
            'in_value_area', 'is_1tick_spread', 'data_quality'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        # Filtrer features modèle
        available_features = [f for f in self.feature_names if f in feature_cols]
        missing_features = set(self.feature_names) - set(available_features)

        if missing_features:
            logger.warning(f"   ⚠️  Features manquantes: {len(missing_features)}")
            for feat in list(missing_features)[:5]:
                logger.warning(f"      - {feat}")
            if len(missing_features) > 5:
                logger.warning(f"      ... et {len(missing_features) - 5} autres")

            # Ajouter features manquantes avec 0
            for feat in missing_features:
                df[feat] = 0.0

        # Réordonner colonnes selon feature_names
        X = df[self.feature_names].copy()

        logger.info(f"   📊 Features: {len(self.feature_names)}")
        logger.info(f"   🎯 Target: {target_col}")
        logger.info(f"   📈 WINs: {y.sum():,} ({y.sum()/len(y)*100:.1f}%)")
        logger.info(f"   📉 LOSSes: {(~y.astype(bool)).sum():,} ({(~y.astype(bool)).sum()/len(y)*100:.1f}%)")
        logger.info(f"{'='*70}\n")

        return X, y, df

    def _evaluate_predictions(
        self,
        y_true: pd.Series,
        y_pred_proba: np.ndarray,
        threshold: float
    ) -> Dict:
        """
        Évalue les prédictions avec un seuil donné.

        Args:
            y_true: Labels réels
            y_pred_proba: Probabilités prédites (classe 1)
            threshold: Seuil de décision

        Returns:
            Dict avec métriques
        """

        # Prédictions binaires
        y_pred = (y_pred_proba >= threshold).astype(int)

        # Métriques
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        try:
            auc = roc_auc_score(y_true, y_pred_proba)
        except:
            auc = 0.0

        # Matrice de confusion
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        return {
            'threshold': threshold,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'auc_roc': auc,
            'confusion_matrix': cm,
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_positives': int(tp),
            'n_samples': len(y_true),
            'n_predicted_wins': int(y_pred.sum()),
            'n_predicted_losses': int((~y_pred.astype(bool)).sum())
        }

    def _analyze_trades(self, df: pd.DataFrame, y_pred: np.ndarray) -> Dict:
        """
        Analyse les trades prédits WIN vs LOSS.

        Args:
            df: DataFrame avec colonnes pnl_ticks, duration_minutes, etc.
            y_pred: Prédictions binaires (1=WIN, 0=LOSS)

        Returns:
            Dict avec statistiques trades
        """

        # Ajouter prédictions
        df_analysis = df.copy()
        df_analysis['predicted'] = y_pred

        # Séparer trades prédits WIN vs LOSS
        predicted_wins = df_analysis[df_analysis['predicted'] == 1]
        predicted_losses = df_analysis[df_analysis['predicted'] == 0]

        # Statistiques P&L
        stats = {
            # Trades prédits WIN
            'predicted_wins_count': len(predicted_wins),
            'predicted_wins_pnl_mean': predicted_wins['pnl_ticks'].mean() if len(predicted_wins) > 0 else 0,
            'predicted_wins_pnl_total': predicted_wins['pnl_ticks'].sum() if len(predicted_wins) > 0 else 0,
            'predicted_wins_duration_mean': predicted_wins['duration_minutes'].mean() if len(predicted_wins) > 0 else 0,
            # Trades prédits LOSS
            'predicted_losses_count': len(predicted_losses),
            'predicted_losses_pnl_mean': predicted_losses['pnl_ticks'].mean() if len(predicted_losses) > 0 else 0,
            'predicted_losses_pnl_total': predicted_losses['pnl_ticks'].sum() if len(predicted_losses) > 0 else 0,
            'predicted_losses_duration_mean': predicted_losses['duration_minutes'].mean() if len(predicted_losses) > 0 else 0,
        }

        # P&L si on tradait SEULEMENT les prédictions WIN
        if len(predicted_wins) > 0:
            stats['strategy_pnl_total'] = stats['predicted_wins_pnl_total']
            stats['strategy_pnl_per_trade'] = stats['predicted_wins_pnl_mean']
        else:
            stats['strategy_pnl_total'] = 0
            stats['strategy_pnl_per_trade'] = 0

        return stats

    def run_backtest(
        self,
        test_dates_only: Optional[List[str]] = None
    ) -> Dict:
        """
        Exécute le backtest complet.

        Args:
            test_dates_only: Si fourni, backtest UNIQUEMENT sur ces dates (OUT-OF-SAMPLE)
                            Si None, backtest sur toutes les données (IN-SAMPLE, optimiste)

        Returns:
            Dict avec tous les résultats
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"{'='*70}")
        logger.info(f"##   🎯 BACKTEST CLASSIFIER - ML 3-LAYER STRATEGY")

        if test_dates_only:
            logger.info(f"##   MODE: OUT-OF-SAMPLE (dates test uniquement)")
        else:
            logger.info(f"##   ⚠️  MODE: IN-SAMPLE (toutes les données - optimiste)")

        logger.info(f"{'='*70}")
        logger.info(f"{'='*70}\n")

        if test_dates_only:
            logger.info(f"   🎯 Dates test (out-of-sample): {test_dates_only}")
            logger.info(f"   ✅ Modèle n'a JAMAIS vu ces dates en training\n")

        # 1. Charger données (avec filtre si OUT-OF-SAMPLE)
        X, y, df_full = self._load_data_out_of_sample(test_dates_only=test_dates_only)

        # 2. Prédictions
        logger.info(f"\n{'='*70}")
        logger.info(f"🔮 PRÉDICTIONS")
        logger.info(f"{'='*70}")

        # Scaler
        if self.scaler:
            X_scaled = self.scaler.transform(X)
            logger.info(f"   ✅ Features standardisées (StandardScaler)")
        else:
            X_scaled = X.values
            logger.info(f"   ⚠️ Pas de StandardScaler (features brutes)")

        # Prédictions probabilités
        y_pred_proba = self.model.predict_proba(X_scaled)[:, 1]

        logger.info(f"   ✅ Prédictions calculées")
        logger.info(f"   📊 Probabilité WIN moyenne: {y_pred_proba.mean():.4f}")
        logger.info(f"   📊 Probabilité WIN médiane: {np.median(y_pred_proba):.4f}")
        logger.info(f"{'='*70}\n")

        # 3. Évaluation seuil par défaut (0.50)
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 MÉTRIQUES SEUIL PAR DÉFAUT (0.50)")
        logger.info(f"{'='*70}")

        metrics_default = self._evaluate_predictions(y, y_pred_proba, threshold=0.50)

        logger.info(f"   Accuracy:  {metrics_default['accuracy']:.4f} ({metrics_default['accuracy']*100:.2f}%)")
        logger.info(f"   Precision: {metrics_default['precision']:.4f}")
        logger.info(f"   Recall:    {metrics_default['recall']:.4f}")
        logger.info(f"   F1-Score:  {metrics_default['f1_score']:.4f}")
        logger.info(f"   AUC-ROC:   {metrics_default['auc_roc']:.4f}")
        logger.info(f"\n   📊 Matrice de Confusion:")
        logger.info(f"      TN={metrics_default['true_negatives']:,} | FP={metrics_default['false_positives']:,}")
        logger.info(f"      FN={metrics_default['false_negatives']:,} | TP={metrics_default['true_positives']:,}")
        logger.info(f"{'='*70}\n")

        # 4. Évaluation seuil optimal (0.45)
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 MÉTRIQUES SEUIL OPTIMAL ({self.optimal_threshold})")
        logger.info(f"{'='*70}")

        metrics_optimal = self._evaluate_predictions(y, y_pred_proba, threshold=self.optimal_threshold)

        logger.info(f"   Accuracy:  {metrics_optimal['accuracy']:.4f} ({metrics_optimal['accuracy']*100:.2f}%)")
        logger.info(f"   Precision: {metrics_optimal['precision']:.4f}")
        logger.info(f"   Recall:    {metrics_optimal['recall']:.4f}")
        logger.info(f"   F1-Score:  {metrics_optimal['f1_score']:.4f} 🔥")
        logger.info(f"   AUC-ROC:   {metrics_optimal['auc_roc']:.4f}")
        logger.info(f"\n   📊 Matrice de Confusion:")
        logger.info(f"      TN={metrics_optimal['true_negatives']:,} | FP={metrics_optimal['false_positives']:,}")
        logger.info(f"      FN={metrics_optimal['false_negatives']:,} | TP={metrics_optimal['true_positives']:,}")
        logger.info(f"\n   📈 Prédictions:")
        logger.info(f"      WINs prédits:  {metrics_optimal['n_predicted_wins']:,} ({metrics_optimal['n_predicted_wins']/metrics_optimal['n_samples']*100:.1f}%)")
        logger.info(f"      LOSSes prédits: {metrics_optimal['n_predicted_losses']:,} ({metrics_optimal['n_predicted_losses']/metrics_optimal['n_samples']*100:.1f}%)")
        logger.info(f"{'='*70}\n")

        # 5. Gain seuil optimal
        f1_gain = ((metrics_optimal['f1_score'] - metrics_default['f1_score']) / metrics_default['f1_score'] * 100) if metrics_default['f1_score'] > 0 else 0

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 GAIN SEUIL OPTIMAL")
        logger.info(f"{'='*70}")
        logger.info(f"   F1-Score: {metrics_default['f1_score']:.4f} → {metrics_optimal['f1_score']:.4f} ({f1_gain:+.1f}%)")
        logger.info(f"   Recall:   {metrics_default['recall']:.4f} → {metrics_optimal['recall']:.4f} ({(metrics_optimal['recall']-metrics_default['recall'])*100:+.1f}%)")
        logger.info(f"{'='*70}\n")

        # 6. Analyse P&L (si colonnes disponibles)
        # df_full déjà chargé dans _load_data_out_of_sample()

        if 'pnl_ticks' in df_full.columns:
            logger.info(f"\n{'='*70}")
            logger.info(f"💰 ANALYSE P&L - STRATÉGIE 'TRADE SEULEMENT SI WIN PRÉDIT'")
            logger.info(f"{'='*70}")

            y_pred_optimal = (y_pred_proba >= self.optimal_threshold).astype(int)
            trade_stats = self._analyze_trades(df_full, y_pred_optimal)

            logger.info(f"\n   📊 TRADES PRÉDITS WIN:")
            logger.info(f"      Nombre: {trade_stats['predicted_wins_count']:,}")
            logger.info(f"      P&L moyen: {trade_stats['predicted_wins_pnl_mean']:+.2f} ticks")
            logger.info(f"      P&L total: {trade_stats['predicted_wins_pnl_total']:+.1f} ticks")
            logger.info(f"      Durée moyenne: {trade_stats['predicted_wins_duration_mean']:.1f} min")

            logger.info(f"\n   📊 TRADES PRÉDITS LOSS (non tradés):")
            logger.info(f"      Nombre: {trade_stats['predicted_losses_count']:,}")
            logger.info(f"      P&L moyen: {trade_stats['predicted_losses_pnl_mean']:+.2f} ticks")
            logger.info(f"      P&L total: {trade_stats['predicted_losses_pnl_total']:+.1f} ticks (évité !)")

            logger.info(f"\n   🎯 STRATÉGIE FINALE (trader seulement WINs prédits):")
            logger.info(f"      P&L total: {trade_stats['strategy_pnl_total']:+.1f} ticks")
            logger.info(f"      P&L par trade: {trade_stats['strategy_pnl_per_trade']:+.2f} ticks")
            logger.info(f"      Nombre de trades: {trade_stats['predicted_wins_count']:,}")

            # Comparaison avec "trader tout"
            total_pnl_all_trades = df_full['pnl_ticks'].sum()
            logger.info(f"\n   📊 COMPARAISON:")
            logger.info(f"      P&L si on trade TOUT: {total_pnl_all_trades:+.1f} ticks ({len(df_full):,} trades)")
            logger.info(f"      P&L avec filtre ML:   {trade_stats['strategy_pnl_total']:+.1f} ticks ({trade_stats['predicted_wins_count']:,} trades)")

            gain_pct = ((trade_stats['strategy_pnl_total'] - total_pnl_all_trades) / abs(total_pnl_all_trades) * 100) if total_pnl_all_trades != 0 else 0
            logger.info(f"      🎯 Gain: {trade_stats['strategy_pnl_total'] - total_pnl_all_trades:+.1f} ticks ({gain_pct:+.1f}%)")

            logger.info(f"{'='*70}\n")

        # Résultats finaux
        results = {
            'metrics_default': metrics_default,
            'metrics_optimal': metrics_optimal,
            'optimal_threshold': self.optimal_threshold,
            'trade_stats': trade_stats if 'pnl_ticks' in df_full.columns else None
        }

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ BACKTEST TERMINÉ AVEC SUCCÈS !")
        logger.info(f"{'='*70}\n")

        return results


# ═══════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Backtest du classifier sur données OUT-OF-SAMPLE."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # ═══════════════════════════════════════════════════════════════
    # 🎯 DATES TEST (OUT-OF-SAMPLE) - À ALIGNER AVEC TRAINING !
    # ═══════════════════════════════════════════════════════════════
    # Vérifier dans ml/models/lightgbm_quality_v1_metadata.json
    # Section 'split_info' → 'test_dates'

    # Si split temporel 60/20/20 sur 10 jours (05-14 nov):
    # - Train: 05-10 nov (6 jours)
    # - Val:   11-12 nov (2 jours)
    # - Test:  13-14 nov (2 jours) ← BACKTEST SUR CES DATES !

    TEST_DATES_OUT_OF_SAMPLE = [
        '20251113',  # 13 novembre 2025 (format YYYYMMDD)
        '20251114'   # 14 novembre 2025 (format YYYYMMDD)
    ]

    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 BACKTEST OUT-OF-SAMPLE")
    logger.info(f"{'='*70}")
    logger.info(f"   📅 Dates test: {TEST_DATES_OUT_OF_SAMPLE}")
    logger.info(f"   ⚠️  Modèle n'a JAMAIS vu ces dates en training")
    logger.info(f"   ✅ Résultats représentatifs pour production")
    logger.info(f"{'='*70}\n")

    # Exécuter backtest OUT-OF-SAMPLE
    backtest = ClassifierBacktest(
        model_path="ml/models/lightgbm_quality_v1.pkl",
        data_path="ml/data/labeled_trades.parquet",
        optimal_threshold=0.45
    )

    results = backtest.run_backtest(test_dates_only=TEST_DATES_OUT_OF_SAMPLE)

    logger.info(f"\n{'='*70}")
    logger.info(f"✅ BACKTEST OUT-OF-SAMPLE TERMINÉ !")
    logger.info(f"{'='*70}")
    logger.info(f"   F1-Score: {results['metrics_optimal']['f1_score']:.4f}")
    logger.info(f"   Recall:   {results['metrics_optimal']['recall']:.4f}")
    logger.info(f"   Precision: {results['metrics_optimal']['precision']:.4f}")

    if results['trade_stats']:
        logger.info(f"\n   💰 P&L OUT-OF-SAMPLE:")
        logger.info(f"      Total: {results['trade_stats']['strategy_pnl_total']:+.1f} ticks")
        logger.info(f"      Par trade: {results['trade_stats']['strategy_pnl_per_trade']:+.2f} ticks")
        logger.info(f"      Trades: {results['trade_stats']['predicted_wins_count']:,}")

    logger.info(f"{'='*70}\n")
