#!/usr/bin/env python3
"""
Trailing Stop Manager Module
============================

Gère les trailing stops automatiques (break-even et trailing).

Author: MIA_IA_SYSTEM
Version: 1.1.0 - SYNC (pas de blocage async)
Date: 12 Novembre 2025
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TrailingStopConfig:
    """
    Configuration du trailing stop manager - VERSION PROGRESSIVE 08/12/2025

    🔥 NOUVEAU: Trailing PROGRESSIF au lieu de "tout ou rien"
    Le SL se déplace graduellement pour protéger les profits
    """

    # ═══════════════════════════════════════════════════════════════
    # 🔥 TRAILING PROGRESSIF - Paliers de protection
    # ═══════════════════════════════════════════════════════════════
    # Format: Liste de tuples (profit_trigger, sl_offset)
    # Quand profit >= profit_trigger → SL = entry + sl_offset (LONG) ou entry - sl_offset (SHORT)

    progressive_levels: Dict[str, list] = field(default_factory=lambda: {
        # 🔥 08/12/2025: CONFIG AGRESSIF - Trailing serré pour capturer plus de MFE
        # Backtest: +$211 vs config précédente, MFE capture 97.1%
        'ES': [
            (8, 2),    # +8t profit  → SL à +2t (+$25 garanti) ← BE BUFFER
            (10, 4),   # +10t profit → SL à +4t (+$50 garanti) ← NOUVEAU!
            (12, 6),   # +12t profit → SL à +6t (+$75 garanti) ← NOUVEAU!
            (15, 8),   # +15t profit → SL à +8t (+$100 garanti)
            (20, 12),  # +20t profit → SL à +12t (+$150 garanti)
        ],
        'NQ': [
            (10, 3),   # +10t profit → SL à +3t (+$15 garanti) ← BE BUFFER
            (12, 5),   # +12t profit → SL à +5t (+$25 garanti) ← NOUVEAU!
            (15, 7),   # +15t profit → SL à +7t (+$35 garanti) ← NOUVEAU!
            (18, 10),  # +18t profit → SL à +10t (+$50 garanti)
            (22, 14),  # +22t profit → SL à +14t (+$70 garanti)
        ],
        'RTY': [
            (8, 2),    # +8t profit  → SL à +2t ← BE BUFFER
            (10, 4),   # +10t profit → SL à +4t ← NOUVEAU!
            (12, 6),   # +12t profit → SL à +6t
            (15, 8),   # +15t profit → SL à +8t
            (20, 12),  # +20t profit → SL à +12t
        ]
    })

    # ═══════════════════════════════════════════════════════════════
    # TRAILING CLASSIQUE (après dernier palier progressif)
    # ═══════════════════════════════════════════════════════════════

    # Trailing start (quand démarrer le trailing dynamique après les paliers)
    trailing_start_ticks: Dict[str, int] = field(default_factory=lambda: {
        'ES': 28,   # Trailing dynamique à +28 ticks
        'NQ': 35,   # Trailing dynamique à +35 ticks
        'RTY': 24
    })

    # Trailing distance (distance du prix pour trailing dynamique)
    trailing_distance_ticks: Dict[str, int] = field(default_factory=lambda: {
        'ES': 8,    # Trail à 8 ticks du prix
        'NQ': 10,   # Trail à 10 ticks du prix
        'RTY': 8
    })

    trailing_enabled: bool = False  # 🔴 DÉSACTIVÉ 09/12 - Laisse courir jusqu'au TP
    progressive_enabled: bool = False  # 🔴 DÉSACTIVÉ 09/12 - Distance 6t trop serrée, coupe les winners


class TrailingStopManager:
    """Gestion des trailing stops automatiques - VERSION SIMPLIFIÉE SYNCHRONE"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = TrailingStopConfig()
        if config:
            for key, value in config.items():
                if hasattr(self.config, key):
                    if isinstance(getattr(self.config, key), dict) and isinstance(value, dict):
                        getattr(self.config, key).update(value)
                    else:
                        setattr(self.config, key, value)

        self.active_trailing_stops: Dict[str, Dict[str, Any]] = {}

        # 🔥 VERSION PROGRESSIVE 08/12/2025
        logger.info(f"📈 TrailingStopManager initialisé (VERSION PROGRESSIVE)")
        logger.info(f"   🔥 Mode Progressif: {'ACTIVÉ' if self.config.progressive_enabled else 'DÉSACTIVÉ'}")

        # Afficher les paliers pour NQ
        nq_levels = self.config.progressive_levels.get('NQ', [])
        logger.info(f"   📊 Paliers NQ: {len(nq_levels)} niveaux")
        for i, (trigger, offset) in enumerate(nq_levels):
            profit_garanti = offset * 5  # $5 par tick NQ
            logger.info(f"      Palier {i+1}: +{trigger}t → SL à +{offset}t (+${profit_garanti} garanti)")

        # Afficher les paliers pour ES
        es_levels = self.config.progressive_levels.get('ES', [])
        logger.info(f"   📊 Paliers ES: {len(es_levels)} niveaux")
        for i, (trigger, offset) in enumerate(es_levels):
            profit_garanti = offset * 12.5  # $12.5 par tick ES
            logger.info(f"      Palier {i+1}: +{trigger}t → SL à +{offset}t (+${profit_garanti:.0f} garanti)")

        logger.info(f"   📈 Trailing dynamique: ES @ +{self.config.trailing_start_ticks.get('ES')}t, NQ @ +{self.config.trailing_start_ticks.get('NQ')}t")

    def _get_tick_size(self, symbol: str) -> float:
        """Obtenir le tick size pour un symbole"""
        return 0.25 if symbol in ['ES', 'NQ'] else 0.10

    def calculate_new_stop(self, symbol: str, current_position: Dict[str, Any],
                          current_price: float, atr: float = None) -> Optional[float]:
        """
        Calcule le nouveau stop loss - VERSION PROGRESSIVE 08/12/2025

        🔥 NOUVEAU: Trailing PROGRESSIF
        - Le SL se déplace par paliers pour protéger les profits graduellement
        - Plus de "tout ou rien" - chaque palier de profit verrouille un gain

        Args:
            symbol: ES, NQ, RTY
            current_position: Dict avec entry_price, side, sl_price
            current_price: Prix actuel du marché
            atr: ATR actuel (optionnel)

        Returns:
            Nouveau prix SL ou None si pas de changement
        """
        if not self.config.trailing_enabled or not current_position:
            return None

        try:
            entry_price = current_position['entry_price']
            position_side = current_position['side']
            current_sl = current_position['sl_price']
            tick_size = self._get_tick_size(symbol)
            tick_value = 5.0 if symbol == 'NQ' else 12.5 if symbol == 'ES' else 5.0

            # Initialiser tracking si nécessaire OU si nouveau trade (entry différente)
            # 🔥 FIX 08/12: Réinitialiser si entry_price a changé (nouveau trade!)
            existing = self.active_trailing_stops.get(symbol)
            if not existing or existing.get('entry_price') != entry_price:
                logger.info(f"   🔄 [{symbol}] RESET trailing stop pour nouveau trade (entry={entry_price})")
                self.active_trailing_stops[symbol] = {
                    'entry_price': entry_price,
                    'original_sl': current_sl,
                    'current_sl': current_sl,
                    'current_level': -1,  # 🔥 Niveau progressif actuel
                    'trailing_started': False,
                    'max_profit_ticks': 0.0
                }

            tracked_stop = self.active_trailing_stops[symbol]

            # Calculer profit actuel en ticks
            if position_side == "LONG":
                profit_ticks = (current_price - entry_price) / tick_size
            else:
                profit_ticks = (entry_price - current_price) / tick_size

            # 🔥 DEBUG 08/12: Log profit et paliers
            logger.info(f"🔄 [{symbol}] BE CHECK: profit={profit_ticks:.1f}t, entry={entry_price:.2f}, price={current_price:.2f}, sl={current_sl:.2f}")

            # Mettre à jour max profit
            if profit_ticks > tracked_stop['max_profit_ticks']:
                tracked_stop['max_profit_ticks'] = profit_ticks
                logger.info(f"   📈 Nouveau max profit: {profit_ticks:.1f}t")

            # ═══════════════════════════════════════════════════════════════
            # 🔥 PHASE 1: TRAILING PROGRESSIF PAR PALIERS
            # ═══════════════════════════════════════════════════════════════

            if self.config.progressive_enabled:
                progressive_levels = self.config.progressive_levels.get(symbol, [])

                # Trouver le palier le plus élevé atteint
                best_level_idx = -1
                best_sl_offset = 0

                for idx, (trigger, sl_offset) in enumerate(progressive_levels):
                    if profit_ticks >= trigger:
                        best_level_idx = idx
                        best_sl_offset = sl_offset

                # Si on a atteint un nouveau palier
                if best_level_idx > tracked_stop.get('current_level', -1):
                    # Calculer nouveau SL
                    if position_side == "LONG":
                        new_sl = entry_price + (best_sl_offset * tick_size)
                    else:  # SHORT
                        new_sl = entry_price - (best_sl_offset * tick_size)

                    # Vérifier que c'est une amélioration
                    is_better = (position_side == "LONG" and new_sl > tracked_stop['current_sl']) or \
                                (position_side == "SHORT" and new_sl < tracked_stop['current_sl'])

                    if is_better:
                        profit_garanti = best_sl_offset * tick_value
                        trigger_level = progressive_levels[best_level_idx][0]

                        logger.info(f"   🎯 PROGRESSIF [{symbol}]: +{profit_ticks:.1f}t atteint palier {best_level_idx+1}")
                        logger.info(f"      → SL déplacé: {tracked_stop['current_sl']:.2f} → {new_sl:.2f}")
                        logger.info(f"      → Profit verrouillé: +{best_sl_offset}t (+${profit_garanti:.0f} garanti)")

                        tracked_stop['current_level'] = best_level_idx
                        tracked_stop['current_sl'] = new_sl
                        return new_sl

            # ═══════════════════════════════════════════════════════════════
            # PHASE 2: TRAILING DYNAMIQUE (après les paliers)
            # ═══════════════════════════════════════════════════════════════

            trailing_start = self.config.trailing_start_ticks.get(symbol, 30)
            trailing_distance = self.config.trailing_distance_ticks.get(symbol, 10)

            if profit_ticks >= trailing_start:
                tracked_stop['trailing_started'] = True

                # Calculer nouveau SL avec trailing distance
                if position_side == "LONG":
                    trailing_sl = current_price - (trailing_distance * tick_size)
                else:  # SHORT
                    trailing_sl = current_price + (trailing_distance * tick_size)

                # Appliquer seulement si meilleur que SL actuel
                is_better = (position_side == "LONG" and trailing_sl > tracked_stop['current_sl']) or \
                            (position_side == "SHORT" and trailing_sl < tracked_stop['current_sl'])

                if is_better:
                    if position_side == "LONG":
                        profit_locked = (trailing_sl - entry_price) / tick_size
                    else:
                        profit_locked = (entry_price - trailing_sl) / tick_size

                    logger.info(f"   📈 TRAILING [{symbol}]: +{profit_ticks:.1f}t → SL @ {trailing_sl:.2f} (+{profit_locked:.0f}t verrouillé)")
                    tracked_stop['current_sl'] = trailing_sl
                    return trailing_sl

            return None

        except Exception as e:
            logger.error(f"⚠️ Erreur TrailingStopManager.calculate_new_stop: {e}")
            return None

    def reset_trailing_stop(self, symbol: str):
        """Réinitialiser le trailing stop pour un symbole"""
        if symbol in self.active_trailing_stops:
            del self.active_trailing_stops[symbol]
            logger.info(f"📈 [{symbol}] Trailing Stop réinitialisé.")

    def update(self, symbol: str, direction: str, entry_price: float,
               current_price: float, current_sl: float, current_time: int = None,
               atr: float = None) -> Optional[Dict[str, Any]]:
        """
        Interface simplifiée pour mise à jour trailing stop
        Compatible avec l'appel depuis CleanTradingSystem

        Returns:
            Dict avec new_sl, breakeven_triggered, trailing_activated
            ou None si pas de changement
        """
        # Construire le dict position attendu par calculate_new_stop
        current_position = {
            'entry_price': entry_price,
            'side': direction,  # 'LONG' ou 'SHORT'
            'sl_price': current_sl
        }

        # Calculer nouveau SL
        new_sl = self.calculate_new_stop(symbol, current_position, current_price, atr)

        if new_sl is None:
            return None

        # Déterminer quel type d'update
        tracked = self.active_trailing_stops.get(symbol, {})
        breakeven_triggered = tracked.get('breakeven_reached', False) and not tracked.get('was_breakeven', False)
        trailing_activated = tracked.get('trailing_started', False)

        # Marquer breakeven comme déjà notifié
        if symbol in self.active_trailing_stops:
            self.active_trailing_stops[symbol]['was_breakeven'] = tracked.get('breakeven_reached', False)

        return {
            'new_sl': new_sl,
            'breakeven_triggered': breakeven_triggered,
            'trailing_activated': trailing_activated
        }


def create_trailing_stop_manager(config: Optional[Dict[str, Any]] = None) -> TrailingStopManager:
    """Factory function pour créer un TrailingStopManager"""
    return TrailingStopManager(config)
