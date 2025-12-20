"""
AUDIT DE COHERENCE DU SYSTEME MIA
==================================

Verifie que tout est coherent et stable:
1. Configuration des seuils
2. Fichiers critiques
3. Imports et dependances
4. Coherence entre fichiers
"""

import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ajouter le path
sys.path.insert(0, str(Path(__file__).parent.parent))

ERRORS = []
WARNINGS = []
OK = []


def check(condition, msg_ok, msg_fail, is_warning=False):
    """Helper pour les checks"""
    if condition:
        OK.append(msg_ok)
        return True
    else:
        if is_warning:
            WARNINGS.append(msg_fail)
        else:
            ERRORS.append(msg_fail)
        return False


def audit_config_files():
    """Verifie les fichiers de configuration"""
    print("\n[1] AUDIT FICHIERS CONFIGURATION")
    print("-"*60)

    # unified_thresholds.py
    config_path = Path("config/unified_thresholds.py")
    check(config_path.exists(),
          "unified_thresholds.py existe",
          "unified_thresholds.py MANQUANT!")

    # Verifier les imports
    try:
        from config.unified_thresholds import (
            MIN_TOTAL_CONFIDENCE,
            MIN_LAYER_CONFIDENCE,
            MAX_DISTANCE_TO_LEVEL,
            LAYER_WEIGHTS
        )
        check(True, "Import unified_thresholds OK", "")

        # Verifier les valeurs
        check(MIN_TOTAL_CONFIDENCE.get('ES') == 0.30,
              f"ES MIN_TOTAL_CONFIDENCE = 0.30 OK",
              f"ES MIN_TOTAL_CONFIDENCE = {MIN_TOTAL_CONFIDENCE.get('ES')} (attendu 0.30)")

        check(MIN_TOTAL_CONFIDENCE.get('NQ') == 0.30,
              f"NQ MIN_TOTAL_CONFIDENCE = 0.30 OK",
              f"NQ MIN_TOTAL_CONFIDENCE = {MIN_TOTAL_CONFIDENCE.get('NQ')} (attendu 0.30)")

        check(MAX_DISTANCE_TO_LEVEL.get('ES') == 15,
              f"ES MAX_DISTANCE_TO_LEVEL = 15 OK",
              f"ES MAX_DISTANCE_TO_LEVEL = {MAX_DISTANCE_TO_LEVEL.get('ES')} (attendu 15)", True)

        check(MAX_DISTANCE_TO_LEVEL.get('NQ') == 25,
              f"NQ MAX_DISTANCE_TO_LEVEL = 25 OK",
              f"NQ MAX_DISTANCE_TO_LEVEL = {MAX_DISTANCE_TO_LEVEL.get('NQ')} (attendu 25)", True)

    except ImportError as e:
        ERRORS.append(f"Import unified_thresholds ECHOUE: {e}")


def audit_ml_filter():
    """Verifie le ML 3-Layer Filter"""
    print("\n[2] AUDIT ML 3-LAYER FILTER")
    print("-"*60)

    try:
        from ml.ml_3layer_filter import ML3LayerFilter, TradeSignal
        check(True, "Import ML3LayerFilter OK", "")

        # Tester l'initialisation
        f = ML3LayerFilter()
        check(True, "ML3LayerFilter initialisation OK", "")

        # Tester la methode _check_orderflow_alignment
        check(hasattr(f, '_check_orderflow_alignment'),
              "_check_orderflow_alignment existe",
              "_check_orderflow_alignment MANQUANT!")

        # Test avec donnees
        snap_bullish = {'depth_imbalance': 0.3, 'delta': 100, 'ob_center': 0.5, 'tick_momentum': 0.4}
        snap_bearish = {'depth_imbalance': -0.3, 'delta': -100, 'ob_center': -0.5, 'tick_momentum': -0.4}

        # Test SHORT avec signaux acheteurs (doit bloquer)
        result = f._check_orderflow_alignment(snap_bullish, TradeSignal.SHORT)
        check(result[0] == False,
              "SHORT bloque avec signaux acheteurs OK",
              f"SHORT non bloque avec signaux acheteurs! {result}")

        # Test SHORT avec signaux vendeurs (doit autoriser)
        result = f._check_orderflow_alignment(snap_bearish, TradeSignal.SHORT)
        check(result[0] == True,
              "SHORT autorise avec signaux vendeurs OK",
              f"SHORT bloque avec signaux vendeurs! {result}")

        # Test LONG avec signaux vendeurs (doit bloquer)
        result = f._check_orderflow_alignment(snap_bearish, TradeSignal.LONG)
        check(result[0] == False,
              "LONG bloque avec signaux vendeurs OK",
              f"LONG non bloque avec signaux vendeurs! {result}")

        # Test LONG avec signaux acheteurs (doit autoriser)
        result = f._check_orderflow_alignment(snap_bullish, TradeSignal.LONG)
        check(result[0] == True,
              "LONG autorise avec signaux acheteurs OK",
              f"LONG bloque avec signaux acheteurs! {result}")

    except Exception as e:
        ERRORS.append(f"Audit ML Filter ECHOUE: {e}")


