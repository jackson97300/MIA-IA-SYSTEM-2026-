"""
MIA_IA_SYSTEM - ML_READY Data Helpers
Helper functions pour extraire/dériver des données du ML_READY

Version: 1.0 - GPT v3.0 Improvements
Date: 2 Novembre 2025
"""

from typing import Dict, Any, Optional


def extract_put_wall(ml_data: Dict[str, Any]) -> Optional[float]:
    """
    Extrait le mur PUT le plus proche sous le prix actuel

    Cherche dans les niveaux GEX (gex_1 à gex_10) pour trouver
    le niveau le plus proche sous le prix, qui représente
    le mur PUT/support majeur.

    Args:
        ml_data: Dictionnaire ML_READY

    Returns:
        Prix du mur PUT ou None si non trouvé
    """
    price = ml_data.get('mid')
    if not price:
        return None

    # Extraire tous les niveaux GEX disponibles
    gex_levels = []
    for i in range(1, 11):
        gex = ml_data.get(f'gex_{i}')
        if gex:
            gex_levels.append(gex)

    # Filtrer ceux SOUS le prix (murs PUT)
    put_candidates = [g for g in gex_levels if g < price]

    if put_candidates:
        # Retourner le plus proche (maximum des valeurs sous le prix)
        return max(put_candidates)

    # Fallback: utiliser put_support si disponible
    return ml_data.get('put_support')


def extract_call_wall(ml_data: Dict[str, Any]) -> Optional[float]:
    """
    Extrait le mur CALL le plus proche au-dessus du prix actuel

    Utilise d'abord 'next_wall' si disponible et de type CALL,
    sinon cherche dans les niveaux GEX.

    Args:
        ml_data: Dictionnaire ML_READY

    Returns:
        Prix du mur CALL ou None si non trouvé
    """
    # Priorité: next_wall si c'est un CALL
    next_wall = ml_data.get('next_wall', {})
    if isinstance(next_wall, dict) and next_wall.get('side') == 'call':
        return next_wall.get('price')

    # Sinon chercher dans GEX
    price = ml_data.get('mid')
    if not price:
        return None

    gex_levels = []
    for i in range(1, 11):
        gex = ml_data.get(f'gex_{i}')
        if gex:
            gex_levels.append(gex)

    # Filtrer ceux AU-DESSUS du prix (murs CALL)
    call_candidates = [g for g in gex_levels if g > price]

    if call_candidates:
        # Retourner le plus proche (minimum des valeurs au-dessus du prix)
        return min(call_candidates)

    # Fallback: utiliser call_resistance si disponible
    return ml_data.get('call_resistance')


def calculate_delta_ratio(ml_data: Dict[str, Any]) -> float:
    """
    Calcule le delta ratio (bidPct - askPct)

    Positif = pression acheteuse
    Négatif = pression vendeuse

    Args:
        ml_data: Dictionnaire ML_READY

    Returns:
        Delta ratio [-1.0, +1.0]
    """
    bid_pct = ml_data.get('bidPct', 0.5)
    ask_pct = ml_data.get('askPct', 0.5)

    delta_ratio = bid_pct - ask_pct

    # Clamp pour sécurité
    return max(-1.0, min(1.0, delta_ratio))


def extract_blind_spot_closest(ml_data: Dict[str, Any]) -> Optional[float]:
    """
    Trouve le blind spot le plus proche du prix actuel

    Args:
        ml_data: Dictionnaire ML_READY

    Returns:
        Prix du blind spot le plus proche ou None
    """
    price = ml_data.get('mid')
    if not price:
        return None

    # Extraire tous les blind spots
    blind_spots = []
    for i in range(9):  # blind_spot_0 à blind_spot_8
        bs = ml_data.get(f'blind_spot_{i}')
        if bs:
            blind_spots.append(bs)

    if not blind_spots:
        return None

    # Trouver le plus proche
    distances = [(abs(bs - price), bs) for bs in blind_spots]
    distances.sort()

    return distances[0][1] if distances else None


def get_corridor_info(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait toutes les infos du corridor GEX en un seul appel

    Returns:
        Dict avec call_wall, put_wall, in_corridor, headroom_long_pct, headroom_short_pct
    """
    price = ml_data.get('mid')
    call_wall = extract_call_wall(ml_data)
    put_wall = extract_put_wall(ml_data)

    result = {
        'price': price,
        'call_wall': call_wall,
        'put_wall': put_wall,
        'in_corridor': False,
        'headroom_long_pct': None,
        'headroom_short_pct': None
    }

    if price and call_wall and put_wall:
        result['in_corridor'] = put_wall <= price <= call_wall
        result['headroom_long_pct'] = (call_wall - price) / price
        result['headroom_short_pct'] = (price - put_wall) / price

    return result


if __name__ == "__main__":
    # Test avec données réelles
    test_data = {
        'mid': 6882.13,
        'gex_1': 6900.00,
        'gex_2': 6825.00,
        'gex_3': 6870.00,
        'gex_4': 6890.00,
        'gex_5': 6860.00,
        'next_wall': {
            'price': 6890.00,
            'side': 'call',
            'dist_pts': 7.88
        },
        'bidPct': 0.485164,
        'askPct': 0.514836,
        'blind_spot_4': 6881.07
    }

    print("=== ML_READY HELPERS TEST ===")
    print(f"Prix: {test_data['mid']}")
    print(f"Call Wall: {extract_call_wall(test_data)}")
    print(f"Put Wall: {extract_put_wall(test_data)}")
    print(f"Delta Ratio: {calculate_delta_ratio(test_data):.4f}")
    print(f"Blind Spot Closest: {extract_blind_spot_closest(test_data)}")
    print(f"\nCorridor Info: {get_corridor_info(test_data)}")




