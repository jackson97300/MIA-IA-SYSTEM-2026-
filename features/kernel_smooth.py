"""
MIA_IA_SYSTEM - Kernel Smooth Utilities
Version: 1.0 Elite - Production Ready

Utilitaires pour le kernel lisse calibré :
- Fonctions de proximité exponentielles
- Normalisation par tick size
- Calibration des paramètres λ
- Support multi-symboles

Performance: <1ms par calcul
"""

import math
import numpy as np
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)

# === CONFIGURATION KERNEL SMOOTH ===

# Configuration tick_size par symbole
TICK_SIZE_CONFIG = {
    'ES': 0.25,    # E-mini S&P 500
    'NQ': 0.25,    # E-mini NASDAQ
    'YM': 1.0,     # E-mini Dow
    'RTY': 0.1,    # E-mini Russell
    'GC': 0.1,     # Gold
    'CL': 0.01     # Crude Oil
}

# Configuration des paramètres λ calibrés (AMÉLIORÉS)
LAMBDA_CONFIG = {
    # MenthorQ
    'ES_gamma': 8.0,    # Plus large pour scores plus élevés
    'ES_blind': 6.0,    # Plus large pour scores plus élevés
    'NQ_gamma': 8.0,    # Plus large pour scores plus élevés
    'NQ_blind': 6.0,    # Plus large pour scores plus élevés
    'YM_gamma': 8.0,    # Plus large pour scores plus élevés
    'YM_blind': 6.0,    # Plus large pour scores plus élevés
    
    # Battle Navale
    'ES_vwap': 10.0,    # Plus large pour scores plus élevés
    'ES_poc': 8.0,      # Plus large pour scores plus élevés
    'ES_mq': 12.0,      # Plus large pour scores plus élevés
    'NQ_vwap': 10.0,    # Plus large pour scores plus élevés
    'NQ_poc': 8.0,      # Plus large pour scores plus élevés
    'NQ_mq': 12.0,      # Plus large pour scores plus élevés
    'YM_vwap': 10.0,    # Plus large pour scores plus élevés
    'YM_poc': 8.0,      # Plus large pour scores plus élevés
    'YM_mq': 12.0       # Plus large pour scores plus élevés
}

# === FONCTIONS UTILITAIRES ===

def proximity_kernel(price: float, level: float, tick_size: float, lambda_ticks: float) -> float:
    """
    Fonction utilitaire : kernel de proximité lisse
    
    Args:
        price: Prix actuel
        level: Niveau de référence
        tick_size: Taille du tick
        lambda_ticks: Paramètre λ en ticks
    
    Returns:
        Score de proximité (0.0 à 1.0)
    """
    if level <= 0:
        return 0.0
    
    distance_ticks = abs(price - level) / tick_size
    return math.exp(-distance_ticks / lambda_ticks)

def proximity_kernel_symmetric(price: float, level: float, tick_size: float, lambda_ticks: float) -> float:
    """
    Kernel de proximité symétrique (même score des deux côtés)
    """
    if level <= 0:
        return 0.0
    
    distance_ticks = abs(price - level) / tick_size
    return math.exp(-distance_ticks / lambda_ticks)

def proximity_kernel_directional(price: float, level: float, tick_size: float, lambda_ticks: float, 
                                direction: int, bonus_factor: float = 0.2) -> float:
    """
    Kernel de proximité avec bonus directionnel
    
    Args:
        price: Prix actuel
        level: Niveau de référence
        tick_size: Taille du tick
        lambda_ticks: Paramètre λ en ticks
        direction: Direction (1=Long, -1=Short)
        bonus_factor: Facteur de bonus directionnel
    
    Returns:
        Score de proximité avec bonus directionnel
    """
    if level <= 0:
        return 0.0
    
    distance_ticks = abs(price - level) / tick_size
    base_score = math.exp(-distance_ticks / lambda_ticks)
    
    # Bonus directionnel
    if direction == 1:  # Long
        if price < level:  # Prix en-dessous du niveau (breakout potentiel vers le haut)
            direction_bonus = bonus_factor
        else:
            direction_bonus = 0.0
    else:  # Short
        if price > level:  # Prix au-dessus du niveau (breakout potentiel vers le bas)
            direction_bonus = bonus_factor
        else:
            direction_bonus = 0.0
    
    return min(1.0, base_score + direction_bonus)

