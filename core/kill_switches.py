#!/usr/bin/env python3
"""
Kill Switches & Anomaly Detection (Mode Calibrage)
Protections soft pour détecter anomalies sans stopper

Sprint 3 - TODO Tasks 2a, 2b, 2c
Date: 13 Novembre 2025
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alerte anomalie"""
    timestamp: datetime
    level: AlertLevel
    category: str
    message: str
    data: Dict


class KillSwitches:
    """
    Kill Switches - Mode Calibrage

    Détecte anomalies SANS stopper le bot (phase apprentissage)
    - Consecutive losses
    - Drawdown daily
    - Volatility spikes
    - Strategy health

    En phase calibrage: ALERTE uniquement (pas de blocage)
    """

    def __init__(self, calibration_mode: bool = True):
        self.calibration_mode = calibration_mode

        # Historiques
        self.trades_history = deque(maxlen=1000)
        self.volatility_history = deque(maxlen=100)

        # Tracking par stratégie
        self.strategy_consecutive_losses = defaultdict(int)
        self.strategy_consecutive_wins = defaultdict(int)
        self.strategy_trades_count = defaultdict(int)
        self.strategy_wins_count = defaultdict(int)

        # Alertes
        self.alerts: List[Alert] = []

        # Seuils (Mode Calibrage - Permissif)
        self.MAX_CONSECUTIVE_LOSSES = 10  # Alerte si > 10 pertes
        self.MAX_DAILY_DRAWDOWN_PCT = 0.20  # Alerte si > 20%
        self.MAX_VOLATILITY_SPIKE = 3.0  # Alerte si > 3x median
        self.MIN_STRATEGY_WINRATE = 0.20  # Alerte si < 20% WR
        self.MIN_TRADES_FOR_HEALTH_CHECK = 20  # Min trades avant check WR

        # État daily
        self.daily_start_balance = 0.0
        self.current_balance = 0.0
        self.last_reset_date = datetime.now().date()

        logger.info(
            "🛡️ KillSwitches initialisé (Mode: %s)",
            "CALIBRAGE" if calibration_mode else "PRODUCTION"
        )

    def add_trade(self, strategy: str, win: bool, pnl: float):
        """
        Ajoute trade et check anomalies

        Args:
            strategy: Nom stratégie
            win: Trade gagné?
            pnl: PnL trade
        """
        # Reset daily si nouveau jour
        self._check_daily_reset()

        # Update balance
        self.current_balance += pnl

        # Track trade
        self.trades_history.append({
            'timestamp': datetime.now(),
            'strategy': strategy,
            'win': win,
            'pnl': pnl
        })

        # Update strategy stats
        self.strategy_trades_count[strategy] += 1

        if win:
            self.strategy_wins_count[strategy] += 1
            self.strategy_consecutive_wins[strategy] += 1
            self.strategy_consecutive_losses[strategy] = 0
        else:
            self.strategy_consecutive_losses[strategy] += 1
            self.strategy_consecutive_wins[strategy] = 0

        # Check anomalies
        self._check_consecutive_losses(strategy)
        self._check_daily_drawdown()
        self._check_strategy_health(strategy)

    def update_volatility(self, atr: float):
        """
        Update volatilité et check spike

        Args:
            atr: ATR actuel
        """
        if atr <= 0:
            return

        self.volatility_history.append(atr)

        # Check spike volatilité
        if len(self.volatility_history) >= 50:
            self._check_volatility_spike(atr)

    def _check_daily_reset(self):
        """Reset stats daily"""
        today = datetime.now().date()

        if today != self.last_reset_date:
            logger.info("🔄 Reset daily stats")
            self.daily_start_balance = self.current_balance
            self.last_reset_date = today

    def _check_consecutive_losses(self, strategy: str):
        """
        Check pertes consécutives

        Args:
            strategy: Nom stratégie
        """
        consecutive = self.strategy_consecutive_losses[strategy]

        if consecutive >= self.MAX_CONSECUTIVE_LOSSES:
            self._create_alert(
                level=AlertLevel.CRITICAL if consecutive >= 15 else AlertLevel.WARNING,
                category="CONSECUTIVE_LOSSES",
                message=f"🚨 {strategy}: {consecutive} pertes consécutives!",
                data={
                    'strategy': strategy,
                    'consecutive_losses': consecutive,
                    'threshold': self.MAX_CONSECUTIVE_LOSSES
                }
            )

    def _check_daily_drawdown(self):
        """Check drawdown daily"""
        if self.daily_start_balance == 0:
            return

        drawdown = (self.daily_start_balance - self.current_balance) / abs(self.daily_start_balance)

        if drawdown > self.MAX_DAILY_DRAWDOWN_PCT:
            self._create_alert(
                level=AlertLevel.CRITICAL,
                category="DAILY_DRAWDOWN",
                message=f"🚨 Drawdown daily: {drawdown*100:.1f}% > {self.MAX_DAILY_DRAWDOWN_PCT*100:.1f}%!",
                data={
                    'drawdown_pct': drawdown * 100,
                    'start_balance': self.daily_start_balance,
                    'current_balance': self.current_balance,
                    'threshold_pct': self.MAX_DAILY_DRAWDOWN_PCT * 100
                }
            )

    def _check_volatility_spike(self, current_atr: float):
        """
        Check spike volatilité

        Args:
            current_atr: ATR actuel
        """
        if len(self.volatility_history) < 50:
            return

        median_atr = np.median(list(self.volatility_history))

        if median_atr == 0:
            return

        ratio = current_atr / median_atr

        if ratio > self.MAX_VOLATILITY_SPIKE:
            self._create_alert(
                level=AlertLevel.WARNING,
                category="VOLATILITY_SPIKE",
                message=f"⚠️ Spike volatilité: ATR={current_atr:.2f} ({ratio:.1f}x median={median_atr:.2f})!",
                data={
                    'current_atr': current_atr,
                    'median_atr': median_atr,
                    'ratio': ratio,
                    'threshold': self.MAX_VOLATILITY_SPIKE
                }
            )

    def _check_strategy_health(self, strategy: str):
        """
        Check santé stratégie

        Args:
            strategy: Nom stratégie
        """
        trades = self.strategy_trades_count[strategy]

        # Attendre min trades
        if trades < self.MIN_TRADES_FOR_HEALTH_CHECK:
            return

        wins = self.strategy_wins_count[strategy]
        win_rate = wins / trades if trades > 0 else 0

        if win_rate < self.MIN_STRATEGY_WINRATE:
            self._create_alert(
                level=AlertLevel.WARNING,
                category="STRATEGY_HEALTH",
                message=f"⚠️ {strategy}: Win rate faible {win_rate*100:.1f}% sur {trades} trades!",
                data={
                    'strategy': strategy,
                    'win_rate': win_rate * 100,
                    'trades': trades,
                    'wins': wins,
                    'threshold_pct': self.MIN_STRATEGY_WINRATE * 100
                }
            )

    def _create_alert(
        self,
        level: AlertLevel,
        category: str,
        message: str,
        data: Dict
    ):
        """
        Crée alerte

        Args:
            level: Niveau alerte
            category: Catégorie
            message: Message
            data: Données
        """
        alert = Alert(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            data=data
        )

        self.alerts.append(alert)

        # Log selon niveau
        if level == AlertLevel.CRITICAL:
            logger.critical(message)
        elif level == AlertLevel.WARNING:
            logger.warning(message)
        else:
            logger.info(message)

        # En mode production, activer protections
        if not self.calibration_mode and level == AlertLevel.CRITICAL:
            logger.critical("🛑 KILL SWITCH ACTIVÉ - MODE PRODUCTION")
            # TODO: Implémenter stop trading

    def get_recent_alerts(self, hours: int = 1) -> List[Alert]:
        """
        Retourne alertes récentes

        Args:
            hours: Fenêtre heures

        Returns:
            Liste alertes
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        return [a for a in self.alerts if a.timestamp >= cutoff]

    def is_triggered(self) -> bool:
        """
        Vérifie si kill switch est déclenché

        En mode calibration: Retourne TOUJOURS False (pas de blocage)
        En mode production: Vérifie les alertes critiques

        Returns:
            True si kill switch actif, False sinon
        """
        # En mode calibration, on ne bloque jamais
        if self.calibration_mode:
            return False

        # En mode production, vérifier alertes critiques récentes
        recent_critical = [
            a for a in self.alerts[-10:]  # Dernières 10 alertes
            if a.level == AlertLevel.CRITICAL
        ]

        # Si > 3 alertes critiques récentes, activer kill switch
        return len(recent_critical) >= 3

    def get_strategy_stats(self) -> Dict:
        """Retourne stats stratégies"""
        stats = {}

        for strategy in self.strategy_trades_count.keys():
            trades = self.strategy_trades_count[strategy]
            wins = self.strategy_wins_count[strategy]
            win_rate = wins / trades if trades > 0 else 0

            stats[strategy] = {
                'trades': trades,
                'wins': wins,
                'win_rate': win_rate,
                'consecutive_losses': self.strategy_consecutive_losses[strategy],
                'consecutive_wins': self.strategy_consecutive_wins[strategy]
            }

        return stats

    def print_alerts_summary(self):
        """Affiche résumé alertes"""
        recent = self.get_recent_alerts(hours=24)

        if not recent:
            logger.info("✅ Aucune alerte récente (24h)")
            return

        print("\n" + "=" * 80)
        print("🚨 ALERTES RÉCENTES (24h)")
        print("=" * 80)

        # Compter par catégorie
        by_category = defaultdict(int)
        by_level = defaultdict(int)

        for alert in recent:
            by_category[alert.category] += 1
            by_level[alert.level.value] += 1

        print(f"\nTotal: {len(recent)} alertes")
        print(f"  CRITICAL: {by_level.get('CRITICAL', 0)}")
        print(f"  WARNING: {by_level.get('WARNING', 0)}")
        print(f"  INFO: {by_level.get('INFO', 0)}")

        print("\nPar catégorie:")
        for category, count in sorted(by_category.items()):
            print(f"  {category}: {count}")

        print("\nDernières alertes:")
        for alert in recent[-5:]:
            print(f"  [{alert.level.value}] {alert.message}")

        print("=" * 80 + "\n")


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Créer instance
    ks = KillSwitches(calibration_mode=True)

    # Simuler trades
    print("📊 Simulation trades...\n")

    # Stratégie avec pertes consécutives
    for i in range(12):
        ks.add_trade("ml_3layer", False, -50)

    # Stratégie avec drawdown
    ks.daily_start_balance = 10000
    ks.current_balance = 10000

    for i in range(10):
        ks.add_trade("vwap_sd", False, -250)

    # Spike volatilité
    for i in range(50):
        ks.update_volatility(5.0)

    ks.update_volatility(18.0)  # Spike 3.6x

    # Stratégie faible WR
    for i in range(25):
        win = i % 6 == 0  # ~17% WR
        ks.add_trade("gamma_rejection", win, 50 if win else -40)

    # Afficher alertes
    ks.print_alerts_summary()

    # Stats stratégies
    print("\nSTATS STRATÉGIES:")
    import json
    print(json.dumps(ks.get_strategy_stats(), indent=2))
