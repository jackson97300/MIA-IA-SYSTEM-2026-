r"""
Extracteur donnees ML_READY - ML 3-Layer Strategy
Version: 1.0
Date: 15 novembre 2025

Charge et agrege les donnees ML_READY depuis les fichiers historiques.
Periode: 8 jours (05-14 novembre 2025)
Symboles: ES (Chart 3) + NQ (Chart 9)

Structure donnees:
D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE\
    - 20251105/
        - CHART_3/ML_READY/   # ES
        - CHART_9/ML_READY/   # NQ
    - 20251106/
    ...
    - 20251114/

Output: ml/data/ml_ready_aggregated.parquet (~90 features x 10,000+ snapshots)
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MLReadyDataExtractor:
    """
    Extracteur de données ML_READY depuis fichiers historiques.

    Usage:
        extractor = MLReadyDataExtractor(base_path="D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/NOVEMBRE")
        df = extractor.extract_all(start_date="20251105", end_date="20251114")
    """

    def __init__(self, base_path: str):
        """
        Initialise l'extracteur.

        Args:
            base_path: Chemin racine des données (ex: D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025/NOVEMBRE)
        """
        self.base_path = Path(base_path)

        # Configuration symboles
        self.CHART_MAPPING = {
            'ES': 'CHART_3',
            'NQ': 'CHART_9'
        }

        logger.info(f"✅ MLReadyDataExtractor initialisé")
        logger.info(f"   Base path: {self.base_path}")


    def extract_day(
        self,
        date_str: str,
        symbol: str = 'ES'
    ) -> Optional[pd.DataFrame]:
        """
        Extrait les données ML_READY d'une journée pour un symbole.

        Args:
            date_str: Date au format YYYYMMDD (ex: '20251105')
            symbol: Symbole ('ES' ou 'NQ')

        Returns:
            DataFrame avec tous les snapshots du jour, ou None si erreur
        """

        chart_folder = self.CHART_MAPPING.get(symbol)
        if not chart_folder:
            logger.error(f"❌ Symbole inconnu: {symbol}")
            return None

        # Construire chemin
        ml_ready_path = self.base_path / date_str / chart_folder / "ML_READY"

        if not ml_ready_path.exists():
            logger.warning(f"⚠️ Dossier non trouvé: {ml_ready_path}")
            return None

        # Lister tous les fichiers .jsonl dans ML_READY (JSON Lines format)
        json_files = list(ml_ready_path.glob("*.jsonl"))

        if not json_files:
            logger.warning(f"⚠️ Aucun fichier JSON trouvé dans {ml_ready_path}")
            return None

        logger.info(f"📂 {date_str} - {symbol}: {len(json_files)} fichiers trouvés")

        # Charger tous les snapshots (JSON Lines: 1 ligne = 1 JSON)
        snapshots = []
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:  # Skip empty lines
                            continue
                        try:
                            data = json.loads(line)

                            # Ajouter métadonnées
                            data['date'] = date_str
                            data['symbol_base'] = symbol
                            data['source_file'] = json_file.name

                            snapshots.append(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Erreur JSON ligne {line_num} dans {json_file.name}: {e}")
                            continue

            except Exception as e:
                logger.error(f"❌ Erreur lecture {json_file.name}: {e}")
                continue

        if not snapshots:
            logger.warning(f"⚠️ Aucun snapshot valide pour {date_str} - {symbol}")
            return None

        # Convertir en DataFrame
        df = pd.DataFrame(snapshots)

        logger.info(f"✅ {date_str} - {symbol}: {len(df)} snapshots chargés")

        return df


    def extract_all(
        self,
        start_date: str,
        end_date: str,
        symbols: List[str] = ['ES', 'NQ']
    ) -> pd.DataFrame:
        """
        Extrait toutes les données ML_READY sur une période.

        Args:
            start_date: Date début au format YYYYMMDD
            end_date: Date fin au format YYYYMMDD
            symbols: Liste des symboles à extraire

        Returns:
            DataFrame agrégé avec tous les snapshots
        """

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 EXTRACTION DONNÉES ML_READY")
        logger.info(f"{'='*70}")
        logger.info(f"   Période: {start_date} → {end_date}")
        logger.info(f"   Symboles: {', '.join(symbols)}")
        logger.info(f"{'='*70}\n")

        # Générer liste des dates
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)

        logger.info(f"📅 {len(dates)} jours à extraire: {dates}\n")

        # Extraction par jour et symbole
        all_dataframes = []

        for symbol in symbols:
            logger.info(f"\n{'─'*70}")
            logger.info(f"🔍 EXTRACTION {symbol}")
            logger.info(f"{'─'*70}")

            for date_str in dates:
                df_day = self.extract_day(date_str, symbol)
                if df_day is not None and not df_day.empty:
                    all_dataframes.append(df_day)

        # Agrégation
        if not all_dataframes:
            logger.error(f"❌ Aucune donnée extraite !")
            return pd.DataFrame()

        df_aggregated = pd.concat(all_dataframes, ignore_index=True)

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ EXTRACTION TERMINÉE")
        logger.info(f"{'='*70}")
        logger.info(f"   Total snapshots: {len(df_aggregated):,}")
        logger.info(f"   Total features: {len(df_aggregated.columns)}")
        logger.info(f"   ES snapshots: {len(df_aggregated[df_aggregated['symbol_base'] == 'ES']):,}")
        logger.info(f"   NQ snapshots: {len(df_aggregated[df_aggregated['symbol_base'] == 'NQ']):,}")
        logger.info(f"   Période: {df_aggregated['date'].min()} → {df_aggregated['date'].max()}")
        logger.info(f"{'='*70}\n")

        return df_aggregated


    def save_aggregated(
        self,
        df: pd.DataFrame,
        output_path: str = "ml/data/ml_ready_aggregated.parquet"
    ):
        """
        Sauvegarde le DataFrame agrégé.

        Args:
            df: DataFrame à sauvegarder
            output_path: Chemin de sortie
        """

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Sauvegarde Parquet (compression optimale)
        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)

        file_size = output_file.stat().st_size / (1024 * 1024)  # MB

        logger.info(f"💾 Données sauvegardées:")
        logger.info(f"   Fichier: {output_file}")
        logger.info(f"   Taille: {file_size:.2f} MB")
        logger.info(f"   Format: Parquet (Snappy)")


    def load_aggregated(
        self,
        input_path: str = "ml/data/ml_ready_aggregated.parquet"
    ) -> pd.DataFrame:
        """
        Charge le DataFrame agrégé depuis le fichier.

        Args:
            input_path: Chemin du fichier

        Returns:
            DataFrame chargé
        """

        input_file = Path(input_path)

        if not input_file.exists():
            logger.error(f"❌ Fichier non trouvé: {input_file}")
            return pd.DataFrame()

        df = pd.read_parquet(input_file, engine='pyarrow')

        logger.info(f"📂 Données chargées:")
        logger.info(f"   Fichier: {input_file}")
        logger.info(f"   Snapshots: {len(df):,}")
        logger.info(f"   Features: {len(df.columns)}")

        return df


    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Génère des statistiques sur les données extraites.

        Args:
            df: DataFrame des snapshots

        Returns:
            Dict avec statistiques
        """

        stats = {
            'total_snapshots': len(df),
            'total_features': len(df.columns),
            'date_range': {
                'start': df['date'].min() if 'date' in df.columns else None,
                'end': df['date'].max() if 'date' in df.columns else None,
                'unique_days': df['date'].nunique() if 'date' in df.columns else 0
            },
            'symbols': {},
            'missing_data': {}
        }

        # Stats par symbole
        if 'symbol_base' in df.columns:
            for symbol in df['symbol_base'].unique():
                df_symbol = df[df['symbol_base'] == symbol]
                stats['symbols'][symbol] = {
                    'count': len(df_symbol),
                    'percentage': len(df_symbol) / len(df) * 100
                }

        # Valeurs manquantes
        missing = df.isnull().sum()
        missing_pct = (missing / len(df)) * 100
        stats['missing_data'] = {
            col: {'count': int(count), 'percentage': float(pct)}
            for col, count, pct in zip(df.columns, missing, missing_pct)
            if count > 0
        }

        return stats


