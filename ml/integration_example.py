#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
EXEMPLE D'INTÉGRATION ML DUAL FILTER
═══════════════════════════════════════════════════════════════════════════════

Montre comment intégrer le filtre ML dans launch_optimized_ml_ready.py

Auteur : MIA_IA_SYSTEM
Date : 2 Novembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

from ml.ml_dual_filter import MLDualFilter


# ═══════════════════════════════════════════════════════════════════════════
# DANS MLOptimizedChartManager.__init__
# ═══════════════════════════════════════════════════════════════════════════

def init_ml_filter(self):
    """
    À ajouter dans __init__ de MLOptimizedChartManager
    """
    # Charger seuils calibrés (si disponibles)
    try:
        import json
        from pathlib import Path

        best_es_up = Path("ml/threshold_calibration/best_threshold_ES_UP.json")
        best_nq_down = Path("ml/threshold_calibration/best_threshold_NQ_DOWN.json")

        if best_es_up.exists() and best_nq_down.exists():
            with open(best_es_up, 'r') as f:
                es_up_data = json.load(f)
            with open(best_nq_down, 'r') as f:
                nq_down_data = json.load(f)

            thr_es_up = es_up_data['threshold']
            thr_nq_down = nq_down_data['threshold']

            logger.info(f"✅ Seuils calibrés chargés : ES/UP={thr_es_up:.3f}, NQ/DOWN={thr_nq_down:.3f}")
        else:
            # Seuils par défaut (à calibrer)
            thr_es_up = 0.64
            thr_nq_down = 0.60
            logger.warning(f"⚠️ Seuils par défaut : ES/UP={thr_es_up}, NQ/DOWN={thr_nq_down}")

    except Exception as e:
        logger.warning(f"⚠️ Erreur chargement seuils calibrés : {e}")
        thr_es_up = 0.64
        thr_nq_down = 0.60

    # Initialiser filtre
    self.ml_filter = MLDualFilter(
        model_path_es="ml/models_robust/lgbm_direction_15min_ROBUST_ES_ultra_ensemble_20251102_163801.pkl",
        model_path_nq="ml/models_robust/lgbm_direction_15min_ROBUST_NQ_ultra_ensemble_20251102_164124.pkl",
        thresholds={
            "ES": {"UP": thr_es_up, "DOWN": None},
            "NQ": {"UP": None, "DOWN": thr_nq_down}
        },
        modes={
            "ES": {"UP": "required", "DOWN": "advisory"},
            "NQ": {"UP": "advisory", "DOWN": "required"}
        },
        enabled=True  # Mettre False pour désactiver
    )

    logger.info("✅ ML Dual Filter initialisé")
    logger.info(f"   ES/LONG : required @ {thr_es_up:.3f}")
    logger.info(f"   NQ/SHORT : required @ {thr_nq_down:.3f}")
    logger.info(f"   Autres : advisory (shadow)")


# ═══════════════════════════════════════════════════════════════════════════
# DANS MLOptimizedChartManager._check_ml_filter
# ═══════════════════════════════════════════════════════════════════════════

def _check_ml_filter(self, sig):
    """
    Vérifie le filtre ML (APRÈS les autres garde-fous)

    À placer après :
    - _check_cooldown
    - _check_risk_limits
    - _check_max_positions
    - etc.

    Retourne:
        True si accepté, False si rejeté
    """
    if not hasattr(self, 'ml_filter') or not self.ml_filter.enabled:
        return True  # Pas de filtre ML ou désactivé

    try:
        # Mapper side
        side = "UP" if sig.side == TradeSide.LONG else "DOWN"

        # Validation
        decision = self.ml_filter.validate_signal(
            signal={
                "strategy": sig.name,
                "side": side,
                "symbol": self.symbol
            },
            ml_ready_snapshot=self.current_ml_ready_snapshot,
            log_json=True  # Logs JSON structurés
        )

        if not decision.accepted:
            logger.info(f"❌ ML Filter rejette {sig.name} ({side}) : {decision.reason}")
            logger.info(f"   Latence : {decision.latency_ms:.1f}ms")
            return False

        logger.info(f"✅ ML Filter accepte {sig.name} ({side}) : {decision.reason}")
        logger.info(f"   Confiance : {decision.prediction.confidence:.3f}")
        logger.info(f"   Latence : {decision.latency_ms:.1f}ms")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur ML Filter : {e}", exc_info=True)
        # Fail-safe : accepter en cas d'erreur
        return True


