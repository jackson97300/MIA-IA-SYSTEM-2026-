#!/usr/bin/env python3
"""
Script pour générer les rapports à partir des résultats compilés
Utilise les résultats déjà compilés dans le backtester
"""

import sys
from pathlib import Path
import yaml
import logging
import pickle

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backtesting.backtest_analyzer import BacktestAnalyzer
from backtesting.backtest_reporter import BacktestReporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_results_from_backtester():
    """Charge les résultats depuis un backtester existant"""
    logger.info("Chargement des resultats depuis le backtester...")

    # Créer un nouveau backtester et charger les résultats
    config_path = Path(__file__).parent / 'config' / 'backtest_config.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Convertir chemin data_path en absolu si relatif
    if 'data_path' in config:
        data_path = config['data_path']
        if not Path(data_path).is_absolute():
            config['data_path'] = str(project_root / data_path)

    from backtesting.menthorq_backtester import MenthorQBacktester
    backtester = MenthorQBacktester(config)

    # Charger les résultats compilés (si disponibles)
    # Pour l'instant, on va relancer la compilation depuis les trades
    logger.warning("Les resultats compiles ne sont pas sauvegardes.")
    logger.info("Pour generer les rapports, il faut relancer le backtest complet.")
    return None


def generate_reports_from_json():
    """Génère les rapports depuis un fichier JSON existant"""
    results_dir = Path('backtesting/results')
    json_files = list(results_dir.glob('backtest_data.json'))

    if not json_files:
        logger.error("Aucun fichier backtest_data.json trouve")
        return False

    json_path = json_files[0]
    logger.info(f"Chargement: {json_path}")

    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)

    logger.info(f"Resultats charges: {results.get('total_trades', 0):,} trades")

    # Analyser résultats
    logger.info("\nAnalyse des resultats...")
    analyzer = BacktestAnalyzer()

    analysis = {
        'level_performance': analyzer.analyze_level_performance(results),
        'sl_tp_performance': analyzer.analyze_sl_tp_performance(results),
        'time_performance': analyzer.analyze_time_performance(results),
        'avoid_periods': analyzer.identify_avoid_periods(results),
        'optimal_thresholds': analyzer.optimize_confidence_thresholds(results),
        'optimal_confluence': analyzer.optimize_confluence_strength(results),
        'market_context': analyzer.analyze_market_context(results)
    }

    # Générer rapports
    logger.info("\nGeneration des rapports...")
    reporter = BacktestReporter()

    # Résumé exécutif
    summary = reporter.generate_executive_summary(analysis, results)
    summary_path = Path('backtesting/results/EXECUTIVE_SUMMARY.md')
    summary_path.write_text(summary, encoding='utf-8')
    logger.info(f"OK: Resume executif: {summary_path}")

    # Rapport détaillé
    detailed = reporter.generate_detailed_report(analysis, results)
    detailed_path = Path('backtesting/results/DETAILED_REPORT.md')
    detailed_path.write_text(detailed, encoding='utf-8')
    logger.info(f"OK: Rapport detaille: {detailed_path}")

    # Export Excel (si disponible)
    try:
        excel_path = Path('backtesting/results/backtest_results.xlsx')
        reporter.export_to_excel(analysis, results, str(excel_path))
        logger.info(f"OK: Export Excel: {excel_path}")
    except Exception as e:
        logger.warning(f"ATTENTION: Export Excel echoue: {e}")

    logger.info("\n" + "="*80)
    logger.info("OK: RAPPORTS GENERES !")
    logger.info(f"Resultats dans: backtesting/results/")
    logger.info("="*80)

    return True


if __name__ == '__main__':
    if not generate_reports_from_json():
        logger.info("Tentative de chargement depuis backtester...")
        load_results_from_backtester()
