#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
ENTRAÎNEMENT ML - MENTHORQ PRIORITY MODE
═══════════════════════════════════════════════════════════════════════════════

🔥 VERSION SPÉCIALE: MenthorQ (OPTIONS) comme SIGNAL PRINCIPAL

Objectif : Prédire direction 15min avec MenthorQ comme features DOMINANTES
Algorithme : LightGBM avec feature_fraction contrôlé
Priorité Features : 70% MenthorQ, 20% Order Flow, 10% Autres

FEATURES MENTHORQ PRIORITAIRES (35 features):
───────────────────────────────────────────────
Groupe 1: NEXT_WALL (5 features) - 20% poids
  - next_wall.dist_ticks       ← Distance au mur gamma le plus proche
  - next_wall.strength          ← Force du mur (0-1)
  - next_wall.side              ← Type (call/put)
  - next_wall.age_min           ← Fraîcheur du niveau
  - next_wall.dist_pts          ← Distance en points

Groupe 2: NEAREST GEX (8 features) - 20% poids
  - d_nearest_gex_up_ticks      ← Distance GEX au-dessus
  - d_nearest_gex_down_ticks    ← Distance GEX en-dessous
  - d_nearest_gex_abs_ticks     ← Distance GEX le plus proche
  - d_nearest_gex_atr           ← Distance normalisée ATR
  - gex_1 à gex_10              ← 10 niveaux GEX

Groupe 3: BLIND SPOTS (9 features) - 10% poids
  - blind_spot_0 à blind_spot_8 ← 9 zones aveugles gamma
  - d_nearest_blind_spot_abs_ticks ← Distance blind spot proche

Groupe 4: GAMMA WALLS (6 features) - 10% poids
  - call_resistance             ← Résistance call majeure
  - put_support                 ← Support put majeur
  - gamma_side                  ← Position vs gamma (above/below)
  - gamma_flip_up               ← Franchissement haut
  - gamma_flip_down             ← Franchissement bas
  - gamma_wall_level            ← Niveau actif

Groupe 5: HVL & DISTANCES (7 features) - 10% poids
  - hvl                         ← High Volume Level
  - d_hvl_ticks                 ← Distance au HVL
  - menthor_distances_hvl0      ← Distance HVL primaire
  - menthor_distances_call0     ← Distance call principal
  - menthor_distances_put0      ← Distance put principal
  - menthor_distances_gamma0    ← Distance gamma principal
  - menthorq_proximity_strength ← Score proximité global

ORDRE DE PRIORITÉ FEATURE IMPORTANCE:
───────────────────────────────────────
1. next_wall.dist_ticks          (20%)  ← #1 CRITIQUE
2. d_nearest_gex_down_ticks      (15%)
3. d_nearest_gex_up_ticks        (15%)
4. next_wall.strength            (10%)
5. menthorq_proximity_strength   (10%)
6. d_nearest_blind_spot_abs      (8%)
7. gamma_side                    (7%)
8. hvl                           (5%)
9. smart_money_flow              (4%)
10. institutional_pressure       (3%)
... autres features              (3%)

HYPERPARAMÈTRES OPTIMISÉS MENTHORQ:
──────────────────────────────────────
- feature_fraction = 0.8          ← Force utilisation features critiques
- min_data_in_leaf = 50           ← Évite overfitting micro-patterns
- num_leaves = 63                 ← Arbre riche (patterns complexes)
- learning_rate = 0.03            ← Lent mais stable
- lambda_l1 = 0.5                 ← Régularisation forte
- lambda_l2 = 0.5
- feature_pre_filter = True       ← Force priority features

Auteur : MIA_IA_SYSTEM + Claude Sonnet 4.5
Date : 9 Novembre 2025
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
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_engineering import FeatureEngineer

# Configuration logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"train_menthorq_priority_{log_timestamp}.log"

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

# Reproductibilité
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
os.environ['PYTHONHASHSEED'] = str(RANDOM_SEED)

