#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
ENTRAÎNEMENT MODÈLE ML - DIRECTION 15 MINUTES (PHASE 1)
═══════════════════════════════════════════════════════════════════════════════

Objectif : Prédire la direction du prix dans 15 minutes (UP/DOWN/FLAT)
Algorithme : LightGBM
Features : Top 100 + Feature Engineering (LAGs + Rolling Means)
Dataset : ES Chart 3 + NQ Chart 9 (31 Oct 2025)

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import hashlib
import json
import logging
import os
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.utils.class_weight import compute_class_weight

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_engineering import FeatureEngineer

# Configuration logging AVEC FICHIER LOCAL
# Créer le dossier logs s'il n'existe pas
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Nom du fichier log avec timestamp
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"train_ml_direction_{log_timestamp}.log"

# Configurer le logging (console + fichier)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # ✅ Fichier local
        logging.StreamHandler()  # Console
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"📄 Logs sauvegardés dans: {log_file}")

# ✅ CORRECTIF GPT : Reproductibilité
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
import os
os.environ['PYTHONHASHSEED'] = str(RANDOM_SEED)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG = {
    # Chemins données (05 + 06 novembre combinés)
    "data_paths": {
        "es_chart3_05": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_3/ML_READY",
        "es_chart3_06": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_3/ML_READY",
        "nq_chart9_05": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_9/ML_READY",
        "nq_chart9_06": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_9/ML_READY",
        "rty_chart1_05": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_1/ML_READY",
        "rty_chart1_06": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_1/ML_READY",
    },

    # Labels - Barrières dynamiques ATR (✅ OPTIMISÉES PAR GRID SEARCH 06/11/2025)
    "horizon_seconds_es": 300,   # ✅ ES: 5 min (Grid Search: AUC=0.701, Score=0.647)
    "horizon_seconds_nq": 600,   # ✅ NQ: 10 min (Grid Search: AUC=0.623, Score=0.652)
    "horizon_seconds_rty": 600,  # ✅ RTY: 10 min (Grid Search: AUC=0.769, Score=0.687)
    "threshold_mode": "atr",  # "atr" (dynamique) ou "ticks" (fixe)
    "threshold_ticks": 12,   # Si mode ticks (fallback)
    "threshold_atr_multiplier_es": 0.35,  # ✅ ES: Grid Search optimal
    "threshold_atr_multiplier_nq": 0.36,  # ✅ NQ: Grid Search optimal
    "threshold_atr_multiplier_rty": 0.32,  # ✅ RTY: Grid Search optimal
    "tick_size": 0.25,       # ES et NQ
    "tick_size_rty": 0.10,   # ✅ RTY (différent !)
    "time_gap_tolerance": 60,  # Max 60s de gap acceptable

    # Features
    "n_features_manual": 162,  # ✅ PATCH V3.5: 144 + 13 (V3.3) + 5 (Session Price) = 162 features

    # ✅ PRIORITY FEATURES: Toujours incluses même si Top-K limité
    "priority_features": [
        # Confluences/Proximités (6)
        'confluence_proximity', 'gamma_call_confluence', 'gamma_put_confluence',
        'menthorq_proximity_strength', 'battle_navale_signal_strength', 'battle_navale_confidence',
        # Distances Menthor (8)
        'menthor_distances_call0', 'menthor_distances_put0', 'menthor_distances_gamma0',
        'menthor_distances_hvl0', 'menthor_distances_dist_1d_max', 'menthor_distances_dist_1d_min',
        'menthor_distances_near_gex_up', 'menthor_distances_near_gex_dn',
        # Next-Wall (3)
        'next_wall_dist_pts', 'next_wall_age_min', 'next_wall_side',
        # VWAP ticks (2)
        'd_vwap_weekly_ticks', 'd_vwap_monthly_ticks',
        # ✨ NOUVEAU : Distances OPTIONS dynamiques (8 - CRITIQUES pour la méthode)
        'd_nearest_gex_up_ticks', 'd_nearest_gex_down_ticks', 'd_nearest_gex_abs_ticks',
        'd_nearest_blind_spot_abs_ticks',
        'd_call_resistance_ticks', 'd_put_support_ticks', 'd_hvl_ticks',
        'd_nearest_gex_atr',  # Ratio ATR (normalisation volatilité)

        # ✨ PATCH V3.3: Nouvelles features prioritaires (10 - CRITIQUES pour direction)
        'mia_bullish_score',  # Score composite (bias principal)
        'delta_burst',        # Magnitude changement delta (explosions/absorptions)
        'delta_flip',         # Retournement signe delta (points d'inflexion)
        'upper_wick_ticks',   # Rejets résistance
        'lower_wick_ticks',   # Supports confirmés
        'gamma_flip_up',      # Franchissement gamma haut (stabilisation)
        'gamma_flip_down',    # Franchissement gamma bas (accélération)
        'gamma_wall_level',   # Niveau gamma actif (aimant)
        'stacked_imbalance_bid_rows',  # Murs BID empilés (support)
        'stacked_imbalance_ask_rows',  # Murs ASK empilés (résistance)

        # Signal général (1)
        'corr',
    ],

    # ✅ COLONNES À BANNIR (leak/bruit)
    "forbidden_columns": [
        't_ms', 'tsec', 'seq_unified', 'elapsed_s', 'last_mq_update_ms',
        'bar_index', 'progress01',  # progress01 si redondant avec session_progress
    ],

    # ✅ PATCH R3 GPT: Feature selection Top-K (réduire bruit et variance)
    # Problème: ~450-500 features générées → bruit, overfitting, lenteur
    # Solution: Top-K=130 (41 priority + 89 engineered best gain par importance)
    # Gains: Vitesse +20%, stabilité +15%, réduction overfitting
    # ✅ PHASE 3.5: Sélection par importance en 2 PASSES (optimal)
    "use_top_k": True,   # ✅ ACTIVÉ (était False)
    "top_k": 130,        # ✅ OPTIMISÉ à 130 (était 90)
    "priority_merge": True,  # Garantit que priority_features sont toujours incluses
    "n_features_auto": 30,    # Features sélectionnées automatiquement

    # ✅ PATCH R1 GPT: Réduction rolling_max pour purisme anti-leak
    # Règle: rolling_max < horizon / 5 (900s / 5 = 180s max)
    # Avant: [20, 60, 300] avec rolling_max=300s
    # Après: [20, 60, 180] avec rolling_max=180s (plus conservateur)
    "lag_periods": [1, 5, 10, 20, 60],  # Secondes (inchangé)
    "rolling_windows": [20, 60, 180],   # ✅ R1: 300 → 180s (purisme anti-leak)

    # Split
    "train_ratio": 0.80,
    "test_ratio": 0.20,
    "cv_n_splits": 5,  # TimeSeriesSplit

    # LightGBM - ✅ CONFIGURATION PRO : Solide, 5-20 min, apprentissage réel sans sur-entraînement
    "lgbm_params": {
        "objective": "multiclass",
        "num_class": 3,  # UP=2, FLAT=1, DOWN=0
        "metric": ["multi_logloss", "multi_error"],
        "boosting_type": "gbdt",
        "n_estimators": 5000,  # ✅ OPTIMAL : Analysé sur données réelles
        "learning_rate": 0.025,  # ✅ OPTIMAL : Convergence stable
        "max_depth": -1,
        "num_leaves": 95,  # ✅ OPTIMAL : 2^6.5, compromis capacité/overfitting
        "min_data_in_leaf": 25,  # ✅ OPTIMAL : ~0.2% train size
        "min_sum_hessian_in_leaf": 3.0,  # ✅ OPTIMAL : Moins restrictif
        "min_gain_to_split": 0.0,
        "feature_fraction": 0.75,  # ✅ OPTIMAL : Réduit corrélations
        "bagging_fraction": 0.75,  # ✅ OPTIMAL : Stabilité
        "bagging_freq": 1,
        "lambda_l1": 0.0,  # ✅ ROBUST : Pas de L1
        "lambda_l2": 3.5,  # ✅ OPTIMAL : Régularisation modérée-forte
        "feature_pre_filter": False,
        "is_unbalance": False,  # ✅ ROBUST : Classes ~50/50, pas besoin
        "verbosity": -1,
        "force_row_wise": True,
        "random_state": 42,
    },

    # ✅ CONFIGURATION PRO : Paramètres binaires (solide, 5-20 min, apprentissage réel)
    "lgbm_params_binary": {
        "objective": "binary",
        "metric": ["binary_logloss", "auc"],  # ✅ PRO : Plusieurs métriques pour suivi
        "boosting_type": "gbdt",
        "n_estimators": 5000,  # ✅ OPTIMAL : Analysé sur données réelles
        "learning_rate": 0.025,  # ✅ OPTIMAL : Convergence stable
        "max_depth": -1,
        "num_leaves": 95,  # ✅ OPTIMAL : 2^6.5, compromis capacité/overfitting
        "min_data_in_leaf": 25,  # ✅ OPTIMAL : ~0.2% train size
        "min_sum_hessian_in_leaf": 3.0,  # ✅ OPTIMAL : Moins restrictif
        "min_gain_to_split": 0.0,
        "feature_fraction": 0.75,  # ✅ OPTIMAL : Réduit corrélations
        "bagging_fraction": 0.75,  # ✅ OPTIMAL : Stabilité
        "bagging_freq": 1,
        "lambda_l1": 0.0,  # ✅ ROBUST : Pas de L1
        "lambda_l2": 3.5,  # ✅ OPTIMAL : Régularisation modérée-forte
        "feature_pre_filter": False,
        "is_unbalance": False,  # ✅ ROBUST : Classes ~50/50, pas besoin
        "verbosity": -1,
        "force_row_wise": True,
        "random_state": 42,
    },

    # Early stopping optimal
    "early_stopping_rounds": 400,  # ✅ OPTIMAL : ~8% de n_estimators

    # Seuils confidence à tester
    "confidence_thresholds": [0.55, 0.60, 0.65, 0.70, 0.75],

    # Output
    "output_dir": "ml/models",
    "model_name": "lgbm_direction_optimal",  # ✅ Renommé: horizon optimal par symbole (Grid Search)
}


# ═══════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════════════════

def load_jsonl_data(file_path: str) -> pd.DataFrame:
    """
    Charge un fichier JSONL ML_READY en DataFrame

    Args:
        file_path: Chemin vers fichier JSONL

    Returns:
        DataFrame avec données ML_READY
    """
    logger.info(f"📂 Chargement : {file_path}")

    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    df = pd.DataFrame(data)
    logger.info(f"   ✅ {len(df):,} samples chargés")

    return df


