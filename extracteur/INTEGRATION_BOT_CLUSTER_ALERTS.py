#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTÉGRATION BOT - Cluster Alerts avec MIA Bullish
Comment le bot va interpréter les nouveaux signaux cluster sans supprimer MIA Bullish
"""

import json
from typing import Dict, Any, Optional

class ClusterAlertsProcessor:
    """
    Processeur des alertes cluster qui s'intègre avec MIA Bullish
    """
    
    def __init__(self):
        self.cluster_signals = {}
        self.confluence_signals = {}
        
    def process_cluster_alerts(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite les alertes cluster et retourne des signaux enrichis
        
        Args:
            market_data: Données de marché avec bloc menthorq.alerts
            
        Returns:
            Signaux enrichis pour le bot
        """
        alerts = market_data.get("menthorq", {}).get("alerts", {})
        if not alerts:
            return {"cluster_signals": None, "enhanced_confidence": 0.0}
        
        summary = alerts.get("summary", {})
        signals = summary.get("signals", {})
        nearest = summary.get("nearest_cluster", {})
        
        # === SIGNAL 1: CLUSTER CONFLUENCE ===
        cluster_signal = None
        if signals.get("cluster_confluence") and signals.get("cluster_strong"):
            cluster_signal = {
                "type": "cluster_confluence",
                "priority": "HIGH",
                "zone_min": nearest.get("zone_min"),
                "zone_max": nearest.get("zone_max"),
                "center": nearest.get("center"),
                "width_ticks": nearest.get("width_ticks"),
                "groups": nearest.get("groups"),
                "score": nearest.get("score"),
                "status": nearest.get("status"),
                "distance_ticks": nearest.get("distance_ticks"),
                "strategy": self._determine_cluster_strategy(nearest)
            }
        
        # === SIGNAL 2: CLUSTER TOUCH ===
        elif signals.get("cluster_touch"):
            cluster_signal = {
                "type": "cluster_touch",
                "priority": "MEDIUM",
                "strategy": "touch",
                "zone_min": nearest.get("zone_min"),
                "zone_max": nearest.get("zone_max"),
                "distance_ticks": nearest.get("distance_ticks")
            }
        
        # === SIGNAL 3: CONFLUENCE GAMMA + BLIND ===
        confluence_signal = None
        confluence = alerts.get("confluence")
        if confluence:
            confluence_strength = alerts.get("confluence_strength", 0.0)
            if confluence_strength >= 0.7:
                confluence_signal = {
                    "type": "confluence_strong",
                    "priority": "HIGH",
                    "strategy": "confluence",
                    "gamma_level": confluence["gamma"]["level_type"],
                    "blind_level": confluence["blind"]["level_type"],
                    "gamma_price": confluence["gamma"]["price"],
                    "blind_price": confluence["blind"]["price"],
                    "strength": confluence_strength
                }
        
        # === CALCUL DE CONFIANCE ENRICHIE ===
        enhanced_confidence = self._calculate_enhanced_confidence(alerts)
        
        return {
            "cluster_signals": cluster_signal,
            "confluence_signals": confluence_signal,
            "enhanced_confidence": enhanced_confidence,
            "raw_alerts": alerts  # Pour debug
        }
    
    def _determine_cluster_strategy(self, nearest: Dict[str, Any]) -> str:
        """Détermine la stratégie basée sur la position du prix"""
        status = nearest.get("status", "unknown")
        
        if status == "inside":
            return "fade"  # Prix dans le cluster → Fade
        elif status == "below":
            return "breakout"  # Prix sous le cluster → Breakout
        elif status == "above":
            return "breakdown"  # Prix au-dessus du cluster → Breakdown
        else:
            return "wait"  # Position incertaine → Attendre
    
    def _calculate_enhanced_confidence(self, alerts: Dict[str, Any]) -> float:
        """Calcule la confiance enrichie basée sur les alertes cluster"""
        base_confidence = 0.75  # Confiance de base
        
        # Bonus confluence
        confluence_strength = alerts.get("confluence_strength", 0.0)
        if confluence_strength >= 0.7:
            base_confidence += 0.1
        elif confluence_strength >= 0.5:
            base_confidence += 0.05
        
        # Bonus cluster strong
        summary = alerts.get("summary", {})
        signals = summary.get("signals", {})
        if signals.get("cluster_strong"):
            base_confidence += 0.1
        
        # Bonus cluster confluence
        if signals.get("cluster_confluence"):
            base_confidence += 0.05
        
        # Bonus cluster touch
        if signals.get("cluster_touch"):
            base_confidence += 0.03
        
        return min(1.0, base_confidence)

