"""
MIA_IA_SYSTEM - OrderFlow Advanced Implementation
Version: 1.0 Elite - Production Ready

Implémentation OrderFlow avancé avec :
- Volume Imbalance directionnel
- Delta Momentum avec ATR réel
- Normalisation par volume
- Support multi-symboles

Performance: <5ms, intégration temps réel
"""

import math
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

# === PROTECTION DIVISION PAR ZÉRO ===
EPS = 1e-9

def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    """Division sécurisée avec protection contre division par zéro"""
    return num / den if abs(den) > EPS else default

def _norm_tanh(x: float, scale: float, clip: float = 3.0) -> float:
    """Normalisation tanh avec clamp pour éviter l'écrasement des scores"""
    if scale is None or scale <= 0:
        return 0.0
    z = x / scale
    # Anti-outliers
    if z > clip: 
        z = clip
    elif z < -clip: 
        z = -clip
    # Map [-clip, clip] -> [0,1] via tanh
    return 0.5 * (math.tanh(z) + 1.0)

def _volume_imbalance(buy_vol: float, sell_vol: float) -> float:
    """Calcul d'imbalance de volume sécurisé"""
    den = buy_vol + sell_vol
    return _safe_div(buy_vol - sell_vol, den, 0.0)

def _delta_momentum(curr_cum_delta: float, prev_cum_delta: float) -> float:
    """Calcul de momentum delta sécurisé"""
    base = max(abs(prev_cum_delta), 1.0)
    return (curr_cum_delta - prev_cum_delta) / base

def _real_atr(atr_high, atr_low, atr_close, tick_size: float) -> float:
    """Calcul ATR réel avec fallback sécurisé"""
    if not atr_high or not atr_low or not atr_close:
        logger.debug(f"🔍 ATR fallback: high={len(atr_high) if atr_high else 0}, low={len(atr_low) if atr_low else 0}, close={len(atr_close) if atr_close else 0}")
        return max(tick_size, 1.0 * tick_size)
    n = min(len(atr_high), len(atr_low), len(atr_close))
    if n == 0:
        return max(tick_size, 1.0 * tick_size)
    trs = []
    prev_close = atr_close[0]
    for i in range(n):
        h, l, c = atr_high[i], atr_low[i], atr_close[i]
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    atr = sum(trs) / max(len(trs), 1)
    return max(atr, tick_size)

# === CONFIGURATION ORDERFLOW ADVANCED ===

# Configuration tick_size par symbole
TICK_SIZE_CONFIG = {
    'ES': 0.25,    # E-mini S&P 500
    'NQ': 0.25,    # E-mini NASDAQ
    'YM': 1.0,     # E-mini Dow
    'RTY': 0.1,    # E-mini Russell
    'GC': 0.1,     # Gold
    'CL': 0.01     # Crude Oil
}

# === DATACLASSES ===

@dataclass
class OrderFlowAdvancedResult:
    """Résultat OrderFlow avancé complet"""
    of_score: float
    volume_imbalance: Dict[str, Any]
    delta_momentum: Dict[str, Any]
    calculation_time_ms: float
    timestamp: datetime

@dataclass
class VolumeImbalanceResult:
    """Résultat Volume Imbalance"""
    magnitude: float
    direction: int
    direction_ok: bool
    score: float

@dataclass
class DeltaMomentumResult:
    """Résultat Delta Momentum"""
    slope: float
    normalized_slope: float
    volume_norm: float
    atr_used: float
    score: float

# === UTILITAIRES ===

