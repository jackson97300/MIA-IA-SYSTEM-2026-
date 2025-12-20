"""
Core module pour MIA_IA_SYSTEM
Version avec support UTF-8 et logger centralisé
Version: 3.2.0 - Ajout trading_types.py pour éviter imports circulaires
"""

# IMPORTANT: Importer le logger en premier pour configurer UTF-8
from .logger import get_logger

logger = get_logger(__name__)

# ✅ NOUVEAU: Import trading types (PRIORITÉ HAUTE pour éviter imports circulaires)
try:
    from .trading_types import (
        TradingMode, AutomationStatus, Position
    )
    trading_types_imports = True
    logger.debug("[OK] trading_types importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import trading_types: {e}")
    trading_types_imports = False

# Import base types (SANS TradingSignal pour éviter conflit avec trading_types)
try:
    from .base_types import (
        MarketData, SignalType, MarketRegime,
        ES_TICK_SIZE, ES_TICK_VALUE, OrderFlowData,
        get_session_phase, validate_market_data, TradeResult,
        SystemState
    )
    # ✅ Import TradingSignal depuis trading_types (avec paramètre 'action')
    from .trading_types import TradingSignal
    base_imports = True
    logger.debug("[OK] base_types importé avec succès (TradingSignal from trading_types)")
except ImportError as e:
    logger.warning(f"Could not import base_types: {e}")
    base_imports = False

# Import detectors
try:
    from .battle_navale import (
        BattleNavaleDetector,
        BattleNavaleAnalyzer,
        create_battle_navale_detector
    )
    battle_imports = True
    logger.debug("[OK] battle_navale importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import battle_navale: {e}")
    battle_imports = False

try:
    from .patterns_detector import PatternsDetector, create_patterns_detector
    patterns_imports = True
    logger.debug("[OK] patterns_detector importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import patterns_detector: {e}")
    patterns_imports = False

# IBKR connector supprimé (migration vers Sierra) - Plus utilisé

# Sierra Order Router (trading-only, pas de datafeed)
try:
    from .sierra_order_router import SierraOrderRouter, get_sierra_order_router, place_entry, place_exit, cancel_order
    sierra_router_imports = True
    logger.debug("[OK] sierra_order_router importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import sierra_order_router: {e}")
    sierra_router_imports = False

try:
    from .structure_data import StructureDataProcessor, create_structure_data_processor, MenthorQConsolidator, create_menthorq_consolidator
    structure_imports = True
    logger.debug("[OK] structure_data importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import structure_data: {e}")
    structure_imports = False

# ✅ NOUVEAUX MODULES - Signal Analysis & Risk Management
try:
    from .signal_explainer import SignalExplainer, create_signal_explainer
    signal_explainer_imports = True
    logger.debug("[OK] signal_explainer importé avec succès")
except ImportError as e:
    logger.debug(f"[SKIP] signal_explainer: {e}")  # ✅ Changed to debug
    signal_explainer_imports = False

try:
    from .catastrophe_monitor import CatastropheMonitor, create_catastrophe_monitor
    catastrophe_monitor_imports = True
    logger.debug("[OK] catastrophe_monitor importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import catastrophe_monitor: {e}")
    catastrophe_monitor_imports = False

try:
    from .lessons_learned_analyzer import LessonsLearnedAnalyzer, create_lessons_learned_analyzer
    lessons_learned_imports = True
    logger.debug("[OK] lessons_learned_analyzer importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import lessons_learned_analyzer: {e}")
    lessons_learned_imports = False

try:
    from .session_analyzer import create_session_analyzer
    session_analyzer_imports = True
    logger.debug("[OK] session_analyzer importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import session_analyzer: {e}")
    session_analyzer_imports = False

try:
    from .mentor_system import MentorSystem, create_mentor_system
    mentor_system_imports = True
    logger.debug("[OK] mentor_system importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import mentor_system: {e}")
    mentor_system_imports = False

# MenthorQ Integration Modules
try:
    from .menthorq_battle_navale import MenthorQBattleNavaleAnalyzer, create_menthorq_battle_navale_analyzer
    menthorq_battle_imports = True
    logger.debug("[OK] menthorq_battle_navale importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import menthorq_battle_navale: {e}")
    menthorq_battle_imports = False

# MenthorQ Integration Modules
try:
    from .menthorq_integration import analyze_menthorq_integration, create_menthorq_integration
    menthorq_integration_imports = True
    logger.debug("[OK] menthorq_integration importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import menthorq_integration: {e}")
    menthorq_integration_imports = False

