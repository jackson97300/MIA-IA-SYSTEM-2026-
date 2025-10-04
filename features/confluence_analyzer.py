"""
MIA_IA_SYSTEM - Confluence Analyzer
Analyseur multi-level confluence pour Battle Navale
Version: Phase 3 Elite - MTF Confluence Intégrée
Performance: Analyse <3ms, détection temps réel

RESPONSABILITÉS :
1. Détection zones confluence multi-niveaux
2. Scoring qualité confluence (0-1)
3. Analyse proximité niveaux critiques
4. Validation force supports/résistances
5. Integration Battle Navale + Features
6. 🆕 ELITE MTF CONFLUENCE - Multi-Timeframe Analysis

NIVEAUX ANALYSÉS :
- Gamma Levels : Call walls, Put walls, Gamma flip
- Market Profile : VAH, VAL, POC (current + previous)
- VWAP Bands : VWAP, SD1, SD2 (multiple timeframes)
- Volume Clusters : High Volume Nodes, Volume gaps
- Previous Session : PVAH, PVAL, PPOC, Session H/L
- Technical Levels : Round numbers, Fibonacci, Pivots

CONFLUENCE LOGIC :
- Zone = Prix ± tolerance (ticks)
- Force = Nombre de niveaux dans zone
- Qualité = Pondération selon type niveau
- Score final = Force × Qualité × Proximité
- 🆕 MTF Score = Confluence dynamique multi-timeframes
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from core.logger import get_logger
from collections import defaultdict

# Local imports
from core.base_types import MarketData, ES_TICK_SIZE, ES_TICK_VALUE
from config.automation_config import get_automation_config

# 🆕 MenthorQ Integration
try:
    from features.menthorq_integration import MenthorQIntegration, MenthorQLevelType
    MENTHORQ_AVAILABLE = True
except ImportError:
    MENTHORQ_AVAILABLE = False
    logger.warning("⚠️ MenthorQ Integration non disponible")

logger = get_logger(__name__)

# === CONFLUENCE ENUMS ===

class LevelType(Enum):
    """Types de niveaux"""
    GAMMA_CALL_WALL = "gamma_call_wall"         # Résistance gamma
    GAMMA_PUT_WALL = "gamma_put_wall"           # Support gamma
    GAMMA_FLIP = "gamma_flip"                   # Zone pivot gamma
    VWAP = "vwap"                               # VWAP
    VWAP_SD1_UP = "vwap_sd1_up"                # VWAP +1SD
    VWAP_SD1_DOWN = "vwap_sd1_down"            # VWAP -1SD
    VWAP_SD2_UP = "vwap_sd2_up"                # VWAP +2SD
    VWAP_SD2_DOWN = "vwap_sd2_down"            # VWAP -2SD
    POC = "poc"                                 # Point of Control
    VAH = "vah"                                 # Value Area High
    VAL = "val"                                 # Value Area Low
    PVAH = "pvah"                              # Previous VAH
    PVAL = "pval"                              # Previous VAL
    PPOC = "ppoc"                              # Previous POC
    VOLUME_CLUSTER = "volume_cluster"           # High Volume Node
    SESSION_HIGH = "session_high"               # Session high
    SESSION_LOW = "session_low"                 # Session low
    OVERNIGHT_HIGH = "overnight_high"           # Overnight high
    OVERNIGHT_LOW = "overnight_low"             # Overnight low
    ROUND_NUMBER = "round_number"               # Round number (4500, 4550, etc.)
    PSYCHOLOGICAL = "psychological"             # Psychological level


class ConfluenceQuality(Enum):
    """Qualité confluence"""
    WEAK = "weak"           # 1-2 niveaux
    MODERATE = "moderate"   # 3-4 niveaux
    STRONG = "strong"       # 5-6 niveaux
    EXTREME = "extreme"     # 7+ niveaux


class ConfluenceDirection(Enum):
    """Direction confluence"""
    SUPPORT = "support"     # Zone support (achats)
    RESISTANCE = "resistance"  # Zone résistance (ventes)
    NEUTRAL = "neutral"     # Zone neutre

# === ELITE MTF CONFLUENCE ENUMS ===

class TimeFrameWeight(Enum):
    """Pondération intelligente par timeframe selon volatilité"""
    SCALP_1M = 0.6      # Maximum weight pour scalping précis
    SWING_5M = 0.3      # Weight moyen pour confirmation
    TREND_15M = 0.2     # Weight minimum pour direction générale
    MACRO_1H = 0.1      # Poids faible mais direction macro

# === CONFLUENCE DATA STRUCTURES ===

@dataclass
class Level:
    """Niveau de prix avec métadonnées"""
    price: float
    level_type: LevelType
    strength: float         # 0-1, force du niveau
    age_minutes: int        # Age du niveau
    touches_count: int      # Nombre de fois testé
    last_touch: Optional[datetime] = None

    def is_fresh(self, max_age_minutes: int = 1440) -> bool:
        """Vérifie si niveau est encore frais"""
        return self.age_minutes <= max_age_minutes

    def get_weighted_strength(self) -> float:
        """Force pondérée par age et touches"""
        age_factor = max(0.1, 1 - (self.age_minutes / 1440))  # Décroit sur 24h
        touch_factor = min(2.0, 1 + (self.touches_count * 0.2))  # Bonus touches
        return self.strength * age_factor * touch_factor


@dataclass
class ConfluenceZone:
    """Zone de confluence"""
    center_price: float
    price_min: float
    price_max: float
    levels: List[Level]
    confluence_score: float     # 0-1
    confluence_quality: ConfluenceQuality
    direction: ConfluenceDirection
    dominant_level_types: List[LevelType]

    def get_price_range_ticks(self) -> float:
        """Largeur zone en ticks"""
        return (self.price_max - self.price_min) / ES_TICK_SIZE

    def contains_price(self, price: float) -> bool:
        """Vérifie si prix dans zone"""
        return self.price_min <= price <= self.price_max

    def distance_to_price(self, price: float) -> float:
        """Distance en ticks au prix"""
        if self.contains_price(price):
            return 0.0
        elif price < self.price_min:
            return (self.price_min - price) / ES_TICK_SIZE
        else:
            return (price - self.price_max) / ES_TICK_SIZE


@dataclass
class ConfluenceAnalysis:
    """Résultat analyse confluence"""
    timestamp: datetime
    current_price: float
    zones: List[ConfluenceZone]
    nearest_support_zone: Optional[ConfluenceZone] = None
    nearest_resistance_zone: Optional[ConfluenceZone] = None
    confluence_score_at_price: float = 0.0    # Score confluence au prix actuel
    proximity_score: float = 0.0              # Score proximité zones importantes

    def get_zones_by_quality(self, min_quality: ConfluenceQuality) -> List[ConfluenceZone]:
        """Filtre zones par qualité minimum"""
        quality_order = {
            ConfluenceQuality.WEAK: 1,
            ConfluenceQuality.MODERATE: 2,
            ConfluenceQuality.STRONG: 3,
            ConfluenceQuality.EXTREME: 4
        }
        min_level = quality_order[min_quality]
        return [zone for zone in self.zones
                if quality_order[zone.confluence_quality] >= min_level]

# === 🆕 ELITE MTF CONFLUENCE STRUCTURES ===

@dataclass
class MTFSignalComponent:
    """Composant signal par timeframe pour Elite MTF Confluence"""
    timeframe: str
    signal_strength: float  # -1.0 à +1.0
    confidence: float      # 0.0 à 1.0
    base_quality: float    # 0.0 à 1.0 (qualité pattern Battle Navale)
    volume_confirmation: float  # 0.0 à 1.0
    rouge_sous_verte: bool # Règle d'or Battle Navale
    pattern_completeness: float # 0.0 à 1.0

# === LEVEL WEIGHTS CONFIGURATION ===

LEVEL_WEIGHTS = {
    # Gamma levels (plus importants)
    LevelType.GAMMA_CALL_WALL: 1.0,
    LevelType.GAMMA_PUT_WALL: 1.0,
    LevelType.GAMMA_FLIP: 0.9,

    # Market Profile (très importants)
    LevelType.POC: 0.9,
    LevelType.VAH: 0.8,
    LevelType.VAL: 0.8,
    LevelType.PPOC: 0.7,
    LevelType.PVAH: 0.6,
    LevelType.PVAL: 0.6,

    # VWAP (importants)
    LevelType.VWAP: 0.8,
    LevelType.VWAP_SD1_UP: 0.7,
    LevelType.VWAP_SD1_DOWN: 0.7,
    LevelType.VWAP_SD2_UP: 0.6,
    LevelType.VWAP_SD2_DOWN: 0.6,

    # Volume (modérément importants)
    LevelType.VOLUME_CLUSTER: 0.6,

    # Session levels (modérément importants)
    LevelType.SESSION_HIGH: 0.5,
    LevelType.SESSION_LOW: 0.5,
    LevelType.OVERNIGHT_HIGH: 0.4,
    LevelType.OVERNIGHT_LOW: 0.4,

    # Psychological (moins importants)
    LevelType.ROUND_NUMBER: 0.3,
    LevelType.PSYCHOLOGICAL: 0.2
}

# === 🆕 ELITE MTF CONFLUENCE CLASS ===

class EliteMTFConfluence:
    """
    🎯 TECHNIQUE ELITE: Multi-Timeframe Confluence
    IMPACT CIBLE: +2-3% win rate sur Battle Navale
    
    Innovation vs version basique:
    ✅ Pondération dynamique selon volatilité
    ✅ Bonus qualité pattern par TF
    ✅ Pénalités divergences critiques
    ✅ Filtrage noise sur TF courts
    ✅ Confluence graduelle (pas binaire)
    """
    
    def __init__(self, battle_navale_analyzer=None):
        self.volatility_lookback = 20
        self.min_confluence_threshold = 0.35
        self.elite_confluence_threshold = 0.75
        self.battle_navale_analyzer = battle_navale_analyzer
        
    def calculate_dynamic_weights(self, market_data: Dict) -> Dict[str, float]:
        """
        🧠 Pondération dynamique selon conditions marché
        Plus la volatilité est forte, plus on privilégie TF courts
        """
        current_vol = self._calculate_realized_volatility(market_data)
        
        if current_vol > 0.8:  # Haute volatilité
            return {
                "1min": 0.7,   # Maximum précision
                "5min": 0.2,
                "15min": 0.1,
                "1hour": 0.0   # Ignore macro en haute vol
            }
        elif current_vol > 0.4:  # Volatilité normale
            return {
                "1min": 0.5,
                "5min": 0.3,
                "15min": 0.15,
                "1hour": 0.05
            }
        else:  # Basse volatilité
            return {
                "1min": 0.3,   # Moins de poids aux TF courts
                "5min": 0.3,
                "15min": 0.25,
                "1hour": 0.15  # Plus de poids aux TF longs
            }
    
    def get_battle_navale_signal_enhanced(self, timeframe: str, market_data: Dict) -> MTFSignalComponent:
        """
        🔍 Version améliorée du signal Battle Navale par TF
        Intègre tous les éléments qualitatifs
        """
        # Utilise le vrai analyzer Battle Navale si disponible
        if self.battle_navale_analyzer:
            base_signal = self._get_real_battle_signal(timeframe, market_data)
        else:
            base_signal = self._get_mock_battle_signal(timeframe, market_data)
        
        # Calculs qualitatifs spécifiques
        base_quality = self._assess_base_quality(timeframe, market_data)
        volume_conf = self._assess_volume_confirmation(timeframe, market_data)
        rouge_sous_verte = self._check_rouge_sous_verte_rule(timeframe, market_data)
        pattern_complete = self._assess_pattern_completeness(timeframe, market_data)
        
        # Confidence composite
        confidence = np.mean([base_quality, volume_conf, pattern_complete])
        if rouge_sous_verte:
            confidence *= 1.15  # Bonus règle d'or
        
        return MTFSignalComponent(
            timeframe=timeframe,
            signal_strength=base_signal,
            confidence=confidence,
            base_quality=base_quality,
            volume_confirmation=volume_conf,
            rouge_sous_verte=rouge_sous_verte,
            pattern_completeness=pattern_complete
        )
    
    def calculate_elite_mtf_confluence(self, market_data: Dict) -> Tuple[float, Dict]:
        """
        🎯 FONCTION PRINCIPALE - Confluence Multi-Timeframe Elite
        
        Returns:
            confluence_score: Score final -1.0 à +1.0
            detailed_analysis: Analyse détaillée par composant
        """
        # 1. Weights dynamiques selon conditions marché
        dynamic_weights = self.calculate_dynamic_weights(market_data)
        
        # 2. Signaux par timeframe avec analyse complète
        timeframes = ["1min", "5min", "15min", "1hour"]
        signals = {}
        
        for tf in timeframes:
            signals[tf] = self.get_battle_navale_signal_enhanced(tf, market_data)
        
        # 3. Score de base pondéré
        base_score = 0.0
        total_weight = 0.0
        
        for tf, weight in dynamic_weights.items():
            if tf in signals and weight > 0:
                signal = signals[tf]
                # Pondération par strength ET confidence
                weighted_signal = signal.signal_strength * signal.confidence * weight
                base_score += weighted_signal
                total_weight += weight
        
        if total_weight > 0:
            base_score /= total_weight
        
        # 4. Bonus alignement parfait (tous TF même direction)
        alignment_bonus = self._calculate_alignment_bonus(signals, dynamic_weights)
        
        # 5. Bonus qualité moyenne des patterns
        quality_bonus = self._calculate_quality_bonus(signals, dynamic_weights)
        
        # 6. Pénalité divergences critiques
        divergence_penalty = self._calculate_divergence_penalty(signals, dynamic_weights)
        
        # 7. Score final avec tous les ajustements
        final_score = base_score + alignment_bonus + quality_bonus - divergence_penalty
        final_score = np.clip(final_score, -1.0, 1.0)
        
        # 8. Analyse détaillée pour debugging/monitoring
        detailed_analysis = {
            "base_score": base_score,
            "alignment_bonus": alignment_bonus,
            "quality_bonus": quality_bonus,
            "divergence_penalty": divergence_penalty,
            "final_score": final_score,
            "dynamic_weights": dynamic_weights,
            "signals_by_tf": {tf: {
                "strength": sig.signal_strength,
                "confidence": sig.confidence,
                "base_quality": sig.base_quality,
                "rouge_sous_verte": sig.rouge_sous_verte
            } for tf, sig in signals.items()},
            "market_regime": self._detect_market_regime(market_data)
        }
        
        return final_score, detailed_analysis
    
    def _calculate_alignment_bonus(self, signals: Dict, weights: Dict) -> float:
        """🎯 Bonus when all timeframes align perfectly"""
        weighted_signals = []
        
        for tf, weight in weights.items():
            if tf in signals and weight > 0:
                sig = signals[tf]
                if sig.confidence > 0.6:  # Seulement signaux fiables
                    weighted_signals.append(sig.signal_strength)
        
        if len(weighted_signals) < 2:
            return 0.0
        
        # Tous positifs ou tous négatifs = alignment
        all_positive = all(s > 0.2 for s in weighted_signals)
        all_negative = all(s < -0.2 for s in weighted_signals)
        
        if all_positive or all_negative:
            # Bonus proportionnel au nombre de TF alignés
            return 0.15 * (len(weighted_signals) / len(weights))
        
        return 0.0
    
    def _calculate_quality_bonus(self, signals: Dict, weights: Dict) -> float:
        """⭐ Bonus pour haute qualité moyenne des patterns"""
        quality_scores = []
        
        for tf, weight in weights.items():
            if tf in signals and weight > 0:
                sig = signals[tf]
                # Combine base quality + pattern completeness
                combined_quality = (sig.base_quality + sig.pattern_completeness) / 2
                quality_scores.append(combined_quality * weight)
        
        if not quality_scores:
            return 0.0
        
        avg_quality = np.mean(quality_scores)
        
        # Bonus progressif pour haute qualité
        if avg_quality > 0.8:
            return 0.12
        elif avg_quality > 0.7:
            return 0.08
        elif avg_quality > 0.6:
            return 0.04
        
        return 0.0
    
    def _calculate_divergence_penalty(self, signals: Dict, weights: Dict) -> float:
        """⚠️ Pénalité pour divergences critiques entre TF"""
        high_weight_signals = []
        
        for tf, weight in weights.items():
            if tf in signals and weight >= 0.3:  # TF importants seulement
                sig = signals[tf]
                if sig.confidence > 0.5:
                    high_weight_signals.append(sig.signal_strength)
        
        if len(high_weight_signals) < 2:
            return 0.0
        
        # Divergence = signaux opposés sur TF importants
        has_strong_long = any(s > 0.4 for s in high_weight_signals)
        has_strong_short = any(s < -0.4 for s in high_weight_signals)
        
        if has_strong_long and has_strong_short:
            return 0.2  # Pénalité forte pour divergence majeure
        
        return 0.0
    
    # Méthodes de connection avec Battle Navale
    def _get_real_battle_signal(self, timeframe: str, market_data: Dict) -> float:
        """Connection avec le vrai analyzer Battle Navale"""
        try:
            # Créer MarketData pour le timeframe spécifique
            tf_market_data = self._adapt_market_data_for_timeframe(market_data, timeframe)
            
            # Appeler l'analyzer Battle Navale
            result = self.battle_navale_analyzer.analyze_battle_navale(tf_market_data)
            
            # Convertir en signal -1 à +1
            if result.battle_status.value == "BATAILLE_GAGNEE":
                return result.signal_confidence * (1 if result.signal_confidence > 0 else -1)
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Erreur signal Battle Navale TF {timeframe}: {e}")
            return self._get_mock_battle_signal(timeframe, market_data)
    
    def _adapt_market_data_for_timeframe(self, market_data: Dict, timeframe: str) -> MarketData:
        """Adapte les données marché pour le timeframe"""
        # Logique d'adaptation selon timeframe
        # Pour l'instant, retourne données de base
        return MarketData(
            timestamp=pd.Timestamp.now(),
            symbol=market_data.get("symbol", "ES"),
            open=market_data.get("current_price", 4150.0),
            high=market_data.get("current_price", 4150.0),
            low=market_data.get("current_price", 4150.0),
            close=market_data.get("current_price", 4150.0),
            volume=market_data.get("volume", 1000)
        )
    
    # Méthodes utilitaires (adaptables selon données réelles)
    def _calculate_realized_volatility(self, market_data: Dict) -> float:
        """Calculate current market volatility (0-1 scale)"""
        # Implémentation basique - à améliorer avec vraies données
        return market_data.get("volatility", 0.5)
    
    def _get_mock_battle_signal(self, timeframe: str, market_data: Dict) -> float:
        """Signal Battle Navale simulé"""
        # Simulation pour tests - remplacer par vraie implémentation
        return np.random.uniform(-0.8, 0.8)
    
    def _assess_base_quality(self, timeframe: str, market_data: Dict) -> float:
        """Assess quality of the base pattern"""
        return market_data.get(f"base_quality_{timeframe}", np.random.uniform(0.4, 0.9))
    
    def _assess_volume_confirmation(self, timeframe: str, market_data: Dict) -> float:
        """Check volume confirmation of the pattern"""
        return market_data.get(f"volume_conf_{timeframe}", np.random.uniform(0.3, 0.8))
    
    def _check_rouge_sous_verte_rule(self, timeframe: str, market_data: Dict) -> bool:
        """Check the Rouge Sous Verte golden rule"""
        return market_data.get(f"rouge_sous_verte_{timeframe}", np.random.choice([True, False], p=[0.7, 0.3]))
    
    def _assess_pattern_completeness(self, timeframe: str, market_data: Dict) -> float:
        """Assess how complete/mature the pattern is"""
        return market_data.get(f"pattern_complete_{timeframe}", np.random.uniform(0.5, 0.95))
    
    def _detect_market_regime(self, market_data: Dict) -> str:
        """Detect current market regime"""
        return market_data.get("market_regime", np.random.choice(["TREND", "RANGE", "BREAKOUT"]))

# === MAIN CONFLUENCE ANALYZER ===

class ConfluenceAnalyzer:
    """Analyseur multi-level confluence pour Battle Navale"""

    def __init__(self, config=None, tolerance_ticks: float = 3.0):
        """
        Args:
            config: Configuration dictionary (optional)
            tolerance_ticks: Tolérance pour regrouper niveaux (en ticks)
        """
        # Configuration en premier (utilise paramètre config ou dict vide)
        self.config = config or {}

        # Utilise config si disponible, sinon garde paramètre tolerance_ticks
        tolerance_ticks = self.config.get('tolerance_ticks', tolerance_ticks)
        self.tolerance_ticks = tolerance_ticks

        # Tolerance en prix (protection contre valeurs None)
        if ES_TICK_SIZE is None:
            raise ValueError("ES_TICK_SIZE is None - Import problem in core.base_types")
        if not isinstance(tolerance_ticks, (int, float)):
            raise ValueError(f"tolerance_ticks must be numeric, got {type(tolerance_ticks)}")

        self.tolerance_price = float(tolerance_ticks) * float(ES_TICK_SIZE)

        # Cache niveaux
        self.cached_levels: Dict[LevelType, List[Level]] = defaultdict(list)
        self.last_update: Optional[datetime] = None

        # Performance tracking
        self.stats = {
            'analyses_count': 0,
            'avg_analysis_time_ms': 0.0,
            'zones_detected': 0,
            'strong_zones_count': 0
        }

        # 🆕 INTEGRATION ELITE MTF CONFLUENCE
        self.elite_mtf = EliteMTFConfluence()

        # 🆕 MENTHORQ INTEGRATION
        if MENTHORQ_AVAILABLE:
            try:
                self.menthorq_integration = MenthorQIntegration()
                logger.info("✅ MenthorQ Integration intégré dans ConfluenceAnalyzer")
            except Exception as e:
                logger.error(f"❌ Erreur initialisation MenthorQ: {e}")
                self.menthorq_integration = None
        else:
            self.menthorq_integration = None
            logger.warning("⚠️ MenthorQ Integration non disponible")

        logger.info(f"ConfluenceAnalyzer initialisé (tolérance: {tolerance_ticks} ticks)")

    def set_battle_navale_analyzer(self, battle_navale_analyzer):
        """🔗 Connecte l'analyzer Battle Navale pour MTF Elite"""
        self.elite_mtf.battle_navale_analyzer = battle_navale_analyzer
        logger.info("Battle Navale analyzer connecté pour MTF Elite")

    def analyze_confluence(self,
                           market_data: MarketData,
                           gamma_data: Optional[Dict[str, Any]] = None,
                           market_profile_data: Optional[Dict[str, Any]] = None,
                           vwap_data: Optional[Dict[str, Any]] = None,
                           volume_data: Optional[Dict[str, Any]] = None,
                           session_data: Optional[Dict[str, Any]] = None) -> ConfluenceAnalysis:
        """
        ANALYSE CONFLUENCE COMPLÈTE

        Args:
            market_data: Données OHLC actuelles
            gamma_data: Niveaux gamma options
            market_profile_data: VAH/VAL/POC
            vwap_data: VWAP + bandes
            volume_data: Volume clusters
            session_data: Session levels

        Returns:
            ConfluenceAnalysis avec zones détectées
        """
        start_time = time.perf_counter()

        try:
            # 1. Collecter tous les niveaux
            all_levels = self._collect_all_levels(
                market_data, gamma_data, market_profile_data,
                vwap_data, volume_data, session_data
            )

            # 2. Regrouper en zones de confluence
            confluence_zones = self._group_levels_into_zones(all_levels)

            # 3. Scorer et qualifier zones
            for zone in confluence_zones:
                self._calculate_zone_metrics(zone, market_data.close)

            # 4. Identifier zones clés
            nearest_support = self._find_nearest_support(confluence_zones, market_data.close)
            nearest_resistance = self._find_nearest_resistance(confluence_zones, market_data.close)

            # 5. Calculer scores globaux
            confluence_at_price = self._calculate_confluence_at_price(all_levels, market_data.close)
            proximity_score = self._calculate_proximity_score(confluence_zones, market_data.close)

            # Créer analyse
            analysis = ConfluenceAnalysis(
                timestamp=market_data.timestamp,
                current_price=market_data.close,
                zones=confluence_zones,
                nearest_support_zone=nearest_support,
                nearest_resistance_zone=nearest_resistance,
                confluence_score_at_price=confluence_at_price,
                proximity_score=proximity_score
            )

            # Update stats
            analysis_time = (time.perf_counter() - start_time) * 1000
            self._update_stats(analysis_time, len(confluence_zones))

            logger.debug(
                f"Confluence analysée: {
                    len(confluence_zones)} zones en {
                    analysis_time:.2f}ms")

            return analysis

        except Exception as e:
            logger.error(f"Erreur analyse confluence: {e}")
            # Retour analyse vide en cas d'erreur
            return ConfluenceAnalysis(
                timestamp=market_data.timestamp,
                current_price=market_data.close,
                zones=[]
            )

    def calculate_elite_mtf_confluence(self, market_data_dict: Dict) -> Tuple[float, Dict]:
        """
        🎯 NOUVELLE MÉTHODE - Elite Multi-Timeframe Confluence
        
        Args:
            market_data_dict: Données marché format dict pour MTF
            
        Returns:
            tuple: (confluence_score, detailed_analysis)
        """
        return self.elite_mtf.calculate_elite_mtf_confluence(market_data_dict)

    def _collect_all_levels(self,
                            market_data: MarketData,
                            gamma_data: Optional[Dict[str, Any]],
                            market_profile_data: Optional[Dict[str, Any]],
                            vwap_data: Optional[Dict[str, Any]],
                            volume_data: Optional[Dict[str, Any]],
                            session_data: Optional[Dict[str, Any]]) -> List[Level]:
        """Collecte tous les niveaux de prix + 🆕 MenthorQ"""
        levels = []

        # 1. Gamma levels (options flow)
        if gamma_data:
            levels.extend(self._extract_gamma_levels(gamma_data))

        # 2. Market Profile levels
        if market_profile_data:
            levels.extend(self._extract_market_profile_levels(market_profile_data))

        # 3. VWAP levels
        if vwap_data:
            levels.extend(self._extract_vwap_levels(vwap_data))

        # 4. Volume levels
        if volume_data:
            levels.extend(self._extract_volume_levels(volume_data))

        # 5. Session levels
        if session_data:
            levels.extend(self._extract_session_levels(session_data))

        # 6. Round numbers automatiques
        levels.extend(self._generate_round_number_levels(market_data.close))

        # 🆕 7. MenthorQ Levels (38 niveaux)
        try:
            menthorq_levels = self._extract_menthorq_levels(market_data.close)
            levels.extend(menthorq_levels)
            logger.debug(f"✅ {len(menthorq_levels)} niveaux MenthorQ ajoutés à la confluence")
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction MenthorQ: {e}")

        # Filtrer niveaux valides et trier
        valid_levels = [level for level in levels if self._is_level_valid(level, market_data)]
        valid_levels.sort(key=lambda x: x.price)

        return valid_levels

    def _extract_gamma_levels(self, gamma_data: Dict[str, Any]) -> List[Level]:
        """Extrait niveaux gamma"""
        levels = []

        # Call wall (résistance)
        if 'call_wall' in gamma_data and gamma_data['call_wall']:
            levels.append(Level(
                price=float(gamma_data['call_wall']),
                level_type=LevelType.GAMMA_CALL_WALL,
                strength=0.9,
                age_minutes=gamma_data.get('call_wall_age', 60),
                touches_count=gamma_data.get('call_wall_touches', 0)
            ))

        # Put wall (support)
        if 'put_wall' in gamma_data and gamma_data['put_wall']:
            levels.append(Level(
                price=float(gamma_data['put_wall']),
                level_type=LevelType.GAMMA_PUT_WALL,
                strength=0.9,
                age_minutes=gamma_data.get('put_wall_age', 60),
                touches_count=gamma_data.get('put_wall_touches', 0)
            ))

        # Gamma flip point
        if 'gamma_flip' in gamma_data and gamma_data['gamma_flip']:
            levels.append(Level(
                price=float(gamma_data['gamma_flip']),
                level_type=LevelType.GAMMA_FLIP,
                strength=0.8,
                age_minutes=gamma_data.get('gamma_flip_age', 120),
                touches_count=0
            ))

        return levels

    def _extract_market_profile_levels(self, profile_data: Dict[str, Any]) -> List[Level]:
        """Extrait niveaux Market Profile"""
        levels = []

        # Current session
        if 'poc' in profile_data:
            levels.append(Level(
                price=float(profile_data['poc']),
                level_type=LevelType.POC,
                strength=0.8,
                age_minutes=profile_data.get('poc_age', 180),
                touches_count=profile_data.get('poc_touches', 1)
            ))

        if 'vah' in profile_data:
            levels.append(Level(
                price=float(profile_data['vah']),
                level_type=LevelType.VAH,
                strength=0.7,
                age_minutes=profile_data.get('vah_age', 180),
                touches_count=profile_data.get('vah_touches', 0)
            ))

        if 'val' in profile_data:
            levels.append(Level(
                price=float(profile_data['val']),
                level_type=LevelType.VAL,
                strength=0.7,
                age_minutes=profile_data.get('val_age', 180),
                touches_count=profile_data.get('val_touches', 0)
            ))

        # VVA previous fields removed - no previous session levels

        return levels

    def _extract_vwap_levels(self, vwap_data: Dict[str, Any]) -> List[Level]:
        """Extrait niveaux VWAP"""
        levels = []

        if 'vwap' in vwap_data:
            levels.append(Level(
                price=float(vwap_data['vwap']),
                level_type=LevelType.VWAP,
                strength=0.7,
                age_minutes=vwap_data.get('vwap_age', 300),
                touches_count=vwap_data.get('vwap_touches', 3)
            ))

        # VWAP bands
        if 'vwap_sd1_up' in vwap_data:
            levels.append(Level(
                price=float(vwap_data['vwap_sd1_up']),
                level_type=LevelType.VWAP_SD1_UP,
                strength=0.6,
                age_minutes=300,
                touches_count=1
            ))

        if 'vwap_sd1_down' in vwap_data:
            levels.append(Level(
                price=float(vwap_data['vwap_sd1_down']),
                level_type=LevelType.VWAP_SD1_DOWN,
                strength=0.6,
                age_minutes=300,
                touches_count=1
            ))

        if 'vwap_sd2_up' in vwap_data:
            levels.append(Level(
                price=float(vwap_data['vwap_sd2_up']),
                level_type=LevelType.VWAP_SD2_UP,
                strength=0.5,
                age_minutes=300,
                touches_count=0
            ))

        if 'vwap_sd2_down' in vwap_data:
            levels.append(Level(
                price=float(vwap_data['vwap_sd2_down']),
                level_type=LevelType.VWAP_SD2_DOWN,
                strength=0.5,
                age_minutes=300,
                touches_count=0
            ))

        return levels

    def _extract_volume_levels(self, volume_data: Dict[str, Any]) -> List[Level]:
        """Extrait niveaux volume"""
        levels = []

        # High Volume Nodes
        if 'volume_clusters' in volume_data:
            for i, cluster_price in enumerate(volume_data['volume_clusters']):
                levels.append(Level(
                    price=float(cluster_price),
                    level_type=LevelType.VOLUME_CLUSTER,
                    strength=0.5,
                    age_minutes=volume_data.get('cluster_ages', [360])[min(
                        i, len(volume_data.get('cluster_ages', [])) - 1)],
                    touches_count=volume_data.get('cluster_touches', [2])[min(
                        i, len(volume_data.get('cluster_touches', [])) - 1)]
                ))

        return levels

    def _extract_session_levels(self, session_data: Dict[str, Any]) -> List[Level]:
        """Extrait niveaux session"""
        levels = []

        if 'session_high' in session_data:
            levels.append(Level(
                price=float(session_data['session_high']),
                level_type=LevelType.SESSION_HIGH,
                strength=0.4,
                age_minutes=session_data.get('session_high_age', 240),
                touches_count=session_data.get('session_high_touches', 1)
            ))

        if 'session_low' in session_data:
            levels.append(Level(
                price=float(session_data['session_low']),
                level_type=LevelType.SESSION_LOW,
                strength=0.4,
                age_minutes=session_data.get('session_low_age', 240),
                touches_count=session_data.get('session_low_touches', 1)
            ))

        if 'overnight_high' in session_data:
            levels.append(Level(
                price=float(session_data['overnight_high']),
                level_type=LevelType.OVERNIGHT_HIGH,
                strength=0.3,
                age_minutes=session_data.get('overnight_high_age', 600),
                touches_count=1
            ))

        if 'overnight_low' in session_data:
            levels.append(Level(
                price=float(session_data['overnight_low']),
                level_type=LevelType.OVERNIGHT_LOW,
                strength=0.3,
                age_minutes=session_data.get('overnight_low_age', 600),
                touches_count=1
            ))

        return levels

    def _generate_round_number_levels(self, current_price: float) -> List[Level]:
        """Génère niveaux round numbers proches"""
        levels = []

        # Round numbers sur 25 ticks (ES: 4500, 4525, 4550, etc.)
        base_price = int(current_price / 25) * 25

        for offset in [-50, -25, 0, 25, 50]:  # ±50 points
            round_price = base_price + offset
            if abs(round_price - current_price) <= 50:  # Dans range ±50 points
                levels.append(Level(
                    price=float(round_price),
                    level_type=LevelType.ROUND_NUMBER,
                    strength=0.3,
                    age_minutes=0,  # Toujours frais
                    touches_count=0
                ))

        # Round numbers psychologiques (4500, 4600, etc.)
        base_hundred = int(current_price / 100) * 100

        for offset in [-100, 0, 100]:
            psych_price = base_hundred + offset
            if abs(psych_price - current_price) <= 100 and psych_price % 100 == 0:
                levels.append(Level(
                    price=float(psych_price),
                    level_type=LevelType.PSYCHOLOGICAL,
                    strength=0.2,
                    age_minutes=0,
                    touches_count=0
                ))

        return levels

    def _group_levels_into_zones(self, levels: List[Level]) -> List[ConfluenceZone]:
        """Regroupe niveaux en zones de confluence"""
        if not levels:
            return []

        zones = []
        used_levels = set()

        for i, level in enumerate(levels):
            if i in used_levels:
                continue

            # Trouver tous les niveaux dans la tolérance
            zone_levels = [level]
            used_levels.add(i)

            for j, other_level in enumerate(levels[i+1:], i+1):
                if j in used_levels:
                    continue

                if abs(other_level.price - level.price) <= self.tolerance_price:
                    zone_levels.append(other_level)
                    used_levels.add(j)
                elif other_level.price - level.price > self.tolerance_price:
                    break  # Sorted list, no need to check further

            # Créer zone si au moins 1 niveau (ou 2+ pour confluence vraie)
            if len(zone_levels) >= 1:
                zones.append(self._create_confluence_zone(zone_levels))

        return zones

    def _create_confluence_zone(self, levels: List[Level]) -> ConfluenceZone:
        """Crée zone confluence depuis liste niveaux"""
        if not levels:
            raise ValueError("Cannot create zone with no levels")

        # Calculer bornes zone
        prices = [level.price for level in levels]
        center_price = np.mean(prices)
        price_min = min(prices) - self.tolerance_price / 2
        price_max = max(prices) + self.tolerance_price / 2

        # Déterminer types dominants
        level_types = [level.level_type for level in levels]
        type_counts = {}
        for level_type in level_types:
            type_counts[level_type] = type_counts.get(level_type, 0) + 1

        # Types les plus fréquents
        dominant_types = sorted(type_counts.keys(),
                                key=lambda x: type_counts[x], reverse=True)[:3]

        # Zone temporaire (score calculé plus tard)
        zone = ConfluenceZone(
            center_price=center_price,
            price_min=price_min,
            price_max=price_max,
            levels=levels,
            confluence_score=0.0,  # Calculé dans _calculate_zone_metrics
            confluence_quality=ConfluenceQuality.WEAK,  # Calculé plus tard
            direction=ConfluenceDirection.NEUTRAL,  # Calculé plus tard
            dominant_level_types=dominant_types
        )

        return zone

    def _calculate_zone_metrics(self, zone: ConfluenceZone, current_price: float):
        """Calcule métriques de la zone"""

        # 1. Score confluence basé sur force pondérée des niveaux
        total_weighted_strength = 0.0
        for level in zone.levels:
            weight = LEVEL_WEIGHTS.get(level.level_type, 0.5)
            weighted_strength = level.get_weighted_strength() * weight
            total_weighted_strength += weighted_strength

        # Normaliser par nombre maximum attendu de niveaux (8)
        zone.confluence_score = min(1.0, total_weighted_strength / 8.0)

        # 2. Qualité basée sur score et nombre de niveaux
        num_levels = len(zone.levels)
        if zone.confluence_score >= 0.8 or num_levels >= 7:
            zone.confluence_quality = ConfluenceQuality.EXTREME
        elif zone.confluence_score >= 0.6 or num_levels >= 5:
            zone.confluence_quality = ConfluenceQuality.STRONG
        elif zone.confluence_score >= 0.4 or num_levels >= 3:
            zone.confluence_quality = ConfluenceQuality.MODERATE
        else:
            zone.confluence_quality = ConfluenceQuality.WEAK

        # 3. Direction basée sur position relative au prix
        if zone.center_price > current_price:
            zone.direction = ConfluenceDirection.RESISTANCE
        elif zone.center_price < current_price:
            zone.direction = ConfluenceDirection.SUPPORT
        else:
            zone.direction = ConfluenceDirection.NEUTRAL

    def _find_nearest_support(self, zones: List[ConfluenceZone],
                              current_price: float) -> Optional[ConfluenceZone]:
        """Trouve zone support la plus proche en dessous"""
        support_zones = [zone for zone in zones
                         if zone.direction == ConfluenceDirection.SUPPORT]

        if not support_zones:
            return None

        # Plus proche en dessous
        return min(support_zones,
                   key=lambda z: z.distance_to_price(current_price))

    def _find_nearest_resistance(self, zones: List[ConfluenceZone],
                                 current_price: float) -> Optional[ConfluenceZone]:
        """Trouve zone résistance la plus proche au dessus"""
        resistance_zones = [zone for zone in zones
                            if zone.direction == ConfluenceDirection.RESISTANCE]

        if not resistance_zones:
            return None

        # Plus proche au dessus
        return min(resistance_zones,
                   key=lambda z: z.distance_to_price(current_price))

    def _calculate_confluence_at_price(self, levels: List[Level],
                                       price: float) -> float:
        """Calcule score confluence au prix donné"""
        confluence_strength = 0.0

        for level in levels:
            distance_ticks = abs(level.price - price) / ES_TICK_SIZE

            # Influence décroît avec distance (max 10 ticks)
            if distance_ticks <= 10:
                proximity_factor = max(0, 1 - (distance_ticks / 10))
                weight = LEVEL_WEIGHTS.get(level.level_type, 0.5)
                level_strength = level.get_weighted_strength() * weight * proximity_factor
                confluence_strength += level_strength

        return min(1.0, confluence_strength / 5.0)  # Normaliser sur 5 niveaux max

    def _calculate_proximity_score(self, zones: List[ConfluenceZone],
                                   current_price: float) -> float:
        """Calcule score proximité zones importantes"""
        if not zones:
            return 0.0

        # Trouver zones importantes proches (< 20 ticks)
        important_zones = [zone for zone in zones
                           if zone.confluence_quality in [ConfluenceQuality.STRONG, ConfluenceQuality.EXTREME]
                           and zone.distance_to_price(current_price) <= 20]

        if not important_zones:
            return 0.0

        # Score basé sur proximité et qualité
        total_score = 0.0
        for zone in important_zones:
            distance = zone.distance_to_price(current_price)
            proximity_factor = max(0, 1 - (distance / 20))  # Décroit sur 20 ticks

            quality_multiplier = {
                ConfluenceQuality.EXTREME: 1.0,
                ConfluenceQuality.STRONG: 0.8,
                ConfluenceQuality.MODERATE: 0.6,
                ConfluenceQuality.WEAK: 0.4
            }[zone.confluence_quality]

            zone_score = zone.confluence_score * proximity_factor * quality_multiplier
            total_score += zone_score

        return min(1.0, total_score)

    def _is_level_valid(self, level: Level, market_data: MarketData) -> bool:
        """Vérifie si niveau est valide"""
        # Distance raisonnable du prix actuel (± 200 points)
        if abs(level.price - market_data.close) > 200:
            return False

        # Niveau pas trop ancien (24h max pour la plupart)
        max_age_by_type = {
            LevelType.GAMMA_CALL_WALL: 480,  # 8h
            LevelType.GAMMA_PUT_WALL: 480,   # 8h
            LevelType.GAMMA_FLIP: 720,       # 12h
            LevelType.POC: 1440,             # 24h
            LevelType.VAH: 1440,             # 24h
            LevelType.VAL: 1440,             # 24h
            LevelType.VWAP: 1440,            # 24h
            LevelType.ROUND_NUMBER: 99999,   # Toujours valide
            LevelType.PSYCHOLOGICAL: 99999   # Toujours valide
        }

        max_age = max_age_by_type.get(level.level_type, 1440)
        if level.age_minutes > max_age:
            return False

        return True

    def _update_stats(self, analysis_time_ms: float, zones_count: int):
        """Update statistiques performance"""
        self.stats['analyses_count'] += 1
        self.stats['zones_detected'] += zones_count

        # Moyenne mobile temps analyse
        current_avg = self.stats['avg_analysis_time_ms']
        count = self.stats['analyses_count']

        self.stats['avg_analysis_time_ms'] = (
            (current_avg * (count - 1) + analysis_time_ms) / count
        )

    # === 🆕 MENTHORQ METHODS ===

    def _extract_menthorq_levels(self, current_price: float) -> List[Level]:
        """🆕 Extrait les 38 niveaux MenthorQ pour la confluence"""
        if not self.menthorq_integration:
            return []
        
        try:
            # Récupérer les données MenthorQ
            menthorq_levels = self.menthorq_integration.parse_menthorq_data()
            levels = []
            
            # Convertir les niveaux MenthorQ en Level objects
            for menthorq_level in menthorq_levels.get_all_levels():
                # Mapping des types MenthorQ vers LevelType
                level_type = self._map_menthorq_to_level_type(menthorq_level.level_type)
                
                # Calculer la force basée sur la distance
                distance = abs(current_price - menthorq_level.price)
                strength = self._calculate_menthorq_strength(distance, menthorq_level.level_type)
                
                levels.append(Level(
                    price=menthorq_level.price,
                    level_type=level_type,
                    strength=strength,
                    age_minutes=0,  # MenthorQ temps réel
                    touches_count=0
                ))
            
            logger.debug(f"✅ {len(levels)} niveaux MenthorQ extraits")
            return levels
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction MenthorQ: {e}")
            return []
    
    def _map_menthorq_to_level_type(self, menthorq_type) -> LevelType:
        """Mappe les types MenthorQ vers LevelType"""
        mapping = {
            MenthorQLevelType.CALL_RESISTANCE: LevelType.GAMMA_CALL_WALL,
            MenthorQLevelType.PUT_SUPPORT: LevelType.GAMMA_PUT_WALL,
            MenthorQLevelType.HVL: LevelType.VOLUME_HIGH,
            MenthorQLevelType.ONE_D_MIN: LevelType.SESSION_LOW,
            MenthorQLevelType.ONE_D_MAX: LevelType.SESSION_HIGH,
            MenthorQLevelType.CALL_RESISTANCE_0DTE: LevelType.GAMMA_CALL_WALL,
            MenthorQLevelType.PUT_SUPPORT_0DTE: LevelType.GAMMA_PUT_WALL,
            MenthorQLevelType.GAMMA_WALL_0DTE: LevelType.GAMMA_CALL_WALL,
        }
        
        # Pour les GEX et BL levels, utiliser des types génériques
        if "GEX" in str(menthorq_type):
            return LevelType.GAMMA_CALL_WALL
        elif "BL" in str(menthorq_type):
            return LevelType.VOLUME_HIGH
        else:
            return mapping.get(menthorq_type, LevelType.TECHNICAL_LEVEL)
    
    def _calculate_menthorq_strength(self, distance: float, level_type) -> float:
        """Calcule la force d'un niveau MenthorQ basée sur la distance et le type"""
        # Force de base selon le type
        base_strength = {
            MenthorQLevelType.GAMMA_WALL_0DTE: 0.95,
            MenthorQLevelType.CALL_RESISTANCE_0DTE: 0.90,
            MenthorQLevelType.PUT_SUPPORT_0DTE: 0.90,
            MenthorQLevelType.CALL_RESISTANCE: 0.80,
            MenthorQLevelType.PUT_SUPPORT: 0.80,
            MenthorQLevelType.HVL: 0.75,
        }.get(level_type, 0.70)
        
        # Réduction basée sur la distance
        if distance < 5.0:  # Très proche
            distance_multiplier = 1.0
        elif distance < 15.0:  # Proche
            distance_multiplier = 0.8
        elif distance < 30.0:  # Moyennement proche
            distance_multiplier = 0.6
        else:  # Loin
            distance_multiplier = 0.3
        
        return base_strength * distance_multiplier

    # === PUBLIC METHODS ===

    def get_confluence_score_for_price(self, price: float,
                                       analysis: ConfluenceAnalysis) -> float:
        """Calcule score confluence pour prix donné"""
        return self._calculate_confluence_at_price(
            [level for zone in analysis.zones for level in zone.levels],
            price
        )

    def find_zones_near_price(self, price: float,
                              analysis: ConfluenceAnalysis,
                              max_distance_ticks: float = 10) -> List[ConfluenceZone]:
        """Trouve zones confluence proche d'un prix"""
        return [zone for zone in analysis.zones
                if zone.distance_to_price(price) <= max_distance_ticks]

    def get_confluence_summary(self, analysis: ConfluenceAnalysis) -> Dict[str, Any]:
        """Résumé confluence pour Battle Navale"""
        summary = {
            'total_zones': len(analysis.zones),
            'strong_zones': len(analysis.get_zones_by_quality(ConfluenceQuality.STRONG)),
            'confluence_at_price': analysis.confluence_score_at_price,
            'proximity_score': analysis.proximity_score,
            'nearest_support': {
                'price': analysis.nearest_support_zone.center_price if analysis.nearest_support_zone else None,
                'distance_ticks': analysis.nearest_support_zone.distance_to_price(analysis.current_price) if analysis.nearest_support_zone else None,
                'quality': analysis.nearest_support_zone.confluence_quality.value if analysis.nearest_support_zone else None
            },
            'nearest_resistance': {
                'price': analysis.nearest_resistance_zone.center_price if analysis.nearest_resistance_zone else None,
                'distance_ticks': analysis.nearest_resistance_zone.distance_to_price(analysis.current_price) if analysis.nearest_resistance_zone else None,
                'quality': analysis.nearest_resistance_zone.confluence_quality.value if analysis.nearest_resistance_zone else None
            }
        }

        return summary

    def get_statistics(self) -> Dict[str, Any]:
        """Statistiques confluence analyzer"""
        return {
            'analyses_count': self.stats['analyses_count'],
            'avg_analysis_time_ms': round(self.stats['avg_analysis_time_ms'], 3),
            'total_zones_detected': self.stats['zones_detected'],
            'avg_zones_per_analysis': round(self.stats['zones_detected'] / max(self.stats['analyses_count'], 1), 2),
            'tolerance_ticks': self.tolerance_ticks
        }

