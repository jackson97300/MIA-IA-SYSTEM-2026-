"""
🔍 AUDIT COMPLET ET PROFOND DU SYSTÈME ML
Analyse exhaustive de toute la pipeline pour identifier les problèmes critiques.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from collections import Counter
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def audit_data_quality():
    """Analyse qualité des données labeled."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #1: QUALITÉ DES DONNÉES")
    logger.info("="*80)

    df = pd.read_parquet("ml/data/labeled_trades.parquet")

    # 1. Distribution target
    logger.info(f"\n📊 DISTRIBUTION TARGET 'win':")
    win_dist = df['win'].value_counts()
    logger.info(f"   LOSS (0): {win_dist[0]:,} ({win_dist[0]/len(df)*100:.2f}%)")
    logger.info(f"   WIN (1):  {win_dist[1]:,} ({win_dist[1]/len(df)*100:.2f}%)")
    logger.info(f"   RATIO WIN/LOSS: {win_dist[1]/win_dist[0]:.3f}")

    if win_dist[0] / len(df) > 0.55:
        logger.warning(f"   ⚠️ CLASSE MAJORITAIRE TROP DOMINANTE (>55%)")

    # 2. Distribution P&L
    logger.info(f"\n💰 DISTRIBUTION P&L (ticks):")
    logger.info(f"   Moyenne: {df['pnl_ticks'].mean():+.2f}")
    logger.info(f"   Médiane: {df['pnl_ticks'].median():+.2f}")
    logger.info(f"   Min: {df['pnl_ticks'].min():+.2f}")
    logger.info(f"   Max: {df['pnl_ticks'].max():+.2f}")
    logger.info(f"   Écart-type: {df['pnl_ticks'].std():.2f}")

    wins = df[df['win'] == 1]
    losses = df[df['win'] == 0]
    logger.info(f"\n   P&L moyen WINs:  {wins['pnl_ticks'].mean():+.2f} ticks")
    logger.info(f"   P&L moyen LOSSes: {losses['pnl_ticks'].mean():+.2f} ticks")

    # 3. Durées trades
    logger.info(f"\n⏱️ DURÉES TRADES (minutes):")
    logger.info(f"   Moyenne: {df['duration_minutes'].mean():.1f} min")
    logger.info(f"   Médiane: {df['duration_minutes'].median():.1f} min")
    logger.info(f"   Min: {df['duration_minutes'].min():.1f} min")
    logger.info(f"   Max: {df['duration_minutes'].max():.1f} min")

    # 4. MAE/MFE
    logger.info(f"\n📉 MAE (Maximum Adverse Excursion):")
    logger.info(f"   Moyenne: {df['mae'].mean():.2f} ticks")
    logger.info(f"   Médiane: {df['mae'].median():.2f} ticks")

    logger.info(f"\n📈 MFE (Maximum Favorable Excursion):")
    logger.info(f"   Moyenne: {df['mfe'].mean():.2f} ticks")
    logger.info(f"   Médiane: {df['mfe'].median():.2f} ticks")

    # 5. Valeurs manquantes
    logger.info(f"\n🕳️ VALEURS MANQUANTES:")
    missing = df.isnull().sum()
    missing_features = missing[missing > 0]
    if len(missing_features) > 0:
        for feat, count in missing_features.items():
            logger.warning(f"   ⚠️ {feat}: {count:,} ({count/len(df)*100:.2f}%)")
    else:
        logger.info(f"   ✅ Aucune valeur manquante")

    # 6. Features constantes
    logger.info(f"\n🔒 FEATURES CONSTANTES (variance nulle):")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    constant_features = []
    for col in numeric_cols:
        if df[col].nunique() == 1:
            constant_features.append(col)

    if constant_features:
        for feat in constant_features:
            logger.warning(f"   ⚠️ {feat}: constante (valeur unique: {df[feat].iloc[0]})")
    else:
        logger.info(f"   ✅ Aucune feature constante")

    # 7. Corrélation target vs top features
    logger.info(f"\n🔗 CORRÉLATION TARGET vs TOP 10 FEATURES:")
    correlations = df[numeric_cols].corrwith(df['win']).abs().sort_values(ascending=False)
    for i, (feat, corr) in enumerate(correlations.head(10).items(), 1):
        if feat != 'win':
            symbol = "✅" if corr > 0.1 else "⚠️" if corr > 0.05 else "❌"
            logger.info(f"   {i:2d}. {feat:40s} {corr:.4f} {symbol}")

    if correlations.iloc[1] < 0.05:  # Meilleure feature après 'win'
        logger.error(f"   ❌ CRITIQUE: Meilleure feature a corrélation < 0.05 !")

    return df


