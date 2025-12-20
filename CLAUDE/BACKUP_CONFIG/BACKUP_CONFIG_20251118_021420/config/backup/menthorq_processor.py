"""
MIA_IA_SYSTEM - MenthorQ Processor

Processeur MenthorQ pour système unifié
- Normalisation et déduplication des niveaux
- Cache en RAM avec mise à jour incrémentale
- Exposition des niveaux pour ConfluenceAnalyzer

Version: Phase 2 - Normalisation
Performance: <1ms pour traitement des niveaux
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from core.logger import get_logger
from core.base_types import ES_TICK_SIZE

logger = get_logger(__name__)

# === MENTHORQ DATA STRUCTURES ===

@dataclass
class MenthorQLevel:
    """Niveau MenthorQ avec métadonnées"""
    timestamp: datetime
    symbol: str
    study_id: int
    subgraph: int
    level_type: str  # "menthorq_gamma_levels", "menthorq_blind_spots", "menthorq_swing_levels"
    label: str
    price: float
    session: str
    source: str = "sierrachart"
    
    def is_valid(self) -> bool:
        """Vérifie si le niveau est valide"""
        return (self.price > 0 and 
                self.price < 100000 and  # Prix raisonnable
                self.label and 
                self.symbol)

@dataclass
class MenthorQLevels:
    """Structure des niveaux MenthorQ par type"""
    gamma: Dict[str, float] = field(default_factory=dict)
    blind_spots: Dict[str, float] = field(default_factory=dict)
    swing: Dict[str, float] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    
    def get_all_levels(self) -> List[Tuple[str, str, float]]:
        """Retourne tous les niveaux sous forme (type, label, price)"""
        levels = []
        for label, price in self.gamma.items():
            if price > 0:
                levels.append(("gamma", label, price))
        for label, price in self.blind_spots.items():
            if price > 0:
                levels.append(("blind_spots", label, price))
        for label, price in self.swing.items():
            if price > 0:
                levels.append(("swing", label, price))
        return levels

# === MENTHORQ PROCESSOR ===

class MenthorQProcessor:
    """
    Processeur MenthorQ pour système unifié
    
    Fonctionnalités:
    1. Traitement des données JSONL MenthorQ
    2. Déduplication par (study_id, sg, label) + tolerance tick
    3. Cache en RAM avec mise à jour incrémentale
    4. Exposition des niveaux pour ConfluenceAnalyzer
    """
    
    def __init__(self, tolerance_ticks: float = 1.0):
        """
        Initialisation du processeur MenthorQ
        
        Args:
            tolerance_ticks: Tolérance pour déduplication (en ticks)
        """
        self.tolerance_ticks = tolerance_ticks
        self.tolerance_price = tolerance_ticks * ES_TICK_SIZE
        
        # Cache des derniers niveaux par symbole
        self.levels_cache: Dict[str, MenthorQLevels] = defaultdict(MenthorQLevels)
        
        # Cache des dernières valeurs émises (pour déduplication)
        self.last_emitted: Dict[str, Dict[Tuple[int, int, str], float]] = defaultdict(dict)
        
        # Statistiques
        self.stats = {
            'total_processed': 0,
            'duplicates_filtered': 0,
            'valid_levels': 0,
            'invalid_levels': 0,
            'last_update': None
        }
        
        logger.info(f"MenthorQProcessor initialisé (tolérance: {tolerance_ticks} ticks)")
    
    def process_menthorq_line(self, jsonl_line: str) -> bool:
        """
        Traite une ligne JSONL MenthorQ
        
        Args:
            jsonl_line: Ligne JSONL du fichier unifié
            
        Returns:
            bool: True si niveau traité, False si ignoré
        """
        try:
            data = json.loads(jsonl_line.strip())
            
            # --- Normalisation des alias clés ---
            symbol = data.get("symbol") or data.get("sym") or data.get("ticker")
            if not symbol:
                return False  # rien à indexer
            
            graph = data.get("graph") or data.get("chart")
            stype = data.get("type", "")
            label = data.get("label") or data.get("name") or data.get("id")
            sg = data.get("sg") or data.get("subgraph") or data.get("sg_id")
            study = data.get("study_id") or data.get("study") or data.get("studyId")
            price = data.get("price") or data.get("level") or 0.0
            
            # Sanity checks
            if not price or price <= 0:
                return False
            if stype not in ("menthorq_gamma_levels", "menthorq_blind_spots", "menthorq_swing_levels"):
                return False
            
            # Reconstruire data avec clés normalisées
            normalized_data = {
                "symbol": symbol,
                "graph": graph,
                "type": stype,
                "label": label,
                "sg": sg,
                "study_id": study,
                "price": price,
                "ts": data.get("ts") or data.get("t"),
                "session": data.get("session", "RTH"),
                "src": data.get("src", "sierrachart")
            }
            
            # Vérifier que c'est une donnée MenthorQ
            if not self._is_menthorq_data(normalized_data):
                return False
            
            # Créer objet MenthorQLevel
            level = self._create_menthorq_level(normalized_data)
            
            if not level or not level.is_valid():
                self.stats['invalid_levels'] += 1
                return False
            
            # Vérifier déduplication
            if self._is_duplicate(level):
                self.stats['duplicates_filtered'] += 1
                return False
            
            # Mettre à jour le cache
            self._update_cache(level)
            
            # Mettre à jour les statistiques
            self.stats['total_processed'] += 1
            self.stats['valid_levels'] += 1
            self.stats['last_update'] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur traitement ligne MenthorQ: {e}")
            self.stats['invalid_levels'] += 1
            return False
    
    def _is_menthorq_data(self, data: Dict[str, Any]) -> bool:
        """Vérifie si les données sont de type MenthorQ"""
        return (isinstance(data, dict) and 
                'type' in data and 
                data['type'].startswith('menthorq_'))
    
    def _create_menthorq_level(self, data: Dict[str, Any]) -> Optional[MenthorQLevel]:
        """Crée un objet MenthorQLevel depuis les données JSON"""
        try:
            # Parser le timestamp
            timestamp_str = data.get('ts', '')
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now()
            
            return MenthorQLevel(
                timestamp=timestamp,
                symbol=data.get('symbol', ''),
                study_id=data.get('study_id', 0),
                subgraph=data.get('sg', 0),
                level_type=data.get('type', ''),
                label=data.get('label', ''),
                price=float(data.get('price', 0)),
                session=data.get('session', 'RTH'),
                source=data.get('src', 'sierrachart')
            )
            
        except Exception as e:
            logger.error(f"Erreur création MenthorQLevel: {e}")
            return None
    
    def _is_duplicate(self, level: MenthorQLevel) -> bool:
        """Vérifie si le niveau est un doublon"""
        cache_key = (level.study_id, level.subgraph, level.label)
        symbol = level.symbol
        
        if symbol in self.last_emitted and cache_key in self.last_emitted[symbol]:
            last_price = self.last_emitted[symbol][cache_key]
            if abs(level.price - last_price) < self.tolerance_price:
                return True
        
        return False
    
    def _update_cache(self, level: MenthorQLevel):
        """Met à jour le cache des niveaux"""
        symbol = level.symbol
        cache_key = (level.study_id, level.subgraph, level.label)
        
        # Mettre à jour le cache des dernières valeurs
        self.last_emitted[symbol][cache_key] = level.price
        
        # Mettre à jour les niveaux par type
        if level.level_type == "menthorq_gamma_levels":
            self.levels_cache[symbol].gamma[level.label] = level.price
        elif level.level_type == "menthorq_blind_spots":
            self.levels_cache[symbol].blind_spots[level.label] = level.price
        elif level.level_type == "menthorq_swing_levels":
            self.levels_cache[symbol].swing[level.label] = level.price
        
        # Mettre à jour le timestamp
        self.levels_cache[symbol].last_update = level.timestamp
    
    def get_levels(self, symbol: str = "ESZ5") -> Dict[str, Any]:
        """
        Retourne les niveaux MenthorQ sous format compact
        
        Args:
            symbol: Symbole à récupérer (défaut: ESZ5)
            
        Returns:
            Dict avec structure compacte des niveaux
        """
        if symbol not in self.levels_cache:
            return {
                "gamma": {},
                "blind_spots": {},
                "swing": {},
                "last_update": None,
                "stale": True
            }
        
        levels = self.levels_cache[symbol]
        
        # Vérifier si les données sont obsolètes (>5 minutes)
        is_stale = False
        if levels.last_update:
            # Gérer les timezones (naive vs aware)
            now = datetime.now()
            last_update = levels.last_update
            
            # Si last_update est aware et now est naive, rendre now aware
            if last_update.tzinfo is not None and now.tzinfo is None:
                now = now.replace(tzinfo=last_update.tzinfo)
            # Si last_update est naive et now est aware, rendre last_update aware
            elif last_update.tzinfo is None and now.tzinfo is not None:
                last_update = last_update.replace(tzinfo=now.tzinfo)
            
            age_minutes = (now - last_update).total_seconds() / 60
            is_stale = age_minutes > 5
        
        return {
            "gamma": levels.gamma.copy(),
            "blind_spots": levels.blind_spots.copy(),
            "swing": levels.swing.copy(),
            "last_update": levels.last_update,
            "stale": is_stale
        }
    
    def check_staleness(self, max_age_minutes: int = 60) -> Dict[str, float]:
        """
        Vérifie la staleness des niveaux MenthorQ
        
        Args:
            max_age_minutes: Âge maximum en minutes
            
        Returns:
            Dict des niveaux obsolètes avec leur âge
        """
        now = datetime.now()
        stale = {}
        
        for symbol, levels in self.levels_cache.items():
            if levels.last_update:
                age_minutes = (now - levels.last_update).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    stale[f"{symbol}_last_update"] = round(age_minutes, 1)
        
        return stale
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Retourne le statut de santé du processeur
        
        Returns:
            Dict avec statistiques et warnings
        """
        status = {
            "total_symbols": len(self.levels_cache),
            "stats": self.stats.copy(),
            "staleness": self.check_staleness(),
            "warnings": []
        }
        
        # Vérifier les warnings
        if status["staleness"]:
            status["warnings"].append(f"⚠️ Levels stale: {status['staleness']}")
        
        if self.stats['invalid_levels'] > 0:
            status["warnings"].append(f"⚠️ Invalid levels: {self.stats['invalid_levels']}")
        
        if self.stats['duplicates_filtered'] > 0:
            status["warnings"].append(f"ℹ️ Duplicates filtered: {self.stats['duplicates_filtered']}")
        
        return status
    
    def get_confluence_levels(self, symbol: str = "ESZ5") -> List[Tuple[str, str, float]]:
        """
        Retourne les niveaux pour ConfluenceAnalyzer
        
        Args:
            symbol: Symbole à récupérer
            
        Returns:
            List de tuples (type, label, price)
        """
        levels = self.get_levels(symbol)
        
        confluence_levels = []
        
        # Gamma levels
        for label, price in levels["gamma"].items():
            if price > 0:
                confluence_levels.append(("gamma", label, price))
        
        # Blind spots
        for label, price in levels["blind_spots"].items():
            if price > 0:
                confluence_levels.append(("blind_spots", label, price))
        
        # Swing levels
        for label, price in levels["swing"].items():
            if price > 0:
                confluence_levels.append(("swing", label, price))
        
        return confluence_levels
    
    def check_blind_spots(self, current_price: float, symbol: str = "ESZ5", 
                         tolerance_ticks: float = 5.0) -> List[Tuple[str, float]]:
        """
        Vérifie si le prix est proche d'un Blind Spot
        
        Args:
            current_price: Prix actuel
            symbol: Symbole à vérifier
            tolerance_ticks: Tolérance en ticks
            
        Returns:
            List des Blind Spots proches (label, price)
        """
        levels = self.get_levels(symbol)
        tolerance_price = tolerance_ticks * ES_TICK_SIZE
        
        nearby_blind_spots = []
        
        for label, price in levels["blind_spots"].items():
            if price > 0 and abs(current_price - price) <= tolerance_price:
                nearby_blind_spots.append((label, price))
        
        return nearby_blind_spots
    
    def check_gamma_levels(self, current_price: float, symbol: str = "ESZ5",
                          tolerance_ticks: float = 3.0) -> List[Tuple[str, str, float]]:
        """
        Vérifie si le prix est proche d'un niveau Gamma
        
        Args:
            current_price: Prix actuel
            symbol: Symbole à vérifier
            tolerance_ticks: Tolérance en ticks
            
        Returns:
            List des niveaux Gamma proches (type, label, price)
        """
        levels = self.get_levels(symbol)
        tolerance_price = tolerance_ticks * ES_TICK_SIZE
        
        nearby_gamma = []
        
        for label, price in levels["gamma"].items():
            if price > 0 and abs(current_price - price) <= tolerance_price:
                nearby_gamma.append(("gamma", label, price))
        
        return nearby_gamma
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du processeur"""
        return {
            'total_processed': self.stats['total_processed'],
            'duplicates_filtered': self.stats['duplicates_filtered'],
            'valid_levels': self.stats['valid_levels'],
            'invalid_levels': self.stats['invalid_levels'],
            'last_update': self.stats['last_update'],
            'cached_symbols': list(self.levels_cache.keys()),
            'tolerance_ticks': self.tolerance_ticks
        }
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Vide le cache (optionnel par symbole)"""
        if symbol:
            if symbol in self.levels_cache:
                del self.levels_cache[symbol]
            if symbol in self.last_emitted:
                del self.last_emitted[symbol]
        else:
            self.levels_cache.clear()
            self.last_emitted.clear()
        
        logger.info(f"Cache vidé pour {symbol or 'tous les symboles'}")

