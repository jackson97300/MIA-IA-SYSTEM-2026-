#!/usr/bin/env python3
"""
ELITE UNIFIER ES - Unifier spécialisé pour Chart 3 (ES, YM, GC)
==============================================================

Unifier robuste pour la famille ES :
- ES → Chart 3
- YM → Chart 3  
- GC → Chart 3

Fonctionnalités identiques à l'Elite Unifier :
- MenthorQ Elite
- Battle Navale Elite
- OrderFlow Advanced
- DOM Health Analyzer
- QC robuste + gates + messages

Version: 1.0.0
Date: Janvier 2025
"""

import sys
import os
import json
import pathlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports des composants Elite
try:
    from core.menthorq_elite import MenthorQElite, MenthorQEliteResult
    from core.battle_navale_elite import BattleNavaleElite, BattleNavaleEliteResult
    from features.kernel_smooth import proximity_kernel, LAMBDA_CONFIG, TICK_SIZE_CONFIG
    from features.orderflow_advanced import OrderFlowAdvanced
    from features.dom_health_analyzer import DOMHealthAnalyzer
    ELITE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Modules Elite non disponibles: {e}")
    ELITE_MODULES_AVAILABLE = False

# Imports des composants robustes
from unifier.build_ctx import build_ctx
from unifier.legacy_adapter import LegacyAdapter
from core.decision_messenger import DecisionMessenger
from core.logger import get_logger

logger = get_logger(__name__)
_last_qc_warn_ts: float = 0.0

