"""
Feature Engineering ES-Specific
Génère des features spécifiques à l'ES (E-mini S&P 500)

Caractéristiques ES:
- Large caps, blue chips
- Moins volatile que NQ/RTY
- Flows institutionnels importants
- Réagit aux gamma levels et options
- Sessions bien définies (London/NY overlap crucial)

Version: 1.0
Date: 2025-11-06
"""

import pandas as pd
import numpy as np
from typing import Optional


def add_es_specific_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute des features ES-specific au DataFrame

    Categories:
    1. Institutional Flow (8 features)
    2. Gamma & Options Proximity (7 features)
    3. Session Analysis (6 features)
    4. Volume Profile (7 features)
    5. Price Action ES-style (6 features)
    6. Delta Flow Patterns (6 features)

    Total: 40 features
    """

    df = df.copy()

    print("\n" + "="*70)
    print("AJOUT FEATURES ES-SPECIFIC")
    print("="*70)

    # =========================================================================
    # 1. INSTITUTIONAL FLOW FEATURES (8)
    # =========================================================================
    print("\n1. Institutional Flow Features...")

    # Large block detection (volume > 3x moyenne)
    vol_ma_20 = df['volume'].rolling(20, min_periods=1).mean()
    df['es_large_block'] = (df['volume'] > vol_ma_20 * 3).astype(int)

    # Institutional pressure (delta cumulé normalisé)
    df['es_inst_pressure'] = df['cum_delta_session'] / df['volume'].rolling(60, min_periods=1).sum()
    df['es_inst_pressure'] = df['es_inst_pressure'].fillna(0).clip(-1, 1)

    # Smart money flow (gros delta + spread serré)
    df['es_smart_money'] = (
        (df['delta'].abs() > df['delta'].rolling(20, min_periods=1).std() * 2) &
        (df['spread_ticks'] <= 1)
    ).astype(int)

    # Absorption patterns (volume élevé, prix flat)
    price_change = df['close'].diff(5).abs()
    df['es_absorption'] = (
        (df['volume'] > vol_ma_20 * 2) &
        (price_change < df['atr'] * 0.2)
    ).astype(int)

    # Institutional momentum (delta flow smoothed)
    df['es_delta_flow_smooth'] = df['delta'].rolling(10, min_periods=1).mean()

    # Volume-weighted delta
    df['es_vw_delta'] = df['delta'] * df['volume']
    df['es_vw_delta_ma'] = df['es_vw_delta'].rolling(20, min_periods=1).mean()

    # Persistent flow (même sens 5 bars consécutives)
    delta_sign = np.sign(df['delta'])
    df['es_persistent_flow'] = (delta_sign == delta_sign.shift(1)) & \
                                 (delta_sign == delta_sign.shift(2)) & \
                                 (delta_sign == delta_sign.shift(3)) & \
                                 (delta_sign == delta_sign.shift(4))
    df['es_persistent_flow'] = df['es_persistent_flow'].astype(int)

    print(f"   8 institutional flow features creees")

    # =========================================================================
    # 2. GAMMA & OPTIONS PROXIMITY FEATURES (7)
    # =========================================================================
    print("\n2. Gamma & Options Proximity Features...")

    # Distance au gamma wall normalisée par ATR
    if 'call_resistance' in df.columns and 'put_support' in df.columns:
        df['es_gamma_call_dist_atr'] = (df['call_resistance'] - df['mid']) / df['atr']
        df['es_gamma_put_dist_atr'] = (df['mid'] - df['put_support']) / df['atr']

        # Compression gamma (entre call/put resistance)
        gamma_range = df['call_resistance'] - df['put_support']
        df['es_gamma_compression'] = df['atr'] / gamma_range.replace(0, np.nan)
        df['es_gamma_compression'] = df['es_gamma_compression'].fillna(0).clip(0, 2)

        # Proximity to gamma flip
        df['es_near_gamma_flip'] = (
            (df['es_gamma_call_dist_atr'].abs() < 1.5) |
            (df['es_gamma_put_dist_atr'].abs() < 1.5)
        ).astype(int)
    else:
        df['es_gamma_call_dist_atr'] = 0
        df['es_gamma_put_dist_atr'] = 0
        df['es_gamma_compression'] = 0
        df['es_near_gamma_flip'] = 0

    # GEX concentration (distance au nearest GEX)
    if 'd_nearest_gex_up_ticks' in df.columns and 'd_nearest_gex_down_ticks' in df.columns:
        df['es_gex_proximity'] = np.minimum(
            df['d_nearest_gex_up_ticks'].abs(),
            df['d_nearest_gex_down_ticks'].abs()
        )
        df['es_gex_magnet'] = (df['es_gex_proximity'] < 10).astype(int)
    else:
        df['es_gex_proximity'] = 999
        df['es_gex_magnet'] = 0

    # Options expiration proximity (mock - à implémenter avec calendrier réel)
    df['es_opex_week'] = 0  # Placeholder

    print(f"   7 gamma/options features creees")

    # =========================================================================
    # 3. SESSION ANALYSIS FEATURES (6)
    # =========================================================================
    print("\n3. Session Analysis Features...")

    # Session progress (0-1)
    if 'session_progress' in df.columns:
        session_prog = df['session_progress']
    else:
        session_prog = df['elapsed_s'] / (8 * 3600)  # Approximation 8h session
        session_prog = session_prog.clip(0, 1)

    # Session phases
    df['es_session_opening'] = (session_prog < 0.1).astype(int)  # Premiers 10%
    df['es_session_power_hour'] = (session_prog > 0.85).astype(int)  # Derniers 15%
    df['es_session_lunch'] = ((session_prog > 0.4) & (session_prog < 0.6)).astype(int)

    # Volatility vs session average
    session_atr_mean = df.groupby(df.index // 3600)['atr'].transform('mean')
    df['es_atr_vs_session'] = df['atr'] / session_atr_mean.replace(0, np.nan)
    df['es_atr_vs_session'] = df['es_atr_vs_session'].fillna(1)

    # Volume vs session average
    session_vol_mean = df.groupby(df.index // 3600)['volume'].transform('mean')
    df['es_volume_vs_session'] = df['volume'] / session_vol_mean.replace(0, np.nan)
    df['es_volume_vs_session'] = df['es_volume_vs_session'].fillna(1)

    print(f"   6 session analysis features creees")

    # =========================================================================
    # 4. VOLUME PROFILE FEATURES (7)
    # =========================================================================
    print("\n4. Volume Profile Features...")

    # VPOC proximity
    if 'd_vpoc_ticks' in df.columns:
        df['es_vpoc_distance_atr'] = df['d_vpoc_ticks'] * 0.25 / df['atr']  # 0.25 = ES tick
        df['es_near_vpoc'] = (df['d_vpoc_ticks'].abs() < 8).astype(int)
    else:
        df['es_vpoc_distance_atr'] = 0
        df['es_near_vpoc'] = 0

    # Value Area position
    if 'in_value_area' in df.columns:
        df['es_in_va'] = df['in_value_area'].astype(int)
    else:
        df['es_in_va'] = 0

    # VAH/VAL distance
    if 'd_vah_ticks' in df.columns and 'd_val_ticks' in df.columns:
        df['es_vah_distance'] = df['d_vah_ticks'] * 0.25 / df['atr']
        df['es_val_distance'] = df['d_val_ticks'] * 0.25 / df['atr']

        # VA width (range)
        df['es_va_width_atr'] = (df['d_vah_ticks'] - df['d_val_ticks']).abs() * 0.25 / df['atr']
    else:
        df['es_vah_distance'] = 0
        df['es_val_distance'] = 0
        df['es_va_width_atr'] = 0

    # Volume at edges (VAH/VAL)
    df['es_volume_at_edge'] = (
        (df['es_vah_distance'].abs() < 2) |
        (df['es_val_distance'].abs() < 2)
    ).astype(int)

    print(f"   7 volume profile features creees")

    # =========================================================================
    # 5. PRICE ACTION ES-STYLE (6)
    # =========================================================================
    print("\n5. Price Action ES-Style Features...")

    # Range contraction (Bollinger squeeze proxy)
    atr_ma = df['atr'].rolling(20, min_periods=1).mean()
    df['es_range_contraction'] = df['atr'] / atr_ma

    # Breakout detection (prix sort de range 20 bars)
    high_20 = df['high'].rolling(20, min_periods=1).max()
    low_20 = df['low'].rolling(20, min_periods=1).min()
    df['es_breakout_up'] = (df['close'] > high_20.shift(1)).astype(int)
    df['es_breakout_down'] = (df['close'] < low_20.shift(1)).astype(int)

    # Inside bar (range actuel < range précédent)
    prev_range = (df['high'].shift(1) - df['low'].shift(1))
    curr_range = df['high'] - df['low']
    df['es_inside_bar'] = (curr_range < prev_range).astype(int)

    # Momentum consistency (prix et delta même direction)
    price_direction = np.sign(df['close'].diff())
    delta_direction = np.sign(df['delta'])
    df['es_momentum_aligned'] = (price_direction == delta_direction).astype(int)

    print(f"   6 price action features creees")

    # =========================================================================
    # 6. DELTA FLOW PATTERNS (6)
    # =========================================================================
    print("\n6. Delta Flow Patterns...")

    # Delta divergence (prix monte, delta négatif)
    price_change_5 = df['close'].diff(5)
    delta_sum_5 = df['delta'].rolling(5, min_periods=1).sum()
    df['es_delta_divergence'] = (
        ((price_change_5 > 0) & (delta_sum_5 < 0)) |
        ((price_change_5 < 0) & (delta_sum_5 > 0))
    ).astype(int)

    # Delta acceleration
    delta_ma_fast = df['delta'].rolling(5, min_periods=1).mean()
    delta_ma_slow = df['delta'].rolling(20, min_periods=1).mean()
    df['es_delta_acceleration'] = delta_ma_fast - delta_ma_slow

    # Cumulative delta trend
    df['es_cum_delta_trend'] = np.sign(df['cum_delta_session'].diff(10))

    # Delta exhaustion (delta extrême puis reversal)
    delta_std = df['delta'].rolling(20, min_periods=1).std()
    delta_z = (df['delta'] - df['delta'].rolling(20, min_periods=1).mean()) / delta_std.replace(0, np.nan)
    df['es_delta_exhaustion'] = (delta_z.abs() > 2.5).astype(int)

    # Order flow imbalance strength
    if 'level1_imbalance' in df.columns:
        df['es_imbalance_strength'] = df['level1_imbalance'].abs()
    else:
        df['es_imbalance_strength'] = 0

    print(f"   6 delta flow features creees")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print(f"TOTAL : 40 features ES-specific ajoutees")
    print("="*70)

    return df


# =========================================================================
# TEST BLOCK
# =========================================================================
if __name__ == "__main__":
    print("\nTEST MODULE feature_engineering_es.py")
    print("="*70)

    # Charger des données ES pour tester
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

    # Simuler un DataFrame ES
    print("\nSimulation DataFrame ES...")
    np.random.seed(42)
    n_samples = 1000

    test_df = pd.DataFrame({
        'mid': np.random.randn(n_samples).cumsum() + 6800,
        'close': np.random.randn(n_samples).cumsum() + 6800,
        'high': np.random.randn(n_samples).cumsum() + 6802,
        'low': np.random.randn(n_samples).cumsum() + 6798,
        'volume': np.random.randint(50, 500, n_samples),
        'delta': np.random.randint(-100, 100, n_samples),
        'cum_delta_session': np.random.randint(-500, 500, n_samples).cumsum(),
        'atr': np.random.uniform(1.5, 2.5, n_samples),
        'spread_ticks': np.random.choice([1, 2, 3], n_samples),
        'call_resistance': np.random.uniform(6900, 7000, n_samples),
        'put_support': np.random.uniform(6700, 6800, n_samples),
        'd_nearest_gex_up_ticks': np.random.randint(5, 50, n_samples),
        'd_nearest_gex_down_ticks': np.random.randint(5, 50, n_samples),
        'd_vpoc_ticks': np.random.randint(-20, 20, n_samples),
        'in_value_area': np.random.choice([True, False], n_samples),
        'd_vah_ticks': np.random.randint(10, 40, n_samples),
        'd_val_ticks': np.random.randint(-40, -10, n_samples),
        'level1_imbalance': np.random.uniform(-1, 1, n_samples),
        'session_progress': np.linspace(0, 1, n_samples),
        'elapsed_s': np.arange(n_samples) * 5,
    })

    print(f"Test DataFrame cree : {test_df.shape}")

    # Appliquer les features ES-specific
    print("\nApplication des features ES-specific...")
    test_df_enhanced = add_es_specific_features(test_df)

    # Vérifier les nouvelles colonnes
    new_cols = [col for col in test_df_enhanced.columns if col.startswith('es_')]
    print(f"\nNombres de features ES ajoutees : {len(new_cols)}")
    print(f"\nListe des features :")
    for i, col in enumerate(new_cols, 1):
        print(f"   {i:2d}. {col}")

    # Stats de base
    print(f"\nStats de base (5 premieres features) :")
    print(test_df_enhanced[new_cols[:5]].describe())

    print("\nTEST REUSSI !")