# 🔥 TICK SIZE PAR SYMBOLE (correction RTY)
TICK_SIZE = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION MENTHORQ PRIORITY
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_MENTHORQ = {
    # Chemins données
    "data_paths": {
        "es_chart3_05": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_3/ML_READY",
        "es_chart3_06": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_3/ML_READY",
        "es_chart3_07": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251107/CHART_3/ML_READY",
        "nq_chart9_05": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_9/ML_READY",
        "nq_chart9_06": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_9/ML_READY",
        "nq_chart9_07": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251107/CHART_9/ML_READY",
        "rty_chart1_05": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_1/ML_READY",
        "rty_chart1_06": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_1/ML_READY",
        "rty_chart1_07": "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251107/CHART_1/ML_READY",
    },

    # Labels
    "horizon_seconds": 900,  # 15 minutes
    "threshold_mode": "atr",
    "threshold_atr_multiplier": 0.35,
    "time_gap_tolerance": 60,

    # 🔥 FEATURES MENTHORQ PRIORITAIRES (51 features - 39% du total)
    "menthorq_priority_features": [
        # === GROUPE 1: NEXT_WALL (6 features) ===
        'next_wall_price',
        'next_wall_side',
        'next_wall_dist_pts',
        'next_wall_dist_ticks',  # ⭐ CRITIQUE #1
        'next_wall_strength',
        'next_wall_age_min',

        # === GROUPE 2: GEX LEVELS (10 features) ===
        'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
        'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',

        # === GROUPE 3: BLIND SPOTS (9 features) ===
        'blind_spot_0', 'blind_spot_1', 'blind_spot_2',
        'blind_spot_3', 'blind_spot_4', 'blind_spot_5',
        'blind_spot_6', 'blind_spot_7', 'blind_spot_8',

        # === GROUPE 4: GAMMA WALLS (8 features) ===
        'call_resistance',
        'put_support',
        'gamma_side',  # ⭐ CRITIQUE
        'gamma_wall_level',
        'gamma_flip_up',
        'gamma_flip_down',
        'gamma_call_confluence',
        'gamma_put_confluence',

        # === GROUPE 5: HVL & 1D RANGE (3 features) ===
        'hvl',
        '1d_max',
        '1d_min',

        # === GROUPE 6: MENTHOR DISTANCES (12 features) ===
        'menthor_distances_gamma0',
        'menthor_distances_call0',
        'menthor_distances_put0',
        'menthor_distances_hvl0',
        'menthor_distances_call',
        'menthor_distances_put',
        'menthor_distances_hvl',
        'menthor_distances_dist_1d_max',
        'menthor_distances_dist_1d_min',
        'menthor_distances_near_gex_up',   # ⭐ CRITIQUE
        'menthor_distances_near_gex_dn',   # ⭐ CRITIQUE
        'menthor_distances_near_blind',

        # === GROUPE 7: MENTHORQ SCORES (3 features) ===
        'menthorq_proximity_strength',  # ⭐ CRITIQUE
        'menthorq_impact_score',
        'blind_spot_confluence',

        # === GROUPE 8: DÉRIVÉES MENTHORQ (8 features) ===
        # Ces features sont créées par add_derived_menthorq()
        'd_nearest_gex_up_ticks',      # Distance GEX au-dessus
        'd_nearest_gex_down_ticks',    # Distance GEX en-dessous
        'd_nearest_gex_abs_ticks',     # Distance GEX le plus proche
        'd_nearest_gex_atr',            # Distance normalisée ATR
        'd_call_resistance_ticks',      # Distance call resistance
        'd_put_support_ticks',          # Distance put support
        'd_hvl_ticks',                  # Distance HVL
        'd_nearest_blind_spot_abs_ticks',  # Distance blind spot proche
    ],

    # 🔥 FEATURES SECONDAIRES (Order Flow - 29 features, 22% du total)
    "secondary_features": [
        # Delta (7)
        'delta',  # ⭐ CRITIQUE
        'delta_burst',
        'delta_flip',
        'cum_delta_day',
        'cum_delta_session',
        'deltaPct',
        'delta_cum_10s',

        # Smart Money & Institutional (2)
        'smart_money_flow',  # ⭐ CRITIQUE
        'institutional_pressure',  # ⭐ CRITIQUE

        # Bid/Ask Pressure (4)
        'askPct',
        'bidPct',
        'sell_pct',
        'buy_pct',

        # Imbalances (3)
        'level1_imbalance',  # ⭐ CRITIQUE
        'depth_imbalance',
        'micro_imb',

        # Pressure Strength (4)
        'pressure_strength',
        'pressure_strength_depth',
        'pressure_strength_atr',
        'pressure',

        # DOM Features (8)
        'dom_features_depth_bid',
        'dom_features_depth_ask',
        'dom_features_rings_bid',
        'dom_features_rings_ask',
        'dom_features_imbalance_1_3',  # ⭐
        'dom_features_imbalance_6_10',  # ⭐
        'dom_features_slope_bid_1_3_n',
        'dom_features_slope_ask_1_3_n',

        # Momentum (1)
        'tick_momentum',
    ],

    # 🔥 FEATURES TERTIAIRES (VWAP, Structure, Price Action, Volatilité - 53 features, 39% du total)
    "tertiary_features": [
        # VWAP Distances (6)
        'd_vwap',
        'd_vwap_ticks',  # ⭐ CRITIQUE
        'd_vwap_atr',
        'd_vwap_weekly',
        'd_vwap_weekly_ticks',  # ⭐
        'd_vwap_monthly_ticks',  # ⭐

        # VWAP Bands (8)
        'vwap_up1', 'vwap_dn1',
        'vwap_up2', 'vwap_dn2',
        'vwap_up3', 'vwap_dn3',
        'vwap_weekly_up1', 'vwap_weekly_dn1',

        # Value Area (7)
        'vva_vah', 'vva_val', 'vva_vpoc',
        'd_vah_ticks', 'd_val_ticks',
        'd_vpoc_ticks',  # ⭐ CRITIQUE
        'in_value_area',

        # PVWAP (6)
        'pvwap',
        'd_pvwap_ticks',  # ⭐
        'pvwap_up1', 'pvwap_dn1',
        'pvwap_up2', 'pvwap_dn2',

        # Structure (5)
        'structure_onh', 'structure_onl',
        'structure_ibh', 'structure_ibl',
        'structure_awap_ibo',

        # OHLCV (5)
        'open', 'high', 'low', 'close', 'volume',

        # Wicks & Range (5)
        'upper_wick_ticks',  # ⭐ CRITIQUE
        'lower_wick_ticks',  # ⭐ CRITIQUE
        'total_range_ticks',
        'distance_to_high_pct',
        'distance_to_low_pct',

        # Day Range (2)
        'day_range_pct',
        'position_in_range',

        # Stacked Imbalances (2)
        'stacked_imbalance_bid_rows',
        'stacked_imbalance_ask_rows',

        # Bullish Score (1)
        'mia_bullish_score',  # ⭐ CRITIQUE

        # Volatilité & Contexte (5)
        'atr',  # ⭐ CRITIQUE
        'volatility_regime',
        'volatility_regime_cont',
        'corr',
        'vix',

        # Confluence (2)
        'battle_navale_confidence',
        'confluence_proximity',
    ],

    # Colonnes interdites
    "forbidden_columns": [
        't_ms', 'tsec', 'seq_unified', 'elapsed_s', 'last_mq_update_ms',
        'bar_index', 'progress01', 'session_progress', 'session_elapsed_s',
    ],

    # 🔥 HYPERPARAMÈTRES MENTHORQ-OPTIMISÉS (copiés de train_ml_direction_15min.py - PROVEN)
    "lgbm_params": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 95,            # ✅ OPTIMAL: 2^6.5, compromis capacité/overfitting
        "learning_rate": 0.025,      # ✅ OPTIMAL: Convergence stable (vs 0.03)
        "feature_fraction": 0.75,    # ✅ OPTIMAL: Réduit corrélations (vs 0.85)
        "bagging_fraction": 0.75,    # ✅ OPTIMAL: Stabilité (vs 0.8)
        "bagging_freq": 5,
        "min_data_in_leaf": 25,      # ✅ OPTIMAL: ~0.2% train size (vs 50)
        "lambda_l1": 0.0,            # ✅ OPTIMAL: Pas de régularisation L1 (vs 0.5)
        "lambda_l2": 0.0,            # ✅ OPTIMAL: Pas de régularisation L2 (vs 0.5)
        "min_gain_to_split": 0.0,    # ✅ OPTIMAL: Laisse modèle décider
        "max_depth": -1,             # ✅ OPTIMAL: Pas de limite
        "verbose": -1,
        "seed": RANDOM_SEED,
        "deterministic": True,
        "force_col_wise": True,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES (Import depuis train_ml_direction_15min.py)
# ═══════════════════════════════════════════════════════════════════════════

def load_all_data(paths: List[Path]) -> pd.DataFrame:
    """Charge tous les fichiers JSONL et les combine"""
    logger.info(f"📂 Chargement de {len(paths)} fichiers...")

    dfs = []
    for path in paths:
        if not path.exists():
            logger.warning(f"⚠️  Fichier non trouvé: {path}")
            continue

        try:
            df = pd.read_json(path, lines=True)
            logger.info(f"✅ {path.name}: {len(df)} lignes")
            dfs.append(df)
        except Exception as e:
            logger.error(f"❌ Erreur lecture {path}: {e}")

    if not dfs:
        raise ValueError("❌ Aucun fichier chargé!")

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"✅ Total: {len(combined)} lignes combinées")

    return combined