def audit_feature_distributions(df):
    """Analyse distributions des features clés."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #2: DISTRIBUTION DES FEATURES CLÉS")
    logger.info("="*80)

    # Features MenthorQ
    logger.info(f"\n📊 FEATURES MENTHORQ:")
    menthorq_features = [c for c in df.columns if any(x in c.lower() for x in ['gex', 'call', 'put', 'hvl', 'blind', 'gamma'])]

    for feat in menthorq_features[:10]:  # Top 10
        logger.info(f"\n   {feat}:")
        logger.info(f"      Min:    {df[feat].min():.2f}")
        logger.info(f"      Médiane: {df[feat].median():.2f}")
        logger.info(f"      Max:    {df[feat].max():.2f}")
        logger.info(f"      Std:    {df[feat].std():.2f}")
        logger.info(f"      Unique: {df[feat].nunique()}")

        # Check si variance suffisante
        if df[feat].std() < 0.01:
            logger.warning(f"      ⚠️ Variance très faible (<0.01)")

    # Features Delta
    logger.info(f"\n📊 FEATURES DELTA:")
    delta_features = [c for c in df.columns if 'delta' in c.lower()]
    for feat in delta_features[:5]:
        logger.info(f"\n   {feat}:")
        logger.info(f"      Min:    {df[feat].min():.2f}")
        logger.info(f"      Médiane: {df[feat].median():.2f}")
        logger.info(f"      Max:    {df[feat].max():.2f}")
        logger.info(f"      Std:    {df[feat].std():.2f}")

    # Nouvelles interactions GEX
    logger.info(f"\n📊 NOUVELLES INTERACTIONS GEX:")
    gex_interactions = [
        'gex_delta_momentum', 'gex_volume_intensity', 'gex_vwap_context',
        'gex_volatility_adjusted', 'call_delta_pressure', 'put_delta_pressure',
        'hvl_delta_regime', 'blind_institutional_trap', 'gex_wall_confluence',
        'options_directional_pressure'
    ]

    for feat in gex_interactions:
        if feat in df.columns:
            logger.info(f"\n   {feat}:")
            logger.info(f"      Min:    {df[feat].min():.2f}")
            logger.info(f"      Médiane: {df[feat].median():.2f}")
            logger.info(f"      Max:    {df[feat].max():.2f}")
            logger.info(f"      Std:    {df[feat].std():.2f}")
            logger.info(f"      Non-zero: {(df[feat] != 0).sum()} ({(df[feat] != 0).sum()/len(df)*100:.1f}%)")

            if (df[feat] != 0).sum() < len(df) * 0.01:
                logger.error(f"      ❌ CRITIQUE: Feature presque toujours nulle (<1%)")


def audit_model_performance():
    """Analyse performance du modèle."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #3: PERFORMANCE MODÈLE")
    logger.info("="*80)

    # Charger metadata
    metadata_path = Path("ml/models/lightgbm_quality_v1_metadata.json")
    if not metadata_path.exists():
        logger.error("   ❌ Fichier metadata introuvable !")
        return

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    logger.info(f"\n📋 METADATA MODÈLE:")
    logger.info(f"   Type: {metadata.get('model_type', 'N/A')}")
    logger.info(f"   Target: {metadata.get('target', 'N/A')}")
    logger.info(f"   Features: {metadata.get('n_features', 'N/A')}")
    logger.info(f"   Scaler: {metadata.get('has_scaler', 'N/A')}")

    logger.info(f"\n⚙️ HYPERPARAMÈTRES:")
    params = metadata.get('best_params', {})
    for key, value in params.items():
        logger.info(f"   {key}: {value}")

    # Analyser learning_rate
    lr = params.get('learning_rate', 0)
    if lr < 0.01:
        logger.warning(f"   ⚠️ Learning rate très faible ({lr:.4f}) → training lent")
    elif lr > 0.2:
        logger.warning(f"   ⚠️ Learning rate élevé ({lr:.4f}) → risque overfitting")

    # Analyser n_estimators
    n_est = params.get('n_estimators', 0)
    if n_est < 100:
        logger.warning(f"   ⚠️ Peu d'estimateurs ({n_est}) → modèle simple")
    elif n_est > 400:
        logger.info(f"   ✅ Beaucoup d'estimateurs ({n_est}) → modèle complexe")


