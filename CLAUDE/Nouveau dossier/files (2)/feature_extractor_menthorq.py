"""
🎯 FEATURE EXTRACTOR - MenthorQ Stop Hunt Features
Version: 1.0
Date: 18 Nov 2025

Extrait les 20/40/65 features du snapshot ML_READY.
Aligné avec approche MenthorQ: Options + OrderFlow
"""

import numpy as np
from typing import Dict, List


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Division sécurisée."""
    if b == 0 or np.isnan(b) or np.isinf(b):
        return default
    result = a / b
    return result if not (np.isnan(result) or np.isinf(result)) else default


# ═══════════════════════════════════════════════════════════════
# TIER 1: CORE MENTHORQ FEATURES
# ═══════════════════════════════════════════════════════════════

def extract_tier1_core(snapshot: dict, signal: dict = None) -> dict:
    """
    Extrait les 25 features core MenthorQ.
    
    Args:
        snapshot: ML_READY snapshot complet
        signal: Trading signal (optionnel pour cette tier)
    
    Returns:
        Dict avec 25 features
    """
    features = {}
    
    # ─────────────────────────────────────────────────────────
    # 1. OPTIONS LEVELS (10 features)
    # ─────────────────────────────────────────────────────────
    
    mid = snapshot.get('mid', 0)
    hvl = snapshot.get('hvl', 0)
    tick_size = 0.25
    
    # HVL
    features['hvl'] = hvl
    features['d_hvl_ticks'] = abs(mid - hvl) / tick_size if hvl > 0 else 9999
    
    # GEX Walls
    features['gex_1'] = snapshot.get('gex_1', 0)
    features['gex_2'] = snapshot.get('gex_2', 0)
    features['call_resistance'] = snapshot.get('call_resistance', 0)
    features['put_support'] = snapshot.get('put_support', 0)
    
    # Blind Spots
    features['blind_spot_0'] = snapshot.get('blind_spot_0', 0)
    features['blind_spot_1'] = snapshot.get('blind_spot_1', 0)
    features['blind_spot_confluence'] = snapshot.get('blind_spot_confluence', 0)
    
    # Gamma side
    gamma_side_str = snapshot.get('gamma_side', 'below')
    features['gamma_side'] = 1 if gamma_side_str == 'above' else 0
    
    # ─────────────────────────────────────────────────────────
    # 2. ORDERFLOW DOM (8 features)
    # ─────────────────────────────────────────────────────────
    
    dom_features = snapshot.get('dom_features', {})
    
    features['depth_bid'] = dom_features.get('depth_bid', 0)
    features['depth_ask'] = dom_features.get('depth_ask', 0)
    features['depth_imbalance'] = snapshot.get('depth_imbalance', 0)
    
    features['slope_bid_1_3'] = dom_features.get('slope_bid_1_3', 0)
    features['slope_ask_1_3'] = dom_features.get('slope_ask_1_3', 0)
    
    features['imbalance_1_3'] = dom_features.get('imbalance_1_3', 0)
    features['imbalance_6_10'] = dom_features.get('imbalance_6_10', 0)
    
    features['pressure_strength'] = snapshot.get('pressure_strength', 0)
    
    # ─────────────────────────────────────────────────────────
    # 3. VOLUME/DELTA (7 features)
    # ─────────────────────────────────────────────────────────
    
    features['delta'] = snapshot.get('delta', 0)
    features['cum_delta_session'] = snapshot.get('cum_delta_session', 0)
    features['deltaPct'] = snapshot.get('deltaPct', 0)
    
    features['volume'] = snapshot.get('volume', 0)
    features['bidvol'] = snapshot.get('bidvol', 0)
    features['askvol'] = snapshot.get('askvol', 0)
    
    features['smart_money_flow'] = snapshot.get('smart_money_flow', 0)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 2: CONTEXT FEATURES
# ═══════════════════════════════════════════════════════════════

def extract_tier2_context(snapshot: dict) -> dict:
    """
    Extrait les 15 features de contexte.
    """
    features = {}
    
    # ─────────────────────────────────────────────────────────
    # 4. PRICE POSITION (6 features)
    # ─────────────────────────────────────────────────────────
    
    features['d_vwap'] = snapshot.get('d_vwap', 0)
    features['d_vwap_ticks'] = snapshot.get('d_vwap_ticks', 0)
    features['d_vwap_atr'] = snapshot.get('d_vwap_atr', 0)
    features['d_pvwap'] = snapshot.get('d_pvwap', 0)
    
    features['d_vpoc'] = snapshot.get('d_vpoc', 0)
    features['d_vpoc_ticks'] = snapshot.get('d_vpoc_ticks', 0)
    
    # ─────────────────────────────────────────────────────────
    # 5. VOLATILITY & MOMENTUM (5 features)
    # ─────────────────────────────────────────────────────────
    
    features['atr'] = snapshot.get('atr', 0)
    features['atr_ratio'] = snapshot.get('atr_ratio', 0)
    features['volatility_regime'] = snapshot.get('volatility_regime', 0)
    features['tick_momentum'] = snapshot.get('tick_momentum', 0)
    features['tick_rate_3s'] = snapshot.get('tick_rate_3s', 0)
    
    # ─────────────────────────────────────────────────────────
    # 6. SESSION STRUCTURE (4 features)
    # ─────────────────────────────────────────────────────────
    
    features['session_progress'] = snapshot.get('session_progress', 0)
    features['session_elapsed_s'] = snapshot.get('session_elapsed_s', 0)
    features['position_in_range'] = snapshot.get('position_in_range', 0)
    features['day_range_pct'] = snapshot.get('day_range_pct', 0)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 3: ENGINEERED FEATURES
# ═══════════════════════════════════════════════════════════════

def extract_tier3_engineered(snapshot: dict) -> dict:
    """
    Calcule les 15 features engineered.
    """
    features = {}
    
    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 5.0)
    hvl = snapshot.get('hvl', 0)
    tick_size = 0.25
    
    # ─────────────────────────────────────────────────────────
    # 7. DISTANCE CALCULATIONS (5 features)
    # ─────────────────────────────────────────────────────────
    
    # Distance HVL normalisée
    features['dist_hvl_atr'] = safe_divide(abs(mid - hvl), atr, default=999)
    
    # Distance nearest GEX
    gex_levels = [snapshot.get(f'gex_{i}', 0) for i in range(1, 6)]
    gex_distances = [abs(mid - g) / tick_size for g in gex_levels if g > 0]
    features['dist_nearest_gex_ticks'] = min(gex_distances) if gex_distances else 9999
    
    # Distance nearest blind spot
    blind_spots = [snapshot.get(f'blind_spot_{i}', 0) for i in range(3)]
    blind_distances = [abs(mid - bs) / tick_size for bs in blind_spots if bs > 0]
    features['dist_nearest_blind_spot'] = min(blind_distances) if blind_distances else 9999
    
    # Distance walls
    call_wall = snapshot.get('call_resistance', 0)
    put_wall = snapshot.get('put_support', 0)
    features['dist_call_wall_ticks'] = abs(mid - call_wall) / tick_size if call_wall > 0 else 9999
    features['dist_put_wall_ticks'] = abs(mid - put_wall) / tick_size if put_wall > 0 else 9999
    
    # ─────────────────────────────────────────────────────────
    # 8. DOM RATIOS (5 features)
    # ─────────────────────────────────────────────────────────
    
    dom_features = snapshot.get('dom_features', {})
    depth_bid = dom_features.get('depth_bid', 1)
    depth_ask = dom_features.get('depth_ask', 1)
    
    features['depth_imbalance_ratio'] = safe_divide(depth_bid, depth_ask, default=1.0)
    
    slope_bid = dom_features.get('slope_bid_1_3', 1)
    slope_ask = dom_features.get('slope_ask_1_3', 1)
    features['dom_slope_ratio'] = safe_divide(slope_bid, slope_ask, default=1.0)
    
    # Opposite side imbalance (calculé plus tard avec signal direction)
    features['opposite_side_imbalance'] = 0  # Placeholder
    
    features['pressure_strength_depth'] = snapshot.get('pressure_strength_depth', 0)
    features['ob_center'] = snapshot.get('ob_center', 0.5)
    
    # ─────────────────────────────────────────────────────────
    # 9. CONFLUENCE INDICATORS (5 features)
    # ─────────────────────────────────────────────────────────
    
    features['confluence_strength'] = snapshot.get('confluence_strength', 0)
    features['confluence_proximity'] = snapshot.get('confluence_proximity', 0)
    features['gamma_call_confluence'] = snapshot.get('gamma_call_confluence', 0)
    features['gamma_put_confluence'] = snapshot.get('gamma_put_confluence', 0)
    features['menthorq_impact_score'] = snapshot.get('menthorq_impact_score', 0)
    
    return features


# ═══════════════════════════════════════════════════════════════
# TIER 4: SIGNAL-SPECIFIC FEATURES
# ═══════════════════════════════════════════════════════════════

def extract_tier4_signal(snapshot: dict, signal: dict) -> dict:
    """
    Calcule les 10 features spécifiques au signal.
    
    Args:
        snapshot: ML_READY snapshot
        signal: Trading signal avec:
            - direction: 'LONG' | 'SHORT'
            - entry_price: float
            - sl_price: float
            - tp_price: float
    """
    features = {}
    
    if not signal:
        # Return zeros si pas de signal
        return {f'signal_feat_{i}': 0 for i in range(10)}
    
    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 5.0)
    tick_size = 0.25
    
    direction = signal.get('direction', 'LONG')
    entry = signal.get('entry_price', mid)
    sl = signal.get('sl_price', entry - 15*tick_size if direction=='LONG' else entry + 15*tick_size)
    tp = signal.get('tp_price', entry + 15*tick_size if direction=='LONG' else entry - 15*tick_size)
    
    # ─────────────────────────────────────────────────────────
    # 10. RISK/REWARD DU SIGNAL (10 features)
    # ─────────────────────────────────────────────────────────
    
    # Distances SL/TP
    sl_distance = abs(entry - sl)
    tp_distance = abs(entry - tp)
    
    features['sl_distance_ticks'] = sl_distance / tick_size
    features['sl_distance_atr'] = safe_divide(sl_distance, atr, default=0)
    features['tp_distance_ticks'] = tp_distance / tick_size
    features['tp_distance_atr'] = safe_divide(tp_distance, atr, default=0)
    features['risk_reward_ratio'] = safe_divide(tp_distance, sl_distance, default=1.0)
    
    # Position vs HVL
    hvl = snapshot.get('hvl', 0)
    if hvl > 0:
        features['entry_vs_hvl'] = 1 if entry > hvl else 0
    else:
        features['entry_vs_hvl'] = 0
    
    # SL/TP near level (CRITIQUE!)
    features['sl_near_level'] = check_near_level(sl, snapshot, threshold_ticks=10)
    features['tp_near_level'] = check_near_level(tp, snapshot, threshold_ticks=10)
    
    # Flow alignment
    bidPct = snapshot.get('bidPct', 0.5)
    askPct = snapshot.get('askPct', 0.5)
    flow = bidPct - askPct  # Positif = bullish
    
    if direction == 'LONG':
        features['flow_aligned'] = 1 if flow > 0 else 0
    else:
        features['flow_aligned'] = 1 if flow < 0 else 0
    
    # Pressure alignment
    pressure = snapshot.get('pressure_strength', 0)
    if direction == 'LONG':
        features['pressure_aligned'] = 1 if pressure > 0 else 0
    else:
        features['pressure_aligned'] = 1 if pressure < 0 else 0
    
    # Update opposite_side_imbalance
    dom_features = snapshot.get('dom_features', {})
    depth_bid = dom_features.get('depth_bid', 1)
    depth_ask = dom_features.get('depth_ask', 1)
    
    if direction == 'LONG':
        features['opposite_side_imbalance'] = safe_divide(depth_ask, depth_bid, default=1.0)
    else:
        features['opposite_side_imbalance'] = safe_divide(depth_bid, depth_ask, default=1.0)
    
    return features


def check_near_level(price: float, snapshot: dict, threshold_ticks: int = 10) -> int:
    """
    Vérifie si un prix est proche d'un niveau important MenthorQ.
    
    Returns:
        1 si près d'un niveau, 0 sinon
    """
    tick_size = 0.25
    threshold = threshold_ticks * tick_size
    
    # Niveaux à checker
    levels = [
        snapshot.get('hvl', 0),
        snapshot.get('call_resistance', 0),
        snapshot.get('put_support', 0),
        snapshot.get('gex_1', 0),
        snapshot.get('gex_2', 0),
        snapshot.get('gex_3', 0),
        snapshot.get('blind_spot_0', 0),
        snapshot.get('blind_spot_1', 0),
        snapshot.get('vwap', 0),
    ]
    
    for level in levels:
        if level > 0 and abs(price - level) < threshold:
            return 1  # DANGER! Proche d'un niveau
    
    return 0  # Safe


# ═══════════════════════════════════════════════════════════════
# EXTRACTORS COMPLETS
# ═══════════════════════════════════════════════════════════════

def extract_top20_features(snapshot: dict, signal: dict = None) -> dict:
    """
    Extrait les TOP 20 features minimales.
    """
    features = {}
    
    mid = snapshot.get('mid', 0)
    hvl = snapshot.get('hvl', 0)
    atr = snapshot.get('atr', 5.0)
    tick_size = 0.25
    
    # Niveaux (8)
    features['hvl'] = hvl
    features['d_hvl_ticks'] = abs(mid - hvl) / tick_size if hvl > 0 else 9999
    features['dist_hvl_atr'] = safe_divide(abs(mid - hvl), atr, default=999)
    features['call_resistance'] = snapshot.get('call_resistance', 0)
    features['put_support'] = snapshot.get('put_support', 0)
    features['blind_spot_0'] = snapshot.get('blind_spot_0', 0)
    features['blind_spot_confluence'] = snapshot.get('blind_spot_confluence', 0)
    
    # SL near level (requires signal)
    if signal:
        sl = signal.get('sl_price', 0)
        features['sl_near_level'] = check_near_level(sl, snapshot)
    else:
        features['sl_near_level'] = 0
    
    # DOM (6)
    features['depth_imbalance'] = snapshot.get('depth_imbalance', 0)
    dom_features = snapshot.get('dom_features', {})
    features['imbalance_1_3'] = dom_features.get('imbalance_1_3', 0)
    features['slope_bid_1_3'] = dom_features.get('slope_bid_1_3', 0)
    features['slope_ask_1_3'] = dom_features.get('slope_ask_1_3', 0)
    features['pressure_strength'] = snapshot.get('pressure_strength', 0)
    
    # Opposite side imbalance
    if signal:
        direction = signal.get('direction', 'LONG')
        depth_bid = dom_features.get('depth_bid', 1)
        depth_ask = dom_features.get('depth_ask', 1)
        if direction == 'LONG':
            features['opposite_side_imbalance'] = safe_divide(depth_ask, depth_bid, default=1.0)
        else:
            features['opposite_side_imbalance'] = safe_divide(depth_bid, depth_ask, default=1.0)
    else:
        features['opposite_side_imbalance'] = 1.0
    
    # Context (6)
    features['d_vwap_ticks'] = snapshot.get('d_vwap_ticks', 0)
    features['atr'] = atr
    features['session_progress'] = snapshot.get('session_progress', 0)
    features['confluence_strength'] = snapshot.get('confluence_strength', 0)
    features['deltaPct'] = snapshot.get('deltaPct', 0)
    
    # Flow aligned
    if signal:
        direction = signal.get('direction', 'LONG')
        bidPct = snapshot.get('bidPct', 0.5)
        askPct = snapshot.get('askPct', 0.5)
        flow = bidPct - askPct
        features['flow_aligned'] = 1 if (direction=='LONG' and flow>0) or (direction=='SHORT' and flow<0) else 0
    else:
        features['flow_aligned'] = 0
    
    return features


def extract_top40_features(snapshot: dict, signal: dict = None) -> dict:
    """
    Extrait les TOP 40 features (sweet spot).
    """
    # Start with top 20
    features = extract_top20_features(snapshot, signal)
    
    # Add 20 more
    mid = snapshot.get('mid', 0)
    tick_size = 0.25
    
    # Options (5)
    features['gex_1'] = snapshot.get('gex_1', 0)
    features['gex_2'] = snapshot.get('gex_2', 0)
    gamma_side = snapshot.get('gamma_side', 'below')
    features['gamma_side'] = 1 if gamma_side == 'above' else 0
    
    call_wall = snapshot.get('call_resistance', 0)
    put_wall = snapshot.get('put_support', 0)
    features['dist_call_wall_ticks'] = abs(mid - call_wall) / tick_size if call_wall > 0 else 9999
    features['dist_put_wall_ticks'] = abs(mid - put_wall) / tick_size if put_wall > 0 else 9999
    
    # DOM (5)
    dom_features = snapshot.get('dom_features', {})
    features['depth_bid'] = dom_features.get('depth_bid', 0)
    features['depth_ask'] = dom_features.get('depth_ask', 0)
    features['imbalance_6_10'] = dom_features.get('imbalance_6_10', 0)
    
    depth_bid = dom_features.get('depth_bid', 1)
    depth_ask = dom_features.get('depth_ask', 1)
    features['dom_slope_ratio'] = safe_divide(
        dom_features.get('slope_bid_1_3', 1),
        dom_features.get('slope_ask_1_3', 1),
        default=1.0
    )
    features['ob_center'] = snapshot.get('ob_center', 0.5)
    
    # Volume/Delta (5)
    features['delta'] = snapshot.get('delta', 0)
    features['cum_delta_session'] = snapshot.get('cum_delta_session', 0)
    features['volume'] = snapshot.get('volume', 0)
    features['bidvol'] = snapshot.get('bidvol', 0)
    features['askvol'] = snapshot.get('askvol', 0)
    
    # Context (5)
    features['d_vpoc_ticks'] = snapshot.get('d_vpoc_ticks', 0)
    features['volatility_regime'] = snapshot.get('volatility_regime', 0)
    features['tick_momentum'] = snapshot.get('tick_momentum', 0)
    features['position_in_range'] = snapshot.get('position_in_range', 0)
    features['menthorq_impact_score'] = snapshot.get('menthorq_impact_score', 0)
    
    return features


def extract_full65_features(snapshot: dict, signal: dict = None) -> dict:
    """
    Extrait les 65 features complètes.
    """
    features = {}
    
    # Combiner toutes les tiers
    features.update(extract_tier1_core(snapshot, signal))
    features.update(extract_tier2_context(snapshot))
    features.update(extract_tier3_engineered(snapshot))
    
    if signal:
        features.update(extract_tier4_signal(snapshot, signal))
    
    return features


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
        'blind_spot_0': 24738.51,
        'blind_spot_confluence': 0,
        'gamma_side': 'below',
        'depth_imbalance': 0.073,
        'dom_features': {
            'depth_bid': 22,
            'depth_ask': 19,
            'imbalance_1_3': -0.2,
            'imbalance_6_10': 0.058,
            'slope_bid_1_3': 0,
            'slope_ask_1_3': 2
        },
        'pressure_strength': 0.006,
        'd_vwap_ticks': 46.2,
        'session_progress': 0.002,
        'confluence_strength': 0.047,
        'deltaPct': -0.368,
        'bidPct': 0.315,
        'askPct': 0.684,
        # ... autres features
    }
    
    signal = {
        'direction': 'LONG',
        'entry_price': 24913.63,
        'sl_price': 24898.63,
        'tp_price': 24928.63
    }
    
    # Extract TOP 20
    features_20 = extract_top20_features(snapshot, signal)
    print(f"TOP 20 Features: {len(features_20)}")
    print(features_20)
    
    # Extract TOP 40
    features_40 = extract_top40_features(snapshot, signal)
    print(f"\nTOP 40 Features: {len(features_40)}")
    
    # Extract FULL 65
    features_65 = extract_full65_features(snapshot, signal)
    print(f"\nFULL Features: {len(features_65)}")
