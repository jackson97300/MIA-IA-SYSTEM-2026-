#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GRID SEARCH THRESHOLDS - Calibration seuils ML par Profit Factor
═══════════════════════════════════════════════════════════════════════════════

Trouve les seuils optimaux par symbole et sens pour maximiser le Profit Factor

Usage:
    # ES LONG
    python ml/grid_search_thresholds.py --symbol ES --side UP --thr-min 0.58 --thr-max 0.72

    # NQ SHORT
    python ml/grid_search_thresholds.py --symbol NQ --side DOWN --thr-min 0.54 --thr-max 0.68

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_data(symbol: str, data_dir: Path = Path(".")):
    """
    Charge données test sauvegardées lors de l'entraînement

    TODO: Adapter selon votre format
    """
    test_file = data_dir / f"ml/models_robust/test_data_{symbol}_binary.pkl"

    if not test_file.exists():
        logger.error(f"❌ Fichier test non trouvé : {test_file}")
        logger.error("   Relancez l'entraînement avec sauvegarde des données test")
        sys.exit(1)

    with open(test_file, 'rb') as f:
        data = pickle.load(f)

    return data['X_test'], data['y_test'], data['feature_names']


def load_model(symbol: str, models_dir: Path = Path("ml/models_robust")):
    """Charge modèle binaire"""
    # Chercher dernier modèle
    model_files = list(models_dir.glob(f"*{symbol}*binary*.pkl")) + \
                  list(models_dir.glob(f"*{symbol}*ensemble*.pkl"))

    # Exclure fichiers test_data_*.pkl
    model_files = [f for f in model_files if not f.name.startswith("test_data_")]

    if not model_files:
        logger.error(f"❌ Aucun modèle trouvé pour {symbol}")
        sys.exit(1)

    # Prendre le plus récent
    model_file = max(model_files, key=lambda p: p.stat().st_mtime)

    logger.info(f"📁 Chargement modèle : {model_file}")

    with open(model_file, 'rb') as f:
        models = pickle.load(f)

    # Si c'est un ensemble (liste), on retourne le wrapper
    if isinstance(models, list):
        logger.info(f"   Ensemble de {len(models)} modèles détecté")
        return EnsembleWrapper(models)

    return models


class EnsembleWrapper:
    """Wrapper pour ensembles de modèles"""
    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        """Moyenne des prédictions"""
        probas = np.array([model.predict_proba(X) for model in self.models])
        return probas.mean(axis=0)


def simulate_profit_factor(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    side: str,
    threshold: float,
    avg_win: float = 1.0,
    avg_loss: float = 1.0
) -> Dict:
    """
    Simule PF avec un seuil donné

    Args:
        y_true: Labels vrais (0=DOWN, 1=UP)
        y_proba: Probas [P(DOWN), P(UP)]
        side: "UP" ou "DOWN"
        threshold: Seuil de confiance
        avg_win: Gain moyen (en ticks)
        avg_loss: Perte moyenne (en ticks)

    Returns:
        Dict avec métriques
    """
    # Sélectionner proba selon le sens
    if side == "UP":
        conf = y_proba[:, 1]  # P(UP)
        signal = 1  # On cherche UP
    else:  # DOWN
        conf = y_proba[:, 0]  # P(DOWN)
        signal = 0  # On cherche DOWN

    # Filtre : accepter seulement si conf >= threshold
    mask = conf >= threshold

    # Si aucun signal accepté
    if mask.sum() == 0:
        return {
            "threshold": threshold,
            "n_signals": 0,
            "n_accepted": 0,
            "n_rejected": int(len(y_true)),
            "accept_rate": 0.0,
            "accuracy": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0
        }

    # Signaux acceptés
    y_true_filtered = y_true[mask]
    y_pred_filtered = np.full(mask.sum(), signal)

    # Accuracy sur signaux acceptés
    accuracy = accuracy_score(y_true_filtered, y_pred_filtered)

    # Calcul PnL simplifié
    correct = (y_true_filtered == signal)
    wins = correct.sum()
    losses = (~correct).sum()

    win_rate = wins / len(y_true_filtered) if len(y_true_filtered) > 0 else 0

    total_wins = wins * avg_win
    total_losses = losses * avg_loss

    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    total_pnl = total_wins - total_losses

    return {
        "threshold": threshold,
        "n_signals": int(len(y_true)),
        "n_accepted": int(mask.sum()),
        "n_rejected": int((~mask).sum()),
        "accept_rate": float(mask.sum() / len(y_true) * 100),
        "accuracy": float(accuracy),
        "win_rate": float(win_rate * 100),
        "profit_factor": float(profit_factor),
        "total_pnl": float(total_pnl),
        "n_wins": int(wins),
        "n_losses": int(losses)
    }


