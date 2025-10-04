#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH D'INTÉGRATION - Cluster Alerts dans le Bot Existant
Ajoute la logique cluster sans supprimer MIA Bullish
"""

# === PATCH 1: Ajouter dans launch_24_7_menthorq_final.py ===

def _process_cluster_alerts(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Traite les alertes cluster et retourne des signaux enrichis
    NOUVELLE MÉTHODE - À AJOUTER DANS LA CLASSE MIA_IA_SYSTEM
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
        "raw_alerts": alerts
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

# === PATCH 2: Modifier la méthode analyze_market ===

def analyze_market_with_clusters(self, market_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyse complète du marché avec clusters + MIA Bullish
    VERSION MODIFIÉE DE analyze_market
    """
    start_time = time.perf_counter()
    
    try:
        # Reset métriques quotidiennes si nécessaire
        self._reset_daily_metrics()
        
        # Vérifier limite quotidienne
        if self.daily_signal_count >= self.config.get('max_signals_per_day', 12):
            logger.debug("📊 Limite quotidienne de signaux atteinte")
            return {"signal": None, "reason": "daily_limit_reached"}
        
        # === RÉCUPÉRATION DES DONNÉES SIERRA CHART ===
        if market_data is None and self.sierra_connector:
            try:
                market_data = await self._get_sierra_market_data()
                if not market_data:
                    logger.debug("📊 Aucune donnée Sierra Chart disponible")
                    return {"signal": None, "reason": "no_sierra_data"}
            except Exception as e:
                logger.warning(f"⚠️ Erreur récupération données Sierra Chart: {e}")
                market_data = self._get_fallback_market_data()
        elif market_data is None:
            market_data = self._get_fallback_market_data()
        
        # === NOUVEAU: TRAITEMENT DES ALERTES CLUSTER ===
        cluster_result = self._process_cluster_alerts(market_data)
        
        # === MIA BULLISH EXISTANT (PRÉSERVÉ) ===
        bullish_score = None
        if self.bullish_scorer and 'sierra_events' in market_data:
            # Traiter les événements Sierra Chart avec le BullishScorer
            for event in market_data.get('sierra_events', []):
                try:
                    bullish_result = self.bullish_scorer.ingest(event)
                    if bullish_result:
                        bullish_score = bullish_result
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Erreur BullishScorer: {e}")
        
        # Créer contexte de trading enrichi
        trading_context = self._create_trading_context(market_data)
        
        # Enrichir le contexte avec les résultats cluster
        trading_context.cluster_analysis = cluster_result
        trading_context.bullish_analysis = bullish_score
        
        # Analyse avec le strategy selector
        result = self.strategy_selector.analyze_and_select(trading_context)
        
        # === NOUVEAU: COMBINAISON DES SIGNAUX ===
        final_signal = self._combine_signals(cluster_result, bullish_score, result)
        
        # Calcul temps de traitement
        processing_time = (time.perf_counter() - start_time) * 1000
        
        # Vérifier timeout
        if processing_time > self.config.get('processing_timeout_ms', 100):
            logger.warning(f"⚠️ Timeout processing: {processing_time:.1f}ms")
        
        # Mettre à jour métriques
        self._update_metrics(result, processing_time)
        
        # === NOUVEAU: LOGS ENRICHIS ===
        if final_signal and final_signal.get("type") != "no_signal":
            logger.info(f"🎯 Signal final: {final_signal['type']} - Confiance: {final_signal.get('confidence', 0):.2f}")
            if cluster_result.get("cluster_signals"):
                logger.info(f"   📊 Cluster: {cluster_result['cluster_signals']['strategy']}")
            if bullish_score:
                logger.info(f"   🐂 Bullish: {bullish_score.get('confidence', 0):.2f}")
        
        return {
            "signal": final_signal,
            "processing_time_ms": processing_time,
            "cluster_analysis": cluster_result,
            "bullish_analysis": bullish_score,
            "strategy_result": result,
            "timestamp": pd.Timestamp.now()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse marché: {e}")
        return {"signal": None, "error": str(e)}

def _combine_signals(self, cluster_result: Dict[str, Any], 
                    bullish_result: Dict[str, Any], 
                    strategy_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine les signaux cluster avec MIA Bullish et les stratégies
    NOUVELLE MÉTHODE
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
            "bullish_support": bullish_result is not None,
            "strategy_support": strategy_result is not None
        }
    
    elif confluence_signal and confluence_signal.get("priority") == "HIGH":
        # Signal confluence prioritaire
        return {
            "type": "confluence_high_priority",
            "strategy": confluence_signal.get("strategy"),
            "confidence": cluster_result.get("enhanced_confidence", 0.75),
            "source": "confluence_alerts",
            "details": confluence_signal,
            "bullish_support": bullish_result is not None,
            "strategy_support": strategy_result is not None
        }
    
    elif strategy_result and strategy_result.get("signal"):
        # Stratégies existantes (logique préservée)
        return {
            "type": "strategy_signal",
            "strategy": strategy_result.get("signal", {}).get("strategy", "unknown"),
            "confidence": strategy_result.get("signal", {}).get("confidence", 0.7),
            "source": "strategy_selector",
            "details": strategy_result.get("signal"),
            "cluster_support": cluster_signal is not None,
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

# === PATCH 3: Modifier la méthode _create_trading_context ===

def _create_trading_context_with_clusters(self, market_data: Dict[str, Any]) -> TradingContext:
    """
    Crée le contexte de trading enrichi avec les alertes cluster
    VERSION MODIFIÉE DE _create_trading_context
    """
    # Créer le contexte de base (logique existante préservée)
    trading_context = TradingContext(
        symbol=market_data.get("symbol", "ES"),
        price=market_data.get("price", 4500.0),
        timestamp=market_data.get("timestamp", pd.Timestamp.now()),
        market_data=market_data
    )
    
    # === NOUVEAU: Enrichir avec les alertes cluster ===
    alerts = market_data.get("menthorq", {}).get("alerts", {})
    if alerts:
        trading_context.cluster_alerts = alerts
        trading_context.has_cluster_signals = True
        
        # Ajouter les signaux cluster au contexte
        summary = alerts.get("summary", {})
        signals = summary.get("signals", {})
        trading_context.cluster_signals = signals
        
        # Ajouter la confluence
        if alerts.get("confluence"):
            trading_context.confluence_data = alerts["confluence"]
            trading_context.confluence_strength = alerts.get("confluence_strength", 0.0)
    
    return trading_context

# === INSTRUCTIONS D'APPLICATION ===

"""
INSTRUCTIONS POUR APPLIQUER LE PATCH:

1. Ouvrir launch_24_7_menthorq_final.py

2. Ajouter les 4 nouvelles méthodes dans la classe MIA_IA_SYSTEM:
   - _process_cluster_alerts()
   - _determine_cluster_strategy()
   - _calculate_enhanced_confidence()
   - _combine_signals()

3. Remplacer la méthode analyze_market() par analyze_market_with_clusters()

4. Remplacer la méthode _create_trading_context() par _create_trading_context_with_clusters()

5. Tester avec des données réelles

AVANTAGES:
✅ MIA Bullish préservé et fonctionnel
✅ Nouvelles alertes cluster ajoutées
✅ Logique de combinaison intelligente
✅ Logs enrichis pour le debugging
✅ Performance optimisée
"""


























