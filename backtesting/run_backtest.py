#!/usr/bin/env python3
"""
Script de lancement du backtest MenthorQ

Usage:
    python run_backtest.py
"""

import sys
from pathlib import Path
import yaml
import logging
from datetime import datetime

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backtesting.menthorq_backtester import MenthorQBacktester
from backtesting.backtest_analyzer import BacktestAnalyzer
from backtesting.backtest_reporter import BacktestReporter

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'backtesting/results/backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Execute backtest complet"""

    logger.info("="*80)
    logger.info("BACKTEST MENTHORQ - DEMARRAGE")
    logger.info("="*80)

    # 1. Charger config
    config_path = Path(__file__).parent / 'config' / 'backtest_config.yaml'

    if not config_path.exists():
        logger.error(f"ERREUR: Fichier config non trouve: {config_path}")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Convertir chemin data_path en absolu si relatif
    if 'data_path' in config:
        data_path = config['data_path']
        if not Path(data_path).is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            config['data_path'] = str(project_root / data_path)

    logger.info(f"Configuration chargee: {config_path}")

    # 2. Run backtest
    logger.info("\nLancement du backtest...")
    try:
        backtester = MenthorQBacktester(config)
        results = backtester.run_backtest()

        if not results:
            logger.error("ERREUR: Aucun resultat genere !")
            return
    except KeyboardInterrupt:
        logger.warning("\nATTENTION: Backtest interrompu par l'utilisateur")
        return
    except Exception as e:
        logger.error(f"\nERREUR CRITIQUE: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    logger.info(f"\nOK: Backtest termine: {results.get('total_trades', 0)} trades")

    # 3. Analyser résultats
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

    # 4. Générer rapports
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

    # Export JSON
    import json
    json_path = Path('backtesting/results/backtest_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"OK: Donnees JSON: {json_path}")

    # Export Excel (si disponible)
    try:
        excel_path = Path('backtesting/results/backtest_results.xlsx')
        reporter.export_to_excel(analysis, results, str(excel_path))
        logger.info(f"OK: Export Excel: {excel_path}")
    except Exception as e:
        logger.warning(f"ATTENTION: Export Excel echoue: {e}")

    logger.info("\n" + "="*80)
    logger.info("OK: BACKTEST TERMINE !")
    logger.info(f"Resultats dans: backtesting/results/")
    logger.info("="*80)


if __name__ == '__main__':
    main()