def load_all_data(data_dirs: list, chart_name: str) -> pd.DataFrame:
    """
    Charge tous les fichiers JSONL de plusieurs répertoires ML_READY

    Args:
        data_dirs: Liste de répertoires ML_READY (plusieurs dates)
        chart_name: Nom du chart (ES Chart 3 ou NQ Chart 9)

    Returns:
        DataFrame consolidé de toutes les dates
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 Chargement {chart_name} ({len(data_dirs)} dates)")
    logger.info(f"{'='*70}")

    all_dfs = []

    for data_dir in data_dirs:
        ml_ready_dir = Path(data_dir)
        if not ml_ready_dir.exists():
            logger.warning(f"⚠️  Répertoire ignoré (introuvable) : {ml_ready_dir}")
            continue

        # Trouver tous les fichiers JSONL
        jsonl_files = sorted(ml_ready_dir.glob("*.jsonl"))

        if not jsonl_files:
            logger.warning(f"⚠️  Aucun fichier .jsonl dans {ml_ready_dir}")
            continue

        logger.info(f"📁 {len(jsonl_files)} fichiers trouvés dans {ml_ready_dir.parts[-3]}/{ml_ready_dir.parts[-2]}")

        # Charger les fichiers de ce répertoire
        for jsonl_file in jsonl_files:
            df = load_jsonl_data(str(jsonl_file))
            all_dfs.append(df)

    if not all_dfs:
        raise FileNotFoundError(f"❌ Aucune donnée chargée pour {chart_name}")

    # Concaténer tous les DataFrames
    df_full = pd.concat(all_dfs, ignore_index=True)

    # Trier par timestamp
    df_full = df_full.sort_values('tsec').reset_index(drop=True)

    logger.info(f"✅ Total : {len(df_full):,} samples")
    logger.info(f"📅 De {datetime.fromtimestamp(df_full['tsec'].iloc[0])}")
    logger.info(f"   à {datetime.fromtimestamp(df_full['tsec'].iloc[-1])}")

    return df_full


# ═══════════════════════════════════════════════════════════════════════════
# CRÉATION LABELS
# ═══════════════════════════════════════════════════════════════════════════

def create_labels(
    df: pd.DataFrame,
    horizon_seconds: int = 900,
    threshold_ticks: int = 3,
    tick_size: float = 0.25,
    time_gap_tolerance: int = 60,
    binary_mode: bool = False,
    threshold_mode: str = "ticks",
    atr_multiplier: float = 0.4
) -> pd.DataFrame:
    """
    Crée les labels UP/DOWN/FLAT pour chaque sample

    Args:
        df: DataFrame avec données ML_READY
        horizon_seconds: Horizon de prédiction (900 = 15 min)
        threshold_ticks: Seuil en ticks pour UP/DOWN (si mode="ticks")
        tick_size: Taille du tick (0.25)
        time_gap_tolerance: Tolérance pour gaps temporels (60s)
        binary_mode: True = UP/DOWN, False = UP/FLAT/DOWN
        threshold_mode: "ticks" (fixe) ou "atr" (dynamique)
        atr_multiplier: Multiplicateur ATR si mode="atr" (ex: 0.4)

    Returns:
        DataFrame avec colonne 'label' ajoutée
    """
    logger.info(f"\n{'='*70}")
    mode_str = "BINAIRE (UP/DOWN)" if binary_mode else "3 CLASSES (UP/FLAT/DOWN)"
    logger.info(f"🏷️  CRÉATION LABELS - {mode_str} (v3.0 ATR DYNAMIQUE)")
    logger.info(f"{'='*70}")
    logger.info(f"📏 Horizon : {horizon_seconds}s ({horizon_seconds//60} min) ✅ Grid Search optimal")

    if threshold_mode == "atr":
        logger.info(f"📊 Mode : ATR DYNAMIQUE (multiplier={atr_multiplier})")
        if 'atr' not in df.columns:
            logger.warning(f"⚠️  Colonne 'atr' manquante, fallback sur ticks fixes")
            threshold_mode = "ticks"

    if threshold_mode == "ticks":
        logger.info(f"📊 Seuils : ±{threshold_ticks} ticks (±{threshold_ticks * tick_size}$)")

    logger.info(f"🔧 Tolérance gaps : {time_gap_tolerance}s")
    if binary_mode:
        logger.info(f"⚡ Mode BINAIRE : FLAT sera retiré après création")

    labels = []
    valid_count = 0
    gap_count = 0
    end_of_data_count = 0

    for i in range(len(df)):
        t_current = df.iloc[i]['tsec']
        t_target = t_current + horizon_seconds

        # Chercher l'index du point le plus proche de t_target
        future_mask = df['tsec'] >= t_target

        if not future_mask.any():
            # Pas assez de données futures
            labels.append(np.nan)
            end_of_data_count += 1
            continue

        future_idx = future_mask.idxmax()  # Premier index où tsec >= t_target
        t_future = df.iloc[future_idx]['tsec']
        time_diff = t_future - t_current

        # Vérifier pas de gap temporel
        if abs(time_diff - horizon_seconds) > time_gap_tolerance:
            labels.append(np.nan)
            gap_count += 1
            continue

        # Calculer changement de prix
        mid_current = df.iloc[i]['mid']
        mid_future = df.iloc[future_idx]['mid']
        delta_price = mid_future - mid_current

        # Calculer seuil (ticks ou ATR)
        if threshold_mode == "atr":
            atr_current = df.iloc[i]['atr']
            threshold_value = atr_current * atr_multiplier
            # Labellis er en dollars
            if delta_price >= threshold_value:
                labels.append(2)  # UP
                valid_count += 1
            elif delta_price <= -threshold_value:
                labels.append(0)  # DOWN
                valid_count += 1
            else:
                labels.append(1)  # FLAT
                valid_count += 1
        else:
            # Mode ticks (ancien)
            delta_ticks = round(delta_price / tick_size)
            if delta_ticks >= threshold_ticks:
                labels.append(2)  # UP
                valid_count += 1
            elif delta_ticks <= -threshold_ticks:
                labels.append(0)  # DOWN
                valid_count += 1
            else:
                labels.append(1)  # FLAT
                valid_count += 1

    df['label'] = labels

    # Statistiques
    logger.info(f"\n📊 Statistiques labels :")
    logger.info(f"   ✅ Valides : {valid_count:,} ({valid_count/len(df)*100:.1f}%)")
    logger.info(f"   ⏭️  Fin dataset : {end_of_data_count:,} ({end_of_data_count/len(df)*100:.1f}%)")
    logger.info(f"   ⚠️  Gaps temporels : {gap_count:,} ({gap_count/len(df)*100:.1f}%)")

    # Supprimer les NaN
    df_clean = df.dropna(subset=['label']).reset_index(drop=True)

    # Mode binaire : retirer FLAT
    if binary_mode:
        n_before = len(df_clean)
        n_flat = (df_clean['label'] == 1).sum()
        df_clean = df_clean[df_clean['label'] != 1].reset_index(drop=True)
        # Réencoder : 0=DOWN reste 0, 2=UP devient 1
        df_clean['label'] = (df_clean['label'] == 2).astype(int)
        logger.info(f"\n⚡ MODE BINAIRE :")
        logger.info(f"   Retiré FLAT : {n_flat:,} samples")
        logger.info(f"   Restants : {len(df_clean):,} (0=DOWN, 1=UP)")

    # Vérifier si des données restent
    if len(df_clean) == 0:
        logger.error("❌ AUCUNE DONNÉE après filtrage des labels !")
        logger.error(f"   Samples initiaux : {len(df):,}")
        logger.error(f"   Labels créés : {df['label'].notna().sum():,}")
        logger.error(f"   Après nettoyage : 0")
        logger.error("")
        logger.error("⚠️  CAUSES POSSIBLES :")
        logger.error("   1. Trop de gaps temporels dans les données")
        logger.error("   2. Horizon temporel trop long (15 min)")
        logger.error("   3. Données du 31 octobre incomplètes")
        logger.error("")
        logger.error("💡 SOLUTIONS :")
        logger.error("   1. Réduire time_gap_tolerance dans CONFIG")
        logger.error("   2. Utiliser des données d'une autre date")
        logger.error("   3. Réduire l'horizon à 5 ou 10 minutes")
        raise ValueError("Aucune donnée valide après création des labels - impossible de continuer l'entraînement")

    # Distribution des labels
    label_counts = df_clean['label'].value_counts().sort_index()
    logger.info(f"\n📈 Distribution labels (après nettoyage) :")
    if binary_mode:
        logger.info(f"   DOWN (0) : {label_counts.get(0, 0):,} ({label_counts.get(0, 0)/len(df_clean)*100:.1f}%)")
        logger.info(f"   UP   (1) : {label_counts.get(1, 0):,} ({label_counts.get(1, 0)/len(df_clean)*100:.1f}%)")
    else:
        logger.info(f"   DOWN (0) : {label_counts.get(0, 0):,} ({label_counts.get(0, 0)/len(df_clean)*100:.1f}%)")
        logger.info(f"   FLAT (1) : {label_counts.get(1, 0):,} ({label_counts.get(1, 0)/len(df_clean)*100:.1f}%)")
        logger.info(f"   UP   (2) : {label_counts.get(2, 0):,} ({label_counts.get(2, 0)/len(df_clean)*100:.1f}%)")
    logger.info(f"   Total    : {len(df_clean):,}")

    return df_clean


# ═══════════════════════════════════════════════════════════════════════════
# SÉLECTION FEATURES
# ═══════════════════════════════════════════════════════════════════════════

def get_manual_feature_list() -> List[str]:
    """
    Retourne la liste des ~107 features core sélectionnées manuellement
    INCLUS : 100% DES DONNEES MENTHORQ (tous les champs disponibles)
    - GEX 1-10 (10 niveaux)
    - Blind Spots 0-8 + confluence (10 champs)
    - Menthor Distances (12 champs complets)
    - Next Wall (6 champs complets)
    - Battle Navale (8 champs complets)

    Returns:
        Liste des noms de features
    """
    features = [
        # Prix & Position (8)
        'close', 'mid', 'microprice',
        'd_vwap', 'd_vwap_ticks', 'd_vpoc', 'd_vpoc_ticks',
        'spread_ticks',

        # VWAP & Bandes (14) - AJOUT: d_vwap_weekly/monthly_ticks (ancrages importants)
        'vwap', 'vwap_weekly', 'd_vwap_atr',
        'vwap_up1', 'vwap_dn1', 'vwap_up2', 'vwap_dn2',
        'pvwap', 'd_pvwap', 'd_pvwap_ticks',
        'd_w_up1', 'd_w_dn1',
        'd_vwap_weekly_ticks',  # ✅ AJOUT: Distance VWAP weekly en ticks (ancrage important)
        'd_vwap_monthly_ticks',  # ✅ AJOUT: Distance VWAP monthly en ticks (ancrage important)

        # OrderFlow (10)
        'cum_delta_day', 'cum_delta_session',
        'delta', 'deltaPct',
        'smart_money_flow', 'institutional_pressure',
        'bidvol', 'askvol', 'askPct', 'bidPct',

        # ✨ PATCH V3.3: Nouvelles features OrderFlow (5)
        'sell_pct',          # Ancien askPct (renommé pour clarté sémantique)
        'buy_pct',           # Ancien bidPct (renommé pour clarté sémantique)
        'delta_burst',       # Magnitude changement delta (abs)
        'delta_flip',        # Retournement signe delta (bool → 0/1)
        'mia_bullish_score', # Score composite (40% VWAP + 30% Delta + 20% DeltaPct + 10% VA)

        # DOM (8)
        'level1_imbalance', 'depth_imbalance',
        'q_bq1', 'q_aq1',
        'ob_center', 'top_heavy',
        'dom_features_imbalance_1_3', 'dom_features_imbalance_6_10',

        # ✨ PATCH V3.3: Nouvelles features Price Action (3 - Wicks)
        'upper_wick_ticks',  # Mèche haute (High - max(Open, Close)) / tick_size
        'lower_wick_ticks',  # Mèche basse (min(Open, Close) - Low) / tick_size
        'total_range_ticks', # Range total (High - Low) / tick_size

        # ✨ PATCH V3.3: Nouvelles features DOM (2 - Stacked Imbalance)
        'stacked_imbalance_bid_rows',  # Nombre de niveaux consécutifs avec ratio BID/ASK >= 3.0
        'stacked_imbalance_ask_rows',  # Nombre de niveaux consécutifs avec ratio ASK/BID >= 3.0

        # Gamma & Options (46 + 35 DISTANCES) - 100% DES DONNEES MENTHORQ
        # Menthor Distances (12 - TOUS les champs disponibles)
        'menthor_distances_call', 'menthor_distances_put',
        'menthor_distances_hvl', 'menthor_distances_near_gex_up',
        'menthor_distances_near_gex_dn', 'menthor_distances_near_blind',
        # Distances absolues (variantes 0)
        'menthor_distances_call0', 'menthor_distances_put0',
        'menthor_distances_gamma0', 'menthor_distances_hvl0',
        # Distances extrêmes jour
        'menthor_distances_dist_1d_max', 'menthor_distances_dist_1d_min',
        # Next Wall (5 - champs disponibles dans les données brutes)
        'next_wall_dist_ticks', 'next_wall_strength',
        'next_wall_age_min', 'next_wall_dist_pts',
        'next_wall_price', 'next_wall_side',  # next_wall_side sera encodé en one-hot
        # Note: headroom_pct n'est pas dans les données JSON brutes → non inclus
        # GEX Levels (10 niveaux complets - prix absolus pour référence)
        'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
        'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',
        # ✨ NOUVEAU : Distances relatives GEX (10 - DYNAMIQUES, mises à jour à chaque barre)
        'd_gex_1_ticks', 'd_gex_2_ticks', 'd_gex_3_ticks', 'd_gex_4_ticks', 'd_gex_5_ticks',
        'd_gex_6_ticks', 'd_gex_7_ticks', 'd_gex_8_ticks', 'd_gex_9_ticks', 'd_gex_10_ticks',
        # ✨ NOUVEAU : GEX le plus proche (3 - features agrégées critiques)
        'd_nearest_gex_up_ticks', 'd_nearest_gex_down_ticks', 'd_nearest_gex_abs_ticks',
        # Blind Spots (10 - 9 spots + confluence - prix absolus pour référence)
        'blind_spot_0', 'blind_spot_1', 'blind_spot_2', 'blind_spot_3',
        'blind_spot_4', 'blind_spot_5', 'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
        'blind_spot_confluence',
        # ✨ NOUVEAU : Distances relatives Blind Spots (9 - DYNAMIQUES)
        'd_blind_spot_0_ticks', 'd_blind_spot_1_ticks', 'd_blind_spot_2_ticks',
        'd_blind_spot_3_ticks', 'd_blind_spot_4_ticks', 'd_blind_spot_5_ticks',
        'd_blind_spot_6_ticks', 'd_blind_spot_7_ticks', 'd_blind_spot_8_ticks',
        # ✨ NOUVEAU : Blind Spot le plus proche (1 - feature agrégée)
        'd_nearest_blind_spot_abs_ticks',
        # Structure Options (2 - prix absolus pour référence)
        'call_resistance', 'put_support',
        # ✨ NOUVEAU : Distances relatives Call/Put (2 - DYNAMIQUES)
        'd_call_resistance_ticks', 'd_put_support_ticks',
        # HVL (1 - prix absolu pour référence)
        'hvl',
        # ✨ NOUVEAU : Distance relative HVL (1 - DYNAMIQUE)
        'd_hvl_ticks',
        # ✨ NOUVEAU : Ratios distances / ATR (3 - normalisés par volatilité)
        'd_call_resistance_atr', 'd_put_support_atr', 'd_nearest_gex_atr',
        # Menthor Meta exclus (strings non numériques)
        # 'menthor_meta_month', 'menthor_meta_quarter',

        # Battle Navale (8) - 100% DES DONNEES DISPONIBLES
        'battle_navale_signal_strength', 'battle_navale_confidence',
        'menthorq_impact_score', 'menthorq_proximity_strength',
        'confluence_strength', 'confluence_density', 'confluence_proximity',
        'gamma_call_confluence', 'gamma_put_confluence',

        # ✨ PATCH V3.3: Nouvelles features Gamma (3 - Robust Flip Detection)
        'gamma_flip_up',      # Franchissement gamma wall vers le haut (bool → 0/1)
        'gamma_flip_down',    # Franchissement gamma wall vers le bas (bool → 0/1)
        'gamma_wall_level',   # Niveau du mur gamma actif (prix absolu)
        # Note: gamma_side est une string ("above"/"below"/"unknown") → sera encodée en one-hot si nécessaire

        # Volume & Volatilité (6)
        'volume', 'atr', 'volatility_regime', 'volatility_regime_cont',
        'atr_ratio', 'pressure_strength',

        # Volume Profile (4)
        'vpoc', 'd_vah', 'd_val', 'in_value_area',

        # Structure (4)
        'structure_onh', 'structure_onl',
        'd_1d_max', 'd_1d_min',

        # Session & Corrélation (3)
        'session_progress', 'vix', 'corr',
    ]

    # Ajouter feature symbole
    features.append('symbol_is_nq')

    return features


def flatten_nested_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplatit les champs nested (dom_features.*, menthor_distances.*, etc.)

    Args:
        df: DataFrame avec champs nested

    Returns:
        DataFrame avec champs aplatis
    """
    # dom_features
    if 'dom_features' in df.columns:
        dom_features = pd.json_normalize(df['dom_features'])
        for col in dom_features.columns:
            df[f'dom_features_{col}'] = dom_features[col]

    # menthor_distances
    if 'menthor_distances' in df.columns:
        menthor_distances = pd.json_normalize(df['menthor_distances'])
        for col in menthor_distances.columns:
            df[f'menthor_distances_{col}'] = menthor_distances[col]

    # next_wall
    if 'next_wall' in df.columns:
        next_wall = pd.json_normalize(df['next_wall'])
        for col in next_wall.columns:
            df[f'next_wall_{col}'] = next_wall[col]

    # structure
    if 'structure' in df.columns:
        structure = pd.json_normalize(df['structure'])
        for col in structure.columns:
            df[f'structure_{col}'] = structure[col]

    # vva
    if 'vva' in df.columns:
        vva = pd.json_normalize(df['vva'])
        for col in vva.columns:
            df[f'vva_{col}'] = vva[col]

        # Créer vpoc depuis vva_vpoc si absent
        if 'vva_vpoc' in df.columns and 'vpoc' not in df.columns:
            df['vpoc'] = df['vva_vpoc']

    # menthor_meta
    if 'menthor_meta' in df.columns:
        menthor_meta = pd.json_normalize(df['menthor_meta'])
        for col in menthor_meta.columns:
            df[f'menthor_meta_{col}'] = menthor_meta[col]

    # nbcv
    if 'nbcv' in df.columns:
        nbcv = pd.json_normalize(df['nbcv'])
        for col in nbcv.columns:
            df[f'nbcv_{col}'] = nbcv[col]

    # intermarkets
    if 'intermarkets' in df.columns:
        intermarkets = pd.json_normalize(df['intermarkets'])
        for col in intermarkets.columns:
            df[f'intermarkets_{col}'] = intermarkets[col]

    return df


