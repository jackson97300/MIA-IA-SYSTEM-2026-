"""
RUN TARGET OPTIMIZATION - Script Principal

Ce script lance l'optimisation complète des 8 targets ML
et sélectionne celle qui maximise le P&L net out-of-sample.

Auteur: MIA Trading System
Date: 15 novembre 2025

Usage:
    # Standard (tous les trades, 15-20 min)
    python ml/6_TARGET_OPTIMIZATION/run_optimization.py

    # Rapide (1000 trades, 2 min)
    python ml/6_TARGET_OPTIMIZATION/run_optimization.py --fast --n_trades 1000

    # Custom
    python ml/6_TARGET_OPTIMIZATION/run_optimization.py \\
        --data ml/2_LABELING/labeled_trades.parquet \\
        --output ml/6_TARGET_OPTIMIZATION/results \\
        --fees 0.62
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Ajouter le root au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import depuis le module local
import importlib.util
spec = importlib.util.spec_from_file_location(
    "target_optimizer",
    Path(__file__).parent / "target_optimizer.py"
)
target_optimizer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target_optimizer_module)

TargetOptimizer = target_optimizer_module.TargetOptimizer
ALL_TARGETS = target_optimizer_module.ALL_TARGETS

# Configuration logging
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            output_dir / f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
    ]
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(
        description='Target Optimization System - Trouve la meilleure target ML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Standard (tous les trades)
  python run_optimization.py

  # Mode rapide (test sur 1000 trades)
  python run_optimization.py --fast --n_trades 1000

  # Custom data path
  python run_optimization.py --data /path/to/labeled_trades.parquet
        """
    )

    parser.add_argument(
        '--data',
        type=str,
        default='ml/2_LABELING/labeled_trades.parquet',
        help='Chemin vers labeled_trades.parquet (défaut: ml/2_LABELING/labeled_trades.parquet)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='ml/6_TARGET_OPTIMIZATION/results',
        help='Dossier de sortie pour résultats (défaut: ml/6_TARGET_OPTIMIZATION/results)'
    )

    parser.add_argument(
        '--fees',
        type=float,
        default=0.62,
        help='Fees par trade en ticks (défaut: 0.62)'
    )

    parser.add_argument(
        '--fast',
        action='store_true',
        help='Mode rapide: subset de données pour test (utiliser avec --n_trades)'
    )

    parser.add_argument(
        '--n_trades',
        type=int,
        default=None,
        help='Nombre de trades pour mode rapide (ex: 1000)'
    )

    parser.add_argument(
        '--targets',
        type=str,
        nargs='+',
        default=None,
        help='Targets spécifiques à tester (ex: T1_binary_simple T3_pnl_ratio_reg)'
    )

    return parser.parse_args()


def main():
    """Fonction principale"""

    # Banner
    print("\n" + "="*70)
    print("##   TARGET OPTIMIZATION SYSTEM")
    print("##   Trouve la meilleure target ML pour maximiser P&L")
    print("##   Auteur: MIA Trading System")
    print("="*70 + "\n")

    # Parse arguments
    args = parse_arguments()

    # Valider chemins
    data_path = Path(args.data)
    if not data_path.exists():
        logger.error(f"ERREUR: Fichier introuvable: {data_path}")
        logger.error(f"   Verifiez que labeled_trades.parquet existe")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Afficher configuration
    logger.info(f"CONFIGURATION:")
    logger.info(f"   Data: {data_path}")
    logger.info(f"   Output: {output_dir}")
    logger.info(f"   Fees: {args.fees}t/trade")

    if args.fast:
        logger.info(f"   Mode: RAPIDE (subset {args.n_trades or 'auto'} trades)")
    else:
        logger.info(f"   Mode: STANDARD (tous les trades)")

    if args.targets:
        logger.info(f"   Targets: {', '.join(args.targets)}")
    else:
        logger.info(f"   Targets: TOUTES ({len(ALL_TARGETS)} targets)")

    logger.info("")

    # Créer optimizer
    logger.info("Initialisation TargetOptimizer...")
    optimizer = TargetOptimizer(
        data_path=str(data_path),
        output_dir=str(output_dir),
        fees_per_trade=args.fees
    )

    # Filtrer targets si spécifié
    targets_to_test = ALL_TARGETS
    if args.targets:
        targets_to_test = [t for t in ALL_TARGETS if t.name in args.targets]
        if not targets_to_test:
            logger.error(f"❌ Aucune target valide dans: {args.targets}")
            return 1

    # Mode rapide: subset des données
    if args.fast and args.n_trades:
        logger.info(f"⏱️  Mode RAPIDE: Limitation à {args.n_trades} trades...")
        import pandas as pd
        df = pd.read_parquet(data_path)
        df_subset = df.sample(n=min(args.n_trades, len(df)), random_state=42)
        subset_path = output_dir / "subset_trades.parquet"
        df_subset.to_parquet(subset_path)
        optimizer.data_path = subset_path
        logger.info(f"   ✅ Subset créé: {len(df_subset)} trades")

    # Lancer pipeline
    try:
        logger.info("\n" + "="*70)
        logger.info("LANCEMENT PIPELINE OPTIMISATION")
        logger.info("="*70 + "\n")

        start_time = datetime.now()

        all_results, best_target, validation_results = optimizer.run_optimization_pipeline(
            targets_to_test=targets_to_test
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info("\n" + "="*70)
        logger.info("✅ PIPELINE TERMINÉ AVEC SUCCÈS !")
        logger.info("="*70)
        logger.info(f"   Durée: {elapsed/60:.1f} minutes")
        logger.info(f"   Targets testées: {len(all_results)}")
        logger.info(f"   Meilleure target: {best_target.target_name}")
        logger.info(f"   P&L net: {best_target.pnl_net:+,.1f}t")
        logger.info(f"   P&L/trade: {best_target.pnl_per_trade:+.2f}t")
        logger.info("")

        # Générer visualisations
        logger.info("📊 Génération visualisations...")
        optimizer.plot_pnl_comparison(all_results, optimizer.df_trades)
        optimizer.plot_metrics_heatmap(all_results)
        optimizer.plot_score_breakdown(best_target, all_results)

        # Générer rapport final
        logger.info("📝 Génération rapport final...")
        optimizer.generate_markdown_report(all_results, best_target, validation_results)

        logger.info("\n" + "="*70)
        logger.info("📁 RÉSULTATS DISPONIBLES:")
        logger.info("="*70)
        logger.info(f"   📊 Tableau comparatif: {output_dir / 'comparison_table.csv'}")
        logger.info(f"   🏆 Meilleure target: {output_dir / 'best_target.json'}")
        logger.info(f"   📈 Tous résultats: {output_dir / 'all_results.json'}")
        logger.info(f"   📝 Rapport complet: {output_dir / 'TARGET_OPTIMIZATION_REPORT.md'}")
        logger.info(f"   📊 Graphiques: {output_dir / 'plots/'}")
        logger.info("")

        # Recommandations
        logger.info("💡 PROCHAINES ÉTAPES:")
        logger.info("   1. Lire le rapport: TARGET_OPTIMIZATION_REPORT.md")
        logger.info("   2. Valider avec équipe trading")
        logger.info("   3. Implémenter dans bot production")
        logger.info("   4. Monitorer performance en live")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"\n❌ ERREUR PIPELINE: {e}")
        logger.exception(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
