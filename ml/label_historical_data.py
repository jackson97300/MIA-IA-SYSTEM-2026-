#!/usr/bin/env python3
"""
ml/label_historical_data.py

SCRIPT DE LABELLISATION DES DONNÉES HISTORIQUES
Prépare les données du dumper pour l'entraînement ML

FONCTIONNALITÉS :
1. Lit les fichiers JSONL du dumper (study_inventory_chart_X.jsonl)
2. Calcule le "future return" pour chaque tick
3. Labellise : PROFITABLE (1) ou NON-PROFITABLE (0)
4. Export en Parquet pour entraînement rapide
5. Support ES (Chart 3) et NQ (Chart 9)

USAGE :
    python ml/label_historical_data.py --input DATA_SIERRA_CHART/ --output DATASET/labeled_data.parquet

PARAMÈTRES :
    --input: Dossier contenant les fichiers JSONL
    --output: Fichier Parquet de sortie
    --horizon: Horizon de prédiction en secondes (défaut: 60)
    --min_profit_ticks: Profit minimum en ticks pour label=1 (défaut: 8)
    --charts: Charts à traiter (défaut: 3,9 pour ES et NQ)

Version: 1.0
Date: 30 Octobre 2025
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("❌ pandas non disponible - pip install pandas")
    sys.exit(1)

# === CONFIGURATION ===

TICK_SIZES = {
    'ES': 0.25,   # ES: 0.25 points
    'NQ': 0.25,   # NQ: 0.25 points
    'MES': 0.25,
    'MNQ': 0.25
}

CHART_TO_SYMBOL = {
    3: 'ES',
    9: 'NQ'
}

# === FONCTIONS ===

def detect_symbol_from_tick(tick: Dict) -> str:
    """Détecte le symbole depuis le tick"""
    sym = tick.get('sym', '')

    if 'ES' in sym:
        return 'ES'
    elif 'NQ' in sym:
        return 'NQ'
    elif 'MES' in sym:
        return 'MES'
    elif 'MNQ' in sym:
        return 'MNQ'
    else:
        # Fallback sur chart number
        chart = tick.get('chart', 0)
        return CHART_TO_SYMBOL.get(chart, 'UNKNOWN')

def calculate_future_return(
    df: pd.DataFrame,
    horizon_seconds: int = 60,
    price_column: str = 'mid'
) -> pd.Series:
    """
    Calcule le return futur pour chaque tick

    Args:
        df: DataFrame avec colonnes ['t_ms', price_column]
        horizon_seconds: Horizon en secondes
        price_column: Colonne de prix à utiliser

    Returns:
        Series avec le return futur en ticks
    """
    # Convertir horizon en millisecondes
    horizon_ms = horizon_seconds * 1000

    # Future price (chercher le prix X secondes plus tard)
    future_prices = []

    for idx, row in df.iterrows():
        current_time = row['t_ms']
        current_price = row[price_column]
        symbol = row['symbol']

        # Chercher le prix futur
        future_time = current_time + horizon_ms
        future_rows = df[
            (df['t_ms'] >= future_time) &
            (df['t_ms'] <= future_time + 5000)  # +5s de marge
        ]

        if len(future_rows) > 0:
            future_price = future_rows.iloc[0][price_column]

            # Calculer return en ticks
            tick_size = TICK_SIZES.get(symbol, 0.25)
            return_ticks = (future_price - current_price) / tick_size
            future_prices.append(return_ticks)
        else:
            # Pas de données futures → NaN
            future_prices.append(np.nan)

    return pd.Series(future_prices, index=df.index)

def label_profitability(
    future_return: pd.Series,
    min_profit_ticks: int = 8
) -> pd.Series:
    """
    Labellise la profitabilité

    Args:
        future_return: Return futur en ticks
        min_profit_ticks: Profit minimum pour considérer profitable

    Returns:
        Series avec labels : 1 (profitable), 0 (non-profitable)
    """
    # Label = 1 si |return| >= min_profit_ticks
    labels = (np.abs(future_return) >= min_profit_ticks).astype(int)
    return labels

def extract_features(tick: Dict) -> Dict:
    """
    Extrait les features importantes du tick

    Args:
        tick: Dictionnaire dumper complet

    Returns:
        Dictionnaire avec features simplifiées
    """
    features = {
        # Identifiants
        't_ms': tick.get('t_ms', 0),
        'chart': tick.get('chart', 0),
        'symbol': detect_symbol_from_tick(tick),

        # Prix
        'mid': tick.get('mid', 0),
        'spread_ticks': tick.get('spread_ticks', 0),
        'is_1tick_spread': 1 if tick.get('is_1tick_spread', False) else 0,

        # VWAP
        'd_vwap_ticks': tick.get('d_vwap_ticks', 0),
        'd_vwap_weekly_ticks': tick.get('d_vwap_weekly_ticks', 0),
        'd_vwap_monthly_ticks': tick.get('d_vwap_monthly_ticks', 0),
        'd_pvwap_ticks': tick.get('d_pvwap_ticks', 0),
        'd_w_up1_ticks': tick.get('d_w_up1_ticks', 0),
        'd_w_dn1_ticks': tick.get('d_w_dn1_ticks', 0),
        'd_vwap_atr': tick.get('d_vwap_atr', 0),

        # Gamma/MenthorQ
        'confluence_strength': tick.get('confluence_strength', 0),
        'confluence_proximity': tick.get('confluence_proximity', 0),
        'menthorq_impact_score': tick.get('menthorq_impact_score', 0),
        'menthorq_proximity_strength': tick.get('menthorq_proximity_strength', 0),
        'gamma_call_confluence': 1 if tick.get('gamma_call_confluence', False) else 0,
        'gamma_put_confluence': 1 if tick.get('gamma_put_confluence', False) else 0,
        'blind_spot_confluence': 1 if tick.get('blind_spot_confluence', False) else 0,
        'battle_navale_signal_strength': tick.get('battle_navale_signal_strength', 0),

        # DOM
        'level1_imbalance': tick.get('level1_imbalance', 0),
        'depth_imbalance': tick.get('depth_imbalance', 0),
        'ob_center_tanh': tick.get('ob_center_tanh', 0),
        'top_heavy': tick.get('top_heavy', 0),
        'tick_rate_3s': tick.get('tick_rate_3s', 0),
        'tick_momentum': tick.get('tick_momentum', 0),

        # Delta/OrderFlow
        'delta': tick.get('delta', 0),
        'cum_delta_session': tick.get('cum_delta_session', 0),
        'pressure_strength': tick.get('pressure_strength', 0),
        'smart_money_flow': tick.get('smart_money_flow', 0),
        'institutional_pressure': tick.get('institutional_pressure', 0),

        # Volume Profile
        'd_vpoc_ticks': tick.get('d_vpoc_ticks', 0),
        'd_vah_ticks': tick.get('d_vah_ticks', 0),
        'd_val_ticks': tick.get('d_val_ticks', 0),
        'in_value_area': 1 if tick.get('in_value_area', False) else 0,

        # Volatility
        'volatility_regime': tick.get('volatility_regime', 1),
        'atr_ratio': tick.get('atr_ratio', 0),

        # Session
        'session_progress': tick.get('session_progress', 0),
        'elapsed_s': tick.get('elapsed_s', 0)
    }

    return features

def load_jsonl_files(
    input_dir: str,
    charts: List[int] = [3, 9],
    max_ticks: Optional[int] = None
) -> List[Dict]:
    """
    Charge les fichiers JSONL du dumper

    Args:
        input_dir: Dossier racine (ex: DATA_SIERRA_CHART/)
        charts: Liste des charts à charger
        max_ticks: Limite de ticks à charger (None = tous)

    Returns:
        Liste de dictionnaires (ticks)
    """
    all_ticks = []
    input_path = Path(input_dir)

    print(f"📂 Recherche fichiers dans: {input_path}")

    # Chercher tous les fichiers JSONL
    jsonl_files = []
    for chart in charts:
        pattern = f"study_inventory_chart_{chart}_*.jsonl"
        files = list(input_path.rglob(pattern))
        jsonl_files.extend(files)

        # Aussi chercher sans date
        pattern_simple = f"study_inventory_chart_{chart}.jsonl"
        files_simple = list(input_path.rglob(pattern_simple))
        jsonl_files.extend(files_simple)

    if not jsonl_files:
        print(f"⚠️ Aucun fichier JSONL trouvé pour charts {charts}")
        return []

    print(f"📄 {len(jsonl_files)} fichiers trouvés")

    # Charger chaque fichier
    for jsonl_file in jsonl_files:
        print(f"  Lecture: {jsonl_file.name}...")

        try:
            with open(jsonl_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if max_ticks and len(all_ticks) >= max_ticks:
                        break

                    try:
                        tick = json.loads(line.strip())
                        all_ticks.append(tick)
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"    ⚠️ Erreur: {e}")
            continue

    print(f"✅ {len(all_ticks)} ticks chargés")
    return all_ticks

def process_and_label_data(
    input_dir: str,
    output_file: str,
    horizon_seconds: int = 60,
    min_profit_ticks: int = 8,
    charts: List[int] = [3, 9],
    max_ticks: Optional[int] = None
) -> bool:
    """
    Processus complet de labellisation

    Args:
        input_dir: Dossier d'entrée
        output_file: Fichier de sortie (parquet)
        horizon_seconds: Horizon de prédiction
        min_profit_ticks: Profit minimum pour label=1
        charts: Charts à traiter
        max_ticks: Limite de ticks (None = tous)

    Returns:
        True si succès
    """
    print("\n" + "="*60)
    print("🏷️  LABELLISATION DES DONNÉES HISTORIQUES")
    print("="*60)

    # 1. Charger données
    print("\n1️⃣  Chargement des données...")
    ticks = load_jsonl_files(input_dir, charts, max_ticks)

    if not ticks:
        print("❌ Aucune donnée chargée")
        return False

    # 2. Extraire features
    print("\n2️⃣  Extraction des features...")
    features_list = []
    for tick in ticks:
        features = extract_features(tick)
        features_list.append(features)

    df = pd.DataFrame(features_list)
    print(f"   ✅ {len(df)} lignes × {len(df.columns)} colonnes")

    # 3. Trier par temps
    print("\n3️⃣  Tri chronologique...")
    df = df.sort_values('t_ms').reset_index(drop=True)

    # 4. Calculer future return
    print(f"\n4️⃣  Calcul du return futur (horizon={horizon_seconds}s)...")
    df['future_return_ticks'] = calculate_future_return(df, horizon_seconds)

    # Supprimer les lignes sans future return
    valid_count_before = len(df)
    df = df.dropna(subset=['future_return_ticks'])
    valid_count_after = len(df)
    print(f"   ✅ {valid_count_after} lignes valides ({valid_count_before - valid_count_after} supprimées)")

    # 5. Labelliser
    print(f"\n5️⃣  Labellisation (min_profit={min_profit_ticks} ticks)...")
    df['signal_profitable'] = label_profitability(df['future_return_ticks'], min_profit_ticks)

    # Stats
    profitable_count = df['signal_profitable'].sum()
    total_count = len(df)
    profitable_pct = (profitable_count / total_count) * 100

    print(f"   ✅ Profitable: {profitable_count} ({profitable_pct:.1f}%)")
    print(f"   ✅ Non-profitable: {total_count - profitable_count} ({100-profitable_pct:.1f}%)")

    # 6. Export
    print(f"\n6️⃣  Export vers: {output_file}")
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(output_file, index=False)

    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"   ✅ Fichier créé: {file_size_mb:.2f} MB")

    # 7. Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ")
    print("="*60)
    print(f"Total samples: {len(df)}")
    print(f"Features: {len(df.columns) - 3}")  # -3 pour t_ms, future_return, signal_profitable
    print(f"Profitable: {profitable_count} ({profitable_pct:.1f}%)")
    print(f"Horizon: {horizon_seconds}s")
    print(f"Min profit: {min_profit_ticks} ticks")
    print(f"\n✅ Prêt pour l'entraînement !")
    print(f"   Commande: python ml/train_lightgbm.py --input {output_file}")

    return True

# === MAIN ===

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Labellise les données historiques du dumper pour ML"
    )

    parser.add_argument(
        '--input',
        type=str,
        default='DATA_SIERRA_CHART',
        help='Dossier contenant les fichiers JSONL'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='DATASET/labeled_data.parquet',
        help='Fichier Parquet de sortie'
    )

    parser.add_argument(
        '--horizon',
        type=int,
        default=60,
        help='Horizon de prédiction en secondes (défaut: 60)'
    )

    parser.add_argument(
        '--min-profit-ticks',
        type=int,
        default=8,
        help='Profit minimum en ticks pour label=1 (défaut: 8)'
    )

    parser.add_argument(
        '--charts',
        type=str,
        default='3,9',
        help='Charts à traiter, séparés par virgule (défaut: 3,9)'
    )

    parser.add_argument(
        '--max-ticks',
        type=int,
        default=None,
        help='Limite de ticks à charger (défaut: tous)'
    )

    args = parser.parse_args()

    # Parser les charts
    charts = [int(c.strip()) for c in args.charts.split(',')]

    # Lancer le processus
    success = process_and_label_data(
        input_dir=args.input,
        output_file=args.output,
        horizon_seconds=args.horizon,
        min_profit_ticks=args.min_profit_ticks,
        charts=charts,
        max_ticks=args.max_ticks
    )

    sys.exit(0 if success else 1)
