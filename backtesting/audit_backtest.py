#!/usr/bin/env python3
"""
Script d'audit du backtest MenthorQ
Identifie les problèmes potentiels avant le lancement
"""

import sys
from pathlib import Path
import yaml
import logging
import traceback

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backtesting.menthorq_backtester import MenthorQBacktester
from ml.backtester.jsonl_loader import JSONLSnapshotLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def audit_config():
    """Audit de la configuration"""
    logger.info("="*80)
    logger.info("AUDIT 1: CONFIGURATION")
    logger.info("="*80)

    issues = []

    config_path = Path(__file__).parent / 'config' / 'backtest_config.yaml'
    if not config_path.exists():
        issues.append(f"Fichier config non trouve: {config_path}")
        return issues

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Vérifier chemins
        data_path = config.get('data_path', '')
        if not data_path:
            issues.append("data_path manquant dans config")
        else:
            if not Path(data_path).is_absolute():
                data_path = project_root / data_path
            if not Path(data_path).exists():
                issues.append(f"Chemin donnees inexistant: {data_path}")
            else:
                logger.info(f"OK: Chemin donnees: {data_path}")

        # Vérifier symboles
        symbols = config.get('symbols', [])
        if not symbols:
            issues.append("Aucun symbole configure")
        else:
            logger.info(f"OK: Symboles: {symbols}")

        # Vérifier dates
        date_range = config.get('date_range', {})
        start_date = date_range.get('start') or config.get('start_date')
        end_date = date_range.get('end') or config.get('end_date')
        if not start_date or not end_date:
            issues.append("Dates manquantes dans config (cherche date_range.start/end ou start_date/end_date)")
        else:
            logger.info(f"OK: Periode: {start_date} a {end_date}")

    except Exception as e:
        issues.append(f"Erreur lecture config: {e}")
        logger.error(traceback.format_exc())

    if issues:
        logger.error(f"ERREURS TROUVEES: {len(issues)}")
        for issue in issues:
            logger.error(f"  - {issue}")
    else:
        logger.info("OK: Configuration valide")

    return issues


def audit_data_loading():
    """Audit du chargement des données"""
    logger.info("\n" + "="*80)
    logger.info("AUDIT 2: CHARGEMENT DONNEES")
    logger.info("="*80)

    issues = []

    try:
        config_path = Path(__file__).parent / 'config' / 'backtest_config.yaml'
        with open(config_path) as f:
            config = yaml.safe_load(f)

        data_path = config.get('data_path', '')
        if not Path(data_path).is_absolute():
            data_path = project_root / data_path

        loader = JSONLSnapshotLoader(str(data_path))
        logger.info(f"OK: Loader cree")

        # Tester chargement d'une date
        symbols = config.get('symbols', ['ES', 'NQ'])
        date_range = config.get('date_range', {})
        start_date = date_range.get('start') or config.get('start_date', '2025-11-05')

        for symbol in symbols:
            try:
                snapshots = loader.load_day(symbol, start_date.replace('-', ''))
                logger.info(f"OK: {symbol} - {len(snapshots):,} snapshots pour {start_date}")

                if len(snapshots) == 0:
                    issues.append(f"Aucun snapshot pour {symbol} le {start_date}")

                # Vérifier structure snapshot
                if snapshots:
                    sample = snapshots[0]
                    required_keys = ['t_ms', 'mid']  # 'last' est optionnel (fallback sur 'mid')
                    missing = [k for k in required_keys if k not in sample]
                    if missing:
                        issues.append(f"Clefs manquantes dans snapshot {symbol}: {missing}")
                    else:
                        # Vérifier qu'au moins 'mid' ou 'last' existe
                        if 'mid' not in sample and 'last' not in sample:
                            issues.append(f"Snapshot {symbol} doit avoir 'mid' ou 'last'")
                        else:
                            logger.info(f"OK: Structure snapshot {symbol} valide")

            except FileNotFoundError as e:
                issues.append(f"Fichier non trouve pour {symbol}: {e}")
            except Exception as e:
                issues.append(f"Erreur chargement {symbol}: {e}")
                logger.error(traceback.format_exc())

    except Exception as e:
        issues.append(f"Erreur audit donnees: {e}")
        logger.error(traceback.format_exc())

    if issues:
        logger.error(f"ERREURS TROUVEES: {len(issues)}")
        for issue in issues:
            logger.error(f"  - {issue}")
    else:
        logger.info("OK: Chargement donnees valide")

    return issues


def audit_backtester_init():
    """Audit de l'initialisation du backtester"""
    logger.info("\n" + "="*80)
    logger.info("AUDIT 3: INITIALISATION BACKTESTER")
    logger.info("="*80)

    issues = []

    try:
        config_path = Path(__file__).parent / 'config' / 'backtest_config.yaml'
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Convertir chemin data_path en absolu si relatif
        if 'data_path' in config:
            data_path = config['data_path']
            if not Path(data_path).is_absolute():
                config['data_path'] = str(project_root / data_path)

        backtester = MenthorQBacktester(config)
        logger.info("OK: Backtester initialise")

        # Vérifier méthodes critiques
        required_methods = [
            'extract_all_levels',
            'identify_confluences',
            'test_sl_tp_configuration',
            'run_backtest'
        ]

        for method in required_methods:
            if not hasattr(backtester, method):
                issues.append(f"Methode manquante: {method}")
            else:
                logger.info(f"OK: Methode {method} presente")

    except Exception as e:
        issues.append(f"Erreur initialisation backtester: {e}")
        logger.error(traceback.format_exc())

    if issues:
        logger.error(f"ERREURS TROUVEES: {len(issues)}")
        for issue in issues:
            logger.error(f"  - {issue}")
    else:
        logger.info("OK: Initialisation backtester valide")

    return issues


