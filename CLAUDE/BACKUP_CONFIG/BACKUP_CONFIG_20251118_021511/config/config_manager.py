#!/usr/bin/env python3
"""
MIA IA System - Configuration Manager
Version: 3.0.0
Date: 2025-01-27

Gestionnaire centralisé de toutes les configurations du système
Unifie et optimise l'accès aux configurations pour la production
"""

import json
import yaml
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemConfig:
    """Configuration centralisée du système"""
    # Trading & Features
    feature_config: Dict[str, Any]
    trading_config: Dict[str, Any]
    automation_config: Dict[str, Any]
    
    # Leadership & Confluence
    leadership_config: Dict[str, Any]
    confluence_config: Dict[str, Any]
    
    # Sierra Chart & Data
    sierra_config: Dict[str, Any]
    data_collection_config: Dict[str, Any]
    
    # ML & Performance
    ml_config: Dict[str, Any]
    performance_config: Dict[str, Any]
    
    # Market & Session
    market_hours: Dict[str, Any]
    session_thresholds: Dict[str, Any]
    holidays: Dict[str, Any]
    
    # Logging & Monitoring
    logging_config: Dict[str, Any]
    monitoring_config: Dict[str, Any]
    
    # Constants
    constants: Dict[str, Any]

class ConfigManager:
    """Gestionnaire centralisé des configurations"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}
        self._system_config: Optional[SystemConfig] = None
        
    def load_config(self, filename: str) -> Dict[str, Any]:
        """Charge une configuration depuis un fichier"""
        try:
            if filename in self._config_cache:
                return self._config_cache[filename]
                
            file_path = self.config_dir / filename
            
            if not file_path.exists():
                logger.warning(f"⚠️ Fichier config manquant: {filename}")
                return {}
                
            with open(file_path, 'r', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    config = json.load(f)
                elif filename.endswith('.yaml') or filename.endswith('.yml'):
                    config = yaml.safe_load(f)
                elif filename.endswith('.py'):
                    # Pour les fichiers Python, on importe le module
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("config", file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    config = {k: v for k, v in module.__dict__.items() 
                             if not k.startswith('_') and not callable(v)}
                else:
                    logger.error(f"❌ Format de fichier non supporté: {filename}")
                    return {}
                    
            self._config_cache[filename] = config
            logger.debug(f"✅ Config chargée: {filename}")
            return config
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement config {filename}: {e}")
            return {}
    
    def load_system_config(self) -> SystemConfig:
        """Charge la configuration complète du système"""
        try:
            if self._system_config:
                return self._system_config
                
            # Chargement de toutes les configurations
            feature_config = self.load_config("feature_config.json")
            trading_config = self.load_config("trading_config.py")
            automation_config = self.load_config("automation_config.py")
            leadership_config = self.load_config("leadership_config.py")
            confluence_config = self.load_config("confluence_config.py")
            sierra_config = self.load_config("sierra_config.py")
            data_collection_config = self.load_config("data_collection_risk_config.py")
            ml_config = self.load_config("ml_config.py")
            performance_config = self.load_config("latency_optimization_config.py")
            market_hours = self.load_config("market_hours.json")
            session_thresholds = self.load_config("session_thresholds.json")
            holidays = self.load_config("holidays_us.json")
            logging_config = self.load_config("logging_config.py")
            monitoring_config = self.load_config("monitoring_config.py")
            constants = self.load_config("constants.py")
            
            self._system_config = SystemConfig(
                feature_config=feature_config,
                trading_config=trading_config,
                automation_config=automation_config,
                leadership_config=leadership_config,
                confluence_config=confluence_config,
                sierra_config=sierra_config,
                data_collection_config=data_collection_config,
                ml_config=ml_config,
                performance_config=performance_config,
                market_hours=market_hours,
                session_thresholds=session_thresholds,
                holidays=holidays,
                logging_config=logging_config,
                monitoring_config=monitoring_config,
                constants=constants
            )
            
            logger.info("✅ Configuration système chargée avec succès")
            return self._system_config
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement configuration système: {e}")
            raise
    
    def get_config(self, config_type: str, key: str = None) -> Any:
        """Récupère une configuration spécifique"""
        try:
            system_config = self.load_system_config()
            
            if not hasattr(system_config, config_type):
                logger.warning(f"⚠️ Type de config inconnu: {config_type}")
                return None
                
            config_data = getattr(system_config, config_type)
            
            if key is None:
                return config_data
                
            if isinstance(config_data, dict):
                return config_data.get(key)
            else:
                return getattr(config_data, key, None)
                
        except Exception as e:
            logger.error(f"❌ Erreur récupération config {config_type}.{key}: {e}")
            return None
    
    def update_config(self, config_type: str, key: str, value: Any) -> bool:
        """Met à jour une configuration"""
        try:
            system_config = self.load_system_config()
            
            if not hasattr(system_config, config_type):
                logger.warning(f"⚠️ Type de config inconnu: {config_type}")
                return False
                
            config_data = getattr(system_config, config_type)
            
            if isinstance(config_data, dict):
                config_data[key] = value
            else:
                setattr(config_data, key, value)
                
            logger.info(f"✅ Config mise à jour: {config_type}.{key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour config {config_type}.{key}: {e}")
            return False
    
    def save_config(self, config_type: str, filename: str = None) -> bool:
        """Sauvegarde une configuration dans un fichier"""
        try:
            system_config = self.load_system_config()
            
            if not hasattr(system_config, config_type):
                logger.warning(f"⚠️ Type de config inconnu: {config_type}")
                return False
                
            config_data = getattr(system_config, config_type)
            
            if filename is None:
                filename = f"{config_type}.json"
                
            file_path = self.config_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if isinstance(config_data, dict):
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(asdict(config_data), f, indent=2, ensure_ascii=False)
                    
            logger.info(f"✅ Config sauvegardée: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde config {config_type}: {e}")
            return False
    
    def validate_config(self) -> Dict[str, bool]:
        """Valide toutes les configurations"""
        try:
            system_config = self.load_system_config()
            validation_results = {}
            
            # Validation des configurations critiques
            critical_configs = [
                'feature_config', 'trading_config', 'automation_config',
                'leadership_config', 'sierra_config', 'ml_config'
            ]
            
            for config_type in critical_configs:
                config_data = getattr(system_config, config_type)
                validation_results[config_type] = bool(config_data)
                
            # Validation des fichiers de données
            data_files = ['market_hours', 'session_thresholds', 'holidays']
            for data_type in data_files:
                data = getattr(system_config, data_type)
                validation_results[data_type] = bool(data)
                
            logger.info("✅ Validation des configurations terminée")
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Erreur validation configurations: {e}")
            return {}
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Récupère un résumé de toutes les configurations"""
        try:
            system_config = self.load_system_config()
            summary = {}
            
            for field_name in system_config.__dataclass_fields__:
                config_data = getattr(system_config, field_name)
                if isinstance(config_data, dict):
                    summary[field_name] = {
                        'type': 'dict',
                        'keys': list(config_data.keys()) if config_data else [],
                        'size': len(config_data)
                    }
                else:
                    summary[field_name] = {
                        'type': type(config_data).__name__,
                        'size': 1
                    }
                    
            return summary
            
        except Exception as e:
            logger.error(f"❌ Erreur génération résumé config: {e}")
            return {}

# Instance globale du gestionnaire de configuration
config_manager = ConfigManager()

def get_config(config_type: str, key: str = None) -> Any:
    """Fonction utilitaire pour récupérer une configuration"""
    return config_manager.get_config(config_type, key)

def update_config(config_type: str, key: str, value: Any) -> bool:
    """Fonction utilitaire pour mettre à jour une configuration"""
    return config_manager.update_config(config_type, key, value)

def validate_all_configs() -> Dict[str, bool]:
    """Fonction utilitaire pour valider toutes les configurations"""
    return config_manager.validate_config()

if __name__ == "__main__":
    # Test du gestionnaire de configuration
    print("🔧 Test du Configuration Manager...")
    
    # Chargement de la configuration système
    system_config = config_manager.load_system_config()
    print(f"✅ Configuration système chargée: {type(system_config).__name__}")
    
    # Validation des configurations
    validation_results = config_manager.validate_config()
    print(f"✅ Validation: {validation_results}")
    
    # Résumé des configurations
    summary = config_manager.get_config_summary()
    print(f"✅ Résumé: {len(summary)} types de configurations")
    
    print("🎉 Test terminé avec succès!")