def audit_launch_script():
    """Verifie le script de lancement"""
    print("\n[3] AUDIT SCRIPT LANCEMENT")
    print("-"*60)

    launch_path = Path("LAUNCH/launch_production_CLEAN_v2.py")
    check(launch_path.exists(),
          "launch_production_CLEAN_v2.py existe",
          "launch_production_CLEAN_v2.py MANQUANT!")

    if launch_path.exists():
        content = launch_path.read_text(encoding='utf-8')

        # Verifier test_mode=False
        check('test_mode=False' in content or 'test_mode = False' in content,
              "SessionQualityMonitor test_mode=False OK",
              "SessionQualityMonitor test_mode=True (devrait etre False)!", True)

        # Verifier circuit_breaker
        check('circuit_breaker_enabled' in content,
              "Circuit Breaker configure OK",
              "Circuit Breaker non trouve!", True)

        # Verifier max_trades_per_day
        check("'ES': 50" in content or "'ES':50" in content,
              "max_trades_per_day ES=50 OK",
              "max_trades_per_day ES != 50", True)


def audit_data_availability():
    """Verifie la disponibilite des donnees"""
    print("\n[4] AUDIT DISPONIBILITE DONNEES")
    print("-"*60)

    data_dir = Path("DATA_SIERRA_CHART/DATA_2025/DECEMBRE")
    check(data_dir.exists(),
          "Dossier DATA DECEMBRE existe",
          "Dossier DATA DECEMBRE MANQUANT!")

    if data_dir.exists():
        dates = [d.name for d in data_dir.iterdir() if d.is_dir()]
        check(len(dates) >= 5,
              f"{len(dates)} jours de donnees disponibles",
              f"Seulement {len(dates)} jours de donnees")

        # Verifier 05/12
        dec05 = data_dir / "20251205"
        if dec05.exists():
            nq_ml = dec05 / "CHART_9" / "ML_READY"
            check(nq_ml.exists() and list(nq_ml.glob("*.jsonl")),
                  "NQ ML_READY 05/12 disponible",
                  "NQ ML_READY 05/12 MANQUANT!")


def audit_logs():
    """Verifie les logs"""
    print("\n[5] AUDIT LOGS")
    print("-"*60)

    logs_dir = Path("logs_advanced/trades")
    check(logs_dir.exists(),
          "Dossier logs trades existe",
          "Dossier logs trades MANQUANT!")

    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        check(len(log_files) >= 5,
              f"{len(log_files)} fichiers de logs",
              f"Seulement {len(log_files)} fichiers de logs")


def audit_coherence_values():
    """Verifie la coherence des valeurs entre fichiers"""
    print("\n[6] AUDIT COHERENCE INTER-FICHIERS")
    print("-"*60)

    try:
        from config.unified_thresholds import MIN_TOTAL_CONFIDENCE as UT_CONF
        from ml.ml_3layer_filter import ML3LayerFilter

        f = ML3LayerFilter()

        # Comparer les valeurs
        for symbol in ['ES', 'NQ']:
            ut_val = UT_CONF.get(symbol) if isinstance(UT_CONF, dict) else UT_CONF

            # Verifier si c'est un dict ou un float
            ml_conf = f.config.MIN_TOTAL_CONFIDENCE
            if isinstance(ml_conf, dict):
                ml_val = ml_conf.get(symbol)
            else:
                ml_val = ml_conf  # C'est un float

            if ml_val is not None and ut_val is not None:
                # Comparer (tolerance pour float)
                is_equal = abs(ut_val - ml_val) < 0.001 if isinstance(ml_val, float) else ut_val == ml_val
                check(is_equal,
                      f"{symbol} MIN_TOTAL_CONFIDENCE coherent ({ut_val})",
                      f"{symbol} MIN_TOTAL_CONFIDENCE INCOHERENT! unified={ut_val}, ml_filter={ml_val}")

    except Exception as e:
        WARNINGS.append(f"Verification coherence echouee: {e}")


def main():
    print("="*80)
    print("AUDIT DE COHERENCE DU SYSTEME MIA")
    print("="*80)

    # Changer vers le bon repertoire
    os.chdir(Path(__file__).parent.parent)

    audit_config_files()
    audit_ml_filter()
    audit_launch_script()
    audit_data_availability()
    audit_logs()
    audit_coherence_values()

    # Resume
    print("\n" + "="*80)
    print("RESUME DE L'AUDIT")
    print("="*80)

    print(f"\n   [OK] {len(OK)} checks passes")
    for item in OK:
        print(f"      - {item}")

    if WARNINGS:
        print(f"\n   [WARNING] {len(WARNINGS)} avertissements")
        for item in WARNINGS:
            print(f"      - {item}")

    if ERRORS:
        print(f"\n   [ERREUR] {len(ERRORS)} erreurs critiques")
        for item in ERRORS:
            print(f"      - {item}")

    # Verdict final
    print("\n" + "="*80)
    if not ERRORS:
        print("VERDICT: SYSTEME COHERENT ET STABLE")
    else:
        print("VERDICT: ERREURS DETECTEES - CORRIGER AVANT PRODUCTION!")
    print("="*80)


if __name__ == "__main__":
    main()
