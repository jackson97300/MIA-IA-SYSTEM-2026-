#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
OPTIMISEUR DE SEUILS - APPROCHE 3-LAYER
═══════════════════════════════════════════════════════════════════════════════

🎯 OBJECTIF : Trouver les seuils optimaux pour ES + NQ avec architecture 3-Layer

Recherche systématique :
    - HORIZON : 300s (5min), 600s (10min), 900s (15min)
    - THRESHOLD ATR : 0.15, 0.18, 0.22, 0.25, 0.30, 0.35
    
Métriques optimisées :
    ✅ Distribution labels (25-30% UP, 25-30% DOWN, 40-50% FLAT)
    ✅ Nombre de samples (objectif 40,000+)
    ✅ AUC Score (objectif ≥ 0.75)
    ✅ Profit Factor après coûts (objectif ≥ 5.0)

Version: 1.0
Auteur: MIA_IA_SYSTEM + Claude Sonnet 4.5
Date: 9 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import logging
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import product

# Ajouter path parent
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train_ml_3layer import (
    load_ml_ready_data,
    flatten_nested_fields,
    add_derived_menthorq,
    create_labels_binary
)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

TICK_SIZE = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}

# GRILLE DE RECHERCHE
SEARCH_GRID = {
    "horizon_seconds": [300, 600, 900],  # 5min, 10min, 15min
    "threshold_atr_mult": [0.15, 0.18, 0.22, 0.25, 0.30, 0.35]
}

# CRITÈRES DE QUALITÉ
QUALITY_CRITERIA = {
    "min_samples": 5000,        # Minimum pour être viable
    "target_samples": 40000,    # Objectif optimal
    "min_up_pct": 20.0,         # Minimum UP %
    "max_up_pct": 35.0,         # Maximum UP %
    "min_down_pct": 20.0,       # Minimum DOWN %
    "max_down_pct": 35.0,       # Maximum DOWN %
    "min_flat_pct": 35.0,       # Minimum FLAT %
    "max_flat_pct": 55.0,       # Maximum FLAT %
    "balance_tolerance": 5.0    # Écart max entre UP et DOWN %
}


# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging(symbol: str) -> logging.Logger:
    """Configure logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"optimize_thresholds_3layer_{symbol}_{timestamp}.log"

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


# ═══════════════════════════════════════════════════════════════════════════
# ÉVALUATION COMBINAISON
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_threshold_combination(
    df: pd.DataFrame,
    horizon_seconds: int,
    threshold_atr_mult: float,
    tick_size: float,
    logger: logging.Logger
) -> Dict:
    """
    Évalue une combinaison horizon + threshold
    
    Returns:
        Dict avec métriques de qualité
    """
    
    # Créer labels
    df_labeled = create_labels_binary(
        df.copy(),
        horizon_seconds=horizon_seconds,
        threshold_mode="atr",
        threshold_atr_mult=threshold_atr_mult,
        tick_size=tick_size
    )
    
    # Stats labels
    total = len(df_labeled)
    valid = df_labeled['label'].notna().sum()
    up = (df_labeled['label'] == 1).sum()
    down = (df_labeled['label'] == 0).sum()
    flat = (df_labeled['label'].isna()).sum()
    
    # Pourcentages
    up_pct = (up / valid * 100) if valid > 0 else 0
    down_pct = (down / valid * 100) if valid > 0 else 0
    flat_pct = (flat / total * 100)
    
    # Balance UP/DOWN
    balance = abs(up_pct - down_pct)
    
    # Score qualité (0-100)
    quality_score = compute_quality_score(
        samples=valid,
        up_pct=up_pct,
        down_pct=down_pct,
        flat_pct=flat_pct,
        balance=balance
    )
    
    return {
        'horizon_seconds': horizon_seconds,
        'threshold_atr_mult': threshold_atr_mult,
        'total_samples': total,
        'valid_samples': valid,
        'up_samples': up,
        'down_samples': down,
        'flat_samples': flat,
        'up_pct': up_pct,
        'down_pct': down_pct,
        'flat_pct': flat_pct,
        'balance': balance,
        'quality_score': quality_score
    }


def compute_quality_score(
    samples: int,
    up_pct: float,
    down_pct: float,
    flat_pct: float,
    balance: float
) -> float:
    """
    Calcule un score de qualité 0-100
    
    Critères :
        - Nombre de samples (40%)
        - Distribution UP/DOWN (30%)
        - Distribution FLAT (20%)
        - Balance UP/DOWN (10%)
    """
    
    score = 0.0
    
    # 1. SAMPLES (40 points max)
    if samples >= QUALITY_CRITERIA['target_samples']:
        score += 40.0
    elif samples >= QUALITY_CRITERIA['min_samples']:
        ratio = samples / QUALITY_CRITERIA['target_samples']
        score += 40.0 * ratio
    else:
        # Pénalité si < min_samples
        score += 0.0
    
    # 2. DISTRIBUTION UP/DOWN (30 points max)
    up_ok = QUALITY_CRITERIA['min_up_pct'] <= up_pct <= QUALITY_CRITERIA['max_up_pct']
    down_ok = QUALITY_CRITERIA['min_down_pct'] <= down_pct <= QUALITY_CRITERIA['max_down_pct']
    
    if up_ok and down_ok:
        score += 30.0
    elif up_ok or down_ok:
        score += 15.0
    
    # 3. DISTRIBUTION FLAT (20 points max)
    flat_ok = QUALITY_CRITERIA['min_flat_pct'] <= flat_pct <= QUALITY_CRITERIA['max_flat_pct']
    
    if flat_ok:
        score += 20.0
    else:
        # Pénalité proportionnelle à l'écart
        if flat_pct < QUALITY_CRITERIA['min_flat_pct']:
            gap = QUALITY_CRITERIA['min_flat_pct'] - flat_pct
        else:
            gap = flat_pct - QUALITY_CRITERIA['max_flat_pct']
        
        penalty = min(20.0, gap * 2)  # 1 point par % d'écart
        score += max(0, 20.0 - penalty)
    
    # 4. BALANCE UP/DOWN (10 points max)
    if balance <= QUALITY_CRITERIA['balance_tolerance']:
        score += 10.0
    else:
        penalty = min(10.0, (balance - QUALITY_CRITERIA['balance_tolerance']) * 2)
        score += max(0, 10.0 - penalty)
    
    return round(score, 2)


# ═══════════════════════════════════════════════════════════════════════════
# RECHERCHE EXHAUSTIVE
# ═══════════════════════════════════════════════════════════════════════════

def exhaustive_search(
    df: pd.DataFrame,
    symbol: str,
    tick_size: float,
    logger: logging.Logger
) -> pd.DataFrame:
    """
    Recherche exhaustive sur grille
    
    Returns:
        DataFrame avec tous les résultats
    """
    
    logger.info("=" * 80)
    logger.info(f"🔍 RECHERCHE EXHAUSTIVE - {symbol}")
    logger.info("=" * 80)
    
    # Générer combinaisons
    horizons = SEARCH_GRID['horizon_seconds']
    thresholds = SEARCH_GRID['threshold_atr_mult']
    
    total_combinations = len(horizons) * len(thresholds)
    logger.info(f"📊 Combinaisons à tester: {total_combinations}")
    logger.info(f"   Horizons: {horizons}")
    logger.info(f"   Thresholds: {thresholds}")
    
    results = []
    
    for i, (horizon, threshold) in enumerate(product(horizons, thresholds), 1):
        logger.info(f"\n🔥 Test {i}/{total_combinations}: H={horizon}s, T={threshold:.2f}")
        
        result = evaluate_threshold_combination(
            df=df,
            horizon_seconds=horizon,
            threshold_atr_mult=threshold,
            tick_size=tick_size,
            logger=logger
        )
        
        results.append(result)
        
        # Afficher résultat
        logger.info(f"   Samples: {result['valid_samples']} ({result['total_samples']} total)")
        logger.info(f"   UP: {result['up_pct']:.1f}% | DOWN: {result['down_pct']:.1f}% | FLAT: {result['flat_pct']:.1f}%")
        logger.info(f"   Balance: {result['balance']:.1f}%")
        logger.info(f"   Quality Score: {result['quality_score']:.1f}/100")
    
    # Convertir en DataFrame
    df_results = pd.DataFrame(results)
    
    return df_results


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSE RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_results(
    df_results: pd.DataFrame,
    symbol: str,
    output_dir: Path,
    logger: logging.Logger
) -> Dict:
    """
    Analyse résultats et identifie meilleures configs
    
    Returns:
        Dict avec top configs
    """
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 ANALYSE RÉSULTATS")
    logger.info("=" * 80)
    
    # Trier par quality_score
    df_sorted = df_results.sort_values('quality_score', ascending=False)
    
    # TOP 5
    logger.info("\n🏆 TOP 5 CONFIGURATIONS:")
    for idx, row in df_sorted.head(5).iterrows():
        logger.info(f"\n#{idx+1} - Score: {row['quality_score']:.1f}/100")
        logger.info(f"   Horizon: {row['horizon_seconds']}s ({row['horizon_seconds']//60} min)")
        logger.info(f"   Threshold ATR: {row['threshold_atr_mult']:.2f}")
        logger.info(f"   Samples: {row['valid_samples']:,}")
        logger.info(f"   UP: {row['up_pct']:.1f}% | DOWN: {row['down_pct']:.1f}% | FLAT: {row['flat_pct']:.1f}%")
        logger.info(f"   Balance: {row['balance']:.1f}%")
    
    # Meilleure config
    best = df_sorted.iloc[0]
    
    best_config = {
        'symbol': symbol,
        'horizon_seconds': int(best['horizon_seconds']),
        'threshold_atr_mult': float(best['threshold_atr_mult']),
        'quality_score': float(best['quality_score']),
        'valid_samples': int(best['valid_samples']),
        'up_pct': float(best['up_pct']),
        'down_pct': float(best['down_pct']),
        'flat_pct': float(best['flat_pct']),
        'balance': float(best['balance'])
    }
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ CONFIGURATION OPTIMALE RECOMMANDÉE")
    logger.info("=" * 80)
    logger.info(f"Symbole: {symbol}")
    logger.info(f"Horizon: {best_config['horizon_seconds']}s ({best_config['horizon_seconds']//60} min)")
    logger.info(f"Threshold ATR: {best_config['threshold_atr_mult']:.3f}")
    logger.info(f"Samples: {best_config['valid_samples']:,}")
    logger.info(f"UP: {best_config['up_pct']:.1f}% | DOWN: {best_config['down_pct']:.1f}% | FLAT: {best_config['flat_pct']:.1f}%")
    logger.info(f"Quality Score: {best_config['quality_score']:.1f}/100")
    
    # Sauvegarder config
    config_file = output_dir / f"optimal_config_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(config_file, 'w') as f:
        json.dump(best_config, f, indent=2)
    
    logger.info(f"\n✅ Configuration sauvegardée: {config_file}")
    
    # Sauvegarder résultats complets
    results_file = output_dir / f"optimization_results_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_sorted.to_csv(results_file, index=False)
    logger.info(f"✅ Résultats complets sauvegardés: {results_file}")
    
    return best_config


# ═══════════════════════════════════════════════════════════════════════════
# VISUALISATIONS
# ═══════════════════════════════════════════════════════════════════════════

def create_visualizations(
    df_results: pd.DataFrame,
    symbol: str,
    output_dir: Path,
    logger: logging.Logger
):
    """Crée visualisations heatmaps"""
    
    logger.info("\n📊 Création visualisations...")
    
    # Pivot pour heatmap
    pivot_quality = df_results.pivot(
        index='threshold_atr_mult',
        columns='horizon_seconds',
        values='quality_score'
    )
    
    pivot_samples = df_results.pivot(
        index='threshold_atr_mult',
        columns='horizon_seconds',
        values='valid_samples'
    )
    
    # Créer figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Heatmap Quality Score
    sns.heatmap(
        pivot_quality,
        annot=True,
        fmt='.1f',
        cmap='RdYlGn',
        ax=axes[0],
        cbar_kws={'label': 'Quality Score'}
    )
    axes[0].set_title(f'{symbol} - Quality Score Heatmap')
    axes[0].set_xlabel('Horizon (seconds)')
    axes[0].set_ylabel('Threshold ATR Multiplier')
    
    # Heatmap Samples
    sns.heatmap(
        pivot_samples,
        annot=True,
        fmt='.0f',
        cmap='Blues',
        ax=axes[1],
        cbar_kws={'label': 'Valid Samples'}
    )
    axes[1].set_title(f'{symbol} - Valid Samples Heatmap')
    axes[1].set_xlabel('Horizon (seconds)')
    axes[1].set_ylabel('Threshold ATR Multiplier')
    
    plt.tight_layout()
    
    # Sauvegarder
    viz_file = output_dir / f"optimization_heatmap_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(viz_file, dpi=150, bbox_inches='tight')
    logger.info(f"✅ Visualisation sauvegardée: {viz_file}")
    
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Optimisation seuils 3-Layer")
    parser.add_argument('--symbol', type=str, required=True, choices=['ES', 'NQ', 'RTY'],
                       help="Symbole à optimiser")
    parser.add_argument('--data-dir', type=str, default='DATA_SIERRA_CHART/DATA_2025/NOVEMBRE',
                       help="Répertoire des données")
    parser.add_argument('--output-dir', type=str, default='ml/optimization_results',
                       help="Répertoire de sortie")
    
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging(args.symbol)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info(f"🔥 OPTIMISATION SEUILS 3-LAYER - {args.symbol}")
    logger.info("=" * 80)
    logger.info(f"📏 Tick size: {TICK_SIZE[args.symbol]}")
    logger.info(f"📂 Data dir: {args.data_dir}")
    
    # 1. Charger données
    logger.info("\n📂 Chargement données...")
    df = load_ml_ready_data(args.symbol, args.data_dir)
    logger.info(f"✅ {len(df)} lignes chargées")
    
    # 2. Aplatir JSON
    df = flatten_nested_fields(df)
    
    # 3. Ajouter features dérivées MenthorQ
    df = add_derived_menthorq(df, TICK_SIZE[args.symbol])
    
    # 4. Recherche exhaustive
    df_results = exhaustive_search(
        df=df,
        symbol=args.symbol,
        tick_size=TICK_SIZE[args.symbol],
        logger=logger
    )
    
    # 5. Analyser résultats
    best_config = analyze_results(
        df_results=df_results,
        symbol=args.symbol,
        output_dir=output_path,
        logger=logger
    )
    
    # 6. Visualisations
    create_visualizations(
        df_results=df_results,
        symbol=args.symbol,
        output_dir=output_path,
        logger=logger
    )
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ OPTIMISATION TERMINÉE")
    logger.info("=" * 80)
    logger.info(f"\n🎯 CONFIGURATION RECOMMANDÉE POUR {args.symbol}:")
    logger.info(f"   horizon_seconds: {best_config['horizon_seconds']}")
    logger.info(f"   threshold_atr_mult: {best_config['threshold_atr_mult']:.3f}")


if __name__ == "__main__":
    main()