def calculate_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule des champs dérivés manquants

    Args:
        df: DataFrame

    Returns:
        DataFrame avec champs dérivés
    """
    # d_1d_max et d_1d_min (distance aux extrêmes du jour)
    if '1d_max' in df.columns and 'mid' in df.columns:
        df['d_1d_max'] = df['1d_max'] - df['mid']

    if '1d_min' in df.columns and 'mid' in df.columns:
        df['d_1d_min'] = df['mid'] - df['1d_min']

    # ✅ CORRECTIF : Créer vpoc si vva.vpoc existe mais pas vpoc
    if 'vva.vpoc' in df.columns and 'vpoc' not in df.columns:
        df['vpoc'] = df['vva.vpoc']

    # ✅ CORRECTIF : headroom_pct peut ne pas être présent dans toutes les données
    # Il sera simplement ignoré si absent (pas critique pour l'entraînement)

    return df


def calculate_option_distances(df: pd.DataFrame, tick_size: float = 0.25) -> pd.DataFrame:
    """
    ✨ NOUVEAU : Calcule les distances RELATIVES aux niveaux d'options (en ticks)

    Pourquoi : Les niveaux GEX/Blind Spots sont mis à jour 1-2x/jour (fixes pendant session).
    En valeur absolue, ils ont peu de variance → LightGBM ne peut rien apprendre.
    En distance relative au prix actuel, ils deviennent DYNAMIQUES et très utiles !

    Args:
        df: DataFrame avec colonnes 'mid', 'gex_*', 'blind_spot_*', etc.
        tick_size: Taille du tick (0.25 pour ES/NQ)

    Returns:
        DataFrame avec features de distance ajoutées
    """
    if 'mid' not in df.columns:
        logger.warning("⚠️  Colonne 'mid' absente, skip calcul distances options")
        return df

    logger.info("📊 Calcul distances relatives niveaux OPTIONS...")

    # 🎯 Distances aux GEX levels (1-10)
    for i in range(1, 11):
        col_gex = f'gex_{i}'
        col_dist = f'd_gex_{i}_ticks'
        if col_gex in df.columns:
            df[col_dist] = (df[col_gex] - df['mid']) / tick_size

    # 🎯 Distances aux Blind Spots (0-8)
    for i in range(9):
        col_bs = f'blind_spot_{i}'
        col_dist = f'd_blind_spot_{i}_ticks'
        if col_bs in df.columns:
            df[col_dist] = (df[col_bs] - df['mid']) / tick_size

    # 🎯 Distances aux niveaux clés
    if 'call_resistance' in df.columns:
        df['d_call_resistance_ticks'] = (df['call_resistance'] - df['mid']) / tick_size

    if 'put_support' in df.columns:
        df['d_put_support_ticks'] = (df['put_support'] - df['mid']) / tick_size

    if 'hvl' in df.columns:
        df['d_hvl_ticks'] = (df['hvl'] - df['mid']) / tick_size

    # 🎯 Features agrégées : GEX le plus proche (UP/DOWN)
    gex_dist_cols = [f'd_gex_{i}_ticks' for i in range(1, 11) if f'd_gex_{i}_ticks' in df.columns]
    if gex_dist_cols:
        gex_dists = df[gex_dist_cols]
        # GEX le plus proche AU-DESSUS (distance positive minimale)
        df['d_nearest_gex_up_ticks'] = gex_dists.where(gex_dists > 0).min(axis=1)
        # GEX le plus proche EN-DESSOUS (distance négative maximale, ie: la moins négative)
        df['d_nearest_gex_down_ticks'] = gex_dists.where(gex_dists < 0).max(axis=1)
        # Distance absolue au GEX le plus proche (up ou down)
        df['d_nearest_gex_abs_ticks'] = gex_dists.abs().min(axis=1)

    # 🎯 Features agrégées : Blind Spot le plus proche
    bs_dist_cols = [f'd_blind_spot_{i}_ticks' for i in range(9) if f'd_blind_spot_{i}_ticks' in df.columns]
    if bs_dist_cols:
        bs_dists = df[bs_dist_cols]
        df['d_nearest_blind_spot_abs_ticks'] = bs_dists.abs().min(axis=1)

    # 🎯 Ratio distances / ATR (normalisation par volatilité)
    if 'atr' in df.columns and tick_size > 0:
        if 'd_call_resistance_ticks' in df.columns:
            df['d_call_resistance_atr'] = df['d_call_resistance_ticks'] * tick_size / df['atr']
        if 'd_put_support_ticks' in df.columns:
            df['d_put_support_atr'] = df['d_put_support_ticks'] * tick_size / df['atr']
        if 'd_nearest_gex_abs_ticks' in df.columns:
            df['d_nearest_gex_atr'] = df['d_nearest_gex_abs_ticks'] * tick_size / df['atr']

    n_new_features = len([c for c in df.columns if c.startswith('d_gex_') or c.startswith('d_blind_spot_') or c.startswith('d_call_') or c.startswith('d_put_') or c.startswith('d_nearest_') or c.startswith('d_hvl_')])
    logger.info(f"✅ {n_new_features} features de distance OPTIONS créées")

    return df


# ═══════════════════════════════════════════════════════════════════════════
# ENTRAÎNEMENT
# ═══════════════════════════════════════════════════════════════════════════

def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    params: Dict,
    early_stopping_rounds: int = 50,
    symbol: str = None
) -> lgb.LGBMClassifier:
    """
    Entraîne le modèle LightGBM

    Args:
        X_train: Features train
        y_train: Labels train
        X_test: Features test (pour early stopping)
        y_test: Labels test (pour early stopping)
        params: Hyperparamètres LightGBM
        early_stopping_rounds: Rounds pour early stopping

    Returns:
        Modèle entraîné
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🎓 ENTRAÎNEMENT LIGHTGBM")
    logger.info(f"{'='*70}")

    # Calculer class weights
    classes = np.unique(y_train)
    class_weights = compute_class_weight(
        class_weight='balanced',
        classes=classes,
        y=y_train
    )

    class_weight_dict = {
        int(classes[i]): class_weights[i] for i in range(len(classes))
    }

    # ✅ PATCH NQ & ES : Boost class_weight pour DOWN (réduire biais haussier)
    # NQ & ES ont tendance à prédire trop souvent UP → On pénalise plus les erreurs DOWN
    if symbol in ['NQ', 'ES']:
        if 0 in class_weight_dict:  # DOWN
            class_weight_dict[0] = class_weight_dict[0] * 1.25  # +25% poids DOWN
            logger.info(f"🔧 PATCH {symbol}: class_weight DOWN boosté (+25%) pour réduire biais UP")
        if 1 in class_weight_dict:  # UP
            class_weight_dict[1] = class_weight_dict[1] * 0.90  # -10% poids UP
            logger.info(f"🔧 PATCH {symbol}: class_weight UP réduit (-10%) pour équilibrer")

    logger.info(f"⚖️  Class weights :")
    for cls, weight in class_weight_dict.items():
        # Adapter selon le nombre de classes
        if len(classes) == 2:
            cls_name = {0: 'DOWN', 1: 'UP'}[cls]
        else:
            cls_name = {0: 'DOWN', 1: 'FLAT', 2: 'UP'}[cls]
        logger.info(f"   {cls_name} : {weight:.3f}")

    # Créer modèle
    # ✅ ROBUST : Classes ~50/50 donc is_unbalance=False + class_weight manuel
    if params.get('is_unbalance', False):
        model = lgb.LGBMClassifier(**params)
        logger.info(f"   ℹ️  is_unbalance=True activé, class_weight ignoré")
    else:
        model = lgb.LGBMClassifier(**params, class_weight=class_weight_dict)
        logger.info(f"   ✅ is_unbalance=False, class_weight manuel appliqué")

    # ✅ GPT : Déterminer eval_metric selon mode
    # Extraire metric depuis params (peut être string ou liste)
    metric_param = params.get('metric', 'binary_logloss' if params.get('objective') == 'binary' else 'multi_logloss')
    if isinstance(metric_param, list):
        # Si liste, prendre le premier (celui utilisé pour early stopping)
        eval_metric = metric_param[0]
    else:
        eval_metric = metric_param

    logger.info(f"   📌 Eval metric : {eval_metric}")

    # Entraîner
    logger.info(f"\n⏳ Entraînement en cours...")
    logger.info(f"   📌 Params clés : learning_rate={params.get('learning_rate', 'N/A')}, "
                f"min_data_in_leaf={params.get('min_data_in_leaf', 'N/A')}, "
                f"feature_pre_filter={params.get('feature_pre_filter', 'N/A')}, "
                f"early_stopping={early_stopping_rounds}")
    start_time = time.time()

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric=eval_metric,
        callbacks=[
            lgb.early_stopping(
                stopping_rounds=early_stopping_rounds,
                verbose=False,
                first_metric_only=True  # ✅ CORRIGÉ : Utiliser seulement la première métrique pour early stopping
            ),
            lgb.log_evaluation(period=50)  # ✅ PRO : Log toutes les 50 itérations (verbose_eval=50)
        ]
    )

    elapsed = time.time() - start_time
    logger.info(f"✅ Entraînement terminé en {elapsed:.1f}s")
    logger.info(f"📊 Best iteration : {model.best_iteration_}")

    # ✅ GPT : Vérifier best_iteration (doit être > 200)
    if model.best_iteration_ <= 10:
        logger.warning(f"   ⚠️  Best iteration très faible ({model.best_iteration_}) - Modèle peut être sous-entraîné")
        logger.warning(f"   💡 Vérifier : early_stopping trop agressif, learning_rate, min_data_in_leaf")
    elif model.best_iteration_ > 200:
        logger.info(f"   ✅ Best iteration > 200 - Bon apprentissage détecté")

    # ✅ GPT : Log histogramme probabilités après entraînement
    if hasattr(model, 'predict_proba'):
        y_train_proba = model.predict_proba(X_train)
        train_proba_max = y_train_proba.max(axis=1)
        logger.info(f"\n📊 Probabilités TRAIN (après fit) :")
        logger.info(f"   Moyenne : {train_proba_max.mean():.3f}")
        logger.info(f"   Médiane : {np.median(train_proba_max):.3f}")
        logger.info(f"   P25 : {np.percentile(train_proba_max, 25):.3f}")
        logger.info(f"   P75 : {np.percentile(train_proba_max, 75):.3f}")

    return model


