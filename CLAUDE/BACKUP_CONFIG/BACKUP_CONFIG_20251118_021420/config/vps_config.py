# 🚀 CONFIGURATION VPS - SYSTÈME MIA IA
# Configuration spécifique pour le déploiement sur VPS
# Version: 1.0

import os
from pathlib import Path
from typing import Dict, Any

# ========================================
# CONFIGURATION GÉNÉRALE VPS
# ========================================

# Environnement VPS
VPS_ENVIRONMENT = {
    "is_vps": True,
    "vps_provider": "QuantVPS",  # QuantVPS, AWS, Azure, GCP
    "vps_location": "Chicago",   # Chicago, Virginia, Oregon
    "vps_latency_cme": 0.52,     # Latence vers CME en ms
    "vps_ram_gb": 32,            # RAM disponible en GB
    "vps_cpu_cores": 8,          # Nombre de cœurs CPU
    "vps_storage_gb": 200,       # Stockage disponible en GB
}

# ========================================
# CHEMINS VPS
# ========================================

# Répertoires principaux
VPS_PATHS = {
    "project_root": Path("C:/MIA_IA_system"),
    "sierra_chart": Path("C:/SierraChart"),
    "data_sierra": Path("C:/MIA_IA_system/DATA_SIERRA_CHART"),
    "logs": Path("C:/MIA_IA_system/logs"),
    "results": Path("C:/MIA_IA_system/results"),
    "temp": Path("C:/MIA_IA_system/temp"),
    "config_files": Path("C:/MIA_IA_system/config_files"),
    "backups": Path("C:/Backups/MIA_IA"),
    "venv": Path("C:/MIA_IA_system/venv"),
}

# ========================================
# CONFIGURATION SIERRA CHART VPS
# ========================================

SIERRA_CHART_VPS = {
    "installation_path": "C:/SierraChart",
    "data_path": "C:/SierraChart/Data",
    "studies_path": "C:/SierraChart/Data",
    "charts_config": {
        "chart_3": {
            "symbol": "ESU25_FUT_CME",
            "timeframe": "1 minute",
            "studies": ["MIA_Chart_Dumper_patched"],
            "output_files": [
                "chart_3_basedata_{date}.jsonl",
                "chart_3_vwap_{date}.jsonl",
                "chart_3_nbcv_{date}.jsonl",
                "chart_3_cumulative_delta_{date}.jsonl",
                "chart_3_depth_{date}.jsonl",
                "chart_3_trade_{date}.jsonl",
                "chart_3_quote_{date}.jsonl"
            ]
        },
        "chart_4": {
            "symbol": "ESU25_FUT_CME",
            "timeframe": "30 minutes",
            "studies": ["VWAP", "PVWAP"],
            "output_files": [
                "chart_4_basedata_{date}.jsonl",
                "chart_4_vwap_{date}.jsonl",
                "chart_4_pvwap_{date}.jsonl"
            ]
        },
        "chart_8": {
            "symbol": "VIX",
            "timeframe": "1 minute",
            "studies": ["VIX Policy"],
            "output_files": [
                "chart_8_vix_{date}.jsonl",
                "chart_8_policy_{date}.jsonl"
            ]
        },
        "chart_10": {
            "symbol": "ESU25_FUT_CME",
            "timeframe": "1 minute",
            "studies": ["MenthorQ Gamma", "MenthorQ Blind Spots", "MenthorQ Swings"],
            "output_files": [
                "chart_10_menthorq_{date}.jsonl",
                "chart_10_gamma_{date}.jsonl",
                "chart_10_blind_spots_{date}.jsonl",
                "chart_10_swings_{date}.jsonl"
            ]
        }
    }
}

# ========================================
# CONFIGURATION RÉSEAU VPS
# ========================================

VPS_NETWORK = {
    "rdp_port": 3389,
    "mia_http_port": 8080,
    "mia_https_port": 8443,
    "syncthing_port": 8384,
    "firewall_rules": [
        {"name": "RDP", "port": 3389, "protocol": "TCP", "action": "allow"},
        {"name": "MIA_HTTP", "port": 8080, "protocol": "TCP", "action": "allow"},
        {"name": "MIA_HTTPS", "port": 8443, "protocol": "TCP", "action": "allow"},
        {"name": "Syncthing", "port": 8384, "protocol": "TCP", "action": "allow"}
    ]
}

