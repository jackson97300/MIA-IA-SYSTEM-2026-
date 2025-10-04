# compare_models.py
# -*- coding: utf-8 -*-
"""
Comparaison complète de tous les modèles : XGBoost, LightGBM, CatBoost, PPO, SAC
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
import warnings

warnings.filterwarnings("ignore")

# === CONFIG =============================================================
DATASET_PATH = r"D:\MIA_IA_system\DATASET\dataset_20251002_20251003.parquet"
MODELS_DIR = r"D:\MIA_IA_system\DATASET\models"
RESULTS_DIR = r"D:\MIA_IA_system\DATASET\results"

class ModelComparator:
    """Comparateur de modèles ML et RL"""
    
    def __init__(self, dataset_path: str, models_dir: str, results_dir: str):
        self.dataset_path = dataset_path
        self.models_dir = Path(models_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Charger le dataset
        self.df = pd.read_parquet(dataset_path)
        self.df = self.df.sort_values("ts").reset_index(drop=True)
        
        # Split temporel
        pivot_time = self.df["ts"].quantile(0.7)
        self.train_df = self.df[self.df["ts"] < pivot_time].copy()
        self.test_df = self.df[self.df["ts"] >= pivot_time].copy()
        
        print(f"📊 Dataset: {len(self.df)} lignes")
        print(f"📅 Train: {len(self.train_df)} lignes")
        print(f"📅 Test: {len(self.test_df)} lignes")
    
    def evaluate_ml_models(self, target: str) -> Dict[str, Any]:
        """Évalue les modèles ML (XGBoost, LightGBM, CatBoost)"""
        print(f"\n🎯 Évaluation ML pour {target}...")
        
        # Chercher les fichiers de métriques
        metrics_files = list(self.results_dir.glob(f"metrics_{target}_*.csv"))
        
        if not metrics_files:
            print(f"⚠️ Aucun fichier de métriques trouvé pour {target}")
            return {}
        
        # Prendre le plus récent
        latest_file = max(metrics_files, key=lambda x: x.stat().st_mtime)
        
        try:
            df_metrics = pd.read_csv(latest_file)
            print(f"✅ Métriques chargées: {latest_file.name}")
            
            # Convertir en dict
            results = {}
            for _, row in df_metrics.iterrows():
                model_name = row['model']
                results[model_name] = {
                    'ROC_AUC': row.get('ROC_AUC', np.nan),
                    'PR_AUC': row.get('PR_AUC', np.nan),
                    'ACC': row.get('ACC', np.nan),
                    'F1': row.get('F1', np.nan),
                    'MCC': row.get('MCC', np.nan),
                    'LogLoss': row.get('LogLoss', np.nan)
                }
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur lecture métriques: {e}")
            return {}
    
    def evaluate_rl_models(self) -> Dict[str, Any]:
        """Évalue les modèles RL (PPO, SAC)"""
        print(f"\n🤖 Évaluation RL...")
        
        results = {}
        
        # Test PPO
        ppo_model_path = self.models_dir / "ppo_discrete.zip"
        if ppo_model_path.exists():
            try:
                from stable_baselines3 import PPO
                from rl_env import TradingDatasetEnv
                import joblib
                
                # Charger le scaler
                scaler_path = self.models_dir / "scaler_ppo.pkl"
                if scaler_path.exists():
                    scaler = joblib.load(scaler_path)
                else:
                    scaler = None
                
                # Créer l'environnement de test
                test_env = TradingDatasetEnv(
                    self.test_df, scaler=scaler, discret=True,
                    trans_cost=0.01, hold_cost=0.000
                )
                
                # Charger le modèle
                model = PPO.load(str(ppo_model_path))
                
                # Évaluation
                obs, _ = test_env.reset()
                done = False
                total_reward = 0.0
                steps = 0
                
                while not done:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, done, _, _ = test_env.step(action)
                    total_reward += reward
                    steps += 1
                
                results['PPO'] = {
                    'total_reward': total_reward,
                    'avg_reward': total_reward / steps if steps > 0 else 0,
                    'steps': steps,
                    'reward_per_step': total_reward / steps if steps > 0 else 0
                }
                
                print(f"✅ PPO évalué: reward={total_reward:.3f}, steps={steps}")
                
            except Exception as e:
                print(f"❌ Erreur évaluation PPO: {e}")
        
        # Test SAC
        sac_model_path = self.models_dir / "sac_continuous.zip"
        if sac_model_path.exists():
            try:
                from stable_baselines3 import SAC
                from rl_env import TradingDatasetEnv
                import joblib
                
                # Charger le scaler
                scaler_path = self.models_dir / "scaler_sac.pkl"
                if scaler_path.exists():
                    scaler = joblib.load(scaler_path)
                else:
                    scaler = None
                
                # Créer l'environnement de test
                test_env = TradingDatasetEnv(
                    self.test_df, scaler=scaler, discret=False,
                    trans_cost=0.01, hold_cost=0.000
                )
                
                # Charger le modèle
                model = SAC.load(str(sac_model_path))
                
                # Évaluation
                obs, _ = test_env.reset()
                done = False
                total_reward = 0.0
                steps = 0
                
                while not done:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, done, _, _ = test_env.step(action)
                    total_reward += reward
                    steps += 1
                
                results['SAC'] = {
                    'total_reward': total_reward,
                    'avg_reward': total_reward / steps if steps > 0 else 0,
                    'steps': steps,
                    'reward_per_step': total_reward / steps if steps > 0 else 0
                }
                
                print(f"✅ SAC évalué: reward={total_reward:.3f}, steps={steps}")
                
            except Exception as e:
                print(f"❌ Erreur évaluation SAC: {e}")
        
        return results
    
    def create_comparison_report(self, all_results: Dict[str, Dict]) -> str:
        """Crée un rapport de comparaison complet"""
        report_path = self.results_dir / "model_comparison_report.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("RAPPORT DE COMPARAISON DES MODÈLES - MIA IA SYSTEM\n")
            f.write("=" * 80 + "\n\n")
            
            # Résumé des données
            f.write("📊 DONNÉES UTILISÉES\n")
            f.write("-" * 40 + "\n")
            f.write(f"Dataset total: {len(self.df)} lignes\n")
            f.write(f"Train: {len(self.train_df)} lignes\n")
            f.write(f"Test: {len(self.test_df)} lignes\n")
            f.write(f"Période train: {self.train_df['ts'].min()} → {self.train_df['ts'].max()}\n")
            f.write(f"Période test: {self.test_df['ts'].min()} → {self.test_df['ts'].max()}\n\n")
            
            # Résultats par target
            for target, results in all_results.items():
                f.write(f"🎯 {target.upper()}\n")
                f.write("-" * 40 + "\n")
                
                if 'ml_models' in results:
                    f.write("📈 MODÈLES ML:\n")
                    for model_name, metrics in results['ml_models'].items():
                        f.write(f"  {model_name}:\n")
                        for metric, value in metrics.items():
                            if not np.isnan(value):
                                f.write(f"    {metric}: {value:.3f}\n")
                    f.write("\n")
                
                if 'rl_models' in results:
                    f.write("🤖 MODÈLES RL:\n")
                    for model_name, metrics in results['rl_models'].items():
                        f.write(f"  {model_name}:\n")
                        for metric, value in metrics.items():
                            f.write(f"    {metric}: {value:.3f}\n")
                    f.write("\n")
            
            # Recommandations
            f.write("💡 RECOMMANDATIONS\n")
            f.write("-" * 40 + "\n")
            
            # Analyser les meilleurs modèles
            best_models = {}
            for target, results in all_results.items():
                if 'ml_models' in results:
                    # Trouver le meilleur modèle ML par AUC
                    best_auc = -1
                    best_model = None
                    for model_name, metrics in results['ml_models'].items():
                        auc = metrics.get('ROC_AUC', 0)
                        if not np.isnan(auc) and auc > best_auc:
                            best_auc = auc
                            best_model = model_name
                    
                    if best_model:
                        best_models[f"{target}_ml"] = best_model
                        f.write(f"🏆 Meilleur modèle ML pour {target}: {best_model} (AUC: {best_auc:.3f})\n")
            
            # Recommandations générales
            f.write("\n📋 RECOMMANDATIONS GÉNÉRALES:\n")
            f.write("1. Commencez par les modèles ML (XGBoost/LightGBM/CatBoost) pour la stabilité\n")
            f.write("2. Utilisez le Policy Overlay pour gérer les seuils décisionnels\n")
            f.write("3. Testez les modèles RL en paper trading avant le live\n")
            f.write("4. Surveillez les métriques de performance en continu\n")
            f.write("5. Ajustez les coûts de transaction selon votre broker\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("Rapport généré le: " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            f.write("=" * 80 + "\n")
        
        return str(report_path)
    
    def run_comparison(self) -> Dict[str, Dict]:
        """Lance la comparaison complète"""
        print("🔍 COMPARAISON DES MODÈLES - MIA IA SYSTEM")
        print("=" * 60)
        
        all_results = {}
        
        # Targets disponibles
        targets = [col for col in self.df.columns if col.startswith('y_')]
        print(f"🎯 Targets disponibles: {targets}")
        
        # Évaluer chaque target
        for target in targets:
            print(f"\n📊 Évaluation de {target}...")
            
            # Modèles ML
            ml_results = self.evaluate_ml_models(target)
            
            # Modèles RL (une seule fois)
            if target == targets[0]:  # Premier target seulement
                rl_results = self.evaluate_rl_models()
            else:
                rl_results = {}
            
            all_results[target] = {
                'ml_models': ml_results,
                'rl_models': rl_results
            }
        
        # Créer le rapport
        report_path = self.create_comparison_report(all_results)
        print(f"\n📋 Rapport créé: {report_path}")
        
        return all_results

def main():
    """Fonction principale"""
    try:
        comparator = ModelComparator(DATASET_PATH, MODELS_DIR, RESULTS_DIR)
        results = comparator.run_comparison()
        
        print("\n🎉 COMPARAISON TERMINÉE!")
        print("📁 Consultez le rapport détaillé dans DATASET/results/")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