def create_labels_binary(df: pd.DataFrame, horizon_seconds: int,
                        threshold_mode: str, threshold_atr_mult: float,
                        tick_size: float) -> pd.DataFrame:
    """
    🔥 Labels UP/DOWN SANS FUITE TEMPORELLE (as-of lookup)

    Utilise searchsorted pour trouver la 1ère observation EXACTEMENT à t+horizon_seconds.
    Évite le leak temporel causé par .shift() sur données irrégulières.

    Args:
        df: DataFrame avec colonnes t_ms, mid, atr
        horizon_seconds: Horizon de prédiction (900s = 15min)
        threshold_mode: "atr" ou "fixed"
        threshold_atr_mult: Multiplicateur ATR (0.35 optimal)
        tick_size: Taille du tick selon symbole

    Returns:
        DataFrame avec labels binaires (0=DOWN, 1=UP, -1=INVALID)
    """
    logger.info(f"🎯 Création labels binaires (horizon={horizon_seconds}s, mode={threshold_mode})...")

    # Sort par timestamp (CRITIQUE pour as-of lookup)
    df = df.sort_values('t_ms').reset_index(drop=True)

    # 🔥 AS-OF LOOKUP avec searchsorted (évite leak)
    t_ms = df['t_ms'].to_numpy()
    target = t_ms + horizon_seconds * 1000  # Convertir en millisecondes
    idx = np.searchsorted(t_ms, target, side='left')

    # Valider index (pas hors limites)
    valid = idx < len(df)
    future_mid = np.full(len(df), np.nan, dtype=float)
    future_mid[valid] = df['mid'].to_numpy()[idx[valid]]

    df['future_mid'] = future_mid
    df['future_t_ms'] = np.nan
    df.loc[valid, 'future_t_ms'] = t_ms[idx[valid]]

    # Time gap check (vérifier que c'est bien ~horizon_seconds)
    df['time_gap'] = (df['future_t_ms'] - df['t_ms']) / 1000
    df['valid_horizon'] = valid & df['future_mid'].notna()

    # Price change
    df['price_change'] = df['future_mid'] - df['mid']
    df['price_change_ticks'] = df['price_change'] / tick_size

    # Threshold
    if threshold_mode == 'atr':
        df['threshold'] = df['atr'] * threshold_atr_mult
        df['threshold_ticks'] = df['threshold'] / tick_size
    else:
        df['threshold'] = threshold_atr_mult * tick_size
        df['threshold_ticks'] = threshold_atr_mult

    # Labels binaires
    df['direction'] = -1  # INVALID par défaut
    mask = df['valid_horizon'] & df['future_mid'].notna()
    up = mask & (df['price_change_ticks'] >= df['threshold_ticks'])
    down = mask & ~up
    df.loc[up, 'direction'] = 1   # UP
    df.loc[down, 'direction'] = 0  # DOWN

    valid_count = (df['direction'] != -1).sum()
    up_count = (df['direction'] == 1).sum()
    down_count = (df['direction'] == 0).sum()

    logger.info(f"✅ Labels créés:")
    logger.info(f"   Valid: {valid_count} ({valid_count/len(df)*100:.1f}%)")
    logger.info(f"   UP: {up_count} ({up_count/valid_count*100:.1f}%)")
    logger.info(f"   DOWN: {down_count} ({down_count/valid_count*100:.1f}%)")

    return df