def calculate_real_atr(price_data: Dict[str, List[float]], period: int = 14) -> float:
    """Calcul ATR réel sur 14 ou 20 barres"""
    if not price_data or len(price_data.get('high', [])) < period:
        return 0.0
    
    high = np.array(price_data['high'][-period:])
    low = np.array(price_data['low'][-period:])
    close = np.array(price_data['close'][-period:])
    
    # True Range
    tr1 = high - low
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    
    # True Range complet
    tr = np.maximum(tr1[1:], np.maximum(tr2, tr3))
    
    # ATR = moyenne mobile du True Range
    atr = np.mean(tr)
    
    return float(atr) if not np.isnan(atr) else 0.0

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp une valeur entre lo et hi"""
    return max(lo, min(hi, x))

# === CLASSE PRINCIPALE ORDERFLOW ADVANCED ===

class OrderFlowAdvanced:
    """
    OrderFlow Avancé - Implémentation réelle
    
    Composants :
    1. Volume Imbalance (55%) - Direction + magnitude
    2. Delta Momentum (45%) - VRAI momentum avec ATR réel
    """
    
    def __init__(self):
        """Initialisation OrderFlow Advanced"""
        self.tick_size_config = TICK_SIZE_CONFIG
        logger.info("📊 OrderFlow Advanced initialisé - ATR réel + direction")
    
    def calculate_orderflow_advanced(self, trade_summary_data: Dict[str, Any], 
                                   trade_summary_history: List[Dict[str, Any]], 
                                   symbol: str, intended_direction: int, 
                                   atr_data: Dict[str, Any] = None) -> OrderFlowAdvancedResult:
        """
        Calcul du score OrderFlow avancé avec ATR réel
        
        Args:
            trade_summary_data: Données trade summary actuelles
            trade_summary_history: Historique des trade summaries
            symbol: Symbole (ES, NQ, YM, etc.)
            intended_direction: Direction voulue (1=Long, -1=Short)
            atr_data: Données ATR pour normalisation
        
        Returns:
            OrderFlowAdvancedResult complet
        """
        start_time = datetime.now()
        
        try:
            # === VOLUME IMBALANCE AVEC DIRECTION ===
            volume_imbalance = self._calculate_volume_imbalance_directional(
                trade_summary_data, intended_direction
            )
            
            # === DELTA MOMENTUM (VRAI MOMENTUM AVEC ATR RÉEL) ===
            delta_momentum = self._calculate_delta_momentum_true(
                trade_summary_history, symbol, atr_data
            )
            
            # === SCORE FINAL AVEC RESCALING ===
            # Rescaling sigmoïde pour le momentum (éviter les scores trop petits)
            import math
            momentum_raw = delta_momentum.score
            x = 25.0 * momentum_raw  # gain à ajuster
            momentum_rescaled = 1 / (1 + math.exp(-x))  # sigmoïde 0..1
            
            # Score composite avec plancher
            of_score = 0.55 * volume_imbalance.score + 0.45 * momentum_rescaled
            of_score = max(0.05, of_score)  # plancher pour éviter 0.000x
            try:
                # Déterminer la source de l'ATR
                atr_src = "OHLC" if atr_data and atr_data.get('high') else "fallback"
                tick_size = self.tick_size_config.get(symbol, 0.25)
                atr_ticks = delta_momentum.atr_used / max(tick_size, 1e-9)
                
                logger.info(
                    f"🔎 OF Debug: buy_vol={trade_summary_data.get('buy_vol')} sell_vol={trade_summary_data.get('sell_vol')} "
                    f"buy_trades={trade_summary_data.get('buy_trades')} sell_trades={trade_summary_data.get('sell_trades')} | "
                    f"imb_mag={volume_imbalance.magnitude:.4f} dir={volume_imbalance.direction} dir_ok={volume_imbalance.direction_ok} "
                    f"imb_score={volume_imbalance.score:.4f} | delta_slope={delta_momentum.slope:.6f} "
                    f"norm_slope={delta_momentum.normalized_slope:.6f} atr={delta_momentum.atr_used:.4f} src={atr_src} atr_ticks={atr_ticks:.2f} vol_norm={delta_momentum.volume_norm:.2f} "
                    f"dm_score={delta_momentum.score:.4f} | of_score={of_score:.6f}"
                )
            except Exception:
                pass
            
            # === CALCUL TEMPS ===
            calc_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return OrderFlowAdvancedResult(
                of_score=min(1.0, of_score),
                volume_imbalance={
                    'magnitude': volume_imbalance.magnitude,
                    'direction': volume_imbalance.direction,
                    'direction_ok': volume_imbalance.direction_ok,
                    'score': volume_imbalance.score
                },
                delta_momentum={
                    'slope': delta_momentum.slope,
                    'normalized_slope': delta_momentum.normalized_slope,
                    'volume_norm': delta_momentum.volume_norm,
                    'atr_used': delta_momentum.atr_used,
                    'score': delta_momentum.score
                },
                calculation_time_ms=calc_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur OrderFlow Advanced: {e}")
            return OrderFlowAdvancedResult(
                of_score=0.0, volume_imbalance={}, delta_momentum={}, 
                calculation_time_ms=0.0, timestamp=start_time
            )
    
    # === VOLUME IMBALANCE (55%) ===
    
    def _calculate_volume_imbalance_directional(self, trade_summary_data: Dict[str, Any], 
                                              intended_direction: int) -> VolumeImbalanceResult:
        """
        Calcul du déséquilibre de volume avec direction
        
        Args:
            trade_summary_data: Données trade summary
            intended_direction: Direction voulue (1=Long, -1=Short)
        
        Returns:
            VolumeImbalanceResult
        """
        # ✅ Protection robuste contre données manquantes
        buy_vol = max(trade_summary_data.get('buy_vol', 0), 1.0)  # Minimum 1 pour éviter 0
        sell_vol = max(trade_summary_data.get('sell_vol', 0), 1.0)  # Minimum 1 pour éviter 0
        buy_trades = max(trade_summary_data.get('buy_trades', 0), 1)
        sell_trades = max(trade_summary_data.get('sell_trades', 0), 1)
        
        total_vol = buy_vol + sell_vol
        total_trades = buy_trades + sell_trades
        
        # ✅ Imbalance volume (55% du score)
        imb_vol = _volume_imbalance(buy_vol, sell_vol)
        
        # ✅ Imbalance trades (45% du score) 
        imb_trades = _safe_div(buy_trades - sell_trades, total_trades, 0.0)
        
        # ✅ Score composite robuste
        imb_mag = min(1.0, abs(imb_vol) * 0.55 + abs(imb_trades) * 0.45)
        
        # Direction de l'imbalance (basée sur volume principalement)
        imb_dir = 1 if buy_vol > sell_vol else -1  # +1 bull, -1 bear
        
        # Vérification alignement avec direction voulue
        dir_ok = (imb_dir == intended_direction)
        
        # Score final d'imbalance (magnitude × direction)
        score = 0.7 * imb_mag * (1.0 if dir_ok else 0.0)
        
        return VolumeImbalanceResult(
            magnitude=imb_mag,
            direction=imb_dir,
            direction_ok=dir_ok,
            score=score
        )
    
    # === DELTA MOMENTUM (45%) ===
    
    def _calculate_delta_momentum_true(self, trade_summary_history: List[Dict[str, Any]], 
                                     symbol: str, atr_data: Dict[str, Any] = None) -> DeltaMomentumResult:
        """
        Calcul du VRAI momentum du delta avec ATR réel (14 ou 20 barres)
        
        Args:
            trade_summary_history: Historique des trade summaries
            symbol: Symbole
            atr_data: Données ATR pour normalisation
        
        Returns:
            DeltaMomentumResult
        """
        if len(trade_summary_history) < 5:
            return DeltaMomentumResult(
                slope=0.0, normalized_slope=0.0, volume_norm=1.0, 
                atr_used=0.0, score=0.0
            )
        
        # Récupération des dernières valeurs cum_delta_session
        recent_deltas = [data.get('cum_delta_session', 0) for data in trade_summary_history[-5:]]
        
        # Calcul de la pente (momentum) - version sécurisée
        if len(recent_deltas) >= 2:
            delta_slope = _delta_momentum(recent_deltas[-1], recent_deltas[0])
        else:
            delta_slope = 0.0
        
        # ATR réel si disponible, sinon estimation - version sécurisée
        tick_size = self.tick_size_config.get(symbol, 0.25)
        if atr_data is not None:
            highs = atr_data.get('high', [])
            lows = atr_data.get('low', [])
            closes = atr_data.get('close', [])
            logger.debug(f"🔍 ATR data received: highs={len(highs) if highs else 0}, lows={len(lows) if lows else 0}, closes={len(closes) if closes else 0}")
            real_atr = _real_atr(highs, lows, closes, tick_size)
        else:
            # Fallback vers estimation si pas de données de prix
            logger.debug(f"🔍 ATR data is None, using fallback")
            real_atr = max(tick_size * 10, tick_size)
        
        # ✅ Normalisation par ATR réel × volume - version robuste
        recent_volume = sum([max(data.get('buy_vol', 0), 1) + max(data.get('sell_vol', 0), 1) 
                           for data in trade_summary_history[-5:]])
        volume_norm = max(1, recent_volume / 1000)
        
        # ✅ Normalisation finale avec ATR réel - version tanh + clamp
        # ATR exprimé en ticks pour éviter l'écrasement
        tick_size = self.tick_size_config.get(symbol, 0.25)
        atr_ticks = max(real_atr / max(tick_size, 1e-9), 1.0)  # ATR en ticks
        scale_slope = max(atr_ticks, 8.0) * 1.0  # >= 8 ticks de marge
        
        # Normalisation tanh pour éviter l'écrasement
        norm_slope = _norm_tanh(delta_slope, scale_slope)
        
        # ✅ Score final avec lissage
        score = min(1.0, norm_slope * 0.8)  # Légère réduction pour éviter les scores trop élevés
        
        return DeltaMomentumResult(
            slope=delta_slope,
            normalized_slope=norm_slope,
            volume_norm=volume_norm,
            atr_used=real_atr,
            score=score
        )
    
    # === MÉTHODES UTILITAIRES ===
    
    def get_tick_size(self, symbol: str) -> float:
        """Récupère la taille du tick pour un symbole"""
        return self.tick_size_config.get(symbol, 0.25)
    
    def calculate_imbalance_score(self, imb_mag: float, dir_ok: bool) -> float:
        """Score final d'imbalance (magnitude × direction)"""
        return 0.7 * imb_mag * (1.0 if dir_ok else 0.0)
    
    def calculate_momentum_score(self, slope: float, atr: float, volume_norm: float) -> float:
        """Score final de momentum normalisé"""
        normalized_slope = _safe_div(slope, atr * volume_norm, 0.0)
        return min(1.0, abs(normalized_slope))
    
    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle"""
        return {
            'tick_size_config': self.tick_size_config
        }
    
    def set_config(self, config: Dict[str, Any]):
        """Met à jour la configuration"""
        if 'tick_size_config' in config:
            self.tick_size_config.update(config['tick_size_config'])
        logger.info("📊 Configuration OrderFlow Advanced mise à jour")

# === INSTANCE GLOBALE ===

orderflow_advanced = OrderFlowAdvanced()

# === FONCTIONS DE CONVENIENCE ===

def get_orderflow_advanced() -> OrderFlowAdvanced:
    """Retourne l'instance globale d'OrderFlow Advanced"""
    return orderflow_advanced

def calculate_orderflow_quick(trade_summary_data: Dict[str, Any], 
                            trade_summary_history: List[Dict[str, Any]], 
                            symbol: str, intended_direction: int, 
                            atr_data: Dict[str, Any] = None) -> float:
    """Fonction de convenience pour calcul rapide"""
    result = orderflow_advanced.calculate_orderflow_advanced(
        trade_summary_data, trade_summary_history, symbol, intended_direction, atr_data
    )
    return result.of_score
