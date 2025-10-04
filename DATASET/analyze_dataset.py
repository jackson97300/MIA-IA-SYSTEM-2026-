# analyze_dataset.py
# -*- coding: utf-8 -*-
"""
Analyse complète du dataset ML généré :
- Statistiques descriptives
- Analyse des labels
- Détection de fuites temporelles
- Corrélations entre features
- Rapport de qualité
"""

import os
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# === CONFIG =============================================================
DATASET_PATH = r"D:\MIA_IA_system\DATASET\dataset_20251002_20251003.parquet"
OUTPUT_DIR = r"D:\MIA_IA_system\DATASET\analysis"

# === OUTILS =============================================================

def load_dataset(path: str) -> pd.DataFrame:
    """Charge le dataset depuis Parquet ou CSV"""
    if not os.path.exists(path):
        csv_path = path.replace(".parquet", ".csv")
        if os.path.exists(csv_path):
            print(f"Chargement CSV: {csv_path}")
            return pd.read_csv(csv_path)
        else:
            raise FileNotFoundError(f"Dataset non trouvé: {path}")
    
    print(f"Chargement Parquet: {path}")
    return pd.read_parquet(path)

def basic_stats(df: pd.DataFrame) -> Dict:
    """Statistiques de base du dataset"""
    stats = {
        "shape": df.shape,
        "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024**2,
        "date_range": {
            "start": df["ts"].min() if "ts" in df.columns else None,
            "end": df["ts"].max() if "ts" in df.columns else None
        },
        "symbols": df["sym"].nunique() if "sym" in df.columns else 0,
        "columns_count": len(df.columns),
        "missing_data": df.isnull().sum().sum(),
        "duplicate_rows": df.duplicated().sum()
    }
    return stats

def analyze_labels(df: pd.DataFrame) -> Dict:
    """Analyse des labels générés"""
    label_cols = [col for col in df.columns if col.startswith("y_")]
    analysis = {}
    
    for col in label_cols:
        if col in df.columns:
            counts = df[col].value_counts().sort_index()
            analysis[col] = {
                "distribution": counts.to_dict(),
                "balance_ratio": counts.min() / counts.max() if len(counts) > 1 else 1.0,
                "missing": df[col].isnull().sum()
            }
    
    return analysis

def detect_temporal_leaks(df: pd.DataFrame) -> Dict:
    """Détecte les fuites temporelles potentielles"""
    leaks = {}
    
    if "ts" not in df.columns:
        return {"error": "Colonne 'ts' manquante"}
    
    # Vérifier l'ordre temporel par symbole
    for sym in df["sym"].unique():
        sym_data = df[df["sym"] == sym].sort_values("ts")
        if not sym_data["ts"].is_monotonic_increasing:
            leaks[f"non_monotonic_{sym}"] = "Timestamps non monotones"
    
    # Vérifier les colonnes futures accidentelles
    future_cols = [col for col in df.columns if any(word in col.lower() for word in ["fwd", "future", "next", "tomorrow"])]
    if future_cols:
        leaks["future_columns"] = future_cols
    
    # Vérifier les corrélations suspectes avec les labels
    label_cols = [col for col in df.columns if col.startswith("y_")]
    for label in label_cols:
        if label in df.columns:
            # Corrélations très élevées (>0.9) avec des features
            feature_cols = [col for col in df.columns if not col.startswith(("y_", "ts", "sym"))]
            for feat in feature_cols:
                if feat in df.columns:
                    corr = df[label].corr(df[feat])
                    if abs(corr) > 0.9:
                        leaks[f"high_corr_{label}_{feat}"] = f"Corrélation {corr:.3f}"
    
    return leaks

