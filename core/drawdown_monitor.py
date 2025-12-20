#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRAWDOWN MONITOR - Surveillance Drawdown & Recovery Time
=========================================================

Monitor drawdown depuis peak PnL :
- Max Drawdown (%)
- Current Drawdown (%)
- Drawdown Duration (cycles)
- Recovery time
- Halt trading si DD > seuil

Author: MIA System + Claude Sonnet 4.5
Date: 4 Novembre 2025
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class DrawdownMetrics:
    """Métriques drawdown"""
    peak_pnl: float
    current_pnl: float
    current_dd_pct: float
    current_dd_usd: float
    max_dd_pct: float
    max_dd_usd: float
    dd_duration: int  # Cycles depuis peak
    recovery_time: int  # Cycles pour recovery (0 si pas en DD)
    timestamp: datetime

# ═══════════════════════════════════════════════════════════════
# DRAWDOWN MONITOR
# ═══════════════════════════════════════════════════════════════

class DrawdownMonitor:
    """
    Monitor Drawdown & Recovery Time

    Fonctionnalités :
    - Track peak PnL
    - Calcul drawdown current & max
    - Durée drawdown
    - Recovery time
    - Halt trading si DD > seuil
    """

    def __init__(self,
                 max_dd_pct: float = 0.15,
                 max_dd_duration: int = 100,
                 save_history: bool = True,
                 history_path: str = "data/drawdown_history.json"):
        """
        Initialisation

        Args:
            max_dd_pct: Drawdown max autorisé (% du peak) - défaut 15%
            max_dd_duration: Durée max DD autorisée (cycles) - défaut 100
            save_history: Sauver historique drawdowns
            history_path: Chemin fichier historique
        """
        self.max_dd_pct = max_dd_pct
        self.max_dd_duration = max_dd_duration
        self.save_history = save_history
        self.history_path = Path(history_path)

        # État courant
        self.peak_pnl = 0.0
        self.current_pnl = 0.0
        self.current_dd_pct = 0.0
        self.current_dd_usd = 0.0
        self.max_dd_pct_observed = 0.0
        self.max_dd_usd_observed = 0.0
        self.dd_duration = 0
        self.recovery_time = 0
        self.in_drawdown = False

        # Historique
        self.drawdown_history: List[DrawdownMetrics] = []

        # Créer dossier si nécessaire
        if self.save_history:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"🔴 Drawdown Monitor initialisé (Max DD: {max_dd_pct:.1%}, Max Duration: {max_dd_duration} cycles)")

    def update(self, current_pnl: float = None, *, symbol: str = None, 
               pnl: float = None, timestamp: int = None) -> DrawdownMetrics:
        """
        Met à jour drawdown

        Args:
            current_pnl: PnL actuel (legacy)
            symbol: Symbole (optionnel, pour logging)
            pnl: PnL actuel (nouveau paramètre)
            timestamp: Timestamp en ms (optionnel)

        Returns:
            DrawdownMetrics actualisées
        """
        # Support ancienne et nouvelle signature
        if pnl is not None:
            current_pnl = pnl
        elif current_pnl is None:
            current_pnl = self.current_pnl
            
        self.current_pnl = current_pnl

        # Nouveau peak ?
        if current_pnl > self.peak_pnl:
            # Sortie de drawdown
            if self.in_drawdown:
                logger.info(f"✅ Recovery complet ! Peak: ${self.peak_pnl:.2f} → ${current_pnl:.2f} (Recovery time: {self.recovery_time} cycles)")
                self.recovery_time = 0
                self.in_drawdown = False

            # Nouveau peak
            self.peak_pnl = current_pnl
            self.current_dd_pct = 0.0
            self.current_dd_usd = 0.0
            self.dd_duration = 0

        else:
            # En drawdown
            if self.peak_pnl > 0:
                self.current_dd_usd = self.peak_pnl - current_pnl
                self.current_dd_pct = self.current_dd_usd / self.peak_pnl

                # Entrée drawdown
                if not self.in_drawdown and self.current_dd_pct > 0:
                    self.in_drawdown = True
                    self.recovery_time = 0
                    logger.warning(f"⚠️ Entrée Drawdown: Peak ${self.peak_pnl:.2f} → Current ${current_pnl:.2f} (DD: {self.current_dd_pct:.2%})")

                # Incrément durée
                self.dd_duration += 1
                if self.in_drawdown:
                    self.recovery_time += 1

                # Update max DD observé
                if self.current_dd_pct > self.max_dd_pct_observed:
                    self.max_dd_pct_observed = self.current_dd_pct
                    self.max_dd_usd_observed = self.current_dd_usd
                    logger.warning(f"🔴 Nouveau Max Drawdown: {self.current_dd_pct:.2%} (${self.current_dd_usd:.2f})")

        # Créer métriques
        metrics = DrawdownMetrics(
            peak_pnl=self.peak_pnl,
            current_pnl=current_pnl,
            current_dd_pct=self.current_dd_pct,
            current_dd_usd=self.current_dd_usd,
            max_dd_pct=self.max_dd_pct_observed,
            max_dd_usd=self.max_dd_usd_observed,
            dd_duration=self.dd_duration,
            recovery_time=self.recovery_time,
            timestamp=datetime.now()
        )

        # Sauver historique
        if self.save_history:
            self.drawdown_history.append(metrics)
            if len(self.drawdown_history) % 100 == 0:
                self._save_history()

        return metrics

    def should_halt(self) -> bool:
        """
        Vérifie si trading doit être arrêté

        Returns:
            True si halt requis
        """
        # Critère 1: DD > seuil
        if self.current_dd_pct > self.max_dd_pct:
            logger.error(f"🚨 HALT REQUIS: Drawdown {self.current_dd_pct:.2%} > Max autorisé {self.max_dd_pct:.1%}")
            return True

        # Critère 2: DD duration > seuil
        if self.dd_duration > self.max_dd_duration:
            logger.error(f"🚨 HALT REQUIS: DD Duration {self.dd_duration} cycles > Max autorisé {self.max_dd_duration}")
            return True

        return False

    def max_drawdown_exceeded(self) -> bool:
        """
        Alias pour should_halt() - Vérifie si max drawdown est dépassé
        
        Returns:
            True si max drawdown atteint
        """
        return self.should_halt()

    def get_status(self) -> Dict:
        """
        Retourne status complet

        Returns:
            Dict avec toutes métriques
        """
        return {
            'peak_pnl': self.peak_pnl,
            'current_pnl': self.current_pnl,
            'current_dd_pct': self.current_dd_pct,
            'current_dd_usd': self.current_dd_usd,
            'max_dd_pct': self.max_dd_pct_observed,
            'max_dd_usd': self.max_dd_usd_observed,
            'dd_duration': self.dd_duration,
            'recovery_time': self.recovery_time,
            'in_drawdown': self.in_drawdown,
            'should_halt': self.should_halt()
        }

    def reset(self):
        """Reset monitor (début nouveau jour par exemple)"""
        logger.info("🔄 Drawdown Monitor reset")
        self.peak_pnl = self.current_pnl  # Garder PnL actuel comme nouveau peak
        self.current_dd_pct = 0.0
        self.current_dd_usd = 0.0
        self.dd_duration = 0
        self.recovery_time = 0
        self.in_drawdown = False

    def _save_history(self):
        """Sauvegarde historique drawdowns"""
        try:
            history_data = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'peak_pnl': m.peak_pnl,
                    'current_pnl': m.current_pnl,
                    'current_dd_pct': m.current_dd_pct,
                    'current_dd_usd': m.current_dd_usd,
                    'max_dd_pct': m.max_dd_pct,
                    'max_dd_usd': m.max_dd_usd,
                    'dd_duration': m.dd_duration,
                    'recovery_time': m.recovery_time
                }
                for m in self.drawdown_history[-1000:]  # Garder derniers 1000
            ]

            with open(self.history_path, 'w') as f:
                json.dump(history_data, f, indent=2)

            logger.debug(f"💾 Drawdown history sauvegardé: {self.history_path}")

        except Exception as e:
            logger.warning(f"⚠️ Erreur sauvegarde drawdown history: {e}")

    def load_history(self) -> bool:
        """
        Charge historique depuis fichier

        Returns:
            True si chargé avec succès
        """
        try:
            if not self.history_path.exists():
                logger.info("ℹ️ Pas d'historique drawdown existant")
                return False

            with open(self.history_path, 'r') as f:
                history_data = json.load(f)

            self.drawdown_history = [
                DrawdownMetrics(
                    peak_pnl=d['peak_pnl'],
                    current_pnl=d['current_pnl'],
                    current_dd_pct=d['current_dd_pct'],
                    current_dd_usd=d['current_dd_usd'],
                    max_dd_pct=d['max_dd_pct'],
                    max_dd_usd=d['max_dd_usd'],
                    dd_duration=d['dd_duration'],
                    recovery_time=d['recovery_time'],
                    timestamp=datetime.fromisoformat(d['timestamp'])
                )
                for d in history_data
            ]

            logger.info(f"✅ Drawdown history chargé: {len(self.drawdown_history)} entrées")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Erreur chargement drawdown history: {e}")
            return False