def proximity_kernel_band(price: float, lower_level: float, upper_level: float, 
                         tick_size: float, lambda_ticks: float) -> float:
    """
    Kernel de proximité pour une bande (entre lower et upper)
    
    Args:
        price: Prix actuel
        lower_level: Niveau inférieur
        upper_level: Niveau supérieur
        tick_size: Taille du tick
        lambda_ticks: Paramètre λ en ticks
    
    Returns:
        Score de proximité à la bande
    """
    if lower_level <= 0 or upper_level <= 0 or lower_level >= upper_level:
        return 0.0
    
    # Si le prix est dans la bande
    if lower_level <= price <= upper_level:
        return 1.0
    
    # Si le prix est en-dessous de la bande
    if price < lower_level:
        distance_ticks = (lower_level - price) / tick_size
        return math.exp(-distance_ticks / lambda_ticks)
    
    # Si le prix est au-dessus de la bande
    if price > upper_level:
        distance_ticks = (price - upper_level) / tick_size
        return math.exp(-distance_ticks / lambda_ticks)
    
    return 0.0

def proximity_kernel_multi_levels(price: float, levels: list, tick_size: float, 
                                 lambda_ticks: float, method: str = "max") -> float:
    """
    Kernel de proximité pour plusieurs niveaux
    
    Args:
        price: Prix actuel
        levels: Liste des niveaux
        tick_size: Taille du tick
        lambda_ticks: Paramètre λ en ticks
        method: Méthode d'agrégation ("max", "sum", "weighted")
    
    Returns:
        Score de proximité agrégé
    """
    if not levels:
        return 0.0
    
    scores = []
    for level in levels:
        if level > 0:
            score = proximity_kernel(price, level, tick_size, lambda_ticks)
            scores.append(score)
    
    if not scores:
        return 0.0
    
    if method == "max":
        return max(scores)
    elif method == "sum":
        return min(1.0, sum(scores))
    elif method == "weighted":
        # Poids décroissant avec la distance
        weights = [1.0 / (i + 1) for i in range(len(scores))]
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        weight_sum = sum(weights)
        return min(1.0, weighted_sum / weight_sum)
    else:
        return max(scores)

# === CLASSE PRINCIPALE KERNEL SMOOTH ===

