# gated_predictions.py
# -*- coding: utf-8 -*-
"""
Fonctions de prédiction gated pour améliorer les décisions
"""

import numpy as np
import pandas as pd

def gated_argmax(proba, t_down=0.20, t_up=0.20, margin=0.03):
    """
    Décision gated avec seuils pour éviter que la classe neutre aspire tout.
    
    Args:
        proba: array (n, 3) -> [p_down, p_neutral, p_up]
        t_down: seuil minimum pour prédire down
        t_up: seuil minimum pour prédire up  
        margin: marge minimale entre down et up pour éviter l'ambiguïté
    
    Returns:
        yhat: array (n,) avec prédictions 0=down, 1=neutral, 2=up
    """
    p0, p1, p2 = proba[:,0], proba[:,1], proba[:,2]
    yhat = np.ones(len(proba), dtype=int)  # 1 = neutre par défaut
    
    # Conditions pour down (classe 0)
    pick_down = (p0 >= t_down) & ((p0 - p2) >= margin)
    
    # Conditions pour up (classe 2)  
    pick_up = (p2 >= t_up) & ((p2 - p0) >= margin)
    
    yhat[pick_down] = 0
    yhat[pick_up] = 2
    
    return yhat

def adaptive_thresholds(vix_values, atr_values=None, base_t_down=0.18, base_t_up=0.18, base_margin=0.04):
    """
    Seuils adaptatifs basés sur le régime VIX/ATR.
    
    Args:
        vix_values: array des valeurs VIX
        atr_values: array des valeurs ATR (optionnel)
        base_t_down: seuil de base pour down
        base_t_up: seuil de base pour up
        base_margin: marge de base
    
    Returns:
        dict avec t_down, t_up, margin adaptés
    """
    if isinstance(vix_values, (int, float)):
        vix_values = np.array([vix_values])
    
    # Régimes VIX
    vix_median = np.median(vix_values)
    
    if vix_median < 15:  # calm
        factor = 1.2  # Seuils plus élevés (plus conservateur)
    elif vix_median < 25:  # normal
        factor = 1.0  # Seuils de base
    elif vix_median < 35:  # elevated
        factor = 0.8  # Seuils plus bas (plus agressif)
    else:  # high
        factor = 0.6  # Seuils très bas
    
    return {
        't_down': base_t_down * factor,
        't_up': base_t_up * factor,
        'margin': base_margin * factor
    }

def evaluate_gated_predictions(y_true, proba, vix_values=None, atr_values=None):
    """
    Évalue les prédictions gated avec différents seuils.
    
    Args:
        y_true: vraies classes
        proba: probabilités du modèle (n, 3)
        vix_values: valeurs VIX pour seuils adaptatifs
        atr_values: valeurs ATR pour seuils adaptatifs
    
    Returns:
        dict avec métriques pour différents seuils
    """
    from sklearn.metrics import accuracy_score, f1_score, classification_report
    
    results = {}
    
    # Seuils fixes
    thresholds = [
        (0.15, 0.15, 0.03),  # Conservateur
        (0.18, 0.18, 0.04),  # Standard
        (0.20, 0.20, 0.05),  # Agressif
    ]
    
    for t_down, t_up, margin in thresholds:
        y_pred = gated_argmax(proba, t_down, t_up, margin)
        
        results[f"fixed_{t_down}_{t_up}_{margin}"] = {
            'accuracy': accuracy_score(y_true, y_pred),
            'f1_macro': f1_score(y_true, y_pred, average='macro', zero_division=0),
            'f1_weighted': f1_score(y_true, y_pred, average='weighted', zero_division=0),
            'distribution': np.bincount(y_pred, minlength=3).tolist()
        }
    
    # Seuils adaptatifs si VIX disponible
    if vix_values is not None:
        adaptive_params = adaptive_thresholds(vix_values, atr_values)
        y_pred_adaptive = gated_argmax(proba, **adaptive_params)
        
        results['adaptive'] = {
            'accuracy': accuracy_score(y_true, y_pred_adaptive),
            'f1_macro': f1_score(y_true, y_pred_adaptive, average='macro', zero_division=0),
            'f1_weighted': f1_score(y_true, y_pred_adaptive, average='weighted', zero_division=0),
            'distribution': np.bincount(y_pred_adaptive, minlength=3).tolist(),
            'params': adaptive_params
        }
    
    return results

def print_gated_results(results):
    """Affiche les résultats des prédictions gated"""
    print("\n=== RÉSULTATS PRÉDICTIONS GATED ===")
    
    for name, metrics in results.items():
        print(f"\n{name}:")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  F1-macro: {metrics['f1_macro']:.4f}")
        print(f"  F1-weighted: {metrics['f1_weighted']:.4f}")
        print(f"  Distribution: {metrics['distribution']}")
        
        if 'params' in metrics:
            print(f"  Params: {metrics['params']}")

if __name__ == "__main__":
    # Test simple
    np.random.seed(42)
    n = 1000
    proba = np.random.dirichlet([1, 10, 1], n)  # Neutre dominant
    y_true = np.random.choice([0, 1, 2], n, p=[0.1, 0.8, 0.1])
    vix = np.random.normal(20, 5, n)
    
    results = evaluate_gated_predictions(y_true, proba, vix)
    print_gated_results(results)


