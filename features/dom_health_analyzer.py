"""
MIA_IA_SYSTEM - DOM Health Analyzer Implementation
Version: 1.0 Elite - Production Ready

Implémentation DOM Health avec :
- Spread Analysis généralisé par symbole
- L1 BBO Consistency avec gate dur
- Depth Quality analysis
- Gates robustes et QC

Performance: <2ms, intégration temps réel
"""

import math
import numpy as np
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

# === CONFIGURATION DOM HEALTH ===

# Configuration tick_size par symbole
TICK_SIZE_CONFIG = {
    'ES': 0.25,    # E-mini S&P 500
    'NQ': 0.25,    # E-mini NASDAQ
    'YM': 1.0,     # E-mini Dow
    'RTY': 0.1,    # E-mini Russell
    'GC': 0.1,     # Gold
    'CL': 0.01     # Crude Oil
}

# === DATACLASSES ===

@dataclass
class DOMHealthResult:
    """Résultat DOM Health complet"""
    dom_health_score: float
    spread_score: float
    l1_bbo_score: float
    depth_score: float
    gate_status: Dict[str, Any]
    calculation_time_ms: float
    timestamp: datetime

@dataclass
class SpreadAnalysisResult:
    """Résultat analyse spread"""
    spread_ticks: float
    spread_score: float
    quality: str

@dataclass
class L1BBOResult:
    """Résultat L1 BBO"""
    l1_bbo_ratio: float
    l1_bbo_score: float
    consistency: str
    gate_passed: bool

@dataclass
class DepthQualityResult:
    """Résultat qualité profondeur"""
    depth_levels: int
    depth_score: float
    quality: str

