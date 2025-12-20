"""
MIA_IA_SYSTEM - MenthorQ Integration Module

Intégration des niveaux MenthorQ dans le système de confluence existant

Version: Phase 4 Elite - MenthorQ Integration

Performance: Analyse <2ms, intégration temps réel

RESPONSABILITÉS :

1. Collecte des niveaux MenthorQ depuis Sierra Chart Graph 4
2. Intégration dans le système de confluence existant
3. Calcul des scores de confluence MenthorQ
4. Intégration dans le système de vote Battle Navale
5. Calcul des distances aux niveaux critiques
6. Génération d'alertes de confluence extrême

NIVEAUX MENTHORQ INTÉGRÉS :

- Call Resistance / Put Support (niveaux principaux)
- HVL (High Volume Level)
- 1D Min / 1D Max
- Call/Put Support/Resistance 0DTE
- HVL 0DTE / Gamma Wall 0DTE
- GEX Levels 1-10 (Gamma Exposure)
- BL Levels 1-10 (Blind Spots)

PONDÉRATION MENTHORQ :

- Niveaux 0DTE : Poids très élevé (volatilité extrême)
- Gamma Wall 0DTE : Poids critique (cassure directionnelle)
- GEX Levels : Poids moyen (exposition gamma)
- BL Levels : Poids élevé (zones cachées)
- Niveaux principaux : Poids standard

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

# === MENTHORQ ENUMS ===

class MenthorQLevelType(Enum):
    """Types de niveaux MenthorQ"""
    
    # Niveaux principaux
    CALL_RESISTANCE = "call_resistance"
    PUT_SUPPORT = "put_support"
    HVL = "hvl"
    ONE_D_MIN = "1d_min"
    ONE_D_MAX = "1d_max"
    
    # Niveaux 0DTE (Zero Days To Expiration)
    CALL_RESISTANCE_0DTE = "call_resistance_0dte"
    PUT_SUPPORT_0DTE = "put_support_0dte"
    HVL_0DTE = "hvl_0dte"
    GAMMA_WALL_0DTE = "gamma_wall_0dte"
    
    # GEX Levels (Gamma Exposure)
    GEX_1 = "gex_1"
    GEX_2 = "gex_2"
    GEX_3 = "gex_3"
    GEX_4 = "gex_4"
    GEX_5 = "gex_5"
    GEX_6 = "gex_6"
    GEX_7 = "gex_7"
    GEX_8 = "gex_8"
    GEX_9 = "gex_9"
    GEX_10 = "gex_10"
    
    # BL Levels (Blind Spots)
    BL_1 = "bl_1"
    BL_2 = "bl_2"
    BL_3 = "bl_3"
    BL_4 = "bl_4"
    BL_5 = "bl_5"
    BL_6 = "bl_6"
    BL_7 = "bl_7"
    BL_8 = "bl_8"
    BL_9 = "bl_9"
    BL_10 = "bl_10"

class MenthorQConfluenceStrength(Enum):
    """Force de confluence MenthorQ"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    EXTREME = "extreme"

# === MENTHORQ DATA STRUCTURES ===

@dataclass
class MenthorQLevel:
    """Niveau MenthorQ individuel"""
    level_type: MenthorQLevelType
    price: float
    strength: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "menthorq"
    
    def __post_init__(self):
        """Validation post-initialisation"""
        if self.price <= 0:
            raise ValueError(f"Prix invalide pour {self.level_type}: {self.price}")
        if not 0 <= self.strength <= 1:
            raise ValueError(f"Force invalide pour {self.level_type}: {self.strength}")

