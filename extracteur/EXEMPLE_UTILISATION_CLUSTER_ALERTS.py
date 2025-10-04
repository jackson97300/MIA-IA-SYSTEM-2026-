#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemple d'utilisation des alertes cluster/niveau option proche
Intégration dans la logique de trading du bot MIA
"""

import json
from typing import Dict, Any, Optional

def process_unified_alerts(unified_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Traite les alertes unifiées et retourne des signaux de trading
    
    Args:
        unified_row: Ligne du fichier unified_YYYYMMDD.jsonl
        
    Returns:
        Dict avec les signaux de trading générés
    """
    alerts = unified_row.get("alerts") or {}
    summary = alerts.get("summary") or {}
    nearest = summary.get("nearest_cluster") or {}
    signals = summary.get("signals") or {}
    
    # === SIGNAL 1: CLUSTER CONFLUENCE ===
    if signals.get("cluster_confluence") and signals.get("cluster_strong"):
        # Zone prioritaire : cluster multi-groupes et fort
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
            "distance_ticks": nearest.get("distance_ticks")
        }
        
        # Logique de trading selon la position
        if nearest.get("status") == "inside":
            # Prix dans le cluster → Fade strategy
            cluster_signal["strategy"] = "fade"
            cluster_signal["stop_loss"] = 1-2  # ticks au-delà du bord opposé
            cluster_signal["target"] = nearest.get("center")
        elif nearest.get("status") == "below":
            # Prix sous le cluster → Breakout strategy
            cluster_signal["strategy"] = "breakout"
            cluster_signal["entry_trigger"] = nearest.get("zone_max") + 0.5  # 0.5 tick au-dessus
            cluster_signal["stop_loss"] = nearest.get("zone_min") - 1.0
            cluster_signal["target"] = nearest.get("zone_max") + 3.0
        else:  # above
            # Prix au-dessus du cluster → Breakdown strategy
            cluster_signal["strategy"] = "breakdown"
            cluster_signal["entry_trigger"] = nearest.get("zone_min") - 0.5  # 0.5 tick en-dessous
            cluster_signal["stop_loss"] = nearest.get("zone_max") + 1.0
            cluster_signal["target"] = nearest.get("zone_min") - 3.0
            
        return cluster_signal
    
    # === SIGNAL 2: CLUSTER TOUCH ===
    elif signals.get("cluster_touch"):
        # Prix au bord du cluster → Touch strategy
        return {
            "type": "cluster_touch",
            "priority": "MEDIUM",
            "strategy": "touch",
            "zone_min": nearest.get("zone_min"),
            "zone_max": nearest.get("zone_max"),
            "distance_ticks": nearest.get("distance_ticks"),
            "stop_loss": 2.0,  # 2 ticks
            "target": nearest.get("center")
        }
    
    # === SIGNAL 3: CONFLUENCE GAMMA + BLIND ===
    confluence = alerts.get("confluence")
    if confluence:
        confluence_strength = alerts.get("confluence_strength", 0.0)
        if confluence_strength >= 0.7:
            return {
                "type": "confluence_strong",
                "priority": "HIGH",
                "strategy": "confluence",
                "gamma_level": confluence["gamma"]["level_type"],
                "blind_level": confluence["blind"]["level_type"],
                "gamma_price": confluence["gamma"]["price"],
                "blind_price": confluence["blind"]["price"],
                "strength": confluence_strength,
                "stop_loss": 2.0,
                "target": confluence["gamma"]["price"]  # Target vers le niveau gamma
            }
    
    return {"type": "no_signal"}

def calculate_menthorq_confidence(base_confidence: float, alerts: Dict[str, Any]) -> float:
    """
    Calcule la confiance MenthorQ en fonction des alertes
    
    Args:
        base_confidence: Confiance de base de la stratégie
        alerts: Bloc alerts du fichier unifié
        
    Returns:
        Confiance ajustée (0.0 à 1.0)
    """
    bonus = 0.0
    
    # Bonus confluence
    confluence_strength = alerts.get("confluence_strength", 0.0)
    if confluence_strength >= 0.7:
        bonus += 0.1
    elif confluence_strength >= 0.5:
        bonus += 0.05
    
    # Bonus cluster strong
    summary = alerts.get("summary", {})
    signals = summary.get("signals", {})
    if signals.get("cluster_strong"):
        bonus += 0.1
    
    # Bonus cluster confluence
    if signals.get("cluster_confluence"):
        bonus += 0.05
    
    # Bonus cluster touch
    if signals.get("cluster_touch"):
        bonus += 0.03
    
    return min(1.0, base_confidence + bonus)

def example_usage():
    """
    Exemple d'utilisation complète
    """
    # Simulation d'une ligne unifiée
    unified_row = {
        "t": 45917.123456,
        "sym": "ESZ25_FUT_CME",
        "basedata": {"c": 6675.25, "v": 1500},
        "menthorq_levels": [
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
            "clusters": [
                {
                    "type": "cluster",
                    "zone_min": 6675.00,
                    "zone_max": 6675.75,
                    "center": 6675.375,
                    "width_ticks": 3.0,
                    "groups": ["gamma", "blind", "gex"],
                    "score": 3.2
                }
            ],
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
    }
    
    # Traitement des alertes
    signal = process_unified_alerts(unified_row)
    print("Signal généré:", json.dumps(signal, indent=2))
    
    # Calcul de la confiance
    base_confidence = 0.75
    adjusted_confidence = calculate_menthorq_confidence(base_confidence, unified_row["alerts"])
    print(f"Confiance ajustée: {adjusted_confidence:.2f}")

if __name__ == "__main__":
    example_usage()


























