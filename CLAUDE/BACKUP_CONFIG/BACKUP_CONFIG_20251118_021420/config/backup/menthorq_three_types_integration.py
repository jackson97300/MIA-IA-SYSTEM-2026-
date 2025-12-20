"""
MIA_IA_SYSTEM - MenthorQ Three Types Integration

Intégration complète des 3 types de niveaux MenthorQ dans le système MIA

Version: Phase 4 Elite - Complete MenthorQ Integration

Performance: <3ms processing, intégration temps réel

RESPONSABILITÉS :

1. Intégration des 3 types de niveaux MenthorQ
2. Calcul de confluence multi-types
3. Vote Battle Navale pondéré par type
4. Génération d'alertes spécialisées
5. Optimisation des stratégies par type de niveau

TYPES DE NIVEAUX INTÉGRÉS :

1. BLIND SPOTS LEVELS
   - BL 1-10 (zones cachées)
   - Corrélations cross-marchés
   - Gamma shifts

2. GAMMA LEVELS
   - Primary: Call/Put Support/Resistance, HVL, 1D Min/Max, 0DTE
   - Secondary: GEX 1-10 (concentrations gamma)

3. SWING LEVELS
   - Swing Support/Resistance
   - Swing Pivots
   - Swing Targets/Stops

"""

import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from core.logger import get_logger
from collections import defaultdict

# Local imports
from core.base_types import MarketData, ES_TICK_SIZE, ES_TICK_VALUE
from config.automation_config import get_automation_config

logger = get_logger(__name__)

# === MENTHORQ THREE TYPES ENUMS ===

class MenthorQLevelCategory(Enum):
    """Catégories de niveaux MenthorQ"""
    BLIND_SPOTS = "blind_spots"
    GAMMA = "gamma"
    SWING = "swing"

class MenthorQBlindSpotsType(Enum):
    """Types de niveaux Blind Spots"""
    BL_LEVEL = "bl_level"
    CROSS_ASSET_CORRELATION = "cross_asset_correlation"
    GAMMA_SHIFT = "gamma_shift"
    HIDDEN_REACTION_ZONE = "hidden_reaction_zone"

class MenthorQGammaType(Enum):
    """Types de niveaux Gamma"""
    # Primary Levels
    CALL_RESISTANCE = "call_resistance"
    PUT_SUPPORT = "put_support"
    HVL = "hvl"
    ONE_D_MIN = "1d_min"
    ONE_D_MAX = "1d_max"
    CALL_RESISTANCE_0DTE = "call_resistance_0dte"
    PUT_SUPPORT_0DTE = "put_support_0dte"
    HVL_0DTE = "hvl_0dte"
    GAMMA_WALL_0DTE = "gamma_wall_0dte"
    
    # Secondary Levels
    GEX_LEVEL = "gex_level"

class MenthorQSwingType(Enum):
    """Types de niveaux Swing"""
    SWING_SUPPORT = "swing_support"
    SWING_RESISTANCE = "swing_resistance"
    SWING_PIVOT = "swing_pivot"
    SWING_TARGET = "swing_target"
    SWING_STOP = "swing_stop"

# === MENTHORQ THREE TYPES DATA STRUCTURES ===

@dataclass
class MenthorQBlindSpotsLevel:
    """Niveau Blind Spots MenthorQ"""
    level_type: MenthorQBlindSpotsType
    price: float
    strength: float = 1.0
    level_index: int = 0
    correlation_asset: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"Prix invalide pour {self.level_type}: {self.price}")

@dataclass
class MenthorQGammaLevel:
    """Niveau Gamma MenthorQ"""
    level_type: MenthorQGammaType
    price: float
    strength: float = 1.0
    level_index: int = 0
    is_0dte: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"Prix invalide pour {self.level_type}: {self.price}")

@dataclass
class MenthorQSwingLevel:
    """Niveau Swing MenthorQ"""
    level_type: MenthorQSwingType
    price: float
    strength: float = 1.0
    level_index: int = 0
    swing_timeframe: str = "daily"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"Prix invalide pour {self.level_type}: {self.price}")

