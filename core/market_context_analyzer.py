#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Context Analyzer - Analyse contextuelle riche pour trading intraday
Génère des plans de trading automatiques basés sur les niveaux clés et l'orderflow
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TradingScenario(Enum):
    """Types de scénarios de trading"""
    CONTINUATION_BEARISH = "continuation_bearish"
    CONTINUATION_BULLISH = "continuation_bullish"
    FADE_RESISTANCE = "fade_resistance"
    FADE_SUPPORT = "fade_support"
    BREAKOUT_BULLISH = "breakout_bullish"
    BREAKOUT_BEARISH = "breakout_bearish"
    POP_AND_DROP = "pop_and_drop"
    DIP_AND_RIP = "dip_and_rip"


@dataclass
class TradingLevel:
    """Niveau de trading avec contexte"""
    price: float
    type: str  # "entry", "sl", "tp1", "tp2", "tp3"
    distance_pts: float
    distance_ticks: int
    reason: str
    confidence: str  # "high", "medium", "low"


@dataclass
class TradingPlan:
    """Plan de trading complet pour un scénario"""
    scenario: TradingScenario
    direction: str  # "LONG" ou "SHORT"
    priority: int  # 1 = prioritaire, 2 = secondaire, 3 = opportuniste
    trigger: str  # Description du déclencheur
    entry_zone: Tuple[float, float]  # (min, max)
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: Optional[float]
    risk_reward: float
    invalidation: str  # Condition d'invalidation
    management: str  # Règles de gestion
    confidence: float  # 0.0 à 1.0


@dataclass
class MarketContext:
    """Contexte de marché complet"""
    symbol: str
    current_price: float
    position_vs_hvl: str  # "above", "at", "below"
    position_vs_vwap: str
    position_vs_value_area: str  # "inside", "above", "below"
    main_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    orderflow_pressure: str  # "BUYING", "SELLING", "BALANCED"
    gamma_condition: str  # "POSITIVE", "NEGATIVE", "NEUTRAL"
    key_magnets: List[Dict[str, Any]]  # Liste des "aimants" (VWAP, HVL, GEX walls)
    proximity_alerts: List[str]  # Alertes de proximité
    trading_plans: List[TradingPlan]
    reasoning: str  # Explication du raisonnement

    # ═══════════════════════════════════════════════════════════════
    # 🚀 NOUVELLES FEATURES PRO (V3.3)
    # ═══════════════════════════════════════════════════════════════
    bias_strength: float = 0.0  # Score quantifié du bias (-1.0 à +1.0)
    auto_signal: str = "WAIT"  # Signal automatique: "BUY", "SELL", "WAIT"
    visual_zones: List[Dict[str, Any]] = None  # Zones pour dashboard graphique
    gamma_flip_detected: Optional[str] = None  # "UP", "DOWN", None
    summary: Dict[str, Any] = None  # KPIs compacts pour dashboard (price, vwap, bias, etc.)

    # ═══════════════════════════════════════════════════════════════
    # ✨ NOUVELLES FEATURES V3.4
    # ═══════════════════════════════════════════════════════════════
    quality_score: float = 0.5  # Score de qualité du contexte (0.0 à 1.0)


