"""
ML 3-Layer Strategy - VERSION COMPLÈTE ET ROBUSTE
Stratégie utilisant le système ML 3-Layer avec Bible MenthorQ v2.0

Version: 2.1 (Complète avec SL/TP optimisés)
Date: 12 Novembre 2025
Auteur: MIA_IA_SYSTEM
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ML3LayerStrategy:
    """
    Stratégie ML 3-Layer avec Bible MenthorQ v2.0 - VERSION COMPLÈTE

    Cette stratégie utilise le ML3LayerIntegratedSystem qui intègre:
    - Layer 1 (MenthorQ 50%): Niveaux options (GEX, Gamma, HVL, Blind Spots, 0DTE)
    - Layer 2 (OrderFlow 30%): Validation flux (BID/ASK, Delta, Volume)
    - Layer 3 (Context 20%): Filtre contexte (VWAP, Value Area, Spread)

    Features:
    - ✅ Stop Loss / Take Profit optimisés (basés sur analyse losing trades)
    - ✅ TP1 utilise call_resistance/put_support (MenthorQ levels)
    - ✅ TP2 utilise GEX levels ou 5x ATR
    - ✅ Métadonnées enrichies (9 champs)
    - ✅ Validation multi-niveaux (5 checks)
    - ✅ Génération de signal dict conforme aux standards
    """

    def __init__(self, ml_3layer_system=None):
        """
        Initialize ML 3-Layer Strategy

        Args:
            ml_3layer_system: Instance de ML3LayerIntegratedSystem (injecté)
        """
        self.ml_3layer_system = ml_3layer_system
        self.name = "ml_3layer_strategy"
        self.display_name = "ML 3-Layer Strategy (Bible MenthorQ v2.0)"

        # ═══════════════════════════════════════════════════════════════
        # ✅ CONFIGURATION OPTIMALE 15/11/2025 - VALIDÉE PAR 485 COMBINAISONS
        # ES: TP 16t / SL 12t (R:R 1.33:1) → +0.397 t/trade
        # NQ: TP 23t / SL 12t (R:R 1.92:1) → +1.528 t/trade
        # ═══════════════════════════════════════════════════════════════

        # MODE TEST: TP/SL FIXES pour 1 semaine (désactiver ATR adaptatif)
        self.use_fixed_tp_sl = True  # À passer à False pour revenir à ATR adaptatif

        # Configuration OPTIMALE (backtest exhaustif sur 7,949 trades)
        # ✅ CORRECTION P0: SL ES augmenté de 12 à 18 ticks pour améliorer win rate (33.3% → objectif 45-50%)
        self.sl_optimal_ticks = {
            'ES': 30,   # ✅ AUGMENTÉ 20/11: 18 → 30 (protection stop hunt)
            'NQ': 35,   # ✅ AUGMENTÉ 20/11: 12 → 35 (CRITIQUE!)
            'RTY': 25   # ✅ AUGMENTÉ 20/11: 20 → 25
        }

        # ✅ CORRIGÉ 20/11: TP augmentés pour R:R minimum 1.5:1 (après augmentation SL)
        self.tp_optimal_ticks = {
            'ES': 45,   # ✅ CORRIGÉ 20/11: 20 → 45 (R:R 1.5:1 avec SL 30t, était 0.67:1 ❌)
            'NQ': 53,   # ✅ CORRIGÉ 20/11: 23 → 53 (R:R 1.5:1 avec SL 35t, était 0.66:1 ❌)
            'RTY': 38   # ✅ CORRIGÉ 20/11: 25 → 38 (R:R 1.5:1 avec SL 25t, était 1.0:1 ⚠️)
        }

        # Configuration ORIGINALE (ATR adaptatif) - Backup si use_fixed_tp_sl = False
        self.sl_min_ticks = {
            'ES': 20,   # $50 (augmenté de 12 → 20)
            'NQ': 20,   # $100 (augmenté de 10 → 20)
            'RTY': 15   # $15 (augmenté de 8 → 15)
        }

        self.sl_max_ticks = {
            'ES': 40,   # $100 (max cap)
            'NQ': 48,   # $240 (max cap)
            'RTY': 40   # $40 (max cap)
        }

        self.tp_atr_multiplier = 5.0  # 5x ATR pour TP2 (augmenté de 2-3x)

        # Seuils de confiance (alignés avec ml_3layer_filter.py)
        self.min_total_confidence = 0.50   # 50% global
        self.min_layer1_confidence = 0.15  # 15% Layer 1 (MenthorQ) - Aligné avec ml_3layer_filter.py

        # 📊 STATISTIQUES INTERNES (comme autres stratégies)
        self.stats = {
            'signals_generated': 0,
            'long_signals': 0,
            'short_signals': 0,
            'layer1_rejections': 0,
            'layer2_rejections': 0,
            'layer3_rejections': 0,
            'confidence_rejections': 0,
            'total_evaluations': 0,
            'avg_confidence': 0.0,
            'last_signal_time': None
        }

        if self.ml_3layer_system:
            logger.info(f"✅ {self.display_name} initialisée avec ML 3-Layer System")
            logger.info(f"   🔥 MODE: {'TP/SL FIXES' if self.use_fixed_tp_sl else 'ATR ADAPTATIF'}")
            if self.use_fixed_tp_sl:
                logger.info(f"   TP/SL OPTIMAUX: ES={self.tp_optimal_ticks['ES']}t/{self.sl_optimal_ticks['ES']}t, "
                          f"NQ={self.tp_optimal_ticks['NQ']}t/{self.sl_optimal_ticks['NQ']}t "
                          f"(Config validée 15/11/2025)")
            else:
                logger.info(f"   SL Min: ES={self.sl_min_ticks['ES']}t, NQ={self.sl_min_ticks['NQ']}t, RTY={self.sl_min_ticks['RTY']}t")
                logger.info(f"   TP Multiplier: {self.tp_atr_multiplier}x ATR")
            logger.info(f"   Min Confidence: Total={self.min_total_confidence}, Layer1={self.min_layer1_confidence}")
        else:
            logger.warning(f"⚠️ {self.display_name} initialisée SANS ML 3-Layer System")

    def analyze_from_ml_ready(self, snapshot: Dict, symbol: str = None) -> Optional[Dict]:
        """
        Analyse un snapshot ML_READY et génère un signal (interface standard)

        Args:
            snapshot: Snapshot ML_READY
            symbol: Symbole (ES, NQ, RTY) - Optionnel, peut être extrait du snapshot

        Returns:
            Signal dict ou None si rejeté
        """
        # Extraire symbol du snapshot si non fourni
        if symbol is None:
            symbol = snapshot.get('symbol', 'UNKNOWN')

        return self.generate_signal(snapshot, symbol)

    def generate_signal(self, ml_data: Dict, symbol: str) -> Optional[Dict]:
        """
        Génère un signal dict basé sur ML 3-Layer

        Args:
            ml_data: Snapshot ML_READY
            symbol: Symbole (ES, NQ, RTY)

        Returns:
            Signal dict ou None si rejeté

        Workflow:
            1. Vérifier ML 3-Layer System disponible
            2. Évaluer avec ML 3-Layer (toutes les layers)
            3. Valider confidence >= seuils
            4. Calculer SL/TP optimisés
            5. Générer signal dict conforme
        """
        # Incrémenter compteur d'évaluations
        self.stats['total_evaluations'] += 1

        # 🔍 VALIDATION #0: Snapshot contient les champs requis
        if not self._validate_snapshot(ml_data, symbol):
            return None

        if not self.ml_3layer_system:
            logger.warning(f"[{symbol}] ML 3-Layer System non disponible")
            return None

        try:
            # ═══════════════════════════════════════════════════════════════
            # 1️⃣ ÉVALUATION ML 3-LAYER (3 layers de validation)
            # ═══════════════════════════════════════════════════════════════
            result = self.ml_3layer_system.evaluate_signal(ml_data, symbol)

            # ═══════════════════════════════════════════════════════════════
            # 2️⃣ VALIDATIONS MULTI-NIVEAUX (5 checks)
            # ═══════════════════════════════════════════════════════════════

            # VALIDATION #1: Système a retourné un résultat
            if not result:
                logger.debug(f"[{symbol}] ML 3-Layer: Aucun résultat")
                return None

            # VALIDATION #2: should_trade = True
            if not result.get('should_trade', False):
                rejection = result.get('rejection_reason', 'Unknown')
                logger.debug(f"[{symbol}] ML 3-Layer: Rejeté par système ({rejection})")

                # 📊 Tracker rejections par layer
                if 'Layer 1' in rejection:
                    self.stats['layer1_rejections'] += 1
                elif 'Layer 2' in rejection:
                    self.stats['layer2_rejections'] += 1
                elif 'Layer 3' in rejection:
                    self.stats['layer3_rejections'] += 1

                return None

            # VALIDATION #3: Confidence totale >= 0.50
            total_confidence = result.get('confidence', 0.0)
            if total_confidence < self.min_total_confidence:
                self.stats['confidence_rejections'] += 1
                logger.debug(
                    f"[{symbol}] ML 3-Layer: Confidence insuffisante "
                    f"({total_confidence:.3f} < {self.min_total_confidence})"
                )
                return None

            # VALIDATION #4: Layer 1 (MenthorQ) >= 0.15
            layer1_confidence = result.get('layer1_confidence', 0.0)
            if layer1_confidence < self.min_layer1_confidence:
                logger.debug(
                    f"[{symbol}] ML 3-Layer: Layer 1 insuffisant "
                    f"({layer1_confidence:.3f} < {self.min_layer1_confidence})"
                )
                return None

            # VALIDATION #5: Action valide ("LONG" ou "SHORT")
            action = result.get('action')
            if action not in ['LONG', 'SHORT']:
                logger.warning(f"[{symbol}] ML 3-Layer: Action invalide ({action})")
                return None

            # ═══════════════════════════════════════════════════════════════
            # 3️⃣ CALCUL SL/TP OPTIMISÉS - VERSION HYBRIDE INTELLIGENTE
            # ═══════════════════════════════════════════════════════════════

            # Récupérer données de base
            entry = ml_data.get('mid', ml_data.get('ask', 0))
            atr = ml_data.get('atr', 0)
            vwap = ml_data.get('vwap', entry)

            # Récupérer tick size
            symbol_base = symbol[:2] if len(symbol) >= 2 else 'NQ'
            tick_size = self._get_tick_size(symbol_base)

            # ✅ CORRECTION 23/11/2025: Récupérer SL intelligent depuis Layer 1
            suggested_sl = None
            try:
                decision_obj = result.get('decision')
                if decision_obj and hasattr(decision_obj, 'breakdown'):
                    layer1_result = decision_obj.breakdown.get('layer1')
                    if layer1_result and hasattr(layer1_result, 'suggested_sl'):
                        suggested_sl = layer1_result.suggested_sl
                        logger.debug(f"   ✅ SL suggéré récupéré: {suggested_sl:.2f}")
            except Exception as e:
                logger.warning(f"⚠️ [{symbol_base}] Erreur récupération suggested_sl: {e}")

            # ✅ Utiliser SL intelligent si disponible
            if suggested_sl is not None:
                # Valider et ajuster selon limites min/max
                stop = self._validate_and_adjust_sl(
                    suggested_sl, entry, action, symbol_base, tick_size
                )
                logger.info(f"   ✅ SL INTELLIGENT (confluence): {stop:.2f}")

                # Calculer TP avec R:R adaptatif + niveaux techniques
                tp1 = self._calculate_tp_from_sl_with_rr(
                    entry, stop, action, tick_size, symbol_base, ml_data
                )
                tp2 = tp1  # TP unique (identique)
            else:
                # Fallback: méthode actuelle si pas de confluence détectée
                logger.info(f"   ℹ️ [{symbol_base}] Pas de SL confluence, fallback méthode actuelle")
            stop = self._calculate_optimized_stop(
                entry, action, atr, tick_size, symbol_base, ml_data
            )
            tp1, tp2 = self._calculate_optimized_targets(
                entry, action, atr, vwap, tick_size, symbol_base, ml_data
            )

            # ═══════════════════════════════════════════════════════════════
            # 4️⃣ GÉNÉRATION SIGNAL DICT CONFORME
            # ═══════════════════════════════════════════════════════════════

            # Calculer sl_ticks et tp_atr_mult pour metadata
            sl_distance_pts = abs(entry - stop)
            sl_ticks = int(sl_distance_pts / tick_size)

            # Context Flags et Scenario (Bible MenthorQ v2.0)
            context_flags = self._build_context_flags(ml_data, result)
            scenario = self._identify_scenario(result, ml_data)

            # Créer signal dict conforme
            signal = {
                'strategy': self.name,
                'action': action,
                'confidence': total_confidence,
                'entry': entry,
                'stop': stop,
                'targets': [tp1, tp2],
                'size_multiplier': result.get('size_multiplier', 1.0),
                    'layer1_confidence': layer1_confidence,
                    'layer2_confidence': result.get('layer2_confidence', 0.0),
                    'layer3_confidence': result.get('layer3_confidence', 0.0),
                'market_context': result.get('market_context'),
                'hard_rules_result': result.get('hard_rules_result'),
                'context_flags': context_flags,
                'scenario': scenario,
                'metadata': {
                    'source': 'ML_3LAYER_GENERATOR',
                    'bible_menthorq': 'v2.0',
                    'sl_ticks': sl_ticks,
                    'tp_atr_mult': self.tp_atr_multiplier,
                    'menthorq_scenario': result.get('menthorq_scenario', 'UNKNOWN'),
                    'layer1_reasons': result.get('layer1_reasons', []),
                    'timestamp': datetime.now().isoformat(),
                    # ✅ CORRECTION 23/11/2025: Tracking SL/TP intelligents
                    'using_smart_sl': suggested_sl is not None,
                    'sl_source': 'CONFLUENCE' if (suggested_sl is not None) else 'FIXED',
                    'tp_method': 'HYBRID_RR_TECHNICAL',
                    'rr_target': {'ES': 1.5, 'NQ': 1.8, 'RTY': 2.0}.get(symbol_base, 1.5)
                }
            }

            # Logs détaillés pour debug
            logger.info(
                f"✅ [{symbol}] {self.display_name} → {action} @ {entry:.2f} "
                f"(conf={total_confidence:.2f}, "
                f"L1={layer1_confidence:.2f}, "
                f"L2={result.get('layer2_confidence', 0.0):.2f}, "
                f"L3={result.get('layer3_confidence', 0.0):.2f})"
            )

            logger.info(
                f"   SL={stop:.2f} ({sl_ticks}t), "
                f"TP1={tp1:.2f}, TP2={tp2:.2f}"
            )

            logger.info(
                f"   Scenario: {scenario}, "
                f"Size Mult: {result.get('size_multiplier', 1.0):.2f}"
            )

            # 📊 UPDATE STATS (comme autres stratégies)
            self.stats['signals_generated'] += 1
            if action == "LONG":
                self.stats['long_signals'] += 1
            else:
                self.stats['short_signals'] += 1

            # Update average confidence
            total_signals = self.stats['signals_generated']
            self.stats['avg_confidence'] = (
                (self.stats['avg_confidence'] * (total_signals - 1) + total_confidence) / total_signals
            )
            self.stats['last_signal_time'] = datetime.now()

            return signal

        except Exception as e:
            logger.error(f"❌ [{symbol}] Erreur ML 3-Layer Strategy: {e}", exc_info=True)
            return None

    def _get_tick_size(self, symbol_base: str) -> float:
        """Retourne la taille du tick selon le symbole"""
        tick_sizes = {
            'ES': 0.25,
            'NQ': 0.25,
            'RTY': 0.10,
            'RT': 0.10  # Alias pour RTY
        }
        return tick_sizes.get(symbol_base, 0.25)

    def _validate_and_adjust_sl(
        self,
        suggested_sl: float,
        entry: float,
        action: str,
        symbol_base: str,
        tick_size: float
    ) -> float:
        """
        Valide et ajuste le SL suggéré selon limites min/max sécurisées

        Limites optimisées (MAX réduit pour sécurité):
            ES: MIN 8t, MAX 40t, Optimal 30t
            NQ: MIN 10t, MAX 50t, Optimal 35t
            RTY: MIN 15t, MAX 60t, Optimal 25t
        """
        sl_distance_ticks = abs(entry - suggested_sl) / tick_size

        SL_LIMITS = {
            'ES': {'min': 8, 'max': 40, 'optimal': 30},
            'NQ': {'min': 10, 'max': 50, 'optimal': 35},
            'RTY': {'min': 15, 'max': 60, 'optimal': 25}
        }

        limits = SL_LIMITS.get(symbol_base, SL_LIMITS['ES'])

        # Vérifier MIN
        if sl_distance_ticks < limits['min']:
            logger.warning(
                f"⚠️ [{symbol_base}] SL trop serré: {sl_distance_ticks:.0f}t < {limits['min']}t MIN"
            )
            logger.warning(f"   → Ajustement au minimum: {limits['min']}t")
            if action == "LONG":
                return entry - (limits['min'] * tick_size)
            else:
                return entry + (limits['min'] * tick_size)

        # Vérifier MAX (CRITIQUE)
        if sl_distance_ticks > limits['max']:
            logger.warning(
                f"⚠️ [{symbol_base}] SL trop large: {sl_distance_ticks:.0f}t > {limits['max']}t MAX"
            )
            logger.warning(f"   → Ajustement SL optimal: {limits['optimal']}t")
            if action == "LONG":
                return entry - (limits['optimal'] * tick_size)
            else:
                return entry + (limits['optimal'] * tick_size)

        # SL dans les limites → OK
        logger.debug(
            f"✅ [{symbol_base}] SL validé: {sl_distance_ticks:.0f}t "
            f"(MIN: {limits['min']}, MAX: {limits['max']})"
        )
        return suggested_sl

    def _calculate_tp_from_sl_with_rr(
        self,
        entry: float,
        stop: float,
        action: str,
        tick_size: float,
        symbol_base: str,
        ml_data: Dict
    ) -> float:
        """
        Calcule TP unique optimisé : R:R ADAPTATIF + niveaux techniques

        Logique optimisée:
            1. R:R adaptatif par symbole (ES: 1.5, NQ: 1.8, RTY: 2.0)
            2. Distance recherche adaptative (2.5× SL au lieu de fixe)
            3. Ordre niveaux techniques priorisé
            4. R:R minimum garanti (1.2:1)
            5. TP unique (pas de TP2)
        """
        # 1. Distance SL
        sl_distance_ticks = abs(entry - stop) / tick_size

        # 2. R:R ADAPTATIF par symbole
        TARGET_RR = {
            'ES': 1.5,   # Conservateur
            'NQ': 1.8,   # Moyennement agressif
            'RTY': 2.0   # Agressif
        }
        target_rr = TARGET_RR.get(symbol_base, 1.5)
        MIN_RR = 1.2  # Garantie minimum

        # 3. TP basé sur R:R
        if action == "LONG":
            tp_rr = entry + (sl_distance_ticks * target_rr * tick_size)
        else:
            tp_rr = entry - (sl_distance_ticks * target_rr * tick_size)

        # 4. Distance max ADAPTATIVE (2.5× SL)
        max_distance_ticks = sl_distance_ticks * 2.5

        logger.debug(
            f"   🎯 TP R:R {target_rr}:1 = {tp_rr:.2f} "
            f"(cherche niveau < {max_distance_ticks:.0f}t)"
        )

        # 5. Chercher niveau technique proche (ORDRE PRIORISÉ)
        tp_technical = None
        tp_source = None

        if ml_data:
            if action == "LONG":
                levels_priority = [
                    ('call_resistance', ml_data.get('call_resistance', 0)),
                    ('next_wall', ml_data.get('next_wall', {}).get('price', 0)
                     if isinstance(ml_data.get('next_wall'), dict) else 0),
                    ('vwap_up1', ml_data.get('vwap_up1', 0)),
                    ('vwap', ml_data.get('vwap', 0))
                ]

                for name, level in levels_priority:
                    if level and level > entry:
                        distance = abs(level - tp_rr) / tick_size
                        if distance < max_distance_ticks:
                            tp_technical = level
                            tp_source = name
                            logger.info(
                                f"   ✅ Niveau technique: {name} @ {level:.2f} "
                                f"(distance: {distance:.1f}t < {max_distance_ticks:.0f}t)"
                            )
                            break
            else:  # SHORT
                levels_priority = [
                    ('put_support', ml_data.get('put_support', 0)),
                    ('next_wall', ml_data.get('next_wall', {}).get('price', 0)
                     if isinstance(ml_data.get('next_wall'), dict) else 0),
                    ('vwap_dn1', ml_data.get('vwap_dn1', 0)),
                    ('vwap', ml_data.get('vwap', 0))
                ]

                for name, level in levels_priority:
                    if level and level < entry:
                        distance = abs(level - tp_rr) / tick_size
                        if distance < max_distance_ticks:
                            tp_technical = level
                            tp_source = name
                            logger.info(
                                f"   ✅ Niveau technique: {name} @ {level:.2f} "
                                f"(distance: {distance:.1f}t < {max_distance_ticks:.0f}t)"
                            )
                            break

        # 6. Choisir TP (technique ou R:R)
        if tp_technical:
            tp1 = tp_technical
            source = f"TECHNICAL_{tp_source}"
        else:
            tp1 = tp_rr
            source = "R:R"
            logger.debug(f"   ℹ️ Pas de niveau technique proche, utilisation TP R:R")

        # 7. Vérifier R:R minimum (1.2:1)
        actual_rr = abs(tp1 - entry) / abs(entry - stop)

        if actual_rr < MIN_RR:
            logger.warning(
                f"⚠️ [{symbol_base}] R:R trop faible: {actual_rr:.2f}:1 < {MIN_RR}:1 MIN"
            )
            logger.warning(f"   → Ajustement TP pour garantir R:R {MIN_RR}:1")
            if action == "LONG":
                tp1 = entry + (sl_distance_ticks * MIN_RR * tick_size)
            else:
                tp1 = entry - (sl_distance_ticks * MIN_RR * tick_size)
            source = "R:R_MIN"
            actual_rr = MIN_RR

        # 8. Log final
        tp_distance_ticks = abs(tp1 - entry) / tick_size

        logger.info(
            f"   🎯 TP FINAL: {tp1:.2f} ({tp_distance_ticks:.0f}t)\n"
            f"      Source: {source}\n"
            f"      R:R: {actual_rr:.2f}:1 (target: {target_rr}:1)\n"
            f"      SL: {sl_distance_ticks:.0f}t → TP: {tp_distance_ticks:.0f}t"
        )

        return tp1

    def _calculate_optimized_stop(
        self,
        entry: float,
        action: str,
        atr: float,
        tick_size: float,
        symbol_base: str,
        ml_data: Dict
    ) -> float:
        """
        Calcule le Stop Loss optimisé

        Logique:
            - MODE FIXE (use_fixed_tp_sl=True): Utilise sl_optimal_ticks
            - MODE ADAPTATIF (use_fixed_tp_sl=False): 1.5x ATR cappé min/max

        Args:
            entry: Prix d'entrée
            action: "LONG" ou "SHORT"
            atr: ATR actuel
            tick_size: Taille du tick
            symbol_base: Symbole (ES, NQ, RTY)
            ml_data: Snapshot ML_READY

        Returns:
            Stop Loss prix
        """
        # ═══════════════════════════════════════════════════════════════
        # ✅ MODE TEST 1 SEMAINE: SL FIXE (vs ATR adaptatif)
        # ═══════════════════════════════════════════════════════════════
        if self.use_fixed_tp_sl:
            # SL FIXE optimisé (validé par backtest exhaustif)
            sl_ticks = self.sl_optimal_ticks.get(symbol_base, 15)
            sl_distance = sl_ticks * tick_size

            # Calculer prix SL
            if action == "LONG":
                stop = entry - sl_distance
            else:  # SHORT
                stop = entry + sl_distance

            logger.debug(
                f"   SL OPTIMAL FIXE: {sl_ticks}t @ {stop:.2f} "
                f"(Config validée 15/11, mode test 1 semaine)"
            )

            return stop

        # ═══════════════════════════════════════════════════════════════
        # LOGIQUE ORIGINALE: SL basé sur ATR (adaptatif)
        # ═══════════════════════════════════════════════════════════════
        # SL basé sur ATR
        sl_distance_pts = atr * 1.5  # 1.5x ATR
        sl_ticks_calculated = int(sl_distance_pts / tick_size)

        # Appliquer min/max
        sl_min = self.sl_min_ticks.get(symbol_base, 20)
        sl_max = self.sl_max_ticks.get(symbol_base, 40)

        sl_ticks = max(sl_min, min(sl_ticks_calculated, sl_max))
        sl_distance = sl_ticks * tick_size

        # Calculer prix SL
        if action == "LONG":
            stop = entry - sl_distance
        else:  # SHORT
            stop = entry + sl_distance

        logger.debug(
            f"   SL Calculé: {sl_ticks_calculated}t (ATR={atr:.2f}) → "
            f"Capped: {sl_ticks}t (min={sl_min}, max={sl_max})"
        )

        return stop

    def _calculate_optimized_targets(
        self,
        entry: float,
        action: str,
        atr: float,
        vwap: float,
        tick_size: float,
        symbol_base: str,
        ml_data: Dict
    ) -> tuple:
        """
        Calcule les Take Profits optimisés (TP1 et TP2)

        Logique:
            - MODE FIXE (use_fixed_tp_sl=True): Utilise tp_optimal_ticks
            - MODE ADAPTATIF (use_fixed_tp_sl=False): MenthorQ Levels + GEX/ATR

        Args:
            entry: Prix d'entrée
            action: "LONG" ou "SHORT"
            atr: ATR actuel
            vwap: VWAP actuel
            tick_size: Taille du tick
            symbol_base: Symbole (ES, NQ, RTY)
            ml_data: Snapshot ML_READY

        Returns:
            (tp1, tp2) tuple
        """
        # ═══════════════════════════════════════════════════════════════
        # ✅ MODE TEST 1 SEMAINE: TP FIXE (vs MenthorQ/GEX adaptatif)
        # ═══════════════════════════════════════════════════════════════
        if self.use_fixed_tp_sl:
            # TP FIXE optimisé (validé par backtest exhaustif)
            tp_ticks = self.tp_optimal_ticks.get(symbol_base, 20)
            tp_distance = tp_ticks * tick_size

            if action == "LONG":
                tp1 = entry + tp_distance
                tp2 = entry + tp_distance  # TP1 = TP2 en mode fixe
            else:  # SHORT
                tp1 = entry - tp_distance
                tp2 = entry - tp_distance

            logger.debug(
                f"   TP OPTIMAL FIXE: {tp_ticks}t @ {tp1:.2f} "
                f"(Config validée 15/11, mode test 1 semaine)"
            )

            return tp1, tp2

        # ═══════════════════════════════════════════════════════════════
        # LOGIQUE ORIGINALE: TP1 MenthorQ Levels + TP2 GEX/ATR
        # ═══════════════════════════════════════════════════════════════
        # TP1: MenthorQ Levels (call_resistance / put_support)
        # ═══════════════════════════════════════════════════════════════

        if action == "LONG":
            # TP1: Call resistance (si disponible et au-dessus)
            call_resistance = ml_data.get('call_resistance')

            if call_resistance and call_resistance > entry:
                tp1 = float(call_resistance)
                logger.debug(f"   TP1: Call resistance @ {tp1:.2f}")
            else:
                # Fallback: VWAP + 2*ATR
                tp1 = float(vwap + (atr * 2.0))
                logger.debug(f"   TP1: VWAP + 2*ATR @ {tp1:.2f} (call_resistance N/A)")

        else:  # SHORT
            # TP1: Put support (si disponible et en-dessous)
            put_support = ml_data.get('put_support')

            if put_support and put_support < entry:
                tp1 = float(put_support)
                logger.debug(f"   TP1: Put support @ {tp1:.2f}")
            else:
                # Fallback: VWAP - 2*ATR
                tp1 = float(vwap - (atr * 2.0))
                logger.debug(f"   TP1: VWAP - 2*ATR @ {tp1:.2f} (put_support N/A)")

        # ═══════════════════════════════════════════════════════════════
        # TP2: GEX Level ou 5x ATR
        # ═══════════════════════════════════════════════════════════════

        # Chercher le meilleur GEX level comme TP2
        tp2_gex = self._find_best_gex_target(ml_data, entry, action, tick_size)

        if tp2_gex:
            tp2 = float(tp2_gex)
            logger.debug(f"   TP2: GEX level @ {tp2:.2f}")
        else:
            # Fallback: 5x ATR
            if action == "LONG":
                tp2 = float(entry + (atr * self.tp_atr_multiplier))
            else:  # SHORT
                tp2 = float(entry - (atr * self.tp_atr_multiplier))

            logger.debug(f"   TP2: {self.tp_atr_multiplier}x ATR @ {tp2:.2f} (pas de GEX proche)")

        return tp1, tp2

    def _find_best_gex_target(
        self,
        ml_data: Dict,
        entry: float,
        action: str,
        tick_size: float,
        max_distance_ticks: int = 100
    ) -> Optional[float]:
        """
        Trouve le meilleur GEX level comme TP2

        Logique:
            - LONG: Chercher GEX au-dessus de entry (< 100 ticks)
            - SHORT: Chercher GEX en-dessous de entry (< 100 ticks)
            - Retourner le plus proche si disponible

        Args:
            ml_data: Snapshot ML_READY
            entry: Prix d'entrée
            action: "LONG" ou "SHORT"
            tick_size: Taille du tick
            max_distance_ticks: Distance max pour considérer GEX (100 ticks)

        Returns:
            Prix GEX level ou None si pas trouvé
        """
        # Récupérer tous les GEX levels
        gex_levels = []
        for i in range(1, 11):
            gex = ml_data.get(f'gex_{i}')
            if gex and gex > 0:
                gex_levels.append(gex)

        if not gex_levels:
            return None

        # Filtrer selon direction
        if action == "LONG":
            # GEX au-dessus de entry
            candidates = [gex for gex in gex_levels if gex > entry]
        else:  # SHORT
            # GEX en-dessous de entry
            candidates = [gex for gex in gex_levels if gex < entry]

        if not candidates:
            return None

        # Trouver le plus proche (< 100 ticks)
        distances = [(gex, abs((gex - entry) / tick_size)) for gex in candidates]
        distances.sort(key=lambda x: x[1])

        # Prendre le premier si < 100 ticks
        best_gex, best_dist = distances[0]

        if best_dist < max_distance_ticks:
            logger.debug(f"   GEX Target trouvé: {best_gex:.2f} @ {best_dist:.0f} ticks")
            return best_gex
        else:
            logger.debug(f"   GEX Target trop loin: {best_gex:.2f} @ {best_dist:.0f} ticks (> {max_distance_ticks})")
            return None

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES AUXILIAIRES (comme autres stratégies)
    # ═══════════════════════════════════════════════════════════════

    def _validate_snapshot(self, snapshot: Dict, symbol: str) -> bool:
        """
        Valide que le snapshot contient les champs requis

        📚 Bible MenthorQ v2.0: Exiger données minimales pour Layer 1

        Args:
            snapshot: Snapshot ML_READY
            symbol: Symbole

        Returns:
            True si valide, False sinon
        """
        required_fields = ['mid', 'vwap', 'atr', 'bidPct', 'askPct']

        for field in required_fields:
            if field not in snapshot or snapshot[field] is None:
                logger.error(f"[{symbol}] Champ requis manquant: {field}")
                return False

        return True

    def _build_context_flags(self, ml_data: Dict, result: Dict) -> Dict:
        """
        Construit les context_flags enrichis (Bible MenthorQ v2.0)

        📚 Bible MenthorQ v2.0:
           - HVL Regime (positive/negative gamma)
           - Next Wall (call/put)
           - Blind Spot proximity
           - GEX confluence
           - 0DTE active

        Args:
            ml_data: Snapshot ML_READY
            result: Résultat ML 3-Layer

        Returns:
            Dict de context flags
        """
        context_flags = {}

        # HVL Regime (positive/negative gamma)
        hvl = ml_data.get('hvl', 0)
        mid = ml_data.get('mid', 0)

        if hvl and mid:
            if mid > hvl:
                context_flags['hvl_regime'] = 'positive_gamma'  # Mean-revert
            else:
                context_flags['hvl_regime'] = 'negative_gamma'  # Directionnel
        else:
            context_flags['hvl_regime'] = 'unknown'

        # Next Wall
        next_wall = ml_data.get('next_wall', {})
        if isinstance(next_wall, dict):
            context_flags['next_wall'] = next_wall.get('side', 'unknown')
            context_flags['next_wall_dist'] = next_wall.get('dist_ticks', 999)
            context_flags['next_wall_strength'] = next_wall.get('strength', 0.0)
        else:
            context_flags['next_wall'] = 'unknown'

        # Blind Spot Near
        blind_spot_near = ml_data.get('menthor_distances', {}).get('near_blind', 999)
        context_flags['blind_spot_near'] = (blind_spot_near < 25)

        # GEX Confluence
        near_gex_up = ml_data.get('menthor_distances', {}).get('near_gex_up', 999)
        near_gex_dn = ml_data.get('menthor_distances', {}).get('near_gex_dn', 999)
        context_flags['gex_confluence'] = (min(near_gex_up, near_gex_dn) < 30)

        # 0DTE Active
        gamma_wall_0dte = ml_data.get('gamma_wall_0DTE', 0)
        context_flags['0dte_active'] = (gamma_wall_0dte > 0)

        # Market Context
        context_flags['bias'] = ml_data.get('bias', 'NEUTRAL')
        context_flags['in_value_area'] = ml_data.get('in_value_area', False)

        # 🔧 AJOUT: 1-Day Max/Min (Expected Move) - Bible MenthorQ v2.0
        day_max = ml_data.get('1d_max', 0)
        day_min = ml_data.get('1d_min', 0)
        mid = ml_data.get('mid', 0)

        if day_max and day_min and mid and day_max > day_min:
            day_range = day_max - day_min
            position_pct = ((mid - day_min) / day_range) * 100

            context_flags['1d_position_pct'] = round(position_pct, 1)
            context_flags['near_1d_max'] = (position_pct >= 90)  # Proche du max (≥90%)
            context_flags['near_1d_min'] = (position_pct <= 10)  # Proche du min (≤10%)
            context_flags['1d_range_pct'] = round((day_range / mid) * 100, 2)
        else:
            context_flags['1d_position_pct'] = None
            context_flags['near_1d_max'] = False
            context_flags['near_1d_min'] = False
            context_flags['1d_range_pct'] = None

        return context_flags

    def _identify_scenario(self, result: Dict, ml_data: Dict) -> str:
        """
        Identifie le scenario détaillé du setup (comme autres stratégies)

        📚 Bible MenthorQ v2.0: Scenarios communs
           - GAMMA_WALL_BOUNCE: Rebond sur gamma wall
           - GEX_PULL: Attraction vers GEX level
           - BLIND_SPOT_REACTION: Réaction sur blind spot
           - HVL_FADE: Fade d'exhaustion HVL
           - CONFLUENCE: Multiple niveaux alignés

        Args:
            result: Résultat ML 3-Layer
            ml_data: Snapshot ML_READY

        Returns:
            String du scenario identifié
        """
        menthorq_scenario = result.get('menthorq_scenario', 'UNKNOWN')

        # Si ML 3-Layer a déjà identifié un scenario, l'utiliser
        if menthorq_scenario and menthorq_scenario != 'UNKNOWN':
            return menthorq_scenario

        # Sinon, inférer depuis les données
        next_wall = ml_data.get('next_wall', {})
        if isinstance(next_wall, dict):
            dist_ticks = abs(next_wall.get('dist_ticks', 999))
            if dist_ticks < 20:
                return f"NEXT_WALL_{next_wall.get('side', 'UNKNOWN').upper()}"

        # Vérifier GEX proximity
        near_gex = ml_data.get('menthor_distances', {})
        if near_gex:
            gex_up = near_gex.get('near_gex_up', 999)
            gex_dn = near_gex.get('near_gex_dn', 999)

            if min(gex_up, gex_dn) < 30:
                return "GEX_PULL"

        # Vérifier Blind Spot
        blind_near = ml_data.get('menthor_distances', {}).get('near_blind', 999)
        if blind_near < 25:
            return "BLIND_SPOT_REACTION"

        # Vérifier HVL distance
        hvl_dist = ml_data.get('menthor_distances', {}).get('hvl0', 999)
        if hvl_dist < 50:
            return "HVL_PROXIMITY"

        return "ML_3LAYER_CONFLUENCE"

    def get_stats(self) -> Dict:
        """
        Retourne les statistiques (comme autres stratégies)

        Returns:
            Dict des statistiques
        """
        return self.stats.copy()

    def get_strategy_info(self) -> Dict:
        """
        Retourne les infos de la stratégie pour monitoring

        Returns:
            Dict des infos stratégie
        """
        return {
            'name': self.name,
            'display_name': self.display_name,
            'version': '2.1',
            'bible_menthorq': 'v2.0',
            'ml_3layer_available': self.ml_3layer_system is not None,
            'min_confidence': {
                'total': self.min_total_confidence,
                'layer1': self.min_layer1_confidence
            },
            'sl_tp_config': {
                'sl_min_ticks': self.sl_min_ticks,
                'sl_max_ticks': self.sl_max_ticks,
                'tp_atr_multiplier': self.tp_atr_multiplier
            },
            'stats': self.get_stats()
        }


def create_ml_3layer_strategy(ml_3layer_system=None):
    """
    Factory function pour créer ML3LayerStrategy

    Args:
        ml_3layer_system: Instance de ML3LayerIntegratedSystem (injecté)

    Returns:
        Instance de ML3LayerStrategy
    """
    return ML3LayerStrategy(ml_3layer_system=ml_3layer_system)
