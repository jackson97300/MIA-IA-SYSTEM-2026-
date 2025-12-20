#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Configuration Module
Version: Phase 3B - Configuration Management & Automation + Post-Mortem
Responsabilité: Gestion centralisée toutes configurations système + Support Post-Mortem Analysis

COMPOSANTS PRINCIPAUX :
1. [STATS] Trading Parameters - Paramètres de base trading
2. [SHIELD] Risk Management - Configuration gestion risque
3. [TARGET] Feature Configuration - Paramètres features & signaux  
4. [BOT] Automation Parameters - Configuration automation live
5. [BRAIN] ML Training Config - Paramètres machine learning
6. [UP] Monitoring Config - Configuration monitoring système
7. 🆕 [ANALYSIS] Post-Mortem Config - Configuration analyse post-mortem

WORKFLOW CONFIGURATION :
Load → Validate → Apply → Monitor → Adapt

PHILOSOPHIE CONFIGURATION :
- Environment-aware (dev/staging/production)
- Validation automatique cohérence
- Sécurité paramètres par défaut
- Hot reload sans redémarrage
- Backup automatique changements
- Support complet post-mortem analysis
"""

import os
import json
from core.logger import get_logger
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# === CONFIGURATION ENUMS ===

class ConfigType(Enum):
    """Types de configurations disponibles"""
    TRADING_PARAMS = "trading_params"
    RISK_PARAMS = "risk_params"
    FEATURE_CONFIG = "feature_config"
    AUTOMATION_PARAMS = "automation_params"
    ML_TRAINING_CONFIG = "ml_training_config"
    MONITORING_CONFIG = "monitoring_config"

class Environment(Enum):
    """Environnements disponibles"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class ValidationLevel(Enum):
    """Niveaux de validation"""
    BASIC = "basic"
    STRICT = "strict"
    PRODUCTION = "production"

# === CONFIGURATION MANAGER ===

logger = get_logger(__name__)

