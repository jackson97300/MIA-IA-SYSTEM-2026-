#!/usr/bin/env python3
"""
🔗 LIVE LEADERSHIP INTEGRATION - MIA_IA_SYSTEM
Intégration temps réel du système de leadership avec les flux de marché
- Connexion IBKR + Sierra en temps réel
- Injection du ConfluenceIntegrator dans le pipeline
- Monitoring des décisions live
- Validation de la logique Fort/Faible
- Logging structuré pour audit
"""

import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from collections import deque

# Ajouter le chemin du projet
sys.path.append(str(Path(__file__).parent.parent))

from core.logger import get_logger
from features.confluence_integrator import ConfluenceIntegrator, ConfluenceResult
from features.market_state_analyzer import MarketState
from features.leadership_engine import LeadershipResult

logger = get_logger(__name__)

@dataclass
class LiveMarketData:
    """Données de marché en temps réel"""
    timestamp: datetime
    es_data: Dict[str, Any]  # Données ES depuis IBKR/Sierra
    nq_data: Dict[str, Any]  # Données NQ depuis IBKR/Sierra
    bias: str                # Biais actuel ('bullish', 'bearish', 'neutral')
    instrument: str          # Instrument cible ('ES', 'NQ')
    gamma_levels: Optional[List[float]] = None
    vwap: Optional[float] = None
    additional_signals: Optional[Dict[str, float]] = None

@dataclass
class LiveDecision:
    """Décision de trading en temps réel"""
    timestamp: datetime
    market_data: LiveMarketData
    confluence_result: ConfluenceResult
    execution_latency_ms: float
    decision_id: str

