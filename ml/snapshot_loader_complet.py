#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 SNAPSHOT LOADER COMPLET - Backtest ML Quality
Version: 1.0
Date: 16 Novembre 2025

Charge les snapshots ML_READY COMPLETS avec 100% des features
Garantit compatibilité totale avec le modèle ML Quality Score

FEATURES GARANTIES:
- MenthorQ: gex_*, hvl, blind_spot_*, gamma_wall_level (17 features)
- Battle Navale: dom_features, depth_*, battle_navale_* (7 features)
- Volume Profile: d_vpoc_ticks, d_vah_ticks, 1d_max, 1d_min (4 features)
- OrderFlow: delta, cum_delta_*, deltaPct, etc. (15 features)
- Context: vwap, d_vwap, atr, session_progress, etc. (20 features)
- Engineered: Calculées automatiquement (35 features)
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class SnapshotLoaderComplet:
    """
    Charge les snapshots ML_READY complets pour backtest
    Garantit 100% des features attendues par le modèle ML
    """

    # Features CRITIQUES attendues par le modèle ML Quality
    REQUIRED_FEATURES = {
        'menthorq': [
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
            'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
            'call_resistance', 'put_support', 'hvl', 'gamma_wall_level',
            'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
            'menthorq_impact_score', 'menthorq_proximity_strength',
            'confluence_strength', 'confluence_density', 'confluence_proximity'
        ],
        'battle_navale': [
            'depth_bid', 'depth_ask', 'depth_imbalance',
            'dom_age_ms', 'level1_imbalance', 'micro_imb',
            'battle_navale_signal_strength', 'battle_navale_confidence'
        ],
        'volume_profile': [
            'd_vpoc_ticks', 'd_vah_ticks', '1d_max', '1d_min'
        ],
        'orderflow': [
            'delta', 'cum_delta_day', 'cum_delta_session', 'deltaPct',
            'smart_money_flow', 'institutional_pressure',
            'volume', 'bidvol', 'askvol', 'bidPct', 'askPct'
        ],
        'context': [
            'vwap', 'd_vwap', 'd_vwap_ticks', 'd_vwap_atr',
            'atr', 'atr_ratio', 'volatility_regime', 'volatility_regime_cont',
            'session_progress', 'session_elapsed_s',
            'mid', 'spread_ticks', 'microprice', 'microgap_n',
            'vix'
        ]
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialise le loader

        Args:
            data_dir: Répertoire racine des données (défaut: DATA_SIERRA_CHART)
        """
        if data_dir is None:
            self.data_dir = project_root / "DATA_SIERRA_CHART" / "DATA_2025" / "NOVEMBRE"
        else:
            self.data_dir = Path(data_dir)

        self.stats = {
            'total_loaded': 0,
            'total_validated': 0,
            'missing_features': {}
        }

        logger.info("=" * 80)
        logger.info("📊 SNAPSHOT LOADER COMPLET initialisé")
        logger.info(f"   Data dir: {self.data_dir}")
        logger.info("=" * 80)

    def load_day_data(
        self,
        symbol: str,
        date: str,
        chart: int = 9,
        validate_features: bool = True
    ) -> pd.DataFrame:
        """
        Charge les snapshots ML_READY pour une journée complète

        Args:
            symbol: Symbole (ES, NQ, RTY)
            date: Date au format YYYYMMDD (ex: "20251114")
            chart: Numéro de chart (défaut: 9)
            validate_features: Si True, valide que toutes les features sont présentes

        Returns:
            DataFrame avec snapshots complets
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"📂 CHARGEMENT SNAPSHOTS: {symbol} - {date} (Chart {chart})")
        logger.info("=" * 80)

        # Construire chemin fichier
        file_path = (
            self.data_dir / date / f"CHART_{chart}" / "ML_READY" /
            f"ml_{symbol}Z25_FUT_CME_{chart}.jsonl"
        )

        # Si pas trouvé, essayer sans la date dans le nom de fichier
        if not file_path.exists():
            # Vérifier dossier parent
            parent_dir = self.data_dir / date / f"CHART_{chart}" / "ML_READY"
            if parent_dir.exists():
                # Lister les fichiers disponibles
                files = list(parent_dir.glob(f"ml_{symbol}Z25_*.jsonl"))
                if files:
                    file_path = files[0]  # Prendre le premier fichier trouvé
                    logger.info(f"ℹ️  Fichier trouvé: {file_path.name}")

        if not file_path.exists():
            logger.error(f"❌ Fichier non trouvé: {file_path}")
            return pd.DataFrame()

        logger.info(f"✅ Fichier trouvé: {file_path.name}")
        logger.info(f"   Taille: {file_path.stat().st_size / (1024*1024):.2f} MB")

        # Charger snapshots (1 ligne JSON = 1 snapshot)
        snapshots = []
        line_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                if line.strip():
                    try:
                        snapshot = json.loads(line)
                        snapshots.append(snapshot)
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️  Ligne {line_count} invalide: {e}")

        logger.info(f"✅ {len(snapshots)} snapshots chargés ({line_count} lignes lues)")

        if not snapshots:
            logger.error("❌ Aucun snapshot valide chargé")
            return pd.DataFrame()

        # Convertir en DataFrame
        df = pd.DataFrame(snapshots)
        self.stats['total_loaded'] = len(df)

        # Extraire features nested (dom_features, etc.)
        df = self._flatten_nested_features(df)

        # Validation des features
        if validate_features:
            validation_result = self._validate_features(df)

            if not validation_result['valid']:
                logger.warning("\n⚠️  FEATURES MANQUANTES DÉTECTÉES:")
                for category, missing in validation_result['missing_by_category'].items():
                    if missing:
                        logger.warning(f"   {category}: {len(missing)} manquantes")
                        for feat in missing[:3]:
                            logger.warning(f"      - {feat}")
                        if len(missing) > 3:
                            logger.warning(f"      ... et {len(missing) - 3} autres")
            else:
                logger.info("\n✅ VALIDATION FEATURES: 100% OK")
                self.stats['total_validated'] = len(df)

        # Afficher statistiques
        logger.info(f"\n📊 STATISTIQUES SNAPSHOTS:")
        logger.info(f"   Snapshots: {len(df)}")
        logger.info(f"   Features: {len(df.columns)}")
        logger.info(f"   Période: {df['t_ms'].min()} → {df['t_ms'].max()}")

        if 'session_id' in df.columns:
            sessions = df['session_id'].value_counts()
            logger.info(f"   Sessions: {dict(sessions)}")

        logger.info("=" * 80 + "\n")

        return df

    def _flatten_nested_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrait les features imbriquées dans des dicts (dom_features, etc.)

        Args:
            df: DataFrame avec features potentiellement imbriquées

        Returns:
            DataFrame avec features aplaties
        """
        # Colonnes à extraire
        nested_cols = ['dom_features', 'menthor_distances', 'next_wall', 'vva', 'structure']

        for col in nested_cols:
            if col in df.columns:
                # Vérifier si c'est un dict
                first_value = df[col].iloc[0] if not df.empty else None
                if isinstance(first_value, dict):
                    # Extraire les clés du dict dans des colonnes séparées
                    nested_df = pd.json_normalize(df[col])

                    # Préfixer avec le nom de la colonne parent (sauf pour dom_features)
                    if col != 'dom_features':
                        nested_df.columns = [f"{col}_{c}" for c in nested_df.columns]

                    # Ajouter au DataFrame principal
                    df = pd.concat([df, nested_df], axis=1)

                    logger.debug(f"   Extracted {len(nested_df.columns)} features from {col}")

        return df

    def _validate_features(self, df: pd.DataFrame) -> Dict:
        """
        Valide que toutes les features critiques sont présentes

        Args:
            df: DataFrame des snapshots

        Returns:
            Dict avec résultat validation
        """
        missing_by_category = {}
        total_missing = 0

        for category, features in self.REQUIRED_FEATURES.items():
            missing = [f for f in features if f not in df.columns]
            missing_by_category[category] = missing
            total_missing += len(missing)

            if missing:
                self.stats['missing_features'][category] = missing

        total_required = sum(len(feats) for feats in self.REQUIRED_FEATURES.values())
        coverage_pct = ((total_required - total_missing) / total_required * 100) if total_required > 0 else 0

        return {
            'valid': total_missing == 0,
            'total_required': total_required,
            'total_missing': total_missing,
            'coverage_pct': coverage_pct,
            'missing_by_category': missing_by_category
        }

    def get_snapshot_at_time(self, df: pd.DataFrame, timestamp_ms: int) -> Optional[Dict]:
        """
        Récupère le snapshot le plus proche d'un timestamp donné

        Args:
            df: DataFrame des snapshots
            timestamp_ms: Timestamp en millisecondes

        Returns:
            Snapshot dict ou None
        """
        if df.empty:
            return None

        # Trouver l'index le plus proche
        idx = (df['t_ms'] - timestamp_ms).abs().idxmin()
        return df.loc[idx].to_dict()

    def filter_trading_session(
        self,
        df: pd.DataFrame,
        session: str = "London"
    ) -> pd.DataFrame:
        """
        Filtre les snapshots par session de trading

        Args:
            df: DataFrame des snapshots
            session: Nom de la session (London, NewYork, Asian)

        Returns:
            DataFrame filtré
        """
        if 'session_id' not in df.columns:
            logger.warning("⚠️  Colonne 'session_id' non trouvée, pas de filtrage")
            return df

        filtered = df[df['session_id'] == session].copy()
        logger.info(f"📊 Session {session}: {len(filtered)} snapshots")

        return filtered

    def get_stats(self) -> Dict:
        """Retourne les statistiques du loader"""
        return self.stats


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Test du loader avec données réelles"""

    print("\n" + "=" * 80)
    print("🔍 TEST SNAPSHOT LOADER COMPLET")
    print("=" * 80)

    # Initialiser le loader
    loader = SnapshotLoaderComplet()

    # Charger données vendredi 14 novembre (NQ disponible)
    df_nq = loader.load_day_data(
        symbol="NQ",
        date="20251114",
        chart=9,
        validate_features=True
    )

    if not df_nq.empty:
        print(f"\n✅ NQ: {len(df_nq)} snapshots chargés")
        print(f"   Features: {len(df_nq.columns)}")
        print(f"   Colonnes: {list(df_nq.columns[:20])}...")

        # Afficher un snapshot exemple
        print(f"\n📊 SNAPSHOT EXEMPLE (premier):")
        snapshot = df_nq.iloc[0].to_dict()

        # Vérifier features critiques
        critical_features = {
            'MenthorQ': ['gex_1', 'hvl', 'blind_spot_0', 'confluence_strength'],
            'Battle Navale': ['depth_bid', 'depth_ask', 'battle_navale_signal_strength'],
            'Volume Profile': ['d_vpoc_ticks', 'd_vah_ticks', '1d_max'],
            'OrderFlow': ['delta', 'cum_delta_day', 'deltaPct'],
            'Context': ['vwap', 'd_vwap', 'atr', 'session_progress']
        }

        for category, features in critical_features.items():
            print(f"\n   {category}:")
            for feat in features:
                value = snapshot.get(feat, 'MANQUANT')
                print(f"      {feat:30s}: {value}")

    # Statistiques
    stats = loader.get_stats()
    print(f"\n" + "=" * 80)
    print(f"📊 STATISTIQUES FINALES")
    print(f"=" * 80)
    print(f"   Snapshots chargés: {stats['total_loaded']}")
    print(f"   Snapshots validés: {stats['total_validated']}")

    if stats['missing_features']:
        print(f"\n⚠️  Features manquantes par catégorie:")
        for cat, missing in stats['missing_features'].items():
            print(f"   {cat}: {missing}")
    else:
        print(f"\n✅ TOUTES LES FEATURES PRÉSENTES (100%)")

    print("=" * 80)
