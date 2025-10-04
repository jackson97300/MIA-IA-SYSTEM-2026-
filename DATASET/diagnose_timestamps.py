# diagnose_timestamps.py
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour analyser les timestamps dans les fichiers JSONL
"""

import os, glob, json
import pandas as pd
import numpy as np

def analyze_timestamps(file_path: str):
    """Analyse les timestamps d'un fichier JSONL"""
    print(f"\n=== Analyse: {os.path.basename(file_path)} ===")
    
    try:
        # Lire quelques lignes
        with open(file_path, 'r') as f:
            lines = [f.readline().strip() for _ in range(5)]
        
        timestamps = []
        for i, line in enumerate(lines):
            if line:
                try:
                    data = json.loads(line)
                    if 't' in data:
                        timestamps.append(data['t'])
                    elif 'ts' in data:
                        timestamps.append(data['ts'])
                    else:
                        print(f"   Ligne {i}: Pas de timestamp trouvé")
                        print(f"   Clés disponibles: {list(data.keys())}")
                except json.JSONDecodeError:
                    print(f"   Ligne {i}: JSON invalide")
        
        if timestamps:
            timestamps = np.array(timestamps)
            print(f"   Timestamps trouvés: {len(timestamps)}")
            print(f"   Min: {timestamps.min()}")
            print(f"   Max: {timestamps.max()}")
            print(f"   Médiane: {np.median(timestamps)}")
            print(f"   Type: {type(timestamps[0])}")
            
            # Essayer de convertir en datetime
            try:
                # Test nanosecondes
                dt_ns = pd.to_datetime(timestamps, unit='ns')
                print(f"   En nanosecondes: {dt_ns.min()} → {dt_ns.max()}")
            except:
                pass
            
            try:
                # Test millisecondes
                dt_ms = pd.to_datetime(timestamps, unit='ms')
                print(f"   En millisecondes: {dt_ms.min()} → {dt_ms.max()}")
            except:
                pass
            
            try:
                # Test secondes
                dt_s = pd.to_datetime(timestamps, unit='s')
                print(f"   En secondes: {dt_s.min()} → {dt_s.max()}")
            except:
                pass
        
    except Exception as e:
        print(f"   Erreur: {e}")

def main():
    base_dir = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\OCTOBRE"
    ymd = "20251002"
    
    # Trouver quelques fichiers représentatifs
    files = glob.glob(os.path.join(base_dir, "**", f"*{ymd}*.jsonl"), recursive=True)
    
    # Analyser quelques fichiers de chaque type
    file_types = {}
    for f in files:
        basename = os.path.basename(f)
        if "basedata" in basename:
            file_types["basedata"] = f
        elif "vwap" in basename:
            file_types["vwap"] = f
        elif "nbcv" in basename:
            file_types["nbcv"] = f
        elif "menthorq" in basename:
            file_types["menthorq"] = f
    
    print("=== DIAGNOSTIC DES TIMESTAMPS ===")
    for file_type, file_path in file_types.items():
        analyze_timestamps(file_path)
    
    print("\n=== RECOMMANDATIONS ===")
    print("1. Vérifier l'unité des timestamps (ns/ms/s)")
    print("2. Ajuster le parsing dans build_dataset_full.py")
    print("3. Tester avec un fichier spécifique")

if __name__ == "__main__":
    main()