class MIAIntegrationExample:
    """
    Exemple d'intégration avec MIA Bullish existant
    """
    
    def __init__(self):
        self.cluster_processor = ClusterAlertsProcessor()
        self.bullish_scorer = None  # MIA Bullish existant
        
    def analyze_market_with_clusters(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse complète du marché avec clusters + MIA Bullish
        """
        # === 1) TRAITEMENT DES ALERTES CLUSTER ===
        cluster_result = self.cluster_processor.process_cluster_alerts(market_data)
        
        # === 2) MIA BULLISH EXISTANT (PRÉSERVÉ) ===
        bullish_result = None
        if self.bullish_scorer and 'sierra_events' in market_data:
            # Traiter les événements Sierra Chart avec le BullishScorer
            for event in market_data.get('sierra_events', []):
                try:
                    bullish_result = self.bullish_scorer.ingest(event)
                    if bullish_result:
                        break
                except Exception as e:
                    print(f"Erreur BullishScorer: {e}")
        
        # === 3) COMBINAISON DES SIGNAUX ===
        final_signal = self._combine_signals(cluster_result, bullish_result, market_data)
        
        return {
            "cluster_analysis": cluster_result,
            "bullish_analysis": bullish_result,
            "final_signal": final_signal,
            "timestamp": market_data.get("timestamp")
        }
    
    def _combine_signals(self, cluster_result: Dict[str, Any], 
                        bullish_result: Dict[str, Any], 
                        market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine les signaux cluster avec MIA Bullish
        """
        # === PRIORITÉ DES SIGNAUX ===
        cluster_signal = cluster_result.get("cluster_signals")
        confluence_signal = cluster_result.get("confluence_signals")
        
        # === LOGIQUE DE COMBINAISON ===
        if cluster_signal and cluster_signal.get("priority") == "HIGH":
            # Signal cluster prioritaire
            return {
                "type": "cluster_high_priority",
                "strategy": cluster_signal.get("strategy"),
                "confidence": cluster_result.get("enhanced_confidence", 0.75),
                "source": "cluster_alerts",
                "details": cluster_signal,
                "bullish_support": bullish_result is not None
            }
        
        elif confluence_signal and confluence_signal.get("priority") == "HIGH":
            # Signal confluence prioritaire
            return {
                "type": "confluence_high_priority",
                "strategy": confluence_signal.get("strategy"),
                "confidence": cluster_result.get("enhanced_confidence", 0.75),
                "source": "confluence_alerts",
                "details": confluence_signal,
                "bullish_support": bullish_result is not None
            }
        
        elif bullish_result:
            # MIA Bullish seul (logique existante préservée)
            return {
                "type": "bullish_only",
                "strategy": "bullish",
                "confidence": bullish_result.get("confidence", 0.7),
                "source": "mia_bullish",
                "details": bullish_result,
                "cluster_support": cluster_signal is not None
            }
        
        else:
            # Aucun signal
            return {
                "type": "no_signal",
                "confidence": 0.0,
                "source": "none"
            }

def example_integration():
    """
    Exemple d'intégration complète
    """
    # Simulation des données de marché
    market_data = {
        "symbol": "ESZ25_FUT_CME",
        "price": 6675.25,
        "timestamp": "2024-01-15T10:30:00Z",
        "menthorq": {
            "levels": [
                {"level_type": "gamma_wall_0dte", "price": 6675.50, "subgraph": 8},
                {"level_type": "blind_spot_3", "price": 6675.00, "subgraph": 3},
                {"level_type": "gex_5", "price": 6675.75, "subgraph": 13}
            ],
            "alerts": {
                "confluence": {
                    "type": "confluence",
                    "gamma": {"level_type": "gamma_wall_0dte", "price": 6675.50, "ticks": 1.0},
                    "blind": {"level_type": "blind_spot_3", "price": 6675.00, "ticks": 1.0}
                },
                "confluence_strength": 0.8,
                "summary": {
                    "nearest_cluster": {
                        "zone_min": 6675.00,
                        "zone_max": 6675.75,
                        "center": 6675.375,
                        "width_ticks": 3.0,
                        "groups": ["gamma", "blind", "gex"],
                        "score": 3.2,
                        "distance_ticks": 0.0,
                        "status": "inside"
                    },
                    "signals": {
                        "cluster_confluence": True,
                        "cluster_strong": True,
                        "cluster_touch": True
                    }
                }
            }
        },
        "sierra_events": [{"type": "trade", "price": 6675.25, "volume": 100}]
    }
    
    # Traitement
    mia_integration = MIAIntegrationExample()
    result = mia_integration.analyze_market_with_clusters(market_data)
    
    print("=== RÉSULTAT D'INTÉGRATION ===")
    print(json.dumps(result, indent=2, default=str))
    
    # === INTERPRÉTATION POUR LE BOT ===
    final_signal = result["final_signal"]
    
    if final_signal["type"] == "cluster_high_priority":
        print(f"\n🎯 SIGNAL CLUSTER PRIORITAIRE:")
        print(f"   Stratégie: {final_signal['strategy']}")
        print(f"   Confiance: {final_signal['confidence']:.2f}")
        print(f"   Support Bullish: {final_signal['bullish_support']}")
        
    elif final_signal["type"] == "confluence_high_priority":
        print(f"\n🎯 SIGNAL CONFLUENCE PRIORITAIRE:")
        print(f"   Stratégie: {final_signal['strategy']}")
        print(f"   Confiance: {final_signal['confidence']:.2f}")
        print(f"   Support Bullish: {final_signal['bullish_support']}")
        
    elif final_signal["type"] == "bullish_only":
        print(f"\n🎯 SIGNAL MIA BULLISH SEUL:")
        print(f"   Confiance: {final_signal['confidence']:.2f}")
        print(f"   Support Cluster: {final_signal['cluster_support']}")
        
    else:
        print(f"\n❌ AUCUN SIGNAL")

if __name__ == "__main__":
    example_integration()


























