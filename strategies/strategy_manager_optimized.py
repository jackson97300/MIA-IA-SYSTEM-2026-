"""
strategies/strategy_manager_optimized.py

STRATEGY MANAGER OPTIMISÉ - ML_READY
Gère les 10 stratégies sélectionnées (6 core + 4 game changers) avec :
- Priorités
- Cooldowns par stratégie
- Session filters
- ML thresholds par tier
- Conflict resolution

Version: 2.0 (10 stratégies)
Date: 2 Novembre 2025
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from core.logger import get_logger
from config.optimized_strategy_config import (
    get_optimized_config,
    get_ml_threshold_for_strategy,
    get_cooldown_for_strategy,
    is_session_allowed,
    get_position_size_multiplier,
    STRATEGY_PRIORITY
)

# Imports des 10 stratégies (6 core + 4 game changers)
try:
    from core.hybrid_strategy import HybridStrategy
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False

try:
    from strategies.gamma_pin_reversion import GammaPinReversion
    GAMMA_PIN_AVAILABLE = True
except ImportError:
    GAMMA_PIN_AVAILABLE = False

try:
    from strategies.zero_dte_wall_sweep import ZeroDTEWallSweepReversal
    ZERO_DTE_AVAILABLE = True
except ImportError:
    ZERO_DTE_AVAILABLE = False

try:
    from strategies.liquidity_sweep_reversal import LiquiditySweepReversal
    LIQUIDITY_SWEEP_AVAILABLE = True
except ImportError:
    LIQUIDITY_SWEEP_AVAILABLE = False

try:
    from strategies.vwap_band_squeeze_break import VwapBandSqueezeBreak
    VWAP_SQUEEZE_AVAILABLE = True
except ImportError:
    VWAP_SQUEEZE_AVAILABLE = False

try:
    from strategies.head_fake_detector import HeadFakeDetector
    HEAD_FAKE_AVAILABLE = True
except ImportError:
    HEAD_FAKE_AVAILABLE = False

# 4 Nouvelles stratégies game changers
try:
    from strategies.blind_spot_magnetic_pull import BlindSpotMagneticPull
    BLIND_SPOT_AVAILABLE = True
except ImportError:
    BLIND_SPOT_AVAILABLE = False

try:
    from strategies.gamma_wall_break_and_go import GammaWallBreakAndGo
    GAMMA_WALL_AVAILABLE = True
except ImportError:
    GAMMA_WALL_AVAILABLE = False

try:
    from strategies.hvl_magnet_fade import HVLMagnetFade
    HVL_MAGNET_AVAILABLE = True
except ImportError:
    HVL_MAGNET_AVAILABLE = False

try:
    from strategies.call_put_channel_rotation import CallPutChannelRotation
    CHANNEL_ROTATION_AVAILABLE = True
except ImportError:
    CHANNEL_ROTATION_AVAILABLE = False

logger = get_logger(__name__)


class OptimizedStrategyManager:
    """
    Gestionnaire optimisé pour les 10 stratégies ML_READY (6 core + 4 game changers)

    Fonctionnalités :
    - Évaluation par ordre de priorité
    - Cooldowns individuels par stratégie
    - Filtrage par session (Asia, London, US)
    - ML validation avec thresholds par tier
    - Résolution de conflits
    - Tracking performance par stratégie
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialisation du manager"""
        self.config = config or get_optimized_config()

        # Last signal time par stratégie (pour cooldowns)
        self.last_signal_time: Dict[str, datetime] = {}

        # Statistiques par stratégie
        self.stats = defaultdict(lambda: {
            'evaluations': 0,
            'signals_generated': 0,
            'cooldown_blocks': 0,
            'session_blocks': 0,
            'ml_rejections': 0,
            'conflicts': 0
        })

        # Statistiques globales
        self.global_stats = {
            'total_evaluations': 0,
            'total_signals': 0,
            'avg_processing_time_ms': 0.0
        }

        # === INITIALISATION DES 10 STRATÉGIES (6 core + 4 game changers) ===
        self.strategies: Dict[str, Any] = {}

        if "hybrid_strategy" in self.config.get('enabled_strategies', []):
            if HYBRID_AVAILABLE:
                self.strategies['hybrid_strategy'] = HybridStrategy()
                logger.info("✅ Hybrid Strategy chargée")

        if "gamma_pin_reversion" in self.config.get('enabled_strategies', []):
            if GAMMA_PIN_AVAILABLE:
                self.strategies['gamma_pin_reversion'] = GammaPinReversion()
                logger.info("✅ Gamma Pin Reversion chargée")

        if "zero_dte_wall_sweep" in self.config.get('enabled_strategies', []):
            if ZERO_DTE_AVAILABLE:
                self.strategies['zero_dte_wall_sweep'] = ZeroDTEWallSweepReversal()
                logger.info("✅ Zero DTE Wall Sweep chargée")

        if "liquidity_sweep_reversal" in self.config.get('enabled_strategies', []):
            if LIQUIDITY_SWEEP_AVAILABLE:
                self.strategies['liquidity_sweep_reversal'] = LiquiditySweepReversal()
                logger.info("✅ Liquidity Sweep Reversal chargée")

        if "vwap_band_squeeze_break" in self.config.get('enabled_strategies', []):
            if VWAP_SQUEEZE_AVAILABLE:
                self.strategies['vwap_band_squeeze_break'] = VwapBandSqueezeBreak()
                logger.info("✅ VWAP Band Squeeze Break chargée")

        if "head_fake_detector" in self.config.get('enabled_strategies', []):
            if HEAD_FAKE_AVAILABLE:
                self.strategies['head_fake_detector'] = HeadFakeDetector()
                logger.info("✅ Head Fake Detector chargée")

        # === 4 NOUVELLES STRATÉGIES GAME CHANGERS ===
        if "blind_spot_magnetic_pull" in self.config.get('enabled_strategies', []):
            if BLIND_SPOT_AVAILABLE:
                self.strategies['blind_spot_magnetic_pull'] = BlindSpotMagneticPull()
                logger.info("✅ Blind Spot Magnetic Pull chargée (GAME CHANGER #1)")

        if "gamma_wall_break_and_go" in self.config.get('enabled_strategies', []):
            if GAMMA_WALL_AVAILABLE:
                self.strategies['gamma_wall_break_and_go'] = GammaWallBreakAndGo()
                logger.info("✅ Gamma Wall Break And Go chargée (GAME CHANGER GPT)")

        if "hvl_magnet_fade" in self.config.get('enabled_strategies', []):
            if HVL_MAGNET_AVAILABLE:
                self.strategies['hvl_magnet_fade'] = HVLMagnetFade()
                logger.info("✅ HVL Magnet Fade chargée (GAME CHANGER GPT)")

        if "call_put_channel_rotation" in self.config.get('enabled_strategies', []):
            if CHANNEL_ROTATION_AVAILABLE:
                self.strategies['call_put_channel_rotation'] = CallPutChannelRotation()
                logger.info("✅ Call Put Channel Rotation chargée (GAME CHANGER GPT)")

        logger.info(f"✅ StrategyManager initialisé avec {len(self.strategies)} stratégies")

    def _get_signal_direction(self, signal: Any) -> Optional[str]:
        """
        Extrait la direction d'un signal (LONG/SHORT)
        Gère HybridSignal (action) et PatternSignal (side)
        """
        if hasattr(signal, 'side') and signal.side:
            return signal.side
        elif hasattr(signal, 'action'):
            if signal.action == "GO_LONG":
                return "LONG"
            elif signal.action == "GO_SHORT":
                return "SHORT"
        return None

    def evaluate_all(self, ml_data: Dict[str, Any], symbol: str = "ES") -> Optional[Any]:
        """
        Évalue toutes les stratégies par ordre de priorité

        Args:
            ml_data: Dict ML_READY complet
            symbol: Symbole (ES ou NQ)

        Returns:
            Signal final ou None
        """
        start_time = time.perf_counter()
        self.global_stats['total_evaluations'] += 1

        try:
            # Déterminer session actuelle
            current_session = self._get_current_session()
            current_time = datetime.now()

            all_signals = []

            # === ÉVALUATION PAR ORDRE DE PRIORITÉ ===
            priority_order = sorted(
                self.strategies.keys(),
                key=lambda s: STRATEGY_PRIORITY.get(s, 999)
            )

            for strategy_name in priority_order:
                self.stats[strategy_name]['evaluations'] += 1

                # === 1. CHECK COOLDOWN ===
                if self._is_in_cooldown(strategy_name, current_time):
                    self.stats[strategy_name]['cooldown_blocks'] += 1
                    logger.debug(f"⏱️ {strategy_name}: en cooldown")
                    continue

                # === 2. CHECK SESSION ===
                if not is_session_allowed(strategy_name, current_session):
                    self.stats[strategy_name]['session_blocks'] += 1
                    logger.debug(f"🕒 {strategy_name}: session {current_session} non autorisée")
                    continue

                # === 3. ANALYSER STRATÉGIE ===
                strategy = self.strategies[strategy_name]

                if strategy_name == "hybrid_strategy":
                    signal = strategy.analyze_from_ml_ready(ml_data)
                else:
                    signal = strategy.analyze_from_ml_ready(ml_data)

                # Vérifier si signal valide
                if signal:
                    signal_direction = self._get_signal_direction(signal)
                    if signal_direction:
                        all_signals.append((strategy_name, signal))
                        logger.info(f"✅ {strategy_name}: signal {signal_direction} généré")
                    else:
                        logger.debug(f"⚠️ {strategy_name}: signal retourné mais direction invalide")
                else:
                    logger.debug(f"⚠️ {strategy_name}: aucun signal retourné")

            # === 4. SÉLECTION MEILLEUR SIGNAL ===
            if not all_signals:
                # Log détaillé toutes les 100 évaluations pour diagnostic
                if self.global_stats['total_evaluations'] % 100 == 0:
                    total_blocks = sum(s['session_blocks'] + s['cooldown_blocks'] for s in self.stats.values())
                    total_session = sum(s['session_blocks'] for s in self.stats.values())
                    total_cooldown = sum(s['cooldown_blocks'] for s in self.stats.values())
                    logger.info(f"🔍 [{symbol}] Évaluation #{self.global_stats['total_evaluations']}: "
                              f"0 signaux (blocages: {total_blocks}, session: {current_session})")
                    logger.info(f"   📊 Détails: session_blocks={total_session}, cooldown_blocks={total_cooldown}")
                return None

            best_signal = self._select_best_signal(all_signals, ml_data)

            if best_signal:
                strategy_name = best_signal[0]
                signal = best_signal[1]

                # Marquer le temps du signal (cooldown)
                self.last_signal_time[strategy_name] = current_time

                # Stats
                self.stats[strategy_name]['signals_generated'] += 1
                self.global_stats['total_signals'] += 1

                # Processing time
                processing_time = (time.perf_counter() - start_time) * 1000
                alpha = 0.1
                self.global_stats['avg_processing_time_ms'] = (
                    alpha * processing_time +
                    (1 - alpha) * self.global_stats.get('avg_processing_time_ms', processing_time)
                )

                signal_direction = self._get_signal_direction(signal)
                entry = getattr(signal, 'entry', 'N/A')
                logger.info(f"🎯 Signal sélectionné: {strategy_name} → {signal_direction} @ {entry}")
                return signal

            return None

        except Exception as e:
            logger.error(f"❌ Erreur StrategyManager.evaluate_all: {e}")
            return None

    def _is_in_cooldown(self, strategy_name: str, current_time: datetime) -> bool:
        """Vérifie si stratégie est en cooldown"""
        if strategy_name not in self.last_signal_time:
            return False

        cooldown_seconds = get_cooldown_for_strategy(strategy_name)
        last_time = self.last_signal_time[strategy_name]
        elapsed = (current_time - last_time).total_seconds()

        return elapsed < cooldown_seconds

    def _get_current_session(self) -> str:
        """Détermine la session actuelle (basé sur EST timezone)"""
        from datetime import timezone, timedelta
        est_tz = timezone(timedelta(hours=-5))  # EST = UTC-5
        now_est = datetime.now(est_tz)
        hour = now_est.hour

        # Heures EST (corrigées)
        if 18 <= hour or hour < 2:
            return "ASIA"      # 18h-02h EST (00h-08h France)
        elif 2 <= hour < 9:
            return "LONDON"    # 02h-09h EST (08h-15h France)
        elif 9 <= hour < 16:
            return "US"        # 09h-16h EST (15h-22h France)
        else:
            return "OVERNIGHT" # 16h-18h EST (22h-00h France)

    def _select_best_signal(self, signals: List, ml_data: Dict) -> Optional[Any]:
        """
        Sélection du meilleur signal avec résolution de conflits

        Args:
            signals: Liste de (strategy_name, signal)
            ml_data: Dict ML_READY

        Returns:
            (strategy_name, signal) ou None
        """
        if not signals:
            return None

        # Si 1 seul signal
        if len(signals) == 1:
            return signals[0]

        # === RÉSOLUTION CONFLITS ===

        # 1. HeadFake peut invalider autres signaux
        headfake_signals = [s for s in signals if s[0] == "head_fake_detector"]
        if headfake_signals:
            logger.info("🚨 HeadFake détecté, invalide autres signaux")
            return headfake_signals[0]

        # 2. Signaux même direction
        long_signals = [s for s in signals if self._get_signal_direction(s[1]) == "LONG"]
        short_signals = [s for s in signals if self._get_signal_direction(s[1]) == "SHORT"]

        if long_signals and not short_signals:
            # Garder celui avec meilleur headroom
            best = max(long_signals, key=lambda s: self._get_headroom(s, ml_data))
            logger.info(f"✅ Confluence LONG: sélection {best[0]}")
            return best

        if short_signals and not long_signals:
            best = max(short_signals, key=lambda s: self._get_headroom(s, ml_data))
            logger.info(f"✅ Confluence SHORT: sélection {best[0]}")
            return best

        # 3. Signaux opposés → annuler
        if long_signals and short_signals:
            logger.warning("⚠️ Conflit LONG vs SHORT, annulation des 2")
            for strategy_name, _ in signals:
                self.stats[strategy_name]['conflicts'] += 1
            return None

        # 4. Par défaut : meilleure priorité
        return signals[0]

    def _get_headroom(self, signal_tuple: tuple, ml_data: Dict) -> float:
        """Calcule le headroom d'un signal"""
        strategy_name, signal = signal_tuple

        next_wall = ml_data.get('next_wall', {})
        if not next_wall:
            return 0.15  # Default

        wall_dist_pct = next_wall.get('dist_pct', 0.15)

        # Si signal aligné avec direction wall, bon headroom
        signal_direction = self._get_signal_direction(signal)
        if signal_direction == "LONG" and next_wall.get('side') == 'call':
            return wall_dist_pct
        elif signal_direction == "SHORT" and next_wall.get('side') == 'put':
            return wall_dist_pct
        else:
            return 0.05  # Mauvais headroom

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return {
            'global': self.global_stats,
            'per_strategy': dict(self.stats)
        }

    def reset_cooldowns(self):
        """Reset tous les cooldowns (test/debug)"""
        self.last_signal_time.clear()
        logger.info("🔄 Cooldowns réinitialisés")