def audit_feature_importance():
    """Analyse importance des features via SHAP."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #4: IMPORTANCE DES FEATURES")
    logger.info("="*80)

    import pickle

    # Charger modèle
    model_path = Path("ml/models/lightgbm_quality_v1.pkl")
    if not model_path.exists():
        logger.error("   ❌ Modèle introuvable !")
        return

    with open(model_path, 'rb') as f:
        saved = pickle.load(f)

    model = saved['model']
    feature_names = saved['feature_names']

    # Feature importance LightGBM native
    logger.info(f"\n📊 TOP 20 FEATURES (LightGBM importance):")
    importance = model.feature_importances_
    feature_importance = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

    total_importance = sum(importance)
    cumulative = 0

    for i, (feat, imp) in enumerate(feature_importance[:20], 1):
        cumulative += imp
        pct = (imp / total_importance) * 100
        cum_pct = (cumulative / total_importance) * 100

        symbol = "🔥" if pct > 5 else "✅" if pct > 2 else "⚠️" if pct > 1 else "❌"
        logger.info(f"   {i:2d}. {feat:40s} {imp:8.1f} ({pct:5.2f}%) cumul: {cum_pct:5.1f}% {symbol}")

    # Analyser si top features sont GEX
    top_10_features = [f[0] for f in feature_importance[:10]]
    gex_in_top10 = [f for f in top_10_features if any(x in f.lower() for x in ['gex', 'call', 'put', 'hvl', 'blind', 'gamma'])]

    logger.info(f"\n🎯 FEATURES GEX/MENTHORQ dans TOP 10: {len(gex_in_top10)}/10")
    if len(gex_in_top10) > 0:
        for feat in gex_in_top10:
            logger.info(f"   ✅ {feat}")
    else:
        logger.warning(f"   ⚠️ AUCUNE feature GEX dans top 10 !")

    # Analyser cumulative importance
    logger.info(f"\n📈 IMPORTANCE CUMULATIVE:")
    logger.info(f"   Top 10 features: {(cumulative / total_importance * 100):.1f}%")

    cumul_20 = sum([imp for _, imp in feature_importance[:20]])
    logger.info(f"   Top 20 features: {(cumul_20 / total_importance * 100):.1f}%")

    cumul_50 = sum([imp for _, imp in feature_importance[:50]])
    logger.info(f"   Top 50 features: {(cumul_50 / total_importance * 100):.1f}%")

    if (cumulative / total_importance) > 0.7:
        logger.warning(f"   ⚠️ Top 10 features dominent (>70%) → autres features inutiles ?")


def audit_class_separation():
    """Analyse séparation entre WINs et LOSSes."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #5: SÉPARATION DES CLASSES")
    logger.info("="*80)

    df = pd.read_parquet("ml/data/labeled_trades.parquet")

    wins = df[df['win'] == 1]
    losses = df[df['win'] == 0]

    # Top features avec meilleure séparation
    logger.info(f"\n📊 TOP 10 FEATURES AVEC MEILLEURE SÉPARATION WIN/LOSS:")

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    numeric_cols = [c for c in numeric_cols if c not in ['win', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes']]

    separations = []
    for col in numeric_cols:
        win_mean = wins[col].mean()
        loss_mean = losses[col].mean()
        win_std = wins[col].std()
        loss_std = losses[col].std()

        # Cohen's d (effect size)
        pooled_std = np.sqrt((win_std**2 + loss_std**2) / 2)
        if pooled_std > 0:
            cohens_d = abs(win_mean - loss_mean) / pooled_std
            separations.append((col, cohens_d, win_mean, loss_mean))

    separations.sort(key=lambda x: x[1], reverse=True)

    for i, (feat, d, win_m, loss_m) in enumerate(separations[:10], 1):
        symbol = "🔥" if d > 0.5 else "✅" if d > 0.3 else "⚠️" if d > 0.1 else "❌"
        logger.info(f"   {i:2d}. {feat:40s} Cohen's d={d:.3f} {symbol}")
        logger.info(f"       WIN mean: {win_m:8.2f}  |  LOSS mean: {loss_m:8.2f}")

    if separations[0][1] < 0.2:
        logger.error(f"   ❌ CRITIQUE: Meilleure séparation < 0.2 (très faible) !")


def audit_prediction_analysis():
    """Analyse détaillée des prédictions du modèle."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #6: ANALYSE DES PRÉDICTIONS")
    logger.info("="*80)

    import pickle
    from sklearn.preprocessing import StandardScaler

    # Charger données
    df = pd.read_parquet("ml/data/labeled_trades.parquet")

    # Charger modèle et scaler
    with open("ml/models/lightgbm_quality_v1.pkl", 'rb') as f:
        saved = pickle.load(f)

    model = saved['model']
    scaler = saved.get('scaler')
    feature_names = saved['feature_names']

    # Préparer features
    exclude_cols = [
        'win', 'pnl_ticks', 'duration_minutes', 'mae', 'mfe',
        'outcome', 'quality_score', 'entry_time', 'exit_time',
        'symbol', 'action', 'entry_price', 'sl_price', 'tp1_price', 'tp2_price'
    ]

    X = df[[c for c in df.columns if c in feature_names and c not in exclude_cols]]
    y = df['win']

    # Scaler
    if scaler:
        X_scaled = pd.DataFrame(scaler.transform(X), columns=X.columns)
    else:
        X_scaled = X

    # Prédictions
    y_pred = model.predict(X_scaled)
    y_pred_proba = model.predict_proba(X_scaled)[:, 1]

    logger.info(f"\n📊 DISTRIBUTION PROBABILITÉS:")
    logger.info(f"   Min:  {y_pred_proba.min():.4f}")
    logger.info(f"   Q25:  {np.percentile(y_pred_proba, 25):.4f}")
    logger.info(f"   Q50:  {np.percentile(y_pred_proba, 50):.4f}")
    logger.info(f"   Q75:  {np.percentile(y_pred_proba, 75):.4f}")
    logger.info(f"   Max:  {y_pred_proba.max():.4f}")
    logger.info(f"   Mean: {y_pred_proba.mean():.4f}")

    # Analyser seuils
    logger.info(f"\n🎯 ANALYSE SEUILS DE DÉCISION:")
    for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]:
        y_pred_thresh = (y_pred_proba >= threshold).astype(int)

        tp = ((y_pred_thresh == 1) & (y == 1)).sum()
        fp = ((y_pred_thresh == 1) & (y == 0)).sum()
        tn = ((y_pred_thresh == 0) & (y == 0)).sum()
        fn = ((y_pred_thresh == 0) & (y == 1)).sum()

        accuracy = (tp + tn) / len(y)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        pred_wins = y_pred_thresh.sum()

        symbol = "🔥" if accuracy > 0.60 else "✅" if accuracy > 0.55 else "⚠️"
        logger.info(f"\n   Seuil {threshold:.2f}: {symbol}")
        logger.info(f"      Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        logger.info(f"      Precision: {precision:.4f}")
        logger.info(f"      Recall:    {recall:.4f}")
        logger.info(f"      F1-Score:  {f1:.4f}")
        logger.info(f"      Pred WINs: {pred_wins:,} ({pred_wins/len(y)*100:.1f}%)")

    # Trouver seuil optimal
    best_f1 = 0
    best_threshold = 0.5
    for threshold in np.arange(0.1, 0.9, 0.01):
        y_pred_thresh = (y_pred_proba >= threshold).astype(int)
        tp = ((y_pred_thresh == 1) & (y == 1)).sum()
        fp = ((y_pred_thresh == 1) & (y == 0)).sum()
        fn = ((y_pred_thresh == 0) & (y == 1)).sum()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    logger.info(f"\n🎯 SEUIL OPTIMAL (F1): {best_threshold:.3f} (F1={best_f1:.4f})")


def generate_recommendations():
    """Génère recommandations basées sur l'audit."""

    logger.info("\n" + "="*80)
    logger.info("💡 RECOMMANDATIONS PRIORITAIRES")
    logger.info("="*80)

    recommendations = []

    # TODO: Ajouter logique de recommandations basée sur les résultats d'audit

    logger.info(f"\n🔥 CRITIQUES (à faire immédiatement):")
    logger.info(f"   1. Ajuster seuil de décision à 0.35-0.40 (voir audit #6)")
    logger.info(f"   2. Ajouter class_weight='balanced' dans LightGBM")
    logger.info(f"   3. Augmenter dataset à 5-10 dates minimum")

    logger.info(f"\n⚠️ IMPORTANTES (à faire rapidement):")
    logger.info(f"   4. Feature selection: garder top 30-40 features seulement")
    logger.info(f"   5. Analyser trades perdants pour comprendre patterns")
    logger.info(f"   6. Vérifier si GEX levels sont pertinents pour scalping rapide")

    logger.info(f"\n✅ AMÉLIORATIONS (optionnel):")
    logger.info(f"   7. Tester XGBoost ou CatBoost comme alternative")
    logger.info(f"   8. Ajouter features temporelles (heure de journée, etc.)")
    logger.info(f"   9. Stratified K-Fold cross-validation")


if __name__ == "__main__":
    logger.info("\n" + "🔍"*40)
    logger.info("🔍 AUDIT COMPLET ET PROFOND - ML 3-LAYER STRATEGY")
    logger.info("🔍"*40)

    try:
        # Audit #1: Qualité données
        df = audit_data_quality()

        # Audit #2: Distribution features
        audit_feature_distributions(df)

        # Audit #3: Performance modèle
        audit_model_performance()

        # Audit #4: Importance features
        audit_feature_importance()

        # Audit #5: Séparation classes
        audit_class_separation()

        # Audit #6: Analyse prédictions
        audit_prediction_analysis()

        # Recommandations
        generate_recommendations()

        logger.info("\n" + "="*80)
        logger.info("✅ AUDIT TERMINÉ AVEC SUCCÈS")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\n❌ ERREUR DURANT L'AUDIT: {e}")
        import traceback
        traceback.print_exc()



Analyse exhaustive de toute la pipeline pour identifier les problèmes critiques.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from collections import Counter
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def audit_data_quality():
    """Analyse qualité des données labeled."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #1: QUALITÉ DES DONNÉES")
    logger.info("="*80)

    df = pd.read_parquet("ml/data/labeled_trades.parquet")

    # 1. Distribution target
    logger.info(f"\n📊 DISTRIBUTION TARGET 'win':")
    win_dist = df['win'].value_counts()
    logger.info(f"   LOSS (0): {win_dist[0]:,} ({win_dist[0]/len(df)*100:.2f}%)")
    logger.info(f"   WIN (1):  {win_dist[1]:,} ({win_dist[1]/len(df)*100:.2f}%)")
    logger.info(f"   RATIO WIN/LOSS: {win_dist[1]/win_dist[0]:.3f}")

    if win_dist[0] / len(df) > 0.55:
        logger.warning(f"   ⚠️ CLASSE MAJORITAIRE TROP DOMINANTE (>55%)")

    # 2. Distribution P&L
    logger.info(f"\n💰 DISTRIBUTION P&L (ticks):")
    logger.info(f"   Moyenne: {df['pnl_ticks'].mean():+.2f}")
    logger.info(f"   Médiane: {df['pnl_ticks'].median():+.2f}")
    logger.info(f"   Min: {df['pnl_ticks'].min():+.2f}")
    logger.info(f"   Max: {df['pnl_ticks'].max():+.2f}")
    logger.info(f"   Écart-type: {df['pnl_ticks'].std():.2f}")

    wins = df[df['win'] == 1]
    losses = df[df['win'] == 0]
    logger.info(f"\n   P&L moyen WINs:  {wins['pnl_ticks'].mean():+.2f} ticks")
    logger.info(f"   P&L moyen LOSSes: {losses['pnl_ticks'].mean():+.2f} ticks")

    # 3. Durées trades
    logger.info(f"\n⏱️ DURÉES TRADES (minutes):")
    logger.info(f"   Moyenne: {df['duration_minutes'].mean():.1f} min")
    logger.info(f"   Médiane: {df['duration_minutes'].median():.1f} min")
    logger.info(f"   Min: {df['duration_minutes'].min():.1f} min")
    logger.info(f"   Max: {df['duration_minutes'].max():.1f} min")

    # 4. MAE/MFE
    logger.info(f"\n📉 MAE (Maximum Adverse Excursion):")
    logger.info(f"   Moyenne: {df['mae'].mean():.2f} ticks")
    logger.info(f"   Médiane: {df['mae'].median():.2f} ticks")

    logger.info(f"\n📈 MFE (Maximum Favorable Excursion):")
    logger.info(f"   Moyenne: {df['mfe'].mean():.2f} ticks")
    logger.info(f"   Médiane: {df['mfe'].median():.2f} ticks")

    # 5. Valeurs manquantes
    logger.info(f"\n🕳️ VALEURS MANQUANTES:")
    missing = df.isnull().sum()
    missing_features = missing[missing > 0]
    if len(missing_features) > 0:
        for feat, count in missing_features.items():
            logger.warning(f"   ⚠️ {feat}: {count:,} ({count/len(df)*100:.2f}%)")
    else:
        logger.info(f"   ✅ Aucune valeur manquante")

    # 6. Features constantes
    logger.info(f"\n🔒 FEATURES CONSTANTES (variance nulle):")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    constant_features = []
    for col in numeric_cols:
        if df[col].nunique() == 1:
            constant_features.append(col)

    if constant_features:
        for feat in constant_features:
            logger.warning(f"   ⚠️ {feat}: constante (valeur unique: {df[feat].iloc[0]})")
    else:
        logger.info(f"   ✅ Aucune feature constante")

    # 7. Corrélation target vs top features
    logger.info(f"\n🔗 CORRÉLATION TARGET vs TOP 10 FEATURES:")
    correlations = df[numeric_cols].corrwith(df['win']).abs().sort_values(ascending=False)
    for i, (feat, corr) in enumerate(correlations.head(10).items(), 1):
        if feat != 'win':
            symbol = "✅" if corr > 0.1 else "⚠️" if corr > 0.05 else "❌"
            logger.info(f"   {i:2d}. {feat:40s} {corr:.4f} {symbol}")

    if correlations.iloc[1] < 0.05:  # Meilleure feature après 'win'
        logger.error(f"   ❌ CRITIQUE: Meilleure feature a corrélation < 0.05 !")

    return df


def audit_feature_distributions(df):
    """Analyse distributions des features clés."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #2: DISTRIBUTION DES FEATURES CLÉS")
    logger.info("="*80)

    # Features MenthorQ
    logger.info(f"\n📊 FEATURES MENTHORQ:")
    menthorq_features = [c for c in df.columns if any(x in c.lower() for x in ['gex', 'call', 'put', 'hvl', 'blind', 'gamma'])]

    for feat in menthorq_features[:10]:  # Top 10
        logger.info(f"\n   {feat}:")
        logger.info(f"      Min:    {df[feat].min():.2f}")
        logger.info(f"      Médiane: {df[feat].median():.2f}")
        logger.info(f"      Max:    {df[feat].max():.2f}")
        logger.info(f"      Std:    {df[feat].std():.2f}")
        logger.info(f"      Unique: {df[feat].nunique()}")

        # Check si variance suffisante
        if df[feat].std() < 0.01:
            logger.warning(f"      ⚠️ Variance très faible (<0.01)")

    # Features Delta
    logger.info(f"\n📊 FEATURES DELTA:")
    delta_features = [c for c in df.columns if 'delta' in c.lower()]
    for feat in delta_features[:5]:
        logger.info(f"\n   {feat}:")
        logger.info(f"      Min:    {df[feat].min():.2f}")
        logger.info(f"      Médiane: {df[feat].median():.2f}")
        logger.info(f"      Max:    {df[feat].max():.2f}")
        logger.info(f"      Std:    {df[feat].std():.2f}")

    # Nouvelles interactions GEX
    logger.info(f"\n📊 NOUVELLES INTERACTIONS GEX:")
    gex_interactions = [
        'gex_delta_momentum', 'gex_volume_intensity', 'gex_vwap_context',
        'gex_volatility_adjusted', 'call_delta_pressure', 'put_delta_pressure',
        'hvl_delta_regime', 'blind_institutional_trap', 'gex_wall_confluence',
        'options_directional_pressure'
    ]

    for feat in gex_interactions:
        if feat in df.columns:
            logger.info(f"\n   {feat}:")
            logger.info(f"      Min:    {df[feat].min():.2f}")
            logger.info(f"      Médiane: {df[feat].median():.2f}")
            logger.info(f"      Max:    {df[feat].max():.2f}")
            logger.info(f"      Std:    {df[feat].std():.2f}")
            logger.info(f"      Non-zero: {(df[feat] != 0).sum()} ({(df[feat] != 0).sum()/len(df)*100:.1f}%)")

            if (df[feat] != 0).sum() < len(df) * 0.01:
                logger.error(f"      ❌ CRITIQUE: Feature presque toujours nulle (<1%)")


def audit_model_performance():
    """Analyse performance du modèle."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #3: PERFORMANCE MODÈLE")
    logger.info("="*80)

    # Charger metadata
    metadata_path = Path("ml/models/lightgbm_quality_v1_metadata.json")
    if not metadata_path.exists():
        logger.error("   ❌ Fichier metadata introuvable !")
        return

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    logger.info(f"\n📋 METADATA MODÈLE:")
    logger.info(f"   Type: {metadata.get('model_type', 'N/A')}")
    logger.info(f"   Target: {metadata.get('target', 'N/A')}")
    logger.info(f"   Features: {metadata.get('n_features', 'N/A')}")
    logger.info(f"   Scaler: {metadata.get('has_scaler', 'N/A')}")

    logger.info(f"\n⚙️ HYPERPARAMÈTRES:")
    params = metadata.get('best_params', {})
    for key, value in params.items():
        logger.info(f"   {key}: {value}")

    # Analyser learning_rate
    lr = params.get('learning_rate', 0)
    if lr < 0.01:
        logger.warning(f"   ⚠️ Learning rate très faible ({lr:.4f}) → training lent")
    elif lr > 0.2:
        logger.warning(f"   ⚠️ Learning rate élevé ({lr:.4f}) → risque overfitting")

    # Analyser n_estimators
    n_est = params.get('n_estimators', 0)
    if n_est < 100:
        logger.warning(f"   ⚠️ Peu d'estimateurs ({n_est}) → modèle simple")
    elif n_est > 400:
        logger.info(f"   ✅ Beaucoup d'estimateurs ({n_est}) → modèle complexe")


def audit_feature_importance():
    """Analyse importance des features via SHAP."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #4: IMPORTANCE DES FEATURES")
    logger.info("="*80)

    import pickle

    # Charger modèle
    model_path = Path("ml/models/lightgbm_quality_v1.pkl")
    if not model_path.exists():
        logger.error("   ❌ Modèle introuvable !")
        return

    with open(model_path, 'rb') as f:
        saved = pickle.load(f)

    model = saved['model']
    feature_names = saved['feature_names']

    # Feature importance LightGBM native
    logger.info(f"\n📊 TOP 20 FEATURES (LightGBM importance):")
    importance = model.feature_importances_
    feature_importance = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

    total_importance = sum(importance)
    cumulative = 0

    for i, (feat, imp) in enumerate(feature_importance[:20], 1):
        cumulative += imp
        pct = (imp / total_importance) * 100
        cum_pct = (cumulative / total_importance) * 100

        symbol = "🔥" if pct > 5 else "✅" if pct > 2 else "⚠️" if pct > 1 else "❌"
        logger.info(f"   {i:2d}. {feat:40s} {imp:8.1f} ({pct:5.2f}%) cumul: {cum_pct:5.1f}% {symbol}")

    # Analyser si top features sont GEX
    top_10_features = [f[0] for f in feature_importance[:10]]
    gex_in_top10 = [f for f in top_10_features if any(x in f.lower() for x in ['gex', 'call', 'put', 'hvl', 'blind', 'gamma'])]

    logger.info(f"\n🎯 FEATURES GEX/MENTHORQ dans TOP 10: {len(gex_in_top10)}/10")
    if len(gex_in_top10) > 0:
        for feat in gex_in_top10:
            logger.info(f"   ✅ {feat}")
    else:
        logger.warning(f"   ⚠️ AUCUNE feature GEX dans top 10 !")

    # Analyser cumulative importance
    logger.info(f"\n📈 IMPORTANCE CUMULATIVE:")
    logger.info(f"   Top 10 features: {(cumulative / total_importance * 100):.1f}%")

    cumul_20 = sum([imp for _, imp in feature_importance[:20]])
    logger.info(f"   Top 20 features: {(cumul_20 / total_importance * 100):.1f}%")

    cumul_50 = sum([imp for _, imp in feature_importance[:50]])
    logger.info(f"   Top 50 features: {(cumul_50 / total_importance * 100):.1f}%")

    if (cumulative / total_importance) > 0.7:
        logger.warning(f"   ⚠️ Top 10 features dominent (>70%) → autres features inutiles ?")


