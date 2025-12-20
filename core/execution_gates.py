"""
Module: execution_gates.py
Description: Gates d'exécution AVANT interrogation du ML
             Filtre les conditions de marché in-tradables

Principe:
- Le ML doit PRÉDIRE, pas FILTRER
- Les gates sont des conditions DURES qui rendent un trade impossible
- Si un gate échoue → REJECT immédiat sans interroger le ML

Auteur: MIA_IA_SYSTEM
Date: 5 Novembre 2025
Version: 1.0 - PATCH R9 GPT
"""

from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION DES GATES PAR SYMBOLE
# ═══════════════════════════════════════════════════════════════════

GATES_CONFIG = {
    "ES": {
        "max_spread_ticks": 2,
        "min_total_liquidity": 100,  # q_bq1 + q_aq1
        "max_atr_multiplier": 2.5,   # ATR > ATR_mean_20d * 2.5 → VOL_EXTREME
    },
    "NQ": {
        "max_spread_ticks": 2,
        "min_total_liquidity": 80,
        "max_atr_multiplier": 2.5,
    },
    "RTY": {
        "max_spread_ticks": 2,
        "min_total_liquidity": 50,
        "max_atr_multiplier": 2.5,
    },
    "GC": {
        "max_spread_ticks": 3,  # GC peut avoir spread plus large
        "min_total_liquidity": 40,
        "max_atr_multiplier": 2.5,
    },
    "CL": {
        "max_spread_ticks": 2,
        "min_total_liquidity": 60,
        "max_atr_multiplier": 2.5,
    },
}

# Config par défaut pour symboles non définis
DEFAULT_GATES = {
    "max_spread_ticks": 2,
    "min_total_liquidity": 50,
    "max_atr_multiplier": 2.5,
}


# ═══════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════

def check_execution_gates(snapshot: Dict[str, Any], symbol: str = None) -> Tuple[bool, str]:
    """
    Vérifier les gates d'exécution AVANT d'interroger le ML

    Args:
        snapshot: Dict contenant les features du marché actuel
        symbol: Symbole du trade (ES, NQ, RTY, GC, CL)

    Returns:
        Tuple[bool, str]: (gate_ok, reason)
            - gate_ok: True si tous les gates passent, False sinon
            - reason: Code de la raison (ex: "SPREAD_TOO_WIDE", "GATES_OK")

    Exemples:
        >>> snapshot = {"spread_ticks": 1, "q_bq1": 120, "q_aq1": 100, "atr": 0.5}
        >>> check_execution_gates(snapshot, "ES")
        (True, "GATES_OK")

        >>> snapshot = {"spread_ticks": 3, "q_bq1": 50, "q_aq1": 40}
        >>> check_execution_gates(snapshot, "ES")
        (False, "SPREAD_TOO_WIDE")
    """

    # Récupérer config du symbole
    if symbol and symbol.upper() in GATES_CONFIG:
        config = GATES_CONFIG[symbol.upper()]
    else:
        config = DEFAULT_GATES
        if symbol:
            logger.warning(f"⚠️  Symbole {symbol} non défini, utilisation config par défaut")

    # ─────────────────────────────────────────────────────────────────
    # GATE 1: SPREAD
    # ─────────────────────────────────────────────────────────────────
    spread_ticks = snapshot.get('spread_ticks', 999)
    if spread_ticks > config['max_spread_ticks']:
        logger.info(f"❌ GATE 1 FAILED: SPREAD_TOO_WIDE ({spread_ticks} > {config['max_spread_ticks']})")
        return False, "SPREAD_TOO_WIDE"

    # ─────────────────────────────────────────────────────────────────
    # GATE 2: LIQUIDITÉ DOM
    # ─────────────────────────────────────────────────────────────────
    q_bq1 = snapshot.get('q_bq1', 0)
    q_aq1 = snapshot.get('q_aq1', 0)
    total_liq = q_bq1 + q_aq1

    if total_liq < config['min_total_liquidity']:
        logger.info(f"❌ GATE 2 FAILED: DOM_TOO_THIN (total={total_liq} < {config['min_total_liquidity']})")
        return False, "DOM_TOO_THIN"

    # ─────────────────────────────────────────────────────────────────
    # GATE 3: VOLATILITÉ EXTRÊME
    # ─────────────────────────────────────────────────────────────────
    atr = snapshot.get('atr')
    atr_mean_20d = snapshot.get('atr_mean_20d')

    if atr is not None and atr_mean_20d is not None:
        if atr > atr_mean_20d * config['max_atr_multiplier']:
            logger.info(f"❌ GATE 3 FAILED: VOL_EXTREME (ATR={atr:.4f} > {atr_mean_20d:.4f} * {config['max_atr_multiplier']})")
            return False, "VOL_EXTREME"
    elif atr is None:
        logger.warning(f"⚠️  GATE 3 SKIPPED: ATR manquant dans snapshot")

    # ─────────────────────────────────────────────────────────────────
    # GATE 4: GAMMA FLIP CONTRE-SENS
    # ─────────────────────────────────────────────────────────────────
    setup_direction = snapshot.get('setup_direction', 'UNKNOWN').upper()
    gamma_flip_down = snapshot.get('gamma_flip_down', 0)
    gamma_flip_up = snapshot.get('gamma_flip_up', 0)

    if setup_direction == 'LONG' and gamma_flip_down > 0:
        logger.info(f"❌ GATE 4 FAILED: GAMMA_CONTRA_DOWN (LONG setup avec gamma_flip_down={gamma_flip_down})")
        return False, "GAMMA_CONTRA_DOWN"

    if setup_direction == 'SHORT' and gamma_flip_up > 0:
        logger.info(f"❌ GATE 4 FAILED: GAMMA_CONTRA_UP (SHORT setup avec gamma_flip_up={gamma_flip_up})")
        return False, "GAMMA_CONTRA_UP"

    # ─────────────────────────────────────────────────────────────────
    # GATE 5: DOM NEUTRALISÉ (Sécurité contre DOM corrompu)
    # ─────────────────────────────────────────────────────────────────
    dom_neutralized = snapshot.get('dom_neutralized', False)
    if dom_neutralized:
        logger.info(f"❌ GATE 5 FAILED: DOM_NEUTRALIZED (DOM corrompu détecté)")
        return False, "DOM_NEUTRALIZED"

    # ─────────────────────────────────────────────────────────────────
    # TOUS LES GATES PASSÉS
    # ─────────────────────────────────────────────────────────────────

    # Bonus: Spread 1-tick (à utiliser pour ajuster seuil ML)
    is_1tick = snapshot.get('is_1tick_spread', False)
    reason = "GATES_OK +1TICK" if is_1tick else "GATES_OK"

    logger.info(f"✅ ALL GATES PASSED: {reason}")
    return True, reason


