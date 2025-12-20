#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Configuration Loader avec dotify
Version: Production Ready

Gestionnaire de configuration avec support dot-accessible
et validation des clés inconnues
"""

import json
import yaml
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, Optional, List
from core.logger import get_logger

logger = get_logger(__name__)

def dotify(d):
    """
    Convertit un dictionnaire en namespace dot-accessible récursivement

    Args:
        d: Dictionnaire à convertir

    Returns:
        SimpleNamespace avec accès dot
    """
    if isinstance(d, dict):
        return SimpleNamespace(**{k: dotify(v) for k, v in d.items()})
    if isinstance(d, list):
        return [dotify(x) for x in d]
    return d

def require_keys(ns, allowed: List[str], config_name: str = "config"):
    """
    Valide que seules les clés autorisées sont présentes

    Args:
        ns: Namespace à valider
        allowed: Liste des clés autorisées
        config_name: Nom de la configuration pour les logs
    """
    if not isinstance(ns, SimpleNamespace):
        return

    extra = [k for k in vars(ns).keys() if k not in allowed]
    if extra:
        logger.warning(f"⚠️ Clés de config ignorées dans {config_name}: {extra}")

def load_config_file(file_path: str, config_name: str = None) -> SimpleNamespace:
    """
    Charge un fichier de configuration et le convertit en namespace dot-accessible

    Args:
        file_path: Chemin vers le fichier de config
        config_name: Nom de la configuration (pour logs)

    Returns:
        SimpleNamespace avec accès dot
    """
    if config_name is None:
        config_name = Path(file_path).stem

    try:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"❌ Fichier de config introuvable: {file_path}")
            return SimpleNamespace()

        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f) or {}
            else:
                data = json.load(f)

        # Convertir en namespace dot-accessible
        config = dotify(data)
        logger.info(f"✅ Configuration {config_name} chargée depuis {file_path}")
        return config

    except Exception as e:
        logger.error(f"❌ Erreur chargement config {config_name}: {e}")
        return SimpleNamespace()

def load_feature_config() -> SimpleNamespace:
    """
    Charge la configuration des features avec validation

    Returns:
        Configuration des features en format dot-accessible
    """
    config = load_config_file("config/feature_config.json", "features")

    # Validation des clés principales
    main_sections = [
        'confluence', 'menthorq', 'order_book', 'volume_profile',
        'vwap', 'vix', 'nbcv', 'feature_weights', 'thresholds',
        'data_sources', 'advanced', 'live_mode', 'LIVE_DATA_READER'
    ]

    require_keys(config, main_sections, "features")

    return config

def load_trading_config() -> SimpleNamespace:
    """
    Charge la configuration trading

    Returns:
        Configuration trading en format dot-accessible
    """
    return load_config_file("config/trading_config.py", "trading")

def load_automation_config() -> SimpleNamespace:
    """
    Charge la configuration automation

    Returns:
        Configuration automation en format dot-accessible
    """
    return load_config_file("config/automation_config.py", "automation")

def validate_config_compatibility(config: SimpleNamespace, expected_keys: List[str]) -> bool:
    """
    Valide la compatibilité d'une configuration

    Args:
        config: Configuration à valider
        expected_keys: Clés attendues

    Returns:
        True si compatible
    """
    if not isinstance(config, SimpleNamespace):
        logger.error("❌ Configuration doit être un SimpleNamespace")
        return False

    missing = [k for k in expected_keys if not hasattr(config, k)]
    if missing:
        logger.error(f"❌ Clés manquantes dans la configuration: {missing}")
        return False

    return True

# Instance globale pour cache
_feature_config_cache: Optional[SimpleNamespace] = None

def get_feature_config() -> SimpleNamespace:
    """
    Récupère la configuration des features (avec cache)

    Returns:
        Configuration des features
    """
    global _feature_config_cache

    if _feature_config_cache is None:
        _feature_config_cache = load_feature_config()

    return _feature_config_cache

def reload_feature_config() -> SimpleNamespace:
    """
    Recharge la configuration des features (force refresh)

    Returns:
        Configuration des features mise à jour
    """
    global _feature_config_cache
    _feature_config_cache = load_feature_config()
    return _feature_config_cache

# Test de la configuration
if __name__ == "__main__":
    print("🧪 Test du Configuration Loader...")

    # Test chargement feature config
    feature_config = load_feature_config()
    print(f"✅ Feature config chargée: {type(feature_config).__name__}")

    # Test accès dot
    if hasattr(feature_config, 'vwap'):
        print(f"✅ Accès dot OK: vwap.max_history = {getattr(feature_config.vwap, 'max_history', 'N/A')}")

    # Test validation
    expected_keys = ['vwap', 'volume_profile', 'nbcv']
    is_valid = validate_config_compatibility(feature_config, expected_keys)
    print(f"✅ Validation: {'OK' if is_valid else 'ERREUR'}")

    print("🎉 Test terminé avec succès!")
