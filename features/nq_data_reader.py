#!/usr/bin/env python3
"""
Lecteur de données NQ depuis Chart 4
Basé sur la duplication du Chart 3
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class NQDataReader:
    """Lecteur de données NQ depuis les fichiers Chart 4"""
    
    def __init__(self, base_path: str = "D:\\MIA_IA_system\\DATA_SIERRA_CHART"):
        self.base_path = Path(base_path)
        self.chart_number = 4
        self.symbol = "NQU25_FUT_CME"
        
    def get_today_data_path(self) -> Path:
        """Retourne le chemin des données d'aujourd'hui"""
        today = datetime.now()
        year = today.year
        month_names = ["JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN",
                      "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE"]
        month = month_names[today.month - 1]
        date_str = today.strftime("%Y%m%d")
        
        return self.base_path / f"DATA_{year}" / month / date_str / f"CHART_{self.chart_number}"
    
    def read_latest_basedata(self) -> Optional[Dict[str, Any]]:
        """Lit les dernières données basedata NQ"""
        try:
            data_path = self.get_today_data_path()
            basedata_file = data_path / f"chart_{self.chart_number}_basedata_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            if not basedata_file.exists():
                logger.warning(f"Fichier basedata NQ non trouvé: {basedata_file}")
                return None
            
            # Lire la dernière ligne
            with open(basedata_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return None
                
                last_line = lines[-1].strip()
                return json.loads(last_line)
                
        except Exception as e:
            logger.error(f"Erreur lecture basedata NQ: {e}")
            return None
    
    def read_latest_vwap(self) -> Optional[Dict[str, Any]]:
        """Lit les dernières données VWAP NQ"""
        try:
            data_path = self.get_today_data_path()
            vwap_file = data_path / f"chart_{self.chart_number}_vwap_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            if not vwap_file.exists():
                return None
            
            with open(vwap_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return None
                
                last_line = lines[-1].strip()
                return json.loads(last_line)
                
        except Exception as e:
            logger.error(f"Erreur lecture VWAP NQ: {e}")
            return None
    
    def read_latest_depth(self) -> Optional[Dict[str, Any]]:
        """Lit les dernières données DOM NQ"""
        try:
            data_path = self.get_today_data_path()
            depth_file = data_path / f"chart_{self.chart_number}_depth_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            if not depth_file.exists():
                return None
            
            with open(depth_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return None
                
                last_line = lines[-1].strip()
                return json.loads(last_line)
                
        except Exception as e:
            logger.error(f"Erreur lecture DOM NQ: {e}")
            return None
    
    def get_nq_market_data(self) -> Dict[str, Any]:
        """Récupère toutes les données NQ actuelles"""
        basedata = self.read_latest_basedata()
        vwap = self.read_latest_vwap()
        depth = self.read_latest_depth()
        
        return {
            "symbol": self.symbol,
            "chart": self.chart_number,
            "timestamp": datetime.now().isoformat(),
            "basedata": basedata,
            "vwap": vwap,
            "depth": depth,
            "price": basedata.get("c") if basedata else None,
            "volume": basedata.get("v") if basedata else None
        }
    
    def read_historical_data(self, date: str, data_type: str) -> List[Dict[str, Any]]:
        """Lit les données historiques NQ pour une date donnée"""
        try:
            # Parser la date
            target_date = datetime.strptime(date, "%Y%m%d")
            year = target_date.year
            month_names = ["JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN",
                          "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE"]
            month = month_names[target_date.month - 1]
            
            data_path = self.base_path / f"DATA_{year}" / month / date / f"CHART_{self.chart_number}"
            data_file = data_path / f"chart_{self.chart_number}_{data_type}_{date}.jsonl"
            
            if not data_file.exists():
                logger.warning(f"Fichier historique NQ non trouvé: {data_file}")
                return []
            
            data = []
            with open(data_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur lecture historique NQ: {e}")
            return []






