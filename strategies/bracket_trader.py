#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Bracket Trader
Gère le trading des brackets détectés
Entry/Exit/Phases avec gestion adaptative
ÉQUILIBRÉ: Ni trop rigide, ni trop permissif
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from core.logger import get_logger
from config.bracket_config import BracketConfig, create_default_bracket_config
from strategies.bracket_detector import Bracket, BracketDetector, create_bracket_detector
from execution.sierra_dtc_connector import SierraDTCConnector

logger = get_logger(__name__)


class BracketPhase(Enum):
    """Phase du trading sur un bracket"""
    PHASE_1 = "phase_1"  # Trades 1-2: Full size
    PHASE_2 = "phase_2"  # Trade 3: Demi-size
    PHASE_3 = "phase_3"  # Trade 4+: Stop


class TradeDirection(Enum):
    """Direction du trade"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class BracketTrade:
    """Un trade sur un bracket"""
    bracket_id: str
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit_1: float  # Middle
    take_profit_2: float  # Opposite

    # Sizing
    position_size: float
    size_tp1: float  # 50% au TP1
    size_tp2: float  # 50% au TP2

    # Statut
    entry_time: datetime
    phase: BracketPhase
    trade_number: int  # 1, 2, 3...

    # Résultat
    is_closed: bool = False
    pnl: float = 0.0
    exit_reason: str = ""


@dataclass
class BracketTradeSession:
    """Session de trading sur un bracket"""
    bracket: Bracket
    trades: List[BracketTrade] = field(default_factory=list)
    total_pnl: float = 0.0
    current_phase: BracketPhase = BracketPhase.PHASE_1
    is_active: bool = True


class BracketTrader:
    """Trader de brackets avec gestion de phases"""

    def __init__(self, config: Optional[BracketConfig] = None,
                 sierra_connector: Optional[SierraDTCConnector] = None):
        self.config = config or create_default_bracket_config()
        self.detector = create_bracket_detector(self.config)
        self.sierra_connector = sierra_connector
        self.logger = logger

        # Sessions actives
        self.active_sessions: Dict[str, BracketTradeSession] = {}

        # Statistiques
        self.total_brackets_traded: int = 0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_pnl: float = 0.0

        self.logger.info("🎯 BracketTrader initialisé")
        self.logger.info(f"  - Max trades/bracket: {self.config.max_trades_per_bracket}")
        self.logger.info(f"  - TP strategy: {self.config.tp_strategy}")
        self.logger.info(f"  - Équilibré: Ni trop rigide, ni trop permissif ⚖️")

    def analyze_market_for_bracket(self, market_data: Dict) -> Optional[Dict]:
        """
        Analyse le marché pour détecter un bracket et générer un signal

        Returns:
            Signal de trade ou None
        """
        try:
            # 1. Détecter bracket
            bracket = self.detector.detect_bracket(market_data)
            if not bracket:
                return None

            bracket_id = f"{bracket.symbol}_{bracket.detection_time.strftime('%H%M%S')}"

            # 2. Vérifier si déjà une session active
            if bracket_id in self.active_sessions:
                session = self.active_sessions[bracket_id]

                # Vérifier fatigue
                if self.detector.check_bracket_fatigue(bracket, market_data):
                    self.logger.info(f"⚠️ Bracket fatigué, arrêt: {bracket_id}")
                    session.is_active = False
                    return None

                # Vérifier invalidation
                if self.detector.check_bracket_invalidation(bracket, market_data):
                    self.logger.info(f"❌ Bracket invalidé: {bracket_id}")
                    session.is_active = False
                    return None

            else:
                # Créer nouvelle session
                session = BracketTradeSession(bracket=bracket)
                self.active_sessions[bracket_id] = session
                self.total_brackets_traded += 1
                self.logger.info(f"🆕 Nouvelle session bracket: {bracket_id}")

            # 3. Évaluer opportunité de trade
            signal = self._evaluate_trade_opportunity(session, market_data)

            return signal

        except Exception as e:
            self.logger.error(f"❌ Erreur analyse bracket: {e}")
            return None

    def _evaluate_trade_opportunity(self, session: BracketTradeSession,
                                     market_data: Dict) -> Optional[Dict]:
        """Évalue s'il y a une opportunité de trade"""

        if not session.is_active:
            return None

        bracket = session.bracket
        current_price = float(market_data.get('close', 0))

        # Quelle phase sommes-nous?
        trades_taken = len(session.trades)

        if trades_taken >= self.config.max_trades_per_bracket:
            self.logger.debug(f"⚠️ Max trades atteint ({trades_taken})")
            session.is_active = False
            return None

        # Déterminer la phase
        if trades_taken < self.config.phase_1_trades:
            session.current_phase = BracketPhase.PHASE_1
        elif trades_taken < (self.config.phase_1_trades + self.config.phase_2_trades):
            session.current_phase = BracketPhase.PHASE_2
        else:
            session.current_phase = BracketPhase.PHASE_3
            session.is_active = False
            return None

        # Vérifier proximité des bornes
        tick_size = 0.25
        entry_distance = self.config.entry_distance_ticks * tick_size

        # Proche borne HAUTE → SHORT
        distance_upper = bracket.upper_bound.price - current_price
        if 0 <= distance_upper <= entry_distance * 2:  # Petite tolérance
            return self._create_short_signal(session, market_data, current_price)

        # Proche borne BASSE → LONG
        distance_lower = current_price - bracket.lower_bound.price
        if 0 <= distance_lower <= entry_distance * 2:  # Petite tolérance
            return self._create_long_signal(session, market_data, current_price)

        return None

    def _create_short_signal(self, session: BracketTradeSession,
                             market_data: Dict, current_price: float) -> Dict:
        """Crée un signal SHORT à la borne haute"""

        bracket = session.bracket
        trades_taken = len(session.trades)

        # Calculer stop loss
        stop_loss = self._calculate_stop_loss(
            bracket, TradeDirection.SHORT, current_price, market_data
        )

        # Calculer take profits
        tp1, tp2 = self._calculate_take_profits(
            bracket, TradeDirection.SHORT, current_price
        )

        # Calculer position size selon phase
        position_size = self._calculate_position_size(session.current_phase)

        # Risk/Reward check
        risk = abs(current_price - stop_loss)
        reward = abs(current_price - tp1)  # Au moins TP1
        rr_ratio = reward / risk if risk > 0 else 0

        if rr_ratio < self.config.min_rr_ratio:
            self.logger.debug(f"⚠️ RR insuffisant: {rr_ratio:.2f} < {self.config.min_rr_ratio}")
            return None

        signal = {
            'action': 'SHORT',
            'symbol': bracket.symbol,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit_1': tp1,
            'take_profit_2': tp2,
            'position_size': position_size,
            'bracket_id': f"{bracket.symbol}_{bracket.detection_time.strftime('%H%M%S')}",
            'phase': session.current_phase.value,
            'trade_number': trades_taken + 1,
            'quality_score': bracket.quality_score,
            'rr_ratio': rr_ratio,
            'setup_type': 'BRACKET_SHORT_UPPER_BOUND',
            'confidence': min(bracket.quality_score * 1.2, 1.0)
        }

        self.logger.info(f"📉 Signal SHORT bracket: Entry={current_price:.2f}, SL={stop_loss:.2f}, TP1={tp1:.2f}, RR={rr_ratio:.2f}")

        return signal

    def _create_long_signal(self, session: BracketTradeSession,
                            market_data: Dict, current_price: float) -> Dict:
        """Crée un signal LONG à la borne basse"""

        bracket = session.bracket
        trades_taken = len(session.trades)

        # Calculer stop loss
        stop_loss = self._calculate_stop_loss(
            bracket, TradeDirection.LONG, current_price, market_data
        )

        # Calculer take profits
        tp1, tp2 = self._calculate_take_profits(
            bracket, TradeDirection.LONG, current_price
        )

        # Calculer position size selon phase
        position_size = self._calculate_position_size(session.current_phase)

        # Risk/Reward check
        risk = abs(current_price - stop_loss)
        reward = abs(tp1 - current_price)  # Au moins TP1
        rr_ratio = reward / risk if risk > 0 else 0

        if rr_ratio < self.config.min_rr_ratio:
            self.logger.debug(f"⚠️ RR insuffisant: {rr_ratio:.2f} < {self.config.min_rr_ratio}")
            return None

        signal = {
            'action': 'LONG',
            'symbol': bracket.symbol,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit_1': tp1,
            'take_profit_2': tp2,
            'position_size': position_size,
            'bracket_id': f"{bracket.symbol}_{bracket.detection_time.strftime('%H%M%S')}",
            'phase': session.current_phase.value,
            'trade_number': trades_taken + 1,
            'quality_score': bracket.quality_score,
            'rr_ratio': rr_ratio,
            'setup_type': 'BRACKET_LONG_LOWER_BOUND',
            'confidence': min(bracket.quality_score * 1.2, 1.0)
        }

        self.logger.info(f"📈 Signal LONG bracket: Entry={current_price:.2f}, SL={stop_loss:.2f}, TP1={tp1:.2f}, RR={rr_ratio:.2f}")

        return signal

    def _calculate_stop_loss(self, bracket: Bracket, direction: TradeDirection,
                             entry_price: float, market_data: Dict) -> float:
        """Calcule le stop loss selon la taille du bracket et la volatilité"""

        tick_size = 0.25

        # 1. Stop de base selon taille bracket
        if bracket.width_ticks < 30:
            base_stop_ticks = self.config.stop_distance['small_bracket']
        elif bracket.width_ticks < 50:
            base_stop_ticks = self.config.stop_distance['medium_bracket']
        else:
            base_stop_ticks = self.config.stop_distance['large_bracket']

        # 2. Ajustement volatilité (si activé)
        stop_ticks = base_stop_ticks

        if self.config.use_volatility_adjustment:
            vix = market_data.get('vix', 20)

            if vix < 15:
                vix_mult = self.config.vix_multipliers['low']
            elif vix < 25:
                vix_mult = self.config.vix_multipliers['normal']
            else:
                vix_mult = self.config.vix_multipliers['high']

            atr = market_data.get('atr', 0)
            atr_threshold = 0.8 if 'ES' in bracket.symbol else 15.0

            if atr > atr_threshold:
                atr_mult = self.config.atr_multiplier
            else:
                atr_mult = 1.0

            stop_ticks = stop_ticks * vix_mult * atr_mult

        # 3. Cap maximum
        stop_ticks = min(stop_ticks, self.config.max_stop_cap)

        # 4. Calculer prix stop
        stop_distance = stop_ticks * tick_size

        if direction == TradeDirection.SHORT:
            # SHORT: stop AU-DESSUS de la borne haute
            stop_price = bracket.upper_bound.price + stop_distance
        else:
            # LONG: stop EN-DESSOUS de la borne basse
            stop_price = bracket.lower_bound.price - stop_distance

        # Arrondir au tick
        stop_price = round(stop_price / tick_size) * tick_size

        self.logger.debug(f"  Stop: {stop_ticks:.1f} ticks (base={base_stop_ticks}, VIX adj) → ${stop_price:.2f}")

        return stop_price

    def _calculate_take_profits(self, bracket: Bracket, direction: TradeDirection,
                                 entry_price: float) -> Tuple[float, float]:
        """Calcule les take profits (middle et opposé)"""

        tick_size = 0.25
        middle = bracket.middle_price

        if direction == TradeDirection.SHORT:
            # SHORT: TP1 = middle, TP2 = borne basse
            tp1 = middle
            tp2 = bracket.lower_bound.price
        else:
            # LONG: TP1 = middle, TP2 = borne haute
            tp1 = middle
            tp2 = bracket.upper_bound.price

        # Arrondir au tick
        tp1 = round(tp1 / tick_size) * tick_size
        tp2 = round(tp2 / tick_size) * tick_size

        return tp1, tp2

    def _calculate_position_size(self, phase: BracketPhase) -> float:
        """Calcule la taille de position selon la phase"""

        if phase == BracketPhase.PHASE_1:
            return self.config.size_adjustment['trade_1_2']  # 1.0 = 100%
        elif phase == BracketPhase.PHASE_2:
            return self.config.size_adjustment['trade_3']    # 0.5 = 50%
        else:
            return 0.0  # STOP

    async def execute_bracket_trade(self, signal: Dict) -> bool:
        """
        Exécute un trade bracket via Sierra Chart

        Returns:
            True si succès, False sinon
        """
        if not self.sierra_connector:
            self.logger.warning("⚠️ Pas de connecteur Sierra, simulation mode")
            return self._simulate_trade(signal)

        try:
            # TODO: Implémenter l'exécution réelle via Sierra Chart
            # Pour l'instant, simulation
            return self._simulate_trade(signal)

        except Exception as e:
            self.logger.error(f"❌ Erreur exécution trade: {e}")
            return False

    def _simulate_trade(self, signal: Dict) -> bool:
        """Simule un trade (pour testing)"""

        self.logger.info(f"🔄 [SIMULATION] Trade bracket:")
        self.logger.info(f"   {signal['action']} {signal['symbol']}")
        self.logger.info(f"   Entry: {signal['entry_price']:.2f}")
        self.logger.info(f"   Stop: {signal['stop_loss']:.2f}")
        self.logger.info(f"   TP1: {signal['take_profit_1']:.2f} (50%)")
        self.logger.info(f"   TP2: {signal['take_profit_2']:.2f} (50%)")
        self.logger.info(f"   Phase: {signal['phase']} (Trade #{signal['trade_number']})")
        self.logger.info(f"   RR: {signal['rr_ratio']:.2f}:1")

        # Enregistrer le trade
        bracket_id = signal['bracket_id']
        if bracket_id in self.active_sessions:
            session = self.active_sessions[bracket_id]

            trade = BracketTrade(
                bracket_id=bracket_id,
                direction=TradeDirection[signal['action']],
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'],
                take_profit_2=signal['take_profit_2'],
                position_size=signal['position_size'],
                size_tp1=signal['position_size'] * 0.5,
                size_tp2=signal['position_size'] * 0.5,
                entry_time=datetime.now(),
                phase=BracketPhase(signal['phase']),
                trade_number=signal['trade_number']
            )

            session.trades.append(trade)
            self.total_trades += 1

        return True

    def get_statistics(self) -> Dict:
        """Retourne les statistiques de trading"""

        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        return {
            'total_brackets_traded': self.total_brackets_traded,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'active_sessions': len([s for s in self.active_sessions.values() if s.is_active])
        }


# === FACTORY ===

def create_bracket_trader(config: Optional[BracketConfig] = None,
                          sierra_connector: Optional[SierraDTCConnector] = None) -> BracketTrader:
    """Factory pour créer un BracketTrader"""
    return BracketTrader(config, sierra_connector)


# === EXPORTS ===

__all__ = [
    'BracketTrader',
    'BracketPhase',
    'TradeDirection',
    'BracketTrade',
    'BracketTradeSession',
    'create_bracket_trader'
]
