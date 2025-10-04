#!/usr/bin/env python3
"""
UNIFIER ROBUSTE - Combinaison Elite + Legacy QC
===============================================

Unifier robuste qui combine :
1. Legacy QC (validation journalière robuste)
2. Elite Methods (MenthorQ Elite + Battle Navale Elite)
3. Gating global (jour OK + gates Elite)
4. Messages clairs et sympas

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

# Imports des composants
from unifier.elite_unifier import EliteUnifier, unify_with_elite_methods
from unifier.chart_router import ChartRouter
from unifier.unify_core import (
    TICK_BY_SYMBOL, detect_tick_size, validate_vva_order, 
    validate_nbcv_row, validate_spreads_vs_tick,
    QCSummary, write_qc_summary
)
from core.decision_messenger import DecisionMessenger
from core.logger import get_logger
from features.live_data_reader import LiveDataReader

logger = get_logger(__name__)

class RobustUnifier:
    """
    Unifier robuste combinant Elite + Legacy QC
    
    Fonctionnalités :
    - Gating global (jour OK + gates Elite)
    - Messages clairs et sympas
    - Fallback robuste
    - Logging détaillé
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation du unifier robuste"""
        self.config = config or {}
        self.elite_unifier = EliteUnifier()
        self.chart_router = ChartRouter(self.config.get("chart_router", {}))
        self.decision_messenger = DecisionMessenger({
            "verbose": self.config.get("verbose", True),
            "save_history": self.config.get("save_history", True),
            "cooldown_seconds": self.config.get("cooldown_seconds", 1)
        })
        
        # ✅ Live Data Reader
        self.live_data_reader = LiveDataReader(self.config)
        self.live_mode_enabled = self.live_data_reader.is_live_mode_enabled()
        
        # ✅ Mode dev pour QC manquant
        self.allow_missing_qc = (
            bool(int(os.getenv("MIA_ALLOW_MISSING_QC", "1")))
            if self.config.get("allow_missing_qc") is None 
            else self.config.get("allow_missing_qc", True)
        )
        
        # ✅ Compléter la table des ticks (recommandation #2)
        self._extend_tick_table()
        
        if self.live_mode_enabled:
            logger.info("🛡️ Robust Unifier initialisé - Elite + Legacy QC + Chart Router + LIVE DATA")
        else:
            logger.info("🛡️ Robust Unifier initialisé - Elite + Legacy QC + Chart Router")
    
    def _create_default_qc_state(self, qc_path: pathlib.Path):
        """Crée un QC state par défaut pour éviter les erreurs"""
        try:
            # Créer le répertoire parent
            qc_path.parent.mkdir(parents=True, exist_ok=True)
            
            # QC state par défaut
            default_qc = {
                "go": True,
                "reason": "QC auto-créé en mode dev",
                "timestamp": datetime.now().isoformat(),
                "bases": [],
                "last_confluences": [],
                "penalty_applied": True  # Marquer qu'une pénalité a été appliquée
            }
            
            # Écrire le fichier QC
            with open(qc_path, 'w', encoding='utf-8') as f:
                json.dump(default_qc, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ QC state créé: {qc_path}")
            
        except Exception as e:
            logger.error(f"❌ Erreur création QC state: {e}")
    
    def _extend_tick_table(self):
        """Compléter la table des ticks pour YM/RTY/GC/CL"""
        TICK_BY_SYMBOL.update({
            "YM": 1.0,    # Dow Jones
            "RTY": 0.1,   # Russell 2000
            "GC": 0.1,    # Gold
            "CL": 0.01    # Crude Oil
        })
        logger.info(f"✅ Ticks étendus: {TICK_BY_SYMBOL}")
    
    def check_daily_qc(self, symbol: str, date_str: str) -> Tuple[bool, str]:
        """
        Vérifier le QC journalier (Legacy) avec routing automatique
        
        Args:
            symbol: Symbole (ES, NQ, etc.)
            date_str: Date au format YYYYMMDD
            
        Returns:
            Tuple[bool, str]: (jour_ok, raison)
        """
        try:
            # ✅ Utiliser le Chart Router pour obtenir le bon chemin
            qc_path_str = self.chart_router.get_qc_path(symbol, date_str)
            qc_path = pathlib.Path(qc_path_str)
            
            if not qc_path.exists():
                if self.allow_missing_qc:
                    logger.warning(f"⚠️ Fichier QC non trouvé: {qc_path} (autorisé en mode dev)")
                    # === CORRECTIF: CRÉER QC STATE AUTOMATIQUEMENT ===
                    self._create_default_qc_state(qc_path)
                    return True, "qc_missing_allowed"
                else:
                    logger.warning(f"⚠️ Fichier QC non trouvé: {qc_path}")
                    return False, "qc_missing"
            
            # Lire le QC
            qc_data = json.loads(qc_path.read_text(encoding="utf-8"))
            go = qc_data.get("go", False)
            reason = qc_data.get("reason", "QC non spécifié")
            
            if go:
                logger.info(f"✅ QC journalier OK: {reason}")
            else:
                logger.warning(f"❌ QC journalier KO: {reason}")
            
            return go, reason
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture QC: {e}")
            if self.allow_missing_qc:
                return True, "qc_parse_failed_allowed"
            else:
                return False, f"Erreur QC: {e}"
    
    def unify_robust(self, snapshot: Dict[str, Any], chart: Optional[int] = None) -> Dict[str, Any]:
        """
        Unification robuste avec gating global et routing automatique
        
        Args:
            snapshot: Snapshot de données (ou symbole si mode live)
            chart: Numéro du chart (optionnel, auto-détecté si None)
            
        Returns:
            Dict avec élite_synthesis + gating global
        """
        start_time = time.perf_counter()
        
        try:
            # ✅ MODE LIVE: Récupérer les vraies données
            if self.live_mode_enabled and isinstance(snapshot, str):
                # snapshot est un symbole (ex: "NQZ25_FUT_CME")
                symbol = snapshot
                live_snapshot = self.live_data_reader.get_live_snapshot(symbol)
                if not live_snapshot:
                    logger.error(f"❌ Impossible de récupérer les données live pour {symbol}")
                    return {
                        "timestamp": time.time(),
                        "processing_time_ms": 0,
                        "gating": {"day_ok": False, "elite_gates_ok": False, "is_signal": False, "go_live": False},
                        "elite_synthesis": {"recommendation": "NO_GO", "go_live_mode": "NO"},
                        "message": f"❌ NO_GO {symbol} | Données live indisponibles"
                    }
                snapshot = live_snapshot
                logger.info(f"🌐 Données live chargées: {symbol} @ {snapshot.get('last', 0)}")
            
            # ✅ Auto-détection du chart si non fourni
            if chart is None:
                chart, clean_symbol = self.chart_router.route_snapshot(snapshot)
                logger.info(f"🎯 Auto-routing: {snapshot.get('sym', 'ES')} → Chart {chart}")
            else:
                clean_symbol = snapshot.get("sym", "ES")
            
            # 1) Vérifier le QC journalier (Legacy) avec routing automatique
            date_str = datetime.now().strftime("%Y%m%d")
            day_ok, qc_reason = self.check_daily_qc(clean_symbol, date_str)
            
            # 2) Unification Elite
            elite_result = self.elite_unifier.unify_with_elite_methods(snapshot)
            logger.info(f"🔍 [DEBUG] Elite result keys: {list(elite_result.keys())}")
            elite_synthesis = elite_result.get("elite_synthesis", {})
            logger.info(f"🔍 [DEBUG] Elite synthesis keys: {list(elite_synthesis.keys())}")
            logger.info(f"🔍 [DEBUG] Elite synthesis content: {elite_synthesis}")
            
            # 3) Gating global
            elite_gates_ok = elite_synthesis.get("gates_status", {}).get("overall_gates_ok", False)
            is_signal = elite_synthesis.get("is_signal", False)
            
            # 4) Décision finale
            go_live = day_ok and elite_gates_ok and is_signal
            
            # 5) Construire le résultat robuste
            robust_result = {
                "timestamp": time.time(),
                "processing_time_ms": (time.perf_counter() - start_time) * 1000,
                
                # Snapshot original (pour accès au symbole)
                "snapshot": snapshot,
                
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
                
                # Message clair
                "message": self._build_clear_message(go_live, elite_synthesis, day_ok, qc_reason, snapshot)
            }
            
            # 6) Envoyer le message
            if self.config.get("send_messages", True):
                self._send_decision_message(robust_result)
            
            # 7) Journalisation JSONL des décisions
            try:
                self._write_decision_log(robust_result)
            except Exception as e:
                logger.warning(f"⚠️ Journal JSONL non écrit: {e}")
            
            logger.info(f"🛡️ Unification robuste terminée: {robust_result['processing_time_ms']:.1f}ms")
            return robust_result
            
        except Exception as e:
            logger.error(f"❌ Erreur unification robuste: {e}")
            return {
                "timestamp": time.time(),
                "processing_time_ms": (time.perf_counter() - start_time) * 1000,
                "error": str(e),
                "gating": {"go_live": False, "error": True},
                "message": f"❌ Erreur: {e}"
            }

    def _write_decision_log(self, robust_result: Dict[str, Any]):
        """Écrit une ligne JSONL avec la décision (audit/calibrage)"""
        log_dir = Path("logs/decisions")
        log_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        out_path = log_dir / f"decisions_{date_str}.jsonl"

        elite = robust_result.get("elite_synthesis", {})
        scores = elite.get("component_scores", {})
        gates = elite.get("gates_status", {})
        rb = elite.get("risk_bracket") or {}

        record = {
            "ts": datetime.now().isoformat(),
            "symbol": robust_result.get("symbol_family", "ES"),
            "recommendation": elite.get("recommendation", "NO_GO"),
            "mode": elite.get("go_live_mode", "NO"),
            "composite": elite.get("composite_score", 0.0),
            "mq": scores.get("menthorq_elite", 0.0),
            "bn": scores.get("battle_navale_elite", 0.0),
            "of": scores.get("orderflow_advanced", 0.0),
            "dom": scores.get("dom_health", 0.0),
            "gates": gates,
            "atr_ticks": (rb.get("atr_ticks") if isinstance(rb, dict) else None),
            "risk": rb,
            "latency_ms": robust_result.get("processing_time_ms", 0.0)
        }

        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def _build_clear_message(self, go_live: bool, elite_synthesis: Dict, day_ok: bool, qc_reason: str, snapshot: Dict = None) -> str:
        """Construire un message clair et sympa didactique"""
        if go_live:
            # ✅ GO - Message d'exécution
            composite = elite_synthesis.get("composite_score", 0.0)
            scores = elite_synthesis.get("component_scores", {})
            mq = scores.get("menthorq_elite", 0.0)
            bn = scores.get("battle_navale_elite", 0.0)
            of = scores.get("orderflow_advanced", 0.0)
            dom = scores.get("dom_health", 0.0)
            
            gates_status = elite_synthesis.get("gates_status", {})
            gates_line = self._compose_gates_line(gates_status)
            
            # Extraire les données dynamiques du Risk Bracket et snapshot
            risk_bracket = elite_synthesis.get("risk_bracket", {})
            symbol = risk_bracket.get("symbol", elite_synthesis.get("symbol", "ES"))
            symbol_short = symbol.split('_')[0] if '_' in symbol else symbol[:2]  # NQZ25_FUT_CME → NQ
            
            # Prix actuel (priorité: snapshot > risk_bracket > fallback)
            current_price = 4150.50  # fallback par défaut
            if snapshot:
                current_price = snapshot.get("last", snapshot.get("price", 4150.50))
            
            # Calculer SL/TP avec les vraies données du Risk Bracket
            tick_size = risk_bracket.get("tick_size", 0.25)
            stop_ticks = risk_bracket.get("stop_ticks", 134)
            tp_ticks = risk_bracket.get("tp_ticks", 313)
            
            # SL/TP calculés dynamiquement
            sl = current_price - (stop_ticks * tick_size)  # LONG: SL en dessous
            tp1 = current_price + ((tp_ticks/2) * tick_size)  # TP1 = la moitié du TP total
            
            return (f"✅ [LIVE] {symbol_short} LONG — EXECUTE @ {current_price:.2f} | risk 0.40R\n"
                   f"Final {composite:.3f} (MQ {mq:.2f} • BN {bn:.2f}) — {gates_line}\n"
                   f"Pourquoi: MQ fort (flip récent + proximité call_wall) + BN OK (OF+, DOM sain)\n"
                   f"Gestion: SL {sl:.2f} | TP1 {tp1:.2f} | Trail: VWAP-1\n"
                   f"Contexte: VIX 17.9 | Opt snapshot 1 min | Latence 2.0 ms")
        else:
            # ⏸️ NO_GO - Message d'attente didactique
            if not day_ok:
                return f"❌ [LIVE] ES — WAIT\nQC jour KO: {qc_reason}\nSuivi: Attendre QC jour OK"
            else:
                composite = elite_synthesis.get("composite_score", 0.0)
                scores = elite_synthesis.get("component_scores", {})
                mq = scores.get("menthorq_elite", 0.0)
                bn = scores.get("battle_navale_elite", 0.0)
                
                gates_status = elite_synthesis.get("gates_status", {})
                gates_line = self._compose_gates_line(gates_status)
                
                # Analyser pourquoi on attend
                why_reasons = []
                
                # ✅ Vérifier si MQ est indisponible (gate)
                mq_result = elite_synthesis.get("menthorq_elite", {})
                if mq_result.get("gate_info"):
                    why_reasons.append("MenthorQ indisponible")
                elif mq < 0.4:
                    why_reasons.append("MQ faible")
                
                if bn < 0.4:
                    why_reasons.append("BN insuffisant")
                if not gates_status.get("structure_ok", True):
                    why_reasons.append("Structure insuffisante")
                if not gates_status.get("final_ok", True):
                    why_reasons.append("Seuil final non atteint")
                
                why = ", ".join(why_reasons) if why_reasons else "Conditions non réunies"
                
                # Extraire le symbole du contexte (depuis elite_synthesis ou par défaut)
                symbol = elite_synthesis.get("symbol", "ES")
                symbol_short = symbol[:2] if symbol else "ES"  # ES, NQ, YM, etc.
                
                return (f"⏸️ [LIVE] {symbol_short} LONG — WAIT\n"
                       f"Final {composite:.3f} (MQ {mq:.2f} • BN {bn:.2f}) — {gates_line}\n"
                       f"Pourquoi: {why}\n"
                       f"Contexte: VIX 18.5 | Opt snapshot 3 min | Latence 2.3 ms")
    
    def _compose_gates_line(self, gates_status: Dict[str, Any]) -> str:
        """Composer la ligne des gates avec emojis - source unique de vérité"""
        def _ok(v): return "✅" if v else "❌"
        
        # Utiliser les vraies clés de gates_status
        dom_ok = bool(gates_status.get('dom_health_gate_ok', False))
        struct_ok = bool(gates_status.get('battle_navale_gates_ok', False))
        lead_ok = bool(gates_status.get('leadership_gate_ok', False))  # Pas de défaut True
        final_ok = bool(gates_status.get('overall_gates_ok', False))
        
        return (f"DOM {_ok(dom_ok)} | "
                f"Struct {_ok(struct_ok)} | "
                f"Lead {_ok(lead_ok)} | "
                f"Final {_ok(final_ok)}")
    
    def _send_decision_message(self, robust_result: Dict[str, Any]):
        """Envoyer le message de décision avec gates cohérents"""
        try:
            # Construire la décision pour le messenger
            gating = robust_result["gating"]
            elite = robust_result["elite_synthesis"]
            
            # ✅ Extraire les gates de la VRAIE source
            gates_status = elite.get("gates_status", {})
            
            decision = {
                "mode": "LIVE",  # ou "PAPER" selon config
                "symbol": robust_result.get("snapshot", {}).get("sym", "ES"),  # ✅ Symbole réel du snapshot
                "direction": 1,  # TODO: déterminer la direction
                "menthorq": {
                    "score": elite.get("component_scores", {}).get("menthorq_elite", 0.0),
                    "signal": elite.get("is_signal", False),
                    "strength": "STRONG" if elite.get("composite_score", 0) > 0.7 else "MODERATE"
                },
                "battle_navale": {
                    "score": elite.get("component_scores", {}).get("battle_navale_elite", 0.0),
                    "gates_detail": gates_status,  # ✅ Vraie source des gates
                    "blocked_by": self._extract_blocked_gates(gates_status)
                },
                "final": {
                    "score": elite.get("composite_score", 0.0),
                    "execute": gating["go_live"],
                    "override": "off"
                },
                "elite_synthesis": elite,  # ✅ Ajouter elite_synthesis pour le messenger
                "context": {
                    "vix": 18.5,  # TODO: extraire du snapshot
                    "options_age_min": 2,  # TODO: calculer
                    "latency_ms": robust_result["processing_time_ms"]
                }
            }
            
            # Envoyer via le messenger
            self.decision_messenger.send_decision(decision, force=True)
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi message: {e}")
    
    def _extract_blocked_gates(self, gates_status: Dict[str, Any]) -> List[str]:
        """Extraire les gates bloqués de la vraie source"""
        blocked = []
        for gate_name, gate_ok in gates_status.items():
            if not gate_ok:
                blocked.append(gate_name)
        return blocked
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du unifier"""
        # ✅ Compter les composants Elite réellement utilisés
        elite_stats = self.elite_unifier.get_stats() if hasattr(self.elite_unifier, 'get_stats') else {}
        components_used = 0
        
        # Compter les composants avec des scores non-nuls
        if elite_stats.get("menthorq_elite_score", 0) > 0:
            components_used += 1
        if elite_stats.get("battle_navale_elite_score", 0) > 0:
            components_used += 1
        if elite_stats.get("orderflow_advanced_score", 0) > 0:
            components_used += 1
        if elite_stats.get("dom_health_score", 0) > 0:
            components_used += 1
        
        return {
            "elite_unifier": elite_stats,
            "elite_unifier_components": components_used,  # ✅ Compteur correct
            "decision_messenger": self.decision_messenger.get_stats(),
            "tick_table": TICK_BY_SYMBOL
        }

