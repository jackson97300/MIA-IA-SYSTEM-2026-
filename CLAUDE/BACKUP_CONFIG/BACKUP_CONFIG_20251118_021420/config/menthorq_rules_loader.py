#!/usr/bin/env python3
"""
🧠 MENTHORQ RULES LOADER - MIA_IA_SYSTEM
========================================

Chargeur de configuration centralisée pour les règles MenthorQ.
Gère les distances, thresholds, staleness, sizing et hard rules.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback si core.logger n'est pas disponible
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

@dataclass
class MenthorQRules:
    """Configuration centralisée des règles MenthorQ"""
    
    # Distances
    distances: Dict[str, Dict[str, float]]
    
    # Thresholds
    thresholds: Dict[str, Dict[str, float]]
    
    # Staleness
    staleness: Dict[str, Union[int, Dict[str, int]]]
    
    # Sizing
    sizing: Dict[str, float]
    
    # Hard rules
    hard_rules: Dict[str, Dict[str, Any]]
    
    # Monitoring
    monitoring: Dict[str, Dict[str, Any]]
    
    # Weights
    weights: Dict[str, float]
    
    # Level weights
    level_weights: Dict[str, Dict[str, float]]
    
    # Validation
    validation: Dict[str, Union[int, bool]]
    
    # Metadata
    version: str
    last_updated: str

class MenthorQRulesLoader:
    """Chargeur de configuration MenthorQ"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "menthorq_rules.json"
        self._rules: Optional[MenthorQRules] = None
        self._load_time: Optional[datetime] = None
    
    def load_rules(self) -> MenthorQRules:
        """Charge les règles MenthorQ depuis le fichier JSON"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration MenthorQ non trouvée: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self._rules = MenthorQRules(
                distances=config_data.get('distances', {}),
                thresholds=config_data.get('thresholds', {}),
                staleness=config_data.get('staleness', {}),
                sizing=config_data.get('sizing', {}),
                hard_rules=config_data.get('hard_rules', {}),
                monitoring=config_data.get('monitoring', {}),
                weights=config_data.get('weights', {}),
                level_weights=config_data.get('level_weights', {}),
                validation=config_data.get('validation', {}),
                version=config_data.get('version', '1.0'),
                last_updated=config_data.get('last_updated', '')
            )
            
            self._load_time = datetime.now()
            logger.info(f"✅ Configuration MenthorQ chargée: {self.config_path}")
            logger.debug(f"Version: {self._rules.version}, Dernière mise à jour: {self._rules.last_updated}")
            
            return self._rules
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement configuration MenthorQ: {e}")
            raise
    
    def get_rules(self) -> MenthorQRules:
        """Retourne les règles chargées (charge si nécessaire)"""
        if self._rules is None:
            return self.load_rules()
        return self._rules
    
    def reload_rules(self) -> MenthorQRules:
        """Recharge les règles depuis le fichier"""
        self._rules = None
        return self.load_rules()
    
    def get_distance_threshold(self, level_type: str, distance_type: str) -> float:
        """Retourne un seuil de distance pour un type de niveau"""
        rules = self.get_rules()
        return rules.distances.get(level_type, {}).get(distance_type, 50.0)
    
    def get_confluence_threshold(self, threshold_type: str) -> float:
        """Retourne un seuil de confluence"""
        rules = self.get_rules()
        return rules.thresholds.get('confluence', {}).get(threshold_type, 0.5)
    
    def get_leadership_threshold(self, threshold_type: str) -> float:
        """Retourne un seuil de leadership"""
        rules = self.get_rules()
        return rules.thresholds.get('leadership', {}).get(threshold_type, 0.5)
    
    def get_staleness_threshold(self, vix_regime: str = 'normal') -> int:
        """Retourne le seuil de staleness selon le régime VIX"""
        rules = self.get_rules()
        max_age = rules.staleness.get('max_age_minutes', {})
        return max_age.get(vix_regime, 30)
    
    def get_sizing_factor(self, factor_name: str) -> float:
        """Retourne un facteur de sizing"""
        rules = self.get_rules()
        return rules.sizing.get(factor_name, 1.0)
    
    def is_hard_rule_enabled(self, rule_name: str) -> bool:
        """Vérifie si une règle dure est activée"""
        rules = self.get_rules()
        return rules.hard_rules.get(rule_name, {}).get('enabled', False)
    
    def get_hard_rule_config(self, rule_name: str) -> Dict[str, Any]:
        """Retourne la configuration d'une règle dure"""
        rules = self.get_rules()
        return rules.hard_rules.get(rule_name, {})
    
    def get_level_weight(self, level_family: str, level_name: str) -> float:
        """Retourne le poids d'un niveau spécifique"""
        rules = self.get_rules()
        return rules.level_weights.get(level_family, {}).get(level_name, 0.1)
    
    def get_score_weight(self, component: str) -> float:
        """Retourne le poids d'un composant de score"""
        rules = self.get_rules()
        return rules.weights.get(component, 0.33)
    
    def validate_config(self) -> bool:
        """Valide la configuration chargée"""
        try:
            rules = self.get_rules()
            
            # Vérifications de base
            required_sections = ['distances', 'thresholds', 'staleness', 'sizing', 'hard_rules']
            for section in required_sections:
                if not hasattr(rules, section) or not getattr(rules, section):
                    logger.error(f"❌ Section manquante ou vide: {section}")
                    return False
            
            # Vérification des distances
            for level_type in ['blind_spots', 'gamma_levels', 'swing_levels']:
                if level_type not in rules.distances:
                    logger.error(f"❌ Type de niveau manquant: {level_type}")
                    return False
            
            # Vérification des seuils
            for threshold_type in ['confluence', 'leadership']:
                if threshold_type not in rules.thresholds:
                    logger.error(f"❌ Type de seuil manquant: {threshold_type}")
                    return False
            
            logger.info("✅ Configuration MenthorQ validée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur validation configuration: {e}")
            return False

