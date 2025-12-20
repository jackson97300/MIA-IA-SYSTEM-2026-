#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Virtual Trader
Track les signaux NON PRIS pour voir ce qu'on a manqué
Permet d'analyser les opportunités perdues
"""

import json
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VirtualTrade:
    """Un trade virtuel (signal non pris)"""
    # Identification
    virtual_id: str
    signal_id: str  # Lien avec SignalLog
    timestamp: str
    strategy: str

    # Signal
    symbol: str
    direction: str
    was_taken: bool  # Toujours False pour virtual
    ignore_reason: str

    # Trade virtuel
    virtual_entry: float
    virtual_stop: float
    virtual_tp: float

    # Résultat virtuel (calculé après coup)
    virtual_outcome: Optional[str] = None  # WIN / LOSS / BREAKEVEN
    virtual_profit_dollars: Optional[float] = None
    virtual_profit_ticks: Optional[float] = None
    max_adverse_excursion: Optional[float] = None  # Pire point
    max_favorable_excursion: Optional[float] = None  # Meilleur point
    time_to_outcome_minutes: Optional[int] = None

    # Analyse
    would_have_been_profitable: Optional[bool] = None
    missed_opportunity_dollars: Optional[float] = None


class VirtualTrader:
    """Tracker de trades virtuels pour analyse"""

    def __init__(self, base_dir: str = "logs/virtual_trades"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Fichier du jour
        today = datetime.now().strftime("%Y%m%d")
        self.current_file = self.base_dir / f"virtual_{today}.jsonl"

        # Trades virtuels actifs (en cours de suivi)
        self.active_virtuals: Dict[str, VirtualTrade] = {}

        # Statistiques
        self.virtual_wins = 0
        self.virtual_losses = 0
        self.total_missed_profit = 0.0

        logger.info(f"🎮 VirtualTrader initialisé: {self.current_file}")

    def create_virtual_trade(self, signal: Dict, signal_id: str,
                            ignore_reason: str) -> str:
        """
        Crée un trade virtuel pour un signal ignoré

        Args:
            signal: Données du signal
            signal_id: ID du signal dans SignalLogger
            ignore_reason: Pourquoi ignoré

        Returns:
            virtual_id (UUID)
        """
        try:
            # Générer ID unique
            virtual_id = str(uuid.uuid4())

            # Créer virtual trade
            virtual_trade = VirtualTrade(
                virtual_id=virtual_id,
                signal_id=signal_id,
                timestamp=datetime.now().isoformat(),
                strategy=signal.get('strategy', signal.get('setup_type', 'unknown')),

                # Signal de base
                symbol=signal.get('symbol', ''),
                direction=signal.get('action', signal.get('signal_type', '')),
                was_taken=False,
                ignore_reason=ignore_reason,

                # Trade virtuel
                virtual_entry=float(signal.get('entry_price', signal.get('price', 0))),
                virtual_stop=float(signal.get('stop_loss', 0)),
                virtual_tp=float(signal.get('take_profit', signal.get('take_profit_1', 0)))
            )

            # Enregistrer
            self._write_virtual(virtual_trade)

            # Garder en mémoire pour suivi
            self.active_virtuals[virtual_id] = virtual_trade

            logger.debug(f"🎮 Virtual trade créé: {virtual_trade.strategy} {virtual_trade.direction} {virtual_trade.symbol}")

            return virtual_id

        except Exception as e:
            logger.error(f"❌ Erreur création virtual trade: {e}")
            return ""

    def update_virtual_outcome(self, market_data: Dict):
        """
        Met à jour les résultats des trades virtuels actifs
        Vérifie si TP ou SL aurait été touché

        Args:
            market_data: Données de marché actuelles
        """
        try:
            current_price = float(market_data.get('close', market_data.get('price', 0)))
            symbol = market_data.get('sym', '').split('_')[0]  # ESZ25 → ES

            completed_virtuals = []

            for virtual_id, virtual in self.active_virtuals.items():
                # Vérifier si même symbole
                if virtual.symbol not in symbol:
                    continue

                # Vérifier si outcome déjà défini
                if virtual.virtual_outcome is not None:
                    continue

                # Check TP/SL
                outcome = None
                profit = 0.0

                if virtual.direction in ['LONG', 'BUY']:
                    # LONG: TP si prix >= TP, SL si prix <= SL
                    if current_price >= virtual.virtual_tp:
                        outcome = 'WIN'
                        profit = (virtual.virtual_tp - virtual.virtual_entry) * 50  # ES tick value
                    elif current_price <= virtual.virtual_stop:
                        outcome = 'LOSS'
                        profit = (current_price - virtual.virtual_entry) * 50

                else:  # SHORT
                    # SHORT: TP si prix <= TP, SL si prix >= SL
                    if current_price <= virtual.virtual_tp:
                        outcome = 'WIN'
                        profit = (virtual.virtual_entry - virtual.virtual_tp) * 50
                    elif current_price >= virtual.virtual_stop:
                        outcome = 'LOSS'
                        profit = (virtual.virtual_entry - current_price) * 50

                # Si outcome déterminé
                if outcome:
                    virtual.virtual_outcome = outcome
                    virtual.virtual_profit_dollars = profit

                    # Calculer ticks
                    tick_size = 0.25
                    virtual.virtual_profit_ticks = profit / (50 / tick_size)  # ES: $50 per 4 ticks

                    # Temps
                    entry_time = datetime.fromisoformat(virtual.timestamp)
                    duration = (datetime.now() - entry_time).total_seconds() / 60
                    virtual.time_to_outcome_minutes = int(duration)

                    # Analyse
                    virtual.would_have_been_profitable = (profit > 0)
                    virtual.missed_opportunity_dollars = profit if profit > 0 else 0

                    # Stats
                    if outcome == 'WIN':
                        self.virtual_wins += 1
                        self.total_missed_profit += profit
                        logger.info(f"✅ Virtual WIN: {virtual.strategy} aurait gagné {profit:+.2f}$")
                    else:
                        self.virtual_losses += 1
                        logger.debug(f"❌ Virtual LOSS: {virtual.strategy} aurait perdu {profit:+.2f}$")

                    completed_virtuals.append(virtual_id)

            # Écrire les virtuals complétés
            for virtual_id in completed_virtuals:
                virtual = self.active_virtuals.pop(virtual_id)
                self._update_virtual_in_file(virtual)

        except Exception as e:
            logger.error(f"❌ Erreur update virtual outcomes: {e}")

    def _write_virtual(self, virtual_trade: VirtualTrade):
        """Écrit un virtual trade dans le fichier"""
        try:
            with open(self.current_file, 'a', encoding='utf-8') as f:
                virtual_dict = asdict(virtual_trade)
                f.write(json.dumps(virtual_dict) + '\n')
        except Exception as e:
            logger.error(f"❌ Erreur écriture virtual: {e}")

    def _update_virtual_in_file(self, virtual_trade: VirtualTrade):
        """Met à jour un virtual trade dans le fichier"""
        try:
            # Lire tous les virtuals
            virtuals = []
            if self.current_file.exists():
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    virtuals = [json.loads(line) for line in f]

            # Mettre à jour le bon virtual
            for virt in virtuals:
                if virt.get('virtual_id') == virtual_trade.virtual_id:
                    virt.update(asdict(virtual_trade))
                    break

            # Réécrire le fichier
            with open(self.current_file, 'w', encoding='utf-8') as f:
                for virt in virtuals:
                    f.write(json.dumps(virt) + '\n')

        except Exception as e:
            logger.error(f"❌ Erreur update virtual file: {e}")

    def get_virtual_stats(self) -> Dict:
        """Retourne les statistiques des trades virtuels"""
        total = self.virtual_wins + self.virtual_losses
        win_rate = (self.virtual_wins / total * 100) if total > 0 else 0

        return {
            'total_virtual_trades': total,
            'virtual_wins': self.virtual_wins,
            'virtual_losses': self.virtual_losses,
            'virtual_win_rate': win_rate,
            'total_missed_profit': self.total_missed_profit,
            'active_virtuals': len(self.active_virtuals)
        }

    def read_virtual_trades(self, date: Optional[str] = None) -> List[Dict]:
        """
        Lit les trades virtuels d'une date

        Args:
            date: Format YYYYMMDD (None = aujourd'hui)

        Returns:
            Liste des trades virtuels
        """
        try:
            if date is None:
                file_path = self.current_file
            else:
                file_path = self.base_dir / f"virtual_{date}.jsonl"

            if not file_path.exists():
                return []

            virtuals = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    virtuals.append(json.loads(line))

            return virtuals

        except Exception as e:
            logger.error(f"❌ Erreur lecture virtual trades: {e}")
            return []


# === FACTORY ===

_virtual_trader_instance = None

def get_virtual_trader() -> VirtualTrader:
    """Singleton pour le virtual trader"""
    global _virtual_trader_instance
    if _virtual_trader_instance is None:
        _virtual_trader_instance = VirtualTrader()
    return _virtual_trader_instance


# === EXPORTS ===

__all__ = [
    'VirtualTrade',
    'VirtualTrader',
    'get_virtual_trader'
]


# === TESTING ===

if __name__ == "__main__":
    logger.info("🧪 TEST VIRTUAL TRADER...")

    # Créer virtual trader
    vt = VirtualTrader(base_dir="logs/virtual_test")

    # Test 1: Créer virtual trade (SHORT)
    signal = {
        'strategy': 'bracket_trading',
        'symbol': 'ES',
        'action': 'SHORT',
        'entry_price': 6920.0,
        'stop_loss': 6930.0,
        'take_profit': 6900.0
    }

    virtual_id = vt.create_virtual_trade(signal, "signal_123", "Already in position")
    logger.info(f"🎮 Virtual trade créé: {virtual_id}")

    # Test 2: Simuler market data (TP touché)
    market_data_tp = {
        'sym': 'ESZ25_FUT_CME',
        'close': 6900.0  # TP atteint!
    }

    vt.update_virtual_outcome(market_data_tp)

    # Stats
    stats = vt.get_virtual_stats()
    logger.info(f"📊 Virtual stats: {stats}")

    logger.info("[OK] Tests virtual trader terminés!")
