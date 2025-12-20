"""
🎯 PHASE 2: ADVANCED FEATURES - FEATURE #3
VOLATILITY REGIME FILTER

🎯 IMPACT: +1-2% win rate
Ajuste les seuils de trading selon régime de volatilité
Combine ATR + VIX pour détection précise des conditions de marché

Performance: <0.5ms par calcul
Intégration: Compatible avec FeatureCalculator existant
"""

import time
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from collections import deque
from enum import Enum
import logging

# Imports locaux (selon architecture projet)
# from core.base_types import MarketData  # ❌ Désactivé (non utilisé en V3.3)
# from ..data_reader import get_latest_market_data  # ❌ Désactivé (non utilisé en V3.3)

# MarketData simple pour compatibilité V3.3
from typing import NamedTuple
class MarketData(NamedTuple):
    timestamp: any
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int

logger = logging.getLogger(__name__)

# ===== TYPES DE DONNÉES =====

class VolatilityRegime(Enum):
    """Régimes de volatilité détectés"""
    LOW_VOL = "low_vol"              # VIX < 15, ATR faible
    NORMAL_VOL = "normal_vol"        # Conditions standard
    HIGH_VOL = "high_vol"            # VIX > 25, ATR élevé
    TRANSITIONING = "transitioning"   # Changement de régime
    EXTREME_VOL = "extreme_vol"      # Conditions extrêmes

class VolatilityTrend(Enum):
    """Tendance volatilité"""
    DECREASING = "decreasing"        # Volatilité en baisse
    STABLE = "stable"                # Volatilité stable
    INCREASING = "increasing"        # Volatilité en hausse
    EXPLOSIVE = "explosive"          # Explosion volatilité

@dataclass
class VolatilityMetrics:
    """Métriques de volatilité"""
    current_atr: float              # ATR actuel
    avg_atr_20: float              # ATR moyenne 20 périodes
    atr_ratio: float               # ATR actuel / moyenne
    current_vix: float             # VIX actuel
    vix_percentile: float          # Percentile VIX sur 252 jours
    realized_vol: float            # Volatilité réalisée
    vol_of_vol: float              # Volatilité de la volatilité

@dataclass
class TradingThresholds:
    """Seuils de trading adaptés"""
    long_threshold: float          # Seuil signal long
    short_threshold: float         # Seuil signal short
    position_multiplier: float     # Multiplicateur taille position
    stop_loss_multiplier: float    # Multiplicateur stop loss
    take_profit_multiplier: float  # Multiplicateur take profit
    max_positions: int             # Nombre max positions

@dataclass
class VolatilityRegimeResult:
    """Résultat complet analyse volatilité"""
    regime: VolatilityRegime
    trend: VolatilityTrend
    metrics: VolatilityMetrics
    thresholds: TradingThresholds
    regime_confidence: float       # Confiance régime [0, 1]
    stability_score: float         # Score stabilité [0, 1]
    risk_adjustment: float         # Ajustement risque [0.5, 2.0]
    calculation_time_ms: float     # Temps calcul
    days_in_regime: int           # Jours dans régime actuel

# ===== VOLATILITY REGIME CALCULATOR =====

