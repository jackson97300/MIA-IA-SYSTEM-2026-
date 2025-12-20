"""
VALIDATEUR ANTI-UNKNOWN STRATEGY

Créé le 20/11/2024 pour résoudre le bug critique des 64% UNKNOWN
"""

import logging
from typing import Any, Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class StrategyValidator:
    """
    Validateur STRICT pour garantir qu'aucun trade n'ait strategy=UNKNOWN
    """

    # Liste exhaustive des stratégies valides
    VALID_STRATEGIES = [
        'menthorq_3layer_strategy',
        'ml_3layer_strategy',
        'vwap_sd_options_confluence_strategy',
        'gamma_wall_rejection_strategy',
        'gamma_wall_break_and_go',
        'liquidity_sweep_reversal',
        'initial_balance_breakout',
        'blind_spot_magnetic_pull',
        'pvwap_magnetic_bounce',
        'vpoc_extreme_reversion',
        'weekly_vwap_extreme_reversion',
        'call_put_channel_rotation',
        'zero_dte_wall_sweep',
        'hvl_magnet_fade',
        'next_wall_micro_zone_scalp',
        'head_fake_detector',
        'bracket_detector_ml_ready',
        'vwap_band_squeeze_break',
        'gamma_pin_reversion',
        'hybrid_strategy',
        'mia_bullish'
    ]

    @classmethod
    def validate_and_fix(cls, signal: Any, context: Dict = None) -> Tuple[str, str]:
        """
        Valide et CORRIGE une strategy. NE RETOURNE JAMAIS UNKNOWN.

        Args:
            signal: Le signal à valider
            context: Contexte additionnel (tick data, etc.)

        Returns:
            (strategy_name, detection_method)
        """
        strategy = None
        detection_method = "none"

        # ÉTAPE 1: Extraction standard
        if isinstance(signal, dict):
            strategy = signal.get('strategy') or signal.get('strategy_name')
            if strategy:
                detection_method = "dict_key"
        else:
            strategy = getattr(signal, 'strategy', None) or getattr(signal, 'strategy_name', None)
            if strategy:
                detection_method = "object_attr"

        # ÉTAPE 2: Si UNKNOWN ou vide, corriger
        if not strategy or strategy == 'UNKNOWN':
            strategy = cls._detect_strategy(signal, context)
            detection_method = "intelligent_detection"

            logger.warning(f"⚠️ VALIDATOR: Strategy UNKNOWN corrigée → {strategy}")

        # ÉTAPE 3: Validation finale
        if strategy not in cls.VALID_STRATEGIES:
            logger.warning(f"⚠️ Strategy '{strategy}' non standard mais acceptée")

        # NE JAMAIS RETOURNER UNKNOWN
        if strategy == 'UNKNOWN' or not strategy:
            strategy = 'menthorq_3layer_strategy'
            detection_method = "fallback_emergency"
            logger.error("❌ EMERGENCY FALLBACK: menthorq_3layer_strategy")

        return strategy, detection_method

    @classmethod
    def _detect_strategy(cls, signal: Any, context: Dict = None) -> str:
        """
        Détection intelligente de la stratégie
        """
        # Détection par type de classe
        if hasattr(signal, '__class__'):
            class_name = signal.__class__.__name__

            if 'Confluence' in class_name or 'VWAP' in class_name:
                return 'vwap_sd_options_confluence_strategy'
            elif 'MenthorQ' in class_name:
                return 'menthorq_3layer_strategy'
            elif 'ML' in class_name or '3Layer' in class_name:
                return 'ml_3layer_strategy'
            elif 'Gamma' in class_name:
                return 'gamma_wall_rejection_strategy'

        # Détection par attributs/caractéristiques
        confluence = 0
        has_layers = False
        has_vwap = False

        if isinstance(signal, dict):
            confluence = signal.get('confluence', signal.get('confidence', 0))
            has_layers = 'layer1_confidence' in signal
            has_vwap = 'vwap_zone' in signal or 'vwap_distance' in signal
        else:
            confluence = getattr(signal, 'confluence', getattr(signal, 'confidence', 0))
            has_layers = hasattr(signal, 'layer1_confidence')
            has_vwap = hasattr(signal, 'vwap_zone') or hasattr(signal, 'vwap_distance')

        # Décision basée sur caractéristiques
        if has_vwap or confluence > 0.65:
            return 'vwap_sd_options_confluence_strategy'
        elif has_layers:
            return 'ml_3layer_strategy'

        # Détection depuis contexte
        if context:
            if context.get('menthorq_score', 0) > 0.3:
                return 'menthorq_3layer_strategy'
            if abs(context.get('d_vwap_ticks', 0)) > 50:
                return 'vwap_sd_options_confluence_strategy'

        # Fallback statistique (basé sur distribution réelle)
        # 64% UNKNOWN étaient probablement vwap_sd
        return 'vwap_sd_options_confluence_strategy'

    @classmethod
    def emergency_fix_all_unknowns(cls, trades: list) -> int:
        """
        Corrige tous les trades UNKNOWN dans une liste
        """
        fixed = 0
        for trade in trades:
            if trade.get('strategy') == 'UNKNOWN':
                # Analyse des caractéristiques
                confluence = trade.get('confluence', 0)
                vwap_dist = abs(trade.get('vwap_distance', 0))
                ml_conf = trade.get('ml_confidence', 0)

                if confluence > 0.65 or vwap_dist > 50:
                    trade['strategy'] = 'vwap_sd_options_confluence_strategy'
                elif ml_conf > 0:
                    trade['strategy'] = 'ml_3layer_strategy'
                else:
                    trade['strategy'] = 'menthorq_3layer_strategy'

                trade['strategy_fixed'] = True
                fixed += 1

        return fixed


# Instance globale
strategy_validator = StrategyValidator()

