# === UTILITAIRES ===

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp une valeur entre lo et hi"""
    return max(lo, min(hi, x))

def l1_bbo_gate(l1_bbo_ratio_rolling: float, threshold: float = 0.70) -> bool:
    """
    Gate dur : Si L1 != BBO < threshold sur fenêtre récente => pas de signal
    
    Args:
        l1_bbo_ratio_rolling: Ratio L1==BBO sur fenêtre glissante
        threshold: Seuil minimum (défaut 0.70)
    
    Returns:
        True si gate passé, False sinon
    """
    return l1_bbo_ratio_rolling >= threshold

# === CLASSE PRINCIPALE DOM HEALTH ANALYZER ===

class DOMHealthAnalyzer:
    """
    DOM Health Analyzer - Implémentation réelle
    
    Composants :
    1. Spread Analysis (40%) - Généralisé par symbole
    2. L1 BBO Consistency (35%) - Gate dur
    3. Depth Quality (25%) - Analyse profondeur
    """
    
    def __init__(self):
        """Initialisation DOM Health Analyzer"""
        self.tick_size_config = TICK_SIZE_CONFIG
        self.l1_bbo_threshold = 0.70  # Seuil gate L1==BBO
        logger.info("🔍 DOM Health Analyzer initialisé - Gates robustes")
    
    def calculate_dom_health(self, dom_data: Dict[str, Any], symbol: str) -> DOMHealthResult:
        """
        Calcul du score DOM Health (qualité pure, sans direction)
        
        Args:
            dom_data: Données DOM (best_bid, best_ask, l1_bbo_ratio, depth_levels, etc.)
            symbol: Symbole (ES, NQ, YM, etc.)
        
        Returns:
            DOMHealthResult complet
        """
        start_time = datetime.now()
        
        try:
            # === GATE DUR EN AMONT ===
            l1_bbo_ratio_rolling = dom_data.get('l1_bbo_ratio_rolling', 0)
            gate_passed = l1_bbo_gate(l1_bbo_ratio_rolling, self.l1_bbo_threshold)
            
            if not gate_passed:
                logger.warning(f"🚫 Gate DOM L1!=BBO: {l1_bbo_ratio_rolling:.2f} < {self.l1_bbo_threshold}")
                return DOMHealthResult(
                    dom_health_score=0.0, spread_score=0.0, l1_bbo_score=0.0, depth_score=0.0,
                    gate_status={"gate": "L1!=BBO", "passed": False, "ratio": l1_bbo_ratio_rolling},
                    calculation_time_ms=0.0, timestamp=start_time
                )
            
            # === ANALYSES INDIVIDUELLES ===
            spread_analysis = self._analyze_spread(dom_data, symbol)
            l1_bbo_analysis = self._analyze_l1_bbo_consistency(dom_data)
            depth_analysis = self._analyze_depth_quality(dom_data)
            
            # === SCORE FINAL PONDÉRÉ ===
            dom_health_score = (
                0.40 * spread_analysis.spread_score +
                0.35 * l1_bbo_analysis.l1_bbo_score +
                0.25 * depth_analysis.depth_score
            )
            
            # === CALCUL TEMPS ===
            calc_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return DOMHealthResult(
                dom_health_score=dom_health_score,
                spread_score=spread_analysis.spread_score,
                l1_bbo_score=l1_bbo_analysis.l1_bbo_score,
                depth_score=depth_analysis.depth_score,
                gate_status={
                    "gate": "OK", 
                    "passed": True, 
                    "ratio": l1_bbo_ratio_rolling,
                    "threshold": self.l1_bbo_threshold
                },
                calculation_time_ms=calc_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur DOM Health Analyzer: {e}")
            return DOMHealthResult(
                dom_health_score=0.0, spread_score=0.0, l1_bbo_score=0.0, depth_score=0.0,
                gate_status={"gate": "ERROR", "passed": False, "error": str(e)},
                calculation_time_ms=0.0, timestamp=start_time
            )
    
    # === SPREAD ANALYSIS (40%) ===
    
    def _analyze_spread(self, dom_data: Dict[str, Any], symbol: str) -> SpreadAnalysisResult:
        """
        Analyse du spread bid/ask (généralisé par symbole)
        
        Args:
            dom_data: Données DOM
            symbol: Symbole
        
        Returns:
            SpreadAnalysisResult
        """
        best_bid = dom_data.get('best_bid', 0)
        best_ask = dom_data.get('best_ask', 0)
        tick_size = self.tick_size_config.get(symbol, 0.25)
        
        if best_bid <= 0 or best_ask <= 0:
            return SpreadAnalysisResult(
                spread_ticks=0.0, spread_score=0.0, quality="INVALID"
            )
        
        spread_ticks = (best_ask - best_bid) / tick_size
        
        # Score basé sur le spread en ticks
        if spread_ticks <= 1:
            spread_score = 1.0
            quality = "EXCELLENT"
        elif spread_ticks <= 2:
            spread_score = 0.8
            quality = "GOOD"
        elif spread_ticks <= 3:
            spread_score = 0.5
            quality = "ACCEPTABLE"
        elif spread_ticks <= 5:
            spread_score = 0.2
            quality = "POOR"
        else:
            spread_score = 0.0
            quality = "DEGRADED"
        
        return SpreadAnalysisResult(
            spread_ticks=spread_ticks,
            spread_score=spread_score,
            quality=quality
        )
    
    # === L1 BBO CONSISTENCY (35%) ===
    
    def _analyze_l1_bbo_consistency(self, dom_data: Dict[str, Any]) -> L1BBOResult:
        """
        Vérification L1 == BBO (Level 1 = Best Bid/Offer)
        
        Args:
            dom_data: Données DOM
        
        Returns:
            L1BBOResult
        """
        l1_bbo_ratio = dom_data.get('l1_bbo_ratio', 0)
        
        # Score basé sur la cohérence L1==BBO
        if l1_bbo_ratio >= 0.8:
            l1_bbo_score = 1.0
            consistency = "EXCELLENT"
        elif l1_bbo_ratio >= 0.7:
            l1_bbo_score = 0.8
            consistency = "GOOD"
        elif l1_bbo_ratio >= 0.6:
            l1_bbo_score = 0.5
            consistency = "AVERAGE"
        elif l1_bbo_ratio >= 0.5:
            l1_bbo_score = 0.2
            consistency = "POOR"
        else:
            l1_bbo_score = 0.0
            consistency = "DEGRADED"
        
        # Gate passé si ratio >= seuil
        gate_passed = l1_bbo_ratio >= self.l1_bbo_threshold
        
        return L1BBOResult(
            l1_bbo_ratio=l1_bbo_ratio,
            l1_bbo_score=l1_bbo_score,
            consistency=consistency,
            gate_passed=gate_passed
        )
    
    # === DEPTH QUALITY (25%) ===
    
    def _analyze_depth_quality(self, dom_data: Dict[str, Any]) -> DepthQualityResult:
        """
        Analyse de la profondeur du carnet
        
        Args:
            dom_data: Données DOM
        
        Returns:
            DepthQualityResult
        """
        depth_levels = dom_data.get('depth_levels', 0)
        
        # Score basé sur le nombre de niveaux de profondeur
        if depth_levels >= 10:
            depth_score = 1.0
            quality = "EXCELLENT"
        elif depth_levels >= 5:
            depth_score = 0.7
            quality = "GOOD"
        elif depth_levels >= 3:
            depth_score = 0.4
            quality = "ACCEPTABLE"
        elif depth_levels >= 1:
            depth_score = 0.1
            quality = "POOR"
        else:
            depth_score = 0.0
            quality = "INSUFFICIENT"
        
        return DepthQualityResult(
            depth_levels=depth_levels,
            depth_score=depth_score,
            quality=quality
        )
    
    # === MÉTHODES UTILITAIRES ===
    
    def get_tick_size(self, symbol: str) -> float:
        """Récupère la taille du tick pour un symbole"""
        return self.tick_size_config.get(symbol, 0.25)
    
    def set_l1_bbo_threshold(self, threshold: float):
        """Met à jour le seuil L1==BBO"""
        self.l1_bbo_threshold = threshold
        logger.info(f"🔍 Seuil L1==BBO mis à jour: {threshold}")
    
    def get_l1_bbo_threshold(self) -> float:
        """Retourne le seuil L1==BBO actuel"""
        return self.l1_bbo_threshold
    
    def is_dom_healthy(self, dom_data: Dict[str, Any], symbol: str, 
                      min_score: float = 0.50) -> Tuple[bool, float]:
        """
        Vérifie si le DOM est sain
        
        Args:
            dom_data: Données DOM
            symbol: Symbole
            min_score: Score minimum requis
        
        Returns:
            Tuple (is_healthy, score)
        """
        result = self.calculate_dom_health(dom_data, symbol)
        is_healthy = result.dom_health_score >= min_score and result.gate_status["passed"]
        return is_healthy, result.dom_health_score
    
    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle"""
        return {
            'tick_size_config': self.tick_size_config,
            'l1_bbo_threshold': self.l1_bbo_threshold
        }
    
    def set_config(self, config: Dict[str, Any]):
        """Met à jour la configuration"""
        if 'tick_size_config' in config:
            self.tick_size_config.update(config['tick_size_config'])
        if 'l1_bbo_threshold' in config:
            self.l1_bbo_threshold = config['l1_bbo_threshold']
        logger.info("🔍 Configuration DOM Health Analyzer mise à jour")

# === INSTANCE GLOBALE ===

dom_health_analyzer = DOMHealthAnalyzer()

# === FONCTIONS DE CONVENIENCE ===

def get_dom_health_analyzer() -> DOMHealthAnalyzer:
    """Retourne l'instance globale de DOM Health Analyzer"""
    return dom_health_analyzer

def calculate_dom_health_quick(dom_data: Dict[str, Any], symbol: str) -> float:
    """Fonction de convenience pour calcul rapide"""
    result = dom_health_analyzer.calculate_dom_health(dom_data, symbol)
    return result.dom_health_score

def is_dom_healthy_quick(dom_data: Dict[str, Any], symbol: str, 
                        min_score: float = 0.50) -> bool:
    """Fonction de convenience pour vérification rapide"""
    is_healthy, _ = dom_health_analyzer.is_dom_healthy(dom_data, symbol, min_score)
    return is_healthy





