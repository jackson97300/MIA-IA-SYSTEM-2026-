#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
ENTRAÎNEMENT ML 3-LAYER - MENTHORQ FIRST + ORDERFLOW + CONTEXT
═══════════════════════════════════════════════════════════════════════════════

🚀 VERSION ULTIMATE: Système 3-Layer avec MenthorQ comme COEUR (50%)

Architecture:
    LAYER 1 (50%): MenthorQ (Options Data) - SIGNAL PRIMAIRE
    LAYER 2 (30%): OrderFlow - VALIDATEUR
    LAYER 3 (20%): VWAP/Context - FILTRE CONTEXTUEL

Features: 142 total
    - 62 MenthorQ (gamma walls, GEX, blind spots, distances)
    - 35 OrderFlow (delta, volume, DOM, pressure, battle navale)
    - 45 Context (VWAP, value area, structure, volatility)

Modèles générés:
    - lgbm_3layer_ES_BINARY_latest.pkl
    - lgbm_3layer_NQ_BINARY_latest.pkl
    - lgbm_3layer_RTY_BINARY_latest.pkl

Auteur: MIA_IA_SYSTEM + Claude Sonnet 4.5
Date: 9 Novembre 2025
Version: 3.0
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
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
    roc_auc_score
)
from sklearn.model_selection import TimeSeriesSplit

# Ajouter path parent pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_engineering import FeatureEngineer


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# 🔥 TICK SIZE PAR SYMBOLE
TICK_SIZE = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}

