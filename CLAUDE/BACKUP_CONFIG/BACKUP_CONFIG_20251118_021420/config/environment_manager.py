#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Environment Manager avec Overlay
===============================================

Version: Production Ready v1.0
- Gestion des environnements (dev/staging/prod)
- Chargement en couches avec overlay
- Variables d'environnement
- Configuration par défaut
- Validation des environnements

IMPACT: Gestion claire dev/staging/prod
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from core.logger import get_logger

logger = get_logger(__name__)

# === ENUMS ===

class Environment(Enum):
    """Environnements supportés"""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
    PAPER_TRADING = "paper_trading"

class ConfigLayer(Enum):
    """Couches de configuration (ordre de priorité)"""
    BASE = "base"
    ENVIRONMENT = "environment"
    SECRETS = "secrets"
    LOCAL = "local"
    RUNTIME = "runtime"

# === GESTIONNAIRE D'ENVIRONNEMENTS ===

@dataclass
class EnvironmentConfig:
    """Configuration d'un environnement"""
    name: str
    display_name: str
    is_production: bool
    debug_enabled: bool
    mock_data_enabled: bool
    performance_monitoring: bool
    error_reporting: bool
    audit_logging: bool

class EnvironmentManager:
    """
    Gestionnaire d'environnements avec overlay
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.current_env = None
        self.config_cache = {}
        self.environment_configs = self._init_environment_configs()
        
    def _init_environment_configs(self) -> Dict[str, EnvironmentConfig]:
        """Initialise les configurations d'environnements"""
        return {
            Environment.DEVELOPMENT.value: EnvironmentConfig(
                name="dev",
                display_name="Development",
                is_production=False,
                debug_enabled=True,
                mock_data_enabled=True,
                performance_monitoring=False,
                error_reporting=False,
                audit_logging=False
            ),
            Environment.STAGING.value: EnvironmentConfig(
                name="staging",
                display_name="Staging",
                is_production=False,
                debug_enabled=False,
                mock_data_enabled=False,
                performance_monitoring=True,
                error_reporting=True,
                audit_logging=False
            ),
            Environment.PRODUCTION.value: EnvironmentConfig(
                name="production",
                display_name="Production",
                is_production=True,
                debug_enabled=False,
                mock_data_enabled=False,
                performance_monitoring=True,
                error_reporting=True,
                audit_logging=True
            ),
            Environment.PAPER_TRADING.value: EnvironmentConfig(
                name="paper_trading",
                display_name="Paper Trading",
                is_production=False,
                debug_enabled=True,
                mock_data_enabled=False,
                performance_monitoring=True,
                error_reporting=True,
                audit_logging=True
            )
        }
    
    def get_current_environment(self) -> str:
        """
        Détermine l'environnement actuel
        
        Returns:
            Nom de l'environnement
        """
        # 1. Variable d'environnement MIA_ENV
        env_var = os.getenv("MIA_ENV")
        if env_var:
            if env_var in [e.value for e in Environment]:
                logger.info(f"🌍 Environnement détecté via MIA_ENV: {env_var}")
                return env_var
            else:
                logger.warning(f"⚠️ Environnement MIA_ENV invalide: {env_var}")
        
        # 2. Variable d'environnement NODE_ENV (compatibilité)
        node_env = os.getenv("NODE_ENV")
        if node_env:
            env_mapping = {
                "development": Environment.DEVELOPMENT.value,
                "staging": Environment.STAGING.value,
                "production": Environment.PRODUCTION.value
            }
            if node_env in env_mapping:
                env = env_mapping[node_env]
                logger.info(f"🌍 Environnement détecté via NODE_ENV: {env}")
                return env
        
        # 3. Fichier .env local
        env_file = self.config_dir / ".env"
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("MIA_ENV="):
                            env = line.split("=", 1)[1].strip()
                            if env in [e.value for e in Environment]:
                                logger.info(f"🌍 Environnement détecté via .env: {env}")
                                return env
            except Exception as e:
                logger.warning(f"⚠️ Erreur lecture .env: {e}")
        
        # 4. Détection automatique
        if os.path.exists("/etc/mia/production"):
            logger.info("🌍 Environnement détecté automatiquement: production")
            return Environment.PRODUCTION.value
        
        # 5. Défaut: développement
        logger.info("🌍 Environnement par défaut: development")
        return Environment.DEVELOPMENT.value
    
    def load_config_with_overlay(self, base_file: str, env: str = None) -> Dict[str, Any]:
        """
        Charge une configuration avec overlay d'environnement
        
        Args:
            base_file: Fichier de base
            env: Environnement (optionnel)
            
        Returns:
            Configuration avec overlay
        """
        if env is None:
            env = self.get_current_environment()
        
        self.current_env = env
        
        # Cache key
        cache_key = f"{base_file}_{env}"
        if cache_key in self.config_cache:
            logger.debug(f"📋 Cache hit pour {cache_key}")
            return self.config_cache[cache_key]
        
        # Charger la configuration de base
        base_config = self._load_config_file(base_file)
        if not base_config:
            logger.error(f"❌ Impossible de charger la configuration de base: {base_file}")
            return {}
        
        # Charger l'overlay d'environnement
        overlay_config = self._load_environment_overlay(base_file, env)
        
        # Fusionner les configurations
        merged_config = self._deep_merge(base_config, overlay_config)
        
        # Charger les secrets (si disponibles)
        secrets_config = self._load_secrets_config(env)
        if secrets_config:
            merged_config = self._deep_merge(merged_config, secrets_config)
        
        # Charger la configuration locale (si disponible)
        local_config = self._load_local_config(base_file)
        if local_config:
            merged_config = self._deep_merge(merged_config, local_config)
        
        # Appliquer les overrides runtime
        runtime_config = self._get_runtime_overrides()
        if runtime_config:
            merged_config = self._deep_merge(merged_config, runtime_config)
        
        # Mettre en cache
        self.config_cache[cache_key] = merged_config
        
        logger.info(f"✅ Configuration chargée avec overlay {env}")
        return merged_config
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Charge un fichier de configuration"""
        try:
            full_path = self.config_dir / file_path
            if not full_path.exists():
                logger.warning(f"⚠️ Fichier de configuration non trouvé: {full_path}")
                return {}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                if full_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                else:
                    return json.load(f)
                    
        except Exception as e:
            logger.error(f"❌ Erreur chargement {file_path}: {e}")
            return {}
    
    def _load_environment_overlay(self, base_file: str, env: str) -> Dict[str, Any]:
        """Charge l'overlay d'environnement"""
        # Construire le nom du fichier d'overlay
        base_name = Path(base_file).stem
        overlay_file = f"{base_name}.{env}.json"
        
        return self._load_config_file(overlay_file)
    
    def _load_secrets_config(self, env: str) -> Dict[str, Any]:
        """Charge la configuration des secrets"""
        secrets_file = f"secrets.{env}.json"
        return self._load_config_file(secrets_file)
    
    def _load_local_config(self, base_file: str) -> Dict[str, Any]:
        """Charge la configuration locale"""
        base_name = Path(base_file).stem
        local_file = f"{base_name}.local.json"
        return self._load_config_file(local_file)
    
    def _get_runtime_overrides(self) -> Dict[str, Any]:
        """Récupère les overrides runtime depuis les variables d'environnement"""
        overrides = {}
        
        # Variables d'environnement avec préfixe MIA_CONFIG_
        for key, value in os.environ.items():
            if key.startswith("MIA_CONFIG_"):
                config_key = key[11:].lower()  # Enlever MIA_CONFIG_
                overrides[config_key] = self._parse_env_value(value)
        
        return overrides
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse une valeur d'environnement"""
        # Booléens
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Nombres
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Chaînes
        return value
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne deux dictionnaires de manière récursive"""
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_environment_config(self, env: str = None) -> EnvironmentConfig:
        """
        Récupère la configuration d'un environnement
        
        Args:
            env: Nom de l'environnement
            
        Returns:
            Configuration de l'environnement
        """
        if env is None:
            env = self.get_current_environment()
        
        return self.environment_configs.get(env, self.environment_configs[Environment.DEVELOPMENT.value])
    
    def validate_environment(self, env: str) -> bool:
        """
        Valide qu'un environnement est supporté
        
        Args:
            env: Nom de l'environnement
            
        Returns:
            True si valide
        """
        return env in [e.value for e in Environment]
    
    def list_available_environments(self) -> List[str]:
        """
        Liste les environnements disponibles
        
        Returns:
            Liste des environnements
        """
        return [e.value for e in Environment]
    
    def clear_cache(self):
        """Vide le cache de configuration"""
        self.config_cache.clear()
        logger.info("🗑️ Cache de configuration vidé")

# === INSTANCE GLOBALE ===

_env_manager = EnvironmentManager()

def get_current_environment() -> str:
    """Récupère l'environnement actuel"""
    return _env_manager.get_current_environment()

