#!/usr/bin/env python3
"""
🎯 CONFLUENCE INTEGRATOR - MIA_IA_SYSTEM
========================================

Module d'intégration confluence extrait du fichier monstre
- Calcul de confluence avec leadership
- Intégration des scores multiples
- Validation des signaux
- Gestion des seuils adaptatifs
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Ajouter le chemin du projet
sys.path.append(str(Path(__file__).parent.parent))

from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ConfluenceResult:
    """Résultat de calcul de confluence"""
    base_score: float
    leadership_gate: float
    risk_multiplier: float
    final_score: float
    is_valid: bool
    decision: str
    leader: Optional[str]
    confidence: float
    alignment: str

class ConfluenceIntegrator:
    """Intégrateur de confluence avec leadership"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.last_confluence_score = 0.0
        self.confluence_history = []
        
        logger.info("🎯 Confluence Integrator initialisé")
    
    def calculate_confluence_with_leadership(self, market_data: Dict[str, Any]) -> ConfluenceResult:
        """Calcule la confluence avec intégration leadership"""
        try:
            # Extraction des données
            es_data = market_data.get('ES', {})
            nq_data = market_data.get('NQ', {})
            bias = market_data.get('bias', 'neutral')
            session = market_data.get('session', 'unknown')
            
            # Calcul du score de base
            base_score = self._calculate_base_confluence_score(es_data, nq_data, bias)
            
            # Calcul du leadership gate
            leadership_gate = self._calculate_leadership_gate(es_data, nq_data)
            
            # Calcul du multiplicateur de risque
            risk_multiplier = self._calculate_risk_multiplier(session, bias)
            
            # Score final avec intégration leadership
            final_score = base_score * leadership_gate * risk_multiplier
            
            # Validation du signal
            is_valid = self._validate_confluence_signal(final_score, leadership_gate)
            
            # Décision
            decision = self._make_decision(final_score, is_valid)
            
            # Détermination du leader
            leader = self._determine_leader(es_data, nq_data, leadership_gate)
            
            # Alignement
            alignment = self._determine_alignment(final_score, leadership_gate)
            
            # Confiance
            confidence = min(1.0, final_score * 1.5)
            
            # Créer le résultat
            result = ConfluenceResult(
                base_score=base_score,
                leadership_gate=leadership_gate,
                risk_multiplier=risk_multiplier,
                final_score=final_score,
                is_valid=is_valid,
                decision=decision,
                leader=leader,
                confidence=confidence,
                alignment=alignment
            )
            
            # Sauvegarder l'historique
            self.confluence_history.append({
                'timestamp': datetime.now(),
                'result': result,
                'market_data': market_data
            })
            
            # Limiter l'historique
            if len(self.confluence_history) > 100:
                self.confluence_history = self.confluence_history[-100:]
            
            logger.info(f"🎯 Confluence calculée: {final_score:.3f} (base: {base_score:.3f}, gate: {leadership_gate:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul confluence: {e}")
            return self._create_fallback_result()
    
    def _calculate_base_confluence_score(self, es_data: Dict, nq_data: Dict, bias: str) -> float:
        """Calcule le score de confluence de base"""
        try:
            # Scores individuels
            es_score = self._calculate_instrument_score(es_data, 'ES')
            nq_score = self._calculate_instrument_score(nq_data, 'NQ')
            
            # Score de corrélation
            correlation_score = self._calculate_correlation_score(es_data, nq_data)
            
            # Score de biais
            bias_score = self._calculate_bias_score(bias)
            
            # Score composite
            base_score = (
                es_score * 0.3 +
                nq_score * 0.3 +
                correlation_score * 0.25 +
                bias_score * 0.15
            )
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul score base: {e}")
            return 0.5
    
    def _calculate_instrument_score(self, data: Dict, symbol: str) -> float:
        """Calcule le score pour un instrument"""
        try:
            # Données simulées si pas de données réelles - calcul déterministe
            if not data:
                # Score de base déterministe basé sur le symbole
                base_scores = {'ES': 0.65, 'NQ': 0.60, 'YM': 0.55, 'RTY': 0.50}
                return base_scores.get(symbol, 0.60)
            
            # 🔧 CORRECTION: Gestion des DataFrames pandas
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                # Extraire les dernières données du DataFrame
                if len(data) > 0:
                    latest = data.iloc[-1]
                    volume = latest.get('volume', 1000)
                    close = latest.get('close', 4500.0 if symbol == 'ES' else 15000.0)
                    
                    # Calculer la volatilité basée sur high/low
                    high = latest.get('high', close + 5)
                    low = latest.get('low', close - 5)
                    volatility = (high - low) / close if close > 0 else 0.01
                    
                    # Calculer le momentum basé sur open/close
                    open_price = latest.get('open', close)
                    momentum = (close - open_price) / open_price if open_price > 0 else 0.0
                    
                    # Score composite amélioré
                    volume_score = min(1.0, volume / 1000.0)
                    price_score = 0.5 + (close - (4500.0 if symbol == 'ES' else 15000.0)) / 1000.0
                    volatility_score = 1.0 - abs(volatility - 0.01)  # Optimal à 1%
                    momentum_score = abs(momentum)
                    
                    return (volume_score * 0.4 + price_score * 0.2 + volatility_score * 0.2 + momentum_score * 0.2)
                else:
                    # Score déterministe basé sur le symbole
                    base_scores = {'ES': 0.55, 'NQ': 0.50, 'YM': 0.45, 'RTY': 0.40}
                    return base_scores.get(symbol, 0.50)
            
            # Traitement des dictionnaires (ancien format)
            volume = data.get('volume', 1000)
            price = data.get('price', 4500.0 if symbol == 'ES' else 15000.0)
            
            # Normalisation
            volume_score = min(1.0, volume / 1000.0)
            price_score = 0.5 + (price - (4500.0 if symbol == 'ES' else 15000.0)) / 1000.0
            
            return (volume_score * 0.6 + price_score * 0.4)
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul score instrument {symbol}: {e}")
            return 0.5
    
    def _calculate_correlation_score(self, es_data: Dict, nq_data: Dict) -> float:
        """Calcule le score de corrélation ES/NQ"""
        try:
            # 🔧 CORRECTION: Calcul de corrélation réelle avec DataFrames
            import pandas as pd
            import numpy as np
            
            if isinstance(es_data, pd.DataFrame) and isinstance(nq_data, pd.DataFrame):
                if len(es_data) > 5 and len(nq_data) > 5:
                    # Utiliser les prix de clôture pour la corrélation
                    es_prices = es_data['close'].values
                    nq_prices = nq_data['close'].values
                    
                    # S'assurer que les arrays ont la même longueur
                    min_len = min(len(es_prices), len(nq_prices))
                    es_prices = es_prices[-min_len:]
                    nq_prices = nq_prices[-min_len:]
                    
                    # Calculer la corrélation
                    if min_len > 2:
                        correlation = np.corrcoef(es_prices, nq_prices)[0, 1]
                        
                        # Gestion des valeurs NaN
                        if np.isnan(correlation):
                            logger.warning("⚠️ Corrélation NaN détectée → 0.0")
                            return 0.0
                        
                        return max(0.0, min(1.0, abs(correlation)))
                    else:
                        logger.warning("⚠️ Pas assez de données pour corrélation → calcul déterministe")
                        # Corrélation déterministe basée sur les paires d'instruments
                        correlation_map = {
                            ('ES', 'NQ'): 0.88, ('ES', 'YM'): 0.82, ('ES', 'RTY'): 0.75,
                            ('NQ', 'YM'): 0.85, ('NQ', 'RTY'): 0.70, ('YM', 'RTY'): 0.78
                        }
                        return correlation_map.get((symbol, 'ES'), 0.80)
                else:
                    logger.warning("⚠️ DataFrames trop courts → calcul déterministe")
                    # Corrélation déterministe basée sur les paires d'instruments
                    correlation_map = {
                        ('ES', 'NQ'): 0.88, ('ES', 'YM'): 0.82, ('ES', 'RTY'): 0.75,
                        ('NQ', 'YM'): 0.85, ('NQ', 'RTY'): 0.70, ('YM', 'RTY'): 0.78
                    }
                    return correlation_map.get((symbol, 'ES'), 0.80)
            
            # Fallback: Corrélation déterministe
            base_correlation = 0.85
            # Variation déterministe basée sur le symbole (hash simple)
            symbol_hash = hash(symbol) % 100
            variation = (symbol_hash - 50) / 500.0  # -0.1 à +0.1
            correlation = base_correlation + variation
            
            # Gestion des valeurs NaN
            if correlation != correlation:  # NaN check
                logger.warning("⚠️ Corrélation NaN détectée → 0.0")
                return 0.0
            
            return max(0.0, min(1.0, abs(correlation)))
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul corrélation: {e}")
            return 0.5
    
    def _calculate_bias_score(self, bias: str) -> float:
        """Calcule le score de biais"""
        try:
            bias_scores = {
                'bullish': 0.8,
                'bearish': 0.2,
                'neutral': 0.5
            }
            
            return bias_scores.get(bias, 0.5)
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul biais: {e}")
            return 0.5
    
    def _calculate_leadership_gate(self, es_data: Dict, nq_data: Dict) -> float:
        """Calcule le gate de leadership"""
        try:
            # Analyse de leadership basique
            es_strength = self._calculate_leadership_strength(es_data, 'ES')
            nq_strength = self._calculate_leadership_strength(nq_data, 'NQ')
            
            # Gate basé sur la différence de force
            strength_diff = abs(es_strength - nq_strength)
            leadership_gate = 0.5 + (strength_diff * 0.5)
            
            return max(0.1, min(1.0, leadership_gate))
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul leadership gate: {e}")
            return 0.5
    
    def _calculate_leadership_strength(self, data: Dict, symbol: str) -> float:
        """Calcule la force de leadership d'un instrument"""
        try:
            if not data:
                # Force de leadership déterministe basée sur le symbole
                leadership_strength = {'ES': 0.7, 'NQ': 0.6, 'YM': 0.5, 'RTY': 0.4}
                return leadership_strength.get(symbol, 0.5)
            
            # 🔧 CORRECTION: Gestion des DataFrames pandas
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                if len(data) > 0:
                    latest = data.iloc[-1]
                    
                    # Extraire les données du DataFrame
                    volume = latest.get('volume', 1000)
                    close = latest.get('close', 4500.0 if symbol == 'ES' else 15000.0)
                    high = latest.get('high', close + 5)
                    low = latest.get('low', close - 5)
                    open_price = latest.get('open', close)
                    
                    # Calculer les facteurs
                    volatility = (high - low) / close if close > 0 else 0.01
                    momentum = (close - open_price) / open_price if open_price > 0 else 0.0
                    
                    # Score composite
                    volume_factor = min(1.0, volume / 1000.0)
                    volatility_factor = 1.0 - abs(volatility - 0.01)  # Optimal à 1%
                    momentum_factor = abs(momentum)
                    
                    strength = (
                        volume_factor * 0.4 +
                        volatility_factor * 0.3 +
                        momentum_factor * 0.3
                    )
                    
                    return max(0.0, min(1.0, strength))
                else:
                    # Force de leadership déterministe basée sur le symbole
                    leadership_strength = {'ES': 0.6, 'NQ': 0.5, 'YM': 0.4, 'RTY': 0.3}
                    return leadership_strength.get(symbol, 0.5)
            
            # Traitement des dictionnaires (ancien format)
            volume = data.get('volume', 1000)
            volatility = data.get('volatility', 0.5)
            momentum = data.get('momentum', 0.0)
            
            # Score composite
            volume_factor = min(1.0, volume / 1000.0)
            volatility_factor = 1.0 - abs(volatility - 0.5)  # Optimal à 0.5
            momentum_factor = abs(momentum)
            
            strength = (
                volume_factor * 0.4 +
                volatility_factor * 0.3 +
                momentum_factor * 0.3
            )
            
            return max(0.0, min(1.0, strength))
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul force leadership {symbol}: {e}")
            return 0.5
    
    def _calculate_risk_multiplier(self, session: str, bias: str) -> float:
        """Calcule le multiplicateur de risque"""
        try:
            # Multiplicateurs par session
            session_multipliers = {
                'london_session': 1.2,
                'new_york_session': 1.0,
                'asian_session': 0.8,
                'unknown': 1.0
            }
            
            # Multiplicateurs par biais
            bias_multipliers = {
                'bullish': 1.1,
                'bearish': 0.9,
                'neutral': 1.0
            }
            
            session_mult = session_multipliers.get(session, 1.0)
            bias_mult = bias_multipliers.get(bias, 1.0)
            
            return session_mult * bias_mult
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul multiplicateur risque: {e}")
            return 1.0
    
    def _validate_confluence_signal(self, final_score: float, leadership_gate: float) -> bool:
        """Valide le signal de confluence"""
        try:
            # Seuils de validation
            min_score = self.config.get('min_confluence_score', 0.3)
            min_leadership = self.config.get('min_leadership_gate', 0.4)
            
            # Validation
            score_valid = final_score >= min_score
            leadership_valid = leadership_gate >= min_leadership
            
            return score_valid and leadership_valid
            
        except Exception as e:
            logger.error(f"❌ Erreur validation confluence: {e}")
            return False
    
    def _make_decision(self, final_score: float, is_valid: bool) -> str:
        """Prend une décision basée sur le score final"""
        try:
            if not is_valid:
                return 'REJECT'
            
            if final_score >= 0.7:
                return 'STRONG_BUY'
            elif final_score >= 0.5:
                return 'BUY'
            elif final_score >= 0.3:
                return 'WEAK_BUY'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"❌ Erreur décision: {e}")
            return 'NEUTRAL'
    
    def _determine_leader(self, es_data: Dict, nq_data: Dict, leadership_gate: float) -> Optional[str]:
        """Détermine l'instrument leader"""
        try:
            if leadership_gate < 0.5:
                return None  # Pas de leader clair
            
            es_strength = self._calculate_leadership_strength(es_data, 'ES')
            nq_strength = self._calculate_leadership_strength(nq_data, 'NQ')
            
            if es_strength > nq_strength * 1.1:
                return 'ES'
            elif nq_strength > es_strength * 1.1:
                return 'NQ'
            else:
                return None  # Leadership partagé
                
        except Exception as e:
            logger.error(f"❌ Erreur détermination leader: {e}")
            return None
    
    def _determine_alignment(self, final_score: float, leadership_gate: float) -> str:
        """Détermine l'alignement du signal"""
        try:
            if final_score >= 0.7 and leadership_gate >= 0.6:
                return 'strong_leader'
            elif final_score >= 0.5 and leadership_gate >= 0.4:
                return 'moderate_leader'
            elif final_score >= 0.3:
                return 'weak_signal'
            else:
                return 'no_signal'
                
        except Exception as e:
            logger.error(f"❌ Erreur détermination alignement: {e}")
            return 'no_signal'
    
    def _create_fallback_result(self) -> ConfluenceResult:
        """Crée un résultat de fallback"""
        return ConfluenceResult(
            base_score=0.5,
            leadership_gate=0.5,
            risk_multiplier=1.0,
            final_score=0.25,
            is_valid=False,
            decision='NEUTRAL',
            leader=None,
            confidence=0.25,
            alignment='no_signal'
        )
    
    def get_confluence_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de confluence"""
        try:
            if not self.confluence_history:
                return {'total_signals': 0, 'avg_score': 0.0}
            
            total_signals = len(self.confluence_history)
            avg_score = sum(r.result.final_score for r in self.confluence_history) / total_signals
            valid_signals = sum(1 for r in self.confluence_history if r.result.is_valid)
            
            return {
                'total_signals': total_signals,
                'valid_signals': valid_signals,
                'avg_score': avg_score,
                'validation_rate': valid_signals / total_signals if total_signals > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul stats confluence: {e}")
            return {'total_signals': 0, 'avg_score': 0.0}
    
    def reset_confluence_history(self) -> None:
        """Reset l'historique de confluence"""
        self.confluence_history.clear()
        logger.info("🔄 Historique confluence reseté")

def create_confluence_integrator(config=None) -> ConfluenceIntegrator:
    """Factory pour créer un ConfluenceIntegrator"""
    return ConfluenceIntegrator(config)
