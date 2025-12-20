"""
TP & SL OPTIMIZER EXTENDED - Analyse avec SL élargi
===================================================

Objectif: Re-tester avec SL plus large (12-18t) pour laisser respirer les trades
         et trouver le meilleur équilibre ES/NQ.

Auteur: MIA Trading System
Date: 15 Novembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Import de la classe existante
import sys
sys.path.append('.')
from ml.tp_sl_optimizer import TPSLOptimizer

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_with_larger_sl():
    """
    Analyse avec SL élargi (12-18t) pour laisser respirer les trades
    """

    logger.info("=" * 80)
    logger.info("ANALYSE EXTENDED - SL ELARGI POUR NQ (12-18t)")
    logger.info("=" * 80)
    logger.info("")

    output_dir = Path("ml/output")
    output_dir.mkdir(exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    all_results = {}

    # OPTIMISER ES ET NQ avec SL élargi
    for symbol in ["ES", "NQ"]:
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"OPTIMISATION {symbol} - SL ELARGI")
        logger.info("=" * 80)
        logger.info("")

        # Créer l'optimiseur
        optimizer = TPSLOptimizer(
            data_path="ml/data/labeled_trades.parquet",
            symbol=symbol,
            fees_per_trade=None
        )

        # Optimiser avec SL 12-18t (plus large)
        df_results = optimizer.optimize_tp_sl(
            tp_range=(15, 35, 1),   # TP: 15-35 ticks
            sl_range=(12, 18, 1)    # SL: 12-18 ticks (ELARGI)
        )

        # Sauvegarder résultats
        csv_file = output_dir / f"tp_sl_extended_{symbol}_{timestamp}.csv"
        df_results.to_csv(csv_file, index=False)
        logger.info(f"Resultats CSV: {csv_file}")

        # Générer heatmaps
        heatmap_file = output_dir / f"tp_sl_extended_heatmap_{symbol}_{timestamp}.png"
        optimizer.plot_heatmaps(df_results, save_path=heatmap_file)

        # Générer rapport
        report_file = output_dir / f"tp_sl_extended_{symbol}_{timestamp}.txt"
        report = optimizer.generate_report(df_results, save_path=report_file)

        all_results[symbol] = {
            'optimizer': optimizer,
            'df_results': df_results,
            'report': report
        }

    # RAPPORT COMPARATIF DETAILLE
    logger.info("")
    logger.info("=" * 80)
    logger.info("GENERATION RAPPORT COMPARATIF DETAILLE")
    logger.info("=" * 80)
    logger.info("")

    # Extraire meilleures combinaisons avec critères stricts
    best_es = all_results['ES']['optimizer'].find_best_combination(
        all_results['ES']['df_results'],
        'pnl_per_trade',
        min_rr=1.5,           # R:R minimum 1.5:1
        min_winrate=0.38,     # WinRate minimum 38%
        min_profit_factor=1.1 # PF minimum 1.1
    )

    best_nq = all_results['NQ']['optimizer'].find_best_combination(
        all_results['NQ']['df_results'],
        'pnl_per_trade',
        min_rr=1.5,
        min_winrate=0.38,
        min_profit_factor=1.1
    )

    # ANALYSE DES MEILLEURES ZONES (Top 20)
    logger.info("")
    logger.info("ANALYSE DES MEILLEURES ZONES:")
    logger.info("")

    for symbol in ["ES", "NQ"]:
        df = all_results[symbol]['df_results']
        top20 = df.nlargest(20, 'pnl_per_trade')

        logger.info(f"--- {symbol} TOP 20 ---")
        logger.info(f"TP moyen: {top20['tp_ticks'].mean():.1f}t")
        logger.info(f"SL moyen: {top20['sl_ticks'].mean():.1f}t")
        logger.info(f"R:R moyen: {top20['rr_ratio'].mean():.2f}:1")
        logger.info(f"P&L moyen: {top20['pnl_per_trade'].mean():+.3f}t")
        logger.info(f"WinRate moyen: {top20['winrate'].mean()*100:.1f}%")
        logger.info("")

    # Créer rapport comparatif détaillé
    comp_report = []
    comp_report.append("=" * 80)
    comp_report.append("RAPPORT COMPARATIF DETAILLE: TP/SL OPTIMAL ES vs NQ")
    comp_report.append("SL ELARGI (12-18t) - Trades qui respirent")
    comp_report.append("=" * 80)
    comp_report.append("")

    comp_report.append("## CONTEXTE")
    comp_report.append("")
    comp_report.append("Analyse avec SL elargi (12-18t) pour:")
    comp_report.append("- Laisser respirer les trades NQ (haute volatilite)")
    comp_report.append("- Eviter les stop-outs prematures")
    comp_report.append("- Trouver equilibre optimal ES/NQ")
    comp_report.append("")

    comp_report.append("## RESULTATS PAR SYMBOLE")
    comp_report.append("")

    # ES
    comp_report.append("### ES (S&P 500)")
    comp_report.append("")
    comp_report.append(f"TP Optimal:      {int(best_es['tp_ticks'])} ticks")
    comp_report.append(f"SL Optimal:      {int(best_es['sl_ticks'])} ticks")
    comp_report.append(f"R:R:             {best_es['rr_ratio']:.2f}:1")
    comp_report.append(f"P&L/trade:       {best_es['pnl_per_trade']:+.3f} ticks")
    comp_report.append(f"WinRate:         {best_es['winrate']*100:.1f}%")
    comp_report.append(f"Profit Factor:   {best_es['profit_factor']:.2f}")
    comp_report.append(f"TP Hit Rate:     {best_es['tp_hit_rate']*100:.1f}%")
    comp_report.append(f"SL Hit Rate:     {best_es['sl_hit_rate']*100:.1f}%")
    comp_report.append(f"Fees:            {all_results['ES']['optimizer'].fees_per_trade} ticks")
    comp_report.append("")
    pnl_usd_es = best_es['pnl_per_trade'] * 1000 * all_results['ES']['optimizer'].tick_value
    comp_report.append(f"Sur 1,000 trades: {pnl_usd_es:+,.2f} USD")
    comp_report.append("")

    # NQ
    comp_report.append("### NQ (Nasdaq-100)")
    comp_report.append("")
    comp_report.append(f"TP Optimal:      {int(best_nq['tp_ticks'])} ticks")
    comp_report.append(f"SL Optimal:      {int(best_nq['sl_ticks'])} ticks")
    comp_report.append(f"R:R:             {best_nq['rr_ratio']:.2f}:1")
    comp_report.append(f"P&L/trade:       {best_nq['pnl_per_trade']:+.3f} ticks")
    comp_report.append(f"WinRate:         {best_nq['winrate']*100:.1f}%")
    comp_report.append(f"Profit Factor:   {best_nq['profit_factor']:.2f}")
    comp_report.append(f"TP Hit Rate:     {best_nq['tp_hit_rate']*100:.1f}%")
    comp_report.append(f"SL Hit Rate:     {best_nq['sl_hit_rate']*100:.1f}%")
    comp_report.append(f"Fees:            {all_results['NQ']['optimizer'].fees_per_trade} ticks")
    comp_report.append("")
    pnl_usd_nq = best_nq['pnl_per_trade'] * 1000 * all_results['NQ']['optimizer'].tick_value
    comp_report.append(f"Sur 1,000 trades: {pnl_usd_nq:+,.2f} USD")
    comp_report.append("")

    # Comparaison
    comp_report.append("## COMPARAISON")
    comp_report.append("")

    comp_report.append("| Metrique | ES | NQ | Difference |")
    comp_report.append("|----------|----|----|------------|")
    comp_report.append(f"| TP | {int(best_es['tp_ticks'])}t | {int(best_nq['tp_ticks'])}t | {int(best_nq['tp_ticks']-best_es['tp_ticks']):+d}t |")
    comp_report.append(f"| SL | {int(best_es['sl_ticks'])}t | {int(best_nq['sl_ticks'])}t | {int(best_nq['sl_ticks']-best_es['sl_ticks']):+d}t |")
    comp_report.append(f"| R:R | {best_es['rr_ratio']:.2f}:1 | {best_nq['rr_ratio']:.2f}:1 | {(best_nq['rr_ratio']-best_es['rr_ratio']):+.2f} |")
    comp_report.append(f"| P&L/trade | {best_es['pnl_per_trade']:+.3f}t | {best_nq['pnl_per_trade']:+.3f}t | {(best_nq['pnl_per_trade']-best_es['pnl_per_trade']):+.3f}t |")
    comp_report.append(f"| WinRate | {best_es['winrate']*100:.1f}% | {best_nq['winrate']*100:.1f}% | {(best_nq['winrate']-best_es['winrate'])*100:+.1f}% |")
    comp_report.append(f"| Profit Factor | {best_es['profit_factor']:.2f} | {best_nq['profit_factor']:.2f} | {(best_nq['profit_factor']-best_es['profit_factor']):+.2f} |")
    comp_report.append(f"| TP Hit Rate | {best_es['tp_hit_rate']*100:.1f}% | {best_nq['tp_hit_rate']*100:.1f}% | {(best_nq['tp_hit_rate']-best_es['tp_hit_rate'])*100:+.1f}% |")
    comp_report.append(f"| SL Hit Rate | {best_es['sl_hit_rate']*100:.1f}% | {best_nq['sl_hit_rate']*100:.1f}% | {(best_nq['sl_hit_rate']-best_es['sl_hit_rate'])*100:+.1f}% |")
    comp_report.append(f"| P&L 1000 | ${pnl_usd_es:,.0f} | ${pnl_usd_nq:,.0f} | ${(pnl_usd_nq-pnl_usd_es):+,.0f} |")
    comp_report.append(f"| Objectif +1.0t | {'OUI' if best_es['pnl_per_trade'] >= 1.0 else 'NON'} | {'OUI' if best_nq['pnl_per_trade'] >= 1.0 else 'NON'} | - |")
    comp_report.append("")

    # Impact du SL élargi
    comp_report.append("## IMPACT DU SL ELARGI (12-18t)")
    comp_report.append("")
    comp_report.append("### Avantages:")
    comp_report.append(f"- Trades respirent mieux (SL NQ: {int(best_nq['sl_ticks'])}t vs 9t avant)")
    comp_report.append(f"- Moins de stop-outs prematures (SL Hit: {best_nq['sl_hit_rate']*100:.1f}%)")
    comp_report.append(f"- WinRate potentiellement ameliore")
    comp_report.append("")
    comp_report.append("### Compromis:")
    comp_report.append(f"- R:R reduit (mais compense par meilleur WinRate)")
    comp_report.append(f"- Risque par trade augmente")
    comp_report.append("")

    # Analyse Top 10 pour chaque symbole
    comp_report.append("## TOP 10 COMBINAISONS PAR SYMBOLE")
    comp_report.append("")

    for symbol in ["ES", "NQ"]:
        comp_report.append(f"### {symbol} Top 10:")
        comp_report.append("")
        df = all_results[symbol]['df_results']
        top10 = df.nlargest(10, 'pnl_per_trade')

        for i, (idx, row) in enumerate(top10.iterrows(), 1):
            comp_report.append(f"{i:2d}. TP={int(row['tp_ticks']):2d}t, SL={int(row['sl_ticks']):2d}t | "
                             f"R:R={row['rr_ratio']:.2f}:1 | "
                             f"P&L={row['pnl_per_trade']:+.3f}t | "
                             f"WR={row['winrate']*100:.1f}% | "
                             f"TP Hit={row['tp_hit_rate']*100:.1f}% | "
                             f"SL Hit={row['sl_hit_rate']*100:.1f}%")
        comp_report.append("")

    # Recommandation stratégique
    comp_report.append("## RECOMMANDATION STRATEGIQUE")
    comp_report.append("")

    # Décider si ES et NQ sont viables
    es_viable = best_es['pnl_per_trade'] >= 0.5
    nq_viable = best_nq['pnl_per_trade'] >= 0.5

    if es_viable and nq_viable:
        comp_report.append("**TRADER ES ET NQ SIMULTANEMENT**")
        comp_report.append("")
        comp_report.append("Les deux symboles sont rentables avec SL elargi.")
        comp_report.append("Configuration recommandee:")
    elif nq_viable and not es_viable:
        comp_report.append("**FOCUS EXCLUSIF SUR NQ**")
        comp_report.append("")
        comp_report.append("ES reste sous-performant meme avec SL elargi.")
        comp_report.append("Configuration recommandee:")
    else:
        comp_report.append("**REVISION COMPLETE DES SETUPS NECESSAIRE**")
        comp_report.append("")
        comp_report.append("Configuration actuelle:")

    comp_report.append("")
    comp_report.append("```python")
    comp_report.append("# ES:")
    comp_report.append(f"tp_ticks_es = {int(best_es['tp_ticks'])}  # R:R {best_es['rr_ratio']:.2f}:1")
    comp_report.append(f"sl_ticks_es = {int(best_es['sl_ticks'])}")
    comp_report.append(f"# Performance: {best_es['pnl_per_trade']:+.3f} t/trade")
    comp_report.append(f"# Status: {'ACTIF' if es_viable else 'SUSPENDU - Optimisation requise'}")
    comp_report.append("")
    comp_report.append("# NQ:")
    comp_report.append(f"tp_ticks_nq = {int(best_nq['tp_ticks'])}  # R:R {best_nq['rr_ratio']:.2f}:1")
    comp_report.append(f"sl_ticks_nq = {int(best_nq['sl_ticks'])}")
    comp_report.append(f"# Performance: {best_nq['pnl_per_trade']:+.3f} t/trade")
    comp_report.append(f"# Status: {'ACTIF' if nq_viable else 'SUSPENDU'}")
    comp_report.append("```")
    comp_report.append("")

    # Conclusion
    comp_report.append("## CONCLUSION")
    comp_report.append("")

    if best_nq['pnl_per_trade'] >= 1.0:
        comp_report.append(f"NQ ATTEINT l'objectif +1.0t/trade avec SL elargi ! (+{best_nq['pnl_per_trade']:+.3f}t)")
    else:
        gap = 1.0 - best_nq['pnl_per_trade']
        comp_report.append(f"NQ proche de l'objectif, gap: {gap:.3f}t ({gap/1.0*100:.1f}%)")

    if best_es['pnl_per_trade'] >= 1.0:
        comp_report.append(f"ES ATTEINT l'objectif +1.0t/trade ! (+{best_es['pnl_per_trade']:+.3f}t)")
    elif best_es['pnl_per_trade'] >= 0.5:
        comp_report.append(f"ES rentable mais sous-optimal (+{best_es['pnl_per_trade']:+.3f}t)")
    else:
        comp_report.append(f"ES necessite optimisation majeure (+{best_es['pnl_per_trade']:+.3f}t)")

    comp_report.append("")
    comp_report.append("=" * 80)

    comp_report_text = "\n".join(comp_report)

    # Sauvegarder rapport
    comp_file = output_dir / f"tp_sl_extended_COMPARISON_{timestamp}.txt"
    comp_file.write_text(comp_report_text, encoding='utf-8')
    logger.info(f"Rapport comparatif: {comp_file}")

    # Afficher rapports
    print("")
    print("=" * 80)
    print("RAPPORT ES (SL ELARGI)")
    print("=" * 80)
    print(all_results['ES']['report'])

    print("")
    print("=" * 80)
    print("RAPPORT NQ (SL ELARGI)")
    print("=" * 80)
    print(all_results['NQ']['report'])

    print("")
    print(comp_report_text)

    logger.info("")
    logger.info("ANALYSE EXTENDED TERMINEE [OK]")
    logger.info("=" * 80)


if __name__ == "__main__":
    analyze_with_larger_sl()







