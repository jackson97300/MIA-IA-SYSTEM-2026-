"""
🚀 ML 3-LAYER FILTER - MENTHORQ FIRST + ORDERFLOW VALIDATOR + CONTEXT FILTER

Architecture:
    LAYER 1 (50%): MenthorQ (Options Data) - SIGNAL PRIMAIRE
        → Identifie les ZONES DE RÉACTION (Support/Resistance gamma)
        → GEX, Gamma Walls, Next Wall, Blind Spots
        → NE DÉCIDE PAS si on trade, juste "où réagir"

    LAYER 2 (30%): OrderFlow - VALIDATEUR DIRECTIONNEL
        → VALIDE que le flow confirme la direction du Layer 1
        → Delta, Volume Profile, DOM Imbalance, Institutional Pressure
        → FILTRE #1: Rejette si flow ne confirme PAS

    LAYER 3 (20%): VWAP/Context - FILTRE CONTEXTUEL
        → CONFIRME que le contexte de marché est favorable
        → VWAP distance, Value Area, Market Structure, Volatility
        → FILTRE #2: Rejette si contexte défavorable

Workflow (Validation Progressive):
    1. Layer 1 génère signal (LONG/SHORT) → "GEX @ 35t = resistance potentielle"
    2. Layer 2 VALIDE direction → "Flow confirme SHORT ?"
    3. Layer 3 CONFIRME contexte → "Contexte favorable ?"
    4. Si les 3 layers passent → TRADE VALIDÉ ✅

Philosophie:
    - Layer 1 = IDENTIFIER les zones de réaction (support/resistance options)
    - Layer 2 = VALIDER la direction avec orderflow (confirmation flux)
    - Layer 3 = CONFIRMER le contexte (timing et conditions favorables)

    ⚠️ UN SIGNAL N'EST JAMAIS TRADÉ SANS VALIDATION LAYER 2 + 3 !

🔥 NOUVEAU 13-NOV-2025: Best Practices Pro
    - VWAP Band Width comme ATR (au lieu d'ATR 1-min)
    - Adaptive Thresholds (seuils dynamiques)

Version: 1.3 - VWAP Band ATR + Adaptive
Date: 2025-11-13
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from zoneinfo import ZoneInfo

# ═══════════════════════════════════════════════════════════════════════
# 🔥 PHASE 1 FIX: Import unified thresholds
# ═══════════════════════════════════════════════════════════════════════
try:
    from config.unified_thresholds import (
        MIN_TOTAL_CONFIDENCE,
        MIN_LAYER_CONFIDENCE,
        LAYER_WEIGHTS,
        MENTHORQ_WEIGHTS,
        ORDERFLOW_WEIGHTS,
        CONTEXT_WEIGHTS,
        DISTANCE_TOLERANCE,
        ORDERFLOW_VALIDATION,
        get_min_confidence,
        get_layer_min_confidence,
        get_distance_score,
        is_orderflow_valid
    )
    UNIFIED_THRESHOLDS_AVAILABLE = True
except ImportError as e:
    UNIFIED_THRESHOLDS_AVAILABLE = False
    # Fallback aux valeurs hardcodées si nécessaire

logger = logging.getLogger(__name__)

if UNIFIED_THRESHOLDS_AVAILABLE:
    logger.info("✅ Unified thresholds importés")
else:
    logger.warning(f"⚠️ Unified thresholds non disponibles")

# ═══════════════════════════════════════════════════════════════════════
# 🔥 PHASE 2: Import optimizations
# ═══════════════════════════════════════════════════════════════════════
try:
    from core.confluence_detector import (
        detect_confluences,
        get_confluence_bonus,
        ConfluenceAnalysis
    )
    CONFLUENCE_DETECTOR_AVAILABLE = True
    logger.info("✅ Confluence detector importé")
except ImportError as e:
    CONFLUENCE_DETECTOR_AVAILABLE = False
    logger.warning(f"⚠️ Confluence detector non disponible: {e}")

try:
    from core.vwap_band_calculator import (
        get_structural_volatility,
        normalize_distance_structural
    )
    VWAP_CALCULATOR_AVAILABLE = True
    logger.info("✅ VWAP band calculator importé")
except ImportError as e:
    VWAP_CALCULATOR_AVAILABLE = False
    logger.warning(f"⚠️ VWAP calculator non disponible: {e}")


# ═══════════════════════════════════════════════════════════════════════
# TYPES & ENUMS
# ═══════════════════════════════════════════════════════════════════════

class TradeSignal(Enum):
    """Signal de trading"""
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = None


@dataclass
class Layer1Result:
    """Résultat Layer 1 (MenthorQ)"""
    signal: Optional[TradeSignal]
    confidence: float  # 0.0-0.50
    reason: str
    triggers: List[str]
    breakdown: Dict[str, float]  # Score par groupe
    # 🔧 AJOUT 2025-11-13: SL/TP optimisés basés sur confluences
    confluence_levels: Optional[List[float]] = None  # Niveaux de confluence détectés
    suggested_sl: Optional[float] = None             # SL suggéré (sous/au-dessus confluence)
    suggested_tp: Optional[float] = None             # TP suggéré (VWAP ou résistance)
    sl_distance_ticks: Optional[float] = None        # Distance SL en ticks


@dataclass
class Layer2Result:
    """Résultat Layer 2 (OrderFlow)"""
    validated: bool
    confidence: float  # 0.0-0.30
    reason: str
    validations: List[str]
    metrics: Dict[str, bool]


@dataclass
class Layer3Result:
    """Résultat Layer 3 (Context)"""
    favorable: bool
    confidence: float  # 0.0-0.20
    reason: str
    warnings: List[str]


@dataclass
class TradeDecision:
    """Décision finale de trading"""
    action: Optional[TradeSignal]
    should_trade: bool
    total_confidence: float  # 0.0-1.0
    layer1_confidence: float
    layer2_confidence: float
    layer3_confidence: float
    breakdown: Dict
    rejection_reason: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

class ML3LayerConfig:
    """Configuration du système 3-Layer"""

    # ═══════════════════════════════════════════════════════════════════════
    # 🔥 PHASE 1 FIX: Utiliser unified_thresholds si disponible
    # ═══════════════════════════════════════════════════════════════════════

    if UNIFIED_THRESHOLDS_AVAILABLE:
        # Import depuis unified_thresholds
        LAYER_WEIGHTS = LAYER_WEIGHTS
        MENTHORQ_WEIGHTS = MENTHORQ_WEIGHTS
        ORDERFLOW_WEIGHTS = ORDERFLOW_WEIGHTS
        CONTEXT_WEIGHTS = CONTEXT_WEIGHTS
        MIN_TOTAL_CONFIDENCE = MIN_TOTAL_CONFIDENCE
        MIN_LAYER_CONFIDENCE = MIN_LAYER_CONFIDENCE

        logger.info("✅ ML3LayerConfig utilise unified_thresholds")
    else:
        # Fallback valeurs par défaut (NE DEVRAIT JAMAIS ARRIVER)
        logger.warning("⚠️ ML3LayerConfig utilise valeurs fallback")

        # === POIDS PAR LAYER ===
        LAYER_WEIGHTS = {
            "menthorq": 0.50,    # 50% - Signal primaire
            "orderflow": 0.30,   # 30% - Validateur
            "context": 0.20      # 20% - Filtre contextuel
        }

        # === POIDS DÉTAILLÉS LAYER 1 (MenthorQ) ===
        MENTHORQ_WEIGHTS = {
            "gamma_walls": 0.10,      # 10%
            "gex_levels": 0.10,       # 10%
            "blind_spots": 0.08,      # 8% ⚠️ Ancien
            "next_wall": 0.08,        # 8% ⚠️ Ancien
            "distances": 0.08,        # 8%
            "scores": 0.06            # 6% ⚠️ Ancien
        }

        # === POIDS DÉTAILLÉS LAYER 2 (OrderFlow) ===
        ORDERFLOW_WEIGHTS = {
            "delta": 0.12,            # 12%
            "volume": 0.06,           # 6%
            "dom": 0.06,              # 6%
            "pressure": 0.04,         # 4%
            "battle_navale": 0.02     # 2%
        }

        # === POIDS DÉTAILLÉS LAYER 3 (Context) ===
        CONTEXT_WEIGHTS = {
            "vwap": 0.08,             # 8%
            "value_area": 0.06,       # 6%
            "structure": 0.04,        # 4%
            "volatility": 0.02        # 2%
        }

        # === SEUILS MINIMAUX (Fallback - COHÉRENT avec unified_thresholds.py 05/12) ===
        MIN_TOTAL_CONFIDENCE = {
            'ES': 0.30,    # 🔄 05/12: Cohérent avec unified_thresholds.py
            'NQ': 0.30,    # 🔄 05/12: Cohérent avec unified_thresholds.py
            'RTY': 0.42
        }

        # ⚠️ V10.2 16/12/2025: L2 = 0.15 PARTOUT (OrderFlow plus impactant)
        MIN_LAYER_CONFIDENCE = {
            'ES': {'layer1': 0.20, 'layer2': 0.17, 'layer3': 0.12},  # 🔥 V10.3
            'NQ': {'layer1': 0.20, 'layer2': 0.17, 'layer3': 0.12},  # 🔥 V10.3
            'RTY': {'layer1': 0.20, 'layer2': 0.17, 'layer3': 0.12}  # 🔥 V10.3
        }

    # === SEUILS MINIMAUX (COHÉRENTS avec unified_thresholds.py - 05/12/2025) ===
    # 🔄 Ces seuils DOIVENT être alignés avec config/unified_thresholds.py
    MIN_MENTHORQ_CONFIDENCE = 0.05   # Min Layer 1 (fallback)
    MIN_ORDERFLOW_CONFIDENCE = 0.01  # Min Layer 2 (fallback)
    MIN_CONTEXT_CONFIDENCE = 0.05    # Min Layer 3 (fallback)
    # ⚠️ MIN_TOTAL_CONFIDENCE est déjà défini comme dict plus haut (lignes 223-227)
    # Ne PAS redéfinir ici comme float!

    # === SEUILS MENTHORQ (OPTION B - ÉQUILIBRÉ) ===
    # 🔧 AJUSTEMENT ES: Seuils élargis pour captures plus fréquentes
    # ES bouge moins en ticks que NQ/RTY → Besoin seuils plus larges
    # 🔧 OPTIMISÉ: Augmenté pour capturer plus de setups (analyse losing trades)
    # 🔧 MODIFICATION 2025-11-13: Assouplissement Layer 1 pour permettre plus de trades
    # ✅ CORRIGÉ 27/11/2025: Distances STRICTES pour tous les niveaux
    # L'edge vient de la PROXIMITÉ, pas de trader à 450 ticks!
    # ✅ COMPROMIS QUALITÉ: Pas trop serré, pas trop large
    # ES: 40 ticks = 10 pts | NQ: 120 ticks = 30 pts | RTY: 40 ticks = 4 pts
    # ✅ 10/12/2025: CONFIG PRO SCALPING - Entry AU niveau!
    # Pratique PRO: Scalping 2-5t = On trade QUASI au niveau
    GAMMA_WALL_MAX_DISTANCE_TICKS = {
        'ES': 8,     # 🎯 10/12: OPTIMAL (WR 64.7% avec TP15/SL15)
        'NQ': 10,    # 🎯 10/12: Réduit de 15 à 10
        'RTY': 12    # RTY: Valeur originale
    }
    GEX_LEVEL_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔴 09/12: CONFIG SERRÉE
        'NQ': 15,    # 🔴 09/12: CONFIG SERRÉE
        'RTY': 12    # 🔴 09/12: CONFIG SERRÉE
    }
    GEX_PROXIMITY_THRESHOLDS = {
        5:  0.10,   # < 5 ticks: full weight (très proche) 🔴 SERRÉ
        10: 0.07,   # < 10 ticks: 70% weight (proche)
        25: 0.04,   # < 25 ticks: 40% weight (acceptable)
        50: 0.02    # < 50 ticks: 20% weight (limite)
    }
    BLIND_SPOT_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔴 09/12: CONFIG SERRÉE
        'NQ': 15,    # 🔴 09/12: CONFIG SERRÉE
        'RTY': 12    # 🔴 09/12: CONFIG SERRÉE
    }
    NEXT_WALL_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔴 09/12: CONFIG SERRÉE
        'NQ': 15,    # 🔴 09/12: CONFIG SERRÉE
        'RTY': 12    # 🔴 09/12: CONFIG SERRÉE
    }
    NEXT_WALL_MIN_STRENGTH = 0.12  # 🔧 Assoupli: 0.15 → 0.12 (-20%)

    # ═══════════════════════════════════════════════════════════════════════
    # 🆕 12/12/2025: NOUVEAUX NIVEAUX VWAP & VOLUME PROFILE
    # Ces niveaux sont proches du prix 30-50% du temps → Plus d'opportunités!
    #
    # 🔧 POIDS NORMALISÉS pour garder Layer 1 = ~50% max
    # Anciens (gamma, gex, blind, wall, daily, scores) = ~46%
    # Nouveaux (vwap, poc, vah) = ~12%
    # TOTAL ≈ 58% (marge de sécurité pour confluence)
    # ═══════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════
    # 🔧 12/12/2025: DISTANCES ALIGNÉES SUR MENTHORQ (STRICT)
    # ES: 10 ticks | NQ: 15 ticks | RTY: 12 ticks
    # ═══════════════════════════════════════════════════════════════════════

    # VWAP DAILY (Priorité #1)
    VWAP_ENTRY_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔧 Aligné: 15 → 10 (strict comme MenthorQ)
        'NQ': 15,    # 🔧 Aligné: 25 → 15 (strict comme MenthorQ)
        'RTY': 12    # 🔧 Aligné: 20 → 12 (strict comme MenthorQ)
    }
    VWAP_ENTRY_WEIGHT = 0.05  # 5% du score Layer 1

    # VWAP BANDS ±1σ (Priorité #2)
    VWAP_BAND_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔧 Aligné: 15 → 10
        'NQ': 15,    # 🔧 Aligné: 25 → 15
        'RTY': 12    # 🔧 Aligné: 20 → 12
    }
    VWAP_BAND_WEIGHT = 0.03  # 3% du score Layer 1

    # VWAP WEEKLY (Priorité #3)
    VWAP_WEEKLY_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔧 Aligné: 20 → 10
        'NQ': 15,    # 🔧 Aligné: 30 → 15
        'RTY': 12    # 🔧 Aligné: 25 → 12
    }
    VWAP_WEEKLY_WEIGHT = 0.03  # 3% du score Layer 1

    # POC - Point of Control (Priorité #4)
    POC_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔧 Aligné: 20 → 10
        'NQ': 15,    # 🔧 Aligné: 30 → 15
        'RTY': 12    # 🔧 Aligné: 20 → 12
    }
    POC_WEIGHT = 0.03  # 3% du score Layer 1

    # PRIOR VWAP (Priorité #5)
    PVWAP_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔧 Aligné: 15 → 10
        'NQ': 15,    # 🔧 Aligné: 25 → 15
        'RTY': 12    # 🔧 Aligné: 20 → 12
    }
    PVWAP_WEIGHT = 0.02  # 2% du score Layer 1

    # VAH SEULEMENT (Priorité #6 - ES/RTY seulement)
    # ⚠️ VAL DÉSACTIVÉ: Score 0% (jamais proche du prix)
    VAH_MAX_DISTANCE_TICKS = {
        'ES': 10,    # 🔧 Aligné: 15 → 10
        'NQ': None,  # Désactivé pour NQ (score trop bas)
        'RTY': 12    # 🔧 Aligné: 15 → 12
    }
    VAH_WEIGHT = 0.02  # 2% du score Layer 1 (VAH seulement, VAL désactivé)

    # === SEUILS ORDERFLOW ===
    # 🔧 MODIFICATION 2025-11-13: Assouplissement pour permettre plus de trades
    #    Analyse rejets: Layer 2 rejette 70% des signaux (trop strict)
    DELTA_MIN_CUMULATIVE = 300        # 500 → 300 (réduit de 40%)
    VOLUME_MIN_PERCENTAGE = 0.52      # 0.55 → 0.52 (55% → 52%)
    DOM_MIN_IMBALANCE = 0.10          # 0.15 → 0.10 (15% → 10%)
    INSTITUTIONAL_MIN_PRESSURE = 0.15  # 0.20 → 0.15 (20% → 15%)

    # === SEUILS CONTEXT ===
    VWAP_MAX_DISTANCE_ATR = 2.0       # Max 2 ATR de distance VWAP
    RANGE_POSITION_LOW_THRESHOLD = 40.0   # Bas 40% du range (en %)
    RANGE_POSITION_HIGH_THRESHOLD = 60.0  # Haut 40% du range (en %)
    STRUCTURE_PROXIMITY_TICKS = 20    # 20 ticks de ONH/ONL

    # === TICK SIZES ===
    TICK_SIZE = {
        'ES': 0.25,
        'NQ': 0.25,
        'RTY': 0.10
    }


# ═══════════════════════════════════════════════════════════════════════
# ML 3-LAYER FILTER
# ═══════════════════════════════════════════════════════════════════════

class ML3LayerFilter:
    """
    Filtre ML 3-Layer: MenthorQ → OrderFlow → Context

    Usage:
        filter = ML3LayerFilter()
        decision = filter.evaluate_trade(snapshot)

        if decision.should_trade:
            execute_trade(decision.action, decision.total_confidence)
    """

    def __init__(self, config: Optional[ML3LayerConfig] = None):
        """
        Initialise le filtre 3-Layer

        Args:
            config: Configuration personnalisée (optionnel)
        """
        self.config = config or ML3LayerConfig()

        # 🔥 FIX 08/12/2025: Initialiser self.stats pour éviter AttributeError
        self.stats = {
            '0dte_hvl_used': 0,
            '0dte_gamma_wall_used': 0,
            '0dte_total_usage': 0
        }

        # 🔥 NOUVEAU 13-NOV-2025: Best Practices Pro Modules
        try:
            from core.fast_filters_first import FastFiltersFirst
            from core.adaptive_thresholds import AdaptiveThresholds

            self.fast_filters = FastFiltersFirst({})
            self.adaptive_thresholds = AdaptiveThresholds()

            logger.info("=" * 80)
            logger.info("🚀 ML 3-LAYER FILTER INITIALISÉ + BEST PRACTICES PRO")
            logger.info("=" * 80)
            logger.info(f"   Layer 1 (MenthorQ):  {self.config.LAYER_WEIGHTS['menthorq']:.0%}")
            logger.info(f"   Layer 2 (OrderFlow): {self.config.LAYER_WEIGHTS['orderflow']:.0%}")
            logger.info(f"   Layer 3 (Context):   {self.config.LAYER_WEIGHTS['context']:.0%}")
            logger.info("   ⚡ Fast Filters First: ACTIF (gain latence ~60%)")
            logger.info("   🔧 Adaptive Thresholds: ACTIF (seuils dynamiques)")
            logger.info("=" * 80)
        except Exception as e:
            logger.warning(f"⚠️ Best Practices modules non disponibles: {e}")
            self.fast_filters = None
            self.adaptive_thresholds = None

            logger.info("=" * 80)
            logger.info("🚀 ML 3-LAYER FILTER INITIALISÉ")
            logger.info("=" * 80)
            logger.info(f"   Layer 1 (MenthorQ):  {self.config.LAYER_WEIGHTS['menthorq']:.0%}")
            logger.info(f"   Layer 2 (OrderFlow): {self.config.LAYER_WEIGHTS['orderflow']:.0%}")
            logger.info(f"   Layer 3 (Context):   {self.config.LAYER_WEIGHTS['context']:.0%}")
            logger.info("=" * 80)

        # ═══════════════════════════════════════════════════════════════════════
        # 🔥 PHASE 2: Modules optimisations
        # ═══════════════════════════════════════════════════════════════════════
        self.confluence_enabled = CONFLUENCE_DETECTOR_AVAILABLE
        self.vwap_calculator_enabled = VWAP_CALCULATOR_AVAILABLE

        if self.confluence_enabled:
            logger.info("✅ Détection confluence activée")
        else:
            logger.warning("⚠️ Détection confluence désactivée (module non disponible)")

        if self.vwap_calculator_enabled:
            logger.info("✅ VWAP band calculator activé")
        else:
            logger.warning("⚠️ VWAP calculator désactivé (fallback ATR)")

    # ═══════════════════════════════════════════════════════════════════
    # 🆕 PHASE 1 TODO_001: EXTRACTION COMPLÈTE DES NIVEAUX (85 NIVEAUX)
    # ═══════════════════════════════════════════════════════════════════

    def _extract_all_menthorq_levels(self, snapshot: Dict, current_price: float, symbol: str) -> List[Dict]:
        """
        🆕 TODO_001: Extrait TOUS les niveaux MenthorQ (85 niveaux)

        Catégories:
        - GEX (10)
        - Blind Spots (9)
        - Options Strikes (dynamique, tous les 25 pts)
        - Round Numbers (dynamique, tous les 10 pts)
        - VWAP Daily (7)
        - VWAP Weekly (3)
        - PVWAP (5)
        - AWAP (2)
        - Session Structure (6)
        - Volume Profile (3)
        - Options Walls (2)
        - HVL (1)
        - Next Wall (1)
        - VWAP Monthly (1)

        Returns:
            List[Dict]: Liste de dictionnaires avec structure:
                {
                    'id': str,
                    'price': float,
                    'distance_ticks': float,
                    'type': str,
                    'priority': float (0-1),
                    'category': str
                }
        """

        all_levels = []
        # ✅ FIX 23/11/2025: Tick size correct par symbole
        tick_sizes = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}
        tick_size = tick_sizes.get(symbol, 0.25)

        # ═══════════════════════════════════════════════════════════════
        # 1. GEX LEVELS (10 niveaux)
        # ═══════════════════════════════════════════════════════════════
        for i in range(1, 11):
            gex_price = snapshot.get(f'gex_{i}', None)
            if gex_price:
                all_levels.append({
                    'id': f'gex_{i}',
                    'price': gex_price,
                    'distance_ticks': (gex_price - current_price) / tick_size,
                    'type': 'GEX',
                    'priority': 0.95,
                    'category': 'INSTITUTIONAL'
                })

        # ═══════════════════════════════════════════════════════════════
        # 2. BLIND SPOTS (9 niveaux)
        # ═══════════════════════════════════════════════════════════════
        for i in range(9):
            bs_price = snapshot.get(f'blind_spot_{i}', None)
            if bs_price:
                all_levels.append({
                    'id': f'blind_spot_{i}',
                    'price': bs_price,
                    'distance_ticks': (bs_price - current_price) / tick_size,
                    'type': 'BLIND_SPOT',
                    'priority': 0.95,
                    'category': 'INSTITUTIONAL'
                })

        # ═══════════════════════════════════════════════════════════════
        # 3. OPTIONS STRIKES (Every 25 points)
        # ═══════════════════════════════════════════════════════════════
        put_support = snapshot.get('put_support', 6500)
        call_resistance = snapshot.get('call_resistance', 7000)

        # Générer strikes tous les 25 points dans ±500 pts du prix actuel
        strike_price = int((current_price - 500) / 25) * 25
        while strike_price <= current_price + 500:
            if put_support <= strike_price <= call_resistance:
                all_levels.append({
                    'id': f'strike_{int(strike_price)}',
                    'price': strike_price,
                    'distance_ticks': (strike_price - current_price) / tick_size,
                    'type': 'OPTIONS_STRIKE',
                    'priority': 0.85,
                    'category': 'OPTIONS'
                })
            strike_price += 25

        # ═══════════════════════════════════════════════════════════════
        # 4. ROUND NUMBERS (Psychological levels, every 10 points)
        # ═══════════════════════════════════════════════════════════════
        round_base = int(current_price / 10) * 10
        for offset in range(-100, 110, 10):
            round_price = round_base + offset
            if abs(round_price - current_price) <= 100:  # Dans ±100 pts
                all_levels.append({
                    'id': f'round_{int(round_price)}',
                    'price': round_price,
                    'distance_ticks': (round_price - current_price) / tick_size,
                    'type': 'ROUND_NUMBER',
                    'priority': 0.70,
                    'category': 'PSYCHOLOGICAL'
                })

        # ═══════════════════════════════════════════════════════════════
        # 6. VWAP DAILY (7 niveaux)
        # ═══════════════════════════════════════════════════════════════
        vwap_levels = {
            'vwap': snapshot.get('vwap'),
            'vwap_up1': snapshot.get('vwap_up1'),
            'vwap_dn1': snapshot.get('vwap_dn1'),
            'vwap_up2': snapshot.get('vwap_up2'),
            'vwap_dn2': snapshot.get('vwap_dn2'),
            'vwap_up3': snapshot.get('vwap_up3'),
            'vwap_dn3': snapshot.get('vwap_dn3')
        }

        for vwap_id, vwap_price in vwap_levels.items():
            if vwap_price:
                all_levels.append({
                    'id': vwap_id,
                    'price': vwap_price,
                    'distance_ticks': (vwap_price - current_price) / tick_size,
                    'type': 'VWAP_DAILY',
                    'priority': 0.80,
                    'category': 'VWAP'
                })

        # ═══════════════════════════════════════════════════════════════
        # 7. VWAP WEEKLY (3 niveaux)
        # ═══════════════════════════════════════════════════════════════
        vwap_weekly_levels = {
            'vwap_weekly': snapshot.get('vwap_weekly'),
            'vwap_weekly_up1': snapshot.get('vwap_weekly_up1'),
            'vwap_weekly_dn1': snapshot.get('vwap_weekly_dn1')
        }

        for vw_id, vw_price in vwap_weekly_levels.items():
            if vw_price:
                all_levels.append({
                    'id': vw_id,
                    'price': vw_price,
                    'distance_ticks': (vw_price - current_price) / tick_size,
                    'type': 'VWAP_WEEKLY',
                    'priority': 0.70,
                    'category': 'VWAP'
                })

        # ═══════════════════════════════════════════════════════════════
        # 8. PVWAP (5 niveaux)
        # ═══════════════════════════════════════════════════════════════
        pvwap_levels = {
            'pvwap': snapshot.get('pvwap'),
            'pvwap_up1': snapshot.get('pvwap_up1'),
            'pvwap_dn1': snapshot.get('pvwap_dn1'),
            'pvwap_up2': snapshot.get('pvwap_up2'),
            'pvwap_dn2': snapshot.get('pvwap_dn2')
        }

        for pv_id, pv_price in pvwap_levels.items():
            if pv_price:
                all_levels.append({
                    'id': pv_id,
                    'price': pv_price,
                    'distance_ticks': (pv_price - current_price) / tick_size,
                    'type': 'PVWAP',
                    'priority': 0.70,
                    'category': 'VWAP'
                })

        # ═══════════════════════════════════════════════════════════════
        # 9. AWAP (Anchored VWAP Opening)
        # ═══════════════════════════════════════════════════════════════
        structure = snapshot.get('structure', {})
        awap_levels = {
            'awap_onh': structure.get('awap_onh'),
            'awap_onl': structure.get('awap_onl'),
            'awap_ibo': structure.get('awap_ibo')
        }

        for awap_id, awap_price in awap_levels.items():
            if awap_price:
                all_levels.append({
                    'id': awap_id,
                    'price': awap_price,
                    'distance_ticks': (awap_price - current_price) / tick_size,
                    'type': 'AWAP',
                    'priority': 0.75,
                    'category': 'VWAP'
                })

        # ═══════════════════════════════════════════════════════════════
        # 10. SESSION STRUCTURE (6 niveaux)
        # ═══════════════════════════════════════════════════════════════
        session_levels = {
            'onh': structure.get('onh'),
            'onl': structure.get('onl'),
            'ibh': structure.get('ibh'),
            'ibl': structure.get('ibl'),
            '1d_max': snapshot.get('1d_max'),
            '1d_min': snapshot.get('1d_min')
        }

        for sess_id, sess_price in session_levels.items():
            if sess_price:
                all_levels.append({
                    'id': sess_id,
                    'price': sess_price,
                    'distance_ticks': (sess_price - current_price) / tick_size,
                    'type': 'SESSION_STRUCTURE',
                    'priority': 0.75,
                    'category': 'SESSION'
                })

        # ═══════════════════════════════════════════════════════════════
        # 11. VOLUME PROFILE (3 niveaux)
        # ═══════════════════════════════════════════════════════════════
        vva = snapshot.get('vva', {})
        volume_levels = {
            'vpoc': vva.get('vpoc'),
            'vah': vva.get('vah'),
            'val': vva.get('val')
        }

        for vol_id, vol_price in volume_levels.items():
            if vol_price:
                all_levels.append({
                    'id': vol_id,
                    'price': vol_price,
                    'distance_ticks': (vol_price - current_price) / tick_size,
                    'type': 'VOLUME_PROFILE',
                    'priority': 0.80,
                    'category': 'VOLUME'
                })

        # ═══════════════════════════════════════════════════════════════
        # 12. OPTIONS WALLS (2 niveaux)
        # ═══════════════════════════════════════════════════════════════
        all_levels.append({
            'id': 'call_resistance',
            'price': call_resistance,
            'distance_ticks': (call_resistance - current_price) / tick_size,
            'type': 'CALL_WALL',
            'priority': 0.90,
            'category': 'INSTITUTIONAL'
        })

        all_levels.append({
            'id': 'put_support',
            'price': put_support,
            'distance_ticks': (put_support - current_price) / tick_size,
            'type': 'PUT_WALL',
            'priority': 0.90,
            'category': 'INSTITUTIONAL'
        })

        # ═══════════════════════════════════════════════════════════════
        # 13. HVL (1 niveau)
        # ═══════════════════════════════════════════════════════════════
        hvl_price = snapshot.get('hvl')
        if hvl_price:
            all_levels.append({
                'id': 'hvl',
                'price': hvl_price,
                'distance_ticks': (hvl_price - current_price) / tick_size,
                'type': 'HVL',
                'priority': 0.60,
                'category': 'VOLATILITY'
            })

        # ═══════════════════════════════════════════════════════════════
        # 13bis. NIVEAUX 0DTE (4 niveaux) - AJOUT 05/12/2025
        # ═══════════════════════════════════════════════════════════════
        # Ces niveaux sont CRITIQUES pour le trading intraday (0DTE options)
        # Priorité MAXIMALE car très réactifs et aimants intraday

        # Call Resistance 0DTE
        cr_0dte = snapshot.get('call_resistance_0dte', 0)
        if cr_0dte:
            all_levels.append({
                'id': 'call_resistance_0dte',
                'price': cr_0dte,
                'distance_ticks': (cr_0dte - current_price) / tick_size,
                'type': 'CALL_WALL_0DTE',
                'priority': 0.98,  # Très haute priorité (intraday)
                'category': 'INSTITUTIONAL_0DTE'
            })

        # Put Support 0DTE
        ps_0dte = snapshot.get('put_support_0dte', 0)
        if ps_0dte:
            all_levels.append({
                'id': 'put_support_0dte',
                'price': ps_0dte,
                'distance_ticks': (ps_0dte - current_price) / tick_size,
                'type': 'PUT_WALL_0DTE',
                'priority': 0.98,  # Très haute priorité (intraday)
                'category': 'INSTITUTIONAL_0DTE'
            })

        # HVL 0DTE (pivot intraday)
        hvl_0dte = snapshot.get('hvl_0dte', 0)
        if hvl_0dte:
            all_levels.append({
                'id': 'hvl_0dte',
                'price': hvl_0dte,
                'distance_ticks': (hvl_0dte - current_price) / tick_size,
                'type': 'HVL_0DTE',
                'priority': 0.85,  # Pivot volatilité intraday
                'category': 'VOLATILITY_0DTE'
            })

        # Gamma Wall 0DTE (mur gamma intraday)
        gw_0dte = snapshot.get('gamma_wall_0dte', 0)
        if gw_0dte:
            all_levels.append({
                'id': 'gamma_wall_0dte',
                'price': gw_0dte,
                'distance_ticks': (gw_0dte - current_price) / tick_size,
                'type': 'GAMMA_WALL_0DTE',
                'priority': 0.95,  # Mur gamma très important
                'category': 'INSTITUTIONAL_0DTE'
            })

        # ═══════════════════════════════════════════════════════════════
        # 13ter. INITIAL BALANCE (IBH/IBL) - AJOUT 05/12/2025
        # ═══════════════════════════════════════════════════════════════
        # UNIQUEMENT SESSION US (après 16:30 Paris = 10:30 ET)
        # L'IB est défini pendant la 1ère heure US (09:30-10:30 ET)
        # Note: datetime et ZoneInfo importés globalement en haut du fichier
        paris_tz = ZoneInfo('Europe/Paris')
        hour_paris = datetime.now(paris_tz).hour
        is_us_session = 16 <= hour_paris < 22

        if is_us_session:
            structure = snapshot.get('structure', {})

            # IBH - Initial Balance High (niveaux critiques pour breakout/retest)
            ibh = structure.get('ibh')
            if ibh:
                all_levels.append({
                    'id': 'ibh',
                    'price': ibh,
                    'distance_ticks': (ibh - current_price) / tick_size,
                    'type': 'IBH',
                    'priority': 0.90,  # Priorité élevée - niveau institutionnel
                    'category': 'STRUCTURE'
                })

            # IBL - Initial Balance Low
            ibl = structure.get('ibl')
            if ibl:
                all_levels.append({
                    'id': 'ibl',
                    'price': ibl,
                    'distance_ticks': (ibl - current_price) / tick_size,
                    'type': 'IBL',
                    'priority': 0.90,  # Priorité élevée - niveau institutionnel
                    'category': 'STRUCTURE'
                })

        # ═══════════════════════════════════════════════════════════════
        # 14. VWAP MONTHLY (1 niveau)
        # ═══════════════════════════════════════════════════════════════
        vwap_monthly = snapshot.get('vwap_monthly')
        if vwap_monthly:
            all_levels.append({
                'id': 'vwap_monthly',
                'price': vwap_monthly,
                'distance_ticks': (vwap_monthly - current_price) / tick_size,
                'type': 'VWAP_MONTHLY',
                'priority': 0.65,
                'category': 'VWAP'
            })

        # ═══════════════════════════════════════════════════════════════
        # 15. NEXT WALL (1 niveau - dynamique, PRIORITÉ MAXIMALE)
        # ═══════════════════════════════════════════════════════════════
        next_wall = snapshot.get('next_wall', {})
        if next_wall.get('price'):
            all_levels.append({
                'id': 'next_wall',
                'price': next_wall['price'],
                'distance_ticks': next_wall.get('dist_ticks', 999),
                'type': 'NEXT_WALL',
                'priority': 1.0,  # PRIORITÉ MAXIMALE
                'category': 'INSTITUTIONAL',
                'strength': next_wall.get('strength', 0),
                'side': next_wall.get('side', 'unknown')
            })

        # ═══════════════════════════════════════════════════════════════
        # 16. GAMMA WALL (1 niveau - Max Gamma Strike, si proche)
        #     🔴 PHASE 1 BONUS: +2% Bible MenthorQ
        # ═══════════════════════════════════════════════════════════════
        gamma_wall = snapshot.get('gamma_wall_level', None)
        call_resistance = snapshot.get('call_resistance', None)
        put_support = snapshot.get('put_support', None)

        if gamma_wall and gamma_wall > 0:
            distance_ticks = abs((gamma_wall - current_price) / tick_size)

            # FILTRE 1: Distance max 200 ticks (zone tradable)
            if distance_ticks <= 200:
                # FILTRE 2: Éviter duplication avec call/put walls
                is_duplicate = (gamma_wall == call_resistance) or (gamma_wall == put_support)

                if not is_duplicate:
                    all_levels.append({
                        'id': 'gamma_wall',
                        'price': gamma_wall,
                        'distance_ticks': (gamma_wall - current_price) / tick_size,
                        'type': 'GAMMA_WALL',
                        'priority': 0.95,  # Très haute priorité
                        'category': 'INSTITUTIONAL'
                    })
                    logger.debug(f"✅ Gamma Wall extrait @ {gamma_wall:.2f} ({distance_ticks:.0f}t)")
                else:
                    logger.debug(f"⚠️ Gamma Wall @ {gamma_wall:.2f} déjà extrait (duplication call/put)")
            else:
                logger.debug(f"⚠️ Gamma Wall @ {gamma_wall:.2f} trop loin ({distance_ticks:.0f}t > 200t)")

        logger.debug(f"✅ {len(all_levels)} niveaux MenthorQ extraits")  # ✅ Optimisé: INFO → DEBUG

        return all_levels

    def _find_closest_level(self, all_levels: List[Dict], current_price: float, signal: TradeSignal, symbol: str) -> Optional[Dict]:
        """
        🆕 TODO_002: Trouve le niveau MenthorQ le plus pertinent

        Critères:
        1. Distance (plus proche = mieux)
        2. Direction alignée (support pour LONG, résistance pour SHORT)
        3. Priorité du type de niveau
        4. Dans limite acceptable (max 50 ticks)

        Returns:
            Dict: Niveau optimal avec score calculé, ou None si aucun trouvé
        """

        MAX_DISTANCE_TICKS = 50

        # Filtrer niveaux trop loin
        valid_levels = [
            level for level in all_levels
            if abs(level['distance_ticks']) <= MAX_DISTANCE_TICKS
        ]

        if not valid_levels:
            logger.warning(f"🆕 TODO_002: Aucun niveau dans {MAX_DISTANCE_TICKS}t")
            return None

        # Scorer chaque niveau
        for level in valid_levels:
            score = 0.0
            distance = abs(level['distance_ticks'])

            # Score distance (40% du total)
            if distance <= 10:
                distance_score = 1.0
            elif distance <= 20:
                distance_score = 0.8
            elif distance <= 35:
                distance_score = 0.6
            else:
                distance_score = 0.4

            score += distance_score * 0.40

            # Score priorité type (30% du total)
            score += level['priority'] * 0.30

            # Score direction alignée (30% du total)
            if signal == TradeSignal.LONG and level['distance_ticks'] < 0:
                # Support en-dessous pour LONG
                score += 0.30
            elif signal == TradeSignal.SHORT and level['distance_ticks'] > 0:
                # Résistance au-dessus pour SHORT
                score += 0.30
            else:
                score += 0.10  # Pénalité si pas aligné

            level['score'] = score

        # Retourner niveau avec meilleur score
        best_level = max(valid_levels, key=lambda x: x['score'])

        logger.debug(f"✅ Niveau optimal: {best_level['type']} @ {best_level['price']:.2f} ({best_level['distance_ticks']:.0f}t, score={best_level['score']:.2f})")  # ✅ Optimisé

        return best_level

    def _detect_confluence(self, all_levels: List[Dict], primary_level: Dict, threshold_ticks: int = 10) -> List[Dict]:
        """
        🆕 TODO_003: Détecte les niveaux en confluence avec le niveau principal

        Confluence = 2+ niveaux dans threshold_ticks l'un de l'autre

        Args:
            all_levels: Liste complète des niveaux
            primary_level: Niveau principal
            threshold_ticks: Distance max pour confluence (défaut: 10 ticks)

        Returns:
            List[Dict]: Liste des niveaux en confluence (sans le niveau principal)
        """

        confluence_levels = []
        primary_price = primary_level['price']
        tick_size = 0.25  # ES/NQ

        for level in all_levels:
            if level['id'] == primary_level['id']:
                continue  # Skip le niveau principal lui-même

            distance_pts = abs(level['price'] - primary_price)
            distance_ticks = distance_pts / tick_size

            if distance_ticks <= threshold_ticks:
                confluence_levels.append(level)

        if len(confluence_levels) > 0:
            logger.debug(f"✅ {len(confluence_levels)} niveau(x) en confluence:")  # ✅ Optimisé
            for conf_level in confluence_levels:
                distance_to_primary = abs(conf_level['price'] - primary_price) / tick_size
                logger.info(f"   → {conf_level['type']} @ {conf_level['price']:.2f} ({distance_to_primary:.0f}t)")

        return confluence_levels

    def _score_menthorq_level(self, level: Dict, snapshot: Dict, signal: TradeSignal, confluence_levels: List[Dict]) -> Tuple[float, List[str]]:
        """
        🆕 TODO_004: Score le niveau MenthorQ sélectionné avec bonus

        Scoring:
        - Base score: priorité du type (0-1)
        - Proximity bonus: +0.20 si <15t, +0.10 si <30t
        - Confluence bonus: +0.05 par niveau (max +0.20)
        - Next Wall bonus: +0.15 si c'est Next Wall
        - Institutional bonus: +0.10 si catégorie INSTITUTIONAL

        Returns:
            (score, validations): Score final (0-1) et liste de validations
        """

        validations = []
        score = 0.0

        # Base score du niveau
        base_score = level['priority'] * 0.50
        score += base_score

        validations.append(f"📍 Niveau: {level['type']} @ {level['price']:.2f}")
        validations.append(f"   Distance: {level['distance_ticks']:.0f}t")
        validations.append(f"   Priorité: {level['priority']:.2%}")
        validations.append(f"   Base Score: {base_score:.2%}")

        # Proximity Bonus (distance)
        distance = abs(level['distance_ticks'])
        if distance <= 15:
            proximity_bonus = 0.20
            score += proximity_bonus
            validations.append(f"   ✅ Proximity Bonus: +{proximity_bonus:.2%} (distance {distance:.0f}t < 15t)")
        elif distance <= 30:
            proximity_bonus = 0.10
            score += proximity_bonus
            validations.append(f"   ⚠️ Proximity Bonus: +{proximity_bonus:.2%} (distance {distance:.0f}t < 30t)")

        # Confluence Bonus
        if len(confluence_levels) > 0:
            confluence_bonus = min(len(confluence_levels) * 0.05, 0.20)  # Max +20%
            score += confluence_bonus
            validations.append(f"   ✅ Confluence Bonus: +{confluence_bonus:.2%} ({len(confluence_levels)} niveau(x))")

        # Next Wall Bonus (priorité maximale)
        if level['type'] == 'NEXT_WALL':
            next_wall_bonus = 0.15
            score += next_wall_bonus
            strength = level.get('strength', 0)
            validations.append(f"   ✅ Next Wall Bonus: +{next_wall_bonus:.2%} (strength {strength:.2%})")

        # Institutional Bonus
        if level['category'] == 'INSTITUTIONAL':
            institutional_bonus = 0.10
            score += institutional_bonus
            validations.append(f"   ✅ Institutional Level: +{institutional_bonus:.2%}")

        # ═══════════════════════════════════════════════════════════════════
        # 🔴 PHASE 1: ADJUSTMENTS ADAPTATIFS BIBLE MENTHORQ
        # ═══════════════════════════════════════════════════════════════════

        # Stocker priorité avant adjustments pour comparaison
        priority_before = level['priority']

        # 1. VIX Regime adjustment (+10% Bible)
        level['priority'] = self._adjust_priority_by_vix(level, snapshot)

        # 2. Dealers Bias adjustment (+15% Bible)
        level['priority'] = self._adjust_priority_by_dealers_bias(level, snapshot, signal)

        # 3. Gamma Side adjustment (Bonus +5% Bible)
        level['priority'] = self._adjust_priority_by_gamma_side(level, snapshot)

        # Calculer impact total des adjustments
        priority_after = level['priority']
        adjustment_delta = priority_after - priority_before

        if abs(adjustment_delta) > 0.001:  # Seuil significatif
            adjustment_pct = (adjustment_delta / priority_before) * 100 if priority_before > 0 else 0
            validations.append(f"   🔄 Adjustments Adaptatifs: {adjustment_pct:+.1f}% (priority: {priority_before:.3f} → {priority_after:.3f})")

            # Recalculer base_score avec priorité ajustée
            adjusted_base_score = priority_after * 0.50
            score_adjustment = adjusted_base_score - base_score
            score += score_adjustment

            if score_adjustment > 0:
                validations.append(f"   ✅ Score Boost: +{score_adjustment:.2%}")
            elif score_adjustment < 0:
                validations.append(f"   ⚠️ Score Penalty: {score_adjustment:.2%}")

        # Normaliser score max 1.0
        score = min(score, 1.0)

        validations.append(f"   📊 Score Total Final: {score:.2%}")

        logger.debug(f"✅ Score final = {score:.2%}")  # ✅ Optimisé

        return score, validations

    # ═══════════════════════════════════════════════════════════════════
    # BIBLE MENTHORQ: ADJUSTMENTS ADAPTATIFS (Phase 1)
    # ═══════════════════════════════════════════════════════════════════

    def _adjust_priority_by_vix(self, level: Dict, snapshot: Dict) -> float:
        """
        🔴 P1: Ajuster priorité niveau selon régime VIX (+10% Bible MenthorQ)

        VIX < 15  → COMPRESSION  → Boost breakout levels
        VIX 15-25 → NORMAL       → Pas d'ajustement
        VIX > 25  → EXTENSION    → Boost mean-revert levels

        Args:
            level: Niveau MenthorQ avec 'type' et 'priority'
            snapshot: Snapshot marché avec 'vix'

        Returns:
            Priority ajustée (capped à 1.0)
        """
        vix = snapshot.get('vix', 17.0)
        priority = level.get('priority', 0.5)
        level_type = level.get('type', 'UNKNOWN')

        # VIX < 15: COMPRESSION → Favoriser breakouts
        if vix < 15:
            if level_type in ['GEX', 'OPTIONS_STRIKE', 'ROUND_NUMBER', 'GAMMA_WALL']:
                priority *= 1.15  # +15% priorité breakout
                logger.debug(f"🔵 VIX COMPRESSION ({vix:.1f}): Boost {level_type} +15%")
            elif level_type in ['VWAP_DAILY', 'VWAP_WEEKLY', 'VOLUME_PROFILE', 'PVWAP']:
                priority *= 0.90  # -10% priorité mean-revert

        # VIX > 25: EXTENSION → Favoriser mean-revert
        elif vix > 25:
            if level_type in ['VWAP_DAILY', 'VWAP_WEEKLY', 'VOLUME_PROFILE', 'PVWAP']:
                priority *= 1.20  # +20% priorité mean-revert
                logger.debug(f"🔴 VIX EXTENSION ({vix:.1f}): Boost {level_type} +20%")
            elif level_type in ['GEX', 'OPTIONS_STRIKE']:
                priority *= 0.85  # -15% (facilement cassés en haute vol)

        # VIX 15-25: NORMAL → Pas d'ajustement
        else:
            pass  # Comportement standard

        return min(priority, 1.0)

    def _adjust_priority_by_dealers_bias(self, level: Dict, snapshot: Dict, signal: TradeSignal) -> float:
        """
        🔴 P1: Ajuster priorité selon Dealers Bias (+15% Bible MenthorQ)

        Notre mia_bullish_score = Dealers Bias custom (format: -1.0 à +1.0)

        Bullish Bias > +0.3:
        - Renforcer Put Support (MM achètent les dips)
        - Affaiblir Call Resistance (MM vendent les rallies)

        Bearish Bias < -0.3:
        - Renforcer Call Resistance (MM vendent les rallies)
        - Affaiblir Put Support (MM vendent les dips aussi)

        Args:
            level: Niveau MenthorQ avec 'type' et 'priority'
            snapshot: Snapshot marché avec 'mia_bullish_score'
            signal: Signal directionnel (LONG/SHORT)

        Returns:
            Priority ajustée (capped à 1.0)
        """
        mia_bias = snapshot.get('mia_bullish_score', 0.0)
        priority = level.get('priority', 0.5)
        level_type = level.get('type', 'UNKNOWN')

        # Bullish Bias > +0.3: MM supportent le marché
        if mia_bias > 0.3:
            if level_type in ['PUT_SUPPORT', 'BLIND_SPOT_DOWN'] or \
               (level_type == 'GEX' and signal == TradeSignal.LONG):
                priority *= 1.15  # +15% (support MM actif)
                logger.debug(f"🟢 BULLISH BIAS ({mia_bias:+.2f}): Boost support +15%")
            elif level_type in ['CALL_RESISTANCE', 'BLIND_SPOT_UP'] or \
                 (level_type == 'GEX' and signal == TradeSignal.SHORT):
                priority *= 0.90  # -10% (résistance MM passive)

        # Bearish Bias < -0.3: MM résistent au marché
        elif mia_bias < -0.3:
            if level_type in ['CALL_RESISTANCE', 'BLIND_SPOT_UP'] or \
               (level_type == 'GEX' and signal == TradeSignal.SHORT):
                priority *= 1.15  # +15% (résistance MM active)
                logger.debug(f"🔴 BEARISH BIAS ({mia_bias:+.2f}): Boost résistance +15%")
            elif level_type in ['PUT_SUPPORT', 'BLIND_SPOT_DOWN'] or \
                 (level_type == 'GEX' and signal == TradeSignal.LONG):
                priority *= 0.90  # -10% (support MM passif)

        # Neutral -0.3 à +0.3: Pas d'ajustement
        else:
            pass

        return min(priority, 1.0)

    def _adjust_priority_by_gamma_side(self, level: Dict, snapshot: Dict) -> float:
        """
        🟡 BONUS: Ajuster priorité selon Gamma Side (+5% Bible)

        "below" → Negative Gamma → Directionnel (amplification mouvements)
        "above" → Positive Gamma → Mean-revert (stabilisation)

        Args:
            level: Niveau MenthorQ avec 'type' et 'priority'
            snapshot: Snapshot marché avec 'gamma_side'

        Returns:
            Priority ajustée (capped à 1.0)
        """
        gamma_side = snapshot.get('gamma_side', 'unknown')
        priority = level.get('priority', 0.5)
        level_type = level.get('type', 'UNKNOWN')

        # Negative Gamma (below): Momentum/Directionnel
        if gamma_side == 'below':
            if level_type in ['GEX', 'OPTIONS_STRIKE', 'NEXT_WALL', 'GAMMA_WALL']:
                priority *= 1.10  # +10% breakout levels
                logger.debug(f"⚫ NEGATIVE GAMMA: Boost {level_type} +10%")
            elif level_type in ['VWAP_DAILY', 'VOLUME_PROFILE']:
                priority *= 0.95  # -5% mean-revert levels

        # Positive Gamma (above): Mean-revert
        elif gamma_side == 'above':
            if level_type in ['VWAP_DAILY', 'VWAP_WEEKLY', 'VOLUME_PROFILE', 'PVWAP']:
                priority *= 1.10  # +10% mean-revert levels
                logger.debug(f"⚪ POSITIVE GAMMA: Boost {level_type} +10%")
            elif level_type in ['GEX', 'OPTIONS_STRIKE']:
                priority *= 0.95  # -5% breakout levels

        return min(priority, 1.0)

    # ═══════════════════════════════════════════════════════════════════
    # LAYER 1: MenthorQ (Signal Primaire)
    # ═══════════════════════════════════════════════════════════════════

    def validate_layer1_menthorq(self, snapshot: Dict) -> Layer1Result:
        """
        LAYER 1: MenthorQ ENRICHI - Extraction 85+ niveaux + Sélection optimale

        WORKFLOW ENRICHI (21/11/2025):
        1. Extraire TOUS les niveaux (85+) via _extract_all_menthorq_levels()
        2. Sélectionner niveau optimal via _find_closest_level()
        3. Détecter confluence via _detect_confluence()
        4. Scorer enrichi via _score_menthorq_level()
        5. Déterminer signal directionnel

        Returns:
            Layer1Result avec signal (LONG/SHORT/None) et confidence enrichie
        """
        symbol = snapshot.get('sym', 'NQ')[:2]  # ES, NQ, or RTY
        tick_size = self.config.TICK_SIZE.get(symbol, 0.25)
        mid = snapshot['mid']

        logger.debug("=" * 80)
        logger.debug("EXTRACTION 85+ NIVEAUX MENTHORQ")  # ✅ Optimisé: INFO → DEBUG
        logger.debug("=" * 80)
        logger.info(f"   Symbol: {symbol} | Prix: {mid}")

        # Initialisation variables
        menthorq_score = 0.0
        triggers = []
        breakdown = {}

        # === 1. GAMMA WALLS (10% weight) ===
        gamma_score, gamma_signal, gamma_triggers = self._analyze_gamma_walls(
            snapshot, mid, tick_size
        )
        menthorq_score += gamma_score
        triggers.extend(gamma_triggers)
        breakdown['gamma_walls'] = gamma_score

        # === 2. GEX LEVELS (10% weight) ===
        gex_score, gex_signal, gex_triggers = self._analyze_gex_levels(
            snapshot, mid, tick_size
        )
        menthorq_score += gex_score
        triggers.extend(gex_triggers)
        breakdown['gex_levels'] = gex_score

        # === 3. BLIND SPOTS (8% weight) ===
        blind_score, blind_signal, blind_triggers = self._analyze_blind_spots(
            snapshot, mid, tick_size
        )
        menthorq_score += blind_score
        triggers.extend(blind_triggers)
        breakdown['blind_spots'] = blind_score

        # === 4. HVL (High Vol Level) - NOUVEAU (Bible MenthorQ v2.0) ===
        hvl_regime, hvl_distance, hvl_confidence, hvl_triggers = self._analyze_hvl(
            snapshot, mid, tick_size
        )
        if hvl_regime:
            triggers.extend(hvl_triggers)
            breakdown['hvl_regime'] = hvl_regime
            breakdown['hvl_confidence'] = hvl_confidence
            # Stocker pour Layer 3 (utilisation dans contexte)
            snapshot['_hvl_regime'] = hvl_regime
            snapshot['_hvl_confidence'] = hvl_confidence

        # === 5. 0DTE LEVELS - NOUVEAU (Bible MenthorQ v2.0) ===
        has_0dte, dte_triggers = self._analyze_0dte_levels(
            snapshot, mid, tick_size
        )
        if has_0dte:
            triggers.extend(dte_triggers)
            breakdown['0dte_active'] = True
            logger.info("   ✅ Niveaux 0DTE détectés → Influence INTRADAY renforcée")

        # === 6. NEXT WALL (8% weight) ===
        wall_score, wall_signal, wall_triggers = self._analyze_next_wall(
            snapshot, mid, tick_size
        )
        menthorq_score += wall_score
        triggers.extend(wall_triggers)
        breakdown['next_wall'] = wall_score

        # === 7. DAILY EXTREMES (1-Day Max/Min) - NOUVEAU (Bible MenthorQ v2.0) ===
        daily_score, daily_signal, daily_triggers = self._analyze_daily_extremes(
            snapshot, mid, tick_size
        )
        menthorq_score += daily_score
        triggers.extend(daily_triggers)
        breakdown['daily_extremes'] = daily_score

        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 12/12/2025: NOUVEAUX NIVEAUX VWAP & VOLUME PROFILE
        # Ces niveaux génèrent +50-100% de signaux supplémentaires
        # ═══════════════════════════════════════════════════════════════════════

        # === 8. VWAP ENTRIES (VWAP Daily, Weekly, Prior) ===
        vwap_score, vwap_signal, vwap_triggers = self._analyze_vwap_entries(
            snapshot, mid, tick_size
        )
        menthorq_score += vwap_score
        triggers.extend(vwap_triggers)
        breakdown['vwap_entries'] = vwap_score

        # === 9. VWAP BANDS (±1σ, ±2σ) ===
        bands_score, bands_signal, bands_triggers = self._analyze_vwap_bands(
            snapshot, mid, tick_size
        )
        menthorq_score += bands_score
        triggers.extend(bands_triggers)
        breakdown['vwap_bands'] = bands_score

        # === 10. VOLUME PROFILE (POC, VAH, VAL) ===
        vp_score, vp_signal, vp_triggers = self._analyze_volume_profile(
            snapshot, mid, tick_size
        )
        menthorq_score += vp_score
        triggers.extend(vp_triggers)
        breakdown['volume_profile'] = vp_score

        # === 11. MENTHORQ SCORES (6% weight) ===
        scores_value, scores_triggers = self._analyze_menthorq_scores(snapshot)
        menthorq_score += scores_value
        triggers.extend(scores_triggers)
        breakdown['scores'] = scores_value

        # === DÉCISION FINALE LAYER 1 (WEIGHTED SCORING) ===
        # 🔍 DEBUG: Résultats de chaque analyse
        logger.debug("=" * 80)
        logger.debug("LAYER 1: RÉSULTATS PAR ANALYSE")  # ✅ Optimisé
        logger.debug("=" * 80)
        logger.info(f"   1️⃣ GAMMA WALLS: signal={gamma_signal.value if gamma_signal else 'None'}, score={gamma_score:.4f}")
        logger.info(f"      Triggers: {gamma_triggers}")
        logger.info(f"   2️⃣ GEX LEVELS: signal={gex_signal.value if gex_signal else 'None'}, score={gex_score:.4f}")
        logger.info(f"      Triggers: {gex_triggers}")
        logger.info(f"   3️⃣ BLIND SPOTS: signal={blind_signal.value if blind_signal else 'None'}, score={blind_score:.4f}")
        logger.info(f"      Triggers: {blind_triggers}")
        logger.info(f"   4️⃣ NEXT WALL: signal={wall_signal.value if wall_signal else 'None'}, score={wall_score:.4f}")
        logger.info(f"      Triggers: {wall_triggers}")
        logger.info(f"   5️⃣ DAILY EXTREMES: signal={daily_signal.value if daily_signal else 'None'}, score={daily_score:.4f}")
        logger.info(f"      Triggers: {daily_triggers}")
        # 🆕 12/12/2025: Nouveaux niveaux VWAP & Volume Profile
        logger.info(f"   6️⃣ VWAP ENTRIES: signal={vwap_signal.value if vwap_signal else 'None'}, score={vwap_score:.4f}")
        logger.info(f"      Triggers: {vwap_triggers}")
        logger.info(f"   7️⃣ VWAP BANDS: signal={bands_signal.value if bands_signal else 'None'}, score={bands_score:.4f}")
        logger.info(f"      Triggers: {bands_triggers}")
        logger.info(f"   8️⃣ VOLUME PROFILE: signal={vp_signal.value if vp_signal else 'None'}, score={vp_score:.4f}")
        logger.info(f"      Triggers: {vp_triggers}")
        logger.info(f"   9️⃣ MENTHORQ SCORES: score={scores_value:.4f}")
        logger.info(f"      Triggers: {scores_triggers}")
        logger.info("=" * 80)

        # Créer une liste de (signal, score) pour tous les signaux valides
        signal_weights = []
        if gamma_signal and gamma_score > 0:
            signal_weights.append((gamma_signal, gamma_score))
        if gex_signal and gex_score > 0:
            signal_weights.append((gex_signal, gex_score))
        if blind_signal and blind_score > 0:
            signal_weights.append((blind_signal, blind_score))
        if wall_signal and wall_score > 0:
            signal_weights.append((wall_signal, wall_score))
        if daily_signal and daily_score > 0:
            signal_weights.append((daily_signal, daily_score))
        # 🆕 12/12/2025: Ajouter VWAP et Volume Profile
        if vwap_signal and vwap_score > 0:
            signal_weights.append((vwap_signal, vwap_score))
        if bands_signal and bands_score > 0:
            signal_weights.append((bands_signal, bands_score))
        if vp_signal and vp_score > 0:
            signal_weights.append((vp_signal, vp_score))

        # Calculer le poids pour LONG et SHORT
        long_weight = sum(score for sig, score in signal_weights if sig == TradeSignal.LONG)
        short_weight = sum(score for sig, score in signal_weights if sig == TradeSignal.SHORT)

        # 🔍 DEBUG: Weighted scoring
        logger.info("🔍 DEBUG LAYER 1: WEIGHTED SCORING")
        logger.info(f"   Signal Weights List: {[(s.value, f'{sc:.4f}') for s, sc in signal_weights]}")
        logger.info(f"   📊 LONG Weight:  {long_weight:.4f}")
        logger.info(f"   📊 SHORT Weight: {short_weight:.4f}")
        logger.info(f"   Total Score: {menthorq_score:.4f}")

        # Déterminer la direction dominante
        final_signal = None
        total_score = menthorq_score

        # ✅ NOUVEAU 21/11 05:40: Extraire MIA Bullish Score pour confluence
        mia_score = snapshot.get('mia_bullish_score', 0)

        if len(signal_weights) >= 2:
            # Bonus de confluence (+20%) si 2+ signaux dans la même direction
            if long_weight > short_weight and long_weight > 0:
                final_signal = TradeSignal.LONG
                total_score = min(total_score * 1.2, 1.0)  # ✅ FIX 21/11 05:15: Clamp à 1.0

                # ✅ NOUVEAU 21/11 05:40: Bonus MIA Score si aligné
                if mia_score > 0.5:
                    total_score = min(total_score * 1.10, 1.0)  # Bonus 10%
                    triggers.append(f"✨ MIA Bullish aligned: {mia_score:.2f}")
                    logger.info(f"   ✨ BONUS MIA: MIA Score {mia_score:.2f} aligné avec signal LONG → +10%")

                triggers.append(f"✨ Bonus confluence: {len([s for s, _ in signal_weights if s == TradeSignal.LONG])} signaux LONG")
                logger.info(f"   ✅ Direction dominante: LONG (long_weight={long_weight:.4f} > short_weight={short_weight:.4f}) → total_score={total_score:.4f}")
            elif short_weight > long_weight and short_weight > 0:
                final_signal = TradeSignal.SHORT
                total_score = min(total_score * 1.2, 1.0)  # ✅ FIX 21/11 05:15: Clamp à 1.0

                # ✅ NOUVEAU 21/11 05:40: Bonus MIA Score si aligné
                if mia_score < -0.5:
                    total_score = min(total_score * 1.10, 1.0)  # Bonus 10%
                    triggers.append(f"✨ MIA Bearish aligned: {mia_score:.2f}")
                    logger.info(f"   ✨ BONUS MIA: MIA Score {mia_score:.2f} aligné avec signal SHORT → +10%")

                triggers.append(f"✨ Bonus confluence: {len([s for s, _ in signal_weights if s == TradeSignal.SHORT])} signaux SHORT")
                logger.info(f"   ✅ Direction dominante: SHORT (short_weight={short_weight:.4f} > long_weight={long_weight:.4f}) → total_score={total_score:.4f}")
        elif long_weight > 0:
            # 1 seul signal LONG
            final_signal = TradeSignal.LONG
            logger.info(f"   ✅ 1 seul signal: LONG (weight={long_weight:.4f})")
        elif short_weight > 0:
            # 1 seul signal SHORT
            final_signal = TradeSignal.SHORT
            logger.info(f"   ✅ 1 seul signal: SHORT (weight={short_weight:.4f})")

        # ═══════════════════════════════════════════════════════════════════════
        # 🔧 SOLUTION: Générer signal si aucun mais score suffisant
        # ═══════════════════════════════════════════════════════════════════════
        # Problème: Parfois aucun composant ne génère de signal directionnel
        # mais le score total est > seuil minimum (ex: NQ avec score 0.191)
        # Solution: Générer signal basé sur contexte (gamma_side, HVL)
        # ═══════════════════════════════════════════════════════════════════════
        if final_signal is None and total_score >= self.config.MIN_MENTHORQ_CONFIDENCE:
            # Log pour debug
            logger.info(
                f"[{symbol}] ℹ️ Aucun signal directionnel mais score suffisant "
                f"({total_score:.3f}). Génération signal basé sur contexte..."
            )

            # 🔥 FIX 12/12: Stratégie basée sur MIA BULLISH SCORE (tendance réelle)
            mia_score = snapshot.get('mia_bullish_score', 0)
            mid = snapshot.get('mid', 0)
            day_min = snapshot.get('1d_min', 0) or snapshot.get('day_min', 0)
            day_max = snapshot.get('1d_max', 0) or snapshot.get('day_max', 0)

            # Stratégie 1: Basé sur MIA bullish score (PRIORITAIRE)
            if mia_score > 0.30:
                final_signal = TradeSignal.LONG
                logger.info(f"[{symbol}]   → LONG (mia_score={mia_score:.2f} > 0.30 = BULLISH)")
            elif mia_score < -0.30:
                final_signal = TradeSignal.SHORT
                logger.info(f"[{symbol}]   → SHORT (mia_score={mia_score:.2f} < -0.30 = BEARISH)")
            # Stratégie 2: Basé sur position dans le range journalier
            elif day_min > 0 and day_max > 0 and mid > 0:
                day_range = day_max - day_min
                if day_range > 0:
                    position_pct = ((mid - day_min) / day_range) * 100
                    if mid < day_min:
                        # Prix SOUS le 1D Min → BREAKDOWN → SHORT
                        final_signal = TradeSignal.SHORT
                        logger.info(f"[{symbol}]   → SHORT (breakdown sous 1D_min)")
                    elif mid > day_max:
                        # Prix AU-DESSUS du 1D Max → BREAKOUT → LONG
                        final_signal = TradeSignal.LONG
                        logger.info(f"[{symbol}]   → LONG (breakout au-dessus 1D_max)")
                    elif position_pct < 30:
                        # Bas du range → potentiel LONG
                        final_signal = TradeSignal.LONG
                        logger.info(f"[{symbol}]   → LONG (bas du range: {position_pct:.0f}%)")
                    elif position_pct > 70:
                        # Haut du range → potentiel SHORT
                        final_signal = TradeSignal.SHORT
                        logger.info(f"[{symbol}]   → SHORT (haut du range: {position_pct:.0f}%)")
                    else:
                        # Milieu du range → pas de signal
                        logger.warning(f"[{symbol}]   ⚠️ Milieu du range ({position_pct:.0f}%) - pas de signal")
                else:
                    logger.warning(f"[{symbol}]   ⚠️ Range invalide - pas de signal")
            else:
                # Fallback: Pas de signal
                logger.warning(
                    f"[{symbol}]   ⚠️ Impossible de générer signal - "
                    f"Données insuffisantes"
                )

            # Réduire confidence légèrement (signal moins fiable)
            if final_signal is not None:
                total_score *= 0.85  # Pénalité 15%
                logger.info(
                    f"[{symbol}]   ℹ️ Confidence ajustée: {total_score:.3f} "
                    f"(pénalité -15% pour signal généré)"
                )

        # ═══════════════════════════════════════════════════════════════════════
        # 🔥 PHASE 2: DÉTECTION CONFLUENCE
        # ═══════════════════════════════════════════════════════════════════════

        confluence_bonus = 0.0
        confluence_description = "Aucune"

        if self.confluence_enabled:
            try:
                confluence_analysis = detect_confluences(snapshot, symbol)

                if confluence_analysis.total_count > 0:
                    confluence_bonus = confluence_analysis.max_bonus

                    # Log confluence détectée
                    logger.info(f"🎯 Confluence détectée: {confluence_analysis.total_count} groupe(s)")

                    if confluence_analysis.strongest_confluence:
                        c = confluence_analysis.strongest_confluence
                        logger.info(f"   Plus forte: {c.count} niveaux @ {c.price:.2f}")
                        logger.info(f"   Description: {c.description}")
                        logger.info(f"   Bonus: {c.bonus_confidence:.2f}")

                        confluence_description = c.description

                    # APPLIQUER LE BONUS À LA CONFIDENCE
                    # 🔥 P0-2: Limiter bonus max à 0.20 (21/11/2025 15:30)
                    confluence_bonus = min(confluence_bonus, 0.20)  # Max +20%
                    total_score += confluence_bonus
                    total_score = min(total_score, 1.0)  # Cap à 100%

                    logger.info(f"   ✅ Confidence après confluence: {total_score:.3f} "
                               f"(bonus={confluence_bonus:.3f}, max=0.20)")

            except Exception as e:
                logger.error(f"❌ Erreur détection confluence: {e}")

        # Ajouter confluence au breakdown
        breakdown['confluence'] = confluence_bonus

        # Validation finale: score total doit dépasser le minimum
        if total_score < self.config.MIN_MENTHORQ_CONFIDENCE:
            final_signal = None
            reason = f"MenthorQ: Score {total_score:.3f} < Min {self.config.MIN_MENTHORQ_CONFIDENCE:.3f}"
            logger.info(f"   ❌ Score insuffisant: {total_score:.3f} < {self.config.MIN_MENTHORQ_CONFIDENCE:.3f}")
        else:
            reason = f"MenthorQ: {len(triggers)} triggers, Score={total_score:.3f}, L={long_weight:.3f} vs S={short_weight:.3f}"
            if confluence_bonus > 0:
                reason += f", Confluence={confluence_description}"
            logger.info(f"   ✅ Score suffisant: {total_score:.3f} >= {self.config.MIN_MENTHORQ_CONFIDENCE:.3f}")

        # 🔍 DEBUG: Signal final
        logger.info("=" * 80)
        logger.debug(f"🎯 LAYER 1: SIGNAL FINAL = {final_signal.value if final_signal else 'NONE'}")  # ✅ Optimisé
        logger.info(f"   Total Confidence: {total_score:.3f}")
        logger.info("=" * 80)

        # Logs détaillés pour debug
        logger.info(f"📊 MenthorQ Layer 1 [{symbol}]: Gamma={gamma_score:.3f}, GEX={gex_score:.3f}, Blind={blind_score:.3f}, Wall={wall_score:.3f}, Scores={scores_value:.3f} → Total={total_score:.3f}")

        # 🔧 DIAGNOSTIC: Alerter si toutes les données primaires sont absentes
        if gamma_score == 0 and gex_score == 0 and blind_score == 0 and wall_score == 0:
            logger.warning(f"⚠️  [{symbol}] TOUTES les données MenthorQ primaires sont à ZÉRO !")
            logger.warning(f"   → call_resistance={snapshot.get('call_resistance', 'N/A')}, put_support={snapshot.get('put_support', 'N/A')}")
            logger.warning(f"   → gex_1={snapshot.get('gex_1', 'N/A')}, blind_spot_0={snapshot.get('blind_spot_0', 'N/A')}")
            logger.warning(f"   → next_wall={snapshot.get('next_wall', 'N/A')}")

            # Si données présentes mais scores = 0 → Seuils trop stricts
            # 🔧 FIX 08/12: Gérer None explicitement
            has_data = (
                (snapshot.get('call_resistance') or 0) > 0 or
                (snapshot.get('put_support') or 0) > 0 or
                (snapshot.get('gex_1') or 0) > 0 or
                (snapshot.get('blind_spot_0') or 0) > 0 or
                (snapshot.get('next_wall') or {}).get('price', 0) > 0
            )

            if has_data:
                logger.warning(f"   💡 DIAGNOSTIC: Données MenthorQ présentes mais SEUILS TROP STRICTS !")
                logger.warning(f"      → Distances probablement > seuils configurés")

        # 🔧 AJOUT 2025-11-13: COLLECTER LES NIVEAUX DE CONFLUENCE
        confluence_levels = []

        # Collecter tous les niveaux proches (< 100 ticks)
        CONFLUENCE_THRESHOLD_TICKS = 100

        # GEX levels
        for i in range(1, 11):
            gex_level = snapshot.get(f'gex_{i}', 0)
            if gex_level:
                dist_ticks = abs((mid - gex_level) / tick_size)
                if dist_ticks < CONFLUENCE_THRESHOLD_TICKS:
                    confluence_levels.append(gex_level)

        # Next Wall
        next_wall = snapshot.get('next_wall', {})
        if next_wall:
            nw_price = next_wall.get('price', 0)
            if nw_price:
                dist_ticks = abs((mid - nw_price) / tick_size)
                if dist_ticks < CONFLUENCE_THRESHOLD_TICKS:
                    confluence_levels.append(nw_price)

        # Blind Spots
        for i in range(10):
            blind_spot = snapshot.get(f'blind_spot_{i}', 0)
            if blind_spot:
                dist_ticks = abs((mid - blind_spot) / tick_size)
                if dist_ticks < CONFLUENCE_THRESHOLD_TICKS:
                    confluence_levels.append(blind_spot)

        # Gamma Walls - 🔧 FIX 08/12: Gérer None
        call_resistance = snapshot.get('call_resistance') or 0
        put_support = snapshot.get('put_support') or 0
        if call_resistance:
            dist_ticks = abs((mid - call_resistance) / tick_size)
            if dist_ticks < CONFLUENCE_THRESHOLD_TICKS:
                confluence_levels.append(call_resistance)
        if put_support:
            dist_ticks = abs((mid - put_support) / tick_size)
            if dist_ticks < CONFLUENCE_THRESHOLD_TICKS:
                confluence_levels.append(put_support)

        # HVL
        hvl = snapshot.get('hvl', 0)
        if hvl:
            dist_ticks = abs((mid - hvl) / tick_size)
            if dist_ticks < CONFLUENCE_THRESHOLD_TICKS:
                confluence_levels.append(hvl)

        # 🎯 CALCUL SL/TP SI CONFLUENCE DÉTECTÉE
        suggested_sl = None
        suggested_tp = None
        sl_distance_ticks = None

        if confluence_levels and final_signal:
            # Trier les niveaux (pour faciliter la détection)
            confluence_levels_sorted = sorted(set(confluence_levels))

            logger.info("=" * 80)
            logger.info(f"✨ {len(confluence_levels_sorted)} niveaux de confluence détectés:")
            for level in confluence_levels_sorted:
                dist = abs((mid - level) / tick_size)
                logger.info(f"   → {level:.2f} ({dist:.0f}t)")

            # 🎯 NOUVEAU 13-NOV-2025: Bonus pour confluences multiples
            if len(confluence_levels_sorted) >= 3:
                confluence_bonus = 0.05  # +5% pour 3+ confluences (déjà limité)
                total_score += confluence_bonus
                triggers.append(f"🎯 Bonus: {len(confluence_levels_sorted)} confluences (+{confluence_bonus:.2f})")
                logger.info(f"   🎯 BONUS CONFLUENCE: +{confluence_bonus:.2f} ({len(confluence_levels_sorted)} niveaux, max=0.05)")

            logger.info("=" * 80)

            # ═══════════════════════════════════════════════════════════════════════
            # 🆕 ENRICHISSEMENT MENTHORQ (21/11/2025) - OPTION C: AJOUT SANS CASSER
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("=" * 80)
            logger.info("ENRICHISSEMENT MENTHORQ: Extraction 85+ niveaux")
            logger.info("=" * 80)

            try:
                # Extraire TOUS les niveaux (85+)
                all_menthorq_levels = self._extract_all_menthorq_levels(snapshot, mid, symbol)
                logger.debug(f"✅ {len(all_menthorq_levels)} niveaux extraits")  # ✅ Optimisé

                if all_menthorq_levels and final_signal:
                    # Sélectionner niveau optimal
                    optimal_menthorq_level = self._find_closest_level(
                        all_menthorq_levels, mid, final_signal, symbol
                    )

                    if optimal_menthorq_level:
                        logger.debug(f"✅ Niveau optimal: {optimal_menthorq_level['type']} @ {optimal_menthorq_level['price']:.2f} ({optimal_menthorq_level['distance_ticks']:.0f}t, score={optimal_menthorq_level['score']:.2f})")  # ✅ Optimisé

                        # Détecter confluence enrichie
                        confluence_menthorq = self._detect_confluence(
                            all_menthorq_levels, optimal_menthorq_level, threshold_ticks=10
                        )
                        logger.debug(f"✅ {len(confluence_menthorq)} niveau(x) en confluence:")  # ✅ Optimisé
                        for conf in confluence_menthorq[:3]:  # Top 3
                            logger.info(f"   → {conf['type']} @ {conf['price']:.2f}")

                        # Scorer enrichi
                        enriched_score, enriched_validations = self._score_menthorq_level(
                            optimal_menthorq_level, snapshot, final_signal, confluence_menthorq
                        )

                        logger.debug(f"✅ Score enrichi = {enriched_score:.2%}")  # ✅ Optimisé

                        # ENRICHIR le score total (bonus jusqu'à +20%)
                        if enriched_score > total_score:
                            enrichment_bonus = min(enriched_score - total_score, 0.20)
                            total_score += enrichment_bonus
                            triggers.append(f"⭐ Enrichissement MenthorQ: +{enrichment_bonus:.2%}")
                            logger.info(f"   ⭐ BONUS ENRICHISSEMENT: +{enrichment_bonus:.2%} (score enrichi > ancien)")

                        logger.info(f"   📊 Score FINAL après enrichissement: {total_score:.2%}")
                    else:
                        logger.debug("⚠️ Aucun niveau optimal dans 50t")  # ✅ Optimisé
                else:
                    logger.info("   Pas d'enrichissement (niveaux vides ou pas de signal)")

            except Exception as e:
                logger.error(f"   ⚠️ Erreur enrichissement MenthorQ: {str(e)}")
                # Continue sans enrichissement (pas de crash)

            logger.info("=" * 80)

            # 🔥 ÉTAPE 1: VÉRIFIER BREAKOUT + PULLBACK (prioritaire)
            is_breakout, breakout_signal, broken_level = self._detect_breakout_pullback(
                entry_price=mid,
                confluence_levels=confluence_levels_sorted,
                snapshot=snapshot,
                tick_size=tick_size
            )

            if is_breakout and breakout_signal:
                # BREAKOUT+PULLBACK détecté → Overwrite signal Layer 1
                logger.info("🔥 BREAKOUT+PULLBACK PRIORITAIRE → Signal Layer 1 ajusté")
                final_signal = breakout_signal
                total_score += 0.10  # Bonus pour breakout+pullback
                triggers.append(f"🔥 Breakout+Pullback @ {broken_level:.2f}")

                # SL spécifique pour breakout+pullback
                if breakout_signal == TradeSignal.LONG:
                    suggested_sl = broken_level - (2 * tick_size)  # Sous niveau cassé
                else:
                    suggested_sl = broken_level + (2 * tick_size)  # Au-dessus niveau cassé

                sl_distance_ticks = abs((mid - suggested_sl) / tick_size)

                # TP normal (VWAP)
                vwap = snapshot.get('vwap', 0)
                vwap_up1 = snapshot.get('vwap_up1', 0)
                vwap_dn1 = snapshot.get('vwap_dn1', 0)

                if breakout_signal == TradeSignal.LONG:
                    suggested_tp = vwap_up1 if vwap_up1 > mid else vwap
                else:
                    suggested_tp = vwap_dn1 if vwap_dn1 < mid else vwap

                logger.info(f"   📍 SL Breakout+Pullback: {suggested_sl:.2f} ({sl_distance_ticks:.0f}t)")
                logger.info(f"   🎯 TP: {suggested_tp:.2f}")

            # 🎯 ÉTAPE 2: SINON, CALCUL SL/TP NORMAL (bounce sur confluence)
            if not is_breakout:
                # Calculer SL/TP optimaux (logique normale)
                suggested_sl, suggested_tp, sl_distance_ticks = self._calculate_sl_tp_from_confluence(
                    entry_price=mid,
                    signal=final_signal,
                    confluence_levels=confluence_levels_sorted,
                    snapshot=snapshot,
                    tick_size=tick_size,
                    symbol=symbol
                )

        return Layer1Result(
            signal=final_signal,
            confidence=total_score,
            reason=reason,
            triggers=triggers,
            breakdown=breakdown,
            confluence_levels=confluence_levels if confluence_levels else None,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            sl_distance_ticks=sl_distance_ticks
        )

    def _calculate_sl_tp_from_confluence(
        self,
        entry_price: float,
        signal: Optional[TradeSignal],
        confluence_levels: List[float],
        snapshot: Dict,
        tick_size: float,
        symbol: str
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        🎯 Calcule le SL et TP optimaux basés sur les niveaux de confluence détectés

        Logique professionnelle:
            - LONG: SL = 2-3 ticks SOUS le niveau de confluence le plus bas
            - SHORT: SL = 2-3 ticks AU-DESSUS du niveau de confluence le plus haut
            - TP = VWAP ou prochaine résistance/support majeur

        Args:
            entry_price: Prix d'entrée du trade
            signal: LONG ou SHORT
            confluence_levels: Liste des niveaux détectés [6875.00, 6872.32, ...]
            snapshot: Données ML_READY pour calculer TP (VWAP, etc.)
            tick_size: Taille du tick (0.25 pour ES, 0.25 pour NQ, 0.10 pour RTY)
            symbol: ES, NQ, ou RTY

        Returns:
            (sl_price, tp_price, sl_distance_ticks)
        """
        if not confluence_levels or not signal:
            return None, None, None

        # 📍 CALCUL STOP-LOSS
        sl_buffer_ticks = 2  # 2 ticks de buffer (sécurité)

        if signal == TradeSignal.LONG:
            # LONG: SL sous le niveau le plus BAS de la confluence
            lowest_level = min(confluence_levels)
            sl_price = lowest_level - (sl_buffer_ticks * tick_size)

            logger.info(f"   📍 [SL LONG] {sl_price:.2f} ({sl_buffer_ticks}t sous confluence @ {lowest_level:.2f})")

        else:  # SHORT
            # SHORT: SL au-dessus du niveau le plus HAUT de la confluence
            highest_level = max(confluence_levels)
            sl_price = highest_level + (sl_buffer_ticks * tick_size)

            logger.info(f"   📍 [SL SHORT] {sl_price:.2f} ({sl_buffer_ticks}t au-dessus confluence @ {highest_level:.2f})")

        sl_distance_ticks = abs((entry_price - sl_price) / tick_size)

        # ⚠️ SÉCURITÉ: SL minimum
        MIN_SL_TICKS = {
            'ES': 8,   # 8 ticks = 2 pts ES
            'NQ': 10,  # 10 ticks = 2.5 pts NQ
            'RTY': 15  # 15 ticks = 1.5 pts RTY
        }
        min_sl = MIN_SL_TICKS.get(symbol, 10)

        if sl_distance_ticks < min_sl:
            logger.warning(f"   ⚠️ SL trop serré ({sl_distance_ticks:.0f}t < {min_sl}t minimum)")
            logger.warning(f"      → Ajusté à {min_sl}t pour sécurité")

            if signal == TradeSignal.LONG:
                sl_price = entry_price - (min_sl * tick_size)
            else:
                sl_price = entry_price + (min_sl * tick_size)

            sl_distance_ticks = min_sl

        # 🎯 CALCUL TAKE-PROFIT
        vwap = snapshot.get('vwap', 0)
        vwap_up1 = snapshot.get('vwap_up1', 0)
        vwap_dn1 = snapshot.get('vwap_dn1', 0)

        if signal == TradeSignal.LONG:
            # LONG: TP = VWAP si au-dessus, sinon VWAP +1σ
            if vwap and vwap > entry_price:
                tp_price = vwap
                tp_label = "VWAP"
            elif vwap_up1 and vwap_up1 > entry_price:
                tp_price = vwap_up1
                tp_label = "VWAP +1σ"
            else:
                # Sinon, TP = Entry + (2x distance SL) pour R/R 2:1
                tp_price = entry_price + (sl_distance_ticks * tick_size * 2)
                tp_label = "R/R 2:1"

            logger.info(f"   🎯 [TP LONG] {tp_price:.2f} ({tp_label})")

        else:  # SHORT
            # SHORT: TP = VWAP si en-dessous, sinon VWAP -1σ
            if vwap and vwap < entry_price:
                tp_price = vwap
                tp_label = "VWAP"
            elif vwap_dn1 and vwap_dn1 < entry_price:
                tp_price = vwap_dn1
                tp_label = "VWAP -1σ"
            else:
                # Sinon, TP = Entry - (2x distance SL) pour R/R 2:1
                tp_price = entry_price - (sl_distance_ticks * tick_size * 2)
                tp_label = "R/R 2:1"

            logger.info(f"   🎯 [TP SHORT] {tp_price:.2f} ({tp_label})")

        # 📊 Calculer R/R
        tp_distance_ticks = abs((tp_price - entry_price) / tick_size)
        r_r_ratio = tp_distance_ticks / sl_distance_ticks if sl_distance_ticks > 0 else 0

        logger.info(f"   📊 R/R Ratio: {r_r_ratio:.2f}:1 (TP={tp_distance_ticks:.0f}t / SL={sl_distance_ticks:.0f}t)")

        return sl_price, tp_price, sl_distance_ticks

    def _detect_breakout_pullback(
        self,
        entry_price: float,
        confluence_levels: List[float],
        snapshot: Dict,
        tick_size: float
    ) -> Tuple[bool, Optional[TradeSignal], Optional[float]]:
        """
        🔥 DÉTECTE UN PATTERN BREAKOUT + PULLBACK

        Logique professionnelle:
            1. Un niveau de confluence a été CASSÉ récemment (breakout)
            2. Prix revient TESTER ce niveau (pullback)
            3. Ancien support devient résistance (ou vice-versa)
            4. Entrée sur le pullback avec SL de l'autre côté du niveau

        Conditions de BREAKOUT VALIDE:
            - Volume élevé (> 1.5x moyenne)
            - Momentum fort (delta burst)
            - Cassure nette (> 5 ticks au-delà du niveau)

        Conditions de PULLBACK VALIDE:
            - Prix revenu proche du niveau (< 10 ticks)
            - Volume diminué (consolidation)
            - Reversal pattern (wicks de rejection)

        Args:
            entry_price: Prix actuel
            confluence_levels: Niveaux de confluence détectés
            snapshot: Données ML_READY
            tick_size: Taille du tick

        Returns:
            (is_breakout_pullback, signal, broken_level)
        """
        if not confluence_levels:
            return False, None, None

        # Récupérer les données nécessaires
        high = snapshot.get('high', 0)
        low = snapshot.get('low', 0)
        volume = snapshot.get('volume', 1)
        delta = snapshot.get('delta', 0)
        delta_burst = snapshot.get('delta_burst', 0)
        upper_wick_ticks = snapshot.get('upper_wick_ticks', 0)
        lower_wick_ticks = snapshot.get('lower_wick_ticks', 0)

        if not (high and low):
            return False, None, None

        # Seuils de détection
        BREAKOUT_MIN_DISTANCE = 5   # ticks au-delà du niveau
        PULLBACK_MAX_DISTANCE = 10  # ticks de retour au niveau
        MIN_DELTA_BURST = 10        # Volume burst minimum
        MIN_WICK_REJECTION = 3      # Ticks de wick minimum

        # 🔍 Chercher un niveau cassé récemment
        for level in confluence_levels:
            # Calculer les distances
            dist_to_level = abs((entry_price - level) / tick_size)
            high_beyond_level = (high - level) / tick_size
            low_beyond_level = (level - low) / tick_size

            # ════════════════════════════════════════════════════════════
            # CAS 1: BREAKOUT UP → PULLBACK → LONG (continuation haussière)
            # ════════════════════════════════════════════════════════════
            # Niveau cassé vers le HAUT (ancienne résistance devient support)
            if high_beyond_level > BREAKOUT_MIN_DISTANCE:  # Cassé UP
                # Prix revenu proche du niveau (pullback)
                if dist_to_level < PULLBACK_MAX_DISTANCE and entry_price > level:
                    # Vérifier confirmation de rebond (bullish rejection)
                    has_bullish_rejection = (
                        lower_wick_ticks > MIN_WICK_REJECTION or  # Wick bas (rejet vendeurs)
                        delta > 0 or                               # Delta positif
                        abs(delta_burst) > MIN_DELTA_BURST         # Volume burst
                    )

                    if has_bullish_rejection:
                        logger.info("=" * 80)
                        logger.info("🔥 BREAKOUT + PULLBACK DÉTECTÉ (LONG)")
                        logger.info(f"   Niveau cassé UP: {level:.2f}")
                        logger.info(f"   High breakout: {high:.2f} (+{high_beyond_level:.0f}t)")
                        logger.info(f"   Prix actuel: {entry_price:.2f} (pullback à {dist_to_level:.0f}t du niveau)")
                        logger.info(f"   Confirmation: lower_wick={lower_wick_ticks:.0f}t, delta={delta}")
                        logger.info(f"   → SIGNAL: LONG (continuation après pullback)")
                        logger.info(f"   → SL: {level - (2 * tick_size):.2f} (sous ancien support)")
                        logger.info("=" * 80)

                        return True, TradeSignal.LONG, level

            # ════════════════════════════════════════════════════════════
            # CAS 2: BREAKOUT DOWN → PULLBACK → SHORT (continuation baissière)
            # ════════════════════════════════════════════════════════════
            # Niveau cassé vers le BAS (ancien support devient résistance)
            elif low_beyond_level > BREAKOUT_MIN_DISTANCE:  # Cassé DOWN
                # Prix revenu proche du niveau (pullback)
                if dist_to_level < PULLBACK_MAX_DISTANCE and entry_price < level:
                    # Vérifier confirmation de rejection (bearish rejection)
                    has_bearish_rejection = (
                        upper_wick_ticks > MIN_WICK_REJECTION or  # Wick haut (rejet acheteurs)
                        delta < 0 or                               # Delta négatif
                        abs(delta_burst) > MIN_DELTA_BURST         # Volume burst
                    )

                    if has_bearish_rejection:
                        logger.info("=" * 80)
                        logger.info("🔥 BREAKOUT + PULLBACK DÉTECTÉ (SHORT)")
                        logger.info(f"   Niveau cassé DOWN: {level:.2f}")
                        logger.info(f"   Low breakout: {low:.2f} (-{low_beyond_level:.0f}t)")
                        logger.info(f"   Prix actuel: {entry_price:.2f} (pullback à {dist_to_level:.0f}t du niveau)")
                        logger.info(f"   Confirmation: upper_wick={upper_wick_ticks:.0f}t, delta={delta}")
                        logger.info(f"   → SIGNAL: SHORT (continuation après pullback)")
                        logger.info(f"   → SL: {level + (2 * tick_size):.2f} (au-dessus ancienne résistance)")
                        logger.info("=" * 80)

                        return True, TradeSignal.SHORT, level

        # Aucun breakout+pullback détecté
        return False, None, None

    def _detect_bounce_pattern(self, snapshot: Dict, level_price: float, level_type: str, tick_size: float) -> Tuple[bool, Optional[str]]:
        """
        🔄 DÉTECTE UN PATTERN DE BOUNCE (rejection) SUR UN NIVEAU

        Args:
            snapshot: ML_READY data
            level_price: Prix du niveau (GEX, gamma wall, etc.)
            level_type: 'support' ou 'resistance'
            tick_size: Taille du tick

        Returns:
            (bounce_detected, direction)

        Conditions de BOUNCE:
            1. Prix très proche du niveau (< 5 ticks)
            2. Grande mèche de rejection (> 40% du range)
            3. Volume climax (confirmation)
        """
        mid = snapshot.get('mid', 0)
        if not mid:
            return False, None

        # 1. Distance au niveau
        distance_ticks = abs((mid - level_price) / tick_size)
        if distance_ticks > 5:  # Trop loin, pas un bounce
            return False, None

        # 2. Wick de rejection
        upper_wick = snapshot.get('upper_wick_ticks', 0)
        lower_wick = snapshot.get('lower_wick_ticks', 0)
        total_range = snapshot.get('total_range_ticks', 0)

        if total_range == 0:
            return False, None

        # Support: doit avoir lower wick > 40%
        # Resistance: doit avoir upper wick > 40%
        if level_type == 'support':
            wick_ratio = lower_wick / total_range
            rejection = wick_ratio > 0.40
            direction = "LONG" if rejection else None
        else:  # resistance
            wick_ratio = upper_wick / total_range
            rejection = wick_ratio > 0.40
            direction = "SHORT" if rejection else None

        if not rejection:
            return False, None

        # 3. Volume climax (utilise la fonction helper)
        sess = snapshot.get('session_id', 'US')
        sym = (snapshot.get('sym', '') or '').upper()
        vol = snapshot.get('volume', 0)

        # Seuil adaptatif selon session/symbole
        base = 35 if sess == 'Asia' else (45 if sess == 'EU' else 55)
        if 'NQ' in sym:
            base -= 3
        if 'RTY' in sym:
            base -= 5

        volume_climax = vol >= base

        if not volume_climax:
            return False, None

        return True, direction

    def _analyze_gamma_walls(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        Analyse gamma walls selon MenthorQ Bible v2.0

        📚 Sources MenthorQ:
           - Call Resistance = Strike avec plus fort Net Call Gamma (hedging coiffe hausses)
           - Put Support = Strike avec plus fort Net Put Gamma (plancher de marché)
           - Gamma Side = Position vs gamma max (régime structurel)

        Logique Bible MenthorQ:
           • CR = RÉSISTANCE: Rejets probables, dealers vendent pour hedger
           • PS = SUPPORT: Rebonds probables, dealers achètent pour hedger
           • gamma_side enrichit la lecture (below=bullish, above=bearish)

        SCENARIO 1: BOUNCE (0-5 ticks + rejection) - PRIORITAIRE [Bible: Touch/Très Proche]
        SCENARIO 2: PULL (10-200 ticks + attraction) - SECONDAIRE [Bible: Proche/Moyen]
        """
        score = 0.0
        signal = None
        triggers = []

        # 🔧 FIX 08/12: Gérer None explicitement (fallback 0 ne marche pas si valeur = None)
        call_res = snapshot.get('call_resistance') or 0
        put_sup = snapshot.get('put_support') or 0
        gamma_side = snapshot.get('gamma_side', '')
        symbol = snapshot.get('sym', 'NQ')[:2]

        logger.debug("Gamma Walls Analysis:")  # ✅ Optimisé
        logger.info(f"   call_resistance={call_res}, put_support={put_sup}, mid={mid}")
        logger.info(f"   gamma_side={gamma_side} [below=bullish régime, above=bearish régime]")
        logger.info(f"   symbol={symbol}, tick_size={tick_size}")

        if not call_res or not put_sup:
            logger.info(f"   ❌ Données manquantes (call_res={call_res}, put_sup={put_sup})")
            return score, signal, triggers

        # Distance aux walls
        d_call_ticks = (call_res - mid) / tick_size
        d_put_ticks = (mid - put_sup) / tick_size

        logger.info(f"   📏 d_call_ticks={d_call_ticks:.2f} (positif si call AU-DESSUS)")
        logger.info(f"   📏 d_put_ticks={d_put_ticks:.2f} (positif si put EN-DESSOUS)")

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 1: BOUNCE sur put support (< 5 ticks + rejection)
        # ═══════════════════════════════════════════════════════════
        if d_put_ticks < 5:
            bounce_detected, bounce_direction = self._detect_bounce_pattern(
                snapshot, put_sup, 'support', tick_size
            )
            if bounce_detected and bounce_direction == "LONG":
                signal = TradeSignal.LONG
                score = self.config.MENTHORQ_WEIGHTS['gamma_walls'] * 1.3  # +30% bonus bounce
                triggers.append(f"🔄 PUT WALL BOUNCE UP @ {put_sup:.2f} ({d_put_ticks:.0f}t)")
                return score, signal, triggers

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 2: BOUNCE sur call resistance (< 5 ticks + rejection)
        # ═══════════════════════════════════════════════════════════
        if d_call_ticks < 5:
            bounce_detected, bounce_direction = self._detect_bounce_pattern(
                snapshot, call_res, 'resistance', tick_size
            )
            if bounce_detected and bounce_direction == "SHORT":
                signal = TradeSignal.SHORT
                score = self.config.MENTHORQ_WEIGHTS['gamma_walls'] * 1.3  # +30% bonus bounce
                triggers.append(f"🔄 CALL WALL BOUNCE DOWN @ {call_res:.2f} ({d_call_ticks:.0f}t)")
                return score, signal, triggers

        # Seuil adaptatif par symbole
        max_distance = self.config.GAMMA_WALL_MAX_DISTANCE_TICKS.get(symbol, 80)
        max_wall_distance = 200  # ticks - Ignorer si trop loin pour être significatif

        # ═══════════════════════════════════════════════════════════
        # 🔥 FIX 12/12: SCENARIO BREAKDOWN - Prix SOUS le PUT support
        # ═══════════════════════════════════════════════════════════
        if d_put_ticks < 0:
            # Prix en-dessous du PUT support = BREAKDOWN = SHORT
            breakdown_distance = abs(d_put_ticks)
            if breakdown_distance < max_wall_distance:
                signal = TradeSignal.SHORT
                score = self.config.MENTHORQ_WEIGHTS['gamma_walls'] * 1.2  # +20% bonus breakdown
                triggers.append(f"📉 BREAKDOWN sous PUT support ({d_put_ticks:.0f}t)")
                logger.info(f"   🔴 BREAKDOWN: Prix SOUS PUT support → Signal SHORT")
                logger.info(f"   → SIGNAL=SHORT, score={score:.4f} (PUT support cassé → SHORT)")

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 3: PULL vers put support (0-80 ticks AU-DESSUS)
        # ═══════════════════════════════════════════════════════════
        elif 0 < d_put_ticks < max_distance:
            logger.info(f"   ✅ SCENARIO 3: d_put_ticks={d_put_ticks:.0f} < max_distance={max_distance}")
            # Si gamma_side confirme OU si on est vraiment proche (< 20 ticks)
            if gamma_side == 'below' or d_put_ticks < 20:
                signal = TradeSignal.LONG
                score = self.config.MENTHORQ_WEIGHTS['gamma_walls']
                confidence_info = f" [gamma_side={gamma_side}]" if gamma_side else ""
                triggers.append(f"🧲 PUT WALL PULL UP ({d_put_ticks:.0f}t){confidence_info}")
                logger.info(f"   → SIGNAL=LONG, score={score:.4f} (PUT support → LONG)")

        # ═══════════════════════════════════════════════════════════
        # 🔥 FIX 12/12: SCENARIO BREAKOUT - Prix AU-DESSUS du CALL resistance
        # ═══════════════════════════════════════════════════════════
        if d_call_ticks < 0:
            # Prix au-dessus du CALL resistance = BREAKOUT = LONG
            breakout_distance = abs(d_call_ticks)
            if breakout_distance < max_wall_distance:
                signal = TradeSignal.LONG
                score = self.config.MENTHORQ_WEIGHTS['gamma_walls'] * 1.2  # +20% bonus breakout
                triggers.append(f"📈 BREAKOUT au-dessus CALL resistance ({d_call_ticks:.0f}t)")
                logger.info(f"   🟢 BREAKOUT: Prix AU-DESSUS CALL resistance → Signal LONG")
                logger.info(f"   → SIGNAL=LONG, score={score:.4f} (CALL resistance cassé → LONG)")

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 4: PULL vers call resistance (0-80 ticks EN-DESSOUS)
        # ═══════════════════════════════════════════════════════════
        elif abs(d_call_ticks) > max_wall_distance:
            logger.debug(f"   ⚠️ CALL WALL ignoré: distance {d_call_ticks:.0f}t > {max_wall_distance}t (trop loin)")
            # Ne pas ajouter ce trigger
        elif 0 < d_call_ticks < max_distance:
            logger.info(f"   ✅ SCENARIO 4: d_call_ticks={d_call_ticks:.0f} < max_distance={max_distance}")
            # Si gamma_side confirme OU si on est vraiment proche (< 20 ticks)
            if gamma_side == 'above' or d_call_ticks < 20:
                signal = TradeSignal.SHORT
                score = self.config.MENTHORQ_WEIGHTS['gamma_walls']
                confidence_info = f" [gamma_side={gamma_side}]" if gamma_side else ""
                triggers.append(f"🧲 CALL WALL PULL DOWN ({d_call_ticks:.0f}t){confidence_info}")
                logger.info(f"   → SIGNAL=SHORT, score={score:.4f} (CALL resistance → SHORT)")

        if signal is None:
            logger.info(f"   ❌ Aucun scénario valide (d_put={d_put_ticks:.0f}, d_call={d_call_ticks:.0f}, max={max_distance})")

        return score, signal, triggers

    def _analyze_gex_levels(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        Analyse GEX levels selon Bible MenthorQ v2.0

        📚 Sources MenthorQ Officielles:
           - GEX = Zones d'exposition GAMMA AGRÉGÉE (niveaux "sticky")
           - GEX Levels 1→10 = Tournants intraday, cibles scalp, bornes de zone

        ⚠️ AVERTISSEMENT BIBLE MENTHORQ:
           "GEX seuls = zones de réaction, PAS de signal directionnel brut !"
           "MEILLEUR en CONFLUENCE avec HVL/CR/PS/Blind Spots"

        Bible MenthorQ - Grille distance:
           • Touch (≤5t): Réaction IMMÉDIATE (bounce/rejection) [Priorité absolue]
           • Proche (≤25t): Attraction "pull" vers niveau [Entrée anticipée]
           • Moyen (25-100t): Rôle structurel [Attendre confluence]
           • Loin (≥100t): Impact faible [Biais seulement]

        SCENARIO 1: BOUNCE (0-5 ticks + rejection) - PRIORITAIRE
        SCENARIO 2A: Support/Resistance (5-50 ticks) - Aligné doc MenthorQ
        SCENARIO 2B: Magnetic Pull (50-120 ticks) - Attraction faible
        """
        score = 0.0
        signal = None
        triggers = []
        symbol = snapshot.get('sym', 'NQ')[:2]

        # Récupérer tous les GEX levels
        gex_levels = []
        for i in range(1, 11):
            gex = snapshot.get(f'gex_{i}', 0)
            if gex > 0:
                gex_levels.append(gex)

        logger.debug(f"GEX Levels Analysis:")  # ✅ Optimisé
        logger.info(f"   GEX levels trouvés: {gex_levels}")
        logger.info(f"   Mid: {mid}")

        # ⚠️ AVERTISSEMENT BIBLE MENTHORQ
        logger.info("📚 Bible MenthorQ: GEX = zones de réaction, NON directionnelles seules")
        logger.info("   → Meilleur en CONFLUENCE avec CR/PS/HVL/Blind Spots")

        if not gex_levels:
            logger.info(f"   ❌ Aucun GEX level disponible")
            return score, signal, triggers

        # Trouver le GEX le plus proche
        gex_distances = [(gex, abs(mid - gex)) for gex in gex_levels]
        nearest_gex, nearest_dist = min(gex_distances, key=lambda x: x[1])
        nearest_dist_ticks = nearest_dist / tick_size

        logger.info(f"   nearest_gex={nearest_gex:.2f}, distance={nearest_dist_ticks:.2f} ticks")
        logger.info(f"   mid < gex? {mid < nearest_gex} (si True → LONG, si False → SHORT)")

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 1: BOUNCE (Prix très proche + rejection)
        # ═══════════════════════════════════════════════════════════
        if nearest_dist_ticks < 5:  # Très proche (< 5 ticks)
            level_type = 'support' if mid > nearest_gex else 'resistance'
            bounce_detected, bounce_direction = self._detect_bounce_pattern(
                snapshot, nearest_gex, level_type, tick_size
            )

            if bounce_detected:
                signal = TradeSignal.LONG if bounce_direction == "LONG" else TradeSignal.SHORT
                score = self.config.MENTHORQ_WEIGHTS['gex_levels'] * 1.3  # +30% bonus bounce
                triggers.append(f"🔄 GEX BOUNCE {bounce_direction} @ {nearest_gex:.2f} ({nearest_dist_ticks:.0f}t)")
                return score, signal, triggers

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 2: DOUBLE LOGIQUE GEX
        # ═══════════════════════════════════════════════════════════
        # ✅ LOGIQUE CONFIRMÉE PAR DOCUMENTATION OFFICIELLE MENTHORQ
        # Source: METHODE_MENTHORQ_ELITE.md (seuils gamma: 20 ticks max, 5 ticks strong)
        # Ajustement: GEX plus serré aligné avec philosophie MenthorQ
        #
        # < 50 ticks : GEX = SUPPORT/RESISTANCE (bounce/rejection) ✅ AJUSTÉ
        # 50-120 ticks : GEX = MAGNETIC PULL (attraction faible)
        # ═══════════════════════════════════════════════════════════
        max_distance = self.config.GEX_LEVEL_MAX_DISTANCE_TICKS.get(symbol, 50)

        if nearest_dist_ticks < 50:
            # TRÈS PROCHE : GEX agit comme Support/Resistance
            logger.info(f"   ✅ SCENARIO 2A: TRÈS PROCHE ({nearest_dist_ticks:.0f}t < 50t) → GEX = SUPPORT/RESISTANCE")
            if mid < nearest_gex:
                # Prix EN-DESSOUS du GEX → GEX = RESISTANCE → Rebond DOWN
                signal = TradeSignal.SHORT
                triggers.append(f"🔴 GEX RESISTANCE @ {nearest_gex:.2f} ({nearest_dist_ticks:.0f}t)")
                logger.info(f"   → SIGNAL=SHORT (mid={mid:.2f} < gex={nearest_gex:.2f} → GEX resistance, rebond DOWN)")
            else:
                # Prix AU-DESSUS du GEX → GEX = SUPPORT → Rebond UP
                signal = TradeSignal.LONG
                triggers.append(f"🟢 GEX SUPPORT @ {nearest_gex:.2f} ({nearest_dist_ticks:.0f}t)")
                logger.info(f"   → SIGNAL=LONG (mid={mid:.2f} > gex={nearest_gex:.2f} → GEX support, rebond UP)")

            # Score selon proximité
            for threshold, weight in self.config.GEX_PROXIMITY_THRESHOLDS.items():
                if nearest_dist_ticks < threshold:
                    score = self.config.MENTHORQ_WEIGHTS['gex_levels'] * (weight / 0.10)
                    logger.info(f"   Score={score:.4f} (threshold={threshold}, weight={weight})")
                    break
            else:
                # Si > 50 ticks dans le seuil config
                score = self.config.MENTHORQ_WEIGHTS['gex_levels'] * 0.5
                logger.info(f"   Score={score:.4f} (proche mais > 50t)")

        elif nearest_dist_ticks < max_distance:
            # LOIN : GEX agit comme un aimant faible (magnetic pull)
            logger.info(f"   ✅ SCENARIO 2B: LOIN ({nearest_dist_ticks:.0f}t, 50-{max_distance}t) → GEX = MAGNETIC PULL (faible)")
            if mid < nearest_gex:
                signal = TradeSignal.LONG
                triggers.append(f"🧲 GEX PULL UP @ {nearest_gex:.2f} ({nearest_dist_ticks:.0f}t)")
                logger.info(f"   → SIGNAL=LONG (mid={mid:.2f} < gex={nearest_gex:.2f} → pull UP)")
            else:
                signal = TradeSignal.SHORT
                triggers.append(f"🧲 GEX PULL DOWN @ {nearest_gex:.2f} ({nearest_dist_ticks:.0f}t)")
                logger.info(f"   → SIGNAL=SHORT (mid={mid:.2f} > gex={nearest_gex:.2f} → pull DOWN)")

            # Score faible pour attraction lointaine
            score = self.config.MENTHORQ_WEIGHTS['gex_levels'] * 0.3
            logger.info(f"   Score={score:.4f} (attraction lointaine)")
        else:
            logger.info(f"   ❌ Distance trop grande: {nearest_dist_ticks:.0f} >= {max_distance}")

        # ⚠️ Vérifier confluence (Bible MenthorQ: GEX meilleur avec confluence)
        if score > 0:
            has_confluence = self._check_gex_confluence(snapshot, nearest_gex, tick_size)
            if not has_confluence:
                logger.warning("⚠️ GEX utilisé SEUL sans confluence CR/PS/Blind Spot/HVL")
                logger.warning("   → Signal FAIBLE selon Bible MenthorQ")
            else:
                # Bonus si confluence détectée
                score *= 1.2
                triggers.append("✨ Confluence GEX détectée")
                logger.info(f"✨ Confluence GEX + autre niveau MQ → bonus +20%")

        return score, signal, triggers

    def _check_gex_confluence(self, snapshot: Dict, gex_price: float, tick_size: float) -> bool:
        """
        Vérifie si GEX est en confluence avec autre niveau MenthorQ

        Bible MenthorQ v2.0: GEX EXTRA-PUISSANT en confluence avec CR/PS/HVL/Blind Spots/Next Wall

        Returns:
            True si confluence détectée (autre niveau < 15 ticks du GEX)
        """
        confluence_threshold = 15  # ticks

        # 🔧 AJOUT 2025-11-13: Vérifier Next Wall (PRIORITÉ HAUTE)
        next_wall = snapshot.get('next_wall', {})
        if next_wall:
            nw_price = next_wall.get('price', 0)
            if nw_price and abs((nw_price - gex_price) / tick_size) < 5:  # < 5 ticks = même niveau !
                logger.info(f"   ✅✨ CONFLUENCE MAJEURE: GEX + Next Wall @ {nw_price:.2f} (MÊME NIVEAU !)")
                return True

        # Vérifier CR/PS - 🔧 FIX 08/12: Gérer None
        cr = snapshot.get('call_resistance') or 0
        ps = snapshot.get('put_support') or 0

        if cr and abs((cr - gex_price) / tick_size) < confluence_threshold:
            logger.info(f"   ✅ Confluence GEX + CR @ {cr:.2f}")
            return True

        if ps and abs((ps - gex_price) / tick_size) < confluence_threshold:
            logger.info(f"   ✅ Confluence GEX + PS @ {ps:.2f}")
            return True

        # Vérifier Blind Spots
        for i in range(9):
            bs = snapshot.get(f'blind_spot_{i}', 0)
            if bs and abs((bs - gex_price) / tick_size) < confluence_threshold:
                logger.info(f"   ✅ Confluence GEX + Blind Spot {i} @ {bs:.2f}")
                return True

        # Vérifier HVL si disponible
        hvl = snapshot.get('hvl', 0)
        if hvl and abs((hvl - gex_price) / tick_size) < confluence_threshold:
            logger.info(f"   ✅ Confluence GEX + HVL @ {hvl:.2f}")
            return True

        return False

    def _analyze_blind_spots(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        Analyse Blind Spots selon Bible MenthorQ v2.0

        📚 Sources MenthorQ Officielles:
           - Blind Spots = Zones de réaction CACHÉES issues de corrélations CROSS-ASSET
           - Détectées via interconnexions SPX/NDX/RUT non visibles sur chart classique
           - Réactions VIVES attendues: fakeouts, reversals soudains, accélérations

        ⚠️⚠️⚠️ AVERTISSEMENT SÉVÈRE BIBLE MENTHORQ:
           "NE JAMAIS trader Blind Spot SEUL sans validation orderflow !"
           "Éviter d'entrer DANS la zone sans confirmation Layer 2 (delta/volume/DOM)"
           "EXTRA-PUISSANT en confluence avec GEX/HVL/CR/PS"

        Bible MenthorQ - Exploitation:
           • Test + Rejet confirmé = Entrée contra-mouvement
           • Cassure validée = Suivre le mouvement
           • TOUJOURS exiger validation Layer 2 !

        SCENARIO 1: BOUNCE (0-5 ticks + rejection) - PRIORITAIRE
        SCENARIO 2: PULL (10-150 ticks + attraction) - SECONDAIRE
        """
        score = 0.0
        signal = None
        triggers = []
        symbol = snapshot.get('sym', 'NQ')[:2]

        # Récupérer blind spots
        blind_spots = []
        for i in range(9):
            bs = snapshot.get(f'blind_spot_{i}', 0)
            if bs > 0:
                blind_spots.append(bs)

        logger.debug("Blind Spots Analysis:")  # ✅ Optimisé
        logger.info(f"   Blind spots trouvés: {blind_spots}")
        logger.info(f"   Mid: {mid}")

        # ⚠️⚠️⚠️ AVERTISSEMENT SÉVÈRE BIBLE MENTHORQ
        logger.warning("📚 Bible MenthorQ: Blind Spots = zones réaction CACHÉES cross-asset")
        logger.warning("   ⚠️ NE JAMAIS trader Blind Spot SEUL sans validation orderflow !")
        logger.warning("   ⚠️ Exiger confirmation Layer 2 (delta/volume/DOM) ABSOLUMENT")

        if not blind_spots:
            return score, signal, triggers

        # Trouver le blind spot le plus proche
        blind_distances = [(bs, abs(mid - bs)) for bs in blind_spots]
        nearest_blind, nearest_dist = min(blind_distances, key=lambda x: x[1])
        nearest_dist_ticks = nearest_dist / tick_size

        logger.info(f"   nearest_blind={nearest_blind:.2f}, distance={nearest_dist_ticks:.2f} ticks")

        # ⚠️ ALERTE si prix TRÈS PROCHE d'un Blind Spot
        if nearest_dist_ticks < 10:
            logger.warning(f"🚨 PRIX DANS BLIND SPOT @ {nearest_blind:.2f} ({nearest_dist_ticks:.0f}t)")
            logger.warning("   ⚠️ RISQUE ÉLEVÉ: Réaction vive possible (fakeout/reversal)")
            logger.warning("   → Exiger validation orderflow FORTE avant trade")
            triggers.append(f"🚨 BLIND SPOT ALERTE @ {nearest_blind:.2f}")

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 1: BOUNCE (Prix très proche + rejection)
        # ═══════════════════════════════════════════════════════════
        if nearest_dist_ticks < 5:  # Très proche (< 5 ticks)
            level_type = 'support' if mid > nearest_blind else 'resistance'
            bounce_detected, bounce_direction = self._detect_bounce_pattern(
                snapshot, nearest_blind, level_type, tick_size
            )

            if bounce_detected:
                signal = TradeSignal.LONG if bounce_direction == "LONG" else TradeSignal.SHORT
                score = self.config.MENTHORQ_WEIGHTS['blind_spots'] * 1.3  # +30% bonus bounce
                triggers.append(f"🔄 BLIND SPOT BOUNCE {bounce_direction} @ {nearest_blind:.2f} ({nearest_dist_ticks:.0f}t)")
                return score, signal, triggers

        # ═══════════════════════════════════════════════════════════
        # SCENARIO 2: PULL (Prix loin mais proche + magnetic attraction)
        # ═══════════════════════════════════════════════════════════
        max_distance = self.config.BLIND_SPOT_MAX_DISTANCE_TICKS.get(symbol, 70)

        if nearest_dist_ticks < max_distance:
            if mid < nearest_blind:
                signal = TradeSignal.LONG
                triggers.append(f"🧲 BLIND SPOT PULL UP ({nearest_dist_ticks:.0f}t)")
            else:
                signal = TradeSignal.SHORT
                triggers.append(f"🧲 BLIND SPOT PULL DOWN ({nearest_dist_ticks:.0f}t)")

            score = self.config.MENTHORQ_WEIGHTS['blind_spots']

        return score, signal, triggers

    def _analyze_hvl(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[Optional[str], float, float, List[str]]:
        """
        Analyse High Vol Level (HVL) selon Bible MenthorQ v2.0

        📚 Sources MenthorQ Officielles:
           - HVL = PIVOT de régime gamma (transition +γ ↔ −γ)
           - Zone de bascule entre "stabilité" vs "expansion/directionnalité"

        Bible MenthorQ - Régimes:
           • AU-DESSUS HVL (Positive Gamma):
             - Marché plus "STICKY" (mean-reverting)
             - Volatilité comprimée
             - Dealers STABILISENT (achètent baisse, vendent hausse)
             → Favoriser stratégies MEAN-REVERT

           • AU-DESSOUS HVL (Negative Gamma):
             - Marché plus DIRECTIONNEL/TRENDING
             - Volatilité expansive
             - Dealers AMPLIFIENT (vendent baisse, achètent hausse)
             → Favoriser stratégies TREND-FOLLOWING

        Comportements typiques:
           • PINNING: Prix "colle" au HVL (expiration proche)
           • BOUNCE: Rebond au test du HVL
           • BREAKDOWN: Cassure → changement de régime VIOLENT

        Returns:
            (regime, distance_ticks, confidence, triggers)
            regime: 'positive_gamma' ou 'negative_gamma' ou None
        """
        hvl = snapshot.get('hvl', 0)
        if not hvl:
            logger.info("   ℹ️ HVL non disponible")
            return None, 0, 0.0, []

        distance_ticks = (mid - hvl) / tick_size
        abs_distance = abs(distance_ticks)
        triggers = []

        # Déterminer régime
        if mid > hvl:
            regime = 'positive_gamma'
            regime_desc = "MEAN-REVERT (stable, dealers stabilisent)"
            regime_emoji = "🟢"
        else:
            regime = 'negative_gamma'
            regime_desc = "DIRECTIONNEL (volatile, dealers amplifient)"
            regime_emoji = "🔴"

        logger.info("═" * 60)
        logger.info("📊 HVL ANALYSIS (Bible MenthorQ v2.0):")
        logger.info("═" * 60)
        logger.info(f"   HVL @ {hvl:.2f}, Mid @ {mid:.2f}")
        logger.info(f"   Distance: {distance_ticks:+.0f} ticks (mid - hvl)")
        logger.info(f"   {regime_emoji} Régime: {regime.upper()}")
        logger.info(f"   → {regime_desc}")

        # ALERTE si très proche du HVL (< 10 ticks)
        if abs_distance < 10:
            logger.warning(f"🚨 PRIX TRÈS PROCHE HVL ({abs_distance:.0f}t)")
            logger.warning("   ⚠️ Risque PINNING ou BREAKDOWN violent")
            logger.warning("   → Prudence extrême, attendre cassure confirmée")
            triggers.append(f"🚨 Proche HVL @ {hvl:.2f} ({abs_distance:.0f}t)")

        # Confidence selon distance (plus proche = plus fort le régime)
        if abs_distance < 25:
            confidence = 1.0
            logger.info(f"   💪 Régime FORT (< 25 ticks)")
        elif abs_distance < 50:
            confidence = 0.8
            logger.info(f"   ⚡ Régime MOYEN (25-50 ticks)")
        else:
            confidence = 0.5
            logger.info(f"   ℹ️ Régime FAIBLE (> 50 ticks)")

        triggers.append(f"📊 HVL: {regime} @ {hvl:.2f} ({distance_ticks:+.0f}t)")
        logger.info("═" * 60)

        return regime, abs_distance, confidence, triggers

    def _analyze_0dte_levels(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[bool, List[str]]:
        """
        Analyse niveaux 0DTE selon Bible MenthorQ v2.0

        📚 Sources MenthorQ Officielles:
           - CR/PS 0DTE = Plafond/Plancher calculés échéance DU JOUR (≤24h)
           - Aimant INTRADAY plus "magnétique" (flux 0DTE massifs)
           - Hedging plus AGRESSIF (échéance proche)

        Bible MenthorQ - Particularités 0DTE:
           • Influence FORTE des flux options 0DTE (volume quotidien énorme)
           • Comportement plus ERRATIQUE en fin de journée
           • PINNING fréquent à l'approche de l'expiration
           • Cassure → EXPANSION possible si dealers forcés à recouvrir

        Utilisation:
           • SCALP / DAY-TRADE sur test du niveau
           • Stops SERRÉS (volatilité intraday)
           • Confluence avec GEX proches = signal FORT

        Returns:
            (has_0dte_levels, triggers)
        """
        triggers_0dte = []
        has_0dte = False

        # Chercher différents noms possibles pour 0DTE
        # ✅ FIX 05/12/2025: Utiliser les noms corrects du dumper C++ (minuscules)
        cr_0dte = snapshot.get('call_resistance_0dte', snapshot.get('cr_0DTE', 0))
        ps_0dte = snapshot.get('put_support_0dte', snapshot.get('ps_0DTE', 0))
        hvl_0dte = snapshot.get('hvl_0dte', snapshot.get('hvl_0DTE', 0))
        gamma_wall_0dte = snapshot.get('gamma_wall_0dte', snapshot.get('gamma_wall_0DTE', 0))

        if not cr_0dte and not ps_0dte and not hvl_0dte and not gamma_wall_0dte:
            logger.info("   ℹ️ Aucun niveau 0DTE disponible")
            return False, []

        logger.info("═" * 60)
        logger.info("🎯 0DTE LEVELS ANALYSIS (Bible MenthorQ v2.0):")
        logger.info("═" * 60)
        logger.info("   📚 Bible: Aimants INTRADAY, hedging AGRESSIF, PINNING fréquent")

        # Analyser CR 0DTE
        if cr_0dte:
            dist_cr = (cr_0dte - mid) / tick_size
            abs_dist_cr = abs(dist_cr)

            if abs_dist_cr < 25:  # Proche intraday
                has_0dte = True
                triggers_0dte.append(
                    f"🎯 CR 0DTE @ {cr_0dte:.2f} ({dist_cr:+.0f}t) - AIMANT INTRADAY"
                )
                logger.info(f"   🔴 CR 0DTE @ {cr_0dte:.2f} ({dist_cr:+.0f}t)")
                logger.info(f"      → Résistance magnétique INTRADAY")

                if abs_dist_cr < 10:
                    logger.warning("      ⚠️ TRÈS PROCHE → Risque PINNING ou CASSURE")

        # Analyser PS 0DTE
        if ps_0dte:
            dist_ps = (mid - ps_0dte) / tick_size
            abs_dist_ps = abs(dist_ps)

            if abs_dist_ps < 25:
                has_0dte = True
                triggers_0dte.append(
                    f"🎯 PS 0DTE @ {ps_0dte:.2f} ({dist_ps:+.0f}t) - AIMANT INTRADAY"
                )
                logger.info(f"   🟢 PS 0DTE @ {ps_0dte:.2f} ({dist_ps:+.0f}t)")
                logger.info(f"      → Support magnétique INTRADAY")

                if abs_dist_ps < 10:
                    logger.warning("      ⚠️ TRÈS PROCHE → Risque PINNING ou CASSURE")

        # Analyser HVL 0DTE
        if hvl_0dte:
            dist_hvl = (mid - hvl_0dte) / tick_size
            abs_dist_hvl = abs(dist_hvl)

            if abs_dist_hvl < 25:
                has_0dte = True
                triggers_0dte.append(
                    f"🎯 HVL 0DTE @ {hvl_0dte:.2f} ({dist_hvl:+.0f}t) - PIVOT INTRADAY"
                )
                # 📚 Monitoring 0DTE usage
                self.stats['0dte_hvl_used'] += 1
                logger.info(f"   📊 HVL 0DTE @ {hvl_0dte:.2f} ({dist_hvl:+.0f}t)")
                logger.info(f"      → Pivot régime INTRADAY (plus réactif que HVL All Exp)")

        # Analyser Gamma Wall 0DTE
        if gamma_wall_0dte:
            dist_gamma = (mid - gamma_wall_0dte) / tick_size
            abs_dist_gamma = abs(dist_gamma)

            if abs_dist_gamma < 25:
                has_0dte = True
                triggers_0dte.append(
                    f"🧱 GAMMA WALL 0DTE @ {gamma_wall_0dte:.2f} ({dist_gamma:+.0f}t) - MUR INTRADAY"
                )
                # 📚 Monitoring 0DTE usage
                self.stats['0dte_gamma_wall_used'] += 1
                logger.info(f"   📊 Gamma Wall 0DTE @ {gamma_wall_0dte:.2f} ({dist_gamma:+.0f}t)")
                logger.info(f"      → Mur gamma INTRADAY (pinning effect)")

        if has_0dte:
            # 📚 Incrémenter compteur global d'utilisation 0DTE
            self.stats['0dte_total_usage'] += 1
            logger.info("   ✅ Niveaux 0DTE actifs → Influence INTRADAY forte")

        logger.info("═" * 60)

        return has_0dte, triggers_0dte

    def _analyze_next_wall(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """Analyse next wall"""
        score = 0.0
        signal = None
        triggers = []
        symbol = snapshot.get('sym', 'NQ')[:2]

        next_wall = snapshot.get('next_wall', {})

        logger.debug(f"Next Wall Analysis:")  # ✅ Optimisé
        logger.info(f"   next_wall={next_wall}")

        if not next_wall:
            logger.info(f"   ❌ next_wall absent")
            return score, signal, triggers

        wall_side = next_wall.get('side', '')
        wall_dist = abs(next_wall.get('dist_ticks', 9999))
        wall_strength = next_wall.get('strength', 0)

        logger.info(f"   wall_side={wall_side}, wall_dist={wall_dist}t, wall_strength={wall_strength:.3f}")

        # Seuil adaptatif par symbole
        max_distance = self.config.NEXT_WALL_MAX_DISTANCE_TICKS.get(symbol, 100)
        min_strength = self.config.NEXT_WALL_MIN_STRENGTH

        # SIGNAL: Next wall proche et fort
        # ✅ LOGIQUE CONFIRMÉE PAR DOCUMENTATION OFFICIELLE MENTHORQ
        # Source: METHODE_MENTHORQ_ELITE.md lignes 93-149
        # PUT WALL = SUPPORT (prix rebondit UP) → LONG
        # CALL WALL = RESISTANCE (prix rebondit DOWN) → SHORT
        logger.info(f"   ✅ LOGIQUE MENTHORQ OFFICIELLE:")
        logger.info(f"      Put wall = Support → LONG (rebond UP)")
        logger.info(f"      Call wall = Resistance → SHORT (rebond DOWN)")

        if wall_dist < max_distance and wall_strength > min_strength:
            logger.info(f"   ✅ Conditions OK: dist={wall_dist} < {max_distance}, strength={wall_strength:.3f} > {min_strength}")
            if wall_side == 'put':
                signal = TradeSignal.LONG   # ✅ CORRIGÉ: Put wall = Support = LONG
                triggers.append(f"🟢 Put wall support ({wall_dist}t, str={wall_strength:.2f})")
                logger.info(f"   → SIGNAL=LONG (put wall = support, rebond UP)")
            elif wall_side == 'call':
                signal = TradeSignal.SHORT  # ✅ CORRIGÉ: Call wall = Resistance = SHORT
                triggers.append(f"🔴 Call wall resistance ({wall_dist}t, str={wall_strength:.2f})")
                logger.info(f"   → SIGNAL=SHORT (call wall = resistance, rebond DOWN)")

            # ═══════════════════════════════════════════════════════════
            # 🔥 PHASE 1 FIX: Utiliser distance_score si disponible
            # ═══════════════════════════════════════════════════════════

            if UNIFIED_THRESHOLDS_AVAILABLE:
                # Utiliser get_distance_score pour score basé sur distance
                distance_score = get_distance_score('next_wall', wall_dist)
                # Combiner avec force du wall
                base_score = distance_score * wall_strength
                # Appliquer poids 15% (au lieu de 8%)
                score = self.config.MENTHORQ_WEIGHTS['next_wall'] * base_score
                logger.info(f"   Score={score:.4f} (distance_score={distance_score:.2f}, strength={wall_strength:.3f}, weight={self.config.MENTHORQ_WEIGHTS['next_wall']:.2f})")
            else:
                # Fallback: ancien calcul
                score = self.config.MENTHORQ_WEIGHTS['next_wall'] * wall_strength
                logger.info(f"   Score={score:.4f} (fallback)")
        else:
            logger.info(f"   ❌ Conditions non remplies (dist={wall_dist}, max={max_distance}, str={wall_strength:.3f}, min={min_strength})")

        return score, signal, triggers

    def _analyze_daily_extremes(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        Analyse 1-Day Max/Min selon Bible MenthorQ v2.0

        🎯 PRINCIPE (Bible MenthorQ):
           - 1-Day Max = Résistance PSYCHOLOGIQUE forte (dernier plus haut de la journée)
           - 1-Day Min = Support PSYCHOLOGIQUE fort (dernier plus bas de la journée)
           - < 50 ticks = Niveau CRITIQUE (prudence extrême)
           - Market Makers utilisent ces niveaux comme références intraday

        📊 COMPORTEMENT:
           - Prix proche 1-Day Max → Risque de rejet DOWN (resistance)
           - Prix proche 1-Day Min → Risque de rejet UP (support)
           - Casser ces niveaux = breakout significatif (volume requis)

        ⚠️ UTILISATION:
           - Layer 1: Identification du niveau comme S/R
           - Layer 3: Contexte de PRUDENCE si trop proche
           - Exiger validation OrderFlow renforcée si < 30 ticks

        Args:
            snapshot: ML_READY data
            mid: Prix mid actuel
            tick_size: Taille du tick

        Returns:
            (score, signal, triggers)
        """
        score = 0.0
        signal = None
        triggers = []

        day_max = snapshot.get('day_max', 0) or snapshot.get('1d_max', 0)
        day_min = snapshot.get('day_min', 0) or snapshot.get('1d_min', 0)

        if not day_max or not day_min:
            return score, signal, triggers

        # Distances aux extrêmes
        dist_to_max_ticks = abs((day_max - mid) / tick_size)
        dist_to_min_ticks = abs((mid - day_min) / tick_size)

        # 🔍 DEBUG
        logger.info("=" * 60)
        logger.info("📊 DAILY EXTREMES ANALYSIS (Bible MenthorQ v2.0):")
        logger.info("=" * 60)
        logger.info(f"   1-Day Max @ {day_max:.2f}, Mid @ {mid:.2f}")
        logger.info(f"   Distance to Max: {dist_to_max_ticks:.0f} ticks")
        logger.info(f"   1-Day Min @ {day_min:.2f}")
        logger.info(f"   Distance to Min: {dist_to_min_ticks:.0f} ticks")

        # Seuils
        CRITICAL_DISTANCE = 30  # < 30 ticks = DANGER ABSOLU
        VERY_CLOSE = 50         # < 50 ticks = Niveau critique
        CLOSE = 100             # < 100 ticks = Influence notable

        # Analyser 1-Day MAX (resistance)
        if mid > day_max:
            # Prix AU-DESSUS du 1-Day Max → Breakout UP
            logger.info(f"   🟢 BREAKOUT: Prix au-dessus 1-Day Max (+{dist_to_max_ticks:.0f}t)")
            logger.info(f"      → Momentum BULLISH, continuation probable si volume OK")
            triggers.append(f"📈 Breakout 1-Day Max (+{dist_to_max_ticks:.0f}t)")
            # 🔥 FIX 12/12: Générer signal LONG pour suivre le breakout
            signal = TradeSignal.LONG
            score = 0.08  # 8% weight (breakout fort)
            logger.info(f"      → Signal LONG généré (breakout continuation)")
        elif dist_to_max_ticks < CRITICAL_DISTANCE:
            # TRÈS PROCHE du 1-Day Max
            logger.warning(f"   🚨 CRITIQUE: Prix TRÈS PROCHE 1-Day Max ({dist_to_max_ticks:.0f}t < {CRITICAL_DISTANCE}t)")
            logger.warning(f"      ⚠️ Résistance PSYCHOLOGIQUE forte")
            logger.warning(f"      → Exiger validation OrderFlow ABSOLUE !")
            signal = TradeSignal.SHORT
            score = 0.06  # 6% weight (fort)
            triggers.append(f"⚠️⚠️⚠️ 1-Day Max CRITIQUE ({dist_to_max_ticks:.0f}t)")
        elif dist_to_max_ticks < VERY_CLOSE:
            # PROCHE du 1-Day Max
            logger.warning(f"   ⚠️ Prix proche 1-Day Max ({dist_to_max_ticks:.0f}t < {VERY_CLOSE}t)")
            logger.warning(f"      → Resistance forte, prudence sur LONG")
            signal = TradeSignal.SHORT
            score = 0.04  # 4% weight (modéré)
            triggers.append(f"⚠️ 1-Day Max proche ({dist_to_max_ticks:.0f}t)")
        elif dist_to_max_ticks < CLOSE:
            # INFLUENCE du 1-Day Max
            logger.info(f"   ℹ️ Prix sous influence 1-Day Max ({dist_to_max_ticks:.0f}t < {CLOSE}t)")
            triggers.append(f"📊 1-Day Max influence ({dist_to_max_ticks:.0f}t)")
            score = 0.02  # 2% weight (faible)

        # Analyser 1-Day MIN (support)
        if mid < day_min:
            # Prix EN-DESSOUS du 1-Day Min → Breakout DOWN
            logger.info(f"   🔴 BREAKDOWN: Prix en-dessous 1-Day Min (-{dist_to_min_ticks:.0f}t)")
            logger.info(f"      → Momentum BEARISH, continuation probable si volume OK")
            triggers.append(f"📉 Breakdown 1-Day Min (-{dist_to_min_ticks:.0f}t)")
            # 🔥 FIX 12/12: Générer signal SHORT pour suivre le breakdown
            signal = TradeSignal.SHORT
            score = 0.08  # 8% weight (breakdown fort)
            logger.info(f"      → Signal SHORT généré (breakdown continuation)")
        elif dist_to_min_ticks < CRITICAL_DISTANCE:
            # TRÈS PROCHE du 1-Day Min
            logger.warning(f"   🚨 CRITIQUE: Prix TRÈS PROCHE 1-Day Min ({dist_to_min_ticks:.0f}t < {CRITICAL_DISTANCE}t)")
            logger.warning(f"      ⚠️ Support PSYCHOLOGIQUE fort")
            logger.warning(f"      → Exiger validation OrderFlow ABSOLUE !")
            # Si pas déjà de signal MAX, proposer LONG
            if not signal:
                signal = TradeSignal.LONG
                score = 0.06  # 6% weight (fort)
            triggers.append(f"⚠️⚠️⚠️ 1-Day Min CRITIQUE ({dist_to_min_ticks:.0f}t)")
        elif dist_to_min_ticks < VERY_CLOSE:
            # PROCHE du 1-Day Min
            logger.warning(f"   ⚠️ Prix proche 1-Day Min ({dist_to_min_ticks:.0f}t < {VERY_CLOSE}t)")
            logger.warning(f"      → Support fort, prudence sur SHORT")
            if not signal:
                signal = TradeSignal.LONG
                score = 0.04  # 4% weight (modéré)
            triggers.append(f"⚠️ 1-Day Min proche ({dist_to_min_ticks:.0f}t)")
        elif dist_to_min_ticks < CLOSE:
            # INFLUENCE du 1-Day Min
            logger.info(f"   ℹ️ Prix sous influence 1-Day Min ({dist_to_min_ticks:.0f}t < {CLOSE}t)")
            triggers.append(f"📊 1-Day Min influence ({dist_to_min_ticks:.0f}t)")
            if not signal and score == 0:
                score = 0.02  # 2% weight (faible)

        logger.info("=" * 60)

        return score, signal, triggers

    # ═══════════════════════════════════════════════════════════════════════
    # 🆕 12/12/2025: NOUVEAUX NIVEAUX VWAP & VOLUME PROFILE
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_vwap_entries(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        🆕 Analyse VWAP Daily, Weekly et Prior VWAP comme niveaux d'ENTRY

        📊 DONNÉES RÉELLES (analyse 12/12/2025):
           - VWAP Daily: 33.7% du temps < 10 ticks (ES) → TRÈS PERTINENT
           - VWAP Weekly: 32.5% du temps < 10 ticks (ES) → TRÈS PERTINENT
           - Prior VWAP: 16% du temps < 10 ticks (ES) → PERTINENT

        🎯 LOGIQUE:
           - Prix PROCHE du VWAP → Opportunité MEAN REVERSION
           - Prix AU-DESSUS du VWAP → Bias LONG
           - Prix EN-DESSOUS du VWAP → Bias SHORT

        Args:
            snapshot: ML_READY data
            mid: Prix mid actuel
            tick_size: Taille du tick

        Returns:
            (score, signal, triggers)
        """
        symbol = snapshot.get('sym', 'NQ')[:2]
        score = 0.0
        signal = None
        triggers = []

        logger.info("=" * 60)
        logger.info("🆕 ANALYSE VWAP ENTRIES")
        logger.info("=" * 60)

        # === 1. VWAP DAILY ===
        vwap_daily = snapshot.get('vwap')
        if vwap_daily and vwap_daily > 0:
            dist_ticks = abs(mid - vwap_daily) / tick_size
            max_dist = self.config.VWAP_ENTRY_MAX_DISTANCE_TICKS.get(symbol, 15)

            logger.info(f"   📍 VWAP Daily: {vwap_daily} | Distance: {dist_ticks:.1f}t (max: {max_dist}t)")

            if dist_ticks <= max_dist:
                # Prix proche du VWAP → Signal d'entry potentiel
                proximity_factor = 1 - (dist_ticks / max_dist)
                vwap_score = self.config.VWAP_ENTRY_WEIGHT * proximity_factor
                score += vwap_score

                # Déterminer direction
                if mid < vwap_daily:
                    # Prix sous VWAP → Favorise LONG (mean reversion)
                    signal = TradeSignal.LONG
                    triggers.append(f"📈 VWAP Daily: LONG favori (prix sous VWAP, {dist_ticks:.0f}t)")
                else:
                    # Prix au-dessus VWAP → Favorise SHORT (mean reversion)
                    signal = TradeSignal.SHORT
                    triggers.append(f"📉 VWAP Daily: SHORT favori (prix sur VWAP, {dist_ticks:.0f}t)")

                logger.info(f"   ✅ VWAP Daily ENTRY: {signal.value if signal else 'N/A'} | Score: +{vwap_score:.4f}")

        # === 2. VWAP WEEKLY ===
        vwap_weekly = snapshot.get('vwap_weekly')
        if vwap_weekly and vwap_weekly > 0:
            dist_ticks = abs(mid - vwap_weekly) / tick_size
            max_dist = self.config.VWAP_WEEKLY_MAX_DISTANCE_TICKS.get(symbol, 20)

            logger.info(f"   📍 VWAP Weekly: {vwap_weekly} | Distance: {dist_ticks:.1f}t (max: {max_dist}t)")

            if dist_ticks <= max_dist:
                proximity_factor = 1 - (dist_ticks / max_dist)
                weekly_score = self.config.VWAP_WEEKLY_WEIGHT * proximity_factor
                score += weekly_score

                if mid < vwap_weekly:
                    weekly_signal = TradeSignal.LONG
                    triggers.append(f"📈 VWAP Weekly: LONG ({dist_ticks:.0f}t)")
                else:
                    weekly_signal = TradeSignal.SHORT
                    triggers.append(f"📉 VWAP Weekly: SHORT ({dist_ticks:.0f}t)")

                # Le signal weekly ne remplace que si pas déjà défini
                if signal is None:
                    signal = weekly_signal

                logger.info(f"   ✅ VWAP Weekly ENTRY: {weekly_signal.value} | Score: +{weekly_score:.4f}")

        # === 3. PRIOR VWAP (pvwap) ===
        pvwap = snapshot.get('pvwap')
        if pvwap and pvwap > 0:
            dist_ticks = abs(mid - pvwap) / tick_size
            max_dist = self.config.PVWAP_MAX_DISTANCE_TICKS.get(symbol, 15)

            logger.info(f"   📍 Prior VWAP: {pvwap} | Distance: {dist_ticks:.1f}t (max: {max_dist}t)")

            if dist_ticks <= max_dist:
                proximity_factor = 1 - (dist_ticks / max_dist)
                pvwap_score = self.config.PVWAP_WEIGHT * proximity_factor
                score += pvwap_score

                if mid < pvwap:
                    pvwap_signal = TradeSignal.LONG
                    triggers.append(f"📈 Prior VWAP: LONG ({dist_ticks:.0f}t)")
                else:
                    pvwap_signal = TradeSignal.SHORT
                    triggers.append(f"📉 Prior VWAP: SHORT ({dist_ticks:.0f}t)")

                if signal is None:
                    signal = pvwap_signal

                logger.info(f"   ✅ Prior VWAP ENTRY: {pvwap_signal.value} | Score: +{pvwap_score:.4f}")

        logger.info(f"   📊 TOTAL VWAP ENTRIES: Score={score:.4f} | Signal={signal.value if signal else 'None'}")
        logger.info("=" * 60)

        return score, signal, triggers

    def _analyze_vwap_bands(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        🆕 Analyse VWAP Bands (±1σ, ±2σ) comme niveaux d'ENTRY

        📊 DONNÉES RÉELLES (analyse 12/12/2025):
           - VWAP +1σ: 27% tight (ES), 11% (NQ)
           - VWAP -1σ: 18% tight (ES), 11% (NQ)

        🎯 LOGIQUE:
           - Prix à VWAP +1σ → Possible résistance → SHORT si rejet
           - Prix à VWAP -1σ → Possible support → LONG si rejet
           - Les bands agissent comme des niveaux de REVERSION

        Args:
            snapshot: ML_READY data
            mid: Prix mid actuel
            tick_size: Taille du tick

        Returns:
            (score, signal, triggers)
        """
        symbol = snapshot.get('sym', 'NQ')[:2]
        score = 0.0
        signal = None
        triggers = []

        logger.debug("   🔸 Analyse VWAP Bands...")

        max_dist = self.config.VWAP_BAND_MAX_DISTANCE_TICKS.get(symbol, 15)

        # VWAP Upper Band (+1σ)
        vwap_up1 = snapshot.get('vwap_up1')
        if vwap_up1 and vwap_up1 > 0:
            dist_ticks = abs(mid - vwap_up1) / tick_size
            if dist_ticks <= max_dist:
                proximity_factor = 1 - (dist_ticks / max_dist)
                band_score = self.config.VWAP_BAND_WEIGHT * proximity_factor * 0.5
                score += band_score
                # Prix proche de +1σ → Résistance potentielle → SHORT
                signal = TradeSignal.SHORT
                triggers.append(f"📉 VWAP +1σ: SHORT potentiel ({dist_ticks:.0f}t)")
                logger.info(f"   ✅ VWAP +1σ ENTRY: SHORT | Score: +{band_score:.4f}")

        # VWAP Lower Band (-1σ)
        vwap_dn1 = snapshot.get('vwap_dn1')
        if vwap_dn1 and vwap_dn1 > 0:
            dist_ticks = abs(mid - vwap_dn1) / tick_size
            if dist_ticks <= max_dist:
                proximity_factor = 1 - (dist_ticks / max_dist)
                band_score = self.config.VWAP_BAND_WEIGHT * proximity_factor * 0.5
                score += band_score
                # Prix proche de -1σ → Support potentiel → LONG
                band_signal = TradeSignal.LONG
                triggers.append(f"📈 VWAP -1σ: LONG potentiel ({dist_ticks:.0f}t)")
                logger.info(f"   ✅ VWAP -1σ ENTRY: LONG | Score: +{band_score:.4f}")
                if signal is None:
                    signal = band_signal

        # VWAP Upper Band +2σ (Weekly)
        vwap_up2 = snapshot.get('vwap_weekly_up1')  # Weekly +1σ
        if vwap_up2 and vwap_up2 > 0:
            dist_ticks = abs(mid - vwap_up2) / tick_size
            if dist_ticks <= max_dist * 1.5:  # Distance plus large pour weekly
                proximity_factor = 1 - (dist_ticks / (max_dist * 1.5))
                band_score = self.config.VWAP_BAND_WEIGHT * proximity_factor * 0.3
                score += band_score
                triggers.append(f"📉 Weekly +1σ proche ({dist_ticks:.0f}t)")

        # VWAP Lower Band -2σ (Weekly)
        vwap_dn2 = snapshot.get('vwap_weekly_dn1')  # Weekly -1σ
        if vwap_dn2 and vwap_dn2 > 0:
            dist_ticks = abs(mid - vwap_dn2) / tick_size
            if dist_ticks <= max_dist * 1.5:
                proximity_factor = 1 - (dist_ticks / (max_dist * 1.5))
                band_score = self.config.VWAP_BAND_WEIGHT * proximity_factor * 0.3
                score += band_score
                triggers.append(f"📈 Weekly -1σ proche ({dist_ticks:.0f}t)")

        return score, signal, triggers

    def _analyze_volume_profile(self, snapshot: Dict, mid: float, tick_size: float) -> Tuple[float, Optional[TradeSignal], List[str]]:
        """
        🆕 Analyse Volume Profile (POC, VAH, VAL) comme niveaux d'ENTRY

        📊 DONNÉES RÉELLES (analyse 12/12/2025):
           - POC: 5.4% tight (ES), 3.4% (NQ)
           - VAH: 5.2% tight (ES seulement)
           - VAL: Moins pertinent

        🎯 LOGIQUE:
           - POC = Point of Control = Zone de VALEUR maximale
           - VAH = Value Area High = Résistance volume
           - VAL = Value Area Low = Support volume
           - Prix proche de ces niveaux → Haute liquidité → Bon entry

        Args:
            snapshot: ML_READY data
            mid: Prix mid actuel
            tick_size: Taille du tick

        Returns:
            (score, signal, triggers)
        """
        symbol = snapshot.get('sym', 'NQ')[:2]
        score = 0.0
        signal = None
        triggers = []

        logger.debug("   🔸 Analyse Volume Profile...")

        # Récupérer vva (Visible Value Area)
        vva = snapshot.get('vva', {})

        # === POC (Point of Control) ===
        vpoc = vva.get('vpoc') if isinstance(vva, dict) else None
        if vpoc and vpoc > 0:
            dist_ticks = abs(mid - vpoc) / tick_size
            max_dist = self.config.POC_MAX_DISTANCE_TICKS.get(symbol, 20)

            logger.info(f"   📍 POC: {vpoc} | Distance: {dist_ticks:.1f}t (max: {max_dist}t)")

            if dist_ticks <= max_dist:
                proximity_factor = 1 - (dist_ticks / max_dist)
                poc_score = self.config.POC_WEIGHT * proximity_factor
                score += poc_score

                # POC = zone de valeur → pas de direction claire, c'est plutôt un support/résistance
                # On prend la direction basée sur la position relative
                if mid < vpoc:
                    signal = TradeSignal.LONG  # Prix sous POC → favori LONG
                    triggers.append(f"📈 POC: LONG (prix sous POC, {dist_ticks:.0f}t)")
                else:
                    signal = TradeSignal.SHORT  # Prix sur POC → favori SHORT
                    triggers.append(f"📉 POC: SHORT (prix sur POC, {dist_ticks:.0f}t)")

                logger.info(f"   ✅ POC ENTRY: {signal.value} | Score: +{poc_score:.4f}")

        # === VAH (Value Area High) - ES/RTY SEULEMENT ===
        vah_max_dist = self.config.VAH_MAX_DISTANCE_TICKS.get(symbol)
        if vah_max_dist:  # None = désactivé pour ce symbole (ex: NQ)
            vah = vva.get('vah') if isinstance(vva, dict) else None
            if vah and vah > 0:
                dist_ticks = abs(mid - vah) / tick_size

                logger.info(f"   📍 VAH: {vah} | Distance: {dist_ticks:.1f}t (max: {vah_max_dist}t)")

                if dist_ticks <= vah_max_dist:
                    proximity_factor = 1 - (dist_ticks / vah_max_dist)
                    vah_score = self.config.VAH_WEIGHT * proximity_factor
                    score += vah_score

                    # VAH = Résistance volume → SHORT si prix au-dessus
                    if mid >= vah:
                        vah_signal = TradeSignal.SHORT
                        triggers.append(f"📉 VAH: SHORT (résistance volume, {dist_ticks:.0f}t)")
                    else:
                        vah_signal = TradeSignal.LONG
                        triggers.append(f"📈 VAH: LONG (support volume, {dist_ticks:.0f}t)")

                    if signal is None:
                        signal = vah_signal

                    logger.info(f"   ✅ VAH ENTRY: {vah_signal.value} | Score: +{vah_score:.4f}")

            # ⚠️ VAL DÉSACTIVÉ (12/12/2025): Score 0% - jamais proche du prix
            # Analyse montre que VAL est TOUJOURS trop loin pour être utile
            # Code conservé mais commenté pour référence future
            # === VAL (Value Area Low) - DÉSACTIVÉ ===
            # val = vva.get('val') if isinstance(vva, dict) else None
            # if val and val > 0:
            #     ... code VAL désactivé ...

        if score > 0:
            logger.info(f"   📊 TOTAL VOLUME PROFILE: Score={score:.4f} | Signal={signal.value if signal else 'None'}")

        return score, signal, triggers

    def _analyze_menthorq_scores(self, snapshot: Dict) -> Tuple[float, List[str]]:
        """Analyse MenthorQ scores"""
        score = 0.0
        triggers = []

        impact = snapshot.get('menthorq_impact_score', 0)
        proximity = snapshot.get('menthorq_proximity_strength', 0)

        # 🔧 AJUSTEMENT ES: Seuils plus permissifs (était 0.05 et 0.10)
        if impact > 0.03 or proximity > 0.06:
            avg_score = (impact + proximity) / 2
            score = self.config.MENTHORQ_WEIGHTS['scores'] * avg_score * 10  # Normalisation
            triggers.append(f"📊 MenthorQ scores: impact={impact:.3f}, prox={proximity:.3f}")

        return score, triggers

    # ═══════════════════════════════════════════════════════════════════
    # LAYER 2: OrderFlow (Validateur)
    # ═══════════════════════════════════════════════════════════════════

    def validate_layer2_orderflow(self, snapshot: Dict, menthorq_signal: TradeSignal) -> Layer2Result:
        """
        LAYER 2: OrderFlow VALIDE la direction identifiée par Layer 1

        ⚠️ RÔLE: FILTRE #1 - Confirme que le flow va dans la même direction

        Logique:
            - Si Layer 1 dit "GEX resistance @ 35t = SHORT potentiel"
            - Layer 2 vérifie: "Le flow confirme-t-il SHORT ?"
                → Cum Delta négatif ? (ventes)
                → Ask Volume dominant ? (ventes)
                → DOM Imbalance négatif ? (pression vendeuse)
                → Institutional Pressure négatif ? (institutionnels vendent)
            - Si OUI → validated=True (on passe à Layer 3)
            - Si NON → validated=False (REJET, pas de trade)

        Analyse:
            - Delta (cum_delta_session, delta, smart_money_flow)
            - Volume profile (askPct, bidPct)
            - DOM imbalance (level1_imbalance)
            - Institutional pressure
            - Battle Navale

        Returns:
            Layer2Result avec validation (True/False) et confidence
            → True = Flow CONFIRME la direction du Layer 1
            → False = Flow CONTREDIT le Layer 1 → REJET
        """
        orderflow_score = 0.0
        validations = []
        metrics = {}

        # ═══════════════════════════════════════════════════════════════════
        # 🔥 NOUVELLE RÈGLE 05/12/2025: ORDERFLOW ALIGNMENT CHECK
        # ═══════════════════════════════════════════════════════════════════
        # Découverte: Les trades perdants avaient l'OrderFlow CONTRE eux!
        # - Pour SHORT: depth_imb positif, delta positif, ob_center positif
        # - Pour LONG: depth_imb négatif, delta négatif, ob_center négatif
        #
        # RÈGLE: Bloquer si 2+ indicateurs OrderFlow sont contre la direction
        # ═══════════════════════════════════════════════════════════════════

        is_aligned, alignment_reason, counter_count = self._check_orderflow_alignment(
            snapshot, menthorq_signal
        )

        # 🔧 13/12: DÉSACTIVÉ - Ce filtre bloquait 237 trades!
        # Le seuil était trop strict (ratio 3:1 suffisait à bloquer)
        # TODO: Réactiver avec seuil plus permissif (ratio > 10:1)
        # if not is_aligned:
        #     # OrderFlow CONTRE la direction → REJET IMMÉDIAT
        #     logger.warning(f"🚨 ORDERFLOW ALIGNMENT BLOCK: {alignment_reason}")
        #     return Layer2Result(
        #         validated=False,
        #         confidence=0.0,
        #         reason=f"❌ OrderFlow contre direction: {alignment_reason}",
        #         validations=[f"❌ BLOQUÉ: {counter_count} indicateurs OrderFlow contre {menthorq_signal.value}"],
        #         metrics={'orderflow_aligned': False, 'counter_signals': counter_count}
        #     )
        # else:
        #     validations.append(f"✅ OrderFlow aligné avec {menthorq_signal.value}")
        #     metrics['orderflow_aligned'] = True

        # Log informatif seulement (pas de blocage)
        if not is_aligned:
            logger.info(f"⚠️ OrderFlow pas aligné: {alignment_reason} (non bloquant)")
        validations.append(f"ℹ️ OrderFlow check: aligned={is_aligned}")
        metrics['orderflow_aligned'] = is_aligned

        # === 1. DELTA ANALYSIS (12% weight) ===
        delta_validates, delta_score, delta_msgs = self._analyze_delta(
            snapshot, menthorq_signal
        )
        orderflow_score += delta_score
        validations.extend(delta_msgs)
        metrics['delta_validates'] = delta_validates

        # === 2. VOLUME PROFILE (6% weight) ===
        volume_validates, volume_score, volume_msgs = self._analyze_volume(
            snapshot, menthorq_signal
        )
        orderflow_score += volume_score
        validations.extend(volume_msgs)
        metrics['volume_validates'] = volume_validates

        # === 3. DOM IMBALANCE (6% weight) ===
        dom_validates, dom_score, dom_msgs = self._analyze_dom(
            snapshot, menthorq_signal
        )
        orderflow_score += dom_score
        validations.extend(dom_msgs)
        metrics['dom_validates'] = dom_validates

        # === 4. INSTITUTIONAL PRESSURE (4% weight) ===
        pressure_score, pressure_msgs = self._analyze_pressure(
            snapshot, menthorq_signal
        )
        orderflow_score += pressure_score
        validations.extend(pressure_msgs)

        # === 5. BATTLE NAVALE (2% weight) ===
        bn_score, bn_msgs = self._analyze_battle_navale(snapshot)
        orderflow_score += bn_score
        validations.extend(bn_msgs)

        # === DÉCISION FINALE LAYER 2 ===
        # 🔧 MODIFICATION 2025-11-13: Assouplir Layer 2
        #    Problème: Rejette trop (ex: LONG @ 0.17 avec Blind Spot rejected)
        #    Solution: Accepter même sans delta/volume si DOM/pressure/BN confirment

        # Validation si AU MOINS 1 validation (delta, volume, ou DOM)
        validated = delta_validates or volume_validates or dom_validates

        # 🔧 NOUVEAU: Si aucune validation mais confidence Layer 1 > 0.15
        #    ET que le flow n'est pas FORTEMENT contraire → accepter quand même
        if not validated:
            # Vérifier si le flow n'est pas trop contraire
            delta = snapshot.get('delta', 0)
            bid_pct = snapshot.get('bidPct', 0.5)
            ask_pct = snapshot.get('askPct', 0.5)

            # Pour LONG: Accepter si delta >= -100 OU bid >= 45%
            if menthorq_signal == TradeSignal.LONG:
                if delta >= -100 or bid_pct >= 0.45:
                    validated = True
                    # ✅ FIX 21/11 06:10: Donner un score minimal pour fallback
                    orderflow_score = max(orderflow_score, 0.08)  # 8% minimum
                    validations.append(f"⚠️ Layer 2: Flow neutre → Accepté (delta={delta}, bid={bid_pct:.1%})")
            # Pour SHORT: Accepter si delta <= 100 OU ask >= 45%
            elif menthorq_signal == TradeSignal.SHORT:
                if delta <= 100 or ask_pct >= 0.45:
                    validated = True
                    # ✅ FIX 21/11 06:10: Donner un score minimal pour fallback
                    orderflow_score = max(orderflow_score, 0.08)  # 8% minimum
                    validations.append(f"⚠️ Layer 2: Flow neutre → Accepté (delta={delta}, ask={ask_pct:.1%})")

        passed = len([v for v in validations if '✅' in v])
        total = len(validations)
        reason = f"OrderFlow: {passed}/{total} checks passed"

        # ✅ FIX 21/11 05:15: Normaliser orderflow_score (clamp à 1.0)
        orderflow_score = min(orderflow_score, 1.0)

        return Layer2Result(
            validated=validated,
            confidence=orderflow_score,
            reason=reason,
            validations=validations,
            metrics=metrics
        )

    def _check_orderflow_alignment(self, snapshot: Dict, signal: TradeSignal) -> Tuple[bool, str, int]:
        """
        🔥 RÈGLE PONDÉRÉE 05/12/2025: Vérifie alignement OrderFlow avec direction

        Découverte basée sur analyse des trades perdants du 05/12/2025:
        - Les trades gagnants avaient OrderFlow ALIGNÉ avec direction
        - Les trades perdants avaient OrderFlow CONTRE la direction

        AMÉLIORATION 05/12 SOIR: Logique PONDÉRÉE au lieu de binaire
        - Évite de bloquer des trades gagnants avec signaux mixtes
        - Le trade +$937 du 04/12 avait tick_mom=-0.833 (fort vendeur)
          mais depth_imb=+0.22 et ob_center=+1.29 (acheteurs faibles)
        - La pondération permet de capturer l'INTENSITÉ des signaux

        RÈGLE: Calculer score acheteur vs vendeur, bloquer si ratio > 1.5

        Returns:
            Tuple[is_aligned, reason, counter_count]
        """
        depth_imb = snapshot.get('depth_imbalance', 0)
        delta = snapshot.get('delta', 0)
        ob_center = snapshot.get('ob_center', 0)
        tick_mom = snapshot.get('tick_momentum', 0)

        # Facteurs de normalisation (basés sur l'analyse des trades)
        DEPTH_NORM = 0.20   # depth_imbalance typique: -0.3 à +0.3
        DELTA_NORM = 100    # delta typique: -200 à +200
        OB_NORM = 0.50      # ob_center typique: -1 à +1
        TICK_NORM = 0.50    # tick_momentum typique: -1 à +1

        # Seuil de ratio pour bloquer (testé sur données réelles)
        BLOCK_RATIO = 1.5

        if signal == TradeSignal.SHORT:
            # Pour SHORT: on veut pression VENDEUSE (valeurs négatives)

            # Score acheteur (CONTRE le SHORT)
            buyer_score = (
                max(0, depth_imb) / DEPTH_NORM +
                max(0, delta) / DELTA_NORM +
                max(0, ob_center) / OB_NORM +
                max(0, tick_mom) / TICK_NORM
            )

            # Score vendeur (POUR le SHORT)
            seller_score = (
                abs(min(0, depth_imb)) / DEPTH_NORM +
                abs(min(0, delta)) / DELTA_NORM +
                abs(min(0, ob_center)) / OB_NORM +
                abs(min(0, tick_mom)) / TICK_NORM
            )

            # Calculer ratio
            ratio = buyer_score / max(seller_score, 0.01)

            # BLOQUER seulement si score acheteur >> score vendeur
            if ratio > BLOCK_RATIO:
                return False, f"SHORT bloqué: buyer={buyer_score:.2f} >> seller={seller_score:.2f} (ratio={ratio:.1f})", int(ratio)

            return True, f"OrderFlow OK pour SHORT (buyer={buyer_score:.2f}, seller={seller_score:.2f}, ratio={ratio:.2f})", 0

        elif signal == TradeSignal.LONG:
            # Pour LONG: on veut pression ACHETEUSE (valeurs positives)

            # Score vendeur (CONTRE le LONG)
            seller_score = (
                abs(min(0, depth_imb)) / DEPTH_NORM +
                abs(min(0, delta)) / DELTA_NORM +
                abs(min(0, ob_center)) / OB_NORM +
                abs(min(0, tick_mom)) / TICK_NORM
            )

            # Score acheteur (POUR le LONG)
            buyer_score = (
                max(0, depth_imb) / DEPTH_NORM +
                max(0, delta) / DELTA_NORM +
                max(0, ob_center) / OB_NORM +
                max(0, tick_mom) / TICK_NORM
            )

            # Calculer ratio
            ratio = seller_score / max(buyer_score, 0.01)

            # BLOQUER seulement si score vendeur >> score acheteur
            if ratio > BLOCK_RATIO:
                return False, f"LONG bloqué: seller={seller_score:.2f} >> buyer={buyer_score:.2f} (ratio={ratio:.1f})", int(ratio)

            return True, f"OrderFlow OK pour LONG (seller={seller_score:.2f}, buyer={buyer_score:.2f}, ratio={ratio:.2f})", 0

        # Signal non reconnu → laisser passer
        return True, "Signal non reconnu", 0

    def _analyze_delta(self, snapshot: Dict, signal: TradeSignal) -> Tuple[bool, float, List[str]]:
        """
        Analyse delta

        🔥 PHASE 1 FIX: Validation assouplie - tolère delta légèrement opposé si près d'un niveau
        """
        validates = False
        score = 0.0
        msgs = []

        cum_delta = snapshot.get('cum_delta_session', 0)
        delta = snapshot.get('delta', 0)
        smart_money = snapshot.get('smart_money_flow', 0)
        level1_imbalance = snapshot.get('level1_imbalance', 0)

        # Calculer distance au niveau le plus proche
        next_wall = snapshot.get('next_wall', {})
        distance_to_level = abs(next_wall.get('dist_ticks', 999)) if next_wall else 999

        # ═══════════════════════════════════════════════════════════
        # 🔥 PHASE 1 FIX: Utiliser is_orderflow_valid si disponible
        # ═══════════════════════════════════════════════════════════

        if UNIFIED_THRESHOLDS_AVAILABLE:
            signal_side = "LONG" if signal == TradeSignal.LONG else "SHORT"
            delta_ok = is_orderflow_valid(signal_side, delta, level1_imbalance, distance_to_level)

            if delta_ok:
                validates = True
                # Score selon force de la confirmation
                if signal == TradeSignal.LONG:
                    if delta > ORDERFLOW_VALIDATION['delta']['strong_confirmation']:
                        score = self.config.ORDERFLOW_WEIGHTS['delta']
                        msgs.append(f"✅ Delta confirms LONG (delta={delta:.1f}, strong)")
                    elif delta > ORDERFLOW_VALIDATION['delta']['weak_confirmation']:
                        score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.8
                        msgs.append(f"✅ Delta confirms LONG (delta={delta:.1f}, weak)")
                    else:
                        # Delta opposé mais toléré (près niveau)
                        score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.6
                        msgs.append(f"⚠️ Delta opposé toléré LONG (delta={delta:.1f}, dist={distance_to_level:.0f}t, imb={level1_imbalance:.2f})")
                else:  # SHORT
                    if delta < -ORDERFLOW_VALIDATION['delta']['strong_confirmation']:
                        score = self.config.ORDERFLOW_WEIGHTS['delta']
                        msgs.append(f"✅ Delta confirms SHORT (delta={delta:.1f}, strong)")
                    elif delta < -ORDERFLOW_VALIDATION['delta']['weak_confirmation']:
                        score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.8
                        msgs.append(f"✅ Delta confirms SHORT (delta={delta:.1f}, weak)")
                    else:
                        score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.6
                        msgs.append(f"⚠️ Delta opposé toléré SHORT (delta={delta:.1f}, dist={distance_to_level:.0f}t, imb={level1_imbalance:.2f})")
            else:
                # Vérifier smart_money comme fallback
                if signal == TradeSignal.LONG and smart_money > 0.20:
                    validates = True
                    score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.7
                    msgs.append(f"⚠️ Smart money confirms LONG ({smart_money:.2f})")
                elif signal == TradeSignal.SHORT and smart_money < -0.20:
                    validates = True
                    score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.7
                    msgs.append(f"⚠️ Smart money confirms SHORT ({smart_money:.2f})")
                else:
                    msgs.append(f"❌ Delta rejects {signal.value} (delta={delta:.1f}, dist={distance_to_level:.0f}t)")
        else:
            # Fallback: logique originale
            if signal == TradeSignal.LONG:
                # Pour LONG: besoin delta positif
                if cum_delta > self.config.DELTA_MIN_CUMULATIVE and delta > 0:
                    validates = True
                    score = self.config.ORDERFLOW_WEIGHTS['delta']
                    msgs.append(f"✅ Delta confirms LONG (cumul={cum_delta}, delta={delta})")
                elif smart_money > 0.20:
                    validates = True
                    score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.7
                    msgs.append(f"⚠️ Smart money confirms LONG ({smart_money:.2f})")
                else:
                    msgs.append(f"❌ Delta rejects LONG (cumul={cum_delta}, delta={delta})")

            elif signal == TradeSignal.SHORT:
                # Pour SHORT: besoin delta négatif
                if cum_delta < -self.config.DELTA_MIN_CUMULATIVE and delta < 0:
                    validates = True
                    score = self.config.ORDERFLOW_WEIGHTS['delta']
                    msgs.append(f"✅ Delta confirms SHORT (cumul={cum_delta}, delta={delta})")
                elif smart_money < -0.20:
                    validates = True
                    score = self.config.ORDERFLOW_WEIGHTS['delta'] * 0.7
                    msgs.append(f"⚠️ Smart money confirms SHORT ({smart_money:.2f})")
                else:
                    msgs.append(f"❌ Delta rejects SHORT (cumul={cum_delta}, delta={delta})")

        return validates, score, msgs

    def _analyze_volume(self, snapshot: Dict, signal: TradeSignal) -> Tuple[bool, float, List[str]]:
        """Analyse volume profile"""
        validates = False
        score = 0.0
        msgs = []

        ask_pct = snapshot.get('askPct', 0.5)
        bid_pct = snapshot.get('bidPct', 0.5)

        if signal == TradeSignal.LONG:
            # Pour LONG: besoin plus de volume BID
            if bid_pct > self.config.VOLUME_MIN_PERCENTAGE:
                validates = True
                score = self.config.ORDERFLOW_WEIGHTS['volume']
                msgs.append(f"✅ Volume confirms LONG (bid={bid_pct:.1%})")
            else:
                msgs.append(f"❌ Volume rejects LONG (bid={bid_pct:.1%}, ask={ask_pct:.1%})")

        elif signal == TradeSignal.SHORT:
            # Pour SHORT: besoin plus de volume ASK
            if ask_pct > self.config.VOLUME_MIN_PERCENTAGE:
                validates = True
                score = self.config.ORDERFLOW_WEIGHTS['volume']
                msgs.append(f"✅ Volume confirms SHORT (ask={ask_pct:.1%})")
            else:
                msgs.append(f"❌ Volume rejects SHORT (ask={ask_pct:.1%}, bid={bid_pct:.1%})")

        return validates, score, msgs

    def _analyze_dom(self, snapshot: Dict, signal: TradeSignal) -> Tuple[bool, float, List[str]]:
        """Analyse DOM imbalance"""
        validates = False
        score = 0.0
        msgs = []

        level1_imb = snapshot.get('level1_imbalance', 0)

        if signal == TradeSignal.LONG:
            # Pour LONG: besoin imbalance positive
            if level1_imb > self.config.DOM_MIN_IMBALANCE:
                validates = True
                score = self.config.ORDERFLOW_WEIGHTS['dom']
                msgs.append(f"✅ DOM confirms LONG (imb={level1_imb:.2f})")
            else:
                msgs.append(f"⚠️ DOM neutral/negative pour LONG (imb={level1_imb:.2f})")

        elif signal == TradeSignal.SHORT:
            # Pour SHORT: besoin imbalance négative
            if level1_imb < -self.config.DOM_MIN_IMBALANCE:
                validates = True
                score = self.config.ORDERFLOW_WEIGHTS['dom']
                msgs.append(f"✅ DOM confirms SHORT (imb={level1_imb:.2f})")
            else:
                msgs.append(f"⚠️ DOM neutral/positive pour SHORT (imb={level1_imb:.2f})")

        return validates, score, msgs

    def _analyze_pressure(self, snapshot: Dict, signal: TradeSignal) -> Tuple[float, List[str]]:
        """Analyse institutional pressure"""
        score = 0.0
        msgs = []

        inst_pressure = snapshot.get('institutional_pressure', 0)

        if signal == TradeSignal.LONG and inst_pressure > self.config.INSTITUTIONAL_MIN_PRESSURE:
            score = self.config.ORDERFLOW_WEIGHTS['pressure']
            msgs.append(f"✅ Institutional pressure confirms LONG ({inst_pressure:.2f})")
        elif signal == TradeSignal.SHORT and inst_pressure < -self.config.INSTITUTIONAL_MIN_PRESSURE:
            score = self.config.ORDERFLOW_WEIGHTS['pressure']
            msgs.append(f"✅ Institutional pressure confirms SHORT ({inst_pressure:.2f})")

        return score, msgs

    def _analyze_battle_navale(self, snapshot: Dict) -> Tuple[float, List[str]]:
        """Analyse Battle Navale"""
        score = 0.0
        msgs = []

        bn_strength = snapshot.get('battle_navale_signal_strength', 0)

        if bn_strength > 0.05:
            score = self.config.ORDERFLOW_WEIGHTS['battle_navale']
            msgs.append(f"✅ Battle Navale signal ({bn_strength:.3f})")

        return score, msgs

    # ═══════════════════════════════════════════════════════════════════
    # LAYER 3: Context (Filtre Contextuel)
    # ═══════════════════════════════════════════════════════════════════

    def validate_layer3_context(self, snapshot: Dict, menthorq_signal: TradeSignal, layer1_confidence: float = 0.0, layer2_confidence: float = 0.0) -> Layer3Result:
        """
        LAYER 3: Contexte CONFIRME que les conditions de marché sont favorables

        ⚠️ RÔLE: FILTRE #2 - Vérifie que le timing et le contexte sont bons

        Logique:
            - Si Layer 1 dit "SHORT potentiel" ET Layer 2 confirme "Flow SHORT"
            - Layer 3 vérifie: "Est-ce le bon moment pour trader ?"
                → Prix loin de VWAP ? (éviter zones volatiles)
                → Position dans la Value Area ? (liquidité suffisante)
                → Market Structure favorable ? (tendance alignée)
                → Volatility normale ? (conditions stables)
            - Si OUI → favorable=True (TRADE VALIDÉ ✅)
            - Si NON → favorable=False (REJET, attendre meilleur setup)

        Analyse:
            - VWAP distances (d_vwap, d_vwap_atr)
            - Value Area (in_value_area, position_in_range)
            - Market structure (onh, onl, ibh, ibl)
            - Volatility (atr, volatility_regime)

        Returns:
            Layer3Result avec favorable (True/False) et confidence
            → True = Contexte FAVORABLE, timing OK → TRADE !
            → False = Contexte DÉFAVORABLE → ATTENDRE
        """
        context_score = 0.0
        warnings = []

        # === 1. VWAP CONTEXT (8% weight) ===
        vwap_favorable, vwap_score, vwap_msgs = self._analyze_vwap_context(snapshot)
        context_score += vwap_score
        warnings.extend(vwap_msgs)

        # === 2. VALUE AREA (6% weight) ===
        va_score, va_msgs = self._analyze_value_area(snapshot, menthorq_signal)
        context_score += va_score
        warnings.extend(va_msgs)

        # === 3. MARKET STRUCTURE (4% weight) ===
        struct_score, struct_msgs = self._analyze_structure(snapshot, menthorq_signal)
        context_score += struct_score
        warnings.extend(struct_msgs)

        # === 4. VOLATILITY (2% weight) ===
        vol_score, vol_msgs = self._analyze_volatility(snapshot)
        context_score += vol_score
        warnings.extend(vol_msgs)

        # === 5. HVL REGIME CONTEXT - NOUVEAU (Bible MenthorQ v2.0) ===
        hvl_regime = snapshot.get('_hvl_regime')
        if hvl_regime:
            logger.info("═" * 60)
            logger.info("📊 LAYER 3: HVL REGIME CONTEXTE (Bible MenthorQ v2.0)")
            logger.info(f"   Régime détecté: {hvl_regime.upper()}")

            if hvl_regime == 'positive_gamma':
                logger.info("   → Régime MEAN-REVERT: Favorise rebounds/rejections")
                logger.info("   → Dealers stabilisent le marché")
                warnings.append("💡 Régime Positive Gamma (mean-revert favorisé)")
            else:  # negative_gamma
                logger.info("   → Régime DIRECTIONNEL: Favorise breakouts/trends")
                logger.info("   → Dealers amplifient les mouvements")
                warnings.append("💡 Régime Negative Gamma (directionnel favorisé)")
            logger.info("═" * 60)

        # === 6. 1-DAY MAX/MIN WARNING - NOUVEAU (Bible MenthorQ v2.0) ===
        # 🔧 CORRECTION: Utiliser '1d_max' au lieu de '1day_max' (aligné avec extracteur C++)
        day_max = snapshot.get('1d_max', 0)
        day_min = snapshot.get('1d_min', 0)
        mid = snapshot.get('mid', 0)

        if day_max and day_min and mid:
            day_range = day_max - day_min
            if day_range > 0:
                # Position dans le range journalier (0-100%)
                position_pct = ((mid - day_min) / day_range) * 100

                logger.info("═" * 60)
                logger.info("📈 LAYER 3: 1-DAY MAX/MIN CONTEXTE (Bible MenthorQ v2.0)")
                logger.info(f"   1-Day Range: {day_min:.2f} → {day_max:.2f}")
                logger.info(f"   Mid @ {mid:.2f} = {position_pct:.0f}% du range")

                # Avertissements si proche des extrêmes
                if position_pct >= 95:
                    warnings.append(f"⚠️ Proche 1-Day Max ({position_pct:.0f}%) - Prudence extensions")
                    logger.warning(f"   ⚠️ TRÈS HAUT ({position_pct:.0f}%) - Risque reversal/consolidation")
                elif position_pct <= 5:
                    warnings.append(f"⚠️ Proche 1-Day Min ({position_pct:.0f}%) - Prudence extensions")
                    logger.warning(f"   ⚠️ TRÈS BAS ({position_pct:.0f}%) - Risque reversal/consolidation")
                elif position_pct >= 85:
                    logger.info(f"   ℹ️ Zone haute ({position_pct:.0f}%) - Surveiller résistances")
                elif position_pct <= 15:
                    logger.info(f"   ℹ️ Zone basse ({position_pct:.0f}%) - Surveiller supports")
                else:
                    logger.info(f"   ✅ Zone médiane ({position_pct:.0f}%) - OK pour extensions")

                logger.info("═" * 60)

        # === DÉCISION FINALE LAYER 3 ===
        # 🔧 ASSOUPLISSEMENT SESSION-AWARE (GLOBAL - 0 trade en 24h = trop strict partout):
        #    - US Session (14h-00h): modéré → 3 warnings (au lieu de 2)
        #    - London Session (8h-14h): permissif → 4 warnings (au lieu de 3)
        #    - Asia Session (0h-8h): très permissif → 5 warnings (au lieu de 4)
        num_warnings = len([w for w in warnings if '⚠️' in w])

        # Détecter session actuelle
        current_hour = datetime.now().hour

        # 🔧 MODIFICATION 2025-11-13: Augmenter warnings autorisés pour permettre plus de trades
        if 0 <= current_hour < 8:
            session = "ASIA"
            max_warnings = 6  # 5 → 6 (très permissif)
        elif 8 <= current_hour < 14:
            session = "LONDON"
            max_warnings = 5  # 4 → 5 (permissif)
        else:
            session = "US"
            max_warnings = 4  # 3 → 4 (modéré)

        # 🔍 AFFICHER TOUS LES WARNINGS DÉTECTÉS (pour debug)
        logger.info("=" * 60)
        logger.info(f"📊 LAYER 3: SYNTHÈSE WARNINGS [{session}]")
        logger.info(f"   Total warnings: {num_warnings}/{max_warnings} autorisés")
        if warnings:
            logger.info("   Liste des warnings détectés:")
            for w in warnings:
                if '⚠️' in w:
                    logger.warning(f"      {w}")
                else:
                    logger.info(f"      {w}")
        else:
            logger.info("   ✅ Aucun warning détecté")
        logger.info(f"   VWAP favorable: {vwap_favorable}")
        logger.info("=" * 60)

        # ✅ Favorable si VWAP OK ET warnings sous le seuil
        # 🔧 MODIFICATION 2025-11-13: VWAP Override basé sur Layer 1 + Layer 2
        #    Si confluence forte OU OrderFlow parfait, accepter même si VWAP défavorable
        vwap_override = False

        # Option 1 : Layer 1 confidence élevée
        if layer1_confidence > 0.25:
            vwap_override = True
            logger.info(f"   💡 VWAP override: Layer 1 confidence élevée ({layer1_confidence:.2f})")

        # Option 2 : Layer 2 confidence élevée (OrderFlow parfait)
        if layer2_confidence > 0.20:
            vwap_override = True
            logger.info(f"   💡 VWAP override: Layer 2 confidence élevée ({layer2_confidence:.2f})")

        # Option 3 : Total confidence proche du seuil
        if (layer1_confidence + layer2_confidence) >= 0.40:
            vwap_override = True
            logger.info(f"   💡 VWAP override: Total confidence proche seuil ({layer1_confidence + layer2_confidence:.2f})")

        if vwap_override and not vwap_favorable:
            logger.info(f"   ✅ VWAP défavorable mais override activé")

        favorable = (vwap_favorable or vwap_override) and num_warnings <= max_warnings

        reason = f"Context: {num_warnings}/{max_warnings} warning(s) [{session}]"

        return Layer3Result(
            favorable=favorable,
            confidence=context_score,
            reason=reason,
            warnings=warnings
        )

    def _analyze_vwap_context(self, snapshot: Dict) -> Tuple[bool, float, List[str]]:
        """Analyse VWAP context"""
        favorable = True
        score = 0.0
        msgs = []

        in_value_area = snapshot.get('in_value_area', False)

        # === NOUVELLE MÉTHODE: VWAP BAND WIDTH COMME ATR ===
        # 🔧 CORRECTION DÉFINITIVE 2025-11-13: Remplacer ATR par VWAP Band Width
        #    Problème: ATR snapshot = 1.14 (1-minute bars) → Distance semble énorme
        #    Solution: Utiliser VWAP ±1σ (calculé sur session) comme volatilité de référence

        mid = snapshot.get('mid', 0)
        vwap = snapshot.get('vwap', 0)
        vwap_up1 = snapshot.get('vwap_up1', 0)
        vwap_dn1 = snapshot.get('vwap_dn1', 0)
        tick_size = snapshot.get('tick_size', 0.25)

        # 🔥 PHASE 2: Calculer ATR effectif depuis VWAP bands (utiliser calculator si disponible)
        if self.vwap_calculator_enabled:
            try:
                atr_effective = get_structural_volatility(snapshot)
                atr_source = "VWAP_BAND"
                logger.debug(f"   📊 ATR effectif (VWAP band): {atr_effective:.2f} pts")
            except Exception as e:
                logger.warning(f"Erreur VWAP calculator: {e}, fallback ATR")
                # Fallback: calcul manuel
                if vwap_up1 and vwap_dn1 and vwap_up1 > vwap_dn1:
                    vwap_band_width = vwap_up1 - vwap_dn1
                    atr_effective = vwap_band_width / 2
                    atr_source = "VWAP_BAND_MANUAL"
                    logger.debug(f"   📊 ATR effectif (VWAP band manual): {atr_effective:.2f} pts")
                else:
                    atr_raw = snapshot.get('atr', 1.0)
                    atr_source = "ATR_FALLBACK"
        elif vwap_up1 and vwap_dn1 and vwap_up1 > vwap_dn1:
            # Fallback: calcul manuel si calculator non disponible
            vwap_band_width = vwap_up1 - vwap_dn1
            atr_effective = vwap_band_width / 2
            atr_source = "VWAP_BAND_MANUAL"
            logger.debug(f"   📊 ATR effectif (VWAP band manual): {atr_effective:.2f} pts (band={vwap_band_width:.2f})")
        else:
            # Fallback: ATR snapshot avec minimum de référence
            atr_raw = snapshot.get('atr', 1.0)

            # Détecter symbole
            sym = snapshot.get('sym', 'ES')

            # ATR minimum par instrument
            ATR_MIN_REFERENCE = {
                'ES': 3.0,
                'NQ': 10.0,
                'RTY': 2.0
            }

            if 'ES' in sym:
                atr_min = ATR_MIN_REFERENCE['ES']
            elif 'NQ' in sym:
                atr_min = ATR_MIN_REFERENCE['NQ']
            elif 'RTY' in sym or '2RTY' in sym:
                atr_min = ATR_MIN_REFERENCE['RTY']
            else:
                atr_min = 3.0

            atr_effective = max(atr_raw, atr_min)
            atr_source = "ATR_NORMALIZED"

            logger.debug(f"   📊 ATR effectif (snapshot normalisé): {atr_effective:.2f} pts (raw={atr_raw:.2f})")

        # Calculer distance VWAP en ATR effectif
        d_vwap_pts = abs(mid - vwap)
        d_vwap_atr = d_vwap_pts / atr_effective if atr_effective > 0 else 0

        # Log comparaison
        logger.info(f"   📏 Distance VWAP: {d_vwap_pts:.2f} pts = {d_vwap_atr:.2f} ATR ({atr_source})")

        # Debug si snapshot avait valeur anormale
        d_vwap_atr_snapshot = snapshot.get('d_vwap_atr', 0)
        if abs(d_vwap_atr_snapshot) > 10.0:
            logger.warning(f"   ⚠️ Snapshot d_vwap_atr={d_vwap_atr_snapshot:.2f} (anormal)")
            logger.warning(f"   ✅ Corrigé à {d_vwap_atr:.2f} ATR avec {atr_source}")

        # === SEUILS MAX VWAP DISTANCE (ADAPTATIFS) ===
        # 🔥 NOUVEAU 13-NOV-2025: Seuils dynamiques avec Adaptive Thresholds
        # Au lieu de seuils fixes, utiliser seuils adaptatifs selon volatilité
        current_hour = datetime.now().hour

        if self.adaptive_thresholds:
            # Obtenir seuils adaptatifs
            adaptive = self.adaptive_thresholds.get_adaptive_thresholds(snapshot)
            max_vwap_distance = adaptive['max_vwap_distance_atr']

            logger.info(f"   🔧 Seuil adaptatif VWAP: {max_vwap_distance:.2f} ATR (régime={adaptive['volatility_regime']})")
        else:
            # Fallback: Seuils fixes par session
            # 🔧 MODIFICATION 2025-11-13: Augmentation drastique pour permettre trades en tendance forte
            #    Observé en live: d_vwap_atr = -13.99 (tendance baissière forte)
            if 0 <= current_hour < 8:
                # ASIA : Permissif (spreads larges, liquidité faible)
                max_vwap_distance = 15.0  # 4.0 → 15.0 ATR (permettre tendances extrêmes)
            elif 8 <= current_hour < 14:
                # LONDON : Normal
                max_vwap_distance = 12.0  # 3.0 → 12.0 ATR
            else:
                # US : Normal (haute liquidité)
                max_vwap_distance = 15.0  # 2.5 → 15.0 ATR (observé 13.99 en live)

        # RÈGLE: Ne pas trader trop loin de VWAP
        if abs(d_vwap_atr) > max_vwap_distance:
            favorable = False
            msgs.append(f"⚠️ Trop loin VWAP ({d_vwap_atr:.2f} > {max_vwap_distance:.1f} ATR)")
        else:
            score = self.config.CONTEXT_WEIGHTS['vwap']

        # BONUS: Si dans value area
        if in_value_area:
            score += 0.02

        return favorable, score, msgs

    def _analyze_value_area(self, snapshot: Dict, signal: TradeSignal) -> Tuple[float, List[str]]:
        """Analyse value area"""
        score = 0.0
        msgs = []

        position = snapshot.get('position_in_range', 50)

        if signal == TradeSignal.LONG:
            # Pour LONG: meilleur si bas du range
            if position < self.config.RANGE_POSITION_LOW_THRESHOLD:
                score = self.config.CONTEXT_WEIGHTS['value_area']
            elif position > self.config.RANGE_POSITION_HIGH_THRESHOLD:
                msgs.append(f"⚠️ LONG proche haut range ({position:.0f}%)")

        elif signal == TradeSignal.SHORT:
            # Pour SHORT: meilleur si haut du range
            if position > self.config.RANGE_POSITION_HIGH_THRESHOLD:
                score = self.config.CONTEXT_WEIGHTS['value_area']
            elif position < self.config.RANGE_POSITION_LOW_THRESHOLD:
                msgs.append(f"⚠️ SHORT proche bas range ({position:.0f}%)")

        return score, msgs

    def _analyze_structure(self, snapshot: Dict, signal: TradeSignal) -> Tuple[float, List[str]]:
        """Analyse market structure"""
        score = 0.0
        msgs = []

        structure = snapshot.get('structure', {})
        onh = structure.get('onh', 0)
        onl = structure.get('onl', 0)
        mid = snapshot.get('mid', 0)

        if not onh or not onl:
            return score, msgs

        if signal == TradeSignal.LONG:
            # Pour LONG: favorable si proche ONL
            if mid < onl + self.config.STRUCTURE_PROXIMITY_TICKS:
                score = self.config.CONTEXT_WEIGHTS['structure']
            elif mid > onh - self.config.STRUCTURE_PROXIMITY_TICKS:
                msgs.append(f"⚠️ LONG proche ONH ({onh:.2f})")

        elif signal == TradeSignal.SHORT:
            # Pour SHORT: favorable si proche ONH
            if mid > onh - self.config.STRUCTURE_PROXIMITY_TICKS:
                score = self.config.CONTEXT_WEIGHTS['structure']
            elif mid < onl + self.config.STRUCTURE_PROXIMITY_TICKS:
                msgs.append(f"⚠️ SHORT proche ONL ({onl:.2f})")

        return score, msgs

    def _analyze_volatility(self, snapshot: Dict) -> Tuple[float, List[str]]:
        """Analyse volatility"""
        score = 0.0
        msgs = []

        vol_regime = snapshot.get('volatility_regime', 1)

        if vol_regime == 1:  # Normal
            score = self.config.CONTEXT_WEIGHTS['volatility']
        elif vol_regime == 2:  # High
            score = self.config.CONTEXT_WEIGHTS['volatility'] * 0.5
            msgs.append(f"⚠️ Haute volatilité (regime={vol_regime})")

        return score, msgs

    # ═══════════════════════════════════════════════════════════════════
    # PIPELINE COMPLET 3-LAYER
    # ═══════════════════════════════════════════════════════════════════

    def evaluate_trade(self, snapshot: Dict) -> TradeDecision:
        """
        Pipeline complet 3-Layer

        Workflow:
            0. Fast Filters: Pre-filter ultra-rapide (< 1ms)
            1. Layer 1: MenthorQ génère signal
            2. Layer 2: OrderFlow valide signal
            3. Layer 3: Context filtre signal
            4. Décision finale basée sur les 3 layers

        Args:
            snapshot: Snapshot ML_READY complet

        Returns:
            TradeDecision avec action finale et confidence totale
        """
        logger.info("=" * 80)
        logger.debug("ÉVALUATION 3-LAYER")  # ✅ Optimisé
        logger.info("=" * 80)

        # === ⚡ FAST FILTERS FIRST (Nouveau 13-NOV-2025) ===
        # Rejection ultra-rapide des cas évidents non-tradables
        if self.fast_filters:
            passed, reason, time_ms = self.fast_filters.evaluate_fast_pipeline(snapshot)

            if not passed:
                logger.info(f"⚡ FAST FILTER REJET: {reason} ({time_ms:.3f}ms)")
                return TradeDecision(
                    action=None,
                    should_trade=False,
                    total_confidence=0.0,
                    layer1_confidence=0.0,
                    layer2_confidence=0.0,
                    layer3_confidence=0.0,
                    breakdown={},
                    rejection_reason=f"Fast Filter: {reason}"
                )

            logger.debug(f"⚡ FAST FILTERS: PASSÉ ({time_ms:.3f}ms)")

        # === 🔧 ADAPTIVE THRESHOLDS (Nouveau 13-NOV-2025) ===
        # Mettre à jour historiques pour seuils adaptatifs
        if self.adaptive_thresholds:
            self.adaptive_thresholds.update(snapshot)

        # === LAYER 1: MenthorQ Signal ===
        layer1 = self.validate_layer1_menthorq(snapshot)

        if not layer1.signal:
            logger.info("❌ LAYER 1: Aucun signal MenthorQ")
            return TradeDecision(
                action=None,
                should_trade=False,
                total_confidence=0.0,
                layer1_confidence=layer1.confidence,
                layer2_confidence=0.0,
                layer3_confidence=0.0,
                breakdown={'layer1': layer1},
                rejection_reason="Layer 1: No MenthorQ signal"
            )

        logger.info(f"🔥 LAYER 1 (MenthorQ): {layer1.signal.value} @ {layer1.confidence:.2f}")
        for trigger in layer1.triggers:
            logger.info(f"   {trigger}")

        # === LAYER 2: OrderFlow Validation ===
        layer2 = self.validate_layer2_orderflow(snapshot, layer1.signal)

        if not layer2.validated:
            logger.info(f"❌ LAYER 2: OrderFlow rejette {layer1.signal.value}")
            return TradeDecision(
                action=None,
                should_trade=False,
                total_confidence=layer1.confidence,
                layer1_confidence=layer1.confidence,
                layer2_confidence=layer2.confidence,
                layer3_confidence=0.0,
                breakdown={'layer1': layer1, 'layer2': layer2},
                rejection_reason=f"Layer 2: OrderFlow rejects {layer1.signal.value}"
            )

        logger.info(f"✅ LAYER 2 (OrderFlow): VALIDÉ @ {layer2.confidence:.2f}")
        for validation in layer2.validations:
            logger.info(f"   {validation}")

        # === LAYER 3: Context Filter ===
        layer3 = self.validate_layer3_context(snapshot, layer1.signal, layer1_confidence=layer1.confidence, layer2_confidence=layer2.confidence)

        if not layer3.favorable:
            logger.info(f"❌ LAYER 3: Contexte défavorable pour {layer1.signal.value}")
            return TradeDecision(
                action=None,
                should_trade=False,
                total_confidence=layer1.confidence + layer2.confidence,
                layer1_confidence=layer1.confidence,
                layer2_confidence=layer2.confidence,
                layer3_confidence=layer3.confidence,
                breakdown={'layer1': layer1, 'layer2': layer2, 'layer3': layer3},
                rejection_reason=f"Layer 3: Context unfavorable for {layer1.signal.value}"
            )

        logger.info(f"✅ LAYER 3 (Context): FAVORABLE @ {layer3.confidence:.2f}")
        for warning in layer3.warnings:
            logger.info(f"   {warning}")

        # === CALCUL CONFIANCE TOTALE ===
        total_confidence = layer1.confidence + layer2.confidence + layer3.confidence

        # ═══════════════════════════════════════════════════════════════
        # 🔥 DÉTECTION CONTRE-TENDANCE
        # ═══════════════════════════════════════════════════════════════
        # Si signal contre le context bias → Exiger confluence plus élevée
        context_bias = snapshot.get('bias', 'NEUTRAL')
        signal_direction = layer1.signal.value  # "LONG" ou "SHORT"

        is_counter_trend = False
        if context_bias == "BULLISH" and signal_direction == "SHORT":
            is_counter_trend = True
        elif context_bias == "BEARISH" and signal_direction == "LONG":
            is_counter_trend = True

        # === DÉCISION FINALE ===
        # 🔥 FIX 02/12/2025: Utiliser seuils PAR SYMBOLE depuis unified_thresholds
        # 🔥 FIX 08/12/2025: Extraire symbole AVANT de calculer required_confidence
        symbol = snapshot.get('sym', 'ES')
        # Normaliser symbole (ESZ25_FUT_CME → ES, NQU25_FUT_CME → NQ)
        if '_' in symbol:
            symbol = symbol.split('_')[0]
        base_symbol = symbol[:2] if len(symbol) >= 2 else symbol  # ESZ25 → ES, NQU25 → NQ

        # Récupérer seuils par symbole depuis unified_thresholds
        if UNIFIED_THRESHOLDS_AVAILABLE and base_symbol in MIN_LAYER_CONFIDENCE:
            min_menthorq = MIN_LAYER_CONFIDENCE[base_symbol]['layer1']
            min_orderflow = MIN_LAYER_CONFIDENCE[base_symbol]['layer2']
            min_context = MIN_LAYER_CONFIDENCE[base_symbol]['layer3']
            min_total = MIN_TOTAL_CONFIDENCE.get(base_symbol, 0.35)
            logger.info(f"🎯 [{base_symbol}] Seuils: L1={min_menthorq:.0%}, L2={min_orderflow:.0%}, L3={min_context:.0%}, Total={min_total:.0%}")
        else:
            # Fallback seuils globaux
            min_menthorq = self.config.MIN_MENTHORQ_CONFIDENCE
            min_orderflow = self.config.MIN_ORDERFLOW_CONFIDENCE
            min_context = self.config.MIN_CONTEXT_CONFIDENCE
            # 🔥 FIX 08/12/2025: MIN_TOTAL_CONFIDENCE est un dict, pas un float!
            if isinstance(self.config.MIN_TOTAL_CONFIDENCE, dict):
                min_total = self.config.MIN_TOTAL_CONFIDENCE.get(base_symbol, 0.35)
            else:
                min_total = self.config.MIN_TOTAL_CONFIDENCE
            logger.warning(f"⚠️ [{base_symbol}] Seuils globaux utilisés (unified_thresholds non disponible)")

        # ✅ FIX 21/11 06:10: Seuil contre-tendance réduit de 50% → 30%
        #    Raison: Layer 2 avec fallback donne 8%, impossible d'atteindre 50%
        #    Nouveau: Layer1 (37%) + Layer2 (8%) + Layer3 (20%) = 65% possible
        if is_counter_trend:
            required_confidence = 0.30  # ✅ 30% pour contre-tendance (réduit de 50%)
            logger.warning(f"⚠️ SIGNAL CONTRE-TENDANCE: {signal_direction} vs Context {context_bias}")
            logger.warning(f"   → Confluence requise: {required_confidence:.0%} (au lieu de {min_total:.0%})")
        else:
            required_confidence = min_total  # 🔥 FIX 08/12: Utiliser min_total (float) au lieu du dict

        # Vérifier chaque condition individuellement pour un meilleur diagnostic
        layer1_ok = layer1.confidence >= min_menthorq
        layer2_ok = layer2.confidence >= min_orderflow
        layer3_ok = layer3.confidence >= min_context
        # Pour le total, utiliser required_confidence (qui gère contre-tendance) OU min_total
        total_ok = total_confidence >= max(required_confidence, min_total)

        should_trade = layer1_ok and layer2_ok and layer3_ok and total_ok

        if should_trade:
            logger.info("=" * 80)
            if is_counter_trend:
                logger.info(f"🚀 TRADE VALIDÉ (CONTRE-TENDANCE): {layer1.signal.value} @ {total_confidence:.1%} confidence")
                logger.info(f"   ✅ Confluence élevée atteinte ({total_confidence:.1%} >= {required_confidence:.0%})")
            else:
                logger.info(f"🚀 TRADE VALIDÉ: {layer1.signal.value} @ {total_confidence:.1%} confidence")
            logger.info("=" * 80)
        else:
            logger.info("=" * 80)
            rejection_reasons = []
            if not layer1_ok:
                rejection_reasons.append(f"Layer1: {layer1.confidence:.1%} < {min_menthorq:.1%}")
            if not layer2_ok:
                rejection_reasons.append(f"Layer2: {layer2.confidence:.1%} < {min_orderflow:.1%}")
            if not layer3_ok:
                rejection_reasons.append(f"Layer3: {layer3.confidence:.1%} < {min_context:.1%}")
            if not total_ok:
                rejection_reasons.append(f"Total: {total_confidence:.1%} < {max(required_confidence, min_total):.1%}")

            if is_counter_trend:
                logger.info(f"❌ TRADE REJETÉ (CONTRE-TENDANCE): {', '.join(rejection_reasons)}")
                logger.info(f"   → Besoin {required_confidence:.0%} pour contre-tendance (vs {min_total:.0%} normal)")
            else:
                logger.info(f"❌ TRADE REJETÉ: {', '.join(rejection_reasons)}")
                logger.info(f"   → Total confidence: {total_confidence:.1%}, Required: {max(required_confidence, min_total):.1%}")
            logger.info("=" * 80)

        return TradeDecision(
            action=layer1.signal if should_trade else None,
            should_trade=should_trade,
            total_confidence=total_confidence,
            layer1_confidence=layer1.confidence,
            layer2_confidence=layer2.confidence,
            layer3_confidence=layer3.confidence,
            breakdown={
                'layer1': layer1,
                'layer2': layer2,
                'layer3': layer3
            },
            rejection_reason=None if should_trade else "Insufficient confidence across layers"
        )


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Créer filtre
    filter = ML3LayerFilter()

    # Exemple snapshot NQ
    snapshot = {
        "sym": "NQZ25_FUT_CME",
        "mid": 25224.38,
        "cum_delta_session": 1863,
        "delta": -86,
        "deltaPct": -0.288591,
        "smart_money_flow": 0.288591,
        "level1_imbalance": -0.333333,
        "askPct": 0.644295,
        "bidPct": 0.355705,
        "call_resistance": 27500.00,
        "put_support": 24000.00,
        "gamma_side": "below",
        "next_wall": {
            "price": 25200.00,
            "side": "put",
            "dist_ticks": -98,
            "strength": 0.310101
        },
        "gex_1": 25500.00,
        "gex_2": 25050.00,
        "gex_3": 25200.00,
        "blind_spot_0": 25702.61,
        "hvl": 25490.00,
        "menthorq_impact_score": 0.097000,
        "menthorq_proximity_strength": 0.194000,
        "d_vwap": 3.72,
        "d_vwap_atr": 0.914337,
        "in_value_area": True,
        "position_in_range": 46.495957,
        "atr": 4.07,
        "volatility_regime": 1,
        "structure": {
            "onh": 25746.88,
            "onl": 25746.38,
            "ibh": 25104.00,
            "ibl": 24883.88
        },
        "institutional_pressure": 0.288591,
        "battle_navale_signal_strength": 0.033198
    }

    # Évaluer trade
    decision = filter.evaluate_trade(snapshot)

    # Afficher résultat
    print("\n" + "=" * 80)
    print("📊 RÉSULTAT FINAL")
    print("=" * 80)
    print(f"Action:           {decision.action.value if decision.action else 'NONE'}")
    print(f"Should Trade:     {decision.should_trade}")
    print(f"Total Confidence: {decision.total_confidence:.1%}")
    print(f"  Layer 1:        {decision.layer1_confidence:.1%} / 50%")
    print(f"  Layer 2:        {decision.layer2_confidence:.1%} / 30%")
    print(f"  Layer 3:        {decision.layer3_confidence:.1%} / 20%")
    if decision.rejection_reason:
        print(f"Rejection:        {decision.rejection_reason}")
    print("=" * 80)
    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Créer filtre
    filter = ML3LayerFilter()

    # Exemple snapshot NQ
    snapshot = {
        "sym": "NQZ25_FUT_CME",
        "mid": 25224.38,
        "cum_delta_session": 1863,
        "delta": -86,
        "deltaPct": -0.288591,
        "smart_money_flow": 0.288591,
        "level1_imbalance": -0.333333,
        "askPct": 0.644295,
        "bidPct": 0.355705,
        "call_resistance": 27500.00,
        "put_support": 24000.00,
        "gamma_side": "below",
        "next_wall": {
            "price": 25200.00,
            "side": "put",
            "dist_ticks": -98,
            "strength": 0.310101
        },
        "gex_1": 25500.00,
        "gex_2": 25050.00,
        "gex_3": 25200.00,
        "blind_spot_0": 25702.61,
        "hvl": 25490.00,
        "menthorq_impact_score": 0.097000,
        "menthorq_proximity_strength": 0.194000,
        "d_vwap": 3.72,
        "d_vwap_atr": 0.914337,
        "in_value_area": True,
        "position_in_range": 46.495957,
        "atr": 4.07,
        "volatility_regime": 1,
        "structure": {
            "onh": 25746.88,
            "onl": 25746.38,
            "ibh": 25104.00,
            "ibl": 24883.88
        },
        "institutional_pressure": 0.288591,
        "battle_navale_signal_strength": 0.033198
    }

    # Évaluer trade
    decision = filter.evaluate_trade(snapshot)

    # Afficher résultat
    print("\n" + "=" * 80)
    print("📊 RÉSULTAT FINAL")
    print("=" * 80)
    print(f"Action:           {decision.action.value if decision.action else 'NONE'}")
    print(f"Should Trade:     {decision.should_trade}")
    print(f"Total Confidence: {decision.total_confidence:.1%}")
    print(f"  Layer 1:        {decision.layer1_confidence:.1%} / 50%")
    print(f"  Layer 2:        {decision.layer2_confidence:.1%} / 30%")
    print(f"  Layer 3:        {decision.layer3_confidence:.1%} / 20%")
    if decision.rejection_reason:
        print(f"Rejection:        {decision.rejection_reason}")
    print("=" * 80)


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Créer filtre
    filter = ML3LayerFilter()

    # Exemple snapshot NQ
    snapshot = {
        "sym": "NQZ25_FUT_CME",
        "mid": 25224.38,
        "cum_delta_session": 1863,
        "delta": -86,
        "deltaPct": -0.288591,
        "smart_money_flow": 0.288591,
        "level1_imbalance": -0.333333,
        "askPct": 0.644295,
        "bidPct": 0.355705,
        "call_resistance": 27500.00,
        "put_support": 24000.00,
        "gamma_side": "below",
        "next_wall": {
            "price": 25200.00,
            "side": "put",
            "dist_ticks": -98,
            "strength": 0.310101
        },
        "gex_1": 25500.00,
        "gex_2": 25050.00,
        "gex_3": 25200.00,
        "blind_spot_0": 25702.61,
        "hvl": 25490.00,
        "menthorq_impact_score": 0.097000,
        "menthorq_proximity_strength": 0.194000,
        "d_vwap": 3.72,
        "d_vwap_atr": 0.914337,
        "in_value_area": True,
        "position_in_range": 46.495957,
        "atr": 4.07,
        "volatility_regime": 1,
        "structure": {
            "onh": 25746.88,
            "onl": 25746.38,
            "ibh": 25104.00,
            "ibl": 24883.88
        },
        "institutional_pressure": 0.288591,
        "battle_navale_signal_strength": 0.033198
    }

    # Évaluer trade
    decision = filter.evaluate_trade(snapshot)

    # Afficher résultat
    print("\n" + "=" * 80)
    print("📊 RÉSULTAT FINAL")
    print("=" * 80)
    print(f"Action:           {decision.action.value if decision.action else 'NONE'}")
    print(f"Should Trade:     {decision.should_trade}")
    print(f"Total Confidence: {decision.total_confidence:.1%}")
    print(f"  Layer 1:        {decision.layer1_confidence:.1%} / 50%")
    print(f"  Layer 2:        {decision.layer2_confidence:.1%} / 30%")
    print(f"  Layer 3:        {decision.layer3_confidence:.1%} / 20%")
    if decision.rejection_reason:
        print(f"Rejection:        {decision.rejection_reason}")
    print("=" * 80)
