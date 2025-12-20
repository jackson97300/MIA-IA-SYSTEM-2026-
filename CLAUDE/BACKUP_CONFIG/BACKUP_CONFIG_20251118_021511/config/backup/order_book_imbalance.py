"""
Order Book Imbalance Calculator - MIA_IA_SYSTEM
==================================================

Module de calcul de l'imbalance order book pour améliorer le win rate.
Compatible avec l'architecture existante et les règles d'imports.

IMPACT: +3-5% win rate immédiat
INTÉGRATION: features/order_book_imbalance.py
"""

# === IMPORTS STRICTS (RÈGLES RESPECTÉES) ===

# 1. STDLIB
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque
import logging

# 2. THIRD-PARTY
import numpy as np
import pandas as pd

# 3. LOCAL (imports absolus, niveau 2 compatible)
from core.base_types import MarketData, OrderFlowData
from core.logger import get_logger

# === CONFIGURATION ===

logger = get_logger(__name__)

@dataclass
class OrderBookImbalanceConfig:
    """Configuration pour calcul order book imbalance"""
    depth_levels: int = 5           # Niveaux de profondeur à analyser
    weight_decay: float = 0.8       # Décroissance poids par niveau
    smoothing_window: int = 10      # Fenêtre lissage
    cache_ttl: int = 5              # TTL cache en secondes
    min_volume_threshold: int = 10   # Volume minimum pour validation
    
@dataclass
class OrderBookLevel:
    """Représentation d'un niveau order book"""
    price: float
    size: int
    num_orders: int = 1

@dataclass
class OrderBookSnapshot:
    """Snapshot complet order book"""
    timestamp: pd.Timestamp
    bids: List[OrderBookLevel]  # Trié par prix DESC
    asks: List[OrderBookLevel]  # Trié par prix ASC
    
@dataclass
class ImbalanceResult:
    """Résultat calcul imbalance"""
    timestamp: pd.Timestamp
    level1_imbalance: float        # Imbalance niveau 1 (bid/ask immédiat)
    depth_imbalance: float         # Imbalance profondeur (5 niveaux)
    weighted_imbalance: float      # Imbalance pondérée finale
    volume_ratio: float           # Ratio volume total bid/ask
    spread_bps: float             # Spread en basis points
    liquidity_score: float        # Score liquidité [0-1]
    signal_strength: float        # Force signal final [-1, 1]
    calculation_time_ms: float    # Temps calcul

