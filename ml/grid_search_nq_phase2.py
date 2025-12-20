#!/usr/bin/env python3
"""
Grid Search Phase 2 - Optimisation ATR pour NQ avec class_weight patch
Teste différents ATR multipliers pour trouver le meilleur compromis volume/qualité
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys
from sklearn.utils.class_weight import compute_class_weight

# Ajouter le répertoire parent au PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train_ml_direction_15min import load_all_data, create_labels
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

# ═══════════════════════════════════════════════════════════════════════════
# GRILLE DE PARAMÈTRES À TESTER POUR NQ
# ═══════════════════════════════════════════════════════════════════════════

GRID_NQ = {
    "horizons": [600],  # Garder 10 min (optimal du Grid Search initial)
    "atr_multipliers": [0.24, 0.28, 0.30, 0.32, 0.36, 0.40],  # Tester autour de 0.36
}

NQ_CONFIG = {
    "data_dirs": [
        Path("DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251105/CHART_9/ML_READY"),
        Path("DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251106/CHART_9/ML_READY"),
    ],
    "tick_size": 0.25,
    "symbol": "NQ"
}

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def quick_train_and_evaluate(df, feature_cols, apply_nq_patch=True):
    """
    Entraîne un modèle rapidement et retourne les métriques

    Args:
        df: DataFrame avec features et labels
        feature_cols: Liste des features à utiliser
        apply_nq_patch: Si True, applique le patch class_weight NQ
    """
    # Préparer X, y
    X = df[feature_cols].values
    y = df['label'].values

    # Split temporel 80/20
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

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

    # ✅ Appliquer patch NQ si demandé
    if apply_nq_patch:
        if 0 in class_weight_dict:  # DOWN
            class_weight_dict[0] = class_weight_dict[0] * 1.25
        if 1 in class_weight_dict:  # UP
            class_weight_dict[1] = class_weight_dict[1] * 0.90

    # Entraîner modèle léger
    model = LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=8,
        num_leaves=31,
        min_child_samples=50,
        subsample=0.8,
        colsample_bytree=0.7,
        objective='binary',
        metric='auc',
        random_state=42,
        class_weight=class_weight_dict,
        verbose=-1
    )

    model.fit(X_train, y_train)

    # Prédictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # Métriques
    accuracy = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred, average='macro')
    recall = recall_score(y_test, y_pred, average='macro')

    # Distribution labels
    label_counts = pd.Series(y_train).value_counts()
    down_count = label_counts.get(0, 0)
    up_count = label_counts.get(1, 0)
    total = len(y_train)

    down_pct = (down_count / total * 100) if total > 0 else 0
    up_pct = (up_count / total * 100) if total > 0 else 0
    balance_ratio = max(down_count, up_count) / min(down_count, up_count) if min(down_count, up_count) > 0 else 999

    # Calculer métriques de trading simulées
    # Filtrer par seuil de confiance
    high_conf_mask = y_proba >= 0.60
    n_trades_60 = high_conf_mask.sum()

    if n_trades_60 > 0:
        y_pred_60 = y_pred[high_conf_mask]
        y_test_60 = y_test[high_conf_mask]
        accuracy_60 = accuracy_score(y_test_60, y_pred_60)
        win_rate_60 = accuracy_60
    else:
        accuracy_60 = 0
        win_rate_60 = 0
        n_trades_60 = 0

    return {
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "auc": auc,
        "precision": precision,
        "recall": recall,
        "n_train": len(y_train),
        "n_test": len(y_test),
        "down_pct": down_pct,
        "up_pct": up_pct,
        "balance_ratio": balance_ratio,
        "trades_at_60": n_trades_60,
        "accuracy_at_60": accuracy_60,
        "win_rate_at_60": win_rate_60
    }


def test_configuration(horizon, atr_mult):
    """
    Teste une configuration spécifique
    """
    print(f"\n{'─'*70}")
    print(f"🧪 TEST NQ | Horizon={horizon}s ({horizon//60}min) | ATR×{atr_mult:.2f}")
    print(f"{'─'*70}")

    try:
        # Charger les données
        df = load_all_data(NQ_CONFIG['data_dirs'], "NQ Grid Search Phase 2")
        print(f"✅ {len(df):,} samples chargés")

        # Créer les labels
        df = create_labels(
            df,
            horizon_seconds=horizon,
            threshold_ticks=None,
            tick_size=NQ_CONFIG['tick_size'],
            time_gap_tolerance=60,
            threshold_mode="atr",
            atr_multiplier=atr_mult,
            binary_mode=True
        )

        # Filtrer les valides
        df_valid = df[df['label'].notna()].copy()
        print(f"✅ {len(df_valid):,} samples avec labels valides ({len(df_valid)/len(df)*100:.1f}%)")

        if len(df_valid) < 1000:
            print(f"⚠️  Pas assez de samples valides: {len(df_valid)}")
            return None

        # Features basiques pour le test rapide
        base_features = [
            'mid', 'spread_ticks', 'atr', 'delta', 'cum_delta_session', 'cum_delta_day',
            'd_vwap_ticks', 'd_vpoc_ticks', 'level1_imbalance', 'depth_imbalance',
            'ob_center', 'vwap', 'd_vwap_atr', 'smart_money_flow', 'vwap_up1', 'vwap_dn1',
            'corr', 'institutional_pressure', 'mia_bullish_score'
        ]

        # Filtrer les features disponibles
        available_features = [f for f in base_features if f in df_valid.columns]
        print(f"📊 {len(available_features)} features utilisées")

        # Entraîner et évaluer (AVEC patch NQ)
        results = quick_train_and_evaluate(df_valid, available_features, apply_nq_patch=True)

        # Afficher les résultats
        print(f"✅ Accuracy: {results['accuracy']:.3f} | F1: {results['f1_macro']:.3f} | AUC: {results['auc']:.3f}")
        print(f"📊 Labels: DOWN={results['down_pct']:.1f}% UP={results['up_pct']:.1f}% (ratio={results['balance_ratio']:.2f}:1)")
        print(f"📈 Samples: {results['n_train']:,} train / {results['n_test']:,} test")
        print(f"💰 Trades @0.60: {results['trades_at_60']:,} (WR={results['win_rate_at_60']:.1%})")

        return {
            "horizon": int(horizon),
            "atr_multiplier": float(atr_mult),
            "accuracy": float(results['accuracy']),
            "f1_macro": float(results['f1_macro']),
            "auc": float(results['auc']),
            "precision": float(results['precision']),
            "recall": float(results['recall']),
            "down_pct": float(results['down_pct']),
            "up_pct": float(results['up_pct']),
            "balance_ratio": float(results['balance_ratio']),
            "n_train": int(results['n_train']),
            "n_test": int(results['n_test']),
            "trades_at_60": int(results['trades_at_60']),
            "win_rate_at_60": float(results['win_rate_at_60']),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Point d'entrée principal"""

    print("\n" + "="*70)
    print("🔍 GRID SEARCH PHASE 2 - OPTIMISATION ATR POUR NQ")
    print("="*70)
    print(f"📊 Symbole: {NQ_CONFIG['symbol']}")
    print(f"📊 Horizon: {GRID_NQ['horizons'][0]}s ({GRID_NQ['horizons'][0]//60} min)")
    print(f"📊 ATR multipliers à tester: {GRID_NQ['atr_multipliers']}")
    print(f"✅ Patch class_weight NQ: ACTIVÉ (DOWN +25%, UP -10%)")
    print(f"📁 Données: {NQ_CONFIG['data_dirs'][0].parent.name} + {NQ_CONFIG['data_dirs'][1].parent.name}")
    print("="*70)

    results = []
    total_configs = len(GRID_NQ['horizons']) * len(GRID_NQ['atr_multipliers'])
    current = 0

    for horizon in GRID_NQ['horizons']:
        for atr_mult in GRID_NQ['atr_multipliers']:
            current += 1
            print(f"\n{'='*70}")
            print(f"📊 Configuration {current}/{total_configs}")
            print(f"{'='*70}")

            result = test_configuration(horizon, atr_mult)

            if result:
                results.append(result)

                # Sauvegarder après chaque test
                output_file = Path("ml/grid_search_nq_phase2_results.json")
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"💾 Résultats sauvegardés: {output_file}")

    # Afficher le résumé final
    print("\n" + "="*70)
    print("📊 RÉSUMÉ FINAL - GRID SEARCH PHASE 2 NQ")
    print("="*70)

    if results:
        df_results = pd.DataFrame(results)

        # Trier par accuracy
        df_sorted = df_results.sort_values('accuracy', ascending=False)

        print("\n🏆 TOP 3 CONFIGURATIONS (par Accuracy):")
        print("─"*70)
        for idx, row in df_sorted.head(3).iterrows():
            print(f"\n{idx+1}. ATR×{row['atr_multiplier']:.2f}")
            print(f"   Accuracy: {row['accuracy']:.3f} | AUC: {row['auc']:.3f} | F1: {row['f1_macro']:.3f}")
            print(f"   Labels: DOWN={row['down_pct']:.1f}% UP={row['up_pct']:.1f}%")
            print(f"   Trades @0.60: {row['trades_at_60']:,} (WR={row['win_rate_at_60']:.1%})")

        # Recommandation finale
        print("\n" + "="*70)
        print("🎯 RECOMMANDATION FINALE")
        print("="*70)

        best = df_sorted.iloc[0]
        print(f"\n✅ Meilleure configuration:")
        print(f"   Horizon: {best['horizon']}s ({best['horizon']//60} min)")
        print(f"   ATR multiplier: {best['atr_multiplier']:.2f}")
        print(f"   Accuracy: {best['accuracy']:.3f}")
        print(f"   AUC: {best['auc']:.3f}")
        print(f"   Trades @0.60: {best['trades_at_60']:,}")
        print(f"   Win Rate @0.60: {best['win_rate_at_60']:.1%}")

        # Sauvegarder résumé
        summary = {
            "best_config": best.to_dict(),
            "all_configs": df_results.to_dict('records'),
            "total_tested": len(results),
            "timestamp": datetime.now().isoformat()
        }

        summary_file = Path("ml/grid_search_nq_phase2_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n💾 Résumé sauvegardé: {summary_file}")

    else:
        print("\n❌ Aucun résultat valide")

    print("\n" + "="*70)
    print("✅ GRID SEARCH PHASE 2 TERMINÉ")
    print("="*70)


if __name__ == "__main__":
    main()