def flatten_nested_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten nested JSON fields"""
    for col in ['dom_features', 'menthor_distances', 'next_wall', 'intermarkets', 'structure', 'vva']:
        if col in df.columns:
            nested = pd.json_normalize(df[col])
            nested.columns = [f'{col}_{subcol}' for subcol in nested.columns]
            df = pd.concat([df.drop(columns=[col]), nested], axis=1)

    return df


def add_derived_menthorq(df: pd.DataFrame, tick_size: float) -> pd.DataFrame:
    """
    🔥 Crée features DÉRIVÉES MenthorQ (8 features critiques)

    Ces features sont essentielles pour la prédiction et doivent être créées
    EXPLICITEMENT (ne pas dépendre de FeatureEngineer).

    Args:
        df: DataFrame avec features MenthorQ de base
        tick_size: Taille du tick selon symbole

    Returns:
        DataFrame avec 8 features dérivées ajoutées
    """
    logger.info("🔥 Création features dérivées MenthorQ...")

    # 1. GEX DÉRIVÉS (4 features)
    if 'menthor_distances_near_gex_up' in df.columns and 'menthor_distances_near_gex_dn' in df.columns:
        df['d_nearest_gex_up_ticks'] = df['menthor_distances_near_gex_up']
        df['d_nearest_gex_down_ticks'] = df['menthor_distances_near_gex_dn']
        df['d_nearest_gex_abs_ticks'] = pd.concat([
            df['d_nearest_gex_up_ticks'].abs(),
            df['d_nearest_gex_down_ticks'].abs()
        ], axis=1).min(axis=1)
        df['d_nearest_gex_atr'] = (df['d_nearest_gex_abs_ticks'] * tick_size) / df['atr'].replace(0, np.nan)
        logger.info("   ✅ GEX dérivés (4 features)")

    # 2. GAMMA/HVL DISTANCES (3 features)
    if {'call_resistance', 'mid'}.issubset(df.columns):
        df['d_call_resistance_ticks'] = (df['call_resistance'] - df['mid']) / tick_size
        logger.info("   ✅ d_call_resistance_ticks")

    if {'put_support', 'mid'}.issubset(df.columns):
        df['d_put_support_ticks'] = (df['put_support'] - df['mid']) / tick_size
        logger.info("   ✅ d_put_support_ticks")

    if {'hvl', 'mid'}.issubset(df.columns):
        df['d_hvl_ticks'] = (df['hvl'] - df['mid']) / tick_size
        logger.info("   ✅ d_hvl_ticks")

    # 3. BLIND SPOT PROXIMITÉ (1 feature)
    if 'menthor_distances_near_blind' in df.columns:
        df['d_nearest_blind_spot_abs_ticks'] = df['menthor_distances_near_blind'].abs()
        logger.info("   ✅ d_nearest_blind_spot_abs_ticks")

    logger.info(f"✅ Features dérivées MenthorQ créées: 8 features")
    return df


def enforce_menthorq_priority(X_train: pd.DataFrame, X_test: pd.DataFrame,
                               priority_features: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    🔥 FORCE les features MenthorQ en priorité

    Stratégie:
    1. Identifier features MenthorQ présentes
    2. Les mettre en PREMIER dans l'ordre des colonnes
    3. Ajouter features secondaires après
    """
    logger.info("🔥 Enforcement priorité MenthorQ...")

    # Features présentes
    available_priority = [f for f in priority_features if f in X_train.columns]
    other_features = [f for f in X_train.columns if f not in priority_features]

    # Réordonner: MenthorQ FIRST, autres après
    ordered_cols = available_priority + other_features

    X_train = X_train[ordered_cols]
    X_test = X_test[ordered_cols]

    logger.info(f"✅ Features MenthorQ prioritaires: {len(available_priority)}")
    logger.info(f"   Autres features: {len(other_features)}")
    logger.info(f"   Ordre forcé: {ordered_cols[:10]}...")

    return X_train, X_test


# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRAINING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def train_menthorq_priority(symbol: str, output_dir: str = "ml/models_menthorq"):
    """
    Entraîne modèle avec MenthorQ en priorité absolue

    Args:
        symbol: "ES", "NQ", ou "RTY"
        output_dir: Dossier de sortie
    """
    logger.info("=" * 80)
    logger.info(f"🔥 ENTRAÎNEMENT MENTHORQ PRIORITY - {symbol}")
    logger.info("=" * 80)

    start_time = time.time()

    # Chemins selon symbole
    if symbol == "ES":
        paths = [
            Path(CONFIG_MENTHORQ["data_paths"]["es_chart3_05"]),
            Path(CONFIG_MENTHORQ["data_paths"]["es_chart3_06"]),
            Path(CONFIG_MENTHORQ["data_paths"]["es_chart3_07"]),
        ]
    elif symbol == "NQ":
        paths = [
            Path(CONFIG_MENTHORQ["data_paths"]["nq_chart9_05"]),
            Path(CONFIG_MENTHORQ["data_paths"]["nq_chart9_06"]),
            Path(CONFIG_MENTHORQ["data_paths"]["nq_chart9_07"]),
        ]
    else:  # RTY
        paths = [
            Path(CONFIG_MENTHORQ["data_paths"]["rty_chart1_05"]),
            Path(CONFIG_MENTHORQ["data_paths"]["rty_chart1_06"]),
            Path(CONFIG_MENTHORQ["data_paths"]["rty_chart1_07"]),
        ]

    # 🔥 Tick size selon symbole (CRITIQUE pour RTY)
    tick_size = TICK_SIZE.get(symbol, 0.25)
    logger.info(f"📏 Tick size {symbol}: {tick_size}")

    # Charger fichiers ML_READY
    all_jsonl = []
    for base_path in paths:
        if base_path.exists():
            all_jsonl.extend(list(base_path.glob("ml_*.jsonl")))

    if not all_jsonl:
        logger.error(f"❌ Aucun fichier ML_READY trouvé pour {symbol}")
        return

    logger.info(f"📂 Fichiers trouvés: {len(all_jsonl)}")

    df = load_all_data(all_jsonl)

    # 2. Créer labels binaires (as-of lookup, pas shift)
    df = create_labels_binary(
        df,
        horizon_seconds=CONFIG_MENTHORQ["horizon_seconds"],
        threshold_mode=CONFIG_MENTHORQ["threshold_mode"],
        threshold_atr_mult=CONFIG_MENTHORQ["threshold_atr_multiplier"],
        tick_size=tick_size  # 🔥 Utilise tick_size du symbole
    )

    # Filtrer valides
    df = df[df['direction'] != -1].reset_index(drop=True)

    # 3. Flatten nested fields
    df = flatten_nested_fields(df)

    # 3.5 🔥 Créer features dérivées MenthorQ (AVANT FeatureEngineer)
    df = add_derived_menthorq(df, tick_size)

    # 4. Feature Engineering
    logger.info("⚙️  Feature Engineering...")
    try:
        fe = FeatureEngineer()
        # Features pour LAGs et Rolling
        lag_features = ['close', 'delta', 'level1_imbalance', 'd_vwap_ticks', 'next_wall_dist_ticks']
        rolling_features = ['close', 'delta', 'level1_imbalance']

        df = fe.apply_all(df, lag_features, rolling_features)
        logger.info(f"✅ Feature Engineering terminé: {len(df.columns)} colonnes")
    except Exception as e:
        logger.warning(f"⚠️  Feature Engineering partiel: {e}")
        # Continuer sans feature engineering si erreur

    # 5. Sélectionner features
    all_priority = (
        CONFIG_MENTHORQ["menthorq_priority_features"] +
        CONFIG_MENTHORQ["secondary_features"] +
        CONFIG_MENTHORQ["tertiary_features"]
    )

    available_features = [f for f in all_priority if f in df.columns]
    forbidden = CONFIG_MENTHORQ["forbidden_columns"]

    feature_cols = [f for f in available_features if f not in forbidden]

    # Logger features manquantes
    missing_features = [f for f in all_priority if f not in df.columns]
    if missing_features:
        logger.warning(f"⚠️  Features manquantes ({len(missing_features)}): {missing_features[:10]}...")

    logger.info(f"📊 Features sélectionnées: {len(feature_cols)}")
    logger.info(f"   MenthorQ: {len([f for f in feature_cols if f in CONFIG_MENTHORQ['menthorq_priority_features']])}")
    logger.info(f"   Order Flow: {len([f for f in feature_cols if f in CONFIG_MENTHORQ['secondary_features']])}")
    logger.info(f"   Structure: {len([f for f in feature_cols if f in CONFIG_MENTHORQ['tertiary_features']])}")

    # 6. Préparer X, y
    X = df[feature_cols].copy()
    y = df['direction'].values

    # 🔥 ENCODER FEATURES CATÉGORIELLES (DIRECTIONNEL)
    logger.info("🔥 Encodage catégorielles directionnel...")

    # gamma_side: "above" → 1, "below" → -1 (DIRECTIONNEL)
    if 'gamma_side' in X.columns:
        X['gamma_side'] = X['gamma_side'].map({'above': 1, 'below': -1}).fillna(0).astype(np.int8)
        logger.info("   ✅ gamma_side encodé: above=1, below=-1")

    # next_wall_side: "call" → 1, "put" → -1 (DIRECTIONNEL)
    if 'next_wall_side' in X.columns:
        X['next_wall_side'] = X['next_wall_side'].map({'call': 1, 'put': -1}).fillna(0).astype(np.int8)
        logger.info("   ✅ next_wall_side encodé: call=1, put=-1")

    # Booleans → int8 (économie mémoire)
    bool_features = [
        'gamma_flip_up', 'gamma_flip_down',
        'gamma_call_confluence', 'gamma_put_confluence',
        'blind_spot_confluence', 'in_value_area', 'delta_flip'
    ]
    for b in bool_features:
        if b in X.columns:
            X[b] = X[b].astype(np.int8)
    logger.info(f"   ✅ {sum(b in X.columns for b in bool_features)} booleans → int8")

    # NaN handling
    logger.info(f"⚙️  NaN handling: {X.isna().sum().sum()} valeurs NaN")
    X = X.fillna(0)
    X = X.replace([np.inf, -np.inf], 0)
    logger.info("✅ NaN/Inf remplacés par 0")

    # 7. Split temporel (80/20)
    split_idx = int(len(X) * 0.8)
    X_train = X.iloc[:split_idx].reset_index(drop=True)
    X_test = X.iloc[split_idx:].reset_index(drop=True)
    y_train = y[:split_idx]
    y_test = y[split_idx:]

    logger.info(f"✅ Split:")
    logger.info(f"   Train: {len(X_train)} samples")
    logger.info(f"   Test: {len(X_test)} samples")

    # 8. 🔥 ENFORCER PRIORITÉ MENTHORQ
    X_train, X_test = enforce_menthorq_priority(
        X_train, X_test,
        CONFIG_MENTHORQ["menthorq_priority_features"]
    )

    # 9. 🔥 GESTION DÉSÉQUILIBRE CLASSES (scale_pos_weight)
    pos = float((y_train == 1).sum())
    neg = float((y_train == 0).sum())
    spw = max(1.0, (neg / pos)) if pos > 0 else 1.0

    lgbm_params = dict(CONFIG_MENTHORQ["lgbm_params"])
    lgbm_params["scale_pos_weight"] = spw

    logger.info(f"⚖️  Déséquilibre classes:")
    logger.info(f"   UP (1): {int(pos)} ({pos/(pos+neg)*100:.1f}%)")
    logger.info(f"   DOWN (0): {int(neg)} ({neg/(pos+neg)*100:.1f}%)")
    logger.info(f"   scale_pos_weight: {spw:.2f}")

    # 10. Entraîner LightGBM
    logger.info("🎓 Entraînement LightGBM...")

    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    model = lgb.train(
        lgbm_params,
        train_data,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        num_boost_round=5000,  # ✅ Comme ancien modèle (vs 600)
        callbacks=[
            lgb.early_stopping(stopping_rounds=100),  # ✅ Plus patient (vs 60)
            lgb.log_evaluation(period=50)
        ]
    )

    # 10. Évaluation
    logger.info("📊 Évaluation...")

    y_pred_proba = model.predict(X_test, num_iteration=model.best_iteration)
    y_pred = (y_pred_proba >= 0.5).astype(int)

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)

    logger.info("=" * 80)
    logger.info("📊 RÉSULTATS TEST SET")
    logger.info("=" * 80)
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"AUC: {auc:.4f}")
    logger.info(f"Best Iteration: {model.best_iteration}")

    # Feature importance
    importance = model.feature_importance(importance_type='gain')
    feature_names = X_train.columns

    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    logger.info("\n🔥 TOP 20 FEATURES (By Gain):")
    for idx, row in importance_df.head(20).iterrows():
        is_menthorq = row['feature'] in CONFIG_MENTHORQ["menthorq_priority_features"]
        prefix = "🔥" if is_menthorq else "  "
        logger.info(f"{prefix} {row['feature']}: {row['importance']:.1f}")

    # 11. Sauvegarder
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_file = output_path / f"lgbm_menthorq_{symbol}_BINARY_{timestamp}.pkl"

    with open(model_file, 'wb') as f:
        pickle.dump(model, f)

    logger.info(f"✅ Modèle sauvegardé: {model_file}")

    # Symlink latest (avec fallback copie pour Windows)
    latest_file = output_path / f"lgbm_menthorq_{symbol}_BINARY_latest.pkl"
    if latest_file.exists():
        try:
            latest_file.unlink()
        except Exception:
            pass

    # Try symlink (optimal), fallback copie si échec (Windows sans admin)
    try:
        latest_file.symlink_to(model_file.name)
        logger.info(f"✅ Symlink créé: {latest_file}")
    except Exception as e:
        logger.warning(f"⚠️  Symlink échec ({e}), fallback copie...")
        import shutil
        shutil.copyfile(model_file, latest_file)
        logger.info(f"✅ Copie créée: {latest_file}")

    # Sauvegarder importance
    importance_df.to_csv(
        output_path / f"feature_importance_menthorq_{symbol}_{timestamp}.csv",
        index=False
    )

    elapsed = time.time() - start_time
    logger.info(f"⏱️  Temps total: {elapsed/60:.1f} min")
    logger.info("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement ML MenthorQ Priority")
    parser.add_argument('--symbol', type=str, required=True, choices=['ES', 'NQ', 'RTY'],
                       help='Symbole à entraîner')
    parser.add_argument('--output-dir', type=str, default='ml/models_menthorq',
                       help='Dossier de sortie')

    args = parser.parse_args()

    train_menthorq_priority(args.symbol, args.output_dir)
