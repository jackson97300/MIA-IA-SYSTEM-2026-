# policy_overlay_v2.py
# -*- coding: utf-8 -*-
"""
Policy Overlay v2 - Intégration des seuils adaptatifs basés sur VIX/ATR
"""

import json
import os
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from gated_predictions import gated_argmax, adaptive_thresholds

# Constantes pour les décisions gated
LABELS = [0, 1, 2]  # 0=Down, 1=Neutral, 2=Up

REGIME_CAP = {"calm": 1.00, "normal": 0.60, "elevated": 0.30, "high": 0.25}
REGIME_THR = {  # seuils directionnels (proba) pour BUY/SELL
    "calm": 0.30, "normal": 0.22, "elevated": 0.18, "high": 0.15
}
NEUTRAL_THR = {"calm": 0.70, "normal": 0.65, "elevated": 0.60, "high": 0.55}
PRESS_MIN = 0.20    # pression minimale absolue pour agir
MARGIN = 0.04       # marge anti-flip (diff up vs down)

@dataclass
class PolicyState:
    """État interne pour hystérésis et cooldown"""
    prev_side: int = 0  # -1, 0, +1
    since_sl: int = 0   # barres depuis stop loss
    daily_dd: float = 0.0  # drawdown journalier
    last_decision: str = "HOLD"

def vix_regime(vix: float) -> str:
    """Détermine le régime VIX"""
    if vix < 15:  return "calm"
    if vix < 25:  return "normal"
    if vix < 35:  return "elevated"
    return "high"

def gated_argmax_v2(proba: np.ndarray, regime: str, margin: float = MARGIN) -> Tuple[str, float]:
    """Retourne (decision, confidence) sans taille : BUY/SELL/HOLD"""
    p0, p1, p2 = proba  # down, neutral, up
    t_dir = REGIME_THR[regime]
    t_neu = NEUTRAL_THR[regime]

    # Neutralité forte → HOLD
    if p1 >= t_neu:
        return "HOLD", float(p1)

    # Choix directionnel avec marge anti-flip
    if p2 >= t_dir and (p2 - p0) >= margin:
        return "BUY", float(p2)
    if p0 >= t_dir and (p0 - p2) >= margin:
        return "SELL", float(p0)

    return "HOLD", float(max(p1, p0, p2))

def overlay_decision_v2(proba: np.ndarray, vix: float, atr: float, 
                       pressure_smooth: float, state: PolicyState, 
                       gamma_press: float = 0.75) -> Dict:
    """
    Décision overlay avec gating proba + pression + hystérésis
    
    Args:
        proba: [p_down, p_neutral, p_up]
        vix: valeur VIX
        atr: valeur ATR
        pressure_smooth: pression lissée
        state: état interne pour hystérésis
        gamma_press: exposant pour le facteur de pression
    
    Returns:
        dict avec decision, confidence, position, reason
    """
    regime = vix_regime(vix)
    cap = REGIME_CAP[regime]

    # Décision brute (gated)
    dec, conf = gated_argmax_v2(proba, regime)

    # Gating pression
    if abs(pressure_smooth) < PRESS_MIN and dec != "HOLD":
        return {
            "decision": "HOLD", 
            "confidence": 0.0, 
            "position": 0.0,
            "reason": f"Pressure too low ({pressure_smooth:.2f}) in {regime}"
        }

    # Hystérésis simple : si on inverse le sens, demande +marge
    side = {"SELL": -1, "HOLD": 0, "BUY": +1}[dec]
    if state.prev_side != 0 and side != 0 and side != state.prev_side:
        # exige marge extra pour flip
        extra = 0.02
        p0, p1, p2 = proba
        if side == +1 and (p2 - p0) < (MARGIN + extra):  # pas assez d'écart
            dec, side, conf = "HOLD", 0, p1
        if side == -1 and (p0 - p2) < (MARGIN + extra):
            dec, side, conf = "HOLD", 0, p1

    # Sizing régimique + pression (borné au cap)
    press_factor = max(0.0, min(1.0, abs(pressure_smooth))) ** gamma_press
    raw_size = conf * press_factor
    pos = min(cap, raw_size)

    # Mettre à jour l'état
    state.prev_side = side
    state.last_decision = dec

    return {
        "decision": dec, 
        "confidence": float(conf), 
        "position": float(pos),
        "reason": f"Model: {dec}, VIX: {vix:.1f} ({regime}), Conf: {conf:.3f}, Press: {pressure_smooth:.2f}, Cap: {cap:.2f}"
    }