# ========================================
# CONFIGURATION PERFORMANCE VPS
# ========================================

VPS_PERFORMANCE = {
    "max_memory_usage": 0.8,  # 80% de la RAM max
    "max_cpu_usage": 0.9,     # 90% du CPU max
    "max_disk_usage": 0.85,   # 85% du disque max
    "log_retention_days": 30,
    "backup_retention_days": 7,
    "monitoring_interval": 60,  # secondes
    "auto_restart_on_failure": True,
    "auto_cleanup_temp": True,
    "temp_cleanup_interval": 3600,  # secondes (1 heure)
}

# ========================================
# CONFIGURATION SÉCURITÉ VPS
# ========================================

VPS_SECURITY = {
    "enable_firewall": True,
    "enable_antivirus": True,
    "enable_windows_update": True,
    "enable_rdp_encryption": True,
    "enable_audit_logging": True,
    "max_failed_logins": 3,
    "lockout_duration": 300,  # secondes (5 minutes)
    "password_policy": {
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special": True,
        "max_age_days": 90
    }
}

# ========================================
# CONFIGURATION MONITORING VPS
# ========================================

VPS_MONITORING = {
    "enable_system_monitoring": True,
    "enable_application_monitoring": True,
    "enable_network_monitoring": True,
    "enable_disk_monitoring": True,
    "alert_thresholds": {
        "cpu_high": 80,      # %
        "memory_high": 85,   # %
        "disk_high": 90,     # %
        "network_latency": 100,  # ms
        "process_memory": 1000   # MB
    },
    "notification_methods": ["email", "log"],
    "notification_recipients": ["admin@example.com"],
    "log_levels": ["INFO", "WARNING", "ERROR", "CRITICAL"]
}

# ========================================
# CONFIGURATION SAUVEGARDE VPS
# ========================================

VPS_BACKUP = {
    "enable_automatic_backup": True,
    "backup_schedule": "daily",  # daily, weekly, monthly
    "backup_time": "02:00",      # HH:MM
    "backup_retention": 7,       # jours
    "backup_compression": True,
    "backup_encryption": True,
    "backup_locations": [
        "C:/Backups/MIA_IA",
        "C:/Backups/SierraChart"
    ],
    "exclude_patterns": [
        "*.log",
        "*.tmp",
        "*.pyc",
        "__pycache__",
        "venv",
        "temp"
    ]
}

# ========================================
# CONFIGURATION DÉMARRAGE AUTOMATIQUE
# ========================================

VPS_AUTOSTART = {
    "enable_autostart": True,
    "startup_delay": 30,  # secondes après le boot
    "startup_script": "C:/MIA_IA_system/start_mia_vps.bat",
    "startup_priority": "normal",  # low, normal, high
    "restart_on_failure": True,
    "max_restart_attempts": 3,
    "restart_delay": 60,  # secondes entre les tentatives
}

# ========================================
# CONFIGURATION DOCKER VPS
# ========================================

VPS_DOCKER = {
    "enable_docker": False,  # Désactivé par défaut sur VPS
    "docker_compose_file": "docker-compose.vps.yml",
    "container_restart_policy": "unless-stopped",
    "container_memory_limit": "2G",
    "container_cpu_limit": "1.0",
    "container_ports": {
        "mia_http": "8080:8080",
        "mia_https": "8443:8443",
        "syncthing": "8384:8384"
    }
}

# ========================================
# CONFIGURATION SPÉCIFIQUE FOURNISSEUR
# ========================================

VPS_PROVIDER_CONFIG = {
    "QuantVPS": {
        "optimization": "trading",
        "latency_cme": 0.52,
        "recommended_settings": {
            "tcp_nodelay": True,
            "tcp_quickack": True,
            "network_buffer_size": 65536
        }
    },
    "AWS": {
        "optimization": "general",
        "latency_cme": 1.2,
        "recommended_settings": {
            "enhanced_networking": True,
            "placement_group": True
        }
    },
    "Azure": {
        "optimization": "general",
        "latency_cme": 1.5,
        "recommended_settings": {
            "accelerated_networking": True,
            "proximity_placement": True
        }
    },
    "GCP": {
        "optimization": "general",
        "latency_cme": 1.8,
        "recommended_settings": {
            "network_tier": "premium",
            "placement_policy": True
        }
    }
}

# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_vps_config() -> Dict[str, Any]:
    """Retourne la configuration VPS complète"""
    return {
        "environment": VPS_ENVIRONMENT,
        "paths": VPS_PATHS,
        "sierra_chart": SIERRA_CHART_VPS,
        "network": VPS_NETWORK,
        "performance": VPS_PERFORMANCE,
        "security": VPS_SECURITY,
        "monitoring": VPS_MONITORING,
        "backup": VPS_BACKUP,
        "autostart": VPS_AUTOSTART,
        "docker": VPS_DOCKER,
        "provider": VPS_PROVIDER_CONFIG
    }

def get_vps_paths() -> Dict[str, Path]:
    """Retourne les chemins VPS"""
    return VPS_PATHS

def get_sierra_chart_vps_config() -> Dict[str, Any]:
    """Retourne la configuration Sierra Chart pour VPS"""
    return SIERRA_CHART_VPS

def is_vps_environment() -> bool:
    """Vérifie si on est dans un environnement VPS"""
    return VPS_ENVIRONMENT.get("is_vps", False)

def get_vps_provider() -> str:
    """Retourne le fournisseur VPS"""
    return VPS_ENVIRONMENT.get("vps_provider", "Unknown")

def get_vps_latency_cme() -> float:
    """Retourne la latence vers CME"""
    return VPS_ENVIRONMENT.get("vps_latency_cme", 1.0)

def get_vps_resources() -> Dict[str, int]:
    """Retourne les ressources VPS"""
    return {
        "ram_gb": VPS_ENVIRONMENT.get("vps_ram_gb", 16),
        "cpu_cores": VPS_ENVIRONMENT.get("vps_cpu_cores", 4),
        "storage_gb": VPS_ENVIRONMENT.get("vps_storage_gb", 100)
    }

# ========================================
# CONFIGURATION D'ENVIRONNEMENT
# ========================================

# Variables d'environnement VPS
VPS_ENV_VARS = {
    "MIA_ENV": "vps_production",
    "MIA_LOG_LEVEL": "INFO",
    "MIA_VPS_MODE": "true",
    "MIA_VPS_PROVIDER": VPS_ENVIRONMENT["vps_provider"],
    "MIA_VPS_LOCATION": VPS_ENVIRONMENT["vps_location"],
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1"
}

def setup_vps_environment():
    """Configure les variables d'environnement VPS"""
    for key, value in VPS_ENV_VARS.items():
        os.environ[key] = value

# ========================================
# VALIDATION DE CONFIGURATION
# ========================================

def validate_vps_config() -> bool:
    """Valide la configuration VPS"""
    try:
        # Vérifier les chemins
        for name, path in VPS_PATHS.items():
            if not isinstance(path, Path):
                print(f"❌ Chemin invalide pour {name}: {path}")
                return False
        
        # Vérifier la configuration Sierra Chart
        if not SIERRA_CHART_VPS.get("installation_path"):
            print("❌ Chemin d'installation Sierra Chart manquant")
            return False
        
        # Vérifier les ressources
        resources = get_vps_resources()
        if resources["ram_gb"] < 8:
            print("⚠️ RAM insuffisante (minimum 8GB recommandé)")
        
        if resources["cpu_cores"] < 4:
            print("⚠️ CPU insuffisant (minimum 4 cœurs recommandé)")
        
        print("✅ Configuration VPS validée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de validation VPS: {e}")
        return False

# ========================================
# INITIALISATION
# ========================================

if __name__ == "__main__":
    # Configurer l'environnement VPS
    setup_vps_environment()
    
    # Valider la configuration
    if validate_vps_config():
        print("🎯 Configuration VPS prête pour le déploiement")
    else:
        print("❌ Configuration VPS invalide")

