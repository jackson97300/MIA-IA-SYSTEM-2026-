
    Usage:
        engineer = FeatureEngineer(
            lag_periods=[1, 5, 10, 20, 60],
            rolling_windows=[20, 60, 180]  # ✅ R1 GPT: 300→180s (anti-leak)
        )

        df = engineer.add_lags(df, ['close', 'delta', 'level1_imbalance'])
        df = engineer.add_rolling_means(df, ['close', 'delta'])
    """

    def __init__(
        self,
        lag_periods: Optional[List[int]] = None,
        rolling_windows: Optional[List[int]] = None
    ):
        """
        Initialise le FeatureEngineer

        Args:
            lag_periods: Périodes de LAG en secondes (défaut: [1,5,10,20,60])
            rolling_windows: Fenêtres rolling en secondes (défaut: [20,60,180])  # ✅ R1: Réduit de 300→180s
        """
        self.lag_periods = lag_periods or [1, 5, 10, 20, 60]
        self.rolling_windows = rolling_windows or [20, 60, 180]  # ✅ R1 GPT: Anti-leak (horizon=900s, 180s=900/5)

        logger.info(f"FeatureEngineer initialisé :")
        logger.info(f"  LAG periods : {self.lag_periods}")
        logger.info(f"  Rolling windows : {self.rolling_windows}")

    def add_lags(
        self,
        df: pd.DataFrame,
        feature_names: List[str],
        fill_method: str = 'ffill',
        time_col: str = 'tsec',
        time_gap_tolerance: int = 60
    ) -> pd.DataFrame:
        """
        Ajoute des LAGs (valeurs historiques) pour chaque feature

        Args:
            df: DataFrame
            feature_names: Liste des features à lag
            fill_method: Méthode de remplissage NaN ('ffill', 'bfill', None)
            time_col: Colonne timestamp pour tri et gaps
            time_gap_tolerance: Tolérance gap temporel (secondes)

        Returns:
            DataFrame avec colonnes LAG ajoutées
        """
        logger.info(f"\n🔄 Ajout LAGs pour {len(feature_names)} features...")

        # ✅ CORRECTIF GPT : Tri et détection gaps
        if time_col in df.columns:
            # Forcer tri chronologique
            if not df[time_col].is_monotonic_increasing:
                logger.info(f"   📊 Tri chronologique par {time_col}...")
                df = df.sort_values(time_col).reset_index(drop=True)

            # Détecter gaps temporels
            time_diff = df[time_col].diff()
            gaps = time_diff[time_diff > time_gap_tolerance]
            if len(gaps) > 0:
                logger.warning(f"   ⚠️ {len(gaps)} gaps temporels > {time_gap_tolerance}s détectés")
                logger.warning(f"   → Les LAGs seront invalidés autour des gaps")
        else:
            logger.warning(f"   ⚠️ Colonne {time_col} introuvable, pas de vérification gaps")

        n_na_before = df.isna().sum().sum()

        for feature in feature_names:
            if feature not in df.columns:
                logger.warning(f"⚠️  Feature '{feature}' non trouvée, skip")
                continue

            for lag in self.lag_periods:
                lag_col_name = f"{feature}_lag_{lag}"
                df[lag_col_name] = df[feature].shift(lag)

                # ✅ CORRECTIF GPT : Invalider LAGs autour des gaps
                if time_col in df.columns and len(gaps) > 0:
                    for gap_idx in gaps.index:
                        # Invalider LAG si il traverse un gap
                        affected_range = range(max(0, gap_idx - lag), min(len(df), gap_idx + 1))
                        df.loc[list(affected_range), lag_col_name] = np.nan

                # ✅ CORRECTIF A: Remplir NaN si demandé (après invalidation gaps)
                if fill_method == 'ffill':
                    df[lag_col_name] = df[lag_col_name].ffill()  # Remplace fillna(method='ffill')
                elif fill_method == 'bfill':
                    df[lag_col_name] = df[lag_col_name].bfill()  # Remplace fillna(method='bfill')

        n_na_after = df.isna().sum().sum()
        n_na_created = n_na_after - n_na_before
        pct_na = (n_na_created / (len(df) * len(feature_names) * len(self.lag_periods))) * 100 if len(df) > 0 else 0

        n_lag_features = len(feature_names) * len(self.lag_periods)
        logger.info(f"✅ {n_lag_features} features LAG créées")
        logger.info(f"   📊 NaN créés : {n_na_created:,} ({pct_na:.1f}% des LAGs)")

        return df

    def add_rolling_means(
        self,
        df: pd.DataFrame,
        feature_names: List[str],
        add_distance: bool = True,
        add_slope: bool = True,
        min_periods: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Ajoute des Rolling Means (moyennes mobiles) pour chaque feature

        Args:
            df: DataFrame
            feature_names: Liste des features
            add_distance: Ajouter distance à la moyenne (feature - ma)
            add_slope: Ajouter slope de la moyenne (ma - ma_prev)
            min_periods: Minimum de périodes pour calcul (défaut: window_size)

        Returns:
            DataFrame avec colonnes Rolling ajoutées
        """
        logger.info(f"\n📊 Ajout Rolling Means pour {len(feature_names)} features...")

        # ✅ CORRECTIF GPT : Log % NaN créés par rolling
        n_na_before = df.isna().sum().sum()

        # ✅ CORRECTIF PerformanceWarning : Collecter toutes les colonnes avant ajout
        new_columns = {}

        for feature in feature_names:
            if feature not in df.columns:
                logger.warning(f"⚠️  Feature '{feature}' non trouvée, skip")
                continue

            for window in self.rolling_windows:
                # ✅ CORRECTIF CRITIQUE : Éviter fuite temporelle - shift(1) avant rolling
                # Utiliser la valeur précédente pour éviter d'inclure la barre courante
                feature_lag = df[feature].shift(1)

                # Moyenne mobile
                ma_col_name = f"{feature}_ma_{window}"
                new_columns[ma_col_name] = feature_lag.rolling(
                    window=window,
                    min_periods=min_periods or window
                ).mean()

                # Distance à la moyenne (feature - ma)
                if add_distance:
                    dist_col_name = f"{feature}_vs_ma_{window}"
                    new_columns[dist_col_name] = df[feature] - new_columns[ma_col_name]

                    # Version pourcentage (pour certaines features)
                    if feature in ['close', 'mid', 'vwap', 'vpoc']:
                        pct_col_name = f"{feature}_vs_ma_{window}_pct"
                        # Éviter division par zéro
                        new_columns[pct_col_name] = ((df[feature] / (new_columns[ma_col_name] + 1e-9)) - 1) * 100

                # Slope de la moyenne (changement)
                if add_slope:
                    slope_col_name = f"{feature}_ma_{window}_slope"
                    # Slope = ma actuelle - ma il y a 10% de window
                    slope_window = max(1, window // 10)
                    new_columns[slope_col_name] = new_columns[ma_col_name] - new_columns[ma_col_name].shift(slope_window)

        # ✅ CORRECTIF PerformanceWarning : Ajouter toutes les colonnes en une seule fois
        if new_columns:
            df = pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)

        # ✅ CORRECTIF GPT : Logger statistiques NaN (après ajout des colonnes)
        n_na_after = df.isna().sum().sum()
        n_na_created = n_na_after - n_na_before

        # Compter features créées (déjà comptées dans new_columns)
        n_ma_features = len(new_columns)

        pct_na = (n_na_created / (len(df) * n_ma_features)) * 100 if len(df) > 0 and n_ma_features > 0 else 0

        logger.info(f"✅ {n_ma_features} features Rolling créées")
        logger.info(f"   📊 NaN créés : {n_na_created:,} ({pct_na:.1f}% des Rolling)")

        return df

    def add_momentum_features(
        self,
        df: pd.DataFrame,
        feature_names: List[str],
        windows: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Ajoute des features de momentum (changements sur plusieurs périodes)

        Args:
            df: DataFrame
            feature_names: Liste des features
            windows: Fenêtres de calcul (défaut: lag_periods)

        Returns:
            DataFrame avec features momentum
        """
        windows = windows or self.lag_periods

        logger.info(f"\n⚡ Ajout Momentum features pour {len(feature_names)} features...")

        for feature in feature_names:
            if feature not in df.columns:
                continue

            for window in windows:
                # Changement absolu
                change_col = f"{feature}_change_{window}"
                df[change_col] = df[feature] - df[feature].shift(window)

                # Changement relatif (pct)
                if feature in ['close', 'mid', 'vwap', 'volume']:
                    pct_change_col = f"{feature}_pct_change_{window}"
                    df[pct_change_col] = df[feature].pct_change(periods=window) * 100

        logger.info(f"✅ Momentum features créées")

        return df

    def add_volatility_features(
        self,
        df: pd.DataFrame,
        feature_names: List[str],
        windows: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Ajoute des features de volatilité (std, range)

        Args:
            df: DataFrame
            feature_names: Liste des features
            windows: Fenêtres de calcul (défaut: rolling_windows)

        Returns:
            DataFrame avec features volatilité
        """
        windows = windows or self.rolling_windows

        logger.info(f"\n📉 Ajout Volatilité features pour {len(feature_names)} features...")

        for feature in feature_names:
            if feature not in df.columns:
                continue

            for window in windows:
                # Écart-type
                std_col = f"{feature}_std_{window}"
                df[std_col] = df[feature].rolling(window=window).std()

                # Range (max - min)
                range_col = f"{feature}_range_{window}"
                df[range_col] = (
                    df[feature].rolling(window=window).max() -
                    df[feature].rolling(window=window).min()
                )

        logger.info(f"✅ Volatilité features créées")

        return df

    def add_ratio_features(
        self,
        df: pd.DataFrame,
        numerator_features: List[str],
        denominator_features: List[str]
    ) -> pd.DataFrame:
        """
        Ajoute des ratios entre features

        Args:
            df: DataFrame
            numerator_features: Features numérateur
            denominator_features: Features dénominateur

        Returns:
            DataFrame avec ratios
        """
        logger.info(f"\n➗ Ajout Ratio features...")

        n_ratios = 0
        for num_feat in numerator_features:
            if num_feat not in df.columns:
                continue

            for denom_feat in denominator_features:
                if denom_feat not in df.columns:
                    continue

                if num_feat == denom_feat:
                    continue

                ratio_col = f"{num_feat}_div_{denom_feat}"

                # Éviter division par zéro
                df[ratio_col] = df[num_feat] / (df[denom_feat] + 1e-9)

                # Clipper valeurs extrêmes
                df[ratio_col] = df[ratio_col].clip(-1000, 1000)

                n_ratios += 1

        logger.info(f"✅ {n_ratios} Ratio features créées")

        return df

    def apply_all(
        self,
        df: pd.DataFrame,
        features_for_lags: List[str],
        features_for_rolling: List[str],
        features_for_momentum: Optional[List[str]] = None,
        features_for_volatility: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Applique toutes les transformations en une fois

        Args:
            df: DataFrame
            features_for_lags: Features pour LAGs
            features_for_rolling: Features pour Rolling
            features_for_momentum: Features pour Momentum (optionnel)
            features_for_volatility: Features pour Volatilité (optionnel)

        Returns:
            DataFrame transformé
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🔧 APPLICATION FEATURE ENGINEERING COMPLET")
        logger.info(f"{'='*70}")

        initial_cols = len(df.columns)

        # LAGs
        df = self.add_lags(df, features_for_lags)

        # Rolling Means
        df = self.add_rolling_means(df, features_for_rolling)

        # Momentum (optionnel)
        if features_for_momentum:
            df = self.add_momentum_features(df, features_for_momentum)

        # Volatilité (optionnel)
        if features_for_volatility:
            df = self.add_volatility_features(df, features_for_volatility)

        final_cols = len(df.columns)
        n_new_features = final_cols - initial_cols

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ FEATURE ENGINEERING TERMINÉ")
        logger.info(f"{'='*70}")
        logger.info(f"📊 Features initiales : {initial_cols}")
        logger.info(f"📊 Features finales : {final_cols}")
        logger.info(f"🆕 Nouvelles features : {n_new_features}")

        return df


class RealtimeFeatureCalculator:
    """
    Calculateur de features en temps réel pour production

    Maintient un buffer des N dernières valeurs pour calculer
    LAGs et Rolling Means sans DataFrame complet

    Usage:
        calculator = RealtimeFeatureCalculator(
            feature_names=['close', 'delta'],
            lag_periods=[1, 5, 10, 20, 60],
            rolling_windows=[20, 60, 180],  # ✅ R1 GPT: 300→180s (anti-leak)
            buffer_size=300
        )

        # À chaque nouveau snapshot
        features = calculator.update(ml_ready_snapshot)
    """

    def __init__(
        self,
        feature_names: List[str],
        lag_periods: List[int],
        rolling_windows: List[int],
        buffer_size: int = 300
    ):
        """
        Initialise le calculateur temps réel

        Args:
            feature_names: Features à tracker
            lag_periods: Périodes LAG
            rolling_windows: Fenêtres rolling
            buffer_size: Taille du buffer (max des windows)
        """
        self.feature_names = feature_names
        self.lag_periods = lag_periods
        self.rolling_windows = rolling_windows
        self.buffer_size = max(buffer_size, max(rolling_windows) + 10)

        # Buffer circulaire pour chaque feature
        self.buffers = {
            feat: np.full(self.buffer_size, np.nan)
            for feat in feature_names
        }

        self.current_idx = 0
        self.is_full = False

        logger.info(f"RealtimeFeatureCalculator initialisé :")
        logger.info(f"  Features : {len(feature_names)}")
        logger.info(f"  Buffer size : {self.buffer_size}")

    def update(self, ml_ready_snapshot: dict) -> dict:
        """
        Met à jour les buffers et calcule features dérivées

        Args:
            ml_ready_snapshot: Snapshot ML_READY actuel

        Returns:
            Dict avec toutes les features (brutes + dérivées)
        """
        # Extraire valeurs actuelles
        for feat in self.feature_names:
            if feat in ml_ready_snapshot:
                self.buffers[feat][self.current_idx] = ml_ready_snapshot[feat]

        # Calculer features dérivées
        derived_features = {}

        # LAGs
        for feat in self.feature_names:
            for lag in self.lag_periods:
                lag_idx = (self.current_idx - lag) % self.buffer_size

                if self.is_full or lag_idx < self.current_idx:
                    lag_value = self.buffers[feat][lag_idx]
                    derived_features[f"{feat}_lag_{lag}"] = lag_value

        # Rolling Means
        for feat in self.feature_names:
            for window in self.rolling_windows:
                if self.is_full or self.current_idx >= window:
                    # Extraire fenêtre
                    if self.is_full:
                        indices = [(self.current_idx - i) % self.buffer_size
                                  for i in range(window)]
                        values = self.buffers[feat][indices]
                    else:
                        start_idx = max(0, self.current_idx - window + 1)
                        values = self.buffers[feat][start_idx:self.current_idx + 1]

                    # Moyenne
                    ma = np.nanmean(values)
                    derived_features[f"{feat}_ma_{window}"] = ma

                    # Distance à la moyenne
                    current_value = self.buffers[feat][self.current_idx]
                    derived_features[f"{feat}_vs_ma_{window}"] = current_value - ma

                    # Slope (si assez de données)
                    slope_lag = max(1, window // 10)
                    if self.is_full or self.current_idx >= window + slope_lag:
                        slope_idx = (self.current_idx - slope_lag) % self.buffer_size
                        if self.is_full:
                            indices_prev = [(slope_idx - i) % self.buffer_size
                                           for i in range(window)]
                            values_prev = self.buffers[feat][indices_prev]
                        else:
                            start_idx_prev = max(0, slope_idx - window + 1)
                            values_prev = self.buffers[feat][start_idx_prev:slope_idx + 1]

                        ma_prev = np.nanmean(values_prev)
                        derived_features[f"{feat}_ma_{window}_slope"] = ma - ma_prev

        # Incrémenter index
        self.current_idx = (self.current_idx + 1) % self.buffer_size

        if self.current_idx == 0:
            self.is_full = True

        # Combiner features brutes + dérivées
        all_features = {**ml_ready_snapshot, **derived_features}

        return all_features

    def reset(self):
        """Reset les buffers"""
        for feat in self.feature_names:
            self.buffers[feat][:] = np.nan

        self.current_idx = 0
        self.is_full = False

        logger.info("RealtimeFeatureCalculator reset")


# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════

def get_recommended_features_for_engineering() -> dict:
    """
    Retourne les features recommandées pour feature engineering

    Returns:
        Dict avec listes de features par catégorie
    """
    return {
        'lags': [
            # Prix
            'close', 'mid',

            # OrderFlow
            'level1_imbalance', 'smart_money_flow',
            'cum_delta_session', 'delta', 'deltaPct',

            # VWAP (ENRICHI: d_vwap_weekly/monthly_ticks pour ancrage)
            'd_vwap', 'd_vpoc', 'd_vwap_weekly_ticks', 'd_vwap_monthly_ticks',

            # DOM
            'ob_center', 'depth_imbalance',

            # Gamma & MenthorQ (100% DONNEES) - Naming avec underscores (CORRIGÉ)
            'menthor_distances_call', 'menthor_distances_put',
            'menthor_distances_near_blind',
            # Menthor Distances (complément - variantes 0 et extrêmes jour)
            'menthor_distances_call0', 'menthor_distances_put0',
            'menthor_distances_gamma0', 'menthor_distances_hvl0',
            'menthor_distances_dist_1d_max', 'menthor_distances_dist_1d_min',
            # Next Wall (contexte complet)
            'next_wall_dist_ticks', 'next_wall_strength',
            'next_wall_dist_pts', 'next_wall_age_min',
            'gex_1', 'gex_2', 'gex_3',  # GEX principaux pour LAGs (prix absolus)
            'blind_spot_0', 'blind_spot_1',  # Blind spots principaux (prix absolus)
            # ✨ NOUVEAU : Distances OPTIONS dynamiques (LAGs critiques)
            'd_nearest_gex_up_ticks', 'd_nearest_gex_down_ticks', 'd_nearest_gex_abs_ticks',
            'd_nearest_blind_spot_abs_ticks',
            'd_call_resistance_ticks', 'd_put_support_ticks', 'd_hvl_ticks',
            'd_gex_1_ticks', 'd_gex_2_ticks', 'd_gex_3_ticks',  # Top 3 GEX en distance
            # Confluences/Proximités (IMPORTANTES)
            'menthorq_impact_score', 'menthorq_proximity_strength',
            'confluence_strength', 'confluence_density', 'confluence_proximity',
            'gamma_call_confluence', 'gamma_put_confluence',

            # Battle Navale
            'battle_navale_signal_strength',

            # Volume & Volatilité
            'pressure_strength', 'volatility_regime_cont',
        ],

        'rolling': [
            # Prix
            'close', 'mid',

            # OrderFlow
            'delta', 'smart_money_flow',
            'level1_imbalance',

            # VWAP (ENRICHI: d_vwap_weekly/monthly_ticks pour ancrage)
            'd_vwap', 'd_vwap_weekly_ticks', 'd_vwap_monthly_ticks',

            # Gamma & MenthorQ (100% DONNEES) - Naming avec underscores
            'menthor_distances_call', 'menthor_distances_put',
            # Menthor Distances (complément)
            'menthor_distances_call0', 'menthor_distances_put0',
            'menthor_distances_dist_1d_max', 'menthor_distances_dist_1d_min',
            # Next Wall (contexte)
            'next_wall_dist_pts', 'next_wall_age_min',
            'gex_1', 'gex_2', 'gex_3',  # GEX principaux pour rolling means (prix absolus)
            'blind_spot_0', 'blind_spot_1',  # Blind spots pour rolling (prix absolus)
            # ✨ NOUVEAU : Distances OPTIONS dynamiques (Rolling means critiques)
            'd_nearest_gex_up_ticks', 'd_nearest_gex_down_ticks', 'd_nearest_gex_abs_ticks',
            'd_nearest_blind_spot_abs_ticks',
            'd_call_resistance_ticks', 'd_put_support_ticks', 'd_hvl_ticks',
            # Confluences/Proximités (IMPORTANTES)
            'menthorq_impact_score', 'menthorq_proximity_strength',
            'confluence_strength', 'confluence_density', 'confluence_proximity',
            'gamma_call_confluence', 'gamma_put_confluence',

            # Battle Navale
            'battle_navale_signal_strength',

            # Volume
            'volume', 'pressure_strength',
        ],

        'momentum': [
            'close', 'delta', 'cum_delta_session',
            'level1_imbalance', 'd_vwap',
        ],

        'volatility': [
            'close', 'delta', 'volume',
        ]
    }


if __name__ == '__main__':
    """Test du module"""

    # Test avec données simulées
    import pandas as pd

    logger.info("🧪 Test FeatureEngineer")

    # Créer données test
    n_samples = 1000
    df_test = pd.DataFrame({
        'close': 6875 + np.random.randn(n_samples).cumsum() * 0.5,
        'delta': np.random.randn(n_samples) * 100,
        'level1_imbalance': np.random.randn(n_samples) * 0.1,
    })

    # Appliquer feature engineering
    engineer = FeatureEngineer(
        lag_periods=[1, 5, 10],
        rolling_windows=[20, 60]
    )

    df_test = engineer.apply_all(
        df_test,
        features_for_lags=['close', 'delta'],
        features_for_rolling=['close', 'delta'],
    )

    logger.info(f"\n✅ Test réussi !")
    logger.info(f"Colonnes finales : {len(df_test.columns)}")
    logger.info(f"Exemples colonnes :")
    for col in list(df_test.columns)[:10]:
        logger.info(f"  - {col}")
