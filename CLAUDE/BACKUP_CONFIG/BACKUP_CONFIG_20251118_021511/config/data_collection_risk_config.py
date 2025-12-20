#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Data Collection Risk Configuration
Configuration spécialisée pour collecter 500-1000 trades rapidement
Version: Production Ready - CORRIGÉ
Location: D:\\MIA_IA_system\\config\\data_collection_risk_config.py

CORRECTIONS APPLIQUÉES:
- Import corrigé de RiskParameters depuis execution.risk_manager
- Structure standardisée pour compatibilité avec simple_trader.py
- Ajout de logging approprié
- Export complet des constantes et fonctions

OBJECTIF: Paramètres optimisés pour collecter un maximum de données
- Mode DATA_COLLECTION: Seuils réduits pour plus de trades
- Mode PAPER: Paramètres standards de validation
- Mode LIVE: Paramètres stricts pour trading réel
"""

from core.logger import get_logger
from dataclasses import dataclass, field
from datetime import time
from typing import Dict, Any

# Import correct de RiskParameters
try:
    from execution.risk_manager import RiskParameters
except ImportError:
    # Fallback si RiskParameters n'existe pas encore
    from dataclasses import dataclass

    @dataclass
    class RiskParameters:
        """Fallback RiskParameters si execution.risk_manager non disponible"""
        # Position sizing
        base_position_size: int = 1
        max_position_size: int = 3
        max_positions_concurrent: int = 1

        # Risk per trade
        risk_per_trade_percent: float = 1.0
        max_risk_per_trade_dollars: float = 200.0

        # Daily limits
        daily_loss_limit: float = 1000.0
        daily_profit_target: float = 2000.0
        max_daily_trades: int = 20

        # Drawdown
        max_drawdown_percent: float = 5.0
        trailing_drawdown: bool = True

        # Battle Navale thresholds
        min_base_quality_for_trade: float = 0.6
        min_confluence_score: float = 0.65
        min_signal_probability: float = 0.70
        golden_rule_strict: bool = True

        # Mode flags
        data_collection_mode: bool = False

        # Time restrictions
        no_trade_before: time = field(default_factory=lambda: time(9, 35))
        no_trade_after: time = field(default_factory=lambda: time(15, 45))
        reduce_size_after: time = field(default_factory=lambda: time(15, 0))

        # Volatility
        high_volatility_threshold: float = 30.0
        reduce_size_high_vol: bool = True

        # Session multipliers
        session_risk_multipliers: Dict[str, float] = field(default_factory=lambda: {
            'asian': 0.5,
            'london': 1.0,
            'ny_am': 1.2,
            'ny_pm': 0.8,
            'close': 0.5
        })

# Configure logging
logger = get_logger(__name__)

# === DATA COLLECTION MODE (500-1000 TRADES) ===

DATA_COLLECTION_RISK_PARAMS = RiskParameters(
    # Position sizing - Plus agressif pour collecter
    base_position_size=1,                    # Taille base réduite
    max_position_size=3,                     # Max 3 contrats
    max_positions_concurrent=2,              # 2 positions simultanées

    # Risk per trade - Réduit pour plus de trades
    risk_per_trade_percent=0.5,             # 0.5% du capital (vs 1% normal)
    max_risk_per_trade_dollars=250.0,       # $250 max par trade

    # Daily limits - Optimisé pour collecte données
    daily_loss_limit=1000.0,                # $1000 limite perte (SEULE VRAIE LIMITE)
    daily_profit_target=5000.0,             # $5000 target (très élevé = pas d'arrêt)
    max_daily_trades=999,                   # Pas de limite trades!

    # Drawdown - Permissif
    max_drawdown_percent=8.0,               # 8% drawdown max
    trailing_drawdown=True,

    # Bataille Navale - SEUILS RÉDUITS pour plus de trades
    min_base_quality_for_trade=0.4,         # 0.4 vs 0.6 normal (40% plus de trades)
    min_confluence_score=0.45,              # 0.45 vs 0.65 normal (35% plus de trades)
    min_signal_probability=0.55,            # 55% probabilité minimum (vs 70% normal)
    golden_rule_strict=False,               # Désactivé pour plus de trades

    # Mode collecte activé
    data_collection_mode=True,              # MODE SPÉCIAL ACTIVÉ

    # Time restrictions - Étendues pour plus d'opportunités
    no_trade_before=time(9, 31),           # 1 min après ouverture (vs 5 min)
    no_trade_after=time(15, 55),           # 5 min avant fermeture (vs 15 min)
    reduce_size_after=time(15, 30),        # Réduction plus tardive

    # Volatility - Moins restrictif
    high_volatility_threshold=40.0,         # Seuil VIX plus élevé
    reduce_size_high_vol=False,            # Pas de réduction en haute vol

    # Session multipliers - Uniformes pour plus de trades
    session_risk_multipliers={
        'asian': 0.8,      # Permissif même Asie
        'london': 1.0,     # Normal Londres
        'ny_am': 1.0,      # Normal matin NY
        'ny_pm': 1.0,      # Normal après-midi (vs réduction)
        'close': 0.8       # Permissif fin journée
    }
)

# === PAPER TRADING MODE (VALIDATION STRATÉGIE) ===

PAPER_TRADING_RISK_PARAMS = RiskParameters(
    # Position sizing - Standard
    base_position_size=1,
    max_position_size=3,                    # Max 3 contrats (ES + NQ simultanés)
    max_positions_concurrent=2,             # 2 positions simultanées (1 ES + 1 NQ)

    # Risk per trade - Standard
    risk_per_trade_percent=1.0,             # 1% du capital
    max_risk_per_trade_dollars=200.0,       # $200 max par trade

    # 🔥 PHASE CALIBRAGE ES + NQ: Daily limits augmentées pour 2 symboles
    daily_loss_limit=10000.0,               # $10000 limite (CALIBRAGE ES+NQ)
    daily_profit_target=20000.0,            # $20000 target (CALIBRAGE ES+NQ)
    max_daily_trades=400,                   # 400 trades max (200 par symbole)

    # Drawdown - Standard
    max_drawdown_percent=5.0,               # 5% drawdown max
    trailing_drawdown=True,

    # 🔥 PHASE CALIBRAGE: Seuils abaissés pour collecter toutes les données
    min_base_quality_for_trade=0.30,        # 30% qualité minimum (CALIBRAGE)
    min_confluence_score=0.30,              # 30% confluence minimum (CALIBRAGE)
    min_signal_probability=0.40,            # 40% probabilité minimum (CALIBRAGE)
    golden_rule_strict=False,               # Règle DÉSACTIVÉE (CALIBRAGE)

    # Mode normal
    data_collection_mode=False,

    # Time restrictions - Standards
    no_trade_before=time(9, 35),           # 5 min après ouverture
    no_trade_after=time(15, 45),           # 15 min avant fermeture
    reduce_size_after=time(15, 0),         # Réduction après 15h

    # Volatility - Standard
    high_volatility_threshold=30.0,         # Seuil VIX normal
    reduce_size_high_vol=True,

    # Session multipliers - Standards
    session_risk_multipliers={
        'asian': 0.5,      # Réduit Asie
        'london': 1.0,     # Normal Londres
        'ny_am': 1.2,      # Boost matin NY
        'ny_pm': 0.8,      # Réduit après-midi
        'close': 0.5       # Très réduit fin journée
    }
)

# === LIVE TRADING MODE (PRODUCTION) ===

LIVE_TRADING_RISK_PARAMS = RiskParameters(
    # Position sizing - Conservateur
    base_position_size=1,
    max_position_size=3,                    # Max 3 contrats (ES + NQ simultanés)
    max_positions_concurrent=2,             # 2 positions simultanées (1 ES + 1 NQ)

    # Risk per trade - Très conservateur
    risk_per_trade_percent=0.75,            # 0.75% seulement
    max_risk_per_trade_dollars=400.0,       # $400 max

    # 🔥 PHASE CALIBRAGE ES + NQ: Limites augmentées pour 2 symboles
    daily_loss_limit=10000.0,               # $10000 limite (CALIBRAGE ES+NQ)
    daily_profit_target=20000.0,            # $20000 target (CALIBRAGE ES+NQ)
    max_daily_trades=400,                   # 400 trades max (200 par symbole)

    # Drawdown - Très strict
    max_drawdown_percent=3.0,               # 3% seulement!
    trailing_drawdown=True,

    # 🔥 PHASE CALIBRAGE: Seuils abaissés pour collecter toutes les données ML
    min_base_quality_for_trade=0.30,        # 30% qualité minimum (CALIBRAGE - très permissif)
    min_confluence_score=0.30,              # 30% confluence minimum (CALIBRAGE)
    min_signal_probability=0.40,            # 40% probabilité minimum (CALIBRAGE)
    golden_rule_strict=False,               # Règle DÉSACTIVÉE (CALIBRAGE)

    # Mode production
    data_collection_mode=False,

    # Time restrictions - Conservatrices
    no_trade_before=time(9, 40),           # 10 min après ouverture
    no_trade_after=time(15, 30),           # 30 min avant fermeture
    reduce_size_after=time(14, 30),        # Réduction précoce

    # Volatility - Très conservateur
    high_volatility_threshold=25.0,         # Seuil VIX bas
    reduce_size_high_vol=True,

    # Session multipliers - Conservateurs
    session_risk_multipliers={
        'asian': 0.3,      # Très réduit Asie
        'london': 0.8,     # Réduit Londres
        'ny_am': 1.0,      # Normal matin NY
        'ny_pm': 0.6,      # Très réduit après-midi
        'close': 0.2       # Quasi-arrêt fin journée
    }
)

# === HELPER FUNCTIONS ===


def get_risk_params_for_mode(mode: str) -> RiskParameters:
    """
    Retourne les paramètres de risque appropriés selon le mode

    Args:
        mode: "DATA_COLLECTION", "PAPER" ou "LIVE"

    Returns:
        RiskParameters configurés pour le mode
    """
    mode = mode.upper().strip()

    if mode in ["DATA_COLLECTION", "COLLECT", "DATA"]:
        logger.info("Configuration risk: MODE DATA COLLECTION")
        return DATA_COLLECTION_RISK_PARAMS
    elif mode in ["PAPER", "PAPER_TRADING", "SIMULATION"]:
        logger.info("Configuration risk: MODE PAPER TRADING")
        return PAPER_TRADING_RISK_PARAMS
    elif mode in ["LIVE", "LIVE_TRADING", "PRODUCTION"]:
        logger.info("Configuration risk: MODE LIVE TRADING")
        return LIVE_TRADING_RISK_PARAMS
    else:
        logger.warning(f"Mode inconnu '{mode}', utilisation PAPER_TRADING par défaut")
        return PAPER_TRADING_RISK_PARAMS


def validate_risk_params(params: RiskParameters) -> bool:
    """Valide la cohérence des paramètres de risque"""
    try:
        # Vérifications de base
        assert params.max_position_size > 0
        assert params.daily_loss_limit > 0
        assert params.max_daily_trades > 0

        # Vérifications de cohérence
        assert 0 < params.min_signal_probability <= 1
        assert 0 < params.min_confluence_score <= 1
        assert 0 < params.min_base_quality_for_trade <= 1
        assert params.max_position_size >= params.base_position_size

        # Risk per trade
        assert params.max_risk_per_trade_dollars > 0
        assert params.risk_per_trade_percent > 0

        return True

    except AssertionError as e:
        logger.error(f"Validation risk params échouée: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur validation risk params: {e}")
        return False


def compare_risk_modes():
    """Compare les différents modes de risque"""
    modes = {
        "DATA_COLLECTION": DATA_COLLECTION_RISK_PARAMS,
        "PAPER_TRADING": PAPER_TRADING_RISK_PARAMS,
        "LIVE_TRADING": LIVE_TRADING_RISK_PARAMS
    }

    logger.info("[STATS] COMPARAISON MODES DE RISQUE")
    logger.info("=" * 80)

    # Headers
    logger.info(f"{'PARAMÈTRE':<30} {'DATA_COLLECT':<15} {'PAPER':<15} {'LIVE':<15}")
    logger.info("-" * 80)

    # Comparaisons clés
    comparisons = [
        ("Min Signal Probability", "min_signal_probability"),
        ("Min Base Quality", "min_base_quality_for_trade"),
        ("Min Confluence", "min_confluence_score"),
        ("Daily Loss Limit", "daily_loss_limit"),
        ("Max Daily Trades", "max_daily_trades"),
        ("Max Position Size", "max_position_size"),
        ("Max Concurrent Pos", "max_positions_concurrent"),
        ("Golden Rule Strict", "golden_rule_strict"),
        ("Data Collection Mode", "data_collection_mode")
    ]

    for label, attr in comparisons:
        values = []
        for mode_name in ["DATA_COLLECTION", "PAPER_TRADING", "LIVE_TRADING"]:
            value = getattr(modes[mode_name], attr)
            if isinstance(value, bool):
                value_str = "✓" if value else "✗"
            elif isinstance(value, float) and value < 1:
                value_str = f"{value:.2%}"
            elif isinstance(value, float):
                value_str = f"${value:.0f}"
            else:
                value_str = str(value)
            values.append(value_str)

        logger.info(f"{label:<30} {values[0]:<15} {values[1]:<15} {values[2]:<15}")


def validate_all_configs() -> bool:
    """Valide toutes les configurations"""
    configs = {
        "DATA_COLLECTION": DATA_COLLECTION_RISK_PARAMS,
        "PAPER_TRADING": PAPER_TRADING_RISK_PARAMS,
        "LIVE_TRADING": LIVE_TRADING_RISK_PARAMS
    }

    all_valid = True
    for name, config in configs.items():
        valid = validate_risk_params(config)
        status = "[OK] VALIDE" if valid else "[ERROR] INVALIDE"
        logger.info(f"{name}: {status}")
        if not valid:
            all_valid = False

    return all_valid

# === EXPORTS ===


__all__ = [
    # Configurations
    'DATA_COLLECTION_RISK_PARAMS',
    'PAPER_TRADING_RISK_PARAMS',
    'LIVE_TRADING_RISK_PARAMS',

    # Functions
    'get_risk_params_for_mode',
    'validate_risk_params',
    'compare_risk_modes',
    'validate_all_configs',

    # Type
    'RiskParameters'
]

# === TESTING ===

if __name__ == "__main__":
    logger.info("🧪 TEST CONFIGURATION RISQUE...")

    # Test comparaison
    compare_risk_modes()

    # Test validation
    logger.info("\n📋 VALIDATION CONFIGURATIONS:")
    validate_all_configs()

    # Test factory
    logger.info("\n🏭 TEST FACTORY FUNCTION:")
    for mode in ["data_collection", "paper", "live", "unknown"]:
        params = get_risk_params_for_mode(mode)
        logger.info(f"Mode '{mode}' → data_collection_mode={params.data_collection_mode}")

    logger.info("\n[OK] Tests configuration risque terminés!")