@dataclass
class MenthorQLevels:
    """Collection de tous les niveaux MenthorQ"""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Niveaux principaux
    call_resistance: Optional[float] = None
    put_support: Optional[float] = None
    hvl: Optional[float] = None
    one_d_min: Optional[float] = None
    one_d_max: Optional[float] = None
    
    # Niveaux 0DTE
    call_resistance_0dte: Optional[float] = None
    put_support_0dte: Optional[float] = None
    hvl_0dte: Optional[float] = None
    gamma_wall_0dte: Optional[float] = None
    
    # GEX Levels
    gex_levels: List[float] = field(default_factory=list)
    
    # BL Levels
    bl_levels: List[float] = field(default_factory=list)
    
    def get_all_levels(self) -> List[MenthorQLevel]:
        """Retourne tous les niveaux sous forme de liste"""
        levels = []
        
        # Niveaux principaux
        if self.call_resistance:
            levels.append(MenthorQLevel(MenthorQLevelType.CALL_RESISTANCE, self.call_resistance))
        if self.put_support:
            levels.append(MenthorQLevel(MenthorQLevelType.PUT_SUPPORT, self.put_support))
        if self.hvl:
            levels.append(MenthorQLevel(MenthorQLevelType.HVL, self.hvl))
        if self.one_d_min:
            levels.append(MenthorQLevel(MenthorQLevelType.ONE_D_MIN, self.one_d_min))
        if self.one_d_max:
            levels.append(MenthorQLevel(MenthorQLevelType.ONE_D_MAX, self.one_d_max))
        
        # Niveaux 0DTE
        if self.call_resistance_0dte:
            levels.append(MenthorQLevel(MenthorQLevelType.CALL_RESISTANCE_0DTE, self.call_resistance_0dte))
        if self.put_support_0dte:
            levels.append(MenthorQLevel(MenthorQLevelType.PUT_SUPPORT_0DTE, self.put_support_0dte))
        if self.hvl_0dte:
            levels.append(MenthorQLevel(MenthorQLevelType.HVL_0DTE, self.hvl_0dte))
        if self.gamma_wall_0dte:
            levels.append(MenthorQLevel(MenthorQLevelType.GAMMA_WALL_0DTE, self.gamma_wall_0dte))
        
        # GEX Levels
        for i, gex_price in enumerate(self.gex_levels, 1):
            if gex_price:
                level_type = MenthorQLevelType(f"GEX_{i}")
                levels.append(MenthorQLevel(level_type, gex_price))
        
        # BL Levels
        for i, bl_price in enumerate(self.bl_levels, 1):
            if bl_price:
                level_type = MenthorQLevelType(f"BL_{i}")
                levels.append(MenthorQLevel(level_type, bl_price))
        
        return levels

