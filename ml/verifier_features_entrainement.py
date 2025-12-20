#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérifie quelles features MenthorQ étaient disponibles lors du dernier entraînement
et lesquelles ont été sélectionnées par LightGBM
"""

import json
import sys
from pathlib import Path
from typing import Set, List

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train_ml_direction_15min import get_manual_feature_list


def main():
    print("="*70)
    print("🔍 VÉRIFICATION FEATURES MENTHORQ - ENTRÂINEMENT RÉEL")
    print("="*70)
    print()

    # 1. Features disponibles dans get_manual_feature_list() (version actuelle)
    print("📋 Étape 1 : Liste complète dans get_manual_feature_list()")
    all_manual_features = get_manual_feature_list()

    menthorq_manual = []
    for feat in all_manual_features:
        if any(x in feat for x in [
            'gex_', 'blind_spot', 'menthor_distances', 'next_wall',
            'battle_navale', 'menthorq_', 'confluence_',
            'gamma_call', 'gamma_put', 'call_resistance',
            'put_support', 'hvl', 'menthor_meta'
        ]):
            menthorq_manual.append(feat)

    print(f"   ✅ {len(menthorq_manual)} features MenthorQ dans la liste manuelle")
    print()

    # 2. Features sélectionnées par le modèle (dernier entraînement)
    print("📋 Étape 2 : Features sélectionnées par LightGBM (modèle ES)")
    model_file = Path("ml/models_robust/lgbm_direction_15min_ROBUST_ES_ultra_features_20251102_165521.json")

    if not model_file.exists():
        print(f"   ❌ Fichier non trouvé : {model_file}")
        return

    with open(model_file, 'r') as f:
        selected_features = json.load(f)

    menthorq_selected = []
    for feat in selected_features:
        if any(x in feat for x in [
            'gex_', 'blind_spot', 'menthor_distances', 'next_wall',
            'battle_navale', 'menthorq_', 'confluence_',
            'gamma_call', 'gamma_put', 'call_resistance',
            'put_support', 'hvl', 'menthor_meta'
        ]):
            menthorq_selected.append(feat)

    print(f"   ✅ {len(menthorq_selected)} features MenthorQ sélectionnées (sur {len(selected_features)} totales)")
    print()

    # 3. Comparaison
    print("="*70)
    print("📊 COMPARAISON")
    print("="*70)
    print()

    print(f"Features MenthorQ dans la liste manuelle     : {len(menthorq_manual)}")
    print(f"Features MenthorQ sélectionnées par LightGBM : {len(menthorq_selected)}")
    print()

    # Features manuelles vs sélectionnées (en tenant compte des features dérivées)
    print("✅ Features MenthorQ SÉLECTIONNÉES :")
    menthorq_selected_base = set()
    menthorq_selected_derived = []

    for feat in sorted(menthorq_selected):
        # Extraire le nom de base (sans _lag_, _ma_, etc.)
        base = feat
        for suffix in ['_lag_', '_ma_', '_vs_ma_', '_slope']:
            if suffix in feat:
                idx = feat.find(suffix)
                base = feat[:idx]
                menthorq_selected_derived.append(feat)
                break
        else:
            menthorq_selected_base.add(feat)

    print(f"   Features de base : {len(menthorq_selected_base)}")
    for feat in sorted(menthorq_selected_base):
        print(f"      - {feat}")

    print(f"\n   Features dérivées (LAGs/Rolling) : {len(menthorq_selected_derived)}")
    for feat in sorted(menthorq_selected_derived)[:10]:  # Afficher les 10 premières
        print(f"      - {feat}")
    if len(menthorq_selected_derived) > 10:
        print(f"      ... et {len(menthorq_selected_derived) - 10} autres")
    print()

    # Features disponibles mais NON sélectionnées
    print("❌ Features MenthorQ DISPONIBLES mais NON SÉLECTIONNÉES :")

    # Extraire les bases des features sélectionnées
    selected_bases = set()
    for feat in menthorq_selected:
        base = feat
        for suffix in ['_lag_', '_ma_', '_vs_ma_', '_slope', '_pct']:
            if suffix in feat:
                idx = feat.find(suffix)
                base = feat[:idx]
                break
        selected_bases.add(base)

    # Comparer avec les features manuelles
    missing = []
    for feat in menthorq_manual:
        if feat not in selected_bases:
            # Vérifier aussi si une variante a été sélectionnée
            found_variant = False
            for selected_base in selected_bases:
                if feat in selected_base or selected_base in feat:
                    found_variant = True
                    break
            if not found_variant:
                missing.append(feat)

    if missing:
        print(f"   {len(missing)} features disponibles mais non sélectionnées :")
        for feat in sorted(missing):
            print(f"      - {feat}")
    else:
        print("   ✅ Toutes les features MenthorQ de base ont été utilisées !")
        print("      (Certaines peuvent être absentes car dérivées en LAGs/Rolling)")
    print()

    # Statistiques par catégorie
    print("="*70)
    print("📈 STATISTIQUES PAR CATÉGORIE")
    print("="*70)
    print()

    categories = {
        'GEX': [f for f in menthorq_manual if f.startswith('gex_')],
        'Blind Spots': [f for f in menthorq_manual if 'blind_spot' in f],
        'Menthor Distances': [f for f in menthorq_manual if 'menthor_distances' in f],
        'Next Wall': [f for f in menthorq_manual if 'next_wall' in f],
        'Battle Navale': [f for f in menthorq_manual if 'battle_navale' in f],
        'MenthorQ Scores': [f for f in menthorq_manual if 'menthorq_' in f],
        'Confluence': [f for f in menthorq_manual if 'confluence' in f],
        'Structure': [f for f in menthorq_manual if f in ['call_resistance', 'put_support', 'hvl']],
        'Menthor Meta': [f for f in menthorq_manual if 'menthor_meta' in f],
    }

    for cat_name, cat_features in categories.items():
        if cat_features:
            # Compter celles sélectionnées (base ou dérivées)
            selected_in_cat = 0
            for feat in cat_features:
                # Vérifier si la feature ou une dérivée a été sélectionnée
                for selected in menthorq_selected:
                    base_selected = selected
                    for suffix in ['_lag_', '_ma_', '_vs_ma_', '_slope']:
                        if suffix in selected:
                            base_selected = selected[:selected.find(suffix)]
                            break
                    if feat == base_selected or feat in base_selected:
                        selected_in_cat += 1
                        break

            print(f"{cat_name:20s} : {len(cat_features):2d} disponibles, {selected_in_cat:2d} utilisées ({selected_in_cat/len(cat_features)*100:.0f}%)")

    print()
    print("="*70)
    print("💡 CONCLUSION")
    print("="*70)
    print()

    if len(menthorq_selected) >= len(menthorq_manual) * 0.5:
        print("✅ La majorité des features MenthorQ ont été utilisées.")
        print("   LightGBM a automatiquement sélectionné les plus importantes.")
    else:
        print("⚠️  Seulement une partie des features MenthorQ a été sélectionnée.")
        print("   Cela peut être dû à :")
        print("   1. Sélection automatique de LightGBM (feature importance)")
        print("   2. Features corrélées (LightGBM préfère une seule)")
        print("   3. Features moins discriminantes pour cette tâche")

    print()
    print(f"📊 Taux d'utilisation : {len(menthorq_selected_base)}/{len(menthorq_manual)} features de base ({len(menthorq_selected_base)/len(menthorq_manual)*100:.1f}%)")
    print(f"📊 Avec features dérivées : {len(menthorq_selected)} features totales")
    print()


if __name__ == '__main__':
    main()

