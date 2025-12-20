"""
Backtest Analyzer - Analyse exhaustive des résultats

Répond aux 7 questions clés:
1. Quels niveaux sont les plus pertinents?
2. Quels SL/TP sont les plus performants?
3. Quelles heures sont les plus profitables?
4. Quels moments éviter?
5. Quels seuils de confiance optimaux?
6. Quelle confluence strength minimale?
7. Quel contexte marché favorable?
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class BacktestAnalyzer:
    """Analyseur exhaustif des résultats de backtest"""

    def analyze_level_performance(self, results: Dict) -> pd.DataFrame:
        """
        Question 1: Quels niveaux sont les PLUS PERTINENTS?

        Returns:
            DataFrame trié par performance
        """
        if 'by_level' not in results:
            return pd.DataFrame()

        level_data = results['by_level']
        rows = []

        for level_name, stats in level_data.items():
            if not isinstance(stats, dict):
                continue
            rows.append({
                'level': str(level_name),
                'trades': int(stats.get('trades', 0)) if isinstance(stats.get('trades', 0), (int, float)) else 0,
                'wins': int(stats.get('wins', 0)) if isinstance(stats.get('wins', 0), (int, float)) else 0,
                'losses': int(stats.get('losses', 0)) if isinstance(stats.get('losses', 0), (int, float)) else 0,
                'win_rate': float(stats.get('win_rate', 0)) if isinstance(stats.get('win_rate', 0), (int, float)) else 0.0,
                'pnl_ticks': float(stats.get('pnl_ticks', 0)) if isinstance(stats.get('pnl_ticks', 0), (int, float)) else 0.0,
                'avg_pnl': float(stats.get('avg_pnl', 0)) if isinstance(stats.get('avg_pnl', 0), (int, float)) else 0.0
            })

        df = pd.DataFrame(rows)
        if len(df) > 0:
            df = df.sort_values('win_rate', ascending=False)

        return df

    def analyze_sl_tp_performance(self, results: Dict) -> pd.DataFrame:
        """
        Question 2: Quels SL/TP sont les PLUS PERFORMANTS?

        Returns:
            DataFrame avec meilleure config par symbole
        """
        if 'by_sl_tp' not in results:
            return pd.DataFrame()

        sl_tp_data = results['by_sl_tp']
        rows = []

        for config_key, stats in sl_tp_data.items():
            if not isinstance(stats, dict):
                continue
            rows.append({
                'config': str(config_key),
                'trades': int(stats.get('trades', 0)) if isinstance(stats.get('trades', 0), (int, float)) else 0,
                'wins': int(stats.get('wins', 0)) if isinstance(stats.get('wins', 0), (int, float)) else 0,
                'losses': int(stats.get('losses', 0)) if isinstance(stats.get('losses', 0), (int, float)) else 0,
                'win_rate': float(stats.get('win_rate', 0)) if isinstance(stats.get('win_rate', 0), (int, float)) else 0.0,
                'pnl_ticks': float(stats.get('pnl_ticks', 0)) if isinstance(stats.get('pnl_ticks', 0), (int, float)) else 0.0,
                'avg_pnl': float(stats.get('avg_pnl', 0)) if isinstance(stats.get('avg_pnl', 0), (int, float)) else 0.0
            })

        df = pd.DataFrame(rows)
        if len(df) > 0:
            df = df.sort_values('pnl_ticks', ascending=False)

        return df

    def analyze_time_performance(self, results: Dict) -> pd.DataFrame:
        """
        Question 3: Quelles HEURES sont les PLUS PROFITABLES?

        Returns:
            DataFrame avec best/worst hours
        """
        if 'by_time' not in results:
            return pd.DataFrame()

        time_data = results['by_time']
        rows = []

        for hour, stats in time_data.items():
            if not isinstance(stats, dict):
                continue
            rows.append({
                'hour': str(hour),
                'trades': int(stats.get('trades', 0)) if isinstance(stats.get('trades', 0), (int, float)) else 0,
                'wins': int(stats.get('wins', 0)) if isinstance(stats.get('wins', 0), (int, float)) else 0,
                'losses': int(stats.get('losses', 0)) if isinstance(stats.get('losses', 0), (int, float)) else 0,
                'win_rate': float(stats.get('win_rate', 0)) if isinstance(stats.get('win_rate', 0), (int, float)) else 0.0,
                'pnl_ticks': float(stats.get('pnl_ticks', 0)) if isinstance(stats.get('pnl_ticks', 0), (int, float)) else 0.0,
                'avg_pnl': float(stats.get('avg_pnl', 0)) if isinstance(stats.get('avg_pnl', 0), (int, float)) else 0.0
            })

        df = pd.DataFrame(rows)
        if len(df) > 0:
            df = df.sort_values('pnl_ticks', ascending=False)

        return df

    def identify_avoid_periods(self, results: Dict) -> List[Dict]:
        """
        Question 4: Quels MOMENTS ÉVITER?

        Returns:
            Liste de périodes à éviter avec raisons
        """
        avoid_periods = []

        if 'by_time' in results:
            time_data = results['by_time']
            for hour, stats in time_data.items():
                if not isinstance(stats, dict):
                    continue
                win_rate = float(stats.get('win_rate', 0)) if isinstance(stats.get('win_rate', 0), (int, float)) else 0.0
                pnl = float(stats.get('pnl_ticks', 0)) if isinstance(stats.get('pnl_ticks', 0), (int, float)) else 0.0

                if win_rate < 40 or pnl < -100:
                    try:
                        hour_int = int(hour) if isinstance(hour, (int, float, str)) and str(hour).replace('_', '').isdigit() else 0
                    except:
                        hour_int = 0
                    avoid_periods.append({
                        'period': f"{hour_int}h00",
                        'reason': f"Win rate: {win_rate:.1f}%, P&L: {pnl:.1f} ticks",
                        'win_rate': win_rate,
                        'pnl': pnl
                    })

        return sorted(avoid_periods, key=lambda x: x['win_rate'])

    def optimize_confidence_thresholds(self, results: Dict) -> Dict:
        """
        Question 5: Quels SEUILS de confiance OPTIMAUX?

        Returns:
            Seuils optimaux par symbole
        """
        # Pour l'instant, retourne valeurs par défaut
        # À implémenter avec données de confiance si disponibles
        return {
            'ES': {'layer1': 0.20, 'layer2': 0.60, 'layer3': 0.70},
            'NQ': {'layer1': 0.20, 'layer2': 0.60, 'layer3': 0.70}
        }

    def optimize_confluence_strength(self, results: Dict) -> Dict:
        """
        Question 6: Quelle CONFLUENCE strength minimale?

        Returns:
            Strength minimum recommandée
        """
        if 'by_confluence' not in results:
            return {'min_strength': 2, 'recommended': 3}

        confluence_data = results['by_confluence']
        best_strength = 2
        best_win_rate = 0

        for strength, stats in confluence_data.items():
            if not isinstance(stats, dict):
                continue
            win_rate = float(stats.get('win_rate', 0))
            trades = int(stats.get('trades', 0)) if isinstance(stats.get('trades', 0), (int, float)) else 0
            if win_rate > best_win_rate and trades >= 10:
                best_win_rate = win_rate
                best_strength = int(strength) if isinstance(strength, (int, float, str)) and str(strength).isdigit() else 2

        return {
            'min_strength': 2,
            'recommended': max(3, best_strength),
            'best_win_rate': best_win_rate
        }

    def analyze_market_context(self, results: Dict) -> Dict:
        """
        Question 7: Quel CONTEXTE MARCHÉ favorable?

        Returns:
            Contextes favorables/défavorables
        """
        # Pour l'instant, retourne structure de base
        # À enrichir avec données VIX, volume, etc. si disponibles
        return {
            'favorable': {
                'win_rate_threshold': 55,
                'pnl_threshold': 0
            },
            'unfavorable': {
                'win_rate_threshold': 45,
                'pnl_threshold': -50
            }
        }