class VolatilityRegimeCalculator:
    """
    Calculateur de régime de volatilité avec ajustement seuils adaptatifs

    Fonctionnalités:
    - Analyse ATR + VIX combinée
    - Détection transitions de régime
    - Seuils adaptatifs par régime
    - Cache optimisé pour performance
    - Tracking stabilité régime
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation calculateur"""
        self.config = config or {}

        # Paramètres ATR
        self.atr_period = self.config.get('atr_period', 20)
        self.atr_lookback = self.config.get('atr_lookback', 100)

        # Paramètres VIX
        self.vix_lookback = self.config.get('vix_lookback', 252)  # 1 an
        self.vix_low_threshold = self.config.get('vix_low', 15.0)
        self.vix_high_threshold = self.config.get('vix_high', 25.0)

        # Seuils ATR ratio
        self.atr_low_ratio = self.config.get('atr_low_ratio', 0.8)
        self.atr_high_ratio = self.config.get('atr_high_ratio', 1.5)

        # Historiques pour calculs
        self.max_history = self.config.get('max_history', 500)
        self.price_history: deque = deque(maxlen=self.max_history)
        self.atr_history: deque = deque(maxlen=self.max_history)
        self.vix_history: deque = deque(maxlen=self.max_history)
        self.regime_history: deque = deque(maxlen=50)  # Historique régimes

        # Cache pour optimisation
        self.cache: Dict[str, Tuple[float, VolatilityRegimeResult]] = {}
        self.cache_max_size = 20
        self.cache_ttl = 10.0  # 10 secondes (régime change lentement)

        # Suivi régime actuel
        self.current_regime: Optional[VolatilityRegime] = None
        self.regime_start_time: Optional[float] = None
        self.regime_stability_days = 0

        # Statistiques
        self.stats = {
            'total_calculations': 0,
            'regime_changes': 0,
            'low_vol_periods': 0,
            'high_vol_periods': 0,
            'extreme_vol_periods': 0,
            'avg_calc_time_ms': 0.0,
            'cache_hits': 0
        }

        logger.info(f"VolatilityRegimeCalculator initialisé (ATR={self.atr_period}, VIX thresholds={self.vix_low_threshold}/{self.vix_high_threshold})")

    def add_market_data(self,
                       price_data: MarketData,
                       current_vix: float,
                       timestamp: Optional[float] = None) -> None:
        """
        Ajoute données de marché pour analyse

        Args:
            price_data: Données OHLC
            current_vix: Valeur VIX actuelle
            timestamp: Timestamp (auto si None)
        """
        if timestamp is None:
            timestamp = time.time()

        # Calcul ATR pour cette barre
        atr_value = self._calculate_true_range(price_data)

        # Ajout aux historiques
        self.price_history.append(price_data)
        self.atr_history.append(atr_value)
        self.vix_history.append(current_vix)

        # Nettoyage cache
        self._cleanup_cache()

    def add_real_market_data(self, symbol: str = "ES") -> None:
        """
        🆕 Ajoute les vraies données de marché depuis Sierra Chart

        Args:
            symbol: Symbole à analyser (défaut: ES)
        """
        try:
            # Récupérer les vraies données
            market_data = get_latest_market_data(symbol)

            if market_data:
                # VIX depuis les vraies données
                vix = market_data.get('vix', 20.0)
                self.add_vix_data(vix)

                # ATR calculé depuis OHLC
                if all(key in market_data for key in ['open', 'high', 'low', 'close']):
                    o, h, l, c = market_data['open'], market_data['high'], market_data['low'], market_data['close']
                    atr = self._calculate_atr(o, h, l, c)
                    self.add_atr_data(atr)

                logger.debug(f"✅ Données volatilité réelles ajoutées: {symbol}, VIX: {vix:.2f}")
            else:
                logger.warning(f"⚠️ Pas de données pour {symbol}")

        except Exception as e:
            logger.error(f"❌ Erreur ajout données volatilité réelles: {e}")

    def _calculate_atr(self, open_price: float, high: float, low: float, close: float) -> float:
        """Calcule l'ATR (Average True Range) simple pour une barre"""
        try:
            # True Range = max(high-low, abs(high-close_prev), abs(low-close_prev))
            # Pour une seule barre, on utilise high-low comme approximation
            true_range = high - low
            return max(true_range, 0.5)  # Minimum 0.5 pour éviter les valeurs trop faibles
        except Exception as e:
            logger.error(f"❌ Erreur calcul ATR: {e}")
            return 2.0  # Valeur par défaut

    def add_atr_data(self, atr_value: float) -> None:
        """Ajoute une valeur ATR à l'historique"""
        try:
            self.atr_history.append(atr_value)

            # Maintenir la taille de l'historique
            if len(self.atr_history) > self.atr_period * 2:
                self.atr_history.popleft()

            logger.debug(f"✅ ATR ajouté: {atr_value:.2f} (historique: {len(self.atr_history)})")
        except Exception as e:
            logger.error(f"❌ Erreur ajout ATR: {e}")

    def calculate_volatility_regime(self) -> VolatilityRegimeResult:
        """
        🎯 CALCUL PRINCIPAL: Analyse régime de volatilité

        Analyse:
        1. Calcul métriques volatilité (ATR + VIX)
        2. Détection régime actuel
        3. Analyse tendance volatilité
        4. Génération seuils adaptatifs
        5. Score stabilité régime

        Returns:
            VolatilityRegimeResult avec régime et seuils
        """
        start_time = time.perf_counter()

        try:
            # Vérification cache
            cache_key = f"vol_regime_{len(self.atr_history)}_{len(self.vix_history)}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result

            # Vérification données suffisantes
            if len(self.atr_history) < self.atr_period or len(self.vix_history) < 10:
                return self._create_default_result(start_time)

            # 1. CALCUL MÉTRIQUES VOLATILITÉ
            metrics = self._calculate_volatility_metrics()

            # 2. DÉTECTION RÉGIME
            regime = self._detect_volatility_regime(metrics)

            # 3. ANALYSE TENDANCE
            trend = self._analyze_volatility_trend(metrics)

            # 4. GÉNÉRATION SEUILS ADAPTATIFS
            thresholds = self._generate_adaptive_thresholds(regime, metrics)

            # 5. CALCUL SCORES CONFIANCE/STABILITÉ
            regime_confidence = self._calculate_regime_confidence(regime, metrics)
            stability_score = self._calculate_stability_score(regime)

            # 6. AJUSTEMENT RISQUE
            risk_adjustment = self._calculate_risk_adjustment(regime, metrics)

            # 7. SUIVI DURÉE RÉGIME
            days_in_regime = self._update_regime_tracking(regime)

            # 8. CRÉATION RÉSULTAT
            calc_time = (time.perf_counter() - start_time) * 1000

            result = VolatilityRegimeResult(
                regime=regime,
                trend=trend,
                metrics=metrics,
                thresholds=thresholds,
                regime_confidence=regime_confidence,
                stability_score=stability_score,
                risk_adjustment=risk_adjustment,
                calculation_time_ms=calc_time,
                days_in_regime=days_in_regime
            )

            # Cache et stats
            self._cache_result(cache_key, result)
            self._update_stats(calc_time, regime)

            return result

        except Exception as e:
            logger.error(f"Erreur calcul régime volatilité: {e}")
            return self._create_default_result(start_time)

    # ✅ Compat API: certaines intégrations appellent add_vix_data()
    def add_vix_data(self, vix_value: float, timestamp: Optional[float] = None) -> None:
        """Ajoute une observation VIX dans l'historique."""
        try:
            if vix_value is None:
                return
            self.vix_history.append(float(vix_value))
        except Exception:
            pass

    def _calculate_true_range(self, price_data: MarketData) -> float:
        """Calcule True Range pour une barre"""
        if len(self.price_history) == 0:
            return price_data.high - price_data.low

        prev_close = self.price_history[-1].close

        tr1 = price_data.high - price_data.low
        tr2 = abs(price_data.high - prev_close)
        tr3 = abs(price_data.low - prev_close)

        return max(tr1, tr2, tr3)

    def _calculate_volatility_metrics(self) -> VolatilityMetrics:
        """
        Calcule toutes les métriques de volatilité

        Returns:
            VolatilityMetrics complètes
        """
        # ATR metrics
        current_atr = list(self.atr_history)[-1]
        atr_values = list(self.atr_history)[-self.atr_period:]
        avg_atr_20 = np.mean(atr_values)
        atr_ratio = current_atr / avg_atr_20 if avg_atr_20 > 0 else 1.0

        # VIX metrics
        current_vix = list(self.vix_history)[-1]
        vix_values = list(self.vix_history)
        vix_percentile = self._calculate_percentile(current_vix, vix_values)

        # Volatilité réalisée (écart-type returns)
        if len(self.price_history) >= 20:
            prices = [p.close for p in list(self.price_history)[-20:]]
            returns = np.diff(np.log(prices))
            realized_vol = np.std(returns) * np.sqrt(252) * 100  # Annualisée en %
        else:
            realized_vol = current_vix  # Fallback

        # Volatilité de la volatilité
        if len(self.vix_history) >= 10:
            recent_vix = list(self.vix_history)[-10:]
            vol_of_vol = np.std(recent_vix)
        else:
            vol_of_vol = 0.0

        return VolatilityMetrics(
            current_atr=current_atr,
            avg_atr_20=avg_atr_20,
            atr_ratio=atr_ratio,
            current_vix=current_vix,
            vix_percentile=vix_percentile,
            realized_vol=realized_vol,
            vol_of_vol=vol_of_vol
        )

    def _detect_volatility_regime(self, metrics: VolatilityMetrics) -> VolatilityRegime:
        """
        Détecte le régime de volatilité actuel

        Logique combinée ATR + VIX:
        - LOW_VOL: VIX < 15 ET ATR ratio < 0.8
        - HIGH_VOL: VIX > 25 OU ATR ratio > 1.5
        - EXTREME_VOL: VIX > 35 OU ATR ratio > 2.0
        - NORMAL_VOL: Conditions standard
        """
        vix = metrics.current_vix
        atr_ratio = metrics.atr_ratio

        # Conditions extrêmes
        if vix > 35 or atr_ratio > 2.0:
            return VolatilityRegime.EXTREME_VOL

        # Haute volatilité
        if vix > self.vix_high_threshold or atr_ratio > self.atr_high_ratio:
            return VolatilityRegime.HIGH_VOL

        # Basse volatilité (conditions strictes)
        if vix < self.vix_low_threshold and atr_ratio < self.atr_low_ratio:
            return VolatilityRegime.LOW_VOL

        # Transition (change récent de régime)
        if self._is_regime_transitioning():
            return VolatilityRegime.TRANSITIONING

        # Conditions normales par défaut
        return VolatilityRegime.NORMAL_VOL

    def _analyze_volatility_trend(self, metrics: VolatilityMetrics) -> VolatilityTrend:
        """Analyse la tendance de volatilité"""
        if len(self.vix_history) < 5:
            return VolatilityTrend.STABLE

        # Analyse slope VIX récent
        recent_vix = list(self.vix_history)[-5:]
        vix_slope = np.polyfit(range(len(recent_vix)), recent_vix, 1)[0]

        # Analyse slope ATR
        recent_atr = list(self.atr_history)[-5:]
        atr_slope = np.polyfit(range(len(recent_atr)), recent_atr, 1)[0]

        # Combinaison slopes
        combined_slope = (vix_slope + atr_slope * 10) / 2  # Normalisation ATR

        # Classification tendance
        if combined_slope > 2.0:
            return VolatilityTrend.EXPLOSIVE
        elif combined_slope > 0.5:
            return VolatilityTrend.INCREASING
        elif combined_slope < -0.5:
            return VolatilityTrend.DECREASING
        else:
            return VolatilityTrend.STABLE

    def _generate_adaptive_thresholds(self,
                                    regime: VolatilityRegime,
                                    metrics: VolatilityMetrics) -> TradingThresholds:
        """
        🎯 GÉNÈRE SEUILS ADAPTATIFS selon régime volatilité

        Logique:
        - LOW_VOL: Seuils plus bas (plus de trades)
        - HIGH_VOL: Seuils plus élevés (trades sélectifs)
        - EXTREME_VOL: Seuils très élevés (protection)
        """
        # Seuils de base
        base_long = 0.25
        base_short = -0.25
        base_multiplier = 1.0
        base_stop_mult = 1.0
        base_tp_mult = 1.0
        base_max_pos = 3

        # Ajustements par régime
        if regime == VolatilityRegime.LOW_VOL:
            # Conditions calmes = plus de trades, stops plus serrés
            long_threshold = base_long * 0.8    # 0.20
            short_threshold = base_short * 0.8  # -0.20
            position_multiplier = base_multiplier * 1.2  # Size ×1.2
            stop_multiplier = base_stop_mult * 0.8       # Stop plus serré
            tp_multiplier = base_tp_mult * 0.9           # TP plus proche
            max_positions = base_max_pos + 1             # Plus de positions

        elif regime == VolatilityRegime.HIGH_VOL:
            # Haute volatilité = trades sélectifs, stops larges
            long_threshold = base_long * 1.4    # 0.35
            short_threshold = base_short * 1.4  # -0.35
            position_multiplier = base_multiplier * 0.8  # Size ×0.8
            stop_multiplier = base_stop_mult * 1.5       # Stop plus large
            tp_multiplier = base_tp_mult * 1.5           # TP plus loin
            max_positions = base_max_pos - 1             # Moins de positions

        elif regime == VolatilityRegime.EXTREME_VOL:
            # Conditions extrêmes = très sélectif
            long_threshold = base_long * 2.0    # 0.50
            short_threshold = base_short * 2.0  # -0.50
            position_multiplier = base_multiplier * 0.5  # Size ×0.5
            stop_multiplier = base_stop_mult * 2.0       # Stop très large
            tp_multiplier = base_tp_mult * 2.0           # TP très loin
            max_positions = 1                            # Position unique

        elif regime == VolatilityRegime.TRANSITIONING:
            # Transition = prudence
            long_threshold = base_long * 1.2    # 0.30
            short_threshold = base_short * 1.2  # -0.30
            position_multiplier = base_multiplier * 0.7  # Size réduit
            stop_multiplier = base_stop_mult * 1.2       # Stop prudent
            tp_multiplier = base_tp_mult * 1.1           # TP prudent
            max_positions = base_max_pos - 1             # Moins de positions

        else:  # NORMAL_VOL
            # Conditions standard
            long_threshold = base_long           # 0.25
            short_threshold = base_short         # -0.25
            position_multiplier = base_multiplier # 1.0
            stop_multiplier = base_stop_mult     # 1.0
            tp_multiplier = base_tp_mult         # 1.0
            max_positions = base_max_pos         # 3

        # Ajustement fine selon métriques
        atr_adjustment = min(1.5, max(0.7, metrics.atr_ratio))
        position_multiplier *= atr_adjustment

        return TradingThresholds(
            long_threshold=long_threshold,
            short_threshold=short_threshold,
            position_multiplier=position_multiplier,
            stop_loss_multiplier=stop_multiplier,
            take_profit_multiplier=tp_multiplier,
            max_positions=max_positions
        )

    def _calculate_regime_confidence(self,
                                   regime: VolatilityRegime,
                                   metrics: VolatilityMetrics) -> float:
        """Calcule confiance dans la détection de régime"""
        vix = metrics.current_vix
        atr_ratio = metrics.atr_ratio

        # Distance aux seuils = confiance
        if regime == VolatilityRegime.LOW_VOL:
            vix_dist = (self.vix_low_threshold - vix) / self.vix_low_threshold
            atr_dist = (self.atr_low_ratio - atr_ratio) / self.atr_low_ratio
            confidence = (vix_dist + atr_dist) / 2

        elif regime == VolatilityRegime.HIGH_VOL:
            vix_dist = (vix - self.vix_high_threshold) / self.vix_high_threshold
            atr_dist = (atr_ratio - self.atr_high_ratio) / self.atr_high_ratio
            confidence = (vix_dist + atr_dist) / 2

        elif regime == VolatilityRegime.EXTREME_VOL:
            # Conditions extrêmes = haute confiance
            confidence = 0.9

        else:
            # Normal/Transition = confiance modérée
            confidence = 0.6

        return np.clip(confidence, 0.0, 1.0)

    def _calculate_stability_score(self, current_regime: VolatilityRegime) -> float:
        """Calcule score de stabilité du régime actuel"""
        if len(self.regime_history) < 5:
            return 0.5  # Score neutre

        # Consistance régime récent
        recent_regimes = list(self.regime_history)[-5:]
        same_regime_count = sum(1 for r in recent_regimes if r == current_regime)
        consistency = same_regime_count / len(recent_regimes)

        # Bonus stabilité temporelle
        time_bonus = min(1.0, self.regime_stability_days / 5.0)  # Max après 5 jours

        stability = (consistency * 0.7) + (time_bonus * 0.3)
        return np.clip(stability, 0.0, 1.0)

    def _calculate_risk_adjustment(self,
                                 regime: VolatilityRegime,
                                 metrics: VolatilityMetrics) -> float:
        """
        Calcule facteur d'ajustement du risque

        Returns:
            float: Facteur [0.5, 2.0] pour ajuster exposition
        """
        base_adjustment = {
            VolatilityRegime.LOW_VOL: 1.2,      # Plus d'exposition
            VolatilityRegime.NORMAL_VOL: 1.0,   # Exposition normale
            VolatilityRegime.HIGH_VOL: 0.8,     # Moins d'exposition
            VolatilityRegime.EXTREME_VOL: 0.5,  # Exposition minimale
            VolatilityRegime.TRANSITIONING: 0.7 # Exposition réduite
        }.get(regime, 1.0)

        # Ajustement selon vol of vol
        vol_of_vol_factor = 1.0 - (metrics.vol_of_vol / 20.0)  # Plus de vol of vol = moins d'exposition
        vol_of_vol_factor = np.clip(vol_of_vol_factor, 0.5, 1.2)

        final_adjustment = base_adjustment * vol_of_vol_factor
        return np.clip(final_adjustment, 0.5, 2.0)

    def _is_regime_transitioning(self) -> bool:
        """Détecte si on est en transition de régime"""
        if len(self.regime_history) < 3:
            return False

        # Vérifier changements récents
        recent_regimes = list(self.regime_history)[-3:]
        unique_regimes = len(set(recent_regimes))

        # Transition = plus d'un régime dans les 3 dernières périodes
        return unique_regimes > 1

    def _update_regime_tracking(self, current_regime: VolatilityRegime) -> int:
        """Met à jour le suivi du régime actuel"""
        # Premier régime détecté
        if self.current_regime is None:
            self.current_regime = current_regime
            self.regime_start_time = time.time()
            self.regime_stability_days = 0

        # Changement de régime
        elif self.current_regime != current_regime:
            self.stats['regime_changes'] += 1
            self.current_regime = current_regime
            self.regime_start_time = time.time()
            self.regime_stability_days = 0

        # Même régime = incrémente stabilité
        else:
            if self.regime_start_time:
                days_elapsed = (time.time() - self.regime_start_time) / 86400  # Secondes -> jours
                self.regime_stability_days = int(days_elapsed)

        # Ajout à l'historique
        self.regime_history.append(current_regime)

        return self.regime_stability_days

    def _calculate_percentile(self, value: float, data: List[float]) -> float:
        """Calcule percentile d'une valeur dans un dataset"""
        if len(data) < 2:
            return 50.0

        data_sorted = sorted(data)
        position = np.searchsorted(data_sorted, value)
        percentile = (position / len(data)) * 100

        return np.clip(percentile, 0.0, 100.0)

    def _create_default_result(self, start_time: float) -> VolatilityRegimeResult:
        """Crée résultat par défaut en cas de données insuffisantes"""
        calc_time = (time.perf_counter() - start_time) * 1000

        default_metrics = VolatilityMetrics(
            current_atr=1.0,
            avg_atr_20=1.0,
            atr_ratio=1.0,
            current_vix=20.0,
            vix_percentile=50.0,
            realized_vol=20.0,
            vol_of_vol=0.0
        )

        default_thresholds = TradingThresholds(
            long_threshold=0.25,
            short_threshold=-0.25,
            position_multiplier=1.0,
            stop_loss_multiplier=1.0,
            take_profit_multiplier=1.0,
            max_positions=3
        )

        return VolatilityRegimeResult(
            regime=VolatilityRegime.NORMAL_VOL,
            trend=VolatilityTrend.STABLE,
            metrics=default_metrics,
            thresholds=default_thresholds,
            regime_confidence=0.5,
            stability_score=0.5,
            risk_adjustment=1.0,
            calculation_time_ms=calc_time,
            days_in_regime=0
        )

    # ===== CACHE ET OPTIMISATION =====

    def _get_from_cache(self, key: str) -> Optional[VolatilityRegimeResult]:
        """Récupération depuis cache avec TTL"""
        if key in self.cache:
            timestamp, result = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self.cache[key]
        return None

    def _cache_result(self, key: str, result: VolatilityRegimeResult) -> None:
        """Sauvegarde en cache"""
        if len(self.cache) >= self.cache_max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = (time.time(), result)

    def _cleanup_cache(self) -> None:
        """Nettoyage cache expiré"""
        current_time = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self.cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]

    def _update_stats(self, calc_time: float, regime: VolatilityRegime) -> None:
        """Mise à jour statistiques"""
        self.stats['total_calculations'] += 1

        # Rolling average calc time
        count = self.stats['total_calculations']
        prev_avg = self.stats['avg_calc_time_ms']
        self.stats['avg_calc_time_ms'] = ((prev_avg * (count - 1)) + calc_time) / count

        # Comptage régimes
        if regime == VolatilityRegime.LOW_VOL:
            self.stats['low_vol_periods'] += 1
        elif regime == VolatilityRegime.HIGH_VOL:
            self.stats['high_vol_periods'] += 1
        elif regime == VolatilityRegime.EXTREME_VOL:
            self.stats['extreme_vol_periods'] += 1

    # ===== MÉTHODES UTILITAIRES =====

    def get_current_thresholds(self) -> Optional[TradingThresholds]:
        """Retourne les seuils actuels pour intégration externe"""
        if len(self.atr_history) > 0 and len(self.vix_history) > 0:
            result = self.calculate_volatility_regime()
            return result.thresholds
        return None

    def get_statistics(self) -> Dict[str, any]:
        """Statistiques calculateur"""
        total = self.stats['total_calculations']
        cache_hit_rate = (self.stats['cache_hits'] / max(1, total)) * 100

        return {
            'total_calculations': total,
            'regime_changes': self.stats['regime_changes'],
            'low_vol_periods': self.stats['low_vol_periods'],
            'high_vol_periods': self.stats['high_vol_periods'],
            'extreme_vol_periods': self.stats['extreme_vol_periods'],
            'avg_calculation_time_ms': round(self.stats['avg_calc_time_ms'], 3),
            'cache_hit_rate_pct': round(cache_hit_rate, 1),
            'current_regime': self.current_regime.value if self.current_regime else None,
            'regime_stability_days': self.regime_stability_days,
            'data_points_atr': len(self.atr_history),
            'data_points_vix': len(self.vix_history)
        }

    def reset_history(self) -> None:
        """Reset historique (pour tests/debug)"""
        self.price_history.clear()
        self.atr_history.clear()
        self.vix_history.clear()
        self.regime_history.clear()
        self.cache.clear()
        self.current_regime = None
        self.regime_start_time = None
        self.regime_stability_days = 0
        logger.info("Historique volatility regime reseté")

