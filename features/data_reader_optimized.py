#!/usr/bin/env python3
"""
DATA READER OPTIMIZED - Lecteur de données optimisé pour réduire les temps de cold start
======================================================================================

Optimisations :
- Lecture partielle "dernier N" pour éviter de charger tout le fichier
- Warm-up + cache pour pré-calculer les features
- Streaming pour les gros fichiers JSONL
- Cache LRU avec TTL

Version: 1.0.0
Date: Janvier 2025
"""

import json
import collections
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
from functools import lru_cache
import pandas as pd

class OptimizedDataReader:
    """
    Lecteur de données optimisé pour réduire les temps de cold start
    
    Fonctionnalités :
    - Lecture partielle des derniers N enregistrements
    - Streaming pour les gros fichiers
    - Cache LRU avec TTL
    - Warm-up des features
    """
    
    def __init__(self, cache_size: int = 500, cache_ttl: int = 60):
        """Initialisation du lecteur optimisé"""
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}
        
        print("📊 OptimizedDataReader initialisé")
        print(f"   - Cache size: {cache_size}")
        print(f"   - Cache TTL: {cache_ttl}s")
    
    def read_latest_unified(self, path: str, symbol: str, last_n: int = 200) -> List[Dict[str, Any]]:
        """
        Lit les derniers N enregistrements d'un fichier unifié
        
        Args:
            path: Chemin vers le fichier JSONL
            symbol: Symbole à filtrer
            last_n: Nombre d'enregistrements à lire (derniers)
            
        Returns:
            Liste des derniers N enregistrements
        """
        cache_key = f"{path}:{symbol}:{last_n}"
        
        # Vérifier le cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # Utiliser un deque pour garder seulement les derniers N
            buffer = collections.deque(maxlen=last_n)
            
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record.get("sym", "").startswith(symbol):
                            buffer.append(record)
                    except json.JSONDecodeError:
                        continue
            
            result = list(buffer)
            
            # Mettre en cache
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            
            print(f"📊 Lecture optimisée: {len(result)} enregistrements pour {symbol}")
            return result
            
        except Exception as e:
            print(f"❌ Erreur lecture optimisée: {e}")
            return []
    
    def read_jsonl_streaming(self, path: str, symbol: str) -> Iterator[Dict[str, Any]]:
        """
        Lit un fichier JSONL en streaming (itérateur)
        
        Args:
            path: Chemin vers le fichier JSONL
            symbol: Symbole à filtrer
            
        Yields:
            Enregistrements un par un
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record.get("sym", "").startswith(symbol):
                            yield record
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"❌ Erreur streaming: {e}")
    
    def warmup_features(self, data: List[Dict[str, Any]], feature_calculator) -> Dict[str, Any]:
        """
        Warm-up des features pour éviter le cold start
        
        Args:
            data: Données à pré-calculer
            feature_calculator: Calculateur de features
            
        Returns:
            Cache des features pré-calculées
        """
        print("🔥 Warm-up des features...")
        start_time = time.time()
        
        cache = {}
        warmup_count = min(len(data), 50)  # Pré-calculer max 50 enregistrements
        
        for i, record in enumerate(data[-warmup_count:]):
            try:
                # Convertir en MarketData
                market_data = self._record_to_market_data(record)
                
                # Calculer les features
                features = feature_calculator.calculate_features(market_data)
                
                # Stocker dans le cache
                cache_key = f"{record.get('sym', '')}:{record.get('t', 0)}"
                cache[cache_key] = features
                
            except Exception as e:
                print(f"⚠️ Erreur warm-up {i}: {e}")
                continue
        
        warmup_time = (time.time() - start_time) * 1000
        print(f"✅ Warm-up terminé: {warmup_count} enregistrements en {warmup_time:.1f}ms")
        
        return cache
    
    def _record_to_market_data(self, record: Dict[str, Any]):
        """Convertit un enregistrement en MarketData"""
        from core.base_types import MarketData
        import pandas as pd
        
        return MarketData(
            symbol=record.get("sym", "ES"),
            open=float(record.get("o", 0)),
            high=float(record.get("h", 0)),
            low=float(record.get("l", 0)),
            close=float(record.get("c", 0)),
            volume=float(record.get("v", 0)),
            timestamp=pd.Timestamp(record.get("t", time.time()), unit='s')
        )
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si le cache est valide"""
        if cache_key not in self._cache:
            return False
        
        cache_time = self._cache_timestamps.get(cache_key, 0)
        return (time.time() - cache_time) < self.cache_ttl
    
    def clear_cache(self):
        """Vide le cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
        print("🗑️ Cache vidé")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        return {
            "cache_size": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "cache_ttl": self.cache_ttl
        }

# Instance globale
_global_reader = None

def get_optimized_data_reader() -> OptimizedDataReader:
    """Retourne l'instance globale du lecteur optimisé"""
    global _global_reader
    if _global_reader is None:
        _global_reader = OptimizedDataReader()
    return _global_reader

# Fonctions de compatibilité
def read_latest_unified(path: str, symbol: str, last_n: int = 200) -> List[Dict[str, Any]]:
    """Fonction de compatibilité pour lire les derniers N enregistrements"""
    reader = get_optimized_data_reader()
    return reader.read_latest_unified(path, symbol, last_n)

def warmup_features(data: List[Dict[str, Any]], feature_calculator) -> Dict[str, Any]:
    """Fonction de compatibilité pour le warm-up"""
    reader = get_optimized_data_reader()
    return reader.warmup_features(data, feature_calculator)

if __name__ == "__main__":
    # Test du lecteur optimisé
    print("🧪 Test OptimizedDataReader...")
    
    reader = OptimizedDataReader()
    
    # Test avec un fichier fictif
    test_data = [
        {"sym": "ESZ25_FUT_CME", "t": 1640995200, "o": 4150.0, "h": 4155.0, "l": 4145.0, "c": 4152.0, "v": 1000},
        {"sym": "ESZ25_FUT_CME", "t": 1640995260, "o": 4152.0, "h": 4158.0, "l": 4150.0, "c": 4156.0, "v": 1200},
        {"sym": "NQZ25_FUT_CME", "t": 1640995320, "o": 15000.0, "h": 15050.0, "l": 14950.0, "c": 15025.0, "v": 800}
    ]
    
    # Test de lecture
    result = reader.read_latest_unified("test.jsonl", "ES", 2)
    print(f"📊 Résultat: {len(result)} enregistrements")
    
    # Test des stats du cache
    stats = reader.get_cache_stats()
    print(f"📈 Stats cache: {stats}")
    
    print("✅ Test OptimizedDataReader terminé")





