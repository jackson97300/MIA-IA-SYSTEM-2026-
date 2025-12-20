#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Signal Logger
Enregistre TOUS les signaux générés (pris ou non)
Pour analyse et optimisation des stratégies
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SignalLog:
    """Un signal enregistré"""
    # Identification
    signal_id: str
    timestamp: str
    strategy: str

    # Signal
    symbol: str
    direction: str  # LONG / SHORT
    entry_price: float
    stop_loss: float
    take_profit: float

    # Qualité
    quality_score: float
    confidence: float

    # Contexte marché
    vix: float
    session: str
    market_regime: str
    atr: float

    # Exécution
    signal_taken: bool
    ignore_reason: Optional[str] = None

    # Résultat (rempli après)
    outcome: Optional[str] = None  # WIN / LOSS / BREAKEVEN / PENDING
    actual_exit_price: Optional[float] = None
    profit_ticks: Optional[float] = None
    profit_dollars: Optional[float] = None
    exit_reason: Optional[str] = None
    duration_minutes: Optional[int] = None

    # Métadonnées
    setup_type: Optional[str] = None
    rr_ratio: Optional[float] = None
    additional_data: Optional[Dict] = None


class SignalLogger:
    """Logger de signaux pour analyse de performance"""

    def __init__(self, base_dir: str = "logs/signals"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Fichier du jour
        today = datetime.now().strftime("%Y%m%d")
        self.current_file = self.base_dir / f"signals_{today}.jsonl"

        # Statistiques en mémoire
        self.signals_today = 0
        self.signals_taken = 0
        self.signals_ignored = 0

        logger.info(f"📊 SignalLogger initialisé: {self.current_file}")

    def log_signal(self, signal: Dict, taken: bool = False,
                   ignore_reason: Optional[str] = None) -> str:
        """
        Enregistre un signal

        Args:
            signal: Données du signal
            taken: Le signal a-t-il été pris?
            ignore_reason: Raison si ignoré

        Returns:
            signal_id (UUID)
        """
        try:
            # Générer ID unique
            signal_id = str(uuid.uuid4())

            # Créer log
            signal_log = SignalLog(
                signal_id=signal_id,
                timestamp=datetime.now().isoformat(),
                strategy=signal.get('strategy', signal.get('setup_type', 'unknown')),

                # Signal de base
                symbol=signal.get('symbol', ''),
                direction=signal.get('action', signal.get('signal_type', '')),
                entry_price=float(signal.get('entry_price', signal.get('price', 0))),
                stop_loss=float(signal.get('stop_loss', 0)),
                take_profit=float(signal.get('take_profit', signal.get('take_profit_1', 0))),

                # Qualité
                quality_score=float(signal.get('quality_score', signal.get('base_quality', 0.5))),
                confidence=float(signal.get('confidence', signal.get('signal_probability', 0.5))),

                # Contexte
                vix=float(signal.get('vix', 0)),
                session=signal.get('session', signal.get('session_id', '')),
                market_regime=signal.get('market_regime', ''),
                atr=float(signal.get('atr', 0)),

                # Exécution
                signal_taken=taken,
                ignore_reason=ignore_reason,

                # Métadonnées
                setup_type=signal.get('setup_type', ''),
                rr_ratio=signal.get('rr_ratio', 0.0),
                additional_data=signal.get('additional_data')
            )

            # Écrire en JSONL
            self._write_log(signal_log)

            # Mettre à jour stats
            self.signals_today += 1
            if taken:
                self.signals_taken += 1
                logger.info(f"✅ Signal pris: {signal_log.strategy} {signal_log.direction} {signal_log.symbol}")
            else:
                self.signals_ignored += 1
                logger.debug(f"⚠️ Signal ignoré: {signal_log.strategy} - Raison: {ignore_reason}")

            return signal_id

        except Exception as e:
            logger.error(f"❌ Erreur log signal: {e}")
            return ""

    def update_signal_outcome(self, signal_id: str, outcome: str,
                              exit_price: float, profit_dollars: float,
                              exit_reason: str = "", duration_minutes: int = 0):
        """
        Met à jour le résultat d'un signal

        Args:
            signal_id: ID du signal
            outcome: WIN / LOSS / BREAKEVEN
            exit_price: Prix de sortie
            profit_dollars: Profit/perte en dollars
            exit_reason: Raison de sortie (TP_HIT, SL_HIT, etc.)
            duration_minutes: Durée du trade
        """
        try:
            # Lire le fichier
            signals = []
            if self.current_file.exists():
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    signals = [json.loads(line) for line in f]

            # Trouver et mettre à jour le signal
            updated = False
            for sig in signals:
                if sig.get('signal_id') == signal_id:
                    sig['outcome'] = outcome
                    sig['actual_exit_price'] = exit_price
                    sig['profit_dollars'] = profit_dollars
                    sig['exit_reason'] = exit_reason
                    sig['duration_minutes'] = duration_minutes

                    # Calculer profit en ticks
                    entry = sig.get('entry_price', 0)
                    tick_size = 0.25
                    if sig.get('direction') == 'LONG':
                        profit_ticks = (exit_price - entry) / tick_size
                    else:
                        profit_ticks = (entry - exit_price) / tick_size
                    sig['profit_ticks'] = profit_ticks

                    updated = True
                    break

            if updated:
                # Réécrire le fichier
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    for sig in signals:
                        f.write(json.dumps(sig) + '\n')

                logger.info(f"📝 Signal {signal_id} mis à jour: {outcome} ({profit_dollars:+.2f}$)")
            else:
                logger.warning(f"⚠️ Signal {signal_id} non trouvé pour mise à jour")

        except Exception as e:
            logger.error(f"❌ Erreur update signal: {e}")

    def _write_log(self, signal_log: SignalLog):
        """Écrit un log dans le fichier JSONL"""
        try:
            with open(self.current_file, 'a', encoding='utf-8') as f:
                log_dict = asdict(signal_log)
                f.write(json.dumps(log_dict) + '\n')
        except Exception as e:
            logger.error(f"❌ Erreur écriture log: {e}")

    def get_today_stats(self) -> Dict:
        """Retourne les statistiques du jour"""
        return {
            'total_signals': self.signals_today,
            'signals_taken': self.signals_taken,
            'signals_ignored': self.signals_ignored,
            'take_rate': (self.signals_taken / self.signals_today * 100) if self.signals_today > 0 else 0
        }

    def read_signals(self, date: Optional[str] = None) -> list:
        """
        Lit les signaux d'une date

        Args:
            date: Format YYYYMMDD (None = aujourd'hui)

        Returns:
            Liste des signaux
        """
        try:
            if date is None:
                file_path = self.current_file
            else:
                file_path = self.base_dir / f"signals_{date}.jsonl"

            if not file_path.exists():
                return []

            signals = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    signals.append(json.loads(line))

            return signals

        except Exception as e:
            logger.error(f"❌ Erreur lecture signaux: {e}")
            return []


# === FACTORY ===

_signal_logger_instance = None

def get_signal_logger() -> SignalLogger:
    """Singleton pour le signal logger"""
    global _signal_logger_instance
    if _signal_logger_instance is None:
        _signal_logger_instance = SignalLogger()
    return _signal_logger_instance


# === EXPORTS ===

__all__ = [
    'SignalLog',
    'SignalLogger',
    'get_signal_logger'
]


# === TESTING ===

if __name__ == "__main__":
    logger.info("🧪 TEST SIGNAL LOGGER...")

    # Créer logger
    sig_logger = SignalLogger(base_dir="logs/signals_test")

    # Test 1: Signal pris
    signal1 = {
        'strategy': 'menthorq_first',
        'symbol': 'ES',
        'action': 'LONG',
        'entry_price': 6900.0,
        'stop_loss': 6885.0,
        'take_profit': 6930.0,
        'quality_score': 0.82,
        'confidence': 0.75,
        'vix': 18.5,
        'session': 'London',
        'market_regime': 'CHOPPY',
        'atr': 0.75,
        'rr_ratio': 2.0
    }

    signal_id1 = sig_logger.log_signal(signal1, taken=True)
    logger.info(f"✅ Signal 1 logged: {signal_id1}")

    # Test 2: Signal ignoré
    signal2 = {
        'strategy': 'bracket_trading',
        'symbol': 'NQ',
        'action': 'SHORT',
        'entry_price': 26200.0,
        'stop_loss': 26215.0,
        'take_profit': 26170.0,
        'quality_score': 0.65,
        'confidence': 0.60,
        'vix': 18.5,
        'session': 'London',
        'market_regime': 'RANGE',
        'atr': 12.5
    }

    signal_id2 = sig_logger.log_signal(signal2, taken=False, ignore_reason="Already in position NQ")
    logger.info(f"⚠️ Signal 2 logged (ignored): {signal_id2}")

    # Test 3: Update outcome
    sig_logger.update_signal_outcome(
        signal_id1,
        outcome='WIN',
        exit_price=6930.0,
        profit_dollars=375.0,
        exit_reason='TP_HIT',
        duration_minutes=45
    )

    # Stats
    stats = sig_logger.get_today_stats()
    logger.info(f"📊 Stats: {stats}")

    # Relire
    signals = sig_logger.read_signals()
    logger.info(f"📖 {len(signals)} signaux relus")

    logger.info("[OK] Tests signal logger terminés!")
