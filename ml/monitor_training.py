#!/usr/bin/env python3
"""
Moniteur d'entraînement - Configurations optimales Grid Search
"""

import time
from pathlib import Path
from datetime import datetime
import json

SYMBOLS = {
    "ES": {"horizon": "5min", "atr": 0.35},
    "NQ": {"horizon": "10min", "atr": 0.36},
    "RTY": {"horizon": "10min", "atr": 0.32}
}

def check_training_progress():
    """Vérifie la progression des entraînements"""
    
    models_dir = Path("ml/models_robust")
    
    print("\n" + "="*70)
    print("MONITEUR D'ENTRAINEMENT - CONFIGURATIONS OPTIMALES")
    print("="*70)
    print(f"\nDemarre a: {datetime.now().strftime('%H:%M:%S')}")
    print("\nConfigurations Grid Search:")
    for sym, config in SYMBOLS.items():
        print(f"  {sym}: {config['horizon']} | ATR×{config['atr']}")
    print("\n" + "="*70)
    
    check_count = 0
    max_checks = 20  # 20 × 3 min = 60 min max
    
    while check_count < max_checks:
        check_count += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Verification #{check_count}/{max_checks}")
        
        completed = []
        pending = []
        
        for symbol in SYMBOLS.keys():
            # Chercher le dernier modèle
            pattern = f"lgbm_direction_optimal_{symbol}_BINARY_*.pkl"
            models = list(models_dir.glob(pattern))
            
            if models:
                latest = max(models, key=lambda p: p.stat().st_mtime)
                size_mb = latest.stat().st_size / (1024*1024)
                
                # Lire les métriques si disponibles
                metrics_file = latest.with_suffix('').name.replace("_latest", "") + "_metrics.json"
                metrics_path = models_dir / (metrics_file if not metrics_file.endswith(".json") else metrics_file.replace(".pkl", ".json"))
                
                if not str(metrics_path).endswith("_metrics.json"):
                    # Trouver le bon fichier metrics
                    base_name = latest.name.replace("_latest.pkl", "").replace(".pkl", "")
                    metrics_files = list(models_dir.glob(f"{base_name}*_metrics.json"))
                    if metrics_files:
                        metrics_path = metrics_files[0]
                
                if metrics_path.exists():
                    try:
                        with open(metrics_path, 'r') as f:
                            metrics = json.load(f)
                        acc = metrics.get('accuracy', 0)
                        auc = metrics.get('auc', 0)
                        completed.append((symbol, size_mb, acc, auc, latest.stat().st_mtime))
                        print(f"  [{symbol}] TERMINE - Acc={acc:.3f} AUC={auc:.3f} ({size_mb:.1f}MB)")
                    except:
                        pending.append(symbol)
                        print(f"  [{symbol}] En cours... ({size_mb:.1f}MB)")
                else:
                    pending.append(symbol)
                    print(f"  [{symbol}] En cours... ({size_mb:.1f}MB)")
            else:
                pending.append(symbol)
                print(f"  [{symbol}] Pas encore demarre")
        
        if len(completed) == 3:
            print(f"\n{'='*70}")
            print("TOUS LES ENTRAINEMENTS TERMINES !")
            print(f"{'='*70}\n")
            
            # Trier par score
            completed_sorted = sorted(completed, key=lambda x: x[3] if x[3] else 0, reverse=True)
            
            print("Resultats finaux:")
            print(f"{'Symbol':<10} {'Accuracy':<12} {'AUC':<12} {'Taille':<12}")
            print("-"*70)
            for sym, size, acc, auc, _ in completed_sorted:
                config = SYMBOLS[sym]
                print(f"{sym:<10} {acc:<12.3f} {auc if auc else 'N/A':<12} {size:<12.1f}MB")
                print(f"           Config: {config['horizon']} | ATR×{config['atr']}")
            
            return True
        
        if check_count < max_checks:
            print("\nProchaine verification dans 3 min...")
            time.sleep(180)
    
    print(f"\nTemps ecoule apres {check_count * 3} minutes")
    return False


if __name__ == "__main__":
    check_training_progress()


