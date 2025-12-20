"""
🔧 FEATURE ENGINEERING - LightGBM ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Transforme snapshots ML_READY (bruts) en features ML-ready pour LightGBM.

INPUT: 70 features brutes depuis snapshot
OUTPUT: 100 features (70 brutes + 30 engineered)

Features engineered:
- 10 Ratios (delta_intensity, depth_imbalance_ratio, etc.)
- 10 Interactions (layer1_layer2, blind_gex_confluence, etc.)
- 10 Interactions GEX avancées (gex_delta_momentum, call_delta_pressure, etc.)
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# ✅ CORRIGÉ: Import module GEX interactions
# Note: Utiliser importlib car le nom du module commence par un chiffre (3_FEATURES)
try:
    import importlib
    gex_interactions_module = importlib.import_module('ml.3_FEATURES.gex_interactions')
    add_gex_interactions = gex_interactions_module.add_gex_interactions
    GEX_INTERACTIONS_AVAILABLE = True
except (ImportError, AttributeError) as e:
    GEX_INTERACTIONS_AVAILABLE = False
    logger.warning(f"⚠️ Module gex_interactions non disponible: {e}")

# ✅ CORRIGÉ: Import MenthorQZoneTransformer pour features de zones
# Note: Utiliser importlib car le nom du module commence par un chiffre (3_FEATURES)
try:
    import importlib
    menthorq_zone_module = importlib.import_module('ml.3_FEATURES.menthorq_zone_transformer')
    MenthorQZoneTransformer = menthorq_zone_module.MenthorQZoneTransformer
    ZONE_TRANSFORMER_AVAILABLE = True
except (ImportError, AttributeError) as e:
    ZONE_TRANSFORMER_AVAILABLE = False
    logger.warning(f"⚠️ MenthorQZoneTransformer non disponible: {e}")


class FeatureEngineer:
    """
    Crée features avancées pour LightGBM depuis snapshots ML_READY.

    Usage:
        engineer = FeatureEngineer()
        df_features = engineer.engineer_features(df_snapshots)
    """

    def __init__(self):
        """Initialise le feature engineer."""

        # Liste des 70 features brutes à extraire du snapshot
        self.CORE_FEATURES = [
            # ═══════════════════════════════════════════════════
            # OPTIONS (Layer 1) - 20 features
            # ═══════════════════════════════════════════════════
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
            'call_resistance', 'put_support', 'hvl',
            'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
            'menthorq_impact_score', 'menthorq_proximity_strength',
            'confluence_strength', 'confluence_density', 'confluence_proximity',
            'vix', 'volatility_regime', 'atr_ratio',
            'gamma_wall_level',

            # ═══════════════════════════════════════════════════
            # ORDERFLOW (Layer 2) - 15 features
            # ═══════════════════════════════════════════════════
            'delta', 'cum_delta_day', 'cum_delta_session',
            'deltaPct', 'smart_money_flow', 'institutional_pressure',
            'volume', 'bidvol', 'askvol',
            'bidPct', 'askPct',
            'depth_bid', 'depth_ask', 'depth_imbalance',
            'dom_age_ms',

            # ═══════════════════════════════════════════════════
            # CONTEXT (Layer 3) - 12 features
            # ═══════════════════════════════════════════════════
            'vwap', 'd_vwap', 'd_vwap_ticks', 'd_vwap_atr',
            'atr', 'volatility_regime_cont',
            'session_progress', 'session_elapsed_s',
            'mid', 'spread_ticks', 'microprice', 'microgap_n',

            # ═══════════════════════════════════════════════════
            # ADVANCED - 8 features
            # ═══════════════════════════════════════════════════
            '1d_max', '1d_min',
            'd_vpoc_ticks', 'd_vah_ticks',

            # ═══════════════════════════════════════════════════
            # ENGINEERED DISPONIBLES - 10 features
            # ═══════════════════════════════════════════════════
            'level1_imbalance', 'micro_imb',
            'corr',
            'mia_bullish_score',
            'distance_to_high_pct', 'distance_to_low_pct',
            'position_in_range',
            'tick_rate_1s', 'tick_rate_3s',
            'pressure_strength',

            # ═══════════════════════════════════════════════════
            # FEATURES CONTEXTUELLES (pour calculs) - 5 features
            # ═══════════════════════════════════════════════════
            'next_wall_dist_ticks', 'next_wall_strength',
        ]

        # Features de métadonnées (pas pour ML, juste tracking)
        self.META_FEATURES = [
            'symbol_base', 'date', 't_ms', 'sym'
        ]

        # ✅ CORRIGÉ: Initialiser MenthorQZoneTransformer pour features de zones
        if ZONE_TRANSFORMER_AVAILABLE:
            self.zone_transformer = MenthorQZoneTransformer()
            logger.info("✅ MenthorQZoneTransformer initialisé")
        else:
            self.zone_transformer = None
            logger.warning("⚠️ MenthorQZoneTransformer non disponible - features zones manquantes")

        logger.info("✅ FeatureEngineer initialisé")
        logger.info(f"   Core features: {len(self.CORE_FEATURES)}")


    def _safe_divide(self, numerator: pd.Series, denominator: pd.Series, default: float = 0.0) -> pd.Series:
        """Division sécurisée (évite division par zéro)."""
        return np.where(denominator != 0, numerator / denominator, default)


    def _create_ratio_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Crée 10 features de type RATIO.

        Args:
            df: DataFrame avec features brutes

        Returns:
            DataFrame avec features ratio ajoutées
        """

        logger.info("🔧 Création features RATIO (10)...")

        # ═══════════════════════════════════════════════════════
        # RATIO #1: Delta Intensity
        # ═══════════════════════════════════════════════════════
        df['delta_intensity'] = self._safe_divide(
            df['delta'].abs(),
            df['volume'],
            default=0.0
        )

        # ═══════════════════════════════════════════════════════
        # RATIO #2: Depth Imbalance Ratio
        # ═══════════════════════════════════════════════════════
        df['depth_imbalance_ratio'] = self._safe_divide(
            df['depth_bid'],
            df['depth_ask'],
            default=1.0
        )

        # ═══════════════════════════════════════════════════════
        # RATIO #3: VWAP ATR Ratio
        # ═══════════════════════════════════════════════════════
        atr_ticks = self._safe_divide(df['atr'], 0.25, default=20)
        df['vwap_atr_ratio'] = self._safe_divide(
            df['d_vwap_ticks'],
            atr_ticks,
            default=0.0
        )

        # ═══════════════════════════════════════════════════════
        # RATIO #4: Gamma Position
        # ═══════════════════════════════════════════════════════
        df['gamma_position'] = self._safe_divide(
            (df['mid'] - df['hvl']),
            df['atr'],
            default=0.0
        )

        # ═══════════════════════════════════════════════════════
        # RATIO #5: Flow Direction
        # ═══════════════════════════════════════════════════════
        df['flow_direction'] = df['bidPct'] - df['askPct']

        # ═══════════════════════════════════════════════════════
        # RATIO #6: GEX Proximity Min
        # ═══════════════════════════════════════════════════════
        gex_cols = ['gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5']
        gex_distances = []
        for col in gex_cols:
            if col in df.columns:
                gex_distances.append((df['mid'] - df[col]).abs())

        if gex_distances:
            df['gex_proximity_min'] = pd.concat(gex_distances, axis=1).min(axis=1)
        else:
            df['gex_proximity_min'] = 9999.0

        # ═══════════════════════════════════════════════════════
        # RATIO #7: Range Bias (1D)
        # ═══════════════════════════════════════════════════════
        # Extraire distances depuis menthor_distances si nested dict
        if 'dist_1d_min' in df.columns and 'dist_1d_max' in df.columns:
            dist_1d_min = df['dist_1d_min'].abs()
            dist_1d_max = df['dist_1d_max'].abs()
        else:
            dist_1d_min = (df['mid'] - df['1d_min']).abs() / 0.25
            dist_1d_max = (df['1d_max'] - df['mid']).abs() / 0.25

        df['range_bias'] = self._safe_divide(
            dist_1d_min,
            (dist_1d_min + dist_1d_max),
            default=0.5
        )

        # ═══════════════════════════════════════════════════════
        # RATIO #8: Efficiency Ratio (placeholder - calculé post-trade)
        # ═══════════════════════════════════════════════════════
        # Note: Cette feature sera calculée après simulation trade
        df['efficiency_ratio_placeholder'] = 0.0

        # ═══════════════════════════════════════════════════════
        # RATIO #9: DOM Slope Ratio
        # ═══════════════════════════════════════════════════════
        # Extraire depuis dom_features si nested dict
        if 'slope_bid_1_3' in df.columns and 'slope_ask_1_3' in df.columns:
            df['dom_slope_ratio'] = self._safe_divide(
                df['slope_bid_1_3'],
                df['slope_ask_1_3'],
                default=1.0
            )
        else:
            df['dom_slope_ratio'] = 1.0  # Fallback

        # ═══════════════════════════════════════════════════════
        # RATIO #10: Confluence Delta
        # ═══════════════════════════════════════════════════════
        df['confluence_delta'] = df['confluence_strength'] * df['deltaPct'].abs()

        logger.info(f"   ✅ 10 features RATIO créées")

        return df


    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Crée 10 features de type INTERACTION.

        Args:
            df: DataFrame avec features brutes + ratios

        Returns:
            DataFrame avec features interaction ajoutées
        """

        logger.info("🔧 Création features INTERACTION (10)...")

        # ═══════════════════════════════════════════════════════
        # INTERACTION #1: Layer1 × Layer2
        # ═══════════════════════════════════════════════════════
        df['layer1_layer2_interaction'] = (
            df['menthorq_impact_score'] * df['depth_imbalance']
        )

        # ═══════════════════════════════════════════════════════
        # INTERACTION #2: Next Wall Weighted
        # ═══════════════════════════════════════════════════════
        df['next_wall_weighted'] = self._safe_divide(
            df['next_wall_strength'],
            df['next_wall_dist_ticks'].abs() + 1,  # +1 évite div/0
            default=0.0
        )

        # ═══════════════════════════════════════════════════════
        # INTERACTION #3: Blind Spot × GEX Confluence (placeholder)
        # ═══════════════════════════════════════════════════════
        # Note: blind_spot_weight et gex_weight viennent des TODOs #7/#8
        # Si pas disponibles, on utilise proximity
        if 'blind_spot_weight' in df.columns and 'gex_weight' in df.columns:
            df['blind_gex_confluence'] = df['blind_spot_weight'] * df['gex_weight']
        else:
            # Approximation basée sur proximité
            blind_proximity = 1.0 / (df['gex_proximity_min'] / 10 + 1)  # Inverse proximity
            df['blind_gex_confluence'] = blind_proximity * df['confluence_strength']

        # ═══════════════════════════════════════════════════════
        # INTERACTION #4: VWAP × HVL Regime
        # ═══════════════════════════════════════════════════════
        # Encoder régimes en numérique
        vwap_regime_map = {
            'EXTREME_OVERSOLD': -2,
            'OVERSOLD': -1,
            'NEUTRAL': 0,
            'OVERBOUGHT': 1,
            'EXTREME_OVERBOUGHT': 2
        }

        if 'vwap_regime' in df.columns:
            df['vwap_regime_encoded'] = df['vwap_regime'].map(vwap_regime_map).fillna(0)
        else:
            # Approximation depuis d_vwap_atr
            df['vwap_regime_encoded'] = np.where(
                df['d_vwap_atr'] < -10, -2,
                np.where(df['d_vwap_atr'] < -5, -1,
                np.where(df['d_vwap_atr'] > 10, 2,
                np.where(df['d_vwap_atr'] > 5, 1, 0)))
            )

        hvl_regime_map = {'negative_gamma': -1, 'positive_gamma': 1}

        if 'hvl_regime' in df.columns:
            df['hvl_regime_encoded'] = df['hvl_regime'].map(hvl_regime_map).fillna(0)
        else:
            # Approximation: mid > hvl = positive gamma
            df['hvl_regime_encoded'] = np.where(df['mid'] > df['hvl'], 1, -1)

        df['vwap_hvl_regime'] = df['vwap_regime_encoded'] * df['hvl_regime_encoded']

        # ═══════════════════════════════════════════════════════
        # INTERACTION #5: Delta Session Ratio
        # ═══════════════════════════════════════════════════════
        df['delta_session_ratio'] = self._safe_divide(
            df['delta'],
            df['cum_delta_session'].abs() + 1,  # +1 évite div/0
            default=0.0
        )

        # ═══════════════════════════════════════════════════════
        # INTERACTION #6: Volume × ATR Intensity
        # ═══════════════════════════════════════════════════════
        df['volume_atr_intensity'] = df['volume'] * df['atr_ratio']

        # ═══════════════════════════════════════════════════════
        # INTERACTION #7: Approaching 1D Max (binary)
        # ═══════════════════════════════════════════════════════
        if 'dist_1d_max' in df.columns:
            dist_1d_max = df['dist_1d_max'].abs()
        else:
            dist_1d_max = (df['1d_max'] - df['mid']).abs() / 0.25

        df['approaching_1d_max'] = np.where(dist_1d_max < 50, 1, 0)

        # ═══════════════════════════════════════════════════════
        # INTERACTION #8: Approaching 1D Min (binary)
        # ═══════════════════════════════════════════════════════
        if 'dist_1d_min' in df.columns:
            dist_1d_min = df['dist_1d_min'].abs()
        else:
            dist_1d_min = (df['mid'] - df['1d_min']).abs() / 0.25

        df['approaching_1d_min'] = np.where(dist_1d_min < 50, 1, 0)

        # ═══════════════════════════════════════════════════════
        # INTERACTION #9: Range Expansion
        # ═══════════════════════════════════════════════════════
        df['range_expansion'] = self._safe_divide(
            (df['1d_max'] - df['1d_min']),
            df['atr'],
            default=1.0
        )

        # ═══════════════════════════════════════════════════════
        # INTERACTION #10: VIX × ATR Volatility
        # ═══════════════════════════════════════════════════════
        df['vix_atr_volatility'] = df['vix'] * df['atr_ratio']

        logger.info(f"   ✅ 10 features INTERACTION créées")

        # ═══════════════════════════════════════════════════════════
        # NOUVELLES INTERACTIONS GEX (10 features) - 15 NOV 2025
        # ═══════════════════════════════════════════════════════════
        if GEX_INTERACTIONS_AVAILABLE:
            logger.info(f"   🔧 Ajout des 10 interactions GEX avancées...")
            df = add_gex_interactions(df)
            logger.info(f"   ✅ 10 features GEX INTERACTIONS créées")
        else:
            logger.warning(f"   ⚠️ Module gex_interactions non disponible, skip")

        return df


    def _flatten_nested_dict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplatit les dictionnaires nested dans le snapshot.

        Exemples:
        - menthor_distances.dist_1d_max → dist_1d_max
        - dom_features.slope_bid_1_3 → slope_bid_1_3
        - next_wall.dist_ticks → next_wall_dist_ticks
        """

        # Nested fields communs
        nested_mappings = {
            # menthor_distances
            'menthor_distances': ['dist_1d_max', 'dist_1d_min'],
            # dom_features - ✅ CORRIGÉ: Ajout de depth_bid et depth_ask
            'dom_features': ['slope_bid_1_3', 'slope_ask_1_3', 'imbalance_1_3', 'depth_bid', 'depth_ask', 'depth_imbalance'],
            # next_wall
            'next_wall': ['dist_ticks', 'strength', 'side']
        }

        for parent_key, child_keys in nested_mappings.items():
            if parent_key in df.columns:
                # Extraire nested dict
                for idx, row in df.iterrows():
                    parent_val = row[parent_key]
                    if isinstance(parent_val, dict):
                        for child_key in child_keys:
                            # ✅ CORRIGÉ: Pour dom_features, extraire directement au niveau racine (depth_bid, depth_ask)
                            # Pour next_wall, utiliser le préfixe next_wall_
                            if parent_key == 'dom_features' and child_key in ['depth_bid', 'depth_ask', 'depth_imbalance']:
                                # Extraire directement au niveau racine (pas de préfixe dom_features_)
                                col_name = child_key
                            elif parent_key == 'next_wall':
                                col_name = f"next_wall_{child_key}"
                            else:
                                col_name = f"{parent_key}_{child_key}"

                            if col_name not in df.columns:
                                df.at[idx, col_name] = parent_val.get(child_key, 0)

        return df


    def engineer_features(
        self,
        df_snapshots: pd.DataFrame,
        include_meta: bool = True
    ) -> pd.DataFrame:
        """
        Transforme snapshots bruts en features ML-ready (90 features).

        Args:
            df_snapshots: DataFrame des snapshots ML_READY
            include_meta: Si True, inclut features métadonnées

        Returns:
            DataFrame avec 90 features (70 brutes + 20 engineered)
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"🔧 FEATURE ENGINEERING")
        logger.info(f"{'='*70}")
        logger.info(f"   Input snapshots: {len(df_snapshots):,}")
        logger.info(f"   Input features: {len(df_snapshots.columns)}")
        logger.info(f"{'='*70}\n")

        df = df_snapshots.copy()

        # ═══════════════════════════════════════════════════════
        # 1. Aplatir nested dicts
        # ═══════════════════════════════════════════════════════
        logger.info("📋 Aplatissement nested dictionaries...")
        df = self._flatten_nested_dict(df)

        # ═══════════════════════════════════════════════════════
        # 2. Sélectionner 70 core features
        # ═══════════════════════════════════════════════════════
        logger.info("📋 Extraction 70 core features...")

        available_features = [f for f in self.CORE_FEATURES if f in df.columns]
        missing_features = [f for f in self.CORE_FEATURES if f not in df.columns]

        if missing_features:
            logger.warning(f"⚠️ {len(missing_features)} features manquantes (remplacées par 0):")
            for feat in missing_features[:10]:  # Afficher max 10
                logger.warning(f"   - {feat}")
            if len(missing_features) > 10:
                logger.warning(f"   ... et {len(missing_features)-10} autres")

            # Ajouter features manquantes avec valeur par défaut
            for feat in missing_features:
                df[feat] = 0.0

        logger.info(f"   ✅ {len(available_features)}/{len(self.CORE_FEATURES)} core features disponibles")

        # ═══════════════════════════════════════════════════════
        # 3. Créer 20 features engineered
        # ═══════════════════════════════════════════════════════
        df = self._create_ratio_features(df)
        df = self._create_interaction_features(df)

        # ═══════════════════════════════════════════════════════
        # 4. Créer 15 features de zones MenthorQ
        # ═══════════════════════════════════════════════════════
        if self.zone_transformer:
            logger.info("🔧 Création features ZONES MenthorQ (15)...")
            df = self.zone_transformer.transform_all(df)
            logger.info(f"   ✅ 15 features ZONES créées")
        else:
            logger.warning("⚠️ Zone transformer non disponible - features zones manquantes")
            # Créer features zones avec valeurs par défaut
            default_zone_features = [
                'in_gex_zone', 'closest_gex_proximity', 'gex_count_nearby', 'gex_sandwich',
                'in_blind_zone', 'closest_blind_proximity', 'blind_count_nearby',
                'in_hvl_zone', 'hvl_proximity', 'hvl_side',
                'in_call_zone', 'call_proximity', 'in_put_zone', 'put_proximity', 'in_strike_sandwich'
            ]
            for feat in default_zone_features:
                if feat not in df.columns:
                    df[feat] = 0.0

        # ═══════════════════════════════════════════════════════
        # 5. Ajouter features ML manquantes (depuis snapshot ou defaults)
        # ═══════════════════════════════════════════════════════
        # confluence: depuis snapshot ou calculée depuis confluence_strength
        if 'confluence' not in df.columns:
            df['confluence'] = df.get('confluence_strength', 0.0)

        # layer1_confidence: depuis snapshot ou 0.0 (sera rempli par ML 3-Layer)
        if 'layer1_confidence' not in df.columns:
            df['layer1_confidence'] = 0.0

        # ml_confidence: depuis snapshot ou 0.0 (sera rempli par ML 3-Layer)
        if 'ml_confidence' not in df.columns:
            df['ml_confidence'] = 0.0

        # ═══════════════════════════════════════════════════════
        # 6. Sélectionner features finales (111 total: 63 core + 30 engineered + 15 zones + 3 ML)
        # ═══════════════════════════════════════════════════════
        engineered_features = [
            # Ratios (10)
            'delta_intensity', 'depth_imbalance_ratio', 'vwap_atr_ratio',
            'gamma_position', 'flow_direction', 'gex_proximity_min',
            'range_bias', 'efficiency_ratio_placeholder', 'dom_slope_ratio',
            'confluence_delta',
            # Interactions (10)
            'layer1_layer2_interaction', 'next_wall_weighted', 'blind_gex_confluence',
            'vwap_hvl_regime', 'delta_session_ratio', 'volume_atr_intensity',
            'approaching_1d_max', 'approaching_1d_min', 'range_expansion',
            'vix_atr_volatility',
            # GEX Interactions (10) - ✅ AJOUTÉ: Features GEX avancées
            'gex_delta_momentum', 'gex_volume_intensity', 'gex_vwap_context',
            'gex_volatility_adjusted', 'call_delta_pressure', 'put_delta_pressure',
            'hvl_delta_regime', 'blind_institutional_trap', 'gex_wall_confluence',
            'options_directional_pressure'
        ]

        # ✅ CORRIGÉ: Ajouter features de zones (15)
        if self.zone_transformer:
            zone_features = self.zone_transformer.get_zone_features()
        else:
            zone_features = [
                'in_gex_zone', 'closest_gex_proximity', 'gex_count_nearby', 'gex_sandwich',
                'in_blind_zone', 'closest_blind_proximity', 'blind_count_nearby',
                'in_hvl_zone', 'hvl_proximity', 'hvl_side',
                'in_call_zone', 'call_proximity', 'in_put_zone', 'put_proximity', 'in_strike_sandwich'
            ]

        # ✅ CORRIGÉ: Ajouter features ML (3)
        ml_features = ['confluence', 'layer1_confidence', 'ml_confidence']

        final_features = self.CORE_FEATURES + engineered_features + zone_features + ml_features

        if include_meta:
            final_features = self.META_FEATURES + final_features

        # Sélectionner colonnes (créer si manquantes)
        for feat in final_features:
            if feat not in df.columns:
                df[feat] = 0.0

        df_final = df[final_features].copy()

        # ═══════════════════════════════════════════════════════
        # 5. Gestion valeurs manquantes
        # ═══════════════════════════════════════════════════════
        missing_counts = df_final.isnull().sum()
        if missing_counts.sum() > 0:
            logger.warning(f"⚠️ Valeurs manquantes détectées:")
            for col, count in missing_counts[missing_counts > 0].items():
                logger.warning(f"   {col}: {count} ({count/len(df_final)*100:.1f}%)")

            # Remplacer NaN par 0 (stratégie conservatrice)
            df_final = df_final.fillna(0.0)
            logger.info("   ✅ Valeurs manquantes remplacées par 0")

        # ═══════════════════════════════════════════════════════
        # 6. Résultat final
        # ═══════════════════════════════════════════════════════
        # ✅ CORRIGÉ: Compter les features GEX séparément si disponibles
        gex_features = [
            'gex_delta_momentum', 'gex_volume_intensity', 'gex_vwap_context',
            'gex_volatility_adjusted', 'call_delta_pressure', 'put_delta_pressure',
            'hvl_delta_regime', 'blind_institutional_trap', 'gex_wall_confluence',
            'options_directional_pressure'
        ]
        gex_count = sum(1 for f in gex_features if f in df_final.columns)
        base_engineered_count = len(engineered_features) - len(gex_features)  # 20 features de base

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ FEATURE ENGINEERING TERMINÉ")
        logger.info(f"{'='*70}")
        logger.info(f"   Output snapshots: {len(df_final):,}")
        logger.info(f"   Output features: {len(df_final.columns)}")
        logger.info(f"   - Meta: {len(self.META_FEATURES) if include_meta else 0}")
        logger.info(f"   - Core brutes: {len(self.CORE_FEATURES)}")
        logger.info(f"   - Engineered: {base_engineered_count} (ratios + interactions)")
        if gex_count > 0:
            logger.info(f"   - GEX Interactions: {gex_count}")
        logger.info(f"   - Zones MenthorQ: {len(zone_features)}")
        logger.info(f"   - ML features: {len(ml_features)}")
        total_expected = len(self.CORE_FEATURES) + base_engineered_count + gex_count + len(zone_features) + len(ml_features)
        logger.info(f"   - TOTAL ML features: {len(self.CORE_FEATURES)} + {base_engineered_count} + {gex_count} + {len(zone_features)} + {len(ml_features)} = {total_expected} ✅")
        logger.info(f"{'='*70}\n")

        return df_final


# ═══════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Feature engineering sur données ML_READY."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # ═══════════════════════════════════════════════════════════
    # CHARGEMENT DONNÉES
    # ═══════════════════════════════════════════════════════════

    INPUT_PATH = "ml/data/ml_ready_aggregated.parquet"
    OUTPUT_PATH = "ml/data/ml_features_engineered.parquet"

    logger.info(f"📂 Chargement données: {INPUT_PATH}")

    if not Path(INPUT_PATH).exists():
        logger.error(f"❌ Fichier non trouvé: {INPUT_PATH}")
        logger.error("   Exécutez d'abord: python ml/extract_ml_ready_data.py")
        exit(1)

    df_snapshots = pd.read_parquet(INPUT_PATH)
    logger.info(f"✅ {len(df_snapshots):,} snapshots chargés\n")

    # ═══════════════════════════════════════════════════════════
    # FEATURE ENGINEERING
    # ═══════════════════════════════════════════════════════════

    engineer = FeatureEngineer()

    df_features = engineer.engineer_features(
        df_snapshots=df_snapshots,
        include_meta=True
    )

    # ═══════════════════════════════════════════════════════════
    # SAUVEGARDE
    # ═══════════════════════════════════════════════════════════

    output_file = Path(OUTPUT_PATH)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    df_features.to_parquet(OUTPUT_PATH, engine='pyarrow', compression='snappy', index=False)

    file_size = output_file.stat().st_size / (1024 * 1024)

    logger.info(f"💾 Features engineered sauvegardées:")
    logger.info(f"   Fichier: {OUTPUT_PATH}")
    logger.info(f"   Taille: {file_size:.2f} MB")
    logger.info(f"   Snapshots: {len(df_features):,}")
    logger.info(f"   Features: {len(df_features.columns)}")

    logger.info("\n✅ Feature engineering terminé avec succès !")
