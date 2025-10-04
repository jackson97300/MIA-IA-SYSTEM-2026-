#!/usr/bin/env python3
"""
UNIFIER ELITE - Intégration des nouvelles méthodes Elite
========================================================

Unifier spécialisé pour intégrer les méthodes Elite :
- MenthorQ Elite
- Battle Navale Elite  
- Kernel Smooth
- OrderFlow Advanced
- DOM Health Analyzer

Version: 1.0.0
Date: Janvier 2025
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports des méthodes Elite
try:
    from core.logger import get_logger
    from core.menthorq_elite import MenthorQElite, MenthorQEliteResult
    from core.battle_navale_elite import BattleNavaleElite, BattleNavaleEliteResult
    from features.kernel_smooth import proximity_kernel, LAMBDA_CONFIG, TICK_SIZE_CONFIG
    from features.orderflow_advanced import OrderFlowAdvanced
    from features.dom_health_analyzer import DOMHealthAnalyzer
    from core.risk_sizing_engine import RiskSizingEngine
    ELITE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Modules Elite non disponibles: {e}")
    ELITE_MODULES_AVAILABLE = False

# Logger
logger = get_logger(__name__)

# Import du build_ctx existant
from unifier.build_ctx import build_ctx

class EliteUnifier:
    """
    Unifier spécialisé pour les méthodes Elite
    
    Fonctionnalités :
    - Intégration MenthorQ Elite
    - Intégration Battle Navale Elite
    - Kernel Smoothing avancé
    - OrderFlow Advanced
    - DOM Health Analysis
    """
    
    _ready = False
    
    def __init__(self):
        """Initialisation de l'Elite Unifier"""
        if self._ready:
            return
            
        self.logger = logger
        self.menthorq_elite = MenthorQElite() if ELITE_MODULES_AVAILABLE else None
        self.battle_navale_elite = BattleNavaleElite() if ELITE_MODULES_AVAILABLE else None
        self.orderflow_advanced = OrderFlowAdvanced() if ELITE_MODULES_AVAILABLE else None
        self.dom_health_analyzer = DOMHealthAnalyzer() if ELITE_MODULES_AVAILABLE else None
        self.risk_sizing_engine = RiskSizingEngine() if ELITE_MODULES_AVAILABLE else None
        # Mémoire pour l'hystérésis SCOUT↔GO
        self._last_mode: str = "NO"
        
        print("🚀 Elite Unifier initialisé")
        if ELITE_MODULES_AVAILABLE:
            print("✅ Tous les modules Elite disponibles")
        else:
            print("⚠️ Modules Elite non disponibles - Mode fallback")
            
        self._ready = True
    
    def unify_with_elite_methods(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unifie les données avec les méthodes Elite
        
        Args:
            snapshot: Données brutes du snapshot
            
        Returns:
            Dict unifié avec les résultats des méthodes Elite
        """
        # Construire le contexte de base
        base_ctx = build_ctx(snapshot)
        
        if not ELITE_MODULES_AVAILABLE:
            # Mode fallback - retourner le contexte de base
            base_ctx["elite_methods"]["available"] = False
            base_ctx["elite_methods"]["error"] = "Modules Elite non disponibles"
            return base_ctx
        
        try:
            self.logger.info(f"🚀 EliteUnifier: Début unification avec snapshot {snapshot.get('sym', 'UNKNOWN')} @ {snapshot.get('last', 0.0)}")
            
            # === MENTHORQ ELITE ===
            self.logger.info(f"🧠 EliteUnifier: Traitement MenthorQ Elite...")
            menthorq_result = self._process_menthorq_elite(base_ctx, snapshot)
            base_ctx["menthorq_elite"] = menthorq_result
            self.logger.info(f"🧠 EliteUnifier: MenthorQ Elite terminé - score={menthorq_result.get('score', 0.0)}")
            
            # === BATTLE NAVALE ELITE ===
            self.logger.info(f"⚔️ EliteUnifier: Traitement Battle Navale Elite...")
            battle_navale_result = self._process_battle_navale_elite(base_ctx, snapshot)
            base_ctx["battle_navale_elite"] = battle_navale_result
            self.logger.info(f"⚔️ EliteUnifier: Battle Navale Elite terminé - score={battle_navale_result.get('score', 0.0)}")
            
            # === ORDERFLOW ADVANCED ===
            orderflow_result = self._process_orderflow_advanced(base_ctx, snapshot)
            base_ctx["orderflow_advanced"] = orderflow_result
            
            # === DOM HEALTH ===
            dom_health_result = self._process_dom_health(base_ctx, snapshot)
            base_ctx["dom_health"] = dom_health_result
            
            # === SYNTHÈSE ELITE ===
            elite_synthesis = self._synthesize_elite_results(
                menthorq_result, battle_navale_result, orderflow_result, dom_health_result, base_ctx
            )
            
            # Ajouter le symbole à elite_synthesis
            elite_synthesis["symbol"] = base_ctx.get("sym", "ES")
            base_ctx["elite_synthesis"] = elite_synthesis
            
            base_ctx["elite_methods"]["available"] = True
            base_ctx["elite_methods"]["processed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"❌ Erreur traitement Elite: {e}")
            base_ctx["elite_methods"]["available"] = False
            base_ctx["elite_methods"]["error"] = str(e)
        
        return base_ctx
    
    def _process_menthorq_elite(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite MenthorQ Elite"""
        try:
            # ✅ Utiliser le payload correctement formaté avec les vraies données JSONL
            from unifier.legacy_adapter import LegacyAdapter
            adapter = LegacyAdapter()
            
            # Vérifier si on a des données JSONL MenthorQ
            has_jsonl_data = any(k.startswith("gex_") or k in ["hvl", "hvl_0dte", "call_resistance", "call_resistance_0dte", "put_support", "put_support_0dte"] for k in snapshot.keys())
            
            if has_jsonl_data:
                # ✅ Utiliser build_menthorq_payload avec les vraies données JSONL
                current_price = ctx.get('current_price', 0.0)
                menthorq_data = adapter.build_menthorq_payload(snapshot, current_price)
                self.logger.info(f"🎯 MenthorQ Elite: Utilisation des données JSONL réelles - gamma_max={menthorq_data['gamma']['gamma_max']}")
            else:
                # ✅ Fallback vers l'ancien mapping
                menthorq_data = adapter.to_menthorq_payload(snapshot)
                self.logger.info(f"🎯 MenthorQ Elite: Utilisation du mapping legacy")
            
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
                "components": {
                    "gamma_levels": result.gamma_levels,
                    "blind_spots": result.blind_spots,
                    "dealers_bias": result.dealers_bias,
                    "vwap_confluence": result.vwap_confluence,
                    "vix_regime": result.vix_regime
                }
            }
        except Exception as e:
            return {"error": str(e), "score": 0.0}
    
    def _process_battle_navale_elite(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite Battle Navale Elite"""
        try:
            # Construire les données DOM
            dom_data = {
                'best_bid': snapshot.get('best_bid', 0),
                'best_ask': snapshot.get('best_ask', 0),
                'l1_bbo_ratio': snapshot.get('l1_bbo_ratio', 1.0),
                'l1_bbo_ratio_rolling': snapshot.get('l1_bbo_ratio_rolling', 1.0),
                'depth_levels': snapshot.get('depth_levels', 10)
            }
            
            # Debug DOM data
            self.logger.info(f"🔍 [DEBUG] BN DOM: bid={dom_data['best_bid']}, ask={dom_data['best_ask']}, l1={dom_data['l1_bbo_ratio']}")
            
            # Construire les données OrderFlow
            orderflow_data = {
                'current': snapshot.get('trade_summary_current', {}),
                'history': snapshot.get('trade_summary_history', []),
                'intended_direction': 1  # Par défaut LONG
            }
            
            # Construire les données Structure
            # ✅ CORRECTION: Récupérer VWAP depuis plusieurs sources (session > day > MQ payload > fallback)
            vwap_value = 0.0
            vwap_source = "none"
            
            # 1) Essayer VWAP session depuis micro
            vwap_value = ctx.get('micro', {}).get('vwap', {}).get('vwap', 0.0)
            if vwap_value > 0:
                vwap_source = "session"
            else:
                # 2) Essayer VWAP day depuis micro
                vwap_value = ctx.get('micro', {}).get('vwap', {}).get('vwap_day', 0.0)
                if vwap_value > 0:
                    vwap_source = "day"
                else:
                    # 3) Essayer VWAP depuis snapshot direct
                    vwap_value = snapshot.get('vwap', 0.0)
                    if vwap_value > 0:
                        vwap_source = "snapshot"
                    else:
                        # 4) Fallback: utiliser le VWAP du payload MenthorQ
                        try:
                            adapter = LegacyAdapter()
                            current_price = ctx.get('current_price', 0.0)
                            mq_payload = adapter.build_menthorq_payload(snapshot, current_price)
                            vwap_value = mq_payload.get('vwap', {}).get('vwap', 0.0)
                            if vwap_value > 0:
                                vwap_source = "mq_payload"
                        except Exception:
                            vwap_value = 0.0
            
            # === CORRECTIF VWAP + VPOC ÉCHELLE NQ ===
            # VWAP fallback si session_vwap=0
            session_vwap = vwap_value
            if not session_vwap or session_vwap <= 0:
                # MODE DEV: Fallback temporaire pour tester
                session_vwap = ctx.get('current_price', 0.0)
                vwap_source = "fallback_dev"
                self.logger.warning(f"⚠️ BN: VWAP {vwap_source} → fallback prix actuel: {session_vwap} (mode dev)")
            else:
                self.logger.info(f"✅ BN: VWAP {vwap_source}: {session_vwap}")
            
            # VPOC: corriger l'échelle NQ (pas de mélange ES/NQ)
            vpoc_raw = ctx.get('micro', {}).get('vp', {}).get('vpoc', 0.0)
            symbol = ctx.get('sym', 'ES')
            if symbol.startswith('NQ') and vpoc_raw > 0 and vpoc_raw < 10000:
                # VPOC semble être en échelle ES → convertir approximativement
                vpoc_corrected = vpoc_raw * 3.8  # Ratio approximatif NQ/ES
                self.logger.warning(f"⚠️ BN: VPOC échelle ES détectée {vpoc_raw} → corrigé {vpoc_corrected}")
                vpoc_final = vpoc_corrected
            else:
                vpoc_final = vpoc_raw
            
            structure_data = {
                'price': ctx.get('current_price', 0.0),
                'vwap': session_vwap,
                'vpoc': vpoc_final,
                'val': ctx.get('micro', {}).get('vp', {}).get('val', 0.0),
                'vah': ctx.get('micro', {}).get('vp', {}).get('vah', 0.0),
                'menthorq_levels': snapshot.get('menthorq_levels', []),
                'symbol': symbol,
                'vwap_qc_p95': ctx.get('qc_context', {}).get('vwap_qc_p95', 0.0)
            }
            
            # Debug Structure data
            self.logger.info(f"🔍 [DEBUG] BN Structure: price={structure_data['price']}, vwap={structure_data['vwap']}, vpoc={structure_data['vpoc']}")
            
            # Construire les données Patterns
            patterns_data = snapshot.get('sierra_patterns', {})
            
            # Construire les données Microstructure
            micro_data = {
                'iceberg_confirmed': snapshot.get('iceberg_confirmed', False),
                'large_prints': snapshot.get('large_prints', [])
            }
            
            # Données ATR
            atr_data = {
                'current_atr': ctx.get('qc_context', {}).get('atr_per_bar', 1.0),
                'atr_median_20d': ctx.get('qc_context', {}).get('atr_relative', 1.0)
            }
            
            vix_level = ctx.get('macro', {}).get('vix', 20.0)
            symbol = ctx.get('sym', 'ES')
            
            result = self.battle_navale_elite.calculate_battle_navale_elite(
                dom_data=dom_data,
                orderflow_data=orderflow_data,
                structure_data=structure_data,
                patterns_data=patterns_data,
                micro_data=micro_data,
                symbol=symbol,
                vix_level=vix_level,
                atr_data=atr_data
            )
            
            # Debug result
            self.logger.info(f"🔍 [DEBUG] BN Result: score={result.bn_score}, gates_ok={result.gates_ok}, blocked_by={result.blocked_by}")
            
            return {
                "score": result.bn_score,
                "gates_ok": result.gates_ok,
                "gates_detail": result.gates_detail,
                "blocked_by": result.blocked_by,
                "components": result.components,
                "regime": result.regime,
                "tolerance": result.tolerance,
                "calculation_time_ms": result.calculation_time_ms
            }
        except Exception as e:
            return {"error": str(e), "score": 0.0, "gates_ok": False}
    
    def _process_orderflow_advanced(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite OrderFlow Advanced"""
        try:
            trade_summary_data = snapshot.get('trade_summary_current', {})
            trade_summary_history = snapshot.get('trade_summary_history', [])
            symbol = ctx.get('sym', 'ES')
            # Déduire une direction intelligente depuis MQ, puis surcharger avec OF si signal fort (fallback LONG)
            intended_direction = 1
            try:
                current_price = snapshot.get('last') or snapshot.get('current_price')
                adapter = LegacyAdapter()
                mq_payload = adapter.build_menthorq_payload(snapshot, current_price)
                gamma = (mq_payload or {}).get('gamma', {})
                vwap = (mq_payload or {}).get('vwap', {})
                zero_gamma = gamma.get('zero_gamma') or gamma.get('flip_price') or 0.0
                call_wall = gamma.get('call_wall', 0.0)
                put_wall = gamma.get('put_wall', 0.0)
                vwap_level = vwap.get('vwap', 0.0)
                if current_price and vwap_level and abs(current_price - vwap_level) <= 6.0:
                    intended_direction = 1
                elif call_wall and current_price and current_price > call_wall:
                    intended_direction = -1
                elif zero_gamma and current_price:
                    intended_direction = 1 if current_price > zero_gamma else -1
                else:
                    intended_direction = 1
                # Surcharge via signal OF si fort: imbalance ou pente delta marquée
                buy_vol = float(trade_summary_data.get('buy_vol', 0) or 0)
                sell_vol = float(trade_summary_data.get('sell_vol', 0) or 0)
                imb_total = buy_vol + sell_vol
                if imb_total > 0:
                    imb_mag = abs(buy_vol - sell_vol) / max(imb_total, 1.0)
                    imb_dir = 1 if buy_vol > sell_vol else -1
                else:
                    imb_mag = 0.0
                    imb_dir = 0
                recent = [d.get('cum_delta_session', 0.0) for d in (trade_summary_history[-30:] or [])]
                slope_sign = 0
                if len(recent) >= 5:
                    slope_sign = 1 if (recent[-1] - recent[0]) > 0 else -1 if (recent[-1] - recent[0]) < 0 else 0
                # Si MQ faible ou contradiction, privilégier majorité OF
                mq_score = float(ctx.get('menthorq_elite', {}).get('score', 0.0))
                of_votes = [d for d in [imb_dir, slope_sign] if d != 0]
                if of_votes:
                    majority = 1 if sum(of_votes) >= 0 else -1
                    # Plus permissif : si OrderFlow est clair, le suivre
                    if mq_score < 0.6 or (majority != intended_direction and imb_mag >= 0.015):
                        intended_direction = majority
                self.logger.info(
                    f"🔎 [DEBUG] Intended dir: {intended_direction} | MQ={mq_score:.3f} | imb_mag={imb_mag:.3f} imb_dir={imb_dir} slope_sign={slope_sign} "
                    f"(price={current_price}, ZG={zero_gamma}, CW={call_wall}, VWAP={vwap_level})"
                )
            except Exception:
                intended_direction = 1
            
            # Debug: vérifier les données trade_summary
            self.logger.info(f"🔍 [DEBUG] OrderFlow: trade_summary_current keys: {list(trade_summary_data.keys()) if trade_summary_data else 'EMPTY'}")
            self.logger.info(f"🔍 [DEBUG] OrderFlow: trade_summary_history length: {len(trade_summary_history) if trade_summary_history else 0}")
            
            # Données ATR pour normalisation
            atr_data = {
                'high': snapshot.get('price_highs', []),
                'low': snapshot.get('price_lows', []),
                'close': snapshot.get('price_closes', [])
            }
            self.logger.info(f"🔍 [DEBUG] ATR data in elite_unifier: highs={len(atr_data['high'])}, lows={len(atr_data['low'])}, closes={len(atr_data['close'])}")
            
            result = self.orderflow_advanced.calculate_orderflow_advanced(
                trade_summary_data, trade_summary_history, symbol, intended_direction, atr_data
            )
            
            # Propager ATR ticks réel vers le contexte pour le Risk Engine
            try:
                dm_obj = self.orderflow_advanced._calculate_delta_momentum_true(
                    trade_summary_history, symbol, atr_data
                )
                tick_size_local = TICK_SIZE_CONFIG.get(symbol, 0.25)
                atr_ticks_val = dm_obj.atr_used / max(tick_size_local, 1e-9)
                ctx['atr_ticks'] = atr_ticks_val
            except Exception:
                pass

            return {
                "score": result.of_score if hasattr(result, 'of_score') else 0.0,
                "volume_imbalance": self.orderflow_advanced._calculate_volume_imbalance_directional(
                    trade_summary_data, intended_direction
                ),
                "delta_momentum": dm_obj if 'dm_obj' in locals() else self.orderflow_advanced._calculate_delta_momentum_true(
                    trade_summary_history, symbol, atr_data
                ),
                "atr_ticks": ctx.get('atr_ticks')
            }
        except Exception as e:
            return {"error": str(e), "score": 0.0}
    
    def _finalize_recommendation(self, elite_synthesis: Dict[str, Any]) -> Dict[str, Any]:
        """Filet de sécurité : garantit une recommandation valide et cohérente"""
        try:
            # Extraire les données
            rec = elite_synthesis.get("recommendation")
            scores = elite_synthesis.get("component_scores", {}) or {}
            gates = elite_synthesis.get("gates_status", {}) or {}
            
            mq = float(scores.get("menthorq_elite", 0.0))
            bn = float(scores.get("battle_navale_elite", 0.0))
            ofv = float(scores.get("orderflow_advanced", 0.0))
            dom_ok = bool(gates.get("dom_health_gate_ok", False))
            
            # Si déjà propre, on garde
            if rec in ("GO", "SCOUT_GO", "NO_GO"):
                final_rec = rec
            else:
                # Auto-derive si manquant/invalid → règle SCOUT (règle qui marchait)
                if dom_ok and mq >= 0.40 and 0.30 <= bn < 0.40 and ofv >= 0.20:
                    final_rec = "SCOUT_GO"
                else:
                    # Sinon, on force NO_GO
                    final_rec = "NO_GO"
            
            # Imposer un mode cohérent avec la reco
            REC2MODE = {"GO": "FULL", "SCOUT_GO": "SCOUT", "NO_GO": "NO"}
            final_mode = REC2MODE.get(final_rec, "NO")

            # === HYSTÉRÉSIS SCOUT↔GO ===
            try:
                last_mode = getattr(self, "_last_mode", "NO") or "NO"
                # Promotion SCOUT → GO si marge atteinte
                if last_mode in ("SCOUT", "NO") and dom_ok and (bn >= 0.42 or mq >= 0.47) and ofv >= 0.25:
                    final_rec = "GO"
                    final_mode = "FULL"
                # Rétrogradation GO → SCOUT si faiblesse
                elif last_mode in ("FULL", "SCOUT") and (not dom_ok or bn < 0.36 or mq < 0.40 or ofv < 0.20):
                    if dom_ok and mq >= 0.40 and ofv >= 0.20 and bn >= 0.30:
                        final_rec = "SCOUT_GO"
                        final_mode = "SCOUT"
                    else:
                        final_rec = "NO_GO"
                        final_mode = "NO"
            except Exception:
                pass
            
            # Mettre à jour elite_synthesis
            elite_synthesis["recommendation"] = final_rec
            elite_synthesis["go_live_mode"] = final_mode
            elite_synthesis["is_signal"] = (final_rec == "GO")
            elite_synthesis["position_size_hint"] = "half" if final_rec == "SCOUT_GO" else "flat"
            # Mémoriser pour prochaine itération
            self._last_mode = final_mode
            
            self.logger.info(f"🔒 Recommendation finalisée: {final_rec} → Mode: {final_mode}")
            return elite_synthesis
            
        except Exception as e:
            self.logger.error(f"❌ Erreur finalisation recommendation: {e}")
            # Fallback sécurisé
            elite_synthesis["recommendation"] = "NO_GO"
            elite_synthesis["go_live_mode"] = "NO"
            elite_synthesis["is_signal"] = False
            return elite_synthesis
    
    def _extract_dom_inputs(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les données DOM avec fallback intelligent"""
        # Essayer d'abord au niveau racine, puis sous ofdom
        bb = snapshot.get('best_bid') or snapshot.get('ofdom', {}).get('best_bid', 0)
        ba = snapshot.get('best_ask') or snapshot.get('ofdom', {}).get('best_ask', 0)
        
        # Calculer le spread si pas fourni
        spread = None
        if bb and ba:
            spread = abs(ba - bb)
        else:
            spread = snapshot.get('ofdom', {}).get('spread', 0.25)  # fallback 1 tick ES
        
        l1 = snapshot.get('l1_bbo_ratio') or snapshot.get('ofdom', {}).get('l1_bbo_ratio', 1.0)
        l1_roll = snapshot.get('l1_bbo_ratio_rolling', 1.0)
        depth = snapshot.get('depth_levels') or snapshot.get('ofdom', {}).get('depth_levels', 10)
        
        return {
            'best_bid': bb,
            'best_ask': ba,
            'spread': spread,
            'l1_bbo_ratio': l1,
            'l1_bbo_ratio_rolling': l1_roll,
            'depth_levels': depth
        }

    def _process_dom_health(self, ctx: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Traite DOM Health"""
        try:
            dom_data = self._extract_dom_inputs(snapshot)
            
            # Debug: vérifier les données DOM
            self.logger.info(f"🔍 [DEBUG] DOM: best_bid={dom_data['best_bid']}, best_ask={dom_data['best_ask']}, spread={dom_data['spread']}, l1_roll={dom_data['l1_bbo_ratio_rolling']}")
            
            symbol = ctx.get('sym', 'ES')
            
            result = self.dom_health_analyzer.calculate_dom_health(dom_data, symbol)
            
            return {
                "score": result.dom_health_score if hasattr(result, 'dom_health_score') else 0.0,
                "gate_status": result.gate_status if hasattr(result, 'gate_status') else {"gate": "ERROR", "passed": False},
                "spread_score": result.spread_score if hasattr(result, 'spread_score') else 0.0,
                "l1_bbo_score": result.l1_bbo_score if hasattr(result, 'l1_bbo_score') else 0.0,
                "depth_score": result.depth_score if hasattr(result, 'depth_score') else 0.0
            }
        except Exception as e:
            return {"error": str(e), "score": 0.0}
    
    def _synthesize_elite_results(self, menthorq_result: Dict, battle_navale_result: Dict, 
                                 orderflow_result: Dict, dom_health_result: Dict, ctx: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synthétise les résultats des méthodes Elite"""
        try:
            # Scores de base - gérer les objets et dictionnaires
            mq_score = menthorq_result.get('score', 0.0) if isinstance(menthorq_result, dict) else getattr(menthorq_result, 'score', 0.0)
            bn_score = battle_navale_result.get('score', 0.0) if isinstance(battle_navale_result, dict) else getattr(battle_navale_result, 'score', 0.0)
            of_score = orderflow_result.get('score', 0.0) if isinstance(orderflow_result, dict) else getattr(orderflow_result, 'score', 0.0)
            dom_score = dom_health_result.get('score', 0.0) if isinstance(dom_health_result, dict) else getattr(dom_health_result, 'score', 0.0)
            
            # Vérification des gates - gérer les objets et dictionnaires
            bn_gates_ok = battle_navale_result.get('gates_ok', False) if isinstance(battle_navale_result, dict) else getattr(battle_navale_result, 'gates_ok', False)
            dom_gate_ok = (dom_health_result.get('gate_status', {}).get('gate') == 'OK' if isinstance(dom_health_result, dict) 
                          else getattr(dom_health_result, 'gate_status', {}).get('gate') == 'OK')
            
            # Composite robuste - ne pèse que ce qui est disponible (>0)
            WEIGHTS = {
                "menthorq_elite": 0.60,
                "battle_navale_elite": 0.40,
                "orderflow_advanced": 0.20,
                "dom_health": 0.20,
            }
            
            component_scores = {
                "menthorq_elite": mq_score,
                "battle_navale_elite": bn_score,
                "orderflow_advanced": of_score,
                "dom_health": dom_score
            }
            
            # Calcul composite robuste - seulement les composantes significatives
            MIN_COMPONENT = 0.05  # Seuil minimum pour éviter dilution
            available = {k: v for k, v in component_scores.items() if k in WEIGHTS and v >= MIN_COMPONENT}
            if not available:
                composite_score = 0.0
            else:
                norm = sum(WEIGHTS[k] for k in available)
                composite_score = sum(WEIGHTS[k] * available[k] for k in available) / norm
            
            # === GATES STATUS ===
            gates_status = {
                "battle_navale_gates_ok": bn_gates_ok,
                "dom_health_gate_ok": dom_gate_ok,
                "leadership_gate_ok": battle_navale_result.get('gates_detail', {}).get('leadership_ok', True),  # Ajouter leadership
                "overall_gates_ok": bn_gates_ok and dom_gate_ok
            }
            
            # === RECOMMENDATION FINALE ===
            recommendation = self._recommendation_from_scores(component_scores, gates_status)
            
            # GO LIVE MODE (NO/SCOUT/FULL)
            if recommendation == "GO":
                go_live_mode = "FULL"
            elif recommendation == "SCOUT_GO":
                go_live_mode = "SCOUT"
            else:
                go_live_mode = "NO"
            
            # Signal final
            signal_strength = "STRONG" if composite_score >= 0.8 else "MODERATE" if composite_score >= 0.6 else "WEAK"
            is_signal = (recommendation == "GO")
            
            # Créer elite_synthesis d'abord
            elite_synthesis = {
                "composite_score": composite_score,
                "signal_strength": signal_strength,
                "is_signal": is_signal,
                "component_scores": {
                    "menthorq_elite": mq_score,
                    "battle_navale_elite": bn_score,
                    "orderflow_advanced": of_score,
                    "dom_health": dom_score
                },
                "gates_status": gates_status,
                "recommendation": recommendation,
                "go_live_mode": go_live_mode,  # NO/SCOUT/FULL
                "confidence": min(composite_score * 1.2, 1.0),  # Boost de confiance
                "position_size_hint": "half" if recommendation == "SCOUT_GO" else "flat"
            }
            
            # Risk & Sizing Bracket (après création d'elite_synthesis) - TOUJOURS calculer
            risk_bracket = None
            try:
                atr_ticks = 20.0
                if ctx and 'atr_ticks' in ctx:
                    atr_ticks = ctx['atr_ticks'] or 20.0
                elif ctx and 'atr_data' in ctx:
                    atr_data = ctx.get('atr_data', {})
                    if atr_data and 'atr_used' in atr_data:
                        # Si on a l'ATR en points, convertir en ticks génériques (fallback 0.25)
                        tick_size_tmp = 0.25
                        atr_ticks = atr_data['atr_used'] / max(tick_size_tmp, 1e-9)
                symbol = (ctx.get('sym') if ctx else None) or elite_synthesis.get('symbol', 'ES') or 'ES'
                # Risk Bracket sera calculé APRÈS la finalisation de la recommandation
            except Exception as e:
                self.logger.warning(f"⚠️ Risk Bracket fallback error: {e}")
            
            # === FILET DE SÉCURITÉ : NORMALISER LA RECOMMANDATION ===
            elite_synthesis = self._finalize_recommendation(elite_synthesis)
            
            # Risk & Sizing Bracket (APRÈS finalisation de la recommandation)
            if self.risk_sizing_engine and elite_synthesis.get("go_live_mode") in ("SCOUT", "FULL"):
                try:
                    atr_ticks_for_rb = ctx.get('atr_ticks', 20.0)
                    symbol = ctx.get('sym', 'ES') if ctx else 'ES'
                    risk_bracket = self.risk_sizing_engine.build_risk_bracket(
                        elite_synthesis, symbol, atr_ticks_for_rb
                    )
                    if risk_bracket:
                        if hasattr(risk_bracket, '__dict__'):
                            elite_synthesis["risk_bracket"] = risk_bracket.__dict__
                        else:
                            elite_synthesis["risk_bracket"] = risk_bracket
                    else:
                        elite_synthesis["risk_bracket"] = None
                except Exception as e:
                    self.logger.warning(f"⚠️ Risk Bracket error: {e}")
                    elite_synthesis["risk_bracket"] = None
            else:
                elite_synthesis["risk_bracket"] = None
            
            return elite_synthesis
        except Exception as e:
            return {
                "error": str(e),
                "composite_score": 0.0,
                "is_signal": False,
                "recommendation": "ERROR"
            }
    
    def _recommendation_from_scores(self, comps: dict, gates: dict) -> str:
        """Logique de recommandation basée sur les scores et gates"""
        mq = comps.get('menthorq_elite', 0.0)
        bn = comps.get('battle_navale_elite', 0.0)
        of = comps.get('orderflow_advanced', 0.0)
        dom_ok = gates.get('dom_health_gate_ok', False)
        overall_ok = gates.get('overall_gates_ok', False)

        # === CORRECTIF: JAMAIS DE GO SI overall_gates_ok=False ===
        if not overall_ok:
            self.logger.warning(f"⚠️ Elite: overall_gates_ok=False → FORCE NO_GO (mq={mq:.3f}, bn={bn:.3f}, of={of:.3f})")
            return "NO_GO"

        # GO plein (seulement si overall_gates_ok=True)
        if dom_ok and mq >= 0.50 and bn >= 0.40 and of >= 0.25:
            return "GO"

        # SCOUT_GO (seulement si overall_gates_ok=True)
        if dom_ok and mq >= 0.40 and 0.30 <= bn < 0.40 and of >= 0.20:
            return "SCOUT_GO"

        return "NO_GO"

def create_elite_unifier() -> EliteUnifier:
    """Factory function pour créer un Elite Unifier"""
    return EliteUnifier()

# Fonction de compatibilité avec l'ancien système
def unify_with_elite_methods(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fonction de compatibilité pour unifier avec les méthodes Elite
    
    Args:
        snapshot: Données brutes du snapshot
        
    Returns:
        Dict unifié avec les résultats des méthodes Elite
    """
    unifier = create_elite_unifier()
    return unifier.unify_with_elite_methods(snapshot)

if __name__ == "__main__":
    # Test de l'Elite Unifier
    print("🧪 Test Elite Unifier...")
    
    # Données de test
    test_snapshot = {
        "sym": "ESZ25_FUT_CME",
        "t": 1640995200.0,
        "last": 4150.25,
        "phase": "RTH",
        "regime": "NORMAL",
        "vix": 18.5,
        "vix_trend": "STABLE",
        "mentorq_gamma": {
            "gamma_max": 4150.0,
            "call_wall": 4155.0,
            "put_wall": 4145.0
        },
        "mentorq_swing": {"avail": True},
        "mentorq_blind": {
            "blind_spot_1": 4152.0
        },
        "scanner": {"recent": {}},
        "qscore": 4,
        "vwap": {"vwap": 4150.0},
        "vp": {
            "vpoc": 4150.0,
            "val": 4145.0,
            "vah": 4155.0
        },
        "ofdom": {
            "best_bid": 4150.0,
            "best_ask": 4150.25
        },
        "lead": {"nq_stronger_than_es": True, "sync_ok": True},
        "cluster": {"signals": {}},
        "mia_score": 0.75,
        "mia_state": "BULLISH",
        "prev_state": "NEUTRE"
    }
    
    unifier = create_elite_unifier()
    result = unifier.unify_with_elite_methods(test_snapshot)
    
    print("✅ Test Elite Unifier terminé")
    print(f"📊 Résultat: {json.dumps(result.get('elite_synthesis', {}), indent=2)}")
