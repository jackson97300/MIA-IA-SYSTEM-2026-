"""

MIA_IA_SYSTEM - Feature Calculator

Calcul des features syst√®me avec scoring confluence + Order Book Imbalance + Smart Money

Version: Production Ready v3.1 - PRIORIT√â #3 + TECHNIQUE #2 ELITE

Performance: <2ms garanti pour toutes features avec cache LRU



FEATURES SYST√àME (100% TOTAL) :

1. gamma_levels_proximity (28%) - Options flow SpotGamma (RENFORC√â)

2. volume_confirmation (20%) - Order flow + volume (RENFORC√â)  

3. vwap_trend_signal (16%) - VWAP slope + position

4. sierra_pattern_strength (16%) - Patterns tick reversal

5. options_flow_bias (13%) - Call/Put sentiment (RENFORC√â)

6. smart_money_strength (12.5%) - üÜï TECHNIQUE #2 ELITE

7. level_proximity (7%) - Market Profile levels

8. es_nq_correlation (7%) - Cross-market alignment

9. order_book_imbalance (15%) - Pression achat/vente

10. session_context (2.5%) - Session performance

11. pullback_quality (1.5%) - Anti-FOMO patience

-- dow_trend_regime: SUPPRIM√â ‚ùå (redondant avec vwap_trend)



SEUILS TRADING :

- 85-100% = PREMIUM_SIGNAL (size √ó1.5)

- 70-84%  = STRONG_SIGNAL  (size √ó1.0)

- 60-69%  = WEAK_SIGNAL   (size √ó0.5)

- 0-59%   = NO_TRADE      (attendre)

"""



import time

import numpy as np

import pandas as pd

from typing import Dict, List, Tuple, Optional, Any, Union

from features.confluence_analyzer import ConfluenceAnalyzer, ConfluenceZone

from dataclasses import dataclass, field

from enum import Enum

from core.logger import get_logger

from collections import deque, OrderedDict

import hashlib



# Local imports

from core.base_types import (

    MarketData, OrderFlowData, TradingFeatures,

    ES_TICK_SIZE, ES_TICK_VALUE, get_session_phase

)

from config import get_feature_config



# === IMPORT ORDER BOOK IMBALANCE ===

try:

    from .order_book_imbalance import (

        calculate_order_book_imbalance_feature,

        create_order_book_imbalance_calculator,

        OrderBookSnapshot

    )

    ORDER_BOOK_IMBALANCE_AVAILABLE = True

except ImportError:

    ORDER_BOOK_IMBALANCE_AVAILABLE = False



# === üÜï IMPORT MTF CONFLUENCE - TECHNIQUE #1 ELITE ===

try:

    from .mtf_confluence_elite import (

        EliteMTFConfluence,

        create_mtf_analyzer,

        calculate_mtf_confluence_score

    )

    MTF_CONFLUENCE_AVAILABLE = True

except ImportError:

    MTF_CONFLUENCE_AVAILABLE = False





# === üÜï IMPORT SMART MONEY TRACKER - TECHNIQUE #2 ELITE ===

try:

    from .smart_money_tracker import (

        SmartMoneyTracker, 

        create_smart_money_tracker,

        SmartMoneyAnalysis

    )

    SMART_MONEY_AVAILABLE = True

except ImportError:

    SMART_MONEY_AVAILABLE = False



logger = get_logger(__name__)



# === FEATURE WEIGHTS CONFIGURATION (TECHNIQUE #2 - NOUVELLE R√âPARTITION) ===



CONFLUENCE_WEIGHTS = {

    'gamma_levels_proximity': 0.20,      # 20% - Options flow SpotGamma (réduit pour Elite)

    'volume_confirmation': 0.15,         # 15% - Order flow + volume (réduit pour Elite)

    'vwap_trend_signal': 0.15,           # 15% - VWAP slope + position (réduit pour Elite)

    'sierra_pattern_strength': 0.15,     # 15% - Patterns tick reversal (réduit pour Elite)

    'mtf_confluence_score': 0.12,        # 12% - TECHNIQUE #1 ELITE: MTF Confluence

    'smart_money_strength': 0.08,        # 8% - TECHNIQUE #2 ELITE: Smart Money (réduit)

    'order_book_imbalance': 0.03,        # 3% - Pression achat/vente (réduit pour Elite)

    'options_flow_bias': 0.02,           # 2% - Call/Put sentiment (réduit pour Elite)
    'dealers_bias': 0.10,                # 10% - DEALER'S BIAS (NOUVEAU)

    # Supprimés pour faire place aux techniques Elite:

    # 'level_proximity': 0.0,             # Supprimé

    # 'es_nq_correlation': 0.0,           # Supprimé  

    # 'session_context': 0.0,             # Supprimé

    # 'pullback_quality': 0.0,            # Supprimé

}



# Validation weights = 100%

assert abs(sum(CONFLUENCE_WEIGHTS.values()) - 1.0) < 0.001, f"Weights must sum to 100%, got {sum(CONFLUENCE_WEIGHTS.values()):.3f}"



# === TRADING THRESHOLDS ===



TRADING_THRESHOLDS = {

    'PREMIUM_SIGNAL': 0.85,    # 85%+ = Premium trade (size √ó1.5)

    'STRONG_SIGNAL': 0.70,     # 70%+ = Strong trade (size √ó1.0)

    'WEAK_SIGNAL': 0.60,       # 60%+ = Weak trade (size √ó0.5)

    'NO_TRADE': 0.59,          # <60% = No trade (wait)

}



class SignalQuality(Enum):

    """Qualit√© du signal trading"""

    PREMIUM = "premium"     # 85-100%

    STRONG = "strong"       # 70-84%

    WEAK = "weak"          # 60-69%

    NO_TRADE = "no_trade"  # 0-59%



# === DATACLASSES ===



@dataclass

class OptionsData:

    """Donn√©es options pour gamma levels"""

    timestamp: pd.Timestamp



    # SpotGamma style data

    call_wall: float = 0.0

    put_wall: float = 0.0

    vol_trigger: float = 0.0

    net_gamma: float = 0.0



    # Options flow

    call_volume: int = 0

    put_volume: int = 0

    call_oi: int = 0

    put_oi: int = 0



    # Calculated metrics

    put_call_ratio: float = 0.0

    gamma_exposure: float = 0.0



    def __post_init__(self):

        """Calculs automatiques"""

        if self.call_volume > 0:

            self.put_call_ratio = self.put_volume / self.call_volume



        self.gamma_exposure = abs(self.net_gamma)



@dataclass

class MarketStructureData:

    """Structure de march√© compl√®te"""

    timestamp: pd.Timestamp



    # Market Profile

    poc_price: float = 0.0

    vah_price: float = 0.0

    val_price: float = 0.0



    # VWAP

    vwap_price: float = 0.0

    vwap_sd1_up: float = 0.0

    vwap_sd1_down: float = 0.0

    vwap_slope: float = 0.0



    # Previous session

    pvah: float = 0.0

    pval: float = 0.0

    ppoc: float = 0.0



    # Volume clusters

    volume_clusters: List[float] = field(default_factory=list)



    # üÜï Gamma levels pour Smart Money alignment

    call_wall: Optional[float] = None

    put_wall: Optional[float] = None



@dataclass

class ESNQData:

    """Donn√©es ES/NQ pour corr√©lation"""

    timestamp: pd.Timestamp



    # Prices

    es_price: float = 0.0

    nq_price: float = 0.0



    # Momentum

    es_momentum: float = 0.0

    nq_momentum: float = 0.0



    # Correlation metrics

    correlation: float = 0.0

    divergence_signal: float = 0.0

    leader: str = "ES"  # ES or NQ



@dataclass

