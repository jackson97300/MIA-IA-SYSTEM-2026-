#!/usr/bin/env python3
"""
ml/train_lightgbm.py

SCRIPT D'ENTRAÎNEMENT LIGHTGBM
Entraîne un modèle LightGBM sur les données labellisées

FONCTIONNALITÉS :
1. Charge les données labellisées (parquet)
2. Split train/validation/test
3. Entraîne LightGBM avec hyperparamètres optimaux
4. Validation et métriques détaillées
5. Feature importance
6. Export modèle production-ready

USAGE :
    python ml/train_lightgbm.py --input DATASET/labeled_data.parquet

PARAMÈTRES :
    --input: Fichier Parquet d'entrée
    --output: Chemin du modèle de sortie (défaut: ml/trained_models/lgb_signal_filter.txt)
    --test-size: Proportion test (défaut: 0.2)
    --val-size: Proportion validation (défaut: 0.2)

Version: 1.0
Date: 30 Octobre 2025
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Vérifier imports
try:
    import lightgbm as lgb
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, classification_report, confusion_matrix
    )
    LIBRARIES_AVAILABLE = True
except ImportError as e:
    print(f"❌ Librairie manquante: {e}")
    print("💡 Installer: pip install lightgbm pandas scikit-learn")
    sys.exit(1)

# === CONFIGURATION ===

# Features à utiliser (même ordre que lightgbm_signal_filter.py)
FEATURE_COLUMNS = [
    # VWAP (8)
    'd_vwap_ticks', 'd_vwap_weekly_ticks', 'd_vwap_monthly_ticks',
    'd_pvwap_ticks', 'd_w_up1_ticks', 'd_w_dn1_ticks',
    'd_vwap_atr', 'is_1tick_spread',

    # Gamma/MenthorQ (8)
    'confluence_strength', 'confluence_proximity',
    'menthorq_impact_score', 'menthorq_proximity_strength',
    'gamma_call_confluence', 'gamma_put_confluence',
    'blind_spot_confluence', 'battle_navale_signal_strength',

    # DOM (6)
    'level1_imbalance', 'depth_imbalance',
    'ob_center_tanh', 'top_heavy',
    'tick_rate_3s', 'tick_momentum',

    # Delta/OrderFlow (5)
    'delta', 'cum_delta_session', 'pressure_strength',
    'smart_money_flow', 'institutional_pressure',

    # Volume Profile (3)
    'd_vpoc_ticks', 'd_vah_ticks', 'd_val_ticks'
]

# Hyperparamètres LightGBM optimaux pour trading
LIGHTGBM_PARAMS = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_data_in_leaf': 50,
    'max_depth': -1,
    'verbose': -1,
    'seed': 42
}

# === FONCTIONS ===

def load_and_prepare_data(
    input_file: str,
    test_size: float = 0.2,
    val_size: float = 0.2
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Charge et prépare les données

    Args:
        input_file: Fichier parquet d'entrée
        test_size: Proportion test
        val_size: Proportion validation (sur le train)

    Returns:
        Tuple (train_df, val_df, test_df)
    """
    print(f"📂 Chargement: {input_file}")
    df = pd.read_parquet(input_file)

    print(f"   ✅ {len(df)} lignes chargées")
    print(f"   ✅ {len(df.columns)} colonnes")

    # Vérifier que toutes les features sont présentes
    missing_features = [f for f in FEATURE_COLUMNS if f not in df.columns]
    if missing_features:
        print(f"⚠️  Features manquantes: {missing_features}")
        print("   (Elles seront ignorées)")
        # Retirer les features manquantes
        global FEATURE_COLUMNS
        FEATURE_COLUMNS = [f for f in FEATURE_COLUMNS if f in df.columns]

    print(f"   ✅ {len(FEATURE_COLUMNS)} features utilisées")

    # Vérifier le label
    if 'signal_profitable' not in df.columns:
        raise ValueError("❌ Colonne 'signal_profitable' manquante dans le dataset")

    # Split train/test
    train_val_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=42,
        stratify=df['signal_profitable']  # Garder les proportions
    )

    # Split train/val
    train_df, val_df = train_test_split(
        train_val_df,
        test_size=val_size,
        random_state=42,
        stratify=train_val_df['signal_profitable']
    )

    print(f"\n📊 Split:")
    print(f"   Train: {len(train_df)} samples")
    print(f"   Val:   {len(val_df)} samples")
    print(f"   Test:  {len(test_df)} samples")

    return train_df, val_df, test_df

def train_lightgbm(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_columns: List[str],
    params: Dict
) -> lgb.Booster:
    """
    Entraîne le modèle LightGBM

    Args:
        train_df: DataFrame train
        val_df: DataFrame validation
        feature_columns: Liste des features
        params: Hyperparamètres LightGBM

    Returns:
        Modèle entraîné
    """
    print("\n🚀 Entraînement LightGBM...")

    # Préparer données
    X_train = train_df[feature_columns].values
    y_train = train_df['signal_profitable'].values

    X_val = val_df[feature_columns].values
    y_val = val_df['signal_profitable'].values

    # Créer datasets LightGBM
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    # Entraîner
    print("   Training en cours...")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[train_data, val_data],
        valid_names=['train', 'val'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=100)
        ]
    )

    print(f"   ✅ Entraînement terminé: {model.num_trees()} arbres")

    return model