# 🔥 CONFIGURATION 3-LAYER
CONFIG_3LAYER = {
    "description": "Configuration 3-Layer: MenthorQ First (50%) + OrderFlow (30%) + Context (20%)",

    # === FEATURES PAR LAYER ===
    "features": {
        # LAYER 1: MenthorQ (62 features)
        "menthorq": [
            # Gamma Walls (8)
            'call_resistance', 'put_support', 'gamma_side', 'gamma_wall_level',
            'gamma_flip_up', 'gamma_flip_down', 'gamma_call_confluence', 'gamma_put_confluence',

            # GEX Levels (10)
            'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
            'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',

            # Blind Spots (9)
            'blind_spot_0', 'blind_spot_1', 'blind_spot_2', 'blind_spot_3', 'blind_spot_4',
            'blind_spot_5', 'blind_spot_6', 'blind_spot_7', 'blind_spot_8',

            # Next Wall (6)
            'next_wall_price', 'next_wall_side', 'next_wall_dist_pts', 'next_wall_dist_ticks',
            'next_wall_strength', 'next_wall_age_min',

            # HVL & Range (3)
            'hvl', '1d_max', '1d_min',

            # MenthorQ Distances (12)
            'menthor_distances_gamma0', 'menthor_distances_call0', 'menthor_distances_put0',
            'menthor_distances_hvl0', 'menthor_distances_call', 'menthor_distances_put',
            'menthor_distances_hvl', 'menthor_distances_dist_1d_max', 'menthor_distances_dist_1d_min',
            'menthor_distances_near_gex_up', 'menthor_distances_near_gex_dn', 'menthor_distances_near_blind',

            # MenthorQ Scores (3)
            'menthorq_impact_score', 'menthorq_proximity_strength', 'blind_spot_confluence',

            # Dérivées MenthorQ (8) - seront créées
            'd_nearest_gex_up_ticks', 'd_nearest_gex_down_ticks', 'd_nearest_gex_abs_ticks',
            'd_nearest_gex_atr', 'd_call_resistance_ticks', 'd_put_support_ticks',
            'd_hvl_ticks', 'd_nearest_blind_spot_abs_ticks',

            # Confluence Flags (3)
            'confluence_density', 'confluence_strength', 'confluence_proximity'
        ],

        # LAYER 2: OrderFlow (35 features)
        "orderflow": [
            # Delta (10)
            'cum_delta_day', 'cum_delta_session', 'delta', 'deltaPct', 'delta_burst',
            'delta_flip', 'delta_cum_10s', 'delta_rate_1s', 'smart_money_flow',

            # Volume Profile (8)
            'volume', 'bidvol', 'askvol', 'askPct', 'bidPct', 'buy_pct', 'sell_pct',

            # DOM Imbalance (8)
            'level1_imbalance', 'depth_imbalance', 'ob_center', 'ob_center_b',
            'ob_center_tanh', 'top_heavy',

            # Pressure (5)
            'pressure', 'institutional_pressure', 'pressure_strength',
            'pressure_strength_depth', 'pressure_strength_atr',

            # Battle Navale (4)
            'battle_navale_signal_strength', 'battle_navale_confidence',
            'tick_momentum', 'tick_rate_3s'
        ],

        # LAYER 3: Context (45 features)
        "context": [
            # VWAP Distances (6)
            'd_vwap', 'd_vwap_ticks', 'd_vwap_atr',
            'd_vwap_weekly', 'd_vwap_weekly_ticks', 'd_vwap_monthly',

            # VWAP Bands (12)
            'vwap', 'vwap_up1', 'vwap_up2', 'vwap_up3',
            'vwap_dn1', 'vwap_dn2', 'vwap_dn3',
            'vwap_weekly_up1', 'vwap_weekly_dn1',
            'd_w_up1', 'd_w_dn1', 'd_pvwap',

            # Value Area (9)
            'd_vah', 'd_vah_ticks', 'd_val', 'd_val_ticks',
            'd_vpoc', 'd_vpoc_ticks', 'd_vpoc_atr',
            'in_value_area', 'position_in_range',

            # Market Structure (12)
            'structure_onh', 'structure_onl', 'structure_ibh', 'structure_ibl',
            'structure_awap_onh', 'structure_awap_onl', 'structure_awap_ibo',
            'day_range_pct', 'distance_to_high_pct', 'distance_to_low_pct',

            # Volatility (6)
            'atr', 'atr_ratio', 'volatility_regime', 'volatility_regime5',
            'volatility_regime_cont', 'vix'
        ]
    },

    # === POIDS PAR LAYER ===
    "layer_weights": {
        "menthorq": 0.50,    # 50%
        "orderflow": 0.30,   # 30%
        "context": 0.20      # 20%
    },

    # === HYPERPARAMÈTRES LIGHTGBM (OPTIMAUX) ===
    "lgbm_params": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 95,            # ✅ OPTIMAL
        "learning_rate": 0.025,      # ✅ OPTIMAL
        "feature_fraction": 0.75,    # ✅ OPTIMAL
        "bagging_fraction": 0.75,    # ✅ OPTIMAL
        "bagging_freq": 5,
        "min_data_in_leaf": 25,      # ✅ OPTIMAL
        "lambda_l1": 0.0,            # ✅ OPTIMAL
        "lambda_l2": 0.0,            # ✅ OPTIMAL
        "min_gain_to_split": 0.0,    # ✅ OPTIMAL
        "max_depth": -1,             # ✅ OPTIMAL
        "verbose": -1,
        "seed": RANDOM_SEED,
        "deterministic": True,
        "force_col_wise": True,
    },

    # === PARAMÈTRES TRAINING ===
    "training": {
        "horizon_seconds": 900,           # 15 minutes
        "threshold_mode": "atr",          # "atr" ou "fixed"
        "threshold_atr_mult": 0.3,        # 0.3x ATR
        "test_size": 0.20,                # 20% test
        "num_boost_round": 5000,          # Max iterations
        "early_stopping_rounds": 100,     # Patience
        "use_derived_menthorq": True,     # Créer features dérivées
        "use_feature_engineering": True,  # LAGs + Rolling
        "lag_periods": [1, 5, 10, 20, 60],
        "rolling_windows": [20, 60, 180]
    }
}


# ═══════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════

