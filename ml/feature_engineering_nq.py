#!/usr/bin/env python3
"""
Phase 3 : Feature Engineering spécifique NQ
Ajoute des features momentum et volatilité adaptées au Nasdaq
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Ajouter le répertoire parent au PATH
sys.path.insert(0, str(Path(__file__).parent.parent))


def add_nq_specific_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute des features spécifiques pour NQ (Nasdaq)

    NQ caractéristiques :
    - Plus volatile que ES/RTY
    - Réagit fortement aux tech stocks
    - Momentum agressif
    - Swings plus importants

    Args:
        df: DataFrame avec les données brutes

    Returns:
        DataFrame enrichi avec features NQ-specific
    """

    print("\n" + "="*70)
    print("🔧 AJOUT FEATURES NQ-SPECIFIC")
    print("="*70)

    df = df.copy()

    # ═════════════════════════════════════════════════════════════════════
    # 1. MOMENTUM FEATURES (réactivité court terme)
    # ═════════════════════════════════════════════════════════════════════

    print("\n📈 1. Momentum Features...")

    # Momentum court terme (3s, 5s, 10s)
    for period in [3, 5, 10, 20]:
        df[f'momentum_{period}s'] = df['close'].diff(period)
        df[f'momentum_pct_{period}s'] = df['close'].pct_change(period) * 100

    # Momentum normalisé par ATR
    for period in [5, 10, 20]:
        df[f'momentum_atr_{period}s'] = df[f'momentum_{period}s'] / df['atr'].replace(0, np.nan)

    # Accélération du prix (dérivée seconde)
    df['price_acceleration_5s'] = df['momentum_5s'].diff(5)
    df['price_acceleration_10s'] = df['momentum_10s'].diff(5)

    print(f"   ✅ {9} momentum features créées")

    # ═════════════════════════════════════════════════════════════════════
    # 2. VOLATILITY FEATURES (expansion/contraction)
    # ═════════════════════════════════════════════════════════════════════

    print("\n📊 2. Volatility Features...")

    # Rolling std court terme
    for window in [10, 20, 60]:
        df[f'volatility_std_{window}s'] = df['close'].rolling(window).std()

    # Ratio volatilité actuelle / moyenne
    df['volatility_ratio_20_60'] = (
        df['volatility_std_20s'] / df['volatility_std_60s'].replace(0, np.nan)
    )

    # Volatility surge (expansion soudaine)
    df['volatility_surge'] = (
        df['volatility_std_10s'] / df['volatility_std_60s'].rolling(60).mean().replace(0, np.nan)
    )

    # Range expansion
    df['range_expansion'] = df['total_range_ticks'] / df['total_range_ticks'].rolling(20).mean().replace(0, np.nan)

    print(f"   ✅ {6} volatility features créées")

    # ═════════════════════════════════════════════════════════════════════
    # 3. VOLUME FEATURES (pression d'achat/vente)
    # ═════════════════════════════════════════════════════════════════════

    print("\n📦 3. Volume Features...")

    # Volume surge
    df['volume_surge_20s'] = df['volume'] / df['volume'].rolling(20).mean().replace(0, np.nan)
    df['volume_surge_60s'] = df['volume'] / df['volume'].rolling(60).mean().replace(0, np.nan)

    # Volume-weighted momentum
    df['volume_weighted_momentum_5s'] = df['momentum_5s'] * df['volume_surge_20s']
    df['volume_weighted_momentum_10s'] = df['momentum_10s'] * df['volume_surge_20s']

    # Delta momentum (order flow momentum)
    for period in [5, 10, 20]:
        df[f'delta_momentum_{period}s'] = df['delta'].diff(period)

    # Cumulative delta acceleration
    df['cum_delta_acceleration'] = df['cum_delta_session'].diff(10)

    print(f"   ✅ {8} volume features créées")

    # ═════════════════════════════════════════════════════════════════════
    # 4. PRICE ACTION FEATURES (patterns court terme)
    # ═════════════════════════════════════════════════════════════════════

    print("\n🎯 4. Price Action Features...")

    # Wick ratios (rejet de prix)
    df['upper_wick_ratio'] = df['upper_wick_ticks'] / df['total_range_ticks'].replace(0, np.nan)
    df['lower_wick_ratio'] = df['lower_wick_ticks'] / df['total_range_ticks'].replace(0, np.nan)
    df['wick_imbalance'] = df['upper_wick_ratio'] - df['lower_wick_ratio']

    # Distance au VWAP court terme
    df['d_vwap_volatility'] = df['d_vwap'] / df['volatility_std_20s'].replace(0, np.nan)

    # Reversion probability (distance extrême → probable reversion)
    df['reversion_score'] = np.abs(df['d_vwap_atr']) * df['volatility_surge']

    # Trend strength (coherence du mouvement)
    df['trend_strength_10s'] = (
        df['momentum_10s'].rolling(10).apply(lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0.5)
    )

    print(f"   ✅ {6} price action features créées")

    # ═════════════════════════════════════════════════════════════════════
    # 5. RELATIVE STRENGTH FEATURES (ES/NQ leadership)
    # ═════════════════════════════════════════════════════════════════════

    print("\n🔗 5. Relative Strength Features...")

    # Leadership vs ES (déjà existant via 'corr' mais on l'améliore)
    if 'corr' in df.columns:
        df['corr_strength'] = np.abs(df['corr'])  # Force de la corrélation
        df['corr_change'] = df['corr'].diff(10)   # Changement de corrélation

    # Ratio de volatilité NQ/ES (si disponible via intermarkets)
    # Note: Nécessite données ES en temps réel

    print(f"   ✅ {2} relative strength features créées")

    # ═════════════════════════════════════════════════════════════════════
    # 6. MICRO-STRUCTURE FEATURES (DOM + execution)
    # ═════════════════════════════════════════════════════════════════════

    print("\n🔬 6. Micro-structure Features...")

    # Spread dynamics
    df['spread_volatility'] = df['spread_ticks'].rolling(20).std()
    df['spread_expansion'] = df['spread_ticks'] / df['spread_ticks'].rolling(60).mean().replace(0, np.nan)

    # Microprice momentum
    df['microprice_momentum_5s'] = df['microprice'].diff(5)
    df['microprice_momentum_10s'] = df['microprice'].diff(10)

    # Order book pressure acceleration
    df['ob_pressure_change'] = df['ob_center'].diff(5)
    df['depth_imbalance_momentum'] = df['depth_imbalance'].diff(10)

    print(f"   ✅ {6} micro-structure features créées")

    # ═════════════════════════════════════════════════════════════════════
    # NETTOYAGE
    # ═════════════════════════════════════════════════════════════════════

    # Compter les nouvelles features
    new_features = [col for col in df.columns if any(
        substr in col for substr in [
            'momentum_', 'volatility_', 'volume_surge', 'delta_momentum',
            'wick_', 'reversion_', 'trend_strength', 'corr_',
            'spread_', 'microprice_momentum', 'ob_pressure', 'price_acceleration',
            'volume_weighted_momentum', 'cum_delta_acceleration', 'range_expansion'
        ]
    )]

    print(f"\n{'='*70}")
    print(f"✅ TOTAL : {len(new_features)} features NQ-specific ajoutées")
    print(f"{'='*70}")

    # Remplacer inf par NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df