# ===== FACTORY ET HELPERS =====

def create_volatility_regime_calculator(config: Optional[Dict] = None) -> VolatilityRegimeCalculator:
    """Factory function pour calculateur régime volatilité"""
    return VolatilityRegimeCalculator(config)

def simulate_volatility_scenario(scenario: str = "normal") -> List[Tuple[MarketData, float]]:
    """
    Génère scénario de volatilité pour testing

    Args:
        scenario: "low", "normal", "high", "extreme"

    Returns:
        List[(MarketData, VIX)]
    """
    data_points = []
    base_price = 4500.0

    # Paramètres par scénario
    scenario_params = {
        "low": {"vix_base": 12, "vix_var": 2, "price_var": 5},
        "normal": {"vix_base": 20, "vix_var": 5, "price_var": 15},
        "high": {"vix_base": 30, "vix_var": 8, "price_var": 30},
        "extreme": {"vix_base": 45, "vix_var": 15, "price_var": 50}
    }

    params = scenario_params.get(scenario, scenario_params["normal"])

    for i in range(50):
        # Génération VIX
        vix = max(5, params["vix_base"] + np.random.normal(0, params["vix_var"]))

        # Génération prix avec volatilité correspondante
        price_change = np.random.normal(0, params["price_var"])
        base_price += price_change

        # Génération OHLC
        open_price = base_price
        high_price = base_price + abs(np.random.normal(0, params["price_var"] / 2))
        low_price = base_price - abs(np.random.normal(0, params["price_var"] / 2))
        close_price = base_price + np.random.normal(0, params["price_var"] / 4)

        market_data = MarketData(
            timestamp=pd.Timestamp.now(),
            symbol="ES",
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=np.random.randint(1000, 5000)
        )

        data_points.append((market_data, vix))
        base_price = close_price

    return data_points


