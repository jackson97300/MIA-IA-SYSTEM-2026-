# -*- coding: utf-8 -*-
"""
CORRELATION FILTER ES/NQ
========================
Filtre les trades quand ES et NQ sont décorrélés.
Méthode: Pearson correlation sur rolling window.

Créé: 08/12/2025
Version: 1.0 (BACKTEST - Non intégré en prod)
"""

from collections import deque
from typing import Tuple, Optional, Dict, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CorrelationFilter:
    """
    Filtre les trades quand ES/NQ sont décorrélés.

    Principe:
    - ES et NQ sont naturellement corrélés à ~90%
    - Quand ils divergent → marché confus → éviter les trades
    - Utilise Pearson correlation sur les returns (variations de prix)

    Usage:
        filter = CorrelationFilter(window=30, min_correlation=0.50)

        # À chaque tick
        filter.update('ES', es_price)
        filter.update('NQ', nq_price)

        # Avant de trader
        can_trade, reason, corr = filter.should_trade('ES')
    """

    def __init__(self, window: int = 30, min_correlation: float = 0.50):
        """
        Args:
            window: Nombre de ticks pour le calcul (default: 30 ~30s)
            min_correlation: Seuil minimum pour autoriser le trade (default: 0.50)
        """
        self.window = window
        self.min_correlation = min_correlation

        # Buffers de prix
        self.es_prices: deque = deque(maxlen=window)
        self.nq_prices: deque = deque(maxlen=window)

        # Cache
        self.last_correlation: float = 1.0
        self.last_es_price: Optional[float] = None
        self.last_nq_price: Optional[float] = None

        # Stats
        self.stats = {
            'total_checks': 0,
            'blocks': 0,
            'allows': 0,
            'min_correlation_seen': 1.0,
            'max_correlation_seen': -1.0,
            'correlation_history': []
        }

        logger.info(f"🔄 CorrelationFilter initialisé (window={window}, min_corr={min_correlation})")

    def update(self, symbol: str, price: float) -> None:
        """
        Met à jour le buffer de prix pour un symbole.
        Appelé à CHAQUE tick, même sans signal.

        Args:
            symbol: 'ES' ou 'NQ'
            price: Prix mid actuel
        """
        if symbol.upper() == 'ES':
            # Éviter les doublons
            if self.last_es_price != price:
                self.es_prices.append(price)
                self.last_es_price = price
        elif symbol.upper() == 'NQ':
            if self.last_nq_price != price:
                self.nq_prices.append(price)
                self.last_nq_price = price

    def calculate_correlation(self) -> float:
        """
        Calcule la corrélation Pearson sur les returns.

        Returns:
            Corrélation entre -1 et +1 (1.0 si pas assez de données)
        """
        min_samples = max(15, self.window // 2)

        # Pas assez de données
        if len(self.es_prices) < min_samples or len(self.nq_prices) < min_samples:
            return 1.0  # Assume aligné

        # Convertir en numpy arrays
        es = np.array(list(self.es_prices))
        nq = np.array(list(self.nq_prices))

        # Aligner les longueurs
        min_len = min(len(es), len(nq))
        es = es[-min_len:]
        nq = nq[-min_len:]

        # Calculer les returns (variations)
        es_ret = np.diff(es)
        nq_ret = np.diff(nq)

        # Éviter division par zéro (marché flat)
        if np.std(es_ret) == 0 or np.std(nq_ret) == 0:
            return 1.0  # Marché flat → OK pour trader

        # Corrélation Pearson
        try:
            corr = np.corrcoef(es_ret, nq_ret)[0, 1]

            if np.isnan(corr):
                corr = 1.0

            self.last_correlation = corr

            # Update stats
            self.stats['min_correlation_seen'] = min(self.stats['min_correlation_seen'], corr)
            self.stats['max_correlation_seen'] = max(self.stats['max_correlation_seen'], corr)

            return corr

        except Exception as e:
            logger.warning(f"⚠️ Erreur calcul corrélation: {e}")
            return 1.0

    def should_trade(self, symbol: str) -> Tuple[bool, str, float]:
        """
        Décide si on peut trader basé sur la corrélation ES/NQ.

        Args:
            symbol: Symbole qu'on veut trader ('ES' ou 'NQ')

        Returns:
            (can_trade, reason, correlation_value)
        """
        self.stats['total_checks'] += 1

        corr = self.calculate_correlation()

        # Stocker pour analyse
        self.stats['correlation_history'].append(corr)

        if corr < self.min_correlation:
            self.stats['blocks'] += 1
            reason = f"⚠️ ES/NQ décorrélés (r={corr:.3f} < {self.min_correlation})"
            logger.info(f"🔄 CORRELATION BLOCK [{symbol}]: {reason}")
            return (False, reason, corr)

        self.stats['allows'] += 1
        reason = f"✅ ES/NQ alignés (r={corr:.3f})"
        return (True, reason, corr)

    def get_stats(self) -> Dict:
        """Retourne les statistiques du filtre"""
        total = self.stats['total_checks']
        return {
            'total_checks': total,
            'blocks': self.stats['blocks'],
            'allows': self.stats['allows'],
            'block_rate': self.stats['blocks'] / total if total > 0 else 0,
            'min_correlation': self.stats['min_correlation_seen'],
            'max_correlation': self.stats['max_correlation_seen'],
            'avg_correlation': np.mean(self.stats['correlation_history']) if self.stats['correlation_history'] else 0,
            'current_correlation': self.last_correlation
        }

    def reset(self) -> None:
        """Reset les buffers (utile pour nouvelle session)"""
        self.es_prices.clear()
        self.nq_prices.clear()
        self.last_correlation = 1.0
        self.last_es_price = None
        self.last_nq_price = None
        logger.info("🔄 CorrelationFilter reset")


# ============================================================================
# FONCTIONS UTILITAIRES POUR BACKTEST
# ============================================================================

def backtest_correlation_filter(
    es_data: List[Dict],
    nq_data: List[Dict],
    signals: List[Dict],
    min_correlation: float = 0.50,
    window: int = 30
) -> Dict:
    """
    Backteste le filtre de corrélation sur des données historiques.

    Args:
        es_data: Liste de snapshots ES [{'t_ms': ..., 'mid': ...}, ...]
        nq_data: Liste de snapshots NQ [{'t_ms': ..., 'mid': ...}, ...]
        signals: Liste de signaux [{'t_ms': ..., 'symbol': ..., 'direction': ..., 'pnl': ...}, ...]
        min_correlation: Seuil de corrélation
        window: Taille de la fenêtre

    Returns:
        Résultats du backtest
    """
    filter_obj = CorrelationFilter(window=window, min_correlation=min_correlation)

    results = {
        'total_signals': len(signals),
        'blocked_signals': 0,
        'allowed_signals': 0,
        'blocked_would_win': 0,
        'blocked_would_lose': 0,
        'allowed_won': 0,
        'allowed_lost': 0,
        'blocked_details': [],
        'correlation_at_signals': []
    }

    # Index pour parcourir les données
    es_idx = 0
    nq_idx = 0

    for signal in signals:
        signal_time = signal.get('t_ms', 0)

        # Alimenter le filtre avec les données jusqu'à ce signal
        while es_idx < len(es_data) and es_data[es_idx].get('t_ms', 0) <= signal_time:
            filter_obj.update('ES', es_data[es_idx].get('mid', 0))
            es_idx += 1

        while nq_idx < len(nq_data) and nq_data[nq_idx].get('t_ms', 0) <= signal_time:
            filter_obj.update('NQ', nq_data[nq_idx].get('mid', 0))
            nq_idx += 1

        # Vérifier la corrélation
        can_trade, reason, corr = filter_obj.should_trade(signal.get('symbol', 'ES'))

        results['correlation_at_signals'].append(corr)

        pnl = signal.get('pnl', 0)
        is_winner = pnl > 0

        if can_trade:
            results['allowed_signals'] += 1
            if is_winner:
                results['allowed_won'] += 1
            else:
                results['allowed_lost'] += 1
        else:
            results['blocked_signals'] += 1
            if is_winner:
                results['blocked_would_win'] += 1
            else:
                results['blocked_would_lose'] += 1

            results['blocked_details'].append({
                'time': signal_time,
                'symbol': signal.get('symbol'),
                'direction': signal.get('direction'),
                'correlation': corr,
                'would_have_pnl': pnl
            })

    # Calculer les métriques
    if results['allowed_signals'] > 0:
        results['allowed_win_rate'] = results['allowed_won'] / results['allowed_signals']
    else:
        results['allowed_win_rate'] = 0

    if results['blocked_signals'] > 0:
        results['blocked_would_have_win_rate'] = results['blocked_would_win'] / results['blocked_signals']
    else:
        results['blocked_would_have_win_rate'] = 0

    results['avg_correlation'] = np.mean(results['correlation_at_signals']) if results['correlation_at_signals'] else 0

    return results



