try:
    from .menthorq_execution_rules import evaluate_execution_rules, create_menthorq_execution_rules, ExecutionRulesResult
    menthorq_rules_imports = True
    logger.debug("[OK] menthorq_execution_rules importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import menthorq_execution_rules: {e}")
    menthorq_rules_imports = False

# Data Integrity Validator est dans base_types.py, importé avec base_types

# MIA Unifier Stub
try:
    from .mia_unifier_stub import MIAUnifier, UnifiedEmitter, JSONLReader
    mia_unifier_imports = True
    logger.debug("[OK] mia_unifier_stub importé avec succès")
except ImportError as e:
    logger.warning(f"Could not import mia_unifier_stub: {e}")
    mia_unifier_imports = False

# Import logger functions pour export
try:
    from .logger import get_logger, setup_logging, get_logger_config
    logger_imports = True
    logger.debug("[OK] logger functions importées avec succès")
except ImportError as e:
    logger.warning(f"Could not import logger functions: {e}")
    logger_imports = False

# Build __all__ based on successful imports
__all__ = []

# Logger functions (priorité pour configuration UTF-8)
if logger_imports:
    __all__.extend(['get_logger', 'setup_logging', 'get_logger_config'])

# ✅ NOUVEAU: Trading types (priorité haute pour éviter imports circulaires)
if trading_types_imports:
    __all__.extend(['TradingMode', 'AutomationStatus', 'Position'])

# Base types
if base_imports:
    __all__.extend([
        'MarketData', 'TradingSignal', 'SignalType', 'MarketRegime',
        'ES_TICK_SIZE', 'ES_TICK_VALUE', 'OrderFlowData',
        'get_session_phase', 'validate_market_data', 'TradeResult',
        'SystemState'
    ])

# Detectors
if battle_imports:
    __all__.extend([
        'BattleNavaleDetector',
        'BattleNavaleAnalyzer',
        'create_battle_navale_detector'
    ])

if patterns_imports:
    __all__.extend(['PatternsDetector', 'create_patterns_detector'])

# IBKR exports supprimés (migration vers Sierra) - Plus utilisé

if sierra_router_imports:
    __all__.extend(['SierraOrderRouter', 'get_sierra_order_router', 'place_entry', 'place_exit', 'cancel_order'])

if structure_imports:
    __all__.extend(['StructureDataProcessor', 'create_structure_data_processor', 'MenthorQConsolidator', 'create_menthorq_consolidator'])

# Structure data supprimé (migration vers JSONL normalizer)

# ✅ NOUVEAUX MODULES - Signal Analysis & Risk Management
if signal_explainer_imports:
    __all__.extend(['SignalExplainer', 'create_signal_explainer'])

if catastrophe_monitor_imports:
    __all__.extend(['CatastropheMonitor', 'create_catastrophe_monitor'])

if lessons_learned_imports:
    __all__.extend(['LessonsLearnedAnalyzer', 'create_lessons_learned_analyzer'])

if session_analyzer_imports:
    __all__.extend(['create_session_analyzer'])

if mentor_system_imports:
    __all__.extend(['MentorSystem', 'create_mentor_system'])

# MenthorQ Integration exports
if menthorq_battle_imports:
    __all__.extend(['MenthorQBattleNavaleAnalyzer', 'create_menthorq_battle_navale_analyzer'])

if menthorq_integration_imports:
    __all__.extend(['analyze_menthorq_integration', 'create_menthorq_integration'])

if menthorq_rules_imports:
    __all__.extend(['evaluate_execution_rules', 'create_menthorq_execution_rules', 'ExecutionRulesResult'])

# MIA Unifier exports
if mia_unifier_imports:
    __all__.extend(['MIAUnifier', 'UnifiedEmitter', 'JSONLReader'])

# Log summary of imports
successful_imports = []
failed_imports = []

# ✅ NOUVEAU: Trading types tracking
if trading_types_imports: successful_imports.append("trading_types")
else: failed_imports.append("trading_types")

if base_imports: successful_imports.append("base_types")
else: failed_imports.append("base_types")

if battle_imports: successful_imports.append("battle_navale")
else: failed_imports.append("battle_navale")

if patterns_imports: successful_imports.append("patterns_detector")
else: failed_imports.append("patterns_detector")

# IBKR tracking supprimé (migration vers Sierra) - No longer logged