def grid_search(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: List[str],
    side: str,
    thr_min: float = 0.50,
    thr_max: float = 0.80,
    thr_step: float = 0.01,
    avg_win: float = 3.0,
    avg_loss: float = 3.0
) -> pd.DataFrame:
    """
    Grid search des seuils

    Returns:
        DataFrame avec résultats
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 GRID SEARCH THRESHOLDS - {side}")
    logger.info(f"{'='*70}")
    logger.info(f"   Range : {thr_min:.2f} → {thr_max:.2f} (step {thr_step})")
    logger.info(f"   Avg win : {avg_win} ticks")
    logger.info(f"   Avg loss : {avg_loss} ticks")

    # Prédiction
    # Convertir en float (X_test peut être en dtype object)
    X_test_float = np.array(X_test, dtype=float)
    X_test_df = pd.DataFrame(X_test_float, columns=feature_names)
    y_proba = model.predict_proba(X_test_df)

    # Grid
    thresholds = np.arange(thr_min, thr_max + thr_step, thr_step)
    results = []

    for thr in thresholds:
        metrics = simulate_profit_factor(y_test, y_proba, side, thr, avg_win, avg_loss)
        results.append(metrics)

        # Log tous les 5%
        if int(thr * 100) % 5 == 0:
            logger.info(f"   thr={thr:.2f} : PF={metrics['profit_factor']:.2f}, "
                       f"WR={metrics['win_rate']:.1f}%, "
                       f"accept={metrics['accept_rate']:.1f}%")

    df = pd.DataFrame(results)
    return df


def main(args):
    """Main"""

    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 CALIBRATION SEUILS ML - {args.symbol}/{args.side}")
    logger.info(f"{'='*70}\n")

    # Charger modèle
    model = load_model(args.symbol, Path(args.models_dir))

    # Charger données test (si disponibles)
    # Sinon, réentraîner ou utiliser un jeu de validation
    try:
        X_test, y_test, feature_names = load_test_data(args.symbol, Path(args.data_dir))
        logger.info(f"✅ Données test chargées : {len(X_test)} samples")
    except:
        logger.warning("⚠️ Données test non disponibles")
        logger.warning("   Utilisation des données d'entraînement (attention overfitting)")
        # TODO: Charger depuis ML_READY et recréer features
        sys.exit(1)

    # Grid search
    results_df = grid_search(
        model, X_test, y_test, feature_names,
        args.side,
        args.thr_min, args.thr_max, args.thr_step,
        args.avg_win, args.avg_loss
    )

    # Trouver meilleur seuil (max PF)
    best_idx = results_df['profit_factor'].idxmax()
    best = results_df.loc[best_idx]

    logger.info(f"\n{'='*70}")
    logger.info(f"🏆 MEILLEUR SEUIL (max Profit Factor)")
    logger.info(f"{'='*70}")
    logger.info(f"   Threshold : {best['threshold']:.3f}")
    logger.info(f"   Profit Factor : {best['profit_factor']:.2f}")
    logger.info(f"   Win Rate : {best['win_rate']:.1f}%")
    logger.info(f"   Accept Rate : {best['accept_rate']:.1f}%")
    logger.info(f"   Accuracy : {best['accuracy']:.1f}%")
    logger.info(f"   Total PnL : {best['total_pnl']:.1f} ticks")
    logger.info(f"   Wins/Losses : {best['n_wins']}/{best['n_losses']}")
    logger.info(f"{'='*70}\n")

    # Sauvegarder résultats
    output_file = Path(args.output_dir) / f"threshold_grid_{args.symbol}_{args.side}.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_file, index=False)
    logger.info(f"💾 Résultats sauvegardés : {output_file}")

    # Sauvegarder best threshold
    best_file = Path(args.output_dir) / f"best_threshold_{args.symbol}_{args.side}.json"
    with open(best_file, 'w') as f:
        json.dump({
            "symbol": args.symbol,
            "side": args.side,
            "threshold": float(best['threshold']),
            "profit_factor": float(best['profit_factor']),
            "win_rate": float(best['win_rate']),
            "accept_rate": float(best['accept_rate']),
            "accuracy": float(best['accuracy'])
        }, f, indent=2)
    logger.info(f"💾 Best threshold sauvegardé : {best_file}")

    # Top 5
    logger.info(f"\n📊 TOP 5 THRESHOLDS (par PF) :")
    top5 = results_df.nlargest(5, 'profit_factor')
    print(top5[['threshold', 'profit_factor', 'win_rate', 'accept_rate', 'accuracy']].to_string(index=False))
    logger.info("")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Calibration seuils ML par Profit Factor"
    )

    parser.add_argument('--symbol', type=str, required=True, choices=['ES', 'NQ'])
    parser.add_argument('--side', type=str, required=True, choices=['UP', 'DOWN'])
    parser.add_argument('--thr-min', type=float, default=0.50)
    parser.add_argument('--thr-max', type=float, default=0.80)
    parser.add_argument('--thr-step', type=float, default=0.01)
    parser.add_argument('--avg-win', type=float, default=3.0, help="Gain moyen en ticks")
    parser.add_argument('--avg-loss', type=float, default=3.0, help="Perte moyenne en ticks")
    parser.add_argument('--data-dir', type=str, default=".")
    parser.add_argument('--models-dir', type=str, default="ml/models_robust")
    parser.add_argument('--output-dir', type=str, default="ml/threshold_calibration")

    args = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        sys.exit(1)
