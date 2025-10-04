#!/usr/bin/env python3
"""
Lanceur MIA en mode PAPER TRADING COMPLET
Configuration optimisée pour simulation complète avec données unifiées
"""

import sys
import os
import asyncio

# Ajouter le répertoire racine au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from LAUNCH.launch_24_7_menthorq_final import main, FINAL_CONFIG

# Configuration PAPER TRADING COMPLET OPTIMISÉ
PAPER_TRADING_CONFIG = FINAL_CONFIG.copy()
PAPER_TRADING_CONFIG.update({
    # Sierra Chart Integration - MODE PAPER TRADING
    'sierra_enabled': True,
    'sierra_fallback_simulation': True,  # Fallback activé pour paper trading
    'sierra_live_mode': False,  # Mode paper trading activé
    
    # Performance ULTRA-OPTIMISÉE pour paper trading
    'processing_timeout_ms': 200,  # Objectif <200ms
    'max_signals_per_day': 20,  # Plus de signaux en paper trading
    
    # Risk management standard pour paper trading
    'max_risk_budget': 1.0,  # 100% du capital (simulation)
    'min_pattern_confidence': 0.60,  # Moins strict en paper trading
    'min_confluence_execution': 0.65,  # Moins strict en paper trading
    
    # Features ULTRA-OPTIMISÉES pour paper trading
    'features_config': {
        'enable_advanced_features': True,
        'enable_menthorq_integration': True,
        'enable_smart_money_tracker': True,
        'enable_dow_theory': True,  # Dow Theory activée
        'enable_paper_trading_mode': True,  # Mode paper trading activé
        'enable_cache_optimization': True,  # Cache activé
        'enable_lazy_loading': True,  # Lazy loading activé
        'enable_prefiltering': True  # Préfiltrage activé
    },
    
    # Configuration des données unifiées
    'sierra_data_path': 'DATA_SIERRA_CHART/DATA_2025/OCTOBRE/20251001',
    'sierra_charts': [3, 9],  # CHART_3 (ES) et CHART_9 (NQ)
    'sierra_unified_pattern': 'chart_*_unified_20251001.jsonl',
    
    # Configuration des caches
    'cache_config': {
        'menthorq_cache_size': 1000,
        'menthorq_cache_ttl': 300,  # 5 minutes
        'battle_navale_cache_size': 500,
        'battle_navale_cache_ttl': 60,  # 1 minute
        'feature_cache_size': 2000,
        'feature_cache_ttl': 180  # 3 minutes
    }
})

async def main_paper_trading():
    """Fonction principale pour mode paper trading"""
    print("🚀 DÉMARRAGE MIA EN MODE PAPER TRADING COMPLET")
    print("=" * 60)
    print("📊 Mode: PAPER TRADING (simulation complète)")
    print("📈 Données: Fichiers unifiés du 1er octobre 2025")
    print("🎯 Charts: CHART_3 (ES) + CHART_9 (NQ)")
    print("🛡️ Risk management: Standard (simulation)")
    print("=" * 60)
    
    # Override de la configuration globale
    import LAUNCH.launch_24_7_menthorq_final as launcher_module
    launcher_module.FINAL_CONFIG.update(PAPER_TRADING_CONFIG)
    
    # Lancer le système principal
    await main()

if __name__ == "__main__":
    print("🎭 MIA PAPER TRADING SYSTEM")
    print("=" * 40)
    print("📅 Date: 1er octobre 2025")
    print("📊 Charts: ES (CHART_3) + NQ (CHART_9)")
    print("🎯 Mode: Simulation complète")
    print("=" * 40)
    
    try:
        asyncio.run(main_paper_trading())
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du système paper trading...")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