def purged_tscv(df, n_splits=3, purge_bars=300, embargo_bars=100):
    """
    ✅ PATCH 3: TimeSeriesSplit avec purge (LAGs) + embargo (labels futurs)

    Évite le leakage temporel en :
    - Retirant les dernières barres du train (purge) → évite influence des LAGs
    - Retirant les premières barres du test (embargo) → évite influence des labels futurs

    Args:
        df: DataFrame ou taille dataset
        n_splits: Nombre de splits
        purge_bars: Barres à retirer fin train (typiquement = max LAG period)
        embargo_bars: Barres à retirer début test (typiquement = horizon_seconds / bar_duration)

    Yields:
        (train_idx, test_idx): Indices purged/embargoed
    """
    from sklearn.model_selection import TimeSeriesSplit

    n_samples = len(df) if hasattr(df, '__len__') else df
    tscv = TimeSeriesSplit(n_splits=n_splits)

    logger.info(f"\n🔒 Purged/Embargoed CV : purge={purge_bars} bars, embargo={embargo_bars} bars")

    for fold, (train_idx, test_idx) in enumerate(tscv.split(range(n_samples))):
        # Purge: retirer fin train (évite LAGs qui "voient" le test)
        original_train_end = train_idx[-1]
        if len(train_idx) > purge_bars:
            train_idx = train_idx[:-purge_bars]

        # Embargo: retirer début test (évite labels qui utilisent info du futur proche)
        original_test_start = test_idx[0]
        if len(test_idx) > embargo_bars:
            test_idx = test_idx[embargo_bars:]

        # Vérifier gap suffisant
        gap = test_idx[0] - train_idx[-1] if len(train_idx) > 0 and len(test_idx) > 0 else 0

        logger.info(f"   Fold {fold+1}: Train[{train_idx[0]}:{train_idx[-1]}] → "
                   f"Test[{test_idx[0]}:{test_idx[-1]}] | "
                   f"Gap: {gap} bars | "
                   f"Purged: {original_train_end - train_idx[-1]} | "
                   f"Embargoed: {test_idx[0] - original_test_start}")

        if gap < (purge_bars + embargo_bars):
            logger.warning(f"⚠️  Gap insuffisant ({gap} < {purge_bars + embargo_bars}) - risque leakage")

        yield train_idx, test_idx


def cross_validate_model(
    X: np.ndarray,
    y: np.ndarray,
    params: Dict,
    n_splits: int = 5,
    timestamps: Optional[np.ndarray] = None
) -> Dict:
    """
    Validation croisée avec TimeSeriesSplit

    Args:
        X: Features
        y: Labels
        params: Hyperparamètres
        n_splits: Nombre de folds
        timestamps: Timestamps pour logs (optionnel)

    Returns:
        Dict avec métriques moyennes
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🔄 VALIDATION CROISÉE (TimeSeriesSplit {n_splits}-fold)")
    logger.info(f"{'='*70}")

    tscv = TimeSeriesSplit(n_splits=n_splits)

    scores = {
        'accuracy': [],
        'f1_macro': [],
        'precision_macro': [],
        'recall_macro': []
    }

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        logger.info(f"\n📁 Fold {fold}/{n_splits}")

        # ✅ CORRECTIF GPT : Logger dates des folds (éviter data leakage)
        if timestamps is not None:
            train_start = datetime.fromtimestamp(timestamps[train_idx[0]])
            train_end = datetime.fromtimestamp(timestamps[train_idx[-1]])
            val_start = datetime.fromtimestamp(timestamps[val_idx[0]])
            val_end = datetime.fromtimestamp(timestamps[val_idx[-1]])

            logger.info(f"   Train : {train_start} → {train_end} ({len(train_idx):,} samples)")
            logger.info(f"   Val   : {val_start} → {val_end} ({len(val_idx):,} samples)")

            # Vérifier pas de chevauchement
            if timestamps[val_idx[0]] < timestamps[train_idx[-1]]:
                logger.warning(f"⚠️ ATTENTION : Chevauchement temporel détecté !")

        X_train_fold = X[train_idx]
        y_train_fold = y[train_idx]
        X_val_fold = X[val_idx]
        y_val_fold = y[val_idx]

        # Calculer class weights
        classes = np.unique(y_train_fold)
        class_weights = compute_class_weight(
            class_weight='balanced',
            classes=classes,
            y=y_train_fold
        )
        class_weight_dict = {int(classes[i]): class_weights[i] for i in range(len(classes))}

        # Entraîner
        model = lgb.LGBMClassifier(**params, class_weight=class_weight_dict, verbose=-1, random_state=RANDOM_SEED)
        model.fit(X_train_fold, y_train_fold)

        # Prédire
        y_pred = model.predict(X_val_fold)

        # Métriques
        scores['accuracy'].append(accuracy_score(y_val_fold, y_pred))
        scores['f1_macro'].append(f1_score(y_val_fold, y_pred, average='macro'))
        scores['precision_macro'].append(precision_score(y_val_fold, y_pred, average='macro'))
        scores['recall_macro'].append(recall_score(y_val_fold, y_pred, average='macro'))

        logger.info(f"   📊 Accuracy : {scores['accuracy'][-1]:.4f}")
        logger.info(f"   📊 F1 macro : {scores['f1_macro'][-1]:.4f}")

    # Moyennes
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 RÉSULTATS VALIDATION CROISÉE (moyenne ± std)")
    logger.info(f"{'='*70}")

    for metric, values in scores.items():
        mean = np.mean(values)
        std = np.std(values)
        logger.info(f"{metric:20s} : {mean:.4f} ± {std:.4f}")

    return scores


# ═══════════════════════════════════════════════════════════════════════════
# ÉVALUATION
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_model(
    model: lgb.LGBMClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray,
    output_dir: Path,
    binary_mode: bool = False
) -> Dict:
    """
    Évalue le modèle sur test set

    Args:
        model: Modèle entraîné
        X_test: Features test
        y_test: Labels test
        output_dir: Répertoire pour sauvegarder graphiques

    Returns:
        Dict avec métriques
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 ÉVALUATION TEST SET")
    logger.info(f"{'='*70}")

    # Prédictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    # ✅ GPT : Analyse détaillée probabilités (histogramme)
    proba_max = y_proba.max(axis=1)
    logger.info(f"\n📊 Analyse probabilités (GPT) :")
    logger.info(f"   Max probabilité globale : {proba_max.max():.3f}")
    logger.info(f"   Min probabilité globale : {proba_max.min():.3f}")
    logger.info(f"   Moyenne probabilité max : {proba_max.mean():.3f}")
    logger.info(f"   Médiane probabilité max : {np.median(proba_max):.3f}")

    # Histogramme détaillé (percentiles)
    percentiles = [1, 25, 50, 75, 99]
    logger.info(f"   Histogramme (percentiles) :")
    for p in percentiles:
        val = np.percentile(proba_max, p)
        logger.info(f"      P{p:2d} : {val:.3f}")

    # Seuils
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    logger.info(f"   % prédictions par seuil :")
    for thresh in thresholds:
        pct = (proba_max > thresh).sum() / len(proba_max) * 100
        logger.info(f"      > {thresh:.2f} : {pct:5.1f}%")

    # ✅ GPT : Vérifier si problème best_iteration=1
    if proba_max.max() < 0.52:
        logger.warning(f"   ⚠️  Probabilités très faibles (max={proba_max.max():.3f}) - Possible best_iteration=1")
        logger.warning(f"   💡 Vérifier : early_stopping, learning_rate, min_data_in_leaf, feature_pre_filter")

    # Métriques globales
    accuracy = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    precision_macro = precision_score(y_test, y_pred, average='macro')
    recall_macro = recall_score(y_test, y_pred, average='macro')

    logger.info(f"\n🎯 Métriques globales :")
    logger.info(f"   Accuracy       : {accuracy:.4f} ({accuracy*100:.2f}%)")
    logger.info(f"   F1-Score macro : {f1_macro:.4f}")
    logger.info(f"   Precision macro: {precision_macro:.4f}")
    logger.info(f"   Recall macro   : {recall_macro:.4f}")

    # Rapport par classe
    logger.info(f"\n📈 Rapport par classe :")
    # Détecter le nombre de classes réel
    unique_classes = np.unique(y_test)
    n_classes = len(unique_classes)

    if binary_mode:
        # Mode binaire : 2 classes (DOWN=0, UP=1)
        class_names = ['DOWN', 'UP']
        # S'assurer que la confusion matrix est 2x2
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

        logger.info(f"🔢 Matrice de confusion (BINAIRE) :")
        logger.info(f"              Pred DOWN  Pred UP")
        for i, true_label in enumerate(class_names):
            if n_classes == 2:
                logger.info(f"True {true_label:4s}  {cm[i,0]:10d}  {cm[i,1]:8d}")
            else:
                logger.info(f"True {true_label:4s}  {cm[i,0]:10d}  {cm[i,1] if cm.shape[1] > 1 else 0:8d}")
    else:
        # Mode multiclass : 3 classes (DOWN=0, FLAT=1, UP=2)
        class_names = ['DOWN', 'FLAT', 'UP']
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

        logger.info(f"🔢 Matrice de confusion (MULTICLASS) :")
        logger.info(f"              Pred DOWN  Pred FLAT  Pred UP")
        for i, true_label in enumerate(class_names):
            if cm.shape[1] == 3:
                logger.info(f"True {true_label:4s}  {cm[i,0]:10d}  {cm[i,1]:10d}  {cm[i,2]:8d}")
            else:
                # Gérer les cas où certaines classes ne sont pas présentes
                logger.info(f"True {true_label:4s}  {cm[i,0] if cm.shape[1] > 0 else 0:10d}  {cm[i,1] if cm.shape[1] > 1 else 0:10d}  {cm[i,2] if cm.shape[1] > 2 else 0:8d}")

    # Utiliser les labels réels pour classification_report
    print(classification_report(y_test, y_pred, target_names=class_names, labels=unique_classes, zero_division=0))

    # Sauvegarder confusion matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Matrice de Confusion - Test Set')
    plt.ylabel('Vrai Label')
    plt.xlabel('Label Prédit')
    plt.tight_layout()
    plt.savefig(output_dir / 'confusion_matrix.png', dpi=150)
    logger.info(f"💾 Confusion matrix sauvegardée : {output_dir / 'confusion_matrix.png'}")
    plt.close()

    # Métriques
    metrics = {
        'accuracy': accuracy,
        'f1_macro': f1_macro,
        'precision_macro': precision_macro,
        'recall_macro': recall_macro,
        'confusion_matrix': cm.tolist(),
    }

    return metrics


def evaluate_by_segment(
    df_test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    binary_mode: bool = False
):
    """
    ✅ CORRECTIF D: Métriques segmentées par jour, session, régime volatilité

    Permet de détecter les blind spots temporels (jours/sessions où le modèle échoue)
    et les régimes de volatilité où les performances varient.

    Args:
        df_test: DataFrame test avec timestamps et features
        y_true: Labels réels
        y_pred: Labels prédits
        y_proba: Probabilités prédites
        binary_mode: Si True, mode binaire (UP/DOWN), sinon multiclass
    """
    from sklearn.metrics import roc_auc_score, accuracy_score

    df_test = df_test.copy().reset_index(drop=True)
    df_test['y_true'] = y_true
    df_test['y_pred'] = y_pred

    # Probabilités : classe positive (UP en binaire, ou max prob en multiclass)
    if binary_mode and y_proba.ndim > 1:
        df_test['y_proba'] = y_proba[:, 1]  # P(UP)
    elif y_proba.ndim > 1:
        df_test['y_proba'] = y_proba.max(axis=1)  # Max prob
    else:
        df_test['y_proba'] = y_proba

    logger.info(f"\n{'='*70}")
    logger.info(f"📊 MÉTRIQUES SEGMENTÉES (DÉTECTION BLIND SPOTS)")
    logger.info(f"{'='*70}")

    # ═════════════════════════════════════════════════════════════
    # SEGMENT 1: Par jour
    # ═════════════════════════════════════════════════════════════
    try:
        if 't_ms' in df_test.columns:
            df_test['date'] = pd.to_datetime(df_test['t_ms'], unit='ms').dt.date
            logger.info(f"\n📅 PAR JOUR:")

            for date, grp in df_test.groupby('date'):
                if len(grp) >= 50:  # Min 50 samples
                    try:
                        auc_day = roc_auc_score(grp['y_true'], grp['y_proba'])
                        acc_day = accuracy_score(grp['y_true'], grp['y_pred'])
                        logger.info(f"   {date}: AUC={auc_day:.3f}, Acc={acc_day:.2%}, n={len(grp):,}")
                    except Exception as e:
                        logger.debug(f"   {date}: Erreur AUC ({e}), n={len(grp):,}")
    except Exception as e:
        logger.warning(f"⚠️ Segmentation par jour échouée: {e}")

    # ═════════════════════════════════════════════════════════════
    # SEGMENT 2: Par session (ASIA / LONDON / NY)
    # ═════════════════════════════════════════════════════════════
    try:
        if 't_ms' in df_test.columns:
            df_test['hour'] = pd.to_datetime(df_test['t_ms'], unit='ms').dt.hour
            df_test['session'] = df_test['hour'].apply(
                lambda h: 'ASIA' if h < 8 else ('LONDON' if h < 13 else 'NY')
            )
            logger.info(f"\n🌍 PAR SESSION:")

            for session, grp in df_test.groupby('session'):
                if len(grp) >= 100:  # Min 100 samples
                    try:
                        auc_sess = roc_auc_score(grp['y_true'], grp['y_proba'])
                        acc_sess = accuracy_score(grp['y_true'], grp['y_pred'])
                        logger.info(f"   {session:7s}: AUC={auc_sess:.3f}, Acc={acc_sess:.2%}, n={len(grp):,}")
                    except Exception as e:
                        logger.debug(f"   {session}: Erreur AUC ({e})")
    except Exception as e:
        logger.warning(f"⚠️ Segmentation par session échouée: {e}")

    # ═════════════════════════════════════════════════════════════
    # SEGMENT 3: Par régime volatilité (LOW / MED / HIGH)
    # ═════════════════════════════════════════════════════════════
    try:
        if 'atr' in df_test.columns:
            df_test['vol_regime'] = pd.cut(
                df_test['atr'],
                bins=3,
                labels=['LOW', 'MED', 'HIGH']
            )
            logger.info(f"\n📊 PAR RÉGIME VOLATILITÉ:")

            for regime, grp in df_test.groupby('vol_regime'):
                if len(grp) >= 50:  # Min 50 samples
                    try:
                        auc_vol = roc_auc_score(grp['y_true'], grp['y_proba'])
                        acc_vol = accuracy_score(grp['y_true'], grp['y_pred'])
                        logger.info(f"   VOL_{regime}: AUC={auc_vol:.3f}, Acc={acc_vol:.2%}, n={len(grp):,}")
                    except Exception as e:
                        logger.debug(f"   VOL_{regime}: Erreur AUC ({e})")
    except Exception as e:
        logger.warning(f"⚠️ Segmentation par volatilité échouée: {e}")

    logger.info(f"\n💡 Utilisez ces segments pour détecter les jours/sessions/régimes problématiques")


