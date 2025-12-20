"""
MIA_IA_SYSTEM - Timeframe Aligner
Gestion de l'alignement des timeframes (daily, weekly, monthly)

Version: 1.0 - GPT v3.0 Improvements
Date: 2 Novembre 2025
"""

from typing import Dict, Any
import numpy as np


class TimeframeAligner:
    """
    Analyse l'alignement des timeframes multiples

    Détecte les conflits (ex: bull monthly mais bear weekly)
    Ajuste les poids des composantes selon l'alignement
    """

    def __init__(self, ml_data: Dict[str, Any]):
        """
        Initialise l'analyseur de timeframes

        Args:
            ml_data: Dictionnaire ML_READY avec vwap, vwap_weekly, vwap_monthly
        """
        self.ml_data = ml_data
        self.price = ml_data.get('mid')
        self.vwap_daily = ml_data.get('vwap')
        self.vwap_weekly = ml_data.get('vwap_weekly')
        self.vwap_monthly = ml_data.get('vwap_monthly')

    def get_alignment(self) -> int:
        """
        Retourne l'alignement des timeframes

        Returns:
            +1 : Tous alignés (bull-bull ou bear-bear)
            -1 : Conflit (ex: bull monthly, bear weekly)
             0 : Données insuffisantes ou neutre
        """
        if not all([self.price, self.vwap_weekly, self.vwap_monthly]):
            return 0  # Pas assez de données

        # Position vs weekly
        weekly_bull = self.price > self.vwap_weekly

        # Position vs monthly
        monthly_bull = self.price > self.vwap_monthly

        # Alignés ?
        if weekly_bull == monthly_bull:
            return +1  # Alignés (même direction)
        else:
            return -1  # Conflit (directions opposées)

    def get_weight_adjustments(self) -> Dict[str, float]:
        """
        Ajuste les poids des composantes selon l'alignement

        SI CONFLIT (monthly bull, weekly bear):
          → +5% poids VWAP/OF (plus sensible court terme)
          → -5% poids VVA (moins confiance trend long terme)

        SI ALIGNÉS:
          → Poids normaux (1.0)

        Returns:
            Dict avec multiplicateurs pour chaque composante
        """
        alignment = self.get_alignment()

        if alignment == -1:  # CONFLIT
            return {
                'vwap_weight': 1.05,   # +5% (favoriser court terme)
                'of_weight': 1.05,      # +5% (order flow plus important)
                'vva_weight': 0.95,     # -5% (réduire confiance VVA)
                'cd_weight': 1.00,      # Neutre
                'vix_weight': 1.00      # Neutre
            }

        else:  # ALIGNÉS ou PAS DE DONNÉES
            return {
                'vwap_weight': 1.00,
                'of_weight': 1.00,
                'vva_weight': 1.00,
                'cd_weight': 1.00,
                'vix_weight': 1.00
            }

    def get_trend_strength(self, timeframe: str = 'weekly') -> float:
        """
        Force du trend sur un timeframe donné

        Args:
            timeframe: 'daily', 'weekly', 'monthly'

        Returns:
            Force [0, 1] avec 0.5 = neutre
        """
        if not self.price:
            return 0.5

        if timeframe == 'daily':
            vwap = self.vwap_daily
        elif timeframe == 'weekly':
            vwap = self.vwap_weekly
        elif timeframe == 'monthly':
            vwap = self.vwap_monthly
        else:
            return 0.5

        if not vwap:
            return 0.5

        # Distance relative au VWAP
        distance = (self.price - vwap) / vwap

        # Convertir en force [0, 1] avec tanh
        strength = 0.5 + 0.5 * np.tanh(distance * 100)

        return np.clip(strength, 0.0, 1.0)

    def get_info(self) -> Dict[str, Any]:
        """
        Retourne toutes les infos d'alignement

        Returns:
            Dict complet avec alignment, weights, trends
        """
        alignment = self.get_alignment()
        weights = self.get_weight_adjustments()

        return {
            'price': self.price,
            'vwap_daily': self.vwap_daily,
            'vwap_weekly': self.vwap_weekly,
            'vwap_monthly': self.vwap_monthly,
            'alignment': alignment,
            'alignment_str': 'ALIGNED' if alignment == 1 else 'CONFLICT' if alignment == -1 else 'UNKNOWN',
            'weights': weights,
            'trend_daily': self.get_trend_strength('daily'),
            'trend_weekly': self.get_trend_strength('weekly'),
            'trend_monthly': self.get_trend_strength('monthly')
        }


if __name__ == "__main__":
    # Test avec données réelles GPT
    test_data = {
        'mid': 6882.13,
        'vwap': 6896.65,
        'vwap_weekly': 6913.33,
        'vwap_monthly': 6808.93
    }

    print("=== TIMEFRAME ALIGNER TEST ===")
    aligner = TimeframeAligner(test_data)

    info = aligner.get_info()

    print(f"\nPrix: {info['price']}")
    print(f"VWAP Daily: {info['vwap_daily']}")
    print(f"VWAP Weekly: {info['vwap_weekly']}")
    print(f"VWAP Monthly: {info['vwap_monthly']}")

    print(f"\n--- ALIGNMENT ---")
    print(f"Status: {info['alignment_str']} ({info['alignment']})")

    print(f"\n--- WEIGHT ADJUSTMENTS ---")
    for key, value in info['weights'].items():
        change = (value - 1.0) * 100
        print(f"{key}: {value:.2f} ({change:+.1f}%)")

    print(f"\n--- TREND STRENGTH [0=bear, 0.5=neutre, 1=bull] ---")
    print(f"Daily: {info['trend_daily']:.3f}")
    print(f"Weekly: {info['trend_weekly']:.3f}")
    print(f"Monthly: {info['trend_monthly']:.3f}")

    print(f"\n🎯 ANALYSE:")
    if info['alignment'] == -1:
        print("⚠️ CONFLIT DÉTECTÉ: Trend monthly BULL mais weekly BEAR")
        print("→ Augmentation poids VWAP/OF (+5%)")
        print("→ Réduction poids VVA (-5%)")
    else:
        print("✅ Timeframes alignés, poids normaux")




