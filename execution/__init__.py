"""
Execution module pour MIA_IA_SYSTEM - Version Sans Import Circulaire + Post-Mortem
Version: 3.1 - Intégration Post-Mortem Analysis System
"""

from core.logger import get_logger

logger = get_logger(__name__)

__all__ = []

# ✅ Import types depuis core/trading_types en premier
try:
    from core.trading_types import TradingMode, AutomationStatus, Position
    __all__.extend(['TradingMode', 'AutomationStatus', 'Position'])
    logger.debug("[OK] Import core trading types")
except ImportError as e:
    logger.warning(f"Could not import core trading types: {e}")

# Import types de base (évite les dépendances circulaires)
try:
    from .risk_manager import RiskParameters, RiskAction, RiskLevel
    __all__.extend(['RiskParameters', 'RiskAction', 'RiskLevel'])
    logger.debug("[OK] Import risk_manager types")
except ImportError as e:
    logger.debug(f"Could not import risk_manager types: {e}")

try:
    from .order_manager import (
        OrderManager,
        create_order_manager,
        OrderType,
        OrderStatus,
        BrokerType
    )
    __all__.extend([
        'OrderManager',
        'create_order_manager', 
        'OrderType',
        'OrderStatus',
        'BrokerType'
    ])
    logger.debug("[OK] Import order_manager")
except ImportError as e:
    logger.warning(f"Could not import order_manager: {e}")

try:
    from .risk_manager import RiskManager, create_risk_manager
    __all__.extend(['RiskManager', 'create_risk_manager'])
    logger.debug("[OK] Import risk_manager complet")
except ImportError as e:
    logger.warning(f"Could not import risk_manager: {e}")

try:
    from .trade_snapshotter import TradeSnapshotter, create_trade_snapshotter
    __all__.extend(['TradeSnapshotter', 'create_trade_snapshotter'])
    logger.debug("[OK] Import trade_snapshotter")
except ImportError as e:
    logger.warning(f"Could not import trade_snapshotter: {e}")

# 🆕 NOUVEAU: Import Post-Mortem Analyzer
post_mortem_available = False
try:
    from .post_mortem_analyzer import (
        PostMortemAnalyzer,
        create_post_mortem_analyzer,
        setup_complete_post_mortem_system,
        PostMortemAnalysis,
        PostMortemInsight,
        TradeOutcome
    )
    __all__.extend([
        'PostMortemAnalyzer',
        'create_post_mortem_analyzer',
        'setup_complete_post_mortem_system',
        'PostMortemAnalysis',
        'PostMortemInsight', 
        'TradeOutcome'
    ])
    logger.debug("[OK] Import post_mortem_analyzer")
    post_mortem_available = True
except ImportError as e:
    logger.warning(f"Could not import post_mortem_analyzer: {e}")
    post_mortem_available = False

try:
    from .simple_trader import (
        SimpleBattleNavaleTrader,
        create_simple_trader,
        TradingSession,
        run_data_collection_session
    )
    __all__.extend([
        'SimpleBattleNavaleTrader',
        'create_simple_trader',
        'TradingSession', 
        'run_data_collection_session'
    ])
    logger.debug("[OK] Import simple_trader")
except ImportError as e:
    logger.debug(f"[SKIP] simple_trader: {e}")  # ✅ Changed to debug

successful_imports = [name for name in __all__ if name in globals() and globals()[name] is not None]
if successful_imports:
    logger.info(f"Execution module loaded successfully: {', '.join(successful_imports)}")
    if post_mortem_available:
        logger.info("🔍 Post-Mortem Analysis System: DISPONIBLE")
    else:
        logger.warning("🔍 Post-Mortem Analysis System: NON DISPONIBLE")
else:
    logger.error("No execution modules could be loaded!")

def is_module_available(module_name: str) -> bool:
    """Vérifie si un module est disponible"""
    return module_name in globals() and globals()[module_name] is not None

def is_post_mortem_available() -> bool:
    """Vérifie si le système post-mortem est disponible"""
    return post_mortem_available

