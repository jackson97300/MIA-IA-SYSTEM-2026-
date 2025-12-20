#!/usr/bin/env python3
"""
🚀 LIVE LEADERSHIP DEMO - MIA_IA_SYSTEM
Démonstration temps réel du système de leadership avec corrections
- Bootstrap historique pour warm-up
- Configuration test adaptée (30s)
- Agrégation 1m correcte
- Compteurs PASS & REJECT
- Restauration calibration production
"""

import sys
import time
import asyncio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Ajouter le chemin du projet
sys.path.append(str(Path(__file__).parent.parent))

from core.logger import get_logger
from features.confluence_integrator import ConfluenceIntegrator, ConfluenceResult
from features.market_state_analyzer import MarketStateAnalyzer
from config.leadership_config import LeadershipConfigManager

logger = get_logger(__name__)

@dataclass
class DemoStats:
    """Statistiques de la démonstration"""
    total_decisions: int = 0
    valid_decisions: int = 0
    rejected_decisions: int = 0
    start_time: datetime = None
    end_time: datetime = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    @property
    def valid_rate(self) -> float:
        return self.valid_decisions / max(self.total_decisions, 1)
    
    @property
    def reject_rate(self) -> float:
        return self.rejected_decisions / max(self.total_decisions, 1)
    
    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

