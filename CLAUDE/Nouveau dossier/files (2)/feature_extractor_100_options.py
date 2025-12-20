"""
🎯 FEATURE EXTRACTOR - 100 FEATURES EDITION OPTIONS
Version: 2.0
Date: 18 Nov 2025

Extraction complète de 100 features avec focus massif sur Options/GEX.
Aligné avec intuition: Plus de niveaux = Meilleure prédiction
"""

import numpy as np
from typing import Dict, List, Tuple


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Division sécurisée."""
    if b == 0 or np.isnan(b) or np.isinf(b):
        return default
    result = a / b
    return result if not (np.isnan(result) or np.isinf(result)) else default


def count_levels_within(price: float, levels: List[float], threshold_ticks: int) -> int:
    """
    Compte combien de niveaux sont dans un rayon donné.
    """
    tick_size = 0.25
    threshold = threshold_ticks * tick_size
    return sum(1 for level in levels if level > 0 and abs(price - level) < threshold)


def check_near_level(price: float, levels: List[float], threshold_ticks: int) -> int:
    """
    Vérifie si un prix est proche d'au moins un niveau.
    Returns: 1 si proche, 0 sinon
    """
    tick_size = 0.25
    threshold = threshold_ticks * tick_size
    
    for level in levels:
        if level > 0 and abs(price - level) < threshold:
            return 1
    return 0


# ═══════════════════════════════════════════════════════════════
# TIER 1: OPTIONS/GEX COMPLET (50 features)
# ═══════════════════════════════════════════════════════════════

def extract_options_complete(snapshot: dict, signal: dict = None) -> dict:
    """
    Extrait les 50 features Options/GEX complètes.
    """
    features = {}
    
    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 5.0)
    tick_size = 0.25
    
    # ─────────────────────────────────────────────────────────
    # 1.1 HVL & Proximity (5 features)
    # ─────────────────────────────────────────────────────────
    
    hvl = snapshot.get('hvl', 0)
    
    features['hvl'] = hvl
    features['d_hvl_ticks'] = abs(mid - hvl) / tick_size if hvl > 0 else 9999
    features['dist_hvl_atr'] = safe_divide(abs(mid - hvl), atr, default=999)
    features['hvl_proximity_pct'] = safe_divide(abs(mid - hvl), mid, default=1.0) * 100
    features['in_hvl_zone'] = 1 if (hvl > 0 and abs(mid - hvl) < 10 * tick_size) else 0
    
    # ─────────────────────────────────────────────────────────
    # 1.2 GEX Walls COMPLETS (15 features)
    # ─────────────────────────────────────────────────────────
    
    # Les 10 niveaux GEX bruts
    gex_levels = []
    for i in range(1, 11):
        gex = snapshot.get(f'gex_{i}', 0)
        features[f'gex_{i}'] = gex
        if gex > 0:
            gex_levels.append(gex)
    
    # Distances calculées
    if gex_levels:
        gex_distances = sorted([abs(mid - g) / tick_size for g in gex_levels])
        
        features['dist_nearest_gex_ticks'] = gex_distances[0]
        features['dist_nearest_gex_atr'] = safe_divide(gex_distances[0] * tick_size, atr, default=999)
        features['dist_2nd_nearest_gex'] = gex_distances[1] if len(gex_distances) > 1 else 9999
        features['dist_3rd_nearest_gex'] = gex_distances[2] if len(gex_distances) > 2 else 9999
    else:
        features['dist_nearest_gex_ticks'] = 9999
        features['dist_nearest_gex_atr'] = 999
        features['dist_2nd_nearest_gex'] = 9999
        features['dist_3rd_nearest_gex'] = 9999
    
    # Confluence GEX
    features['num_gex_within_20ticks'] = count_levels_within(mid, gex_levels, 20)
    
    # ─────────────────────────────────────────────────────────
    # 1.3 Call/Put Walls (8 features)
    # ─────────────────────────────────────────────────────────
    
    call_wall = snapshot.get('call_resistance', 0)
    put_wall = snapshot.get('put_support', 0)
    
    features['call_resistance'] = call_wall
    features['put_support'] = put_wall
    
    features['dist_call_wall_ticks'] = abs(mid - call_wall) / tick_size if call_wall > 0 else 9999
    features['dist_call_wall_atr'] = safe_divide(abs(mid - call_wall), atr, default=999)
    features['dist_put_wall_ticks'] = abs(mid - put_wall) / tick_size if put_wall > 0 else 9999
    features['dist_put_wall_atr'] = safe_divide(abs(mid - put_wall), atr, default=999)
    
    # Entre les murs?
    if call_wall > 0 and put_wall > 0:
        features['between_call_put'] = 1 if put_wall < mid < call_wall else 0
        features['distance_to_walls_ratio'] = safe_divide(
            features['dist_call_wall_ticks'],
            features['dist_put_wall_ticks'],
            default=1.0
        )
    else:
        features['between_call_put'] = 0
        features['distance_to_walls_ratio'] = 1.0
    
    # ─────────────────────────────────────────────────────────
    # 1.4 Blind Spots COMPLETS (13 features)
    # ─────────────────────────────────────────────────────────
    
    blind_spots = []
    for i in range(9):
        bs = snapshot.get(f'blind_spot_{i}', 0)
        features[f'blind_spot_{i}'] = bs
        if bs > 0:
            blind_spots.append(bs)
    
    # Distances blind spots
    if blind_spots:
        blind_distances = sorted([abs(mid - bs) / tick_size for bs in blind_spots])
        
        features['dist_nearest_blind_spot'] = blind_distances[0]
        features['dist_2nd_nearest_blind_spot'] = blind_distances[1] if len(blind_distances) > 1 else 9999
    else:
        features['dist_nearest_blind_spot'] = 9999
        features['dist_2nd_nearest_blind_spot'] = 9999
    
    # Confluence blind spots
    features['num_blind_spots_within_30ticks'] = count_levels_within(mid, blind_spots, 30)
    features['blind_spot_confluence'] = snapshot.get('blind_spot_confluence', 0)
    
    # ─────────────────────────────────────────────────────────
    # 1.5 Gamma Position & Confluence (9 features)
    # ─────────────────────────────────────────────────────────
    
    # Gamma side
    gamma_side_str = snapshot.get('gamma_side', 'below')
    features['gamma_side'] = 1 if gamma_side_str == 'above' else 0
    
    gamma_wall = snapshot.get('gamma_wall_level', 0)
    features['gamma_wall_level'] = gamma_wall
    features['dist_gamma_wall_ticks'] = abs(mid - gamma_wall) / tick_size if gamma_wall > 0 else 9999
    
    # Confluence avec gamma
    features['gamma_call_confluence'] = snapshot.get('gamma_call_confluence', 0)
    features['gamma_put_confluence'] = snapshot.get('gamma_put_confluence', 0)
    
    # Blind spot + GEX confluence
    blind_gex_aligned = (
        features['dist_nearest_blind_spot'] < 20 and
        features['dist_nearest_gex_ticks'] < 15
    )
    features['blind_spot_gex_confluence'] = 1 if blind_gex_aligned else 0
    
    # Triple confluence (HVL + GEX + Blind spot)
    hvl_close = features['d_hvl_ticks'] < 10
    gex_close = features['dist_nearest_gex_ticks'] < 10
    blind_close = features['dist_nearest_blind_spot'] < 20
    features['triple_confluence'] = 1 if (hvl_close and gex_close and blind_close) else 0
    
    # Scores globaux
    features['confluence_strength'] = snapshot.get('confluence_strength', 0)
    features['confluence_density'] = snapshot.get('confluence_density', 0)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 2: ORDERFLOW DOM PROFOND (20 features)
# ═══════════════════════════════════════════════════════════════

def extract_orderflow_deep(snapshot: dict) -> dict:
    """
    Extrait les 20 features OrderFlow DOM profondes.
    """
    features = {}
    
    dom_features = snapshot.get('dom_features', {})
    
    # ─────────────────────────────────────────────────────────
    # 2.1 Depth & Imbalances (8 features)
    # ─────────────────────────────────────────────────────────
    
    depth_bid = dom_features.get('depth_bid', 0)
    depth_ask = dom_features.get('depth_ask', 0)
    
    features['depth_bid'] = depth_bid
    features['depth_ask'] = depth_ask
    features['depth_total'] = depth_bid + depth_ask
    
    features['depth_imbalance'] = snapshot.get('depth_imbalance', 0)
    features['depth_imbalance_ratio'] = safe_divide(depth_bid, depth_ask, default=1.0)
    
    features['imbalance_1_3'] = dom_features.get('imbalance_1_3', 0)
    features['imbalance_4_5'] = dom_features.get('imbalance_4_5', 0)  # Si disponible
    features['imbalance_6_10'] = dom_features.get('imbalance_6_10', 0)
    
    # ─────────────────────────────────────────────────────────
    # 2.2 DOM Slopes (8 features)
    # ─────────────────────────────────────────────────────────
    
    slope_bid = dom_features.get('slope_bid_1_3', 0)
    slope_ask = dom_features.get('slope_ask_1_3', 0)
    slope_bid_n = dom_features.get('slope_bid_1_3_n', 0)
    slope_ask_n = dom_features.get('slope_ask_1_3_n', 0)
    
    features['slope_bid_1_3'] = slope_bid
    features['slope_ask_1_3'] = slope_ask
    features['slope_bid_1_3_n'] = slope_bid_n
    features['slope_ask_1_3_n'] = slope_ask_n
    
    # Ratios
    features['dom_slope_ratio'] = safe_divide(slope_bid, slope_ask, default=1.0)
    features['slope_asymmetry'] = abs(slope_bid_n - slope_ask_n)
    
    # Stacked imbalances
    features['stacked_imbalance_bid_rows'] = snapshot.get('stacked_imbalance_bid_rows', 0)
    features['stacked_imbalance_ask_rows'] = snapshot.get('stacked_imbalance_ask_rows', 0)
    
    # ─────────────────────────────────────────────────────────
    # 2.3 Pressure & Center (4 features)
    # ─────────────────────────────────────────────────────────
    
    features['pressure_strength'] = snapshot.get('pressure_strength', 0)
    features['pressure_strength_depth'] = snapshot.get('pressure_strength_depth', 0)
    features['pressure_strength_atr'] = snapshot.get('pressure_strength_atr', 0)
    features['ob_center'] = snapshot.get('ob_center', 0.5)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 3: VOLUME/DELTA (12 features)
# ═══════════════════════════════════════════════════════════════

def extract_volume_delta(snapshot: dict) -> dict:
    """
    Extrait les 12 features Volume/Delta.
    """
    features = {}
    
    # ─────────────────────────────────────────────────────────
    # 3.1 Delta Core (6 features)
    # ─────────────────────────────────────────────────────────
    
    delta = snapshot.get('delta', 0)
    volume = snapshot.get('volume', 1)
    
    features['delta'] = delta
    features['cum_delta_session'] = snapshot.get('cum_delta_session', 0)
    features['cum_delta_day'] = snapshot.get('cum_delta_day', 0)
    features['deltaPct'] = snapshot.get('deltaPct', 0)
    features['delta_intensity'] = safe_divide(abs(delta), volume, default=0)
    features['delta_burst'] = snapshot.get('delta_burst', 0)
    
    # ─────────────────────────────────────────────────────────
    # 3.2 Volume Analysis (6 features)
    # ─────────────────────────────────────────────────────────
    
    features['volume'] = volume
    features['bidvol'] = snapshot.get('bidvol', 0)
    features['askvol'] = snapshot.get('askvol', 0)
    features['bidPct'] = snapshot.get('bidPct', 0.5)
    features['askPct'] = snapshot.get('askPct', 0.5)
    features['smart_money_flow'] = snapshot.get('smart_money_flow', 0)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 4: CONTEXT TRADING (10 features)
# ═══════════════════════════════════════════════════════════════

def extract_context(snapshot: dict) -> dict:
    """
    Extrait les 10 features de contexte.
    """
    features = {}
    
    # ─────────────────────────────────────────────────────────
    # 4.1 VWAP Position (4 features)
    # ─────────────────────────────────────────────────────────
    
    features['d_vwap_ticks'] = snapshot.get('d_vwap_ticks', 0)
    features['d_vwap_atr'] = snapshot.get('d_vwap_atr', 0)
    features['d_pvwap_ticks'] = snapshot.get('d_pvwap_ticks', 0)
    features['d_vpoc_ticks'] = snapshot.get('d_vpoc_ticks', 0)
    
    # ─────────────────────────────────────────────────────────
    # 4.2 Volatility & Momentum (4 features)
    # ─────────────────────────────────────────────────────────
    
    features['atr'] = snapshot.get('atr', 0)
    features['atr_ratio'] = snapshot.get('atr_ratio', 0)
    features['volatility_regime'] = snapshot.get('volatility_regime', 0)
    features['tick_momentum'] = snapshot.get('tick_momentum', 0)
    
    # ─────────────────────────────────────────────────────────
    # 4.3 Session Structure (2 features)
    # ─────────────────────────────────────────────────────────
    
    features['session_progress'] = snapshot.get('session_progress', 0)
    features['position_in_range'] = snapshot.get('position_in_range', 0)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 5: SIGNAL CHARACTERISTICS (8 features)
# ═══════════════════════════════════════════════════════════════

def extract_signal_analysis(snapshot: dict, signal: dict) -> dict:
    """
    Extrait les 8 features spécifiques au signal.
    CRITIQUE pour détecter stop hunts!
    """
    features = {}
    
    if not signal:
        # Return zeros
        return {f'signal_{i}': 0 for i in range(8)}
    
    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 5.0)
    tick_size = 0.25
    
    direction = signal.get('direction', 'LONG')
    entry = signal.get('entry_price', mid)
    sl = signal.get('sl_price', entry - 15*tick_size if direction=='LONG' else entry + 15*tick_size)
    tp = signal.get('tp_price', entry + 15*tick_size if direction=='LONG' else entry - 15*tick_size)
    
    # ─────────────────────────────────────────────────────────
    # 5.1 SL/TP Analysis (8 features)
    # ─────────────────────────────────────────────────────────
    
    # Distances
    sl_distance = abs(entry - sl)
    tp_distance = abs(entry - tp)
    
    features['sl_distance_ticks'] = sl_distance / tick_size
    features['sl_distance_atr'] = safe_divide(sl_distance, atr, default=0)
    features['tp_distance_ticks'] = tp_distance / tick_size
    features['risk_reward_ratio'] = safe_divide(tp_distance, sl_distance, default=1.0)
    
    # Position SL vs niveaux (CRITIQUE!)
    hvl = snapshot.get('hvl', 0)
    gex_levels = [snapshot.get(f'gex_{i}', 0) for i in range(1, 11)]
    blind_spots = [snapshot.get(f'blind_spot_{i}', 0) for i in range(9)]
    
    features['sl_near_hvl'] = 1 if (hvl > 0 and abs(sl - hvl) < 5 * tick_size) else 0
    features['sl_near_gex'] = check_near_level(sl, gex_levels, 5)
    features['sl_near_blind_spot'] = check_near_level(sl, blind_spots, 10)
    
    # SL en zone de confluence (DANGER MAXIMUM!)
    # Si 3+ niveaux proches du SL = stop hunt GARANTI
    levels_near_sl = []
    if hvl > 0 and abs(sl - hvl) < 10 * tick_size:
        levels_near_sl.append('hvl')
    
    for gex in gex_levels:
        if gex > 0 and abs(sl - gex) < 10 * tick_size:
            levels_near_sl.append('gex')
            break  # Compter comme 1 seul
    
    for bs in blind_spots:
        if bs > 0 and abs(sl - bs) < 15 * tick_size:
            levels_near_sl.append('blind_spot')
            break  # Compter comme 1 seul
    
    features['sl_in_confluence_zone'] = 1 if len(levels_near_sl) >= 2 else 0
    
    return features


# ═══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE - 100 FEATURES
# ═══════════════════════════════════════════════════════════════

def extract_100_features(snapshot: dict, signal: dict = None) -> dict:
    """
    Extrait les 100 features complètes.
    
    Args:
        snapshot: ML_READY snapshot complet
        signal: Trading signal avec direction, entry, SL, TP
    
    Returns:
        Dict avec 100 features
    """
    features = {}
    
    # Tier 1: Options/GEX (50)
    features.update(extract_options_complete(snapshot, signal))
    
    # Tier 2: OrderFlow (20)
    features.update(extract_orderflow_deep(snapshot))
    
    # Tier 3: Volume/Delta (12)
    features.update(extract_volume_delta(snapshot))
    
    # Tier 4: Context (10)
    features.update(extract_context(snapshot))
    
    # Tier 5: Signal (8)
    if signal:
        features.update(extract_signal_analysis(snapshot, signal))
    else:
        # Placeholder si pas de signal
        for i in range(8):
            features[f'signal_{i}'] = 0
    
    return features


# ═══════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════

def validate_features(features: dict) -> Tuple[bool, str]:
    """
    Valide que toutes les features sont présentes et valides.
    
    Returns:
        (is_valid, error_message)
    """
    expected_count = 100
    actual_count = len(features)
    
    if actual_count != expected_count:
        return False, f"Expected {expected_count} features, got {actual_count}"
    
    # Check for NaN/Inf
    invalid_features = []
    for name, value in features.items():
        if np.isnan(value) or np.isinf(value):
            invalid_features.append(name)
    
    if invalid_features:
        return False, f"Invalid values in features: {invalid_features[:5]}"
    
    return True, "OK"


# ═══════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    
    # Exemple snapshot
    snapshot = {
        'mid': 24913.63,
        'hvl': 25140.00,
        'atr': 5.57,
        'call_resistance': 26000.00,
        'put_support': 24000.00,
        'gex_1': 25000.00,
        'gex_2': 24750.00,
        'gex_3': 25100.00,
        'gex_4': 25250.00,
        'gex_5': 24900.00,
        'gex_6': 24500.00,
        'gex_7': 24700.00,
        'gex_8': 24400.00,
        'gex_9': 24600.00,
        'gex_10': 25750.00,
        'blind_spot_0': 24738.51,
        'blind_spot_1': 26383.01,
        'blind_spot_2': 25448.95,
        'blind_spot_3': 25088.47,
        'blind_spot_4': 26725.83,
        'blind_spot_5': 25825.88,
        'blind_spot_6': 25196.65,
        'blind_spot_7': 24470.17,
        'blind_spot_8': 24706.29,
        'blind_spot_confluence': 0,
        'gamma_side': 'below',
        'gamma_wall_level': 26000.00,
        'depth_imbalance': 0.073,
        'dom_features': {
            'depth_bid': 22,
            'depth_ask': 19,
            'imbalance_1_3': -0.2,
            'imbalance_6_10': 0.058,
            'slope_bid_1_3': 0,
            'slope_ask_1_3': 2,
            'slope_bid_1_3_n': 0.0,
            'slope_ask_1_3_n': 20.0
        },
        'pressure_strength': 0.006,
        'd_vwap_ticks': 46.2,
        'session_progress': 0.002,
        'confluence_strength': 0.047,
        'deltaPct': -0.368,
        'delta': -7,
        'volume': 19,
        'bidvol': 6,
        'askvol': 13,
        'bidPct': 0.315,
        'askPct': 0.684,
        'cum_delta_session': 54,
        'cum_delta_day': 54,
        'smart_money_flow': 0.368,
        'tick_momentum': -0.5,
        'volatility_regime': 1,
        'atr_ratio': 22.28,
        'position_in_range': 39.17,
        'stacked_imbalance_bid_rows': 1,
        'stacked_imbalance_ask_rows': 1,
        'ob_center': 0.487,
        'pressure_strength_depth': 0.024,
        'pressure_strength_atr': 0.007,
        'd_vwap_atr': 2.073,
        'd_pvwap_ticks': -385,
        'd_vpoc_ticks': -2945,
        'delta_burst': 7,
        'confluence_density': 0,
    }
    
    signal = {
        'direction': 'LONG',
        'entry_price': 24913.63,
        'sl_price': 24898.63,
        'tp_price': 24928.63
    }
    
    # Extraire 100 features
    features = extract_100_features(snapshot, signal)
    
    # Valider
    is_valid, message = validate_features(features)
    
    print(f"✅ Extracted {len(features)} features")
    print(f"Validation: {message}")
    
    if is_valid:
        # Afficher quelques features clés
        print("\n🔥 Key Features:")
        print(f"  triple_confluence: {features['triple_confluence']}")
        print(f"  sl_in_confluence_zone: {features['sl_in_confluence_zone']}")
        print(f"  dist_hvl_ticks: {features['d_hvl_ticks']:.1f}")
        print(f"  num_gex_within_20ticks: {features['num_gex_within_20ticks']}")
        print(f"  depth_imbalance: {features['depth_imbalance']:.3f}")