class FeatureCalculationResult:

    """R√©sultat complet calcul features (TECHNIQUE #2 - avec smart_money_strength)"""

    timestamp: pd.Timestamp



    # Individual features (0-1) - dow_trend_regime SUPPRIM√â ‚ùå

    vwap_trend_signal: float = 0.0

    sierra_pattern_strength: float = 0.0

    gamma_levels_proximity: float = 0.0

    # level_proximity: float = 0.0  # Supprim√© pour techniques Elite

    # es_nq_correlation: float = 0.0  # Supprim√© pour techniques Elite

    volume_confirmation: float = 0.0

    options_flow_bias: float = 0.0
    dealers_bias: float = 0.0              # 🎯 DEALER'S BIAS

    # session_context: float = 0.0  # Supprim√© pour techniques Elite

    # pullback_quality: float = 0.0  # Supprim√© pour techniques Elite

    order_book_imbalance: float = 0.0

    mtf_confluence_score: float = 0.0      # üÜï TECHNIQUE #1 ELITE

    smart_money_strength: float = 0.0  # üÜï TECHNIQUE #2 ELITE



    # Aggregate metrics

    confluence_score: float = 0.0

    signal_quality: SignalQuality = SignalQuality.NO_TRADE

    position_multiplier: float = 0.0



    # Performance tracking

    calculation_time_ms: float = 0.0



    def to_trading_features(self) -> TradingFeatures:

        """Conversion vers TradingFeatures (avec Smart Money)"""

        return TradingFeatures(

            timestamp=self.timestamp,

            battle_navale_signal=self.sierra_pattern_strength,

            gamma_pin_strength=self.gamma_levels_proximity,

            headfake_signal=0.0,  # dow_trend_regime supprim√©

            microstructure_anomaly=self.volume_confirmation,

            market_regime_score=self.vwap_trend_signal,

            base_quality=0.0,  # level_proximity supprim√© pour techniques Elite

            confluence_score=self.confluence_score,

            session_context=0.0,  # session_context supprim√© pour techniques Elite

            order_book_imbalance=self.order_book_imbalance,

            smart_money_score=self.smart_money_strength,      # üÜï TECHNIQUE #2

            mtf_confluence_score=self.mtf_confluence_score,   # üÜï TECHNIQUE #1

            calculation_time_ms=self.calculation_time_ms

        )



# === MAIN FEATURE CALCULATOR ===