def setup_logging(symbol: str) -> logging.Logger:
    """Configure logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"train_3layer_{symbol}_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"📄 Logs sauvegardés dans: {log_file}")

    return logger


# ═══════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════════════

def load_ml_ready_data(symbol: str, data_dir: str = "ml_ready_data") -> pd.DataFrame:
    """
    Charge les snapshots ML_READY pour un symbole

    Args:
        symbol: ES, NQ, ou RTY
        data_dir: Répertoire des données

    Returns:
        DataFrame avec tous les snapshots
    """
    logger = logging.getLogger(__name__)

    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Répertoire {data_dir} introuvable")

    # Pattern fichier: ml_ESZ25_FUT_CME_9.jsonl (recherche récursive)
    pattern = f"**/ml_{symbol}*.jsonl"
    files = sorted(data_path.glob(pattern))

    if not files:
        raise FileNotFoundError(f"Aucun fichier {pattern} dans {data_dir}")

    logger.info(f"📂 Fichiers trouvés: {len(files)}")

    dfs = []
    for file in files:
        logger.info(f"📂 Chargement de {file.name}...")

        # Lecture JSONL
        with open(file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        records = [json.loads(line) for line in lines if line.strip()]
        df = pd.DataFrame(records)

        logger.info(f"✅ {file.name}: {len(df)} lignes")
        dfs.append(df)

    # Combiner
    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"✅ Total: {len(df_combined)} lignes combinées")

    return df_combined


def flatten_nested_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Aplatir les champs JSON imbriqués (next_wall, structure, menthor_distances)"""
    logger = logging.getLogger(__name__)

    # next_wall
    if 'next_wall' in df.columns and isinstance(df['next_wall'].iloc[0], dict):
        next_wall_df = pd.json_normalize(df['next_wall'])
        next_wall_df.columns = [f'next_wall_{col}' for col in next_wall_df.columns]
        df = pd.concat([df.drop('next_wall', axis=1), next_wall_df], axis=1)
        logger.info("✅ next_wall aplati")

    # structure
    if 'structure' in df.columns and isinstance(df['structure'].iloc[0], dict):
        structure_df = pd.json_normalize(df['structure'])
        structure_df.columns = [f'structure_{col}' for col in structure_df.columns]
        df = pd.concat([df.drop('structure', axis=1), structure_df], axis=1)
        logger.info("✅ structure aplati")

    # menthor_distances
    if 'menthor_distances' in df.columns and isinstance(df['menthor_distances'].iloc[0], dict):
        distances_df = pd.json_normalize(df['menthor_distances'])
        distances_df.columns = [f'menthor_distances_{col}' for col in distances_df.columns]
        df = pd.concat([df.drop('menthor_distances', axis=1), distances_df], axis=1)
        logger.info("✅ menthor_distances aplati")

    # vva (Value Area)
    if 'vva' in df.columns and isinstance(df['vva'].iloc[0], dict):
        vva_df = pd.json_normalize(df['vva'])
        vva_df.columns = [f'vva_{col}' for col in vva_df.columns]
        df = pd.concat([df.drop('vva', axis=1), vva_df], axis=1)
        logger.info("✅ vva aplati")

    return df


# ═══════════════════════════════════════════════════════════════════════
# LABELS (AS-OF LOOKUP SANS FUITE)
# ═══════════════════════════════════════════════════════════════════════