if sierra_router_imports: successful_imports.append("sierra_order_router")
else: failed_imports.append("sierra_order_router")

# Structure data - ajout conditionnel selon le succès de l'import
if structure_imports:
    successful_imports.append("structure_data")
else:
    failed_imports.append("structure_data")

# ✅ NOUVEAUX MODULES - Signal Analysis & Risk Management
if signal_explainer_imports: successful_imports.append("signal_explainer")
else: failed_imports.append("signal_explainer")

if catastrophe_monitor_imports: successful_imports.append("catastrophe_monitor")
else: failed_imports.append("catastrophe_monitor")

if lessons_learned_imports: successful_imports.append("lessons_learned_analyzer")
else: failed_imports.append("lessons_learned_analyzer")

if session_analyzer_imports: successful_imports.append("session_analyzer")
else: failed_imports.append("session_analyzer")

if mentor_system_imports: successful_imports.append("mentor_system")
else: failed_imports.append("mentor_system")

# MenthorQ Integration tracking
if menthorq_battle_imports: successful_imports.append("menthorq_battle_navale")
else: failed_imports.append("menthorq_battle_navale")

if menthorq_integration_imports: successful_imports.append("menthorq_integration")
else: failed_imports.append("menthorq_integration")

if menthorq_rules_imports: successful_imports.append("menthorq_execution_rules")
else: failed_imports.append("menthorq_execution_rules")

if mia_unifier_imports: successful_imports.append("mia_unifier_stub")
else: failed_imports.append("mia_unifier_stub")

if logger_imports: successful_imports.append("logger")
else: failed_imports.append("logger")

# Log initialization status
if successful_imports:
    logger.info(f"Core module initialized. Loaded: {', '.join(successful_imports)}")
if failed_imports:
    logger.warning(f"Failed to load: {', '.join(failed_imports)}")

# ✅ NOUVEAU: Log spécial pour trading_types (critique pour imports circulaires)
if trading_types_imports:
    logger.info("[CRITICAL] trading_types module loaded - circular imports prevention active")
else:
    logger.error("[ERROR] trading_types module failed - risk of circular imports!")

# Version info
__version__ = "3.2.0"
__author__ = "MIA Trading System"

# Module status function
def get_module_status():
    """Get status of core module imports"""
    return {
        'version': __version__,
        'successful_imports': successful_imports,
        'failed_imports': failed_imports,
        'total_exports': len(__all__),
        'logger_configured': logger_imports,
        'trading_types_available': trading_types_imports,  # ✅ NOUVEAU
        'base_types_available': base_imports,
        'battle_navale_available': battle_imports,
        'patterns_available': patterns_imports,
        'ibkr_available': False,  # Supprimé (migration vers Sierra) - Plus utilisé
        'sierra_router_available': sierra_router_imports,
        'structure_available': structure_imports,
        # ✅ NOUVEAUX MODULES - Signal Analysis & Risk Management
        'signal_explainer_available': signal_explainer_imports,
        'catastrophe_monitor_available': catastrophe_monitor_imports,
        'lessons_learned_analyzer_available': lessons_learned_imports,
        'session_analyzer_available': session_analyzer_imports,
        'mentor_system_available': mentor_system_imports,
        # MenthorQ Integration
        'menthorq_battle_available': menthorq_battle_imports,
        'menthorq_integration_available': menthorq_integration_imports,
        'menthorq_rules_available': menthorq_rules_imports,
        'mia_unifier_available': mia_unifier_imports,
        'data_integrity_validator_available': base_imports,  # Dans base_types.py
        'circular_imports_prevention': trading_types_imports  # ✅ NOUVEAU
    }

# ✅ NOUVEAU: Fonction de diagnostic imports circulaires
def check_circular_imports_prevention():
    """Vérifie que la prévention des imports circulaires est active"""
    if not trading_types_imports:
        logger.error("[ERROR] trading_types non chargé - risque d'imports circulaires!")
        return False

    # Vérifier que les types sont disponibles
    try:
        from .trading_types import TradingMode, AutomationStatus, Position
        test_mode = TradingMode.PAPER
        test_status = AutomationStatus.STOPPED
        test_position = Position.FLAT
        logger.info("[OK] trading_types functional - circular imports prevented")
        return True
    except Exception as e:
        logger.error(f"[ERROR] trading_types dysfunctional: {e}")
        return False

__all__.extend(['get_module_status', 'check_circular_imports_prevention'])