# === INSTANCE GLOBALE ===

# Instance globale pour utilisation dans tout le système
_global_loader: Optional[MenthorQRulesLoader] = None

def get_menthorq_rules() -> MenthorQRules:
    """Retourne l'instance globale des règles MenthorQ"""
    global _global_loader
    if _global_loader is None:
        _global_loader = MenthorQRulesLoader()
    return _global_loader.get_rules()

def reload_menthorq_rules() -> MenthorQRules:
    """Recharge les règles MenthorQ"""
    global _global_loader
    if _global_loader is None:
        _global_loader = MenthorQRulesLoader()
    return _global_loader.reload_rules()

# === FONCTIONS UTILITAIRES ===

def get_blind_spot_distance_threshold(distance_type: str = 'close') -> float:
    """Retourne un seuil de distance pour les Blind Spots"""
    rules = get_menthorq_rules()
    return rules.distances.get('blind_spots', {}).get(distance_type, 15.0)

def get_gamma_distance_threshold(distance_type: str = 'close') -> float:
    """Retourne un seuil de distance pour les niveaux Gamma"""
    rules = get_menthorq_rules()
    return rules.distances.get('gamma_levels', {}).get(distance_type, 10.0)

def get_confluence_threshold(threshold_type: str = 'medium') -> float:
    """Retourne un seuil de confluence"""
    rules = get_menthorq_rules()
    return rules.thresholds.get('confluence', {}).get(threshold_type, 0.6)

def get_leadership_threshold(threshold_type: str = 'moderate') -> float:
    """Retourne un seuil de leadership"""
    rules = get_menthorq_rules()
    return rules.thresholds.get('leadership', {}).get(threshold_type, 0.5)

def get_staleness_threshold(vix_regime: str = 'normal') -> int:
    """Retourne le seuil de staleness selon le régime VIX"""
    rules = get_menthorq_rules()
    max_age = rules.staleness.get('max_age_minutes', {})
    return max_age.get(vix_regime, 30)

def is_hard_rule_enabled(rule_name: str) -> bool:
    """Vérifie si une règle dure est activée"""
    rules = get_menthorq_rules()
    return rules.hard_rules.get(rule_name, {}).get('enabled', False)

# === TEST ===

if __name__ == "__main__":
    # Test du chargeur
    loader = MenthorQRulesLoader()
    
    try:
        rules = loader.load_rules()
        print(f"✅ Configuration chargée: {rules.version}")
        print(f"📊 Distances Blind Spots: {rules.distances.get('blind_spots', {})}")
        print(f"🎯 Seuils Confluence: {rules.thresholds.get('confluence', {})}")
        print(f"⏰ Staleness: {rules.staleness.get('max_age_minutes', {})}")
        
        # Test validation
        if loader.validate_config():
            print("✅ Configuration validée avec succès")
        else:
            print("❌ Erreurs de validation détectées")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