class EliteUnifierES:
    """
    Unifier Elite spécialisé pour Chart 3 (ES, YM, GC)
    
    Fonctionnalités :
    - Même code Elite que l'unifier principal
    - QC robuste pour Chart 3
    - Gates et messages identiques
    - Performance optimisée
    """
    
    _ready = False
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation de l'Elite Unifier ES"""
        if self._ready:
            return
            
        self.config = config or {}
        self.chart_number = 3
        self.supported_symbols = ["ES", "YM", "GC"]
        
        # ✅ Modules Elite
        self.menthorq_elite = MenthorQElite() if ELITE_MODULES_AVAILABLE else None
        self.battle_navale_elite = BattleNavaleElite() if ELITE_MODULES_AVAILABLE else None
        self.orderflow_advanced = OrderFlowAdvanced() if ELITE_MODULES_AVAILABLE else None
        self.dom_health_analyzer = DOMHealthAnalyzer() if ELITE_MODULES_AVAILABLE else None
        
        # ✅ Composants robustes
        self.legacy_adapter = LegacyAdapter()
        self.decision_messenger = DecisionMessenger({
            "verbose": self.config.get("verbose", True),
            "save_history": self.config.get("save_history", True),
            "cooldown_seconds": self.config.get("cooldown_seconds", 1)
        })
        
        # ✅ QC manquant (par défaut désactivé en prod)
        self.allow_missing_qc = (
            bool(int(os.getenv("MIA_ALLOW_MISSING_QC", "0")))
            if self.config.get("allow_missing_qc") is None 
            else self.config.get("allow_missing_qc", False)
        )
        
        print(f"🚀 Elite Unifier ES (Chart {self.chart_number}) initialisé")
        if ELITE_MODULES_AVAILABLE:
            print("✅ Tous les modules Elite disponibles")
        else:
            print("⚠️ Modules Elite non disponibles - Mode fallback")
            
        self._ready = True
    
    def unify_es(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unification robuste pour la famille ES (Chart 3)
        
        Args:
            snapshot: Snapshot de données
            
        Returns:
            Dict avec élite_synthesis + gating global
        """
        start_time = time.perf_counter()
        
        try:
            # ✅ Vérifier que c'est bien un symbole ES
            symbol = snapshot.get("sym", "ES")
            if not self._is_es_family(symbol):
                logger.warning(f"⚠️ Symbole {symbol} pas dans la famille ES, redirection recommandée")
            
            # 1) Vérifier le QC journalier Chart 3
            date_str = datetime.now().strftime("%Y%m%d")
            day_ok, qc_reason = self._check_daily_qc_chart3(date_str)
            
            # 2) Unification Elite
            elite_result = self._unify_with_elite_methods(snapshot)
            elite_synthesis = elite_result.get("elite_synthesis", {})

            # 2.b) Résumé enrichi (blind confluence + VP)
            try:
                menthorq_payload = self.legacy_adapter.to_menthorq_payload(snapshot)
            except Exception:
                menthorq_payload = {}
            blind_score = (
                (menthorq_payload.get("blind_spots", {}) or {}).get("confluence_score")
            )
            # Top 3 blinds les plus proches du prix
            top_blinds = None
            try:
                last_px = float(snapshot.get("last", 0.0) or 0.0)
                spots = list(menthorq_payload.get("blind_spots", {}).get("spots", []) or [])
                items = []
                for v in spots:
                    try:
                        val = float(v)
                    except Exception:
                        continue
                    if val <= 0:
                        continue
                    items.append({"px": val, "dist": round(abs(val - last_px), 6)})
                if items:
                    items.sort(key=lambda x: x["dist"])  # plus proches d'abord
                    top_blinds = {"top": items[:3], "count": len(items)}
            except Exception:
                top_blinds = None
            # VP compact
            vp_blk = None
            try:
                vp_src = (elite_result.get("micro", {}) or {}).get("vp", {})
                if any(vp_src.get(k) for k in ("vpoc", "val", "vah")):
                    vp_blk = {k: vp_src.get(k) for k in ("vpoc", "val", "vah")}
            except Exception:
                vp_blk = None
            
            # 3) Gating global
            elite_gates_ok = elite_synthesis.get("gates_status", {}).get("overall_gates_ok", False)
            is_signal = elite_synthesis.get("is_signal", False)
            
            # 4) Décision finale
            go_live = day_ok and elite_gates_ok and is_signal
            
            # 5) Construire le résultat robuste
            robust_result = {
                "timestamp": time.time(),
                "processing_time_ms": (time.perf_counter() - start_time) * 1000,
                "chart": self.chart_number,
                "symbol_family": "ES",
                # Fraîcheur des données
                "data_age_ms": self._compute_data_age_ms(snapshot),
                
                # Gating global
                "gating": {
                    "day_ok": day_ok,
                    "qc_reason": qc_reason,
                    "elite_gates_ok": elite_gates_ok,
                    "is_signal": is_signal,
                    "go_live": go_live
                },
                
                # Résultats Elite
                "elite_synthesis": elite_synthesis,
                # Résumé enrichi pour consommation rapide
                "summary": {
                    "blind_confluence_score": blind_score,
                    "menthorq_blind_spots": top_blinds,
                    "vp": vp_blk,
                },
                
                # Message clair
                "message": self._build_clear_message(go_live, elite_synthesis, day_ok, qc_reason, symbol)
            }
            
            # 6) Envoyer le message
            if self.config.get("send_messages", True):
                self._send_decision_message(robust_result)
            
            logger.info(f"🛡️ Unification ES terminée: {robust_result['processing_time_ms']:.1f}ms")
            return robust_result
            
        except Exception as e:
            logger.error(f"❌ Erreur unification ES: {e}")
            return {
                "timestamp": time.time(),
                "processing_time_ms": (time.perf_counter() - start_time) * 1000,
                "chart": self.chart_number,
                "symbol_family": "ES",
                "error": str(e),
                "gating": {"go_live": False, "error": True},
                "message": f"❌ Erreur ES: {e}"
            }
    
    def _is_es_family(self, symbol: str) -> bool:
        """Vérifier si le symbole fait partie de la famille ES"""
        clean_symbol = symbol.upper()
        for suffix in ["Z25", "H26", "M26", "U26", "Z26", "_FUT", "_CME"]:
            clean_symbol = clean_symbol.replace(suffix, "")
        return clean_symbol in self.supported_symbols
    
    def _check_daily_qc_chart3(self, date_str: str) -> Tuple[bool, str]:
        """Vérifier le QC journalier pour Chart 3"""
        try:
            # Chercher le fichier QC où qu'il soit dans DATA_SIERRA_CHART (mois variable)
            base = pathlib.Path("DATA_SIERRA_CHART")
            qc_path = None
            if base.exists():
                for p in base.rglob(f"**/CHART_{self.chart_number}/chart_{self.chart_number}_qc_go_nogo_{date_str}.json"):
                    qc_path = p
                    break
            if qc_path is None:
                # Fallback chemin historique
                qc_path = pathlib.Path(f"DATA_SIERRA_CHART/DATA_2025/{date_str}/CHART_{self.chart_number}/chart_{self.chart_number}_qc_go_nogo_{date_str}.json")
            
            if not qc_path.exists():
                # Throttle du warning pour éviter le spam
                import time as _t
                global _last_qc_warn_ts
                if self.allow_missing_qc:
                    if _t.time() - _last_qc_warn_ts > 5.0:
                        logger.warning(f"⚠️ Fichier QC Chart {self.chart_number} non trouvé: {qc_path} (autorisé en mode dev)")
                        _last_qc_warn_ts = _t.time()
                    return True, "qc_missing_allowed"
                else:
                    if _t.time() - _last_qc_warn_ts > 5.0:
                        logger.warning(f"⚠️ Fichier QC Chart {self.chart_number} non trouvé: {qc_path}")
                        _last_qc_warn_ts = _t.time()
                    return False, "qc_missing"
            
            # Lire le QC
            qc_data = json.loads(qc_path.read_text(encoding="utf-8"))
            go = qc_data.get("go", False)
            reason = qc_data.get("reason", "QC non spécifié")
            
            if go:
                logger.info(f"✅ QC Chart {self.chart_number} OK: {reason}")
            else:
                logger.warning(f"❌ QC Chart {self.chart_number} KO: {reason}")
            
            return go, reason
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture QC Chart {self.chart_number}: {e}")
            if self.allow_missing_qc:
                return True, "qc_parse_failed_allowed"
            else:
                return False, f"Erreur QC: {e}"

    def _compute_data_age_ms(self, snapshot: Dict[str, Any]) -> float:
        """Calcule l'âge (ms) du snapshot par rapport à l'horloge système."""
        try:
            ts = snapshot.get("t") or snapshot.get("ts")
            if ts is None:
                return 0.0
            if isinstance(ts, (int, float)):
                snap_s = float(ts)
            else:
                from datetime import datetime
                snap_s = datetime.fromisoformat(str(ts).replace('Z', '+00:00')).timestamp()
            import time as _t
            return max(0.0, ( _t.time() - snap_s) * 1000.0)
        except Exception:
            return 0.0
    
    def _unify_with_elite_methods(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Unification avec les méthodes Elite (même code que l'unifier principal)"""
        try:
            # Construire le contexte de base
            base_ctx = build_ctx(snapshot)
            
            # === MENTHORQ ELITE ===
            menthorq_result = self._process_menthorq_elite(base_ctx, snapshot)
            base_ctx["menthorq_elite"] = menthorq_result
            
            # === BATTLE NAVALE ELITE ===
            battle_navale_result = self._process_battle_navale_elite(base_ctx, snapshot)
            base_ctx["battle_navale_elite"] = battle_navale_result
            
            # === ORDERFLOW ADVANCED ===
            orderflow_result = self._process_orderflow_advanced(base_ctx, snapshot)
            base_ctx["orderflow_advanced"] = orderflow_result
            
            # === DOM HEALTH ===
            dom_health_result = self._process_dom_health(base_ctx, snapshot)
            base_ctx["dom_health"] = dom_health_result
            
            # === SYNTHÈSE ELITE ===
            elite_synthesis = self._synthesize_elite_results(
                menthorq_result, battle_navale_result, orderflow_result, dom_health_result
            )
            base_ctx["elite_synthesis"] = elite_synthesis
            
            base_ctx["elite_methods"] = {
                "available": True,
                "processed_at": datetime.now().isoformat(),
                "chart": self.chart_number,
                "symbol_family": "ES"
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement Elite ES: {e}")
            base_ctx["elite_methods"] = {
                "available": False,
                "error": str(e),
                "chart": self.chart_number,
                "symbol_family": "ES"
            }
        
        return base_ctx
    
    def _process_menthorq_elite(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite MenthorQ Elite (même code que l'unifier principal)"""
        try:
            if not self.menthorq_elite:
                return {"score": 0.0, "error": "MenthorQ Elite non disponible"}
            
            # ✅ Utiliser le payload correctement formaté
            menthorq_data = self.legacy_adapter.to_menthorq_payload(snapshot)
            
            qc = ctx.get('qc_context', {})
            current_price = ctx.get('current_price', 0.0)
            symbol = ctx.get('sym', 'ES')
            intended_direction = 1  # Par défaut LONG
            
            result = self.menthorq_elite.calculate_menthorq_elite(
                menthorq_data, current_price, symbol, intended_direction, qc
            )
            
            return {
                "score": result.menthorq_score,
                "raw_score": result.raw_score,
                "vix_multiplier": result.vix_multiplier,
                "is_signal": result.is_signal,
                "signal_strength": result.signal_strength,
                "risk_multiplier": result.risk_multiplier,
                "patience_minutes": result.patience_minutes,
                "calculation_time_ms": result.calculation_time_ms,
                "timestamp": result.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur MenthorQ Elite ES: {e}")
            return {"score": 0.0, "error": str(e)}
    
    def _process_battle_navale_elite(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite Battle Navale Elite (même code que l'unifier principal)"""
        try:
            if not self.battle_navale_elite:
                return {"score": 0.0, "error": "Battle Navale Elite non disponible"}
            
            # Construire les données Battle Navale
            # ✅ CORRECTION: S'assurer que le VWAP est disponible dans structure
            micro_data = ctx.get('micro', {})
            if micro_data.get('vwap', {}).get('vwap', 0.0) == 0.0:
                # Fallback: utiliser le VWAP du payload MenthorQ
                try:
                    from unifier.legacy_adapter import LegacyAdapter
                    adapter = LegacyAdapter()
                    current_price = ctx.get('current_price', 0.0)
                    mq_payload = adapter.build_menthorq_payload(snapshot, current_price)
                    vwap_value = mq_payload.get('vwap', {}).get('vwap', 0.0)
                    if vwap_value > 0:
                        micro_data['vwap'] = {'vwap': vwap_value}
                except Exception:
                    pass
            
            battle_navale_data = {
                'dom': ctx.get('ofdom', {}),
                'structure': micro_data,
                'leadership': ctx.get('leadership', {}),
                'confluence': ctx.get('cluster', {}),
                'mia': ctx.get('mia', {})
            }
            
            qc = ctx.get('qc_context', {})
            current_price = ctx.get('current_price', 0.0)
            symbol = ctx.get('sym', 'ES')
            intended_direction = 1  # Par défaut LONG
            
            # Compatibilité multi-signatures (anciennes/nouvelles)
            vix_level = ctx.get('vix', snapshot.get('vix', 18.5))
            try:
                result = self.battle_navale_elite.calculate_battle_navale_elite(
                    battle_navale_data, current_price, symbol, intended_direction, qc, vix_level
                )
            except TypeError:
                try:
                    result = self.battle_navale_elite.calculate_battle_navale_elite(
                        battle_navale_data, current_price, symbol, intended_direction, qc
                    )
                except TypeError:
                    # Fallback minimal si signature incompatible
                    return {"score": 0.0, "error": "BN incompatible signature"}
            
            return {
                "score": result.battle_navale_score,
                "raw_score": result.raw_score,
                "gates_status": result.gates_status,
                "is_signal": result.is_signal,
                "signal_strength": result.signal_strength,
                "risk_multiplier": result.risk_multiplier,
                "patience_minutes": result.patience_minutes,
                "calculation_time_ms": result.calculation_time_ms,
                "timestamp": result.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur Battle Navale Elite ES: {e}")
            return {"score": 0.0, "error": str(e)}
    
    def _process_orderflow_advanced(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite OrderFlow Advanced (même code que l'unifier principal)"""
        try:
            if not self.orderflow_advanced:
                return {"score": 0.0, "error": "OrderFlow Advanced non disponible"}
            
            # Construire les données OrderFlow
            orderflow_data = {
                'trade_summary': snapshot.get('trade_summary', {}),
                'order_book': snapshot.get('order_book', {}),
                'current_price': ctx.get('current_price', 0.0)
            }
            
            # Compatibilité: certaines versions exposent analyze(orderflow_data)
            if hasattr(self.orderflow_advanced, 'analyze_orderflow'):
                result = self.orderflow_advanced.analyze_orderflow(orderflow_data)
            elif hasattr(self.orderflow_advanced, 'analyze'):
                result = self.orderflow_advanced.analyze(orderflow_data)
            else:
                return {"score": 0.0, "error": "OrderFlow analyzer indisponible"}
            
            return {
                "score": result.get('orderflow_score', 0.0),
                "delta_score": result.get('delta_score', 0.0),
                "volume_score": result.get('volume_score', 0.0),
                "imbalance_score": result.get('imbalance_score', 0.0),
                "is_signal": result.get('is_signal', False),
                "signal_strength": result.get('signal_strength', 'WEAK'),
                "calculation_time_ms": result.get('calculation_time_ms', 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur OrderFlow Advanced ES: {e}")
            return {"score": 0.0, "error": str(e)}
    
    def _process_dom_health(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite DOM Health (même code que l'unifier principal)"""
        try:
            if not self.dom_health_analyzer:
                return {"score": 0.0, "error": "DOM Health non disponible"}
            
            # Construire les données DOM
            dom_data = {
                'order_book': ctx.get('ofdom', {}),
                'current_price': ctx.get('current_price', 0.0),
                'symbol': ctx.get('sym', 'ES')
            }
            
            # Compatibilité: certaines versions exposent analyze(dom_data)
            if hasattr(self.dom_health_analyzer, 'analyze_dom_health'):
                result = self.dom_health_analyzer.analyze_dom_health(dom_data)
            elif hasattr(self.dom_health_analyzer, 'analyze'):
                result = self.dom_health_analyzer.analyze(dom_data)
            else:
                return {"score": 0.0, "error": "DOM Health analyzer indisponible"}
            
            return {
                "score": result.get('dom_health_score', 0.0),
                "spread_score": result.get('spread_score', 0.0),
                "depth_score": result.get('depth_score', 0.0),
                "imbalance_score": result.get('imbalance_score', 0.0),
                "is_healthy": result.get('is_healthy', False),
                "health_level": result.get('health_level', 'POOR'),
                "calculation_time_ms": result.get('calculation_time_ms', 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur DOM Health ES: {e}")
            return {"score": 0.0, "error": str(e)}
    
    def _synthesize_elite_results(self, menthorq_result: Dict, battle_navale_result: Dict, 
                                 orderflow_result: Dict, dom_health_result: Dict) -> Dict[str, Any]:
        """Synthèse des résultats Elite (même code que l'unifier principal)"""
        try:
            # Scores des composants
            menthorq_score = menthorq_result.get("score", 0.0)
            battle_navale_score = battle_navale_result.get("score", 0.0)
            orderflow_score = orderflow_result.get("score", 0.0)
            dom_health_score = dom_health_result.get("score", 0.0)
            
            # Poids des composants
            weights = {
                "menthorq_elite": 0.40,
                "battle_navale_elite": 0.35,
                "orderflow_advanced": 0.15,
                "dom_health": 0.10
            }
            
            # Score composite pondéré
            composite_score = (
                menthorq_score * weights["menthorq_elite"] +
                battle_navale_score * weights["battle_navale_elite"] +
                orderflow_score * weights["orderflow_advanced"] +
                dom_health_score * weights["dom_health"]
            )
            
            # Gates status
            gates_status = battle_navale_result.get("gates_status", {})
            overall_gates_ok = gates_status.get("overall_gates_ok", False)
            
            # Signal final
            is_signal = (
                menthorq_result.get("is_signal", False) and
                battle_navale_result.get("is_signal", False) and
                overall_gates_ok and
                composite_score > 0.5
            )
            
            # Confiance
            confidence = min(composite_score * 1.2, 1.0) if is_signal else composite_score
            
            return {
                "composite_score": composite_score,
                "confidence": confidence,
                "is_signal": is_signal,
                "component_scores": {
                    "menthorq_elite": menthorq_score,
                    "battle_navale_elite": battle_navale_score,
                    "orderflow_advanced": orderflow_score,
                    "dom_health": dom_health_score
                },
                "gates_status": gates_status,
                "weights": weights,
                "chart": self.chart_number,
                "symbol_family": "ES"
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur synthèse Elite ES: {e}")
            return {
                "composite_score": 0.0,
                "confidence": 0.0,
                "is_signal": False,
                "error": str(e),
                "chart": self.chart_number,
                "symbol_family": "ES"
            }
    
    def _build_clear_message(self, go_live: bool, elite_synthesis: Dict, day_ok: bool, qc_reason: str, symbol: str = "ES") -> str:
        """Construire un message clair et sympa"""
        if go_live:
            # GO
            composite = elite_synthesis.get("composite_score", 0.0)
            scores = elite_synthesis.get("component_scores", {})
            mq = scores.get("menthorq_elite", 0.0)
            bn = scores.get("battle_navale_elite", 0.0)
            of = scores.get("orderflow_advanced", 0.0)
            dom = scores.get("dom_health", 0.0)
            
            return (f"✅ GO ES | composite={composite:.3f} | "
                   f"MQ={mq:.2f} BN={bn:.2f} OF={of:.2f} DOM={dom:.2f} | "
                   f"Gates OK (BN+DOM) → j'exécute")
        else:
            # NO_GO
            if not day_ok:
                return f"❌ NO_GO {symbol} | QC jour KO: {qc_reason}"
            else:
                gates_status = elite_synthesis.get("gates_status", {})
                gates_line = self._compose_gates_line(gates_status)
                return f"❌ NO_GO {symbol} | Gates Elite KO: {gates_line}"
    
    def _compose_gates_line(self, gates_status: Dict[str, Any]) -> str:
        """Composer la ligne des gates avec emojis corrects"""
        def _ok(v): return "✅" if v else "❌"
        
        return (f"DOM {_ok(gates_status.get('dom_ok'))} | "
                f"Struct {_ok(gates_status.get('structure_ok'))} | "
                f"Lead {_ok(gates_status.get('leadership_ok'))} | "
                f"Final {_ok(gates_status.get('final_ok'))}")
    
    def _send_decision_message(self, robust_result: Dict[str, Any]):
        """Envoyer le message de décision"""
        try:
            # Construire la décision pour le messenger
            gating = robust_result["gating"]
            elite = robust_result["elite_synthesis"]
            
            # Extraire le symbole du snapshot
            symbol = robust_result.get("snapshot", {}).get("sym", "ES")
            
            decision = {
                "mode": "LIVE",
                "symbol": symbol,  # Symbole réel du snapshot
                "direction": 1,
                "menthorq": {
                    "score": elite.get("component_scores", {}).get("menthorq_elite", 0.0),
                    "signal": elite.get("is_signal", False),
                    "strength": "STRONG" if elite.get("composite_score", 0) > 0.7 else "MODERATE"
                },
                "battle_navale": {
                    "score": elite.get("component_scores", {}).get("battle_navale_elite", 0.0),
                    "gates_detail": elite.get("gates_status", {}),
                    "blocked_by": []
                },
                "final": {
                    "score": elite.get("composite_score", 0.0),
                    "execute": gating["go_live"],
                    "override": "off"
                },
                "context": {
                    "vix": 18.5,
                    "options_age_min": 2,
                    "latency_ms": robust_result["processing_time_ms"]
                }
            }
            
            # Envoyer via le messenger
            self.decision_messenger.send_decision(decision, force=True)
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi message ES: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du unifier ES"""
        return {
            "chart": self.chart_number,
            "symbol_family": "ES",
            "supported_symbols": self.supported_symbols,
            "elite_modules_available": ELITE_MODULES_AVAILABLE,
            "decision_messenger": self.decision_messenger.get_stats(),
            "allow_missing_qc": self.allow_missing_qc
        }

# Fonction d'export
def unify_es_elite(snapshot: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fonction d'export pour unification ES Elite
    
    Args:
        snapshot: Snapshot de données
        config: Configuration optionnelle
        
    Returns:
        Résultat de l'unification ES Elite
    """
    unifier = EliteUnifierES(config)
    return unifier.unify_es(snapshot)

# Test rapide
if __name__ == "__main__":
    print("🧪 Test Elite Unifier ES...")
    
    # Test snapshot ES
    test_snapshot = {
        "sym": "ESZ25_FUT_CME",
        "t": int(time.time()),
        "last": 4150.25,
        "phase": "REGULAR",
        "regime": "TREND",
        "vix": 18.5,
        "mentorq_gamma": {"levels": [], "call_wall": 4155.0, "put_wall": 4145.0},
        "mentorq_blind": {"spots": [], "spot_1": 4152.0, "spot_2": 4148.0},
        "vwap": {"value": 4150.0, "upper_band": 4155.0, "lower_band": 4145.0},
        "vp": {"vpoc": 4150.0, "val": 4145.0, "vah": 4155.0},
        "ofdom": {"best_bid": 4150.0, "best_ask": 4150.25, "spread": 0.25},
        "lead": {"nq_stronger_than_es": False, "sync_ok": True},
        "mia_score": 0.75,
        "mia_state": "BULLISH"
    }
    
    # Test
    result = unify_es_elite(test_snapshot)
    print(f"✅ Résultat ES: {result['gating']['go_live']}")
    print(f"📝 Message: {result['message']}")
    print(f"⏱️ Temps: {result['processing_time_ms']:.1f}ms")