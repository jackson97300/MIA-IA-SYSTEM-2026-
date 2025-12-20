#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 DATA LOADER - MIA Trading Bot
=================================

Helper pour charger les snapshots depuis l'architecture
DATA_SIERRA_CHART documentée dans ARCHITECTURE_DONNEES.md

Créé: 10/12/2025
Author: MIA System + Claude Sonnet 4.5
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import json
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION ARCHITECTURE
# ═══════════════════════════════════════════════════════════════

# Mapping symboles → Chart ID (selon ARCHITECTURE_DONNEES.md)
CHART_MAPPING = {
    "ES": 3,   # E-mini S&P 500 → CHART_3
    "NQ": 9,   # E-mini NASDAQ → CHART_9
    "RTY": 1   # E-mini Russell 2000 → CHART_1
}

# Mapping numéro mois → nom français MAJUSCULES
MONTH_NAMES = {
    1: "JANVIER",
    2: "FEVRIER",
    3: "MARS",
    4: "AVRIL",
    5: "MAI",
    6: "JUIN",
    7: "JUILLET",
    8: "AOUT",
    9: "SEPTEMBRE",
    10: "OCTOBRE",
    11: "NOVEMBRE",
    12: "DECEMBRE"
}

# ═══════════════════════════════════════════════════════════════
# 🔄 ROLLOVER AUTOMATIQUE
# ═══════════════════════════════════════════════════════════════

def get_current_contract_month(date: Optional[datetime] = None) -> str:
    """
    Détermine automatiquement le code du contrat actif (H, M, U, Z).
    Rollover typique: ~10 du mois d'expiration.
    """
    if date is None:
        date = datetime.now()
    month = date.month
    year = date.year % 100
    if month == 12:
        return f"Z{year}" if date.day < 10 else f"H{(year + 1) % 100}"
    elif month in [1, 2]:
        return f"H{year}"
    elif month == 3:
        return f"H{year}" if date.day < 10 else f"M{year}"
    elif month in [4, 5]:
        return f"M{year}"
    elif month == 6:
        return f"M{year}" if date.day < 10 else f"U{year}"
    elif month in [7, 8]:
        return f"U{year}"
    elif month == 9:
        return f"U{year}" if date.day < 10 else f"Z{year}"
    elif month in [10, 11]:
        return f"Z{year}"
    return f"H{year}"

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def get_chart_id(symbol: str) -> Optional[int]:
    """Retourne le Chart ID pour un symbole"""
    return CHART_MAPPING.get(symbol.upper())


def get_month_name(month_num: int) -> str:
    """Retourne le nom du mois en français MAJUSCULES"""
    return MONTH_NAMES.get(month_num, "")


def build_snapshot_path(
    symbol: str,
    date: Optional[datetime] = None,
    year: int = 2025
) -> Optional[Path]:
    """
    Construit le chemin vers le fichier JSONL selon l'architecture.

    Architecture:
    DATA_SIERRA_CHART/DATA_{YEAR}/{MOIS}/{DATE}/CHART_{ID}/ML_READY/ml_{SYMBOL}Z25_FUT_CME_{ID}.jsonl

    Args:
        symbol: Symbole (ES, NQ, RTY)
        date: Date du fichier (défaut: aujourd'hui)
        year: Année (défaut: 2025)

    Returns:
        Path vers le fichier ou None si invalide
    """
    # Date par défaut = aujourd'hui
    if date is None:
        date = datetime.now()

    # Récupérer Chart ID
    chart_id = get_chart_id(symbol)
    if chart_id is None:
        logger.error(f"Symbole inconnu: {symbol}")
        return None

    # Construire le chemin
    base_path = Path("DATA_SIERRA_CHART")
    year_dir = f"DATA_{year}"
    month_name = get_month_name(date.month)
    date_str = date.strftime("%Y%m%d")
    chart_dir = f"CHART_{chart_id}"
    # 🔄 ROLLOVER AUTOMATIQUE
    contract = get_current_contract_month(date)
    filename = f"ml_{symbol.upper()}{contract}_FUT_CME_{chart_id}.jsonl"

    full_path = (
        base_path / year_dir / month_name / date_str /
        chart_dir / "ML_READY" / filename
    )

    return full_path