# ═══════════════════════════════════════════════════════════════════
# UTILITAIRE: DIAGNOSTIC COMPLET
# ═══════════════════════════════════════════════════════════════════

def diagnostic_gates(snapshot: Dict[str, Any], symbol: str = None) -> Dict[str, Any]:
    """
    Diagnostic complet des gates (pour debugging)

    Args:
        snapshot: Dict contenant les features
        symbol: Symbole du trade

    Returns:
        Dict avec status de chaque gate
    """

    config = GATES_CONFIG.get(symbol.upper() if symbol else "ES", DEFAULT_GATES)

    spread_ticks = snapshot.get('spread_ticks', 999)
    q_bq1 = snapshot.get('q_bq1', 0)
    q_aq1 = snapshot.get('q_aq1', 0)
    total_liq = q_bq1 + q_aq1
    atr = snapshot.get('atr')
    atr_mean_20d = snapshot.get('atr_mean_20d')
    setup_direction = snapshot.get('setup_direction', 'UNKNOWN').upper()
    gamma_flip_down = snapshot.get('gamma_flip_down', 0)
    gamma_flip_up = snapshot.get('gamma_flip_up', 0)
    dom_neutralized = snapshot.get('dom_neutralized', False)
    is_1tick = snapshot.get('is_1tick_spread', False)

    # Calcul vol ratio
    vol_ratio = None
    if atr is not None and atr_mean_20d is not None and atr_mean_20d > 0:
        vol_ratio = atr / atr_mean_20d

    return {
        "symbol": symbol,
        "gates": {
            "gate_1_spread": {
                "status": "PASS" if spread_ticks <= config['max_spread_ticks'] else "FAIL",
                "value": spread_ticks,
                "threshold": config['max_spread_ticks']
            },
            "gate_2_liquidity": {
                "status": "PASS" if total_liq >= config['min_total_liquidity'] else "FAIL",
                "value": total_liq,
                "threshold": config['min_total_liquidity']
            },
            "gate_3_volatility": {
                "status": "PASS" if vol_ratio is None or vol_ratio <= config['max_atr_multiplier'] else "FAIL",
                "value": vol_ratio,
                "threshold": config['max_atr_multiplier']
            },
            "gate_4_gamma": {
                "status": "PASS" if not ((setup_direction == 'LONG' and gamma_flip_down > 0) or
                                         (setup_direction == 'SHORT' and gamma_flip_up > 0)) else "FAIL",
                "setup_direction": setup_direction,
                "gamma_flip_down": gamma_flip_down,
                "gamma_flip_up": gamma_flip_up
            },
            "gate_5_dom": {
                "status": "PASS" if not dom_neutralized else "FAIL",
                "dom_neutralized": dom_neutralized
            }
        },
        "bonuses": {
            "spread_1tick": is_1tick
        },
        "overall": "PASS" if spread_ticks <= config['max_spread_ticks'] and \
                             total_liq >= config['min_total_liquidity'] and \
                             (vol_ratio is None or vol_ratio <= config['max_atr_multiplier']) and \
                             not ((setup_direction == 'LONG' and gamma_flip_down > 0) or
                                  (setup_direction == 'SHORT' and gamma_flip_up > 0)) and \
                             not dom_neutralized else "FAIL"
    }


