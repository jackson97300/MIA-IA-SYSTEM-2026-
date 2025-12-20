"""
ML 3-Layer Strategy - VERSION COMPLÈTE ET ROBUSTE
Stratégie utilisant le système ML 3-Layer avec Bible MenthorQ v2.0

Version: 2.2 (Ajout filtre pressure_strength par session)
Date: 06 Décembre 2025
Auteur: MIA_IA_SYSTEM
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import pytz

# 🆕 Import du filtre pressure_strength (06/12/2025)
try:
    from config.unified_thresholds import get_min_pressure_strength
    PRESSURE_FILTER_AVAILABLE = True
except ImportError:
    PRESSURE_FILTER_AVAILABLE = False

logger = logging.getLogger(__name__)


class MenthorQ3LayerStrategy:
    """
    Stratégie MenthorQ 3-Layer avec Bible MenthorQ v2.0 - VERSION COMPLÈTE

    ⚠️ IMPORTANT: Cette stratégie utilise des RÈGLES (pas de ML)
    Le système évalue les signaux via scoring pondéré sur 3 couches:
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
        Initialize MenthorQ 3-Layer Strategy

        Args:
            ml_3layer_system: Instance de ML3LayerIntegratedSystem (injecté)
        """
        self.ml_3layer_system = ml_3layer_system
        self.name = "menthorq_3layer_strategy"
        self.display_name = "MenthorQ 3-Layer Strategy (Rules-Based)"

        # ═══════════════════════════════════════════════════════════════
        # ✅ CONFIGURATION OPTIMALE 15/11/2025 - VALIDÉE PAR 485 COMBINAISONS
        # ES: TP 16t / SL 12t (R:R 1.33:1) → +0.397 t/trade
        # NQ: TP 23t / SL 12t (R:R 1.92:1) → +1.528 t/trade
        # ═══════════════════════════════════════════════════════════════

        # MODE PRODUCTION: TP/SL ADAPTATIFS (via adaptive_sltp_calculator)
        self.use_fixed_tp_sl = False  # ✅ 10/12/2025: TOUJOURS en mode adaptatif

        # ✅ CONFIGURATION OPTIMISÉE 10/12/2025 - Alignée avec trading_params.py
        #    ES: SL 15t, TP 15t (R:R 1:1) - Protection capitale
        #    NQ: SL 25t, TP 31t (R:R 1.24:1) - Protection capitale
        self.sl_optimal_ticks = {
            'ES': 15,   # ✅ ALIGNÉ 10/12: Depuis trading_params.py
            'NQ': 25,   # ✅ ALIGNÉ 10/12: Depuis trading_params.py
            'RTY': 30   # Inchangé
        }

        self.tp_optimal_ticks = {
            'ES': 15,   # ✅ ALIGNÉ 10/12: Depuis trading_params.py
            'NQ': 31,   # ✅ ALIGNÉ 10/12: Depuis trading_params.py
            'RTY': 45   # Inchangé
        }

        # ✅ UNIFIÉ 28/11/2025: Configuration distances MenthorQ (remplace 2 configs séparées)
        # Source unique de vérité (était distance_config + max_distance_menthorq_config avec valeurs différentes)
        self.MENTHORQ_DISTANCE_CONFIG = {
            'ES': 8,     # 🔴 10/12/2025: Aligné avec trading_params.py
            'NQ': 10,    # 🔴 10/12/2025: Aligné avec trading_params.py
            'RTY': 12    # 🔴 09/12/2025: 1.2 pts - CONFIG SERRÉE (meilleur R:R)
        }
        logger.info("="*60)
        logger.info("📏 MENTHORQ DISTANCE CONFIG (unifié 28/11):")
        for sym, dist in self.MENTHORQ_DISTANCE_CONFIG.items():
            logger.info(f"   {sym}: {dist}t max")
        logger.info("="*60)

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

        # Seuils de confiance (alignés avec unified_thresholds.py)
        # ⚠️ V10.1 16/12/2025: Synchronisé avec OPTIMAL_SESSION_CONFIGS
        self.min_total_confidence = 0.35   # 🔧 16/12 V10.1: Aligné avec MIN_TOTAL_CONFIDENCE
        self.min_layer1_confidence = 0.20  # 🔧 16/12 V10.1: Aligné avec MIN_LAYER_CONFIDENCE

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
                          f"(Config validée 10/12/2025 - trading_params.py)")
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
        # ✅ CORRIGÉ 19/11: Extraire symbol du snapshot (essayer 'sym' puis 'symbol')
        if symbol is None:
            symbol = snapshot.get('sym', snapshot.get('symbol', 'UNKNOWN'))
            if symbol == 'UNKNOWN':
                logger.warning(f"⚠️ [menthorq_3layer] Symbol UNKNOWN dans snapshot, clés disponibles: {list(snapshot.keys())[:10]}")

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
        # ✅ DEBUG 17/11: Logger l'appel pour ES
        if symbol == 'ES':
            logger.info(f"🔍 [ES DEBUG] menthorq_3layer_strategy.generate_signal() appelé")

        # Incrémenter compteur d'évaluations
        self.stats['total_evaluations'] += 1

        # 🔍 VALIDATION #0: Snapshot contient les champs requis
        if not self._validate_snapshot(ml_data, symbol):
            if symbol == 'ES':
                logger.warning(f"🔍 [ES DEBUG] Snapshot invalide - _validate_snapshot() retourné False")
            return None

        if not self.ml_3layer_system:
            logger.warning(f"[{symbol}] ML 3-Layer System non disponible")
            if symbol == 'ES':
                logger.error(f"🔍 [ES DEBUG] ML 3-Layer System non disponible pour ES!")
            return None

        try:
            # ═══════════════════════════════════════════════════════════════
            # 1️⃣ ÉVALUATION ML 3-LAYER (3 layers de validation)
            # ═══════════════════════════════════════════════════════════════
            logger.info(f"🤖 [ML DEBUG] [{symbol}] Appel ml_3layer_system.evaluate_signal()...")
            logger.info(f"🤖 [ML DEBUG] [{symbol}] ml_data keys: {list(ml_data.keys())[:10]}...")
            logger.info(f"🤖 [ML DEBUG] [{symbol}] price={ml_data.get('price', 0):.2f}")

            result = self.ml_3layer_system.evaluate_signal(ml_data, symbol)

            logger.info(f"🤖 [ML DEBUG] [{symbol}] ML result: {result is not None}")
            if result:
                logger.info(f"🤖 [ML DEBUG] [{symbol}] should_trade={result.get('should_trade')}, confidence={result.get('confidence', 0):.3f}")

            if symbol == 'ES':
                if result:
                    logger.info(f"🔍 [ES DEBUG] ML 3-Layer a retourné un résultat: should_trade={result.get('should_trade', False)}, confidence={result.get('confidence', 0):.3f}")
                else:
                    logger.warning(f"🔍 [ES DEBUG] ML 3-Layer a retourné None - Aucun résultat")

            # ✅ CORRECTION P0 #2: Exiger niveau MenthorQ proche (17/11/2025)
            # Vérifier qu'au moins un niveau critique est proche (<10 ticks)
            closest_level_distance = 999  # Distance par défaut

            # Chercher le niveau le plus proche parmi GEX, Gamma, HVL
            for level_type in ['closest_gex_level', 'closest_gamma_wall', 'closest_hvl']:
                level_data = ml_data.get(level_type)
                if level_data and isinstance(level_data, dict):
                    distance = level_data.get('distance', 999)
                    if distance < closest_level_distance:
                        closest_level_distance = distance
                elif level_data and isinstance(level_data, (int, float)):
                    # Format alternatif: valeur directe (distance en ticks)
                    if level_data < closest_level_distance:
                        closest_level_distance = level_data

            # Vérifier aussi menthor_distances si disponible
            # ✅ CORRECTION: Les distances sont en POINTS, pas en TICKS - convertir!
            menthor_distances = ml_data.get('menthor_distances', {})
            if isinstance(menthor_distances, dict):
                # Récupérer tick_size
                symbol_base = symbol.split('_')[0] if '_' in symbol else symbol[:2]
                tick_size = self._get_tick_size(symbol_base)

                # ✅ CORRECTION 25/11: menthor_distances est DÉJÀ en ticks (pas en points)
                # Ne PAS diviser par tick_size
                for key in ['near_gex_up', 'near_gex_dn', 'hvl0', 'near_blind']:
                    dist_ticks = menthor_distances.get(key, 999)
                    if isinstance(dist_ticks, (int, float)) and abs(dist_ticks) < 10000:  # Filtrer valeurs aberrantes
                        # Déjà en ticks - prendre valeur absolue uniquement
                        dist_ticks_abs = abs(dist_ticks)
                        if dist_ticks_abs < closest_level_distance:
                            closest_level_distance = dist_ticks_abs

                # ✅ CORRECTION: Calculer depuis niveaux réels (plus fiable)
                # Vérifier aussi si niveaux sont à jour (éviter niveaux stales)
                mid = ml_data.get('mid', ml_data.get('microprice', 0))
                if mid > 0:
                    # Vérifier timestamp des niveaux (si disponible)
                    levels_timestamp = ml_data.get('levels_timestamp') or ml_data.get('menthor_meta', {}).get('timestamp')
                    levels_stale = False
                    if levels_timestamp:
                        # Vérifier si niveaux sont récents (< 1 jour)
                        # datetime et timezone déjà importés en haut du fichier
                        try:
                            if isinstance(levels_timestamp, str):
                                # Parser timestamp
                                levels_dt = datetime.fromisoformat(levels_timestamp.replace('Z', '+00:00'))
                            else:
                                levels_dt = datetime.fromtimestamp(levels_timestamp, tz=timezone.utc)
                            age_hours = (datetime.now(timezone.utc) - levels_dt).total_seconds() / 3600
                            if age_hours > 24:
                                levels_stale = True
                                logger.warning(f"⚠️ [{symbol}] Niveaux MenthorQ stales ({age_hours:.1f}h) - risque de distances incorrectes")
                        except:
                            pass

                    # Calculer distances depuis niveaux réels
                    # GEX levels (priorité: gex_9, gex_10 car souvent plus proches)
                    for i in [9, 10, 8, 7, 6, 5, 4, 3, 2, 1]:  # Prioriser gex_9, gex_10
                        gex_key = f'gex_{i}'
                        gex_level = ml_data.get(gex_key)
                        if gex_level and isinstance(gex_level, (int, float)) and gex_level > 0:
                            dist_ticks = abs(gex_level - mid) / tick_size
                            if dist_ticks < closest_level_distance:
                                closest_level_distance = dist_ticks

                    # Blind spots (priorité: blind_spot_0, blind_spot_6 souvent plus proches)
                    for i in [0, 6, 1, 2, 3, 4, 5, 7, 8]:
                        blind_key = f'blind_spot_{i}'
                        blind_level = ml_data.get(blind_key)
                        if blind_level and isinstance(blind_level, (int, float)) and blind_level > 0:
                            dist_ticks = abs(blind_level - mid) / tick_size
                            if dist_ticks < closest_level_distance:
                                closest_level_distance = dist_ticks

                    # HVL, 1d_max (niveaux critiques)
                    for level_key in ['hvl', '1d_max', 'call_resistance', 'put_support']:
                        level = ml_data.get(level_key)
                        if level and isinstance(level, (int, float)) and level > 0:
                            dist_ticks = abs(level - mid) / tick_size
                            if dist_ticks < closest_level_distance:
                                closest_level_distance = dist_ticks

                    # Si niveaux stales et distance > 200 ticks, être plus strict
                    if levels_stale and closest_level_distance > 200:
                        logger.warning(f"⚠️ [{symbol}] Niveaux stales + distance élevée ({closest_level_distance:.1f}t) - rejet par prudence")
                        self.stats['layer1_rejections'] += 1
                        return None

            # Rejeter si aucun niveau proche
            # ✅ CONFIGURATION ASIA: Distance max augmentée pour liquidité faible
            session = ml_data.get('session', ml_data.get('session_id', 'UNKNOWN'))
            session_upper = session.upper() if isinstance(session, str) else 'UNKNOWN'

            # Distance max selon session et symbole
            # ✅ CORRIGÉ 27/11/2025: Distance adaptée par symbole + bypass confluence
            # - ES: 80 ticks ($1,000) - range-bound, besoin de proximité
            # - NQ: 250 ticks ($1,250) - volatil, confluence valide même à distance
            # - RTY: 50 ticks ($250) - petit, besoin de proximité

            # ✅ UNIFIÉ 28/11/2025: Configuration distances MenthorQ (définie dans __init__)
            # Utiliser self.MENTHORQ_DISTANCE_CONFIG au lieu de variable locale

            # Détection confluence forte (3+ niveaux groupés)
            confluence_levels = ml_data.get('confluence_levels', [])
            confluence_detected = len(confluence_levels) >= 3 if isinstance(confluence_levels, list) else False

            # 🔴 FIX 10/12/2025: NE PLUS BYPASS la distance même avec confluence!
            # Le bypass permettait des trades à 31t du niveau (BUG!)
            # Confluence = bonus au score, PAS bypass de la distance
            max_distance = self.MENTHORQ_DISTANCE_CONFIG.get(symbol, 35)

            if confluence_detected:
                # Confluence = bonus de +5 ticks max (pas bypass total!)
                max_distance = max_distance + 5
                logger.info(f"[{symbol}] ✅ Confluence forte ({len(confluence_levels)} niveaux) -> distance +5t = {max_distance}t max")

            # ASIA: réduire distance (liquidité faible)
            if session_upper == 'ASIA' and not confluence_detected:
                max_distance = min(max_distance, 50)  # ⬇️ Cap à 50 ticks pour ASIA (optimisé 02/12/2025)

            if closest_level_distance > max_distance:
                logger.error(
                    f"🔴 [AUDIT] [{symbol}] BLOQUÉ NIVEAU 5: Pas de niveau MenthorQ proche "
                    f"(closest={closest_level_distance:.1f}t > {max_distance}t, session={session_upper})"
                )
                self.stats['layer1_rejections'] += 1
                return None

            # ═══════════════════════════════════════════════════════════════
            # 2️⃣ VALIDATIONS MULTI-NIVEAUX (5 checks)
            # ═══════════════════════════════════════════════════════════════

            # VALIDATION #1: Système a retourné un résultat
            if not result:
                logger.debug(f"[{symbol}] ML 3-Layer: Aucun résultat")
                if symbol == 'ES':
                    logger.warning(f"🔍 [ES DEBUG] REJET: ML 3-Layer a retourné None")
                return None

            # VALIDATION #2: should_trade = True
            if not result.get('should_trade', False):
                rejection = result.get('rejection_reason', 'Unknown')
                logger.error(f"🔴 [AUDIT] [{symbol}] BLOQUÉ NIVEAU 6: ML 3-Layer should_trade=False - {rejection}")

                # 📊 Tracker rejections par layer
                if 'Layer 1' in rejection:
                    self.stats['layer1_rejections'] += 1
                elif 'Layer 2' in rejection:
                    self.stats['layer2_rejections'] += 1
                elif 'Layer 3' in rejection:
                    self.stats['layer3_rejections'] += 1

                return None

            # VALIDATION #3: Confidence totale avec tolérance VWAP override
            total_confidence = result.get('confidence', 0.0)
            layer1_confidence = result.get('layer1_confidence', 0.0)
            layer2_confidence = result.get('layer2_confidence', 0.0)

            # ✅ CORRECTION 20/11/2025: VWAP Override avec tolérance
            # Si VWAP override actif (Layer 1 élevée OU Layer 2 élevée OU total proche seuil)
            # → Réduire le seuil de 0.05 (0.60 → 0.55)
            vwap_override_tolerance = 0.05
            vwap_override_active = False

            # Vérifier si VWAP override est actif
            vwap_favorable = ml_data.get('vwap_favorable', False)
            if not vwap_favorable:
                # VWAP défavorable mais override possible si:
                # 1. Layer 1 confidence élevée (≥ 0.35)
                # 2. Layer 2 confidence élevée (≥ 0.20)
                # 3. Total confidence proche seuil (≥ 0.45)
                if layer1_confidence >= 0.35:
                    vwap_override_active = True
                    logger.info(f"💡 [{symbol}] VWAP override: Layer 1 confidence élevée ({layer1_confidence:.2f})")
                elif layer2_confidence >= 0.20:
                    vwap_override_active = True
                    logger.info(f"💡 [{symbol}] VWAP override: Layer 2 confidence élevée ({layer2_confidence:.2f})")
                elif total_confidence >= 0.45:
                    vwap_override_active = True
                    logger.info(f"💡 [{symbol}] VWAP override: Total confidence proche seuil ({total_confidence:.2f})")

            # Calculer seuil effectif
            if vwap_override_active:
                min_confidence_effective = self.min_total_confidence - vwap_override_tolerance
                logger.info(f"✅ [{symbol}] VWAP override: seuil réduit {self.min_total_confidence:.2f} → {min_confidence_effective:.2f}")
            else:
                min_confidence_effective = self.min_total_confidence

            # Vérifier confidence
            if total_confidence < min_confidence_effective:
                self.stats['confidence_rejections'] += 1
                logger.debug(
                    f"[{symbol}] ML 3-Layer: Confidence insuffisante "
                    f"({total_confidence:.3f} < {min_confidence_effective:.3f})"
                )
                return None

            # VALIDATION #4: Layer 1 (MenthorQ) >= 0.30 (🔥 CRITIQUE: BLOQUER SI = 0.00)
            # Layer 1 représente 50% du score total et doit être significatif
            layer1_confidence = result.get('layer1_confidence', 0.0)

            # ✅ CORRECTION CRITIQUE 27/11: BLOQUER si MenthorQ = 0.00 (aucun niveau valide)
            if layer1_confidence <= 0.0:
                logger.error(
                    f"❌ [{symbol}] REJECT CRITIQUE: MenthorQ score = 0.00 (aucun niveau valide) - TRADE BLOQUÉ"
                )
                self.stats['layer1_rejections'] += 1
                return None

            min_layer1_threshold = self.min_layer1_confidence  # 0.30 minimum
            if layer1_confidence < min_layer1_threshold:
                logger.warning(
                    f"❌ [{symbol}] REJECT: Layer 1 (MenthorQ) trop faible "
                    f"({layer1_confidence:.2f} < {min_layer1_threshold:.2f})"
                )
                self.stats['layer1_rejections'] += 1
                return None

            # ═══════════════════════════════════════════════════════════════
            # 🆕 VALIDATION #4B: PRESSURE_STRENGTH PAR SESSION + SYMBOLE (07/12/2025)
            # ═══════════════════════════════════════════════════════════════
            # Backtest 24 jours: P&L +$3,125 → +$141,375 (+4,424%)
            # 🔥 OPTIMISÉ 07/12: ES utilise seuil 0.20 (plus strict)
            if PRESSURE_FILTER_AVAILABLE:
                pressure_strength = ml_data.get('pressure_strength', 0)
                current_session = self._get_current_session_name()
                min_pressure = get_min_pressure_strength(current_session, symbol)  # 🔥 Ajout symbole

                if pressure_strength < min_pressure:
                    logger.warning(
                        f"🚫 [{symbol}] REJECT: pressure_strength {pressure_strength:.4f} < "
                        f"{min_pressure:.2f} (session {current_session})"
                    )
                    self.stats['pressure_rejections'] = self.stats.get('pressure_rejections', 0) + 1
                    return None
                else:
                    logger.debug(
                        f"✅ [{symbol}] pressure_strength OK: {pressure_strength:.4f} >= "
                        f"{min_pressure:.2f} (session {current_session})"
                    )

            # VALIDATION #5: Action valide ("LONG" ou "SHORT")
            action = result.get('action')
            if action not in ['LONG', 'SHORT']:
                logger.warning(f"[{symbol}] ML 3-Layer: Action invalide ({action})")
                return None

            # ═══════════════════════════════════════════════════════════════
            # VALIDATION #6: VALIDATIONS STRUCTURELLES CATASTROPHIQUES (AVANT ASIA)
            # ═══════════════════════════════════════════════════════════════
            # ⚠️ IMPORTANT: Ces validations sont INDÉPENDANTES des scores
            # Elles doivent être vérifiées AVANT les validations ASIA
            # pour bloquer les trades catastrophiques même si scores OK

            # Créer un signal temporaire pour les validations
            temp_signal = {
                'confluence': total_confidence,
                'confidence': total_confidence,
                'layer1_confidence': layer1_confidence,
                'layer2_confidence': result.get('layer2_confidence', 0.0),
                'layer3_confidence': result.get('layer3_confidence', 0.0)
            }

            # Appeler validations structurelles catastrophiques
            # ✅ NOUVEAU 28/11: Pour l'instant pas de key_level ici (ML data seulement)
            # TODO: Enrichir ml_data avec nearest_level si disponible
            structure_check = self._validate_catastrophic_trade_filters(
                temp_signal, ml_data, symbol, key_level=None
            )
            if structure_check is None:
                logger.error(f"🔴 [AUDIT] [{symbol}] BLOQUÉ NIVEAU 7-8: Signal rejeté par validations structurelles critiques (MenthorQ distance ou 1D MAX)")
                return None

            # ═══════════════════════════════════════════════════════════════
            # VALIDATION #7: SEUILS PAR SESSION (ASIA plus stricts)
            # ═══════════════════════════════════════════════════════════════
            from config.unified_thresholds import VALIDATION_THRESHOLDS

            # Détecter session depuis ml_data
            session = ml_data.get('session', ml_data.get('session_id', 'UNKNOWN'))
            session_upper = session.upper() if isinstance(session, str) else 'UNKNOWN'

            # Récupérer scores individuels
            # Confluence = total_confidence (pondération des 3 layers)
            confluence_score = total_confidence
            layer1_score = layer1_confidence  # MenthorQ (50%)
            layer2_score = result.get('layer2_confidence', 0.0)  # OrderFlow (30%)
            layer3_score = result.get('layer3_confidence', 0.0)  # Context (20%)

            # Si scores individuels absents, utiliser total_confidence comme proxy
            # (certains trades n'ont que confluence, pas les layers séparés)
            if layer2_score == 0.0 and layer3_score == 0.0:
                # Estimer depuis total_confidence si layers absents
                # Layer2 = 30% du total, Layer3 = 20% du total
                layer2_score = total_confidence * 0.30
                layer3_score = total_confidence * 0.20

            # Appliquer seuils selon session
            session_thresholds = None
            session_name = 'UNKNOWN'

            if session_upper == 'ASIA':
                # ✅ CONFIGURATION ASIA SPÉCIFIQUE
                from config.asia_session_config import get_asia_thresholds
                asia_thresholds = get_asia_thresholds()
                session_thresholds = {
                    'confluence': asia_thresholds.get('confluence', 0.65),
                    'orderflow': asia_thresholds.get('orderflow', 0.00),  # Désactivé
                    'context': asia_thresholds.get('context', 0.08),
                    'menthorq': asia_thresholds.get('menthorq', 0.15)  # Nouveau seuil
                }
                session_name = 'ASIA'
            elif session_upper in ['LONDON', 'LONDRES']:
                session_thresholds = VALIDATION_THRESHOLDS.get('london', {})
                session_name = 'LONDON'
            elif session_upper in ['US', 'NY', 'NEW_YORK', 'OPENING_BELL', 'POWER_HOUR']:
                session_thresholds = VALIDATION_THRESHOLDS.get('us', {})
                session_name = 'US'

            # Si seuils spécifiques à la session trouvés, les appliquer
            if session_thresholds:
                min_confluence = session_thresholds.get('confluence', VALIDATION_THRESHOLDS.get('confluence', 0.75))
                min_orderflow = session_thresholds.get('orderflow', VALIDATION_THRESHOLDS.get('orderflow_min', 0.20))
                min_context = session_thresholds.get('context', VALIDATION_THRESHOLDS.get('context_min', 0.15))

                # Validation Confluence par session
                if confluence_score < min_confluence:
                    logger.warning(
                        f"❌ [{symbol}] REJECT {session_name}: Confluence insuffisante "
                        f"({confluence_score:.2f} < {min_confluence:.2f})"
                    )
                    self.stats['confidence_rejections'] += 1
                    return None

                # Validation OrderFlow par session (désactivé pour ASIA si 0.00)
                if min_orderflow > 0.0 and layer2_score < min_orderflow:
                    logger.warning(
                        f"❌ [{symbol}] REJECT {session_name}: OrderFlow insuffisant "
                        f"({layer2_score:.2f} < {min_orderflow:.2f})"
                    )
                    self.stats['layer2_rejections'] += 1
                    return None
                elif session_name == 'ASIA' and min_orderflow == 0.0:
                    logger.debug(f"✅ [{symbol}] ASIA: OrderFlow désactivé (pas fiable)")

                # Validation Context par session
                # ✅ CORRECTION CRITIQUE 27/11: BLOQUER si Context = 0.00 (pas de contexte)
                if layer3_score <= 0.0:
                    logger.error(
                        f"❌ [{symbol}] REJECT CRITIQUE {session_name}: Context score = 0.00 (pas de contexte) - TRADE BLOQUÉ"
                    )
                    self.stats['layer3_rejections'] += 1
                    return None

                if layer3_score < min_context:
                    logger.warning(
                        f"❌ [{symbol}] REJECT {session_name}: Context insuffisant "
                        f"({layer3_score:.2f} < {min_context:.2f})"
                    )
                    self.stats['layer3_rejections'] += 1
                    return None

                # ✅ CORRECTION CRITIQUE 27/11: Validation MenthorQ pour TOUTES les sessions (ASIA, LONDON, US)
                if 'menthorq' in session_thresholds:
                    min_menthorq = session_thresholds.get('menthorq', 0.30)
                    if layer1_score < min_menthorq:
                        logger.warning(
                            f"❌ [{symbol}] REJECT {session_name}: MenthorQ insuffisant "
                            f"({layer1_score:.2f} < {min_menthorq:.2f})"
                        )
                        self.stats['layer1_rejections'] += 1
                        return None

                logger.info(
                    f"✅ [{symbol}] {session_name} thresholds OK: "
                    f"Confluence={confluence_score:.2f} (min={min_confluence:.2f}), "
                    f"OrderFlow={'DÉSACTIVÉ' if min_orderflow == 0.0 else f'{layer2_score:.2f} (min={min_orderflow:.2f})'}, "
                    f"Context={layer3_score:.2f} (min={min_context:.2f}), "
                    f"MenthorQ={layer1_score:.2f} (min={session_thresholds.get('menthorq', 0.30):.2f})"
                )
            else:
                # Seuils par défaut si session non reconnue
                min_menthorq = VALIDATION_THRESHOLDS.get('menthorq_min', 0.50)
                min_orderflow = VALIDATION_THRESHOLDS.get('orderflow_min', 0.20)
                min_context = VALIDATION_THRESHOLDS.get('context_min', 0.15)

                # Validation MenthorQ (seulement si seuil plus strict que layer1_confidence)
                if min_menthorq > self.min_layer1_confidence and layer1_score < min_menthorq:
                    logger.warning(
                        f"❌ [{symbol}] REJECT: MenthorQ insuffisant "
                        f"({layer1_score:.2f} < {min_menthorq:.2f})"
                    )
                    self.stats['layer1_rejections'] += 1
                    return None

                # Validation OrderFlow
                if layer2_score < min_orderflow:
                    logger.warning(
                        f"❌ [{symbol}] REJECT: OrderFlow insuffisant "
                        f"({layer2_score:.2f} < {min_orderflow:.2f})"
                    )
                    self.stats['layer2_rejections'] += 1
                    return None

                # Validation Context
                if layer3_score < min_context:
                    logger.warning(
                        f"❌ [{symbol}] REJECT: Context insuffisant "
                        f"({layer3_score:.2f} < {min_context:.2f})"
                    )
                    self.stats['layer3_rejections'] += 1
                    return None

            # ═══════════════════════════════════════════════════════════════
            # 3️⃣ CALCUL SL/TP ADAPTATIFS (NOUVEAU 02/12/2025)
            # ═══════════════════════════════════════════════════════════════
            # Utilise AdaptiveSLTPCalculator pour placer SL/TP basés sur niveaux MenthorQ
            # - SL: SOUS le support (LONG) ou AU-DESSUS la résistance (SHORT)
            # - TP: Si niveau proche respectant R:R min → utiliser ce niveau, sinon fixe

            # Récupérer données de base
            entry = ml_data.get('mid', ml_data.get('ask', 0))
            atr = ml_data.get('atr', 0)
            vwap = ml_data.get('vwap', entry)

            # Récupérer tick size
            symbol_base = symbol[:2] if len(symbol) >= 2 else 'NQ'
            tick_size = self._get_tick_size(symbol_base)

            # ✅ NOUVEAU: Utiliser AdaptiveSLTPCalculator
            try:
                from core.adaptive_sltp_calculator import get_adaptive_sltp_calculator

                sltp_calc = get_adaptive_sltp_calculator()

                # ✅ VALIDATION DISTANCE D'ENTRÉE (02/12/2025)
                # Setup préféré: Attendre que prix soit PROCHE du niveau (5-10t ES, 3-7t NQ)
                is_distance_valid, distance_reason, suggested_entry = sltp_calc.validate_entry_distance(
                    symbol=symbol_base,
                    direction=action,
                    entry_price=entry,
                    ml_data=ml_data,
                )

                if not is_distance_valid:
                    logger.warning(f"❌ [{symbol}] Trade rejeté: {distance_reason}")
                    if suggested_entry:
                        logger.info(f"   💡 Suggestion: Attendre entry @ {suggested_entry:.2f}")
                    self.stats['distance_rejections'] = self.stats.get('distance_rejections', 0) + 1
                    return None

                # Si distance acceptable mais pas optimale, logger pour analyse
                if "acceptable mais pas optimale" in distance_reason:
                    logger.info(f"   ⚠️ {distance_reason}")
                    if suggested_entry:
                        logger.info(f"   💡 Pour meilleur R:R: {suggested_entry:.2f}")

                # ✅ CALCUL SL/TP ADAPTATIF
                sltp_result = sltp_calc.calculate_adaptive_sltp(
                    symbol=symbol_base,
                    direction=action,
                    entry_price=entry,
                    ml_data=ml_data,
                    session=session_upper,
                )

                # ✅ VÉRIFIER VALIDITÉ (R:R, etc.)
                if not sltp_result.is_valid:
                    logger.warning(f"❌ [{symbol}] Trade rejeté: {sltp_result.rejection_reason}")
                    self.stats['sl_tp_rejections'] = self.stats.get('sl_tp_rejections', 0) + 1
                    return None

                # Utiliser les résultats adaptatifs
                stop = sltp_result.sl_price
                tp1 = sltp_result.tp_price
                tp2 = sltp_result.tp_price  # TP2 = TP1 pour simplifier

                # Log détaillé
                logger.info(f"   📐 SL/TP Adaptatif: SL={stop:.2f} ({sltp_result.sl_based_on}), TP={tp1:.2f} ({sltp_result.tp_based_on})")
                if sltp_result.sl_level_name:
                    logger.info(f"      └─ SL sous {sltp_result.sl_level_name} @ {sltp_result.sl_level_price}")
                if sltp_result.tp_level_name:
                    logger.info(f"      └─ TP vers {sltp_result.tp_level_name} @ {sltp_result.tp_level_price}")
                logger.info(f"      └─ R:R: {sltp_result.rr_ratio:.2f}:1 ✅")

            except Exception as e:
                # Fallback sur ancienne méthode si erreur
                logger.warning(f"   ⚠️ Fallback SL/TP fixe: {e}")
                import traceback
                traceback.print_exc()
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

            # ✅ CONFIGURATION ASIA: Taille réduite de 50%
            size_multiplier_base = result.get('size_multiplier', 1.0)
            if session_upper == 'ASIA':
                from config.asia_session_config import get_asia_risk_adjustments
                asia_risk = get_asia_risk_adjustments()
                asia_size_mult = asia_risk.get('size_multiplier', 0.5)
                size_multiplier = size_multiplier_base * asia_size_mult
                logger.debug(f"✅ [{symbol}] ASIA: Taille réduite {size_multiplier_base:.2f} → {size_multiplier:.2f} (×{asia_size_mult})")
            else:
                size_multiplier = size_multiplier_base

            # Créer signal dict conforme
            signal = {
                'strategy': self.name,
                'symbol': symbol,  # 🔧 FIX 25/11: Pour logs/Discord corrects
                'action': action,
                'confidence': total_confidence,
                'confluence': total_confidence,  # ✅ Ajouté 20/11/2025: Pour validations catastrophiques
                'ml_validated': True,  # 🔧 FIX 25/11: Bypass filtre counter-trend car ML 3-Layer a validé
                'entry': entry,
                'stop': stop,
                'targets': [tp1, tp2],
                'size_multiplier': size_multiplier,
                'layer1_confidence': layer1_confidence,
                'layer2_confidence': result.get('layer2_confidence', 0.0),
                'layer3_confidence': result.get('layer3_confidence', 0.0),
                'market_context': result.get('market_context'),
                'hard_rules_result': result.get('hard_rules_result'),
                'context_flags': context_flags,
                'scenario': scenario,
                # ✅ MÉTADONNÉES ML (16/11/2025)
                'ml_quality_score': result.get('ml_quality_score'),
                'ml_win_probability': result.get('ml_win_probability'),
                'ml_prediction_label': result.get('ml_prediction_label'),
                'metadata': {
                    'source': 'ML_3LAYER_GENERATOR',
                    'bible_menthorq': 'v2.0',
                    'sl_ticks': sl_ticks,
                    'tp_atr_mult': self.tp_atr_multiplier,
                    'menthorq_scenario': result.get('menthorq_scenario', 'UNKNOWN'),
                    'layer1_reasons': result.get('layer1_reasons', []),
                    'timestamp': datetime.now().isoformat()
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

            # ✅ LOGS ML (16/11/2025)
            ml_quality = result.get('ml_quality_score')
            ml_win_proba = result.get('ml_win_probability')
            if ml_quality or ml_win_proba:
                ml_log_parts = []
                if ml_quality:
                    ml_log_parts.append(f"Quality={ml_quality:.1f}/100")
                if ml_win_proba:
                    ml_log_parts.append(f"P(WIN)={ml_win_proba:.1%}")
                logger.info(f"   🧠 ML: {', '.join(ml_log_parts)}")

            # ═══════════════════════════════════════════════════════════════
            # VALIDATION SESSION QUALITY (NOUVEAU! 🔥 DURCI 19/11/2025)
            # ═══════════════════════════════════════════════════════════════
            session_quality = self._calculate_session_quality(
                ml_data,
                symbol,
                result
            )

            from config.unified_thresholds import MIN_SESSION_QUALITY
            # 🔧 BACKTEST 28/11: Désactiver temporairement (pré-filtré par script)
            min_session = 0.0  # ✅ Désactivé (était 0.20) - Le script backtest fait déjà le filtrage

            if session_quality < min_session:
                logger.warning(
                    f"[{symbol}] Signal rejeté: Session quality trop faible "
                    f"({session_quality:.1%} < {min_session:.1%})"
                )
                return None

            logger.info(
                f"[{symbol}] ✅ Session quality acceptable: {session_quality:.1%}"
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

            # ═══════════════════════════════════════════════════════════
            # VALIDATION PROXIMITÉ NIVEAU (CORRIGÉE)
            # ═══════════════════════════════════════════════════════════
            from core.level_proximity_validator import level_proximity_validator

            entry_price = signal.get('entry_price', ml_data.get('mid', 0))
            direction = signal.get('action', 'LONG')

            is_valid, reject_reason, nearest_level = level_proximity_validator.validate_proximity(
                snapshot=ml_data,
                price=entry_price,
                symbol=symbol,
                direction=direction
            )

            if not is_valid:
                logger.warning(f"[{symbol}] ❌ Signal rejeté: {reject_reason}")
                return None

            # Trade justifié par ce niveau
            logger.info(
                f"[{symbol}] ✅ Trade justifié par: {nearest_level.description} "
                f"({nearest_level.distance_ticks:.0f}t)"
            )

            # ✅ NOUVEAU 28/11: Extraire key_level pour exclusion validations
            key_level = None
            if nearest_level:
                key_level = {
                    'type': nearest_level.level_type if hasattr(nearest_level, 'level_type') else None,
                    'price': nearest_level.price if hasattr(nearest_level, 'price') else None,
                    'distance': nearest_level.distance_ticks if hasattr(nearest_level, 'distance_ticks') else None
                }

                # 🔥 FIX 08/12: AJOUTER LE NIVEAU AUX MÉTADONNÉES POUR LE FILTRE TENDANCE!
                # Sans ça, le trend_filter ne sait pas que c'est un rebond sur niveau majeur
                signal['metadata']['menthorq_level'] = nearest_level.level_type if hasattr(nearest_level, 'level_type') else None
                signal['metadata']['menthorq_level_price'] = nearest_level.price if hasattr(nearest_level, 'price') else None
                signal['metadata']['menthorq_level_distance'] = nearest_level.distance_ticks if hasattr(nearest_level, 'distance_ticks') else None
                logger.info(f"[{symbol}] 🔑 Niveau ajouté aux métadonnées: {signal['metadata']['menthorq_level']}")

            # ═══════════════════════════════════════════════════════════
            # VALIDATIONS CRITIQUES (ajouté 20/11/2025)
            # Empêcher trades catastrophiques comme NQ_20251120_002007
            # ═══════════════════════════════════════════════════════════
            validation_result = self._validate_catastrophic_trade_filters(
                signal, ml_data, symbol, key_level=key_level  # ✅ NOUVEAU 28/11: Passer key_level
            )
            if validation_result is None:
                logger.warning(f"[{symbol}] ❌ Signal rejeté par validations critiques")
                return None

            return signal

        except Exception as e:
            logger.error(f"❌ [{symbol}] Erreur ML 3-Layer Strategy: {e}", exc_info=True)
            return None

    def _validate_catastrophic_trade_filters(self, signal: Dict,
                                             snapshot: dict, symbol: str,
                                             key_level: Optional[Dict] = None) -> Optional[Dict]:
        """
        Valide les filtres critiques pour empêcher trades catastrophiques.

        Ajouté 20/11/2025 pour bloquer trades comme NQ_20251120_002007:
        - MenthorQ UNKNOWN
        - 1D Proximity excessive
        - Scores insuffisants
        - Session ASIA filtres stricts

        Args:
            signal: Signal de trading
            snapshot: Snapshot de marché
            symbol: ES/NQ/RTY
            key_level: ✅ NOUVEAU 28/11: Niveau MenthorQ tradé (à exclure des validations)
                       Format: {'type': 'GEX_3', 'price': 21000.50, 'distance': 8}
                       OU: {'level_type': 'hvl', 'level_price': 21000.50}
        """
        # ═══════════════════════════════════════════════════════════
        # VALIDATION MENTHORQ (ajouté 20/11/2025)
        # ✅ CORRIGÉ 20/11: Calculer depuis niveaux disponibles
        # ═══════════════════════════════════════════════════════════

        # ✅ CORRIGÉ 20/11: Utiliser menthor_distances (distances en points) au lieu de chercher niveaux directs
        # Les snapshots contiennent menthor_distances avec distances en points, pas les prix des niveaux
        price = snapshot.get('mid', snapshot.get('close', 0))

        # ✅ CORRIGÉ: Normaliser symbol pour obtenir tick_size correct
        symbol_base = symbol.split('_')[0] if '_' in symbol else symbol[:2] if len(symbol) >= 2 else symbol
        symbol_base = symbol_base.upper()

        # Déterminer tick_size selon symbole
        if symbol_base in ['ES', 'NQ']:
            tick_size = 0.25
        elif symbol_base == 'RTY':
            tick_size = 0.10
        else:
            tick_size = 0.25  # Par défaut

        # ✅ NOUVEAU 28/11: Extraire infos du key_level pour l'exclure des validations
        key_level_type = None
        key_level_price = None

        if key_level:
            # Gérer différents formats de key_level
            key_level_type = (
                key_level.get('type') or
                key_level.get('level_type') or
                key_level.get('menthorq_level_type')
            )
            key_level_price = (
                key_level.get('price') or
                key_level.get('level_price') or
                key_level.get('level')
            )

            if key_level_type and key_level_price:
                logger.info(
                    f"[{symbol}] 🔑 Key level à exclure des validations: "
                    f"{key_level_type} @ {key_level_price:.2f}"
                )

        # ✅ NOUVEAU 28/11: Helper pour vérifier si un niveau doit être exclu
        def is_key_level_match(level_type_check: str, level_price_check: float) -> bool:
            """Vérifie si ce niveau est le key_level qu'on trade (à exclure)"""
            if not key_level_type or not key_level_price:
                return False

            # Tolérance 2 ticks pour matching
            tolerance = 2 * tick_size

            # Normaliser les types pour comparaison (GEX_3 vs GEX_DN, etc.)
            type_check_upper = level_type_check.upper().replace('_', '')
            key_type_upper = key_level_type.upper().replace('_', '')

            # Match si même type (avec variations) ET même prix (±2 ticks)
            type_match = (
                type_check_upper == key_type_upper or
                key_type_upper in type_check_upper or
                type_check_upper in key_type_upper
            )
            price_match = abs(level_price_check - key_level_price) < tolerance

            return type_match and price_match

        # Trouver le niveau MenthorQ le plus proche via menthor_distances
        menthorq_level = None
        menthorq_distance = 9999

        # ✅ PRIORITÉ: Utiliser menthor_distances (distances en points)
        menthor_distances = snapshot.get('menthor_distances', {})
        if isinstance(menthor_distances, dict):
            # Convertir points en ticks (1 point = 4 ticks pour ES/NQ)
            # Priorité 1: Blind Spots (souvent les plus proches)
            near_blind = menthor_distances.get('near_blind')
            if near_blind is not None:
                dist_ticks = abs(near_blind)  # ✅ CORRECTION 25/11: DÉJÀ EN TICKS
                if dist_ticks < menthorq_distance:
                    menthorq_distance = dist_ticks
                    menthorq_level = 'BLIND_SPOT'

            # Priorité 2: HVL
            # ✅ CORRECTION 25/11: menthor_distances est DÉJÀ en ticks
            hvl0 = menthor_distances.get('hvl0')
            if hvl0 is not None:
                dist_ticks = abs(hvl0)  # ✅ DÉJÀ EN TICKS
                if dist_ticks < menthorq_distance:
                    menthorq_distance = dist_ticks
                    menthorq_level = 'HVL'

            # Priorité 3: GEX
            # ✅ CORRECTION 25/11: menthor_distances est DÉJÀ en ticks (pas en points)
            # Ne PAS multiplier par 4 (tick_size)
            near_gex_up = menthor_distances.get('near_gex_up')
            near_gex_dn = menthor_distances.get('near_gex_dn')
            if near_gex_up is not None:
                dist_ticks = abs(near_gex_up)  # ✅ DÉJÀ EN TICKS
                if dist_ticks < menthorq_distance:
                    menthorq_distance = dist_ticks
                    menthorq_level = 'GEX_UP'
            if near_gex_dn is not None:
                dist_ticks = abs(near_gex_dn)  # ✅ DÉJÀ EN TICKS
                if dist_ticks < menthorq_distance:
                    menthorq_distance = dist_ticks
                    menthorq_level = 'GEX_DN'

            # Priorité 4: 1D MAX/MIN
            # ✅ CORRECTION 25/11: menthor_distances est DÉJÀ en ticks
            dist_1d_max = menthor_distances.get('dist_1d_max')
            if dist_1d_max is not None:
                dist_ticks = abs(dist_1d_max)  # ✅ DÉJÀ EN TICKS
                if dist_ticks < menthorq_distance:
                    menthorq_distance = dist_ticks
                    menthorq_level = '1D_MAX'

            dist_1d_min = menthor_distances.get('dist_1d_min')
            if dist_1d_min is not None:
                dist_ticks = abs(dist_1d_min)  # ✅ DÉJÀ EN TICKS
                if dist_ticks < menthorq_distance:
                    menthorq_distance = dist_ticks
                    menthorq_level = '1D_MIN'

        # ✅ FALLBACK: Si menthor_distances non disponible, chercher niveaux directs
        if menthorq_level is None:
            # Priorité 1: HVL
            hvl = snapshot.get('hvl')
            if hvl:
                # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                if not is_key_level_match('HVL', hvl):
                    dist = abs(price - hvl) / tick_size
                    if dist < menthorq_distance:
                        menthorq_distance = dist
                        menthorq_level = 'HVL'
                else:
                    logger.debug(f"[{symbol}] ✅ HVL exclu (c'est le key_level)")

            # Priorité 2: Blind Spots
            for i in range(9):
                blind = snapshot.get(f'blind_spot_{i}')
                if blind:
                    # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                    if not is_key_level_match(f'BLIND_SPOT_{i}', blind):
                        dist = abs(price - blind) / tick_size
                        if dist < menthorq_distance:
                            menthorq_distance = dist
                            menthorq_level = f'BLIND_SPOT_{i}'
                    else:
                        logger.debug(f"[{symbol}] ✅ BLIND_SPOT_{i} exclu (c'est le key_level)")

            # Priorité 3: 1D MAX/MIN
            day_max = snapshot.get('1d_max')
            if day_max:
                # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                if not is_key_level_match('1D_MAX', day_max):
                    dist = abs(price - day_max) / tick_size
                    if dist < menthorq_distance:
                        menthorq_distance = dist
                        menthorq_level = '1D_MAX'
                else:
                    logger.debug(f"[{symbol}] ✅ 1D_MAX exclu (c'est le key_level)")

            day_min = snapshot.get('1d_min')
            if day_min:
                # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                if not is_key_level_match('1D_MIN', day_min):
                    dist = abs(price - day_min) / tick_size
                    if dist < menthorq_distance:
                        menthorq_distance = dist
                        menthorq_level = '1D_MIN'
                else:
                    logger.debug(f"[{symbol}] ✅ 1D_MIN exclu (c'est le key_level)")

            # Priorité 4: GEX levels
            for i in range(1, 11):
                gex = snapshot.get(f'gex_{i}')
                if gex:
                    # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                    if not is_key_level_match(f'GEX_{i}', gex):
                        dist = abs(price - gex) / tick_size
                        if dist < menthorq_distance:
                            menthorq_distance = dist
                            menthorq_level = f'GEX_{i}'
                    else:
                        logger.debug(f"[{symbol}] ✅ GEX_{i} exclu (c'est le key_level)")

            # Priorité 5: Call Resistance / Put Support
            call_res = snapshot.get('call_resistance')
            if call_res:
                # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                if not is_key_level_match('CALL_RESISTANCE', call_res):
                    dist = abs(price - call_res) / tick_size
                    if dist < menthorq_distance:
                        menthorq_distance = dist
                        menthorq_level = 'CALL_RESISTANCE'
                else:
                    logger.debug(f"[{symbol}] ✅ CALL_RESISTANCE exclu (c'est le key_level)")

            put_sup = snapshot.get('put_support')
            if put_sup:
                # ✅ NOUVEAU 28/11: Exclure si c'est le key_level
                if not is_key_level_match('PUT_SUPPORT', put_sup):
                    dist = abs(price - put_sup) / tick_size
                    if dist < menthorq_distance:
                        menthorq_distance = dist
                        menthorq_level = 'PUT_SUPPORT'
                else:
                    logger.debug(f"[{symbol}] ✅ PUT_SUPPORT exclu (c'est le key_level)")

        # ✅ CORRIGÉ 20/11: Si aucun niveau trouvé après les deux méthodes, rejeter
        if menthorq_level is None:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: Aucun niveau MenthorQ trouvé "
                f"(ni menthor_distances, ni niveaux directs dans snapshot)"
            )
            return None

        # ✅ UNIFIÉ 28/11/2025: Utiliser configuration unifiée (self.MENTHORQ_DISTANCE_CONFIG)
        # Une seule source de vérité: ES 15t, NQ 35t (compromis optimal), RTY 12t
        symbol_base = symbol.split('_')[0] if '_' in symbol else symbol[:2]
        max_distance_menthorq = self.MENTHORQ_DISTANCE_CONFIG.get(symbol_base.upper(), 35)

        if menthorq_distance > max_distance_menthorq:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: MenthorQ trop loin - "
                f"Distance: {menthorq_distance:.0f}t > {max_distance_menthorq}t max "
                f"(Niveau: {menthorq_level})"
            )
            return None

        logger.info(
            f"[{symbol}] ✅ MenthorQ OK: {menthorq_level} @ "
            f"{menthorq_distance:.0f}t"
        )

        # ═══════════════════════════════════════════════════════════
        # VALIDATION PRIX AU-DESSUS DU 1D MAX (ajouté 20/11/2025)
        # Rejeter si prix trop au-dessus du max (faux breakout)
        # ═══════════════════════════════════════════════════════════

        day_max = snapshot.get('1d_max')
        if day_max and price > day_max:
            distance_above_max = (price - day_max) / tick_size

            # 🔧 TEST 20/11: Seuils augmentés pour permettre signaux valides (marché en extension forte)
            # ✅ CORRIGÉ: Normaliser symbol (ESZ25_FUT_CME → ES)
            symbol_base = symbol.split('_')[0] if '_' in symbol else symbol[:2] if len(symbol) >= 2 else symbol
            symbol_base = symbol_base.upper()

            max_above_max = {
                'ES': 150,   # 🔧 TEST: 50 → 150 ticks (37.5 points) - permet extensions fortes actuelles
                'NQ': 600,   # 🔧 TEST: 60 → 600 ticks (150 points) - NQ très volatil, extensions très fortes
                'RTY': 100   # 🔧 TEST: 35 → 100 ticks (10 points)
            }

            max_dist = max_above_max.get(symbol_base, 150)  # 🔧 TEST: Fallback à 150 au lieu de 20

            if distance_above_max > max_dist:
                logger.warning(
                    f"[{symbol}] ❌ Signal REJETÉ: Prix trop au-dessus du 1D MAX - "
                    f"Distance: {distance_above_max:.0f}t > {max_dist}t max "
                    f"(Prix: {price:.2f} > Max: {day_max:.2f})"
                )
                return None

            logger.info(
                f"[{symbol}] ✅ Prix au-dessus du 1D MAX mais acceptable: "
                f"{distance_above_max:.0f}t < {max_dist}t"
            )

        # ═══════════════════════════════════════════════════════════
        # VALIDATION 1D PROXIMITY (ajouté 20/11/2025)
        # ✅ CORRIGÉ 20/11: Calculer depuis 1d_max et 1d_min
        # ═══════════════════════════════════════════════════════════

        # ✅ CORRECTION: Calculer la distance au 1D high/low au lieu de chercher un champ inexistant
        day_min = snapshot.get('1d_min')

        proximity_1d = 9999

        if day_max:
            dist_max = abs(price - day_max) / tick_size
            if dist_max < proximity_1d:
                proximity_1d = dist_max

        if day_min:
            dist_min = abs(price - day_min) / tick_size
            if dist_min < proximity_1d:
                proximity_1d = dist_min

        max_proximity_1d = {
            'ES': 50,    # ticks
            'NQ': 2000,  # ticks (DÉSACTIVÉ - accepte tout le range)
            'RTY': 40    # ticks
        }

        max_prox = max_proximity_1d.get(symbol, 50)

        # 🔧 TEMPORAIREMENT DÉSACTIVÉ (25/11/2025) - Pour tester trades au milieu du range
        # if proximity_1d > max_prox:
        #     logger.warning(
        #         f"[{symbol}] ❌ Signal REJETÉ: Trop loin du 1D high/low - "
        #         f"Distance: {proximity_1d:.0f}t > {max_prox}t max"
        #     )
        #     return None

        logger.info(
            f"[{symbol}] ℹ️ 1D Proximity CHECK DÉSACTIVÉ: {proximity_1d:.0f}t (filtre temporairement off)"
        )

        # ═══════════════════════════════════════════════════════════
        # VALIDATION SCORES MINIMUM (ajouté 20/11/2025)
        # 🔥 CORRIGÉ 20/11: Utiliser seuils par session depuis unified_thresholds
        # ═══════════════════════════════════════════════════════════

        from config.unified_thresholds import VALIDATION_THRESHOLDS

        # Récupérer scores depuis signal ou snapshot
        # Confluence = total_confidence dans menthorq_3layer
        confluence = signal.get('confluence', signal.get('confidence', 0.0))
        menthorq_score = signal.get('layer1_confidence', snapshot.get('menthorq_score', 0.0))
        orderflow = signal.get('layer2_confidence', snapshot.get('orderflow_score', 0.0))
        context = signal.get('layer3_confidence', snapshot.get('context_score', 0.0))

        # Déterminer la session pour utiliser les bons seuils
        # 🔥 CORRIGÉ 20/11: La session peut être dans 'session', 'session_id', ou 'context.session'
        session = (
            snapshot.get('session') or
            snapshot.get('session_id') or
            snapshot.get('context', {}).get('session') or
            snapshot.get('context', {}).get('session_id') or
            'UNKNOWN'
        )
        # 🔥 CORRIGÉ 20/11: Gérer cas où session est un dict (ex: {'name': 'LONDON'})
        if isinstance(session, dict):
            session = session.get('name', session.get('session', 'UNKNOWN'))
        session_upper = session.upper() if isinstance(session, str) else 'UNKNOWN'

        # Mapper session vers clé dans VALIDATION_THRESHOLDS
        session_key = None
        if 'ASIA' in session_upper:
            session_key = 'asia'
        elif 'LONDON' in session_upper or 'EUROPE' in session_upper or 'LONDRES' in session_upper:
            session_key = 'london'
        elif 'US' in session_upper or 'NEW_YORK' in session_upper or 'NEWYORK' in session_upper:
            session_key = 'us'

        # 🔥 CORRIGÉ 20/11: Validation et recalcul si session semble incorrecte
        current_hour = datetime.now().hour
        if session_upper == 'US' and 8 <= current_hour < 16:
            # Session devrait être LONDON mais snapshot dit US → recalculer
            logger.warning(f"[{symbol}] ⚠️ Session incorrecte dans snapshot: {session} (heure={current_hour}h) → Forcer LONDON")
            session_upper = 'LONDON'
            session_key = 'london'
        elif session_upper == 'LONDON' and (current_hour < 8 or current_hour >= 16):
            # Session devrait être autre chose mais snapshot dit LONDON → recalculer
            if 0 <= current_hour < 8:
                session_upper = 'ASIA'
                session_key = 'asia'
            else:
                session_upper = 'US'
                session_key = 'us'
            logger.warning(f"[{symbol}] ⚠️ Session incorrecte dans snapshot: {session} (heure={current_hour}h) → Forcer {session_upper}")

        # 🔍 DEBUG: Logger la détection de session (INFO pour diagnostic)
        logger.info(f"[{symbol}] 🔍 Détection session: raw={session}, upper={session_upper}, key={session_key}, heure={current_hour}h")

        # Récupérer seuils par session ou par défaut
        if session_key and session_key in VALIDATION_THRESHOLDS:
            session_thresholds = VALIDATION_THRESHOLDS[session_key]
            min_confluence = session_thresholds.get('confluence', VALIDATION_THRESHOLDS.get('confluence', 0.75))
            min_orderflow = session_thresholds.get('orderflow', VALIDATION_THRESHOLDS.get('orderflow_min', 0.20))
            min_context = session_thresholds.get('context', VALIDATION_THRESHOLDS.get('context_min', 0.15))
            min_menthorq = session_thresholds.get('menthorq', VALIDATION_THRESHOLDS.get('menthorq_min', 0.50))
        else:
            # Seuils par défaut si session non reconnue
            min_confluence = VALIDATION_THRESHOLDS.get('confluence', 0.75)
            min_orderflow = VALIDATION_THRESHOLDS.get('orderflow_min', 0.20)
            min_context = VALIDATION_THRESHOLDS.get('context_min', 0.15)
            min_menthorq = VALIDATION_THRESHOLDS.get('menthorq_min', 0.50)

        # Vérifier confluence
        if confluence < min_confluence:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: Confluence insuffisante - "
                f"{confluence:.2f} < {min_confluence:.2f} ({session_key or 'default'})"
            )
            return None

        # Vérifier MenthorQ score
        # 🔥 CORRIGÉ 20/11: Utiliser epsilon pour éviter problèmes de précision flottante
        EPSILON = 1e-6
        if menthorq_score < min_menthorq - EPSILON:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: MenthorQ score insuffisant - "
                f"{menthorq_score:.2f} < {min_menthorq:.2f} ({session_key or 'default'})"
            )
            return None

        # Vérifier OrderFlow (seulement si seuil > 0, car ASIA peut être désactivé)
        if min_orderflow > 0.0 and orderflow < min_orderflow:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: OrderFlow insuffisant - "
                f"{orderflow:.2f} < {min_orderflow:.2f} ({session_key or 'default'})"
            )
            return None
        elif min_orderflow == 0.0:
            logger.debug(f"[{symbol}] ✅ OrderFlow désactivé pour session {session_key}")

        # Vérifier Context
        if context < min_context:
            logger.warning(
                f"[{symbol}] ❌ Signal REJETÉ: Context insuffisant - "
                f"{context:.2f} < {min_context:.2f} ({session_key or 'default'})"
            )
            return None

        logger.info(
            f"[{symbol}] ✅ Scores OK ({session_key or 'default'}): "
            f"C={confluence:.2f} (min={min_confluence:.2f}), "
            f"M={menthorq_score:.2f} (min={min_menthorq:.2f}), "
            f"O={orderflow:.2f} (min={'DÉSACTIVÉ' if min_orderflow == 0.0 else f'{min_orderflow:.2f}'}), "
            f"Ctx={context:.2f} (min={min_context:.2f})"
        )

        return signal

    def _get_tick_size(self, symbol_base: str) -> float:
        """Retourne la taille du tick selon le symbole"""
        tick_sizes = {
            'ES': 0.25,
            'NQ': 0.25,
            'RTY': 0.10,
            'RT': 0.10  # Alias pour RTY
        }
        return tick_sizes.get(symbol_base, 0.25)

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
            # ✅ CONFIGURATION ASIA: SL plus large (liquidité faible)
            sl_base = self.sl_optimal_ticks.get(symbol_base, 15)

            # ✅ CONFIGURATION ASIA: SL plus large (liquidité faible)
            session = ml_data.get('session', ml_data.get('session_id', 'UNKNOWN'))
            session_upper = session.upper() if isinstance(session, str) else 'UNKNOWN'

            if session_upper == 'ASIA':
                from config.asia_session_config import get_asia_risk_adjustments
                asia_risk = get_asia_risk_adjustments()
                sl_extra = asia_risk.get('sl_extra_ticks', 10)
                sl_ticks = sl_base + sl_extra
                logger.debug(f"✅ [{symbol_base}] ASIA: SL ajusté {sl_base}t → {sl_ticks}t (+{sl_extra}t)")
            else:
                sl_ticks = sl_base
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

    def _get_current_session_name(self) -> str:
        """
        🆕 Retourne le nom de la session actuelle basé sur l'heure Paris.

        Sessions de trading:
        - London: 08:00-11:00
        - US Morning: 15:50-17:00
        - US Power Hour: 20:00-21:30

        Sessions non tradées:
        - ASIA: 00:00-08:00
        - Pre-US: 11:00-15:50
        - Lunch: 17:00-20:00
        - Closed: 21:30-00:00

        Returns:
            str: Nom de la session (correspondant aux clés de MIN_PRESSURE_STRENGTH_BY_SESSION)
        """
        paris_tz = pytz.timezone('Europe/Paris')
        now = datetime.now(paris_tz)
        hour = now.hour
        minute = now.minute

        # ASIA Session (00:00-08:00 Paris)
        if 0 <= hour < 8:
            return "ASIA"
        # London Session (08:00-11:00)
        elif 8 <= hour < 11:
            return "London"
        # Pre-US (11:00-15:50)
        elif 11 <= hour < 15 or (hour == 15 and minute < 50):
            return "Pre-US"
        # US Morning (15:50-17:00) - ✅ SESSION PRODUCTION
        elif (hour == 15 and minute >= 50) or hour == 16:
            return "US Morning"
        # Lunch US (17:00-20:00)
        elif hour == 17 or hour == 18 or hour == 19:
            return "Lunch"
        # US Power Hour (20:00-21:30) - ✅ SESSION PRODUCTION
        elif hour == 20 or (hour == 21 and minute < 30):
            return "US Power Hour"
        # Closed (21:30-00:00)
        else:
            return "Closed"

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

    def _calculate_session_quality(self, snapshot: Dict, symbol: str, context: Dict) -> float:
        """
        Calcule score de qualité de la session.

        Critères:
        - Hot zone (15h-16h30 ET): +40%
        - Haute volatilité (VIX >18): +20%
        - Volume élevé: +20%
        - Momentum clair: +20%

        Args:
            snapshot: Snapshot ML_READY
            symbol: Symbole
            context: Résultat ML 3-Layer

        Returns:
            float: Score 0.0-1.0
        """
        score = 0.0

        # 1. Hot zone (40%)
        # 🔥 25/11/2025: FIX - Utiliser datetime.now() directement car snapshot['timestamp'] souvent vide
        try:
            # Calculer l'heure UTC actuelle
            dt = datetime.now(timezone.utc)
            hour = dt.hour
            logger.info(f"[{symbol}] 🔍 SESSION QUALITY: Heure UTC actuelle={hour}h")

            # 🔥 HOT ZONES CORRIGÉES - 27/11/2025 - FIX BUG US MORNING
            # Hot zone ASIE: 00h-04h UTC (01h-05h FR) - Tokyo/Hong Kong
            # Hot zone LONDRES: 08h-12h UTC (09h-13h FR)
            # Hot zone US MORNING: 14h-17h UTC (09h30-12h00 ET) - US Open + Morning
            # Hot zone US POWER: 20h-21h UTC (15h00-16h00 ET) - Power Hour + Close
            asia_hot = 0 <= hour <= 4
            london_hot = 8 <= hour <= 12
            us_hot = (14 <= hour <= 17) or (20 <= hour <= 21)  # ✅ CORRIGÉ: Ajout US Morning
            hot_zone = asia_hot or london_hot or us_hot

            if hot_zone:
                zone_name = 'ASIE' if asia_hot else ('LONDRES' if london_hot else 'US')
                logger.info(f"[{symbol}] ✅ Hot zone détectée: {zone_name} @ {hour}h UTC")
                score += 0.40
                logger.info(f"[{symbol}] Session: Hot zone (+40%) → score={score:.2f}")
            else:
                logger.info(f"[{symbol}] ❌ Hors hot zone @ {hour}h UTC (asia={asia_hot}, london={london_hot}, us={us_hot})")

        except Exception as e:
            logger.error(f"[{symbol}] ❌ Erreur calcul hot_zone: {e}")
            hot_zone = False

        # 2. Volatilité (20%)
        vix = snapshot.get('vix', context.get('vix', 15.0))
        if vix >= 18:
            score += 0.20
            logger.debug(f"[{symbol}] Session: High VIX {vix:.1f} (+20%)")
        elif vix >= 15:
            score += 0.10
            logger.debug(f"[{symbol}] Session: Medium VIX {vix:.1f} (+10%)")

        # 3. Volume (20%)
        volume_ratio = snapshot.get('volume_ratio', 1.0)
        if volume_ratio >= 1.5:
            score += 0.20
            logger.debug(f"[{symbol}] Session: High volume {volume_ratio:.2f}x (+20%)")
        elif volume_ratio >= 1.2:
            score += 0.10
            logger.debug(f"[{symbol}] Session: Good volume {volume_ratio:.2f}x (+10%)")

        # 4. Momentum (20%)
        bullish_score = context.get('bullish_score', snapshot.get('bullish_score', 0.0))
        if abs(bullish_score) >= 0.15:
            score += 0.20
            logger.debug(f"[{symbol}] Session: Clear momentum {bullish_score:+.2f} (+20%)")
        elif abs(bullish_score) >= 0.08:
            score += 0.10
            logger.debug(f"[{symbol}] Session: Some momentum {bullish_score:+.2f} (+10%)")

        return score


def create_ml_3layer_strategy(ml_3layer_system=None):
    """
    Factory function pour créer ML3LayerStrategy

    Args:
        ml_3layer_system: Instance de ML3LayerIntegratedSystem (injecté)

    Returns:
        Instance de MenthorQ3LayerStrategy (anciennement ML3LayerStrategy)
    """
    return MenthorQ3LayerStrategy(ml_3layer_system=ml_3layer_system)


def create_menthorq_3layer_strategy(ml_3layer_system=None):
    """
    Factory function pour créer une instance de MenthorQ3LayerStrategy.

    Args:
        ml_3layer_system: Instance de ML3LayerIntegratedSystem (premier argument, pas config!)

    Returns:
        MenthorQ3LayerStrategy: Instance initialisée
    """
    return MenthorQ3LayerStrategy(ml_3layer_system=ml_3layer_system)