class LiveLeadershipDemo:
    """Démonstration temps réel du système de leadership"""
    
    def __init__(self):
        self.config_manager = LeadershipConfigManager()
        self.original_calibration = None
        self.demo_stats = DemoStats()
        
        logger.info("🚀 LiveLeadershipDemo initialisé")
    
    def create_test_calibration(self) -> Dict[str, Any]:
        """Crée une calibration de test optimisée pour 25-30% valid rate"""
        return {
            'persistence_bars': 2,            # confirmation en 2 minutes (stabilité)
            'leader_strength_min': 0.30,      # permissif pour tests
            'corr_min': 0.55,                 # PATCH: baissé de 0.60 à 0.55
            'corr_weak_threshold': 0.65,      # PATCH: ajouté
            'corr_tight_threshold': 0.85,     # PATCH: ajouté
            'window_1m': 3,                   # fenêtres courtes
            'window_5m': 5,
            'window_15m': 7,
            'bars_timeframe_minutes': 1,      # 1 minute
            'risk_multiplier_tight_corr': 0.8, # PATCH: remonté de 0.7 à 0.8
            'risk_multiplier_weak_corr': 0.9,  # PATCH: remonté de 0.8 à 0.9
            'allow_half_size_if_neutral': True, # activer demi-taille conditionnelle
            'max_latency_ms': 50
        }
    
    def create_bootstrap_history(self, minutes: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Crée un historique de bootstrap avec données corrélées"""
        logger.info(f"📊 Création historique bootstrap ({minutes} minutes)...")
        
        # Dates pour l'historique
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes)
        dates = pd.date_range(start_time, end_time, freq='1min')
        
        # Base prices
        es_base = 6397.5
        nq_base = 23246.0
        
        # Créer des données corrélées (ES et NQ bougent ensemble)
        np.random.seed(42)  # Pour reproductibilité
        
        # Trend commun
        trend = np.cumsum(np.random.normal(0, 0.1, len(dates)))
        
        # ES data
        es_prices = es_base + trend * 0.5 + np.random.normal(0, 0.05, len(dates))
        es_volumes = 1000 + np.random.normal(0, 100, len(dates))
        
        # NQ data (corrélé à ES)
        nq_prices = nq_base + trend * 0.2 + np.random.normal(0, 0.1, len(dates))
        nq_volumes = 800 + np.random.normal(0, 80, len(dates))
        
        # Créer les DataFrames
        es_df = pd.DataFrame({
            'close': es_prices,
            'volume': es_volumes,
            'buy_volume': es_volumes * 0.6,
            'sell_volume': es_volumes * 0.4
        }, index=dates)
        
        nq_df = pd.DataFrame({
            'close': nq_prices,
            'volume': nq_volumes,
            'buy_volume': nq_volumes * 0.6,
            'sell_volume': nq_volumes * 0.4
        }, index=dates)
        
        logger.info(f"✅ Historique créé: ES ({len(es_df)} barres), NQ ({len(nq_df)} barres)")
        logger.info(f"  📈 ES range: {es_df['close'].min():.1f} - {es_df['close'].max():.1f}")
        logger.info(f"  📈 NQ range: {nq_df['close'].min():.1f} - {nq_df['close'].max():.1f}")
        
        return es_df, nq_df
    
    def bootstrap_integrator(self, integrator: ConfluenceIntegrator, 
                           es_history: pd.DataFrame, nq_history: pd.DataFrame):
        """Bootstrap l'intégrateur avec l'historique"""
        logger.info("🔥 Bootstrap de l'intégrateur...")
        
        # Récupérer la calibration actuelle
        cal = self.config_manager.get_calibration()
        
        # Simuler des appels pour "chauffer" le moteur
        for i in range(max(5, len(es_history) // 2)):  # Au moins 5 appels
            idx = -(i + 1)  # Commencer par les plus récentes
            if idx >= -len(es_history):
                now = es_history.index[idx]
                
                # Créer des données de marché pour cet instant
                market_data = {
                    'ES': es_history.iloc[:idx+1] if idx < -1 else es_history,
                    'NQ': nq_history.iloc[:idx+1] if idx < -1 else nq_history,
                    'bias': 'bullish',
                    'symbol': 'ES',
                    'now': now,
                    'gamma_levels': [6600, 6700, 6800],  # Éloignés
                    'gamma_proximity': 0.7,
                    'volume_confirmation': 0.8,
                    'vwap_trend': 0.6,
                    'options_flow': 0.5,
                    'order_book_imbalance': 0.4,
                    'demo_mode': True
                }
                
                # Appeler l'intégrateur (sans compter dans les stats)
                try:
                    result = integrator.calculate_confluence_with_leadership(market_data)
                    logger.debug(f"  🔄 Bootstrap {i+1}: {result.is_valid} (score: {result.final_score:.3f})")
                except Exception as e:
                    logger.warning(f"  ⚠️ Erreur bootstrap {i+1}: {e}")
        
        logger.info("✅ Bootstrap terminé")
    
    async def run_demo(self, duration_seconds: int = 60):
        """Exécute la démonstration temps réel"""
        logger.info(f"🚀 DÉMARRAGE DÉMO LIVE ({duration_seconds}s)")
        logger.info("=" * 60)
        
        try:
            # 1. Sauvegarder la calibration originale
            self.original_calibration = self.config_manager.get_calibration()
            logger.info("💾 Calibration originale sauvegardée")
            
            # 2. Appliquer la calibration de test
            test_cal = self.create_test_calibration()
            self.config_manager.update_calibration(test_cal)
            logger.info("⚙️ Calibration de test appliquée")
            logger.info(f"  📊 Persistence: {test_cal['persistence_bars']} barres")
            logger.info(f"  🎯 Leader strength min: {test_cal['leader_strength_min']}")
            logger.info(f"  🔗 Corr min: {test_cal['corr_min']}")
            logger.info(f"  ⏱️ Fenêtres: {test_cal['window_1m']}/{test_cal['window_5m']}/{test_cal['window_15m']}")
            
            # 3. Créer l'intégrateur avec la calibration injectée
            cal = self.config_manager.get_calibration()  # <<< re-fetch après reload
            self.integrator = ConfluenceIntegrator(calibration=cal)  # <<< injecte et stocke
            logger.info(f"🔗 Intégrateur initialisé avec calibration test - corr_min: {cal.corr_min}")
            
            # 4. Créer et injecter l'historique de bootstrap
            es_history, nq_history = self.create_bootstrap_history(minutes=10)
            self.bootstrap_integrator(self.integrator, es_history, nq_history)
            
            # 5. Boucle principale de démonstration
            logger.info("🔄 Début de la boucle de démonstration...")
            
            current_time = datetime.now()
            step_count = 0
            
            while (datetime.now() - current_time).total_seconds() < duration_seconds:
                step_count += 1
                step_start = time.time()
                
                # Simuler de nouvelles données (1 minute de plus)
                new_time = current_time + timedelta(minutes=step_count)
                
                # Créer de nouvelles barres (corrélées)
                # Choc commun (drive la corrélation)
                z = np.random.normal(0, 1)
                
                # Incréments corrélés
                es_inc = 0.10 * z + np.random.normal(0, 0.03)   # 0.10 = poids commun ES
                nq_inc = 0.06 * z + np.random.normal(0, 0.02)   # 0.06 = poids commun NQ
                
                es_new_price = es_history['close'].iloc[-1] + es_inc
                nq_new_price = nq_history['close'].iloc[-1] + nq_inc
                
                # Ajouter aux historiques
                es_new_row = pd.DataFrame({
                    'close': [es_new_price],
                    'volume': [1000 + np.random.normal(0, 50)],
                    'buy_volume': [600 + np.random.normal(0, 30)],
                    'sell_volume': [400 + np.random.normal(0, 20)]
                }, index=[new_time])
                
                nq_new_row = pd.DataFrame({
                    'close': [nq_new_price],
                    'volume': [800 + np.random.normal(0, 40)],
                    'buy_volume': [480 + np.random.normal(0, 24)],
                    'sell_volume': [320 + np.random.normal(0, 16)]
                }, index=[new_time])
                
                es_current = pd.concat([es_history, es_new_row])
                nq_current = pd.concat([nq_history, nq_new_row])
                
                # Rotation des biais et instruments pour tester différents cas
                bias_cycle = ['bullish', 'bearish', 'neutral']
                instrument_cycle = ['ES', 'NQ']
                
                bias = bias_cycle[step_count % len(bias_cycle)]
                instrument = instrument_cycle[step_count % len(instrument_cycle)]
                
                # Créer les données de marché
                market_data = {
                    'ES': es_current,
                    'NQ': nq_current,
                    'bias': bias,
                    'symbol': instrument,
                    'now': new_time,
                    'gamma_levels': [6600, 6700, 6800],  # Éloignés du prix courant
                    'gamma_proximity': 0.7 + np.random.normal(0, 0.1),
                    'volume_confirmation': 0.8 + np.random.normal(0, 0.1),
                    'vwap_trend': 0.6 + np.random.normal(0, 0.1),
                    'options_flow': 0.5 + np.random.normal(0, 0.1),
                    'order_book_imbalance': 0.4 + np.random.normal(0, 0.1),
                    'demo_mode': True  # Flag pour éviter le gate dur en démo
                }
                
                # Calculer la confluence avec leadership
                result = self.integrator.calculate_confluence_with_leadership(market_data)
                
                # Mettre à jour les statistiques
                self.demo_stats.total_decisions += 1
                if result.is_valid:
                    self.demo_stats.valid_decisions += 1
                else:
                    self.demo_stats.rejected_decisions += 1
                
                # Logging de la décision
                status = "✅ VALID" if result.is_valid else "❌ REJECT"
                logger.info(f"{status} | Step {step_count} | {bias} {instrument}")
                logger.info(f"  🎯 Leader: {result.leadership_result.leader} | Force: {result.leadership_result.strength:.3f}")
                logger.info(f"  🔗 Corr: {result.market_state.corr_15m:.3f} ({result.market_state.corr_regime})")
                logger.info(f"  💰 Score: {result.final_score:.3f} | Risk: {result.risk_multiplier:.3f}")
                logger.info(f"  📝 Raison: {result.reason}")
                
                # Mettre à jour les historiques pour le prochain cycle
                es_history = es_current
                nq_history = nq_current
                
                # Contrôle de latence
                step_duration = (time.time() - step_start) * 1000
                if step_duration > 1000:  # Plus d'1 seconde
                    logger.warning(f"⚠️ Latence élevée: {step_duration:.1f}ms")
                
                # Attendre avant le prochain cycle (simulation temps réel)
                await asyncio.sleep(1.0)  # 1 seconde entre chaque "minute"
            
            # 6. Statistiques finales
            self.demo_stats.end_time = datetime.now()
            self._log_final_stats()
            
        except Exception as e:
            logger.error(f"❌ Erreur démonstration: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
        
        finally:
            # 7. Restaurer la calibration originale
            await self._restore_original_calibration()
    
    def _log_final_stats(self):
        """Log les statistiques finales"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 STATISTIQUES FINALES DE LA DÉMO")
        logger.info("=" * 60)
        
        duration = self.demo_stats.duration_seconds
        total = self.demo_stats.total_decisions
        valid = self.demo_stats.valid_decisions
        rejected = self.demo_stats.rejected_decisions
        
        logger.info(f"⏱️ Durée: {duration:.1f} secondes")
        logger.info(f"📈 Total décisions: {total}")
        logger.info(f"✅ Décisions validées: {valid} ({self.demo_stats.valid_rate:.1%})")
        logger.info(f"❌ Décisions rejetées: {rejected} ({self.demo_stats.reject_rate:.1%})")
        
        if total > 0:
            logger.info(f"⚡ Décisions/minute: {total / (duration / 60):.1f}")
        
        # Vérifier que nous avons eu des décisions
        if total == 0:
            logger.error("🚨 AUCUNE DÉCISION GÉNÉRÉE - Problème détecté!")
        elif valid == 0:
            logger.warning("⚠️ AUCUNE DÉCISION VALIDÉE - Vérifier la logique")
        else:
            logger.info("✅ DÉMO RÉUSSIE - Système fonctionnel")
            
        # PATCH: Monitoring par régime (si intégrateur disponible)
        if hasattr(self, 'integrator') and hasattr(self.integrator, 'render_regime_report'):
            logger.info("\n🧭 MONITORING PAR RÉGIME:")
            logger.info(self.integrator.render_regime_report())
    
    async def _restore_original_calibration(self):
        """Restaure la calibration originale"""
        if self.original_calibration:
            try:
                self.config_manager.update_calibration(self.original_calibration.__dict__)
                logger.info("🔄 Calibration originale restaurée")
            except Exception as e:
                logger.error(f"❌ Erreur restauration calibration: {e}")
        else:
            logger.warning("⚠️ Pas de calibration originale à restaurer")

async def main():
    """Fonction principale de la démonstration"""
    logger.info("🧮 DÉMONSTRATION LIVE LEADERSHIP INTEGRATION")
    logger.info("=" * 60)
    
    # Créer et exécuter la démonstration
    demo = LiveLeadershipDemo()
    
    # Démarrer la démonstration (60 secondes)
    await demo.run_demo(duration_seconds=60)
    
    logger.info("🎉 DÉMONSTRATION TERMINÉE")

if __name__ == "__main__":
    asyncio.run(main())
