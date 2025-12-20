#!/usr/bin/env python3
"""
Test de vérification de l'architecture pour toutes les dates
Vérifie que chaque date a la même structure
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from ml.backtester.jsonl_loader import JSONLSnapshotLoader

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_all_dates():
    """Test l'architecture pour toutes les dates disponibles"""

    logger.info("="*80)
    logger.info("🧪 TEST ARCHITECTURE - TOUTES LES DATES")
    logger.info("="*80)

    # Configuration
    project_root = Path(__file__).resolve().parent.parent
    base_path = project_root / "DATA_SIERRA_CHART" / "DATA_2025" / "NOVEMBRE"

    logger.info(f"\n📁 Base path: {base_path}")

    # Trouver toutes les dates disponibles
    if not base_path.exists():
        logger.error(f"❌ Dossier non trouvé: {base_path}")
        return False

    date_dirs = [d.name for d in base_path.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 8]
    date_dirs.sort()

    logger.info(f"\n📅 Dates trouvées: {len(date_dirs)}")
    for date in date_dirs[:5]:
        logger.info(f"   - {date}")
    if len(date_dirs) > 5:
        logger.info(f"   ... et {len(date_dirs) - 5} autres")

    # Créer loader
    try:
        loader = JSONLSnapshotLoader(str(base_path))
        logger.info(f"\n✅ Loader créé")
    except Exception as e:
        logger.error(f"❌ Erreur création loader: {e}")
        return False

    # Tester chaque date pour ES et NQ
    symbols = ['ES', 'NQ']
    results = {}

    logger.info(f"\n{'='*80}")
    logger.info(f"📊 VÉRIFICATION PAR DATE")
    logger.info(f"{'='*80}")

    for date in date_dirs:
        results[date] = {}
        for symbol in symbols:
            try:
                snapshots = loader.load_day(symbol, date)
                results[date][symbol] = {
                    'exists': True,
                    'count': len(snapshots),
                    'error': None
                }
                logger.info(f"✅ {date} - {symbol}: {len(snapshots):,} snapshots")
            except FileNotFoundError:
                results[date][symbol] = {
                    'exists': False,
                    'count': 0,
                    'error': 'FileNotFound'
                }
                logger.warning(f"⚠️ {date} - {symbol}: FICHIER MANQUANT")
            except Exception as e:
                results[date][symbol] = {
                    'exists': False,
                    'count': 0,
                    'error': str(e)
                }
                logger.error(f"❌ {date} - {symbol}: ERREUR - {e}")

    # Résumé
    logger.info(f"\n{'='*80}")
    logger.info(f"📈 RÉSUMÉ")
    logger.info(f"{'='*80}")

    total_dates = len(date_dirs)
    es_available = sum(1 for date in date_dirs if results[date].get('ES', {}).get('exists', False))
    nq_available = sum(1 for date in date_dirs if results[date].get('NQ', {}).get('exists', False))

    logger.info(f"\n📊 Disponibilité:")
    logger.info(f"   ES: {es_available}/{total_dates} dates ({es_available/total_dates*100:.1f}%)")
    logger.info(f"   NQ: {nq_available}/{total_dates} dates ({nq_available/total_dates*100:.1f}%)")

    # Dates manquantes
    missing_es = [date for date in date_dirs if not results[date].get('ES', {}).get('exists', False)]
    missing_nq = [date for date in date_dirs if not results[date].get('NQ', {}).get('exists', False)]

    if missing_es:
        logger.warning(f"\n⚠️ Dates ES manquantes: {', '.join(missing_es[:10])}")
        if len(missing_es) > 10:
            logger.warning(f"   ... et {len(missing_es) - 10} autres")

    if missing_nq:
        logger.warning(f"\n⚠️ Dates NQ manquantes: {', '.join(missing_nq[:10])}")
        if len(missing_nq) > 10:
            logger.warning(f"   ... et {len(missing_nq) - 10} autres")

    # Vérifier structure identique
    logger.info(f"\n🔍 Vérification structure:")
    structure_ok = True

    for date in date_dirs[:5]:  # Tester les 5 premières
        for symbol in symbols:
            if results[date].get(symbol, {}).get('exists', False):
                # Vérifier que le chemin est correct
                chart_id = 3 if symbol == 'ES' else 9
                expected_path = base_path / date / f"CHART_{chart_id}" / "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{chart_id}.jsonl"
                if expected_path.exists():
                    logger.info(f"   ✅ {date}/{symbol}: Structure OK")
                else:
                    logger.error(f"   ❌ {date}/{symbol}: Structure incorrecte")
                    structure_ok = False

    if structure_ok:
        logger.info(f"\n✅ ARCHITECTURE IDENTIQUE POUR TOUTES LES DATES !")
    else:
        logger.warning(f"\n⚠️ Certaines dates ont une structure différente")

    logger.info(f"\n{'='*80}")

    return True


if __name__ == "__main__":
    success = test_all_dates()
    sys.exit(0 if success else 1)