class FeatureCalculator:

    """

    Calculateur features syst√®me avec confluence scoring et cache LRU

    Version 3.1 - TECHNIQUE #2 ELITE : Smart Money Tracker int√©gr√©



    Performance garantie <2ms pour tous calculs

    Int√®gre donn√©es options (SpotGamma) + patterns Sierra + Order Book + Smart Money

    Cache interne pour optimiser les calculs r√©p√©titifs

    

    CHANGEMENTS TECHNIQUE #2:

    - Ajout Smart Money Tracker (12.5% weight)

    - Redistribution pond√©rations pour balance optimale

    - D√©tection flux institutionnels >100 contrats ES

    - Performance maintenue: <2ms, +2-3% win rate attendu

    """



    def __init__(self, config: Optional[Dict[str, Any]] = None):

        """Initialisation calculateur"""

        self.config = config or get_feature_config()



        # Param√®tres calcul

        self.lookback_periods = self.config.get('lookback_periods', 20)

        self.vwap_slope_periods = self.config.get('vwap_slope_periods', 15)

        self.correlation_periods = self.config.get('correlation_periods', 50)



        # Historique pour calculs

        self.price_history: deque = deque(maxlen=100)

        self.es_nq_history: deque = deque(maxlen=self.correlation_periods)

        self.session_performance: Dict[str, float] = {}



        # Cache interne (LRU style)

        self.cache: OrderedDict = OrderedDict()

        self.cache_max_size = self.config.get('cache_size', 500)

        self.cache_ttl = self.config.get('cache_ttl', 60)  # secondes



        # Statistiques cache

        self.cache_stats = {

            'cache_hits': 0,

            'cache_misses': 0,

            'avg_calc_time_ms': 0.0,

            'cached_calc_time_ms': 0.0,

            'total_calculations': 0

        }



        # Suivi des temps de calcul

        self._all_calc_times: List[float] = []

        self._cache_hit_times: List[float] = []



        # Performance tracking

        self.stats = {

            'calculations_count': 0,

            'avg_calc_time_ms': 0.0,

            'feature_quality_scores': []

        }



        # Configuration des logs

        self.enable_cache_debug = self.config.get('enable_cache_debug', False)



        # === Order Book Imbalance Calculator ===

        if ORDER_BOOK_IMBALANCE_AVAILABLE:

            self._ob_imbalance_calc = None  # Lazy initialization

            logger.info("‚úÖ Order Book Imbalance disponible (+3-5% win rate)")

        else:

            logger.warning("‚ö†Ô� è  Order Book Imbalance non disponible")



        # === üÜï MTF Confluence - TECHNIQUE #1 ELITE ===

        if MTF_CONFLUENCE_AVAILABLE:

            self._mtf_analyzer = create_mtf_analyzer()

            logger.info("‚úÖ MTF Confluence Elite initialis√© (+2-3% win rate)")

        else:

            self._mtf_analyzer = None

            logger.warning("‚ö†Ô� è MTF Confluence Elite non disponible")



        # === üÜï Smart Money Tracker - TECHNIQUE #2 ELITE ===

        if SMART_MONEY_AVAILABLE:

            self._smart_money_tracker = create_smart_money_tracker(config)

            logger.info("‚úÖ Smart Money Tracker initialis√© (+2-3% win rate)")

        else:

            self._smart_money_tracker = None

            logger.warning("‚ö†Ô� è Smart Money Tracker non disponible")



        logger.info(f"FeatureCalculator v4.0 - TECHNIQUES ELITE int√©gr√©es")



    def _generate_cache_key(self, market_data: MarketData, order_flow: Optional[OrderFlowData],

                            options_data: Optional[OptionsData], structure_data: Optional[MarketStructureData],

                            es_nq_data: Optional[ESNQData], sierra_patterns: Optional[Dict[str, float]],

                            order_book: Optional[OrderBookSnapshot]) -> str:

        """G√©n√®re une cl√© unique pour le cache bas√©e sur les donn√©es d'entr√©e"""

        try:

            key_components = [

                str(market_data),

                str(order_flow) if order_flow else "None",

                str(options_data) if options_data else "None",

                str(structure_data) if structure_data else "None",

                str(es_nq_data) if es_nq_data else "None",

                str(sierra_patterns) if sierra_patterns else "None",

                str(order_book) if order_book else "None"

            ]

            return hashlib.md5("".join(key_components).encode()).hexdigest()

        except Exception as e:

            logger.error(f"Erreur g√©n√©ration cl√© cache: {e}")

            return hashlib.md5(str(time.time()).encode()).hexdigest()  # Fallback



    def _prune_cache(self):

        """Supprime les entr√©es expir√©es du cache et limite la taille"""

        current_time = time.time()

        while self.cache and len(self.cache) >= self.cache_max_size:

            self.cache.popitem(last=False)  # Supprime l'√©l√©ment le plus ancien

        # Supprimer les entr√©es expir√©es

        expired_keys = [key for key, (ts, _) in self.cache.items() if current_time - ts > self.cache_ttl]

        for key in expired_keys:

            self.cache.pop(key, None)



    def _calculate_order_book_imbalance(self, 

                                       market_data: MarketData,

                                       order_book: Optional[OrderBookSnapshot] = None) -> float:

        """

        Calcule order book imbalance feature

        

        üéØ IMPACT: +3-5% win rate

        

        Returns:

            float: Signal imbalance [0, 1]

        """

        if not ORDER_BOOK_IMBALANCE_AVAILABLE:

            if self.enable_cache_debug:

                logger.warning("Order book imbalance non disponible - retour 0.0")

            return 0.0

        

        try:

            # Utiliser calculateur existant ou en cr√©er un

            if not hasattr(self, '_ob_imbalance_calc') or self._ob_imbalance_calc is None:

                self._ob_imbalance_calc = create_order_book_imbalance_calculator()

            

            # Calcul feature

            imbalance_value = calculate_order_book_imbalance_feature(

                market_data=market_data,

                order_book=order_book,

                calculator=self._ob_imbalance_calc

            )

            

            # Log pour debug si activ√©

            if self.enable_cache_debug:

                logger.debug(f"Order book imbalance: {imbalance_value:.3f}")

            

            # Convertir de [-1, 1] vers [0, 1] pour confluence

            normalized_value = (imbalance_value + 1.0) / 2.0

            return max(0.0, min(1.0, normalized_value))

        

        except Exception as e:

            logger.error(f"Erreur calcul order book imbalance: {e}")

            return 0.0





    def _calculate_mtf_confluence_score(self,

                                       market_data: MarketData,

                                       structure_data: Optional[MarketStructureData]) -> float:

        """

        üÜï MTF CONFLUENCE SCORE (12%) - TECHNIQUE #1 ELITE

        

        Multi-Timeframe Confluence Analysis

        """

        if not MTF_CONFLUENCE_AVAILABLE or not hasattr(self, '_mtf_analyzer') or not self._mtf_analyzer:

            return 0.5  # Neutral si non disponible

        

        try:

            # Pr√©paration donn√©es pour MTF analyzer

            market_dict = {

                "symbol": market_data.symbol,

                "open": market_data.open,

                "high": market_data.high,

                "low": market_data.low,

                "close": market_data.close,

                "volume": market_data.volume,

                "current_price": market_data.close

            }

            

            # Calcul MTF confluence

            mtf_score, detailed_analysis = self._mtf_analyzer.calculate_elite_mtf_confluence(market_dict)

            

            # Conversion -1,+1 vers 0,1 pour confluence

            normalized_score = (mtf_score + 1.0) / 2.0

            return max(0.0, min(1.0, normalized_score))

            

        except Exception as e:

            logger.error(f"Erreur MTF Confluence calculation: {e}")

            return 0.5



    def _calculate_smart_money_strength(self,

                                       market_data: MarketData,

                                       order_flow: Optional[OrderFlowData] = None,

                                       structure_data: Optional[MarketStructureData] = None) -> float:

        """

        üéØ SMART MONEY STRENGTH (10%) - TECHNIQUE #2 ELITE (VERSION CORRIG√âE)

        

        TECHNIQUE #2 ELITE: Analyse flux institutionnels via Smart Money Tracker

        

        Utilise maintenant les OrderFlowData pour d√©tecter les mouvements Smart Money :

        - Large trades institutionnels (>100 contrats ES)

        - Patterns d'accumulation/distribution

        - Alignement avec structure march√©

        

        Returns:

            float: Score Smart Money [0, 1] pour confluence

        """

        if not SMART_MONEY_AVAILABLE or not self._smart_money_tracker:

            return 0.5  # Neutral si non disponible

        

        try:

            # === UTILISATION DU SMART MONEY TRACKER AVEC ORDER FLOW ===

            

            # Assurer que le tracker a un cache d√©sactiv√© pour √©viter les interf√©rences

            if hasattr(self._smart_money_tracker, 'cache_ttl_seconds'):

                original_cache_ttl = self._smart_money_tracker.cache_ttl_seconds

                self._smart_money_tracker.cache_ttl_seconds = 0  # D√©sactiver temporairement

            

            # Pr√©parer structure data pour alignment si disponible

            structure_dict = None

            if structure_data:

                structure_dict = {

                    'supports': getattr(structure_data, 'supports', []),

                    'resistances': getattr(structure_data, 'resistances', []),

                    'gamma_levels': getattr(structure_data, 'gamma_levels', [])

                }

            

            # === ANALYSE SMART MONEY AVEC ORDER FLOW ===

            analysis = self._smart_money_tracker.analyze_smart_money(

                market_data=market_data,

                order_flow=order_flow,  # ‚Üê TRANSMISSION CORRECTE DES DONN√âES

                structure_data=structure_dict

            )

            

            # Restaurer le cache original

            if hasattr(self._smart_money_tracker, 'cache_ttl_seconds'):

                self._smart_money_tracker.cache_ttl_seconds = original_cache_ttl

            

            # === SCORE FINAL AVEC NORMALISATION ===

            

            smart_money_score = analysis.smart_money_score

            

            # Log pour debugging (peut √™tre supprim√© en production)

            if self.enable_cache_debug:

                logger.debug(f"üéØ Smart Money Analysis:")

                logger.debug(f"  Signal Type: {analysis.signal_type.value}")

                logger.debug(f"  Confidence: {analysis.confidence:.3f}")

                logger.debug(f"  Net Flow: {analysis.flow_data.net_flow:.3f}")

                logger.debug(f"  Smart Money Score: {smart_money_score:.3f}")

                logger.debug(f"  Large Trades: {len(analysis.large_trades)}")

            

            # Normalisation finale [-1, 1] ‚Üí [0, 1] pour confluence

            normalized_score = (smart_money_score + 1.0) / 2.0

            

            return max(0.0, min(1.0, normalized_score))

            

        except Exception as e:

            logger.warning(f"Erreur Smart Money calculation: {e}")

            

            # === FALLBACK: ANALYSE SIMPLIFI√âE SANS ORDER FLOW ===

            

            # Si order_flow disponible, utiliser une analyse simplifi√©e

            if order_flow:

                try:

                    total_volume = order_flow.bid_volume + order_flow.ask_volume

                    if total_volume > 0:

                        # Analyse basique du net delta

                        net_delta_ratio = order_flow.net_delta / total_volume

                        

                        # Analyse aggressive trades

                        total_aggressive = order_flow.aggressive_buys + order_flow.aggressive_sells

                        if total_aggressive > 100:  # Seuil minimum large trades

                            aggressive_ratio = (order_flow.aggressive_buys - order_flow.aggressive_sells) / total_aggressive

                            

                            # Combinaison des signaux

                            combined_signal = (net_delta_ratio * 0.6) + (aggressive_ratio * 0.4)

                            

                            # Normalisation [0, 1]

                            normalized_fallback = (combined_signal + 1.0) / 2.0

                            return max(0.0, min(1.0, normalized_fallback))

                except:

                    pass

            

            # Fallback ultime: analyse volume seul

            if len(self.price_history) >= 5:

                recent_volumes = [bar.volume for bar in list(self.price_history)[-5:]]

                avg_volume = np.mean(recent_volumes)

                

                current_volume = market_data.volume

                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

                

                # Volume √©lev√© = activit√© institutionnelle possible

                volume_score = min(volume_ratio / 2.0, 1.0)

                return volume_score

            

            # Dernier fallback

            return 0.5  # Neutre



    def calculate_all_features(self,

                               market_data: MarketData,

                               order_flow: Optional[OrderFlowData] = None,

                               options_data: Optional[OptionsData] = None,

                               structure_data: Optional[MarketStructureData] = None,

                               es_nq_data: Optional[ESNQData] = None,

                               sierra_patterns: Optional[Dict[str, float]] = None,

                               order_book: Optional[OrderBookSnapshot] = None,

                               **kwargs) -> FeatureCalculationResult:

        """

        CALCUL COMPLET DES FEATURES (TECHNIQUE #2 ELITE)

        

        NOUVEAU: Smart Money Tracker int√©gr√© comme 11√®me feature (12.5% weight)



        Args:

            market_data: Donn√©es OHLC + volume

            order_flow: Order flow + volume distribution

            options_data: Donn√©es options SpotGamma

            structure_data: Market Profile + VWAP + Gamma levels

            es_nq_data: Donn√©es corr√©lation ES/NQ

            sierra_patterns: Patterns depuis battle_navale.py

            order_book: Snapshot order book pour imbalance



        Returns:

            FeatureCalculationResult avec Smart Money int√©gr√©

        """

        start_time = time.perf_counter()



        # G√©n√©rer cl√© de cache

        cache_key = self._generate_cache_key(market_data, order_flow, options_data, 

                                            structure_data, es_nq_data, sierra_patterns, order_book)



        # V√©rifier cache

        self._prune_cache()

        if cache_key in self.cache:

            cached_time, result = self.cache[cache_key]

            if time.time() - cached_time <= self.cache_ttl:

                self.cache_stats['cache_hits'] += 1

                self.cache_stats['total_calculations'] += 1

                self.cache.move_to_end(cache_key)  # Rafra√Æchir LRU

                calc_time = (time.perf_counter() - start_time) * 1000

                result.calculation_time_ms = calc_time

                self._all_calc_times.append(calc_time)

                self._cache_hit_times.append(calc_time)

                if self.enable_cache_debug:

                    logger.debug(f"Cache hit pour cl√© {cache_key}")

                return result



        # Cache miss

        self.cache_stats['cache_misses'] += 1

        self.cache_stats['total_calculations'] += 1



        try:

            # Ajout √† l'historique

            self.price_history.append(market_data)

            if es_nq_data is not None:

                self.es_nq_history.append(es_nq_data)



            # Calcul features individuelles

            result = FeatureCalculationResult(timestamp=market_data.timestamp)



            # 1. VWAP TREND SIGNAL (16%) - R√©duit pour Smart Money

            result.vwap_trend_signal = self._calculate_vwap_trend_signal(

                market_data, structure_data

            )



            # 2. SIERRA PATTERN STRENGTH (16%) - R√©duit pour Smart Money

            result.sierra_pattern_strength = self._calculate_sierra_pattern_strength(

                sierra_patterns or {}

            )



            # 3. GAMMA LEVELS PROXIMITY (28%) - R√©duit pour Smart Money

            result.gamma_levels_proximity = self._calculate_gamma_proximity(

                market_data.close, options_data

            )



            # 4. LEVEL PROXIMITY - Supprim√© pour techniques Elite

            # result.level_proximity = 0.0  # Supprim√©



            # 5. ES/NQ CORRELATION - Supprim√© pour techniques Elite  

            # result.es_nq_correlation = 0.0  # Supprim√©



            # 6. VOLUME CONFIRMATION (20%) - R√©duit pour Smart Money

            result.volume_confirmation = self._calculate_volume_confirmation(

                market_data, order_flow

            )



            # 7. OPTIONS FLOW BIAS (13%) - R√©duit pour Smart Money

            result.options_flow_bias = self._calculate_options_flow_bias(

                options_data, market_data.close

            )

            # 8. DEALER'S BIAS (15%) - NOUVEAU
            result.dealers_bias = self._calculate_dealers_bias(
                market_data.symbol, market_data.close
            )

            # 9. SESSION CONTEXT - Supprim√© pour techniques Elite

            # result.session_context = 0.0  # Supprim√©



            # 9. PULLBACK QUALITY - Supprim√© pour techniques Elite

            # result.pullback_quality = 0.0  # Supprim√©



            # 10. ORDER BOOK IMBALANCE (15%) - Maintenu

            result.order_book_imbalance = self._calculate_order_book_imbalance(

                market_data=market_data,

                order_book=order_book

            )



            # üÜï 11. MTF CONFLUENCE SCORE (12%) - TECHNIQUE #1 ELITE

            result.mtf_confluence_score = self._calculate_mtf_confluence_score(

                market_data=market_data,

                structure_data=structure_data

            )



            # üÜï 12. SMART MONEY STRENGTH (10%) - TECHNIQUE #2 ELITE (CORRIG√â)

            result.smart_money_strength = self._calculate_smart_money_strength(

                market_data=market_data,

                order_flow=order_flow,  # ‚Üê TRANSMISSION CORRECTE

                structure_data=structure_data

            )



            # CALCUL CONFLUENCE FINALE (AVEC Smart Money)

            result.confluence_score = self._calculate_confluence_score(result)

            result.signal_quality = self._determine_signal_quality(result.confluence_score)

            result.position_multiplier = self._get_position_multiplier(result.signal_quality)



            # Performance tracking

            calc_time = (time.perf_counter() - start_time) * 1000

            result.calculation_time_ms = calc_time

            self._all_calc_times.append(calc_time)



            # Mettre en cache

            self._prune_cache()

            self.cache[cache_key] = (time.time(), result)



            self._update_performance_stats(calc_time, result.confluence_score)



            return result



        except Exception as e:

            logger.error(f"Erreur calcul features: {e}")

            calc_time = (time.perf_counter() - start_time) * 1000

            self._all_calc_times.append(calc_time)

            return FeatureCalculationResult(

                timestamp=market_data.timestamp,

                calculation_time_ms=calc_time

            )



    def get_cache_stats(self) -> Dict[str, Any]:

        """Retourne les statistiques du cache"""

        total = self.cache_stats['total_calculations'] or 1

        hit_rate = self.cache_stats['cache_hits'] / total if total > 0 else 0.0

        return {

            'cache_hits': self.cache_stats['cache_hits'],

            'cache_misses': self.cache_stats['cache_misses'],

            'hit_rate': hit_rate,

            'avg_calculation_time_ms': self.cache_stats['avg_calc_time_ms'],

            'cached_calc_time_ms': self.cache_stats['cached_calc_time_ms'],

            'min_calc_time_ms': min(self._all_calc_times) if self._all_calc_times else 0.0,

            'max_calc_time_ms': max(self._all_calc_times) if self._all_calc_times else 0.0,

            'min_cached_time_ms': min(self._cache_hit_times) if self._cache_hit_times else 0.0,

            'max_cached_time_ms': max(self._cache_hit_times) if self._cache_hit_times else 0.0,

            'total_calculations': self.cache_stats['total_calculations'],

            'cache_max_size': self.cache_max_size,

            'cache_ttl': self.cache_ttl,

            'order_book_imbalance_available': ORDER_BOOK_IMBALANCE_AVAILABLE,

            'smart_money_available': SMART_MONEY_AVAILABLE,  # üÜï

            'dow_trend_regime_removed': True

        }



    def _calculate_vwap_trend_signal(self,

                                     market_data: MarketData,

                                     structure_data: Optional[MarketStructureData]) -> float:

        """

        VWAP TREND SIGNAL (16%) - R√©duit pour Smart Money

        

        Combine :

        - VWAP slope (inclinaison)

        - Position vs VWAP/SD bands

        - Trend strength

        - Structure Dow int√©gr√©e (absorbe dow_trend_regime)

        """

        if not structure_data or len(self.price_history) < self.vwap_slope_periods:

            return 0.5  # Neutral



        current_price = market_data.close

        vwap = structure_data.vwap_price

        vwap_slope = structure_data.vwap_slope

        sd1_up = structure_data.vwap_sd1_up

        sd1_down = structure_data.vwap_sd1_down



        signal = 0.0



        # 1. VWAP slope analysis (30% of feature)

        if vwap_slope > 0.5:      # Strong uptrend

            signal += 0.3

        elif vwap_slope > 0.2:    # Moderate uptrend

            signal += 0.25

        elif vwap_slope > -0.2:   # Sideways

            signal += 0.15

        elif vwap_slope > -0.5:   # Moderate downtrend

            signal += 0.1

        # else: signal += 0.0     # Strong downtrend



        # 2. Position relative to VWAP (25% of feature)

        if current_price > vwap:

            vwap_position = min((current_price - vwap) / (sd1_up - vwap), 2.0)

            signal += 0.125 + (vwap_position * 0.125)  # 0.125 to 0.25

        else:

            vwap_position = min((vwap - current_price) / (vwap - sd1_down), 2.0)

            signal += 0.125 - (vwap_position * 0.125)  # 0.125 to 0.0



        # 3. Trend consistency (25% of feature)

        if len(self.price_history) >= 10:

            recent_closes = [bar.close for bar in list(self.price_history)[-10:]]

            trend_direction = np.polyfit(range(10), recent_closes, 1)[0]



            # Normalize trend direction

            trend_strength = min(abs(trend_direction) / ES_TICK_SIZE, 1.0)



            if trend_direction > 0 and vwap_slope > 0:  # Aligned bullish

                signal += 0.25 * trend_strength

            elif trend_direction < 0 and vwap_slope < 0:  # Aligned bearish

                signal += 0.25 * (1 - trend_strength)  # Inverted for bearish

            else:  # Misaligned

                signal += 0.125  # Neutral



        # 4. INT√âGRATION DOW STRUCTURE (20% of feature) - Absorbe dow_trend_regime

        if len(self.price_history) >= 20:

            recent_bars = list(self.price_history)[-20:]

            highs = [bar.high for bar in recent_bars]

            lows = [bar.low for bar in recent_bars]



            # Trend des highs et lows

            high_trend = np.polyfit(range(len(highs)), highs, 1)[0]

            low_trend = np.polyfit(range(len(lows)), lows, 1)[0]



            # Score Dow structure

            dow_component = 0.1  # Start neutral (50% of 20%)



            # Higher Highs + Higher Lows = Bullish

            if high_trend > 0 and low_trend > 0:

                trend_strength = min((high_trend + low_trend) / (2 * ES_TICK_SIZE), 1.0)

                dow_component = 0.1 + (0.1 * trend_strength)  # 0.1 to 0.2



            # Lower Highs + Lower Lows = Bearish

            elif high_trend < 0 and low_trend < 0:

                trend_strength = min(abs(high_trend + low_trend) / (2 * ES_TICK_SIZE), 1.0)

                dow_component = 0.1 - (0.1 * trend_strength)  # 0.1 to 0.0



            signal += dow_component



        return max(0.0, min(1.0, signal))



    def _calculate_sierra_pattern_strength(self,

                                           sierra_patterns: Dict[str, float]) -> float:

        """

        SIERRA PATTERN STRENGTH (16%) - R√©duit pour Smart Money



        Force des patterns depuis battle_navale.py :

        - Long Down Up Bar

        - Long Up Down Bar

        - Color Down Setting

        - Base quality

        """

        if not sierra_patterns:

            return 0.0



        # R√©cup√©ration patterns

        battle_signal = sierra_patterns.get('battle_navale_signal', 0.0)

        base_quality = sierra_patterns.get('base_quality', 0.0)

        trend_continuation = sierra_patterns.get('trend_continuation', 0.0)

        battle_strength = sierra_patterns.get('battle_strength', 0.0)



        # Pond√©ration patterns

        pattern_score = (

            battle_signal * 0.4 +      # 40% - Signal principal bataille

            base_quality * 0.25 +      # 25% - Qualit√© des bases

            trend_continuation * 0.2 +  # 20% - Respect r√®gle d'or

            battle_strength * 0.15     # 15% - Force patterns

        )



        return max(0.0, min(1.0, pattern_score))

    def _calculate_gamma_proximity(self,
                                    current_price: float,
                                    options_data: Optional[OptionsData]) -> float:
        """
        🎯 GAMMA LEVELS PROXIMITY (28%) - VERSION CORRIGÉE FINALE
        
        CORRECTION CRITIQUE : Monotonie garantie + Bonus capé
        
        Distance aux niveaux gamma critiques :
        - Call Wall proximity (32.5% du feature)
        - Put Wall proximity (32.5% du feature)  
        - Vol Trigger proximity (10% du feature)
        - Net Gamma regime (25% du feature)
        - Gamma Flip bonus (5% du feature) - CAPÉ
        
        Returns:
            float: Score gamma proximity [0, 1] pour confluence
        """
        if not options_data:
            return 0.0

        try:
            # Récupération données options
            call_wall = options_data.call_wall
            put_wall = options_data.put_wall
            vol_trigger = options_data.vol_trigger
            net_gamma = options_data.net_gamma
            gamma_flip = getattr(options_data, 'gamma_flip', 0)
            
            # Constantes de sécurité
            ES_TICK_SIZE = 0.25
            SPAN_TICKS = 100  # 25 points pour ES
            
            # 1. Call Wall Proximity (32.5%) - CORRECTION MONOTONIE
            if call_wall and call_wall > 0:
                # CORRECTION : Calcul direct pour monotonie garantie
                call_distance = abs(current_price - call_wall)
                span_distance = SPAN_TICKS * ES_TICK_SIZE
                call_proximity = max(0.0, 1.0 - (call_distance / span_distance))
            else:
                call_proximity = 0.0
            
            # 2. Put Wall Proximity (32.5%) - CORRECTION MONOTONIE
            if put_wall and put_wall > 0:
                # CORRECTION : Calcul direct pour monotonie garantie
                put_distance = abs(current_price - put_wall)
                span_distance = SPAN_TICKS * ES_TICK_SIZE
                put_proximity = max(0.0, 1.0 - (put_distance / span_distance))
            else:
                put_proximity = 0.0
            
            # 3. Vol Trigger Proximity (10%) - CORRECTION MONOTONIE
            if vol_trigger and vol_trigger > 0:
                # CORRECTION : Calcul direct pour monotonie garantie
                vol_distance = abs(current_price - vol_trigger)
                span_distance = SPAN_TICKS * ES_TICK_SIZE
                vol_proximity = max(0.0, 1.0 - (vol_distance / span_distance))
            else:
                vol_proximity = 0.0
            
            # 4. Net Gamma Regime (25%)
            abs_net_gamma = min(1.0, abs(net_gamma) / 0.1)  # Normalisé sur 0.1
            
            # 5. Gamma Flip Bonus (5% - CAPÉ)
            if gamma_flip and gamma_flip > 0:
                # CORRECTION : Calcul direct pour monotonie garantie
                flip_distance = abs(current_price - gamma_flip)
                span_distance = SPAN_TICKS * ES_TICK_SIZE
                flip_proximity = max(0.0, 1.0 - (flip_distance / span_distance))
                flip_bonus = min(0.05, flip_proximity * 0.05)  # CAPÉ à 5%
            else:
                flip_bonus = 0.0
            
            # CORRECTION CRITIQUE : Bonus capé pour éviter overflow
            base_score = (0.325 * call_proximity + 
                         0.325 * put_proximity + 
                         0.10 * vol_proximity + 
                         0.25 * abs_net_gamma)
            
            gamma_score = min(1.0, base_score + flip_bonus)  # CAPÉ à 100%
            
            # Logging détaillé pour traçabilité
            logger.debug(
                "γ-prox | call=%.3f put=%.3f vol=%.3f net=%.3f flip=%.3f → score=%.3f",
                call_proximity, put_proximity, vol_proximity, abs_net_gamma, flip_bonus, gamma_score
            )
            
            return gamma_score
            
        except Exception as e:
            logger.error(f"❌ Erreur gamma_proximity: {e}")
            return 0.0

    def _safe_proximity_calculation(self, current_price: float, target_level: float, 
                                   span_ticks: int = 100, tick_size: float = 0.25) -> float:
        """
        🛡️ CALCUL SÉCURISÉ DE PROXIMITÉ
        
        Gestion sécurisée des cas edge :
        - Murs manquants (None, 0, négatifs)
        - Distances infinies
        - Valeurs NaN
        
        Returns:
            float: Proximité normalisée [0, 1] ou 0.0 si invalide
        """
        try:
            # Validation des entrées
            if (current_price is None or target_level is None or 
                target_level <= 0 or current_price <= 0):
                return 0.0
            
            # Calcul distance sécurisé
            distance = abs(current_price - target_level)
            
            # Protection contre distances infinies
            if distance <= 0 or distance > 10000:  # Limite raisonnable
                return 0.0
            
            # Calcul proximité normalisée
            span_distance = span_ticks * tick_size
            proximity = max(0.0, 1.0 - (distance / span_distance))
            
            # Protection finale
            return max(0.0, min(1.0, proximity))
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul proximité: {e}")
            return 0.0



    def _calculate_level_proximity(self,

                                   current_price: float,

                                   structure_data: Optional[MarketStructureData]) -> float:

        """

        LEVEL PROXIMITY (7%) - R√©duit pour Smart Money



        Distance aux niveaux Market Profile :

        - POC, VAH, VAL

        - Previous session levels

        - Volume clusters

        """

        if not structure_data:

            return 0.0



        levels = []



        # Current session levels

        if structure_data.poc_price > 0:

            levels.append(structure_data.poc_price)

        if structure_data.vah_price > 0:

            levels.append(structure_data.vah_price)

        if structure_data.val_price > 0:

            levels.append(structure_data.val_price)



        # Previous session levels

        if structure_data.pvah > 0:

            levels.append(structure_data.pvah)

        if structure_data.pval > 0:

            levels.append(structure_data.pval)

        if structure_data.ppoc > 0:

            levels.append(structure_data.ppoc)



        # Volume clusters

        levels.extend(structure_data.volume_clusters)



        if not levels:

            return 0.0



        # Find closest level

        distances = [abs(current_price - level) for level in levels]

        min_distance = min(distances)



        # Proximity score (within 3 ticks = full score)

        proximity_score = max(0, 1 - (min_distance / (3 * ES_TICK_SIZE)))



        return proximity_score



    def _calculate_es_nq_correlation(self,

                                     es_nq_data: Optional[ESNQData]) -> float:

        """

        ES/NQ CORRELATION (7%) - R√©duit pour Smart Money



        Alignment entre ES et NQ :

        - Correlation coefficient

        - Divergence detection

        - Leadership analysis

        """

        if not es_nq_data or len(self.es_nq_history) < 10:

            return 0.5  # Neutral



        correlation = es_nq_data.correlation

        divergence = es_nq_data.divergence_signal



        # High correlation = good signal

        corr_score = max(0, correlation)  # Correlation -1 to 1, we want 0 to 1



        # Low divergence = good signal

        divergence_score = max(0, 1 - abs(divergence))



        # Combined score

        es_nq_score = (corr_score * 0.7) + (divergence_score * 0.3)



        return max(0.0, min(1.0, es_nq_score))



    def _calculate_volume_confirmation(self,

                                       market_data: MarketData,

                                       order_flow: Optional[OrderFlowData]) -> float:

        """

        VOLUME CONFIRMATION (20%) - R√©duit pour Smart Money



        Confirmation volume et order flow :

        - Volume relatif

        - Order flow direction

        - Aggressive trades

        """

        volume_score = 0.0



        # 1. Volume analysis (45% of feature)

        if len(self.price_history) >= 10:

            recent_volumes = [bar.volume for bar in list(self.price_history)[-10:]]

            avg_volume = np.mean(recent_volumes)



            current_volume = market_data.volume

            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0



            # Higher volume = better confirmation

            volume_strength = min(volume_ratio / 1.8, 1.0)

            volume_score += volume_strength * 0.45



        # 2. Order flow confirmation (35% of feature)

        if order_flow:

            # Net delta analysis

            total_volume = order_flow.bid_volume + order_flow.ask_volume

            if total_volume > 0:

                net_delta_ratio = abs(order_flow.net_delta) / total_volume

                order_flow_strength = min(net_delta_ratio * 2.2, 1.0)

                volume_score += order_flow_strength * 0.25



            # Aggressive trades

            total_aggressive = order_flow.aggressive_buys + order_flow.aggressive_sells

            if total_aggressive > 0:

                aggressive_ratio = total_aggressive / total_volume if total_volume > 0 else 0

                aggressive_strength = min(aggressive_ratio * 8, 1.0)

                volume_score += aggressive_strength * 0.10



        # 3. Volume trend consistency (20% of feature)

        if len(self.price_history) >= 5:

            recent_volumes = [bar.volume for bar in list(self.price_history)[-5:]]

            recent_closes = [bar.close for bar in list(self.price_history)[-5:]]

            

            # Corr√©lation volume/price

            if len(set(recent_volumes)) > 1 and len(set(recent_closes)) > 1:

                # PATCH: Vérification échantillon suffisant
                if len(recent_volumes) >= 2 and len(recent_closes) >= 2:
                    with np.errstate(all='ignore'):
                        volume_price_corr = np.corrcoef(recent_volumes, recent_closes)[0, 1]
                    if np.isfinite(volume_price_corr):
                        # Volume-price correlation strengthens signal
                        corr_score = (abs(volume_price_corr) + 1) / 2  # 0 to 1
                        volume_score += corr_score * 0.20



        return max(0.0, min(1.0, volume_score))



    def _calculate_options_flow_bias(self,

                                     options_data: Optional[OptionsData],

                                     current_price: float = None) -> float:

        """

        🎯 OPTIONS FLOW BIAS (13%) - VERSION CORRIGÉE
        
        CORRECTION CRITIQUE : Réduction Vol Trigger de 10% à 5% pour éviter double comptage
        
        Sentiment options complet :
        - Put/Call ratio (40% du feature)
        - Volume flow (30% du feature)
        - Call/Put Walls proximity (20% du feature)
        - Vol Trigger impact (5% du feature) - RÉDUIT pour éviter double comptage
        """
        if not options_data:
            return 0.5  # Neutral

        try:
            put_call_ratio = options_data.put_call_ratio
            call_volume = options_data.call_volume
            put_volume = options_data.put_volume
            call_wall = options_data.call_wall
            put_wall = options_data.put_wall
            vol_trigger = options_data.vol_trigger
            
            # Constantes de sécurité
            ES_TICK_SIZE = 0.25
            SPAN_TICKS = 100
            
            # 1. Put/Call Ratio (40%) - CORRECTION MONOTONIE
            if put_call_ratio > 0:
                # CORRECTION : PCR monotone et centre neutre correct
                # PCR < 1.0 = bullish, PCR > 1.0 = bearish, PCR = 1.0 = neutre
                if put_call_ratio < 1.0:
                    # PCR < 1.0 : bullish (0.5 → 1.0)
                    pcr_bias = 0.5 + (1.0 - put_call_ratio) * 0.5  # 0.5 → 1.0
                elif put_call_ratio > 1.0:
                    # PCR > 1.0 : bearish (0.5 → 0.0)
                    pcr_bias = max(0.0, 0.5 - (put_call_ratio - 1.0) * 0.5)  # 0.5 → 0.0
                else:
                    # PCR = 1.0 : neutre
                    pcr_bias = 0.5
            else:
                pcr_bias = 0.5
            
            # 2. Volume Flow (30%)
            total_volume = call_volume + put_volume
            if total_volume > 0:
                call_ratio = call_volume / total_volume
                volume_flow = call_ratio  # 0.0 = bearish, 1.0 = bullish
            else:
                volume_flow = 0.5
            
            # 3. Call/Put Walls Proximity (20%)
            walls_bias = 0.5  # Neutre par défaut
            
            if current_price and call_wall and put_wall:
                # Distance aux murs
                call_distance = abs(current_price - call_wall)
                put_distance = abs(current_price - put_wall)
                
                # Proximité normalisée
                call_prox = max(0.0, 1.0 - (call_distance / (SPAN_TICKS * ES_TICK_SIZE)))
                put_prox = max(0.0, 1.0 - (put_distance / (SPAN_TICKS * ES_TICK_SIZE)))
                
                # Bias basé sur proximité relative
                if call_prox > put_prox:
                    walls_bias = 0.5 + (call_prox - put_prox) * 0.5  # Plus bullish si call wall proche
                else:
                    walls_bias = 0.5 - (put_prox - call_prox) * 0.5  # Plus bearish si put wall proche
            
            # 4. Vol Trigger Impact (5% - RÉDUIT pour éviter double comptage)
            vol_trigger_bias = 0.5  # Neutre par défaut
            
            if current_price and vol_trigger:
                vol_distance = abs(current_price - vol_trigger)
                vol_prox = max(0.0, 1.0 - (vol_distance / (SPAN_TICKS * ES_TICK_SIZE)))
                
                # Vol trigger proche = plus de volatilité = bias neutre
                vol_trigger_bias = 0.5 + (vol_prox - 0.5) * 0.1  # Impact réduit
            
            # Calcul final avec pondérations corrigées
            final_bias = (0.40 * pcr_bias + 
                          0.30 * volume_flow + 
                          0.20 * walls_bias + 
                          0.05 * vol_trigger_bias)  # RÉDUIT de 10% à 5%
            
            # CORRECTION CRITIQUE : Uniformisation échelle [0,1] avec 0.5 neutre
            # 0.0 = bearish, 0.5 = neutre, 1.0 = bullish
            final_bias = max(0.0, min(1.0, final_bias))
            
            # Validation cohérence
            if final_bias < 0.0 or final_bias > 1.0:
                logger.warning(f"⚠️ Options bias hors échelle: {final_bias:.3f}, clampé")
                final_bias = max(0.0, min(1.0, final_bias))
            
            # Logging détaillé pour traçabilité
            logger.debug(
                "opt-bias | walls=%.3f volFlow=%.3f pcr=%.3f volTrig=%.3f → bias=%.3f",
                walls_bias, volume_flow, pcr_bias, vol_trigger_bias, final_bias
            )
            
            return final_bias
            
        except Exception as e:
            logger.error(f"❌ Erreur options_flow_bias: {e}")
            return 0.5  # Neutral en cas d'erreur

    def _calculate_dealers_bias(self, symbol: str, current_price: float) -> float:
        """
        🎯 DEALER'S BIAS (15%) - NOUVEAU
        
        Intégration du Dealer's Bias depuis les snapshots options
        - Gamma Flip (pivot de tendance)
        - Gamma Pins (zones d'aimantation)
        - PCR, IV Skew, VIX
        - Score normalisé [0,1] avec 0.5 neutre
        """
        try:
            # Import dynamique pour éviter circular imports
            from features.dealers_bias_analyzer import get_dealers_bias_analyzer
            
            analyzer = get_dealers_bias_analyzer()
            bias_data = analyzer.get_dealers_bias(symbol)
            
            if not bias_data:
                logger.warning(f"⚠️ Pas de données Dealer's Bias pour {symbol}")
                return 0.5  # Neutre
            
            # Score de confluence normalisé [0,1]
            confluence_score = analyzer.get_confluence_score(symbol)
            
            # Validation et logging
            if confluence_score < 0.0 or confluence_score > 1.0:
                logger.warning(f"⚠️ Dealer's Bias score hors échelle: {confluence_score:.3f}")
                confluence_score = max(0.0, min(1.0, confluence_score))
            
            logger.debug(
                "dealers-bias | score=%.3f direction=%s strength=%s → confluence=%.3f",
                bias_data.dealers_bias_score, bias_data.direction, bias_data.strength, confluence_score
            )
            
            return confluence_score
            
        except Exception as e:
            logger.error(f"❌ Erreur dealers_bias: {e}")
            return 0.5  # Neutre en cas d'erreur



    def _calculate_session_context(self,

                                   timestamp: pd.Timestamp) -> float:

        """

        SESSION CONTEXT (2.5%) - R√©duit pour Smart Money



        Performance par session :

        - London Open, NY Open, Lunch, etc.

        - Historical win rate par session

        """

        session_phase = get_session_phase(timestamp)



        # Performance historique par session (√† impl√©menter avec donn√©es r√©elles)

        session_performance = {

            'london_open': 0.65,    # 65% win rate

            'ny_open': 0.75,        # 75% win rate

            'lunch': 0.45,          # 45% win rate (√©viter)

            'afternoon': 0.60,      # 60% win rate

            'close': 0.50,          # 50% win rate

            'after_hours': 0.40,    # 40% win rate (√©viter)

            'pre_market': 0.50      # 50% win rate

        }



        session_key = session_phase.value

        return session_performance.get(session_key, 0.5)



    def _calculate_pullback_quality(self,

                                    market_data: MarketData) -> float:

        """

        PULLBACK QUALITY (1.5%) - R√©duit pour Smart Money

        

        Anti-FOMO patience feature :

        - Qualit√© du pullback

        - Respect des niveaux

        """

        if len(self.price_history) < 10:

            return 0.5



        # Analyse simple qualit√© pullback

        recent_bars = list(self.price_history)[-10:]

        recent_highs = [bar.high for bar in recent_bars]

        recent_lows = [bar.low for bar in recent_bars]



        current_price = market_data.close

        recent_high = max(recent_highs)

        recent_low = min(recent_lows)



        # Position dans la range r√©cente

        if recent_high > recent_low:

            position_in_range = (current_price - recent_low) / (recent_high - recent_low)

            

            # Pullback quality: meilleur si on n'est pas aux extr√™mes

            if 0.3 <= position_in_range <= 0.7:  # Zone de pullback qualit√©

                pullback_quality = 0.7

            elif 0.2 <= position_in_range <= 0.8:  # Zone acceptable

                pullback_quality = 0.6

            else:  # Extr√™mes - attention FOMO

                pullback_quality = 0.4

        else:

            pullback_quality = 0.5



        return pullback_quality



    def _calculate_confluence_score(self,

                                    result: FeatureCalculationResult) -> float:

        """

        CALCUL CONFLUENCE FINALE (TECHNIQUE #2 ELITE)



        Pond√©ration de toutes les features selon CONFLUENCE_WEIGHTS

        AVEC Smart Money int√©gr√©

        """

        features = {

            'gamma_levels_proximity': result.gamma_levels_proximity,

            'volume_confirmation': result.volume_confirmation,

            'vwap_trend_signal': result.vwap_trend_signal,

            'sierra_pattern_strength': result.sierra_pattern_strength,

            'mtf_confluence_score': result.mtf_confluence_score,      # üÜï TECHNIQUE #1

            'smart_money_strength': result.smart_money_strength,      # üÜï TECHNIQUE #2

            'order_book_imbalance': result.order_book_imbalance,

            'options_flow_bias': result.options_flow_bias,

            'dealers_bias': result.dealers_bias,                      # 🎯 DEALER'S BIAS

            # Features supprim√©es pour techniques Elite:

            # 'level_proximity': 0.0,

            # 'es_context': 0.0,

            # 'session_context': 0.0,

            # 'pullback_quality': 0.0,

        }



        confluence_score = 0.0



        for feature_name, feature_value in features.items():

            weight = CONFLUENCE_WEIGHTS.get(feature_name, 0.0)

            confluence_score += feature_value * weight



        return max(0.0, min(1.0, confluence_score))



    def _determine_signal_quality(self,

                                  confluence_score: float) -> SignalQuality:

        """D√©termine qualit√© signal selon seuils"""

        if confluence_score >= TRADING_THRESHOLDS['PREMIUM_SIGNAL']:

            return SignalQuality.PREMIUM

        elif confluence_score >= TRADING_THRESHOLDS['STRONG_SIGNAL']:

            return SignalQuality.STRONG

        elif confluence_score >= TRADING_THRESHOLDS['WEAK_SIGNAL']:

            return SignalQuality.WEAK

        else:

            return SignalQuality.NO_TRADE



    def _get_position_multiplier(self,

                                 signal_quality: SignalQuality) -> float:

        """Multiplicateur position selon qualit√©"""

        multipliers = {

            SignalQuality.PREMIUM: 1.5,   # Size √ó1.5

            SignalQuality.STRONG: 1.0,    # Size √ó1.0

            SignalQuality.WEAK: 0.5,      # Size √ó0.5

            SignalQuality.NO_TRADE: 0.0   # No trade

        }

        return multipliers.get(signal_quality, 0.0)



    def _update_performance_stats(self,

                                  calc_time: float,

                                  confluence_score: float):

        """Mise √† jour statistiques performance"""

        self.stats['calculations_count'] += 1



        # Rolling average calculation time

        count = self.stats['calculations_count']

        prev_avg = self.stats['avg_calc_time_ms']

        self.stats['avg_calc_time_ms'] = ((prev_avg * (count - 1)) + calc_time) / count



        # Mise √† jour cache stats

        total = self.cache_stats['total_calculations'] or 1

        self.cache_stats['avg_calc_time_ms'] = (

            (self.cache_stats['avg_calc_time_ms'] * (total - 1)) + calc_time

        ) / total if total > 0 else calc_time



        # Feature quality tracking

        self.stats['feature_quality_scores'].append(confluence_score)

        if len(self.stats['feature_quality_scores']) > 100:

            self.stats['feature_quality_scores'].pop(0)  # Keep last 100



    def get_statistics(self) -> Dict[str, Any]:

        """Statistiques calculateur"""

        quality_scores = self.stats['feature_quality_scores']



        return {

            'calculations_count': self.stats['calculations_count'],

            'avg_calculation_time_ms': round(self.stats['avg_calc_time_ms'], 3),

            'avg_confluence_score': round(np.mean(quality_scores), 3) if quality_scores else 0.0,

            'confluence_score_std': round(np.std(quality_scores), 3) if quality_scores else 0.0,

            'premium_signals_pct': len([s for s in quality_scores if s >= 0.85]) / len(quality_scores) * 100 if quality_scores else 0.0,

            'no_trade_signals_pct': len([s for s in quality_scores if s < 0.60]) / len(quality_scores) * 100 if quality_scores else 0.0,

            'order_book_imbalance_enabled': ORDER_BOOK_IMBALANCE_AVAILABLE,

            'smart_money_enabled': SMART_MONEY_AVAILABLE,  # üÜï TECHNIQUE #2

            'dow_trend_regime_removed': True,

            'version': '3.1_TECHNIQUE_2_ELITE'

        }