def find_latest_snapshot(symbol: str) -> Dict:
    """
    Trouve et charge le dernier snapshot pour un symbole.

    Cherche d'abord aujourd'hui, puis hier si fichier vide/absent.

    Args:
        symbol: Symbole (ES, NQ, RTY)

    Returns:
        Dict contenant le snapshot ou {} si introuvable
    """
    from datetime import timedelta

    # Essayer aujourd'hui
    for days_back in range(0, 3):  # Essayer 3 jours max
        date = datetime.now() - timedelta(days=days_back)
        file_path = build_snapshot_path(symbol, date)

        if file_path is None:
            continue

        if not file_path.exists():
            if days_back == 0:
                logger.debug(f"Fichier {file_path} introuvable (essai jour précédent)")
            continue

        try:
            # Lire la dernière ligne (snapshot le plus récent)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

                if not lines:
                    logger.warning(f"Fichier {file_path} vide")
                    continue

                # Parser la dernière ligne
                last_line = lines[-1].strip()
                if last_line:
                    snapshot = json.loads(last_line)
                    logger.info(f"✅ Snapshot chargé: {symbol} ({file_path.name})")
                    return snapshot

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON {file_path}: {e}")
            continue
        except Exception as e:
            logger.error(f"Erreur lecture {file_path}: {e}")
            continue

    logger.warning(f"❌ Aucun snapshot trouvé pour {symbol} (3 derniers jours)")
    return {}


def load_all_snapshots(symbol: str, date: Optional[datetime] = None) -> List[Dict]:
    """
    Charge TOUS les snapshots d'un fichier JSONL.

    Args:
        symbol: Symbole (ES, NQ, RTY)
        date: Date du fichier (défaut: aujourd'hui)

    Returns:
        Liste de snapshots
    """
    file_path = build_snapshot_path(symbol, date)

    if file_path is None or not file_path.exists():
        logger.error(f"Fichier introuvable: {file_path}")
        return []

    snapshots = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    snapshot = json.loads(line)
                    snapshots.append(snapshot)
                except json.JSONDecodeError as e:
                    logger.warning(f"Ligne {line_num} invalide dans {file_path}: {e}")

        logger.info(f"✅ {len(snapshots)} snapshots chargés: {symbol} ({file_path.name})")
        return snapshots

    except Exception as e:
        logger.error(f"Erreur lecture {file_path}: {e}")
        return []


def get_available_dates(symbol: str, year: int = 2025) -> List[str]:
    """
    Liste toutes les dates disponibles pour un symbole.

    Args:
        symbol: Symbole (ES, NQ, RTY)
        year: Année (défaut: 2025)

    Returns:
        Liste de dates au format YYYYMMDD
    """
    chart_id = get_chart_id(symbol)
    if chart_id is None:
        return []

    base_path = Path("DATA_SIERRA_CHART") / f"DATA_{year}"

    if not base_path.exists():
        logger.error(f"Dossier {base_path} introuvable")
        return []

    dates = []

    # Parcourir tous les mois
    for month_dir in base_path.iterdir():
        if not month_dir.is_dir():
            continue

        # Parcourir toutes les dates du mois
        for date_dir in month_dir.iterdir():
            if not date_dir.is_dir():
                continue

            # Vérifier que c'est une date valide (8 chiffres)
            if date_dir.name.isdigit() and len(date_dir.name) == 8:
                # Vérifier que le fichier existe
                chart_path = date_dir / f"CHART_{chart_id}" / "ML_READY"
                if chart_path.exists():
                    filename = f"ml_{symbol.upper()}Z25_FUT_CME_{chart_id}.jsonl"
                    if (chart_path / filename).exists():
                        dates.append(date_dir.name)

    dates.sort()
    return dates


def validate_snapshot(snapshot: Dict) -> bool:
    """
    Valide qu'un snapshot contient les champs critiques.

    Args:
        snapshot: Snapshot à valider

    Returns:
        True si valide, False sinon
    """
    required_fields = ['t_ms', 'sym', 'mid', 'bid', 'ask']

    for field in required_fields:
        if field not in snapshot:
            logger.warning(f"Snapshot invalide: champ '{field}' manquant")
            return False

    # Vérifier que mid > 0
    if snapshot.get('mid', 0) <= 0:
        logger.warning(f"Snapshot invalide: mid={snapshot.get('mid')}")
        return False

    return True


# ═══════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test chargement
    for symbol in ['ES', 'NQ', 'RTY']:
        snapshot = find_latest_snapshot(symbol)
        if snapshot:
            print(f"\n{symbol} - Dernier snapshot:")
            print(f"  Prix: {snapshot.get('mid', 'N/A')}")
            print(f"  Timestamp: {snapshot.get('t_ms', 'N/A')}")
            print(f"  HVL: {snapshot.get('hvl', 'N/A')}")
            print(f"  GEX_1: {snapshot.get('gex_1', 'N/A')}")
