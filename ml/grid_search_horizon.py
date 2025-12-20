#!/usr/bin/env python3
"""
Grid Search pour trouver le meilleur horizon et les meilleurs seuils ATR
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys
from itertools import product

# Ajouter le répertoire parent au PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train_ml_direction_15min import load_all_data, create_labels
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

# ═══════════════════════════════════════════════════════════════════════════
# GRILLE DE PARAMÈTRES À TESTER
# ═══════════════════════════════════════════════════════════════════════════

GRID = {
    "horizons": [300, 600, 900, 1200],  # 5, 10, 15, 20 minutes
    "atr_multipliers_es": [0.22, 0.28, 0.35, 0.42],
    "atr_multipliers_nq": [0.18, 0.24, 0.30, 0.36],
    "atr_multipliers_rty": [0.25, 0.32, 0.40, 0.48],
}

SYMBOLS = {
    "ES": {
        "data_dirs": [
            "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_3/ML_READY",
            "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_3/ML_READY"
        ],
        "tick_size": 0.25,
        "atr_key": "atr_multipliers_es"
    },
    "NQ": {
        "data_dirs": [
            "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_9/ML_READY",
            "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_9/ML_READY"
        ],
        "tick_size": 0.25,
        "atr_key": "atr_multipliers_nq"
    },
    "RTY": {
        "data_dirs": [
            "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_1/ML_READY",
            "DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_1/ML_READY"
        ],
        "tick_size": 0.10,
        "atr_key": "atr_multipliers_rty"
    }
}


def quick_train_and_evaluate(df, feature_cols):
    """
    Entraînement rapide pour évaluation
    """
    # Split temporel simple 80/20
    split_idx = int(len(df) * 0.8)
    df_train = df.iloc[:split_idx].copy()
    df_test = df.iloc[split_idx:].copy()

    # Préparer X, y
    X_train = df_train[feature_cols].fillna(0)
    y_train = df_train['label']
    X_test = df_test[feature_cols].fillna(0)
    y_test = df_test['label']

    # Entraînement léger
    model = LGBMClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )

    model.fit(X_train, y_train)

    # Prédictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # Métriques
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='macro')

    try:
        auc = roc_auc_score(y_test, y_proba)
    except:
        auc = 0.5

    # Distribution des labels
    label_dist = y_train.value_counts(normalize=True).to_dict()
    down_pct = label_dist.get(0, 0) * 100
    up_pct = label_dist.get(1, 0) * 100
    balance_ratio = max(down_pct, up_pct) / min(down_pct, up_pct) if min(down_pct, up_pct) > 0 else 999

    return {
        "accuracy": acc,
        "f1_macro": f1,
        "auc": auc,
        "n_train": len(df_train),
        "n_test": len(df_test),
        "down_pct": down_pct,
        "up_pct": up_pct,
        "balance_ratio": balance_ratio
    }


def test_configuration(symbol, horizon, atr_mult, data_dirs, tick_size):
    """
    Teste une configuration spécifique
    """
    print(f"\n{'─'*70}")
    print(f"🧪 TEST: {symbol} | Horizon={horizon}s ({horizon//60}min) | ATR×{atr_mult:.2f}")
    print(f"{'─'*70}")

    try:
        # Charger les données
        df = load_all_data(data_dirs, f"{symbol} Grid Search")

        # Créer les labels
        df = create_labels(
            df,
            horizon_seconds=horizon,
            threshold_ticks=None,
            tick_size=tick_size,
            time_gap_tolerance=60,
            threshold_mode="atr",
            atr_multiplier=atr_mult,
            binary_mode=True
        )

        # Filtrer les valides
        df_valid = df[df['label'].notna()].copy()

        if len(df_valid) < 500:
            print(f"⚠️  Pas assez de samples valides: {len(df_valid)}")
            return None

        # Features basiques pour le test rapide
        base_features = [
            'mid', 'spread_ticks', 'atr', 'delta', 'cum_delta_session',
            'd_vwap_ticks', 'd_vpoc_ticks', 'level1_imbalance', 'depth_imbalance',
            'ob_center', 'vwap', 'd_vwap_atr', 'smart_money_flow'
        ]

        # Filtrer les features disponibles
        available_features = [f for f in base_features if f in df_valid.columns]

        # Entraîner et évaluer
        results = quick_train_and_evaluate(df_valid, available_features)

        # Afficher les résultats
        print(f"✅ Accuracy: {results['accuracy']:.3f} | F1: {results['f1_macro']:.3f} | AUC: {results['auc']:.3f}")
        print(f"📊 Labels: DOWN={results['down_pct']:.1f}% UP={results['up_pct']:.1f}% (ratio={results['balance_ratio']:.2f}:1)")
        print(f"📈 Samples: {results['n_train']:,} train / {results['n_test']:,} test")

        return {
            "symbol": symbol,
            "horizon_sec": horizon,
            "horizon_min": horizon // 60,
            "atr_mult": atr_mult,
            **results,
            "score": results['auc'] * 0.4 + results['f1_macro'] * 0.3 + (1.0 / results['balance_ratio']) * 0.3
        }

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def main():
    """
    Point d'entrée principal
    """
    print("\n" + "="*70)
    print("🔍 GRID SEARCH - HORIZON & SEUILS ATR OPTIMAUX")
    print("="*70)
    print(f"\n📊 Configurations à tester par symbole:")
    print(f"   Horizons: {GRID['horizons']} secondes")
    print(f"   ES ATR mult: {GRID['atr_multipliers_es']}")
    print(f"   NQ ATR mult: {GRID['atr_multipliers_nq']}")
    print(f"   RTY ATR mult: {GRID['atr_multipliers_rty']}")

    total_tests = len(SYMBOLS) * len(GRID['horizons']) * len(GRID['atr_multipliers_es'])
    print(f"\n🎯 Total: {total_tests} configurations à tester")
    print(f"⏱️  Durée estimée: ~{total_tests * 0.5:.0f} minutes")

    input("\n▶️  Appuyez sur ENTRÉE pour démarrer...")

    all_results = []

    for symbol, config in SYMBOLS.items():
        print(f"\n{'═'*70}")
        print(f"📈 SYMBOLE: {symbol}")
        print(f"{'═'*70}")

        for horizon in GRID['horizons']:
            for atr_mult in GRID[config['atr_key']]:
                result = test_configuration(
                    symbol,
                    horizon,
                    atr_mult,
                    config['data_dirs'],
                    config['tick_size']
                )

                if result:
                    all_results.append(result)

    # Sauvegarder tous les résultats
    output_path = Path("ml/grid_search_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print("🏆 RÉSULTATS FINAUX - TOP 10 CONFIGURATIONS")
    print(f"{'='*70}\n")

    # Trier par score
    sorted_results = sorted(all_results, key=lambda x: x['score'], reverse=True)

    # Afficher le top 10
    print(f"{'Rank':<5} {'Symbol':<8} {'Horizon':<10} {'ATR':<8} {'AUC':<8} {'F1':<8} {'Balance':<10} {'Score':<8}")
    print("─"*80)

    for i, r in enumerate(sorted_results[:10], 1):
        print(f"{i:<5} {r['symbol']:<8} {r['horizon_min']:>3}min     {r['atr_mult']:<8.2f} {r['auc']:<8.3f} {r['f1_macro']:<8.3f} {r['balance_ratio']:<10.2f} {r['score']:<8.3f}")

    # Meilleure config par symbole
    print(f"\n{'='*70}")
    print("🥇 MEILLEURE CONFIGURATION PAR SYMBOLE")
    print(f"{'='*70}\n")

    for symbol in SYMBOLS.keys():
        symbol_results = [r for r in sorted_results if r['symbol'] == symbol]
        if symbol_results:
            best = symbol_results[0]
            print(f"📊 {symbol}:")
            print(f"   Horizon: {best['horizon_min']} minutes ({best['horizon_sec']}s)")
            print(f"   ATR mult: {best['atr_mult']:.2f}")
            print(f"   AUC: {best['auc']:.3f} | F1: {best['f1_macro']:.3f} | Acc: {best['accuracy']:.3f}")
            print(f"   Balance: DOWN={best['down_pct']:.1f}% UP={best['up_pct']:.1f}% (ratio={best['balance_ratio']:.2f}:1)")
            print(f"   Score global: {best['score']:.3f}")
            print()

    print(f"\n✅ Résultats complets sauvegardés: {output_path}")


if __name__ == "__main__":
    main()

