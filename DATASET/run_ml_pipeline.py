# run_ml_pipeline.py
# -*- coding: utf-8 -*-
"""
Pipeline ML complet pour MIA IA System :
1. Construction du dataset à partir des JSONL
2. Analyse et validation du dataset
3. Entraînement des modèles baseline
4. Génération des rapports et visualisations

Usage:
    python run_ml_pipeline.py [--skip-build] [--skip-analysis] [--skip-training]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

def run_script(script_path: str, description: str) -> bool:
    """Exécute un script Python et retourne le succès"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ Succès!")
            if result.stdout:
                print("📋 Sortie:")
                print(result.stdout)
            return True
        else:
            print("❌ Erreur!")
            if result.stderr:
                print("🔍 Erreur:")
                print(result.stderr)
            if result.stdout:
                print("📋 Sortie:")
                print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    required_packages = [
        'pandas', 'numpy', 'scikit-learn', 'xgboost', 
        'matplotlib', 'seaborn', 'pyarrow'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Packages manquants:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n💡 Installez avec: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ Toutes les dépendances sont installées")
    return True

def check_data_availability():
    """Vérifie que les données source sont disponibles"""
    data_dir = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\OCTOBRE"
    
    if not os.path.exists(data_dir):
        print(f"❌ Répertoire de données non trouvé: {data_dir}")
        return False
    
    # Chercher des fichiers JSONL
    import glob
    jsonl_files = glob.glob(os.path.join(data_dir, "**", "*.jsonl"), recursive=True)
    
    if not jsonl_files:
        print(f"❌ Aucun fichier JSONL trouvé dans: {data_dir}")
        return False
    
    print(f"✅ {len(jsonl_files)} fichiers JSONL trouvés")
    return True

def main():
    """Fonction principale du pipeline"""
    parser = argparse.ArgumentParser(description="Pipeline ML complet pour MIA IA System")
    parser.add_argument("--skip-build", action="store_true", 
                       help="Ignorer la construction du dataset")
    parser.add_argument("--skip-analysis", action="store_true", 
                       help="Ignorer l'analyse du dataset")
    parser.add_argument("--skip-training", action="store_true", 
                       help="Ignorer l'entraînement des modèles")
    parser.add_argument("--force", action="store_true", 
                       help="Forcer l'exécution même en cas d'erreurs")
    
    args = parser.parse_args()
    
    print("🎯 MIA IA SYSTEM - PIPELINE ML COMPLET")
    print("=" * 60)
    print(f"📅 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Vérifications préliminaires
    print("\n🔍 Vérifications préliminaires...")
    
    if not check_dependencies():
        if not args.force:
            sys.exit(1)
        else:
            print("⚠️ Continuation forcée malgré les dépendances manquantes")
    
    if not check_data_availability():
        if not args.force:
            sys.exit(1)
        else:
            print("⚠️ Continuation forcée malgré les données manquantes")
    
    # Pipeline d'exécution
    success_count = 0
    total_steps = 0
    
    # 1. Construction du dataset
    if not args.skip_build:
        total_steps += 1
        if run_script("build_dataset.py", "CONSTRUCTION DU DATASET"):
            success_count += 1
        elif not args.force:
            print("❌ Pipeline arrêté à cause de l'échec de construction")
            sys.exit(1)
    
    # 2. Analyse du dataset
    if not args.skip_analysis:
        total_steps += 1
        if run_script("analyze_dataset.py", "ANALYSE DU DATASET"):
            success_count += 1
        elif not args.force:
            print("❌ Pipeline arrêté à cause de l'échec d'analyse")
            sys.exit(1)
    
    # 3. Entraînement des modèles
    if not args.skip_training:
        total_steps += 1
        if run_script("train_baseline.py", "ENTRAÎNEMENT DES MODÈLES"):
            success_count += 1
        elif not args.force:
            print("❌ Pipeline arrêté à cause de l'échec d'entraînement")
            sys.exit(1)
    
    # Résumé final
    print(f"\n{'='*60}")
    print("🎉 PIPELINE TERMINÉ!")
    print(f"{'='*60}")
    print(f"📊 Étapes réussies: {success_count}/{total_steps}")
    print(f"📅 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success_count == total_steps:
        print("✅ Toutes les étapes ont réussi!")
        print("\n📁 Fichiers générés:")
        print("  📊 Dataset: DATASET/dataset_20251002_20251003.parquet")
        print("  📈 Analyse: DATASET/analysis/")
        print("  🤖 Modèles: DATASET/models/")
        print("  📋 Résultats: DATASET/results/")
    else:
        print("⚠️ Certaines étapes ont échoué")
        if not args.force:
            sys.exit(1)

if __name__ == "__main__":
    main()