# ═══════════════════════════════════════════════════════════════════════════
# DANS MLOptimizedChartManager.on_signal (EXEMPLE COMPLET)
# ═══════════════════════════════════════════════════════════════════════════

def on_signal_with_ml_filter(self, sig):
    """
    Traitement signal avec filtre ML intégré
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 SIGNAL REÇU : {sig.name} {sig.side}")
    logger.info(f"{'='*70}")

    # 1. Vérifier que snapshot ML_READY est disponible
    if self.current_ml_ready_snapshot is None:
        logger.warning("⚠️ Pas de snapshot ML_READY → Attente")
        return

    # 2. Garde-fous de base
    if not self._check_cooldown(sig):
        logger.info("❌ Rejeté : cooldown")
        return

    if not self._check_risk_limits():
        logger.info("❌ Rejeté : risque")
        return

    if not self._check_max_positions():
        logger.info("❌ Rejeté : max positions")
        return

    # 3. FILTRE ML (NOUVEAU)
    if not self._check_ml_filter(sig):
        logger.info("❌ Rejeté : ML Filter")
        # Incrémenter compteur rejets ML
        self.stats['ml_filter_rejections'] = self.stats.get('ml_filter_rejections', 0) + 1
        return

    # 4. Signal accepté → Passer au Risk Manager
    logger.info(f"✅ Signal accepté : {sig.name} {sig.side}")
    self._execute_signal(sig)


# ═══════════════════════════════════════════════════════════════════════════
# STATS PÉRIODIQUES
# ═══════════════════════════════════════════════════════════════════════════

def print_ml_stats(self):
    """
    À appeler périodiquement (tous les X signaux ou en fin de journée)
    """
    if hasattr(self, 'ml_filter'):
        self.ml_filter.print_stats()


# ═══════════════════════════════════════════════════════════════════════════
# EXEMPLE COMPLET : MINIMAL INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

class MLOptimizedChartManagerExample:
    """
    Exemple minimal d'intégration
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

        # ... autres initialisations ...

        # Initialiser ML Filter
        self.ml_filter = MLDualFilter(
            model_path_es="ml/models_robust/lgbm_direction_15min_ROBUST_ES_ultra_ensemble_20251102_163801.pkl",
            model_path_nq="ml/models_robust/lgbm_direction_15min_ROBUST_NQ_ultra_ensemble_20251102_164124.pkl",
            thresholds={
                "ES": {"UP": 0.64, "DOWN": None},
                "NQ": {"UP": None, "DOWN": 0.60}
            },
            modes={
                "ES": {"UP": "required", "DOWN": "advisory"},
                "NQ": {"UP": "advisory", "DOWN": "required"}
            },
            enabled=True
        )

    def on_signal(self, sig):
        """Traitement signal"""

        # Garde-fous existants
        # ...

        # ML Filter
        decision = self.ml_filter.validate_signal(
            signal={
                "strategy": sig.name,
                "side": "UP" if sig.side == TradeSide.LONG else "DOWN",
                "symbol": self.symbol
            },
            ml_ready_snapshot=self.current_ml_ready_snapshot
        )

        if not decision.accepted:
            logger.info(f"❌ ML rejeté : {decision.reason}")
            return

        # Exécuter
        logger.info(f"✅ ML accepté : {decision.reason}")
        self._execute_signal(sig)


# ═══════════════════════════════════════════════════════════════════════════
# NOTES D'IMPLÉMENTATION
# ═══════════════════════════════════════════════════════════════════════════

"""
POINTS IMPORTANTS :

1. Ordre des garde-fous :
   - Cooldown
   - Risk limits
   - Max positions
   - ML Filter (DERNIER)

   → ML Filter s'exécute seulement si les autres passent

2. Fail-safe :
   - En cas d'erreur ML, accepter le signal
   - Ne jamais bloquer à cause d'un bug du filtre

3. Latence :
   - Viser < 10ms par validation
   - Si > 50ms → investiguer

4. Logs JSON :
   - Parser avec jq ou Python
   - Agréger quotidiennement
   - KPIs : accept_rate, win_rate, PF, latency_p95

5. Shadow mode :
   - Commencer avec tous en "advisory"
   - Collecter métriques 1-2 jours
   - Activer progressivement si PF > 1.3

6. Monitoring :
   - Logger ml_filter.print_stats() toutes les heures
   - Alerter si accept_rate < 50% ou PF < 1.2
"""