class KernelSmooth:
    """
    Gestionnaire de kernel lisse calibré
    
    Fonctionnalités :
    - Calculs de proximité optimisés
    - Support multi-symboles
    - Calibration des paramètres λ
    - Cache des calculs fréquents
    """
    
    def __init__(self):
        """Initialisation Kernel Smooth"""
        self.tick_size_config = TICK_SIZE_CONFIG
        self.lambda_config = LAMBDA_CONFIG
        self._cache = {}  # Cache simple pour optimiser
        logger.info("🔧 Kernel Smooth initialisé - Support multi-symboles")
    
    def get_tick_size(self, symbol: str) -> float:
        """Récupère la taille du tick pour un symbole"""
        return self.tick_size_config.get(symbol, 0.25)
    
    def get_lambda(self, symbol: str, component: str) -> float:
        """Récupère le paramètre λ pour un symbole et composant"""
        key = f"{symbol}_{component}"
        return self.lambda_config.get(key, 5.0)  # Défaut 5.0
    
    def calculate_proximity(self, price: float, level: float, symbol: str, 
                          component: str, method: str = "standard") -> float:
        """
        Calcule la proximité avec kernel lisse
        
        Args:
            price: Prix actuel
            level: Niveau de référence
            symbol: Symbole (ES, NQ, YM, etc.)
            component: Composant (gamma, blind, vwap, poc, mq)
            method: Méthode de calcul ("standard", "symmetric", "directional")
        
        Returns:
            Score de proximité (0.0 à 1.0)
        """
        if level <= 0:
            return 0.0
        
        tick_size = self.get_tick_size(symbol)
        lambda_ticks = self.get_lambda(symbol, component)
        
        if method == "standard":
            return proximity_kernel(price, level, tick_size, lambda_ticks)
        elif method == "symmetric":
            return proximity_kernel_symmetric(price, level, tick_size, lambda_ticks)
        else:
            return proximity_kernel(price, level, tick_size, lambda_ticks)
    
    def calculate_proximity_directional(self, price: float, level: float, symbol: str, 
                                      component: str, direction: int, 
                                      bonus_factor: float = 0.2) -> float:
        """
        Calcule la proximité avec bonus directionnel
        
        Args:
            price: Prix actuel
            level: Niveau de référence
            symbol: Symbole
            component: Composant
            direction: Direction (1=Long, -1=Short)
            bonus_factor: Facteur de bonus
        
        Returns:
            Score de proximité avec bonus directionnel
        """
        if level <= 0:
            return 0.0
        
        tick_size = self.get_tick_size(symbol)
        lambda_ticks = self.get_lambda(symbol, component)
        
        return proximity_kernel_directional(price, level, tick_size, lambda_ticks, 
                                          direction, bonus_factor)
    
    def calculate_proximity_band(self, price: float, lower_level: float, upper_level: float, 
                               symbol: str, component: str) -> float:
        """
        Calcule la proximité à une bande
        
        Args:
            price: Prix actuel
            lower_level: Niveau inférieur
            upper_level: Niveau supérieur
            symbol: Symbole
            component: Composant
        
        Returns:
            Score de proximité à la bande
        """
        if lower_level <= 0 or upper_level <= 0 or lower_level >= upper_level:
            return 0.0
        
        tick_size = self.get_tick_size(symbol)
        lambda_ticks = self.get_lambda(symbol, component)
        
        return proximity_kernel_band(price, lower_level, upper_level, tick_size, lambda_ticks)
    
    def calculate_proximity_multi_levels(self, price: float, levels: list, symbol: str, 
                                       component: str, method: str = "max") -> float:
        """
        Calcule la proximité à plusieurs niveaux
        
        Args:
            price: Prix actuel
            levels: Liste des niveaux
            symbol: Symbole
            component: Composant
            method: Méthode d'agrégation
        
        Returns:
            Score de proximité agrégé
        """
        if not levels:
            return 0.0
        
        tick_size = self.get_tick_size(symbol)
        lambda_ticks = self.get_lambda(symbol, component)
        
        return proximity_kernel_multi_levels(price, levels, tick_size, lambda_ticks, method)
    
    def calibrate_lambda(self, symbol: str, component: str, historical_data: list, 
                        target_accuracy: float = 0.8) -> float:
        """
        Calibre le paramètre λ sur données historiques
        
        Args:
            symbol: Symbole
            component: Composant
            historical_data: Données historiques
            target_accuracy: Précision cible
        
        Returns:
            Paramètre λ calibré
        """
        # TODO: Implémenter la calibration automatique
        # Pour l'instant, retourne la valeur par défaut
        return self.get_lambda(symbol, component)
    
    def update_lambda(self, symbol: str, component: str, new_lambda: float):
        """Met à jour le paramètre λ pour un symbole et composant"""
        key = f"{symbol}_{component}"
        self.lambda_config[key] = new_lambda
        logger.info(f"🔧 Lambda mis à jour: {key} = {new_lambda}")
    
    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle"""
        return {
            'tick_size_config': self.tick_size_config,
            'lambda_config': self.lambda_config
        }
    
    def set_config(self, config: Dict[str, Any]):
        """Met à jour la configuration"""
        if 'tick_size_config' in config:
            self.tick_size_config.update(config['tick_size_config'])
        if 'lambda_config' in config:
            self.lambda_config.update(config['lambda_config'])
        logger.info("🔧 Configuration Kernel Smooth mise à jour")

# === INSTANCE GLOBALE ===

kernel_smooth = KernelSmooth()

# === FONCTIONS DE CONVENIENCE ===

def get_kernel_smooth() -> KernelSmooth:
    """Retourne l'instance globale de Kernel Smooth"""
    return kernel_smooth

def proximity_kernel_quick(price: float, level: float, symbol: str, component: str) -> float:
    """Fonction de convenience pour calcul rapide"""
    return kernel_smooth.calculate_proximity(price, level, symbol, component)

def proximity_kernel_directional_quick(price: float, level: float, symbol: str, 
                                     component: str, direction: int) -> float:
    """Fonction de convenience pour calcul directionnel rapide"""
    return kernel_smooth.calculate_proximity_directional(price, level, symbol, component, direction)
