#!/usr/bin/env python3
"""
Test de chargement des données ML_READY
Vérifie que l'architecture est correcte et que les fichiers sont accessibles
"""

import sys
from pathlib import Path
import json
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


def test_loader():
    """Test le chargement d'un fichier réel"""

    logger.info("="*80)
    logger.info("🧪 TEST DE CHARGEMENT ML_READY")
    logger.info("="*80)

    # Configuration - Chemin absolu depuis racine projet
    project_root = Path(__file__).resolve().parent.parent
    base_path = project_root / "DATA_SIERRA_CHART" / "DATA_2025" / "NOVEMBRE"
    symbol = "NQ"
    date = "20251121"

    logger.info(f"\n📁 Configuration:")
    logger.info(f"   Base path: {base_path}")
    logger.info(f"   Symbole: {symbol}")
    logger.info(f"   Date: {date}")

    # Créer loader (convertir Path en string)
    try:
        loader = JSONLSnapshotLoader(str(base_path))
        logger.info(f"\n✅ Loader créé avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur création loader: {e}")
        return False

    # Charger un jour
    try:
        logger.info(f"\n📂 Chargement: {date}/{symbol}...")
        snapshots = loader.load_day(symbol, date)
        logger.info(f"✅ {len(snapshots):,} snapshots chargés")
    except FileNotFoundError as e:
        logger.error(f"❌ Fichier non trouvé: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur chargement: {e}")
        return False

    if not snapshots:
        logger.warning("⚠️ Aucun snapshot chargé")
        return False

    # Analyser premier snapshot
    logger.info(f"\n📊 Analyse du premier snapshot:")
    first_snapshot = snapshots[0]

    # Vérifier champs clés
    logger.info(f"   Timestamp: {first_snapshot.get('t_ms', 'N/A')}")
    logger.info(f"   Mid: {first_snapshot.get('mid', 'N/A')}")
    logger.info(f"   Symbol: {first_snapshot.get('sym', 'N/A')}")

    # Vérifier niveaux MenthorQ
    logger.info(f"\n🎯 Niveaux MenthorQ détectés:")

    # GEX
    gex_count = 0
    for i in range(1, 11):
        key = f'gex_{i}'
        if key in first_snapshot and first_snapshot[key]:
            gex_count += 1
            if gex_count <= 3:  # Afficher les 3 premiers
                logger.info(f"   {key}: {first_snapshot[key]}")
    if gex_count > 3:
        logger.info(f"   ... et {gex_count - 3} autres niveaux GEX")

    # Blind Spots
    bs_count = 0
    for i in range(9):
        key = f'blind_spot_{i}'
        if key in first_snapshot and first_snapshot[key]:
            bs_count += 1
            if bs_count <= 3:
                logger.info(f"   {key}: {first_snapshot[key]}")
    if bs_count > 3:
        logger.info(f"   ... et {bs_count - 3} autres blind spots")

    # Structure
    structure_keys = ['call_resistance', 'put_support', 'hvl', 'vwap']
    logger.info(f"\n📐 Niveaux structure:")
    for key in structure_keys:
        if key in first_snapshot and first_snapshot[key]:
            logger.info(f"   {key}: {first_snapshot[key]}")

    # Statistiques globales
    logger.info(f"\n📈 Statistiques sur tous les snapshots:")
    logger.info(f"   Total: {len(snapshots):,}")

    # Compter snapshots avec niveaux
    snapshots_with_gex = sum(1 for s in snapshots if any(f'gex_{i}' in s and s[f'gex_{i}'] for i in range(1, 11)))
    snapshots_with_bs = sum(1 for s in snapshots if any(f'blind_spot_{i}' in s and s[f'blind_spot_{i}'] for i in range(9)))

    logger.info(f"   Snapshots avec GEX: {snapshots_with_gex:,} ({snapshots_with_gex/len(snapshots)*100:.1f}%)")
    logger.info(f"   Snapshots avec Blind Spots: {snapshots_with_bs:,} ({snapshots_with_bs/len(snapshots)*100:.1f}%)")

    logger.info(f"\n✅ TEST RÉUSSI !")
    logger.info("="*80)

    return True


if __name__ == "__main__":
    success = test_loader()
    sys.exit(0 if success else 1)