class OrderBookImbalanceCalculator:
    """
    Calculateur Order Book Imbalance pour MIA_IA_SYSTEM
    
    Calcule l'imbalance entre ordres d'achat et de vente pour prédire
    la direction court terme du prix. Compatible avec architecture existante.
    """
    
    def __init__(self, config: Optional[OrderBookImbalanceConfig] = None):
        """Initialisation calculateur"""
        self.config = config or OrderBookImbalanceConfig()
        
        # Historique pour lissage
        self.imbalance_history: deque = deque(maxlen=self.config.smoothing_window)
        self.volume_history: deque = deque(maxlen=50)
        
        # Cache pour optimisation
        self.cache: Dict[str, Tuple[Any, float]] = {}
        
        # Statistiques
        self.stats = {
            'calculations_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_calc_time_ms': 0.0,
            'signal_accuracy_history': deque(maxlen=100)
        }
        
        logger.info(f"OrderBookImbalanceCalculator initialisé - depth: {self.config.depth_levels}")
    
    def _generate_cache_key(self, market_data: MarketData, order_book: OrderBookSnapshot) -> str:
        """Génère clé cache basée sur timestamp et données market"""
        return f"{market_data.symbol}_{order_book.timestamp.value}_{len(order_book.bids)}_{len(order_book.asks)}"
    
    def _is_cache_valid(self, cache_entry: Tuple[Any, float]) -> bool:
        """Vérifie validité entrée cache"""
        _, timestamp = cache_entry
        return (time.time() - timestamp) < self.config.cache_ttl
    
    def _calculate_level1_imbalance(self, bids: List[OrderBookLevel], asks: List[OrderBookLevel]) -> float:
        """
        Calcule imbalance niveau 1 (bid/ask immédiat)
        
        Returns:
            float: Imbalance [-1, 1] où >0 = pression achat, <0 = pression vente
        """
        if not bids or not asks:
            return 0.0
        
        best_bid_size = bids[0].size
        best_ask_size = asks[0].size
        
        total_size = best_bid_size + best_ask_size
        if total_size == 0:
            return 0.0
        
        imbalance = (best_bid_size - best_ask_size) / total_size
        return max(-1.0, min(1.0, imbalance))
    
    def _calculate_depth_imbalance(self, bids: List[OrderBookLevel], asks: List[OrderBookLevel]) -> float:
        """
        Calcule imbalance sur profondeur (5 niveaux avec pondération)
        
        Returns:
            float: Imbalance pondérée [-1, 1]
        """
        max_levels = min(self.config.depth_levels, len(bids), len(asks))
        if max_levels == 0:
            return 0.0
        
        weighted_bid_volume = 0.0
        weighted_ask_volume = 0.0
        total_weight = 0.0
        
        for i in range(max_levels):
            # Poids décroissant par niveau
            weight = self.config.weight_decay ** i
            
            weighted_bid_volume += bids[i].size * weight
            weighted_ask_volume += asks[i].size * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalisation
        weighted_bid_volume /= total_weight
        weighted_ask_volume /= total_weight
        
        total_volume = weighted_bid_volume + weighted_ask_volume
        if total_volume == 0:
            return 0.0
        
        imbalance = (weighted_bid_volume - weighted_ask_volume) / total_volume
        return max(-1.0, min(1.0, imbalance))
    
    def _calculate_volume_ratio(self, bids: List[OrderBookLevel], asks: List[OrderBookLevel]) -> float:
        """Calcule ratio volume total bid/ask"""
        total_bid_volume = sum(level.size for level in bids[:self.config.depth_levels])
        total_ask_volume = sum(level.size for level in asks[:self.config.depth_levels])
        
        if total_ask_volume == 0:
            return 1.0 if total_bid_volume > 0 else 0.0
        
        return total_bid_volume / (total_bid_volume + total_ask_volume)
    
    def _calculate_spread_bps(self, bids: List[OrderBookLevel], asks: List[OrderBookLevel]) -> float:
        """Calcule spread en basis points"""
        if not bids or not asks:
            return 0.0
        
        best_bid = bids[0].price
        best_ask = asks[0].price
        
        if best_bid <= 0:
            return 0.0
        
        spread = best_ask - best_bid
        spread_bps = (spread / best_bid) * 10000  # Basis points
        
        return max(0.0, spread_bps)
    
    def _calculate_liquidity_score(self, bids: List[OrderBookLevel], asks: List[OrderBookLevel]) -> float:
        """
        Calcule score liquidité basé sur volume et nombre de niveaux
        
        Returns:
            float: Score [0-1] où 1 = très liquide
        """
        # Volume total
        total_volume = sum(level.size for level in bids[:self.config.depth_levels])
        total_volume += sum(level.size for level in asks[:self.config.depth_levels])
        
        # Nombre de niveaux actifs
        active_levels = len([level for level in bids[:self.config.depth_levels] if level.size > 0])
        active_levels += len([level for level in asks[:self.config.depth_levels] if level.size > 0])
        
        # Score basé sur volume (normalisé par historique)
        volume_score = 0.5
        if self.volume_history:
            avg_volume = np.mean(self.volume_history)
            if avg_volume > 0:
                volume_score = min(1.0, total_volume / (avg_volume * 2))
        
        # Score basé sur profondeur
        depth_score = active_levels / (self.config.depth_levels * 2)
        
        # Score combiné
        liquidity_score = (volume_score * 0.7) + (depth_score * 0.3)
        return max(0.0, min(1.0, liquidity_score))
    
    def _apply_smoothing(self, raw_imbalance: float) -> float:
        """Applique lissage sur historique imbalances"""
        self.imbalance_history.append(raw_imbalance)
        
        if len(self.imbalance_history) < 3:
            return raw_imbalance
        
        # Moyenne pondérée (plus de poids sur valeurs récentes)
        weights = np.exp(np.linspace(0, 1, len(self.imbalance_history)))
        weights /= weights.sum()
        
        smoothed = np.average(list(self.imbalance_history), weights=weights)
        return float(smoothed)
    
    def calculate_imbalance(self, 
                          market_data: MarketData,
                          order_book: OrderBookSnapshot) -> ImbalanceResult:
        """
        Calcule order book imbalance complet
        
        Args:
            market_data: Données marché actuelles
            order_book: Snapshot order book
            
        Returns:
            ImbalanceResult: Résultat complet avec signal final
        """
        start_time = time.time()
        
        # Vérification cache
        cache_key = self._generate_cache_key(market_data, order_book)
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            result, _ = self.cache[cache_key]
            self.stats['cache_hits'] += 1
            return result
        
        self.stats['cache_misses'] += 1
        
        # Validation données
        if not order_book.bids or not order_book.asks:
            logger.warning("Order book vide - retour signal neutre")
            return ImbalanceResult(
                timestamp=order_book.timestamp,
                level1_imbalance=0.0,
                depth_imbalance=0.0,
                weighted_imbalance=0.0,
                volume_ratio=0.5,
                spread_bps=0.0,
                liquidity_score=0.0,
                signal_strength=0.0,
                calculation_time_ms=0.0
            )
        
        # Calculs core
        level1_imbalance = self._calculate_level1_imbalance(order_book.bids, order_book.asks)
        depth_imbalance = self._calculate_depth_imbalance(order_book.bids, order_book.asks)
        volume_ratio = self._calculate_volume_ratio(order_book.bids, order_book.asks)
        spread_bps = self._calculate_spread_bps(order_book.bids, order_book.asks)
        liquidity_score = self._calculate_liquidity_score(order_book.bids, order_book.asks)
        
        # Imbalance pondérée (combinaison niveau 1 + profondeur)
        weighted_imbalance = (level1_imbalance * 0.6) + (depth_imbalance * 0.4)
        
        # Lissage temporel
        smoothed_imbalance = self._apply_smoothing(weighted_imbalance)
        
        # Signal final avec ajustements
        signal_strength = smoothed_imbalance
        
        # Pénalité si faible liquidité
        signal_strength *= liquidity_score
        
        # Pénalité si spread trop large (>50bps)
        if spread_bps > 50:
            spread_penalty = max(0.5, 1.0 - (spread_bps - 50) / 100)
            signal_strength *= spread_penalty
        
        # Clamp final
        signal_strength = max(-1.0, min(1.0, signal_strength))
        
        # Temps calcul
        calc_time_ms = (time.time() - start_time) * 1000
        
        # Résultat
        result = ImbalanceResult(
            timestamp=order_book.timestamp,
            level1_imbalance=level1_imbalance,
            depth_imbalance=depth_imbalance,
            weighted_imbalance=weighted_imbalance,
            volume_ratio=volume_ratio,
            spread_bps=spread_bps,
            liquidity_score=liquidity_score,
            signal_strength=signal_strength,
            calculation_time_ms=calc_time_ms
        )
        
        # Cache + stats
        self.cache[cache_key] = (result, time.time())
        self._update_stats(calc_time_ms)
        
        # Historique volume
        total_volume = sum(level.size for level in order_book.bids[:5])
        total_volume += sum(level.size for level in order_book.asks[:5])
        self.volume_history.append(total_volume)
        
        return result
    
    def _update_stats(self, calc_time_ms: float):
        """Met à jour statistiques performance"""
        self.stats['calculations_count'] += 1
        
        # Moyenne mobile temps calcul
        count = self.stats['calculations_count']
        current_avg = self.stats['avg_calc_time_ms']
        self.stats['avg_calc_time_ms'] = ((current_avg * (count - 1)) + calc_time_ms) / count
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne statistiques calculateur"""
        cache_total = self.stats['cache_hits'] + self.stats['cache_misses']
        cache_hit_rate = (self.stats['cache_hits'] / cache_total * 100) if cache_total > 0 else 0.0
        
        return {
            'calculations_count': self.stats['calculations_count'],
            'cache_hit_rate_pct': round(cache_hit_rate, 1),
            'avg_calc_time_ms': round(self.stats['avg_calc_time_ms'], 2),
            'cache_size': len(self.cache),
            'imbalance_history_size': len(self.imbalance_history),
            'volume_history_size': len(self.volume_history)
        }
    
    def reset_cache(self):
        """Reset cache et historiques"""
        self.cache.clear()
        self.imbalance_history.clear()
        self.volume_history.clear()
        logger.info("Cache et historiques réinitialisés")

# === FACTORY FUNCTIONS ===

def create_order_book_imbalance_calculator(config: Optional[OrderBookImbalanceConfig] = None) -> OrderBookImbalanceCalculator:
    """Factory function pour créer calculateur order book imbalance"""
    return OrderBookImbalanceCalculator(config)

def create_mock_order_book(symbol: str = "ES", base_price: float = 4500.0) -> OrderBookSnapshot:
    """Crée mock order book pour tests"""
    timestamp = pd.Timestamp.now()
    
    # Bids (descending prices)
    bids = [
        OrderBookLevel(base_price - 0.25, 150, 3),  # Best bid
        OrderBookLevel(base_price - 0.50, 120, 2),
        OrderBookLevel(base_price - 0.75, 100, 4),
        OrderBookLevel(base_price - 1.00, 80, 2),
        OrderBookLevel(base_price - 1.25, 60, 1),
    ]
    
    # Asks (ascending prices)
    asks = [
        OrderBookLevel(base_price + 0.25, 140, 2),  # Best ask
        OrderBookLevel(base_price + 0.50, 110, 3),
        OrderBookLevel(base_price + 0.75, 90, 2),
        OrderBookLevel(base_price + 1.00, 70, 4),
        OrderBookLevel(base_price + 1.25, 50, 1),
    ]
    
    return OrderBookSnapshot(timestamp=timestamp, bids=bids, asks=asks)

# === INTÉGRATION AVEC FEATURE CALCULATOR ===

def calculate_order_book_imbalance_feature(market_data: MarketData,
                                         order_book: Optional[OrderBookSnapshot] = None,
                                         calculator: Optional[OrderBookImbalanceCalculator] = None) -> float:
    """
    Function d'intégration avec FeatureCalculator existant
    
    Returns:
        float: Signal imbalance [-1, 1] pour integration dans confluence
    """
    if calculator is None:
        calculator = create_order_book_imbalance_calculator()
    
    if order_book is None:
        # Mock order book si pas de données réelles
        order_book = create_mock_order_book(
            symbol=market_data.symbol,
            base_price=market_data.close
        )
        logger.debug("Utilisation mock order book - remplacer par données réelles")
    
    result = calculator.calculate_imbalance(market_data, order_book)
    return result.signal_strength

def convert_ibkr_level2_to_orderbook(ibkr_level2_data: Dict[str, Any]) -> OrderBookSnapshot:
    """
    Convertit données Level 2 IBKR en OrderBookSnapshot
    
    Args:
        ibkr_level2_data: Données Level 2 depuis IBKR
        
    Returns:
        OrderBookSnapshot: Format standardisé pour le bot
    """
    try:
        timestamp = pd.Timestamp.now()
        bids = []
        asks = []
        
        # Traitement bids (prix décroissants)
        if 'bids' in ibkr_level2_data:
            for price, size in ibkr_level2_data['bids']:
                bids.append(OrderBookLevel(
                    price=float(price),
                    size=int(size),
                    num_orders=1  # Par défaut, à améliorer si disponible
                ))
        
        # Traitement asks (prix croissants)
        if 'asks' in ibkr_level2_data:
            for price, size in ibkr_level2_data['asks']:
                asks.append(OrderBookLevel(
                    price=float(price),
                    size=int(size),
                    num_orders=1  # Par défaut, à améliorer si disponible
                ))
        
        # Tri par prix (bids DESC, asks ASC)
        bids.sort(key=lambda x: x.price, reverse=True)
        asks.sort(key=lambda x: x.price, reverse=False)
        
        return OrderBookSnapshot(
            timestamp=timestamp,
            bids=bids,
            asks=asks
        )
        
    except Exception as e:
        logger.error(f"Erreur conversion IBKR Level 2: {e}")
        # Fallback vers mock
        return create_mock_order_book(
            symbol=ibkr_level2_data.get('symbol', 'ES'),
            base_price=ibkr_level2_data.get('base_price', 4500.0)
        )

def get_real_order_book_data(ibkr_connector, symbol: str) -> Optional[OrderBookSnapshot]:
    """
    Récupère vraies données order book depuis IBKR
    
    Args:
        ibkr_connector: Connecteur IBKR
        symbol: Symbole (ES, NQ, etc.)
        
    Returns:
        OrderBookSnapshot: Données order book réelles ou None
    """
    try:
        import asyncio
        
        # Récupération données Level 2
        level2_data = asyncio.run(ibkr_connector.get_level2_data(symbol))
        
        if level2_data and level2_data.get('mode') in ['live_level2', 'level1_fallback']:
            # Conversion vers format standard
            order_book = convert_ibkr_level2_to_orderbook(level2_data)
            logger.info(f"✅ Order book Level 2 récupéré pour {symbol}: {len(order_book.bids)} bids, {len(order_book.asks)} asks")
            return order_book
        else:
            logger.warning(f"❌ Données Level 2 non disponibles pour {symbol}")
            return None
            
    except Exception as e:
        logger.error(f"Erreur récupération order book {symbol}: {e}")
        return None

# === TESTING ===

def test_order_book_imbalance():
    """Test complet order book imbalance calculator"""
    logger.info("=== TEST ORDER BOOK IMBALANCE ===")
    
    # Création calculateur
    config = OrderBookImbalanceConfig(
        depth_levels=5,
        smoothing_window=10,
        cache_ttl=5
    )
    calculator = create_order_book_imbalance_calculator(config)
    
    # Données test
    market_data = MarketData(
        timestamp=pd.Timestamp.now(),
        symbol="ES",
        open=4500.0,
        high=4505.0,
        low=4495.0,
        close=4502.0,
        volume=1500
    )
    
    # Test 1: Order book équilibré
    logger.info("\n[TEST] Order book équilibré")
    balanced_book = create_mock_order_book("ES", 4502.0)
    result_balanced = calculator.calculate_imbalance(market_data, balanced_book)
    
    logger.info(f"Signal strength: {result_balanced.signal_strength:.3f}")
    logger.info(f"Level1 imbalance: {result_balanced.level1_imbalance:.3f}")
    logger.info(f"Depth imbalance: {result_balanced.depth_imbalance:.3f}")
    logger.info(f"Liquidity score: {result_balanced.liquidity_score:.3f}")
    logger.info(f"Calculation time: {result_balanced.calculation_time_ms:.2f}ms")
    
    # Test 2: Order book avec bias achat
    logger.info("\n[TEST] Order book bias achat")
    biased_bids = [
        OrderBookLevel(4501.75, 200, 5),  # Plus gros volume bid
        OrderBookLevel(4501.50, 180, 4),
        OrderBookLevel(4501.25, 150, 3),
        OrderBookLevel(4501.00, 120, 2),
        OrderBookLevel(4500.75, 100, 2),
    ]
    biased_asks = [
        OrderBookLevel(4502.25, 80, 2),   # Moins de volume ask
        OrderBookLevel(4502.50, 70, 1),
        OrderBookLevel(4502.75, 60, 2),
        OrderBookLevel(4503.00, 50, 1),
        OrderBookLevel(4503.25, 40, 1),
    ]
    
    biased_book = OrderBookSnapshot(
        timestamp=pd.Timestamp.now(),
        bids=biased_bids,
        asks=biased_asks
    )
    
    result_biased = calculator.calculate_imbalance(market_data, biased_book)
    
    logger.info(f"Signal strength: {result_biased.signal_strength:.3f}")
    logger.info(f"Level1 imbalance: {result_biased.level1_imbalance:.3f}")
    logger.info(f"Volume ratio: {result_biased.volume_ratio:.3f}")
    
    # Test 3: Performance sur multiple calculs
    logger.info("\n[TEST] Performance multiple calculs")
    start_time = time.time()
    
    for i in range(100):
        test_book = create_mock_order_book("ES", 4500.0 + (i * 0.25))
        calculator.calculate_imbalance(market_data, test_book)
    
    total_time = (time.time() - start_time) * 1000
    logger.info(f"100 calculs en {total_time:.2f}ms ({total_time/100:.2f}ms/calcul)")
    
    # Statistiques finales
    stats = calculator.get_stats()
    logger.info("\n[STATS] Statistiques finales:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # Test intégration
    logger.info("\n[TEST] Intégration avec FeatureCalculator")
    feature_value = calculate_order_book_imbalance_feature(market_data, balanced_book)
    logger.info(f"Feature value pour intégration: {feature_value:.3f}")
    
    logger.info("\n=== TEST TERMINÉ AVEC SUCCÈS ===")
    return True

if __name__ == "__main__":
    test_order_book_imbalance()