def evaluate_model(
    model: lgb.Booster,
    df: pd.DataFrame,
    feature_columns: List[str],
    dataset_name: str = "Test"
) -> Dict:
    """
    Évalue le modèle

    Args:
        model: Modèle LightGBM
        df: DataFrame à évaluer
        feature_columns: Liste des features
        dataset_name: Nom du dataset (pour affichage)

    Returns:
        Dictionnaire avec métriques
    """
    print(f"\n📊 Évaluation sur {dataset_name}...")

    X = df[feature_columns].values
    y_true = df['signal_profitable'].values

    # Prédictions
    y_proba = model.predict(X)
    y_pred = (y_proba >= 0.5).astype(int)

    # Métriques
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, y_proba)

    print(f"   Accuracy:  {accuracy:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   AUC:       {auc:.4f}")

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    print(f"\n   Confusion Matrix:")
    print(f"   TN={cm[0,0]:<6} FP={cm[0,1]:<6}")
    print(f"   FN={cm[1,0]:<6} TP={cm[1,1]:<6}")

    # Win rate simulée (si on suit le modèle)
    if y_pred.sum() > 0:
        model_win_rate = y_true[y_pred == 1].mean()
        print(f"\n   Win Rate (si on suit le modèle): {model_win_rate:.2%}")
        print(f"   Nombre de trades recommandés: {y_pred.sum()} / {len(y_pred)}")

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'auc': auc,
        'confusion_matrix': cm.tolist()
    }

def analyze_feature_importance(
    model: lgb.Booster,
    feature_columns: List[str],
    top_n: int = 10
):
    """
    Analyse l'importance des features

    Args:
        model: Modèle LightGBM
        feature_columns: Liste des features
        top_n: Nombre de top features à afficher
    """
    print(f"\n🔍 Top {top_n} Features les plus importantes:")

    importance = model.feature_importance(importance_type='gain')
    feature_importance = list(zip(feature_columns, importance))
    feature_importance = sorted(feature_importance, key=lambda x: x[1], reverse=True)

    for i, (feature, imp) in enumerate(feature_importance[:top_n], 1):
        print(f"   {i:2d}. {feature:<35} {imp:>10.1f}")

    return feature_importance

def save_model(
    model: lgb.Booster,
    output_path: str,
    feature_columns: List[str],
    metrics: Dict
):
    """
    Sauvegarde le modèle et métadonnées

    Args:
        model: Modèle LightGBM
        output_path: Chemin de sortie
        feature_columns: Liste des features
        metrics: Métriques de performance
    """
    print(f"\n💾 Sauvegarde du modèle...")

    # Créer le dossier
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sauvegarder modèle
    model.save_model(str(output_path))

    # Sauvegarder métadonnées
    metadata = {
        'created_at': pd.Timestamp.now().isoformat(),
        'num_trees': model.num_trees(),
        'feature_columns': feature_columns,
        'num_features': len(feature_columns),
        'metrics': metrics
    }

    metadata_path = output_path.with_suffix('.json')
    import json
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Tailles fichiers
    model_size_kb = output_path.stat().st_size / 1024

    print(f"   ✅ Modèle: {output_path} ({model_size_kb:.1f} KB)")
    print(f"   ✅ Métadonnées: {metadata_path}")

    return output_path

# === MAIN ===

def main(args):
    """Fonction principale"""

    print("\n" + "="*60)
    print("🤖 ENTRAÎNEMENT LIGHTGBM - MIA TRADING SYSTEM")
    print("="*60)

    # 1. Charger données
    print("\n1️⃣  Chargement des données")
    train_df, val_df, test_df = load_and_prepare_data(
        args.input,
        test_size=args.test_size,
        val_size=args.val_size
    )

    # 2. Entraîner
    print("\n2️⃣  Entraînement")
    model = train_lightgbm(
        train_df,
        val_df,
        FEATURE_COLUMNS,
        LIGHTGBM_PARAMS
    )

    # 3. Évaluer
    print("\n3️⃣  Évaluation")

    # Validation
    val_metrics = evaluate_model(model, val_df, FEATURE_COLUMNS, "Validation")

    # Test
    test_metrics = evaluate_model(model, test_df, FEATURE_COLUMNS, "Test")

    # 4. Feature importance
    print("\n4️⃣  Feature Importance")
    feature_importance = analyze_feature_importance(model, FEATURE_COLUMNS, top_n=15)

    # 5. Sauvegarder
    print("\n5️⃣  Sauvegarde")
    output_path = save_model(
        model,
        args.output,
        FEATURE_COLUMNS,
        test_metrics
    )

    # 6. Résumé final
    print("\n" + "="*60)
    print("✅ ENTRAÎNEMENT TERMINÉ")
    print("="*60)
    print(f"\n📊 Performance (Test Set):")
    print(f"   AUC:       {test_metrics['auc']:.4f}")
    print(f"   Accuracy:  {test_metrics['accuracy']:.4f}")
    print(f"   Precision: {test_metrics['precision']:.4f}")
    print(f"   Recall:    {test_metrics['recall']:.4f}")
    print(f"\n📁 Modèle sauvegardé:")
    print(f"   {output_path}")
    print(f"\n🚀 Intégration dans le lanceur:")
    print(f"   Le modèle est prêt à être utilisé automatiquement !")
    print(f"   Il sera chargé par ml/lightgbm_signal_filter.py")

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Entraîne un modèle LightGBM pour filtrer les signaux"
    )

    parser.add_argument(
        '--input',
        type=str,
        default='DATASET/labeled_data.parquet',
        help='Fichier Parquet d\'entrée (données labellisées)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='ml/trained_models/lgb_signal_filter.txt',
        help='Chemin du modèle de sortie'
    )

    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Proportion test (défaut: 0.2)'
    )

    parser.add_argument(
        '--val-size',
        type=float,
        default=0.2,
        help='Proportion validation sur train (défaut: 0.2)'
    )

    args = parser.parse_args()

    sys.exit(main(args))