class ConfigManager:
    """
    CONFIGURATION MANAGER - Gestionnaire centralisé configurations
    
    Responsabilités :
    1. Chargement/sauvegarde configurations JSON
    2. Validation cohérence inter-configurations
    3. Gestion environnements (dev/staging/prod)
    4. Hot reload configurations
    5. Backup automatique
    6. 🆕 Support configuration post-mortem
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialisation Configuration Manager
        
        Args:
            config_dir: Répertoire configurations (optionnel)
        """
        # Utiliser config_files/ comme répertoire par défaut
        if config_dir is None:
            base_dir = Path(__file__).parent.parent  # Remonter au niveau MIA_IA_system/
            config_dir = base_dir / "config_files"
        
        self.config_dir = config_dir
        self.configs: Dict[str, Dict] = {}
        self.environment = Environment.DEVELOPMENT
        self.validation_level = ValidationLevel.BASIC
        self.backup_dir = self.config_dir / "backups"
        
        # Création directories
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Fichiers de configuration
        self.config_files = {
            ConfigType.TRADING_PARAMS: "trading_params.json",
            ConfigType.RISK_PARAMS: "risk_params.json", 
            ConfigType.FEATURE_CONFIG: "feature_config.json",
            ConfigType.AUTOMATION_PARAMS: "automation_params.json",
            ConfigType.ML_TRAINING_CONFIG: "ml_training_config.json",
            ConfigType.MONITORING_CONFIG: "monitoring_config.json"
        }
        
        # Chargement initial
        self._load_all_configs()
        
        logger.info(f"ConfigManager initialisé: {self.config_dir}")
        logger.info("🔍 Support Post-Mortem: ACTIVÉ")
    
    def load_config(self, config_type: ConfigType) -> Dict[str, Any]:
        """
        CHARGEMENT CONFIGURATION SPÉCIFIQUE
        
        Args:
            config_type: Type de configuration à charger
            
        Returns:
            Dict: Configuration chargée
        """
        try:
            filename = self.config_files[config_type]
            config_path = self.config_dir / filename
            
            if not config_path.exists():
                logger.warning(f"Config file not found: {filename}")
                return self._get_default_config(config_type)
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validation
            if self._validate_config(config_type, config):
                self.configs[config_type.value] = config
                logger.info(f"Configuration chargée: {config_type.value}")
                return config
            else:
                logger.error(f"Validation échouée: {config_type.value}")
                return self._get_default_config(config_type)
                
        except Exception as e:
            logger.error(f"Erreur chargement {config_type.value}: {e}")
            return self._get_default_config(config_type)
    
    def save_config(self, config_type: ConfigType, config: Dict[str, Any], 
                   backup: bool = True) -> bool:
        """
        SAUVEGARDE CONFIGURATION
        
        Args:
            config_type: Type de configuration
            config: Configuration à sauvegarder
            backup: Créer backup avant sauvegarde
            
        Returns:
            bool: Succès de la sauvegarde
        """
        try:
            filename = self.config_files[config_type]
            config_path = self.config_dir / filename
            
            # Backup si demandé
            if backup and config_path.exists():
                self._create_backup(config_type)
            
            # Validation avant sauvegarde
            if not self._validate_config(config_type, config):
                logger.error(f"Validation échouée pour sauvegarde: {config_type.value}")
                return False
            
            # Sauvegarde
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Mise à jour cache
            self.configs[config_type.value] = config
            
            logger.info(f"Configuration sauvegardée: {config_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde {config_type.value}: {e}")
            return False
    
    def get_config(self, config_type: ConfigType) -> Dict[str, Any]:
        """
        RÉCUPÉRATION CONFIGURATION
        
        Args:
            config_type: Type de configuration
            
        Returns:
            Dict: Configuration demandée
        """
        if config_type.value not in self.configs:
            return self.load_config(config_type)
        
        return self.configs[config_type.value]
    
    def update_config(self, config_type: ConfigType, updates: Dict[str, Any]) -> bool:
        """
        MISE À JOUR CONFIGURATION PARTIELLE
        
        Args:
            config_type: Type de configuration
            updates: Mises à jour à appliquer
            
        Returns:
            bool: Succès de la mise à jour
        """
        try:
            current_config = self.get_config(config_type)
            
            # Merge updates
            updated_config = self._deep_merge(current_config, updates)
            
            # Sauvegarde
            return self.save_config(config_type, updated_config)
            
        except Exception as e:
            logger.error(f"Erreur update_config {config_type.value}: {e}")
            return False
    
    def validate_all_configs(self) -> Dict[str, bool]:
        """
        VALIDATION TOUTES CONFIGURATIONS
        
        Returns:
            Dict: Résultats validation par config
        """
        results = {}
        
        for config_type in ConfigType:
            config = self.get_config(config_type)
            results[config_type.value] = self._validate_config(config_type, config)
        
        # Validation croisée
        results['cross_validation'] = self._cross_validate_configs()
        
        # 🆕 Validation post-mortem
        results['post_mortem_validation'] = self._validate_post_mortem_config()
        
        return results
    
    def set_environment(self, environment: Environment) -> None:
        """
        DÉFINITION ENVIRONNEMENT
        
        Args:
            environment: Nouvel environnement
        """
        self.environment = environment
        
        # Ajustement niveau validation selon environnement
        if environment == Environment.PRODUCTION:
            self.validation_level = ValidationLevel.PRODUCTION
        elif environment == Environment.STAGING:
            self.validation_level = ValidationLevel.STRICT
        else:
            self.validation_level = ValidationLevel.BASIC
        
        logger.info(f"Environnement: {environment.value}, validation: {self.validation_level.value}")
    
    # 🆕 NOUVELLES MÉTHODES POST-MORTEM
    
    def get_post_mortem_config(self) -> Dict[str, Any]:
        """
        Récupère configuration post-mortem depuis automation_params.json
        
        Returns:
            Dict: Configuration post-mortem
        """
        automation_config = self.get_config(ConfigType.AUTOMATION_PARAMS)
        return automation_config.get('post_mortem_analysis', {})
    
    def update_post_mortem_config(self, updates: Dict[str, Any]) -> bool:
        """
        Met à jour configuration post-mortem
        
        Args:
            updates: Mises à jour configuration post-mortem
            
        Returns:
            bool: Succès de la mise à jour
        """
        try:
            automation_config = self.get_config(ConfigType.AUTOMATION_PARAMS)
            
            if 'post_mortem_analysis' not in automation_config:
                automation_config['post_mortem_analysis'] = {}
            
            # Merge des updates dans la section post-mortem
            automation_config['post_mortem_analysis'] = self._deep_merge(
                automation_config['post_mortem_analysis'], 
                updates
            )
            
            return self.save_config(ConfigType.AUTOMATION_PARAMS, automation_config)
            
        except Exception as e:
            logger.error(f"Erreur update post-mortem config: {e}")
            return False
    
    def is_post_mortem_enabled(self) -> bool:
        """
        Vérifie si post-mortem est activé
        
        Returns:
            bool: Post-mortem activé
        """
        post_mortem_config = self.get_post_mortem_config()
        return post_mortem_config.get('enabled', False)
    
    def get_post_mortem_tracking_duration(self, trade_outcome: str) -> int:
        """
        Récupère durée tracking pour un type de trade
        
        Args:
            trade_outcome: Type de trade ('winning', 'losing', 'breakeven')
            
        Returns:
            int: Durée en minutes
        """
        post_mortem_config = self.get_post_mortem_config()
        durations = post_mortem_config.get('tracking_durations', {})
        
        default_durations = {
            'winning': 20,
            'losing': 15,
            'breakeven': 12
        }
        
        key = f"{trade_outcome}_trades_minutes"
        return durations.get(key, default_durations.get(trade_outcome, 15))
    
    def get_post_mortem_pattern_threshold(self) -> int:
        """
        Récupère seuil détection patterns
        
        Returns:
            int: Nombre d'occurrences pour déclencher alerte
        """
        post_mortem_config = self.get_post_mortem_config()
        pattern_config = post_mortem_config.get('pattern_detection', {})
        return pattern_config.get('alert_threshold', 3)
    
    def get_status(self) -> Dict[str, Any]:
        """Status du gestionnaire de configuration"""
        post_mortem_config = self.get_post_mortem_config()
        
        return {
            'environment': self.environment.value,
            'validation_level': self.validation_level.value,
            'configs_loaded': len(self.configs),
            'config_dir': str(self.config_dir),
            'backup_dir': str(self.backup_dir),
            'last_validation': self.validate_all_configs(),
            'post_mortem_enabled': self.is_post_mortem_enabled(),
            'post_mortem_features': {
                'tracking_enabled': post_mortem_config.get('tracking_configuration', {}).get('analyze_all_trades', False),
                'pattern_detection': post_mortem_config.get('pattern_detection', {}).get('enabled', False),
                'discord_notifications': post_mortem_config.get('discord_notifications', {}).get('enabled', False),
                'ml_integration': post_mortem_config.get('machine_learning_integration', {}).get('enabled', False)
            }
        }
    
    # === PRIVATE METHODS ===
    
    def _load_all_configs(self):
        """Chargement de toutes les configurations"""
        for config_type in ConfigType:
            self.load_config(config_type)
    
    def _validate_config(self, config_type: ConfigType, config: Dict[str, Any]) -> bool:
        """
        VALIDATION CONFIGURATION SPÉCIFIQUE
        
        Args:
            config_type: Type de configuration
            config: Configuration à valider
            
        Returns:
            bool: Configuration valide
        """
        try:
            if config_type == ConfigType.TRADING_PARAMS:
                return self._validate_trading_params(config)
            elif config_type == ConfigType.RISK_PARAMS:
                return self._validate_risk_params(config)
            elif config_type == ConfigType.FEATURE_CONFIG:
                return self._validate_feature_config(config)
            elif config_type == ConfigType.AUTOMATION_PARAMS:
                return self._validate_automation_params(config)
            elif config_type == ConfigType.ML_TRAINING_CONFIG:
                return self._validate_ml_config(config)
            elif config_type == ConfigType.MONITORING_CONFIG:
                return self._validate_monitoring_config(config)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation {config_type.value}: {e}")
            return False
    
    def _validate_trading_params(self, config: Dict) -> bool:
        """Validation paramètres trading"""
        required_keys = ['symbols', 'timeframes', 'session_hours']
        return all(key in config for key in required_keys)
    
    def _validate_risk_params(self, config: Dict) -> bool:
        """Validation paramètres risque"""
        required_keys = ['max_position_size', 'stop_loss', 'daily_loss_limit']
        return all(key in config for key in required_keys)
    
    def _validate_feature_config(self, config: Dict) -> bool:
        """Validation configuration features"""
        required_keys = ['features_enabled', 'feature_weights', 'confidence_thresholds']
        return all(key in config for key in required_keys)
    
    def _validate_automation_params(self, config: Dict) -> bool:
        """Validation paramètres automation + post-mortem"""
        if 'automation' not in config:
            return False
        
        automation = config['automation']
        required_keys = ['enabled', 'mode', 'max_position_size']
        
        # Validation automation de base
        if not all(key in automation for key in required_keys):
            return False
        
        # 🆕 Validation post-mortem si présent
        if 'post_mortem_analysis' in config:
            return self._validate_post_mortem_section(config['post_mortem_analysis'])
        
        return True
    
    def _validate_ml_config(self, config: Dict) -> bool:
        """Validation configuration ML"""
        if 'model' not in config:
            return False
        
        model = config['model']
        required_keys = ['type', 'retrain_frequency']
        return all(key in model for key in required_keys)
    
    def _validate_monitoring_config(self, config: Dict) -> bool:
        """Validation configuration monitoring"""
        if 'monitoring' not in config:
            return False
        
        monitoring = config['monitoring']
        required_keys = ['enabled', 'update_frequency_seconds']
        return all(key in monitoring for key in required_keys)
    
    # 🆕 NOUVELLE MÉTHODE
    def _validate_post_mortem_section(self, post_mortem_config: Dict) -> bool:
        """
        Validation section post-mortem
        
        Args:
            post_mortem_config: Configuration post-mortem à valider
            
        Returns:
            bool: Configuration valide
        """
        try:
            # Clés requises
            required_sections = [
                'enabled', 'tracking_configuration', 'tracking_durations',
                'analysis_criteria', 'pattern_detection', 'discord_notifications'
            ]
            
            if not all(section in post_mortem_config for section in required_sections):
                logger.error("Sections manquantes dans post_mortem_analysis")
                return False
            
            # Validation tracking_durations
            durations = post_mortem_config.get('tracking_durations', {})
            required_durations = ['winning_trades_minutes', 'losing_trades_minutes', 'breakeven_trades_minutes']
            
            if not all(key in durations for key in required_durations):
                logger.error("Durées tracking manquantes")
                return False
            
            # Validation valeurs numériques
            for key in required_durations:
                if not isinstance(durations[key], (int, float)) or durations[key] <= 0:
                    logger.error(f"Durée invalide: {key}")
                    return False
            
            # Validation pattern_detection
            pattern_config = post_mortem_config.get('pattern_detection', {})
            if 'alert_threshold' in pattern_config:
                threshold = pattern_config['alert_threshold']
                if not isinstance(threshold, int) or threshold < 1:
                    logger.error("Seuil pattern detection invalide")
                    return False
            
            logger.info("Configuration post-mortem validée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation post-mortem: {e}")
            return False
    
    # 🆕 NOUVELLE MÉTHODE
    def _validate_post_mortem_config(self) -> bool:
        """
        Validation globale configuration post-mortem
        
        Returns:
            bool: Configuration post-mortem valide
        """
        try:
            post_mortem_config = self.get_post_mortem_config()
            
            if not post_mortem_config:
                logger.warning("Aucune configuration post-mortem trouvée")
                return True  # Optionnel
            
            return self._validate_post_mortem_section(post_mortem_config)
            
        except Exception as e:
            logger.error(f"Erreur validation post-mortem globale: {e}")
            return False
    
    def _cross_validate_configs(self) -> bool:
        """Validation croisée entre configurations"""
        try:
            # Validation cohérence automation + risk
            automation_config = self.get_config(ConfigType.AUTOMATION_PARAMS)
            risk_config = self.get_config(ConfigType.RISK_PARAMS)
            
            if automation_config.get('automation', {}).get('enabled', False):
                automation_max_pos = automation_config.get('automation', {}).get('max_position_size', 0)
                risk_max_pos = risk_config.get('max_position_size', 0)
                
                if automation_max_pos > risk_max_pos:
                    logger.error("Position size automation > risk limit")
                    return False
            
            # 🆕 Validation post-mortem + environment
            if self.is_post_mortem_enabled():
                post_mortem_config = self.get_post_mortem_config()
                
                # En production, certaines options doivent être activées
                if self.environment == Environment.PRODUCTION:
                    pattern_detection = post_mortem_config.get('pattern_detection', {}).get('enabled', False)
                    if not pattern_detection:
                        logger.warning("Pattern detection recommandé en production")
                
                # Validation durées cohérentes
                durations = post_mortem_config.get('tracking_durations', {})
                winning_duration = durations.get('winning_trades_minutes', 20)
                losing_duration = durations.get('losing_trades_minutes', 15)
                
                if winning_duration < losing_duration:
                    logger.warning("Durée tracking gagnants < perdants (inhabituel)")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur cross validation: {e}")
            return False
    
    def _get_default_config(self, config_type: ConfigType) -> Dict[str, Any]:
        """Configuration par défaut pour un type"""
        defaults = {
            ConfigType.TRADING_PARAMS: {
                "symbols": ["ES"],
                "timeframes": ["1min", "5min"],
                "session_hours": {"start": 9, "end": 16}
            },
            ConfigType.RISK_PARAMS: {
                "max_position_size": 1,
                "stop_loss": 10.0,
                "daily_loss_limit": 500.0
            },
            ConfigType.FEATURE_CONFIG: {
                "features_enabled": True,
                "feature_weights": {},
                "confidence_thresholds": {}
            },
            ConfigType.AUTOMATION_PARAMS: {
                "automation": {
                    "enabled": False,
                    "mode": "paper_trading",
                    "max_position_size": 1
                },
                # 🆕 Configuration post-mortem par défaut
                "post_mortem_analysis": {
                    "enabled": True,
                    "tracking_configuration": {
                        "analyze_all_trades": True,
                        "analyze_winning_trades": True,
                        "analyze_losing_trades": True,
                        "analyze_breakeven_trades": True
                    },
                    "tracking_durations": {
                        "winning_trades_minutes": 20,
                        "losing_trades_minutes": 15,
                        "breakeven_trades_minutes": 12
                    },
                    "analysis_criteria": {
                        "profit_efficiency_analysis": True,
                        "stop_justification_analysis": True,
                        "exit_timing_analysis": True
                    },
                    "pattern_detection": {
                        "enabled": True,
                        "alert_threshold": 3,
                        "lookback_trades": 10
                    },
                    "discord_notifications": {
                        "immediate_notification": True,
                        "final_analysis_notification": True,
                        "pattern_alerts": True
                    }
                }
            },
            ConfigType.ML_TRAINING_CONFIG: {
                "model": {
                    "type": "linear",
                    "retrain_frequency": 50
                }
            },
            ConfigType.MONITORING_CONFIG: {
                "monitoring": {
                    "enabled": True,
                    "update_frequency_seconds": 5
                }
            }
        }
        
        return defaults.get(config_type, {})
    
    def _create_backup(self, config_type: ConfigType):
        """Création backup configuration"""
        try:
            filename = self.config_files[config_type]
            config_path = self.config_dir / filename
            
            if config_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{config_type.value}_{timestamp}.json"
                backup_path = self.backup_dir / backup_filename
                
                with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
                
                logger.info(f"Backup créé: {backup_filename}")
                
        except Exception as e:
            logger.error(f"Erreur création backup: {e}")
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """Fusion profonde de dictionnaires"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result

# === GLOBAL INSTANCE ===

_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Récupération instance globale ConfigManager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

# === CONVENIENCE FUNCTIONS ===

def load_trading_params() -> Dict[str, Any]:
    """Chargement paramètres trading"""
    return get_config_manager().get_config(ConfigType.TRADING_PARAMS)

def load_risk_params() -> Dict[str, Any]:
    """Chargement paramètres risque"""
    return get_config_manager().get_config(ConfigType.RISK_PARAMS)

def load_feature_config() -> Dict[str, Any]:
    """Chargement configuration features"""
    return get_config_manager().get_config(ConfigType.FEATURE_CONFIG)

def load_automation_params() -> Dict[str, Any]:
    """Chargement paramètres automation"""
    return get_config_manager().get_config(ConfigType.AUTOMATION_PARAMS)

def load_ml_training_config() -> Dict[str, Any]:
    """Chargement configuration ML"""
    return get_config_manager().get_config(ConfigType.ML_TRAINING_CONFIG)

def load_monitoring_config() -> Dict[str, Any]:
    """Chargement configuration monitoring"""
    return get_config_manager().get_config(ConfigType.MONITORING_CONFIG)

# 🆕 NOUVELLES FONCTIONS POST-MORTEM

def load_post_mortem_config() -> Dict[str, Any]:
    """Chargement configuration post-mortem"""
    return get_config_manager().get_post_mortem_config()

def is_post_mortem_enabled() -> bool:
    """Vérifie si post-mortem est activé"""
    return get_config_manager().is_post_mortem_enabled()

def get_post_mortem_tracking_duration(trade_outcome: str) -> int:
    """Récupère durée tracking post-mortem"""
    return get_config_manager().get_post_mortem_tracking_duration(trade_outcome)

def update_post_mortem_config(updates: Dict[str, Any]) -> bool:
    """Met à jour configuration post-mortem"""
    return get_config_manager().update_post_mortem_config(updates)

# === COMPATIBILITY FUNCTION ===

def get_automation_config() -> Dict[str, Any]:
    """
    Fonction de compatibilité pour automation_config.py
    
    Returns:
        Dict: Configuration automation complète
    """
    return load_automation_params()

# === EXPORTS ===

__all__ = [
    # Main classes
    'ConfigManager',
    'ConfigType',
    'Environment', 
    'ValidationLevel',
    
    # Functions de base
    'get_config_manager',
    'load_trading_params',
    'load_risk_params',
    'load_feature_config',
    'load_automation_params',
    'load_ml_training_config',
    'load_monitoring_config',
    
    # 🆕 Fonctions post-mortem
    'load_post_mortem_config',
    'is_post_mortem_enabled',
    'get_post_mortem_tracking_duration',
    'update_post_mortem_config',
    
    # Compatibility
    'get_automation_config'
]

# === MODULE INFO ===

__version__ = "3.2.2"
__author__ = "MIA_IA_SYSTEM"

# Log de chargement
logger.info(f"Module Configuration {__version__} chargé - Automation + Post-Mortem Focus")
logger.info("🔍 Support Post-Mortem Analysis: INTÉGRÉ")

# === END MODULE ===