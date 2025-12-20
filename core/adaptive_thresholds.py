#!/usr/bin/env python3
"""
Adaptive Thresholds - Seuils Dynamiques
Calcul adaptatif basé sur rolling statistics

Sprint 2 - TODO Tasks 1a, 1b, 1c
Date: 13 Novembre 2025
"""

import logging
from typing import Dict, Optional, Tuple
from collections import deque
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """Régimes de volatilité"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class AdaptiveThresholds:
    """
    Calcul adaptatif des seuils
    
    - ATR adaptatif (max_vwap_distance)
    - Confidence adaptative (selon régime volatilité)
    - VWAP distance adaptative (rolling stats)
    
    Principe : Les seuils s'ajustent automatiquement aux conditions
    """
    
    def __init__(self):
        # Historiques rolling
        self.atr_history = deque(maxlen=100)
        self.vwap_distance_history = deque(maxlen=500)
        self.confidence_history = deque(maxlen=200)
        
        # Statistiques
        self.atr_median = None
        self.vwap_dist_std = None
        
        # Seuils de base (fallback)
        self.BASE_MAX_VWAP_DISTANCE = {
            "LOW": 3.0,
            "MEDIUM": 5.0,
            "HIGH": 8.0,
            "EXTREME": 12.0
        }
        
        self.BASE_MIN_CONFIDENCE = {
            "LOW": 0.35,     # Plus strict en faible volatilité
            "MEDIUM": 0.25,  # Normal
            "HIGH": 0.20,    # Moins strict en haute volatilité
            "EXTREME": 0.15  # Très permissif
        }
        
        # ATR minimum par instrument (pour normalisation)
        self.ATR_MIN_REFERENCE = {
            'ES': 3.0,
            'NQ': 10.0,
            'RTY': 2.0
        }
        
        logger.info("🔧 AdaptiveThresholds initialisé")
    
    def update(self, snapshot: Dict):
        """
        Met à jour historiques avec nouveau snapshot
        
        Args:
            snapshot: Données ML_READY
        """
        # ATR
        atr = snapshot.get('atr', 1.0)
        if atr > 0:
            self.atr_history.append(atr)
        
        # VWAP distance
        d_vwap_ticks = abs(snapshot.get('d_vwap_ticks', 0))
        if d_vwap_ticks > 0:
            self.vwap_distance_history.append(d_vwap_ticks)
        
        # Recalculer stats
        if len(self.atr_history) >= 50:
            self.atr_median = np.median(list(self.atr_history))
        
        if len(self.vwap_distance_history) >= 100:
            self.vwap_dist_std = np.std(list(self.vwap_distance_history))
    
    def get_max_vwap_distance_atr(
        self,
        current_atr: float,
        symbol: str,
        session: str = "LONDON"
    ) -> float:
        """
        Calcul adaptatif max_vwap_distance (en ATR)
        
        Logique :
        1. Si ATR actuel < ATR médian → Ajuster seuil
        2. Selon régime volatilité → Ajuster seuil
        3. Selon session → Ajuster seuil
        
        Args:
            current_atr: ATR actuel
            symbol: ES/NQ/RTY
            session: ASIA/LONDON/US
            
        Returns:
            max_vwap_distance en ATR
        """
        # Déterminer régime volatilité
        regime = self.get_volatility_regime(current_atr, symbol)
        
        # Seuil de base selon régime
        base_threshold = self.BASE_MAX_VWAP_DISTANCE[regime.value]
        
        # Ajustement si ATR anormalement bas
        if self.atr_median and current_atr < self.atr_median * 0.5:
            # ATR faible → Augmenter seuil
            adjustment = self.atr_median / current_atr
            base_threshold *= min(adjustment, 2.5)  # Cap à 2.5x
            
            logger.debug(
                "🔧 ATR Adaptatif: ATR=%.2f < median=%.2f → Seuil ajusté x%.2f",
                current_atr,
                self.atr_median,
                adjustment
            )
        
        # Ajustement selon session
        session_multiplier = {
            "ASIA": 1.2,   # Plus permissif
            "LONDON": 1.0,
            "US": 0.9      # Plus strict
        }.get(session, 1.0)
        
        final_threshold = base_threshold * session_multiplier
        
        return final_threshold
    
    def get_min_confidence(
        self,
        current_atr: float,
        symbol: str
    ) -> float:
        """
        Calcul adaptatif min_confidence
        
        Logique :
        - Volatilité LOW → Plus strict (0.35)
        - Volatilité HIGH → Moins strict (0.20)
        - Volatilité EXTREME → Très permissif (0.15)
        
        Args:
            current_atr: ATR actuel
            symbol: ES/NQ/RTY
            
        Returns:
            min_confidence
        """
        regime = self.get_volatility_regime(current_atr, symbol)
        
        min_confidence = self.BASE_MIN_CONFIDENCE[regime.value]
        
        logger.debug(
            "🔧 Confidence Adaptative: Régime=%s → min_confidence=%.2f",
            regime.value,
            min_confidence
        )
        
        return min_confidence
    
    def get_max_vwap_distance_ticks(
        self,
        symbol: str
    ) -> float:
        """
        Calcul adaptatif max_vwap_distance (en ticks)
        
        Utilise rolling_std des distances VWAP historiques
        
        Args:
            symbol: ES/NQ/RTY
            
        Returns:
            max_vwap_distance en ticks
        """
        if not self.vwap_dist_std or self.vwap_dist_std == 0:
            # Fallback seuils par défaut
            fallback = {
                'ES': 60,
                'NQ': 150,
                'RTY': 40
            }.get(symbol, 60)
            
            return fallback
        
        # Utiliser 2.5 * rolling_std
        adaptive_threshold = self.vwap_dist_std * 2.5
        
        logger.debug(
            "🔧 VWAP Distance Adaptive: std=%.1f → max_distance=%.1f ticks",
            self.vwap_dist_std,
            adaptive_threshold
        )
        
        return adaptive_threshold
    
    def get_volatility_regime(
        self,
        current_atr: float,
        symbol: str
    ) -> VolatilityRegime:
        """
        Détermine régime de volatilité
        
        Args:
            current_atr: ATR actuel
            symbol: ES/NQ/RTY
            
        Returns:
            VolatilityRegime
        """
        if not self.atr_median:
            return VolatilityRegime.MEDIUM
        
        # Ratio ATR actuel / ATR médian
        ratio = current_atr / self.atr_median
        
        if ratio < 0.5:
            return VolatilityRegime.LOW
        elif ratio < 1.2:
            return VolatilityRegime.MEDIUM
        elif ratio < 2.0:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def get_normalized_atr(
        self,
        current_atr: float,
        symbol: str
    ) -> float:
        """
        Retourne ATR normalisé (min reference)
        
        Si ATR actuel < ATR min, utilise ATR min
        
        Args:
            current_atr: ATR actuel
            symbol: ES/NQ/RTY
            
        Returns:
            ATR normalisé
        """
        atr_min = self.ATR_MIN_REFERENCE.get(symbol, 3.0)
        
        return max(current_atr, atr_min)
    
    def get_adaptive_thresholds(
        self,
        snapshot: Dict
    ) -> Dict:
        """
        Retourne tous les seuils adaptatifs pour un snapshot
        
        Args:
            snapshot: Données ML_READY
            
        Returns:
            Dict avec tous les seuils calculés
        """
        # Extraire données
        sym = snapshot.get('sym', 'ES')
        if 'ES' in sym:
            symbol = 'ES'
        elif 'NQ' in sym:
            symbol = 'NQ'
        elif 'RTY' in sym or '2RTY' in sym:
            symbol = 'RTY'
        else:
            symbol = 'ES'
        
        current_atr = snapshot.get('atr', 1.0)
        session = snapshot.get('session_id', 'LONDON')
        
        # Calculer tous les seuils
        max_vwap_distance_atr = self.get_max_vwap_distance_atr(
            current_atr, symbol, session
        )
        
        min_confidence = self.get_min_confidence(current_atr, symbol)
        
        max_vwap_distance_ticks = self.get_max_vwap_distance_ticks(symbol)
        
        atr_normalized = self.get_normalized_atr(current_atr, symbol)
        
        regime = self.get_volatility_regime(current_atr, symbol)
        
        return {
            'max_vwap_distance_atr': max_vwap_distance_atr,
            'min_confidence': min_confidence,
            'max_vwap_distance_ticks': max_vwap_distance_ticks,
            'atr_normalized': atr_normalized,
            'volatility_regime': regime.value,
            'atr_median': self.atr_median,
            'vwap_dist_std': self.vwap_dist_std
        }


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Créer instance
    adaptive = AdaptiveThresholds()
    
    # Simuler historique
    print("📊 Simulation historique ATR...")
    for i in range(100):
        snapshot = {
            'sym': 'ESZ25',
            'atr': 5.0 + np.random.randn() * 2.0,  # Mean 5, std 2
            'd_vwap_ticks': abs(np.random.randn() * 50),
            'session_id': 'LONDON'
        }
        adaptive.update(snapshot)
    
    print(f"ATR median: {adaptive.atr_median:.2f}")
    print(f"VWAP dist std: {adaptive.vwap_dist_std:.2f}")
    
    # Test avec ATR normal
    print("\n" + "=" * 60)
    print("TEST 1: ATR Normal (5.0)")
    print("=" * 60)
    
    snapshot_normal = {
        'sym': 'ESZ25',
        'atr': 5.0,
        'd_vwap_ticks': 45,
        'session_id': 'LONDON'
    }
    
    thresholds = adaptive.get_adaptive_thresholds(snapshot_normal)
    print(json.dumps(thresholds, indent=2, default=str))
    
    # Test avec ATR anormalement bas
    print("\n" + "=" * 60)
    print("TEST 2: ATR Anormalement Bas (1.14)")
    print("=" * 60)
    
    snapshot_low_atr = {
        'sym': 'ESZ25',
        'atr': 1.14,
        'd_vwap_ticks': 60,
        'session_id': 'LONDON'
    }
    
    thresholds_low = adaptive.get_adaptive_thresholds(snapshot_low_atr)
    print(json.dumps(thresholds_low, indent=2, default=str))
    
    # Test avec ATR très haut
    print("\n" + "=" * 60)
    print("TEST 3: ATR Très Haut (15.0 - Crash)")
    print("=" * 60)
    
    snapshot_high_atr = {
        'sym': 'ESZ25',
        'atr': 15.0,
        'd_vwap_ticks': 200,
        'session_id': 'LONDON'
    }
    
    thresholds_high = adaptive.get_adaptive_thresholds(snapshot_high_atr)
    print(json.dumps(thresholds_high, indent=2, default=str))
    
    import json