def load_config_with_environment(base_file: str, env: str = None) -> Dict[str, Any]:
    """Charge une configuration avec overlay d'environnement"""
    return _env_manager.load_config_with_overlay(base_file, env)

def get_environment_config(env: str = None) -> EnvironmentConfig:
    """Récupère la configuration d'un environnement"""
    return _env_manager.get_environment_config(env)

def validate_environment(env: str) -> bool:
    """Valide qu'un environnement est supporté"""
    return _env_manager.validate_environment(env)

# === FONCTIONS DE CONVENIENCE ===

def is_production() -> bool:
    """Vérifie si on est en production"""
    return get_environment_config().is_production

def is_development() -> bool:
    """Vérifie si on est en développement"""
    return get_current_environment() == Environment.DEVELOPMENT.value

def is_staging() -> bool:
    """Vérifie si on est en staging"""
    return get_current_environment() == Environment.STAGING.value

def is_debug_enabled() -> bool:
    """Vérifie si le debug est activé"""
    return get_environment_config().debug_enabled

def is_mock_data_enabled() -> bool:
    """Vérifie si les données mock sont activées"""
    return get_environment_config().mock_data_enabled

# === TEST DU GESTIONNAIRE D'ENVIRONNEMENTS ===

if __name__ == "__main__":
    print("🧪 Test du Environment Manager...")
    
    # Test détection environnement
    current_env = get_current_environment()
    print(f"✅ Environnement actuel: {current_env}")
    
    # Test configuration d'environnement
    env_config = get_environment_config()
    print(f"✅ Config environnement: {env_config.display_name}")
    print(f"   - Debug: {env_config.debug_enabled}")
    print(f"   - Mock data: {env_config.mock_data_enabled}")
    print(f"   - Production: {env_config.is_production}")
    
    # Test chargement avec overlay
    config = load_config_with_environment("feature_config.base.json")
    print(f"✅ Configuration chargée: {len(config)} sections")
    
    # Test fonctions de convenience
    print(f"✅ Is production: {is_production()}")
    print(f"✅ Is development: {is_development()}")
    print(f"✅ Debug enabled: {is_debug_enabled()}")
    print(f"✅ Mock data enabled: {is_mock_data_enabled()}")
    
    # Test environnements disponibles
    available_envs = _env_manager.list_available_environments()
    print(f"✅ Environnements disponibles: {available_envs}")
    
    print("🎉 Test Environment Manager terminé avec succès!")