class PolicyOverlayV2:
    """Policy Overlay avec seuils adaptatifs et décisions gated"""
    
    def __init__(self, config_path: str = "policy_config_v2.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.state = PolicyState()  # État interne pour hystérésis
        
        # Régimes VIX
        self.vix_regimes = {
            'calm': (0, 15),
            'normal': (15, 25), 
            'elevated': (25, 35),
            'high': (35, 100)
        }
        
        # Régimes ATR
        self.atr_regimes = {
            'low': (0, 0.5),
            'medium': (0.5, 1.0),
            'high': (1.0, 2.0),
            'extreme': (2.0, 10.0)
        }
    
    def _load_config(self) -> dict:
        """Charge la configuration ou crée une config par défaut"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Configuration par défaut
            default_config = {
                "base_thresholds": {
                    "t_down": 0.18,
                    "t_up": 0.18, 
                    "margin": 0.04
                },
                "regime_multipliers": {
                    "calm": 1.2,      # Plus conservateur
                    "normal": 1.0,    # Standard
                    "elevated": 0.8,  # Plus agressif
                    "high": 0.6       # Très agressif
                },
                "position_sizing": {
                    "max_position": 1.0,
                    "min_confidence": 0.15,
                    "risk_multiplier": 0.5
                },
                "gates": {
                    "min_vix": 10.0,
                    "max_vix": 50.0,
                    "min_atr": 0.1,
                    "max_atr": 5.0
                }
            }
            
            # Sauvegarder la config par défaut
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            return default_config
    
    def get_vix_regime(self, vix: float) -> str:
        """Détermine le régime VIX"""
        for regime, (min_val, max_val) in self.vix_regimes.items():
            if min_val <= vix < max_val:
                return regime
        return 'high'  # Fallback
    
    def get_atr_regime(self, atr: float) -> str:
        """Détermine le régime ATR"""
        for regime, (min_val, max_val) in self.atr_regimes.items():
            if min_val <= atr < max_val:
                return regime
        return 'extreme'  # Fallback
    
    def get_adaptive_thresholds(self, vix: float, atr: Optional[float] = None) -> Dict[str, float]:
        """Calcule les seuils adaptatifs basés sur VIX/ATR"""
        base = self.config["base_thresholds"]
        regime = self.get_vix_regime(vix)
        multiplier = self.config["regime_multipliers"].get(regime, 1.0)
        
        # Ajustement ATR si disponible
        if atr is not None:
            atr_regime = self.get_atr_regime(atr)
            if atr_regime in ['high', 'extreme']:
                multiplier *= 0.9  # Seuils légèrement plus bas en haute volatilité
        
        return {
            't_down': base['t_down'] * multiplier,
            't_up': base['t_up'] * multiplier,
            'margin': base['margin'] * multiplier
        }
    
    def make_decision(self, 
                     model_proba: np.ndarray,
                     vix: float,
                     atr: Optional[float] = None,
                     pressure_smooth: Optional[float] = None) -> Dict:
        """
        Prend une décision de trading basée sur le modèle et le contexte
        
        Args:
            model_proba: probabilités du modèle (3 classes: down, neutral, up)
            vix: valeur VIX actuelle
            atr: valeur ATR actuelle (optionnel)
            pressure_smooth: pression de marché lissée (optionnel)
        
        Returns:
            dict avec decision, confidence, position_size, context
        """
        # Vérifications de sécurité
        gates = self.config["gates"]
        if not (gates["min_vix"] <= vix <= gates["max_vix"]):
            return {
                'decision': 'HOLD',
                'confidence': 0.0,
                'position_size': 0.0,
                'reason': f'VIX hors limites: {vix:.2f}',
                'context': {'vix_regime': 'invalid', 'atr_regime': 'unknown'}
            }
        
        if atr is not None and not (gates["min_atr"] <= atr <= gates["max_atr"]):
            return {
                'decision': 'HOLD', 
                'confidence': 0.0,
                'position_size': 0.0,
                'reason': f'ATR hors limites: {atr:.2f}',
                'context': {'vix_regime': 'unknown', 'atr_regime': 'invalid'}
            }
        
        # Seuils adaptatifs
        thresholds = self.get_adaptive_thresholds(vix, atr)
        
        # Décision gated
        y_pred = gated_argmax(
            model_proba.reshape(1, -1), 
            thresholds['t_down'],
            thresholds['t_up'], 
            thresholds['margin']
        )[0]
        
        # Mapping des classes
        class_mapping = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        decision = class_mapping[y_pred]
        
        # Calcul de la confiance
        if y_pred == 1:  # Neutral
            confidence = model_proba[1]  # Probabilité neutre
        else:
            confidence = model_proba[y_pred]  # Probabilité de la classe choisie
        
        # Position sizing
        position_config = self.config["position_sizing"]
        if confidence < position_config["min_confidence"]:
            position_size = 0.0
        else:
            # Taille basée sur la confiance et le risque
            base_size = min(confidence, position_config["max_position"])
            
            # Ajustement par régime VIX
            vix_regime = self.get_vix_regime(vix)
            if vix_regime in ['elevated', 'high']:
                base_size *= position_config["risk_multiplier"]
            
            position_size = base_size
        
        # Contexte
        context = {
            'vix_regime': self.get_vix_regime(vix),
            'atr_regime': self.get_atr_regime(atr) if atr else 'unknown',
            'thresholds': thresholds,
            'model_proba': model_proba.tolist(),
            'pressure_smooth': pressure_smooth
        }
        
        return {
            'decision': decision,
            'confidence': float(confidence),
            'position_size': float(position_size),
            'reason': f'Model: {decision}, VIX: {vix:.1f} ({context["vix_regime"]}), Conf: {confidence:.3f}',
            'context': context
        }
    
    def batch_decisions(self, 
                       model_probas: np.ndarray,
                       vix_values: np.ndarray,
                       atr_values: Optional[np.ndarray] = None,
                       pressure_values: Optional[np.ndarray] = None) -> pd.DataFrame:
        """
        Prend des décisions en batch pour un dataset
        
        Args:
            model_probas: array (n, 3) des probabilités
            vix_values: array (n,) des valeurs VIX
            atr_values: array (n,) des valeurs ATR (optionnel)
            pressure_values: array (n,) des valeurs de pression (optionnel)
        
        Returns:
            DataFrame avec les décisions
        """
        n = len(model_probas)
        decisions = []
        
        for i in range(n):
            atr = atr_values[i] if atr_values is not None else None
            pressure = pressure_values[i] if pressure_values is not None else None
            
            decision = self.make_decision(
                model_probas[i], 
                vix_values[i], 
                atr, 
                pressure
            )
            decisions.append(decision)
        
        return pd.DataFrame(decisions)
    
    def make_decision_v2(self, 
                        model_proba: np.ndarray,
                        vix: float,
                        atr: float,
                        pressure_smooth: float,
                        gamma_press: float = 0.75) -> Dict:
        """
        Nouvelle méthode utilisant overlay_decision_v2 avec hystérésis
        
        Args:
            model_proba: probabilités du modèle (3 classes: down, neutral, up)
            vix: valeur VIX actuelle
            atr: valeur ATR actuelle
            pressure_smooth: pression de marché lissée
            gamma_press: exposant pour le facteur de pression
        
        Returns:
            dict avec decision, confidence, position, reason
        """
        return overlay_decision_v2(
            model_proba, vix, atr, pressure_smooth, self.state, gamma_press
        )

def test_policy_overlay():
    """Test du Policy Overlay avec les nouveaux scénarios"""
    policy = PolicyOverlayV2()
    
    # Test avec les nouveaux scénarios (p_down, p_neutral, p_up), vix, atr, pressure
    scenarios = [
        ([0.10, 0.80, 0.10], 12.0, 0.3, 0.40),  # Calm, neutre, pression OK
        ([0.30, 0.40, 0.30], 20.0, 0.7, 0.30),  # Normal, équilibré, pression OK
        ([0.35, 0.45, 0.20], 30.0, 1.2, 0.20),  # Elevated, neutre domine, pression limite
        ([0.55, 0.20, 0.25], 45.0, 2.0, 0.50),  # High, down, pression forte
    ]
    
    print("=== TEST POLICY OVERLAY V2 (NOUVEAUX SCÉNARIOS) ===")
    for i, (proba, vix, atr, pressure) in enumerate(scenarios, 1):
        decision = policy.make_decision_v2(
            np.array(proba), vix, atr, pressure
        )
        
        print(f"\nScénario {i}: VIX={vix}, ATR={atr}, Pressure={pressure}")
        print(f"  Proba: [Down={proba[0]:.2f}, Neutral={proba[1]:.2f}, Up={proba[2]:.2f}]")
        print(f"  Décision: {decision['decision']}")
        print(f"  Confiance: {decision['confidence']:.3f}")
        print(f"  Position: {decision['position']:.3f}")
        print(f"  Raison: {decision['reason']}")
    
    print("\n=== TEST ANCIENNE MÉTHODE (COMPARAISON) ===")
    for i, (proba, vix, atr, pressure) in enumerate(scenarios, 1):
        decision = policy.make_decision(
            np.array(proba), vix, atr
        )
        
        print(f"\nScénario {i} (ancien): VIX={vix}, ATR={atr}")
        print(f"  Décision: {decision['decision']}")
        print(f"  Confiance: {decision['confidence']:.3f}")
        print(f"  Position: {decision['position_size']:.3f}")
        print(f"  Raison: {decision['reason']}")

if __name__ == "__main__":
    test_policy_overlay()