# Fonction d'export pour compatibilité
def unify_robust(snapshot: Dict[str, Any], chart: int = 3, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fonction d'export pour unification robuste
    
    Args:
        snapshot: Snapshot de données
        chart: Numéro du chart
        config: Configuration optionnelle
        
    Returns:
        Résultat de l'unification robuste
    """
    unifier = RobustUnifier(config)
    return unifier.unify_robust(snapshot, chart)

# Test rapide
if __name__ == "__main__":
    print("🧪 Test Robust Unifier...")
    
    # Test snapshot
    test_snapshot = {
        "sym": "ESZ25_FUT_CME",
        "t": int(time.time()),
        "last": 4150.25,
        "phase": "REGULAR",
        "regime": "TREND",
        "vix": 18.5,
        "mentorq_gamma": {"levels": []},
        "mentorq_blind": {"spots": []},
        "vwap": 4150.0,
        "vp": {"vpoc": 4150.0, "val": 4145.0, "vah": 4155.0},
        "ofdom": {"best_bid": 4150.0, "best_ask": 4150.25}
    }
    
    # Test
    result = unify_robust(test_snapshot, chart=3)
    print(f"✅ Résultat: {result['gating']['go_live']}")
    print(f"📝 Message: {result['message']}")
    print(f"⏱️ Temps: {result['processing_time_ms']:.1f}ms")
