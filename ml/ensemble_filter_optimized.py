#!/usr/bin/env python3
"""
ML ENSEMBLE FILTER OPTIMIZED - Filtre ML optimisé avec placeholders fit
======================================================================

Corrige les warnings ML "not fitted" en utilisant des placeholders fit.
Comportement neutre (≈0.5) tant que les vrais modèles ne sont pas chargés.

Version: 1.0.0
Date: Janvier 2025
"""

import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.dummy import DummyClassifier
from sklearn.utils.validation import check_is_fitted
import warnings

class MLEnsembleFilterOptimized:
    """
    Filtre ML optimisé avec placeholders fit pour éviter les warnings
    
    Fonctionnalités :
    - Placeholders fit pour éviter les warnings "not fitted"
    - Comportement neutre (≈0.5) par défaut
    - Support pour vrais modèles quand disponibles
    - Cache des prédictions
    """
    
    def __init__(self, n_features: int = 16):
        """Initialisation du filtre ML optimisé"""
        self.n_features = n_features
        self.models = {
            "rf": DummyClassifier(strategy="prior"),
            "xgb": DummyClassifier(strategy="prior"),
            "logreg": DummyClassifier(strategy="prior"),
        }
        
        # Cache des prédictions
        self.prediction_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Initialiser les placeholders fit
        self._fit_placeholders()
        
        print("🤖 MLEnsembleFilterOptimized initialisé")
        print(f"   - Features: {n_features}")
        print(f"   - Modèles: {list(self.models.keys())}")
        print("   - Placeholders fit: ✅")
    
    def _fit_placeholders(self):
        """Fit les placeholders pour éviter les warnings"""
        # Données d'entraînement fictives
        X = np.zeros((2, self.n_features), dtype=float)
        y = np.array([0, 1])
        
        for name, model in self.models.items():
            try:
                # Supprimer les warnings pour les placeholders
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(X, y)
                print(f"   ✅ {name} placeholder fit")
            except Exception as e:
                print(f"   ⚠️ Erreur fit {name}: {e}")
    
    def predict_proba(self, X: np.ndarray, use_cache: bool = True) -> float:
        """
        Prédiction de probabilité avec cache
        
        Args:
            X: Features (1D array)
            use_cache: Utiliser le cache des prédictions
            
        Returns:
            Probabilité de signal (0.0-1.0)
        """
        # Vérifier le cache
        if use_cache:
            cache_key = self._get_cache_key(X)
            if cache_key in self.prediction_cache:
                self.cache_hits += 1
                return self.prediction_cache[cache_key]
        
        # Calculer les prédictions
        probs = {}
        for name, model in self.models.items():
            try:
                # Vérifier si le modèle est fit
                check_is_fitted(model)
                
                # Prédiction
                if hasattr(model, 'predict_proba'):
                    prob = model.predict_proba(X.reshape(1, -1))[0, 1]
                else:
                    prob = 0.5  # Fallback neutre
                
                probs[name] = float(prob)
                
            except Exception as e:
                # Fallback neutre en cas d'erreur
                probs[name] = 0.5
                print(f"⚠️ Erreur prédiction {name}: {e}")
        
        # Agrégation robuste
        if probs:
            final_prob = float(np.mean(list(probs.values())))
        else:
            final_prob = 0.5  # Fallback neutre
        
        # Mettre en cache
        if use_cache:
            cache_key = self._get_cache_key(X)
            self.prediction_cache[cache_key] = final_prob
            self.cache_misses += 1
        
        return final_prob
    
    def _get_cache_key(self, X: np.ndarray) -> str:
        """Génère une clé de cache pour les features"""
        # Utiliser les premières et dernières features pour la clé
        key_features = np.concatenate([X[:3], X[-3:]])
        return str(np.round(key_features, 3))
    
    def load_real_models(self, model_paths: Dict[str, str]):
        """
        Charge les vrais modèles depuis le disque
        
        Args:
            model_paths: Dictionnaire {nom_modèle: chemin_fichier}
        """
        print("🔄 Chargement des vrais modèles...")
        
        for name, path in model_paths.items():
            try:
                if name in self.models:
                    # Charger le modèle (exemple avec joblib)
                    import joblib
                    real_model = joblib.load(path)
                    self.models[name] = real_model
                    print(f"   ✅ {name} chargé depuis {path}")
                else:
                    print(f"   ⚠️ Modèle {name} non reconnu")
                    
            except Exception as e:
                print(f"   ❌ Erreur chargement {name}: {e}")
    
    def get_model_status(self) -> Dict[str, Any]:
        """Retourne le statut des modèles"""
        status = {}
        for name, model in self.models.items():
            try:
                check_is_fitted(model)
                status[name] = {
                    "fitted": True,
                    "type": type(model).__name__,
                    "is_placeholder": isinstance(model, DummyClassifier)
                }
            except Exception:
                status[name] = {
                    "fitted": False,
                    "type": type(model).__name__,
                    "is_placeholder": isinstance(model, DummyClassifier)
                }
        
        return status
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.prediction_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": hit_rate
        }
    
    def clear_cache(self):
        """Vide le cache des prédictions"""
        self.prediction_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        print("🗑️ Cache ML vidé")

# Instance globale
_global_ml_filter = None

def get_ml_ensemble_filter() -> MLEnsembleFilterOptimized:
    """Retourne l'instance globale du filtre ML"""
    global _global_ml_filter
    if _global_ml_filter is None:
        _global_ml_filter = MLEnsembleFilterOptimized()
    return _global_ml_filter

# Fonction de compatibilité
def predict_signal_probability(features: np.ndarray) -> float:
    """Fonction de compatibilité pour prédire la probabilité de signal"""
    ml_filter = get_ml_ensemble_filter()
    return ml_filter.predict_proba(features)

if __name__ == "__main__":
    # Test du filtre ML optimisé
    print("🧪 Test MLEnsembleFilterOptimized...")
    
    ml_filter = MLEnsembleFilterOptimized(n_features=8)
    
    # Test de prédiction
    test_features = np.random.random(8)
    prob = ml_filter.predict_proba(test_features)
    print(f"📊 Probabilité prédite: {prob:.3f}")
    
    # Test du statut des modèles
    status = ml_filter.get_model_status()
    print(f"🤖 Statut modèles: {status}")
    
    # Test des stats du cache
    cache_stats = ml_filter.get_cache_stats()
    print(f"📈 Stats cache: {cache_stats}")
    
    print("✅ Test MLEnsembleFilterOptimized terminé")





