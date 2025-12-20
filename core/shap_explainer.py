"""
Module: shap_explainer.py
Description: Explainability SHAP pour prédictions ML en production

Principe:
- Calculer top-3 features les plus influentes par prédiction
- Utiliser TreeExplainer de SHAP (rapide pour LightGBM)
- Mode production: calcul à la demande pour debugging

Auteur: MIA_IA_SYSTEM
Date: 5 Novembre 2025
Version: 1.0 - PATCH R10 GPT
"""

from typing import List, Dict, Any, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    Wrapper SHAP pour explainability des prédictions LightGBM
    
    Usage:
        explainer = SHAPExplainer(model, feature_names)
        top_features = explainer.explain_prediction(snapshot, top_n=3)
    """
    
    def __init__(self, model, feature_names: List[str]):
        """
        Initialiser l'explainer
        
        Args:
            model: Modèle LightGBM entraîné
            feature_names: Liste ordonnée des noms de features
        """
        try:
            import shap
            self.shap = shap
            self.has_shap = True
        except ImportError:
            logger.warning("⚠️  SHAP non installé. Utiliser: pip install shap")
            self.has_shap = False
            return
        
        self.model = model
        self.feature_names = feature_names
        
        # Créer TreeExplainer (rapide pour LightGBM)
        try:
            self.explainer = shap.TreeExplainer(model)
            logger.info("✅ SHAP TreeExplainer initialisé")
        except Exception as e:
            logger.warning(f"⚠️  Impossible d'initialiser SHAP: {e}")
            self.has_shap = False
    
    def explain_prediction(
        self,
        features: np.ndarray,
        top_n: int = 3
    ) -> Dict[str, Any]:
        """
        Expliquer une prédiction avec SHAP
        
        Args:
            features: Vecteur de features (1D array)
            top_n: Nombre de top features à retourner
        
        Returns:
            Dict avec:
                - top_features: Liste [(feature_name, shap_value, feature_value), ...]
                - base_value: Valeur de base (moyenne)
                - prediction: Prédiction finale
        """
        if not self.has_shap:
            return {
                "top_features": [],
                "base_value": None,
                "prediction": None,
                "error": "SHAP non disponible"
            }
        
        try:
            # Reshape si nécessaire
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # Calculer SHAP values
            shap_values = self.explainer.shap_values(features)
            
            # Si binaire, prendre classe positive (UP)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # Classe 1 (UP)
            
            # Extraire pour la première (et seule) prédiction
            shap_vals = shap_values[0] if shap_values.ndim > 1 else shap_values
            
            # Trier par importance absolue
            abs_shap = np.abs(shap_vals)
            top_indices = np.argsort(abs_shap)[::-1][:top_n]
            
            # Créer liste top features
            top_features = []
            for idx in top_indices:
                feature_name = self.feature_names[idx]
                shap_value = float(shap_vals[idx])
                feature_value = float(features[0, idx])
                
                top_features.append({
                    "feature": feature_name,
                    "shap_value": shap_value,
                    "feature_value": feature_value,
                    "contribution": "positive" if shap_value > 0 else "negative"
                })
            
            # Base value (moyenne des prédictions)
            base_value = float(self.explainer.expected_value[1] if isinstance(self.explainer.expected_value, (list, np.ndarray)) else self.explainer.expected_value)
            
            # Prédiction finale
            prediction = float(self.model.predict_proba(features)[0, 1]) if hasattr(self.model, 'predict_proba') else None
            
            return {
                "top_features": top_features,
                "base_value": base_value,
                "prediction": prediction,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"❌ Erreur SHAP: {e}")
            return {
                "top_features": [],
                "base_value": None,
                "prediction": None,
                "error": str(e)
            }
    
    def explain_prediction_simple(
        self,
        features: np.ndarray,
        top_n: int = 3
    ) -> List[Tuple[str, float, float]]:
        """
        Version simplifiée qui retourne seulement les top features
        
        Args:
            features: Vecteur de features
            top_n: Nombre de top features
        
        Returns:
            Liste de tuples (feature_name, shap_value, feature_value)
        """
        result = self.explain_prediction(features, top_n)
        
        if result["error"]:
            return []
        
        return [
            (f["feature"], f["shap_value"], f["feature_value"])
            for f in result["top_features"]
        ]
    
    def format_explanation(self, features: np.ndarray, top_n: int = 3) -> str:
        """
        Formater explication en texte lisible
        
        Args:
            features: Vecteur de features
            top_n: Nombre de top features
        
        Returns:
            String formaté pour logs
        """
        result = self.explain_prediction(features, top_n)
        
        if result["error"]:
            return f"SHAP non disponible: {result['error']}"
        
        lines = [f"📊 SHAP Explanation (Top-{top_n}):"]
        lines.append(f"   Base value: {result['base_value']:.3f}")
        lines.append(f"   Prediction: {result['prediction']:.3f}")
        lines.append(f"")
        lines.append(f"   Top features:")
        
        for i, f in enumerate(result['top_features'], 1):
            sign = "+" if f['shap_value'] > 0 else ""
            lines.append(f"   {i}. {f['feature']}: {sign}{f['shap_value']:.4f} (value={f['feature_value']:.2f})")
        
        return "\n".join(lines)


# ═════════════════════════════════════════════════════════════
# FONCTION UTILITAIRE POUR PRODUCTION
# ═════════════════════════════════════════════════════════════

def create_explainer_from_model_dir(model_path: str, manifest_path: str):
    """
    Créer explainer depuis fichiers sauvegardés
    
    Args:
        model_path: Chemin vers modèle .pkl
        manifest_path: Chemin vers features_manifest.json
    
    Returns:
        SHAPExplainer initialisé
    """
    import pickle
    import json
    
    # Charger modèle
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Charger manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    feature_names = manifest['feature_order']
    
    return SHAPExplainer(model, feature_names)


# ═════════════════════════════════════════════════════════════
# EXEMPLE D'USAGE EN PRODUCTION
# ═════════════════════════════════════════════════════════════

"""
EXEMPLE D'INTÉGRATION DANS LE SIGNAL HANDLER:

from core.shap_explainer import SHAPExplainer

# Initialisation (une seule fois au démarrage)
explainer = SHAPExplainer(model, feature_names)

# Dans la boucle de trading
def handle_signal(signal_data):
    snapshot = capture_market_snapshot()
    
    # Gates
    gate_ok, gate_reason = check_execution_gates(snapshot, signal_data['symbol'])
    if not gate_ok:
        return {"decision": "REJECT", "reason": gate_reason}
    
    # Préparer features
    features_ordered = np.array([snapshot.get(f, np.nan) for f in manifest['feature_order']])
    
    # ML
    proba_ml = model.predict_proba([features_ordered])[0, 1]
    seuil = compute_dynamic_threshold(snapshot)
    
    # ✅ SHAP Explanation (optionnel, seulement si accepté)
    if proba_ml >= seuil:
        explanation = explainer.format_explanation(features_ordered, top_n=3)
        logger.info(f"✅ ACCEPT: proba={proba_ml:.3f} | {gate_reason}")
        logger.info(explanation)
        
        # Extraire top-3 pour runbook
        top_features = explainer.explain_prediction_simple(features_ordered, top_n=3)
        
        return {
            "decision": "ACCEPT",
            "proba": proba_ml,
            "seuil": seuil,
            "reason": gate_reason,
            "shap_top3": top_features  # [(feature, shap_val, feat_val), ...]
        }
    else:
        return {"decision": "REJECT", "proba": proba_ml, "seuil": seuil}
"""


if __name__ == "__main__":
    # Test unitaire (nécessite un modèle entraîné)
    print("\n" + "="*70)
    print("SHAP EXPLAINER - MODULE DE TEST")
    print("="*70)
    
    try:
        import shap
        print("✅ SHAP installé")
    except ImportError:
        print("❌ SHAP non installé. Installer avec: pip install shap")
        exit(1)
    
    # Créer un modèle factice pour test
    from lightgbm import LGBMClassifier
    from sklearn.datasets import make_classification
    
    print("\n📊 Création modèle factice pour test...")
    X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
    feature_names = [f"feature_{i}" for i in range(10)]
    
    model = LGBMClassifier(n_estimators=50, random_state=42, verbose=-1)
    model.fit(X, y)
    
    print("✅ Modèle entraîné")
    
    # Créer explainer
    print("\n🔧 Initialisation SHAP explainer...")
    explainer = SHAPExplainer(model, feature_names)
    
    # Expliquer une prédiction
    print("\n📊 Explication d'une prédiction...")
    test_sample = X[0]
    
    # Version détaillée
    result = explainer.explain_prediction(test_sample, top_n=3)
    print(f"\n✅ Résultat détaillé:")
    print(f"   Prediction: {result['prediction']:.3f}")
    print(f"   Base value: {result['base_value']:.3f}")
    print(f"   Top-3 features:")
    for f in result['top_features']:
        print(f"      - {f['feature']}: {f['shap_value']:.4f} (value={f['feature_value']:.2f})")
    
    # Version formatée
    print("\n📝 Version formatée pour logs:")
    formatted = explainer.format_explanation(test_sample, top_n=3)
    print(formatted)
    
    # Version simple
    print("\n📋 Version simple (pour runbook):")
    simple = explainer.explain_prediction_simple(test_sample, top_n=3)
    for feat, shap_val, feat_val in simple:
        print(f"   {feat}: {shap_val:.4f} (value={feat_val:.2f})")
    
    print("\n✅ Tous les tests passés !")
    print("\n💡 Usage:")
    print("   pip install shap")
    print("   explainer = SHAPExplainer(model, feature_names)")
    print("   top_features = explainer.explain_prediction_simple(features, top_n=3)")


