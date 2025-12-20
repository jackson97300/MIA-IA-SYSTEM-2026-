"""
ml_ready_context_adapter.py

🔧 ADAPTER ML_READY → MODULES ELITE

Convertit les données ML_READY (Sierra Chart dumper) vers les formats
attendus par les modules Elite:
- RulesEngine context
- MarketContextAnalyzer (validation incluse)
- MenthorQDecisionEngine (TODO - Phase 2)

Version: 1.0
Date: 7 Novembre 2025
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def ml_ready_to_rules_context(ml_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    🔧 Convertit ML_READY → RulesEngine context format

    Args:
        ml_data: Données ML_READY du dumper Sierra Chart
        symbol: ES/NQ/RTY

    Returns:
        Dict compatible avec RulesEngine.evaluate_entry_rules()

    Format RulesEngine attendu:
    {
        'summary': {'atr': float, 'vix': float},
        'macro': {'vix': float},
        'main_bias': 'BULLISH'|'BEARISH'|'NEUTRAL',
        'bias_strength': float (-1.0 à +1.0),
        'orderflow_pressure': 'BUYING'|'SELLING'|'BALANCED',
        'proximity_alerts': List[str],
        'gamma_flip_detected': 'UP'|'DOWN'|None
    }
    """
    # 1. Summary (ATR, VIX)
    atr = ml_data.get('atr', 1.0)
    vix = ml_data.get('vix', 20.0)

    summary = {
        'atr': float(atr) if atr else 1.0,
        'vix': float(vix) if vix else 20.0
    }

    # 2. Macro (VIX)
    macro = {
        'vix': summary['vix']
    }

    # 3. Main Bias (depuis dealer_bias ou mia_bullish_score)
    main_bias = _extract_main_bias(ml_data)

    # 4. Bias Strength (depuis dealer_bias_strength ou calcul)
    bias_strength = _extract_bias_strength(ml_data)

    # 5. Orderflow Pressure (depuis orderflow_direction ou deltaPct)
    orderflow_pressure = _extract_orderflow_pressure(ml_data)

    # 6. Proximity Alerts (depuis proximity_alerts ou distance HVL/VWAP)
    proximity_alerts = _extract_proximity_alerts(ml_data, symbol)

    # 7. Gamma Flip (depuis gamma_flip ou changement net_gex)
    gamma_flip_detected = ml_data.get('gamma_flip', None)

    context = {
        'summary': summary,
        'macro': macro,
        'main_bias': main_bias,
        'bias_strength': bias_strength,
        'orderflow_pressure': orderflow_pressure,
        'proximity_alerts': proximity_alerts,
        'gamma_flip_detected': gamma_flip_detected
    }

    logger.debug(f"[{symbol}] ML_READY -> RulesEngine: bias={main_bias}, strength={bias_strength:.2f}, flow={orderflow_pressure}")

    return context


def _extract_main_bias(ml_data: Dict[str, Any]) -> str:
    """
    Extrait le bias principal depuis ML_READY

    Sources (par ordre de priorité):
    1. dealer_bias (directement)
    2. mia_bullish_score (calcul)
    3. d_vwap_atr (fallback)

    Returns:
        'BULLISH' | 'BEARISH' | 'NEUTRAL'
    """
    # 1. dealer_bias (si disponible)
    dealer_bias = ml_data.get('dealer_bias')
    if dealer_bias:
        if dealer_bias.upper() in ['BULLISH', 'BEARISH', 'NEUTRAL']:
            return dealer_bias.upper()

    # 2. mia_bullish_score (range -1 à +1)
    mia_score = ml_data.get('mia_bullish_score')
    if mia_score is not None:
        if mia_score > 0.3:
            return 'BULLISH'
        elif mia_score < -0.3:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    # 3. Fallback: d_vwap_atr
    d_vwap_atr = ml_data.get('d_vwap_atr', 0.0)
    if d_vwap_atr > 1.0:
        return 'BULLISH'
    elif d_vwap_atr < -1.0:
        return 'BEARISH'

    return 'NEUTRAL'


def _extract_bias_strength(ml_data: Dict[str, Any]) -> float:
    """
    Extrait la force du bias (-1.0 à +1.0)

    Sources:
    1. dealer_bias_strength (directement)
    2. mia_bullish_score (directement)
    3. Calcul manuel (d_vwap_atr + deltaPct)

    Returns:
        float entre -1.0 et +1.0
    """
    # 1. dealer_bias_strength
    bias_strength = ml_data.get('dealer_bias_strength')
    if bias_strength is not None:
        try:
            return max(-1.0, min(1.0, float(bias_strength)))
        except (ValueError, TypeError):
            pass

    # 2. mia_bullish_score
    mia_score = ml_data.get('mia_bullish_score')
    if mia_score is not None:
        try:
            return max(-1.0, min(1.0, float(mia_score)))
        except (ValueError, TypeError):
            pass

    # 3. Calcul manuel (d_vwap_atr 70% + deltaPct 30%)
    d_vwap_atr = ml_data.get('d_vwap_atr', 0.0)
    delta_pct = ml_data.get('deltaPct', 0.5)

    # Normaliser d_vwap_atr (typiquement -3 à +3)
    vwap_component = max(-1.0, min(1.0, d_vwap_atr / 3.0)) * 0.7

    # Normaliser deltaPct (0 à 1 → -1 à +1)
    delta_component = (delta_pct - 0.5) * 2.0 * 0.3

    return max(-1.0, min(1.0, vwap_component + delta_component))


