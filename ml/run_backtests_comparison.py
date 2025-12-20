"""
Lanceur de Backtest Comparatif: Baseline vs Optimisé
====================================================

Lance les 2 backtests et génère un rapport comparatif

Usage:
    python ml/run_backtests_comparison.py

Date: 15 Novembre 2025
"""

import subprocess
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_backtest(script_name: str):
    """
    Lance un script de backtest

    Args:
        script_name: Nom du script Python à lancer
    """
    logger.info(f"Lancement de {script_name}...")
    logger.info("=" * 70)

    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"ERREUR lors de l'exécution de {script_name}")
        return False

    logger.info(f"{script_name} terminé avec succès")
    logger.info("")
    return True


def generate_comparison_report():
    """
    Génère un rapport comparatif entre Baseline et Optimisé
    """
    logger.info("Génération du rapport comparatif...")

    # Charger les résultats
    baseline_csv = Path("ml/output/backtest_baseline_results.csv")
    optimized_csv = Path("ml/output/backtest_optimized_results.csv")

    if not baseline_csv.exists() or not optimized_csv.exists():
        logger.error("Fichiers de résultats manquants!")
        return

    df_baseline = pd.read_csv(baseline_csv)
    df_optimized = pd.read_csv(optimized_csv)

    # Calculer métriques comparatives
    report = []
    report.append("=" * 90)
    report.append("RAPPORT COMPARATIF: BASELINE (ATR) vs OPTIMISÉ (TP/SL FIXES)")
    report.append("=" * 90)
    report.append("")
    report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("-" * 90)

    for symbol in ['ES', 'NQ', 'TOTAL']:
        if symbol == 'TOTAL':
            df_b = df_baseline
            df_o = df_optimized
        else:
            df_b = df_baseline[df_baseline['symbol'] == symbol]
            df_o = df_optimized[df_optimized['symbol'] == symbol]

        if len(df_b) == 0 or len(df_o) == 0:
            continue

        # Métriques Baseline
        b_pnl_net = df_b['pnl_ticks'].sum()
        b_pnl_per_trade = b_pnl_net / len(df_b)
        b_winrate = len(df_b[df_b['pnl_ticks'] > 0]) / len(df_b)
        b_tp_hit = df_b['hit_tp'].sum() / len(df_b)
        b_sl_hit = df_b['hit_sl'].sum() / len(df_b)
        b_avg_sl = df_b['sl_ticks'].mean()
        b_avg_tp = df_b['tp_ticks'].mean()

        # Métriques Optimisé
        o_pnl_net = df_o['pnl_ticks'].sum()
        o_pnl_per_trade = o_pnl_net / len(df_o)
        o_winrate = len(df_o[df_o['pnl_ticks'] > 0]) / len(df_o)
        o_tp_hit = df_o['hit_tp'].sum() / len(df_o)
        o_sl_hit = df_o['hit_sl'].sum() / len(df_o)
        o_avg_sl = df_o['sl_ticks'].mean()
        o_avg_tp = df_o['tp_ticks'].mean()

        # Différences
        diff_pnl_net = o_pnl_net - b_pnl_net
        diff_pnl_per_trade = o_pnl_per_trade - b_pnl_per_trade
        diff_winrate = o_winrate - b_winrate
        diff_tp_hit = o_tp_hit - b_tp_hit
        diff_sl_hit = o_sl_hit - b_sl_hit

        report.append("")
        report.append(f"{'=' * 40} {symbol} {'=' * 40}")
        report.append("")
        report.append(f"{'MÉTRIQUE':<30} {'BASELINE':>15} {'OPTIMISÉ':>15} {'DIFF':>15}")
        report.append("-" * 90)
        report.append(f"{'Trades':<30} {len(df_b):>15} {len(df_o):>15} {len(df_o)-len(df_b):>15}")
        report.append("")
        report.append(f"{'P&L Net (ticks)':<30} {b_pnl_net:>15.2f} {o_pnl_net:>15.2f} {diff_pnl_net:>15.2f}")
        report.append(f"{'P&L/trade (ticks)':<30} {b_pnl_per_trade:>15.3f} {o_pnl_per_trade:>15.3f} {diff_pnl_per_trade:>15.3f}")
        report.append("")
        report.append(f"{'WinRate':<30} {b_winrate*100:>14.1f}% {o_winrate*100:>14.1f}% {diff_winrate*100:>14.1f}%")
        report.append("")
        report.append(f"{'TP Hit Rate':<30} {b_tp_hit*100:>14.1f}% {o_tp_hit*100:>14.1f}% {diff_tp_hit*100:>14.1f}%")
        report.append(f"{'SL Hit Rate':<30} {b_sl_hit*100:>14.1f}% {o_sl_hit*100:>14.1f}% {diff_sl_hit*100:>14.1f}%")
        report.append("")
        report.append(f"{'Avg SL (ticks)':<30} {b_avg_sl:>15.1f} {o_avg_sl:>15.1f} {o_avg_sl-b_avg_sl:>15.1f}")
        report.append(f"{'Avg TP (ticks)':<30} {b_avg_tp:>15.1f} {o_avg_tp:>15.1f} {o_avg_tp-b_avg_tp:>15.1f}")
        report.append("")

    report.append("=" * 90)
    report.append("")
    report.append("ANALYSE:")
    report.append("")

    # Analyse ES
    df_b_es = df_baseline[df_baseline['symbol'] == 'ES']
    df_o_es = df_optimized[df_optimized['symbol'] == 'ES']
    if len(df_b_es) > 0 and len(df_o_es) > 0:
        es_improvement = (df_o_es['pnl_ticks'].sum() / len(df_o_es)) - (df_b_es['pnl_ticks'].sum() / len(df_b_es))
        es_status = "AMÉLIORATION" if es_improvement > 0 else "DÉGRADATION"
        report.append(f"  ES: {es_status} de {es_improvement:+.3f} t/trade")

    # Analyse NQ
    df_b_nq = df_baseline[df_baseline['symbol'] == 'NQ']
    df_o_nq = df_optimized[df_optimized['symbol'] == 'NQ']
    if len(df_b_nq) > 0 and len(df_o_nq) > 0:
        nq_improvement = (df_o_nq['pnl_ticks'].sum() / len(df_o_nq)) - (df_b_nq['pnl_ticks'].sum() / len(df_b_nq))
        nq_status = "AMÉLIORATION" if nq_improvement > 0 else "DÉGRADATION"
        report.append(f"  NQ: {nq_status} de {nq_improvement:+.3f} t/trade")

    report.append("")

    # Recommandation
    total_improvement = (df_optimized['pnl_ticks'].sum() / len(df_optimized)) - (df_baseline['pnl_ticks'].sum() / len(df_baseline))
    report.append("RECOMMANDATION:")
    report.append("")
    if total_improvement > 0:
        report.append(f"  LANCER EN PRODUCTION avec config OPTIMISÉE")
        report.append(f"  Amélioration globale: {total_improvement:+.3f} t/trade")
    else:
        report.append(f"  INVESTIGUER: Config optimisée sous-performe ({total_improvement:+.3f} t/trade)")
        report.append(f"  Analyser en détail les trades avant lancement")

    report.append("")
    report.append("=" * 90)

    report_text = "\n".join(report)

    # Sauvegarder
    output_file = Path("ml/output/backtest_comparison_report.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)

    logger.info(f"Rapport comparatif sauvegardé: {output_file}")

    # Afficher
    print(report_text)


def main():
    """
    Fonction principale
    """
    logger.info("=" * 90)
    logger.info("LANCEMENT DES BACKTESTS COMPARATIFS")
    logger.info("=" * 90)
    logger.info("")

    # 1. Backtest Baseline
    logger.info("ÉTAPE 1/3: Backtest BASELINE (ATR adaptatif)")
    success_baseline = run_backtest("ml/backtest_current_ml3layer.py")

    if not success_baseline:
        logger.error("Échec du backtest BASELINE. Arrêt.")
        return

    # 2. Backtest Optimisé
    logger.info("ÉTAPE 2/3: Backtest OPTIMISÉ (TP/SL fixes)")
    success_optimized = run_backtest("ml/backtest_optimized_ml3layer.py")

    if not success_optimized:
        logger.error("Échec du backtest OPTIMISÉ. Arrêt.")
        return

    # 3. Rapport comparatif
    logger.info("ÉTAPE 3/3: Génération du rapport comparatif")
    generate_comparison_report()

    logger.info("")
    logger.info("=" * 90)
    logger.info("BACKTESTS COMPARATIFS TERMINÉS AVEC SUCCÈS")
    logger.info("=" * 90)
    logger.info("")
    logger.info("Fichiers générés:")
    logger.info("  - ml/output/backtest_baseline_results.csv")
    logger.info("  - ml/output/backtest_baseline_report.txt")
    logger.info("  - ml/output/backtest_optimized_results.csv")
    logger.info("  - ml/output/backtest_optimized_report.txt")
    logger.info("  - ml/output/backtest_comparison_report.txt")
    logger.info("")


if __name__ == "__main__":
    main()