# ═══════════════════════════════════════════════════════════════════
# EXEMPLE D'USAGE EN PRODUCTION
# ═══════════════════════════════════════════════════════════════════

"""
EXEMPLE D'INTÉGRATION DANS LE SIGNAL HANDLER:

from core.execution_gates import check_execution_gates

def handle_signal(signal_data):
    # Capturer snapshot marché
    snapshot = capture_market_snapshot()

    # ÉTAPE 1: Gates durs (AVANT ML)
    gate_ok, gate_reason = check_execution_gates(snapshot, signal_data['symbol'])
    if not gate_ok:
        logger.info(f"❌ REJECT: {gate_reason}")
        return {
            "decision": "REJECT",
            "reason": gate_reason,
            "stage": "GATES"
        }

    # ÉTAPE 2: Préparer features pour ML
    features_ordered = [snapshot.get(f, np.nan) for f in manifest['feature_order']]

    # ÉTAPE 3: Interroger ML
    proba_ml = model.predict_proba([features_ordered])[0, 1]
    seuil = compute_dynamic_threshold(snapshot)

    # ÉTAPE 4: Décision finale
    if proba_ml >= seuil:
        logger.info(f"✅ ACCEPT: proba={proba_ml:.3f} >= {seuil:.3f} | {gate_reason}")
        return {
            "decision": "ACCEPT",
            "proba": proba_ml,
            "seuil": seuil,
            "reason": gate_reason
        }
    else:
        logger.info(f"❌ REJECT: proba={proba_ml:.3f} < {seuil:.3f}")
        return {
            "decision": "REJECT",
            "proba": proba_ml,
            "seuil": seuil,
            "stage": "ML"
        }
"""


if __name__ == "__main__":
    # Test unitaire simple
    logging.basicConfig(level=logging.INFO)

    # Test 1: Snapshot valide
    print("\n" + "="*70)
    print("TEST 1: Snapshot valide")
    print("="*70)
    snapshot_ok = {
        "spread_ticks": 1,
        "q_bq1": 120,
        "q_aq1": 100,
        "atr": 0.5,
        "atr_mean_20d": 0.6,
        "setup_direction": "LONG",
        "gamma_flip_down": 0,
        "gamma_flip_up": 0,
        "dom_neutralized": False,
        "is_1tick_spread": True
    }
    result, reason = check_execution_gates(snapshot_ok, "ES")
    print(f"Résultat: {result}, Raison: {reason}")
    assert result == True
    assert reason == "GATES_OK +1TICK"

    # Test 2: Spread trop large
    print("\n" + "="*70)
    print("TEST 2: Spread trop large")
    print("="*70)
    snapshot_bad_spread = {
        "spread_ticks": 3,
        "q_bq1": 120,
        "q_aq1": 100
    }
    result, reason = check_execution_gates(snapshot_bad_spread, "ES")
    print(f"Résultat: {result}, Raison: {reason}")
    assert result == False
    assert reason == "SPREAD_TOO_WIDE"

    # Test 3: DOM trop fin
    print("\n" + "="*70)
    print("TEST 3: DOM trop fin")
    print("="*70)
    snapshot_bad_dom = {
        "spread_ticks": 1,
        "q_bq1": 20,
        "q_aq1": 25
    }
    result, reason = check_execution_gates(snapshot_bad_dom, "ES")
    print(f"Résultat: {result}, Raison: {reason}")
    assert result == False
    assert reason == "DOM_TOO_THIN"

    # Test 4: Gamma flip contre-sens
    print("\n" + "="*70)
    print("TEST 4: Gamma flip contre-sens")
    print("="*70)
    snapshot_gamma_contra = {
        "spread_ticks": 1,
        "q_bq1": 120,
        "q_aq1": 100,
        "setup_direction": "LONG",
        "gamma_flip_down": 1
    }
    result, reason = check_execution_gates(snapshot_gamma_contra, "ES")
    print(f"Résultat: {result}, Raison: {reason}")
    assert result == False
    assert reason == "GAMMA_CONTRA_DOWN"

    print("\n✅ Tous les tests passés !")

