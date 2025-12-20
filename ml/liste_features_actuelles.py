#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liste complète et actualisée de toutes les features utilisées dans l'entraînement ML
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.train_ml_direction_15min import get_manual_feature_list


def main():
    print("="*80)
    print("📋 LISTE COMPLÈTE DES FEATURES ACTUELLES - ACTUALISÉE")
    print("="*80)
    print()
    print(f"Date: 2 Novembre 2025")
    print(f"Fichier: ml/train_ml_direction_15min.py")
    print(f"Fonction: get_manual_feature_list()")
    print()

    # Récupérer toutes les features
    all_features = get_manual_feature_list()

    print("="*80)
    print(f"📊 TOTAL: {len(all_features)} features manuelles")
    print("="*80)
    print()

    # Catégoriser les features
    categories = {
        'Prix & Position': [],
        'VWAP & Bandes': [],
        'OrderFlow': [],
        'DOM': [],
        'Gamma & Options (MenthorQ)': [],
        'Battle Navale & MenthorQ Scores': [],
        'Volume & Volatilité': [],
        'Volume Profile': [],
        'Structure': [],
        'Session & Corrélation': [],
        'Symbole': [],
    }

    for feat in all_features:
        if any(x in feat for x in ['close', 'mid', 'microprice', 'd_vwap', 'd_vpoc', 'spread']):
            if 'd_vwap' in feat or 'd_vpoc' in feat or 'd_pvwap' in feat or 'd_w_' in feat:
                if any(x in feat for x in ['vwap', 'pvwap', 'w_']):
                    categories['VWAP & Bandes'].append(feat)
                else:
                    categories['Prix & Position'].append(feat)
            else:
                categories['Prix & Position'].append(feat)
        elif any(x in feat for x in ['vwap', 'pvwap', 'w_']):
            categories['VWAP & Bandes'].append(feat)
        elif any(x in feat for x in ['delta', 'cum_delta', 'smart_money', 'institutional', 'bidvol', 'askvol', 'askPct', 'bidPct']):
            categories['OrderFlow'].append(feat)
        elif any(x in feat for x in ['level1_imbalance', 'depth_imbalance', 'q_bq', 'q_aq', 'ob_center', 'top_heavy', 'dom_features']):
            categories['DOM'].append(feat)
        elif any(x in feat for x in ['gex_', 'blind_spot', 'menthor_distances', 'next_wall', 'call_resistance', 'put_support', 'hvl', 'menthor_meta']):
            categories['Gamma & Options (MenthorQ)'].append(feat)
        elif any(x in feat for x in ['battle_navale', 'menthorq_', 'confluence', 'gamma_call', 'gamma_put']):
            categories['Battle Navale & MenthorQ Scores'].append(feat)
        elif any(x in feat for x in ['volume', 'atr', 'volatility_regime', 'pressure_strength']):
            categories['Volume & Volatilité'].append(feat)
        elif any(x in feat for x in ['vpoc', 'vah', 'val', 'in_value_area']):
            categories['Volume Profile'].append(feat)
        elif any(x in feat for x in ['structure', 'd_1d_max', 'd_1d_min']):
            categories['Structure'].append(feat)
        elif any(x in feat for x in ['session', 'vix', 'corr']):
            categories['Session & Corrélation'].append(feat)
        elif 'symbol' in feat:
            categories['Symbole'].append(feat)
        else:
            categories['Prix & Position'].append(feat)  # Par défaut

    # Afficher par catégorie
    for cat_name, cat_features in categories.items():
        if cat_features:
            print(f"{'─'*80}")
            print(f"📂 {cat_name} ({len(cat_features)} features)")
            print(f"{'─'*80}")
            for i, feat in enumerate(sorted(cat_features), 1):
                # Marquer les features importantes récemment ajoutées/enrichies
                important_markers = {
                    'd_vwap_weekly_ticks': ' ✨ NOUVEAU',
                    'confluence_proximity': ' ⭐ IMPORTANT',
                    'gamma_call_confluence': ' ⭐ IMPORTANT',
                    'gamma_put_confluence': ' ⭐ IMPORTANT',
                    'menthor_distances.call0': ' ⭐ IMPORTANT',
                    'menthor_distances.put0': ' ⭐ IMPORTANT',
                    'menthor_distances.gamma0': ' ⭐ IMPORTANT',
                    'menthor_distances.hvl0': ' ⭐ IMPORTANT',
                    'menthor_distances.dist_1d_max': ' ⭐ IMPORTANT',
                    'menthor_distances.dist_1d_min': ' ⭐ IMPORTANT',
                    'next_wall.age_min': ' ⭐ IMPORTANT',
                    'next_wall.dist_pts': ' ⭐ IMPORTANT',
                }
                marker = important_markers.get(feat, '')
                print(f"  {i:3d}. {feat:55s}{marker}")
            print()

    # Statistiques MenthorQ
    print("="*80)
    print("📊 STATISTIQUES MENTHORQ")
    print("="*80)
    print()

    menthorq_features = []
    for feat in all_features:
        if any(x in feat for x in [
            'gex_', 'blind_spot', 'menthor_distances', 'next_wall',
            'battle_navale', 'menthorq_', 'confluence_',
            'gamma_call', 'gamma_put', 'call_resistance',
            'put_support', 'hvl', 'menthor_meta'
        ]):
            menthorq_features.append(feat)

    print(f"Features MenthorQ totales: {len(menthorq_features)}")
    print()

    # Détail par sous-catégorie MenthorQ
    menthorq_categories = {
        'GEX Levels': [f for f in menthorq_features if f.startswith('gex_')],
        'Blind Spots': [f for f in menthorq_features if 'blind_spot' in f],
        'Menthor Distances': [f for f in menthorq_features if 'menthor_distances' in f],
        'Next Wall': [f for f in menthorq_features if 'next_wall' in f],
        'Battle Navale': [f for f in menthorq_features if 'battle_navale' in f],
        'MenthorQ Scores': [f for f in menthorq_features if 'menthorq_' in f],
        'Confluence': [f for f in menthorq_features if 'confluence' in f],
        'Structure Options': [f for f in menthorq_features if f in ['call_resistance', 'put_support', 'hvl']],
        'Menthor Meta': [f for f in menthorq_features if 'menthor_meta' in f],
    }

    for cat_name, cat_features in menthorq_categories.items():
        if cat_features:
            print(f"  {cat_name:25s} : {len(cat_features):2d} features")
            for feat in sorted(cat_features):
                print(f"      - {feat}")

    print()
    print("="*80)
    print("✅ Liste complète générée")
    print("="*80)


if __name__ == '__main__':
    main()