def get_nq_feature_list():
    """Retourne la liste des features NQ-specific pour le training"""

    nq_features = [
        # Momentum
        'momentum_3s', 'momentum_5s', 'momentum_10s', 'momentum_20s',
        'momentum_pct_3s', 'momentum_pct_5s', 'momentum_pct_10s', 'momentum_pct_20s',
        'momentum_atr_5s', 'momentum_atr_10s', 'momentum_atr_20s',
        'price_acceleration_5s', 'price_acceleration_10s',

        # Volatility
        'volatility_std_10s', 'volatility_std_20s', 'volatility_std_60s',
        'volatility_ratio_20_60', 'volatility_surge', 'range_expansion',

        # Volume
        'volume_surge_20s', 'volume_surge_60s',
        'volume_weighted_momentum_5s', 'volume_weighted_momentum_10s',
        'delta_momentum_5s', 'delta_momentum_10s', 'delta_momentum_20s',
        'cum_delta_acceleration',

        # Price Action
        'upper_wick_ratio', 'lower_wick_ratio', 'wick_imbalance',
        'd_vwap_volatility', 'reversion_score', 'trend_strength_10s',

        # Relative Strength
        'corr_strength', 'corr_change',

        # Micro-structure
        'spread_volatility', 'spread_expansion',
        'microprice_momentum_5s', 'microprice_momentum_10s',
        'ob_pressure_change', 'depth_imbalance_momentum'
    ]

    return nq_features


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TEST FEATURE ENGINEERING NQ")
    print("="*70)

    # Test sur un petit échantillon
    from ml.train_ml_direction_15min import load_all_data

    data_dirs = [
        Path("DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_9/ML_READY"),
        Path("DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_9/ML_READY"),
    ]

    df = load_all_data(data_dirs, "NQ Test Features")
    print(f"\n✅ {len(df):,} samples chargés")
    print(f"📊 Colonnes initiales : {len(df.columns)}")

    # Ajouter features NQ
    df_enriched = add_nq_specific_features(df)

    print(f"\n📊 Colonnes après enrichissement : {len(df_enriched.columns)}")
    print(f"➕ Nouvelles features : {len(df_enriched.columns) - len(df.columns)}")

    # Afficher quelques stats
    nq_features = get_nq_feature_list()
    print(f"\n📋 Features NQ-specific disponibles : {len(nq_features)}")

    # Vérifier NaN
    nan_counts = df_enriched[nq_features].isnull().sum()
    features_with_nan = nan_counts[nan_counts > 0]

    if len(features_with_nan) > 0:
        print(f"\n⚠️  Features avec NaN :")
        for feat, count in features_with_nan.items():
            pct = count / len(df_enriched) * 100
            print(f"   {feat}: {count:,} ({pct:.1f}%)")
    else:
        print(f"\n✅ Aucune feature avec NaN")

    print(f"\n{'='*70}")
    print("✅ TEST TERMINÉ")
    print(f"{'='*70}")