def _extract_orderflow_pressure(ml_data: Dict[str, Any]) -> str:
    """
    Extrait la pression orderflow

    Sources:
    1. orderflow_direction (directement)
    2. deltaPct + cum_delta_session (calcul)

    Returns:
        'BUYING' | 'SELLING' | 'BALANCED'
    """
    # 1. orderflow_direction
    orderflow_dir = ml_data.get('orderflow_direction')
    if orderflow_dir:
        if orderflow_dir.upper() in ['BUYING', 'SELLING', 'BALANCED', 'NEUTRAL']:
            return 'BALANCED' if orderflow_dir.upper() == 'NEUTRAL' else orderflow_dir.upper()

    # 2. Calcul depuis deltaPct + cum_delta
    delta_pct = ml_data.get('deltaPct', 0.5)
    cum_delta = ml_data.get('cum_delta_session', 0)

    # Pression courante
    if delta_pct > 0.65:
        current = 'BUYING'
    elif delta_pct < 0.35:
        current = 'SELLING'
    else:
        current = 'BALANCED'

    # Confirmer avec cumul
    if cum_delta > 500:
        return 'BUYING'
    elif cum_delta < -500:
        return 'SELLING'
    else:
        return current


def _extract_proximity_alerts(ml_data: Dict[str, Any], symbol: str) -> List[str]:
    """
    Extrait les alertes de proximité

    Sources:
    1. proximity_alerts (directement)
    2. Calcul manuel (distance HVL, VWAP, GEX)

    Returns:
        Liste d'alertes textuelles
    """
    alerts = []

    # 1. Si déjà fourni dans ML_READY
    existing_alerts = ml_data.get('proximity_alerts', [])
    if existing_alerts:
        return existing_alerts

    # 2. Calcul manuel
    mid = ml_data.get('mid', 0)
    atr = ml_data.get('atr', 1.0)

    if mid == 0 or atr == 0:
        return []

    # HVL proximity
    hvl = ml_data.get('hvl')
    if hvl and abs(mid - hvl) < 0.5 * atr:
        alerts.append(f"TRES PROCHE DE HVL ({hvl:.2f})")

    # VWAP proximity
    vwap = ml_data.get('vwap')
    if vwap and abs(mid - vwap) < 0.5 * atr:
        alerts.append(f"TRES PROCHE DE VWAP ({vwap:.2f})")

    # Value Area proximity
    vva = ml_data.get('vva', {})
    if isinstance(vva, dict):
        vah = vva.get('vah')
        val = vva.get('val')

        if vah and abs(mid - vah) < 0.4 * atr:
            alerts.append(f"Test VAH ({vah:.2f})")

        if val and abs(mid - val) < 0.4 * atr:
            alerts.append(f"Test VAL ({val:.2f})")

    # GEX walls proximity
    menthor_dist = ml_data.get('menthor_distances', {})
    if isinstance(menthor_dist, dict):
        near_gex_up = menthor_dist.get('near_gex_up')
        near_gex_dn = menthor_dist.get('near_gex_dn')

        if near_gex_up is not None and abs(near_gex_up) < 1.0 * atr:
            alerts.append(f"GEX Wall au-dessus (~{abs(near_gex_up):.2f} pts)")

        if near_gex_dn is not None and abs(near_gex_dn) < 1.0 * atr:
            alerts.append(f"GEX Wall en-dessous (~{abs(near_gex_dn):.2f} pts)")

    return alerts


def validate_ml_ready_for_rules(ml_data: Dict[str, Any]) -> tuple[bool, str]:
    """
    🔧 Valide que ML_READY contient les données minimales pour RulesEngine

    Args:
        ml_data: Données ML_READY

    Returns:
        (is_valid, error_message)
    """
    required = ['mid', 'atr']

    for field in required:
        if field not in ml_data or ml_data[field] is None:
            return False, f"Champ requis manquant: {field}"

    # Vérifier valeurs cohérentes
    mid = ml_data.get('mid', 0)
    if mid <= 0:
        return False, f"Prix mid invalide: {mid}"

    atr = ml_data.get('atr', 0)
    if atr <= 0:
        return False, f"ATR invalide: {atr}"

    return True, "OK"


# ═══════════════════════════════════════════════════════════════
# 🧪 TESTS RAPIDES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Test data
    test_ml_data = {
        'mid': 6050.25,
        'atr': 12.5,
        'vix': 18.2,
        'dealer_bias': 'BULLISH',
        'dealer_bias_strength': 0.65,
        'orderflow_direction': 'BUYING',
        'deltaPct': 0.72,
        'cum_delta_session': 1250,
        'd_vwap_atr': 1.5,
        'hvl': 6045.0,
        'vwap': 6048.0,
        'vva': {'vah': 6055.0, 'val': 6040.0},
        'menthor_distances': {
            'near_gex_up': 8.5,
            'near_gex_dn': -12.0
        },
        'gamma_flip': None
    }

    print("=" * 60)
    print("TEST ML_READY -> RulesEngine")
    print("=" * 60)

    # Test validation
    is_valid, msg = validate_ml_ready_for_rules(test_ml_data)
    print(f"\nValidation: {is_valid} ({msg})")

    # Test conversion
    context = ml_ready_to_rules_context(test_ml_data, "ES")

    print("\nContext genere:")
    for key, value in context.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("TEST TERMINE")
    print("=" * 60)
