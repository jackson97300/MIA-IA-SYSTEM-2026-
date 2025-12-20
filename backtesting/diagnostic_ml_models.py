#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC MODÈLES ML
Vérifie l'état des modèles ML et leur calibration
"""

import sys
from pathlib import Path
import pickle
import json
import logging
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_model_quality():
    """Vérifie le modèle Quality Score"""
    model_path = Path("ml/models/lightgbm_quality_v1.pkl")
    metadata_path = Path("ml/models/lightgbm_quality_v1_metadata.json")

    logger.info("="*80)
    logger.info("📊 MODÈLE QUALITY SCORE")
    logger.info("="*80)

    if not model_path.exists():
        logger.error(f"❌ Modèle non trouvé: {model_path}")
        return False

    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

        logger.info(f"✅ Modèle trouvé: {model_path}")
        logger.info(f"   Version: {metadata.get('version', 'N/A')}")
        logger.info(f"   Features: {metadata.get('n_features', 0)}")
        logger.info(f"   Train dates: {metadata.get('split_info', {}).get('train_dates', [])}")
        logger.info(f"   Test dates: {metadata.get('split_info', {}).get('test_dates', [])}")
        logger.info(f"   Train win rate: {metadata.get('split_info', {}).get('train_win_rate', 0):.1%}")
        logger.info(f"   Test win rate: {metadata.get('split_info', {}).get('test_win_rate', 0):.1%}")

        # Vérifier si dates backtest chevauchent train/test
        backtest_dates = ["20251105", "20251106", "20251107", "20251108", "20251111",
                         "20251112", "20251113", "20251114", "20251115", "20251118",
                         "20251119", "20251120", "20251121"]

        train_dates = metadata.get('split_info', {}).get('train_dates', [])
        test_dates = metadata.get('split_info', {}).get('test_dates', [])

        overlap_train = set(backtest_dates) & set(train_dates)
        overlap_test = set(backtest_dates) & set(test_dates)

        if overlap_train:
            logger.warning(f"⚠️  CHEVAUCHEMENT avec train set: {overlap_train}")
        if overlap_test:
            logger.warning(f"⚠️  CHEVAUCHEMENT avec test set: {overlap_test}")

        return True
    else:
        logger.warning(f"⚠️  Metadata non trouvé: {metadata_path}")
        return False


def check_model_classifier():
    """Vérifie le modèle WIN/LOSS Classifier"""
    model_path = Path("ml/models/lightgbm_t1_binary_simple.pkl")

    logger.info("\n" + "="*80)
    logger.info("📊 MODÈLE WIN/LOSS CLASSIFIER")
    logger.info("="*80)

    if not model_path.exists():
        logger.error(f"❌ Modèle non trouvé: {model_path}")
        return False

    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        logger.info(f"✅ Modèle trouvé: {model_path}")
        logger.info(f"   Type: {type(model_data)}")

        # Vérifier si c'est un dict avec model/scaler/features
        if isinstance(model_data, dict):
            logger.info(f"   Clés: {list(model_data.keys())}")
            if 'model' in model_data:
                logger.info(f"   Model type: {type(model_data['model'])}")
            if 'features' in model_data:
                logger.info(f"   Features count: {len(model_data['features'])}")

        return True
    except Exception as e:
        logger.error(f"❌ Erreur lecture modèle: {e}")
        return False


def check_feature_alignment():
    """Vérifie l'alignement des features"""
    logger.info("\n" + "="*80)
    logger.info("📊 ALIGNEMENT FEATURES")
    logger.info("="*80)

    metadata_path = Path("ml/models/lightgbm_quality_v1_metadata.json")
    if not metadata_path.exists():
        logger.warning("⚠️  Metadata non disponible")
        return

    with open(metadata_path) as f:
        metadata = json.load(f)

    expected_features = metadata.get('feature_names', [])
    logger.info(f"✅ Features attendues: {len(expected_features)}")
    logger.info(f"   Exemples: {expected_features[:10]}")

    # Vérifier features critiques
    critical_features = [
        'confluence', 'layer1_confidence', 'gex_1', 'call_resistance',
        'put_support', 'hvl', 'delta', 'volume', 'vwap', 'atr'
    ]

    missing = [f for f in critical_features if f not in expected_features]
    if missing:
        logger.warning(f"⚠️  Features critiques manquantes: {missing}")
    else:
        logger.info(f"✅ Toutes les features critiques présentes")


def main():
    """Diagnostic complet"""
    logger.info("\n" + "="*80)
    logger.info("🔍 DIAGNOSTIC MODÈLES ML")
    logger.info("="*80)

    quality_ok = check_model_quality()
    classifier_ok = check_model_classifier()
    check_feature_alignment()

    logger.info("\n" + "="*80)
    logger.info("📋 RÉSUMÉ")
    logger.info("="*80)
    logger.info(f"Quality Score Model: {'✅ OK' if quality_ok else '❌ PROBLÈME'}")
    logger.info(f"WIN/LOSS Classifier: {'✅ OK' if classifier_ok else '❌ PROBLÈME'}")

    if not quality_ok or not classifier_ok:
        logger.warning("\n⚠️  RECOMMANDATION:")
        logger.warning("   1. Réentraîner les modèles sur données récentes")
        logger.warning("   2. Ou désactiver temporairement ML (use_ml_models=False)")
        logger.warning("   3. Vérifier alignement features avec snapshots réels")


if __name__ == '__main__':
    main()
