#!/usr/bin/env python3
"""
CHART ROUTER - Routage intelligent Chart 3 (ES) vs Chart 9 (NQ)
================================================================

Route automatiquement vers le bon chart selon le symbole :
- ES → Chart 3
- NQ → Chart 9
- YM → Chart 3 (même que ES)
- RTY → Chart 9 (même que NQ)

Version: 1.0.0
Date: Janvier 2025
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import time

# Ajouter le répertoire racine au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import get_logger

logger = get_logger(__name__)

class ChartRouter:
    """
    Routeur intelligent pour les charts selon le symbole
    
    Fonctionnalités :
    - Routing automatique ES→Chart3, NQ→Chart9
    - Support multi-symboles
    - Configuration flexible
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialisation du routeur de charts"""
        self.config = config or {}
        
        # ✅ Configuration du routing par défaut
        self.chart_mapping = {
            "ES": 3,      # ES → Chart 3
            "NQ": 9,      # NQ → Chart 9
            "YM": 3,      # YM → Chart 3 (même que ES)
            "RTY": 9,     # RTY → Chart 9 (même que NQ)
            "GC": 3,      # Gold → Chart 3
            "CL": 9,      # Crude Oil → Chart 9
        }
        
        # Permettre la surcharge via config
        if "chart_mapping" in self.config:
            self.chart_mapping.update(self.config["chart_mapping"])
        
        logger.info(f"🎯 Chart Router initialisé: {self.chart_mapping}")
    
    def get_chart_for_symbol(self, symbol: str) -> int:
        """
        Obtenir le numéro de chart pour un symbole
        
        Args:
            symbol: Symbole (ES, NQ, YM, RTY, etc.)
            
        Returns:
            Numéro de chart (3 ou 9)
        """
        # Nettoyer le symbole
        clean_symbol = self._clean_symbol(symbol)
        
        # Chercher dans le mapping
        chart = self.chart_mapping.get(clean_symbol, 3)  # Default Chart 3
        
        logger.debug(f"🎯 {symbol} → Chart {chart}")
        return chart
    
    def _clean_symbol(self, symbol: str) -> str:
        """Nettoyer le symbole pour le mapping"""
        if not symbol:
            return "ES"  # Default
        
        # Enlever les suffixes de contrat
        clean = symbol.upper()
        for suffix in ["Z25", "H26", "M26", "U26", "Z26", "_FUT", "_CME"]:
            clean = clean.replace(suffix, "")
        
        # Garder seulement les 2-3 premiers caractères
        return clean[:3]
    
    def route_snapshot(self, snapshot: Dict[str, Any]) -> Tuple[int, str]:
        """
        Router un snapshot vers le bon chart
        
        Args:
            snapshot: Snapshot de données
            
        Returns:
            Tuple[chart_number, clean_symbol]
        """
        symbol = snapshot.get("sym", "ES")
        clean_symbol = self._clean_symbol(symbol)
        chart = self.get_chart_for_symbol(clean_symbol)
        
        return chart, clean_symbol
    
    def get_qc_path(self, symbol: str, date_str: str) -> str:
        """
        Obtenir le chemin du fichier QC pour un symbole et une date
        
        Args:
            symbol: Symbole
            date_str: Date au format YYYYMMDD
            
        Returns:
            Chemin du fichier QC
        """
        chart = self.get_chart_for_symbol(symbol)
        return f"DATA_SIERRA_CHART/DATA_2025/{date_str}/CHART_{chart}/chart_{chart}_qc_go_nogo_{date_str}.json"
    
    def get_data_paths(self, symbol: str, date_str: str) -> Dict[str, str]:
        """
        Obtenir tous les chemins de données pour un symbole
        
        Args:
            symbol: Symbole
            date_str: Date au format YYYYMMDD
            
        Returns:
            Dictionnaire des chemins de données
        """
        chart = self.get_chart_for_symbol(symbol)
        base_path = f"DATA_SIERRA_CHART/DATA_2025/{date_str}/CHART_{chart}"
        
        return {
            "base_path": base_path,
            "qc_path": f"{base_path}/chart_{chart}_qc_go_nogo_{date_str}.json",
            "unified_path": f"{base_path}/unified_{date_str}_v8.jsonl",
            "trade_summary_path": f"{base_path}/chart_{chart}_trade_summary_{symbol}_FUT_CME_{date_str}.jsonl",
            "order_book_path": f"{base_path}/chart_{chart}_order_book_{symbol}_FUT_CME_{date_str}.jsonl"
        }
    
    def is_es_family(self, symbol: str) -> bool:
        """Vérifier si le symbole fait partie de la famille ES (Chart 3)"""
        clean_symbol = self._clean_symbol(symbol)
        return self.get_chart_for_symbol(clean_symbol) == 3
    
    def is_nq_family(self, symbol: str) -> bool:
        """Vérifier si le symbole fait partie de la famille NQ (Chart 9)"""
        clean_symbol = self._clean_symbol(symbol)
        return self.get_chart_for_symbol(clean_symbol) == 9
    
    def get_family_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtenir les informations de famille pour un symbole
        
        Args:
            symbol: Symbole
            
        Returns:
            Informations de famille
        """
        clean_symbol = self._clean_symbol(symbol)
        chart = self.get_chart_for_symbol(clean_symbol)
        
        if chart == 3:
            family = "ES_FAMILY"
            primary = "ES"
        else:
            family = "NQ_FAMILY"
            primary = "NQ"
        
        return {
            "symbol": clean_symbol,
            "chart": chart,
            "family": family,
            "primary_symbol": primary,
            "is_es_family": chart == 3,
            "is_nq_family": chart == 9
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du routeur"""
        return {
            "chart_mapping": self.chart_mapping,
            "total_symbols": len(self.chart_mapping),
            "chart_3_symbols": [s for s, c in self.chart_mapping.items() if c == 3],
            "chart_9_symbols": [s for s, c in self.chart_mapping.items() if c == 9]
        }

# Fonction d'export
def get_chart_for_symbol(symbol: str) -> int:
    """
    Fonction d'export pour obtenir le chart d'un symbole
    
    Args:
        symbol: Symbole
        
    Returns:
        Numéro de chart
    """
    router = ChartRouter()
    return router.get_chart_for_symbol(symbol)

# Test rapide
if __name__ == "__main__":
    print("🧪 Test Chart Router...")
    
    router = ChartRouter()
    
    # Test des symboles
    test_symbols = ["ESZ25_FUT_CME", "NQH26_FUT_CME", "YMZ25_FUT_CME", "RTYH26_FUT_CME", "GCZ25_FUT_CME"]
    
    for symbol in test_symbols:
        chart = router.get_chart_for_symbol(symbol)
        family_info = router.get_family_info(symbol)
        print(f"✅ {symbol} → Chart {chart} ({family_info['family']})")
    
    print(f"\n📊 Stats: {router.get_stats()}")