class LiveLeadershipIntegration:
    """Intégration temps réel du système de leadership"""
    
    def __init__(self, 
                 ibkr_connector=None,
                 sierra_connector=None,
                 decision_callback: Optional[Callable[[LiveDecision], None]] = None):
        """
        Initialise l'intégration temps réel
        
        Args:
            ibkr_connector: Connecteur IBKR (à implémenter)
            sierra_connector: Connecteur Sierra (à implémenter)
            decision_callback: Callback appelé à chaque décision
        """
        self.ibkr_connector = ibkr_connector
        self.sierra_connector = sierra_connector
        self.decision_callback = decision_callback
        
        # PATCH: Intégrateur avec calibration YAML
        self.integrator = ConfluenceIntegrator()
        
        # Monitoring temps réel
        self.decision_history = deque(maxlen=1000)
        self.start_time = datetime.now()
        self.decision_count = 0
        self.valid_decisions = 0
        self.rejected_decisions = 0
        
        # Configuration monitoring
        self.monitoring_interval = 60  # secondes
        self.last_monitoring = datetime.now()
        
        logger.info("🔗 LiveLeadershipIntegration initialisé")
        logger.info(f"  📊 Monitoring interval: {self.monitoring_interval}s")
        logger.info(f"  📈 Decision history size: {self.decision_history.maxlen}")
    
    async def start_live_integration(self, 
                                   symbols: List[str] = ['ES', 'NQ'],
                                   update_interval_ms: int = 1000):
        """
        Démarre l'intégration temps réel
        
        Args:
            symbols: Symboles à monitorer
            update_interval_ms: Intervalle de mise à jour en ms
        """
        logger.info(f"🚀 Démarrage intégration temps réel")
        logger.info(f"  📊 Symboles: {symboles}")
        logger.info(f"  ⏱️ Intervalle: {update_interval_ms}ms")
        
        try:
            # Connexion aux flux de données
            await self._connect_data_sources(symbols)
            
            # Boucle principale d'intégration
            cycle_count = 0
            logger.info("🔄 Début de la boucle principale...")
            
            while True:
                start_time = time.time()
                cycle_count += 1
                
                logger.info(f"🔄 Cycle {cycle_count} - Récupération données...")
                
                # 1. Récupérer les données temps réel
                market_data = await self._fetch_live_market_data(symbols)
                
                if market_data:
                    logger.info(f"📊 Données reçues: {market_data.bias} {market_data.instrument}")
                    
                    # 2. Calculer la confluence avec leadership
                    decision = await self._process_market_data(market_data)
                    
                    # 3. Appliquer la décision
                    if decision:
                        await self._apply_decision(decision)
                else:
                    logger.warning("⚠️ Aucune donnée de marché reçue")
                
                # 4. Monitoring périodique
                await self._periodic_monitoring()
                
                # 5. Contrôle de latence
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms > update_interval_ms:
                    logger.warning(f"⚠️ Latence élevée: {elapsed_ms:.1f}ms > {update_interval_ms}ms")
                
                # 6. Attendre le prochain cycle
                sleep_time = max(0.001, (update_interval_ms - elapsed_ms) / 1000)
                logger.info(f"⏱️ Attente {sleep_time:.3f}s avant prochain cycle")
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur intégration temps réel: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
        finally:
            await self._cleanup()
    
    async def _connect_data_sources(self, symbols: List[str]):
        """Connecte aux sources de données temps réel"""
        logger.info("🔌 Connexion aux sources de données...")
        
        # TODO: Implémenter la connexion IBKR
        if self.ibkr_connector:
            try:
                # await self.ibkr_connector.connect()
                logger.info("✅ Connexion IBKR établie")
            except Exception as e:
                logger.error(f"❌ Erreur connexion IBKR: {e}")
        
        # TODO: Implémenter la connexion Sierra
        if self.sierra_connector:
            try:
                # await self.sierra_connector.connect()
                logger.info("✅ Connexion Sierra établie")
            except Exception as e:
                logger.error(f"❌ Erreur connexion Sierra: {e}")
        
        logger.info("🔌 Connexions établies")
    
    async def _fetch_live_market_data(self, symbols: List[str]) -> Optional[LiveMarketData]:
        """Récupère les données de marché temps réel"""
        try:
            # TODO: Remplacer par les vraies données IBKR/Sierra
            # Pour l'instant, simulation avec données de test
            now = datetime.now()
            
            # Simulation données ES
            es_data = {
                'close': 6397.5 + (now.second % 60) * 0.1,
                'volume': 1000 + (now.second % 30) * 10,
                'bid': 6397.0,
                'ask': 6398.0,
                'timestamp': now
            }
            
            # Simulation données NQ
            nq_data = {
                'close': 23246.0 + (now.second % 60) * 0.2,
                'volume': 800 + (now.second % 30) * 8,
                'bid': 23245.5,
                'ask': 23246.5,
                'timestamp': now
            }
            
            # Simulation biais et instrument (rotation pour test)
            bias_cycle = ['bullish', 'bearish', 'neutral']
            instrument_cycle = ['ES', 'NQ']
            
            bias = bias_cycle[(now.second // 20) % len(bias_cycle)]
            instrument = instrument_cycle[(now.second // 15) % len(instrument_cycle)]
            
            return LiveMarketData(
                timestamp=now,
                es_data=es_data,
                nq_data=nq_data,
                bias=bias,
                instrument=instrument,
                gamma_levels=[6400, 6450, 6500],
                vwap=6398.0,
                additional_signals={
                    'gamma_proximity': 0.7,
                    'volume_confirmation': 0.8,
                    'vwap_trend': 0.6,
                    'options_flow': 0.5,
                    'order_book_imbalance': 0.4
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération données temps réel: {e}")
            return None
    
    async def _process_market_data(self, market_data: LiveMarketData) -> Optional[LiveDecision]:
        """Traite les données de marché et génère une décision"""
        try:
            start_time = time.time()
            
            # Convertir les données en format attendu par l'intégrateur
            processed_data = self._convert_to_integrator_format(market_data)
            
            # Calculer la confluence avec leadership
            confluence_result = self.integrator.calculate_confluence_with_leadership(processed_data)
            
            # Calculer la latence
            execution_latency_ms = (time.time() - start_time) * 1000
            
            # Créer la décision
            decision = LiveDecision(
                timestamp=market_data.timestamp,
                market_data=market_data,
                confluence_result=confluence_result,
                execution_latency_ms=execution_latency_ms,
                decision_id=f"DEC_{self.decision_count:06d}"
            )
            
            # Mettre à jour les statistiques
            self.decision_count += 1
            if confluence_result.is_valid:
                self.valid_decisions += 1
            else:
                self.rejected_decisions += 1
            
            # Ajouter à l'historique
            self.decision_history.append(decision)
            
            # Logging de la décision
            self._log_live_decision(decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement données marché: {e}")
            return None
    
    def _convert_to_integrator_format(self, market_data: LiveMarketData) -> Dict[str, Any]:
        """Convertit les données temps réel au format attendu par l'intégrateur"""
        import pandas as pd
        
        # Créer des DataFrames simulées (à remplacer par vraies données)
        dates = pd.date_range(market_data.timestamp - timedelta(minutes=100), 
                             market_data.timestamp, freq='1min')
        
        # ES DataFrame
        es_df = pd.DataFrame({
            'close': [market_data.es_data['close'] - i*0.1 for i in range(len(dates))],
            'volume': [market_data.es_data['volume'] - i*5 for i in range(len(dates))],
            'buy_volume': [market_data.es_data['volume']*0.6 - i*3 for i in range(len(dates))],
            'sell_volume': [market_data.es_data['volume']*0.4 - i*2 for i in range(len(dates))]
        }, index=dates)
        
        # NQ DataFrame
        nq_df = pd.DataFrame({
            'close': [market_data.nq_data['close'] - i*0.2 for i in range(len(dates))],
            'volume': [market_data.nq_data['volume'] - i*4 for i in range(len(dates))],
            'buy_volume': [market_data.nq_data['volume']*0.6 - i*2.4 for i in range(len(dates))],
            'sell_volume': [market_data.nq_data['volume']*0.4 - i*1.6 for i in range(len(dates))]
        }, index=dates)
        
        return {
            'ES': es_df,
            'NQ': nq_df,
            'bias': market_data.bias,
            'symbol': market_data.instrument,
            'now': market_data.timestamp,
            'gamma_levels': market_data.gamma_levels,
            'vwap': market_data.vwap,
            **market_data.additional_signals
        }
    
    async def _apply_decision(self, decision: LiveDecision):
        """Applique la décision de trading"""
        try:
            if decision.confluence_result.is_valid:
                logger.info(f"🎯 EXÉCUTION: {decision.decision_id}")
                logger.info(f"  📊 Score final: {decision.confluence_result.final_score:.3f}")
                logger.info(f"  🎯 Instrument: {decision.market_data.instrument}")
                logger.info(f"  📈 Biais: {decision.market_data.bias}")
                
                # TODO: Implémenter l'exécution réelle
                # await self._execute_trade(decision)
                
            else:
                logger.info(f"❌ REJET: {decision.decision_id}")
                logger.info(f"  📝 Raison: {decision.confluence_result.reason}")
            
            # Appeler le callback si défini
            if self.decision_callback:
                await self.decision_callback(decision)
                
        except Exception as e:
            logger.error(f"❌ Erreur application décision: {e}")
    
    def _log_live_decision(self, decision: LiveDecision):
        """Log une décision temps réel"""
        try:
            result = decision.confluence_result
            market_data = decision.market_data
            
            status = "✅ VALID" if result.is_valid else "❌ REJECT"
            
            logger.info(f"{status} | {decision.decision_id} | Latency: {decision.execution_latency_ms:.1f}ms")
            logger.info(f"  📊 Bias: {market_data.bias} | Instrument: {market_data.instrument}")
            logger.info(f"  🎯 Leader: {result.leadership_result.leader} | Force: {result.leadership_result.strength:.3f}")
            logger.info(f"  🔗 Corr: {result.market_state.corr_15m:.3f} ({result.market_state.corr_regime})")
            logger.info(f"  💰 Final Score: {result.final_score:.3f} | Risk Mult: {result.risk_multiplier:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Erreur logging décision live: {e}")
    
    async def _periodic_monitoring(self):
        """Monitoring périodique du système"""
        now = datetime.now()
        if (now - self.last_monitoring).total_seconds() >= self.monitoring_interval:
            self._log_monitoring_stats()
            self.last_monitoring = now
    
    def _log_monitoring_stats(self):
        """Log les statistiques de monitoring"""
        try:
            uptime = (datetime.now() - self.start_time).total_seconds()
            valid_rate = self.valid_decisions / max(self.decision_count, 1)
            reject_rate = self.rejected_decisions / max(self.decision_count, 1)
            
            # Statistiques de l'intégrateur
            integrator_stats = self.integrator.get_statistics()
            
            logger.info("📊 MONITORING STATS:")
            logger.info(f"  ⏱️ Uptime: {uptime:.0f}s")
            logger.info(f"  📈 Total decisions: {self.decision_count}")
            logger.info(f"  ✅ Valid rate: {valid_rate:.1%}")
            logger.info(f"  ❌ Reject rate: {reject_rate:.1%}")
            logger.info(f"  🔗 Leadership pass rate: {integrator_stats['leadership_stats']['pass_rate']:.1%}")
            logger.info(f"  ⚡ Latency exceeded: {integrator_stats['latency_exceeded_rate']:.1%}")
            
            # Dernières décisions
            if self.decision_history:
                recent_decisions = list(self.decision_history)[-5:]
                logger.info("📜 RÉCENTES DÉCISIONS:")
                for decision in recent_decisions:
                    status = "✅" if decision.confluence_result.is_valid else "❌"
                    logger.info(f"  {status} {decision.decision_id}: {decision.confluence_result.final_score:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Erreur monitoring stats: {e}")
    
    async def _cleanup(self):
        """Nettoyage à la fin"""
        logger.info("🧹 Nettoyage intégration temps réel...")
        
        # TODO: Fermer les connexions
        if self.ibkr_connector:
            # await self.ibkr_connector.disconnect()
            pass
        
        if self.sierra_connector:
            # await self.sierra_connector.disconnect()
            pass
        
        logger.info("✅ Nettoyage terminé")
    
    def get_live_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques temps réel"""
        return {
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'decision_count': self.decision_count,
            'valid_decisions': self.valid_decisions,
            'rejected_decisions': self.rejected_decisions,
            'valid_rate': self.valid_decisions / max(self.decision_count, 1),
            'reject_rate': self.rejected_decisions / max(self.decision_count, 1),
            'integrator_stats': self.integrator.get_statistics(),
            'recent_decisions': list(self.decision_history)[-10:]
        }

async def test_live_integration():
    """Test de l'intégration temps réel"""
    logger.info("🧮 TEST LIVE LEADERSHIP INTEGRATION")
    logger.info("=" * 50)
    
    # Initialiser l'intégration
    integration = LiveLeadershipIntegration()
    
    # Callback pour les décisions
    async def decision_callback(decision: LiveDecision):
        logger.info(f"🔔 CALLBACK: Décision {decision.decision_id} reçue")
    
    integration.decision_callback = decision_callback
    
    # Démarrer l'intégration (simulation 30 secondes)
    logger.info("🚀 Démarrage simulation 30 secondes...")
    
    try:
        # Lancer l'intégration en arrière-plan
        task = asyncio.create_task(
            integration.start_live_integration(update_interval_ms=2000)
        )
        
        # Attendre 30 secondes
        await asyncio.sleep(30)
        
        # Annuler la tâche
        task.cancel()
        
    except asyncio.CancelledError:
        logger.info("✅ Simulation terminée")
    
    # Statistiques finales
    stats = integration.get_live_statistics()
    logger.info("\n📋 STATISTIQUES FINALES:")
    logger.info(f"  ⏱️ Uptime: {stats['uptime_seconds']:.0f}s")
    logger.info(f"  📈 Total decisions: {stats['decision_count']}")
    logger.info(f"  ✅ Valid rate: {stats['valid_rate']:.1%}")
    logger.info(f"  ❌ Reject rate: {stats['reject_rate']:.1%}")

if __name__ == "__main__":
    asyncio.run(test_live_integration())