# === FACTORY FUNCTION ===

def create_confluence_analyzer(tolerance_ticks: float = 3.0) -> ConfluenceAnalyzer:
    """Factory function pour confluence analyzer"""
    return ConfluenceAnalyzer(tolerance_ticks)

# === TESTING ===

def test_confluence_analyzer():
    """Test confluence analyzer"""
    logger.debug("Test confluence analyzer...")

    analyzer = create_confluence_analyzer(tolerance_ticks=2.0)

    # Test market data
    market_data = MarketData(
        timestamp=pd.Timestamp.now(),
        symbol="ES",
        open=4500.0,
        high=4510.0,
        low=4495.0,
        close=4505.0,
        volume=1500
    )

    # Mock data pour tests
    gamma_data = {
        'call_wall': 4520.0,
        'put_wall': 4480.0,
        'gamma_flip': 4500.0
    }

    market_profile_data = {
        'poc': 4502.0,
        'vah': 4515.0,
        'val': 4485.0,
        'ppoc': 4498.0
    }

    vwap_data = {
        'vwap': 4503.0,
        'vwap_sd1_up': 4508.0,
        'vwap_sd1_down': 4498.0
    }

    volume_data = {
        'volume_clusters': [4500.0, 4505.0]
    }

    session_data = {
        'session_high': 4515.0,
        'session_low': 4485.0
    }

    # Test analyse
    analysis = analyzer.analyze_confluence(
        market_data=market_data,
        gamma_data=gamma_data,
        market_profile_data=market_profile_data,
        vwap_data=vwap_data,
        volume_data=volume_data,
        session_data=session_data
    )

    logger.info(f"Zones détectées: {len(analysis.zones)}")
    logger.info(f"Confluence au prix: {analysis.confluence_score_at_price:.3f}")
    logger.info(f"Proximity score: {analysis.proximity_score:.3f}")

    if analysis.nearest_support_zone:
        logger.info(f"Support proche: {analysis.nearest_support_zone.center_price:.2f}")

    if analysis.nearest_resistance_zone:
        logger.info(f"Résistance proche: {analysis.nearest_resistance_zone.center_price:.2f}")

    # Test summary
    summary = analyzer.get_confluence_summary(analysis)
    logger.info(f"Summary: {summary['total_zones']} zones, {summary['strong_zones']} fortes")

    # Test statistics
    stats = analyzer.get_statistics()
    logger.info(f"Stats: {stats}")

    # 🆕 TEST ELITE MTF CONFLUENCE
    logger.info("=== Test Elite MTF Confluence ===")
    
    test_market_data = {
        "symbol": "ES",
        "current_price": 4505.0,
        "volume": 125000,
        "volatility": 0.6
    }
    
    mtf_score, mtf_analysis = analyzer.calculate_elite_mtf_confluence(test_market_data)
    
    logger.info(f"🎯 MTF Confluence Score: {mtf_score:.3f}")
    logger.info(f"📊 Base Score: {mtf_analysis['base_score']:.3f}")
    logger.info(f"⚡ Alignment Bonus: {mtf_analysis['alignment_bonus']:.3f}")
    logger.info(f"⭐ Quality Bonus: {mtf_analysis['quality_bonus']:.3f}")
    logger.info(f"⚠️ Divergence Penalty: {mtf_analysis['divergence_penalty']:.3f}")
    
    # Décision signal selon confluence
    if mtf_score > 0.75:
        logger.info("🚀 SIGNAL ELITE: EXECUTION RECOMMANDÉE")
    elif mtf_score > 0.35:
        logger.info("✅ SIGNAL STANDARD: EXECUTION POSSIBLE")
    elif mtf_score < -0.35:
        logger.info("🔴 SIGNAL SHORT: ANALYSE SUPPLÉMENTAIRE")
    else:
        logger.info("⏸️ PAS DE SIGNAL: ATTENDRE CONFLUENCE")

    logger.info("[TARGET] Confluence analyzer test COMPLETED")
    return True


if __name__ == "__main__":
    test_confluence_analyzer()