# ═══════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Extraction des données ML_READY (8 jours)."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION
    # ═══════════════════════════════════════════════════════════

    BASE_PATH = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE"
    START_DATE = "20251105"  # 5 novembre 2025
    END_DATE = "20251114"    # 14 novembre 2025 (8 jours de trading)
    SYMBOLS = ['ES', 'NQ']
    OUTPUT_PATH = "ml/data/ml_ready_aggregated.parquet"

    # ═══════════════════════════════════════════════════════════
    # EXTRACTION
    # ═══════════════════════════════════════════════════════════

    extractor = MLReadyDataExtractor(base_path=BASE_PATH)

    df = extractor.extract_all(
        start_date=START_DATE,
        end_date=END_DATE,
        symbols=SYMBOLS
    )

    if df.empty:
        logger.error("❌ Aucune donnée extraite ! Vérifiez les chemins.")
        exit(1)

    # ═══════════════════════════════════════════════════════════
    # STATISTIQUES
    # ═══════════════════════════════════════════════════════════

    stats = extractor.get_statistics(df)

    print("\n" + "="*70)
    print("STATISTIQUES DONNEES EXTRAITES")
    print("="*70)
    print(f"Total snapshots: {stats['total_snapshots']:,}")
    print(f"Total features: {stats['total_features']}")
    print(f"Periode: {stats['date_range']['start']} -> {stats['date_range']['end']}")
    print(f"Jours uniques: {stats['date_range']['unique_days']}")
    print("\nPar symbole:")
    for symbol, data in stats['symbols'].items():
        print(f"  {symbol}: {data['count']:,} ({data['percentage']:.1f}%)")

    if stats['missing_data']:
        print(f"\n*** {len(stats['missing_data'])} features avec valeurs manquantes")
        print("(Voir logs pour details)")

    print("="*70 + "\n")

    # ═══════════════════════════════════════════════════════════
    # SAUVEGARDE
    # ═══════════════════════════════════════════════════════════

    extractor.save_aggregated(df, OUTPUT_PATH)

    logger.info("✅ Extraction terminée avec succès !")
