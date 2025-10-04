#!/usr/bin/env python3
"""
🌐 LIVE DATA READER - MIA_IA_SYSTEM
====================================

Reader en temps réel pour les données Sierra Chart collectées en direct.
Remplace les snapshots statiques par les vraies données live.

FONCTIONNALITÉS:
- ✅ Lecture des derniers fichiers par timestamp
- ✅ Détection de staleness (fichiers obsolètes)
- ✅ Mapping symbole → chart → fichiers
- ✅ Anti-cache et mode strict
- ✅ Validation des échelles de prix

Author: MIA_IA_SYSTEM
Version: 1.0.0
Date: Octobre 2025
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging

from core.logger import get_logger

logger = get_logger(__name__)

class LiveDataReader:
    """
    Reader de données live depuis les fichiers Sierra Chart
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialisation du reader live"""
        self.config = config
        self.live_config = config.get("live_mode", {})
        self.watch_dirs = self.live_config.get("realtime", {}).get("watch_dirs", [])
        self.poll_ms = self.live_config.get("realtime", {}).get("poll_ms", 250)
        self.staleness_seconds = self.live_config.get("realtime", {}).get("file_staleness_seconds", 3)
        self.chart_mapping = self.live_config.get("chart_mapping", {"NQ": 9, "ES": 3})
        self.disable_fallbacks = self.live_config.get("disable_fallbacks", True)
        
        logger.info(f"🌐 Live Data Reader initialisé - Watch dirs: {len(self.watch_dirs)}")
        logger.info(f"📊 Chart mapping: {self.chart_mapping}")
        logger.info(f"⏱️ Poll interval: {self.poll_ms}ms, Staleness: {self.staleness_seconds}s")
    
    def get_chart_dir(self, symbol: str) -> Optional[Path]:
        """Retourne le répertoire de la chart pour un symbole"""
        # Extraire le préfixe du symbole (NQZ25_FUT_CME -> NQ)
        symbol_prefix = symbol.split('_')[0][:2]  # NQZ25 -> NQ
        chart_id = self.chart_mapping.get(symbol_prefix, None)
        if not chart_id:
            logger.warning(f"⚠️ Pas de mapping chart pour {symbol} (préfixe: {symbol_prefix})")
            return None
        
        # Chercher le répertoire correspondant
        for watch_dir in self.watch_dirs:
            if f"CHART_{chart_id}" in watch_dir:
                chart_path = Path(watch_dir)
                if chart_path.exists():
                    return chart_path
        
        logger.warning(f"⚠️ Répertoire CHART_{chart_id} non trouvé")
        return None
    
    def latest_file(self, chart_dir: Path, pattern: str) -> Optional[Path]:
        """Retourne le fichier le plus récent correspondant au pattern"""
        try:
            files = list(chart_dir.glob(pattern))
            if not files:
                return None
            
            # Trier par modification time (plus récent en premier)
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_file = files[0]
            
            # Vérifier la staleness
            now = time.time()
            file_age = now - latest_file.stat().st_mtime
            
            if file_age > self.staleness_seconds:
                logger.warning(f"⚠️ Fichier stale: {latest_file.name} (âge: {file_age:.1f}s)")
                return None
            
            return latest_file
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche fichier {pattern}: {e}")
            return None
    
    def read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Lit un fichier JSON avec gestion d'erreurs"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return None
                
                # Gérer les fichiers JSONL (une ligne = un JSON)
                if content.startswith('{'):
                    return json.loads(content)
                else:
                    # JSONL: prendre la dernière ligne
                    lines = content.split('\n')
                    last_line = lines[-1].strip()
                    if last_line:
                        return json.loads(last_line)
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erreur lecture {file_path}: {e}")
            return None
    
    def get_live_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Construit un snapshot live à partir des fichiers Sierra Chart
        
        Args:
            symbol: Symbole (ex: NQZ25_FUT_CME, ESZ25_FUT_CME)
            
        Returns:
            Snapshot live ou None si données indisponibles
        """
        try:
            chart_dir = self.get_chart_dir(symbol)
            if not chart_dir:
                return None
            
            symbol_short = symbol.split('_')[0]  # NQZ25_FUT_CME -> NQZ25
            symbol_prefix = symbol_short[:2]  # NQZ25 -> NQ
            chart_id = self.chart_mapping.get(symbol_prefix)  # NQ -> 9
            
            logger.debug(f"🔍 Lecture live snapshot: {symbol} → CHART_{chart_id}")
            
            # === 1. PRIX ET QUOTES ===
            quote_file = self.latest_file(chart_dir, f"chart_{chart_id}_quote_{symbol_short}_*.json*")
            if not quote_file:
                logger.warning(f"⚠️ Pas de quote file pour {symbol}")
                return None
            
            quote_data = self.read_json_file(quote_file)
            if not quote_data:
                return None
            
            # === 2. DOM/DEPTH ===
            depth_file = self.latest_file(chart_dir, f"chart_{chart_id}_depth_{symbol_short}_*.json*")
            depth_data = self.read_json_file(depth_file) if depth_file else {}
            
            # === 3. TRADE SUMMARY (OrderFlow) ===
            trade_file = self.latest_file(chart_dir, f"chart_{chart_id}_trade_summary_{symbol_short}_*.json*")
            trade_data = self.read_json_file(trade_file) if trade_file else {}
            
            # === 4. VWAP ===
            vwap_file = self.latest_file(chart_dir, f"chart_{chart_id}_vwap_{symbol_short}_*.json*")
            vwap_data = self.read_json_file(vwap_file) if vwap_file else {}
            
            # === 5. VOLUME PROFILE (VPOC) ===
            vp_file = self.latest_file(chart_dir, f"chart_{chart_id}_vva_{symbol_short}_*.json*")
            vp_data = self.read_json_file(vp_file) if vp_file else {}
            
            # === 6. MENTHORQ GAMMA ===
            gamma_file = self.latest_file(chart_dir, f"chart_{chart_id}_menthorq_gamma_{symbol_short}_*.json*")
            gamma_data = self.read_json_file(gamma_file) if gamma_file else {}
            
            # === 7. MENTHORQ BLIND SPOTS ===
            blind_file = self.latest_file(chart_dir, f"chart_{chart_id}_menthorq_blind_spots_{symbol_short}_*.json*")
            blind_data = self.read_json_file(blind_file) if blind_file else {}
            
            # === CONSTRUCTION DU SNAPSHOT ===
            snapshot = {
                "sym": symbol,
                "t": int(time.time()),
                "last": quote_data.get("last", 0.0),
                "bid": quote_data.get("bid", 0.0),
                "ask": quote_data.get("ask", 0.0),
                "phase": "REGULAR",
                "regime": "TREND",
                "vix": 18.5,  # TODO: lire depuis VIX file
                
                # DOM Data
                "dom": depth_data,
                
                # Trade Summary (OrderFlow)
                "trade_summary_current": trade_data,
                "trade_summary_history": [],  # TODO: charger historique
                
                # VWAP
                "vwap": vwap_data.get("vwap", 0.0),
                "vwap_session": vwap_data.get("session", 0.0),
                
                # Volume Profile
                "vpoc": vp_data.get("vpoc", 0.0),
                "val": vp_data.get("val", 0.0),
                "vah": vp_data.get("vah", 0.0),
                
                # MenthorQ
                "menthorq_gamma": gamma_data,
                "menthorq_blind_spots": blind_data,
                
                # Métadonnées
                "_source": "live_files",
                "_chart_id": chart_id,
                "_files_used": {
                    "quote": quote_file.name if quote_file else None,
                    "depth": depth_file.name if depth_file else None,
                    "trade": trade_file.name if trade_file else None,
                    "vwap": vwap_file.name if vwap_file else None,
                    "vp": vp_file.name if vp_file else None,
                    "gamma": gamma_file.name if gamma_file else None,
                    "blind": blind_file.name if blind_file else None
                }
            }
            
            # === VALIDATION DES DONNÉES ===
            if not self._validate_snapshot(snapshot, symbol):
                return None
            
            logger.info(f"✅ Snapshot live construit: {symbol} @ {snapshot['last']}")
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Erreur construction snapshot live {symbol}: {e}")
            return None
    
    def _validate_snapshot(self, snapshot: Dict[str, Any], symbol: str) -> bool:
        """Valide la cohérence du snapshot"""
        try:
            price = snapshot.get("last", 0.0)
            vwap = snapshot.get("vwap", 0.0)
            vpoc = snapshot.get("vpoc", 0.0)
            
            # Validation prix
            if price <= 0:
                logger.warning(f"⚠️ Prix invalide: {price}")
                return False
            
            # Validation échelle NQ vs ES
            if symbol.startswith("NQ") and price < 10000:
                logger.warning(f"⚠️ Prix NQ suspect: {price} (attendu ~25000)")
                return False
            
            if symbol.startswith("ES") and price > 10000:
                logger.warning(f"⚠️ Prix ES suspect: {price} (attendu ~4000)")
                return False
            
            # Validation VWAP
            if vwap > 0 and abs(price - vwap) / price > 0.1:  # 10% d'écart max
                logger.warning(f"⚠️ VWAP incohérent: prix={price}, vwap={vwap}")
                if self.disable_fallbacks:
                    return False
            
            # Validation VPOC
            if vpoc > 0:
                if symbol.startswith("NQ") and vpoc < 10000:
                    logger.warning(f"⚠️ VPOC NQ échelle ES: {vpoc}")
                    if self.disable_fallbacks:
                        return False
                
                if symbol.startswith("ES") and vpoc > 10000:
                    logger.warning(f"⚠️ VPOC ES échelle NQ: {vpoc}")
                    if self.disable_fallbacks:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur validation snapshot: {e}")
            return False
    
    def is_live_mode_enabled(self) -> bool:
        """Vérifie si le mode live est activé"""
        return self.live_config.get("enabled", False)
    
    def get_available_symbols(self) -> List[str]:
        """Retourne la liste des symboles disponibles"""
        symbols = []
        for symbol_prefix, chart_id in self.chart_mapping.items():
            chart_dir = self.get_chart_dir(symbol_prefix)
            if chart_dir:
                # Chercher les fichiers quote pour détecter les symboles
                quote_files = list(chart_dir.glob(f"chart_{chart_id}_quote_*_*.json*"))
                for file in quote_files:
                    # Extraire le symbole du nom de fichier
                    # Ex: chart_9_quote_NQZ25_FUT_CME_20251002.jsonl
                    parts = file.name.split('_')
                    if len(parts) >= 6:
                        # Reconstituer le symbole complet (ignorer le préfixe "quote")
                        # parts[0] = "chart", parts[1] = "9", parts[2] = "quote", parts[3] = "NQZ25", etc.
                        symbol = f"{parts[3]}_{parts[4]}_{parts[5].split('.')[0]}"
                        symbols.append(symbol)
        
        return list(set(symbols))  # Dédupliquer