def feature_importance_analysis(df: pd.DataFrame) -> Dict:
    """Analyse l'importance des features via corrélations"""
    label_cols = [col for col in df.columns if col.startswith("y_")]
    feature_cols = [col for col in df.columns if not col.startswith(("y_", "ts", "sym", "c_fwd", "hi_win", "lo_win"))]
    
    importance = {}
    
    for label in label_cols:
        if label in df.columns:
            correlations = []
            for feat in feature_cols:
                if feat in df.columns:
                    corr = df[label].corr(df[feat])
                    if not np.isnan(corr):
                        correlations.append((feat, abs(corr)))
            
            # Top 10 features les plus corrélées
            correlations.sort(key=lambda x: x[1], reverse=True)
            importance[label] = correlations[:10]
    
    return importance

def availability_analysis(df: pd.DataFrame) -> Dict:
    """Analyse des masques de disponibilité"""
    avail_cols = [col for col in df.columns if col.startswith("avail_")]
    analysis = {}
    
    for col in avail_cols:
        if col in df.columns:
            analysis[col] = {
                "availability_rate": df[col].mean(),
                "total_available": df[col].sum(),
                "total_rows": len(df)
            }
    
    return analysis

def generate_report(df: pd.DataFrame, output_dir: str) -> str:
    """Génère un rapport complet d'analyse"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    report_path = os.path.join(output_dir, "dataset_analysis_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("RAPPORT D'ANALYSE DU DATASET ML - MIA IA SYSTEM\n")
        f.write("=" * 80 + "\n\n")
        
        # Statistiques de base
        stats = basic_stats(df)
        f.write("📊 STATISTIQUES DE BASE\n")
        f.write("-" * 40 + "\n")
        f.write(f"Shape: {stats['shape']}\n")
        f.write(f"Mémoire utilisée: {stats['memory_usage_mb']:.1f} MB\n")
        f.write(f"Symboles: {stats['symbols']}\n")
        f.write(f"Colonnes: {stats['columns_count']}\n")
        f.write(f"Données manquantes: {stats['missing_data']}\n")
        f.write(f"Lignes dupliquées: {stats['duplicate_rows']}\n")
        if stats['date_range']['start']:
            f.write(f"Période: {stats['date_range']['start']} → {stats['date_range']['end']}\n")
        f.write("\n")
        
        # Analyse des labels
        labels = analyze_labels(df)
        f.write("🎯 ANALYSE DES LABELS\n")
        f.write("-" * 40 + "\n")
        for label, info in labels.items():
            f.write(f"{label}:\n")
            f.write(f"  Distribution: {info['distribution']}\n")
            f.write(f"  Balance ratio: {info['balance_ratio']:.3f}\n")
            f.write(f"  Manquants: {info['missing']}\n")
        f.write("\n")
        
        # Détection de fuites
        leaks = detect_temporal_leaks(df)
        f.write("🔍 DÉTECTION DE FUITES TEMPORELLES\n")
        f.write("-" * 40 + "\n")
        if leaks:
            for leak_type, description in leaks.items():
                f.write(f"⚠️ {leak_type}: {description}\n")
        else:
            f.write("✅ Aucune fuite temporelle détectée\n")
        f.write("\n")
        
        # Importance des features
        importance = feature_importance_analysis(df)
        f.write("📈 TOP 10 FEATURES PAR LABEL\n")
        f.write("-" * 40 + "\n")
        for label, features in importance.items():
            f.write(f"{label}:\n")
            for feat, corr in features:
                f.write(f"  {feat}: {corr:.3f}\n")
        f.write("\n")
        
        # Disponibilité des données
        availability = availability_analysis(df)
        f.write("📊 DISPONIBILITÉ DES DONNÉES\n")
        f.write("-" * 40 + "\n")
        for block, info in availability.items():
            f.write(f"{block}: {info['availability_rate']:.1%} ({info['total_available']}/{info['total_rows']})\n")
        f.write("\n")
        
        # Recommandations
        f.write("💡 RECOMMANDATIONS\n")
        f.write("-" * 40 + "\n")
        
        # Vérifier l'équilibre des labels
        for label, info in labels.items():
            if info['balance_ratio'] < 0.3:
                f.write(f"⚠️ Label {label} déséquilibré (ratio: {info['balance_ratio']:.3f})\n")
        
        # Vérifier la disponibilité des données
        for block, info in availability.items():
            if info['availability_rate'] < 0.5:
                f.write(f"⚠️ Bloc {block} peu disponible ({info['availability_rate']:.1%})\n")
        
        if not leaks:
            f.write("✅ Dataset prêt pour l'entraînement ML\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("Rapport généré le: " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write("=" * 80 + "\n")
    
    return report_path

def create_visualizations(df: pd.DataFrame, output_dir: str):
    """Crée des visualisations du dataset"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Configuration des graphiques
    plt.style.use('default')
    sns.set_palette("husl")
    
    # 1. Distribution des labels
    label_cols = [col for col in df.columns if col.startswith("y_")]
    if label_cols:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.flatten()
        
        for i, label in enumerate(label_cols[:4]):
            if label in df.columns and i < len(axes):
                df[label].value_counts().plot(kind='bar', ax=axes[i])
                axes[i].set_title(f'Distribution de {label}')
                axes[i].set_xlabel('Valeur')
                axes[i].set_ylabel('Fréquence')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "label_distributions.png"), dpi=300, bbox_inches='tight')
        plt.close()
    
    # 2. Matrice de corrélation des features principales
    feature_cols = [col for col in df.columns if not col.startswith(("y_", "ts", "sym", "avail_"))]
    if len(feature_cols) > 5:
        # Prendre les 20 features les plus importantes
        corr_matrix = df[feature_cols[:20]].corr()
        
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr_matrix, annot=False, cmap='coolwarm', center=0, 
                   square=True, cbar_kws={'shrink': 0.8})
        plt.title('Matrice de Corrélation des Features Principales')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "correlation_matrix.png"), dpi=300, bbox_inches='tight')
        plt.close()
    
    # 3. Disponibilité des données par bloc
    avail_cols = [col for col in df.columns if col.startswith("avail_")]
    if avail_cols:
        availability_rates = [df[col].mean() for col in avail_cols]
        block_names = [col.replace("avail_", "") for col in avail_cols]
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(block_names, availability_rates)
        plt.title('Taux de Disponibilité par Bloc de Données')
        plt.ylabel('Taux de Disponibilité')
        plt.xticks(rotation=45)
        
        # Colorer les barres selon le taux
        for bar, rate in zip(bars, availability_rates):
            if rate >= 0.8:
                bar.set_color('green')
            elif rate >= 0.5:
                bar.set_color('orange')
            else:
                bar.set_color('red')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "data_availability.png"), dpi=300, bbox_inches='tight')
        plt.close()