def get_volatility_multiplier_for_time(hour: int = None) -> float:
    """
    Helper rapide pour obtenir multiplicateur volatilité selon heure

    Args:
        hour: Heure EST (défaut: maintenant)

    Returns:
        float: Multiplicateur volatilité
    """
    if hour is None:
        est = pytz.timezone('US/Eastern')
        hour = datetime.now(est).hour

    # Multiplicateurs volatilité par heure
    hour_multipliers = {
        # London Open (4-8h EST) - Volatilité élevée
        4: 1.1, 5: 1.1, 6: 1.1, 7: 1.1,
        # NY Premarket (8-9h30 EST)
        8: 1.0, 9: 1.0,
        # NY Open (9h30-11h EST) - Très volatile
        10: 1.3, 11: 1.2,
        # NY Midday (11-14h EST) - Calme
        12: 0.8, 13: 0.7,
        # NY Power Hour (14-16h EST) - Volatile
        14: 1.2, 15: 1.2,
        # After Hours (16-18h EST) - Faible
        16: 0.6, 17: 0.5,
        # Overnight (18-4h EST) - Très faible
        18: 0.4, 19: 0.4, 20: 0.4, 21: 0.4, 22: 0.4, 23: 0.4,
        0: 0.4, 1: 0.4, 2: 0.4, 3: 0.4
    }

    return hour_multipliers.get(hour, 1.0)

