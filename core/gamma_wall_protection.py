#!/usr/bin/env python3
"""
Gamma Wall Protection Module
============================

Détecte les rejets de gamma walls et protège les positions ouvertes (VERSION SIMPLIFIÉE).

Author: MIA_IA_SYSTEM
Version: 1.1.0 - SYNC (pas de blocage async)
Date: 12 Novembre 2025
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GammaWallProtector:
    """Protection contre rejets de gamma walls - VERSION SIMPLIFIÉE SYNCHRONE"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {
            'min_distance_ticks': 5,
            'min_drawdown_for_close': 0.3,
            'auto_close_enabled': True,
            'auto_reverse_enabled': False,
            'rejection_candle_min_range': 3,
            'cooldown_seconds': 60
        }
        if config:
            self.config.update(config)
        
        self.last_action_time = datetime.min
        logger.info(f"🛡️ GammaWallProtector initialisé (version sync, pas de blocage)")
    
    def _is_cooldown_active(self) -> bool:
        """Vérifier si le cooldown est actif"""
        elapsed = (datetime.now() - self.last_action_time).total_seconds()
        return elapsed < self.config['cooldown_seconds']
    
    def check_rejection(self, symbol: str, current_position: Dict[str, Any], 
                       tick: Dict[str, Any]) -> Optional[str]:
        """
        Vérifier si position proche d'un gamma wall (VERSION SYNCHRONE - pas de fermeture auto)
        
        Returns:
            str: Action suggérée ("CLOSE_LONG", "CLOSE_SHORT", etc.) ou None
        """
        if not current_position or self._is_cooldown_active():
            return None
        
        try:
            position_side = current_position.get('side')
            entry_price = current_position.get('entry_price')
            sl_price = current_position.get('sl_price')
            tick_size = current_position.get('tick_size', 0.25)
            
            current_price = tick.get('mid', tick.get('close'))
            if not current_price:
                return None
            
            # Calculer P&L en ticks
            if position_side == "LONG":
                pnl_ticks = (current_price - entry_price) / tick_size
            else:
                pnl_ticks = (entry_price - current_price) / tick_size
            
            max_loss_ticks = abs(entry_price - sl_price) / tick_size
            
            # Vérifier Call Resistance pour LONG
            if position_side == "LONG":
                call_resistance = tick.get('call_resistance', 0)
                if call_resistance > 0:
                    dist_to_resistance = abs(current_price - call_resistance) / tick_size
                    
                    if dist_to_resistance <= self.config['min_distance_ticks']:
                        # Proche de résistance
                        if pnl_ticks < 0:
                            drawdown_pct = abs(pnl_ticks) / max_loss_ticks
                            if drawdown_pct >= self.config['min_drawdown_for_close']:
                                logger.warning(
                                    f"🛡️ [{symbol}] ALERTE: Proche Call Resistance {call_resistance:.2f} "
                                    f"({dist_to_resistance:.1f}t) avec drawdown {drawdown_pct:.1%}"
                                )
                                self.last_action_time = datetime.now()
                                return "CLOSE_LONG"
            
            # Vérifier Put Support pour SHORT
            elif position_side == "SHORT":
                put_support = tick.get('put_support', 0)
                if put_support > 0:
                    dist_to_support = abs(current_price - put_support) / tick_size
                    
                    if dist_to_support <= self.config['min_distance_ticks']:
                        if pnl_ticks < 0:
                            drawdown_pct = abs(pnl_ticks) / max_loss_ticks
                            if drawdown_pct >= self.config['min_drawdown_for_close']:
                                logger.warning(
                                    f"🛡️ [{symbol}] ALERTE: Proche Put Support {put_support:.2f} "
                                    f"({dist_to_support:.1f}t) avec drawdown {drawdown_pct:.1%}"
                                )
                                self.last_action_time = datetime.now()
                                return "CLOSE_SHORT"
            
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ Erreur GammaWallProtector.check_rejection: {e}")
            return None


def create_gamma_wall_protector(config: Optional[Dict[str, Any]] = None) -> GammaWallProtector:
    """Factory function pour créer un GammaWallProtector"""
    return GammaWallProtector(config)
