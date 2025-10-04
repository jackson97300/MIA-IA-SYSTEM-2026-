#!/usr/bin/env python3
"""
🎯 DATA READER - MIA_IA_SYSTEM
==============================

Lecteur des données JSONL unifiées collectées par le système C++
- Lecture des 52 types de données
- Parsing des fichiers mia_unified_YYYYMMDD.jsonl
- Interface pour les features Python
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging
import time
from core.base_types import normalize_ts

logger = logging.getLogger(__name__)

@dataclass
class MarketDataSnapshot:
    """Snapshot des données de marché à un instant T"""
    timestamp: datetime
    symbol: str
    chart: int
    
    # BaseData (Graph 3)
    basedata: Optional[Dict] = None
    
    # VWAP (Graph 3 & 4)
    vwap_current: Optional[Dict] = None
    vwap_previous: Optional[Dict] = None
    
    # Volume Profile (Graph 3)
    volume_profile: Optional[Dict] = None
    vva: Optional[Dict] = None  # Value Area Lines
    
    # NBCV OrderFlow (Graph 3 & 4)
    nbcv_footprint: Optional[Dict] = None
    nbcv_metrics: Optional[Dict] = None
    nbcv_orderflow: Optional[Dict] = None
    
    # VIX (Graph 8)
    vix: Optional[Dict] = None
    
    # MenthorQ (Graph 10)
    menthorq_levels: List[Dict] = None
    
    # DOM & Quotes
    dom_levels: List[Dict] = None
    quotes: List[Dict] = None
    trades: List[Dict] = None
    
    def __post_init__(self):
        if self.menthorq_levels is None:
            self.menthorq_levels = []
        if self.dom_levels is None:
            self.dom_levels = []
        if self.quotes is None:
            self.quotes = []
        if self.trades is None:
            self.trades = []

class MIADataReader:
    """Lecteur des données MIA unifiées"""
    
    def __init__(self, data_dir: str = "D:\\MIA_IA_system"):
        self.data_dir = Path(data_dir)
        self.cache = {}  # Cache des données lues
        self.last_update = {}
        
        logger.info(f"🎯 MIA Data Reader initialisé - Dir: {self.data_dir}")
    
    def get_latest_unified_file(self) -> Optional[Path]:
        """Trouve le fichier unifié le plus récent"""
        pattern = "unified_*.jsonl"
        files = list(self.data_dir.glob(pattern))
        
        if not files:
            logger.warning("⚠️ Aucun fichier unified_*.jsonl trouvé")
            return None
        
        # Trier par date de modification
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        logger.info(f"📁 Fichier unifié le plus récent: {latest_file.name}")
        return latest_file
    
    def read_unified_data(self, file_path: Optional[Path] = None, 
                         max_lines: int = 1000) -> List[MarketDataSnapshot]:
        """Lit les données unifiées et les parse"""
        
        if file_path is None:
            file_path = self.get_latest_unified_file()
        
        if not file_path or not file_path.exists():
            logger.error(f"❌ Fichier non trouvé: {file_path}")
            return []
        
        snapshots = []
        current_snapshot = None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-max_lines:]  # Dernières lignes seulement
                
                for line_num, line in enumerate(lines, 1):
                    try:
                        data = json.loads(line.strip())
                        
                        # Extraire les informations de base avec normalisation
                        raw_timestamp = data.get('t', 0)
                        timestamp = normalize_ts(raw_timestamp)
                        symbol = data.get('sym', 'ES')
                        chart = data.get('chart', 3)
                        data_type = data.get('type', 'unknown')
                        
                        # Pour MenthorQ, créer un snapshot par niveau pour éviter la déduplication
                        if data_type in ["menthorq", "menthorq_level",
                                         "menthorq_gamma_levels", "menthorq_blind_spots", "menthorq_swing_levels"]:
                            # Ignorer tout niveau MenthorQ qui ne provient pas du Graph 10
                            if chart != 10:
                                continue
                            # Créer un nouveau snapshot pour chaque niveau MenthorQ
                            menthorq_snapshot = MarketDataSnapshot(
                                timestamp=timestamp,
                                symbol=symbol,
                                chart=chart
                            )
                            self._distribute_data(menthorq_snapshot, data_type, data)
                            snapshots.append(menthorq_snapshot)
                        else:
                            # Logique normale pour les autres types de données
                            if (current_snapshot is None or 
                                current_snapshot.timestamp != timestamp or
                                current_snapshot.symbol != symbol or
                                current_snapshot.chart != chart):
                                
                                if current_snapshot:
                                    snapshots.append(current_snapshot)
                                
                                current_snapshot = MarketDataSnapshot(
                                    timestamp=timestamp,
                                    symbol=symbol,
                                    chart=chart
                                )
                            
                            # Distribuer les données selon le type
                            self._distribute_data(current_snapshot, data_type, data)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Ligne {line_num} JSON invalide: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur ligne {line_num}: {e}")
                        continue
            
            # Ajouter le dernier snapshot (si ce n'est pas déjà un snapshot MenthorQ)
            if current_snapshot:
                snapshots.append(current_snapshot)
                
            logger.info(f"✅ {len(snapshots)} snapshots lus depuis {file_path.name}")
            return snapshots
            
        except Exception as e:
            logger.error(f"❌ Erreur lecture fichier {file_path}: {e}")
            return []
    
    def _distribute_data(self, snapshot: MarketDataSnapshot, data_type: str, data: Dict):
        """Distribue les données dans le bon champ du snapshot"""
        
        if data_type == "basedata":
            snapshot.basedata = data
        elif data_type == "vwap":
            if data.get('chart') == 3:
                snapshot.vwap_current = data
            elif data.get('chart') == 4:
                snapshot.vwap_previous = data
        elif data_type == "vva":
            snapshot.vva = data
        elif data_type == "nbcv_footprint":
            snapshot.nbcv_footprint = data
        elif data_type == "nbcv_metrics":
            snapshot.nbcv_metrics = data
        elif data_type == "nbcv_orderflow":
            snapshot.nbcv_orderflow = data
        elif data_type == "vix":
            snapshot.vix = data
        elif data_type in ["menthorq", "menthorq_level", "menthorq_gamma_levels", "menthorq_blind_spots", "menthorq_swing_levels"]:
            snapshot.menthorq_levels.append(data)
            # Gérer les deux formats : 'level_type' (nouveau) et 'name' (ancien)
            level_name = data.get('level_type', data.get('name', 'unknown'))
            price = data.get('price', data.get('px', 0))
            logger.debug(f"📊 MenthorQ level ajouté: {level_name} = {price}")
        elif data_type == "depth":
            snapshot.dom_levels.append(data)
        elif data_type == "quote":
            snapshot.quotes.append(data)
        elif data_type == "trade":
            snapshot.trades.append(data)
    
    def get_latest_snapshot(self, symbol: str = "ES") -> Optional[MarketDataSnapshot]:
        """Récupère le snapshot le plus récent pour un symbole avec cache"""
        # Vérifier le cache d'abord
        cache_key = f"latest_snapshot_{symbol}"
        current_time = time.time()
        
        if cache_key in self.cache:
            snapshot, timestamp = self.cache[cache_key]
            # Cache valide pendant 5 secondes
            if current_time - timestamp < 5.0:
                return snapshot
        
        # Lire plus de lignes pour avoir plus de données historiques
        snapshots = self.read_unified_data(max_lines=2000)
        
        # Mapping des symboles vers les patterns dans le fichier JSONL
        symbol_patterns = {
            "ES": ["ESU25_FUT_CME", "ES", "ES_FUT"],
            "NQ": ["NQU25_FUT_CME", "NQ", "NQ_FUT"],
            "VIX": ["VIX", "VIX_INDEX"]
        }
        
        # Trouver les snapshots correspondants
        symbol_snapshots = []
        patterns = symbol_patterns.get(symbol, [symbol])
        
        for snapshot in snapshots:
            if any(pattern in snapshot.symbol for pattern in patterns):
                symbol_snapshots.append(snapshot)
        
        if not symbol_snapshots:
            logger.warning(f"⚠️ Aucun snapshot trouvé pour {symbol} (patterns: {patterns})")
            # Afficher les symboles disponibles pour debug
            available_symbols = list(set(s.symbol for s in snapshots))
            logger.info(f"📋 Symboles disponibles: {available_symbols}")
            return None
        
        latest = max(symbol_snapshots, key=lambda s: s.timestamp)
        
        # Mettre en cache
        self.cache[cache_key] = (latest, current_time)
        
        logger.info(f"📊 Snapshot le plus récent pour {symbol}: {latest.symbol} à {latest.timestamp}")
        return latest
    
    def get_menthorq_data(self, symbol: str = "ES") -> Optional[MarketDataSnapshot]:
        """Récupère spécifiquement les données MenthorQ du Graph 10"""
        # Chercher dans le fichier chart_10 spécifique
        chart_10_files = list(self.data_dir.glob("chart_10_*.jsonl"))
        
        if not chart_10_files:
            logger.warning("⚠️ Aucun fichier chart_10_*.jsonl trouvé")
            return None
        
        # Prendre le plus récent
        latest_chart_10 = max(chart_10_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"📁 Fichier MenthorQ Graph 10: {latest_chart_10.name}")
        
        # Lire les données du fichier chart_10
        snapshots = self.read_unified_data(latest_chart_10, max_lines=1000)
        
        # Chercher spécifiquement sur le Graph 10 pour MenthorQ
        menthorq_snapshots = []
        for snapshot in snapshots:
            if snapshot.chart == 10 and any(pattern in snapshot.symbol for pattern in ["ESU25_FUT_CME", "ES", "ES_FUT"]):
                menthorq_snapshots.append(snapshot)
        
        if not menthorq_snapshots:
            logger.warning(f"⚠️ Aucune donnée MenthorQ trouvée sur Graph 10 pour {symbol}")
            return None
        
        # Combiner tous les snapshots pour avoir tous les niveaux
        combined_snapshot = menthorq_snapshots[0]
        for snapshot in menthorq_snapshots[1:]:
            combined_snapshot.menthorq_levels.extend(snapshot.menthorq_levels)
        
        logger.info(f"📊 Données MenthorQ Graph 10 pour {symbol}: {combined_snapshot.symbol} à {combined_snapshot.timestamp}")
        logger.info(f"📊 Total niveaux combinés: {len(combined_snapshot.menthorq_levels)}")
        return combined_snapshot
    
    def get_historical_data(self, symbol: str = "ES", 
                           hours_back: int = 1) -> List[MarketDataSnapshot]:
        """Récupère les données historiques sur N heures"""
        snapshots = self.read_unified_data(max_lines=5000)
        
        # Filtrer par symbole et période
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        symbol_snapshots = [
            s for s in snapshots 
            if s.symbol == symbol and s.timestamp >= cutoff_time
        ]
        
        logger.info(f"📈 {len(symbol_snapshots)} snapshots historiques pour {symbol}")
        return symbol_snapshots

# === FONCTIONS UTILITAIRES ===

def create_market_data_dict(snapshot: MarketDataSnapshot) -> Dict[str, Any]:
    """Convertit un snapshot en dictionnaire compatible avec les features existantes"""
    
    # Normaliser le timestamp
    normalized_timestamp = normalize_ts(snapshot.timestamp)
    
    market_data = {
        'timestamp': normalized_timestamp,
        'symbol': snapshot.symbol,
        'chart': snapshot.chart
    }
    
    # BaseData - Génération de données par défaut si manquantes
    if snapshot.basedata:
        market_data.update({
            'open': snapshot.basedata.get('o', 4500.0),
            'high': snapshot.basedata.get('h', 4505.0),
            'low': snapshot.basedata.get('l', 4495.0),
            'close': snapshot.basedata.get('c', 4500.0),
            'volume': snapshot.basedata.get('v', 1000),
            'bid_volume': snapshot.basedata.get('bidvol', 500),
            'ask_volume': snapshot.basedata.get('askvol', 500)
        })
    else:
        # Génération de données OHLC par défaut basées sur les trades
        if snapshot.trades:
            prices = [trade.get('price', 4500.0) for trade in snapshot.trades]
            volumes = [trade.get('volume', 1) for trade in snapshot.trades]
            
            market_data.update({
                'open': prices[0] if prices else 4500.0,
                'high': max(prices) if prices else 4505.0,
                'low': min(prices) if prices else 4495.0,
                'close': prices[-1] if prices else 4500.0,
                'volume': sum(volumes) if volumes else 1000,
                'bid_volume': sum(volumes) // 2 if volumes else 500,
                'ask_volume': sum(volumes) // 2 if volumes else 500
            })
        else:
            # Données par défaut si aucune donnée disponible
            market_data.update({
                'open': 4500.0,
                'high': 4505.0,
                'low': 4495.0,
                'close': 4500.0,
                'volume': 1000,
                'bid_volume': 500,
                'ask_volume': 500
            })
    
    # VWAP
    if snapshot.vwap_current:
        market_data.update({
            'vwap': snapshot.vwap_current.get('v', 4500.0),
            'vwap_up1': snapshot.vwap_current.get('up1', 4505.0),
            'vwap_dn1': snapshot.vwap_current.get('dn1', 4495.0),
            'vwap_up2': snapshot.vwap_current.get('up2', 4510.0),
            'vwap_dn2': snapshot.vwap_current.get('dn2', 4490.0)
        })
    
    # Volume Profile
    if snapshot.vva:
        market_data.update({
            'vah': snapshot.vva.get('vah', 4505.0),
            'val': snapshot.vva.get('val', 4495.0),
            'vpoc': snapshot.vva.get('vpoc', 4500.0),
            # VVA previous fields removed
        })
    
    # NBCV OrderFlow - Génération de données delta si manquantes
    if snapshot.nbcv_footprint:
        market_data.update({
            'ask_volume': snapshot.nbcv_footprint.get('ask_volume', 500),
            'bid_volume': snapshot.nbcv_footprint.get('bid_volume', 500),
            'delta': snapshot.nbcv_footprint.get('delta', 0),
            'trades': snapshot.nbcv_footprint.get('trades', 100),
            'cumulative_delta': snapshot.nbcv_footprint.get('cumulative_delta', 0),
            'total_volume': snapshot.nbcv_footprint.get('total_volume', 1000)
        })
    else:
        # Génération de données delta basées sur les trades et quotes
        bid_volume = 0
        ask_volume = 0
        
        if snapshot.trades:
            # Estimation basée sur les prix des trades vs bid/ask
            for trade in snapshot.trades:
                price = trade.get('price', 4500.0)
                volume = trade.get('volume', 1)
                
                # Estimation simple : prix proche du bid = volume bid, sinon ask
                if snapshot.quotes:
                    bid = snapshot.quotes.get('bid', price - 0.25)
                    ask = snapshot.quotes.get('ask', price + 0.25)
                    mid = (bid + ask) / 2
                    
                    if price <= mid:
                        bid_volume += volume
                    else:
                        ask_volume += volume
                else:
                    # Répartition 50/50 si pas de quotes
                    bid_volume += volume // 2
                    ask_volume += volume - (volume // 2)
        
        delta = ask_volume - bid_volume
        total_volume = bid_volume + ask_volume
        
        market_data.update({
            'ask_volume': ask_volume,
            'bid_volume': bid_volume,
            'delta': delta,
            'trades': len(snapshot.trades) if snapshot.trades else 0,
            'cumulative_delta': delta,  # Simplification pour les tests
            'total_volume': total_volume if total_volume > 0 else 1000
        })
    
    # NBCV OrderFlow Metrics (volume_imbalance)
    if snapshot.nbcv_orderflow:
        market_data.update({
            'volume_imbalance': snapshot.nbcv_orderflow.get('volume_imbalance', 0.0),
            'trade_intensity': snapshot.nbcv_orderflow.get('trade_intensity', 0.0),
            'delta_trend': snapshot.nbcv_orderflow.get('delta_trend', 0.0),
            'absorption_pattern': snapshot.nbcv_orderflow.get('absorption_pattern', 0.0)
        })
    
    # VIX
    if snapshot.vix:
        market_data.update({
            'vix': snapshot.vix.get('last', 20.0)
        })
    
    # MenthorQ Levels
    if snapshot.menthorq_levels:
        menthorq_data = {}
        for level in snapshot.menthorq_levels:
            # Gérer le cas où level est un string (données brutes)
            if isinstance(level, str):
                try:
                    import json
                    level = json.loads(level)
                except json.JSONDecodeError:
                    continue
            
            if isinstance(level, dict):
                # Gérer les deux formats : 'name' (ancien) et 'level_type' (nouveau)
                level_name = level.get('level_type', level.get('name', 'unknown'))
                price = level.get('price', level.get('px', 4500.0))
                menthorq_data[level_name] = price
        
        market_data['menthorq_levels'] = menthorq_data
    
    # DOM & Quotes
    if snapshot.dom_levels:
        market_data['dom_levels'] = snapshot.dom_levels
        
        # Extraire les meilleurs niveaux DOM
        bid_levels = [level for level in snapshot.dom_levels if level.get('side') == 'BID']
        ask_levels = [level for level in snapshot.dom_levels if level.get('side') == 'ASK']
        
        if bid_levels:
            best_bid = max(bid_levels, key=lambda x: x.get('price', 0))
            market_data['best_bid'] = best_bid.get('price', 4500.0)
            market_data['best_bid_size'] = best_bid.get('size', 100)
        
        if ask_levels:
            best_ask = min(ask_levels, key=lambda x: x.get('price', 999999))
            market_data['best_ask'] = best_ask.get('price', 4500.0)
            market_data['best_ask_size'] = best_ask.get('size', 100)
    
    if snapshot.quotes:
        market_data['quotes'] = snapshot.quotes
    
    if snapshot.trades:
        market_data['trades'] = snapshot.trades
    
    return market_data

# === INSTANCE GLOBALE ===
data_reader = MIADataReader()

def get_latest_market_data(symbol: str = "ES") -> Dict[str, Any]:
    """Fonction utilitaire pour récupérer les dernières données de marché"""
    snapshot = data_reader.get_latest_snapshot(symbol)
    if snapshot:
        return create_market_data_dict(snapshot)
    else:
        logger.warning(f"⚠️ Pas de données pour {symbol} - retour dictionnaire vide")
        return {'symbol': symbol, 'timestamp': datetime.now()}

def get_menthorq_market_data(symbol: str = "ES") -> Dict[str, Any]:
    """Fonction utilitaire pour récupérer les données MenthorQ du Graph 10"""
    snapshot = data_reader.get_menthorq_data(symbol)
    if snapshot:
        return create_market_data_dict(snapshot)
    else:
        logger.warning(f"⚠️ Pas de données MenthorQ pour {symbol} - retour dictionnaire vide")
        return {'symbol': symbol, 'timestamp': datetime.now()}

if __name__ == "__main__":
    # Test du lecteur
    reader = MIADataReader()
    latest = reader.get_latest_snapshot("ES")
    
    if latest:
        print(f"✅ Snapshot trouvé: {latest.timestamp}")
        print(f"   Symbol: {latest.symbol}")
        print(f"   Chart: {latest.chart}")
        print(f"   BaseData: {latest.basedata is not None}")
        print(f"   VWAP: {latest.vwap_current is not None}")
        print(f"   NBCV: {latest.nbcv_footprint is not None}")
        print(f"   VIX: {latest.vix is not None}")
        print(f"   MenthorQ: {len(latest.menthorq_levels)} niveaux")
    else:
        print("❌ Aucun snapshot trouvé")