@dataclass
class MenthorQThreeTypesData:
    """Collection complète des 3 types de niveaux MenthorQ"""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Blind Spots Levels
    blind_spots_levels: List[MenthorQBlindSpotsLevel] = field(default_factory=list)
    
    # Gamma Levels
    gamma_levels: List[MenthorQGammaLevel] = field(default_factory=list)
    
    # Swing Levels
    swing_levels: List[MenthorQSwingLevel] = field(default_factory=list)
    
    def get_all_levels(self) -> List[Tuple[MenthorQLevelCategory, Any]]:
        """Retourne tous les niveaux avec leur catégorie"""
        all_levels = []
        
        for level in self.blind_spots_levels:
            all_levels.append((MenthorQLevelCategory.BLIND_SPOTS, level))
        
        for level in self.gamma_levels:
            all_levels.append((MenthorQLevelCategory.GAMMA, level))
        
        for level in self.swing_levels:
            all_levels.append((MenthorQLevelCategory.SWING, level))
        
        return all_levels

@dataclass
class MenthorQThreeTypesConfluenceResult:
    """Résultat de confluence pour les 3 types de niveaux"""
    current_price: float
    total_confluence_score: float
    
    # Scores par catégorie
    blind_spots_score: float
    gamma_score: float
    swing_score: float
    
    # Détails par catégorie
    blind_spots_nearby: List[Tuple[MenthorQBlindSpotsLevel, float]]
    gamma_nearby: List[Tuple[MenthorQGammaLevel, float]]
    swing_nearby: List[Tuple[MenthorQSwingLevel, float]]
    
    # Niveaux critiques
    critical_levels: List[Any]
    
    # Analyse de distance
    distance_analysis: Dict[str, Any]
    
    timestamp: datetime = field(default_factory=datetime.now)

# === MENTHORQ THREE TYPES CONFIGURATION ===

class MenthorQThreeTypesConfig:
    """Configuration pour les 3 types de niveaux MenthorQ"""
    
    # Pondération par catégorie
    CATEGORY_WEIGHTS = {
        MenthorQLevelCategory.BLIND_SPOTS: 0.25,  # Poids élevé - zones cachées
        MenthorQLevelCategory.GAMMA: 0.50,        # Poids très élevé - institutionnel
        MenthorQLevelCategory.SWING: 0.25         # Poids élevé - structurel
    }
    
    # Pondération par type de niveau
    LEVEL_TYPE_WEIGHTS = {
        # Blind Spots
        MenthorQBlindSpotsType.BL_LEVEL: 0.8,
        MenthorQBlindSpotsType.CROSS_ASSET_CORRELATION: 0.9,
        MenthorQBlindSpotsType.GAMMA_SHIFT: 0.7,
        MenthorQBlindSpotsType.HIDDEN_REACTION_ZONE: 0.6,
        
        # Gamma
        MenthorQGammaType.CALL_RESISTANCE: 0.9,
        MenthorQGammaType.PUT_SUPPORT: 0.9,
        MenthorQGammaType.HVL: 0.8,
        MenthorQGammaType.ONE_D_MIN: 0.7,
        MenthorQGammaType.ONE_D_MAX: 0.7,
        MenthorQGammaType.CALL_RESISTANCE_0DTE: 1.0,  # Poids critique
        MenthorQGammaType.PUT_SUPPORT_0DTE: 1.0,      # Poids critique
        MenthorQGammaType.HVL_0DTE: 0.9,
        MenthorQGammaType.GAMMA_WALL_0DTE: 1.0,       # Poids critique
        MenthorQGammaType.GEX_LEVEL: 0.6,
        
        # Swing
        MenthorQSwingType.SWING_SUPPORT: 0.8,
        MenthorQSwingType.SWING_RESISTANCE: 0.8,
        MenthorQSwingType.SWING_PIVOT: 0.9,
        MenthorQSwingType.SWING_TARGET: 0.7,
        MenthorQSwingType.SWING_STOP: 0.7
    }
    
    # Seuils de distance (en points)
    DISTANCE_THRESHOLDS = {
        "very_close": 5.0,
        "close": 15.0,
        "moderate": 30.0,
        "far": 50.0
    }
    
    # Seuils de confluence par catégorie
    CONFLUENCE_THRESHOLDS = {
        MenthorQLevelCategory.BLIND_SPOTS: {
            "weak": 0.2,
            "moderate": 0.4,
            "strong": 0.6,
            "extreme": 0.8
        },
        MenthorQLevelCategory.GAMMA: {
            "weak": 0.15,
            "moderate": 0.35,
            "strong": 0.55,
            "extreme": 0.75
        },
        MenthorQLevelCategory.SWING: {
            "weak": 0.25,
            "moderate": 0.45,
            "strong": 0.65,
            "extreme": 0.85
        }
    }

