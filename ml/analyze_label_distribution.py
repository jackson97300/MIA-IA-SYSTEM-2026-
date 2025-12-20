#!/usr/bin/env python3
"""
Analyse la distribution des labels (UP/DOWN) pour chaque symbole
afin de détecter les déséquilibres de classe.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys

# Ajouter le répertoire parent au PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train_ml_direction_15min import load_all_data, create_labels

# Configuration
CONFIG = {
    "horizon_seconds": 300,  # 5 minutes
    "threshold_atr_multiplier_es": 0.22,
    "threshold_atr_multiplier_nq": 0.18,
    "threshold_atr_multiplier_rty": 0.25,
    "tick_size_es": 0.25,
    "tick_size_nq": 0.25,
    "tick_size_rty": 0.10,
}

def analyze_symbol(symbol_name, data_dirs, atr_mult, tick_size):
    """Analyse la distribution des labels pour un symbole"""

    print(f"\n{'='*70}")
    print(f"📊 ANALYSE {symbol_name}")
    print(f"{'='*70}")

    # Charger les données
    df = load_all_data(data_dirs, f"{symbol_name} Analysis")
    print(f"✅ {len(df):,} samples chargés")

    # Créer les labels
    df = create_labels(
        df,
        horizon_seconds=CONFIG['horizon_seconds'],
        threshold_ticks=None,
        tick_size=tick_size,
        time_gap_tolerance=60,
        threshold_mode="atr",
        atr_multiplier=atr_mult,
        binary_mode=True
    )

    # Filtrer les NaN
    df_valid = df[df['label'].notna()].copy()
    print(f"✅ {len(df_valid):,} samples avec labels valides ({len(df_valid)/len(df)*100:.1f}%)")

    # Distribution des labels
    label_counts = df_valid['label'].value_counts()
    label_pcts = df_valid['label'].value_counts(normalize=True) * 100

    print(f"\n📈 DISTRIBUTION DES LABELS:")
    print(f"{'='*70}")
    for label in sorted(label_counts.index):
        label_name = "UP" if label == 1 else "DOWN"
        count = label_counts[label]
        pct = label_pcts[label]
        print(f"  {label_name:8s} : {count:6,} samples ({pct:5.1f}%)")

    # Ratio UP/DOWN
    if len(label_counts) >= 2:
        ratio = label_counts.max() / label_counts.min()
        print(f"\n⚖️  Ratio déséquilibre : {ratio:.2f}:1")

        if ratio > 2.0:
            print(f"❌ DÉSÉQUILIBRE CRITIQUE (ratio > 2.0)")
        elif ratio > 1.5:
            print(f"⚠️  DÉSÉQUILIBRE MODÉRÉ (ratio > 1.5)")
        else:
            print(f"✅ ÉQUILIBRE ACCEPTABLE (ratio < 1.5)")

    # Statistiques ATR
    print(f"\n📊 STATISTIQUES ATR:")
    print(f"{'='*70}")
    print(f"  ATR moyen : {df_valid['atr'].mean():.4f}")
    print(f"  ATR médian : {df_valid['atr'].median():.4f}")
    print(f"  ATR min : {df_valid['atr'].min():.4f}")
    print(f"  ATR max : {df_valid['atr'].max():.4f}")

    # Seuil effectif
    threshold_pts = df_valid['atr'].median() * atr_mult
    threshold_ticks = threshold_pts / tick_size
    print(f"\n🎯 SEUIL EFFECTIF:")
    print(f"  ATR multiplier : {atr_mult}")
    print(f"  Seuil médian : {threshold_pts:.2f} pts ({threshold_ticks:.1f} ticks)")

    return {
        "symbol": symbol_name,
        "total_samples": len(df),
        "valid_samples": len(df_valid),
        "valid_pct": len(df_valid)/len(df)*100,
        "label_counts": label_counts.to_dict(),
        "label_pcts": label_pcts.to_dict(),
        "imbalance_ratio": label_counts.max() / label_counts.min() if len(label_counts) >= 2 else 1.0,
        "atr_mean": float(df_valid['atr'].mean()),
        "atr_median": float(df_valid['atr'].median()),
        "threshold_pts": float(threshold_pts),
        "threshold_ticks": float(threshold_ticks),
    }


def main():
    """Point d'entrée principal"""

    print("\n" + "="*70)
    print("🔍 ANALYSE DISTRIBUTION DES LABELS - HORIZON 5 MIN")
    print("="*70)

    base_dir = Path("DATA_SIERRA_CHART/DATA_2025/NOVEMBRE")

    results = []

    # ES
    results.append(analyze_symbol(
        "ES",
        [
            base_dir / "20251105/CHART_3/ML_READY",
            base_dir / "20251106/CHART_3/ML_READY"
        ],
        CONFIG['threshold_atr_multiplier_es'],
        CONFIG['tick_size_es']
    ))

    # NQ
    results.append(analyze_symbol(
        "NQ",
        [
            base_dir / "20251105/CHART_9/ML_READY",
            base_dir / "20251106/CHART_9/ML_READY"
        ],
        CONFIG['threshold_atr_multiplier_nq'],
        CONFIG['tick_size_nq']
    ))

    # RTY
    results.append(analyze_symbol(
        "RTY",
        [
            base_dir / "20251105/CHART_1/ML_READY",
            base_dir / "20251106/CHART_1/ML_READY"
        ],
        CONFIG['threshold_atr_multiplier_rty'],
        CONFIG['tick_size_rty']
    ))

    # Résumé comparatif
    print(f"\n{'='*70}")
    print("📊 RÉSUMÉ COMPARATIF")
    print(f"{'='*70}")
    print(f"\n{'Symbole':<10} {'Samples':<10} {'UP %':<10} {'DOWN %':<10} {'Ratio':10} {'Status':<20}")
    print("-"*70)

    for r in results:
        up_pct = r['label_pcts'].get('UP', 0)
        down_pct = r['label_pcts'].get('DOWN', 0)
        ratio = r['imbalance_ratio']

        if ratio > 2.0:
            status = "❌ CRITIQUE"
        elif ratio > 1.5:
            status = "⚠️  MODÉRÉ"
        else:
            status = "✅ OK"

        print(f"{r['symbol']:<10} {r['valid_samples']:<10,} {up_pct:<10.1f} {down_pct:<10.1f} {ratio:<10.2f} {status:<20}")

    # Sauvegarder le rapport
    output_path = Path("ml/label_distribution_analysis.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Rapport sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
