"""
Backtest Reporter - Génération de rapports exhaustifs

Formats:
- Markdown (résumé exécutif)
- JSON (données brutes)
- Excel (tables détaillées)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BacktestReporter:
    """Générateur de rapports détaillés du backtest"""

    def generate_executive_summary(self, analysis: Dict, results: Dict) -> str:
        """
        Génère résumé exécutif en Markdown

        Contient:
        - Top 10 niveaux plus performants
        - Meilleure config SL/TP
        - Meilleures heures de trading
        - Périodes à éviter
        - Seuils optimaux
        - Recommendations finales
        """
        summary = []
        summary.append("# BACKTEST MENTHORQ - RESUME EXECUTIF\n")
        summary.append(f"**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        summary.append(f"**Total Trades**: {results.get('total_trades', 0):,}\n\n")

        # Top niveaux
        if 'level_performance' in analysis and not analysis['level_performance'].empty:
            summary.append("## Top 10 Niveaux les Plus Performants\n\n")
            top_levels = analysis['level_performance'].head(10)
            summary.append("| Niveau | Trades | Win Rate | P&L (ticks) | Avg P&L |\n")
            summary.append("|--------|--------|----------|-------------|----------|\n")
            for _, row in top_levels.iterrows():
                summary.append(
                    f"| {row['level']} | {row['trades']} | {row['win_rate']:.1f}% | "
                    f"{row['pnl_ticks']:.1f} | {row['avg_pnl']:.2f} |\n"
                )
            summary.append("\n")

        # Meilleure config SL/TP
        if 'sl_tp_performance' in analysis and not analysis['sl_tp_performance'].empty:
            summary.append("## Meilleure Configuration SL/TP\n\n")
            best_config = analysis['sl_tp_performance'].head(1)
            if len(best_config) > 0:
                row = best_config.iloc[0]
                summary.append(f"- **Config**: {row['config']}\n")
                summary.append(f"- **Trades**: {row['trades']}\n")
                summary.append(f"- **Win Rate**: {row['win_rate']:.1f}%\n")
                summary.append(f"- **P&L Total**: {row['pnl_ticks']:.1f} ticks\n")
                summary.append(f"- **Avg P&L**: {row['avg_pnl']:.2f} ticks/trade\n\n")

        # Meilleures heures
        if 'time_performance' in analysis and not analysis['time_performance'].empty:
            summary.append("## Meilleures Heures de Trading\n\n")
            top_hours = analysis['time_performance'].head(5)
            summary.append("| Heure | Trades | Win Rate | P&L (ticks) |\n")
            summary.append("|-------|--------|----------|-------------|\n")
            for _, row in top_hours.iterrows():
                summary.append(
                    f"| {int(row['hour'])}h00 | {row['trades']} | {row['win_rate']:.1f}% | "
                    f"{row['pnl_ticks']:.1f} |\n"
                )
            summary.append("\n")

        # Périodes à éviter
        if 'avoid_periods' in analysis:
            summary.append("## ATTENTION: Periodes a Eviter\n\n")
            for period in analysis['avoid_periods'][:5]:
                summary.append(f"- **{period['period']}**: {period['reason']}\n")
            summary.append("\n")

        # Recommendations
        summary.append("## Recommendations\n\n")
        if 'optimal_confluence' in analysis:
            opt_conf = analysis['optimal_confluence']
            summary.append(f"- **Confluence minimale**: {opt_conf.get('recommended', 3)} niveaux\n")

        return ''.join(summary)

    def generate_detailed_report(self, analysis: Dict, results: Dict) -> str:
        """
        Génère rapport détaillé avec toutes les analyses
        """
        report = []
        report.append("# BACKTEST MENTHORQ - RAPPORT DETAILLE\n\n")
        report.append(self.generate_executive_summary(analysis, results))

        # Ajouter sections détaillées
        report.append("\n## Analyses Detaillees\n\n")
        report.append("Voir fichiers Excel et JSON pour analyses complètes.\n")

        return ''.join(report)

    def export_to_excel(self, analysis: Dict, results: Dict, filepath: str):
        """
        Exporte vers Excel avec multiple sheets

        Sheets:
        - Summary
        - By_Level
        - By_SL_TP
        - By_Time
        - By_Confluence
        - All_Trades
        """
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Summary
                summary_data = {
                    'Metric': ['Total Trades', 'Wins', 'Losses', 'Win Rate', 'Total P&L', 'Avg P&L'],
                    'Value': [
                        results.get('summary', {}).get('total_trades', 0),
                        results.get('summary', {}).get('wins', 0),
                        results.get('summary', {}).get('losses', 0),
                        f"{results.get('summary', {}).get('win_rate', 0):.1f}%",
                        results.get('summary', {}).get('total_pnl_ticks', 0),
                        results.get('summary', {}).get('avg_pnl_ticks', 0)
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

                # By Level
                if 'level_performance' in analysis and not analysis['level_performance'].empty:
                    analysis['level_performance'].to_excel(writer, sheet_name='By_Level', index=False)

                # By SL/TP
                if 'sl_tp_performance' in analysis and not analysis['sl_tp_performance'].empty:
                    analysis['sl_tp_performance'].to_excel(writer, sheet_name='By_SL_TP', index=False)

                # By Time
                if 'time_performance' in analysis and not analysis['time_performance'].empty:
                    analysis['time_performance'].to_excel(writer, sheet_name='By_Time', index=False)

                # By Confluence
                if 'by_confluence' in results:
                    confluence_data = results['by_confluence']
                    rows = []
                    for strength, stats in confluence_data.items():
                        rows.append({
                            'Strength': strength,
                            'Trades': stats.get('trades', 0),
                            'Wins': stats.get('wins', 0),
                            'Losses': stats.get('losses', 0),
                            'Win Rate': stats.get('win_rate', 0),
                            'P&L Ticks': stats.get('pnl_ticks', 0)
                        })
                    if rows:
                        pd.DataFrame(rows).to_excel(writer, sheet_name='By_Confluence', index=False)

                # All Trades
                if 'all_trades' in results and results['all_trades']:
                    pd.DataFrame(results['all_trades']).to_excel(writer, sheet_name='All_Trades', index=False)

            logger.info(f"OK: Excel exporte: {filepath}")
        except ImportError:
            logger.warning("ATTENTION: openpyxl non installe, export Excel ignore")
        except Exception as e:
            logger.error(f"ERREUR: Erreur export Excel: {e}")
