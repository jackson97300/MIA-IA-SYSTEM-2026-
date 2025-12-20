"""
BACKTEST DU MODELE LIGHTGBM SUR DONNEES REELLES
================================================

Charge le modele LightGBM entraine et le teste sur les trades labelises
pour comparer les predictions vs les quality scores reels.

Metriques:
- MAE, RMSE, R2, MAPE
- Distribution erreurs
- Performance par symbole
- Performance par outcome (WIN/LOSS)
- Correlation predictions vs scores reels
"""

import sys
from pathlib import Path

# Ajouter le chemin parent pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import logging
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour eviter erreurs display
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.lightgbm_predictor import LightGBMPredictor

class LightGBMBacktester:
    """Backteste le modele LightGBM sur donnees reelles."""

    def __init__(self, model_path: Path, labeled_trades_path: Path, output_dir: Path = Path("ml/backtest_results")):
        self.model_path = model_path
        self.labeled_trades_path = labeled_trades_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Backtester initialise")
        logger.info(f"   Modele: {model_path}")
        logger.info(f"   Trades: {labeled_trades_path}")
        logger.info(f"   Output: {output_dir}")

    def run_backtest(self):
        """Execute le backtest complet."""
        logger.info("\n" + "="*70)
        logger.info("BACKTEST LIGHTGBM - DONNEES REELLES")
        logger.info("="*70 + "\n")

        # 1. Charger le modele
        logger.info("1. CHARGEMENT MODELE...")
        predictor = LightGBMPredictor.load(str(self.model_path))
        model_info = predictor.get_model_info()
        logger.info(f"   OK - Modele charge")
        logger.info(f"   Type: {model_info['model_type']}")
        logger.info(f"   Features: {model_info['n_features']}")

        # 2. Charger les trades labelises
        logger.info("\n2. CHARGEMENT TRADES LABELISES...")
        df_trades = pd.read_parquet(self.labeled_trades_path)
        logger.info(f"   OK - {len(df_trades):,} trades charges")
        logger.info(f"   Colonnes: {len(df_trades.columns)}")

        # 3. Faire predictions sur tous les trades
        logger.info("\n3. PREDICTIONS SUR TOUS LES TRADES...")
        predictions = []
        errors = []

        for idx, row in df_trades.iterrows():
            # Convertir la ligne en dict (snapshot)
            snapshot = row.to_dict()

            try:
                # Prediction
                predicted_score = predictor.predict(snapshot)
                real_score = row['quality_score']

                predictions.append({
                    'trade_id': idx,
                    'symbol': row.get('symbol', row.get('sym', 'UNKNOWN')),
                    'outcome': row.get('outcome', 'UNKNOWN'),
                    'pnl_ticks': row.get('pnl_ticks', 0),
                    'real_score': real_score,
                    'predicted_score': predicted_score,
                    'error': abs(predicted_score - real_score),
                    'error_pct': abs(predicted_score - real_score) / real_score * 100 if real_score != 0 else 0
                })
            except Exception as e:
                errors.append({'trade_id': idx, 'error': str(e)})
                continue

        df_results = pd.DataFrame(predictions)
        logger.info(f"   OK - {len(predictions):,} predictions ({len(errors)} erreurs)")

        # 4. Calculer metriques globales
        logger.info("\n" + "="*70)
        logger.info("4. METRIQUES GLOBALES")
        logger.info("="*70)

        y_true = df_results['real_score']
        y_pred = df_results['predicted_score']

        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        correlation = np.corrcoef(y_true, y_pred)[0, 1]

        logger.info(f"\n   MAE:         {mae:.2f} points")
        logger.info(f"   RMSE:        {rmse:.2f} points")
        logger.info(f"   R2:          {r2:.4f}")
        logger.info(f"   MAPE:        {mape:.2f}%")
        logger.info(f"   Correlation: {correlation:.4f}")

        # 5. Distribution erreurs
        logger.info("\n" + "="*70)
        logger.info("5. DISTRIBUTION ERREURS")
        logger.info("="*70)

        logger.info(f"\n   Min error:    {df_results['error'].min():.2f}")
        logger.info(f"   Q25 error:    {df_results['error'].quantile(0.25):.2f}")
        logger.info(f"   Median error: {df_results['error'].median():.2f}")
        logger.info(f"   Q75 error:    {df_results['error'].quantile(0.75):.2f}")
        logger.info(f"   Max error:    {df_results['error'].max():.2f}")
        logger.info(f"   Mean error:   {df_results['error'].mean():.2f}")

        # Pourcentage d'erreurs < 5, 10, 15 points
        pct_under_5 = (df_results['error'] < 5).sum() / len(df_results) * 100
        pct_under_10 = (df_results['error'] < 10).sum() / len(df_results) * 100
        pct_under_15 = (df_results['error'] < 15).sum() / len(df_results) * 100

        logger.info(f"\n   Erreur < 5 pts:  {pct_under_5:.1f}%")
        logger.info(f"   Erreur < 10 pts: {pct_under_10:.1f}%")
        logger.info(f"   Erreur < 15 pts: {pct_under_15:.1f}%")

        # 6. Performance par symbole
        logger.info("\n" + "="*70)
        logger.info("6. PERFORMANCE PAR SYMBOLE")
        logger.info("="*70 + "\n")

        for symbol in df_results['symbol'].unique():
            df_sym = df_results[df_results['symbol'] == symbol]
            mae_sym = mean_absolute_error(df_sym['real_score'], df_sym['predicted_score'])
            r2_sym = r2_score(df_sym['real_score'], df_sym['predicted_score'])
            logger.info(f"   {symbol}: {len(df_sym):4d} trades | MAE={mae_sym:.2f} | R2={r2_sym:.4f}")

        # 7. Performance par outcome (WIN/LOSS)
        logger.info("\n" + "="*70)
        logger.info("7. PERFORMANCE PAR OUTCOME")
        logger.info("="*70 + "\n")

        for outcome in df_results['outcome'].unique():
            df_out = df_results[df_results['outcome'] == outcome]
            mae_out = mean_absolute_error(df_out['real_score'], df_out['predicted_score'])
            r2_out = r2_score(df_out['real_score'], df_out['predicted_score'])
            logger.info(f"   {outcome}: {len(df_out):4d} trades | MAE={mae_out:.2f} | R2={r2_out:.4f}")

        # 8. Analyse trades avec plus grosse erreur
        logger.info("\n" + "="*70)
        logger.info("8. TOP 10 TRADES AVEC PLUS GROSSE ERREUR")
        logger.info("="*70 + "\n")

        df_worst = df_results.nlargest(10, 'error')
        for idx, row in df_worst.iterrows():
            logger.info(f"   Trade {row['trade_id']:5d} ({row['symbol']}, {row['outcome']}): "
                       f"Real={row['real_score']:.1f}, Pred={row['predicted_score']:.1f}, "
                       f"Error={row['error']:.1f} pts")

        # 9. Generer plots
        logger.info("\n" + "="*70)
        logger.info("9. GENERATION PLOTS")
        logger.info("="*70 + "\n")

        self._generate_plots(df_results)

        # 10. Sauvegarder resultats
        logger.info("\n" + "="*70)
        logger.info("10. SAUVEGARDE RESULTATS")
        logger.info("="*70 + "\n")

        results_path = self.output_dir / "backtest_results.parquet"
        df_results.to_parquet(results_path, index=False)
        logger.info(f"   Resultats: {results_path}")

        # Rapport texte
        report_path = self.output_dir / "backtest_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("RAPPORT BACKTEST LIGHTGBM\n")
            f.write("="*70 + "\n\n")
            f.write(f"Trades total:    {len(df_results):,}\n")
            f.write(f"Trades errors:   {len(errors)}\n\n")
            f.write(f"MAE:             {mae:.2f} points\n")
            f.write(f"RMSE:            {rmse:.2f} points\n")
            f.write(f"R2:              {r2:.4f}\n")
            f.write(f"MAPE:            {mape:.2f}%\n")
            f.write(f"Correlation:     {correlation:.4f}\n\n")
            f.write(f"Erreur < 5 pts:  {pct_under_5:.1f}%\n")
            f.write(f"Erreur < 10 pts: {pct_under_10:.1f}%\n")
            f.write(f"Erreur < 15 pts: {pct_under_15:.1f}%\n")

        logger.info(f"   Rapport: {report_path}")

        logger.info("\n" + "="*70)
        logger.info("BACKTEST TERMINE !")
        logger.info("="*70 + "\n")

        return df_results

    def _generate_plots(self, df_results: pd.DataFrame):
        """Genere les plots de visualisation."""

        # 1. Scatter plot: Predictions vs Real
        plt.figure(figsize=(10, 8))
        plt.scatter(df_results['real_score'], df_results['predicted_score'], alpha=0.5)
        plt.plot([0, 100], [0, 100], 'r--', label='Perfect prediction')
        plt.xlabel('Real Quality Score')
        plt.ylabel('Predicted Quality Score')
        plt.title('Predictions vs Real Quality Scores')
        plt.legend()
        plt.grid(True, alpha=0.3)
        scatter_path = self.output_dir / "predictions_vs_real.png"
        plt.savefig(scatter_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 1: {scatter_path}")

        # 2. Distribution erreurs
        plt.figure(figsize=(10, 6))
        plt.hist(df_results['error'], bins=50, alpha=0.7, edgecolor='black')
        plt.axvline(df_results['error'].mean(), color='r', linestyle='--', label=f'Mean: {df_results["error"].mean():.2f}')
        plt.axvline(df_results['error'].median(), color='g', linestyle='--', label=f'Median: {df_results["error"].median():.2f}')
        plt.xlabel('Absolute Error (points)')
        plt.ylabel('Frequency')
        plt.title('Distribution of Prediction Errors')
        plt.legend()
        plt.grid(True, alpha=0.3)
        error_dist_path = self.output_dir / "error_distribution.png"
        plt.savefig(error_dist_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 2: {error_dist_path}")

        # 3. Erreurs par symbole
        plt.figure(figsize=(10, 6))
        df_results.boxplot(column='error', by='symbol', figsize=(10, 6))
        plt.suptitle('')
        plt.title('Prediction Errors by Symbol')
        plt.xlabel('Symbol')
        plt.ylabel('Absolute Error (points)')
        plt.grid(True, alpha=0.3)
        error_by_symbol_path = self.output_dir / "error_by_symbol.png"
        plt.savefig(error_by_symbol_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 3: {error_by_symbol_path}")

        # 4. Erreurs par outcome
        plt.figure(figsize=(10, 6))
        df_results.boxplot(column='error', by='outcome', figsize=(10, 6))
        plt.suptitle('')
        plt.title('Prediction Errors by Outcome')
        plt.xlabel('Outcome')
        plt.ylabel('Absolute Error (points)')
        plt.grid(True, alpha=0.3)
        error_by_outcome_path = self.output_dir / "error_by_outcome.png"
        plt.savefig(error_by_outcome_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 4: {error_by_outcome_path}")


if __name__ == '__main__':
    # Configuration
    MODEL_PATH = Path("ml/models/lightgbm_quality_v1.pkl")
    LABELED_TRADES_PATH = Path("ml/data/labeled_trades.parquet")
    OUTPUT_DIR = Path("ml/backtest_results")

    # Verifier que les fichiers existent
    if not MODEL_PATH.exists():
        logger.error(f"ERREUR: Modele non trouve: {MODEL_PATH}")
        logger.error("Veuillez executer 'python ml/train_lightgbm_model.py' d'abord !")
        exit(1)

    if not LABELED_TRADES_PATH.exists():
        logger.error(f"ERREUR: Trades labelises non trouves: {LABELED_TRADES_PATH}")
        logger.error("Veuillez executer 'python ml/label_trades.py' d'abord !")
        exit(1)

    # Executer le backtest
    backtester = LightGBMBacktester(MODEL_PATH, LABELED_TRADES_PATH, OUTPUT_DIR)
    df_results = backtester.run_backtest()

    logger.info("\nResultats sauvegardes dans: ml/backtest_results/")



================================================

Charge le modele LightGBM entraine et le teste sur les trades labelises
pour comparer les predictions vs les quality scores reels.

Metriques:
- MAE, RMSE, R2, MAPE
- Distribution erreurs
- Performance par symbole
- Performance par outcome (WIN/LOSS)
- Correlation predictions vs scores reels
"""

import sys
from pathlib import Path

# Ajouter le chemin parent pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import logging
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour eviter erreurs display
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.lightgbm_predictor import LightGBMPredictor

class LightGBMBacktester:
    """Backteste le modele LightGBM sur donnees reelles."""

    def __init__(self, model_path: Path, labeled_trades_path: Path, output_dir: Path = Path("ml/backtest_results")):
        self.model_path = model_path
        self.labeled_trades_path = labeled_trades_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Backtester initialise")
        logger.info(f"   Modele: {model_path}")
        logger.info(f"   Trades: {labeled_trades_path}")
        logger.info(f"   Output: {output_dir}")

    def run_backtest(self):
        """Execute le backtest complet."""
        logger.info("\n" + "="*70)
        logger.info("BACKTEST LIGHTGBM - DONNEES REELLES")
        logger.info("="*70 + "\n")

        # 1. Charger le modele
        logger.info("1. CHARGEMENT MODELE...")
        predictor = LightGBMPredictor.load(str(self.model_path))
        model_info = predictor.get_model_info()
        logger.info(f"   OK - Modele charge")
        logger.info(f"   Type: {model_info['model_type']}")
        logger.info(f"   Features: {model_info['n_features']}")

        # 2. Charger les trades labelises
        logger.info("\n2. CHARGEMENT TRADES LABELISES...")
        df_trades = pd.read_parquet(self.labeled_trades_path)
        logger.info(f"   OK - {len(df_trades):,} trades charges")
        logger.info(f"   Colonnes: {len(df_trades.columns)}")

        # 3. Faire predictions sur tous les trades
        logger.info("\n3. PREDICTIONS SUR TOUS LES TRADES...")
        predictions = []
        errors = []

        for idx, row in df_trades.iterrows():
            # Convertir la ligne en dict (snapshot)
            snapshot = row.to_dict()

            try:
                # Prediction
                predicted_score = predictor.predict(snapshot)
                real_score = row['quality_score']

                predictions.append({
                    'trade_id': idx,
                    'symbol': row.get('symbol', row.get('sym', 'UNKNOWN')),
                    'outcome': row.get('outcome', 'UNKNOWN'),
                    'pnl_ticks': row.get('pnl_ticks', 0),
                    'real_score': real_score,
                    'predicted_score': predicted_score,
                    'error': abs(predicted_score - real_score),
                    'error_pct': abs(predicted_score - real_score) / real_score * 100 if real_score != 0 else 0
                })
            except Exception as e:
                errors.append({'trade_id': idx, 'error': str(e)})
                continue

        df_results = pd.DataFrame(predictions)
        logger.info(f"   OK - {len(predictions):,} predictions ({len(errors)} erreurs)")

        # 4. Calculer metriques globales
        logger.info("\n" + "="*70)
        logger.info("4. METRIQUES GLOBALES")
        logger.info("="*70)

        y_true = df_results['real_score']
        y_pred = df_results['predicted_score']

        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        correlation = np.corrcoef(y_true, y_pred)[0, 1]

        logger.info(f"\n   MAE:         {mae:.2f} points")
        logger.info(f"   RMSE:        {rmse:.2f} points")
        logger.info(f"   R2:          {r2:.4f}")
        logger.info(f"   MAPE:        {mape:.2f}%")
        logger.info(f"   Correlation: {correlation:.4f}")

        # 5. Distribution erreurs
        logger.info("\n" + "="*70)
        logger.info("5. DISTRIBUTION ERREURS")
        logger.info("="*70)

        logger.info(f"\n   Min error:    {df_results['error'].min():.2f}")
        logger.info(f"   Q25 error:    {df_results['error'].quantile(0.25):.2f}")
        logger.info(f"   Median error: {df_results['error'].median():.2f}")
        logger.info(f"   Q75 error:    {df_results['error'].quantile(0.75):.2f}")
        logger.info(f"   Max error:    {df_results['error'].max():.2f}")
        logger.info(f"   Mean error:   {df_results['error'].mean():.2f}")

        # Pourcentage d'erreurs < 5, 10, 15 points
        pct_under_5 = (df_results['error'] < 5).sum() / len(df_results) * 100
        pct_under_10 = (df_results['error'] < 10).sum() / len(df_results) * 100
        pct_under_15 = (df_results['error'] < 15).sum() / len(df_results) * 100

        logger.info(f"\n   Erreur < 5 pts:  {pct_under_5:.1f}%")
        logger.info(f"   Erreur < 10 pts: {pct_under_10:.1f}%")
        logger.info(f"   Erreur < 15 pts: {pct_under_15:.1f}%")

        # 6. Performance par symbole
        logger.info("\n" + "="*70)
        logger.info("6. PERFORMANCE PAR SYMBOLE")
        logger.info("="*70 + "\n")

        for symbol in df_results['symbol'].unique():
            df_sym = df_results[df_results['symbol'] == symbol]
            mae_sym = mean_absolute_error(df_sym['real_score'], df_sym['predicted_score'])
            r2_sym = r2_score(df_sym['real_score'], df_sym['predicted_score'])
            logger.info(f"   {symbol}: {len(df_sym):4d} trades | MAE={mae_sym:.2f} | R2={r2_sym:.4f}")

        # 7. Performance par outcome (WIN/LOSS)
        logger.info("\n" + "="*70)
        logger.info("7. PERFORMANCE PAR OUTCOME")
        logger.info("="*70 + "\n")

        for outcome in df_results['outcome'].unique():
            df_out = df_results[df_results['outcome'] == outcome]
            mae_out = mean_absolute_error(df_out['real_score'], df_out['predicted_score'])
            r2_out = r2_score(df_out['real_score'], df_out['predicted_score'])
            logger.info(f"   {outcome}: {len(df_out):4d} trades | MAE={mae_out:.2f} | R2={r2_out:.4f}")

        # 8. Analyse trades avec plus grosse erreur
        logger.info("\n" + "="*70)
        logger.info("8. TOP 10 TRADES AVEC PLUS GROSSE ERREUR")
        logger.info("="*70 + "\n")

        df_worst = df_results.nlargest(10, 'error')
        for idx, row in df_worst.iterrows():
            logger.info(f"   Trade {row['trade_id']:5d} ({row['symbol']}, {row['outcome']}): "
                       f"Real={row['real_score']:.1f}, Pred={row['predicted_score']:.1f}, "
                       f"Error={row['error']:.1f} pts")

        # 9. Generer plots
        logger.info("\n" + "="*70)
        logger.info("9. GENERATION PLOTS")
        logger.info("="*70 + "\n")

        self._generate_plots(df_results)

        # 10. Sauvegarder resultats
        logger.info("\n" + "="*70)
        logger.info("10. SAUVEGARDE RESULTATS")
        logger.info("="*70 + "\n")

        results_path = self.output_dir / "backtest_results.parquet"
        df_results.to_parquet(results_path, index=False)
        logger.info(f"   Resultats: {results_path}")

        # Rapport texte
        report_path = self.output_dir / "backtest_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("RAPPORT BACKTEST LIGHTGBM\n")
            f.write("="*70 + "\n\n")
            f.write(f"Trades total:    {len(df_results):,}\n")
            f.write(f"Trades errors:   {len(errors)}\n\n")
            f.write(f"MAE:             {mae:.2f} points\n")
            f.write(f"RMSE:            {rmse:.2f} points\n")
            f.write(f"R2:              {r2:.4f}\n")
            f.write(f"MAPE:            {mape:.2f}%\n")
            f.write(f"Correlation:     {correlation:.4f}\n\n")
            f.write(f"Erreur < 5 pts:  {pct_under_5:.1f}%\n")
            f.write(f"Erreur < 10 pts: {pct_under_10:.1f}%\n")
            f.write(f"Erreur < 15 pts: {pct_under_15:.1f}%\n")

        logger.info(f"   Rapport: {report_path}")

        logger.info("\n" + "="*70)
        logger.info("BACKTEST TERMINE !")
        logger.info("="*70 + "\n")

        return df_results

    def _generate_plots(self, df_results: pd.DataFrame):
        """Genere les plots de visualisation."""

        # 1. Scatter plot: Predictions vs Real
        plt.figure(figsize=(10, 8))
        plt.scatter(df_results['real_score'], df_results['predicted_score'], alpha=0.5)
        plt.plot([0, 100], [0, 100], 'r--', label='Perfect prediction')
        plt.xlabel('Real Quality Score')
        plt.ylabel('Predicted Quality Score')
        plt.title('Predictions vs Real Quality Scores')
        plt.legend()
        plt.grid(True, alpha=0.3)
        scatter_path = self.output_dir / "predictions_vs_real.png"
        plt.savefig(scatter_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 1: {scatter_path}")

        # 2. Distribution erreurs
        plt.figure(figsize=(10, 6))
        plt.hist(df_results['error'], bins=50, alpha=0.7, edgecolor='black')
        plt.axvline(df_results['error'].mean(), color='r', linestyle='--', label=f'Mean: {df_results["error"].mean():.2f}')
        plt.axvline(df_results['error'].median(), color='g', linestyle='--', label=f'Median: {df_results["error"].median():.2f}')
        plt.xlabel('Absolute Error (points)')
        plt.ylabel('Frequency')
        plt.title('Distribution of Prediction Errors')
        plt.legend()
        plt.grid(True, alpha=0.3)
        error_dist_path = self.output_dir / "error_distribution.png"
        plt.savefig(error_dist_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 2: {error_dist_path}")

        # 3. Erreurs par symbole
        plt.figure(figsize=(10, 6))
        df_results.boxplot(column='error', by='symbol', figsize=(10, 6))
        plt.suptitle('')
        plt.title('Prediction Errors by Symbol')
        plt.xlabel('Symbol')
        plt.ylabel('Absolute Error (points)')
        plt.grid(True, alpha=0.3)
        error_by_symbol_path = self.output_dir / "error_by_symbol.png"
        plt.savefig(error_by_symbol_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 3: {error_by_symbol_path}")

        # 4. Erreurs par outcome
        plt.figure(figsize=(10, 6))
        df_results.boxplot(column='error', by='outcome', figsize=(10, 6))
        plt.suptitle('')
        plt.title('Prediction Errors by Outcome')
        plt.xlabel('Outcome')
        plt.ylabel('Absolute Error (points)')
        plt.grid(True, alpha=0.3)
        error_by_outcome_path = self.output_dir / "error_by_outcome.png"
        plt.savefig(error_by_outcome_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"   Plot 4: {error_by_outcome_path}")


if __name__ == '__main__':
    # Configuration
    MODEL_PATH = Path("ml/models/lightgbm_quality_v1.pkl")
    LABELED_TRADES_PATH = Path("ml/data/labeled_trades.parquet")
    OUTPUT_DIR = Path("ml/backtest_results")

    # Verifier que les fichiers existent
    if not MODEL_PATH.exists():
        logger.error(f"ERREUR: Modele non trouve: {MODEL_PATH}")
        logger.error("Veuillez executer 'python ml/train_lightgbm_model.py' d'abord !")
        exit(1)

    if not LABELED_TRADES_PATH.exists():
        logger.error(f"ERREUR: Trades labelises non trouves: {LABELED_TRADES_PATH}")
        logger.error("Veuillez executer 'python ml/label_trades.py' d'abord !")
        exit(1)

    # Executer le backtest
    backtester = LightGBMBacktester(MODEL_PATH, LABELED_TRADES_PATH, OUTPUT_DIR)
    df_results = backtester.run_backtest()

    logger.info("\nResultats sauvegardes dans: ml/backtest_results/")