class MarketContextAnalyzer:
    """
    Analyseur de contexte de marché - Génère des plans de trading automatiques

    ✨ V3.4: Ajout quality_score, stats tracking, validation input
    """

    def __init__(self, symbol: str = "ES"):
        self.symbol = symbol
        self.atr_multiplier_sl = 1.0  # 1x ATR pour SL
        self.atr_multiplier_tp = 2.0  # 2x ATR pour TP
        self.last_trade_ts = {}  # Cool-down par scénario

        # ═══════════════════════════════════════════════════════════════
        # 🚀 CACHE POUR GAMMA FLIP DETECTION
        # ═══════════════════════════════════════════════════════════════
        self._last_gamma_condition = {}  # Cache pour détecter les flips

        # ═══════════════════════════════════════════════════════════════
        # ✨ V3.4: STATS TRACKING
        # ═══════════════════════════════════════════════════════════════
        self.stats = {
            'total_analyses': 0,
            'by_bias': {'BULLISH': 0, 'BEARISH': 0, 'NEUTRAL': 0},
            'by_gamma': {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0},
            'gamma_flips': 0,
            'plans_generated': 0,
            'avg_quality_score': 0.0
        }

    def _get_tick_size(self, data: Dict[str, Any]) -> float:
        """
        Obtenir la taille de tick avec validation anti-corruption

        PATCH v3.5.24: Protection contre spreads aberrants des feeds différés
        (ex: CL différé peut avoir spread=5967.73 au lieu de 0.01)
        """
        ts = data.get('tick_size')
        if ts and ts > 0:
            return float(ts)

        spr = float(data.get('spread', 0.25))

        # PATCH v3.5.24: Validation spread pour feed différé corrompu
        if spr > 100:  # Spread aberrant détecté (ex: CL différé = 5967)
            # Force default ES/NQ pour éviter propagation d'erreur
            return 0.25

        # ES/NQ: la plupart du temps 0.25
        if spr in (0.25, 0.5, 1.0):
            return 0.25

        return max(round(spr, 4), 0.01)

    def _safe(self, value: Any, default: Any = None) -> Any:
        """
        Helper robuste pour null handling

        Args:
            value: Valeur à vérifier
            default: Valeur par défaut si None

        Returns:
            value si non None, sinon default
        """
        return value if value is not None else default

    def _rr_from_entry_zone(self, entry_zone: Tuple[float, float], stop: float, tp: float) -> float:
        """Calculer le Risk/Reward depuis la zone d'entrée moyenne"""
        if not entry_zone:
            return 0.0
        entry_avg = (entry_zone[0] + entry_zone[1]) / 2.0
        risk = abs(stop - entry_avg)
        reward = abs(tp - entry_avg)
        return (reward / risk) if risk > 0 else 0.0

    def _cooldown_ok(self, scenario: TradingScenario, seconds: int = 180) -> bool:
        """Vérifier si le cool-down est respecté"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).timestamp()
        ts = self.last_trade_ts.get(scenario.value, 0)
        return (now - ts) > seconds

    def _time_filter_ok(self, tsec: float) -> bool:
        """
        Filtre horaire intraday - DÉSACTIVÉ

        ⚠️ ATTENTION: Ce filtre utilisait UTC (14:35-21:00) ce qui est INCORRECT.
        Les heures de trading sont gérées par SessionQualityMonitor en heure Paris.
        Ce filtre est donc redondant et a été désactivé.
        """
        # ✅ Toujours retourner True - SessionQualityMonitor gère les heures
        return True

    def _confluence_boost(self, data: Dict[str, Any]) -> float:
        """Boost de confiance basé sur la confluence des indicateurs"""
        boost = 0.0
        boost += float(data.get('confluence_strength', 0.0)) * 0.3
        boost += float(data.get('menthorq_proximity_strength', 0.0)) * 0.2
        boost += (float(data.get('smart_money_flow', 0.5)) - 0.5) * 0.6
        boost += float(data.get('depth_imbalance', 0.0)) * 0.2
        return max(min(boost, 0.4), -0.4)  # clamp [-0.4, 0.4]

    # ═══════════════════════════════════════════════════════════════
    # ✨ V3.4: NOUVELLES MÉTHODES
    # ═══════════════════════════════════════════════════════════════

    def validate_ml_ready_data(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        ✨ V3.4: Valide que les données ML_READY sont complètes

        Args:
            data: Dict ML_READY

        Returns:
            (is_valid, error_message)
        """
        required_fields = ['mid', 'hvl', 'vwap', 'atr', 'vva']

        for field in required_fields:
            if field not in data or data[field] is None:
                return False, f"Champ requis manquant: {field}"

        # Vérifier vva structure
        vva = data.get('vva', {})
        if not isinstance(vva, dict):
            return False, "vva doit être un dictionnaire"

        if 'vah' not in vva or 'val' not in vva:
            return False, "vva doit contenir vah et val"

        # Vérifier valeurs cohérentes
        mid = data.get('mid', 0)
        if mid <= 0:
            return False, f"Prix mid invalide: {mid}"

        atr = data.get('atr', 0)
        if atr <= 0:
            return False, f"ATR invalide: {atr}"

        return True, "OK"

    def _calculate_quality_score(
        self,
        data: Dict[str, Any],
        bias_strength: float,
        orderflow: str,
        gamma_condition: str,
        proximity_alerts: List[str]
    ) -> float:
        """
        ✨ V3.4: Calcule un score de qualité du contexte (0.0 à 1.0)

        Facteurs:
        - Bias strength (30%)
        - Orderflow alignment (20%)
        - Gamma condition (20%)
        - Confluence (15%)
        - Proximity (15% - pénalité)

        Args:
            data: Données marché
            bias_strength: Score bias (-1 à +1)
            orderflow: BUYING/SELLING/BALANCED
            gamma_condition: POSITIVE/NEGATIVE/NEUTRAL
            proximity_alerts: Liste alertes proximité

        Returns:
            Quality score (0.0 à 1.0)
        """
        score = 0.0

        # 1. Bias strength (30%) - Converti de [-1,+1] à [0,1]
        bias_component = (abs(bias_strength) * 0.30)
        score += bias_component

        # 2. Orderflow alignment (20%)
        if orderflow in ["BUYING", "SELLING"]:
            score += 0.20
        else:  # BALANCED
            score += 0.10

        # 3. Gamma condition (20%)
        if gamma_condition == "POSITIVE":
            score += 0.20  # Market stable
        elif gamma_condition == "NEUTRAL":
            score += 0.15
        else:  # NEGATIVE
            score += 0.10  # Market instable

        # 4. Confluence (15%)
        confluence_boost = self._confluence_boost(data)
        confluence_component = max(0, min((confluence_boost + 0.4) / 0.8, 1.0)) * 0.15
        score += confluence_component

        # 5. Proximity pénalité (15%)
        # Moins d'alertes = meilleur score
        proximity_penalty = min(len(proximity_alerts) * 0.05, 0.15)
        score += (0.15 - proximity_penalty)

        # Clamp final
        return max(0.1, min(score, 1.0))

    def get_stats(self) -> Dict[str, Any]:
        """
        ✨ V3.4: Retourne statistiques d'analyse

        Returns:
            Dict avec stats tracking
        """
        return self.stats.copy()

    def reset_stats(self):
        """✨ V3.4: Reset statistiques"""
        self.stats = {
            'total_analyses': 0,
            'by_bias': {'BULLISH': 0, 'BEARISH': 0, 'NEUTRAL': 0},
            'by_gamma': {'POSITIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0},
            'gamma_flips': 0,
            'plans_generated': 0,
            'avg_quality_score': 0.0
        }
        logger.info(f"[{self.symbol}] Stats MarketContextAnalyzer réinitialisées")

    # ═══════════════════════════════════════════════════════════════
    # 🚀 MÉTHODES PRO V3.3 - AMÉLIORATIONS INTELLIGENTES
    # ═══════════════════════════════════════════════════════════════

    def _detect_gamma_flip(self, data: Dict[str, Any], current_gamma_cond: str) -> Optional[str]:
        """
        Détecte un changement de condition gamma (flip) entre deux ticks

        Returns:
            "UP" si flip vers POSITIVE
            "DOWN" si flip vers NEGATIVE
            None si pas de flip
        """
        sym = self.symbol
        prev = self._last_gamma_condition.get(sym, "NEUTRAL")

        flip = None
        if prev != current_gamma_cond:
            if current_gamma_cond == "POSITIVE" and prev in ["NEGATIVE", "NEUTRAL"]:
                flip = "UP"
                logger.info(f"[{sym}] 🔼 Gamma Flip UP → retour en zone stable (gamma positif)")
                self.stats['gamma_flips'] += 1  # ✨ V3.4
            elif current_gamma_cond == "NEGATIVE" and prev in ["POSITIVE", "NEUTRAL"]:
                flip = "DOWN"
                logger.info(f"[{sym}] 🔻 Gamma Flip DOWN → risque d'accélération (gamma négatif)")
                self.stats['gamma_flips'] += 1  # ✨ V3.4

        # Mise à jour cache
        self._last_gamma_condition[sym] = current_gamma_cond
        return flip

    def _calculate_bias_strength(self, data: Dict[str, Any], bias: str, orderflow: str) -> float:
        """
        Calcule un score quantifié du bias (-1.0 à +1.0)

        Formule: mia_bullish_score (60%) + orderflow (30%) + position_vs_vwap (10%)
        """
        mia_score = data.get('mia_bullish_score', 0.0)

        # Orderflow contribution
        flow_score = 0.0
        if orderflow == "BUYING":
            flow_score = 0.5
        elif orderflow == "SELLING":
            flow_score = -0.5

        # VWAP position contribution
        d_vwap_atr = data.get('d_vwap_atr', 0.0)
        vwap_score = max(-0.3, min(0.3, d_vwap_atr / 10.0))  # Normalisé

        # Somme pondérée
        bias_strength = (mia_score * 0.6) + (flow_score * 0.3) + (vwap_score * 0.1)

        return max(-1.0, min(1.0, bias_strength))

    def _contextual_confidence_adjust(self, data: Dict[str, Any], conf: float, scenario_name: str) -> float:
        """
        Ajuste la confiance d'un plan selon le contexte volatilité + gamma

        Args:
            data: données de marché
            conf: confiance de base
            scenario_name: nom du scénario (pour détecter FADE vs CONTINUATION)

        Returns:
            Confiance ajustée (clamped 0.1-0.95)
        """
        net_gex = data.get('net_gex', 0)
        vol_regime = data.get('volatility_regime', 1)

        # Pénalité volatilité haute
        if vol_regime > 2:
            conf *= 0.8
            logger.debug(f"[{self.symbol}] Volatilité élevée (regime={vol_regime}) → confiance réduite")

        # Boost gamma positif pour FADES
        if net_gex > 0 and "FADE" in scenario_name.upper():
            conf *= 1.1
            logger.debug(f"[{self.symbol}] Gamma positif + FADE → confiance boostée")

        # Boost gamma négatif pour CONTINUATIONS
        elif net_gex < 0 and "CONTINUATION" in scenario_name.upper():
            conf *= 1.1
            logger.debug(f"[{self.symbol}] Gamma négatif + CONTINUATION → confiance boostée")

        return max(0.1, min(conf, 0.95))

    def _generate_visual_zones(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Génère les zones visuelles pour le dashboard graphique

        Returns:
            Liste de zones avec label, y (price), color
        """
        zones = []

        # VWAP
        vwap = data.get('vwap', 0)
        if vwap > 0:
            zones.append({
                "label": "VWAP",
                "y": vwap,
                "color": "#339AF0",
                "style": "solid"
            })

        # HVL
        hvl = data.get('hvl', 0)
        if hvl > 0:
            zones.append({
                "label": "HVL",
                "y": hvl,
                "color": "#FAB005",
                "style": "dashed"
            })

        # Value Area High/Low
        vva = data.get('vva', {})
        vah = vva.get('vah', 0)
        val = vva.get('val', 0)

        if vah > 0:
            zones.append({
                "label": "VAH",
                "y": vah,
                "color": "#51CF66",
                "style": "dotted"
            })

        if val > 0:
            zones.append({
                "label": "VAL",
                "y": val,
                "color": "#FF6B6B",
                "style": "dotted"
            })

        # Gamma Wall (si présent)
        gamma_wall = data.get('gamma_wall_level', 0)
        if gamma_wall > 0:
            zones.append({
                "label": "Gamma Wall",
                "y": gamma_wall,
                "color": "#FF00FF",
                "style": "solid"
            })

        # GEX levels proches
        gex_1 = data.get('gex_1', 0)
        if gex_1 > 0:
            zones.append({
                "label": "GEX_1",
                "y": gex_1,
                "color": "#9C27B0",
                "style": "dashed"
            })

        return zones

    def _generate_auto_signal(
        self,
        bias: str,
        orderflow: str,
        gamma_condition: str,
        bias_strength: float
    ) -> str:
        """
        Génère un signal automatique BUY/SELL/WAIT selon les conditions

        Args:
            bias: "BULLISH", "BEARISH", "NEUTRAL"
            orderflow: "BUYING", "SELLING", "BALANCED"
            gamma_condition: "POSITIVE", "NEGATIVE", "NEUTRAL"
            bias_strength: score quantifié (-1.0 à +1.0)

        Returns:
            "BUY", "SELL", "WAIT"
        """
        # Condition BUY: bias bullish + orderflow buying + gamma non négatif + strength > 0.4
        if (bias == "BULLISH" and
            orderflow == "BUYING" and
            gamma_condition != "NEGATIVE" and
            bias_strength > 0.4):
            return "BUY"

        # Condition SELL: bias bearish + orderflow selling + gamma non positif + strength < -0.4
        if (bias == "BEARISH" and
            orderflow == "SELLING" and
            gamma_condition != "POSITIVE" and
            bias_strength < -0.4):
            return "SELL"

        # Sinon, attendre
        return "WAIT"

    def _build_summary(
        self,
        data: Dict[str, Any],
        bias: str,
        orderflow: str,
        gamma_condition: str
    ) -> Dict[str, Any]:
        """
        Construit un résumé compact pour affichage dashboard (KPIs)

        Args:
            data: Données de marché
            bias: Bias principal
            orderflow: Pression orderflow
            gamma_condition: Condition gamma

        Returns:
            Dict avec KPIs essentiels
        """
        vva = self._safe(data.get('vva'), {})
        if not isinstance(vva, dict):
            vva = {}

        return {
            "price": round(self._safe(data.get('mid'), 0.0), 2),
            "d_vwap": round(self._safe(data.get('d_vwap'), 0.0), 2),
            "d_vwap_atr": round(self._safe(data.get('d_vwap_atr'), 0.0), 2),
            "vwap": self._safe(data.get('vwap')),
            "vah": vva.get('vah'),
            "val": vva.get('val'),
            "vpoc": vva.get('vpoc'),
            "hvl": self._safe(data.get('hvl')),
            "bias": bias,
            "orderflow": orderflow,
            "gamma": gamma_condition,
            "vol_regime": self._safe(data.get('volatility_regime'), 1.0),
            "net_gex": self._safe(data.get('net_gex')),
            "atr": self._safe(data.get('atr'), 0.0),
            "cum_delta_session": self._safe(data.get('cum_delta_session'), 0),
            "in_value_area": self._safe(data.get('in_value_area'), False),
        }

    def _apply_sane_buffers(
        self,
        data: Dict[str, Any],
        entry_zone: Tuple[float, float],
        sl: float,
        tp_list: List[Optional[float]]
    ) -> Tuple[float, List[Optional[float]]]:
        """Appliquer des marges minimales et snapper aux ticks"""
        ts = self._get_tick_size(data)

        # Au moins 4 ticks de marge pour SL
        if sl is not None and entry_zone:
            entry_avg = (entry_zone[0] + entry_zone[1]) / 2.0
            if abs(sl - entry_avg) < 4 * ts:
                sl = entry_avg - 4*ts if sl < entry_avg else entry_avg + 4*ts

        # Snap au pas de tick
        def snap(x):
            if x is None:
                return None
            return round(x / ts) * ts

        sl = snap(sl)
        tp_list = [snap(x) for x in tp_list]

        return sl, tp_list

    def analyze(self, data: Dict[str, Any], symbol: Optional[str] = None) -> MarketContext:
        """
        Analyse complète du contexte de marché

        ✨ V3.4: Ajout validation input, quality_score, stats tracking

        Args:
            data: Dictionnaire contenant toutes les données ML_READY
            symbol: Override symbol (optionnel)

        Returns:
            MarketContext avec plans de trading + quality_score
        """
        try:
            # ✨ V3.4: Validation input
            is_valid, error_msg = self.validate_ml_ready_data(data)
            if not is_valid:
                logger.error(f"[{self.symbol}] Données ML_READY invalides: {error_msg}")
                return self._create_empty_context()

            # ✨ V3.4: Stats tracking
            self.stats['total_analyses'] += 1

            # Override symbol si fourni
            if symbol:
                self.symbol = symbol

            mid_price = data.get('mid', 0)

            # 1. Analyser la position vs niveaux clés
            position_hvl = self._analyze_position_vs_hvl(data)
            position_vwap = self._analyze_position_vs_vwap(data)
            position_value_area = self._analyze_position_vs_value_area(data)

            # 2. Déterminer le biais principal
            main_bias = self._determine_main_bias(data)
            self.stats['by_bias'][main_bias] += 1  # ✨ V3.4

            # 3. Analyser l'orderflow
            orderflow_pressure = self._analyze_orderflow(data)

            # 4. Déterminer la condition gamma
            gamma_condition = self._determine_gamma_condition(data)
            self.stats['by_gamma'][gamma_condition] += 1  # ✨ V3.4

            # 5. Identifier les "aimants" (magnets)
            key_magnets = self._identify_magnets(data)

            # 6. Détecter les proximités critiques
            proximity_alerts = self._detect_proximity_alerts(data)

            # ═══════════════════════════════════════════════════════════════
            # 🚀 NOUVELLES INTÉGRATIONS PRO V3.3
            # ═══════════════════════════════════════════════════════════════

            # 6A. Détecter gamma flip (changement de condition)
            gamma_flip = self._detect_gamma_flip(data, gamma_condition)
            if gamma_flip:
                alert_msg = f"🔔 Gamma Flip {gamma_flip} → " + (
                    "retour zone stable (POSITIVE)" if gamma_flip == "UP"
                    else "risque accélération (NEGATIVE)"
                )
                proximity_alerts.insert(0, alert_msg)  # Prioritaire en tête

            # 6B. Calculer bias_strength quantifié
            bias_strength = self._calculate_bias_strength(data, main_bias, orderflow_pressure)

            # 6C. Générer visual zones pour dashboard
            visual_zones = self._generate_visual_zones(data)

            # 6D. Générer auto-signal (BUY/SELL/WAIT)
            auto_signal = self._generate_auto_signal(main_bias, orderflow_pressure, gamma_condition, bias_strength)

            # 6E. Construire summary KPIs pour dashboard
            summary = self._build_summary(data, main_bias, orderflow_pressure, gamma_condition)

            # ═══════════════════════════════════════════════════════════════
            # ✨ V3.4: QUALITY SCORE
            # ═══════════════════════════════════════════════════════════════

            quality_score = self._calculate_quality_score(
                data, bias_strength, orderflow_pressure, gamma_condition, proximity_alerts
            )

            # Update avg quality score (moving average)
            alpha = 0.1
            self.stats['avg_quality_score'] = (
                alpha * quality_score +
                (1 - alpha) * self.stats.get('avg_quality_score', quality_score)
            )

            # 7. Générer les plans de trading
            trading_plans = self._generate_trading_plans(data, main_bias, orderflow_pressure)
            self.stats['plans_generated'] += len(trading_plans)  # ✨ V3.4

            # 8. Générer le raisonnement
            reasoning = self._generate_reasoning(
                data, main_bias, orderflow_pressure,
                position_hvl, position_vwap, position_value_area
            )

            context = MarketContext(
                symbol=self.symbol,
                current_price=mid_price,
                position_vs_hvl=position_hvl,
                position_vs_vwap=position_vwap,
                position_vs_value_area=position_value_area,
                main_bias=main_bias,
                orderflow_pressure=orderflow_pressure,
                gamma_condition=gamma_condition,
                key_magnets=key_magnets,
                proximity_alerts=proximity_alerts,
                trading_plans=trading_plans,
                reasoning=reasoning,
                # 🚀 NOUVELLES FEATURES PRO
                bias_strength=bias_strength,
                auto_signal=auto_signal,
                visual_zones=visual_zones,
                gamma_flip_detected=gamma_flip,
                summary=summary
            )

            # ✨ V3.4: Ajouter quality_score au context
            context.quality_score = quality_score

            return context

        except Exception as e:
            logger.error(f"Erreur analyse contexte: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return self._create_empty_context()

    def _analyze_position_vs_hvl(self, data: Dict[str, Any]) -> str:
        """Analyser position vs HVL"""
        mid = data.get('mid', 0)
        hvl = data.get('hvl', 0)

        if not hvl or hvl == 0:
            return "unknown"

        diff = mid - hvl
        if abs(diff) < 2:
            return "at"
        elif diff > 0:
            return "above"
        else:
            return "below"

    def _analyze_position_vs_vwap(self, data: Dict[str, Any]) -> str:
        """Analyser position vs VWAP"""
        mid = data.get('mid', 0)
        vwap = data.get('vwap', 0)

        if not vwap or vwap == 0:
            return "unknown"

        diff = mid - vwap
        atr = data.get('atr', 1.0)

        if abs(diff) < atr * 0.5:
            return "at"
        elif diff > 0:
            return "above"
        else:
            return "below"

    def _analyze_position_vs_value_area(self, data: Dict[str, Any]) -> str:
        """Analyser position vs Value Area"""
        mid = data.get('mid', 0)
        vva = data.get('vva', {})
        vah = vva.get('vah', 0)
        val = vva.get('val', 0)

        if not vah or not val:
            return "unknown"

        if mid > vah:
            return "above"
        elif mid < val:
            return "below"
        else:
            return "inside"

    def _determine_main_bias(self, data: Dict[str, Any]) -> str:
        """Déterminer le biais principal (utilise mia_bullish_score du dumper)"""
        # Priorité : utiliser mia_bullish_score si disponible
        mia_score = data.get('mia_bullish_score')

        if mia_score is not None and mia_score != 0:
            # Score du dumper C++ (range: -1 à +1)
            if mia_score > 0.3:
                return "BULLISH"
            elif mia_score < -0.3:
                return "BEARISH"
            else:
                return "NEUTRAL"

        # Fallback : calcul manuel si mia_bullish_score absent
        logger.debug(f"[{self.symbol}] mia_bullish_score absent, calcul manuel du bias")
        score = 0

        # Delta VWAP
        d_vwap_atr = data.get('d_vwap_atr', 0)
        if d_vwap_atr > 1.0:
            score += 2
        elif d_vwap_atr > 0.3:
            score += 1
        elif d_vwap_atr < -1.0:
            score -= 2
        elif d_vwap_atr < -0.3:
            score -= 1

        # Order Flow
        delta_pct = data.get('deltaPct', 0.5)
        if delta_pct > 0.6:
            score += 1
        elif delta_pct < 0.4:
            score -= 1

        # Position vs Value Area
        vva = data.get('vva', {})
        mid = data.get('mid', 0)
        vah = vva.get('vah', 0)
        val = vva.get('val', 0)

        if vah and val:
            if mid > vah:
                score += 1
            elif mid < val:
                score -= 1

        if score >= 2:
            return "BULLISH"
        elif score <= -2:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _analyze_orderflow(self, data: Dict[str, Any]) -> str:
        """Analyser la pression de l'orderflow"""
        delta_pct = data.get('deltaPct', 0.5)
        cum_delta = data.get('cum_delta_session', 0)

        # Pression courante
        if delta_pct > 0.65:
            current_pressure = "BUYING"
        elif delta_pct < 0.35:
            current_pressure = "SELLING"
        else:
            current_pressure = "BALANCED"

        # Confirmer avec delta cumulé
        if cum_delta > 500:
            return "BUYING"
        elif cum_delta < -500:
            return "SELLING"
        else:
            return current_pressure

    def _determine_gamma_condition(self, data: Dict[str, Any]) -> str:
        """
        Déterminer condition gamma selon Bible MenthorQ v2.0

        📚 BIBLE MENTHORQ (priorité HVL):
        - Prix AU-DESSUS HVL = POSITIVE GAMMA (mean-revert, dealers stabilisent)
        - Prix AU-DESSOUS HVL = NEGATIVE GAMMA (directionnel, dealers amplifient)

        Fallback (si HVL absent): Logique GEX up/dn
        """
        mid = data.get('mid', 0)
        hvl = data.get('hvl', 0)

        # ✅ MÉTHODE BIBLE MENTHORQ (prioritaire si HVL disponible)
        if hvl > 0 and mid > 0:
            if mid > hvl:
                logger.debug(f"[{self.symbol}] 📚 Bible MenthorQ: Prix {mid:.2f} > HVL {hvl:.2f} → POSITIVE GAMMA")
                return "POSITIVE"  # Au-dessus HVL = Positive Gamma (mean-revert)
            else:
                logger.debug(f"[{self.symbol}] 📚 Bible MenthorQ: Prix {mid:.2f} < HVL {hvl:.2f} → NEGATIVE GAMMA")
                return "NEGATIVE"  # Au-dessous HVL = Negative Gamma (directionnel)

        # ⚠️ FALLBACK: Logique GEX (si HVL absent)
        logger.debug(f"[{self.symbol}] ⚠️ HVL absent, utilisation fallback GEX")
        atr = max(float(data.get('atr', 1.0)), 0.5)
        md = data.get('menthor_distances', {})
        up, dn = md.get('near_gex_up'), md.get('near_gex_dn')

        if up is not None and dn is not None and abs(up) < 2*atr and abs(dn) < 2*atr:
            return "POSITIVE"  # Market pinné entre les murs

        if (up is not None and abs(up) < 1.5*atr and (dn is None or abs(dn) > 3*atr)) \
           or (dn is not None and abs(dn) < 1.5*atr and (up is None or abs(up) > 3*atr)):
            return "NEGATIVE"  # Asymétrie gamma -> breakout potentiel

        return "NEUTRAL"

    def _identify_magnets(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identifier les niveaux 'aimants' (magnets)"""
        magnets = []
        mid = data.get('mid', 0)

        # HVL
        hvl = data.get('hvl', 0)
        if hvl:
            magnets.append({
                'type': 'HVL',
                'price': hvl,
                'distance': hvl - mid,
                'strength': 'high',
                'description': 'High Volume Level (aimant principal)'
            })

        # VWAP
        vwap = data.get('vwap', 0)
        if vwap:
            magnets.append({
                'type': 'VWAP',
                'price': vwap,
                'distance': vwap - mid,
                'strength': 'high',
                'description': 'Volume Weighted Average Price'
            })

        # VPOC
        vva = data.get('vva', {})
        vpoc = vva.get('vpoc', 0)
        if vpoc:
            magnets.append({
                'type': 'VPOC',
                'price': vpoc,
                'distance': vpoc - mid,
                'strength': 'medium',
                'description': 'Volume Point of Control'
            })

        # GEX Walls
        call_resist = data.get('call_resistance', 0)
        put_support = data.get('put_support', 0)

        if call_resist:
            magnets.append({
                'type': 'CALL_WALL',
                'price': call_resist,
                'distance': call_resist - mid,
                'strength': 'high',
                'description': 'Call Gamma Wall (résistance)'
            })

        if put_support:
            magnets.append({
                'type': 'PUT_WALL',
                'price': put_support,
                'distance': put_support - mid,
                'strength': 'high',
                'description': 'Put Gamma Wall (support)'
            })

        # Trier par distance absolue
        magnets.sort(key=lambda x: abs(x['distance']))

        return magnets

    def _analyze_next_wall(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse Next Wall selon Bible MenthorQ v2.0

        📚 BIBLE MENTHORQ:
        - Put Wall = Support (LONG bias si proche)
        - Call Wall = Résistance (SHORT bias si proche)

        Returns:
            Dict avec side, distance, strength, interpretation
        """
        next_wall = data.get('next_wall', {})

        if not next_wall or not isinstance(next_wall, dict):
            return {
                'side': 'UNKNOWN',
                'distance': 999,
                'strength': 0.0,
                'interpretation': 'Next Wall absent'
            }

        wall_side = next_wall.get('side', 'UNKNOWN')
        wall_dist = next_wall.get('dist_ticks', 999)
        wall_strength = next_wall.get('strength', 0.5)
        wall_price = next_wall.get('price', 0)

        # 📚 Bible MenthorQ: interprétation classique
        if wall_side == 'put':
            interpretation = f"📚 Put Wall @ {wall_price:.2f} ({wall_dist}t) → SUPPORT structurel (bias LONG si proche)"
        elif wall_side == 'call':
            interpretation = f"📚 Call Wall @ {wall_price:.2f} ({wall_dist}t) → RÉSISTANCE structurelle (bias SHORT si proche)"
        else:
            interpretation = "Next Wall non déterminé"

        logger.debug(f"[{self.symbol}] {interpretation}")

        return {
            'side': wall_side,
            'distance': wall_dist,
            'strength': wall_strength,
            'interpretation': interpretation
        }

    def _detect_gex_confluence(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Détecte les GEX levels en confluence avec CR/PS/HVL

        📚 BIBLE MENTHORQ V2.0: "GEX EXTRA-PUISSANT en confluence"

        Returns:
            Liste de confluences détectées
        """
        confluences = []

        cr = data.get('call_resistance', 0)
        ps = data.get('put_support', 0)
        hvl = data.get('hvl', 0)
        tick_size = self._get_tick_size(data)

        # Parcourir les 10 GEX levels
        for i in range(1, 11):
            gex = data.get(f'gex_{i}', 0)
            if gex == 0:
                continue

            # Vérifier distance à CR/PS/HVL
            gex_to_cr = abs(gex - cr) / tick_size if cr > 0 else 999
            gex_to_ps = abs(gex - ps) / tick_size if ps > 0 else 999
            gex_to_hvl = abs(gex - hvl) / tick_size if hvl > 0 else 999

            min_dist = min(gex_to_cr, gex_to_ps, gex_to_hvl)

            # 📚 Bible: confluence si < 15 ticks
            if min_dist < 15:
                confluent_with = []
                if gex_to_cr < 15:
                    confluent_with.append(f"CR ({cr:.2f})")
                if gex_to_ps < 15:
                    confluent_with.append(f"PS ({ps:.2f})")
                if gex_to_hvl < 15:
                    confluent_with.append(f"HVL ({hvl:.2f})")

                confluences.append({
                    'gex_level': f'gex_{i}',
                    'gex_price': gex,
                    'confluent_with': confluent_with,
                    'strength': 'EXTRA-PUISSANT',
                    'interpretation': f"📚 Bible MenthorQ: GEX_{i} @ {gex:.2f} en confluence avec {', '.join(confluent_with)} → ZONE MAJEURE !"
                })

                logger.info(f"[{self.symbol}] ✅✅ {confluences[-1]['interpretation']}")

        return confluences

    def _analyze_0dte_levels(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse niveaux 0DTE selon Bible MenthorQ v2.0

        📚 PARTICULARITÉS 0DTE:
        - Hedging plus AGRESSIF (échéance proche)
        - Pinning fréquent à l'expiration
        - Aimant intraday plus fort

        Returns:
            Dict avec call_0dte, put_0dte, hvl_0dte, gamma_wall_0dte, interpretation
        """
        # ✅ FIX 05/12/2025: Utiliser les bonnes clés du snapshot (minuscules)
        # Les données 0DTE sont maintenant des champs séparés, pas un dictionnaire
        call_0dte = data.get('call_resistance_0dte', 0)
        put_0dte = data.get('put_support_0dte', 0)
        hvl_0dte = data.get('hvl_0dte', 0)
        gamma_wall_0dte = data.get('gamma_wall_0dte', 0)

        if not call_0dte and not put_0dte and not hvl_0dte and not gamma_wall_0dte:
            return {
                'call_0dte': None,
                'put_0dte': None,
                'hvl_0dte': None,
                'gamma_wall_0dte': None,
                'interpretation': 'Pas de niveaux 0DTE détectés'
            }

        mid = data.get('mid', 0)
        tick_size = self._get_tick_size(data)

        interpretations = []

        if call_0dte > 0:
            dist = abs(mid - call_0dte) / tick_size
            if dist < 25:
                interpretations.append(
                    f"📚 Bible MenthorQ: Call 0DTE @ {call_0dte:.2f} ({dist:.0f}t) - "
                    f"RÉSISTANCE intraday MAGNÉTIQUE ! Pinning fréquent, hedging agressif"
                )

        if put_0dte > 0:
            dist = abs(mid - put_0dte) / tick_size
            if dist < 25:
                interpretations.append(
                    f"📚 Bible MenthorQ: Put 0DTE @ {put_0dte:.2f} ({dist:.0f}t) - "
                    f"SUPPORT intraday MAGNÉTIQUE ! Pinning fréquent, hedging agressif"
                )

        # Analyser gamma_wall_0dte aussi
        if gamma_wall_0dte > 0:
            dist = abs(mid - gamma_wall_0dte) / tick_size
            if dist < 25:
                interpretations.append(
                    f"📚 Bible MenthorQ: Gamma Wall 0DTE @ {gamma_wall_0dte:.2f} ({dist:.0f}t) - "
                    f"MUR GAMMA intraday ! Pinning effect maximal"
                )

        logger.debug(f"[{self.symbol}] 0DTE: {' | '.join(interpretations) if interpretations else 'Niveaux 0DTE loin'}")

        return {
            'call_0dte': call_0dte,
            'put_0dte': put_0dte,
            'hvl_0dte': hvl_0dte,
            'gamma_wall_0dte': gamma_wall_0dte,
            'interpretation': ' | '.join(interpretations) if interpretations else 'Niveaux 0DTE loin'
        }

    def _analyze_daily_extremes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse 1-Day Max/Min selon Bible MenthorQ v2.0

        📚 BORNES QUOTIDIENNES:
        - Résistance psychologique en haut (1-Day Max)
        - Support psychologique en bas (1-Day Min)

        Returns:
            Dict avec max, min, dist_to_max, dist_to_min, interpretation
        """
        day_max = data.get('1_day_max', 0)
        day_min = data.get('1_day_min', 0)
        mid = data.get('mid', 0)
        atr = data.get('atr', 1.0)

        if day_max == 0 or day_min == 0:
            return {
                'max': None,
                'min': None,
                'interpretation': '1-Day Max/Min non disponibles'
            }

        dist_to_max = abs(mid - day_max)
        dist_to_min = abs(mid - day_min)

        interpretations = []

        if dist_to_max < 0.5 * atr:
            interpretations.append(
                f"📚 Bible MenthorQ: PROCHE 1-Day MAX ({day_max:.2f}) - "
                f"Résistance psychologique FORTE ! Risque de rejet"
            )

        if dist_to_min < 0.5 * atr:
            interpretations.append(
                f"📚 Bible MenthorQ: PROCHE 1-Day MIN ({day_min:.2f}) - "
                f"Support psychologique FORT ! Rebond probable"
            )

        logger.debug(f"[{self.symbol}] 1-Day Extremes: {' | '.join(interpretations) if interpretations else 'Loin des extrêmes'}")

        return {
            'max': day_max,
            'min': day_min,
            'dist_to_max': dist_to_max,
            'dist_to_min': dist_to_min,
            'interpretation': ' | '.join(interpretations) if interpretations else 'Loin des extrêmes quotidiens'
        }

    def _detect_proximity_alerts(self, data: Dict[str, Any]) -> List[str]:
        """Détecter les alertes de proximité (seuils en ATR)"""
        alerts = []
        mid = data.get('mid', 0.0)
        atr = max(float(data.get('atr', 1.0)), 0.5)

        # Proximité HVL
        hvl = data.get('hvl')
        if hvl and abs(mid - hvl) < 0.5 * atr:
            alerts.append(f"⚠️ TRÈS PROCHE DE HVL ({hvl:.2f}) - Zone de décision clé (<0.5 ATR) !")

        # Proximité Value Area
        vva = data.get('vva', {})
        val = vva.get('val')
        vah = vva.get('vah')

        if val and abs(mid - val) < 0.4 * atr:
            alerts.append(f"📊 Test VAL ({val:.2f}) - Support critique (<0.4 ATR) !")

        if vah and abs(mid - vah) < 0.4 * atr:
            alerts.append(f"📊 Test VAH ({vah:.2f}) - Résistance critique (<0.4 ATR) !")

        # Proximité GEX
        md = data.get('menthor_distances', {})
        near_gex_up = md.get('near_gex_up')
        near_gex_dn = md.get('near_gex_dn')

        if near_gex_up is not None and abs(near_gex_up) < 1.0 * atr:
            gex_price = mid + near_gex_up
            alerts.append(f"🔺 GEX Wall au-dessus à {gex_price:.2f} (~{abs(near_gex_up):.2f} pts, <1 ATR) - Résistance gamma !")

        if near_gex_dn is not None and abs(near_gex_dn) < 1.0 * atr:
            gex_price = mid + near_gex_dn
            alerts.append(f"🔻 GEX Wall en-dessous à {gex_price:.2f} (~{abs(near_gex_dn):.2f} pts, <1 ATR) - Support gamma !")

        # Proximité Blind Spot
        # ⚠️⚠️⚠️ BIBLE MENTHORQ V2.0 - AVERTISSEMENT CRITIQUE:
        # NE JAMAIS trader Blind Spot SEUL sans validation orderflow ABSOLUMENT
        near_blind = md.get('near_blind')
        if near_blind is not None and abs(near_blind) < 0.8 * atr:
            blind_price = mid + near_blind
            alerts.append(
                f"⚠️⚠️⚠️ BLIND SPOT IMMÉDIAT ({blind_price:.2f}, {abs(near_blind):.2f}pts) - "
                f"DANGER ABSOLU ! NE JAMAIS trader SEUL sans validation orderflow (delta/volume/DOM) OBLIGATOIRE ! "
                f"Attention rebond/cassure violent (<0.8 ATR) !"
            )

        return alerts

    def _generate_trading_plans(
        self,
        data: Dict[str, Any],
        main_bias: str,
        orderflow_pressure: str
    ) -> List[TradingPlan]:
        """Générer les plans de trading automatiques"""
        plans = []

        # Filtre horaire (éviter mid-day chop)
        if not self._time_filter_ok(data.get('tsec')):
            logger.debug("Plans de trading désactivés hors horaires de trading optimaux")
            return []

        mid = data.get('mid', 0)
        atr = data.get('atr', 1.0)

        # Garde-fous: Skip si niveaux clés manquants (évite "mid fallback")
        hvl = data.get('hvl')
        vwap = data.get('vwap')
        vva = data.get('vva', {})
        val, vah = vva.get('val'), vva.get('vah')

        call_resist = data.get('call_resistance')
        put_support = data.get('put_support')

        has_va = (val is not None and vah is not None)
        if hvl is None or vwap is None or not has_va:
            logger.warning("Niveaux structurants manquants (HVL/VWAP/VA) - Skip plans de trading")
            return []

        # Plan 1: Continuation du biais principal
        if main_bias == "BEARISH":
            scenario = TradingScenario.CONTINUATION_BEARISH
            if self._cooldown_ok(scenario):
                plan = self._create_continuation_bearish_plan(
                    data, mid, atr, hvl, val, put_support, orderflow_pressure
                )
                if plan:
                    plans.append(plan)
        elif main_bias == "BULLISH":
            scenario = TradingScenario.CONTINUATION_BULLISH
            if self._cooldown_ok(scenario):
                plan = self._create_continuation_bullish_plan(
                    data, mid, atr, hvl, vah, call_resist, orderflow_pressure
                )
                if plan:
                    plans.append(plan)

        # Plan 2: Fade de la résistance (si proche)
        if mid > hvl and abs(mid - vah) < atr * 2:
            scenario = TradingScenario.FADE_RESISTANCE
            if self._cooldown_ok(scenario):
                plan = self._create_fade_resistance_plan(data, mid, atr, vah, hvl, call_resist)
                if plan:
                    plans.append(plan)

        # Plan 3: Fade du support (si proche)
        if mid < hvl and abs(mid - val) < atr * 2:
            scenario = TradingScenario.FADE_SUPPORT
            if self._cooldown_ok(scenario):
                plan = self._create_fade_support_plan(data, mid, atr, val, hvl, put_support)
                if plan:
                    plans.append(plan)

        # Trier par priorité
        plans.sort(key=lambda x: x.priority)

        return plans[:3]  # Max 3 plans

    def _create_continuation_bearish_plan(
        self, data, mid, atr, hvl, val, put_support, orderflow
    ) -> Optional[TradingPlan]:
        """Plan de continuation baissière"""
        # Utiliser niveaux réels pour TPs
        md = data.get('menthor_distances', {})

        # Zone d'entrée
        entry_high = mid + atr * 0.5
        entry_low = mid - atr * 0.5
        entry_zone = (entry_low, entry_high)

        # SL
        sl = entry_high + atr * 1.5

        # TP1: VAL ou blind spot le plus proche
        near_blind_dn = md.get('near_blind')
        tp1 = val if val < mid else mid - atr * 2
        if near_blind_dn and near_blind_dn < 0 and abs(near_blind_dn) < abs(val - mid):
            tp1 = mid + near_blind_dn

        # TP2: Put Support ou GEX proche
        near_gex_dn = md.get('near_gex_dn')
        tp2 = put_support if put_support and put_support < tp1 else mid - atr * 4
        if near_gex_dn and near_gex_dn < 0:
            gex_level = mid + near_gex_dn
            if gex_level < tp1 and gex_level > tp2:
                tp2 = gex_level

        # TP3: Extension
        tp3 = mid - atr * 6

        # Appliquer buffers et snap
        sl, tp_list = self._apply_sane_buffers(data, entry_zone, sl, [tp1, tp2, tp3])
        tp1, tp2, tp3 = tp_list

        # Recalculer RR
        rr = self._rr_from_entry_zone(entry_zone, sl, tp1)

        # Confiance avec confluence
        base_conf = 0.7 if orderflow == "SELLING" else 0.5

        # === PATCH V1: Boost confiance si delta_flip détecté (retournement) ===
        delta_flip = data.get('delta_flip', False)
        flip_boost = 0.12 if delta_flip else 0.0

        base_confidence = max(0.1, min(0.95, base_conf + self._confluence_boost(data) + flip_boost))

        # 🚀 PATCH V3.3: Ajustement contextuel (volatilité + gamma)
        confidence = self._contextual_confidence_adjust(data, base_confidence, "CONTINUATION_BEARISH")

        return TradingPlan(
            scenario=TradingScenario.CONTINUATION_BEARISH,
            direction="SHORT",
            priority=1,
            trigger=f"Échec sous HVL {hvl:.2f} + footprint rouge (delta < 0) OU cassure nette sous {entry_low:.2f}",
            entry_zone=entry_zone,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=rr,
            invalidation=f"Clôture > {sl:.2f} ou réintégration HVL avec delta positif",
            management="BE à +1.5 ATR ; 50% sur TP1, runner vers TP2/TP3",
            confidence=confidence
        )

    def _create_continuation_bullish_plan(
        self, data, mid, atr, hvl, vah, call_resist, orderflow
    ) -> Optional[TradingPlan]:
        """Plan de continuation haussière"""
        # Utiliser niveaux réels pour TPs
        md = data.get('menthor_distances', {})

        # Zone d'entrée
        entry_low = mid - atr * 0.5
        entry_high = mid + atr * 0.5
        entry_zone = (entry_low, entry_high)

        # SL
        sl = entry_low - atr * 1.5

        # TP1: VAH ou blind spot le plus proche
        near_blind_up = md.get('near_blind')
        tp1 = vah if vah > mid else mid + atr * 2
        if near_blind_up and near_blind_up > 0 and abs(near_blind_up) < abs(vah - mid):
            tp1 = mid + near_blind_up

        # TP2: Call Resistance ou GEX proche
        near_gex_up = md.get('near_gex_up')
        tp2 = call_resist if call_resist and call_resist > tp1 else mid + atr * 4
        if near_gex_up and near_gex_up > 0:
            gex_level = mid + near_gex_up
            if gex_level > tp1 and gex_level < tp2:
                tp2 = gex_level

        # TP3: Extension
        tp3 = mid + atr * 6

        # Appliquer buffers et snap
        sl, tp_list = self._apply_sane_buffers(data, entry_zone, sl, [tp1, tp2, tp3])
        tp1, tp2, tp3 = tp_list

        # Recalculer RR
        rr = self._rr_from_entry_zone(entry_zone, sl, tp1)

        # Confiance avec confluence
        base_conf = 0.7 if orderflow == "BUYING" else 0.5

        # === PATCH V1: Boost confiance si delta_flip détecté (retournement) ===
        delta_flip = data.get('delta_flip', False)
        flip_boost = 0.12 if delta_flip else 0.0

        base_confidence = max(0.1, min(0.95, base_conf + self._confluence_boost(data) + flip_boost))

        # 🚀 PATCH V3.3: Ajustement contextuel (volatilité + gamma)
        confidence = self._contextual_confidence_adjust(data, base_confidence, "CONTINUATION_BULLISH")

        return TradingPlan(
            scenario=TradingScenario.CONTINUATION_BULLISH,
            direction="LONG",
            priority=1,
            trigger=f"Absorption vendeuse + réintégration HVL {hvl:.2f} avec delta positif",
            entry_zone=entry_zone,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=rr,
            invalidation=f"Clôture < {sl:.2f} ou retour sous HVL avec delta négatif",
            management="BE à +1.5 ATR ; 50% sur TP1, runner vers TP2/TP3",
            confidence=confidence
        )

    def _create_fade_resistance_plan(
        self, data, mid, atr, vah, hvl, call_resist
    ) -> Optional[TradingPlan]:
        """Plan de fade de résistance (pop & drop)"""
        # Zone d'entrée autour de VAH
        entry_low = vah - atr * 0.5
        entry_high = min(vah + atr * 0.5, call_resist - atr * 0.5) if call_resist else vah + atr * 0.5
        entry_zone = (entry_low, entry_high)

        # SL
        sl = entry_high + atr * 1.5

        # TPs
        tp1 = hvl
        tp2 = hvl - atr * 2
        tp3 = hvl - atr * 4

        # Appliquer buffers et snap
        sl, tp_list = self._apply_sane_buffers(data, entry_zone, sl, [tp1, tp2, tp3])
        tp1, tp2, tp3 = tp_list

        # Recalculer RR
        rr = self._rr_from_entry_zone(entry_zone, sl, tp1)

        # Confiance avec confluence
        base_conf = 0.6

        # === PATCH V1: Boost confiance si mèche haute détectée ===
        upper_wick = data.get('upper_wick_ticks', 0)
        wick_boost = 0.0
        wick_strength = "faible"

        if upper_wick > 5:
            wick_boost = 0.15  # Grosse mèche = fort rejet
            wick_strength = "forte"
        elif upper_wick > 2:
            wick_boost = 0.08  # Mèche moyenne
            wick_strength = "moyenne"

        base_confidence = max(0.1, min(0.95, base_conf + self._confluence_boost(data) + wick_boost))

        # 🚀 PATCH V3.3: Ajustement contextuel (volatilité + gamma)
        confidence = self._contextual_confidence_adjust(data, base_confidence, "FADE_RESISTANCE")

        # Trigger enrichi avec info mèche
        if upper_wick > 2:
            trigger_text = f"Rebond à VAH {vah:.2f} + mèche haute {wick_strength} ({upper_wick:.0f} ticks) → Rejet confirmé"
        else:
            trigger_text = f"Rebond à VAH {vah:.2f} + absorption acheteuse"

        return TradingPlan(
            scenario=TradingScenario.FADE_RESISTANCE,
            direction="SHORT",
            priority=2,
            trigger=trigger_text,
            entry_zone=entry_zone,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=rr,
            invalidation=f"Clôture > {sl:.2f} avec delta acheteur soutenu",
            management="BE à +1.0 ATR ; fade agressif si échec rapide",
            confidence=confidence
        )

    def _create_fade_support_plan(
        self, data, mid, atr, val, hvl, put_support
    ) -> Optional[TradingPlan]:
        """Plan de fade de support (dip & rip)"""
        # Zone d'entrée autour de VAL
        entry_high = val + atr * 0.5
        entry_low = max(val - atr * 0.5, put_support + atr * 0.5) if put_support else val - atr * 0.5
        entry_zone = (entry_low, entry_high)

        # SL
        sl = entry_low - atr * 1.5

        # TPs
        tp1 = hvl
        tp2 = hvl + atr * 2
        tp3 = hvl + atr * 4

        # Appliquer buffers et snap
        sl, tp_list = self._apply_sane_buffers(data, entry_zone, sl, [tp1, tp2, tp3])
        tp1, tp2, tp3 = tp_list

        # Recalculer RR
        rr = self._rr_from_entry_zone(entry_zone, sl, tp1)

        # Confiance avec confluence
        base_conf = 0.6

        # === PATCH V1: Boost confiance si mèche basse détectée ===
        lower_wick = data.get('lower_wick_ticks', 0)
        wick_boost = 0.0
        wick_strength = "faible"

        if lower_wick > 5:
            wick_boost = 0.15  # Grosse mèche = fort rejet vers le bas
            wick_strength = "forte"
        elif lower_wick > 2:
            wick_boost = 0.08  # Mèche moyenne
            wick_strength = "moyenne"

        base_confidence = max(0.1, min(0.95, base_conf + self._confluence_boost(data) + wick_boost))

        # 🚀 PATCH V3.3: Ajustement contextuel (volatilité + gamma)
        confidence = self._contextual_confidence_adjust(data, base_confidence, "FADE_SUPPORT")

        # Trigger enrichi avec info mèche
        if lower_wick > 2:
            trigger_text = f"Mèche basse {wick_strength} ({lower_wick:.0f} ticks) sous VAL {val:.2f} → Support confirmé"
        else:
            trigger_text = f"Mèche sous VAL {val:.2f} + absorption vendeuse (retournement delta)"

        return TradingPlan(
            scenario=TradingScenario.FADE_SUPPORT,
            direction="LONG",
            priority=2,
            trigger=trigger_text,
            entry_zone=entry_zone,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward=rr,
            invalidation=f"Clôture < {sl:.2f} avec delta vendeur accéléré",
            management="BE à +1.0 ATR ; fade agressif si rebond technique",
            confidence=confidence
        )

    def _generate_reasoning(
        self,
        data: Dict[str, Any],
        main_bias: str,
        orderflow: str,
        pos_hvl: str,
        pos_vwap: str,
        pos_va: str
    ) -> str:
        """Générer l'explication du raisonnement"""
        mid = data.get('mid', 0)
        d_vwap = data.get('d_vwap', 0)
        d_vwap_atr = data.get('d_vwap_atr', 0)
        delta_pct = data.get('deltaPct', 0.5)
        cum_delta = data.get('cum_delta_session', 0)

        reasoning_parts = []

        # Position générale
        if pos_va == "below":
            reasoning_parts.append(f"🔴 Prix {mid:.2f} SOUS Value Area → Biais vendeur tant qu'on ne réintègre pas VAL.")
        elif pos_va == "above":
            reasoning_parts.append(f"🟢 Prix {mid:.2f} AU-DESSUS Value Area → Biais acheteur tant qu'on tient au-dessus VAH.")
        else:
            reasoning_parts.append(f"⚪ Prix {mid:.2f} DANS Value Area → Zone d'équilibre, attendre cassure/confirmation.")

        # Position vs VWAP
        if abs(d_vwap_atr) > 1.0:
            direction = "AU-DESSUS" if d_vwap_atr > 0 else "EN-DESSOUS"
            reasoning_parts.append(f"📊 VWAP {direction} de {abs(d_vwap_atr):.1f} ATR → Écart fort, aimant de retour potentiel.")

        # Order Flow
        if delta_pct > 0.6:
            reasoning_parts.append(f"💪 Order Flow ACHETEUR (delta {delta_pct:.1%}, cum: {cum_delta}) → Pression haussière.")
        elif delta_pct < 0.4:
            reasoning_parts.append(f"📉 Order Flow VENDEUR (delta {delta_pct:.1%}, cum: {cum_delta}) → Pression baissière.")
        else:
            reasoning_parts.append(f"⚖️ Order Flow ÉQUILIBRÉ (delta {delta_pct:.1%}) → Pas de pression dominante.")

        # Conclusion
        if main_bias == "BEARISH":
            reasoning_parts.append(f"🎯 CONCLUSION: BIAIS SHORT privilégié. Chercher fades de résistance ou continuation baissière.")
        elif main_bias == "BULLISH":
            reasoning_parts.append(f"🎯 CONCLUSION: BIAIS LONG privilégié. Chercher fades de support ou continuation haussière.")
        else:
            reasoning_parts.append(f"🎯 CONCLUSION: BIAIS NEUTRE. Attendre confirmations claires avant entrée.")

        return " | ".join(reasoning_parts)

    def _create_empty_context(self) -> MarketContext:
        """Créer un contexte vide en cas d'erreur"""
        return MarketContext(
            symbol=self.symbol,
            current_price=0.0,
            position_vs_hvl="unknown",
            position_vs_vwap="unknown",
            position_vs_value_area="unknown",
            main_bias="NEUTRAL",
            orderflow_pressure="BALANCED",
            gamma_condition="NEUTRAL",
            key_magnets=[],
            proximity_alerts=["⚠️ Données insuffisantes pour analyse"],
            trading_plans=[],
            reasoning="Impossible d'analyser le contexte (données manquantes)",
            # 🚀 NOUVELLES FEATURES PRO
            bias_strength=0.0,
            auto_signal="WAIT",
            visual_zones=[],
            gamma_flip_detected=None,
            summary={}
        )


def create_market_context_analyzer(symbol: str = "ES") -> MarketContextAnalyzer:
    """Factory function pour créer un analyseur"""
    return MarketContextAnalyzer(symbol=symbol)