@dataclass
class MenthorQConfluenceResult:
    """Résultat d'analyse de confluence MenthorQ"""
    current_price: float
    confluence_score: float
    strength: MenthorQConfluenceStrength
    nearby_levels: List[Tuple[MenthorQLevel, float]]  # (level, distance)
    critical_levels: List[MenthorQLevel]
    distance_analysis: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validation post-initialisation"""
        if not 0 <= self.confluence_score <= 1:
            raise ValueError(f"Score de confluence invalide: {self.confluence_score}")

# === MENTHORQ CONFIGURATION ===

class MenthorQConfig:
    """Configuration MenthorQ"""
    
    # Pondération des niveaux
    LEVEL_WEIGHTS = {
        # Niveaux principaux
        MenthorQLevelType.CALL_RESISTANCE: 0.15,
        MenthorQLevelType.PUT_SUPPORT: 0.15,
        MenthorQLevelType.HVL: 0.12,
        MenthorQLevelType.ONE_D_MIN: 0.10,
        MenthorQLevelType.ONE_D_MAX: 0.10,
        
        # Niveaux 0DTE (poids très élevé - volatilité extrême)
        MenthorQLevelType.CALL_RESISTANCE_0DTE: 0.20,
        MenthorQLevelType.PUT_SUPPORT_0DTE: 0.20,
        MenthorQLevelType.HVL_0DTE: 0.18,
        MenthorQLevelType.GAMMA_WALL_0DTE: 0.25,
        
        # GEX Levels (poids moyen)
        MenthorQLevelType.GEX_1: 0.08,
        MenthorQLevelType.GEX_2: 0.08,
        MenthorQLevelType.GEX_3: 0.08,
        MenthorQLevelType.GEX_4: 0.08,
        MenthorQLevelType.GEX_5: 0.08,
        MenthorQLevelType.GEX_6: 0.08,
        MenthorQLevelType.GEX_7: 0.08,
        MenthorQLevelType.GEX_8: 0.08,
        MenthorQLevelType.GEX_9: 0.08,
        MenthorQLevelType.GEX_10: 0.08,
        
        # BL Levels (poids élevé - zones cachées)
        MenthorQLevelType.BL_1: 0.12,
        MenthorQLevelType.BL_2: 0.12,
        MenthorQLevelType.BL_3: 0.12,
        MenthorQLevelType.BL_4: 0.12,
        MenthorQLevelType.BL_5: 0.12,
        MenthorQLevelType.BL_6: 0.12,
        MenthorQLevelType.BL_7: 0.12,
        MenthorQLevelType.BL_8: 0.12,
        MenthorQLevelType.BL_9: 0.12,
        MenthorQLevelType.BL_10: 0.12,
    }
    
    # Seuils de distance (en points)
    DISTANCE_THRESHOLDS = {
        "very_close": 5.0,    # Très proche
        "close": 15.0,        # Proche
        "moderate": 30.0,     # Moyennement proche
        "far": 50.0,          # Loin
    }
    
    # Seuils de confluence
    CONFLUENCE_THRESHOLDS = {
        MenthorQConfluenceStrength.WEAK: 0.2,
        MenthorQConfluenceStrength.MODERATE: 0.4,
        MenthorQConfluenceStrength.STRONG: 0.6,
        MenthorQConfluenceStrength.EXTREME: 0.8,
    }
    
    # Cache TTL (secondes)
    CACHE_TTL = 60
    
    # Taille max du cache
    MAX_CACHE_SIZE = 1000

# === MENTHORQ INTEGRATION CLASS ===

class MenthorQIntegration:
    """Intégration MenthorQ dans le système de confluence"""
    
    def __init__(self):
        """Initialisation"""
        self.config = MenthorQConfig()
        self.cache = {}
        self.cache_timestamps = {}
        self.logger = get_logger(__name__)
        
        # Statistiques
        self.stats = {
            "total_analyses": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "extreme_confluences": 0,
            "last_analysis_time": 0,
        }
    
    def parse_menthorq_data(self, raw_data: str) -> MenthorQLevels:
        """Parse les données MenthorQ depuis Sierra Chart"""
        try:
            # Exemple de parsing pour ESU25_FUT_CME
            # Format: "Call Resistance, 6600, Put Support, 6425, HVL, 6470, ..."
            
            levels = MenthorQLevels(symbol="ESU25_FUT_CME")
            
            # Parse des niveaux principaux
            if "Call Resistance," in raw_data:
                levels.call_resistance = self._extract_price(raw_data, "Call Resistance,")
            if "Put Support," in raw_data:
                levels.put_support = self._extract_price(raw_data, "Put Support,")
            if "HVL," in raw_data:
                levels.hvl = self._extract_price(raw_data, "HVL,")
            if "1D Min," in raw_data:
                levels.one_d_min = self._extract_price(raw_data, "1D Min,")
            if "1D Max," in raw_data:
                levels.one_d_max = self._extract_price(raw_data, "1D Max,")
            
            # Parse des niveaux 0DTE
            if "Call Resistance 0DTE," in raw_data:
                levels.call_resistance_0dte = self._extract_price(raw_data, "Call Resistance 0DTE,")
            if "Put Support 0DTE," in raw_data:
                levels.put_support_0dte = self._extract_price(raw_data, "Put Support 0DTE,")
            if "HVL 0DTE," in raw_data:
                levels.hvl_0dte = self._extract_price(raw_data, "HVL 0DTE,")
            if "Gamma Wall 0DTE," in raw_data:
                levels.gamma_wall_0dte = self._extract_price(raw_data, "Gamma Wall 0DTE,")
            
            # Parse des GEX Levels
            for i in range(1, 11):
                gex_key = f"GEX {i},"
                if gex_key in raw_data:
                    gex_price = self._extract_price(raw_data, gex_key)
                    if gex_price:
                        levels.gex_levels.append(gex_price)
            
            # Parse des BL Levels
            for i in range(1, 11):
                bl_key = f"BL {i},"
                if bl_key in raw_data:
                    bl_price = self._extract_price(raw_data, bl_key)
                    if bl_price:
                        levels.bl_levels.append(bl_price)
            
            return levels
            
        except Exception as e:
            self.logger.error(f"Erreur parsing MenthorQ: {e}")
            return MenthorQLevels(symbol="ESU25_FUT_CME")
    
    def _extract_price(self, data: str, key: str) -> Optional[float]:
        """Extrait un prix depuis les données"""
        try:
            if key in data:
                parts = data.split(key)
                if len(parts) > 1:
                    price_str = parts[1].split(',')[0].strip()
                    return float(price_str)
            return None
        except (ValueError, IndexError):
            return None
    
    def calculate_confluence(self, current_price: float, levels: MenthorQLevels) -> MenthorQConfluenceResult:
        """Calcule la confluence MenthorQ"""
        start_time = time.time()
        
        try:
            all_levels = levels.get_all_levels()
            confluence_score = 0.0
            nearby_levels = []
            critical_levels = []
            
            # Calcul du score de confluence
            for level in all_levels:
                distance = abs(current_price - level.price)
                weight = self.config.LEVEL_WEIGHTS.get(level.level_type, 0.1)
                
                # Calcul du score basé sur la distance
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
                
                # Niveaux critiques (0DTE et Gamma Wall)
                if level.level_type in [
                    MenthorQLevelType.CALL_RESISTANCE_0DTE,
                    MenthorQLevelType.PUT_SUPPORT_0DTE,
                    MenthorQLevelType.GAMMA_WALL_0DTE
                ] and distance < self.config.DISTANCE_THRESHOLDS["very_close"]:
                    critical_levels.append(level)
            
            # Normalisation du score
            confluence_score = min(confluence_score, 1.0)
            
            # Détermination de la force
            strength = self._determine_strength(confluence_score)
            
            # Analyse des distances
            distance_analysis = self._analyze_distances(current_price, all_levels)
            
            result = MenthorQConfluenceResult(
                current_price=current_price,
                confluence_score=confluence_score,
                strength=strength,
                nearby_levels=nearby_levels,
                critical_levels=critical_levels,
                distance_analysis=distance_analysis
            )
            
            # Mise à jour des statistiques
            self.stats["total_analyses"] += 1
            self.stats["last_analysis_time"] = time.time() - start_time
            
            if strength == MenthorQConfluenceStrength.EXTREME:
                self.stats["extreme_confluences"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur calcul confluence MenthorQ: {e}")
            return MenthorQConfluenceResult(
                current_price=current_price,
                confluence_score=0.0,
                strength=MenthorQConfluenceStrength.WEAK,
                nearby_levels=[],
                critical_levels=[],
                distance_analysis={}
            )
    
    def _determine_strength(self, score: float) -> MenthorQConfluenceStrength:
        """Détermine la force de confluence"""
        if score >= self.config.CONFLUENCE_THRESHOLDS[MenthorQConfluenceStrength.EXTREME]:
            return MenthorQConfluenceStrength.EXTREME
        elif score >= self.config.CONFLUENCE_THRESHOLDS[MenthorQConfluenceStrength.STRONG]:
            return MenthorQConfluenceStrength.STRONG
        elif score >= self.config.CONFLUENCE_THRESHOLDS[MenthorQConfluenceStrength.MODERATE]:
            return MenthorQConfluenceStrength.MODERATE
        else:
            return MenthorQConfluenceStrength.WEAK
    
    def _analyze_distances(self, current_price: float, levels: List[MenthorQLevel]) -> Dict[str, Any]:
        """Analyse des distances aux niveaux"""
        analysis = {
            "nearest_level": None,
            "nearest_distance": float('inf'),
            "levels_within_5": [],
            "levels_within_15": [],
            "levels_within_30": [],
            "total_levels": len(levels),
            "active_levels": 0
        }
        
        for level in levels:
            distance = abs(current_price - level.price)
            
            if distance < analysis["nearest_distance"]:
                analysis["nearest_level"] = level
                analysis["nearest_distance"] = distance
            
            if distance < 5:
                analysis["levels_within_5"].append((level, distance))
            if distance < 15:
                analysis["levels_within_15"].append((level, distance))
            if distance < 30:
                analysis["levels_within_30"].append((level, distance))
            
            if distance < 50:  # Niveau actif
                analysis["active_levels"] += 1
        
        return analysis
    
    def get_battle_navale_vote(self, confluence_result: MenthorQConfluenceResult) -> float:
        """Calcule le vote Battle Navale basé sur MenthorQ"""
        try:
            vote = 0.0
            current_price = confluence_result.current_price
            
            # Vote basé sur les niveaux proches
            for level, distance in confluence_result.nearby_levels:
                weight = self.config.LEVEL_WEIGHTS.get(level.level_type, 0.1)
                distance_factor = max(0, 1 - distance / 20)  # Décroissance sur 20 points
                
                # Vote directionnel
                if level.level_type in [
                    MenthorQLevelType.CALL_RESISTANCE,
                    MenthorQLevelType.CALL_RESISTANCE_0DTE,
                    MenthorQLevelType.ONE_D_MAX
                ]:
                    # Niveaux de résistance = vote baissier
                    vote -= weight * distance_factor
                
                elif level.level_type in [
                    MenthorQLevelType.PUT_SUPPORT,
                    MenthorQLevelType.PUT_SUPPORT_0DTE,
                    MenthorQLevelType.ONE_D_MIN
                ]:
                    # Niveaux de support = vote haussier
                    vote += weight * distance_factor
                
                elif level.level_type == MenthorQLevelType.GAMMA_WALL_0DTE:
                    # Gamma Wall = vote neutre mais critique
                    if current_price > level.price:
                        vote -= weight * distance_factor * 0.5  # Légèrement baissier
                    else:
                        vote += weight * distance_factor * 0.5  # Légèrement haussier
            
            # Bonus pour confluence extrême
            if confluence_result.strength == MenthorQConfluenceStrength.EXTREME:
                vote *= 1.5
            
            # Limitation du vote
            return max(-1.0, min(1.0, vote))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul vote Battle Navale MenthorQ: {e}")
            return 0.0
    
    def get_confluence_alert(self, confluence_result: MenthorQConfluenceResult) -> Optional[Dict[str, Any]]:
        """Génère une alerte de confluence si nécessaire"""
        try:
            if confluence_result.strength in [MenthorQConfluenceStrength.STRONG, MenthorQConfluenceStrength.EXTREME]:
                return {
                    "type": "MENTHORQ_CONFLUENCE",
                    "strength": confluence_result.strength.value,
                    "score": confluence_result.confluence_score,
                    "current_price": confluence_result.current_price,
                    "nearby_levels": [
                        {
                            "type": level.level_type.value,
                            "price": level.price,
                            "distance": distance
                        }
                        for level, distance in confluence_result.nearby_levels
                    ],
                    "critical_levels": [
                        {
                            "type": level.level_type.value,
                            "price": level.price
                        }
                        for level in confluence_result.critical_levels
                    ],
                    "timestamp": confluence_result.timestamp.isoformat()
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur génération alerte confluence: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "config": {
                "level_weights_count": len(self.config.LEVEL_WEIGHTS),
                "distance_thresholds": self.config.DISTANCE_THRESHOLDS,
                "confluence_thresholds": self.config.CONFLUENCE_THRESHOLDS
            }
        }

# === INSTANCE GLOBALE ===

menthorq_integration = MenthorQIntegration()

# === FONCTIONS UTILITAIRES ===

def get_menthorq_confluence(current_price: float, raw_menthorq_data: str) -> MenthorQConfluenceResult:
    """Fonction utilitaire pour calculer la confluence MenthorQ"""
    levels = menthorq_integration.parse_menthorq_data(raw_menthorq_data)
    return menthorq_integration.calculate_confluence(current_price, levels)

def get_menthorq_battle_navale_vote(confluence_result: MenthorQConfluenceResult) -> float:
    """Fonction utilitaire pour le vote Battle Navale MenthorQ"""
    return menthorq_integration.get_battle_navale_vote(confluence_result)

def get_menthorq_alert(confluence_result: MenthorQConfluenceResult) -> Optional[Dict[str, Any]]:
    """Fonction utilitaire pour les alertes MenthorQ"""
    return menthorq_integration.get_confluence_alert(confluence_result)

# === EXEMPLE D'UTILISATION ===

if __name__ == "__main__":
    # Exemple d'utilisation
    raw_data = "Call Resistance, 6600, Put Support, 6425, HVL, 6470, 1D Min, 6445.6, 1D Max, 6533.9, Call Resistance 0DTE, 6485, Put Support 0DTE, 6450, HVL 0DTE, 6480, Gamma Wall 0DTE, 6485, GEX 1, 6500, GEX 2, 6525, GEX 3, 6510, GEX 4, 6530, GEX 5, 6520, GEX 6, 6550, GEX 7, 6575, GEX 8, 6420, GEX 9, 6560, GEX 10, 6570, BL 1, 6487.95, BL 2, 6496.38, BL 3, 6518.74, BL 4, 6508.94, BL 5, 6527.57, BL 6, 6684.96, BL 7, 6534.18, BL 8, 6425.05, BL 9, 6557.33, BL 10, 6295.53"
    
    current_price = 6500.0
    
    # Calcul de la confluence
    confluence_result = get_menthorq_confluence(current_price, raw_data)
    
    print(f"Score de confluence: {confluence_result.confluence_score:.3f}")
    print(f"Force: {confluence_result.strength.value}")
    print(f"Niveaux proches: {len(confluence_result.nearby_levels)}")
    print(f"Niveaux critiques: {len(confluence_result.critical_levels)}")
    
    # Vote Battle Navale
    vote = get_menthorq_battle_navale_vote(confluence_result)
    print(f"Vote Battle Navale: {vote:.3f}")
    
    # Alerte
    alert = get_menthorq_alert(confluence_result)
    if alert:
        print(f"Alerte générée: {alert['type']}")
    
    # Statistiques
    stats = menthorq_integration.get_stats()
    print(f"Statistiques: {stats}")