# ═══════════════════════════════════════════════════════════════
# FONCTION HELPER
# ═══════════════════════════════════════════════════════════════

def create_drawdown_monitor(max_dd_pct: float = 0.15,
                            max_dd_duration: int = 100) -> DrawdownMonitor:
    """
    Factory function pour créer DrawdownMonitor

    Args:
        max_dd_pct: Drawdown max autorisé (défaut 15%)
        max_dd_duration: Durée max DD (cycles, défaut 100)

    Returns:
        DrawdownMonitor configuré
    """
    return DrawdownMonitor(
        max_dd_pct=max_dd_pct,
        max_dd_duration=max_dd_duration,
        save_history=True
    )


if __name__ == "__main__":
    # Test simple
    logging.basicConfig(level=logging.INFO)

    monitor = create_drawdown_monitor(max_dd_pct=0.15, max_dd_duration=50)

    # Simuler PnL
    print("\n🔴 Test Drawdown Monitor:")

    # Montée
    for pnl in [100, 200, 300, 400, 500]:
        metrics = monitor.update(pnl)
        print(f"PnL: ${pnl} | Peak: ${metrics.peak_pnl:.0f} | DD: {metrics.current_dd_pct:.1%} | Duration: {metrics.dd_duration}")

    # Drawdown
    print("\n⚠️ Drawdown commence...")
    for pnl in [450, 400, 350, 300]:
        metrics = monitor.update(pnl)
        print(f"PnL: ${pnl} | Peak: ${metrics.peak_pnl:.0f} | DD: {metrics.current_dd_pct:.1%} | Duration: {metrics.dd_duration} | Halt: {monitor.should_halt()}")

    # Recovery
    print("\n✅ Recovery...")
    for pnl in [350, 400, 450, 500, 550]:
        metrics = monitor.update(pnl)
        print(f"PnL: ${pnl} | Peak: ${metrics.peak_pnl:.0f} | DD: {metrics.current_dd_pct:.1%} | Recovery time: {metrics.recovery_time}")

    print(f"\n📊 Max DD observé: {monitor.max_dd_pct_observed:.2%} (${monitor.max_dd_usd_observed:.2f})")