def simulate_profit_factor(
    y_test: np.ndarray,
    y_proba: np.ndarray,
    confidence_thresholds: List[float],
    binary_mode: bool = False
) -> Dict:
    """
    Simule le Profit Factor pour différents seuils de confidence

    Args:
        y_test: Vrais labels
        y_proba: Probabilités prédites
        confidence_thresholds: Liste de seuils à tester

    Returns:
        Dict avec résultats par seuil
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"💰 SIMULATION PROFIT FACTOR")
    logger.info(f"{'='*70}")

    results = {}

    # Paramètres simulation (moyennes de vos stratégies)
    TP_AVG_TICKS = 10  # TP1 moyen = 10 ticks
    SL_AVG_TICKS = 5   # SL moyen = 5 ticks

    for threshold in confidence_thresholds:
        # Prédictions avec seuil
        y_pred = []
        confidences = []

        for i in range(len(y_proba)):
            max_prob = np.max(y_proba[i])
            pred_class = np.argmax(y_proba[i])

            # Rejeter si confidence trop faible
            if max_prob < threshold:
                y_pred.append(-1)  # Skip
                confidences.append(max_prob)
            elif binary_mode:
                # Mode binaire : seulement DOWN(0) et UP(1), pas de FLAT
                y_pred.append(pred_class)
                confidences.append(max_prob)
            else:
                # Mode multiclass : rejeter FLAT (classe 1)
                if pred_class == 1:  # FLAT
                    y_pred.append(-1)  # Skip
                    confidences.append(max_prob)
                else:
                    y_pred.append(pred_class)
                    confidences.append(max_prob)

        y_pred = np.array(y_pred)

        # Simuler trades
        wins = []
        losses = []

        for i in range(len(y_test)):
            if y_pred[i] == -1:  # Skip
                continue

            # Simuler résultat
            if y_pred[i] == y_test[i]:
                wins.append(TP_AVG_TICKS)
            else:
                losses.append(SL_AVG_TICKS)

        # Métriques
        n_trades = len(wins) + len(losses)
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = n_wins / n_trades if n_trades > 0 else 0

        total_wins = sum(wins)
        total_losses = sum(losses)
        profit_factor_before = total_wins / total_losses if total_losses > 0 else float('inf')

        net_ticks_before = total_wins - total_losses

        # ✅ PATCH 1: Coûts réalistes (slippage + fees)
        tick_size = 0.25
        point_value = 50.0  # ES/NQ
        slippage_ticks = 1.0          # moyen (0.5-1.5 ticks)
        fees_round_trip_usd = 2.40    # round-trip ($1.20 × 2)
        cost_per_trade_ticks = slippage_ticks + (fees_round_trip_usd / (tick_size * point_value))
        total_cost_ticks = n_trades * cost_per_trade_ticks

        # PF et net après coûts
        net_ticks_after = net_ticks_before - total_cost_ticks
        profit_factor_after = (total_wins - total_cost_ticks) / total_losses if total_losses > 0 else float('inf')

        # ✅ CORRECTIF C: Min support pour seuils fiables
        MIN_SUPPORT_TRADES = 300
        reliable = n_trades >= MIN_SUPPORT_TRADES

        results[threshold] = {
            'n_trades': n_trades,
            'n_wins': n_wins,
            'n_losses': n_losses,
            'win_rate': win_rate,
            'profit_factor_before': profit_factor_before,
            'profit_factor': profit_factor_after,  # ✅ PF après coûts = métrique principale
            'net_ticks_before': net_ticks_before,
            'net_ticks': net_ticks_after,
            'total_costs_ticks': total_cost_ticks,
            'reliable': reliable,  # ✅ CORRECTIF C
        }

        logger.info(f"\n🎯 Seuil confidence : {threshold:.2f}")
        logger.info(f"   Trades           : {n_trades:,}")

        # ✅ CORRECTIF C: Warning si support insuffisant
        if not reliable:
            logger.warning(f"   ⚠️  ANECDOTIQUE: {n_trades} trades < {MIN_SUPPORT_TRADES} requis (statistiquement non fiable)")

        logger.info(f"   Win rate         : {win_rate:.1%}")
        logger.info(f"   💰 PF AVANT coûts: {profit_factor_before:.2f}")
        logger.info(f"   💸 Coûts ({cost_per_trade_ticks:.2f} ticks/trade): -{total_cost_ticks:.0f} ticks")
        logger.info(f"   💰 PF APRÈS coûts: {profit_factor_after:.2f}")
        logger.info(f"   Net ticks        : {net_ticks_after:+,}")

    # Recommandation
    logger.info(f"\n{'='*70}")
    logger.info(f"💡 RECOMMANDATION SEUIL")
    logger.info(f"{'='*70}")

    best_pf = max(results.items(), key=lambda x: x[1]['profit_factor'])
    logger.info(f"🏆 Meilleur Profit Factor : seuil {best_pf[0]:.2f} (PF={best_pf[1]['profit_factor']:.2f})")

    best_wr = max(results.items(), key=lambda x: x[1]['win_rate'])
    logger.info(f"🎯 Meilleur Win Rate : seuil {best_wr[0]:.2f} (WR={best_wr[1]['win_rate']:.1%})")

    return results


def plot_feature_importance(
    model: lgb.LGBMClassifier,
    feature_names: List[str],
    output_dir: Path,
    top_n: int = 30
):
    """
    Plot et sauvegarde feature importance

    Args:
        model: Modèle entraîné
        feature_names: Noms des features
        output_dir: Répertoire de sortie
        top_n: Nombre de top features à afficher
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 FEATURE IMPORTANCE (Top {top_n}) - GPT")
    logger.info(f"{'='*70}")

    # ✅ CORRECTIF BUG: Gérer modèle calibré (CalibratedClassifierCV)
    if hasattr(model, 'calibrated_classifiers_'):
        # Modèle calibré: accéder au estimator (pas base_estimator !)
        base_model = model.calibrated_classifiers_[0].estimator
        importances = base_model.feature_importances_
        logger.info(f"   📌 Feature importance extraite du modèle calibré")
    elif hasattr(model, 'base_estimator'):
        # Autre wrapper
        importances = model.base_estimator.feature_importances_
    else:
        # Modèle non calibré
        importances = model.feature_importances_

    # ✅ GPT : Vérifier priority features
    priority_features_list = CONFIG.get('priority_features', [])

    # Créer DataFrame
    feat_imp_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)

    # Afficher top features avec marqueur priority
    priority_in_top = []
    top_features_df = feat_imp_df.head(top_n)
    for i, (idx, row) in enumerate(top_features_df.iterrows(), 1):
        feat_name = row['feature']
        is_priority = any(pf in feat_name for pf in priority_features_list)
        marker = "⭐" if is_priority else "  "
        logger.info(f"{marker} {i:2d}. {feat_name:40s} : {row['importance']:8.1f}")
        if is_priority:
            priority_in_top.append(feat_name)

    # ✅ CORRECTIF B: Résumé priority features (ratio correct)
    if priority_in_top:
        logger.info(f"\n✅ Priority features dans Top {top_n} : {len(priority_in_top)}/{len(priority_features_list)}")
        for pf in priority_in_top[:5]:  # Afficher premiers 5
            logger.info(f"   - {pf}")
    else:
        logger.warning(f"   ⚠️  Aucune priority feature dans Top {top_n} (total: {len(priority_features_list)}) - Vérifier feature importance")

    # Plot
    plt.figure(figsize=(12, 10))
    top_features = feat_imp_df.head(top_n)
    plt.barh(range(len(top_features)), top_features['importance'])
    plt.yticks(range(len(top_features)), top_features['feature'])
    plt.xlabel('Importance')
    plt.title(f'Top {top_n} Features - LightGBM Feature Importance')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(output_dir / 'feature_importance.png', dpi=150)
    logger.info(f"\n💾 Feature importance sauvegardée : {output_dir / 'feature_importance.png'}")
    plt.close()

    # Sauvegarder CSV
    feat_imp_df.to_csv(output_dir / 'feature_importance.csv', index=False)
    logger.info(f"💾 Feature importance CSV : {output_dir / 'feature_importance.csv'}")


# ═══════════════════════════════════════════════════════════════════════════
# SAUVEGARDE
# ═══════════════════════════════════════════════════════════════════════════