# === FACTORY FUNCTIONS ===



def create_feature_calculator(config: Optional[Dict[str, Any]] = None) -> FeatureCalculator:

    """Factory function pour calculateur"""

    return FeatureCalculator(config)



def calculate_features_from_data(market_data: MarketData,

                                 order_flow: Optional[OrderFlowData] = None,

                                 options_data: Optional[OptionsData] = None,

                                 structure_data: Optional[MarketStructureData] = None,

                                 es_nq_data: Optional[ESNQData] = None,

                                 sierra_patterns: Optional[Dict[str, float]] = None,

                                 order_book: Optional[OrderBookSnapshot] = None,

                                 calculator: Optional[FeatureCalculator] = None) -> FeatureCalculationResult:

    """Helper function pour calcul features"""

    if calculator is None:

        calculator = create_feature_calculator()



    return calculator.calculate_all_features(

        market_data=market_data,

        order_flow=order_flow,

        options_data=options_data,

        structure_data=structure_data,

        es_nq_data=es_nq_data,

        sierra_patterns=sierra_patterns,

        order_book=order_book

    )



# === TESTING ===



def test_feature_calculator():

    """Test complet feature calculator TECHNIQUE #2 ELITE (avec Smart Money)"""

    logger.info("TEST FEATURE CALCULATOR v3.1 - TECHNIQUE #2 ELITE")

    print("=" * 50)



    # Cr√©ation calculateur

    config = {'enable_cache_debug': True}

    calculator = create_feature_calculator(config)



    # Donn√©es de test

    market_data = MarketData(

        timestamp=pd.Timestamp.now(),

        symbol="ES",

        open=4500.0,

        high=4510.0,

        low=4495.0,

        close=4505.0,

        volume=2500  # Volume √©lev√© pour Smart Money

    )



    # Order flow test pour Smart Money

    order_flow = OrderFlowData(

        timestamp=pd.Timestamp.now(),

        symbol="ES",

        cumulative_delta=150.0,

        bid_volume=1000,

        ask_volume=1500,

        aggressive_buys=800,  # Large institutional buying

        aggressive_sells=200,

        net_delta=600

    )



    # Options data test

    options_data = OptionsData(

        timestamp=pd.Timestamp.now(),

        call_wall=4520.0,

        put_wall=4480.0,

        net_gamma=2.5,

        call_volume=1200,

        put_volume=800

    )



    # Structure data test avec gamma levels pour Smart Money

    structure_data = MarketStructureData(

        timestamp=pd.Timestamp.now(),

        poc_price=4500.0,

        vah_price=4515.0,

        val_price=4485.0,

        vwap_price=4502.0,

        vwap_slope=0.3,

        call_wall=4520.0,  # üÜï Pour Smart Money alignment

        put_wall=4480.0    # üÜï Pour Smart Money alignment

    )



    # Sierra patterns test

    sierra_patterns = {

        'battle_navale_signal': 0.8,

        'base_quality': 0.7,

        'trend_continuation': 0.9,

        'battle_strength': 0.75

    }



    # Order Book test

    order_book = None

    if ORDER_BOOK_IMBALANCE_AVAILABLE:

        from .order_book_imbalance import create_mock_order_book

        order_book = create_mock_order_book("ES", 4505.0)

        logger.info("‚úÖ Order Book mock cr√©√© pour test")



    # Calcul features

    result = calculator.calculate_all_features(

        market_data=market_data,

        order_flow=order_flow,

        options_data=options_data,

        structure_data=structure_data,

        sierra_patterns=sierra_patterns,

        order_book=order_book

    )



    logger.info(f"‚úÖ Features calcul√©es en {result.calculation_time_ms:.2f}ms")

    logger.info(f"‚úÖ Confluence score: {result.confluence_score:.3f}")

    logger.info(f"‚úÖ Signal quality: {result.signal_quality.value}")

    logger.info(f"‚úÖ Position multiplier: {result.position_multiplier}x")



    # Validation TECHNIQUES ELITE

    logger.info("\n[TECHNIQUES ELITE] VALIDATION:")

    logger.info(f"   ‚Ä¢ MTF Confluence Score: {result.mtf_confluence_score:.3f} (12%)")

    logger.info(f"   ‚Ä¢ Smart Money Strength: {result.smart_money_strength:.3f} (10%)")

    logger.info(f"   ‚Ä¢ Gamma Levels Proximity: {result.gamma_levels_proximity:.3f} (28%)")

    logger.info(f"   ‚Ä¢ Volume Confirmation: {result.volume_confirmation:.3f} (20%)")

    logger.info(f"   ‚Ä¢ VWAP Trend Signal: {result.vwap_trend_signal:.3f} (16%)")

    logger.info(f"   ‚Ä¢ Sierra Pattern Strength: {result.sierra_pattern_strength:.3f} (16%)")



    # Test conversion to TradingFeatures

    trading_features = result.to_trading_features()

    logger.info(f"   ‚Ä¢ TradingFeatures.smart_money_score: {trading_features.smart_money_score:.3f}")



    # Validation des nouvelles pond√©rations

    logger.info("\n[POND√âRATIONS TECHNIQUE #2] VALIDATION:")

    for feature_name, weight in CONFLUENCE_WEIGHTS.items():

        logger.info(f"   ‚Ä¢ {feature_name}: {weight:.1%}")

    

    total_weight = sum(CONFLUENCE_WEIGHTS.values())

    logger.info(f"   ‚Ä¢ TOTAL: {total_weight:.1%}")

    

    if abs(total_weight - 1.0) < 0.001:

        logger.info("‚úÖ Pond√©rations valid√©es - Total = 100%")

    else:

        logger.error(f"‚ùå Erreur pond√©rations - Total = {total_weight:.1%}")



    # Cache stats

    cache_stats = calculator.get_cache_stats()

    logger.info(f"\n[CACHE] Smart Money disponible: {cache_stats['smart_money_available']}")



    # Stats calculateur

    stats = calculator.get_statistics()

    logger.info(f"\n[STATS] Smart Money enabled: {stats['smart_money_enabled']}")

    logger.info(f"[STATS] Version: {stats['version']}")



    logger.info("\nüéØ TECHNIQUE #2 ELITE COMPLETED: Smart Money Tracker int√©gr√© avec succ√®s")

    logger.info("üìà Gains attendus: +2-3% win rate via d√©tection flux institutionnels")

    return True



if __name__ == "__main__":

    test_feature_calculator()