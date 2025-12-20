"""
📊 OUTIL D'ANALYSE HEBDOMADAIRE - Production Week 1
===================================================

Analyse automatique des performances après 1 semaine de production:
- P&L net par symbole
- WinRate, Profit Factor, Sharpe Ratio
- Exit Breakdown (TP/SL/Reversal/Timeout)
- Consistency jour par jour
- Drawdown analysis
- Recommandation ES vs NQ

Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class WeeklyAnalyzer:
    """Analyseur de performance hebdomadaire"""

    def __init__(self, trades_file: str = "LAUNCH/daily_trades.json"):
        self.trades_file = trades_file
        self.tick_values = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}
        self.fees_ticks = {'ES': 0.12, 'NQ': 0.28, 'RTY': 0.10}

    def load_trades(self, start_date: str = None, end_date: str = None):
        """Charge les trades de la période spécifiée"""
        try:
            df = pd.read_json(self.trades_file)

            # Convertir timestamp
            if 'entry_time' in df.columns:
                df['entry_time'] = pd.to_datetime(df['entry_time'])
                df['date'] = df['entry_time'].dt.date

            # Filtrer par période
            if start_date:
                df = df[df['entry_time'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['entry_time'] <= pd.to_datetime(end_date)]

            logger.info(f"✅ {len(df)} trades chargés ({df['date'].min()} → {df['date'].max()})")
            return df

        except FileNotFoundError:
            logger.error(f"❌ Fichier non trouvé: {self.trades_file}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ Erreur chargement: {e}")
            return pd.DataFrame()

    def analyze_by_symbol(self, df: pd.DataFrame):
        """Analyse détaillée par symbole"""

        logger.info("")
        logger.info("=" * 90)
        logger.info("📊 ANALYSE PAR SYMBOLE")
        logger.info("=" * 90)
        logger.info("")

        results = {}

        for symbol in ['ES', 'NQ']:
            df_sym = df[df['symbol'] == symbol]

            if df_sym.empty:
                logger.warning(f"⚠️ Aucun trade {symbol}")
                continue

            n_trades = len(df_sym)
            n_win = df_sym['win'].sum() if 'win' in df_sym.columns else (df_sym['pnl_ticks'] > 0).sum()
            n_loss = n_trades - n_win

            winrate = n_win / n_trades if n_trades > 0 else 0

            # P&L
            pnl_ticks = df_sym['pnl_ticks'].sum()
            pnl_per_trade = pnl_ticks / n_trades if n_trades > 0 else 0
            pnl_usd = pnl_ticks * self.tick_values[symbol]

            # Profit Factor
            gross_profit = df_sym[df_sym['pnl_ticks'] > 0]['pnl_ticks'].sum()
            gross_loss = abs(df_sym[df_sym['pnl_ticks'] < 0]['pnl_ticks'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

            # Sharpe Ratio (simplifié)
            returns = df_sym['pnl_ticks'].values
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

            # Drawdown
            cumsum = df_sym['pnl_ticks'].cumsum()
            running_max = cumsum.cummax()
            drawdown = cumsum - running_max
            max_dd = drawdown.min()

            # Exit Breakdown
            exit_breakdown = {}
            if 'exit_reason' in df_sym.columns:
                exit_counts = df_sym['exit_reason'].value_counts()
                for reason, count in exit_counts.items():
                    exit_breakdown[reason] = {'count': count, 'pct': count/n_trades*100}

            results[symbol] = {
                'n_trades': n_trades,
                'n_win': n_win,
                'n_loss': n_loss,
                'winrate': winrate,
                'pnl_ticks': pnl_ticks,
                'pnl_per_trade': pnl_per_trade,
                'pnl_usd': pnl_usd,
                'profit_factor': profit_factor,
                'sharpe': sharpe,
                'max_dd': max_dd,
                'exit_breakdown': exit_breakdown
            }

            # Affichage
            logger.info(f"{'=' * 42} {symbol} {'=' * 42}")
            logger.info("")
            logger.info(f"  📈 TRADES:")
            logger.info(f"     Total:        {n_trades}")
            logger.info(f"     Wins:         {n_win} ({winrate*100:.1f}%)")
            logger.info(f"     Losses:       {n_loss} ({(1-winrate)*100:.1f}%)")
            logger.info("")
            logger.info(f"  💰 P&L:")
            logger.info(f"     Net:          {pnl_ticks:+.1f} ticks (${pnl_usd:+,.2f})")
            logger.info(f"     Per Trade:    {pnl_per_trade:+.3f} ticks")
            logger.info(f"     Gross Profit: {gross_profit:.1f} ticks")
            logger.info(f"     Gross Loss:   {gross_loss:.1f} ticks")
            logger.info("")
            logger.info(f"  📊 MÉTRIQUES:")
            logger.info(f"     Profit Factor: {profit_factor:.2f}")
            logger.info(f"     Sharpe Ratio:  {sharpe:.2f}")
            logger.info(f"     Max Drawdown:  {max_dd:.1f} ticks")
            logger.info("")

            if exit_breakdown:
                logger.info(f"  🚪 EXIT BREAKDOWN:")
                for reason, data in sorted(exit_breakdown.items(), key=lambda x: x[1]['count'], reverse=True):
                    logger.info(f"     {reason:15s}: {data['count']:4d} ({data['pct']:5.1f}%)")
                logger.info("")

        logger.info("=" * 90)
        logger.info("")

        return results

    def daily_consistency(self, df: pd.DataFrame):
        """Analyse de la consistance jour par jour"""

        logger.info("")
        logger.info("=" * 90)
        logger.info("📅 CONSISTANCE QUOTIDIENNE")
        logger.info("=" * 90)
        logger.info("")

        for symbol in ['ES', 'NQ']:
            df_sym = df[df['symbol'] == symbol]

            if df_sym.empty:
                continue

            daily = df_sym.groupby('date').agg({
                'pnl_ticks': ['sum', 'count'],
                'win': 'sum'
            }).reset_index()

            daily.columns = ['date', 'pnl', 'trades', 'wins']
            daily['winrate'] = daily['wins'] / daily['trades']

            logger.info(f"{symbol}:")
            logger.info("")
            logger.info(f"  Date       | Trades | Wins | WR    | P&L (ticks)")
            logger.info(f"  " + "-" * 58)

            for _, row in daily.iterrows():
                logger.info(f"  {row['date']} |   {row['trades']:3.0f}  | {row['wins']:3.0f}  | {row['winrate']*100:4.1f}% | {row['pnl']:+7.1f}")

            logger.info("")

            # Statistiques
            winning_days = (daily['pnl'] > 0).sum()
            total_days = len(daily)

            logger.info(f"  📊 Jours gagnants: {winning_days}/{total_days} ({winning_days/total_days*100:.1f}%)")
            logger.info(f"  📊 P&L moyen/jour: {daily['pnl'].mean():+.1f} ticks")
            logger.info(f"  📊 Écart-type:     {daily['pnl'].std():.1f} ticks")
            logger.info("")

        logger.info("=" * 90)
        logger.info("")

    def compare_es_vs_nq(self, results: dict):
        """Compare ES vs NQ et donne recommandation"""

        logger.info("")
        logger.info("=" * 90)
        logger.info("⚔️  COMPARAISON ES vs NQ")
        logger.info("=" * 90)
        logger.info("")

        if 'ES' not in results or 'NQ' not in results:
            logger.warning("⚠️ Données insuffisantes pour comparaison")
            return

        es = results['ES']
        nq = results['NQ']

        logger.info(f"  Métrique              |    ES      |    NQ      | Gagnant")
        logger.info(f"  " + "-" * 65)
        logger.info(f"  Trades                |   {es['n_trades']:4d}   |   {nq['n_trades']:4d}   | {('ES' if es['n_trades'] > nq['n_trades'] else 'NQ'):3s}")
        logger.info(f"  WinRate               | {es['winrate']*100:6.1f}%  | {nq['winrate']*100:6.1f}%  | {('ES' if es['winrate'] > nq['winrate'] else 'NQ'):3s}")
        logger.info(f"  P&L/trade             | {es['pnl_per_trade']:+7.3f}t | {nq['pnl_per_trade']:+7.3f}t | {('ES' if es['pnl_per_trade'] > nq['pnl_per_trade'] else 'NQ'):3s}")
        logger.info(f"  Profit Factor         | {es['profit_factor']:7.2f}  | {nq['profit_factor']:7.2f}  | {('ES' if es['profit_factor'] > nq['profit_factor'] else 'NQ'):3s}")
        logger.info(f"  Sharpe Ratio          | {es['sharpe']:7.2f}  | {nq['sharpe']:7.2f}  | {('ES' if es['sharpe'] > nq['sharpe'] else 'NQ'):3s}")
        logger.info(f"  Max Drawdown          | {es['max_dd']:7.1f}t | {nq['max_dd']:7.1f}t | {('ES' if es['max_dd'] > nq['max_dd'] else 'NQ'):3s}")
        logger.info(f"  P&L USD               | ${es['pnl_usd']:+9,.2f} | ${nq['pnl_usd']:+9,.2f} | {('ES' if es['pnl_usd'] > nq['pnl_usd'] else 'NQ'):3s}")
        logger.info("")

        # Score multi-critères
        score_es = 0
        score_nq = 0

        if es['winrate'] > nq['winrate']: score_es += 1
        else: score_nq += 1

        if es['pnl_per_trade'] > nq['pnl_per_trade']: score_es += 2
        else: score_nq += 2

        if es['profit_factor'] > nq['profit_factor']: score_es += 1
        else: score_nq += 1

        if es['sharpe'] > nq['sharpe']: score_es += 1
        else: score_nq += 1

        if es['max_dd'] > nq['max_dd']: score_nq += 1  # Moins de DD = mieux
        else: score_es += 1

        logger.info(f"  🏆 SCORE MULTI-CRITÈRES:")
        logger.info(f"     ES: {score_es}/6")
        logger.info(f"     NQ: {score_nq}/6")
        logger.info("")

        # Recommandation
        logger.info("=" * 90)
        logger.info("🎯 RECOMMANDATION:")
        logger.info("=" * 90)
        logger.info("")

        if score_nq > score_es:
            logger.info("  ✅ FOCUS NQ")
            logger.info(f"     - Meilleur P&L/trade: {nq['pnl_per_trade']:+.3f}t vs {es['pnl_per_trade']:+.3f}t")
            logger.info(f"     - Score: {score_nq}/6 vs {score_es}/6")
            logger.info(f"     - Projection 1 mois: ${nq['pnl_per_trade'] * nq['n_trades'] * 4:+,.2f}")
        elif score_es > score_nq:
            logger.info("  ✅ FOCUS ES")
            logger.info(f"     - Meilleur P&L/trade: {es['pnl_per_trade']:+.3f}t vs {nq['pnl_per_trade']:+.3f}t")
            logger.info(f"     - Score: {score_es}/6 vs {score_nq}/6")
            logger.info(f"     - Projection 1 mois: ${es['pnl_per_trade'] * es['n_trades'] * 4:+,.2f}")
        else:
            logger.info("  ⚖️ GARDER LES DEUX")
            logger.info(f"     - Performance équivalente")
            logger.info(f"     - Diversification bénéfique")
            logger.info(f"     - Projection 1 mois: ${(es['pnl_usd'] + nq['pnl_usd']) * 4:+,.2f}")

        logger.info("")
        logger.info("=" * 90)
        logger.info("")

    def generate_report(self, start_date: str = None, end_date: str = None):
        """Génère le rapport complet"""

        logger.info("")
        logger.info("=" * 90)
        logger.info("📊 ANALYSE HEBDOMADAIRE - PRODUCTION WEEK 1")
        logger.info("=" * 90)
        logger.info("")

        # Charger données
        df = self.load_trades(start_date, end_date)

        if df.empty:
            logger.error("❌ Aucune donnée à analyser")
            return

        # Analyses
        results = self.analyze_by_symbol(df)
        self.daily_consistency(df)
        self.compare_es_vs_nq(results)

        logger.info("")
        logger.info("=" * 90)
        logger.info("✅ ANALYSE TERMINÉE")
        logger.info("=" * 90)
        logger.info("")

        return results


def main():
    """Point d'entrée principal"""

    # Exemple: Analyser la semaine du 18-22 Nov 2025
    analyzer = WeeklyAnalyzer()

    # Option 1: Dernière semaine
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    results = analyzer.generate_report(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    return results


if __name__ == "__main__":
    main()







