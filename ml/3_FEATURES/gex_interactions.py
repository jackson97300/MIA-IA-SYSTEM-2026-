"""
Module pour les interactions GEX avancées.
10 nouvelles features qui combinent les niveaux MenthorQ avec d'autres indicateurs.
"""

import pandas as pd
import numpy as np


def add_gex_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute 10 nouvelles interactions GEX au DataFrame.
    
    Args:
        df: DataFrame avec features de base
        
    Returns:
        DataFrame avec 10 colonnes supplémentaires
    """
    
    # Helper pour éviter division par zéro
    def safe_divide(a, b, default=0.0):
        result = np.where(b != 0, a / b, default)
        return result
    
    # ═══════════════════════════════════════════════════════════
    # 1. GEX × Delta (momentum vers GEX)
    # ═══════════════════════════════════════════════════════════
    df['gex_delta_momentum'] = safe_divide(
        df['gex_proximity_min'] * df['cum_delta_session'],
        1000,
        default=0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 2. GEX × Volume (intensité)
    # ═══════════════════════════════════════════════════════════
    volume_ma20 = df['volume'].rolling(window=20, min_periods=1).mean()
    df['gex_volume_intensity'] = safe_divide(
        df['gex_proximity_min'] * df['volume'],
        volume_ma20,
        default=0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 3. GEX × VWAP distance (contexte)
    # ═══════════════════════════════════════════════════════════
    df['gex_vwap_context'] = safe_divide(
        df['gex_proximity_min'] * df['d_vwap_ticks'].abs(),
        10,
        default=0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 4. GEX × ATR (volatilité ajustée)
    # ═══════════════════════════════════════════════════════════
    df['gex_volatility_adjusted'] = safe_divide(
        df['gex_proximity_min'],
        df['atr'] + 0.01,
        default=0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 5. Call resistance × Delta (pression vers résistance)
    # ═══════════════════════════════════════════════════════════
    df['call_delta_pressure'] = np.where(
        df['mid'] < df['call_resistance'],
        safe_divide(
            (df['call_resistance'] - df['mid']) * df['cum_delta_session'],
            1000,
            default=0.0
        ),
        0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 6. Put support × Delta (pression vers support)
    # ═══════════════════════════════════════════════════════════
    df['put_delta_pressure'] = np.where(
        df['mid'] > df['put_support'],
        safe_divide(
            (df['mid'] - df['put_support']) * df['cum_delta_session'],
            1000,
            default=0.0
        ),
        0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 7. HVL × Delta (gamma regime momentum)
    # ═══════════════════════════════════════════════════════════
    df['hvl_delta_regime'] = safe_divide(
        (df['mid'] - df['hvl']) * df['cum_delta_session'],
        1000,
        default=0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 8. Blind spot × Institutional pressure (piège institutionnel)
    # ═══════════════════════════════════════════════════════════
    if 'blind_spot_weight' in df.columns and 'institutional_pressure' in df.columns:
        df['blind_institutional_trap'] = df['blind_spot_weight'] * df['institutional_pressure']
    else:
        # Approximation
        blind_prox = 1.0 / (df['gex_proximity_min'] / 10 + 1)
        inst_pressure = df['institutional_pressure'] if 'institutional_pressure' in df.columns else 0
        df['blind_institutional_trap'] = blind_prox * inst_pressure
    
    # ═══════════════════════════════════════════════════════════
    # 9. GEX × Next wall (confluence niveaux clés)
    # ═══════════════════════════════════════════════════════════
    df['gex_wall_confluence'] = safe_divide(
        df['gex_proximity_min'] * df['next_wall_strength'],
        df['next_wall_dist_ticks'].abs() + 1,
        default=0.0
    )
    
    # ═══════════════════════════════════════════════════════════
    # 10. Call/Put spread × Volume (pression directionnelle options)
    # ═══════════════════════════════════════════════════════════
    call_put_spread = df['call_resistance'] - df['put_support']
    mid_in_spread = safe_divide(
        df['mid'] - df['put_support'],
        call_put_spread,
        default=0.5
    )
    df['options_directional_pressure'] = mid_in_spread * df['volume'] / 100
    
    return df


if __name__ == "__main__":
    print("✅ Module GEX interactions chargé")
    print("   10 nouvelles features disponibles:")
    print("   1. gex_delta_momentum")
    print("   2. gex_volume_intensity")
    print("   3. gex_vwap_context")
    print("   4. gex_volatility_adjusted")
    print("   5. call_delta_pressure")
    print("   6. put_delta_pressure")
    print("   7. hvl_delta_regime")
    print("   8. blind_institutional_trap")
    print("   9. gex_wall_confluence")
    print("   10. options_directional_pressure")

