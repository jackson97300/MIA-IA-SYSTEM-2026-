#!/usr/bin/env python3
"""
Moniteur de progression du Grid Search
"""

import json
import time
from pathlib import Path
from datetime import datetime

def check_progress():
    """Vérifie la progression du grid search"""

    results_file = Path("ml/grid_search_results.json")
    check_count = 0
    max_checks = 10  # 10 vérifications × 3 min = 30 min max

    print("\n" + "="*70)
    print("MONITEUR GRID SEARCH - HORIZON & SEUILS ATR")
    print("="*70)
    print(f"\nDemarre a: {datetime.now().strftime('%H:%M:%S')}")
    print("48 configurations a tester (ES, NQ, RTY)")
    print("Verification toutes les 3 minutes\n")
    print("="*70)

    while check_count < max_checks:
        check_count += 1

        print(f"\nVerification #{check_count}/{max_checks} - {datetime.now().strftime('%H:%M:%S')}")

        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    results = json.load(f)

                n_results = len(results)
                print(f"\nTERMINE ! {n_results} configurations testees")

                # Trier par score
                sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)

                print(f"\n{'='*70}")
                print("TOP 10 CONFIGURATIONS")
                print(f"{'='*70}\n")
                print(f"{'Rank':<5} {'Symbol':<8} {'Horizon':<10} {'ATR':<8} {'AUC':<8} {'F1':<8} {'Score':<8}")
                print("-"*70)

                for i, r in enumerate(sorted_results[:10], 1):
                    print(f"{i:<5} {r['symbol']:<8} {r['horizon_min']:>3}min     {r['atr_mult']:<8.2f} {r['auc']:<8.3f} {r['f1_macro']:<8.3f} {r['score']:<8.3f}")

                # Meilleure par symbole
                print(f"\n{'='*70}")
                print("MEILLEURE CONFIGURATION PAR SYMBOLE")
                print(f"{'='*70}\n")

                for symbol in ['ES', 'NQ', 'RTY']:
                    symbol_results = [r for r in sorted_results if r['symbol'] == symbol]
                    if symbol_results:
                        best = symbol_results[0]
                        print(f"{symbol}:")
                        print(f"   Horizon: {best['horizon_min']} min ({best['horizon_sec']}s)")
                        print(f"   ATR mult: {best['atr_mult']:.2f}")
                        print(f"   AUC: {best['auc']:.3f} | F1: {best['f1_macro']:.3f}")
                        print(f"   Balance: {best['balance_ratio']:.2f}:1")
                        print(f"   Score: {best['score']:.3f}\n")

                print(f"Resultats sauvegardes: {results_file}")
                return True

            except Exception as e:
                print(f"⚠️  Erreur lecture résultats: {e}")

        else:
            print("En cours... (prochaine verification dans 3 min)")

            # Attendre 3 minutes
            if check_count < max_checks:
                time.sleep(180)

    print(f"\nGrid search toujours en cours apres {check_count * 3} minutes")
    print("Le processus continue en arriere-plan. Relancez ce moniteur plus tard.")
    return False


if __name__ == "__main__":
    check_progress()
