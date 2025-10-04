# install_rl_deps.py
# -*- coding: utf-8 -*-
"""
Script d'installation des dépendances pour le RL
"""

import subprocess
import sys
import os

def install_package(package):
    """Installe un package via pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installé avec succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur installation {package}: {e}")
        return False

def main():
    """Installe toutes les dépendances RL"""
    print("🚀 INSTALLATION DES DÉPENDANCES RL")
    print("=" * 50)
    
    # Dépendances RL
    rl_packages = [
        "stable-baselines3==2.3.2",
        "torch==2.3.1", 
        "gymnasium==0.29.1",
        "joblib"
    ]
    
    # Dépendances ML (au cas où)
    ml_packages = [
        "xgboost",
        "lightgbm", 
        "catboost",
        "scikit-learn",
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
        "pyarrow"
    ]
    
    all_packages = rl_packages + ml_packages
    
    print("📦 Installation des packages...")
    
    success_count = 0
    for package in all_packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 RÉSULTAT: {success_count}/{len(all_packages)} packages installés")
    
    if success_count == len(all_packages):
        print("🎉 Toutes les dépendances sont installées!")
        print("\n🚀 Vous pouvez maintenant lancer:")
        print("  python train_baseline.py --target y_dir_h")
        print("  python train_ppo.py")
        print("  python train_sac.py")
    else:
        print("⚠️ Certaines installations ont échoué")
        print("💡 Essayez d'installer manuellement les packages manquants")

if __name__ == "__main__":
    main()


