"""
Feature Engineering RTY-Specific
Génère des features spécifiques au RTY (Russell 2000)

Caractéristiques RTY:
- Small caps
- Plus volatile que ES/NQ
- Moins de liquidité (spreads plus larges)
- Réagit fortement aux momentum shifts
- Corrélation avec ES/NQ mais avec lag

Version: 1.0
Date: 2025-11-06
"""

import pandas as pd
import numpy as np
from typing import Optional


def add_rty_specific_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute des features RTY-specific au DataFrame

    Categories:
    1. Volatility & Range Features (8 features)
    2. Momentum & Acceleration (7 features)
    3. Spread & Liquidity (6 features)
    4. Relative Strength vs ES/NQ (7 features)
    5. Breakout & Reversal Patterns (6 features)
    6. Small-Cap Flow Signatures (6 features)

    Total: 40 features
    """

    df = df.copy()

    print("\n" + "="*70)
    print("AJOUT FEATURES RTY-SPECIFIC")
    print("="*70)

    # =========================================================================
    # 1. VOLATILITY & RANGE FEATURES (8)
    # =========================================================================
    print("\n1. Volatility & Range Features...")

    # Volatility expansion (ATR actuel vs moyenne)
    atr_ma_20 = df['atr'].rolling(20, min_periods=1).mean()
    df['rty_volatility_expansion'] = df['atr'] / atr_ma_20.replace(0, np.nan)
    df['rty_volatility_expansion'] = df['rty_volatility_expansion'].fillna(1)

    # Volatility surge detection
    atr_std = df['atr'].rolling(20, min_periods=1).std()
    df['rty_volatility_surge'] = (
        df['atr'] > atr_ma_20 + 2 * atr_std
    ).astype(int)

    # Range expansion rate (accélération de la volatilité)
    df['rty_range_expansion_rate'] = df['atr'].diff(5) / df['atr'].shift(5).replace(0, np.nan)
    df['rty_range_expansion_rate'] = df['rty_range_expansion_rate'].fillna(0).clip(-2, 2)

    # Intrabar volatility (high-low range)
    bar_range = df['high'] - df['low']
    bar_range_ma = bar_range.rolling(20, min_periods=1).mean()
    df['rty_intrabar_volatility'] = bar_range / bar_range_ma.replace(0, np.nan)
    df['rty_intrabar_volatility'] = df['rty_intrabar_volatility'].fillna(1)

    # Volatility persistence (volatilité élevée prolongée)
    high_vol = (df['atr'] > atr_ma_20 * 1.2).astype(int)
    df['rty_volatility_persistence'] = high_vol.rolling(5, min_periods=1).sum()

    # Price whipsaw (changements de direction fréquents)
    price_direction = np.sign(df['close'].diff())
    direction_changes = (price_direction != price_direction.shift(1)).astype(int)
    df['rty_whipsaw_count'] = direction_changes.rolling(10, min_periods=1).sum()

    # Range normalized by tick size (RTY tick = 0.10)
    df['rty_range_ticks'] = bar_range / 0.10
    df['rty_range_ticks_ma'] = df['rty_range_ticks'].rolling(20, min_periods=1).mean()

    print(f"   8 volatility/range features creees")

    # =========================================================================
    # 2. MOMENTUM & ACCELERATION (7)
    # =========================================================================
    print("\n2. Momentum & Acceleration Features...")

    # Fast momentum (court terme - réactivité small caps)
    df['rty_momentum_3s'] = df['close'].diff(3)
    df['rty_momentum_5s'] = df['close'].diff(5)
    df['rty_momentum_10s'] = df['close'].diff(10)

    # Momentum strength (normalisé par ATR)
    df['rty_momentum_strength'] = df['rty_momentum_5s'] / df['atr'].replace(0, np.nan)
    df['rty_momentum_strength'] = df['rty_momentum_strength'].fillna(0).clip(-5, 5)

    # Price acceleration (dérivée seconde)
    momentum_5 = df['close'].diff(5)
    df['rty_price_acceleration'] = momentum_5.diff(5)

    # Momentum persistence (même direction prolongée)
    momentum_sign = np.sign(df['rty_momentum_5s'])
    df['rty_momentum_persistence'] = (
        (momentum_sign == momentum_sign.shift(1)) &
        (momentum_sign == momentum_sign.shift(2))
    ).astype(int)

    # Momentum exhaustion (momentum extrême puis ralentissement)
    momentum_ma = df['rty_momentum_5s'].rolling(20, min_periods=1).mean()
    momentum_std = df['rty_momentum_5s'].rolling(20, min_periods=1).std()
    momentum_z = (df['rty_momentum_5s'] - momentum_ma) / momentum_std.replace(0, np.nan)
    df['rty_momentum_exhaustion'] = (momentum_z.abs() > 2.5).astype(int)

    print(f"   7 momentum/acceleration features creees")

    # =========================================================================
    # 3. SPREAD & LIQUIDITY FEATURES (6)
    # =========================================================================
    print("\n3. Spread & Liquidity Features...")

    # Spread width analysis
    if 'spread_ticks' in df.columns:
        spread_ma = df['spread_ticks'].rolling(20, min_periods=1).mean()
        df['rty_spread_vs_avg'] = df['spread_ticks'] / spread_ma.replace(0, np.nan)
        df['rty_spread_vs_avg'] = df['rty_spread_vs_avg'].fillna(1)

        # Wide spread detection (liquidité faible)
        df['rty_wide_spread'] = (df['spread_ticks'] > 2).astype(int)

        # Spread expansion (spread croissant = liquidité décroissante)
        df['rty_spread_expansion'] = df['spread_ticks'].diff(5) > 0
        df['rty_spread_expansion'] = df['rty_spread_expansion'].astype(int)
    else:
        df['rty_spread_vs_avg'] = 1
        df['rty_wide_spread'] = 0
        df['rty_spread_expansion'] = 0

    # Liquidity proxy (volume relatif)
    vol_ma = df['volume'].rolling(20, min_periods=1).mean()
    df['rty_liquidity_proxy'] = df['volume'] / vol_ma.replace(0, np.nan)
    df['rty_liquidity_proxy'] = df['rty_liquidity_proxy'].fillna(1)

    # Thin market detection (faible volume + spread large)
    low_volume = df['volume'] < vol_ma * 0.5
    df['rty_thin_market'] = (low_volume & (df['rty_wide_spread'] == 1)).astype(int)

    # Order book depth proxy
    if 'q_bq1' in df.columns and 'q_aq1' in df.columns:
        total_depth = df['q_bq1'] + df['q_aq1']
        depth_ma = total_depth.rolling(20, min_periods=1).mean()
        df['rty_depth_vs_avg'] = total_depth / depth_ma.replace(0, np.nan)
        df['rty_depth_vs_avg'] = df['rty_depth_vs_avg'].fillna(1)
    else:
        df['rty_depth_vs_avg'] = 1

    print(f"   6 spread/liquidity features creees")

    # =========================================================================
    # 4. RELATIVE STRENGTH VS ES/NQ (7)
    # =========================================================================
    print("\n4. Relative Strength vs ES/NQ Features...")

    # RTY momentum vs ES/NQ (proxy - à améliorer avec vraies données ES/NQ)
    # Pour l'instant, on utilise les corrélations disponibles

    # RTY leading/lagging indicator
    momentum_10 = df['close'].diff(10)
    momentum_20 = df['close'].diff(20)
    df['rty_momentum_divergence'] = momentum_10 - momentum_20

    # Relative volatility (RTY vs market average)
    # Proxy: volatility regime
    if 'volatility_regime' in df.columns:
        df['rty_relative_volatility'] = df['volatility_regime']
    else:
        df['rty_relative_volatility'] = 1

    # Beta proxy (sensibilité aux mouvements du marché)
    # Calculé comme ratio des variations
    if len(df) > 60:
        price_returns = df['close'].pct_change()
        returns_std = price_returns.rolling(60, min_periods=20).std()
        df['rty_beta_proxy'] = returns_std / returns_std.rolling(120, min_periods=40).mean()
        df['rty_beta_proxy'] = df['rty_beta_proxy'].fillna(1)
    else:
        df['rty_beta_proxy'] = 1

    # Correlation breakdown detection (RTY décorrèle de ES/NQ)
    if 'corr' in df.columns:
        corr_ma = df['corr'].rolling(20, min_periods=1).mean()
        df['rty_correlation_breakdown'] = (df['corr'] < corr_ma - 0.1).astype(int)
    else:
        df['rty_correlation_breakdown'] = 0

    # Small cap outperformance (RTY plus fort que large caps)
    df['rty_outperformance'] = (momentum_10 > momentum_10.rolling(20, min_periods=1).mean()).astype(int)

    # Risk-on/Risk-off proxy (RTY sensible au risk sentiment)
    # High volume + high volatility = Risk-on
    high_vol = df['volume'] > vol_ma * 1.5
    high_atr = df['atr'] > atr_ma_20 * 1.2
    df['rty_risk_on'] = (high_vol & high_atr).astype(int)
    df['rty_risk_off'] = (~high_vol & ~high_atr).astype(int)

    print(f"   7 relative strength features creees")

    # =========================================================================
    # 5. BREAKOUT & REVERSAL PATTERNS (6)
    # =========================================================================
    print("\n5. Breakout & Reversal Patterns...")

    # Breakout strength (distance au range)
    high_20 = df['high'].rolling(20, min_periods=1).max()
    low_20 = df['low'].rolling(20, min_periods=1).min()
    range_20 = high_20 - low_20

    df['rty_breakout_strength_up'] = (df['close'] - high_20) / range_20.replace(0, np.nan)
    df['rty_breakout_strength_up'] = df['rty_breakout_strength_up'].fillna(0).clip(0, 2)

    df['rty_breakout_strength_down'] = (low_20 - df['close']) / range_20.replace(0, np.nan)
    df['rty_breakout_strength_down'] = df['rty_breakout_strength_down'].fillna(0).clip(0, 2)

    # False breakout detection (breakout puis reversal rapide)
    breakout_up = df['close'] > high_20.shift(1)
    reversal_down = df['close'] < df['close'].shift(5)
    df['rty_false_breakout_up'] = (breakout_up & reversal_down).astype(int)

    breakout_down = df['close'] < low_20.shift(1)
    reversal_up = df['close'] > df['close'].shift(5)
    df['rty_false_breakout_down'] = (breakout_down & reversal_up).astype(int)

    # Reversal signal (prix extrême + delta divergence)
    price_extreme_up = df['close'] > high_20.shift(1)
    price_extreme_down = df['close'] < low_20.shift(1)

    if 'delta' in df.columns:
        delta_down = df['delta'] < 0
        delta_up = df['delta'] > 0
        df['rty_reversal_signal_up'] = (price_extreme_down & delta_up).astype(int)
        df['rty_reversal_signal_down'] = (price_extreme_up & delta_down).astype(int)
    else:
        df['rty_reversal_signal_up'] = 0
        df['rty_reversal_signal_down'] = 0

    print(f"   6 breakout/reversal features creees")

    # =========================================================================
    # 6. SMALL-CAP FLOW SIGNATURES (6)
    # =========================================================================
    print("\n6. Small-Cap Flow Signatures...")

    # Retail flow proxy (petits volumes fréquents)
    small_volume = df['volume'] < vol_ma * 0.7
    df['rty_retail_flow_count'] = small_volume.rolling(10, min_periods=1).sum()

    # Institutional sweep (gros volume soudain)
    df['rty_institutional_sweep'] = (df['volume'] > vol_ma * 3).astype(int)

    # Delta clustering (delta similaires consécutifs)
    if 'delta' in df.columns:
        delta_sign = np.sign(df['delta'])
        delta_consistent = (delta_sign == delta_sign.shift(1)) & (delta_sign == delta_sign.shift(2))
        df['rty_delta_clustering'] = delta_consistent.astype(int)

        # Delta volatility (instabilité order flow)
        delta_std = df['delta'].rolling(10, min_periods=1).std()
        delta_std_ma = delta_std.rolling(20, min_periods=1).mean()
        df['rty_delta_volatility'] = delta_std / delta_std_ma.replace(0, np.nan)
        df['rty_delta_volatility'] = df['rty_delta_volatility'].fillna(1)
    else:
        df['rty_delta_clustering'] = 0
        df['rty_delta_volatility'] = 1

    # Order flow exhaustion (volume élevé sans mouvement prix)
    high_volume = df['volume'] > vol_ma * 2
    low_price_change = df['close'].diff(5).abs() < df['atr'] * 0.3
    df['rty_flow_exhaustion'] = (high_volume & low_price_change).astype(int)

    # Momentum vs volume divergence
    strong_momentum = df['rty_momentum_5s'].abs() > df['rty_momentum_5s'].rolling(20, min_periods=1).std() * 2
    low_vol = df['volume'] < vol_ma
    df['rty_momentum_volume_divergence'] = (strong_momentum & low_vol).astype(int)

    print(f"   6 small-cap flow features creees")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print(f"TOTAL : 40 features RTY-specific ajoutees")
    print("="*70)

    return df


# =========================================================================
# TEST BLOCK
# =========================================================================
if __name__ == "__main__":
    print("\nTEST MODULE feature_engineering_rty.py")
    print("="*70)

    # Simuler un DataFrame RTY
    print("\nSimulation DataFrame RTY...")
    np.random.seed(42)
    n_samples = 1000

    test_df = pd.DataFrame({
        'mid': np.random.randn(n_samples).cumsum() + 2447,
        'close': np.random.randn(n_samples).cumsum() + 2447,
        'high': np.random.randn(n_samples).cumsum() + 2449,
        'low': np.random.randn(n_samples).cumsum() + 2445,
        'volume': np.random.randint(20, 200, n_samples),
        'delta': np.random.randint(-50, 50, n_samples),
        'atr': np.random.uniform(0.6, 1.2, n_samples),
        'spread_ticks': np.random.choice([1, 2, 3, 4], n_samples),
        'q_bq1': np.random.randint(5, 30, n_samples),
        'q_aq1': np.random.randint(5, 30, n_samples),
        'volatility_regime': np.random.choice([1, 2, 3], n_samples),
        'corr': np.random.uniform(0.5, 0.95, n_samples),
    })

    print(f"Test DataFrame cree : {test_df.shape}")

    # Appliquer les features RTY-specific
    print("\nApplication des features RTY-specific...")
    test_df_enhanced = add_rty_specific_features(test_df)

    # Vérifier les nouvelles colonnes
    new_cols = [col for col in test_df_enhanced.columns if col.startswith('rty_')]
    print(f"\nNombres de features RTY ajoutees : {len(new_cols)}")
    print(f"\nListe des features :")
    for i, col in enumerate(new_cols, 1):
        print(f"   {i:2d}. {col}")

    # Stats de base
    print(f"\nStats de base (5 premieres features) :")
    print(test_df_enhanced[new_cols[:5]].describe())

    print("\nTEST REUSSI !")