def audit_class_separation():
    """Analyse séparation entre WINs et LOSSes."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #5: SÉPARATION DES CLASSES")
    logger.info("="*80)

    df = pd.read_parquet("ml/data/labeled_trades.parquet")

    wins = df[df['win'] == 1]
    losses = df[df['win'] == 0]

    # Top features avec meilleure séparation
    logger.info(f"\n📊 TOP 10 FEATURES AVEC MEILLEURE SÉPARATION WIN/LOSS:")

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    numeric_cols = [c for c in numeric_cols if c not in ['win', 'pnl_ticks', 'mae', 'mfe', 'duration_minutes']]

    separations = []
    for col in numeric_cols:
        win_mean = wins[col].mean()
        loss_mean = losses[col].mean()
        win_std = wins[col].std()
        loss_std = losses[col].std()

        # Cohen's d (effect size)
        pooled_std = np.sqrt((win_std**2 + loss_std**2) / 2)
        if pooled_std > 0:
            cohens_d = abs(win_mean - loss_mean) / pooled_std
            separations.append((col, cohens_d, win_mean, loss_mean))

    separations.sort(key=lambda x: x[1], reverse=True)

    for i, (feat, d, win_m, loss_m) in enumerate(separations[:10], 1):
        symbol = "🔥" if d > 0.5 else "✅" if d > 0.3 else "⚠️" if d > 0.1 else "❌"
        logger.info(f"   {i:2d}. {feat:40s} Cohen's d={d:.3f} {symbol}")
        logger.info(f"       WIN mean: {win_m:8.2f}  |  LOSS mean: {loss_m:8.2f}")

    if separations[0][1] < 0.2:
        logger.error(f"   ❌ CRITIQUE: Meilleure séparation < 0.2 (très faible) !")


def audit_prediction_analysis():
    """Analyse détaillée des prédictions du modèle."""

    logger.info("\n" + "="*80)
    logger.info("🔍 AUDIT #6: ANALYSE DES PRÉDICTIONS")
    logger.info("="*80)

    import pickle
    from sklearn.preprocessing import StandardScaler

    # Charger données
    df = pd.read_parquet("ml/data/labeled_trades.parquet")

    # Charger modèle et scaler
    with open("ml/models/lightgbm_quality_v1.pkl", 'rb') as f:
        saved = pickle.load(f)

    model = saved['model']
    scaler = saved.get('scaler')
    feature_names = saved['feature_names']

    # Préparer features
    exclude_cols = [
        'win', 'pnl_ticks', 'duration_minutes', 'mae', 'mfe',
        'outcome', 'quality_score', 'entry_time', 'exit_time',
        'symbol', 'action', 'entry_price', 'sl_price', 'tp1_price', 'tp2_price'
    ]

    X = df[[c for c in df.columns if c in feature_names and c not in exclude_cols]]
    y = df['win']

    # Scaler
    if scaler:
        X_scaled = pd.DataFrame(scaler.transform(X), columns=X.columns)
    else:
        X_scaled = X

    # Prédictions
    y_pred = model.predict(X_scaled)
    y_pred_proba = model.predict_proba(X_scaled)[:, 1]

    logger.info(f"\n📊 DISTRIBUTION PROBABILITÉS:")
    logger.info(f"   Min:  {y_pred_proba.min():.4f}")
    logger.info(f"   Q25:  {np.percentile(y_pred_proba, 25):.4f}")
    logger.info(f"   Q50:  {np.percentile(y_pred_proba, 50):.4f}")
    logger.info(f"   Q75:  {np.percentile(y_pred_proba, 75):.4f}")
    logger.info(f"   Max:  {y_pred_proba.max():.4f}")
    logger.info(f"   Mean: {y_pred_proba.mean():.4f}")

    # Analyser seuils
    logger.info(f"\n🎯 ANALYSE SEUILS DE DÉCISION:")
    for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]:
        y_pred_thresh = (y_pred_proba >= threshold).astype(int)

        tp = ((y_pred_thresh == 1) & (y == 1)).sum()
        fp = ((y_pred_thresh == 1) & (y == 0)).sum()
        tn = ((y_pred_thresh == 0) & (y == 0)).sum()
        fn = ((y_pred_thresh == 0) & (y == 1)).sum()

        accuracy = (tp + tn) / len(y)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        pred_wins = y_pred_thresh.sum()

        symbol = "🔥" if accuracy > 0.60 else "✅" if accuracy > 0.55 else "⚠️"
        logger.info(f"\n   Seuil {threshold:.2f}: {symbol}")
        logger.info(f"      Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        logger.info(f"      Precision: {precision:.4f}")
        logger.info(f"      Recall:    {recall:.4f}")
        logger.info(f"      F1-Score:  {f1:.4f}")
        logger.info(f"      Pred WINs: {pred_wins:,} ({pred_wins/len(y)*100:.1f}%)")

    # Trouver seuil optimal
    best_f1 = 0
    best_threshold = 0.5
    for threshold in np.arange(0.1, 0.9, 0.01):
        y_pred_thresh = (y_pred_proba >= threshold).astype(int)
        tp = ((y_pred_thresh == 1) & (y == 1)).sum()
        fp = ((y_pred_thresh == 1) & (y == 0)).sum()
        fn = ((y_pred_thresh == 0) & (y == 1)).sum()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    logger.info(f"\n🎯 SEUIL OPTIMAL (F1): {best_threshold:.3f} (F1={best_f1:.4f})")


def generate_recommendations():
    """Génère recommandations basées sur l'audit."""

    logger.info("\n" + "="*80)
    logger.info("💡 RECOMMANDATIONS PRIORITAIRES")
    logger.info("="*80)

    recommendations = []

    # TODO: Ajouter logique de recommandations basée sur les résultats d'audit

    logger.info(f"\n🔥 CRITIQUES (à faire immédiatement):")
    logger.info(f"   1. Ajuster seuil de décision à 0.35-0.40 (voir audit #6)")
    logger.info(f"   2. Ajouter class_weight='balanced' dans LightGBM")
    logger.info(f"   3. Augmenter dataset à 5-10 dates minimum")

    logger.info(f"\n⚠️ IMPORTANTES (à faire rapidement):")
    logger.info(f"   4. Feature selection: garder top 30-40 features seulement")
    logger.info(f"   5. Analyser trades perdants pour comprendre patterns")
    logger.info(f"   6. Vérifier si GEX levels sont pertinents pour scalping rapide")

    logger.info(f"\n✅ AMÉLIORATIONS (optionnel):")
    logger.info(f"   7. Tester XGBoost ou CatBoost comme alternative")
    logger.info(f"   8. Ajouter features temporelles (heure de journée, etc.)")
    logger.info(f"   9. Stratified K-Fold cross-validation")


if __name__ == "__main__":
    logger.info("\n" + "🔍"*40)
    logger.info("🔍 AUDIT COMPLET ET PROFOND - ML 3-LAYER STRATEGY")
    logger.info("🔍"*40)

    try:
        # Audit #1: Qualité données
        df = audit_data_quality()

        # Audit #2: Distribution features
        audit_feature_distributions(df)

        # Audit #3: Performance modèle
        audit_model_performance()

        # Audit #4: Importance features
        audit_feature_importance()

        # Audit #5: Séparation classes
        audit_class_separation()

        # Audit #6: Analyse prédictions
        audit_prediction_analysis()

        # Recommandations
        generate_recommendations()

        logger.info("\n" + "="*80)
        logger.info("✅ AUDIT TERMINÉ AVEC SUCCÈS")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\n❌ ERREUR DURANT L'AUDIT: {e}")
        import traceback
        traceback.print_exc()





