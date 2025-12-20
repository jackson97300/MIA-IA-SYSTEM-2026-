#!/usr/bin/env python3
"""
🧠 MENTHORQ RUNTIME CONFIGURATION - MIA_IA_SYSTEM
=================================================

Configuration centralisée pour l'intégration MenthorQ en mode Sierra-only.
Gère les politiques de mise à jour, seuils et chemins unifiés.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

@dataclass
class MenthorQRuntimeConfig:
    """Configuration runtime pour MenthorQ"""
    
    # === POLITIQUES DE MISE À JOUR ===
    
    # Politique VIX → Timeframe
    vix_update_threshold: float = 2.0  # Seuil de changement VIX pour mise à jour
    vix_normal_threshold: float = 20.0  # VIX normal
    vix_high_threshold: float = 30.0   # VIX élevé
    
    # Fréquence Graph10 (MenthorQ)
    graph10_update_interval_normal: int = 30  # minutes en mode normal
    graph10_update_interval_high_vix: int = 15  # minutes en mode VIX élevé
    graph10_update_interval_extreme: int = 5   # minutes en mode extrême
    
    # === SEUILS DEALERS BIAS ===
    
    # Seuils de confluence
    confluence_threshold: float = 0.15
    confluence_strong_threshold: float = 0.25
    
    # Seuils gamma levels
    gamma_proximity_threshold: float = 0.5  # points
    gamma_strength_threshold: float = 0.3
    
    # Seuils blind spots
    blind_spot_violation_threshold: float = 0.3
    blind_spot_strength_threshold: float = 0.4
    
    # === SEUILS POSITION SIZING ===
    
    # Facteurs de sizing
    base_sizing_factor: float = 0.5
    vix_sizing_multiplier: float = 0.8  # Réduction en cas de VIX élevé
    confluence_sizing_boost: float = 1.2  # Boost si forte confluence
    
    # Limites de position
    max_position_size: float = 2.0
    min_position_size: float = 0.1
    
    # === CHEMINS UNIFIÉS ===
    
    # Chemins d'entrée (Sierra JSONL)
    sierra_input_dir: Path = Path(r"D:\MIA_IA_system")
    chart_patterns: Dict[int, str] = None  # Sera initialisé
    
    # Chemins de sortie
    unified_output_dir: Path = Path(r"D:\MIA_IA_system")
    unified_filename_format: str = "mia_unified_{date}.jsonl"
    
    # Chemins de logs
    logs_dir: Path = Path(r"D:\MIA_IA_system\logs")
    
    def __post_init__(self):
        """Initialisation des chemins après création"""
        if self.chart_patterns is None:
            self.chart_patterns = {
                3: "chart_3_{date}.jsonl",
                # 4: "chart_4_{date}.jsonl",  # Chart 4 désactivé 
                8: "chart_8_{date}.jsonl",
                10: "chart_10_{date}.jsonl"
            }
    
    # === MÉTHODES UTILITAIRES ===
    
    def get_vix_policy(self, vix_value: float) -> str:
        """Détermine la politique VIX actuelle"""
        if vix_value < self.vix_normal_threshold:
            return "normal"
        elif vix_value < self.vix_high_threshold:
            return "elevated"
        else:
            return "extreme"
    
    def get_update_interval(self, vix_value: float) -> int:
        """Retourne l'intervalle de mise à jour basé sur le VIX"""
        policy = self.get_vix_policy(vix_value)
        
        if policy == "normal":
            return self.graph10_update_interval_normal
        elif policy == "elevated":
            return self.graph10_update_interval_high_vix
        else:
            return self.graph10_update_interval_extreme
    
    def get_sizing_factor(self, vix_value: float, confluence_score: float) -> float:
        """Calcule le facteur de sizing basé sur VIX et confluence"""
        base_factor = self.base_sizing_factor
        
        # Ajustement VIX
        if vix_value > self.vix_high_threshold:
            base_factor *= self.vix_sizing_multiplier
        
        # Boost confluence
        if confluence_score > self.confluence_strong_threshold:
            base_factor *= self.confluence_sizing_boost
        
        # Limites
        return max(self.min_position_size, min(self.max_position_size, base_factor))
    
    def get_chart_path(self, chart_number: int, date_str: str) -> Path:
        """Retourne le chemin d'un fichier chart"""
        pattern = self.chart_patterns.get(chart_number)
        if not pattern:
            raise ValueError(f"Chart {chart_number} non supporté")
        
        filename = pattern.format(date=date_str)
        return self.sierra_input_dir / filename
    
    def get_unified_path(self, date_str: str) -> Path:
        """Retourne le chemin du fichier unifié"""
        filename = self.unified_filename_format.format(date=date_str)
        return self.unified_output_dir / filename
    
    def get_current_date_str(self) -> str:
        """Retourne la date actuelle au format YYYYMMDD"""
        return datetime.now().strftime("%Y%m%d")
    
    def should_update_menthorq(self, last_update: datetime, vix_value: float) -> bool:
        """Détermine si MenthorQ doit être mis à jour"""
        if last_update is None:
            return True
        
        interval_minutes = self.get_update_interval(vix_value)
        time_since_update = datetime.now(timezone.utc) - last_update
        
        return time_since_update.total_seconds() >= (interval_minutes * 60)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de la configuration"""
        return {
            "vix_thresholds": {
                "normal": self.vix_normal_threshold,
                "high": self.vix_high_threshold
            },
            "update_intervals": {
                "normal": self.graph10_update_interval_normal,
                "high_vix": self.graph10_update_interval_high_vix,
                "extreme": self.graph10_update_interval_extreme
            },
            "thresholds": {
                "confluence": self.confluence_threshold,
                "gamma_proximity": self.gamma_proximity_threshold,
                "blind_spot_violation": self.blind_spot_violation_threshold
            },
            "sizing": {
                "base_factor": self.base_sizing_factor,
                "max_size": self.max_position_size,
                "min_size": self.min_position_size
            },
            "paths": {
                "input_dir": str(self.sierra_input_dir),
                "output_dir": str(self.unified_output_dir),
                "logs_dir": str(self.logs_dir)
            }
        }

# === INSTANCE GLOBALE ===

# Configuration par défaut
menthorq_runtime_config = MenthorQRuntimeConfig()

# Configuration pour tests
test_menthorq_runtime_config = MenthorQRuntimeConfig(
    vix_update_threshold=1.0,
    graph10_update_interval_normal=5,  # Plus rapide pour les tests
    confluence_threshold=0.1,
    base_sizing_factor=0.2
)

def get_menthorq_config(test_mode: bool = False) -> MenthorQRuntimeConfig:
    """Retourne la configuration MenthorQ appropriée"""
    return test_menthorq_runtime_config if test_mode else menthorq_runtime_config