#!/usr/bin/env python3
"""
Optimisation des seuils de décision pour T1, T4 et T7
En utilisant les PRÉDICTIONS des modèles (pas les vraies valeurs)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pickle
import logging
from typing import Dict, List
from sklearn.preprocessing import StandardScaler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_model_and_scaler(model_path: str):
    """Charge le modèle et scaler"""
    with open(model_path, 'rb') as f:
        data = pickle.load(f)

    model = data.get('model')
    scaler = data.get('scaler')

    return model, scaler


def load_test_data(data_path: str, test_dates: List[str]):
    """Charge les données de test"""
    df = pd.read_parquet(data_path)

    # Créer sl_ticks si nécessaire
    if 'stop' in df.columns and 'sl_ticks' not in df.columns:
        df['sl_ticks'] = abs(df['stop'] - df['entry_price']) * 4

    # Filtrer période test
    df_test = df[df['date'].isin(test_dates)].copy()

    return df_test


def prepare_features(df: pd.DataFrame, feature_names: List[str]):
    """Prépare les features pour prédiction"""
    # Sélectionner seulement les features du modèle
    available_features = [f for f in feature_names if f in df.columns]

    if len(available_features) != len(feature_names):
        missing = set(feature_names) - set(available_features)
        logger.warning(f"Features manquantes: {missing}")

    X = df[available_features].copy()

    # Remplacer NaN par 0
    X = X.fillna(0)

    return X


def backtest_with_predictions(
    df: pd.DataFrame,
    predictions: np.ndarray,
    threshold: float,
    target_name: str,
    decision_type: str,
    fees: float = 0.62
) -> Dict:
    """Backtest avec prédictions du modèle"""

    # Décision TRADE/SKIP basée sur prédictions
    if decision_type == 'classification':
        # predictions = probabilités [proba_loss, proba_win]
        proba_win = predictions[:, 1] if predictions.ndim > 1 else predictions
        trades_taken = proba_win > threshold
    elif decision_type == 'regression':
        # predictions = valeurs continues
        trades_taken = predictions > threshold
    else:
        raise ValueError(f"decision_type invalide: {decision_type}")

    # Trades effectués
    df_trades = df[trades_taken].copy()
    n_trades = len(df_trades)

    if n_trades == 0:
        return {
            'target': target_name,
            'threshold': threshold,
            'n_trades': 0,
            'pnl_gross': 0.0,
            'pnl_net': 0.0,
            'pnl_per_trade': 0.0,
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0
        }

    # Calculer P&L réel
    pnl_gross = df_trades['pnl_ticks'].sum()
    pnl_net = pnl_gross - (n_trades * fees)
    pnl_per_trade = pnl_net / n_trades

    # Métriques
    wins = df_trades[df_trades['pnl_ticks'] > 0]
    losses = df_trades[df_trades['pnl_ticks'] <= 0]

    winrate = len(wins) / n_trades if n_trades > 0 else 0.0
    avg_win = wins['pnl_ticks'].mean() if len(wins) > 0 else 0.0
    avg_loss = losses['pnl_ticks'].mean() if len(losses) > 0 else 0.0

    gross_profit = wins['pnl_ticks'].sum() if len(wins) > 0 else 0.0
    gross_loss = abs(losses['pnl_ticks'].sum()) if len(losses) > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    return {
        'target': target_name,
        'threshold': threshold,
        'n_trades': n_trades,
        'pnl_gross': pnl_gross,
        'pnl_net': pnl_net,
        'pnl_per_trade': pnl_per_trade,
        'winrate': winrate * 100,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor
    }


def optimize_target(
    target_name: str,
    model_path: str,
    data_path: str,
    test_dates: List[str],
    thresholds: List[float],
    decision_type: str,
    fees: float = 0.62
):
    """Optimise les seuils pour une target donnée"""

    logger.info("\n" + "="*70)
    logger.info(f"OPTIMISATION: {target_name}")
    logger.info("="*70)

    # Charger modèle
    logger.info(f"\nChargement modele: {model_path}")
    model, scaler = load_model_and_scaler(model_path)

    if model is None:
        logger.error(f"   ERREUR: Impossible de charger le modele")
        return []

    logger.info(f"   Modele: {type(model).__name__}")

    # Charger données test
    logger.info(f"\nChargement donnees test...")
    df_test = load_test_data(data_path, test_dates)
    logger.info(f"   Trades test: {len(df_test):,}")

    # Préparer features
    feature_names = model.feature_name_ if hasattr(model, 'feature_name_') else []
    logger.info(f"   Features: {len(feature_names)}")

    X_test = prepare_features(df_test, feature_names)

    # Standardiser
    if scaler is not None:
        X_test = scaler.transform(X_test)

    # Faire prédictions
    logger.info(f"\nPredictions...")
    if decision_type == 'classification':
        predictions = model.predict_proba(X_test)
        logger.info(f"   Proba WIN moyenne: {predictions[:, 1].mean():.3f}")
        logger.info(f"   Proba WIN mediane: {np.median(predictions[:, 1]):.3f}")
    else:
        predictions = model.predict(X_test)
        logger.info(f"   Prediction moyenne: {predictions.mean():+.2f}")
        logger.info(f"   Prediction mediane: {np.median(predictions):+.2f}")

    # Tester chaque seuil
    logger.info(f"\n{'='*70}")
    logger.info(f"TEST SEUILS")
    logger.info(f"{'='*70}")

    results = []
    for threshold in thresholds:
        result = backtest_with_predictions(
            df_test, predictions, threshold, target_name, decision_type, fees
        )
        results.append(result)

        logger.info(f"\n--- Seuil: {threshold:.2f} ---")
        logger.info(f"   Trades: {result['n_trades']:,} / {len(df_test):,} ({result['n_trades']/len(df_test)*100:.1f}%)")
        logger.info(f"   P&L net: {result['pnl_net']:+,.1f}t")
        logger.info(f"   P&L/trade: {result['pnl_per_trade']:+.2f}t")
        logger.info(f"   WinRate: {result['winrate']:.1f}%")
        logger.info(f"   Profit Factor: {result['profit_factor']:.2f}")

    return results


def main():
    """Point d'entrée principal"""

    logger.info("\n" + "="*70)
    logger.info("OPTIMISATION SEUILS - PREDICTIONS MODELES")
    logger.info("="*70)

    # Configuration
    DATA_PATH = "ml/data/labeled_trades.parquet"
    TEST_DATES = ['20251113', '20251114']
    FEES = 0.62

    # Modèles à tester (si disponibles)
    targets_config = [
        {
            'name': 'T1_binary_simple',
            'model_path': 'ml/models/lightgbm_t1_binary_simple.pkl',
            'thresholds': [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
            'decision_type': 'classification'
        },
        {
            'name': 'T4_pnl_ticks_capped',
            'model_path': 'ml/models/lightgbm_t4_pnl_ticks_capped.pkl',
            'thresholds': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            'decision_type': 'regression'
        }
    ]

    all_results = []

    # Tester chaque target
    for config in targets_config:
        model_path = Path(config['model_path'])

        if not model_path.exists():
            logger.warning(f"\nModele introuvable: {model_path}")
            logger.warning(f"   Skipping {config['name']}")
            continue

        results = optimize_target(
            target_name=config['name'],
            model_path=str(model_path),
            data_path=DATA_PATH,
            test_dates=TEST_DATES,
            thresholds=config['thresholds'],
            decision_type=config['decision_type'],
            fees=FEES
        )

        all_results.extend(results)

    if len(all_results) == 0:
        logger.error("\nAUCUN resultat genere")
        return 1

    # Créer DataFrame résultats
    df_results = pd.DataFrame(all_results)

    # Sauvegarder
    output_path = Path("ml/6_TARGET_OPTIMIZATION/results/threshold_optimization_predictions.csv")
    df_results.to_csv(output_path, index=False)
    logger.info(f"\n\nResultats sauvegardes: {output_path}")

    # Analyse globale
    logger.info("\n" + "="*70)
    logger.info("ANALYSE GLOBALE")
    logger.info("="*70)

    # Meilleurs résultats par target
    for target_name in df_results['target'].unique():
        df_target = df_results[df_results['target'] == target_name]

        # Meilleur P&L/trade
        best = df_target.loc[df_target['pnl_per_trade'].idxmax()]

        logger.info(f"\n{target_name}:")
        logger.info(f"   Meilleur seuil: {best['threshold']:.2f}")
        logger.info(f"   P&L/trade: {best['pnl_per_trade']:+.2f}t")
        logger.info(f"   P&L net: {best['pnl_net']:+,.1f}t")
        logger.info(f"   Trades: {best['n_trades']:.0f}")
        logger.info(f"   WinRate: {best['winrate']:.1f}%")

        # Vérifier si objectif atteint
        if best['pnl_per_trade'] >= 1.0:
            logger.info(f"   OBJECTIF +1.0t/trade: OK")
        else:
            logger.info(f"   OBJECTIF +1.0t/trade: NON ATTEINT (manque {1.0 - best['pnl_per_trade']:.2f}t)")

    logger.info("\n" + "="*70)
    logger.info("OPTIMISATION TERMINEE")
    logger.info("="*70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
