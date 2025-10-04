# policy_overlay.py
# -*- coding: utf-8 -*-
"""
Policy Overlay pour gérer les seuils décisionnels
Basé sur les recommandations ChatGPT: gating par pressure_smooth et régime VIX/ATR
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Any
import json

class PolicyOverlay:
    """
    Overlay de politique pour gérer les seuils décisionnels
    avec gating par pressure_smooth et régime VIX/ATR
    """
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.vix_regimes = {
            'calm': (0, 15),
            'normal': (15, 25),
            'elevated': (25, 35),
            'high': (35, 100)
        }
        self.atr_regimes = {
            'low': (0, 0.5),
            'medium': (0.5, 1.0),
            'high': (1.0, 2.0),
            'extreme': (2.0, 10.0)
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration des seuils"""
        default_config = {
            'direction_thresholds': {
                'calm': {'low_atr': 0.6, 'medium_atr': 0.5, 'high_atr': 0.4, 'extreme_atr': 0.3},
                'normal': {'low_atr': 0.5, 'medium_atr': 0.4, 'high_atr': 0.3, 'extreme_atr': 0.2},
                'elevated': {'low_atr': 0.4, 'medium_atr': 0.3, 'high_atr': 0.2, 'extreme_atr': 0.15},
                'high': {'low_atr': 0.3, 'medium_atr': 0.2, 'high_atr': 0.15, 'extreme_atr': 0.1}
            },
            'touch_thresholds': {
                'calm': {'low_atr': 0.7, 'medium_atr': 0.6, 'high_atr': 0.5, 'extreme_atr': 0.4},
                'normal': {'low_atr': 0.6, 'medium_atr': 0.5, 'high_atr': 0.4, 'extreme_atr': 0.3},
                'elevated': {'low_atr': 0.5, 'medium_atr': 0.4, 'high_atr': 0.3, 'extreme_atr': 0.2},
                'high': {'low_atr': 0.4, 'medium_atr': 0.3, 'high_atr': 0.2, 'extreme_atr': 0.15}
            },
            'pressure_gates': {
                'min_pressure_abs': 0.2,  # Pression minimale absolue
                'pressure_multiplier': 1.5,  # Multiplicateur de confiance
                'max_confidence': 0.95  # Confiance maximale
            },
            'sizing_rules': {
                'base_size': 0.1,  # Taille de base (10%)
                'max_size': 0.3,   # Taille maximale (30%)
                'confidence_scaling': True,  # Scaling par confiance
                'regime_penalty': 0.5  # Pénalité en régime extrême
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"⚠️ Erreur chargement config: {e}, utilisation config par défaut")
        
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
                return f"{regime}_atr"  # Ajouter le suffixe _atr
        return 'extreme_atr'  # Fallback
    
    def get_dynamic_threshold(self, proba: float, vix: float, atr: float, 
                            target_type: str = 'direction') -> float:
        """Calcule le seuil dynamique basé sur VIX et ATR"""
        vix_regime = self.get_vix_regime(vix)
        atr_regime = self.get_atr_regime(atr)
        
        if target_type == 'direction':
            thresholds = self.config['direction_thresholds']
        else:  # touch
            thresholds = self.config['touch_thresholds']
        
        base_threshold = thresholds[vix_regime][atr_regime]
        
        # Ajustement par probabilité (plus la proba est élevée, plus on peut être strict)
        if proba > 0.8:
            adjusted_threshold = base_threshold * 1.2
        elif proba > 0.6:
            adjusted_threshold = base_threshold
        else:
            adjusted_threshold = base_threshold * 0.8
        
        return min(adjusted_threshold, 0.95)  # Cap à 95%
    
    def apply_pressure_gate(self, proba: float, pressure: float) -> Tuple[float, bool]:
        """Applique le gating par pression"""
        min_pressure = self.config['pressure_gates']['min_pressure_abs']
        multiplier = self.config['pressure_gates']['pressure_multiplier']
        max_conf = self.config['pressure_gates']['max_confidence']
        
        # Vérifier si la pression est suffisante
        pressure_abs = abs(pressure)
        if pressure_abs < min_pressure:
            return proba, False  # Pression insuffisante
        
        # Ajuster la confiance par la pression
        pressure_factor = min(pressure_abs * multiplier, 2.0)
        adjusted_proba = proba * pressure_factor
        
        # Cap à la confiance maximale
        adjusted_proba = min(adjusted_proba, max_conf)
        
        return adjusted_proba, True
    
    def calculate_position_size(self, proba: float, confidence: float, 
                              vix: float, atr: float) -> float:
        """Calcule la taille de position basée sur la confiance et le régime"""
        base_size = self.config['sizing_rules']['base_size']
        max_size = self.config['sizing_rules']['max_size']
        regime_penalty = self.config['sizing_rules']['regime_penalty']
        
        # Taille de base
        size = base_size
        
        # Scaling par confiance
        if self.config['sizing_rules']['confidence_scaling']:
            size *= confidence
        
        # Pénalité en régime extrême
        vix_regime = self.get_vix_regime(vix)
        atr_regime = self.get_atr_regime(atr)
        
        if vix_regime in ['elevated', 'high'] or atr_regime in ['high', 'extreme']:
            size *= regime_penalty
        
        # Cap à la taille maximale
        size = min(size, max_size)
        
        return size
    
    def make_decision(self, predictions: Dict[str, float], 
                     market_context: Dict[str, float]) -> Dict[str, Any]:
        """
        Prend une décision basée sur les prédictions et le contexte de marché
        
        Args:
            predictions: Dict avec les probabilités des modèles
            market_context: Dict avec vix, atr, pressure_smooth, etc.
        
        Returns:
            Dict avec la décision finale
        """
        vix = market_context.get('vix', 20.0)
        atr = market_context.get('atr', 1.0)
        pressure = market_context.get('pressure_smooth', 0.0)
        
        decision = {
            'timestamp': market_context.get('ts', pd.Timestamp.now()),
            'symbol': market_context.get('sym', 'UNKNOWN'),
            'signals': {},
            'final_decision': 'NO_GO',
            'confidence': 0.0,
            'position_size': 0.0,
            'reasoning': []
        }
        
        # Traiter chaque signal
        for signal_name, proba in predictions.items():
            if signal_name.startswith('y_dir_h'):
                # Signal de direction
                threshold = self.get_dynamic_threshold(proba, vix, atr, 'direction')
                adjusted_proba, pressure_ok = self.apply_pressure_gate(proba, pressure)
                
                if adjusted_proba > threshold and pressure_ok:
                    direction = 'BULLISH' if proba > 0.5 else 'BEARISH'
                    decision['signals'][signal_name] = {
                        'action': direction,
                        'probability': adjusted_proba,
                        'threshold': threshold,
                        'pressure_gated': True
                    }
                    decision['reasoning'].append(f"Direction {direction} (conf: {adjusted_proba:.3f})")
                else:
                    decision['signals'][signal_name] = {
                        'action': 'NO_GO',
                        'probability': adjusted_proba,
                        'threshold': threshold,
                        'pressure_gated': pressure_ok
                    }
            
            elif signal_name.startswith('y_touch_'):
                # Signal de touch
                threshold = self.get_dynamic_threshold(proba, vix, atr, 'touch')
                adjusted_proba, pressure_ok = self.apply_pressure_gate(proba, pressure)
                
                if adjusted_proba > threshold and pressure_ok:
                    decision['signals'][signal_name] = {
                        'action': 'TOUCH',
                        'probability': adjusted_proba,
                        'threshold': threshold,
                        'pressure_gated': True
                    }
                    decision['reasoning'].append(f"Touch {signal_name} (conf: {adjusted_proba:.3f})")
                else:
                    decision['signals'][signal_name] = {
                        'action': 'NO_GO',
                        'probability': adjusted_proba,
                        'threshold': threshold,
                        'pressure_gated': pressure_ok
                    }
        
        # Décision finale
        active_signals = [s for s in decision['signals'].values() 
                         if s['action'] != 'NO_GO' and s['pressure_gated']]
        
        if active_signals:
            # Prendre le signal avec la plus haute confiance
            best_signal = max(active_signals, key=lambda x: x['probability'])
            decision['final_decision'] = best_signal['action']
            decision['confidence'] = best_signal['probability']
            
            # Calculer la taille de position
            decision['position_size'] = self.calculate_position_size(
                best_signal['probability'], 
                best_signal['probability'],
                vix, atr
            )
        
        # Ajouter le contexte de marché
        decision['market_context'] = {
            'vix': vix,
            'vix_regime': self.get_vix_regime(vix),
            'atr': atr,
            'atr_regime': self.get_atr_regime(atr),
            'pressure': pressure,
            'pressure_abs': abs(pressure)
        }
        
        return decision
    
    def save_config(self, config_path: str):
        """Sauvegarde la configuration"""
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def update_config(self, updates: Dict):
        """Met à jour la configuration"""
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d
        
        self.config = deep_update(self.config, updates)

def create_sample_config() -> Dict:
    """Crée un exemple de configuration"""
    return {
        'direction_thresholds': {
            'calm': {'low_atr': 0.6, 'medium_atr': 0.5, 'high_atr': 0.4, 'extreme_atr': 0.3},
            'normal': {'low_atr': 0.5, 'medium_atr': 0.4, 'high_atr': 0.3, 'extreme_atr': 0.2},
            'elevated': {'low_atr': 0.4, 'medium_atr': 0.3, 'high_atr': 0.2, 'extreme_atr': 0.15},
            'high': {'low_atr': 0.3, 'medium_atr': 0.2, 'high_atr': 0.15, 'extreme_atr': 0.1}
        },
        'touch_thresholds': {
            'calm': {'low_atr': 0.7, 'medium_atr': 0.6, 'high_atr': 0.5, 'extreme_atr': 0.4},
            'normal': {'low_atr': 0.6, 'medium_atr': 0.5, 'high_atr': 0.4, 'extreme_atr': 0.3},
            'elevated': {'low_atr': 0.5, 'medium_atr': 0.4, 'high_atr': 0.3, 'extreme_atr': 0.2},
            'high': {'low_atr': 0.4, 'medium_atr': 0.3, 'high_atr': 0.2, 'extreme_atr': 0.15}
        },
        'pressure_gates': {
            'min_pressure_abs': 0.2,
            'pressure_multiplier': 1.5,
            'max_confidence': 0.95
        },
        'sizing_rules': {
            'base_size': 0.1,
            'max_size': 0.3,
            'confidence_scaling': True,
            'regime_penalty': 0.5
        }
    }

# Exemple d'utilisation
if __name__ == "__main__":
    # Créer la configuration
    config = create_sample_config()
    
    # Sauvegarder la config
    with open('policy_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Initialiser le policy overlay
    policy = PolicyOverlay('policy_config.json')
    
    # Exemple de décision
    predictions = {
        'y_dir_h': 0.75,
        'y_touch_vwap': 0.65,
        'y_touch_up1': 0.45
    }
    
    market_context = {
        'vix': 18.5,
        'atr': 0.8,
        'pressure_smooth': 0.3,
        'ts': pd.Timestamp.now(),
        'sym': 'ESZ25'
    }
    
    decision = policy.make_decision(predictions, market_context)
    
    print("🎯 DÉCISION POLICY OVERLAY:")
    print(f"Action: {decision['final_decision']}")
    print(f"Confiance: {decision['confidence']:.3f}")
    print(f"Taille: {decision['position_size']:.1%}")
    print(f"Raisonnement: {', '.join(decision['reasoning'])}")
    print(f"Contexte: VIX={decision['market_context']['vix_regime']}, ATR={decision['market_context']['atr_regime']}")