# 🆕 NOUVEAU: Factory function pour système complet avec post-mortem
def create_complete_trading_system(mode: str = "PAPER", enable_post_mortem: bool = True):
    """
    Crée un système de trading complet avec post-mortem
    
    Args:
        mode: Mode de trading ("PAPER", "LIVE", "DATA_COLLECTION")
        enable_post_mortem: Activer l'analyse post-mortem
        
    Returns:
        SimpleBattleNavaleTrader avec post-mortem intégré
    """
    if enable_post_mortem and not post_mortem_available:
        logger.warning("Post-mortem demandé mais non disponible - création sans post-mortem")
        enable_post_mortem = False
    
    trader = create_simple_trader(mode)
    
    if enable_post_mortem:
        logger.info("🔍 Système de trading créé avec Post-Mortem Analysis")
    else:
        logger.info("📊 Système de trading créé sans Post-Mortem Analysis")
    
    return trader

# 🆕 NOUVEAU: Diagnostic du module execution
def diagnose_execution_module():
    """Diagnostic complet du module execution"""
    print("🔍 DIAGNOSTIC EXECUTION MODULE v3.1")
    print("=" * 50)
    
    # Modules core
    print("\n📦 MODULES CORE:")
    core_modules = ['OrderManager', 'RiskManager', 'TradeSnapshotter', 'SimpleBattleNavaleTrader']
    for module in core_modules:
        status = "✅ OK" if is_module_available(module) else "❌ MANQUANT"
        print(f"  {status} {module}")
    
    # Post-Mortem System
    print("\n🔍 POST-MORTEM ANALYSIS:")
    if post_mortem_available:
        print("  ✅ PostMortemAnalyzer")
        print("  ✅ create_post_mortem_analyzer")
        print("  ✅ setup_complete_post_mortem_system")
        print("  ✅ Integration automatique disponible")
    else:
        print("  ❌ Post-Mortem System non disponible")
        print("  ❌ Fichier post_mortem_analyzer.py manquant?")
    
    # Factory functions
    print("\n🏭 FACTORY FUNCTIONS:")
    factories = ['create_simple_trader', 'create_complete_trading_system']
    for factory in factories:
        status = "✅ OK" if factory in globals() else "❌ MANQUANT"
        print(f"  {status} {factory}")
    
    # Types disponibles
    print("\n📋 TYPES DISPONIBLES:")
    types_list = ['TradingMode', 'AutomationStatus', 'Position', 'RiskAction']
    for type_name in types_list:
        status = "✅ OK" if is_module_available(type_name) else "❌ MANQUANT"
        print(f"  {status} {type_name}")
    
    # Status global
    core_ok = all(is_module_available(m) for m in core_modules)
    print(f"\n🎯 STATUS GLOBAL:")
    print(f"  Core Trading: {'✅ COMPLET' if core_ok else '❌ INCOMPLET'}")
    print(f"  Post-Mortem: {'✅ ACTIVÉ' if post_mortem_available else '❌ DÉSACTIVÉ'}")
    print(f"  Factory Ready: {'✅ OK' if 'create_complete_trading_system' in globals() else '❌ ERROR'}")
    
    return core_ok and post_mortem_available

# 🆕 NOUVEAU: Test rapide du système
def test_execution_system():
    """Test rapide du système execution"""
    print("🧪 TEST EXECUTION SYSTEM")
    print("-" * 30)
    
    try:
        # Test création trader standard
        trader = create_simple_trader("PAPER")
        print("✅ create_simple_trader: OK")
        
        # Test création système complet
        complete_trader = create_complete_trading_system("PAPER", True)
        print("✅ create_complete_trading_system: OK")
        
        # Test post-mortem si disponible
        if post_mortem_available:
            post_mortem = create_post_mortem_analyzer()
            print("✅ create_post_mortem_analyzer: OK")
        else:
            print("⚠️ post_mortem_analyzer: NON DISPONIBLE")
        
        print("🎯 Test execution system: RÉUSSI")
        return True
        
    except Exception as e:
        print(f"❌ Test execution system: ÉCHEC - {e}")
        return False

__all__.extend([
    'is_module_available',
    'is_post_mortem_available', 
    'create_complete_trading_system',
    'diagnose_execution_module',
    'test_execution_system'
])

# Auto-diagnostic si exécuté directement
if __name__ == "__main__":
    diagnose_execution_module()
    test_execution_system()