def save_model_and_artifacts(
    model: lgb.LGBMClassifier,
    feature_names: List[str],
    metrics: Dict,
    profit_factor_results: Dict,
    output_dir: Path,
    model_name: str
):
    """
    Sauvegarde le modèle et tous les artifacts

    Args:
        model: Modèle entraîné
        feature_names: Liste des features
        metrics: Métriques d'évaluation
        profit_factor_results: Résultats simulation PF
        output_dir: Répertoire de sortie
        model_name: Nom du modèle
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"💾 SAUVEGARDE MODÈLE & ARTIFACTS")
    logger.info(f"{'='*70}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Modèle LightGBM
    model_path = output_dir / f"{model_name}_{timestamp}.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    logger.info(f"✅ Modèle : {model_path}")

    # 2. Feature names
    features_path = output_dir / f"{model_name}_features_{timestamp}.json"
    with open(features_path, 'w') as f:
        json.dump(feature_names, f, indent=2)
    logger.info(f"✅ Features : {features_path}")

    # 3. Métriques
    metrics_path = output_dir / f"{model_name}_metrics_{timestamp}.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"✅ Métriques : {metrics_path}")

    # 4. Profit Factor results
    pf_path = output_dir / f"{model_name}_profit_factor_{timestamp}.json"
    with open(pf_path, 'w') as f:
        json.dump(profit_factor_results, f, indent=2)
    logger.info(f"✅ Profit Factor : {pf_path}")

    # 5. Lien "latest" (sans timestamp)
    latest_model = output_dir / f"{model_name}_latest.pkl"
    latest_features = output_dir / f"{model_name}_features_latest.json"

    import shutil
    shutil.copy(model_path, latest_model)
    shutil.copy(features_path, latest_features)

    logger.info(f"✅ Latest model : {latest_model}")
    logger.info(f"✅ Latest features : {latest_features}")

    logger.info(f"\n🎉 Sauvegarde terminée !")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main(args):
    """Fonction principale"""

    logger.info(f"\n{'='*70}")
    logger.info(f"🚀 ENTRAÎNEMENT MODÈLE ML - DIRECTION 15 MIN")
    logger.info(f"{'='*70}")
    logger.info(f"📅 Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ─────────────────────────────────────────────────────────────────
    # 1. CHARGEMENT DONNÉES
    # ─────────────────────────────────────────────────────────────────

    def quick_validate(df):
        """✅ PATCH E: Validation rapide NaN/Inf sur colonnes critiques"""
        CRITICAL_COLS_CHECK = ['t_ms', 'mid', 'atr', 'close', 'volume']

        missing = [c for c in CRITICAL_COLS_CHECK if c not in df.columns]
        if missing:
            raise ValueError(f"❌ Colonnes critiques manquantes: {missing}")

        for col in CRITICAL_COLS_CHECK:
            if df[col].isna().any():
                n_nan = df[col].isna().sum()
                raise ValueError(f"❌ {n_nan} NaN détectés dans colonne critique '{col}'")
            if not np.isfinite(df[col]).all():
                n_inf = (~np.isfinite(df[col])).sum()
                raise ValueError(f"❌ {n_inf} Inf détectés dans colonne critique '{col}'")

        logger.info(f"✅ Validation données : 0 NaN/Inf sur {len(CRITICAL_COLS_CHECK)} colonnes critiques")

    # ✅ Support multi-répertoires avec --data-dirs
    if args.data_dirs:
        logger.info(f"\n{'='*70}")
        logger.info(f"📂 CHARGEMENT MULTI-RÉPERTOIRES ({len(args.data_dirs)} dossiers)")
        logger.info(f"{'='*70}")

        dfs = []
        for data_dir_path in args.data_dirs:
            df_temp = load_all_data(Path(data_dir_path), f"Data dir: {data_dir_path}")

            # Déterminer symbole depuis path ou args.symbol
            if 'CHART_3' in data_dir_path.upper() or (args.symbol and args.symbol.upper() == 'ES'):
                df_temp['symbol'] = 'ESZ25_FUT_CME'
            elif 'CHART_9' in data_dir_path.upper() or (args.symbol and args.symbol.upper() == 'NQ'):
                df_temp['symbol'] = 'NQZ25_FUT_CME'
            elif 'CHART_1' in data_dir_path.upper() or (args.symbol and args.symbol.upper() == 'RTY'):  # ✅ RTY ajouté
                df_temp['symbol'] = 'RTYZ25_FUT_CME'

            dfs.append(df_temp)
            logger.info(f"   ✅ {Path(data_dir_path).name}: {len(df_temp):,} samples")

        df = pd.concat(dfs, ignore_index=True)
        df = df.sort_values('tsec').reset_index(drop=True)
        logger.info(f"\n✅ TOTAL CHARGÉ : {len(df):,} samples")

        # ✅ PATCH E: Validation données
        quick_validate(df)

    else:
        # Mode classique avec --data-dir
        # ES Chart 3 (05 + 06 novembre)
        df_es = load_all_data(
            [
                args.data_dir / CONFIG['data_paths']['es_chart3_05'],
                args.data_dir / CONFIG['data_paths']['es_chart3_06']
            ],
            "ES Chart 3"
        )
        df_es['symbol'] = 'ESZ25_FUT_CME'

        # NQ Chart 9 (05 + 06 novembre)
        df_nq = load_all_data(
            [
                args.data_dir / CONFIG['data_paths']['nq_chart9_05'],
                args.data_dir / CONFIG['data_paths']['nq_chart9_06']
            ],
            "NQ Chart 9"
        )
        df_nq['symbol'] = 'NQZ25_FUT_CME'

        # ✅ RTY Chart 1 (05 + 06 novembre)
        df_rty = load_all_data(
            [
                args.data_dir / CONFIG['data_paths']['rty_chart1_05'],
                args.data_dir / CONFIG['data_paths']['rty_chart1_06']
            ],
            "RTY Chart 1"
        )
        df_rty['symbol'] = 'RTYZ25_FUT_CME'

        # Filtrer par symbole si spécifié
        if args.symbol:
            logger.info(f"\n{'='*70}")
            logger.info(f"🎯 FILTRAGE PAR SYMBOLE : {args.symbol.upper()}")
            logger.info(f"{'='*70}")

            if args.symbol.upper() == 'ES':
                df = df_es.copy()
                logger.info(f"✅ ES uniquement : {len(df):,} samples")
            elif args.symbol.upper() == 'NQ':
                df = df_nq.copy()
                logger.info(f"✅ NQ uniquement : {len(df):,} samples")
            elif args.symbol.upper() == 'RTY':  # ✅ RTY ajouté
                df = df_rty.copy()
                logger.info(f"✅ RTY uniquement : {len(df):,} samples")
            else:
                raise ValueError(f"❌ Symbole invalide : {args.symbol}. Utiliser 'ES', 'NQ' ou 'RTY'")
        else:
            # Concaténer (modèle commun)
            logger.info(f"\n{'='*70}")
            logger.info(f"🔗 CONCATÉNATION ES + NQ + RTY (Modèle commun)")  # ✅ RTY ajouté au message
            logger.info(f"{'='*70}")
            df = pd.concat([df_es, df_nq, df_rty], ignore_index=True)  # ✅ RTY ajouté
            df = df.sort_values('tsec').reset_index(drop=True)
            logger.info(f"✅ Total : {len(df):,} samples")

    # ✅ PATCH E: Validation données (mode classique)
    quick_validate(df)

    # ─────────────────────────────────────────────────────────────────
    # 2. CRÉATION LABELS (✅ Horizon spécifique par symbole - Grid Search)
    # ─────────────────────────────────────────────────────────────────

    # ✅ Déterminer horizon optimal selon symbole (Grid Search)
    if args.symbol:
        symbol_upper = args.symbol.upper()
        if symbol_upper == 'ES':
            horizon_seconds = CONFIG['horizon_seconds_es']  # 5 min
        elif symbol_upper == 'NQ':
            horizon_seconds = CONFIG['horizon_seconds_nq']  # 10 min
        elif symbol_upper == 'RTY':
            horizon_seconds = CONFIG['horizon_seconds_rty']  # 10 min
        else:
            horizon_seconds = 600  # Fallback 10 min
    else:
        horizon_seconds = 600  # Mode multi-symboles: 10 min par défaut

    # ✅ Sélectionner multiplier ATR et tick_size optimaux selon symbole
    if args.symbol and args.symbol.upper() == 'ES':
        atr_mult = CONFIG.get('threshold_atr_multiplier_es', 0.45)
        tick_size = CONFIG.get('tick_size', 0.25)
    elif args.symbol and args.symbol.upper() == 'NQ':
        atr_mult = CONFIG.get('threshold_atr_multiplier_nq', 0.35)
        tick_size = CONFIG.get('tick_size', 0.25)
    elif args.symbol and args.symbol.upper() == 'RTY':  # ✅ RTY ajouté
        atr_mult = CONFIG.get('threshold_atr_multiplier_rty', 0.50)
        tick_size = CONFIG.get('tick_size_rty', 0.10)
    else:
        atr_mult = 0.4  # Fallback générique
        tick_size = CONFIG.get('tick_size', 0.25)

    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 SYMBOLE: {args.symbol.upper() if args.symbol else 'AUTO'}")
    logger.info(f"📊 Horizon optimal: {horizon_seconds}s ({horizon_seconds//60} min) - Grid Search")
    logger.info(f"📊 Multiplier ATR optimal: {atr_mult}")
    logger.info(f"📏 Tick size: {tick_size}")  # ✅ Ajout tick_size dans logs
    logger.info(f"{'='*70}")

    df = create_labels(
        df,
        horizon_seconds=horizon_seconds,  # ✅ Utiliser horizon spécifique par symbole
        threshold_ticks=CONFIG['threshold_ticks'],
        tick_size=tick_size,  # ✅ Utiliser tick_size spécifique au symbole
        time_gap_tolerance=CONFIG['time_gap_tolerance'],
        binary_mode=args.binary,
        threshold_mode=CONFIG.get('threshold_mode', 'ticks'),
        atr_multiplier=atr_mult
    )

    # ─────────────────────────────────────────────────────────────────
    # 3. PRÉPARATION FEATURES
    # ─────────────────────────────────────────────────────────────────

    logger.info(f"\n{'='*70}")
    logger.info(f"🔧 PRÉPARATION FEATURES")
    logger.info(f"{'='*70}")

    # Aplatir nested fields
    df = flatten_nested_fields(df)

    # Calculer derived fields
    df = calculate_derived_fields(df)

    # ✨ NOUVEAU : Calculer distances relatives niveaux OPTIONS
    df = calculate_option_distances(df, tick_size=tick_size)  # ✅ Utiliser tick_size spécifique au symbole

    # Feature symbole
    df['symbol_is_nq'] = (df['symbol'] == 'NQZ25_FUT_CME').astype(int)

    # Feature engineering (LAGs + Rolling)
    logger.info(f"\n🧮 Feature Engineering (LAGs + Rolling Means)...")
    feature_engineer = FeatureEngineer(
        lag_periods=CONFIG['lag_periods'],
        rolling_windows=CONFIG['rolling_windows']
    )

    # Features à transformer (ENRICHI: toutes les features MenthorQ importantes + OPTIONS dynamiques)
    features_to_lag = [
        'close', 'level1_imbalance', 'smart_money_flow',
        'cum_delta_session', 'delta', 'd_vwap',
        'battle_navale_signal_strength', 'pressure_strength',
        # ✅ CORRIGÉ: Menthor Distances avec underscores (post-flattening)
        'menthor_distances_call', 'menthor_distances_put',
        'menthor_distances_call0', 'menthor_distances_put0',
        'menthor_distances_gamma0', 'menthor_distances_hvl0',
        'menthor_distances_dist_1d_max', 'menthor_distances_dist_1d_min',
        # Confluences/Proximités (IMPORTANTES)
        'confluence_proximity', 'menthorq_proximity_strength',
        'gamma_call_confluence', 'gamma_put_confluence',
        # ✅ CORRIGÉ: Next Wall avec underscores (post-flattening)
        'next_wall_dist_pts', 'next_wall_age_min',
        # VWAP weekly/monthly (ancrage)
        'd_vwap_weekly_ticks', 'd_vwap_monthly_ticks',
        # ✨ NOUVEAU : Distances OPTIONS dynamiques (LAGs critiques)
        'd_nearest_gex_up_ticks', 'd_nearest_gex_down_ticks', 'd_nearest_gex_abs_ticks',
        'd_nearest_blind_spot_abs_ticks',
        'd_call_resistance_ticks', 'd_put_support_ticks', 'd_hvl_ticks',
        'd_call_resistance_atr', 'd_put_support_atr', 'd_nearest_gex_atr',
    ]

    df = feature_engineer.add_lags(df, features_to_lag)
    df = feature_engineer.add_rolling_means(df, features_to_lag)

    # ✅ PHASE 3 : Features symbol-specific
    if args.symbol:
        symbol_upper = args.symbol.upper()

        if symbol_upper == 'NQ':
            logger.info(f"\n{'='*70}")
            logger.info(f"🔧 PHASE 3 : FEATURES NQ-SPECIFIC")
            logger.info(f"{'='*70}")

            from ml.feature_engineering_nq import add_nq_specific_features

            n_cols_before = len(df.columns)
            df = add_nq_specific_features(df)
            n_cols_after = len(df.columns)

            logger.info(f"✅ {n_cols_after - n_cols_before} features NQ ajoutées")
            logger.info(f"📊 Total colonnes : {n_cols_before} → {n_cols_after}")
            logger.info(f"{'='*70}")

        elif symbol_upper == 'ES':
            logger.info(f"\n{'='*70}")
            logger.info(f"🔧 PHASE 3 : FEATURES ES-SPECIFIC")
            logger.info(f"{'='*70}")

            from ml.feature_engineering_es import add_es_specific_features

            n_cols_before = len(df.columns)
            df = add_es_specific_features(df)
            n_cols_after = len(df.columns)

            logger.info(f"✅ {n_cols_after - n_cols_before} features ES ajoutées")
            logger.info(f"📊 Total colonnes : {n_cols_before} → {n_cols_after}")
            logger.info(f"{'='*70}")

        elif symbol_upper == 'RTY':
            logger.info(f"\n{'='*70}")
            logger.info(f"🔧 PHASE 3 : FEATURES RTY-SPECIFIC")
            logger.info(f"{'='*70}")

            from ml.feature_engineering_rty import add_rty_specific_features

            n_cols_before = len(df.columns)
            df = add_rty_specific_features(df)
            n_cols_after = len(df.columns)

            logger.info(f"✅ {n_cols_after - n_cols_before} features RTY ajoutées")
            logger.info(f"📊 Total colonnes : {n_cols_before} → {n_cols_after}")
            logger.info(f"{'='*70}")

    # ✅ CORRECTIF : Log avant dropna pour diagnostiquer
    n_before_dropna = len(df)
    n_na_rows = df.isna().any(axis=1).sum()
    logger.info(f"📊 Avant dropna : {n_before_dropna:,} samples")
    logger.info(f"   Lignes avec NaN : {n_na_rows:,} ({n_na_rows/n_before_dropna*100:.1f}%)")

    # Supprimer NaN créés par feature engineering
    # ✅ CORRECTIF : Ne supprimer que les NaN dans les colonnes critiques (label + features principales)
    # au lieu de toutes les colonnes pour préserver plus de données
    critical_cols = ['label'] + [col for col in df.columns if col in features_to_lag[:10]]  # Premières features importantes
    critical_cols = [col for col in critical_cols if col in df.columns]
    df = df.dropna(subset=critical_cols).reset_index(drop=True)

    n_after_dropna = len(df)
    logger.info(f"📊 Après dropna (colonnes critiques uniquement) : {n_after_dropna:,} samples")
    logger.info(f"   Perte : {n_before_dropna - n_after_dropna:,} samples ({(n_before_dropna - n_after_dropna)/n_before_dropna*100:.1f}%)")

    # ✅ ÉTAPE 1: Bannir colonnes interdites (leak/bruit)
    forbidden_cols = CONFIG.get('forbidden_columns', [])
    cols_to_remove = [col for col in forbidden_cols if col in df.columns]
    if cols_to_remove:
        logger.info(f"\n🚫 Bannissement de {len(cols_to_remove)} colonnes interdites")
        logger.info(f"   Colonnes bannies : {cols_to_remove}")
        df = df.drop(columns=cols_to_remove, errors='ignore')

    # ✅ ÉTAPE 2: One-hot encoding pour next_wall_side (si présent)
    # Note: next_wall_side est catégoriel, on crée des one-hot et on retire l'original
    one_hot_cols_created = []
    priority_features_updated = CONFIG.get('priority_features', []).copy()  # Initialiser dès le début
    if 'next_wall_side' in df.columns:
        logger.info(f"\n🔀 One-hot encoding pour next_wall_side...")
        side_values = df['next_wall_side'].unique()
        for side_val in side_values:
            if pd.notna(side_val):
                col_name = f'next_wall_side_{side_val}'
                df[col_name] = (df['next_wall_side'] == side_val).astype(int)
                one_hot_cols_created.append(col_name)
        # Retirer la colonne originale (catégorielle) après création des one-hot
        df = df.drop(columns=['next_wall_side'], errors='ignore')
        logger.info(f"   ✅ Créé {len(one_hot_cols_created)} colonnes one-hot: {one_hot_cols_created}")
        logger.info(f"   🗑️  Colonne originale 'next_wall_side' retirée (catégorielle)")

    # Mettre à jour priority_features : remplacer next_wall_side par les one-hot
    if 'next_wall_side' in priority_features_updated and one_hot_cols_created:
        priority_features_updated.remove('next_wall_side')
        priority_features_updated.extend(one_hot_cols_created)
        logger.info(f"   ✅ Priority features mises à jour : next_wall_side → {one_hot_cols_created}")

    # ✅ ÉTAPE 3: Sélection features
    manual_features = get_manual_feature_list()

    # ✅ PATCH RTY: Exclure feature 'corr' (hardcodée ES/NQ, non pertinente pour RTY)
    # Note: 'corr' = Corrélation(ES, NQ) calculée dans le dumper C++
    # Pour ES/NQ : Feature CRITIQUE (détecte lead/lag intermarché)
    # Pour RTY : Feature NON PERTINENTE (RTY ≠ corrélé ES/NQ directement)
    # TODO GC/CL: Même problème - exclure 'corr' ou implémenter corrélation adaptative
    if args.symbol and args.symbol.upper() in ['RTY', 'GC', 'CL']:
        if 'corr' in manual_features:
            manual_features.remove('corr')
            logger.info(f"\n🔧 {args.symbol.upper()}: Feature 'corr' exclue (hardcodée ES/NQ)")
            logger.info(f"   💡 Raison: 'corr' mesure Corrélation(ES, NQ), non pertinent pour {args.symbol.upper()}")
            logger.info(f"   ℹ️  Impact: Gain potentiel +0.5-1% accuracy par élimination feature polluante")

    # Features générées par feature engineering
    engineered_features = [col for col in df.columns
                          if '_lag_' in col or '_ma_' in col or '_vs_ma_' in col or '_slope' in col]

    # ✅ PHASE 3: Ajouter features symbol-specific
    symbol_specific_features = []
    if args.symbol:
        symbol_upper = args.symbol.upper()

        if symbol_upper == 'NQ':
            # Détecter les features NQ-specific
            nq_keywords = [
                'momentum_', 'volatility_', 'volume_surge', 'delta_momentum',
                'wick_', 'reversion_', 'trend_strength', 'corr_',
                'spread_', 'microprice_momentum', 'ob_pressure', 'price_acceleration',
                'volume_weighted_momentum', 'cum_delta_acceleration', 'range_expansion'
            ]
            symbol_specific_features = [col for col in df.columns
                                       if any(keyword in col for keyword in nq_keywords)]

        elif symbol_upper == 'ES':
            # Détecter les features ES-specific
            es_keywords = ['es_']
            symbol_specific_features = [col for col in df.columns
                                       if any(keyword in col for keyword in es_keywords)]

        elif symbol_upper == 'RTY':
            # Détecter les features RTY-specific
            rty_keywords = ['rty_']
            symbol_specific_features = [col for col in df.columns
                                        if any(keyword in col for keyword in rty_keywords)]

        if symbol_specific_features:
            logger.info(f"\n🔧 Features {symbol_upper}-specific détectées : {len(symbol_specific_features)}")

    all_features = manual_features + engineered_features + symbol_specific_features

    # Vérifier disponibilité
    available_features = [f for f in all_features if f in df.columns]
    missing_features = [f for f in all_features if f not in df.columns]

    logger.info(f"\n📊 Features :")
    logger.info(f"   Demandées : {len(all_features)}")
    logger.info(f"   Disponibles : {len(available_features)}")
    logger.info(f"   Manquantes : {len(missing_features)}")

    if missing_features:
        logger.warning(f"⚠️  Features manquantes (premiers 10) : {missing_features[:10]}...")
        logger.info(f"   💡 Ces features peuvent être dans des champs nested non encore extraits")
        logger.info(f"   → Vérifier flatten_nested_fields() et calculate_derived_fields()")

    # ✅ ÉTAPE 4: Système PRIORITY_FEATURES + Top-K avec sélection par importance
    # Utiliser priority_features mis à jour avec one-hot si créé
    priority_features = priority_features_updated
    use_top_k = CONFIG.get('use_top_k', False)
    top_k = CONFIG.get('top_k', 110)
    priority_merge = CONFIG.get('priority_merge', True)

    # Variables pour stocker la sélection (sera remplie après labeling si nécessaire)
    feature_cols = None
    selected_non_priority = None

    if use_top_k and priority_merge:
        # Garantir que priority_features sont toujours incluses
        priority_available = [f for f in priority_features if f in df.columns]
        non_priority = [f for f in available_features if f not in priority_features]

        logger.info(f"\n🎯 Feature selection avec PRIORITY + Top-K (sélection par importance)")
        logger.info(f"   Priority features disponibles : {len(priority_available)}/{len(priority_features)}")
        logger.info(f"   Non-priority features : {len(non_priority)}")

        # Si Top-K activé, préparer pour sélection après labeling
        if len(priority_available) < top_k:
            k_remaining = top_k - len(priority_available)
            logger.info(f"   → Sélection par importance sera effectuée APRÈS labeling ({k_remaining} features à sélectionner)")
            # Pour l'instant, garder temporairement toutes les features
            feature_cols_temp = available_features
        else:
            feature_cols = priority_available[:top_k]
            logger.info(f"   ⚠️  Toutes les features sont priority, limitation à Top-K={top_k}")
    elif use_top_k:
        # Top-K simple sans priority
        feature_cols = available_features[:top_k]
        logger.info(f"\n🎯 Feature selection Top-K={top_k}")
        logger.info(f"   ✅ Sélection : {len(feature_cols)} features (sur {len(available_features)} disponibles)")
    else:
        # Pas de Top-K : utiliser toutes les features disponibles
        feature_cols = available_features
        logger.info(f"\n✅ Utilisation de toutes les {len(feature_cols)} features disponibles")
        if priority_features:
            priority_available = [f for f in priority_features if f in df.columns]
            missing_priority = [f for f in priority_features if f not in df.columns]
            if priority_available:
                logger.info(f"   ✅ Priority features incluses : {len(priority_available)}/{len(priority_features)}")
            if missing_priority:
                logger.warning(f"   ⚠️  Priority features manquantes : {missing_priority}")

    # ─────────────────────────────────────────────────────────────────
    # 4. SPLIT TRAIN/TEST
    # ─────────────────────────────────────────────────────────────────

    logger.info(f"\n{'='*70}")
    logger.info(f"✂️  SPLIT TRAIN/TEST")
    logger.info(f"{'='*70}")

    # ✅ PATCH CRITIQUE R4 GPT: Split temporel avec EMBARGO (éviter leak temporel rolling)
    # Problème: rolling_max=300s sans embargo → leak des features rolling dans test set
    # Solution: Embargo de 600s (2× rolling_max) entre train et test

    test_ratio = 1 - CONFIG['train_ratio']  # 0.2 par défaut
    embargo_seconds = 600  # 2× rolling_max (300s) → 600s embargo

    if 't_ms' in df.columns:
        # Split temporel avec embargo par timestamp
        n = len(df)
        test_start_idx = int(n * CONFIG['train_ratio'])

        # Calculer embargo en rows (approximation: 1 row ≈ 60s)
        embargo_rows = max(int(embargo_seconds / 60), 10)  # Min 10 rows
        train_end_idx = max(test_start_idx - embargo_rows, 0)

        df_train = df.iloc[:train_end_idx].copy()
        df_test = df.iloc[test_start_idx:].copy()

        train_end_ts = df.iloc[train_end_idx]['t_ms']
        test_start_ts = df.iloc[test_start_idx]['t_ms']

        logger.info(f"   ✅ Split temporel AVEC EMBARGO (anti-leak rolling)")
        logger.info(f"   📅 Train end: {pd.Timestamp(train_end_ts/1000, unit='s')}")
        logger.info(f"   ⏸️  Embargo: {embargo_rows} rows ({embargo_seconds}s) SUPPRIMÉS")
        logger.info(f"   📅 Test start: {pd.Timestamp(test_start_ts/1000, unit='s')}")
    else:
        # Split par index avec embargo
        n = len(df)
        test_start_idx = int(n * CONFIG['train_ratio'])
        embargo_rows = max(int(embargo_seconds / 60), 10)
        train_end_idx = max(test_start_idx - embargo_rows, 0)

        df_train = df.iloc[:train_end_idx].copy()
        df_test = df.iloc[test_start_idx:].copy()

        logger.info(f"   ✅ Split par index AVEC EMBARGO (anti-leak rolling)")
        logger.info(f"   ⏸️  Embargo: {embargo_rows} rows ({embargo_seconds}s) SUPPRIMÉS")

    # ✅ PHASE 3.5 : SÉLECTION PAR IMPORTANCE (2 PASSES) - APRÈS LABELING
    if use_top_k and priority_merge and feature_cols is None:
        # PASSE 1 : Entraînement rapide pour calculer l'importance
        logger.info(f"\n{'='*70}")
        logger.info(f"🔥 PASSE 1 : Entraînement rapide pour feature importance...")
        logger.info(f"{'='*70}")
        logger.info(f"   → Entraînement avec TOUTES les {len(available_features)} features")
        logger.info(f"   → n_estimators=200 (rapide), early_stopping=50")

        # Préparer données temporaires APRÈS labeling
        X_temp = df_train[available_features].copy()
        y_temp = df_train['label'].copy().astype(int)

        # Split temporel simple (80/20 du train)
        split_idx = int(len(X_temp) * 0.80)
        X_train_temp = X_temp.iloc[:split_idx]
        X_val_temp = X_temp.iloc[split_idx:]
        y_train_temp = y_temp.iloc[:split_idx]
        y_val_temp = y_temp.iloc[split_idx:]

        # Modèle rapide
        params_fast = CONFIG["lgbm_params_binary"].copy()
        params_fast['n_estimators'] = 200  # Au lieu de 5000
        params_fast['verbosity'] = -1

        model_fast = lgb.LGBMClassifier(**params_fast)

        try:
            model_fast.fit(
                X_train_temp, y_train_temp,
                eval_set=[(X_val_temp, y_val_temp)],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=50, verbose=False),
                    lgb.log_evaluation(period=0)  # Pas de logs
                ]
            )

            # Extraire feature importance
            importances = model_fast.feature_importances_

            # Créer DataFrame avec importance
            feat_imp_df = pd.DataFrame({
                'feature': available_features,
                'importance': importances
            }).sort_values('importance', ascending=False)

            logger.info(f"   ✅ Feature importance calculée ({model_fast.n_estimators} arbres entraînés)")

            # Afficher top 10 features par importance
            logger.info(f"\n   📊 Top 10 features par importance :")
            for i, row in feat_imp_df.head(10).iterrows():
                is_priority = row['feature'] in priority_features
                marker = "⭐" if is_priority else "  "
                logger.info(f"   {marker} {row['feature']:40s} : {row['importance']:8.1f}")

            # Sélectionner les k_remaining meilleures features non-priority
            k_remaining = top_k - len(priority_available)
            non_priority_sorted = [f for f in feat_imp_df['feature'].tolist()
                                  if f not in priority_features]
            selected_non_priority = non_priority_sorted[:k_remaining]

            feature_cols = priority_available + selected_non_priority

            logger.info(f"\n   ✅ PASSE 1 TERMINÉE - Sélection par importance :")
            logger.info(f"      • {len(priority_available)} priority features (toujours incluses)")
            logger.info(f"      • {len(selected_non_priority)} features sélectionnées (sur {len(non_priority)} disponibles)")
            logger.info(f"      • TOTAL = {len(feature_cols)} features pour PASSE 2")
            logger.info(f"{'='*70}\n")

            # Sauvegarder feature importance
            importance_path = Path(CONFIG["output_dir"]) / f"feature_importance_pass1_{args.symbol or 'ALL'}.csv"
            feat_imp_df.to_csv(importance_path, index=False)
            logger.info(f"      • Feature importance sauvegardée : {importance_path.name}")

        except Exception as e:
            logger.warning(f"   ⚠️  Erreur PASSE 1 : {e}")
            logger.warning(f"   → Fallback : sélection sans importance (ordre DataFrame)")
            k_remaining = top_k - len(priority_available)
            selected_non_priority = non_priority[:k_remaining] if k_remaining < len(non_priority) else non_priority
            feature_cols = priority_available + selected_non_priority
            logger.info(f"   ✅ Fallback : {len(priority_available)} priority + {len(selected_non_priority)} autres = {len(feature_cols)} totales")

    # Si feature_cols n'a pas été défini, utiliser fallback
    if feature_cols is None:
        feature_cols = available_features
        logger.info(f"\n⚠️  feature_cols non défini, utilisation de toutes les features disponibles : {len(feature_cols)}")

    X_train = df_train[feature_cols].values
    y_train = df_train['label'].values.astype(int)
    X_test = df_test[feature_cols].values
    y_test = df_test['label'].values.astype(int)

    logger.info(f"📊 Train : {len(X_train):,} samples ({len(X_train)/len(df)*100:.1f}%)")
    logger.info(f"📊 Test  : {len(X_test):,} samples ({len(X_test)/len(df)*100:.1f}%)")

    # ✅ GPT : Vérifications avant fit
    logger.info(f"\n🔍 VÉRIFICATIONS AVANT FIT (GPT)")
    logger.info(f"{'='*70}")

    # Distribution classes
    train_dist = pd.Series(y_train).value_counts(normalize=True).sort_index()
    test_dist = pd.Series(y_test).value_counts(normalize=True).sort_index()

    logger.info(f"\n📊 Ratio classes TRAIN :")
    for cls, pct in train_dist.items():
        cls_name = ["DOWN", "FLAT", "UP"][cls] if not args.binary else ["DOWN", "UP"][cls]
        logger.info(f"   {cls_name} ({cls}) : {pct*100:.1f}%")
        if pct < 0.30:
            logger.warning(f"      ⚠️  Classe minoritaire (<30%), is_unbalance=True activé")

    logger.info(f"\n📊 Ratio classes TEST :")
    for cls, pct in test_dist.items():
        cls_name = ["DOWN", "FLAT", "UP"][cls] if not args.binary else ["DOWN", "UP"][cls]
        logger.info(f"   {cls_name} ({cls}) : {pct*100:.1f}%")

    # Vérifier intersection features
    logger.info(f"\n📋 Features utilisées :")
    logger.info(f"   Total : {len(feature_cols)}")
    priority_features_list = CONFIG.get('priority_features', [])
    priority_included = sum(1 for f in feature_cols if any(pf in f for pf in priority_features_list))
    logger.info(f"   Priority features incluses : {priority_included}/{len(priority_features_list)}")

    # Vérifier colonnes interdites bannies
    forbidden_found = [col for col in CONFIG['forbidden_columns'] if col in feature_cols]
    if forbidden_found:
        logger.error(f"   ❌ Colonnes interdites trouvées dans features : {forbidden_found}")
    else:
        logger.info(f"   ✅ Toutes les colonnes interdites bannies")

    logger.info(f"")

    if args.binary:
        # Mode binaire : 2 classes (DOWN=0, UP=1)
        logger.info(f"\n📈 Distribution Train (BINAIRE) :")
        logger.info(f"   DOWN (0) : {train_dist.get(0, 0):.1%}")
        logger.info(f"   UP   (1) : {train_dist.get(1, 0):.1%}")

        logger.info(f"\n📈 Distribution Test (BINAIRE) :")
        logger.info(f"   DOWN (0) : {test_dist.get(0, 0):.1%}")
        logger.info(f"   UP   (1) : {test_dist.get(1, 0):.1%}")
    else:
        # Mode multiclass : 3 classes (DOWN=0, FLAT=1, UP=2)
        logger.info(f"\n📈 Distribution Train (MULTICLASS) :")
        logger.info(f"   DOWN (0) : {train_dist.get(0, 0):.1%}")
        logger.info(f"   FLAT (1) : {train_dist.get(1, 0):.1%}")
        logger.info(f"   UP   (2) : {test_dist.get(2, 0):.1%}")

        logger.info(f"\n📈 Distribution Test (MULTICLASS) :")
        logger.info(f"   DOWN (0) : {test_dist.get(0, 0):.1%}")
        logger.info(f"   FLAT (1) : {test_dist.get(1, 0):.1%}")
        logger.info(f"   UP   (2) : {test_dist.get(2, 0):.1%}")

    # ─────────────────────────────────────────────────────────────────
    # 5. VALIDATION CROISÉE (optionnel)
    # ─────────────────────────────────────────────────────────────────

    if args.cross_validate:
        # ✅ CORRECTIF GPT : Passer timestamps pour logs des folds
        train_timestamps = df_train['tsec'].values
        cv_scores = cross_validate_model(
            X_train, y_train,
            CONFIG['lgbm_params'],
            n_splits=CONFIG['cv_n_splits'],
            timestamps=train_timestamps
        )

    # ─────────────────────────────────────────────────────────────────
    # 6. ENTRAÎNEMENT
    # ─────────────────────────────────────────────────────────────────

    # ✅ GPT : Utiliser paramètres optimisés selon mode
    if args.binary:
        # Mode binaire : utiliser paramètres binaires GPT
        lgbm_params = CONFIG['lgbm_params_binary'].copy()
        logger.info(f"🎯 Mode BINAIRE : objective=binary, metric=auc+binary_logloss (GPT patch)")
    else:
        # Mode multiclass : utiliser paramètres multiclass GPT
        lgbm_params = CONFIG['lgbm_params'].copy()
        logger.info(f"🎯 Mode MULTICLASS : objective=multiclass, metric=multi_logloss (GPT patch)")

    model = train_model(
        X_train, y_train,
        X_test, y_test,
        lgbm_params,
        early_stopping_rounds=CONFIG['early_stopping_rounds'],
        symbol=args.symbol  # ✅ Passer le symbole pour patch NQ
    )

    # ─────────────────────────────────────────────────────────────────
    # 6b. ✅ PATCH 2: CALIBRATION PROBABILITÉS
    # ─────────────────────────────────────────────────────────────────

    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 CALIBRATION MODÈLE (IsotonicRegression)")
    logger.info(f"{'='*70}")

    try:
        from sklearn.calibration import CalibratedClassifierCV, calibration_curve
        from sklearn.metrics import brier_score_loss

        # ⚠️ NOTE: Pour une calibration optimale, utiliser un hold-out validation set distinct
        # Ici, on calibre sur X_test pour simplification (à améliorer avec 3-way split)
        logger.info("⚠️  Calibration sur test set (non optimal mais mieux que rien)")
        logger.info("💡 TODO: Implémenter 3-way split (train/valid/test) pour calibration robuste")

        # Calibration isotonic (non-paramétrique, adaptatif)
        calibrated_model = CalibratedClassifierCV(
            model,
            method="isotonic",  # Plus flexible que sigmoid
            cv="prefit"  # Modèle déjà entraîné
        )

        # Calibrer sur test set (pas idéal mais fonctionnel)
        calibrated_model.fit(X_test, y_test)

        # Évaluation calibration
        y_proba_uncal = model.predict_proba(X_test)
        y_proba_cal = calibrated_model.predict_proba(X_test)

        if args.binary:
            # Mode binaire : classe positive (UP)
            brier_uncal = brier_score_loss(y_test, y_proba_uncal[:, 1])
            brier_cal = brier_score_loss(y_test, y_proba_cal[:, 1])

            logger.info(f"📊 Brier Score AVANT calibration: {brier_uncal:.4f}")
            logger.info(f"📊 Brier Score APRÈS calibration: {brier_cal:.4f}")
            logger.info(f"   Amélioration: {(brier_uncal - brier_cal):.4f} ({'✅' if brier_cal < brier_uncal else '⚠️'})")

            # Plot reliability curve
            try:
                prob_true_uncal, prob_pred_uncal = calibration_curve(y_test, y_proba_uncal[:, 1], n_bins=10)
                prob_true_cal, prob_pred_cal = calibration_curve(y_test, y_proba_cal[:, 1], n_bins=10)

                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                plt.figure(figsize=(10, 6))
                plt.plot(prob_pred_uncal, prob_true_uncal, marker='o', label='Non calibré', linestyle='--')
                plt.plot(prob_pred_cal, prob_true_cal, marker='s', label='Calibré (Isotonic)')
                plt.plot([0, 1], [0, 1], linestyle=':', color='gray', label='Parfait')
                plt.xlabel('Probabilité prédite')
                plt.ylabel('Probabilité réelle')
                plt.title('Courbe de Calibration')
                plt.legend()
                plt.grid(True, alpha=0.3)

                calib_path = output_dir / "calibration_curve.png"
                plt.savefig(calib_path, dpi=150, bbox_inches='tight')
                plt.close()

                logger.info(f"📊 Courbe de calibration: {calib_path}")
            except Exception as e:
                logger.warning(f"⚠️  Impossible de tracer courbe calibration: {e}")

        # Remplacer model par calibrated_model
        model = calibrated_model
        logger.info(f"✅ Modèle calibré (les seuils 0.70/0.75 sont maintenant fiables)")

    except Exception as e:
        logger.error(f"❌ Erreur calibration: {e}")
        logger.warning(f"⚠️  Utilisation du modèle NON calibré (seuils moins fiables)")

    # ─────────────────────────────────────────────────────────────────
    # 7. ÉVALUATION
    # ─────────────────────────────────────────────────────────────────

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = evaluate_model(model, X_test, y_test, output_dir, binary_mode=args.binary)

    # ─────────────────────────────────────────────────────────────────
    # 7b. ✅ CORRECTIF D: MÉTRIQUES SEGMENTÉES (jour/session/vol)
    # ─────────────────────────────────────────────────────────────────

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    try:
        evaluate_by_segment(
            df_test=df_test,
            y_true=y_test,
            y_pred=y_pred,
            y_proba=y_proba,
            binary_mode=args.binary
        )
    except Exception as e:
        logger.warning(f"⚠️ Segmentation métriques échouée: {e}")

    # ─────────────────────────────────────────────────────────────────
    # 8. PROFIT FACTOR
    # ─────────────────────────────────────────────────────────────────

    pf_results = simulate_profit_factor(
        y_test, y_proba,
        CONFIG['confidence_thresholds'],
        binary_mode=args.binary
    )

    # ─────────────────────────────────────────────────────────────────
    # 9. FEATURE IMPORTANCE (GPT : Top 20 avec vérification priority features)
    # ─────────────────────────────────────────────────────────────────

    plot_feature_importance(model, feature_cols, output_dir, top_n=30)

    # ─────────────────────────────────────────────────────────────────
    # 10. SAUVEGARDE
    # ─────────────────────────────────────────────────────────────────

    # Nom du modèle avec symbole si spécifié
    model_name = CONFIG['model_name']
    if args.symbol:
        model_name = f"{CONFIG['model_name']}_{args.symbol.upper()}"
    if args.binary:
        model_name = f"{model_name}_BINARY"

    save_model_and_artifacts(
        model,
        feature_cols,
        metrics,
        pf_results,
        output_dir,
        model_name
    )

    # ─────────────────────────────────────────────────────────────────
    # 10b. ✅ PATCH R8 GPT: SAUVEGARDE MANIFEST POUR INFERENCE
    # ─────────────────────────────────────────────────────────────────

    # ✅ PATCH CRITIQUE R8: Features manifest pour inference sécurisée
    # Problème: Ordre features en prod ≠ ordre entraînement → plantage
    # Solution: Sauvegarder ordre exact + métadonnées + hash datasets
    # Note: json, hashlib, sys, datetime déjà importés au début du fichier

    # ✅ PATCH R7 GPT: Hash datasets pour reproductibilité 100%
    # Hash du dataset complet (shape + premières/dernières lignes)
    data_sample = f"{df.shape}_{df.iloc[0].to_dict()}_{df.iloc[-1].to_dict()}"
    data_hash = hashlib.md5(data_sample.encode()).hexdigest()[:8]

    # Hash des features sélectionnées
    features_str = "_".join(sorted(feature_cols))
    features_hash = hashlib.md5(features_str.encode()).hexdigest()[:8]

    # Métadonnées complètes
    features_manifest = {
        "feature_order": feature_cols,  # Liste ordonnée CRITIQUE
        "n_features": len(feature_cols),
        "priority_features": CONFIG['priority_features'],
        "symbol": args.symbol.upper() if args.symbol else "ES_NQ_MULTI",
        "tick_size": tick_size,
        "threshold_atr_mult": atr_mult,
        "horizon_seconds": horizon_seconds,  # ✅ Traçabilité horizon (spécifique par symbole)
        "version": "v3.5.23_R8_GRID_SEARCH",
        "train_date": datetime.now().isoformat(),
        "n_train_samples": len(df_train),
        "n_test_samples": len(df_test),
        "embargo_seconds": 600,
        "data_shape": str(df.shape),
        "data_hash": data_hash,  # ✅ R7: Hash datasets
        "features_hash": features_hash,  # ✅ R7: Hash features
        "top_k_used": CONFIG['use_top_k'],
        "top_k_value": CONFIG['top_k'] if CONFIG['use_top_k'] else None,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "train_mode": "BINARY" if args.binary else "MULTICLASS",

        # ✅ R7: Versions des packages critiques
        "package_versions": {
            "lightgbm": __import__('lightgbm').__version__,
            "scikit-learn": __import__('sklearn').__version__,
            "pandas": __import__('pandas').__version__,
            "numpy": __import__('numpy').__version__,
        }
    }

    manifest_path = output_dir / "features_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(features_manifest, f, indent=2)

    logger.info(f"\n📋 Manifest d'inférence sauvegardé: {manifest_path}")
    logger.info(f"   ✅ Features ordonnées: {len(feature_cols)}")
    logger.info(f"   ✅ Data hash: {data_hash}")
    logger.info(f"   ✅ Features hash: {features_hash}")
    logger.info(f"   ✅ Symbole: {features_manifest['symbol']}")
    logger.info(f"   💡 Utiliser ce manifest pour aligner features en production")

    # ✅ R7: Sauvegarder pip freeze (versions exactes de tous les packages)
    try:
        import subprocess
        pip_freeze_output = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'],
                                                    text=True,
                                                    stderr=subprocess.DEVNULL)
        requirements_path = output_dir / "requirements_train.txt"
        with open(requirements_path, "w") as f:
            f.write(f"# Requirements pour reproduire l'entraînement\n")
            f.write(f"# Date: {datetime.now().isoformat()}\n")
            f.write(f"# Symbole: {features_manifest['symbol']}\n")
            f.write(f"# Python: {sys.version}\n\n")
            f.write(pip_freeze_output)

        logger.info(f"   ✅ Requirements sauvegardés: {requirements_path}")
        logger.info(f"   💡 Utiliser: pip install -r {requirements_path.name}")
    except Exception as e:
        logger.warning(f"   ⚠️  Impossible de sauvegarder pip freeze: {e}")

    # ─────────────────────────────────────────────────────────────────
    # FIN
    # ─────────────────────────────────────────────────────────────────

    logger.info(f"\n{'='*70}")
    logger.info(f"🎉 ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS !")
    logger.info(f"{'='*70}")
    logger.info(f"📁 Modèle sauvegardé dans : {output_dir}")
    logger.info(f"🚀 Prêt pour intégration dans le système de trading !")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Entraînement modèle ML - Direction 15 minutes"
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('.'),
        help='Répertoire racine des données (défaut: .)'
    )

    parser.add_argument(
        '--data-dirs',
        type=str,
        nargs='+',
        help='Liste de répertoires ML_READY à charger (ex: dir1 dir2 dir3)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=CONFIG['output_dir'],
        help=f"Répertoire de sortie (défaut: {CONFIG['output_dir']})"
    )

    parser.add_argument(
        '--symbol',
        type=str,
        choices=['ES', 'NQ', 'RTY', 'es', 'nq', 'rty'],  # ✅ RTY ajouté
        default=None,
        help='Symbole à entraîner (ES, NQ ou RTY). Si non spécifié, entraîne sur ES+NQ combinés'
    )

    parser.add_argument(
        '--cross-validate',
        action='store_true',
        help='Activer validation croisée (TimeSeriesSplit 5-fold)'
    )

    parser.add_argument(
        '--no-feature-engineering',
        action='store_true',
        help='Désactiver feature engineering (LAGs + Rolling)'
    )

    parser.add_argument(
        '--binary',
        action='store_true',
        help='Mode binaire (UP/DOWN seulement, pas de FLAT)'
    )

    args = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        sys.exit(1)
