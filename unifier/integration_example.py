#!/usr/bin/env python3
"""
EXEMPLE D'INTÉGRATION - Unifier Robuste en action
================================================

Exemple complet d'intégration du unifier robuste avec :
1. Gating global (jour OK + gates Elite)
2. Messages clairs et sympas
3. Fallback robuste
4. Logging détaillé

Version: 1.0.0
Date: Janvier 2025
"""

import sys
import os
import json
import pathlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from collections import deque
from datetime import datetime
import time

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unifier.robust_unifier import RobustUnifier, unify_robust
from unifier.legacy_adapter import LegacyAdapter, adapt_legacy_snapshot
from core.logger import get_logger

logger = get_logger(__name__)

class IntegrationExample:
    """
    Exemple d'intégration complète du unifier robuste
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation de l'exemple d'intégration"""
        self.config = config or {}
        self.robust_unifier = RobustUnifier(self.config)
        self.legacy_adapter = LegacyAdapter()
        
        logger.info("🚀 Exemple d'intégration initialisé")
    
    def run_integration_example(self, chart: int = 3):
        """
        Exécuter l'exemple d'intégration complet
        
        Args:
            chart: Numéro du chart
        """
        print("🚀 EXEMPLE D'INTÉGRATION - UNIFIER ROBUSTE")
        print("=" * 60)
        
        # 1) Créer un snapshot legacy de test
        legacy_snapshot = self._create_test_legacy_snapshot()
        print(f"📊 Snapshot legacy créé: {legacy_snapshot['sym']} @ {legacy_snapshot['last']}")
        
        # 2) Adapter le snapshot pour Elite
        elite_snapshot = self.legacy_adapter.adapt_snapshot_for_elite(legacy_snapshot)
        print(f"🔄 Snapshot adapté pour Elite: {elite_snapshot['sym']} @ {elite_snapshot['last']}")
        
        # 3) Unification robuste
        print("\n🛡️ UNIFICATION ROBUSTE...")
        
        # ✅ Debug du payload MenthorQ avec les vraies données JSONL
        from unifier.legacy_adapter import LegacyAdapter
        adapter = LegacyAdapter()
        
        # Debug: vérifier les clés JSONL dans le snapshot
        jsonl_keys = [k for k in elite_snapshot.keys() if k.startswith("gex_") or k in ["hvl", "hvl_0dte", "call_resistance", "call_resistance_0dte", "put_support", "put_support_0dte"]]
        print(f"🔍 [DEBUG] Clés JSONL trouvées: {jsonl_keys}")
        print(f"🔍 [DEBUG] Exemple gex_1: {elite_snapshot.get('gex_1', 'NOT_FOUND')}")
        print(f"🔍 [DEBUG] Exemple hvl_0dte: {elite_snapshot.get('hvl_0dte', 'NOT_FOUND')}")
        
        # Utiliser build_menthorq_payload avec les vraies données JSONL
        current_price = elite_snapshot.get("last", 6700.0)
        mq_payload = adapter.build_menthorq_payload(elite_snapshot, current_price)
        print(f"🔍 [DEBUG] MQ payload (JSONL) = {json.dumps(mq_payload, default=str)[:400]}...")
        
        robust_result = self.robust_unifier.unify_robust(elite_snapshot, chart)
        
        # 4) Afficher les résultats
        self._display_results(robust_result)
        
        # 5) Afficher les statistiques
        self._display_stats()
        
        print("=" * 60)
        print("✅ Exemple d'intégration terminé")
    
    def _create_test_legacy_snapshot(self) -> Dict[str, Any]:
        """Créer un snapshot legacy de test avec VRAIES données MenthorQ JSONL"""
        snapshot = {
            # Par défaut: test NQ (Chart 9). Pour ES, remets ESZ25_FUT_CME et chart:3
            "sym": "NQZ25_FUT_CME",
            "t": int(time.time()),
            "last": 25500.0,  # Prix réaliste NQ (échelle)
            "phase": "REGULAR",
            "regime": "TREND",
            "vix": 18.5,
            "vix_trend": "DECLINING",
            
            # ✅ MenthorQ JSONL (vraies données du fichier) — NB: pour NQ, adapter si nécessaire
            "type": "menthorq_gamma",
            "i": 960,
            "chart": 9,
            "gex_1": 6700.0,
            "gex_2": 6725.0,
            "gex_3": 6675.0,
            "gex_4": 6740.0,
            "gex_5": 6670.0,
            "gex_6": 6800.0,
            "gex_7": 6650.0,
            "gex_8": 6775.0,
            "gex_9": 6790.0,
            "gex_10": 6625.0,
            "hvl": 6695.0,
            "hvl_0dte": 6705.0,
            "1d_max": 6768.9,
            "1d_min": 6658.1,
            "call_resistance": 6750.0,
            "call_resistance_0dte": 6710.0,
            "put_support": 6300.0,
            "put_support_0dte": 6660.0,
            "gamma_wall_0dte": 6750.0,
            
            # Blind spots (simulés)
            "blind_spot_1": 6690.0,
            "blind_spot_2": 6715.0,
            "liquidity_gap": 6705.0,
            "dead_zone": 6700.0,
            
            # Dealers bias (simulé)
            "bias_score": 0.2,
            "bias_strength": 0.6,
            "bias_confidence": 0.8,
            
            # VWAP (simulé)
            "study_vwap": 6700.0,
            "vwap_up1": 6710.0,
            "vwap_dn1": 6690.0,
            
            "vix_level": 18.5,
            
                # ✅ DOM / Orderflow (Battle Navale) - DONNÉES RÉALISTES NQ
                "best_bid": 25499.75,  # NQ échelle
                "best_ask": 25500.25,  # NQ échelle
                "l1_bbo_ratio": 0.90,
                "l1_bbo_ratio_rolling": 0.90,
                "depth_levels": 10,
                
                "buy_vol": 125000,
                "sell_vol": 120000,
                "cum_delta_session": 5000,  # >0 pour LONG
                
                # ✅ TRADE SUMMARY (OrderFlow Advanced) - DONNÉES RÉELLES DES DERNIÈRES LIGNES
                "trade_summary_current": {
                    "t": 45931.393853,
                    "sym": "ESZ25_FUT_CME",
                    "type": "trade_summary",
                    "buy_trades": 60710,
                    "sell_trades": 63706,
                    "buy_vol": 76708,
                    "sell_vol": 80989,
                    "chart": 3,
                    "cum_delta_day": -2759.0,
                    "cum_delta_session": 2204.0,
                    "session_id": "London"
                },
                
                    # ✅ TRADE SUMMARY HISTORY (dernières 10 entrées avec MOMENTUM CROISSANT)
                    "trade_summary_history": [
                        {"t": 45931.393583, "buy_trades": 60557, "sell_trades": 63603, "buy_vol": 76514, "sell_vol": 80858, "cum_delta_day": -2822.0, "cum_delta_session": 2204.0, "session_id": "London"},
                        {"t": 45931.393395, "buy_trades": 60427, "sell_trades": 63477, "buy_vol": 76315, "sell_vol": 80683, "cum_delta_day": -2846.0, "cum_delta_session": 2000.0, "session_id": "London"},
                        {"t": 45931.393359, "buy_trades": 60241, "sell_trades": 63407, "buy_vol": 76020, "sell_vol": 80586, "cum_delta_day": -3044.0, "cum_delta_session": 1800.0, "session_id": "London"},
                        {"t": 45931.392865, "buy_trades": 60077, "sell_trades": 63315, "buy_vol": 75804, "sell_vol": 80448, "cum_delta_day": -3122.0, "cum_delta_session": 1600.0, "session_id": "London"},
                        {"t": 45931.391970, "buy_trades": 59953, "sell_trades": 63183, "buy_vol": 75651, "sell_vol": 80224, "cum_delta_day": -3051.0, "cum_delta_session": 1400.0, "session_id": "London"},
                        {"t": 45931.391290, "buy_trades": 59798, "sell_trades": 63082, "buy_vol": 75462, "sell_vol": 80100, "cum_delta_day": -3116.0, "cum_delta_session": 1200.0, "session_id": "London"},
                        {"t": 45931.390158, "buy_trades": 59663, "sell_trades": 62961, "buy_vol": 75278, "sell_vol": 79916, "cum_delta_day": -3116.0, "cum_delta_session": 1000.0, "session_id": "London"},
                        {"t": 45931.389059, "buy_trades": 59529, "sell_trades": 62839, "buy_vol": 75088, "sell_vol": 79767, "cum_delta_day": -3157.0, "cum_delta_session": 800.0, "session_id": "London"},
                        {"t": 45931.388224, "buy_trades": 59397, "sell_trades": 62715, "buy_vol": 74918, "sell_vol": 79548, "cum_delta_day": -3108.0, "cum_delta_session": 600.0, "session_id": "London"},
                        {"t": 45931.387547, "buy_trades": 59289, "sell_trades": 62567, "buy_vol": 74773, "sell_vol": 79345, "cum_delta_day": -3050.0, "cum_delta_session": 400.0, "session_id": "London"}
                    ],
            
                # ✅ QC utiles
                "atr_per_bar": 2.0,
                "vwap_qc_p95": 0.12,
                
            # ✅ ATR RÉEL pour OrderFlow Advanced - 20 barres (NQ échelle)
            "price_highs": [25500.0 + (i * 5.0) + (10.0 if i % 2 == 0 else 7.5) for i in range(20)],
            "price_lows": [25500.0 - (i * 5.0) - (10.0 if i % 3 == 0 else 7.5) for i in range(20)],
            "price_closes": [25500.0 + (i * 2.0) + (8.0 if i % 4 == 0 else -4.0) for i in range(20)],
            
            # ✅ Volume profile (structure) - données riches pour BN
            "vpoc": 6700.0,
            "val": 6695.0,
            "vah": 6705.0,
            
            # ✅ VWAP pour éviter le fallback
            "vwap": 25500.0,  # VWAP NQ réaliste
            
            # ✅ Niveaux MenthorQ pour structure BN
            "menthorq_levels": [6705.0, 6710.0, 6660.0, 6685.0],  # HVL, CW, PS, ZG
            
            # Legacy format (pour compatibilité)
            "mentorq_gamma": {
                "levels": [
                    {"price": 6710.0, "gamma": 1000.0, "type": "call"},
                    {"price": 6660.0, "gamma": 800.0, "type": "put"}
                ],
                "call_wall": 6710.0,
                "put_wall": 6660.0,
                "zero_gamma": 6685.0,
                "gamma_max": 1000.0
            },
            "mentorq_swing": {"avail": True, "level": 6705.0, "strength": 0.75},
            "mentorq_blind": {
                "spots": [
                    {"price": 6715.0, "strength": 0.6},
                    {"price": 6690.0, "strength": 0.4}
                ],
                "spot_1": 6715.0,
                "spot_2": 6690.0
            },
            "scanner": {"recent": {"signals": 3, "strength": 0.8}},
            "qscore": 4,
            
            # Microstructure
            "vwap": {
                "value": 6700.0,
                "upper_band": 6710.0,
                "lower_band": 6690.0,
                "deviation": 0.25
            },
            "vp": {
                "vpoc": 6700.0,
                "val": 6695.0,
                "vah": 6705.0,
                "volume": 1000000
            },
            
            # Order Flow / DOM
            "ofdom": {
                "best_bid": 25499.75,  # NQ échelle
                "best_ask": 25500.25,  # NQ échelle
                "spread": 0.5,
                "bid_size": 150,
                "ask_size": 120,
                "volume_imbalance": 0.2,
                "l1_bbo_ratio": 1.0,
                "depth_imbalance": 0.15
            },
            
            # Leadership
            "lead": {
                "nq_stronger_than_es": False,
                "sync_ok": True,
                "correlation": 0.85,
                "lead_lag": 0.1
            },
            
            # Cluster
            "cluster": {
                "signals": {"confluence": 0.7, "strength": "STRONG"},
                "confluence_score": 0.7,
                "strength": "STRONG"
            },
            
            # MIA
            "mia_score": 0.75,
            "mia_state": "BULLISH",
            "prev_state": "NEUTRE",
            
            # QC
            "options_age_min": 2,
            "data_quality": 0.9,
            "atr_relative": 1.2
        }

        # ✅ Injecter OrderFlow Advanced réel depuis le fichier trade_summary JSONL si disponible
        try:
            sym = snapshot["sym"]
            if sym.startswith("NQ"):
                ts_path = Path("DATA_SIERRA_CHART/DATA_2025/OCTOBRE/20251001/CHART_9/chart_9_trade_summary_NQZ25_FUT_CME_20251001.jsonl")
            else:
                ts_path = Path("DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250929/CHART_3/chart_3_trade_summary_ESZ25_FUT_CME_20250929.jsonl")
            if ts_path.exists():
                current, history = self._load_trade_summary(str(ts_path), symbol_filter=snapshot["sym"], max_records=200)
                if current:
                    snapshot["trade_summary_current"] = current
                if history:
                    snapshot["trade_summary_history"] = history
                logger.info(f"📥 Trade summary injecté: current={'OK' if current else 'NONE'}, history={len(history) if history else 0}")
            else:
                logger.warning(f"⚠️ Fichier trade_summary introuvable: {ts_path}")
        except Exception as e:
            logger.error(f"❌ Erreur injection trade_summary: {e}")

        return snapshot

    def _load_trade_summary(self, file_path: str, symbol_filter: Optional[str] = None, max_records: int = 200) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Charge les derniers enregistrements trade_summary depuis un JSONL.
        Retourne (courant, historique_recent)
        """
        recent = deque(maxlen=max_records)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("type") != "trade_summary":
                        continue
                    if symbol_filter and rec.get("sym") != symbol_filter:
                        continue
                    recent.append(rec)
        except FileNotFoundError:
            return None, []
        except Exception as e:
            logger.error(f"❌ Erreur lecture trade_summary: {e}")
            return None, []

        if not recent:
            return None, []
        current = recent[-1]
        history = list(recent)
        return current, history
    
    def _display_results(self, robust_result: Dict[str, Any]):
        """Afficher les résultats de l'unification robuste"""
        print("\n📊 RÉSULTATS DE L'UNIFICATION ROBUSTE")
        print("-" * 40)
        
        # Vérifier si le résultat contient une erreur
        if "error" in robust_result:
            print(f"❌ Erreur: {robust_result['error']}")
            return
        
        # Gating
        gating = robust_result.get("gating", {})
        elite = robust_result.get("elite_synthesis", {})
        go_live_mode = elite.get("go_live_mode", "NO")
        
        # Signal state basé sur recommendation (avec helper défensif)
        rec = elite.get("recommendation", "NO_GO")
        # Jamais 'ERROR' à l'écran: on mappe dur → NO_GO par défaut
        signal_state = {"GO": "GO", "SCOUT_GO": "SCOUT_GO", "NO_GO": "NO_GO"}.get(str(rec), "NO_GO")
        
        print(f"🛡️ Gating Global:")
        print(f"   - Jour OK: {gating.get('day_ok', 'N/A')} ({gating.get('qc_reason', 'N/A')})")
        print(f"   - Gates Elite OK: {gating.get('elite_gates_ok', 'N/A')}")
        print(f"   - Signal: {signal_state}")
        print(f"   - Mode: {go_live_mode}  (NO / SCOUT / FULL)")
        
        # Elite Synthesis
        elite = robust_result.get("elite_synthesis", {})
        if elite:
            print(f"\n🧠 Elite Synthesis:")
            print(f"   - Composite Score: {elite.get('composite_score', 0.0):.3f}")
            print(f"   - Confidence: {elite.get('confidence', 0.0):.3f}")
            
            # Component Scores
            scores = elite.get("component_scores", {})
            print(f"   - MenthorQ Elite: {scores.get('menthorq_elite', 0.0):.3f}")
            print(f"   - Battle Navale Elite: {scores.get('battle_navale_elite', 0.0):.3f}")
            print(f"   - OrderFlow Advanced: {scores.get('orderflow_advanced', 0.0):.3f}")
            print(f"   - DOM Health: {scores.get('dom_health', 0.0):.3f}")
            
            # Gates Status
            gates = elite.get("gates_status", {})
            print(f"\n🚪 Gates Status:")
            for gate_name, gate_ok in gates.items():
                status = "✅" if gate_ok else "❌"
                print(f"   - {gate_name}: {status}")
            
            # Risk Bracket
            risk_bracket = elite.get("risk_bracket")
            if risk_bracket:
                print(f"\n🎯 Risk Bracket:")
                print(f"   - Mode: {risk_bracket.get('mode', 'N/A')}")
                print(f"   - Symbol: {risk_bracket.get('symbol', 'N/A')}")
                print(f"   - Contracts: {risk_bracket.get('contracts', 0)}")
                print(f"   - Stop: {risk_bracket.get('stop_ticks', 0)} ticks")
                print(f"   - TP: {risk_bracket.get('tp_ticks', 0)} ticks")
                print(f"   - Risk: ${risk_bracket.get('risk_usd', 0)}")
                print(f"   - Size Hint: {risk_bracket.get('size_hint', 'N/A')}")
            else:
                print(f"\n🎯 Risk Bracket: Pas de signal")
        else:
            print(f"\n🧠 Elite Synthesis: Non disponible")
        
        # Message
        print(f"\n💬 Message: {robust_result.get('message', 'N/A')}")
        
        # Performance
        print(f"\n⏱️ Performance: {robust_result.get('processing_time_ms', 0.0):.1f}ms")
    
    def _display_stats(self):
        """Afficher les statistiques"""
        print("\n📈 STATISTIQUES")
        print("-" * 20)
        
        # Stats du unifier robuste
        robust_stats = self.robust_unifier.get_stats()
        print(f"🛡️ Robust Unifier:")
        print(f"   - Elite Unifier: {len(robust_stats.get('elite_unifier', {}))} composants")
        print(f"   - Decision Messenger: {robust_stats.get('decision_messenger', {}).get('messages_sent', 0)} messages")
        print(f"   - Tick Table: {len(robust_stats.get('tick_table', {}))} symboles")
        
        # Stats de l'adapter
        adapter_stats = self.legacy_adapter.get_mapping_stats()
        print(f"\n🔄 Legacy Adapter:")
        print(f"   - Mappings totaux: {adapter_stats['total_mappings']}")
        print(f"   - Succès: {adapter_stats['successful_mappings']}")
        print(f"   - Fallback: {adapter_stats['fallback_used']}")
        print(f"   - Taux de réussite: {adapter_stats['success_rate_percent']:.1f}%")

def main():
    """Fonction principale"""
    print("🚀 EXEMPLE D'INTÉGRATION - UNIFIER ROBUSTE")
    print("=" * 60)
    
    # Configuration
    config = {
        "verbose": True,
        "save_history": False,  # Pas de sauvegarde pour l'exemple
        "cooldown_seconds": 0,
        "send_messages": True
    }
    
    # Créer et exécuter l'exemple
    example = IntegrationExample(config)
    example.run_integration_example(chart=3)
    
    print("\n🎉 Exemple terminé avec succès !")
    print("💡 Utilisez ce code comme base pour votre intégration")

if __name__ == "__main__":
    main()
