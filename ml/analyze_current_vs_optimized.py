"""
Analyse Performance Actuelle vs TP/SL Optimaux
==============================================

Analyse directe des données labeled_trades.parquet pour:
1. Calculer performance ACTUELLE du bot
2. Simuler performance avec TP/SL OPTIMAUX
3. Comparer et recommander

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


class OptimizedTPSLAnalyzer:
    """
    Analyse performance avec TP/SL optimaux vs actuels
    """

    def __init__(self, data_path: str = "ml/data/labeled_trades.parquet"):
        self.data_path = Path(data_path)
        self.df = None

        # Configuration OPTIMALE
        self.sl_optimal_ticks = {'ES': 12, 'NQ': 12, 'RTY': 20}
        self.tp_optimal_ticks = {'ES': 16, 'NQ': 23, 'RTY': 25}

        # Fees (PropFirms)
        self.fees_ticks = {'ES': 0.12, 'NQ': 0.28, 'RTY': 0.30}

        # Tick values
        self.tick_values = {'ES': 12.50, 'NQ': 5.00, 'RTY': 10.00}

        logger.info("Analyzer initialisé avec config optimale:")
        logger.info(f"  ES: TP {self.tp_optimal_ticks['ES']}t / SL {self.sl_optimal_ticks['ES']}t")
        logger.info(f"  NQ: TP {self.tp_optimal_ticks['NQ']}t / SL {self.sl_optimal_ticks['NQ']}t")

    def load_data(self):
        """Charge les données"""
        logger.info(f"Chargement des données depuis {self.data_path}...")

        if not self.data_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {self.data_path}")

        self.df = pd.read_parquet(self.data_path)
        logger.info(f"✅ {len(self.df)} trades chargés")

        # Filtrer ES et NQ seulement
        self.df = self.df[self.df['symbol'].isin(['ES', 'NQ'])].copy()
        logger.info(f"✅ Après filtre ES/NQ: {len(self.df)} trades")

        # Calculer sl_ticks et tp_ticks actuels
        self.df['sl_ticks_actual'] = ((self.df['entry_price'] - self.df['stop']).abs() / 0.25).astype(int)
        self.df['tp_ticks_actual'] = ((self.df['target'] - self.df['entry_price']).abs() / 0.25).astype(int)

        return self.df

    def analyze_current_performance(self):
        """
        Analyse performance ACTUELLE (avec TP/SL utilisés historiquement)
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 ANALYSE PERFORMANCE ACTUELLE (TP/SL historiques)")
        logger.info("=" * 70)

        results = {}

        for symbol in ['ES', 'NQ', 'TOTAL']:
            if symbol == 'TOTAL':
                df_sym = self.df
            else:
                df_sym = self.df[self.df['symbol'] == symbol]

            if len(df_sym) == 0:
                continue

            n_trades = len(df_sym)
            n_win = df_sym['win'].sum()
            n_loss = n_trades - n_win
            winrate = n_win / n_trades if n_trades > 0 else 0

            # P&L réel (déjà calculé dans les données)
            pnl_net_ticks = df_sym['pnl_ticks'].sum()
            pnl_per_trade_ticks = pnl_net_ticks / n_trades if n_trades > 0 else 0

            # P&L en USD
            if symbol != 'TOTAL':
                pnl_net_usd = pnl_net_ticks * self.tick_values[symbol]
            else:
                pnl_net_usd = (
                    self.df[self.df['symbol'] == 'ES']['pnl_ticks'].sum() * self.tick_values['ES'] +
                    self.df[self.df['symbol'] == 'NQ']['pnl_ticks'].sum() * self.tick_values['NQ']
                )

            # Calculer TP/SL Hit Rates (approximation)
            tp_hits = n_win  # Simplification: WIN = TP hit
            sl_hits = len(df_sym[df_sym['exit_reason'].str.contains('SL|stop', case=False, na=False)])

            tp_hit_rate = tp_hits / n_trades if n_trades > 0 else 0
            sl_hit_rate = sl_hits / n_trades if n_trades > 0 else 0

            # SL/TP moyens
            avg_sl = df_sym['sl_ticks_actual'].mean()
            avg_tp = df_sym['tp_ticks_actual'].mean()

            results[symbol] = {
                'n_trades': n_trades,
                'n_win': n_win,
                'n_loss': n_loss,
                'winrate': winrate,
                'pnl_net_ticks': pnl_net_ticks,
                'pnl_net_usd': pnl_net_usd,
                'pnl_per_trade_ticks': pnl_per_trade_ticks,
                'tp_hit_rate': tp_hit_rate,
                'sl_hit_rate': sl_hit_rate,
                'avg_sl': avg_sl,
                'avg_tp': avg_tp
            }

            logger.info("")
            logger.info(f"{'=' * 30} {symbol} {'=' * 30}")
            logger.info(f"  Trades:        {n_trades} (WIN: {n_win}, LOSS: {n_loss})")
            logger.info(f"  WinRate:       {winrate*100:.1f}%")
            logger.info(f"  P&L Net:       {pnl_net_ticks:+.2f} ticks (${pnl_net_usd:+,.2f})")
            logger.info(f"  P&L/trade:     {pnl_per_trade_ticks:+.3f} ticks")
            logger.info(f"  TP Hit Rate:   {tp_hit_rate*100:.1f}%")
            logger.info(f"  SL Hit Rate:   {sl_hit_rate*100:.1f}%")
            logger.info(f"  Avg SL:        {avg_sl:.1f} ticks")
            logger.info(f"  Avg TP:        {avg_tp:.1f} ticks")

        logger.info("")
        logger.info("=" * 70)

        return results

    def simulate_optimized_tpsl(self):
        """
        Simule performance avec TP/SL OPTIMAUX
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎯 SIMULATION AVEC TP/SL OPTIMAUX")
        logger.info("=" * 70)

        results_optimized = {}

        for symbol in ['ES', 'NQ', 'TOTAL']:
            if symbol == 'TOTAL':
                df_sym = self.df.copy()
            else:
                df_sym = self.df[self.df['symbol'] == symbol].copy()

            if len(df_sym) == 0:
                continue

            # Pour chaque trade, recalculer si TP ou SL aurait été touché
            if symbol != 'TOTAL':
                sl_opt = self.sl_optimal_ticks[symbol]
                tp_opt = self.tp_optimal_ticks[symbol]
                fees = self.fees_ticks[symbol]

                def simulate_trade(row):
                    """Simule un trade avec TP/SL optimaux"""
                    mfe = row['mfe']  # Maximum Favorable Excursion (ticks)
                    mae = row['mae']  # Maximum Adverse Excursion (ticks)

                    # Vérifier si TP atteint
                    hit_tp = mfe >= tp_opt
                    # Vérifier si SL atteint
                    hit_sl = mae >= sl_opt

                    # Calculer P&L
                    if hit_tp and not hit_sl:
                        # TP atteint avant SL
                        pnl = tp_opt - fees
                        win = 1
                    elif hit_sl:
                        # SL atteint
                        pnl = -sl_opt - fees
                        win = 0
                    else:
                        # Ni TP ni SL → Exit timeout (prendre MFE si positif)
                        if mfe > 0:
                            pnl = min(mfe, tp_opt * 0.5) - fees
                            win = 1 if pnl > 0 else 0
                        else:
                            pnl = max(-mae, -sl_opt * 0.5) - fees
                            win = 0

                    return pd.Series({
                        'pnl_opt': pnl,
                        'win_opt': win,
                        'hit_tp_opt': hit_tp,
                        'hit_sl_opt': hit_sl
                    })

                # Appliquer simulation
                sim_results = df_sym.apply(simulate_trade, axis=1)
                df_sym = pd.concat([df_sym, sim_results], axis=1)
            else:
                # Pour TOTAL, combiner ES et NQ déjà simulés
                pass

            # Calculer métriques optimisées
            n_trades = len(df_sym)

            if symbol != 'TOTAL':
                n_win_opt = df_sym['win_opt'].sum()
                winrate_opt = n_win_opt / n_trades if n_trades > 0 else 0

                pnl_net_ticks_opt = df_sym['pnl_opt'].sum()
                pnl_per_trade_ticks_opt = pnl_net_ticks_opt / n_trades if n_trades > 0 else 0
                pnl_net_usd_opt = pnl_net_ticks_opt * self.tick_values[symbol]

                tp_hit_rate_opt = df_sym['hit_tp_opt'].sum() / n_trades if n_trades > 0 else 0
                sl_hit_rate_opt = df_sym['hit_sl_opt'].sum() / n_trades if n_trades > 0 else 0
            else:
                # Pour TOTAL, recalculer à partir de ES et NQ
                df_es_opt = self.df[self.df['symbol'] == 'ES'].copy()
                df_nq_opt = self.df[self.df['symbol'] == 'NQ'].copy()

                # Simuler ES
                for idx, row in df_es_opt.iterrows():
                    mfe, mae = row['mfe'], row['mae']
                    sl_opt, tp_opt, fees = self.sl_optimal_ticks['ES'], self.tp_optimal_ticks['ES'], self.fees_ticks['ES']

                    hit_tp = mfe >= tp_opt
                    hit_sl = mae >= sl_opt

                    if hit_tp and not hit_sl:
                        pnl = tp_opt - fees
                    elif hit_sl:
                        pnl = -sl_opt - fees
                    else:
                        pnl = (min(mfe, tp_opt * 0.5) if mfe > 0 else max(-mae, -sl_opt * 0.5)) - fees

                    df_es_opt.at[idx, 'pnl_opt'] = pnl
                    df_es_opt.at[idx, 'win_opt'] = 1 if pnl > 0 else 0

                # Simuler NQ
                for idx, row in df_nq_opt.iterrows():
                    mfe, mae = row['mfe'], row['mae']
                    sl_opt, tp_opt, fees = self.sl_optimal_ticks['NQ'], self.tp_optimal_ticks['NQ'], self.fees_ticks['NQ']

                    hit_tp = mfe >= tp_opt
                    hit_sl = mae >= sl_opt

                    if hit_tp and not hit_sl:
                        pnl = tp_opt - fees
                    elif hit_sl:
                        pnl = -sl_opt - fees
                    else:
                        pnl = (min(mfe, tp_opt * 0.5) if mfe > 0 else max(-mae, -sl_opt * 0.5)) - fees

                    df_nq_opt.at[idx, 'pnl_opt'] = pnl
                    df_nq_opt.at[idx, 'win_opt'] = 1 if pnl > 0 else 0

                n_win_opt = df_es_opt['win_opt'].sum() + df_nq_opt['win_opt'].sum()
                winrate_opt = n_win_opt / n_trades if n_trades > 0 else 0

                pnl_net_ticks_opt = df_es_opt['pnl_opt'].sum() + df_nq_opt['pnl_opt'].sum()
                pnl_per_trade_ticks_opt = pnl_net_ticks_opt / n_trades if n_trades > 0 else 0

                pnl_net_usd_opt = (
                    df_es_opt['pnl_opt'].sum() * self.tick_values['ES'] +
                    df_nq_opt['pnl_opt'].sum() * self.tick_values['NQ']
                )

                tp_hit_rate_opt = 0  # Pas calculé pour TOTAL
                sl_hit_rate_opt = 0

            results_optimized[symbol] = {
                'n_trades': n_trades,
                'n_win_opt': n_win_opt,
                'winrate_opt': winrate_opt,
                'pnl_net_ticks_opt': pnl_net_ticks_opt,
                'pnl_net_usd_opt': pnl_net_usd_opt,
                'pnl_per_trade_ticks_opt': pnl_per_trade_ticks_opt,
                'tp_hit_rate_opt': tp_hit_rate_opt,
                'sl_hit_rate_opt': sl_hit_rate_opt
            }

            logger.info("")
            logger.info(f"{'=' * 30} {symbol} {'=' * 30}")
            logger.info(f"  Trades:        {n_trades} (WIN: {int(n_win_opt)})")
            logger.info(f"  WinRate:       {winrate_opt*100:.1f}%")
            logger.info(f"  P&L Net:       {pnl_net_ticks_opt:+.2f} ticks (${pnl_net_usd_opt:+,.2f})")
            logger.info(f"  P&L/trade:     {pnl_per_trade_ticks_opt:+.3f} ticks")
            if symbol != 'TOTAL':
                logger.info(f"  TP Hit Rate:   {tp_hit_rate_opt*100:.1f}%")
                logger.info(f"  SL Hit Rate:   {sl_hit_rate_opt*100:.1f}%")
                logger.info(f"  SL Optimal:    {self.sl_optimal_ticks[symbol]} ticks")
                logger.info(f"  TP Optimal:    {self.tp_optimal_ticks[symbol]} ticks")

        logger.info("")
        logger.info("=" * 70)

        return results_optimized

    def generate_comparison_report(self, current, optimized):
        """
        Génère rapport comparatif
        """
        logger.info("")
        logger.info("=" * 90)
        logger.info("📊 RAPPORT COMPARATIF: ACTUEL vs OPTIMISÉ")
        logger.info("=" * 90)

        report = []
        report.append("=" * 90)
        report.append("RAPPORT COMPARATIF: PERFORMANCE ACTUELLE vs TP/SL OPTIMAUX")
        report.append("=" * 90)
        report.append("")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Données: {len(self.df)} trades (ES + NQ)")
        report.append("")
        report.append("CONFIGURATION OPTIMALE:")
        report.append("  ES: TP 16t / SL 12t (R:R 1.33:1) - Validé par 485 combinaisons")
        report.append("  NQ: TP 23t / SL 12t (R:R 1.92:1) - Validé par 485 combinaisons")
        report.append("")
        report.append("-" * 90)

        for symbol in ['ES', 'NQ', 'TOTAL']:
            if symbol not in current or symbol not in optimized:
                continue

            c = current[symbol]
            o = optimized[symbol]

            # Différences
            diff_pnl_net = o['pnl_net_ticks_opt'] - c['pnl_net_ticks']
            diff_pnl_per_trade = o['pnl_per_trade_ticks_opt'] - c['pnl_per_trade_ticks']
            diff_winrate = o['winrate_opt'] - c['winrate']

            # Performance attendue
            if symbol == 'ES':
                expected = 0.397
            elif symbol == 'NQ':
                expected = 1.528
            else:
                expected = None

            report.append("")
            report.append(f"{'=' * 40} {symbol} {'=' * 40}")
            report.append("")
            report.append(f"{'MÉTRIQUE':<35} {'ACTUEL':>15} {'OPTIMISÉ':>15} {'DIFF':>15}")
            report.append("-" * 90)
            report.append(f"{'Trades':<35} {c['n_trades']:>15} {o['n_trades']:>15} {0:>15}")
            report.append("")
            report.append(f"{'WinRate':<35} {c['winrate']*100:>14.1f}% {o['winrate_opt']*100:>14.1f}% {diff_winrate*100:>14.1f}%")
            report.append("")
            report.append(f"{'P&L Net (ticks)':<35} {c['pnl_net_ticks']:>15.2f} {o['pnl_net_ticks_opt']:>15.2f} {diff_pnl_net:>15.2f}")
            report.append(f"{'P&L/trade (ticks)':<35} {c['pnl_per_trade_ticks']:>15.3f} {o['pnl_per_trade_ticks_opt']:>15.3f} {diff_pnl_per_trade:>15.3f}")

            if expected:
                vs_expected = o['pnl_per_trade_ticks_opt'] - expected
                report.append(f"{'  vs Attendu ({:.3f}t)'.format(expected):<35} {'-':>15} {'-':>15} {vs_expected:>15.3f}")

            report.append("")
            report.append(f"{'P&L Net (USD)':<35} ${c['pnl_net_usd']:>14,.2f} ${o['pnl_net_usd_opt']:>14,.2f} ${o['pnl_net_usd_opt']-c['pnl_net_usd']:>14,.2f}")
            report.append("")

            if symbol != 'TOTAL':
                report.append(f"{'TP Hit Rate':<35} {c['tp_hit_rate']*100:>14.1f}% {o['tp_hit_rate_opt']*100:>14.1f}% {(o['tp_hit_rate_opt']-c['tp_hit_rate'])*100:>14.1f}%")
                report.append(f"{'SL Hit Rate':<35} {c['sl_hit_rate']*100:>14.1f}% {o['sl_hit_rate_opt']*100:>14.1f}% {(o['sl_hit_rate_opt']-c['sl_hit_rate'])*100:>14.1f}%")
                report.append("")
                report.append(f"{'Avg SL (ticks)':<35} {c['avg_sl']:>15.1f} {self.sl_optimal_ticks[symbol]:>15.1f} {self.sl_optimal_ticks[symbol]-c['avg_sl']:>15.1f}")
                report.append(f"{'Avg TP (ticks)':<35} {c['avg_tp']:>15.1f} {self.tp_optimal_ticks[symbol]:>15.1f} {self.tp_optimal_ticks[symbol]-c['avg_tp']:>15.1f}")

            report.append("")

        report.append("=" * 90)
        report.append("")
        report.append("RECOMMANDATION:")
        report.append("")

        # Calculer amélioration totale
        total_improvement_ticks = optimized['TOTAL']['pnl_per_trade_ticks_opt'] - current['TOTAL']['pnl_per_trade_ticks']
        total_improvement_usd = optimized['TOTAL']['pnl_net_usd_opt'] - current['TOTAL']['pnl_net_usd']

        if total_improvement_ticks > 0:
            report.append(f"  ✅ LANCER EN PRODUCTION avec TP/SL OPTIMAUX")
            report.append(f"  Amélioration: {total_improvement_ticks:+.3f} t/trade (${total_improvement_usd:+,.2f} total)")
            report.append("")
            report.append(f"  Gain projeté sur 1 semaine (50 trades/symbole):")
            report.append(f"    ES: ${(optimized['ES']['pnl_per_trade_ticks_opt'] * 50 * self.tick_values['ES']):+,.2f}")
            report.append(f"    NQ: ${(optimized['NQ']['pnl_per_trade_ticks_opt'] * 50 * self.tick_values['NQ']):+,.2f}")
        else:
            report.append(f"  ⚠️ CONFIG OPTIMISÉE SOUS-PERFORME: {total_improvement_ticks:+.3f} t/trade")
            report.append(f"  INVESTIGUER avant lancement")

        report.append("")
        report.append("=" * 90)

        report_text = "\n".join(report)

        # Sauvegarder
        output_file = Path("ml/output/analysis_current_vs_optimized.txt")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"✅ Rapport sauvegardé: {output_file}")

        # Afficher
        print("\n" + report_text)

        return report_text


def main():
    """Fonction principale"""
    logger.info("=" * 90)
    logger.info("ANALYSE PERFORMANCE: ACTUEL vs TP/SL OPTIMAUX")
    logger.info("=" * 90)
    logger.info("")

    # Initialiser analyzer
    analyzer = OptimizedTPSLAnalyzer()

    # Charger données
    analyzer.load_data()

    # Analyser performance actuelle
    current_results = analyzer.analyze_current_performance()

    # Simuler avec TP/SL optimaux
    optimized_results = analyzer.simulate_optimized_tpsl()

    # Générer rapport comparatif
    analyzer.generate_comparison_report(current_results, optimized_results)

    logger.info("")
    logger.info("=" * 90)
    logger.info("✅ ANALYSE TERMINÉE")
    logger.info("=" * 90)


if __name__ == "__main__":
    main()