# === MENTHORQ THREE TYPES INTEGRATION CLASS ===

class MenthorQThreeTypesIntegration:
    """Intégration complète des 3 types de niveaux MenthorQ"""
    
    def __init__(self):
        """Initialisation"""
        self.config = MenthorQThreeTypesConfig()
        self.logger = get_logger(__name__)
        
        # Cache
        self.cache = {}
        self.cache_ttl = 60
        
        # Statistiques
        self.stats = {
            "total_analyses": 0,
            "blind_spots_analyses": 0,
            "gamma_analyses": 0,
            "swing_analyses": 0,
            "extreme_confluences": 0,
            "last_analysis_time": 0
        }
    
    def parse_three_types_data(self, raw_data: str) -> MenthorQThreeTypesData:
        """Parse les données des 3 types de niveaux MenthorQ"""
        try:
            data = MenthorQThreeTypesData(symbol="ESU25_FUT_CME")
            
            # Parse Blind Spots Levels
            data.blind_spots_levels = self._parse_blind_spots_levels(raw_data)
            
            # Parse Gamma Levels
            data.gamma_levels = self._parse_gamma_levels(raw_data)
            
            # Parse Swing Levels
            data.swing_levels = self._parse_swing_levels(raw_data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Erreur parsing 3 types MenthorQ: {e}")
            return MenthorQThreeTypesData(symbol="ESU25_FUT_CME")
    
    def _parse_blind_spots_levels(self, raw_data: str) -> List[MenthorQBlindSpotsLevel]:
        """Parse les niveaux Blind Spots"""
        levels = []
        
        try:
            # Parse BL Levels (1-10)
            for i in range(1, 11):
                bl_key = f"BL {i},"
                if bl_key in raw_data:
                    price = self._extract_price(raw_data, bl_key)
                    if price > 0:
                        level = MenthorQBlindSpotsLevel(
                            level_type=MenthorQBlindSpotsType.BL_LEVEL,
                            price=price,
                            strength=0.8,
                            level_index=i
                        )
                        levels.append(level)
            
            # Parse Cross Asset Correlations
            correlation_assets = ["SPX", "NDX", "VIX"]
            for asset in correlation_assets:
                asset_key = f"{asset} Correlation,"
                if asset_key in raw_data:
                    price = self._extract_price(raw_data, asset_key)
                    if price > 0:
                        level = MenthorQBlindSpotsLevel(
                            level_type=MenthorQBlindSpotsType.CROSS_ASSET_CORRELATION,
                            price=price,
                            strength=0.9,
                            correlation_asset=asset
                        )
                        levels.append(level)
            
        except Exception as e:
            self.logger.error(f"Erreur parsing Blind Spots: {e}")
        
        return levels
    
    def _parse_gamma_levels(self, raw_data: str) -> List[MenthorQGammaLevel]:
        """Parse les niveaux Gamma"""
        levels = []
        
        try:
            # Primary Levels
            primary_mapping = {
                "Call Resistance,": MenthorQGammaType.CALL_RESISTANCE,
                "Put Support,": MenthorQGammaType.PUT_SUPPORT,
                "HVL,": MenthorQGammaType.HVL,
                "1D Min,": MenthorQGammaType.ONE_D_MIN,
                "1D Max,": MenthorQGammaType.ONE_D_MAX,
                "Call Resistance 0DTE,": MenthorQGammaType.CALL_RESISTANCE_0DTE,
                "Put Support 0DTE,": MenthorQGammaType.PUT_SUPPORT_0DTE,
                "HVL 0DTE,": MenthorQGammaType.HVL_0DTE,
                "Gamma Wall 0DTE,": MenthorQGammaType.GAMMA_WALL_0DTE
            }
            
            for key, level_type in primary_mapping.items():
                if key in raw_data:
                    price = self._extract_price(raw_data, key)
                    if price > 0:
                        is_0dte = "0DTE" in key
                        strength = 1.0 if is_0dte else 0.9
                        
                        level = MenthorQGammaLevel(
                            level_type=level_type,
                            price=price,
                            strength=strength,
                            is_0dte=is_0dte
                        )
                        levels.append(level)
            
            # GEX Levels (1-10)
            for i in range(1, 11):
                gex_key = f"GEX {i},"
                if gex_key in raw_data:
                    price = self._extract_price(raw_data, gex_key)
                    if price > 0:
                        level = MenthorQGammaLevel(
                            level_type=MenthorQGammaType.GEX_LEVEL,
                            price=price,
                            strength=0.6,
                            level_index=i
                        )
                        levels.append(level)
            
        except Exception as e:
            self.logger.error(f"Erreur parsing Gamma: {e}")
        
        return levels
    
    def _parse_swing_levels(self, raw_data: str) -> List[MenthorQSwingLevel]:
        """Parse les niveaux Swing"""
        levels = []
        
        try:
            # Swing Levels
            swing_mapping = {
                "Swing Support,": MenthorQSwingType.SWING_SUPPORT,
                "Swing Resistance,": MenthorQSwingType.SWING_RESISTANCE,
                "Swing Pivot,": MenthorQSwingType.SWING_PIVOT,
                "Swing Target,": MenthorQSwingType.SWING_TARGET,
                "Swing Stop,": MenthorQSwingType.SWING_STOP
            }
            
            for key, level_type in swing_mapping.items():
                if key in raw_data:
                    price = self._extract_price(raw_data, key)
                    if price > 0:
                        level = MenthorQSwingLevel(
                            level_type=level_type,
                            price=price,
                            strength=0.8
                        )
                        levels.append(level)
            
        except Exception as e:
            self.logger.error(f"Erreur parsing Swing: {e}")
        
        return levels
    
    def _extract_price(self, data: str, key: str) -> float:
        """Extrait un prix depuis les données"""
        try:
            if key in data:
                parts = data.split(key)
                if len(parts) > 1:
                    price_str = parts[1].split(',')[0].strip()
                    return float(price_str)
            return 0.0
        except (ValueError, IndexError):
            return 0.0
    
    def calculate_three_types_confluence(self, current_price: float, data: MenthorQThreeTypesData) -> MenthorQThreeTypesConfluenceResult:
        """Calcule la confluence pour les 3 types de niveaux"""
        start_time = time.time()
        
        try:
            # Calcul par catégorie
            blind_spots_score, blind_spots_nearby = self._calculate_category_confluence(
                current_price, data.blind_spots_levels, MenthorQLevelCategory.BLIND_SPOTS
            )
            
            gamma_score, gamma_nearby = self._calculate_category_confluence(
                current_price, data.gamma_levels, MenthorQLevelCategory.GAMMA
            )
            
            swing_score, swing_nearby = self._calculate_category_confluence(
                current_price, data.swing_levels, MenthorQLevelCategory.SWING
            )
            
            # Score total pondéré
            total_score = (
                blind_spots_score * self.config.CATEGORY_WEIGHTS[MenthorQLevelCategory.BLIND_SPOTS] +
                gamma_score * self.config.CATEGORY_WEIGHTS[MenthorQLevelCategory.GAMMA] +
                swing_score * self.config.CATEGORY_WEIGHTS[MenthorQLevelCategory.SWING]
            )
            
            # Niveaux critiques
            critical_levels = self._identify_critical_levels(
                blind_spots_nearby, gamma_nearby, swing_nearby
            )
            
            # Analyse des distances
            distance_analysis = self._analyze_three_types_distances(
                current_price, data
            )
            
            result = MenthorQThreeTypesConfluenceResult(
                current_price=current_price,
                total_confluence_score=min(total_score, 1.0),
                blind_spots_score=blind_spots_score,
                gamma_score=gamma_score,
                swing_score=swing_score,
                blind_spots_nearby=blind_spots_nearby,
                gamma_nearby=gamma_nearby,
                swing_nearby=swing_nearby,
                critical_levels=critical_levels,
                distance_analysis=distance_analysis
            )
            
            # Mise à jour des statistiques
            self.stats["total_analyses"] += 1
            self.stats["blind_spots_analyses"] += 1
            self.stats["gamma_analyses"] += 1
            self.stats["swing_analyses"] += 1
            self.stats["last_analysis_time"] = time.time() - start_time
            
            if total_score > 0.8:
                self.stats["extreme_confluences"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur calcul confluence 3 types: {e}")
            return MenthorQThreeTypesConfluenceResult(
                current_price=current_price,
                total_confluence_score=0.0,
                blind_spots_score=0.0,
                gamma_score=0.0,
                swing_score=0.0,
                blind_spots_nearby=[],
                gamma_nearby=[],
                swing_nearby=[],
                critical_levels=[],
                distance_analysis={}
            )
    
    def _calculate_category_confluence(self, current_price: float, levels: List[Any], category: MenthorQLevelCategory) -> Tuple[float, List[Tuple[Any, float]]]:
        """Calcule la confluence pour une catégorie"""
        confluence_score = 0.0
        nearby_levels = []
        
        for level in levels:
            distance = abs(current_price - level.price)
            weight = self.config.LEVEL_TYPE_WEIGHTS.get(level.level_type, 0.5)
            
            # Score basé sur la distance
            if distance < self.config.DISTANCE_THRESHOLDS["very_close"]:
                distance_score = 1.0
            elif distance < self.config.DISTANCE_THRESHOLDS["close"]:
                distance_score = 0.7
            elif distance < self.config.DISTANCE_THRESHOLDS["moderate"]:
                distance_score = 0.4
            else:
                distance_score = 0.1
            
            # Score pondéré
            level_score = weight * distance_score * level.strength
            confluence_score += level_score
            
            # Niveaux proches
            if distance < self.config.DISTANCE_THRESHOLDS["close"]:
                nearby_levels.append((level, distance))
        
        return min(confluence_score, 1.0), nearby_levels
    
    def _identify_critical_levels(self, blind_spots_nearby: List, gamma_nearby: List, swing_nearby: List) -> List[Any]:
        """Identifie les niveaux critiques"""
        critical_levels = []
        
        # Niveaux 0DTE critiques
        for level, distance in gamma_nearby:
            if hasattr(level, 'is_0dte') and level.is_0dte and distance < 10:
                critical_levels.append(level)
        
        # Niveaux de corrélation critiques
        for level, distance in blind_spots_nearby:
            if hasattr(level, 'level_type') and level.level_type == MenthorQBlindSpotsType.CROSS_ASSET_CORRELATION and distance < 15:
                critical_levels.append(level)
        
        # Pivots swing critiques
        for level, distance in swing_nearby:
            if hasattr(level, 'level_type') and level.level_type == MenthorQSwingType.SWING_PIVOT and distance < 20:
                critical_levels.append(level)
        
        return critical_levels
    
    def _analyze_three_types_distances(self, current_price: float, data: MenthorQThreeTypesData) -> Dict[str, Any]:
        """Analyse des distances pour les 3 types"""
        analysis = {
            "blind_spots": {"nearest": None, "nearest_distance": float('inf'), "levels_within_15": 0},
            "gamma": {"nearest": None, "nearest_distance": float('inf'), "levels_within_15": 0},
            "swing": {"nearest": None, "nearest_distance": float('inf'), "levels_within_15": 0}
        }
        
        # Analyse Blind Spots
        for level in data.blind_spots_levels:
            distance = abs(current_price - level.price)
            if distance < analysis["blind_spots"]["nearest_distance"]:
                analysis["blind_spots"]["nearest"] = level
                analysis["blind_spots"]["nearest_distance"] = distance
            if distance < 15:
                analysis["blind_spots"]["levels_within_15"] += 1
        
        # Analyse Gamma
        for level in data.gamma_levels:
            distance = abs(current_price - level.price)
            if distance < analysis["gamma"]["nearest_distance"]:
                analysis["gamma"]["nearest"] = level
                analysis["gamma"]["nearest_distance"] = distance
            if distance < 15:
                analysis["gamma"]["levels_within_15"] += 1
        
        # Analyse Swing
        for level in data.swing_levels:
            distance = abs(current_price - level.price)
            if distance < analysis["swing"]["nearest_distance"]:
                analysis["swing"]["nearest"] = level
                analysis["swing"]["nearest_distance"] = distance
            if distance < 15:
                analysis["swing"]["levels_within_15"] += 1
        
        return analysis
    
    def get_three_types_battle_navale_vote(self, confluence_result: MenthorQThreeTypesConfluenceResult) -> float:
        """Calcule le vote Battle Navale pour les 3 types"""
        try:
            vote = 0.0
            current_price = confluence_result.current_price
            
            # Vote Blind Spots (neutre mais informatif)
            for level, distance in confluence_result.blind_spots_nearby:
                weight = 0.1  # Poids faible pour Blind Spots
                distance_factor = max(0, 1 - distance / 25)
                vote += weight * distance_factor * 0.1  # Légère contribution
            
            # Vote Gamma (directionnel)
            for level, distance in confluence_result.gamma_nearby:
                weight = 0.3  # Poids élevé pour Gamma
                distance_factor = max(0, 1 - distance / 20)
                
                # Vote directionnel basé sur le type
                if hasattr(level, 'level_type'):
                    if level.level_type in [MenthorQGammaType.CALL_RESISTANCE, MenthorQGammaType.CALL_RESISTANCE_0DTE]:
                        vote -= weight * distance_factor  # Vote baissier
                    elif level.level_type in [MenthorQGammaType.PUT_SUPPORT, MenthorQGammaType.PUT_SUPPORT_0DTE]:
                        vote += weight * distance_factor  # Vote haussier
                    elif level.level_type == MenthorQGammaType.GAMMA_WALL_0DTE:
                        # Vote neutre mais critique
                        if current_price > level.price:
                            vote -= weight * distance_factor * 0.5
                        else:
                            vote += weight * distance_factor * 0.5
            
            # Vote Swing (structurel)
            for level, distance in confluence_result.swing_nearby:
                weight = 0.2  # Poids moyen pour Swing
                distance_factor = max(0, 1 - distance / 30)
                
                if hasattr(level, 'level_type'):
                    if level.level_type in [MenthorQSwingType.SWING_RESISTANCE, MenthorQSwingType.SWING_PIVOT]:
                        vote -= weight * distance_factor * 0.3  # Légèrement baissier
                    elif level.level_type in [MenthorQSwingType.SWING_SUPPORT, MenthorQSwingType.SWING_PIVOT]:
                        vote += weight * distance_factor * 0.3  # Légèrement haussier
            
            # Bonus pour confluence extrême
            if confluence_result.total_confluence_score > 0.8:
                vote *= 1.5
            
            return max(-1.0, min(1.0, vote))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul vote Battle Navale 3 types: {e}")
            return 0.0
    
    def get_three_types_alert(self, confluence_result: MenthorQThreeTypesConfluenceResult) -> Optional[Dict[str, Any]]:
        """Génère une alerte pour les 3 types"""
        try:
            if confluence_result.total_confluence_score > 0.7:
                return {
                    "type": "MENTHORQ_THREE_TYPES_CONFLUENCE",
                    "total_score": confluence_result.total_confluence_score,
                    "blind_spots_score": confluence_result.blind_spots_score,
                    "gamma_score": confluence_result.gamma_score,
                    "swing_score": confluence_result.swing_score,
                    "current_price": confluence_result.current_price,
                    "critical_levels_count": len(confluence_result.critical_levels),
                    "blind_spots_nearby": len(confluence_result.blind_spots_nearby),
                    "gamma_nearby": len(confluence_result.gamma_nearby),
                    "swing_nearby": len(confluence_result.swing_nearby),
                    "timestamp": confluence_result.timestamp.isoformat()
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur génération alerte 3 types: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return self.stats.copy()

# === INSTANCE GLOBALE ===

menthorq_three_types_integration = MenthorQThreeTypesIntegration()

# === FONCTIONS UTILITAIRES ===

def get_three_types_confluence(current_price: float, raw_data: str) -> MenthorQThreeTypesConfluenceResult:
    """Fonction utilitaire pour calculer la confluence des 3 types"""
    data = menthorq_three_types_integration.parse_three_types_data(raw_data)
    return menthorq_three_types_integration.calculate_three_types_confluence(current_price, data)

def get_three_types_battle_navale_vote(confluence_result: MenthorQThreeTypesConfluenceResult) -> float:
    """Fonction utilitaire pour le vote Battle Navale des 3 types"""
    return menthorq_three_types_integration.get_three_types_battle_navale_vote(confluence_result)

def get_three_types_alert(confluence_result: MenthorQThreeTypesConfluenceResult) -> Optional[Dict[str, Any]]:
    """Fonction utilitaire pour les alertes des 3 types"""
    return menthorq_three_types_integration.get_three_types_alert(confluence_result)

# === EXEMPLE D'UTILISATION ===

if __name__ == "__main__":
    # Exemple d'utilisation avec les 3 types
    raw_data = "Call Resistance, 6600, Put Support, 6425, HVL, 6470, 1D Min, 6445.6, 1D Max, 6533.9, Call Resistance 0DTE, 6485, Put Support 0DTE, 6450, HVL 0DTE, 6480, Gamma Wall 0DTE, 6485, GEX 1, 6500, GEX 2, 6525, GEX 3, 6510, GEX 4, 6530, GEX 5, 6520, GEX 6, 6550, GEX 7, 6575, GEX 8, 6420, GEX 9, 6560, GEX 10, 6570, BL 1, 6487.95, BL 2, 6496.38, BL 3, 6518.74, BL 4, 6508.94, BL 5, 6527.57, BL 6, 6684.96, BL 7, 6534.18, BL 8, 6425.05, BL 9, 6557.33, BL 10, 6295.53, Swing Support, 6450, Swing Resistance, 6550, Swing Pivot, 6500"
    
    current_price = 6500.0
    
    # Calcul de la confluence des 3 types
    confluence_result = get_three_types_confluence(current_price, raw_data)
    
    print(f"Score de confluence total: {confluence_result.total_confluence_score:.3f}")
    print(f"Score Blind Spots: {confluence_result.blind_spots_score:.3f}")
    print(f"Score Gamma: {confluence_result.gamma_score:.3f}")
    print(f"Score Swing: {confluence_result.swing_score:.3f}")
    print(f"Niveaux critiques: {len(confluence_result.critical_levels)}")
    
    # Vote Battle Navale
    vote = get_three_types_battle_navale_vote(confluence_result)
    print(f"Vote Battle Navale: {vote:.3f}")
    
    # Alerte
    alert = get_three_types_alert(confluence_result)
    if alert:
        print(f"Alerte générée: {alert['type']}")
    
    # Statistiques
    stats = menthorq_three_types_integration.get_stats()
    print(f"Statistiques: {stats}")