def create_labels_binary(df: pd.DataFrame, horizon_seconds: int,
                        threshold_mode: str, threshold_atr_mult: float,
                        tick_size: float) -> pd.DataFrame:
    """
    🔥 Labels UP/DOWN SANS FUITE TEMPORELLE (as-of lookup)

    Utilise searchsorted pour trouver la 1ère observation EXACTEMENT à t+horizon_seconds.
    Évite le leak temporel causé par .shift() sur données irrégulières.
    """
    logger = logging.getLogger(__name__)

    logger.info(f"🎯 Création labels binaires (horizon={horizon_seconds}s, mode={threshold_mode})...")

    df = df.copy()
    df['label'] = np.nan

    timestamps = df['tsec'].values
    prices = df['mid'].values
    atrs = df['atr'].values

    for i in range(len(df) - 1):
        t_now = timestamps[i]
        t_target = t_now + horizon_seconds

        # Trouver index futur via searchsorted (as-of)
        idx_future = np.searchsorted(timestamps, t_target, side='left')

        if idx_future >= len(timestamps):
            continue

        # Prix actuel et futur
        p_now = prices[i]
        p_future = prices[idx_future]

        # Calculer variation
        delta_pts = p_future - p_now
        delta_ticks = delta_pts / tick_size

        # Seuil
        if threshold_mode == "atr":
            threshold = atrs[i] * threshold_atr_mult
        else:
            threshold = threshold_atr_mult  # Fixed threshold

        # Label binaire
        if delta_pts > threshold:
            df.loc[i, 'label'] = 1  # UP
        elif delta_pts < -threshold:
            df.loc[i, 'label'] = 0  # DOWN
        else:
            df.loc[i, 'label'] = np.nan  # Neutral (ignoré)

    # Stats
    valid = df['label'].notna().sum()
    total = len(df)
    up = (df['label'] == 1).sum()
    down = (df['label'] == 0).sum()

    logger.info(f"✅ Labels créés:")
    logger.info(f"   Valid: {valid} ({valid/total*100:.1f}%)")
    logger.info(f"   UP: {up} ({up/valid*100:.1f}%)")
    logger.info(f"   DOWN: {down} ({down/valid*100:.1f}%)")

    return df


# ═══════════════════════════════════════════════════════════════════════
# FEATURES DÉRIVÉES MENTHORQ
# ═══════════════════════════════════════════════════════════════════════

def add_derived_menthorq(df: pd.DataFrame, tick_size: float) -> pd.DataFrame:
    """
    🔥 Crée features DÉRIVÉES MenthorQ (8 features critiques)

    Ces features normalisent les distances options pour le ML model.
    """
    logger = logging.getLogger(__name__)
    logger.info("🔥 Création features dérivées MenthorQ...")

    df = df.copy()
    mid = df['mid']
    atr = df['atr']

    # === GEX DISTANCES ===
    # Trouver GEX le plus proche au-dessus et en-dessous
    gex_cols = [f'gex_{i}' for i in range(1, 11)]
    gex_levels = df[gex_cols].values

    nearest_up = []
    nearest_down = []
    nearest_abs = []

    for i, row_mid in enumerate(mid):
        gex_row = gex_levels[i]
        gex_up = gex_row[gex_row > row_mid]
        gex_down = gex_row[gex_row < row_mid]

        d_up = (min(gex_up) - row_mid) / tick_size if len(gex_up) > 0 else np.nan
        d_down = (row_mid - max(gex_down)) / tick_size if len(gex_down) > 0 else np.nan
        d_abs = min(d_up, d_down) if not np.isnan(d_up) and not np.isnan(d_down) else (d_up if not np.isnan(d_up) else d_down)

        nearest_up.append(d_up)
        nearest_down.append(d_down)
        nearest_abs.append(d_abs)

    df['d_nearest_gex_up_ticks'] = nearest_up
    df['d_nearest_gex_down_ticks'] = nearest_down
    df['d_nearest_gex_abs_ticks'] = nearest_abs
    df['d_nearest_gex_atr'] = df['d_nearest_gex_abs_ticks'] / (atr / tick_size)  # Normalisation ATR

    logger.info("   ✅ GEX dérivés (4 features)")

    # === GAMMA WALLS / HVL DISTANCES ===
    df['d_call_resistance_ticks'] = (df['call_resistance'] - mid) / tick_size
    df['d_put_support_ticks'] = (mid - df['put_support']) / tick_size
    df['d_hvl_ticks'] = (df['hvl'] - mid).abs() / tick_size

    logger.info("   ✅ d_call_resistance_ticks")
    logger.info("   ✅ d_put_support_ticks")
    logger.info("   ✅ d_hvl_ticks")

    # === BLIND SPOTS DISTANCE ===
    blind_cols = [f'blind_spot_{i}' for i in range(9)]
    blind_spots = df[blind_cols].values

    nearest_blind = []
    for i, row_mid in enumerate(mid):
        blind_row = blind_spots[i]
        blind_row = blind_row[~np.isnan(blind_row)]

        if len(blind_row) > 0:
            distances = np.abs(blind_row - row_mid)
            nearest_blind.append(min(distances) / tick_size)
        else:
            nearest_blind.append(np.nan)

    df['d_nearest_blind_spot_abs_ticks'] = nearest_blind
    logger.info("   ✅ d_nearest_blind_spot_abs_ticks")

    logger.info(f"✅ Features dérivées MenthorQ créées: 8 features")

    return df