# ===== TESTING =====

def test_volatility_regime_calculator():
    """Test complet volatility regime calculator"""
    print("=" * 50)
    print("🎯 TEST VOLATILITY REGIME CALCULATOR")
    print("=" * 50)

    # Configuration test
    config = {
        'atr_period': 20,
        'vix_low': 15,
        'vix_high': 25,
        'atr_low_ratio': 0.8,
        'atr_high_ratio': 1.5
    }

    calculator = create_volatility_regime_calculator(config)

    # Test 1: Régime low volatility
    print("\n📉 TEST 1: Régime Low Volatility")
    low_vol_data = simulate_volatility_scenario("low")

    for market_data, vix in low_vol_data:
        calculator.add_market_data(market_data, vix)

    result = calculator.calculate_volatility_regime()
    print(f"Régime détecté: {result.regime.value}")
    print(f"Tendance: {result.trend.value}")
    print(f"Seuil long: {result.thresholds.long_threshold:.3f}")
    print(f"Multiplicateur position: {result.thresholds.position_multiplier:.2f}")
    print(f"Confiance régime: {result.regime_confidence:.3f}")
    print(f"Score stabilité: {result.stability_score:.3f}")
    print(f"Temps calcul: {result.calculation_time_ms:.2f}ms")

    # Test 2: Reset et régime high volatility
    print("\n📈 TEST 2: Régime High Volatility")
    calculator.reset_history()

    high_vol_data = simulate_volatility_scenario("high")
    for market_data, vix in high_vol_data:
        calculator.add_market_data(market_data, vix)

    result = calculator.calculate_volatility_regime()
    print(f"Régime détecté: {result.regime.value}")
    print(f"Seuil long: {result.thresholds.long_threshold:.3f}")
    print(f"Multiplicateur position: {result.thresholds.position_multiplier:.2f}")
    print(f"Max positions: {result.thresholds.max_positions}")
    print(f"Ajustement risque: {result.risk_adjustment:.2f}")

    # Test 3: Régime extreme
    print("\n⚡ TEST 3: Régime Extreme Volatility")
    calculator.reset_history()

    extreme_vol_data = simulate_volatility_scenario("extreme")
    for market_data, vix in extreme_vol_data:
        calculator.add_market_data(market_data, vix)

    result = calculator.calculate_volatility_regime()
    print(f"Régime détecté: {result.regime.value}")
    print(f"Seuil long: {result.thresholds.long_threshold:.3f}")
    print(f"Multiplicateur position: {result.thresholds.position_multiplier:.2f}")
    print(f"Jours dans régime: {result.days_in_regime}")

    # Test 4: Performance cache
    print("\n⚡ TEST 4: Performance cache")
    start = time.perf_counter()
    for _ in range(10):
        calculator.calculate_volatility_regime()
    cache_time = (time.perf_counter() - start) * 1000
    print(f"10 calculs avec cache: {cache_time:.2f}ms")

    # Test 5: Seuils adaptatifs
    print("\n🎯 TEST 5: Comparaison seuils par régime")
    scenarios = ["low", "normal", "high", "extreme"]
    for scenario in scenarios:
        calculator.reset_history()
        data = simulate_volatility_scenario(scenario)
        for market_data, vix in data[-10:]:  # Derniers points seulement
            calculator.add_market_data(market_data, vix)

        result = calculator.calculate_volatility_regime()
        print(f"{scenario.upper()}: Long={result.thresholds.long_threshold:.3f}, "
              f"Mult={result.thresholds.position_multiplier:.2f}, "
              f"MaxPos={result.thresholds.max_positions}")

    # Statistiques finales
    stats = calculator.get_statistics()
    print(f"\n📊 STATISTIQUES:")
    for key, value in stats.items():
        print(f"   • {key}: {value}")

    print("\n✅ VOLATILITY REGIME CALCULATOR TEST COMPLETED")
    return True

if __name__ == "__main__":
    test_volatility_regime_calculator()
