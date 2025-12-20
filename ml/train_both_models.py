#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SCRIPT HELPER - ENTRAÎNEMENT 2 MODÈLES (ES + NQ)
═══════════════════════════════════════════════════════════════════════════════

Lance l'entraînement des 2 modèles en séquence :
1. Modèle ES
2. Modèle NQ

Usage:
    python ml/train_both_models.py

    # Avec options
    python ml/train_both_models.py --cross-validate --data-dir D:\MIA_IA_system

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_training(symbol: str, args):
    """
    Lance l'entraînement pour un symbole

    Args:
        symbol: 'ES' ou 'NQ'
        args: Arguments CLI

    Returns:
        True si succès, False sinon
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🚀 ENTRAÎNEMENT MODÈLE {symbol}")
    logger.info(f"{'='*70}")

    # ✅ CORRECTIF GPT : Chemins absolus + portabilité
    HERE = Path(__file__).resolve().parent
    TRAIN_SCRIPT = HERE / "train_ml_direction_15min.py"

    if not TRAIN_SCRIPT.exists():
        logger.error(f"❌ Script introuvable : {TRAIN_SCRIPT}")
        return False

    # Construire commande (avec sys.executable pour portabilité venv)
    cmd = [
        sys.executable,
        str(TRAIN_SCRIPT),
        '--symbol', symbol,
        '--data-dir', str(args.data_dir),
        '--output-dir', str(args.output_dir),
    ]

    if args.cross_validate:
        cmd.append('--cross-validate')

    if args.no_feature_engineering:
        cmd.append('--no-feature-engineering')

    # Lancer
    logger.info(f"📝 Commande : {' '.join(cmd)}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False  # Afficher output en direct
        )

        elapsed = time.time() - start_time
        logger.info(f"\n✅ Modèle {symbol} entraîné avec succès en {elapsed:.1f}s")
        return True

    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        logger.error(f"\n❌ Erreur entraînement {symbol} après {elapsed:.1f}s")
        logger.error(f"Code retour : {e.returncode}")
        return False


def main(args):
    """Fonction principale"""

    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 ENTRAÎNEMENT 2 MODÈLES (ES + NQ)")
    logger.info(f"{'='*70}")
    logger.info(f"📁 Répertoire données : {args.data_dir}")
    logger.info(f"📁 Répertoire sortie : {args.output_dir}")
    logger.info(f"🔄 Validation croisée : {'Oui' if args.cross_validate else 'Non'}")
    logger.info(f"{'='*70}")

    total_start = time.time()

    # ✅ CORRECTIF GPT : Résumé final avec statuts
    results = {'ES': False, 'NQ': False}

    # Entraîner ES
    success_es = run_training('ES', args)
    results['ES'] = success_es

    if not success_es:
        logger.error("\n❌ Échec entraînement ES.")
        logger.info("💡 Vérifier les logs ci-dessus pour détails")
        # Ne pas arrêter, essayer NQ quand même

    # Entraîner NQ
    success_nq = run_training('NQ', args)
    results['NQ'] = success_nq

    if not success_nq:
        logger.error("\n❌ Échec entraînement NQ.")
        logger.info("💡 Vérifier les logs ci-dessus pour détails")

    # Résumé final
    total_elapsed = time.time() - total_start

    logger.info(f"\n{'='*70}")
    logger.info(f"📊 RÉSUMÉ FINAL")
    logger.info(f"{'='*70}")
    logger.info(f"⏱️  Temps total : {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")

    logger.info(f"\n🎯 Statuts :")
    logger.info(f"   ES : {'✅ SUCCÈS' if results['ES'] else '❌ ÉCHEC'}")
    logger.info(f"   NQ : {'✅ SUCCÈS' if results['NQ'] else '❌ ÉCHEC'}")

    if results['ES'] and results['NQ']:
        logger.info(f"\n🎉 ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS")
        logger.info(f"\n📦 Modèles créés :")
        logger.info(f"   🔵 ES : {args.output_dir}/lgbm_direction_15min_ES_latest.pkl")
        logger.info(f"   🟢 NQ : {args.output_dir}/lgbm_direction_15min_NQ_latest.pkl")
        logger.info(f"\n🚀 Prochaines étapes :")
        logger.info(f"   1. Grid search : python ml/grid_search_thresholds.py")
        logger.info(f"   2. Comparer ES vs NQ (métriques)")
        logger.info(f"   3. Intégrer MLDualFilter dans le système")
        logger.info(f"{'='*70}")
        return 0
    elif results['ES'] or results['NQ']:
        logger.warning(f"\n⚠️ ENTRAÎNEMENT PARTIEL")
        if results['ES']:
            logger.info(f"   ✅ ES disponible : {args.output_dir}/lgbm_direction_15min_ES_latest.pkl")
        if results['NQ']:
            logger.info(f"   ✅ NQ disponible : {args.output_dir}/lgbm_direction_15min_NQ_latest.pkl")
        logger.info(f"{'='*70}")
        return 1
    else:
        logger.error(f"\n❌ ÉCHEC COMPLET - Aucun modèle entraîné")
        logger.info(f"{'='*70}")
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Entraînement 2 modèles (ES + NQ)"
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('.'),
        help='Répertoire racine des données (défaut: .)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('ml/models'),
        help='Répertoire de sortie (défaut: ml/models)'
    )

    parser.add_argument(
        '--cross-validate',
        action='store_true',
        help='Activer validation croisée (TimeSeriesSplit 5-fold)'
    )

    parser.add_argument(
        '--no-feature-engineering',
        action='store_true',
        help='Désactiver feature engineering (LAGs + Rolling)'
    )

    args = parser.parse_args()

    sys.exit(main(args))