# ═══════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING (LAGs + Rolling)
# ═══════════════════════════════════════════════════════════════════════

def apply_feature_engineering(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Applique feature engineering (LAGs + Rolling means)"""
    logger = logging.getLogger(__name__)
    logger.info("⚙️  Feature Engineering...")

    # Features pour LAGs (OrderFlow principalement)
    lag_features = [
        'cum_delta_session', 'delta', 'smart_money_flow',
        'level1_imbalance', 'institutional_pressure'
    ]
    lag_features = [f for f in lag_features if f in df.columns]

    # Features pour Rolling (Context + MenthorQ)
    rolling_features = [
        'd_vwap', 'atr', 'd_nearest_gex_atr'
    ]
    rolling_features = [f for f in rolling_features if f in df.columns]

    # Appliquer
    fe = FeatureEngineer(
        lag_periods=config['training']['lag_periods'],
        rolling_windows=config['training']['rolling_windows']
    )

    df = fe.apply_all(df, lag_features, rolling_features)

    logger.info(f"✅ Feature Engineering terminé: {len(df.columns)} colonnes")

    return df


# ═══════════════════════════════════════════════════════════════════════
# SÉLECTION FEATURES 3-LAYER
# ═══════════════════════════════════════════════════════════════════════

def select_features_3layer(df: pd.DataFrame, config: Dict) -> Tuple[List[str], Dict[str, int]]:
    """
    Sélectionne features selon architecture 3-Layer

    Returns:
        (liste_features, stats_par_layer)
    """
    logger = logging.getLogger(__name__)

    # Récupérer features disponibles
    available = set(df.columns)

    selected = []
    stats = {"menthorq": 0, "orderflow": 0, "context": 0}

    # LAYER 1: MenthorQ
    for feat in config['features']['menthorq']:
        if feat in available:
            selected.append(feat)
            stats['menthorq'] += 1

    # LAYER 2: OrderFlow
    for feat in config['features']['orderflow']:
        if feat in available:
            selected.append(feat)
            stats['orderflow'] += 1

    # LAYER 3: Context
    for feat in config['features']['context']:
        if feat in available:
            selected.append(feat)
            stats['context'] += 1

    # Ajouter LAGs et Rolling si disponibles
    lag_rolling = [col for col in df.columns if '_lag_' in col or '_rolling_' in col]
    selected.extend(lag_rolling)

    logger.info(f"📊 Features sélectionnées: {len(selected)}")
    logger.info(f"   MenthorQ: {stats['menthorq']}")
    logger.info(f"   OrderFlow: {stats['orderflow']}")
    logger.info(f"   Context: {stats['context']}")
    logger.info(f"   LAGs + Rolling: {len(lag_rolling)}")

    return selected, stats


# ═══════════════════════════════════════════════════════════════════════
# ENCODAGE & NETTOYAGE
# ═══════════════════════════════════════════════════════════════════════

def encode_and_clean(X: pd.DataFrame) -> pd.DataFrame:
    """Encode catégorielles et nettoie NaN/Inf"""
    logger = logging.getLogger(__name__)

    logger.info("🔥 Encodage catégorielles directionnel...")

    # gamma_side: "above" → 1, "below" → -1 (DIRECTIONNEL)
    if 'gamma_side' in X.columns:
        X['gamma_side'] = X['gamma_side'].map({'above': 1, 'below': -1}).fillna(0).astype(np.int8)
        logger.info("   ✅ gamma_side encodé: above=1, below=-1")

    # next_wall_side: "call" → 1, "put" → -1 (DIRECTIONNEL)
    if 'next_wall_side' in X.columns:
        X['next_wall_side'] = X['next_wall_side'].map({'call': 1, 'put': -1}).fillna(0).astype(np.int8)
        logger.info("   ✅ next_wall_side encodé: call=1, put=-1")

    # Booleans → int8
    bool_features = [
        'gamma_flip_up', 'gamma_flip_down', 'gamma_call_confluence', 'gamma_put_confluence',
        'blind_spot_confluence', 'in_value_area', 'delta_flip'
    ]
    for b in bool_features:
        if b in X.columns:
            X[b] = X[b].astype(np.int8)
    logger.info(f"   ✅ {sum(b in X.columns for b in bool_features)} booleans → int8")

    # NaN/Inf handling
    nan_count = X.isna().sum().sum()
    if nan_count > 0:
        logger.info(f"⚙️  NaN handling: {nan_count} valeurs NaN")
        X = X.fillna(0)

    inf_count = np.isinf(X.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        logger.info(f"⚙️  Inf handling: {inf_count} valeurs Inf")
        X = X.replace([np.inf, -np.inf], 0)

    logger.info("✅ NaN/Inf remplacés par 0")

    return X


# ═══════════════════════════════════════════════════════════════════════
# ENTRAÎNEMENT LIGHTGBM
# ═══════════════════════════════════════════════════════════════════════

def train_lightgbm_3layer(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    config: Dict,
    symbol: str,
    output_dir: Path
) -> Tuple[lgb.Booster, Dict]:
    """
    Entraîne modèle LightGBM avec architecture 3-Layer

    Returns:
        (modèle, metrics)
    """
    logger = logging.getLogger(__name__)

    # Gestion déséquilibre classes
    pos = float((y_train == 1).sum())
    neg = float((y_train == 0).sum())
    spw = max(1.0, (neg / pos)) if pos > 0 else 1.0

    lgbm_params = dict(config['lgbm_params'])
    lgbm_params["scale_pos_weight"] = spw

    logger.info(f"⚖️  Déséquilibre classes:")
    logger.info(f"   UP (1): {int(pos)} ({pos/(pos+neg)*100:.1f}%)")
    logger.info(f"   DOWN (0): {int(neg)} ({neg/(pos+neg)*100:.1f}%)")
    logger.info(f"   scale_pos_weight: {spw:.2f}")

    # Créer datasets LightGBM
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    # Entraînement
    logger.info("🎓 Entraînement LightGBM...")

    model = lgb.train(
        lgbm_params,
        train_data,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        num_boost_round=config['training']['num_boost_round'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=config['training']['early_stopping_rounds']),
            lgb.log_evaluation(period=50)
        ]
    )

    # Évaluation
    logger.info("📊 Évaluation...")

    y_pred_proba = model.predict(X_test)
    y_pred = (y_pred_proba > 0.5).astype(int)

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)
    f1 = f1_score(y_test, y_pred)

    metrics = {
        'accuracy': accuracy,
        'auc': auc,
        'f1': f1,
        'best_iteration': model.best_iteration
    }

    logger.info("=" * 80)
    logger.info("📊 RÉSULTATS TEST SET")
    logger.info("=" * 80)
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"AUC: {auc:.4f}")
    logger.info(f"F1-Score: {f1:.4f}")
    logger.info(f"Best Iteration: {model.best_iteration}")

    # Feature Importance
    importance = model.feature_importance(importance_type='gain')
    feature_names = X_train.columns

    feat_imp = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    logger.info(f"\n🔥 TOP 20 FEATURES (By Gain):")
    for idx, row in feat_imp.head(20).iterrows():
        # Identifier layer
        if row['feature'] in config['features']['menthorq'] or any(x in row['feature'] for x in ['gex', 'blind', 'gamma', 'menthor']):
            layer_emoji = "🔥"
        elif row['feature'] in config['features']['orderflow'] or any(x in row['feature'] for x in ['delta', 'volume', 'dom']):
            layer_emoji = "✅"
        else:
            layer_emoji = "📊"

        logger.info(f"   {layer_emoji} {row['feature']}: {row['importance']:.1f}")

    # Sauvegarder feature importance
    feat_imp_file = output_dir / f"feature_importance_3layer_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    feat_imp.to_csv(feat_imp_file, index=False)
    logger.info(f"✅ Feature importance sauvegardée: {feat_imp_file}")

    return model, metrics


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Entraînement ML 3-Layer")
    parser.add_argument('--symbol', type=str, required=True, choices=['ES', 'NQ', 'RTY'],
                       help="Symbole à entraîner")
    parser.add_argument('--output-dir', type=str, default='ml/models_3layer',
                       help="Répertoire de sortie des modèles")
    parser.add_argument('--data-dir', type=str, default='ml_ready_data',
                       help="Répertoire des données ML_READY")

    args = parser.parse_args()

    # Setup
    logger = setup_logging(args.symbol)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"🔥 ENTRAÎNEMENT 3-LAYER - {args.symbol}")
    logger.info("=" * 80)
    logger.info(f"📏 Tick size {args.symbol}: {TICK_SIZE[args.symbol]}")

    # 1. Charger données
    df = load_ml_ready_data(args.symbol, args.data_dir)

    # 2. Aplatir JSON
    df = flatten_nested_fields(df)

    # 3. Créer features dérivées MenthorQ
    if CONFIG_3LAYER['training']['use_derived_menthorq']:
        df = add_derived_menthorq(df, TICK_SIZE[args.symbol])

    # 4. Créer labels
    df = create_labels_binary(
        df,
        CONFIG_3LAYER['training']['horizon_seconds'],
        CONFIG_3LAYER['training']['threshold_mode'],
        CONFIG_3LAYER['training']['threshold_atr_mult'],
        TICK_SIZE[args.symbol]
    )

    # 5. Feature Engineering
    if CONFIG_3LAYER['training']['use_feature_engineering']:
        df = apply_feature_engineering(df, CONFIG_3LAYER)

    # 6. Sélectionner features 3-Layer
    feature_list, stats = select_features_3layer(df, CONFIG_3LAYER)

    # 7. Préparer X, y
    df_clean = df[df['label'].notna()].copy()
    X = df_clean[feature_list].copy()
    y = df_clean['label'].astype(int)

    # 8. Encoder et nettoyer
    X = encode_and_clean(X)

    # 9. Split train/test (Time Series Split)
    split_idx = int(len(X) * (1 - CONFIG_3LAYER['training']['test_size']))
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    logger.info(f"✅ Split:")
    logger.info(f"   Train: {len(X_train)} samples")
    logger.info(f"   Test: {len(X_test)} samples")

    # 10. Entraîner modèle
    model, metrics = train_lightgbm_3layer(
        X_train, y_train, X_test, y_test,
        CONFIG_3LAYER, args.symbol, output_path
    )

    # 11. Sauvegarder modèle
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_file = output_path / f"lgbm_3layer_{args.symbol}_BINARY_{timestamp}.pkl"

    with open(model_file, 'wb') as f:
        pickle.dump({
            'model': model,
            'features': feature_list,
            'metrics': metrics,
            'config': CONFIG_3LAYER,
            'symbol': args.symbol,
            'timestamp': timestamp
        }, f)

    logger.info(f"✅ Modèle sauvegardé: {model_file}")

    # 12. Symlink latest (avec fallback copie pour Windows)
    latest_file = output_path / f"lgbm_3layer_{args.symbol}_BINARY_latest.pkl"
    if latest_file.exists():
        try:
            latest_file.unlink()
        except Exception:
            pass

    try:
        latest_file.symlink_to(model_file.name)
        logger.info(f"✅ Symlink créé: {latest_file}")
    except Exception as e:
        logger.warning(f"⚠️  Symlink échec ({e}), fallback copie...")
        import shutil
        shutil.copyfile(model_file, latest_file)
        logger.info(f"✅ Copie créée: {latest_file}")

    # 13. Temps total
    logger.info("=" * 80)
    logger.info("✅ ENTRAÎNEMENT TERMINÉ")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