def main():
    """Fonction principale d'analyse"""
    print("🔍 ANALYSE DU DATASET ML - MIA IA SYSTEM")
    print("=" * 50)
    
    try:
        # Chargement du dataset
        print("📁 Chargement du dataset...")
        df = load_dataset(DATASET_PATH)
        print(f"✅ Dataset chargé: {df.shape}")
        
        # Génération du rapport
        print("📊 Génération du rapport d'analyse...")
        report_path = generate_report(df, OUTPUT_DIR)
        print(f"✅ Rapport généré: {report_path}")
        
        # Création des visualisations
        print("📈 Création des visualisations...")
        create_visualizations(df, OUTPUT_DIR)
        print(f"✅ Visualisations sauvegardées dans: {OUTPUT_DIR}")
        
        # Affichage des statistiques principales
        stats = basic_stats(df)
        print("\n📋 RÉSUMÉ:")
        print(f"  📊 Shape: {stats['shape']}")
        print(f"  💾 Mémoire: {stats['memory_usage_mb']:.1f} MB")
        print(f"  🎯 Symboles: {stats['symbols']}")
        print(f"  📈 Colonnes: {stats['columns_count']}")
        
        # Vérification des fuites
        leaks = detect_temporal_leaks(df)
        if leaks:
            print(f"  ⚠️ Fuites détectées: {len(leaks)}")
        else:
            print("  ✅ Aucune fuite temporelle")
        
        print(f"\n🎉 Analyse terminée! Consultez {OUTPUT_DIR} pour les détails.")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


