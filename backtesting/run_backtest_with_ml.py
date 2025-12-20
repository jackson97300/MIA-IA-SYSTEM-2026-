#!/usr/bin/env python3
"""
Script de lancement du backtest MenthorQ AVEC ML ENTRAÎNÉ

Utilise:
- ML 3-Layer Filter (1 signal/bar max)
- ML WIN/LOSS Probability (modèle entraîné)
- Filtre: Probabilité WIN >= 50%
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

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'backtesting/results/backtest_with_ml_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Execute backtest avec ML entraîné"""

    logger.info("="*80)
    logger.info("BACKTEST MENTHORQ - AVEC ML ENTRAÎNÉ")
    logger.info("="*80)
    logger.info("CONFIGURATION:")
    logger.info("  - 1 signal/bar maximum (via ML 3-Layer Strategy)")
    logger.info("  - Filtres ML 3-Layer actifs (Layer 1/2/3)")
    logger.info("  - ML WIN/LOSS Probability: ACTIF (modèle entraîné)")
    logger.info("  - Filtre ML: Probabilité WIN >= 50%")
    logger.info("  - SL/TP optimaux (ES: 30/45, NQ: 35/53)")
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
            config['data_path'] = str(project_root / data_path)

    # Activer ML dans la config
    config['use_ml_models'] = True

    logger.info(f"Configuration chargee: {config_path}")
    logger.info(f"ML Models: ACTIVÉ (use_ml_models=True)")

    # 2. Run backtest avec ML
    logger.info("\nLancement du backtest AVEC ML...")
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

    # 3. Afficher résultats
    logger.info("\n" + "="*80)
    logger.info("RESULTATS BACKTEST AVEC ML")
    logger.info("="*80)
    logger.info(f"Total Trades: {results.get('total_trades', 0):,}")
    logger.info(f"Win Rate: {results.get('win_rate', 0):.2f}%")
    logger.info(f"Total PnL (ticks): {results.get('total_pnl_ticks', 0):,.0f}")
    logger.info(f"Total PnL ($): ${results.get('total_pnl_dollars', 0):,.2f}")
    logger.info(f"Average PnL: {results.get('avg_pnl_ticks', 0):.2f} ticks/trade")

    summary = results.get('summary', {})
    if summary:
        logger.info(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")

    # 4. Sauvegarder résultats
    import json
    json_path = Path('backtesting/results/backtest_with_ml_results.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nOK: Resultats sauvegardes: {json_path}")

    logger.info("\n" + "="*80)
    logger.info("OK: BACKTEST AVEC ML TERMINE!")
    logger.info("="*80)


if __name__ == '__main__':
    main()
