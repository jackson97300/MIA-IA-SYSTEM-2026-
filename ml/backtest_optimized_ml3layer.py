"""
Backtest ML_3LAYER avec Configuration OPTIMISÉE (TP/SL Fixes)
=============================================================

Configuration:
- use_fixed_tp_sl = True (TP/SL fixes)
- ES: TP 16t / SL 12t (R:R 1.33:1)
- NQ: TP 23t / SL 12t (R:R 1.92:1)

Objectif:
- Valider performance avec TP/SL optimaux (485 combinaisons)
- Comparer avec baseline (ATR adaptatif)

Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ML3LayerOptimizedBacktest:
    """
    Backtest ML_3LAYER avec configuration OPTIMISÉE (TP/SL fixes)
    """

    def __init__(self, data_path: str = "ml/data/labeled_trades.parquet"):
        """
        Initialise le backtester

        Args:
            data_path: Chemin vers labeled_trades.parquet
        """
        self.data_path = Path(data_path)
        self.df = None

        # ═══════════════════════════════════════════════════════════════
        # ✅ CONFIGURATION OPTIMALE 15/11/2025 - VALIDÉE PAR 485 COMBINAISONS
        # ES: TP 16t / SL 12t (R:R 1.33:1) → +0.397 t/trade
        # NQ: TP 23t / SL 12t (R:R 1.92:1) → +1.528 t/trade
        # ═══════════════════════════════════════════════════════════════
        self.sl_optimal_ticks = {
            'ES': 12,
            'NQ': 12,
            'RTY': 20
        }

        self.tp_optimal_ticks = {
            'ES': 16,
            'NQ': 23,
            'RTY': 25
        }

        # Fees (PropFirms Moyennes)
        self.fees_per_trade = {
            'ES': 0.12,  # ticks
            'NQ': 0.28,  # ticks
            'RTY': 0.30  # ticks
        }

        # Tick values
        self.tick_values = {
            'ES': 12.50,
            'NQ': 5.00,
            'RTY': 10.00
        }

        logger.info("ML_3LAYER Optimized Backtest initialisé")
        logger.info(f"Config: TP/SL FIXES (ES: {self.tp_optimal_ticks['ES']}t/{self.sl_optimal_ticks['ES']}t, "
                   f"NQ: {self.tp_optimal_ticks['NQ']}t/{self.sl_optimal_ticks['NQ']}t)")

    def load_data(self):
        """Charge les données historiques"""
        logger.info(f"Chargement des données depuis {self.data_path}...")

        if not self.data_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {self.data_path}")

        self.df = pd.read_parquet(self.data_path)
        logger.info(f"Données chargées: {len(self.df)} trades")

        # Filtrer uniquement ES et NQ
        self.df = self.df[self.df['symbol'].isin(['ES', 'NQ'])].copy()
        logger.info(f"Après filtre ES/NQ: {len(self.df)} trades")

        return self.df

    def simulate_trade(self, row):
        """
        Simule un trade avec config OPTIMISÉE

        Returns:
            dict avec résultats du trade
        """
        symbol = row['symbol']
        direction = row.get('direction', 'LONG')
        entry = row.get('mid', row.get('entry', 0))

        # TP/SL FIXES optimaux
        sl_ticks = self.sl_optimal_ticks[symbol]
        tp_ticks = self.tp_optimal_ticks[symbol]

        # Données marché
        high = row.get('high', entry)
        low = row.get('low', entry)
        duration = row.get('duration_seconds', 300)

        # Calculer MFE/MAE
        if direction == 'LONG':
            mfe_ticks = (high - entry) / 0.25
            mae_ticks = (entry - low) / 0.25
        else:  # SHORT
            mfe_ticks = (entry - low) / 0.25
            mae_ticks = (high - entry) / 0.25

        # Déterminer résultat
        hit_tp = mfe_ticks >= tp_ticks
        hit_sl = mae_ticks >= sl_ticks

        # Calculer P&L
        if hit_tp:
            pnl_ticks = tp_ticks - self.fees_per_trade[symbol]
            exit_type = 'TP'
        elif hit_sl:
            pnl_ticks = -sl_ticks - self.fees_per_trade[symbol]
            exit_type = 'SL'
        else:
            # Ni TP ni SL → Simuler exit à MFE si positif, sinon 0
            if mfe_ticks > 0:
                pnl_ticks = min(mfe_ticks, tp_ticks * 0.5) - self.fees_per_trade[symbol]
                exit_type = 'TIMEOUT_PROFIT'
            else:
                pnl_ticks = max(-mae_ticks, -sl_ticks * 0.5) - self.fees_per_trade[symbol]
                exit_type = 'TIMEOUT_LOSS'

        return {
            'symbol': symbol,
            'direction': direction,
            'entry': entry,
            'sl_ticks': sl_ticks,
            'tp_ticks': tp_ticks,
            'mfe_ticks': mfe_ticks,
            'mae_ticks': mae_ticks,
            'hit_tp': hit_tp,
            'hit_sl': hit_sl,
            'exit_type': exit_type,
            'pnl_ticks': pnl_ticks,
            'pnl_usd': pnl_ticks * self.tick_values[symbol],
            'duration': duration
        }

    def run_backtest(self):
        """
        Lance le backtest complet

        Returns:
            DataFrame avec résultats de chaque trade
        """
        logger.info("Lancement du backtest OPTIMISÉ...")

        results = []

        for idx, row in self.df.iterrows():
            result = self.simulate_trade(row)
            results.append(result)

            if (idx + 1) % 500 == 0:
                logger.info(f"Processed {idx + 1}/{len(self.df)} trades...")

        results_df = pd.DataFrame(results)
        logger.info(f"Backtest terminé: {len(results_df)} trades simulés")

        return results_df

    def calculate_metrics(self, results_df):
        """
        Calcule les métriques de performance

        Args:
            results_df: DataFrame avec résultats des trades

        Returns:
            dict avec métriques par symbole et globales
        """
        metrics = {}

        for symbol in ['ES', 'NQ', 'TOTAL']:
            if symbol == 'TOTAL':
                df_sym = results_df
            else:
                df_sym = results_df[results_df['symbol'] == symbol]

            if len(df_sym) == 0:
                continue

            n_trades = len(df_sym)
            n_win = len(df_sym[df_sym['pnl_ticks'] > 0])
            n_loss = len(df_sym[df_sym['pnl_ticks'] <= 0])

            winrate = n_win / n_trades if n_trades > 0 else 0

            pnl_net_ticks = df_sym['pnl_ticks'].sum()
            pnl_net_usd = df_sym['pnl_usd'].sum()
            pnl_per_trade_ticks = pnl_net_ticks / n_trades if n_trades > 0 else 0

            tp_hit_rate = df_sym['hit_tp'].sum() / n_trades if n_trades > 0 else 0
            sl_hit_rate = df_sym['hit_sl'].sum() / n_trades if n_trades > 0 else 0

            avg_sl_ticks = df_sym['sl_ticks'].mean()
            avg_tp_ticks = df_sym['tp_ticks'].mean()

            metrics[symbol] = {
                'n_trades': n_trades,
                'n_win': n_win,
                'n_loss': n_loss,
                'winrate': winrate,
                'pnl_net_ticks': pnl_net_ticks,
                'pnl_net_usd': pnl_net_usd,
                'pnl_per_trade_ticks': pnl_per_trade_ticks,
                'tp_hit_rate': tp_hit_rate,
                'sl_hit_rate': sl_hit_rate,
                'avg_sl_ticks': avg_sl_ticks,
                'avg_tp_ticks': avg_tp_ticks
            }

        return metrics

    def generate_report(self, metrics, output_path: str = "ml/output/backtest_optimized_report.txt"):
        """
        Génère un rapport texte détaillé

        Args:
            metrics: dict avec métriques
            output_path: Chemin de sortie du rapport
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        report = []
        report.append("=" * 70)
        report.append("BACKTEST ML_3LAYER - CONFIGURATION OPTIMISÉE (TP/SL FIXES)")
        report.append("=" * 70)
        report.append("")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("CONFIGURATION:")
        report.append("  ES: TP 16t / SL 12t (R:R 1.33:1) - Validé par 485 combinaisons")
        report.append("  NQ: TP 23t / SL 12t (R:R 1.92:1) - Validé par 485 combinaisons")
        report.append("  Fees: ES 0.12t, NQ 0.28t")
        report.append("")
        report.append("PERFORMANCE ATTENDUE (Optimisation exhaustive):")
        report.append("  ES: +0.397 t/trade")
        report.append("  NQ: +1.528 t/trade")
        report.append("")
        report.append("-" * 70)

        for symbol in ['ES', 'NQ', 'TOTAL']:
            if symbol not in metrics:
                continue

            m = metrics[symbol]

            # Calculer vs attendu pour ES et NQ
            if symbol == 'ES':
                expected = 0.397
                diff = m['pnl_per_trade_ticks'] - expected
                vs_expected = f" (vs {expected:+.3f}t attendu: {diff:+.3f}t)"
            elif symbol == 'NQ':
                expected = 1.528
                diff = m['pnl_per_trade_ticks'] - expected
                vs_expected = f" (vs {expected:+.3f}t attendu: {diff:+.3f}t)"
            else:
                vs_expected = ""

            report.append("")
            report.append(f"{'=' * 30} {symbol} {'=' * 30}")
            report.append("")
            report.append(f"  Trades Total:      {m['n_trades']}")
            report.append(f"  Trades WIN:        {m['n_win']} ({m['winrate']*100:.1f}%)")
            report.append(f"  Trades LOSS:       {m['n_loss']} ({(1-m['winrate'])*100:.1f}%)")
            report.append("")
            report.append(f"  P&L Net:           {m['pnl_net_ticks']:+.2f} ticks (${m['pnl_net_usd']:+,.2f})")
            report.append(f"  P&L/trade:         {m['pnl_per_trade_ticks']:+.3f} ticks{vs_expected}")
            report.append("")
            report.append(f"  TP Hit Rate:       {m['tp_hit_rate']*100:.1f}%")
            report.append(f"  SL Hit Rate:       {m['sl_hit_rate']*100:.1f}%")
            report.append("")
            report.append(f"  Avg SL:            {m['avg_sl_ticks']:.1f} ticks")
            report.append(f"  Avg TP:            {m['avg_tp_ticks']:.1f} ticks")
            report.append("")

        report.append("=" * 70)
        report.append("")

        report_text = "\n".join(report)

        # Sauvegarder
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"Rapport sauvegardé: {output_file}")

        # Afficher aussi
        print(report_text)

        return report_text


def main():
    """
    Fonction principale
    """
    logger.info("DÉMARRAGE BACKTEST OPTIMISÉ ML_3LAYER")
    logger.info("=" * 70)

    # Initialiser backtester
    backtester = ML3LayerOptimizedBacktest(
        data_path="ml/data/labeled_trades.parquet"
    )

    # Charger données
    backtester.load_data()

    # Lancer backtest
    results_df = backtester.run_backtest()

    # Sauvegarder résultats détaillés
    output_csv = Path("ml/output/backtest_optimized_results.csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_csv, index=False)
    logger.info(f"Résultats détaillés sauvegardés: {output_csv}")

    # Calculer métriques
    metrics = backtester.calculate_metrics(results_df)

    # Générer rapport
    backtester.generate_report(metrics)

    logger.info("")
    logger.info("=" * 70)
    logger.info("BACKTEST OPTIMISÉ TERMINÉ")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
