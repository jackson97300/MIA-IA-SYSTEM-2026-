#!/usr/bin/env python3
"""
Script de monitoring pour suivre la progression du Grid Search NQ Phase 2
"""

import json
import time
from pathlib import Path
from datetime import datetime

def monitor_grid_search():
    """Surveille la progression du grid search"""

    results_file = Path("ml/grid_search_nq_phase2_results.json")

    print("\n" + "="*70)
    print("MONITORING GRID SEARCH NQ PHASE 2")
    print("="*70)
    print(f"Configurations a tester: 6 (ATR: 0.24, 0.28, 0.30, 0.32, 0.36, 0.40)")
    print(f"Fichier resultats: {results_file}")
    print("="*70)

    last_count = 0

    while True:
        try:
            if results_file.exists():
                with open(results_file, 'r') as f:
                    results = json.load(f)

                current_count = len(results)

                if current_count > last_count:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {current_count}/6 configurations testees")

                    if current_count > 0:
                        latest = results[-1]
                        print(f"  ATR x{latest['atr_multiplier']:.2f}")
                        print(f"    Accuracy: {latest['accuracy']:.3f}")
                        print(f"    AUC: {latest['auc']:.3f}")
                        print(f"    Trades @0.60: {latest['trades_at_60']:,} (WR={latest['win_rate_at_60']:.1%})")

                        # Afficher le meilleur jusqu'a maintenant
                        best = max(results, key=lambda x: x['accuracy'])
                        print(f"\n  Meilleur: ATR x{best['atr_multiplier']:.2f} (Acc={best['accuracy']:.3f})")

                    last_count = current_count

                # Si tous les tests sont termines
                if current_count >= 6:
                    print(f"\n{'='*70}")
                    print("GRID SEARCH TERMINE !")
                    print(f"{'='*70}\n")

                    # Afficher le classement final
                    sorted_results = sorted(results, key=lambda x: x['accuracy'], reverse=True)

                    print("CLASSEMENT FINAL (par Accuracy):\n")
                    for i, r in enumerate(sorted_results, 1):
                        print(f"{i}. ATR x{r['atr_multiplier']:.2f}")
                        print(f"   Accuracy: {r['accuracy']:.3f} | AUC: {r['auc']:.3f}")
                        print(f"   Trades @0.60: {r['trades_at_60']:,} (WR={r['win_rate_at_60']:.1%})")
                        print()

                    best = sorted_results[0]
                    print(f"{'='*70}")
                    print("MEILLEURE CONFIGURATION:")
                    print(f"{'='*70}")
                    print(f"  ATR Multiplier: {best['atr_multiplier']:.2f}")
                    print(f"  Accuracy: {best['accuracy']:.3f}")
                    print(f"  AUC: {best['auc']:.3f}")
                    print(f"  F1-Score: {best['f1_macro']:.3f}")
                    print(f"  Trades @0.60: {best['trades_at_60']:,}")
                    print(f"  Win Rate @0.60: {best['win_rate_at_60']:.1%}")
                    print(f"{'='*70}\n")

                    break
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] En attente du fichier resultats...")

            time.sleep(5)  # Verifier toutes les 5 secondes

        except json.JSONDecodeError:
            # Fichier en cours d'ecriture
            time.sleep(1)
            continue
        except KeyboardInterrupt:
            print("\n\nMonitoring interrompu par l'utilisateur")
            break
        except Exception as e:
            print(f"\nErreur: {e}")
            time.sleep(5)


if __name__ == "__main__":
    monitor_grid_search()