# === FACTORY FUNCTION ===

def create_menthorq_processor(tolerance_ticks: float = 1.0) -> MenthorQProcessor:
    """Factory function pour MenthorQProcessor"""
    return MenthorQProcessor(tolerance_ticks)

# === TESTING ===

def test_menthorq_processor():
    """Test du MenthorQProcessor"""
    logger.info("Test MenthorQProcessor...")
    
    processor = create_menthorq_processor(tolerance_ticks=1.0)
    
    # Test données MenthorQ
    test_lines = [
        '{"ts":"2025-09-07T14:31:00.123Z","symbol":"ESZ5","graph":10,"study_id":1,"sg":1,"type":"menthorq_gamma_levels","label":"Call Resistance","price":5294.00,"session":"RTH","src":"sierrachart"}',
        '{"ts":"2025-09-07T14:31:01.123Z","symbol":"ESZ5","graph":10,"study_id":2,"sg":1,"type":"menthorq_blind_spots","label":"BL 1","price":5282.00,"session":"RTH","src":"sierrachart"}',
        '{"ts":"2025-09-07T14:31:02.123Z","symbol":"ESZ5","graph":10,"study_id":3,"sg":1,"type":"menthorq_swing_levels","label":"SG1","price":5271.00,"session":"RTH","src":"sierrachart"}'
    ]
    
    # Traitement des lignes
    for line in test_lines:
        result = processor.process_menthorq_line(line)
        logger.info(f"Ligne traitée: {result}")
    
    # Test récupération des niveaux
    levels = processor.get_levels("ESZ5")
    logger.info(f"Niveaux récupérés: {levels}")
    
    # Test confluence levels
    confluence_levels = processor.get_confluence_levels("ESZ5")
    logger.info(f"Niveaux confluence: {confluence_levels}")
    
    # Test Blind Spots
    nearby_bl = processor.check_blind_spots(5282.5, "ESZ5", 5.0)
    logger.info(f"Blind Spots proches: {nearby_bl}")
    
    # Test Gamma levels
    nearby_gamma = processor.check_gamma_levels(5294.5, "ESZ5", 3.0)
    logger.info(f"Gamma levels proches: {nearby_gamma}")
    
    # Statistiques
    stats = processor.get_statistics()
    logger.info(f"Statistiques: {stats}")
    
    logger.info("Test MenthorQProcessor terminé")
    return True

if __name__ == "__main__":
    test_menthorq_processor()