def audit_methods():
    """Audit des méthodes critiques avec données réelles"""
    logger.info("\n" + "="*80)
    logger.info("AUDIT 4: METHODES CRITIQUES")
    logger.info("="*80)

    issues = []

    try:
        config_path = Path(__file__).parent / 'config' / 'backtest_config.yaml'
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if 'data_path' in config:
            data_path = config['data_path']
            if not Path(data_path).is_absolute():
                config['data_path'] = str(project_root / data_path)

        backtester = MenthorQBacktester(config)

        # Charger un snapshot de test
        loader = JSONLSnapshotLoader(config['data_path'])
        symbols = config.get('symbols', ['ES'])
        date_range = config.get('date_range', {})
        start_date = (date_range.get('start') or config.get('start_date', '2025-11-05')).replace('-', '')

        for symbol in symbols[:1]:  # Tester seulement le premier
            try:
                snapshots = loader.load_day(symbol, start_date)
                if not snapshots:
                    issues.append(f"Aucun snapshot pour tester {symbol}")
                    continue

                # Tester extract_all_levels
                test_snapshot = snapshots[100]  # Éviter les premiers
                try:
                    levels = backtester.extract_all_levels(test_snapshot)
                    logger.info(f"OK: extract_all_levels - {len(levels)} niveaux extraits")
                except Exception as e:
                    issues.append(f"Erreur extract_all_levels: {e}")
                    logger.error(traceback.format_exc())

                # Tester identify_confluences
                try:
                    current_price = test_snapshot.get('mid', test_snapshot.get('last', 0))
                    if current_price > 0:
                        confluences = backtester.identify_confluences(levels, current_price, symbol)
                        logger.info(f"OK: identify_confluences - {len(confluences)} confluences trouvees")
                    else:
                        issues.append("Prix invalide dans snapshot de test")
                except Exception as e:
                    issues.append(f"Erreur identify_confluences: {e}")
                    logger.error(traceback.format_exc())

                # Tester test_sl_tp_configuration avec données minimales
                try:
                    if current_price > 0 and len(snapshots) > 150:
                        future_snapshots = snapshots[101:151]
                        sl_config = {'method': 'fixed', 'ticks': 10}
                        tp_config = {'method': 'rr', 'ratio': 1.5}

                        result = backtester.test_sl_tp_configuration(
                            entry=current_price,
                            direction='LONG',
                            sl_config=sl_config,
                            tp_config=tp_config,
                            future_snapshots=future_snapshots,
                            tick_size=0.25,
                            symbol=symbol
                        )
                        logger.info(f"OK: test_sl_tp_configuration - Resultat: {result.get('outcome', 'UNKNOWN')}")
                    else:
                        issues.append("Pas assez de snapshots pour tester SL/TP")
                except Exception as e:
                    issues.append(f"Erreur test_sl_tp_configuration: {e}")
                    logger.error(traceback.format_exc())

            except Exception as e:
                issues.append(f"Erreur test {symbol}: {e}")
                logger.error(traceback.format_exc())

    except Exception as e:
        issues.append(f"Erreur audit methodes: {e}")
        logger.error(traceback.format_exc())

    if issues:
        logger.error(f"ERREURS TROUVEES: {len(issues)}")
        for issue in issues:
            logger.error(f"  - {issue}")
    else:
        logger.info("OK: Methodes critiques valides")

    return issues


def main():
    """Execute audit complet"""
    logger.info("\n" + "="*80)
    logger.info("AUDIT COMPLET DU BACKTEST MENTHORQ")
    logger.info("="*80)

    all_issues = []

    # Audit 1: Configuration
    all_issues.extend(audit_config())

    # Audit 2: Chargement données
    all_issues.extend(audit_data_loading())

    # Audit 3: Initialisation backtester
    all_issues.extend(audit_backtester_init())

    # Audit 4: Méthodes critiques
    all_issues.extend(audit_methods())

    # Résumé final
    logger.info("\n" + "="*80)
    logger.info("RESUME AUDIT")
    logger.info("="*80)

    if all_issues:
        logger.error(f"\nERREURS TROUVEES: {len(all_issues)}")
        for i, issue in enumerate(all_issues, 1):
            logger.error(f"  {i}. {issue}")
        logger.error("\nCORRIGER LES ERREURS AVANT DE LANCER LE BACKTEST")
        return False
    else:
        logger.info("\nOK: AUCUNE ERREUR TROUVEE")
        logger.info("LE BACKTEST PEUT ETRE LANCE")
        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
